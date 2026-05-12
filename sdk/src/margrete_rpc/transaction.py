from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from margrete_rpc._proto.margrete.rpc.v1 import messages_pb2
from margrete_rpc.chart import Appendable

if TYPE_CHECKING:
    from margrete_rpc.client import Margrete


class Transaction:
    def __init__(self, client: Margrete, name: str) -> None:
        self._client = client
        self._name = name
        self._items: list[messages_pb2.AppendItem] = []

    def __enter__(self) -> Transaction:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            return False
        self.commit()
        return False

    def append(self, item: Appendable) -> None:
        self._items.append(item.to_append_item())

    def insert_at_tick(self, origin_tick: int, objects: Iterable[Appendable]) -> None:
        for obj in objects:
            self.append(obj.shifted(origin_tick))

    def commit(self) -> int:
        if not self._items:
            return 0
        count = self._client._append_transaction(self._name, self._items)
        self._items.clear()
        return count
