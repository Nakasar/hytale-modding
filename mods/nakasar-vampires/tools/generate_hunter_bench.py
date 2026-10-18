#!/usr/bin/env python3
"""Génère le modèle, la texture, la hitbox et les icônes de l'établi des chasseurs de vampires.

Usage : python3 mods/nakasar-vampires/tools/generate_hunter_bench.py [--preview DOSSIER]

Même gabarit que l'autel sacrificiel (generate_altar.py, dont on réutilise la peinture,
l'atlas, l'écriture du .blockymodel et le rendu des icônes) : 2 blocs de large (X), 1 de
profondeur (Z), bloc d'ancrage = celui posé par le joueur, le modèle s'étend vers +X.
Une table de bois sombre ferrée d'argent, un râtelier à pieux au dos, et sur le plateau
une arbalète, des lingots d'argent, des gousses d'ail, un grimoire et une lanterne de feu
purificateur (flamme blanche, non éclairée par la scène).

Écrit aussi les icônes des onglets de l'établi (Icons/CraftingCategories/Nakasar/) et celles
des effets des runes de chasseur (UI/StatusEffects/Nakasar/Light_Aura.png, Invisible.png).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import generate_altar as ga

ROOT = ga.ROOT
MODEL = ROOT / "Common/Blocks/Nakasar/Hunter_Workbench.blockymodel"
TEXTURE = ROOT / "Common/BlockTextures/Nakasar/Hunter_Workbench.png"
ICON = ROOT / "Common/Icons/Items/Nakasar/Hunter_Workbench.png"
HITBOX = ROOT / "Server/Item/Block/Hitboxes/Nakasar/Nakasar_Hunter_Workbench.json"
CATEGORIES = ROOT / "Common/Icons/CraftingCategories/Nakasar"
STATUS = ROOT / "Common/UI/StatusEffects/Nakasar"

WOOD = (104, 72, 50)
WOOD_DARK = (70, 48, 36)
WOOD_LIGHT = (138, 100, 70)
SILVER = (196, 204, 214)
SILVER_DARK = (138, 146, 160)
IRON = (84, 86, 94)
GARLIC = (232, 226, 206)
BOOK = (92, 30, 34)
PAPER = (226, 214, 180)
FLAME = (236, 244, 255)


def wood(base, grain=True):
    """Bois : la peinture de pierre de l'autel, plus des veines horizontales sombres."""
    def painter(w, h, kind, face):
        img = ga.paint_stone(w, h, base, kind)
        if grain and kind != "bottom" and w > 4:
            d = ImageDraw.Draw(img)
            for y in range(2, h - 1, 4 if kind == "top" else 3):
                d.line((1, y, w - 2, y), fill=ga.shade(base, 0.78) + (255,))
        return img
    return painter


def metal(color):
    return lambda w, h, kind, face: ga.paint_flat(w, h, color, kind, top_color=ga.shade(color, 1.1))


def flame(w, h, kind, face):
    return ga.paint_flat(w, h, FLAME, "top", top_color=FLAME)


def book(w, h, kind, face):
    img = ga.paint_flat(w, h, BOOK, kind, top_color=ga.shade(BOOK, 1.1))
    if face in ("left", "right") and kind == "side":
        ImageDraw.Draw(img).line((1, h - 1, w - 2, h - 1), fill=PAPER + (255,))
    return img


CX = 16
PARTS = [
    # table
    ("Top", (CX, 23, 0), (62, 4, 28), 0, wood(WOOD_LIGHT), "flat"),
    ("Top_Band_Front", (CX, 20, 13), (60, 2, 1), 0, metal(SILVER_DARK), "flat"),
    ("Top_Band_Back", (CX, 20, -13), (60, 2, 1), 0, metal(SILVER_DARK), "flat"),
    ("Shelf", (CX, 6, 0), (56, 2, 24), 0, wood(WOOD), "flat"),
]
for n, (x, z) in enumerate([(-13, -11), (45, -11), (-13, 11), (45, 11)]):
    PARTS.append((f"Leg_{n}", (x, 10.5, z), (4, 21, 4), 0, wood(WOOD_DARK, grain=False), "flat"))
