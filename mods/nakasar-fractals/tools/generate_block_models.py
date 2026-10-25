"""Modèles 3D des blocs du mod Fractales (passe « vrais assets 3D ») et cubes repeints dans le même style.

Chaque bloc a un modèle .blockymodel, son atlas peint et une icône rendue depuis le modèle ; `block_type(tex)` rend les
clés du BlockType (DrawType Model, CustomModel, animation en boucle, particules) que generate_observatory.py pose sur
l'objet. Format et style copiés des blocs vanilla lus dans Assets.zip 0.7.2 (coffre Chest_Epic_Small, feu de camp,
torche) : 32 unités par bloc, origine au centre du bas, face avant vers +Z.

    python generate_block_models.py [--preview DOSSIER]   # écrit les modèles ; --preview : planche d'aperçu
"""
import json
import math
import random
import sys
import zlib
from pathlib import Path

from PIL import Image

import fractal_blocks as fb

ROOT = Path(__file__).resolve().parent.parent / "src/main/resources"
COMMON = ROOT / "Common"
MODELS = "Blocks/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"
CUBE_TEXTURES = "BlockTextures/Nakasar/Fractals"

# Palette de l'Observatoire : pierre gris-bleu, laiton, bois sombre, cristal des Brumes violet.
STONE = (128, 134, 160)
STONE_DARK = (92, 96, 124)
BRASS = (204, 158, 76)
GOLD = (232, 190, 96)
WOOD = (96, 62, 44)
WOOD_DARK = (70, 44, 34)
MIST_DARK = (110, 60, 190)
MIST_LIGHT = (230, 200, 255)
MIST = (186, 140, 255)
SOCKET = (34, 30, 48)


def part(name, center, size, paint, **kw):
    return dict(name=name, center=center, size=size, paint=paint, **kw)


def inlay(name, center, size, color, kind, faces, parent=None):
    """Rune lumineuse plaquée sur une face (0,5 unité d'épaisseur, fond transparent)."""
    return part(name, center, size, fb.glyph(color, kind, faces), glow=True, parent=parent)


# ---------------------------------------------------------------- modèles

def selection_console():
    """Pupitre de pierre sur le socle de l'Astrolabe : alvéole ronde (noyau), fente (diapason), cadran qui tourne."""
    s = fb.smooth_stone(STONE)
    p = [
        part("Base", (0, 2, 0), (30, 4, 30), s),
        part("Shaft", (0, 10, 0), (20, 12, 20), fb.stone(STONE_DARK, (7, 4))),
        inlay("Rune_Front", (0, 10, 10.25), (10, 9, 0.5), MIST, "ring", ("front",)),
        inlay("Rune_Back", (0, 10, -10.25), (10, 9, 0.5), MIST, "ring", ("back",)),
        inlay("Rune_Right", (10.25, 10, 0), (0.5, 9, 10), MIST, "ring", ("right",)),
        inlay("Rune_Left", (-10.25, 10, 0), (0.5, 9, 10), MIST, "ring", ("left",)),
        part("Band", (0, 17, 0), (22, 2, 22), fb.metal(BRASS)),
        part("Top", (0, 20.5, 0), (28, 5, 28), s),
        part("Rim_Front", (0, 23.5, 13), (28, 1, 2), fb.metal(GOLD, False)),
        part("Rim_Back", (0, 23.5, -13), (28, 1, 2), fb.metal(GOLD, False)),
        part("Rim_Right", (13, 23.5, 0), (2, 1, 24), fb.metal(GOLD, False)),
        part("Rim_Left", (-13, 23.5, 0), (2, 1, 24), fb.metal(GOLD, False)),
        part("Core_Socket", (-5, 23.5, 4), (11, 1, 11), fb.metal(BRASS, False)),
        part("Core_Hole", (-5, 23.6, 4), (7, 1.1, 7), fb.solid(SOCKET)),
        part("Core_Glow", (-5, 24.1, 4), (3, 0.4, 3), fb.crystal(MIST_DARK, MIST_LIGHT), glow=True),
        part("Fork_Socket", (7, 23.5, 4), (5, 1, 12), fb.metal(BRASS, False)),
        part("Fork_Slot", (7, 23.6, 4), (2, 1.1, 9), fb.solid(SOCKET)),
        part("Dial_Post", (0, 28, -9), (3, 8, 3), fb.metal(BRASS)),
        part("Dial", (0, 37, -9), (16, 10, 2), fb.metal(GOLD), pivot=(0, 37, -9)),
        part("Dial_Cross", (0, 37, -9.1), (10, 16, 1.8), fb.metal(GOLD), parent="Dial"),
        inlay("Dial_Ticks", (0, 37, -7.75), (12, 12, 0.5), MIST_LIGHT, "ring", ("front",), parent="Dial"),
        part("Dial_Hand", (0, 40, -7.6), (1.5, 6, 0.6), fb.crystal(MIST_DARK, MIST_LIGHT), glow=True, parent="Dial"),
        part("Dial_Gem", (0, 37, -7.5), (3, 3, 1), fb.crystal(MIST_DARK, MIST_LIGHT), glow=True, parent="Dial"),
    ]
    a = fb.anim(240, {"Dial": {"orientation": [(0, (0, 0, 0)), (60, (0, 0, -90)), (120, (0, 0, -180)),
                                               (180, (0, 0, -270)), (240, (0, 0, -360))]}})
    return p, a


def resonator():
    """Diapason géant en laiton planté dans un socle, cristal des Brumes qui flotte entre les branches."""
    c = fb.crystal(MIST_DARK, MIST_LIGHT)
    p = [
        part("Base", (0, 3, 0), (22, 6, 22), fb.stone(STONE_DARK, (7, 5))),
        inlay("Rune_Front", (0, 3, 11.25), (5, 5, 0.5), MIST, "fork", ("front",)),
        inlay("Rune_Back", (0, 3, -11.25), (5, 5, 0.5), MIST, "fork", ("back",)),
        part("Band", (0, 6.5, 0), (14, 1, 14), fb.metal(BRASS, False)),
        part("Stem", (0, 12, 0), (4, 10, 4), fb.metal(BRASS)),
        part("Collar", (0, 15, 0), (6, 2, 6), fb.metal(GOLD, False)),
        part("Bridge", (0, 18.5, 0), (17, 3, 4), fb.metal(BRASS)),
        part("Prong_L", (-6.5, 31, 0), (3, 22, 3), fb.metal(BRASS, False), pivot=(-6.5, 20, 0)),
        part("Prong_R", (6.5, 31, 0), (3, 22, 3), fb.metal(BRASS, False), pivot=(6.5, 20, 0)),
        part("Cap_L", (-6.5, 43, 0), (4, 2, 4), fb.metal(GOLD, False), parent="Prong_L"),
        part("Cap_R", (6.5, 43, 0), (4, 2, 4), fb.metal(GOLD, False), parent="Prong_R"),
        part("Crystal", (0, 30, 0), (5, 9, 5), c, glow=True, rot=(0, 45, 0)),
        part("Crystal_Tip", (0, 36, 0), (3, 3, 3), c, glow=True, rot=(0, 45, 0)),
        part("Crystal_Foot", (0, 24.5, 0), (3, 2, 3), c, glow=True, rot=(0, 45, 0)),
    ]
    bob = [(0, (0, 0, 0)), (60, (0, 1.5, 0)), (120, (0, 0, 0))]
    a = fb.anim(120, {
        "Crystal": {"position": bob}, "Crystal_Tip": {"position": bob}, "Crystal_Foot": {"position": bob},
        "Prong_L": {"orientation": [(0, (0, 0, 0)), (30, (0, 0, 1.2)), (60, (0, 0, 0)), (90, (0, 0, -1.2)),
                                    (120, (0, 0, 0))]},
        "Prong_R": {"orientation": [(0, (0, 0, 0)), (30, (0, 0, -1.2)), (60, (0, 0, 0)), (90, (0, 0, 1.2)),
                                    (120, (0, 0, 0))]},
    })
    return p, a


