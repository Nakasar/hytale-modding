"""Modèles 3D des blocs du mod Fractales (passe « vrais assets 3D », lot test de 5 blocs de l'Observatoire).

Chaque bloc a un modèle .blockymodel, son atlas peint et une icône rendue depuis le modèle ; `block_type(tex)` rend les
clés du BlockType (DrawType Model, CustomModel, animation en boucle, particules) que generate_observatory.py pose sur
l'objet. Format et style copiés des blocs vanilla lus dans Assets.zip 0.7.2 (coffre Chest_Epic_Small, feu de camp,
torche) : 32 unités par bloc, origine au centre du bas, face avant vers +Z.

    python generate_block_models.py [--preview DOSSIER]   # écrit les modèles ; --preview : planche d'aperçu
"""
import json
import zlib
import sys
from pathlib import Path

from PIL import Image

import fractal_blocks as fb

ROOT = Path(__file__).resolve().parent.parent / "src/main/resources"
COMMON = ROOT / "Common"
MODELS = "Blocks/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"

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


# tex (nom des fichiers) -> (fabrique, réglages du BlockType)
BLOCKS = {
    "Selection_Console": (selection_console, {"particles": "Dungeon_Goblin_Void_Motes_Cluster", "particle_y": 0.8}),
    "Resonator": (resonator, {"particles": "Dust_Sparkles_Fine", "particle_y": 1.0}),
    "Reward_Chest": (reward_chest, {"particles": "Block_Treasure_Sparks", "particle_y": 0.6}),
    "Exit_Stone": (exit_stone, {"particles": "Dungeon_Goblin_Void_Motes_Cluster", "particle_y": 0.7}),
    "Archivist_Counter": (archivist_counter, {}),
}


def build(tex, seed=None):
    """Écrit modèle, atlas, animation et icône de `tex` ; rend (aperçu 384 px, clés du BlockType)."""
    make, cfg = BLOCKS[tex]
    parts, animation = make()
    model_dir = COMMON / MODELS
    preview = fb.write_block_model(tex, parts, model_dir, COMMON / ICONS, seed or zlib.crc32(tex.encode()))
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
        keys["Particles"] = [{"SystemId": cfg["particles"], "Scale": 1, "PositionOffset": {"Y": cfg["particle_y"]}}]
    return preview, keys


def apply(doc, tex):
    """Remplace le cube de l'objet bloc `doc` par le modèle de `tex` (s'il en a un) ; rend l'aperçu ou None."""
    if tex not in BLOCKS:
        return None
    preview, keys = build(tex)
    block = doc["BlockType"]
    block.pop("Textures", None)
    block.update(keys)
    doc["IconProperties"] = {"Scale": 0.55, "Translation": [0, -12], "Rotation": [22.5, 45, 22.5]}
    stale = COMMON / "BlockTextures/Nakasar/Fractals" / f"{tex}.png"
    if stale.exists():
        stale.unlink()
    return preview


def sheet(previews, path):
    w = 384
    img = Image.new("RGBA", (w * len(previews), w), (36, 38, 52, 255))
    for k, p in enumerate(previews):
        img.alpha_composite(p, (w * k, 0))
    img.save(path)


def main():
    out = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    previews = [build(tex)[0] for tex in BLOCKS]
    if out:
        out.mkdir(parents=True, exist_ok=True)
        sheet(previews, out / "blocs_3d.png")
    print(f"{len(BLOCKS)} modèles de blocs")


if __name__ == "__main__":
    main()
