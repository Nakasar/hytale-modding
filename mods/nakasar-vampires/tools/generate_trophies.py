#!/usr/bin/env python3
"""Génère les trophées de la voie des chasseurs et les sceaux qui font monter l'établi.

    python3 mods/nakasar-vampires/tools/generate_trophies.py [--preview DOSSIER]

Trophées (lâchés par les créatures du Comté, voir Server/Drops/Nakasar/Trophies/) :
- croc de vampire : un rejeton sur deux ;
- cœur d'Abomination, insigne du Capitaine de la garde, graine de la Citrouille géante : toujours, un
  par élite tuée.

Sceaux (fabriqués à l'établi des chasseurs, onglet Trophées) : ce sont eux que demandent les
améliorations de l'établi, parce qu'une amélioration ne prend qu'une liste fixe d'ingrédients alors
que le document de progression demande « un trophée d'élite, n'importe lequel ». Chaque monde du Comté
n'a pas toutes les élites (fermes, postes de garde et champs tirés au sort), d'où une recette de sceau
par trophée ou paire de trophées :
- Sceau du traqueur (niveau 1) : 3 crocs + un trophée d'élite, au choix ;
- Sceau du chasseur (niveau 2) : 4 crocs + deux trophées d'élite différents, au choix.

Écrit les objets, leurs modèles (.blockymodel, même écriture que l'autel : 32 unités = 1 bloc), leurs
textures et icônes, les listes de butin des trophées, les recettes des sceaux et l'icône de l'onglet.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

from PIL import Image, ImageDraw

import generate_altar as ga

ROOT = ga.ROOT
SERVER = ROOT / "Server"
ITEMS = SERVER / "Item/Items/Trophy/Nakasar"
RECIPES = SERVER / "Item/Recipes/Nakasar"
DROPS = SERVER / "Drops/Nakasar/Trophies"
MODELS = "Items/Nakasar/Trophies"
ICONS = "Icons/Items/Nakasar/Trophies"
CATEGORIES = ROOT / "Common/Icons/CraftingCategories/Nakasar"
LANG = "nakasar_hunters"
BENCH = "Nakasar_Hunter_Workbench"
TAB = "Nakasar_Hunter_Trophies"

FANG = "Nakasar_Trophy_Vampire_Fang"
HEART = "Nakasar_Trophy_Abomination_Heart"
INSIGNIA = "Nakasar_Trophy_Captain_Insignia"
SEED = "Nakasar_Trophy_Pumpkin_Seed"
ELITES = [HEART, INSIGNIA, SEED]
SEAL_TRACKER = "Nakasar_Hunter_Seal_Tracker"
SEAL_HUNTER = "Nakasar_Hunter_Seal_Hunter"

IVORY = (232, 222, 196)
GUM = (122, 30, 40)
FLESH = (128, 26, 34)
FLESH_DARK = (82, 14, 24)
VEIN = (70, 40, 92)
ROT = (110, 128, 60)
IRON = (84, 86, 94)
GOLD = (214, 172, 70)
BONE = (226, 214, 186)
SEED_SHELL = (196, 120, 46)
SEED_DARK = (130, 72, 30)
SPROUT = (120, 220, 90)
SILVER = (196, 204, 214)
SILVER_DARK = (138, 146, 160)
RIBBON_RED = (150, 30, 40)
RIBBON_BLUE = (40, 70, 150)
STAKE = (138, 100, 70)


def flat(color, top=None):
    return lambda w, h, kind, face: ga.paint_flat(w, h, color, kind, top_color=top or ga.shade(color, 1.1))


def smooth(color):
    return lambda w, h, kind, face: ga.paint_stone(w, h, color, kind)


def glow(color):
    return lambda w, h, kind, face: ga.paint_flat(w, h, color, "top", top_color=color)


def fang_parts(side, x0, flip):
    """Un croc courbe : racine rouge, puis des tronçons qui rétrécissent et s'écartent en X."""
    return [
        (f"Gum_{side}", (x0, 13, 0), (5, 3, 4), 0, smooth(GUM), "flat"),
        (f"Fang_{side}_A", (x0, 10, 0), (4, 4, 3), 0, smooth(IVORY), "flat"),
        (f"Fang_{side}_B", (x0 + 0.5 * flip, 6.5, 0), (3, 3, 3), 0, smooth(IVORY), "flat"),
        (f"Fang_{side}_C", (x0 + 1.0 * flip, 3.5, 0), (2, 3, 2), 0, smooth(IVORY), "flat"),
        (f"Fang_{side}_Tip", (x0 + 1.5 * flip, 1.5, 0), (1, 1, 1), 0, flat(IVORY), "flat"),
    ]


