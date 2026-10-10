"""Narrow storage interface so a SQLite backend could be swapped in later."""
from typing import Protocol

from app.domain.models import State


class Store(Protocol):
    def get_state(self) -> State: ...
    def reset(self) -> None: ...
