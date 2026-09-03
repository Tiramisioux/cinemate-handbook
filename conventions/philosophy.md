# Philosophy — what this project believes, tested against its own code

The system review tested a set of candidate principles — drawn from the codebase's own
comments and structure — against the actual source. The finding that matters most:

> **This project knows what it believes, states it in prose, and enforces it nowhere.**
> Where a principle is violated, the violation is almost never ignorance — the correct
> implementation usually exists a few hundred lines away, in the same repository.

Use this page to understand *why* the codebase is shaped the way it is, and to recognise when
you're about to repeat a violation the project has already fixed once elsewhere.

## The principles

**Redis is the single source of live state — between processes, not within one.** True as
topology and aspiration; false as a strict invariant. `get_value()` reads a cache, not Redis
(see [`../orientation/the-traps.md`](../orientation/the-traps.md) #1); a handful of call
sites hold their own separate Redis clients; the key registry is convention, not enforcement;
and a real fraction of the HDMI GUI's state never reaches Redis at all. Design new features
against the *practised* version of this principle, not the aspirational one.

**The Pi is the runtime truth.** Confirmed, and the project genuinely lives it — comments
record falsified experiments rather than hiding them, and code that hasn't been hardware
tested says so about itself. See
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) for what this
means in practice for how confident you should be in a desk diagnosis.

**Fail visible, never silent.** Stated explicitly in the codebase — and the single most
violated principle in the system. The sharpened form worth adopting verbatim: **the operator
must never be shown a plausible wrong number.** The worst confirmed instance was the Redis
listener thread dying silently while every surface kept rendering frozen-but-plausible
values — fixed by wrapping the dispatch loop in `try`/`except`, copying a pattern that
already existed correctly elsewhere in the same file. Before you ship a new failure path, ask
whether it could produce a value that looks fine but isn't.

**Hardware facts live in one data file, read and translated by one repo.** `sensors.json` is
a genuine single source, but only cinemate reads it — cinepi-raw has zero references to it.
Hardware facts reach cinepi-raw as Redis keys and command-line arguments that cinemate
translates. The actual shared contract between the repos is the Redis keys (see
[`../architecture/redis-contract.md`](../architecture/redis-contract.md)), not the sensor
data file.

**One process owns the display, enforced by the hardware itself.** DRM master is exclusive
per GPU. Ownership binds at process start and cannot be rebound — this is *why* HDMI
hot-plug restarts capture, not an accident. See
[`../orientation/the-traps.md`](../orientation/the-traps.md) #4.

**Comments record the why, including dead ends — and that's the best thing about this
codebase.** Effectively zero `TODO`/`FIXME` debt; the comments that exist justify decisions
that would otherwise look wrong. The boundary: **comments that assert a fact about *other*
code rot**, because nothing checks them, while the published docs site is actively checked.
A comment is not a substitute for a check — see [`checks-and-ci.md`](checks-and-ci.md).

**The camera must survive its own software.** The project's best work: the recovery console
(standard-library-only by a stated rule, with the reason given in place), standby-storage
promotion, and the Wi-Fi hotspot credential ladder are all independent, real mechanisms for
this. The generalisable shape: **degrade in ladders whose last rung still produces a usable
answer**, not an error.

**Config is declarative and user-editable, and its comments are part of the product.**
`settings.jsonc`'s comments carry real explanatory content. The web settings editor used to
round-trip the file through `json.dumps`, silently destroying every comment on save, with no
backup — a real, once-shipped violation of this. It's fixed now: `src/module/jsonc_edit.py`
locates each changed value's exact span in the original text and rewrites only that span,
so comments, key order and formatting survive untouched; the settings editor backs up the
file first, then writes through this (`apply_updates()`), falling back to a full `json.dumps`
rewrite — and telling the operator so — only when the change is structural (a key added or
removed, an array resized). When you're about to write configuration back to disk, copy
`apply_updates()`, not a bare `json.dumps()`.

## Principles the review surfaced that weren't stated anywhere first

**Degrade in ladders whose last rung still answers.** Generalised from the survival
mechanisms above — numbered fallbacks where the final one still works, not an error.

**State the reason in place, especially for a compromise.** The project's best comments
justify a decision that would otherwise look wrong, rather than describing *what* the code
does (which the code already shows).

**Duplicated truth must be deleted, or carry a named reason *and* a check. A comment is not a
check.** This is the principle the project most needs and has historically had least: several
instances of one fact stated in two places, kept in sync by hand, have drifted — including
comments that specifically exist to flag the duplication, some of which were themselves
wrong. This finding is the reason this handbook exists in the repo instead of duplicated into
a skill — see the handbook [`README.md`](../README.md).

**Route, don't replicate.** The project's one clearly successful de-duplication: CLI, serial,
and web control flow all now go through one dispatch path
(`POST /api/v1/cmd` and the same command table), with the reason recorded in code. It has
held. Compare the settings-editor's action catalogue, maintained by hand in multiple copies,
which was corrected once and drifted again. **When this project routes, it wins. When it
copies and comments, it loses.** Prefer routing over duplication-with-a-comment every time
you have the choice.

## Further reading

- `system-review/deliverables/CINEMATE-PHILOSOPHY.md` — the full verdict-by-verdict analysis this page distills, with citations.
- [`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) — how "the Pi is the runtime truth" plays out concretely.