def medal_parts(metal, metal_dark, ribbon, emblem):
    return [
        ("Ribbon_L", (-2, 15, -0.5), (3, 8, 1), 0, flat(ribbon), "flat"),
        ("Ribbon_R", (2, 15, -0.5), (3, 8, 1), 0, flat(ribbon), "flat"),
        ("Disc_H", (0, 6, 0), (12, 6, 2), 0, smooth(metal), "flat"),
        ("Disc_V", (0, 6, 0), (6, 12, 2), 0, smooth(metal), "flat"),
        ("Disc_C", (0, 6, 0), (10, 10, 2), 0, smooth(metal), "flat"),
        ("Rim", (0, 6, 0.6), (8, 8, 1), 0, flat(metal_dark), "flat"),
        ("Emblem_Stake", (0, 6, 1.2), (2, 7, 1), 0, flat(emblem), "flat"),
        ("Emblem_Bar", (0, 7.5, 1.2), (5, 1, 1), 0, flat(emblem), "flat"),
    ]


# id, qualité, niveau, pile max, pièces du modèle, centre du rendu d'icône, échelle du rendu
MODELS_DEF = {
    FANG: ("Uncommon", 15, 25, fang_parts("L", -3.5, 1) + fang_parts("R", 3.5, -1) + [
        ("Cord", (0, 15, 0), (12, 1, 1), 0, flat((92, 60, 44)), "flat")], (0, 8, 0), 10.0),
    HEART: ("Rare", 25, 10, [
        ("Core", (0, 6, 0), (8, 8, 7), 0, smooth(FLESH), "flat"),
        ("Lobe_L", (-2.5, 10.5, 0), (4, 3, 5), 0, smooth(FLESH), "flat"),
        ("Lobe_R", (2.5, 10.5, 0), (4, 3, 5), 0, smooth(FLESH), "flat"),
        ("Point", (0.5, 1.5, 0), (4, 2, 4), 0, smooth(FLESH_DARK), "flat"),
        ("Vessel_A", (-1.5, 13.5, 0), (2, 3, 2), 0, flat(VEIN), "flat"),
        ("Vessel_B", (1.5, 14, -1), (2, 4, 2), 0, flat(VEIN), "flat"),
        ("Rot_A", (-3.6, 6, 1.5), (1, 3, 2), 0, flat(ROT), "flat"),
        ("Rot_B", (2.5, 4, 3.6), (2, 2, 1), 0, flat(ROT), "flat"),
        ("Stitch", (0, 7, 3.6), (5, 1, 1), 0, flat((40, 30, 30)), "flat"),
    ], (0, 7, 0), 11.0),
    INSIGNIA: ("Rare", 25, 10, [
        ("Plate", (0, 7, 0), (10, 10, 1), 0, smooth(IRON), "flat"),
        ("Point", (0, 1, 0), (6, 3, 1), 0, smooth(IRON), "flat"),
        ("Rim_Top", (0, 12.5, 0.5), (12, 1, 1), 0, flat(GOLD), "flat"),
        ("Rim_L", (-5.5, 7, 0.5), (1, 10, 1), 0, flat(GOLD), "flat"),
        ("Rim_R", (5.5, 7, 0.5), (1, 10, 1), 0, flat(GOLD), "flat"),
        ("Skull", (0, 8, 0.8), (4, 3, 1), 0, flat(BONE), "flat"),
        ("Jaw", (0, 5.5, 0.8), (2, 2, 1), 0, flat(BONE), "flat"),
        ("Eye_L", (-1, 8, 1.2), (1, 1, 1), 0, flat((30, 24, 24)), "flat"),
        ("Eye_R", (1, 8, 1.2), (1, 1, 1), 0, flat((30, 24, 24)), "flat"),
    ], (0, 7, 0), 11.0),
    SEED: ("Rare", 25, 10, [
        ("Shell", (0, 6, 0), (6, 9, 4), 0, smooth(SEED_SHELL), "flat"),
        ("Shell_Wide", (0, 5, 0), (7, 5, 3), 0, smooth(SEED_SHELL), "flat"),
        ("Tip", (0, 1, 0), (3, 2, 2), 0, smooth(SEED_DARK), "flat"),
        ("Ridge", (0, 6, 2.2), (1, 7, 1), 0, flat(SEED_DARK), "flat"),
        ("Sprout", (0.5, 12, 0), (1, 4, 1), 0, glow(SPROUT), "fullbright"),
        ("Leaf_A", (2, 13.5, 0), (3, 1, 2), 25, glow(SPROUT), "fullbright"),
        ("Leaf_B", (-1, 14.5, 0), (2, 1, 2), -20, glow(SPROUT), "fullbright"),
    ], (0, 7, 0), 11.0),
    SEAL_TRACKER: ("Epic", 30, 5, medal_parts(SILVER, SILVER_DARK, RIBBON_RED, STAKE), (0, 9, 0), 9.0),
    SEAL_HUNTER: ("Epic", 40, 5, medal_parts(GOLD, ga.shade(GOLD, 0.7), RIBBON_BLUE, SILVER), (0, 9, 0), 9.0),
}


