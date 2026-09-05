# What the Pi taught us

This page is about *how to reason about this system*, not a list of what happened during one
review. The headline number: of the sixteen hardware predictions originally written from
source during the system review, **five were contradicted** — and of three desk diagnoses
handed to the Pi later for a fix, **two were wrong about the mechanism**. Every one of those
was written by someone who had read the code carefully. That is the lesson: reading carefully
is necessary and not sufficient, and the value of this page is knowing *which kinds* of claim
that applies to.

(The verification queue has since grown to seventeen entries — PI-017 was added 2026-08-26,
reopening a finding on a later correction rather than belonging to the original sixteen-item
pass, and it's still `unverified`. It sits outside the sixteen/five count above; see
[`hardware-log.md`](hardware-log.md).)

A contradicted prediction is a good outcome. The entire value of writing a prediction down
before looking is that it lets you notice, later, exactly where your model of the system
broke — instead of quietly rationalizing whatever you found into having been expected all
along. See [`../working/hardware-session.md`](../working/hardware-session.md) for the method
this page's cases came from.

## The working rule

**A claim about what the code says can be settled by reading. A claim about what the machine
does cannot.** Structure — control flow, what calls what, whether a lock is held — is
knowable at a desk. Environment, permissions, timing, and hardware state are not, no matter
how carefully you read.

## Cases worth knowing, one lesson each

### Static analysis proves absence of *references*, never absence of *behaviour*

Source reading found eleven Redis keys that cinepi-raw touches with no reference anywhere in
cinemate — a plausible "dead code" list. On hardware, **all eleven were live.** Eight turned
out to be an undocumented launch-config contract: cinepi-raw reads them from Redis once per
process (re)start, with real values that were seeded long before the observing session and
persisted only in Redis's own snapshot — nothing in either repo's tracked source sets them.
The other two are per-frame phase-lock telemetry, written on the order of once per frame,
with zero reader. "Nothing in the source references this key" and "this key is dead" are
different claims, and only a live trace distinguishes them.

### `apt` supplies Python packages without a `pip` entry

A finding predicted that disabling an installer flag would leave a required GPIO package
missing, crashing the app with `ModuleNotFoundError` before any of the startup-failure display
machinery could even run. On a real install: the package arrived anyway, as an `apt`
dependency of an unrelated package the flag doesn't control. The predicted crash cannot
happen on this OS generation. The review's own writeup had already named this exact
possibility as a reason hardware was needed — and it turned out to be exactly what happened.
Any "package X is unused, or X is required" claim about the Python dependency surface is
static until it's tested against a real, freshly-imaged install — not an already-running
unit, which has already resolved its dependencies once and won't tell you what a fresh one
would do.

### A tool exiting `0` does not mean it answered

A storage-detection helper called `blkid -c /dev/null` as an unprivileged user. On this
device's `blkid` version, that returns **empty output with exit code 0** instead of raising a
permission error — and the fallback chain treated any successful exit as final, so it never
reached the cache-backed query one step further that actually had the answer. A desk
diagnosis of the same symptom guessed the fault was a 1-second timeout firing and being
swallowed; instrumented timing across ten reproduced failures showed every call completing in
milliseconds — nowhere near the timeout. The real mechanism was the silently-successful empty
result. A second detail neither desk guess had available: the affected NVMe volume has no
partition table at all, so its label lives directly on the whole-disk device node — a fact no
amount of reading the code could have supplied, because it's a property of one specific piece
of hardware.

### The plausible mechanism is not always the actual one

A restart hang looked exactly like a well-known systemd deadlock pattern: a `Conflicts=`
dependency without `--no-block` on the failing line. Debug tracing confirmed the script did
hang at that exact line — but not on a `--no-block` deadlock. It hung on an **interactive
PolicyKit authentication prompt**, in a shutdown-hook context that can never answer one.
`sudo -n` fixed it; `--no-block` (already present elsewhere in the same script, for an
unrelated reason) would not have. A second race the same diagnosis predicted turned out to be
real, but it came from a completely different code path — a second, independent call
elsewhere in the Python layer racing the same underlying system constraint from a direction
neither original guess had considered. Getting the symptom right and the fix right is not the
same as getting the mechanism right, and the mechanism is what determines whether a *related*
symptom will also be fixed.

### Measure before you argue from resources

An architecture decision rejected two design options partly on the grounds that the
development board was memory-constrained. A hardware measurement later found the board's real
total memory was roughly double what had been assumed, and available memory at the sensor's
most demanding capture mode never dropped anywhere near the threshold the argument relied on.
The decision itself survived — on its other, independent grounds — but one of its two legs
was gone, and the record now says so explicitly rather than quietly keeping the stale
argument. If a conclusion rests partly on a resource figure, measure that figure on the actual
unit before trusting the conclusion; "it's a small board" is not a substitute for `free -m`.

### Reconstructed numbers are not measured numbers

