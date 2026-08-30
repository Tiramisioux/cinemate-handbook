# IMX585 Clear HDR light-at-startup clamp — external research findings

**Status: IN PROGRESS.** Cloud research session, started 2026-08-30. Sections land incrementally,
one commit per research question; a section marked *(pending)* has not been researched yet, and
a section marked *(complete)* has had its lane finished and committed. Evidence lanes are
strictly labelled: **[doc]** = documented fact (verbatim quote + URL) · **[anecdote]** =
community report (URL, date, hardware, closeness of match) · **[inference]** = reasoning,
explicitly ours. Everything here is EXTERNAL evidence; the hardware fingerprint itself is
established in `lessons/hardware-log.md` (campaign rounds 0.1–3.3) and
`lessons/clearhdr-instability-report.md`, and is not re-argued here.

---

## 1. Headline

*(pending — written last, after Q1–Q6.)*

---

## 2. Findings per research question

### Q1 — Sony primary documentation (IMX585 datasheet / appnotes / errata)

*(complete — researched 2026-08-30/31. Environment caveat: this cloud session's egress proxy
blocks sony-semicon.com, dl.khadas.com, lcsc.com, scribd.com, framos.com and most mirrors, so
several primary-document items below are search-snippet evidence, labelled as such. Driver
commit/comment quotes and the INNO-MAKER manual were verified first-hand from local clones —
including a re-extraction of the manual PDF's text by the overseer session.)*

**Ranked result: no public Sony text documents a light-at-startup condition, a combine-stage
initialization step, a wait-frame rule, or any errata for the IMX585. But every documented
failure semantics for a mis-configured Clear HDR combine is "outputs the BLC pedestal" — our
clamp exactly matches the documented fallback's *signature* while matching none of its
documented *triggers*.**

#### [doc] — AppNote content as quoted by the driver lineage (secondary evidence: these are
Will Whang's comments/commit messages quoting the NDA AppNote, in will127534/imx585-v4l2-driver;
commits verified first-hand in a local clone with full history)

1. **Prohibited EXP_TH order → pedestal-only.** imx585.c:1531–1536 and commit 954a52a
   ("imx585: fix prohibited hdr_thresh_def per AppNote §4.2", 2026-05-13): *"EXP_TH_H <
   EXP_TH_L is explicitly marked 'Prohibited' in the IMX585 application note §4.2. Under that
   condition the sensor emits only the BLC pedestal (~50) for the entire frame: every pixel is
   below threshold so HG selection is disabled and LG is multiplied by zero by the blend
   logic."* Also: *"Test patterns work fine (they bypass the pixel array entirely)."* Only
   "Prohibited" is verbatim spec text; the mechanism sentence is the maintainer's gloss.
   <https://github.com/will127534/imx585-v4l2-driver/commit/954a52a>
2. **Even the AppNote's own initial value clamps near BLC.** Commit be3cb94 ("Fix EXP_TH
   default — AppNote 'blend off' config clamps signal at BLC", 2026-05-13): *"The AppNote
   (§4.2 page 15) lists 0x1000 each as the 'initial value' for EXP_TH_H / EXP_TH_L, with the
   equality case routing through the EXP_BK weighted-blend path. Empirically that path leaves
   the HG/LG combiner output stuck at the BLC pedestal for typical scenes: Before fix
   (TH_H=TH_L=0x1000): HDR-16 DNG max ≈ 4200 (basically BLC). After fix (TH_H=0xFFF, TH_L=0):
   … ≈ 36000 (signal!)"* — i.e. the spec-blessed default drives the combiner into a
   pedestal-adjacent state on real scenes.
3. **Out-of-range ACMP slopes → BLC-clamped output.** imx585.c:1583–1593 / commit 1ac3cec:
   ACMP1_EXP allowed 06h–0Bh, ACMP2_EXP allowed 00h–05h per *"IMX585 ClearHDR AppNote Rev1.0
   page 16"*; *"Writing a prohibited value puts the sensor into a degenerate state and the
   output ends up clamped at BLC for all pixels"* (pre-fix measurement: *"CCMP-12 DNG had
   min=max=mean=BLC (3200) across all pixels"*).
4. **EXP_BK prohibited indices.** imx585.c:333–335: *"EXP_BK register values per AppNote §4.2
   page 15. Indices 0–7 are valid; higher values are 'Setting Prohibited'."* Commit 1eff18f
   additionally fixed an off-by-one that could write *"the 'Setting Prohibited' value 8"* to
   the blender register.
5. **Invalid mode pairing → "returns BLC".** imx585.c:1012–1015: *"Per AppNote §2 page 6, the
   1920×1080 binning mode in Clear HDR only supports 16-bit output — 12-bit binned HDR is not
   a valid sensor configuration and the part returns BLC if asked."* Sony's documented failure
   semantics for invalid Clear HDR configurations is precisely "return the black level".
6. **Documented engage-window constraints (none light-dependent).** imx585.c:123–130: SHR0
   minimum "More than 8h" Normal / "More than 10h" Clear HDR (AppNote p.5 "List of Setting
   Register"); imx585.c:165–168: GAIN 00h–50h and the §5 p.18 sum constraint
   *"9.6 dB ≤ GAIN + EXP_GAIN ≤ 29.1 dB for built-in combination"*.
7. **Stateful, content-driven latching inside the HDR path (empirical, two independent
   drivers).** imx585.c:223–231: in Clear HDR *"the OB rows contain stuck pixels that latch at
   the HG saturation value (~35968)"*; independently, Kurokesu/imx585-rpi-driver imx585.c:202–206
   (v0.2.0, 2026-08-27): *"In Clear HDR they latch at the HG saturation value and show as a
   speckle band if left in."* Not AppNote text — but direct evidence the combine/data-selection
   stage carries pixel-content-driven latch state.

#### [doc] — Sony primary documents: what exists and where

8. **Sony flyer, IMX585-AAQJ1** (snippet only — not fetched; sony-semicon.com egress-blocked):
   *"When the Clear HDR feature is on, the image sensor captures two images simultaneously, one
   with a low gain level set to the bright region and the other with a high gain level adjusted
   to the dark region. The images are then synthesized."*
   <https://www.sony-semicon.com/files/62/flyer_security/IMX585-AAQJ1_Flyer.pdf>
9. **Sony flyer, IMX585-AAMJ1 (mono)** (snippet only): *"supports RAW10 / RAW12 / RAW16 (Clear
   HDR) output"* — the mono variant officially carries Clear HDR.
   <https://www.sony-semicon.com/files/62/flyer_security/IMX585-AAMJ1_Flyer.pdf>
10. **The obtainable primary-doc set**: a "IMX585-AAQJ1-C TechnicalDatasheet E Rev 0.2" exists
    (Scribd upload title; mirrors at LCSC and
    <https://dl.khadas.com/products/add-ons/cameras/imx585/datasheet/imx585-datasheet.pdf> —
    all egress-blocked here; the Khadas mirror's search metadata says 1,350,034 bytes, updated
    2025-07-22, first line "Copyright 2018 Sony Semiconductor Solutions Corporation" — the 2018
    date is anomalous for a 2021+ part, verify before relying on it). The datasheet references
    an **"IMX585_Standard_Register_Setting" Excel file** and per-function **application notes**
    (snippet-level evidence); the driver pins the HDR one as **"IMX585 ClearHDR AppNote Rev
    1.0"** (imx585.c:1583). Full set is distributed via RESTAR FRAMOS / Soho Enterprise /
    e-con / INNO-MAKER after inquiry (NDA-ish), so the campaign CAN obtain §2–§5 in full.
