#!/usr/bin/env python3
"""
plateau_probe.py -- read the ClearHDR merge plateau off a take, one comparable number per run.

The merge-clamp model has four free hypotheses (does the plateau track EXP_GAIN? does EXP_BK
enter it? is the fall with analogue gain a hard 29.1 dB cap or a continuous loss? does the
sensor clip or wrap?). Each is settled by changing one register and re-reading the plateau.
This prints the plateau the same way every time so the runs are comparable.

WHAT IT PRINTS, per take:
  - per-CFA p1 / p50 / p99 of the blown region, in raw code and as a fraction of full scale
    above black (16-bit: black 3200, FS 65535; 12-bit: decoded through the CCMP curve first)
  - the plateau floor and its width (the 1st and 99th percentile of converged quads' max)
  - the convergence ratio 2nd/max, which is what says "this is the clamp, not a bright subject"
  - the count of converged quads, so a run with nothing blown in frame reports 0 rather than
    a number derived from noise

HOW THE BLOWN REGION IS FOUND: quads whose top two channels agree (2nd/max >= --ratio) and
which sit above --level of full scale, i.e. the same test the preview correction uses. Pass
--roi to restrict to a hand-picked box instead.

USAGE
  python3 plateau_probe.py TAKE_OR_DNG [--frame N] [--roi x0,y0,x1,y1]
                           [--binning 1|4]        # 12-bit only: which CCMP table to decode with
                           [--ratio 0.98] [--level 0.40]
                           [--label "run A code 71 adder +6"]     # goes in the output line
  python3 plateau_probe.py --selftest              # synthetic plateau, no DNG needed

  Sweep example (one line per run, paste into the hardware log):
    for t in ~/takes/runA_code*; do python3 plateau_probe.py "$t" --label "$(basename $t)"; done

READ THE GAIN OFF THE JOURNAL, NOT THE ISO. Every plateau number in this project's history that
lacks a recorded analogue gain code is the reason the model still has free hypotheses. The
driver prints `ANALOG_GAIN=` on every write; capture it with the take and pass it in --label.

Read-only: never writes next to the take. Needs rawpy + numpy.
"""
import argparse
import glob
import os
import sys

import numpy as np

# The CCMP compander, from cinepi-raw cinepi/ccmp_lut.hpp (kT1Effective). 12-bit takes store
# companded codes; the plateau only means something in the delivered-linear domain, so decode
# first. rawpy applies the DNG's own LinearizationTable when one is attached -- this is the
# fallback for a file written without it, and the cross-check when one is present.
CCMP = {1.0: dict(T1=500.3389, T2=11500.0, s1=1 / 64, s2=1 / 16, P=200.0, b=1.0),
        4.0: dict(T1=500.9431, T2=11500.0, s1=1 / 64, s2=1 / 16, P=200.0, b=4.0)}


def ccmp_decode(code, p):
    """stored 12-bit code -> L (linear above black, 16-bit ClearHDR LSB)."""
    y = p["b"] * (np.asarray(code, dtype=np.float64) - p["P"])
    C2 = p["T1"] + (p["T2"] - p["T1"]) * p["s1"]
    out = np.where(y <= p["T1"], y,
          np.where(y <= C2, p["T1"] + (y - p["T1"]) / p["s1"],
                            p["T2"] + (y - C2) / p["s2"]))
    return out / p["b"]


def load(path):
    import rawpy
    with rawpy.imread(path) as raw:
        img = raw.raw_image_visible.astype(np.float64)
        black = float(np.mean(raw.black_level_per_channel))
        white = float(raw.white_level)
        pattern = raw.raw_pattern.copy()
        desc = raw.color_desc.decode() if isinstance(raw.color_desc, bytes) else str(raw.color_desc)
        linearized = raw.raw_image_visible.max() > 4095
    return img, black, white, pattern, desc, linearized


def split_cfa(img, pattern, desc):
    """-> dict channel -> array of one sample per quad (G is the mean of the two greens)."""
    h, w = img.shape
    h -= h % 2
    w -= w % 2
    img = img[:h, :w]
    sites = {(0, 0): img[0::2, 0::2], (0, 1): img[0::2, 1::2],
             (1, 0): img[1::2, 0::2], (1, 1): img[1::2, 1::2]}
    ch = {}
    for (y, x), a in sites.items():
        ch.setdefault(desc[pattern[y, x]], []).append(a)
    return {"R": ch["R"][0], "G": 0.5 * (ch["G"][0] + ch["G"][1]), "B": ch["B"][0],
            "G1": ch["G"][0], "G2": ch["G"][1]}


