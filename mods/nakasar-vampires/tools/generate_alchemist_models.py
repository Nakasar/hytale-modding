#!/usr/bin/env python3
"""Génère les pièces de modèle de l'Alchimiste (boss final de la Tour de l'Alchimiste) et ses quatre piliers
élémentaires.

    python3 mods/nakasar-vampires/tools/generate_alchemist_models.py [--preview DOSSIER]

- Common/NPC/Nakasar/Alchemist_Garb/ : pièces attachées au squelette du joueur (comme les cols des vampires,
  tools/generate_vampire_models.py) par-dessus la robe de mage violette vanilla :
  - sur l'os Head : le masque à bec de cuir (plaque cousue sur le visage, long bec recourbé cerclé de laiton, sangles)
    et ses deux verres violets cerclés de laiton (ce masque est le trophée « Masque de l'Alchimiste ») ;
  - sur l'os Chest : la bavette du tablier de cuir taché, sa poche et ses bretelles ;
  - sur l'os Pelvis : la ceinture de cuir à boucle de laiton, la jupe du tablier et les fioles lumineuses pendues à la
    ceinture (rouge, bleue, jaune, verte, violette).
  Les enfants d'une pièce sont placés par rapport au centre de la boîte de l'os (tête 30 × 28 × 28, verres devant les
  yeux en (±7,5 ; -1,8), face avant vers z = +14 ; torse 28 × 22 × 20 ; bassin 26 × 12 × 18), comme les lunettes de
  gobelin et la robe vanilla (Cosmetics/Face_Accessories/GoblinGoggles, Cosmetics/Overpants/Dress).
- Common/NPC/Nakasar/Alchemist_Pillar_<Élément>/ : pilier de marbre cerclé d'or coiffé d'un cristal de l'élément qui
  flotte et tourne ; il tremble quand on le frappe et le cristal éclate à sa destruction (feu, givre, foudre, racines).
  Server/Models/Nakasar/Nakasar_Alchemist_Pillar_<Élément>.json : modèles (hitbox, lumière de l'élément).

Même repère et même écriture que tools/generate_pumpkin_models.py (64 unités = 1 bloc, face avant vers +Z).
--preview DOSSIER écrit des rendus PNG (le masque et le tablier sur un mannequin, les piliers).
"""
import math
import sys
from pathlib import Path

import generate_pumpkin_models as gpm
from generate_pumpkin_models import Anim, Box, Joint, keys, mix, p_glow, p_round, shade, soft_noise, solid
from PIL import Image

LEATHER = (112, 74, 46)
LEATHER_DARK = (58, 36, 22)
LEATHER_LIGHT = (156, 112, 72)
APRON = (128, 96, 66)
APRON_DARK = (74, 52, 34)
APRON_LIGHT = (170, 136, 98)
BRASS = (196, 150, 64)
BRASS_DARK = (118, 82, 28)
BRASS_LIGHT = (246, 210, 120)
LENS = (196, 120, 255)
LENS_DEEP = (96, 30, 170)
CORK = (150, 110, 70)
MARBLE = (218, 212, 204)
MARBLE_DARK = (150, 144, 140)
MARBLE_LIGHT = (246, 242, 236)
GOLD = (210, 166, 70)
GOLD_DARK = (128, 92, 30)
GOLD_LIGHT = (255, 224, 130)

VIALS = [((255, 120, 60), (190, 30, 10)), ((150, 220, 255), (40, 110, 210)), ((255, 240, 120), (210, 160, 20)),
         ((150, 255, 110), (40, 160, 50)), ((220, 150, 255), (110, 40, 190))]

# Élément de chaque pilier : (cœur du cristal, bord, couleur de la lumière).
ELEMENTS = {
    "Fire": ((255, 170, 70), (200, 40, 10), "#ff7a2a"),
    "Frost": ((200, 240, 255), (60, 140, 220), "#8fd8ff"),
    "Thunder": ((255, 246, 150), (220, 160, 20), "#ffe066"),
    "Root": ((160, 240, 110), (40, 130, 40), "#7dff6a"),
}

GARB = "NPC/Nakasar/Alchemist_Garb"
OUT = gpm.COMMON / GARB


