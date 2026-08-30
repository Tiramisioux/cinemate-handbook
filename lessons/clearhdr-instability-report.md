# Why is ClearHDR unstable? — a desk archaeology of 2026-08-10 → 2026-08-30

**Status: FINAL.** Desk-only investigation: 21 evidence agents over the five repos + GitHub, followed by 5 adversarial refuters attacking the load-bearing conclusions (all five returned *holds-with-corrections*; every correction is folded in below, including two that overturned this report's own draft claims). Every code claim was read from source at a named SHA; every record claim cites a hardware-log section. Markers: **[confirmed]** = read directly, **[probable]** = inferred with stated basis, **[unknown]** = not determinable from the desk. (Raw per-agent evidence lived in the desk session's scratchpad and is not preserved; every load-bearing claim carries its file:line/SHA or hardware-log citation inline below.)

---

## 0. The shape of the answer

1. **No layer of the stack contains a mechanism that varies boot-to-boot while staying consistent within a boot — except state the stack deliberately persists (Redis) and state the sensor itself holds.** The driver reprograms everything from scratch at every stream start on both branches; libcamera persists nothing; cinepi-raw's sensor writes all funnel through the V4L2 control cache and are re-asserted deterministically at each stream start. **[confirmed]**
2. **Within a boot, recording takes are stream-invisible.** The whole `rec` path is Redis-only — it never stops or starts the camera — so round 8's "5 fills in a row" involved **zero** sensor re-programmings and **zero** power cycles between takes; the ClearHDR engage happens once or a handful of times per boot, clustered at startup (launch, the Plymouth-handoff relaunch on real boots, plus any self-heal bounces). **Much of the "within-boot consistency" is therefore structural: takes share one engage.** **[confirmed]**
3. During confirmed failing takes, every register userspace can influence read correct — and post-#170 the threshold keys seed empty, so the failing boots demonstrably ran the driver's own default pair. Register-visible *configuration* is exonerated as a resident cause. **[confirmed]**
4. What is *not* exonerated: the sensor's **ClearHDR data-selection/combine stage itself**. It demonstrably has register-*valid* configurations that output pure BLC pedestal (measured on this hardware family), it demonstrably behaves **condition-dependently** (the "Prohibited" pair produced pedestal in one bench measurement and real data twice in the rig's own record), and the observed defect is exactly that stage producing pedestal with correct registers — i.e. internal state. **[confirmed for the stage's existence and condition-dependence; probable for it being the defect's locus]**
5. The record's eliminations needed an audit of their own: the "automated shutter kick failed" elimination is **contradicted — the automated kick never ran at all** (dev carries the gain shock; the kick commit never merged; the branch's own later commits say so); the "mid-scale thresholds don't clear it" elimination **stands** (the test deliberately wrote name-reversed values that landed as a valid pair, verified over I2C — correcting this report's own draft); the 24 dB gain datum stands but its provenance is unrecorded. **[confirmed]**
6. The 2026-08-10 golden anchor is weaker than believed: ~1 boot, colour only — and the golden-era driver's own replayed threshold default was `{512,1024}`, the *Prohibited* pair by its own documentation. Colour has never been tested for intermittency at all. **[confirmed]**

---

## 1. Q1 — Configuration pinning

### Known-good #1: 2026-08-10 colour golden verification

Prescribed in `PI-TEST-HANDOFF.md` @ cinemate `docs/ccmp12-workspace` c195b5e (committed 2026-08-10 21:13 +0200); targets b=1 WhiteLevel 63265, b=4 62704, byte-identical. **[confirmed]**

| Layer | State | Evidence | Confidence |
|---|---|---|---|
| cinepi-raw | `feature/log-encode` @ **37fb3b2** (21:39 that evening; earlier trees could not compile SensorBinning) | 37fb3b2 commit message; next commit 08-11 | probable (near-certain) |
| cinemate | `feature/log-encode` @ **cede78bf** — SHA unresolvable locally (branch deleted). No ClearHDR knob/seeding code existed in cinemate yet (first `hdr_threshold` commit 07d3186, 08-13) | handoff survey; `git cat-file` fails | probable |
| imx585 driver | **6.12.y @ 479117e** ("valid CCMP gradation-compression ratios", 07-21). cb7c7a6 did not exist until 08-26 | `CCMP12-ANALYSIS-HANDOFF.md:126`: "Driver 479117e is built, loaded and governing" | **confirmed** |
| libcamera | `cinemate`, tip then **bcdd7e1** (07-14); on-Pi build state not surveyed | rev-list dating | probable |
| kernel | **6.12.93+rpt-rpi-2712**, stock rp1-cfe (colour Bayer16 already csi_dt=0) | handoff survey table | **confirmed** |
| overlay/link/clock | colour overlay, 1440 Mbps default (dts@479117e:77-78), stock clock; config.txt not preserved | dts; overclock work starts 08-21 | probable |
| **EXP_TH on the sensor** | driver default `hdr_thresh_def = {512, 1024}` → **EXP_TH_H=512 < EXP_TH_L=1024 = the documented Prohibited pair**, replayed at every stream start; cinemate seeded nothing; stray Redis keys unknown | `git show 479117e:imx585.c:955,900-902` | **confirmed** (default) / unknown (live values) |

**Boots: not documented anywhere. Plausibly 1.** (Plus the 08-06 chart sessions the LUT rests on, ~8 colour ClearHDR launches, boots uncounted.) Colour total: ~10+ ClearHDR starts, zero fills, on likely 2–3 boots. **[confirmed as record-absence]**

### Known-good #2: 2026-08-27 night milestone + 08-27/28 rate matrix

Tag `milestone-mono-clearhdr-2026-08-27`: cinemate `fix/mono-clearhdr-stack` @ **02b2bec8**, cinepi-raw @ **1f3383d**, driver **innomaker-v1.0 @ 70bdb26**, libcamera **3c7b9ab**, kernel 6.12.93 + **local rp1-cfe Y16 csi_dt=0 patch** (first compile and first load that night), `dtoverlay=imx585,cam0,mono,ccmp`, 1440 Mbps, stock clock, `--max-pixel-rate 380.0`. **[confirmed]**

**Boots: milestone = 1 documented boot. Rate matrix = ≥6 structurally implied (six config.txt cells), explicit count absent.** All within ~30 h on the identical stack that latched on 08-29/30.

**The milestone threshold caveat, adversarially resolved as far as the desk allows [R4]:** cinemate @ 02b2bec8 unconditionally seeded Redis `hdr_threshold_low/high = 0/0` at every start (`02b2bec8:src/main.py:737-741`, `settings.jsonc:196-197` **[confirmed]**); cinepi-raw's `sync()` ran before the camera opened, so the write latched into the control cache and was programmed at every ClearHDR stream-on *after* the driver's good base table (`imx585.c:1354` pm-gate; `:2024` replay **[confirmed]**). Yet the matrix byte-verified real, exposure-exact data. Silent write failure is effectively refuted (same path proven working by I2C readback). The evidence **favors an unrecorded operator threshold set** — the record's own wording ("re-issuing…", "degraded to 0/0") presupposes non-zero values earlier; the EXPERIMENT drawer with live threshold sliders merged ~6 h before the milestone; 2048/3584 are default step-array values. The alternative — that `EXP_TH_H=EXP_TH_L=0` does not flatten output (pure-LG reading) — is textually disfavored (the driver's comments tie the blend fallback to *equality*, and be3cb94 measured the equality case as pedestal at 0x1000/0x1000) but was **never measured at 0/0**. Net: the milestone's threshold state is **unknown**, and "verified working" is entangled with it. **[probable/unknown]**

