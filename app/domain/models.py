"""Plain data structures. No business rules here."""
from dataclasses import dataclass, field


@dataclass
class Account:
    id: str
    owner: str = ""
    balance: int = 0          # integer cents
    fail_streak: int = 0      # consecutive TRANSFER failures (E506/E507) as source
    intentos: int = 0         # E510 answers since the account got blocked


@dataclass
class Operation:
    id: str
    kind: str = ""            # "DEPOSITO" | "TRANSFER"
    cancelled: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class State:
    accounts: dict[str, Account] = field(default_factory=dict)
    operations: dict[str, Operation] = field(default_factory=dict)
    next_account_seq: int = 1
    next_operation_seq: int = 1
