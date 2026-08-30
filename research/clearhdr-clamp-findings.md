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

*(pending)*

### Q3 — Community corroboration (forums, GitHub issues, firmware changelogs)

*(pending)*

### Q4 — Driver-implementation comparison (Clear HDR enable sequencing)

*(in progress — external-driver comparison pending; our-stack baseline recorded below.)*

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

### Q5 — Silicon-level plausibility (patents, ISSCC/IISW papers)

*(pending)*

### Q6 — Adjacent errata (other Sony HDR families)

*(pending)*

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

---

## 4. Candidate remediations used elsewhere

*(pending)*

---

## 5. Most promising single follow-up lead

*(pending)*
