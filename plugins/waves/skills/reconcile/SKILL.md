---
name: reconcile
description: >
  Phase 0 of a wave on its own: sync with main, read the tickets and comments, confirm what is merged or reopened,
  run the done bar baseline, check free disk, and report before any dispatch. Use for /waves:reconcile, "where are
  we", "establish the baseline", before starting any wave or when returning to a repo after a break.
argument-hint: "[ticket keys]"
---

Reconcile for: $ARGUMENTS (all open tickets In Progress or reopened in the tracker when empty).

Follow `waves:coordinate` section 1 exactly and report, in this order: `main` SHA and whether local equals origin;
any leftover worktrees and branches (and whether each is merged); the done-bar result on `main`; for each target
ticket its status, the last owner comment and whether its key appears in `git log main`; open owner acceptance
failures with the build SHA the owner tested; free disk and how many agents fit; and the dispatch order you propose.
Change nothing except fetching and pruning merged worktrees.