11. **INNO-MAKER CAM-IMX585 user manual** (read first-hand from the vendor repo clone;
    text re-extracted and quote-verified by the overseer): §5.3 *"ClearHDR also has a lower
    maximum exposure (~4484 lines). If --shutter exceeds this limit, the result is a fully
    black frame."* Troubleshooting table: *"Fully black after enabling ClearHDR — --shutter
    exceeds ClearHDR exposure limit — Reduce --shutter (e.g. 200–2000 µs)"*; control table
    gives ClearHDR exposure range 2–4484 lines. A second vendor-documented all-black ClearHDR
    condition — exposure-triggered, not illumination-triggered.
    <https://github.com/INNO-MAKER/CAM-IMX585>
12. **Nothing found — startup ordering / wait-frame / settle requirements**: no "set before
    streaming" note, no calibration-frames caveat, no prohibited-transition list anywhere
    public. Queries tried: `"IMX585" OR "IMX678" "Clear HDR" appnote "wait" OR "settle" OR
    "invalid" frames after mode set`; `IMX585 "Standard Register Setting"`; `"EXP_TH" pedestal
    prohibited threshold`.
13. **Nothing found — errata / technical notices**: `"IMX585" errata OR "technical notice" OR
    "known issue" Sony sensor` → nothing; GitHub-wide code/issue searches for IMX585 vendor SDK
    headers (`imx585_cmos.c`, `COMBI_EN WDMODE`, `"0x36d0" imx585`) → no public vendor SDK
    exists for this part.
14. **Mainline status**: "[PATCH v3 0/2] media: Add Sony IMX585 image sensor support", Will
    Whang, 2025-08-16 (lore/spinics; snippet only — archives egress-blocked): v3 *removed* the
    driver-specific HDR tuning controls; not merged into torvalds/linux as of today.

#### [anecdote]

- Cloudy Nights topic 960063 "Player One Uranus-M Pro (IMX585) Update on HDR mode" (snippet
  only — domain blocked): Player One added IMX585 "HDR mode" via driver 3.9.0/DLL updates; an
  AstroBin report of "terrible results" after enabling. Same silicon, different (USB/FPGA)
  controller; shows vendor-side Clear HDR enablement was non-trivial. Match: medium-low (no
  pedestal-clamp description at snippet level).
- will127534/imx585-v4l2-driver issue #17 (2026-07-17): ACMP gradation controls can't be set
  independently — same combine block, plumbing-level only. Issues #1–#18 contain **no**
  black-at-lit-start report.

#### [inference]

- Every publicly documented pedestal-only condition for IMX585 Clear HDR is a **static
  register-validity** condition (EXP_TH order; ACMP range; EXP_BK range; invalid binned-12-bit
  mode; over-limit exposure). Our clamp — valid registers, engage-time scene dependence,
  in-stream hysteresis releases — appears in no public Sony-derived text. If Sony documents it
  at all, it is in unseen sections of the NDA AppNote/datasheet or in a non-public technical
  notice.
- The convergent picture (invalid configs "return BLC"; the spec-default blend path clamps near
  BLC on real scenes; OB pixels latch at HG saturation) supports reading "output the pedestal"
  as the combine stage's **generic fallback state**, reachable both by static mis-configuration
  and — per our hardware evidence — by an undocumented engage-time condition involving uniform
  illumination. The registers select *into* this fallback; they evidently do not *report* it.

### Q2 — Same-architecture siblings (IMX678 / IMX675 / IMX664 / IMX662 / IMX485)

*(complete — researched 2026-08-30/31. Same egress caveat as Q1/Q3: non-GitHub sources are
snippet-only, labelled. All driver-source quotes below were read from local clones and the
three load-bearing FRAMOS facts (items 2–4) were independently re-verified line-by-line by the
overseer session.)*

**Ranked result: no sibling document describes our fingerprint — but the sibling ecosystem
proves the combine/data-selection stage is a separable, bypassable block, and two shipping
vendor configurations bypass or de-fang exactly the stage our clamp lives in.**

#### [doc]

1. **WDMODE is a path selector, and Sony's own reference Clear HDR for IMX662/IMX678 emits
   HG/LG as two UNCOMBINED streams (WDMODE=0x08), fusing on the SoC.**
   framosimaging/framos-nxp-drivers, `isp-vvcam/.../imx662/imx662_regs.h:335–351`
   (overseer-verified): `imx662_setting_clear_hdr[] = { {WINMODE,0x00}, {WDMODE,0x08},
   {ADDMODE,0x00}, … {FDG_SEL0,0x02}, {EXP_GAIN,0x02}, … {0x3460,0x22}, {0x3C40,0x05} }`, with
   `.stitching_mode = SENSOR_STITCHING_DUAL_DCG_NOWAIT` (imx662_mipi.c:606). Same for IMX678
   (imx678_regs.h: WDMODE 0x01 = DOL at :538, 0x08 = Clear HDR dual-stream at :557, plus a
   large undocumented-register block). **The HG/LG chains exist and can be output around the
   combiner — the on-chip combine (our WDMODE=0x10 + COMBI_EN=0x02) is architecturally
   separable from readout.** <https://github.com/framosimaging/framos-nxp-drivers>
2. **FRAMOS's official IMX585 Jetson driver runs 16-bit Clear HDR with COMBI_EN=0x00.**
   framosimaging/framos-jetson-drivers, `fr_imx585_mode_tbls.h:200–206` (overseer-verified):
   `imx585_clearHDR_16bit_mode[] = { {MDBIT,0x03}, {COMBI_EN,0x00}, … }`, applied ON TOP of
   the 12-bit Clear HDR table (WDMODE=0x10, COMBI_EN=0x02) by `fr_imx585.c:860–875` for
   SRGGB16. Our rig's 16-bit mode keeps COMBI_EN=0x02. A shipping vendor driver treats
   "built-in combination" as optional in the exact bit depth we fail in.
   <https://github.com/framosimaging/framos-jetson-drivers>
3. **FRAMOS ships Sony's "initial value" thresholds as defaults, in a 13-bit domain.**
   `fr_imx585.c:147–168` (overseer-verified): custom controls "Exposure threshold low/high",
   `.def = 0x1000`, `.max = 0x1FFF` — the equal-threshold configuration that our lineage's
   commit be3cb94 measured as near-BLC on real scenes. The 0x1FFF ceiling implies data
   selection compares in a 13-bit domain (12-bit ADC + 1 bit headroom).
4. **FRAMOS's start sequence differs from ours at the engage moment**: `imx585_start[]`
   (fr_imx585_mode_tbls.h:133–139, overseer-verified) = STANDBY=0x00 → **wait 30 ms** → XMSTA
   0x00; per-table settle `IMX585_WAIT_MS` = 10 ms. Ours writes XMSTA=0 *before* standby
   release with no wait (Q4 baseline step 7). No wait-frames, no illumination precondition,
   no combine-init note anywhere in the FRAMOS driver either.
5. **Clear HDR flips "reserved" analog registers on siblings.** IMX662 Clear HDR requires
   0x3C40 06h→05h and 0x3460 21h→22h (FRAMOS table above; independently corroborated by
   will127534/imx662-v4l2-driver imx662.c:255: *"{0x3C40, 0x06}, // Normal mode. CHDR=05h"*).
   Sony's reference settings change undocumented analog-domain registers between Normal and
   Clear HDR — a class of hidden state the register readback can't audit.
