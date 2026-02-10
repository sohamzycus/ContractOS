"""Unit tests for contract-specific regex patterns (T044)."""

from __future__ import annotations

import pytest

from contractos.tools.contract_patterns import (
    ALIAS_PATTERN,
    DATE_PATTERN,
    DEFINITION_PATTERN,
    DURATION_PATTERN,
    MONETARY_PATTERN,
    PERCENTAGE_PATTERN,
    SECTION_REF_PATTERN,
    PatternMatch,
    extract_patterns,
)


class TestDefinitionPattern:
    def test_shall_mean(self) -> None:
        text = '"Effective Date" shall mean January 1, 2025.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1
        assert matches[0][0] == "Effective Date"

    def test_means(self) -> None:
        text = '"Service Period" means the period of thirty (30) days.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1
        assert matches[0][0] == "Service Period"

    def test_refers_to(self) -> None:
        text = '"Agreement" refers to this Master Services Agreement.'
        matches = DEFINITION_PATTERN.findall(text)
        assert len(matches) >= 1


class TestSectionRefPattern:
    def test_section_number(self) -> None:
        text = "as mentioned in Section 3.2.1"
        matches = SECTION_REF_PATTERN.findall(text)
        assert "3.2.1" in matches

    def test_section_symbol(self) -> None:
        text = "Subject to §12.1"
        matches = SECTION_REF_PATTERN.findall(text)
        assert "12.1" in matches

    def test_appendix(self) -> None:
        text = "as detailed in Appendix A"
        matches = SECTION_REF_PATTERN.findall(text)
        assert "A" in matches

    def test_schedule(self) -> None:
        text = "listed in Schedule B"
        matches = SECTION_REF_PATTERN.findall(text)
        assert "B" in matches

    def test_clause_with_sub(self) -> None:
        text = "per Clause 4(a)"
        matches = SECTION_REF_PATTERN.findall(text)
        assert any("4" in m for m in matches)


class TestDurationPattern:
    def test_word_and_number(self) -> None:
        text = "thirty (30) days"
        matches = DURATION_PATTERN.findall(text)
        assert len(matches) >= 1
        # group 2 is the number, group 3 is the unit
        assert any(m[1] == "30" and "day" in m[2] for m in matches)

    def test_number_only(self) -> None:
        text = "90 days"
        matches = DURATION_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_months(self) -> None:
        text = "twenty-four (24) months"
        matches = DURATION_PATTERN.findall(text)
        assert any("24" in m[1] for m in matches)


class TestMonetaryPattern:
    def test_dollar_amount(self) -> None:
        text = "$150,000.00"
        matches = MONETARY_PATTERN.findall(text)
        assert len(matches) >= 1
        assert "$150,000.00" in matches

    def test_usd_prefix(self) -> None:
        text = "USD 1,000"
        matches = MONETARY_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_euro(self) -> None:
        text = "€500"
        matches = MONETARY_PATTERN.findall(text)
        assert len(matches) >= 1


class TestDatePattern:
    def test_long_date(self) -> None:
        text = "January 1, 2025"
        matches = DATE_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_slash_date(self) -> None:
        text = "01/01/2025"
        matches = DATE_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_iso_date(self) -> None:
        text = "2025-01-01"
        matches = DATE_PATTERN.findall(text)
        assert len(matches) >= 1


class TestPercentagePattern:
    def test_integer_percent(self) -> None:
        matches = PERCENTAGE_PATTERN.findall("5%")
        assert len(matches) >= 1

    def test_decimal_percent(self) -> None:
        matches = PERCENTAGE_PATTERN.findall("10.5%")
        assert len(matches) >= 1


class TestAliasPattern:
    def test_hereinafter_referred_to_as(self) -> None:
        text = 'Alpha Corp, hereinafter referred to as "Buyer"'
        matches = ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1
        assert any("Alpha Corp" in m[0] for m in matches)
        assert any("Buyer" in m[1] for m in matches)

    def test_the_pattern(self) -> None:
        text = 'Gamma Inc (the "Discloser")'
        matches = ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1

    def test_hereafter(self) -> None:
        text = "Beta Services Ltd, hereafter 'Vendor'"
        matches = ALIAS_PATTERN.findall(text)
        assert len(matches) >= 1


class TestExtractPatterns:
    def test_extracts_multiple_types(self) -> None:
        text = (
            '"Effective Date" shall mean January 1, 2025. '
            "Payment of $150,000.00 due in 30 days. "
            "See Section 3.2.1 for details."
        )
        matches = extract_patterns(text)
        pattern_names = {m.pattern_name for m in matches}
        assert "definition" in pattern_names
        assert "date" in pattern_names
        assert "monetary" in pattern_names
        assert "duration" in pattern_names
        assert "section_reference" in pattern_names

    def test_results_sorted_by_position(self) -> None:
        text = "$100 due in 30 days per Section 5."
        matches = extract_patterns(text)
        for i in range(1, len(matches)):
            assert matches[i].start >= matches[i - 1].start

    def test_returns_pattern_match_objects(self) -> None:
        text = "$100"
        matches = extract_patterns(text)
        assert all(isinstance(m, PatternMatch) for m in matches)
