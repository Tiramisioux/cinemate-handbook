# Checks and CI

## What CI is, in two sentences

CI (continuous integration) means a set of automated checks run on GitHub's own machines
every time a pull request is opened or updated, without anyone having to remember to run them
by hand. If a check fails, that's visible on the PR before it merges — nobody has to hold the
rule in their head.

## The five cinemate jobs

Defined in `.github/workflows/checks.yml`, all on plain `ubuntu-latest`, none needing a Pi:

| Job | What it runs | What it actually protects |
|---|---|---|
| `pytest` | The full `_test/` suite (~900 tests) | The Python behaviour the tests cover — portable by design, no hardware, no Redis server, no GPIO. See [`testing.md`](../working/testing.md). |
| `ruff` | `ruff check src/` | Style, unused imports, and — critically — bare `except:` and silent `except: pass`, which enforces the "fail visible" principle mechanically (see [`philosophy.md`](philosophy.md)). |
| `shellcheck` | Every `.sh` file in the repo | The installer and helper scripts stay shell-correct; this is the best-maintained corner of the codebase and this job is why. |
| `mkdocs` (in `docs.yml`) | `mkdocs build --clean` | The published documentation site still builds — every PR, not just pushes to `main`/`dev`. Publishing itself is gated to `main` only. |
| **contract drift** | Six custom stdlib-only scripts under `tools/` | The cross-file and cross-repo facts that keep silently disagreeing — see below. This job is this review's real, lasting legacy. |

## The contract-drift job, in detail

Six checks, each aimed at a specific place this codebase has drifted before:

- **`docs_drift_check.py --strict`** — docs match the code (settings keys, controller
  methods documented, etc.).
- **`findings_disposition_check.py`** — every row in `system-review/FINDINGS.md` carries one
  of five dispositions (`fixed`/`guarded`/`accepted`/`superseded`/`strength`). B10.1 gave all
  228 findings a disposition; this is what stops a new one being appended without one, or with
  a typo'd value.
- **`design_token_diff.py --strict`** — the HDMI GUI's colour constants and the web
  template's CSS custom properties haven't diverged. Gated at zero; nothing has drifted yet.
- **`gui_field_extract.py --max-unresolved 0`** — every action the settings editor (and the
  GPIO/rotary config surface) offers actually resolves to a real method on the controller.
  Gated at **zero**: this is the check that would have caught `set_log` shipping as a button
  that silently did nothing (see [`../orientation/the-traps.md`](../orientation/the-traps.md)
  #3).
- **`link_frequency_drift_check.py --strict`** — the CSI-2 link-frequency values (hz options
  the settings editor offers per sensor) live only in `resources/sensors.json`; this fails if
  the settings-editor template hardcodes one of those numbers instead of reading it from the
  database. Gated at zero.
- **`redis_key_diff.py --max-unreferenced 12`** — needs both repositories checked out,
  because the key contract spans them (see
  [`../architecture/redis-contract.md`](../architecture/redis-contract.md)). This one is a
  **ratchet, not a gate**: 8 keys cinepi-raw touches currently have no reference in cinemate
  (the ceiling itself, 12, hasn't been tightened down to match — see below), and the check
  exists to stop a thirteenth appearing unnoticed, not to fail until those are triaged.

## A ratchet is not a gate

`--max-unresolved 0` and `--max-unreferenced 12` look similar but mean different things. A
**gate** at zero says "this must already be perfect, and stay perfect." A **ratchet** at a
nonzero number says "this is where reality currently sits — don't make it worse, and tighten
the number as reality improves." The `gui_field_extract` check used to be a ratchet too, sitting
above zero, until the underlying issue it tracked was fixed — at which point the number was
tightened to zero, permanently converting it into a gate.

**Raising a ratchet's number to make a job pass is never the fix.** If a change adds a
thirteenth unreferenced Redis key, the fix is to reference it, remove it, or document why it's
intentionally one-sided — not to bump the ratchet to 13. The workflow file says this in a
comment at the check itself, precisely so nobody "fixes" the red job the easy way.

## cinepi-raw's CI

cinepi-raw had no CI at all until unit tests for its pure-C++ helpers (DNG pixel packing,
the phase-lock core, the CCMP/log-LUT math) were written and wired up. Because the project's
own `meson.build` requires libcamera unconditionally at configure time, running `meson test`
on a plain GitHub runner isn't possible without building libcamera from source first — too
slow to be worth it for tests that don't need libcamera at all. Instead, each pure test
target is compiled and run directly with `g++`, one project header plus the standard library,
bypassing `meson setup` entirely.

To run those same tests by hand, `meson test -C /home/pi/cinepi-raw/build <name>
--print-errorlogs` on the Pi remains the project's own, more thorough entry point — see
[`testing.md`](../working/testing.md) and the skill's `references/unit-testing.md` for the
exact build/test loop.

## How to add a check

1. Identify the fact that two places must agree on (a doc and the code, two hand-maintained
   catalogues, a key both repos reference).
2. Write a small, standard-library-only script under `tools/` (cinemate) that verifies it and
   exits non-zero on disagreement. Keep it dependency-free — it has to run in CI without a
   fragile install step.
3. Decide gate or ratchet. If the codebase is already clean, gate at zero. If there's existing
   debt, ratchet at the current count and say so in a comment, the way `redis_key_diff.py` does.
4. Wire it into `.github/workflows/checks.yml` under the `drift` job (or its own job, if it
   needs something the others don't — like cinepi-raw's checkout).
5. Tighten ratchets over time as the underlying debt is paid down — see the `gui_field_extract`
   history above for the shape this takes.

**The standard this review set: a check beats a comment, because a comment cannot fail.**
If you're tempted to add a comment saying "keep X and Y in sync", write a check instead —
see [`philosophy.md`](philosophy.md)'s "duplicated truth" principle.

## Two ways a check quietly stops protecting you

Both of these apply to anything that scrapes a file for a set of names — the `tools/` drift
scripts and the text-reading guards in `_test/` alike.

**A check that finds nothing must fail, not pass.** A guard that extracts a set from a file
and compares it against another set passes trivially once the extraction stops matching:
change the markup shape and the check is comparing two empty sets, green forever. Assert a
plausible floor on what the extractor found — the settings editor's page-tab guard asserts at
least five tabs were located before it compares anything, precisely so a markup change goes
red instead of silently checking nothing.

**When a text-scraping check fails, suspect the extractor before the code.** A tab-name
pattern of `[a-z]+` silently dropped the page named `i2c` because of the digit — and it did
not fail as "the extractor is wrong", it failed as a set mismatch blaming a missing landing
section, pointing at a file that was fine. A set-difference assertion cannot tell you whether
the set is wrong or the source is, so make the extraction pattern the first thing you check
and write the reason next to it. The concrete guards this came from are in
[`../working/repository-and-tooling-traps.md`](../working/repository-and-tooling-traps.md);
note that the corrected pattern now lives in two test files held together by a comment — the
weaker half of the rule above, and still uncovered.

## Further reading

- `.github/workflows/checks.yml`, `.github/workflows/docs.yml` — the actual job definitions.
- `system-review/harness/` — the drift-check scripts' own README and source.
- [`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) — why these checks can only ever settle claims about the *code*, never about the running *machine*.
