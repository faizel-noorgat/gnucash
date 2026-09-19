# Current State

**Status:** ACTIVE

**Last Updated:** 2026-09-19T10:25:49Z

**Last Session Summary:** Closed the "Gnucash modernization" thread (ran 2026-09-18T12:48Z → 2026-09-19T09:48Z) by mining its transcript with five parallel investigators and checking every claim against the tree. The thread produced a 19-artifact analysis tree under `analysis/gnucash/` and a 459-file reimagine scaffold under `modernized/gnucash-reimagined/`, including spikes and an approved target architecture — but it never ran a single test on the new code, and it died on HTTP 429 while migrating tests. Two modernization plans now sit on disk both presenting themselves as the plan. Nothing is committed.

**Branch / HEAD:** `stable` @ `fb2c773bf6` — an upstream commit. Working tree carries `M .gitignore` plus four untracked directories: `.claude/`, `analysis/`, `memory-bank/`, `modernized/`.

**Workstream:** `modernization`

**Build state:** Not verified this session, and not attempted — this session did state mining, not code work. The last *verified* result stands from the 2026-09-18 preflight: at HEAD `fb2c773bf6` with a clean tree, `ninja` completed 845/845 targets and `ninja check` ran 133 tests with 131 passing. The two failures were `test-qof` and `test-gnc-numeric`; they were never diagnosed (T-0008). Do not carry that pass forward — it describes the tree as it was on 09-18, and it is not re-asserted here.

The reimagined tree is a separate and worse case: **nothing under `modernized/gnucash-reimagined/` has ever been executed.** No pytest run, no Django migration, no database, no import. Its 87 `apps/` files and 20 test files are written but unproven.

Verify the upstream tree with:

```bash
cmake -G Ninja -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

**Focus:** Closing the modernization thread — persisting its state and its stopping point, not advancing it.

**Next:** T-0003 — resume Phase E.1's stalled test migration. T-0004 and T-0005 unblock the golden accounting tests, which is the user's own gate for the whole phase.

**Pending Human Action:**

- **D-0001** — decide whether the four untracked trees (`.claude/`, `memory-bank/core/`, `analysis/`, `modernized/`) are committed to this fork or excluded from git entirely.
- **T-0007** — confirm that the reimagine track is the live plan and the same-stack uplift brief is dormant. Both are on disk claiming approval.
- **Q-0001** — confirm whether `borrowed/` plus `contrib/` are the off-limits trees. It was proposed by the assistant and never answered by the user.
- **Q-0002** — sign off the five medium-confidence P0 business rules before they are frozen as regression contracts.

**Known Blockers:**

| ID | Item | Owner | Blocks | Status |
|----|------|-------|--------|--------|
| B-0001 | Provider rate limits (HTTP 429) killed the thread mid-phase and, at the end, the permission classifier too — so two agent launches never started. Work must resume in batches of ≤3. | external | T-0003, T-0004, T-0005, T-0006 | open |

**Decisions passed:**

- 2026-09-19 — Session memory ported with two skills (`session-start`, `session-close`) rather than one multi-mode skill, matching the two Cursor commands 1:1.
- 2026-09-19 — Tracking axes adapted from py-hoarder's SDLC-phase × project-plan model to gnucash-native axes (workstream + build state). GnuCash has no phase plans or `prompts/` tree to track against.
- 2026-09-19 — `prompts/` and `docs/40-delivery/` deliberately excluded from the port; lessons learned live in `memory-bank/core/lessons-learned.md` instead.
- 2026-09-19 — Scratchpad tests ported from pytest to stdlib `unittest` so the suite adds no dependency to an upstream C/C++ project.
- 2026-09-18 — Forked to `faizel-noorgat/gnucash` (`origin`) with `Gnucash/gnucash` as `upstream`; `stable` was 641 ahead / 40 behind, so the fork was reset to `upstream/stable` and force-pushed. The pre-reset divergence came from unrelated history in the fork, not from this work.
- 2026-09-18 — Analysis scope: `bindings/*.i` counts as source (SWIG input), not generated code. Off-limits was proposed as `borrowed/` + `contrib/` — still unconfirmed (Q-0001).
- 2026-09-19 — Modernization target is a **greenfield multi-tenant cloud accounting SaaS**, not a same-stack uplift: Django + PostgreSQL + Celery + React/TypeScript, five bounded contexts (`identity`, `accounting`, `business_documents`, `document_intelligence`, `reporting`), delivered as a modular monolith with one Django app per context and REST only.
- 2026-09-19 — Rejected at design review: GraphQL, Django Channels/WebSockets, a separate AI service container, eight bounded contexts, full intercompany consolidation, and putting many client companies into one Tenant. A practice managing many clients is modelled explicitly (`Practice`, `PracticeMembership`, `ClientEngagement`, `AdvisorAccessGrant`), never by conflating tenants.
- 2026-09-19 — Multi-tenancy is shared-schema PostgreSQL with row-level security (`SET LOCAL`, transaction-local, fail-closed), not schema-per-tenant.
- 2026-09-19 — Posted-record immutability is enforced by PostgreSQL `BEFORE UPDATE`/`BEFORE DELETE` triggers plus service-layer guards, **not** a `CheckConstraint` — a constraint cannot compare OLD against NEW.
- 2026-09-19 — GnuCash's dual `amount` (account commodity) / `value` (transaction currency) fields are preserved, with trading accounts kept internally but hidden from the UI.
