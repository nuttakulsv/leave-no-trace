# leave-no-trace

[ภาษาไทย](README.th.md) · From the maker of [honest-tests](https://github.com/nuttakulsv/honest-tests) and [chesterton](https://github.com/nuttakulsv/chesterton)

You ask a coding agent to fix one bug. It fixes the bug, and then your `git status` looks like this:

```
?? IMPLEMENTATION_SUMMARY.md
?? test_login_fix.py
?? debug_session.py
?? src/auth.ts.bak
?? output.txt
 M src/auth.ts        <- the fix, plus two console.logs and a block of commented-out code
```

leave-no-trace is a Claude Code hook (plus a skill for any agent) that notices this before the agent says "done" and makes it clean up after itself.

## What it catches

Only things that showed up **during this session**. Files and edits you had before the agent started are left alone.

| | Examples |
|---|---|
| Summary and report docs | `IMPLEMENTATION_SUMMARY.md`, `FIX_NOTES.md`, `TEST_RESULTS.md`, `REFACTORING_PLAN.md` |
| Scratch scripts | `debug_auth.py`, `scratch.js`, `repro.sh`, and `test_fix.py` / `verify.js` / `check_*.py` at the top of the repo (real tests in `tests/` are fine) |
| Backup copies | `*.bak`, `*.orig`, `*.rej`, `config.old.yml`, `utils_backup.py`, `file~` |
| Command output | `output.txt`, `results.json`, `nohup.out`, new `*.log` / `*.patch` files that git isn't ignoring |
| System junk | `.DS_Store`, `Thumbs.db` |
| Debug leftovers | `console.log`, `debugger`, `breakpoint()`, `pdb.set_trace()`, `print(f"{x=}")`, `binding.pry`, `dbg!`, `var_dump`, `// TEMP`, `# REMOVE ME` |
| Commented-out code | three or more commented lines in a row that read like code |

When the agent tries to finish, it gets the list back:

```
leave-no-trace: before you finish, clean up after yourself. These were left in the project during this session:

- IMPLEMENTATION_SUMMARY.md  summary or report doc
- src/auth.ts.bak  backup copy
- src/auth.ts:3  debug leftover: console.log('token', token)
- src/auth.ts:7  commented-out code: 4 lines, starting `const old = legacyCheck(user)`

Delete anything that was only for you while you worked ... If something here belongs in the project
(the user asked for it, or it's real code), keep it and say so in your reply. Each item is flagged once.
```

It never deletes anything itself. The agent decides, and if it keeps something it has to tell you why. Each item is flagged once, so an intentional `console.log` in a CLI won't trap the agent in a loop.

## Install

Claude Code (hook and skill):

```
/plugin marketplace add nuttakulsv/leave-no-trace
/plugin install leave-no-trace@leave-no-trace
```

Codex, Cursor, or anything else that reads SKILL.md (skill only, no hook):

```
npx skills add nuttakulsv/leave-no-trace
```

## Use it yourself, or in CI

The same check works without an agent. It needs `python3` and `git`, nothing else:

```
python3 hooks/litter.py --check          # your uncommitted changes and untracked files
python3 hooks/litter.py --check main     # everything since main, e.g. in a PR job
```

It exits 1 if it finds something, so you can drop it into a pre-commit hook or a CI step.

## How it works

At the start of a session it takes a snapshot of the working tree with `git stash create` (this doesn't touch your files or your stash list) and notes which untracked files already exist. When the agent stops, it diffs against that snapshot and looks at new files and added lines. Everything is local. No network, no dependencies.

## Limits

- It's pattern matching. A file called `check_permissions.py` at the top of your repo might be real, and the agent can say so. A scratch file named `helpers2.py` gets through.
- Debug prints are only checked in source files, and `print()` in Python only when it looks like debugging (`DEBUG`, `HERE`, `{x=}`), since plenty of Python programs print on purpose.
- Files git ignores are not checked. If they're ignored, they won't end up in your commit anyway.

## Tests

```
python3 hooks/litter.py --test
```

## License

MIT
