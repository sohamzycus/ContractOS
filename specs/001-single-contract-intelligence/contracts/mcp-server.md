# API Contract: ContractOS MCP Server

**Date**: 2026-02-09  
**Protocol**: Model Context Protocol (MCP) v1.x  
**SDK**: `mcp[cli]` >= 1.26.0  
**Transports**: stdio (default), Streamable HTTP (optional)

---

## Server Identity

```python
FastMCP(
    name="ContractOS",
    version="0.1.0",
    description="Contract intelligence — upload, analyze, review, triage, and query legal contracts with full provenance",
    json_response=True,
)
```

---

## Tools

### 1. `upload_contract`

Upload and analyze a contract document.

```
Input:
  file_path: str          # Absolute path to DOCX or PDF file
  
Output: UploadResult
  document_id: str
  filename: str
  page_count: int
  fact_count: int
  clause_count: int
  binding_count: int
  extraction_time_ms: int
  message: str

Errors:
  - "File not found: {path}" — file doesn't exist
  - "Unsupported format: {ext}. Use .docx or .pdf" — wrong file type
  - "Extraction failed: {reason}" — parsing error
```

### 2. `load_sample_contract`

Load a built-in sample contract for testing.

```
Input:
  filename: str           # One of: simple_nda.pdf, simple_procurement.docx,
                          #         complex_it_outsourcing.docx, complex_procurement_framework.pdf

Output: UploadResult      # Same as upload_contract

Errors:
  - "Sample not found: {filename}. Available: ..." — invalid sample name
```

### 3. `ask_question`

Ask a natural-language question about uploaded contracts.

```
Input:
  question: str           # The question to ask
  document_ids: list[str] | None  # Specific docs (None = all indexed)

Output: QuestionResult
  answer: str
  confidence: float
  confidence_label: str
  provenance: list[ProvenanceNode]
  sources: list[str]
  follow_up_suggestions: list[str]

Errors:
  - "No contracts indexed. Upload a contract first." — empty index
  - "Document not found: {id}" — invalid document ID
```

### 4. `review_against_playbook`

Run playbook compliance review on a contract.

```
Input:
  document_id: str
  playbook_path: str | None  # Custom playbook YAML (None = default)

Output: ReviewResult
  findings: list[ReviewFinding]
    - clause_type: str
    - severity: "GREEN" | "YELLOW" | "RED"
    - explanation: str
    - redline: RedlineSuggestion | None
  risk_profile: RiskProfile
  negotiation_strategy: str

Progress:
  ctx.report_progress(0.0–1.0) at each clause reviewed

Errors:
  - "Document not found: {id}"
  - "Playbook not found: {path}"
```

### 5. `triage_nda`

Run NDA triage screening (10-point checklist).

```
Input:
  document_id: str

Output: TriageResult
  checklist: list[ChecklistResult]
    - item: str
    - status: "PASS" | "FAIL" | "PARTIAL"
    - explanation: str
    - evidence: str | None
  classification: "GREEN" | "YELLOW" | "RED"
  summary: str

Progress:
  ctx.report_progress(0.0–1.0) at each checklist item

Errors:
  - "Document not found: {id}"
```

### 6. `discover_hidden_facts`

LLM-powered discovery of implicit obligations, risks, and hidden facts.

```
Input:
  document_id: str

Output: DiscoveryResult
  discovered_facts: list[DiscoveredFact]
    - fact_text: str
    - category: str
    - severity: str
    - evidence_location: str
    - confidence: float
  summary: str
  categories_found: str

Errors:
  - "Document not found: {id}"
```

### 7. `extract_obligations`

Extract and categorize all contractual obligations.

```
Input:
  document_id: str

Output: ObligationResult
  obligations: list[ObligationItem]
    - obligation: str
    - type: "affirmative" | "negative" | "conditional"
    - party: str
    - clause_reference: str
    - risk_level: "low" | "medium" | "high"
  summary: str
  total_affirmative: int
  total_negative: int
  total_conditional: int

Errors:
  - "Document not found: {id}"
```

### 8. `generate_risk_memo`

Generate a structured risk assessment memo.

```
Input:
  document_id: str

Output: RiskMemoResult
  executive_summary: str
  overall_risk_rating: str
  key_risks: list[RiskItem]
    - risk: str
    - severity: "low" | "medium" | "high" | "critical"
    - clause_reference: str
    - mitigation: str
  missing_protections: list[str]
  recommendations: list[str]
  escalation_items: list[str]

Errors:
  - "Document not found: {id}"
```

### 9. `get_clause_gaps`

Identify mandatory fact gaps per clause type.

```
Input:
  document_id: str

Output: ClauseGapResult
  gaps: list[ClauseGap]
    - clause_type: str
    - clause_heading: str
    - missing_facts: list[str]
    - present_facts: list[str]
  total_gaps: int
  total_clauses: int

Errors:
  - "Document not found: {id}"
```

