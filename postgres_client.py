"""PostgreSQL connector — works for local and AWS RDS."""

from typing import List, Optional
import psycopg2
import psycopg2.extras
import pandas as pd

from db_base import BaseDBClient


class PostgresClient(BaseDBClient):

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        sslmode: str = "prefer",
        max_rows: int = 50,
        label: str = "PostgreSQL",
    ):
        self.host     = host
        self.port     = port
        self.database = database
        self.user     = user
        self.password = password
        self.sslmode  = sslmode
        self.max_rows = max_rows
        self.label    = label
        self._conn: Optional[psycopg2.extensions.connection] = None
        self._schema_cache: str = ""

    def connect(self) -> None:
        self._conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
            sslmode=self.sslmode,
            connect_timeout=30,
        )
        self._conn.autocommit = True

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def query_df(self, sql: str) -> pd.DataFrame:
        if not self._conn:
            raise RuntimeError("Not connected.")
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchmany(self.max_rows + 1)
            truncated = len(rows) > self.max_rows
            df = pd.DataFrame(list(rows[:self.max_rows]))
            df.attrs["truncated"] = truncated
            return df

    def _query_all(self, sql: str) -> pd.DataFrame:
        """Fetch all rows with no max_rows cap — used for schema discovery only."""
        if not self._conn:
            raise RuntimeError("Not connected.")
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return pd.DataFrame(list(rows))

    def get_schema(self, force_refresh: bool = False) -> str:
        if self._schema_cache and not force_refresh:
            return self._schema_cache

        sql = """
        SELECT c.table_schema, c.table_name, c.column_name,
               c.data_type, c.is_nullable
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE t.table_type = 'BASE TABLE'
          AND c.table_schema NOT IN ('information_schema','pg_catalog')
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
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
            "SELECT table_schema, table_name "
            "FROM information_schema.tables "
            "WHERE table_type='BASE TABLE' "
            "AND table_schema NOT IN ('information_schema','pg_catalog') "
            "ORDER BY table_schema, table_name"
        )
        return [f"{r['table_schema']}.{r['table_name']}" for _, r in df.iterrows()]

    def get_sample(self, table: str, n: int = 5) -> pd.DataFrame:
        return self.query_df(f"SELECT * FROM {table} LIMIT {n}")
