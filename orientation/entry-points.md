# Entry points — where do I go to change X

The recurring cost in this codebase is not finding the primary edit — it's the **second
edit** somewhere else that nothing reminds you about. This table's fourth column is the
point of the page. Where it says "nothing", you are on your own: no check exists, and that is
where drift has historically appeared.

Six drift checks exist and run in CI — see
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md) for what they gate.

| Adding / changing | Primary edit | Also update | Caught by |
|---|---|---|---|
| A Redis key | `redis_controller.py`'s `ParameterKey` enum | cinepi-raw's `CONTROL_KEY_*` if it crosses the boundary; `docs/redis-keys.md` | `tools/redis_key_diff.py` (ratchet, cross-repo side) |
| A controller method / new action | A public method on `CinePiController` | **Five places**: `cli_commands.py`'s command table, `app/settings_editor.py`'s action catalogue (Python **and** its JS copy), `docs/controller-methods.md`, and any `"method"` string under `settings.jsonc`'s `hardware_controls`/`input_peripherals` (buttons, switches, rotary encoders) | `tools/gui_field_extract.py` (gated at 0) checks the settings-editor catalogue only; `tools/docs_drift_check.py --strict` separately gates `docs/controller-methods.md`; **nothing** checks `settings.jsonc`'s method strings — see [`the-traps.md`](the-traps.md) #3 |
| A settings key | `settings.jsonc` | `settings.schema.json` (**required** — unknown keys are rejected), the loader's defaults, `docs/settings-json.md` | schema test, `tools/docs_drift_check.py` |
| A GUI field | `simple_gui.py`'s `populate_values()` | Usually nothing — the web GUI consumes the same dict and gets it automatically | `tools/gui_field_extract.py` |
| A colour | `simple_gui.py` module constants or `self.colors` | The CSS custom properties in the web template | `tools/design_token_diff.py` (gated at 0) |
| A Python dependency | `requirements.txt` (portable) or `requirements-hardware.txt` (needs a Pi) | Nothing — the installer reads both | the `pytest` CI job, if the import is portable |
| A CLI command | `cli_commands.py`'s command table | `docs/cli-commands.md` and/or `docs/cli-user-guide.md` | **nothing** |
| A systemd service | `services/<name>/` with a `.service` file and a Makefile | `services/Makefile`'s service list, the installer's service step, `docs/system-services.md` | **nothing** |
| A sensor | `resources/sensors.json` | `settings.jsonc`'s `arrays.*.steps` if new modes should be exposed; `docs/sensors.md`; a driver step in the installer if it needs an out-of-tree module | **nothing** |

See [`../working/changing-a-control.md`](../working/changing-a-control.md) for a walked-through
example of the first three rows, and
[`../working/changing-the-gui.md`](../working/changing-the-gui.md) for the GUI/colour rows.

## Three things not in the table

**Everything live goes through one cached bus.** `RedisController.get_value()` reads a local
cache, not Redis — see [`the-traps.md`](the-traps.md) #1.

**Two dispatch paths, only one serialised.** See [`the-traps.md`](the-traps.md) #2.

**One process owns the display.** See [`the-traps.md`](the-traps.md) #4 and
[`../architecture/gui-state-model.md`](../architecture/gui-state-model.md).

## Where the map is thin

Stated so you know what you're inheriting rather than discovering it:

- `cinepi_controller.py` is wide, not deep — around 150 methods on one class, averaging
  roughly 16 lines each. "Primary edit: here" doesn't tell you much more than that.
- cinepi-raw's DNG writer (`dng_encoder.cpp`) has changed substantially between reviewed
  snapshots — treat any specific claim about its internals as unverified until you read the
  current file yourself.
- The settings editor's client-side JavaScript (over a thousand lines) is only partly mapped.
  Four corners are now written up — MJPEG stream recovery, the fullscreen probe, the two grid
  sizing traps, and the log console — in
  [`../working/browser-side-traps.md`](../working/browser-side-traps.md) and
  [`../working/repository-and-tooling-traps.md`](../working/repository-and-tooling-traps.md);
  the rest has been scanned for catalogue names but not read closely.
- The Wi-Fi hotspot triangle (a service, an in-app manager, and a superseded copy) is only
  partly read.
