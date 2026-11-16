#!/usr/bin/env python3
"""Cœurs de village des Peuples d'Orbis : une place ronde par peuple, faite de prefabs et de blocs VANILLA, qui
s'étoffe à chaque palier (Kevin, 2026-11-15 : le carré de chemin d'avant était « moche »).

Repère d'une scène : x est, z sud (nord = -Z), y = 0 surface de la place aplanie, y = 1 premier bloc d'air. Le cœur du
village (bloc invisible) est en (0, 1, 0) et reste libre. Les prefabs vanilla sont collés ancre en (x, y, z), comme
village/VillageBuilder.

Pour chaque palier t, la scène complète S_t est composée ; le Java applique ensuite l'écart avec S_{t-1} :
  1. « Pieces » : prefabs vanilla nouveaux au palier t (collés par VillageBuilder.paste : rotations, fluides, remplissages
     faits par le moteur) ;
  2. « Set » : blocs du mod (blocs vanilla posés un à un) nouveaux ou changés, ou dans l'emprise d'une pièce nouvelle
     (le collage d'un prefab efface ses cases « Empty ») ;
  3. « Clear » : blocs de S_{t-1} absents de S_t (feuillage d'un arbre qui a grandi), retirés seulement s'ils sont
     toujours là ;
  4. « Fluids » : eau posée par le mod (bassin feran), via un petit prefab de fluides du mod.
Le tableau, le dépôt et la bannière sont posés par le Java aux places choisies (Board/Deposit/Banner), tournés vers le
cœur ; ces cases et celle du cœur ne reçoivent jamais de bloc.

Orientation (rotation = index RotationTuple : lacet + 4 × tangage) : lacet 0 = face au sud (+Z), 1 est, 2 nord, 3 ouest ;
un tronc couché vaut 4 le long de Z, 5 le long de X. Pas de meuble à plusieurs cases (bancs, cage, grande torche
feran) parmi les blocs posés un à un : le moteur ne poserait pas leurs cases de remplissage.

Les prefabs vanilla viennent d'Assets.zip : `--vanilla` est le JSON écrit par tools/extract_vanilla_prefabs.py
(prefabs listés dans PIECES). Sortie : tools/village-hearts.json, lu par generate_village_layouts.py (champ « Heart »
des plans), et les prefabs de fluides Server/Prefabs/Nakasar/Peuples/Hearts/. `--preview DIR --palette pal.json` dessine
les aperçus (tools/heart_render.py).

    python3 tools/generate_village_hearts.py --vanilla vanilla-heart-prefabs.json [--preview DIR --palette pal.json]
"""
import argparse
import json
import math
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
OUT_JSON = TOOLS / "village-hearts.json"
FLUID_DIR = ROOT / "src/main/resources/Server/Prefabs/Nakasar/Peuples/Hearts"
FLUID_PREFIX = "Nakasar/Peuples/Hearts/"
BLOCK_IDS = TOOLS / "vanilla-block-ids-0.7.2.txt"

OAK = "Npc/Kweebec/Oak/"
TRORK = "Npc/Trork/"
TIERS = (0, 1, 2, 3)

# Lacets : face au sud, à l'est, au nord, à l'ouest.
SOUTH, EAST, NORTH, WEST = 0, 1, 2, 3
ALONG_Z, ALONG_X = 4, 5
# Blocs à plusieurs cases (remplissages dans les prefabs vanilla) : jamais posés un à un.
MULTI_CELL = {"Furniture_Ancient_Bench", "Furniture_Feran_Bench", "Deco_Trork_Cage", "Furniture_Feran_Torch_Tall"}
# Blocs des prefabs vanilla à retirer après collage (le spawner ne se résout qu'à la génération du monde).
STRIP = ("Block_Spawner_Block",)

VANILLA = {}


