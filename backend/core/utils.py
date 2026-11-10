"""Small shared helpers."""

from __future__ import annotations

from typing import Any


def to_jsonable(value: Any) -> Any:
    """Convert numpy / torch scalars into plain Python types.

    The values themselves are never modified — only their representation, so
    that the prediction can be serialised as JSON and stored in PostgreSQL.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    # numpy / torch scalars expose `.item()`.
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return to_jsonable(item())
        except Exception:  # pragma: no cover - defensive
            pass

    return value
