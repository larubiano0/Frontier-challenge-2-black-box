# PROPOSE pass — hypotheses H-001 … H-008

_Mode: `PROPOSE`. Written 2026-10-10 ≈17:35 Bogotá (system clock check at 17:20:44 Bogotá = 18:20:44 EDT). **0 original requests were sent by this pass** (no curl/httpx/replay tool, no network). Deadline 20:00 Bogotá → **≈2 h 25 min left at write time** (2 h 39 min at the clock check)._

## 0. Corrections / qualifications to `Documentation.md` (raw logs re-inspected first)

I re-read `experimentos.jsonl` (ids 1–21), `experimentos_trace.jsonl`, `pruebas/ejemplos.jsonl`. Every id, status, body, `x_req`, the 12-equal/8-different table (§4) and the counter (21/21) match the raw files. Only these points need qualification:

1. **"E402 new in v2" (Documentation §3 "v2-only observations", §8) is not established.** v1 never exercised `ANULA` on a non-existent operation (EX-13/14 act on an operation that existed). E402 may be old behavior never seen. Treat it as *unknown version status*, not "new".
2. **Documentation §7's "−3 per unit" lead is reproducible, but the simple numeric-amount form is falsified by one row** (my offline check, `tools/analysis/resid.py`, `predict.py`): with 100000→12 as anchor, "control ≡ −3·amount (mod 97)" gives 55 for 120000 ✔ (id 10) but **77 for 40000, observed 86** (id 8) → off by +9. So "amount enters numerically" is at best a partial model (length or char-level effects).
3. **Bound on the E506 threshold that Documentation does not state:** v2 id 17 (`TRANSFER … AC-0002→AC-0001 50000`, balance 40000) returned **E507, not E506**. Either the limit is >50000 (limit checked first), or the balance check runs before the limit check (inference; both unproven). Documentation implies only "40000 passes".
4. Timestamp in Documentation header (≈17:05) is stale; remaining time is now as above.

## 1. State of knowledge (≤15 lines)

- **Requests consumed:** 21 (H-000, ids 1–21, `seq v2-s1`: 1 reset + 20 `/msg`). `tools/original_request_counter.json`: day_count 21, lifetime 21 (limit 8,000/day). True token consumption outside this tooling: **unknown**. This pass: **0**.
- **Evidence classes:** historical v1 = EX-1…20 (not in the log). Observed v2 = ids 1–21 (one observation each). Confirmed unchanged = **none**; confirmed changed = **none**; unknown = everything not in §8 of Documentation.
- **Golden re-run by me (`python -m tools.run_golden`, `python -m pytest`):** 1 sequence, 0 passing; requests 18/21 = 85.7 % (`/msg` 17/20 = 85.0 %); Sequence Agreement 0 %; 0 new regressions; known mismatches = steps 2,3,4 (all E202 cascade). pytest: 62 passed, 1 failed (`test_v2_sequence[v2-s1]`). Max latency 3.2 ms. (The rerun regenerated `reports/golden_v2_last_run.json`; fixtures/baseline untouched.)
- **FR-0153 (3 changes):** candidates D-A (`saldo` int→`"x.yy"` string, ids 6,9,12,20) and D-B (`TRANSFER 100000` 200→422 E506, id 11) are *descriptive only*. **Third change: unidentified.** D-C is *possibly* a consequence of D-B (not separable: `ANULA` over an existing op never observed in v2).
- **Inference:** all 13 messages with an accepted control in v2 (ids 4–9,11,12,14–17,19) behave like v1 at the control stage (EX-3,4,5,6,7,8,9,10,11,13,15,16,18) → the control algorithm very probably did **not** change; it is needed, not a change candidate.
- **Placeholders that are guaranteed failures if the hidden set touches them:** 501 `not_implemented` (non-JSON, missing `m`, no `;`, odd amounts, empty ALTA name, same-account TRANSFER, unreversible ANULA); auth body (`app/core/auth.py:25`), `/health` body (`app/api/routes.py:17`).
- **Hard design constraint discovered offline:** any probe `m` needs a **valid control**, and the algorithm is unknown. Only these `(message → control)` pairs are *known valid in v2*: `ALTA;Lucia;82`, `ALTA;Mateo;3`, `CONSULTA;AC-0001;14`, `CONSULTA;AC-0002;11`, `CONSULTA;AC-0009;87`, `DEPOSITO;AC-0001;250000;86`, `DEPOSITO;AC-0002;700;35`, `TRANSFER;AC-0001;AC-0002;40000;86`, `…;100000;12`, `…;120000;55`, `TRANSFER;AC-0002;AC-0001;50000;23`, `ANULA;OP-0003;66`, `CONSULTa;AC-0001;14` (ids 4,5,6,7,8,9,10,11,12,14,16,17,19, 20). **H-001…H-004, H-007, H-008 are designed to use only these**, so they cost no control-scanning.

## 2. Ranking

Score = (est. hidden tests touched × P(resolve)) / requests, all three factors are my **inferences** (v1 sample: 2/20 ANULA, 5/20 TRANSFER, 2/20 control errors, 1/20 unknown command, 1/20 arity; hidden mix 40/45/15).

