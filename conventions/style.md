# Style — how code is written here

Derived from measuring the actual codebase, not from general Python practice. Where a rule
is near-universal here, that's stated; where the codebase disagrees with itself, that's
stated too rather than smoothed over.

## Naming — settled, leave it alone

Functions and methods: snake_case, essentially without exception. Classes: CapWords.
Module-level constants: `SCREAMING_SNAKE`. Private: a single leading underscore, used
consistently for both methods and helper classes. This is thoroughly settled convention —
don't spend review time on it, and don't deviate in new code.

## Module shape

One module, one concern, exporting one class named after it: `ssd_monitor.py` →
`SSDMonitor`, `redis_controller.py` → `RedisController`. `main.py` imports most of the
project's modules directly, with no composition layer in between. **That flatness is
deliberate, not an accident** — it's why the boot sequence in
[`../architecture/cinemate.md`](../architecture/cinemate.md) is legible as one long function.
Don't introduce an intermediate composition layer without deciding that trade-off on purpose.

**The exception worth copying**: the recovery console is standard-library-only by a rule
stated at the top of its own file, with the reason given in place — it exists to survive
failure modes ("cinemate's Python packages are missing or broken", "redis is down") that would
kill anything importing more. When a module has a non-obvious constraint, say so at the top like that.

## Threading — two shapes, not interchangeable

**A long-lived component** subclasses `threading.Thread` and exposes `run()` and `stop()`.
**A one-off task** uses `threading.Thread(target=..., daemon=True)`. Four rules the codebase
earned the hard way:

1. **Give every `join()` a timeout.** Shutdown must not hang on a thread wedged in a
   blocking poll.
2. **If you start it in `run_application()`, stop it in `cleanup()`.** This is the most
   common omission in this codebase's history — see
   [`../architecture/cinemate.md`](../architecture/cinemate.md).
3. **A `daemon=True` thread that dies takes its function with it, and nothing notices** —
   this is exactly how the Redis listener could freeze all live state silently (see
   [`../orientation/the-traps.md`](../orientation/the-traps.md) #1). If a thread is
   load-bearing, expose a liveness check on it.
4. **A retry loop needs a branch for "this can never succeed."** Optional peripherals are
   optional: hardware that has not answered since startup is not fitted and will not start
   answering, so say so once at `INFO` and stop probing, and keep the interval retry for the
   case that can actually recover — something that *was* present and went away. A loop that
   warns every few seconds forever is not diligence; it evicts the startup output that every
   other diagnosis on that machine depends on. Worked example in
   [`../working/repository-and-tooling-traps.md`](../working/repository-and-tooling-traps.md).

## Error handling — one stated principle, three legitimate shapes

The project states its own rule: **fail visible, never silent** (see
[`philosophy.md`](philosophy.md) for how consistently that's actually followed). Three shapes
are distinguishable on sight:

```python
# 1. Best-effort cleanup on something already failing. Say so syntactically.
with contextlib.suppress(Exception):
    ser.close()

# 2. A deliberate fallback. Keep the fallback; do not keep the silence.
try:
    cpu_load = Utils.cpu_load()
except Exception:
    logging.debug("cpu_load unavailable; keeping the last value", exc_info=True)

# 3. Something the operator needs to know about.
except Exception:
    logging.exception("Redis subscriber %s failed; continuing with the rest", name)
```

**Never `except Exception: pass`.** If the silence is intentional, shape 1 says so
syntactically. **Never bare `except:`** — it swallows `KeyboardInterrupt`/`SystemExit` too.
**Use `debug`, not `warning`, on a hot path** (e.g. the GUI redraw loop) — at `warning` you
flood the log you're trying to inform. When dispatching to a list of callbacks, guard each
one individually and continue to the next rather than letting one failure stop the rest.

## Logging

`logging.<level>()` at module scope and named-logger instances both appear in this codebase.
**Match the file you're in** rather than converting a file wholesale as a side effect of an
unrelated change. Never `print()` in library code — it bypasses the file handler and the
in-app log view. `basicConfig` belongs only inside `if __name__ == "__main__":` — calling it
at import time hijacks the root logger for anything that imports the module.

## Configuration

`settings.jsonc`'s comments are part of the product — **never round-trip it through
`json.dumps`**, which silently deletes every comment. Use the project's own
`jsonc_edit.apply_updates()`, which rewrites only the spans whose values actually changed.
Every new settings key needs a `settings.schema.json` entry — `additionalProperties` is
`false` throughout, so an undescribed key is rejected outright. See
[`../orientation/entry-points.md`](../orientation/entry-points.md).

Use `ParameterKey` for Redis keys rather than raw strings where you can — it's convention,
not enforcement (`set_value()` accepts any string), so the convention is all there is.

## Comments — the best thing about this codebase

Load-bearing prose explaining *why*, including experiments that were tried and failed, is the
house style — and there is essentially no commented-out code and no `TODO`/`FIXME` debt.
**Defend this.** Three rules follow from what the good comments do:

1. **State the reason in place, especially for a compromise.** Where the codebase does this,
   the surrounding code is trustworthy; where it skips it, the same construct is usually a
   defect.
2. **A comment is not a check.** Hand-maintained comments that assert two things agree have
   drifted before, more than once. If two things must agree, write a check — see
   [`checks-and-ci.md`](checks-and-ci.md).
3. **Comments rot where `docs/` does not.** The published docs site is actively checked for
   drift; a comment or docstring is not. If a comment records a fact worth keeping accurate
   long-term, consider whether it belongs in `docs/` instead.

## Tests

The test suite is fully portable — no Raspberry Pi required, runs in a couple of seconds.
Keep it that way; a test that needs hardware cannot run in CI, and CI is the only thing that
runs these at all. **Write a test that fails against the unfixed code, and check that it
does** — a test that passes on broken code is worse than no test. See
[`../working/testing.md`](../working/testing.md).

## What this page doesn't cover

- **cinepi-raw's C++.** It has its own formatting config and its own unit-test targets; the
  seam that matters cross-repo is the Redis key contract, not C++ style.
- **Shell.** Already the best-maintained code in the repo — read `cinemate-install.sh`
  directly rather than a style guide; its idempotency is designed and documented in place.
- **Type hints.** Deliberately not adopted wholesale in Python.
- **Formatting.** Not auto-formatted; `.editorconfig` is authoritative for whitespace, and
  long lines are allowed on purpose.
