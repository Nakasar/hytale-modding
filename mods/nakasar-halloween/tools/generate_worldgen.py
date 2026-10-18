#!/usr/bin/env python3
"""Génère les assets HytaleGenerator du Fragment halloween (biome et structure de monde).

    python3 mods/nakasar-halloween/tools/generate_worldgen.py

Le biome est un gros arbre de nœuds JSON ; le décrire en Python évite de dupliquer à la main les
motifs répétés (localisateur de surface, rotations aléatoires) et garde les constantes alignées
(hauteur du sol, positions des structures). Les fichiers produits restent éditables dans le
Hytale Node Editor.

Principe :
- Forme : une île flottante au-dessus du vide, comme les fragments d'Orbis du jeu de base (rayon
  ISLAND_RADIUS). Le dessus s'abaisse un peu près du bord puis finit en falaise ; le contour est
  dentelé par du bruit et le dessous forme un cône rocheux irrégulier. Au-delà, tout est vide.
- Terrain : collines (deux bruits simplex, jusqu'à une quinzaine de blocs de dénivelé) autour d'une
  hauteur de base. Le relief n'est aplani que sous les structures, le point d'apparition et le
  château du comte, pour que les prefabs reposent à plat.
- Matériaux : herbe brûlée en surface, avec des plaques de cendre, de terre brûlée et de gravier
  moussu (bruit), puis terre, gravier et pierre (et un peu d'ardoise et de schiste).
- Props, par étapes : 0 = grandes structures, 1 = arbres morts et petits décors (affleurements,
  cercles de champignons, autels, troncs couchés...), 2 = végétation et champignons luisants.
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
DRACULA = (0, GROUND_Y, -110)

# Île : rayon total, début de la pente du bord, et rayon max du centre d'une grande structure
# (la plus grande fait 41 × 41, le château du comte 49 × 49 : elles restent sur le plat).
ISLAND_RADIUS = 170.0
EDGE_START = 148.0
STRUCTURE_MAX_RADIUS = 116.0
# Taille de la maille des grandes structures (une par cellule) : plus elle est grande, plus il reste
# de collines entre elles.
STRUCTURE_MESH = 66.0
# Distance minimale entre le centre d'une grande structure et le point d'apparition / le château.
SPAWN_CLEARANCE = 45.0
DRACULA_CLEARANCE = 64.0

# Chemins relatifs à Server/Prefabs/ (PrefabPropAsset résout dans <pack>/Server/Prefabs).
PREFABS = "Nakasar/Halloween"
# Distance minimale entre un arbre / un décor et le centre d'une structure (demi-diagonale du
# château du comte, 41 × 41, plus la portée des branches).
STRUCTURE_CLEARANCE = 34.0
AIR = {"Solid": "Empty"}
SURFACE_BLOCKS = ["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Soil_Ash", "Soil_Gravel_Mossy"]
PUMPKIN_RIPE = "*Plant_Crop_Pumpkin_Block_State_Definitions_StageFinal"


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


def radial(distance_curve):
    """Densité = courbe(distance horizontale au centre de l'île, l'axe Y passant par 0, 0)."""
    return {"Type": "Axis", "Axis": {"X": 0.0, "Y": 1.0, "Z": 0.0}, "IsAnchored": False, "Curve": distance_curve}


def within(field, low, high, positions):
    """Garde les positions dont la densité `field` est dans [low, high]."""
    return {"Type": "FieldFunction", "FieldFunction": field, "Delimiters": [{"Min": low, "Max": high}], "Positions": positions}


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


def field_material(field, *bands):
    """Matériau choisi selon la valeur d'un champ (bruit) : bandes (de, à, fournisseur)."""
    return {
        "Type": "FieldFunction",
        "FieldFunction": field,
        "Delimiters": [{"From": a, "To": b, "Material": m} for a, b, m in bands],
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


VANILLA_DEAD_TREES = "Trees/Ash_Dead"


def prefab(path, seed, rotate=True, vanilla=False):
    """Prop d'un dossier de prefabs : les nôtres sous Nakasar/Halloween, ou ceux du jeu (`vanilla`).

    Le serveur cherche le chemin dans tous les packs, jeu compris, et charge tous les prefabs du
    dossier. Un chemin absent ne place rien, sans erreur.
    """
    p = {"Type": "Prefab", "WeightedPrefabPaths": [{"Path": path if vanilla else f"{PREFABS}/{path}", "Weight": 1.0}]}
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

    # Grandes structures aléatoires sur le plat de l'île, à l'écart du point d'apparition et du
    # château. Jitter 0,15 : chaque point bouge d'au plus 0,15 × 66 ≈ 10 blocs, donc deux structures
    # restent à plus de 46 blocs l'une de l'autre (la plus grande en fait 41).
    far = lambda point, d: distance_to(list_positions(point), d + 1.0, curve((0, 0), (d + 1.0, d + 1.0)))
    structure_positions = within(
        radial(curve((0, 0), (ISLAND_RADIUS, ISLAND_RADIUS))), 0.0, STRUCTURE_MAX_RADIUS,
        within(far(SPAWN, SPAWN_CLEARANCE), SPAWN_CLEARANCE, 1.0e9,
               within(far(DRACULA, DRACULA_CLEARANCE), DRACULA_CLEARANCE, 1.0e9,
                      mesh(STRUCTURE_MESH, 0.15, "Structures"))))
    structure_positions["ExportAs"] = STRUCTURES_EXPORT

    # Relief : 0 sous une structure (sol plat), 1 au-delà de 40 blocs de son centre (collines). La
    # plus grande structure (château du comte, 41 × 41) tient dans un rayon de 22 blocs ; au-delà,
    # le sol remonte ou descend progressivement autour d'elle.
    relief = distance_to(
        {"Type": "Union", "Positions": [imported(STRUCTURES_EXPORT), imported(LANDMARKS_EXPORT)]},
        42.0,
        curve((0, 0), (24, 0), (40, 1)),
    )
    hills = add(
        mul(simplex2d(110.0, 3, "Hills"), const(1.5)),
        mul(simplex2d(26.0, 2, "Bumps"), const(0.45)),
    )
    # Dessus de l'île (positif sous le sol) : le sol s'abaisse de 8 blocs entre EDGE_START et le bord,
    # où le dessous coupe le terrain en falaise.
    top = add(
        mul({"Type": "YValue"}, const(-0.125)),
        const((GROUND_Y - 0.5) / 8.0),
        mul(hills, relief),
        radial(curve((0, 0), (EDGE_START, 0), (ISLAND_RADIUS, -1.0))),
    )
    # Dessous de l'île (positif au-dessus du fond) : un cône dont le fond remonte vers le bord,
    # bosselé par du bruit ; au-delà du rayon, le fond passe très haut et tout devient du vide.
    bottom_depth = [(0, 64), (0.4, 52), (0.7, 38), (0.88, 28), (0.97, 18), (1.0, 12)]
    bottom_curve = [(f * ISLAND_RADIUS, d / 8.0 - GROUND_Y / 8.0) for f, d in bottom_depth]
    bottom_curve.append((ISLAND_RADIUS + 1.0, -(GROUND_Y + 200) / 8.0))
    # Le contour est dentelé : près du bord, un bruit à grande échelle avance ou recule la falaise.
    rim = mul(simplex2d(46.0, 2, "Rim"), radial(curve((0, 0), (ISLAND_RADIUS - 40.0, 0), (ISLAND_RADIUS - 5.0, 1.8))))
    bottom = add(
        mul({"Type": "YValue"}, const(0.125)),
        radial(curve(*bottom_curve)),
        mul(simplex2d(22.0, 2, "Underside"), const(0.8)),
        rim,
    )
    terrain_density = {"Type": "Min", "Inputs": [top, bottom]}

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
                        {"Type": "ConstantThickness", "Thickness": 1, "Material": field_material(
                            simplex2d(23.0, 2, "Patches"),
                            (-10.0, -0.5, material("Soil_Ash")),
                            (-0.5, 0.35, weighted_material("Surface", ("Soil_Grass_Burnt", 12), ("Soil_Dirt_Burnt", 1))),
                            (0.35, 0.6, material("Soil_Dirt_Burnt")),
                            (0.6, 10.0, weighted_material("Gravel", ("Soil_Gravel_Mossy", 3), ("Soil_Gravel", 1))),
                        )},
                        {"Type": "ConstantThickness", "Thickness": 4, "Material": weighted_material(
                            "Subsoil", ("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 2), ("Soil_Gravel", 1))},
                    ],
                },
                weighted_material("Bedrock", ("Rock_Stone", 6), ("Rock_Stone_Mossy", 1), ("Rock_Slate", 2), ("Rock_Shale", 1)),
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

    # Pas d'arbre ni de décor qui dépasse du bord de l'île.
    def on_island(positions):
        return within(radial(curve((0, 0), (ISLAND_RADIUS, ISLAND_RADIUS))), 0.0, EDGE_START + 10.0, positions)

    small = lambda path, seed: surface_locator(prefab(path, seed), GRASS_FLOOR, 26)
    trees = runtime(1, "Chunk", on_island(outside_structures(mesh(13.0, 0.45, "Trees"))), weighted_assignments("TreePick", 0.35, [
        (small("Trees", "Tree"), 1.0),
        # frênes morts du jeu (dossier Server/Prefabs/Trees/Ash_Dead d'Assets.zip, toutes tailles)
        (surface_locator(prefab(VANILLA_DEAD_TREES, "VanillaTree", vanilla=True), GRASS_FLOOR, 26), 0.8),
    ]))
    decor = runtime(1, "Chunk", on_island(outside_structures(mesh(21.0, 0.45, "Decor"))), weighted_assignments("DecorPick", 0.25, [
        (small("Decor/Outcrops", "Outcrop"), 2.5),
        (small("Decor/FallenLogs", "Log"), 1.5),
        (small("Decor/MushroomRings", "Ring"), 1.2),
        (small("Decor/BonePiles", "Bones"), 1.5),
        (small("Decor/Graves", "Grave"), 1.5),
        (small("Decor/SpiderNests", "Nest"), 1.0),
        (small("Decor/PumpkinPatches", "Pumpkins"), 1.5),
        (small("Decor/Shrines", "Shrine"), 0.8),
    ]))

    def plant(name):
        return surface_locator({"Type": "Manual", "Blocks": [{"Position": {"X": 0, "Y": 0, "Z": 0}, "Material": {"Solid": name}}]}, GRASS_FLOOR, 26)

    plants = runtime(2, "Chunk", mesh(3.0, 0.5, "Plants"), weighted_assignments("PlantPick", 0.45, [
        (plant("Plant_Grass_Gnarled"), 5.0),
        (plant("Plant_Grass_Gnarled_Short"), 4.0),
        (plant("Plant_Grass_Gnarled_Tall"), 2.0),
        (plant("Plant_Bush_Dead"), 1.5),
        (plant("Plant_Bush_Dead_Tall"), 0.7),
        (plant("Plant_Bush_Dead_Twisted"), 0.4),
        (plant("Plant_Bramble_Dead_Twisted"), 0.3),
        (plant("Plant_Leaves_Dead"), 0.6),
        (plant("Wood_Gnarled_Roots"), 0.5),
        (plant("Plant_Crop_Mushroom_Glowing_Purple"), 0.2),
        (plant("Plant_Crop_Mushroom_Glowing_Violet"), 0.12),
        (plant("Plant_Crop_Mushroom_Glowing_Green"), 0.08),
        (plant(PUMPKIN_RIPE), 0.1),
        (plant("Deco_Halloween_Pumpkin_Scary"), 0.04),
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
