# Quickstart: ContractOS MCP Server

**Date**: 2026-02-09

---

## Scenario 1: Local Development with Cursor

### Setup

```bash
# 1. Install MCP dependency
cd /path/to/ContractOS
pip install "mcp[cli]>=1.26.0"

# 2. Verify MCP server starts
PYTHONPATH=src ANTHROPIC_API_KEY=sk-... python -m contractos.mcp.server
# Should print: "ContractOS MCP server running on stdio"
```

### Cursor Configuration

Create `.cursor/mcp.json` in project root:

```json
{
  "mcpServers": {
    "contractos": {
      "command": "python",
      "args": ["-m", "contractos.mcp.server"],
      "env": {
        "PYTHONPATH": "src",
        "ANTHROPIC_API_KEY": "sk-your-key",
        "ANTHROPIC_BASE_URL": "https://litellm-qc.zycus.net/",
        "ANTHROPIC_MODEL": "claude-sonnet-4-5-global"
      }
    }
  }
}
```

### Usage in Cursor Chat

```
User: Load the simple NDA sample and triage it

Cursor (using MCP):
  1. Calls load_sample_contract(filename="simple_nda.pdf")
     → Returns: doc_id="abc123", 45 facts, 12 clauses
  2. Calls triage_nda(document_id="abc123")
     → Returns: 8/10 PASS, 2 PARTIAL, classification=YELLOW
  3. Presents formatted results to user
```

```
User: What are the termination provisions and are they standard?

Cursor (using MCP):
  1. Calls ask_question(question="What are the termination provisions?", document_ids=["abc123"])
     → Returns: answer with provenance pointing to Section 8
  2. Calls review_against_playbook(document_id="abc123")
     → Returns: termination clause finding with severity and redline
  3. Synthesizes answer with source references
```

---

## Scenario 2: Full Contract Analysis Pipeline

```
User: Upload this MSA and give me a complete analysis

Cursor (using MCP):
  1. upload_contract(file_path="/path/to/msa.docx")
     → doc_id, 120 facts, 28 clauses
  2. triage_nda(document_id=doc_id)
     → NDA screening results
  3. review_against_playbook(document_id=doc_id)
     → Compliance findings with redlines
  4. extract_obligations(document_id=doc_id)
     → 45 obligations categorized
  5. generate_risk_memo(document_id=doc_id)
     → Risk assessment with recommendations
  6. discover_hidden_facts(document_id=doc_id)
     → 8 hidden facts discovered
  7. generate_report(document_id=doc_id, report_type="review")
     → HTML report
```

---

## Scenario 3: Cross-Contract Comparison

```
User: Compare the liability clauses between our two vendor contracts

Cursor (using MCP):
  1. Reads contractos://contracts resource to list indexed docs
  2. compare_clauses(doc_id_1="vendor_a", doc_id_2="vendor_b", clause_type="liability")
     → Differences with significance ratings
  3. ask_question(question="Which contract has more favorable liability terms?")
     → Grounded answer with provenance from both docs
```

---

## Scenario 4: Container Deployment (Remote MCP)

> **Container engine agnostic:** Replace `docker compose` with your engine's equivalent:
> - Docker Desktop: `docker compose`
> - Rancher Desktop: `nerdctl compose` (or `docker compose` with Docker CLI compatibility)
> - Podman: `podman-compose` or `podman compose`

### Start

```bash
# Both FastAPI and MCP HTTP run in the same container
docker compose up --build -d

# FastAPI UI:  http://host:8742/demo/copilot.html
# MCP server:  http://host:8743/mcp
```

### Connect from Cursor

```json
{
  "mcpServers": {
    "contractos": {
      "url": "http://your-vdi-host:8743/mcp"
    }
  }
}
```

---

## Scenario 5: Claude Desktop Integration

### Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contractos": {
      "command": "python",
      "args": ["-m", "contractos.mcp.server"],
      "cwd": "/path/to/ContractOS",
      "env": {
        "PYTHONPATH": "src",
        "ANTHROPIC_API_KEY": "sk-your-key",
        "ANTHROPIC_BASE_URL": "https://litellm-qc.zycus.net/",
        "ANTHROPIC_MODEL": "claude-sonnet-4-5-global"
      }
    }
  }
}
```

### Usage

Open Claude Desktop → the ContractOS tools appear in the tools panel. Ask Claude to analyze contracts naturally:

> "I have a procurement contract at ~/Documents/vendor_msa.pdf. Can you upload it and check for any risky clauses?"

Claude will use `upload_contract` → `review_against_playbook` → `discover_hidden_facts` and present a comprehensive analysis.

---

## Scenario 6: Testing with MCP Inspector

```bash
# Start MCP server in HTTP mode
PYTHONPATH=src ANTHROPIC_API_KEY=sk-... python -m contractos.mcp.server --transport http --port 8743

# In another terminal, launch inspector
npx -y @modelcontextprotocol/inspector

# Connect to http://localhost:8743/mcp
# Browse tools, resources, prompts
# Test individual tool calls interactively
```

---

## Verification Checklist

| # | Check | Command |
|---|-------|---------|
| 1 | MCP server starts | `python -m contractos.mcp.server` (no errors) |
| 2 | Tools listed | Inspector shows 13 tools |
| 3 | Resources listed | Inspector shows 10 resources |
| 4 | Prompts listed | Inspector shows 5 prompts |
| 5 | Upload works | Call `upload_contract` with sample PDF |
| 6 | Q&A works | Call `ask_question` after upload |
| 7 | Review works | Call `review_against_playbook` |
| 8 | Triage works | Call `triage_nda` |
| 9 | Cursor integration | `.cursor/mcp.json` loads, tools appear |
| 10 | Docker MCP | `docker compose up`, connect via HTTP |
