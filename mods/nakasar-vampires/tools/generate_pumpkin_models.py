#!/usr/bin/env python3
"""Génère les modèles animés de la citrouille géante et de ses vrilles combattantes.

    python3 mods/nakasar-vampires/tools/generate_pumpkin_models.py [--preview DOSSIER]

- Common/NPC/Nakasar/Giant_Pumpkin/ : citrouille sculptée de 2,3 blocs de large faite de huit côtes en
  relief, coupée au niveau de la bouche. Le haut (« Head ») pivote sur une charnière à l'arrière : la
  bouche s'ouvre et se ferme et laisse voir l'intérieur rougeoyant. Yeux, nez et bouche sont découpés
  sur les trois côtes de face (plaques « Glow » en fullbright, transparentes hors des découpes, bord
  de chair peint autour), avec des dents en relief ; tige recourbée, grandes feuilles et vrilles.
- Common/NPC/Nakasar/Pumpkin_Vine/ : vrille épineuse de 3 blocs de haut sortant d'une motte de terre :
  huit segments octogonaux qui s'affinent, épines et feuilles découpées (plaques croisées), et au bout
  une fleur de citrouille dont les quatre pétales s'ouvrent sur un cœur lumineux.
- Animations (.blockyanim, 60 images par seconde) : repos, apparition, blessure, mort, et une par
  attaque. Les animations d'attaque sont jouées par les interactions (Effects.ItemAnimationId) via
  les jeux Server/Item/Animations/Nakasar/<modèle>.json ; leur durée suit celle des interactions.
  Les états de déplacement (Walk, Fall…) rejouent le repos : un PNJ immobile n'est jamais figé.
- Server/Models/Nakasar/Nakasar_Giant_Pumpkin.json et Nakasar_Pumpkin_Vine.json : modèles (hitbox,
  lumière, AnimationSets).

Repère : format « character », 64 unités = 1 bloc, origine au sol, face avant vers +Z. Les
articulations sont des nœuds sans forme ; les boîtes sont des feuilles centrées sur leur position.
Une rotation positive autour de X penche le haut d'un nœud vers l'avant (+Z). Les textures sont
peintes en dégradés doux (formes arrondies, comme les modèles vanilla), sans grain.

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
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def soft_noise(rng, w, h, scale=8, amp=0.04):
    """Variations très douces (taches larges), pour casser l'uniformité sans grain."""
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
            c = f(x, y)
            px[x, y] = c if len(c) == 4 else c + (255,)
    return img


