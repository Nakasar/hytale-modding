#!/usr/bin/env python3
"""Génère les modèles animés de la citrouille géante et de ses vrilles combattantes.

    python3 mods/nakasar-vampires/tools/generate_pumpkin_models.py [--preview DOSSIER]

- Common/NPC/Nakasar/Giant_Pumpkin/ : citrouille sculptée de 2,3 blocs de large, coupée au niveau de la
  bouche. Le haut (« Head ») pivote sur une charnière à l'arrière : la bouche s'ouvre et se ferme et
  laisse voir l'intérieur rougeoyant. Yeux, nez et bouche sont découpés et lumineux (plaque « Glow »
  en fullbright, transparente ailleurs).
- Common/NPC/Nakasar/Pumpkin_Vine/ : vrille épineuse de 2,8 blocs de haut sortant d'un monticule de
  terre : six segments articulés, épines orange, feuilles, bourgeon crochu au bout.
- Animations (.blockyanim, 60 images par seconde) : repos, apparition, blessure, mort, et une par
  attaque. Les animations d'attaque sont jouées par les interactions (Effects.ItemAnimationId) via
  les jeux Server/Item/Animations/Nakasar/<modèle>.json ; leur durée suit celle des interactions.
- Server/Models/Nakasar/Nakasar_Giant_Pumpkin.json et Nakasar_Pumpkin_Vine.json : modèles (hitbox,
  lumière, AnimationSets).

Repère : format « character », 64 unités = 1 bloc, origine au sol, face avant vers +Z. Les
articulations sont des nœuds sans forme ; les boîtes sont des feuilles centrées sur leur position.
Une rotation positive autour de X penche le haut d'un nœud vers l'avant (+Z).

--preview DOSSIER écrit des rendus PNG (repos et images clés des attaques) pour vérifier les modèles.
"""
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
FPS = 60

FACES = ("top", "bottom", "front", "back", "left", "right")


# --- maths -------------------------------------------------------------------------------------

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qaxis(axis, deg):
    s, c = math.sin(math.radians(deg) / 2), math.cos(math.radians(deg) / 2)
    return tuple(v * s for v in axis) + (c,)


def qeuler(x=0.0, y=0.0, z=0.0):
    """Lacet (Y), puis tangage (X), puis roulis (Z), en degrés."""
    return qmul(qmul(qaxis((0, 1, 0), y), qaxis((1, 0, 0), x)), qaxis((0, 0, 1), z))


def qrot(q, v):
    x, y, z, w = q
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return p[:3]


def qjson(q):
    return {k: round(v, 6) + 0 for k, v in zip("xyzw", q)}


def vjson(v):
    return {k: num(round(c, 4)) for k, c in zip("xyz", v)}


def num(v):
    return int(v) if float(v).is_integer() else v


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def keys(t, points):
    """Interpolation douce entre des points (temps, valeur) triés."""
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * smooth((t - t0) / (t1 - t0))
    return points[-1][1]


# --- couleurs et peintres ----------------------------------------------------------------------

def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c[:3])


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def soft_noise(rng, w, h, scale=4, amp=0.1):
    gw, gh = max(2, w // scale + 2), max(2, h // scale + 2)
    small = Image.new("L", (gw, gh))
    small.putdata([rng.randint(0, 255) for _ in range(gw * gh)])
    big = small.resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(scale / 2)).crop((scale, scale, scale + w, scale + h))
    px = big.load()
    return [[1 + amp * ((px[x, y] - 128) / 128) for x in range(w)] for y in range(h)]


def solid(img, f):
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            px[x, y] = f(x, y) + (255,)
    return img


def p_plain(base, top=1.12, bottom=0.7, grad=0.2, amp=0.1):
    """Couleur unie bruitée : dessus plus clair, bas plus sombre."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=amp)
        if face == "top":
            return solid(Image.new("RGBA", (w, h)), lambda x, y: shade(base, top * n[y][x]))
        if face == "bottom":
            return solid(Image.new("RGBA", (w, h)), lambda x, y: shade(base, bottom * n[y][x]))
        return solid(Image.new("RGBA", (w, h)),
                     lambda x, y: shade(base, (1 + grad / 2 - grad * y / max(1, h - 1)) * n[y][x]))

    return paint


def p_ribbed(base, dark, light, period, top=1.1, bottom=0.65, grad=0.25, inside=None):
    """Côtes verticales (citrouille, vrille) : sillons sombres, bosses plus claires."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=0.08)
        if face == "top" or face == "bottom":
            if inside is not None and face == "bottom":
                return inside(rng, w, h, face)
            f = top if face == "top" else bottom
            cx, cy = (w - 1) / 2, (h - 1) / 2

            def c(x, y):
                a = math.atan2(y - cy, x - cx)
                r = math.hypot((x - cx) / max(1, cx), (y - cy) / max(1, cy))
                rib = 0.5 + 0.5 * math.cos(a * 8)
                col = mix(dark, base, 0.55 + 0.45 * (1 - rib ** 6))
                return shade(col, f * (1.05 - 0.15 * r) * n[y][x])

            return solid(Image.new("RGBA", (w, h)), c)

        def c(x, y):
            phase = (x + 0.5) / period
            rib = abs(math.sin(math.pi * phase))
            col = mix(dark, base, min(1.0, rib * 1.6))
            col = mix(col, light, max(0.0, rib - 0.75) * 1.4)
            return shade(col, (1 + grad / 2 - grad * y / max(1, h - 1)) * n[y][x])

        return solid(Image.new("RGBA", (w, h)), c)

    return paint


