#!/usr/bin/env python3
"""Génère les tenues cosmétiques du mod (sans protection) et les recettes de décor du Comté.

    python3 mods/nakasar-vampires/tools/generate_cosmetics.py [--preview DOSSIER]

- Tenue de chasseur (établi des chasseurs, onglet Tenues, niveau 1) :
  - Armor_Nakasar_Hunter_Hat (tête) : chapeau de cuir sombre à larges bords et bande d'argent ;
  - Armor_Nakasar_Hunter_Coat (torse) : long manteau de cuir à pèlerine, col relevé, boutons d'argent et pans qui
    tombent sur les jambes (pièce sur l'os Pelvis).
- Tenue de l'Alchimiste (autel sacrificiel, onglet Décor et tenues, et établi des chasseurs, onglet Tenues,
  niveau 3) : les pièces du boss (tools/generate_alchemist_models.py) portées par le joueur :
  - Armor_Nakasar_Alchemist_Mask (tête) : le masque à bec ;
  - Armor_Nakasar_Alchemist_Garb (torse) : la bavette, la ceinture, la jupe du tablier et les fioles.
- Blocs du manoir (autel, onglet Décor et tenues, niveau 1) : vitraux pourpre et violet, gargouille, grille et vantail
  de portail en fer forgé (les blocs existent déjà, tools/generate_assets.py du Comté ; seules les recettes sont ici).

Écrit : modèles et textures (Common/Items/Nakasar/Cosmetics/<Nom>/), icônes (Common/Icons/Items/Nakasar/Cosmetics/),
icônes des onglets (Common/Icons/CraftingCategories/Nakasar/Cosmetics.png, Decor.png), objets
(Server/Item/Items/Cosmetic/Nakasar/) et recettes (Server/Item/Recipes/Nakasar/Cosmetics/).
Les onglets sont déclarés à la main dans les deux établis (Server/Item/Items/Bench/Nakasar/) et les textes dans
Server/Languages/*/nakasar_cosmetics.lang.

Même repère que tools/generate_pumpkin_models.py : 64 unités = 1 bloc, devant vers +Z ; les pièces sont placées par
rapport au centre de l'os (tête 30 × 28 × 28, torse 28 × 22 × 20, bassin 26 × 12 × 18).
"""
import json
import sys
from pathlib import Path

from PIL import Image

import generate_alchemist_models as gam
import generate_pumpkin_models as gpm
from generate_pumpkin_models import Box, Joint, p_round, shade

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
MODELS = "Items/Nakasar/Cosmetics"
ICONS = "Icons/Items/Nakasar/Cosmetics"
CATEGORY_ICONS = COMMON / "Icons/CraftingCategories/Nakasar"
ITEMS = SERVER / "Item/Items/Cosmetic/Nakasar"
RECIPES = SERVER / "Item/Recipes/Nakasar/Cosmetics"
LANG = "nakasar_cosmetics"

ALTAR = ("Nakasar_Sacrificial_Altar", "Nakasar_Altar_Decor")
HUNTERS = ("Nakasar_Hunter_Workbench", "Nakasar_Hunter_Cosmetics")

FELT = (52, 40, 36)
FELT_DARK = (26, 20, 18)
FELT_LIGHT = (86, 68, 58)
COAT = (70, 48, 34)
COAT_DARK = (36, 24, 16)
COAT_LIGHT = (112, 80, 56)
LINEN = (176, 160, 132)
SILVER = (196, 204, 214)
SILVER_DARK = (110, 118, 130)
SILVER_LIGHT = (240, 244, 250)
BACKGROUND = (40, 44, 52, 255)

SALT = "Ingredient_Nakasar_Philosophers_Salt"
SULFUR = "Ingredient_Nakasar_Burning_Sulfur"
MERCURY = "Ingredient_Nakasar_Quicksilver"


# --- modèles ---------------------------------------------------------------------------------------

