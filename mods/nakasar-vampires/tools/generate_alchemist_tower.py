#!/usr/bin/env python3
"""Génère la Tour de l'Alchimiste, premier donjon du mod : clé, portail, instance, règles, îles et prefabs.

    python3 mods/nakasar-vampires/tools/generate_alchemist_tower.py [--preview DOSSIER]

Document de conception : https://claude.ai/code/artifact/38f49cae-a653-428c-86dc-4e1cdf0da191 (le donjon s'inspire
du donjon vanilla Deepworks).

- la clé `PortalKey_Nakasar_Alchemist_Tower`, même recette à l'établi des chasseurs et à l'autel (palier 3) ;
- le type de portail et l'instance : pas de limite de temps ni d'entrées, ciel violet et vert figé au crépuscule ;
- les règles (GameplayConfig, comme Deepworks) : ni pose ni casse de blocs, aucune perte d'objets à la mort ;
- l'archipel, à l'échelle de Deepworks (tools/alchemist_archipelago.py) : l'île d'arrivée, une chaîne de petites îles
  (haltes à fontaine, kiosque, sources, arches ; Jardins des Alambics ; Ruines du premier laboratoire, premier point de
  contrôle) reliées par des ponts elfiques, la grande île de la tour couverte d'une forêt d'arbres du jeu et traversée
  par un chemin, des îlots à toutes hauteurs (arbre fantastique, cristaux, émanations magiques : blocs invisibles
  `Nakasar_Tower_Emanation_*` qui portent des particules du jeu et une lumière), et des géodes, rochers et cristaux
  flottants du jeu dans le ciel ;
- le parvis d'arrivée (point d'apparition, portail de sortie anticipée), fermé comme tout le parcours par un
  garde-corps ;
- les barrières de repoussée (resources/TriggerVolumeData.json de l'instance, comme les Player_Pushback de Deepworks)
  au-dessus des garde-corps qui bordent le vide : places, ponts, coursives et escaliers extérieurs de la tour ;
- la tour elle-même (tools/alchemist_tower.py), environ 220 blocs de haut, posée en tranches empilées (Tower0 à
  Tower3, TOWER_SLICES) : étages, balcons, escaliers extérieurs, points de vue fermés, points de contrôle ;
  TowerLayout.java (Java, généré) reprend les positions des points de contrôle, ruines comprises ;
- les points de contrôle de Deepworks : statue Dungeon_Checkpoint_Statue et volume qui l'allume, fait du lieu le point
  d'apparition du groupe et soigne (checkpoint_volumes). Un joueur qui tombe quand même dans le vide est ramené au point
  d'apparition du monde, donc au dernier point de contrôle (TowerFallSystem) ;
- les pièges et énigmes (tools/alchemist_traps.py) : leurs volumes rejoignent ceux des barrières et des points de
  contrôle.

Repère : x vers l'est, z vers le sud, y vers le haut ; le point d'apparition est en (0, GROUND_Y, 0).
"""
import json
import shutil
import math
import uuid
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import alchemist_archipelago as arch
import alchemist_tower
import alchemist_traps
import tower_fx
import tower_warnings
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
# Archipel à l'échelle de Deepworks (tools/alchemist_archipelago.py) : îles du parcours, ponts, îlots.
ARRIVAL_RADIUS, ARRIVAL_FLAT = arch.ARRIVAL["radius"], arch.ARRIVAL["flat"]
TOWER_CENTER = (arch.TOWER["center"][0], GROUND_Y, arch.TOWER["center"][1])
TOWER_RADIUS, TOWER_FLAT = arch.TOWER["radius"], arch.TOWER["flat"]
STAGES = arch.HALTS                # îles du parcours entre l'arrivée et la tour (haltes, Jardins, Ruines)
PLAZA_RADIUS = arch.PLAZA_EDGE - 1  # parvis d'arrivée : rayon intérieur du parapet
BRIDGE_HALF = arch.BRIDGE_HALF
EXIT_Z = 6                         # portail de sortie anticipée, au sud du point d'apparition
TOWER_SEED = 4242
# Esprit qui sort de chaque quadrant de la Salle des Transmutations quand il s'éveille (rôles de generate_tower_mobs.py).
SPIRITS = {"Fire": "Nakasar_Elemental_Fire", "Ice": "Nakasar_Elemental_Frost", "Air": "Nakasar_Elemental_Thunder",
           "Earth": "Nakasar_Elemental_Root"}
# La tour se pose en tranches empilées (un prefab par tranche, coupé sous un plancher) : bas de chaque tranche.
TOWER_SLICES = [-8, alchemist_tower.F_LIBRARY - 1, alchemist_tower.F_LAB - 1, alchemist_tower.F_DECK - 1, 240]
ISLETS = arch.islets()
SKY = arch.sky_decor(ISLETS)
FOREST = arch.forest_sites()
UNDERGROWTH = arch.undergrowth_sites()
# Émanations magiques : blocs invisibles et traversables qui portent des particules du jeu et une lumière. La teinte
# « Color » d'une particule de bloc ne change pas les systèmes (vu avec la brèche) : on choisit des systèmes déjà colorés.
EMANATIONS = {
    "Smoke": ("Eye_Void_Smoke_Green", 1.2, 0.5, "#4f8"),
    "Motes": ("Dungeon_Goblin_Temple_Motes", 1.0, 0.5, "#a6f"),
    "Spiral": ("ForgottenTemple_Spark_Spiral", 1.0, 0.5, "#6ef"),
    "Arc": ("Goblin_Decorative_Lightning", 1.5, 1.0, "#9cf"),
    "Mist": ("Eye_Void_Smoke_Teal", 1.5, 0.5, "#4dc"),
    "Fireflies": ("Fireflies_GS", 1.0, 0.5, "#cf8"),
    # Fuite de la tuyauterie de gaz : les particules du bloc vanilla VFX_Dungeon_Goblin_Leaking_Pipe, dont la boîte
    # « Rubble » se ramasse avec Utiliser comme un caillou (Kevin a obtenu un « Tuyau qui fuit » en coupant la vanne).
    "Leak": ("Dungeon_Goblin_Leaking_Pipe", 1.0, 0.5, "#6f4"),
}
EMANATION_COLORS = {"Smoke": (90, 240, 140), "Motes": (180, 110, 255), "Spiral": (110, 230, 255),
                    "Arc": (160, 200, 255), "Mist": (70, 220, 200), "Fireflies": (210, 255, 120),
                    "Leak": (120, 230, 80)}

