#!/usr/bin/env python3
"""Génère les contrats de primes des chasseurs : clés, types de portail, instances et mini-fragments.

    python3 mods/nakasar-vampires/tools/generate_contracts.py [--preview DOSSIER]

Un contrat est une clé de portail (comme la clé du Comté) fabriquée à l'établi des chasseurs, onglet
Contrats. Posée dans un Portal_Device, elle ouvre un mini-fragment où tout le groupe peut entrer : une
petite île flottante de nuit, la crypte d'arrivée (avec son portail de retour) au centre et, au nord,
le lieu de la cible, repris tel quel des structures du Comté avec ses blocs d'apparition (l'élite et
sa garde). Tuer la cible remplit le contrat : elle lâche, avec son trophée, le sac de prime du contrat,
un seul pour tout le groupe (ContractBounties, Java ; sacs dans generate_trophies.py).

| Contrat  | Niveau | Lieu (prefabs du Comté)       | Cible                       |
| -------- | ------ | ----------------------------- | --------------------------- |
| Farm     | 1      | Farms/Zombies                 | Nakasar_Zombie_Abomination  |
| Pumpkin  | 2      | PumpkinFields/Giant           | Nakasar_Giant_Pumpkin       |
| Garrison | 2      | GuardPosts/Garrison           | Nakasar_Guard_Captain       |
| Crypt    | 2      | Crypts/Guarded                | Nakasar_Enchanted_Armor     |
| Castle   | 3      | HauntedCastles/Spectre        | Nakasar_Spectre             |

Les cibles et les primes sont aussi écrites dans ContractBounties.java : les garder alignées.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import generate_worldgen as wg

PACK = wg.PACK
SERVER = PACK / "Server"
COMMON = PACK / "Common"
LANG = "nakasar_hunters"
BENCH = "Nakasar_Hunter_Workbench"
TAB = "Nakasar_Hunter_Contracts"
ICONS = "Icons/Items/Nakasar/Contracts"
FANG = "Nakasar_Trophy_Vampire_Fang"

GROUND_Y = wg.GROUND_Y
SPAWN = (0, GROUND_Y, 0)
# Lieu de la cible, au nord de la crypte d'arrivée (dont la porte donne au nord) : la ferme fait
# 49 × 45 blocs, son bord sud reste à une quinzaine de blocs de la crypte.
TARGET = (0, GROUND_Y, -54)
ISLAND_RADIUS = 112.0
EDGE_START = 92.0
TIME_LIMIT = 900

# id court, niveau de l'établi, dossier de prefabs, couleur du sceau, ingrédients, tags du portail
CONTRACTS = [
    ("Farm", 1, "Farms/Zombies", (150, 40, 40),
     [(FANG, 2), ("Ingredient_Bar_Silver", 1), ("Ingredient_Fabric_Scrap_Linen", 2), ("Ingredient_Rune_Shard", 1)],
     ["undead", "elite"]),
    ("Pumpkin", 2, "PumpkinFields/Giant", (214, 110, 30),
     [(FANG, 2), ("Ingredient_Bar_Silver", 1), ("Ingredient_Fabric_Scrap_Linen", 2), ("Ingredient_Rune_Shard", 1)],
     ["plant", "elite"]),
    ("Garrison", 2, "GuardPosts/Garrison", (60, 70, 150),
     [(FANG, 4), ("Ingredient_Bar_Silver", 2), ("Ingredient_Fabric_Scrap_Linen", 2), ("Ingredient_Rune_Shard", 2)],
     ["undead", "elite", "prison"]),
    ("Crypt", 2, "Crypts/Guarded", (70, 120, 200),
     [(FANG, 3), ("Ingredient_Bar_Silver", 2), ("Ingredient_Fabric_Scrap_Linen", 2), ("Ingredient_Rune_Shard", 2)],
     ["construct", "elite", "fireproof"]),
    ("Castle", 3, "HauntedCastles/Spectre", (150, 200, 230),
     [(FANG, 4), ("Ingredient_Bar_Silver", 3), ("Ingredient_Fabric_Scrap_Linen", 3), ("Ingredient_Rune_Shard", 3)],
     ["undead", "elite", "frost"]),
]
DISPLAY_NAMES = {"Farm": "Contrat : la Bête de la ferme", "Pumpkin": "Contrat : le Champ maudit",
                 "Garrison": "Contrat : la Garnison du Capitaine", "Crypt": "Contrat : le Gardien de la crypte",
                 "Castle": "Contrat : le Spectre du château"}
TAG_COLORS = {"undead": "#9b59b6", "elite": "#c0392b", "plant": "#ff7518", "prison": "#7f8c8d",
              "construct": "#5a8fd8", "fireproof": "#e67e22", "frost": "#8fd4ff"}


def ids(short):
    return {
        "item": f"Nakasar_Contract_{short}",
        "portal": f"Nakasar_Contract_{short}",
        "instance": f"Nakasar_Contract_{short}",
        "biome": f"Nakasar_Contract_{short}_Island",
        "structure": f"Nakasar_Contract_{short}",
        "key": f"{LANG}.contract.{short.lower()}",
    }


# --- objets et portails -----------------------------------------------------------------------

def item(short, tier, inputs):
    i = ids(short)
    return {
        "Parent": "PortalKey_Taiga",
        "TranslationProperties": {"Name": f"{LANG}.items.{i['item']}.name",
                                  "Description": f"{LANG}.items.{i['item']}.description"},
        "Icon": f"{ICONS}/Contract_{short}.png",
        "Quality": "Rare",
        # Recette écrite dans l'objet : il hériterait sinon de celle de son parent, s'il en a une.
        "Recipe": {
            "TimeSeconds": 3,
            "KnowledgeRequired": False,
            "Input": [{"ItemId": k, "Quantity": q} for k, q in inputs],
            "BenchRequirement": [{"Type": "Crafting", "Id": BENCH, "Categories": [TAB], "RequiredTierLevel": tier}],
        },
        "PortalKey": {"PortalType": i["portal"], "TimeLimitSeconds": TIME_LIMIT},
    }


def portal_type(short, color, tags):
    i = ids(short)
    return {
        "InstanceId": i["instance"],
        "Description": {
            "DisplayName": f"{i['key']}.name",
            "FlavorText": f"{i['key']}.flavor",
            "ThemeColor": "#%02x%02x%02x" % color,
            "DescriptionTags": [{"TranslationKey": f"{LANG}.contract.tag.{t}", "Color": TAG_COLORS[t]} for t in tags],
            "Objectives": [f"{i['key']}.objective"],
        },
        "Spawn": {
            # Le portail de retour est dans la crypte d'arrivée (prefab), pas sur le point d'arrivée :
            # voir PortalTypes/Nakasar_Halloween.json.
            "SpawnReturnPortal": False,
            "SpawnProviderOverride": {"Id": "Global", "SpawnPoint": {"X": 0.5, "Y": float(GROUND_Y), "Z": 0.5, "Yaw": 0.0}},
        },
        "TimeLimitSeconds": TIME_LIMIT,
        "CloseWhenEmpty": True,
        "VoidInvasionEnabled": False,
    }


def instance(short):
    i = ids(short)
    return {
        "DisplayName": DISPLAY_NAMES[short],
        "WorldGen": {"Type": "HytaleGenerator", "WorldStructure": i["structure"]},
        "ForcedWeather": "Nakasar_Weather_Halloween",
        "GameTime": "0001-01-01T22:00:00Z",
        "DaytimeDurationSeconds": 300,
        "NighttimeDurationSeconds": 1200,
        "IsPvpEnabled": False,
        "IsSpawningNPC": True,
        "SpawnProvider": {"Id": "Global", "SpawnPoint": {"X": 0.5, "Y": float(GROUND_Y), "Z": 0.5,
                                                         "Pitch": 0, "Yaw": 0, "Roll": 0}},
        "Plugin": {"PortalWorldConfig": {"Config": {"PortalType": i["portal"], "TimeLimitSeconds": TIME_LIMIT}}},
    }


# --- mini-fragment ----------------------------------------------------------------------------

def radial(points):
    return wg.radial(wg.curve(*points))


def biome(short, folder):
    i = ids(short)
    relief = {"Type": "Min", "Inputs": [
        wg.distance_to(wg.list_positions(TARGET), 52.0, wg.curve((0, 0), (34, 0), (50, 1))),
        wg.distance_to(wg.list_positions(SPAWN), 30.0, wg.curve((0, 0), (16, 0), (28, 1))),
    ]}
    hills = wg.add(wg.mul(wg.simplex2d(60.0, 2, "Hills"), wg.const(0.9)),
                   wg.mul(wg.simplex2d(18.0, 2, "Bumps"), wg.const(0.3)))
    top = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(-0.125)),
        wg.column(wg.add(
            wg.const((GROUND_Y - 0.5) / 8.0),
            wg.mul(hills, relief),
            radial([(0, 0), (EDGE_START, 0), (ISLAND_RADIUS, -1.0)]),
        )),
    )
    bottom_depth = [(0, 56), (0.5, 46), (0.8, 34), (0.95, 22), (1.0, 14)]
    bottom_curve = [(f * ISLAND_RADIUS, d / 8.0 - GROUND_Y / 8.0) for f, d in bottom_depth]
    bottom_curve.append((ISLAND_RADIUS + 1.0, -(GROUND_Y + 200) / 8.0))
    rim = wg.mul(wg.simplex2d(30.0, 2, "Rim"), radial([(0, 0), (ISLAND_RADIUS - 24.0, 0), (ISLAND_RADIUS - 4.0, 1.6)]))
    bottom = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(0.125)),
        wg.column(wg.add(radial(bottom_curve), wg.mul(wg.simplex2d(16.0, 2, "Underside"), wg.const(0.7)), rim)),
    )
    materials = {
        "Type": "Solidity",
        "Solid": {"Type": "Queue", "Queue": [
            {"Type": "SpaceAndDepth", "LayerContext": "DepthIntoFloor", "MaxExpectedDepth": 5, "Layers": [
                {"Type": "ConstantThickness", "Thickness": 1, "Material": wg.field_material(
                    wg.simplex2d(17.0, 2, "Patches"),
                    (-10.0, -0.5, wg.material("Soil_Ash")),
                    (-0.5, 0.5, wg.weighted_material("Surface", ("Soil_Grass_Burnt", 10), ("Soil_Dirt_Burnt", 1))),
                    (0.5, 10.0, wg.weighted_material("Gravel", ("Soil_Gravel_Mossy", 3), ("Soil_Gravel", 1))),
                )},
                {"Type": "ConstantThickness", "Thickness": 4, "Material": wg.weighted_material(
                    "Subsoil", ("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 2), ("Soil_Gravel", 1))},
            ]},
            wg.weighted_material("Bedrock", ("Rock_Stone", 6), ("Rock_Stone_Mossy", 1), ("Rock_Slate", 2)),
        ]},
        "Empty": {"Type": "Constant", "Material": wg.AIR},
    }
    big = lambda path, seed: wg.surface_locator(wg.prefab(path, seed, rotate=False), wg.SOLID_FLOOR, 12)
    target = wg.runtime(0, "Prop", wg.list_positions(TARGET), {"Type": "Constant", "Prop": big(folder, "Target")})
    crypt = wg.runtime(0, "Prop", wg.list_positions(SPAWN), {"Type": "Constant", "Prop": big("SpawnCrypt", "SpawnCrypt")})

    def clear(positions):
        """Pas d'arbre sur le lieu de la cible, la crypte ou le bord de l'île."""
        positions = wg.within(wg.distance_to(wg.list_positions(TARGET), 39.0, wg.curve((0, 0), (39, 39))), 38.0, 1.0e9, positions)
        positions = wg.within(wg.distance_to(wg.list_positions(SPAWN), 19.0, wg.curve((0, 0), (19, 19))), 18.0, 1.0e9, positions)
        return wg.within(radial([(0, 0), (ISLAND_RADIUS, ISLAND_RADIUS)]), 0.0, EDGE_START, positions)

    tree = lambda path, n: wg.surface_locator(wg.prefab(path, f"ContractTree{n}", vanilla=True), wg.GRASS_FLOOR, 20)
    trees = wg.runtime(1, "Chunk", clear(wg.mesh(9.0, 0.45, "Trees")), wg.weighted_assignments(
        "TreePick", 0.3, [(tree(p, n), w) for n, (p, w) in enumerate(wg.FOREST_TREES + wg.LONE_TREES)]))

    def plant(name):
        return wg.surface_locator({"Type": "Manual", "Blocks": [
            {"Position": {"X": 0, "Y": 0, "Z": 0}, "Material": {"Solid": name}}]}, wg.GRASS_FLOOR, 20)

    plants = wg.runtime(2, "Chunk", wg.mesh(3.0, 0.5, "Plants"), wg.weighted_assignments("PlantPick", 0.5, [
        (plant("Plant_Grass_Gnarled"), 5.0), (plant("Plant_Grass_Gnarled_Short"), 4.0),
        (plant("Plant_Bush_Dead"), 1.5), (plant("Plant_Leaves_Dead"), 0.6), (plant("Plant_Fern_Forest"), 0.5),
    ]))
    return {
        "Name": i["biome"],
        "Terrain": {"Type": "DAOTerrain", "Density": {"Type": "Min", "Inputs": [top, bottom]}},
        "MaterialProvider": materials,
        "Props": [target, crypt, trees, plants],
        "EnvironmentProvider": {"Type": "Constant", "Environment": "Nakasar_Env_Contract"},  # sans rejetons de vampire
        "TintProvider": {"Type": "Constant", "Color": "#7a6534"},
    }


def world_structure(short):
    return {
        "Type": "NoiseRange",
        "DefaultBiome": ids(short)["biome"],
        "DefaultTransitionDistance": 16,
        "MaxBiomeEdgeDistance": 0,
        "Density": wg.const(0.0),
        "Biomes": [],
        "SpawnPositions": wg.list_positions(SPAWN),
    }


# --- icônes -----------------------------------------------------------------------------------

PAPER = (226, 210, 168)
PAPER_DARK = (176, 150, 104)
INK = (60, 36, 30)


def contract_icon(short, seal):
    """Parchemin déroulé, quelques lignes d'encre, un emblème de la cible et un sceau de cire."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((12, 8, 52, 56), fill=PAPER + (255,), outline=PAPER_DARK + (255,))
    d.rectangle((9, 5, 55, 10), fill=PAPER_DARK + (255,))
    d.rectangle((9, 54, 55, 59), fill=PAPER_DARK + (255,))
    for y in (16, 21, 26):
        d.line((17, y, 47, y), fill=INK + (255,), width=1)
    if short == "Farm":       # fourche
        d.line((32, 30, 32, 46), fill=INK + (255,), width=2)
        for x in (27, 32, 37):
            d.line((x, 30, x, 35), fill=INK + (255,), width=2)
        d.line((27, 35, 37, 35), fill=INK + (255,), width=2)
    elif short == "Pumpkin":  # citrouille
        d.ellipse((24, 32, 40, 46), fill=(214, 110, 30, 255), outline=INK + (255,))
        d.line((32, 28, 32, 33), fill=(60, 120, 40, 255), width=2)
    elif short == "Crypt":    # roue dentée
        d.ellipse((25, 31, 39, 45), fill=(176, 120, 58, 255), outline=INK + (255,))
        for x, y in ((32, 29), (32, 47), (23, 38), (41, 38)):
            d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=(176, 120, 58, 255), outline=INK + (255,))
        d.ellipse((30, 36, 34, 40), fill=(90, 170, 255, 255))
    elif short == "Castle":   # fantôme
        d.pieslice((25, 29, 39, 43), 180, 360, fill=(220, 236, 248, 255), outline=INK + (255,))
        d.rectangle((25, 36, 39, 45), fill=(220, 236, 248, 255))
        for x in (25, 30, 35):
            d.polygon(((x, 45), (x + 2, 47), (x + 4, 45)), fill=(220, 236, 248, 255))
        d.rectangle((28, 34, 29, 36), fill=INK + (255,))
        d.rectangle((34, 34, 35, 36), fill=INK + (255,))
    else:                     # heaume
        d.rectangle((26, 31, 38, 45), fill=(120, 124, 132, 255), outline=INK + (255,))
        d.line((26, 37, 38, 37), fill=INK + (255,), width=2)
    d.ellipse((38, 40, 52, 54), fill=seal + (255,), outline=tuple(int(c * 0.6) for c in seal) + (255,))
    d.ellipse((42, 44, 48, 50), fill=tuple(min(255, int(c * 1.3)) for c in seal) + (255,))
    return img