6. **Register-map identity across the family is confirmed.** AraKiLiu/imx662-v4l2-driver
   imx662.c:268–286 names 0x3069 = CHDR_GAIN_EN and per-channel CHDR HG/LG gain registers;
   EXP_TH_H/L, EXP_BK, CCMP1/2_EXP, ACMP1/2_EXP sit at identical addresses to IMX585
   (0x36D0/0x36D4/0x36E2/…). Sibling findings transfer.
7. **Runtime constraint on the HG/LG path during CHDR streaming**: FRAMOS NXP imx662_mipi.c:
   1548–1551: *"Default value for conversion gain should not be changed in Clear HDR stream"*
   (FDG_SEL0 writes refused while streaming CHDR).
8. **A shipping third-party IMX585 driver contains the ACMP-swap that produces all-BLC
   frames**: octopuscinema/linux-camera-support `drivers/media/i2c/imx585.c:1432–1434` writes
   ACMP1_EXP=0x2 / ACMP2_EXP=0x6 — exactly the out-of-range configuration our lineage's
   annotation says "produced all-BLC frames in 12-bit ClearHDR mode". (OCTOPUS uses a valid
   EXP_TH pair 4095/512.) The BLC-pedestal degenerate state is easy to ship accidentally.
9. **Sony's official Clear HDR description** (snippet only): the sensor *"captures two images
   simultaneously, one with a low gain level set to the bright region and the other with a
   high gain level adjusted to the dark region, and the images are then synthesized"*; Clear
   HDR listed for IMX585/662/664/675/678 (+832/835/838). **IMX485 is DOL-only** (snippets) —
   the predecessor doesn't carry the suspect stage.
10. **Sibling manuals exist publicly but were unfetchable here**: "IMX678 Software Reference
    Manual E Rev 4.0" (Scribd id 897816949; CSDN mirror announcement); IMX678/IMX585
    datasheets on dl.khadas.com; ModalAI M0186 IMX664 page (*"75.8 dB in a single exposure"*,
    snippet). Obtainable from any unproxied machine — worth harvesting for combine-stage
    detail beyond our AppNote.
11. **Negative results (read in full, not snippets)**: no black-frame/HDR-startup issue in the
    trackers of will127534/imx585-v4l2-driver (8 issues), will127534/imx678-v4l2-driver (1),
    framosimaging/framos-jetson-drivers (9). FRAMOS implements Clear HDR only for IMX585 on
    Jetson (fr_imx678/675/662 tables are DOL-only); Hailo's IMX678 driver is 3-DOL only; VC
    MIPI's Jetson IMX585 driver exposes SDR only (init lives in VC's module MCU). Mainline:
    Will Whang's IMX585 v3 submission (2025-08-16) dropped Clear HDR support after review, so
    no mainline review discussion of the combine exists.

#### [anecdote] (ranked by closeness)

1. **"One frame entirely black" named as the Clear HDR fusion-failure signature for IMX662**
   (snippet only — piveral.com mirror of NVIDIA forum content): *"If one frame is entirely
   black in Clear HDR mode for the IMX662, this indicates a failure in fusion; check gain and
   exposure configurations accordingly."* Closest sibling text to whole-frame black-in-CHDR.
2. **IMX662 Clear HDR "did not look like the merged image" on Jetson Orin Nano**
   (forums.developer.nvidia.com t/264319, ~2023, snippet only): brightness jumped, noisy,
   unmerged; a *"fusion logic error … was fixed in the r35.4.1 release"* (SoC-side fix).
   Match: combine misbehaving at enablement; not pedestal-black, not sensor-side.
3. **IMX662 Clear HDR on i.MX8MP: stream starts, Frame Start/End events, no video output**
   (community.nxp.com td-p/2071177, snippet only) — dual-VC CHDR bring-up difficulty.
4. **IMX585 Clear HDR pink band on Pi 5** (forums.raspberrypi.com t=388520, snippet only —
   also in Q3): a luminance band renders wrong around a data-selection threshold.
5. **IMX678 Clear HDR effectively unavailable to end users** (NVIDIA forum t/211377, snippet
   only): as of that thread only QHYCCD/ToupTek firmware exposed it — explains sibling silence.
6. **Hackaday 2026-03-19 on IMX585 Pi HDR** (snippet only): *"a lot of the standard white
   balance and image control algorithms don't work, and image preview can be unusable at
   times."*

#### [inference]

1. WDMODE decodes as a path selector (0x01 DOL / 0x08 CHDR-dual-stream-uncombined / 0x10
   CHDR-with-on-chip-combine). Since Sony's own reference emits HG/LG *around* the combiner on
   siblings, the combiner/data-selection block is separable — consistent with our clamp living
   exactly there while defect pixels ride through.
2. The sibling ecosystem never exercises our exact path: Jetson/FRAMOS ships near-BLC
   equal-threshold defaults users tune away; NXP bypasses the on-chip combiner entirely; astro
   vendors run their own FPGA firmware. The on-chip-combine + valid-threshold path is
   essentially a Raspberry-Pi-lineage exclusive (will127534, Kurokesu, OCTOPUS) — which is
   precisely where the only two "black in Clear HDR" caveats appear.
3. A comparator/selection state armed at stream start under bright input, in a 13-bit compare
   domain, would clamp all output to BLC until the signal crosses back under a release
   condition — consistent with dark-release and short-integration-release both working while
   *more* light never releases.

### Q3 — Community corroboration (forums, GitHub issues, firmware changelogs)

*(complete — researched 2026-08-30/31. Environment caveat: the egress proxy blocks nearly every
forum domain (forums.raspberrypi.com, cloudynights.com, stargazerslounge.com, bbs.zwoastro.com,
ipcamtalk.com, forums.sharpcap.co.uk, forum.arducam.com, astrobin, NVIDIA developer forums,
lore.kernel.org, patchwork.linuxtv.org, web.archive.org…); GitHub was fully reachable. Forum
items below are search-snippet evidence, honestly labelled. Independence caveat: the strongest
[doc] items live in the upstream repo of our own driver lineage, so they are corroboration of
the AppNote and of register-caused pedestal states, not independent discovery of our bug.)*

**Ranked result: the exact fingerprint — lit-start exact-pedestal clamp, dark-start immunity,
one-way in-stream release by short-integration command or covering — is unreported anywhere
reachable. The nearest cousins: the driver lineage's own three register-caused pedestal
states; an independent company (Kurokesu) shipping this sensor+driver family with a written
"bright parts can render black" Clear HDR warning; and the ToupTek IMX585 OEM family needing
camera-firmware revisions to fix broken HDR output.**

#### [doc]

1. **Prohibited EXP_TH order → pedestal-only** — upstream commit 954a52a (2026-05-13), fetched
   and quoted in full under Q1 item 1. *"Symptom: enable ClearHDR (wide_dynamic_range=1) on a
   4K all-pixel mode and the output is a flat solid colour at BLC level regardless of scene."*
   <https://github.com/will127534/imx585-v4l2-driver/commit/954a52a>
2. **Out-of-spec ACMP defaults → all output clamped to black level** — commit 1ac3cec:
   *"causing the sensor to enter a degenerate state where all pixel output was clamped to
   black level."* <https://github.com/will127534/imx585-v4l2-driver/commit/1ac3cec>
