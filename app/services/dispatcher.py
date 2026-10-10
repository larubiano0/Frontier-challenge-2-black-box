"""`POST /msg` pipeline (after route + auth). Pure function of (body, state).

Order (reports/handoff_implementation.md §1):
  3-7. parse: E101 size -> E100 json -> E102 `m` -> E103 no ';' -> E104 empty segment
  8.   PING (case-insensitive, exact) skips the control checks (ids 52, 53, 95, 104-108)
  9.   control format ^[0-9]{1,2}$, last segment only    -> E201
  10.  control value (app/domain/control.py)             -> E202 (before E301/E302: ids 54, 56, 121)
  11.  command, case-insensitive                         -> E301 (+ optional `sugerencia`)
  12.  arity                                             -> E302
  13.  handler (accounts, amounts, limits, blocking ...)
"""
import re

from app.domain import rules
from app.domain.control import control_matches
from app.domain.errors import ServiceError, e201, e202, e301, e302
from app.protocol.parser import parse_message
from app.services.commands import COMMANDS, Reply
from app.storage.base import Store

_CONTROL_RE = re.compile(r"[0-9]{1,2}")   # ASCII only, no sign/space/newline (ids 112, 113, 2798)


def process(raw_body: bytes, store: Store) -> tuple[int, dict]:
    try:
        msg = parse_message(raw_body)
        name = msg.command.upper()
        if name != "PING":
            if not _CONTROL_RE.fullmatch(msg.control):
                raise e201()
            if not control_matches(msg.body_without_control, msg.control):
                raise e202()
        entry = COMMANDS.get(name)
        if entry is None:
            raise e301(rules.suggest_command(msg.command, list(COMMANDS)))
        arity, handler = entry
        if len(msg.args) != arity:
            raise e302()
        reply: Reply = handler(store.get_state(), msg.args)
        return reply.status, reply.body
    except ServiceError as err:
        return err.status, err.body()
