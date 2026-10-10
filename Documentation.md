# FRONTIER — Durable Research Memory

> **Living document.** Pi agents may update this file after meaningful progress and at every handoff. Do not edit `Prompt.md`, `Implement.md`, or `Plan.md`. Keep this document short and evidence-linked; raw request/response records belong in `experimentos.jsonl`.

_Last updated: 2026-10-10 ≈17:05 Bogotá (18:05 EDT local clock). Deadline 20:00 Bogotá → ≈2 h 55 min remaining._

## 0. Session 3 update — BUILD from `reports/handoff_implementation.md` (supersedes §1, §6, §7 and the E202 parts of §8/§9)

- **Mode:** `BUILD`. **0 requests to the original** in this session (log stays at 2,880 lines; counter unchanged).
- **Implemented in `app/`** (every rule cites log ids in code): catch-all routing (unknown route/method → 404 E404, checked before auth; no FastAPI 404/405/422 or slash redirects) · 401 E001 · `/health` → `{"ok":true}` · body >8192 B → 413 E101 · E100/E102/E103/E104 · PING exempt from control checks (arity still applies) · E201 `^[0-9]{1,2}$` · **E202** · E301 + `sugerencia` (Levenshtein ≤2) · E302 · E303 amount `^[1-9][0-9]{0,9}$` (cents) · E304 · E401/E402 · E506 `amount > 50000` before E507 · **E510** blocking (3 consecutive E506/E507 as source; `intentos` counter; cleared by successful TRANSFER from / DEPOSITO into the account, and by reset) · ANULA unconditional reversal (negative balances) · `saldo` `"X.YY"` incl. negatives. All `Unevidenced`/501 placeholders removed.
- **E202 solved offline** (`app/domain/control.py`): keep ASCII alphanumerics of the message without its last `;control` segment, upper-case, letters → A=1…Z=26, digits as-is, concatenate to integer N; control = `98 − (N·100 mod 97)` (ISO 7064 MOD 97-10 style), compared as an exact string (`03` ≠ `3`). Fits all 66 distinct normalized pairs of `reports/control_rows.json` and every E202/non-E202 outcome in the 2,880-step golden suite. Confidence: **probable** (offline fit, not separately probed with new predictions); non-ASCII letters ignored and empty-N → 98 are `supuesto`.
- **Golden suite:** `tools/build_golden.py` now builds all 43 sequences (2,880/2,880 log entries); `h003-entrada` and `h003-limits2` (no leading reset) admitted via an explicit, justified `STATELESS_SEQUENCES` allow-list. `tools/golden_lib.py` replays method/path/auth/raw-body records. v2-s1 fixture unchanged.
- **Metrics (run 2026-10-10, session 3):** sequences 43/43 pass · requests 2,880/2,880 (Request Agreement 100 %, `/msg` 2,823/2,823) · Sequence Agreement 100 % · 0 regressions · 0 known mismatches · max step latency ≈8 ms. `python -m pytest`: **132 passed**. v1 historical suite (informational): 12/20 — the 8 differences are the saldo format and the 50000 limit (+ its cascade). Real uvicorn smoke test OK.
- **Tests rewritten:** `tests/test_rules_local.py` (encoded disproven assumptions: 501 placeholders, limit ≥100000, no E202) → new local tests for the v2 rules; `tests/test_golden_lib.py` fixture-start check honours the stateless allow-list.
- **`supuesto` defaults in code:** successful ANULA does not touch the block state; E510 answers do not add to the streak; `intentos` uncapped; E301 tie → first of PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA; HEAD/other methods → E404; E101 checked after auth; JSON `NaN`/`Infinity` → E100; `X-Req` header = per-process count of authorized `/msg` calls, not reset by `/__reset` (headers unscored).
- **Still open:** specification document (`specification.md`) not written; not deployed; `RUN_BACKEND.md` is stale (lists E202 as missing and 501 placeholders); the three FR-0153 changes still need to be stated with v1-vs-v2 evidence (candidates: saldo string, limit 100000 accepted in v1 vs `>50000` rejected in v2, third unidentified).
- **Next single action:** write `specification.md` from `reports/handoff_implementation.md` §6–7 + the E202 model, then deploy to Railway.

