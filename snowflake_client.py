"""Snowflake connector."""

from typing import List, Optional
import pandas as pd
import snowflake.connector

from db_base import BaseDBClient


class SnowflakeClient(BaseDBClient):
    label = "Snowflake"

    def __init__(
        self,
        account: str,
        user: str,
        password: str,
        warehouse: str,
        database: str,
        schema: str = "PUBLIC",
        role: str = "",
        max_rows: int = 50,
    ):
        self.account    = account
        self.user       = user
        self.password   = password
        self.warehouse  = warehouse
        self.database   = database
        self.schema     = schema
        self.role       = role
        self.max_rows   = max_rows
        self._conn: Optional[snowflake.connector.SnowflakeConnection] = None
        self._schema_cache: str = ""

    def connect(self) -> None:
        kwargs = dict(
            account=self.account,
            user=self.user,
            password=self.password,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
        )
        if self.role:
            kwargs["role"] = self.role
        self._conn = snowflake.connector.connect(**kwargs)

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def query_df(self, sql: str) -> pd.DataFrame:
        if not self._conn:
            raise RuntimeError("Not connected.")
        cur = self._conn.cursor()
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(self.max_rows + 1)
        truncated = len(rows) > self.max_rows
        df = pd.DataFrame(rows[:self.max_rows], columns=cols)
        df.attrs["truncated"] = truncated
        return df

    def get_schema(self, force_refresh: bool = False) -> str:
        if self._schema_cache and not force_refresh:
            return self._schema_cache

        sql = """
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_CATALOG = CURRENT_DATABASE()
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """
        df = self.query_df(sql)
        if df.empty:
            return "No tables found."

        lines: List[str] = []
        for (schema, table), grp in df.groupby(["TABLE_SCHEMA", "TABLE_NAME"]):
            lines.append(f"\nTable: {schema}.{table}")
            for _, row in grp.iterrows():
                null = "NULL" if row["IS_NULLABLE"] == "YES" else "NOT NULL"
                lines.append(f"  {row['COLUMN_NAME']}  {row['DATA_TYPE'].upper()}  {null}")

        self._schema_cache = "\n".join(lines)
        return self._schema_cache

    def list_tables(self) -> List[str]:
        df = self.query_df(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE='BASE TABLE' AND TABLE_CATALOG=CURRENT_DATABASE() "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME"
        )
        return [f"{r.TABLE_SCHEMA}.{r.TABLE_NAME}" for _, r in df.iterrows()]

    def get_sample(self, table: str, n: int = 5) -> pd.DataFrame:
        return self.query_df(f"SELECT * FROM {table} LIMIT {n}")
