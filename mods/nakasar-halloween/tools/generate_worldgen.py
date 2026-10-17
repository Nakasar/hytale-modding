#!/usr/bin/env python3
"""Génère les assets HytaleGenerator du Fragment halloween (biome et structure de monde).

    python3 mods/nakasar-halloween/tools/generate_worldgen.py

Le biome est un gros arbre de nœuds JSON ; le décrire en Python évite de dupliquer à la main les
motifs répétés (localisateur de surface, rotations aléatoires) et garde les constantes alignées
(hauteur du sol, positions des structures). Les fichiers produits restent éditables dans le
Hytale Node Editor.

Principe :
- Terrain : collines douces (bruit simplex) autour d'une hauteur de base. Le relief est aplani
  près des structures, du point d'apparition et du château du comte pour que les prefabs reposent
  à plat.
- Matériaux : herbe brûlée, terre brûlée puis pierre (et un peu d'ardoise).
- Props, par étapes : 0 = grandes structures, 1 = arbres morts et petits décors, 2 = végétation.
- Environnement : « hanté » à proximité des structures (plus de morts-vivants), « lande » ailleurs.
"""

import json
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "pack"
GEN = PACK / "Server" / "HytaleGenerator"

BIOME_ID = "Nakasar_Halloween_Barrens"
WORLD_STRUCTURE_ID = "Nakasar_Halloween"
STRUCTURES_EXPORT = "Nakasar_Halloween_Structure_Positions"
LANDMARKS_EXPORT = "Nakasar_Halloween_Landmark_Positions"

# Première couche d'air au-dessus du sol aplani (le dernier bloc solide est GROUND_Y - 1).
GROUND_Y = 81
SPAWN = (0, GROUND_Y, 0)
DRACULA = (0, GROUND_Y, -190)

PREFABS = "Prefabs/Nakasar/Halloween"
# Distance minimale entre un arbre / un décor et le centre d'une structure (demi-diagonale du
# château du comte, 41 × 41, plus la portée des branches).
STRUCTURE_CLEARANCE = 34.0
AIR = {"Solid": "Empty"}
SURFACE_BLOCKS = ["Soil_Grass_Burnt", "Soil_Grass_Burnt_Full", "Soil_Dirt_Burnt"]


# --- briques de nœuds -------------------------------------------------------------------------

def const(v):
    return {"Type": "Constant", "Value": v}


def mul(*inputs):
    return {"Type": "Multiplier", "Inputs": list(inputs)}


def add(*inputs):
    return {"Type": "Sum", "Inputs": list(inputs)}


def simplex2d(scale, octaves, seed):
    return {"Type": "SimplexNoise2D", "Scale": scale, "Octaves": octaves, "Lacunarity": 2.0, "Persistence": 0.5, "Seed": seed}


def curve(*points):
    return {"Type": "Manual", "Points": [{"In": i, "Out": o} for i, o in points]}


def list_positions(*points):
    return {"Type": "List", "Positions": [{"X": x, "Y": y, "Z": z} for x, y, z in points]}


def distance_to(positions, max_distance, distance_curve):
    """Densité = courbe(distance à la position la plus proche) ; au-delà de max_distance, la
    distance vaut l'infini et la courbe renvoie sa dernière valeur."""
    return {
        "Type": "PositionsCellNoise",
        "Positions": positions,
        "ReturnType": {"Type": "Curve", "Curve": distance_curve},
        "DistanceFunction": {"Type": "Euclidean"},
        "MaxDistance": max_distance,
    }


def imported(name):
    return {"Type": "Imported", "Name": name}


def material(solid):
    return {"Type": "Constant", "Material": {"Solid": solid}}


def weighted_material(seed, *entries):
    return {
        "Type": "Weighted",
        "Seed": seed,
        "SkipChance": 0.0,
        "WeightedMaterials": [{"Weight": w, "Material": material(name)} for name, w in entries],
    }


def is_block(name):
    return {"Type": "BlockType", "Material": {"Solid": name}}


def on_floor(floor_pattern):
    """Case d'air posée sur `floor_pattern`."""
    return {"Type": "Floor", "Floor": floor_pattern, "Origin": {"Type": "BlockType", "Material": AIR}}


SOLID_FLOOR = on_floor({"Type": "Not", "Pattern": {"Type": "BlockType", "Material": AIR}})
GRASS_FLOOR = on_floor({"Type": "Or", "Patterns": [is_block(b) for b in SURFACE_BLOCKS]})


def surface_locator(prop, pattern, reach):
    """Cherche, de haut en bas dans la colonne, la première case qui respecte `pattern`."""
    return {
        "Type": "Locator",
        "Pattern": pattern,
        "Scanner": {
            "Type": "Linear",
            "Axis": "Y",
            "Range": {"MinInclusive": -reach, "MaxExclusive": reach + 1},
            "AscendingOrder": False,
            "Scanner": {"Type": "Origin"},
        },
        "PlacementCap": 1,
        "Prop": prop,
    }


