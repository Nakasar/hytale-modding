#!/usr/bin/env python3
"""Génère la Tour de l'Alchimiste, premier donjon du mod : clé, portail, instance, règles, îles et prefabs.

    python3 mods/nakasar-vampires/tools/generate_alchemist_tower.py [--preview DOSSIER]

Document de conception : https://claude.ai/code/artifact/38f49cae-a653-428c-86dc-4e1cdf0da191 (le donjon s'inspire
du donjon vanilla Deepworks).

- la clé `PortalKey_Nakasar_Alchemist_Tower`, même recette à l'établi des chasseurs et à l'autel (palier 3) ;
- le type de portail et l'instance : pas de limite de temps ni d'entrées, ciel violet et vert figé au crépuscule ;
- les règles (GameplayConfig, comme Deepworks) : ni pose ni casse de blocs, aucune perte d'objets à la mort ;
- les îles flottantes au-dessus du vide : l'île d'arrivée, au nord l'île de la tour et son jardin d'arbres
  fantastiques, et des îlots à toutes hauteurs, chacun avec un arbre fantastique du jeu, des cristaux et des émanations
  magiques (blocs invisibles `Nakasar_Tower_Emanation_*` qui portent des particules du jeu et une lumière) ;
- le parvis d'arrivée (point d'apparition, portail de sortie anticipée) et le pont, fermés par des parapets de 2 blocs ;
- la tour elle-même (tools/alchemist_tower.py) : étages, balcons, escaliers extérieurs, points de vue fermés, points de
  contrôle ; TowerLayout.java (Java, généré) en reprend les positions. Un joueur qui tombe quand même dans le vide est
  ramené à son dernier point de contrôle (TowerFallSystem, TowerCheckpointSystem).

Repère : x vers l'est, z vers le sud, y vers le haut ; le point d'apparition est en (0, GROUND_Y, 0).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import alchemist_tower
import generate_prefabs as pf
import generate_worldgen as wg

PACK = wg.PACK
SERVER = PACK / "Server"
COMMON = PACK / "Common"
LANG = "nakasar_alchemist"
TOWER = "Nakasar_Alchemist_Tower"
KEY = "PortalKey_Nakasar_Alchemist_Tower"
EXIT = "Nakasar_Tower_Exit"
EXIT_PARTICLES = "Nakasar_Tower_Exit_Portal"
EMANATION_PREFIX = "Nakasar_Tower_Emanation_"
JAVA_LAYOUT = PACK.parent / "java/dev/nakasar/hytale/vampires/tower/TowerLayout.java"
PREFABS = "Nakasar/AlchemistTower"
ICON = "Icons/Items/Nakasar/Tower/PortalKey_Alchemist_Tower.png"
WEATHER = "Nakasar_Weather_Alchemist_Tower"
ENVIRONMENT = "Nakasar_Env_Alchemist_Tower"

# Clé : même recette dans les deux ateliers (décision de Kevin, 19 octobre 2026). Les essences sont celles du jeu ;
# l'essence de vie tient lieu d'essence de racine.
KEY_INPUTS = [("Ingredient_Rune_Shard", 4), ("Ingredient_Void_Essence", 2), ("Ingredient_Fire_Essence", 1),
              ("Ingredient_Ice_Essence", 1), ("Ingredient_Lightning_Essence", 1), ("Ingredient_Life_Essence", 1)]
KEY_BENCHES = [("Nakasar_Hunter_Workbench", "Nakasar_Hunter_Fragments", 3),
               ("Nakasar_Sacrificial_Altar", "Nakasar_Altar_Rituals", 3)]

# Première couche d'air au-dessus du sol des îles : aligné avec TowerFallSystem.GROUND_Y.
GROUND_Y = 100
SPAWN = (0, GROUND_Y, 0)
# Île d'arrivée : rayon, rayon du plat. Île de la tour, au nord : centre, rayon, rayon du plat.
ARRIVAL_RADIUS, ARRIVAL_FLAT = 22.0, 15.0
TOWER_CENTER = (0, GROUND_Y, -100)
TOWER_RADIUS, TOWER_FLAT = 48.0, 40.0
# Parvis d'arrivée (rayon intérieur du parapet), pont (demi-largeur, de z à z) : le pont s'arrête au bord du parvis de
# la tour (z = 40 dans le repère du prefab de la tour, alchemist_tower.court).
PLAZA_RADIUS = 9
BRIDGE_HALF = 2
BRIDGE_START, BRIDGE_END = -10, TOWER_CENTER[2] + 41
EXIT_Z = 6                         # portail de sortie anticipée, au sud du point d'apparition
TOWER_SEED = 4242
# Îlots flottants autour de la tour, chacun portant un arbre fantastique du jeu (dossiers de Server/Prefabs d'Assets.zip,
# lus le 2026-10-19 ; demi-largeur et hauteur en commentaire) : (centre du dessus, rayon, arbre).
ISLETS = [
    ((-78, 112, -66), 11, "Trees/Wisteria/Stage_2"),         # ±11
    ((74, 124, -58), 10, "Trees/Spiral/Stage_3"),            # ±10, 17 de haut
    ((-68, 138, -152), 14, "Trees/Jungle_Crystal/Stage_3"),  # ±22, 50 de haut
    ((72, 154, -144), 12, "Trees/Azure/Stage_3"),            # ±8, 27 de haut
    ((0, 166, -186), 13, "Trees/Fig_Blue/Stage_3"),          # ±14, 45 de haut : derrière la tour, vu de l'Observatoire
    ((-98, 96, -112), 9, "Trees/Crystal/Stage_3"),
    ((100, 142, -100), 10, "Trees/Zone5/Aqua/Large"),        # ±22
    ((44, 92, 36), 8, "Trees/Silver/Stage_3"),               # au sud-est de l'île d'arrivée
]
# Jardin de l'île de la tour : arbres plus sages, assez loin pour ne pas toucher balcons ni cheminées (rayon 25 au plus).
GARDEN_RADIUS = 40
GARDEN = [(150, "Trees/Willow/Stage_3"), (200, "Trees/Crystal/Stage_3"), (250, "Trees/Silver/Stage_3"),
          (300, "Trees/Wisteria/Stage_2"), (345, "Trees/Crystal/Stage_3"), (30, "Trees/Willow/Stage_3")]
# Émanations magiques : blocs invisibles et traversables qui portent des particules du jeu et une lumière. La teinte
# « Color » d'une particule de bloc ne change pas les systèmes (vu avec la brèche) : on choisit des systèmes déjà colorés.
EMANATIONS = {
    "Smoke": ("Eye_Void_Smoke_Green", 1.2, 0.5, "#4f8"),
    "Motes": ("Dungeon_Goblin_Temple_Motes", 1.0, 0.5, "#a6f"),
    "Spiral": ("ForgottenTemple_Spark_Spiral", 1.0, 0.5, "#6ef"),
    "Arc": ("Goblin_Decorative_Lightning", 1.5, 1.0, "#9cf"),
    "Mist": ("Eye_Void_Smoke_Teal", 1.5, 0.5, "#4dc"),
    "Fireflies": ("Fireflies_GS", 1.0, 0.5, "#cf8"),
}
EMANATION_COLORS = {"Smoke": (90, 240, 140), "Motes": (180, 110, 255), "Spiral": (110, 230, 255),
                    "Arc": (160, 200, 255), "Mist": (70, 220, 200), "Fireflies": (210, 255, 120)}

# Pierres de la tour : marbre clair, liserés d'or, cristaux violets et verts (les couleurs de l'Alchimiste).
FLOOR = [("Rock_Marble_Brick", 5), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
PARAPET = "Rock_Marble_Brick"
PARAPET_TOP = "Rock_Marble_Brick_Wall"
TRIM = "Rock_Gold_Brick_Decorative"
CRYSTALS = [(c, 1) for c in ("Rock_Crystal_Purple_Large", "Rock_Crystal_Purple_Medium", "Rock_Crystal_Green_Medium",
                              "Rock_Crystal_Green_Large", "Rock_Crystal_Pink_Medium")]


# --- clé, portail, instance, règles -----------------------------------------------------------

def key_item():
    return {
        "Parent": "PortalKey_Taiga",
        "TranslationProperties": {"Name": f"{LANG}.items.{KEY}.name", "Description": f"{LANG}.items.{KEY}.description"},
        "Icon": ICON,
        "Quality": "Epic",
        "Recipe": {
            "TimeSeconds": 4,
            "KnowledgeRequired": False,
            "Input": [{"ItemId": k, "Quantity": q} for k, q in KEY_INPUTS],
            # Une recette, deux ateliers : le serveur l'ajoute à chaque établi cité (CraftingPlugin).
            "BenchRequirement": [{"Type": "Crafting", "Id": bench, "Categories": [tab], "RequiredTierLevel": tier}
                                 for bench, tab, tier in KEY_BENCHES],
        },
        # -1 : pas de limite de temps (comme Deepworks) ; écrit ici pour ne rien hériter de la clé parente.
        "PortalKey": {"PortalType": TOWER, "TimeLimitSeconds": -1},
    }


def portal_type():
    return {
        "InstanceId": TOWER,
        "GameplayConfig": TOWER,
        "Description": {
            "DisplayName": f"{LANG}.portal.name",
            "FlavorText": f"{LANG}.portal.flavor",
            "ThemeColor": "#8e44ad",
            "DescriptionTags": [
                {"TranslationKey": f"{LANG}.portal.tag.dungeon", "Color": "#c0392b"},
                {"TranslationKey": f"{LANG}.portal.tag.elemental", "Color": "#27ae60"},
                {"TranslationKey": f"{LANG}.portal.tag.group", "Color": "#2980b9"},
            ],
            "Objectives": [f"{LANG}.portal.objective.climb", f"{LANG}.portal.objective.alchemist"],
        },
        "Spawn": {
            "SpawnReturnPortal": False,
            "SpawnProviderOverride": {"Id": "Global", "SpawnPoint": {"X": 0.5, "Y": float(GROUND_Y), "Z": 0.5, "Yaw": 0.0}},
        },
        "TimeLimitSeconds": -1,
        "AllowedEntryCount": 0,            # 0 = entrées illimitées, comme The_Deepworks
        "CloseWhenEmpty": True,
        "VoidInvasionEnabled": False,
        "AllowPlayersToLeaveViaMap": True,
    }


def instance():
    return {
        "DisplayName": "Tour de l'Alchimiste",
        "WorldGen": {"Type": "HytaleGenerator", "WorldStructure": TOWER},
        "ForcedWeather": WEATHER,
        "GameTime": "0001-01-01T19:00:00Z",
        "IsGameTimePaused": True,
        "GameplayConfig": TOWER,
        "IsPvpEnabled": False,
        "IsSpawningNPC": True,
        "SpawnProvider": {"Id": "Global", "SpawnPoint": {"X": 0.5, "Y": float(GROUND_Y), "Z": 0.5,
                                                         "Pitch": 0, "Yaw": 0, "Roll": 0}},
    }


def gameplay_config():
    """Règles de Deepworks (GameplayConfigs/TheDeepworks.json, 0.7.2)."""
    return {
        "Parent": "Default",
        "World": {
            "AllowBlockGathering": False,
            "AllowBlockPlacement": False,
            "AllowBlockBreaking": False,
            "BlockedRootInteractionTags": ["Type=Rail_Kart", "Type=Bed"],
        },
        "Plugin": {"Portal": {}, "WorldEvents": {}},
        "Death": {"ItemsLossMode": "None", "ItemsAmountLossPercentage": 0, "ItemsDurabilityLossPercentage": 0},
    }


# Anneaux de fumée horizontaux du portail vanilla : centrés à mi-hauteur de l'ovale, ils flottent.
# On les descend au ras du socle (2,5 blocs au-dessus du bloc, socle haut de 0,5).
RING_SPAWNERS = {"MagicPortal_VoidSmokeMiddle", "MagicPortal_VoidGlowSmoke"}
RING_DROP = -2.0


def exit_particles():
    """Copie de MagicPortal_VoidKeyArt (vanilla 0.7.2) avec les anneaux de fumée posés au sol."""
    spawners = [
        {"SpawnerId": "MagicPortal_VoidSpawn"},
        {"SpawnerId": "MagicPortal_VoidFlash"},
        {"SpawnerId": "MagicPortal_VoidCenterCircle"},
        {"SpawnerId": "MagicPortal_VoidSmokeAlpha", "StartDelay": 0, "PositionOffset": {"Y": 0.2}},
        {"SpawnerId": "MagicPortal_VoidSparks"},
        {"SpawnerId": "MagicPortal_VoidSparksDark"},
        {"SpawnerId": "MagicPortal_Center", "StartDelay": 0.5},
        {"SpawnerId": "MagicPortal_VoidCenterGlow", "StartDelay": 0.5},
        {"SpawnerId": "MagicPortal_VoidSmokeMiddle", "RotationOffset": {"Pitch": 90.0}},
        {"SpawnerId": "MagicPortal_VoidGlowSmoke", "RotationOffset": {"Pitch": 90.0}},
        {"SpawnerId": "MagicPortal_VoidGlowCenterIntense"},
        {"SpawnerId": "MagicPortal_VoidOuterCircle", "RotationOffset": {"Pitch": 90.0}},
        {"SpawnerId": "MagicPortal_VoidTentacles", "PositionOffset": {"Z": 0.4}},
    ]
    for sp in spawners:
        if sp["SpawnerId"] in RING_SPAWNERS:
            sp["PositionOffset"] = {"Y": RING_DROP}
    return {
        "$Comment": "Copie de MagicPortal_VoidKeyArt, anneaux au sol. Générée par tools/generate_alchemist_tower.py.",
        "Spawners": spawners,
        "CullDistance": 50.0,
        "IsImportant": True,
    }


def exit_item():
    """Portail de sortie anticipée : celui de Deepworks (Dungeon_Portal_Early_Exit), avec nos textes."""
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{EXIT}.name", "Description": f"{LANG}.items.{EXIT}.description"},
        "Icon": "Icons/ItemsGenerated/Portal_Return.png",
        "Categories": ["Blocks.Portals"],
        "BlockType": {
            "AmbientSoundEventId": "SFX_Portal_Neutral",
            "DrawType": "Model",
            "Material": "Solid",
            "Opacity": "Transparent",
            "CustomModel": "Blocks/Miscellaneous/Platform_Magic_Exit.blockymodel",
            "CustomModelTexture": [{"Texture": "Blocks/Miscellaneous/Platform_Magic_Blue2.png", "Weight": 1}],
            "HitboxType": "Dungeon_Portal",
            "BlockParticleSetId": "Stone",
            "BlockSoundSetId": "Stone",
            "PhysicalMaterialId": "Stone",
            "VariantRotation": "NESW",
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "Particles": [{"SystemId": EXIT_PARTICLES, "PositionOffset": {"Y": 2.5}}],
            "TextureComputedColor": "#736940",
            "Interactions": {"Use": {"Interactions": [{
                "Type": "OpenCustomUI",
                "Page": {
                    "Id": "Confirmation",
                    "TitleKey": f"{LANG}.exit.title",
                    "MessageKey": f"{LANG}.exit.message",
                    "ConfirmKey": f"{LANG}.exit.leave",
                    "CancelKey": f"{LANG}.exit.stay",
                    "Success": {"Interactions": ["Portal_Return"]},
                },
            }]}},
        },
        "PlayerAnimationsId": "Block",
        "Tags": {"Type": ["Portal"]},
        "Quality": "Technical",
        "IconProperties": {"Scale": 0.35, "Rotation": [22.5, 45.0, 22.5], "Translation": [0.0, -13.5]},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    }


# --- ciel et environnement --------------------------------------------------------------------

def weather():
    """Crépuscule magique figé (19 h, GameTime en pause) : zénith violet profond, horizon vert d'émeraude, brume
    lointaine pour garder les panoramas. Les autres heures suivent, au cas où l'heure bougerait."""
    def keys(*pairs):
        return [{"Hour": h, "Color": c} for h, c in pairs]
    return {
        "FogDistance": [-20, 260],
        "FogColors": keys((0, "#1a1030"), (12, "#4a5a70"), (19, "#3b2a5a"), (22, "#1c1236")),
        "FogDensities": [{"Hour": 0, "Value": 0.45}, {"Hour": 19, "Value": 0.3}],
        "SkyTopColors": keys((0, "#0a0620ff"), (12, "#3a3a7aff"), (19, "#2a0f4aff"), (22, "#120830ff")),
        "SkyBottomColors": keys((0, "#123a2aff"), (12, "#6ab08aff"), (19, "#2fa36aff"), (22, "#174a3aff")),
        "SkySunsetColors": keys((0, "#00000000"), (19, "#b04ad8a0"), (22, "#00000000")),
        "SunlightColors": keys((0, "#4a3a8a"), (12, "#c0c8d0"), (19, "#a07ac8"), (22, "#5a4a9a")),
        "SunColors": keys((0, "#ffffff"), (19, "#e070ff")),
        "MoonColors": keys((0, "#d8ffe8ff"), (12, "#d8ffe8ff")),
        "MoonGlowColors": keys((0, "#3cff9a60"), (12, "#3cff9a60")),
        "WaterTints": keys((0, "#2a1a4a"), (12, "#3a6a5a")),
    }