def p_round(base, dark, light, top=None, bottom=None, streaks=0, amp=0.04):
    """Peinture « arrondie » : chaque face est claire au centre et sombre vers ses bords (comme un
    cylindre éclairé), un peu plus claire en haut. streaks : fines nervures sombres dans la longueur."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=amp)
        lines = [rng.uniform(0.15, 0.85) for _ in range(streaks)]
        if face in ("top", "bottom"):
            cap = top if face == "top" else bottom
            cx, cy = (w - 1) / 2, (h - 1) / 2

            def c(x, y):
                r = max(abs(x - cx) / max(1, cx), abs(y - cy) / max(1, cy))
                col = mix(cap or light, dark, r ** 2 * 0.8) if face == "top" else mix(cap or dark, dark, 0.5)
                return shade(col, n[y][x])

            return solid(Image.new("RGBA", (w, h)), c)

        def c(x, y):
            u = (x + 0.5) / w
            v = (y + 0.5) / h
            k = math.sin(math.pi * u)  # 0 aux bords, 1 au centre
            col = mix(dark, base, min(1.0, k * 1.5))
            col = mix(col, light, max(0.0, k - 0.8) * 2.5 * (1.1 - v))
            for s in lines:
                if abs(u - s) < 0.5 / max(4, w):
                    col = mix(col, dark, 0.45)
            return shade(col, (1.06 - 0.16 * v) * n[y][x])

        return solid(Image.new("RGBA", (w, h)), c)

    return paint


def p_glow(c0, c1):
    """Lueur : dégradé du cœur (c0) vers le bord (c1)."""

    def paint(rng, w, h, face):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        return solid(Image.new("RGBA", (w, h)),
                     lambda x, y: mix(c0, c1, math.hypot((x - cx) / max(1, cx), (y - cy) / max(1, cy))))

    return paint


def p_plate(shape, color, axis="z"):
    """Plaque découpée (feuille, épine, pétale) : la forme est peinte sur les deux grandes faces
    (front/back si axis="z", top/bottom si axis="y", right/left si axis="x"), le reste est transparent.
    shape(u, v) -> bool, color(u, v) -> couleur, u et v entre 0 et 1 (v = 0 en haut / à la pointe)."""
    faces = {"z": ("front", "back"), "y": ("top", "bottom"), "x": ("right", "left")}[axis]

    def paint(rng, w, h, face):
        if face not in faces:
            return Image.new("RGBA", (w, h), (0, 0, 0, 0))
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        f = 1.0 if face == faces[0] else 0.8
        for y in range(h):
            for x in range(w):
                u, v = (x + 0.5) / w, (y + 0.5) / h
                if face == faces[1] and axis != "y":
                    u = 1 - u
                if shape(u, v):
                    px[x, y] = shade(color(u, v), f) + (255,)
        return img

    return paint


def leaf_shape(u, v):
    """Feuille pointue (pointe en v = 0), large au tiers bas, bord légèrement dentelé."""
    half = 0.5 * math.sin(math.pi * min(1.0, (1 - v) * 1.15)) ** 0.8
    half *= 1 - 0.08 * (math.sin(v * 22) > 0.6)
    return abs(u - 0.5) < half


def leaf_color(base, vein, dark):
    def c(u, v):
        d = abs(u - 0.5)
        col = mix(base, dark, d * 1.4 + v * 0.2)
        if d < 0.035 or (abs(d - (1 - v) * 0.35 + 0.05) < 0.03 and v > 0.25):
            col = mix(col, vein, 0.6)
        return col

    return c


def thorn_shape(u, v):
    """Épine : triangle effilé, pointe en v = 0."""
    return abs(u - 0.5) < 0.5 * v ** 1.2


def petal_shape(u, v):
    """Pétale : goutte pointue (pointe en v = 0), arrondie en bas."""
    return abs(u - 0.5) < 0.5 * math.sin(math.pi * min(1.0, (1 - v) * 0.62 + 0.1)) * min(1.0, v * 3 + 0.25)


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


# --- palette -----------------------------------------------------------------------------------

ORANGE = (232, 120, 30)
ORANGE_DARK = (150, 56, 14)
ORANGE_LIGHT = (255, 178, 74)
FLESH = (250, 198, 100)
FLESH_DARK = (190, 112, 36)
GLOW_HOT = (255, 242, 160)
GLOW = (255, 150, 30)
STEM = (110, 88, 46)
STEM_DARK = (60, 46, 24)
STEM_LIGHT = (160, 136, 76)
LEAF = (82, 146, 50)
LEAF_DARK = (36, 82, 28)
LEAF_VEIN = (160, 208, 96)
VINE = (72, 136, 46)
VINE_DARK = (30, 72, 24)
VINE_LIGHT = (136, 196, 80)
THORN = (92, 34, 18)
THORN_TIP = (255, 196, 96)
EARTH = (96, 68, 44)
EARTH_DARK = (52, 38, 26)
EARTH_LIGHT = (134, 100, 68)
PETAL = (255, 170, 50)
PETAL_DARK = (196, 84, 20)


def on_surface(r, t, a_deg):
    """Point à la distance r du centre dans la direction a (degrés depuis +Z), décalé de t le long de la tangente."""
    a = math.radians(a_deg)
    return (r * math.sin(a) + t * math.cos(a), r * math.cos(a) - t * math.sin(a))


def leaf(name, base, angle, length, width, lift=8, roll=0, tex=None):
    """Feuille posée à plat, pointe dirigée vers angle (degrés depuis +Z), base en base."""
    x, z = on_surface(length / 2, 0, angle)
    return Box(name, (base[0] + x, base[1], base[2] + z), (width, 0.6, length),
               p_plate(leaf_shape, tex or leaf_color(LEAF, LEAF_VEIN, LEAF_DARK), axis="y"),
               rot=(lift, angle + 180, roll), double=True)


def thorn(name, pos, angle, tilt=55, size=(8, 14)):
    """Épine en deux plaques croisées, pointe dirigée vers l'extérieur (angle) et vers le haut."""
    color = lambda u, v: mix(THORN_TIP, THORN, v ** 0.7)
    return [
        Box(name + "_A", pos, (size[0], size[1], 0.4), p_plate(thorn_shape, color, axis="z"), rot=(tilt, angle, 0), double=True),
        Box(name + "_B", pos, (0.4, size[1], size[0]), p_plate(thorn_shape, color, axis="x"), rot=(tilt, angle, 0), double=True),
    ]


# --- citrouille géante -------------------------------------------------------------------------

