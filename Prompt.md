# FRONTIER 2026 — Challenge 2: La caja negra

> **Immutable project charter.** Do not modify this file unless the researcher explicitly requests a change. Operational progress belongs in `Documentation.md`. (Updated once, by explicit authorization, for Incident FR-0153; immutable again.)

## Mission

Reconstruct the **observable behavior** of an undocumented, stateful HTTP service, including legacy quirks, failures, error precedence, and state transitions. Deliver a standalone, internet-accessible replacement that produces the same **HTTP status and response body** as the current original service for previously unseen requests and request sequences.

The goal is **behavioral equivalence**, not a cleaner redesign. Never silently fix a legacy bug that clients can observe.

## Current target — Version 2 (Incident FR-0153)

Ticket **FR-0153** (HIGH, opened 15:30 Bogotá): *"The provider deployed version 2 of the service without prior notice."* The original now runs **VERSION 2**. **Exactly three observable behaviors changed**; everything else is identical to version 1. The organizers have not disclosed which three or how. **Their identities are unknown; never invent them.**

- **Version 2 is the implementation target from the start.** Do not build version 1 first. Hidden conformance tests and the final deployed replacement target version 2.
- The team must: (1) discover the three changes; (2) determine the new behavior of each; (3) document supporting evidence in `experimentos.jsonl`; (4) make the replacement reproduce version 2; (5) explain the changes in the technical debrief. Incident response counts toward the Execution score.
- Distinguish **independent changes** from multiple mismatches that are consequences of one changed rule. Do not declare a change confirmed without evidence. For each confirmed change preserve: version 1 behavior, version 2 behavior, supporting evidence, experiment IDs, confidence, and implications for the replacement. Candidate categories (not confirmed changes) include integrity validation, parsing, command semantics, error codes/messages, validation precedence, state transitions, account/transaction behavior, cancellation, and boundaries.
- **Evidence classes** must stay separate and labeled with version and provenance: historical v1 observations; observed v2 behavior; confirmed unchanged; confirmed changed; unknown version status. Historical evidence is never silently overwritten. A v1 observation becomes a current v2 expectation only after sufficient v2 verification.

## Authoritative materials

1. The organizers' `README.md` is the binding competition contract.
2. `pruebas/ejemplos.jsonl` contains **20 requests in one ordered sequence after a reset**, captured against the morning version (**version 1**). It is **historical v1 evidence**, valuable for hypotheses, but **not** automatically current expected behavior; version 2 may differ in exactly three behaviors.
3. The current original service, queried through authorized experiments, provides additional evidence; it now runs **version 2** and may change again.
4. `Documentation.md`, `experimentos.jsonl`, and the inferred specification are derived research artifacts, not substitutes for observations.

Original service: `https://caja-negra-production-c64f.up.railway.app`.
Authorized experiment endpoints include `POST /msg`, `POST /__reset`, and `GET /health`. Each original-service request uses `Authorization: Bearer <participant token>`. Obtain tokens securely from the researcher / environment. **Never print, commit, or store raw tokens in research logs.**

## Required deliverables (20:00 Bogotá time)

1. **Standalone replacement** deployed on **Railway**, reachable over the internet. Implement `POST /msg`, `POST /__reset`, `GET /health`, bearer-token handling, and matching behavior for all other routes and methods (including non-existent routes). Every evaluation test begins with `/__reset`.
2. **Behavioral specification** allowing another engineer to reproduce the service without querying the original. Use the exact seven sections required by the organizers: **Entrada, Integridad, Comandos, Memoria entre requests, Errores, Cambios durante el día, Riesgos**. Each section contains a table `ID | Comportamiento | Evidencia | Confianza`.
3. **`experimentos.jsonl`** containing **one entry per request sent to the original**, with unique `id`, `seq`, response-header `x_req`, `hipotesis`, exact `request`, `status`, exact `response`, and optional `conclusion`. Specification claims must cite evidence IDs from this log.

## Non-negotiable rules