3. **"Write sane register defaults at ClearHDR stream start"** — commit 1eff18f: writes
   spec-valid combine defaults in `common_clearHDR_mode` *"so the sensor always starts in a
   valid state regardless of V4L2 control init order"*, and fixes a menu off-by-one that could
   write *"the 'Setting Prohibited' value 8"* to the blender register. The lineage's own
   history is one long fight with combine-stage validity at stream start.
   <https://github.com/will127534/imx585-v4l2-driver/commit/1eff18f>
4. **Kurokesu (independent camera company) ships this sensor+driver family with a written
   Clear HDR warning** — Kurokesu/imx585-rpi-driver README, commit c29030e (2026-08-28):
   *"Clear HDR is experimental and not yet tuned. Bright parts of a scene can render black in
   both 16-bit and 12-bit output."* No start-condition or release-trigger detail. Their Jetson
   driver has Clear HDR only *"planned"*.
   <https://github.com/Kurokesu/imx585-rpi-driver/commit/c29030e>
5. **ToupTek IMX585 OEM family (ATR585C/M + Altair/OGMA/Meade rebrands) shipped camera-firmware
   fixes specifically for broken HDR mode** (snippet only — forums.sharpcap.co.uk blocked):
   FPGA firmware 4.43 (cooled colour) / 4.49 (mono) / 5.6 (uncooled) + driver dated
   2025-01-21; per snippets SharpCap's developer obtained unpublished firmware from ToupTek
   and *"with this update the HDR seems fixed"* (threads t=8307 "IMX585 Firmware updates for
   ToupTek cameras", t=8289).

#### [anecdote] (ranked by closeness of match)

1. **Raspberry Pi Forums t=388520, "With ClearHDR enabled on IMX585, part of the picture turns
   pink"** (2025-06-03; RPi 5 + IMX585 Clear HDR, raw DNG; snippet only — domain blocked): a
   luminance band renders pink; replies note *"problems when some of the colour channels
   saturate, but not others, and the way the sensor is combining the low and high gain images
   seems to be incorrect"*, with raw files implicating the sensor. Match: HDR-only ✓, on-chip
   HG/LG combine misbehaving around a data-selection threshold ✓, sensor-level ✓; black clamp
   ✗, start-condition ✗, release ✗. The closest public sibling of our mechanism family.
2. **SharpCap forums t=8289, ToupTek ATR585C HDR breakage** (~2024-11; snippet only): *"HDR
   mode was doing weird things… invalid results in the sensor analysis and really bad images
   when the brightness level is low"* — fixed by the firmware in [doc] 5. Match: HDR-only ✓,
   light-level-dependent ✓ (inverted polarity); pedestal clamp ✗.
3. **GitHub indilib/indi-3rdparty #1133, "Touptek 585-based cameras still disfunctional"**
   (2025-08-07, Touptek 585C, libindi 2.1.4; fetched): *"Images taken with HDR are either
   good, or half-downloaded, or have color artifacts"*; hangs. Related #1114 (ATR585M hangs on
   Mono16 after firmware update). Match: IMX585 HDR-mode instability ✓; black-at-start ✗.
   <https://github.com/indilib/indi-3rdparty/issues/1133>
4. **Cloudy Nights topic 945637 p.6, QHY miniCAM8 (IMX585)** (snippet only): after a 2025
   driver/SDK update, *"the only way to take images with correct gain and offset is to keep
   the camera in 'Full Resolution' mode rather than HDR mode"*. Match: HDR-only settings
   dysfunction ✓; black frames ✗.
5. **Cloudy Nights topics 918015 / 900797 (ToupTek 585CP / "HDR mode on Touptek Camera")**
   (snippets only): *"HDR mode doesn't work properly"*; users flashing FPGA v4.35 to get HDR
   working; *"the Touptek 585 ignores the set offset in HDR mode and uses 512 no matter
   what you set."* Match: HDR-only ✓, firmware-fix trail ✓; black-at-start ✗.
6. **will127534/StarlightEye #26 "Clear HDR mode"** (2025-09-29, open, zero replies; fetched):
   only asks how to enable Clear HDR from picamera2 — included as evidence of how thin the
   direct-Clear-HDR user base is. <https://github.com/will127534/StarlightEye/issues/26>

**Explicit nothing-found:** GitHub-wide issue searches `imx585 hdr black` (0), `imx585 "no
image"` (2 irrelevant), `"wide_dynamic_range" imx585` (0), `imx678 hdr` (1 irrelevant); all 8
issues in will127534/imx585-v4l2-driver, 3 in Kurokesu, 3 in INNO-MAKER/CAM-IMX585, 0 in
Apertar-D1, 3 imx585 issues in raspberrypi/libcamera (format-related) enumerated — none
matches; nothing on ZWO forum, Reddit, EEVblog, Khadas, or in Chinese (IMX585 HDR 黑屏) /
Japanese (IMX585 HDR 真っ黒) searches. Full query log preserved in the session record.

#### [inference]

1. External evidence establishes at least three *register-caused* ways the IMX585 Clear HDR
   combine emits exactly the frame-wide black pedestal — proving a reachable "degenerate state
   whose output is precisely BLC pedestal", the same visual signature as ours. Every
   documented case is static and register-caused; ours is register-invisible and
   light-history-dependent. That arm appears genuinely unreported.
2. Kurokesu's "bright parts of a scene can render black" is the only independent-company field
   observation of content-dependent black rendering in Clear HDR; a uniformly bright scene
   under that description would render fully black — possibly a partial, uncharacterized
   sighting of our lit-start clamp.
3. The community silence is plausibly a population artifact: ZWO/Player One/QHY expose
   dual-gain HDR through their own FPGA/SDK paths (with their own HDR firmware bugs), not raw
   on-chip Clear HDR registers; the population driving Clear HDR directly is essentially the
   small Pi-driver crowd — and astro users start their streams in darkness, precisely the arm
   of the fingerprint where the bug is invisible.

### Q4 — Driver-implementation comparison (Clear HDR enable sequencing)

*(complete — researched 2026-08-30/31. Our-stack baseline read first-hand by the overseer;
external drivers read from local clones by the research agent, with the youjunl and FRAMOS
key claims re-verified line-by-line by the overseer.)*

**Ranked result: no publicly visible driver implements ANY deliberate startup workaround —
no dummy/masked first frames, no forced short-exposure kick, no HDR-enable-after-stream, no
double start, no HDR-specific settle delay. Every Clear HDR implementation writes the full
HDR configuration in standby and releases standby last. If the lit-start clamp is intrinsic
silicon behaviour, nobody upstream has knowingly coded around it. The only workaround-shaped
text anywhere is INNO-MAKER's user advice "if the image goes black … reduce --shutter" —
operationally the same move as our reliable SHR-kick release.**

#### Baseline: our own driver's engage sequence (read from source, first-hand)

