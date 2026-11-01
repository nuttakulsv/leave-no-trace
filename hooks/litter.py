#!/usr/bin/env python3
"""leave-no-trace: catch what a coding agent leaves behind.

SessionStart: remember what the repo looked like when the session began.
Stop:         look at what changed since then. Summary docs nobody asked for, scratch scripts,
              backup copies, debug prints and commented-out code get sent back to the agent once,
              to delete or explain.

    python3 litter.py --check [BASE]   scan your own changes (default: against HEAD, plus untracked files)
    python3 litter.py --test           self-check
"""
import json
import os
import re
import subprocess
import sys

IGNORED = re.compile(r"(^|/)(node_modules|vendor|dist|build|coverage|\.next|\.venv|venv|target)/|\.lock$|-lock\.(json|ya?ml)$|\.min\.js$")
TEST_DIR = re.compile(r"(^|/)(tests?|__tests__|specs?|e2e|testing)/")
SOURCE = re.compile(r"\.(py|[cm]?[jt]sx?|vue|svelte|go|rs|rb|php|java|kt|kts|scala|swift|cs|c|cc|cpp|h|hpp|ex|exs|dart|lua|sh)$")

# new files: (what it is, pattern on the path)
FILES = [(label, re.compile(rx)) for label, rx in [
    ("summary or report doc", r"(^|/)[A-Z0-9_ -]*(SUMMARY|REPORT|IMPLEMENTATION|ANALYSIS|INVESTIGATION|FINDINGS|PROGRESS|STATUS"
                              r"|COMPLETE|COMPLETED|DONE|RESULTS|FIXES|FIX|CHANGES_MADE|WALKTHROUGH|REFACTOR(ING)?_PLAN"
                              r"|NEXT_STEPS|NOTES)[A-Z0-9_ -]*\.(md|txt)$"),
    # unmistakable names anywhere; names like check_*.py only at the top level, where real modules rarely live
    ("scratch script", r"((^|/)(debug|scratch|tmp|temp|try|repro|playground|sandbox)|^(verify|check|test|demo|example|quick|foo))"
                       r"([_-][^/]*)?\.(py|[cm]?[jt]s|sh|rb|go|php)$"),
    ("backup copy", r"\.(bak|orig|rej|old|backup|swp)$|~$|[._-](backup|copy|old)\.[a-z0-9]+$"),
    ("command output", r"(^|/)(out|output|result|results|dump|log|nohup)\d*\.(txt|json|html|csv|out)$|\.(log|patch|diff)$"),
    ("system junk", r"(^|/)(\.DS_Store|Thumbs\.db|desktop\.ini)$"),
]]

# added lines in source files
DEBUG = re.compile(
    r"\bconsole\.(log|debug|dir|trace|table|time|timeEnd)\s*\(|^\s*debugger\s*;?\s*$"
    r"|\bbreakpoint\(\)|\b(i?pdb|pudb)\.set_trace\(|^\s*import\s+i?pdb\b|^\s*from\s+i?pdb\s+import"
    r"|^\s*print\(\s*f?['\"](DEBUG|debug|>>>|-->|HERE|here|XXX)|^\s*print\(\s*f['\"][^'\"]*=\}"
    r"|\bbinding\.(pry|irb)\b|^\s*byebug\b|\bdbg!\(|\bvar_dump\(|^\s*dd\(|\bspew\.Dump\("
    r"|\bfmt\.Print(ln|f)?\(\s*\"(DEBUG|debug)|System\.(out|err)\.println\(\s*\"(DEBUG|debug)"
    r"|(//|#)\s*(DEBUG|TEMP|TEMPORARY|REMOVE ME|REMOVEME|DELETE ME|DO NOT COMMIT|NOCOMMIT)\b"
)
COMMENT = re.compile(r"^\s*(//+|#+|--)\s?(.*)$")
CODEISH = re.compile(
    r"^(return\b|if\s*\(|if\s+\S.*:$|elif\b|else\b|for\s*\(|for\s+\w+\s+in\b|while\b|const\s|let\s|var\s|def\s|async\s|await\s"
    r"|class\s|import\s|from\s+\S+\s+import\b|try\b|except\b|catch\b|throw\b|raise\b|func\s|fn\s|pub\s|self\.|this\."
    r"|[\w.\[\]'\"]+\s*[+\-*/]?=\s*\S|[\w.]+\(.*\)\s*;?$|[})\]]+[;,]?$)"
)

