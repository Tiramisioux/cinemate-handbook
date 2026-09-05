# Probing the optional I²C peripherals

The settings editor's i2c pane answers one question — *what is plugged in right now* — and it
has to answer it without disturbing anything that is already running. That constraint is the
whole design. Every driver in this codebase discovers presence as a side effect of a full
initialisation, so the pane cannot reuse any of them; it re-derives presence from the cheapest
primitive that exists. This page is the durable version of that reasoning, so the next surface
that needs to know what is attached does not rediscover it. The implementation lives in
`src/module/app/hardware_probe.py`, its route in `src/module/app/settings_editor.py`, and its
tests in `_test/test_i2c_hardware_pane.py`.

## Presence is a one-byte ACK, never an initialisation

**A probe opens the bus, does a one-byte read at an address, and closes the handle — nothing
else.** `_ack()` in `hardware_probe.py` treats `OSError` as *absence* rather than as an error
(it covers both "no such bus" and "nobody home at that address"), and closes the handle in a
`finally`, including on the failure path — `analog_controls.py` closes only on success, so it
leaks a handle every time the HAT is not fitted. Nothing in the module writes to a bus, which
makes every probe safe to re-run on every HTTP request, with a live take in progress and an
operator's hand on the dials.

The primitive is not new. `AnalogControls.__init__` already finds the Grove HAT this way, and
`SsdMonitor._detect_cfe_hat` and `services/storage-automount/storage-automount.py` already find
the CFE Hat this way. The probe module is a shared, guarded version of a shape the codebase had
in three places.

One guard is genuinely new: `_smbus()` wraps the `import smbus2` in a `try`, returning `None`
off-hardware. Nothing else in `src/` guards that import — which is why the test suite has to
stuff fakes into `sys.modules` (see [`testing.md`](testing.md)). A web request must render on a
desktop checkout rather than 500.

## Why the drivers must not be used to probe

| Driver | What its detection actually does | Why that disqualifies it |
| --- | --- | --- |
| `grove_base_hat_adc.ADC` | Every read path — `read_raw`, `read`, `read_voltage`, `name`, `version` — funnels into `read_register`, whose `except IOError` prints a hint and calls `sys.exit(2)`. The constructor builds a `grove.i2c.Bus()` and can raise on its own. | `SystemExit` derives from `BaseException`, so `AnalogControls.run()`'s `except Exception` does not catch it, and on a Flask worker it unwinds only the calling thread — a 500 rather than a dead process. Either way it is not a probe primitive. |
| `QuadRotaryController._initialize_device` | Builds `busio.I2C`, sleeps 0.1 s, constructs the seesaw, four encoders, four `DigitalIO` switches, then a `NeoPixel` strip and sets its brightness. | It **writes** to the board, and resets encoder/button baselines. Re-running it stamps on a controller an operator may be turning at that moment. |
| `I2cOled._initialize_display` | Builds `busio.I2C`, sleeps 0.1 s, constructs `SSD1306_I2C`, which re-runs the display init sequence. | It blanks whatever is on the screen. A status display going dark because someone opened a diagnostics page is a worse outcome than no diagnostics page. |

Two further reasons the driver objects are not an option at all, independent of what they do:

- **They are unreachable from a request.** `analog_controls`, `i2c_oled` and `quad_rotary` are
  locals inside `run_application()`, and `create_app` publishes exactly six things into
  `app.config`: `REDIS_CONTROLLER`, `CINEPI_CONTROLLER`, `SIMPLE_GUI`, `SENSOR_DETECT`,
  `COMMAND_EXECUTOR`, `SETTINGS`. No handle to any peripheral driver crosses that boundary.
- **Their flags answer a different question.** `AnalogControls` and `SsdMonitor` decide presence
  once at startup and never look again. That is correct for them and wrong for a pane whose
  entire purpose is *right now*. The pane probes per request; the drivers' answers are
  boot-time history.

## The address map

Addresses are data in `DEVICES` / `OLED_TYPES`, not literals scattered through the probe
functions, and each is pinned in the test suite against the code that already used it.

| Address | Device | Bus | Where the repo already used it |
| --- | --- | --- | --- |
| `0x08` | Grove Base HAT (analog inputs) | 1 | `analog_controls.py` ACK probe; default address in `grove_base_hat_adc.py` |
| `0x34` | CFE Hat latch/LED microcontroller | 1 | `ssd_monitor.py` (`_detect_cfe_hat`); `storage-automount.py` (`_cfe_hat_worker`, `_cfe_hat_init`) |
| `0x49` | Adafruit seesaw quad rotary encoder | 1 | `i2c/quad_rotary_controller.py` |
| `0x68` | Real-time clock (DS3231-style) | 1 | `docs/hardware-controls.md` describes the module; no code stated the address before the pane |
| `0x3C` / `0x3D` | SSD1306 / SSD1309 OLED — default, and ADDR strapped high | 1 | **Nowhere.** `i2c_oled.py` constructs `SSD1306_I2C` without an address and takes the library default |

That last row is the reason the addresses live in a table rather than as literals. A value the
repo never states anywhere is exactly the value a future reader cannot verify from the source,
so it is written down once, with a note saying which strapping it corresponds to, and the
matched row is reported back to the caller rather than a bare `True`.

## Scope the bus, or you will mislabel a device

