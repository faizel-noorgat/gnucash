# Lessons Learned

Recurring pitfalls, each with a stable ID. Append during `/session-close` when a session hits something that will bite again. One entry per lesson; if an entry grows past a short paragraph, it is describing a design, not a lesson, and belongs in `docs/decisions/`.

Format:

```
## LL-NNN — <one-line rule>

**Trigger:** what situation surfaces this.
**Symptom:** what you observe when it bites.
**Fix:** what to do instead.
```

---

## LL-001 — A build or test result is only valid for the exact tree state that produced it

**Trigger:** Relying on a recorded build/test pass from an earlier session, or from before uncommitted edits.

**Symptom:** "It built fine last time" while the tree has since changed. Time lost re-deriving why something that should work does not.

**Fix:** Record the tree state (branch, HEAD, dirty/clean) alongside any build result, and re-run before depending on it. Say "not verified this session" rather than carrying a stale pass forward.

---

## LL-002 — A copied test is not a migrated test

**Trigger:** Moving code into a new tree by copying files instead of rewriting imports as you go.

**Symptom:** The new suite passes while proving the *old* code. Stale imports (`accounting_engine.models` in a tree that now uses `apps.accounting.models`) still resolve, because the legacy package directories are still on disk next to the new ones. Nothing errors, so the run looks green and means nothing.

**Fix:** Rewrite imports in the same pass as the copy, and make the legacy tree fail loudly when imported — delete it, rename it, or refuse at import time. Verify what an import actually resolved to before trusting any pass. A red suite is more honest than a green one over the wrong tree.

---

## LL-003 — Fan-out is rate-limited twice: on the model quota and on the permission classifier

**Trigger:** Launching many subagents concurrently, or resuming a large workflow after a quota wall.

**Symptom:** Two distinct signatures. The obvious one is `API Error: Request rejected (429) · usage allocated quota exceeded`, which kills running agents mid-flight and leaves their work half-applied. The quieter one is `the permission classifier is temporarily unavailable (rate-limited), so auto mode cannot determine the safety of <tool>` — the tool never launches at all, so a batch silently comes up short.

