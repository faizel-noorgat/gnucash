# Notes for Next Session

**Written:** 2026-09-19T13:26:04Z
**Status at Close:** IDLE. Branch `modernization/reimagine-scaffold` @ `6af43d13cb`, working tree **dirty (64 paths)**, branch **local and unpushed**. The reimagined Django tree now genuinely executes: 186 tests collected, 120 passed, 66 failed on PostgreSQL 16.15.

---

## Priority Actions (do these first)

1. **T-0010 — Implement the three stub identity services.** This is the single biggest win available: 41 of the 66 remaining failures.

   `apps/identity/services/{authentication,authorization,tenant_service}.py` are entirely `raise NotImplementedError`, **and their method names do not match their own contract tests**. The tests need `authenticate_user`, `generate_access_token`, `validate_token`, `is_tenant_member`, `get_accessible_tenants`, `get_tenant` — none of which exist in the stubs, which also use instance methods where the tests call at class level.

   Port behaviour from `identity-access/identity_access/domain/services/`. Target the flat `apps/identity/services/` package — do **not** recreate the legacy `domain/` + `infrastructure/` layering. The contract is `tests/identity/unit/test_services.py`; make the methods match what it calls.

2. **T-0009 — Push the branch.** The entire modernization workstream, plus everything this session produced, exists only on this machine.
   ```bash
   git push -u origin modernization/reimagine-scaffold
   ```

3. **B-0002 — Decide the document-intelligence test structure.** 25 of 32 tests subclass `unittest.TestCase` while their methods take pytest fixtures, which pytest cannot inject. This is structural, not implementation work: no amount of code makes them pass. Choose between rewriting the classes as plain pytest classes or moving fixtures into `setUp()`. Affects BR-DI-001 through BR-DI-010 coverage.

4. **B-0004 then B-0003 — provision RLS.** B-0004 first: `docker/init-db.sql` declares `get_current_user_id()` / `get_current_entity_id()` as `RETURNS integer` while every PK is a UUID, and the function's `EXCEPTION WHEN OTHERS THEN RETURN NULL` swallows the failed cast, so policies would read NULL silently. Fix the return types, then write a `RunSQL` migration under `common/rls/` installing the functions and policies.

5. **T-0014 — the unmanaged `ImmutablePostedJournal*` models break every ORM delete** of a journal entry or line: Django's deletion collector follows their relations and emits `DELETE FROM accounting_immutable_posted_journal_line`, which does not exist. Either give them real tables or take them out of the deletion path.

6. **T-0008 — diagnose `test-qof` and `test-gnc-numeric`** in the *upstream* tree (unrelated to the reimagine work):
   ```bash
   cmake --build build && ctest --test-dir build -R "test-qof|test-gnc-numeric" --output-on-failure
   ```

**Waiting on the human (cannot be resolved by reading the tree):**

- **T-0007** — confirm the reimagine track is live and the same-stack uplift brief is dormant. Both claim approval on disk.
- **Q-0001** — confirm the off-limits trees (`borrowed/` + `contrib/` were proposed, never answered).
- **Q-0002** — sign off the five medium-confidence P0 rules before they harden into regression contracts.
- **Q-0003** — decide whether `DocumentPostingService` should own the draft→posted transition. Today the caller does it, matching the legacy contract, and all 15 business-document tests pass. Changing it means editing a test.

Lower priority: **F-0001** (re-apply plugin-cache agent edits after a plugin update), **F-0002** (`FRONTEND_URL` and the `LLM_*` keys are undeclared settings, read via `getattr` fallbacks), **F-0003** (project/cost-centre support belongs to a future Dimension model), **F-0004** (residual `TODO`/`NotImplementedError` markers by context — identity 15, business_documents 15, document_intelligence 10, reporting 1, accounting 0; reclassify each as missing behaviour, hardening note, or stale comment before scheduling any of it).

---

## Context to Remember

- **Environment.** Tests run with `~/.venvs/gnucash-reimagined/bin/python -m pytest`, from `modernized/gnucash-reimagined/`. System `python3` has **no Django** — it will fail confusingly. There is deliberately **no venv inside the repo**: `.venv` is not gitignored and would dirty the tree. PostgreSQL 16.15 runs locally with `postgres`/`postgres`. **Docker is not installed**, so `compose.yml` is unusable and `docker/init-db.sql` never runs.

- **The test database.** `config/settings/test.py` points at `gnucash_test`, which pytest creates and drops itself. Do not create it by hand — a leftover `gnucash_test` makes pytest log "Got an error creating the test database: database already exists" and obscures the real run.

