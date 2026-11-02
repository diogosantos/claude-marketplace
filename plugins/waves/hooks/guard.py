#!/usr/bin/env python3
"""PreToolUse guard for the waves plugin.

Blocks the few shell commands that have caused real damage in multi-agent waves, in the
coordinator session and in every subagent:
  - writing git config (worktrees share .git/config; a scratch identity relabelled 155 commits)
  - killing processes by name (other agents and the owner run the same app concurrently)
  - synthetic OS input (clicks and keystrokes land in whichever window is frontmost)
  - force pushes
Exit 2 with the reason on stderr blocks the call; anything else lets it through.
"""
import json
import re
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


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str(payload.get("tool_input", {}).get("command", ""))
    for pattern, extra, reason in RULES:
        for match in pattern.finditer(command):
            if extra is None or extra(match):
                sys.stderr.write(f"waves guard: {reason}\n")
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