def environment():
    """Pas d'apparitions de monde : les mobs de la tour viendront de marqueurs posés par ses prefabs."""
    return {
        "Parent": "Env_Zone1_Plains",
        "SpawnDensity": 0.0,
        "BlockModificationAllowed": False,
        "WaterTint": "#3a6a5a",
        "WeatherForecastSeed": ENVIRONMENT,
        "WeatherForecasts": {str(h): [{"WeatherId": WEATHER, "Weight": 1}] for h in range(24)},
    }


# --- îles -------------------------------------------------------------------------------------

def island(center, radius, flat, seed):
    """Île flottante centrée sur `center` (y = première couche d'air du dessus) : dessus plat jusqu'à `flat`, puis bord
    qui s'abaisse de 6 blocs ; dessous en cône rocheux dentelé. Densité positive dans l'île, négative ailleurs."""
    here = wg.list_positions(center)
    top_y = center[1]
    top = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(-0.125)),
        wg.column(wg.add(
            wg.const((top_y - 0.5) / 8.0),
            wg.distance_to(here, radius + 2.0, wg.curve((0, 0), (flat, 0), (radius, -0.75))),
        )),
    )
    depth = [(0, 0.85 * radius + 6), (0.5, 0.7 * radius + 4), (0.8, 0.45 * radius + 3), (0.95, 8), (1.0, 4)]
    bottom_curve = [(f * radius, d / 8.0 - top_y / 8.0) for f, d in depth]
    bottom_curve.append((radius + 1.0, -(top_y + 200) / 8.0))
    rim = wg.mul(wg.simplex2d(14.0, 2, f"{seed}Rim"),
                 wg.distance_to(here, radius + 2.0, wg.curve((0, 0), (max(radius - 10.0, 1.0), 0), (radius - 2.0, 1.2))))
    bottom = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(0.125)),
        wg.column(wg.add(wg.distance_to(here, radius + 2.0, wg.curve(*bottom_curve)),
                         wg.mul(wg.simplex2d(9.0, 2, f"{seed}Underside"), wg.const(0.6)), rim)),
    )
    return {"Type": "Min", "Inputs": [top, bottom]}


