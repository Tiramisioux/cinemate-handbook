# Changing the GUI

Read [`../architecture/gui-state-model.md`](../architecture/gui-state-model.md) first if you
haven't — this page assumes it.

## Adding or changing a field the GUI shows

1. Add or change the field inside `simple_gui.py`'s `populate_values()`.
2. That's usually it. The web GUI consumes the same dict verbatim over Socket.IO, so a new
   field reaches the browser automatically. `tools/gui_field_extract.py` reports which
   fields reach the template, which is a useful check that your new field is actually wired
   up, not a step you need to perform by hand.
3. If you want it *displayed* on the HDMI GUI specifically, you also need an entry in
   `self.layout` (or the relevant section list in `setup_resources()`) and, on the web side,
   the template.

**Watch for:** deltas are emitted from inside `draw_gui()`, so the browser's update cadence is
tied to the HDMI redraw loop's cadence, not something independent — if that thread stops, the
browser stops too (see [`../orientation/the-traps.md`](../orientation/the-traps.md) #5).
Measured cadence on real hardware has been closer to ~7.5 Hz than the commonly assumed
~12 fps — don't design an animation or a fast-changing indicator around a higher number
without measuring on your own unit.

## Changing a colour

Shared colours live once now, in `src/module/design_tokens.py`'s `DESIGN_TOKENS` dict (name →
`(r, g, b)`) — ADR-001 step 1 replaced what used to be two independently hand-maintained lists.
`simple_gui.py`'s module-level `*_COLOR` constants (plus the `self.colors` table's `lock` and
`voltage` entries) read from that dict; don't reintroduce a literal there. The web template's
`:root { --token: rgb(...) }` block in `template.html` is still hand-written, not generated, so
a new or changed token needs both: the entry in `design_tokens.py` and the matching CSS custom
property. `tools/design_token_diff.py --strict` gates at zero in CI and checks every
`design_tokens.py` entry has an exact CSS counterpart. The rest of `self.colors` is
informational only — it predates the shared source and was never brought into its scope.

## Changing the HDMI layout specifically

The section layout (`setup_resources()`'s `left_section_layout`/`right_section_layout`) is a
spec of labels, ordered items, per-item formatters, and a `condition` predicate for
visibility. **Use the `condition` predicate for anything that should show or hide** — several
places in this codebase historically commented out a layout entry instead, which is harder
to find later and easier to forget about. The top row does measured, justified flow layout;
the rest of the layout is fixed-position. Nothing checks a layout change automatically —
verify visually.

## If you're considering unifying the two renderers further

Don't start from scratch. `system-review/decisions/ADR-001-gui-harmonization.md` already
worked through this exact question against measured constraints — DRM exclusivity, real
refresh cadence, real RAM headroom on the actual hardware — and reached a specific, ordered
recommendation of four steps, numbered **step 0 through step 3**. **Two are already
shipped:** step 0, the Redis-listener failure mode (see
[`../orientation/the-traps.md`](../orientation/the-traps.md) #1, hardware-verified fixed),
and step 1, shared design tokens (`design_tokens.py`, see "Changing a colour" above). What's
left is step 2, lift the section spec into shared data (replace the lambdas in
`left_section_layout`/`right_section_layout` with named formatter references the web backend
can read too), then step 3, generalise the layout primitives (extract `_top_row_layout`'s
justified-row logic and the conditional-stack logic into a region-layout helper shared by
both renderers) — each step shippable and revertible on its own, keeping per-surface region
layout separate (a 1920px instrument panel and a phone browser should not share a grid). Read
the ADR before proposing a different shape; it also records two rejected options (a resident
browser driving HDMI; server-side HTML rasterised to the framebuffer) and exactly why,
including which rejection grounds were later contradicted by hardware measurement and which
held anyway — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md).

## Scope exclusion

The settings editor and the recovery console are **not** part of this state model — they edit
files on disk, not live state, and the recovery console's isolation from the rest of the
system is a deliberate property, not a gap to unify away. The settings editor's Playback pane
is the same exclusion for a different reason: `src/module/app/playback.py` reads DNGs straight
off the card (via `raw_files`/`dng_preview`) and serves frames over its own
`/api/playback/clips` routes, deliberately independent of Redis and `populate_values()` — so
"adding a field the GUI shows" above does not apply there. See
[`../architecture/gui-state-model.md`](../architecture/gui-state-model.md).