`[doc]` — will127534/imx585-v4l2-driver, branch `main` @ 70bdb26 ("imx585: gate 12-bit CCMP
Clear HDR behind a dtoverlay param") — which is byte-identical to the rig's running driver
(hardware-log rounds 0.1–3.3 verified this by on-Pi source diff). Read from a local clone of
<https://github.com/will127534/imx585-v4l2-driver>. The complete Clear HDR bring-up order in
`imx585_enable_streams()` (imx585.c:1900–2049):

1. `pm_runtime_get_sync` → `imx585_power_on`: regulators on → INCK on → XCLR high →
   **500 ms wait** (`IMX585_XCLR_MIN_DELAY_US = 500000`, imx585.c:58).
2. Sensor still in its power-on standby. `common_regs` (226 writes) → INCK_SEL →
   BLKLEVEL=50 → DATARATE_SEL → LANEMODE → BIN_MODE → XVS/XHS sync config.
3. Mode table (ADDMODE, ADBIT, MDBIT, window crop).
4. `common_clearHDR_mode` (imx585.c:510–545), in this order: **WDMODE 0x301A=0x10 is the
   FIRST write of the block, COMBI_EN 0x3024=0x02 the second**, then 0x3069/0x3074/DUR/
   0x3A4C/0x3A50/ADTHEN/0x493C/0x4940, then EXP_GAIN 0x3081=+12 dB, then
   EXP_TH_H 0x36D0=0x0FFF, EXP_TH_L 0x36D4=0x0000, EXP_BK 0x36E2=0x00, then
   ACMP2_EXP=1/16, ACMP1_EXP=1/64. I.e. **the combine is enabled before its thresholds,
   blend weights, and slopes are programmed — but all of it happens inside standby.**
5. CCMP_EN + MDBIT override (16-bit linear: CCMP_EN=0), then DIGITAL_CLAMP=0.
6. VMAX/HMAX/SHR controls zeroed, then `__v4l2_ctrl_handler_setup()` replays every cached
   V4L2 control (imx585.c:2024).
7. **XMSTA 0x3002=0x00 is written BEFORE standby release**, then MODE_SELECT 0x3000=0x00
   (standby → streaming) with **no delay between them** (imx585.c:2031–2038); one 25 ms
   sleep after (`IMX585_STREAM_DELAY_US`, imx585.c:54).
8. Stop (imx585.c:2069) writes MODE_SELECT=STANDBY only — XMSTA is never returned to 1, so
   a within-power-window restart exits standby with XMSTA already low.

`[doc]` — the same file already carries two spec-anchored pedestal-clamp facts as comments
citing the (NDA) Sony AppNote: the data-selection threshold comment (imx585.c:523–533)
records that **the AppNote's own "initial value" EXP_TH_H = EXP_TH_L = 0x1000 "documents a
fallback to the EXP_BK weighted blend, but empirically that path leaves the combiner output
clamped near BLC for typical scenes"** (bench-verified on this hardware family), and the
gradation-compression comment (imx585.c:537–542) records that ACMP slopes outside their
allowed ranges mean "the sensor output clamps at BLC". The driver's constraint comment at
imx585.c:1534 records the AppNote marking EXP_TH_H < EXP_TH_L as prohibited. So the
combine/data-selection stage has at least three *documented or bench-measured* ways to sit
at pure pedestal with a live readout — our clamp is a fourth, condition-triggered one.

`[inference]` — structural facts that matter for the external comparison: our driver does
**no** dummy/masked first frames, no settle wait between HDR-enable and standby release
beyond I2C transaction time, no post-start re-write of any HDR register, no double
stream-start, and the engage moment (standby release under light) is exactly where the
clamp condition is set. Any external driver that inserts something at that moment —
thresholds before WDMODE, a wait-N-frames rule, a forced short-exposure first frame, a
masked-frame register — is a candidate fix template. Note also XMSTA-before-standby-release
with zero inter-write delay; if Sony's canonical start sequence (standby release → wait →
master start) differs, that is a concrete, testable deviation.

#### External comparison ([doc] unless noted; every driver read from source in a local clone)

**Sequencing table across every reachable implementation:**

| Driver | Clear HDR | EXP_TH written | HDR regs vs stream | Stream-on order | Delay | Dummy frames |
|---|---|---|---|---|---|---|
| will127534 main @ 70bdb26 (= our rig) | yes | 0x0FFF / 0 (in table) | all in standby | XMSTA=0 → 0x3000=0 | 25 ms after | no |
| will127534 old lineage (via Cine-Fox fork @ e82cf36, 2025-10-09) | yes | via ctrl default {512,1024} = the Prohibited pair | all in standby | same | 25 ms after | no |
| Kurokesu/imx585-rpi-driver @ cdd0214 (v0.2.0) | yes | 0x0FFF / 0 | all in standby | same | 25 ms after | no |
| FRAMOS fr_imx585 (l4t-r36.4.4) | yes | **never** (controls only → sensor default 0x1000/0x1000) | all in standby | **0x3000=0 → 40 ms → XMSTA** | between | no |
| youjunl/imx586-v4l2-driver @ e71e517 | yes | **0x0FFF / 512** + BK=0, written procedurally just before stream-on (imx586.c:1514–1519, overseer-verified) | all in standby | 0x3000=0 only (**no XMSTA write at all**) | 25 ms after | no |
| mainline imx678 (torvalds @ 2026-08-30) | no (SDR only) | – | – | 0x3000=0 → 25 ms → XMSTA | between | no |
| Rockchip BSP imx678 | DOL only | – | in standby (XMSTA in table) | 0x3000=0 last | – | no |
| OpenIPC/waybeam cv610 imx662 | no (deferred: *"Bring linear up first. Add Clear-HDR … later"*) | – | – | 0x3000=0 → XMSTA | 2 ms after | no |
| pauliustumas/imx662 | no | – | – | 0x3000=0 → 30 ms → XMSTA | between | no |
| VC MIPI IMX585 (vc_mipi_nvidia) | no (SDR only) | – | closed MCU firmware | n/a | – | unknown |
| Kurokesu/imx585-jetson-driver | no (SDR only) | – | – | XMSTA → 0x3000=0 | after | no |

Load-bearing observations:

1. **The old lineage shipped the Prohibited pair as its default** — Cine-Fox/imx585-v4l2-driver
   @ e82cf36 (2025-10-09): `common_clearHDR_mode` ends at EXP_GAIN with **no EXP_TH/EXP_BK/ACMP
   writes at all**, and `hdr_thresh_def[2] = { 512, 1024 }` applied via the control handler.
   This externally confirms the instability report's finding about the golden-era 6.12.y
   driver, from an independent fork snapshot.
2. **FRAMOS is the only other real Clear HDR implementation** and diverges from us at exactly
   the engage moment: standby release first, a 40 ms gap, then master start — the reverse
   pairing of ours — and thresholds left at the sensor's power-on 0x1000/0x1000 (the config
   commit be3cb94 measured as near-BLC). No EXP_TH/EXP_BK/EXP_GAIN in any FRAMOS table; no
   HDR-quirk comments.
3. **youjunl's independent early driver** writes a *nonzero* low threshold (TH_L=512) and
   never touches XMSTA. No workarounds, no quirk comments.
4. **Mainline direction is retreat, not workaround**: Will Whang's `upstream_dev_stripdown`
   branch (@ cecfe17, fetched) removes Clear HDR entirely — only WDMODE=0x00 remains — and the
   v3 mainline submission dropped Clear HDR + HCG/LCG after review (snippet-corroborated). The
   sibling story matches: mainline imx678 is SDR-only, Rockchip is DOL-only, OpenIPC defers
   Clear HDR explicitly, VC MIPI hides init in closed MCU firmware.
5. **Nothing found**: no `soho-enterprise` fork exists (full fork list: Kurokesu, BaconWaffle,
   Cine-Fox, con-maykr, daleghent, darkdragonsastro, Interferometry, NathanHowell,
   Tiramisioux, VoeGalore); Leopard Imaging / e-con / THine Clear HDR driver source is not
   public; GitHub-wide code searches for `COMBI_EN`, `"0x36d0" imx585`, `imx585_cmos` return
   nothing beyond the repos above (queries preserved in session record).

