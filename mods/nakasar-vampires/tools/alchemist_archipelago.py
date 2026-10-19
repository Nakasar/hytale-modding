"""L'archipel de la Tour de l'Alchimiste, à l'échelle du donjon vanilla Deepworks (environ 500 × 600 blocs) : les îles
du parcours, les ponts qui les relient et les îlots de décor. Utilisé par generate_alchemist_tower.py.

Parcours (Kevin, 19 octobre 2026 : « archipel en étapes ») : île d'arrivée, pont, Jardins des Alambics, pont coudé,
Ruines du premier laboratoire (point de contrôle), pont coudé, parvis de la tour. Chaque île du parcours est fermée par
un mur de 2 blocs, ouvert seulement là où arrivent les ponts ; les ponts ont des parapets de 2 blocs.

Repère : x vers l'est, z vers le sud ; les positions (x, z) sont celles du monde, le sol des îles est à GROUND_Y.
"""
import math
import random

import generate_prefabs as pf

AIR = pf.AIR
GROUND_Y = 100  # première couche d'air au-dessus du sol des îles (generate_alchemist_tower.GROUND_Y)

ARRIVAL = {"center": (0, 0), "radius": 24.0, "flat": 17.0}
GARDENS = {"center": (0, -140), "radius": 46.0, "flat": 38.0, "wall": 35}
RUINS = {"center": (-70, -290), "radius": 40.0, "flat": 32.0, "wall": 29}
TOWER = {"center": (0, -480), "radius": 100.0, "flat": 90.0}

BRIDGE_HALF = 3  # pont de 7 blocs de large (alchemist_tower.BRIDGE_HALF)
PLAZA_EDGE = 10  # le parapet du parvis d'arrivée est à 10 blocs du point d'apparition


def _gate(island, direction):
    """Point (x, z) au milieu de la porte du mur d'une île du parcours, côté `direction` (N, S, E, O)."""
    (cx, cz), r = island["center"], island["wall"]
    return {"N": (cx, cz - r), "S": (cx, cz + r), "E": (cx + r, cz), "O": (cx - r, cz)}[direction]


# Ponts : lignes brisées à angles droits, du départ à l'arrivée. Le dernier s'arrête sur la ligne de parapet du parvis
# de la tour (z = 80 dans le repère du prefab de la tour, alchemist_tower.COURT_END + 1).
BRIDGES = [
    [(0, -PLAZA_EDGE), _gate(GARDENS, "S")],
    [_gate(GARDENS, "N"), (0, -290), _gate(RUINS, "E")],
    [_gate(RUINS, "N"), (-70, -350), (0, -350), (0, TOWER["center"][1] + 81)],
]
ROUTE_ISLANDS = [("Gardens", GARDENS, ("S", "N")), ("Ruins", RUINS, ("E", "N"))]

