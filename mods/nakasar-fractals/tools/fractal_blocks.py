"""Moteur de blocs en modèle 3D (DrawType Model), dans le style des blocs vanilla lus dans Assets.zip 0.7.2.

Repère vanilla : 32 unités = 1 bloc, origine au centre du bas du bloc, Y vers le haut, face avant vers +Z,
1 texel par unité. Une pièce est un dict :
    name     nom du nœud (les animations visent les nœuds par leur nom : "Lid" pour le coffre vanilla…)
    center   centre de la boîte, en unités, repère du bloc
    size     (x, y, z)
    paint    peintre (rng, largeur, hauteur, face) -> image RGBA ; un texel transparent est découpé en jeu
    rot      (rx, ry, rz) en degrés, ordre X puis Y puis Z ; seulement sur une pièce sans enfant ni pivot
    parent   nom d'une pièce déjà déclarée (hiérarchie du .blockymodel)
    pivot    point de rotation des animations (le nœud y est posé, la boîte décalée par shape.offset) ; les
             enfants sont placés par rapport au centre de la boîte parente
    glow     True : shadingMode "fullbright" (parties lumineuses)
"""
import json
import math
import random

from PIL import Image, ImageFilter

import fractal_materials as fmat

FACES = ("top", "bottom", "front", "back", "left", "right")
UNIT = 32


# ---------------------------------------------------------------- couleurs

def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def noise(rng, w, h, scale=4, amp=0.10):
    gw, gh = max(2, w // scale + 2), max(2, h // scale + 2)
    small = Image.new("L", (gw, gh))
    small.putdata([rng.randint(0, 255) for _ in range(gw * gh)])
    big = small.resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(scale / 3)).crop((scale, scale, scale + w, scale + h))
    px = big.load()
    return [[1 + amp * ((px[x, y] - 128) / 128) for x in range(w)] for y in range(h)]


