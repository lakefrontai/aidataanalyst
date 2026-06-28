"""AWS Bedrock client — uses Converse API for all Mistral models."""

import re
import json
from typing import Optional, List, Dict
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config import config


class BedrockMistralClient:

    def __init__(self):
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.model_id = config.BEDROCK_MODEL_ID

    # ── Core invoke via Converse API ──────────────────────────────────────────

    def _invoke(
        self,
        system: str,
        messages: List[Dict],
        max_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> str:
        """
        Call Bedrock Converse API — works with all current Mistral models.
        messages: list of {"role": "user"|"assistant", "content": str}
        """
        converse_msgs = [
            {"role": m["role"], "content": [{"text": m["content"]}]}
            for m in messages
            if m["role"] in ("user", "assistant")
        ]

        kwargs = dict(
            modelId=self.model_id,
            messages=converse_msgs,
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        if system:
            kwargs["system"] = [{"text": system}]

        try:
            resp = self._client.converse(**kwargs)
            return resp["output"]["message"]["content"][0]["text"].strip()
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not found.")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg  = e.response["Error"]["Message"]
            raise RuntimeError(f"Bedrock error [{code}]: {msg}") from e

    # ── Public helpers ────────────────────────────────────────────────────────

    def chat(self, system: str, user: str, history: Optional[List[Dict]] = None) -> str:
        msgs: List[Dict] = []
        if history:
            msgs.extend([m for m in history if m["role"] in ("user", "assistant")])
        msgs.append({"role": "user", "content": user})
        return self._invoke(system, msgs)

    def generate_sql(self, schema: str, question: str, dialect: str = "PostgreSQL",
                     history: Optional[List[Dict]] = None) -> str:
        system = (
            f"You are an expert {dialect} SQL developer and data analyst.\n"
            "Your ONLY job is to output a single valid SQL SELECT query — nothing else.\n\n"
            "STRICT RULES — violating any rule makes the response wrong:\n"
            "1. Output ONLY the raw SQL query. No explanations. No markdown. No code fences. No apologies.\n"
            "2. The first character of your response MUST be S (from SELECT) or W (from WITH).\n"
            "3. Never say 'I', 'I'm', 'Unable', 'cannot', or any English prose.\n"
            "4. If you are unsure, write your best guess at a SELECT query anyway.\n"
            "5. Never use DROP, DELETE, UPDATE, INSERT, CREATE, ALTER, or TRUNCATE.\n"
            "6. Always use the exact table and column names from the schema below.\n"
            "7. Qualify every column with its table alias.\n\n"
            f"DATABASE SCHEMA:\n{schema}"
        )
        raw = self.chat(system, question, history)
        return self._clean_sql(raw)

    def summarize_results(self, question: str, sql: str, result_text: str) -> str:
        system = (
            "You are a helpful data analyst. Summarize the query results in clear natural language. "
            "Highlight key numbers, trends, or anomalies. Be concise."
        )
        user = (
            f"Question: {question}\n\n"
            f"SQL run:\n{sql}\n\n"
            f"Results:\n{result_text}"
        )
        return self.chat(system, user)

    def clarify(self, question: str, error: str) -> str:
        system = (
            "You are a SQL debugging assistant. "
            "Explain the error cause in one sentence, then provide a corrected SQL query."
        )
        return self.chat(system, f"Question: {question}\nError: {error}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """Strip markdown fences and any leading prose before the first SELECT/WITH."""
        raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
        raw = raw.replace("```", "").strip()
        # Find the first SELECT or WITH keyword and trim anything before it
        match = re.search(r"\b(SELECT|WITH)\b", raw, re.IGNORECASE)
        if match:
            raw = raw[match.start():]
        return raw.strip()
