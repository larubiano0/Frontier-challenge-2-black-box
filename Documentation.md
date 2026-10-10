# FRONTIER — Durable Research Memory

> **Living document.** Pi agents may update this file after meaningful progress and at every handoff. Do not edit `Prompt.md`, `Implement.md`, or `Plan.md`. Keep this document short and evidence-linked; raw request/response records belong in `experimentos.jsonl`.

_Last updated: 2026-10-10 ~15:30 Bogotá (16:30 EDT local clock). Deadline 20:00 Bogotá → ≈4.5 h remaining at time of writing._

## 1. Current status

- **Mode:** `PROPOSE` (read-only; no original-API calls). Bootstrap/orientation session completed.
- **Phase:** M0 (bootstrap) — repository inspected; nothing built yet.
- **Current approved hypothesis:** None.
- **Current experimental agent request cap:** Not assigned.
- **Original API calls recorded by this workflow:** 0. Verified: `experimentos.jsonl` does not exist; no script in the repo can call the original.
- **Remaining daily original-request budget per token:** Unknown (limit is 8,000/day and 10/s per token; the researcher's actual consumption so far is not known to this workflow). Number of tokens available to the team: unknown.
- **Tokens/credentials:** No `FRONTIER_TOKEN` or `ORIGINAL_BEARER_TOKEN` found in the agent's environment. No token files in the repo. (`.env` is git-ignored.) Treated as **not available**.
- **Replacement implementation:** None. No code, no `requirements.txt`, no tests, no Railway config (`Procfile`/`railway.json`/`Dockerfile`).
- **Deployment URL / status:** None. Railway CLI not found on the machine (`which railway` empty); deployment path not yet established.
- **Specification (`specification.md`):** Not created.
- **Last verified current-version observation:** None from this workflow.

### Repository inventory (inspected)

| Path | State |
| --- | --- |
| `README.md` | Organizers' contract (git-tracked). |
| `Prompt.md`, `Implement.md`, `Plan.md` | Immutable instructions (untracked in git, unmodified by me). |
| `Documentation.md` | This file (untracked). |
| `pruebas/ejemplos.jsonl` | 20 baseline examples, one ordered sequence (`seq: "ejemplos"`), morning version. |
| `.gitignore`, `.gitattributes` | Standard Python ignore; `.env`/`.venv` ignored. |
| _(absent)_ | App code, tests, `experimentos.jsonl`, `specification.md`, deploy config. |

Local toolchain: Python 3.14.7. `fastapi`, `pytest`, `httpx` are **not installed** (`import` fails); `uvicorn`/`requests` not checked individually (not shown by `pip3 list`). Python 3.14 compatibility with the FastAPI/pydantic stack must be checked when installing (use a venv; fall back to an older interpreter if wheels are missing).

## 2. Known inputs (not new experimental evidence)

- Organizers' `README.md`: challenge contract, endpoints, rules, deliverables, evaluation.
- `pruebas/ejemplos.jsonl`: 20 requests, one sequence after reset, morning version. **Not** an entry in `experimentos.jsonl`; cannot be cited as log evidence unless replayed and recorded by us. Cite it as `EX-n` (line `n`) in this file only.
- Evaluation (README): 100 hidden tests (40 single / 45 of 2–5 / 15 of 6–12 steps), each starts with `/__reset`; pass = every compared step has identical status and body (JSON compared key-order-insensitively with exact scalars/types; non-JSON compared character-for-character); 5 s per step; single process; replacement must never call the original (set value 0 otherwise).
- The spec is judged against the full list of service behaviors; each behavior needs a cited log `id`; **false claims subtract**.

### Example-derived observations (`EX-n`; descriptive only, unverified against the current service)

These are read straight off `pruebas/ejemplos.jsonl` (morning version). They are **leads for hypotheses**, not findings; none is `confirmado`, and none may enter the spec without log evidence.

| Ref | Observation in the examples |
| --- | --- |
| EX-1 | `PING;64` → 200 `{"pong":true}`. |
| EX-2,3 | `ALTA;Lucia;83` → 400 `E202 "control inválido"`; identical body with control `82` → 201 `{"cuentaId":"AC-0001"}`. So the control depends on message content. Failed ALTA did not consume an account ID. |
| EX-4 | `ALTA;Mateo;3` → 201 `AC-0002`. A control without zero padding (`3`) is accepted. |
| EX-17,18 | Control `5X` → 400 `E201 "control mal formado"`; same body with `35` → 200 (`E201` = non-numeric format, `E202` = numeric but wrong). |
| EX-5,11 | `CONSULTA;AC-0001;14` and `CONSULTa;AC-0001;14` both succeed with the same control → command token appears case-insensitive, and the control either ignores the command's case or doesn't cover it. |
| EX-5,8,19 | `CONSULTA` → 200 `{"cuenta_id":..., "saldo": <int>}` (key `cuenta_id`, whereas ALTA uses `cuentaId`). |
| EX-6,7,10,18 | `DEPOSITO`/`TRANSFER` success → 200 `{"status":"recieved","operacionId":"OP-000n"}` (note misspelling). Operation IDs increment only on success (failed EX-9/16 did not consume an ID). Balance reflected on the very next CONSULTA (EX-8). |
| EX-9,10 | `TRANSFER … 120000` → 422 `E506 "límite excedido"` although the source balance (210000) was sufficient; `100000` succeeds. A limit exists somewhere in (100000, 120000]; whether it is per-operation, cumulative, or per-day is unknown. DEPOSITO 250000 (EX-6) was accepted, so deposits are not under the same limit. |
| EX-13,14 | `ANULA;OP-0003` → 200 `{"ok":true,"anulada":"OP-0003"}`; repeat → 200 `{"ok":false,"motivo":"ya anulada"}` (business failure is HTTP 200). |
| EX-16,19 | After cancelling OP-0003 (a 100000 transfer), `TRANSFER AC-0002→AC-0001 50000` → 422 `E507 "saldo insuficiente"` and AC-0002's later balance is 40700 (=40000+700). Consistent with **ANULA reversing the transfer's balance effect**. Inferred only. |
| EX-15 | `CONSULTA;AC-0009` → 404 `E401 "cuenta inexistente"`. |
| EX-12 | `SALDOS;…` → 400 `E301` with message **`"comando desconocido "` (trailing space)**. Preserve byte-exact. |
| EX-20 | `ALTA;Lucia;Gomez;11` → 400 `E302 "aridad inválida"`. Unknown whether control (`11`) was valid → precedence arity vs. control is **undetermined** from the examples. |
| IDs | Accounts `AC-%04d`, operations `OP-%04d`, sequential from 1 after reset; separate counters. |

Control-field algorithm: **unknown**. Two naive offline candidates (byte-sum of the body before the last `;` mod 100, with and without the trailing `;`) do not reproduce the example controls. No further offline fitting was done (would amount to starting hypothesis work without approval). Whether controls on `PING`, `CONSULTA`, etc. are even validated, and whether the control has a fixed range, is unknown.

## 3. Hypothesis backlog and approvals

_No proposer output or approvals recorded yet._

Format when available: `ID | Hypothesis | Alternatives / counterexamples | Priority | Evidence IDs | Confidence | Researcher decision | Approved cap | Status`.

**Candidate areas for the first `PROPOSE` pass (not yet hypotheses; no approval implied):** (a) control-field algorithm and range; (b) error-precedence (control vs. arity vs. unknown command vs. missing account vs. limit vs. balance); (c) transport/protocol surface: auth failures, malformed JSON, missing/non-string `m`, wrong methods, unknown routes, body size; (d) the `E506` limit's semantics; (e) `ANULA` semantics across operation types (deposit, transfer, unknown/foreign OP, cancel-then-rebalance); (f) numeric/ID parsing (amounts: negative, zero, decimals, leading zeros, huge; IDs: case, padding); (g) reset semantics and counters; (h) what changed since the morning version.

## 4. Confirmed/probable findings

_No original-API evidence independently collected by this workflow yet._ (See Section 2 for example-derived leads only.)

For each finding record: `Rule ID | Precise claim | Original experiment IDs | Confidence (confirmado/probable/supuesto) | Last observed time/version | Counterexamples`.

## 5. Experiments and request accounting

- **Experiment log location:** `experimentos.jsonl` (to be created on the first authorized original request; **not present now**).
- **Token-by-token counts and limits:** None recorded. Count **all** original HTTP calls, including reset and health requests.
- **Active sequences / token locks:** None.
- **Infrastructure rate-limit events:** None.
- **Original calls used by this session:** 0.

Log batches here as: `time | hypothesis | agent | token alias | max calls | calls used | seq IDs | key results | handoff`.

## 6. Implementation, tests, and deployment

- **Code:** none. **Tests run:** none. **Deployed:** no.
- Local run/test commands: not yet defined (no venv, no dependencies installed).
- The 20-example fixture (`pruebas/ejemplos.jsonl`) is available to be replayed as ONE ordered sequence after reset once a baseline exists.

Track: files changed, runnable endpoints, comparison fixtures, exact passing/failing sequences, error categories, locally measured latency, deployed URL and live checks. Never report a test as passing unless it actually ran.

## 7. Decisions, deviations, and incident watch

- **Fixed architecture:** Python/FastAPI modular monolith; dataclasses + in-memory state behind a storage boundary; SQLite only if justified.
- **Research model:** proposer → researcher selects one hypothesis/budget → scoped experimental agent → evidence → differential tests → handoff.
- **Service change status:** Unknown. The examples are from the morning; no change independently verified.
- **Note for the researcher (2026-10-10):** The organizers' README says "No uses herramientas que hagan el trabajo por ti"; `Prompt.md` allows own scripts/fuzzers but forbids relying on an external black-box replication product. This workflow's agent-driven approach follows `Prompt.md`; the researcher should confirm it is acceptable under the official rules. Where they conflict, the README wins.

## 8. Open questions / blockers

- **Blocker for any probing:** no approved hypothesis, no request cap, and no token available in the environment (how/where will the researcher supply `ORIGINAL_BEARER_TOKEN` safely?).
- Control/integrity algorithm (range, which fields it covers, case sensitivity, applicability per command).
- Validation and error-precedence rules (control vs. arity vs. command vs. account vs. limit vs. balance).
- Semantics of `E506` limit; full list of error codes (so far seen: E201, E202, E301, E302, E401, E506, E507).
- `ANULA` scope (which operations, reversal rules, unknown IDs, authorization).
- Transport behavior: auth failure body/status, malformed JSON, wrong methods, unknown routes, `/health` body, `/__reset` body.
- What changed since the morning version, and when.
- How many tokens does the team have, and how much daily budget has been consumed?
- Railway access: project/account ready? Which Python version does Railway build use?

## 9. Next bounded action / handoff

**Current mode:** `PROPOSE` (no original calls).

**Recommended next single action (needs researcher go-ahead on scope only; no API use):** `BUILD` the M0/M1 skeleton locally — venv + dependencies, FastAPI app with `/health`, `/__reset`, `/msg`, in-memory store behind an interface, command-dispatch skeleton, and a pytest fixture replaying the 20 examples as one ordered sequence (expected to partly fail until rules are evidenced; failing steps will be marked as such). No original calls. Then run a full `PROPOSE` pass producing `H-001…` with request-cost estimates, and wait for the researcher to pick **one** hypothesis plus a numeric cap.

**Inputs needed from the researcher before any `INVESTIGATE`:** chosen hypothesis, numeric request cap `N`, a token supplied via environment variable (`ORIGINAL_BEARER_TOKEN`), and today's consumed-request count per token.

**Before handing off:** update status, newly obtained facts with evidence IDs, failures and uncertainty, remaining token budgets, and one recommended next action.