# Pierres de la tour : marbre clair, liserés d'or, cristaux violets et verts (les couleurs de l'Alchimiste).
FLOOR = arch.FLOOR
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
        # Comme Server/Instances/The_Deepworks/instance.bson (0.7.2) : mode Aventure, marqueurs d'apparition des mobs
        # actifs, instance supprimée une minute après le départ du dernier joueur. La mort sans perte d'objets vient
        # du GameplayConfig (gameplay_config), la réapparition au dernier point de contrôle des volumes SetWorldSpawn.
        "GameMode": "Adventure",
        "IsSpawnMarkersEnabled": True,
        "IsBlockSpawnersEnabled": True,
        "IsSavingPlayers": True,
        "DeleteOnRemove": True,
        "Plugin": {
            "Instance": {"RemovalConditions": [{"Type": "WorldEmpty", "TimeoutSeconds": 60}]},
            "PortalWorldConfig": {"Config": {"PortalType": TOWER, "TimeLimitSeconds": -1}},
        },
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
        # Pas de tombe sur la carte ni la boussole à chaque mort : c'est un donjon, on réapparaît au point de contrôle.
        "WorldMap": {"DisplayDeathMarker": False},
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
    # wg.column lit les distances à Y = wg.GROUND_Y : le centre doit être à cette hauteur, sinon l'écart vertical
    # s'ajoute à la distance (île plus basse au centre, plat rétréci, îlots hauts absents).
    here = wg.list_positions((center[0], wg.GROUND_Y, center[2]))
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
    # Prefabs posés à hauteur fixe (le dessus des îles est plat, à stage_y - 1) : ponts, îles du parcours, abords de
    # la tour (muret du bord, chemin de la forêt), tranches de la tour.
    fixed = [wg.runtime(0, "Prop", wg.list_positions((0, GROUND_Y, 0)), {"Type": "Constant", "Prop": prefab_prop("Bridges")})]
    for stage in STAGES:
        cx, cz = stage["center"]
        fixed.append(wg.runtime(0, "Prop", wg.list_positions((cx, arch.stage_y(stage), cz)),
                                {"Type": "Constant", "Prop": prefab_prop(stage["name"])}))
    fixed.append(wg.runtime(0, "Prop", wg.list_positions(TOWER_CENTER), {"Type": "Constant", "Prop": prefab_prop("Grounds")}))
    for i, y0 in enumerate(TOWER_SLICES[:-1]):
        fixed.append(wg.runtime(0, "Prop", wg.list_positions((TOWER_CENTER[0], GROUND_Y + y0, TOWER_CENTER[2])),
                                {"Type": "Constant", "Prop": prefab_prop(f"Tower{i}")}))

    def plant(name):
        return wg.surface_locator(block_prop(name), wg.on_floor(
            {"Type": "Or", "Patterns": [wg.is_block(b) for b in ("Soil_Grass_Full", "Soil_Grass", "Soil_Grass_Deep")]}), 80)

    # Points de semis à mi-hauteur des îles : chacun cherche le premier gazon de sa colonne, de y = 250 à y = 90.
    plant_points = wg.mesh(2.5, 0.5, "TowerPlants")
    plant_points["PointsY"] = 170
    plants = wg.runtime(1, "Chunk", plant_points, wg.weighted_assignments("TowerPlantPick", 0.45, [
        (plant("Plant_Grass_Lush_Short"), 5.0), (plant("Plant_Grass_Lush"), 3.0), (plant("Plant_Flower_Common_Violet"), 0.6),
        (plant("Plant_Flower_Common_Lime"), 0.5), (plant("Plant_Flower_Orchid_Purple"), 0.3),
        (plant("Plant_Flower_Tall_Cyan"), 0.3), (plant("Plant_Moss_Short_Green"), 1.0),
    ]))
    # Arbres fantastiques : un par îlot ; la forêt de l'île de la tour (arbres fantastiques et grands chênes, hêtres) et
    # son sous-bois ; deux arbres sur chaque grande île du parcours, entre le garde-corps et le bord.
    trees = []
    for i, (center, radius, tree) in enumerate(ISLETS):
        trees.append(wg.runtime(2, "Prop", wg.list_positions(center), {"Type": "Constant", "Prop": wg.surface_locator(
            wg.prefab(tree, f"TowerIslet{i}", vanilla=True), wg.SOLID_FLOOR, 6)}))
    ox, _, oz = TOWER_CENTER
    for size, folders in arch.FOREST_TREES.items():
        sites = [(x, z) for x, z, s in FOREST if s == size]
        for k, folder in enumerate(folders):
            group = sites[k::len(folders)]
            if group:
                trees.append(wg.runtime(2, "Prop", wg.list_positions(*[(ox + x, GROUND_Y, oz + z) for x, z in group]),
                                        {"Type": "Constant", "Prop": wg.surface_locator(
                                            wg.prefab(folder, f"TowerForest{size}{k}", vanilla=True), wg.SOLID_FLOOR, 8)}))
    for k, folder in enumerate(arch.UNDERGROWTH):
        group = [(ox + x, GROUND_Y, oz + z) for x, z, f in UNDERGROWTH if f == folder]
        trees.append(wg.runtime(2, "Prop", wg.list_positions(*group), {"Type": "Constant", "Prop": wg.surface_locator(
            wg.prefab(folder, f"TowerUnder{k}", vanilla=True), wg.SOLID_FLOOR, 8)}))
    for stage in STAGES:
        if stage["plaza"] < 20:
            continue
        for k, (x, z) in enumerate(arch.stage_trees(stage)):
            trees.append(wg.runtime(2, "Prop", wg.list_positions((x, arch.stage_y(stage), z)), {"Type": "Constant",
                "Prop": wg.surface_locator(wg.prefab(arch.SMALL_TREES[k % 3], f"{stage['name']}Tree{k}", vanilla=True),
                                           wg.SOLID_FLOOR, 8)}))
    # Ciel : géodes, rochers et cristaux flottants du jeu, posés tels quels dans le vide.
    sky = []
    for k, ((x, y, z), folder) in enumerate(SKY):
        sky.append(wg.runtime(3, "Prop", wg.list_positions((x, y, z)), {"Type": "Constant",
                                                                        "Prop": wg.prefab(folder, f"TowerSky{k}", vanilla=True)}))
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
        ] + [island((s["center"][0], arch.stage_y(s), s["center"][1]), s["radius"], s["flat"], s["name"]) for s in STAGES]
          + [island(center, radius, 0.6 * radius, f"Islet{i}") for i, (center, radius, _) in enumerate(ISLETS)]}},
        "MaterialProvider": materials,
        "Props": [arrival] + fixed + [plants] + trees + islet_decor + sky,
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


