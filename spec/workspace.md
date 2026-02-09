# ContractOS Workspace

> Like Cursor remembers your project, ContractOS remembers your contracts.

## Why Workspace Exists

When a procurement professional works with contracts, they don't work with one
document at a time. They work within a **context** — a set of related
documents, a supplier relationship, a category of spend, an ongoing
negotiation.

ContractOS introduces the **Workspace** as a first-class concept: a persistent,
evolving context that remembers:

- Which documents the user is working with
- What questions have been asked before
- What the system has learned about these contracts
- How documents relate to each other

This is directly analogous to how Cursor maintains project context — the user
shouldn't have to re-explain their working set every time they open a document.

---

## Workspace Model

```
Workspace {
  workspace_id:     string
  owner:            string          // user or team
  name:             string          // "Dell IT Services Review"
  created_at:       timestamp
  last_active:      timestamp

  // The working set — documents currently "in context"
  context: {
    active_documents: [DocumentRef]   // explicitly added by user
    discovered_documents: [DocumentRef] // auto-discovered related docs
    pinned_documents: [DocumentRef]   // always in context for this workspace
  }

  // What ContractOS has learned within this workspace
  knowledge: {
    facts_indexed:    int             // facts extracted from context docs
    bindings_resolved: int            // bindings resolved
    inferences_cached: int            // inferences generated
    domain_mappings:  int             // DomainBridge resolutions
  }

  // User preferences for this workspace
  preferences: {
    role:             string          // procurement, legal, audit
    policies:         [string]        // which policy documents apply
    jurisdiction:     string?         // default jurisdiction if applicable
    confidentiality:  enum            // private, team, organization
  }

  // History of reasoning sessions
  sessions:         [ReasoningSession]
}
```

### DocumentRef

```
DocumentRef {
  document_id:      string
  source:           enum            // user_added, auto_discovered,
                                    // family_member, policy_reference
  added_at:         timestamp
  trust_graph_status: enum          // not_indexed, indexing, indexed, stale
  family_role:      string?         // "governing_msa", "active_amendment", etc.
}
```

---

## Context Management

### How Documents Enter the Workspace

**1. User adds explicitly** (like dragging a file into Cursor chat)

The user opens a contract in Word/PDF and invokes the Copilot. The document
enters the workspace's active context.

```
User action: Opens "SOW-2024-003.docx" and starts Copilot
→ ContractOS adds SOW-2024-003 to workspace.context.active_documents
→ If not already indexed, triggers FactExtractor + BindingResolver
→ Triggers auto-discovery (see below)
```

**2. Auto-discovery adds related documents**

When a document enters the workspace, ContractOS searches the ContractGraph
for related documents and adds them automatically.

```
SOW-2024-003 enters workspace
→ ContractGraph discovery finds:
   - MSA-2024-001 (governs this SOW) — confidence 0.95
   - Amendment-001 (amends the MSA) — confidence 0.98
   - Schedule-A (pricing for this SOW) — confidence 0.92
→ All added to workspace.context.discovered_documents
→ User notified: "Found 3 related documents. MSA-2024-001 governs this SOW."
```

**3. User pins documents** (always in context)

For ongoing work, a user can pin documents so they're always included.

```
User: "Always include our Standard Procurement Policy when I'm in this workspace"
→ Policy document pinned to workspace.context.pinned_documents
→ ComplianceAgent automatically checks new documents against it
```

### Context Persistence

The workspace context persists across sessions:

- User closes Word → reopens next day → workspace context is intact
- All facts, bindings, and inferences remain in TrustGraph
- User doesn't need to re-add documents or re-explain context
- New questions can reference prior reasoning sessions

### Context Scope for Queries

When a user asks a question, the query scope is determined by:

```
Query scope resolution:
1. If user specifies scope → use it
   "In this SOW only, what are the payment terms?"
   → scope: single document (SOW-2024-003)

2. If question requires cross-document reasoning → expand to family
   "What are the effective payment terms?"
   → scope: contract family (needs MSA + amendments)

3. If question is repository-level → expand to full repository
   "Find all contracts with similar termination clauses"
   → scope: repository

4. Default → contract family
   Most procurement questions need family context
```

---

## ReasoningSession

A ReasoningSession is the lifecycle of a single query within a workspace.

```
ReasoningSession {
  session_id:       string
  workspace_id:     string
  query:            string          // the user's question
  scope:            enum            // document, family, repository
  status:           enum            // planning, gathering, reasoning,
                                    // assembling, complete, failed

  // Execution plan
  plan: {
    sub_queries:    [SubQuery]      // decomposed questions
    agents_invoked: [string]        // which agents participated
    tools_called:   [ToolCall]      // which tools were executed
  }

  // Results
  result: {
    answer:         string          // synthesized answer
    provenance:     ProvenanceChain // full evidence trail
    confidence:     float           // overall answer confidence
    facts_used:     [string]        // fact_ids
    inferences_made: [string]       // inference_ids
    opinions_generated: [string]    // opinion_ids (if applicable)
  }

  // Timing
  started_at:       timestamp
  completed_at:     timestamp
  duration_ms:      int

  // For streaming / partial results
  partial_results:  [PartialResult]
}
```

