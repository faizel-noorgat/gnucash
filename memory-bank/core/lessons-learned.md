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
