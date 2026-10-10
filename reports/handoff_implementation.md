# Handoff report: tested hypotheses and changes to implement

_Written 2026-10-10 against the ORIGINAL (v2), after testing H-001…H-008 except H-005. Deadline is 20:00 Bogotá._

**Audience:** the agent that implements the changes in `app/`.
**Evidence:** every claim cites ids from `experimentos.jsonl`. The log now has 2,880 lines: ids 1–21 from H-000, ids 22–2880 from this pass.
**Probe tool:** `tools/probe.py`. It reads the token from the `ORIGINAL_BEARER_TOKEN` env var and redacts it. A scan of both log files for the token found 0 hits.
**Request budget:** the token's tool-observed daily counter is 2,880 of 8,000. Rate stayed at about 6 req/s with no `X-Frontier-Infra` events.
**Status of earlier docs:** `reports/hypotheses.md` and `Documentation.md` predate these results. Where they conflict with this file, this file wins.

## 0. Summary

| Hyp | Result |
|---|---|
| H-001 ANULA over existing op | **Confirmed.** Same as v1, plus extra findings (§3.6). |
| H-002 E506 limit | **Confirmed per-operation `amount > 50000`.** Not cumulative. The limit is checked before the balance (E507). |
| H-003 Input/auth/routes | **All behaviors found.** Many new error codes (E001, E100–E104, E404, E101/413). The current placeholders are wrong. |
| H-004 Precedence | **Established** (§2). PING is exempt from the control check. |
| H-006 Amounts | **Established.** New errors E303 and E304; amount unit is cents. |
| H-007 Grammar | **Established.** The control ignores case and non-alphanumerics. E301 has a fuzzy `sugerencia`. |
| H-008 ALTA duplicates | **Confirmed.** Duplicates are allowed. |
| **Not in the plan: E510** | **A hidden stateful feature found:** accounts get blocked after 3 consecutive failed transfers (§3.5). |
| H-005 control algorithm | **Not attempted.** New rows and invariants are in §5. |

The three v2 changes are still unidentified. Strong candidates (v1 vs v2):

- `saldo` as a `"x.yy"` string.
- The E506 threshold: v1 accepted 100000, v2 rejects anything above 50000.
- A third change. Candidates: E510 blocking and the E301 `sugerencia`. v1 evidence neither confirms nor excludes either. Do not claim them as "the three changes" without saying they are inferences.

## 1. Request pipeline (implement in this order)

Verified order for `POST /msg`. Write it as a pure function with explicit steps.

