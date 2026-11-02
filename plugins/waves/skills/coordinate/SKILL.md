---
name: coordinate
description: >
  The coordinator method for a Jira-driven wave: reconcile with main, root-cause each ticket from the code,
  split only what can run in parallel, write binding briefs, dispatch Sonnet implementers in worktrees, monitor
  and re-drive them, integrate with reviews, and hand the owner an acceptance build. Use when running /waves:wave,
  when asked to "run a wave", "dispatch agents", "coordinate these tickets", or whenever more than one ticket is
  to be delivered through subagents.
---

# Coordinate a wave

You are the coordinator. You plan, brief, dispatch, verify and merge. **You never write production code**: every
code change comes from an implementer agent on its own branch. You may edit briefs, `CHANGELOG.md`,
`docs/release/KNOWN_LIMITATIONS.md`, and resolve merge conflicts (resolution only, no new logic).

Project facts (tracker, done bar, review commands, app check, branch names) live in the repo's `.claude/waves.md`.
Read it first; if it is missing, run `/waves:init` before anything else. `CLAUDE.md` holds the project's engineering
rules; both are binding for you and for every agent.

## 1. Reconcile (always, before any dispatch)

1. `git fetch origin && git status`; be on a clean `main` at `origin/main`. Read the last merged commits.
2. Read `CLAUDE.md`, `.claude/waves.md`, `docs/release/KNOWN_LIMITATIONS.md`, and every target ticket **with all
   comments** (owner comments are authoritative: an owner decision in Jira overrides the brief you were given).
3. Confirm which tickets are already merged (`git log --oneline main | grep KEY`), which are reopened, and why
   owner acceptance failed (the exact build SHA the owner tested matters: reconcile it against `main`).
4. Baseline: run the project's done bar on `main`. A red baseline is reported, never fixed by a wave agent.
5. `df -h /`: want 20 GB or more free per concurrent agent (each worktree builds its own target dir). Delete stale
   worktree build caches first if tight. See the `lessons` skill.

## 2. Plan

- **Root cause before split.** Read the code path for each ticket yourself and write the diagnosis into the brief
  with file:line references. Agents verify it with tests; they do not start from zero.
- **Split only for parallelism.** One agent per ticket is the default. Create Jira subtasks only when the work
  divides into pieces that own **disjoint files** and can be reviewed independently. Shared files that several
  agents must touch get named functions per agent, never whole-file ownership by two agents.
- **Interfaces up front.** When two agents meet at a boundary, write the exact trait, type, function signatures and
  the behavioural contract into both briefs before dispatch. The agent that owns the type creates it first; the other
  codes against the brief's signature.
- **Sequence shared infrastructure.** Work on core shared files (playback, app state, main window) merges before
  unrelated agents that depend on it start; do not run two agents on the same core file.
- Create the branches/subtasks in Jira, move each ticket to In Progress when its agent starts, parents follow children.

## 3. Brief

Write one brief per agent to `.claude/worktrees/<wave>-<ticket>-brief.md` from `templates/brief.md` in this plugin.
A brief is binding and self-contained. It always contains:

- Read-first list: `CLAUDE.md`, `.claude/waves.md`, the ticket and context tickets with comments, the limitations
  entries for the ticket.
- Branch name (`KEY-slug` off `main`, or off the ticket branch for a subtask), base SHA, review base.
- Files owned; files other agents are editing right now (do not touch); shared files limited to named functions.
- The diagnosis with file:line references, and the question the agent must answer (regression? missing
  affordance? wrong rule?).
- Required behaviour as a checklist; what to protect (previously accepted behaviour, by ticket key).
- Tests, red first, by scenario.
- Real-app check: the project's app check command, PID watchdog, isolated HOME, window-only screenshots, dev flags
  instead of synthetic input, crash-report count before and after.
- Jira: the closing-comment content (see `ticket-closeout`), no status changes by agents.
- The final-report shape (branch, SHA, files, tests, review verdicts, proposed CHANGELOG line, proposed
  KNOWN_LIMITATIONS edit, follow-ups, decisions for the coordinator).

## 4. Dispatch

- `Agent` with `subagent_type: "waves:implementer"`, `model: "sonnet"`, `isolation: "worktree"`, one agent per brief.
  The prompt is: the brief path, the repo path, and "read the brief fully before starting".
- Launch every independent agent **in one message** so they run concurrently. Respect the disk budget.
- Reviews of a whole ticket branch go to `subagent_type: "waves:ticket-reviewer"`, never to the agent that wrote it.

## 5. Monitor

- On every stop notification: read the agent's report, then **verify it yourself** from the branch: head SHA exists,
  done bar passes on it, both review verdicts are quoted, the Jira closing comment exists. Never relay an agent's
  claim you did not check.
- A stalled or incomplete agent is re-driven with `SendMessage` (same agent, same context); a wrong direction gets
  a corrected brief, not a new agent from scratch.
- An agent that reports "waiting on a background job" has stopped; re-drive it with the instruction to run the job in
  the foreground.
- Never fabricate or predict a pending agent's result.

## 6. Integrate

1. Merge subtask branches into the ticket branch (`--no-ff`), then run the ticket-level review (ponytail, then Codex
   against `main`) through `waves:ticket-reviewer`. Fix cycles go back to the implementer.
2. Merge the ticket branch into `main` with `/waves:merge-ticket KEY` (changelog, limitations, push, CI, cleanup,
   Jira Done).
3. After each merge, agents still running on branches older than `main` get `main` merged into their branch by you
   before their ticket-level review, so the review sees the real result.

## 7. Acceptance

- Run the project's app check yourself on the final `main` (real plugin or real data, isolated HOME, PID watchdog,
  crash reports before and after) before handing the owner any run command.
- Package with the project's packaging command; record the exact SHA and the archive's SHA-256.
- Post the wave report on the epic (see `ticket-closeout`, section "Wave report") and send the owner the short
  version: build command, per-ticket root cause and fix, what was verified automatically and in the real app, the
  manual acceptance checklist, and new follow-up tickets.