def p_stained(base, dark, light):
    """Cuir de tablier : arrondi comme p_round, avec des taches de réactifs (vert, ocre, violet) et des brûlures."""
    round_paint = p_round(base, dark, light, amp=0.06)
    stains = [(90, 150, 60), (190, 140, 40), (120, 60, 140), (40, 30, 24)]

    def paint(rng, w, h, face):
        img = round_paint(rng, w, h, face)
        px = img.load()
        for _ in range(max(1, w * h // 90)):
            cx, cy, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.8, 2.6)
            col = rng.choice(stains)
            for y in range(max(0, int(cy - r)), min(h, int(cy + r) + 1)):
                for x in range(max(0, int(cx - r)), min(w, int(cx + r) + 1)):
                    if math.hypot(x - cx, y - cy) <= r:
                        px[x, y] = mix(px[x, y][:3], col, 0.55) + (255,)
        return img

    return paint


def p_stitched(base, dark, light):
    """Cuir cousu : arrondi, une couture de points clairs au milieu de chaque grande face."""
    round_paint = p_round(base, dark, light, amp=0.05)

    def paint(rng, w, h, face):
        img = round_paint(rng, w, h, face)
        if w >= 6 and h >= 4:
            px = img.load()
            y = h // 2
            for x in range(1, w - 1, 2):
                px[x, y] = mix(px[x, y][:3], (226, 206, 170), 0.7) + (255,)
        return img

    return paint


def p_lens(c0, c1):
    """Verre : lueur du centre vers le bord et un reflet clair en haut à gauche."""
    glow = p_glow(c0, c1)

    def paint(rng, w, h, face):
        img = glow(rng, w, h, face)
        if w >= 3 and h >= 3:
            img.load()[1, 1] = (255, 255, 255, 255)
        return img

    return paint


def mask():
    """Masque à bec, sur l'os Head (repère : centre de la tête)."""
    leather = p_stitched(LEATHER, LEATHER_DARK, LEATHER_LIGHT)
    dark = p_round(LEATHER_DARK, (30, 18, 12), LEATHER)
    brass = p_round(BRASS, BRASS_DARK, BRASS_LIGHT)
    lens = p_lens(LENS, LENS_DEEP)
    parts = [
        Box("MaskPlate", (0, -5, 15.2), (31, 20, 2), leather),
        Box("MaskBrow", (0, 5.5, 15.4), (31, 2, 2.4), dark),
        Box("StrapL", (15.6, 0, 2), (1.4, 3, 24), dark),
        Box("StrapR", (-15.6, 0, 2), (1.4, 3, 24), dark),
        Box("StrapBack", (0, 0, -14.6), (32.6, 3, 1.4), dark),
    ]
    for side, x in (("L", 7.5), ("R", -7.5)):
        parts += [Box(f"Rim{side}", (x, -1.8, 16.8), (9, 9, 2), brass),
                  Box(f"Lens{side}", (x, -1.8, 18.0), (7, 7, 0.8), lens, shading="fullbright")]
    beak = Joint("Beak", (0, -8, 16.4), [
        Box("Beak1", (0, 0, 3.5), (13, 11, 7), leather),
        Box("BeakBand", (0, 0, 7.2), (13.6, 11.4, 1.2), brass),
        Box("Beak2", (0, -0.6, 10.5), (10, 8.4, 7), leather),
        Box("Beak3", (0, -1.4, 16.5), (7, 6, 6), leather),
        Box("Beak4", (0, -2.2, 21.5), (4.4, 4, 5), leather),
        Box("BeakTip", (0, -3.2, 25.0), (2.4, 2.4, 3), dark),
    ], rot=(24, 0, 0))
    return Joint("Head", (0, 0, 0), parts + [beak])


def bib():
    """Bavette du tablier, sur l'os Chest (repère : centre du torse, devant vers z = +10)."""
    apron = p_stained(APRON, APRON_DARK, APRON_LIGHT)
    dark = p_round(LEATHER_DARK, (30, 18, 12), LEATHER)
    return Joint("Chest", (0, 0, 0), [
        Box("Bib", (0, -2, 12.0), (17, 19, 1), apron),
        Box("BibPocket", (0, -7, 12.7), (9, 6, 0.6), dark),
        Box("BibStrapL", (7.5, 9.5, 11.6), (2, 5, 1), dark),
        Box("BibStrapR", (-7.5, 9.5, 11.6), (2, 5, 1), dark),
        Box("NeckStrap", (0, 11.6, 0), (19, 1.2, 23), dark),
    ])


def belt():
    """Ceinture, jupe du tablier et fioles, sur l'os Pelvis (repère : centre du bassin, devant vers z = +9)."""
    apron = p_stained(APRON, APRON_DARK, APRON_LIGHT)
    dark = p_round(LEATHER_DARK, (30, 18, 12), LEATHER)
    brass = p_round(BRASS, BRASS_DARK, BRASS_LIGHT)
    cork = p_round(CORK, shade(CORK, 0.6), shade(CORK, 1.25))
    parts = [
        Box("Belt", (0, 4, 0), (31, 3.5, 23), dark),
        Box("Buckle", (0, 4, 11.8), (5, 4.4, 1), brass),
        Joint("ApronSkirt", (0, 3, 12.2), [Box("Skirt", (0, -15, 0), (20, 30, 1), apron)], rot=(-7, 0, 0)),
    ]
    spots = [(16.6, -6), (16.6, 0), (16.6, 6), (-16.6, -6), (-16.6, 0), (-16.6, 6), (12.6, 11.4), (-12.6, 11.4)]
    for k, (x, z) in enumerate(spots):
        c0, c1 = VIALS[k % len(VIALS)]
        h = 5 + (k % 2)
        parts += [Box(f"Vial{k}", (x, 3.2 - h / 2, z), (3, h, 3), p_glow(c0, c1), shading="fullbright"),
                  Box(f"Cork{k}", (x, 3.6, z), (2, 1.4, 2), cork)]
    return Joint("Pelvis", (0, 0, 0), parts)


def garb_json(roots, uv):
    """Un fichier, trois pièces (Head, Chest, Pelvis) : les nœuds racines sont des pièces (isPiece)."""
    doc = gpm.model_json(Joint("Garb", (0, 0, 0), roots), uv)
    nodes = doc["nodes"][0]["children"]
    for node in nodes:
        node["shape"]["settings"]["isPiece"] = True
    return {"nodes": nodes, "format": "character", "lod": "auto"}


def mannequin(roots):
    """Pour l'aperçu seulement : boîtes grises du joueur, les pièces posées au centre de leurs os."""
    skin = p_round((150, 120, 170), (80, 60, 100), (190, 160, 210))
    head, chest, pelvis = roots
    return Joint("Mannequin", (0, 0, 0), [
        Joint("HeadBone", (0, 112, 0), [Box("HeadBox", (0, 0, 0), (30, 28, 28), skin), head]),
        Joint("ChestBone", (0, 76, 0), [Box("ChestBox", (0, 0, 0), (28, 22, 20), skin), chest]),
        Joint("PelvisBone", (0, 56, 0), [Box("PelvisBox", (0, 0, 0), (26, 12, 18), skin), pelvis]),
        Box("LegL", (7, 25, 0), (11, 50, 12), skin),
        Box("LegR", (-7, 25, 0), (11, 50, 12), skin),
    ])


def build_garb(preview):
    roots = [mask(), bib(), belt()]
    atlas, uv = gpm.build_atlas(Joint("Garb", (0, 0, 0), roots), 71, 128)
    OUT.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT / "Texture.png")
    gpm.write_json(OUT / "Garb.blockymodel", garb_json(roots, uv))
    if preview:
        body = mannequin(roots)
        atlas2, uv2 = gpm.build_atlas(body, 71, 256)
        for label, view in (("face", {"yaw": 20, "pitch": 8}), ("profil", {"yaw": 90, "pitch": 5}),
                            ("dos", {"yaw": 200, "pitch": 10})):
            img = gpm.render(body, atlas2, uv2, {}, size=360, scale=2.2, center=(0, 80, 0), **view)
            img.save(preview / f"alchimiste_{label}.png")


