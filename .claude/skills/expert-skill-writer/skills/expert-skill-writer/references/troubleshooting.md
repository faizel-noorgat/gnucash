# Troubleshooting

Common issues and their solutions, extracted from observed patterns in skill
development.

## Skill Won't Upload

**"Could not find SKILL.md in uploaded folder"**
- Cause: File not named exactly `SKILL.md` (case-sensitive)
- Solution: Rename to `SKILL.md`. Verify with `ls -la` — must show exactly `SKILL.md`

**"Invalid frontmatter"**
- Cause: YAML formatting issue
- Common mistakes:
  - Missing `---` delimiters around the frontmatter
  - Unclosed quotes in the description
  - Indentation errors in metadata
- Solution: Ensure frontmatter opens and closes with `---` on their own lines

**"Invalid skill name"**
- Cause: Name has spaces, capitals, or underscores
- Solution: Use kebab-case only (e.g., `my-cool-skill`)

## Skill Doesn't Trigger

**Symptom:** Skill never loads automatically when it should.

**Root cause is almost always the description field.** Quick checklist:
- Is it too generic? ("Helps with projects" will never work)
- Does it include trigger phrases users would actually say?
- Does it mention relevant file types if applicable?
- Is it "pushy" enough? Claude tends to undertrigger, so be explicit about when to use it

**Debugging approach:** Ask Claude "When would you use the [skill name] skill?"
Claude will quote the description back. What's missing from that response tells you
what to add.

**Fix:** Revise the description to include more specific trigger conditions and
phrases.

## Skill Triggers Too Often

**Symptom:** Skill loads for unrelated queries.

**Solutions (in order of preference):**

1. Add negative triggers:
```yaml
description: >
  Advanced data analysis for CSV files. Use for statistical modeling,
  regression, clustering. Do NOT use for simple data exploration
  (use data-viz skill instead).
```

2. Be more specific:
```yaml
# Too broad
description: Processes documents

# More specific
description: Processes PDF legal documents for contract review
```

3. Clarify scope explicitly:
```yaml
description: >
  PayFlow payment processing for e-commerce. Use specifically for
  online payment workflows, not for general financial queries.
```

## MCP Connection Issues

**Symptom:** Skill loads but MCP calls fail.

**Checklist:**
1. Verify MCP server is connected — Claude.ai: Settings > Extensions > [Your Service],
   should show "Connected" status
2. Check authentication — API keys valid and not expired, proper permissions/scopes
   granted, OAuth tokens refreshed
3. Test MCP independently — ask Claude to call MCP directly without the skill:
   "Use [Service] MCP to fetch my projects." If this fails, the issue is MCP, not the skill
4. Verify tool names — skill references the correct MCP tool names (case-sensitive)

## Instructions Not Followed

**Symptom:** Skill loads but Claude doesn't follow the instructions.

**Common causes and fixes:**

**1. Instructions too verbose**
- Keep instructions concise
- Use bullet points and numbered lists for steps
- Move detailed reference material to separate files in `references/`

**2. Instructions buried**
- Put critical instructions at the top of the SKILL.md body
- Use clear headers (`## Important`, `## Critical`)
- Repeat key points if they're essential

**3. Ambiguous language**
```markdown
# Bad
Make sure to validate things properly

# Good
CRITICAL: Before calling create_project, verify:
- Project name is non-empty
- At least one team member assigned
- Start date is not in the past
```

**4. Model "laziness" on long tasks**
Add explicit encouragement (note: this is more effective in user prompts than in
SKILL.md, but can help in the skill too):
```markdown
# Performance Notes
- Take your time to do this thoroughly
- Quality is more important than speed
- Do not skip validation steps
```

**5. Critical validations not enforced**
For checks that absolutely must happen, bundle a script rather than relying on
language instructions. Code is deterministic; language interpretation is not.

## Large Context Issues

**Symptom:** Skill seems slow or responses are degraded.

**Causes:**
- Skill content too large (SKILL.md over 5,000 words)
- Too many skills enabled simultaneously (more than 20-50)
- All content loaded inline instead of using progressive disclosure

**Solutions:**

1. Optimize SKILL.md size — move detailed docs to `references/`, link to them instead
   of inlining, keep SKILL.md under 5,000 words
2. Reduce enabled skills — if more than 20-50 skills are active, recommend selective
   enablement or consider skill "packs" for related capabilities
3. Use progressive disclosure properly — frontmatter for triggering, SKILL.md body
   for core instructions, linked files for everything else

## Iteration Signals

**Undertriggering signals** (skill not used enough):
- Skill doesn't load when it should
- Users manually enabling it
- Support questions about when to use it
- Fix: Add more detail and nuance to the description — this may include keywords
  particularly for technical terms that users might use

**Overtriggering signals** (skill used too much):
- Skill loads for irrelevant queries
- Users disabling it
- Confusion about purpose
- Fix: Add negative triggers, be more specific in description

**Execution issues** (skill loads but performs poorly):
- Inconsistent results across sessions
- API call failures
- Users correcting Claude mid-workflow
- Fix: Improve instructions, add error handling, use validation scripts
