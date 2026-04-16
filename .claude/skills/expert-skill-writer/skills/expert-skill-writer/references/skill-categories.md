# Skill Categories

At Anthropic, three common skill use case categories have been observed. Understanding
which category a skill falls into helps you choose the right structure and techniques.

## Category 1: Document and Asset Creation

**Used for:** Creating consistent, high-quality output including documents,
presentations, apps, designs, code, etc.

**Real-world example:** The `frontend-design` skill — "Create distinctive,
production-grade frontend interfaces with high design quality. Use when building web
components, pages, artifacts, posters, or applications."

**Key techniques:**
- Embedded style guides and brand standards
- Template structures for consistent output
- Quality checklists before finalizing
- No external tools required — uses Claude's built-in capabilities

**When to choose this category:** The user wants Claude to produce a specific
deliverable (a file, a design, a document) with consistent quality and formatting
every time. The skill encodes *what good looks like* for that output type.

## Category 2: Workflow Automation

**Used for:** Multi-step processes that benefit from consistent methodology, including
coordination across multiple MCP servers.

**Real-world example:** The `skill-creator` skill — "Interactive guide for creating
new skills. Walks the user through use case definition, frontmatter generation,
instruction writing, and validation."

**Key techniques:**
- Step-by-step workflow with validation gates
- Templates for common structures
- Built-in review and improvement suggestions
- Iterative refinement loops

**When to choose this category:** The user has a repeatable multi-step process that
they want Claude to execute consistently. The value comes from encoding the *sequence
and decision logic*, not just the final output.

## Category 3: MCP Enhancement

**Used for:** Workflow guidance to enhance the tool access an MCP server provides.

**Real-world example:** The `sentry-code-review` skill from Sentry — "Automatically
analyzes and fixes detected bugs in GitHub Pull Requests using Sentry's error
monitoring data via their MCP server."

**Key techniques:**
- Coordinates multiple MCP calls in sequence
- Embeds domain expertise about the service
- Provides context users would otherwise need to specify manually
- Error handling for common MCP issues

**When to choose this category:** The user already has an MCP server connected but
wants Claude to use it *effectively* — following best practices, executing optimal
workflows, and applying domain knowledge automatically.

## The Kitchen Analogy

MCP provides the professional kitchen: access to tools, ingredients, and equipment.
Skills provide the recipes: step-by-step instructions on how to create something
valuable. Together, they enable users to accomplish complex tasks without needing
to figure out every step themselves.

| MCP (Connectivity)                          | Skills (Knowledge)                              |
|---------------------------------------------|------------------------------------------------|
| Connects Claude to your service             | Teaches Claude how to use your service well    |
| Provides real-time data access and tools    | Captures workflows and best practices          |
| What Claude *can* do                        | How Claude *should* do it                      |

## Choosing Between Categories

Most skills lean toward one category. Ask:

- Is the primary output a **deliverable** (document, file, design)? → Category 1
- Is the primary value in **orchestrating steps** consistently? → Category 2
- Does the skill **enhance an existing MCP connection**? → Category 3

Some skills blend categories. A skill that uses MCP tools to generate a formatted
report combines Category 3 (MCP enhancement) with Category 1 (document creation).
That's fine — choose the dominant framing and apply techniques from both.

## Problem-First vs. Tool-First

Two valid approaches for framing your skill:

- **Problem-first:** "I need to set up a project workspace" → The skill orchestrates
  the right MCP calls in the right sequence. Users describe outcomes; the skill
  handles the tools.
- **Tool-first:** "I have Notion MCP connected" → The skill teaches Claude the optimal
  workflows and best practices. Users have access; the skill provides expertise.

Most skills lean one direction. Knowing which framing fits your use case helps you
choose the right workflow pattern.
