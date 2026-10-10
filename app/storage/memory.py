"""In-process store. State is lost on restart by design."""
from app.domain.models import State


class MemoryStore:
    def __init__(self) -> None:
        self._state = State()

    def get_state(self) -> State:
        return self._state

    def reset(self) -> None:
        self._state = State()


store = MemoryStore()
