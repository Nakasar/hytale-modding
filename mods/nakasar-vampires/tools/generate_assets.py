#!/usr/bin/env python3
"""Génère les blocs décoratifs du manoir gothique : vitraux, gargouille, grille et portail en fer forgé.

    python3 mods/nakasar-vampires/tools/generate_assets.py [--preview DOSSIER]

Pour chaque bloc : modèle (.blockymodel) ou texture de cube, icône, définition d'objet et, pour le
portail qui occupe deux blocs de haut, hitbox (les blocs de remplissage viennent de la hitbox).

Repère des modèles (comme l'autel sacrificiel) : 32 unités = 1 bloc, origine au centre du bas
du bloc d'ancrage, face « front » vers +Z. Les modèles sont faits de boîtes, avec au plus une
rotation autour de Y ; les textures sont peintes à 1 texel par unité, en dégradés doux.

- Nakasar_Stained_Glass_Red / _Violet : vitrail plein (cube), plombs noirs en losanges.
- Nakasar_Gargoyle : gargouille accroupie sur son socle, ailes repliées, yeux rouges luisants.
- Nakasar_Iron_Railing : grille à lances (VariantRotation Wall, comme les grilles en fer : rotation
  0 pour une ligne est-ouest, 1 pour une ligne nord-sud).
- Nakasar_Iron_Gate : vantail de portail en fer forgé, 1 × 2 blocs (VariantRotation NESW).
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
MODELS = COMMON / "Blocks" / "Nakasar" / "Halloween"
TEXTURES = COMMON / "BlockTextures" / "Nakasar" / "Halloween"
ICONS = COMMON / "Icons" / "Items" / "Nakasar" / "Halloween"
ITEMS = SERVER / "Item" / "Items" / "Deco" / "Nakasar"
HITBOXES = SERVER / "Item" / "Block" / "Hitboxes" / "Nakasar"

STONE = (104, 100, 104)
STONE_DARK = (70, 66, 72)
STONE_LIGHT = (138, 132, 134)
MOSS = (78, 96, 62)
IRON = (52, 50, 56)
IRON_LIGHT = (92, 90, 98)
IRON_DARK = (30, 28, 32)
EYE = (255, 40, 30)
FANG = (214, 204, 180)


def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def soft_noise(rng, w, h, scale=6, amp=0.12):
    """Bruit basse fréquence flouté : variations douces, pas de grain."""
    gw, gh = max(2, w // scale + 2), max(2, h // scale + 2)
    small = Image.new("L", (gw, gh))
    small.putdata([rng.randint(0, 255) for _ in range(gw * gh)])
    big = small.resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(scale / 2)).crop((scale, scale, scale + w, scale + h))
    px = big.load()
    return [[1 + amp * ((px[x, y] - 128) / 128) for x in range(w)] for y in range(h)]


def painter(base, kind="stone", moss=0.0, glow=False):
    """Peintre de face : couleur de base, dessus plus clair, bas plus sombre, arêtes adoucies."""

    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h))
        px = img.load()
        if glow:
            for y in range(h):
                for x in range(w):
                    px[x, y] = base + (255,)
            return img
        noise = soft_noise(rng, w, h, amp=0.10 if kind == "stone" else 0.06)
        for y in range(h):
            for x in range(w):
                if face == "top":
                    f = 1.12
                elif face == "bottom":
                    f = 0.72
                else:
                    f = 1.06 - 0.22 * (y / max(1, h - 1))
                edge = min(x, y, w - 1 - x, h - 1 - y)
                if edge == 0 and min(w, h) > 2:
                    f *= 1.1 if kind == "iron" else 0.9
                c = shade(base, f * noise[y][x])
                if moss and face in ("top", "front", "left", "right", "back") and noise[y][x] > 1.05 - moss * 0.1:
                    c = mix(c, MOSS, 0.55)
                px[x, y] = c + (255,)
        return img

    return paint


# --- modèles -----------------------------------------------------------------------------------

def gargoyle():
    s, d, l = painter(STONE, moss=0.2), painter(STONE_DARK), painter(STONE_LIGHT)
    parts = [
        ("Plinth", (0, 3, 0), (26, 6, 26), 0, d, "flat"),
        ("Plinth_Lip", (0, 6.5, 0), (22, 1, 22), 0, s, "flat"),
    ]
    for side, n in ((-1, "L"), (1, "R")):
        parts += [
            (f"Haunch_{n}", (6 * side, 11, -3), (7, 9, 11), 0, s, "flat"),
            (f"Foot_{n}", (6 * side, 8, 1), (6, 2, 6), 0, d, "flat"),
            (f"Arm_{n}", (5 * side, 12, 8), (4, 11, 4), 0, s, "flat"),
            (f"Claw_{n}", (5 * side, 8, 11), (5, 2, 4), 0, d, "flat"),
            (f"Wing_{n}", (10 * side, 25, -5), (3, 20, 13), 12 * side, d, "flat"),
            (f"Wing_Tip_{n}", (12 * side, 37, -9), (2, 7, 6), 12 * side, d, "flat"),
            (f"Horn_{n}", (4 * side, 33.5, 5), (2, 5, 2), 0, l, "flat"),
            (f"Horn_Tip_{n}", (5 * side, 37, 3.5), (2, 3, 2), 0, l, "flat"),
            (f"Eye_{n}", (3 * side, 29, 12.25), (2, 1.5, 0.5), 0, painter(EYE, glow=True), "fullbright"),
            (f"Fang_{n}", (2 * side, 22.5, 14.5), (1, 2, 1), 0, painter(FANG), "flat"),
        ]
    parts += [
        ("Body", (0, 18, -1), (14, 15, 12), 0, s, "flat"),
        ("Chest", (0, 17, 6), (11, 9, 4), 0, l, "flat"),
        ("Head", (0, 28, 7), (11, 9, 10), 0, s, "flat"),
        ("Brow", (0, 30.5, 12.5), (10, 2, 1), 0, d, "flat"),
        ("Snout", (0, 25, 13.5), (7, 5, 4), 0, s, "flat"),
        ("Tail", (0, 9, -11), (4, 3, 8), 0, d, "flat"),
        ("Tail_Tip", (3, 9, -15), (4, 3, 3), 0, d, "flat"),
    ]
    return parts


def iron_parts_spear(x, top, n):
    """Lance de grille : pointe en losange au-dessus du barreau."""
    i, li = painter(IRON, "iron"), painter(IRON_LIGHT, "iron")
    return [
        (f"Spear_{n}", (x, top + 1.5, 0), (2.6, 3, 2.6), 45, i, "flat"),
        (f"Spear_Tip_{n}", (x, top + 4, 0), (1.4, 2, 1.4), 45, li, "flat"),
    ]


def railing():
    i, dk = painter(IRON, "iron"), painter(IRON_DARK, "iron")
    parts = [
        ("Rail_Bottom", (0, 3, 0), (32, 2, 2), 0, i, "flat"),
        ("Rail_Top", (0, 25, 0), (32, 2, 2), 0, i, "flat"),
    ]
    for k, x in enumerate((-12, -4, 4, 12)):
        parts.append((f"Bar_{k}", (x, 15, 0), (2, 30, 2), 0, i, "flat"))
        parts += iron_parts_spear(x, 30, k)
    for k, x in enumerate((-8, 0, 8)):
        parts.append((f"Scroll_{k}", (x, 20, 0), (3, 3, 1), 0, dk, "flat"))
    return parts


def gate():
    i, dk = painter(IRON, "iron"), painter(IRON_DARK, "iron")
    parts = [
        ("Stile_L", (-15, 32, 0), (2, 64, 2), 0, i, "flat"),
        ("Stile_R", (15, 32, 0), (2, 64, 2), 0, i, "flat"),
    ]
    for k, y in enumerate((3, 30, 56)):
        parts.append((f"Rail_{k}", (0, y, 0), (28, 2, 2), 0, i, "flat"))
    for k, x in enumerate((-9, -3, 3, 9)):
        parts.append((f"Bar_{k}", (x, 31, 0), (2, 58, 2), 0, i, "flat"))
        parts += iron_parts_spear(x, 60, k)
    parts += iron_parts_spear(-15, 64, "L") + iron_parts_spear(15, 64, "R")
    for k, x in enumerate((-6, 0, 6)):
        parts.append((f"Ring_{k}", (x, 43, 0), (4, 4, 1), 0, dk, "flat"))
        parts.append((f"Ring_Low_{k}", (x, 16, 0), (4, 4, 1), 0, dk, "flat"))
    return parts


FACES = ("top", "bottom", "front", "back", "left", "right")


def face_size(size, face):
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sz
    if face in ("front", "back"):
        return sx, sy
    return sz, sy


def build_atlas(parts, seed, tex_w=128):
    rng = random.Random(seed)
    regions = []
    for pi, (name, c, size, rot, paint, _) in enumerate(parts):
        for g in (("top",), ("bottom",), ("front", "back"), ("left", "right")):
            w, h = (max(1, math.ceil(v)) for v in face_size(size, g[0]))
            regions.append((pi, g, w, h, paint(rng, w, h, g[0])))
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
        tex_h *= 2


def quat_y(deg):
    a = math.radians(deg) / 2
    return {"x": 0, "y": round(math.sin(a), 6), "z": 0, "w": round(math.cos(a), 6)}


def num(v):
    return int(v) if float(v).is_integer() else v


def build_model(name, parts, uv):
    children = []
    for pi, (pname, c, size, rot, _, shading) in enumerate(parts):
        layout = {f: {"offset": {"x": uv[(pi, f)][0], "y": uv[(pi, f)][1]}, "mirror": {"x": False, "y": False}, "angle": 0}
                  for f in FACES}
        children.append({
            "id": str(pi + 2),
            "name": pname,
            "position": {"x": num(c[0]), "y": num(c[1]), "z": num(c[2])},
            "orientation": quat_y(rot),
            "shape": {
                "type": "box",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"size": {"x": num(size[0]), "y": num(size[1]), "z": num(size[2])}, "isStaticBox": True},
                "textureLayout": layout,
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": shading,
            },
        })
    root = {
        "id": "1",
        "name": name,
        "position": {"x": 0, "y": 0, "z": 0},
        "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
        "shape": {
            "type": "none",
            "offset": {"x": 0, "y": 0, "z": 0},
            "stretch": {"x": 1, "y": 1, "z": 1},
            "settings": {"isPiece": False},
            "textureLayout": {},
            "unwrapMode": "custom",
            "visible": True,
            "doubleSided": False,
            "shadingMode": "flat",
        },
        "children": children,
    }
    return {"format": "prop", "lod": "auto", "nodes": [root]}


# --- rendu logiciel (icônes et aperçus) --------------------------------------------------------

def rot_y(p, deg):
    a = math.radians(deg)
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def face_quads(part, uv, pi):
    name, c, size, rot, _, shading = part
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    defs = {
        "top": ((-hx, hy, -hz), (2 * hx, 0, 0), (0, 0, 2 * hz), (0, 1, 0)),
        "bottom": ((-hx, -hy, hz), (2 * hx, 0, 0), (0, 0, -2 * hz), (0, -1, 0)),
        "front": ((-hx, hy, hz), (2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, 1)),
        "back": ((hx, hy, -hz), (-2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, -1)),
        "right": ((hx, hy, hz), (0, 0, -2 * hz), (0, -2 * hy, 0), (1, 0, 0)),
        "left": ((-hx, hy, -hz), (0, 0, 2 * hz), (0, -2 * hy, 0), (-1, 0, 0)),
    }
    for f, (o, u, v, n) in defs.items():
        o = rot_y(o, rot)
        o = (o[0] + c[0], o[1] + c[1], o[2] + c[2])
        yield f, o, rot_y(u, rot), rot_y(v, rot), rot_y(n, rot), uv[(pi, f)], face_size(size, f), shading


def render(parts, atlas, uv, size, yaw, pitch, scale, center):
    W = H = size
    zbuf = [[-1e9] * W for _ in range(H)]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px, tex = img.load(), atlas.load()
    light = (0.45, 0.8, 0.4)
    ln = math.sqrt(sum(v * v for v in light))
    light = tuple(v / ln for v in light)

    def view(p):
        p = rot_y((p[0] - center[0], p[1] - center[1], p[2] - center[2]), yaw)
        a = math.radians(pitch)
        return (p[0], p[1] * math.cos(a) - p[2] * math.sin(a), p[1] * math.sin(a) + p[2] * math.cos(a))

    for pi, part in enumerate(parts):
        for f, o, u, v, n, (tu, tv), (fw, fh), shading in face_quads(part, uv, pi):
            nv = view((n[0] + center[0], n[1] + center[1], n[2] + center[2]))
            if nv[2] <= 0:
                continue
            lum = 1.0 if shading == "fullbright" else 0.55 + 0.45 * max(0, sum(n[k] * light[k] for k in range(3)))
            su, sv = max(2, int(fw * scale * 1.6) + 2), max(2, int(fh * scale * 1.6) + 2)
            for j in range(sv):
                fv = (j + 0.5) / sv
                for i in range(su):
                    fu = (i + 0.5) / su
                    q = view(tuple(o[k] + u[k] * fu + v[k] * fv for k in range(3)))
                    sx, sy = int(W / 2 + q[0] * scale), int(H / 2 - q[1] * scale)
                    if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                        zbuf[sy][sx] = q[2]
                        t = tex[min(tu + int(fu * max(1, math.ceil(fw))), atlas.width - 1),
                                min(tv + int(fv * max(1, math.ceil(fh))), atlas.height - 1)]
                        px[sx, sy] = shade(t[:3], lum) + (255,)
    return img


# --- vitraux -----------------------------------------------------------------------------------

GLASS = {
    "Red": [(150, 18, 30), (196, 40, 44), (120, 14, 40), (150, 18, 30), (196, 140, 50), (90, 20, 70)],
    "Violet": [(84, 30, 120), (120, 52, 160), (54, 30, 104), (40, 96, 92), (150, 40, 70)],
}
LEAD = (22, 20, 24, 255)


def stained_glass(colors, seed):
    """Losanges colorés sertis de plomb, dans un cadre de plomb ; un peu translucides."""
    rng = random.Random(seed)
    n = 32
    img = Image.new("RGBA", (n, n))
    px = img.load()
    cells = {}
    for y in range(n):
        for x in range(n):
            u, v = (x + y) // 8, (x - y + n) // 8
            if (u, v) not in cells:
                cells[(u, v)] = rng.choice(colors)
            base = cells[(u, v)]
            glow = 1.15 - 0.3 * abs((x - 15.5) / 16) - 0.2 * (y / n)
            px[x, y] = shade(base, glow) + (205,)
            if (x + y) % 8 == 0 or (x - y) % 8 == 0 or x < 2 or y < 2 or x > n - 3 or y > n - 3:
                px[x, y] = LEAD
    # reflets clairs sur quelques losanges
    d = ImageDraw.Draw(img)
    for _ in range(5):
        x, y = rng.randint(4, 26), rng.randint(4, 26)
        if px[x, y] != LEAD:
            d.point((x, y), fill=shade(px[x, y][:3], 1.5) + (215,))
    return img


# --- définitions d'objets ----------------------------------------------------------------------

def model_item(block_id, icon, model, texture, hitbox, rotation, sound, particles, color, support_down=False):
    bt = {
        "Material": "Solid",
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": model,
        "CustomModelTexture": [{"Texture": texture, "Weight": 1}],
        "HitboxType": hitbox,
        "VariantRotation": rotation,
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Rocks"}},
        "BlockParticleSetId": particles,
        "BlockSoundSetId": sound,
        "ParticleColor": color,
    }
    if support_down:
        bt["Support"] = {"Down": [{"FaceType": "Full"}]}
    return {
        "TranslationProperties": {"Name": f"nakasar_halloween.items.{block_id}.name"},
        "Icon": icon,
        "Categories": ["Blocks.Deco"],
        "PlayerAnimationsId": "Block",
        "BlockType": bt,
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Items_Metal" if sound == "Metal" else "ISS_Blocks_Stone",
    }


def glass_item(block_id, icon, texture, color):
    return {
        "TranslationProperties": {"Name": f"nakasar_halloween.items.{block_id}.name"},
        "Icon": icon,
        "Categories": ["Blocks.Deco"],
        "PlayerAnimationsId": "Block",
        "BlockType": {
            "Material": "Solid",
            "DrawType": "Cube",
            "Opacity": "Semitransparent",
            "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
            "HitboxType": "Full",
            "Flags": {},
            "Gathering": {"Breaking": {"GatherType": "Rocks"}},
            "BlockParticleSetId": "Crystal",
            "BlockSoundSetId": "Crystal",
            "ParticleColor": color,
        },
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    }


def rel(path):
    return path.relative_to(COMMON).as_posix()


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def hitbox_box(x0, y0, z0, x1, y1, z1):
    to = lambda u, axis: round(u / 32 + (0 if axis == "y" else 0.5), 4)
    return {"Min": {"X": to(x0, "x"), "Y": to(y0, "y"), "Z": to(z0, "z")},
            "Max": {"X": to(x1, "x"), "Y": to(y1, "y"), "Z": to(z1, "z")}}


MODEL_BLOCKS = [
    # id, fichier, pièces, hitbox, rotation, son, particules, couleur, posée sur un bloc plein, centre du rendu
    ("Nakasar_Gargoyle", "Gargoyle", gargoyle, "Statue_Small", "NESW", "Stone", "Stone", "#68646a", True, (0, 20, 0)),
    ("Nakasar_Iron_Railing", "Iron_Railing", railing, "Fence_Thin", "Wall", "Metal", "Metal", "#343238", False, (0, 18, 0)),
    ("Nakasar_Iron_Gate", "Iron_Gate", gate, "Nakasar_Iron_Gate", "NESW", "Metal", "Metal", "#343238", False, (0, 34, 0)),
]


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview.mkdir(parents=True, exist_ok=True)
    for i, (block_id, name, build, hitbox, rotation, sound, particles, color, support, center) in enumerate(MODEL_BLOCKS):
        parts = build()
        atlas, uv = build_atlas(parts, seed=100 + i)
        model, texture, icon = MODELS / f"{name}.blockymodel", TEXTURES / f"{name}.png", ICONS / f"{name}.png"
        for path in (model, texture, icon):
            path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(texture)
        model.write_text(json.dumps(build_model(name, parts, uv), indent=2) + "\n", encoding="utf-8")
        height = 70 if name == "Iron_Gate" else 40
        scale = 256 / (height * 1.5)
        big = render(parts, atlas, uv, 256, yaw=-35, pitch=22, scale=scale, center=center)
        big.resize((64, 64), Image.LANCZOS).save(icon)
        write_json(ITEMS / f"{block_id}.json",
                   model_item(block_id, rel(icon), rel(model), rel(texture), hitbox, rotation, sound, particles, color, support))
        if preview:
            render(parts, atlas, uv, 512, yaw=-35, pitch=22, scale=scale * 2, center=center).save(preview / f"{name}_front.png")
            render(parts, atlas, uv, 512, yaw=145, pitch=22, scale=scale * 2, center=center).save(preview / f"{name}_back.png")
    # le vantail du portail occupe 1 × 2 blocs, un grillage fin au milieu du bloc
    write_json(HITBOXES / "Nakasar_Iron_Gate.json", {"Boxes": [hitbox_box(-16, 0, -2, 16, 64, 2)]})
    for i, (colour, palette) in enumerate(GLASS.items()):
        block_id = f"Nakasar_Stained_Glass_{colour}"
        img = stained_glass(palette, seed=200 + i)
        texture, icon = TEXTURES / f"Stained_Glass_{colour}.png", ICONS / f"Stained_Glass_{colour}.png"
        texture.parent.mkdir(parents=True, exist_ok=True)
        icon.parent.mkdir(parents=True, exist_ok=True)
        img.save(texture)
        img.resize((64, 64), Image.NEAREST).save(icon)
        write_json(ITEMS / f"{block_id}.json", glass_item(block_id, rel(icon), rel(texture), "#%02x%02x%02x" % palette[0]))
        if preview:
            img.resize((256, 256), Image.NEAREST).save(preview / f"Stained_Glass_{colour}.png")
    print("blocs du manoir générés")


if __name__ == "__main__":
    main()
