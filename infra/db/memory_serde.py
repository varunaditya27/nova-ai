"""Generic JSON codec for Layer-2 memory dataclasses.

`to_jsonable` turns any dataclass tree into JSON-native primitives; `from_jsonable`
rebuilds a typed dataclass from that tree, driven by the target type's annotations. This is
the fidelity guarantee for PostgresMemoryStore: `from_jsonable(T, to_jsonable(x)) == x`.

UUID decoding is deliberately lenient: an id string that is not a valid UUID (e.g. the
pipeline's "local-user") is returned unchanged, matching the design decision that ids are
opaque keys and the dataclass `UUID` annotation is advisory.

Pure stdlib (no SQLAlchemy) so it imports on a bare interpreter.
"""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

_HINTS_CACHE: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    if cls not in _HINTS_CACHE:
        _HINTS_CACHE[cls] = get_type_hints(cls)
    return _HINTS_CACHE[cls]


def to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):        # after datetime (datetime is a subclass of date)
        return obj.isoformat()
    if dataclasses.is_dataclass(obj):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    raise TypeError(f"cannot serialize {type(obj)!r}")


def _unwrap_optional(tp: Any) -> Any:
    if get_origin(tp) is Union:
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def from_jsonable(tp: Any, data: Any) -> Any:
    if data is None:
        return None
    tp = _unwrap_optional(tp)
    origin = get_origin(tp)
    if origin in (list, tuple):
        args = get_args(tp)
        item_tp = args[0] if args else Any
        return [from_jsonable(item_tp, x) for x in data]
    if origin is dict:
        return dict(data)
    if dataclasses.is_dataclass(tp):
        hints = _hints(tp)
        return tp(**{f.name: from_jsonable(hints[f.name], data[f.name])
                     for f in dataclasses.fields(tp) if f.name in data})
    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(data)
    if tp is UUID:
        try:
            return UUID(data)
        except (ValueError, AttributeError, TypeError):
            return data  # opaque string id — keep as-is (advisory UUID annotation)
    if tp is datetime:
        return datetime.fromisoformat(data)
    if tp is date:
        return date.fromisoformat(data)
    return data