def prefab(path, seed, rotate=True):
    p = {"Type": "Prefab", "WeightedPrefabPaths": [{"Path": f"{PREFABS}/{path}", "Weight": 1.0}]}
    if rotate:
        p = {"Type": "RandomRotator", "HorizontalRotations": True, "Seed": seed, "Prop": p}
    return p


def mesh(scale, jitter, seed, export=None):
    m = {
        "Type": "Mesh2D",
        "PointsY": GROUND_Y,
        "PointGenerator": {"Type": "Mesh", "ScaleX": scale, "ScaleY": scale, "ScaleZ": scale, "Jitter": jitter, "Seed": seed},
    }
    if export:
        m["ExportAs"] = export
    return m


def weighted_assignments(seed, skip, entries):
    return {
        "Type": "Weighted",
        "Seed": seed,
        "SkipChance": skip,
        "WeightedAssignments": [{"Weight": w, "Assignments": {"Type": "Constant", "Prop": prop}} for prop, w in entries],
    }


def runtime(index, precision, positions, assignments):
    return {
        "Runtime": index,
        "ContextPrecision": precision,
        "PropDistribution": {
            "Type": "Assigned",
            "OverrideAllProps": True,
            "PropDistribution": {"Type": "Positions", "Positions": positions},
            "Assignments": assignments,
        },
    }


# --- biome ------------------------------------------------------------------------------------

