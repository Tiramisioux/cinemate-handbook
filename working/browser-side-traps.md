# Browser-side traps

The web GUI (`src/module/app/templates/template.html`) and the settings editor
(`src/module/app/templates/settings_editor.html`) are the only two parts of this stack that
run in someone else's runtime. Everything below was **measured in a browser on real
hardware**, not derived from a spec — each one had a plausible desk explanation that was
wrong, or was invisible from the desk entirely. The settings editor embeds the shooting
screen at `/?xp=1` in an iframe, so a trap in `template.html` is a trap on both pages.

| Trap | Symptom | Invisible to |
|---|---|---|
| MJPEG `<img>` accepted-and-silent | preview black from boot, recovers only on a resolution change | every event handler — nothing fires |
| No iOS Fullscreen API for an `<img>` | button flashes on tap, does nothing | desk browsers, which all have the API |
| `height: 100%` on a phone | bottom row sits behind the browser toolbar, unscrollable | device emulation — it has no toolbar |
| Grid automatic minimum size | preview squeezed to 0px, drawer never scrolls | reading the CSS; only measured boxes show it |

## An MJPEG `<img>` can be accepted and then silent, and that fires nothing

**cinepi-raw registers `/stream` before the first frame exists, on purpose, and that
deliberate kindness is what broke the GUI's `<img>`.** `mjpegPreviewStage` accepts a client
that connects early and simply makes it wait for the first real frame, so a person typing the
address during boot does not land on a 404. The GUI's `<img>` used to depend on exactly that
404: it fired `error`, and the error handler re-armed the retry. Accepted-and-silent fires
`error` never, `load` never, and nothing at all — so nothing retried, and the preview stayed
black until something else called `reloadStreams()`. A resolution change does. That is the
whole of the "it only comes up if I change resolution" reproduction.

The fix is a **first-frame watchdog** (`armStreamWatchdog`), armed whenever a `src` is set and
disarmed for good by the first frame, plus a periodic sweep for `naturalWidth === 0`. Two
measured facts govern how it has to be written:

- **`load` fires once per connection, not once per frame.** Ten seconds of a running stream
  produced **zero** `load` events. It is a first-frame signal and nothing more; it cannot be
  used as a liveness or heartbeat signal, and a watchdog re-armed on every `load` would never
  re-arm. (Whether a browser fires `load` per part of a `multipart/x-mixed-replace` response
  is not portable enough to bet a reconnect loop on either way.)
- **The first-frame flag must be cleared on every reconnect.** `scheduleStreamReload` clears
  `img._gotFrame` before setting the new `src`, because a fresh connection has produced
  nothing whatever the last one managed. Leave it set and `armStreamWatchdog` declines to arm
  — so the one reconnect that most often lands silent, the one issued while the camera is
  still coming up after a restart, is the one with nothing watching it.

Six signals feed recovery, and each is blind to something. Do not delete one because another
looks like it covers the case:

| Signal | Fires when | Blind to |
|---|---|---|
| `error` on the `<img>` | refused, 404, or a drop the browser reports | accepted-and-silent; a frozen stream |
| `reload_stream` socket emit | the server knows it restarted the camera | a missed emit — backgrounded tab, socket hiccup mid-restart |
| `resolution_switching` truthy→falsy edge | the Redis fan-out says the switch finished | anything that is not a resolution switch |
| socket `connect` after a prior connect | cinemate went away and came back | cinepi-raw restarting while cinemate survives |
| first-frame watchdog after each `src` set | accepted-and-silent | a stream that delivered a frame, then froze |
| `naturalWidth === 0` sweep | a listener that never decodes a frame — e.g. an orphan process squatting on `:8000` | a freeze after the first decoded frame |

**Related, same mechanism: do not add a cache-buster to the stream URL.** nadjieb's
`mjpeg_streamer.hpp` reads the request target with `getline(iss, target_, ' ')`, so the query
string is part of the target, and `pathExists()` is an exact map lookup — `/stream?reload=…`
misses, the server answers 404 and closes. Because every recovery path funnels through one
function, a cache-buster did not merely fail to help: it replaced a working MJPEG connection
with a permanent 404, including in the case cinepi-raw handles well on its own (it keeps the
listener alive across a camera reconfigure, so the old connection would have survived).
Dropping `src` first — the thing the cache-buster was there to achieve — is what makes the
browser re-request an identical URL.

## iOS has no Fullscreen API for anything but a `<video>`

**Probe the methods, never the user agent, and hide a control you cannot make work.** iPhone
Safari exposes no element-fullscreen API at all; iPad does (webkit-prefixed since iOS 12,
unprefixed since 16.4). Probing `requestFullscreen || webkitRequestFullscreen` keeps the
button on iPad and lets a future iPhone gain it for free. The preview is an MJPEG `<img>`, so
there is no `HTMLVideoElement.webkitEnterFullscreen()` fallback available to it.

Two measured details are the reason this page exists rather than a one-line guard:

- **A dead control still feels alive.** Calling the missing method threw a `TypeError` inside
  the click listener that nothing caught, and `button:active` still flashed on tap — so the
  control looked like it worked, on the one platform where it could not.
- **The obvious substitute was measured, and buys nothing.** A "maximise" stand-in that hides
  the readouts and both rails was built and measured on a 390px-wide phone: the picture was
  **438×246 before and 438×246 after**. A 16:9 picture on a portrait phone is limited by
  *width*, not height, and the rails hand back about 31px a side out of ~490. It was not
  shipped. A button that appears to do something and does nothing is worse than no button,
  which is why this one hides instead.