STOP_REASON = """leave-no-trace: before you finish, clean up after yourself. These were left in the project during this session:

{list}

Delete anything that was only for you while you worked: scratch scripts, summary docs, backups, output files, debug prints, commented-out code. Put summaries in your reply, not in a file. If something here belongs in the project (the user asked for it, or it's real code), keep it and say so in your reply. Each item is flagged once."""


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, errors="replace")
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def parse_diff(text):
    """Unified diff (-U0) -> {path: {"added": [(line, text)], "new": bool}}"""
    files, cur, in_hunk, line_no = {}, None, False, 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", line)
            cur = files.setdefault(m.group(2), {"added": [], "new": False}) if m else None
            in_hunk = False
        elif cur is None:
            continue
        elif not in_hunk and line.startswith("new file mode"):
            cur["new"] = True
        elif line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            line_no, in_hunk = (int(m.group(1)) if m else 0), True
        elif in_hunk and line.startswith("+"):
            cur["added"].append((line_no, line[1:]))
            line_no += 1
    return files


def commented_code(added):
    """Runs of 3+ consecutive added comment lines that read like code."""
    out, run = [], []
    for n, text in added + [(None, "")]:
        m = COMMENT.match(text)
        body = m.group(2).strip() if m else ""
        if m and body and CODEISH.match(body) and (not run or run[-1][0] == n - 1):
            run.append((n, body))
            continue
        if len(run) >= 3:
            out.append((run[0][0], f"{len(run)} lines, starting `{run[0][1][:80]}`"))
        run = [(n, body)] if m and body and CODEISH.match(body) else []
    return out


def scan(files):
    out = []
    for path, f in sorted(files.items()):
        if IGNORED.search(path):
            continue
        if f["new"]:
            for label, rx in FILES:
                if rx.search(path) and not (label == "scratch script" and TEST_DIR.search(path)):
                    out.append((path, None, label, ""))
                    break
        if not SOURCE.search(path):
            continue
        for n, text in f["added"]:
            if DEBUG.search(text):
                out.append((path, n, "debug leftover", text.strip()))
        out += [(path, n, "commented-out code", what) for n, what in commented_code(f["added"])]
    return out


def untracked(top):
    return [p for p in (git(top, "ls-files", "--others", "--exclude-standard", "-z") or "").split("\0") if p][:500]


def read_lines(path):
    try:
        if os.path.getsize(path) > 512_000:
            return []
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError):
        return []
    return [] if "\0" in text else list(enumerate(text.splitlines(), 1))


def changes(top, base, known_untracked):
    if not base or git(top, "cat-file", "-e", base) is None:
        base = git(top, "rev-parse", "-q", "--verify", "HEAD") or git(top, "hash-object", "-t", "tree", "/dev/null")
    files = parse_diff(git(top, "diff", "--no-color", "--no-ext-diff", "--unified=0", "--no-renames", base) or "")
    if known_untracked is not None:  # without a baseline we can't tell new files from the user's own
        for path in untracked(top):
            if path not in known_untracked and not IGNORED.search(path):
                files[path] = {"added": read_lines(os.path.join(top, path)), "new": True}
    return files


