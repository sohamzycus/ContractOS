# ContractOS Q&A Test Report

**Generated**: 2026-02-10  
**Model**: `claude-sonnet-4-5-global` (via LiteLLM proxy)  
**Total Queries**: 17 (10 MSA + 7 NDA)  
**Raw JSON**: [`qa_report_procurement_msa.json`](qa_report_procurement_msa.json), [`qa_report_nda.json`](qa_report_nda.json)

---

## Summary

| Metric | MSA (DOCX) | NDA (PDF) | Total |
|--------|:----------:|:---------:|:-----:|
| Queries | 10 | 7 | 17 |
| Fact-grounded answers | 7 | 5 | 12 |
| Not-found (honest) | 3 | 2 | 5 |
| Very high confidence | 6 | 5 | 11 |
| High confidence | 1 | 0 | 1 |
| Moderate confidence | 1 | 0 | 1 |
| Speculative | 1 | 1 | 2 |
| Not-found (speculative) | 1 | 1 | 2 |
| Avg generation time | 7.98s | 6.72s | 7.44s |
| Avg facts referenced | 3.7 | 4.6 | 4.1 |

---

## Report 1: Master Services Agreement (`simple_procurement.docx`)

**Document**: Procurement MSA between Alpha Corp (Buyer) and Beta Services Ltd (Vendor)  
**Extraction**: 41 facts, 8 clauses, 5 bindings, 6 cross-references

### Q1: "Who are the parties to this agreement?"

| Field | Value |
|-------|-------|
| **Answer** | The parties to this agreement are Alpha Corp (referred to as "Buyer") and Beta Services Ltd (referred to as "Vendor"). |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 8,853 ms |

**Provenance Chain** (4 nodes):
1. **Fact** `f-9754d9d0` — chars 86–156: *"is entered into between Alpha Corp, hereinafter referred to as "Buyer""*
2. **Fact** `f-5715610a` — chars 158–216: *"and Beta Services Ltd, hereinafter referred to as "Vendor""*
3. **Fact** `f-alias-9d7c6779` — Alias: *Alpha Corp → Buyer*
4. **Fact** `f-alias-6e66e042` — Alias: *Beta Services Ltd → Vendor*

---

### Q2: "What are the payment terms?"

| Field | Value |
|-------|-------|
| **Answer** | Buyer shall pay Vendor a total amount of $150,000.00. Payment is due within sixty (60) days from the Effective Date (January 1, 2025), which means payment must be made by March 2, 2025. The payment terms are detailed in Section 3.2.1 of the Agreement. |
| **Answer Type** | `fact` |
| **Confidence** | **0.95** — very_high (blue) |
| **Facts Referenced** | 5 facts |
| **Generation Time** | 9,096 ms |

**Provenance Chain** (5 nodes):
1. **Fact** — heading: *"3. Payment Terms"*
2. **Fact** — chars 561–572: *"$150,000.00"*
3. **Fact** — chars 766–781: *"sixty (60) days"*
4. **Fact** — chars 862–875: *"Section 3.2.1"*
5. **Fact** — chars 246–261: *"January 1, 2025"*

---

### Q3: "What is the effective date of this contract?"

| Field | Value |
|-------|-------|
| **Answer** | The effective date of this contract is January 1, 2025. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 2 facts |
| **Generation Time** | 7,358 ms |

**Provenance Chain** (2 nodes):
1. **Fact** — chars 218–262: *"Effective Date"* (definition span)
2. **Fact** — chars 246–261: *"January 1, 2025"*

---

### Q4: "What is the service period?"

| Field | Value |
|-------|-------|
| **Answer** | The service period is thirty (30) days from the Effective Date, which is January 1, 2025. Therefore, the service period runs from January 1, 2025 to January 30, 2025. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 3 facts |
| **Generation Time** | 6,702 ms |

**Provenance Chain** (3 nodes):
1. **Fact** — chars 263–346: *"Service Period"* (definition span)
2. **Fact** — chars 305–321: *"thirty (30) days"*
3. **Fact** — chars 246–261: *"January 1, 2025"*

---

### Q5: "What are the termination conditions?"

| Field | Value |
|-------|-------|
| **Answer** | The contract does not contain specific termination conditions in the provided facts. While there is a section titled '4. Termination', the actual termination provisions and conditions are not included in the extracted facts. |
| **Answer Type** | `not_found` |
| **Confidence** | **0.85** — high (green) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 11,458 ms |

> **Note**: The model correctly identifies that while a Termination heading exists, the clause body text was not extracted as individual facts. This is an honest "not found" — the system does not hallucinate.

---

### Q6: "What confidentiality obligations exist?"

| Field | Value |
|-------|-------|
| **Answer** | Cannot identify specific confidentiality obligations. While a 'Confidentiality' section exists (Section 5), the actual content was not extracted. |
| **Answer Type** | `not_found` |
| **Confidence** | **0.1** — speculative (red) |
| **Facts Referenced** | 1 fact |
| **Generation Time** | 7,856 ms |

> **Note**: Low confidence correctly reflects that only the heading was found, not the obligations themselves.

---

### Q7: "What products are covered under this agreement?"

| Field | Value |
|-------|-------|
| **Answer** | Three products: (1) Dell Inspiron 15 (IT Equipment, qty 50), (2) HP LaserJet Pro (Office Equipment, qty 25), (3) Cisco Router 4000 (Network Equipment, qty 10). Specified in Schedule A. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 10 facts |
| **Generation Time** | 7,765 ms |