# --- prefab : parvis d'arrivée -----------------------------------------------------------------

def arrival_prefab(seed):
    p = pf.Prefab(seed)
    r = p.rng
    p.clear(-12, 0, -12, 12, 14, 12)

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
    # Garde-corps (Barrier au-dessus, comme sur tout le parcours), poteaux à lanterne aux quatre diagonales et de part
    # et d'autre du pont ; cristaux de part et d'autre du portail de sortie.
    posts = {(round((PLAZA_RADIUS + 1) * math.cos(math.radians(a))), round((PLAZA_RADIUS + 1) * math.sin(math.radians(a))))
             for a in (45, 135, 225, 315)}
    for x, z in ring:
        arch.guard(p, x, z, post=(x, z) in posts or (z < 0 and abs(x) == BRIDGE_HALF + 1))
    for x in (-3, 3):
        p.set(x, 0, EXIT_Z, p.pick(CRYSTALS))
    # Portail de sortie anticipée, au sud, tourné vers le point d'apparition ; 3 × 5 × 3 blocs libres autour.
    p.fill(-1, 0, EXIT_Z - 1, 1, 4, EXIT_Z + 1, pf.AIR)
    p.set(0, 0, EXIT_Z, EXIT, pf.NORTH)

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


# --- barrières de repoussée (comme Deepworks) ----------------------------------------------------

# Kevin (19 octobre 2026) : pas de blocs invisibles, des barrières comme dans Deepworks. Les générateurs posent des blocs
# Barrier là où un mur invisible est nécessaire (les vérifications de parcours en tiennent compte) ; on les retire des
# prefabs et on les remplace par des volumes de repoussée de l'instance (resources/TriggerVolumeData.json, copié dans
# chaque monde d'instance), comme les volumes Player_Pushback de Deepworks : en y entrant, le joueur est renvoyé vers
# l'intérieur, avec l'éclat et le son des barrières d'énergie de Deepworks.
PUSH_SPEED, PUSH_UP = 10.0, 4.0
PUSH_GROUP = str(uuid.uuid5(uuid.NAMESPACE_URL, "nakasar/alchemist-tower/pushback"))
PUSH_INSET = 0.2  # les boîtes rentrent un peu dans la colonne : longer le garde-corps ne déclenche rien


def extract_barriers(prefab, origin, inward):
    """Retire les blocs Barrier du prefab ; renvoie leurs colonnes {(x monde, z monde): (bas, haut, direction)}.

    `inward(x, z)` donne la direction (dx, dz) vers l'intérieur, dans le repère du prefab."""
    ox, oy, oz = origin
    columns = {}
    for (x, y, z) in [c for c, (name, _) in prefab.blocks.items() if name == arch.BARRIER]:
        prefab.set(x, y, z, None)
        lo, hi, _ = columns.get((x, z), (y, y, None))
        columns[(x, z)] = (min(lo, y), max(hi, y), inward(x, z))
    out = {}
    for (x, z), (lo, hi, (dx, dz)) in columns.items():
        a = round(math.degrees(math.atan2(dz, dx)) / 45) % 8  # 8 directions
        out[(x + ox, z + oz)] = (lo + oy, hi + oy + 2, a)
    return out


def toward(cx, cz):
    return lambda x, z: (cx - x, cz - z)


