#!/usr/bin/env python3
"""Génère le modèle, la texture, la hitbox et l'icône de l'autel sacrificiel.

Usage : python3 mods/nakasar-runes/tools/generate_altar.py [--preview DOSSIER]

L'autel occupe 2 blocs de large (X), 2 de haut (Y) et 1 de profondeur (Z), comme
l'établi d'alchimie vanilla. Le bloc d'ancrage est celui posé par le joueur ; le
modèle s'étend vers +X sur le second bloc (les blocs de remplissage viennent de la
hitbox). Grille du modèle : 32 unités = 1 bloc, origine au centre du bas du bloc
d'ancrage. Texture peinte à 1 texel par unité, en dégradés doux (pas de bruit
pixel par pixel) pour coller au style des props Hytale.

Rien de rouge sur les faces du dessous : la dalle de l'ancien modèle réutilisait
la flaque de sang pour sa face inférieure, visible sous l'autel.
"""
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent / "src/main/resources"
MODEL = ROOT / "Common/Blocks/Nakasar/Sacrificial_Altar.blockymodel"
TEXTURE = ROOT / "Common/BlockTextures/Nakasar/Sacrificial_Altar.png"
ICON = ROOT / "Common/Icons/Items/Nakasar/Sacrificial_Altar.png"
HITBOX = ROOT / "Server/Item/Block/Hitboxes/Nakasar/Nakasar_Sacrificial_Altar.json"

TEX_W, TEX_H = 256, 128
random.seed(7)

# Palette : pierre sombre légèrement violacée, os, sang, cire, flamme.
STONE = (122, 112, 108)
STONE_DARK = (82, 73, 76)
STONE_LIGHT = (158, 147, 138)
BASALT = (72, 64, 70)
BLOOD = (122, 22, 34)
BLOOD_LIGHT = (168, 40, 48)
BLOOD_DARK = (78, 12, 22)
CRYSTAL = (150, 28, 46)
CRYSTAL_LIGHT = (226, 92, 102)
WAX = (222, 208, 176)
WAX_DARK = (184, 166, 132)
FLAME = (255, 196, 92)
FLAME_CORE = (255, 240, 190)
STEEL = (170, 172, 182)
LEATHER = (92, 60, 44)
BONE = (226, 214, 186)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


# --------------------------------------------------------------------------
# Peinture des faces
# --------------------------------------------------------------------------