def reward_chest():
    """Coffre bombé cerclé de laiton, serrure en cristal : mêmes nœuds que le coffre vanilla (couvercle « Lid »)."""
    wood = fb.planks(WOOD_DARK, 5, vertical=False)
    p = [
        part("Block", (0, 9, 0), (30, 16, 23), wood),
        part("Frame", (0, 2, 0), (32, 4, 26), fb.metal(BRASS), parent="Block"),
        part("Corner_FL", (-12.5, 4, 10.5), (6, 6, 6), fb.metal(GOLD), parent="Frame"),
        part("Corner_FR", (12.5, 4, 10.5), (6, 6, 6), fb.metal(GOLD), parent="Frame"),
        part("Corner_BL", (-12.5, 4, -10.5), (6, 6, 6), fb.metal(GOLD), parent="Frame"),
        part("Corner_BR", (12.5, 4, -10.5), (6, 6, 6), fb.metal(GOLD), parent="Frame"),
        part("Lid", (0, 23.5, 0), (29, 13, 24), wood, pivot=(0, 17, -12)),
        part("Lid_Frame_R", (12, 23.5, 0), (4, 14, 25), fb.metal(BRASS), parent="Lid"),
        part("Lid_Frame_L", (-12, 23.5, 0), (4, 14, 25), fb.metal(BRASS), parent="Lid"),
        part("Lock_Plate", (0, 18, 12.5), (10, 10, 2), fb.metal(GOLD), parent="Lid"),
        part("Lock", (0, 18, 13.75), (5, 6, 1), fb.crystal(MIST_DARK, MIST_LIGHT), glow=True, parent="Lid"),
        inlay("Lid_Rune", (0, 30.25, 0), (14, 0.5, 14), MIST, "ring", ("top",), parent="Lid"),
    ]
    return p, None


def exit_stone():
    """Menhir runique : rune des Brumes devant et derrière, deux éclats qui tournent autour."""
    s = fb.stone(STONE, (9, 6))
    c = fb.crystal(MIST_DARK, MIST_LIGHT)
    p = [
        part("Rubble_1", (-10, 2, 6), (7, 4, 6), fb.smooth_stone(STONE_DARK), rot=(0, 20, 0)),
        part("Rubble_2", (10, 1.5, -5), (6, 3, 6), fb.smooth_stone(STONE_DARK), rot=(0, 35, 0)),
        part("Base", (0, 3, 0), (20, 6, 16), fb.smooth_stone(STONE_DARK)),
        part("Body", (0, 17, 0), (17, 22, 13), s),
        part("Upper", (0, 33, 0), (14, 10, 11), s),
        part("Cap", (0, 40, 0), (10, 4, 8), fb.smooth_stone(STONE), rot=(0, 8, 0)),
        inlay("Rune_Front", (0, 19, 6.75), (11, 11, 0.5), MIST, "eye", ("front",)),
        inlay("Rune_Back", (0, 19, -6.75), (11, 11, 0.5), MIST, "eye", ("back",)),
        part("Shard_A", (13, 26, 0), (3, 5, 3), c, glow=True, pivot=(0, 26, 0)),
        part("Shard_B", (-13, 32, 0), (2, 4, 2), c, glow=True, pivot=(0, 32, 0)),
    ]
    spin = [(0, (0, 0, 0)), (60, (0, 90, 0)), (120, (0, 180, 0)), (180, (0, 270, 0)), (240, (0, 360, 0))]
    a = fb.anim(240, {"Shard_A": {"orientation": spin}, "Shard_B": {"orientation": spin}})
    return p, a


def mists_portal():
    """Portail des Brumes : arche de pierre 3 × 4 blocs, bandes de laiton, voile de brume, clé de voûte de cristal."""
    s = fb.stone(STONE, (9, 6))
    dark = fb.smooth_stone(STONE_DARK)
    c = glow(MIST)
    p = [
        part("Base", (0, 2, 0), (100, 4, 18), fb.stone(STONE_DARK, (10, 6))),
        part("Pillar_L", (-41, 62, 0), (14, 116, 14), s),
        part("Pillar_R", (41, 62, 0), (14, 116, 14), s),
        part("Foot_L", (-41, 8, 0), (18, 8, 18), dark),
        part("Foot_R", (41, 8, 0), (18, 8, 18), dark),
        part("Lintel", (0, 124, 0), (100, 10, 16), s),
        part("Lintel_Cap", (0, 130.5, 0), (90, 3, 12), dark),
        part("Keystone", (0, 120, 0), (14, 16, 18), dark),
        part("Keystone_Gem", (0, 138, 0), (8, 10, 8), c, glow=True, rot=(0, 45, 0)),
        part("Veil", (0, 62, 0), (68, 112, 1), fb.mist(MIST_DARK, MIST_LIGHT, 200), glow=True),
    ]
    for side, x in (("L", -41), ("R", 41)):
        for k, y in enumerate((30, 62, 94)):
            p.append(part(f"Band_{side}_{k + 1}", (x, y, 0), (15, 2, 15), fb.metal(BRASS, False)))
        p.append(inlay(f"Rune_{side}_Front", (x, 46, 7.25), (9, 9, 0.5), MIST, "eye", ("front",)))
        p.append(inlay(f"Rune_{side}_Back", (x, 46, -7.25), (9, 9, 0.5), MIST, "eye", ("back",)))
        p.append(inlay(f"Rune_{side}_Front_2", (x, 78, 7.25), (9, 9, 0.5), MIST, "ring", ("front",)))
        p.append(inlay(f"Rune_{side}_Back_2", (x, 78, -7.25), (9, 9, 0.5), MIST, "ring", ("back",)))
    tracks = {
        "Keystone_Gem": {"position": bob(2, 120), "orientation": spin_y(240)},
        "Veil": {"shapeStretch": [(0, (1, 1, 1)), (60, (1.02, 0.99, 1)), (120, (0.98, 1.01, 1)), (180, (1, 1, 1))]},
    }
    return p, fb.anim(240, tracks)


def archivist_counter():
    """Comptoir de l'Archiviste : bois sombre, balance de laiton, registre ouvert, bocal d'éclats."""
    c = fb.crystal(MIST_DARK, MIST_LIGHT)
    p = [
        part("Plinth", (0, 1, 0), (32, 2, 24), fb.planks(WOOD_DARK, 6, vertical=False)),
        part("Body", (0, 11, 0), (30, 18, 22), fb.planks(WOOD, 5)),
        part("Panel", (0, 11, 11.25), (22, 12, 0.5), fb.planks(WOOD_DARK, 4)),
        part("Emblem", (0, 11.5, 11.75), (8, 8, 0.5), fb.glyph(GOLD, "eye", ("front",))),
        part("Top", (0, 21.5, 1), (32, 3, 26), fb.planks(WOOD_DARK, 6, vertical=False)),
        part("Edge", (0, 22.5, 14.25), (32, 1.5, 1), fb.metal(BRASS, False)),
        part("Scale_Base", (-9, 23.5, -3), (6, 1, 6), fb.metal(BRASS, False)),
        part("Scale_Post", (-9, 29, -3), (1.5, 10, 1.5), fb.metal(BRASS, False)),
        part("Scale_Beam", (-9, 34.5, -3), (15, 1, 1), fb.metal(GOLD, False)),
        part("Chain_L", (-15.5, 32, -3), (0.5, 4, 0.5), fb.solid(BRASS)),
        part("Chain_R", (-2.5, 32, -3), (0.5, 4, 0.5), fb.solid(BRASS)),
        part("Pan_L", (-15.5, 29.5, -3), (5, 1, 5), fb.metal(BRASS, False)),
        part("Pan_R", (-2.5, 29.5, -3), (5, 1, 5), fb.metal(BRASS, False)),
        part("Pan_Shards", (-15.5, 30.75, -3), (2.5, 1.5, 2.5), c, glow=True, rot=(0, 30, 0)),
        part("Book_Cover", (8, 23.5, 4), (14, 1, 10), fb.solid((120, 48, 42)), rot=(0, -14, 0)),
        part("Book_Pages", (8, 24.4, 4), (12.5, 1, 8.5), fb.paper(), rot=(0, -14, 0)),
        part("Jar", (10, 27, -7), (5, 6, 5), c, glow=True),
        part("Jar_Cork", (10, 31, -7), (3.5, 2, 3.5), fb.planks(WOOD, 2)),
    ]
    return p, None




# ---------------------------------------------------------------- reste de l'Observatoire

CORE_COLORS = {  # couleur de chaque fractale (noyaux du distributeur), dans l'ordre du catalogue
    "Cliffside": (186, 140, 255), "Uncategorized": (110, 210, 255), "Volcanic": (255, 140, 60),
    "SolidOcean": (90, 220, 160), "Swampland": (160, 230, 90), "Snowblind": (205, 235, 255),
    "SilentSurf": (40, 160, 175),
    "SirensReef": (74, 160, 96),
}
COPPER = (190, 112, 70)
SILVER = (200, 206, 218)
IRON = (86, 88, 98)
IRON_DARK = (58, 58, 66)
PAPER = (232, 220, 190)


def glow(color):
    """Cristal lumineux d'une couleur : face sombre à 55 %, reflet blanchi."""
    return fb.crystal(fb.shade(color, 0.55), fb.mix(color, (255, 255, 255), 0.6))