| ID | Hypothesis (one line) | Category | v1→v2 change candidate? | Est. requests (incl. resets) | Suggested cap | Expected value of information | Risk if wrong |
|---|---|---|---|---|---|---|---|
| **H-001** | `ANULA` over an *existing* op in v2 still returns `{"ok":true,"anulada":…}`, reverses both balances, and repeats → `{"ok":false,"motivo":"ya anulada"}` | cancelación / transiciones de estado | **YES — best candidate for the 3rd change** | 11 | **14** | Very high: ~8–12 tests (ANULA in ~10 % of examples); P≈0.9; score ≈0.9/req | Low (state-free outside own token); may reveal the E506 cumulative effect and abort its tail |
| **H-002** | E506 is a per-operation threshold in (50000,100000], not cumulative, and is checked before balance | límites/fronteras (+precedencia) | YES (explains D-B; 2nd/3rd change) | 19 (+≤100 optional stage B) | **24** (stage B needs its own cap) | High: 3–6 tests; P≈0.7 bracket, boundary needs stage B; score ≈0.2/req | Low; stage B may spend ≤100 on control scanning |
| **H-003** | Entrada: auth failures, unknown route/method, non-JSON / missing `m` / no-`;` bodies, `/health`, each answer with a specific status/body that differs from our placeholders | entrada/rutas/auth | Unknown (no v1 evidence; cannot be called a change) | 14 | **17** | High for the 40 single-request tests: 3–8 tests; P≈0.9; score ≈0.4/req | **Expected 401/403 → waiver of the abort rule needed for probes 2–5** |
| **H-004** | Validation precedence: control-format → control-value → command → arity → account → limit → balance, and PING validates its control | precedencia / integridad | Possible (precedence is a candidate category) | 13 | **16** | High: 5–10 tests with combined errors; P≈0.85; score ≈0.5/req; also decides whether `CONSULTA`/`PING` can be a cheap E202 oracle (gates H-005/H-006) | Low |
| **H-005** | Control = affine function mod 97 of the message (place-value weights −3·10^p on trailing digits; command case-insensitive); designed one-variable family | integridad | Unlikely a change (inference); needed regardless | ≈25 + up to ≈390 scan | **420** | Medium-high but low P: 4–10 tests (E202/E201-tests + their cascades); P≈0.3 in 420 req; score ≈0.01/req | Spends the most budget; P(no model found) ≈0.7 |
| **H-006** | Amount parsing (0, negative, decimal, leading zeros, huge, non-numeric) and same-account TRANSFER give specific errors instead of 501; can be probed with a dummy control iff H-004 shows control is checked last | parsing / límites | Possible (parsing is a candidate category; decimals ↔ D-A) | 12 | **14** | Medium: 3–6 tests, removes 501s; P≈0.5 (conditional); score ≈0.15/req | If control precedes amount, outcome is all E202 → wasted 12 |
| **H-007** | Command grammar: case, whitespace, empty fields, trailing `;`, extra args, id case are handled as in v2 id 12 (`CONSULTa` accepted) | parsing | Possible | 11 | **13** | Medium: 3–5 tests; P≈0.8; score ≈0.3/req; leaks info on the control algorithm (what text is hashed) | Low |
| **H-008** | ALTA duplicates are allowed and just consume the next `AC-n` | transiciones de estado | Unlikely | 4 | **6** | Low-medium: 2–3 tests; P≈0.9; score ≈0.5/req | Negligible |

**Drop entirely if <90 min remain** (i.e. after ≈18:30): H-005 (control scanning), H-006, H-008; shrink H-002 to sequence (a)+(c) only. Keep H-001, H-004, H-003 (all ≤16 requests, results implementable in minutes).

**Reserve:** keep **≥40 requests** and a 19:20–19:40 Bogotá slot for a *sentinel re-check* (see §4); the original may change again.

## 3. Detailed blocks

Notation: `S(n)` = step n of the sequence. "v1 EX-n" = historical, `id n` = observed v2. "cur." = what `app/` does now.

---

### H-001 — ANULA over an existing operation (cancelación)

1. **Statement.** In v2, after two TRANSFERs of 40000 (OP-0002, OP-0003) from AC-0001 to AC-0002, `ANULA;OP-0003;66` returns `200 {"ok":true,"anulada":"OP-0003"}`, restores 40000 to AC-0001 and removes 40000 from AC-0002, and a second identical `ANULA` returns `200 {"ok":false,"motivo":"ya anulada"}`. One mismatch at S(8), S(9), S(10) or S(11) refutes it.
2. **Current evidence.** *Historical v1:* EX-13 (`ANULA;OP-0003;66` → 200 `{"ok":true,"anulada":"OP-0003"}`), EX-14 (repeat → 200 `{"ok":false,"motivo":"ya anulada"}`), EX-11→EX-19 show balance reversal (110000 → after cancel AC-0002 40000 = EX-19 40700 incl. deposit). *Observed v2:* ids 14, 15 → 404 E402 on a non-existent OP-0003 (OP-0003 was never created because id 11 was rejected). **Absent:** any v2 `ANULA` on an existing operation; ANULA on DEPOSITO ops (never observed even in v1); who is credited/debited on reversal.
3. **Competing explanations.** H-001a unchanged v1 semantics. H-001b ANULA marks the op but does **not** reverse balances (state-transition change). H-001c reversal affects only the destination (or only the source). H-001d ANULA of a TRANSFER is now rejected (new error code/status). H-001e repeat now yields `ok:true` again / a different message / a 4xx. H-001f the 2nd 40000 TRANSFER (S(6)) is itself rejected (cumulative E506) → ANULA target missing; **this is the confound D-C**; see branch below.
4. **Probe sequence `h001-anula`** (all controls known valid in v2):
   `S(1) POST /__reset` · `S(2) {"m":"ALTA;Lucia;82"}` · `S(3) {"m":"ALTA;Mateo;3"}` · `S(4) {"m":"DEPOSITO;AC-0001;250000;86"}` · `S(5) {"m":"TRANSFER;AC-0001;AC-0002;40000;86"}` · `S(6) {"m":"TRANSFER;AC-0001;AC-0002;40000;86"}` · `S(7) {"m":"CONSULTA;AC-0002;11"}` · `S(8) {"m":"ANULA;OP-0003;66"}` · `S(9) {"m":"CONSULTA;AC-0002;11"}` · `S(10) {"m":"ANULA;OP-0003;66"}` · `S(11) {"m":"CONSULTA;AC-0001;14"}`.
   Branch: if S(6) is `422 E506` (cumulative limit) send `{"m":"DEPOSITO;AC-0002;700;35"}` (→ OP-0003, id 19 pattern), then continue from S(8) with the deposit as target (AC-0002 expected `"7.00"`→ after cancel `"0.00"`); count +1.
