"""MySQL connector — works for local and AWS RDS MySQL / Aurora MySQL."""

from typing import List, Optional
import pandas as pd

from db_base import BaseDBClient


class MySQLClient(BaseDBClient):
    """MySQL connector for local and AWS RDS / Aurora MySQL instances."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        ssl_disabled: bool = False,
        max_rows: int = 50,
        label: str = "MySQL",
    ):
        self.host         = host
        self.port         = port
        self.database     = database
        self.user         = user
        self.password     = password
        self.ssl_disabled = ssl_disabled
        self.max_rows     = max_rows
        self.label        = label
        self._conn        = None
        self._schema_cache: str = ""

    def connect(self) -> None:
        try:
            import mysql.connector
        except ImportError:
            raise RuntimeError(
                "mysql-connector-python is not installed.\n"
                "Run:  pip install mysql-connector-python"
            )
        ssl_args = {"ssl_disabled": True} if self.ssl_disabled else {}
        self._conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            connection_timeout=30,
            **ssl_args,
        )

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def query_df(self, sql: str) -> pd.DataFrame:
        if not self._conn:
            raise RuntimeError("Not connected.")
        # Re-ping to handle dropped connections
        try:
            self._conn.ping(reconnect=True, attempts=2, delay=1)
        except Exception:
            pass
        cursor = self._conn.cursor(dictionary=True)
        cursor.execute(sql)
        rows = cursor.fetchmany(self.max_rows + 1)
        truncated = len(rows) > self.max_rows
        df = pd.DataFrame(rows[: self.max_rows])
        cursor.fetchall()  # drain remaining rows
        cursor.close()
        df.attrs["truncated"] = truncated
        return df

    def _query_all(self, sql: str) -> pd.DataFrame:
        """Fetch all rows with no cap — used for schema discovery only."""
        if not self._conn:
            raise RuntimeError("Not connected.")
        try:
            self._conn.ping(reconnect=True, attempts=2, delay=1)
        except Exception:
            pass
        cursor = self._conn.cursor(dictionary=True)
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close()
        return pd.DataFrame(rows)

    def get_schema(self, force_refresh: bool = False) -> str:
        if self._schema_cache and not force_refresh:
            return self._schema_cache

        sql = """
        SELECT c.TABLE_SCHEMA  AS table_schema,
               c.TABLE_NAME    AS table_name,
               c.COLUMN_NAME   AS column_name,
               c.DATA_TYPE     AS data_type,
               c.IS_NULLABLE   AS is_nullable
        FROM information_schema.COLUMNS c
        JOIN information_schema.TABLES t
          ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
         AND t.TABLE_NAME   = c.TABLE_NAME
        WHERE t.TABLE_TYPE = 'BASE TABLE'
          AND c.TABLE_SCHEMA NOT IN (
              'information_schema','performance_schema','mysql','sys'
          )
        ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
        """
        df = self._query_all(sql)
        if df.empty:
            return "No tables found."

        lines: List[str] = []
        for (schema, table), grp in df.groupby(["table_schema", "table_name"]):
            lines.append(f"\nTable: {schema}.{table}")
            for _, row in grp.iterrows():
                null = "NULL" if row["is_nullable"] == "YES" else "NOT NULL"
                lines.append(f"  {row['column_name']}  {row['data_type'].upper()}  {null}")

        self._schema_cache = "\n".join(lines)
        return self._schema_cache

    def list_tables(self) -> List[str]:
        df = self._query_all(
            "SELECT TABLE_SCHEMA, TABLE_NAME "
            "FROM information_schema.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' "
            "AND TABLE_SCHEMA NOT IN "
            "('information_schema','performance_schema','mysql','sys') "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        return [f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}" for _, r in df.iterrows()]

    def get_sample(self, table: str, n: int = 5) -> pd.DataFrame:
        return self.query_df(f"SELECT * FROM {table} LIMIT {n}")
