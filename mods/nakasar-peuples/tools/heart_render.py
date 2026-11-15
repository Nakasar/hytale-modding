"""Aperçus des cœurs de village (generate_village_hearts.py --preview) : rendu isométrique à sous-voxels, couleurs
moyennes des textures vanilla (palette extraite d'Assets.zip), formes approchées par la boîte englobante des modèles."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = __import__('pathlib').Path(__file__).resolve().parent
PAL = {}
SUB = 4

def tinted(c, t):
    return [c[i] * t[i] / 255 for i in range(3)] if t else c

def info(name):
    e = PAL.get(name) or PAL.get(name.lstrip('*').split('_State_Definitions')[0]) or {}
    t = e.get('tint')
    if name.startswith('Plant_Leaves'):
        c = e.get('mtex') or [60, 110, 40]
        if 'Snow' in name: c = [225, 232, 236]
        return dict(kind='full', top=c, side=[v * .85 for v in c], glow=False)
    if name.startswith('Wood_Bamboo_Trunk'):
        c=e.get('side') or e.get('mtex') or [120,140,60]
        return dict(kind='box', bb=[-5,0,-5,5,32,5], top=c, side=c, glow=False)
    if e.get('model'):
        bb = e.get('bbox')
        base = tinted(e.get('mtex') or [128, 128, 128], t)
        acc = tinted(e.get('macc') or base, t)
        plant = name.startswith('Plant_') or name.startswith('Wood_') and ('Branch' in name or 'Roots' in name)
        if name.startswith('Plant_Grass') or name.startswith('Plant_Fern') or name.startswith('Plant_Bush'):
            c = tinted(e.get('mtex') or [200, 200, 200], t or [103, 182, 45])
            return dict(kind='plant', top=c, side=c, h=0.6 if 'Short' in name else 0.85, glow=False)
        if name.startswith('Plant_Flower'):
            return dict(kind='flower', top=acc, side=base, h=0.6, glow=False)
        return dict(kind='box', bb=bb, top=acc if e.get('light') else base, side=base, glow=bool(e.get('light')))
    top = tinted(e.get('top') or [128, 128, 128], t)
    side = e.get('side') or top
    if name.endswith('_Half'):
        return dict(kind='half', top=top, side=side, glow=False)
    return dict(kind='full', top=top, side=side, glow=bool(e.get('light')))

def voxels(S):
    pts, tops, sides, glows = [], [], [], []
    cache = {}
    def add(x0, y0, z0, lo, hi, inf, top=None):
        a = [range(int(round(lo[i] * SUB)), max(int(round(lo[i] * SUB)) + 1, int(round(hi[i] * SUB)))) for i in range(3)]
        for i in a[0]:
            for j in a[1]:
                for k in a[2]:
                    pts.append((x0 * SUB + i, y0 * SUB + j, z0 * SUB + k))
                    tops.append(top or inf['top']); sides.append(inf['side']); glows.append(inf['glow'])
    for (x, y, z), (name, r) in S.b.items():
        inf = cache.get(name) or cache.setdefault(name, info(name))
        k = inf['kind']
        if k == 'full': add(x, y, z, (0, 0, 0), (1, 1, 1), inf)
        elif k == 'half': add(x, y, z, (0, 0, 0), (1, .5, 1), inf)
        elif k == 'plant':
            add(x, y, z, (.375, 0, .375), (.625, inf['h'], .625), inf)
            add(x, y, z, (.125, 0, .375), (.875, inf['h'] * .6, .625), inf)
        elif k == 'flower':
            add(x, y, z, (.375, 0, .375), (.625, .4, .625), dict(inf, top=inf['side']))
            add(x, y, z, (.25, .4, .25), (.75, .65, .75), dict(inf, side=inf['top']))
        else:
            bb = inf.get('bb')
            if not bb: add(x, y, z, (0, 0, 0), (1, 1, 1), inf); continue
            lo = [max(0, min(1, (bb[0] + 16) / 32)), max(0, min(2, bb[1] / 32)), max(0, min(1, (bb[2] + 16) / 32))]
            hi = [max(0, min(1, (bb[3] + 16) / 32)), max(0, min(2.5, bb[4] / 32)), max(0, min(1, (bb[5] + 16) / 32))]
            if r % 2 == 1: lo[0], lo[2], hi[0], hi[2] = lo[2], lo[0], hi[2], hi[0]
            add(x, y, z, lo, hi, inf)
    for (x, y, z), n in S.fluid.items():
        inf = dict(top=[70, 130, 190], side=[50, 100, 160], glow=False)
        add(x, y, z, (0, 0, 0), (1, .85, 1), inf)
    return np.array(pts), np.array(tops, float), np.array(sides, float), np.array(glows)

def sprite(k):
    P = lambda x, y, z: (2 * k * (x - z), k * (x + z) - 2 * k * y)
    faces = [[(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)], [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)], [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]]
    off = 4 * k + 2
    im = Image.new('L', (2 * off, 2 * off), 255); d = ImageDraw.Draw(im)
    for f, quad in enumerate(faces):
        d.polygon([(px + off, py + off) for px, py in (P(*c) for c in quad)], fill=f)
    a = np.array(im); ys, xs = np.nonzero(a != 255)
    return xs - off, ys - off, a[ys, xs]

def iso(S, k=1, view=0, bg=(222, 228, 232), title=None, size=None, crop=None):
    xyz, top, side, glow = voxels(S)
    x, y, z = xyz[:, 0].astype(np.int64), xyz[:, 1].astype(np.int64), xyz[:, 2].astype(np.int64)
    for _ in range(view % 4): x, z = -z, x
    sx = 2 * k * (x - z); sy = k * (x + z) - 2 * k * y
    m = 30
    x0, x1 = sx.min() - 4 * k - m, sx.max() + 4 * k + m
    y0, y1 = sy.min() - 4 * k - m - (40 if title else 0), sy.max() + 4 * k + m
    W, H = int(x1 - x0), int(y1 - y0)
    depth = x + y + z; dq = (depth - depth.min()).astype(np.int64)
    zbuf = np.full(W * H, -1, np.int64)
    dxs, dys, fs = sprite(k); vid = np.arange(len(x), dtype=np.int64)
    for dx, dy, f in zip(dxs, dys, fs):
        key = (dq << 34) | (vid << 2) | int(f)
        np.maximum.at(zbuf, (sy - y0 + dy) * W + (sx - x0 + dx), key)
    hit = zbuf >= 0
    v = (zbuf[hit] >> 2) & ((1 << 32) - 1); f = zbuf[hit] & 3
    shade = np.array([1.0, 0.78, 0.62])[f]
    col = np.where((f == 0)[:, None], top[v], side[v]) * shade[:, None]
    col = np.where(glow[v][:, None], np.minimum(top[v] * 1.25 + 40, 255), col)
    # légère ambiance : ce qui est bas est un peu plus sombre
    yy = y[v]; col *= (0.86 + 0.14 * np.clip((yy - y.min()) / max(1, (y.max() - y.min())), 0, 1))[:, None]
    img = np.zeros((H * W, 3)); img[:] = bg; img[hit] = col
    im = Image.fromarray(np.clip(img.reshape(H, W, 3), 0, 255).astype(np.uint8))
    # contours : arêtes entre voxels de profondeur très différente
    if title:
        d = ImageDraw.Draw(im)
        try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
        except Exception: font = None
        d.text((16, 10), title, fill=(30, 30, 40), font=font)
    return im

F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 12)
def plan(S, title, cell=14, R=None):
    cols = {}
    for (x, y, z), (n, r) in S.b.items():
        if y > 4: continue
        if (x, z) not in cols or y > cols[(x, z)][0]:
            cols[(x, z)] = (y, n)
    for (x, y, z) in S.fluid:
        if (x, z) not in cols or y >= cols[(x, z)][0]:
            cols[(x, z)] = (y, 'WATER')
    xs = [c[0] for c in cols]; zs = [c[1] for c in cols]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    W, H = (x1 - x0 + 1) * cell, (z1 - z0 + 1) * cell + 30
    im = Image.new('RGB', (W, H), (222, 228, 232)); d = ImageDraw.Draw(im)
    for (x, z), (y, n) in cols.items():
        if n == 'WATER': c = (70, 130, 190)
        else:
            inf = info(n); c = inf['top']
        k = 0.8 + 0.04 * min(y, 6)
        c = tuple(int(min(255, v * k)) for v in c)
        px, pz = (x - x0) * cell, (z - z0) * cell + 30
        d.rectangle([px, pz, px + cell - 1, pz + cell - 1], fill=c)
    labels = {'heart': ('cœur', (230, 40, 40)), 'board': ('tableau', (255, 230, 80)), 'deposit': ('dépôt', (120, 220, 255)), 'banner': ('bannière', (255, 140, 255))}
    for k, (txt, c) in labels.items():
        if k in S.marks:
            x, y, z = S.marks[k]; px, pz = (x - x0) * cell + cell // 2, (z - z0) * cell + 30 + cell // 2
            d.ellipse([px - 5, pz - 5, px + 5, pz + 5], fill=c, outline=(0, 0, 0))
            d.text((px + 7, pz - 7), txt, fill=(255, 255, 255), font=F, stroke_width=2, stroke_fill=(0, 0, 0))
    d.text((8, 6), title + '  (nord en haut)', fill=(30, 30, 40), font=F)
    return im

def scene_view(S):
    """Vue d'une scène du générateur : blocs (sans propriétaire), fluides, repères ; sol de contexte autour."""
    class V:
        pass
    v = V()
    v.b = {c: (n, r) for c, (n, r, o) in S.b.items()}
    v.fluid = dict(S.fluid)
    v.marks = {k: (m[:3] if isinstance(m, tuple) and len(m) == 4 else m) for k, m in S.marks.items()}
    v.marks["heart"] = (0, 1, 0)
    plaza = S.marks.get("plaza", set())
    E = max(max(abs(x), abs(z)) for x, z in plaza) + 3
    for x in range(-E, E + 1):
        for z in range(-E, E + 1):
            if math.hypot(x, z) > E + 0.5:
                continue
            for y in (-3, -2, -1):
                v.b.setdefault((x, y, z), ("Soil_Dirt", 0))
            if (x, z) not in plaza:
                v.b.setdefault((x, 0, z), ("Soil_Grass", 0))
    return v


def sheets(hearts, palette, out_dir):
    PAL.update(json.load(open(palette)))
    out_dir.mkdir(parents=True, exist_ok=True)
    for layout_id, (people, compose) in hearts.items():
        ims = [iso(scene_view(compose(t)), k=2, title=f"palier {t}") for t in (0, 3)]
        ims.append(plan(scene_view(compose(3)), "plan au sol, palier 3", cell=17))
        W = sum(i.width for i in ims) + 20
        H = max(i.height for i in ims) + 50
        sh = Image.new("RGB", (W, H), (222, 228, 232))
        x = 0
        for i in ims:
            sh.paste(i, (x, H - i.height))
            x += i.width
        ImageDraw.Draw(sh).text((16, 10), layout_id, fill=(20, 20, 30), font=F)
        sh.save(out_dir / f"coeur_{layout_id}.png")
        print("aperçu", out_dir / f"coeur_{layout_id}.png")