def p_glow(c0, c1):
    """Lueur : dégradé du cœur (c0) vers le bord (c1)."""

    def paint(rng, w, h, face):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        return solid(Image.new("RGBA", (w, h)),
                     lambda x, y: mix(c0, c1, min(1.0, math.hypot((x - cx) / max(1, cx), (y - cy) / max(1, cy)))))

    return paint


def p_thorn(base, tip):
    """Épine : de la base (sombre) à la pointe (claire) le long de Y."""

    def paint(rng, w, h, face):
        if face in ("top",):
            return solid(Image.new("RGBA", (w, h)), lambda x, y: tip)
        if face in ("bottom",):
            return solid(Image.new("RGBA", (w, h)), lambda x, y: shade(base, 0.7))
        return solid(Image.new("RGBA", (w, h)), lambda x, y: mix(tip, base, y / max(1, h - 1)))

    return paint


def p_leaf(base, vein):
    def paint(rng, w, h, face):
        if face not in ("top", "bottom"):
            return solid(Image.new("RGBA", (w, h)), lambda x, y: shade(base, 0.8))
        cx = (w - 1) / 2
        n = soft_noise(rng, w, h, amp=0.08)
        f = 1.08 if face == "top" else 0.8
        return solid(Image.new("RGBA", (w, h)),
                     lambda x, y: shade(vein if abs(x - cx) < 0.6 or (abs(x - cx) - abs(y - h * 0.4) * 0.6) ** 2 < 0.3 else base,
                                        f * n[y][x]))

    return paint


def p_transparent():
    def paint(rng, w, h, face):
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    return paint


# --- modèle ------------------------------------------------------------------------------------

class Box:
    def __init__(self, name, pos, size, paint, stretch=1, rot=(0, 0, 0), shading="flat", double=False):
        self.name, self.pos, self.size, self.paint = name, pos, size, paint
        self.stretch = (stretch,) * 3 if isinstance(stretch, (int, float)) else stretch
        self.rot, self.shading, self.double = qeuler(*rot), shading, double


class Joint:
    def __init__(self, name, pos, children, rot=(0, 0, 0)):
        self.name, self.pos, self.children, self.rot = name, pos, children, qeuler(*rot)


def face_size(size, face):
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sz
    if face in ("front", "back"):
        return sx, sy
    return sz, sy


def walk(node):
    yield node
    if isinstance(node, Joint):
        for c in node.children:
            yield from walk(c)


def build_atlas(root, seed, tex_w):
    rng = random.Random(seed)
    boxes = [n for n in walk(root) if isinstance(n, Box)]
    regions = []
    for b in boxes:
        for f in FACES:
            w, h = (max(1, math.ceil(v)) for v in face_size(b.size, f))
            regions.append((b.name, f, w, h, b.paint(rng, w, h, f)))
    order = sorted(range(len(regions)), key=lambda k: (-regions[k][3], -regions[k][2]))
    tex_h = 32
    while True:
        atlas = Image.new("RGBA", (tex_w, tex_h), (0, 0, 0, 0))
        uv, x, y, shelf, ok = {}, 0, 0, 0, True
        for k in order:
            name, f, w, h, img = regions[k]
            if x + w > tex_w:
                x, y, shelf = 0, y + shelf, 0
            if y + h > tex_h:
                ok = False
                break
            atlas.paste(img, (x, y))
            uv[(name, f)] = (x, y)
            x += w
            shelf = max(shelf, h)
        if ok:
            return atlas, uv
        tex_h *= 2


def model_json(root, uv):
    ids = iter(range(1, 1000))
    names = set()

    def node(n):
        assert n.name not in names, n.name
        names.add(n.name)
        doc = {"id": str(next(ids)), "name": n.name, "position": vjson(n.pos), "orientation": qjson(n.rot)}
        if isinstance(n, Box):
            doc["shape"] = {
                "type": "box",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": vjson(n.stretch),
                "settings": {"size": vjson(n.size)},
                "textureLayout": {f: {"offset": {"x": uv[(n.name, f)][0], "y": uv[(n.name, f)][1]},
                                      "mirror": {"x": False, "y": False}, "angle": 0} for f in FACES},
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": n.double,
                "shadingMode": n.shading,
            }
        else:
            doc["shape"] = {
                "type": "none",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"isPiece": False},
                "textureLayout": {},
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": "flat",
            }
            doc["children"] = [node(c) for c in n.children]
        return doc

    nodes = [node(root)]
    assert len(names) <= 255
    return {"nodes": nodes, "format": "character", "lod": "auto"}


# --- animations --------------------------------------------------------------------------------