`[inference]` — the real divergences available to test are exactly two: (a) XMSTA-vs-standby
ordering and gap at engage (three distinct arrangements ship: ours, FRAMOS's, youjunl's), and
(b) EXP_TH policy at engage (0x0FFF/0 vs 0x0FFF/512 vs untouched 0x1000/0x1000 vs prohibited
{512,1024}). Both are cheap A/B experiments on our rig. And INNO-MAKER's documented recovery
("if the image goes black, suspect the shutter is too large first — reduce --shutter … to
recover") shows the vendor ecosystem's only public cure for black Clear HDR frames is an
integration-time cut — the same lever as our deterministic release, packaged as user advice.

### Q5 — Silicon-level plausibility (patents, ISSCC/IISW papers)

*(complete — researched 2026-08-30/31. **Severe access caveat**: every patent database
(Google Patents, Espacenet, USPTO full-text, Justia, FPO, Lens), every publisher (IEEE,
arXiv, PMC, MDPI), Sony's site, and Image Sensors World were egress-blocked. **Every patent
number and paper detail below is search-snippet evidence only — numbers/titles surfaced in
search results, never confirmed by fetching the patent itself.** Treat each as a pointer to
re-verify from an unproxied machine, not as an established citation. The [doc] lane is
GitHub-only material.)*

#### [doc]

1. The driver-anchored facts underpinning this section's reasoning are recorded in Q1 items
   1–7 (three configuration routes into an all-pixels-at-BLC combiner state; OB rows latching
   at HG saturation in Clear HDR; the EXP_GAIN sum window; DIGITAL_CLAMP written 0 at every
   stream start in both SDR and HDR).
2. **The silicon has an OB-referenced digital-clamp block with a row pointer that tracks
   binning.** Kurokesu/imx585-jetson-driver `imx585_mode_tbls.h`: `IMX585_REG_DIGITAL_CLAMP
   0x3458` ("/* Disable digital clamp */", 0x00 in normal modes) and `IMX585_REG_DIG_CLP_VSTART
   0x30D5` = 4 (all-pixel) / 2 (binned) — an OB-row start pointer for an on-chip digital clamp.
   (Our driver also writes 0x30D5 per-mode and DIGITAL_CLAMP=0 each start.)
3. **Register-family identity across Starvis 2** (mainline imx678.c fragment; also Q2 item 6)
   — silicon-level findings on siblings transfer to the IMX585.

#### [anecdote] — snippet-only secondary sources (none fetched; all labelled)

- **Sony official** (sony-semicon feature 2022012801 + security tech page): Clear HDR
  *"records images simultaneously with differences only in gain… then synthesized"*; 88 dB
  single exposure. No internals published.
- **Ximea / FastCompression Pregius-S dual-ADC pages**: two 12-bit readouts at different gains
  merged to 16-bit; gradation compression is a PWL knee curve whose *"knee points come from
  Low gain and High gain values"*; in built-in combination mode *"low gain lines and high gain
  lines are combined and output, with the number of output lines halved."*
- **LUCID IMX490 tech brief**: four gain/sub-pixel channels *"combined on-sensor into a single
  linear 24-bit HDR value"*; *"incorrectly setting the HDR Exposure Time and Gain of each
  channel can cause HDR artifacts… and HDR output which does not use the full 24-bit output
  range"* — an OEM documenting Sony on-chip synthesis degenerating under bad channel
  gain/exposure relationships.
- **ToupTek ATR585 (IMX585) HDR mode** (Cloudy Nights topic 900797 era): camera firmware in
  HDR mode *"ignore[s] user-set offset values… defaulting to a fixed offset of 512… to ensure
  consistent merging of these two gain channels"* — an integrator pinning the black-level
  relationship the merge depends on.
- **Patents (numbers from snippets only — NOT verified by fetch):**
  - *US9445019* "Solid-state image sensor and image pickup apparatus" (Sony-attributed by the
    search summary): combine rule — high-sensitivity signal used below a first threshold,
    low-sensitivity above a second — the EXP_TH_H/EXP_TH_L architecture in patent form.
  - *US9402039B2* (OmniVision) per-pixel digital HG/LG selection; *US9386240B1*
    "Compensation for dual conversion gain HDR sensor": ADC *"sequentially receive[s] a first
    reset signal, a second reset signal, a high gain image signal, and a low gain image
    signal, in that order"* — DCG readout depends on reference samples taken at defined times.
  - *US20140152844A1* "Black level calibration methods for image sensors": OB data *"can be
    corrupted if light at high intensity impinges upon active pixels near the optically black
    pixels… due to leakage and/or cross talk"*; related text: an iterative process *"enables
    the black clamping feedback loop to accurately converge… and prevents transients from
    corrupting the black reference level."*
  - *US7551212* "Image pickup apparatus for clamping optical black level to a predetermined
    level": *"preventing blacking of an image occurring due to blooming and capable of
    restoring an image to a normal image at a high speed… detecting abnormalities in the
    optical black level and clamping to a first target value (during normal times)… or a
    second target value (during abnormal times)."* Whole-image blackout via a corrupted OB
    clamp, plus explicit abnormality-detection/recovery logic, is patented prior art.
  - *US8648946*: black-level regulator with *"a frame integration average holding unit…
    updating when image pickup conditions change"* — held clamp state refreshed on condition
    changes.
  - **"Black sun" family** (incl. KR20060087130A): oversaturation corrupts the reset/reference
    sample so saturated pixels read as *black*; sensors ship dedicated clamp countermeasures.
  - *US12323716* "…improving image quality in a dual conversion gain image sensor" (USPTO
    snippet; assignee unresolved through the blocks).
- **Papers**: IEDM 2021 Sony 2.9 µm security pixel, *"97 dB single exposure"* (paper 30-3,
  authorship per an Image Sensors World summary snippet — low confidence); Image Sensors World
  2021-06 "Sony Presents 2.9um Pixel with 88dB DR in a Single Exposure" (IISW 2021 — exists,
  unfetchable); Sensors 18(1):203 (2018) triple-gain 90 dB single-exposure sensor (open
  access, unfetchable here). **ISSCC: nothing found** for a Starvis-2 combine paper (queries
  in session record).

#### [inference] — mechanism synthesis (the best literature-anchored story for all five arms)

1. **The combiner has a native "all-reject → BLC pedestal" output state** — documented three
   separate register routes into it (Q1). Our clamp is byte-identical-register, so it is this
   same *output state* entered via internal state rather than configuration.
2. **The combine stage carries per-stream-start internal reference state.** The silicon has an
   OB-referenced digital clamp block ([doc] 2); the merge demands a pinned HG/LG offset
   relationship (ToupTek's forced offset-512; LUCID's degenerate-output warning; the AppNote's
   EXP_GAIN sum window); DCG readout is reference-sample-ordered (US9386240 snippet). Clamp
   integrators / held averages are canonical *unmapped* state — matching register invisibility.
3. **A uniformly bright field at engage corrupts that reference.** Prior art recognizes
   intense light corrupting OB references via leakage/blooming (US20140152844A1), whole-image
   blackout from a corrupted OB clamp (US7551212), and saturated reset references reading as
   black (black-sun family). In Clear HDR specifically the OB region itself misbehaves (OB
   rows latch at HG saturation — Q1 item 7). An OB/reference-sampled initialization performed
   in the first Clear HDR frames under flood plausibly latches a saturated offset/ratio
   estimate; selection then rejects everything → pedestal. A dark engage samples a sane
   reference → dark-start immunity.
4. **Release semantics match "held state, updated on abnormality or condition change."**
   US7551212-shaped logic re-clamps when an OB *abnormality* is detected — a one-sided,
   level-drop-watching detector explains downswing-only stochastic release (the ~2 s dark
   transient must overlap a sampling window) and never-release-on-increase (a reference
   latched at the rail cannot be exceeded upward). US8648946-shaped logic re-initializes the
   held average when *"image pickup conditions change"* — a commanded large SHR step is
   exactly such a change (and SHR is the one parameter the AppNote binds specially in Clear
   HDR: doubled minimum, reduced maximum; INNO-MAKER's black-frame cure is a shutter
   *reduction*) → the deterministic ~0.6 s release. Plain gain/exposure sweeps inside the
   valid window never cross the re-init trigger's hysteresis.
5. **SDR immunity follows for free**: WDMODE=0 → COMBI_EN=0 → the combine/clamp machinery
   never arms.

**Confidence**: the *class* (per-stream-start offset/reference initialization in the HG/LG
combine stage, saturable by a bright field, re-armed only by a level-drop detector or an
exposure-condition change) — moderate, ~70%: every component is separately documented, but no
single source describes the assembled mechanism, and Sony's Clear HDR internals are NDA'd.
The alternative — the trigger living in the *gradation-compression knee estimator* (knee
points "come from Low gain and High gain values" per the Pregius-S snippet) — is disfavored:
the rig clamps identically in 16-bit linear with CCMP disabled.

### Q6 — Adjacent errata (other Sony HDR families)

*(complete — researched 2026-08-30/31. Egress caveat: every machine-vision vendor domain
(FLIR/Teledyne, Basler, Lucid, Allied Vision, IDS, XIMEA…), astro vendor sites, NVIDIA
forums, and lore.kernel.org were blocked — the machine-vision release-note goldmine could
NOT be assayed, so absence there is unproven, not established. Kernel/driver quotes below
were fetched from raw sources; the top item was independently re-fetched and quote-verified
by the overseer.)*

**Ranked result: the closest documented relative anywhere is Sony's own on-chip-combine
sensor on our own platform — the IMX708, whose vendor helper silently discards the first
startup frame in HDR mode only. No black-image latch erratum was found in any Sony family.**

#### [doc]

1. **IMX708 (Pi Camera Module 3, on-sensor QBC-HDR merge): the first startup frame in HDR
   mode specifically is bad, and Raspberry Pi's helper discards it.**
   raspberrypi/libcamera `src/ipa/rpi/cam_helper/cam_helper_imx708.cpp` (fetched;
   overseer-re-verified): *"We need to drop the first startup frame in HDR mode. Unfortunately
   the only way to currently determine if the sensor is in the HDR mode is to match with the
   resolution and framerate."* `hideFramesStartup()`/`hideFramesModeSwitch()` return 1 only in
   the HDR mode, 0 otherwise. **Start-condition-specific, HDR-combine-specific, absent in
   SDR — exactly our envelope, except the IMX708's bad state self-clears after one frame
   instead of latching.** Not stated to be light-dependent.
2. **IMX708 kernel driver: on-chip HDR cannot be toggled while streaming** —
   raspberrypi/linux `drivers/media/i2c/imx708.c` (fetched): the wide-dynamic-range control
   carries `V4L2_CTRL_FLAG_MODIFY_LAYOUT` and is grabbed during streaming. The combine
   engages only at stream start on Sony on-chip-combine parts — consistent with an
   engage-time-armed state.
3. **IMX290 family: stream-start frames are suspect even in linear mode** — raspberrypi/
   libcamera `cam_helper_imx290.cpp` (fetched): *"On startup, we seem to get 1 bad frame."* /
   *"After a mode switch, we seem to get 1 bad frame."* And mainline `imx290.c` (fetched):
   *"vflip and hflip should not be changed during streaming as the sensor will produce an
   invalid frame"* — mainline ships **no DOL support at all** for the DOL patriarch.
4. **Rockchip BSP IMX415 (DOL): hidden mode-polarity registers and fragile HDR arithmetic** —
   `rockchip-linux/kernel drivers/media/i2c/imx415.c` (fetched): *"0x3260 should be set 0x01
   in normal mode, should be 0x00 in hdr mode"*; *"IMX415 HDR mode T-line is half of Linear
   mode, make vts double to workaround"*; RHS1 alignment rules (*"rhs1 should be 4n+1 when set
   hdr ae"*). No black-latch, but undocumented mode-dependent registers where wrong values
   break output.
5. **OpenIPC "waybeam" IMX662 (Starvis 2 sibling): Clear HDR deferred; blend documented as
   corruptible by write ordering** — `imx662_cmos.c` (code-search fragments + README fetched):
   *"FDG_SEL1 (3031h) … has no slot here, so stamping 0/1 every frame would silently corrupt
   an HDR blend"*; README: linear only, *"HDR stays deferred."* An active bring-up treats the
   HG/LG blend as fragile against register sequencing and shipped without it.

#### [anecdote] (ranked by closeness)

1. **ZWO ASI294 / IMX294 (DCG): dual-gain crossover pathology under bright uniform light**
   (snippets only — AstroBin topic 56402, Cloudy Nights flats threads): at gains ~120–140
   around the HCG/LCG switch, flat frames plateau below saturation — *"If increasing exposure
   no longer affects the histogram and pixels remain unsaturated, you have the problem"*;
   community workaround: avoid the crossover band. **A Sony dual-conversion-gain selector
   misbehaving specifically under bright uniform fields** — the same stimulus that arms our
   latch — though the failure is a clipping plateau, not black, and not latched.
2. **Jetson + IMX662 Clear HDR wrong at bring-up, fixed by a platform "fusion logic" update**
   (snippets — NVIDIA forum t/264319 & mirrors): unmerged/bright/noisy output; *"the fusion
   logic error … was fixed in the r35.4.1 release."* Combine-enable failure, but SoC-side and
   not black. (Also in Q2.)
3. **OpenIPC firmware #573 — HI3516EV300 + IMX335: camera started in the DARK fails to start;
   started in light runs fine; once running, light changes don't hurt** (fetched:
   github.com/OpenIPC/firmware/issues/573, 2022-11, open). **The exact logical shape of ours
   with opposite polarity** — start-condition-dependent, scene-luminance-dependent, hysteretic
   — but almost certainly an AE/ISP pipeline failure, and only a restart releases it.
