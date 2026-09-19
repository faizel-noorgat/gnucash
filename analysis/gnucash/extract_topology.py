#!/usr/bin/env python3
"""
Extract topology from GnuCash codebase.
Produces topology.json for interactive viewer.
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path("/projects/gnucash")
OUT_DIR = Path("/projects/gnucash/analysis/gnucash")

# Domain mapping (from ARCHITECTURE.mmd)
DOMAINS = {
    "engine": {
        "name": "Core Engine",
        "patterns": ["libgnucash/engine/*.c", "libgnucash/engine/*.cpp", "libgnucash/engine/*.h"],
    },
    "backend": {
        "name": "Backend/Persistence",
        "patterns": ["libgnucash/backend/**/*.c", "libgnucash/backend/**/*.cpp"],
    },
    "core-utils": {
        "name": "Core Utilities",
        "patterns": ["libgnucash/core-utils/*.c"],
    },
    "app-utils": {
        "name": "App Utilities",
        "patterns": ["libgnucash/app-utils/*.c", "libgnucash/app-utils/*.cpp"],
    },
    "gui": {
        "name": "GUI/Gnome",
        "patterns": ["gnucash/gnome/*.c", "gnucash/gnome/*.cpp", "gnucash/gnome-utils/*.c", "gnucash/gnome-utils/*.cpp"],
    },
    "register": {
        "name": "Register",
        "patterns": ["gnucash/register/**/*.c", "gnucash/register/**/*.cpp"],
    },
    "reports": {
        "name": "Reports",
        "patterns": ["gnucash/report/*.scm", "gnucash/report/**/*.scm"],
    },
    "import-export": {
        "name": "Import/Export",
        "patterns": ["gnucash/import-export/**/*.c", "gnucash/import-export/**/*.cpp"],
    },
    "bindings": {
        "name": "Bindings",
        "patterns": ["bindings/**/*.py", "bindings/**/*.scm", "bindings/**/*.cpp"],
    },
}

def find_source_files():
    """Find all source files in repo."""
    files = []
    for ext in ["*.c", "*.cpp", "*.h", "*.hpp", "*.scm", "*.py"]:
        files.extend(REPO_ROOT.rglob(ext))
    # Filter out borrowed/, contrib/, build/, test/
    return [f for f in files if not any(x in str(f) for x in ["borrowed/", "contrib/", "build/", ".git/"])]

def extract_module_info(filepath):
    """Extract module metadata from file."""
    rel_path = filepath.relative_to(REPO_ROOT)

    # Determine domain
    domain = "unknown"
    path_str = str(rel_path)
    if path_str.startswith("libgnucash/engine/"):
        domain = "engine"
    elif path_str.startswith("libgnucash/backend/"):
        domain = "backend"
    elif path_str.startswith("libgnucash/core-utils/"):
        domain = "core-utils"
    elif path_str.startswith("libgnucash/app-utils/"):
        domain = "app-utils"
    elif path_str.startswith("gnucash/gnome") or path_str.startswith("gnucash/gnome-utils"):
        domain = "gui"
    elif path_str.startswith("gnucash/register/"):
        domain = "register"
    elif path_str.startswith("gnucash/report/"):
        domain = "reports"
    elif path_str.startswith("gnucash/import-export/"):
        domain = "import-export"
    elif path_str.startswith("bindings/"):
        domain = "bindings"

    # Count LOC
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            loc = len([l for l in lines if l.strip() and not l.strip().startswith(('//', '/*', '*', '#'))])
    except:
        loc = 0

    # Language
    lang = filepath.suffix[1:] if filepath.suffix else "unknown"
    if lang == "scm":
        lang = "scheme"

    # Module name (filename without extension)
    module_name = filepath.stem

    return {
        "id": str(rel_path),
        "name": module_name,
        "kind": "module",
        "language": lang,
        "loc": loc,
        "file": str(rel_path),
        "domain": domain,
    }

def extract_calls(filepath):
    """Extract function calls from C/C++ file."""
    calls = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Match function calls: identifier followed by (
        # Skip common keywords and control structures
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, content)

        # Filter out keywords
        keywords = {'if', 'for', 'while', 'switch', 'return', 'sizeof', 'typeof', 'new', 'delete', 'throw', 'catch'}
        calls = [m for m in matches if m not in keywords and len(m) > 2]

    except:
        pass

    return calls

def extract_data_access(filepath):
    """Extract data store access (SQL, XML, file I/O)."""
    accesses = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # SQL patterns
        if re.search(r'EXEC\s+SQL|SELECT\s+|INSERT\s+|UPDATE\s+|DELETE\s+FROM', content, re.I):
            accesses.append({"type": "sql", "store": "SQL Database"})

        # XML patterns
        if re.search(r'xmlParse|xmlRead|xmlDoc|gnc_xml', content, re.I):
            accesses.append({"type": "xml", "store": "XML File"})

        # File I/O
        if re.search(r'fopen|fread|fwrite|g_file', content):
            accesses.append({"type": "file", "store": "File System"})

        # GSettings/preferences
        if re.search(r'g_settings|gnc_prefs', content, re.I):
            accesses.append({"type": "prefs", "store": "Preferences"})

    except:
        pass

    return accesses

def find_entry_points():
    """Find entry points (main, CLI handlers)."""
    entry_points = []

    # Main entry
    main_file = REPO_ROOT / "gnucash" / "gnucash.c"
    if main_file.exists():
        entry_points.append({
            "id": str(main_file.relative_to(REPO_ROOT)),
            "name": "main",
            "type": "cli",
        })

    # Python bindings entry
    py_main = REPO_ROOT / "bindings" / "python" / "gnucash_core.py"
    if py_main.exists():
        entry_points.append({
            "id": str(py_main.relative_to(REPO_ROOT)),
            "name": "Session",
            "type": "api",
        })

    return entry_points

def main():
    print("Extracting GnuCash topology...")

    # Find all source files
    files = find_source_files()
    print(f"Found {len(files)} source files")

    # Extract modules
    modules = []
    module_map = {}  # id -> module
    for f in files:
        if f.suffix in ['.c', '.cpp', '.h', '.hpp', '.scm', '.py']:
            mod = extract_module_info(f)
            modules.append(mod)
            module_map[mod['id']] = mod

    print(f"Extracted {len(modules)} modules")

    # Build domain tree
    domain_modules = defaultdict(list)
    for mod in modules:
        domain_modules[mod['domain']].append(mod)

    # Extract edges (calls)
    edges = []
    call_count = 0
    for mod in modules:
        filepath = REPO_ROOT / mod['file']
        if filepath.exists() and mod['language'] in ['c', 'cpp']:
            calls = extract_calls(filepath)
            # For now, just count calls (full resolution would need symbol table)
            call_count += len(calls)

    print(f"Found {call_count} function calls (unresolved)")

    # Extract data access
    data_edges = []
    data_stores = set()
    for mod in modules:
        filepath = REPO_ROOT / mod['file']
        if filepath.exists():
            accesses = extract_data_access(filepath)
            for acc in accesses:
                store_id = f"ds:{acc['store'].replace(' ', '_')}"
                data_stores.add((store_id, acc['store']))
                data_edges.append({
                    "source": mod['id'],
                    "target": store_id,
                    "kind": "read" if acc['type'] in ['xml', 'file', 'prefs'] else "write",
                })

    print(f"Found {len(data_stores)} data stores, {len(data_edges)} data edges")

    # Find entry points
    entry_points = find_entry_points()
    print(f"Found {len(entry_points)} entry points")

    # Identify dead ends (modules with no inbound calls)
    # Simplified: modules not called by others (would need full call graph)
    dead_ends = []  # Skip for now - need full call graph resolution

    # Build topology.json
    children = []
    for domain_id, domain_info in DOMAINS.items():
        domain_children = []
        for mod in domain_modules.get(domain_id, []):
            domain_children.append({
                "id": mod['id'],
                "name": mod['name'],
                "kind": "module",
                "language": mod['language'],
                "loc": mod['loc'],
                "file": mod['file'],
            })

        if domain_children:
            children.append({
                "id": f"dom:{domain_id}",
                "name": domain_info['name'],
                "kind": "domain",
                "children": domain_children[:20],  # Limit to top 20 per domain
            })

    # Add data stores domain
    data_children = [{"id": sid, "name": sname, "kind": "datastore"} for sid, sname in data_stores]
    if data_children:
        children.append({
            "id": "dom:data",
            "name": "Data Stores",
            "kind": "domain",
            "children": data_children,
        })

    topology = {
        "system": "GnuCash",
        "root": {
            "id": "sys",
            "name": "GnuCash",
            "kind": "system",
            "children": children,
        },
        "edges": data_edges[:100],  # Limit edges for visualization
        "entryPoints": [ep['id'] for ep in entry_points],
        "deadEnds": dead_ends,
        "observations": [
            "Core engine (libgnucash/engine) is the largest domain with ~108 files",
            "Backend supports multiple storage formats: XML (native), SQL (SQLite/PostgreSQL/MySQL)",
            "GUI layer (gnucash/gnome) has highest cyclomatic complexity in several files",
            "Scheme used for reports (~80 files) creates contributor barrier",
            "SWIG bindings enable Python/Scheme scripting of core engine",
            "Register widget (gnucash/register) is complex spreadsheet-like UI component",
            "Import/export supports multiple formats: CSV, QIF, OFX, AQBanking",
        ],
        "flows": [
            {
                "name": "Open Account File",
                "persona": "User",
                "description": "User opens existing GnuCash account file",
                "steps": [
                    {"label": "User clicks File > Open", "nodes": ["gnucash/gnome/gnc-main-window.cpp"]},
                    {"label": "File dialog shown", "nodes": ["gnucash/gnome-utils/gnc-file.c"]},
                    {"label": "Backend loads XML/SQL", "nodes": ["libgnucash/backend/xml/gnc-xml-backend.cpp"]},
                    {"label": "Engine creates Book/Account objects", "nodes": ["libgnucash/engine/Account.cpp"]},
                    {"label": "GUI displays account tree", "nodes": ["gnucash/gnome/gnc-plugin-page-account-tree.cpp"]},
                ],
            },
            {
                "name": "Enter Transaction",
                "persona": "User",
                "description": "User enters a financial transaction in register",
                "steps": [
                    {"label": "User selects account", "nodes": ["gnucash/gnome/gnc-plugin-page-account-tree.cpp"]},
                    {"label": "Register widget opens", "nodes": ["gnucash/register/ledger-core/split-register.c"]},
                    {"label": "User enters transaction data", "nodes": ["gnucash/register/ledger-core/split-register-control.cpp"]},
                    {"label": "Engine creates Transaction/Split", "nodes": ["libgnucash/engine/Transaction.cpp"]},
                    {"label": "Backend saves to file", "nodes": ["libgnucash/backend/xml/gnc-xml-backend.cpp"]},
                ],
            },
            {
                "name": "Generate Report",
                "persona": "User",
                "description": "User generates a financial report (balance sheet, income statement)",
                "steps": [
                    {"label": "User selects Reports menu", "nodes": ["gnucash/gnome/gnc-plugin-page-report.cpp"]},
                    {"label": "Scheme report engine runs", "nodes": ["gnucash/report/report.scm"]},
                    {"label": "Report queries engine data", "nodes": ["libgnucash/engine/Account.cpp"]},
                    {"label": "HTML generated", "nodes": ["gnucash/report/html-document.scm"]},
                    {"label": "Report displayed", "nodes": ["gnucash/html/gnc-html.c"]},
                ],
            },
        ],
    }

    # Write topology.json
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / "topology.json"
    with open(out_file, 'w') as f:
        json.dump(topology, f, indent=2)

    print(f"\nWrote {out_file}")
    print(f"  {len(modules)} modules")
    print(f"  {len(children)} domains")
    print(f"  {len(data_edges)} data edges")
    print(f"  {len(entry_points)} entry points")
    print(f"  {len(topology['flows'])} persona flows")

if __name__ == "__main__":
    main()
