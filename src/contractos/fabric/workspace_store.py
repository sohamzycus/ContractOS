"""WorkspaceStore — SQLite-backed persistence for workspaces and reasoning sessions."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from contractos.models.workspace import ReasoningSession, SessionStatus, Workspace


class WorkspaceStore:
    """SQLite-backed storage for workspaces and reasoning sessions.

    Shares the same database connection as TrustGraph (same schema).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    # ── Workspace CRUD ─────────────────────────────────────────────

    def create_workspace(self, workspace: Workspace) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO workspaces
               (workspace_id, name, indexed_documents, created_at, last_accessed_at, settings)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                workspace.workspace_id, workspace.name,
                json.dumps(workspace.indexed_documents),
                workspace.created_at.isoformat(),
                workspace.last_accessed_at.isoformat(),
                json.dumps(workspace.settings),
            ),
        )
        self._conn.commit()

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        row = self._conn.execute(
            "SELECT * FROM workspaces WHERE workspace_id = ?", (workspace_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_workspace(row)

    def list_workspaces(self) -> list[Workspace]:
        rows = self._conn.execute(
            "SELECT * FROM workspaces ORDER BY last_accessed_at DESC"
        ).fetchall()
        return [self._row_to_workspace(r) for r in rows]

    def update_last_accessed(self, workspace_id: str, ts: datetime | None = None) -> None:
        ts = ts or datetime.now()
        self._conn.execute(
            "UPDATE workspaces SET last_accessed_at = ? WHERE workspace_id = ?",
            (ts.isoformat(), workspace_id),
        )
        self._conn.commit()

    def add_document_to_workspace(self, workspace_id: str, document_id: str) -> None:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            msg = f"Workspace {workspace_id} not found"
            raise ValueError(msg)
        if document_id not in ws.indexed_documents:
            ws.indexed_documents.append(document_id)
            self._conn.execute(
                "UPDATE workspaces SET indexed_documents = ? WHERE workspace_id = ?",
                (json.dumps(ws.indexed_documents), workspace_id),
            )
            self._conn.commit()

    def remove_document_from_workspace(self, workspace_id: str, document_id: str) -> None:
        ws = self.get_workspace(workspace_id)
        if ws is None:
            msg = f"Workspace {workspace_id} not found"
            raise ValueError(msg)
        if document_id in ws.indexed_documents:
            ws.indexed_documents.remove(document_id)
            self._conn.execute(
                "UPDATE workspaces SET indexed_documents = ? WHERE workspace_id = ?",
                (json.dumps(ws.indexed_documents), workspace_id),
            )
            self._conn.commit()

    def delete_workspace(self, workspace_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM workspaces WHERE workspace_id = ?", (workspace_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def _row_to_workspace(self, row: sqlite3.Row) -> Workspace:
        return Workspace(
            workspace_id=row["workspace_id"],
            name=row["name"],
            indexed_documents=json.loads(row["indexed_documents"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed_at=datetime.fromisoformat(row["last_accessed_at"]),
            settings=json.loads(row["settings"]),
        )

    # ── ReasoningSession CRUD ──────────────────────────────────────

    def create_session(self, session: ReasoningSession) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO reasoning_sessions
               (session_id, workspace_id, query_text, query_scope,
                target_document_ids, answer, answer_type, confidence,
                status, started_at, completed_at, generation_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.session_id, session.workspace_id, session.query_text,
                session.query_scope,
                json.dumps(session.target_document_ids),
                session.answer, session.answer_type, session.confidence,
                session.status.value, session.started_at.isoformat(),
                session.completed_at.isoformat() if session.completed_at else None,
                session.generation_time_ms,
            ),
        )
        self._conn.commit()

    def get_session(self, session_id: str) -> ReasoningSession | None:
        row = self._conn.execute(
            "SELECT * FROM reasoning_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    def get_sessions_by_workspace(self, workspace_id: str) -> list[ReasoningSession]:
        rows = self._conn.execute(
            "SELECT * FROM reasoning_sessions WHERE workspace_id = ? ORDER BY started_at DESC",
            (workspace_id,),
        ).fetchall()
        return [self._row_to_session(r) for r in rows]

    def complete_session(
        self,
        session_id: str,
        answer: str,
        answer_type: str,
        confidence: float | None,
        generation_time_ms: int,
    ) -> None:
        now = datetime.now()
        self._conn.execute(
            """UPDATE reasoning_sessions
               SET answer = ?, answer_type = ?, confidence = ?,
                   status = ?, completed_at = ?, generation_time_ms = ?
               WHERE session_id = ?""",
            (
                answer, answer_type, confidence,
                SessionStatus.COMPLETED.value, now.isoformat(),
                generation_time_ms, session_id,
            ),
        )
        self._conn.commit()

    def fail_session(self, session_id: str, error_message: str) -> None:
        now = datetime.now()
        self._conn.execute(
            """UPDATE reasoning_sessions
               SET answer = ?, status = ?, completed_at = ?
               WHERE session_id = ?""",
            (error_message, SessionStatus.FAILED.value, now.isoformat(), session_id),
        )
        self._conn.commit()

    def _row_to_session(self, row: sqlite3.Row) -> ReasoningSession:
        return ReasoningSession(
            session_id=row["session_id"],
            workspace_id=row["workspace_id"],
            query_text=row["query_text"],
            query_scope=row["query_scope"],
            target_document_ids=json.loads(row["target_document_ids"]),
            answer=row["answer"],
            answer_type=row["answer_type"],
            confidence=row["confidence"],
            status=SessionStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            generation_time_ms=row["generation_time_ms"],
        )