| # | Step | Result | Evidence |
|---|---|---|---|
| 1 | Route and method. Only `GET /health`, `POST /__reset` and `POST /msg` exist. Any other method or path (`GET /msg`, `PUT /msg`, `GET /__reset`, `POST /health`, `/`, `/msg/`, `/MSG`) returns **404 `{"error":"E404","mensaje":"ruta desconocida"}`**. This is evaluated **before auth**: an unknown route without a token also returns 404. | 404 | ids 70–77, 91, 92 |
| 2 | Auth, for known routes only. A missing or wrong token on `/health`, `/msg` or `/__reset` returns **401 `{"error":"E001","mensaje":"no autorizado"}`**. | 401 | ids 65–69 |
| 3 | Body larger than **8192 bytes**. Exactly 8192 is accepted, 8193 is rejected. | **413 `{"error":"E101","mensaje":"cuerpo demasiado grande"}`** | ids 2800–2802, 2804–2821 |
| 4 | Body is not valid JSON (garbage or empty). | 400 `{"error":"E100","mensaje":"json inválido"}` | ids 78, 85 |
| 5 | JSON is not an object, `m` is missing, `m` is not a string, or `m` is null. Includes `[1,2]`, `{}`, `{"m":5}`, `{"M":…}`, `{"m":[…]}`. | 400 `{"error":"E102","mensaje":"falta m"}` | ids 79, 80, 83, 84, 89, 90 |
| 6 | `m` contains no `;`. This includes `""`, `"   "`, `"\n"` and `"PING"`. | 400 `{"error":"E103","mensaje":"falta control"}` | ids 81, 82, 2794, 2795 |
| 7 | Split `m` on `;`. If any segment is empty (`PING;`, `;64`, `PING;;64`, `PING;64;`, `;`, `CONSULTA;AC-0001;`), return 400 `{"error":"E104","mensaje":"segmento vacío"}`. | 400 | ids 99–103, 109, 110, 115, 118, 120, 124, 132, 133, 145–147 |
| 8 | **PING (case-insensitive command) skips steps 9 and 10.** `PING;65`, `PING;5X`, `PING;-1`, `PING;+5`, `PING; 5`, `PING;007`, `PING;１２`, `PING;64 ` and `PING;64\n` all return pong. PING still needs exactly 1 field after the command: `PING;x;64` returns E302. If the command is exactly `PING`, go to step 12. Whitespace is not trimmed for the command match: `" PING;64"`, `"PING ;64"` and `"P ING;64"` fall to E301 (step 11). | `{"pong":true}` | ids 52, 53, 95–98, 100, 104–108, 2796, 2797 |
| 9 | Control format. The last segment must match `^\d{1,2}$` (ASCII digits, no sign, no spaces). `5X`, `100`, `014`, `14 `, ` 14`, `3 ` and `82\n` return 400 `{"error":"E201","mensaje":"control mal formado"}`. `3` is valid. `03` passes the format check (1–2 digits) and then fails as E202 (ids 62, 122), so there is no numeric normalization. | 400 | ids 55, 57, 63, 112, 113, 123, 130, 131, 148, 2798 |
| 10 | Control value (E202). The control must equal an unknown function of the message body. See §5. A wrong value returns 400 `{"error":"E202","mensaje":"control inválido"}`. | 400 | ids 54, 56, 58, 62, 117, 119, 121, 122, 125, 127–129 |
| 11 | Command lookup is case-insensitive. An unknown command returns **400 `{"error":"E301","mensaje":"comando desconocido "}`** with the trailing space. Add `"sugerencia":"<COMMAND>"` when the nearest known command is within edit distance ≤ 2 (§3.7). | 400 | ids 13, 97, 136–144, 220, 303, 365, 445, 503, 602, 696, 795, 800, 844, 865, 904, 941 |
| 12 | Arity. Wrong field count returns 400 `{"error":"E302","mensaje":"aridad inválida"}`. Arities after the command, not counting the control: PING 0, ALTA 1, CONSULTA 1, DEPOSITO 2, TRANSFER 3, ANULA 1. | 400 | ids 21, 56, 100, 121, 2771 |
| 13 | Handler (§3). | | |

Notes on the order:

- E104 comes before E201, E202, E301 and E302 (ids 145–147).
- E202 comes before E301 and E302 (ids 54, 56, 121).
- E201 is only evaluated on the last segment. For `CONSULTA;14` the 14 is the control, so the body is `CONSULTA` with arity 0, and the reply is E202 (id 119).
- The PING exemption has one open question: whether E201 and E202 are skipped only for PING or for any message whose command matches PING exactly. Lowercase `ping` is exempt (id 95). The tested forms with leading whitespace are not PING and go through E201/E202 (ids 97, 136–140).

`GET /health` returns **200 `{"ok":true}`** with auth (id 64). With no auth it returns the E001 401.
`POST /__reset` returns 200 `{"ok":true}`; it clears all state, including blocks and counters.
The current placeholders `{"status":"ok"}` and `{"error":"unauthorized"}` are wrong.
Responses are JSON with `Content-Type: application/json; charset=utf-8`. Headers are not scored.

`Content-Type` is ignored: `text/plain` and a missing header both work (ids 86, 87). Extra keys in the body are ignored (id 88).

## 2. Precedence inside handlers

| Command | Order | Evidence |
|---|---|---|
| DEPOSITO | E303 (amount) → E401 (account) → success | ids 1470, 1148 |
| TRANSFER | E303 (amount, even if accounts are bogus) → E304 (src == dst, even if the account does not exist) → E401 (src or dst missing) → **E510 (src blocked)** → E506 (amount > 50000) → E507 (balance) → success | ids 1516, 1550, 1555, 1561, 1636, 1710, 1804, 2142–2146, 49, 50 |
| CONSULTA | E401 → success | ids 16, 59 |
| ANULA | E402 → already-cancelled → reversal | §3.6 |

