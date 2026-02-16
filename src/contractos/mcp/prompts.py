"""MCP prompt definitions for ContractOS.

Prompts are reusable workflow templates that guide AI assistants
through multi-step contract analysis processes.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

from contractos.mcp.context import MCPContext

logger = logging.getLogger("contractos.mcp.prompts")


def register_prompts(mcp: FastMCP, ctx: MCPContext) -> None:
    """Register all 5 ContractOS MCP prompts."""

    @mcp.prompt()
    def full_contract_analysis(document_id: str) -> list[base.Message]:
        """Run a complete contract analysis pipeline.

        Guides the AI through: triage → review → obligations → risk memo → discover.
        """
        return [
            base.UserMessage(
                f"""Run a complete analysis on document {document_id}. Follow these steps in order:

1. **NDA Triage** — Call triage_nda(document_id="{document_id}") to screen the contract
2. **Playbook Review** — Call review_against_playbook(document_id="{document_id}") for compliance findings
3. **Obligation Extraction** — Call extract_obligations(document_id="{document_id}") to identify all duties
4. **Risk Memo** — Call generate_risk_memo(document_id="{document_id}") for risk assessment
5. **Hidden Facts** — Call discover_hidden_facts(document_id="{document_id}") for implicit risks

After all steps complete, synthesise the results into a comprehensive executive summary covering:
- Overall risk rating and classification
- Top 5 critical findings requiring immediate attention
- Key obligations by party
- Recommended next steps for the legal/procurement team"""
            ),
        ]

    @mcp.prompt()
    def due_diligence_checklist(document_id: str) -> list[base.Message]:
        """Structured due diligence review checklist.

        Covers parties, term, termination, liability, IP, confidentiality, compliance.
        """
        return [
            base.UserMessage(
                f"""Perform a due diligence review on document {document_id}. Check each area:

**Parties & Authority**
- Ask: "Who are the parties and what are their roles?" (use ask_question)
- Ask: "Is there a proper authority/signatory clause?"

**Term & Termination**
- Ask: "What is the contract term and renewal mechanism?"
- Ask: "What are the termination provisions and notice periods?"

**Liability & Indemnification**
- Call review_against_playbook for liability/indemnification findings
- Ask: "Are there any liability caps or exclusions?"

**Intellectual Property**
- Ask: "How is IP ownership and licensing handled?"
- Ask: "Are there any IP assignment clauses?"

**Confidentiality**
- Call triage_nda for NDA-specific checks
- Ask: "What are the confidentiality obligations and carve-outs?"

**Compliance & Governing Law**
- Ask: "What is the governing law and dispute resolution mechanism?"
- Ask: "Are there any regulatory compliance requirements?"

**Obligations**
- Call extract_obligations to identify all contractual duties

Compile findings into a structured due diligence report with RAG (Red/Amber/Green) ratings per area."""
            ),
        ]

    @mcp.prompt()
    def negotiation_prep(document_id: str) -> list[base.Message]:
        """Prepare negotiation strategy from playbook review findings."""
        return [
            base.UserMessage(
                f"""Prepare a negotiation strategy for document {document_id}:

1. Call review_against_playbook(document_id="{document_id}") to get compliance findings
2. Read the playbook resource at contractos://playbook to understand our standard positions
3. Call extract_obligations(document_id="{document_id}") to understand what we're committing to

Based on the results, prepare:

**Negotiation Brief**
- List all YELLOW and RED findings as negotiation points
- For each, state: our preferred position, fallback position, and walk-away threshold
- Prioritise by business impact (highest impact first)

**Redline Strategy**
- Include specific redline language suggestions from the review
- Group by negotiation tier (must-have vs nice-to-have vs concession)

**Talking Points**
- 3-5 key talking points for the negotiation meeting
- Anticipated counterarguments and our responses"""
            ),
        ]

    @mcp.prompt()
    def risk_summary(document_id: str) -> list[base.Message]:
        """Executive risk summary combining all analysis outputs."""
        return [
            base.UserMessage(
                f"""Generate an executive risk briefing for document {document_id}:

1. Call generate_risk_memo(document_id="{document_id}") for the risk assessment
2. Call extract_obligations(document_id="{document_id}") for obligation analysis
3. Call discover_hidden_facts(document_id="{document_id}") for hidden risks

Synthesise into a 1-page executive briefing:

**Risk Dashboard** — Overall rating, number of high/medium/low risks
**Top 3 Risks** — Description, impact, likelihood, mitigation
**Missing Protections** — What standard clauses are absent
**Hidden Concerns** — Implicit obligations or risks discovered
**Recommendation** — Proceed / Proceed with caution / Do not proceed"""
            ),
        ]

    @mcp.prompt()
    def clause_comparison(
        doc_id_1: str,
        doc_id_2: str,
        clause_type: str,
    ) -> list[base.Message]:
        """Compare clause language across two contracts."""
        return [
            base.UserMessage(
                f"""Compare the {clause_type} clauses between two contracts:

1. Call compare_clauses(document_id_1="{doc_id_1}", document_id_2="{doc_id_2}", clause_type="{clause_type}")
2. Read the clauses from both contracts:
   - contractos://contracts/{doc_id_1}/clauses
   - contractos://contracts/{doc_id_2}/clauses

Produce a structured comparison:

**Side-by-Side Analysis**
- Key differences with significance ratings (minor/moderate/major)
- Which contract is more favourable for us and why

**Risk Implications**
- What risks does each version expose us to?

**Recommendation**
- Which language should we adopt and why
- Specific redline suggestions if neither is ideal"""
            ),
        ]
