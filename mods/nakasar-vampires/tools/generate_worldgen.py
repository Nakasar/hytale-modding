#!/usr/bin/env python3
"""Génère les assets HytaleGenerator du Fragment halloween (biome et structure de monde).

    python3 mods/nakasar-vampires/tools/generate_worldgen.py

Le biome est un gros arbre de nœuds JSON ; le décrire en Python évite de dupliquer à la main les
motifs répétés (localisateur de surface, rotations aléatoires) et garde les constantes alignées
(hauteur du sol, positions des structures). Les fichiers produits restent éditables dans le
Hytale Node Editor.

Principe :
- Forme : une île flottante au-dessus du vide, comme les fragments d'Orbis du jeu de base (rayon
  ISLAND_RADIUS). Le dessus s'abaisse un peu près du bord puis finit en falaise ; le contour est
  dentelé par du bruit et le dessous forme un cône rocheux irrégulier. Au-delà, tout est vide.
- Terrain : collines (deux bruits simplex, jusqu'à une quinzaine de blocs de dénivelé) autour d'une
  hauteur de base. Le relief n'est aplani que sous les structures, la crypte d'arrivée et le
  manoir du comte, pour que les prefabs reposent à plat.
- Matériaux : herbe brûlée en surface, avec des plaques de cendre, de terre brûlée et de gravier
  moussu (bruit), puis terre, gravier et pierre (et un peu d'ardoise et de schiste).
- Structures : le domaine du Comte. Treize emplacements, décalés de quelques blocs selon la graine
  du monde (Jitter2d) ; le type de chacun dépend de la répartition choisie par la graine. Le premier
  exemplaire de chaque type est toujours là, le second une fois sur deux (bruit lu à l'emplacement). D'où 0 ou 1 village, 1 ou 2 fermes, postes de garde,
  cimetières, cryptes, champs de citrouilles et châteaux hantés, et toujours un seul manoir.
- Props, par étapes : 0 = grandes structures, 1 = forêts (taches denses de sapins et frênes morts)
  et arbres isolés, petits décors (affleurements, troncs couchés...), 2 = végétation.
- Environnement : « hanté » à proximité des structures (plus de morts-vivants), « lande » ailleurs.
"""

import json
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
GEN = PACK / "Server" / "HytaleGenerator"

BIOME_ID = "Nakasar_Halloween_Barrens"
WORLD_STRUCTURE_ID = "Nakasar_Halloween"
STRUCTURES_EXPORT = "Nakasar_Halloween_Structure_Positions"
VILLAGE_EXPORT = "Nakasar_Halloween_Village_Positions"
LANDMARKS_EXPORT = "Nakasar_Halloween_Landmark_Positions"

# Première couche d'air au-dessus du sol aplani (le dernier bloc solide est GROUND_Y - 1).
GROUND_Y = 81
SPAWN = (0, GROUND_Y, 0)
# Le manoir du comte, loin au nord du point d'apparition (qui est dans la crypte d'arrivée).
DRACULA = (0, GROUND_Y, -220)

