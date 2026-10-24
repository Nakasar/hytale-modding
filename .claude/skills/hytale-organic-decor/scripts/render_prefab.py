#!/usr/bin/env python3
"""Aperçu et audit « organique » d'un ou plusieurs prefabs Hytale (.prefab.json, version 8).

    python3 .claude/skills/hytale-organic-decor/scripts/render_prefab.py CHEMIN [CHEMIN…] --out DOSSIER
            [--views iso,top] [--quarters 0,1,2,3] [--k 2] [--ignore REGEX] [--no-audit]

CHEMIN : un fichier .prefab.json ou un dossier (tous les prefabs dessous, assemblés dans le même repère :
c'est le cas des fractales découpées en Section_NN). Écrit dans DOSSIER :
  - iso_q<N>.png : vue isométrique depuis 4 côtés possibles (q0 = depuis +X+Z) ;
  - top.png : vue de dessus ombrée par la hauteur ;
  - audit.txt : les mesures ci-dessous (aussi affichées).

Audit (ce qui trahit un décor « couloir droit sans âme ») :
  - bords rectilignes : plus longues portions de contour parfaitement droites (≥ 8 blocs = à casser) ;
  - plateaux plats : plus grandes surfaces marchables à une seule hauteur, et leur remplissage de leur
    rectangle englobant (≈ 1,0 = rectangle parfait) ;
  - relief : écart-type des hauteurs du dessus ;
  - matières : nombre de blocs différents vus du dessus et part du plus fréquent (> 60 % = monotone).
Ce sont des signaux, pas des verdicts : une arène ronde voulue ou un mur de rempart peuvent être droits.
Toujours regarder les images.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import subprocess


def repo_root():
    """Dépôt du dossier courant (un worktree garde ses propres outils), sinon celui du script."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except Exception:  # noqa: BLE001
        return Path(__file__).resolve().parents[4]


ROOT = repo_root()
sys.path.insert(0, str(ROOT / "mods/nakasar-fractals/tools"))
try:
    from fractal_nature import nature_color  # palette d'aperçu déjà utilisée par les générateurs
except Exception:  # noqa: BLE001
    nature_color = lambda name: None  # noqa: E731

FAMILY = [
    (r"^Wood_.*(Roof|Planks|Beam|Plank)", (150, 105, 65)), (r"^Wood_", (120, 85, 55)),
    (r"Lava|Magma", (235, 95, 30)), (r"^(Water|Fluid)", (60, 110, 200)), (r"Ice", (170, 210, 240)),
    (r"^Rock_.*Brick", (150, 140, 130)), (r"^Rock_", (125, 125, 125)), (r"^Soil_", (140, 110, 75)),
    (r"^Plant_", (90, 160, 70)), (r"^Furniture_|^Deco_", (170, 140, 90)), (r"Glass", (180, 220, 235)),
    (r"Metal|Iron|Gold|Copper", (170, 165, 150)), (r"Light|Torch|Lantern|Candle|Brazier", (255, 220, 120)),
]
EMISSIVE = re.compile(r"Light|Torch|Lantern|Candle|Brazier|Lava|Magma|Glow|Crystal")


def color_of(name):
    c = nature_color(name)
    if c:
        return c
    for rx, col in FAMILY:
        if re.search(rx, name):
            return col
    h = hashlib.md5(name.encode()).digest()
    return (80 + h[0] % 150, 80 + h[1] % 150, 80 + h[2] % 150)


def load(paths, ignore):
    files = []
    for p in paths:
        p = Path(p)
        files += sorted(p.rglob("*.prefab.json")) if p.is_dir() else [p]
    rx = re.compile(ignore) if ignore else None
    cells = {}
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        for b in d.get("blocks", []):
            name = b.get("name", "")
            if not name or name == "Empty" or "filler" in b or (rx and rx.search(name)):
                continue
            cells[(b["x"], b["y"], b["z"])] = name
    if not cells:
        sys.exit("aucun bloc")
    return files, cells


def arrays(cells):
    keys = list(cells)
    xyz = np.array(keys, dtype=np.int64)
    names = [cells[k] for k in keys]
    rgb = np.array([color_of(n) for n in names], dtype=float)
    em = np.array([bool(EMISSIVE.search(n)) for n in names])
    return xyz, rgb, em, names


