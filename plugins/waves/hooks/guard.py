#!/usr/bin/env python3
"""PreToolUse guard for the waves plugin.

Blocks the few shell commands that have caused real damage in multi-agent waves, in the
coordinator session and in every subagent:
  - writing git config (worktrees share .git/config; a scratch identity relabelled 155 commits)
  - killing processes by name (other agents and the owner run the same app concurrently)
  - synthetic OS input (clicks and keystrokes land in whichever window is frontmost)
  - force pushes
  - pushes to main/master (work lands through pull requests)
  - merging a pull request whose base is main/master (only the codeowner merges into main),
    through `gh pr merge` or the REST/GraphQL API

The command line is parsed, not pattern-matched: it is split into the simple commands the
shell would run (across `;`, `&&`, `||`, `|`, newlines, `$(...)`, backticks, `bash -c`,
`eval` and heredocs fed to a shell), and each command is judged by its own arguments. Text
that is only data (a quoted commit message, a PR body in a heredoc, an `echo` argument)
never triggers a rule.

Exit 2 with the reason on stderr blocks the call; exit 0 lets it through. An internal error
exits 1 (shown to the user, does not block).
"""
import json
import os
import re
import shlex
import subprocess
import sys

PROTECTED = {"main", "master"}

GIT_CONFIG = (
    "git config writes are blocked: worktrees share .git/config, so a 'temporary' identity "
    "relabels every commit in the repository. Pass a one-off identity on the command line "
    "instead: git -c user.name=scratch -c user.email=scratch@invalid <command>."
)
KILL_BY_NAME = (
    "pkill/killall are blocked: other agents and the owner run the same programs. Stop only "
    "processes you started, by PID (kill <pid>)."
)
KILL_ALL = "kill -1 (every process) is blocked. Stop only processes you started, by PID."
SYNTHETIC_INPUT = (
    "Synthetic OS input is blocked: clicks and keys land in whichever window is frontmost, "
    "including other agents' windows and the owner's desktop. Use dev flags, headless UI "
    "tests, or an in-process event posted by the app itself when the brief allows it."
)
FORCE_PUSH = (
    "Force pushes are blocked. Merge or rebase onto the branch and push normally; if history "
    "must be rewritten, stop and report it to the owner."
)
PUSH_TO_MAIN = (
    "Pushing to main is blocked: work lands through pull requests. Push your own branch "
    "(git push -u origin <branch>) and open a PR into its base (the wave branch for a ticket)."
)
MERGE_TO_MAIN = (
    "Merging a pull request into main is blocked: only the codeowner merges into main. Leave the "
    "wave PR open, report its URL, and let the owner merge it."
)

SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
INTERPRETERS = SHELLS | {"python", "python3", "swift", "node", "ruby", "perl", "osascript", "jxa"}
WRAPPERS = {"env", "command", "builtin", "nohup", "time", "sudo", "exec", "nice", "caffeinate"}
CGEVENT = re.compile(r"\b(CGEventPost|CGEventCreate(Keyboard|Mouse)Event|AXUIElementPerformAction)\b")
OSASCRIPT_INPUT = re.compile(r"keystroke|key code|\bclick\b|System Events")
MAX_DEPTH = 5


class Block(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


# --- lookups (replaced in tests) -------------------------------------------------------------

def current_branch(cwd):
    try:
        out = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd or None,
                             capture_output=True, text=True, timeout=3)
        return out.stdout.strip()
    except Exception:
        return ""


