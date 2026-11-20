# waves

A Claude Code plugin for Jira-driven, multi-agent delivery of a closed-source product:

- a **coordinator** (your main session) that reconciles, opens a wave branch, root-causes, briefs, dispatches, verifies
  and merges agents' PRs into the wave branch, and never writes production code;
- **implementer** agents (Sonnet, one per ticket or subtask, each in an isolated git worktree) that start every fix with
  a failing regression test and end by opening a PR for their own branch;
- an independent **ticket-reviewer** agent for the whole ticket branch;
- a fixed **review gate**: ponytail review, then Codex review, both clean before anything merges;
- **Jira as the only source of truth** for a product owner who never opens the repo: self-contained closing comments,
  inline app-window screenshots, follow-up tickets, known-limitations entries that always name an open ticket;
- a **guard hook** that blocks the commands that have caused real damage in shared multi-agent runs (writing git
  config, pkill/killall, synthetic OS input, force pushes) and anything that would land on `main` without the
  codeowner (pushing to `main`, `gh pr merge` on a PR into `main`), in the coordinator and in every subagent;
- **`main` belongs to the codeowner**: a wave ends with one PR from the wave branch into `main`, which only the
  codeowner merges.

```
main ── wave/<slug> ── KEY-42-slug ── KEY-42.1-slug
          ▲               ▲   └── PR → KEY-42-slug   (subtask agent opens, coordinator merges)
          │               └────── PR → wave/<slug>   (ticket agent opens, coordinator merges)
          └────────────────────── PR → main          (coordinator opens, codeowner merges)
```

It was distilled from eight delivery waves on a Rust desktop DAW. Project facts (tracker, done bar, review commands,
app check) live in each repository's `.claude/waves.md`; engineering rules stay in that repo's `CLAUDE.md`.

## Install

```
claude plugin marketplace add diogosantos/claude-marketplace
claude plugin install waves@diogosantos
```

Development: `claude --plugin-dir ./plugins/waves` and `claude plugin validate ./plugins/waves`.

Dependencies you install separately: the [ponytail](https://github.com/DietrichGebert/ponytail) plugin, the Atlassian
MCP server (Jira), the `codex` CLI, `gh`, `python3` (for the guard hook).

## Use

| Command | What it does |
| --- | --- |
| `/waves:init` | Creates `.claude/waves.md` from the repo and points `CLAUDE.md` at the plugin |
| `/waves:reconcile [keys]` | Phase 0: baseline on `main`, ticket states, leftovers, disk, dispatch order |
| `/waves:wave <doc or keys>` | Runs a wave end to end: wave branch, brief, dispatch, review, merge into the wave branch, acceptance build, wave PR |
| `/waves:merge-ticket KEY` | Changelog, limitations, CI on the ticket PR, merge it into the wave branch, cleanup, Jira comment |
| `/waves:ship-wave [branch]` | Opens the wave PR into `main` for the codeowner; after they merge it, moves tickets to Done |
| `/waves:ticket-closeout [KEY]` | The Jira closing comment, screenshots, follow-ups, wave report |
| `/waves:review-loop` | Ponytail then Codex, fix until clean |
| `/waves:lessons` | Operational lessons for shared-machine multi-agent runs |

Agents: `waves:implementer`, `waves:ticket-reviewer` (both `model: sonnet`, `isolation: worktree`). Templates for
the project file and for agent briefs are in `templates/`.

## Layout

```
plugins/waves/
  .claude-plugin/plugin.json
  agents/        implementer.md, ticket-reviewer.md
  skills/        coordinate, wave, reconcile, init, merge-ticket, ship-wave, ticket-closeout, review-loop, lessons
  hooks/         hooks.json, guard.py
  templates/     waves.md, brief.md
```