## 1. Current status

- **Mode at handoff:** `HANDOFF`. Session 1 ran `BUILD` tooling + `INVESTIGATE H-000`. Session 2 ran `BUILD` only (implemented the researcher-approved rules S-1…S-3 + minimal scaffolding); **0 requests were sent to the original in session 2**.
- **Phase:** M0 ✔ · M1b ✔ · M1 ✔ (runnable local replacement) · M3b **partial**: S-1…S-3 implemented as `supuesto` plus v1-derived scaffolding; control value check (E202) **not implemented** (algorithm unknown). Not deployed.
- **Approved hypothesis:** H-000 only — *executed and closed*. **No other hypothesis is approved.** Nothing further may be sent to the original without a new approval.
- **Token handling:** `ORIGINAL_BEARER_TOKEN` was read only via `os.environ`. **Confirmation: no token was printed, logged or stored.** Verified by scanning every file in the repo (excluding `.venv`/`.git`) for the token value → 0 hits (including `experimentos.jsonl`, `experimentos_trace.jsonl`, the counter file, fixtures, reports and this file). `FRONTIER_TOKEN` was not used against the original. The runner/pytest use a dummy local token.
- **Deployment:** none yet. **Specification (`specification.md`):** not created.

## 2. Request budget (H-000) — unchanged in session 2

| Item | Value |
| --- | --- |
| Approved cap (resets included) | **25** (1 reset + 20 `/msg` + ≤4 reserve) |
| **Used** | **21** = 1 `POST /__reset` + 20 `POST /msg` |
| **Remaining of the H-000 cap** | **4 (unused reserve; not to be spent — H-000 is closed, any further call needs a new approval)** |
| Experiment IDs | **1–21**, `seq` = `v2-s1` |
| Rate used | ≈4 req/s (limit 10/s); latency 16–72 ms per request |
| Infra rate-limit events / 401 / 403 / connectivity errors | 0 / 0 / 0 / 0 |
| Per-token counter (tool-observed, `tools/original_request_counter.json`, key = env-var name) | day_count = 21, lifetime = 21 of 8,000/day |
| True daily consumption of the researcher's token | **Unknown** (earlier use outside this tool is not measurable here) |

ID ↔ example mapping: `id 1` = `POST /__reset`; `id k` (k = 2…21) = example `n = k−1` of `pruebas/ejemplos.jsonl`, same order, one sequence after the reset.

## 3. Evidence classification

| Class | Content |
| --- | --- |
| **Historical v1** | `pruebas/ejemplos.jsonl` (EX-1…EX-20; morning version; organizer-supplied; **not** in `experimentos.jsonl`). Kept in `tests/golden/v1_historical/ejemplos.json`; never enforced as current. |
| **Observed v2** | `experimentos.jsonl` ids **1–21** (single observation each, `seq v2-s1`). In `tests/golden/v2/v2-s1.json`. Supplementary provenance (raw body, headers of interest, version=2, eligibility): `experimentos_trace.jsonl`. |
| **Confirmed unchanged** | **None.** 12 of the 20 steps gave a v2 response equal to v1, but each was seen once in one sequence → "observed v2 = v1", not yet `confirmado`. |
| **Confirmed changed** | **None.** Only *candidates* (§4). |
| **Unknown version status** | Everything not exercised: control algorithm and range, control on PING/CONSULTA, arity/precedence, amount parsing, the `E506` threshold semantics, ANULA on an existing operation in v2, auth failures, routes/methods, malformed bodies, `/health` body, … |

### v2-only observations (single observations; no v1 counterpart)
- `POST /__reset` → 200 `{"ok":true}` (id 1), `Content-Type: application/json; charset=utf-8`, **no `X-Req` header** (→ `x_req: null`, flagged in the log).
- `X-Req` on `/msg` responses: 1, 2, …, 20 (ids 2–21), i.e. +1 per `/msg` since the reset (descriptive only).
- New error seen in v2: `404 {"error":"E402","mensaje":"operación inexistente"}` (ids 14, 15). v1 examples never exercised this code.

