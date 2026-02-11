"""DocumentAgent — answers questions about a single contract using facts, bindings, and LLM reasoning.

Uses FAISS-backed semantic retrieval to select the most relevant facts for each
query, replacing the naive full-scan approach. The retrieval pipeline:

1. Semantic search: FAISS top-k nearest neighbors (sentence-transformers embeddings)
2. Context assembly: relevant facts + all bindings + clause headings
3. LLM reasoning: grounded answer with provenance chain
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime

from contractos.fabric.embedding_index import EmbeddingIndex, SearchResult
from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import LLMMessage, LLMProvider
from contractos.models.binding import Binding
from contractos.models.fact import Fact
from contractos.models.inference import Inference, InferenceType
from contractos.models.provenance import ProvenanceChain, ProvenanceNode
from contractos.models.query import Query, QueryResult, QueryScope
from contractos.tools.binding_resolver import resolve_term

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are ContractOS, a contract intelligence system. You answer questions about contracts
using ONLY the facts and bindings provided. You must:

1. Ground every claim in specific facts (cite fact_ids)
2. Resolve entity aliases using bindings
3. Distinguish between facts (directly stated) and inferences (derived)
4. Express confidence based on evidence strength
5. Never fabricate information not in the provided context

Respond in JSON format:
{
  "answer": "Your answer text",
  "answer_type": "fact" | "inference" | "not_found",
  "confidence": 0.0-1.0,
  "facts_referenced": ["f-001", "f-002"],
  "reasoning_chain": "Step-by-step reasoning",
  "inferences": [{"claim": "...", "type": "obligation|coverage|...", "supporting_facts": ["f-001"]}]
}"""


