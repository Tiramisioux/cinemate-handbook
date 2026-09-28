# Changing a sensor's mode table

Adding, removing or reordering a mode in `imx585.c` or `imx283.c` looks like editing a list.
It is not: the array's **position** carries meaning, its **advertised sizes** must be unique,
and the fps a new entry will report is decided by arithmetic that is easy to guess wrong.
Three sessions have now rediscovered at least one of those. This page is the durable version.

It covers the driver side. What CineMate then does with the modes it is handed —
the two-probe parse, the settings filters — is in
[`../architecture/cinemate.md`](../architecture/cinemate.md); the offline way to test that
half without a camera is in [`testing.md`](testing.md).

## Position in the array decides which capture modes an entry is offered in

`imx585_get_mode_table()` hands out **contiguous ranges** of `supported_modes[]`, one per
pixel format. It does not filter by a per-entry flag. So where an entry sits is the only thing
that says whether it is offered in 12-bit Clear HDR, in SDR, or in RAW16:

| range | meaning |
|---|---|
| `[IMX585_MODE_1080P_12BIT .. IMX585_MODE_CROP_1440X1080_HDR12]` | 12-bit Clear HDR (CCMP) |
| `[IMX585_MODE_1080P_12BIT, IMX585_MODE_4K_16BIT_HDR)` | 12-bit SDR |
| `[IMX585_MODE_4K_16BIT_HDR .. IMX585_MODE_1080P_16BIT_HDR]` | 16-bit Clear HDR |

WP-585-9 exploited this deliberately: the windowed 2x2 crops were **moved** to sit after the
HDR-12 crop, which is what keeps them out of Clear HDR. Nothing about those entries says
"SDR only" — their index does. Three `static_assert`s next to the enum pin the arrangement, so
a reordering fails the build instead of silently re-opening Clear HDR to modes a hardware gate
is meant to be holding back:

```c
static_assert(IMX585_MODE_1080P_12BIT == 0);
static_assert(IMX585_MODE_CROP_1440X1080_HDR12 + 1 == IMX585_MODE_CROP_BIN_1080X1080);
static_assert(IMX585_MODE_CROP_BIN_1024X400 + 1 == IMX585_MODE_4K_16BIT_HDR);
```

**Appending to the windowed-2x2 block means moving the third assert to the new last entry.**
That is not bookkeeping; the assert is the only thing checking the gate still holds.

## Two entries may never advertise the same WxH

`v4l2_find_nearest_size()` picks the first match, so a duplicate advertised size makes one of
the pair **permanently unreachable** — it appears in `--list-cameras` and can never be
selected. This is the failure WP-585-5 and WP-585-8 are both about, and it is the single most
common defect in this area.

RAW16 entries collide in a way that is easy to miss, because a RAW16 entry does not advertise
its window: the sensor prepends optical-black rows, so the advertised height is

- 1x1: `crop.height + 2 * IMX585_PIXEL_ARRAY_TOP_4K` (= window + 40)
- 2x2: `crop.height / 2 + IMX585_PIXEL_ARRAY_TOP_4K` (= window/2 + 20)

So a RAW16 window of 1920x1040 advertises **1920x1080**, which is `IMX585_MODE_1080P_12BIT`.
It reads as a 1.85:1 crop and collides with the binned full frame.

The offset cuts both ways, and the result is counterintuitive: at a 1920-wide window the
16-bit family is *more* complete than the SDR one — ten ratios against three — because the
+40 shifts the RAW16 entries clear of the sizes the pre-existing 3840-wide 2x2-binned family
already owns, while the SDR entries land straight on them.

## Frame rate comes from the window's HEIGHT, never its width

```
fps = 74.25e6 / (HMAX x VMAX)
```

`imx585_update_hmax()` derives both, and **the window width appears in neither**:

```
min_hmax = hmax_table[link_freq_idx] * lane_scale / hmax_div   (Clear HDR: floored at 550)
min_vmax = windowed ? IMX585_CROP_VMAX(crop.height + (raw16 ? 20 : 0)) * hdr_scale
                    : IMX585_VMAX_DEFAULT (2250) * hdr_scale
```

A 1920-wide window therefore runs at **exactly** the frame rate of a 3840-wide window of the
same height. Narrow crops are framing modes, not speed modes. The speed they do buy over the
full frame is entirely the reduced height: 97.8 fps at 1920x1080 against 50.0 at full 4K, SDR
at 720 MHz. Sanity check the arithmetic against a known value — full-field 4K at 720 MHz is
`74.25e6 / (660 x 2250)` = 50.00, which is what `resources/sensors.json` records.

**Do not infer HMAX from the fps in `--list-cameras`.** Doing that on a real capture suggested
HMAX varying with width (~1514 at 3840 wide, ~1126 at 2880) and a floor reached around 2880.
The driver predicts about 1% between those two entries, not 35%. Whatever produces that
difference is above the driver, and it is still unexplained — so a width-related fps claim
needs hardware, not a listing.

## The crop rectangle is in native sensor pixels, and the invariant is checked

`mode->crop` is sensor-domain at every binning — `imx585_program_window()` writes it to the
WINMODE registers unmultiplied, and libcamera derives its own binning from
`analogCrop.width / outputSize.width`. The invariant every entry must satisfy:

| entry kind | crop.width | crop.height |
|---|---|---|
| non-RAW16, binning b | `width * b` | `height * b` |
| RAW16, 1x1 | `width` | `height - 40` |
| RAW16, 2x2 | `width * 2` | `(height - 20) * 2` |

`imx585_program_window()` then rejects a window that is not aligned:

```c
hst = IMX585_PIXEL_ARRAY_LEFT + crop.left;   vst = 12 + crop.top;
reject if  crop.width < 64 || crop.width > 3840 || crop.height < 239 || crop.height > 2160
        || (hst & 1) || (crop.width & 15) || (vst & 3) || (crop.height & 3) || !hst
```

In practice: width a multiple of 16, height a multiple of 4, `crop.top` a multiple of 4, and
`crop.left` even. Centred origins for common widths — 1920 → 960, 2048 → 896 — all qualify.

## Windowed 2x2 RAW16 does not work on this sensor

WP-585-8 withdrew every one of them: on hardware a windowed, 2x2-binned RAW16 entry returns
the optical-black pedestal rather than an image, confirmed by four takes with byte-level
analysis. The probe-time audit warns on any `raw16 && windowed && binning == 2` entry
specifically so nobody re-adds one. Binned Clear HDR is full-field only.

## Check the table before you build

`imx585_check_mode_table()` runs at probe and `dev_warn()`s every violation above — but only
on hardware, at insmod, into `dmesg`. For a desk review, replay it:

```
python3 tools/replay_mode_table_audit.py     # ports the C audit + the crop invariant
python3 tools/check_window_alignment.py      # replays program_window()'s reject predicate
```

Both live in the driver repo and take no arguments. They parse `imx585.c` itself, so they
also catch structural damage — a botched merge that left the array one brace short showed up
here as a truncated entry count before anything else noticed.

Run the audit against the **base branch too** when you inherit a warning, to separate what you
introduced from what was already there:

```
git show <base>:imx585.c > /tmp/base.c    # then point the script at it
```

## Before you start: get the branch right

`cinemate-modes` is the driver's default branch and what `cinemate-install.sh` pins
(`IMX585_DRIVER_REPO_REF`). Base new work on it. `cinemate-7modes` was the default and the pin
until 2026-09-27 and is now neither; `experimental-cropped-modes-v2` is the ancestor that
introduced the windowed machinery, and is three commits behind the gate work that the
`static_assert`s above belong to — branching from it will produce a table that does not build
on the current default.