def _canvas(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img, img.load()


def _rim(x, y, w, h, face):
    """Facteur d'arête façon vanilla : arête haute éclairée, contour sombre d'un texel."""
    if face in ("top", "bottom"):
        if min(x, y, w - 1 - x, h - 1 - y) == 0:
            return 0.78 if face == "bottom" else 1.16
        return 1.0
    if y == 0:
        return 1.18
    if y == h - 1 or x == 0 or x == w - 1:
        return 0.74
    return 1.0


# ---------------------------------------------------------------- peintres

def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def _painted(key, base, rotate=False, aligned=False, contrast=1.0, bottom=0.7, rim=True):
    """Peintre « façon Hytale » : texture de bloc vanilla (fractal_materials) recolorée vers `base`, arêtes vanilla."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        turn = rotate if face not in ("top", "bottom") else False
        f = fmat.factors(key, rng, w, h, turn, aligned, contrast)
        for y in range(h):
            for x in range(w):
                k = f[y][x] * (bottom if face == "bottom" else 1.0)
                if rim:
                    k *= _rim(x, y, w, h, face)
                px[x, y] = shade(base, k) + (255,)
        return img
    return paint


# Style Hytale (Kevin, 25 octobre 2026) : planches, pierre, métal, écorce et toile reprennent le dessin peint des blocs
# vanilla (tools/materials/), recoloré ; les signatures d'origine sont gardées (les anciens réglages de dessin, largeur
# de planche ou taille de pierre, ne servent plus).

def planks(base, width=5, vertical=True, grain=0.16, rim=True):
    """Planches : bois dur vanilla (bois sombre vanilla pour une teinte foncée), à la verticale par défaut."""
    return _painted("planks_dark" if _lum(base) < 70 else "planks", base, rotate=vertical, rim=rim)


def stone(base, brick=(8, 5), mortar=0.6, rim=True):
    """Pierre taillée : briques de pierre vanilla."""
    return _painted("brick", base, contrast=1.1, rim=rim)


def smooth_stone(base, rim=True):
    """Pierre lisse (dalles, socles) : pierre lisse vanilla à cadre, alignée sur l'arête."""
    return _painted("smooth", base, aligned=True, rim=rim)


def metal(base, rivets=True):
    """Laiton / or / fer : bronze lisse vanilla (rivets aux coins) ou fer lisse pour une teinte froide."""
    return _painted("metal" if base[0] >= base[2] else "metal_cold", base, aligned=rivets, contrast=1.3)


def crystal(dark, light):
    """Facette de cristal lumineuse (rendue en fullbright) : dégradé diagonal, reflet."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        for y in range(h):
            for x in range(w):
                t = (x / max(1, w - 1) * 0.4 + y / max(1, h - 1) * 0.6)
                c = mix(light, dark, t)
                if (x + y) % 5 == 0:
                    c = shade(c, 1.12)
                if x == 0 or y == 0:
                    c = shade(light, 1.15)
                px[x, y] = c + (255,)
        return img
    return paint


def solid(color, f_bottom=0.7):
    def paint(rng, w, h, face):
        return Image.new("RGBA", (w, h), shade(color, f_bottom if face == "bottom" else 1.0) + (255,))
    return paint


def glyph(color, kind="ring", faces=("front", "back")):
    """Rune lumineuse sur fond transparent (incrustation fullbright posée devant une face)."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        if face not in faces:
            return img
        cx, cy = (w - 1) / 2, (h - 1) / 2
        r = min(w, h) / 2 - 1
        for y in range(h):
            for x in range(w):
                d = math.hypot(x - cx, y - cy)
                on = False
                if kind in ("ring", "eye"):
                    on = abs(d - r) < 0.7 or (kind == "eye" and d < r * 0.35)
                    on = on or (abs(x - cx) < 0.6 and r * 0.45 < d < r)
                elif kind == "fork":
                    on = (abs(x - cx) < 0.6 and y > cy) or (abs(d - r * 0.6) < 0.7 and y <= cy)
                elif kind == "tick":
                    on = (x + y) % 4 == 0 and (x in (0, w - 1) or y in (0, h - 1))
                if on:
                    px[x, y] = shade(color, 1.0 + 0.15 * ((x + y) % 2)) + (255,)
        return img
    return paint


def log(bark, core=(196, 156, 104)):
    """Rondin le long de l'axe Z : écorce sur les côtés, cernes sur les bouts (faces avant et arrière)."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        n = noise(rng, w, h, 2, 0.1)
        # Écorce de chêne vanilla, fibres le long du rondin (axe Z).
        sides = fmat.factors("bark", rng, w, h, rotate=face in ("top", "bottom", "left", "right"))
        cx, cy = (w - 1) / 2, (h - 1) / 2
        for y in range(h):
            for x in range(w):
                if face in ("front", "back"):
                    d = max(abs(x - cx), abs(y - cy))
                    if d >= min(w, h) / 2 - 1:
                        c = shade(bark, 0.8)
                    else:
                        c = shade(core, (1.0 if int(d) % 2 else 0.86) * n[y][x])
                else:
                    c = shade(bark, sides[y][x] * (1.12 if (x if face in ("left", "right") else y) == 0 else 1.0))
                px[x, y] = c + (255,)
        return img
    return paint


def ground(side, top, rim_color=None):
    """Bloc de sol : côtés de terre, dessus d'herbe/mousse/neige qui déborde d'un ou deux texels sur les côtés."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        n = noise(rng, w, h, 3, 0.12)
        for y in range(h):
            for x in range(w):
                if face == "top":
                    c = shade(top, n[y][x] * (1.08 if rng.random() < 0.08 else 1.0))
                elif face == "bottom":
                    c = shade(side, 0.7 * n[y][x])
                else:
                    edge = 2 + (x * 7 + 3) % 3
                    c = shade(rim_color or top, n[y][x] * 0.92) if y < edge else shade(side, n[y][x] * (0.95 - 0.1 * y / h))
                px[x, y] = c + (255,)
        return img
    return paint


def mist(dark, light, alpha=255):
    """Brume des Brumes : volutes douces entre deux violets."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        n = noise(rng, w, h, 4, 0.9)
        for y in range(h):
            for x in range(w):
                t = max(0.0, min(1.0, (n[y][x] - 0.1) / 1.8 + 0.25 * ((x + 2 * y) % 9 < 2)))
                px[x, y] = mix(dark, light, t) + (alpha,)
        return img
    return paint


def jade(base, vein):
    """Jade poli : bruit doux, veines claires en diagonale."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        n = noise(rng, w, h, 4, 0.14)
        phase = rng.random() * 6
        for y in range(h):
            for x in range(w):
                v = math.sin((x + y) * 0.5 + phase + 2 * n[y][x])
                c = mix(shade(base, n[y][x]), vein, 0.55) if v > 0.93 else shade(base, n[y][x])
                if face not in ("top", "bottom"):
                    c = shade(c, _rim(x, y, w, h, face))
                px[x, y] = c + (255,)
        return img
    return paint


def glass(tint, alpha=150):
    """Verre teinté semi-transparent, reflets en diagonale."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        for y in range(h):
            for x in range(w):
                c, a = tint, alpha
                if (x - y) % 11 in (0, 1):
                    c, a = shade(tint, 1.3), min(255, alpha + 60)
                if x in (0, w - 1) or y in (0, h - 1):
                    c, a = shade(tint, 1.2), min(255, alpha + 40)
                px[x, y] = c + (a,)
        return img
    return paint


def cloth(base, stripe=None):
    """Toile : tissage de la toile blanche vanilla, recoloré."""
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        n = fmat.factors("cloth", rng, w, h, contrast=1.4)
        for y in range(h):
            for x in range(w):
                c = shade(base, n[y][x] * (0.75 if face == "bottom" else 1.0))
                if stripe and y in (1, h - 2):
                    c = stripe
                px[x, y] = c + (255,)
        return img
    return paint


def faces(top_paint, side_paint):
    """Peintre composé : un pour le dessus et le dessous, un autre pour les côtés."""
    def paint(rng, w, h, face):
        return (top_paint if face in ("top", "bottom") else side_paint)(rng, w, h, face)
    return paint


def paper(base=(232, 220, 190), ink=(70, 55, 45)):
    def paint(rng, w, h, face):
        img, px = _canvas(w, h)
        for y in range(h):
            for x in range(w):
                c = shade(base, 0.97 + 0.05 * rng.random())
                if face == "top" and 1 < x < w - 2 and y % 2 == 1 and rng.random() < 0.7:
                    c = mix(c, ink, 0.55)
                if face != "top":
                    c = shade(c, 0.85 if (y % 2) else 0.95)
                px[x, y] = c + (255,)
        return img
    return paint


# ---------------------------------------------------------------- géométrie

def euler(rot):
    rx, ry, rz = (math.radians(a) for a in (rot or (0, 0, 0)))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    mx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    my = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    mz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))
    return mul(mz, mul(my, mx))


def apply(m, p):
    return tuple(sum(m[i][k] * p[k] for k in range(3)) for i in range(3))


def quat(m):
    t = m[0][0] + m[1][1] + m[2][2]
    if t > 0:
        s = math.sqrt(t + 1) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, s / 4)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (s / 4, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, s / 4, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, s / 4, (m[1][0] - m[0][1]) / s)
    return {"x": round(q[0], 6), "y": round(q[1], 6), "z": round(q[2], 6), "w": round(q[3], 6)}


def tilt(base, rot, local):
    """Point `local` (repère d'une pièce tournée de `rot` autour de `base`) dans le repère du bloc."""
    p = apply(euler(rot), local)
    return (base[0] + p[0], base[1] + p[1], base[2] + p[2])


def face_size(size, face):
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sz
    if face in ("front", "back"):
        return sx, sy
    return sz, sy


def tex_size(size, face):
    return tuple(max(1, math.ceil(v - 1e-6)) for v in face_size(size, face))


def build_atlas(parts, seed, tex_w=64):
    rng = random.Random(seed)
    regions = []
    for pi, p in enumerate(parts):
        for g in (("top",), ("bottom",), ("front", "back"), ("left", "right")):
            w, h = tex_size(p["size"], g[0])
            regions.append((pi, g, w, h, p["paint"](rng, w, h, g[0])))
    tex_w = max(tex_w, max(r[2] for r in regions))
    order = sorted(range(len(regions)), key=lambda k: (-regions[k][3], -regions[k][2]))
    tex_h = 32
    while True:
        atlas = Image.new("RGBA", (tex_w, tex_h), (0, 0, 0, 0))
        uv, x, y, shelf, ok = {}, 0, 0, 0, True
        for k in order:
            pi, g, w, h, img = regions[k]
            if x + w > tex_w:
                x, y, shelf = 0, y + shelf, 0
            if y + h > tex_h:
                ok = False
                break
            atlas.paste(img, (x, y))
            for f in g:
                uv[(pi, f)] = (x, y)
            x += w
            shelf = max(shelf, h)
        if ok:
            return atlas, uv
        tex_h += 32


def num(v):
    v = round(v, 4)
    return int(v) if float(v).is_integer() else v


def vec(v):
    return {"x": num(v[0]), "y": num(v[1]), "z": num(v[2])}


def origin(p):
    return p.get("pivot") or p["center"]


def check(parts):
    names = set()
    for p in parts:
        if p.get("parent") and p["parent"] not in names:
            raise ValueError(f"{p['name']} : parent {p['parent']} inconnu ou déclaré après")
        names.add(p["name"])
        if p.get("rot") and (p.get("pivot") or any(c.get("parent") == p["name"] for c in parts)):
            raise ValueError(f"{p['name']} : rotation seulement sur une pièce sans pivot ni enfant")


def build_model(parts, uv):
    check(parts)
    by_name, nodes = {}, []
    for pi, p in enumerate(parts):
        o = origin(p)
        parent = by_name.get(p.get("parent"))
        # Les enfants se placent par rapport au centre de la boîte parente (position + offset), comme le
        # couvercle du coffre vanilla Chest_Epic_Small (serrure et ferrures suivent la boîte, pas la charnière).
        po = parent[0]["center"] if parent else (0, 0, 0)
        layout = {f: {"offset": {"x": uv[(pi, f)][0], "y": uv[(pi, f)][1]}, "mirror": {"x": False, "y": False},
                      "angle": 0} for f in FACES}
        node = {
            "id": str(pi + 1),
            "name": p["name"],
            "position": vec(tuple(o[k] - po[k] for k in range(3))),
            "orientation": quat(euler(p.get("rot"))),
            "shape": {
                "type": "box",
                "offset": vec(tuple(p["center"][k] - o[k] for k in range(3))),
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"size": vec(p["size"])},
                "textureLayout": layout,
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": "fullbright" if p.get("glow") else "standard",
            },
            "children": [],
        }
        by_name[p["name"] + f"#{pi}"] = (p, node)
        by_name[p["name"]] = (p, node)
        (parent[1]["children"] if parent else nodes).append(node)
    return {"nodes": nodes, "lod": "auto"}


# ---------------------------------------------------------------- rendu logiciel (aperçus et icônes)

def quads(p, pi, uv):
    hx, hy, hz = (v / 2 for v in p["size"])
    m = euler(p.get("rot"))
    c = p["center"]
    defs = {
        "top": ((-hx, hy, -hz), (2 * hx, 0, 0), (0, 0, 2 * hz), (0, 1, 0)),
        "bottom": ((-hx, -hy, hz), (2 * hx, 0, 0), (0, 0, -2 * hz), (0, -1, 0)),
        "front": ((-hx, hy, hz), (2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, 1)),
        "back": ((hx, hy, -hz), (-2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, -1)),
        "right": ((hx, hy, hz), (0, 0, -2 * hz), (0, -2 * hy, 0), (1, 0, 0)),
        "left": ((-hx, hy, -hz), (0, 0, 2 * hz), (0, -2 * hy, 0), (-1, 0, 0)),
    }
    for f, (o, u, v, n) in defs.items():
        o = apply(m, o)
        yield (f, (o[0] + c[0], o[1] + c[1], o[2] + c[2]), apply(m, u), apply(m, v), apply(m, n),
               uv[(pi, f)], tex_size(p["size"], f))


def render(parts, atlas, uv, size=256, yaw=-35, pitch=26, scale=None, center=None, bg=None):
    if center is None or scale is None:
        lo = [min(p["center"][k] - max(p["size"]) / 2 for p in parts) for k in range(3)]
        hi = [max(p["center"][k] + max(p["size"]) / 2 for p in parts) for k in range(3)]
        center = center or tuple((lo[k] + hi[k]) / 2 for k in range(3))
        scale = scale or size * 0.62 / max(hi[k] - lo[k] for k in range(3))
    W = H = size
    zbuf = [[-1e9] * W for _ in range(H)]
    img = Image.new("RGBA", (W, H), bg or (0, 0, 0, 0))
    px, tex = img.load(), atlas.load()
    a, b = math.radians(yaw), math.radians(pitch)

    def view(p):
        x, y, z = p[0] - center[0], p[1] - center[1], p[2] - center[2]
        x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        return (x, y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b))

    def lum(n):
        if n[1] > 0.7:
            return 1.0
        if n[1] < -0.7:
            return 0.5
        return 0.72 + 0.16 * max(-1, min(1, 0.8 * n[0] + 0.6 * n[2]))

    # deux passes : l'opaque remplit le z-buffer, puis le verre translucide se mélange par-dessus
    for clear in (False, True):
        for pi, p in enumerate(parts):
            for f, o, u, v, n, (tu, tv), (fw, fh) in quads(p, pi, uv):
                nv = view((n[0] + center[0], n[1] + center[1], n[2] + center[2]))
                if nv[2] <= 1e-6:
                    continue
                l = 1.0 if p.get("glow") else lum(n)
                su = max(2, int(math.hypot(*u) * scale * 1.5) + 2)
                sv = max(2, int(math.hypot(*v) * scale * 1.5) + 2)
                done = set()
                for j in range(sv):
                    fv = (j + 0.5) / sv
                    for i in range(su):
                        fu = (i + 0.5) / su
                        q = view(tuple(o[k] + u[k] * fu + v[k] * fv for k in range(3)))
                        sx, sy = int(W / 2 + q[0] * scale), int(H / 2 - q[1] * scale)
                        if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                            t = tex[min(tu + int(fu * fw), atlas.width - 1), min(tv + int(fv * fh), atlas.height - 1)]
                            if t[3] < 16 or (t[3] < 250) != clear:
                                continue
                            if not clear:
                                zbuf[sy][sx] = q[2]
                                px[sx, sy] = shade(t, l) + (255,)
                            elif (sx, sy) not in done:
                                done.add((sx, sy))
                                k, d = t[3] / 255, px[sx, sy]
                                c = shade(t, l)
                                px[sx, sy] = tuple(int(c[m] * k + d[m] * (1 - k)) for m in range(3)) + \
                                    (max(d[3], t[3]),)
    return img


