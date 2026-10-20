#!/usr/bin/env python3
"""Génère les contrats de primes des chasseurs : clés, types de portail, instances et mini-fragments.

    python3 mods/nakasar-vampires/tools/generate_contracts.py [--preview DOSSIER]

Un contrat est une clé de portail (comme la clé du Comté) fabriquée à l'établi des chasseurs, onglet
Contrats. Posée dans un Portal_Device, elle ouvre un mini-fragment où tout le groupe peut entrer : une
île flottante de nuit faite de plusieurs lobes, la crypte d'arrivée (avec son portail de retour) sur
l'un d'eux et, un à trois lobes plus loin, rarement devant la porte, le lieu de la cible, repris tel
quel des structures du Comté avec ses blocs d'apparition (l'élite et sa garde). Chaque contrat a ses
VARIANTS formes d'île, une par monde (bruit lu en un point fixe, comme les répartitions du Comté), et
son propre paysage (THEMES : relief, forêts, décor). Tuer la cible remplit le contrat : elle lâche, avec son trophée, le sac de prime du contrat,
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
# Point d'arrivée fixe (PortalTypes, instance) : la crypte d'arrivée est toujours en 0, 0, sa porte
# au nord ; c'est l'île qui se place autour d'elle.
SPAWN = (0, GROUND_Y, 0)
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
     ["undead", "elite"]),
    ("Crypt", 2, "Crypts/Guarded", (70, 120, 200),
     [(FANG, 3), ("Ingredient_Bar_Silver", 2), ("Ingredient_Fabric_Scrap_Linen", 2), ("Ingredient_Rune_Shard", 2)],
     ["construct", "elite"]),
    ("Castle", 3, "HauntedCastles/Spectre", (150, 200, 230),
     [(FANG, 4), ("Ingredient_Bar_Silver", 3), ("Ingredient_Fabric_Scrap_Linen", 3), ("Ingredient_Rune_Shard", 3)],
     ["undead", "elite"]),
]
DISPLAY_NAMES = {"Farm": "Contrat : la Bête de la ferme", "Pumpkin": "Contrat : le Champ maudit",
                 "Garrison": "Contrat : la Garnison du Capitaine", "Crypt": "Contrat : le Gardien de la crypte",
                 "Castle": "Contrat : le Spectre du château"}
# Tags d'identité de la cible seulement : rien sur sa façon de se battre (les joueurs la découvrent).
TAG_COLORS = {"undead": "#9b59b6", "elite": "#c0392b", "plant": "#ff7518", "construct": "#5a8fd8"}


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

# Île = union de disques (lobes) de rayon R : le sol descend entre R - EDGE et R, puis la falaise.
# Deux lobes voisins sont à au plus NECK_MAX(R) l'un de l'autre : le col entre eux reste sur le plat
# (milieu à moins de R - 25 blocs des deux centres, là où le bord dentelé ne mord pas encore).
EDGE = 18.0
VARIANTS = 4
# Distance à vol d'oiseau entre la crypte et la cible, et angle minimal avec le nord (la porte de la
# crypte) : la cible n'est jamais droit devant.
TARGET_DISTANCE = (115.0, 190.0)
TARGET_MIN_ANGLE = 40.0
# Sol plat autour de la cible : le plus grand lieu (la ferme, 49 × 45, la crypte gardée et son caveau
# qui descend à 35 blocs au nord) tient dans 36 blocs ; collines au-delà de 52.
TARGET_FLAT, TARGET_HILLS = 36.0, 52.0
SPAWN_FLAT, SPAWN_HILLS = 16.0, 28.0
TARGET_CLEARANCE, SPAWN_CLEARANCE, LANDMARK_CLEARANCE = 39.0, 18.0, 7.0


def neck_max(r):
    return 2.0 * r - 50.0


# Paysage de chaque contrat : rayon des lobes, nombre de lobes sur le chemin de la cible (sans la
# crypte) et en cul-de-sac, ampleur des collines, seuil du bruit de forêt (plus bas = plus de bois),
# maille des arbres épars, poids du décor (prefabs Decor/ du Comté) aux repères et dans la lande.
THEMES = {
    "Farm": {"radius": 78.0, "path": (2, 2), "side": (1, 2), "hills": 0.7, "forest": 0.35, "trees": 11.0,
             "decor": {"Outcrops": 1.0, "FallenLogs": 2.0, "Shrines": 1.5, "BonePiles": 0.5}},
    "Pumpkin": {"radius": 74.0, "path": (2, 3), "side": (1, 2), "hills": 0.6, "forest": -0.15, "trees": 8.0,
                "decor": {"FallenLogs": 2.0, "MushroomRings": 2.0, "SpiderNests": 0.7, "Shrines": 0.8}},
    "Garrison": {"radius": 84.0, "path": (2, 2), "side": (1, 2), "hills": 1.4, "forest": 0.3, "trees": 12.0,
                 "decor": {"Outcrops": 3.0, "BonePiles": 1.0, "Graves": 0.8, "Shrines": 0.6}},
    "Crypt": {"radius": 76.0, "path": (2, 3), "side": (1, 2), "hills": 0.9, "forest": 0.1, "trees": 9.0,
              "decor": {"Graves": 3.0, "BonePiles": 1.5, "Shrines": 1.0, "MushroomRings": 0.5}},
    "Castle": {"radius": 88.0, "path": (3, 3), "side": (1, 2), "hills": 1.5, "forest": 0.15, "trees": 10.0,
               "decor": {"Shrines": 2.0, "Graves": 1.5, "Outcrops": 1.5, "SpiderNests": 0.5}},
}


def variant_bands():
    """VARIANTS + 1 seuils à peu près équiprobables pour le bruit de wg.layout_value()."""
    from statistics import NormalDist
    inner = [NormalDist(0.0, wg.LAYOUT_NOISE_SPREAD).inv_cdf(k / VARIANTS) for k in range(1, VARIANTS)]
    return [-1.0e9] + [round(v, 3) for v in inner] + [1.0e9]


VARIANT_BANDS = variant_bands()


def island_layouts(short):
    """VARIANTS formes d'île, tirées une fois pour toutes : (lobes [(x, z)], indice du lobe cible).
    Le lobe 0 est la crypte (0, 0) ; un chemin de lobes mène à la cible, des culs-de-sac partent
    d'ailleurs. Deux lobes non voisins restent à plus de 0,9 R (sinon ils se fondent en un seul)."""
    import math
    import random
    theme = THEMES[short]
    r = theme["radius"]
    rng = random.Random(f"Contract{short}")
    out = []
    while len(out) < VARIANTS:
        lobes = [(0.0, 0.0)]
        heading = rng.uniform(0.0, 360.0)
        ok = True
        for _ in range(rng.randint(*theme["path"])):
            for _ in range(40):
                h = heading + rng.uniform(-65.0, 65.0)
                d = rng.uniform(0.95 * r, neck_max(r))
                x, z = lobes[-1][0] + d * math.sin(math.radians(h)), lobes[-1][1] - d * math.cos(math.radians(h))
                if all(math.dist((x, z), p) > 0.9 * r for p in lobes[:-1]):
                    lobes.append((x, z))
                    heading = h
                    break
            else:
                ok = False
        target = len(lobes) - 1
        tx, tz = lobes[target]
        dist = math.hypot(tx, tz)
        # Angle avec le nord (-Z), en degrés, 0 à 180.
        angle = abs((math.degrees(math.atan2(tx, -tz)) + 180.0) % 360.0 - 180.0)
        if not ok or not TARGET_DISTANCE[0] <= dist <= TARGET_DISTANCE[1] or angle < TARGET_MIN_ANGLE:
            continue
        for _ in range(rng.randint(*theme["side"])):
            for _ in range(40):
                parent = lobes[rng.randrange(target)]   # jamais depuis la cible : elle reste au bout
                h = rng.uniform(0.0, 360.0)
                d = rng.uniform(0.95 * r, neck_max(r))
                x, z = parent[0] + d * math.sin(math.radians(h)), parent[1] - d * math.cos(math.radians(h))
                if all(math.dist((x, z), p) > 0.9 * r for p in lobes if p != parent):
                    lobes.append((x, z))
                    break
        layout = ([(round(x), round(z)) for x, z in lobes], target)
        if layout not in out:
            out.append(layout)
    return out