**Fix:** Cap concurrency (the user's rule here is three) and record a resume point before every fan-out, so a wall costs a re-run and not a re-derivation. When the classifier is down, read-only tools still work — keep investigating rather than stopping. Never assume a launched batch actually launched; check the completion count.

---

## LL-004 — Claims in artifacts and transcripts disagree; the disk is the tiebreaker

**Trigger:** Quoting a count, verdict, or status from a generated report, a handoff, or a previous session's summary.

**Symptom:** The same fact has several values depending on where you read it. In this repo: rule splits of 47/164/26 versus 47/142/48, golden tests counted as 20 versus 39 on disk, file counts of 1,345 versus 1,801, and two modernization plans that both state they are approved.

**Fix:** Treat every number in a generated artifact as a claim, not a finding. Re-derive it from the tree before repeating it, and say which source a number came from when it matters. When two plans or documents both claim approval, that is a live conflict to surface — not a detail to average over.

---

## LL-005 — A pipeline hides the exit status of whatever is inside it

**Trigger:** `set -e` plus a command piped onward, e.g. `pip install ... | tail -25`, then checking `$?`.

**Symptom:** The pipeline reports success because `$?` is the *last* command's status, not the piped one's. A failed install prints `ERROR: Could not find a version that satisfies the requirement ...` and the script still reports "EXIT: 0". Long stretches spent believing an environment exists when it does not.

**Fix:** Add `set -o pipefail`, or redirect to a file and check the status of the real command. Verify the end state directly (import the package, stat the artefact) rather than trusting a status.

---

## LL-006 — Only *some* undefined names block an import; linting does not tell you which

**Trigger:** Undefined names reported by `ruff --select F821` (or pyflakes) across a module.

**Symptom:** A missing import breaks things in three different ways depending on where the name sits. In a plain function-signature annotation (`def f(x: Decimal) -> Decimal:`) it raises `NameError` at *def* time and kills the whole process — here it took down `django.setup()` for the entire project. In a class-body annotation it raises at class-creation time. In a *string* annotation (`-> "Decimal"`) or inside a method body it is entirely latent and only fails when something calls `typing.get_type_hints()` or invokes the method. Ruff reports all three identically, so a fix-until-clean loop fixes latent ones first and the blocker last.

**Fix:** When an import dies, rank the candidates by where the name appears before fixing anything: signature annotations first, then class bodies, then string annotations and bodies. Fix all of them — a latent one is still a defect — but expect the process-killer to be last.

---

## LL-007 — An application-layer guard is not a boundary

**Trigger:** Assuming a model's `clean()` / `save()` validation protects an invariant.

**Symptom:** `QuerySet.update()`, `bulk_create`, raw SQL, and data-fix scripts all skip `Model.save()` entirely. In this repo a posted-journal immutability guard existed only in `clean()` while the ADR called it "immutability" — and the code's own comment claimed a database trigger that had never been written. Worse, a fixture-built posted entry meant six tests never exercised the guard at all.

**Fix:** Enforce financial and security invariants in the database (`RunSQL` triggers, `CheckConstraint`) and treat the ORM guard as defence in depth. Test the *bypass paths* explicitly, not just the happy path — and note that a guard which cannot be reached, because the fixture can't construct the state that would trigger it, is untested no matter how green the suite is.

---

## LL-008 — A test can pass for the right result and the wrong reason; assert the specific failure

**Trigger:** `assertRaises(Exception)` / `pytest.raises(DatabaseError)` with no message match.

**Symptom:** The test goes green while proving nothing about the mechanism it names. An ORM-delete test here passed because Django's *deletion collector* crashed on a missing unmanaged table — nothing to do with the trigger under test. It then flipped to failing on a later run when the trigger happened to fire first, because the ordering is not stable.

**Fix:** Match the specific message or exception subclass the mechanism produces (`pytest.raises(DatabaseError, match="ADR-010")`). Where two different layers can legitimately refuse and the ordering is not stable, say so in the docstring and widen only deliberately — never leave the reason implicit.

---

## LL-009 — An unconditional skip inside a test body silently disables every assertion below it

**Trigger:** `pytest.xfail(...)` or `pytest.skip(...)` as the first statement of a test.

**Symptom:** The test reports as skipped/xfailed and looks accounted for, while the whole body is dead code. Two tests here carried `pytest.xfail("Accounting engine not yet implemented")` for a whole phase — the engine was by then implemented and green, and removing the call immediately exposed that the service they tested was completely broken. The stale reason string gave no hint.

**Fix:** Grep for in-body `pytest.xfail`/`pytest.skip` when auditing coverage, and tie any such marker to a tracked item with a review date. Prefer a decorator with a matching ID over a body call, so the reason is visible at collection time.

---

## LL-010 — Overriding a framework's setup fixture replaces it entirely, it does not wrap it

**Trigger:** Redefining `django_db_setup` (or any framework-provided fixture) to "adjust" configuration.

**Symptom:** The override supplies only what the author had in mind and silently drops everything else the original did. Here `django_db_setup` was redefined to mutate `settings.DATABASES` and never called the original — which is the fixture that *creates the test database*. Every DB-backed test was unrunnable, and the failure (`relation "auth_group" does not exist`) pointed nowhere near the cause.

**Fix:** Never redefine a framework fixture to tweak a setting; put configuration in settings, where it belongs. If an override is genuinely needed, call the original explicitly and note in its docstring which behaviour is being preserved.

---

## LL-011 — A search index answers confidently about code that no longer exists

**Trigger:** Using an indexed code-search tool (jcodemunch) after the tree has changed since the index was built.

**Symptom:** Nothing in the response says "stale". `search_text` returned a method's *previous* docstring minutes after the file was edited, and `get_file_outline` returned zero symbols for a file that plainly exists — reading like "that file has no symbols" rather than "that file was not indexed". Worst case is a negative: "no callers found" built on a stale index silently under-reports, and a refactor proceeds on a false premise.

**Fix:** Check the index build time (`indexed_at`) against the tree's modification time before trusting any result, and treat a negative from a stale index as no evidence at all. Call `register_edit` with `reindex=true` after editing, and `Read` the file before acting on it. The index is a convenience for finding things, never the authority on what exists.

---

## LL-012 — Two tests in the same tree can encode contradictory contracts

**Trigger:** A test fails on a name or signature mismatch rather than on a behavioural assertion.

**Symptom:** `AdvisorAccessGrant.revoke` was called as `revoke(revoked_by=…)` by the acceptance test and `revoke(revoked_by_user=…)` by the unit test — in the same live tree, with the same split present in the legacy tree it came from, which proves the acceptance test could never have passed there either. Making either test green breaks the other, so "get the suite green" has no local answer and the obvious moves are both wrong.

**Fix:** Treat it as a contract conflict, not a bug, and resolve it against the domain: here, the field the method actually sets (`revoked_by`) settled it. Align the outlier, and say plainly in the commit and the handoff that a test was edited and why — an unexplained test edit is indistinguishable from weakening one. Never resolve this by picking whichever name makes more tests pass, and never by relaxing an assertion.

---

## LL-013 — A leftover test database produces failures that vanish on the next run

**Trigger:** A suite that is otherwise deterministic reports `relation "…" does not exist` or "database already exists", more failures on one run than the next.

**Symptom:** Twenty-seven failures with `ProgrammingError: relation "users" does not exist` on a run whose tests pass individually and pass when re-run as a whole — the failure count moves without a code change. It reads like a test-isolation bug or a real schema problem and is neither.

**Fix:** Before diagnosing, re-run the same command once and compare. If the numbers move, suspect a test database left behind by a previously-aborted run (here `gnucash_test`, dropped by pytest on a clean exit and not on an abort). Do not create the test database by hand to "fix" it — that is what causes this state. Confirm determinism twice before believing any failure count.

---

## LL-014 — A privilege level above the mechanism makes a test of that mechanism vacuous

**Trigger:** Testing a security boundary — row-level security, file permissions, a sandbox — through the connection or user the test suite happens to run as.

**Symptom:** The test passes and proves nothing. PostgreSQL's row-level security is bypassed by **superusers regardless of `FORCE ROW LEVEL SECURITY`**, which exists precisely to defeat the *owner* bypass but does not touch superuser status. Django's test connection here is the `postgres` superuser, so every RLS assertion made through it — `relrowsecurity` true, policies present, rows filtered — would have gone green even with no policy at all. The same shape appears with `BYPASSRLS` roles, `root` against file modes, and container capabilities.

**Fix:** Establish the privilege the mechanism is meant to constrain *before* asserting. Here that is `SET LOCAL ROLE app_user` plus transaction-local GUCs, in a helper every test goes through, so the assertion is made from the position the policy actually governs. Confirm which bypasses exist by experiment against the real system rather than from documentation — the superuser behaviour was verified directly before any test relied on it. And note that setting the mechanism's *input* (here, the tenant context) is only half the job: the connecting role must also be one the mechanism applies to.

---

## LL-015 — A test harness that resets state in a `finally` can invalidate the measurement

**Trigger:** A helper that sets some state, then unconditionally undoes it in a `finally`, used alongside state the caller set up itself.

**Symptom:** Two probe results that were confidently wrong. A query helper reset the role in its `finally`, which silently clobbered a role the caller had set before calling it. Subsequent reads ran as the wrong role and returned results that looked like a policy failure — the opposite of the truth. Nothing errored; the numbers were simply from a different setup than the one believed to be in effect.

**Fix:** Make the harness own the *whole* scope it resets, or reset nothing. Prefer a context manager covering setup and teardown of one coherent scope over a call-scoped `finally` that reaches outside its own frame. When a probe produces a surprising result, re-derive it with the setup inlined and visible before building anything on it — a measurement from an unknown configuration is not a measurement.

---

## LL-016 — A second, unexecuted definition of the same database object is a landmine

**Trigger:** A bootstrap script (`init-db.sql`, a seed file, a hand-run snippet) that defines objects that migrations also define.

**Symptom:** Whichever definition runs is the one that wins, and only one of them ever does. Here `docker/init-db.sql` declared two RLS helper functions as `RETURNS integer` against UUID columns; it was never executed on the development machine (docker is not installed), so the defect sat inert and the functions were absent rather than wrong. Worse, the obvious migration would have **failed** on any deployment that *had* run it: `CREATE OR REPLACE FUNCTION` cannot change a return type, so it raises `cannot change return type of existing function` — breaking upgrades on exactly the machines that most needed fixing.

**Fix:** One definition, in the place that always runs — for schema, the migration graph. Where a bootstrap script must still exist, strip it to what genuinely cannot come from a migration and have it say why. Use `DROP FUNCTION IF EXISTS` before `CREATE` when a stale definition may exist, and verify the upgrade path by seeding the *old* definition into a scratch database and migrating over it, not by testing only the clean-install path.


---

## LL-017 — A policy on a table whose RLS is not enabled does nothing, and nothing says so

**Trigger:** Adding row-level security to existing tables in bulk, especially in a migration that loops over a list.

**Symptom:** `CREATE POLICY` succeeds and the policy appears in `pg_policies`. The table stays completely open. PostgreSQL only consults policies once `relrowsecurity` is set on the table, so `ENABLE ROW LEVEL SECURITY` is a separate, silently-omittable prerequisite — there is no error, no warning, and no catalogue view that reveals the gap unless you deliberately join `pg_class.relrowsecurity`. Here 14 tables received policies in the first draft of a migration and were never enabled; every other assertion in the file still passed, including a test that checked "every tenant-scoped table has a policy".

**Fix:** Treat `ENABLE` + `FORCE` + `CREATE POLICY` as one indivisible unit — a helper function that emits all three, so a policy cannot be created without them. Assert on the **flag**, not on the policy's existence: `SELECT relname FROM pg_class WHERE relrowsecurity AND relforcerowsecurity`. And write a test whose name states the trap (`test_a_policy_alone_does_not_count_as_isolation`), because the failure mode is a test suite that is entirely green over a wide-open table.

---

## LL-018 — "Implemented" is not "ran"; a middleware can look right and never execute

**Trigger:** Code whose effect depends on transaction-scoped state (`SET LOCAL`, temporary tables, cursor state) called from a context that is not inside a transaction.

**Symptom:** `TenantContextMiddleware` set the RLS context in `MiddlewareMixin.process_request`, which Django runs before the view and under autocommit. Every `SET LOCAL` was discarded before the view issued a single query, so the middleware had never done anything at all. Nothing failed: requests succeeded, policies saw `NULL`, and queries returned zero rows — which reads as missing data, not as a broken mechanism. The docstring even warned that callers must be inside `transaction.atomic()`; the middleware was not one of the callers that obeyed it. Confirmed in one command against the real system: `SET LOCAL app.current_tenant_id = 'abc'` alone emits `WARNING: SET LOCAL can only be used in transaction blocks`.

**Fix:** When a mechanism depends on a transaction, the code that sets it must own the transaction — not document the requirement for a caller. Rewrite as new-style middleware (`__init__(get_response)` + `__call__`) wrapping `get_response` in `transaction.atomic()`. Then prove it end to end by asserting *from inside the view*, with the role and context the production path uses; a unit test of the setter would have passed and proved nothing.

---

## LL-019 — Two agents in one working tree is a shared mutable resource, and git will not warn you

**Trigger:** More than one Claude session (or any two writers) running against the same checkout at the same time.

**Symptom:** Two distinct failures, both silent and both misattributed. First, one session ran `git stash push -m <msg>` followed by `git reset --hard HEAD`, discarding ~1600 uncommitted lines from the other; `git status` then read clean, which is precisely what a healthy tree looks like. Second, both sessions' test runs used the hard-coded `gnucash_test` database, so two pytest processes created and dropped the same database under each other — producing `duplicate key ... auth_permission` after a truncated flush, `database "gnucash_test" does not exist` mid-run, and results that flipped between identical invocations. Roughly 90 phantom failures were bisected before the concurrency was noticed, and the code was innocent throughout.

**Fix:** Treat a checkout as single-writer. Before bisecting a mystery failure, check whether another process owns the resource (`ps`, database list, transcript mtimes) before assuming a recent edit is at fault. Give each concurrent run its own test database via a settings module outside the repo rather than editing the committed settings. And `git stash` + `reset` is not a safe "clean up" — check for uncommitted work first; the recovery here worked only because a stash happened to exist, and `git stash apply` (not `pop`) keeps that safety net until the restore is verified.

---

## LL-020 — A child typed more strictly than its parent makes valid parent rows unusable

**Trigger:** Adding a foreign key or constraint to a child table to strengthen an invariant the parent does not itself enforce.

**Symptom:** A passing test broke when `document_extractions` gained a real FK to `tenants`. Its parent, `Document`, stores its tenant as a bare `UUIDField`, so documents can exist against tenant ids that are not rows in `tenants`. The child's stricter FK therefore rejected extractions for documents the database had already accepted — an inconsistency introduced in the name of safety, making some parent rows impossible to attach anything to.

**Fix:** A derived column takes the **shape** of the column it is derived from: a foreign key where the parent has one, a bare value where it does not. Enforce the invariant that actually matters — that the child agrees with its parent — with a composite key `(parent_id, derived) → parent(pk, derived)`, which is exactly as strong as the parent is and no stronger. If the parent's looseness is itself wrong, fix the parent deliberately and in its own change; do not smuggle the fix in through the child.

---

## LL-021 — Grep the template, not the rendered value

**Trigger:** Verifying that generated output (SQL, config, code) contains some specific value, by searching the source for that value as a literal.

**Symptom:** `grep 'TO app_user'` across commit `290cc7e73e` returned **zero** matches, which reads as "the policies were never re-principled and are still `TO PUBLIC`". They were not: `common/rls/migrations/0004_tenant_isolation_closure.py` emits every policy as `TO {APP_ROLE}` from `APP_ROLE = "app_user"`, so the role name is only ever assembled at migration-run time. The grep was answering a different question than the one asked, and its confident zero was indistinguishable from a real absence.

**Fix:** When a search for an expected literal finds nothing, establish whether the value is composed before concluding it is missing — grep the template (`{APP_ROLE}`, `f"..."` interpolations, constants, config lookups) or grep the *effect* (the migration's output, `pg_policies` after a migrate). The same rule covers the inverse: a literal present in source proves only that someone typed it, not that anything runs it (LL-018). Absence of a string is evidence about the string, never about the behaviour.

---

## LL-022 — A cluster-scoped object touched by a per-database migration is touched once per database

**Trigger:** A migration that provisions or re-asserts something whose scope is larger than the database it runs in — a role, a tablespace, a cluster-wide setting — and that is written to be safe to run repeatedly.

**Symptom:** `common/rls/migrations/0001` ended with `ALTER ROLE app_user NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOLOGIN`. The statement is idempotent, so it reads as harmless. Roles are **cluster-scoped**; a migration is not. So it ran once per database, and every freshly migrated database revoked `app_user`'s `LOGIN` across the entire cluster. pytest creates a fresh database per run, so running the test suite locked the running application out of any development or production database on that cluster. Reproduced in three commands: grant `LOGIN`, run `pytest tests/rls/test_rls_provisioning.py`, read `pg_roles` — `rolcanlogin` is `false`. The failure surfaces in a different component from the cause: the application cannot connect, and nothing in the test output mentions a role.

**Fix:** Separate what a migration *must* assert from what the deployment *owns*. Re-assert the safety attributes (here `NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE`) — those must never drift. Do not re-assert anything the deployment is expected to set, because a per-database run will overwrite it cluster-wide. When a provisioning statement is being made "idempotent", ask what its scope is and how often it actually runs; idempotent in value is not idempotent in effect.

---

## LL-023 — A test suite cannot have a different database identity from the one that migrated it

**Trigger:** Wanting end-to-end tests to run as the restricted runtime role, in an environment where migrations need a privileged one.

**Symptom:** Django's test runner creates *and* migrates the test database through the `default` connection, so the role that migrates is the role the tests then run as; there is no seam between them. `test_db_signature()` also excludes `USER`, so a second alias with different credentials is grouped with the first as a mirror rather than giving the tests a second identity. A handoff predicted that splitting the runtime and deploy credentials would make a registration-time constraint testable. It does not. The suite stays green while the endpoint is broken in every environment that enforces the policies — a passing result that is evidence of nothing.

**Fix:** Do not assume a privilege change reaches the tests. Where a test must exercise enforcement, assume the restricted role **inside** the test (`SET LOCAL ROLE app_user` within a transaction), which is equivalent for the duration of the block, and treat "this test does not enter that context" as "this test cannot see this class of defect". Record the gap as an item rather than leaving it as an inference about the suite's coverage.