class Anim:
    """Animation échantillonnée : pose(t) -> {nœud: (euler (x, y, z), décalage (x, y, z))}, t en secondes."""

    def __init__(self, name, duration, pose, step=3, loop=False, hold=False):
        self.name, self.duration, self.pose, self.step, self.loop, self.hold = name, duration, pose, step, loop, hold

    def frames(self):
        return int(round(self.duration * FPS))

    def to_json(self, joints):
        total = self.frames()
        times = list(range(0, total, self.step)) + [total]
        tracks = {j: {"position": [], "orientation": [], "shapeStretch": [], "shapeVisible": [], "shapeUvOffset": []}
                  for j in joints}
        for fr in times:
            t = fr / FPS
            if self.loop and fr == total:
                t = 0.0
            pose = self.pose(t)
            for j in joints:
                rot, off = pose.get(j, ((0, 0, 0), (0, 0, 0)))
                tracks[j]["orientation"].append({"time": fr, "delta": qjson(qeuler(*rot)), "interpolationType": "smooth"})
                tracks[j]["position"].append({"time": fr, "delta": vjson(off), "interpolationType": "smooth"})
        for j in joints:
            for kind in ("orientation", "position"):
                frames = tracks[j][kind]
                if all(f["delta"] == frames[0]["delta"] for f in frames):
                    tracks[j][kind] = []
        return {"formatVersion": 1, "duration": total, "holdLastKeyframe": self.hold,
                "nodeAnimations": {j: tr for j, tr in tracks.items()
                                   if tr["orientation"] or tr["position"]}}


# --- rendu logiciel (aperçus) ------------------------------------------------------------------

def world_boxes(root, pose):
    out = []

    def go(n, ppos, prot):
        rot, off = pose.get(n.name, ((0, 0, 0), (0, 0, 0))) if isinstance(n, Joint) else ((0, 0, 0), (0, 0, 0))
        lp = tuple(n.pos[i] + off[i] for i in range(3))
        wpos = tuple(ppos[i] + qrot(prot, lp)[i] for i in range(3))
        wrot = qmul(qmul(prot, n.rot), qeuler(*rot))
        if isinstance(n, Box):
            out.append((n, wpos, wrot))
        else:
            for c in n.children:
                go(c, wpos, wrot)

    go(root, (0, 0, 0), (0, 0, 0, 1))
    return out


FACE_DEFS = {
    "top": ((-1, 1, -1), (2, 0, 0), (0, 0, 2), (0, 1, 0)),
    "bottom": ((-1, -1, 1), (2, 0, 0), (0, 0, -2), (0, -1, 0)),
    "front": ((-1, 1, 1), (2, 0, 0), (0, -2, 0), (0, 0, 1)),
    "back": ((1, 1, -1), (-2, 0, 0), (0, -2, 0), (0, 0, -1)),
    "right": ((1, 1, 1), (0, 0, -2), (0, -2, 0), (1, 0, 0)),
    "left": ((-1, 1, -1), (0, 0, 2), (0, -2, 0), (-1, 0, 0)),
}


def render(root, atlas, uv, pose, size=320, yaw=30, pitch=15, scale=1.4, center=(0, 80, 0)):
    W = H = size
    zbuf = [[-1e9] * W for _ in range(H)]
    img = Image.new("RGBA", (W, H), (40, 44, 52, 255))
    px, tex = img.load(), atlas.load()
    light = (0.45, 0.8, 0.4)
    view_q = qmul(qaxis((1, 0, 0), pitch), qaxis((0, 1, 0), yaw))
    for b, wpos, wrot in world_boxes(root, pose):
        half = tuple(b.size[i] * b.stretch[i] / 2 for i in range(3))
        for f, (o, u, v, n) in FACE_DEFS.items():
            o = tuple(o[i] * half[i] for i in range(3))
            u = tuple(u[i] * half[i] for i in range(3))
            v = tuple(v[i] * half[i] for i in range(3))
            o, u, v, n = qrot(wrot, o), qrot(wrot, u), qrot(wrot, v), qrot(wrot, n)
            o = tuple(o[i] + wpos[i] for i in range(3))
            nv = qrot(view_q, n)
            if nv[2] <= 0 and not b.double:
                continue
            lum = 1.0 if b.shading == "fullbright" else 0.5 + 0.5 * max(0, sum(n[k] * light[k] for k in range(3)))
            fw, fh = face_size(b.size, f)
            tu, tv = uv[(b.name, f)]
            ul, vl = math.dist((0, 0, 0), u), math.dist((0, 0, 0), v)
            su, sv = max(2, int(ul * scale * 1.5) + 2), max(2, int(vl * scale * 1.5) + 2)
            for j in range(sv):
                fv = (j + 0.5) / sv
                for i in range(su):
                    fu = (i + 0.5) / su
                    p = tuple(o[k] + u[k] * fu + v[k] * fv - center[k] for k in range(3))
                    q = qrot(view_q, p)
                    sx, sy = int(W / 2 + q[0] * scale), int(H / 2 - q[1] * scale)
                    if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                        t = tex[min(tu + int(fu * max(1, math.ceil(fw))), atlas.width - 1),
                                min(tv + int(fv * max(1, math.ceil(fh))), atlas.height - 1)]
                        if t[3] < 128:
                            continue
                        zbuf[sy][sx] = q[2]
                        px[sx, sy] = shade(t, lum) + (255,)
    return img


