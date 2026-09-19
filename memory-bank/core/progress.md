# Progress

Done / Pending / Backlog across sessions.

**This file is written only during `/session-close` and is deliberately not read during boot.** It is a historical ledger, not working state. For where things stand right now, read `current-state.md`.

---

## Done

- **2026-09-19** — *Made the reimagined tree execute for the first time.* It never could: a phantom `decimal-converter` PyPI dependency made `pip install -e ".[dev]"` impossible, and once that was removed, a `Decimal` used in a def-time annotation in `apps/accounting/models/fiscal.py` killed `django.setup()` for the whole project. Provisioned `~/.venvs/gnucash-reimagined` (Django 5.2.17, pytest 8.4.2, psycopg 3.3.6) — outside the repo, because `.venv` is not gitignored. The suite now collects at 186 tests with zero errors and runs on PostgreSQL 16.15.
- **2026-09-19** — *Migrated the test suite into one directory per bounded context* (`tests/{accounting,identity,business_documents,document_intelligence,reporting}/`), mirroring `apps/`, preserving domain organisation and test-function counts per context. Fixed every stale import, added `testpaths = ["tests"]` so pytest stops collecting the legacy service trees, and registered three unregistered markers (`acceptance`, `rule`, `golden_dependency`) that `--strict-markers` would otherwise have hard-errored on.
- **2026-09-19** — *Generated the schema.* Seven initial migrations across the five apps; `makemigrations --check` clean. Verified to apply and reverse cleanly against an empty database.
- **2026-09-19** — *Golden accounting suite green on PostgreSQL for the first time*, then hardened: 40/40. Eight initial failures were classified before fixing — six were invalid fixtures constructing posted entries directly or building invalid state outside `pytest.raises`, one was a real implementation defect (BR-BUS-001 un-posting was unguarded), one fixture both contradicted and failed to exercise BR-ACCT-002. No safeguard weakened.
- **2026-09-19** — *Found and fixed a false-negative in the balance check.* `_check_balance_per_commodity` folded `amount` and `value` into one accumulator, so two errors cancelled: a single line with amount +100 and value −100, with no offsetting line, was reported balanced. Since `is_balanced` gates posting, unbalanced entries could be posted. Fixed, with a regression test.
- **2026-09-19** — *ADR-010 enforced in PostgreSQL.* `accounting/0003_adr010_posted_immutability.py` installs `BEFORE INSERT/UPDATE/DELETE` triggers; policy expressed as an allow-list of mutable columns so new columns are protected by default. 16 PostgreSQL-specific tests, all via `QuerySet.update()`, `bulk_create` or raw SQL so a pass cannot come from Django validation. Independently proved with a raw psycopg connection and no Django in the process.
- **2026-09-19** — *Business-documents posting wired in-process and green* (15/15, was 15 failing). Five root causes: factories using legacy field names, `create_user` without the required email, BR-BUS-002 unenforced, two tests calling `pytest.xfail` unconditionally and thereby disabling their own assertions, and `DocumentPostingService.post_document` scaffolded against an imagined accounting API.
- **2026-09-19** — *Repaired dropped services in accounting and reporting.* `PostingService.void_journal_entry` had called `PostingService.create_reversal_entry`, a method on a different class — voiding had never worked. Reversal/correcting links are now set at creation rather than after posting. Ported the missing reporting modules (`ai_explainer`, `golden_dependency`) and remapped the two renamed ones.
- **2026-09-19** — *Centralised tenant context* into `common/middleware/tenant.py` as the single authoritative implementation; apps may re-export but not reimplement.
- **2026-09-19** — Committed the modernization workstream to the fork on branch `modernization/reimagine-scaffold` (`74374234d1`): 417 files, 59,762 insertions covering `analysis/`, `modernized/`, `.claude/`, `memory-bank/core/`. Extended `.gitignore` to exclude `memory-bank/runtime/` live state, `.claude/scheduled_tasks.lock`, and `__pycache__`/`*.pyc`. Branch is local only; `stable` untouched. (Resolves D-0001.)
- **2026-09-19** — Ported session memory from the py-hoarder-v2 Cursor skill to Claude Code. Created `.claude/skills/session-start` and `.claude/skills/session-close`; ported `session_scratchpad.py` verbatim to `.claude/scripts/`; scaffolded `memory-bank/core/` and `memory-bank/runtime/`; ported the scratchpad test suite to stdlib `unittest`.
- **2026-09-19** — Closed the "Gnucash modernization" thread (09-18T12:48Z → 09-19T09:48Z) by mining its transcript with five parallel investigators and verifying every claim against the tree. Recorded the stopping point, the two conflicting plans, the unrun test suite, and the four open human decisions in the Memory Bank.
- **2026-09-18/19** — *Inside the modernization thread:* environment preflight and analysis-tool install (`scc`, `lizard`, `glow`, `delta`); fork created and reset to upstream at `fb2c773bf6`; assessment (468,607 SLOC, 1,801 files, 20 hotspots, 0% doc coverage); topology map (1,281 modules, 10 domains, 3 persona flows); business-rule extraction (237 rules = 47 P0, 58 data objects); delta catalog (14 deltas); three completed design spikes (multi-tenancy, multi-currency, semantic verification); target architecture approved through three HITL checkpoints; five bounded contexts scaffolded twice — once as standalone services (drift, redirected) and again as a Django modular monolith under `apps/`.