def sprite(k):
    P = lambda x, y, z: (2 * k * (x - z), k * (x + z) - 2 * k * y)  # noqa: E731
    faces = [[(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)],
             [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
             [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]]
    off = 4 * k + 2
    im = Image.new("L", (2 * off, 2 * off), 255)
    d = ImageDraw.Draw(im)
    for f, quad in enumerate(faces):
        d.polygon([(px + off, py + off) for px, py in (P(*c) for c in quad)], fill=f)
    a = np.array(im)
    ys, xs = np.nonzero(a != 255)
    return xs - off, ys - off, a[ys, xs]


def iso(xyz, rgb, em, k=2, quarter=0, bg=((150, 190, 230), (225, 235, 245)), margin=30):
    x, y, z = xyz[:, 0].copy(), xyz[:, 1], xyz[:, 2].copy()
    for _ in range(quarter % 4):
        x, z = -z, x
    sx = 2 * k * (x - z)
    sy = k * (x + z) - 2 * k * y
    x0, y0 = sx.min() - 4 * k - margin, sy.min() - 4 * k - margin
    W, H = int(sx.max() + 4 * k + margin - x0), int(sy.max() + 4 * k + margin - y0)
    if W * H > 60_000_000:
        sys.exit(f"image trop grande ({W}x{H}) : baisser --k ou rendre une section")
    depth = x + y + z
    dq = depth - depth.min()
    zbuf = np.full(W * H, -1, np.int64)
    vid = np.arange(len(x), dtype=np.int64)
    for dx, dy, f in zip(*sprite(k)):
        np.maximum.at(zbuf, (sy - y0 + dy) * W + (sx - x0 + dx), (dq << 34) | (vid << 2) | int(f))
    hit = zbuf >= 0
    v = (zbuf[hit] >> 2) & ((1 << 32) - 1)
    f = zbuf[hit] & 3
    col = rgb[v] * np.array([1.0, 0.78, 0.62])[f][:, None]
    col = np.where(em[v][:, None], np.minimum(rgb[v] * 1.1 + 15, 255), col)
    g = np.linspace(0, 1, H)[:, None, None]
    img = np.array(bg[0], float) * (1 - g) + np.array(bg[1], float) * g
    img = np.broadcast_to(img, (H, W, 3)).copy().reshape(-1, 3)
    img[hit] = col
    return Image.fromarray(np.clip(img.reshape(H, W, 3), 0, 255).astype(np.uint8))


def heightmap(xyz, names):
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    X0, Z0 = x.min(), z.min()
    W, H = int(x.max() - X0 + 1), int(z.max() - Z0 + 1)
    top = np.full((H, W), -10**9, np.int64)
    idx = np.full((H, W), -1, np.int64)
    order = np.argsort(y)
    top[z[order] - Z0, x[order] - X0] = y[order]
    idx[z[order] - Z0, x[order] - X0] = order
    return top, idx, (X0, Z0)


def top_view(rgb, top, idx, scale=3):
    has = idx >= 0
    c = np.zeros(top.shape + (3,))
    c[:] = (25, 30, 45)
    hv = top[has]
    c[has] = rgb[idx[has]]
    t = np.zeros(top.shape)
    if hv.size:
        t[has] = (hv - hv.min()) / max(1, hv.max() - hv.min())
    gz, gx = np.gradient(np.where(has, top, hv.min() if hv.size else 0).astype(float))
    shade = np.clip(0.55 + 0.45 * t - 0.05 * (gx + gz), 0.35, 1.25)
    c[has] *= shade[has][:, None]
    img = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def runs(mask):
    """Plus longues suites de True, par ligne."""
    best = []
    for r, row in enumerate(mask):
        n = 0
        for c, v in enumerate(list(row) + [False]):
            if v:
                n += 1
            else:
                if n:
                    best.append((n, r, c - n))
                n = 0
    return best


def audit(top, idx, names, origin):
    X0, Z0 = origin
    has = idx >= 0
    out = []
    # contour : une cellule pleine dont le voisin d'un côté est vide ; on compte les suites droites par côté
    edges = []
    pad = np.pad(has, 1)
    for label, (dz, dx) in {"nord (-Z)": (-1, 0), "sud (+Z)": (1, 0), "ouest (-X)": (0, -1), "est (+X)": (0, 1)}.items():
        nb = pad[1 + dz:pad.shape[0] - 1 + dz, 1 + dx:pad.shape[1] - 1 + dx]
        border = has & ~nb
        if dz:  # bord horizontal : suites le long de X
            for n, r, c in runs(border):
                edges.append((n, label, (int(X0 + c), int(Z0 + r))))
        else:
            for n, r, c in runs(border.T):
                edges.append((n, label, (int(X0 + r), int(Z0 + c))))
    # un bord posé sur la limite du prefab chargé est une coupure (sections de 64 en z), pas un vrai bord
    H0, W0 = has.shape
    def clipped(label, x, z):
        return (label.startswith("nord") and z == Z0) or (label.startswith("sud") and z == Z0 + H0 - 1) or \
               (label.startswith("ouest") and x == X0) or (label.startswith("est") and x == X0 + W0 - 1)
    cut = [e for e in edges if clipped(e[1], *e[2])]
    edges = [e for e in edges if not clipped(e[1], *e[2])]
    edges.sort(reverse=True)
    straight = [e for e in edges if e[0] >= 8]
    out.append(f"Bords rectilignes ≥ 8 blocs : {len(straight)}"
               + (f" (hors {len(cut)} coupures sur la limite du prefab chargé : charger les sections voisines)" if cut else ""))
    for n, label, (x, z) in straight[:8]:
        out.append(f"  - {n} blocs, bord {label}, depuis x={x} z={z}")
    # plateaux : composantes 4-connexes à hauteur égale
    seen = np.zeros_like(has)
    plats = []
    H, W = has.shape
    for r0 in range(H):
        for c0 in range(W):
            if not has[r0, c0] or seen[r0, c0]:
                continue
            h = top[r0, c0]
            stack, comp = [(r0, c0)], []
            seen[r0, c0] = True
            while stack:
                r, c = stack.pop()
                comp.append((r, c))
                for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if 0 <= rr < H and 0 <= cc < W and has[rr, cc] and not seen[rr, cc] and top[rr, cc] == h:
                        seen[rr, cc] = True
                        stack.append((rr, cc))
            if len(comp) >= 24:
                rs, cs = zip(*comp)
                box = (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
                plats.append((len(comp), int(h), round(len(comp) / box, 2), tuple(int(v) for v in (X0 + min(cs), Z0 + min(rs), X0 + max(cs), Z0 + max(rs)))))
    plats.sort(reverse=True)
    total = int(has.sum())
    out.append(f"Surface vue du dessus : {total} cellules")
    out.append("Plus grands plateaux plats (cellules, y, remplissage du rectangle, x0 z0 x1 z1) :")
    for n, h, fill, box in plats[:6]:
        flag = "  <- rectangle plat" if fill > 0.9 and n >= 60 else ""
        out.append(f"  - {n} ({100 * n // max(1, total)} %), y={h}, {fill}, {box}{flag}")
    hv = top[has]
    out.append(f"Relief : y de {hv.min()} à {hv.max()}, écart-type {hv.std():.1f}")
    tops = Counter(names[i] for i in idx[has])
    name, cnt = tops.most_common(1)[0]
    out.append(f"Matières vues du dessus : {len(tops)} blocs différents ; {name} = {100 * cnt // total} %")
    out.append("  " + ", ".join(f"{n} {100 * c // total}%" for n, c in tops.most_common(8)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--views", default="iso,top")
    ap.add_argument("--quarters", default="0")
    ap.add_argument("--k", type=int, default=2, help="taille d'un bloc en vue iso (pixels/2)")
    ap.add_argument("--ignore", help="regex de blocs à ne pas dessiner (ex. marqueurs invisibles)")
    ap.add_argument("--no-audit", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files, cells = load(a.paths, a.ignore or r"^Nakasar_.*(Marker|Spawner|Prison_Cell|Arena_Marker)")
    xyz, rgb, em, names = arrays(cells)
    print(f"{len(files)} prefab(s), {len(cells)} blocs")
    views = a.views.split(",")
    if "iso" in views:
        for q in (int(s) for s in a.quarters.split(",")):
            p = out / f"iso_q{q}.png"
            iso(xyz, rgb, em, a.k, q).save(p)
            print("écrit", p)
    top, idx, origin = heightmap(xyz, names)
    if "top" in views:
        p = out / "top.png"
        top_view(rgb, top, idx).save(p)
        print("écrit", p)
    if not a.no_audit:
        lines = audit(top, idx, names, origin)
        (out / "audit.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