def pushback_volumes(columns):
    """Boîtes : colonnes de même hauteur et de même direction, fusionnées en rectangles (rangées en x, puis en z)."""
    rows = {}
    for (x, z), key in columns.items():
        rows.setdefault((key, z), []).append(x)
    runs = {}
    for (key, z), xs in rows.items():
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            runs.setdefault((key, start, prev), []).append(z)
            if x is not None:
                start = prev = x
    boxes = []
    for (key, x0, x1), zs in runs.items():
        zs.sort()
        start = prev = zs[0]
        for z in zs[1:] + [None]:
            if z is not None and z == prev + 1:
                prev = z
                continue
            boxes.append((key, x0, x1, start, prev))
            if z is not None:
                start = prev = z
    volumes = {}
    for k, ((lo, hi, a), x0, x1, z0, z1) in enumerate(sorted(boxes)):
        rad = math.radians(a * 45)
        hx, hy, hz = (x1 - x0 + 1) / 2 - PUSH_INSET, (hi - lo) / 2, (z1 - z0 + 1) / 2 - PUSH_INSET
        vid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"nakasar/alchemist-tower/pushback/{x0},{lo},{z0},{a}"))
        volumes[vid] = {
            "Position": {"X": (x0 + x1 + 1) / 2, "Y": (lo + hi) / 2, "Z": (z0 + z1 + 1) / 2},
            "Shape": {"Type": "Box", "Min": {"X": -hx, "Y": -hy, "Z": -hz}, "Max": {"X": hx, "Y": hy, "Z": hz}},
            "Effects": [
                {"Type": "SetVelocity", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0,
                 "Velocity": {"X": round(PUSH_SPEED * math.cos(rad), 3), "Y": PUSH_UP,
                              "Z": round(PUSH_SPEED * math.sin(rad), 3)},
                 "Additive": False, "RelativeMode": "Absolute"},
                {"Type": "PlayVfx", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0,
                 "ParticleSystem": "Dungeon_Goblin_Energy_Barrier_Impact", "Offset": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                 "Anchor": "Entity", "Scale": 1.0, "Rotation": {"X": 0.0, "Y": 0.0, "Z": 0.0}, "Duration": 0.0},
                {"Type": "PlaySound", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0,
                 "SoundEvent": "SFX_Deployable_Totem_Heal_Despawn", "PitchSemitones": 6.0, "Location": "Entity",
                 "Offset": {"X": 0.0, "Y": 0.0, "Z": 0.0}},
            ],
            "TargetTypes": ["Player"],
            "Enabled": True,
            "GroupId": PUSH_GROUP,
            "KeepLoaded": False,
            "Name": f"Player_Pushback_{k + 1:04d}",
        }
    return volumes


def trigger_volumes(volumes, groups):
    """resources/TriggerVolumeData.json de l'instance (même format que celui de The_Deepworks)."""
    origin = {"X": 0.0, "Y": float(GROUND_Y), "Z": 0.0}
    return {
        "Volumes": volumes,
        "Groups": {PUSH_GROUP: {"Origin": origin, "TargetTypes": ["Player"], "Enabled": True, "Color": 16711680,
                                "Name": "Player_Pushback"},
                   CHECKPOINT_GROUP: {"Origin": origin, "TargetTypes": ["Player"], "Enabled": True,
                                      "Color": 10879231, "Name": "Checkpoints"},
                   **groups},
    }


# --- points de contrôle (comme Deepworks) -------------------------------------------------------

# Kevin (19 octobre 2026) : mêmes statues et effets que Deepworks, soin compris. Chaque statue
# Dungeon_Checkpoint_Statue a son volume, copie des volumes Checkpoint_NN de The_Deepworks (lus dans Assets.zip 0.7.2) :
# en entrant, la statue s'anime puis s'allume, devient le point d'apparition du monde pour tout le groupe (les points de
# réapparition des joueurs sont effacés), titre « Point de contrôle » avec le nom du lieu, soin Dungeon_Checkpoint_Heal
# pendant 8,5 s ; la statue active précédente s'éteint (état Disabled) et ne se rallume plus.
CHECKPOINT_GROUP = str(uuid.uuid5(uuid.NAMESPACE_URL, "nakasar/alchemist-tower/checkpoints"))
CHECKPOINT_STATUE = "Dungeon_Checkpoint_Statue"
CHECKPOINT_RADIUS, CHECKPOINT_HEIGHT = 6.0, 5.0  # Deepworks : 9 × 7 ; plus petit ici, les rampes de la tour se croisent
ROTATIONS = ["None", "Ninety", "OneEighty", "TwoSeventy"]


def tag_condition(event, source, value, inverted=False, key="Checkpoint", entry=None):
    c = {"Type": "TagCondition", "Event": event}
    if entry is not None:
        c["Entry"] = entry
    c.update({"Source": source, "TagKey": key, "Comparison": "Exactly", "CompareAgainst": "Value", "TagValue": value,
              "Inverted": inverted, "MatchKey": "", "MatchValue": "", "Radius": 50.0, "Center": "Volume"})
    return c