4. **Jetson + IMX678 DOL threads** (snippets): fused image correct until an object moves
   dark→bright, then *"the 'overexposed' area appears pink"*; short frames not fused on
   r36.2. Light-transition-dependent combine misbehaviour, ISP-side.
5. **QHY294C: the first frame after an exposure-time change is discarded by design**
   (snippet — SharpCap forum t=3532): *"camera will give up the first frame that you changed
   expose time."* On IMX294 platforms an exposure-time change is the canonical internal-state
   flush event — echoing that our latch releases on a commanded integration-time cut.
6. **Arducam IMX477** (snippet): the *"image abnormality in the first frame"* can be *"resolved
   with a firmware upgrade"* — precedent for Sony sensor-side first-frame defects fixed in
   sensor microcode; non-HDR part.

**Explicit nothing-found:** machine-vision release notes (FLIR/Basler/Lucid/Allied Vision/
IDS/Daheng/Hikrobot/XIMEA) — candidate documents located but domains blocked; only recovered
Dual-ADC constraint: *"Dual ADC Mode is not available when ADC Bit Depth is set to 8-bit or
10-bit"* (snippet). Sony technical notices/errata: nothing (only adjacent datum: industrial
IMX900 *"does not include an HDR compositing function"*, snippet). Broadcast/cinema dual-gain
(IMX410/455/571): nothing shaped like ours — their HCG/LCG is a global mode select, not an
on-chip per-pixel combine, so the suspect circuit isn't exercised. One unfetchable lead
flagged for an unproxied machine: "Sony IMX290/462 image sensors I2C xfer peculiarity"
(lkml.iu.edu, 2023-10).

