"""Abstract base class for all database clients."""

from abc import ABC, abstractmethod
from typing import List
import pandas as pd


class BaseDBClient(ABC):
    """Common interface every connector must implement."""

    # Human-readable name shown in UI
    label: str = "Database"

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def query_df(self, sql: str) -> pd.DataFrame: ...

    @abstractmethod
    def get_schema(self, force_refresh: bool = False) -> str: ...

    @abstractmethod
    def list_tables(self) -> List[str]: ...

    def get_sample(self, table: str, n: int = 5) -> pd.DataFrame:
        """Default implementation — connectors can override for efficiency."""
        return self.query_df(f"SELECT * FROM {table} LIMIT {n}")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
