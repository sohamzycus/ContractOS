"""Clause classifier — assigns ClauseTypeEnum to document sections.

Includes a structural fallback for documents where parsers couldn't
detect heading levels (e.g., PDFs without font-size variation, DOCX
without Heading styles).
"""

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

# Structural heading detection patterns (for fallback)
_NUMBERED_HEADING_PATTERN = re.compile(r'^(\d+(?:\.\d+)*)\.?\s+([A-Z].*)')
_ALLCAPS_HEADING_PATTERN = re.compile(r'^[A-Z][A-Z\s\-&/]{3,59}$')


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


def classify_paragraphs_with_fallback(
    paragraphs: list[ParsedParagraph],
    document_id: str,
) -> list[Clause]:
    """Classify paragraphs with structural fallback for heading detection.

    First tries standard heading-based classification. If that produces
    zero clauses, applies structural heuristics to detect headings from:
    - Numbered paragraphs: "1. DEFINITIONS", "12.1 Payment Terms"
    - ALL-CAPS short lines: "CONFIDENTIALITY", "TERM AND TERMINATION"
    - Section-start patterns in long paragraphs (common in PDFs)
    """
    # Try standard classification first
    clauses = classify_paragraphs(paragraphs, document_id)

    # Check if we got meaningful clauses (not just title-page elements)
    if clauses and _has_meaningful_clauses(clauses):
        return clauses

    # Fallback 1: extract section headings from long paragraphs
    # (PDFs often merge entire sections into single blocks)
    split = _split_section_paragraphs(paragraphs)
    if len(split) > len(paragraphs):
        promoted = _promote_structural_headings(split)
        split_clauses = classify_paragraphs(promoted, document_id)
        if split_clauses and _has_meaningful_clauses(split_clauses):
            return split_clauses

    # Fallback 2: promote structural headings to heading_level=1
    promoted = _promote_structural_headings(paragraphs)
    fallback_clauses = classify_paragraphs(promoted, document_id)
    if fallback_clauses and _has_meaningful_clauses(fallback_clauses):
        return fallback_clauses

    # Return whatever we have (even if all GENERAL)
    return clauses or fallback_clauses


def _has_meaningful_clauses(clauses: list[Clause]) -> bool:
    """Check if clause list contains at least one non-GENERAL classified clause.

    Title-page elements (company names, "BETWEEN", "AND") all classify as
    GENERAL. A meaningful extraction should have at least one specific type.
    """
    return any(c.clause_type != ClauseTypeEnum.GENERAL for c in clauses)


def _promote_structural_headings(
    paragraphs: list[ParsedParagraph],
) -> list[ParsedParagraph]:
    """Promote paragraphs that look like headings based on structure.

    Creates new ParsedParagraph objects with heading_level set for
    paragraphs matching structural heading patterns.
    """
    promoted: list[ParsedParagraph] = []

    for para in paragraphs:
        if para.heading_level is not None:
            promoted.append(para)
            continue

        text = para.text.strip()
        if not text:
            promoted.append(para)
            continue

        heading_level = None

        # Check numbered heading: "1. DEFINITIONS", "12.1 Payment Terms"
        m = _NUMBERED_HEADING_PATTERN.match(text)
        if m and len(text) < 80:
            heading_level = 1

        # Check ALL-CAPS heading: "CONFIDENTIALITY", "TERM AND TERMINATION"
        if heading_level is None and _ALLCAPS_HEADING_PATTERN.match(text):
            word_count = len(text.split())
            if word_count <= 8 and any(c.isalpha() for c in text):
                heading_level = 1

        if heading_level is not None:
            promoted.append(ParsedParagraph(
                text=para.text,
                char_start=para.char_start,
                char_end=para.char_end,
                structural_path=f"body > heading[{heading_level}][promoted]",
                heading_level=heading_level,
                page_number=para.page_number,
            ))
        else:
            promoted.append(para)

    return promoted


# Pattern for section starts within long text blocks
_SECTION_START_PATTERN = re.compile(
    r'(?:^|\s)(\d+)\.\s+([A-Z][A-Z\s\-&/]+?)(?:\s+\d+\.\d+|\s{2,})',
)


def _split_section_paragraphs(
    paragraphs: list[ParsedParagraph],
) -> list[ParsedParagraph]:
    """Split long paragraphs that contain multiple section headings.

    Common in PDFs where entire sections are merged into single text blocks.
    Detects patterns like "5. PERSONNEL 5.1 SOWs..." and splits them.
    """
    result: list[ParsedParagraph] = []

    for para in paragraphs:
        text = para.text.strip()
        if not text or len(text) < 80:
            result.append(para)
            continue

        # Find section-start patterns: "N. HEADING_TEXT"
        section_matches = list(_SECTION_START_PATTERN.finditer(text))
        if not section_matches:
            result.append(para)
            continue

        # Create a synthetic heading paragraph for each section found
        for m in section_matches:
            section_num = m.group(1)
            heading_text = m.group(2).strip()
            full_heading = f"{section_num}. {heading_text}"

            result.append(ParsedParagraph(
                text=full_heading,
                char_start=para.char_start + m.start(),
                char_end=para.char_start + m.start() + len(full_heading),
                structural_path=f"{para.structural_path} > section[{section_num}]",
                heading_level=None,
                page_number=para.page_number,
            ))

        # Keep the original paragraph too (for body text)
        result.append(para)

    return result
