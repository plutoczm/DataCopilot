from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DataSourceSchemaSnapshot:
    datasource: str
    engine: str
    schema_context: str
    table_count: int
    fingerprint: str


class SchemaCatalog(Protocol):
    @property
    def name(self) -> str:
        raise NotImplementedError

    def available(self) -> bool:
        raise NotImplementedError

    def load_schema(self) -> DataSourceSchemaSnapshot:
        raise NotImplementedError
