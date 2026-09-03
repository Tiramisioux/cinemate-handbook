# Review archive — a map, not a copy

This page tells you where to look in `system-review/` (inside the `cinemate` repo, on `dev`)
when a handbook page's citation isn't enough. It doesn't restate the findings — that's the
one thing this handbook is built specifically not to do (see the handbook
[`README.md`](../README.md)).

`system-review/` is a **dated archive with evidence**: an eleven-session audit (228 findings)
plus the remediation and hardware verification that followed. The findings total grew past
the audit's original 193 during that remediation — later batches (B10.1 onward) appended new
entries as fixes surfaced further issues; `FINDINGS.md` is append-only, so the growth is
traceable row by row rather than a renumbering. See
[`../conventions/checks-and-ci.md`](../conventions/checks-and-ci.md)'s
`findings_disposition_check.py` entry for the check that now guards the total. This handbook
is **stable, curated, forward-looking guidance**. When you're reading a handbook page and want
the underlying evidence, come here.

## If you want...

| | Go to |
|---|---|
| A specific finding by number (`F-204`, `F-286`, ...) | `system-review/FINDINGS.md` for the index, or `system-review/findings/F-###.md` if it has its own file |
| The full line-cited source map of cinemate | `system-review/deliverables/CODE-MAP-cinemate.md` |
| The full line-cited source map of cinepi-raw | `system-review/deliverables/CODE-MAP-cinepi-raw.md` |
| The full "where do I change X" table with line numbers | `system-review/deliverables/ENTRY-POINTS.md` |
| The full GUI field-by-field matrix | `system-review/deliverables/GUI-STATE-MODEL.md` |
| The style rules with exact counts and citations | `system-review/deliverables/CINEMATE-STYLE.md` |
| The philosophy verdicts with exact citations | `system-review/deliverables/CINEMATE-PHILOSOPHY.md` |
| The GUI-unification decision in full, with its decision matrix | `system-review/decisions/ADR-001-gui-harmonization.md` |
| Every hardware verification item, worked in full | `system-review/PI-VERIFICATION-QUEUE.md`, `PI-RESULTS-2026-08-24.md`, `PI-RESULTS-2026-08-25.md` |
| The original inventory of every finding, unfiltered | `system-review/deliverables/CENSUS.md` |
| The remediation plan that fixed the highest-priority findings | `system-review/deliverables/REMEDIATION-PLAN.md` |
| The drift-check scripts' own source and README | `system-review/harness/` |
| A single, self-contained "read with no repo open" summary | `system-review/deliverables/SKILL-PAYLOAD.md` — this is what most of `orientation/` and `architecture/` in this handbook were distilled from |

## What's archive-only, and why it wasn't promoted here

`CENSUS.md` (the full unfiltered inventory), `REMEDIATION-PLAN.md` (the prioritized fix plan,
now largely executed), and `ADR-001`'s complete decision matrix are deliberately **not**
reproduced as handbook pages. All three are point-in-time project-management artifacts —
useful for understanding *how the review reached its conclusions* and *what has already been
fixed*, but not something a developer needs on hand to make a new change. The handbook links
to them rather than promoting them; if you're doing historical research on the review itself
rather than making a change to the code, start there instead of here.

## Line numbers in the archive vs. this handbook

The archive's deliverables cite exact `file:line` locations, current as of the snapshot each
session read. This handbook deliberately does not, because those numbers rot the moment a
file's shape changes and nothing checks them — see the handbook
[`README.md`](../README.md)'s closing note. If you need a precise citation for something,
the archive is where to get it; treat it as accurate as of its own stated date, not as
current.
