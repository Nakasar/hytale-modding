#!/usr/bin/env python3
"""Génère la Tour de l'Alchimiste, premier donjon du mod : clé, portail, instance, règles, îles et prefabs.

    python3 mods/nakasar-vampires/tools/generate_alchemist_tower.py [--preview DOSSIER]

Document de conception : https://claude.ai/code/artifact/38f49cae-a653-428c-86dc-4e1cdf0da191 (le donjon s'inspire
du donjon vanilla Deepworks). Étape 1, le socle :

- la clé `PortalKey_Nakasar_Alchemist_Tower`, même recette à l'établi des chasseurs et à l'autel (palier 3) ;
- le type de portail et l'instance : pas de limite de temps, ciel violet et vert figé au crépuscule ;
- les règles (GameplayConfig, comme Deepworks) : ni pose ni casse de blocs, aucune perte d'objets à la mort ;
- deux îles flottantes au-dessus du vide : l'île d'arrivée et, au nord, l'île de la tour, reliées par un pont ;
- le parvis d'arrivée (point d'apparition, portail de sortie anticipée), le pont et le pied de la tour, fermés par des
  parapets de 2 blocs : on ne peut pas sauter dans le vide. Un joueur qui y tombe quand même est ramené sur le parvis
  (TowerFallSystem, Java). La tour elle-même vient à l'étape 2 ; d'ici là, un portail de retour provisoire attend au
  pied de sa porte scellée.

Repère : x vers l'est, z vers le sud, y vers le haut ; le point d'apparition est en (0, GROUND_Y, 0).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import generate_prefabs as pf
import generate_worldgen as wg

PACK = wg.PACK
SERVER = PACK / "Server"
COMMON = PACK / "Common"
LANG = "nakasar_alchemist"
TOWER = "Nakasar_Alchemist_Tower"
KEY = "PortalKey_Nakasar_Alchemist_Tower"
EXIT = "Nakasar_Tower_Exit"
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
# Parvis d'arrivée (rayon intérieur du parapet), pont (demi-largeur, de z à z), pied de la tour.
PLAZA_RADIUS = 9
BRIDGE_HALF = 2
BRIDGE_START, BRIDGE_END = -10, -60
FOOT = (-8, -72, 8, -60)          # x0, z0, x1, z1 du parvis au pied de la tour
EXIT_Z = 6                         # portail de sortie anticipée, au sud du point d'apparition
RETURN_Z = -66                     # portail de retour provisoire, au pied de la tour

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
            "Particles": [{"SystemId": "MagicPortal_VoidKeyArt", "PositionOffset": {"Y": 2.5}}],
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
    """Île flottante centrée sur `center` : dessus plat jusqu'à `flat`, puis bord qui s'abaisse de 6 blocs ;
    dessous en cône rocheux dentelé. Densité positive dans l'île, négative ailleurs."""
    here = wg.list_positions(center)
    top = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(-0.125)),
        wg.column(wg.add(
            wg.const((GROUND_Y - 0.5) / 8.0),
            wg.distance_to(here, radius + 2.0, wg.curve((0, 0), (flat, 0), (radius, -0.75))),
        )),
    )
    depth = [(0, 0.85 * radius + 6), (0.5, 0.7 * radius + 4), (0.8, 0.45 * radius + 3), (0.95, 8), (1.0, 4)]
    bottom_curve = [(f * radius, d / 8.0 - GROUND_Y / 8.0) for f, d in depth]
    bottom_curve.append((radius + 1.0, -(GROUND_Y + 200) / 8.0))
    rim = wg.mul(wg.simplex2d(14.0, 2, f"{seed}Rim"),
                 wg.distance_to(here, radius + 2.0, wg.curve((0, 0), (radius - 10.0, 0), (radius - 2.0, 1.2))))
    bottom = wg.add(
        wg.mul({"Type": "YValue"}, wg.const(0.125)),
        wg.column(wg.add(wg.distance_to(here, radius + 2.0, wg.curve(*bottom_curve)),
                         wg.mul(wg.simplex2d(9.0, 2, f"{seed}Underside"), wg.const(0.6)), rim)),
    )
    return {"Type": "Min", "Inputs": [top, bottom]}