MOUTH_Y = 44
HINGE = (0, MOUTH_Y, -70)
LOBE_W, LOBE_D, LOBE_RC = 60, 40, 50  # largeur, épaisseur, rayon du centre : surface à 70 unités
FACE_LOBES = {0: 0, 1: 1, 7: -1}  # côte -> rang sur le visage (-1 à gauche, 0 au centre, 1 à droite)


def mouth_top(u):
    return 49 + 9 * (u / 66) ** 2


def mouth_bottom(u):
    return 30 + 12 * (u / 66) ** 2


def face_canvas():
    """Découpes du visage dans le repère « déroulé » des côtes de face : u de -90 à 90 (le long du tour),
    y de 0 à 128 (hauteur). Renvoie (masque des découpes, masque du bord de chair)."""
    w, h = 180, 128
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    to = lambda u, y: (u + 90, h - y)
    for s in (-1, 1):
        d.polygon([to(s * 22, 75), to(s * 58, 83), to(s * 42, 60)], fill=255)
    d.polygon([to(-7, 58), to(7, 58), to(0, 68)], fill=255)
    top = [to(u, mouth_top(u)) for u in range(-66, 67, 2)]
    bottom = [to(u, mouth_bottom(u)) for u in range(66, -67, -2)]
    d.polygon(top + bottom, fill=255)
    rim = img.filter(ImageFilter.MaxFilter(7))
    return img.load(), rim.load()


FACE_MASK, FACE_RIM = face_canvas()


def face_at(u, y):
    """0 : peau, 1 : bord de chair, 2 : découpe."""
    x, r = int(round(u + 90)), int(round(128 - y))
    if not (0 <= x < 180 and 0 <= r < 128):
        return 0
    return 2 if FACE_MASK[x, r] else 1 if FACE_RIM[x, r] else 0


def p_lobe(rank, y0, y1, top=None, bottom=None):
    """Côte de citrouille ; sur les côtes de face (rank), le visage est creusé dans la face avant."""
    base = p_round(ORANGE, ORANGE_DARK, ORANGE_LIGHT, top=top, bottom=bottom)

    def paint(rng, w, h, face):
        img = base(rng, w, h, face)
        if rank is None or face != "front":
            return img
        px = img.load()
        for r in range(h):
            for x in range(w):
                u = rank * LOBE_W + (x + 0.5) / w * LOBE_W - LOBE_W / 2
                y = y1 - (r + 0.5) / h * (y1 - y0)
                k = face_at(u, y)
                if k == 1:
                    px[x, r] = mix(FLESH, FLESH_DARK, 0.25) + (255,)
                elif k == 2:
                    px[x, r] = FLESH_DARK + (255,)
        return img

    return paint


def p_face_glow(rank, y0, y1):
    """Lueur des découpes (plaque fullbright posée sur la côte), transparente ailleurs."""

    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if face != "front":
            return img
        px = img.load()
        for r in range(h):
            for x in range(w):
                u = rank * LOBE_W + (x + 0.5) / w * LOBE_W - LOBE_W / 2
                y = y1 - (r + 0.5) / h * (y1 - y0)
                if face_at(u, y) == 2:
                    px[x, r] = mix(GLOW_HOT, GLOW, min(1.0, abs(y - 56) / 30)) + (255,)
        return img

    return paint


def lobes(prefix, k_range, y0, y1, rc, w, d, paint_for, offset=(0, 0, 0), stretch=2):
    out = []
    for k in k_range:
        a = k * 45
        x, z = on_surface(rc, 0, a)
        out.append(Box(f"{prefix}{k}", (x - offset[0], (y0 + y1) / 2 - offset[1], z - offset[2]),
                       (w / stretch, (y1 - y0) / stretch, d / stretch), paint_for(k), stretch=stretch, rot=(0, a, 0)))
    return out


def teeth(prefix, us, y_of, up, offset):
    """Dents en relief au bord de la bouche (losanges dont une moitié dépasse)."""
    out = []
    for i, u in enumerate(us):
        rank = max(-1, min(1, round(u / LOBE_W)))
        x, z = on_surface(LOBE_RC + LOBE_D / 2 + 0.5, u - rank * LOBE_W, rank * 45)
        y = y_of(u) + (-1 if up else 1)
        out.append(Box(f"{prefix}{i}", (x - offset[0], y - offset[1], z - offset[2]), (12, 12, 9),
                       p_round((255, 214, 120), (226, 150, 60), (255, 240, 190)), rot=(0, rank * 45, 45)))
    return out