5. **Predictions** (S(1)–S(6) expected: 200 `{"ok":true}`; 201 AC-0001; 201 AC-0002; 200 OP-0001; 200 OP-0002; 200 OP-0003 under all explanations except f):

| step | a: v1 semantics | b: no reversal | c: dst-only reversal | d: TRANSFER ANULA rejected | e: repeat changed |
|---|---|---|---|---|---|
| S(7) | 200 `saldo:"800.00"` | same | same | same | same |
| S(8) | 200 `{"ok":true,"anulada":"OP-0003"}` | same | same | **non-200 / other body (new)** | same |
| S(9) | `"400.00"` | `"800.00"` | `"400.00"` | `"800.00"` | `"400.00"` |
| S(10) | 200 `{"ok":false,"motivo":"ya anulada"}` | same | same | (same as S(8) error) | **any other status/body** |
| S(11) | `"2100.00"` | `"1700.00"` | `"1700.00"` | `"1700.00"` | `"2100.00"` |

   Column c = destination-only reversal (AC-0002 debited, AC-0001 not credited). Source-only reversal (not tabulated) would give S(9) `"800.00"`, S(11) `"2100.00"`. The pair (S(9), S(11)) separates a / b / c / source-only; b and (d) coincide on balances because nothing was cancelled, and are separated by S(8).
6. **Stop / abort.** Stop early after S(11) (nothing more is useful). If S(8) returns a body that is not in the table, still run S(9)–S(11) (3 requests) to learn its state effect. **Abort** on `X-Frontier-Infra: rate-limit`, any 401/403, any 5xx, or if S(1)–S(5) disagree with ids 4–8.
7. **Accounting.** 11 requests (1 reset). Cap 14 = 11 + 1 for the branch + 2 spare. Total used would be 21+11=32.
8. **Impact.** Sequence tests (2–5 and 6–12 steps) that cancel anything (≈ 8–12 tests, inference). Confirms/refutes S-3 (`app/services/commands.py:94`, only the E402 half) and the **v1-derived** ANULA scaffolding (`commands.py` lines ~95–110, tagged `[v1]`); replaces the 501 branch on "unreversible ANULA" only partly. Closes the golden gap "ANULA on existing op" (no v2 fixture exists).
9. **Change bookkeeping.** v1: EX-13/14. v2 under test: S(8)–S(11). If outcome ≠ a, the difference **cannot** be a consequence of D-A (display) or D-B (limit): the probe never touches amounts ≥100000, and S(5)/S(6) are below the limit (ids 8 and EX-7 precedent). It would be an **independent** change (third FR-0153 change, strongest candidate: categories "cancelación / state transitions"). If outcome = a, D-C is *entirely* a consequence of D-B and E402 gets a second v2 observation context (OP never existed vs. existing).

---

### H-002 — Shape of the E506 limit

1. **Statement.** E506 in v2 is raised by a **per-operation** check `amount > T` with 50000 < T ≤ 100000 (so ≥100000 fails, 50000 passes), independent of previously transferred volume, and is evaluated **before** the balance check (E507). Refuted by: fresh-state 100000 succeeding (cumulative), a 50000 transfer failing with E506 (T ≤ 50000), or a zero-balance 120000 returning E507.
2. **Current evidence.** *Hist. v1:* EX-9 120000 → E506; EX-10 100000 → OK (OP-0003); EX-16 50000 with insufficient funds → E507. *Observed v2:* id 10 (120000, balance 210000) E506; id 11 (100000, AC-0001 has 210000, already 40000 transferred) E506; id 8 (40000) OK; id 17 (50000, AC-0002 balance 40000) **E507** (so either limit >50000 or balance-before-limit). **Absent:** any amount in (40000,100000) that exceeds the balance-free case; fresh-state 100000; two successive transfers; order of E506 vs E507.
3. **Competing.** H-002a per-op threshold lowered (T∈(50000,100000)). H-002b per-op **inclusive** (`>= 100000`; v1 was `> 100000`). H-002c unit change (inputs now cents, limit now e.g. 1000.00 → same observable as a/b). H-002d cumulative per source account since reset (40000 + 100000 > L). H-002e global cumulative. H-002f balance check precedes limit check. **Declared inseparable by any probe:** a vs c (observable behavior identical); b vs a with T=99999 only separable by stage B (needs a new control).
4. **Probe sequences** (known controls only):
   - `h002-a` (5): `POST /__reset` · `ALTA;Lucia;82` · `ALTA;Mateo;3` · `DEPOSITO;AC-0001;250000;86` · `TRANSFER;AC-0001;AC-0002;100000;12`.
   - `h002-b` (9): `POST /__reset` · `ALTA;Lucia;82` · `ALTA;Mateo;3` · `DEPOSITO;AC-0001;250000;86` · `TRANSFER;AC-0001;AC-0002;40000;86` · `TRANSFER;AC-0001;AC-0002;40000;86` · `TRANSFER;AC-0002;AC-0001;50000;23` · `TRANSFER;AC-0001;AC-0002;40000;86`.
   - `h002-c` (5): `POST /__reset` · `ALTA;Lucia;82` · `ALTA;Mateo;3` · `TRANSFER;AC-0001;AC-0002;120000;55` · `TRANSFER;AC-0001;AC-0002;100000;12` (AC-0001 balance 0 in both).
   - *Stage B (optional, separate cap, ≤100):* `h002-d` fresh funded state + `TRANSFER;AC-0001;AC-0002;99999;cc` with `cc` first = 24 (model guess, ~1 % confidence), then scan 0…96 until the reply is not E202.