def prefab_prop(name):
    return {"Type": "Prefab", "WeightedPrefabPaths": [{"Path": f"{PREFABS}/{name}", "Weight": 1.0}]}


def block_prop(name, x=0, y=0, z=0):
    return {"Type": "Manual", "Blocks": [{"Position": {"X": x, "Y": y, "Z": z}, "Material": {"Solid": name}}]}


def crystal_cluster(i):
    """Trois cristaux serrés, en pointe vers le haut."""
    names = [c for c, _ in CRYSTALS]
    return {"Type": "Manual", "Blocks": [
        {"Position": {"X": dx, "Y": 0, "Z": dz}, "Material": {"Solid": names[(i + k) % len(names)]}}
        for k, (dx, dz) in enumerate(((0, 0), (1, 0), (0, 1)))]}


def biome():
    materials = {
        "Type": "Solidity",
        "Solid": {"Type": "Queue", "Queue": [
            {"Type": "SpaceAndDepth", "LayerContext": "DepthIntoFloor", "MaxExpectedDepth": 5, "Layers": [
                {"Type": "ConstantThickness", "Thickness": 1, "Material": wg.field_material(
                    wg.simplex2d(13.0, 2, "TowerPatches"),
                    (-10.0, -0.45, wg.material("Soil_Grass_Deep")),
                    (-0.45, 0.55, wg.weighted_material("TowerSurface", ("Soil_Grass_Full", 6), ("Soil_Grass", 2))),
                    (0.55, 10.0, wg.material("Plant_Moss_Block_Green_Dark")),
                )},
                {"Type": "ConstantThickness", "Thickness": 4, "Material": wg.weighted_material(
                    "TowerSubsoil", ("Soil_Dirt", 3), ("Rock_Stone_Mossy", 1))},
            ]},
            wg.weighted_material("TowerBedrock", ("Rock_Stone", 5), ("Rock_Marble", 2), ("Rock_Slate", 1),
                                 ("Rock_Crystal_Purple_Block", 0.05), ("Rock_Crystal_Green_Block", 0.05)),
        ]},
        "Empty": {"Type": "Constant", "Material": wg.AIR},
    }
    arrival = wg.runtime(0, "Prop", wg.list_positions(SPAWN), {"Type": "Constant", "Prop": wg.surface_locator(
        prefab_prop("Arrival"), wg.SOLID_FLOOR, 12)})
    tower = wg.runtime(0, "Prop", wg.list_positions(TOWER_CENTER), {"Type": "Constant", "Prop": wg.surface_locator(
        prefab_prop("Tower"), wg.SOLID_FLOOR, 12)})

    def plant(name):
        return wg.surface_locator(block_prop(name), wg.on_floor(
            {"Type": "Or", "Patterns": [wg.is_block(b) for b in ("Soil_Grass_Full", "Soil_Grass", "Soil_Grass_Deep")]}), 45)

    # Points de semis à mi-hauteur des îles : chacun cherche le premier gazon de sa colonne, de y = 180 à y = 90.
    plant_points = wg.mesh(2.5, 0.5, "TowerPlants")
    plant_points["PointsY"] = 135
    plants = wg.runtime(1, "Chunk", plant_points, wg.weighted_assignments("TowerPlantPick", 0.45, [
        (plant("Plant_Grass_Lush_Short"), 5.0), (plant("Plant_Grass_Lush"), 3.0), (plant("Plant_Flower_Common_Violet"), 0.6),
        (plant("Plant_Flower_Common_Lime"), 0.5), (plant("Plant_Flower_Orchid_Purple"), 0.3),
        (plant("Plant_Flower_Tall_Cyan"), 0.3), (plant("Plant_Moss_Short_Green"), 1.0),
    ]))
    # Arbres fantastiques : un par îlot, et le jardin autour de la tour. Puis les cristaux et émanations des îlots.
    trees = []
    for i, (center, radius, tree) in enumerate(ISLETS):
        trees.append(wg.runtime(2, "Prop", wg.list_positions(center), {"Type": "Constant", "Prop": wg.surface_locator(
            wg.prefab(tree, f"TowerIslet{i}", vanilla=True), wg.SOLID_FLOOR, 6)}))
    for i, (a, tree) in enumerate(GARDEN):
        x = TOWER_CENTER[0] + round(GARDEN_RADIUS * math.cos(math.radians(a)))
        z = TOWER_CENTER[2] + round(GARDEN_RADIUS * math.sin(math.radians(a)))
        trees.append(wg.runtime(2, "Prop", wg.list_positions((x, GROUND_Y, z)), {"Type": "Constant",
            "Prop": wg.surface_locator(wg.prefab(tree, f"TowerGarden{i}", vanilla=True), wg.SOLID_FLOOR, 8)}))
    islet_decor = []
    kinds = ["Motes", "Fireflies", "Mist", "Spiral"]
    for i, (center, radius, _) in enumerate(ISLETS):
        cx, cy, cz = center
        for k in range(3):
            a = 70 + 120 * k + 37 * i
            d = 0.55 * radius
            pos = (cx + round(d * math.cos(math.radians(a))), cy, cz + round(d * math.sin(math.radians(a))))
            prop = block_prop(f"{EMANATION_PREFIX}{kinds[(i + k) % len(kinds)]}") if k < 2 else crystal_cluster(i)
            islet_decor.append(wg.runtime(3, "Prop", wg.list_positions(pos), {"Type": "Constant",
                                                                             "Prop": wg.surface_locator(prop, wg.SOLID_FLOOR, 6)}))
    return {
        "Name": TOWER,
        "Terrain": {"Type": "DAOTerrain", "Density": {"Type": "Max", "Inputs": [
            island(SPAWN, ARRIVAL_RADIUS, ARRIVAL_FLAT, "Arrival"),
            island(TOWER_CENTER, TOWER_RADIUS, TOWER_FLAT, "Tower"),
        ] + [island(center, radius, 0.6 * radius, f"Islet{i}") for i, (center, radius, _) in enumerate(ISLETS)]}},
        "MaterialProvider": materials,
        "Props": [arrival, tower, plants] + trees + islet_decor,
        "EnvironmentProvider": {"Type": "Constant", "Environment": ENVIRONMENT},
        "TintProvider": {"Type": "Constant", "Color": "#4f9a6a"},
    }


