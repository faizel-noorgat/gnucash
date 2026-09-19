"""Manage repository-local prospective memory through validated mutations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = REPO_ROOT / "memory-bank/runtime/session-scratchpad.json"
DEFAULT_ARCHIVE = REPO_ROOT / "memory-bank/runtime/session-scratchpad-archive.jsonl"
SCHEMA_VERSION = 1

TYPE_RULES = {
    "task": {"prefix": "T", "initial": "open", "statuses": {"open", "in_progress", "blocked", "done", "cancelled", "obsolete"}, "resolved": {"done", "cancelled", "obsolete"}},
    "question": {"prefix": "Q", "initial": "open", "statuses": {"open", "answered", "obsolete"}, "resolved": {"answered", "obsolete"}},
    "blocker": {"prefix": "B", "initial": "open", "statuses": {"open", "resolved", "obsolete"}, "resolved": {"resolved", "obsolete"}},
    "decision": {"prefix": "D", "initial": "pending", "statuses": {"pending", "decided", "superseded"}, "resolved": {"decided", "superseded"}},
    "follow_up": {"prefix": "F", "initial": "open", "statuses": {"open", "in_progress", "blocked", "done", "cancelled", "obsolete"}, "resolved": {"done", "cancelled", "obsolete"}},
}
REQUIRED_TEXT_FIELDS = ("title", "context", "why", "next_action")
IMMUTABLE_FIELDS = {"id", "type", "created_at"}
OPTIONAL_LIST_FIELDS = {"depends_on", "blocked_by", "decision_criteria"}
ITEM_FIELDS = set(REQUIRED_TEXT_FIELDS) | OPTIONAL_LIST_FIELDS | {
    "id", "type", "status", "created_at", "updated_at", "current_preference", "outcome",
    "resolved_at", "source", "history",
}


class ScratchpadError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_document(now: str | None = None) -> dict[str, Any]:
    timestamp = now or utc_now()
    return {
        "version": SCHEMA_VERSION,
        "session": {"id": timestamp, "started_at": timestamp, "updated_at": timestamp},
        "next_ids": {item_type: 1 for item_type in TYPE_RULES},
        "items": [],
    }


def safe_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).resolve()
    try:
        path.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise ScratchpadError(f"Path must stay inside repository: {path}") from exc
    return path


def load_document(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScratchpadError(f"Scratchpad does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ScratchpadError(f"Scratchpad contains invalid JSON at line {exc.lineno}") from exc
    validate_document(document)
    return document


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def normalized_title(title: str) -> str:
    return re.sub(r"[\W_]+", " ", title.casefold()).strip()


def is_resolved(item: dict[str, Any]) -> bool:
    return item["status"] in TYPE_RULES[item["type"]]["resolved"]


def validate_document(document: Any) -> None:
    if not isinstance(document, dict) or document.get("version") != SCHEMA_VERSION:
        raise ScratchpadError(f"Scratchpad version must be {SCHEMA_VERSION}")
    session = document.get("session")
    if not isinstance(session, dict):
        raise ScratchpadError("session must be an object")
    for field in ("id", "started_at", "updated_at"):
        if not isinstance(session.get(field), str):
            raise ScratchpadError(f"session.{field} must be text")
        parse_timestamp(session[field])
    if not isinstance(document.get("next_ids"), dict):
        raise ScratchpadError("next_ids must be an object")
    if set(document["next_ids"]) != set(TYPE_RULES):
        raise ScratchpadError("next_ids must contain every item type")
    items = document.get("items")
    if not isinstance(items, list):
        raise ScratchpadError("items must be an array")

    ids: set[str] = set()
    active_titles: set[tuple[str, str]] = set()
    for item in items:
        validate_item(item)
        item_id = item["id"]
        if item_id in ids:
            raise ScratchpadError(f"Duplicate item ID: {item_id}")
        ids.add(item_id)
        if not is_resolved(item):
            title_key = (item["type"], normalized_title(item["title"]))
            if title_key in active_titles:
                raise ScratchpadError(f"Duplicate unresolved title: {item['title']}")
            active_titles.add(title_key)

    for item_type, counter in document["next_ids"].items():
        if item_type not in TYPE_RULES or not isinstance(counter, int) or counter < 1:
            raise ScratchpadError(f"Invalid next_ids entry: {item_type}")
    for item in items:
        validate_references(item, ids)
    reject_dependency_cycles(items)


def validate_item(item: Any) -> None:
    if not isinstance(item, dict):
        raise ScratchpadError("Each item must be an object")
    unknown_fields = set(item) - ITEM_FIELDS
    if unknown_fields:
        raise ScratchpadError(f"Unknown item field: {min(unknown_fields)}")
    item_type = item.get("type")
    if item_type not in TYPE_RULES:
        raise ScratchpadError(f"Invalid item type: {item_type}")
    expected_prefix = TYPE_RULES[item_type]["prefix"]
    if not re.fullmatch(rf"{expected_prefix}-\d{{4}}", str(item.get("id", ""))):
        raise ScratchpadError(f"Invalid ID for {item_type}: {item.get('id')}")
    if item.get("status") not in TYPE_RULES[item_type]["statuses"]:
        raise ScratchpadError(f"Invalid status for {item_type}: {item.get('status')}")
    for field in REQUIRED_TEXT_FIELDS:
        if not isinstance(item.get(field), str) or not item[field].strip():
            raise ScratchpadError(f"{field} must be non-empty text")
    for field in ("created_at", "updated_at"):
        if not isinstance(item.get(field), str) or not item[field]:
            raise ScratchpadError(f"{field} is required")
        parse_timestamp(item[field])
    for field in OPTIONAL_LIST_FIELDS:
        if field in item and (
            not isinstance(item[field], list) or any(not isinstance(value, str) for value in item[field])
        ):
            raise ScratchpadError(f"{field} must be an array of item IDs or text")
    if is_resolved(item):
        if not isinstance(item.get("outcome"), str) or not item["outcome"].strip():
            raise ScratchpadError("Resolved item requires outcome")
        if not item.get("resolved_at"):
            raise ScratchpadError("Resolved item requires resolved_at")
    if item["status"] == "blocked" and not item.get("blocked_by"):
        raise ScratchpadError("Blocked item requires blocked_by")


def validate_references(item: dict[str, Any], ids: set[str]) -> None:
    references = set(item.get("depends_on", [])) | set(item.get("blocked_by", []))
    if item["id"] in references:
        raise ScratchpadError(f"Item cannot reference itself: {item['id']}")
    missing = references - ids
    if missing:
        raise ScratchpadError(f"Missing referenced item: {min(missing)}")


def reject_dependency_cycles(items: list[dict[str, Any]]) -> None:
    graph = {
        item["id"]: set(item.get("depends_on", [])) | set(item.get("blocked_by", []))
        for item in items
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item_id: str) -> None:
        if item_id in visiting:
            raise ScratchpadError(f"Dependency cycle includes {item_id}")
        if item_id in visited:
            return
        visiting.add(item_id)
        for dependency in graph[item_id]:
            visit(dependency)
        visiting.remove(item_id)
        visited.add(item_id)

    for item_id in graph:
        visit(item_id)


def find_item(document: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in document["items"]:
        if item["id"] == item_id:
            return item
    raise ScratchpadError(f"Unknown item ID: {item_id}")


def parse_json_object(raw_value: str, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ScratchpadError(f"{field_name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise ScratchpadError(f"{field_name} must be a JSON object")
    return value


def mutate_document(path: Path, mutation: Callable[[dict[str, Any], str], Any]) -> Any:
    document = load_document(path)
    now = utc_now()
    result = mutation(document, now)
    document["session"]["updated_at"] = now
    validate_document(document)
    atomic_write_json(path, document)
    return result


def add_item(document: dict[str, Any], payload: dict[str, Any], now: str) -> dict[str, Any]:
    item_type = payload.get("type")
    if item_type not in TYPE_RULES:
        raise ScratchpadError(f"Invalid item type: {item_type}")
    counter = document["next_ids"][item_type]
    item = {
        **payload,
        "id": f"{TYPE_RULES[item_type]['prefix']}-{counter:04d}",
        "status": payload.get("status", TYPE_RULES[item_type]["initial"]),
        "created_at": now,
        "updated_at": now,
    }
    document["next_ids"][item_type] = counter + 1
    document["items"].append(item)
    return item


def update_item(document: dict[str, Any], item_id: str, changes: dict[str, Any], now: str) -> dict[str, Any]:
    forbidden = IMMUTABLE_FIELDS & changes.keys()
    if forbidden:
        raise ScratchpadError(f"Cannot update immutable field: {min(forbidden)}")
    if "status" in changes:
        raise ScratchpadError("Use transition command to change status")
    item = find_item(document, item_id)
    item.update(changes)
    item["updated_at"] = now
    return item


def transition_item(document: dict[str, Any], item_id: str, changes: dict[str, str | None], now: str) -> dict[str, Any]:
    item = find_item(document, item_id)
    status = changes["status"]
    outcome = changes.get("outcome")
    if not isinstance(status, str):
        raise ScratchpadError("Transition status must be text")
    if status not in TYPE_RULES[item["type"]]["statuses"]:
        raise ScratchpadError(f"Invalid status for {item['type']}: {status}")
    was_resolved = is_resolved(item)
    will_resolve = status in TYPE_RULES[item["type"]]["resolved"]
    if will_resolve and not (outcome or item.get("outcome")):
        raise ScratchpadError("Resolved transition requires outcome")
    if was_resolved and not will_resolve:
        history = item.setdefault("history", [])
        history.append(
            {
                "status": item["status"],
                "outcome": item["outcome"],
                "resolved_at": item["resolved_at"],
            }
        )
        item.pop("outcome", None)
        item.pop("resolved_at", None)
    item["status"] = status
    item["updated_at"] = now
    if will_resolve:
        item["outcome"] = outcome or item["outcome"]
        item["resolved_at"] = now
    return item


def apply_operation(document: dict[str, Any], operation: dict[str, Any], now: str) -> dict[str, Any]:
    operation_name = operation.get("operation")
    if operation_name == "add":
        payload = operation.get("item")
        if not isinstance(payload, dict):
            raise ScratchpadError("add operation requires item object")
        return add_item(document, payload, now)
    item_id = operation.get("id")
    if not isinstance(item_id, str):
        raise ScratchpadError(f"{operation_name} operation requires item ID")
    if operation_name == "update":
        changes = operation.get("changes")
        if not isinstance(changes, dict):
            raise ScratchpadError("update operation requires changes object")
        return update_item(document, item_id, changes, now)
    if operation_name == "transition":
        return transition_item(
            document,
            item_id,
            {"status": operation.get("status"), "outcome": operation.get("outcome")},
            now,
        )
    raise ScratchpadError(f"Unsupported operation: {operation_name}")


def check_handoff(document: dict[str, Any], notes_path: Path) -> None:
    try:
        notes = notes_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScratchpadError(f"Handoff notes do not exist: {notes_path}") from exc
    missing = [item["id"] for item in document["items"] if not is_resolved(item) and item["id"] not in notes]
    stale = [item["id"] for item in document["items"] if is_resolved(item) and item["id"] in notes]
    if missing:
        raise ScratchpadError(f"Handoff missing unresolved item: {missing[0]}")
    if stale:
        raise ScratchpadError(f"Handoff still contains resolved item: {stale[0]}")


def archive_resolved(document: dict[str, Any], archive_path: Path, now: str) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=30)
    records = read_archive(archive_path)
    resolved = [item for item in document["items"] if is_resolved(item)]
    existing_keys = {(record["item"]["id"], record["item"]["resolved_at"]) for record in records}
    for item in resolved:
        key = (item["id"], item["resolved_at"])
        if key not in existing_keys:
            records.append({"session_id": document["session"]["id"], "archived_at": now, "item": item})
    recent = [record for record in records if parse_timestamp(record["archived_at"]) >= cutoff]
    write_archive(archive_path, recent[-100:])
    referenced = {reference for item in document["items"] if not is_resolved(item) for reference in item.get("depends_on", []) + item.get("blocked_by", [])}
    document["items"] = [item for item in document["items"] if not is_resolved(item) or item["id"] in referenced]
    document["session"] = {"id": now, "started_at": now, "updated_at": now}
    return len(resolved)


def parse_timestamp(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ScratchpadError(f"Invalid stored timestamp: {value}") from exc


def read_archive(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ScratchpadError(f"Archive has invalid JSON at line {line_number}") from exc
    return records


def write_archive(path: Path, records: list[dict[str, Any]]) -> None:
    content = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--all", action="store_true")
    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("id")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--operation-file", required=True)
    subparsers.add_parser("validate")
    handoff_parser = subparsers.add_parser("check-handoff")
    handoff_parser.add_argument("--notes", required=True)
    archive_parser = subparsers.add_parser("archive-resolved")
    archive_parser.add_argument("--notes", required=True)
    archive_parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    return parser


def run(args: argparse.Namespace) -> Any:
    path = safe_path(args.file)
    if args.command == "init":
        if not path.exists():
            atomic_write_json(path, empty_document())
        return {"status": "ready", "path": str(path)}
    document = load_document(path)
    if args.command == "list":
        items = document["items"] if args.all else [item for item in document["items"] if not is_resolved(item)]
        return {"items": items}
    if args.command == "get":
        return find_item(document, args.id)
    if args.command == "apply":
        operation_path = safe_path(args.operation_file)
        operation = parse_json_object(operation_path.read_text(encoding="utf-8"), "operation file")
        result = mutate_document(path, lambda state, now: apply_operation(state, operation, now))
        operation_path.unlink()
        return result
    if args.command == "validate":
        return {"status": "valid", "items": len(document["items"])}
    notes_path = safe_path(args.notes)
    if args.command == "check-handoff":
        check_handoff(document, notes_path)
        return {"status": "valid"}
    if args.command == "archive-resolved":
        check_handoff(document, notes_path)
        archive_path = safe_path(args.archive)
        count = mutate_document(
            path,
            lambda state, now: archive_resolved(state, archive_path, now),
        )
        return {"status": "archived", "count": count}
    raise ScratchpadError(f"Unsupported command: {args.command}")


def main() -> int:
    try:
        result = run(build_parser().parse_args())
    except ScratchpadError as exc:
        sys.stderr.write(json.dumps({"error": str(exc)}) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