5. **Predictions.**

| probe step | a (T lowered, 50000<T<100000) | b (≥100000) | c (cents) | d (cum. per source ≥/>100000) | e (cum. global) | f (balance first) |
|---|---|---|---|---|---|---|
| h002-a S5 (100000) | 422 E506 | 422 E506 | 422 E506 | **200 OP-0002** | **200 OP-0002** | 422 E506 |
| h002-b S5, S6 (40000×2) | 200 OP-0002, 200 OP-0003 | same | same | 200, 200 | 200, 200 | same |
| h002-b S7 (50000 AC-0002→AC-0001, AC-0002 has 80000) | 200 OP-0004 | 200 | 200 | **200** (AC-0002 outgoing 0) | **422 E506** (80000+50000>100000) | 200 |
| h002-b S8 (40000 again) | 200 OP-0005 | 200 | 200 | **422 E506** (AC-0001 outgoing 120000) | **422 E506** | 200 |
| h002-b S7 if T ≤ 50000 | 422 E506 (then S8 200) | — | — | — | — | — |
| h002-c S4 (120000, bal 0) | 422 E506 | 422 E506 | 422 E506 | 422 E506 | 422 E506 | **422 E507** |
| h002-c S5 (100000, bal 0) | 422 E506 if limit first | 422 E506 | 422 E506 | 422 E506 | 422 E506 | **422 E507** |
   Outcomes select: S5 of h002-a separates {d,e} from {a,b,c,f}; S7/S8 of h002-b separate d from e and expose T≤50000; h002-c separates f. a/b/c remain jointly "per-op, ≥100000 fails, 50000 passes".
6. **Stop / abort.** Run `h002-a` first; if it returns 200 (cumulative/state effect) skip `h002-c`, do `h002-b`. Stop when a single row of the table is selected. Abort on rate-limit header / 401/403 / any 5xx / any divergence in the *known* steps (S(1)–S(4)).
7. **Accounting.** 5+9+5 = **19** (3 resets). Cap 24. Stage B separately ≤100.
8. **Impact.** TRANSFER hidden tests near the boundary (≈3–6). Confirms/refutes S-2 (`app/domain/rules.py:21`, `transfer_exceeds_limit`; check order at `commands.py:80`). Closes the golden gap on E506-vs-E507 precedence and on cumulative state.
9. **Change bookkeeping.** v1: 100000 OK, 120000 E506 (EX-9/10). v2: 100000 and 120000 E506. h002-a (state with no prior transfer) is exactly the clean v1-equivalent state (v1 EX-10 had 40000 already sent, so `h002-b` S5-S6 re-create that history). Result d/e ⇒ the limit's *state dependence* is the change (independent of D-A); a/b/c ⇒ boundary/limit change; c would link D-A and D-B as **one** unit-change (then they are one change, freeing a slot for the third) — declared **not separable** from a by behavior alone.

---

### H-003 — Entrada: auth, routes, methods, bodies, `/health`

1. **Statement.** Each of the 14 probes below has a deterministic status/body that **differs from our placeholders** in at least one of: auth failure (cur. `401 {"error":"unauthorized"}`), non-JSON/missing-`m`/no-`;` body (cur. `501 {"error":"not_implemented"}`), `/health` (cur. `200 {"status":"ok"}` requiring auth). Refuted per-probe by an exact match.
2. **Current evidence.** *Observed v2:* only `POST /__reset` → 200 `{"ok":true}`, JSON, no `X-Req` (id 1) and `/msg` JSON bodies. *README:* "Con otro token o sin token, responde como el original", "Cualquier otra ruta responde exactamente lo mismo que el original". **Absent:** every probe below (unknown version status).
3. **Competing.** For auth: 401 vs 403 vs 200 (no enforcement), JSON vs plain text vs empty. Routes: 404 JSON `{"error":…}` vs plain `Not Found` vs FastAPI-like `{"detail":"Not Found"}`; methods: 405 vs 404. Body: 400 with an `E1xx/E2xx` code vs 422 `{"detail":[…]}` vs 500 vs the "no-`;`" case mapping to E201/E302. Alternatives cannot be enumerated exactly; the **literal observation** is the datum.
4. **Probe sequence `h003-entrada`** (no resets needed; all state-free; one reset first for hygiene is *not* needed). Literal order:
   1 `GET /health` (token) · 2 `GET /health` (no `Authorization`) · 3 `POST /msg {"m":"PING;64"}` (no `Authorization`) · 4 `POST /msg {"m":"PING;64"}` with `Authorization: Bearer invalid-probe-token` · 5 `POST /__reset` (no `Authorization`; *may mutate nothing*) · 6 `GET /msg` (token) · 7 `POST /nope` (token, body `{}`) · 8 `GET /nope` (token) · 9 `POST /msg` raw body `not json` (`Content-Type: application/json`) · 10 `POST /msg {}` · 11 `POST /msg {"m":5}` · 12 `POST /msg {"m":""}` · 13 `POST /msg {"m":"PING"}` · 14 `POST /msg {"m":"PING;64"}` with `Content-Type: text/plain`.