# --- piliers ---------------------------------------------------------------------------------------

def pillar_model(element):
    c0, c1, _ = ELEMENTS[element]
    marble = p_round(MARBLE, MARBLE_DARK, MARBLE_LIGHT, streaks=2)
    gold = p_round(GOLD, GOLD_DARK, GOLD_LIGHT)
    glow = p_glow(c0, c1)
    column = Joint("Column", (0, 0, 0), [
        Box("Plinth", (0, 6, 0), (44, 12, 44), marble),
        Box("PlinthBand", (0, 12.5, 0), (40, 3, 40), gold),
        Box("Shaft", (0, 52, 0), (28, 78, 28), marble),
        *[Box(f"Band{k}", (0, y, 0), (31, 3, 31), gold) for k, y in enumerate((30, 62))],
        Box("Capital", (0, 94, 0), (38, 8, 38), marble),
        Box("Cup", (0, 100, 0), (30, 4, 30), gold),
        *[Box(f"Rune{k}", (x, 46, z), (w, 12, d), glow, shading="fullbright")
          for k, (x, z, w, d) in enumerate(((0, 14.2, 6, 0.6), (0, -14.2, 6, 0.6), (14.2, 0, 0.6, 6), (-14.2, 0, 0.6, 6)))],
    ])
    crystal = Joint("Crystal", (0, 126, 0), [
        Box("CrystalCore", (0, 0, 0), (16, 30, 16), glow, rot=(0, 45, 0), shading="fullbright"),
        Box("CrystalShardA", (9, -6, 3), (7, 16, 7), glow, rot=(0, 20, -22), shading="fullbright"),
        Box("CrystalShardB", (-8, -7, -4), (6, 14, 6), glow, rot=(0, -30, 20), shading="fullbright"),
        Box("CrystalShardC", (1, -8, -9), (6, 12, 6), glow, rot=(18, 10, 0), shading="fullbright"),
    ])
    return Joint("Body", (0, 0, 0), [column, crystal])


