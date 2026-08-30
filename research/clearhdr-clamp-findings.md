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

*(pending)*

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

*(pending — accumulated from Q1–Q6, deduplicated and numbered at the end.)*

---

## 4. Candidate remediations used elsewhere

*(pending)*

---

## 5. Most promising single follow-up lead

*(pending)*
