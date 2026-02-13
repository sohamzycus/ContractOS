# Quickstart: Phase 9 — Playbook Intelligence & Risk Framework

## Scenario 1: Playbook-Based Contract Review

### Setup
```bash
# Server running with real LLM
docker compose up -d

# Upload a contract
curl -X POST http://localhost:8742/contracts/upload \
  -F "file=@vendor_agreement.docx"
# → { "document_id": "doc-abc123", "fact_count": 245, "clause_count": 18 }
```

### Review Against Playbook
```bash
curl -X POST http://localhost:8742/contracts/doc-abc123/review \
  -H "Content-Type: application/json" \
  -d '{"user_side": "customer", "generate_redlines": true}'
```

### Expected Response
```json
{
  "summary": "3 RED, 5 YELLOW, 8 GREEN. Key: uncapped indemnification, missing DPA, short notice period.",
  "red_count": 3,
  "yellow_count": 5,
  "green_count": 8,
  "findings": [
    {
      "severity": "red",
      "clause_type": "indemnification",
      "deviation_description": "Unilateral indemnification — Buyer only",
      "redline": {
        "proposed_language": "Each Party shall indemnify...",
        "priority": "tier_1"
      }
    }
  ],
  "negotiation_strategy": "Lead with Tier 1: indemnification, DPA, liability cap..."
}
```

### Copilot UI Flow
1. Upload contract → document renders
2. Click "Review Against Playbook" button
3. Reasoning steps animate (loading playbook → analyzing clauses → scoring risk)
4. Results appear as color-coded cards in sidebar
5. Click any finding → document scrolls to and highlights the clause
6. Expand finding → see redline suggestion with rationale

---

## Scenario 2: NDA Triage

### Triage an Incoming NDA
```bash
# Upload NDA
curl -X POST http://localhost:8742/contracts/upload \
  -F "file=@vendor_nda.pdf"
# → { "document_id": "doc-nda-789" }

# Triage
curl -X POST http://localhost:8742/contracts/doc-nda-789/triage \
  -H "Content-Type: application/json" \
  -d '{"context": "New vendor for cloud services evaluation"}'
```

### Expected Response
```json
{
  "classification": {
    "level": "green",
    "routing": "Approve and route for signature",
    "timeline": "Same day"
  },
  "pass_count": 9,
  "fail_count": 0,
  "review_count": 1,
  "summary": "Standard mutual NDA. All criteria met. Minor note: governing law is Delaware (acceptable)."
}
```

### Copilot UI Flow
1. Upload NDA → document renders
2. Click "Triage NDA" button
3. Reasoning steps animate
4. Large GREEN/YELLOW/RED badge appears
5. 10-item checklist with pass/fail/review icons
6. Routing recommendation with timeline

---

## Scenario 3: Custom Playbook

### Create Organization Playbook
```yaml
# config/my_org_playbook.yaml
playbook:
  name: "Acme Corp Legal Playbook"
  version: "1.0"
  positions:
    limitation_of_liability:
      clause_type: "limitation_of_liability"
      standard_position: "Mutual cap at 24 months of fees"
      acceptable_range:
        min_position: "12 months of fees"
        max_position: "36 months of fees"
      escalation_triggers:
        - "Uncapped liability"
        - "Cap less than 6 months"
      priority: "tier_1"
      required: true

    termination:
      clause_type: "termination"
      standard_position: "Annual term with 30-day termination for convenience"
      acceptable_range:
        min_position: "Quarterly term with 15-day notice"
        max_position: "Multi-year with termination for convenience after initial term"
      escalation_triggers:
        - "No termination for convenience"
        - "Auto-renewal without notice period"
      priority: "tier_2"
      required: true
```

### Use Custom Playbook
```bash
curl -X POST http://localhost:8742/contracts/doc-abc123/review \
  -H "Content-Type: application/json" \
  -d '{"playbook": "my_org_playbook", "user_side": "customer"}'
```

---

## Scenario 4: Risk Matrix Visualization

After a playbook review, the Copilot displays a 5×5 risk matrix:

```
                    LIKELIHOOD →
              Remote  Unlikely  Possible  Likely  Certain
SEVERITY ↓
Critical  |        |         |    ●    |   ●●  |        |
High      |        |    ●    |         |   ●   |        |
Moderate  |        |   ●●    |   ●●●  |        |        |
Low       |   ●    |  ●●●●   |         |        |        |
Negligible|  ●●●   |         |         |        |        |
```

Each dot represents a finding. Click a dot to see the finding details and jump to the clause in the document.

---

## Integration Test Scenarios

### T200: Playbook Review — Basic Flow
```python
async def test_review_returns_findings(client):
    # Upload contract
    r = await client.post("/contracts/upload", files={"file": pdf_file})
    doc_id = r.json()["document_id"]

    # Review
    r = await client.post(f"/contracts/{doc_id}/review",
                          json={"user_side": "customer"})
    assert r.status_code == 200
    data = r.json()
    assert data["green_count"] + data["yellow_count"] + data["red_count"] > 0
    assert all(f["severity"] in ["green", "yellow", "red"] for f in data["findings"])
    assert all(f["provenance_facts"] for f in data["findings"])
```

### T201: NDA Triage — GREEN Classification
```python
async def test_standard_nda_classified_green(client):
    r = await client.post("/contracts/upload", files={"file": standard_nda})
    doc_id = r.json()["document_id"]

    r = await client.post(f"/contracts/{doc_id}/triage")
    assert r.status_code == 200
    data = r.json()
    assert data["classification"]["level"] == "green"
    assert data["pass_count"] >= 8
```

### T202: Redline Generation
```python
async def test_redline_generated_for_red_finding(client):
    r = await client.post("/contracts/upload", files={"file": problematic_contract})
    doc_id = r.json()["document_id"]

    r = await client.post(f"/contracts/{doc_id}/review",
                          json={"generate_redlines": True})
    data = r.json()
    red_findings = [f for f in data["findings"] if f["severity"] == "red"]
    assert len(red_findings) > 0
    for f in red_findings:
        assert f["redline"] is not None
        assert f["redline"]["proposed_language"]
        assert f["redline"]["rationale"]
        assert f["redline"]["priority"]
```