# --- citrouille géante -------------------------------------------------------------------------

ORANGE = (226, 112, 26)
ORANGE_DARK = (150, 58, 14)
ORANGE_LIGHT = (250, 160, 60)
STEM = (92, 74, 40)
STEM_DARK = (58, 44, 24)
GLOW_HOT = (255, 236, 140)
GLOW = (255, 150, 30)
FLESH = (238, 150, 50)
VINE = (64, 128, 44)
VINE_DARK = (34, 74, 26)
VINE_LIGHT = (120, 186, 70)
THORN = (110, 40, 20)
THORN_TIP = (255, 176, 70)
EARTH = (84, 60, 40)

# Hauteur de la bouche (charnière du couvercle) et dimensions de la citrouille, en unités.
MOUTH_Y = 44
HINGE_Z = -60
FACE_W = 112


def mouth_top_edge(x):
    """Bord haut de la bouche sur la plaque du visage (rangée, 0 en haut) : un sourire."""
    t = (x - FACE_W / 2) / (FACE_W / 2 - 14)
    return 48 + 8 * (1 - t * t)


def face_features(w, h, glow):
    """Yeux, nez et moitié haute de la bouche ; glow=True : couleur de la lueur, ailleurs transparent."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill = (255, 255, 255, 255)
    for s in (-1, 1):
        cx = w / 2 + s * 28
        # Yeux en triangles inclinés (regard mauvais) : coin intérieur plus bas.
        d.polygon([(cx - 16, 20 - (0 if s < 0 else 6)), (cx + 16, 20 - (6 if s < 0 else 0)), (cx + s * 4, 40)], fill=fill)
    d.polygon([(w / 2 - 6, 38), (w / 2 + 6, 38), (w / 2, 30)], fill=fill)
    pts = [(x, mouth_top_edge(x)) for x in range(14, w - 13, 2)]
    d.polygon(pts + [(w - 14, h), (14, h)], fill=fill)
    # Dents du haut : triangles de chair qui pendent dans la bouche.
    for tx in (w / 2 - 22, w / 2, w / 2 + 22):
        d.polygon([(tx - 6, mouth_top_edge(tx) - 1), (tx + 6, mouth_top_edge(tx) - 1), (tx, h - 3)], fill=(0, 0, 0, 0))
    mask = img.split()[3]
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px, m = out.load(), mask.load()
    for y in range(h):
        for x in range(w):
            if m[x, y]:
                t = min(1.0, abs(y - 30) / 30)
                px[x, y] = mix(GLOW_HOT, GLOW, t) + (255,) if glow else shade(ORANGE_DARK, 0.6) + (255,)
    return out


def jaw_features(w, h, glow):
    """Moitié basse de la bouche sur la plaque de la mâchoire, avec deux dents du bas."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(x, 4 + 9 * (1 - ((x - w / 2) / (w / 2 - 14)) ** 2)) for x in range(14, w - 13, 2)]
    d.polygon([(14, 0), (w - 14, 0)] + pts[::-1], fill=(255, 255, 255, 255))
    for tx in (w / 2 - 11, w / 2 + 11):
        d.polygon([(tx - 6, 13), (tx + 6, 13), (tx, 1)], fill=(0, 0, 0, 0))
    m = img.split()[3].load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = out.load()
    for y in range(h):
        for x in range(w):
            if m[x, y]:
                px[x, y] = mix(GLOW_HOT, GLOW, min(1.0, y / 14)) + (255,) if glow else shade(ORANGE_DARK, 0.6) + (255,)
    return out


def p_face_plate(features):
    base = p_ribbed(ORANGE, ORANGE_DARK, ORANGE_LIGHT, period=14)

    def paint(rng, w, h, face):
        img = base(rng, w, h, face)
        if face == "front":
            img.alpha_composite(features(w, h, False))
        return img

    return paint


def p_glow_plate(features):
    def paint(rng, w, h, face):
        if face == "front":
            return features(w, h, True)
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    return paint


