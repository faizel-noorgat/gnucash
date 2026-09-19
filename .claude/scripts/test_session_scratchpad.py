"""Contract tests for the session scratchpad tooling and its Claude Code skills.

Run from the repository root:

    python3 .claude/scripts/test_session_scratchpad.py -v

or

    python3 -m unittest discover -s .claude/scripts -p "test_*.py" -v

Ported from the py-hoarder-v2 pytest suite at tests/cursor/test_session_scratchpad.py.
Deliberately uses only the standard library so it adds no dependency to the tree.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / ".claude/scripts/session_scratchpad.py"
RUNTIME_DIR = REPO_ROOT / "memory-bank/runtime"
CORE_DIR = REPO_ROOT / "memory-bank/core"
START_SKILL = REPO_ROOT / ".claude/skills/session-start/SKILL.md"
CLOSE_SKILL = REPO_ROOT / ".claude/skills/session-close/SKILL.md"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("session_scratchpad", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load session scratchpad module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scratchpad = load_module()


def item_payload(
    item_type: str = "task",
    title: str = "Verify session handoff",
) -> dict[str, Any]:
    return {
        "type": item_type,
        "title": title,
        "context": "Session created work that must survive context rollover.",
        "why": "Next agent needs enough context to continue safely.",
        "next_action": "Complete verification and record outcome.",
    }


def frontmatter(text: str) -> dict[str, str]:
    """Parse the flat key: value frontmatter block without a YAML dependency."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("SKILL.md must open with a --- frontmatter marker")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    raise AssertionError("SKILL.md frontmatter is not terminated")


class ScratchpadTestCase(unittest.TestCase):
    """Base case giving each test a scratchpad inside the repo-confined runtime dir.

    The scratchpad lives under memory-bank/runtime because ``safe_path`` confines all
    tooling paths to the repository root, so an OS temp directory would be rejected.
    """

    def setUp(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._tempdir = tempfile.TemporaryDirectory(prefix=".scratchpad-test-", dir=RUNTIME_DIR)
        self.workspace = Path(self._tempdir.name)
        self.path = self.workspace / "scratchpad.json"
        scratchpad.atomic_write_json(self.path, scratchpad.empty_document("2026-09-04T00:00:00Z"))

    def tearDown(self) -> None:
        self._tempdir.cleanup()

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        return scratchpad.mutate_document(
            self.path,
            lambda document, now: scratchpad.add_item(document, payload, now),
        )

    def update(self, item_id: str, changes: dict[str, Any]) -> dict[str, Any]:
        return scratchpad.mutate_document(
            self.path,
            lambda document, now: scratchpad.update_item(document, item_id, changes, now),
        )

    def transition(
        self,
        item_id: str,
        status: str,
        outcome: str | None = None,
    ) -> dict[str, Any]:
        return scratchpad.mutate_document(
            self.path,
            lambda document, now: scratchpad.transition_item(
                document,
                item_id,
                {"status": status, "outcome": outcome},
                now,
            ),
        )


class DocumentShapeTests(ScratchpadTestCase):
    def test_empty_document_matches_versioned_example(self) -> None:
        document = scratchpad.empty_document("2026-09-04T00:00:00Z")
        example = json.loads(
            (RUNTIME_DIR / "session-scratchpad.example.json").read_text(encoding="utf-8")
        )

        scratchpad.validate_document(document)
        scratchpad.validate_document(example)

        self.assertEqual(document["version"], 1)
        self.assertEqual(document["session"]["id"], "2026-09-04T00:00:00Z")
        self.assertEqual(document["items"], [])
        self.assertEqual(
            set(document["next_ids"]),
            {"task", "question", "blocker", "decision", "follow_up"},
        )

    def test_paths_outside_repository_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(scratchpad.ScratchpadError, "inside repository"):
                scratchpad.safe_path(Path(outside) / "outside.json")


class AddItemTests(ScratchpadTestCase):
    def test_add_allocates_type_specific_stable_ids(self) -> None:
        cases = [
            ("task", "T-0001", "open"),
            ("question", "Q-0001", "open"),
            ("blocker", "B-0001", "open"),
            ("decision", "D-0001", "pending"),
            ("follow_up", "F-0001", "open"),
        ]
        for item_type, expected_id, expected_status in cases:
            with self.subTest(item_type=item_type):
                item = self.add(item_payload(item_type, title=f"Item for {item_type}"))
                self.assertEqual(item["id"], expected_id)
                self.assertEqual(item["status"], expected_status)
                scratchpad.validate_document(scratchpad.load_document(self.path))

    def test_invalid_add_preserves_previous_file(self) -> None:
        before = self.path.read_text(encoding="utf-8")
        payload = item_payload()
        payload["why"] = ""

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "why must be non-empty"):
            self.add(payload)

        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_unknown_item_field_is_rejected(self) -> None:
        payload = item_payload()
        payload["unexpected"] = "typo"

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "Unknown item field"):
            self.add(payload)

    def test_normalized_active_duplicate_is_rejected(self) -> None:
        self.add(item_payload(title="Verify session handoff"))

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "Duplicate unresolved title"):
            self.add(item_payload(title=" VERIFY_session---handoff "))


