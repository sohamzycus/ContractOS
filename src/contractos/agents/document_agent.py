"""DocumentAgent — answers questions about a single contract using facts, bindings, and LLM reasoning."""

from __future__ import annotations

import json
import time
from datetime import datetime

from contractos.fabric.trust_graph import TrustGraph
from contractos.llm.provider import LLMMessage, LLMProvider
from contractos.models.binding import Binding
from contractos.models.fact import Fact
from contractos.models.inference import Inference, InferenceType
from contractos.models.provenance import ProvenanceChain, ProvenanceNode
from contractos.models.query import Query, QueryResult, QueryScope
from contractos.tools.binding_resolver import resolve_term

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

    Uses facts and bindings from TrustGraph + LLM for reasoning.
    """

    def __init__(
        self,
        trust_graph: TrustGraph,
        llm: LLMProvider,
    ) -> None:
        self._graph = trust_graph
        self._llm = llm

    async def answer(self, query: Query) -> QueryResult:
        """Answer a question about a contract.

        Pipeline:
        1. Retrieve facts and bindings for the target document
        2. Build context with resolved bindings
        3. Send to LLM with system prompt
        4. Parse response and build QueryResult with provenance
        """
        start_time = time.monotonic()

        if not query.target_document_ids:
            return self._not_found_result(query, "No target document specified", start_time)

        document_id = query.target_document_ids[0]

        # Step 1: Retrieve facts and bindings
        facts = self._graph.get_facts_by_document(document_id)
        bindings = self._graph.get_bindings_by_document(document_id)
        clauses = self._graph.get_clauses_by_document(document_id)

        if not facts:
            return self._not_found_result(
                query, f"No facts found for document {document_id}", start_time
            )

        # Step 2: Build context
        context = self._build_context(facts, bindings, query.text)

        # Step 3: Send to LLM
        messages = [
            LLMMessage(role="user", content=context),
        ]

        try:
            llm_response = await self._llm.complete_json(
                messages, system=SYSTEM_PROMPT, temperature=0.0
            )
        except Exception as e:
            return self._error_result(query, str(e), start_time)

        # Step 4: Parse and build result
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return self._build_result(query, llm_response, facts, elapsed_ms)

    def _build_context(
        self,
        facts: list[Fact],
        bindings: list[Binding],
        question: str,
    ) -> str:
        """Build the context string for the LLM."""
        parts = [f"## Question\n{question}\n"]

        # Add bindings
        if bindings:
            parts.append("## Entity Bindings")
            for b in bindings:
                parts.append(f"- \"{b.term}\" → \"{b.resolves_to}\" (type: {b.binding_type})")
            parts.append("")

        # Add facts (grouped by type)
        parts.append("## Extracted Facts")
        for fact in facts[:100]:  # limit to avoid token overflow
            parts.append(
                f"- [{fact.fact_id}] ({fact.fact_type}) \"{fact.value}\" "
                f"@ {fact.evidence.location_hint}"
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
