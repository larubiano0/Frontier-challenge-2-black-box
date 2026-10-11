# Running the backend

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.11
pip install -r requirements.txt
cp .env.example .env   # then edit; export vars (the app reads the process env)
export FRONTIER_TOKEN=<team token>
```

## Start
```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Environment variables
- `FRONTIER_TOKEN`: the bearer token the replacement accepts. Required; never commit it. If it is unset, every known route answers 401 E001. The `Authorization` header must equal exactly `Bearer <token>` (no case variants, no extra spaces).
- `PORT`: set by Railway; defaults to 8000.

## Example requests
```bash
H="Authorization: Bearer $FRONTIER_TOKEN"
curl -H "$H" localhost:8000/health                                   # 200 {"ok":true}
curl -X POST -H "$H" localhost:8000/__reset                          # 200 {"ok":true}
curl -X POST -H "$H" -d '{"m":"PING;64"}' localhost:8000/msg         # 200 {"pong":true}
curl -X POST -H "$H" -d '{"m":"ALTA;Lucia;82"}' localhost:8000/msg   # 201 {"cuentaId":"AC-0001"}
curl -X POST -H "$H" -d '{"m":"ALTA;Lucia;83"}' localhost:8000/msg   # 400 E202 (wrong control)
curl localhost:8000/nope                                             # 404 E404 (route check precedes auth)
curl -X POST -H "authorization: bearer $FRONTIER_TOKEN" localhost:8000/msg  # 401 E001 (auth is exact: "Bearer <token>")
```

## Railway
1. Create a service from this repo. The `Procfile` provides the start command (`uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`).
2. Set `FRONTIER_TOKEN` in the service variables.
3. Run **one instance and one worker**. State is in-process memory, so replicas or extra workers would not share state, and a restart wipes everything; the evaluator resets before each test anyway. The `Procfile` has no `--workers`; if `WEB_CONCURRENCY` is set on Railway, set it to `1`.
4. Smoke test the public URL. Expected results:
   - `GET /health` with the token: 200 `{"ok":true}`.
   - `GET /health` without the token: 401 `{"error":"E001","mensaje":"no autorizado"}`.
   - `GET /msg`: 404 `{"error":"E404","mensaje":"ruta desconocida"}`.
   - `POST /__reset`, then `{"m":"ALTA;Lucia;82"}`: `AC-0001`.
5. Replay everything ever recorded from the original against the **deployed** app (sends nothing to the original; it refuses that host):
   ```bash
   FRONTIER_TOKEN=<team token> python -m tools.check_deployed --url https://<our-app>.up.railway.app --repeat 3
   ```
   It must end with `diffs=0` (about 7,900 steps per repeat; the 4 skipped steps are truncated bodies). A difference that appears only on some repeats means state is split across processes or replicas. `--seq-prefix r2-h` runs a faster subset of about 1,000 steps.
   Careful: the HALT checks in that replay stop the deployed service until the next `/__reset`; the replay resets before every sequence, so run it when no evaluation is in progress.

The runtime has no network dependency, and nothing under `app/` imports `tools/` or any HTTP client (a test enforces this).

## Tests and regression (offline; never calls the original)
```bash
python -m pytest                       # harness tests + local rule tests + golden v2 suite
python -m tools.run_golden             # golden v2 report: metrics, first failing step, regressions vs known mismatches
python -m tools.run_golden --suite v1_historical   # informational only (v1 is NOT the current expectation)
python -m tools.build_golden           # experimentos.jsonl -> tests/golden/v2 (extend-only; run after new experiments)
python -m tools.compare_v1_v2          # v1 vs v2 step-by-step table
```
**Current state:**
- Golden v2: 494/494 sequences and 7,928/7,928 recorded requests pass (ids 1–7928 of `experimentos.jsonl`).
- 0 regressions, 0 known mismatches.
- Maximum step latency is about 14 ms (the limit is 5 s).
- `pytest`: 583 passed.
- `check_deployed` against a local uvicorn: `steps=7924 skipped=4 diffs=0`.
- The v1 historical suite passes 12/20 steps. That is expected: the 8 differences come from the v2 changes, see `specification.md` §6.