# râtelier au dos : deux montants, une planche, des pieux d'argent
PARTS += [
    ("Rack_Post_L", (-12, 36, -12), (3, 22, 3), 0, wood(WOOD_DARK, grain=False), "flat"),
    ("Rack_Post_R", (44, 36, -12), (3, 22, 3), 0, wood(WOOD_DARK, grain=False), "flat"),
    ("Rack_Board", (CX, 40, -12.5), (54, 10, 2), 0, wood(WOOD), "flat"),
    ("Rack_Rail", (CX, 46, -11), (58, 2, 2), 0, metal(IRON), "flat"),
]
for i, x in enumerate(range(-6, 40, 7)):
    PARTS += [
        (f"Stake_{i}", (x, 38, -10.5), (2, 14, 2), 0, wood(WOOD_LIGHT, grain=False), "flat"),
        (f"Stake_{i}_Tip", (x, 30.5, -10.5), (1, 2, 1), 0, metal(SILVER), "flat"),
    ]
# arbalète posée sur le plateau
PARTS += [
    ("Crossbow_Stock", (2, 26, 3), (20, 2, 3), 0, wood(WOOD_DARK, grain=False), "flat"),
    ("Crossbow_Arms", (10, 26, 3), (2, 2, 18), 0, metal(IRON), "flat"),
    ("Crossbow_Bolt", (4, 27.5, 3), (16, 1, 1), 0, metal(SILVER), "flat"),
]
# lingots d'argent empilés
for i, (x, y, z) in enumerate([(22, 26, 6), (27, 26, 6), (24.5, 28, 6)]):
    PARTS.append((f"Silver_Bar_{i}", (x, y, z), (4, 2, 7), 0, metal(SILVER), "flat"))
# gousses d'ail
for i, (x, z) in enumerate([(31, -4), (34, -2), (32, 1)]):
    PARTS += [
        (f"Garlic_{i}", (x, 26.5, z), (3, 3, 3), 45, metal(GARLIC), "flat"),
        (f"Garlic_{i}_Stem", (x, 28.5, z), (1, 1, 1), 0, metal(ga.shade(GARLIC, 0.8)), "flat"),
    ]
# grimoire
PARTS.append(("Book", (20, 26, -5), (8, 2, 10), 15, book, "flat"))
# lanterne de feu purificateur
PARTS += [
    ("Lantern_Base", (41, 25.5, 0), (6, 1, 6), 0, metal(IRON), "flat"),
    ("Lantern_Glass", (41, 29, 0), (4, 6, 4), 0, flame, "fullbright"),
    ("Lantern_Post_A", (38.5, 29, -2.5), (1, 6, 1), 0, metal(IRON), "flat"),
    ("Lantern_Post_B", (43.5, 29, -2.5), (1, 6, 1), 0, metal(IRON), "flat"),
    ("Lantern_Post_C", (38.5, 29, 2.5), (1, 6, 1), 0, metal(IRON), "flat"),
    ("Lantern_Post_D", (43.5, 29, 2.5), (1, 6, 1), 0, metal(IRON), "flat"),
    ("Lantern_Cap", (41, 32.5, 0), (6, 1, 6), 0, metal(IRON), "flat"),
    ("Lantern_Ring", (41, 34, 0), (2, 2, 1), 0, metal(IRON), "flat"),
]


def build_hitbox():
    def box(x0, y0, z0, x1, y1, z1):
        return {"Min": {"X": ga.to_block(x0, "x"), "Y": ga.to_block(y0, "y"), "Z": ga.to_block(z0, "z")},
                "Max": {"X": ga.to_block(x1, "x"), "Y": ga.to_block(y1, "y"), "Z": ga.to_block(z1, "z")}}
    # table pleine sur 2 x 1 blocs (les blocs de remplissage), râtelier au dos
    return {"Boxes": [box(-16, 0, -16, 48, 25, 16), box(-14, 25, -16, 46, 47, -9)]}


