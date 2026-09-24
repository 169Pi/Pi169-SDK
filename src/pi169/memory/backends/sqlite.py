from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Sequence

from ..models import (
    Memory,
    MemoryQuery,
    MemoryResult,
    Message,
    Session,
)
from ..storage import (
    MemoryNotFoundError,
    SessionNotFoundError,
    StorageBackend,
)


class SQLiteStorage(StorageBackend):
    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Storage not initialized.")
        return self._conn

    def initialize(self) -> None:
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON;")

        self._create_schema()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions(
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0,
                summary TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS messages(
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                turn_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                token_count INTEGER,
                metadata TEXT,

                FOREIGN KEY(session_id)
                REFERENCES sessions(session_id)
                ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memory_items(
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                source_message_id TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_accessed_at TEXT,
                access_count INTEGER DEFAULT 0,

                content_hash TEXT NOT NULL,

                embedding_model TEXT NOT NULL,
                embedding_dimension INTEGER NOT NULL,
                embedding_version TEXT NOT NULL,

                metadata TEXT,

                FOREIGN KEY(session_id)
                REFERENCES sessions(session_id)
                ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id);

            CREATE INDEX IF NOT EXISTS idx_messages_sequence
            ON messages(session_id, sequence);

            CREATE INDEX IF NOT EXISTS idx_memory_session
            ON memory_items(session_id);

            CREATE INDEX IF NOT EXISTS idx_memory_hash
            ON memory_items(session_id, content_hash);
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, session: Session) -> Session:
        self.conn.execute(
            """
            INSERT INTO sessions VALUES(?,?,?,?,?,?)
            """,
            (
                session.session_id,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.message_count,
                session.summary,
                json.dumps(session.metadata),
            ),
        )
        return session

    def get_session(self, session_id: str) -> Session | None:
        row = self.conn.execute(
            "SELECT * FROM sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()

        if row is None:
            return None

        return Session.from_sqlite(row)

    def update_session(self, session: Session) -> Session:
        cursor = self.conn.execute(
            """
            UPDATE sessions
            SET updated_at=?,
                message_count=?,
                summary=?,
                metadata=?
            WHERE session_id=?
            """,
            (
                session.updated_at.isoformat(),
                session.message_count,
                session.summary,
                json.dumps(session.metadata),
                session.session_id,
            ),
        )

        if cursor.rowcount == 0:
            raise SessionNotFoundError(session.session_id)

        return session

    def delete_session(self, session_id: str) -> None:
        self.conn.execute(
            "DELETE FROM sessions WHERE session_id=?",
            (session_id,),
        )

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def add_message(self, message: Message) -> Message:
        self.conn.execute(
            """
            INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                message.id,
                message.session_id,
                message.turn_id,
                message.role,
                message.content,
                message.sequence,
                message.created_at.isoformat(),
                message.token_count,
                json.dumps(message.metadata),
            ),
        )

        self.conn.execute(
            """
            UPDATE sessions
            SET message_count = message_count + 1
            WHERE session_id=?
            """,
            (message.session_id,),
        )

        return message

    def get_message(self, message_id: str):
        row = self.conn.execute(
            "SELECT * FROM messages WHERE id=?",
            (message_id,),
        ).fetchone()

        return None if row is None else Message.from_sqlite(row)

    def get_messages(
        self,
        session_id: str,
        *,
        limit=None,
        before_sequence=None,
        after_sequence=None,
    ):
        query = "SELECT * FROM messages WHERE session_id=?"
        params = [session_id]

        if before_sequence is not None:
            query += " AND sequence < ?"
            params.append(before_sequence)

        if after_sequence is not None:
            query += " AND sequence > ?"
            params.append(after_sequence)

        query += " ORDER BY sequence ASC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(query, params).fetchall()

        return [Message.from_sqlite(r) for r in rows]

    def delete_message(self, message_id: str) -> None:
        self.conn.execute(
            "DELETE FROM messages WHERE id=?",
            (message_id,),
        )

    # ------------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------------

    def add_memory(self, memory: Memory) -> Memory:
        self.conn.execute(
            """
            INSERT INTO memory_items VALUES(
                ?,?,?,?,?,?,?,?,?,?,?,?,?
            )
            """,
            (
                memory.id,
                memory.session_id,
                memory.content,
                memory.memory_type,
                memory.source_message_id,
                memory.created_at.isoformat(),
                memory.updated_at.isoformat(),
                memory.last_accessed_at.isoformat()
                if memory.last_accessed_at
                else None,
                memory.access_count,
                memory.content_hash,
                memory.embedding_model,
                memory.embedding_dimension,
                memory.embedding_version,
                json.dumps(memory.metadata),
            ),
        )

        return memory

    def get_memory(self, memory_id: str):
        row = self.conn.execute(
            "SELECT * FROM memory_items WHERE id=?",
            (memory_id,),
        ).fetchone()

        return None if row is None else Memory.from_sqlite(row)

    def update_memory(self, memory: Memory):
        cursor = self.conn.execute(
            """
            UPDATE memory_items
            SET content=?,
                updated_at=?,
                last_accessed_at=?,
                access_count=?,
                metadata=?
            WHERE id=?
            """,
            (
                memory.content,
                memory.updated_at.isoformat(),
                memory.last_accessed_at.isoformat()
                if memory.last_accessed_at
                else None,
                memory.access_count,
                json.dumps(memory.metadata),
                memory.id,
            ),
        )

        if cursor.rowcount == 0:
            raise MemoryNotFoundError(memory.id)

        return memory

    def delete_memory(self, memory_id: str) -> None:
        self.conn.execute(
            "DELETE FROM memory_items WHERE id=?",
            (memory_id,),
        )

    def get_memories(
        self,
        session_id: str,
        *,
        limit=None,
        memory_type=None,
    ):
        query = "SELECT * FROM memory_items WHERE session_id=?"
        params = [session_id]

        if memory_type:
            query += " AND memory_type=?"
            params.append(memory_type)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        rows = self.conn.execute(query, params).fetchall()

        return [Memory.from_sqlite(r) for r in rows]

    def search_memories(
        self,
        query: MemoryQuery,
    ):
        """
        Storage-level filtering only.

        Semantic search happens in FAISS.
        """
        memories = self.get_memories(
            session_id=query.session_id,
            limit=query.limit,
            memory_type=query.memory_type,
        )

        return [
            MemoryResult(memory=m, score=0.0)
            for m in memories
        ]

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    def get_memories_by_ids(
        self,
        memory_ids: Sequence[str],
    ):
        if not memory_ids:
            return []

        placeholders = ",".join("?" * len(memory_ids))

        rows = self.conn.execute(
            f"""
            SELECT * FROM memory_items
            WHERE id IN ({placeholders})
            """,
            tuple(memory_ids),
        ).fetchall()

        mapping = {
            r["id"]: Memory.from_sqlite(r)
            for r in rows
        }

        # Preserve FAISS ordering
        return [
            mapping[mid]
            for mid in memory_ids
            if mid in mapping
        ]

    def delete_memories_by_session(
        self,
        session_id: str,
    ):
        self.conn.execute(
            """
            DELETE FROM memory_items
            WHERE session_id=?
            """,
            (session_id,),
        )

    def get_all_memories(
        self,
        *,
        session_id=None,
    ):
        if session_id:
            rows = self.conn.execute(
                """
                SELECT * FROM memory_items
                WHERE session_id=?
                """,
                (session_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM memory_items"
            ).fetchall()

        return [Memory.from_sqlite(r) for r in rows]

    # ------------------------------------------------------------------
    # Access tracking
    # ------------------------------------------------------------------

    def mark_memory_accessed(
        self,
        memory_id: str,
    ):
        self.conn.execute(
            """
            UPDATE memory_items
            SET access_count = access_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (memory_id,),
        )

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def begin_transaction(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()