# Île : rayon total, début de la pente du bord, et rayon max du centre d'une grande structure
# (la plus grande fait 41 × 41, le domaine du manoir 57 × 51 : elles restent sur le plat).
ISLAND_RADIUS = 340.0
EDGE_START = 296.0
# Décalage maximal d'un emplacement de structure selon la graine du monde.
STRUCTURE_JITTER = 16.0
# Types de structures : (nom, [(dossier de prefabs, poids)], tourner ?, [part des mondes où chaque
# exemplaire existe]) : le premier exemplaire est toujours là, le second une fois sur deux, le
# village 60 % du temps.
STRUCTURE_TYPES = [
    ("Village", [("Villages/Zombies", 1.0), ("Villages/Ruins", 1.0), ("Villages/Spiders", 1.0)], True, [0.6]),
    ("Farm", [("Farms/Zombies", 1.0), ("Farms/Ruins", 1.0), ("Farms/Burnt", 1.0)], True, [1.0, 0.5]),
    ("GuardPost", [("GuardPosts/Ruins", 1.0), ("GuardPosts/Spiders", 1.0), ("GuardPosts/Rebels", 1.0),
                   ("GuardPosts/Garrison", 1.2)], True, [1.0, 0.5]),
    ("Cemetery", [("Cemeteries/Haunted", 1.0), ("Cemeteries/Spiders", 1.0), ("Cemeteries/Undead", 1.0)], True, [1.0, 0.5]),
    ("Crypt", [("Crypts", 1.0)], True, [1.0, 0.5]),
    ("PumpkinField", [("PumpkinFields", 1.0)], True, [1.0, 0.5]),
    ("HauntedCastle", [("HauntedCastles", 1.0)], True, [1.0, 0.5]),
]
# Emplacements (x, z, grand ?) : 13, un par exemplaire. Les grands peuvent recevoir le village
# (69 × 69) ; entre deux structures, au moins 9 blocs dans le pire des décalages (village et ferme
# voisins décalés l'un vers l'autre).
SLOTS = [
    (-35, 195, True), (115, 165, True), (185, -65, True),
    (-205, 30, False), (-190, -85, False), (-155, 145, False), (-115, -175, False), (-80, -55, False),
    (-65, 70, False), (30, -90, False), (75, 35, False), (115, -175, False), (200, 65, False),
]
# Le type de chaque emplacement change d'un monde à l'autre : LAYOUTS répartitions (tirées ici une
# fois pour toutes), le monde en choisit une selon un bruit lu en un point fixe (valeur qui ne dépend
# que de la graine). Seuils à peu près équiprobables pour un bruit simplex centré.
LAYOUTS = 8
LAYOUT_NOISE_SPREAD = 0.35   # écart type supposé du bruit en un point, d'une graine à l'autre


def layout_bands():
    """LAYOUTS + 1 seuils : quantiles d'une loi normale d'écart type LAYOUT_NOISE_SPREAD."""
    from statistics import NormalDist
    inner = [NormalDist(0.0, LAYOUT_NOISE_SPREAD).inv_cdf(k / LAYOUTS) for k in range(1, LAYOUTS)]
    return [-1.0e9] + [round(v, 3) for v in inner] + [1.0e9]


LAYOUT_BANDS = layout_bands()


def layouts():
    """Pour chaque répartition, la liste (type, part des mondes) par emplacement. Le village va sur
    un grand emplacement ; deux structures du même type restent à plus de 140 blocs l'une de l'autre."""
    import random
    rng = random.Random(1031)
    roles = [(name, keep) for name, _, _, keeps in STRUCTURE_TYPES for keep in keeps]
    out = []
    while len(out) < LAYOUTS:
        order = roles[:]
        rng.shuffle(order)
        if order[0][0] != "Village":
            continue
        big = [i for i, s in enumerate(SLOTS) if s[2]]
        small = [i for i, s in enumerate(SLOTS) if not s[2]]
        rng.shuffle(big)
        rng.shuffle(small)
        idx = big[:1] + big[1:] + small
        layout = [None] * len(SLOTS)
        for slot, role in zip(idx, order):
            layout[slot] = role
        far = all(((SLOTS[i][0] - SLOTS[j][0]) ** 2 + (SLOTS[i][1] - SLOTS[j][1]) ** 2) ** 0.5 > 140
                  for i in range(len(SLOTS)) for j in range(i + 1, len(SLOTS)) if layout[i][0] == layout[j][0])
        if far and layout not in out:
            out.append(layout)
    return out
# Sol aplani autour du manoir : plat jusqu'à MANOR_FLAT blocs du centre, collines au-delà de MANOR_HILLS.
MANOR_FLAT, MANOR_HILLS = 38.0, 58.0

# Chemins relatifs à Server/Prefabs/ (PrefabPropAsset résout dans <pack>/Server/Prefabs).
PREFABS = "Nakasar/Halloween"
# Distance minimale entre un arbre / un décor et le centre d'une structure (demi-diagonale de la
# ferme, 49 × 45, plus la portée des branches) ; le village (69 × 69) a sa propre marge.
STRUCTURE_CLEARANCE = 38.0
VILLAGE_CLEARANCE = 54.0
AIR = {"Solid": "Empty"}
SURFACE_BLOCKS = ["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Soil_Ash", "Soil_Gravel_Mossy"]


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


