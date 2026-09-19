# System Patterns

Architectural conventions that hold across the GnuCash tree. Read the code before trusting any of these — they describe shape, not current specifics.

## Engine and backend are separate

`libgnucash/engine/` models the accounting domain and knows nothing about persistence. `libgnucash/backend/` implements persistence — XML and the SQL backends (SQLite, MySQL, PostgreSQL) — behind that boundary. A change to how something is stored belongs in the backend; a change to what it means belongs in the engine. Crossing that line is the classic way to make a small fix large.

## Everything hangs off a book

The engine has no meaningful global state. Objects belong to a `QofBook`, and a session may hold several. Code that reaches for a singleton to avoid threading a book through a call chain is a bug waiting for the second book to exist. Pass the book.

## QOF objects and KVP

Domain objects are QOF objects — GObject-based, with registered properties and a key-value pair (KVP) frame for extensible, schema-less storage. KVP is how the tree carries data without a schema migration, and it is also how data becomes invisible: nothing enumerates KVP keys for you. When behaviour depends on a KVP value, make that dependency explicit rather than implicit.

## Modules load dynamically

`libgnucash/gnc-module/` handles dynamic module loading and version negotiation. Load order and version compatibility are real failure modes, not formalities.

## Reports are Scheme, and they are public API

Reports under `gnucash/report/` are written in Guile Scheme against a SWIG-wrapped C API. Users write their own. Treat the exposed report API as public surface: additions are safe, signature changes and removals are breaking.

## Text encoding is load-bearing and platform-dependent

GnuCash handles user data in arbitrary locales across Linux, macOS, and Windows. Recent work on this branch has been exactly here — forcing the mingw32 CRT to use the process code page, routing locale setting through msvcrt's `_wsetlocale`, and shipping a manifest to force UTF-8. Any change touching strings, filenames, locale, or `printf`-family functions on Windows is in this minefield. Test on the affected platform, not just the one you are sitting at.

## Naming

Public C symbols carry a `gnc`/`qof` prefix by subsystem (`gncAccount*`, `qofBook*`). File names mirror the primary type they implement. Match the surrounding file rather than introducing a new convention.

## Testing

Tests live next to the code they cover and are registered with CTest. Scheme tests exist for reports. A change with no runnable test is incomplete — but note that a build or test result is only current for the tree state that produced it.
