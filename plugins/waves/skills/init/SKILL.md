---
name: init
description: >
  Set a repository up for the waves workflow: create .claude/waves.md (tracker, done bar, review commands, app check,
  branch and commit rules, protected behaviours) from the plugin template by reading the repo, and point CLAUDE.md at
  the plugin. Use for /waves:init, "set this repo up for waves", or whenever .claude/waves.md is missing.
---

Create `.claude/waves.md` in the repository root from `${CLAUDE_PLUGIN_ROOT}/templates/waves.md` (read it from
the plugin directory: `ls ~/.claude/plugins/cache/*/waves/*/templates/waves.md` or the `--plugin-dir` path).

Fill every field from evidence, not guesses:
- Tracker: ask the user for the Jira project key if no ticket key appears in the git log; get the cloudId from
  `mcp__atlassian__getAccessibleAtlassianResources`; read the transition ids with `getJiraIssue` on any issue
  (`transitions` expand) or leave them for the first `/waves:merge-ticket` to discover and fill in.
- Done bar: the exact commands CI runs (read `.github/workflows/*`, `Makefile`, `scripts/check.sh`, `package.json`).
- Review: the ponytail skill names and the Codex command with the model override the user wants.
- App check: how the app is run headless or with real data for a crash check, the isolated-home convention, and
  where crash reports land. Ask if the repo gives no hint.
- Branch, commit and changelog conventions from `CLAUDE.md` and the git log.
- Protect: the behaviours the owner has accepted and every wave must keep (ask the user).

Then add to `CLAUDE.md`, under Development, one paragraph: "Delivery runs through the `waves` plugin: `/waves:wave`
for a wave, `/waves:merge-ticket KEY` to integrate, `/waves:reconcile` for the baseline; project facts in
`.claude/waves.md`." Remove from `CLAUDE.md` only the process text the plugin now owns (coordinator and agent roles,
branch and merge mechanics, the review loop, the Jira closeout rules), keeping every project-specific engineering
rule. Show the user the diff before committing; commit on a branch, not on `main`.