def cached_positions(positions):
    """Positions mémorisées par sections de 32 blocs : la liste filtrée (bruits de répartition et de
    présence) n'est calculée qu'une fois par section, pas à chaque requête de distance."""
    return {"Type": "Cache", "SectionSize": 32, "CacheSize": 100, "Positions": positions}


def column(density):
    """Densité calculée une fois par colonne : Y est forcé à GROUND_Y avant le cache, donc tous les
    blocs d'une colonne relisent la même entrée. Les repères (structures, manoir) sont à GROUND_Y :
    les distances deviennent horizontales, comme elles l'étaient déjà au niveau du sol. Sans ça,
    les distances aux structures étaient recalculées pour chaque bloc de hauteur et le fragment
    mettait de longues secondes à générer son point d'arrivée."""
    return {"Type": "YOverride", "Value": float(GROUND_Y), "Inputs": [
        {"Type": "Cache", "Capacity": 64, "Inputs": [density]}]}


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


# Arbres du jeu (Server/Prefabs d'Assets.zip, lus le 2026-10-18) : chaque dossier est chargé en entier.
# Forêts : sapins et frênes morts, chênes moussus, souches et troncs couchés.
FOREST_TREES = [
    ("Trees/Fir_Dead/Stage_2", 1.2),
    ("Trees/Fir_Dead/Stage_3", 1.6),
    ("Trees/Fir_Dead_Large/Stage_2", 0.8),
    ("Trees/Fir_Dead_Large/Stage_3", 0.6),
    ("Trees/Ash_Dead/Stage_2", 0.9),
    ("Trees/Ash_Dead/Stage_3", 0.9),
    ("Trees/Oak_Moss/Stage_4", 0.5),
    ("Trees/Ash_Moss/Stage_3", 0.3),
    ("Trees/Ash_swamp_dead/Stage_3", 0.3),
    ("Trees/Poisoned/Stage_3", 0.15),
    ("Trees/Beech_Dry/Stage_3", 0.3),
    ("Trees/Dry_Dead", 0.3),
    ("Trees/Oak/Stumps", 0.25),
    ("Trees/Ash/Stumps", 0.25),
    ("Trees/Logs/Oak/Moss", 0.15),
    ("Trees/Logs/Ash/Mushroom_Cap_Brown", 0.1),
]
# Lande : arbres isolés, morts, tordus, quelques calcinés et de rares repères.
LONE_TREES = [
    ("Trees/Ash_Dead/Stage_3", 1.0),
    ("Trees/Fir_Dead/Stage_1", 0.6),
    ("Trees/Ash_twisted", 0.5),
    ("Trees/Ash_twisted_Large", 0.4),
    ("Trees/Burnt_dead/Stage_2", 0.4),
    ("Trees/Burnt/Stage_2", 0.3),
    ("Trees/Petrified_Dead/Stage_1", 0.2),
    ("Trees/Petrified_Dead/Stage_2", 0.2),
    ("Trees/Ash_twisted_Giant", 0.05),
    ("Trees/Burnt_Roots/Spider", 0.04),
]


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

def type_export(name):
    return f"Nakasar_Halloween_{name}_Positions"


def layout_value():
    """Bruit lu au même point (x et z forcés) partout : une valeur par graine de monde."""
    return {"Type": "XOverride", "Value": 7919.5, "Inputs": [
        {"Type": "ZOverride", "Value": -4441.5, "Inputs": [simplex2d(60.0, 1, "Layout")]}]}


def slot_positions(name):
    """Positions d'un type de structure : dans chaque répartition, ses emplacements, décalés selon la
    graine du monde, gardés seulement si la répartition est celle du monde ; un exemplaire facultatif
    n'est gardé que là où un bruit propre à l'emplacement dépasse un seuil (part `keep` des mondes,
    à peu près : le bruit simplex est symétrique autour de 0)."""
    out = []
    for k, layout in enumerate(LAYOUTS_TABLE):
        for i, (role, keep) in enumerate(layout):
            if role != name:
                continue
            x, z, _ = SLOTS[i]
            pos = {"Type": "Jitter2d", "Magnitude": STRUCTURE_JITTER, "Seed": f"Slot{i}",
                   "Positions": list_positions((x, GROUND_Y, z))}
            if keep < 1.0:
                pos = within(simplex2d(40.0, 1, f"Keep{i}"), 1.0 - 2.0 * keep, 1.0e9, pos)
            out.append(within(layout_value(), LAYOUT_BANDS[k], LAYOUT_BANDS[k + 1], pos))
    return {"Type": "Union", "Positions": out}


