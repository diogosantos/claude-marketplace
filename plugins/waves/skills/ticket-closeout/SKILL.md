---
name: ticket-closeout
argument-hint: "[ticket key]"
description: >
  How a ticket is closed in Jira so the product owner never needs the repo: the self-contained closing comment,
  inline screenshots of the app window, follow-up tickets with the right labels, the known-limitations rule, and
  the wave report on the epic. Use for /waves:closeout, "write the closing comment", "post the report on the
  epic", "create a follow-up ticket".
---

# Ticket closeout

Jira is the single source of truth and the owner reads **only Jira**. Nothing that matters stays in the repo, a
README, an ADR or a chat message: copy it into the ticket.

Tracker facts (project key, cloudId, transition ids) are in `.claude/waves.md`. Load the Atlassian tools with
`ToolSearch select:mcp__atlassian__addOrEditJiraIssueComment,mcp__atlassian__createJiraIssue,mcp__atlassian__searchJiraIssuesUsingJql,mcp__atlassian__getJiraIssue,mcp__atlassian__transitionJiraIssue,mcp__atlassian__executeWrite`.

## Status rules

- In Progress when work starts; Done only once merged to `main`. A subtask is Done once merged into its ticket
  branch. Parents follow children.
- Agents never change status; the coordinator does, at merge time.
- A ticket the owner reopened stays In Progress until the owner confirms by hand, if they asked for that.
- Decisions and blockers are posted as comments **when they happen**, not at the end.

## The closing comment (one per ticket and subtask)

In this order, in plain language the owner can read without the code:

1. **Diagnosis**: what was actually wrong, where (file:line), and whether it was a regression, a missing piece or a
   wrong rule. For a reopened ticket, why the previous fix failed on the build the owner tested.
2. **What was built** and how it behaves for the user (a short table for rules and precedence when there are several).
3. **Tests added**, by name, noting which were red before the fix.
4. **Review findings**: every ponytail and Codex finding with its fate (fixed with SHA, or declined with the reason).
   Say if the ponytail review was run from SKILL.md.
5. **Real-app evidence**: the command run, the relevant log lines, crash-report count before and after.
6. **Screenshots** inline (any ticket with visible UI). See below.
7. **Known limitations** that remain, each with the follow-up ticket key.
8. **What the owner should try by hand**, as a numbered checklist.
9. Branch, head SHA, and "merged to main at <sha>" (coordinator) or "merge to main pending coordinator" (agent).

## Screenshots

Capture **only the app window**: `screencapture -o -l <window-id> shot.png` (find the id with the project's helper or
`osascript` reading the window id of your own PID only; never a full-screen capture, never another app's window).
Upload with `executeWrite` operation `uploadAttachmentToJiraIssue` (`filePath` input): it returns a curl command;
run it, then reference the attachment in the comment body with the inline-file fields
(`inlineFileId`, `inlineFileCollection`, `inlineFileName`) returned by the upload. Use `discover` if the
operation name has changed.

## Follow-up tickets

Real future work found during a ticket (a defect, an open question, an owner decision) becomes a **focused** Task:

- Search first (`project = KEY AND summary ~ "..."`) to avoid duplicates.
- Label `follow-up`; add `decision` when the owner must choose, `owner-review` when the owner must look.
- Name the epic in the description, link it from the finding ticket's closing comment.
- No broad, vague tickets; one thing each.

## Known limitations

Every entry in `docs/release/KNOWN_LIMITATIONS.md` names an **open** ticket (label `known-limitation`, plus
`decision` when it is the owner's call). A ticket that adds a limitation creates that follow-up ticket before it
merges; a ticket that lifts one removes the entry and comments on or closes the tracking ticket. No entry without a key.

## Wave report (on the epic, after the acceptance build)

Build archive and SHA-256, exact Git SHA, CI status; then per ticket: root cause, fix and merged commit, automated
evidence, real-app evidence, screenshots, limitations, outstanding owner checks; then new defects found and their
follow-up keys. Say explicitly which subsystem caused each P0 and do not report visual readiness as proof of
functional readiness.