## 4. v1 vs v2, step by step (candidate differences — descriptive only)

Generated by `python -m tools.compare_v1_v2` (also saved in `reports/v1_vs_v2.md`). 20 steps: **12 equal, 8 different**. Rows marked *candidata* are **not** declared changes: a difference may be a consequence of another one and the evidence is insufficient (one sequence, no counter-probes).

| n | request | respuesta v1 (histórica) | respuesta v2 (observada, id) | ¿igual? |
|---|---|---|---|---|
| 1 | `PING;64` | 200 `{"pong":true}` | 200 `{"pong":true}` (2) | sí |
| 2 | `ALTA;Lucia;83` | 400 `{"error":"E202","mensaje":"control inválido"}` | idéntica (3) | sí |
| 3 | `ALTA;Lucia;82` | 201 `{"cuentaId":"AC-0001"}` | idéntica (4) | sí |
| 4 | `ALTA;Mateo;3` | 201 `{"cuentaId":"AC-0002"}` | idéntica (5) | sí |
| 5 | `CONSULTA;AC-0001;14` | 200 `{"cuenta_id":"AC-0001","saldo":0}` | 200 `{"cuenta_id":"AC-0001","saldo":"0.00"}` (6) | **NO · candidata** (`saldo` int → str) |
| 6 | `DEPOSITO;AC-0001;250000;86` | 200 `{"status":"recieved","operacionId":"OP-0001"}` | idéntica (7) | sí |
| 7 | `TRANSFER;AC-0001;AC-0002;40000;86` | 200 `{"status":"recieved","operacionId":"OP-0002"}` | idéntica (8) | sí |
| 8 | `CONSULTA;AC-0002;11` | 200 `…"saldo":40000}` | 200 `…"saldo":"400.00"}` (9) | **NO · candidata** (`saldo` int → str) |
| 9 | `TRANSFER;AC-0001;AC-0002;120000;55` | 422 `{"error":"E506","mensaje":"límite excedido"}` | idéntica (10) | sí |
| 10 | `TRANSFER;AC-0001;AC-0002;100000;12` | 200 `{"status":"recieved","operacionId":"OP-0003"}` | **422 `{"error":"E506","mensaje":"límite excedido"}`** (11) | **NO · candidata** (status 200→422, cuerpo distinto) |
| 11 | `CONSULTa;AC-0001;14` | 200 `…"saldo":110000}` | 200 `…"saldo":"2100.00"}` (12) | **NO · candidata** (tipo de `saldo`; además el valor numérico es otro) |
| 12 | `SALDOS;AC-0001;38` | 400 `{"error":"E301","mensaje":"comando desconocido "}` | idéntica (13) | sí |
| 13 | `ANULA;OP-0003;66` | 200 `{"ok":true,"anulada":"OP-0003"}` | **404 `{"error":"E402","mensaje":"operación inexistente"}`** (14) | **NO · candidata** |
| 14 | `ANULA;OP-0003;66` | 200 `{"ok":false,"motivo":"ya anulada"}` | **404 `{"error":"E402","mensaje":"operación inexistente"}`** (15) | **NO · candidata** |
| 15 | `CONSULTA;AC-0009;87` | 404 `{"error":"E401","mensaje":"cuenta inexistente"}` | idéntica (16) | sí |
| 16 | `TRANSFER;AC-0002;AC-0001;50000;23` | 422 `{"error":"E507","mensaje":"saldo insuficiente"}` | idéntica (17) | sí |
| 17 | `DEPOSITO;AC-0002;700;5X` | 400 `{"error":"E201","mensaje":"control mal formado"}` | idéntica (18) | sí |
| 18 | `DEPOSITO;AC-0002;700;35` | 200 `{"status":"recieved","operacionId":"OP-0004"}` | 200 `…"operacionId":"OP-0003"}` (19) | **NO · candidata** (OP-0004 → OP-0003) |
| 19 | `CONSULTA;AC-0002;11` | 200 `…"saldo":40700}` | 200 `…"saldo":"407.00"}` (20) | **NO · candidata** (`saldo` int → str) |
| 20 | `ALTA;Lucia;Gomez;11` | 400 `{"error":"E302","mensaje":"aridad inválida"}` | idéntica (21) | sí |