LAYOUTS_TABLE = layouts()


def exports():
    """Nœuds flottants qui déclarent les positions exportées avant tout import : une par type de
    structure, leur union, et les repères (point d'apparition, manoir)."""
    nodes = []
    for name, *_ in STRUCTURE_TYPES:
        positions = cached_positions(slot_positions(name))
        positions["ExportAs"] = VILLAGE_EXPORT if name == "Village" else type_export(name)
        nodes.append(distance_to(positions, 1.0, curve((0, 0), (1, 1))))
    union = cached_positions({"Type": "Union", "Positions": [
        imported(VILLAGE_EXPORT if name == "Village" else type_export(name)) for name, *_ in STRUCTURE_TYPES]})
    union["ExportAs"] = STRUCTURES_EXPORT
    nodes.append(distance_to(union, 1.0, curve((0, 0), (1, 1))))
    landmarks = dict(list_positions(SPAWN, DRACULA))
    landmarks["ExportAs"] = LANDMARKS_EXPORT
    nodes.append(distance_to(landmarks, 1.0, curve((0, 0), (1, 1))))
    return nodes


def biome():
    # Relief : 0 sous une structure (sol plat), 1 plus loin (collines). Plat jusqu'à 34 blocs du
    # centre d'une structure (la ferme, 49 × 45, tient dans un rayon de 33), 50 pour le village
    # (69 × 69), 24 pour la crypte d'arrivée ; le domaine du manoir jusqu'à MANOR_FLAT blocs.
    relief = {"Type": "Min", "Inputs": [
        distance_to(imported(STRUCTURES_EXPORT), 54.0, curve((0, 0), (34, 0), (52, 1))),
        distance_to(imported(VILLAGE_EXPORT), 72.0, curve((0, 0), (50, 0), (70, 1))),
        distance_to(imported(LANDMARKS_EXPORT), 42.0, curve((0, 0), (24, 0), (40, 1))),
        distance_to(list_positions(DRACULA), MANOR_HILLS + 2.0, curve((0, 0), (MANOR_FLAT, 0), (MANOR_HILLS, 1))),
    ]}
    hills = add(
        mul(simplex2d(110.0, 3, "Hills"), const(1.5)),
        mul(simplex2d(26.0, 2, "Bumps"), const(0.45)),
    )
    # Dessus de l'île (positif sous le sol) : le sol s'abaisse de 8 blocs entre EDGE_START et le bord,
    # où le dessous coupe le terrain en falaise.
    top = add(
        mul({"Type": "YValue"}, const(-0.125)),
        column(add(
            const((GROUND_Y - 0.5) / 8.0),
            mul(hills, relief),
            radial(curve((0, 0), (EDGE_START, 0), (ISLAND_RADIUS, -1.0))),
        )),
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
        column(add(
            radial(curve(*bottom_curve)),
            mul(simplex2d(22.0, 2, "Underside"), const(0.8)),
            rim,
        )),
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

    big = lambda path, seed, rotate: surface_locator(prefab(path, seed, rotate), SOLID_FLOOR, 12)
    structures = [
        runtime(0, "Prop", imported(VILLAGE_EXPORT if name == "Village" else type_export(name)),
                weighted_assignments(f"{name}Pick", 0.0, [(big(path, path.replace("/", ""), rotate), w) for path, w in folders]))
        for name, folders, rotate, _ in STRUCTURE_TYPES
    ]
    dracula = runtime(0, "Prop", list_positions(DRACULA), {
        "Type": "Constant",
        "Prop": surface_locator(prefab("VampireManor", "Manor", rotate=False), SOLID_FLOOR, 12),
    })
    # Crypte d'arrivée : le portail de retour apparaît en son centre (PortalTypes : point d'apparition
    # fixe en 0, GROUND_Y, 0), la porte donne au nord, vers le manoir.
    spawn_crypt = runtime(0, "Prop", list_positions(SPAWN), {
        "Type": "Constant",
        "Prop": surface_locator(prefab("SpawnCrypt", "SpawnCrypt", rotate=False), SOLID_FLOOR, 12),
    })

    # Arbres et décor : jamais dans une structure, ni sur le point d'apparition.
    def outside_structures(positions):
        manor = distance_to(list_positions(DRACULA), MANOR_FLAT + 9.0, curve((0, 0), (MANOR_FLAT + 9.0, MANOR_FLAT + 9.0)))
        positions = within(manor, MANOR_FLAT + 8.0, 1.0e9, positions)
        village = distance_to(imported(VILLAGE_EXPORT), VILLAGE_CLEARANCE + 1.0,
                              curve((0, 0), (VILLAGE_CLEARANCE + 1.0, VILLAGE_CLEARANCE + 1.0)))
        positions = within(village, VILLAGE_CLEARANCE, 1.0e9, positions)
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
    # Forêts : là où un bruit à grande échelle est haut, arbres serrés ; ailleurs, arbres épars.
    forest = simplex2d(95.0, 2, "Forest")
    vanilla_tree = lambda path, i: surface_locator(prefab(path, f"VanillaTree{i}", vanilla=True), GRASS_FLOOR, 26)
    woods = runtime(1, "Chunk", on_island(outside_structures(within(forest, 0.2, 1.0e9, mesh(6.5, 0.45, "Forest")))),
                    weighted_assignments("ForestPick", 0.15, [(small("Trees", "Tree"), 0.4)] + [
                        (vanilla_tree(path, i), w) for i, (path, w) in enumerate(FOREST_TREES)]))
    trees = runtime(1, "Chunk", on_island(outside_structures(within(forest, -1.0e9, 0.2, mesh(16.0, 0.45, "Trees")))),
                    weighted_assignments("TreePick", 0.35, [(small("Trees", "Tree"), 0.8)] + [
                        (vanilla_tree(path, 100 + i), w) for i, (path, w) in enumerate(LONE_TREES)]))
    decor = runtime(1, "Chunk", on_island(outside_structures(mesh(26.0, 0.45, "Decor"))), weighted_assignments("DecorPick", 0.4, [
        (small("Decor/Outcrops", "Outcrop"), 2.5),
        (small("Decor/FallenLogs", "Log"), 2.0),
        (small("Decor/MushroomRings", "Ring"), 0.5),
        (small("Decor/BonePiles", "Bones"), 0.6),
        (small("Decor/Graves", "Grave"), 0.5),
        (small("Decor/SpiderNests", "Nest"), 0.4),
        (small("Decor/Shrines", "Shrine"), 0.6),
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
        (plant("Plant_Fern_Forest"), 0.6),
        (plant("Plant_Crop_Mushroom_Common_Brown"), 0.15),
        (plant("Plant_Crop_Mushroom_Cap_Brown"), 0.08),
        (plant("Plant_Crop_Mushroom_Glowing_Purple"), 0.04),
    ]))

    environment = {
        "Type": "DensityDelimited",
        "Density": column(distance_to(
            {"Type": "Union", "Positions": [imported(STRUCTURES_EXPORT), list_positions(DRACULA)]},
            60.0,
            curve((0, 0), (60, 60)),
        )),
        "Delimiters": [
            {"Range": {"MinInclusive": 0.0, "MaxExclusive": 45.0}, "Environment": {"Type": "Constant", "Environment": "Nakasar_Env_Halloween_Haunted"}},
            {"Range": {"MinInclusive": 45.0, "MaxExclusive": 1.0e12}, "Environment": {"Type": "Constant", "Environment": "Nakasar_Env_Halloween"}},
        ],
    }

    return {
        "Name": BIOME_ID,
        # Les positions exportées sont déclarées avant tout import (nœuds flottants, lus en premier).
        "FloatingFunctionNodes": exports(),
        "Terrain": {"Type": "DAOTerrain", "Density": terrain_density},
        "MaterialProvider": materials,
        "Props": structures + [dracula, spawn_crypt, woods, trees, decor, plants],
        "EnvironmentProvider": environment,
        "TintProvider": {"Type": "Constant", "Color": "#7a6534"},
    }


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
    b = biome()
    write(GEN / "Biomes" / f"{BIOME_ID}.json", b)
    write(GEN / "WorldStructures" / f"{WORLD_STRUCTURE_ID}.json", world_structure())


if __name__ == "__main__":
    main()