def checkpoint_volume(n, statue, rot, spot):
    """Volume du point de contrôle n (1 = ruines) : `statue` et `spot` (arrêt du joueur) en coordonnées du monde."""
    sx, sy, sz = statue

    def place(event, state, delay=0.0, entry=None):
        e = {"Type": "PlaceBlock", "Event": event, "Interval": 0.0, "Delay": delay}
        if entry is not None:
            e["Entry"] = entry
        e.update({"BlockType": CHECKPOINT_STATUE, "BlockState": state, "Position": {"X": 0.0, "Y": 0.0, "Z": 0.0},
                  "Origin": "VolumeOrigin", "ReplaceMode": "Always", "Rotation": ROTATIONS[rot % 4], "Pitch": "None",
                  "Roll": "None"})
        return e

    def tags(event, key, value, match="", delay=0.0, entry=None):
        e = {"Type": "ModifyTags", "Event": event, "Interval": 0.0, "Delay": delay}
        if entry is not None:
            e["Entry"] = entry
        e.update({"Operation": "Set", "TagKey": key, "TagValue": value, "MatchKey": "Checkpoint", "MatchValue": match,
                  "Radius": 5.0, "Center": "Volume"})
        return e

    dx, dz = spot[0] - sx, spot[2] - sz
    return {
        "Position": {"X": sx + 0.5, "Y": float(sy), "Z": sz + 0.5},
        "Shape": {"Type": "Cylinder", "Center": {"X": 0.0, "Y": 0.0, "Z": 0.0}, "Radius": CHECKPOINT_RADIUS,
                  "Height": CHECKPOINT_HEIGHT},
        "Conditions": [
            tag_condition("ENTER", "Self", "Inactive"),
            tag_condition("ENTER", "Self", "Disabled", inverted=True),
            tag_condition("SIGNAL_RECEIVED", "Event", "Disable"),
            tag_condition("SIGNAL_RECEIVED", "Event", "Reset", entry=1),
            tag_condition("TICK", "Self", "Yes", key="Checkpoint_Healing", entry=1),
        ],
        "Effects": [
            place("ENTER", "Activating"),
            {"Type": "PlaySound", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0,
             "SoundEvent": "SFX_Dungeon_Checkpoint_Activate", "Location": "VolumeCenter",
             "Offset": {"X": 0.0, "Y": 0.0, "Z": 0.0}},
            {"Type": "SetWorldSpawn", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0, "Origin": "VolumeOrigin",
             "Position": {"X": float(dx), "Y": 0.0, "Z": float(dz)}, "Yaw": 0.0, "ClearPlayerRespawnPoints": True},
            {"Type": "ShowEventTitle", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0,
             "PrimaryTitle": "server.general.checkpoint.title", "SecondaryTitle": f"{LANG}.checkpoint.{n}",
             "Style": "Major", "Duration": 3.5, "FadeInDuration": 1.0, "FadeOutDuration": 1.0,
             "Recipient": "AllPlayers"},
            {"Type": "SendSignal", "Event": "ENTER", "Interval": 0.0, "Delay": 0.0, "MatchKey": "Checkpoint",
             "MatchValue": "Active", "Radius": 0.0, "Center": "Volume", "SignalKeys": ["Checkpoint"],
             "SignalValues": ["Disable"]},
            tags("ENTER", "Checkpoint", "Active"),
            tags("ENTER", "Checkpoint_Healing", "Yes"),
            place("ENTER", "Active", delay=8.5),
            tags("ENTER", "Checkpoint_Healing", "No", delay=8.5),
            place("SIGNAL_RECEIVED", "Disabled"),
            tags("SIGNAL_RECEIVED", "Checkpoint", "Disabled", match="Active"),
            place("SIGNAL_RECEIVED", "Inactive", entry=1),
            tags("SIGNAL_RECEIVED", "Checkpoint", "Inactive", entry=1),
            {"Type": "EntityEffect", "Event": "TICK", "Interval": 0.25, "Delay": 0.0, "Entry": 1,
             "Effect": "Dungeon_Checkpoint_Heal", "Mode": "Apply", "Duration": 0.5},
        ],
        "TargetTypes": ["Player"],
        "Enabled": True,
        "GroupId": CHECKPOINT_GROUP,
        "KeepLoaded": False,
        "Tags": {"Checkpoint": "Inactive", "Checkpoint_Healing": "No"},
        "Name": f"Checkpoint_{n:02d}",
    }


def checkpoint_volumes(tower, ruins_statue, ruins_spot):
    """Volumes des points de contrôle, dans l'ordre du parcours : ruines, puis la tour."""
    ox, oy, oz = TOWER_CENTER
    rx, rz = arch.RUINS["center"]
    (bx, by, bz), brot = ruins_statue
    ry = arch.stage_y(arch.RUINS)
    points = [((bx + rx, by + ry, bz + rz), brot, (ruins_spot[0] + rx, ruins_spot[1] + ry, ruins_spot[2] + rz))]
    for ((x, y, z), rot), (cx, cy, cz) in zip(tower.statues, tower.checkpoints):
        points.append(((x + ox, y + oy, z + oz), rot, (cx + ox, cy + oy, cz + oz)))
    return {str(uuid.uuid5(uuid.NAMESPACE_URL, f"nakasar/alchemist-tower/checkpoint/{n}")):
            checkpoint_volume(n, statue, rot, spot) for n, (statue, rot, spot) in enumerate(points, 1)}


# --- Java : positions de la tour ---------------------------------------------------------------