def pr_base(selector, repo, cwd):
    """Base branch of the PR `gh pr merge <selector>` would merge ('' when unknown)."""
    try:
        out = subprocess.run(["gh", "pr", "view", *selector, *repo, "--json", "baseRefName",
                              "-q", ".baseRefName"],
                             cwd=cwd or None, capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


def api_pr_base(endpoint, cwd):
    """Base branch of the PR at REST endpoint `repos/<o>/<r>/pulls/<n>` ('' when unknown)."""
    try:
        out = subprocess.run(["gh", "api", endpoint, "--jq", ".base.ref"],
                             cwd=cwd or None, capture_output=True, text=True, timeout=10)
        return out.stdout.strip()
    except Exception:
        return ""


# --- splitting the command line --------------------------------------------------------------

HEREDOC = re.compile(r"<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][\w.-]*)\2")


def split_heredocs(text):
    """Remove heredoc bodies. Returns (text without bodies, [(opening line, body, quoted)]).

    `<<TAG` counts only outside quotes, so a commit message that mentions `<<EOF` cannot
    swallow the commands on the lines after it.
    """
    out, bodies, pending = [], [], []
    i, n, single, double, line_start = 0, len(text), False, False, 0
    while i < n:
        c = text[i]
        if c == "\\" and not single:
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
        elif c == "<" and not single and not double and (i == 0 or text[i - 1] != "<"):
            m = HEREDOC.match(text, i)
            if m:
                pending.append(m.groups())
                out.append(text[i:m.end()])
                i = m.end()
                continue
        elif c == "\n" and not single and not double and pending:
            opening = "".join(out)[line_start:]
            out.append("\n")
            i += 1
            for dash, quote, tag in pending:
                body = []
                while i < n:
                    j = text.find("\n", i)
                    j = n if j < 0 else j
                    line, i = text[i:j], j + 1
                    if (line.lstrip("\t") if dash else line) == tag:
                        break
                    body.append(line)
                bodies.append((opening, "\n".join(body), bool(quote)))
            pending = []
            line_start = len("".join(out))
            continue
        out.append(c)
        i += 1
        if c == "\n":
            line_start = len("".join(out))
    return "".join(out), bodies


def extract_substitutions(text):
    """Replace `$(...)` and backticks outside single quotes; return (text, [inner commands])."""
    out, subs = [], []
    i, n, single, double = 0, len(text), False, False
    while i < n:
        c = text[i]
        if c == "\\" and not single:
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
        elif not single and text.startswith("$(", i) and not text.startswith("$((", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                j += 1
            subs.append(text[i + 2:j - 1] if depth == 0 else text[i + 2:])
            out.append("SUBST")
            i = j
            continue
        elif c == "`" and not single:
            j = text.find("`", i + 1)
            j = n if j < 0 else j
            subs.append(text[i + 1:j])
            out.append("SUBST")
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out), subs


def strip_comments(text):
    """Drop shell comments: a `#` that starts a word, outside quotes, up to the end of the line."""
    out, i, n, single, double = [], 0, len(text), False, False
    while i < n:
        c = text[i]
        if c == "\\" and not single:
            out.append(text[i:i + 2])
            i += 2
            continue
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
        elif c == "#" and not single and not double and (i == 0 or text[i - 1] in " \t\n;&|()"):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def simple_commands(text):
    """Split a command line (no heredoc bodies, no substitutions) into argv lists."""
    try:
        lex = shlex.shlex(strip_comments(text), posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.commenters = ""  # shlex would end a word at any `#`, even mid-word (URLs, a#b)
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        # unbalanced quotes: the shell will refuse it too; judge the plain words
        tokens = text.replace("\n", " ; ").split()
    commands, argv, skip_target = [], [], False
    for tok in tokens:
        if skip_target:
            skip_target = False
            continue
        if tok and set(tok) <= set("();|&\n"):
            if argv:
                commands.append(argv)
            argv = []
        elif tok and set(tok) <= set("<>&"):
            skip_target = True
        else:
            argv.append(tok)
    if argv:
        commands.append(argv)
    return commands


def unwrap(argv):
    """Drop leading VAR=value assignments and wrappers such as env, command, nohup, sudo."""
    while argv:
        if re.match(r"^[A-Za-z_]\w*=", argv[0]):
            argv = argv[1:]
        elif os.path.basename(argv[0]) in WRAPPERS:
            argv = argv[1:]
            while argv and argv[0].startswith("-"):
                argv = argv[1:]
        else:
            break
    return argv


def resolve(cwd, path):
    if path == "-":
        return cwd
    return os.path.normpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(path)))


# --- judging one command ---------------------------------------------------------------------

