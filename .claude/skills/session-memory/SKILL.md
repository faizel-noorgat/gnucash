---
name: session-memory
description: Manage persistent session memory and statements. Use '/session-close' to save current session state to memory files, or '/session-summary' to view current session context.
license: MIT
---

This skill manages persistent session memory and statement tracking for the GnuCash project.

## Commands

### /session-close

When the user says "session close" or runs `/session-close`:

1. **Read the current session context** - Review what was discussed, decided, and accomplished
2. **Update memory files** in `~/.claude/projects/C--Users-Faizel-Noorgat-Documents-Projects-gnucash/memory/`:
   - Update `MEMORY.md` index with new entries
   - Create or update memory files for:
     - `user` type: User preferences, role, working style
     - `feedback` type: Corrections, validated approaches, things to avoid
     - `project` type: Ongoing work, decisions, deadlines, stakeholders
     - `reference` type: External resources, links, documentation
3. **Read CLAUDE.md** and ensure any important project context is preserved
4. **Generate session summary** with:
   - Key decisions made
   - Files modified
   - Pending tasks or next steps
   - Any important context for future sessions

### /session-summary

Display the current session's accumulated context:
- Tasks completed
- Files read/modified
- Key decisions
- Open questions or blockers

## Memory File Format

Memory files use this frontmatter:

```markdown
---
name: {{memory name}}
description: {{one-line description}}
type: {{user|feedback|project|reference}}
---

{{content}}

**Why:** {{reason}}
**How to apply:** {{guidance}}
```

## When to Update Memory

- User explicitly asks to remember something
- User corrects your approach ("no, not that", "don't do X")
- User confirms a non-obvious approach worked
- You learn about ongoing work, deadlines, or stakeholders
- You discover important external resources

## Memory Exclusions

Do NOT save to memory:
- Code patterns (read from codebase)
- Git history (use git commands)
- Ephemeral task details
- Anything already in CLAUDE.md