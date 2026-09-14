# Task brief — make 12-bit ClearHDR previews clean

This is a work order for an agent session, not reference material. Delete it when the work lands.
The reasoning behind it is in [`clearhdr12-recipe.html`](clearhdr12-recipe.html) in this directory; the
history is in [`../lessons/hardware-log.md`](../lessons/hardware-log.md), entries 2026-09-06/07,
2026-09-13 and 2026-09-14.

## The goal

12-bit ClearHDR previews (HDMI, the MJPEG web view, and the embedded DNG thumbnail) render correctly
in all four ClearHDR modes, with **no pink blown highlights, no white speckle, no ragged boundary
against a coloured surround, and no dropped frames**. The recorded DNG does not change.

A separate decision stands that 16-bit plus a log encode is the better capture format. That is not
this task. This task makes 12-bit work on its own terms, because the mode ships and operators use it.

## Branches

Create a feature branch in each repo you actually change. Do not commit to `dev` or `main`.

| Repo | Branch from | Branch name |
|---|---|---|
| `cinepi-raw` | `dev` | `feature/clearhdr12-preview-clean` |
| `cinemate` | `dev` | `feature/clearhdr12-preview-clean` |
| `imx585-v4l2-driver` | `cinemate-7modes` | same name, only if a register actually has to change |
| `libcamera` (fork) | `cinemate` | same name, only if you get to phase 4 option C |

Expect to touch only `cinepi-raw`. If you find yourself changing the driver, stop and say why first.

## What is already settled — do not re-derive any of this

1. **The trigger is channel agreement, never a raw code.** Three shipped builds anchored the highlight
   correction on a code (2900, 2582, 2344) and all three were wrong: the clamp moves with analogue
   gain, with the HG/LG blend and with the scene. Measured: 54100 at gain code 71 and 48600 at code 80
   in 16-bit; about 2298 in 12-bit HD where the table said 2582.
2. **Second-brightest over brightest, not min over max.** A tungsten lamp pins red and green on one
   code while blue sits at 0.79 of it. A test requiring all three channels to agree misses the entire
   12-bit HD case and reports zero converged quads while a fifth of the frame is pink.
3. **The ramp thresholds that work**, measured across three takes: ratio 0.98 to 0.997, level 0.40 to
   0.50 of full scale above black. The first shipped attempt used a level gate of 0.15 to 0.25 and
   produced white speckle in every HDR mode, including the two that had been clean.
4. **One pixel is never a clamp.** A per-pixel rule fires on a few hundred isolated pixels per frame.
   Scattered white pixels are as objectionable as the pink.
5. **The blown-highlight defect is the same in both bit depths**, and the compander is not involved in
   it. Above the compander's second knee the stored code differs from true linear by a *constant*
   (2455.34 at full res, 3016.21 binned), and a constant cannot change the ratios between channels once
   black is subtracted. The mid-tone crush is the compander's doing; the pink highlight is not.
6. **The anchor stays** alongside whatever you build, whichever fires harder. It is hardware-confirmed
   for full res and both 16-bit modes, and taking the maximum can only add correction, never remove any.

## The work, in order

### Phase 1 — land the correctness that already exists

The fix was written, confirmed on hardware, merged, and then reverted for cost. Re-apply it:
`daa5243`, `be711df`, `836f58c`, `6553e88`, `ea0077e` on `origin/feature/clearhdr16-preview-clamp`.

Done when the four pure unit tests build with a direct `g++` line (no meson) and pass, and when
`tests/clip_convergence_test.cpp`'s `genuine_white_at_the_clamp_level` check still passes for the right
reason: a real white subject at the same level as a clamped one must not be touched.

### Phase 2 — the cost, which is why it was reverted

Running that build, the camera dropped 102 frames in 20 minutes and the measured rate collapsed from 25
to between 3.5 and 12.5. On `dev` the same scene drops 2 frames in 3 minutes, both at startup.

Nobody has ever measured what the stage costs on the Pi. Correctness was measured all night; cost was
never measured at all. So measure it first.

1. **Instrument.** Add per-frame timing of the whole `Process` body, including the buffer syncs, to the
   existing periodic log line: median, maximum, the count of frames over a budget, and the frame period
   taken from consecutive sensor timestamps so the two can be compared on one line.
   The budget is 15 ms median against a 40 ms frame period at 25 fps.
   **The diagnostic must be able to come out wrong.** This project shipped a number three times that
   read identically whether the fix worked or not. Before trusting your timer, confirm it moves by the
   predicted amount when the correction is disabled in the post-process file, with no rebuild.