Before this pass the file assumed accounts come before the limit. That is confirmed (id 60: 120000 between non-existent accounts returns E401). The new facts are E303 and E304 before E401, and E510 before E506.

## 3. Handler behavior

### 3.1 ALTA
- `ALTA;<name>;<ctl>` returns 201 `{"cuentaId":"AC-NNNN"}`.
- IDs are sequential. Duplicates are allowed (ids 943–945). Failed ALTAs do not consume an id (ids 3, 4).
- The name has no length limit up to the body limit: 300 `-` characters and 70 spaces were accepted (ids 2778, 2779).
- Names with spaces or case differences are accepted as-is.

### 3.2 CONSULTA
`{"cuenta_id","saldo"}` with `saldo` a string: `"X.YY"` where the internal balance is in cents.
- Negative balances print as `"-400.00"` (ids 2411, 2491).
- Large balances have no thousands separators: `"110002499.98"` (id 1830).
- The account id match is case-sensitive and not trimmed. `ac-0001` and `AC-0001 ` return E401 (ids 111, 114).
- The control ignores case and punctuation, so `CONSULTA;ac-0001;14` passes the control and then fails at E401.

### 3.3 DEPOSITO
- `DEPOSITO;<acc>;<amount>` returns 200 `{"status":"recieved","operacionId":"OP-NNNN"}` (typo is original).
- Amount is in **cents**: `DEPOSITO;AC-0001;1` then CONSULTA shows `"2500.01"` (id 1395).
- Amount rule: `^[1-9][0-9]{0,9}$`, so 1 to 10 digits, no leading zero, no sign, no decimal, not 0.
- Invalid amounts (`0`, `-5`, `1.5`, `007`, `abc`, 11 or more digits) return **400 `{"error":"E303","mensaje":"monto inválido"}`**.
- The 10-digit/11-digit boundary is ids 1814 (ok) and 2776 (E303 at 11 digits); 12 digits at id 1819.
- Ids: 983, 1000, 1063, 1134, 1148, 1153, 1245, 1298, 1394.
- There is no deposit limit. A deposit into a blocked account is allowed and **unblocks it** (§3.5).

### 3.4 TRANSFER
- `TRANSFER;<src>;<dst>;<amount>`. Amount rule is the same as DEPOSITO, E303 on failure.
- src == dst returns **400 `{"error":"E304","mensaje":"origen y destino iguales"}`** (ids 1200, 1550, 1804).
- **Limit:** `amount > 50000` returns 422 E506. 50000 passes and 50001 fails (ids 2792 and 2786). Earlier data: 40000 passes; 75000, 99998, 99999, 100000 and 120000 fail (ids 1924, 1883, 1855, 37, 10).
  - It is per operation, not cumulative. After 40000+40000+50000+40000 all pass (ids 42–45), and a fresh-state 100000 fails (id 37).
  - The limit is checked **before** the balance. A zero-balance account sending 100000 or 120000 gets E506, not E507 (ids 49, 50).
- Balance: `amount > balance` returns 422 E507.
- Success is 200 with `recieved`, and the debit and credit apply immediately.
- The op counter is consumed only on success (id 19).
- The 10-digit amount ceiling does not matter for transfers because of the 50000 limit.

### 3.5 E510: blocked account (NEW, not in any previous document)
- A source account that has **3 consecutive failed transfers** (each failure either E506 or E507) is **blocked**.
- From the 4th attempt onward, `TRANSFER` with that account as **source** returns **423 `{"error":"E510","mensaje":"cuenta bloqueada","intentos":N}`**.
  - `intentos` counts the blocked attempts: 1, 2, 3, … (ids 1998–2004).
  - The first 3 failures return their normal errors (E506/E507).
  - E507 reaches the block the same way (ids 2013–2017).
  - Mixed failures count together: E506 (scan), E507, E507, then the next attempt is blocked (ids 2877–2880).