class UpdateItemTests(ScratchpadTestCase):
    def test_update_changes_one_item_without_losing_another(self) -> None:
        first = self.add(item_payload(title="First task"))
        second = self.add(item_payload(title="Second task"))

        updated = self.update(first["id"], {"next_action": "Run targeted tests."})
        document = scratchpad.load_document(self.path)

        self.assertEqual(updated["next_action"], "Run targeted tests.")
        self.assertEqual(scratchpad.find_item(document, second["id"])["title"], "Second task")

    def test_status_must_change_through_transition_command(self) -> None:
        item = self.add(item_payload())

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "transition command"):
            self.update(item["id"], {"status": "done"})

    def test_resolved_transition_requires_outcome(self) -> None:
        item = self.add(item_payload())

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "requires outcome"):
            self.transition(item["id"], "done", None)

    def test_blocked_status_requires_reference(self) -> None:
        item = self.add(item_payload())

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "requires blocked_by"):
            self.transition(item["id"], "blocked", None)

    def test_resolve_and_reopen_preserves_resolution_history(self) -> None:
        item = self.add(item_payload())
        resolved = self.transition(item["id"], "done", "All checks passed.")
        reopened = self.transition(item["id"], "open", None)

        self.assertTrue(resolved["resolved_at"])
        self.assertEqual(reopened["status"], "open")
        self.assertEqual(reopened["history"][0]["outcome"], "All checks passed.")
        self.assertNotIn("resolved_at", reopened)


class DependencyTests(ScratchpadTestCase):
    def test_self_and_cyclic_dependencies_are_rejected(self) -> None:
        first = self.add(item_payload(title="First task"))
        second_payload = item_payload(title="Second task")
        second_payload["depends_on"] = [first["id"]]
        second = self.add(second_payload)

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "cannot reference itself"):
            self.update(first["id"], {"depends_on": [first["id"]]})

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "Dependency cycle"):
            self.update(first["id"], {"depends_on": [second["id"]]})

    def test_missing_dependency_is_rejected(self) -> None:
        payload = item_payload(title="Missing dependency")
        payload["depends_on"] = ["T-9999"]

        with self.assertRaisesRegex(scratchpad.ScratchpadError, "Missing referenced item"):
            self.add(payload)


class AtomicWriteTests(ScratchpadTestCase):
    def test_atomic_replace_failure_preserves_existing_file(self) -> None:
        before = self.path.read_text(encoding="utf-8")

        with mock.patch.object(
            scratchpad.os,
            "replace",
            side_effect=OSError("simulated replace failure"),
        ):
            with self.assertRaisesRegex(OSError, "simulated replace failure"):
                scratchpad.atomic_write_json(
                    self.path,
                    scratchpad.empty_document("2026-09-04T01:00:00Z"),
                )

        self.assertEqual(self.path.read_text(encoding="utf-8"), before)


