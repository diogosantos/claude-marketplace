"""Tests for hooks/guard.py. Run: python3 -m unittest discover -s plugins/waves/tests"""
import io
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
import guard  # noqa: E402


def run(command, branch="SW-1-feature", pr_base="wave/w1", api_base="wave/w1"):
    """Exit code the hook returns for `command`, with git/gh lookups faked."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/repo"})
    with mock.patch.object(guard, "current_branch", return_value=branch), \
            mock.patch.object(guard, "pr_base", return_value=pr_base), \
            mock.patch.object(guard, "api_pr_base", return_value=api_base), \
            mock.patch.object(sys, "stdin", io.StringIO(payload)), \
            mock.patch.object(sys, "stderr", io.StringIO()):
        return guard.main()


class Blocked(unittest.TestCase):
    def assertBlocked(self, command, **kw):
        self.assertEqual(run(command, **kw), 2, command)

    def test_push_to_main(self):
        for c in ["git push origin main", "git push origin HEAD:refs/heads/main", "git push origin :main",
                  "git push origin --delete main", "git push --all origin", "git push origin master",
                  "git push -u origin feature main"]:
            self.assertBlocked(c)

    def test_push_current_branch_on_main(self):
        for c in ["git push", "git push origin", "git push origin HEAD", "git push origin @",
                  'git push origin "$(git branch --show-current)"']:
            self.assertBlocked(c, branch="main")

    def test_push_behind_global_options_and_wrappers(self):
        for c in ["git -c user.name=x push origin main", "git --no-pager push origin main",
                  "git -C /elsewhere push origin main", "git --git-dir=.git push origin main",
                  "env FOO=1 git push origin main", "FOO=1 command git push origin main",
                  "/usr/bin/git push origin main"]:
            self.assertBlocked(c)

    def test_push_inside_compound_commands(self):
        for c in ["cd /tmp && git push origin main", "true; git push origin main", "echo ok\ngit push origin main",
                  "false || git push origin main", "echo $(git push origin main)", "echo `git push origin main`",
                  "echo a#b && git push origin main", "curl https://x/#frag; git push origin main",
                  "echo x # comment\ngit push origin main",
                  'git commit -m "see <<EOF"\ngit push origin main\nEOF',
                  "cat <<'A' <<B\none\nA\ntwo\nB\ngit push origin main",
                  'bash -c "git push origin main"', "sh -lc 'git push origin main'", "eval git push origin main",
                  "bash <<'EOF'\ngit push origin main\nEOF", 'echo "$(git push origin main)"']:
            self.assertBlocked(c)

    def test_force_push(self):
        for c in ["git push --force origin x", "git push -f origin x", "git push -uf origin x",
                  "git push --force-with-lease origin x", "git push --force-with-lease=x:abc origin x",
                  "git push origin +x", "git push origin +x:x"]:
            self.assertBlocked(c)

    def test_pr_merge_into_main(self):
        for c in ["gh pr merge 60 --merge", "gh pr merge --auto --merge", "gh pr merge 60 -R o/r --squash",
                  "cd /x && gh pr merge 1"]:
            self.assertBlocked(c, pr_base="main")

    def test_pr_merge_fails_closed(self):
        self.assertBlocked("gh pr merge 60", pr_base="")

    def test_api_merge_into_main(self):
        for c in ["gh api -X PUT repos/o/r/pulls/60/merge", "gh api --method PUT /repos/o/r/pulls/60/merge",
                  "gh api --method=PUT repos/{owner}/{repo}/pulls/60/merge -f merge_method=merge",
                  "gh api -XPUT repos/o/r/pulls/60/merge"]:
            self.assertBlocked(c, api_base="main")
        self.assertBlocked("gh api -X PUT repos/o/r/pulls/60/merge", api_base="")
        self.assertBlocked("gh api graphql -f query='mutation { mergePullRequest(input: {}) { clientMutationId } }'")
        self.assertBlocked("gh api graphql -f query='mutation { enablePullRequestAutoMerge(input: {}) { x } }'")

    def test_git_config_writes(self):
        for c in ["git config user.name x", "git config --global user.email a@b", "git config set user.name x",
                  "git config --unset user.name", "git config --add a.b c", "git -C /x config user.name x",
                  "git config -e"]:
            self.assertBlocked(c)

    def test_kill(self):
        for c in ["pkill StationWarp", "killall Xcode", "/usr/bin/pkill -f x", "kill -9 -1", "kill -- -1", "kill -1",
                  "kill -s KILL -1"]:
            self.assertBlocked(c)

    def test_synthetic_input(self):
        for c in ["cliclick c:10,10", "xdotool click 1",
                  "osascript -e 'tell application \"System Events\" to keystroke \"a\"'",
                  "python3 -c 'import Quartz; Quartz.CGEventPost(0, e)'",
                  "osascript <<'EOF'\ntell application \"System Events\" to key code 36\nEOF",
                  "swift - <<EOF\nCGEventPost(.cghidEventTap, e)\nEOF"]:
            self.assertBlocked(c)


class Allowed(unittest.TestCase):
    def assertAllowed(self, command, **kw):
        self.assertEqual(run(command, **kw), 0, command)

    def test_regressions_from_0_2_0(self):
        # a PR body that mentions the blocked commands is data, not a command
        self.assertAllowed("gh pr create --base main --body-file - <<'EOF'\nThe hook blocks `gh pr merge` on PRs into "
                           "main and `git push --force`.\nEOF", branch="main")
        self.assertAllowed("printf '%s' 'git push origin main'", branch="main")
        self.assertAllowed("git push -q && gh api -X POST repos/o/r/pulls/1/comments/2/replies -f body=Fixed")
        self.assertAllowed('git commit -m "Document that git push origin main --force is blocked"', branch="main")

    def test_push_own_branch(self):
        for c in ["git push", "git push -u origin SW-1-feature", "git push origin --delete develop",
                  "git push origin HEAD", "git -c http.extraHeader=x push origin SW-1-feature 2>&1 | tail -1",
                  "git push origin main --dry-run", "git push -n origin main"]:
            self.assertAllowed(c)

    def test_pr_merge_into_wave_branch(self):
        self.assertAllowed("gh pr merge SW-1-feature --merge --delete-branch", pr_base="wave/w1")
        self.assertAllowed("gh pr merge --help", pr_base="")

    def test_api_reads_and_other_writes(self):
        self.assertAllowed("gh api repos/o/r/pulls/60/merge", api_base="main")
        self.assertAllowed("gh api -X PUT repos/o/r/pulls/60/merge", api_base="wave/w1")
        self.assertAllowed("gh api repos/o/r/pulls/60/reviews --jq '.[].state'")
        self.assertAllowed("gh api graphql -f query='{ viewer { login } }'")

    def test_git_config_reads(self):
        for c in ["git config --get user.name", "git config user.name", "git config --list", "git config -l",
                  "git config get user.name", "git config list --show-origin", "git config --global --get-all a.b",
                  "git -c user.name=scratch -c user.email=scratch@invalid commit -m x"]:
            self.assertAllowed(c)

    def test_kill_by_pid(self):
        for c in ["kill 1234", "kill -9 1234", "kill -1 1234", "kill $P", "kill -0 $P 2>/dev/null || break"]:
            self.assertAllowed(c)

    def test_mentions_are_not_commands(self):
        for c in ["grep -rn CGEventPost Sources", "echo 'pkill is blocked'", "rg 'System Events' docs",
                  "# git push origin main --force", "echo done  # then pkill nothing",
                  "cat > notes.md <<'EOF'\nNever run pkill or cliclick.\nEOF"]:
            self.assertAllowed(c)

    def test_non_bash_and_garbage(self):
        payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/x"}})
        with mock.patch.object(sys, "stdin", io.StringIO(payload)):
            self.assertEqual(guard.main(), 0)
        self.assertAllowed('echo "unbalanced')


if __name__ == "__main__":
    unittest.main()
