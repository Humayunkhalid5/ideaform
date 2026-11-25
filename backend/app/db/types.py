"""Custom column types that need no extra package."""

from __future__ import annotations

from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType):
    """pgvector column: 384 dimensions for all-MiniLM-L6-v2."""

    cache_ok = True

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def get_col_spec(self, **kw: object) -> str:
        return f"VECTOR({self.dim})"
