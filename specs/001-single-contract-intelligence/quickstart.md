# Quickstart: Single-Contract Intelligence

**Audience**: Developer setting up ContractOS Phase 1 locally

---

## Prerequisites

- Python 3.12+
- Node.js 18+ (for Word Copilot add-in)
- An Anthropic API key (for Claude) OR OpenAI API key
- Microsoft Word (desktop, with Add-in support)

## 1. Clone and Install

```bash
git clone https://github.com/<org>/ContractOS.git
cd ContractOS

# Python backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_lg

# Word Copilot add-in
cd copilot
npm install
cd ..
```

## 2. Configure

```bash
# Copy default config
cp config/default.yaml config/local.yaml

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."
# OR for OpenAI:
# export OPENAI_API_KEY="sk-..."
# Then update config/local.yaml: llm.provider: "openai"
```

## 3. Start the Server

```bash
contractos serve --config config/local.yaml
# Server starts at http://127.0.0.1:8742
# Health check: http://127.0.0.1:8742/api/v1/health
```

## 4. Load the Word Add-in

```bash
# In a separate terminal
cd copilot
npm run dev-server
# Follow instructions to sideload the add-in in Word
```

## 5. Try It

1. Open a procurement contract (.docx) in Word
2. Open the ContractOS sidebar (Insert → Add-ins → ContractOS)
3. Click "Analyze this contract"
4. Wait for parsing to complete (~15-30 seconds)
5. Ask: "Who are the parties to this contract?"
6. Ask: "What are the payment terms?"
7. Ask: "Does this contract include an indemnification clause?"
8. Click on any fact in the provenance chain to navigate to the source

## 6. Run via CLI (Alternative)

```bash
# Parse a document
contractos parse /path/to/contract.docx

# Ask a question
contractos query "What are the payment terms?" --document /path/to/contract.docx

# List extracted facts
contractos facts /path/to/contract.docx --type entity

# List bindings
contractos bindings /path/to/contract.docx
```

## 7. Run Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires API key)
pytest tests/integration/ -v

# Benchmark (COBench v0.1)
pytest tests/benchmark/cobench_v01.py -v --benchmark
```

---

## Integration Scenarios

### Scenario 1: First-Time Document Analysis

```
1. User opens contract in Word
2. Copilot detects: document not indexed
3. User clicks "Analyze"
4. Server: POST /documents → 202 Accepted
5. Server: FactExtractor runs → 247 facts
6. Server: BindingResolver runs → 18 bindings
7. Copilot polls: GET /documents/{id} → status: "indexed"
8. Sidebar shows: parties, dates, clause count, binding count
```

### Scenario 2: Returning to a Previously Analyzed Document

```
1. User opens same contract in Word
2. Copilot: GET /documents?file_hash=<sha256>
3. Server: document found, already indexed
4. Copilot: shows previous facts and session history immediately
5. User asks new question → fast response (no re-parsing needed)
```

### Scenario 3: Question with Inference

```
1. User asks: "Does this contract cover IT equipment?"
2. Server:
   a. Search facts for "IT equipment" → no exact match
   b. Search facts for product entities → "Dell Inspiron 15"
   c. Binding: none relevant
   d. InferenceEngine:
      - Fact: Schedule A lists "Dell Inspiron 15"
      - Reasoning: Dell Inspiron is a laptop, which is IT equipment
      - Note: DomainBridge not available in Phase 1, so inference
        is LLM-generated with explicit reasoning chain
      - Confidence: 0.80 (no ontology confirmation)
   e. Return inference + provenance
3. Copilot: displays answer with confidence bar and reasoning chain
```

### Scenario 4: Question with No Answer

```
1. User asks: "What is the force majeure clause?"
2. Server:
   a. Search facts for force majeure clauses → none found
   b. Search all clause headings → no match
   c. Search all text for "force majeure" → no occurrences
   d. Return: "not_found" with searched sections list
3. Copilot: "No force majeure clause found in this contract.
   Searched: all 14 identified clauses and full document text."
```
