---
name: session-start
description: Boot the GnuCash session Memory Bank and load unresolved scratchpad items. Use when the user says "initialize", "start session", "new session", "load session", "boot memory", "session start", or runs /session-start.
disable-model-invocation: false
---

# Session Start

Read-only boot of persistent session memory for the GnuCash repository. Initializes the scratchpad if absent; writes nothing else.

## Tracking axes

Two axes, never conflate:

- **Workstream** — which body of work the session serves:
  - `upstream-fix` — a patch intended for `gnucash/gnucash` upstream
  - `modernization` — work under `analysis/` and `modernized/`
  - `fork-local` — personal fork changes not intended upstream
  - `exploration` — reading, prototyping, no deliverable
- **Build state** — whether the tree currently configures, compiles, and passes tests.

Both are recorded in `memory-bank/core/current-state.md`.

## Steps

### 1. Boot the Memory Bank

Read in order:

1. `memory-bank/core/current-state.md`
2. `memory-bank/core/projectbrief.md`
3. `memory-bank/core/productContext.md`
4. `memory-bank/core/techContext.md`
5. `memory-bank/core/systemPatterns.md`
6. `memory-bank/core/NOTES_NEXT_SESSION.md`

**Do NOT read `memory-bank/core/progress.md` on boot.** It is write-only until close; reading it burns context for no benefit.

If any file above is missing — HALT and report the exact path. Do not fabricate its content.

### 2. Load working memory

```bash
python3 .claude/scripts/session_scratchpad.py init
python3 .claude/scripts/session_scratchpad.py validate
python3 .claude/scripts/session_scratchpad.py list
```

`init` is idempotent — an existing scratchpad is left untouched. A missing runtime scratchpad is initialized, not a boot failure.

Classify unresolved items from the `list` output:

- **actionable** — `open` or `in_progress`, with no `blocked_by`
- **blocked** — status `blocked`, or depending on an unresolved blocker
- **pending decisions** — type `decision`, status `pending`

### 3. Verify the working tree

```bash
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git status --short
```

Report branch, HEAD, and whether the tree is dirty. Do not stash, checkout, or clean — this step is observation only.

### 4. Confirm start

```
Memory Bank loaded. Status: <status from current-state.md>.
Workstream: <workstream>. Branch: <branch> @ <sha> (<clean|dirty>).
Build state: <as recorded in current-state.md>.
Scratchpad: <N> unresolved — <A> actionable, <B> blocked, <D> decisions pending.
Ready. Next: <item 1 from NOTES_NEXT_SESSION.md, or "no recorded priority">
```

### 5. Halt conditions

- **Status: BLOCKED** in `current-state.md` — surface the blocker immediately and do no substantive work until the user resolves it.
- **Required boot file missing** — HALT, report the exact path.
- **Scratchpad validation fails** — report the error verbatim. Do not hand-edit the scratchpad to work around it; diagnose the cause first.

### 6. Before non-trivial work

Skim `memory-bank/core/lessons-learned.md` for entries touching the files or subsystems you are about to change.

If `current-state.md` records a build state that predates your changes, say so and plan to re-verify — never treat a stale pass as current.

## What this skill does not do

- Writes no file except initializing an absent scratchpad.
- Does not update `current-state.md` — that happens at close.
- Does not commit, stash, or modify the working tree.

## Related

- `/session-close` — persist state at session end
- `memory-bank/runtime/session-scratchpad.example.json` — scratchpad format