def scan(text, cwd, depth=0):
    if depth > MAX_DEPTH:
        return
    text, bodies = split_heredocs(text)
    for _, body, quoted in bodies:
        if not quoted:
            for sub in extract_substitutions(body)[1]:
                scan(sub, cwd, depth + 1)
    text, subs = extract_substitutions(text)
    for sub in subs:
        scan(sub, cwd, depth + 1)
    for argv in simple_commands(text):
        cwd = check(unwrap(argv), cwd, depth)
    # a heredoc is code only when it feeds an interpreter (`bash <<EOF`, `osascript <<EOF`)
    for opening, body, _ in bodies:
        names = {os.path.basename(a[0]) for a in map(unwrap, simple_commands(opening)) if a}
        if names & SHELLS:
            scan(body, cwd, depth + 1)
        if names & INTERPRETERS:
            check_injected_input(body, "osascript" in names)


def check(argv, cwd, depth):
    if not argv:
        return cwd
    name, args = os.path.basename(argv[0]), argv[1:]
    if name == "cd":
        return resolve(cwd, args[0] if args else "~")
    if name in ("pkill", "killall"):
        raise Block(KILL_BY_NAME)
    if name == "kill":
        check_kill(args)
    if name in ("cliclick", "xdotool", "ydotool"):
        raise Block(SYNTHETIC_INPUT)
    if name in SHELLS:
        for i, a in enumerate(args):
            if re.fullmatch(r"-[a-zA-Z]*c[a-zA-Z]*", a) and i + 1 < len(args):
                scan(args[i + 1], cwd, depth + 1)
                break
    if name == "eval":
        scan(" ".join(args), cwd, depth + 1)
    if name in INTERPRETERS:
        check_injected_input(" ".join(args), name == "osascript")
    if name == "git":
        check_git(args, cwd)
    if name == "gh":
        check_gh(args, cwd)
    return cwd


def check_injected_input(code, osascript):
    if CGEVENT.search(code):
        raise Block("CGEvent/Accessibility input injection is blocked (synthetic OS input).")
    if osascript and OSASCRIPT_INPUT.search(code):
        raise Block("osascript keystrokes/clicks are blocked (synthetic OS input). Use dev flags "
                    "or headless UI tests instead.")


def check_kill(args):
    if args == ["-1"]:
        raise Block(KILL_ALL)
    rest = args
    if rest and rest[0] in ("-s", "-n"):
        rest = rest[2:]
    elif rest and rest[0].startswith("-") and rest[0] != "--":
        rest = rest[1:]  # the signal: `kill -1 1234` sends SIGHUP to 1234
    if rest and rest[0] == "--":
        rest = rest[1:]
    if "-1" in rest:
        raise Block(KILL_ALL)


GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
                  "--super-prefix"}


def check_git(args, cwd):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] in GIT_VALUE_OPTS:
            if args[i] == "-C" and i + 1 < len(args):
                cwd = resolve(cwd, args[i + 1])
            i += 2
        else:
            i += 1
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]
    if sub == "config":
        check_git_config(rest)
    elif sub == "push":
        check_push(rest, cwd)


CONFIG_READ_FLAGS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color",
                     "--get-colorbool", "--list", "-l", "--show-origin", "--show-scope"}
CONFIG_WRITE_FLAGS = {"--add", "--replace-all", "--unset", "--unset-all", "--rename-section",
                      "--remove-section", "--edit", "-e"}
CONFIG_VALUE_OPTS = {"-f", "--file", "--blob", "--type", "--default", "--comment", "--value"}


def check_git_config(rest):
    flags, positional, i = set(), [], 0
    while i < len(rest):
        a = rest[i]
        if a in CONFIG_VALUE_OPTS:
            i += 2
            continue
        if a.startswith("-"):
            flags.add(a.split("=", 1)[0])
        else:
            positional.append(a)
        i += 1
    if positional and positional[0] in ("get", "list"):
        return
    if flags & CONFIG_READ_FLAGS and not flags & CONFIG_WRITE_FLAGS:
        return
    if len(positional) == 1 and not flags & CONFIG_WRITE_FLAGS:
        return  # `git config user.name` prints the value
    if not positional and not flags & CONFIG_WRITE_FLAGS:
        return  # bare `git config` prints usage
    raise Block(GIT_CONFIG)


PUSH_VALUE_OPTS = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}


