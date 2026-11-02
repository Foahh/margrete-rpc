"""Compatibility for string enums on Python 3.10."""

import sys

if sys.version_info >= (3, 11):
    from enum import StrEnum as StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """String-valued enum with value-based string conversion and formatting."""

        def __str__(self) -> str:
            return self.value

        def __format__(self, format_spec: str) -> str:
            return format(self.value, format_spec)
