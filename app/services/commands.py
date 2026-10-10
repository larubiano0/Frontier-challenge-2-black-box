"""Command handlers: PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA.

Legend: [v2] observed in the v2 log; [S-n] v2 `supuesto` rule (domain/rules.py);
[v1] only seen in the historical v1 examples -> `supuesto`; [default] chosen
default with no evidence; [?] no evidence and no reasonable default ->
`Unevidenced` (explicit 501 placeholder).
"""
from dataclasses import dataclass
from typing import Callable

from app.domain import rules
from app.domain.errors import ServiceError, Unevidenced, e401, e402, e506, e507
from app.domain.models import Account, Operation, State


@dataclass(frozen=True)
class Reply:
    status: int
    body: dict


def _amount(text: str) -> int:
    # [?] only plain positive integers are evidenced (700, 40000, 250000 ...).
    if not (text.isascii() and text.isdigit()) or text.startswith("0"):
        raise Unevidenced(f"amount {text!r}: negative/zero/decimal/leading-zero/non-numeric semantics unknown")
    return int(text)


def _account(state: State, account_id: str) -> Account:
    acc = state.accounts.get(account_id)  # [v2] id 16: unknown account -> E401 (exact-match ids [default])
    if acc is None:
        raise e401()
    return acc


def _new_operation(state: State, kind: str, data: dict) -> Operation:
    op = Operation(id=f"OP-{state.next_operation_seq:04d}", kind=kind, data=data)  # [v2] ids 7,8,19
    state.next_operation_seq += 1   # consumed ONLY on success [v2] id 19 (OP-0003 after a rejected TRANSFER)
    state.operations[op.id] = op
    state.history.append(op.id)
    return op


def ping(state: State, args: list[str]) -> Reply:
    return Reply(200, {"pong": True})                                  # [v2] id 2


def alta(state: State, args: list[str]) -> Reply:
    (owner,) = args
    if owner == "":
        raise Unevidenced("ALTA with empty name: unknown")
    acc = Account(id=f"AC-{state.next_account_seq:04d}", owner=owner)  # [v2] ids 4, 5
    state.next_account_seq += 1                                        # only on success [v2] ids 3-5
    state.accounts[acc.id] = acc                                       # [default] duplicate names allowed
    return Reply(201, {"cuentaId": acc.id})


def consulta(state: State, args: list[str]) -> Reply:
    (account_id,) = args
    acc = _account(state, account_id)
    return Reply(200, {"cuenta_id": acc.id, "saldo": rules.format_saldo(acc.balance)})  # [S-1] ids 6,9,12,20


def deposito(state: State, args: list[str]) -> Reply:
    account_id, amount_text = args
    acc = _account(state, account_id)          # [default] E401 for DEPOSITO too (only CONSULTA evidenced)
    amount = _amount(amount_text)
    acc.balance += amount                      # [v2] id 20: 700 deposited -> "407.00"; no limit [v2] id 7
    op = _new_operation(state, "DEPOSITO", {"account": acc.id, "amount": amount})
    return Reply(200, {"status": "recieved", "operacionId": op.id})   # sic "recieved" [v2] id 7


def transfer(state: State, args: list[str]) -> Reply:
    src_id, dst_id, amount_text = args
    src = _account(state, src_id)              # [default] order: src, dst, amount, limit, balance
    dst = _account(state, dst_id)
    amount = _amount(amount_text)
    if src.id == dst.id:
        raise Unevidenced("TRANSFER to the same account: unknown")
    if rules.transfer_exceeds_limit(amount):   # [S-2] ids 10, 11 (checked BEFORE balance [default]: order unknown)
        raise e506()
    if src.balance < amount:                   # [v2] id 17
        raise e507()
    src.balance -= amount
    dst.balance += amount                      # [v2] id 9: "400.00" after 40000
    op = _new_operation(state, "TRANSFER", {"src": src.id, "dst": dst.id, "amount": amount})
    return Reply(200, {"status": "recieved", "operacionId": op.id})


def anula(state: State, args: list[str]) -> Reply:
    (op_id,) = args
    op = state.operations.get(op_id)
    if op is None:
        raise e402()                           # [S-3] v2 ids 14, 15
    if op.cancelled:
        return Reply(200, {"ok": False, "motivo": "ya anulada"})       # [v1] EX-14 (unverified in v2)
    # Reversal of the balance effect: [v1] inferred from EX-16/19 (unverified in v2).
    if op.kind == "DEPOSITO":
        acc = state.accounts[op.data["account"]]
        if acc.balance < op.data["amount"]:
            raise Unevidenced("ANULA of a DEPOSITO whose funds were already spent: unknown")
        acc.balance -= op.data["amount"]
    else:
        src, dst = state.accounts[op.data["src"]], state.accounts[op.data["dst"]]
        if dst.balance < op.data["amount"]:
            raise Unevidenced("ANULA of a TRANSFER whose funds were already spent: unknown")
        dst.balance -= op.data["amount"]
        src.balance += op.data["amount"]
    op.cancelled = True
    return Reply(200, {"ok": True, "anulada": op.id})                  # [v1] EX-13 (unverified in v2)


# name -> (number of args between command and control, handler)
COMMANDS: dict[str, tuple[int, Callable[[State, list[str]], Reply]]] = {
    "PING": (0, ping),
    "ALTA": (1, alta),
    "CONSULTA": (1, consulta),
    "DEPOSITO": (2, deposito),
    "TRANSFER": (3, transfer),
    "ANULA": (1, anula),
}
