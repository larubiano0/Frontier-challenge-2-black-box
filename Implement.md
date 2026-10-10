# Pi Agent — Operating Instructions

> **Immutable agent procedure.** Do not modify `Prompt.md`, `Implement.md`, or `Plan.md` unless the researcher explicitly authorizes it. Update `Documentation.md` as the living project memory. (Updated once, by explicit authorization, for Incident FR-0153; immutable again.)

**Current target: service VERSION 2** (Incident FR-0153: exactly three undisclosed behavioral changes vs. version 1). The 20 supplied examples are **historical v1 evidence**, not current expected behavior. Never assume or invent the three changes.

## Before doing anything

1. Read `Prompt.md`, `Implement.md`, `Plan.md`, `Documentation.md`, and the organizers' `README.md`. Inspect the existing repository and the supplied examples if present.
2. Summarize current verified behavior, unresolved hypotheses, implementation/test/deployment status, and available query budget. Treat absent files, missing credentials, and unknown constraints as unknown rather than pretending they exist.
3. Classify known evidence as: historical v1 / observed v2 / confirmed unchanged / confirmed changed / unknown version status.
4. State the **current mode** (`PROPOSE`, `INVESTIGATE`, `BUILD`, `VERIFY`, or `HANDOFF`) and the next bounded action. Work on one bounded objective at a time.
5. Do not ask the researcher to approve routine local edits/tests. **Original-service probing is different:** do not issue even one original-service request without an explicit approved hypothesis, scope, token, and per-agent request budget. Existing approved investigations may proceed autonomously until their cap or stop condition.

## Agent modes

### `PROPOSE` — no original API calls

Read existing evidence and unresolved issues. Return a concise shortlist of independently testable hypotheses (`H-001`, `H-002`, …). For each include: rationale and current evidence; alternative explanations; precise distinguishing requests or stateful sequences; expected outcomes under each explanation; estimated **total request cost including resets**; importance for hidden tests; and a suggested per-agent budget. Be **version-aware**: tag each hypothesis as targeting a possible v1→v2 change (category, e.g. integrity, parsing, command semantics, error codes/messages, precedence, state transitions, cancellation, boundaries) or an unknown/unchanged behavior; prefer equivalent requests from equivalent initial states; separate independent changes from consequences of one rule. Favor hypotheses with high expected value of information and low cost. Ask the researcher to select **one** and authorize a request cap. Do not begin `INVESTIGATE` automatically.

### `INVESTIGATE H-xxx, budget=N` — bounded autonomous experiment

**Precondition:** explicit human approval of exactly one hypothesis and numeric maximum `N` original-service requests. The approval applies only to that scoped investigation. Confirm the remaining per-token daily budget before probing; if it cannot be measured, use a conservative cap and report the uncertainty.

1. State the competing predictions and a minimal discriminating probe sequence.
2. Use **self-written** experimental scripts, a shared per-token request counter/rate limiter, and a token-specific lock so concurrent sequences cannot corrupt one another's original state. Multiple different tokens may investigate in parallel with isolated states.
3. Use `POST /__reset` when starting an independent sequence; record the reset and all subsequent original-service calls. A new `seq` denotes a distinct reset-controlled experiment. Include resets, health checks and other original requests in the assigned budget.
4. Append a durable entry to `experimentos.jsonl` **immediately for each original request**. Use these exact keys:

   ```json
   {"id": 1, "seq": "s1", "x_req": 1,
    "hipotesis": "H-001: ...", "request": {"m": "PING;64"},
    "status": 200, "response": {"pong": true},
    "conclusion": "..."}
   ```

   Add `version` and provenance metadata (e.g. `"version": 2`) in a supplementary trace or extra key if it does not break the required schema. `id` is globally unique and monotonically increasing. `x_req` is read from the **original response header**, never guessed (use `null` and flag it if absent). `request` is the exact body of the request; for non-`/msg` requests, also preserve method/path in a compatible metadata record or supplementary local trace so no HTTP information is lost. Keep the organizer-required fields intact. Do not fabricate a `conclusion`; omit it until justified. Preserve exact response data and status, including non-JSON text when present. Never log bearer credentials.
5. Check rate and daily limits before **every** request; cap to at most 10/s per token (prefer margin). Infrastructure rate-limit responses do not become behavioral claims. Stop safely on cap exhaustion, auth failure, unrecoverable connectivity problems, or human stop instruction.
6. Use counterexamples, boundary probes, malformed variants, repeated identical calls, error-precedence tests, and **2–12 step stateful sequences** as appropriate. Prefer adaptive probing over large blind sweeps.
7. Every original request must be logged (see step 4) and, via the golden workflow below, converted into fixtures. Reconcile observations against alternatives. Update `Documentation.md` and the behavioral specification with evidence IDs and confidence. If conclusions contradict the current implementation, create regression cases and flag the change; do not write code to accommodate unverified guesses.
8. Stop at `N`, or earlier if the hypothesis is sufficiently resolved. Report query count, evidence IDs, support/refutation, open questions, and the most informative next hypothesis. **Return control to the researcher for the next approval.**

