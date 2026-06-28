"""Microsoft Fabric SQL Analytics Endpoint client."""

import struct
from typing import List, Optional
import pyodbc
import pandas as pd
import requests

from config import config
from db_base import BaseDBClient

# ODBC driver name — installed by the Microsoft ODBC Driver for SQL Server
_DRIVER = "ODBC Driver 18 for SQL Server"

# Azure AD resource for Fabric SQL endpoints
_FABRIC_RESOURCE = "https://database.windows.net/.default"
_AAD_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


class FabricClient(BaseDBClient):
    label = "Microsoft Fabric"
    """Connects to Microsoft Fabric via its SQL Analytics Endpoint (T-SQL)."""

    def __init__(self):
        self._conn: Optional[pyodbc.Connection] = None
        self._schema_cache: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_sp_token(self) -> str:
        """Obtain an AAD bearer token via service principal client-credentials flow."""
        url = _AAD_TOKEN_URL.format(tenant=config.FABRIC_TENANT_ID)
        resp = requests.post(url, data={
            "grant_type": "client_credentials",
            "client_id": config.FABRIC_CLIENT_ID,
            "client_secret": config.FABRIC_CLIENT_SECRET,
            "scope": _FABRIC_RESOURCE,
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()["access_token"]

    @staticmethod
    def _token_to_bytes(token: str) -> bytes:
        """Convert an AAD token string to the SQL Driver token bytes format."""
        token_bytes = token.encode("utf-16-le")
        # The driver expects a 4-byte length prefix
        return struct.pack("<I", len(token_bytes)) + token_bytes

    # ── Connection ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Establish a pyodbc connection to Microsoft Fabric."""
        server = config.FABRIC_SERVER
        database = config.FABRIC_DATABASE

        base_conn = (
            f"DRIVER={{{_DRIVER}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=60;"
        )

        use_sp = (
            config.FABRIC_TENANT_ID
            and config.FABRIC_CLIENT_ID
            and config.FABRIC_CLIENT_SECRET
        )

        if use_sp:
            token = self._get_sp_token()
            token_bytes = self._token_to_bytes(token)
            # SQL_COPT_SS_ACCESS_TOKEN = 1256
            self._conn = pyodbc.connect(
                base_conn,
                attrs_before={1256: token_bytes},
            )
        else:
            conn_str = (
                base_conn
                + f"UID={config.FABRIC_USERNAME};"
                f"PWD={config.FABRIC_PASSWORD};"
                "Authentication=ActiveDirectoryPassword;"
            )
            self._conn = pyodbc.connect(conn_str)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    # ── Schema discovery ──────────────────────────────────────────────────────

    def get_schema(self, force_refresh: bool = False) -> str:
        """
        Return a compact DDL-like schema string for all user tables.
        Result is cached to avoid repeated round-trips.
        """
        if self._schema_cache and not force_refresh:
            return self._schema_cache

        query = """
        SELECT
            t.TABLE_SCHEMA,
            t.TABLE_NAME,
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.TABLES t
        JOIN INFORMATION_SCHEMA.COLUMNS c
            ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
            AND c.TABLE_NAME  = t.TABLE_NAME
        WHERE t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
        """
        df = self.query_df(query)
        if df.empty:
            return "No tables found."

        lines: List[str] = []
        for (schema, table), group in df.groupby(["TABLE_SCHEMA", "TABLE_NAME"]):
            lines.append(f"\nTable: [{schema}].[{table}]")
            for _, row in group.iterrows():
                dtype = row["DATA_TYPE"].upper()
                if row["CHARACTER_MAXIMUM_LENGTH"] and dtype in ("VARCHAR", "NVARCHAR", "CHAR"):
                    max_len = row["CHARACTER_MAXIMUM_LENGTH"]
                    dtype += f"({max_len if max_len != -1 else 'MAX'})"
                nullable = "NULL" if row["IS_NULLABLE"] == "YES" else "NOT NULL"
                lines.append(f"  {row['COLUMN_NAME']}  {dtype}  {nullable}")

        self._schema_cache = "\n".join(lines)
        return self._schema_cache

    def get_sample(self, table: str, n: int = 3) -> pd.DataFrame:
        """Return n sample rows from a fully-qualified table name."""
        return self.query_df(f"SELECT TOP {n} * FROM {table}")

    # ── Query execution ───────────────────────────────────────────────────────

    def query_df(self, sql: str) -> pd.DataFrame:
        """Execute a SELECT query and return results as a DataFrame."""
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")
        cursor = self._conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchmany(config.MAX_ROWS_DISPLAY + 1)
        truncated = len(rows) > config.MAX_ROWS_DISPLAY
        if truncated:
            rows = rows[: config.MAX_ROWS_DISPLAY]
        df = pd.DataFrame(rows, columns=cols)
        df.attrs["truncated"] = truncated
        return df

    def list_tables(self) -> List[str]:
        """Return fully-qualified table names visible in the current database."""
        df = self.query_df(
            "SELECT TABLE_SCHEMA, TABLE_NAME "
            "FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        return [f"[{r.TABLE_SCHEMA}].[{r.TABLE_NAME}]" for _, r in df.iterrows()]