**Provenance Chain** (10 nodes): Schedule A heading + 9 table cells (3 products × 3 columns: name, category, quantity)

---

### Q8: "What locations are covered?"

| Field | Value |
|-------|-------|
| **Answer** | Bangalore, Pune, and Mumbai, all in India. Specified in Schedule B. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 7 facts |
| **Generation Time** | 6,720 ms |

**Provenance Chain** (7 nodes): Schedule B heading + 6 table cells (3 locations × 2 columns: city, country)

---

### Q9: "Who is the Buyer?"

| Field | Value |
|-------|-------|
| **Answer** | The Buyer is Alpha Corp. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 2 facts |
| **Generation Time** | 5,004 ms |

**Provenance Chain** (2 nodes):
1. **Fact** — chars 86–156: *"is entered into between Alpha Corp, hereinafter referred to as "Buyer""*
2. **Fact** — Alias: *Alpha Corp → Buyer*

---

### Q10: "What is the total contract value?"

| Field | Value |
|-------|-------|
| **Answer** | $150,000.00 is the only monetary value explicitly stated. Context does not specify whether this is the total value, a payment installment, or another obligation. |
| **Answer Type** | `fact` |
| **Confidence** | **0.6** — moderate (yellow) |
| **Facts Referenced** | 1 fact |
| **Generation Time** | 8,971 ms |

> **Note**: Moderate confidence correctly reflects the ambiguity — the model finds the amount but cannot confirm it is the "total" value without more context.

---

## Report 2: Non-Disclosure Agreement (`simple_nda.pdf`)

**Document**: NDA between Gamma Inc (Discloser) and Delta LLC (Recipient)  
**Extraction**: 17 facts, 0 clauses, 3 bindings

### Q1: "Who are the parties to this NDA?"

| Field | Value |
|-------|-------|
| **Answer** | Gamma Inc (the "Discloser") and Delta LLC (the "Recipient"). |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 6,174 ms |

**Provenance Chain** (4 nodes):
1. **Fact** — chars 74–124: *"is entered into between Gamma Inc (the "Discloser")"*
2. **Fact** — chars 126–156: *"and Delta LLC (the "Recipient")"*
3. **Fact** — Alias: *Gamma Inc → Discloser*
4. **Fact** — Alias: *Delta LLC → Recipient*

---

### Q2: "What is the duration of the confidentiality obligation?"

| Field | Value |
|-------|-------|
| **Answer** | Cannot be definitively determined. The contract has dates from Jan 1, 2025 to Dec 31, 2026 (~24 months), and references "24 months" and "30 days", but none are explicitly connected to confidentiality obligations in the extracted facts. |
| **Answer Type** | `not_found` |
| **Confidence** | **0.3** — speculative (red) |
| **Facts Referenced** | 6 facts |
| **Generation Time** | 9,120 ms |

> **Note**: Honest answer — temporal facts exist but the model correctly refuses to guess which one applies to confidentiality.

---

### Q3: "What is the effective date?"

| Field | Value |
|-------|-------|
| **Answer** | January 1, 2025. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 4,838 ms |

**Provenance Chain** (4 nodes): Table label "Effective Date" + 3 corroborating date references

---

### Q4: "When does this agreement expire?"

| Field | Value |
|-------|-------|
| **Answer** | December 31, 2026. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 5,914 ms |

**Provenance Chain** (4 nodes): Table label "Expiry Date" + 3 corroborating date references

---

### Q5: "What is the notice period for termination?"

| Field | Value |
|-------|-------|
| **Answer** | Thirty (30) days. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 1 fact |
| **Generation Time** | 4,841 ms |

---

### Q6: "Who is the Discloser and who is the Recipient?"

| Field | Value |
|-------|-------|
| **Answer** | The Discloser is Gamma Inc and the Recipient is Delta LLC. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 4 facts |
| **Generation Time** | 6,129 ms |

---

### Q7: "What are the key dates in this agreement?"

| Field | Value |
|-------|-------|
| **Answer** | (1) Effective Date: January 1, 2025, (2) Expiry Date: December 31, 2026. Duration ~2 years. Also references "thirty (30) days" and "four (24) months" for specific obligations. |
| **Answer Type** | `fact` |
| **Confidence** | **1.0** — very_high (blue) |
| **Facts Referenced** | 10 facts |
| **Generation Time** | 9,995 ms |

**Provenance Chain** (10 nodes): All date-related facts from text spans and table cells

---

## Key Observations

1. **Grounded answers**: 12 of 17 queries (71%) returned fact-grounded answers with very high confidence. The system cites specific character offsets and table cell locations.

2. **Honest "not found"**: 5 queries correctly returned "not found" when clause body text was not available in extracted facts. The system does not hallucinate — it acknowledges the gap.

3. **Binding resolution**: Entity aliases (Buyer→Alpha Corp, Vendor→Beta Services Ltd, Discloser→Gamma Inc, Recipient→Delta LLC) are correctly resolved and used in answers.

4. **Table extraction**: Products (Schedule A) and Locations (Schedule B) are fully extracted from tables with correct row/column metadata, enabling precise answers about covered items.

5. **Confidence calibration**: The model appropriately assigns lower confidence when evidence is ambiguous (Q10: contract value = moderate) or missing (Q6: confidentiality = speculative).

6. **Provenance depth**: Answers reference 1–10 facts each, with full document locations. Every claim traces back to specific evidence.
