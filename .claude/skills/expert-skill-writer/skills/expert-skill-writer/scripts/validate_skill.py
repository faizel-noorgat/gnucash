#!/usr/bin/env python3
"""
Validate a skill folder against Anthropic's skill specification.

Checks:
- SKILL.md exists with correct casing
- YAML frontmatter is valid with required fields
- Name is kebab-case
- Description includes trigger phrases
- No README.md in skill folder
- No XML angle brackets in frontmatter
- No reserved names (claude, anthropic)

Usage:
    python scripts/validate_skill.py <path-to-skill-folder>

Examples:
    python scripts/validate_skill.py ./sprint-planner
    python scripts/validate_skill.py /home/claude/my-skill
"""

import argparse
import os
import re
import sys
import yaml


class SkillValidator:
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self.errors = []
        self.warnings = []

    def error(self, msg: str):
        self.errors.append(f"ERROR: {msg}")

    def warn(self, msg: str):
        self.warnings.append(f"WARNING: {msg}")

    def validate(self) -> bool:
        """Run all validation checks. Returns True if no errors."""
        self._check_folder()
        self._check_skill_md()
        self._check_no_readme()
        self._check_folder_name()

        # Print results
        for w in self.warnings:
            print(f"  ⚠️  {w}")
        for e in self.errors:
            print(f"  ❌ {e}")

        if not self.errors:
            print(f"  ✅ Skill validation passed ({len(self.warnings)} warnings)")
            return True
        else:
            print(f"  ❌ Skill validation failed: {len(self.errors)} errors, {len(self.warnings)} warnings")
            return False

    def _check_folder(self):
        if not os.path.isdir(self.path):
            self.error(f"Not a directory: {self.path}")
            return

    def _check_folder_name(self):
        folder_name = os.path.basename(self.path)
        if not re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', folder_name):
            self.error(f"Folder name '{folder_name}' is not valid kebab-case")
        if 'claude' in folder_name.lower() or 'anthropic' in folder_name.lower():
            self.error(f"Folder name cannot contain 'claude' or 'anthropic' (reserved)")

    def _check_no_readme(self):
        readme_path = os.path.join(self.path, 'README.md')
        if os.path.exists(readme_path):
            self.error("README.md found inside skill folder — not allowed. Move docs to SKILL.md or references/")

    def _check_skill_md(self):
        skill_md = os.path.join(self.path, 'SKILL.md')

        # Check exact casing
        if not os.path.exists(skill_md):
            # Check for common misspellings
            for variant in ['skill.md', 'Skill.md', 'SKILL.MD']:
                if os.path.exists(os.path.join(self.path, variant)):
                    self.error(f"Found '{variant}' but must be exactly 'SKILL.md' (case-sensitive)")
                    return
            self.error("SKILL.md not found")
            return

        with open(skill_md, 'r') as f:
            content = f.read()

        # Check frontmatter
        self._check_frontmatter(content)

        # Check body size
        lines = content.split('\n')
        if len(lines) > 500:
            self.warn(f"SKILL.md is {len(lines)} lines — consider moving content to references/ (recommended: under 500 lines)")

        word_count = len(content.split())
        if word_count > 5000:
            self.warn(f"SKILL.md is ~{word_count} words — consider trimming (recommended: under 5,000 words)")

    def _check_frontmatter(self, content: str):
        # Must start with ---
        if not content.startswith('---'):
            self.error("SKILL.md must start with YAML frontmatter (---)")
            return

        # Find closing ---
        parts = content.split('---', 2)
        if len(parts) < 3:
            self.error("YAML frontmatter not properly closed with ---")
            return

        frontmatter_raw = parts[1].strip()

        # Parse YAML
        try:
            fm = yaml.safe_load(frontmatter_raw)
        except yaml.YAMLError as e:
            self.error(f"Invalid YAML in frontmatter: {e}")
            return

        # Check for XML angle brackets in parsed string values (not raw YAML syntax)
        def check_xml_brackets(obj, path=""):
            if isinstance(obj, str):
                if '<' in obj or '>' in obj:
                    self.error(f"XML angle brackets found in frontmatter value at '{path}' — forbidden for security")
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    check_xml_brackets(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_xml_brackets(v, f"{path}[{i}]")
        check_xml_brackets(fm)

        if not isinstance(fm, dict):
            self.error("Frontmatter must be a YAML mapping (key: value pairs)")
            return

        # Check required fields
        if 'name' not in fm:
            self.error("Missing required field: name")
        else:
            name = str(fm['name'])
            if not re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', name):
                self.error(f"name '{name}' is not valid kebab-case")
            if 'claude' in name.lower() or 'anthropic' in name.lower():
                self.error(f"name cannot contain 'claude' or 'anthropic' (reserved)")

        if 'description' not in fm:
            self.error("Missing required field: description")
        else:
            desc = str(fm['description'])
            if len(desc) > 1024:
                self.error(f"description is {len(desc)} chars — must be under 1024")
            if len(desc) < 20:
                self.warn("description seems very short — include WHAT and WHEN")

            # Check for trigger phrases
            trigger_words = ['use when', 'use for', 'use this', 'trigger', 'when user']
            has_trigger = any(tw in desc.lower() for tw in trigger_words)
            if not has_trigger:
                self.warn("description may be missing trigger phrases — include 'Use when...' for reliable triggering")

        # Check optional field constraints
        if 'compatibility' in fm and fm['compatibility'] is not None:
            compat = str(fm['compatibility'])
            if len(compat) > 500:
                self.error(f"compatibility is {len(compat)} chars — must be under 500")

        # Check name matches folder name
        if 'name' in fm:
            folder_name = os.path.basename(self.path)
            skill_name = str(fm['name'])
            if skill_name != folder_name:
                self.warn(f"name '{skill_name}' does not match folder name '{folder_name}' — guide says they should match")


def main():
    parser = argparse.ArgumentParser(description='Validate a skill folder')
    parser.add_argument('path', help='Path to skill folder')
    args = parser.parse_args()

    print(f"Validating skill: {args.path}")
    validator = SkillValidator(args.path)
    success = validator.validate()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
