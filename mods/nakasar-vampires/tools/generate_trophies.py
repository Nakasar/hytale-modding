#!/usr/bin/env python3
"""Génère les trophées de la voie des chasseurs et les sacs de prime des contrats.

    python3 mods/nakasar-vampires/tools/generate_trophies.py [--preview DOSSIER]

Trophées (lâchés par les créatures du Comté, voir Server/Drops/Nakasar/Trophies/) :
- croc de vampire : un rejeton sur deux ;
- cœur d'Abomination, graine de la Citrouille géante, insigne du Capitaine de la garde : toujours, un
  par élite tuée. Les améliorations de l'établi des chasseurs en demandent de précis, de l'élite la
  plus facile à la plus dure : le cœur pour le niveau 2, la graine et l'insigne pour le niveau 3.

Sacs de prime (un par contrat, voir generate_contracts.py) : la cible d'un contrat en lâche un à sa
mort (ContractBounties, Java), un seul pour tout le groupe. Utilisé (clic droit), le sac disparaît et
donne le contenu de sa liste de butin Nakasar_Bounty_<contrat> (interaction Java Nakasar_OpenBountyBag).

Écrit les objets, leurs modèles (.blockymodel, même écriture que l'autel : 32 unités = 1 bloc), leurs
textures et icônes, les listes de butin des trophées et des sacs, et les interactions des sacs.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import generate_altar as ga

ROOT = ga.ROOT
SERVER = ROOT / "Server"
ITEMS = SERVER / "Item/Items/Trophy/Nakasar"
BAG_ITEMS = SERVER / "Item/Items/Bounty/Nakasar"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Bounty"
ROOT_INTERACTIONS = SERVER / "Item/RootInteractions/Nakasar"
DROPS = SERVER / "Drops/Nakasar/Trophies"
MODELS = "Items/Nakasar/Trophies"
ICONS = "Icons/Items/Nakasar/Trophies"
LANG = "nakasar_hunters"

FANG = "Nakasar_Trophy_Vampire_Fang"
HEART = "Nakasar_Trophy_Abomination_Heart"
INSIGNIA = "Nakasar_Trophy_Captain_Insignia"
SEED = "Nakasar_Trophy_Pumpkin_Seed"
SILVER_BAR = "Ingredient_Bar_Silver"
SHARD = "Ingredient_Rune_Shard"

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
LEATHER = (124, 84, 52)
LEATHER_DARK = (88, 58, 38)


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


def bag_parts(tie):
    """Sac de cuir fermé par un lien de couleur (celle du sceau du contrat), une pièce d'argent au flanc."""
    return [
        ("Body", (0, 5, 0), (10, 9, 9), 0, smooth(LEATHER), "flat"),
        ("Body_Wide", (0, 4, 0), (11, 6, 8), 0, smooth(LEATHER), "flat"),
        ("Neck", (0, 10.5, 0), (5, 2, 5), 0, smooth(LEATHER_DARK), "flat"),
        ("Tie", (0, 11.8, 0), (6, 1, 6), 0, flat(tie), "flat"),
        ("Top", (0, 13, 0), (4, 2, 4), 0, smooth(LEATHER), "flat"),
        ("Coin", (2, 5, 4.6), (3, 3, 1), 0, flat(SILVER), "flat"),
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


# contrat, couleur du lien, qualité, contenu (objet, min, max) puis tirages au choix (objet, quantité, poids sur 4)
BAGS = [
    ("Farm", (150, 40, 40), "Rare",
     [(SILVER_BAR, 2, 3), (SHARD, 2, 3), (FANG, 1, 2)], [("Rock_Gem_Topaz", 1, 1)]),
    ("Pumpkin", (214, 110, 30), "Rare",
     [(SILVER_BAR, 3, 4), (SHARD, 2, 4), (FANG, 1, 2), ("Ingredient_Life_Essence_Pumpkin", 2, 3)], [("Rock_Gem_Ruby", 1, 1)]),
    ("Garrison", (60, 70, 150), "Epic",
     [(SILVER_BAR, 4, 6), (SHARD, 3, 5), (FANG, 2, 3), ("Rock_Gem_Topaz", 1, 1)], [("Rock_Gem_Sapphire", 1, 1)]),
]


def bag_id(contract):
    return f"Nakasar_Bounty_Bag_{contract}"


def bag_item(contract, quality):
    item_id = bag_id(contract)
    doc = item(item_id, quality, 20, 16)
    doc["Tags"] = {"Type": ["Nakasar_Bounty"]}
    doc["Interactions"] = {"Secondary": f"Root_{item_id}"}
    return doc


def bag_drop(contents, extra):
    single = lambda i, lo, hi: {"Type": "Single", "Item": {"ItemId": i, "QuantityMin": lo, "QuantityMax": hi}}
    containers = [single(*c) for c in contents]
    for i, lo, weight in extra:
        containers.append({"Type": "Choice", "Containers": [
            dict(single(i, lo, lo), Weight=weight), {"Type": "Empty", "Weight": 4 - weight}]})
    return {"Container": {"Type": "Multiple", "Containers": containers}}


def drops():
    single = lambda i: {"Type": "Single", "Item": {"ItemId": i, "QuantityMin": 1, "QuantityMax": 1}}
    return {
        FANG: {"Container": {"Type": "Choice", "Containers": [
            dict(single(FANG), Weight=1), {"Type": "Empty", "Weight": 1}]}},
        HEART: {"Container": single(HEART)},
        INSIGNIA: {"Container": single(INSIGNIA)},
        SEED: {"Container": single(SEED)},
    }


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
        write_json(ITEMS / f"{item_id}.json", item(item_id, quality, level, stack))
        if preview:
            sheet.append(ga.render(atlas, uv, 256, yaw=-30, pitch=20, scale=scale, center=center))
    for item_id, doc in drops().items():
        write_json(DROPS / f"Nakasar_Drop_Trophy_{item_id.removeprefix('Nakasar_Trophy_')}.json", doc)
    for contract, tie, quality, contents, extra in BAGS:
        item_id = bag_id(contract)
        name = item_id.removeprefix("Nakasar_")
        ga.PARTS = bag_parts(tie)
        ga.TEX_W, ga.TEX_H = 64, 64
        atlas, uv = ga.build_atlas()
        atlas.save(ROOT / "Common" / MODELS / f"{name}.png")
        (ROOT / "Common" / MODELS / f"{name}.blockymodel").write_text(json.dumps(model_json(uv, name), indent=2) + "\n")
        render = ga.render(atlas, uv, 256, yaw=-30, pitch=20, scale=11.0, center=(0, 7, 0))
        render.resize((64, 64), Image.LANCZOS).save(ROOT / "Common" / ICONS / f"{name}.png")
        write_json(BAG_ITEMS / f"{item_id}.json", bag_item(contract, quality))
        write_json(DROPS / f"Nakasar_Bounty_{contract}.json", bag_drop(contents, extra))
        write_json(INTERACTIONS / f"{item_id}_Open.json", {"Type": "Nakasar_OpenBountyBag", "Droplist": f"Nakasar_Bounty_{contract}"})
        write_json(ROOT_INTERACTIONS / f"Root_{item_id}.json", {"Interactions": [f"{item_id}_Open"], "RequireNewClick": True})
        if preview:
            sheet.append(render)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        out = Image.new("RGBA", (256 * len(sheet), 256), (40, 40, 48, 255))
        for i, img in enumerate(sheet):
            out.alpha_composite(img, (256 * i, 0))
        out.save(preview / "trophees.png")


if __name__ == "__main__":
    main()
