# Running a hardware verification session

This page is about the *method* for settling a claim on real hardware. For the mechanical
commands (starting a managed session, sending a take command, copying artifacts back), see
the `cinemate-dev` skill — this handbook doesn't duplicate that, since it's about operating
the Pi, not understanding the system.

## Write down the claim before you touch the Pi

Every entry in the review's verification queue had the same three parts, and it's worth
keeping the discipline for any new hardware question:

1. **Belief** — what you think is true, and how confident you are (confirmed-in-code /
   probable / unverified).
2. **Why the Pi is needed** — specifically what a desk reading cannot settle. If you can't
   state this precisely, the claim might be settleable by reading after all — check
   `cinepi_controller.py` for internal locking, for instance, closed one queued item for free,
   with no hardware involved.
3. **An exact, runnable procedure**, including a prediction stated in advance. "Watch what
   happens" is not a procedure; "run X, expect Y, and if you see Z instead that means the
   fallback path is live" is.

**Predict before you look.** A prediction that gets contradicted is a *good* outcome for this
process, not a failed one — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md). The value of
writing the prediction down is that it lets you notice when the mechanism you expected isn't
the mechanism you found, instead of quietly rationalizing the result into matching your guess.

## Prefer a full realistic cycle over a narrow one

Several queued items were first run in a narrow window (idle-only, a short trace, a synthetic
single command) and came back `INCONCLUSIVE` — not because the belief was wrong, but because
the test window didn't include the condition that would actually trigger it. A boot → record →
resolution-change → shutdown cycle surfaced live traffic on keys that a 45-second idle trace
completely missed. If a first pass comes back inconclusive, ask whether the window was
actually wide enough before concluding the claim itself is unsettled.

## Record what you did, not just the verdict

For each session: what ran (the actual commands, not a paraphrase), what was observed (the
actual output, not an interpretation of it), the prediction, and the verdict —
**CONFIRMED**, **CONTRADICTED**, or **INCONCLUSIVE**, plus a one-line reason if inconclusive.
Distinguish a structural finding (settled by reading, no hardware) from a consequence finding
(needs hardware to observe) — they can have different confidence levels for the same overall
question, as happened with the un-serialised-control-path finding: the structure was settled
at a desk, the actual starving behaviour needed a live pot.

**Real device modifications made along the way are part of the record, not incidental.**
Installing a package into a live venv to unblock a test, or flipping a config flag temporarily
to reach an otherwise-unreachable code path, changes the system under test — say so
explicitly, and revert what should be reverted afterward.

## When a desk diagnosis turns out to need hardware correction

This will happen — see
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) for three real
examples where a plausible desk diagnosis was confirmed at the symptom level but wrong about
the mechanism. When it does: correct the finding's evidence line to point at the actual
mechanism, don't just append a caveat. The next reader should be able to trust the finding
without re-deriving your correction.

## Further reading

- `system-review/PI-VERIFICATION-QUEUE.md` — seventeen worked examples of this method, including several that needed more than one pass.
- The `cinemate-dev` skill — the deterministic session mechanics (start/wait/rec/copy/stop) this page's method runs on top of.