- **Where the suite stands.** accounting **56/56** (golden **40/40**, ADR-010 **16/16**), reporting **18/18**, business_documents **15/15**, identity **24/65**, document_intelligence **7/32**. The 66 failures are exactly T-0010 (41) plus B-0002 (25) — nothing else.

- **The recurring defect pattern.** Phase E.1's "migrate models" step was recorded complete but was materially incomplete: **services and support modules were dropped** during consolidation, and migrated code kept referring to things that never existed. Every failure this session had that shape. When something is inexplicably red, suspect a reference to a legacy name before suspecting logic. Concrete instances found: a phantom `decimal-converter` PyPI dependency (made `pip install` impossible), a `Decimal` used in a def-time annotation with no import (killed `django.setup()` for the whole project), 9 FKs pointing at `"auth.User"` with a swapped-out user model, a `User` model with `USERNAME_FIELD='email'` and **no matching manager**, `PostingService.create_reversal_entry` called on the wrong class (voiding had never worked), and `DocumentPostingService` scaffolded against an imagined accounting API.

- **Two migrations were added this session** and the schema is now real: 7 initial migrations across the five apps, plus `accounting/0003_adr010_posted_immutability.py`. `makemigrations --check` is clean.

- **ADR-010 is enforced in PostgreSQL**, not just the ORM. The policy is an allow-list of mutable columns compared via whole-row `to_jsonb(OLD)` minus those keys, so new columns are protected by default. Only `updated_at` is mutable on a posted entry; `updated_at`, `reconcile_status`, `date_reconciled`, `online_id` on a posted line. `BEFORE INSERT` is guarded on lines too. There is **no bypass of any kind** and there must never be one.

- **Corrections work by creating new rows.** `DocumentPostingService` now calls `PostingService.create_and_post_journal_entry` in-process. The reversal/correcting links (`reversal_of`, `is_reversal`, `correcting_of`) are passed **at creation**, because the entry is posted before that call returns and ADR-010 then forbids further mutation.

- **Test layout.** One directory per bounded context under `tests/`, mirroring `apps/`, each with its own `conftest.py`. `tests/conftest.py` holds no fixtures — an earlier version overrode `django_db_setup` and thereby suppressed test-database creation entirely.

---

## Do NOT Do

- **Do not run more than three agents at once.** Standing user rule. (The rate-limit blocker that originally motivated it is closed, but the rule stands.)
- **Do not weaken, bypass, or add an escape hatch to any safeguard.** No `force=`, `_skip_validation`, `save_raw`, settings switch, session variable, or bypass manager. The accounting immutability guarantees are the product's core value. If a test or fixture conflicts with a guard, fix the fixture.
- **Do not create a posted `JournalEntry` directly** (`is_posted=True` on create). Post through `PostingService` / `JournalEntry.post()` so balance, fiscal-period and audit checks run.
- **Do not re-add an unconditional `pytest.xfail(...)` inside a test body.** It silently disables every assertion below it. Two such calls were hiding a completely broken posting service.
- **Do not hand-edit `memory-bank/runtime/session-scratchpad.json`.** All mutations go through `.claude/scripts/session_scratchpad.py`.
- **Do not commit `memory-bank/runtime/`** — live per-session state, already gitignored.
- **Do not send anything from `analysis/` or `modernized/` upstream.** Fork branch only; upstream-bound work stays a minimal, reviewable diff against `main`.
- **Do not add or restore `accounting.Project`**, and do not re-add `DocumentLine.project`. Project/cost-centre support is future Dimension work.
- **Do not trust the artifact counts in `analysis/`** without re-deriving them from disk. They disagree with each other and with the transcripts.

---

## Human's Last Instruction

> `/session-close`

Preceded by the three work directives that produced this session's results, in order:

1. *"Golden accounting tests are the current gate."* — take the eight golden failures next, classify each one **before** fixing it (invalid fixture / incorrect expectation / implementation defect / contract ambiguity), never weaken accounting safeguards to make legacy-generated tests green, and report all eight in a table.
2. *"Implement the approved `BEFORE UPDATE / BEFORE DELETE` trigger architecture."* — make PostgreSQL the final enforcement boundary so posted financial records resist `.save()`, `QuerySet.update()`, bulk operations and raw SQL; prove the failure originates from PostgreSQL and not from Django model validation; add no bypass flag, `force=True`, session variable or escape hatch.
3. *"Proceed to Business Documents."* — only after the golden suite went green.

The standing constraints the user set during these are carried in **Do NOT Do** above.