def hunter_hat():
    """Chapeau à larges bords posé sur la tête (dessus de l'os à y = +14)."""
    felt = p_round(FELT, FELT_DARK, FELT_LIGHT, amp=0.05)
    dark = p_round(FELT_DARK, (14, 10, 8), FELT)
    silver = p_round(SILVER, SILVER_DARK, SILVER_LIGHT)
    return Joint("Head", (0, 0, 0), [
        Box("Brim", (0, 12.2, 0), (46, 1.6, 46), felt),
        Box("BrimFront", (0, 12.6, 21.5), (30, 1.4, 6), dark, rot=(-12, 0, 0)),
        Box("Crown", (0, 19.4, -0.6), (31, 13, 29), felt),
        Box("CrownTop", (0, 26.4, -0.6), (27, 2, 25), dark),
        Box("Band", (0, 14.6, -0.6), (31.8, 3.2, 29.8), dark),
        Box("Buckle", (12.2, 14.6, 10), (5, 4, 1.2), silver, rot=(0, 40, 0)),
    ])


def hunter_coat():
    """Manteau : coque du torse, pèlerine, col relevé et boutons (Chest), pans du manteau (Pelvis)."""
    coat = p_round(COAT, COAT_DARK, COAT_LIGHT, amp=0.05)
    dark = p_round(COAT_DARK, (18, 12, 8), COAT)
    linen = p_round(LINEN, shade(LINEN, 0.6), shade(LINEN, 1.2))
    silver = p_round(SILVER, SILVER_DARK, SILVER_LIGHT)
    chest = [
        Box("Shell", (0, 0, 0), (30.4, 23, 21.6), coat),
        Box("Shirt", (0, 4, 10.9), (6, 14, 0.6), linen),
        Box("Capelet", (0, 7.5, -0.4), (35, 7, 25), dark),
        Box("CollarBack", (0, 14, -10.6), (30, 7, 2), dark, rot=(-10, 0, 0)),
        Box("CollarL", (12.6, 13, -1), (2, 6, 20), dark, rot=(0, 0, -10)),
        Box("CollarR", (-12.6, 13, -1), (2, 6, 20), dark, rot=(0, 0, 10)),
        Box("Belt", (0, -9.5, 0), (31.4, 3, 22.6), p_round(FELT_DARK, (14, 10, 8), FELT)),
        Box("BeltBuckle", (0, -9.5, 11.4), (4.4, 3.6, 1), silver),
    ]
    for k, y in enumerate((-5, 0, 5)):
        chest += [Box(f"ButtonL{k}", (5, y, 11.1), (1.8, 1.8, 0.8), silver),
                  Box(f"ButtonR{k}", (-5, y, 11.1), (1.8, 1.8, 0.8), silver)]
    pelvis = [
        Box("Waist", (0, 0, 0), (28.4, 12.6, 19.6), coat),
        Joint("TailBack", (0, 3, -10), [Box("TailBackBox", (0, -15, 0), (27, 30, 1.4), coat)], rot=(8, 0, 0)),
        Joint("TailL", (10, 3, 10), [Box("TailLBox", (0, -14, 0), (9, 28, 1.2), coat)], rot=(-6, 0, 0)),
        Joint("TailR", (-10, 3, 10), [Box("TailRBox", (0, -14, 0), (9, 28, 1.2), coat)], rot=(-6, 0, 0)),
        Joint("TailSideL", (14.4, 3, 0), [Box("TailSideLBox", (0, -14, 0), (1.2, 28, 18), coat)], rot=(0, 0, 5)),
        Joint("TailSideR", (-14.4, 3, 0), [Box("TailSideRBox", (0, -14, 0), (1.2, 28, 18), coat)], rot=(0, 0, -5)),
    ]
    return [Joint("Chest", (0, 0, 0), chest), Joint("Pelvis", (0, 0, 0), pelvis)]


def alchemist_mask():
    return [gam.mask()]


def alchemist_garb():
    return [gam.bib(), gam.belt()]


# --- écriture --------------------------------------------------------------------------------------