def biome():
    landmarks = dict(list_positions(SPAWN, DRACULA))
    landmarks["ExportAs"] = LANDMARKS_EXPORT

    # Grandes structures aléatoires, jamais à moins de 110 blocs du point d'apparition ni du château.
    structure_positions = {
        "Type": "FieldFunction",
        "ExportAs": STRUCTURES_EXPORT,
        "FieldFunction": distance_to(imported(LANDMARKS_EXPORT), 200.0, curve((0, 0), (200, 200))),
        "Delimiters": [{"Min": 110.0, "Max": 1.0e9}],
        # Jitter 0,25 : chaque point bouge d'au plus 0,25 × 150 ≈ 37 blocs, donc deux structures
        # restent à plus de 75 blocs l'une de l'autre (la plus grande en fait 41).
        "Positions": mesh(150.0, 0.25, "Structures"),
    }

    # Relief : 1 près d'une structure (sol plat), 1 au loin (collines).
    relief = distance_to(
        {"Type": "Union", "Positions": [imported(STRUCTURES_EXPORT), imported(LANDMARKS_EXPORT)]},
        70.0,
        curve((0, 0), (34, 0), (62, 1)),
    )
    hills = add(
        mul(simplex2d(140.0, 3, "Hills"), const(1.0)),
        mul(simplex2d(32.0, 2, "Bumps"), const(0.3)),
    )
    terrain_density = add(
        mul({"Type": "YValue"}, const(-0.125)),
        const((GROUND_Y - 0.5) / 8.0),
        mul(hills, relief),
    )

    materials = {
        "Type": "Solidity",
        "Solid": {
            "Type": "Queue",
            "Queue": [
                {
                    "Type": "SpaceAndDepth",
                    "LayerContext": "DepthIntoFloor",
                    "MaxExpectedDepth": 5,
                    "Layers": [
                        {"Type": "ConstantThickness", "Thickness": 1, "Material": weighted_material(
                            "Surface", ("Soil_Grass_Burnt", 8), ("Soil_Grass_Burnt_Full", 2), ("Soil_Dirt_Burnt", 1))},
                        {"Type": "ConstantThickness", "Thickness": 4, "Material": weighted_material(
                            "Subsoil", ("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 2), ("Soil_Gravel", 1))},
                    ],
                },
                weighted_material("Bedrock", ("Rock_Stone", 6), ("Rock_Slate", 2), ("Rock_Shale", 1)),
            ],
        },
        "Empty": {"Type": "Constant", "Material": AIR},
    }

    big = lambda path, seed: surface_locator(prefab(path, seed), SOLID_FLOOR, 12)
    structures = runtime(0, "Prop", structure_positions, weighted_assignments("StructurePick", 0.0, [
        (big("Crypts", "Crypt"), 3.0),
        (big("Cemeteries/Haunted", "CemeteryHaunted"), 1.5),
        (big("Cemeteries/Spiders", "CemeterySpiders"), 1.5),
        (big("Cemeteries/Undead", "CemeteryUndead"), 1.5),
        (big("PumpkinFields", "PumpkinField"), 3.0),
        (big("HauntedCastles", "HauntedCastle"), 2.0),
    ]))
    dracula = runtime(0, "Prop", list_positions(DRACULA), {
        "Type": "Constant",
        "Prop": surface_locator(prefab("DraculaCastle", "Dracula", rotate=False), SOLID_FLOOR, 12),
    })

    # Arbres et décor : jamais dans une structure, ni sur le point d'apparition.
    def outside_structures(positions):
        return {
            "Type": "FieldFunction",
            "FieldFunction": distance_to(
                {"Type": "Union", "Positions": [imported(STRUCTURES_EXPORT), imported(LANDMARKS_EXPORT)]},
                STRUCTURE_CLEARANCE + 1.0,
                curve((0, 0), (STRUCTURE_CLEARANCE + 1.0, STRUCTURE_CLEARANCE + 1.0)),
            ),
            "Delimiters": [{"Min": STRUCTURE_CLEARANCE, "Max": 1.0e9}],
            "Positions": positions,
        }

    small = lambda path, seed: surface_locator(prefab(path, seed), GRASS_FLOOR, 14)
    trees = runtime(1, "Chunk", outside_structures(mesh(13.0, 0.45, "Trees")), weighted_assignments("TreePick", 0.35, [
        (small("Trees", "Tree"), 1.0),
    ]))
    decor = runtime(1, "Chunk", outside_structures(mesh(29.0, 0.45, "Decor")), weighted_assignments("DecorPick", 0.3, [
        (small("Decor/BonePiles", "Bones"), 2.0),
        (small("Decor/Graves", "Grave"), 2.0),
        (small("Decor/SpiderNests", "Nest"), 1.5),
        (small("Decor/PumpkinPatches", "Pumpkins"), 2.0),
    ]))

    def plant(name):
        return surface_locator({"Type": "Manual", "Blocks": [{"Position": {"X": 0, "Y": 0, "Z": 0}, "Material": {"Solid": name}}]}, GRASS_FLOOR, 14)

    plants = runtime(2, "Chunk", mesh(3.0, 0.5, "Plants"), weighted_assignments("PlantPick", 0.45, [
        (plant("Plant_Grass_Gnarled"), 5.0),
        (plant("Plant_Grass_Gnarled_Short"), 4.0),
        (plant("Plant_Grass_Gnarled_Tall"), 2.0),
        (plant("Plant_Bush_Dead"), 1.5),
        (plant("Plant_Bush_Dead_Tall"), 0.7),
        (plant("Plant_Bush_Dead_Twisted"), 0.4),
        (plant("Plant_Bramble_Dead_Twisted"), 0.3),
        (plant("Plant_Leaves_Dead"), 1.0),
        (plant("Plant_Crop_Pumpkin_StageFinal"), 0.15),
    ]))

    environment = {
        "Type": "DensityDelimited",
        "Density": distance_to(
            {"Type": "Union", "Positions": [imported(STRUCTURES_EXPORT), list_positions(DRACULA)]},
            60.0,
            curve((0, 0), (60, 60)),
        ),
        "Delimiters": [
            {"Range": {"MinInclusive": 0.0, "MaxExclusive": 45.0}, "Environment": {"Type": "Constant", "Environment": "Nakasar_Env_Halloween_Haunted"}},
            {"Range": {"MinInclusive": 45.0, "MaxExclusive": 1.0e12}, "Environment": {"Type": "Constant", "Environment": "Nakasar_Env_Halloween"}},
        ],
    }

    return {
        "Name": BIOME_ID,
        "FloatingFunctionNodes": [],
        "Terrain": {"Type": "DAOTerrain", "Density": terrain_density},
        "MaterialProvider": materials,
        "Props": [structures, dracula, trees, decor, plants],
        "EnvironmentProvider": environment,
        "TintProvider": {"Type": "Constant", "Color": "#7a6534"},
        # Les positions exportées sont déclarées ici pour exister même si l'ordre de lecture change.
        "$Exports": None,
    }, landmarks


def world_structure():
    return {
        "Type": "NoiseRange",
        "DefaultBiome": BIOME_ID,
        "DefaultTransitionDistance": 16,
        "MaxBiomeEdgeDistance": 0,
        "Density": const(0.0),
        "Biomes": [],
        "SpawnPositions": list_positions(SPAWN),
    }


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.relative_to(PACK))


def main():
    b, landmarks = biome()
    del b["$Exports"]
    # Les exports doivent être déclarés avant leurs imports : les repères sont un nœud flottant.
    b["FloatingFunctionNodes"] = [distance_to(landmarks, 1.0, curve((0, 0), (1, 1)))]
    write(GEN / "Biomes" / f"{BIOME_ID}.json", b)
    write(GEN / "WorldStructures" / f"{WORLD_STRUCTURE_ID}.json", world_structure())


if __name__ == "__main__":
    main()