def pumpkin_model():
    skin = p_ribbed(ORANGE, ORANGE_DARK, ORANGE_LIGHT, period=7)
    inside = p_glow(FLESH, ORANGE_DARK)
    skin_lid = p_ribbed(ORANGE, ORANGE_DARK, ORANGE_LIGHT, period=7, inside=inside)
    jaw_h = MOUTH_Y - 6
    jaw = Joint("Jaw", (0, 0, 0), [
        Box("Jaw_Base", (0, 3, 0), (60, 3, 60), p_plain(ORANGE_DARK), stretch=2),
        Box("Jaw_Core", (0, 12 + (jaw_h - 6) / 2, 0), (75, (jaw_h - 6) / 2, 56), skin, stretch=2),
        Box("Jaw_Ring", (0, 9 + (jaw_h - 3) / 2, 0), (67, (jaw_h - 3) / 2, 67), skin, stretch=2),
        Box("Jaw_Cross", (0, 6 + jaw_h / 2, 0), (56, jaw_h / 2, 75), skin, stretch=2),
        Box("Jaw_Face", (0, 6 + jaw_h / 2, 75.5), (FACE_W, jaw_h, 1), p_face_plate(jaw_features)),
        Box("Jaw_Glow", (0, 6 + jaw_h / 2, 76.3), (FACE_W, jaw_h, 0.5), p_glow_plate(jaw_features), shading="fullbright"),
        Box("Mouth_Inside", (0, MOUTH_Y - 1, 0), (64, 2, 64), p_glow(GLOW_HOT, GLOW), stretch=(2, 1, 2), shading="fullbright"),
    ])
    lid_h = 60
    zc = -HINGE_Z  # centre de la citrouille vu de la charnière
    stem = Joint("Stem", (0, lid_h + 20, zc), [
        Box("Stem_Base", (0, 6, 0), (16, 14, 16), p_ribbed(STEM, STEM_DARK, (130, 110, 60), period=4)),
        Box("Stem_Top", (2, 18, 1), (12, 14, 12), p_ribbed(STEM, STEM_DARK, (130, 110, 60), period=4), rot=(8, 0, -14)),
        Box("Stem_Leaf_L", (16, 8, 4), (22, 1, 14), p_leaf(VINE, VINE_LIGHT), rot=(0, 30, -18), double=True),
        Box("Stem_Leaf_R", (-14, 6, -8), (20, 1, 12), p_leaf(VINE, VINE_LIGHT), rot=(0, -40, 22), double=True),
        Box("Stem_Curl", (-6, 3, 14), (4, 4, 18), p_plain(VINE), rot=(0, 30, 0)),
    ], rot=(0, 20, 0))
    head = Joint("Head", (0, MOUTH_Y, HINGE_Z), [
        Box("Head_Core", (0, (lid_h - 12) / 2, zc), (75, (lid_h - 12) / 2, 56), skin_lid, stretch=2),
        Box("Head_Ring", (0, (lid_h - 6) / 2, zc), (67, (lid_h - 6) / 2, 67), skin_lid, stretch=2),
        Box("Head_Cross", (0, lid_h / 2, zc), (56, lid_h / 2, 75), skin_lid, stretch=2),
        Box("Head_Top", (0, lid_h + 6, zc), (60, 6, 60), skin, stretch=2),
        Box("Head_Cap", (0, lid_h + 15, zc), (36, 3, 36), p_plain(ORANGE, top=1.0), stretch=2),
        Box("Head_Face", (0, lid_h / 2, zc + 75.5), (FACE_W, lid_h, 1), p_face_plate(face_features)),
        Box("Head_Glow", (0, lid_h / 2, zc + 76.3), (FACE_W, lid_h, 0.5), p_glow_plate(face_features), shading="fullbright"),
        stem,
    ])
    return Joint("Body", (0, 0, 0), [jaw, head])


PUMPKIN_JOINTS = ["Body", "Jaw", "Head", "Stem"]


