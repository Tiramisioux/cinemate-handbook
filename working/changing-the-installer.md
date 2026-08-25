# Changing the installer

`cinemate-install.sh` is a long, idempotent, step-numbered script. A few hard-won rules
before you touch it:

## Never round-trip `settings.jsonc` through `json.dumps`/`json.loads` unconditionally

This has been a real, shipped bug: a step that patches a couple of hotspot/HDMI values in
`settings.jsonc` used to round-trip the whole file through Python's JSON module on
**every** install, destroying every one of its ~70 comment lines even when nothing actually
needed to change — comments are part of the product here (see
[`../conventions/style.md`](../conventions/style.md)). The fix that shipped: skip the write
entirely when the installer's defaults already match what's on disk (the common case), and
only fall back to a rewrite — with a warning and a backup — when a value is genuinely being
customized. If you're adding a new installer step that touches `settings.jsonc` or
`config.txt`, follow that shape: check-then-skip before write-with-backup, never a silent
unconditional rewrite.

## Prefer absolute paths inside the installed tree

A relative path written into `settings.jsonc` by the installer (a tuning-file override) used
to work only because the systemd unit happened to pin a working directory — silently
dependent on something outside the file itself. Match whatever convention the *other*,
non-buggy paths in the same settings block already use, which in this case was "always
absolute."

## `sudo -v` is not safe to assume works

`bootstrap_sudo()`'s `sudo -v` hung forever, with no error and no timeout, on stock Raspberry
Pi OS — a NOPASSWD sudoers rule for the `pi` user doesn't make `sudo -v` specifically
passwordless, even though a plain `sudo <cmd>` is. Use `sudo -n true` (non-interactive,
fails fast) instead of `sudo -v` anywhere the installer needs to check for sudo access without
blocking.

## Pin package downloads against a pool that actually keeps old versions

A specific `raspi-firmware` version pinned against the Raspberry Pi apt "untested" pool 404'd,
because that pool only ever retains the single newest upload — the exact pinned version had
already been promoted to "main" and removed from "untested". If you pin a package version,
pin it against a pool that retains history, or accept that the pin will need bumping whenever
upstream rotates it out.

## Dependencies: two files, read by one script

A dependency needs to land in `requirements.txt` (if it imports anywhere) and/or
`requirements-hardware.txt` (if it needs a Pi). The installer reads both — don't add a
dependency as a literal `pip install` line inside `cinemate-install.sh` itself; that's exactly
the kind of duplicated fact this codebase has drifted on before (see
[`../conventions/philosophy.md`](../conventions/philosophy.md)'s "duplicated truth"
principle).

## Adding a systemd service

Add `services/<name>/` with its own `.service` file and a Makefile implementing
`install`/`uninstall`, then add it to `services/Makefile`'s service list, the installer's
service step, and `docs/system-services.md` / the services section of
`docs/installation-steps.md`. **Nothing in CI catches a missed doc update here** — the
install docs have historically covered four of five existing services, missing the recovery
console entirely. Double-check by hand.

## Test on a genuinely blank card before trusting a clean-install claim

Several real installer bugs (the three above) were only found by testing on an actual blank
Raspberry Pi OS image — an already-running production unit doesn't exercise first-boot
behaviour, sudoers defaults, or package resolution the same way. See
[`../lessons/what-the-pi-taught-us.md`](../lessons/what-the-pi-taught-us.md) for why a clean
install is one of the categories that only hardware can settle.

## Further reading

- [`hardware-session.md`](hardware-session.md) — how to run a deterministic verification session, including a clean-install test.
- [`../architecture/cinemate.md`](../architecture/cinemate.md) — what the installer actually launches into (`run_application()`'s boot sequence).