### Session Lifecycle

```
User asks: "Does this contract indemnify the buyer for data breach?"

1. PARSE
   QueryPlanner analyzes the question:
   - Intent: indemnity check
   - Entity: "buyer" (needs binding resolution), "data breach"
   - Likely scope: contract family (indemnity may be in MSA)

2. SCOPE
   ScopeResolver determines:
   - Current document: SOW-2024-003
   - Family: MSA-2024-001, Amendment-001, Amendment-002
   - Scope: contract family (indemnity clauses are typically in MSA)

3. GATHER
   DocumentAgent collects from TrustGraph:
   - All facts tagged "indemnity" or "indemnification" across family
   - All bindings for "buyer", "data breach", "loss"
   - Any prior inferences about indemnity in this family

4. REASON
   InferenceEngine + DomainBridge:
   - Resolves "buyer" → binding → "ClientCo Ltd"
   - Finds §12.1 in MSA: indemnification clause
   - Checks if "data breach" is explicitly mentioned
   - If not explicit, checks if "loss arising from unauthorized
     access to data" covers it (inference)
   - Checks Amendment-002 (GDPR clauses) for data-specific provisions
   - Generates inference with confidence

5. JUDGE (if opinion needed)
   ComplianceAgent:
   - Compares indemnity scope against organization's standard
   - Flags if coverage is narrower than expected

6. ASSEMBLE
   Synthesize answer with provenance chain:
   "Yes, §12.1 of the MSA (as amended by Amendment-002) indemnifies
    the buyer for losses arising from data breaches. Specifically..."

7. PRESENT
   Format for Word Copilot:
   - Answer summary
   - Expandable provenance chain
   - Confidence indicator
   - Links to source clauses in documents
```

### Partial Results and Streaming

For complex queries (especially repository-level), results stream as they
become available:

```
User: "Find all contracts with IT equipment maintenance clauses"

Stream:
  t=0.5s  "Searching across 2,847 contracts..."
  t=1.2s  "Found 12 potential matches. Analyzing..."
  t=2.0s  Result 1: Contract-2024-001 (confidence: 0.95) — §7.3 maintenance
  t=2.3s  Result 2: Contract-2023-047 (confidence: 0.92) — §8.1 support
  t=2.8s  Result 3: Contract-2024-112 (confidence: 0.88) — Schedule C
  ...
  t=5.0s  "Complete. Found 8 contracts with IT equipment maintenance clauses."
```

### Scope Escalation

If an agent determines it needs broader context mid-reasoning, it can escalate:

```
User asks about SOW-2024-003: "What's the liability cap?"

DocumentAgent searches SOW... no liability cap found.
→ Scope escalation: check governing MSA
→ MSA-2024-001 §14.2: liability cap of $5M
→ Check amendments... Amendment-001 doesn't modify §14.2
→ Answer: "The liability cap is $5M per §14.2 of the governing MSA.
   The SOW does not define its own cap."
```

The user sees this seamlessly — they don't have to manually say "check the MSA."

---

## Workspace Memory

The workspace accumulates knowledge over time:

### What Is Remembered

| Type | Stored Where | Persistence |
|------|-------------|-------------|
| Extracted facts | TrustGraph | Permanent (until document removed) |
| Resolved bindings | TrustGraph | Permanent |
| Generated inferences | TrustGraph | Until invalidated by new evidence |
| Document relationships | ContractGraph | Permanent |
| DomainBridge resolutions | DomainStore | Cached, refreshable |
| Prior Q&A sessions | SessionStore | Searchable, archivable |
| User preferences | WorkspaceConfig | Persistent |

### What Is NOT Remembered

| Type | Why |
|------|-----|
| Opinions | Computed on demand (truth model rule) |
| LLM conversation context | Stateless agents; context rebuilt from TrustGraph |
| Intermediate reasoning steps | Only final inferences are stored |

### Benefits of Memory

1. **No redundant extraction**: Once a document is indexed, it's never
   re-extracted (unless the document changes)
2. **Faster subsequent queries**: Facts and bindings are already in TrustGraph
3. **Cross-session continuity**: "Last week you asked about the termination
   clause. Since then, Amendment-003 was added. The effective terms have
   changed."
4. **Progressive learning**: Corpus-derived ontology improves as more contracts
   are processed

---

## Multi-User Workspaces

A workspace can be:

- **Personal**: One user's working context
- **Shared**: A team working on the same contract family (e.g., a deal team)
- **Organizational**: Repository-level workspace for analytics

Sharing rules:
- Facts and bindings are always shareable (they're document-grounded)
- Inferences can be shared within confidentiality boundaries
- Sessions (Q&A history) are private by default, shareable by choice
- Opinions depend on the viewer's role and policies
