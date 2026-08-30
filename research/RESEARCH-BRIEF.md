# Cloud research thread — IMX585 Clear HDR light-at-startup clamp

Paste this whole file as the first message of a Claude Code cloud session running on the
repository **Tiramisioux/cinemate-handbook**.

## Setup (do this before any research)

1. Create branch `research/clearhdr-clamp` off the default branch — or, if it already
   exists, switch to it and READ what is already there first: a previous session may have
   partial findings; continue, don't restart.
2. Context (optional but recommended): read `lessons/hardware-log.md` — the entries dated
   2026-08-30 and 2026-08-31 at the end are the campaign evidence — and
   `lessons/clearhdr-instability-report.md`. The fingerprint below is self-sufficient if
   those files are unavailable.
3. Your deliverable is the in-repo file `research/clearhdr-clamp-findings.md`.
4. **Incremental persistence is a hard requirement:** commit AND push after completing
   EACH research question's section (≥6 commits), and again whenever you revise the
   predictions or remediations sections. If this session dies or runs out of tokens, the
   pushed branch must already contain everything found so far. Never hold findings only in
   the conversation. Commit messages: `research: Q<n> <lane> — <one-line result>`.
5. Do not touch any file outside `research/` on this branch.

## Research task

Find external documentation, community reports, driver implementations, errata, patents,
or papers that explain or corroborate a sensor-internal failure mode we have characterized
on hardware in the Sony IMX585 (Starvis 2) when its single-exposure dual-gain "Clear HDR"
mode is started while the sensor is exposed to light. Web search + datasheet/appnote
hunting. The measurements below are hardware-confirmed — your job is external evidence,
not re-derivation.

## The phenomenon (hardware-confirmed fingerprint — use these details to craft searches)

Setup: Sony IMX585 (mono variant; colour also affected historically), V4L2 driver on
Raspberry Pi CM5 (will127534/Tiramisioux imx585-v4l2-driver lineage), 4K mode, Clear HDR
enabled (WDMODE 0x301A = 0x10, COMBI_EN 0x3024 = 0x02), 12-bit gradation-compressed and
16-bit linear outputs.

- If the sensor STARTS STREAMING in Clear HDR while seeing roughly uniform light — from
  full lens-less flood down to light through a sheet of printer paper — every active pixel
  outputs EXACTLY the black-level pedestal (BLKLEVEL register 50 → 200 in 12-bit, 3200 in
  a 16-bit container; active-area σ as low as 0.0). Reproduced 8/8.
- Hot and dead defect pixels ride through unaffected (hot still 65535, dead still 0) — the
  readout chain is alive; the clamp sits in the HG/LG combine / data-selection stage.
- Starting the stream in DARKNESS avoids it completely (2/2): the sensor images normally,
  and light applied afterwards is imaged correctly.
- The clamped state is exposure-independent (analogue gain sweeps do nothing) and
  register-invisible: every readable register — WDMODE, COMBI_EN, EXP_TH_H 0x36D0 /
  EXP_TH_L 0x36D4, EXP_BK, EXP_GAIN 0x3081, ACMP1/2, CCMP1/2_EXP, ADDMODE, DIGITAL_CLAMP,
  BLKLEVEL, HMAX, VMAX, SHR — is byte-identical between clamped and healthy states,
  verified over raw I2C during both AND across a live, frame-resolved release.
- Release, while streaming, is one-way per stream and possible two ways: (a) covering the
  sensor — a large DOWNWARD light transient — releases after ~2 s of dark, stochastically
  (2/3 attempts); (b) commanding a very short integration (shutter ~1°, i.e. a large SHR
  step) releases reliably within ~0.6 s, during the short-integration hold. INCREASING
  light does not release it (held ≥13 min under a diffuse→flood step).
- SDR (WDMODE=0) on the same power-up is completely unaffected.
- The state does not survive stream restarts as such — it is RE-ENTERED at every restart
  under light (an engage-time condition, not a persistent latch).
- The AppNote marks EXP_TH_H < EXP_TH_L as prohibited ("outputs only the pedestal") — but
  our clamp occurs with a VALID pair (0x0FFF / 0x0000) and correct registers throughout.

## Already eliminated (do not spend effort here)

