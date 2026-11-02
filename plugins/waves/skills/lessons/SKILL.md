---
name: lessons
description: >
  Operational lessons from running multi-agent waves on a shared macOS machine: disk budget before dispatch,
  worktree locks held by the harness, attributing crash reports, verifying dev flags quit, reading Codex output,
  shared git config across worktrees, synthetic input. Read before dispatching agents and when something odd
  happens on the machine.
---

# Lessons

- **Disk before dispatch.** Each worktree builds its own target dir (1 to 10 GB for a debug desktop build, more
  for the main repo). Three fresh builds once filled the disk; with ENOSPC the harness cannot write tool output, so
  no session can free space and the owner must delete caches by hand. `df -h /` first; want 20 GB+ free per concurrent
  agent; delete stale `.claude/worktrees/*/target` and `target/debug/incremental` (caches only) if tight.
- **Git config is shared across worktrees.** `.git/config` is one file for every worktree. An agent that set a
  "temporary" `user.name` in a scratch worktree relabelled 155 of the owner's commits over a week. Agents never write
  git config; the plugin hook blocks it. A one-off identity goes on the command line: `git -c user.name=scratch -c
  user.email=scratch@invalid revert -n <sha>`.
- **Worktree locks.** After an agent in `isolation: worktree` finishes, its worktree shows as locked by a pid that is
  the harness, not the agent. Confirm the branch is merged, then `git worktree remove -f -f <path>` and prune.
- **Crash reports have several authors.** `~/Library/Logs/DiagnosticReports/<app>-*.ips` is also written by plugin
  probe helper processes (a run with a fresh HOME probes every installed plugin) and by test binaries. Parse the JSON
  after the first line, read `faultingThread` and `procLaunch`, and attribute the crash to the app run, a probe or a
  test before counting it against a change. Probe crashes are still product issues.
- **Dev flags must quit.** Verify every new dev flag with `--quit-after N` under a PID watchdog (macOS has no
  `timeout`). A flag that builds its state through the undo history leaves the project dirty and the quit hangs on
  the unsaved-changes prompt; demo flags must produce a clean baseline.
- **Codex output.** The closing `codex` message is the verdict; there is no structured block. `--uncommitted` can
  exit 0 with no verdict at all. Read it with `grep -v '^[+-]' out.txt | grep -B2 -A40 '^codex$' | tail -60`.
- **Synthetic input races.** Two agents' cliclick drags once landed in another agent's window (and could land on the
  owner's desktop). No OS-level input from any agent; dev flags, headless UI tests and window-only screenshots are the
  evidence. Posting an event into the app's own process queue from a dev flag is fine when the brief says so.
- **Skills inside subagents.** Plugin skills from other plugins (ponytail) do not load via the Skill tool inside
  subagents; briefs point at the SKILL.md on disk and the agent follows it by hand.
- **Agents do not wake up.** An agent that ends its turn to "wait" for cargo or Codex is stopped. Long commands run
  in the foreground with a timeout up to 600000 ms; the coordinator re-drives any agent that stops early.
- **CI watch.** `gh run watch` is unreliable from a session; poll `gh run list --branch main --limit 1 --json ...`.
- **BSD tools.** macOS `sed` has no `\b`; use perl for word-boundary renames.