### `BUILD` — standalone replacement implementation

- Use Python + FastAPI in a **single repo**. Separate route/auth, protocol parsing, validation/error handling, command handlers, data models (`dataclass`), and an in-memory store behind a swappable interface. Use the simplest structure consistent with current code; no unnecessary frameworks, queues, or microservices.
- Implement `/health`, `/__reset`, `/msg`, auth and unmatched routes/methods with **observed original behavior**, not FastAPI's defaults when they differ. Watch automatic 422 validation, body parsing, content types, trailing slashes, and error precedence.
- Make state changes explicit and atomic within the process; reset balances, accounts, operations, counters, and other discovered state. Keep order-sensitive semantics and legacy misspellings if observed.
- **Production code must contain no network route, import dependency, or fallback to the original or another replica.** The test harness may query the original; runtime code cannot.
- Keep credentials in environment variables, never tracked files. Prefer `FRONTIER_TOKEN` for the replacement token and a separately supplied `ORIGINAL_BEARER_TOKEN` for offline experiments (names can be mapped to the actual environment).
- For unknown cases, implement and document an explicit default as **`supuesto`**, not a proven behavior.
- After a coherent edit, run the relevant local tests. Do not report success without execution. Describe what was and was not verified.

### `VERIFY` — differential and regression evaluation

- The **20 supplied examples** (v1) may be replayed as ONE ordered sequence after reset as a *historical* suite; expected mismatches against v2 are information, not necessarily bugs, and must not be treated as current expectations until verified on v2. Never test them as 20 independent requests.
- Run the golden regression suite per the section below.
- Compare matching reset-controlled sequences against the original (when authorized and budgeted) and the local replacement. Compare statuses and typed JSON structures/values (key order irrelevant; array order fixed), or exact text if either body is non-JSON. Preserve mismatches with expected/actual outputs and reproducing sequence.
- Keep golden cases from observed v2 original traces, plus locally generated unit, stateful, authentication, malformed-input, routing, and regression tests. Never assume a test is confirmed by the original if it was generated without querying it.
- Cover both single calls and 2–5 / 6–12 request sequences, including repeated operations, cancels, reset effects, unknown account/operation references, validation precedence, and state interactions.
- Measure exact **sequence pass rate**, per-command/error agreement, response time (<5s), regressions, and original-query consumption. A request-level match is not necessarily a passing sequence.
- If the researcher provides results from `/evento/resultados`, log them as **external hidden-set feedback**, not evidence of a particular black-box rule.

### `HANDOFF` — durable agent memory

Before ending a substantial session, update `Documentation.md` with what changed, exact observed evidence IDs, competing hypotheses, rejected hypotheses, implementation/test status, mismatches, blockers, available budget, and the next *single* recommended action. Link large artifacts instead of pasting entire logs into agent context. The next agent must independently inspect cited evidence before relying on a conclusion.

## Evidence and specification discipline

Maintain a distinct graded specification (for example `specification.md`) with these **seven README-mandated sections**: `Entrada`, `Integridad`, `Comandos` (one block per command), `Memoria entre requests`, `Errores` (including precedence), `Cambios durante el día`, `Riesgos`. Within each section use `ID | Comportamiento | Evidencia | Confianza`. Accepted labels are exactly **`confirmado`**, **`probable`**, **`supuesto`**. Do not label a rule `confirmado` without repeated supporting probes; a single observation is generally `probable`. Each asserted behavior must cite actual IDs in `experimentos.jsonl`; the 20 provided examples are a starting fixture, **not** entries in that log unless replayed and recorded by us. False claims are penalized, so omit or mark uncertainty rather than invent evidence.

## Change/incident procedure

Incident **FR-0153** (version 2) is active: investigate the three changes through the normal approval flow (hypothesis → human approval → budget). For each confirmed change record in `Documentation.md` and the specification (`Cambios durante el día`): v1 behavior, v2 behavior, evidence/experiment IDs, confidence, and replacement implications; state how it was distinguished from a consequence of another rule. Do not declare a change confirmed without evidence, and do not stop at fewer or more than evidence supports (expected total: three independent changes). Prepare a debrief-ready explanation. The original may change again during the day. Allocate a reserve of the token budget for later. Periodically run a **small, approved sentinel suite**, recording its original calls; on a behavior change, identify the first contradictory evidence, isolate affected rules, update `Documentation.md`/the specification, add reproducible regression tests, and patch the minimal module. Avoid confusing infrastructure throttling with a service change. The final observed version at 20:00 Bogotá is what matters.

