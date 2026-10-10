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
- `FRONTIER_TOKEN` – bearer token the replacement accepts (required; never commit).
- `PORT` – set by Railway; default 8000.

## Example requests
```bash
H="Authorization: Bearer $FRONTIER_TOKEN"
curl -H "$H" localhost:8000/health
curl -X POST -H "$H" localhost:8000/__reset
curl -X POST -H "$H" -H 'Content-Type: application/json' -d '{"m":"PING;64"}' localhost:8000/msg
```

## Railway
Set `FRONTIER_TOKEN` in service variables. `Procfile` provides the start command
(`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). State is in-process only.

## Tests and regression (offline; never calls the original)
```bash
python -m pytest                       # harness tests + local rule tests + golden v2 suite
python -m tools.run_golden             # golden v2 report: metrics, first failing step, regressions vs known mismatches
python -m tools.run_golden --suite v1_historical   # informational only (v1 is NOT the current expectation)
python -m tools.build_golden           # experimentos.jsonl -> tests/golden/v2 (extend-only)
python -m tools.compare_v1_v2          # v1 vs v2 step-by-step table
```
Current state: golden v2 = 18/21 requests, 0/1 sequences, 0 regressions, 3 known mismatches (all caused by the missing E202). `tests/test_golden_v2.py` is expected to stay red until E202 is implemented; do not edit fixtures to fix it.

Experiments against the original use `tools/replay_original.py` (needs `ORIGINAL_BEARER_TOKEN`, dry-run by default, requires an approved hypothesis and a request cap). It is research tooling only and must never be imported from `app/`.

## Implemented (all `supuesto` unless the golden suite says otherwise)
- `POST /msg` with PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA, in-memory state, `/__reset`, `/health`.
- v2 rules (see `app/domain/rules.py`): CONSULTA `saldo` as `"X.YY"` string (balance/100); TRANSFER amount >= 100000 -> 422 E506; ANULA of a non-existent operation -> 404 E402.
- Errors E201, E301 (trailing space), E302, E401, E402, E506, E507 with observed bodies.
- Validation order (control format -> command -> arity -> handler) is a default, not evidence.

## Not implemented / unknown
- **Control VALUE check (E202):** the algorithm is unknown, so any digits-only control is accepted. This is the only reason golden v2-s1 fails.
- Inputs with no evidence return an explicit placeholder `501 {"error":"not_implemented"}` (NOT the original's behavior): non-JSON body, missing `m`, message without `;`, amounts that are not plain positive integers, empty ALTA name, TRANSFER to the same account, ANULA whose funds were already spent.
- Original behavior for bad/missing token, unknown routes/methods, and the exact `/health` and `/__reset` bodies (placeholders marked `supuesto`).
- ANULA on an existing operation and the exact E506 threshold are unverified in v2.
- Not deployed to Railway yet.
