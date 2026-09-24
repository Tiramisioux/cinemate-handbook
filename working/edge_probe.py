#!/usr/bin/env python3
"""
edge_probe.py -- what the ragged 12-bit boundary pixels actually are.

Reads one CinemaDNG frame with rawpy (its own linearisation), applies the
shipped convergence rule per Bayer quad, finds the transition band between the
neutralised core and the yellow surround, and answers three questions with
numbers rather than reasoning:

  Q1  ties:      in the band, how often are the top two channels on the IDENTICAL
                 linearised value (== identical stored code), vs merely close?
  Q2  separability: distribution of 2nd/max for core / band / surround (p5, p50,
                 p95) -- do the yellow surround and the clamp overlap in ratio?
  Q3  treatment: for the shipped rule (per-quad want, 2x2 min) and for candidate
                 feathering variants, count holes (unfired 2x2 blocks with >=6 of
                 8 fired neighbours), islands (fired blocks with <=1 fired
                 neighbour), and how much of the yellow surround each variant
                 touches (the cost of widening the ramp).

Usage:
  python3 edge_probe.py <take_dir_or_dng> [--frame 44] [--ratio-lo 0.98 --ratio-hi 0.997
                        --level-lo 0.40 --level-hi 0.50] [--roi x0,y0,x1,y1] [--png out.png]
  python3 edge_probe.py --synthetic        # self-check on a synthetic lamp, no DNG needed

Read-only: never writes next to the take. Requires rawpy + numpy (PNG output
optional, needs Pillow).
"""
import argparse, glob, os, sys
import numpy as np


def load_dng(path):
    import rawpy
    with rawpy.imread(path) as raw:
        img = raw.raw_image_visible.astype(np.int64)           # LibRaw applies the LinearizationTable at load
        black = int(np.round(np.mean(raw.black_level_per_channel)))
        white = int(raw.white_level)
        pattern = raw.raw_pattern.copy()                       # 2x2 of indices into color_desc
        desc = raw.color_desc.decode() if isinstance(raw.color_desc, bytes) else str(raw.color_desc)
        top = raw.raw_image_visible.max()
    return img, black, white, pattern, desc, int(top)


def split_quads(img, pattern, desc):
    """-> R, G(mean of two), B, and the raw per-site arrays (r, g1, g2, b), one value per quad."""
    h, w = img.shape
    h -= h % 2; w -= w % 2
    img = img[:h, :w]
    sites = {(0, 0): img[0::2, 0::2], (0, 1): img[0::2, 1::2], (1, 0): img[1::2, 0::2], (1, 1): img[1::2, 1::2]}
    ch = {}
    for (y, x), a in sites.items():
        c = desc[pattern[y, x]]
        ch.setdefault(c, []).append(a)
    R = ch['R'][0]; B = ch['B'][0]; g1, g2 = ch['G'][0], ch['G'][1]
    return R, g1, g2, B


def rule(R, G, B, black, white, rlo, rhi, llo, lhi):
    """The shipped clip_convergence_blend, vectorised. Returns want in [0,1], ratio, level, and top-two-equal mask."""
    span = float(white - black)
    r = np.clip((R - black) / span, 0, None); g = np.clip((G - black) / span, 0, None); b = np.clip((B - black) / span, 0, None)
    stack = np.stack([r, g, b], axis=-1)
    srt = np.sort(stack, axis=-1)
    mx = srt[..., 2]; second = srt[..., 1]
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = np.where(mx > 0, second / mx, 0.0)
    s_ratio = np.clip((ratio - rlo) / (rhi - rlo), 0, 1)
    s_level = np.clip((mx - llo) / (lhi - llo), 0, 1)
    want = np.where((mx > llo) & (ratio > rlo), s_ratio * s_level, 0.0)
    return want, ratio, mx


def block_min(w):   # the shipped 2x2 erosion, on quad grid -> block grid
    h, ww = w.shape; h -= h % 2; ww -= ww % 2; w = w[:h, :ww]
    return np.minimum(np.minimum(w[0::2, 0::2], w[0::2, 1::2]), np.minimum(w[1::2, 0::2], w[1::2, 1::2]))


def block_mean(w):
    h, ww = w.shape; h -= h % 2; ww -= ww % 2; w = w[:h, :ww]
    return 0.25 * (w[0::2, 0::2] + w[0::2, 1::2] + w[1::2, 0::2] + w[1::2, 1::2])


def box3(a):
    p = np.pad(a, 1, mode='edge')
    return sum(p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3)) / 9.0


def neighbours_fired(f):
    p = np.pad(f.astype(np.int32), 1)
    return sum(p[i:i + f.shape[0], j:j + f.shape[1]] for i in range(3) for j in range(3)) - f.astype(np.int32)


def holes_islands(s, thr=0.5):
    f = s >= thr
    n = neighbours_fired(f)
    holes = int(np.sum(~f & (n >= 6)))
    islands = int(np.sum(f & (n <= 1)))
    return holes, islands, int(f.sum())


def pct(a, q):
    return float(np.percentile(a, q)) if a.size else float('nan')