def per_variant(short, points_of):
    """Positions choisies selon la variante du monde : `points_of(lobes, target)` pour chaque variante,
    gardées seulement dans sa bande du bruit de répartition, mémorisées par sections."""
    variants = []
    for k, (lobes, target) in enumerate(island_layouts(short)):
        points = [(x, GROUND_Y, z) for x, z in points_of(lobes, target)]
        if points:
            variants.append(wg.within(wg.layout_value(), VARIANT_BANDS[k], VARIANT_BANDS[k + 1],
                                      wg.list_positions(*points)))
    return wg.cached_positions({"Type": "Union", "Positions": variants})


def landmarks(lobes, target):
    """Repères à explorer : le centre de chaque lobe hors crypte et cible."""
    return [p for n, p in enumerate(lobes) if n not in (0, target)]


def biome(short, folder):
    i = ids(short)
    theme = THEMES[short]
    r = theme["radius"]
    edge_start = r - EDGE
    lobes = per_variant(short, lambda lobes, target: lobes)
    target_pos = per_variant(short, lambda lobes, target: [lobes[target]])
    marks = per_variant(short, landmarks)

    def to_lobes(points):
        """Courbe de la distance au centre du lobe le plus proche."""
        return wg.distance_to(lobes, r + 2.0, wg.curve(*points))

    relief = {"Type": "Min", "Inputs": [
        wg.distance_to(target_pos, TARGET_HILLS + 2.0, wg.curve((0, 0), (TARGET_FLAT, 0), (TARGET_HILLS, 1))),
        wg.distance_to(wg.list_positions(SPAWN), SPAWN_HILLS + 2.0, wg.curve((0, 0), (SPAWN_FLAT, 0), (SPAWN_HILLS, 1))),
    ]}
    hills = wg.add(wg.mul(wg.simplex2d(70.0, 2, "Hills"), wg.const(theme["hills"])),
                   wg.mul(wg.simplex2d(18.0, 2, "Bumps"), wg.const(0.3)))
    top = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(-0.125)),
        wg.column(wg.add(
            wg.const((GROUND_Y - 0.5) / 8.0),
            wg.mul(hills, relief),
            to_lobes([(0, 0), (edge_start, 0), (r, -1.0), (r + 2.0, -1.0)]),
        )),
    )
    # Dessous : un cône sous chaque lobe, au-delà du rayon le fond passe très haut (vide).
    bottom_depth = [(0, 50), (0.5, 42), (0.8, 30), (0.95, 20), (1.0, 14)]
    bottom_curve = [(f * r, d / 8.0 - GROUND_Y / 8.0) for f, d in bottom_depth]
    bottom_curve.append((r + 1.0, -(GROUND_Y + 200) / 8.0))
    rim = wg.mul(wg.simplex2d(30.0, 2, "Rim"), to_lobes([(0, 0), (r - 24.0, 0), (r - 4.0, 1.6), (r + 2.0, 1.6)]))
    bottom = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(0.125)),
        wg.column(wg.add(to_lobes(bottom_curve), wg.mul(wg.simplex2d(16.0, 2, "Underside"), wg.const(0.7)), rim)),
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
    target = wg.runtime(0, "Prop", target_pos, {"Type": "Constant", "Prop": big(folder, "Target")})
    crypt = wg.runtime(0, "Prop", wg.list_positions(SPAWN), {"Type": "Constant", "Prop": big("SpawnCrypt", "SpawnCrypt")})
    small = lambda path, seed: wg.surface_locator(wg.prefab(path, seed), wg.GRASS_FLOOR, 20)
    decor_entries = [(small(f"Decor/{name}", f"Contract{name}"), w) for name, w in theme["decor"].items()]
    mark_props = wg.runtime(0, "Prop", marks, wg.weighted_assignments("LandmarkPick", 0.0, decor_entries))

    def keep_out(positions, extra=0.0):
        """Rien sur le lieu de la cible, la crypte, les repères ni le bord de l'île."""
        for points, clearance in ((target_pos, TARGET_CLEARANCE), (wg.list_positions(SPAWN), SPAWN_CLEARANCE),
                                  (marks, LANDMARK_CLEARANCE)):
            clearance += extra
            field = wg.distance_to(points, clearance + 1.0, wg.curve((0, 0), (clearance + 1.0, clearance + 1.0)))
            positions = wg.within(field, clearance, 1.0e9, positions)
        return wg.within(to_lobes([(0, 0), (r + 2.0, r + 2.0)]), 0.0, edge_start, positions)

    tree = lambda path, n: wg.surface_locator(wg.prefab(path, f"ContractTree{n}", vanilla=True), wg.GRASS_FLOOR, 20)
    forest = wg.simplex2d(80.0, 2, "Forest")
    woods = wg.runtime(1, "Chunk", keep_out(wg.within(forest, theme["forest"], 1.0e9, wg.mesh(6.5, 0.45, "Woods"))),
                       wg.weighted_assignments("WoodsPick", 0.15, [
                           (tree(p, n), w) for n, (p, w) in enumerate(wg.FOREST_TREES)]))
    trees = wg.runtime(1, "Chunk", keep_out(wg.within(forest, -1.0e9, theme["forest"], wg.mesh(theme["trees"], 0.45, "Trees"))),
                       wg.weighted_assignments("TreePick", 0.3, [
                           (tree(p, 100 + n), w) for n, (p, w) in enumerate(wg.LONE_TREES)]))
    decor = wg.runtime(1, "Chunk", keep_out(wg.mesh(30.0, 0.45, "Decor"), 4.0),
                       wg.weighted_assignments("DecorPick", 0.5, decor_entries))

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
        "Props": [target, crypt, mark_props, woods, trees, decor, plants],
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