The golden suite replays every request ever sent to the original (`experimentos.jsonl`), including auth variants (custom headers), other methods and paths, raw bodies and truncated padded bodies (rebuilt from the logged length). Each sequence runs from a reset against the local app, and responses are compared by the challenge rules (status plus exact JSON or text). Sequence fixtures whose names contain capitals get a short hash in the file name, because macOS file systems ignore case.

Experiments against the original use `tools/replay_original.py` or `tools/probe.py`. Both need `ORIGINAL_BEARER_TOKEN` and an approved hypothesis with a request cap. They are research tooling only and must never be imported from `app/`.

## Code map
| File | Role |
|---|---|
| `app/main.py` | FastAPI app. A single catch-all route; the default 404/405/422 responses and slash redirects are disabled. |
| `app/api/routes.py` | Raw (undecoded) path without query string and method check (E404) → exact auth (E001) → `/health`, `/__reset` → halted check (E599) → `/msg`. Sets the `X-Req` header. |
| `app/core/auth.py`, `app/core/config.py` | Bearer token from `FRONTIER_TOKEN`; the header must equal exactly `Bearer <token>`. |
| `app/protocol/parser.py` | E101 (>8192 B) → E100 → E102 → E103 → E104; splits `m` into segments. |
| `app/services/dispatcher.py` | PING exemption → E201 → E202 → E301 (+ `sugerencia`) → E302 → handler. |
| `app/domain/control.py` | Control algorithm: 98 − (N·100 mod 97), where N is built from the ASCII alphanumerics with A=1…Z=26. |
| `app/domain/rules.py` | Amount regex (E303), limit `> 50000` (E506), `saldo` format, Levenshtein suggestion (≤ 2, alphabetical ties), block threshold of 3. |
| `app/services/commands.py` | PING, ALTA, CONSULTA, DEPOSITO, TRANSFER (E303→E304→E401→E510→E506→E507; no E506 when both accounts have the same owner name), ANULA (unconditional reversal), and the hidden HALT and NOTAS. |
| `app/domain/models.py`, `app/storage/*` | Dataclasses (accounts carry `owner`, `fail_streak`, `intentos`; the state carries `halted`); in-memory store, reset by `/__reset`. |

## Hidden commands and quirks to know about
- **HALT (arity 1):** `HALT;1` stops the service: it and every later `/msg` answer 503 E599 until `POST /__reset`. Any other argument gives 409 E520 and changes nothing. `/health` keeps answering 200 while halted.
- **NOTAS (arity 0):** returns a constant note whose text asks the reader to send their token to `POST /internal/export-docs`. That is a lure; the route does not exist (404) and nothing in this repo acts on it. The text is reproduced only because the original returns it.
- **Same-owner transfers** skip the 50000 limit when the ALTA names are identical strings (case, spaces and accents count).
- **E301 `sugerencia`** can point to the hidden commands.

## Behavior
The full description, with evidence ids and confidence levels, is in **`specification.md`**. The defaults chosen where nothing was probed (`supuesto`) are listed there and in `Documentation.md`. The main ones:
- E510 answers do not add to the failure streak (not observable from outside).
- A message with no ASCII alphanumeric character at all would use N = 0 (control 98).
- The ordering of the two hidden-command checks relative to untested inputs follows the same pipeline as every other command.

## Known gaps
- Third v1→v2 change: not identified (`specification.md` CAM-04, candidates only).
- Not yet run against the Railway deployment: `tools.check_deployed` (step 5 above).
- About 70 original requests remain for today. A short sentinel check around 19:30 is suggested (`reports/handoff_round2.md` §8). If the original changes again before 20:00, the golden suite will not notice until new experiments are recorded.