PILLAR_JOINTS = ["Body", "Column", "Crystal"]


def pillar_anims():
    def idle(t):
        u = 2 * math.pi * t / 4.0
        return {"Crystal": ((0, 360 * t / 4.0, 0), (0, 3 * math.sin(u), 0))}

    def hurt(t):
        k = keys(t, [(0, 0), (0.06, 1), (0.3, 0)])
        return {"Column": ((0, 0, 3 * k), (0, 0, 0)), "Crystal": ((0, 0, -8 * k), (2 * k, 0, 0))}

    def death(t):
        k = keys(t, [(0, 0), (0.25, 1), (1.0, 1)])
        sink = keys(t, [(0, 0), (0.3, 0), (1.0, -40)])
        return {"Crystal": ((40 * k, 180 * k, 25 * k), (0, -60 * k, 0)), "Column": ((0, 0, 0), (0, sink, 0))}

    return [
        Anim("Idle", 4.0, idle, step=3, loop=True),
        Anim("Hurt", 0.3, hurt, step=3),
        Anim("Death", 1.0, death, step=3, hold=True),
    ]


def build_pillars(preview):
    for k, element in enumerate(ELEMENTS):
        light = ELEMENTS[element][2]
        gpm.build(f"Alchemist_Pillar_{element}", pillar_model(element), PILLAR_JOINTS, pillar_anims(), 72 + k, 128, {
            "$Comment": f"Pilier élémentaire de la Convergence ({element}), généré par tools/generate_alchemist_models.py : marbre cerclé d'or, cristal de l'élément qui flotte au sommet. Tant qu'il tient, l'Alchimiste peut prendre son élément ; le détruire le retire du cycle.",
            "EyeHeight": 1.6,
            "HitBox": {"Max": {"X": 0.4, "Y": 2.3, "Z": 0.4}, "Min": {"X": -0.4, "Y": 0, "Z": -0.4}},
            "MinScale": 1,
            "MaxScale": 1,
            "Light": {"Color": light, "Radius": 5},
        }, [], preview, [
            ("repos", None, 0, {"size": 240, "scale": 1.3, "center": (0, 72, 0)}),
            ("mort", "Death", 1.0, {"size": 240, "scale": 1.3, "center": (0, 60, 0), "yaw": 70}),
        ] if element == "Fire" else [("repos", None, 0, {"size": 240, "scale": 1.3, "center": (0, 72, 0)})])


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
    build_garb(preview)
    build_pillars(preview)


if __name__ == "__main__":
    main()
