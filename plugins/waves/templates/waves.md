# Waves: project facts

Read by the `waves` plugin (coordinator, implementers, reviewers). Facts only; engineering rules live in `CLAUDE.md`.

## Tracker
- Jira site: `<site>.atlassian.net`, project key: `KEY`, cloudId: `<uuid>`
- Epics: `KEY-1` … (what each covers, one line each)
- Transition ids: In Progress `<id>`, Done `<id>`
- Labels in use: `follow-up`, `decision`, `owner-review`, `known-limitation`

## Done bar
Run in this order; all must pass on the final commit:
```
<format check>
<lint, warnings denied>
<full test suite>
```
Local gate script (same as CI): `<path or none>`. CI: `<provider, OS, workflow file>`.

## Reviews
- Ponytail: Skill `ponytail:ponytail` (coding) and `ponytail:ponytail-review` (review); fallback SKILL.md under
  `~/.claude/plugins/cache/ponytail/ponytail/<version>/skills/`.
- Codex: `codex exec review -c model="gpt-6-luna" --base <branch>` (plugin default); fallback model `gpt-5.6-luna`.

## App check (coordinator before handing the owner a command; agents for runtime tickets)
- Command: `<binary> <flags for a headless/no-device run with real data or a real plugin>`
- Isolated home: `HOME=$(mktemp -d)` (or `<project equivalent>`); PID watchdog, no `timeout` on macOS.
- Crash reports: `~/Library/Logs/DiagnosticReports/<binary>-*.ips` (also written by `<probe helpers / tests>`).
- Screenshots: app window only, `screencapture -o -l <window-id>`.
- Packaging for owner builds: `<script>`; releasing notes: `<doc>`.

## Branches and commits
- Ticket branch `KEY-42-slug` off `main`; subtask branch `KEY-42.1-slug` off the ticket branch; no pull requests;
  coordinator merges `--no-ff` and pushes `main` after every ticket.
- Commit message starts with the key; trailers: the session's attribution lines, plus `<any project trailer>`.
- `CHANGELOG.md` section for new lines: `<[Unreleased] or version>`; limitations file: `docs/release/KNOWN_LIMITATIONS.md`.

## Protect (accepted behaviour every wave keeps; name the ticket that accepted it)
- `<behaviour>` (`KEY-n`)

## Worktrees and disk
- Agent worktrees under `.claude/worktrees/`; a debug build is about `<n>` GB per worktree; want 20 GB+ free per
  concurrent agent.
