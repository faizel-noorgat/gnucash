# expert-skill-writer

A skill that teaches Claude how to write production-quality skills — the folders of instructions that customize Claude for specific tasks and workflows.

Built entirely from [Anthropic's official guide](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en), this skill covers frontmatter craft, progressive disclosure architecture, workflow patterns, validation, and troubleshooting. Install it once and Claude becomes an expert skill author across all your conversations.

## Install

Pick whichever method matches your setup:

### npx skills CLI (Claude Code, Codex, Cursor, 35+ agents)

```bash
npx skills add arch1904/expert-skill-writer
```

### Claude Code — plugin marketplace

```
/plugin marketplace add arch1904/expert-skill-writer
/plugin install expert-skill-writer
```

### Claude Code — manual

Clone this repo and copy the skill folder:

```bash
git clone https://github.com/arch1904/expert-skill-writer.git
cp -r expert-skill-writer/skills/expert-skill-writer ~/.claude/skills/
```

### Claude.ai

1. Download `expert-skill-writer.zip` from the [latest release](https://github.com/arch1904/expert-skill-writer/releases/latest)
2. Go to **Settings → Capabilities → Skills**
3. Click **Upload skill** and select the zip

## What it does

When you ask Claude to write, review, or improve a skill, this skill activates and walks through a structured process:

1. **Understand intent** — clarifies use cases, triggers, expected output, and skill category
2. **Design architecture** — plans folder structure, progressive disclosure levels, composability
3. **Write frontmatter** — crafts the description field (the most important part) with proper trigger phrases
4. **Write instructions** — produces specific, actionable skill content with error handling and examples
5. **Review and validate** — runs through a quality checklist covering structure, content, triggering, and distribution

## What's included

| File | Purpose |
|---|---|
| `SKILL.md` | Core instructions — the skill itself (321 lines) |
| `references/frontmatter-spec.md` | Complete YAML frontmatter specification with good/bad examples |
| `references/skill-categories.md` | Three skill categories with real-world examples and the kitchen analogy |
| `references/workflow-patterns.md` | Five proven workflow patterns (sequential, multi-MCP, iterative, context-aware, domain intelligence) |
| `references/quality-checklist.md` | Pre-upload and post-upload validation checklist |
| `references/troubleshooting.md` | Common issues: undertriggering, overtriggering, MCP failures, instructions not followed |
| `scripts/validate_skill.py` | Programmatic validator — checks naming, frontmatter, structure against the spec |
| `scripts/scaffold_skill.py` | Generates a new skill folder with correct structure |

## Try it

After installing, test with prompts like:

- *"Write a skill that helps Claude generate unit tests for Python projects"*
- *"Review this SKILL.md and suggest improvements"* (paste or upload your skill)
- *"I have a Notion MCP connected — help me build a skill for project setup workflows"*
- *"Turn this conversation into a reusable skill"*

## How it differs from skill-creator

Anthropic's built-in `skill-creator` focuses on eval/benchmark iteration — running test cases, grading outputs, and improving skills through automated loops. This skill focuses on the **writing craft**: producing well-structured, effective skill content that triggers reliably and follows Anthropic's official best practices. They're complementary — use `skill-creator` for iteration, use `expert-skill-writer` for authoring.

## Source

100% based on [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf?hsLang=en) (Anthropic, January 2026). No external sources or invented guidance.

## License

[MIT](LICENSE)