FLOOR = [("Rock_Marble_Brick", 5), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
PARAPET, PARAPET_TOP = "Rock_Marble_Brick", "Rock_Marble_Brick_Wall"
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
GLASS = "Nakasar_Stained_Glass_Violet"
STATUE = "Furniture_Temple_Light_Statue"
CRYSTALS = ["Rock_Crystal_Purple_Large", "Rock_Crystal_Purple_Medium", "Rock_Crystal_Green_Medium",
            "Rock_Crystal_Green_Large", "Rock_Crystal_Pink_Medium"]
PLANTS = ["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green", "Plant_Flower_Orchid_Purple",
          "Plant_Flower_Tall_Cyan", "Plant_Grass_Lush"]


def parapet(p, x, z, y=0):
    p.set(x, y, z, PARAPET)
    p.set(x, y + 1, z, PARAPET_TOP)


# --- ponts ------------------------------------------------------------------------------------

def _segment_cells(a, b, half):
    (x0, z0), (x1, z1) = a, b
    for x in range(min(x0, x1) - half, max(x0, x1) + half + 1):
        for z in range(min(z0, z1) - half, max(z0, z1) + half + 1):
            yield x, z


def bridges_prefab(seed):
    """Tous les ponts du parcours, dans le repère du monde (origine posée en (0, GROUND_Y, 0))."""
    p = pf.Prefab(seed)
    deck, ends = set(), []
    for line in BRIDGES:
        for a, b in zip(line, line[1:]):
            deck.update(_segment_cells(a, b, BRIDGE_HALF))
        # Les deux bouts restent ouverts : on retire le débord du tablier au-delà des extrémités.
        for end, nxt in ((line[0], line[1]), (line[-1], line[-2])):
            dx, dz = (end[0] > nxt[0]) - (end[0] < nxt[0]), (end[1] > nxt[1]) - (end[1] < nxt[1])
            ends.append((end, (dx, dz)))
    for (ex, ez), (dx, dz) in ends:
        for k in range(1, BRIDGE_HALF + 1):
            for w in range(-BRIDGE_HALF - 1, BRIDGE_HALF + 2):
                deck.discard((ex + dx * k + dz * w, ez + dz * k + dx * w))

    def beyond_end(x, z):
        for (ex, ez), (dx, dz) in ends:
            if (x - ex) * dx + (z - ez) * dz >= 1 and abs((x - ex) * dz - (z - ez) * dx) <= BRIDGE_HALF + 1:
                return True
        return False

    rails = set()
    for x, z in deck:
        for ddx in (-1, 0, 1):
            for ddz in (-1, 0, 1):
                n = (x + ddx, z + ddz)
                if n not in deck and not beyond_end(*n):
                    rails.add(n)
    for x, z in deck:
        p.set(x, -1, z, TRIM if (x + z) % 9 == 0 and (x, z) not in rails else p.pick(FLOOR))
        p.set(x, -2, z, PARAPET)
        for y in range(0, 6):
            p.set(x, y, z, AIR)
    for x, z in rails:
        p.set(x, -1, z, PARAPET)
        p.set(x, -2, z, PARAPET)
        parapet(p, x, z)
        if (x * 7 + z * 3) % 10 == 0:
            p.set(x, 2, z, "Deco_Lantern")
    # Piles qui pendent sous le tablier, tous les 12 blocs.
    for x, z in deck:
        if x % 12 == 0 and z % 12 == 0:
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    if (x + dx, z + dz) in deck:
                        p.fill(x + dx, -6 + abs(dx) + abs(dz), z + dz, x + dx, -3, z + dz,
                               "Rock_Marble_Brick_Pillar_Middle")
    return p


# --- îles du parcours -------------------------------------------------------------------------

def _walled_island(p, island, gates):
    """Mur de 2 blocs en cercle, ouvert aux portes ; dallage des allées d'une porte au centre."""
    (cx, cz), r = island["center"], island["wall"]
    gate_points = [_gate(island, g) for g in gates]
    open_cells = set()
    for gx, gz in gate_points:
        for x in range(gx - BRIDGE_HALF, gx + BRIDGE_HALF + 1):
            for z in range(gz - BRIDGE_HALF, gz + BRIDGE_HALF + 1):
                open_cells.add((x, z))
    for x in range(-r - 2, r + 3):
        for z in range(-r - 2, r + 3):
            d = math.hypot(x, z)
            if r - 0.5 <= d < r + 0.6 and (x, z) not in open_cells:
                parapet(p, x, z)
                a = math.degrees(math.atan2(z, x)) % 360
                if int(a) % 18 == 0:
                    p.set(x, 2, z, "Deco_Lantern")
    # Allées : de chaque porte au centre, 5 de large, liseré d'or.
    for gx, gz in gate_points:
        lx, lz = gx - cx, gz - cz
        steps = max(abs(lx), abs(lz))
        for i in range(steps + 1):
            px, pz = round(lx * i / steps), round(lz * i / steps)
            for w in range(-2, 3):
                x, z = (px + w, pz) if lx == 0 else (px, pz + w)
                p.set(x, -1, z, TRIM if abs(w) == 2 else p.pick(FLOOR))
                for y in range(0, 4):
                    p.set(x, y, z, AIR)
    return gate_points


def gardens_prefab(seed):
    """Jardins des Alambics : fontaine d'élixir au centre, plates-bandes de plantes lumineuses, chaudrons, émanations."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    _walled_island(p, GARDENS, ("S", "N"))
    # Fontaine : bassin cerclé d'or, élixir vert, alambic de verre au milieu.
    for x in range(-7, 8):
        for z in range(-7, 8):
            d = math.hypot(x, z)
            if d < 5.5:
                p.set(x, -1, z, "Rock_Crystal_Green_Block")
                for y in range(0, 4):
                    p.set(x, y, z, AIR)
            elif d < 6.5:
                p.set(x, -1, z, GOLD)
                p.set(x, 0, z, GOLD)
            elif d < 7.5:
                p.set(x, -1, z, TRIM)
    for y in range(0, 9):
        for x in range(-1, 2):
            for z in range(-1, 2):
                p.set(x, y, z, GLASS if (x, z) != (0, 0) else "Rock_Crystal_Green_Block")
    p.set(0, 9, 0, "Rock_Gold_Brick_Ornate")
    p.set(0, 10, 0, "Nakasar_Tower_Emanation_Spiral")
    # Plates-bandes en anneau, coupées par les allées.
    for x in range(-30, 31):
        for z in range(-30, 31):
            d = math.hypot(x, z)
            if abs(x) <= 3:  # allée nord-sud
                continue
            if 12 <= d < 15 or 22 <= d < 25:
                p.set(x, -1, z, "Soil_Grass_Full")
                p.set(x, 0, z, rng.choice(PLANTS) if rng.random() < 0.7 else AIR)
            elif 15 <= d < 22 and (x + z) % 2 == 0 and rng.random() < 0.05:
                p.set(x, 0, z, "Alchemy_Cauldron")
    for a in range(20, 360, 40):
        x, z = round(28 * math.cos(math.radians(a))), round(28 * math.sin(math.radians(a)))
        if abs(x) > 4:
            p.set(x, 0, z, rng.choice(CRYSTALS))
            p.set(x, 3, z, "Nakasar_Tower_Emanation_Motes")
    return p


def ruins_prefab(seed):
    """Ruines du premier laboratoire : tour écroulée, colonnes brisées, cristaux ; point de contrôle à la porte nord."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    gates = _walled_island(p, RUINS, ("E", "N"))
    # Tour écroulée à l'ouest : cylindre de 8 de rayon, sommet déchiqueté, portes.
    tx, tz = -12, 6
    for x in range(-9, 10):
        for z in range(-9, 10):
            d = math.hypot(x, z)
            if 7 <= d < 8.5:
                a = math.degrees(math.atan2(z, x)) % 360
                if 80 <= a <= 100 or 260 <= a <= 280:
                    continue  # brèches
                top = 4 + int(10 * abs(math.sin(math.radians(a * 2.3))) + rng.random() * 4)
                for y in range(0, top):
                    p.set(tx + x, y, tz + z, rng.choice(["Rock_Marble_Brick", "Rock_Marble_Cobble",
                                                          "Rock_Stone_Mossy"]))
            elif d < 7:
                p.set(tx + x, -1, tz + z, rng.choice(["Rock_Marble_Cobble", "Rock_Stone_Mossy", "Soil_Grass_Full"]))
    # Colonnes brisées en cercle.
    for a in range(0, 360, 30):
        x, z = round(18 * math.cos(math.radians(a))), round(18 * math.sin(math.radians(a)))
        if abs(x) <= 4 and z < 0 or abs(z) <= 4 and x > 0:
            continue  # allées
        h = rng.randint(2, 8)
        p.set(x, 0, z, "Rock_Gold_Brick_Pillar_Base")
        for y in range(1, h):
            p.set(x, y, z, "Rock_Marble_Brick_Pillar_Middle")
    for _ in range(14):
        a, r = rng.uniform(0, 360), rng.uniform(8, 26)
        x, z = round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))
        if abs(x) <= 3 or abs(z) <= 3 or p.get(x, 0, z) not in (None, AIR):
            continue
        p.set(x, 0, z, rng.choice(CRYSTALS))
    for x, z in ((10, 10), (-20, -12), (6, -20)):
        p.set(x, 2, z, "Nakasar_Tower_Emanation_Mist")
    # Point de contrôle devant la porte nord.
    gx, gz = gates[1][0] - RUINS["center"][0], gates[1][1] - RUINS["center"][1]
    spot = (gx, 0, gz + 6)
    p.set(gx + 4, -1, gz + 6, "Rock_Gold_Brick_Ornate")
    p.set(gx + 4, 0, gz + 6, STATUE, pf.WEST)
    return p, spot