- **Failures that count:** only E506 and E507 from `TRANSFER`.
- **Failures that do not count:** E303, E304, E401 and E301 (ids 2057–2066, 2297).
- **Resets the counter and unblocks:**
  - a successful `TRANSFER` from that account (ids 2025–2031: E506, E506, success, E506, success, success, no block);
  - a successful `DEPOSITO` into that account (ids 2074–2077, 2270–2272, 2327–2332; after unblock the next block shows `intentos:1` again).
- **Does not reset:** `CONSULTA` (own or other), `PING`, `ALTA`, an unknown command, `DEPOSITO` into another account, a failed `DEPOSITO` (E303), `ANULA` with E402, an E507 on another account (ids 2228–2317).
- **Blocking is per source account.**
  - A blocked account can still receive transfers (id 2141) and still do `CONSULTA`, `DEPOSITO` and `ANULA` (ids 2147, 2220, 2005–2008).
  - Receiving a transfer does not unblock (ids 2146, 2141).
  - Another account blocked does not affect AC-0001 as a source (ids 2018–2020).
- **No time expiry:** the block persisted across 130 s (ids 2829–2831).
- `__reset` clears everything (id 2227: after reset the same transfer succeeds).
- **Check order:** E510 comes after E303, E304 and E401 (ids 2142–2145) and **before** E506 (id 2146) and E507.
- **Untested (assumption, mark `supuesto`):**
  - whether a successful `ANULA` resets the counter;
  - whether E510 attempts add to the failure counter (assumed no);
  - whether `intentos` has a cap.
- **Unknown version status:** nothing in v1 contradicts this (v1 never had 3 consecutive failures). Whether v1 had it is unknown.

### 3.6 ANULA
- `ANULA;<opId>` where the op exists and is not cancelled returns 200 `{"ok":true,"anulada":"OP-NNNN"}` (ids 29, 2220, 2410, 2489).
- A second ANULA on the same op returns 200 `{"ok":false,"motivo":"ya anulada"}` (ids 31, 2413).
- An unknown op id returns 404 E402 `{"error":"E402","mensaje":"operación inexistente"}`. This covers `OP-9999`, `XYZ`, `AC-0001` and lowercase `op-0001` (ids 2547, 2592, 2652, 2725). Op ids are case-sensitive and exact.
- **Reversal of a TRANSFER:** debits dst, credits src. After 2 transfers of 40000 and a cancel, the dst balance went 800.00 → 400.00 and the src went to 2100.00 (ids 28–32).
- **Reversal of a DEPOSITO:** debits the account.
- **Reversal is unconditional, with no balance check.** Balances can go negative:
  - cancelling a 250000 deposit with 210000 left gives `"-400.00"` (ids 2410, 2411);
  - cancelling a transfer whose funds were spent gives dst `"-400.00"` (ids 2489–2491).
- The current `Unevidenced` raises for spent funds must be replaced by this unconditional reversal.
- Cancelling an op does not unblock anything (an ANULA on a blocked account was fine and left it blocked, ids 2146 then 2220).
- Arity is 1: `ANULA;OP-0001;x;<ctl>` returns E302 (id 2771).

### 3.7 E301 suggestion
- `{"error":"E301","mensaje":"comando desconocido ","sugerencia":"<CMD>"}` is returned when a known command is within **Levenshtein distance ≤ 2** of the normalized command.
- The closest command wins (assumed; ties untested).
- Without a close match the `sugerencia` key is absent: `SALDOS`, `SALDO`, `CONS`, `XYZ`, `ALTAXYZ`, `PINGPONG` get none.
- Positive evidence:

| Input | Suggestion | Id |
|---|---|---|
| `" PING"` | PING | 97 |
| `PNG` | PING | 220 |
| `CONSULTAS` | CONSULTA | 303 |
| `TRANSFERIR` | TRANSFER | 365 |
| `ALTAXY` | ALTA | 445 |
| `PONG` | PING | 602 |
| `ANUL` | ANULA | 696 |
| `DEPOSITOX` | DEPOSITO | 795 |
| `TRANSF` | TRANSFER | 800 |