## Working style and safety

- Prefer inspect → hypothesize → test → implement → verify → document. Optimize for correctness and evidence rather than lines of code or number of agents.
- Never spend the request budget without a hypothesis and a stopping rule. Do not start a new independent hypothesis merely because tokens or context remain.
- Do not overwrite experiment logs, reorder entries, alter observed responses, or delete negative evidence.
- Do not modify immutable instruction files. Put progress in `Documentation.md`; put data in `experimentos.jsonl`; put graded claims in the specification; put executable behavior in code/tests.
- If instructions conflict with the challenge README, follow the README and notify the researcher.
- Favor precise, short researcher-facing summaries and explicit next actions over long unverified narratives.

## Mandatory Continuous Golden Regression Testing

Applies to every agent. **No agent may silently bypass, weaken, skip, or edit expectations of the golden suite.**

### Workflow

`Original API (v2) → request/response capture → experimentos.jsonl → golden fixtures → local FastAPI replacement → automatic differential comparison → MATCH | MISMATCH → failure report`

1. **Accumulation.** Every eligible v2 observation (successes *and* application-level errors, non-JSON bodies included) automatically yields a golden assertion with exact status and body. Do not hand-pick successes. Infrastructure responses (`X-Frontier-Infra: rate-limit`) and invalid/corrupted records are ineligible; document why, never delete.
2. **Stateful sequences.** Fixtures store complete sequences from a known reset (reset represented explicitly), steps in original order, each with its expected response and source experiment `id`. Never test stateful requests independently. Fixtures carry `version` and provenance.
3. **Version separation.** v2 fixtures form the current suite. v1 evidence (incl. the 20 examples) lives in a separate historical suite; a v1 case is promoted to v2 only after v2 verification, keeping its provenance. If v2 contradicts v1, keep both. Never mix them in the current suite.
4. **Exact comparison** (README rules): status; JSON values/strings/numbers/types identical; array order fixed; object key order ignored; non-JSON compared character-for-character. Preserve error codes/messages, capitalization, whitespace (e.g. trailing spaces), misspellings, sequential IDs, state effects, cancellation behavior.
5. **Offline only.** Regression runs use recorded evidence and the local replacement; they **never call the original API** or consume budget.
6. **Run after every backend change** (and before marking any milestone complete): execute the full applicable suite; mimic evaluation conditions (reset before each sequence; 1-request, 2–5 and 6–12 step sequences; <5 s per step).
7. **Failure report**: for each failing sequence give the earliest failing step, expected vs. actual status/body, source experiment IDs, and whether it is a newly introduced regression or a known mismatch. Record unresolved failures in `Documentation.md`.
8. **Metrics** (report every run): Request Agreement Rate = correctly reproduced requests / evaluated requests; Sequence Agreement Rate = completely correct sequences / evaluated sequences; total golden sequences; total recorded requests; passing and failing sequences; newly introduced regressions; remaining known mismatches.
9. **Immutability.** Never change expected outputs to make tests pass. If evidence is wrong or superseded, annotate the reason and keep the original record.
10. **Tooling separation.** Fixture generation, replay and research scripts live outside the production app package; production code contains nothing that can reach the original or another replica.

### Responsibilities

- **Hypothesis Generator** (`PROPOSE`): reviews logs, golden failures, and version-status classes; proposes competing, version-aware hypotheses (incl. v1→v2 change candidates) with discriminating experiments and budget estimates; never queries the original; never self-approves.
- **Experimental Agent** (`INVESTIGATE`): acts only on the one human-approved hypothesis within its explicit request budget (resets included); logs every request immediately; ensures new observations become golden fixtures; updates/rejects hypotheses by evidence; records candidate and confirmed changes; produces a structured handoff (queries used/remaining, evidence IDs, supported/rejected hypotheses, open questions, suggested next hypothesis); then returns control.
- **Backend Implementation Agent** (`BUILD`): implements v2 behavior only from cited evidence (unverified rules marked `supuesto`); runs the golden suite after every change; reports metrics and new regressions; fixes failures in code, never in fixtures. Research→Backend communication goes through `experimentos.jsonl`, golden fixtures, the specification and `Documentation.md` (evidence IDs, confidence, implications); Backend→Research through failing sequences and `supuesto` rules that need experiments.
- **Verification Agent** (`VERIFY`): independently reruns the suite, checks fixture completeness against the log (every eligible v2 entry represented), version separation, exact comparison, the no-original-call guarantee, latency, and reports metrics/mismatches; may propose but not approve new experiments.

### Hand-off requirements

At each `HANDOFF`, `Documentation.md` must include the latest regression metrics, known mismatches, confirmed/suspected v1→v2 changes with evidence IDs, remaining budgets, and one recommended next action. Successors re-inspect cited evidence rather than trusting conclusions.
