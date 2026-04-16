#!/usr/bin/env python3
"""
Initialize a new skill folder with the correct structure and a SKILL.md template.

Usage:
    python scripts/scaffold_skill.py <skill-name> [--path <output-directory>]

Examples:
    python scripts/scaffold_skill.py sprint-planner
    python scripts/scaffold_skill.py sprint-planner --path /home/claude/my-skills
"""

import argparse
import os
import re
import sys


def validate_name(name: str) -> bool:
    """Validate skill name is kebab-case with no spaces, capitals, or underscores."""
    pattern = r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$'
    if not re.match(pattern, name):
        return False
    if 'claude' in name.lower() or 'anthropic' in name.lower():
        print(f"Error: Skill name cannot contain 'claude' or 'anthropic' (reserved).")
        return False
    return True


def create_skill_folder(name: str, base_path: str) -> str:
    """Create skill folder with correct structure and SKILL.md template."""
    skill_path = os.path.join(base_path, name)

    if os.path.exists(skill_path):
        print(f"Error: Directory already exists: {skill_path}")
        sys.exit(1)

    # Create folder structure
    os.makedirs(skill_path)
    os.makedirs(os.path.join(skill_path, 'scripts'), exist_ok=True)
    os.makedirs(os.path.join(skill_path, 'references'), exist_ok=True)
    os.makedirs(os.path.join(skill_path, 'assets'), exist_ok=True)

    # Create SKILL.md template
    skill_md = f"""---
name: {name}
description: >
  [What this skill does]. Use when user [specific trigger phrases and contexts].
  Also use when user says "[phrase 1]", "[phrase 2]", or "[phrase 3]".
---

# {name.replace('-', ' ').title()}

[Brief description of what this skill does and why it exists.]

## Instructions

### Step 1: [First Major Step]

[Clear explanation of what happens at this step.]

### Step 2: [Next Step]

[Continue with additional steps as needed.]

## Examples

**Example 1: [Common scenario]**

User says: "[realistic user prompt]"

Actions:
1. [First action]
2. [Second action]

Result: [What the user gets]

## Troubleshooting

**Error: [Common error message]**
- Cause: [Why it happens]
- Solution: [How to fix it]
"""

    skill_md_path = os.path.join(skill_path, 'SKILL.md')
    with open(skill_md_path, 'w') as f:
        f.write(skill_md)

    return skill_path


def main():
    parser = argparse.ArgumentParser(description='Scaffold a new skill folder')
    parser.add_argument('name', help='Skill name in kebab-case (e.g., sprint-planner)')
    parser.add_argument('--path', default='.', help='Output directory (default: current)')
    args = parser.parse_args()

    if not validate_name(args.name):
        print(f"Error: '{args.name}' is not valid kebab-case.")
        print("Use lowercase letters, numbers, and hyphens only (e.g., my-cool-skill)")
        sys.exit(1)

    skill_path = create_skill_folder(args.name, args.path)

    print(f"Created skill scaffold at: {skill_path}")
    print(f"  {args.name}/")
    print(f"  ├── SKILL.md          (edit this — it's the core of your skill)")
    print(f"  ├── scripts/          (add executable code here)")
    print(f"  ├── references/       (add documentation loaded as needed)")
    print(f"  └── assets/           (add templates, fonts, icons)")
    print()
    print("Next steps:")
    print("  1. Edit SKILL.md — fill in the description and instructions")
    print("  2. Add reference files, scripts, or assets as needed")
    print("  3. Test with realistic user prompts")


if __name__ == '__main__':
    main()
