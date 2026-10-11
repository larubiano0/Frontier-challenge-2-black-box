# Video script (2 min max)

## 1. Problem (10 s)
- A 10-year-old undocumented HTTP service. The goal is a replacement that matches it exactly, errors included.
- At 15:30 the provider shipped **v2** with 3 undisclosed changes (FR-0153).

## 2. Method (25 s)
- Every request to the original has a hypothesis and goes into `experimentos.jsonl` (7,928 entries).
- My own scripts only: `probe`, `replay_original` and `diffprobe`. About 7,930 of 8,000 daily requests used, with a rate limiter and no tokens logged.
- v1 and v2 evidence kept separate. A rule is `confirmado` only if it repeated.

## 3. Findings (35 s)
- 3 routes only. Everything else is E404, checked before auth. Auth is strict.
- Control = `98 − (N·100 mod 97)` over the alphanumerics, with PING exempt.
- Fixed error precedence: E404 → E001 → E599 → E101…E104 → E201 → E202 → E301 → E302 → command rules.
- v2 changes:
  1. `saldo` is now a string like `"400.00"`.
  2. The TRANSFER limit is now `> 50000`.
  3. The third one is not identified, and I say so in the spec (CAM-04).
- Hidden surprises:
  - The `HALT` and `NOTAS` commands were found through the E301 typo suggestion.
  - `NOTAS` contains a lure asking for the token, and I ignored it.
  - Fuzzing found that the limit does not apply when both accounts have the same owner name.

## 4. Verification (30 s)
- Golden suite: every recorded original request is replayed offline against the local app, which never calls the original.
- All golden sequences pass, with 583 tests passing and about 8 ms max latency.
- Fuzz of original vs local gave 0 differences after the fixes.
- Deployed on Railway as a single instance, because the state is in memory.

## 5. Risks (15 s)
- Don't inherit these: PING skipping the control, unbounded `intentos`, unconditional ANULA, and HALT reachable by any caller.
- Open gaps: the third v2 change, and any change after 20:00.

## Screen (while talking)
`README.md` code map → `pytest` / `run_golden` → curl `/health` on the deployed URL → one log line next to its spec row.
