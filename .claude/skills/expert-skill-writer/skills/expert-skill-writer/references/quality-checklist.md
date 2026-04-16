# Quality Checklist

Use this checklist to validate a skill before and after upload. Run through it every
time you finish writing or revising a skill.

## Before You Start

- [ ] Identified 2-3 concrete use cases with specific triggers, steps, and results
- [ ] Tools identified (built-in capabilities, MCP servers, or both)
- [ ] Reviewed this guide and relevant example skills
- [ ] Planned folder structure (what goes in scripts/, references/, assets/)
- [ ] Determined skill category (Document/Asset Creation, Workflow Automation, MCP Enhancement)

## Structural Validation

- [ ] Folder named in kebab-case (e.g., `sprint-planner`, not `Sprint_Planner`)
- [ ] SKILL.md file exists with exact spelling and casing
- [ ] YAML frontmatter opens and closes with `---` delimiters
- [ ] `name` field is kebab-case, no spaces, no capitals, matches folder name
- [ ] `name` does not contain "claude" or "anthropic" (reserved)
- [ ] `description` is under 1024 characters
- [ ] `description` includes WHAT the skill does AND WHEN to use it
- [ ] `description` includes specific trigger phrases users would actually say
- [ ] No XML angle brackets (`<` `>`) anywhere in frontmatter
- [ ] No README.md inside the skill folder (all docs go in SKILL.md or references/)

## Content Validation

- [ ] Instructions use the imperative form
- [ ] Instructions are specific and actionable (no "validate things properly")
- [ ] Key instructions appear near the top, not buried deep
- [ ] Error handling included for workflow steps
- [ ] Examples provided for common scenarios
- [ ] References clearly linked with guidance on when to read them
- [ ] SKILL.md is under 500 lines / 5,000 words (move excess to references/)
- [ ] Large reference files (over 300 lines) include a table of contents
- [ ] Critical validations use scripts where possible (code is deterministic)
- [ ] Every instruction earns its place — no dead weight

## Writing Quality

- [ ] Explains *why* things matter, not just *what* to do
- [ ] Avoids oppressively rigid ALL-CAPS MUSTs where reasoning would be more effective
- [ ] Generalizes from examples rather than overfitting to specific cases
- [ ] Uses theory of mind — instructions are understandable by an LLM
- [ ] Draft was reviewed with fresh eyes and improved before presenting

## Triggering Validation

- [ ] Would trigger on obvious task requests (direct phrasing)
- [ ] Would trigger on paraphrased requests (indirect phrasing)
- [ ] Would NOT trigger on unrelated topics
- [ ] Description is slightly "pushy" to counteract undertriggering tendency
- [ ] Negative triggers included if overtriggering is a risk

**Debugging tip:** Ask Claude "When would you use the [skill name] skill?" and see
what it quotes back. Adjust the description based on what's missing or misunderstood.

## Before Upload

- [ ] Tested mentally or actually with 2-3 realistic user prompts
- [ ] Skill compressed as .zip if uploading to Claude.ai
- [ ] If distributing via GitHub, repo-level README exists (separate from skill folder)

## After Upload

- [ ] Tested in real conversations
- [ ] Monitored for under-triggering (skill not loading when it should)
- [ ] Monitored for over-triggering (skill loading for unrelated queries)
- [ ] Collected user feedback
- [ ] Iterated on description and instructions based on feedback
- [ ] Updated version in metadata if using versioning

## Success Criteria (Aspirational Targets)

These are rough benchmarks, not precise thresholds:

**Quantitative:**
- Skill triggers on ~90% of relevant queries
- Completes workflow in a reasonable number of tool calls
- Zero failed API calls per workflow execution

**Qualitative:**
- Users don't need to prompt Claude about next steps
- Workflows complete without user correction
- Consistent results across different sessions
- A new user can accomplish the task on first try with minimal guidance