#### [inference]

1. Across every ecosystem where a Sony on-chip combine ships (IMX708 QBC-HDR, IMX662/678
   Clear HDR), the combine is (a) only engageable with the stream stopped and (b) known to
   produce at least one invalid frame at HDR stream start. **Our latch looks like the
   pathological limit of the IMX708 behaviour: the settling that normally completes in one
   frame never completes when the first integrations are uniformly lit**, and nothing re-arms
   the HG/LG selector until a large downward exposure/illumination step drives it back through
   its threshold.
2. The IMX294 crossover plateau and waybeam's "silently corrupt an HDR blend" warning both
   point at the HG/LG selection logic — not the exposure engine — as the family's fragile
   element, and the IMX294 case specifically implicates bright uniform fields.
3. No source anywhere describes a register-invisible latched state; that facet appears
   publicly novel. Machine-vision silence is weak evidence: Pregius-S dual-ADC combine is
   typically configurable only with acquisition stopped, so the failure may be unreachable in
   those products.

---

## 3. Hardware-testable predictions

*(raw accumulating list, one block per completed question; deduplicated and renumbered in a
final pass after Q6.)*

From Q1:
- If commit be3cb94 is right that the EXP_BK weighted-blend path clamps near BLC, then writing
  EXP_TH_H=EXP_TH_L=0x1000 into a healthy lit stream should collapse active pixels to
  near-pedestal within a frame or two — a second, register-visible route into the same
  combiner-fallback state our clamp enters invisibly.
- If AppNote §2 p.6's "returns BLC if asked" fallback is the same state as our clamp, then
  while clamped, sweeping EXP_BK 0h–7h and ACMP1/2 across their valid ranges should produce
  zero output change (combiner bypassed to pedestal, not mis-blending), whereas the same sweep
  on a healthy stream visibly changes tone mapping.
- If INNO-MAKER's "fully black when --shutter exceeds ~4484 lines" limit shares our clamp's
  mechanism, then commanding exposure above 4484 lines on a healthy lit stream should
  reproduce exact-pedestal output that a subsequent short-SHR command releases in ~0.6 s —
  the same release signature would tie both black-frame conditions to one internal state
  machine.

From Q3:
- If Kurokesu's warning describes our latch rather than static threshold mistuning, then a
  half-covered scene at lit stream start → the lit region clamps to pedestal while the covered
  region does not, reproducing "bright parts render black" spatially within one frame (this is
  also the campaign's open structured-scene question, sharpened).
- If the AppNote §4.2 "blend-off" state is architecturally distinct (EXP_TH_H=EXP_TH_L=0x1000
  routes through the EXP_BK weighted blend), then pre-setting both thresholds to 0x1000 before
  a lit stream start → no clamp; a clamp there would prove the latch sits below the
  selection/blend fork and is a new, reportable finding.
- If ToupTek's FPGA firmware fixes addressed HDR re-initialization rather than tuning, then
  toggling COMBI_EN (0x3024) 0x02→0x00→0x02 mid-stream on a lit clamped stream → releases or
  re-arms the clamp, mirroring what a firmware-side combine reinit would do.

From Q2:
- If FRAMOS's fr_imx585 16-bit table is valid silicon usage (WDMODE=0x10 + COMBI_EN=0x00 +
  MDBIT=0x03), then starting a lit 16-bit stream with COMBI_EN=0x00 → either no clamp (the
  clamp lives in the built-in combination gated by COMBI_EN) or clamp persists (it lives in
  the WDMODE=0x10 data-selection stage upstream of combination). Either outcome localizes the
  latch by one register.
- If the sibling WDMODE map transfers (0x08 = Clear HDR dual-stream uncombined per FRAMOS NXP
  imx662/678 tables), then a lit engage with WDMODE=0x08 → non-pedestal HG/LG data (likely two
  virtual channels / doubled rows, needing CFE DT tolerance), proving readout and both gain
  chains are healthy while only the combiner latches.
- If Kurokesu's "bright parts of a scene can render black" is the per-pixel form of the same
  mechanism, then a lit engage on a half-flooded/half-dark scene → only the lit half sits at
  exactly the pedestal while the dark half shows normal read noise (per-pixel data-selection
  verdict), whereas a fully global latch predicts the dark half clamps too.

From Q4:
- If FRAMOS's engage arrangement (0x3000=0 → 40 ms → XMSTA=0) matters, then swapping our
  driver to standby-release-first with a ≥40 ms gap before XMSTA → lit starts come up with
  signal; if they still clamp, the XMSTA/standby ordering is exonerated.
- If youjunl's nonzero low threshold avoids the clamp, then writing EXP_TH_L=512 instead of 0
  before standby release → lit starts produce non-pedestal output from frame 1.
- If INNO-MAKER's shutter rule generalizes to a fix template, then baking an "integration
  kick" into enable_streams — program SHR to the Clear HDR minimum (16 lines) for the first
  frame after master start, restore the requested exposure a frame later — → lit starts
  recover within ~2 frames instead of never, matching the ~0.6 s commanded-release timing.

From Q5:
- If the corrupted-reference-at-engage story is right, then engaging Clear HDR under the same
  flood but with SHR pre-set near its Clear HDR maximum (shortest legal integration, so the
  field reads far below the selection thresholds) → clean engages, versus consistent clamps at
  long integration under identical lux — the trigger is signal level at engage, not
  illumination per se.
- If US8648946-style "update on imaging-condition change" applies beyond SHR, then while
  clamped, a large commanded EXP_GAIN step (hdr_gain_adder 2→5 and back) or a rewrite of
  EXP_TH_H with its current value → release with SHR untouched; if only the SHR path releases,
  the re-init hook is exposure-specific.
- If the reference is sampled from the pixel array/OB at stream start only (test patterns
  "bypass the pixel array entirely so the blend logic is never exercised" — commit 954a52a),
  then starting the Clear HDR stream with TPG enabled under flood and disabling TPG ~5 s in →
  the stream comes up clean and stays clean (arming window missed), while the same sequence
  without TPG clamps — proving the corruptible initialization is confined to the first frames.

From Q6:
- If the IMX708 "first HDR startup frame is bad" mechanism is the benign form of our latch,
  then starting the Clear HDR stream with integration pre-programmed to its minimum for the
  first few frames, then lengthening it → no black lock even under uniform bright light — the
  release stimulus (large integration cut) baked into the start sequence. (Converges with
  Q4's integration-kick prediction.)
- If the IMX294 crossover pathology shares the HG/LG selector lineage, then a stream started
  against a high-contrast half-dark/half-bright target → never latches at any brightness,
  while a uniform gray card latches across a wide brightness range — uniformity, not absolute
  level, is the arming condition. (Converges with Q2/Q3's structured-scene predictions.)
- If the Jetson IMX662 analogy (platform-side fusion) were right, defect pixels would blacken
  with everything else; since hot pixels ride through on our rig, a raw-CSI2 tap during a
  clamp should show pedestal-exact black already in the sensor's own output — re-confirming
  sensor locus against any lingering ISP suspicion.

---

## 4. Candidate remediations used elsewhere

*(pending)*

---

## 5. Most promising single follow-up lead

*(pending)*
