# Project Brief

## What this repository is

GnuCash — free, open-source double-entry accounting software. This is the `stable` branch of a working checkout, with `main` as the upstream default branch.

## Scope of this Memory Bank

This Memory Bank tracks **work done in this checkout by this user**, not the GnuCash project's own roadmap. Upstream planning lives in GnuCash's own mailing lists, Bugzilla, and `NEWS`.

Three workstreams are in play:

1. **Upstream fixes** — patches intended for `gnucash/gnucash`. Recent work on this branch has centred on Windows/mingw64 codepage handling, `libgnucash/app-utils` test hygiene, and report scripts (`new-owner-report`).
2. **Modernization exploration** — work under the untracked `analysis/` and `modernized/` directories, produced by the code-modernization tooling. Explicitly exploratory; nothing here is bound for upstream in its current form.
3. **Fork-local changes** — anything that serves this checkout only.

## Goals

- Keep a durable record of what each session changed, what it proved, and what it left unproven.
- Never let a stale build pass be mistaken for a current one.
- Preserve enough context that a session starting cold can resume without re-deriving decisions.

## Non-goals

- Mirroring upstream GnuCash planning or release management.
- Tracking code structure that is already readable from the tree.
- Replacing `git log` — history is git's job.

## Boundaries

- `analysis/` and `modernized/` are untracked and outside the upstream diff.
- Changes intended for upstream should stay reviewable as a minimal diff against `main`.