Real screen on a phone comes from turning it landscape, or from Add to Home Screen, which
drops the browser chrome entirely. If you are about to build a layout-based substitute for a
missing platform API, measure the picture before and after first — the substitute is a
hypothesis about which axis binds.

## `height: 100%` on a phone resolves against the large viewport

**Safari and Chrome on a phone resolve `100%` against the LARGE viewport — the one that exists
when the toolbar is retracted — so the foot of a non-scrolling page sits behind the toolbar,
and `overflow: hidden` means it cannot be scrolled into view.** The button row, and the
FULLSCREEN button with it, was simply unreachable. `100dvh` is the visible viewport, toolbar
included; it ships behind `@supports (height: 100dvh)` with `height: 100%` left as the
fallback for anything without it.

The durable part is the second half: **emulation cannot reproduce this, because emulation has
no toolbar.** Measuring at 390×620 put the button comfortably on screen. Device emulation
models viewport dimensions, not browser chrome — so any bug whose mechanism *is* chrome
(toolbar occlusion, address-bar collapse, safe-area insets) needs a real phone, the same way a
claim about what the machine does needs the machine. See
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) for the general
form of this rule.

## CSS Grid: two sizing traps that both end with the preview gone

### `align-items` on the container hits the column you meant to leave alone

**Alignment intended for some children belongs on those children.** Upright on a phone the
rails should be as tall as the picture and centred beside it. Setting `align-items: center` on
`#stage` achieves that — and also stops the *preview* column stretching, so `#preview-wrap`
collapses to whatever `--preview-h` last said, `sizePreview()` letterboxes into that smaller
box, and writes a smaller `--preview-h`. Measured at 390×844: a 585px row with the picture
settled at 237px and still shrinking. The fix is `align-self: center` on `#rail-left` and
`#rail-right` only, with `#stage` left at `align-items: stretch`.

A related loop in the same file, worth knowing before you add another observer: the
`ResizeObserver` watches `#stage`, **not** the rails. Writing `--fit` changes a rail's own
width, which would re-trigger an observer on the rail; `#stage`'s border box is fixed by the
grid and only its columns redistribute, so observing the container cannot feed itself.

### A grid item's automatic minimum size is its content

**`min-height: 0` alone does not make a panel scroll — a definite `max-height` does.** The
EXPERIMENT drawer given a flexible row and no cap grew to the full height of its controls,
squeezed `#stage` to zero — the preview vanished outright — and never engaged its own
`overflow-y`, because the box was already as tall as its content. There is nothing left for
`overflow` to overflow. Measured on the camera: rows-and-`fr` gave stage **0px** with 125px of
overflow; a definite cap gave stage **170px**, drawer **527px**, and a drawer that actually
scrolls.

The cap is also what decides who wins the space, so pick it deliberately rather than
generously. In the settings editor's Live view pane an earlier, looser cap let the drawer take
what it wanted, pinning `#stage` at its floor: measured at 1400×900 that produced a **298×166**
preview inside a 1266px-wide pane, and dragged the rails down with it (`fitRails()` sizes them
off the stage height, and their legibility floors stop the shrink short, so large badges sat
beside a tiny picture). The shipped cap gives **791×442**, with the drawer still 240px and
still scrolling.

The two pages trade in opposite directions here, and that is intentional: the shooting screen
never scrolls and the drawer eats into the preview, because a layout that grows under the
operator mid-shot is worse than a smaller picture; the settings editor's pane is a desk tool,
so it pins the stage and lets the page scroll instead. If you change one, check the other —
they share the file.

## What the four have in common

Every one of these was a **silent** failure in a runtime that owed no explanation: no event, no
console error, no exception that reached anything. Three of the four had a confident desk
diagnosis that a browser then contradicted, and the fourth (`height: 100%`) was actively
*confirmed as fine* by emulation. Two working rules follow:

- **A missing event is not the same as a working stream.** When recovery hangs off an event,
  ask what happens in the case where the event never fires at all — then arm a timer for that
  case and clear its flag on every retry.
- **Measure the box, not the CSS.** Grid and flex failures show up as numbers
  (`getBoundingClientRect`, `naturalWidth`) long before they show up as anything readable in a
  stylesheet, and both grid traps here look correct on the page.

Neither of these is checkable in CI today — the browser layer has no automated check at all,
which is worth remembering before treating a comment in `template.html` as a guarantee (see
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md): a comment cannot fail).

## Further reading

- [`changing-the-gui.md`](changing-the-gui.md) — adding a field, the colour-token pair, and the layout spec
- [`../architecture/gui-state-model.md`](../architecture/gui-state-model.md) — why the web GUI has no state of its own, and why the settings editor is a different model
- [`../architecture/cinepi-raw.md`](../architecture/cinepi-raw.md) — `mjpegPreviewStage`, preview ownership, and what a camera reconfigure does to a live connection
- [`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) — the reading-settles-structure / machine-settles-behaviour rule these four are instances of
- [`../orientation/the-traps.md`](../orientation/the-traps.md) — the stack-level traps, of which #5 (the web GUI's cadence is the HDMI redraw loop's) is the one most likely to be mistaken for a browser bug
