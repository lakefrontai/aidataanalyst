"""
Core AI analyst: orchestrates Mistral (Bedrock) + Microsoft Fabric.

Flow for each user question:
  1. Ensure schema is loaded from Fabric.
  2. Ask Mistral to generate T-SQL.
  3. Execute SQL on Fabric.
  4. Ask Mistral to summarise the results.
  5. Return answer + raw data.
"""

import re
from typing import Dict, List, Optional
import pandas as pd
from tabulate import tabulate

from bedrock_client import BedrockMistralClient
from db_base import BaseDBClient
from config import config


class AnalystSession:
    """Stateful analyst session: maintains conversation history and schema cache."""

    def __init__(self, fabric: BaseDBClient, bedrock: BedrockMistralClient):
        self._fabric = fabric
        self._bedrock = bedrock
        self._history: List[Dict] = []   # rolling chat history for Mistral
        self._schema: str = ""

    # ── Setup ─────────────────────────────────────────────────────────────────

    def load_schema(self, force: bool = False) -> str:
        if not self._schema or force:
            self._schema = self._fabric.get_schema(force_refresh=force)
        return self._schema

    # ── Main entry point ──────────────────────────────────────────────────────

    def ask(self, question: str) -> dict:
        """
        Process a natural-language question and return:
          {
            "question": str,
            "sql": str,
            "data": None,  # type: Optional[pd.DataFrame]
            "answer": str,
            "error": None,  # type: Optional[str]
          }
        """
        self.load_schema()

        result = {
            "question": question,
            "sql": "",
            "data": None,
            "answer": "",
            "error": None,
        }

        # ── 1. Generate SQL ───────────────────────────────────────────────────
        try:
            dialect = getattr(self._fabric, "label", "SQL")
            raw_sql = self._bedrock.generate_sql(
                schema=self._schema,
                question=question,
                dialect=dialect,
                history=self._history[-6:],
            )
            sql = self._clean_sql(raw_sql)
            result["sql"] = sql
        except Exception as e:
            result["error"] = f"SQL generation failed: {e}"
            result["answer"] = result["error"]
            return result

        # ── 2. Execute on Fabric ──────────────────────────────────────────────
        try:
            df = self._fabric.query_df(sql)
            result["data"] = df
        except Exception as e:
            result["error"] = str(e)
            # Ask Mistral to suggest a fix
            try:
                suggestion = self._bedrock.clarify(question, str(e))
                result["answer"] = (
                    f"Query execution failed.\n\nError: {e}\n\n"
                    f"Mistral suggestion:\n{suggestion}"
                )
            except Exception:
                result["answer"] = f"Query execution failed: {e}"
            return result

        # ── 3. Summarise ──────────────────────────────────────────────────────
        result_text = self._df_to_text(df)
        try:
            answer = self._bedrock.summarize_results(question, sql, result_text)
            result["answer"] = answer
        except Exception as e:
            # Still show the data even if summarisation fails
            result["answer"] = f"(Summarisation failed: {e})\n\n{result_text}"

        # ── 4. Update history ─────────────────────────────────────────────────
        self._history.append({"role": "user", "content": question})
        self._history.append({"role": "assistant", "content": result["answer"]})
        # Keep history bounded
        if len(self._history) > 20:
            self._history = self._history[-20:]

        return result

    def general_chat(self, message: str) -> str:
        """Handle non-data questions (general conversation with the analyst)."""
        system = (
            "You are an AI data analyst assistant. You have access to a Microsoft Fabric "
            "data warehouse. Answer the user's question helpfully. If it relates to data, "
            "let them know they can ask data questions and you'll write SQL for them."
        )
        response = self._bedrock.chat(system, message, self._history[-6:])
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "assistant", "content": response})
        return response

    def reset_history(self) -> None:
        self._history = []

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """Strip markdown fences and whitespace from Mistral's SQL output."""
        # Remove ```sql ... ``` or ``` ... ```
        raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
        raw = raw.replace("```", "").strip()
        return raw

    @staticmethod
    def _df_to_text(df: pd.DataFrame) -> str:
        if df.empty:
            return "(No rows returned)"
        truncated = df.attrs.get("truncated", False)
        text = tabulate(df, headers="keys", tablefmt="psql", showindex=False)
        if truncated:
            text += f"\n[Showing first {config.MAX_ROWS_DISPLAY} rows — more rows exist]"
        return text