def pumpkin_model():
    rank = lambda k: FACE_LOBES.get(k)
    plain = lambda **kw: (lambda k: p_lobe(None, 0, 0, **kw))
    jaw = Joint("Jaw", (0, 0, 0), [
        *lobes("Jaw_Foot", range(8), 0, 8, 38, 42, 32, plain()),
        *lobes("Jaw_Hip", range(8), 6, 20, 46, 54, 38, plain()),
        *lobes("Jaw_Lobe", range(8), 18, MOUTH_Y, LOBE_RC, LOBE_W, LOBE_D,
               lambda k: p_lobe(rank(k), 18, MOUTH_Y, top=FLESH)),
        Box("Jaw_Core", (0, (8 + MOUTH_Y) / 2, 0), (48, (MOUTH_Y - 8) / 2, 48), p_round(ORANGE, ORANGE_DARK, FLESH, top=FLESH),
            stretch=2, rot=(0, 22.5, 0)),
        Box("Mouth_Inside", (0, MOUTH_Y, 0), (45, 1, 45), p_glow(GLOW_HOT, GLOW), stretch=(2, 2, 2), rot=(0, 22.5, 0), shading="fullbright"),
        *[Box(f"Jaw_Glow{k}", (on_surface(LOBE_RC + LOBE_D / 2 + 0.3, 0, k * 45)[0], (18 + MOUTH_Y) / 2,
                                on_surface(LOBE_RC + LOBE_D / 2 + 0.3, 0, k * 45)[1]),
              (LOBE_W, MOUTH_Y - 18, 0.4), p_face_glow(r, 18, MOUTH_Y), rot=(0, k * 45, 0), shading="fullbright")
          for k, r in FACE_LOBES.items()],
        *teeth("Jaw_Tooth", (-28, 0, 28), mouth_bottom, True, (0, 0, 0)),
    ])
    lid_top = 86
    head_parts = [
        *lobes("Head_Lobe", range(8), MOUTH_Y, lid_top, LOBE_RC, LOBE_W, LOBE_D,
               lambda k: p_lobe(rank(k), MOUTH_Y, lid_top, bottom=FLESH_DARK), offset=HINGE),
        *lobes("Head_Shoulder", range(8), lid_top - 2, 100, 46, 54, 38, plain(top=ORANGE_LIGHT), offset=HINGE),
        *lobes("Head_Crown", range(8), 98, 110, 38, 44, 32, plain(top=ORANGE_LIGHT), offset=HINGE),
        Box("Head_Core", (0, (MOUTH_Y + 106) / 2 - HINGE[1], -HINGE[2]), (48, 31, 48),
            p_round(ORANGE, ORANGE_DARK, ORANGE_LIGHT, bottom=FLESH_DARK), stretch=2, rot=(0, 22.5, 0)),
        Box("Head_Cap", (0, 111 - HINGE[1], -HINGE[2]), (42, 5, 42), p_round(ORANGE, ORANGE_DARK, ORANGE_LIGHT), stretch=2, rot=(0, 22.5, 0)),
        Box("Head_Cap2", (0, 116 - HINGE[1], -HINGE[2]), (24, 3, 24), p_round(ORANGE, ORANGE_DARK, ORANGE_LIGHT), stretch=2),
        *[Box(f"Head_Glow{k}", (on_surface(LOBE_RC + LOBE_D / 2 + 0.3, 0, k * 45)[0], (MOUTH_Y + lid_top) / 2 - HINGE[1],
                                 on_surface(LOBE_RC + LOBE_D / 2 + 0.3, 0, k * 45)[1] - HINGE[2]),
              (LOBE_W, lid_top - MOUTH_Y, 0.4), p_face_glow(r, MOUTH_Y, lid_top), rot=(0, k * 45, 0), shading="fullbright")
          for k, r in FACE_LOBES.items()],
        *teeth("Head_Tooth", (-42, -14, 14, 42), mouth_top, False, HINGE),
    ]
    stem_paint = p_round(STEM, STEM_DARK, STEM_LIGHT, top=STEM_LIGHT, streaks=2)
    stem_c = Joint("Stem_C", (0, 13, 0), [
        Box("Stem_C_Box", (0, 5, 0), (9, 12, 9), stem_paint),
        Box("Stem_Tip", (0, 12, 0), (6, 5, 6), stem_paint, rot=(0, 30, 0)),
    ], rot=(0, 0, -38))
    stem_b = Joint("Stem_B", (0, 15, 0), [Box("Stem_B_Box", (0, 7, 0), (12, 16, 12), stem_paint), stem_c], rot=(4, 0, -22))
    curl, parent = None, None
    for i in range(6, 0, -1):
        kids = [Box(f"Curl{i}_Box", (0, 0, 4.5), (3.5, 3.5, 11), p_round(VINE, VINE_DARK, VINE_LIGHT))]
        if curl:
            kids.append(curl)
        curl = Joint(f"Curl{i}", (0, 0, 9) if i > 1 else (6, 2, -8), kids, rot=(-6 if i > 1 else 10, 48 if i > 1 else -150, 0))
    stem = Joint("Stem", (0, 118 - HINGE[1], -HINGE[2]), [
        Box("Stem_A", (0, 8, 0), (17, 18, 17), stem_paint, rot=(4, 0, -6)),
        stem_b,
        leaf("Leaf_Big", (6, 2, 4), 70, 54, 34, lift=-14, roll=6),
        leaf("Leaf_Back", (-4, 2, -6), 215, 46, 30, lift=-18, roll=-8),
        leaf("Leaf_Small", (-6, 3, 6), 320, 30, 20, lift=-6),
        curl,
    ], rot=(0, 20, 0))
    head = Joint("Head", HINGE, head_parts + [stem])
    return Joint("Body", (0, 0, 0), [jaw, head])