def check_push(rest, cwd):
    positional, force, every, dry_run, i = [], False, False, False, 0
    while i < len(rest):
        a = rest[i]
        if a == "--":
            positional += rest[i + 1:]
            break
        if a in PUSH_VALUE_OPTS:
            i += 2
            continue
        if a.startswith("--"):
            opt = a.split("=", 1)[0]
            if opt in ("--force", "--force-with-lease", "--force-if-includes"):
                force = True
            elif opt in ("--all", "--mirror", "--branches"):
                every = True
            elif opt == "--dry-run":
                dry_run = True
        elif a.startswith("-") and len(a) > 1:
            force = force or "f" in a[1:]
            dry_run = dry_run or "n" in a[1:]
        else:
            positional.append(a)
        i += 1
    refspecs = positional[1:]
    if force or any(s.startswith("+") for s in refspecs):
        raise Block(FORCE_PUSH)
    if dry_run:
        return
    if every:
        raise Block(PUSH_TO_MAIN)
    if not refspecs:
        if current_branch(cwd) in PROTECTED:
            raise Block(PUSH_TO_MAIN)
        return
    for spec in refspecs:
        src, _, dst = spec.partition(":")
        target = dst if ":" in spec else src
        if target in ("HEAD", "@") or "SUBST" in target:
            # `$(git branch --show-current)` and friends usually name the current branch
            target = current_branch(cwd)
        if target.removeprefix("refs/heads/") in PROTECTED:
            raise Block(PUSH_TO_MAIN)


PR_MERGE_VALUE_OPTS = {"-R", "--repo", "-b", "--body", "-F", "--body-file", "-t", "--subject",
                       "-A", "--author-email", "--match-head-commit"}
API_VALUE_OPTS = {"-X", "--method", "-H", "--header", "-f", "--raw-field", "-F", "--field",
                  "--input", "-q", "--jq", "-t", "--template", "--hostname", "--cache", "-p",
                  "--preview"}
API_PR_MERGE = re.compile(r"^/?(repos/[^/]+/[^/]+/pulls/\d+)/merge/?$")


def check_gh(args, cwd):
    if args[:2] == ["pr", "merge"]:
        check_pr_merge(args[2:], cwd)
    elif args[:1] == ["api"]:
        check_api(args[1:], cwd)


def check_pr_merge(rest, cwd):
    if "--help" in rest or "-h" in rest:
        return
    selector, repo, i = [], [], 0
    while i < len(rest):
        a = rest[i]
        if a in PR_MERGE_VALUE_OPTS:
            if a in ("-R", "--repo") and i + 1 < len(rest):
                repo = ["-R", rest[i + 1]]
            i += 2
            continue
        if a.startswith("--repo="):
            repo = ["-R", a.split("=", 1)[1]]
        elif not a.startswith("-") and not selector:
            selector = [a]
        i += 1
    base = pr_base(selector, repo, cwd)
    # fail closed: a PR whose base cannot be read is treated as targeting main
    if not base or base in PROTECTED:
        raise Block(MERGE_TO_MAIN)


def check_api(rest, cwd):
    method, endpoint, values, i = "", "", [], 0
    while i < len(rest):
        a = rest[i]
        if a in API_VALUE_OPTS:
            value = rest[i + 1] if i + 1 < len(rest) else ""
            if a in ("-X", "--method"):
                method = value
            else:
                values.append(value)
            i += 2
            continue
        if a.startswith("--method="):
            method = a.split("=", 1)[1]
        elif a.startswith("-X") and len(a) > 2:
            method = a[2:]
        elif a.startswith("-"):
            values.append(a)
        elif not endpoint:
            endpoint = a
        i += 1
    if endpoint.strip("/") == "graphql":
        if re.search(r"\b(mergePullRequest|enablePullRequestAutoMerge)\b", " ".join(values)):
            raise Block(MERGE_TO_MAIN)
        return
    m = API_PR_MERGE.match(endpoint)
    if m and method.upper() == "PUT":
        base = api_pr_base(m.group(1), cwd)
        if not base or base in PROTECTED:
            raise Block(MERGE_TO_MAIN)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str(payload.get("tool_input", {}).get("command", ""))
    try:
        scan(command, payload.get("cwd"))
    except Block as block:
        sys.stderr.write(f"waves guard: {block.reason}\n")
        return 2
    except Exception as error:  # a guard bug must not wedge every shell command
        sys.stderr.write(f"waves guard: internal error, command not checked: {error!r}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
