# waves

A Claude Code plugin for Jira-driven, multi-agent delivery of a closed-source product:

- a **coordinator** (your main session) that reconciles, root-causes, briefs, dispatches, verifies and merges, and never
  writes production code;
- **implementer** agents (Sonnet, one per ticket or subtask, each in an isolated git worktree) that start every fix with
  a failing regression test;
- an independent **ticket-reviewer** agent for the whole ticket branch;
- a fixed **review gate**: ponytail review, then Codex review, both clean before anything merges;
- **Jira as the only source of truth** for a product owner who never opens the repo: self-contained closing comments,
  inline app-window screenshots, follow-up tickets, known-limitations entries that always name an open ticket;
- a **guard hook** that blocks the commands that have caused real damage in shared multi-agent runs (writing git
  config, pkill/killall, synthetic OS input, force pushes), in the coordinator and in every subagent.

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
| `/waves:wave <doc or keys>` | Runs a wave end to end: brief, dispatch, review, merge, acceptance build, report |
| `/waves:merge-ticket KEY` | Changelog, limitations, no-ff merge, push, CI poll, cleanup, Jira Done |
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
  skills/        coordinate, wave, reconcile, init, merge-ticket, ticket-closeout, review-loop, lessons
  hooks/         hooks.json, guard.py
  templates/     waves.md, brief.md
```
