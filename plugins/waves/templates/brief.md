# KEY-42 — <one-line title in the owner's words>

Read first (binding): `CLAUDE.md`, `.claude/waves.md`, Jira KEY-42 with every comment, context tickets `KEY-n`
(why), the `KNOWN_LIMITATIONS.md` entries for this ticket. Paths are relative to `<absolute repo path>`; your
worktree is a copy under `.claude/worktrees/`.

Branch `KEY-42-slug` off `main` (`<base sha>`). Reviews against `main`.
You own: `<files>`. Shared files, named functions only: `<file>::<fn>`. Other agents are editing right now, do not
touch: `<files>`.

## Diagnosis from code reading (verify with tests first, then report whether it holds)
<what is wrong, where, file:line; regression / missing affordance / wrong rule; what the owner saw and why>

## Interfaces (when another agent meets you at a boundary)
```
<exact signatures and the behavioural contract; who creates the type first>
```

## Required
- <behaviour, as the owner will experience it>
- Protect: <accepted behaviour by ticket key>; <persisted format unchanged unless this brief says otherwise>.

## Tests (red first on main)
<scenarios, by name, through the real input path where one exists>

## Real app
<app-check command and flags, dev flag for the state to show, PID watchdog, isolated HOME, window-only screenshot,
crash reports before/after>

## Jira
Closing comment per `waves:ticket-closeout`: diagnosis with line numbers; what was built; rules in one table; tests
by name (red first); ponytail and Codex findings and their fate; what the owner should try by hand; branch + head SHA;
"merge to main pending coordinator". No status changes. Proposed CHANGELOG line and KNOWN_LIMITATIONS edit go in your
final report.
