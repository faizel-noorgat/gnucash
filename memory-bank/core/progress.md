# Progress

Done / Pending / Backlog across sessions.

**This file is written only during `/session-close` and is deliberately not read during boot.** It is a historical ledger, not working state. For where things stand right now, read `current-state.md`.

---

## Done

- **2026-09-19** — Ported session memory from the py-hoarder-v2 Cursor skill to Claude Code. Created `.claude/skills/session-start` and `.claude/skills/session-close`; ported `session_scratchpad.py` verbatim to `.claude/scripts/`; scaffolded `memory-bank/core/` and `memory-bank/runtime/`; ported the scratchpad test suite to stdlib `unittest`.
- **2026-09-19** — Closed the "Gnucash modernization" thread (09-18T12:48Z → 09-19T09:48Z) by mining its transcript with five parallel investigators and verifying every claim against the tree. Recorded the stopping point, the two conflicting plans, the unrun test suite, and the four open human decisions in the Memory Bank.
- **2026-09-18/19** — *Inside the modernization thread:* environment preflight and analysis-tool install (`scc`, `lizard`, `glow`, `delta`); fork created and reset to upstream at `fb2c773bf6`; assessment (468,607 SLOC, 1,801 files, 20 hotspots, 0% doc coverage); topology map (1,281 modules, 10 domains, 3 persona flows); business-rule extraction (237 rules = 47 P0, 58 data objects); delta catalog (14 deltas); three completed design spikes (multi-tenancy, multi-currency, semantic verification); target architecture approved through three HITL checkpoints; five bounded contexts scaffolded twice — once as standalone services (drift, redirected) and again as a Django modular monolith under `apps/`.

---

## Pending

- Resume the Phase E.1 test migration — 33 of 40 test files remain (T-0003).
- Generate Django migrations for the five apps; none exist (T-0004).
- Run the golden accounting tests for the first time — 39 test functions, never executed (T-0005).
- Fix the stale imports in the copied tests so a pass proves the monolith, not the legacy tree (T-0006).
- Confirm which modernization plan is live and mark the other dormant (T-0007).
- Diagnose the two failing tests in `ninja check` (`test-qof`, `test-gnc-numeric`) (T-0008).
- Exercise `/session-start` end to end and confirm the boot sequence behaves (T-0001).
- Decide whether `.claude/`, `memory-bank/core/`, `analysis/` and `modernized/` are committed or excluded from the fork's history (D-0001).
- Confirm the off-limits trees (Q-0001) and sign off the five medium-confidence P0 rules (Q-0002).
- Re-apply the plugin-cache agent edits after any `code-modernization` plugin update (F-0001).

---

## Backlog

- **The same-stack uplift track is dormant, not dead.** `MODERNIZATION_BRIEF.md` (C++17/20, GTK4, Guile 3.0, five phases, pilot `libgnucash/engine/Account.cpp`) is fully planned and was never started. Its approval block is unsigned. `DELTA_CATALOG.md` (14 deltas, GTK3→GTK4 blocking, 237+ API call sites) stays valid if that track is ever revived.
- **Lot tracking** is deferred to v2 of the reimagined system, though its data model was designed.
- **Full intercompany consolidation** — consolidation groups, automatic eliminations — deferred out of v1; only a minimal intercompany slice was kept.
- **The React/TypeScript frontend** is approved in the architecture but has no code at all.