def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def transparent(img):
    """Le rendu a un fond gris opaque : il devient transparent pour les icônes."""
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            if px[x, y] == BACKGROUND:
                px[x, y] = (0, 0, 0, 0)
    return img


def full_body(roots):
    """Les pièces aux os du mannequin (gam.mannequin attend tête, torse, bassin), pour l'aperçu."""
    by_bone = {r.name: r for r in roots}
    return gam.mannequin([by_bone.get(b, Joint(b, (0, 0, 0), [])) for b in ("Head", "Chest", "Pelvis")])


def worn(roots):
    """Les pièces seules, posées à la hauteur de leurs os comme sur le mannequin, pour l'icône."""
    heights = {"Head": 112, "Chest": 76, "Pelvis": 56}
    return Joint("Worn", (0, 0, 0), [Joint(f"{r.name}Bone", (0, heights[r.name], 0), [r]) for r in roots])


def write_model(name, roots, seed, icon_view, preview):
    folder = COMMON / MODELS / name
    atlas, uv = gpm.build_atlas(Joint(name, (0, 0, 0), roots), seed, 128)
    folder.mkdir(parents=True, exist_ok=True)
    atlas.save(folder / "Texture.png")
    nodes = gpm.model_json(Joint(name, (0, 0, 0), roots), uv)["nodes"][0]["children"]
    for node in nodes:
        node["shape"]["settings"]["isPiece"] = True
    write_json(folder / "Model.blockymodel", {"nodes": nodes, "format": "character", "lod": "auto"})
    alone = worn(roots)
    atlas2, uv2 = gpm.build_atlas(alone, seed, 256)
    icon = gpm.render(alone, atlas2, uv2, {}, size=256, yaw=25, pitch=10, **icon_view)
    (COMMON / ICONS).mkdir(parents=True, exist_ok=True)
    icon = transparent(icon).resize((64, 64), Image.LANCZOS)
    icon.save(COMMON / ICONS / f"{name}.png")
    if preview:
        body = full_body(roots)
        atlas2, uv2 = gpm.build_atlas(body, seed, 256)
        for label, view in (("face", {"yaw": 20, "pitch": 8}), ("profil", {"yaw": 90, "pitch": 5}),
                            ("dos", {"yaw": 200, "pitch": 10})):
            gpm.render(body, atlas2, uv2, {}, size=360, scale=2.2, center=(0, 80, 0), **view).save(
                preview / f"{name}_{label}.png")
    return icon


def write_item(item_id, name, slot, hide, quality):
    write_json(ITEMS / f"{item_id}.json", {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name",
                                  "Description": f"{LANG}.items.{item_id}.description"},
        "Quality": quality,
        "ItemLevel": 10,
        "PlayerAnimationsId": "Block",
        "ItemSoundSetId": "ISS_Armor_Leather",
        "Categories": ["Items.Armors"],
        "Icon": f"{ICONS}/{name}.png",
        "IconProperties": {"Rotation": [0, 0, 0], "Scale": 1.0, "Translation": [0, 0]},
        "Model": f"{MODELS}/{name}/Model.blockymodel",
        "Texture": f"{MODELS}/{name}/Texture.png",
        "Interactions": {"Primary": {"Interactions": [{"Type": "EquipItem"}]},
                         "Secondary": {"Interactions": [{"Type": "EquipItem"}]}},
        "Armor": {"ArmorSlot": slot, "BaseDamageResistance": 0, "CosmeticsToHide": hide},
        "MaxDurability": 1000,
        "Tags": {"Type": ["Armor"], "Family": ["Nakasar_Cosmetic"]},
    })