### Current stack (rounds 7–8, the failing configuration)

| Layer | State | Confidence |
|---|---|---|
| cinemate | `dev` @ **e660925** (merge #175; 24 commits past milestone). Thresholds seed `""`; blend 0; **gain_adder 1 (+6 dB)**. Self-heal **live and default-on** (gain shock + mode bounce; flag gate #176 unmerged) | confirmed |
| cinepi-raw | `dev` @ **fef2c22** (merge #68; 9 past milestone). **Threshold key swap still live** (#69 open) | confirmed |
| driver | innomaker-v1.0 @ **70bdb26** (unchanged since 2026-06; source-diff-verified on the Pi in rounds 7/8) | confirmed |
| libcamera | `cinemate` @ **3c7b9ab** (unchanged since milestone) | confirmed |
| kernel/rp1-cfe | 6.12.93 + Y16 patch in place (no kernel change recorded; rounds-7/8 16-bit shows clean pedestal, not the unpatched COMP1 motif) | probable (strong) |
| regime | mono,ccmp overlay; 1440 Mbps; stock clock | probable |
| not running | #176 (self-heal flag) and #69 (threshold order fix) — both open | confirmed |

**Boots for the failing characterisation:** round 8 = 5 fills on one boot, 3 clean on the next (**2 boots**); "across several boots" for rounds 7–8 overall.

### Driver lineage delta between the anchors

Golden colour ran **6.12.y @ 479117e**; everything mono since 08-27 runs **innomaker-v1.0 @ 70bdb26** (merge-base 682e872; ~969 changed lines in imx585.c). **No colour session of any kind is recorded after 08-10** — zero colour evidence for innomaker-v1.0, and only one working-mono datapoint for 6.12.y ClearHDR (the 08-27 evening forensics found 4K 12-bit CCMP mono real on 479117e in the 19:07 take **[confirmed]**). The only reconciliation of the two lines is the never-merged, never-booted branch `fix/cinemate-modes` (360cdb4).

---

## 2. Q5 — The change audit (one row per PR)

Verdicts: **sound** = correct and could not plausibly destabilise · **unverified** = plausibly correct, no adequate hardware evidence · **suspect** = flawed reasoning or plausibly destabilising.

### cinemate

| PR | Title (short) | Verdict | Justification (short) |
|---|---|---|---|
| #157 | docs C6 correctness | **sound** | Docs-only by construction; spot-checked key claim true. |
| #158 | web-gui auto reload | **unverified** | Reasoning checks out line-by-line; browser deliverable never run on the Pi. No camera path. |
| #159 | B9/B11 fixes (eject, timecode, restart) | **unverified** | Well-evidenced diagnoses (B11.4 rests on the F-283 hardware record); its three acceptance gates never recorded as run. |
| #160 | phone usability CSS/meta | **sound** | CSS/meta only; measured in a browser harness. |
| #161 | dev-track docs | **sound** | +5965/−0, all under dev-track/. |
| #162 | release dev→main | **sound** | Byte-exact pure merge, honest body; carried the (pre-existing) 0/0 seed to main. |
| #163 | EXPERIMENT drawer | **unverified** | No new control path (all widgets → existing `/api/v1/cmd` dispatcher, gesture-gated — confirmed); shipped pending its own hardware pass, never recorded. Residual defect found: post-#170 its reset arrows can send a coerced mid-scale threshold (`events.py:73` fallback → slider null-coercion). |
| #164 | re-apply controls after mode switch | **unverified** | Real hardware-documented defect + confirmed dedup mechanism; the fix's target scenario never re-tested on hardware; cannot fire at boot (no startup caller — confirmed). The 12-frame shutter anomaly shows post-switch HDR control-apply remained broken anyway. |
| #165 | dropdown CSS | **sound** | One CSS rule. |
| #166 | rp1_regime authority + mono AWB drop | **sound** (caveats) | Both changes behavioral no-ops on the rig (veto was dead code at 333 MHz; AWB args were IPA no-ops on mono — confirmed). Caveats: body rewritten 35 min post-merge to describe unmerged "Round 2" work; the motivating "580 with overlay commented out" claim is impossible against the fixed code (probable misattribution of #167's stale-toggle bug); merged 18 min after a substantive review request. |
| #167 | config.txt toggle re-sync | **sound** | Confirmed read-only (one guarded GET). |
| #168 | dev→main sync | **unverified** | Pure merge (byte-exact), but empty body, 8-second self-merge, three direct-to-dev commits outside any PR, and froze main 2 minutes before the #170 fix existed — **main still seeds 0/0 today** while also shipping the mono-stack installer. |
| #169 | fix/mono-clearhdr-stack→main | **unverified** | Pure merge; core payload has the best hardware pedigree in the window (~7 boots) but the published union tree ran 0 boots; this is the action that makes main's unfixed 0/0 seeding the default install. |
| #170 | stop seeding 0/0 thresholds | **sound** | Confirmed against source + hardware record; removes a once-per-boot degenerate write; swap-immune because it writes nothing; rounds-7/8 I2C readback confirms its intended end state. Hygiene poor (16-s self-merge; its own 4-item Pi gate never run). |
| #171 | shutter/exposure staleness + WDR retry | **suspect** | Two of three commits sound (hardware-reproduced display-state bugs). The WDR-retry commit's causal story is refuted by the driver's own semantics: `hdr_mode` is `__v4l2_ctrl_grab`-bound for the whole streaming period and the retry runs *before* teardown begins — all five attempts deterministically EBUSY; the retry is inert except for ~200 ms added latency, and the warning it meant to silence still fires. The repo recorded the refuting fact 6 h later (65e60a8 comment) without anyone revisiting. |
| #172 | mono stack installer default (02b2bec8 etc.) | **unverified** | Mechanically correct (ccmp plumbing confirmed end-to-end; cg_rb/AWB skips sensor-inert); runtime content had ~7 pre-merge boots. But the actual deliverable — the installer path — has **zero** recorded runs; `patch-rp1-cfe.sh` clones **unpinned** rpi-6.12.y (fresh installs are not binary-reproducible against the verified module); kernel upgrades silently revert the patch. Cannot have caused the rig's failures (the rig got the same stack on 08-27, pre-merge). |
| #173 | sync-mode nominal staleness | **sound** | Every claim checks out; tests demonstrated to fail pre-fix; no boot path, no control-write moves; epistemically careful. |
| #174 | self-heal (detector + mode bounce) | **suspect** | "Reliably clears" extrapolated from *manual* anecdotes; refuted by its own author's live test within minutes (two automated bounces failed). Detector later measured to carry **zero information** on this rig (uniq=1 healthy and filling). Default-on `sensor_mode` rewrites + up to 4 extra full relaunches per start during an active investigation of a boot-latched defect. Merged 52 s after opening, zero review. |
| #175 | self-heal shutter kick (title) | **suspect** | **The PR record misdescribes the merge**: merged head 65e60a8 is the *gain shock*; the shutter-kick commit f7cedba was authored ~13.5 h **after** merge and never reached dev; the body was rewritten post-merge to describe code dev never received. Merged in 36 seconds; the merged mechanism was then live-refuted. dev @ e660925 still carries the gain shock + a false-firing stale-`hdr` gate. |
| #176 (open) | self-heal behind flag, default off + detector fix | **sound** | The only PR of the trio with measured evidence (live byte-level /stream captures; regression test failing pre-fix; detector scored against DNGs on healthy and filling streams). Right containment; must actually merge to end the contamination. One overstatement: "never fired" — the heal fired ≥3 recorded times (all failures or false positives). |

### cinepi-raw

| PR | Title (short) | Verdict | Justification (short) |
|---|---|---|---|
| #62 | docs C6 README | **suspect** | Its central claim ("every README claim checked against code") is falsified: it republished, under a verification banner, threshold examples that (a) via the live key swap and (b) **directly, in the v4l2-ctl example at README.md:425 (`=500,3000`), on both driver branches** write the documented Prohibited pair. (Both examples predate #62; it inherited and certified them.) |
| #63 | redis pipeline + bgsave debounce | **sound** | Touches only per-frame telemetry and the subscriber bgsave; the launch-restore path has no hunks (confirmed). Adversarial re-read found no defect; heavily exercised incidentally (≥5–10 boots). Residual: post-crash Redis staleness window (real; excluded for rounds 7/8 by the I2C readback). |
| #64 | SMPTE base from configured fps | **unverified** | Strong desk forensics, coherent fix, zero destabilisation surface; the target case (24.5 fps, two modes) has zero post-fix hardware evidence. |
| #65 | zoom dedup baseline reset | **unverified** | Sound reasoning, minimal change — and **functionally reverted two days later by evil merge 2bbd9d6** (both call sites deleted; carried to dev by #67's merge; `resetZoomDedup` now has zero callers while comments claim otherwise — confirmed). Nobody noticed. |
| #66 | mono preview + "race-free" sensor mode | **sound** (caveats) | The two merged commits are correct. Caveats: merged 29 min before its own "Round 2" content existed while the body describes it as delivered; "race-free" oversells (no race demonstrated); the trust gate landed only via #67. |
| #67 | trusted-mode gate + WDR verify | **suspect** | Suspect on reasoning, not destabilisation: 1f3383d's premise (12-bit request lands on 16-bit mode) is contradicted — including by libcamera's own scoring math (`pipeline_base.cpp:940-982`) — and 58cf8cc's causal story (silent WDR failure → pedestal) is contradicted by driver docs and the rounds-7/8 record; its round-6 "repro" was probably the boot-latch itself misread. The gate is metadata-only and **cannot** change which sensor mode runs (confirmed). |
| #68 | report restore failures at startup | **sound** | +6 logging lines in else-branches; incapable of destabilising. Flaw: the message names the wrong cause for value-rejection failures (flagged by review 8 min before merge, not applied). |
| #69 (open) | threshold order fix + prohibited-pair refusal | **sound** | Swap confirmed end-to-end (source both branches + hardware I2C readback); fix direction and guard correct; stateless, can only narrow what reaches the sensor. Gaps: equal pairs ({0,0}) still pass; post-fix the operator's habitual `low 4095/high 0` gets refused (behavior inversion); post-fix runtime 0 boots. Its "prohibited ⇒ pedestal-only" justification is overstated by the record (§7). |

### The stranded-commit sweep

| Repo/branch | Merged PR | Stranded | Significance |
|---|---|---|---|
| cinemate `fix/round8-clearhdr-gain-shock` | #175 | **f7cedba (the actual shutter kick), e3963cb (stale-hdr gate fix)** | **Highest impact.** dev runs the gain shock the PR body says didn't work; the fix the body describes never landed. Both ride open #176. |
| cinemate `fix/mono-clearhdr-stack` | #166→#172 | none remaining | The #166-era stranding fully landed via #167/#170/#171/#172. |
| cinepi-raw `fix/mono-clearhdr-stack` | #66→#67 | none remaining | Landed via #67 — **but** the #67 merge (via 2bbd9d6) silently deleted #65's zoom hooks. |
| cinemate `feature/dev-track` | #161 | 10 post-merge commits | Docs/duplicates; minor test-rename residue only. |
| cinepi-raw `fix/clearhdr-threshold-key-swap` | none (open #69) | the fix itself | Until merged, every threshold write on dev is swapped. |
| cinemate + cinepi-raw `feature/clearhdr-controls` | no PR | INNO-MAKER knob defaults; **HCG Redis→V4L2 wiring** | Never merged; dev has zero HCG wiring (confirmed). HCG sits in the sensor's analogue chain — a potential *probe* for §5's hypothesis, not a believed-landed fix. |
| driver `port/clearhdr-upstream-fixes` | no PR | 3 ported commits | Correctly absent (tried 08-27, "same result", reverted — though that test predates the kernel Y16 fix and its conditions were uncaptured). |
| driver `fix/cinemate-modes` | no PR | 360cdb4 — the **only** merge of the two driver lines ever made | Never booted. |
| cinemate `fix/link-frequency-over-spec-warning` | no PR | 71ec057 | The D-PHY over-spec warning the team may believe exists does not. |

Process pattern: **every PR self-merged, zero reviews acted on, several within 10–60 seconds of opening; two PR bodies rewritten after merge to describe unmerged code (#166, #175).** The "Pi-unverified" banners functioned as disclaimers, not gates.

---

## 3. Q2 — The 6.12.y → innomaker-v1.0 driver diff

Three axes read exhaustively (enable_streams/tables; control init/replay; power/PM/probe/timing), then adversarially re-attacked (R2). Full detail in `evidence/q2_*.json`, `verify/R2*.json`.

### Verdict: **No — nothing in the swap introduces a per-boot entropy source or once-per-boot register path.** [confirmed]

- `power_on`/`power_off` **byte-identical**; runtime-PM identical (autosuspend 1000 ms, same call sites); probe writes nothing but a chip-ID read (delta: one `of_property_read_bool` for ccmp); standby/XMSTA choreography identical; `common_regs` (226 entries) byte-identical and identically ordered; control set, CIDs, defaults (compound `{0x0FFF,0}` memcpy'd into p_cur/p_new), registration order, and the `__v4l2_ctrl_handler_setup` call site identical. **Nothing in either branch executes once-per-boot** (`common_regs_written` is write-only dead state in both). No module params, no entropy sources, uncached regmap in both. **[confirmed]**
- Deterministic-per-stream-start differences: innomaker's ClearHDR table appends 7 threshold/slope entries (EXP_TH_H via byte-split writes); a **WINMODE crop block** every start (the largest never-golden-validated sensor-state delta, with a driver-admitted unexplained ClearHDR×OB interaction, `imx585.c:1976-1986`); TPG writes at every setup; manual VMAX/HMAX/SHR wiped each start; the ccmp `-EINVAL` gate; strict error checking (the *silent-failure* asymmetry belongs to the **older** branch). Inventory-complete per R2 (SHR_MIN_HDR 10→16, HMAX table cells inert at 1440 Mbps, EXP_BK menu 9→8, pad guards, crop bounds, RAW10 — all deterministic values). **[confirmed]**
- **The prohibited-transit correction (R2):** the ~2-transaction Prohibited EXP_TH transit during bring-up is **not introduced by the swap** — 6.12.y @ cb7c7a6 already transits it for ~1 transaction at handler setup after any true power-on (TH_H written first while the sensor-side TH_L still holds its power-on 0x1000). The diff merely moves it earlier and widens it ~1→~2 transactions (through intermediate TH_H=0x10FF), while *removing* the later ctrl-path transit by pre-zeroing TH_L. Same class, quantitative change only. And the transit is **conditional on a true sensor power cycle** — a restart inside the autosuspend window leaves TH_L=0, no transit. **[confirmed]**
- **Two contradictions of inherited premises:** (1) the golden-era 6.12.y default was the steady Prohibited pair `{512,1024}` replayed at every start — the golden branch's threshold sequencing was *dirtier* than the failing branch's, and the golden run shows prohibited/degenerate register states are recoverable by later writes; (2) the bring-up window with power-on `0x1000/0x1000` blend config standing under an engaged WDMODE is *longer on the golden branch* (~22 writes vs ~13). Both run the wrong way for blaming the swap. **[confirmed]**
- Hardware facts established on the way: **neither overlay wires `reset-gpios` — the driver never toggles XCLR on this hardware**; the only switched elements are vana (`cam1_reg`, 300 ms startup delay) + INCK; the `always-on` dtparam exists (dormant fragment@99) but cinemate never emits it; vdig/vddl are dummy regulators. Whether a vana cut actually depowers the module is board wiring — **[unknown]**, and it is the one thing that could make the widened transit quantitatively relevant (a single latching trial per boot). R2's refutation conditions: a ≥10-boot A/B of the two drivers on the same rig; no such data exists.

---

## 4. Q3 — Mono versus colour

**Was the instability ever looked for on colour? No.** The last colour session of any kind is 2026-08-10 (~1 boot, byte-identity only, 6.12.y driver). Every hardware-log entry from 08-23 onward is the mono rig; no PR in the window mentions a colour check. "Colour is immune" is indistinguishable from "colour was never watched." **[confirmed as record-absence]**

Per-layer mono divergences (full lists in `evidence/q3_*.json`); **none can produce boot-to-boot variance**:

- **Driver:** mono = one static DT boolean read at probe; mono ClearHDR programs *byte-identical* sensor registers to colour (Y16/Y12 sit in the same classifier sets); BIN_MODE 0x3019 written every start (and the three upstream "mono binning fix" commits are one fix — #6 and #7 are empty commits). The one genuine mono-vs-colour hardware datum in the record — **binned 12-bit ClearHDR returns pure BLC on mono but passed the 08-10 goldens on colour, same registers** — is structural evidence for mono-specific susceptibility to pedestal states in the selection/combine stage. **[confirmed]**
- **libcamera:** ClearHDR-unaware (zero hits for hdr_scale/clear_hdr); persists nothing, reads no per-boot state; mono tuning is a stale fork (missing awb/ccm; pre-retune geq/lux/noise; black_level 3200 in both). Everything mono-divergent acts downstream of the CFE raw tap and cannot make a uniform raw pedestal. Two boot-latch-shaped inputs it faithfully forwards: `LIBCAMERA_RPI_MAX_PIXEL_RATE` (per-process → HBLANK→HMAX; **HMAX was never in the failing-take readback list**) and kernel-persistent clear_hdr/ccmp state gating enumeration. No `rpi.sync` in either imx585 json — SyncMode is a silent no-op (hardens that elimination). libcamera's scoring math also contradicts PR #67's premise. **[confirmed]**
- **cinepi-raw:** all sensor writes funnel through the control cache; final register state is order-independent. Divergences are value-shaped and Redis-keyed — boot-latched by construction but excluded as resident causes for rounds 7/8 by the I2C readback. Live items: the threshold key swap (#69) and `EXP_GAIN 0x3081` seeded to +6 dB (below the AppNote's 9.6 dB sum floor at gain 0; **never read back during a failing take**; the golden runs plausibly ran +12 dB). Latent: `cg_rb` launch UB (`strtok` on an unchecked optional — mono-leaning, pre-camera crash risk only). **[confirmed]**
- **cinemate:** mono divergences are launch-time only (AWB/cg_rb omission, `_mono` tuning file, cg_rb re-apply skip). The real variance carriers are state and ordering: the never-seeded **`(hdr, sensor_mode)` Redis pair** decides what a boot launches, written non-atomically by self-heal and startup fallback against a **per-boot re-derived mode table** (a failed `--hdr sensor` probe silently renumbers it); `cp_controls` delivery depends on prior-boot Redis via the dedup; **real boots get a hidden second full camera start (Plymouth handoff) that manual restarts don't** — a systematic boot-vs-restart confound; and at dev the **self-heal cascade** can add up to 4 extra full relaunches per start_all on any ClearHDR boot whose preview probe succeeds (the detector false-reads "stuck" on this rig's lensless scene). The **quad-rotary suspicion is refuted**: its init-failure path writes nothing to Redis. The 0/0 "degradation persisting across reboots" was cinemate's own unconditional per-start seed (with logs wiped at each start). **[confirmed]**

---

## 5. Q4 — Ranked mechanisms for a boot-latched pedestal

Constraint set: (a) varies across boots with identical code/config/registers; (b) consistent within a boot; (c) survives every raw-I2C elimination; (d) escape by light transient in either direction / manual shutter-to-1° / (some) resolution bounces, while gain writes and (some) bounces fail — noting per §7 that the escape/failed sets are **small-N samples of a stochastic escape, not a clean partition**; (e) SDR unaffected on the same boot; (f) identical pedestal in 12-bit CCMP (200) and 16-bit linear (3200) with CCMP_EN=0 — upstream of the container split.

### H1 — A condition-dependent pedestal state of the sensor's ClearHDR data-selection/combine stage — **top rank** [probable]

- **The stage is real and its pedestal modes are documented and partly measured.** Two register-*valid* configurations of it produce exactly the observed output: the equality/blend-fallback case (`TH_H=TH_L=0x1000` measured on this hardware family: HDR-16 max ~4200 with pedestal 3200, vs ~36000 fixed — `imx585.c:523-536` comment, commit be3cb94) and the Prohibited order (`imx585.c:1530-1543`, commit 954a52a: "HG selection is disabled and LG is multiplied by zero by the blend logic… only outputs the BLC pedestal"). **[confirmed]** Note the mechanism language is *digital selection/blend*; nothing in either driver anchors an "analogue combiner" — the correct locus statement is "the HG/LG combine/data-selection chain, upstream of the CCMP-vs-linear split, invisible over I2C" (R5 correction). SDR is unaffected because WDMODE=0 bypasses the chain.
- **The stage's behaviour is demonstrably condition-dependent.** The same Prohibited pair that 954a52a measured as pedestal produced *real data* twice in the rig's own record (the 08-10 goldens plausibly ran the `{512,1024}` default; the round-4 recovery wrote `H=2048<L=3584` through the swap and "restored real data instantly"). A stage that yields pedestal on some occasions and real output on others under identical register values **is** the phenomenon, observed from the register side. **[confirmed]**
- **The defect = that stage holding its pedestal mode with correct registers.** Entry happens at ClearHDR engage (WDMODE+COMBI_EN during bring-up — where every fresh-power-on start transits the degenerate power-on config and briefly the Prohibited pair, on *both* driver branches; H2 below). **Why it presents as boot-latched:** per R1, engages are rare and clustered at startup — takes never re-engage — so within-boot consistency is largely *structural*; and the two record datapoints where re-engages happened on a failing boot (the two automated bounce failures) suggest the state also *persists across re-engages*, favouring a genuine latch over an independent per-engage roll. The record cannot fully distinguish "latch set once per boot, persisting" from "per-engage roll biased by conditions stable within a boot" — both fit everything; the §6 experiment separates them. **[probable]**
- **Entry bias, unmeasured:** every characterized failing boot ran the bare, lensless sensor flooded at ~99.9% of full scale; the golden and matrix verifications used structured scenes. Saturation (or ambient light) at engage is an untested covariate that would supply the boot-to-boot variation (room light differs across boots) — and it is the record's own named open question. **[unknown]**
- **Escape:** stochastic, triggered by large sustained changes in integrated photocharge — optical (flash, cover) or integration-time (the manual shutter-to-1° escape **is** an SHR register write, so "registers can't clear it" is wrong as stated; the correct narrowing is *gain, threshold, and full mode reprogramming don't reliably clear it; a large sustained integration change does*). The automated failures are weak evidence: the automated shutter kick **never ran** (§7.2); the gain shock bypassed the normal path but did deliver writes (gain is not the trigger variable); the mode bounce failed twice *and* succeeded on other occasions per the code's own comments — probabilistic, and judged by a detector measured to carry no information. **[confirmed corrections; probable synthesis]**
- **What would refute H1:** real varying data on the documented `/dev/video0` CSI-bypass capture during a failing take (moves the fault downstream); an I2C register diff across a light-flash escape showing any register change; a fill beginning mid-stream with no transient; pedestal reproduction with lens/ND at moderate light killing the saturation-bias variant.

### H2 — Entry trigger: bring-up transient through degenerate/prohibited combiner configs [probable as H1's entry detail; weak standalone]

On every ClearHDR start after a true sensor power cycle, both branches engage WDMODE while EXP_TH/EXP_BK/ACMP still hold power-on defaults (`0x1000/0x1000` = the measured pedestal blend config) — ~13 writes' window on innomaker, ~22 on 6.12.y — and transit the Prohibited pair (~2 transactions innomaker via byte-split table writes; ~1 transaction 6.12.y at handler setup). A latch set in this window survives the steady-state readback. It is deterministic per fresh-power-on activation, so it needs H1's persistence and/or an engage-time bias to produce boot variance. **The diff runs the wrong way to blame the driver swap** (same class in both branches; the *blend-config* window is longer on the golden branch). **[confirmed mechanics]**

### H3 — Userspace boot-latched value carriers (Redis/dump.rdb → control cache → replay) [confirmed as a class; **excluded as the resident rounds-7/8 cause**; prime historical contaminant]

The one structural way this stack makes boots differ: dump.rdb + seeding decide, per boot, what the replay programs. It demonstrably produced pedestal-adjacent states before (the 0/0 era; the swap; README's own examples — including a v4l2-ctl example that writes the Prohibited pair *directly*, unfixed even by #69). For rounds 7/8 the I2C readback shows the driver-default pair — no write happened — so it is not the current resident cause. A **transient** prohibited pair written mid-boot and corrected by the next replay would leave the observed clean-register signature; whether any failing boot saw one is checkable in journals since #68's log lines. **[confirmed mechanics / unknown occurrence]**

### H4 — Per-boot mode-identity drift (`(hdr, sensor_mode)` desync; probe-dependent table renumbering; pixel-rate env → HMAX) [confirmed mechanics; killed for rounds 7/8 by the live-subdev check; historical contaminant]

The failing takes had the correct Y12 3840×2160 idx3 mode live. This class very plausibly explains earlier "it filled/it worked" noise (the 08-26/27 mode-label divergence era). HMAX remains unread during a failing take — cheap to close.

### H5 — Value-shaped susceptibility modifiers [confirmed states; weak by the ranking rule]

`EXP_GAIN 0x3081` at +6 dB (cinemate's deliberate seed) vs +12 dB golden-era default — an unmeasured combine-stage input whose sum with gain sits below the AppNote combination window at gain 0; the WINMODE-crop×ClearHDR combination (innomaker-only, never golden-validated, driver-admitted unexplained OB behaviour); ACMP2 1/4→1/16. None varies per boot; each could modulate susceptibility.

**Explicitly down-ranked:** anything register-resident (measured); the WDR write path (no registers; timing eliminated; the #67 gate verifies control state, not combiner state); libcamera processing (cannot touch raw); the self-heal as *cause* (postdates the round-3 constant-200 sighting) — it is a measurement contaminant, not the defect.

---

## 6. The single cheapest discriminating experiment

**On the next confirmed-failing boot, without rebooting and without touching the scene:**

1. **Free:** count this boot's sensor power cycles and engages so far: `journalctl -b | grep -Ec "imx585.*(power_on|power_off)"` and `grep -c "Streaming started"`. Both drivers log every transition (`imx585.c:2093/2122`). Caveats for the count (R1): probe itself contributes one on/off pair before any streaming; a real boot gets a second full start at the Plymouth handoff; self-heal bounces add pairs; and because `pm_runtime_mark_last_busy` is called only at probe, `power_off` can fire almost immediately on *any* stream stop — a power cycle does not imply a >1 s gap.
2. `systemctl stop cinemate-autostart`; **wait 120 s** (guarantees runtime-PM suspend → vana+INCK off, plus generous rail-drain margin); start it; observe fill/clean. **Repeat 3×.**
3. If still filling after all three: `rmmod imx585`, wait **5 min**, `modprobe imx585`, restart the stack, observe.

**Pre-registered predictions:**

| Hypothesis variant | Step 2 (3× stop/120 s/start) | Step 3 (rmmod + 5 min) |
|---|---|---|
| **H1-latch, vana cut really depowers the module** | fill **re-rolls** — at least one of the three restarts plausibly comes up clean (each restart is a fresh cold engage) | moot |
| **H1-latch, module not depowered by cam1_reg** (board wiring) | fill **persists** all three | fill **persists** — next step is electrical (measure the module rail), not software |
| **H1 per-engage roll biased by boot-stable conditions** (e.g. ambient light) | fill **persists on all three** *if* the bias holds (same room, same light) — distinguishable from the latch variants only by also changing the light: add one covered-sensor restart; the roll variant predicts that restart can come up clean | persists (same bias) |
| **H3-transient (a userspace write latched it this boot)** | persists; but step 1's journal must show a threshold/control write line before the first fill — **absence of such a line kills this branch outright** | persists |
| any per-activation race (already disfavoured) | outcomes **vary** across the three restarts with no pattern | — |

Step 1's counts also retroactively answer whether round-8's "5 fills in a row" spanned any engage at all — data the record lacks.

**Named follow-ups (cheap, in order):** (a) raw-I2C read of **EXP_GAIN 0x3081** and **HMAX** during one failing take (two registers never in the readback set); (b) an I2C snapshot of the full ClearHDR register set immediately **before and after a light-flash escape** — any register change restores a register mechanism, none confirms internal state; (c) the **covered-vs-lit boot series** (10+10) for entry-vs-light — the record's own open question, and the discriminator for the roll-vs-latch variants; (d) the `/dev/video0` CSI-bypass capture (procedure already in hardware-log) during a failing take to nail the sensor locus; (e) one **colour-sensor ClearHDR boot series** — colour has never been sampled for intermittency; (f) re-test the automated **shutter kick** (it has never actually run) with a dwell ≥ the measured ~12-frame control-apply latency, and with delivery verified at the subdev.

---

## 7. Corrections to the eliminated-facts list (adversarially verified)

1. **"Mid-scale data-selection thresholds do not clear it" — STANDS.** This report's draft claimed the test was contaminated by the key swap; the refuter proved otherwise: the recorded test deliberately wrote `low=3000/high=500` (name-reversed), which through the swap landed as the **valid** pair `EXP_TH_H=3000 ≥ EXP_TH_L=500`, verified by raw-I2C readback during the 2026-08-30 fills (PR #69 body). The elimination rests on register-level evidence. Only a residue survives: any *additional, unrecorded* round-7 attempt issued as low<high without readback would have landed prohibited. **[confirmed]**
2. **"An automated shutter kick through the normal control path failed" — CONTRADICTED: it never ran.** dev's merged self-heal is the gain shock (`_shock_analog_gain`, e660925); `_shock_shutter_angle` exists only on the unmerged branch (f7cedba, authored 08-30 10:58, after the round-8 merges), and the branch's own commits state "the shutter kick's automated form has never run on the rig" (24ee25f; PR #176 table). The elimination should be struck: *never tested, not failed*. The genuine live failures are the mode bounce (twice) and the gain shock (which bypassed the normal path via v4l2-ctl but did deliver writes — gain is simply not the trigger variable). **[confirmed]**
3. **The "24 dB analogue swing moved output ~5%" datum — provenance unrecorded, datum stands.** It exactly matches the gain shock's 0→80 sweep (0.3 dB/step), but the same eliminated bullet's below/inside/above-window claims require a multi-point sweep the shock cannot produce, so a deliberate operator sweep is equally supported. Either way the writes reached the sensor (gain is not grab-bound), so the elimination itself (gain doesn't clear it) survives. `ROUND8-RESULTS.md` — needed to settle it — was never committed to any repo. **[confirmed absence; undetermined provenance]**
4. **The round-4 "0/0 degradation → pedestal, cleared by re-issuing thresholds" — reinterpreted.** The 0/0 pair was cinemate's own per-start seed (not the quad-rotary; refuted from source), and the cure (`low 2048/high 3584`) landed through the swap as the doc-Prohibited pair yet restored real data instantly. Round-4's fill responded to a threshold write while the rounds-7/8 fill did not — **most probably two distinct states**: a real threshold-coupled pedestal (register-resident, recoverable) and the boot-latch (register-invisible). The paradox that the *cure* wrote a Prohibited pair is itself evidence that the selection stage's pedestal behaviour is condition-dependent (§5-H1). **[probable]**
5. **"Prohibited pair ⇒ pedestal-only, always" — overstated.** Bench-measured true once (954a52a); contradicted twice by the rig's own record (golden-era default; round-4 cure). Treat as condition-dependent. PR #69's guard remains correct engineering regardless (never write spec-prohibited states). **[confirmed]**
6. **Round-8 boot statistics — exposure confirmed, contamination unquantified.** The self-heal was live and default-on from 08-29 21:12; on this rig's lensless scene its detector false-reads "stuck", so any post-merge boot statistic had a heal armed at every start (gain sweep + up to two bounces = four relaunches). The 5-fill/3-clean counts are not timestamped relative to the merges. **[confirmed exposure]**
7. **PR #67's premise** ("12-bit request lands on 16-bit mode") — contradicted by libcamera's scoring math and the live subdev. **[confirmed]**
8. **Hardware-log 2026-08-26 "thresholds 4095/0 survive reboot"** vs committed code of that date (unconditional 0/0 re-seed) — irreconcilable unless the rig's working-tree settings.jsonc was locally edited; rig "shipped defaults" observations from that era are unreliable. **[probable]**
9. **The hardware-log's bounce record is internally contradictory:** "a resolution bounce … clears it (operator-confirmed)" vs. two automated bounces failing — same machinery in source (`cinepi.restart` → stop_all/start_all in both cases), so the manual/automated distinction cannot carry the difference; the honest reading is *bounces clear it sometimes* (stochastic escape). The log entry should be amended. **[confirmed]**

---

## 8. What could not be determined from source (named explicitly)

- The **cinemate SHA actually running on 2026-08-10** (`cede78bf` unresolvable) and the Pi's libcamera build state that day.
- **Live EXP_TH values during the 08-10 goldens and the 08-27 milestone/matrix takes** — both anchors are entangled with unrecorded threshold state (the milestone favors an unrecorded operator set of 2048/3584; a re-issue would have been needed after each matrix-cell reboot and none is recorded).
- **Boot counts** for the 08-10 verification (plausibly 1) and the rate matrix (≥6 inferred).
- Whether **cam1_reg switching actually depowers the sensor module** (board wiring; decides H1's sub-variant — §6 discriminates behaviourally).
- Whether any failing boot's journal shows a **threshold/control write before the first fill** (checkable on-rig since #68's log lines).
- Whether round-8's fills/clean-runs **spanned any ClearHDR engage or power cycle at all** (recoverable from that boot's journal — §6 step 1).
- **Ambient light level at boot/engage** for any failing vs clean boot — never recorded; every characterized failing boot was the bare lensless sensor at ~99.9% full scale, every verification used structured scenes (untested covariate).
- The contents of `ROUND8-RESULTS.md` / `OVERSEER-NOTES-R6/R8.md` / `RATE-MATRIX-RESULTS.md` — cited by the record, never committed to any repo.
- Whether `EXP_TH_H=EXP_TH_L=0` flattens output or selects pure-LG (never measured; the only equality measurement is at 0x1000).
- Anything about the sensor's internal selection/combine stage beyond its register interface (the AppNote is not in the repos; no scope/logic-analyzer data exists).

---

## 9. Overturned or corrected premises (index)

| # | Premise | Status | Source |
|---|---|---|---|
| 1 | "The golden 6.12.y config had sane thresholds" | **Overturned** — default was the Prohibited `{512,1024}`, replayed every start | `479117e:imx585.c:955` |
| 2 | "Prohibited pair ⇒ pedestal-only, always" | **Overstated** — condition-dependent (bench true once; contradicted twice in the rig record) | §7.5 |
| 3 | "Quad-rotary loop degraded the thresholds" | **Refuted** — writes nothing; cinemate's own per-start seed did it | `quad_rotary_controller.py` |
| 4 | "The driver power-cycles/XCLR-resets the sensor between takes" | **Corrected** — no reset-gpios anywhere; takes never touch the stream; power cycles cluster at startup | dts + `imx585.c:2373`; R1 |
| 5 | "#175 gave dev the shutter kick" | **Refuted** — dev has the gain shock; the kick never merged **and never ran** | `origin/dev:cinepi_multi.py:944`; 24ee25f |
| 6 | "#65 fixed the zoom dedup" | **Refuted** — evil-merge reverted; zero callers on dev | `2bbd9d6` diff |
| 7 | "12-bit request can land on the 16-bit mode" (#67) | **Refuted** — scoring math + live subdev | `pipeline_base.cpp:940-982` |
| 8 | "The 6.12.y→innomaker swap is the prime suspect" | **Downgraded** — no variance mechanism in the diff; its transients are same-class in both branches and the blend window is *longer* on the golden branch | §3 |
| 9 | "Mid-scale thresholds were tested through the swap and are contaminated" *(this report's own draft)* | **Self-corrected** — the test was name-reversed and register-verified; the elimination stands | §7.1 |
| 10 | "The automated shutter kick was tried and failed" | **Struck** — never ran | §7.2 |
| 11 | "The rig's 'it worked' anchors are multi-boot" | **Corrected** — colour ~1 boot; milestone 1 boot; matrix ≥6 within 30 h | §1 |
| 12 | "The defect's locus is the *analogue* combiner" | **Re-localized** — the source-anchored pedestal mechanisms are in the digital HG/LG data-selection/blend logic; correct statement: "the combine/selection chain upstream of the container split, invisible over I2C" | R5 |
