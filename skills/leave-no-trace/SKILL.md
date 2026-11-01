---
name: leave-no-trace
description: Use whenever you change files in a project, and before you tell the user a task is done. Keeps the repo free of things you made only for yourself while working - summary or report markdown files, scratch and debug scripts, .bak copies, command output dumps, debug prints, commented-out code.
---

# Leave no trace

The user should be able to read your diff and see only the change they asked for. Everything you made to help yourself think, test or debug goes away before you finish.

## While you work

- **Summaries go in your reply, not in a file.** Don't create `IMPLEMENTATION_SUMMARY.md`, `CHANGES.md`, `FIX_NOTES.md`, `TEST_RESULTS.md` or anything like them unless the user asked for that file.
- **Scratch scripts live outside the repo.** If you need a throwaway script to reproduce a bug or check an idea, put it in the system temp directory (`$TMPDIR`, `/tmp`) or delete it when you're done. If it turned out to be a useful test, move it into the real test suite with a proper name.
- **Git is the backup.** Don't make `file.bak`, `file.orig`, `file_old.py` or `file.copy.ts`. To compare with the old version, use `git diff` or `git show HEAD:path`.
- **Don't save command output into the repo** (`output.txt`, `results.json`, `test.log`). Read it and move on.
- **Debug prints are temporary.** `console.log`, `print(f"{x=}")`, `debugger`, `breakpoint()`, `binding.pry`, `dbg!`, `var_dump` come out before you finish. Logging the project actually wants goes through its logger.
- **Delete code instead of commenting it out.** The old version is in git history.

## Before you say you're done

1. Run `git status --short` and look at every new file. For each one, ask whether the user would expect it in this change.
2. Look at your diff (`git diff`) for debug prints, commented-out blocks and changes unrelated to the task (reformatting files you didn't need to touch, reordering imports, stray whitespace).
3. Remove what doesn't belong. If you kept something unusual on purpose, say so in your reply and why.
