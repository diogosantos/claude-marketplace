---
name: ship-wave
argument-hint: "[wave branch]"
description: >
  Close a wave: open the pull request from the wave branch into main for the codeowner, with the wave report as its
  body; never merge it. Once the codeowner has merged it, move the tickets to Done and clean up. Use for
  /waves:ship-wave, "open the wave PR", "ship the wave", "the wave PR is merged", or at the end of /waves:wave.
---

# Ship a wave

Wave branch: $ARGUMENTS (default: the one `wave/*` branch on origin, `git branch -r --list 'origin/wave/*'`; ask if
there are several). Codeowner: "Codeowner" in `.claude/waves.md`.

`gh pr list --head <wave branch> --base main --state all --json number,state,url,mergeCommit` tells you which case
you are in.

## No PR yet: open it

Preconditions: every ticket PR of the wave is merged into the wave branch (`gh pr list --base <wave branch> --state
open` is empty, or what is left is explicitly deferred); the acceptance build (`coordinate` section 7) was made from
the wave branch head and its app check passed.

1. `git fetch origin`; if `main` moved, merge `origin/main` into the wave branch, re-run the done bar and push.
2. Open the PR:
   ```
   gh pr create --base main --head <wave branch> --title "Wave <name>: <KEY-1, KEY-2, ...>" --body-file <file>
   ```
   Body: the wave report (`ticket-closeout`, "Wave report") in short form: per ticket the Jira link, root cause, fix,
   its merged ticket PR; the acceptance build SHA and archive SHA-256; the manual acceptance checklist; known
   limitations and follow-ups. Request the codeowner's review (`--reviewer <handle>` when `.claude/waves.md` gives a
   GitHub handle). End the body with the attribution line the session gives you.
3. Poll its CI (`gh pr checks <wave branch>`, as in `merge-ticket` step 5) and record the result on the PR.
4. Comment the PR URL on the epic and send it to the owner. **Stop. Never merge this PR**, never approve it on the
   owner's behalf, never enable auto-merge on it; the guard hook refuses `gh pr merge` on any PR into `main`.

## PR open: report

Report its state, checks and review decision (`gh pr view <n> --json state,reviewDecision,statusCheckRollup`).
Address review comments from the codeowner on the wave branch through implementers (production code) or yourself
(changelog, limitations, conflict resolution), push, and comment what changed. Do not merge.

## PR merged by the codeowner: close out

1. `git fetch origin && git checkout main && git pull --ff-only`; confirm the merge commit is on `main`.
2. **Jira**: move every ticket and subtask of the wave to Done (parents follow children; a reopened ticket whose
   owner asked to confirm by hand stays where the owner put it); append "merged to main via <wave PR URL> at <sha>"
   to each.
3. Delete the wave branch locally and on origin if GitHub did not; prune worktrees.

## PR closed without merge

Report it to the owner with their closing comment; change no ticket status.
