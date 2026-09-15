# Task brief — ClearHDR must stop *offering* the ISOs it already refuses

A work order for an agent session, not reference material. Delete it when the work lands.
Background: [`../lessons/hardware-log.md`](../lessons/hardware-log.md), entry
**2026-09-14 "ClearHDR's ISO cap lands on 799, and the operator found the off-by-one-step"**,
and [`clearhdr12-recipe.html`](clearhdr12-recipe.html) §05.

## The goal, in one sentence

In a ClearHDR mode, an ISO the camera will refuse must not appear as a choice — not in the
framebuffer GUI, not in the web GUI dropdown, not under an encoder or a pot — and the ceiling
must be **799**, not the 1585 currently on `dev`.

## What the operator sees today

> "it is already capping at 1585"

That is the whole defect in five words. `set_iso()` clamps correctly; nothing else knows. The
operator can still select 1200, 1600, 2500 or 3200, and the camera silently hands back 1585.
A control that lies about its own range is worse than one that stops.

## Branch

cinemate only.

```
git fetch origin dev
git checkout -b feature/clearhdr-iso-799 origin/dev
```

`dev` moved on 2026-09-15 (`5bc2b28`, `0bb47e6`): the ISO cap docs were restructured, the
12-bit ClearHDR material was removed from the manual, and binned 16-bit ClearHDR became opt-in
behind `imx585_clear_hdr_16bit_hd`. Branch off the current `dev`, not off anything cached, and
re-read `docs/clear-hdr.md` before editing it — the Docs section below reflects the new shape.

No `cinepi-raw`, no libcamera, no driver change. If you conclude you need one, stop and say why
before writing anything.

## Read this before you write a line — most of it already exists

`origin/feature/clearhdr12-preview-clean` @ `384f3b7` already carries **exactly the design you
want**, at the right number:

- `CLEARHDR_ISO_MAX_DEFAULT = 799`, `image_capture.hdr.iso_max: 799`
- `_clearhdr_iso_ceiling()`, `effective_iso_steps()`, `iso_is_capped()`
- the "keep the first step above the cap, land it on the cap, tint it green" rule
- the green tint in both GUIs (`simple_gui.py`, `template.html`)

`dev` has the same three methods and the same tint, differing **only** in the constant (1585)
and the prose around it. Diff the two and port; do not re-derive. The commit message on
`384f3b7` is worth reading in full — it is the operator's own reasoning for keeping the 800
step rather than dropping it.

So the numeric half of this task is a port. The real work is the half nobody did: the surfaces.

## What is settled — do not re-measure any of this

1. **The ceiling is 799.** `imx585.c` line 167 documents `9.6dB <= GAIN + EXP_GAIN <= 29.1dB`
   for built-in combination, which with the ClearHDR default `gain_adder` of +12 dB caps
   analogue gain at code 57. Measured on the rig off the driver's own `ANALOG_GAIN=` lines:

   | ISO | 640 | 700 | 799 | 800 | 900 | 1000 |
   |---|---|---|---|---|---|---|
   | gain code | 51 | 56 | 56 | **60** | 63 | 66 |

   799 is the last ISO inside the window; 800 is the first outside it.

2. **1200 and above are genuinely out of reach.** In 12-bit ClearHDR HD, reading the merge
   ceiling off the raw: code 71 (ISO 1200) reaches 3188 of 4095, code 80 reaches 2408 — about
   a stop and a half of highlight range gone, which is the range ClearHDR exists to deliver.

3. **1585 is a real limit too, just the wrong one to cap on.** Above ~ISO 1585 analogue gain
   pins at code 80 and the recording stops changing at all. That is the *outer* limit; 799 is
   the *useful* one. Keep the 1585 explanation in the docs as secondary context — it is true,
   and it is why `dev` picked it — but the cap lands on 799.

4. **Lowering `gain_adder` does not buy the range back.** The adder *is* the HG/LG ratio; at
   adder 0 the measured ceiling is 1452, worse. Do not offer this as an escape hatch.

5. **SDR is never capped.** The window is a ClearHDR combination limit. An operator who wants
   the full range back sets `image_capture.hdr.iso_max: null`.

## The actual defect: five surfaces publish the uncapped table

`effective_iso_steps()` exists and is correct. Almost nothing calls it. Confirmed by reading
`origin/dev`:

| # | Where | What it does today |
|---|---|---|
| 1 | `src/module/parameters.py:127` | `_ISO` declares `steps=lambda c: c.iso_steps` — the raw table |
| 2 | `src/module/cinepi_controller.py:3072` and `:3101` | `increment_setting`/`decrement_setting` do `dynamic_steps = param.steps(self)`, **discarding the `steps` argument their caller passed** |
| 3 | `src/module/app/main/events.py:46` | `'iso_steps': cinepi_controller.iso_steps` → the web GUI's `s-iso` dropdown |
| 4 | `src/module/simple_gui.py:1022` | `values["iso_steps"] = ... controller.iso_steps` → the framebuffer GUI and the socket push |
| 5 | `src/module/analog_controls.py:158` | `return c.iso_steps` for a pot |

Surface 2 is the one to look at first, because it makes an existing comment untrue.
`inc_iso()` at `:3129` reads:

```python
# effective_iso_steps() rather than iso_steps: stepping up must stop
# where ClearHDR stops being ClearHDR, the same place set_iso() clamps.
self.increment_setting('iso', self.effective_iso_steps())
```

It passes the capped table, and `increment_setting` throws it away on the next line in favour
of the registry's uncapped one. **Verify this yourself before fixing it** — read both methods
end to end and write the failing test first. If I have misread the precedence, say so and
stop; everything below depends on it.

## The fix I would write, and why

Do not invent a mechanism. **`fps` already solved this exact problem in this exact file.**

`fps_steps_dynamic` is the FPS table capped at the sensor mode's `fps_max`: rebuilt in
`_rebuild_fps_steps()` (`:902`), published by both GUIs, and snapped against by `set_fps()`.
`simple_gui.py:1018` even documents the convention:

> `shutter_a_steps_dynamic` and `fps_steps_dynamic`, not their non-dynamic siblings: those two
> are the tables `set_shutter_a_nom()` and `set_fps()` actually snap an incoming value against,
> which is what lets a browser control offer only values that will stick.

ISO is the one parameter in that list that publishes the table values do *not* stick to.

And `iso_steps_dynamic` **already exists** — `cinepi_controller.py:96` assigns it at
construction and nothing ever reads it again. It is a slot cut for this and left empty.

So: make `iso_steps_dynamic` the ClearHDR-capped ISO table, rebuild it wherever `iso_steps` is
rebuilt and wherever the HDR flag changes, and point all five surfaces at it. That is a small
diff that matches a convention already documented in the files it touches.

**Watch the rebuild triggers.** Unlike `fps_max`, the ISO ceiling depends on live Redis state
(the `hdr` key), so it changes when the operator switches modes, not only when settings reload.
`_publish_resolution_gui_state()` (`cinepi_controller.py:2331`) is the only writer of that key —
rebuild after it, and after a settings load. A stale table here is the whole bug again, wearing
a different hat.

Rebuild *after* the publisher returns, from `_apply_resolution_mode()`, not inside
`_publish_resolution_gui_state()` itself. That function is a pure publisher and at least one
test builds a partial controller and calls it directly; putting work inside it breaks
`test_cinepi_controller_resolution_gui`. Learned the hard way — see the hardware log.

## Drop, or grey?

The operator said "removing 1200 from the array (or hiding it, making it grey)". Both, split by
what the surface can express:

- **Cycling surfaces** (encoder, pot, `inc_iso`/`dec_iso`) — **drop**. There is nowhere to show
  grey; stepping up must simply stop at 800.
- **List surfaces that show the whole table at once** (the web GUI `<select>`) — **grey**, via
  `disabled` options. The machinery is already there: `freeStepBounds()` in `template.html`
  greys interior options exactly this way, and its comment explains that a disabled `<option>`
  can still be selected programmatically, so the live value keeps showing.

Greying tells the operator *why* their ISO stops at 800, which a silently shortened list does
not. If greying the dropdown turns out to be more than a small change, ship the drop everywhere
and ask before going further.

**One trap.** `template.html:1098` currently says:

> NOT ISO: `set_iso` clamps and never snaps in any mode, so `iso_free` changes what is offered,
> not what is accepted. Greying either would state something untrue.

That is about **free stepping**, a different reason, and it is still correct. If you add cap
greying, amend that comment to distinguish the two cases, or the file contradicts itself.

**One consequence to check, not fix by accident.** The EXPERIMENT drawer's ISO slider
(`XP_SLIDER_GROUPS`, `template.html:1515`) takes its bounds from the ends of the live ISO table
(`boundsFrom: 'iso'`). Publishing the capped table narrows the slider to 100–800 in ClearHDR.
That is correct and desirable — pin it with a test rather than letting it be a surprise.