Raspberry Pi capture-path/CSI/ISP bugs (defect pixels survive, SDR fine, byte-level DNG
forensics done); userspace/driver register writes (persistent journal + I2C readback prove
none); sensor power-cycling up to ~140 s (re-enters at the next lit engage); software
decompand paths (16-bit linear runs with compand disabled and clamps identically).

## Ranked research questions (one committed section each)

1. **Sony primary documentation.** IMX585 datasheet / application notes / reference
   register settings: startup-condition requirements for Clear HDR, combine-stage or
   data-selection initialization notes, required write ORDER for WDMODE / COMBI_EN /
   EXP_TH / EXP_BK, settle-time requirements, or errata mentioning black/pedestal output
   or combine lock-up. Search phrases: "Clear HDR", "ClearHDR", "gradation compression",
   "EXP_TH", "COMBI_EN", "WDMODE", "data selection", with imx585.
2. **Same-architecture siblings.** IMX678, IMX675, IMX664, IMX662, IMX485 (Starvis 2,
   shared Clear HDR architecture): their datasheets/appnotes/integration guides sometimes
   document the combine stage in more detail. Startup caveats or black-screen errata?
3. **Community corroboration.** These sensors ship in astro cameras (ZWO ASI585MC/MM,
   Player One Uranus-C, QHY, Touptek), security/machine-vision cameras, and Pi HATs
   (INNO-MAKER, Soho Enterprise, Will Whang's OneInchEye). Search Cloudy Nights,
   Stargazers Lounge, vendor firmware changelogs, GitHub issues on
   will127534/imx585-v4l2-driver and forks, libcamera-devel, Raspberry Pi forums:
   "black frames in HDR mode", "HDR no image until light change / exposure change",
   "sensor starts black", changelog lines like "fixed HDR startup". Astro users start
   cameras in daylight and switch modes constantly — if this bites in the field, they
   wrote about it.
4. **Driver-implementation comparison.** How do OTHER IMX585/IMX678-family drivers
   (vendor SDKs, Jetson/NVIDIA drivers and device trees, FRAMOS, Soho, e-con, The Imaging
   Source, UVC bridge firmwares) sequence Clear HDR enable relative to stream start?
   Anything that looks like a deliberate workaround: thresholds written before WDMODE, a
   dummy short-exposure frame, a forced integration kick, a delay, a double stream-start?
   A driver that provably avoids the condition is a fix template.
5. **Silicon-level plausibility.** Sony patents and ISSCC/IISW papers on
   dual-conversion-gain single-exposure HDR with on-chip combine/data-selection (terms:
   "dual conversion gain" + "data selection", "high gain low gain combine", "subframe
   HDR", Sony "Clear HDR" patent). Is there a described auto-zero / reference sampling /
   per-frame calibration at stream start that a uniformly bright field could corrupt —
   and that only a large signal DOWNSWING or integration-time step re-triggers? That
   would explain every arm of the fingerprint.
6. **Adjacent errata.** Documented "black image lock" / "combine latch" errata in other
   Sony HDR families (DOL or DCG), even older — same circuit lineage counts.

## Deliverable — `research/clearhdr-clamp-findings.md`, exactly these sections

1. **Headline** — a matching known erratum or documented startup requirement we violate,
   if found; otherwise say plainly no smoking gun exists.
2. **Findings per research question (1–6)** — ranked by relevance, three lanes strictly
   separated and labelled: `[doc]` documented fact (quote the exact passage, cite with
   URL), `[anecdote]` community report (URL, date, hardware, how closely the fingerprint
   matches ours), `[inference]` your reasoning. For an empty question: an explicit
   "nothing found — here is where I looked" with the actual queries/sources tried.
3. **Hardware-testable predictions** — numbered, each one sentence: "if <source> is
   right, then on our rig <specific test> → <specific outcome>". Only tests runnable on a
   Raspberry Pi CM5 + IMX585 with I2C access, frame capture, register readback, and
   journals. These convert directly into campaign rounds — the primary deliverable.
4. **Candidate remediations used elsewhere** — with sources, and for each: what it would
   look like in a V4L2 driver or userspace sequencing change on our stack.
5. **Most promising single follow-up lead** — one paragraph, and why.

Finish by pushing the final commit and posting a short chat summary of sections 1, 3
and 5. The campaign overseer will fetch the branch and ingest the file.
