"""MCP tool definitions for ContractOS.

Each tool maps to a user intent (not a raw API endpoint).  All LLM
calls go through ``ctx.state.llm`` — the provider abstraction.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from contractos.mcp.context import MCPContext

logger = logging.getLogger("contractos.mcp.tools")


def register_tools(mcp: FastMCP, ctx: MCPContext) -> None:  # noqa: C901
    """Register all 13 ContractOS MCP tools."""

    # ── 1. upload_contract ───────────────────────────────────

    @mcp.tool()
    async def upload_contract(file_path: str) -> dict[str, Any]:
        """Upload and analyse a contract document (DOCX or PDF).

        Returns document ID, extracted fact/clause/binding counts, and timing.
        """
        t0 = time.perf_counter()
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        ext = path.suffix.lower()
        if ext not in (".docx", ".pdf"):
            return {"error": f"Unsupported format: {ext}. Use .docx or .pdf"}

        try:
            import hashlib
            import uuid
            from datetime import datetime, timezone

            from contractos.fabric.embedding_index import build_chunks_from_extraction
            from contractos.models.document import Contract
            from contractos.tools.binding_resolver import resolve_bindings
            from contractos.tools.fact_extractor import extract_from_file

            doc_id = uuid.uuid4().hex[:12]
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            result = extract_from_file(str(path), doc_id)

            full_text = result.parsed_document.full_text if result.parsed_document else ""
            all_bindings = resolve_bindings(result.facts, result.bindings, full_text, doc_id)

            parsed = result.parsed_document
            word_count = len(full_text.split()) if full_text else 0
            parties: list[str] = []
            for b in all_bindings:
                if b.binding_type.value == "alias" and b.resolves_to not in parties:
                    parties.append(b.resolves_to)

            now = datetime.now(timezone.utc)
            contract = Contract(
                document_id=doc_id,
                title=path.stem,
                file_path=str(path),
                file_format=ext.lstrip("."),
                file_hash=file_hash,
                parties=parties,
                page_count=0,
                word_count=word_count,
                indexed_at=now,
                last_parsed_at=now,
                extraction_version="0.1.0",
            )

            tg = ctx.state.trust_graph
            tg.insert_contract(contract)
            if result.facts:
                tg.insert_facts(result.facts)
            for b in all_bindings:
                tg.insert_binding(b)
            for c in result.clauses:
                tg.insert_clause(c)
            for xr in result.cross_references:
                tg.insert_cross_reference(xr)
            for slot in result.clause_fact_slots:
                tg.insert_clause_fact_slot(slot)

            chunks = build_chunks_from_extraction(
                doc_id, result.facts, result.clauses, all_bindings
            )
            ctx.state.embedding_index.index_document(doc_id, chunks)

            elapsed = int((time.perf_counter() - t0) * 1000)
            return {
                "document_id": doc_id,
                "filename": path.name,
                "fact_count": len(result.facts),
                "clause_count": len(result.clauses),
                "binding_count": len(all_bindings),
                "extraction_time_ms": elapsed,
                "message": f"Successfully analysed {path.name}: {len(result.facts)} facts, "
                f"{len(result.clauses)} clauses, {len(all_bindings)} bindings",
            }
        except Exception as exc:
            logger.exception("upload_contract failed")
            return {"error": f"Extraction failed: {exc}"}

    # ── 2. load_sample_contract ──────────────────────────────

    @mcp.tool()
    async def load_sample_contract(filename: str) -> dict[str, Any]:
        """Load a built-in sample contract for testing.

        Available: simple_nda.pdf, simple_procurement.docx,
        complex_it_outsourcing.docx, complex_procurement_framework.pdf
        """
        try:
            path = ctx.get_sample_path(filename)
            return await upload_contract(str(path))
        except ValueError as exc:
            return {"error": str(exc)}

    # ── 3. ask_question ──────────────────────────────────────

    @mcp.tool()
    async def ask_question(
        question: str,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ask a natural-language question about uploaded contracts.

        Returns a grounded answer with provenance and confidence.
        """
        contracts = ctx.state.trust_graph.list_contracts()
        if not contracts:
            return {"error": "No contracts indexed. Upload a contract first."}

        if document_ids:
            for did in document_ids:
                try:
                    ctx.get_contract_or_error(did)
                except ValueError as exc:
                    return {"error": str(exc)}

        import uuid
        from datetime import datetime

        from contractos.agents.document_agent import DocumentAgent
        from contractos.models.query import Query, QueryScope

        doc_ids = document_ids or [c.document_id for c in contracts]
        scope = QueryScope.SINGLE_DOCUMENT if len(doc_ids) == 1 else QueryScope.REPOSITORY
        query = Query(
            query_id=f"q-{uuid.uuid4().hex[:8]}",
            text=question,
            scope=scope,
            target_document_ids=doc_ids,
            submitted_at=datetime.now(),
        )
        agent = DocumentAgent(ctx.state.trust_graph, ctx.state.llm, ctx.state.embedding_index)
        result = await agent.answer(query)

        from contractos.tools.confidence import confidence_label

        conf = confidence_label(result.confidence)
        provenance_items = []
        if result.provenance and result.provenance.nodes:
            for node in result.provenance.nodes:
                provenance_items.append({
                    "node_type": node.node_type,
                    "summary": node.summary[:200],
                    "reference_id": node.reference_id,
                    "location": node.document_location or "",
                })
        return {
            "answer": result.answer,
            "confidence": result.confidence,
            "confidence_label": conf.label,
            "sources": doc_ids,
            "provenance": provenance_items,
        }

    # ── 4. review_against_playbook ───────────────────────────

    @mcp.tool()
    async def review_against_playbook(
        document_id: str,
        playbook_path: str | None = None,
    ) -> dict[str, Any]:
        """Run playbook compliance review on a contract.

        Returns findings (GREEN/YELLOW/RED) with redline suggestions,
        risk profile, and negotiation strategy.
        """
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        from contractos.agents.compliance_agent import ComplianceAgent
        from contractos.tools.playbook_loader import load_default_playbook, load_playbook

        playbook = load_playbook(playbook_path) if playbook_path else load_default_playbook()
        agent = ComplianceAgent(
            trust_graph=ctx.state.trust_graph,
            llm=ctx.state.llm,
        )
        result = await agent.review(document_id, playbook, generate_redlines=True)

        findings = []
        for f in result.findings:
            finding: dict[str, Any] = {
                "clause_type": f.clause_type,
                "severity": f.severity.value,
                "deviation": f.deviation_description,
                "business_impact": f.business_impact,
            }
            if f.redline:
                finding["redline"] = {
                    "proposed_language": f.redline.proposed_language,
                    "rationale": f.redline.rationale,
                    "fallback": f.redline.fallback_language or "",
                }
            findings.append(finding)

        risk_data: dict[str, Any] = {}
        if result.risk_profile:
            risk_data = {
                "overall_level": result.risk_profile.overall_level.value,
                "overall_score": result.risk_profile.overall_score,
                "highest_risk_finding": result.risk_profile.highest_risk_finding,
                "risk_distribution": result.risk_profile.risk_distribution,
            }

        return {
            "findings": findings,
            "risk_profile": risk_data,
            "negotiation_strategy": result.negotiation_strategy,
            "total_findings": len(result.findings),
            "green_count": result.green_count,
            "yellow_count": result.yellow_count,
            "red_count": result.red_count,
            "missing_clauses": result.missing_clauses,
        }

    # ── 5. triage_nda ────────────────────────────────────────

    @mcp.tool()
    async def triage_nda(document_id: str) -> dict[str, Any]:
        """Run NDA triage screening (10-point checklist).

        Returns checklist results with PASS/FAIL/PARTIAL per item
        and overall GREEN/YELLOW/RED classification.
        """
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        from contractos.agents.nda_triage_agent import NDATriageAgent

        agent = NDATriageAgent(
            trust_graph=ctx.state.trust_graph,
            llm=ctx.state.llm,
        )
        result = await agent.triage(document_id)

        return {
            "checklist": [
                {
                    "item": item.name,
                    "status": item.status.value,
                    "finding": item.finding,
                    "evidence": item.evidence,
                }
                for item in result.checklist_results
            ],
            "classification": result.classification.level.value,
            "routing": result.classification.routing,
            "summary": result.summary,
            "pass_count": result.pass_count,
            "fail_count": result.fail_count,
            "review_count": result.review_count,
            "key_issues": result.key_issues,
        }

    # ── 6. discover_hidden_facts ─────────────────────────────

    @mcp.tool()
    async def discover_hidden_facts(document_id: str) -> dict[str, Any]:
        """LLM-powered discovery of implicit obligations, risks, and hidden facts."""
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        text = ctx.get_document_text(document_id)
        facts = ctx.state.trust_graph.get_facts_by_document(document_id)
        clauses = ctx.state.trust_graph.get_clauses_by_document(document_id)
        bindings = ctx.state.trust_graph.get_bindings_by_document(document_id)

        facts_summary = "; ".join(f"{f.fact_type}: {f.value}" for f in facts[:30])
        clauses_summary = "; ".join(f"{c.clause_type}: {c.heading}" for c in clauses[:20])
        bindings_summary = "; ".join(f"{b.term} → {b.resolves_to}" for b in bindings[:20])

        from contractos.tools.fact_discovery import discover_hidden_facts as _discover

        result = await _discover(text, facts_summary, clauses_summary, bindings_summary, ctx.state.llm)

        return {
            "discovered_facts": [
                {
                    "claim": df.claim,
                    "fact_type": df.type,
                    "risk_level": df.risk_level,
                    "evidence": df.evidence,
                    "explanation": df.explanation,
                }
                for df in result.discovered_facts
            ],
            "summary": result.summary,
            "categories_found": result.categories_found,
            "count": len(result.discovered_facts),
        }

    # ── 7. extract_obligations ───────────────────────────────

    @mcp.tool()
    async def extract_obligations(document_id: str) -> dict[str, Any]:
        """Extract and categorise all contractual obligations.

        Returns obligations grouped by type (affirmative, negative, conditional).
        """
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        text = ctx.get_document_text(document_id)

        from contractos.api.routes.stream import OBLIGATION_SYSTEM_PROMPT
        from contractos.llm.provider import LLMMessage
        from contractos.tools.fact_discovery import _parse_lenient_json

        resp = await ctx.state.llm.complete(
            messages=[LLMMessage(role="user", content=f"Contract text:\n\n{text[:30000]}")],
            system=OBLIGATION_SYSTEM_PROMPT,
            max_tokens=16384,
        )
        parsed = _parse_lenient_json(resp.content)

        obligations = parsed.get("obligations", [])
        return {
            "obligations": obligations,
            "summary": parsed.get("summary", ""),
            "total_affirmative": parsed.get("total_affirmative", 0),
            "total_negative": parsed.get("total_negative", 0),
            "total_conditional": parsed.get("total_conditional", 0),
            "count": len(obligations),
        }

    # ── 8. generate_risk_memo ────────────────────────────────

    @mcp.tool()
    async def generate_risk_memo(document_id: str) -> dict[str, Any]:
        """Generate a structured risk assessment memo.

        Returns executive summary, key risks, missing protections,
        recommendations, and escalation items.
        """
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        text = ctx.get_document_text(document_id)

        from contractos.api.routes.stream import RISK_MEMO_PROMPT
        from contractos.llm.provider import LLMMessage
        from contractos.tools.fact_discovery import _parse_lenient_json

        resp = await ctx.state.llm.complete(
            messages=[LLMMessage(role="user", content=f"Contract text:\n\n{text[:30000]}")],
            system=RISK_MEMO_PROMPT,
            max_tokens=16384,
        )
        parsed = _parse_lenient_json(resp.content)

        return {
            "executive_summary": parsed.get("executive_summary", ""),
            "overall_risk_rating": parsed.get("overall_risk_rating", ""),
            "key_risks": parsed.get("key_risks", []),
            "missing_protections": parsed.get("missing_protections", []),
            "recommendations": parsed.get("recommendations", []),
            "escalation_items": parsed.get("escalation_items", []),
        }

    # ── 9. get_clause_gaps ───────────────────────────────────

    @mcp.tool()
    async def get_clause_gaps(document_id: str) -> dict[str, Any]:
        """Identify mandatory fact gaps per clause type."""
        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        tg = ctx.state.trust_graph
        missing = tg.get_missing_slots_by_document(document_id)
        clauses = tg.get_clauses_by_document(document_id)

        gaps_by_clause: dict[str, dict[str, Any]] = {}
        for slot in missing:
            key = slot.clause_id
            if key not in gaps_by_clause:
                clause = next((c for c in clauses if c.clause_id == slot.clause_id), None)
                gaps_by_clause[key] = {
                    "clause_type": slot.clause_type if hasattr(slot, "clause_type") else "",
                    "clause_heading": clause.heading if clause else "",
                    "missing_facts": [],
                    "present_facts": [],
                }
            if slot.status.value == "missing" if hasattr(slot.status, "value") else str(slot.status) == "missing":
                gaps_by_clause[key]["missing_facts"].append(slot.fact_spec_name if hasattr(slot, "fact_spec_name") else str(slot))
            else:
                gaps_by_clause[key]["present_facts"].append(slot.fact_spec_name if hasattr(slot, "fact_spec_name") else str(slot))

        gaps = list(gaps_by_clause.values())
        return {
            "gaps": gaps,
            "total_gaps": sum(len(g["missing_facts"]) for g in gaps),
            "total_clauses": len(clauses),
        }

    # ── 10. search_contracts ─────────────────────────────────

    @mcp.tool()
    async def search_contracts(query: str, top_k: int = 5) -> dict[str, Any]:
        """Semantic search across all indexed contracts."""
        contracts = ctx.state.trust_graph.list_contracts()
        if not contracts:
            return {"error": "No contracts indexed. Upload a contract first."}

        all_results = []
        for c in contracts:
            doc_id = c.document_id
            if ctx.state.embedding_index.has_document(doc_id):
                hits = ctx.state.embedding_index.search(doc_id, query, top_k=top_k)
                for hit in hits:
                    all_results.append({
                        "document_id": doc_id,
                        "chunk_text": hit.chunk.text[:500],
                        "score": round(hit.score, 4),
                        "chunk_type": hit.chunk.chunk_type,
                    })

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return {
            "query": query,
            "results": all_results[:top_k],
            "total_documents_searched": len(contracts),
        }

    # ── 11. compare_clauses ──────────────────────────────────

    CLAUSE_COMPARISON_PROMPT = """You are ContractOS Clause Comparator. Compare the same clause type across two contracts.

Output STRICT JSON:
{
  "differences": [
    {"aspect": "...", "contract_1": "...", "contract_2": "...", "significance": "minor|moderate|major"}
  ],
  "summary": "...",
  "recommendation": "..."
}
Keep each field under 80 words. Return at most 8 differences."""

    @mcp.tool()
    async def compare_clauses(
        document_id_1: str,
        document_id_2: str,
        clause_type: str,
    ) -> dict[str, Any]:
        """Compare specific clause types across two contracts.

        Returns differences with significance ratings and a recommendation.
        """
        for did in [document_id_1, document_id_2]:
            try:
                ctx.get_contract_or_error(did)
            except ValueError as exc:
                return {"error": str(exc)}

        tg = ctx.state.trust_graph
        clauses_1 = [c for c in tg.get_clauses_by_document(document_id_1) if clause_type.lower() in (c.clause_type or "").lower()]
        clauses_2 = [c for c in tg.get_clauses_by_document(document_id_2) if clause_type.lower() in (c.clause_type or "").lower()]

        if not clauses_1:
            return {"error": f"Clause type '{clause_type}' not found in document {document_id_1}"}
        if not clauses_2:
            return {"error": f"Clause type '{clause_type}' not found in document {document_id_2}"}

        text_1 = "\n".join(c.text for c in clauses_1 if c.text)
        text_2 = "\n".join(c.text for c in clauses_2 if c.text)

        from contractos.llm.provider import LLMMessage
        from contractos.tools.fact_discovery import _parse_lenient_json

        resp = await ctx.state.llm.complete(
            messages=[LLMMessage(
                role="user",
                content=f"Contract 1 ({clause_type}):\n{text_1[:8000]}\n\nContract 2 ({clause_type}):\n{text_2[:8000]}",
            )],
            system=CLAUSE_COMPARISON_PROMPT,
            max_tokens=4096,
        )
        parsed = _parse_lenient_json(resp.content)

        return {
            "clause_type": clause_type,
            "contract_1_id": document_id_1,
            "contract_2_id": document_id_2,
            "differences": parsed.get("differences", []),
            "summary": parsed.get("summary", ""),
            "recommendation": parsed.get("recommendation", ""),
        }

    # ── 12. generate_report ──────────────────────────────────

    @mcp.tool()
    async def generate_report(
        document_id: str,
        report_type: str,
    ) -> dict[str, Any]:
        """Generate an HTML report for a completed analysis.

        report_type must be one of: review, triage, discovery
        """
        if report_type not in ("review", "triage", "discovery"):
            return {"error": f"Invalid report_type: {report_type}. Use: review, triage, discovery"}

        try:
            ctx.get_contract_or_error(document_id)
        except ValueError as exc:
            return {"error": str(exc)}

        from contractos.api.routes.stream import _report_template

        import datetime

        html = _report_template(
            title=f"ContractOS {report_type.title()} Report",
            subtitle=f"Document: {document_id}",
            summary=f"Generated {report_type} analysis report.",
            body=f"<p>Run the {report_type} analysis tool first to populate detailed results.</p>",
            elapsed_ms=0,
        )

        return {
            "html_content": html,
            "report_type": report_type,
            "document_id": document_id,
            "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }

    # ── 13. clear_workspace ──────────────────────────────────

    @mcp.tool()
    async def clear_workspace() -> dict[str, Any]:
        """Clear all uploaded contracts, facts, and analysis data."""
        tg = ctx.state.trust_graph
        contracts = tg.list_contracts()
        count = len(contracts)

        tg.clear_all_data()

        for c in contracts:
            doc_id = c.document_id
            if ctx.state.embedding_index.has_document(doc_id):
                ctx.state.embedding_index.remove_document(doc_id)

        return {
            "message": "Workspace cleared. All contracts and analysis data removed.",
            "contracts_removed": count,
        }