def h(x, z, salt=0):
    """Bruit déterministe 0..1."""
    n = (x * 73856093) ^ (z * 19349663) ^ (salt * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def rot(x, z, r):
    """Même convention que PrefabRotation du serveur (quarts de tour : x' = z, z' = -x)."""
    for _ in range(r % 4):
        x, z = z, -x
    return x, z


def facing(x, z):
    """Lacet d'un bloc en (x, z) tourné vers le cœur (0, 0)."""
    if abs(x) > abs(z):
        return WEST if x > 0 else EAST
    return NORTH if z > 0 else SOUTH


class Scene:
    def __init__(self):
        self.b = {}       # (x, y, z) -> (nom, rotation, propriétaire)
        self.fluid = {}   # (x, y, z) -> nom du fluide
        self.pieces = []  # (prefab, x, y, z, rotation)
        self.marks = {}
        self.reserved = set()

    def set(self, x, y, z, name, r=0, owner="mod"):
        if owner == "mod" and (x, y, z) in self.reserved:
            return
        if name is None:
            self.b.pop((x, y, z), None)
        else:
            self.b[(x, y, z)] = (name, r, owner)

    def get(self, x, y, z):
        v = self.b.get((x, y, z))
        return v[0] if v else None

    def water(self, x, y, z):
        self.b.pop((x, y, z), None)
        self.fluid[(x, y, z)] = "Water_Source"

    def paste(self, prefab, x, y, z, r=0):
        p = VANILLA[prefab]
        ax, ay, az = p["anchor"]
        key = (prefab, x, y, z, r)
        self.pieces.append(key)
        for bx, by, bz, name, br in p["blocks"]:
            if name in STRIP:
                continue
            dx, dz = rot(bx - ax, bz - az, r)
            self.set(x + dx, y + by - ay, z + dz, name, br, owner=key)
        for bx, by, bz, name in p["fluids"]:
            dx, dz = rot(bx - ax, bz - az, r)
            self.b.pop((x + dx, y + by - ay, z + dz), None)
            self.fluid[(x + dx, y + by - ay, z + dz)] = ("vanilla", name)

    def footprint(self, key):
        """Cases (x, y, z) couvertes par une pièce vanilla, cases vides comprises (boîte englobante)."""
        prefab, x, y, z, r = key
        p = VANILLA[prefab]
        ax, ay, az = p["anchor"]
        pts = [(rot(bx - ax, bz - az, r), by - ay) for bx, by, bz, _, _ in p["blocks"]]
        if not pts:
            return set()
        xs = [q[0][0] for q in pts]
        zs = [q[0][1] for q in pts]
        ys = [q[1] for q in pts]
        return {(x + i, y + j, z + k) for i in range(min(xs), max(xs) + 1) for j in range(min(ys), max(ys) + 1)
                for k in range(min(zs), max(zs) + 1)}


def disc(R, x, z, salt=1):
    a = math.atan2(z, x)
    return math.hypot(x, z) <= R - 0.4 + 0.8 * math.sin(3 * a + salt) + 0.5 * math.sin(5 * a + 2 * salt)


def ground(S, R, P, pick, salt=1):
    """Sol de la place dans un disque bruité de rayon R, borné au carré aplani de demi-côté P."""
    for x in range(-P, P + 1):
        for z in range(-P, P + 1):
            if disc(R, x, z, salt=salt):
                S.set(x, 0, z, pick(x, z, math.hypot(x, z)))
                S.marks.setdefault("plaza", set()).add((x, z))


def scatter(S, cells, rate, choices, salt, cond=None):
    """Herbes et fleurs posées sur le sol de la place (jamais en l'air)."""
    for (x, z) in sorted(cells):
        if cond and not cond(x, z):
            continue
        if S.get(x, 1, z) is None and S.get(x, 0, z) and (x, 1, z) not in S.fluid and h(x, z, salt) < rate:
            S.set(x, 1, z, choices[int(h(x, z, salt + 1) * len(choices))])


def functional(S, board, deposit, banner, wide):
    """Places du tableau, du dépôt et de la bannière (posés par le Java, tournés vers le cœur). `wide` : seconde case du
    dépôt quand il devient un grand coffre (palier 2, Java village/Deposits), à côté du petit coffre sur l'axe du coffre
    (perpendiculaire au lacet), choisie hors des allées de la place pour ne pas gêner les villageois."""
    for key, (x, y, z) in (("board", board), ("deposit", deposit), ("banner", banner)):
        S.marks[key] = (x, y, z, facing(x, z))
        S.reserved.add((x, y, z))
    S.marks["deposit_wide"] = wide
    S.reserved.add(wide)
    S.reserved.add((0, 1, 0))
    S.reserved.add((0, 2, 0))
    for cell in S.reserved:
        if S.b.get(cell, (None, 0, None))[2] == "mod":
            del S.b[cell]


# ---------------------------------------------------------------- Kweebecs : la clairière du rejeton
KWEEBEC_TREE = {0: "Orbis/Trees/Oak/Stage_1/Oak_Stage1_001", 1: "Orbis/Trees/Oak/Stage_2/Oak_Stage2_001",
                2: "Orbis/Trees/Oak/Stage_2/Oak_Stage2_001", 3: "Orbis/Trees/Oak/Stage_3/Oak_Stage3_001"}
FLOWERS = ["Plant_Flower_Common_Pink", "Plant_Flower_Common_Yellow", "Plant_Flower_Common_White",
           "Plant_Flower_Tall_Yellow", "Plant_Flower_Common_Blue", "Plant_Flower_Bushy_Purple"]


def kweebec(tier):
    S = Scene()
    R, P = 9, 10
    TX, TZ = 0, -5

    def pick(x, z, d):
        spoke = (abs(z) <= 1 and abs(x) >= 3) or (abs(x) <= 1 and z >= 3)
        if d < 3.3 or spoke:
            return "Soil_Pathway" if h(x, z, 3) > 0.12 else "Soil_Leaves"
        if d < 5.6:
            v = h(x, z, 4)
            return "Soil_Pathway" if v < 0.45 else "Soil_Leaves" if v < 0.75 else "Soil_Grass_Deep"
        return "Soil_Grass_Deep" if h(x, z, 5) < 0.35 else "Soil_Grass"

    ground(S, R, P, pick)
    # Tertre de mousse du rejeton, racines, anneau de fleurs.
    for x in range(TX - 4, TX + 5):
        for z in range(TZ - 4, TZ + 5):
            d = math.hypot(x - TX, z - TZ)
            if d <= 2.2:
                S.set(x, 0, z, "Soil_Grass_Deep")
                S.set(x, 1, z, "Soil_Leaves" if d <= 1.5 else "Soil_Grass_Deep")
            elif d <= 3.4:
                S.set(x, 0, z, "Soil_Grass_Deep")
                if h(x, z, 21) < 0.55:
                    S.set(x, 1, z, FLOWERS[int(h(x, z, 22) * len(FLOWERS))])
    for (dx, dz) in ((2, 0), (-2, 1), (0, 2), (1, -2), (-1, -2)):
        S.set(TX + dx, 2, TZ + dz, "Wood_Oak_Roots")
    # Le rejeton grandit à chaque palier (arbres vanilla).
    S.paste(KWEEBEC_TREE[tier], TX, 2, TZ)
    if tier >= 1:
        S.paste(OAK + "Water_Pool/Kweebec_Oak_Water_Pool_005", 6, 0, -4)
    S.paste(OAK + "Lampposts/Kweebec_Oak_Lampposts_004", -6, 0, -6)
    S.paste(OAK + "Lampposts/Kweebec_Oak_Lampposts_006", 6, 0, 4)
    S.paste(OAK + "Seats/Small/Kweebec_Oak_Seats_Small_001", -6, 0, 5)
    if tier >= 2:
        S.paste(OAK + "Seats/Small/Kweebec_Oak_Seats_Small_003", 7, 0, 7, 1)
        S.paste(OAK + "Lampposts/Kweebec_Oak_Lampposts_001", -7, 0, 0)
    # Coin du tableau : deux poteaux, auvent de feuilles, lanterne suspendue.
    for px in (-6, -2):
        for y in (1, 2, 3):
            S.set(px, y, -2, "Wood_Oak_Trunk")
    for x in range(-7, -1):
        S.set(x, 4, -2, "Plant_Leaves_Oak")
    for x in (-6, -2):
        S.set(x, 4, -3, "Plant_Leaves_Oak")
    S.set(-4, 3, -2, "Furniture_Kweebec_Lantern_Ceiling")
    # Coin du dépôt : caisses, pommes, tabouret.
    S.set(4, 1, -2, "Furniture_Village_Crate")
    S.set(5, 1, -1, "Furniture_Village_Crate")
    S.set(5, 2, -1, "Plant_Fruit_Apple")
    S.set(2, 1, -3, "Furniture_Kweebec_Stool")
    functional(S, board=(-4, 1, -2), deposit=(3, 1, -1), banner=(0, 1, -2), wide=(3, 1, -2))
    S.marks["woodpile"] = (-3, 3)
    edge = {c for c in S.marks["plaza"] if math.hypot(*c) > 6.2}
    scatter(S, edge, 0.45, ["Plant_Grass_Sharp", "Plant_Grass_Sharp_Short", "Plant_Fern"] + FLOWERS[:3], 31)
    if tier >= 3:
        # Lianes du rejeton, accrochées sous son feuillage.
        for (x, z) in ((-3, -8), (3, -2), (-4, -4), (4, -7), (-2, -1), (2, -8)):
            for y in range(4, 12):
                if S.get(x, y + 1, z) == "Plant_Leaves_Oak" and S.get(x, y, z) is None:
                    S.set(x, y, z, "Plant_Vine_Hanging")
                    break
    return S


# ---------------------------------------------------------------- Trorks : l'arbre aux trophées
def trork(tier):
    S = Scene()
    R, P = 7, 8

    def pick(x, z, d):
        v = h(x, z, 6)
        if d < 2.6:
            return "Soil_Dirt_Burnt" if v < 0.55 else "Soil_Pathway"
        if d < 5.2:
            return "Soil_Pathway" if v < 0.45 else "Soil_Dirt" if v < 0.75 else "Soil_Gravel"
        return "Soil_Dirt" if v < 0.5 else "Soil_Grass"

    ground(S, R, P, pick, salt=3)
    # Anneau de grosses pierres, ouvert au sud, à l'est et à l'ouest.
    for i in range(28):
        a = i / 28 * 2 * math.pi
        x, z = round(7.3 * math.cos(a)), round(7.3 * math.sin(a))
        if abs(z) <= 1 or (abs(x) <= 2 and z > 0) or max(abs(x), abs(z)) > P:
            continue
        if h(x, z, 41) < 0.7:
            S.set(x, 0, z, "Rock_Stone")
            S.set(x, 1, z, "Rock_Stone")
            if h(x, z, 42) < 0.4:
                S.set(x, 2, z, "Rubble_Stone_Medium" if h(x, z, 43) < 0.5 else "Rock_Stone")
    # Arbre aux trophées vanilla (arbre mort, crânes et os pendus), braseros grossiers, pics d'os.
    S.paste(TRORK + "Warning/Trork_Warning_Trork_Warning_002", 1, 0, -4)
    S.set(-4, 1, -3, "Furniture_Crude_Brazier")
    S.set(4, 1, -3, "Furniture_Crude_Brazier")
    S.set(-2, 1, -2, "Deco_Bone_Spike")
    S.set(2, 1, -2, "Deco_Bone_Spike")
    # Fosse à feu vanilla au sud du cœur, rondins couchés pour s'asseoir.
    S.paste(TRORK + "Fireplace/Trork_Fireplace_001", 0, 0, 3)
    for z in (2, 3, 4):
        S.set(-3, 1, z, "Wood_Beech_Trunk", ALONG_Z)
    for x in (-1, 0, 1):
        S.set(x, 1, 6, "Wood_Beech_Trunk", ALONG_X)
    # Coin du dépôt : tonneaux, caisse, os.
    S.set(5, 1, -1, "Furniture_Ancient_Barrel")
    S.set(5, 1, 0, "Furniture_Ancient_Barrel")
    S.set(5, 2, -1, "Furniture_Village_Crate")
    S.set(4, 1, 1, "Deco_Bone_Pile")
    # Pieu du tableau, coiffé d'un crâne.
    S.set(-5, 1, -1, "Wood_Beech_Trunk")
    S.set(-5, 2, -1, "Deco_Bone_Skulls", EAST)
    if tier >= 1:
        for z in (2, 3, 4):
            S.set(3, 1, z, "Wood_Beech_Trunk", ALONG_Z)
    if tier >= 2:
        # Séchoir à viande vanilla (cage et chaînes comprises).
        S.paste(TRORK + "Misc/Large/Trork_Misc_Large_002", 5, 0, 5)
    if tier >= 3:
        for (x, z) in ((-6, 3), (-3, -6), (3, -6)):
            S.set(x, 1, z, "Furniture_Crude_Brazier")
    functional(S, board=(-4, 1, -1), deposit=(4, 1, -1), banner=(0, 1, -1), wide=(4, 1, 0))
    S.marks["woodpile"] = (-2, 4)
    scatter(S, S.marks["plaza"], 0.08, ["Rubble_Stone", "Deco_Bone_Pile", "Rubble_Basalt"], 51,
            cond=lambda x, z: math.hypot(x, z) > 4.5)
    return S


# ---------------------------------------------------------------- Feran : le bassin de l'oasis
PALMS = {0: "Orbis/Trees/Palm/Stage_2/Palm_Stage2_001", 1: "Orbis/Trees/Palm/Stage_3/Palm_Stage3_002",
         2: "Orbis/Trees/Palm/Stage_3/Palm_Stage3_002", 3: "Orbis/Trees/Palm/Stage_4/Palm_Stage4_001"}


def pillar_torch(S, x, z, height=2):
    """Colonne de grès (base, fûts, chapiteau = base retournée) coiffée d'une torche feran."""
    S.set(x, 1, z, "Rock_Sandstone_Brick_Pillar_Base")
    for y in range(2, 1 + height):
        S.set(x, y, z, "Rock_Sandstone_Brick_Pillar_Middle")
    S.set(x, 1 + height, z, "Rock_Sandstone_Brick_Pillar_Base", 8)
    S.set(x, 2 + height, z, "Furniture_Feran_Torch")


def feran(tier):
    S = Scene()
    R, P = 8, 9
    BZ = -4

    def pick(x, z, d):
        if d < 5.2:
            return "Rock_Sandstone_Brick_Smooth" if int(d) % 2 else "Rock_Sandstone_Brick"
        if d < 6.3:
            return "Rock_Sandstone_Cobble" if h(x, z, 7) < 0.6 else "Soil_Gravel_Sand"
        return "Soil_Sand" if h(x, z, 8) < 0.7 else "Soil_Gravel_Sand"

    ground(S, R, P, pick, salt=5)
    # Bassin rond : fond de briques, eau, margelle de demi-briques.
    for x in range(-4, 5):
        for z in range(BZ - 4, BZ + 5):
            d = math.hypot(x, z - BZ)
            if d <= 2.3:
                S.set(x, -1, z, "Rock_Sandstone_Brick")
                S.water(x, 0, z)
            elif d <= 3.3:
                S.set(x, 0, z, "Rock_Sandstone_Brick")
                S.set(x, 1, z, "Rock_Sandstone_Brick_Half")
    pillar_torch(S, -3, BZ - 2)
    pillar_torch(S, 3, BZ - 2)
    # Colonne ornée au nord du bassin : la bannière (statue du vent) la coiffe.
    S.set(0, 1, BZ - 3, "Rock_Sandstone_Brick_Ornate")
    # Palmiers vanilla qui grandissent avec les paliers.
    S.paste(PALMS[tier], -5, 1, -7)
    S.paste(PALMS[max(0, tier - 1)], 5, 1, -6)
    if tier >= 2:
        S.paste(PALMS[tier], -6, 1, 4)
    # Auvent de toile au-dessus du tableau, sur poteaux de bois sec.
    for px in (-6, -3):
        for pz in (-1, 1):
            for y in (1, 2, 3):
                S.set(px, y, pz, "Wood_Dry_Trunk")
    for x in range(-6, -2):
        for z in (-1, 0, 1):
            S.set(x, 4, z, "Cloth_Roof_Orange_Flat")
    # Coin du dépôt : jarres, jardinière, tabourets.
    S.set(5, 1, 0, "Furniture_Feran_Pot")
    S.set(5, 1, 1, "Furniture_Feran_Pot_Secondary")
    S.set(5, 1, 2, "Furniture_Feran_Planter")
    for (x, z) in ((2, 3), (-2, 3), (3, 4)):
        S.set(x, 1, z, "Furniture_Feran_Stool")
    if tier >= 3:
        pillar_torch(S, -2, 6, 1)
        pillar_torch(S, 2, 6, 1)
    functional(S, board=(-4, 1, 0), deposit=(4, 1, 1), banner=(0, 2, BZ - 3), wide=(4, 1, 2))
    S.marks["woodpile"] = (-2, 5)
    edge = {c for c in S.marks["plaza"] if math.hypot(*c) > 6.4}
    scatter(S, edge, 0.3, ["Plant_Grass_Arid", "Plant_Bush_Arid", "Plant_Grass_Arid_Short"], 61)
    return S


# ---------------------------------------------------------------- Renoncés : le foyer des repentis
def renonce(tier):
    S = Scene()
    R, P = 8, 9

    def pick(x, z, d):
        v = h(x, z, 11)
        if d < 5.5:
            return "Rock_Slate_Cobble" if v < 0.5 else "Soil_Pebbles_Frozen" if v < 0.8 else "Soil_Gravel"
        return "Soil_Snow" if v < 0.8 else "Soil_Pebbles_Frozen"

    ground(S, R, P, pick, salt=7)
    # Foyer vanilla des Outlanders (fosse à feu, bancs, appentis de peaux) au nord du cœur.
    S.paste("Npc/Outlander/Misc/Outlander_Misc_003", 0, -1, -3)
    # Bûcher de sapin couché, lanterne de bûcheron.
    for (x, y, z) in ((5, 1, 6), (5, 1, 7), (5, 2, 6), (5, 2, 7)):
        S.set(x, y, z, "Wood_Fir_Trunk", ALONG_X)
    S.set(-5, 1, 6, "Furniture_Lumberjack_Lantern")
    if tier >= 1:
        S.paste("Orbis/Trees/Fir_Snow/Stage_2/Fir_Snow_Stage2_001", -7, 1, 5)
    if tier >= 2:
        S.paste("Npc/Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", -8, 0, -2)
        S.paste("Npc/Outlander/Braziers/Outlander_Braziers_Npc_Outlander_Brazier_001", 8, 0, -2)
    if tier >= 3:
        S.paste("Orbis/Trees/Fir_Snow/Stage_3/Fir_Snow_Stage3_001", -8, 1, -7)
    functional(S, board=(-3, 1, 6), deposit=(3, 1, 6), banner=(0, 1, 7), wide=(4, 1, 6))
    S.marks["woodpile"] = (2, 7)
    scatter(S, {c for c in S.marks["plaza"] if c[1] > 4}, 0.15, ["Plant_Grass_Winter_Short", "Rubble_Slate"], 71)
    return S


# ---------------------------------------------------------------- Slothians : le jardin de veille
def slothian(tier):
    S = Scene()
    R, P = 8, 9

    def pick(x, z, d):
        v = h(x, z, 13)
        if d < 4.5:
            return "Rock_Basalt_Cobble" if (x + z) % 2 == 0 or v < 0.3 else "Rock_Basalt_Brick_Smooth"
        return "Soil_Mud_Dry" if v < 0.6 else "Soil_Grass"

    ground(S, R, P, pick, salt=9)
    # Sanctuaire slothian vanilla au nord (sans son bloc de spawn).
    S.paste("Monuments/Incidental/Slothian/Land/Shrine/Incidental_Slothian_Shrine_Slothian_Shrine_001", 0, 0, -4)
    # Bosquets de bambou (tiges vanilla, feuillage au sommet), plus hauts à chaque palier.
    for (bx, bz) in ((-6, -2), (6, -3)) + (((-5, 5), (5, 5)) if tier >= 2 else ()):
        for dx, dz in ((0, 0), (1, 0), (0, 1)):
            top = 4 + int(h(bx + dx, bz + dz, 81) * 3) + tier
            for y in range(1, top):
                S.set(bx + dx, y, bz + dz, "Wood_Bamboo_Trunk")
            S.set(bx + dx, top, bz + dz, "Plant_Leaves_Bamboo")
    S.set(-3, 1, 3, "Furniture_Jungle_Planter")
    S.set(3, 1, 3, "Furniture_Jungle_Planter")
    if tier >= 3:
        for (x, z) in ((-4, 1), (4, 1)):
            S.set(x, 1, z, "Rock_Basalt_Brick_Pillar_Base")
            S.set(x, 2, z, "Furniture_Jungle_Torch")
    functional(S, board=(-2, 1, 2), deposit=(2, 1, 2), banner=(0, 1, 4), wide=(3, 1, 2))
    S.marks["woodpile"] = (-3, 5)
    return S


# Plan de village -> (peuple, composition).
HEARTS = {
    "Kweebec_Oak": ("Kweebec", kweebec),
    "Trork_Camp": ("Trork", trork),
    "Feran_Oasis": ("Feran", feran),
    "Renonce_Givre": ("Renonce", renonce),
    "Slothian_Monastere": ("Slothian", slothian),
}
PLAZA = {"Kweebec_Oak": 10, "Trork_Camp": 8, "Feran_Oasis": 9, "Renonce_Givre": 9, "Slothian_Monastere": 9}


def pieces_needed():
    """Prefabs vanilla utilisés (pour tools/extract_vanilla_prefabs.py)."""
    seen = set()

    class Probe(Scene):
        def paste(self, prefab, x, y, z, r=0):
            seen.add(prefab)

    for _, compose in HEARTS.values():
        for t in TIERS:
            g = compose.__globals__
            old = g["Scene"]
            g["Scene"] = Probe
            try:
                compose(t)
            except Exception:
                pass
            finally:
                g["Scene"] = old
    return sorted(seen)


def check(layout_id, S, tier, known, errors):
    P = PLAZA[layout_id]
    for (x, y, z), (name, r, owner) in S.b.items():
        if owner == "mod":
            base = name.lstrip("*")
            if base not in known:
                errors.append(f"{layout_id} T{tier} : bloc vanilla inconnu {name} en {x} {y} {z}")
            if base in MULTI_CELL:
                errors.append(f"{layout_id} T{tier} : {name} occupe plusieurs cases, à poser via un prefab vanilla")
            if max(abs(x), abs(z)) > P + 1:
                errors.append(f"{layout_id} T{tier} : {name} en {x} {z} hors de la place (demi-côté {P})")
    for cell in S.reserved:
        v = S.b.get(cell)
        if v is not None:
            errors.append(f"{layout_id} T{tier} : case réservée {cell} occupée par {v[0]}")
        if cell in S.fluid:
            errors.append(f"{layout_id} T{tier} : case réservée {cell} dans l'eau")
    for key in ("board", "deposit", "banner"):
        x, y, z, _ = S.marks[key]
        if S.b.get((x, y - 1, z)) is None:
            errors.append(f"{layout_id} T{tier} : {key} en {x} {y} {z} sans appui")
    # Grand coffre du dépôt : case voisine sur l'axe du coffre (le lacet le tourne de face vers le cœur), avec appui,
    # hors des grandes allées de la place (choisie à la main, voir les appels de functional).
    dx, dy, dz, yaw = S.marks["deposit"]
    wx, wy, wz = S.marks["deposit_wide"]
    side = rot(-1, 0, yaw)
    if wy != dy or (wx - dx, wz - dz) not in (side, (-side[0], -side[1])):
        errors.append(f"{layout_id} : seconde case du dépôt {wx} {wy} {wz} pas à côté du coffre (axe {side})")
    under = S.get(wx, wy - 1, wz)
    if under is None:
        errors.append(f"{layout_id} T{tier} : seconde case du dépôt {wx} {wy} {wz} sans appui")
    if (wx, wy, wz) == (0, 1, 0):
        errors.append(f"{layout_id} : seconde case du dépôt sur le cœur")


def steps(layout_id, compose, errors, known):
    prev = None
    out = []
    fluids_out = {}
    for t in TIERS:
        S = compose(t)
        check(layout_id, S, t, known, errors)
        new_pieces = [p for p in S.pieces if prev is None or p not in prev.pieces]
        touched = set()
        for p in new_pieces:
            touched |= S.footprint(p)
        sets, clears = [], []
        for cell, (name, r, owner) in sorted(S.b.items()):
            if owner != "mod" or cell in S.reserved:
                continue
            before = prev.b.get(cell) if prev else None
            if before is None or before[0] != name or before[1] != r or cell in touched or before[2] != "mod":
                sets.append(f"{cell[0]} {cell[1]} {cell[2]} {r} {name}")
        if prev:
            for cell, (name, r, owner) in sorted(prev.b.items()):
                if cell not in S.b and cell not in S.fluid:
                    clears.append(f"{cell[0]} {cell[1]} {cell[2]} {name}")
        # Spawners des pièces vanilla : retirés après collage.
        for p in new_pieces:
            prefab, px, py, pz, pr = p
            v = VANILLA[prefab]
            ax, ay, az = v["anchor"]
            for bx, by, bz, name, _ in v.get("stripped", []):
                dx, dz = rot(bx - ax, bz - az, pr)
                clears.append(f"{px + dx} {py + by - ay} {pz + dz} {name}")
        mod_fluids = {c: n for c, n in S.fluid.items() if isinstance(n, str)}
        prev_fluids = {c for c, n in prev.fluid.items() if isinstance(n, str)} if prev else set()
        fluid_prefab = ""
        new_fluids = {c: n for c, n in mod_fluids.items() if c not in prev_fluids}
        # Le sol aplani sous l'eau du mod est retiré avant de poser le fluide.
        for (x, y, z) in sorted(new_fluids):
            sets.append(f"{x} {y} {z} 0 Empty")
        if new_fluids:
            fluid_prefab = f"{FLUID_PREFIX}{layout_id}_T{t}_Fluids"
            fluids_out[f"{layout_id}_T{t}_Fluids"] = new_fluids
        out.append({
            "Tier": t,
            "Pieces": [{"Prefab": p[0], "X": p[1], "Y": p[2], "Z": p[3], "Rotation": p[4]} for p in new_pieces],
            "Set": sets,
            "Clear": clears,
            "Fluids": fluid_prefab,
        })
        prev = S
    return out, fluids_out, prev


def fluid_prefab(cells):
    """Prefab du mod qui ne porte que des fluides (ancre en 0, 0, 0 = surface de la place)."""
    return {
        "version": 8,
        "blockIdVersion": 11,
        "anchorX": 0,
        "anchorY": 0,
        "anchorZ": 0,
        "blocks": [],
        "fluids": [{"x": x, "y": y, "z": z, "name": n, "level": 1} for (x, y, z), n in sorted(cells.items())],
        "entities": [],
    }


def load_vanilla(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    prefabs = data.get("prefabs", data)
    for name, p in prefabs.items():
        p["stripped"] = [b for b in p["blocks"] if b[3] in STRIP]
        VANILLA[name] = p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vanilla", help="JSON des prefabs vanilla (tools/extract_vanilla_prefabs.py)")
    parser.add_argument("--preview", type=Path, help="dossier des aperçus PNG")
    parser.add_argument("--palette", type=Path, help="palette des blocs pour les aperçus (extract_vanilla_prefabs.py --palette)")
    parser.add_argument("--list", action="store_true", help="liste les prefabs vanilla utilisés et s'arrête")
    args = parser.parse_args()
    if args.list:
        print("\n".join(pieces_needed()))
        return
    load_vanilla(args.vanilla)
    known = {l.strip().lstrip("*") for l in BLOCK_IDS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
    errors = []
    doc = {}
    FLUID_DIR.mkdir(parents=True, exist_ok=True)
    for old in FLUID_DIR.glob("*.prefab.json"):
        old.unlink()
    for layout_id, (people, compose) in HEARTS.items():
        st, fluids, last = steps(layout_id, compose, errors, known)
        for name, cells in fluids.items():
            (FLUID_DIR / f"{name}.prefab.json").write_text(json.dumps(fluid_prefab(cells), indent=2) + "\n", encoding="utf-8")
        marks = last.marks
        doc[layout_id] = {
            "People": people,
            "PlazaRadius": PLAZA[layout_id],
            "Board": list(marks["board"]),
            "Deposit": list(marks["deposit"]),
            "DepositWide": list(marks["deposit_wide"]),
            "Banner": list(marks["banner"]),
            "Woodpile": list(marks["woodpile"]),
            "Steps": st,
        }
        n = sum(len(s["Set"]) for s in st)
        print(f"{layout_id} : {n} blocs posés, {sum(len(s['Pieces']) for s in st)} pièces vanilla, "
              f"{sum(len(s['Clear']) for s in st)} retraits")
    for e in errors:
        print("ERREUR", e)
    OUT_JSON.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT_JSON.relative_to(ROOT)} écrit")
    if args.preview:
        import heart_render
        heart_render.sheets(HEARTS, args.palette, args.preview)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
