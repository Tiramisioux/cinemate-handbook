# Repository and tooling traps

Four traps that cost real time in a single session, none of which are about the camera. They
are about the repository and the tools around it: a filter that rewrites files on the way
into the index, a UI element that had never been connected to anything, a retry loop that
destroyed the evidence needed to debug something else, and the guards that caught the
mistakes the others didn't.

## 1. `.gitattributes` declares LFS; the repo has nothing in LFS

`.gitattributes` declares three patterns as LFS-managed:

```
*.jpg filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.ipynb filter=lfs diff=lfs merge=lfs -text
```

**But the repo stores its images as plain binaries and `git lfs ls-files` is empty.** The
attribute and the content disagree, and the consequence is permanent: to diff a working-tree
file against a stored blob, git runs the clean filter on the worktree copy first. The filter
returns a pointer, the stored blob is a real PNG, so the two never match. Every image reads
as modified on every checkout, forever, with no way to clean it.

The modification is genuinely phantom — worktree and committed blob are byte-identical:

```
$ shasum -a 256 docs/images/gui-i2c.png            # b4424b4d...
$ git cat-file -p HEAD:docs/images/gui-i2c.png | shasum -a 256   # b4424b4d...
$ git diff -- docs/images/gui-i2c.png
Binary files a/docs/images/gui-i2c.png and b/docs/images/gui-i2c.png differ
```

### How it did damage

`git add -u` stages every tracked file that git believes is modified — which here means
every image in the repo, always. One commit swept four of them in and **committed 130-byte
pointer files over real PNGs**, including `docs/images/camera-stack3.png`, the figure on the
landing pages `docs/readme.md` and `docs/cinemate-stack.md`. Nothing failed. The commit was
about an unrelated I²C pane; the images were collateral, and a later commit restored them
from the working tree, which still held the real files.

**Do not use `git add -u` in this repo.** Stage paths explicitly.

### Neutralising the filter: `filter.lfs.clean` is not the knob

This is the part that wastes the time. `-c filter.lfs.clean=cat` looks like it disables the
filter. It does not: `filter.<driver>.process` takes precedence over `clean`/`smudge`, and
`git lfs install` writes all three into the global config. The `clean` override is accepted,
ignored, and **exits 0** — you get a pointer and no warning.

Measured directly on `git 2.50.1` / `git-lfs 3.7.1`, adding a 5000-byte PNG under an
LFS attribute:

| Invocation | Exit | Staged blob |
|---|---|---|
| `git add a.png` | 0 | ~130-byte pointer |
| `git -c filter.lfs.clean=cat add a.png` | 0 | ~130-byte pointer |
| `git -c filter.lfs.required=false add a.png` | 0 | ~130-byte pointer |
| `git -c filter.lfs.process= add a.png` | 128 | nothing — `fatal: clean filter 'lfs' failed` |
| `git -c filter.lfs.process= -c filter.lfs.required=false add a.png` | 0 | **5000 bytes — the real file** |

Two things to take from the table. Clearing `process` is necessary but **not sufficient**:
because `git lfs install` also sets `filter.lfs.required=true`, an empty process command is a
hard failure rather than a bypass, so `required=false` has to come with it. And the only
silent row is the one that looks like the fix — every genuinely broken invocation either
fails loudly or stages the real bytes.

Pointer size varies with the digit count of the recorded `size`, so the pointers in this
repo's history are 130 bytes and a scratch reproduction's were 129. Neither number is a
constant to test against; the magic first line is (`version https://git-lfs.github.com/spec/v1`).

### Always verify after staging

```
git cat-file -s :docs/images/whatever.png
```

Six figures means the real image. Three means you just staged a pointer. Check the *index*
(`:path`), not the commit — after the commit it is history.

### The underlying inconsistency is still there

The attribute-versus-content mismatch has not been resolved; it is a migration decision
(either move the images into LFS, or drop the three patterns from `.gitattributes`), not
something to paper over per commit. Until it is resolved, **nothing checks for this** — there
is no LFS or pointer guard anywhere in `tools/`, `.github/workflows/`, or `_test/`. By the
house rule that a check beats a comment, the cheap guard is a test asserting that no tracked
file begins with the LFS pointer magic while `git lfs ls-files` is empty; it would have
turned that commit red instead of shipping four broken figures. See
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md).