def world_structure():
    return {
        "Type": "NoiseRange",
        "DefaultBiome": TOWER,
        "DefaultTransitionDistance": 16,
        "MaxBiomeEdgeDistance": 0,
        "Density": wg.const(0.0),
        "Biomes": [],
        "SpawnPositions": wg.list_positions(SPAWN),
    }


# --- prefab : parvis et pont ------------------------------------------------------------------

def parapet(p, x, z):
    """Garde-corps de 2 blocs (un bloc plein, un muret) : trop haut pour être sauté."""
    p.set(x, 0, z, PARAPET)
    p.set(x, 1, z, PARAPET_TOP)


def arrival_prefab(seed):
    p = pf.Prefab(seed)
    r = p.rng
    p.clear(-12, 0, BRIDGE_END, 12, 14, 12)

    # Parvis rond : dallage de marbre, anneau d'or, parapet tout autour sauf l'entrée du pont au nord.
    ring = set()
    for x in range(-PLAZA_RADIUS - 1, PLAZA_RADIUS + 2):
        for z in range(-PLAZA_RADIUS - 1, PLAZA_RADIUS + 2):
            d = math.hypot(x, z)
            if d < PLAZA_RADIUS + 0.5:
                p.set(x, -1, z, TRIM if 4.5 <= d < 5.3 else p.pick(FLOOR))
                p.fill(x, -4, z, x, -2, z, "Rock_Marble")
            elif d < PLAZA_RADIUS + 1.5:
                p.set(x, -1, z, p.pick(FLOOR))
                if not (z < 0 and abs(x) <= BRIDGE_HALF):
                    ring.add((x, z))
    for x, z in ring:
        parapet(p, x, z)
    # Lanternes sur le parapet aux quatre diagonales, cristaux de part et d'autre du portail de sortie.
    for a in (45, 135, 225, 315):
        x = round((PLAZA_RADIUS + 1) * math.cos(math.radians(a)))
        z = round((PLAZA_RADIUS + 1) * math.sin(math.radians(a)))
        if (x, z) in ring:
            p.set(x, 2, z, "Deco_Lantern")
    for x in (-3, 3):
        p.set(x, 0, EXIT_Z, p.pick(CRYSTALS))
    # Portail de sortie anticipée, au sud, tourné vers le point d'apparition ; 3 × 5 × 3 blocs libres autour.
    p.fill(-1, 0, EXIT_Z - 1, 1, 4, EXIT_Z + 1, pf.AIR)
    p.set(0, 0, EXIT_Z, EXIT, pf.NORTH)

    # Pont au-dessus du vide : tablier de marbre, parapets, lanternes et piles qui pendent sous le tablier.
    for z in range(BRIDGE_END, BRIDGE_START + 1):
        for x in range(-BRIDGE_HALF, BRIDGE_HALF + 1):
            p.set(x, -1, z, TRIM if x == 0 and z % 4 == 0 else p.pick(FLOOR))
            p.set(x, -2, z, "Rock_Marble_Brick")
            p.fill(x, 0, z, x, 4, z, pf.AIR)
        for x in (-BRIDGE_HALF - 1, BRIDGE_HALF + 1):
            p.set(x, -1, z, "Rock_Marble_Brick")
            p.set(x, -2, z, "Rock_Marble_Brick")
            parapet(p, x, z)
            if z % 8 == 0:
                p.set(x, 2, z, "Deco_Lantern")
        if z % 10 == 0:
            for x in range(-BRIDGE_HALF - 1, BRIDGE_HALF + 2):
                depth = 3 if abs(x) <= 1 else 5
                p.fill(x, -2 - depth, z, x, -3, z, "Rock_Marble_Brick_Pillar_Middle")

    # Point d'apparition : 3 × 3 × 3 blocs libres.
    p.fill(-1, 0, -1, 1, 2, 1, pf.AIR)
    return p