def analyse(R, G, B, black, span, ratio_gate, level_gate, label, note=""):
    r = np.clip((R - black) / span, 0, None)
    g = np.clip((G - black) / span, 0, None)
    b = np.clip((B - black) / span, 0, None)
    st = np.sort(np.stack([r, g, b], axis=-1), axis=-1)
    mx, second = st[..., 2], st[..., 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        conv = np.where(mx > 0, second / mx, 0.0)
    sel = (conv >= ratio_gate) & (mx >= level_gate)
    n = int(sel.sum())
    print(f"\n=== {label}{(' ' + note) if note else ''}")
    print(f"    converged quads: {n} of {mx.size} ({100.0 * n / mx.size:.2f}% of frame)"
          f"   gates: 2nd/max >= {ratio_gate}, level >= {level_gate}")
    if n < 64:
        print("    NO PLATEAU: fewer than 64 converged quads. Nothing in this frame is clamped,")
        print("    or the gates are wrong for it. Do not read a plateau off this take.")
        return None
    pl = mx[sel]
    p1, p50, p99 = (float(np.percentile(pl, q)) for q in (1, 50, 99))
    print(f"    plateau (fraction of full scale above black): p1 {p1:.4f}  p50 {p50:.4f}  p99 {p99:.4f}"
          f"   width {100 * (p99 - p1):.2f}%")
    print(f"    plateau in code:  p1 {black + p1 * span:8.0f}  p50 {black + p50 * span:8.0f}"
          f"  p99 {black + p99 * span:8.0f}   (black {black:.0f}, span {span:.0f})")
    print(f"    convergence on the plateau: 2nd/max p5 {np.percentile(conv[sel], 5):.4f}"
          f"  p50 {np.percentile(conv[sel], 50):.4f}")
    for name, arr in (("R", r), ("G", g), ("B", b)):
        v = arr[sel]
        print(f"      {name}: p1 {np.percentile(v, 1):.4f}  p50 {np.percentile(v, 50):.4f}"
              f"  p99 {np.percentile(v, 99):.4f}")
    frac_at_top = float(np.mean(pl > 0.995))
    if frac_at_top > 0.5:
        print(f"    WARNING: {100 * frac_at_top:.0f}% of the plateau sits at full scale. The merged")
        print("    output is clipping the container, so this reads the container, not the merge.")
    return dict(p1=p1, p50=p50, p99=p99, n=n)


def selftest():
    """A synthetic 16-bit frame: a blown core pinned on one code, a yellow surround, noise."""
    rng = np.random.default_rng(7)
    h, w = 1100, 1920
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(yy - h / 2, xx - w / 2) / (0.22 * w)
    black, white = 3200.0, 65535.0
    span = white - black
    plateau_code = 54100.0
    core = d < 1.0
    lvl = 0.45 * np.exp(-d * d)
    noise = lambda: 1 + rng.normal(0, 0.004, (h, w))
    R = np.where(core, plateau_code, black + lvl * span * noise())
    G = np.where(core, plateau_code, black + lvl * span * noise())
    B = np.where(core, plateau_code, black + 0.35 * lvl * span * noise())
    res = analyse(R, G, B, black, span, 0.98, 0.40, "selftest: synthetic plateau at code 54100")
    ok = res is not None and abs((black + res["p50"] * span) - plateau_code) < 200
    print(f"\n    selftest {'PASSED' if ok else 'FAILED'}: recovered "
          f"{black + res['p50'] * span:.0f} against 54100" if res else "    selftest FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--frame", type=int, default=20,
                    help="frame index in a take directory (default 20: after the sensor settles)")
    ap.add_argument("--roi", type=str, default=None, help="x0,y0,x1,y1 in raw pixels")
    ap.add_argument("--binning", type=float, default=None,
                    help="12-bit only: 1 or 4, to decode the CCMP curve when the file carries no table")
    ap.add_argument("--ratio", type=float, default=0.98)
    ap.add_argument("--level", type=float, default=0.40)
    ap.add_argument("--label", type=str, default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.path:
        ap.error("need a take directory or a .dng, or --selftest")
    path = a.path
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.dng")))
        if not files:
            sys.exit("no DNGs in " + path)
        path = files[min(a.frame, len(files) - 1)]
    img, black, white, pattern, desc, linearized = load(path)
    note = f"[{os.path.basename(path)} {img.shape[1]}x{img.shape[0]} cfa {desc}]"
    if a.roi:
        x0, y0, x1, y1 = (int(v) for v in a.roi.split(","))
        img = img[y0:y1, x0:x1]
    ch = split_cfa(img, pattern, desc)
    R, G, B = ch["R"], ch["G"], ch["B"]
    if a.binning is not None and not linearized:
        p = CCMP.get(a.binning)
        if p is None:
            sys.exit("--binning must be 1 or 4")
        R, G, B = (ccmp_decode(x, p) for x in (R, G, B))
        black, white = 0.0, 63265.0 if a.binning == 1 else 62704.0
        note += f" [CCMP-decoded b={a.binning:.0f}]"
    elif linearized:
        note += " [rawpy applied the file's LinearizationTable]"
    analyse(R, G, B, black, white - black, a.ratio, a.level,
            a.label or os.path.basename(path), note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