# ---------------------------------------------------------------- animations (.blockyanim)

def anim(duration, nodes, loop=True):
    """nodes : {nom: {"orientation": [(t, (rx, ry, rz))], "position": [(t, (x, y, z))]}} en images (60/s)."""
    out = {}
    for name, tracks in nodes.items():
        entry = {"position": [], "orientation": [], "shapeStretch": [], "shapeVisible": [], "shapeUvOffset": []}
        for t, p in tracks.get("position", []):
            entry["position"].append({"time": t, "delta": vec(p), "interpolationType": "linear"})
        for t, r in tracks.get("orientation", []):
            entry["orientation"].append({"time": t, "delta": quat(euler(r)), "interpolationType": "linear"})
        for t, s in tracks.get("shapeStretch", []):
            entry["shapeStretch"].append({"time": t, "delta": vec(s), "interpolationType": "smooth"})
        out[name] = entry
    return {"formatVersion": 1, "duration": duration, "holdLastKeyframe": not loop, "nodeAnimations": out}


def write_block_model(name, parts, model_dir, icon_dir, seed, icon_yaw=-35):
    """Écrit <name>.blockymodel et <name>_Texture.png dans model_dir, l'icône 64×64 ; rend l'aperçu 384×384."""
    atlas, uv = build_atlas(parts, seed)
    model_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    atlas.save(model_dir / f"{name}_Texture.png")
    (model_dir / f"{name}.blockymodel").write_text(json.dumps(build_model(parts, uv), indent=2) + "\n")
    big = render(parts, atlas, uv, 256, yaw=icon_yaw)
    big.resize((64, 64), Image.LANCZOS).save(icon_dir / f"{name}.png")
    return render(parts, atlas, uv, 384, yaw=icon_yaw, bg=(36, 38, 52, 255))