A handoff document rebuilt a sensor's supported-mode table from notes taken during an earlier
session, for use in a fix that needed exact figures. It was close, but it was a
reconstruction, not a measurement — and it was replaced with the real table pulled directly
from the capture tool's own mode-listing output before the fix was verified. The
reconstruction turned out to match closely in this case; treat that as luck, not as
justification for skipping the real query next time a fix depends on exact hardware figures.

### A default is a claim, not a fact — verify the value the hardware actually receives

A sensor feature shipped with the wrong default for one control. The symptom looked like a
hardware-state defect, and it drew a week of forensics: register sweeps over raw I2C during
failing captures, per-frame decode of pulled frames, cold-boot series, light-level
experiments, a model of the sensor's internal state. Those measured real things. None of them
looked at the default. It was stated in six places across the driver, the app's settings, the
Redis seed, and the docs — and exactly one of the six was ever checked. Six copies of a value
are not six confirmations. They are one claim, restated, and the review's own rule
(**duplicated truth stops agreeing**) says they will drift.

The rule this leaves: before modelling *why* the device misbehaves, walk the value from where
it is declared to where it is consumed, and confirm at each hop that it is still what you
think it is. The copy that decides behaviour is the one the silicon receives, which is none of
the written ones — it is whatever the last writer in the chain put there. If you cannot read
it back at the far end, say so explicitly and treat every conclusion downstream of it as
resting on an unverified premise. That sentence is cheap at the start of an investigation and
very expensive at the end of one.

### A log line is only evidence if one build could have printed it

Playback reported no embedded thumbnail on every take. The camera's log said
`DNG writer: raw-only frames; embedded lores thumbnail disabled`, and that line was read as
proof that a mode variable had been assigned too late — a subtle ordering race, duly fixed. It
was **the same string in both candidate builds**: unconditional in the branch that has no
thumbnail code, and the `mode == 0` arm of a new `if` in the branch that does. It could not
distinguish "the setting read 0" from "this binary predates the feature", which was the actual
open question that evening. Before treating a message as evidence for a mechanism, check how
many code paths and how many builds can emit that exact string. If more than one can, it
narrows nothing. Two habits follow: log values, not conclusions — `thumbnail=0` would have been
unambiguous where `disabled` was not — and when a feature arrives by merge, establish that the
running binary contains it before diagnosing why it misbehaves.

### The file is the witness, not the control that was supposed to configure it

The same session's diagnosis started from the right place. The playback API's per-clip `source`
field is derived by reading each DNG for a chained second IFD — it never consults Redis — so it
reports what was *written*, take by take, and it split the takes cleanly on the day the camera
changed branches. The Redis key looked correct throughout and pointed at nothing, because a
control's value tells you what was requested, not what happened. When a pipeline has an
artifact, interrogate the artifact: it is the only participant with no opinion.

### A fallback whose failure mode is "yes" is not a fallback

Hat detection probed the hat's own I²C address and, when that did not answer, fell back to the
existence of a sysfs node bound on every Pi 5. The fallback could return true and could never
return false, so a plain NVMe was labelled CFexpress on hardware that had no hat within reach.
The tell is structural and readable at a desk: a presence test that cannot produce a negative on
the hardware you ship on is an unconditional `True`. A second component had probed the same
address correctly, with no fallback, since the day it was written — the two had simply never been
asked the same question out loud. And the fix immediately exposed a second bug downstream, a
status box that had only ever fitted because the wrong label happened to be the right length.

### What held, and why it held

Not every prediction broke. A finding that one particular subscriber, if it ever raised an
exception, would silently freeze every downstream display — GUI, web, HTTP API — was
predicted from source and then **confirmed decisively** on hardware, exactly as described: a
forced fault froze the cache-backed API and the live event stream permanently and silently on
the very first update after the fault, with nothing else in the process appearing unhealthy.
This is the line the working rule draws: this was a claim about *code structure* — a
synchronous, unguarded loop over subscribers, no exception boundary, a daemon thread with no
supervisor — not about the runtime environment. Structure held because it was actually
knowable at a desk. The fix (guarding that loop, mirroring a pattern that already existed
correctly a few hundred lines away in the other repo) was later hardware re-verified against
the exact same fault injection and confirmed to close it.

## Recording new experiences here

Every hardware session — a deterministic verification run, an ad hoc debugging session, or a
finding the operator confirms as verified on real hardware — should add to this record, not
just live in a chat transcript. See [`hardware-log.md`](hardware-log.md) for the running,
dated log this page's cases were originally drawn from, and
[`../working/hardware-session.md`](../working/hardware-session.md) for the method (belief →
why the Pi is needed → exact procedure → prediction → verdict) that keeps an entry useful to
someone who wasn't there.

## Further reading

- [`hardware-log.md`](hardware-log.md) — the ongoing, dated log of hardware findings this page distills the durable lessons from.
- `system-review/PI-VERIFICATION-QUEUE.md`, `PI-RESULTS-2026-08-24.md`, `PI-RESULTS-2026-08-25.md` (in the `cinemate` repo) — the original sixteen full worked cases and the fix-round verification behind this page, plus the seventeenth (PI-017) added afterward — see [`hardware-log.md`](hardware-log.md).