### Candidate differences (grouped for discussion; NOT confirmed, NOT counted as "the 3 changes")
- **D-A — forma de `saldo` en CONSULTA** (n = 5, 8, 11, 19; ids 6, 9, 12, 20): int → string con 2 decimales. Los 4 valores son numéricamente coherentes con *entero v1 ÷ 100* (0→`"0.00"`, 40000→`"400.00"`, 40700→`"407.00"`; el 2100.00 de n=11 corresponde a 210000 = 250000−40000, ver D-B). Desconocido: negativos, valores grandes, si cambió la unidad de los montos de entrada (DEPOSITO/TRANSFER) o solo la salida.
- **D-B — TRANSFER de 100000** (n = 10; id 11): v1 aceptaba (OP-0003); v2 responde 422 `E506`. En v2 también se rechaza 120000 (id 10), como en v1. Explicaciones alternativas **sin probar**: umbral por operación más bajo; límite inclusivo (`>=`) en vez de exclusivo; límite acumulado/por cuenta (ya había 40000 transferidos); cambio de unidad entre montos y límite (ver D-A); precedencia distinta. Cualquiera sirve para el hecho observado.
- **D-C — posibles consecuencias de D-B** (no verificado; sin contraejemplo): n = 11 (saldo AC-0001 = `2100.00` ≙ 210000, es decir, como si OP-0003 no se hubiera ejecutado), n = 13/14 (`ANULA;OP-0003` → 404 `E402`: en v2 **OP-0003 no existía** porque n=10 fue rechazada), n = 18 (OP-0004 → OP-0003: una operación rechazada no consume ID; v1 ya lo mostraba en EX-9/16). **No se puede separar** "ANULA cambió" de "ANULA se comporta igual y solo faltó la operación": ANULA sobre una operación existente nunca se observó en v2.
- **Tercer cambio:** no identificado. Puede estar dentro de lo ya visto (p. ej. D-A y D-B pueden ser dos cambios y D-C consecuencia) o en comportamiento **no ejercitado** por esta secuencia. No se infiere.

## 5. Hypothesis log

| ID | Hypothesis | Evidence IDs | Result | Status |
| --- | --- | --- | --- | --- |
| H-000 | Reproducir los 20 requests de `ejemplos.jsonl` como una secuencia tras reset contra el original v2 → línea base v2 y diferencias con v1 | 1–21 | Línea base obtenida; 12/20 pasos iguales a v1, 8 distintos (candidatas D-A…D-C) | **Cerrada** |
| H-001 | ANULA sobre operación existente en v2 (reversión, repetición) — candidata a 3.er cambio | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap sugerido 14 |
| H-002 | Forma del límite E506 (por operación vs acumulado; orden vs E507) | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 24 |
| H-003 | Entrada: auth, rutas/métodos, cuerpos no JSON / sin `m` / sin `;`, `/health` | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 17 (requiere exención de la regla de abortar en 401/403) |
| H-004 | Precedencia de validación (control formato/valor, comando, aridad, cuenta, límite, saldo) y si PING valida control | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 16 |
| H-005 | Algoritmo de control (E202), experimento diseñado de una variable | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 420; descartar si quedan <90 min |
| H-006 | Parseo de montos (0, negativo, decimal, ceros, enorme) y TRANSFER a la misma cuenta | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 14; depende de H-004 |
| H-007 | Gramática de comandos (mayúsculas, espacios, campos vacíos, args extra) | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 13 |
| H-008 | ALTA duplicados y contadores de ID | — | — | **propuesta** ([reports/hypotheses.md](reports/hypotheses.md)), cap 6 |

