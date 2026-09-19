---
name: session-close
description: Persist GnuCash session state to the Memory Bank — reconcile the scratchpad, write the next-session handoff, and archive resolved items. Use when the user says "close session", "session close", "save session", "persist state", "end session", "wrap up", or runs /session-close.
disable-model-invocation: false
---

# Session Close

Persist session state so the next session resumes without re-deriving context. Run the steps in order — later steps depend on earlier ones.

## Steps

### 1. Verified timestamp

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

Use this exact value for every write in this sequence. Never guess it or reuse a timestamp from earlier in the session.

### 2. Reconcile the scratchpad

```bash
python3 .claude/scripts/session_scratchpad.py validate
python3 .claude/scripts/session_scratchpad.py list
```

Compare every unresolved item against final session state:

| Situation | Action |
|---|---|
| Still open, unchanged | leave it |
| Progressed | `update` its `next_action` / `context` |
| Finished | `transition` to `done` with `outcome` |
| Deferred by the user | `update` with the new condition, or `transition` to `cancelled` |
| No longer relevant | `transition` to `obsolete` |
| Superseded | `transition` to `superseded` (decisions only) or `obsolete` |

Add obligations discovered late in the session that are not yet represented. Before adding, check the `list` output for a semantically duplicate active item and update that one instead — the helper rejects duplicate unresolved titles.

**Never edit `memory-bank/runtime/session-scratchpad.json` directly.** Mutations go through the helper, which validates and writes atomically.

Write exactly one operation to `memory-bank/runtime/session-scratchpad-operation.json`, then apply it:

```bash
python3 .claude/scripts/session_scratchpad.py apply \
  --operation-file memory-bank/runtime/session-scratchpad-operation.json
```

Operation shapes:

```json
{
  "operation": "add",
  "item": {
    "type": "task",
    "title": "Verify finance::quote build against new gwenhywfar",
    "context": "Quote module links gwenhywfar; version bumped in the last merge.",
    "why": "Quotes silently fail at runtime if the ABI mismatch is not caught at build time.",
    "next_action": "Reconfigure with cmake -G Ninja -S . -B build and build libgnucash/quotes."
  }
}
```

```json
{ "operation": "update", "id": "T-0001", "changes": { "next_action": "Run ctest -R engine." } }
```

```json
{ "operation": "transition", "id": "T-0001", "status": "done", "outcome": "Engine tests pass on stable @ fb2c773bf6." }
```

The helper deletes the operation file on success. A failed operation leaves live state untouched and the operation file in place for diagnosis. One operation per file.

Item types:

| Type | Prefix | Initial | Statuses |
|---|---|---|---|
| `task` | `T` | `open` | `open`, `in_progress`, `blocked`, `done`, `cancelled`, `obsolete` |
| `question` | `Q` | `open` | `open`, `answered`, `obsolete` |
| `blocker` | `B` | `open` | `open`, `resolved`, `obsolete` |
| `decision` | `D` | `pending` | `pending`, `decided`, `superseded` |
| `follow_up` | `F` | `open` | `open`, `in_progress`, `blocked`, `done`, `cancelled`, `obsolete` |

A resolved status requires `outcome`. A `blocked` item requires `blocked_by`.

### 3. Update `memory-bank/core/current-state.md`

- **Status** — `ACTIVE`, `BLOCKED`, or `IDLE`
- **Last Updated** — verified timestamp
- **Last Session Summary** — 2–4 sentences. What changed, what is proven, what is still unproven.
- **Branch / HEAD** — current branch and short sha
- **Workstream** — `upstream-fix` | `modernization` | `fork-local` | `exploration`
- **Build state** — the last *verified* configure/build/test result, with the command that produced it. If the build was not run this session, say so explicitly. Never carry forward a stale pass as if it were current.
- **Focus** — what this session was about
- **Next** — the single next action
- **Pending Human Action** — things only the user can do: review, sign-off, hardware, credentials, upstream mailing-list replies
- **Known Blockers** — table: ID, item, owner, blocks, status
- **Decisions passed** — append any decision the user made this session, with date and one line of reasoning