5. **Prediction table:** a prediction per explanation is impossible without evidence (that is the point); record `(status, exact body bytes, content-type)` per step. Decision rules: step 3/4 equal → single auth failure path; step 2 ≠ 200 → `/health` requires auth (our replacement already requires it; change only if 200); step 6 vs 7 vs 8 → 404 vs 405 separation; step 9–13 → replace each `501` branch; step 14 → body parsing ignores content-type or not.
6. **Stop / abort.** No early exit (14 independent singletons) except: stop after step 8 if steps 1–8 show an `X-Frontier-Infra: rate-limit`. **Waiver required from the researcher:** the standard abort rule "any 401/403" must be waived for steps 2–5 (they are *expected* auth failures). Abort on rate-limit header or a connection error. Never log the real token; the wrong-token probe uses the literal `invalid-probe-token`.
7. **Accounting.** 14 requests, 0 resets. Cap 17 (2 retries if a step is ambiguous, 1 spare).
8. **Impact.** The README explicitly lists auth and unknown routes → likely present among the **40 single-request tests** (inference; ≈3–8 tests). Replaces/confirm `app/core/auth.py:25`, `app/api/routes.py:17,25`, and the 501 branches in `app/protocol/parser.py:25-30`. Closes golden gaps: none exist (no fixtures) → creates 14 new single-step v2 fixtures.
9. **Change bookkeeping.** No v1 evidence exists ⇒ it cannot be labelled a *change*; it only fills `unknown` entries. (Low probability, ≈5 %, that a body format here is the third change — inference.)

---

### H-004 — Validation precedence & what the control gates

1. **Statement.** Precedence is: control **format** (E201) → control **value** (E202) → command (E301) → arity (E302) → account existence (E401) → limit (E506) → balance (E507); and `PING` validates its control. Each probe below refutes one inequality by yielding the other error.
2. **Current evidence.** *Observed v2:* id 18 (`DEPOSITO…;5X` → E201, rest valid); id 3 (`ALTA;Lucia;83` → E202); id 13 (`SALDOS;AC-0001;38` → E301: control unknown validity); id 21 (`ALTA;Lucia;Gomez;11` → E302: control validity unknown); id 16 (`CONSULTA;AC-0009;87` → E401, control valid); id 2 (`PING;64` → pong). **Absent:** every ordering between control, command, arity, account; whether `PING`/`CONSULTA` check control. Current order is a `supuesto` (`app/services/dispatcher.py` lines 3–10, 29–37).
3. **Competing.** H-004a (the statement). H-004b command before control. H-004c arity before control value. H-004d account existence before control value. H-004e control not checked for `PING` (and maybe other commands). H-004f control value check after E301/E302 but before account.
4. **Probe sequence `h004-prec`** (all state-free until the last two; probes 3–9 use messages whose valid control is known or known-different):
   `S1 POST /__reset` ·
   `S2 {"m":"PING;65"}` (64 is valid) ·
   `S3 {"m":"PING;5X"}` ·
   `S4 {"m":"SALDOS;AC-0001;39"}` (38 known → E301) ·
   `S5 {"m":"SALDOS;AC-0001;5X"}` ·
   `S6 {"m":"ALTA;Lucia;Gomez;12"}` (11 known → E302) ·
   `S7 {"m":"ALTA;Lucia;Gomez;5X"}` ·
   `S8 {"m":"CONSULTA;AC-0009;88"}` (87 valid; no accounts exist after reset) ·
   `S9 {"m":"CONSULTA;AC-0009;87"}` (no accounts; known control) ·
   `S10 {"m":"TRANSFER;AC-0001;AC-0002;120000;55"}` (no accounts; limit vs account) ·
   `S11 {"m":"DEPOSITO;AC-0002;700;35"}` (no accounts) ·
   `S12 {"m":"ALTA;Mateo;03"}` (3 valid; leading zero) ·
   `S13 {"m":"ALTA;Mateo;100"}` (3+97).
5. **Predictions.**