def tower_layout(tower, ruins_spot):
    """TowerLayout.java : point d'arrivée, points de contrôle, arènes du Codex vivant (pupitres, volumes que
    tower.CodexSystem étiquette), du golem de cristal (quadrants de tower.TransmutationSystem), de la Chimère (cuve,
    bassins, volumes de tower.ChimeraSystem) et de
    l'Alchimiste (athanor, piliers, fioles, rebord, volumes de tower.AlchemistSystem), en coordonnées du monde."""
    ox, oy, oz = TOWER_CENTER
    rx, rz = arch.RUINS["center"]
    spots = [(ruins_spot[0] + rx, ruins_spot[1] + arch.stage_y(arch.RUINS), ruins_spot[2] + rz)]
    spots += [(x + ox, y + oy, z + oz) for x, y, z in tower.checkpoints]
    rows = ",\n".join(f"            new Vector3d({x + 0.5}, {y}, {z + 0.5})" for x, y, z in spots)
    codex = tower.trap["codex"]
    cx, cy, cz = codex["center"]
    lecterns = ",\n".join(f"            new Vector3d({x + ox + 0.5}, {y + oy + 1}, {z + oz + 0.5})"
                           for x, y, z in codex["lecterns"])
    ids = alchemist_traps.codex_ids()
    chimera = tower.trap["chimera"]
    vx, vy, vz = chimera["vat"]
    chimera_ids = alchemist_traps.chimera_ids()
    trans = tower.trap["trans"]
    tx, ty, tz = trans["center"]
    trans_ids = alchemist_traps.trans_ids()
    quadrants = list(alchemist_tower.TRANS_QUADRANTS)
    alch = tower.trap["alchemist"]
    ax, ay, az = alch["center"]

    def points(cells, dy=0):
        return ",\n".join(f"            new Vector3d({x + ox + 0.5}, {y + oy + dy}, {z + oz + 0.5})" for x, y, z in cells)
    alch_ids = alchemist_traps.alchemist_ids()
    arcs = ", ".join(f"{{{a0}, {a1}}}" for a0, a1 in alchemist_tower.DECK_COLLAPSE_ARCS)
    codex_arcs = ", ".join(f"{{{a0}, {a1}}}" for a0, a1 in alchemist_tower.COLLAPSE_ARCS)

    def strings(values):
        return ", ".join(f'"{v}"' for v in values)
    return f"""package dev.nakasar.hytale.vampires.tower;

import org.joml.Vector3d;

/** Positions de la Tour de l'Alchimiste. Généré par tools/generate_alchemist_tower.py : ne pas modifier à la main. */
public final class TowerLayout {{

    /** Première couche d'air au-dessus du sol des îles. */
    public static final double GROUND_Y = {GROUND_Y};
    /** Point d'apparition, sur le parvis d'arrivée. */
    public static final Vector3d ARRIVAL = new Vector3d({SPAWN[0] + 0.5}, {SPAWN[1]}, {SPAWN[2] + 0.5});
    /** Points de contrôle, dans l'ordre du parcours : ruines du premier laboratoire, bibliothèque, Escalier des vents, antichambre. */
    public static final Vector3d[] CHECKPOINTS = {{
{rows}
    }};

    /** Codex vivant : centre de la rotonde de la bibliothèque, au sol. */
    public static final Vector3d CODEX_CENTER = new Vector3d({cx + ox + 0.5}, {cy + oy}, {cz + oz + 0.5});
    /** Rayon de l'arène du Codex (intérieur de la tour). */
    public static final double CODEX_ARENA_RADIUS = {alchemist_tower.R_IN};
    /** Dessus des trois pupitres où le Codex ouvre ses chapitres. */
    public static final Vector3d[] CODEX_LECTERNS = {{
{lecterns}
    }};
    /** Volumes de l'arène (tools/alchemist_traps.py, Traps.codex) : sceau de la rampe (Codex=On), remise à zéro (Reset=On). */
    public static final String CODEX_SEAL = "{ids['seal']}";
    public static final String CODEX_ARENA = "{ids['arena']}";
    /** Sorts des chapitres (Cast=On) : cercle de feu, pluie de livres, onde de givre de chaque pupitre. */
    public static final String CODEX_FIRE = "{ids['fire']}";
    public static final String CODEX_RAIN = "{ids['rain']}";
    public static final String[] CODEX_FROST = {{{strings(ids['frost'])}}};
    /** Pans d'étagères qui s'effondrent (Collapse=On) : volumes, secteurs en degrés (atan2(dz, dx)) entre deux rayons. */
    public static final String[] CODEX_COLLAPSE = {{{strings(ids['collapse'])}}};
    public static final double[][] CODEX_COLLAPSE_ARCS = {{{codex_arcs}}};
    public static final double[] CODEX_COLLAPSE_RADII = {{{alchemist_tower.COLLAPSE_R[0]}, {alchemist_tower.COLLAPSE_R[1]}}};
    /** Durée du cône rouge avant la chute d'un pan (tools/alchemist_traps.py, CODEX_COLLAPSE_WARN). */
    public static final float CODEX_COLLAPSE_WARN = {alchemist_traps.CODEX_COLLAPSE_WARN}f;

    /** Salle des Transmutations : centre (golem de cristal), au sol ; rayon de l'arène. */
    public static final Vector3d TRANS_CENTER = new Vector3d({tx + ox + 0.5}, {ty + oy}, {tz + oz + 0.5});
    public static final double TRANS_ARENA_RADIUS = {alchemist_tower.R_IN};
    /** Hauteur des quadrants au-dessus du sol : plus haut (l'hélice), on est hors de l'arène. */
    public static final double TRANS_ARENA_HEIGHT = {alchemist_tower.TRANS_ZONE_HEIGHT};
    /** Quadrants élémentaires dans l'ordre du tour (le répit passe à un voisin) : nom, volume (tools/alchemist_traps.py,
     * Traps.transmutation : State, Fx), rôle de l'esprit qui en sort, signes (x, z) du quadrant. */
    public static final String[] TRANS_QUADRANTS = {{{strings(quadrants)}}};
    public static final String[] TRANS_ZONES = {{{strings(trans_ids[el] for el in quadrants)}}};
    public static final String[] TRANS_SPIRITS = {{{strings(SPIRITS[el] for el in quadrants)}}};
    public static final int[][] TRANS_SIGNS = {{{", ".join(f"{{{sx}, {sz}}}" for sx, sz in alchemist_tower.TRANS_QUADRANTS.values())}}};
    /** Où les esprits de chaque quadrant apparaissent (une ligne par quadrant, dans l'ordre de TRANS_QUADRANTS). */
    public static final Vector3d[][] TRANS_SPIRIT_SPOTS = {{
{",\n".join("            {" + ", ".join(f"new Vector3d({x + ox + 0.5}, {y + oy + 1}, {z + oz + 0.5})" for x, y, z in trans["spirits"][el]) + "}" for el in quadrants)}
    }};
    /** Sceau du pied de l'hélice (Golem=On à la mort du golem). */
    public static final String TRANS_SEAL = "{trans_ids['seal']}";

    /** Chimère du laboratoire : centre de la cuve, au niveau du sol de la salle. */
    public static final Vector3d CHIMERA_VAT = new Vector3d({vx + ox + 0.5}, {vy + oy}, {vz + oz + 0.5});
    /** Rayon de l'arène de la Chimère (intérieur de la tour) et rayon intérieur de la margelle de la cuve. */
    public static final double CHIMERA_ARENA_RADIUS = {alchemist_tower.R_IN};
    public static final double CHIMERA_VAT_RADIUS = 7.5;
    /** Bassins d'acide secondaires (centre, au sol) et, devant chacun, la case où un zombie remplit son seau. */
    public static final Vector3d[] CHIMERA_BASINS = {{
{points(chimera["basins"])}
    }};
    public static final Vector3d[] CHIMERA_FILLS = {{
{points(chimera["fills"])}
    }};
    /** Volume (tools/alchemist_traps.py, Traps.chimera) : sceau de la porte nord (Chimera=On). */
    public static final String CHIMERA_SEAL = "{chimera_ids['seal']}";

    /** Alchimiste : centre de l'athanor, au sol de sa chambre (il s'y enferme au Grand Œuvre). */
    public static final Vector3d ALCHEMIST_CENTER = new Vector3d({ax + ox + 0.5}, {ay + oy}, {az + oz + 0.5});
    /** Rayon de la terrasse de l'Observatoire. */
    public static final double ALCHEMIST_DECK_RADIUS = {alchemist_tower.DECK_R};
    /** Antichambre (hors de l'arène) : secteur en degrés (atan2(dz, dx), comme tools/alchemist_tower.py) au-delà du rayon. */
    public static final double[] ALCHEMIST_ANTECHAMBER_ARC = {{{alchemist_tower.ANTECHAMBER_ARC[0]}, {alchemist_tower.ANTECHAMBER_ARC[1]}}};
    public static final double ALCHEMIST_ANTECHAMBER_RADIUS = 22;
    /** Bureau (hors de l'arène) : au-delà de cette coordonnée z du monde. */
    public static final double ALCHEMIST_STUDY_Z = {alchemist_tower.STUDY_DOOR_Z + oz};
    /** Pans du rebord qui s'effondrent au Grand Œuvre : secteurs en degrés, entre deux rayons. */
    public static final double[][] ALCHEMIST_COLLAPSE_ARCS = {{{arcs}}};
    public static final double[] ALCHEMIST_COLLAPSE_RADII = {{{alchemist_tower.DECK_COLLAPSE_R[0]}, {alchemist_tower.DECK_COLLAPSE_R[1]}}};
    /** Durée du cône rouge avant la chute d'un pan (tools/alchemist_traps.py, DECK_COLLAPSE_WARN). */
    public static final float ALCHEMIST_COLLAPSE_WARN = {alchemist_traps.DECK_COLLAPSE_WARN}f;
    /** Rayon des murs de l'athanor. */
    public static final double ALCHEMIST_ATHANOR_RADIUS = {alchemist_tower.ATHANOR_R};
    /** Cases libres autour de l'athanor où il ressort. */
    public static final Vector3d[] ALCHEMIST_EXITS = {{
{points(alch["exits"])}
    }};
    /** Piliers élémentaires de la Convergence (feu, givre, foudre, racines), au sol. */
    public static final Vector3d[] ALCHEMIST_PILLARS = {{
{points(alch["pillars"])}
    }};
    /** Points sûrs du bord intérieur où revient qui tombe d'un pan effondré. */
    public static final Vector3d[] ALCHEMIST_SAFE = {{
{points(alch["safe"])}
    }};
    /** Volumes (tools/alchemist_traps.py, Traps.alchemist) : sceau du bureau (Alchemist=On), levier du mode difficile
     * (lu : Hard ; posé : Locked), remise à zéro (Reset=On), titres des phases (Cast=On), pans (Collapse=On), fioles de
     * soin (Pack=On, une par case de {{@link #ALCHEMIST_HEALS}}). */
    public static final String ALCHEMIST_SEAL = "{alch_ids['seal']}";
    public static final String ALCHEMIST_LEVER = "{alch_ids['lever']}";
    public static final String ALCHEMIST_ARENA = "{alch_ids['arena']}";
    public static final String ALCHEMIST_PHASE_2 = "{alch_ids['phase2']}";
    public static final String ALCHEMIST_PHASE_3 = "{alch_ids['phase3']}";
    public static final String[] ALCHEMIST_COLLAPSE = {{{strings(alch_ids['collapse'])}}};
    public static final String[] ALCHEMIST_HEAL = {{{strings(alch_ids['heals'])}}};
    public static final Vector3d[] ALCHEMIST_HEALS = {{
{points(alch["heals"])}
    }};

    /** Cour : les gardiens d'airain à abattre, et le volume des portes de la tour (tools/alchemist_traps.py,
     * Traps.court) qui tombent quand ils le sont tous (Guardians=On). */
    public static final int COURT_GUARDIANS = {len(alchemist_tower.GUARDIANS)};
    public static final String COURT_DOOR = "{alchemist_traps.court_ids()['door']}";

    /** Barrières des arènes (tools/alchemist_traps.py, Traps.arena_gate ; Gate=Close / Gate=Open, tower.ArenaGate). */
    public static final String CODEX_GATE = "{alchemist_traps.arena_ids()['Codex']}";
    public static final String CHIMERA_GATE = "{alchemist_traps.arena_ids()['Chimera']}";
    public static final String ALCHEMIST_GATE = "{alchemist_traps.arena_ids()['Alchemist']}";

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
    columns = {}
    arrival = arrival_prefab(9600)
    arch.yield_to_bridges(arrival, (SPAWN[0], SPAWN[2]), PLAZA_RADIUS + 0.5)
    columns.update(extract_barriers(arrival, SPAWN, toward(0, 0)))
    count = arrival.write(out / "Arrival" / "Arrival.prefab.json")
    print(f"Arrival: {count} blocs")
    tower = alchemist_tower.build_checked(TOWER_SEED)
    columns.update(extract_barriers(tower.p, TOWER_CENTER, toward(0, 0)))
    shutil.rmtree(out / "Tower", ignore_errors=True)  # ancienne tour d'un seul tenant
    for i, (y0, y1) in enumerate(zip(TOWER_SLICES, TOWER_SLICES[1:])):
        count = tower.p.write(out / f"Tower{i}" / f"Tower{i}.prefab.json", y0, y1)
        print(f"Tower{i} (y {y0}..{y1 - 1}): {count} blocs")
    print(f"Points de contrôle de la tour : {tower.checkpoints}")
    bridges = arch.bridges_prefab(9601)
    deck, _ = arch._deck(arch.BRIDGES, arch.BRIDGE_HALF)

    def to_deck(x, z):
        return (sum(dx for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (x + dx, z + dz) in deck),
                sum(dz for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (x + dx, z + dz) in deck))

    columns.update(extract_barriers(bridges, (0, GROUND_Y, 0), to_deck))
    count = bridges.write(out / "Bridges" / "Bridges.prefab.json")
    print(f"Bridges: {count} blocs")
    grounds = arch.grounds_prefab(9604)

    def grounds_inward(x, z):
        if abs(x - arch.TOWER_GATE_X) == arch.PATH_HALF + 1 and z > arch.TOWER_RIM - 4:
            return (arch.TOWER_GATE_X - x, 0)
        return (-x, -z)

    columns.update(extract_barriers(grounds, TOWER_CENTER, grounds_inward))
    count = grounds.write(out / "Grounds" / "Grounds.prefab.json")
    print(f"Grounds: {count} blocs, {len(FOREST)} arbres, {len(SKY)} décors flottants, {len(ISLETS)} îlots")
    ruins_spot = None
    for k, stage in enumerate(STAGES):
        if stage["feature"] == "gardens":
            prefab = arch.gardens_prefab(9602)
        elif stage["feature"] == "ruins":
            prefab, ruins_spot, ruins_statue = arch.ruins_prefab(9603)
        else:
            prefab = arch.halt_prefab(stage, 9610 + k)
        cx, cz = stage["center"]
        arch.yield_to_bridges(prefab, (cx, cz), stage["plaza"] - 0.5)
        columns.update(extract_barriers(prefab, (cx, arch.stage_y(stage), cz), toward(0, 0)))
        count = prefab.write(out / stage["name"] / f"{stage['name']}.prefab.json")
        print(f"{stage['name']}: {count} blocs")
    volumes = pushback_volumes(columns)
    print(f"Barrières de repoussée : {len(columns)} colonnes, {len(volumes)} volumes")
    volumes.update(checkpoint_volumes(tower, ruins_statue, ruins_spot))
    traps, trap_groups = alchemist_traps.trap_volumes(tower, TOWER_CENTER)
    volumes.update(traps)
    print(f"Pièges et énigmes : {len(traps)} volumes, nuages {alchemist_traps.write_clouds()}")
    tower_warnings.system(2.5)  # zones des éléments de l'Alchimiste (AlchemistSystem.WARNING)
    # CodexSystem : tourbillons (1,5 s), jets d'encre (1,6 à 2,1 s le long de la ligne), onde de changement de phase.
    for seconds in (1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2):
        tower_warnings.system(seconds)
    # TransmutationSystem : chutes annoncées (1,5 s) ; ChimeraSystem : jets d'acide (2,2 s) ; AlchemistSystem :
    # anneau de l'athanor (cônes, tous écrits par tower_warnings.write).
    print(f"Zones d'annonce : {tower_warnings.write()} dixièmes de seconde, cônes {tower_warnings.CONE_TENTHS.start} "
          f"à {tower_warnings.CONE_TENTHS.stop - 1}")
    print(f"Effets des combats : {len(tower_fx.write())} systèmes")
    write_json(SERVER / "Instances" / TOWER / "resources" / "TriggerVolumeData.json", trigger_volumes(volumes, trap_groups))
    JAVA_LAYOUT.write_text(tower_layout(tower, ruins_spot), encoding="utf-8")
    (COMMON / ICON).parent.mkdir(parents=True, exist_ok=True)
    key_icon().save(COMMON / ICON)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        key_icon().resize((192, 192), Image.NEAREST).save(preview / "cle_tour.png")


if __name__ == "__main__":
    main()
