from __future__ import annotations

import warnings as warnings
from typing import Any

if not hasattr(warnings, "deprecated"):

    def _deprecated(
        message: str,
        /,
        *,
        category: type[Warning] | None = DeprecationWarning,
        stacklevel: int = 1,
    ):
        del category, stacklevel

        def decorator(obj: Any) -> Any:
            obj.__deprecated__ = message
            return obj

        return decorator

    warnings.deprecated = _deprecated  # type: ignore[attr-defined]


__all__ = ["warnings"]