def analyse(R, g1, g2, B, black, white, args, label=""):
    G = 0.5 * (g1 + g2)
    want, ratio, level = rule(R, G, B, black, white, args.ratio_lo, args.ratio_hi, args.level_lo, args.level_hi)
    core = want >= 0.99
    band = (want > 0.0) & (want < 0.99)
    # the surround: bright-ish, not fired, within 6 quads of a fired quad -> "yellow shade" proxy
    fired_any = want > 0
    near = neighbours_fired(fired_any) > 0
    for _ in range(5):
        near = neighbours_fired(near) > 0
    surround = near & ~fired_any & (level > 0.2)
    print(f"\n[{label}] quads: core {core.sum()}  band {band.sum()}  surround {surround.sum()}  frame {want.size}")

    # Q1: exact ties in the band, on the linearised values (== identical stored codes)
    stack = np.stack([R, G, B], axis=-1); srt = np.sort(stack, axis=-1)
    tie_rg = (R == g1) | (R == g2) | (B == g1) | (B == g2) | (R == B)  # any two sites of different colour on the identical code
    top_tie = (srt[..., 2] == srt[..., 1])          # top two CHANNELS identical (G is a mean, so this is stricter)
    for name, m in (("core", core), ("band", band), ("surround", surround)):
        if m.sum() == 0:
            continue
        print(f"  Q1 {name:9s}: top-two-channels identical {100*top_tie[m].mean():5.1f}%   any-site tie {100*tie_rg[m].mean():5.1f}%   "
              f"|max-second| in codes p50 {pct((srt[m][:,2]-srt[m][:,1]),50):.1f} p90 {pct((srt[m][:,2]-srt[m][:,1]),90):.1f}")
    # Q2: separability
    for name, m in (("core", core), ("band", band), ("surround", surround)):
        if m.sum() == 0:
            continue
        print(f"  Q2 {name:9s}: 2nd/max p5 {pct(ratio[m],5):.4f} p50 {pct(ratio[m],50):.4f} p95 {pct(ratio[m],95):.4f}   "
              f"level p5 {pct(level[m],5):.3f} p50 {pct(level[m],50):.3f} p95 {pct(level[m],95):.3f}")
    # Q3: treatments
    surround_blk = block_mean(surround.astype(float)) > 0.5
    variants = {
        "shipped: 2x2 min": block_min(want),
        "2x2 mean": block_mean(want),
        "2x2 mean + 3x3 box": box3(block_mean(want)),
        "2x2 min + 3x3 box": box3(block_min(want)),
    }
    # widened ratio ramp, then blurred
    want_w, _, _ = rule(R, G, B, black, white, args.ratio_lo - 0.02, args.ratio_hi, args.level_lo, args.level_hi)
    variants["ratio_lo-0.02, 2x2 mean + 3x3 box"] = box3(block_mean(want_w))
    # decimated trigger: ONE quad per 2x2 block (a quarter of the per-quad work), then the blur does the noise rejection
    h2, w2 = want.shape[0] - want.shape[0] % 2, want.shape[1] - want.shape[1] % 2
    variants["decimated 1 quad/block + 3x3 box"] = box3(want[:h2:2, :w2:2])
    variants["decimated 1 quad/block, no blur"] = want[:h2:2, :w2:2]
    lone = int(np.sum((want > 0.5) & (neighbours_fired(want > 0.5) == 0)))
    print(f"  per-quad rule: isolated fired quads (no fired 8-neighbour): {lone}   (hardware log: 245 / 498 on the two 16-bit takes)")
    print("  Q3 treatment                          holes  islands  fired_blocks  surround_touched(s>0.05)")
    for name, s in variants.items():
        h, i, n = holes_islands(s)
        touched = float(np.mean(s[surround_blk] > 0.05)) * 100 if surround_blk.sum() else float('nan')
        print(f"     {name:36s} {h:6d}  {i:7d}  {n:12d}  {touched:6.1f}%")
    return want


def synthetic():
    """A tungsten lamp: pinned R,G core, yellow shade, noise, 12-bit b=4 style quantisation."""
    rng = np.random.default_rng(1)
    h, w = 545, 964
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(yy - h / 2, xx - w / 2) / (0.25 * w)
    black, white = 200, 62704
    L = np.exp(-d * d * 3.0)                            # falloff
    G = 0.80 * L; R = 0.80 * L; Bc = 0.30 * L            # yellow: R~=G, B low
    noise = lambda: 1 + rng.normal(0, 0.006, (h, w))
    R = R * noise(); G1 = G * noise(); G2 = G * noise(); Bc = Bc * noise()
    clamp = 0.56
    Rq = np.minimum(R, clamp); G1q = np.minimum(G1, clamp); G2q = np.minimum(G2, clamp)
    # 12-bit b=4 style coarse quantisation of the linear domain near the clamp (64 L per code on the middle segment)
    q = 64.0 / white
    tocode = lambda a: np.round(a / q) * q * (white - black) + black
    return tocode(Rq), tocode(G1q), tocode(G2q), tocode(Bc), black, white


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--frame", type=int, default=44)
    ap.add_argument("--ratio-lo", type=float, default=0.98); ap.add_argument("--ratio-hi", type=float, default=0.997)
    ap.add_argument("--level-lo", type=float, default=0.40); ap.add_argument("--level-hi", type=float, default=0.50)
    ap.add_argument("--roi", type=str, default=None, help="x0,y0,x1,y1 in raw pixels")
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    if args.synthetic:
        R, g1, g2, B, black, white = synthetic()
        analyse(R, g1, g2, B, black, white, args, "synthetic lamp")
        return 0
    if not args.path:
        ap.error("need a take directory or a .dng, or --synthetic")
    path = args.path
    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, "*.dng")))
        if not files:
            sys.exit("no DNGs in " + path)
        path = files[min(args.frame, len(files) - 1)]
    img, black, white, pattern, desc, top = load_dng(path)
    print(f"{os.path.basename(path)}: {img.shape[1]}x{img.shape[0]}  black {black}  white {white}  top linearised value {top}  cfa {desc} {pattern.tolist()}")
    if args.roi:
        x0, y0, x1, y1 = (int(v) for v in args.roi.split(","))
        img = img[y0:y1, x0:x1]
    R, g1, g2, B = split_quads(img, pattern, desc)
    analyse(R, g1, g2, B, black, white, args, os.path.basename(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