def pumpkin_anims():
    def idle(t):
        u = t / 2.5
        chomp = keys(u, [(0, 0), (0.25, 0), (0.38, 14), (0.5, 2), (0.62, 9), (0.72, 0), (1, 0)])
        return {
            "Body": ((1.2 * math.sin(2 * math.pi * u), 2 * math.sin(2 * math.pi * u + 1), 1.5 * math.sin(4 * math.pi * u)),
                     (0, 1.2 * math.sin(4 * math.pi * u), 0)),
            "Head": ((-chomp, 0, 0), (0, 0, 0)),
            "Stem": ((0, 0, 6 * math.sin(2 * math.pi * u + 2)), (0, 0, 0)),
        }

    def spit(t):
        # 1 s de préparation (la citrouille se gonfle et tremble), crachat à 1 s, bouche refermée à 1,4 s.
        shake = math.sin(t * 60) * keys(t, [(0, 0), (0.9, 3), (1.0, 0)])
        back = keys(t, [(0, 0), (0.8, -10), (1.0, -10), (1.06, 12), (1.25, 4), (1.4, 0)])
        mouth = keys(t, [(0, 0), (0.3, 4), (0.95, 6), (1.03, 42), (1.2, 38), (1.4, 0)])
        lift = keys(t, [(0, 0), (0.9, 6), (1.05, -2), (1.4, 0)])
        return {"Body": ((back, shake, shake * 0.5), (0, lift, 0)), "Head": ((-mouth, 0, 0), (0, 0, 0)),
                "Stem": ((0, 0, -shake * 3), (0, 0, 0))}

    def roottrap(t):
        # 2,2 s de charge (elle s'enfonce en grondant, de plus en plus agitée), puis elle se soulève d'un coup.
        grow = keys(t, [(0, 0), (2.1, 1), (2.2, 0)])
        shake = math.sin(t * 50) * 4 * grow
        sink = keys(t, [(0, 0), (2.1, -10), (2.3, 10), (2.6, -3), (3.1, 0)])
        mouth = keys(t, [(0, 0), (0.4, 8), (2.1, 12), (2.25, 34), (2.7, 20), (3.1, 0)])
        return {"Body": ((keys(t, [(0, 0), (2.1, 8), (2.3, -6), (3.1, 0)]), shake, shake * 0.6), (0, sink, 0)),
                "Head": ((-mouth - abs(shake), 0, 0), (0, 0, 0)), "Stem": ((0, 0, shake * 2), (0, 0, 0))}

    def summon(t):
        # 0,8 s de bercement, rugissement à 0,8 s quand les vrilles sortent de terre.
        rock = math.sin(t * 2 * math.pi * 2.5) * keys(t, [(0, 0), (0.3, 8), (0.8, 8), (1.0, 0)])
        mouth = keys(t, [(0, 0), (0.6, 6), (0.85, 36), (1.2, 30), (1.5, 0)])
        return {"Body": ((keys(t, [(0, 0), (0.75, -6), (0.9, 6), (1.5, 0)]), 0, rock), (0, 0, 0)),
                "Head": ((-mouth, 0, 0), (0, 0, 0)), "Stem": ((0, 0, -rock * 2), (0, 0, 0))}

    def hurt(t):
        k = keys(t, [(0, 0), (0.08, 1), (0.3, 0)])
        return {"Body": ((-6 * k, 0, 0), (0, -3 * k, 0)), "Head": ((-10 * k, 0, 0), (0, 0, 0))}

    def death(t):
        mouth = keys(t, [(0, 0), (0.3, 50), (0.7, 58), (1.0, 64)])
        return {"Body": ((keys(t, [(0, 0), (1.0, 6)]), 0, keys(t, [(0, 0), (1.0, 12)])), (0, keys(t, [(0, 0), (0.4, 0), (1.0, -28)]), 0)),
                "Head": ((-mouth, 0, 0), (0, 0, 0)), "Stem": ((0, 0, keys(t, [(0, 0), (1.0, 40)])), (0, 0, 0))}

    return [
        Anim("Idle", 2.5, idle, step=6, loop=True),
        Anim("Hurt", 0.3, hurt, step=3),
        Anim("Death", 1.0, death, step=6, hold=True),
        Anim("Spit", 1.4, spit, step=2),
        Anim("RootTrap", 3.1, roottrap, step=3),
        Anim("Summon", 1.5, summon, step=3),
    ]


# --- vrille ------------------------------------------------------------------------------------

SEGMENTS = [  # (longueur, épaisseur, courbure au repos en degrés)
    (30, 26, 0),
    (28, 22, 4),
    (26, 19, 8),
    (24, 16, 8),
    (22, 13, 10),
    (20, 11, 12),
]


def vine_model():
    skin = p_ribbed(VINE, VINE_DARK, VINE_LIGHT, period=4, grad=0.3)
    thorn = p_thorn(THORN, THORN_TIP)
    leaf = p_leaf(VINE, VINE_LIGHT)
    tip = Joint("Tip", (0, SEGMENTS[-1][0], 0), [
        Box("Bud", (0, 10, 0), (18, 20, 18), p_ribbed((206, 98, 28), (120, 50, 16), (250, 160, 70), period=4), rot=(0, 45, 0)),
        Box("Bud_Hook", (0, 23, 5), (8, 16, 8), thorn, rot=(40, 0, 0)),
        Box("Bud_Fang_L", (9, 5, 5), (4, 16, 4), thorn, rot=(30, 0, -50)),
        Box("Bud_Fang_R", (-9, 5, 5), (4, 16, 4), thorn, rot=(30, 0, 50)),
        Box("Bud_Glow", (0, 11, 9.1), (8, 8, 1), p_glow(GLOW_HOT, GLOW), shading="fullbright", rot=(0, 0, 45)),
    ], rot=(10, 0, 0))
    child = tip
    for i in range(len(SEGMENTS), 0, -1):
        length, thick, bend = SEGMENTS[i - 1]
        parts = [Box(f"Seg{i}_Box", (0, length / 2, 0), (thick, length + 2, thick), skin)]
        # Épines en couronne, décalées d'un segment à l'autre.
        for k in range(3):
            a = (k * 120 + i * 50) % 360
            r = thick / 2 + 4
            x, z = r * math.sin(math.radians(a)), r * math.cos(math.radians(a))
            parts.append(Box(f"Seg{i}_Thorn{k}", (x, length * 0.55, z), (4, 12, 4), thorn, rot=(60, a, 0)))
        if i in (2, 4):
            s = 1 if i == 2 else -1
            parts.append(Box(f"Seg{i}_Leaf", (s * (thick / 2 + 12), length * 0.4, 0), (26, 1, 16), leaf, rot=(0, 0, s * 25), double=True))
        child = Joint(f"Seg{i}", (0, 8 if i == 1 else SEGMENTS[i - 2][0], 0), parts + [child], rot=(bend, 0, 0))
    mound = [
        Box("Mound", (0, 3, 0), (40, 6, 40), p_plain(EARTH, amp=0.18)),
        Box("Mound_Top", (0, 8, 0), (26, 5, 26), p_plain(EARTH, amp=0.18)),
        Box("Root_L", (17, 3, 6), (18, 4, 5), p_plain(VINE_DARK), rot=(0, 20, 12)),
        Box("Root_R", (-15, 3, -9), (16, 4, 5), p_plain(VINE_DARK), rot=(0, -35, -12)),
        Box("Root_B", (2, 3, -18), (5, 4, 16), p_plain(VINE_DARK), rot=(-10, 10, 0)),
    ]
    return Joint("Root", (0, 0, 0), mound + [child])


