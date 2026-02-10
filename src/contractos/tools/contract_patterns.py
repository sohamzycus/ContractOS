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


# ── Pattern Definitions ────────────────────────────────────────────

# Definition patterns: "X shall mean Y", "X means Y"
DEFINITION_PATTERN = re.compile(
    r'"([^"]+)"\s+(?:shall\s+mean|means|refers?\s+to|is\s+defined\s+as)\s+(.+?)(?:\.|$)',
    re.IGNORECASE | re.MULTILINE,
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


def extract_patterns(text: str) -> list[PatternMatch]:
    """Extract all contract patterns from text."""
    matches: list[PatternMatch] = []

    for m in DEFINITION_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="definition",
            value=m.group(1),
            start=m.start(),
            end=m.end(),
            metadata={"term": m.group(1), "definition": m.group(2).strip()},
        ))

    for m in SECTION_REF_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="section_reference",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"reference": m.group(1)},
        ))

    for m in DURATION_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="duration",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"number": m.group(2), "unit": m.group(3)},
        ))

    for m in MONETARY_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="monetary",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in DATE_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="date",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in PERCENTAGE_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="percentage",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
        ))

    for m in ALIAS_PATTERN.finditer(text):
        matches.append(PatternMatch(
            pattern_name="entity_alias",
            value=m.group(0),
            start=m.start(),
            end=m.end(),
            metadata={"entity": m.group(1).strip(), "alias": m.group(2).strip()},
        ))

    # Sort by position
    matches.sort(key=lambda x: x.start)
    return matches