def prefab_prop(name):
    return {"Type": "Prefab", "WeightedPrefabPaths": [{"Path": f"{PREFABS}/{name}", "Weight": 1.0}]}


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

    def plant(name):
        return wg.surface_locator({"Type": "Manual", "Blocks": [
            {"Position": {"X": 0, "Y": 0, "Z": 0}, "Material": {"Solid": name}}]}, wg.on_floor(
            {"Type": "Or", "Patterns": [wg.is_block(b) for b in ("Soil_Grass_Full", "Soil_Grass", "Soil_Grass_Deep")]}), 12)

    plants = wg.runtime(1, "Chunk", wg.mesh(2.5, 0.5, "TowerPlants"), wg.weighted_assignments("TowerPlantPick", 0.45, [
        (plant("Plant_Grass_Lush_Short"), 5.0), (plant("Plant_Grass_Lush"), 3.0), (plant("Plant_Flower_Common_Violet"), 0.6),
        (plant("Plant_Flower_Common_Lime"), 0.5), (plant("Plant_Flower_Orchid_Purple"), 0.3),
        (plant("Plant_Flower_Tall_Cyan"), 0.3), (plant("Plant_Moss_Short_Green"), 1.0),
    ]))
    return {
        "Name": TOWER,
        "Terrain": {"Type": "DAOTerrain", "Density": {"Type": "Max", "Inputs": [
            island(SPAWN, ARRIVAL_RADIUS, ARRIVAL_FLAT, "Arrival"),
            island(TOWER_CENTER, TOWER_RADIUS, TOWER_FLAT, "Tower"),
        ]}},
        "MaterialProvider": materials,
        "Props": [arrival, plants],
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


# --- prefab : parvis, pont, pied de la tour ---------------------------------------------------

def parapet(p, x, z):
    """Garde-corps de 2 blocs (un bloc plein, un muret) : trop haut pour être sauté."""
    p.set(x, 0, z, PARAPET)
    p.set(x, 1, z, PARAPET_TOP)


def arrival_prefab(seed):
    p = pf.Prefab(seed)
    r = p.rng
    p.clear(-12, 0, FOOT[1] - 4, 12, 14, 12)

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

    # Pied de la tour : parvis carré fermé, porte scellée au nord, portail de retour provisoire.
    x0, z0, x1, z1 = FOOT
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            p.set(x, -1, z, p.pick(FLOOR))
            p.fill(x, 0, z, x, 6, z, pf.AIR)
            edge = x in (x0, x1) or z in (z0, z1)
            if edge and not (z == z1 and abs(x) <= BRIDGE_HALF):
                parapet(p, x, z)
    for x in range(x0, x1 + 1):                        # façade de la tour, porte en ogive murée de grilles
        p.fill(x, 0, z0, x, 8, z0, "Rock_Marble_Brick")
    for x in range(-2, 3):
        p.fill(x, 0, z0, x, 4 if abs(x) < 2 else 3, z0, "Deco_Iron_Bars")
    p.fill(-2, 5, z0, 2, 5, z0, "Rock_Gold_Brick_Ornate")
    p.set(0, 6, z0, "Rock_Crystal_Purple_Block")
    for x in (x0 + 1, x1 - 1):
        p.set(x, 0, z0 + 1, p.pick(CRYSTALS))
        p.set(x, 2, z1, "Deco_Lantern")
    p.fill(-1, 0, RETURN_Z - 1, 1, 2, RETURN_Z + 1, pf.AIR)
    p.set(0, 0, RETURN_Z, "Portal_Return")

    # Point d'apparition : 3 × 3 × 3 blocs libres.
    p.fill(-1, 0, -1, 1, 2, 1, pf.AIR)
    return p


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
    write_json(SERVER / "PortalTypes" / f"{TOWER}.json", portal_type())
    write_json(SERVER / "Instances" / TOWER / "instance.bson", instance())
    write_json(SERVER / "GameplayConfigs" / f"{TOWER}.json", gameplay_config())
    write_json(SERVER / "Weathers" / f"{WEATHER}.json", weather())
    write_json(SERVER / "Environments" / f"{ENVIRONMENT}.json", environment())
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{TOWER}.json", biome())
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{TOWER}.json", world_structure())
    out = SERVER / "Prefabs" / PREFABS
    count = arrival_prefab(9600).write(out / "Arrival" / "Arrival.prefab.json")
    print(f"Arrival: {count} blocs")
    (COMMON / ICON).parent.mkdir(parents=True, exist_ok=True)
    key_icon().save(COMMON / ICON)
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        key_icon().resize((192, 192), Image.NEAREST).save(preview / "cle_tour.png")


if __name__ == "__main__":
    main()
