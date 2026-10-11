# Video script (about 5 min)

## 1. The problem (30 s)
- A 10-year-old HTTP service with no documentation. We had to build a replacement that matches it exactly, errors included.
- Graded on 100 hidden tests, on the spec, and on the experiment log.
- Midday twist: the provider shipped **v2**, with 3 undisclosed changes (ticket FR-0153).

## 2. Method (60 s)
- Hypothesis-driven. Every request to the original has a stated hypothesis, and the result goes into `experimentos.jsonl`.
- I wrote my own tooling (`tools/probe.py`, `replay_original.py`, `diffprobe.py`). No black-box replication products.
- Safety: a request counter and rate limiter (10 req/s, 8,000/day), tokens never logged, and approval before each batch.
- Rules for evidence: v1 observations stayed separate from v2, and a rule was only `confirmado` if it was repeated.

## 3. What I found (90 s)
- Only 3 routes. Anything else gives E404, and route check comes before auth.
- Integrity: the control is `98 − (N·100 mod 97)` (MOD 97-10), computed over the alphanumerics with A=1…Z=26. PING is exempt.
- Error precedence: E101 → E100 → E102 → E103 → E104 → E201 → E202 → E301 → E302 → handler errors.
- Commands: PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA.
- State: sequential account IDs, a failure streak that blocks an account after 3 failures (E510), and `X-Req`, which is not reset by `/__reset`.
- Show one or two real examples (the ALTA with a wrong control, and the E510 block).

## 4. The v2 incident (60 s)
- Change 1: `saldo` format.
- Change 2: transfer limit (`> 50000` → E506).
- Change 3: not identified with certainty. Say so honestly (spec CAM-04). Stating the gap is better than a false claim.
- How I detected them: I replayed the 20 v1 examples on v2 and diffed them (`tools/compare_v1_v2.py`, `reports/v1_vs_v2.md`).

## 5. Building and verifying the replacement (60 s)
- FastAPI, in-memory state, a single catch-all route, and no dependency on the original (a test enforces it).
- Golden regression suite: every recorded original request is replayed offline against the local app. Status: 43/43 sequences, 2,880/2,880 requests, and the latest fuzz rounds added more.
- Differential fuzzing (`diffprobe`) found the same-owner exemption bug. I turned it into a hypothesis, probed it and fixed it.
- Deployed on Railway with a single instance, because state lives in memory.

## 6. Risks and lessons (30 s)
- Legacy quirks a new client should not inherit: the PING exemption from the control, the unbounded `intentos`, ANULA reversing unconditionally.
- Open gaps: the third v2 change, and any change after 20:00.
- Lesson: the log and the regression suite made it safe to change the code quickly.

## Demo checklist (screen)
1. `README.md` (run instructions) and the code map.
2. `python -m pytest` and `python -m tools.run_golden`.
3. Two curl calls against the deployed URL (`/health`, one `ALTA`).
4. A few lines of `experimentos.jsonl` and the matching spec row with its evidence ID.