## Docs — brief

The house style is to trim, not to add; `caa82de` and `04a4f2a` are both doc-trimming commits.
Match that. A sentence each, not a paragraph:

| File | What changes |
|---|---|
| `docs/clear-hdr.md` | The cap now has **its own section**, `## ISO is capped at 1585` (line 15), plus a bullet at line 6 that cross-links to it. The heading, its anchor `#iso-is-capped-at-1585`, and that link all carry the number — change all three together or the link breaks. Its gain-code table lists 800/1600/2500/3200; it needs the 640/700/799/800 sweep instead. |
| `docs/settings-json.md` (the `image_capture.hdr.iso_max` row, line 539) | Currently a wall. Cut it to: default `799`, ClearHDR only, `null` lifts it, the 800 step is kept and lands on 799 in green, above that is not offered. |
| `settings.jsonc` + `resources/settings/settings_default.jsonc` | The comment block above `iso_max` (now line 298) carries the 1585 reasoning. Replace with the 799 reasoning, same length or shorter. |
| `settings.schema.json` | The `iso_max` description and any default. |
| `docs/changelog.md` | One line. |
| `resources/gui-text/05-settings-exposure-and-steps.md` | Check whether any card mentions the ISO cap; `tools/gui_text_check.py` is the contract-drift check for these. |

**The new docs section already claims the behaviour this task has to build.**
`docs/clear-hdr.md` line 17 reads "In a ClearHDR mode CineMate stops offering ISO above
**1585**." It does not. It stops *accepting* above 1585 and goes on offering 1200, 1600, 2500
and 3200 in every list. Do not treat that sentence as evidence the surfaces are already
handled — it is the sentence this task makes true.

The 12-bit ISO/gain-code table that used to sit in `docs/clear-hdr.md` (the one with the 799
column) was removed with the rest of the 12-bit material in `5bc2b28`. The 799 sweep now lives
only in this brief and in the handbook's hardware log — carry it into the docs yourself.

## Tests

- `_test/test_clearhdr_iso_ceiling.py` exists and pins the **1585** expectations (line 81
  asserts `[100, 200, 400, 640, 800, 1200, 1600]`). It must move to 799 →
  `[100, 200, 400, 640, 800]`. Its module docstring carries the old reasoning too.
- New, one per surface above: the registry/`increment_setting` precedence, the web GUI payload,
  the framebuffer payload, the pot table, the EXPERIMENT slider bounds.
- Keep the existing guards: SDR is never capped, `null` lifts the cap, a cap below every step
  still leaves one selectable ISO.
- Run the full suite. Baseline on `feature/clearhdr12-preview-clean` was **1187 passed, 1399
  subtests**; `dev` may differ, so record `dev`'s own baseline before you start.
- Run `tools/gui_text_check.py` and `tools/findings_disposition_check.py`.

## At the camera

Ask the operator to run these; do not deploy without saying so first.

1. **Copy `settings.jsonc` before any branch switch on the Pi.** The last switch left conflict
   markers in the live config because the branch modifies that file and the stash dance is not
   enough. Recovered from a copy last time. Do this first, every time.
2. In a ClearHDR mode: the ISO list offers 100, 200, 400, 640, 800 and nothing above.
3. `set iso 800` → Redis reads **799**, shown green in both GUIs.
4. Encoder and pot both stop at 800 and do not walk past it.
5. `set iso 3200` → **799**, with the log line saying why.
6. Switch to an SDR mode without restarting: the full table comes back, no tint.
7. Switch back to ClearHDR: the table shortens again. (This is the rebuild-trigger test.)
8. `image_capture.hdr.iso_max: null` → full table in ClearHDR, no tint.

## Reporting

- One commit per coherent change; the operator reads commit messages as documentation.
- Push to the feature branch, open a draft PR against `dev`.
- Add a hardware-log entry to `cinemate-handbook` when the camera tests run: what was tested,
  what worked, what did not, and any number that contradicts this brief. **A measurement that
  refutes this brief is the most valuable thing you can produce.** Two rounds of published
  claims here have already been corrected by the rig.
- Flag the merge collision explicitly in the PR body: `dev` carries `iso_max: 1585` and
  `feature/clearhdr12-preview-clean` carries `799`. Whoever merges must confirm 799 wins.