def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def save(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(state, fh)


def key(f):
    return f"{f[0]}|{f[2]}|{f[3]}"


def fmt(f):
    path, line, label, snippet = f
    return f"- {path}:{line}  {label}" + (f": {snippet[:120]}" if snippet else "") if line else f"- {path}  {label}"


def handle(data):
    cwd = data.get("cwd") or os.getcwd()
    gitdir, top = git(cwd, "rev-parse", "--absolute-git-dir"), git(cwd, "rev-parse", "--show-toplevel")
    if not gitdir or not top:
        return
    state_path = os.path.join(gitdir, "leave-no-trace", re.sub(r"[^\w.-]", "_", data.get("session_id") or "default") + ".json")
    state = load(state_path)
    event = data.get("hook_event_name")

    if event == "SessionStart" and "base" not in state:
        # stash create snapshots the working tree as a loose commit; files and stash list are untouched
        base = (git(top, "-c", "user.name=leave-no-trace", "-c", "user.email=leave-no-trace@localhost", "stash", "create")
                or git(top, "rev-parse", "-q", "--verify", "HEAD") or "")
        save(state_path, {"base": base, "untracked": untracked(top)})

    elif event == "Stop":
        known = set(state["untracked"]) if "untracked" in state else None
        reported = set(state.get("reported", []))
        new = [f for f in scan(changes(top, state.get("base"), known)) if key(f) not in reported]
        if new:
            state["reported"] = sorted(reported | {key(f) for f in new})
            save(state_path, state)
            print(json.dumps({"decision": "block", "reason": STOP_REASON.format(list="\n".join(map(fmt, new[:30])))}))


def check(base=None):
    top = git(os.getcwd(), "rev-parse", "--show-toplevel")
    if not top:
        sys.exit("not inside a git repository")
    found = scan(changes(top, base or "HEAD", set()))
    print("\n".join(map(fmt, found)) or "clean")
    return 1 if found else 0


def test():
    import contextlib
    import io
    import tempfile

    def put(path, text):
        p = os.path.join(root, path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)

    def hook(event):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handle({"hook_event_name": event, "session_id": "t", "cwd": root})
        return buf.getvalue()

    with tempfile.TemporaryDirectory() as root:
        g = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, check=True)  # noqa: E731
        g("init", "-q")
        g("config", "user.email", "t@t")
        g("config", "user.name", "t")
        put("src/auth.ts", "export function login(user) {\n  return check(user)\n}\n")
        put("app.py", "def main():\n    print('hello')\n")
        put(".gitignore", "*.log\n")
        g("add", ".")
        g("commit", "-qm", "base")
        put("my_notes.md", "# mine\n")                                        # the user's, before the session
        put("src/auth.ts", "export function login(user) {\n  console.log('user', user)\n  return check(user)\n}\n")
        assert hook("SessionStart") == ""

        # the "agent" works, and leaves a mess
        put("src/auth.ts", "export function login(user) {\n  console.log('user', user)\n  debugger\n"
                           "  // const old = legacyCheck(user)\n  // if (!old) {\n  //   return false\n  // }\n"
                           "  // Checks the session first, then the token.\n  return check(user)\n}\n")
        put("IMPLEMENTATION_SUMMARY.md", "# Summary\nI fixed the login.\n")
        put("test_login_fix.py", "from app import main\nmain()\n")
        put("tests/test_login.py", "def test_login():\n    assert True\n")          # real test: fine
        put("src/auth.ts.bak", "old\n")
        put("debug.log", "ignored by .gitignore\n")
        put("output.txt", "...\n")
        put("app.py", "def main():\n    print(f'{user=}')\n    print('hello')\n    breakpoint()\n")
        put("docs/guide.md", "# Usage\n\n# install\n# run\n# deploy\n")                 # markdown headings: fine

        out = hook("Stop")
        assert '"decision": "block"' in out, out
        for want in ["IMPLEMENTATION_SUMMARY.md  summary or report doc", "test_login_fix.py  scratch script",
                     "src/auth.ts.bak  backup copy", "output.txt  command output", "src/auth.ts:3  debug leftover",
                     "src/auth.ts:4  commented-out code: 4 lines", "app.py:2  debug leftover", "app.py:4  debug leftover"]:
            assert want in out, (want, out)
        for clean in ["my_notes.md", "tests/test_login.py", "debug.log", "docs/guide.md", "src/auth.ts:2", "Checks the session"]:
            assert clean not in out, (clean, out)
        assert hook("Stop") == "", "the same findings must not block twice"
        put("scratch.js", "console.log(1)\n")
        out = hook("Stop")
        assert "scratch.js  scratch script" in out and "scratch.js:1  debug leftover" in out and "IMPLEMENTATION" not in out, out

    for rx_label, path, hit in [("summary or report doc", "FIX_SUMMARY.md", True), ("summary or report doc", "README.md", False),
                                ("summary or report doc", "CHANGELOG.md", False), ("scratch script", "verify_auth.js", True),
                                ("scratch script", "src/verify_auth.js", False), ("scratch script", "src/debug_auth.js", True),
                                ("scratch script", "src/checkout.ts", False), ("scratch script", "src/testing_utils.py", False),
                                ("backup copy", "config.old.yml", True), ("backup copy", "golden.json", False)]:
        rx = dict(FILES)[rx_label]
        assert bool(rx.search(path)) == hit, (rx_label, path)
    print("ok")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        test()
    elif sys.argv[1:2] == ["--check"]:
        sys.exit(check(sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        try:
            handle(json.load(sys.stdin))
        except Exception as e:  # a broken hook must never break the session
            print(f"leave-no-trace: {e}", file=sys.stderr)