## 2. The restart console was a simulation

**The settings editor's restart console replayed a hardcoded array of log lines on a
`setTimeout` with random jitter.** It read as streaming output and was nothing of the kind,
and the fabricated lines contradicted the machine they appeared on: two cameras on a
one-camera rig, `phase_lock engaged` when phase lock ships off, Flask on `:80` when it serves
`:5000`, and a fixed `iso 800 · 172.8° · 25 fps` regardless of the camera's actual state. The
card above it promised "the real startup sequence". The operator spotted it, not a test.

A fake progress display is worse than no display: it is confidently wrong at exactly the
moment someone is trying to work out whether the camera came back. This is
[`../conventions/philosophy.md`](../conventions/philosophy.md)'s "the operator must never be
shown a plausible wrong number", in its most literal form.

### Why there was nothing to attach to

Two obvious streams both turn out to be dead ends, and it is worth knowing that before
looking:

- **`log_queue` never reaches the app factory.** `setup_logging()` in `src/module/logger.py`
  creates it and returns it; `src/main.py` keeps it local, handing it to
  `get_recent_log_lines()` and offering it to `serial_handler`. The Flask app is never given
  it.
- **`/api/v1/events` carries Redis keys, not logs.** Its generator in `src/module/app/api.py`
  subscribes to `redis_parameter_changed` and emits `data: key=value`.

### Tail the file, not the queue

The answer is `GET /settings-editor/api/logs` (`stream_logs()` in
`src/module/app/settings_editor.py`): the backlog read by seeking backwards through
`system.log` in `_tail_lines()`, then appended lines, with rotation handled by watching the
inode.

**The file is tailed rather than the logger's queue being shared out, and that is a design
constraint rather than a preference.** The queue has a single consumer, so a second reader
would steal records from whoever is already draining it, and every additional browser tab
would compete for the same lines. A file has as many readers as it likes. If you are ever
tempted to fan a Python `queue.Queue` out to N HTTP clients, this is the reason not to.

### `system.log` carries real ANSI escape codes

libcamera colours its own stdout, cinepi-raw passes it through, and cinemate logs the line
verbatim — so the file contains genuine escape sequences that a browser renders as literal
`[1;32m` rubbish mid-message. They are stripped on the way out (`_ANSI` in
`settings_editor.py`), and anything else that reads this file has to do the same.

The console's own colours are decided **server-side** from `logger.ColoredFormatter`'s
`MODULE_COLORS` and `LEVEL_COLORS` and sent with each line, specifically so the
module-to-colour table is not copied into the template's JavaScript — the same drift shape
this repo already keeps a gate over for the controller-action catalogue (see
[`../orientation/entry-points.md`](../orientation/entry-points.md)).

### What the restart flow may print

Only what the browser can actually observe: the command the page issued, and the real
`/api/v1/hello` response once the camera answers, with how long it took. The first poll waits
(`settleMs`) because the old server keeps answering for a moment after the command is
dispatched, and an immediate hit would report success with nothing having restarted. Nothing
in that console is invented. `_test/test_settings_editor_live_log.py` pins it, including
`test_no_invented_log_lines_survive` and `test_the_card_no_longer_promises_a_startup_sequence`.

## 3. A retry that cannot succeed is a log-destroying loop

`QuadRotaryController` has `RECONNECT_INTERVAL = 5`. With no board fitted,
`_initialize_device()` ran every five seconds forever and logged an identical warning each
time — **twelve lines a minute, on a rig where the board was simply never going to be
present.** By the time anything else needed diagnosing, that loop had already pushed the
camera's own startup output out of the live log's window, which is exactly the history
needed to read a bad take.

The distinction the fix draws is the general one:

| Situation | Meaning | Correct behaviour |
|---|---|---|
| Never answered since startup (`_ever_connected` false) | Hardware is not fitted | Say it **once**, at `INFO`, stop probing |
| Was present, then went away | Bus glitch or knocked cable | Keep retrying on the interval, warn each time |

**Hardware that has never answered is not going to start answering on its own.** The
absent-at-startup message is logged once via `_absent_logged` and names both exits: attach a
board and restart, or turn it off in
`input_peripherals.quad_rotary_controller.enabled`. A board that *was* there and disappears
still reconnects on the old interval, because that case really can recover.

The same commit raised the live log's backlog from 200 lines to 800 (`LOG_TAIL_LINES`) for
the same reason: the encoder prints its configuration once per camera start, and that is the
line worth reaching for when a take comes out wrong.

The general rule this leaves is threading rule 4 in
[`../conventions/style.md`](../conventions/style.md).

## 4. The settings editor's guards, and what each one caught

The settings editor is a single large template with no component framework, so most of its
invariants are unenforceable by types and enforced by text-reading tests instead. These are
not hypothetical; each caught a real mistake.

| Guard | Where | What it caught |
|---|---|---|
| No duplicate element ids | `_test/test_web_ui_combined_download_reconciliation.py::test_no_duplicate_element_ids` | A button added twice — the second one silently unreachable to `getElementById` |
| Five mechanisms per page tab | `_test/test_page_tabs_have_their_markup.py` | A tab landing without its lede, rail group, content group, or topbar predicate |
| Every page has a landing section | `_test/test_settings_editor_page_restore.py::test_every_page_has_a_landing_section_that_exists` | A `PAGE_LANDING` entry missing for a new tab |
| The file stays ES5 | `..._reconciliation.py::test_the_file_stays_es5` | `async`/`await`/arrow syntax that breaks on the older iOS the page targets |
| One `showDirectoryPicker` call site | `..._reconciliation.py` | A second folder-picker client creeping back after a clean auto-merge |

### The page-tab check is the interesting one

The settings editor wires each page by five separate hand-maintained mechanisms that do not
reference each other: a `data-page-tab` button, a `[data-page-lede]` intro, one or more
`.group[data-page]` sections, a `.rail-group[data-page]` sidebar block, and a page-kind
predicate inside `syncTopbarForPage()` deciding whether Save / Revert / Download / Upload
belong on that page at all. **Every failure mode is silent**, because a missing tab-to-page
association is indistinguishable from a page with nothing in it: miss the lede and the page
opens with no heading, miss the rail group and the sidebar keeps showing the previous page's,
miss the predicate and the page offers to save a `settings.jsonc` it does not edit — which is
what the playback tab did.

Two things about how these checks are written generalise past this file — a check that can
pass vacuously, and a check whose own extraction regex is the thing that broke. Both are on
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md), because they apply to
anything under `tools/` as much as to anything under `_test/`.

## The common shape

Each of these is something that reported success while doing the wrong thing, or reported
nothing at all:

- `git -c filter.lfs.clean=cat add` exits 0 and stages a pointer.
- The restart console animated convincingly while connected to nothing.
- The rotary retry logged diligently and destroyed the log.
- Four of the five guards above exist because the failure they catch is invisible.

The recurring defence is the project's own standard: **a check beats a comment, because a
comment cannot fail.** Where a trap here is still only documented — the LFS attribute
mismatch, the twinned tab regex — it is documented precisely because nobody has written the
check yet.

## Further reading

- [`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md) — the five CI jobs, the
  contract-drift scripts in `tools/`, and how to add a check
- [`testing.md`](testing.md) — what runs where, and the `sys.modules` stubbing hazard that
  makes collection order matter
- [`changing-the-gui.md`](changing-the-gui.md) — ADR-001's staged path, and why no GUI step
  should land without its check landing with it
- [`../architecture/gui-state-model.md`](../architecture/gui-state-model.md) — the four
  operator-facing surfaces and which of them owns state
- [`../conventions/philosophy.md`](../conventions/philosophy.md) — "duplicated truth",
  "route, don't replicate", and where the codebase violates its own principles