| step | a (cur.) | b cmd first | c arity first | d account first | e PING unchecked |
|---|---|---|---|---|---|
| S2 `PING;65` | 400 E202 | 400 E202 | 400 E202 | 400 E202 | **200 `{"pong":true}`** |
| S3 `PING;5X` | 400 E201 | E201 | E201 | E201 | **200 pong** (or E201 if format only) |
| S4 `SALDOS;…;39` | **400 E202** (38 was valid) | **400 E301** | E202 | E202 | — |
| S5 `SALDOS;…;5X` | 400 E201 | **400 E301** | E201 | E201 | — |
| S6 `ALTA;Lucia;Gomez;12` | **400 E202** (11 valid) | E202 | **400 E302** | E202 | — |
| S7 `ALTA;Lucia;Gomez;5X` | 400 E201 | E201 | **400 E302** | E201 | — |
| S8 `CONSULTA;AC-0009;88` | **400 E202** | E202 | E202 | **404 E401** | — |
| S9 `CONSULTA;AC-0009;87` | 404 E401 (sanity) | same | same | same | — |
| S10 `TRANSFER … 120000;55` no accts | 404 E401 (accounts before limit, cur. `supuesto`) | — | — | — | alt.: 422 E506 (limit first) |
| S11 `DEPOSITO;AC-0002;700;35` no accts | 404 E401 (supuesto `commands.py`) | — | — | — | alt.: other |
| S12 `ALTA;Mateo;03` | 201 AC-0001 if int-parsed | — | — | — | else E201/E202 |
| S13 `ALTA;Mateo;100` | 400 E202 (strict equality) | — | — | — | 201 AC-0002 ⇒ compared mod 97 |
   Because E202/E201/E301/E302 are mutually distinct bodies, every row yields a mechanical order. If S4 gives E301 *and* S6 gives E302, the observed order of the three early checks is E301/E302 → (E202) — exactly the case where the control value never needs to be known for malformed-command/arity tests.
6. **Stop / abort.** No early stop (13 singletons) except: skip S12–S13 if S2–S11 show unexpected 5xx. **Abort** on rate-limit header, 401/403, 5xx.
7. **Accounting.** 13 requests (1 reset). Cap 16 (1 retry of any ambiguous step, 2 spare).
8. **Impact.** ~5–10 tests with combined errors (e.g. unknown command + bad control, bad account + bad control). Rewrites `app/services/dispatcher.py` order (currently documented as `supuesto`); decides whether E202 can be a cheap one-request oracle for H-005 (S2/S8 show it) and whether H-006 can use dummy controls (S10, S11).
9. **Change bookkeeping.** v1 has *no* precedence observation that conflicts: E301/E302 rows cannot reveal order. So it is `unknown`, a possible change under category *precedence* (≈10 % as 3rd change — inference). Independent of D-A/D-B: no amount ≥100000 sent to a funded account; S10 (limit vs account) is the only overlap with D-B and is read-only on the limit.

---

### H-005 — Control algorithm (designed experiment; not a blind sweep)

**Offline math already done (no requests; `tools/analysis/control_fit.py`, `control_iban.py`, `control_affine.py`, `resid.py`, `amt.py`, `predict.py`):** 13 accepted rows (+1 rejected: `ALTA;Lucia`→83). Searched 0 hits over: sum/xor/len/CRC32/Adler/polynomial (B=2…259, both directions)/position-weighted, 10 text variants (raw, upper, lower, ±`;`, args only, digits, reversed), M∈{90…129,127,128,251,255,256,1000}, `x`, `−x`, `x+1`; affine `b+a·Σ f(c)w` with free a,b over 17 moduli × 10 variants × 4 char maps × 5 weight families × all B<M; IBAN/ISO 7064 mod 97-10-style encodings. **All 0 hits.** Structural facts (inference, ids 6,9,16 / 10,11):
- `CONSULTA;AC-000d`: d=1→14, 2→11, 9→87 ⇒ c ≡ 17 − 3d (mod 97) (two constraints, one parameter: 1/97 chance coincidence).
- `…;120000` vs `…;100000`: Δ=43 ≡ −3·20000 (mod 97) ✔ second independent coincidence (place weight −3·10⁴ ≡ 70).
- `…;40000` breaks the linear-numeric form by +9 (see §0.2). `CONSULTa` = `CONSULTA` (14), so the command text is case-normalized or excluded (ids 6, 12).
- All controls < 97; `ALTA;Mateo;3` unpadded.
**Rows needed:** a char-wise linear-mod-97 model with place-value weights has ≈4 unknowns (a, B, b, char map, per-command offset) ⇒ **≥ 4–6 new independent rows**; each new row = one scan ≤97 (E[·]≈49; range could be 0…99 → ≤100). A fully free per-position weight model needs one row per distinct position-class (≥10).

