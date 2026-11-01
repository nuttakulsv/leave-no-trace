# leave-no-trace

[English](README.md) · จากคนทำ [honest-tests](https://github.com/nuttakulsv/honest-tests) และ [chesterton](https://github.com/nuttakulsv/chesterton)

สั่ง coding agent ให้แก้บั๊กตัวเดียว มันก็แก้ให้ แต่พอเปิด `git status` ดูกลับเจอแบบนี้

```
?? IMPLEMENTATION_SUMMARY.md
?? test_login_fix.py
?? debug_session.py
?? src/auth.ts.bak
?? output.txt
 M src/auth.ts        <- โค้ดที่แก้ บวก console.log อีกสองบรรทัด กับโค้ดเก่าที่ comment ทิ้งไว้อีกก้อน
```

leave-no-trace เป็น hook ของ Claude Code (และมี skill ให้ agent ตัวอื่นใช้ด้วย) ที่ตรวจเจอของพวกนี้ก่อน agent จะบอกว่าเสร็จ แล้วให้มันเก็บกวาดเอง

## จับอะไรได้บ้าง

จับเฉพาะของที่โผล่มา**ระหว่าง session นี้** ไฟล์และสิ่งที่เราแก้ไว้ก่อน agent เริ่มทำงานจะไม่ถูกแตะ

| | ตัวอย่าง |
|---|---|
| ไฟล์สรุปหรือรายงาน | `IMPLEMENTATION_SUMMARY.md`, `FIX_NOTES.md`, `TEST_RESULTS.md`, `REFACTORING_PLAN.md` |
| สคริปต์ทดลอง | `debug_auth.py`, `scratch.js`, `repro.sh` และ `test_fix.py` / `verify.js` / `check_*.py` ที่วางไว้ชั้นบนสุดของ repo (เทสต์จริงใน `tests/` ไม่โดน) |
| ไฟล์สำรอง | `*.bak`, `*.orig`, `*.rej`, `config.old.yml`, `utils_backup.py`, `file~` |
| ผลลัพธ์จากคำสั่ง | `output.txt`, `results.json`, `nohup.out` และไฟล์ `*.log` / `*.patch` ใหม่ที่ git ไม่ได้ ignore ไว้ |
| ไฟล์ขยะของระบบ | `.DS_Store`, `Thumbs.db` |
| ของที่ใส่ไว้ตอน debug | `console.log`, `debugger`, `breakpoint()`, `pdb.set_trace()`, `print(f"{x=}")`, `binding.pry`, `dbg!`, `var_dump`, `// TEMP`, `# REMOVE ME` |
| โค้ดที่ comment ทิ้งไว้ | comment ติดกันตั้งแต่ 3 บรรทัดขึ้นไปที่หน้าตาเป็นโค้ด |

ตอนที่ agent จะจบงาน มันจะได้รายการนี้กลับไป

```
leave-no-trace: before you finish, clean up after yourself. These were left in the project during this session:

- IMPLEMENTATION_SUMMARY.md  summary or report doc
- src/auth.ts.bak  backup copy
- src/auth.ts:3  debug leftover: console.log('token', token)
- src/auth.ts:7  commented-out code: 4 lines, starting `const old = legacyCheck(user)`
...
```

ตัว hook ไม่ลบอะไรเองเลย agent เป็นคนตัดสินใจ ถ้าจะเก็บอะไรไว้ต้องบอกเราว่าเพราะอะไร แต่ละรายการเตือนแค่ครั้งเดียว `console.log` ที่ตั้งใจใส่ไว้ใน CLI จึงไม่ทำให้ agent ติดวนอยู่ที่เดิม

## ติดตั้ง

Claude Code (ได้ทั้ง hook และ skill)

```
/plugin marketplace add nuttakulsv/leave-no-trace
/plugin install leave-no-trace@leave-no-trace
```

Codex, Cursor หรือ agent อื่นที่อ่าน SKILL.md ได้ (ได้แค่ skill ไม่มี hook)

```
npx skills add nuttakulsv/leave-no-trace
```

## ใช้เองหรือใส่ใน CI

ตัวตรวจเดียวกันนี้ใช้ได้โดยไม่ต้องมี agent ต้องมีแค่ `python3` กับ `git`

```
python3 hooks/litter.py --check          # ตรวจสิ่งที่ยังไม่ commit และไฟล์ที่ยังไม่ได้ track
python3 hooks/litter.py --check main     # ตรวจทุกอย่างตั้งแต่ main เช่นใน job ของ PR
```

ถ้าเจออะไรจะจบด้วย exit code 1 เอาไปใส่ใน pre-commit hook หรือขั้นตอนใน CI ได้เลย

## ทำงานยังไง

ตอนเริ่ม session มันจะเก็บสภาพของ working tree ไว้ด้วย `git stash create` (คำสั่งนี้ไม่แตะไฟล์ของเราและไม่เพิ่มอะไรใน stash list) และจดว่ามีไฟล์ที่ยังไม่ track อะไรอยู่แล้วบ้าง พอ agent จะหยุด ก็เทียบกับสภาพตอนเริ่ม แล้วดูไฟล์ใหม่กับบรรทัดที่เพิ่มเข้ามา ทั้งหมดทำในเครื่อง ไม่ต่อเน็ตและไม่มี dependency

## ข้อจำกัด

- ใช้การจับ pattern ไฟล์ชื่อ `check_permissions.py` ที่อยู่ชั้นบนสุดอาจเป็นโค้ดจริงก็ได้ ซึ่ง agent ก็บอกได้ ส่วนไฟล์ทดลองที่ตั้งชื่อว่า `helpers2.py` จะหลุดไป
- `print()` ของ debug ตรวจแค่ในไฟล์ซอร์สโค้ด และใน Python จะนับเฉพาะ `print()` ที่ดูเป็นการ debug (`DEBUG`, `HERE`, `{x=}`) เพราะโปรแกรม Python จำนวนมากตั้งใจ print อยู่แล้ว
- ไฟล์ที่ git ignore ไว้จะไม่ถูกตรวจ เพราะยังไงก็ไม่หลุดเข้าไปใน commit

## รันเทสต์

```
python3 hooks/litter.py --test
```

## License

MIT