def island_sheet(cell=200, scale=0.42):
    """Aperçu vu de dessus : une ligne par contrat, une colonne par variante. Gris : lobes (bord en
    pente plus clair), rouge : la crypte et sa porte (nord en haut), or : la cible, blanc : repères."""
    rows = list(THEMES)
    sheet = Image.new("RGB", (cell * VARIANTS + 90, cell * len(rows)), (24, 24, 30))
    d = ImageDraw.Draw(sheet)
    for row, short in enumerate(rows):
        r = THEMES[short]["radius"] * scale
        d.text((6, row * cell + cell // 2), short, fill=(230, 230, 230))
        for col, (lobes, target) in enumerate(island_layouts(short)):
            ox, oz = 90 + col * cell + cell / 2, row * cell + cell / 2
            xs, zs = [x for x, _ in lobes], [z for _, z in lobes]
            # Centrer l'île dans sa case (la crypte n'est pas au milieu).
            cx, cz = (min(xs) + max(xs)) / 2 * scale, (min(zs) + max(zs)) / 2 * scale
            pt = lambda x, z: (ox + x * scale - cx, oz + z * scale - cz)
            for x, z in lobes:
                px, pz = pt(x, z)
                d.ellipse((px - r, pz - r, px + r, pz + r), fill=(92, 84, 70))
            for x, z in lobes:
                px, pz = pt(x, z)
                e = r - EDGE * scale
                d.ellipse((px - e, pz - e, px + e, pz + e), fill=(64, 72, 48))
            for x, z in landmarks(lobes, target):
                px, pz = pt(x, z)
                d.rectangle((px - 2, pz - 2, px + 2, pz + 2), fill=(240, 240, 240))
            px, pz = pt(*lobes[target])
            t = TARGET_FLAT * scale
            d.ellipse((px - t, pz - t, px + t, pz + t), outline=(230, 180, 40), width=2)
            px, pz = pt(0, 0)
            d.rectangle((px - 3, pz - 4, px + 3, pz + 4), fill=(200, 40, 40))
            d.line((px, pz - 4, px, pz - 12), fill=(200, 40, 40), width=2)
    return sheet


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
        island_sheet().save(preview / "iles_contrats.png")


if __name__ == "__main__":
    main()