VINE_JOINTS = ["Root"] + [f"Seg{i}" for i in range(1, len(SEGMENTS) + 1)] + ["Tip"]


def vine_pose(rot_per_seg, root_rot=(0, 0, 0), root_off=(0, 0, 0), tip=(0, 0, 0)):
    pose = {"Root": (root_rot, root_off), "Tip": (tip, (0, 0, 0))}
    for i, r in enumerate(rot_per_seg, 1):
        pose[f"Seg{i}"] = (r, (0, 0, 0))
    return pose


def sway(t, amp_x, amp_z, speed=1.0):
    n = len(SEGMENTS)
    return [(amp_x * math.sin(2 * math.pi * speed * t - i * 0.7), 0, amp_z * math.sin(2 * math.pi * speed * t - i * 0.6 + 1.3))
            for i in range(n)]


def vine_anims():
    n = len(SEGMENTS)

    def idle(t):
        # Ondulation de serpent qui remonte la tige (boucle de 2 s).
        return vine_pose(sway(t / 2.0, 6, 5), root_rot=(0, 12 * math.sin(math.pi * t), 0),
                         tip=(8 * math.sin(math.pi * t * 2 + 1), 0, 0))

    def spawn(t):
        # Sort de terre en se déroulant (0,5 s).
        k = keys(t, [(0, 0), (0.5, 1)])
        return vine_pose([(35 * (1 - k), 0, 0)] * n, root_off=(0, -150 * (1 - k), 0))

    def hurt(t):
        k = keys(t, [(0, 0), (0.06, 1), (0.25, 0)])
        return vine_pose([(-10 * k, 0, 4 * k)] * n)

    def death(t):
        k = keys(t, [(0, 0), (0.6, 1)])
        sink = keys(t, [(0, 0), (0.35, 0), (0.8, -110)])
        return vine_pose([(14 * k + 6 * i * k, 0, 6 * k) for i in range(n)], root_off=(0, sink, 0))

    def strike(t):
        # Coup normal : elle se cabre (0,3 s) puis fouette vers l'avant et vers le bas.
        a = keys(t, [(0, 0), (0.3, -14), (0.38, 26), (0.5, 22), (0.8, 0)])
        return vine_pose([(a * (0.5 + 0.12 * i), 0, 0) for i in range(n)], tip=(a * 0.8, 0, 0))

    def throw(t):
        # Jet de ronces : elle se cabre puis donne deux coups de tête vers l'avant (épines à 0,5 s et 0,7 s).
        a = keys(t, [(0, 0), (0.42, -20), (0.52, 18), (0.6, -8), (0.72, 18), (0.9, 0)])
        return vine_pose([(a * (0.3 + 0.12 * i), 0, 0) for i in range(n)], tip=(a, 0, 0))

    def sweep(t):
        # Balayage : 1,2 s d'armement (elle se tord en arrière en tremblant), puis elle se couche au ras du sol
        # et fouette tout autour d'elle en un tour presque complet, avant de se redresser.
        shake = math.sin(t * 55) * keys(t, [(0, 0), (1.1, 4), (1.2, 0)])
        yaw = keys(t, [(0, 0), (1.15, -150), (1.2, -150), (1.42, 170), (1.9, 0)])
        low = keys(t, [(0, 0), (1.1, -0.25), (1.2, 1), (1.45, 1), (1.75, 0)])
        segs = []
        for i in range(n):
            if low >= 0:
                x = low * (50 if i == 0 else 15 if i == 1 else -6)
            else:
                x = low * 40
            segs.append((x + shake, 0, shake * 0.5 + (keys(t, [(0, 0), (1.1, 10), (1.2, 0)]) if i > 1 else 0)))
        return vine_pose(segs, root_rot=(0, yaw, 0), tip=(low * 20, 0, 0))

    return [
        Anim("Idle", 2.0, idle, step=6, loop=True),
        Anim("Spawn", 0.5, spawn, step=3),
        Anim("Hurt", 0.25, hurt, step=3),
        Anim("Death", 0.8, death, step=4, hold=True),
        Anim("Strike", 0.8, strike, step=2),
        Anim("Throw", 0.9, throw, step=2),
        Anim("Sweep", 1.9, sweep, step=2),
    ]


# --- écriture ----------------------------------------------------------------------------------

def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def anim_entry(path, **extra):
    return {"Animations": [dict({"Animation": path}, **extra)]}