1. **Statement.** control(msg) = `b_cmd + Σ ord'(c_i)·w_i (mod 97)` with `w` for the last k characters equal to −3·10^p (p = position from the end), command compared case-insensitively. Refuted by the first prediction below that returns E202.
2. **Current evidence.** ids 3 (rejected 83), 4,5,6,7,8,9,10,11,12,14,16,17,19 (accepted) + the matching EX rows; id 18 (E201 `5X`). **Absent:** `PING` control rule, CONSULTA/PING validation (H-004), controls for any other message.
3. **Competing.** 5a place-value polynomial mod 97 (the lead); 5b char-class-specific weights (letters vs digits); 5c includes length or arg count; 5d CRC-like (no linear structure) → then **unidentifiable** within any budget (declare). 5e control depends on the number of fields.
4. **Probe design `h005-ctrl`** (oracle: after one reset and `ALTA;Lucia;82`, `ALTA;Mateo;3`; accepted ⇔ response ≠ E202; use CONSULTA on existing accounts for state-freedom; precondition: H-004 S8 showed control precedes account lookup, else restrict to AC-0001/AC-0002 messages).
   *Stage 1 — one-shot prediction checks* (only the digit-place family, base message `CONSULTA;AC-0001` c=14, state AC-0001/AC-0002 exist):
   - `CONSULTA;AC-0002;11` is known. New: need account ids that exist → impossible beyond AC-0002 unless more ALTAs. Use `ALTA;Lucia;82`, `ALTA;Mateo;3` plus additional `ALTA;Xxx;cc` messages themselves *need* controls. Therefore Stage 1 uses **nonexistent-account CONSULTAs** and relies on H-004 S8 (control before account): predicted controls: `CONSULTA;AC-0003;8`, `;AC-0005;2`, `;AC-0010;84`, `;AC-0011;81`, `;AC-0100;8`.
   *Stage 2 — one-variable scans* (each ≤97 requests until non-E202): (i) `CONSULTA;AC-0001X` length change? (ii) `CONSULTA;ac-0001` (case of id), (iii) `PING;x` if H-004 shows PING validated: a *free oracle family* with command fixed (arg text varies; arity E302 would then pre-empt — only if control first), (iv) `ALTA;Lucia;` different name lengths (names vary letters, digits constant). Choose ≤4 anchors adaptively.
5. **Predictions.** Under 5a: every Stage-1 probe is **not E202** (E401 for nonexistent). Under 5b/5c/5d: E202 at the first probe whose characters are not covered, then the scan returns the true value; the table of (message, true control) rows solves a linear system mod 97 (6 rows ⇒ solves a,B,b if the family is right; the 7th verifies). 5d is declared if 3 independent anchors fit **no** linear model after adding them to the 13 rows.
6. **Stop / abort.** Stop as soon as a model fits all rows (≥ 17) and predicts 2 held-out messages. Stop and *declare unidentifiable* after 4 scans without a fit or when cap is reached. Abort on rate-limit header, any 401/403, 5xx. Rate ≤4 req/s (≈25 s per scan).
7. **Accounting.** reset 1 + ALTA 2 + Stage 1 5 + ≤4 scans × ≤97 = **≤ 396**. Cap **420** (must be set by the researcher; I would *not* approve it with <2 h left).
8. **Impact.** Only the **invalid-control tests** (E202; estimate ≈4–10 tests incl. cascades like v2-s1 steps 2–4) and sequences containing one. Replaces the gap at `dispatcher.py:31`. Closes golden failure `v2-s1` (3 steps). **P(success) ≈ 0.3 (inference)** because 0 of ~10⁵ simple models fit. Cheap partial alternative: none (a lookup table would fake passes — not allowed).
9. **Change bookkeeping.** Not a change candidate (13/13 v2 rows behave as v1; inference). Independent of D-A/D-B.

---

### H-006 — Amount parsing and same-account TRANSFER

1. **Statement.** For `DEPOSITO`/`TRANSFER`, amounts `0`, `-5`, `1.5`, `007`, `abc`, empty and 20-digit values each return a specific non-501 error (not E202) *when sent with a dummy control* — i.e. amount/shape validation happens before the control value. Refuted by E202 (control first) → then amounts need scanning and the hypothesis should be dropped.
2. **Current evidence.** *Observed v2:* only plain positive integers (ids 7,8,10,11,17,19). *Hist. v1:* same. **Absent:** every edge case. Current: `501` (`commands.py:25`), same-account `501` (`commands.py:79`).
3. **Competing.** E202 first (control precedes arguments) vs E5xx-style amount errors (new codes unknown) vs E302/E201 reuse vs acceptance (e.g. `007` → 7).
4. **Probe `h006-amt`** (needs H-004 outcome S8=E202? **if S8 shows account (E401) before control, this probe is meaningless; if control before everything, run only S2–S3 as the sentinel and stop**): `POST /__reset` · `ALTA;Lucia;82` · `DEPOSITO;AC-0001;0;1` · `DEPOSITO;AC-0001;-5;1` · `DEPOSITO;AC-0001;1.5;1` · `DEPOSITO;AC-0001;007;1` · `DEPOSITO;AC-0001;abc;1` · `DEPOSITO;AC-0001;99999999999999999999;1` · `TRANSFER;AC-0001;AC-0001;100;1` · `ANULA;;1`.
5. **Prediction.** Dummy control `1` is invalid for every message (prob. 96 %). If control-first: all 8 probes → 400 E202 → hypothesis refuted at probe 1 (stop after 2). If amount-first: 8 distinct bodies (record). Mixed order (some E202, some not) ⇒ per-field precedence.
6. **Stop.** First E202 at `…;0;1` and `…;abc;1` ⇒ stop (2 requests). Abort as above.
7. **Accounting.** 10 requests (1 reset). Cap 14.
8. **Impact.** Removes up to 6 `501` branches; also tests whether decimals are accepted now that `saldo` is decimal (D-A input side).
9. **Change bookkeeping.** Possible *parsing* change (category) tied to D-A: if `1.5` is accepted and shown as `"0.01"`/`"1.50"` (not integer), the cents-vs-decimal question for D-A is answered; otherwise independent.

---

### H-007 — Command grammar and normalization