def soft_noise(w, h, scale=7, amp=0.12):
    """Bruit basse fréquence flouté : variations douces, pas de grain."""
    gw, gh = max(2, w // scale + 2), max(2, h // scale + 2)
    small = Image.new("L", (gw, gh))
    small.putdata([random.randint(0, 255) for _ in range(gw * gh)])
    big = small.resize((w + scale * 2, h + scale * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.GaussianBlur(scale / 2)).crop((scale, scale, scale + w, scale + h))
    px = big.load()
    return [[1 + amp * ((px[x, y] - 128) / 128) for x in range(w)] for y in range(h)]


def paint_stone(w, h, base, kind, accents=None):
    """Pierre lisse : dégradé vertical, arêtes adoucies, variations douces.

    kind : 'top' (dessus éclairé), 'side' (côté, plus sombre vers le bas),
    'bottom' (dessous uni et sombre).
    """
    img = Image.new("RGBA", (w, h))
    px = img.load()
    noise = soft_noise(w, h)
    for y in range(h):
        for x in range(w):
            if kind == "bottom":
                f = 0.62
            elif kind == "top":
                # léger vignettage vers les bords + arête claire de 1 px
                ex = min(x, w - 1 - x) / max(1, w / 2)
                ey = min(y, h - 1 - y) / max(1, h / 2)
                f = 1.08 - 0.06 * (1 - min(1, min(ex, ey) * 3))
                edge = min(x, y, w - 1 - x, h - 1 - y)
                if edge == 0:
                    f = 1.2
                elif edge == 1 and w > 6 and h > 6:
                    f = 1.12
            else:
                t = y / max(1, h - 1)
                f = 1.0 - 0.28 * t
                if y == 0:
                    f = 1.18
                elif y == 1 and h > 5:
                    f = 1.08
                elif y == h - 1 and h > 2:
                    f *= 0.84
                # bords verticaux un peu assombris : faux biseau
                if (x == 0 or x == w - 1) and w > 4:
                    f *= 0.9
            f *= noise[y][x]
            px[x, y] = shade(base, f) + (255,)
    if accents:
        accents(img)
    return img


def crack(draw, pts, color):
    draw.line(pts, fill=color + (255,), width=1)


def body_front_accents(img):
    """Bandeau de runes gravées sur la face avant/arrière du corps."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    band_top, band_bot = 5, h - 5
    d.rectangle((3, band_top, w - 4, band_bot), fill=shade(BASALT, 0.82) + (255,))
    d.line((3, band_top, w - 4, band_top), fill=shade(BASALT, 0.62) + (255,))
    d.line((3, band_bot, w - 4, band_bot), fill=shade(STONE, 1.1) + (255,))
    # trois glyphes sobres, rouge sombre peint (pas émissif)
    cx = [w // 4, w // 2, 3 * w // 4]
    cy = (band_top + band_bot) // 2
    for i, x in enumerate(cx):
        c = BLOOD if i != 1 else BLOOD_LIGHT
        if i == 1:
            d.ellipse((x - 3, cy - 3, x + 3, cy + 3), outline=c + (255,))
            d.line((x, cy - 4, x, cy + 4), fill=c + (255,))
        else:
            d.line((x - 2, cy - 3, x + 2, cy + 3), fill=c + (255,))
            d.line((x + 2, cy - 3, x - 2, cy + 3), fill=c + (255,))
            d.point((x, cy - 4), fill=c + (255,))
    crack(d, [(w - 9, 1), (w - 11, 3), (w - 10, 4)], shade(STONE, 0.7))


def body_side_accents(img):
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.rectangle((3, 5, w - 4, h - 5), fill=shade(BASALT, 0.82) + (255,))
    d.line((3, 5, w - 4, 5), fill=shade(BASALT, 0.62) + (255,))
    cx, cy = w // 2, h // 2
    d.polygon([(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)], outline=BLOOD + (255,))


def slab_top_accents(img):
    """Dessus de la dalle : rigole périphérique, sang dans la rigole avant."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    groove = shade(BASALT, 0.7)
    d.rectangle((3, 3, w - 4, h - 4), outline=groove + (255,))
    d.line((4, 4, w - 5, 4), fill=shade(BASALT, 0.55) + (255,))
    # sang qui a coulé dans la rigole, depuis le centre vers les bords
    for x in range(w // 2 - 9, w // 2 + 10):
        d.point((x, h - 4), fill=(BLOOD if x % 5 else BLOOD_LIGHT) + (255,))
    d.line((w // 2, h // 2 + 7, w // 2, h - 4), fill=BLOOD + (255,))
    d.line((w // 2 + 1, h // 2 + 7, w // 2 + 1, h - 5), fill=BLOOD_DARK + (255,))
    # quelques gouttes et une tache
    for x, y in [(w // 2 - 4, h // 2 + 9), (w // 2 + 5, h // 2 + 10), (w // 2 - 7, h - 7)]:
        d.point((x, y), fill=BLOOD + (255,))
    crack(d, [(7, 7), (10, 9), (11, 12)], shade(STONE, 0.72))
    crack(d, [(w - 8, h - 9), (w - 12, h - 10)], shade(STONE, 0.72))


def shaft_rune(img):
    w, h = img.size
    d = ImageDraw.Draw(img)
    cx = w // 2
    d.line((cx, 3, cx, h - 4), fill=BLOOD_DARK + (255,))
    d.point((cx - 1, 5), fill=BLOOD + (255,))
    d.point((cx + 1, 7), fill=BLOOD + (255,))
    d.point((cx - 1, 9), fill=BLOOD + (255,))


def slab_front_accents(img):
    w, h = img.size
    d = ImageDraw.Draw(img)
    # une coulée de sang au milieu de la face avant, qui s'arrête vite
    x = w // 2
    d.line((x, 0, x, 3), fill=BLOOD + (255,))
    d.point((x + 1, 0), fill=BLOOD_DARK + (255,))
    d.point((x, 4), fill=BLOOD_DARK + (255,))


def bowl_top_accents(img):
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, w - 3, h - 3), fill=shade(BASALT, 0.6) + (255,))
    d.ellipse((3, 3, w - 4, h - 4), fill=BLOOD_DARK + (255,))
    d.ellipse((4, 4, w - 5, h - 5), fill=BLOOD + (255,))
    d.ellipse((5, 5, w // 2, h // 2), fill=BLOOD_LIGHT + (255,))
    d.point((w // 2 + 2, h // 2 + 2), fill=BLOOD_LIGHT + (255,))


def paint_flat(w, h, color, kind="side", top_color=None):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for x in range(w):
            if kind == "top" and top_color:
                c = top_color
            elif kind == "bottom":
                c = shade(color, 0.7)
            else:
                c = shade(color, 1.08 - 0.25 * t)
            px[x, y] = c + (255,)
    return img


def paint_crystal(w, h, kind):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x + (h - 1 - y)) / max(1, w + h - 2)
            c = mix(CRYSTAL, CRYSTAL_LIGHT, t * 0.8)
            if kind == "bottom":
                c = shade(CRYSTAL, 0.6)
            px[x, y] = c + (255,)
    if kind != "bottom" and w > 2:
        px[1, 1] = (250, 180, 186, 255)
    return img


def paint_flame(w, h, kind):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (FLAME_CORE if y >= h - 1 and kind == "side" else FLAME) + (255,)
    return img


def paint_skull(w, h, kind, face):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            f = 0.7 if kind == "bottom" else (1.05 if kind == "top" else 1.0 - 0.2 * y / max(1, h - 1))
            px[x, y] = shade(BONE, f) + (255,)
    if face in ("front", "back"):
        d = ImageDraw.Draw(img)
        dark = (54, 40, 40, 255)
        d.rectangle((1, 1, 2, 2), fill=dark)
        d.rectangle((w - 3, 1, w - 2, 2), fill=dark)
        d.point((w // 2 - 1 + (w % 2), 3), fill=dark)
        for x in range(1, w - 1, 2):
            d.point((x, h - 1), fill=shade(BONE, 0.6) + (255,))
    return img


def paint_blade(w, h, kind):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            c = shade(STEEL, 1.1 if kind == "top" else 0.85)
            if kind == "top" and x > w - 3:
                c = BLOOD
            px[x, y] = c + (255,)
    return img


# --------------------------------------------------------------------------
# Géométrie : (nom, centre, taille, rotation Y en degrés, peintre, ombrage)
# Le peintre reçoit (largeur, hauteur, type de face, face) et rend une image.
# --------------------------------------------------------------------------

def stone(base, top=None, front=None, side=None):
    def painter(w, h, kind, face):
        acc = None
        if kind == "bottom":
            acc = None
        elif kind == "top":
            acc = top
        elif face in ("front", "back"):
            acc = front
        elif face in ("left", "right"):
            acc = side
        return paint_stone(w, h, base, kind, acc)
    return painter


def flat(color, top_color=None):
    return lambda w, h, kind, face: paint_flat(w, h, color, kind, top_color)


CX = 16  # centre en X des deux blocs (-16..48)
OB_X = (-5, 37)  # obélisques, un par bloc

PARTS = [
    ("Plinth", (CX, 1.5, 0), (62, 3, 30), 0, stone(STONE_DARK), "flat"),
    ("Plinth_Step", (CX, 3.5, 0), (54, 1, 26), 0, stone(STONE), "flat"),
    ("Body", (CX, 12, 0), (46, 16, 22), 0, stone(STONE, front=body_front_accents, side=body_side_accents), "flat"),
    ("Slab", (CX, 25, 0), (56, 6, 28), 0, stone(STONE_LIGHT, top=slab_top_accents), "flat"),
    ("Body_Lip", (CX, 21, 0), (50, 2, 25), 0, stone(STONE_DARK), "flat"),
    ("Bowl_Foot", (CX, 29, 0), (10, 2, 10), 0, stone(BASALT), "flat"),
    ("Bowl", (CX, 32, 0), (16, 4, 16), 0, stone(BASALT, top=bowl_top_accents), "flat"),
]
for i, ox in enumerate(OB_X):
    n = "L" if i == 0 else "R"
    PARTS += [
        (f"Obelisk_{n}_Base", (ox, 30, 0), (12, 4, 12), 0, stone(STONE_DARK), "flat"),
        (f"Obelisk_{n}_Shaft", (ox, 39, 0), (8, 14, 8), 0, stone(STONE, front=shaft_rune, side=shaft_rune), "flat"),
        (f"Obelisk_{n}_Shaft_Top", (ox, 50, 0), (6, 8, 6), 0, stone(STONE), "flat"),
        (f"Obelisk_{n}_Cap", (ox, 55, 0), (9, 2, 9), 0, stone(STONE_DARK), "flat"),
        (f"Obelisk_{n}_Crystal", (ox, 59, 0), (4, 6, 4), 45,
         lambda w, h, kind, face: paint_crystal(w, h, kind), "flat"),
        (f"Obelisk_{n}_Crystal_Tip", (ox, 63, 0), (2, 2, 2), 45,
         lambda w, h, kind, face: paint_crystal(w, h, kind), "flat"),
    ]
# Bougies, en diagonale pour rester symétriques avant/arrière.
for name, x, z, hgt in [("Candle_1", 4, -9, 6), ("Candle_2", 8, -10, 4), ("Candle_3", 28, 9, 6), ("Candle_4", 24, 10, 4)]:
    PARTS += [
        (name, (x, 28 + hgt / 2, z), (2, hgt, 2), 0, flat(WAX, top_color=WAX_DARK), "flat"),
        (name + "_Flame", (x, 28 + hgt + 1, z), (1, 2, 1), 0, lambda w, h, kind, face: paint_flame(w, h, kind), "fullbright"),
    ]
# Crâne posé sur la dalle.
PARTS += [
    ("Skull", (6, 31.5, 6), (6, 5, 6), 0, paint_skull, "flat"),
    ("Skull_Jaw", (6, 28.5, 6.5), (4, 1, 4), 0, paint_skull, "flat"),
]
# Dague rituelle posée sur la dalle.
PARTS += [
    ("Dagger_Blade", (25, 28.5, -8), (9, 1, 2), 0, lambda w, h, kind, face: paint_blade(w, h, kind), "flat"),
    ("Dagger_Handle", (18, 28.5, -8), (5, 1, 2), 0, flat(LEATHER), "flat"),
]

FACES = ("top", "bottom", "front", "back", "left", "right")


def face_size(size, face):
    sx, sy, sz = size
    if face in ("top", "bottom"):
        return sx, sz
    if face in ("front", "back"):
        return sx, sy
    return sz, sy


def face_kind(face):
    return face if face in ("top", "bottom") else "side"


# --------------------------------------------------------------------------
# Atlas : une région par face (les faces opposées identiques sont partagées)
# --------------------------------------------------------------------------

def build_atlas():
    regions = []  # (part index, faces partagées, w, h, image)
    for pi, (name, c, size, rot, painter, _) in enumerate(PARTS):
        groups = [("top",), ("bottom",), ("front", "back"), ("left", "right")]
        for g in groups:
            w, h = (math.ceil(v) for v in face_size(size, g[0]))
            img = painter(w, h, face_kind(g[0]), g[0])
            regions.append((pi, g, w, h, img))
    # étagères, des plus hautes aux plus basses
    order = sorted(range(len(regions)), key=lambda i: (-regions[i][3], -regions[i][2]))
    atlas = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    uv = {}
    x = y = shelf = 0
    for i in order:
        pi, g, w, h, img = regions[i]
        if x + w > TEX_W:
            x, y, shelf = 0, y + shelf, 0
        if y + h > TEX_H:
            raise SystemExit("atlas trop petit")
        atlas.paste(img, (x, y))
        for f in g:
            uv[(pi, f)] = (x, y)
        x += w
        shelf = max(shelf, h)
    return atlas, uv


# --------------------------------------------------------------------------
# Écriture du .blockymodel
# --------------------------------------------------------------------------

def quat_y(deg):
    a = math.radians(deg) / 2
    return {"x": 0, "y": round(math.sin(a), 6), "z": 0, "w": round(math.cos(a), 6)}


def num(v):
    return int(v) if float(v).is_integer() else v


def build_model(uv):
    children = []
    for pi, (name, c, size, rot, _, shading) in enumerate(PARTS):
        layout = {
            f: {"offset": {"x": uv[(pi, f)][0], "y": uv[(pi, f)][1]},
                "mirror": {"x": False, "y": False}, "angle": 0}
            for f in FACES
        }
        children.append({
            "id": str(pi + 2),
            "name": name,
            "position": {"x": num(c[0]), "y": num(c[1]), "z": num(c[2])},
            "orientation": quat_y(rot),
            "shape": {
                "type": "box",
                "offset": {"x": 0, "y": 0, "z": 0},
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"size": {"x": size[0], "y": size[1], "z": size[2]}, "isStaticBox": True},
                "textureLayout": layout,
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": shading,
            },
        })
    root = {
        "id": "1",
        "name": "Sacrificial_Altar",
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


# --------------------------------------------------------------------------
# Hitbox (unités de bloc, bloc d'ancrage = [0,1]³) : 2 x 2 x 1 blocs
# --------------------------------------------------------------------------

def to_block(u, axis):
    return round(u / 32 + (0 if axis == "y" else 0.5), 4)


def build_hitbox():
    def box(x0, y0, z0, x1, y1, z1):
        return {"Min": {"X": to_block(x0, "x"), "Y": to_block(y0, "y"), "Z": to_block(z0, "z")},
                "Max": {"X": to_block(x1, "x"), "Y": to_block(y1, "y"), "Z": to_block(z1, "z")}}
    boxes = [
        # socle + corps + dalle : on étend X et Z aux bords des blocs pour que
        # les blocs de remplissage couvrent exactement 2 x 1.
        box(-16, 0, -16, 48, 28, 16),
    ]
    for ox in OB_X:
        boxes.append(box(ox - 6, 28, -6, ox + 6, 64, 6))
    return {"Boxes": boxes}


# --------------------------------------------------------------------------
# Rendu logiciel (icône et aperçus) : projection orthographique + z-buffer
# --------------------------------------------------------------------------

def rot_y(p, deg):
    a = math.radians(deg)
    x, y, z = p
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def face_quads(part, uvmap, pi):
    """Coins 3D de chaque face (sens texture : u vers la droite, v vers le bas)."""
    name, c, size, rot, _, shading = part
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    # (face, origine haut-gauche, axe u, axe v, normale) dans le repère local
    defs = {
        "top": ((-hx, hy, -hz), (2 * hx, 0, 0), (0, 0, 2 * hz), (0, 1, 0)),
        "bottom": ((-hx, -hy, hz), (2 * hx, 0, 0), (0, 0, -2 * hz), (0, -1, 0)),
        "front": ((-hx, hy, hz), (2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, 1)),
        "back": ((hx, hy, -hz), (-2 * hx, 0, 0), (0, -2 * hy, 0), (0, 0, -1)),
        "right": ((hx, hy, hz), (0, 0, -2 * hz), (0, -2 * hy, 0), (1, 0, 0)),
        "left": ((-hx, hy, -hz), (0, 0, 2 * hz), (0, -2 * hy, 0), (-1, 0, 0)),
    }
    out = []
    for f, (o, u, v, n) in defs.items():
        o = rot_y(o, rot)
        o = (o[0] + c[0], o[1] + c[1], o[2] + c[2])
        out.append((f, o, rot_y(u, rot), rot_y(v, rot), rot_y(n, rot), uvmap[(pi, f)], face_size(size, f), shading))
    return out


def render(atlas, uvmap, size, yaw, pitch, scale, center=(16, 30, 0)):
    """Rend le modèle vu avec un lacet `yaw` et une plongée `pitch`."""
    W = H = size
    zbuf = [[-1e9] * W for _ in range(H)]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    tex = atlas.load()
    light = (0.45, 0.8, 0.4)
    ln = math.sqrt(sum(v * v for v in light))
    light = tuple(v / ln for v in light)

    def view(p):
        p = (p[0] - center[0], p[1] - center[1], p[2] - center[2])
        p = rot_y(p, yaw)
        a = math.radians(pitch)
        y = p[1] * math.cos(a) - p[2] * math.sin(a)
        z = p[1] * math.sin(a) + p[2] * math.cos(a)
        return (p[0], y, z)

    for pi, part in enumerate(PARTS):
        for f, o, u, v, n, (tu, tv), (fw, fh), shading in face_quads(part, uvmap, pi):
            nv = view((n[0] + center[0], n[1] + center[1], n[2] + center[2]))
            if nv[2] <= 0:
                continue  # face de dos
            lum = 1.0 if shading == "fullbright" else 0.55 + 0.45 * max(0, sum(n[i] * light[i] for i in range(3)))
            steps_u = max(2, int(fw * scale * 1.6) + 2)
            steps_v = max(2, int(fh * scale * 1.6) + 2)
            for j in range(steps_v):
                fv = (j + 0.5) / steps_v
                for i in range(steps_u):
                    fu = (i + 0.5) / steps_u
                    p = tuple(o[k] + u[k] * fu + v[k] * fv for k in range(3))
                    q = view(p)
                    sx = int(W / 2 + q[0] * scale)
                    sy = int(H / 2 - q[1] * scale)
                    if 0 <= sx < W and 0 <= sy < H and q[2] > zbuf[sy][sx]:
                        zbuf[sy][sx] = q[2]
                        t = tex[min(tu + int(fu * fw), TEX_W - 1), min(tv + int(fv * fh), TEX_H - 1)]
                        px[sx, sy] = shade(t[:3], lum) + (255,)
    return img


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
    atlas, uv = build_atlas()
    for path in (MODEL, TEXTURE, ICON, HITBOX):
        path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(TEXTURE)
    MODEL.write_text(json.dumps(build_model(uv), indent=2) + "\n")
    HITBOX.write_text(json.dumps(build_hitbox(), indent=2) + "\n")
    big = render(atlas, uv, 256, yaw=-35, pitch=28, scale=3.3)
    big.resize((64, 64), Image.LANCZOS).save(ICON)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        render(atlas, uv, 512, yaw=-35, pitch=28, scale=6.6).save(preview / "altar_front.png")
        render(atlas, uv, 512, yaw=145, pitch=28, scale=6.6).save(preview / "altar_back.png")
        render(atlas, uv, 512, yaw=-35, pitch=-20, scale=6.6).save(preview / "altar_below.png")
        atlas.resize((TEX_W * 2, TEX_H * 2), Image.NEAREST).save(preview / "altar_texture.png")


if __name__ == "__main__":
    main()
