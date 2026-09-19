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