def write_recipe(item_id, inputs, benches, tier, quantity=1, seconds=3):
    write_json(RECIPES / f"Recipe_{item_id}.json", {
        "TimeSeconds": seconds,
        "KnowledgeRequired": False,
        "Input": [{"ResourceTypeId" if i.startswith("#") else "ItemId": i.lstrip("#"), "Quantity": q}
                  for i, q in inputs],
        "PrimaryOutput": {"ItemId": item_id, "Quantity": quantity},
        "Output": [{"ItemId": item_id, "Quantity": quantity}],
        "BenchRequirement": [{"Type": "Crafting", "Id": bench, "Categories": [tab], "RequiredTierLevel": tier}
                             for bench, tab in benches],
    })


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview.mkdir(parents=True, exist_ok=True)

    head_view = {"scale": 4.4, "center": (0, 128, 0)}
    body_view = {"scale": 3.4, "center": (0, 68, 0)}
    outfits = [
        # id, dossier, os, cosmétiques masqués, qualité, pièces, graine, vue de l'icône
        ("Armor_Nakasar_Hunter_Hat", "Hunter_Hat", "Head", ["HeadAccessory", "Haircut", "EarAccessory"], "Rare",
         [hunter_hat()], 301, head_view),
        ("Armor_Nakasar_Hunter_Coat", "Hunter_Coat", "Chest", ["Overtop", "Cape"], "Rare",
         hunter_coat(), 302, body_view),
        ("Armor_Nakasar_Alchemist_Mask", "Alchemist_Mask", "Head", ["FaceAccessory", "FacialHair"], "Epic",
         alchemist_mask(), 303, {"scale": 4.0, "center": (0, 108, 10)}),
        ("Armor_Nakasar_Alchemist_Garb", "Alchemist_Garb", "Chest", [], "Epic",
         alchemist_garb(), 304, body_view),
    ]
    icons = {}
    for item_id, name, slot, hide, quality, roots, seed, view in outfits:
        icons[name] = write_model(name, roots, seed, view, preview)
        write_item(item_id, name, slot, hide, quality)

    leather, linen, silver, iron = "Ingredient_Leather_Light", "Ingredient_Fabric_Scrap_Linen", \
        "Ingredient_Bar_Silver", "Ingredient_Bar_Iron"
    write_recipe("Armor_Nakasar_Hunter_Hat", [(leather, 4), (linen, 2), (silver, 1)], [HUNTERS], 1)
    write_recipe("Armor_Nakasar_Hunter_Coat", [(leather, 8), (linen, 4), (silver, 2)], [HUNTERS], 1)
    write_recipe("Armor_Nakasar_Alchemist_Mask", [(leather, 4), (iron, 1), (SALT, 1), (MERCURY, 1)],
                 [ALTAR, HUNTERS], 3, seconds=5)
    write_recipe("Armor_Nakasar_Alchemist_Garb", [(leather, 6), (linen, 2), (SULFUR, 1), (MERCURY, 1)],
                 [ALTAR, HUNTERS], 3, seconds=5)

    # Blocs du manoir du Comte.
    write_recipe("Nakasar_Stained_Glass_Red", [("Ingredient_Crystal_Red", 1), (iron, 1)], [ALTAR], 1, quantity=4)
    write_recipe("Nakasar_Stained_Glass_Violet", [("Ingredient_Crystal_Purple", 1), (iron, 1)], [ALTAR], 1,
                 quantity=4)
    write_recipe("Nakasar_Gargoyle", [("Rock_Stone_Cobble", 6), ("Ingredient_Crystal_Red", 1)], [ALTAR], 1)
    write_recipe("Nakasar_Iron_Railing", [(iron, 2)], [ALTAR], 1, quantity=4)
    write_recipe("Nakasar_Iron_Gate", [(iron, 4)], [ALTAR], 1)

    # Onglets : le chapeau pour les tenues des chasseurs, le vitrail pour le décor de l'autel.
    icons["Hunter_Hat"].save(CATEGORY_ICONS / "Cosmetics.png")
    glass = COMMON / "Icons/Items/Nakasar"
    found = sorted(glass.rglob("*Stained_Glass_Red*.png"))
    (Image.open(found[0]) if found else icons["Alchemist_Mask"]).convert("RGBA").resize((64, 64)).save(
        CATEGORY_ICONS / "Decor.png")


if __name__ == "__main__":
    main()
