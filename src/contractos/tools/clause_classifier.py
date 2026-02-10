"""Clause classifier — assigns ClauseTypeEnum to document sections."""

from __future__ import annotations

import re
import uuid

from contractos.models.clause import Clause, ClauseTypeEnum
from contractos.tools.parsers import ParsedParagraph

# Heading patterns → clause type mapping
# Order matters: more specific patterns first, broader patterns last
_HEADING_PATTERNS: list[tuple[re.Pattern[str], ClauseTypeEnum]] = [
    (re.compile(r'\btermination\b', re.I), ClauseTypeEnum.TERMINATION),
    (re.compile(r'\bpayment\b|\bfees?\b|\bpricing\b|\bcompensation\b', re.I), ClauseTypeEnum.PAYMENT),
    (re.compile(r'\bconfidential\w*\b|\bnon-disclosure\b|\bnda\b', re.I), ClauseTypeEnum.CONFIDENTIALITY),
    (re.compile(r'\bindemnif\w*\b|\bindemnity\b', re.I), ClauseTypeEnum.INDEMNIFICATION),
    (re.compile(r'\bliabilit\w*\b|\blimitation\b', re.I), ClauseTypeEnum.LIABILITY),
    (re.compile(r'\bwarrant\w*\b|\brepresentation\b', re.I), ClauseTypeEnum.WARRANTY),
    (re.compile(r'\bintellectual\s+property\b|\bip\s+rights\b|\bpatent\b|\bcopyright\b', re.I), ClauseTypeEnum.IP_RIGHTS),
    (re.compile(r'\bforce\s+majeure\b', re.I), ClauseTypeEnum.FORCE_MAJEURE),
    (re.compile(r'\bdispute\b|\barbitration\b|\bmediation\b', re.I), ClauseTypeEnum.DISPUTE_RESOLUTION),
    (re.compile(r'\bgoverning\s+law\b|\bjurisdiction\b|\bchoice\s+of\s+law\b', re.I), ClauseTypeEnum.GOVERNING_LAW),
    (re.compile(r'\bnotices?\b|\bnotification\b', re.I), ClauseTypeEnum.NOTICE),
    (re.compile(r'\bassignment\b|\btransfer\b', re.I), ClauseTypeEnum.ASSIGNMENT),
    (re.compile(r'\binsurance\b', re.I), ClauseTypeEnum.INSURANCE),
    (re.compile(r'\bcompliance\b|\bregulat\w*\b', re.I), ClauseTypeEnum.COMPLIANCE),
    (re.compile(r'\bdata\s+protection\b|\bprivacy\b|\bgdpr\b', re.I), ClauseTypeEnum.DATA_PROTECTION),
    (re.compile(r'\bnon-compete\b|\bnon-solicitation\b|\brestrict\w*\b', re.I), ClauseTypeEnum.NON_COMPETE),
    # Broader patterns last to avoid false positives
    (re.compile(r'\bscope\s+of\b|\bdeliverables?\b', re.I), ClauseTypeEnum.SCOPE),
    (re.compile(r'\bdefinition\b', re.I), ClauseTypeEnum.GENERAL),
]

# Section number pattern: "1.", "1.1", "12.1", "Section 3"
_SECTION_NUMBER_PATTERN = re.compile(r'^(\d+(?:\.\d+)*)\s*\.?\s+')


def classify_heading(heading: str) -> tuple[ClauseTypeEnum, float | None]:
    """Classify a clause by its heading text.

    Returns:
        Tuple of (clause_type, classification_confidence).
        confidence is None for pattern matches (deterministic),
        and a float for LLM-assisted classification.
    """
    for pattern, clause_type in _HEADING_PATTERNS:
        if pattern.search(heading):
            return clause_type, None  # deterministic — no confidence needed
    return ClauseTypeEnum.GENERAL, None


def extract_section_number(heading: str) -> str | None:
    """Extract section number from a heading like '3.2.1 Payment Terms'."""
    m = _SECTION_NUMBER_PATTERN.match(heading)
    return m.group(1) if m else None


def classify_paragraphs(
    paragraphs: list[ParsedParagraph],
    document_id: str,
) -> list[Clause]:
    """Classify heading paragraphs into Clause objects.

    Only paragraphs with heading_level are considered as clause boundaries.
    """
    clauses: list[Clause] = []

    for para in paragraphs:
        if para.heading_level is None:
            continue
        if not para.text.strip():
            continue

        clause_type, confidence = classify_heading(para.text)
        section_number = extract_section_number(para.text)

        clause = Clause(
            clause_id=f"c-{uuid.uuid4().hex[:8]}",
            document_id=document_id,
            clause_type=clause_type,
            heading=para.text,
            section_number=section_number,
            fact_id="",  # Will be linked after fact extraction
            contained_fact_ids=[],
            cross_reference_ids=[],
            classification_method="pattern_match",
            classification_confidence=confidence,
        )
        clauses.append(clause)

    return clauses
