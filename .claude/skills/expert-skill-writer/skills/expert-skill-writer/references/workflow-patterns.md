# Workflow Patterns

These patterns emerged from skills created by early adopters and internal teams at
Anthropic. They represent common approaches that work well, not prescriptive templates.
Choose the pattern that fits your use case, or combine patterns as needed.

## Pattern 1: Sequential Workflow Orchestration

**Use when:** Users need multi-step processes executed in a specific order.

```markdown
# Workflow: Onboard New Customer

# Step 1: Create Account
Call MCP tool: `create_customer`
Parameters: name, email, company

# Step 2: Setup Payment
Call MCP tool: `setup_payment_method`
Wait for: payment method verification

# Step 3: Create Subscription
Call MCP tool: `create_subscription`
Parameters: plan_id, customer_id (from Step 1)

# Step 4: Send Welcome Email
Call MCP tool: `send_email`
Template: welcome_email_template
```

**Key techniques:**
- Explicit step ordering
- Dependencies between steps (Step 3 needs output from Step 1)
- Validation at each stage
- Rollback instructions for failures

## Pattern 2: Multi-MCP Coordination

**Use when:** Workflows span multiple services.

```markdown
# Design-to-Development Handoff

# Phase 1: Design Export (Figma MCP)
1. Export design assets from Figma
2. Generate design specifications
3. Create asset manifest

# Phase 2: Asset Storage (Drive MCP)
1. Create project folder in Drive
2. Upload all assets
3. Generate shareable links

# Phase 3: Task Creation (Linear MCP)
1. Create development tasks
2. Attach asset links to tasks
3. Assign to engineering team

# Phase 4: Notification (Slack MCP)
1. Post handoff summary to #engineering
2. Include asset links and task references
```

**Key techniques:**
- Clear phase separation between services
- Data passing between MCPs (links from Phase 2 used in Phase 3)
- Validation before moving to next phase
- Centralized error handling

## Pattern 3: Iterative Refinement

**Use when:** Output quality improves with iteration.

```markdown
# Iterative Report Creation

# Initial Draft
1. Fetch data via MCP
2. Generate first draft report
3. Save to temporary file

# Quality Check
1. Run validation script: `scripts/check_report.py`
2. Identify issues:
   - Missing sections
   - Inconsistent formatting
   - Data validation errors

# Refinement Loop
1. Address each identified issue
2. Regenerate affected sections
3. Re-validate
4. Repeat until quality threshold met

# Finalization
1. Apply final formatting
2. Generate summary
3. Save final version
```

**Key techniques:**
- Explicit quality criteria defined upfront
- Iterative improvement with clear checks
- Validation scripts for deterministic checks
- Clear stopping conditions (know when to stop iterating)

## Pattern 4: Context-Aware Tool Selection

**Use when:** The same outcome requires different tools depending on context.

```markdown
# Smart File Storage

# Decision Tree
1. Check file type and size
2. Determine best storage location:
   - Large files (>10MB): Use cloud storage MCP
   - Collaborative docs: Use Notion/Docs MCP
   - Code files: Use GitHub MCP
   - Temporary files: Use local storage

# Execute Storage
Based on decision:
- Call appropriate MCP tool
- Apply service-specific metadata
- Generate access link

# Provide Context to User
Explain why that storage was chosen
```

**Key techniques:**
- Clear decision criteria with concrete thresholds
- Fallback options when primary path fails
- Transparency about choices (tell the user why)

## Pattern 5: Domain-Specific Intelligence

**Use when:** The skill adds specialized knowledge beyond tool access.

```markdown
# Payment Processing with Compliance

# Before Processing (Compliance Check)
1. Fetch transaction details via MCP
2. Apply compliance rules:
   - Check sanctions lists
   - Verify jurisdiction allowances
   - Assess risk level
3. Document compliance decision

# Processing
IF compliance passed:
  - Call payment processing MCP tool
  - Apply appropriate fraud checks
  - Process transaction
ELSE:
  - Flag for review
  - Create compliance case

# Audit Trail
- Log all compliance checks
- Record processing decisions
- Generate audit report
```

**Key techniques:**
- Domain expertise embedded directly in the skill logic
- Compliance/safety checks *before* action (not after)
- Comprehensive documentation of decisions
- Clear governance and audit trails

## Choosing a Pattern

| If your skill needs...                     | Use Pattern               |
|--------------------------------------------|---------------------------|
| Steps in a fixed order                     | 1: Sequential             |
| Coordination across services               | 2: Multi-MCP              |
| Quality that improves with passes          | 3: Iterative Refinement   |
| Different tools for different contexts     | 4: Context-Aware          |
| Specialized knowledge baked in             | 5: Domain Intelligence    |

Many real skills combine patterns. A sprint planning skill might use Sequential
Orchestration (Pattern 1) with Domain-Specific Intelligence (Pattern 5) for
capacity analysis. A report generator might combine Multi-MCP Coordination
(Pattern 2) with Iterative Refinement (Pattern 3). Start with the dominant pattern
and layer in others as the complexity demands.