def category_icons():
    """Icônes 64x64 des onglets : runes (déjà là), feux purificateurs, fragment."""
    CATEGORIES.mkdir(parents=True, exist_ok=True)
    fire = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(fire)
    d.rectangle((29, 30, 35, 58), fill=WOOD_DARK + (255,))
    d.rectangle((26, 26, 38, 31), fill=IRON + (255,))
    d.polygon([(32, 4), (42, 22), (38, 28), (26, 28), (22, 22)], fill=(170, 200, 255, 255))
    d.polygon([(32, 11), (37, 22), (34, 27), (30, 27), (27, 22)], fill=FLAME + (255,))
    fire.save(CATEGORIES / "Purifying_Fire.png")
    portal = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(portal)
    d.polygon([(32, 4), (52, 30), (32, 60), (12, 30)], fill=(96, 20, 36, 255), outline=(40, 8, 16, 255))
    d.polygon([(32, 14), (44, 30), (32, 50), (20, 30)], fill=(196, 44, 64, 255))
    d.polygon([(32, 20), (38, 30), (32, 40), (26, 30)], fill=(255, 150, 160, 255))
    portal.save(CATEGORIES / "Fragment.png")


def status_icons(size=128):
    """Icônes d'effets, même format que generate_vampire_models.py (128 px, disque cerclé)."""
    STATUS.mkdir(parents=True, exist_ok=True)
    c = size // 2
    aura = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(aura)
    d.ellipse((6, 6, size - 6, size - 6), fill=(60, 44, 16, 235), outline=(255, 222, 140, 255), width=6)
    for k in range(12):
        a = math.radians(30 * k)
        r0, r1 = 26, 46 if k % 2 == 0 else 38
        d.line((c + math.cos(a) * r0, c + math.sin(a) * r0, c + math.cos(a) * r1, c + math.sin(a) * r1),
               fill=(255, 236, 180, 255), width=7)
    d.ellipse((c - 20, c - 20, c + 20, c + 20), fill=(255, 250, 230, 255))
    aura.save(STATUS / "Light_Aura.png")
    hidden = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(hidden)
    d.ellipse((6, 6, size - 6, size - 6), fill=(24, 28, 40, 235), outline=(150, 162, 186, 255), width=6)
    # œil fermé : paupière en arc et cils
    d.arc((26, 34, size - 26, size - 30), 20, 160, fill=(214, 222, 240, 255), width=8)
    for k in range(5):
        a = math.radians(40 + 25 * k)
        x, y = c + math.cos(a) * 38, c - 2 + math.sin(a) * 30
        d.line((x, y, x + math.cos(a) * 12, y + math.sin(a) * 12), fill=(214, 222, 240, 255), width=5)
    hidden.save(STATUS / "Invisible.png")


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
    ga.PARTS = PARTS
    ga.TEX_W, ga.TEX_H = 256, 128
    atlas, uv = ga.build_atlas()
    for path in (MODEL, TEXTURE, ICON, HITBOX):
        path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(TEXTURE)
    model = ga.build_model(uv)
    model["nodes"][0]["name"] = "Hunter_Workbench"
    MODEL.write_text(json.dumps(model, indent=2) + "\n")
    HITBOX.write_text(json.dumps(build_hitbox(), indent=2) + "\n")
    center = (16, 26, 0)
    big = ga.render(atlas, uv, 256, yaw=-35, pitch=28, scale=3.3, center=center)
    big.resize((64, 64), Image.LANCZOS).save(ICON)
    category_icons()
    status_icons()
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        ga.render(atlas, uv, 512, yaw=-35, pitch=28, scale=6.6, center=center).save(preview / "hunter_bench_front.png")
        ga.render(atlas, uv, 512, yaw=145, pitch=28, scale=6.6, center=center).save(preview / "hunter_bench_back.png")


if __name__ == "__main__":
    main()
