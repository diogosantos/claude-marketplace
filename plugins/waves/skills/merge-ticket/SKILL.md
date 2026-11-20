---
name: merge-ticket
argument-hint: "<ticket key>"
description: >
  Merge a finished, fully reviewed ticket PR into the wave branch: changelog line, known-limitations check, CI on the
  PR, merge commit, worktree and branch cleanup, Jira comment. Never touches main. Use for /waves:merge-ticket KEY,
  "merge SIM-42", "integrate the ticket branch".
---

# Merge a ticket into the wave branch

Ticket: $ARGUMENTS (the ticket branch is the branch whose name starts with that key; its PR targets the wave branch
`wave/<slug>` named in the brief).

Preconditions you verify yourself (do not take the agent's word): the ticket PR exists and its base is the wave
branch (`gh pr view KEY-branch --json baseRefName,headRefOid,url`); the ticket-level ponytail and Codex reviews are
clean on the PR head; the done bar passes on that head; every subtask PR is merged into the ticket branch; the
closing comment exists on every ticket and subtask.

1. `git fetch origin`; if the wave branch moved since the ticket branch was based, merge `origin/<wave branch>` into
   the ticket branch and push it (a conflict resolution is yours; new logic goes back to the implementer), then
   re-run the done bar.
2. **Changelog**: add the ticket's line under `[Unreleased]` in `CHANGELOG.md` (the agent proposed the text in its
   report; edit it for the user's point of view).
3. **Known limitations**: apply the proposed edit to `docs/release/KNOWN_LIMITATIONS.md`; every entry added names an
   open ticket with label `known-limitation`; every entry lifted gets its tracking ticket commented or closed.
4. Commit both on the ticket branch as one `KEY: changelog and known limitations` commit and push the branch (the PR
   updates). End every commit message with the attribution lines the session gives you.
5. **CI on the PR**: poll, do not watch:
   ```
   for i in $(seq 1 60); do
     gh pr checks KEY-branch --json name,bucket --jq 'map(.bucket) | group_by(.) | map("\(.[0])=\(length)") | join(" ")'
     sleep 20
   done
   ```
   Stop when every check is `pass`. A failure is yours to triage on the branch (new logic goes back to the
   implementer). If CI does not run on PRs into the wave branch (`.claude/waves.md` says so), run the project's local
   gate on the PR head instead and record that in the PR and the Jira comment.
6. **Merge**: `gh pr merge KEY-branch --merge --delete-branch` (a merge commit, never squash or rebase, so the ticket
   history stays intact). Record the merge SHA on the wave branch.
7. **Cleanup**: `git worktree remove --force .claude/worktrees/<name>` (a worktree whose lock pid is the harness, not
   the agent, needs `git worktree remove -f -f` once the agent has reported), `git worktree prune`, delete the merged
   branches locally (and on origin if `--delete-branch` did not).
8. **Jira**: comment "merged into `<wave branch>` via <PR URL> at <sha>, CI green; reaches main with the wave PR". Do
   **not** move the ticket to Done: that happens only after the codeowner merges the wave PR (`waves:ship-wave`).
9. Merge `origin/<wave branch>` into every ticket branch still in flight and push it, so their reviews see the real
   result.

Never merge into `main`, never push to `main`; the guard hook refuses both.
