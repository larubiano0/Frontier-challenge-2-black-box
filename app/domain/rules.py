"""Version-2 rules (Incident FR-0153) approved by the researcher as `supuesto`.

These are the ONLY places where v2 intentionally differs from the v1 examples.
They are NOT confirmed changes; they are the simplest defaults consistent with
the v2 observations of experiment sequence `v2-s1` (ids 1-21). Do not widen
them without new evidence.

S-1  CONSULTA returns `saldo` as a STRING with two decimals = balance / 100.
     v2 ids 6, 9, 12, 20 ("0.00", "400.00", "2100.00", "407.00"); v1 returned
     the integer (EX-5, 8, 11, 19). Unknown: negatives, huge values, and whether
     the unit of the INPUT amounts also changed. Balances stay integers.
S-2  TRANSFER with amount >= 100000 -> 422 E506. v2 ids 10 (120000) and 11
     (100000) are rejected; v1 accepted 100000 (EX-10). The true v2 threshold and
     semantics (per-operation, inclusive/exclusive, cumulative, unit) are UNKNOWN;
     100000 is only the simplest value consistent with both observations.
     DEPOSITO is not limited (v2 id 7: 250000 accepted).
S-3  ANULA on an operation that does not exist -> 404 E402 "operación
     inexistente" (v2 ids 14, 15). Implemented in services/commands.py (anula).
"""

TRANSFER_LIMIT = 100_000  # S-2 (supuesto): amounts >= this are rejected with E506


def transfer_exceeds_limit(amount: int) -> bool:
    return amount >= TRANSFER_LIMIT


def format_saldo(balance: int) -> str:
    """S-1 (supuesto): integer balance -> 'X.YY' string (balance / 100), no floats."""
    sign = "-" if balance < 0 else ""
    whole, cents = divmod(abs(balance), 100)
    return f"{sign}{whole}.{cents:02d}"