def bob(height=1.5, period=120, invert=False):
    h = -height if invert else height
    return [(0, (0, 0, 0)), (period // 2, (0, h, 0)), (period, (0, 0, 0))]


def spin_y(period=240, axis=1, sign=1):
    keys = []
    for k in range(5):
        r = [0, 0, 0]
        r[axis] = sign * 90 * k
        keys.append((period * k // 4, tuple(r)))
    return keys


def flicker(period=40):
    return [(0, (1, 1, 1)), (period // 4, (1.08, 1.12, 1.08)), (period // 2, (0.94, 1.04, 0.94)),
            (3 * period // 4, (1.05, 0.92, 1.05)), (period, (1, 1, 1))]


def core_distributor():
    """Présentoir de pierre à six alvéoles : un noyau de chaque fractale flotte au-dessus de sa coupelle."""
    p = [
        part("Base", (0, 3, 0), (30, 6, 30), fb.stone(STONE_DARK, (8, 6))),
        part("Band", (0, 6.5, 0), (26, 1, 26), fb.metal(BRASS, False)),
        part("Top", (0, 9, 2), (28, 4, 20), fb.smooth_stone(STONE)),
        part("Back", (0, 15, -11), (26, 12, 4), fb.stone(STONE, (7, 4))),
        inlay("Back_Rune", (0, 15.5, -8.75), (9, 9, 0.5), MIST, "ring", ("front",)),
        part("Back_Rim", (0, 21.5, -11), (28, 1.5, 5), fb.metal(GOLD, False)),
    ]
    tracks = {}
    for k, (fid, color) in enumerate(CORE_COLORS.items()):
        rows = (-2, 6) if len(CORE_COLORS) <= 6 else (-4, 2, 8)   # trois rangées dès la septième fractale
        x, z = (-8, 0, 8)[k % 3], rows[k // 3]
        p.append(part(f"Cup_{k + 1}", (x, 11.75, z), (5, 1.5, 5), fb.metal(BRASS, False)))
        p.append(part(f"Core_{k + 1}", (x, 16, z), (3.5, 3.5, 3.5), glow(color), glow=True, rot=(35, 45, 0)))
        tracks[f"Core_{k + 1}"] = {"position": bob(1.2, 120, invert=k % 2 == 1)}
    return p, fb.anim(120, tracks)


def level_distributor():
    """Râtelier de diapasons : un diapason par rang (cuivre, argent, or, cristal) accroché à un panneau de bois."""
    p = [
        part("Base", (0, 2, -4), (30, 4, 18), fb.stone(STONE_DARK, (8, 4))),
        part("Board", (0, 17, -10), (28, 26, 3), fb.planks(WOOD, 5)),
        part("Board_Top", (0, 31, -10), (30, 2, 5), fb.metal(BRASS)),
        part("Board_Foot", (0, 4.75, -9.5), (30, 1.5, 4), fb.metal(BRASS, False)),
    ]
    tracks = {}
    for k, (color, lit) in enumerate(((COPPER, False), (SILVER, False), (GOLD, False), (MIST, True))):
        x = (-9, -3, 3, 9)[k]
        paint = glow(color) if lit else fb.metal(color, False)
        name = f"Fork_{k + 1}"
        p.append(part(f"Peg_{k + 1}", (x, 26, -7.5), (1.5, 1.5, 2), fb.metal(BRASS, False)))
        p.append(part(name, (x, 11, -7.5), (1.5, 7, 1.5), paint, glow=lit, pivot=(x, 26, -7.5)))
        p.append(part(f"{name}_Bridge", (x, 15.25, -7.5), (5, 1.5, 1.5), paint, glow=lit, parent=name))
        p.append(part(f"{name}_Prong_L", (x - 1.75, 20, -7.5), (1.5, 8, 1.5), paint, glow=lit, parent=name))
        p.append(part(f"{name}_Prong_R", (x + 1.75, 20, -7.5), (1.5, 8, 1.5), paint, glow=lit, parent=name))
        sway = 2.5 if k % 2 else -2.5
        tracks[name] = {"orientation": [(0, (0, 0, 0)), (45, (0, 0, sway)), (90, (0, 0, 0)), (135, (0, 0, -sway)),
                                        (180, (0, 0, 0))]}
    return p, fb.anim(180, tracks)


def daily_board():
    """Panneau des fractales du jour : trois fiches épinglées sous un petit toit, cadre de laiton."""
    p = [
        part("Post_L", (-13, 15, 0), (3, 30, 3), fb.planks(WOOD_DARK, 3)),
        part("Post_R", (13, 15, 0), (3, 30, 3), fb.planks(WOOD_DARK, 3)),
        part("Board", (0, 19, 0), (24, 18, 2), fb.planks(WOOD, 4, vertical=False)),
        part("Frame_Top", (0, 28.75, 0), (26, 1.5, 3), fb.metal(BRASS, False)),
        part("Frame_Bottom", (0, 9.25, 0), (26, 1.5, 3), fb.metal(BRASS, False)),
        part("Roof", (0, 31, 0), (31, 2, 8), fb.planks(WOOD_DARK, 4, vertical=False)),
        part("Roof_Ridge", (0, 32.5, 0), (31, 1, 3), fb.planks(WOOD_DARK, 4, vertical=False)),
    ]
    for k, color in enumerate((CORE_COLORS["Cliffside"], GOLD, CORE_COLORS["Swampland"])):
        x = (-8, 0, 8)[k]
        p.append(part(f"Card_{k + 1}", (x, 18.5, 1.25), (6.5, 9, 0.5), fb.paper()))
        p.append(inlay(f"Card_Mark_{k + 1}", (x, 18, 1.75), (4, 4, 0.5), color, "ring", ("front",)))
        p.append(part(f"Pin_{k + 1}", (x, 22.5, 1.75), (1, 1, 1), fb.solid((200, 60, 50))))
    return p, None


def registry():
    """Lutrin de bois sur pied de pierre, grand registre ouvert sur le plateau incliné."""
    top_rot = (-22, 0, 0)
    top = (0, 23.5, 1)
    p = [
        part("Foot", (0, 1.5, 0), (18, 3, 16), fb.smooth_stone(STONE_DARK)),
        part("Column", (0, 11, 0), (8, 16, 8), fb.planks(WOOD, 3)),
        part("Collar", (0, 18.5, 0), (10, 1.5, 10), fb.metal(BRASS, False)),
        part("Head", (0, 20.5, 0), (14, 3, 12), fb.planks(WOOD_DARK, 4, vertical=False)),
        part("Desk", top, (22, 2, 16), fb.planks(WOOD_DARK, 4, vertical=False), rot=top_rot),
        part("Desk_Lip", fb.tilt(top, top_rot, (0, 1.5, 8)), (22, 2, 1.5), fb.metal(BRASS, False), rot=top_rot),
        part("Cover", fb.tilt(top, top_rot, (0, 1.5, -0.5)), (20, 1, 13), fb.solid((110, 46, 52)), rot=top_rot),
        part("Pages_L", fb.tilt(top, top_rot, (-4.6, 2.3, -0.5)), (9, 1, 11.5), fb.paper(), rot=top_rot),
        part("Pages_R", fb.tilt(top, top_rot, (4.6, 2.3, -0.5)), (9, 1, 11.5), fb.paper(), rot=top_rot),
        part("Ribbon", fb.tilt(top, top_rot, (1, 2.9, 4)), (1, 0.4, 7), fb.solid((170, 40, 50)), rot=top_rot),
    ]
    return p, None


def infusion_altar():
    """Autel bas de pierre, douze fioles d'infusion en cercle autour d'un cristal des Brumes."""
    p = [
        part("Base", (0, 3, 0), (30, 6, 30), fb.smooth_stone(STONE_DARK)),
        part("Body", (0, 10, 0), (24, 8, 24), fb.stone(STONE, (8, 4))),
        part("Top", (0, 15.5, 0), (28, 3, 28), fb.smooth_stone(STONE)),
        part("Rim", (0, 17.25, 0), (20, 0.5, 20), fb.metal(BRASS, False)),
        part("Crystal", (0, 22, 0), (5, 8, 5), glow(MIST), glow=True, rot=(0, 45, 0)),
        part("Crystal_Tip", (0, 27, 0), (3, 3, 3), glow(MIST), glow=True, rot=(0, 45, 0)),
    ]
    tiers = [fb.mix((110, 170, 255), (190, 120, 255), k / 7) for k in range(8)] + \
            [fb.mix((190, 120, 255), (255, 210, 110), k / 3) for k in range(1, 5)]
    for k in range(12):
        a = math.radians(30 * k + 15)
        x, z = round(10.5 * math.sin(a), 2), round(10.5 * math.cos(a), 2)
        p.append(part(f"Vial_{k + 1}", (x, 19, z), (2.5, 3.5, 2.5), glow(tiers[k]), glow=True))
        p.append(part(f"Cork_{k + 1}", (x, 21.25, z), (1.5, 1, 1.5), fb.solid((150, 110, 70))))
    return p, fb.anim(120, {"Crystal": {"position": bob()}, "Crystal_Tip": {"position": bob()}})


def mist_forge():
    """Creuset de fonte sur un foyer de pierre, Brume liquide violette qui bouillonne."""
    iron = fb.metal(IRON, False)
    p = [
        part("Hearth", (0, 6, 0), (30, 12, 30), fb.stone(STONE_DARK, (8, 4))),
        part("Mouth", (0, 5, 15.1), (12, 6, 0.5), fb.solid((24, 18, 30))),
        part("Embers", (0, 4, 15.3), (10, 3, 0.5), glow((255, 120, 200)), glow=True),
        part("Arch", (0, 8.75, 15.5), (14, 1.5, 1.5), fb.metal(BRASS, False)),
        part("Pot", (0, 17.5, 0), (22, 11, 22), iron),
        part("Rim_F", (0, 24, 10.5), (24, 2, 3), iron),
        part("Rim_B", (0, 24, -10.5), (24, 2, 3), iron),
        part("Rim_L", (-10.5, 24, 0), (3, 2, 18), iron),
        part("Rim_R", (10.5, 24, 0), (3, 2, 18), iron),
        part("Handle_L", (-13, 20, 0), (2, 4, 6), fb.metal(IRON_DARK, False)),
        part("Handle_R", (13, 20, 0), (2, 4, 6), fb.metal(IRON_DARK, False)),
        part("Liquid", (0, 23.25, 0), (18, 0.5, 18), fb.mist((120, 70, 210), (220, 190, 255)), glow=True),
        part("Bubble_1", (-4, 23.8, 3), (2, 1, 2), glow(MIST), glow=True),
        part("Bubble_2", (5, 23.8, -4), (1.5, 1, 1.5), glow(MIST), glow=True),
    ]
    a = fb.anim(80, {"Liquid": {"position": bob(0.4, 80)},
                     "Bubble_1": {"position": [(0, (0, 0, 0)), (40, (0, 1.2, 0)), (80, (0, 0, 0))]},
                     "Bubble_2": {"position": [(0, (0, 1.2, 0)), (40, (0, 0, 0)), (80, (0, 1.2, 0))]}})
    return p, a


def trial_panel():
    """Pupitre asura du golem d'essai : boîtier de métal, écran cyan incliné, leviers et voyants."""
    body = (80, 88, 130)
    screen_rot = (-28, 0, 0)
    top = (0, 19.5, 2)
    p = [
        part("Body", (0, 9, 0), (26, 18, 16), fb.metal(body)),
        part("Trim", (0, 18.25, 0), (27, 1.5, 17), fb.metal(BRASS, False)),
        part("Panel", top, (24, 2, 13), fb.metal((70, 76, 112), False), rot=screen_rot),
        part("Screen", fb.tilt(top, screen_rot, (-3, 1.2, 0)), (14, 0.5, 9), glow((90, 210, 255)), glow=True,
             rot=screen_rot),
        part("Button_1", fb.tilt(top, screen_rot, (8, 1.5, -3)), (3, 1, 3), glow((255, 90, 80)), glow=True,
             rot=screen_rot),
        part("Button_2", fb.tilt(top, screen_rot, (8, 1.5, 2)), (3, 1, 3), glow((120, 255, 120)), glow=True,
             rot=screen_rot),
        part("Lever_Base", (-8, 21, -5), (4, 2, 4), fb.metal(IRON_DARK, False)),
        part("Lever", (-8, 25, -4), (1.5, 7, 1.5), fb.metal(SILVER, False), rot=(18, 0, 0)),
        part("Lever_Knob", (-8, 28.5, -2.8), (3, 3, 3), fb.solid((200, 60, 50))),
        part("Antenna", (10, 25, -6), (1, 10, 1), fb.metal(SILVER, False)),
        part("Bulb", (10, 30.5, -6), (2.5, 2.5, 2.5), glow((255, 200, 90)), glow=True),
        part("Vent", (0, 8, 8.1), (16, 6, 0.5), fb.planks((52, 56, 84), 2, vertical=False, rim=False)),
    ]
    return p, fb.anim(60, {"Bulb": {"shapeStretch": [(0, (1, 1, 1)), (30, (1.3, 1.3, 1.3)), (60, (1, 1, 1))]}})


# ---------------------------------------------------------------- Falaise

CULT = (60, 44, 86)
CULT_GLOW = (196, 120, 255)
CLIFF_STONE = (112, 112, 122)


def hammer_rack():
    """Râtelier du culte : poteaux de bois noir, traverse runique, le marteau debout dans ses crochets."""
    black = fb.planks((46, 36, 44), 3)
    p = [
        part("Base", (0, 1.5, -3), (26, 3, 14), fb.stone((70, 64, 84), (7, 3))),
        part("Post_L", (-11, 15, -7), (3, 26, 3), black),
        part("Post_R", (11, 15, -7), (3, 26, 3), black),
        part("Beam", (0, 27, -7), (28, 3, 3), black),
        inlay("Beam_Rune", (0, 27, -5.25), (14, 2, 0.5), CULT_GLOW, "tick", ("front",)),
        part("Hook", (0, 21, -5), (8, 1.5, 3), fb.metal(IRON_DARK, False)),
        part("Handle", (0, 12, -3), (2, 20, 2), fb.planks((90, 60, 40), 2)),
        part("Grip", (0, 6, -3), (2.5, 6, 2.5), fb.cloth((110, 40, 60))),
        part("Head", (0, 24, -3), (11, 7, 7), fb.smooth_stone((40, 36, 48))),
        part("Head_Band_L", (-3.5, 24, -3), (1, 7.4, 7.4), fb.metal(IRON, False)),
        part("Head_Band_R", (3.5, 24, -3), (1, 7.4, 7.4), fb.metal(IRON, False)),
        inlay("Head_Rune", (0, 24, 0.75), (5, 5, 0.5), CULT_GLOW, "eye", ("front",)),
    ]
    return p, None


def gargoyle():
    """Gargouille de pierre accroupie sur son socle, gueule ouverte, ailes repliées, yeux luisants."""
    s = fb.smooth_stone(CLIFF_STONE)
    dark = fb.smooth_stone(fb.shade(CLIFF_STONE, 0.8))
    p = [
        part("Base", (0, 3, 0), (26, 6, 26), fb.stone(fb.shade(CLIFF_STONE, 0.85), (8, 6))),
        part("Body", (0, 13, -2), (14, 12, 14), s),
        part("Chest", (0, 15, 5), (12, 9, 6), s),
        part("Head", (0, 21, 6), (12, 9, 10), s),
        part("Snout", (0, 20, 12), (8, 4, 4), s),
        part("Jaw", (0, 15.5, 11), (8, 2.5, 6), dark, rot=(18, 0, 0)),
        part("Mouth", (0, 17.5, 13.6), (6, 2, 0.5), fb.solid((30, 26, 34))),
        part("Eye_L", (-3, 23, 11.1), (2, 1.5, 0.5), glow((255, 210, 120)), glow=True),
        part("Eye_R", (3, 23, 11.1), (2, 1.5, 0.5), glow((255, 210, 120)), glow=True),
        part("Horn_L", (-4, 27, 4), (2, 5, 2), dark, rot=(-25, 0, -10)),
        part("Horn_R", (4, 27, 4), (2, 5, 2), dark, rot=(-25, 0, 10)),
        part("Wing_L", (-9, 16, -3), (3, 15, 13), dark, rot=(0, 0, 12)),
        part("Wing_R", (9, 16, -3), (3, 15, 13), dark, rot=(0, 0, -12)),
        part("Claw_L", (-5, 7.5, 8), (4, 3, 5), dark),
        part("Claw_R", (5, 7.5, 8), (4, 3, 5), dark),
        part("Tail", (0, 7.5, -11), (3, 3, 6), dark, rot=(0, 20, 0)),
    ]
    return p, None


def lever(pulled=False):
    """Levier massif : deux joues de pierre, axe de fer, long bras incliné à pommeau de laiton. Tiré : bras rabattu
    de l'autre côté, pommeau de fer terni (le piège est coupé, on le voit de loin)."""
    arm_rot = (-60, 0, 0) if pulled else (30, 0, 0)
    axle = (0, 9, 0)
    p = [
        part("Plinth", (0, 1.5, 0), (20, 3, 18), fb.stone(fb.shade(CLIFF_STONE, 0.9), (6, 3))),
        part("Cheek_L", (-5.5, 7, 0), (4, 8, 10), fb.smooth_stone(CLIFF_STONE)),
        part("Cheek_R", (5.5, 7, 0), (4, 8, 10), fb.smooth_stone(CLIFF_STONE)),
        part("Axle", axle, (14, 2, 2), fb.metal(IRON_DARK, False)),
        part("Arm", fb.tilt(axle, arm_rot, (0, 9, 0)), (2.5, 18, 2.5), fb.metal(IRON, False), rot=arm_rot),
        part("Knob", fb.tilt(axle, arm_rot, (0, 19, 0)), (5, 5, 5), fb.metal(IRON_DARK if pulled else GOLD, not pulled),
             rot=arm_rot),
    ]
    return p, None


def cage_door():
    """Grille de cage en fer forgé (le long de X ; tournée d'un quart de tour sur une ligne en Z), cadenas."""
    iron = fb.metal(IRON_DARK, False)
    p = [
        part("Bottom", (0, 1.5, 0), (32, 3, 5), iron),
        part("Top", (0, 30.5, 0), (32, 3, 5), iron),
        part("Middle", (0, 16, 0), (32, 2, 3), iron),
    ]
    for k, x in enumerate((-12, -6, 0, 6, 12)):
        p.append(part(f"Bar_{k + 1}", (x, 16, 0), (2, 26, 2), fb.metal(IRON, False)))
    p.append(part("Lock", (9, 13, 2), (4, 5, 2), fb.metal(BRASS)))
    return p, None


# ---------------------------------------------------------------- Inclassable (asura)

ASURA = (84, 92, 140)
ASURA_GLOW = (110, 220, 255)


def console():
    """Console asura : socle de métal, pupitre incliné, gros bouton cyan et petit écran."""
    top_rot = (-30, 0, 0)
    top = (0, 17, 1)
    p = [
        part("Foot", (0, 1.5, 0), (22, 3, 18), fb.metal(fb.shade(ASURA, 0.8), False)),
        part("Body", (0, 9, 0), (16, 12, 12), fb.metal(ASURA)),
        part("Desk", top, (22, 3, 16), fb.metal(fb.shade(ASURA, 1.1)), rot=top_rot),
        part("Button", fb.tilt(top, top_rot, (-4, 2, 1)), (6, 2, 6), glow(ASURA_GLOW), glow=True, rot=top_rot),
        part("Screen", fb.tilt(top, top_rot, (6, 1.75, 0)), (7, 0.5, 9), glow((120, 255, 200)), glow=True,
             rot=top_rot),
        part("Trim", (0, 15.25, 0), (17, 1.5, 13), fb.metal(BRASS, False)),
        part("Cable", (0, 4, -7), (3, 3, 4), fb.solid((40, 40, 50))),
    ]
    return p, fb.anim(60, {"Button": {"shapeStretch": [(0, (1, 1, 1)), (30, (1.1, 1.6, 1.1)), (60, (1, 1, 1))]}})


def holo(color, alpha=105):
    """Panneau holographique asura : verre cyan très clair, cadre lumineux, alvéoles et lignes de données."""
    def paint(rng, w, h, face):
        img = fb.glass(color, alpha)(rng, w, h, face)
        px = img.load()
        light = fb.mix(color, (255, 255, 255), 0.55)
        for y in range(h):
            for x in range(w):
                hexa = (x // 3 + (y // 4) % 2) % 3 == 0 and y % 4 == 0
                data = y % 5 == 2 and rng.random() < 0.55 and 2 < x < w - 3
                if hexa or data:
                    px[x, y] = light + (min(255, alpha + 90),)
        return img
    return paint


def asura_hologram():
    """Console asura de l'Observatoire de GW2 : gros socle de bronze sombre aux arêtes vives, pupitre incliné aux
    touches cyan, projecteur et trois panneaux holographiques qui flottent au-dessus en se balançant."""
    bronze = fb.metal((92, 70, 52))
    dark = fb.metal((54, 46, 44), False)
    top_rot = (-28, 0, 0)
    top = (0, 19, 4)
    cyan = (110, 220, 255)
    p = [
        part("Foot", (0, 2, 0), (30, 4, 26), dark),
        part("Body", (0, 11, -3), (24, 14, 18), bronze),
        part("Body_Trim", (0, 17.5, -3), (25, 1.5, 19), fb.metal(BRASS, False)),
        part("Desk", top, (28, 3, 14), bronze, rot=top_rot),
        part("Keys", fb.tilt(top, top_rot, (-5, 1.75, 0)), (12, 0.5, 8), glow(cyan), glow=True, rot=top_rot),
        part("Dial", fb.tilt(top, top_rot, (8, 2, 0)), (6, 1, 6), glow((120, 255, 200)), glow=True, rot=top_rot),
        part("Side_Light_L", (-12.25, 11, -3), (0.5, 8, 3), glow(cyan), glow=True),
        part("Side_Light_R", (12.25, 11, -3), (0.5, 8, 3), glow(cyan), glow=True),
        part("Mast", (0, 25, -9), (4, 12, 4), dark),
        part("Projector", (0, 32, -9), (8, 3, 8), fb.metal(BRASS)),
        part("Lens", (0, 34, -9), (4, 1.5, 4), glow(cyan), glow=True),
        part("Holo_Main", (0, 48, -9), (30, 20, 0.5), holo(cyan), glow=True, pivot=(0, 48, -9)),
        part("Holo_Left", (-17, 58, -6), (12, 14, 0.5), holo(cyan), glow=True, rot=(0, 25, 0)),
        part("Holo_Right", (17, 56, -6), (12, 16, 0.5), holo((150, 230, 255)), glow=True, rot=(0, -25, 0)),
        part("Holo_Top", (0, 66, -8), (14, 8, 0.5), holo(cyan, 90), glow=True, pivot=(0, 66, -8)),
    ]
    a = fb.anim(160, {
        "Holo_Main": {"position": [(0, (0, 0, 0)), (80, (0, 1.2, 0)), (160, (0, 0, 0))]},
        "Holo_Left": {"position": [(0, (0, 1, 0)), (80, (0, -0.5, 0)), (160, (0, 1, 0))]},
        "Holo_Right": {"position": [(0, (0, -0.5, 0)), (80, (0, 1, 0)), (160, (0, -0.5, 0))]},
        "Holo_Top": {"position": [(0, (0, 0, 0)), (40, (0, 1.5, 0)), (120, (0, -0.5, 0)), (160, (0, 0, 0))]},
    })
    return p, a


def light_spring():
    """Source d'une cascade de lumière, au fond d'un bassin : anneau de laiton, cristal bleu qui tourne lentement
    (la cascade elle-même est la particule Nakasar_Fractal_Light_Fall)."""
    c = glow((140, 210, 255))
    p = [
        part("Ring", (0, 1.5, 0), (26, 3, 26), fb.metal(GOLD, False)),
        part("Plate", (0, 2.5, 0), (20, 1, 20), fb.smooth_stone((70, 110, 150))),
        part("Crystal", (0, 9, 0), (7, 11, 7), c, glow=True, rot=(0, 45, 0)),
        part("Crystal_Tip", (0, 16, 0), (4, 4, 4), c, glow=True, rot=(0, 45, 0)),
    ]
    rise = bob(1.5, 160)
    return p, fb.anim(160, {"Crystal": {"position": rise}, "Crystal_Tip": {"position": rise}})


def fan():
    """Ventilateur mural : cadre carré, grille, hélice à quatre pales qui tourne."""
    frame = fb.metal(fb.shade(ASURA, 0.85))
    p = [
        part("Frame_Top", (0, 30, 0), (32, 4, 8), frame),
        part("Frame_Bottom", (0, 2, 0), (32, 4, 8), frame),
        part("Frame_L", (-14, 16, 0), (4, 24, 8), frame),
        part("Frame_R", (14, 16, 0), (4, 24, 8), frame),
        part("Grille", (0, 16, -2), (24, 24, 1), fb.planks((30, 32, 40), 3, rim=False)),
        part("Rotor", (0, 16, 1.5), (6, 6, 3), fb.metal(BRASS), pivot=(0, 16, 1.5)),
    ]
    for k in range(4):
        a = 90 * k + 15
        cx, cy = 6.5 * math.cos(math.radians(a)), 6.5 * math.sin(math.radians(a))
        p.append(part(f"Blade_{k + 1}", (round(cx, 2), round(16 + cy, 2), 1.5), (8, 4, 1),
                      fb.metal(SILVER, False), rot=(0, 0, a), parent="Rotor"))
    return p, fb.anim(60, {"Rotor": {"orientation": spin_y(60, axis=2)}})


def battery(charged):
    """Batterie asura : socle et chapeau de métal, corps de verre (vide, ou liquide cyan), bobines de cuivre."""
    m = fb.metal(fb.shade(ASURA, 0.9))
    p = [
        part("Base", (0, 2, 0), (20, 4, 20), m),
        part("Cap", (0, 27, 0), (20, 4, 20), m),
        part("Coil_1", (0, 9, 0), (17, 1.5, 17), fb.metal(COPPER, False)),
        part("Coil_2", (0, 20, 0), (17, 1.5, 17), fb.metal(COPPER, False)),
        part("Terminal_L", (-5, 30.5, 0), (3, 3, 3), fb.metal(BRASS, False)),
        part("Terminal_R", (5, 30.5, 0), (3, 3, 3), fb.metal(BRASS, False)),
    ]
    if charged:
        p += [part("Core", (0, 14.5, 0), (12, 21, 12), fb.mist((60, 170, 230), (210, 250, 255)), glow=True),
              part("Core_X", (0, 14.5, 0), (16, 20, 8), fb.mist((60, 170, 230), (210, 250, 255)), glow=True)]
        return p, fb.anim(60, {"Core": {"shapeStretch": [(0, (1, 1, 1)), (30, (1.04, 1, 1.04)), (60, (1, 1, 1))]}})
    p += [part("Core", (0, 14.5, 0), (12, 21, 12), fb.solid((34, 40, 56))),
          part("Core_X", (0, 14.5, 0), (16, 20, 8), fb.solid((40, 48, 66)))]
    return p, None


def charge_pylon():
    """Pylône de charge : colonne de métal à bobines de cuivre, sphère violette qui tourne au sommet."""
    p = [
        part("Base", (0, 3, 0), (22, 6, 22), fb.stone((70, 66, 96), (7, 6))),
        part("Column", (0, 20, 0), (8, 28, 8), fb.metal(ASURA)),
    ]
    for k, y in enumerate((11, 17, 23, 29)):
        p.append(part(f"Coil_{k + 1}", (0, y, 0), (12, 2, 12), fb.metal(COPPER, False)))
    p += [
        part("Cradle", (0, 35, 0), (12, 2, 12), fb.metal(BRASS, False)),
        part("Sphere", (0, 41, 0), (10, 8, 10), glow((200, 160, 255)), glow=True, pivot=(0, 41, 0)),
        part("Sphere_X", (0, 41, 0), (8, 10, 8), glow((200, 160, 255)), glow=True, parent="Sphere"),
    ]
    return p, fb.anim(160, {"Sphere": {"orientation": spin_y(160)}})


# ---------------------------------------------------------------- Marais (pièges sur un bloc de sol plein)

MUD = (84, 66, 48)
MOSS = (86, 112, 58)
SWAMP_GLOW = (150, 255, 210)


def swamp_ground():
    return part("Ground", (0, 16, 0), (32, 32, 32), fb.ground(MUD, MOSS, fb.shade(MOSS, 0.9)))


def tripwire():
    """Fil tendu entre deux piquets, sur un bloc de sol (on marche dessus)."""
    stake = fb.planks((96, 70, 44), 2)
    p = [swamp_ground(),
         part("Stake_L", (-13, 36, 0), (2, 8, 2), stake),
         part("Stake_R", (13, 36, 0), (2, 8, 2), stake),
         part("Wire", (0, 36.5, 0), (26, 0.5, 0.5), fb.solid((200, 196, 180))),
         part("Bell", (4, 35, 0), (1.5, 2, 1.5), fb.metal(BRASS, False))]
    return p, None


def bear_trap():
    """Piège à loup ouvert sur un bloc de sol : plaque, deux mâchoires dentées relevées, chaîne."""
    iron = fb.metal(IRON, False)
    p = [swamp_ground(),
         part("Plate", (0, 32.5, 0), (14, 1, 10), fb.metal(IRON_DARK, False)),
         part("Pan", (0, 33.25, 0), (5, 0.5, 5), fb.metal(fb.shade(IRON, 1.2), False)),
         part("Jaw_F", (0, 34.2, 5.2), (16, 4, 1.5), iron, rot=(55, 0, 0)),
         part("Jaw_B", (0, 34.2, -5.2), (16, 4, 1.5), iron, rot=(-55, 0, 0)),
         part("Spring_L", (-8, 33, 0), (3, 2, 8), fb.metal(IRON_DARK, False)),
         part("Spring_R", (8, 33, 0), (3, 2, 8), fb.metal(IRON_DARK, False)),
         part("Chain", (12, 32.4, 6), (1.5, 0.8, 8), fb.metal(IRON_DARK, False), rot=(0, 30, 0))]
    for k, x in enumerate((-6, -2, 2, 6)):
        p.append(part(f"Tooth_F_{k + 1}", (x, 36, 6.4), (1.2, 2, 1.2), fb.metal(SILVER, False), rot=(55, 0, 0)))
        p.append(part(f"Tooth_B_{k + 1}", (x, 36, -6.4), (1.2, 2, 1.2), fb.metal(SILVER, False), rot=(-55, 0, 0)))
    return p, None


def spider_eggs():
    """Grappe d'œufs blanchâtres dans la toile, sur un bloc de sol moussu ; ils palpitent."""
    egg = fb.smooth_stone((226, 222, 196), rim=False)
    p = [swamp_ground(),
         part("Web", (0, 32.25, 0), (26, 0.5, 26), fb.glyph((230, 230, 230), "ring", ("top",))),
         part("Egg_1", (0, 35, 0), (7, 6, 7), egg),
         part("Egg_2", (-6, 34, 4), (5, 4, 5), egg),
         part("Egg_3", (6, 34, -3), (5, 4.5, 5), egg),
         part("Egg_4", (4, 33.5, 7), (4, 3, 4), egg),
         part("Egg_5", (-5, 33.5, -6), (4, 3, 4), egg)]
    pulse = [(0, (1, 1, 1)), (45, (1.08, 1.1, 1.08)), (90, (1, 1, 1))]
    return p, fb.anim(90, {"Egg_1": {"shapeStretch": pulse}, "Egg_3": {"shapeStretch": pulse}})


def spike_plate():
    """Plaque de fer percée sur un bloc de sol : les pointes affleurent."""
    p = [swamp_ground(),
         part("Plate", (0, 32.5, 0), (28, 1, 28), fb.metal(fb.shade(IRON, 0.9), False))]
    for i in range(3):
        for j in range(3):
            x, z = (i - 1) * 8, (j - 1) * 8
            p.append(part(f"Hole_{i}{j}", (x, 33.05, z), (4, 0.2, 4), fb.solid((26, 22, 22))))
            p.append(part(f"Spike_{i}{j}", (x, 34, z), (1.5, 2, 1.5), fb.metal(SILVER, False), rot=(0, 45, 0)))
    return p, None


def invigorator_rack():
    """Râtelier de bois : fusil revigorant à canon évasé posé en travers, fiole dorée au pied."""
    wood = fb.planks((100, 74, 50), 3)
    p = [
        part("Base", (0, 1.5, -2), (26, 3, 12), fb.planks((80, 58, 40), 4, vertical=False)),
        part("Post_L", (-11, 13, -4), (3, 22, 3), wood),
        part("Post_R", (11, 13, -4), (3, 22, 3), wood),
        part("Bar_Low", (0, 13, -4), (25, 2, 3), wood),
        part("Bar_High", (0, 22, -4), (25, 2, 3), wood),
        part("Barrel", (2, 24, -1.5), (20, 2.5, 2.5), fb.metal(IRON, False)),
        part("Muzzle", (13, 24, -1.5), (4, 4.5, 4.5), fb.metal(BRASS)),
        part("Stock", (-10, 23.5, -1.5), (8, 4.5, 3), fb.planks((120, 70, 40), 2)),
        part("Tank", (0, 21.5, -1.5), (5, 4, 4), glow((255, 210, 120)), glow=True),
        part("Vial", (8, 6, 1), (3, 6, 3), glow((255, 210, 120)), glow=True),
        part("Vial_Cork", (8, 9.5, 1), (2, 1, 2), fb.solid((150, 110, 70))),
    ]
    return p, None


def wisp_light():
    """Feu-follet posé sur une pierre moussue : flamme verte translucide qui flotte."""
    p = [
        part("Stone", (0, 3, 0), (18, 6, 16), fb.ground((96, 98, 90), MOSS)),
        part("Flame", (0, 15, 0), (7, 11, 7), glow(SWAMP_GLOW), glow=True, rot=(0, 45, 0)),
        part("Flame_Core", (0, 14, 0), (3.5, 6, 3.5), glow((240, 255, 250)), glow=True, rot=(0, 45, 0)),
        part("Flame_Tip", (0, 22, 0), (3, 4, 3), glow(SWAMP_GLOW), glow=True, rot=(0, 45, 0)),
    ]
    return p, fb.anim(90, {"Flame": {"position": bob(1.5, 90)}, "Flame_Core": {"position": bob(1.5, 90)},
                           "Flame_Tip": {"position": bob(2, 90)}})


def wisp_cleft(lit):
    """Rocher moussu fendu en deux ; illuminé, un feu-follet brille dans la fente."""
    rock = fb.ground((92, 94, 88), MOSS)
    p = [
        part("Base", (0, 2, 0), (30, 4, 26), fb.smooth_stone((80, 82, 76))),
        part("Half_L", (-8, 16, 0), (13, 26, 22), rock, rot=(0, 0, 6)),
        part("Half_R", (8, 16, 0), (13, 26, 22), rock, rot=(0, 0, -6)),
        part("Cleft", (0, 14, 0), (4, 20, 18), fb.solid((20, 26, 22) if not lit else (60, 110, 90))),
    ]
    if not lit:
        return p, None
    p += [part("Wisp", (0, 18, 6), (5, 8, 5), glow(SWAMP_GLOW), glow=True, rot=(0, 45, 0)),
          part("Wisp_Core", (0, 17, 6), (2.5, 4, 2.5), glow((240, 255, 250)), glow=True, rot=(0, 45, 0))]
    return p, fb.anim(90, {"Wisp": {"position": bob(1.5, 90)}, "Wisp_Core": {"position": bob(1.5, 90)}})


# ---------------------------------------------------------------- Tempête de neige

SNOW = (232, 240, 248)
BARK = (84, 60, 44)
CHAR = (40, 32, 30)
FIRE = (255, 150, 50)


def fire(core=False):
    """Flamme : orange vif vers jaune pâle (le peintre cristal assombrit trop la couleur de base)."""
    return fb.crystal((250, 120, 30), (255, 236, 150)) if not core else fb.crystal((255, 190, 70), (255, 250, 210))


def bonfire(lit):
    """Grand feu de camp : cercle de pierres, rondins en tipi ; allumé, trois flammes qui dansent."""
    bark = fb.log(BARK if lit else CHAR, (190, 150, 100) if lit else (70, 60, 56))
    p = [part("Embers", (0, 1, 0), (16, 2, 16), glow((255, 110, 40)) if lit else fb.smooth_stone((60, 56, 56)),
              glow=lit)]
    for k in range(8):
        a = math.radians(45 * k + 10)
        p.append(part(f"Stone_{k + 1}", (round(13 * math.sin(a), 2), 2, round(13 * math.cos(a), 2)), (6, 4, 6),
                      fb.ground((110, 110, 116), SNOW), rot=(0, 45 * k + 10, 0)))
    p += [part("Log_X", (0, 3.5, 0), (4, 4, 24), bark, rot=(0, 90, 0)),
          part("Log_Z", (0, 6, 0), (4, 4, 24), bark)]
    for k, (rx, rz, x, z) in enumerate(((28, 0, 0, -8), (-28, 0, 0, 8), (0, 28, 8, 0), (0, -28, -8, 0))):
        p.append(part(f"Pole_{k + 1}", (x, 10, z), (3, 16, 3), bark, rot=(rx, 0, rz)))
    if not lit:
        return p, None
    p += [part("Flame01", (0, 12, 0), (10, 14, 10), fire(), glow=True, rot=(0, 45, 0)),
          part("Flame02", (0, 21, 0), (6, 9, 6), fire(), glow=True, rot=(0, 20, 0)),
          part("Flame03", (0, 27, 0), (3, 5, 3), fire(True), glow=True, rot=(0, 60, 0)),
          part("Flame_Core", (0, 10, 0), (6, 8, 6), fire(True), glow=True, rot=(0, 10, 0))]
    return p, fb.anim(40, {"Flame01": {"shapeStretch": flicker(40)}, "Flame02": {"shapeStretch": flicker(30)},
                           "Flame03": {"position": bob(1.5, 40)}})


def frost_brazier(lit):
    """Brasero de fer sur trois pieds, coupe pleine de bûches ; éteint, son bord est givré."""
    iron = fb.metal(IRON, False)
    p = [part("Leg_1", (0, 8, 6), (2, 17, 2), iron, rot=(-12, 0, 0)),
         part("Leg_2", (5.2, 8, -3), (2, 17, 2), iron, rot=(6, 0, 10)),
         part("Leg_3", (-5.2, 8, -3), (2, 17, 2), iron, rot=(6, 0, -10)),
         part("Bowl", (0, 19, 0), (18, 5, 18), fb.metal(IRON_DARK)),
         part("Rim", (0, 22, 0), (21, 1.5, 21), fb.metal(SNOW if not lit else IRON, False)),
         part("Log_1", (0, 23.5, 0), (3.5, 3.5, 15), fb.log(BARK if lit else CHAR)),
         part("Log_2", (0, 24.5, 0), (3.5, 3.5, 15), fb.log(BARK if lit else CHAR), rot=(0, 90, 0))]
    if not lit:
        p.append(part("Frost", (2, 26.6, -1), (6, 0.5, 5), fb.smooth_stone(SNOW, rim=False)))
        return p, None
    p += [part("Flame01", (0, 29, 0), (8, 10, 8), fire(), glow=True, rot=(0, 45, 0)),
          part("Flame02", (0, 35, 0), (4, 5, 4), fire(True), glow=True, rot=(0, 20, 0))]
    return p, fb.anim(40, {"Flame01": {"shapeStretch": flicker(40)}, "Flame02": {"position": bob(1.2, 40)}})


def firewood_pile():
    """Pile de bûches liées de cordes, chapeau de neige."""
    p = []
    k = 0
    for row, (n, y) in enumerate(((4, 3), (3, 9), (2, 15))):
        for i in range(n):
            x = (i - (n - 1) / 2) * 6.5
            k += 1
            p.append(part(f"Log_{k}", (x, y, 0), (6, 6, 26 - 2 * row), fb.log(BARK)))
    p += [part("Rope_L", (-6, 9, 0), (1, 15, 27), fb.solid((170, 140, 96))),
          part("Rope_R", (6, 9, 0), (1, 15, 27), fb.solid((170, 140, 96))),
          part("Snow", (0, 18.75, 0), (12, 1.5, 20), fb.smooth_stone(SNOW, rim=False))]
    return p, None


def torch_rack():
    """Râtelier de bois : trois torches debout, flammes vives."""
    wood = fb.planks((96, 70, 46), 3)
    p = [part("Base", (0, 1.5, -2), (26, 3, 12), wood),
         part("Back", (0, 10, -6), (26, 14, 3), wood),
         part("Holder", (0, 9, -2), (24, 2, 6), fb.metal(IRON_DARK, False))]
    tracks = {}
    for k, x in enumerate((-8, 0, 8)):
        p += [part(f"Handle_{k + 1}", (x, 12, -2), (2.5, 16, 2.5), fb.planks((120, 84, 50), 2)),
              part(f"Wrap_{k + 1}", (x, 21, -2), (4, 4, 4), fb.cloth((150, 120, 80))),
              part(f"Flame_{k + 1}", (x, 25.5, -2), (3, 5, 3), fire(), glow=True, rot=(0, 45, 0))]
        tracks[f"Flame_{k + 1}"] = {"shapeStretch": flicker(30 + 6 * k)}
    return p, fb.anim(48, tracks)


# ---------------------------------------------------------------- cubes repeints (plates-formes et sols)

CUBES = {
    # tex -> (peintre des côtés, peintre du dessus, rune du dessus (couleur, forme) ou None, alpha)
    "Harmony_Tile": (fb.stone((72, 84, 124), (8, 8)), fb.smooth_stone((88, 104, 150)), ((120, 200, 255), "ring"), 255),
    "Astrolabe_Ring": (fb.metal(BRASS), fb.metal(GOLD), ((90, 60, 30), "tick"), 255),
    "Landing": (fb.stone((96, 104, 128), (8, 6)), fb.smooth_stone((128, 136, 160)), ((170, 210, 255), "ring"), 255),
    "Pressure_Plate": (fb.stone((96, 90, 84), (8, 8)), fb.stone((110, 104, 96), (8, 8), mortar=0.7), None, 255),
    "Seal_Stone": (fb.stone((58, 44, 80), (8, 6)), fb.smooth_stone((70, 54, 96)), ((196, 120, 255), "eye"), 255),
    "Mist_Barrier": (fb.mist((70, 46, 130), (210, 180, 255)), fb.mist((70, 46, 130), (210, 180, 255)), None, 255),
    "Glimmer": (fb.glass((255, 226, 120), 150), fb.glass((255, 236, 150), 150), None, 150),
    "Gate_Veil": (fb.mist((96, 40, 160), (240, 214, 255), 175), fb.mist((96, 40, 160), (240, 214, 255), 175), None, 175),
}


# ---------------------------------------------------------------- registre

def fires(scale, y, node=None):
    entry = {"SystemId": "Campfire_New_Cartoon", "Scale": scale, "PositionOffset": {"Y": y}}
    if node:
        entry["TargetNodeName"] = node
    return [entry]


FIRE_SOUND = {"AmbientSoundEventId": "SFX_Campfire_Default_Loop", "Looping": True}
VOID_MOTES = "Dungeon_Goblin_Void_Motes_Cluster"


def motes(y, system=VOID_MOTES, scale=1):
    return [{"SystemId": system, "Scale": scale, "PositionOffset": {"Y": y}}]


# tex -> (fabrique, réglages) ; orient : "open" (face vers le côté le plus dégagé), "wall" (dos au bloc plein voisin),
# "line" (le long de la ligne de blocs identiques), absent : modèle symétrique.
BLOCKS = {
    "Selection_Console": (selection_console, {"particles": motes(0.8), "orient": "open"}),
    "Resonator": (resonator, {"particles": motes(1.0, "Dust_Sparkles_Fine")}),
    "Reward_Chest": (reward_chest, {"particles": motes(0.6, "Block_Treasure_Sparks"), "orient": "open"}),
    "Exit_Stone": (exit_stone, {"particles": motes(0.7), "orient": "open"}),
    "Archivist_Counter": (archivist_counter, {"orient": "open"}),
    "Mists_Portal": (mists_portal, {"particles": [
        {"SystemId": VOID_MOTES, "Scale": 1.6, "PositionOffset": {"X": 0, "Y": 2.0, "Z": 0}},
        {"SystemId": "Dust_Sparkles_Fine", "Scale": 1.4, "PositionOffset": {"X": 0, "Y": 1.2, "Z": 0}},
    ], "extra": {"AmbientSoundEventId": "SFX_Goblin_World_Breach_Portal"}}),
    "Core_Distributor": (core_distributor, {"particles": motes(0.6, "Dust_Sparkles_Fine"), "orient": "open"}),
    "Level_Distributor": (level_distributor, {"orient": "open"}),
    "Daily_Board": (daily_board, {"orient": "open"}),
    "Registry": (registry, {"orient": "open"}),
    "Infusion_Altar": (infusion_altar, {"particles": motes(0.8, "Dust_Sparkles_Fine")}),
    "Mist_Forge": (mist_forge, {"particles": motes(0.8), "orient": "open"}),
    "Trial_Panel": (trial_panel, {"orient": "open"}),
    "Hammer_Rack": (hammer_rack, {"particles": motes(0.8), "orient": "wall"}),
    "Gargoyle": (gargoyle, {"orient": "wall"}),
    "Lever": (lever, {"orient": "open", "particles": motes(1.0, "Dust_Sparkles_Fine")}),
    "Lever_Pulled": (lambda: lever(True), {"orient": "open"}),
    "Cage_Door": (cage_door, {"orient": "line"}),
    "Console": (console, {"orient": "open"}),
    "Fan": (fan, {"orient": "open"}),
    "Battery": (lambda: battery(False), {}),
    "Battery_Charged": (lambda: battery(True), {"particles": motes(0.9, "Dust_Sparkles_Fine")}),
    "Charge_Pylon": (charge_pylon, {"particles": motes(1.3, "Dust_Sparkles_Fine")}),
    "Tripwire": (tripwire, {"orient": "line"}),
    "Bear_Trap": (bear_trap, {}),
    "Spider_Eggs": (spider_eggs, {}),
    "Spike_Plate": (spike_plate, {}),
    "Invigorator_Rack": (invigorator_rack, {"orient": "open"}),
    "Wisp_Light": (wisp_light, {"particles": motes(0.5, "Torch_Fire_Green", 0.6)}),
    "Wisp_Cleft": (lambda: wisp_cleft(False), {"orient": "open"}),
    "Wisp_Cleft_Lit": (lambda: wisp_cleft(True), {"particles": motes(0.55, "Torch_Fire_Green", 0.5), "orient": "open"}),
    "Bonfire": (lambda: bonfire(True), {"particles": fires(1.4, 0.35), "extra": FIRE_SOUND}),
    "Bonfire_Out": (lambda: bonfire(False), {"particles": motes(0.5, "Smoke_Black")}),
    "Frost_Brazier": (lambda: frost_brazier(True), {"particles": fires(0.7, 0.85), "extra": FIRE_SOUND}),
    "Frost_Brazier_Out": (lambda: frost_brazier(False), {}),
    "Firewood_Pile": (firewood_pile, {"orient": "open"}),
    "Asura_Console": (asura_hologram, {"particles": motes(1.4, "Dust_Sparkles_Fine"), "orient": "open"}),
    "Light_Spring": (light_spring, {"particles": [{"SystemId": "Nakasar_Fractal_Light_Fall", "PositionOffset": {"Y": 0.5}}]}),
    "Torch_Rack": (torch_rack, {"orient": "wall", "particles": [
        {"SystemId": "Torch_Fire", "Scale": 0.45, "TargetNodeName": f"Flame_{k}"} for k in (1, 2, 3)]}),
}
# Les pièges du marais sont posés sur un cube de sol plein (hitbox Full) : le joueur marche dessus, à y + 1.

ORIENT = {f"Nakasar_Fractal_{tex}": cfg["orient"] for tex, (_, cfg) in BLOCKS.items() if cfg.get("orient")}


def build(tex):
    """Écrit modèle, atlas, animation et icône de `tex` ; rend (aperçu 384 px, clés du BlockType)."""
    make, cfg = BLOCKS[tex]
    parts, animation = make()
    model_dir = COMMON / MODELS
    preview = fb.write_block_model(tex, parts, model_dir, COMMON / ICONS, zlib.crc32(tex.encode()))
    keys = {
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": f"{MODELS}/{tex}.blockymodel",
        "CustomModelTexture": [{"Texture": f"{MODELS}/{tex}_Texture.png", "Weight": 1}],
        "VariantRotation": "NESW",
    }
    anim_path = model_dir / f"{tex}.blockyanim"
    if animation:
        anim_path.write_text(json.dumps(animation, indent=2) + "\n")
        keys["CustomModelAnimation"] = f"{MODELS}/{tex}.blockyanim"
    elif anim_path.exists():
        anim_path.unlink()
    if cfg.get("particles"):
        keys["Particles"] = cfg["particles"]
    keys.update(cfg.get("extra", {}))
    return preview, keys


def build_cube(tex):
    """Repeint un bloc cube (côtés + dessus avec rune) ; rend (aperçu, textures du BlockType)."""
    side, top, rune, alpha = CUBES[tex]
    rng = random.Random(zlib.crc32(tex.encode()))
    tex_dir = COMMON / CUBE_TEXTURES
    side_img = side(rng, 32, 32, "front")
    top_img = top(rng, 32, 32, "top")
    if rune:
        mark = fb.glyph(rune[0], rune[1], ("top",))(rng, 20, 20, "top")
        top_img.alpha_composite(mark, (6, 6))
    tex_dir.mkdir(parents=True, exist_ok=True)
    side_img.save(tex_dir / f"{tex}.png")
    top_img.save(tex_dir / f"{tex}_Top.png")
    cube = [part("Cube", (0, 16, 0), (32, 32, 32),
                 lambda r, w, h, f: (top_img if f in ("top", "bottom") else side_img).copy())]
    atlas, uv = fb.build_atlas(cube, 0)
    big = fb.render(cube, atlas, uv, 256)
    big.resize((64, 64), Image.LANCZOS).save(COMMON / ICONS / f"{tex}.png")
    textures = [{"Sides": f"{CUBE_TEXTURES}/{tex}.png", "UpDown": f"{CUBE_TEXTURES}/{tex}_Top.png", "Weight": 1}]
    return fb.render(cube, atlas, uv, 384, bg=(36, 38, 52, 255)), textures


def apply(doc, tex):
    """Remplace le cube de l'objet bloc `doc` par le modèle de `tex`, ou repeint son cube ; rend l'aperçu ou None."""
    block = doc["BlockType"]
    if tex in CUBES:
        preview, textures = build_cube(tex)
        block["Textures"] = textures
        return preview
    if tex not in BLOCKS:
        return None
    preview, keys = build(tex)
    block.pop("Textures", None)
    block.update(keys)
    doc["IconProperties"] = {"Scale": 0.55, "Translation": [0, -12], "Rotation": [22.5, 45, 22.5]}
    stale = COMMON / CUBE_TEXTURES / f"{tex}.png"
    if stale.exists():
        stale.unlink()
    return preview


def sheet(previews, path, per_row=6):
    w = 256
    rows = (len(previews) + per_row - 1) // per_row
    img = Image.new("RGBA", (w * min(per_row, len(previews)), w * rows), (36, 38, 52, 255))
    for k, p in enumerate(previews):
        img.alpha_composite(p.resize((w, w), Image.LANCZOS), (w * (k % per_row), w * (k // per_row)))
    img.save(path)


def main():
    out = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    previews = [build(tex)[0] for tex in BLOCKS] + [build_cube(tex)[0] for tex in CUBES]
    if out:
        out.mkdir(parents=True, exist_ok=True)
        sheet(previews, out / "blocs_3d.png")
    print(f"{len(BLOCKS)} modèles de blocs, {len(CUBES)} cubes repeints")


if __name__ == "__main__":
    main()