1. **Statement.** Command matching is case-insensitive for *all* commands and the control is independent of command case (as observed for `CONSULTa`, id 12), but whitespace and trailing/empty fields are **not** trimmed. Refuted by a pong for a padded message or a non-pong for `ping;64`.
2. **Current evidence.** *Hist. v1:* EX-11. *Observed v2:* id 12 (`CONSULTa;AC-0001;14` → 200). **Absent:** other commands, whitespace, empty fields, extra args to PING, lowercase ids. Current: case-insensitive via `msg.command.upper()` (`dispatcher.py:32`); everything else follows the parser at `parser.py` (no trim).
3. **Competing.** 7a as stated. 7b the control hashes the *uppercased* command; 7c the control hashes the raw text (then `ping;64` → E202); 7d fields trimmed (`" PING;64"` → pong); 7e `PING` with extra args → pong (arity ignored for 0-ary).
4. **Probe `h007-grammar`:** `POST /__reset` · `ALTA;Lucia;82` · `ping;64` · `Ping;64` · ` PING;64` · `PING;64 ` · `PING;;64` · `PING;x;64` · `PING;64;` · `CONSULTA;ac-0001;14` · `CONSULTA;AC-0001;014`.
5. **Predictions (per explanation):** `ping;64` → 7a pong; 7c E202. ` PING;64` → 7a E301 (`" PING"` unknown, message would be `"comando desconocido "`, see trailing space in id 13) or E202/E201; 7d pong. `PING;;64` → 7a E302 (arity) / E202 per H-004 order. `PING;x;64` → E302 (arity) or E202. `PING;64;` → E201 (empty control) or E302. `CONSULTA;ac-0001;14` → 7a E401 if the id compare is case-sensitive, E202 if control hashes raw text. `CONSULTA;AC-0001;014` → leading zero in control: 200 (int-parsed) vs E202.
6. **Stop.** Stop after the first 4 probes if all are exactly 7a-predicted and nothing new; abort on rate-limit/401/403/5xx.
7. **Accounting.** 11 requests (1 reset). Cap 13.
8. **Impact.** 3–5 tests with odd casing/whitespace; exercise the parser at `app/protocol/parser.py`. Side info for H-005 (what text is hashed).
9. **Change bookkeeping.** Possible parsing change (category); v1 shows only `CONSULTa` (EX-11) which v2 matches (id 12) ⇒ "case-insensitive" is **observed unchanged once** (probable, not confirmed).

---

### H-008 — ALTA duplicates and ID counters

1. **Statement.** Duplicate account names are allowed; each `ALTA` consumes the next `AC-n` ID. Refuted by a non-201 on the second `ALTA;Lucia;82` or a non-sequential id.
2. **Current evidence.** *v1/v2:* IDs `AC-0001`,`AC-0002` (ids 4,5; EX-3,4); E202 rejection did not consume an id (ids 3→4). **Absent:** duplicates (current default: allowed, documented).
3. **Competing.** 8a allowed (AC-0002); 8b rejected with a new error code; 8c same id returned (idempotent).
4. **Probe `h008-alta`:** `POST /__reset` · `ALTA;Lucia;82` · `ALTA;Lucia;82` · `ALTA;Mateo;3`.
5. **Predictions.** 8a: 201 AC-0001, 201 AC-0002, 201 AC-0003. 8b: 201 AC-0001, 4xx new, 201 AC-0002. 8c: 201 AC-0001, 201 AC-0001, 201 AC-0002.
6. **Stop.** After step 3. Abort on rate-limit/401/403/5xx.
7. **Accounting.** 4 requests (1 reset). Cap 6.
8. **Impact.** 2–3 ALTA tests. Confirms/refutes a `[default]` in `commands.py`.
9. **Change bookkeeping.** Unknown version status; ≈3 % chance of the 3rd change.

## 4. Sentinel reserve (not a hypothesis; needs its own approval before 20:00)

≈19:20–19:40 Bogotá: replay `h001-anula` S(1)–S(11) (11) + `h002-a` (5) + 1 `CONSULTA` + 1 `ANULA` ≈ **18–20 requests**, compare to the stored v2 records, to detect a *second* service change (the original "may change again"). Keep **≥40 requests** unused for it and for retries. Daily budget is not binding (21/8000 by our tool; actual unknown); rate and approval are.

## 5. Which hypotheses could be the third FR-0153 change (all inference)

| Rank | Where | Why |
|---|---|---|
| 1 | **H-001** (cancelación / transiciones de estado) | D-C was never separated from D-B; ANULA on an *existing* op is the only core command semantic not observed in v2; E402 is not known to be new. |
| 2 | H-002 (límites) — *only if* it turns out that the limit **and** its state dependence both changed, or if c (unit change) merges D-A/D-B into one change, freeing the slot | D-B has several parallel explanations |
| 3 | H-007 / H-004 (parsing, precedence) | candidate categories named in `Prompt.md`; no evidence either way |
| — | H-005 (integridad) | 13/13 v2 accepted controls equal v1 ⇒ unlikely changed |

## 6. Recommended approval order

1. `INVESTIGATE H-001, budget=14` — 11 requests, all known controls, only plausible handle on the 3rd change, 6–12-step sequence shape.
2. `INVESTIGATE H-004, budget=16` — 13 requests, decides precedence everywhere and whether H-005/H-006 are viable.
3. `INVESTIGATE H-003, budget=17` — 14 single requests that replace guaranteed placeholder failures; requires waiver of the 401/403 abort rule for probes 2–5.
