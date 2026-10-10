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

## Not implemented
- All commands (PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA); `/msg` returns a
  placeholder 501 that does NOT reproduce the original.
- Control-field integrity, arity, error precedence, limits.
- Original behavior for bad/missing token, unknown routes/methods, malformed bodies,
  and the exact `/health` and `/__reset` bodies (placeholders marked `supuesto`).
- Golden regression suite / differential tooling.
