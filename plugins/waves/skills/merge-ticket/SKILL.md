---
name: merge-ticket
argument-hint: "<ticket key>"
description: >
  Merge a finished, fully reviewed ticket branch into main: changelog line, known-limitations check, no-ff merge,
  push, CI poll, worktree and branch cleanup, Jira Done. Use for /waves:merge-ticket KEY, "merge SIM-42",
  "integrate the ticket branch".
---

# Merge a ticket

Ticket: $ARGUMENTS (the ticket branch is the branch whose name starts with that key).

Preconditions you verify yourself (do not take the agent's word): the ticket-level ponytail and Codex reviews are
clean on the branch head, the done bar passes on that head, every subtask is merged into the ticket branch, and
the closing comment exists on every ticket and subtask.

1. `git fetch origin`; if `main` moved since the branch was based, merge `main` into the ticket branch first and
   re-run the done bar (a conflict resolution is yours; new logic goes back to the implementer).
2. **Changelog**: add the ticket's line under `[Unreleased]` in `CHANGELOG.md` (the agent proposed the text in its
   report; edit it for the user's point of view).
3. **Known limitations**: apply the proposed edit to `docs/release/KNOWN_LIMITATIONS.md`; every entry added names an
   open ticket with label `known-limitation`; every entry lifted gets its tracking ticket commented or closed.
4. `git checkout main && git merge --no-ff KEY-branch -m "Merge KEY: <one line>"` (commit the changelog and limitations
   either on the branch before the merge or as one `KEY: changelog and known limitations` commit right after).
   End every commit message with the attribution lines the session gives you.
5. `git push origin main` immediately.
6. **CI**: poll, do not watch:
   ```
   for i in $(seq 1 60); do
     gh run list --branch main --limit 1 --json status,conclusion,headSha --jq '.[0] | "\(.status) \(.conclusion) \(.headSha[0:7])"'
     sleep 20
   done
   ```
   Stop when the line reads `completed success <sha>` for your merge SHA. A failure is yours to triage before the
   next merge.
7. **Cleanup**: `git worktree remove --force .claude/worktrees/<name>` (a worktree whose lock pid is the harness, not
   the agent, needs `git worktree remove -f -f` once the agent has reported), `git worktree prune`, delete the merged
   branches locally and on origin.
8. **Jira**: transition the ticket and its subtasks to Done; append "merged to main at <sha>, CI green" to the closing
   comment or as a short comment.