H-001…H-008 are only *proposed* (PROPOSE pass 2026-10-10 ≈17:35 Bogotá; **0 original requests consumed by that pass**). None is approved. No `confirmado` claim exists.

## 6. Implementation, tools and regression metrics

### Tooling (session 1, outside `app/`; unchanged)
`tools/replay_original.py` (experiments only; dry-run by default; counter, ≤10 req/s using ~4, 5 s timeout, stops on infra rate-limit/401/403/429/connectivity/non-2xx reset) · `tools/build_golden.py` (log → `tests/golden/v2/`, examples → `tests/golden/v1_historical/`, extend-only) · `tools/golden_lib.py` + `tools/run_golden.py` (README comparison rules, in-process local app, network blocked, regression-vs-known classification via `tests/golden/baseline_v2.json`, now also reports steps that went FAIL→PASS) · `tools/compare_v1_v2.py` (§4 table). Log/trace/counter files: `experimentos.jsonl`, `experimentos_trace.jsonl`, `tools/original_request_counter.json`. Commands (repo root, `.venv`): `python -m tools.build_golden` · `python -m tools.run_golden [--suite v1_historical] [--update-baseline]` · `python -m pytest` · `python -m tools.compare_v1_v2`.

### Backend implemented in session 2 (`app/`)
| File | Role |
| --- | --- |
| `app/protocol/parser.py` | `{"m": "..."}` → command / args / control (last `;` field is the control). Invalid JSON, missing/non-string `m`, or no `;` → `Unevidenced`. |
| `app/domain/errors.py` | `ServiceError` + byte-exact E201, E301 (**trailing space**), E302, E401, E402, E506, E507 (each cites its evidence id); `Unevidenced`. |
| `app/domain/rules.py` | **The three v2 rules** (S-1 `format_saldo`, S-2 `TRANSFER_LIMIT`/`transfer_exceeds_limit`; S-3 documented, enforced in `commands.anula`). |
| `app/services/commands.py` | PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA handlers; every line tagged `[v2]`, `[S-n]`, `[v1]`, `[default]` or `[?]`. |
| `app/services/dispatcher.py` | Precedence: shape → control format (E201) → *(control value E202: missing)* → command (E301, case-insensitive) → arity (E302) → handler. |
| `app/api/routes.py`, `app/core/auth.py`, `app/storage/*` | Unchanged (auth body, `/health` and `/__reset` bodies remain placeholders; `/__reset` `{"ok":true}` happens to equal observed id 1). |

**The 3 approved rules (all `supuesto`; none is a confirmed change):**
| Rule | Implemented behavior | Evidence | Where |
| --- | --- | --- | --- |
| S-1 | `CONSULTA` → `saldo` = string `balance/100` with 2 decimals (integer arithmetic; balances stay ints) | v2 ids 6, 9, 12, 20 | `rules.format_saldo`, `commands.consulta` |
| S-2 | `TRANSFER` amount ≥ 100000 → 422 `E506 "límite excedido"` (checked after accounts exist, before balance); `DEPOSITO` unlimited | v2 ids 10, 11 (and 7 for DEPOSITO) | `rules.transfer_exceeds_limit`, `commands.transfer` |
| S-3 | `ANULA` of a non-existent operation → 404 `E402 "operación inexistente"` | v2 ids 14, 15 | `commands.anula` |

