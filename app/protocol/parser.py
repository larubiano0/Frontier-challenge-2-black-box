"""Raw request parsing: bytes -> message pieces. No business rules here.

Observed (v2 ids 2-21 / v1 EX-1..20): body JSON `{"m": "<CMD>;<arg>;...;<control>"}`;
the LAST ';'-separated field is the control, the first is the command.
Anything not evidenced (invalid JSON, missing/non-string `m`, no ';') raises
`Unevidenced` instead of guessing an original error body.
"""
import json
from dataclasses import dataclass

from app.domain.errors import Unevidenced


@dataclass(frozen=True)
class Message:
    command: str          # as received (case preserved)
    args: list[str]       # fields between command and control
    control: str          # last field, raw


def parse_message(raw_body: bytes) -> Message:
    try:
        payload = json.loads(raw_body)
    except ValueError:
        raise Unevidenced("body is not valid JSON (original's response unknown)")
    if not isinstance(payload, dict) or not isinstance(payload.get("m"), str):
        raise Unevidenced("body lacks a string field 'm' (original's response unknown)")
    parts = payload["m"].split(";")
    if len(parts) < 2:
        raise Unevidenced("message without ';' (no control field; original's response unknown)")
    return Message(command=parts[0], args=parts[1:-1], control=parts[-1])
