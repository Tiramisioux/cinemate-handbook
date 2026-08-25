# GUI state model — how the four surfaces relate

There are four operator-facing surfaces. They are not all the same kind of thing, and
treating them as if they were is the mistake this page exists to prevent.

| Surface | What it is | State model |
|---|---|---|
| 1. HDMI GUI | `simple_gui.py`, a `Thread` subclass rasterising via PIL to `/dev/fb0` | `populate_values()` — a single dict, roughly 70 live fields |
| 2. Web GUI | Flask + Socket.IO | **The same dict** — consumed verbatim |
| 3. Settings editor | Flask, edits config | `settings.jsonc` + `config.txt` + a take listing — files on disk |
| 4. Recovery console | Standard-library-only, isolated on its own port | The same two files, plus systemd state and the journal |

## Surfaces 1 and 2 already share one state model

The web GUI has no field set of its own. It consumes the HDMI GUI's `populate_values()`
output directly, and the code says so in a comment. This matters because it means "generate
both surfaces the same way" — a question this project has explicitly asked itself — is
already half true, and the half that's true is the expensive half: a shared **state** model
already exists. What's duplicated is **presentation** — colours, labels, and layout.

Of roughly 70 fields, most reach the web template; the ones that don't fall into two groups:
plain label text (accidentally duplicated as HTML text nodes, currently in agreement but one
edit from drifting), and recording-integrity counts that the HDMI GUI shows as raw numbers
and the web GUI shows only as latched pass/fail badges — a real capability difference, not
an oversight, and worth confirming deliberately if you're touching that area rather than
assuming parity.

**Not all of it is recoverable from Redis.** A meaningful fraction of the shared dict is
`SimpleGUI` instance state — VU smoothing, lock flags, display geometry — that never reaches
Redis at all. Anything that tries to render a surface without going through `SimpleGUI` has
to reproduce this state or lose it.

## Surfaces 3 and 4 are correctly on a different model

They edit **configuration** (files on disk), not live state. Unifying their state model with
surfaces 1/2 would be a category error — don't try. Their one connection to the live-state
world: the settings editor keeps its own catalogue of controller method names (used to
validate that an action button will actually resolve). That catalogue has existed in multiple
hand-maintained copies before, and it has drifted — see
[`../orientation/entry-points.md`](../orientation/entry-points.md)'s row on controller
methods for the check that now guards it.

## The residual hard problem is layout, not state

The HDMI GUI already does more flow layout than a first read suggests — one row measures
rendered widths and distributes free space; the section layout walks a spec of labels,
formatters, and per-item visibility conditions. That grouping spec is close to what a shared
declarative layout would need; the formatters are Python lambdas rather than serialisable
data, which is the gap, not the paradigm. If you're proposing a bigger unification of the two
renderers, read `system-review/decisions/ADR-001-gui-harmonization.md` before starting — it
already worked through this exact question against measured hardware constraints (DRM
exclusivity, actual refresh cadence, actual RAM headroom) and reached a specific, narrow
recommendation. Don't re-derive it from scratch.

## One process owns the display — and the GUI still gets a real plane

See [`../orientation/the-traps.md`](../orientation/the-traps.md) #4. Hardware verification
found the HDMI GUI (via the kernel console framebuffer that `simple_gui.py` writes) occupies
a genuine DRM plane, driving the HDMI output, and — under the conditions actually tested —
cinepi-raw's own preview held no plane at all. That's narrower than "the two interfaces are
racing for the display", and it does not mean a second real display client (a kiosk browser,
say) would be safe — DRM master exclusivity is a separate, harder constraint that this
result doesn't touch. See ADR-001 for how that distinction plays out across the options it
considered.

## Further reading

- `system-review/deliverables/GUI-STATE-MODEL.md` — the full field-by-field matrix this page distills.
- `system-review/decisions/ADR-001-gui-harmonization.md` — the architecture decision this feeds, including the measured constraints (DRM, RAM, refresh rate) and the recommended path.
- [`../working/changing-the-gui.md`](../working/changing-the-gui.md) — the practical checklist for a GUI change.