# --- émanations magiques ----------------------------------------------------------------------

def emanation_item(kind):
    system, scale, offset, light = EMANATIONS[kind]
    return {
        "$Comment": "Émanation magique de la Tour de l'Alchimiste : bloc invisible et traversable qui porte des particules du jeu et une lumière (cheminées, cristaux flottants, îlots). Généré par tools/generate_alchemist_tower.py.",
        "TranslationProperties": {"Name": f"{LANG}.items.{EMANATION_PREFIX}{kind}.name"},
        "Icon": f"Icons/Items/Nakasar/Tower/Emanation_{kind}.png",
        "Quality": "Developer",
        "Categories": ["Blocks.Deco"],
        "BlockType": {
            # Comme la déchirure de la brèche : le client ne dessine pas les particules d'un bloc DrawType « Empty ».
            "Material": "Empty",
            "DrawType": "Model",
            "CustomModel": "Blocks/_Debug/Model.blockymodel",
            "CustomModelTexture": [{"Texture": "Blocks/_Debug/TextureEmpty.png", "Weight": 1}],
            "Opacity": "Transparent",
            "Support": {},
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "Light": {"Color": light},
            "Particles": [{"SystemId": system, "Scale": scale, "PositionOffset": {"X": 0, "Y": offset, "Z": 0}}],
        },
    }


