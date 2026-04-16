# YAML Frontmatter Specification

The YAML frontmatter is the most important part of any skill. It determines whether
Claude ever loads your skill at all. This is Level 1 of progressive disclosure — it
is always present in Claude's system prompt.

## Required Fields

```yaml
---
name: skill-name-in-kebab-case
description: What it does and when to use it. Include specific trigger phrases.
---
```

Both `name` and `description` are required. Everything else is optional.

## Field Details

### name (required)

- Must be kebab-case: `notion-project-setup`
- No spaces: `Notion Project Setup` is invalid
- No underscores: `notion_project_setup` is invalid
- No capitals: `NotionProjectSetup` is invalid
- Should match the folder name
- Cannot contain "claude" or "anthropic" (reserved by Anthropic)

### description (required)

This is the primary triggering mechanism. Structure it as:

`[What it does] + [When to use it] + [Key capabilities]`

Rules:
- MUST include BOTH what the skill does AND when to use it
- Under 1024 characters
- No XML angle brackets (security restriction — frontmatter appears in system prompt)
- Include specific phrases users would actually say
- Mention relevant file types if applicable

Claude has a tendency to *undertrigger* skills — to not use them when they would be
useful. To combat this, make descriptions slightly "pushy." Instead of just stating
what the skill does, explicitly say "Use when..." and list trigger contexts generously.

**Good descriptions:**

```yaml
# Specific and actionable
description: >
  Analyzes Figma design files and generates developer handoff documentation.
  Use when user uploads .fig files, asks for "design specs", "component
  documentation", or "design-to-code handoff".

# Includes trigger phrases
description: >
  Manages Linear project workflows including sprint planning, task creation,
  and status tracking. Use when user mentions "sprint", "Linear tasks",
  "project planning", or asks to "create tickets".

# Clear value proposition
description: >
  End-to-end customer onboarding workflow for PayFlow. Handles account creation,
  payment setup, and subscription management. Use when user says "onboard new
  customer", "set up subscription", or "create PayFlow account".
```

**Bad descriptions:**

```yaml
# Too vague — Claude can't determine when to trigger
description: Helps with projects.

# Missing triggers — no signal about when to use it
description: Creates sophisticated multi-page documentation systems.

# Too technical, no user triggers — no real user would say this
description: Implements the Project entity model with hierarchical relationships.
```

### license (optional)

Use if making the skill open source. Common values: `MIT`, `Apache-2.0`.

### compatibility (optional)

1-500 characters. Indicates environment requirements: intended product, required
system packages, network access needs, etc.

### allowed-tools (optional)

Restrict which tools the skill can access:
```yaml
allowed-tools: "Bash(python:*) Bash(npm:*) WebFetch"
```

### metadata (optional)

Any custom key-value pairs. Suggested fields:
```yaml
metadata:
  author: Company Name
  version: 1.0.0
  mcp-server: server-name
  category: productivity
  tags: [project-management, automation]
  documentation: https://example.com/docs
  support: support@example.com
```

## Security Restrictions

**Forbidden in frontmatter:**
- XML angle brackets (`<` `>`) — because frontmatter appears in Claude's system
  prompt, malicious content could inject instructions
- Code execution in YAML — safe YAML parsing is used, so attempts to execute code
  via YAML constructs will not work
- Skills named with "claude" or "anthropic" prefix (reserved)

**Allowed:**
- Any standard YAML types (strings, numbers, booleans, lists, objects)
- Custom metadata fields
- Long descriptions (up to 1024 characters)

## Complete Example with All Optional Fields

```yaml
---
name: payflow-onboarding
description: >
  End-to-end customer onboarding for PayFlow. Handles account creation,
  payment method setup, and subscription management via MCP. Use when
  user says "onboard new customer", "set up subscription", "create PayFlow
  account", or references new customer workflows.
license: MIT
compatibility: Requires PayFlow MCP server connected via Settings > Extensions
metadata:
  author: PayFlow Inc
  version: 2.1.0
  mcp-server: payflow
  category: onboarding
  tags: [payments, subscriptions, customer-setup]
---
```

## Debugging Frontmatter Issues

**"Could not find SKILL.md in uploaded folder"** — File not named exactly `SKILL.md`
(case-sensitive). Verify with `ls -la`.

**"Invalid frontmatter"** — YAML formatting issue. Common mistakes:
```yaml
# Wrong — missing delimiters
name: my-skill
description: Does things

# Wrong — unclosed quotes
name: my-skill
description: "Does things

# Correct
---
name: my-skill
description: Does things
---
```

**"Invalid skill name"** — Name has spaces or capitals. Use kebab-case only.

**Skill doesn't trigger** — Revise your description. Ask Claude: "When would you use
the [skill name] skill?" to see what it understands from the description. Adjust based
on what's missing.

**Skill triggers too often** — Add negative triggers or be more specific:
```yaml
description: >
  Advanced data analysis for CSV files. Use for statistical modeling,
  regression, clustering. Do NOT use for simple data exploration
  (use data-viz skill instead).
```
