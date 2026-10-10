"""Integrity control (E202) — ISO 7064 MOD 97-10 style check over the message.

Model (derived offline from the recorded log; reproduces all 66 distinct
normalized (message, control) pairs in reports/control_rows.json and every
E202 / non-E202 outcome of the golden v2 suite):

  1. body = every segment of `m` except the last one, re-joined (the control
     is computed over the whole message without its trailing ';<control>').
  2. Keep only ASCII letters and digits; upper-case letters.
     (ids 94-159: case, spaces and punctuation do not change the control.)
  3. Encode: a digit stays itself, a letter becomes its alphabet position
     A=1 … Z=26 (decimal, concatenated).  E.g. "AC0001" -> "1" "3" "0001".
  4. N = that decimal string as an integer.
  5. control = 98 - (N * 100 mod 97)          -> always in 2..98
  6. The received control must be EXACTLY str(control): "03" is rejected
     although it is numerically 3 (ids 62, 122) -> string comparison.

Supuestos (not probed): a body without any ASCII alphanumeric gives N = 0
(control 98); non-ASCII letters are ignored like punctuation.
"""

_A = ord("A")


def expected_control(body: str) -> int:
    digits = []
    for ch in body:
        if "0" <= ch <= "9":
            digits.append(ch)
        elif "A" <= ch <= "Z" or "a" <= ch <= "z":
            digits.append(str(ord(ch.upper()) - _A + 1))
    n = int("".join(digits)) if digits else 0
    return 98 - (n * 100) % 97


def control_matches(body: str, control: str) -> bool:
    return control == str(expected_control(body))