### 10. `search_contracts`

Semantic search across all indexed contracts.

```
Input:
  query: str
  top_k: int = 5           # Number of results

Output: SearchResult
  query: str
  results: list[SearchHit]
    - document_id: str
    - chunk_text: str
    - score: float
    - clause_type: str | None
    - section: str | None
  total_documents_searched: int

Errors:
  - "No contracts indexed."
```

### 11. `compare_clauses`

Compare specific clause types across two contracts.

```
Input:
  document_id_1: str
  document_id_2: str
  clause_type: str          # e.g., "termination", "indemnification", "liability"

Output: ComparisonResult
  clause_type: str
  contract_1_id: str
  contract_2_id: str
  differences: list[ClauseDifference]
    - aspect: str
    - contract_1: str
    - contract_2: str
    - significance: "minor" | "moderate" | "major"
  summary: str
  recommendation: str

Errors:
  - "Document not found: {id}"
  - "Clause type '{type}' not found in document {id}"
```

### 12. `generate_report`

Generate an HTML report for a completed analysis.

```
Input:
  document_id: str
  report_type: "review" | "triage" | "discovery"

Output: ReportResult
  html_content: str
  report_type: str
  document_id: str
  generated_at: str

Errors:
  - "Document not found: {id}"
  - "No {type} analysis found for document {id}. Run the analysis first."
```

### 13. `clear_workspace`

Clear all uploaded contracts, facts, and analysis data.

```
Input: (none)

Output:
  message: str              # "Workspace cleared. All contracts and analysis data removed."
  contracts_removed: int
  facts_removed: int
```

---

## Resources

### `contractos://contracts`
```
Returns: JSON array of Contract objects
  [{ "document_id": "...", "filename": "...", "uploaded_at": "...", "fact_count": N, ... }]
```

### `contractos://contracts/{id}`
```
Returns: JSON Contract object with full metadata
```

### `contractos://contracts/{id}/facts`
```
Returns: JSON array of Fact objects
  [{ "fact_id": "...", "fact_type": "...", "value": "...", "evidence": {...}, ... }]
```

### `contractos://contracts/{id}/clauses`
```
Returns: JSON array of Clause objects
  [{ "clause_id": "...", "clause_type": "...", "heading": "...", "text": "...", ... }]
```

### `contractos://contracts/{id}/bindings`
```
Returns: JSON array of Binding objects
  [{ "term": "...", "resolves_to": "...", "scope": "...", "binding_type": "...", ... }]
```

### `contractos://contracts/{id}/graph`
```
Returns: JSON object with TrustGraph
  { "nodes": [...], "edges": [...] }
```

### `contractos://samples`
```
Returns: JSON array from manifest.json
  [{ "filename": "...", "title": "...", "description": "...", "complexity": "..." }]
```

### `contractos://chat/history`
```
Returns: JSON array of chat sessions
  [{ "session_id": "...", "question": "...", "answer": "...", "timestamp": "..." }]
```

### `contractos://health`
```
Returns: JSON health status
  { "status": "ok", "version": "0.1.0", "contracts_indexed": N, "embedding_model": "..." }
```

### `contractos://playbook`
```
Returns: JSON PlaybookConfig
  { "positions": [...], "negotiation_tiers": [...] }
```

---

## Prompts

### `full_contract_analysis`
```
Parameters: document_id (str)
Returns: Message[] guiding the AI through: upload → triage → review → obligations → risk memo
```

### `due_diligence_checklist`
```
Parameters: document_id (str)
Returns: Message[] with structured due diligence template
```

### `negotiation_prep`
```
Parameters: document_id (str)
Returns: Message[] preparing negotiation strategy from review findings
```

### `risk_summary`
```
Parameters: document_id (str)
Returns: Message[] for executive risk briefing
```

### `clause_comparison`
```
Parameters: doc_id_1 (str), doc_id_2 (str), clause_type (str)
Returns: Message[] for structured clause comparison
```

---

## Transport Configuration

### stdio (Local — Cursor / Claude Desktop)

```json
// .cursor/mcp.json
{
  "mcpServers": {
    "contractos": {
      "command": "python",
      "args": ["-m", "contractos.mcp.server"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-...",
        "ANTHROPIC_BASE_URL": "https://litellm-qc.zycus.net/",
        "ANTHROPIC_MODEL": "claude-sonnet-4-5-global"
      }
    }
  }
}
```

### Streamable HTTP (Remote — Docker / VDI)

```json
// .cursor/mcp.json
{
  "mcpServers": {
    "contractos": {
      "url": "http://<host>:8743/mcp"
    }
  }
}
```

### Docker Compose Addition

```yaml
services:
  contractos-mcp:
    build: .
    command: ["python", "-m", "contractos.mcp.server", "--transport", "http", "--port", "8743"]
    ports:
      - "8743:8743"
    env_file: .env
    volumes:
      - contractos-data:/data/.contractos
```