**`0x34` is two different devices on this camera.** On bus 1 it is the CFE Hat's latch
controller. On the camera buses it is the StarlightEye IR-cut filter — `ir_filter.py` maps
`cam1` to bus 4 and `cam0` to bus 6 on a Pi 5. An `i2cdetect`-style sweep across every bus, or a
probe that does not pin its bus number, will report the IR-cut filter as a CFE Hat, or vice
versa. `I2C_BUS = 1` is a module constant, every probe goes through it, and a test asserts the
value with the reason in its own name.

The same instinct applies to fallbacks, and the pane is what exposed the one that was already
shipping: `SsdMonitor` used to accept the Pi 5's PCIe bridge node as evidence of a CFE Hat, so a
plain NVMe was labelled `CFE` in the GUI while the pane, on the same camera at the same moment,
reported nothing answering at `0x34`. The fallback is gone from `ssd_monitor.py`, the probe never
had it, and a test asserts the module exposes no PCIe constant at all — a check, not a comment,
because [a comment cannot fail](../conventions/checks-and-ci.md). For why that shape of fallback
was readable as broken from a desk, see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md).

## Two things the bus cannot tell you — and must not appear to

**An SSD1306 has no size register.** Nothing on the bus can be asked how many pixels it has;
`i2c_oled.py` reads width and height from `output_peripherals.oled` and tells the driver, not
the other way round. So the pane reports geometry from settings and labels it as such
(`geometry_source: "settings"`), and the UI says *configured* rather than implying a
measurement. A test pins that field.

**SSD1306 and SSD1309 cannot be told apart.** Same command set, same addresses, driven by the
same `adafruit_ssd1306` code, and neither part has a readable ID register. An address that
answers could be either, so the pane names both — `"SSD1306 or SSD1309"` — rather than picking
one and being silently wrong half the time. A test pins the string.

The generalisation is worth carrying to any future detection surface: **report the provenance
alongside the value** — probed, configured, or unknown. A UI that shows a configured number in
the same visual slot as a probed one has quietly invented a measurement.

The RTC row is the third instance of the same idea. An ACK at `0x68` says a chip answered; it
does not say the kernel has an RTC. That needs `dtoverlay=i2c-rtc,ds3231`, which CineMate's
fenced `config.txt` block deliberately does not manage, so the probe reports the I²C answer and
`/dev/rtc`'s existence as two separate facts. A Pi 5 with an onboard clock and no DS3231 on the
bus is the normal case, not a fault, and the pane says so.

## Probing is read-only; acting is a different contract

The same pane can also *set* the RTC, and that path deliberately does not reuse the `set rtc
time` CLI command. That command runs `sudo hwclock --systohc` through `os.system` inside the
dispatcher's lock — no `-n`, no timeout, no exit-status check — so on a machine whose sudoers
lacks a NOPASSWD rule it blocks on a console password prompt and starves every other CLI, serial
and HTTP command, and it reports success either way. The pane's version runs `sudo -n`, checks
the return code, translates a sudo prompt into a message that names the actual cause, and reads
the clock back to verify the write took. That act-then-verify shape is the house pattern (see
[`../conventions/style.md`](../conventions/style.md)); `os.popen`/`os.system` without a status
check is not.

## Extending it

Recognising another display controller, or another peripheral, is a new row rather than new
code: append to `OLED_TYPES` or `DEVICES`. Keep the shape — a `key`, a human `name`, a `hint`,
the address tuple — because the route serialises those straight to the client and the pane
renders whatever it is given. If you add a device that lives on a camera bus, add the bus to the
row too rather than widening `I2C_BUS`; the scoping is load-bearing.

## What the tests pin, and why each one exists

`_test/test_i2c_hardware_pane.py` is worth reading before changing the probe, because each test
encodes a failure someone would otherwise reintroduce:

| Test | The mistake it prevents |
| --- | --- |
| Absent `smbus2` reports everything absent | A desktop checkout 500s on the pane |
| A refused address is absence, not an error | Treating "nobody home" as a fault |
| The handle is closed even when nothing answers | The `analog_controls.py` leak, copied forward |
| Probing never writes to the bus | A future "probe" that resets or blanks a live device |
| Addresses match the probes already in the codebase | The table drifting from `analog_controls.py` / `quad_rotary_controller.py` |
| `I2C_BUS == 1`, with the reason in the test name | An unscoped sweep confusing the CFE Hat with the IR-cut filter |
| `geometry_source == "settings"` | The UI implying a display was measured |
| The controller string names both parts | Guessing SSD1306 over SSD1309 |
| A failed sync answers 500, not a cheerful 200 | The `set rtc time` bug, reimplemented |

All of it runs off-hardware. Everything on this page is a **structural** finding — settled by
reading the source — which is precisely why it did not need a Pi. What a probe does on a bus
with a real device attached is a consequence finding; see
[`hardware-session.md`](hardware-session.md) for the difference and for how to settle the
second kind.

## Further reading

- [`hardware-session.md`](hardware-session.md) — settling a claim that genuinely needs the
  machine, and the structural/consequence split.
- [`testing.md`](testing.md) — the `sys.modules` stubbing hazard the unguarded hardware imports
  create.
- [`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md) — why the address table is
  pinned by tests rather than by a comment.
- [`../conventions/style.md`](../conventions/style.md) — the legitimate error-handling shapes,
  including act-then-verify around a subprocess.
- [`../architecture/gui-state-model.md`](../architecture/gui-state-model.md) — why the settings
  editor is a different model from the live GUIs, and reads the machine rather than shared state.
- [`../lessons/review-archive.md`](../lessons/review-archive.md) — the map into `system-review/`,
  including the CFE-Hat-detection and `os.system` findings this page builds on.
