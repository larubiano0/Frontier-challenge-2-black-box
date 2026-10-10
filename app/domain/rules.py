"""Version-2 business rules (values from reports/handoff_implementation.md).

* TRANSFER limit: amount > 50000 -> E506; 50000 passes, 50001 fails (ids 2792,
  2786). Per operation, not cumulative (ids 42-45). DEPOSITO has no limit.
* Amounts are integer CENTS: ^[1-9][0-9]{0,9}$ (1-10 digits, no sign, no
  decimals, no leading zero, not 0). Anything else -> E303 (ids 983-1394,
  1814 ok at 10 digits, 2776 E303 at 11).
* CONSULTA `saldo` is a string "X.YY" = balance/100, negatives "-400.00"
  (ids 2411, 2491), no thousands separator (id 1830).
* Blocking: 3 consecutive TRANSFER failures (E506/E507) as source -> E510.
* E301 suggestion: nearest known command within Levenshtein distance <= 2.
"""
import re

TRANSFER_LIMIT = 50_000
BLOCK_AFTER_FAILURES = 3

_AMOUNT_RE = re.compile(r"[1-9][0-9]{0,9}")


def parse_amount(text: str) -> int | None:
    """Valid amount in cents, or None (-> E303)."""
    return int(text) if _AMOUNT_RE.fullmatch(text) else None


def transfer_exceeds_limit(amount: int) -> bool:
    return amount > TRANSFER_LIMIT


def format_saldo(balance: int) -> str:
    """Integer cents -> 'X.YY' (no floats, no separators, leading '-' if negative)."""
    sign = "-" if balance < 0 else ""
    whole, cents = divmod(abs(balance), 100)
    return f"{sign}{whole}.{cents:02d}"


def levenshtein(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


SUGGESTION_MAX_DISTANCE = 2


def suggest_command(command: str, known: list[str]) -> str | None:
    """Closest known command (case-insensitive) within distance <= 2.
    Ties: first in `known` order (supuesto, ties never probed)."""
    upper = command.upper()
    best, best_d = None, SUGGESTION_MAX_DISTANCE + 1
    for name in known:
        d = levenshtein(upper, name)
        if d < best_d:
            best, best_d = name, d
    return best
