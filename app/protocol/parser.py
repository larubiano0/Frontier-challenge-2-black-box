"""Raw request parsing: bytes -> ';'-segments. No business rules here.

Order (reports/handoff_implementation.md §1, steps 3-7):
  3. body > 8192 bytes                     -> 413 E101 (ids 2807 ok at 8192, 2821 at 8193)
  4. not valid JSON (incl. empty body)     -> 400 E100 (ids 78, 85)
  5. not an object / `m` missing/not str   -> 400 E102 (ids 79, 80, 83, 84, 89, 90)
  6. `m` without ';'                       -> 400 E103 (ids 81, 82, 2794, 2795)
  7. any empty segment                     -> 400 E104 (ids 99-103, 145-147)
Content-Type is ignored (ids 86, 87); extra keys are ignored (id 88).
Segments are NOT trimmed (ids 97, 98).
"""
import json
from dataclasses import dataclass

from app.domain.errors import e100, e101, e102, e103, e104

MAX_BODY_BYTES = 8192


@dataclass(frozen=True)
class Message:
    segments: list[str]

    @property
    def command(self) -> str:          # as received (case preserved)
        return self.segments[0]

    @property
    def args(self) -> list[str]:       # fields between command and control
        return self.segments[1:-1]

    @property
    def control(self) -> str:          # last field, raw
        return self.segments[-1]

    @property
    def body_without_control(self) -> str:
        return ";".join(self.segments[:-1])


def _reject_constant(name: str):
    # JSON.parse (original is JS-like) rejects NaN/Infinity; Python accepts them. [supuesto]
    raise ValueError(name)


def parse_message(raw_body: bytes) -> Message:
    if len(raw_body) > MAX_BODY_BYTES:
        raise e101()
    try:
        payload = json.loads(raw_body.decode("utf-8"), parse_constant=_reject_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise e100()
    if not isinstance(payload, dict) or not isinstance(payload.get("m"), str):
        raise e102()
    m = payload["m"]
    if ";" not in m:
        raise e103()
    segments = m.split(";")
    if any(s == "" for s in segments):
        raise e104()
    return Message(segments)
