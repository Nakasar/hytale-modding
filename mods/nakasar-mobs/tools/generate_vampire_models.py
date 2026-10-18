#!/usr/bin/env python3
"""
Génère les pièces de modèle propres aux vampires et les icônes d'effets :

- Common/NPC/Nakasar/Vampire/Collar_Count.blockymodel : haut col dressé « à la Dracula » (dos et deux ailes
  évasées autour de la tête, noir dehors, cramoisi dedans, liseré d'or) avec lavallière rouge et rubis.
- Common/NPC/Nakasar/Vampire/Collar_Countess.blockymodel : col Médicis plus large et plus ouvert, pendentif rubis.
- Common/NPC/Nakasar/Vampire/Collar_Texture.png : texture commune des deux cols.
- Common/UI/StatusEffects/Nakasar/*.png : icônes des effets (Domination du comte, toucher glacial du fantôme,
  Emprisonnement du Capitaine de la garde),
  et dans le mod Runes celles de la rune de Domination et des Chaînes spectrales.

Les cols sont des pièces attachées à l'os « Chest » du squelette du joueur (Player) : elles suivent
ses animations, comme les capes vanilla (même repère que Cosmetics/Capes/Cape_King.blockymodel).

Usage : python3 mods/nakasar-mobs/tools/generate_vampire_models.py
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
MOBS_COMMON = ROOT / "mods/nakasar-mobs/src/main/resources/Common"
RUNES_COMMON = ROOT / "mods/nakasar-runes/src/main/resources/Common"
VAMPIRE_DIR = MOBS_COMMON / "NPC/Nakasar/Vampire"

# Zones de la texture des cols (128 x 64) : chaque face pioche dans une zone unie.
TEXTURE_SIZE = (128, 64)
ZONES = {
    "black": (0, 0),     # velours noir, 64 x 32
    "crimson": (64, 0),  # doublure cramoisie, 64 x 32
    "gold": (0, 32),     # liseré d'or, 32 x 32
    "ruby": (32, 32),    # rubis, 16 x 16
    "red": (64, 32),     # lavallière rouge sang, 32 x 32
}


def quat(pitch=0.0, yaw=0.0, roll=0.0):
    """Quaternion (x, y, z, w) d'une rotation en degrés, appliquée dans l'ordre Y, X puis Z."""
    def axis(ax, deg):
        h = math.radians(deg) / 2
        s = math.sin(h)
        return {"x": (s, 0, 0, math.cos(h)), "y": (0, s, 0, math.cos(h)), "z": (0, 0, s, math.cos(h))}[ax]

    def mul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz)

    q = mul(mul(axis("y", yaw), axis("x", pitch)), axis("z", roll))
    return dict(zip("xyzw", (round(v, 5) for v in q)))


class Model:
    def __init__(self):
        self.next_id = 1

    def node_id(self):
        self.next_id += 1
        return str(self.next_id)

    def box(self, name, pos, size, offset=(0, 0, 0), rot=(0, 0, 0), faces=None):
        """Pavé ; faces = {"front": zone, ...} (front = +Z, vers la tête ou vers l'avant)."""
        sx, sy, sz = size
        dims = {"front": (sx, sy), "back": (sx, sy), "left": (sz, sy), "right": (sz, sy),
                "top": (sx, sz), "bottom": (sx, sz)}
        layout = {}
        for face, zone in faces.items():
            ox, oy = ZONES[zone]
            w, h = dims[face]
            assert w <= 64 and h <= 32, (name, face, w, h)
            layout[face] = {"offset": {"x": ox + 1, "y": oy + 1}, "mirror": {"x": False, "y": False}, "angle": 0}
        return {
            "id": self.node_id(),
            "name": name,
            "position": dict(zip("xyz", pos)),
            "orientation": quat(*rot),
            "shape": {
                "type": "box",
                "offset": dict(zip("xyz", offset)),
                "stretch": {"x": 1, "y": 1, "z": 1},
                "settings": {"isPiece": False, "size": dict(zip("xyz", size))},
                "textureLayout": layout,
                "unwrapMode": "custom",
                "visible": True,
                "doubleSided": False,
                "shadingMode": "flat",
            },
        }

    def chest_piece(self, children):
        # Même en-tête que la pièce « Chest » des capes vanilla : les enfants sont dans le repère du col de Cape_King.
        return {
            "nodes": [{
                "id": "1",
                "name": "Chest",
                "position": {"x": 0, "y": 15, "z": 0},
                "orientation": {"x": 0, "y": 0, "z": 0, "w": 1},
                "shape": {
                    "type": "none",
                    "offset": {"x": 0, "y": 11, "z": 0},
                    "stretch": {"x": 1, "y": 1, "z": 1},
                    "settings": {"isPiece": True},
                    "textureLayout": {},
                    "unwrapMode": "custom",
                    "visible": True,
                    "doubleSided": False,
                    "shadingMode": "flat",
                },
                "children": children,
            }],
            "format": "character",
            "lod": "auto",
        }


def panel(m, name, pos, w, h, offset, rot):
    """Pan de col épais d'une unité : cramoisi côté tête, noir dehors, tranches dorées."""
    return m.box(name, pos, (w, h, 1), offset, rot,
                 {"front": "crimson", "back": "black", "left": "gold", "right": "gold", "top": "gold", "bottom": "black"})


def collar_count():
    m = Model()
    children = [
        # Col montant autour du cou (au niveau de celui de Cape_King).
        m.box("NeckBand", (0, 9, -1), (32, 5, 22), (0, 0, 0), (0, 0, 0),
              {"front": "black", "back": "black", "left": "black", "right": "black", "top": "gold", "bottom": "black"}),
        # Dos du col, dressé derrière la tête et légèrement renversé.
        panel(m, "CollarBack", (0, 10, -13), 26, 26, (0, 13, 0), (-14, 0, 0)),
        # Ailes évasées de chaque côté de la tête, bord extérieur ramené vers l'avant.
        panel(m, "CollarWing-L", (12, 10, -10), 14, 24, (7, 12, 0), (-8, -38, -16)),
        panel(m, "CollarWing-R", (-12, 10, -10), 14, 24, (-7, 12, 0), (-8, 38, 16)),
        # Lavallière rouge sur le jabot et broche en rubis.
        m.box("Cravat", (0, 3.5, 12.5), (8, 7, 2), (0, 0, 0), (0, 0, 0),
              {"front": "red", "back": "red", "left": "red", "right": "red", "top": "red", "bottom": "red"}),
        m.box("Brooch", (0, 4.5, 13.8), (3, 3, 1), (0, 0, 0), (0, 0, 45),
              {"front": "ruby", "back": "ruby", "left": "gold", "right": "gold", "top": "gold", "bottom": "gold"}),
    ]
    return m.chest_piece(children)


def collar_countess():
    m = Model()
    children = [
        m.box("NeckBand", (0, 9, -1), (30, 4, 21), (0, 0, 0), (0, 0, 0),
              {"front": "black", "back": "black", "left": "black", "right": "black", "top": "gold", "bottom": "black"}),
        # Col Médicis : large éventail derrière la tête, plus ouvert que celui du comte.
        panel(m, "CollarBack", (0, 9, -12), 34, 22, (0, 11, 0), (-24, 0, 0)),
        panel(m, "CollarWing-L", (14, 9, -9), 16, 20, (8, 10, 0), (-18, -52, -22)),
        panel(m, "CollarWing-R", (-14, 9, -9), 16, 20, (-8, 10, 0), (-18, 52, 22)),
        # Ras-de-cou doré et pendentif rubis.
        m.box("Pendant", (0, 5.5, 12.2), (4, 5, 1), (0, 0, 0), (0, 0, 0),
              {"front": "ruby", "back": "ruby", "left": "gold", "right": "gold", "top": "gold", "bottom": "gold"}),
    ]
    return m.chest_piece(children)


def noise(x, y, seed):
    return ((x * 73856093) ^ (y * 19349663) ^ seed) % 7 - 3


def collar_texture():
    img = Image.new("RGBA", TEXTURE_SIZE, (0, 0, 0, 0))
    px = img.load()

    def fill(zone, w, h, base, shade, seed):
        ox, oy = ZONES[zone]
        for x in range(w):
            for y in range(h):
                n = noise(x, y, seed)
                t = y / max(h - 1, 1)
                r, g, b = (int(base[i] + (shade[i] - base[i]) * t) + n for i in range(3))
                px[ox + x, oy + y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), 255)

    fill("black", 64, 32, (28, 22, 30), (14, 10, 16), 11)
    fill("crimson", 64, 32, (150, 18, 34), (96, 8, 22), 23)
    fill("gold", 32, 32, (222, 182, 70), (170, 128, 40), 37)
    fill("ruby", 16, 16, (230, 30, 60), (130, 6, 30), 41)
    fill("red", 32, 32, (176, 20, 30), (120, 10, 20), 53)
    return img