def item_animations(base, names):
    return {
        "$Comment": "Animations d'attaque jouées par les interactions (Effects.ItemAnimationId), générées par tools/generate_pumpkin_models.py.",
        "Animations": {n: {"ThirdPerson": f"{base}/Animations/{n}.blockyanim", "Looping": False, "Speed": 1} for n in names},
        "WiggleWeights": {"Pitch": 0, "PitchDeceleration": 0.1, "Roll": 0, "RollDeceleration": 0.1,
                          "X": 0, "XDeceleration": 0.1, "Y": 0, "YDeceleration": 0.1, "Z": 0, "ZDeceleration": 0.1},
    }


def build(key, root, joints, anims, seed, tex_w, model_doc, attacks, preview, previews):
    base = f"NPC/Nakasar/{key}"
    atlas, uv = build_atlas(root, seed, tex_w)
    out = COMMON / base
    out.mkdir(parents=True, exist_ok=True)
    atlas.save(out / "Texture.png")
    write_json(out / "Model.blockymodel", model_json(root, uv))
    for a in anims:
        write_json(out / "Animations" / f"{a.name}.blockyanim", a.to_json(joints))
    model_doc = dict(model_doc)
    model_doc["Model"] = f"{base}/Model.blockymodel"
    model_doc["Texture"] = f"{base}/Texture.png"
    sets = {}
    for a in anims:
        if a.name in attacks:
            continue
        extra = {} if a.loop else {"Looping": False}
        sets[a.name] = anim_entry(f"{base}/Animations/{a.name}.blockyanim", **extra)
    model_doc["AnimationSets"] = sets
    write_json(SERVER / "Models" / "Nakasar" / f"Nakasar_{key}.json", model_doc)
    write_json(SERVER / "Item" / "Animations" / "Nakasar" / f"Nakasar_{key}.json", item_animations(base, attacks))
    print(f"{base} : {len(list(walk(root)))} nœuds, texture {atlas.width}x{atlas.height}, {len(anims)} animations")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        anim_by_name = {a.name: a for a in anims}
        tiles = []
        for label, name, t, view in previews:
            pose = anim_by_name[name].pose(t) if name else {}
            tiles.append(render(root, atlas, uv, pose, **view))
        sheet = Image.new("RGBA", (sum(t.width for t in tiles), tiles[0].height))
        x = 0
        for tile in tiles:
            sheet.paste(tile, (x, 0))
            x += tile.width
        sheet.save(preview / f"{key}.png")
        atlas.resize((atlas.width * 2, atlas.height * 2), Image.NEAREST).save(preview / f"{key}_texture.png")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    pumpkin_view = {"size": 300, "scale": 1.3, "center": (0, 60, 0)}
    build("Giant_Pumpkin", pumpkin_model(), PUMPKIN_JOINTS, pumpkin_anims(), 41, 256, {
        "$Comment": "Citrouille géante animée (élite), générée par tools/generate_pumpkin_models.py : sculptée, éclairée de l'intérieur ; le haut se soulève comme une mâchoire (bouche qui s'ouvre, crachat de poison, rugissements). Elle ne se déplace pas.",
        "EyeHeight": 0.9,
        "HitBox": {"Max": {"X": 1.15, "Y": 2.1, "Z": 1.15}, "Min": {"X": -1.15, "Y": 0, "Z": -1.15}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#ff8a1c", "Radius": 10},
    }, ["Spit", "RootTrap", "Summon"], preview, [
        ("repos", None, 0, pumpkin_view),
        ("face", None, 0, dict(pumpkin_view, yaw=0, pitch=5)),
        ("crachat", "Spit", 1.08, dict(pumpkin_view, yaw=0, pitch=5)),
        ("crachat 3/4", "Spit", 1.1, pumpkin_view),
        ("piège", "RootTrap", 2.3, pumpkin_view),
        ("mort", "Death", 1.0, pumpkin_view),
    ])
    vine_view = {"size": 300, "scale": 1.3, "center": (0, 85, 0)}
    build("Pumpkin_Vine", vine_model(), VINE_JOINTS, vine_anims(), 43, 128, {
        "$Comment": "Vrille combattante de la citrouille géante, générée par tools/generate_pumpkin_models.py : tige épineuse articulée de 2,8 blocs, sortie d'un monticule de terre, bourgeon lumineux au bout.",
        "EyeHeight": 2.2,
        "HitBox": {"Max": {"X": 0.4, "Y": 2.7, "Z": 0.4}, "Min": {"X": -0.4, "Y": 0, "Z": -0.4}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#ff9a3c", "Radius": 4},
    }, ["Strike", "Throw", "Sweep"], preview, [
        ("repos", None, 0, vine_view),
        ("idle", "Idle", 0.5, vine_view),
        ("coup", "Strike", 0.38, dict(vine_view, yaw=90, pitch=5)),
        ("jet", "Throw", 0.42, dict(vine_view, yaw=90, pitch=5)),
        ("balayage", "Sweep", 1.3, dict(vine_view, pitch=25, center=(0, 40, 0))),
        ("mort", "Death", 0.6, vine_view),
    ])


if __name__ == "__main__":
    main()
