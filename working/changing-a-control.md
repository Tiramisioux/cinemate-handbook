# Changing a control: Redis key, controller method, or settings key

The three most common categories of change, walked through. Read
[`../orientation/entry-points.md`](../orientation/entry-points.md) first for the full table —
this page is the worked version of its top three rows.

## Adding or renaming a Redis key

1. Add the member to cinemate's `ParameterKey` enum (`redis_controller.py`).
2. If cinepi-raw also reads or writes it, add the matching `CONTROL_KEY_*` macro on that side
   (`cinepi_state.hpp`).
3. If an operator should know the key exists, add a row to `docs/redis-keys.md`.
4. Run `tools/redis_key_diff.py` locally before pushing if the key crosses repos — it's a
   ratchet in CI, not a gate, but don't be the PR that needs the ratchet bumped.

**Watch for:** the enum is convention, not enforcement. `set_value()` accepts any string, and
several live keys bypass the enum entirely — see
[`../architecture/redis-contract.md`](../architecture/redis-contract.md). Adding the enum
member doesn't stop the next person writing the raw string instead.

## Adding a controller method (a new action)

This is the one with the most hidden edits. A new public method on `CinePiController` needs
**all four** of:

1. The method itself, on `CinePiController`.
2. An entry in `cli_commands.py`'s command table — this is what makes it reachable from CLI,
   serial, **and** `POST /api/v1/cmd` simultaneously, since all three share that table.
3. An entry in the settings editor's action catalogue — **in both places it exists**: the
   Python side and its hand-maintained JavaScript copy. These have drifted before, including
   agreeing with each other on the same wrong entry.
4. A row in `docs/controller-methods.md`.

`tools/gui_field_extract.py` gates at zero in CI and will catch a method that's referenced
somewhere but doesn't actually resolve. It will not catch a method you forgot to reference
anywhere at all — that's a silent no-op button, not a CI failure. See
[`../orientation/the-traps.md`](../orientation/the-traps.md) #3 for exactly how that fails in
practice: `getattr(controller, name)` resolving to `None` produces a log line, not an error,
and nothing about pressing the button looks different to the operator.

**If you're renaming an existing method**, remember it may be a **user-facing API**: GPIO
buttons, the quad rotary controller, and pot mappings in `settings.jsonc` reference controller
method names as plain strings. Renaming one silently breaks any camera whose config
references the old name.

## Adding a settings key

1. Add the key to `settings.jsonc`, with a comment explaining what it does — comments here
   are part of the product, not disposable (see [`../conventions/style.md`](../conventions/style.md)).
2. Add it to `settings.schema.json`. This is **required**, not optional: `additionalProperties`
   is `false` throughout, so an undescribed key is rejected by anything that validates against
   the schema.
3. If it needs a default when absent, add it to `config_loader.py`'s default chain — but
   check first whether a default for this concept already exists somewhere else. Defaults are
   currently stated in more than one place in this codebase, and they don't all agree; adding
   a fifth version of one is worse than picking the one that should be authoritative.
4. Add a heading to `docs/settings-json.md` matching the key name.

`tools/docs_drift_check.py` and a schema test both run in CI against this.

## The common thread

Every row above has the same shape: **the primary edit is easy to find; the second edit is
not.** When in doubt, grep the exact string you're changing (a key name, a method name)
across the whole tree — `settings.jsonc`, `docs/`, both settings-editor catalogues, and the
other repo — before assuming you're done. See
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md) for what's automated
already, and consider adding a check rather than a comment if you find a new place this kind
of change needs to land twice.