def emanation_icon(kind):
    """Halo de la couleur de l'émanation, cœur clair."""
    r, g, b = EMANATION_COLORS[kind]
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for k in range(14, 0, -1):
        alpha = int(255 * (1 - k / 15) ** 1.5)
        d.ellipse((32 - 2 * k, 32 - 2 * k, 32 + 2 * k, 32 + 2 * k), fill=(r, g, b, alpha))
    d.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 230))
    return img


# --- Java : positions de la tour ---------------------------------------------------------------

def tower_layout(tower):
    """TowerLayout.java : point d'arrivée et points de contrôle, en coordonnées du monde."""
    ox, oy, oz = TOWER_CENTER
    rows = ",\n".join(f"            new Vector3d({x + ox + 0.5}, {y + oy}, {z + oz + 0.5})" for x, y, z in tower.checkpoints)
    return f"""package dev.nakasar.hytale.vampires.tower;

import org.joml.Vector3d;

/** Positions de la Tour de l'Alchimiste. Généré par tools/generate_alchemist_tower.py : ne pas modifier à la main. */
public final class TowerLayout {{

    /** Première couche d'air au-dessus du sol des îles. */
    public static final double GROUND_Y = {GROUND_Y};
    /** Point d'apparition, sur le parvis d'arrivée. */
    public static final Vector3d ARRIVAL = new Vector3d({SPAWN[0] + 0.5}, {SPAWN[1]}, {SPAWN[2] + 0.5});
    /** Points de contrôle, dans l'ordre du parcours : bibliothèque, laboratoire, Escalier des vents, antichambre. */
    public static final Vector3d[] CHECKPOINTS = {{
{rows}
    }};

    private TowerLayout() {{
    }}
}}
"""