class DocumentAgent:
    """Answers questions about a single contract document.

    Uses FAISS semantic retrieval + TrustGraph facts + LLM for reasoning.
    """

    def __init__(
        self,
        trust_graph: TrustGraph,
        llm: LLMProvider,
        embedding_index: EmbeddingIndex | None = None,
    ) -> None:
        self._graph = trust_graph
        self._llm = llm
        self._embedding_index = embedding_index

    async def answer(self, query: Query) -> QueryResult:
        """Answer a question about one or more contracts.

        Supports multi-document queries: retrieves facts from all target
        documents and merges them into a single context for the LLM.

        Pipeline:
        1. For each document: FAISS semantic retrieval (or full-scan fallback)
        2. Merge facts + bindings across all documents
        3. Build context with document source labels
        4. Send to LLM with system prompt
        5. Parse response and build QueryResult with provenance
        """
        start_time = time.monotonic()

        if not query.target_document_ids:
            return self._not_found_result(query, "No target document specified", start_time)

        # Collect facts and bindings from ALL target documents
        all_facts: list[Fact] = []
        all_bindings: list[Binding] = []
        retrieval_method = "full_scan"
        doc_titles: dict[str, str] = {}

        for document_id in query.target_document_ids:
            # Get document title for labeling
            contract = self._graph.get_contract(document_id)
            doc_titles[document_id] = contract.title if contract else document_id

            bindings = self._graph.get_bindings_by_document(document_id)
            all_bindings.extend(bindings)

            # Semantic retrieval per document
            if self._embedding_index and self._embedding_index.has_document(document_id):
                search_results = self._embedding_index.search(
                    document_id, query.text, top_k=30
                )
                retrieval_method = "faiss_semantic"

                doc_facts = self._graph.get_facts_by_document(document_id)
                fact_lookup = {f.fact_id: f for f in doc_facts}

                facts: list[Fact] = []
                seen: set[str] = set()
                for sr in search_results:
                    if sr.chunk.chunk_type == "fact":
                        fid = sr.chunk.metadata.get("fact_id", sr.chunk.chunk_id)
                        if fid in fact_lookup and fid not in seen:
                            facts.append(fact_lookup[fid])
                            seen.add(fid)

                # Supplement if few results
                if len(facts) < 10:
                    for f in doc_facts:
                        if f.fact_id not in seen:
                            facts.append(f)
                            seen.add(f.fact_id)
                            if len(facts) >= 50:
                                break

                all_facts.extend(facts)
                logger.info(
                    "Semantic retrieval [%s]: %d facts (method=%s)",
                    document_id, len(facts), retrieval_method,
                )
            else:
                doc_facts = self._graph.get_facts_by_document(document_id)
                all_facts.extend(doc_facts)

        if not all_facts:
            return self._not_found_result(
                query, "No facts found for the target documents", start_time
            )

        # Build context (multi-doc aware)
        is_multi = len(query.target_document_ids) > 1
        context = self._build_context(
            all_facts, all_bindings, query.text, retrieval_method,
            doc_titles=doc_titles if is_multi else None,
        )

        # Send to LLM
        messages = [
            LLMMessage(role="user", content=context),
        ]

        try:
            llm_response = await self._llm.complete_json(
                messages, system=SYSTEM_PROMPT, temperature=0.0
            )
        except Exception as e:
            return self._error_result(query, str(e), start_time)

        # Parse and build result
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        result = self._build_result(query, llm_response, all_facts, elapsed_ms)
        result.retrieval_method = retrieval_method
        return result

    def _build_context(
        self,
        facts: list[Fact],
        bindings: list[Binding],
        question: str,
        retrieval_method: str = "full_scan",
        doc_titles: dict[str, str] | None = None,
    ) -> str:
        """Build the context string for the LLM.

        When using semantic retrieval, facts are pre-sorted by relevance.
        For multi-document queries, facts are labeled with their source document.
        """
        parts = [f"## Question\n{question}\n"]

        if doc_titles and len(doc_titles) > 1:
            parts.append("## Documents Being Queried")
            for did, title in doc_titles.items():
                parts.append(f"- [{did}] {title}")
            parts.append("")

        if retrieval_method == "faiss_semantic":
            parts.append(
                f"_Note: The following {len(facts)} facts were selected by semantic "
                f"similarity search (FAISS) as most relevant to your question._\n"
            )

        # Add bindings
        if bindings:
            parts.append("## Entity Bindings")
            for b in bindings:
                doc_label = ""
                if doc_titles and len(doc_titles) > 1:
                    doc_label = f" [from: {doc_titles.get(b.document_id, b.document_id)}]"
                parts.append(
                    f"- \"{b.term}\" → \"{b.resolves_to}\" (type: {b.binding_type}){doc_label}"
                )
            parts.append("")

        # Add facts (pre-sorted by relevance when using FAISS)
        parts.append("## Extracted Facts")
        for fact in facts[:80]:  # limit to avoid token overflow
            doc_label = ""
            if doc_titles and len(doc_titles) > 1:
                doc_label = f" [doc: {doc_titles.get(fact.evidence.document_id, fact.evidence.document_id)}]"
            parts.append(
                f"- [{fact.fact_id}] ({fact.fact_type}) \"{fact.value}\" "
                f"@ {fact.evidence.location_hint}{doc_label}"
            )

        return "\n".join(parts)

    def _build_result(
        self,
        query: Query,
        llm_response: dict,
        facts: list[Fact],
        elapsed_ms: int,
    ) -> QueryResult:
        """Build a QueryResult from the LLM response."""
        answer = llm_response.get("answer", "Unable to determine answer.")
        answer_type = llm_response.get("answer_type", "inference")
        confidence = llm_response.get("confidence")
        facts_referenced = llm_response.get("facts_referenced", [])
        reasoning_chain = llm_response.get("reasoning_chain", "")

        # Build provenance
        nodes = []
        fact_lookup = {f.fact_id: f for f in facts}
        for fid in facts_referenced:
            fact = fact_lookup.get(fid)
            if fact:
                nodes.append(ProvenanceNode(
                    node_type="fact",
                    reference_id=fid,
                    summary=f"{fact.evidence.location_hint}: \"{fact.value[:80]}\"",
                    document_location=fact.evidence.location_hint,
                ))

        provenance = ProvenanceChain(
            nodes=nodes if nodes else [ProvenanceNode(
                node_type="inference",
                reference_id="system",
                summary="Answer derived from document context",
            )],
            reasoning_summary=reasoning_chain or answer[:200],
        )

        return QueryResult(
            result_id=f"r-{query.query_id}",
            query_id=query.query_id,
            answer=answer,
            answer_type=answer_type if answer_type in ("fact", "inference", "not_found", "opinion") else "inference",
            confidence=confidence,
            provenance=provenance,
            facts_referenced=facts_referenced,
            generated_at=datetime.now(),
            generation_time_ms=elapsed_ms,
        )

    def _not_found_result(self, query: Query, reason: str, start_time: float) -> QueryResult:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return QueryResult(
            result_id=f"r-{query.query_id}",
            query_id=query.query_id,
            answer=reason,
            answer_type="not_found",
            confidence=0.0,
            provenance=ProvenanceChain(
                nodes=[ProvenanceNode(
                    node_type="reasoning",
                    reference_id="not_found",
                    summary=reason,
                )],
                reasoning_summary=reason,
            ),
            facts_referenced=[],
            generated_at=datetime.now(),
            generation_time_ms=elapsed_ms,
        )

    def _error_result(self, query: Query, error: str, start_time: float) -> QueryResult:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return QueryResult(
            result_id=f"r-{query.query_id}",
            query_id=query.query_id,
            answer=f"Error during reasoning: {error}",
            answer_type="not_found",
            confidence=0.0,
            provenance=ProvenanceChain(
                nodes=[ProvenanceNode(
                    node_type="reasoning",
                    reference_id="error",
                    summary=error[:200] if error else "Unknown error",
                )],
                reasoning_summary=f"Error: {error}"[:200] if error else "Unknown error",
            ),
            facts_referenced=[],
            generated_at=datetime.now(),
            generation_time_ms=elapsed_ms,
        )