def model_json(uv, name):
    model = ga.build_model(uv)
    model["nodes"][0]["name"] = name
    return model


def item(item_id, quality, level, stack):
    name = item_id.removeprefix("Nakasar_")
    return {
        "TranslationProperties": {
            "Name": f"{LANG}.items.{item_id}.name",
            "Description": f"{LANG}.items.{item_id}.description",
        },
        "Icon": f"{ICONS}/{name}.png",
        "Model": f"{MODELS}/{name}.blockymodel",
        "Texture": f"{MODELS}/{name}.png",
        "Quality": quality,
        "ItemLevel": level,
        "Categories": ["Items.Ingredients"],
        "Tags": {"Type": ["Nakasar_Trophy"]},
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": stack,
    }


def recipe(output, inputs, tier, time=2):
    return {
        "TimeSeconds": time,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": i, "Quantity": q} for i, q in inputs],
        "PrimaryOutput": {"ItemId": output, "Quantity": 1},
        "Output": [{"ItemId": output, "Quantity": 1}],
        "BenchRequirement": [{"Type": "Crafting", "Id": BENCH, "Categories": [TAB], "RequiredTierLevel": tier}],
    }


def short(item_id):
    return item_id.rsplit("_", 1)[-1]


def drops():
    single = lambda i: {"Type": "Single", "Item": {"ItemId": i, "QuantityMin": 1, "QuantityMax": 1}}
    return {
        FANG: {"Container": {"Type": "Choice", "Containers": [
            dict(single(FANG), Weight=1), {"Type": "Empty", "Weight": 1}]}},
        HEART: {"Container": single(HEART)},
        INSIGNIA: {"Container": single(INSIGNIA)},
        SEED: {"Container": single(SEED)},
    }


def recipes():
    out = {}
    for elite in ELITES:
        out[f"Recipe_{SEAL_TRACKER}_{short(elite)}"] = recipe(SEAL_TRACKER, [(FANG, 3), (elite, 1)], 1)
    for a, b in combinations(ELITES, 2):
        out[f"Recipe_{SEAL_HUNTER}_{short(a)}_{short(b)}"] = recipe(
            SEAL_HUNTER, [(FANG, 4), (a, 1), (b, 1), ("Ingredient_Bar_Silver", 2)], 2, time=4)
    return out


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def category_icon(fang_icon):
    """Onglet Trophées : le croc, sur fond transparent, en 64 x 64."""
    CATEGORIES.mkdir(parents=True, exist_ok=True)
    fang_icon.save(CATEGORIES / "Trophies.png")


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
    (ROOT / "Common" / MODELS).mkdir(parents=True, exist_ok=True)
    (ROOT / "Common" / ICONS).mkdir(parents=True, exist_ok=True)
    sheet = []
    for item_id, (quality, level, stack, parts, center, scale) in MODELS_DEF.items():
        name = item_id.removeprefix("Nakasar_")
        ga.PARTS = parts
        ga.TEX_W, ga.TEX_H = 64, 64
        atlas, uv = ga.build_atlas()
        atlas.save(ROOT / "Common" / MODELS / f"{name}.png")
        (ROOT / "Common" / MODELS / f"{name}.blockymodel").write_text(json.dumps(model_json(uv, name), indent=2) + "\n")
        icon = ga.render(atlas, uv, 256, yaw=-30, pitch=20, scale=scale, center=center).resize((64, 64), Image.LANCZOS)
        icon.save(ROOT / "Common" / ICONS / f"{name}.png")
        if item_id == FANG:
            category_icon(icon)
        write_json(ITEMS / f"{item_id}.json", item(item_id, quality, level, stack))
        if preview:
            sheet.append(ga.render(atlas, uv, 256, yaw=-30, pitch=20, scale=scale, center=center))
    for item_id, doc in drops().items():
        write_json(DROPS / f"Nakasar_Drop_Trophy_{item_id.removeprefix('Nakasar_Trophy_')}.json", doc)
    for name, doc in recipes().items():
        write_json(RECIPES / f"{name}.json", doc)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        out = Image.new("RGBA", (256 * len(sheet), 256), (40, 40, 48, 255))
        for i, img in enumerate(sheet):
            out.alpha_composite(img, (256 * i, 0))
        out.save(preview / "trophees.png")


if __name__ == "__main__":
    main()