2. **Cut the work.** Measured off-hardware at `-O3`, the 16-bit in-place path goes from 22.6 ms to
   10.2 ms per frame, byte-identical on every test scene, from three changes: an integer level gate
   before any other work, an integer top-two comparison instead of a float divide, and skipping the six
   writes where the block's blend is zero. The 12-bit path is different: it re-renders the whole frame
   and no single part dominates, so an early-out saves only about 8%.
3. **The detector.** In 12-bit it only feeds a log line. Run it on one quad in four and every fourth
   frame, and add a check that the subsampled floor lands within one histogram bin of the full one.

**Stop here and hand the operator a test.** You have no camera. Ask for: 4K and HD, 12-bit ClearHDR,
25 fps, a blown lamp in frame, twenty minutes each, reporting the new timing line and the dropped-frame
count. State your prediction before they run it.

### Phase 3 — the ragged edge

With the core neutral, the boundary between it and a yellow surround is chunky: white pixels scattered
into the yellow in 2×2 blocks. A tungsten shade has red and green naturally close, which is the same
signature the rule uses, so at the transition both the ratio and the level sit mid-ramp, noise decides,
and the block rule quantises that indecision into visible steps.

Erosion is the right tool for isolated noise and the wrong one for an edge: it keeps the edge hard and
punches holes in it. Replace it with a feathered matte: take the mean of the four quads per output
block, blur that map with a separable 3×3 box, then apply a soft threshold. On synthetic data this took
holes and islands from 321 and 88 to zero without touching the surround, and it measured the same cost
as the gated version because the map is only 226,000 floats.

Before building it, run `edge_probe.py` (in the handoff bundle) on the tungsten take to find out whether
those edge pixels are exact ties or merely close. If they are ties, a tolerance in code space helps and
feathering may not be needed. **Check first that the script reproduces the recorded isolated-pixel counts
of 245 and 498 on the two 16-bit takes**, or its other numbers mean nothing.

The trade-off to state explicitly when you propose thresholds: widening the ratio ramp desaturates
genuinely yellow highlights. The measured orange surround sat at 0.912 with a 95th percentile near 0.94.

### Phase 4 — only if phase 2's measurement says the budget is still blown

In preference order:

- **A.** Use the in-place correction on 12-bit instead of the full-frame render for the highlight defect.
  Point 5 above says it should work unchanged. This removes the render from the highlight path entirely.
- **B.** Split the render across two threads on row halves. Measured 12.6 ms wall against 22.3 on x86.
  Per-thread counters must be merged after the join or the log lies.
- **C.** A ClearHDR-only tuning file carrying black level 2455 at full res and 3016 binned, which makes
  the ISP's own render linear over the top 2.5 stops (4.4 binned) at no per-frame cost. The per-camera
  tuning-file override already exists and ships. Cost: the preview's black lifts by 745 counts, so the
  monitor's toe goes milky, and it does nothing below that knee.

Do not start phase 4 before phase 2's numbers exist.

## Constraints that are not negotiable

- **Preview only.** The recorded DNG keeps the clamped channels exactly as the sensor gave them.
- **Mono has no CFA**, no white-balance gains and no cast, so every quad is trivially converged there.
  The rule must stay off it.
- **The pure headers stay libcamera-free** (`clip_convergence.hpp`, `clip_plateau.hpp`,
  `clip_neutralise.hpp`, `ccmp_preview.hpp`) so the tests compile against nothing but the standard
  library. CI compiles each test directly with `g++`; there is no meson on the runner.
- **House test pattern**: a small `check(cond, name)` helper and a `main()` returning non-zero. No gtest,
  no catch2, no new dependency.
- **A test must fail against the unfixed code, and you must check that it does.** A test that passes
  against broken code is worse than no test.

## What to report back, and when

You have no camera and no takes. Stop and hand over at each of these, with your prediction written down
first:

1. After phase 2's instrumentation and cost work: the timing test above.
2. After phase 3: one look at a tungsten lamp in 12-bit HD, the mode where the edge is worst.
3. Before any phase 4 option: the numbers that justify it.

Between checkpoints, work off-hardware and keep the unit tests green.

## Definition of done

- All four ClearHDR modes render blown highlights neutral, with no speckle and no chunky boundary.
- The periodic log line shows a median stage cost under 15 ms at 4K25, and the operator sees no more
  dropped frames than `dev` does.
- New tests cover both faults that reverted this work the first time: a cost regression and a ragged
  edge. Each fails against the code as it stands today.
- The three operator-confirmed configurations do not regress: 16-bit 4K clean, 16-bit HD clean, and the
  12-bit blown core neutral.
