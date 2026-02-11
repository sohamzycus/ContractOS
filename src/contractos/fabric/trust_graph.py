"""TrustGraph — SQLite-backed storage for facts, bindings, inferences, and clauses."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from contractos.models.binding import Binding, BindingScope, BindingType
from contractos.models.clause import (
    Clause,
    ClauseTypeEnum,
    CrossReference,
    ReferenceEffect,
    ReferenceType,
)
from contractos.models.clause_type import ClauseFactSlot, SlotStatus
from contractos.models.document import Contract
from contractos.models.fact import EntityType, Fact, FactEvidence, FactType
from contractos.models.inference import Inference, InferenceType

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class TrustGraph:
    """SQLite-backed storage for the ContractOS truth model.

    Provides CRUD operations for facts, bindings, inferences, clauses,
    cross-references, and clause fact slots. Enforces typed outputs.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        schema_sql = _SCHEMA_PATH.read_text()
        self._conn.executescript(schema_sql)

    def close(self) -> None:
        self._conn.close()

    def clear_all_data(self) -> dict[str, int]:
        """Delete ALL data from every table. Returns counts of deleted rows per table."""
        tables = [
            "reasoning_sessions", "clause_fact_slots", "cross_references",
            "clauses", "inferences", "bindings", "facts", "workspaces", "contracts",
        ]
        counts: dict[str, int] = {}
        for table in tables:
            cursor = self._conn.execute(f"DELETE FROM {table}")  # noqa: S608
            counts[table] = cursor.rowcount
        self._conn.commit()
        return counts

    def list_contracts(self) -> list[Contract]:
        """Return all indexed contracts."""
        rows = self._conn.execute(
            "SELECT * FROM contracts ORDER BY indexed_at DESC"
        ).fetchall()
        return [self._row_to_contract(r) for r in rows]

    # ── Contract CRUD ──────────────────────────────────────────────

    def insert_contract(self, contract: Contract) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO contracts
               (document_id, title, file_path, file_format, file_hash, parties,
                effective_date, page_count, word_count, indexed_at, last_parsed_at,
                extraction_version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                contract.document_id, contract.title, contract.file_path,
                contract.file_format, contract.file_hash,
                json.dumps(contract.parties),
                contract.effective_date.isoformat() if contract.effective_date else None,
                contract.page_count, contract.word_count,
                contract.indexed_at.isoformat(), contract.last_parsed_at.isoformat(),
                contract.extraction_version,
            ),
        )
        self._conn.commit()

    def get_contract(self, document_id: str) -> Contract | None:
        row = self._conn.execute(
            "SELECT * FROM contracts WHERE document_id = ?", (document_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_contract(row)

    def _row_to_contract(self, row: sqlite3.Row) -> Contract:
        from datetime import date, datetime
        return Contract(
            document_id=row["document_id"],
            title=row["title"],
            file_path=row["file_path"],
            file_format=row["file_format"],
            file_hash=row["file_hash"],
            parties=json.loads(row["parties"]),
            effective_date=date.fromisoformat(row["effective_date"]) if row["effective_date"] else None,
            page_count=row["page_count"],
            word_count=row["word_count"],
            indexed_at=datetime.fromisoformat(row["indexed_at"]),
            last_parsed_at=datetime.fromisoformat(row["last_parsed_at"]),
            extraction_version=row["extraction_version"],
        )

    # ── Fact CRUD ──────────────────────────────────────────────────

    def insert_fact(self, fact: Fact) -> None:
        ev = fact.evidence
        self._conn.execute(
            """INSERT OR REPLACE INTO facts
               (fact_id, document_id, fact_type, entity_type, value,
                text_span, char_start, char_end, location_hint, structural_path,
                page_number, extraction_method, extracted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fact.fact_id, ev.document_id, fact.fact_type.value,
                fact.entity_type.value if fact.entity_type else None,
                fact.value, ev.text_span, ev.char_start, ev.char_end,
                ev.location_hint, ev.structural_path, ev.page_number,
                fact.extraction_method, fact.extracted_at.isoformat(),
            ),
        )
        self._conn.commit()

    def insert_facts(self, facts: list[Fact]) -> None:
        for fact in facts:
            ev = fact.evidence
            self._conn.execute(
                """INSERT OR REPLACE INTO facts
                   (fact_id, document_id, fact_type, entity_type, value,
                    text_span, char_start, char_end, location_hint, structural_path,
                    page_number, extraction_method, extracted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    fact.fact_id, ev.document_id, fact.fact_type.value,
                    fact.entity_type.value if fact.entity_type else None,
                    fact.value, ev.text_span, ev.char_start, ev.char_end,
                    ev.location_hint, ev.structural_path, ev.page_number,
                    fact.extraction_method, fact.extracted_at.isoformat(),
                ),
            )
        self._conn.commit()

    def get_fact(self, fact_id: str) -> Fact | None:
        row = self._conn.execute(
            "SELECT * FROM facts WHERE fact_id = ?", (fact_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_fact(row)

    def get_facts_by_document(
        self,
        document_id: str,
        fact_type: FactType | str | None = None,
        entity_type: EntityType | str | None = None,
    ) -> list[Fact]:
        query = "SELECT * FROM facts WHERE document_id = ?"
        params: list[Any] = [document_id]
        if fact_type is not None:
            query += " AND fact_type = ?"
            params.append(fact_type.value if hasattr(fact_type, "value") else fact_type)
        if entity_type is not None:
            query += " AND entity_type = ?"
            params.append(entity_type.value if hasattr(entity_type, "value") else entity_type)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_fact(r) for r in rows]

    def count_facts(self, document_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM facts WHERE document_id = ?", (document_id,)
        ).fetchone()
        return row["cnt"] if row else 0

    def delete_facts_by_document(self, document_id: str) -> int:
        cursor = self._conn.execute(
            "DELETE FROM facts WHERE document_id = ?", (document_id,)
        )
        self._conn.commit()
        return cursor.rowcount

    def _row_to_fact(self, row: sqlite3.Row) -> Fact:
        from datetime import datetime
        return Fact(
            fact_id=row["fact_id"],
            fact_type=FactType(row["fact_type"]),
            entity_type=EntityType(row["entity_type"]) if row["entity_type"] else None,
            value=row["value"],
            evidence=FactEvidence(
                document_id=row["document_id"],
                text_span=row["text_span"],
                char_start=row["char_start"],
                char_end=row["char_end"],
                location_hint=row["location_hint"],
                structural_path=row["structural_path"],
                page_number=row["page_number"],
            ),
            extraction_method=row["extraction_method"],
            extracted_at=datetime.fromisoformat(row["extracted_at"]),
        )

    # ── Binding CRUD ───────────────────────────────────────────────

    def insert_binding(self, binding: Binding) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO bindings
               (binding_id, document_id, binding_type, term, resolves_to,
                source_fact_id, scope, is_overridden_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                binding.binding_id, binding.document_id, binding.binding_type.value,
                binding.term, binding.resolves_to, binding.source_fact_id,
                binding.scope.value, binding.is_overridden_by,
            ),
        )
        self._conn.commit()

    def get_binding(self, binding_id: str) -> Binding | None:
        row = self._conn.execute(
            "SELECT * FROM bindings WHERE binding_id = ?", (binding_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_binding(row)

    def get_bindings_by_document(self, document_id: str) -> list[Binding]:
        rows = self._conn.execute(
            "SELECT * FROM bindings WHERE document_id = ?", (document_id,)
        ).fetchall()
        return [self._row_to_binding(r) for r in rows]

    def get_binding_by_term(self, document_id: str, term: str) -> Binding | None:
        row = self._conn.execute(
            "SELECT * FROM bindings WHERE document_id = ? AND LOWER(term) = LOWER(?)",
            (document_id, term),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_binding(row)

    def _row_to_binding(self, row: sqlite3.Row) -> Binding:
        return Binding(
            binding_id=row["binding_id"],
            binding_type=BindingType(row["binding_type"]),
            term=row["term"],
            resolves_to=row["resolves_to"],
            source_fact_id=row["source_fact_id"],
            document_id=row["document_id"],
            scope=BindingScope(row["scope"]),
            is_overridden_by=row["is_overridden_by"],
        )

    # ── Inference CRUD ─────────────────────────────────────────────

    def insert_inference(self, inference: Inference) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO inferences
               (inference_id, document_id, inference_type, claim,
                supporting_fact_ids, supporting_binding_ids, domain_sources,
                reasoning_chain, confidence, confidence_basis,
                generated_by, generated_at, query_id, invalidated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                inference.inference_id, inference.document_id,
                inference.inference_type.value, inference.claim,
                json.dumps(inference.supporting_fact_ids),
                json.dumps(inference.supporting_binding_ids),
                json.dumps(inference.domain_sources),
                inference.reasoning_chain, inference.confidence,
                inference.confidence_basis, inference.generated_by,
                inference.generated_at.isoformat(),
                inference.query_id, inference.invalidated_by,
            ),
        )
        self._conn.commit()

    def get_inferences_by_document(self, document_id: str) -> list[Inference]:
        rows = self._conn.execute(
            "SELECT * FROM inferences WHERE document_id = ?", (document_id,)
        ).fetchall()
        return [self._row_to_inference(r) for r in rows]

    def _row_to_inference(self, row: sqlite3.Row) -> Inference:
        from datetime import datetime
        return Inference(
            inference_id=row["inference_id"],
            inference_type=InferenceType(row["inference_type"]),
            claim=row["claim"],
            supporting_fact_ids=json.loads(row["supporting_fact_ids"]),
            supporting_binding_ids=json.loads(row["supporting_binding_ids"]),
            domain_sources=json.loads(row["domain_sources"]),
            reasoning_chain=row["reasoning_chain"],
            confidence=row["confidence"],
            confidence_basis=row["confidence_basis"],
            generated_by=row["generated_by"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            document_id=row["document_id"],
            query_id=row["query_id"],
            invalidated_by=row["invalidated_by"],
        )

    # ── Clause CRUD ────────────────────────────────────────────────

    def insert_clause(self, clause: Clause) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO clauses
               (clause_id, document_id, clause_type, heading, section_number,
                fact_id, contained_fact_ids, cross_reference_ids,
                classification_method, classification_confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                clause.clause_id, clause.document_id, clause.clause_type.value,
                clause.heading, clause.section_number, clause.fact_id,
                json.dumps(clause.contained_fact_ids),
                json.dumps(clause.cross_reference_ids),
                clause.classification_method, clause.classification_confidence,
            ),
        )
        self._conn.commit()

    def get_clauses_by_document(
        self, document_id: str, clause_type: ClauseTypeEnum | str | None = None
    ) -> list[Clause]:
        query = "SELECT * FROM clauses WHERE document_id = ?"
        params: list[Any] = [document_id]
        if clause_type is not None:
            query += " AND clause_type = ?"
            params.append(clause_type.value if hasattr(clause_type, "value") else clause_type)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_clause(r) for r in rows]

    def _row_to_clause(self, row: sqlite3.Row) -> Clause:
        return Clause(
            clause_id=row["clause_id"],
            document_id=row["document_id"],
            clause_type=ClauseTypeEnum(row["clause_type"]),
            heading=row["heading"],
            section_number=row["section_number"],
            fact_id=row["fact_id"],
            contained_fact_ids=json.loads(row["contained_fact_ids"]),
            cross_reference_ids=json.loads(row["cross_reference_ids"]),
            classification_method=row["classification_method"],
            classification_confidence=row["classification_confidence"],
        )

    # ── CrossReference CRUD ────────────────────────────────────────

    def insert_cross_reference(self, xref: CrossReference) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO cross_references
               (reference_id, source_clause_id, target_reference, target_clause_id,
                reference_type, effect, context, resolved, source_fact_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                xref.reference_id, xref.source_clause_id, xref.target_reference,
                xref.target_clause_id, xref.reference_type.value,
                xref.effect.value, xref.context, int(xref.resolved),
                xref.source_fact_id,
            ),
        )
        self._conn.commit()

    def get_cross_references_by_document(self, document_id: str) -> list[CrossReference]:
        """Get all cross-references for clauses in a document."""
        rows = self._conn.execute(
            """SELECT cr.* FROM cross_references cr
               JOIN clauses c ON cr.source_clause_id = c.clause_id
               WHERE c.document_id = ?""",
            (document_id,),
        ).fetchall()
        return [self._row_to_cross_reference(r) for r in rows]

    def get_cross_references_by_clause(self, clause_id: str) -> list[CrossReference]:
        rows = self._conn.execute(
            "SELECT * FROM cross_references WHERE source_clause_id = ?", (clause_id,)
        ).fetchall()
        return [self._row_to_cross_reference(r) for r in rows]

    def _row_to_cross_reference(self, row: sqlite3.Row) -> CrossReference:
        return CrossReference(
            reference_id=row["reference_id"],
            source_clause_id=row["source_clause_id"],
            target_reference=row["target_reference"],
            target_clause_id=row["target_clause_id"],
            reference_type=ReferenceType(row["reference_type"]),
            effect=ReferenceEffect(row["effect"]),
            context=row["context"],
            resolved=bool(row["resolved"]),
            source_fact_id=row["source_fact_id"],
        )

    # ── ClauseFactSlot CRUD ────────────────────────────────────────

    def insert_clause_fact_slot(self, slot: ClauseFactSlot) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO clause_fact_slots
               (clause_id, fact_spec_name, status, filled_by_fact_id, required)
               VALUES (?, ?, ?, ?, ?)""",
            (
                slot.clause_id, slot.fact_spec_name, slot.status.value,
                slot.filled_by_fact_id, int(slot.required),
            ),
        )
        self._conn.commit()

    def get_clause_fact_slots(self, clause_id: str) -> list[ClauseFactSlot]:
        rows = self._conn.execute(
            "SELECT * FROM clause_fact_slots WHERE clause_id = ?", (clause_id,)
        ).fetchall()
        return [self._row_to_slot(r) for r in rows]

    def get_missing_slots_by_document(self, document_id: str) -> list[ClauseFactSlot]:
        rows = self._conn.execute(
            """SELECT cfs.* FROM clause_fact_slots cfs
               JOIN clauses c ON cfs.clause_id = c.clause_id
               WHERE c.document_id = ? AND cfs.status = 'missing' AND cfs.required = 1""",
            (document_id,),
        ).fetchall()
        return [self._row_to_slot(r) for r in rows]

    def _row_to_slot(self, row: sqlite3.Row) -> ClauseFactSlot:
        return ClauseFactSlot(
            clause_id=row["clause_id"],
            fact_spec_name=row["fact_spec_name"],
            status=SlotStatus(row["status"]),
            filled_by_fact_id=row["filled_by_fact_id"],
            required=bool(row["required"]),
        )