---

## Pending

Current suite: **120 passed, 66 failed** of 186. accounting 56/56, reporting 18/18, business_documents 15/15, identity 24/65, document_intelligence 7/32. The 66 failures are exactly T-0010 (41) plus B-0002 (25).

- **T-0010** — implement the three stub identity services. 41 failures; the last major Phase E.1 gap. The stubs use `raise NotImplementedError` *and* their method names do not match their own contract tests.
- **T-0009** — push `modernization/reimagine-scaffold` to the fork. The branch, and 64 dirty paths of this session's work, exist only locally.
- **B-0002** — 25 document-intelligence tests subclass `unittest.TestCase` while taking pytest fixtures; structural, no implementation work fixes it.
- **B-0004 → B-0003** — the RLS SQL functions declare `integer` returns where every PK is a UUID (the cast fails and is silently swallowed), and no migration installs the functions or any policy.
- **T-0014** — the unmanaged `ImmutablePostedJournal*` models break every ORM delete of a journal entry or line.
- **T-0007** — confirm which modernization plan is live and mark the other dormant.
- **T-0008** — diagnose the two failing tests in the *upstream* tree's `ninja check` (`test-qof`, `test-gnc-numeric`); unrelated to the reimagine work.
- **Q-0001 / Q-0002 / Q-0003** — confirm the off-limits trees; sign off the five medium-confidence P0 rules; decide whether `DocumentPostingService` owns the draft→posted transition.
- **F-0001 / F-0002 / F-0003** — re-apply the plugin-cache agent edits after any plugin update; declare `FRONTEND_URL` and the `LLM_*` settings currently read via `getattr` fallbacks; carry project/cost-centre support as future Dimension work.

---

## Backlog

- **Residual stubs by context:** identity 15, business_documents 15, document_intelligence 10, reporting 1, accounting 0 `TODO`/`NotImplementedError` markers. These are not 41 tasks — the markers mix genuinely missing behaviour with hardening notes and stale comments, and need reclassifying before anything is scheduled from them.
- **The same-stack uplift track is dormant, not dead.** `MODERNIZATION_BRIEF.md` (C++17/20, GTK4, Guile 3.0, five phases, pilot `libgnucash/engine/Account.cpp`) is fully planned and was never started. Its approval block is unsigned. `DELTA_CATALOG.md` (14 deltas, GTK3→GTK4 blocking, 237+ API call sites) stays valid if that track is ever revived.
- **Lot tracking** is deferred to v2 of the reimagined system, though its data model was designed.
- **Full intercompany consolidation** — consolidation groups, automatic eliminations — deferred out of v1; only a minimal intercompany slice was kept.
- **The React/TypeScript frontend** is approved in the architecture but has no code at all.