def icon(draw_fn, size=128):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_fn(d, size)
    return img


def draw_domination(d, s):
    # Œil rouge à pupille fendue, cerclé de violet : « tu ne peux plus le blesser ».
    d.ellipse((6, 6, s - 6, s - 6), fill=(40, 6, 34, 235), outline=(178, 63, 255, 255), width=6)
    d.polygon([(16, s // 2), (s // 2, 30), (s - 16, s // 2), (s // 2, s - 30)], fill=(230, 40, 60, 255))
    d.ellipse((s // 2 - 16, s // 2 - 16, s // 2 + 16, s // 2 + 16), fill=(255, 154, 213, 255))
    d.ellipse((s // 2 - 5, s // 2 - 15, s // 2 + 5, s // 2 + 15), fill=(20, 0, 12, 255))


def draw_chill(d, s):
    # Flocon bleu pâle.
    c = s // 2
    d.ellipse((6, 6, s - 6, s - 6), fill=(16, 40, 70, 235), outline=(111, 183, 255, 255), width=6)
    for k in range(6):
        a = math.radians(60 * k)
        d.line((c, c, c + math.cos(a) * 42, c + math.sin(a) * 42), fill=(216, 244, 255, 255), width=8)
        bx, by = c + math.cos(a) * 28, c + math.sin(a) * 28
        for b in (-45, 45):
            ba = a + math.radians(b)
            d.line((bx, by, bx + math.cos(ba) * 14, by + math.sin(ba) * 14), fill=(216, 244, 255, 255), width=5)


def draw_chains(d, s):
    # Maillons de chaîne verts spectraux.
    d.ellipse((6, 6, s - 6, s - 6), fill=(10, 40, 24, 235), outline=(93, 255, 138, 255), width=6)
    for i, c in enumerate((40, 64, 88)):
        # Maillons alternés le long de la diagonale : ovale couché, ovale debout, ovale couché.
        w, h = (20, 11) if i % 2 == 0 else (11, 20)
        d.ellipse((c - w, c - h, c + w, c + h), outline=(200, 255, 215, 255), width=7)


def draw_imprisoned(d, s):
    # Barreaux de cellule gris fer sur fond sombre (Emprisonnement du Capitaine de la garde).
    d.ellipse((6, 6, s - 6, s - 6), fill=(30, 32, 38, 235), outline=(154, 164, 176, 255), width=6)
    for x in (40, 64, 88):
        d.rectangle((x - 5, 22, x + 5, s - 22), fill=(190, 198, 208, 255))
    d.rectangle((26, 40, s - 26, 48), fill=(120, 128, 140, 255))
    d.rectangle((26, s - 48, s - 26, s - 40), fill=(120, 128, 140, 255))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    write_json(VAMPIRE_DIR / "Collar_Count.blockymodel", collar_count())
    write_json(VAMPIRE_DIR / "Collar_Countess.blockymodel", collar_countess())
    collar_texture().save(VAMPIRE_DIR / "Collar_Texture.png")
    icons = {
        MOBS_COMMON / "UI/StatusEffects/Nakasar/Count_Domination.png": draw_domination,
        MOBS_COMMON / "UI/StatusEffects/Nakasar/Ghost_Chill.png": draw_chill,
        MOBS_COMMON / "UI/StatusEffects/Nakasar/Imprisoned.png": draw_imprisoned,
        RUNES_COMMON / "UI/StatusEffects/Nakasar/Dominated.png": draw_domination,
        RUNES_COMMON / "UI/StatusEffects/Nakasar/Spectral_Chains.png": draw_chains,
    }
    for path, fn in icons.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        icon(fn).save(path)
    print("OK : cols et icônes générés")


if __name__ == "__main__":
    main()
