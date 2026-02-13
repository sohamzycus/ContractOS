"""Server-Sent Events (SSE) streaming endpoints for progressive reasoning.

Each long-running operation (review, triage, discover) gets a streaming
counterpart that sends real-time progress events as the analysis proceeds.

Event types:
  step     — A reasoning step started/completed (with intermediate results)
  result   — The final result payload
  error    — An error occurred
  done     — Stream complete
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Annotated, Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from contractos.api.deps import AppState, get_state

router = APIRouter(prefix="/stream", tags=["stream"])
logger = logging.getLogger(__name__)


def _sse_event(event: str, data: dict[str, Any]) -> str:
    """Format a Server-Sent Event."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


# ── Review Stream ──────────────────────────────────────────────────


@router.get("/{document_id}/review")
async def stream_review(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
    user_side: str = "buyer",
) -> StreamingResponse:
    """Stream a playbook review with progressive reasoning steps."""
    from contractos.agents.compliance_agent import ComplianceAgent
    from contractos.agents.draft_agent import DraftAgent
    from contractos.tools.playbook_loader import load_default_playbook

    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    playbook = load_default_playbook()

    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.monotonic()

        # Step 1: Loading playbook
        yield _sse_event("step", {
            "step": "load_playbook",
            "status": "running",
            "label": "Loading playbook positions",
            "detail": f"{len(playbook.positions)} positions in '{playbook.name}'",
        })

        agent = ComplianceAgent(state.trust_graph, state.llm)
        clauses = state.trust_graph.get_clauses_by_document(document_id)
        facts = state.trust_graph.get_facts_by_document(document_id)
        fact_lookup = {f.fact_id: f for f in facts}

        clause_by_type: dict[str, list] = {}
        for clause in clauses:
            ct = clause.clause_type.value
            clause_by_type.setdefault(ct, []).append(clause)

        yield _sse_event("step", {
            "step": "load_playbook",
            "status": "done",
            "label": "Playbook loaded",
            "detail": f"{len(clauses)} clauses, {len(facts)} facts loaded",
        })

        # Step 2: Classify each clause
        from contractos.models.review import ReviewFinding, ReviewSeverity
        findings: list[ReviewFinding] = []
        total_positions = len(playbook.positions)
        reviewed = 0

        yield _sse_event("step", {
            "step": "classify_clauses",
            "status": "running",
            "label": "Comparing clauses against playbook",
            "detail": f"0/{total_positions} positions evaluated",
        })

        # Process positions — batch concurrent LLM calls for speed
        batch_size = 4
        position_items = list(playbook.positions.items())

        for batch_start in range(0, len(position_items), batch_size):
            batch = position_items[batch_start:batch_start + batch_size]
            tasks = []

            for pos_key, position in batch:
                ct = position.clause_type
                matching_clauses = clause_by_type.get(ct, [])

                if not matching_clauses:
                    if position.required:
                        findings.append(agent._missing_clause_finding(position))
                    reviewed += 1
                    continue

                for clause in matching_clauses:
                    tasks.append(agent._review_clause(clause, position, fact_lookup, user_side))
                reviewed += 1

            if tasks:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in batch_results:
                    if isinstance(r, Exception):
                        logger.error("Clause review failed: %s", r)
                    else:
                        findings.append(r)

            # Send progress update with intermediate results
            green = sum(1 for f in findings if f.severity == ReviewSeverity.GREEN)
            yellow = sum(1 for f in findings if f.severity == ReviewSeverity.YELLOW)
            red = sum(1 for f in findings if f.severity == ReviewSeverity.RED)

            yield _sse_event("step", {
                "step": "classify_clauses",
                "status": "running" if reviewed < total_positions else "done",
                "label": f"Classifying deviations ({reviewed}/{total_positions})",
                "detail": f"{green} GREEN, {yellow} YELLOW, {red} RED so far",
                "progress": {"reviewed": reviewed, "total": total_positions,
                             "green": green, "yellow": yellow, "red": red},
            })

        # Step 3: Risk profile
        yield _sse_event("step", {
            "step": "risk_profile",
            "status": "running",
            "label": "Computing risk profile",
            "detail": "Severity × Likelihood risk matrix",
        })

        risk_profile = agent._build_risk_profile(findings)

        yield _sse_event("step", {
            "step": "risk_profile",
            "status": "done",
            "label": "Risk profile computed",
            "detail": f"Overall: {risk_profile.overall_level.value.upper()} (score: {risk_profile.overall_score})",
            "data": {
                "overall_level": risk_profile.overall_level.value,
                "overall_score": risk_profile.overall_score,
                "risk_distribution": risk_profile.risk_distribution,
                "tier_1_issues": risk_profile.tier_1_issues,
                "tier_2_issues": risk_profile.tier_2_issues,
            },
        })

        # Step 4: Generate redlines for YELLOW/RED findings (parallel)
        yellow_red = [f for f in findings if f.severity in (ReviewSeverity.YELLOW, ReviewSeverity.RED)]
        if yellow_red:
            yield _sse_event("step", {
                "step": "generate_redlines",
                "status": "running",
                "label": "Generating redline suggestions",
                "detail": f"{len(yellow_red)} clauses need alternative language",
            })

            draft_agent = DraftAgent(state.llm)
            redline_tasks = []
            finding_position_pairs = []

            for f in yellow_red:
                pos = playbook.positions.get(f.clause_type)
                if pos:
                    redline_tasks.append(draft_agent.generate_redline(f, pos, user_side))
                    finding_position_pairs.append(f)

            if redline_tasks:
                redline_results = await asyncio.gather(*redline_tasks, return_exceptions=True)
                for finding, redline in zip(finding_position_pairs, redline_results):
                    if not isinstance(redline, Exception) and redline is not None:
                        finding.redline = redline

            yield _sse_event("step", {
                "step": "generate_redlines",
                "status": "done",
                "label": "Redlines generated",
                "detail": f"{sum(1 for f in yellow_red if f.redline)} suggestions produced",
            })

        # Step 5: Negotiation strategy
        yield _sse_event("step", {
            "step": "negotiation_strategy",
            "status": "running",
            "label": "Building negotiation strategy",
            "detail": "Generating tier-based approach",
        })

        strategy = await agent._generate_strategy(findings, playbook)

        yield _sse_event("step", {
            "step": "negotiation_strategy",
            "status": "done",
            "label": "Strategy complete",
            "detail": strategy[:100] + "..." if len(strategy) > 100 else strategy,
        })

        # Final result
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        green_count = sum(1 for f in findings if f.severity == ReviewSeverity.GREEN)
        yellow_count = sum(1 for f in findings if f.severity == ReviewSeverity.YELLOW)
        red_count = sum(1 for f in findings if f.severity == ReviewSeverity.RED)
        missing = [
            f.clause_type for f in findings
            if "missing" in f.deviation_description.lower() and f.severity == ReviewSeverity.RED
        ]

        findings_data = []
        for f in findings:
            risk_dict = None
            if f.risk_score:
                risk_dict = {
                    "severity": f.risk_score.severity,
                    "likelihood": f.risk_score.likelihood,
                    "score": f.risk_score.score,
                    "level": f.risk_score.level.value,
                }
            redline_dict = None
            if f.redline:
                redline_dict = {
                    "proposed_language": f.redline.proposed_language,
                    "rationale": f.redline.rationale,
                    "priority": f.redline.priority.value,
                    "fallback_language": f.redline.fallback_language,
                }
            findings_data.append({
                "finding_id": f.finding_id,
                "clause_id": f.clause_id,
                "clause_type": f.clause_type,
                "clause_heading": f.clause_heading,
                "severity": f.severity.value,
                "current_language": f.current_language,
                "playbook_position": f.playbook_position,
                "deviation_description": f.deviation_description,
                "business_impact": f.business_impact,
                "risk_score": risk_dict,
                "redline": redline_dict,
                "provenance_facts": f.provenance_facts,
                "char_start": f.char_start,
                "char_end": f.char_end,
            })

        rp = risk_profile
        result = {
            "document_id": document_id,
            "playbook_name": playbook.name,
            "findings": findings_data,
            "summary": agent._build_summary(findings, playbook.name),
            "risk_profile": {
                "overall_level": rp.overall_level.value,
                "overall_score": rp.overall_score,
                "highest_risk_finding": rp.highest_risk_finding,
                "risk_distribution": rp.risk_distribution,
                "tier_1_issues": rp.tier_1_issues,
                "tier_2_issues": rp.tier_2_issues,
                "tier_3_issues": rp.tier_3_issues,
            },
            "negotiation_strategy": strategy,
            "review_time_ms": elapsed_ms,
            "green_count": green_count,
            "yellow_count": yellow_count,
            "red_count": red_count,
            "missing_clauses": missing,
        }

        yield _sse_event("result", result)
        yield _sse_event("done", {"elapsed_ms": elapsed_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Triage Stream ──────────────────────────────────────────────────


@router.get("/{document_id}/triage")
async def stream_triage(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> StreamingResponse:
    """Stream NDA triage with per-checklist-item progress."""
    from contractos.agents.nda_triage_agent import DEFAULT_CHECKLIST, NDATriageAgent

    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.monotonic()

        agent = NDATriageAgent(state.trust_graph, state.llm)
        items = DEFAULT_CHECKLIST
        facts = state.trust_graph.get_facts_by_document(document_id)
        clauses = state.trust_graph.get_clauses_by_document(document_id)

        facts_text = "\n".join(
            f"- [{f.fact_id}] ({f.evidence.location_hint}): {f.value[:200]}"
            for f in facts[:50]
        )
        clauses_text = "\n".join(
            f"- [{c.clause_id}] {c.clause_type.value}: {c.heading}"
            for c in clauses
        )

        yield _sse_event("step", {
            "step": "load_checklist",
            "status": "done",
            "label": "NDA checklist loaded",
            "detail": f"{len(items)} screening items, {len(facts)} facts, {len(clauses)} clauses",
        })

        # Evaluate each item — stream results as they complete
        from contractos.models.triage import ChecklistStatus
        results = []
        total = len(items)

        # Run items in parallel batches of 3 for speed
        batch_size = 3
        for batch_start in range(0, total, batch_size):
            batch_items = items[batch_start:batch_start + batch_size]

            # Show which items are being evaluated
            names = ", ".join(it.name for it in batch_items)
            yield _sse_event("step", {
                "step": "evaluate",
                "status": "running",
                "label": f"Evaluating ({batch_start + 1}-{min(batch_start + batch_size, total)}/{total})",
                "detail": names,
            })

            tasks = [
                agent._evaluate_item(item, facts, clauses, facts_text, clauses_text)
                for item in batch_items
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for item, r in zip(batch_items, batch_results):
                if isinstance(r, Exception):
                    logger.error("Triage item %s failed: %s", item.item_id, r)
                    from contractos.models.triage import ChecklistResult
                    r = ChecklistResult(
                        item_id=item.item_id, name=item.name,
                        status=ChecklistStatus.REVIEW,
                        finding=f"Evaluation error: {r}",
                    )
                results.append(r)

                # Stream each completed item
                icon = "✅" if r.status == ChecklistStatus.PASS else "❌" if r.status == ChecklistStatus.FAIL else "🔍"
                yield _sse_event("step", {
                    "step": "item_result",
                    "status": "done",
                    "label": f"{icon} {r.name}: {r.status.value.upper()}",
                    "detail": r.finding[:120] if r.finding else "",
                    "data": {
                        "item_id": r.item_id,
                        "name": r.name,
                        "status": r.status.value,
                        "finding": r.finding,
                        "evidence": r.evidence,
                    },
                })

        # Classification
        yield _sse_event("step", {
            "step": "classify",
            "status": "running",
            "label": "Computing classification",
            "detail": "GREEN / YELLOW / RED routing determination",
        })

        classification = agent._classify(results, items)
        key_issues = [
            f"{r.name}: {r.finding}"
            for r in results
            if r.status in (ChecklistStatus.FAIL, ChecklistStatus.REVIEW)
        ]

        pass_count = sum(1 for r in results if r.status == ChecklistStatus.PASS)
        fail_count = sum(1 for r in results if r.status == ChecklistStatus.FAIL)
        review_count = sum(1 for r in results if r.status == ChecklistStatus.REVIEW)

        yield _sse_event("step", {
            "step": "classify",
            "status": "done",
            "label": f"Classification: {classification.level.value.upper()}",
            "detail": f"{pass_count} pass, {fail_count} fail, {review_count} review — {classification.routing}",
        })

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        result = {
            "document_id": document_id,
            "classification": {
                "level": classification.level.value,
                "routing": classification.routing,
                "timeline": classification.timeline,
                "rationale": classification.rationale,
            },
            "checklist_results": [
                {
                    "item_id": cr.item_id,
                    "name": cr.name,
                    "status": cr.status.value,
                    "finding": cr.finding,
                    "evidence": cr.evidence,
                    "fact_ids": cr.fact_ids,
                }
                for cr in results
            ],
            "key_issues": key_issues,
            "summary": agent._build_summary(results, classification),
            "triage_time_ms": elapsed_ms,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "review_count": review_count,
        }

        yield _sse_event("result", result)
        yield _sse_event("done", {"elapsed_ms": elapsed_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Discover Stream ────────────────────────────────────────────────


@router.get("/{document_id}/discover")
async def stream_discover(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> StreamingResponse:
    """Stream hidden fact discovery with progressive steps."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.monotonic()

        # Step 1: Gather context
        yield _sse_event("step", {
            "step": "gather_context",
            "status": "running",
            "label": "Gathering extraction context",
            "detail": "Loading facts, clauses, and bindings",
        })

        facts = state.trust_graph.get_facts_by_document(document_id)
        clauses = state.trust_graph.get_clauses_by_document(document_id)
        bindings = state.trust_graph.get_bindings_by_document(document_id)

        yield _sse_event("step", {
            "step": "gather_context",
            "status": "done",
            "label": "Context loaded",
            "detail": f"{len(facts)} facts, {len(clauses)} clauses, {len(bindings)} bindings",
        })

        # Step 2: Build summaries
        yield _sse_event("step", {
            "step": "build_prompt",
            "status": "running",
            "label": "Building discovery prompt",
            "detail": "Summarizing existing extractions for LLM",
        })

        facts_summary = "\n".join(
            f"- [{f.fact_id}] ({f.fact_type.value if hasattr(f.fact_type, 'value') else f.fact_type}) "
            f'"{f.value[:100]}" @ {f.evidence.location_hint}'
            for f in facts[:60]
        ) or "(No facts extracted)"

        clauses_summary = "\n".join(
            f"- [{c.clause_id}] {c.clause_type.value if hasattr(c.clause_type, 'value') else c.clause_type}: {c.heading}"
            for c in clauses
        ) or "(No clauses classified)"

        bindings_summary = "\n".join(
            f'- "{b.term}" -> "{b.resolves_to}" ({b.binding_type.value if hasattr(b.binding_type, "value") else b.binding_type})'
            for b in bindings
        ) or "(No bindings resolved)"

        text_parts = []
        for f in facts:
            ft = f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)
            if ft == "clause_text" and f.value:
                text_parts.append(f.value)
        contract_text = "\n\n".join(text_parts) if text_parts else facts_summary

        yield _sse_event("step", {
            "step": "build_prompt",
            "status": "done",
            "label": "Prompt ready",
            "detail": f"{len(contract_text)} chars of contract text prepared",
        })

        # Step 3: LLM analysis
        yield _sse_event("step", {
            "step": "llm_analysis",
            "status": "running",
            "label": "LLM deep analysis in progress",
            "detail": "Finding implicit obligations, hidden risks, unstated assumptions...",
        })

        from contractos.tools.fact_discovery import discover_hidden_facts
        result = await discover_hidden_facts(
            contract_text=contract_text,
            existing_facts_summary=facts_summary,
            clauses_summary=clauses_summary,
            bindings_summary=bindings_summary,
            llm=state.llm,
        )

        yield _sse_event("step", {
            "step": "llm_analysis",
            "status": "done",
            "label": f"Discovered {len(result.discovered_facts)} hidden facts",
            "detail": result.categories_found or result.summary[:100],
        })

        # Stream each discovered fact individually
        for i, fact in enumerate(result.discovered_facts):
            yield _sse_event("step", {
                "step": "discovered_fact",
                "status": "done",
                "label": f"[{fact.risk_level.upper()}] {fact.type.replace('_', ' ').title()}",
                "detail": fact.claim[:150],
                "data": fact.to_dict(),
            })

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        from contractos.tools.confidence import confidence_label
        conf = confidence_label(0.75) if result.discovered_facts else confidence_label(0.3)

        final = {
            "discovered_facts": [f.to_dict() for f in result.discovered_facts],
            "summary": result.summary,
            "categories_found": result.categories_found,
            "discovery_time_ms": result.discovery_time_ms,
            "count": len(result.discovered_facts),
            "confidence": {"label": conf.label, "color": conf.color, "score": conf.value} if conf else None,
        }

        yield _sse_event("result", final)
        yield _sse_event("done", {"elapsed_ms": elapsed_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Obligation Extraction ──────────────────────────────────────────


OBLIGATION_SYSTEM_PROMPT = """You are ContractOS Obligation Extractor — an expert at identifying contractual obligations.

Analyze the contract and extract the TOP 15 most important obligations, duties, and commitments.

For each obligation, provide:
- party: Which party bears this obligation (keep short, e.g. "Client" or "Vendor")
- type: "affirmative" (must do), "negative" (must not do), "conditional" (if X then must Y)
- description: What the obligation requires (max 80 words)
- trigger: What triggers this obligation (if conditional, else empty string)
- deadline: Any time constraint (or empty string)
- clause_reference: Which section/clause (e.g. "Section 3.2")
- risk_if_breached: Consequence of non-compliance (max 30 words)

IMPORTANT: Keep each field concise. Return at most 15 obligations. Put the summary BEFORE the obligations array.

Respond in JSON:
{
  "summary": "Brief overview (1-2 sentences)",
  "total_affirmative": 0,
  "total_negative": 0,
  "total_conditional": 0,
  "obligations": [...]
}"""


@router.get("/{document_id}/obligations")
async def stream_obligations(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> StreamingResponse:
    """Extract and stream all contractual obligations."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.monotonic()

        yield _sse_event("step", {
            "step": "gather", "status": "running",
            "label": "Loading contract data",
            "detail": "Gathering facts, clauses, and bindings",
        })

        facts = state.trust_graph.get_facts_by_document(document_id)
        clauses = state.trust_graph.get_clauses_by_document(document_id)

        text_parts = [f.value for f in facts
                      if (f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)) == "clause_text"]
        contract_text = "\n\n".join(text_parts)[:8000] if text_parts else "\n".join(f.value[:200] for f in facts[:50])

        yield _sse_event("step", {
            "step": "gather", "status": "done",
            "label": "Contract loaded",
            "detail": f"{len(facts)} facts, {len(clauses)} clauses",
        })

        yield _sse_event("step", {
            "step": "extract", "status": "running",
            "label": "Extracting obligations",
            "detail": "LLM analyzing each clause for duties and commitments",
        })

        from contractos.llm.provider import LLMMessage
        from contractos.tools.fact_discovery import _parse_lenient_json

        clauses_summary = "\n".join(
            f"- {c.clause_type.value if hasattr(c.clause_type, 'value') else c.clause_type}: {c.heading}"
            for c in clauses
        )

        prompt = f"""## Contract Text
{contract_text}

## Classified Clauses
{clauses_summary}

Extract ALL obligations from this contract. Be thorough — include payment obligations,
delivery timelines, confidentiality duties, reporting requirements, insurance obligations,
indemnification duties, and any conditional obligations."""

        messages = [LLMMessage(role="user", content=prompt)]
        response = await state.llm.complete(
            messages, system=OBLIGATION_SYSTEM_PROMPT, temperature=0.0, max_tokens=16384
        )
        data = _parse_lenient_json(response.content)
        obligations = data.get("obligations", [])
        if not obligations:
            logger.warning("No obligations parsed; raw response length=%d", len(response.content))

        yield _sse_event("step", {
            "step": "extract", "status": "done",
            "label": f"Found {len(obligations)} obligations",
            "detail": data.get("summary", ""),
        })

        # Stream each obligation
        for i, ob in enumerate(obligations):
            ob_type = ob.get("type", "affirmative")
            icon = "📋" if ob_type == "affirmative" else "🚫" if ob_type == "negative" else "⚡"
            yield _sse_event("step", {
                "step": "obligation",
                "status": "done",
                "label": f"{icon} [{ob.get('party', '?')}] {ob_type.title()}",
                "detail": ob.get("description", "")[:150],
                "data": ob,
            })

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        result = {
            "obligations": obligations,
            "summary": data.get("summary", f"Found {len(obligations)} obligations"),
            "total_affirmative": data.get("total_affirmative", sum(1 for o in obligations if o.get("type") == "affirmative")),
            "total_negative": data.get("total_negative", sum(1 for o in obligations if o.get("type") == "negative")),
            "total_conditional": data.get("total_conditional", sum(1 for o in obligations if o.get("type") == "conditional")),
            "elapsed_ms": elapsed_ms,
        }

        yield _sse_event("result", result)
        yield _sse_event("done", {"elapsed_ms": elapsed_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Risk Memo ──────────────────────────────────────────────────────


RISK_MEMO_PROMPT = """You are ContractOS Risk Analyst — generate a structured risk memo.

Analyze the contract and produce a risk memo covering:
1. Executive Summary (2-3 sentences)
2. Key Risks — at most 8, each with severity 1-5, likelihood 1-5, category, mitigation (max 40 words each)
3. Missing Protections — at most 5 bullet points
4. Recommendations — at most 5, prioritized
5. Escalation Items — at most 3

IMPORTANT: Keep every field concise to avoid truncation.

Respond in JSON — put scalar fields FIRST:
{
  "executive_summary": "...",
  "overall_risk_rating": "low|medium|high|critical",
  "missing_protections": ["..."],
  "escalation_items": ["..."],
  "recommendations": [{"priority": "high|medium|low", "action": "...", "owner": "..."}],
  "key_risks": [{"risk": "...", "severity": 1, "likelihood": 1, "category": "...", "mitigation": "..."}]
}"""


@router.get("/{document_id}/risk-memo")
async def stream_risk_memo(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
) -> StreamingResponse:
    """Generate a structured risk memo with progressive steps."""
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    async def generate() -> AsyncGenerator[str, None]:
        start_time = time.monotonic()

        yield _sse_event("step", {
            "step": "gather", "status": "running",
            "label": "Gathering contract intelligence",
            "detail": "Loading facts, clauses, bindings, and cross-references",
        })

        facts = state.trust_graph.get_facts_by_document(document_id)
        clauses = state.trust_graph.get_clauses_by_document(document_id)
        bindings = state.trust_graph.get_bindings_by_document(document_id)

        text_parts = [f.value for f in facts
                      if (f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)) == "clause_text"]
        contract_text = "\n\n".join(text_parts)[:8000] if text_parts else "\n".join(f.value[:200] for f in facts[:50])

        yield _sse_event("step", {
            "step": "gather", "status": "done",
            "label": "Intelligence gathered",
            "detail": f"{len(facts)} facts, {len(clauses)} clauses, {len(bindings)} bindings",
        })

        yield _sse_event("step", {
            "step": "analyze", "status": "running",
            "label": "LLM risk analysis",
            "detail": "Generating comprehensive risk memo",
        })

        from contractos.llm.provider import LLMMessage
        from contractos.tools.fact_discovery import _parse_lenient_json

        clauses_summary = "\n".join(
            f"- {c.clause_type.value if hasattr(c.clause_type, 'value') else c.clause_type}: {c.heading}"
            for c in clauses
        )
        bindings_summary = "\n".join(
            f'- "{b.term}" → "{b.resolves_to}"'
            for b in bindings[:20]
        )

        prompt = f"""## Contract Text
{contract_text}

## Clauses
{clauses_summary}

## Key Definitions
{bindings_summary}

Generate a comprehensive risk memo for this contract. Focus on practical business risks,
missing protections, and actionable recommendations."""

        messages = [LLMMessage(role="user", content=prompt)]
        response = await state.llm.complete(
            messages, system=RISK_MEMO_PROMPT, temperature=0.0, max_tokens=16384
        )
        data = _parse_lenient_json(response.content)

        yield _sse_event("step", {
            "step": "analyze", "status": "done",
            "label": f"Risk memo complete — {data.get('overall_risk_rating', 'N/A').upper()}",
            "detail": data.get("executive_summary", "")[:120],
        })

        # Stream key risks
        for risk in data.get("key_risks", []):
            sev = risk.get("severity", 3)
            emoji = "🚨" if sev >= 4 else "⚠️" if sev >= 3 else "ℹ️"
            yield _sse_event("step", {
                "step": "risk_item", "status": "done",
                "label": f"{emoji} {risk.get('category', 'Risk')}: Severity {sev}/5",
                "detail": risk.get("risk", "")[:120],
                "data": risk,
            })

        # Stream missing protections
        missing = data.get("missing_protections", [])
        if missing:
            yield _sse_event("step", {
                "step": "missing", "status": "done",
                "label": f"🔓 {len(missing)} missing protections",
                "detail": ", ".join(missing[:5]),
            })

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        data["elapsed_ms"] = elapsed_ms

        yield _sse_event("result", data)
        yield _sse_event("done", {"elapsed_ms": elapsed_ms})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Report Download ────────────────────────────────────────────────


@router.get("/{document_id}/report")
async def download_report(
    document_id: str,
    state: Annotated[AppState, Depends(get_state)],
    report_type: str = "review",
) -> StreamingResponse:
    """Generate and download an HTML report for review, triage, or discovery results.

    Query params:
      report_type: "review" | "triage" | "discover"
    """
    contract = state.trust_graph.get_contract(document_id)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Contract {document_id} not found")

    if report_type == "review":
        html = await _generate_review_report(document_id, contract, state)
    elif report_type == "triage":
        html = await _generate_triage_report(document_id, contract, state)
    elif report_type == "discover":
        html = await _generate_discovery_report(document_id, contract, state)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown report_type: {report_type}")

    filename = f"ContractOS_{report_type}_{contract.title[:30]}_{document_id[:8]}.html"

    return StreamingResponse(
        iter([html]),
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/html; charset=utf-8",
        },
    )


async def _generate_review_report(document_id: str, contract: Any, state: AppState) -> str:
    """Generate a full HTML review report."""
    from contractos.agents.compliance_agent import ComplianceAgent
    from contractos.agents.draft_agent import DraftAgent
    from contractos.tools.playbook_loader import load_default_playbook

    playbook = load_default_playbook()
    agent = ComplianceAgent(state.trust_graph, state.llm)
    result = await agent.review(document_id, playbook, generate_redlines=True)

    # Generate redlines for YELLOW/RED
    from contractos.models.review import ReviewSeverity
    draft = DraftAgent(state.llm)
    for f in result.findings:
        if f.severity in (ReviewSeverity.YELLOW, ReviewSeverity.RED) and not f.redline:
            pos = playbook.positions.get(f.clause_type)
            if pos:
                redline = await draft.generate_redline(f, pos, "buyer")
                if redline:
                    f.redline = redline

    findings_html = ""
    for f in result.findings:
        sev = f.severity.value
        color = "#00d2d3" if sev == "green" else "#feca57" if sev == "yellow" else "#ff6b6b"
        redline_section = ""
        if f.redline:
            redline_section = f"""
            <div style="margin-top:8px;padding:8px;background:#1a1d27;border-radius:6px;border-left:3px solid #6c5ce7">
              <div style="font-size:11px;color:#6c5ce7;font-weight:600;margin-bottom:4px">SUGGESTED REDLINE</div>
              <div style="font-size:12px;color:#e4e6f0">{f.redline.proposed_language}</div>
              <div style="font-size:11px;color:#8b8fa3;margin-top:4px">Rationale: {f.redline.rationale}</div>
              {f'<div style="font-size:11px;color:#ff9f43;margin-top:4px">Fallback: {f.redline.fallback_language}</div>' if f.redline.fallback_language else ''}
            </div>"""

        findings_html += f"""
        <div style="padding:12px;margin-bottom:8px;background:#242736;border-radius:8px;border-left:4px solid {color}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="background:{color}20;color:{color};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{sev.upper()}</span>
            <span style="font-weight:600;color:#e4e6f0">{f.clause_heading or f.clause_type}</span>
          </div>
          <div style="font-size:12px;color:#e4e6f0;margin-bottom:4px">{f.deviation_description}</div>
          {f'<div style="font-size:11px;color:#8b8fa3">Impact: {f.business_impact}</div>' if f.business_impact else ''}
          {redline_section}
        </div>"""

    rp = result.risk_profile
    return _report_template(
        title=f"Playbook Review — {contract.title}",
        subtitle=f"Reviewed against: {playbook.name}",
        summary=f"""
        <div style="display:flex;gap:16px;margin-bottom:16px">
          <div style="text-align:center;padding:12px 20px;background:#00d2d320;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#00d2d3">{result.green_count}</div>
            <div style="font-size:11px;color:#8b8fa3">GREEN</div>
          </div>
          <div style="text-align:center;padding:12px 20px;background:#feca5720;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#feca57">{result.yellow_count}</div>
            <div style="font-size:11px;color:#8b8fa3">YELLOW</div>
          </div>
          <div style="text-align:center;padding:12px 20px;background:#ff6b6b20;border-radius:8px">
            <div style="font-size:24px;font-weight:700;color:#ff6b6b">{result.red_count}</div>
            <div style="font-size:11px;color:#8b8fa3">RED</div>
          </div>
        </div>
        <div style="font-size:13px;color:#8b8fa3;margin-bottom:8px">
          Overall Risk: <strong style="color:#e4e6f0">{rp.overall_level.value.upper()}</strong> (score: {rp.overall_score})
          — Tier 1: {rp.tier_1_issues}, Tier 2: {rp.tier_2_issues}
        </div>
        """,
        body=f"""
        <h2 style="color:#e4e6f0;font-size:16px;margin:20px 0 12px">Findings</h2>
        {findings_html}
        <h2 style="color:#e4e6f0;font-size:16px;margin:20px 0 12px">Negotiation Strategy</h2>
        <div style="padding:12px;background:#242736;border-radius:8px;font-size:13px;color:#e4e6f0;white-space:pre-wrap">{result.negotiation_strategy}</div>
        """,
        elapsed_ms=result.review_time_ms,
    )


async def _generate_triage_report(document_id: str, contract: Any, state: AppState) -> str:
    """Generate a full HTML triage report."""
    from contractos.agents.nda_triage_agent import NDATriageAgent

    agent = NDATriageAgent(state.trust_graph, state.llm)
    result = await agent.triage(document_id)

    c = result.classification
    level_color = "#00d2d3" if c.level.value == "green" else "#feca57" if c.level.value == "yellow" else "#ff6b6b"
    icon = "✅" if c.level.value == "green" else "⚠️" if c.level.value == "yellow" else "🚨"

    checklist_html = ""
    for cr in result.checklist_results:
        status_icon = "✅" if cr.status.value == "pass" else "❌" if cr.status.value == "fail" else "🔍"
        status_color = "#00d2d3" if cr.status.value == "pass" else "#ff6b6b" if cr.status.value == "fail" else "#feca57"
        checklist_html += f"""
        <div style="display:flex;align-items:flex-start;gap:10px;padding:10px;border-bottom:1px solid #2d3148">
          <span style="font-size:16px">{status_icon}</span>
          <div style="flex:1">
            <div style="font-weight:600;color:#e4e6f0;font-size:13px">{cr.name}</div>
            <div style="font-size:12px;color:#8b8fa3;margin-top:2px">{cr.finding}</div>
            {f'<div style="font-size:11px;color:#6c5ce7;margin-top:4px">Evidence: {cr.evidence}</div>' if cr.evidence else ''}
          </div>
          <span style="color:{status_color};font-size:11px;font-weight:600">{cr.status.value.upper()}</span>
        </div>"""

    return _report_template(
        title=f"NDA Triage Report — {contract.title}",
        subtitle=f"Routing: {c.routing}",
        summary=f"""
        <div style="text-align:center;margin-bottom:16px">
          <div style="display:inline-block;padding:16px 32px;background:{level_color}20;border:2px solid {level_color};border-radius:12px">
            <span style="font-size:28px">{icon}</span>
            <span style="font-size:24px;font-weight:700;color:{level_color};margin-left:8px">{c.level.value.upper()}</span>
          </div>
          <div style="font-size:12px;color:#8b8fa3;margin-top:8px">Timeline: {c.timeline}</div>
        </div>
        <div style="display:flex;gap:16px;justify-content:center;margin-bottom:12px">
          <span style="color:#00d2d3;font-weight:600">{result.pass_count} Passed</span>
          <span style="color:#ff6b6b;font-weight:600">{result.fail_count} Failed</span>
          <span style="color:#feca57;font-weight:600">{result.review_count} Review</span>
        </div>
        """,
        body=f"""
        <h2 style="color:#e4e6f0;font-size:16px;margin:20px 0 12px">Checklist Results</h2>
        <div style="background:#1a1d27;border-radius:8px;overflow:hidden">{checklist_html}</div>
        {f'<h2 style="color:#e4e6f0;font-size:16px;margin:20px 0 12px">Key Issues</h2><ul style="color:#ff6b6b;font-size:13px">{"".join(f"<li style=margin-bottom:4px>{i}</li>" for i in result.key_issues)}</ul>' if result.key_issues else ''}
        """,
        elapsed_ms=result.triage_time_ms,
    )


async def _generate_discovery_report(document_id: str, contract: Any, state: AppState) -> str:
    """Generate a full HTML discovery report."""
    from contractos.tools.fact_discovery import discover_hidden_facts

    facts = state.trust_graph.get_facts_by_document(document_id)
    clauses = state.trust_graph.get_clauses_by_document(document_id)
    bindings = state.trust_graph.get_bindings_by_document(document_id)

    facts_summary = "\n".join(
        f"- [{f.fact_id}] ({f.fact_type.value if hasattr(f.fact_type, 'value') else f.fact_type}) "
        f'"{f.value[:100]}" @ {f.evidence.location_hint}'
        for f in facts[:60]
    ) or "(No facts)"

    clauses_summary = "\n".join(
        f"- [{c.clause_id}] {c.clause_type.value if hasattr(c.clause_type, 'value') else c.clause_type}: {c.heading}"
        for c in clauses
    ) or "(No clauses)"

    bindings_summary = "\n".join(
        f'- "{b.term}" -> "{b.resolves_to}"'
        for b in bindings
    ) or "(No bindings)"

    text_parts = [f.value for f in facts if (f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type)) == "clause_text" and f.value]
    contract_text = "\n\n".join(text_parts) if text_parts else facts_summary

    result = await discover_hidden_facts(contract_text, facts_summary, clauses_summary, bindings_summary, state.llm)

    facts_html = ""
    for df in result.discovered_facts:
        risk_color = "#ff6b6b" if df.risk_level == "high" else "#feca57" if df.risk_level == "medium" else "#00d2d3"
        facts_html += f"""
        <div style="padding:12px;margin-bottom:8px;background:#242736;border-radius:8px;border-left:4px solid {risk_color}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <span style="background:{risk_color}20;color:{risk_color};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{df.risk_level.upper()}</span>
            <span style="font-weight:600;color:#e4e6f0;font-size:13px">{df.type.replace('_', ' ').title()}</span>
          </div>
          <div style="font-size:13px;color:#e4e6f0;margin-bottom:4px">{df.claim}</div>
          {f'<div style="font-size:12px;color:#8b8fa3;margin-top:4px">Evidence: {df.evidence}</div>' if df.evidence else ''}
          {f'<div style="font-size:11px;color:#6c5ce7;margin-top:4px">{df.explanation}</div>' if df.explanation else ''}
        </div>"""

    return _report_template(
        title=f"Hidden Facts Discovery — {contract.title}",
        subtitle=f"Discovered {len(result.discovered_facts)} hidden facts",
        summary=f"""
        <div style="font-size:14px;color:#e4e6f0;margin-bottom:12px">{result.summary}</div>
        <div style="font-size:12px;color:#8b8fa3">Categories: {result.categories_found or 'N/A'}</div>
        """,
        body=f"""
        <h2 style="color:#e4e6f0;font-size:16px;margin:20px 0 12px">Discovered Facts</h2>
        {facts_html}
        """,
        elapsed_ms=result.discovery_time_ms,
    )


def _report_template(title: str, subtitle: str, summary: str, body: str, elapsed_ms: int) -> str:
    """Shared HTML report template with ContractOS branding."""
    from datetime import datetime
    now = datetime.now().strftime("%B %d, %Y at %H:%M")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — ContractOS</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f1117; color:#e4e6f0; padding:40px; }}
  .report {{ max-width:800px; margin:0 auto; }}
  .header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid #2d3148; }}
  .logo {{ font-size:20px; font-weight:700; color:#6c5ce7; }}
  .meta {{ font-size:11px; color:#8b8fa3; text-align:right; }}
  h1 {{ font-size:22px; margin-bottom:4px; }}
  .subtitle {{ font-size:13px; color:#8b8fa3; margin-bottom:20px; }}
  .summary {{ padding:16px; background:#1a1d27; border-radius:12px; margin-bottom:20px; }}
  .footer {{ margin-top:32px; padding-top:16px; border-top:1px solid #2d3148; font-size:11px; color:#8b8fa3; text-align:center; }}
  @media print {{
    body {{ background:#fff; color:#1a1d27; padding:20px; }}
    .summary {{ background:#f5f5f5; }}
  }}
</style>
</head>
<body>
<div class="report">
  <div class="header">
    <div class="logo">ContractOS</div>
    <div class="meta">Generated: {now}<br>Analysis time: {elapsed_ms/1000:.1f}s</div>
  </div>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
  <div class="summary">{summary}</div>
  {body}
  <div class="footer">Generated by ContractOS — Contract Intelligence Platform</div>
</div>
</body>
</html>"""
