# Tech Context

## Languages

| Language | Where | Notes |
|---|---|---|
| C | `libgnucash/`, `gnucash/` | The bulk of the engine and UI plumbing |
| C++ | `libgnucash/`, `gnucash/` | Modern code; `.cpp` alongside `.c` |
| Scheme (Guile) | `gnucash/report/`, `gnucash/gnome/` | Reports, and increasingly general application logic |
| Python | `bindings/python/`, `util/` | SWIG-generated bindings over the C/C++ API |
| CMake | throughout | Build definition; no autotools in the current tree |

## Build

CMake with the **Ninja** generator in this checkout (`build/CMakeCache.txt` sets `CMAKE_GENERATOR:INTERNAL=Ninja`).

```bash
cmake -G Ninja -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

`/build/` is gitignored (`.gitignore:195`). `ninja`, `cmake`, and `ctest` are all present on this machine.

## Module layout

`libgnucash/` — the non-UI core:

| Directory | Responsibility |
|---|---|
| `engine/` | QOF object framework, the book/transaction/account model, the core of the application |
| `backend/` | Persistence: XML file backend, SQL (SQLite / MySQL / PostgreSQL) |
| `app-utils/` | Application-level helpers built on the engine |
| `core-utils/` | Low-level utilities; no engine dependency |
| `gnc-module/` | Dynamic module loading and versioning |
| `quotes/` | `finance::quote` integration for price retrieval |
| `tax/` | US tax report data tables |

`gnucash/` — the application and UI: `gnome/`, `gnome-utils/`, `gnome-search/`, `gtkbuilder/`, `html/`, plus `gnucash-cli` and the main entry point.

`bindings/` — SWIG interface definitions and generated Python/Guile bindings.
`common/`, `borrowed/` — shared and vendored support code.

## Toolchain in use here

- **GTK3** — pinned via `pkg_check_modules (GTK3 ... gtk+-3.0>=...)`; there is GTK4/WebKit2 work in the tree, but GTK3 is the active dependency.
- **Gwenhywfar** — required by the GTK3 GUI layer (`gwengui-gtk3`).
- **Guile** — Scheme runtime for reports.
- **SWIG** — generates the Python and Guile bindings.

Confirm the exact flags and minimum versions from `CMakeLists.txt` in the directory you are changing rather than from memory — this file records shape, not versions.

## Python in this repo

The repo ships Python for bindings and utilities but has **no pytest infrastructure installed**. Session-memory tooling under `.claude/` is plain `python3` with stdlib only, run via `python3 -m unittest` — deliberately no third-party dependency, because adding one to an upstream C/C++ project is friction the port should not introduce.
