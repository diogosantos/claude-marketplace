---
name: review-loop
description: >
  The two-review gate every change passes before it merges: a ponytail review of the committed diff, then a Codex
  review once ponytail is clean, each finding fixed or declined with a reason, repeated until both are clean. Use for
  "review this branch", "run the review loop", before any merge, and inside agent briefs.
---

# Review loop

Order is fixed: ponytail first, Codex only after ponytail is clean, and everything **committed** before each run.
Re-run both on the fix commits until both are clean. Only then is the change mergeable.

## 1. Ponytail review

- Invoke the Skill `ponytail:ponytail-review` on `git diff <base>...HEAD` (base is `main` for a ticket branch, the
  ticket branch for a subtask).
- If the Skill tool answers "Unknown skill" (it does inside subagents), read and follow
  `~/.claude/plugins/cache/ponytail/ponytail/<version>/skills/ponytail-review/SKILL.md` verbatim and say so in the
  Jira comment ("ponytail review run from SKILL.md"). Find the version with `ls ~/.claude/plugins/cache/ponytail/ponytail/`.
- Read the connected code, not only the diff: callers of every changed function, the tests, the module docs.
- Fix every finding and commit. A finding you decline needs a one-sentence reason recorded in the Jira comment.

## 2. Codex review

```
D=$(mktemp -d)
codex exec review -c model="<codex model from .claude/waves.md>" --base <base> > "$D/codex.txt" 2>&1
grep -v '^[+-]' "$D/codex.txt" | grep -B2 -A40 '^codex$' | tail -60
```

- `--base <branch>` for a branch, `--commit <sha>` for one commit. Run it in the foreground (timeout up to 600000 ms).
- The closing `codex` message is the verdict. "No actionable correctness issues" (or similar) is clean; findings
  appear as `[P1]`/`[P2]` items or a "Review comment" block. **No closing message means "not reviewed", never
  "clean"**; re-run it.
- Fix every finding or record exactly why it does not apply; commit; re-run until clean.
- The ticket-level Codex run against `main` is mandatory even when every subtask was reviewed: it repeatedly finds
  what subtask reviews miss (a schema bump for new persisted data, an event consumed by two handlers).

## 3. Done bar

Re-run the project's done bar (from `.claude/waves.md`) on the final commit. Never loosen lints or add allow
attributes to get green.

## What goes to Jira

Every finding from both reviews, verbatim title, and its fate: fixed (commit SHA) or declined (reason). The owner
reads Jira only.
