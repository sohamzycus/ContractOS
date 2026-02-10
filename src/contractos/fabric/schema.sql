-- ContractOS TrustGraph Schema
-- Stores facts, bindings, inferences, clauses, cross-references, and clause fact slots.

CREATE TABLE IF NOT EXISTS contracts (
    document_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_format TEXT NOT NULL CHECK (file_format IN ('docx', 'pdf')),
    file_hash TEXT NOT NULL,
    parties TEXT NOT NULL DEFAULT '[]',
    effective_date TEXT,
    page_count INTEGER NOT NULL DEFAULT 0,
    word_count INTEGER NOT NULL DEFAULT 0,
    indexed_at TEXT NOT NULL,
    last_parsed_at TEXT NOT NULL,
    extraction_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES contracts(document_id) ON DELETE CASCADE,
    fact_type TEXT NOT NULL,
    entity_type TEXT,
    value TEXT NOT NULL,
    text_span TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    location_hint TEXT NOT NULL,
    structural_path TEXT NOT NULL,
    page_number INTEGER,
    extraction_method TEXT NOT NULL,
    extracted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_facts_document ON facts(document_id);
CREATE INDEX IF NOT EXISTS idx_facts_type ON facts(fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_entity_type ON facts(entity_type);

CREATE TABLE IF NOT EXISTS bindings (
    binding_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES contracts(document_id) ON DELETE CASCADE,
    binding_type TEXT NOT NULL,
    term TEXT NOT NULL,
    resolves_to TEXT NOT NULL,
    source_fact_id TEXT NOT NULL REFERENCES facts(fact_id),
    scope TEXT NOT NULL DEFAULT 'contract',
    is_overridden_by TEXT REFERENCES bindings(binding_id)
);

CREATE INDEX IF NOT EXISTS idx_bindings_document ON bindings(document_id);
CREATE INDEX IF NOT EXISTS idx_bindings_term ON bindings(term);

CREATE TABLE IF NOT EXISTS inferences (
    inference_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    inference_type TEXT NOT NULL,
    claim TEXT NOT NULL,
    supporting_fact_ids TEXT NOT NULL DEFAULT '[]',
    supporting_binding_ids TEXT NOT NULL DEFAULT '[]',
    domain_sources TEXT NOT NULL DEFAULT '[]',
    reasoning_chain TEXT NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    confidence_basis TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    query_id TEXT,
    invalidated_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_inferences_document ON inferences(document_id);
CREATE INDEX IF NOT EXISTS idx_inferences_confidence ON inferences(confidence);

CREATE TABLE IF NOT EXISTS clauses (
    clause_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES contracts(document_id) ON DELETE CASCADE,
    clause_type TEXT NOT NULL,
    heading TEXT NOT NULL,
    section_number TEXT,
    fact_id TEXT NOT NULL REFERENCES facts(fact_id),
    contained_fact_ids TEXT NOT NULL DEFAULT '[]',
    cross_reference_ids TEXT NOT NULL DEFAULT '[]',
    classification_method TEXT NOT NULL,
    classification_confidence REAL
);

CREATE INDEX IF NOT EXISTS idx_clauses_document ON clauses(document_id);
CREATE INDEX IF NOT EXISTS idx_clauses_type ON clauses(clause_type);

CREATE TABLE IF NOT EXISTS cross_references (
    reference_id TEXT PRIMARY KEY,
    source_clause_id TEXT NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
    target_reference TEXT NOT NULL,
    target_clause_id TEXT REFERENCES clauses(clause_id),
    reference_type TEXT NOT NULL,
    effect TEXT NOT NULL,
    context TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    source_fact_id TEXT NOT NULL REFERENCES facts(fact_id)
);

CREATE INDEX IF NOT EXISTS idx_crossrefs_source ON cross_references(source_clause_id);

CREATE TABLE IF NOT EXISTS clause_fact_slots (
    clause_id TEXT NOT NULL REFERENCES clauses(clause_id) ON DELETE CASCADE,
    fact_spec_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('filled', 'missing', 'partial')),
    filled_by_fact_id TEXT REFERENCES facts(fact_id),
    required INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (clause_id, fact_spec_name)
);

CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    indexed_documents TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    settings TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS reasoning_sessions (
    session_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(workspace_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_scope TEXT NOT NULL,
    target_document_ids TEXT NOT NULL DEFAULT '[]',
    answer TEXT,
    answer_type TEXT,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    generation_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON reasoning_sessions(workspace_id);