PUMPKIN_JOINTS = ["Body", "Jaw", "Head", "Stem", "Stem_B", "Stem_C", "Curl1", "Curl3", "Curl5"]


def pumpkin_anims():
    def idle(t):
        u = t / 2.5
        chomp = keys(u, [(0, 0), (0.25, 0), (0.38, 14), (0.5, 2), (0.62, 9), (0.72, 0), (1, 0)])
        sway = math.sin(2 * math.pi * u)
        return {
            "Body": ((1.2 * sway, 2 * math.sin(2 * math.pi * u + 1), 1.5 * math.sin(4 * math.pi * u)),
                     (0, 1.2 * math.sin(4 * math.pi * u), 0)),
            "Head": ((-chomp, 0, 0), (0, 0, 0)),
            "Stem": ((0, 0, 4 * math.sin(2 * math.pi * u + 2)), (0, 0, 0)),
            "Stem_B": ((0, 0, 5 * math.sin(2 * math.pi * u + 2.6)), (0, 0, 0)),
            "Stem_C": ((0, 0, 7 * math.sin(2 * math.pi * u + 3.2)), (0, 0, 0)),
            "Curl1": ((4 * math.sin(2 * math.pi * u), 0, 0), (0, 0, 0)),
            "Curl3": ((0, 6 * math.sin(2 * math.pi * u + 1), 0), (0, 0, 0)),
            "Curl5": ((0, 8 * math.sin(2 * math.pi * u + 2), 0), (0, 0, 0)),
        }

    def stem_shake(s):
        return {"Stem": ((0, 0, -s * 2), (0, 0, 0)), "Stem_B": ((0, 0, -s * 3), (0, 0, 0)), "Stem_C": ((0, 0, -s * 4), (0, 0, 0)),
                "Curl3": ((0, s * 5, 0), (0, 0, 0))}

    def spit(t):
        # 1 s de préparation (la citrouille se gonfle et tremble), crachat à 1 s, bouche refermée à 1,4 s.
        shake = math.sin(t * 60) * keys(t, [(0, 0), (0.9, 3), (1.0, 0)])
        back = keys(t, [(0, 0), (0.8, -10), (1.0, -10), (1.06, 12), (1.25, 4), (1.4, 0)])
        mouth = keys(t, [(0, 0), (0.3, 4), (0.95, 6), (1.03, 42), (1.2, 38), (1.4, 0)])
        lift = keys(t, [(0, 0), (0.9, 6), (1.05, -2), (1.4, 0)])
        return {"Body": ((back, shake, shake * 0.5), (0, lift, 0)), "Head": ((-mouth, 0, 0), (0, 0, 0)), **stem_shake(shake)}

    def roottrap(t):
        # 2,2 s de charge (elle s'enfonce en grondant, de plus en plus agitée), puis elle se soulève d'un coup.
        grow = keys(t, [(0, 0), (2.1, 1), (2.2, 0)])
        shake = math.sin(t * 50) * 4 * grow
        sink = keys(t, [(0, 0), (2.1, -10), (2.3, 10), (2.6, -3), (3.1, 0)])
        mouth = keys(t, [(0, 0), (0.4, 8), (2.1, 12), (2.25, 34), (2.7, 20), (3.1, 0)])
        return {"Body": ((keys(t, [(0, 0), (2.1, 8), (2.3, -6), (3.1, 0)]), shake, shake * 0.6), (0, sink, 0)),
                "Head": ((-mouth - abs(shake), 0, 0), (0, 0, 0)), **stem_shake(shake)}

    def summon(t):
        # 0,8 s de bercement, rugissement à 0,8 s quand les vrilles sortent de terre.
        rock = math.sin(t * 2 * math.pi * 2.5) * keys(t, [(0, 0), (0.3, 8), (0.8, 8), (1.0, 0)])
        mouth = keys(t, [(0, 0), (0.6, 6), (0.85, 36), (1.2, 30), (1.5, 0)])
        return {"Body": ((keys(t, [(0, 0), (0.75, -6), (0.9, 6), (1.5, 0)]), 0, rock), (0, 0, 0)),
                "Head": ((-mouth, 0, 0), (0, 0, 0)), **stem_shake(rock)}

    def hurt(t):
        k = keys(t, [(0, 0), (0.08, 1), (0.3, 0)])
        return {"Body": ((-6 * k, 0, 0), (0, -3 * k, 0)), "Head": ((-10 * k, 0, 0), (0, 0, 0)), **stem_shake(4 * k)}

    def death(t):
        mouth = keys(t, [(0, 0), (0.3, 50), (0.7, 58), (1.0, 64)])
        return {"Body": ((keys(t, [(0, 0), (1.0, 6)]), 0, keys(t, [(0, 0), (1.0, 12)])), (0, keys(t, [(0, 0), (0.4, 0), (1.0, -28)]), 0)),
                "Head": ((-mouth, 0, 0), (0, 0, 0)), "Stem_B": ((0, 0, keys(t, [(0, 0), (1.0, -30)])), (0, 0, 0)),
                "Stem_C": ((0, 0, keys(t, [(0, 0), (1.0, -30)])), (0, 0, 0))}

    return [
        Anim("Idle", 2.5, idle, step=6, loop=True),
        Anim("Hurt", 0.3, hurt, step=3),
        Anim("Death", 1.0, death, step=6, hold=True),
        Anim("Spit", 1.4, spit, step=2),
        Anim("RootTrap", 3.1, roottrap, step=3),
        Anim("Summon", 1.5, summon, step=3),
    ]


