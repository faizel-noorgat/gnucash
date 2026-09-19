# Product Context

## What GnuCash is

A desktop double-entry accounting application for personal and small-business finance. Long-lived: development began in 1997, and the current tree is the accumulation of that history. That age is the dominant fact about working in this codebase.

## What that means in practice

- **Correctness over novelty.** This is money. A regression that silently alters a balance is far worse than a crash, because it may not be noticed for months.
- **Backwards compatibility is a hard constraint.** File formats (XML and the SQL backends), the Scheme report API, and the Python bindings are all consumed by third parties. Breaking them is not a normal refactor.
- **The user base is long-tail and slow to upgrade.** A change that is fine on a fresh build can break a decade-old book file.
- **Multiple platforms are first-class.** Linux, macOS, and Windows via mingw64 are all supported targets. Recent commits on this branch are Windows codepage and locale work — evidence that platform-specific encoding bugs are a live area, not solved history.
- **Reports are user-extensible.** Users write their own Scheme reports. The report API is effectively public surface.

## Working assumptions

- A change that cannot be tested is a change that is not finished.
- Prefer fixing the root cause over the symptom, but on a long-lived branch a minimal, reviewable, upstream-acceptable fix often beats a cleaner rewrite that no maintainer will merge.
- Existing style in the surrounding file wins over personal preference.

## Where durable project truth lives

- `docs/decisions/` — ADRs for this checkout
- Upstream `NEWS`, `ChangeLog`, and the git history — project-level record
- `memory-bank/core/` — session-level state and handoff