- Whitespace variants of a valid command (`P ING`, `CON SULTA`, `CONSULT A`) all suggest the full name. This is consistent with the same edit-distance rule, because a space counts as 1 edit.
- The comparison is case-insensitive (the uppercased input is compared).
- The `mensaje` is always `"comando desconocido "` with the trailing space.
- The exact distance function is inferred. Levenshtein ≤ 2 matches every observation.

## 4. Replacement code: what changes (file by file)

| File | Change |
|---|---|
| `app/api/routes.py` | Add a catch-all 404 `E404` (any method, any path other than the 3 routes). The route check precedes auth. `/health` returns `{"ok":true}`. 401 body → E001. Do not use FastAPI's default 404/405 or 422. |
| `app/core/auth.py` | 401 body `{"error":"E001","mensaje":"no autorizado"}`. |
| `app/protocol/parser.py` | Implement steps 3–7: 8192-byte cap, E100/E102/E103/E104. Return segments rather than raising `Unevidenced`. |
| `app/domain/errors.py` | Add E001, E100, E101 (413), E102, E103, E104, E303, E304, E404, E510 (423, with `intentos`). Extend E301 with an optional `sugerencia`. |
| `app/services/dispatcher.py` | Implement the §1 order. Control format `^\d{1,2}$`. PING exemption. Add E202 (see §5). |
| `app/services/commands.py` | `_amount` → E303 per §3.3. Limit `> 50000`. Handler orders per §2. Add the failure counter and block per §3.5. ANULA reversal unconditional. Remove `Unevidenced` placeholders. |
| `app/domain/rules.py` | `TRANSFER_LIMIT`: replace `>= 100000` with `> 50000`. `format_saldo` must handle negatives and large values. |
| `app/domain/models.py` / `app/storage` | Add `fail_streak` and `blocked_attempts` to Account. Reset them in `__reset` (new state). |

State to add per account: `fail_streak: int` and `intentos: int`.
- On TRANSFER E506/E507 from src: `fail_streak += 1`.
- Block check: if `fail_streak >= 3` then `intentos += 1`, return E510. Do not increment `fail_streak`.
- On successful TRANSFER from src, or successful DEPOSITO to the account: `fail_streak = 0`, `intentos = 0`.

The golden suite must be updated, not forced green. The expected sequence `v2-s1` already contains no E510/E303. Add new fixtures from the log (ids above). `tests/test_golden_v2.py` stays red until E202 is implemented. Do not edit old fixtures.

Existing tests that encode now-disproven assumptions (the 501 placeholders, `{"status":"ok"}`, limit `>= 100000`) must be rewritten, and the change recorded.

## 5. E202: what is known (H-005 was not run, but evidence accumulated)

The algorithm is **still unknown**. Facts to help whoever tackles it:
- File `reports/control_rows.json` holds every `(message-without-control, control)` pair where the original accepted the control (91 pairs). Source: log.
- **Invariants:** the control is the same for any case and for any whitespace or punctuation in the message. Only alphanumeric characters count: `ALTA;Lu cia`, `ALTA;LUCIA` and `ALTA;lucia` all take 82; `CONSULTA;AC.0001`, `AC_0001`, `A-C-0-0-0-1` and `AC0001` all take 14 (ids 94–159).
- Controls observed range from 0 to 98, including **98** (`PONG;98`, `DEPOSITOX;98`). So the modulus is greater than 97, and the earlier "mod 97" idea is wrong or partial.
- `CONSULTA;AC-000d` gives `17 − 3d mod 97` for d = 1, 2, 3, 9 (14, 11, 8, 87). The d = 3 prediction was confirmed (id 947).
- The control for a message body containing `;` seems to be on the whole body. The same alphanumeric content gives the same control, even with different separators or splits.
- PING is never validated. The ALTA name matters (`Lucia` 82, `Mateo` 3).
- A first pass of polynomial-hash search over 26 rows of single-token commands found no fit.
- Practical fallback if not solved: E202 tests will fail wherever the message differs from a known one. Do not hard-code a lookup table of the known pairs as if it were the algorithm. If one is added as a stopgap, mark it `supuesto` and keep it out of the spec's "confirmado".

## 6. Items for the specification document

Use these IDs and evidence for the spec sections (README structure):