# --- vrille ------------------------------------------------------------------------------------

SEGMENTS = [  # (longueur, épaisseur, courbure au repos autour de X puis de Z, en degrés)
    (22, 28, 0, 0),
    (21, 25, 4, 3),
    (21, 22, 6, -4),
    (20, 19, 6, 4),
    (19, 16, 8, -3),
    (18, 14, 8, 3),
    (17, 12, 10, -2),
    (16, 10, 10, 2),
]
PETALS = 4


def vine_model():
    skin = p_round(VINE, VINE_DARK, VINE_LIGHT, top=VINE_LIGHT, streaks=2)
    earth = p_round(EARTH, EARTH_DARK, EARTH_LIGHT, top=EARTH_LIGHT, amp=0.08)
    root_paint = p_round(VINE_DARK, (24, 50, 20), VINE)
    petal_color = lambda u, v: mix(mix(PETAL_DARK, PETAL, v * 1.3), PETAL_DARK, abs(u - 0.5) * 1.2)
    petals = [Joint(f"Petal{j}", (0, 9, 0), [
        Box(f"Petal{j}_Leaf", (0, 11, 3), (17, 24, 0.5), p_plate(petal_shape, petal_color, axis="z"), double=True),
    ], rot=(28, 45 + 90 * j, 0)) for j in range(PETALS)]
    tip = Joint("Tip", (0, SEGMENTS[-1][0], 0), [
        Box("Bud_Base", (0, 4, 0), (15, 10, 15), skin, rot=(0, 20, 0)),
        Box("Bud_Core", (0, 12, 0), (8, 8, 8), p_glow(GLOW_HOT, GLOW), shading="fullbright", rot=(0, 45, 0)),
        *[Box(f"Bud_Inner{j}", (on_surface(3, 0, 90 * j)[0], 13, on_surface(3, 0, 90 * j)[1]), (10, 14, 0.5),
              p_plate(petal_shape, lambda u, v: mix(PETAL, (255, 220, 120), 1 - v), axis="z"), rot=(12, 90 * j, 0), double=True)
          for j in range(PETALS)],
        *petals,
    ], rot=(12, 0, 0))
    child = tip
    for i in range(len(SEGMENTS), 0, -1):
        length, thick, bx, bz = SEGMENTS[i - 1]
        twist = 17 * i
        parts = [
            Box(f"Seg{i}_Box", (0, length / 2, 0), (thick, length + 4, thick), skin, rot=(0, twist, 0)),
            Box(f"Seg{i}_Edge", (0, length / 2, 0), (thick * 0.8, length + 3, thick * 0.8), skin, rot=(0, twist + 45, 0)),
        ]
        if i <= len(SEGMENTS) - 2:
            for k in range(2):
                a = (k * 180 + i * 70) % 360
                x, z = on_surface(thick / 2 + 3, 0, a)
                size = (11, 18) if i < 4 else (8, 13)
                parts += thorn(f"Seg{i}_Thorn{k}", (x, length * (0.35 + 0.3 * k), z), a, size=size)
        if i in (2, 4, 6):
            a = (i * 95) % 360
            x, z = on_surface(thick / 2, 0, a)
            parts.append(leaf(f"Seg{i}_Leaf", (x, length * 0.4, z), a, 30 - i * 2, 18 - i, lift=12))
        child = Joint(f"Seg{i}", (0, 10 if i == 1 else SEGMENTS[i - 2][0], 0), parts + [child], rot=(bx, 0, bz))
    mound = [
        Box("Mound", (0, 3, 0), (44, 8, 40), earth, rot=(0, 15, 0)),
        Box("Mound_Top", (2, 9, -1), (30, 8, 30), earth, rot=(4, 40, 3)),
    ]
    for j in range(4):
        a = 30 + 90 * j
        x, z = on_surface(17, 0, a)
        mound.append(Box(f"Root{j}", (x, 4, z), (7, 6, 22), root_paint, rot=(14, a, 0)))
        x, z = on_surface(29, 0, a + 12)
        mound.append(Box(f"Root{j}_End", (x, 1.5, z), (5, 4, 14), root_paint, rot=(10, a + 12, 0)))
    mound.append(leaf("Ground_Leaf0", (12, 2, 8), 60, 30, 18, lift=-4))
    mound.append(leaf("Ground_Leaf1", (-10, 2, -6), 250, 26, 16, lift=-4))
    return Joint("Root", (0, 0, 0), mound + [child])