# --- icône ------------------------------------------------------------------------------------

def key_icon():
    """Fiole violette au liquide vert lumineux, devant une tour en ombre."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((40, 10, 52, 56), fill=(52, 30, 80, 255))
    d.polygon(((38, 10), (46, 2), (54, 10)), fill=(70, 40, 110, 255))
    d.rectangle((44, 22, 47, 27), fill=(120, 255, 170, 255))
    d.ellipse((8, 22, 42, 56), fill=(150, 90, 210, 255), outline=(60, 30, 90, 255), width=2)
    d.chord((10, 30, 40, 54), 0, 180, fill=(80, 230, 140, 255))
    d.rectangle((19, 8, 31, 24), fill=(170, 120, 220, 255), outline=(60, 30, 90, 255), width=2)
    d.rectangle((17, 5, 33, 9), fill=(150, 100, 60, 255))
    d.ellipse((15, 32, 21, 38), fill=(220, 255, 230, 200))
    return img


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    write_json(SERVER / "Item/Items/Portal/Nakasar" / f"{KEY}.json", key_item())
    write_json(SERVER / "Item/Items/Portal/Nakasar" / f"{EXIT}.json", exit_item())
    write_json(SERVER / "Particles/Nakasar/Tower" / f"{EXIT_PARTICLES}.particlesystem", exit_particles())
    write_json(SERVER / "PortalTypes" / f"{TOWER}.json", portal_type())
    write_json(SERVER / "Instances" / TOWER / "instance.bson", instance())
    write_json(SERVER / "GameplayConfigs" / f"{TOWER}.json", gameplay_config())
    write_json(SERVER / "Weathers" / f"{WEATHER}.json", weather())
    write_json(SERVER / "Environments" / f"{ENVIRONMENT}.json", environment())
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{TOWER}.json", biome())
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{TOWER}.json", world_structure())
    for kind in EMANATIONS:
        write_json(SERVER / "Item/Items/Deco/Nakasar/Tower" / f"{EMANATION_PREFIX}{kind}.json", emanation_item(kind))
        icon = COMMON / f"Icons/Items/Nakasar/Tower/Emanation_{kind}.png"
        icon.parent.mkdir(parents=True, exist_ok=True)
        emanation_icon(kind).save(icon)
    out = SERVER / "Prefabs" / PREFABS
    count = arrival_prefab(9600).write(out / "Arrival" / "Arrival.prefab.json")
    print(f"Arrival: {count} blocs")
    tower = alchemist_tower.build_checked(TOWER_SEED)
    count = tower.p.write(out / "Tower" / "Tower.prefab.json")
    print(f"Tower: {count} blocs, points de contrôle {tower.checkpoints}")
    JAVA_LAYOUT.write_text(tower_layout(tower), encoding="utf-8")
    (COMMON / ICON).parent.mkdir(parents=True, exist_ok=True)
    key_icon().save(COMMON / ICON)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        key_icon().resize((192, 192), Image.NEAREST).save(preview / "cle_tour.png")


if __name__ == "__main__":
    main()
