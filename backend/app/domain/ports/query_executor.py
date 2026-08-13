from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class QueryPage:
    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]
    truncated: bool
    elapsed_ms: float


class QueryExecutor(Protocol):
    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def kind(self) -> str:
        raise NotImplementedError

    def available(self) -> bool:
        raise NotImplementedError

    def execute(
        self,
        sql: str,
        *,
        max_rows: int,
        timeout_ms: int,
    ) -> QueryPage:
        raise NotImplementedError