class HandoffTests(ScratchpadTestCase):
    def test_handoff_requires_active_ids_and_excludes_resolved_ids(self) -> None:
        active = self.add(item_payload(title="Active task"))
        resolved = self.add(item_payload(title="Resolved task"))
        self.transition(resolved["id"], "done", "Finished.")
        notes = self.workspace / "notes.md"

        notes.write_text(
            f"Resume {active['id']} then review {resolved['id']}.",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(scratchpad.ScratchpadError, "still contains resolved"):
            scratchpad.check_handoff(scratchpad.load_document(self.path), notes)

        notes.write_text("No item IDs yet.", encoding="utf-8")
        with self.assertRaisesRegex(scratchpad.ScratchpadError, "missing unresolved"):
            scratchpad.check_handoff(scratchpad.load_document(self.path), notes)

        notes.write_text(f"Resume {active['id']}.", encoding="utf-8")
        scratchpad.check_handoff(scratchpad.load_document(self.path), notes)


class ArchiveTests(ScratchpadTestCase):
    def test_archive_retains_resolved_item_needed_by_pending_decision(self) -> None:
        resolved = self.add(item_payload(title="Resolved task"))
        decision_payload = item_payload("decision", "Pending decision")
        decision_payload["depends_on"] = [resolved["id"]]
        pending = self.add(decision_payload)
        self.transition(resolved["id"], "done", "Finished.")
        archive = self.workspace / "archive.jsonl"

        count = scratchpad.mutate_document(
            self.path,
            lambda document, now: scratchpad.archive_resolved(document, archive, now),
        )
        document = scratchpad.load_document(self.path)
        archived_record = json.loads(archive.read_text(encoding="utf-8"))

        self.assertEqual(count, 1)
        self.assertEqual(
            [item["id"] for item in document["items"]],
            [resolved["id"], pending["id"]],
        )
        self.assertEqual(archived_record["item"]["id"], resolved["id"])
        self.assertNotEqual(document["session"]["id"], "2026-09-04T00:00:00Z")


class CliTests(ScratchpadTestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *arguments],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_initializes_and_validates_local_file(self) -> None:
        path = self.workspace / "cli-scratchpad.json"

        initialized = self.run_cli("--file", str(path), "init")
        validated = self.run_cli("--file", str(path), "validate")

        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertEqual(validated.returncode, 0, validated.stderr)
        self.assertEqual(json.loads(validated.stdout)["status"], "valid")

    def test_cli_applies_operation_file_then_removes_it(self) -> None:
        path = self.workspace / "cli-scratchpad.json"
        operation_path = self.workspace / "operation.json"
        self.run_cli("--file", str(path), "init")
        operation_path.write_text(
            json.dumps({"operation": "add", "item": item_payload()}),
            encoding="utf-8",
        )

        result = self.run_cli(
            "--file",
            str(path),
            "apply",
            "--operation-file",
            str(operation_path),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["id"], "T-0001")
        self.assertFalse(operation_path.exists())
        self.assertEqual(
            scratchpad.load_document(path)["items"][0]["title"],
            "Verify session handoff",
        )

    def test_cli_failure_leaves_operation_file_for_diagnosis(self) -> None:
        path = self.workspace / "cli-scratchpad.json"
        self.run_cli("--file", str(path), "init")
        operation_path = self.workspace / "bad-operation.json"
        operation_path.write_text(
            json.dumps({"operation": "transition", "id": "T-0001", "status": "done"}),
            encoding="utf-8",
        )

        result = self.run_cli(
            "--file",
            str(path),
            "apply",
            "--operation-file",
            str(operation_path),
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown item ID", result.stderr)
        self.assertTrue(operation_path.exists())


class SkillContractTests(unittest.TestCase):
    """The ported skills must carry the same lifecycle contract as the source."""

    def test_skills_declare_expected_frontmatter(self) -> None:
        for skill_path, expected_name in (
            (START_SKILL, "session-start"),
            (CLOSE_SKILL, "session-close"),
        ):
            with self.subTest(skill=expected_name):
                fields = frontmatter(skill_path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("name"), expected_name)
                self.assertTrue(fields.get("description"), "description is required")
                self.assertEqual(fields.get("disable-model-invocation"), "false")

    def test_start_skill_loads_scratchpad_and_skips_progress(self) -> None:
        skill = START_SKILL.read_text(encoding="utf-8")

        self.assertIn("memory-bank/core/current-state.md", skill)
        self.assertIn("memory-bank/core/NOTES_NEXT_SESSION.md", skill)
        self.assertIn("**Do NOT read `memory-bank/core/progress.md` on boot.**", skill)
        self.assertIn("session_scratchpad.py init", skill)
        self.assertIn("session_scratchpad.py validate", skill)
        self.assertIn("session_scratchpad.py list", skill)

    def test_start_skill_boot_list_omits_progress(self) -> None:
        skill = START_SKILL.read_text(encoding="utf-8")
        boot_list = skill.split("### 1. Boot the Memory Bank")[1].split("### 2.")[0]
        numbered = [line for line in boot_list.splitlines() if line[:1].isdigit()]

        self.assertEqual(len(numbered), 6, "boot sequence should list six files")
        self.assertFalse(
            [line for line in numbered if "progress.md" in line],
            "progress.md must not appear in the boot sequence",
        )

    def test_close_skill_reconciles_before_compiling_handoff(self) -> None:
        skill = CLOSE_SKILL.read_text(encoding="utf-8")

        reconcile_position = skill.index("### 2. Reconcile the scratchpad")
        handoff_position = skill.index(
            "### 4. Update `memory-bank/core/NOTES_NEXT_SESSION.md`"
        )

        self.assertLess(reconcile_position, handoff_position)
        self.assertIn("session_scratchpad.py check-handoff", skill)
        self.assertIn("session_scratchpad.py archive-resolved", skill)

    def test_close_skill_checks_handoff_before_archiving(self) -> None:
        skill = CLOSE_SKILL.read_text(encoding="utf-8")

        check_position = skill.index("check-handoff \\")
        archive_position = skill.index("archive-resolved \\")

        self.assertLess(check_position, archive_position)

    def test_close_skill_forbids_direct_scratchpad_edits(self) -> None:
        skill = CLOSE_SKILL.read_text(encoding="utf-8")

        self.assertIn("Never edit `memory-bank/runtime/session-scratchpad.json` directly", skill)


class MemoryBankTests(unittest.TestCase):
    def test_core_files_define_the_memory_layers(self) -> None:
        for name in (
            "current-state.md",
            "projectbrief.md",
            "productContext.md",
            "techContext.md",
            "systemPatterns.md",
            "NOTES_NEXT_SESSION.md",
            "progress.md",
            "lessons-learned.md",
        ):
            with self.subTest(file=name):
                self.assertTrue((CORE_DIR / name).exists(), f"missing {name}")

    def test_current_state_tracks_workstream_and_build_state(self) -> None:
        state = (CORE_DIR / "current-state.md").read_text(encoding="utf-8")

        self.assertIn("**Workstream:**", state)
        self.assertIn("**Build state:**", state)
        self.assertIn("**Branch / HEAD:**", state)

    def test_example_scratchpad_is_tracked_and_valid(self) -> None:
        example = json.loads(
            (RUNTIME_DIR / "session-scratchpad.example.json").read_text(encoding="utf-8")
        )

        scratchpad.validate_document(example)


if __name__ == "__main__":
    unittest.main()
