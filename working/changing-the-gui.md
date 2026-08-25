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

Colours are defined twice: once as HDMI GUI constants (or `self.colors` entries) in
`simple_gui.py`, and once as CSS custom properties in the web template. Both need updating
together. `tools/design_token_diff.py` gates at zero in CI and will catch a mismatch.

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
refresh cadence, real RAM headroom on the actual hardware — and reached a specific
recommendation: fix the Redis-listener failure mode first (see
[`../orientation/the-traps.md`](../orientation/the-traps.md) #1), then unify design tokens,
then lift the section spec into shared data, then generalise the layout primitives — each
step shippable and revertible on its own, keeping per-surface region layout separate (a
1920px instrument panel and a phone browser should not share a grid). Read the ADR before
proposing a different shape; it also records two rejected options (a resident browser driving
HDMI; server-side HTML rasterised to the framebuffer) and exactly why, including which
rejection grounds were later contradicted by hardware measurement and which held anyway — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md).

## Scope exclusion

The settings editor and the recovery console are **not** part of this state model — they edit
files on disk, not live state, and the recovery console's isolation from the rest of the
system is a deliberate property, not a gap to unify away. See
[`../architecture/gui-state-model.md`](../architecture/gui-state-model.md).
