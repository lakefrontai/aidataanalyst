"""
Core AI analyst: orchestrates Mistral (Bedrock) + database + optional vector store.

Flow for each user question:
  1. If vector store is available → embed question → retrieve relevant table schemas.
     Otherwise fall back to full schema.
  2. Ask Mistral to generate SQL.
  3. Execute SQL on the database.
  4. Ask Mistral to summarise the results.
"""

import re
from typing import Dict, List
import pandas as pd
from tabulate import tabulate

from bedrock_client import BedrockMistralClient
from db_base import BaseDBClient
from config import config


class AnalystSession:
    """Stateful analyst session with optional pgvector-backed schema retrieval."""

    def __init__(
        self,
        db: BaseDBClient,
        bedrock: BedrockMistralClient,
        vector_store=None,   # SchemaVectorStore | None
    ):
        self._db      = db
        self._fabric  = db   # backwards-compat alias used internally
        self._bedrock = bedrock
        self._vs      = vector_store
        self._history: List[Dict] = []
        self._schema:  str = ""

    # ── Schema loading ────────────────────────────────────────────────────────

    def load_schema(self, force: bool = False) -> str:
        """Load and cache the full database schema; re-fetch if force=True."""
        if not self._schema or force:
            self._schema = self._db.get_schema(force_refresh=force)
        return self._schema

    def set_vector_store(self, vs) -> None:
        """Attach a SchemaVectorStore for semantic table retrieval."""
        self._vs = vs

    # ── Schema retrieval ──────────────────────────────────────────────────────

    def _get_relevant_schema(self, question: str) -> str:
        """
        If a vector store is configured, retrieve only the relevant table schemas.
        Falls back to the full schema if vector store is unavailable.
        """
        if self._vs:
            db_label = getattr(self._db, "label", "db")
            try:
                retrieved = self._vs.search(db_label, question, top_k=8)
                if retrieved:
                    return retrieved
            except Exception:
                pass  # fall through to full schema
        return self._schema

    # ── Main entry point ──────────────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        """Run the full analyst pipeline: schema → SQL → execute → summarise."""
        self.load_schema()

        result: Dict = {
            "question": question,
            "sql":      "",
            "data":     None,
            "answer":   "",
            "error":    None,
            "schema_source": "vector" if self._vs else "full",
        }

        # ── 1. Retrieve schema (vector or full) ───────────────────────────────
        schema = self._get_relevant_schema(question)

        # ── 2. Generate SQL ───────────────────────────────────────────────────
        try:
            dialect = getattr(self._db, "label", "SQL")
            raw_sql = self._bedrock.generate_sql(
                schema=schema,
                question=question,
                dialect=dialect,
                history=self._history[-6:],
            )
            sql = self._clean_sql(raw_sql)
            result["sql"] = sql
        except Exception as e:
            result["error"]  = f"SQL generation failed: {e}"
            result["answer"] = result["error"]
            return result

        # ── 3. Execute ────────────────────────────────────────────────────────
        try:
            df = self._db.query_df(sql)
            result["data"] = df
        except Exception as e:
            result["error"] = str(e)
            try:
                suggestion = self._bedrock.clarify(question, str(e))
                result["answer"] = (
                    f"Query execution failed.\n\nError: {e}\n\n"
                    f"Suggestion:\n{suggestion}"
                )
            except Exception:
                result["answer"] = f"Query execution failed: {e}"
            return result

        # ── 4. Summarise ──────────────────────────────────────────────────────
        result_text = self._df_to_text(result["data"])
        try:
            result["answer"] = self._bedrock.summarize_results(
                question, sql, result_text
            )
        except Exception as e:
            result["answer"] = f"(Summarisation failed: {e})\n\n{result_text}"

        # ── 5. Update history ─────────────────────────────────────────────────
        self._history.append({"role": "user",      "content": question})
        self._history.append({"role": "assistant", "content": result["answer"]})
        if len(self._history) > 20:
            self._history = self._history[-20:]

        return result

    def general_chat(self, message: str) -> str:
        """Answer a general (non-SQL) question using the Bedrock model."""
        system = (
            "You are an AI data analyst assistant. Answer helpfully. "
            "If the question is about data, let the user know they can ask "
            "data questions and you will write SQL for them."
        )
        response = self._bedrock.chat(system, message, self._history[-6:])
        self._history.append({"role": "user",      "content": message})
        self._history.append({"role": "assistant", "content": response})
        return response

    def reset_history(self) -> None:
        """Clear the conversation history."""
        self._history = []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_sql(raw: str) -> str:
        raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
        raw = raw.replace("```", "").strip()
        match = re.search(r"\b(SELECT|WITH)\b", raw, re.IGNORECASE)
        if match:
            raw = raw[match.start():]
        return raw.strip()

    @staticmethod
    def _df_to_text(df: pd.DataFrame) -> str:
        if df is None or df.empty:
            return "(No rows returned)"
        text = tabulate(df, headers="keys", tablefmt="psql", showindex=False)
        if df.attrs.get("truncated"):
            text += f"\n[Showing first {config.MAX_ROWS_DISPLAY} rows]"
        return text