- **Entrada:** §1 steps 1–7. Evidence ids as in the table.
- **Integridad:** E201, E202 (partial) and the PING exemption.
- **Comandos:** §3, one block per command.
- **Memoria:** account and op counters, balances, op cancelled flag, fail streak and block.
- **Errores:** the table in §7.
- **Riesgos:** E510 blocking is permanent until a deposit or a successful transfer. A new client should not inherit the 8192-byte body cap silently. Negative balances via ANULA are a legacy risk (balances should be checked).

Confidence labels:
- **Confirmed (repeated):** E506 `> 50000` (several ids), E510 behavior, E303, E304, ANULA basic flow, E301 suggestions.
- **Probable (seen once):** the E301 distance rule, the exact length boundaries, the ANULA error forms for bad ids.
- **Assumed:** whether successful ANULA resets the block counter; whether E510 attempts count as failures.

## 7. Error table (all byte-exact)

| Code | Status | Body | When |
|---|---|---|---|
| E001 | 401 | `{"error":"E001","mensaje":"no autorizado"}` | missing or wrong token on a known route |
| E404 | 404 | `{"error":"E404","mensaje":"ruta desconocida"}` | unknown route or method |
| E100 | 400 | `{"error":"E100","mensaje":"json inválido"}` | body not JSON |
| E101 | 413 | `{"error":"E101","mensaje":"cuerpo demasiado grande"}` | body > 8192 bytes |
| E102 | 400 | `{"error":"E102","mensaje":"falta m"}` | no string `m` |
| E103 | 400 | `{"error":"E103","mensaje":"falta control"}` | no `;` in `m` |
| E104 | 400 | `{"error":"E104","mensaje":"segmento vacío"}` | empty segment |
| E201 | 400 | `{"error":"E201","mensaje":"control mal formado"}` | control not `^\d{1,2}$` |
| E202 | 400 | `{"error":"E202","mensaje":"control inválido"}` | control value wrong |
| E301 | 400 | `{"error":"E301","mensaje":"comando desconocido ","sugerencia":"…"}` (sugerencia optional) | unknown command |
| E302 | 400 | `{"error":"E302","mensaje":"aridad inválida"}` | wrong field count |
| E303 | 400 | `{"error":"E303","mensaje":"monto inválido"}` | bad amount |
| E304 | 400 | `{"error":"E304","mensaje":"origen y destino iguales"}` | src == dst |
| E401 | 404 | `{"error":"E401","mensaje":"cuenta inexistente"}` | unknown account |
| E402 | 404 | `{"error":"E402","mensaje":"operación inexistente"}` | unknown op |
| E506 | 422 | `{"error":"E506","mensaje":"límite excedido"}` | transfer amount > 50000 |
| E507 | 422 | `{"error":"E507","mensaje":"saldo insuficiente"}` | balance too low |
| E510 | 423 | `{"error":"E510","mensaje":"cuenta bloqueada","intentos":N}` | blocked source |

## 8. Not tested

- H-005 (control algorithm); see §5.
- Whether the `PING` exemption covers E201 only for exact `PING` command matches with other casing (lowercase tested, others not).
- E301 tie-break when two commands are within distance 2.
- Whether a successful ANULA resets the failure streak; whether `intentos` is capped.
- Unicode and non-ASCII commands or names, and non-ASCII digits as control (`PING;１２` is exempt).
- Concurrency and multiple instances.
- Any further service change after this pass. A sentinel re-check around 19:20–19:40 is recommended: replay h001 (ids 22–32), the E510 sequence (ids 1994–2004) and the 50000/50001 pair (ids 2782–2792), then compare.

## 9. Suggested implementation order

1. Pipeline and errors (§1, §7), including 404, 401, 413 and E100–E104.
2. Handlers (§3), amount parsing, E303/E304, limit `> 50000`.
3. E510 state machine.
4. ANULA unconditional reversal and negative saldo format.
5. E301 suggestion.
6. Add golden fixtures from the log. Run `python -m pytest` and `python -m tools.run_golden` after each step.
7. Update `Documentation.md` and the specification. Do not edit `Prompt.md`, `Plan.md` or `Implement.md`.
