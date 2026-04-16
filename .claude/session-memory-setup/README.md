# Session Memory Setup for GnuCash

This directory contains the session memory and statement management setup for the GnuCash project.

## Files

- `memory/` - Initial memory files (copied to `~/.claude/projects/C--Users-Faizel-Noorgat-Documents-Projects-gnucash/memory/`)
- `skills/session-memory/` - Claude Code skill for memory management

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `/session-close` | Save current session state to memory files |
| `/session-summary` | View current session's accumulated context |

### Automatic Behavior

- **Session Start**: Memory index is automatically loaded via hooks in `.claude/settings.local.json`
- **Session End**: Claude prompts to save important context before closing

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| `user` | User preferences, role, working style | `user_role.md` |
| `feedback` | Corrections, validated approaches | `feedback_testing.md` |
| `project` | Ongoing work, decisions, deadlines | `project_overview.md` |
| `reference` | External resources, documentation links | `reference_grafana.md` |

## Memory File Format

```markdown
---
name: {{memory-name}}
description: {{one-line description}}
type: {{user|feedback|project|reference}}
---

{{content}}

**Why:** {{reason this memory exists}}
**How to apply:** {{guidance for future sessions}}
```

## When to Save Memory

- User explicitly asks to "remember X"
- User corrects your approach ("no, don't do that")
- User confirms a non-obvious approach worked
- You learn about ongoing work, deadlines, or stakeholders
- You discover important external resources

## What NOT to Save

- Code patterns (read from codebase)
- Git history (use git commands)
- Ephemeral task details
- Anything already in CLAUDE.md