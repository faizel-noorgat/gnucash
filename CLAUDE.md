# GnuCash - CLAUDE.md

## Project Overview
GnuCash is open-source accounting software for personal and small business finance management.

## Tech Stack
- **Languages**: C, C++ with GObject system
- **Build**: CMake
- **Dependencies**: GLib, GTK3 (GUI), SQLite/PostgreSQL/MySQL (database)
- **Scripting**: Guile (Scheme), Python
- **Platforms**: Windows, macOS, Linux

## Key Directories
- `src/` - Core C/C++ source code
- `doc/` - Documentation
- `test/` - Test suite
- `docker/` - Docker build configurations

## Development Guidelines
- Maintain C/C++ binding compatibility
- Preserve scripting integration (Scheme/Python)
- Database schema changes require migration scripts
- Cross-platform compatibility must be maintained

## Session Memory
This project uses persistent session memory. Use:
- `/session-close` - Save session context to memory
- `/session-summary` - View accumulated session context

Memory is stored in: `~/.claude/projects/C--Users-Faizel-Noorgat-Documents-Projects-gnucash/memory/`

## Commands
- `/session-close` - Save current session state
- `/session-summary` - View session context
