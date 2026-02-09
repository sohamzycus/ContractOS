# ContractOS DomainBridge

> The component that connects contract text to real-world meaning.

## What DomainBridge Does

Contracts reference real-world entities — products, services, locations,
organizations, regulations — without using standard taxonomy terms. The
DomainBridge resolves these references into structured knowledge that enables
inference.

**Without DomainBridge**: "Dell Inspiron" is just a string in a table cell.

**With DomainBridge**: "Dell Inspiron" → Laptop → IT Equipment → Hardware,
which means §7.3's maintenance obligation applies to this line item because
it covers "all Hardware" per the definitions.

---

## The Three Knowledge Layers

```
┌─────────────────────────────────────────────────┐
│          CORPUS-DERIVED ONTOLOGY                 │
│  Learned from the contract repository itself     │
│  "Contracts mentioning Inspiron also mention     │
│   IT support 94% of the time"                    │
├─────────────────────────────────────────────────┤
│       ORGANIZATIONAL ONTOLOGY                    │
│  Client-specific category trees, naming          │
│  "Category 7B" → "IT Hardware — End User"        │
├─────────────────────────────────────────────────┤
│         UNIVERSAL ONTOLOGY                       │
│  Pre-built standard taxonomies                   │
│  UNSPSC, CPV, ISO country codes, NAICS           │
└─────────────────────────────────────────────────┘
```

Each layer is independent and additive. A deployment may use all three, two,
or just one, depending on configuration.

### Layer 1: Universal Ontology

Pre-built, industry-standard knowledge:

| Domain | Source | Example Resolution |
|--------|--------|-------------------|
| Products & Services | UNSPSC (United Nations Standard Products and Services Code) | Dell Inspiron 15 → 43211500 (Notebook computers) → IT Equipment |
| Products & Services (EU) | CPV (Common Procurement Vocabulary) | Cloud hosting → 72000000 (IT services) |
| Geography | ISO 3166 + city databases | Bangalore → Karnataka → India; "EMEA" → list of countries |
| Industries | NAICS / SIC codes | "Financial services" → specific industry codes |
| Legal references | Jurisdiction databases | "GDPR" → EU regulation; "UCC" → US commercial code |
| Organizations | Public company/entity databases | "Acme Corp" → parent company, subsidiaries, HQ location |

**Provenance**: Every resolution through universal ontology is tagged:
```
{
  "source": "universal_ontology",
  "taxonomy": "UNSPSC",
  "version": "24.0",
  "path": ["43000000 IT Equipment", "43210000 Computers", "43211500 Notebooks"],
  "confidence": 1.0  // taxonomy match is deterministic
}
```

### Layer 2: Organizational Ontology

Client-specific knowledge, configured per deployment:

| Type | Example |
|------|---------|
| Internal category tree | "Category 7B" → "IT Hardware — End User Computing" |
| Supplier hierarchy | "Dell" → {"Dell Technologies", "Dell EMC", "Dell Services"} |
| Internal location codes | "BLR-01" → "Bangalore Office 1, Floor 3" |
| Policy mapping | "Standard T&Cs v3.2" → specific clause requirements |
| Approved supplier list | "Dell Technologies" → approved for IT Hardware, not for Services |

**Loaded via configuration**:
```yaml
domain:
  organizational:
    source: "client_taxonomy.json"
    refresh: "weekly"
    categories:
      - path: "procurement_categories.csv"
        format: "code,name,parent_code"
      - path: "supplier_hierarchy.json"
        format: "nested_json"
    locations:
      - path: "office_locations.csv"
```

### Layer 3: Corpus-Derived Ontology

Automatically learned from the contract repository:

| Signal | How It's Derived | Example |
|--------|-----------------|---------|
| Co-occurrence | Entities that appear together frequently | "Inspiron" + "maintenance" co-occur in 94% of Dell contracts |
| Implicit categories | Products clustered by contract context | Contracts with "Inspiron", "Latitude", "OptiPlex" all fall under IT Hardware procurement |
| Supplier patterns | Which suppliers provide which services | Dell → IT Hardware + IT Support; not: Consulting |
| Clause patterns | Which clause types appear together | Contracts with SLA clauses also have penalty clauses 87% of the time |

**Built automatically** during contract ingestion. No manual configuration
needed.

**Provenance**:
```
{
  "source": "corpus_derived",
  "method": "co_occurrence_analysis",
  "corpus_size": 2847,
  "support": 0.94,  // 94% of relevant contracts show this pattern
  "last_computed": "2025-01-15"
}
```

---

## Resolution Protocol

When an agent needs to resolve a reference, the DomainBridge follows this
protocol:

```
1. EXACT MATCH
   Check if the term exists directly in any ontology layer.
   "Dell Inspiron 15" → UNSPSC match → done (confidence: 1.0)

2. FUZZY MATCH
   If no exact match, try normalized/fuzzy matching.
   "Dell Inspiron" (no model number) → closest UNSPSC match
   (confidence: 0.95)

3. ORGANIZATIONAL CONTEXT
   Check organizational ontology for client-specific resolution.
   "Category 7B" → client's internal mapping → done (confidence: 1.0)

4. CORPUS INFERENCE
   Check corpus-derived patterns.
   "XYZ-9000" (unknown product) → appears in contracts alongside
   IT equipment → likely IT equipment (confidence: 0.75)

5. LLM-ASSISTED RESOLUTION
   If all else fails, use LLM with constrained prompt:
   "Given the context [surrounding text], what product/service
   category does 'XYZ-9000' most likely belong to?
   Choose from: [ontology categories]"
   (confidence: 0.60, flagged for review)

6. UNRESOLVED
   If nothing matches with sufficient confidence:
   Return: "Unable to resolve 'XYZ-9000' to a known category"
   Flag for human resolution.
   Do NOT guess.
```

### Confidence by Resolution Method

| Method | Confidence | Rationale |
|--------|-----------|-----------|
| Exact match (universal) | 1.0 | Taxonomy is deterministic |
| Exact match (organizational) | 1.0 | Client-defined mapping |
| Fuzzy match (universal) | 0.90–0.95 | Minor normalization uncertainty |
| Corpus-derived | 0.70–0.90 | Statistical, depends on support |
| LLM-assisted | 0.50–0.70 | Non-deterministic, needs review |
| Unresolved | 0.0 | No resolution available |

---

## External Knowledge Boundary

### The Critical Rule

ContractOS uses external knowledge but **never presents external knowledge as
document-grounded fact**.

Every piece of external knowledge is:
1. **Declared** — the source is explicit in the provenance chain
2. **Typed** — marked as `source: external` vs `source: document`
3. **Auditable** — a reviewer can see exactly where external knowledge
   was injected
4. **Configurable** — organizations can restrict which external sources
   are allowed

### What External Knowledge Can Do

- Resolve product/service categories (Dell Inspiron → IT Equipment)
- Resolve geography (Bangalore → India)
- Provide industry benchmarks (average payment terms for IT procurement)
- Identify regulatory frameworks (GDPR applicability by jurisdiction)
- Map organization structures (parent-subsidiary relationships)

### What External Knowledge Cannot Do

- Override a document-grounded fact
- Create a fact (external knowledge produces inferences, never facts)
- Be used without declaration in the provenance chain
- Be treated as having the same certainty as document text

### Example in Provenance Chain

```
Inference: "This contract covers IT Equipment maintenance in India"
├── Fact: Schedule A lists "Dell Inspiron 15" [document: contract-001, §A.3]
├── External: Dell Inspiron 15 → IT Equipment [source: UNSPSC v24.0]    ← DECLARED
├── Fact: Schedule B lists "Bangalore, Pune, Mumbai" [document: contract-001, §B.2]
├── External: Bangalore, Pune, Mumbai → India [source: ISO 3166]        ← DECLARED
└── Confidence: 0.92 (high — facts are solid; external mappings are standard)
```

---

## Multi-Language Support

DomainBridge operates across languages by:

1. **Term normalization** — map non-English terms to canonical forms
   before ontology lookup
2. **Multi-language ontologies** — UNSPSC and CPV have official translations
3. **Transliteration handling** — "बैंगलोर" / "Bengaluru" / "Bangalore"
   all resolve to the same entity
4. **Context-aware language detection** — mixed-language contracts
   (common in global procurement) are handled per-section

---

## DomainBridge Configuration

```yaml
domain_bridge:
  universal:
    enabled: true
    sources:
      - type: "unspsc"
        version: "24.0"
        path: "ontologies/unspsc_v24.json"
      - type: "geography"
        source: "iso_3166"
        extended: true  # includes cities, not just countries
      - type: "legal_references"
        jurisdictions: ["US", "EU", "IN", "UK"]
  
  organizational:
    enabled: true
    sources:
      - type: "categories"
        path: "client_data/procurement_categories.csv"
      - type: "suppliers"
        path: "client_data/supplier_hierarchy.json"
      - type: "locations"
        path: "client_data/office_locations.csv"
    refresh_interval: "weekly"
  
  corpus_derived:
    enabled: true
    min_support: 0.70        # minimum co-occurrence threshold
    rebuild_interval: "daily"
    min_corpus_size: 50      # need at least 50 contracts for patterns
  
  llm_fallback:
    enabled: true
    max_confidence: 0.70     # LLM resolutions capped at 0.70
    require_review: true     # flag for human confirmation
  
  unresolved_behavior: "flag_and_skip"  # never guess silently
```