### 4. Update `memory-bank/core/NOTES_NEXT_SESSION.md`

Zero-context handoff — the next session may begin with no memory of this one.

- **Written** — verified timestamp
- **Status at Close** — one line
- **Priority Actions** — numbered; #1 must be the exact next action, concrete enough to execute without asking, including the command when there is one
- **Context to Remember** — decisions made, branch state, files touched, anything that would take a fresh reader ten minutes to rediscover
- **Do NOT Do** — explicit rejections and landmines
- **Human's Last Instruction** — verbatim quote or close paraphrase

Source this primarily from unresolved scratchpad items and include their stable IDs (`T-0008`, `B-0001`). Do not present resolved items as pending.

### 5. Update `memory-bank/core/progress.md`

Written only here — this is the one time `progress.md` is touched. Sync **Done**, **Pending**, and **Backlog** against the session outcome.

### 6. Session artifacts

- **Recurring pitfall** → append to `memory-bank/core/lessons-learned.md` as `LL-NNN — <one-line rule>`, followed by the trigger, the symptom, and the fix.
- **Consequential decision** → append to **Decisions passed** in `current-state.md`; record an ADR under `docs/decisions/` when it changes architecture or a public interface.

### 7. Refresh the indexes

The tree is in its final state for the day — index it now so the next session opens against a fresh index instead of paying for a cold walk.

Code (jCodemunch):

```
index_folder { "path": ".", "incremental": true, "use_ai_summaries": true }
embed_repo { "repo": "Gnucash/gnucash" }
```

Docs (jDocMunch):

```
index_local { "path": ".", "incremental": true, "use_ai_summaries": true, "use_embeddings": true }
```

Incremental only. A full re-index (`incremental: false`) is a deliberate act for a cold index or a parser upgrade, never a close-out step. `embed_repo` is separate from `index_folder` — the folder index has no embedding switch, so skipping it leaves new symbols unembedded and semantic search silently degraded.

Report what changed, and flag the number if it is far larger than the session's actual edits. If either run reports low `embedding_coverage`, say so in the handoff rather than leaving the next session to discover it.

### 8. Validate the handoff, then archive

```bash
python3 .claude/scripts/session_scratchpad.py check-handoff \
  --notes memory-bank/core/NOTES_NEXT_SESSION.md
python3 .claude/scripts/session_scratchpad.py archive-resolved \
  --notes memory-bank/core/NOTES_NEXT_SESSION.md
```

`check-handoff` fails if the handoff is missing any unresolved item ID, or still mentions a resolved one. Fix the handoff and re-run — do not skip past it.

`archive-resolved` runs **only after** `check-handoff` passes. It moves resolved items to the archive, retains the newest 100 from the last 30 days, and rolls the session ID. Resolved items still referenced by unresolved items stay in live state.

### 9. Confirm closure

```
[SESSION CLOSED]
Status persisted: <status>
Timestamp: <verified timestamp>
Memory Bank updated: current-state.md, NOTES_NEXT_SESSION.md, progress.md
Scratchpad: <N> unresolved, <M> archived
Indexes: code <symbols> symbols / docs <sections> sections (<what changed>)
Next session priority: <item 1 from NOTES_NEXT_SESSION.md>
```

## What not to save to memory

- Code structure — read it from the tree; use jCodemunch
- Git history — use `git log`
- Build logs, compiler output, test transcripts — link the command instead
- Content that duplicates `docs/decisions/` or upstream documentation
- Credentials, tokens, passwords, private keys, full environment variables

## Related

- `/session-start` — boot sequence
- `memory-bank/core/lessons-learned.md` — recurring pitfalls
- `memory-bank/runtime/session-scratchpad.example.json` — scratchpad format
