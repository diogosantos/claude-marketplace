#!/usr/bin/env python3
"""PreToolUse guard for the waves plugin.

Blocks the few shell commands that have caused real damage in multi-agent waves, in the
coordinator session and in every subagent:
  - writing git config (worktrees share .git/config; a scratch identity relabelled 155 commits)
  - killing processes by name (other agents and the owner run the same app concurrently)
  - synthetic OS input (clicks and keystrokes land in whichever window is frontmost)
  - force pushes
  - pushes to main/master (work lands through pull requests)
  - merging a pull request whose base is main/master (only the codeowner merges into main)
Exit 2 with the reason on stderr blocks the call; anything else lets it through.
"""
import json
import re
import shlex
import subprocess
import sys

READ_ONLY_CONFIG = re.compile(r"--(get|get-all|get-regexp|list|show-origin|show-scope)\b|(^|\s)-l(\s|$)")

RULES = [
    (
        re.compile(r"\bgit\b(?:\s+-C\s+\S+)?(?:\s+--?[\w-]+(?:=\S+)?)*\s+config\b(?P<rest>.*)"),
        lambda m: not READ_ONLY_CONFIG.search(m.group("rest")),
        "git config writes are blocked: worktrees share .git/config, so a 'temporary' identity "
        "relabels every commit in the repository. Pass a one-off identity on the command line "
        "instead: git -c user.name=scratch -c user.email=scratch@invalid <command>.",
    ),
    (
        re.compile(r"(^|[;&|\s])(pkill|killall)\b"),
        None,
        "pkill/killall are blocked: other agents and the owner run the same programs. Stop only "
        "processes you started, by PID (kill <pid>).",
    ),
    (
        re.compile(r"\bkill\s+(-\S+\s+)*-1\b"),
        None,
        "kill -1 (every process) is blocked. Stop only processes you started, by PID.",
    ),
    (
        re.compile(r"\b(cliclick|xdotool|ydotool)\b"),
        None,
        "Synthetic OS input is blocked: clicks and keys land in whichever window is frontmost, "
        "including other agents' windows and the owner's desktop. Use dev flags, headless UI "
        "tests, or an in-process event posted by the app itself when the brief allows it.",
    ),
    (
        re.compile(r"\bosascript\b.*(keystroke|key code|\bclick\b|System Events)", re.S),
        None,
        "osascript keystrokes/clicks are blocked (synthetic OS input). Use dev flags or headless "
        "UI tests instead.",
    ),
    (
        re.compile(r"\b(CGEventPost|CGEventCreate(Keyboard|Mouse)Event|AXUIElementPerformAction)\b"),
        None,
        "CGEvent/Accessibility input injection is blocked (synthetic OS input).",
    ),
    (
        re.compile(r"\bgit\b(?:\s+-C\s+\S+)?\s+push\b.*(\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S)"),
        None,
        "Force pushes are blocked. Merge or rebase onto the branch and push normally; if history "
        "must be rewritten, stop and report it to the owner.",
    ),
]


PROTECTED = {"main", "master"}
PUSH = re.compile(r"\bgit\b(?P<pre>(?:\s+-C\s+\S+)?)\s+push\b(?P<rest>[^;&|]*)")
PUSH_TO_MAIN = (
    "Pushing to main is blocked: work lands through pull requests. Push your own branch "
    "(git push -u origin <branch>) and open a PR into its base (the wave branch for a ticket)."
)
PR_MERGE = re.compile(r"\bgh\s+pr\s+merge\b(?P<rest>[^;&|]*)")
PR_MERGE_VALUE_FLAGS = {"-R", "--repo", "-b", "--body", "-F", "--body-file", "-t", "--subject",
                        "-A", "--author-email", "--match-head-commit"}
MERGE_TO_MAIN = (
    "Merging a pull request into main is blocked: only the codeowner merges into main. Leave the "
    "wave PR open, report its URL, and let the owner merge it."
)


def current_branch(cwd, pre):
    args = ["git"] + shlex.split(pre) + ["rev-parse", "--abbrev-ref", "HEAD"]
    try:
        out = subprocess.run(args, cwd=cwd or None, capture_output=True, text=True, timeout=3)
        return out.stdout.strip()
    except Exception:
        return ""


def pushes_to_main(command, cwd):
    for m in PUSH.finditer(command):
        try:
            words = shlex.split(m.group("rest"))
        except ValueError:
            words = m.group("rest").split()
        positional = [w for w in words if not w.startswith("-")]
        refspecs = positional[1:]
        if not refspecs:
            # bare `git push` / `git push origin` pushes the current branch
            if current_branch(cwd, m.group("pre")) in PROTECTED:
                return True
            continue
        for spec in refspecs:
            src, _, dst = spec.lstrip("+").rpartition(":") if ":" in spec else ("", "", spec.lstrip("+"))
            target = dst or src
            if target.removeprefix("refs/heads/") in PROTECTED:
                return True
            if target == "HEAD" and current_branch(cwd, m.group("pre")) in PROTECTED:
                return True
    return False


def pr_merge_targets_main(command, cwd):
    for m in PR_MERGE.finditer(command):
        try:
            words = shlex.split(m.group("rest"))
        except ValueError:
            return True
        selector, repo, skip = [], [], False
        for i, w in enumerate(words):
            if skip:
                skip = False
                continue
            if w in PR_MERGE_VALUE_FLAGS:
                skip = True
                if w in ("-R", "--repo") and i + 1 < len(words):
                    repo = ["-R", words[i + 1]]
                continue
            if w.startswith("--repo="):
                repo = ["-R", w.split("=", 1)[1]]
            elif not w.startswith("-") and not selector:
                selector = [w]
        try:
            out = subprocess.run(
                ["gh", "pr", "view", *selector, *repo, "--json", "baseRefName", "-q", ".baseRefName"],
                cwd=cwd or None, capture_output=True, text=True, timeout=10,
            )
            base = out.stdout.strip()
        except Exception:
            base = ""
        # fail closed: a PR whose base cannot be read is treated as targeting main
        if not base or base in PROTECTED:
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str(payload.get("tool_input", {}).get("command", ""))
    if pushes_to_main(command, payload.get("cwd")):
        sys.stderr.write(f"waves guard: {PUSH_TO_MAIN}\n")
        return 2
    if pr_merge_targets_main(command, payload.get("cwd")):
        sys.stderr.write(f"waves guard: {MERGE_TO_MAIN}\n")
        return 2
    for pattern, extra, reason in RULES:
        for match in pattern.finditer(command):
            if extra is None or extra(match):
                sys.stderr.write(f"waves guard: {reason}\n")
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