VINE_JOINTS = ["Root"] + [f"Seg{i}" for i in range(1, len(SEGMENTS) + 1)] + ["Tip"] + [f"Petal{j}" for j in range(PETALS)]


def vine_pose(rot_per_seg, root_rot=(0, 0, 0), root_off=(0, 0, 0), tip=(0, 0, 0), petals=0.0):
    pose = {"Root": (root_rot, root_off), "Tip": (tip, (0, 0, 0))}
    for i, r in enumerate(rot_per_seg, 1):
        pose[f"Seg{i}"] = (r, (0, 0, 0))
    for j in range(PETALS):
        pose[f"Petal{j}"] = ((petals, 0, 0), (0, 0, 0))
    return pose


def sway(t, amp_x, amp_z):
    return [(amp_x * math.sin(2 * math.pi * t - i * 0.7), 0, amp_z * math.sin(2 * math.pi * t - i * 0.6 + 1.3))
            for i in range(len(SEGMENTS))]


def vine_anims():
    n = len(SEGMENTS)

    def idle(t):
        # Ondulation de serpent qui remonte la tige (boucle de 2 s), la fleur respire.
        return vine_pose(sway(t / 2.0, 5, 4), root_rot=(0, 10 * math.sin(math.pi * t), 0),
                         tip=(8 * math.sin(math.pi * t * 2 + 1), 0, 0), petals=6 + 6 * math.sin(math.pi * t))

    def spawn(t):
        # Sort de terre en se déroulant (0,5 s), la fleur s'ouvre en dernier.
        k = keys(t, [(0, 0), (0.45, 1)])
        return vine_pose([(30 * (1 - k), 0, 0)] * n, root_off=(0, -190 * (1 - k), 0),
                         petals=keys(t, [(0, -25), (0.35, -25), (0.5, 6)]))

    def hurt(t):
        k = keys(t, [(0, 0), (0.06, 1), (0.25, 0)])
        return vine_pose([(-10 * k, 0, 4 * k)] * n, petals=-15 * k)

    def death(t):
        k = keys(t, [(0, 0), (0.6, 1)])
        sink = keys(t, [(0, 0), (0.35, 0), (0.8, -120)])
        return vine_pose([(12 * k + 5 * i * k, 0, 5 * k) for i in range(n)], root_off=(0, sink, 0), petals=-25 * k)

    def strike(t):
        # Coup normal : elle se cabre (0,3 s) puis fouette vers l'avant et vers le bas, fleur grande ouverte.
        a = keys(t, [(0, 0), (0.3, -12), (0.38, 22), (0.5, 18), (0.8, 0)])
        return vine_pose([(a * (0.5 + 0.1 * i), 0, 0) for i in range(n)], tip=(a * 0.8, 0, 0),
                         petals=keys(t, [(0, 6), (0.3, -10), (0.36, 45), (0.6, 30), (0.8, 6)]))

    def throw(t):
        # Jet de ronces : elle se cabre puis donne deux coups de tête vers l'avant (épines à 0,5 s et 0,7 s).
        a = keys(t, [(0, 0), (0.42, -18), (0.52, 16), (0.6, -7), (0.72, 16), (0.9, 0)])
        return vine_pose([(a * (0.25 + 0.1 * i), 0, 0) for i in range(n)], tip=(a, 0, 0),
                         petals=keys(t, [(0, 6), (0.42, -15), (0.5, 55), (0.6, 20), (0.7, 55), (0.9, 6)]))

    def sweep(t):
        # Balayage : 1,2 s d'armement (elle se tord en arrière en tremblant), puis elle se couche au ras du sol
        # et fouette tout autour d'elle en un tour presque complet, avant de se redresser.
        shake = math.sin(t * 55) * keys(t, [(0, 0), (1.1, 4), (1.2, 0)])
        yaw = keys(t, [(0, 0), (1.15, -150), (1.2, -150), (1.42, 170), (1.9, 0)])
        low = keys(t, [(0, 0), (1.1, -0.25), (1.2, 1), (1.45, 1), (1.75, 0)])
        coil = keys(t, [(0, 0), (1.1, 8), (1.2, 0)])
        segs = []
        for i in range(n):
            x = low * (45 if i == 0 else 15 if i == 1 else -4) if low >= 0 else low * 32
            segs.append((x + shake, 0, shake * 0.5 + (coil if i > 1 else 0)))
        return vine_pose(segs, root_rot=(0, yaw, 0), tip=(low * 20, 0, 0), petals=-20 * max(0.0, low))

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

