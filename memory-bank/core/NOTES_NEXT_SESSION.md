# Notes for Next Session

**Written:** 2026-09-19T10:25:49Z
**Status at Close:** ACTIVE. The "Gnucash modernization" thread is closed and its state persisted. The reimagine scaffold exists on disk but has never been executed; two modernization plans both claim to be the live one; nothing is committed.

---

## Priority Actions (do these first)

1. **T-0003 — Resume the Phase E.1 test migration.** Seven of forty test files were migrated before the thread died. Relaunch the migration for `identity-access`, `document-intelligence`, `accounting-engine` and `reporting` — **three agents at a time at most** (see B-0001). The original agent prompts are in the closed thread's transcript at `~/.claude/projects/-projects-gnucash/3e3acd0e-6043-4492-81f7-de1c91307316.jsonl`, jsonl idx 1967–1969.
2. **T-0004 — Generate Django migrations.** None exist. Every `migrations/` directory holds only `__init__.py`.
   ```bash
   cd modernized/gnucash-reimagined && python manage.py makemigrations identity accounting business_documents document_intelligence reporting
   ```
3. **T-0005 — Run the golden accounting tests** — 39 test functions that have never executed.
   ```bash
   cd modernized/gnucash-reimagined && python -m pytest tests/golden -x
   ```
4. **T-0006 — Fix the stale imports first if T-0005 fails on import.** The copied tests still import `accounting_engine.*` and `identity_access.domain.*`, and the legacy service trees are still on disk beside `apps/`, so a stale import can resolve silently to old code instead of erroring. A green run over legacy code is worse than a red one.
5. **T-0001 — Exercise `/session-start`.** Still never run as a real skill invocation.
6. **T-0007 — Confirm which modernization plan is live**, then mark the other dormant.
7. **T-0008 — Diagnose the two failures left in `ninja check`** — `test-qof` and `test-gnc-numeric` have been failing since the 09-18 preflight and were never looked at.
   ```bash
   ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **D-0001** — commit `.claude/`, `memory-bank/core/`, `analysis/` and `modernized/` to this fork, or exclude them from git entirely.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they become regression contracts.

---

## Context to Remember

- **Two plans, one tree.** `analysis/gnucash/MODERNIZATION_BRIEF.md` is a same-stack uplift (C++17/20, GTK4, Guile 3.0, pilot `libgnucash/engine/Account.cpp`) with an **unsigned** approval block. `analysis/gnucash/REIMAGINED_ARCHITECTURE.md` v2.1 is the greenfield Django SaaS and is marked approved. Only the second has a tree behind it: `modernized/gnucash-reimagined/`. The approved target stack, the five bounded contexts, and the rejected alternatives are recorded under **Decisions passed** in `current-state.md`.
- **Two generations coexist inside `modernized/gnucash-reimagined/`.** Round one scaffolded five standalone services (`identity-access/`, `accounting-engine/`, `business-documents/`, `document-intelligence/`, `reporting-analytics/`) — that was drift, and the user redirected it. Round two consolidated everything into `apps/{identity,accounting,business_documents,document_intelligence,reporting}/` as a modular monolith. The legacy service directories are **still on disk** next to `apps/`. `unified_consolidation/` is an empty abandoned directory.
- **The scaffold is thin where it matters.** 87 Python files under `apps/`, but 46 TODO/`NotImplementedError` markers — `apps/identity/services/{tenant_service,authentication,authorization}.py` are almost entirely `raise NotImplementedError`, and `apps/business_documents/api/` is all TODO. `common/` is 253 lines total. There is no frontend: the approved React/TypeScript layer has **zero** `.ts`/`.tsx`/`package.json` files.
- **Verified stopping point:** 2026-09-19T09:41–09:48Z. Phase E.1 checklist — (1) unified Django project ✅, (2) shared config ✅, (3) migrate models ⏳, (4) migrate tests ⏳, (5) behaviour contracts ⏳, (6) run golden accounting tests ⏳, (7) completion report ⏳. Three agents were launched for step 4: one died on 429, two never started because the permission classifier was rate-limited.
- **What the analysis tree holds** (19 artifacts, `analysis/gnucash/`): assessment (468,607 SLOC, 1,801 files, 43,275 complexity, 20 hotspots, 0% doc coverage, verdict refactor-in-place), topology (1,281 modules, 10 domains, 1 entry point `gnucash/gnucash.c main()`), `BUSINESS_RULES.md` (237 rules = 47 P0), `DATA_OBJECTS.md` (58 objects), `DELTA_CATALOG.md` (14 deltas; GTK3→GTK4 is the blocking one), and three completed spikes: multi-tenancy (RLS recommended), multi-currency (dual `amount`/`value` fields, hidden trading accounts), semantic verification (**GnuCash has no engine-level posted-journal immutability**; tax tables are referenced by pointer, not snapshotted, so editing a TaxTable silently mutates posted invoices).
- **Fork layout:** `origin` → `faizel-noorgat/gnucash`, `upstream` → `Gnucash/gnucash`, `stable` tracks `origin/stable` and was reset to `upstream/stable` at `fb2c773bf6`. Nothing is committed; HEAD is an upstream commit.
- **Sibling transcript:** `aa70ae1d-fca6-47eb-97ad-b6c5b7d2aa70.jsonl` is the earlier half of this same work (preflight → assess → map → brief → extract-rules) and is the origin of every artifact in `analysis/gnucash/`. It ends `continued-in` the thread just closed and contains **no** reimagine content. Do not treat it as a separate workstream.
- **Numbers in the artifacts disagree with each other.** `BUSINESS_RULES.md` says 47/164/26 P0/P1/P2; the transcript claims 47/142/48. `AI_NATIVE_SPEC.md` counts 36 rules and 21 entities against 237 and 58 in the analysis tree. Golden tests are 39 on disk but were reported as 20. File counts differ too: 1,345 (repo index) versus 1,801 (assessment). **The disk is the tiebreaker** — verify before quoting any of these.

---

## Do NOT Do

- **Do not run more than three agents at once.** The user set this rule after the first quota wall, and the thread still died on 429 (B-0001).
- **Do not assume a green test run means the monolith works.** The legacy service trees are still importable and sit beside `apps/`. Check what an import actually resolved to before trusting a pass (T-0006).
- **Do not trust the artifact counts above without re-deriving them from disk.**
- **Do not edit `memory-bank/runtime/session-scratchpad.json` by hand.** All mutations go through `.claude/scripts/session_scratchpad.py`.
- **Do not commit `memory-bank/runtime/`** — it is live per-session state and is already gitignored.
- **Do not send anything from `analysis/` or `modernized/` upstream.** They are exploratory and untracked; upstream-bound work must stay a minimal, reviewable diff against `main`.
- **Do not re-run the workflow scripts without re-checking the plugin-cache agent edits** (F-0001) — a plugin update wipes them, and the extraction agents then spawn without MCP access again.

---

## Human's Last Instruction

> we got rate limited, continue as normal. dont do it yourself, can you continue with the workflow where it stopped

The thread died before that could happen. Resuming the workflow where it stopped is the first action above, and it is what the user last asked for.
