"""Modèles de PNJ animés des Fractales (squelette de nœuds, .blockyanim), copiés du moteur du mod Vampires
(mods/nakasar-vampires/tools/generate_pumpkin_models.py : pas de bibliothèque partagée, corriger les deux à la main).

Format « character » : 64 unités = 1 bloc, origine au sol, face avant vers +Z. Les articulations (Joint) sont des
nœuds sans forme ; les boîtes (Box) sont des feuilles centrées sur leur position. Une rotation positive autour de X
penche le haut d'un nœud vers l'avant (+Z). Animations à 60 images par seconde ; celles d'attaque sont jouées par les
interactions (Effects.ItemPlayerAnimationsId = Nakasar_Fractal_<modèle>, ItemAnimationId = nom).
"""
import json
import math
import random
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
        "$Comment": "Animations d'attaque jouées par les interactions (Effects.ItemAnimationId), générées par les outils des Fractales.",
        "Animations": {n: {"ThirdPerson": f"{base}/Animations/{n}.blockyanim", "Looping": False, "Speed": 1} for n in names},
        "WiggleWeights": {"Pitch": 0, "PitchDeceleration": 0.1, "Roll": 0, "RollDeceleration": 0.1,
                          "X": 0, "XDeceleration": 0.1, "Y": 0, "YDeceleration": 0.1, "Z": 0, "ZDeceleration": 0.1},
    }


def build(key, root, joints, anims, seed, tex_w, model_doc, attacks, preview, previews):
    base = f"NPC/Nakasar/Fractals/{key}"
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
        sets.setdefault(state, anim_entry(idle))
    model_doc["AnimationSets"] = sets
    write_json(SERVER / "Models" / "Nakasar" / "Fractals" / f"Nakasar_Fractal_{key}.json", model_doc)
    write_json(SERVER / "Item" / "Animations" / "Nakasar" / "Fractals" / f"Nakasar_Fractal_{key}.json", item_animations(base, attacks))
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