**Scaffolding needed to reach the rules (all `supuesto`, from v1 or defaults):** ID formats `AC-%04d`/`OP-%04d` (counters consumed only on success; v2 ids 4, 5, 19); `recieved` body; ANULA of an existing op → `{"ok":true,"anulada":…}` + balance reversal, repeat → `{"ok":false,"motivo":"ya anulada"}` (**v1 only**, never observed in v2); command case-insensitivity (v2 id 12); control must be digits-only else E201 (v2 id 18). **Pure defaults:** order of checks (src, dst, amount, limit, balance), E401 for DEPOSITO/TRANSFER accounts, duplicate names allowed, exact-match account IDs. **No evidence and no default → explicit `501 {"error":"not_implemented"}` (this is NOT the original's behavior):** non-JSON/odd body, message without `;`, amounts that are not plain positive integers, empty ALTA name, TRANSFER to the same account, ANULA that cannot be reversed because the funds are gone.

### Regression metrics — suite v2 vs. current backend — run 2026-10-10 18:04 EDT (session 2)
| Metric | Session 1 (skeleton) | **Now** |
| --- | --- | --- |
| Golden sequences | 1 | **1** (0 passing, 1 failing) |
| Recorded requests | 21 | **21** (1 reset + 20 `/msg`) |
| Request Agreement Rate | 4.8 % (1/21) · `/msg` 0/20 | **85.7 % (18/21)** · `/msg` **85.0 % (17/20)** |
| Sequence Agreement Rate | 0 % | **0 % (0/1)** |
| Steps FAIL→PASS vs. baseline | — | 17 (steps 1, 5–20) |
| Newly introduced regressions | 0 | **0** |
| Known mismatches | 20 | **3** (steps 2, 3, 4) |
| First failing step | step 1 `PING` (501) | **step 2** `ALTA;Lucia;83` (src id 3): expected `400 {"error":"E202","mensaje":"control inválido"}`, actual `201 {"cuentaId":"AC-0001"}` |
| Max step latency | ≈3 ms | <1 ms (limit 5 s) |
| pytest | 41 ok / 1 fail | **62 passed, 1 failed** (`test_v2_sequence[v2-s1]`, expected) |

**Why the sequence still fails:** only because of the missing E202. Step 2 wrongly creates `AC-0001`, so steps 3 and 4 return `AC-0002`/`AC-0003` instead of `AC-0001`/`AC-0002` (cascade, verified by inspecting the actual bodies). Everything else in v2-s1 — including every S-1/S-2/S-3 step (ids 6, 9, 11, 12, 14, 15, 20) — matches. Expectations and fixtures were **not** modified; only `baseline_v2.json` (PASS/FAIL state used for classification) was refreshed, and only because there were no regressions.
Historical v1 suite (informational, **not** an expectation): 9/20 requests, 0/1 sequence; its 11 failures are the 8 candidate rows of §4 plus the 3 E202-cascade steps — i.e. the backend currently behaves like v2 where v2 was observed and like v1 elsewhere, as designed.
Other local tests: `tests/test_rules_local.py` (21 locally generated tests of S-1…S-3 and the scaffolding; **not confirmed by the original**, labeled as such; includes a test documenting the E202 gap and one for the 501 placeholders). Real-server smoke test (uvicorn on localhost, dummy token): responses identical to the TestClient run.

## 7. Control value (E202) — offline analysis, no original requests

Attempted to fit the control algorithm from the 19 usable examples (v1) using the v2 sequence as the same data. Searched: sums/weighted sums/polynomial hashes/XOR/CRC32/Adler over {raw, upper-cased, with/without `;`} for moduli 2…1000, then, for mod 97, linear position-weighted sums (from start and from end) with arbitrary scale and offset. **No model reproduced all rows.** Weak, unverified leads only:
- The three `CONSULTA;AC-000d;c` points (d=1,2,9 → c=14, 11, 87) are consistent with arithmetic **mod 97** and a coefficient of −3 per unit of the last character (and `CONSULTa` = `CONSULTA` suggests case normalization or exclusion of the command). Only 3 points; could be coincidence.
- `TRANSFER;AC-0001;AC-0002;120000;55` vs `…100000;12` also yields −3 per unit if the amount enters numerically, but the `DEPOSITO` pair breaks that simple model.
- All observed controls are < 97 (max 87). `PING;64` and the E301/E302 rows may not be validated at all (unknown).
**Conclusion: the algorithm is unknown.** Not implemented, no lookup table of known values was added (it would fake passing steps). Needs a dedicated hypothesis (`PROPOSE`) with controlled probes.

## 8. Open questions / blockers (anotadas, NO probadas)

- **Blocker for any further original probing:** no approved hypothesis/budget.
- **Control/E202 algorithm** (§7) — the only reason v2-s1 does not pass; likely affects many hidden tests with invalid controls. Whether v2 changed it: unknown.
- D-B: what exactly makes 100000 fail in v2 (threshold, inclusivity, cumulative, unit)? Does 99999 or a smaller amount pass? (S-2 uses ≥100000 as a default only.)
- D-A: negatives/large/zero balances; whether input amounts are now cents.
- ANULA on an existing operation in v2: still `{"ok":true,"anulada":…}` with reversal? repeat → "ya anulada"? (v2-s1 never created OP-0003.) Is `E402` new in v2? This is the main place where the third change could be hiding.
- Real validation precedence (control format vs. command vs. arity vs. account vs. limit vs. balance) — all current order is a default. Does PING validate its control?
- Behavior for malformed bodies, missing `m`, unknown routes/methods, auth failures, `/health` and `/__reset` bodies — still placeholders.
- DEPOSITO/TRANSFER on unknown accounts (E401 assumed), amount parsing (0, negatives, decimals, leading zeros), duplicate names, same-account transfer.
- The third change is unidentified.
- README ambiguity: whether the evaluator compares the `/__reset` response; our reports show `/msg`-only rates separately.
- Team token count; Railway access/Python version (carried over).
- Note for the researcher: README says "No uses herramientas que hagan el trabajo por ti"; this work uses only self-written scripts; confirm acceptable (README wins in a conflict).
- `RUN_BACKEND.md` (not editable by agents) is now stale: it still says `/msg` returns 501 and that the golden suite does not exist.

### Clarification — "header ausente" (X-Req on `/__reset`)
Not a problem with the service or with the code. The log format requires `x_req`, the value of the **`X-Req` response header**. In experiment **id 1** (`POST /__reset`) the original's response simply had **no `X-Req` header** (all 20 `/msg` responses did: 1…20). Per the rules I wrote `x_req: null` and flagged it in that line's `conclusion`. Headers are **not scored** by the evaluator, so the replacement does not need to emit `X-Req`; it is only a quirk to know about (and a hint that `X-Req` counts `/msg` calls since the last reset).

## 9. Next bounded action / handoff

**Current mode:** `HANDOFF`. Original requests used in total: 21 (H-000 only). Local state: backend with S-1…S-3 implemented (`supuesto`), golden v2 at 18/21 requests, 0 regressions, 3 known mismatches (all E202).

**Recommended next single action:** run a `PROPOSE` pass (no original calls) to produce `H-001…` and ask the researcher to approve **one** with a request cap. Priority candidates: (a) the **control algorithm / E202** (largest impact on hidden tests, and what blocks `v2-s1` from passing), designed from the §7 leads; (b) `ANULA` on an *existing* operation in v2 and the `E506` threshold, to confirm or refute S-2/S-3 and look for the third change.

**Inputs needed from the researcher:** which hypothesis to investigate and its cap; today's true consumed-request count for the token (if known); whether the `501 not_implemented` placeholder is acceptable meanwhile or a different default is preferred for unevidenced inputs.

**Before the next handoff:** re-inspect ids 1–21 and the §4 table independently; run `python -m tools.run_golden` and `python -m pytest` after every backend change; never edit fixtures to make tests pass.

### Update — PROPOSE pass (≈17:35 Bogotá)
A `PROPOSE` pass ran: shortlist H-001…H-008 in [reports/hypotheses.md](reports/hypotheses.md) (also offline scripts in `tools/analysis/`, no network). **0 original requests consumed by this pass** (counter still 21). **Awaiting researcher approval of exactly ONE:** recommended `INVESTIGATE H-001, budget=14`, then `H-004, budget=16`, then `H-003, budget=17` (needs a waiver of the 401/403 abort rule). Keep ≥40 requests reserved for a 19:20–19:40 sentinel re-check. Qualification recorded there: "E402 new in v2" is not established (v1 never tried ANULA on a missing op).
