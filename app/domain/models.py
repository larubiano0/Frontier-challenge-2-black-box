"""Plain data structures. No business rules here."""
from dataclasses import dataclass, field


@dataclass
class Account:
    id: str
    owner: str = ""
    balance: int = 0


@dataclass
class Operation:
    id: str
    kind: str = ""
    cancelled: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class State:
    accounts: dict[str, Account] = field(default_factory=dict)
    operations: dict[str, Operation] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)  # operation ids in order
    next_account_seq: int = 1
    next_operation_seq: int = 1