# --- îlots de décor ---------------------------------------------------------------------------

# Arbres fantastiques du jeu (dossiers de Server/Prefabs d'Assets.zip, lus le 2026-10-19), par taille d'îlot.
BIG_TREES = ["Trees/Jungle_Crystal/Stage_3", "Trees/Fig_Blue/Stage_3", "Trees/Zone5/Aqua/Large"]
MEDIUM_TREES = ["Trees/Azure/Stage_3", "Trees/Spiral/Stage_3", "Trees/Wisteria/Stage_2"]
SMALL_TREES = ["Trees/Crystal/Stage_3", "Trees/Silver/Stage_3", "Trees/Willow/Stage_3"]


def _segment_distance(px, pz, a, b):
    (x0, z0), (x1, z1) = a, b
    dx, dz = x1 - x0, z1 - z0
    t = 0.0 if dx == dz == 0 else max(0.0, min(1.0, ((px - x0) * dx + (pz - z0) * dz) / (dx * dx + dz * dz)))
    return math.hypot(px - (x0 + t * dx), pz - (z0 + t * dz))


def islets(seed=19, count=24):
    """Îlots (centre du dessus (x, y, z), rayon, arbre), loin du parcours et des grandes îles."""
    rng = random.Random(seed)
    big = [(ARRIVAL["center"], ARRIVAL["radius"]), (GARDENS["center"], GARDENS["radius"]),
           (RUINS["center"], RUINS["radius"]), (TOWER["center"], TOWER["radius"])]
    out = []
    tries = 0
    while len(out) < count and tries < 20000:
        tries += 1
        x, z = rng.uniform(-260, 260), rng.uniform(-640, 70)
        r = rng.choice([8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 24, 28])
        y = round(rng.uniform(88, 236 if r < 20 else 190))
        if any(math.hypot(x - c[0], z - c[1]) < rr + r + 28 for c, rr in big):
            continue
        if any(_segment_distance(x, z, a, b) < r + 26 for line in BRIDGES for a, b in zip(line, line[1:])):
            continue
        if any(math.hypot(x - o[0][0], z - o[0][2]) < r + o[1] + 22 for o in out):
            continue
        trees = BIG_TREES if r >= 20 else MEDIUM_TREES if r >= 12 else SMALL_TREES
        out.append(((round(x), y, round(z)), float(r), rng.choice(trees)))
    return out