LOCOMOTION = ("Walk", "WalkBackward", "Run", "Sprint", "Jump", "JumpWalk", "JumpRun", "Fall", "Sleep", "Laydown",
              "Crouch", "CrouchWalk", "CrouchWalkBackward", "SwimIdle", "FluidIdle")


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
    # Un PNJ immobile peut quand même passer par un état de déplacement (chute à l'apparition, réveil…) :
    # sans animation pour cet état, le modèle resterait figé. Tous rejouent le repos.
    idle = f"{base}/Animations/Idle.blockyanim"
    for state in LOCOMOTION:
        sets.setdefault(state, anim_entry(idle))
    for state in ("Alerted", "Wake"):
        sets.setdefault(state, anim_entry(idle, Looping=False))
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
    build("Giant_Pumpkin", pumpkin_model(), PUMPKIN_JOINTS, pumpkin_anims(), 41, 512, {
        "$Comment": "Citrouille géante animée (élite), générée par tools/generate_pumpkin_models.py : huit côtes en relief, visage sculpté éclairé de l'intérieur, dents, tige et feuilles ; le haut se soulève comme une mâchoire (bouche qui s'ouvre, crachat de poison, rugissements). Elle ne se déplace pas.",
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
    vine_view = {"size": 300, "scale": 1.2, "center": (0, 95, 0)}
    build("Pumpkin_Vine", vine_model(), VINE_JOINTS, vine_anims(), 43, 256, {
        "$Comment": "Vrille combattante de la citrouille géante, générée par tools/generate_pumpkin_models.py : tige épineuse articulée de 3 blocs sortie d'une motte de terre, épines et feuilles, fleur de citrouille au cœur lumineux.",
        "EyeHeight": 2.5,
        "HitBox": {"Max": {"X": 0.4, "Y": 2.9, "Z": 0.4}, "Min": {"X": -0.4, "Y": 0, "Z": -0.4}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#ff9a3c", "Radius": 4},
    }, ["Strike", "Throw", "Sweep"], preview, [
        ("repos", None, 0, vine_view),
        ("idle", "Idle", 0.5, vine_view),
        ("fleur", None, 0, dict(vine_view, yaw=20, pitch=40, scale=3.0, center=(0, 175, 30))),
        ("coup", "Strike", 0.38, dict(vine_view, yaw=90, pitch=5)),
        ("jet", "Throw", 0.42, dict(vine_view, yaw=90, pitch=5)),
        ("balayage", "Sweep", 1.3, dict(vine_view, pitch=25, center=(0, 40, 0))),
        ("mort", "Death", 0.6, vine_view),
    ])


if __name__ == "__main__":
    main()
