"""Contract-specific regex patterns for entity and structure extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PatternMatch:
    """A match from a contract pattern."""

    pattern_name: str
    value: str
    start: int
    end: int
    metadata: dict[str, str] = field(default_factory=dict)


# ── Quote Normalization ────────────────────────────────────────────

# Smart/curly quote → straight quote mapping
_QUOTE_MAP = str.maketrans({
    "\u201c": '"',  # left double curly quote
    "\u201d": '"',  # right double curly quote
    "\u201e": '"',  # double low-9 quotation mark
    "\u2018": "'",  # left single curly quote
    "\u2019": "'",  # right single curly quote
    "\u201a": "'",  # single low-9 quotation mark
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u00ab": '"',  # left-pointing double angle (guillemet)
    "\u00bb": '"',  # right-pointing double angle (guillemet)
})


def normalize_quotes(text: str) -> str:
    """Normalize smart/curly quotes to straight ASCII equivalents.

    Converts: \u201c\u201d → ", \u2018\u2019 → ', \u2013\u2014 → -
    This ensures regex patterns match regardless of quote style.
    """
    return text.translate(_QUOTE_MAP)


# ── Pattern Definitions ────────────────────────────────────────────

# Definition patterns: "X shall mean Y", "X means Y"
DEFINITION_PATTERN = re.compile(
    r'"([^"]+)"\s+(?:shall\s+mean|means|refers?\s+to|is\s+defined\s+as|designates?|constitutes?|includes?)\s+(.+?)(?:\.|$)',
    re.IGNORECASE | re.MULTILINE,
)

# Parenthetical definition: (the "Agreement") or ("Agreement")
PARENTHETICAL_DEF_PATTERN = re.compile(
    r'\((?:the\s+)?["\']([A-Za-z][A-Za-z\s\-]+?)["\'](?:\s+or\s+["\']([A-Za-z][A-Za-z\s\-]+?)["\'])?\)',
)

# Section references: §12.1, Section 3.2.1, Clause 4(a), Article 5
SECTION_REF_PATTERN = re.compile(
    r'(?:§|Section|Clause|Article|Appendix|Schedule|Annex)\s*'
    r'(\d+(?:\.\d+)*(?:\s*\([a-z]\))?|[A-Z])',
    re.IGNORECASE,
)

# Duration patterns: "thirty (30) days", "90 days", "twelve (12) months"
DURATION_PATTERN = re.compile(
    r'(?:(\w+)\s+\()?(\d+)\)?\s*(days?|months?|years?|weeks?|business\s+days?)',
    re.IGNORECASE,
)

# Monetary patterns: $150,000.00, USD 1,000, €500
MONETARY_PATTERN = re.compile(
    r'(?:[$€£¥]|USD|EUR|GBP|INR)\s*[\d,]+(?:\.\d{1,2})?'
    r'|[\d,]+(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|INR|dollars?|pounds?|euros?)',
    re.IGNORECASE,
)

# Date patterns: January 1, 2025; 01/01/2025; 2025-01-01
DATE_PATTERN = re.compile(
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+\d{1,2},?\s+\d{4}'
    r'|\d{1,2}/\d{1,2}/\d{4}'
    r'|\d{4}-\d{2}-\d{2}',
    re.IGNORECASE,
)

# Percentage patterns: 5%, 10.5%
PERCENTAGE_PATTERN = re.compile(
    r'\d+(?:\.\d+)?\s*%',
)

# Entity alias patterns: "X, hereinafter referred to as 'Y'"
ALIAS_PATTERN = re.compile(
    r'([A-Z][A-Za-z\s&.,]+?)\s*,?\s*'
    r'(?:hereinafter\s+(?:referred\s+to\s+as|called)|'
    r'hereafter\s+(?:referred\s+to\s+as|called|)|'
    r'\(the\s+|'
    r'\()'
    r'\s*["\']([A-Za-z\s]+?)["\']',
    re.IGNORECASE,
)

# Party alias: "Entity Name, a <jurisdiction> <type> ("Alias")"
PARTY_ALIAS_PATTERN = re.compile(
    r'([A-Z][A-Za-z\s&.,]+?(?:Corp(?:oration)?|Inc\.?|LLC|Ltd\.?|Pvt\.?\s*Ltd\.?|L\.?P\.?|Company|Co\.))'
    r'[,\s]+(?:a\s+)?[A-Za-z\s]+?'
    r'(?:corporation|company|partnership|entity|limited\s+liability|limited)\s*'
    r'[,(]\s*["\']?([A-Za-z\s]+?)["\']?\s*\)',
    re.IGNORECASE,
)


def extract_patterns(text: str) -> list[PatternMatch]:
    """Extract all contract patterns from text.

    Normalizes smart/curly quotes before matching so patterns work
    regardless of the document's quote style.
    """
    normalized = normalize_quotes(text)
    matches: list[PatternMatch] = []

    for m in DEFINITION_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="definition",
            value=m.group(1),
            start=m.start(),
            end=m.end(),
            metadata={"term": m.group(1), "definition": m.group(2).strip()},
        ))

    # Parenthetical definitions: (the "Agreement") or ("Service Provider")
    for m in PARENTHETICAL_DEF_PATTERN.finditer(normalized):
        term = m.group(1).strip()
        matches.append(PatternMatch(
            pattern_name="definition",
            value=term,
            start=m.start(),
            end=m.end(),
            metadata={"term": term, "definition": "(parenthetical definition)"},
        ))
        if m.group(2):
            alt_term = m.group(2).strip()
            matches.append(PatternMatch(
                pattern_name="definition",
                value=alt_term,
                start=m.start(),
                end=m.end(),
                metadata={"term": alt_term, "definition": "(parenthetical definition)"},
            ))

    for m in SECTION_REF_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="section_reference",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"reference": m.group(1)},
        ))

    for m in DURATION_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="duration",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"number": m.group(2), "unit": m.group(3)},
        ))

    for m in MONETARY_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="monetary",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in DATE_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="date",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in PERCENTAGE_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="percentage",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in ALIAS_PATTERN.finditer(normalized):
        matches.append(PatternMatch(
            pattern_name="entity_alias",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"entity": m.group(1).strip(), "alias": m.group(2).strip()},
        ))

    # Party alias: "Corp Name, a Delaware corporation ("Alias")"
    for m in PARTY_ALIAS_PATTERN.finditer(normalized):
        entity = m.group(1).strip()
        alias = m.group(2).strip()
        if alias and entity:
            matches.append(PatternMatch(
                pattern_name="entity_alias",
                value=m.group(0),
                start=m.start(),
                end=m.end(),
                metadata={"entity": entity, "alias": alias},
            ))

    # Sort by position and deduplicate overlapping matches
    matches.sort(key=lambda x: x.start)
    return _deduplicate_matches(matches)


def _deduplicate_matches(matches: list[PatternMatch]) -> list[PatternMatch]:
    """Remove overlapping matches, preferring longer/earlier matches."""
    if not matches:
        return matches
    deduped: list[PatternMatch] = []
    for m in matches:
        if deduped and m.start < deduped[-1].end and m.pattern_name == deduped[-1].pattern_name:
            if (m.end - m.start) > (deduped[-1].end - deduped[-1].start):
                deduped[-1] = m
        else:
            deduped.append(m)
    return deduped
