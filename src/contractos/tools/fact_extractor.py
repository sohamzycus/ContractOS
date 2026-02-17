"""FactExtractor — orchestrates document parsing, pattern extraction, and fact generation."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from contractos.models.binding import Binding
from contractos.models.clause import Clause, CrossReference
from contractos.models.clause_type import ClauseFactSlot
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.tools.alias_detector import detect_aliases
from contractos.tools.clause_classifier import classify_paragraphs_with_fallback
from contractos.tools.contract_patterns import PatternMatch, extract_patterns
from contractos.tools.cross_reference_extractor import extract_cross_references
from contractos.tools.docx_parser import parse_docx
from contractos.tools.mandatory_fact_extractor import extract_mandatory_facts
from contractos.tools.parsers import ParsedDocument, ParsedParagraph
from contractos.tools.pdf_parser import parse_pdf

# Pattern name → FactType mapping
_PATTERN_TO_FACT_TYPE: dict[str, FactType] = {
    "definition": FactType.TEXT_SPAN,
    "section_reference": FactType.CROSS_REFERENCE,
    "duration": FactType.TEXT_SPAN,
    "monetary": FactType.TEXT_SPAN,
    "date": FactType.TEXT_SPAN,
    "percentage": FactType.TEXT_SPAN,
    "entity_alias": FactType.ENTITY,
}

# Pattern name → EntityType mapping (only for entity patterns)
_PATTERN_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "entity_alias": EntityType.PARTY,
}


class ExtractionResult:
    """Complete result of document extraction."""

    def __init__(self) -> None:
        self.parsed_document: ParsedDocument | None = None
        self.facts: list[Fact] = []
        self.bindings: list[Binding] = []
        self.clauses: list[Clause] = []
        self.cross_references: list[CrossReference] = []
        self.clause_fact_slots: list[ClauseFactSlot] = []

    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @property
    def clause_count(self) -> int:
        return len(self.clauses)


def extract_from_file(
    file_path: str | Path,
    document_id: str,
    *,
    extraction_version: str = "0.1.0",
) -> ExtractionResult:
    """Run the full extraction pipeline on a document file.

    Pipeline:
    1. Parse document (docx/pdf) → paragraphs, tables, full_text
    2. Extract patterns (definitions, durations, monetary, dates, etc.)
    3. Generate facts from patterns and paragraphs
    4. Detect entity aliases → produce bindings
    5. Classify clauses from headings
    6. Extract cross-references within clauses
    7. Check mandatory facts per clause type

    Returns:
        ExtractionResult with all extracted entities.
    """
    file_path = Path(file_path)
    result = ExtractionResult()

    # Step 1: Parse
    if file_path.suffix.lower() == ".docx":
        parsed = parse_docx(file_path)
    elif file_path.suffix.lower() == ".pdf":
        parsed = parse_pdf(file_path)
    else:
        msg = f"Unsupported file format: {file_path.suffix}"
        raise ValueError(msg)
    result.parsed_document = parsed

    now = datetime.now()
    extraction_method = f"fact_extractor_{extraction_version}"

    # Step 2: Extract patterns from full text
    pattern_matches = extract_patterns(parsed.full_text)

    # Step 3: Generate facts from patterns
    for pm in pattern_matches:
        fact_type = _PATTERN_TO_FACT_TYPE.get(pm.pattern_name, FactType.TEXT_SPAN)
        entity_type = _PATTERN_TO_ENTITY_TYPE.get(pm.pattern_name)

        fact = Fact(
            fact_id=f"f-{uuid.uuid4().hex[:8]}",
            fact_type=fact_type,
            entity_type=entity_type,
            value=pm.value,
            evidence=FactEvidence(
                document_id=document_id,
                text_span=pm.value,
                char_start=pm.start,
                char_end=pm.end,
                location_hint=f"characters {pm.start}-{pm.end}",
                structural_path=f"body > pattern[{pm.pattern_name}]",
            ),
            extraction_method=extraction_method,
            extracted_at=now,
        )
        result.facts.append(fact)

    # Step 3b: Generate facts from table cells
    for table in parsed.tables:
        for cell in table.cells:
            if cell.text.strip() and cell.row > 0:  # skip header row
                fact = Fact(
                    fact_id=f"f-{uuid.uuid4().hex[:8]}",
                    fact_type=FactType.TABLE_CELL,
                    value=cell.text,
                    evidence=FactEvidence(
                        document_id=document_id,
                        text_span=cell.text,
                        char_start=cell.char_start,
                        char_end=cell.char_end,
                        location_hint=f"table row {cell.row}, col {cell.col}",
                        structural_path=cell.structural_path,
                    ),
                    extraction_method=extraction_method,
                    extracted_at=now,
                )
                result.facts.append(fact)

    # Step 4: Detect aliases
    alias_facts, alias_bindings = detect_aliases(parsed.full_text, document_id)
    result.facts.extend(alias_facts)
    result.bindings.extend(alias_bindings)

    # Step 5: Classify clauses (with structural fallback for heading detection)
    clauses = classify_paragraphs_with_fallback(parsed.paragraphs, document_id)

    # Link clause fact_ids to heading paragraph facts
    for clause in clauses:
        heading_fact = Fact(
            fact_id=f"f-{uuid.uuid4().hex[:8]}",
            fact_type=FactType.TEXT_SPAN,
            value=clause.heading,
            evidence=FactEvidence(
                document_id=document_id,
                text_span=clause.heading,
                char_start=0,
                char_end=len(clause.heading),
                location_hint=f"heading: {clause.heading}",
                structural_path="body > heading",
            ),
            extraction_method=extraction_method,
            extracted_at=now,
        )
        result.facts.append(heading_fact)
        clause.fact_id = heading_fact.fact_id

    result.clauses = clauses

    # Step 6: Extract cross-references
    # For each clause, search the text following its heading
    clause_texts = _get_clause_texts(parsed, clauses)
    for clause, clause_text in zip(clauses, clause_texts):
        xrefs = extract_cross_references(clause_text, clause.clause_id, clauses)
        # Link cross-references to the clause's heading fact
        for xref in xrefs:
            if not xref.source_fact_id and clause.fact_id:
                xref.source_fact_id = clause.fact_id
        clause.cross_reference_ids = [x.reference_id for x in xrefs]
        result.cross_references.extend(xrefs)

    # Step 6b: Generate clause body text facts
    # Each non-heading paragraph within a clause becomes a fact so the LLM
    # has the full clause text available for Q&A.
    for clause, clause_text in zip(clauses, clause_texts):
        body_paragraphs = _get_clause_body_paragraphs(parsed, clause)
        for para in body_paragraphs:
            if not para.text.strip():
                continue
            body_fact = Fact(
                fact_id=f"f-body-{uuid.uuid4().hex[:8]}",
                fact_type=FactType.CLAUSE_TEXT,
                value=para.text,
                evidence=FactEvidence(
                    document_id=document_id,
                    text_span=para.text,
                    char_start=para.char_start,
                    char_end=para.char_end,
                    location_hint=f"clause: {clause.heading}",
                    structural_path=para.structural_path or f"body > {clause.heading}",
                ),
                extraction_method=extraction_method,
                extracted_at=now,
            )
            result.facts.append(body_fact)
            # Track contained facts in the clause
            clause.contained_fact_ids.append(body_fact.fact_id)

    # Step 7: Mandatory fact slots
    for clause, clause_text in zip(clauses, clause_texts):
        slots = extract_mandatory_facts(clause, clause_text)
        result.clause_fact_slots.extend(slots)

    return result


def _get_clause_body_paragraphs(
    parsed: ParsedDocument, clause: Clause
) -> list[ParsedParagraph]:
    """Get the body paragraphs (non-heading) belonging to a clause."""
    heading_indices: list[int] = []
    for i, para in enumerate(parsed.paragraphs):
        if para.heading_level is not None and para.text.strip():
            heading_indices.append(i)

    clause_heading_idx = None
    for hi in heading_indices:
        if parsed.paragraphs[hi].text == clause.heading:
            clause_heading_idx = hi
            break

    if clause_heading_idx is None:
        return []

    next_heading_idx = len(parsed.paragraphs)
    for hi in heading_indices:
        if hi > clause_heading_idx:
            next_heading_idx = hi
            break

    # Return only body paragraphs (skip the heading itself)
    return [
        parsed.paragraphs[i]
        for i in range(clause_heading_idx + 1, next_heading_idx)
        if parsed.paragraphs[i].text.strip()
        and parsed.paragraphs[i].heading_level is None
    ]


def _get_clause_texts(parsed: ParsedDocument, clauses: list[Clause]) -> list[str]:
    """Get the text content for each clause (from heading to next heading)."""
    # Find heading paragraph indices
    heading_indices: list[int] = []
    for i, para in enumerate(parsed.paragraphs):
        if para.heading_level is not None and para.text.strip():
            heading_indices.append(i)

    clause_texts: list[str] = []
    for idx, clause in enumerate(clauses):
        # Find the heading index for this clause
        clause_heading_idx = None
        for hi in heading_indices:
            if parsed.paragraphs[hi].text == clause.heading:
                clause_heading_idx = hi
                break

        if clause_heading_idx is None:
            clause_texts.append("")
            continue

        # Collect text from heading to next heading
        next_heading_idx = len(parsed.paragraphs)
        for hi in heading_indices:
            if hi > clause_heading_idx:
                next_heading_idx = hi
                break

        text_parts = [
            parsed.paragraphs[i].text
            for i in range(clause_heading_idx, next_heading_idx)
            if parsed.paragraphs[i].text.strip()
        ]
        clause_texts.append(" ".join(text_parts))

    return clause_texts
