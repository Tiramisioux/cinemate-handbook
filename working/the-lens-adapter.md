# The lens adapter (Pinefeat CEF168)

Canon EF lens control through the Pinefeat adapter: iris, focus position, a database of lenses, calibration. The operator-facing side is `docs/pinefeat/`; this page is what to know before changing the code. Design record and decisions: `development/pinefeat-cef168/PLAN.md` (outside the repos).

## Where things live

| What | Where |
|---|---|
| Talk to the board (both backends, CRC, bus discovery) | `src/module/lens/cef168.py` |
| Lens database, iris step table, focus map helpers | `src/module/lens/database.py` — file is `resources/lenses.json`, gitignored, created on first write |
| Calibration, self-test gesture detector | `lens/calibration.py`, `lens/selftest.py` |
| The thread that owns all of it | `lens/controller.py` (`LensController`), started by `lens/startup.py` |
| Controller methods, CLI, registry | `CinePiController.set_iris`/`inc_iris`/`set_focus`/…, `cli_commands.py`, `parameters.py` (`iris`, `focus`) |
| Autofocus tuning layer (inert unless `lens_control.autofocus`) | `src/module/lens_tuning.py`, wired in `cinepi_multi.py` |
| Install: overlay, DKMS, module check | `resources/overlays/cef168/`, `scripts/cef168-module-installed.sh`, `install_cef168_support` |

## Rules that are easy to break

- **No kernel driver is needed for iris, focus, or calibration.** `Cef168Raw` drives the board over I²C (address `0x0d`, 4-byte command frame, 15-byte status frame, CRC-8 polynomial 168, init `0xFF`). The driver (`Cef168Subdev`) is only preferred when it is already bound.
- **The overlay needs the module.** An overlay that sets `lens-focus` with no `cef168.ko` installed makes the sensor wait for a driver that never comes, and the camera never registers. Only enable the overlay after `scripts/cef168-module-installed.sh` passes.
- **The camera I²C bus is not a constant.** Pi 5 cam0/cam1 = 6/4; CM4 cam0 = 0 (measured); CM5 depends on the carrier board. Bus discovery goes subdev name → sensor subdev name → a table that deliberately has no CM5 row. Never reuse `ir_filter.py`'s table.
- **Iris is write-only.** The board cannot say where the iris is. CineMate stores the commanded value (Redis `iris`, entry `last_iris`) and re-applies it when a lens is detected. Always write absolute values; the relative control only works after an absolute write.
- **The board cannot report an aperture range or focal length** over I²C — those need its UART. The operator types the range per lens. An out-of-range iris value is silently ignored by the lens.
- **No zoom.** Canon EF has no power zoom.
- **Lens control can only be switched on while the adapter is found.** `set_lens_control(1)` refuses otherwise; effective state is toggle AND found.
- **Per-lens capabilities gate the controls.** Each entry has `capabilities {iris, focus, autofocus}` (`null` = untested). A calibration that never sees a focus position marks focus and autofocus false. Controls grey out with a reason; they never fail silently.
- **Calibration is never automatic.** It runs from the Calibrate button, the `calibrate lens` command, or the lens's own AF/MF ×3 self-test gesture (`calibrate_on_selftest`). It is refused while recording.
- **The self-test detector needs the whole signature** (near → far → near within about 15 s, or several separate movement bursts on an uncalibrated lens). Turning the focus ring by hand must not start a calibration sweep. Its thresholds are module constants in `selftest.py`.
- **Do not seed `af_mode`.** Seeding it would switch off stock Camera Module 3 autofocus.
- **Autofocus is paused, not removed.** `rpi.af` in a tuning makes cinepi-raw default to *continuous* AF unless `--autofocus-mode manual` is passed, and libcamera moves the lens to its default position on every cinepi-raw start. The AF layer stays off by default; the cinepi-raw side lives unmerged on `feature/pinefeat-af`.
- **Tuning files are platform-aware now.** Pi 4-family boards use the `bcm2835` (vc4) tuning, Pi 5-family the `pisp` one: `tuning_files.py` resolves the data directory and expected target per platform, for the launch, the override, and the white-balance curve.

## Hardware findings that shaped it

- The Sigma 18-35 f/1.8 DC HSM Art (board lens id 112) never reports a focus position and its focus motor ignores the board's focus commands; its iris moves only slightly across the whole range. Calibration therefore fails on it, correctly. See `../lessons/hardware-log.md`, 2026-10-04 and 2026-10-06.
- On the CM4 dev unit the lens subdev is `cef168 0-000d` beside `imx477 0-001a`.
- A Canon-made lens is still the real test of focus, calibration and the iris range.

## Adding a lens control

Follow [`changing-a-control.md`](changing-a-control.md): the method, `cli_commands.py`, both `ACTION_METHODS` copies (group "Lens (Pinefeat)"), `docs/cli-commands.md`, any `"method"` strings. Then register a name in `parameters.py` if rotaries or pots should reach it, and check `gui_text_check` if the Lens pane's text changes (`resources/gui-text/12-lens-lens-pinefeat.md`). The detection side belongs in [`probing-i2c-peripherals.md`](probing-i2c-peripherals.md).
