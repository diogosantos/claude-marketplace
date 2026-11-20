---
name: wave
description: >
  Run a delivery wave end to end from a wave document or a list of ticket keys: reconcile, root-cause, brief,
  open a wave branch, dispatch implementers, review and merge their PRs into the wave branch, acceptance build,
  report, and a wave PR into main for the codeowner. Use for /waves:wave, "run this wave",
  "wave authorized", or when handed an orchestration prompt with phases and tickets.
argument-hint: "<wave document, ticket keys, or path to a wave .md>"
---

# /waves:wave

The wave is: $ARGUMENTS

If that is a path, read the file. If it is only ticket keys, the wave document is those tickets in the given order
with the default gates below. Load the `waves:coordinate` skill and follow it; this skill fixes the phases and the
gates a wave always has, whatever the document says.

## Phases

**Phase 0, reconcile.** As in `coordinate` section 1. Output a short baseline note before any dispatch: main SHA,
wave branch name, done-bar result, which target tickets are already merged or reopened, free disk, the agents you
will run and in what order. Do not duplicate completed work, reopen settled decisions, or add speculative refactoring.

**Phase 1..n, tickets.** In the document's priority order. For each ticket: root cause from the code, brief, dispatch
(`waves:implementer`, which opens the ticket PR into the wave branch), monitor, ticket-level review
(`waves:ticket-reviewer`), merge into the wave branch (`waves:merge-ticket`).
Independent tickets run in parallel in one dispatch message; tickets that share core files run in sequence. A
ticket the owner reopened must be verified on the exact build the owner tested, and must not be closed without the
kind of evidence the owner asked for (a real plugin window, a real device, a real file).

**Gates (every ticket).**
1. A regression test that fails before the fix and passes after.
2. The project's done bar, lints denied.
3. Ponytail review, then Codex review, both clean (`waves:review-loop`).
4. The project's real-app check with real data or plugins where the ticket touches runtime behaviour.
5. The ticket's PR into the wave branch, clean CI on it, merged by the coordinator. Nothing is pushed or merged
   into `main` during a wave.
6. Self-contained Jira closing comment with evidence and screenshots (`waves:ticket-closeout`).
7. Previously accepted behaviour named in the document or in `.claude/waves.md` under "protect" stays intact.

**Final phase, acceptance build and wave PR.** As in `coordinate` section 7: package from the wave branch head,
exact SHA and archive hash, coordinator-run app check, wave report on the epic, then `waves:ship-wave` opens the PR
from the wave branch into `main`. Short message to the owner with the build command, the wave PR URL, per-ticket
root cause and fix, automated and real-app evidence, manual acceptance checklist, new follow-ups. The wave ends with
the PR open: the codeowner merges it, never the coordinator.

## Execution rules
- Do not wait for routine implementation approvals; escalate only genuine architecture or product decisions, as a
  Jira comment and in your message.
- Never claim a result you did not verify from the branch, the CI run or the app log.
- Never report visual readiness as proof of functional readiness.
