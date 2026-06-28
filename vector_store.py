"""
Schema vector store using pgvector.

Each table in the connected database gets its own embedding.
At query time we do a cosine similarity search to find the most
relevant tables and pass only those schemas to the LLM — reducing
tokens and improving SQL accuracy.
"""

import json
import re
from typing import List, Tuple, Optional, Dict
import numpy as np
import psycopg2
import psycopg2.extras
import boto3
from botocore.exceptions import ClientError


# Titan Text Embeddings v2 — 1024-dim, works on all Bedrock regions
_DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
_EMBED_DIM = 1024

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ai_analyst_schema_embeddings (
    id            SERIAL PRIMARY KEY,
    db_label      TEXT        NOT NULL,
    table_fqn     TEXT        NOT NULL,   -- e.g. public.disputes
    schema_text   TEXT        NOT NULL,   -- full DDL-like text for this table
    embedding     vector({dim}) NOT NULL,
    indexed_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (db_label, table_fqn)
);

CREATE INDEX IF NOT EXISTS ai_analyst_schema_emb_idx
    ON ai_analyst_schema_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);
""".format(dim=_EMBED_DIM)


class SchemaVectorStore:
    """
    Stores per-table schema embeddings in a pgvector-enabled PostgreSQL database.
    Can be the same Postgres instance used for data, or a separate one.
    """

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        sslmode: str = "prefer",
        # Bedrock credentials for embeddings
        aws_key: str = "",
        aws_secret: str = "",
        aws_region: str = "us-east-1",
        embed_model: str = _DEFAULT_EMBED_MODEL,
    ):
        self._pg_kwargs = dict(
            host=host, port=port, dbname=database,
            user=user, password=password, sslmode=sslmode,
        )
        self._conn: Optional[psycopg2.extensions.connection] = None

        self._bedrock = boto3.client(
            "bedrock-runtime",
            region_name=aws_region,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )
        self.embed_model = embed_model

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._conn = psycopg2.connect(**self._pg_kwargs, connect_timeout=30)
        self._conn.autocommit = True
        self._ensure_schema()

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(_DDL)

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> List[float]:
        """Call Bedrock Titan Embeddings and return a float vector."""
        body = json.dumps({"inputText": text[:8000]})  # Titan max input
        try:
            resp = self._bedrock.invoke_model(
                modelId=self.embed_model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            data = json.loads(resp["body"].read())
            return data["embedding"]
        except ClientError as e:
            raise RuntimeError(f"Embedding error: {e}") from e

    # ── Index schema ──────────────────────────────────────────────────────────

    def index_schema(self, db_label: str, schema_text: str) -> int:
        """
        Parse the full schema string into per-table chunks,
        embed each, and upsert into pgvector.
        Returns the number of tables indexed.
        """
        tables = self._parse_tables(schema_text)
        if not tables:
            return 0

        count = 0
        with self._conn.cursor() as cur:
            for table_fqn, table_text in tables.items():
                vec = self._embed(table_text)
                vec_str = "[" + ",".join(str(v) for v in vec) + "]"
                cur.execute("""
                    INSERT INTO ai_analyst_schema_embeddings
                        (db_label, table_fqn, schema_text, embedding)
                    VALUES (%s, %s, %s, %s::vector)
                    ON CONFLICT (db_label, table_fqn)
                    DO UPDATE SET
                        schema_text = EXCLUDED.schema_text,
                        embedding   = EXCLUDED.embedding,
                        indexed_at  = NOW()
                """, (db_label, table_fqn, table_text, vec_str))
                count += 1
        return count

    def clear(self, db_label: str) -> None:
        """Remove all embeddings for a given db_label."""
        with self._conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ai_analyst_schema_embeddings WHERE db_label = %s",
                (db_label,)
            )

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search(self, db_label: str, question: str, top_k: int = 8) -> str:
        """
        Embed the question, find the top-k most similar table schemas,
        and return them concatenated as a schema string for the LLM.
        """
        vec = self._embed(question)
        vec_str = "[" + ",".join(str(v) for v in vec) + "]"

        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT table_fqn, schema_text,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM ai_analyst_schema_embeddings
                WHERE db_label = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (vec_str, db_label, vec_str, top_k))
            rows = cur.fetchall()

        if not rows:
            return ""

        parts = []
        for row in rows:
            sim = row["similarity"]
            parts.append(
                f"-- Relevance: {sim:.2f}\n{row['schema_text']}"
            )
        return "\n\n".join(parts)

    def list_indexed_tables(self, db_label: str) -> List[Dict]:
        """Return metadata about all indexed tables for a db_label."""
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT table_fqn, indexed_at,
                       LENGTH(schema_text) AS schema_chars
                FROM ai_analyst_schema_embeddings
                WHERE db_label = %s
                ORDER BY table_fqn
            """, (db_label,))
            return [dict(r) for r in cur.fetchall()]

    def count(self, db_label: str) -> int:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM ai_analyst_schema_embeddings WHERE db_label = %s",
                (db_label,)
            )
            return cur.fetchone()[0]

    # ── Schema parser ─────────────────────────────────────────────────────────

    @staticmethod
    def _parse_tables(schema_text: str) -> Dict[str, str]:
        """
        Split the full schema string (produced by any BaseDBClient.get_schema)
        into {table_fqn: table_schema_text} chunks.
        """
        tables: Dict[str, str] = {}
        current_table: Optional[str] = None
        current_lines: List[str] = []

        for line in schema_text.splitlines():
            m = re.match(r"^Table:\s*(.+)$", line.strip())
            if m:
                if current_table and current_lines:
                    tables[current_table] = "\n".join(current_lines)
                current_table = m.group(1).strip().strip("[]").replace("].[", ".")
                current_lines = [line]
            elif current_table:
                current_lines.append(line)

        if current_table and current_lines:
            tables[current_table] = "\n".join(current_lines)

        return tables
