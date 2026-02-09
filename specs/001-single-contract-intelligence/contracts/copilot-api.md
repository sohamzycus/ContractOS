# API Contract: Word Copilot ↔ ContractOS Server

**Communication**: HTTP over localhost (Copilot sidebar → FastAPI server)
**Direction**: Copilot is the client; ContractOS server is the authority

---

## Interaction Flow

```
┌─────────────────────────┐      HTTP / SSE      ┌──────────────────────┐
│    Word Copilot         │◄────────────────────► │  ContractOS Server   │
│    (Office Add-in)      │                       │  (localhost:8742)    │
│                         │                       │                      │
│  - Sidebar UI (React)   │  POST /documents      │  - Document parsing  │
│  - Q&A interface        │  POST /query          │  - Fact extraction   │
│  - Provenance display   │  GET /documents/...   │  - Inference engine  │
│  - Document navigation  │  SSE streaming        │  - TrustGraph        │
│                         │                       │                      │
│  Office JS API:         │                       │                      │
│  - Get document name    │                       │                      │
│  - Get selection        │                       │                      │
│  - Navigate to range    │                       │                      │
└─────────────────────────┘                       └──────────────────────┘
```

---

## Copilot Capabilities (Phase 1)

### Document Context

The Copilot sends document context with every request:

```json
{
  "copilot_context": {
    "document_name": "Dell_IT_Services_Agreement_2024.docx",
    "document_path": "/Users/user/contracts/Dell_IT_Services_Agreement_2024.docx",
    "selection_text": "The Supplier shall indemnify...",
    "selection_range": { "start": 8901, "end": 9234 },
    "cursor_position": 8950,
    "active_workspace_id": "w-123"
  }
}
```

### Provenance Navigation

When the user clicks a fact in the provenance chain:

1. Copilot receives `char_start` and `char_end` from the fact's evidence
2. Uses Office JS API `context.document.body` to navigate to that range
3. Highlights the relevant text span

```typescript
// Simplified — actual Office JS code
async function navigateToFact(charStart: number, charEnd: number) {
  await Word.run(async (context) => {
    const body = context.document.body;
    const range = body.getRange();
    // Use search or range slicing to find the text span
    // Highlight with temporary formatting
  });
}
```

### Session Management

- On document open: Copilot checks if document is already indexed
  (`GET /documents?file_hash=<sha256>`)
- If indexed: Load existing facts and show "Ready" state
- If not indexed: Prompt user to "Analyze this contract" → `POST /documents`
- Session history: Previous Q&A sessions are listed in the sidebar
- Workspace auto-creation: First document creates a default workspace

---

## UI Components (Phase 1)

### Sidebar Layout

```
┌────────────────────────────────┐
│  ContractOS                    │
│  ──────────────────────────    │
│  📄 Dell IT Services 2024     │
│  Status: ✅ Indexed (247 facts)│
│                                │
│  ┌────────────────────────┐    │
│  │ Ask a question...      │    │
│  │                        │    │
│  └────────────────────────┘    │
│                                │
│  ── Recent Questions ──        │
│                                │
│  Q: Does this contract         │
│     indemnify for data breach? │
│  A: Yes. §12.1 establishes... │
│     Confidence: ████░ 0.85     │
│     [View provenance ▼]       │
│                                │
│  Q: What are the payment terms?│
│  A: Net 90 from invoice date   │
│     [View provenance ▼]       │
│                                │
│  ── Document Facts ──          │
│  Parties: ClientCo, Dell       │
│  Effective: 2024-01-15         │
│  Clauses: 14 identified        │
│  Bindings: 18 defined terms    │
└────────────────────────────────┘
```

### Provenance Expansion

When "View provenance" is expanded:

```
┌────────────────────────────────┐
│  Provenance Chain              │
│                                │
│  📌 Fact: §12.1 indemnity     │
│     "losses arising from       │
│     unauthorized access..."    │
│     [Go to clause →]          │
│                                │
│  📌 Binding: "Confidential    │
│     Information" → §1.8 def   │
│     [Go to definition →]     │
│                                │
│  💡 Inference: Data breach =   │
│     unauthorized access to     │
│     confidential info          │
│     Confidence: 0.85           │
│                                │
│  📝 Reasoning:                 │
│  "§12.1 indemnifies against    │
│  unauthorized access to        │
│  Confidential Information      │
│  (defined in §1.8). A data     │
│  breach constitutes such       │
│  access. Therefore..."         │
└────────────────────────────────┘
```

---

## Error Handling

| Scenario | Copilot Behavior |
|----------|-----------------|
| Server not running | "ContractOS is not running. Start the service with `contractos serve`" |
| LLM unavailable | "AI reasoning unavailable. Document facts and bindings are still accessible." |
| Document not supported | "This file format is not supported. ContractOS works with .docx and .pdf files." |
| Parsing in progress | Show progress bar with estimated time |
| Query timeout (>30s) | "This is taking longer than expected. [Cancel] [Keep waiting]" |
| Document changed since parse | "This document has been modified. [Re-analyze] [Use cached]" |