def category_icon():
    """Onglet Contrats : un parchemin roulé et scellé."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 22, 56, 42), radius=9, fill=PAPER + (255,), outline=PAPER_DARK + (255,), width=2)
    d.ellipse((4, 22, 20, 42), fill=PAPER_DARK + (255,))
    d.ellipse((8, 26, 16, 38), fill=PAPER + (255,))
    d.rectangle((30, 20, 36, 44), fill=(150, 40, 40, 255))
    d.ellipse((26, 26, 40, 40), fill=(170, 40, 44, 255), outline=(100, 20, 24, 255))
    return img


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
    (COMMON / ICONS).mkdir(parents=True, exist_ok=True)
    icons = []
    for short, tier, folder, seal, inputs, tags in CONTRACTS:
        i = ids(short)
        write_json(SERVER / "Item/Items/Portal/Nakasar" / f"{i['item']}.json", item(short, tier, inputs))
        write_json(SERVER / "PortalTypes" / f"{i['portal']}.json", portal_type(short, seal, tags))
        write_json(SERVER / "Instances" / i["instance"] / "instance.bson", instance(short))
        write_json(SERVER / "HytaleGenerator/Biomes" / f"{i['biome']}.json", biome(short, folder))
        write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{i['structure']}.json", world_structure(short))
        icon = contract_icon(short, seal)
        icon.save(COMMON / ICONS / f"Contract_{short}.png")
        icons.append(icon)
    category_icon().save(COMMON / "Icons/CraftingCategories/Nakasar/Contracts.png")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (64 * (len(icons) + 1), 64), (40, 40, 48, 255))
        for n, icon in enumerate(icons + [category_icon()]):
            sheet.alpha_composite(icon, (64 * n, 0))
        sheet.resize((sheet.width * 3, 192), Image.NEAREST).save(preview / "contrats.png")


if __name__ == "__main__":
    main()