- The **deployed replacement never calls the original service or another replacement**, directly or indirectly. This is a disqualifying failure.
- Original-service calls are permitted **only in separate experimental tooling** and within the researcher's authorization and the official challenge rules. Custom scripts and fuzzers are allowed; do not rely on an external product that performs black-box replication for us.
- Maximum **10 requests/second and 8,000 requests/day per original-service token**, counting all original requests, including resets. If the response carries `X-Frontier-Infra: rate-limit`, it is an **infrastructure response**, not target behavior. Stop or back off; do not learn from it.
- Each replacement step has **5 seconds** to respond. The evaluator uses **one process**, so a simple in-memory state store is appropriate; do not rely on data surviving a process restart.
- Each evaluation test starts with a reset. The hidden set contains **100 tests**: 40 single-request tests, 45 sequences of 2–5 requests, and 15 sequences of 6–12 requests. No hidden test repeats the supplied example sequence.
- A test passes only when **every compared step** has the same status and body. Compare parsed JSON without regard to object-key order, while preserving array order and exact scalar values/types; for non-JSON text, compare character-for-character. Headers are not scored, but `X-Req` is required in the experiment log.
- The original may change during the event; the replacement is evaluated against the version current at **20:00 Bogotá time**. Participant access to the original ends at that time.
- Do not fabricate observations, inferred rules, experiment results, implementation status, or hidden-set scores.

## Chosen architecture

A **modular monolith** in **Python + FastAPI**, deployed to Railway. Keep HTTP routing/authentication, raw request parsing, control/integrity validation, command dispatch, business rules/error mapping, and storage responsibilities conceptually separate, while remaining in one repository and one deployable service.

Keep research and replacement subsystems separate; the original may be queried only by authorized experimental tools/agents during development. Use **classes/dataclasses**, dictionaries indexed by account/operation IDs, counters, and explicit state transitions. Start with an **in-memory store** that `/__reset` can fully reinitialize. Keep a narrow storage boundary so SQLite could be substituted **only if a discovered requirement warrants it**. Prefer deterministic, testable rules over an LLM in the production request path.

Research tooling is **offline/independent of the deployed service**:

`Hypothesis Proposer → Researcher chooses ONE hypothesis + budget → Experimental Agent → Original API (v2) → experimentos.jsonl → Golden fixtures → Local replacement → Differential comparison → Evidence/Specification → New-agent context`.

- **Hypothesis Proposer:** proposes multiple competing, falsifiable hypotheses with rationale, predicted observations, and discriminating probes. It does **not** query the original.
- **Researcher:** explicitly approves **one hypothesis at a time** and defines its scope and maximum original-service request count.
- **Experimental Agent:** autonomously explores **only that approved hypothesis** within its assigned cap, including resets and follow-up probes; seeks counterexamples, updates the evidence, and then hands off. It may refine subhypotheses within the approved scope but **cannot self-approve a new investigation**.
- **Durable memory:** preserve observations, evidence IDs, uncertainty, counterexamples, outstanding questions, and decisions across new agents. An agent inherits evidence, **not unexamined assertions**.

## Continuous golden regression (core objective)

Every eligible **version 2** observation from the original must become part of a persistent, executable golden regression suite, built from complete reset-started stateful sequences (successes **and** application-level errors), compared exactly (status, body per README rules) against the local replacement, and replayed after **every** backend change using recorded evidence only — **never the original API**. Expected outputs are never rewritten to make tests pass; invalid or superseded evidence is annotated, not altered. v1 and v2 expectations are kept in separate suites. Procedures are in `Implement.md`; milestones in `Plan.md`.

## Initial observations — not complete rules

The supplied examples exercise `PING`, `ALTA`, `CONSULTA`, `DEPOSITO`, `TRANSFER`, and `ANULA`; demonstrate account/operation identifiers, balances, and repeated cancellation; and show responses with unexpected spellings (for instance `"recieved"`). These are v1 examples, not proof of all input constraints or semantics. The control-field algorithm, arity and coercion rules, error precedence, limits, state lifecycle, and future changes remain open questions until tested.

## Success criteria and priorities

Prioritize **exact version 2 equivalence, working HTTP compatibility, reproducible evidence, generalization to hidden sequences, and deployability**. Build a small runnable baseline early; improve it by evidence-driven changes with regression tests. Separate *observed*, *inferred*, and *assumed* behaviors. Under time pressure, prefer a verified partial implementation to a broad but untested implementation. Surface uncertainty and trade-offs to the researcher instead of guessing silently.
