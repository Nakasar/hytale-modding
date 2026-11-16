#!/usr/bin/env python3
"""Sentiers et décor des villages du mod Peuples d'Orbis (Kevin, 2026-11-16 : « un village qui s'organise de manière
plus agréable et vivante, avec des décorations, des petits sentiers, etc. entre les bâtiments »).

Appelé par generate_village_layouts.build (donc aussi par generate_zones.py) : ajoute au plan une liste `Streets` de
pas par palier, que le Java (village/VillageStreets) pose sur le sol NATUREL du village quand le palier est atteint
(et rattrape sur les villages déjà bâtis) :

- `Paths` : « x z Bloc » — cases de sentier. Chaque bâtiment (et terrain E1/E2) est relié à la place, ou au sentier
  le plus proche déjà tracé, par un A* qui contourne les emprises : les bâtiments d'un palier se branchent sur le
  réseau des paliers précédents, ce qui donne un réseau en arbre plutôt que des rayons. La ligne est lissée (Chaikin)
  puis épaissie (3 de large pour les axes du campement, 2 ensuite), bords effilochés pour rester organique.
- `Decor` : « x z rotation P|B Id » — P = petit prefab VANILLA collé (règle n° 2 d'AGENTS.md : lampadaires, bancs et
  petits jardins des villages Kweebec Oak), B = bloc vanilla posé sur le sol (meubles et plantes du peuple).
  Lumières le long des sentiers, un ou deux objets près de chaque porte, bancs aux croisements, et petits coins
  (fleurs, pots, os...) dans les espaces libres entre les bâtiments.

Palier d'un élément de décor : le plus haut palier des emprises à moins de TALUS blocs (le terrassement d'un bâtiment
à venir remodèle le sol jusque-là), au moins celui du sentier qu'il borde.

Toutes les positions sont relatives au cœur ; le Java prend la hauteur du sol réel à chaque case.
"""
import heapq
import math
import random
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
NPC = "Npc/Kweebec/Oak/"

# Terrassement d'une emprise (Java VillageBuilder/Chantiers : MARGIN 2 + 2 * BLEND 4) : le sol y bouge quand le
# bâtiment est collé, donc le décor voisin attend ce palier-là.
TALUS = 10
# Écart des chemins aux murs pour le routage (la case devant la porte est libérée).
WALL = 1

# Style par peuple. `path` : bloc du sentier, `speck` : touches mêlées au sentier (proportion), `light` : lumière le
# long des sentiers (prefabs P ou blocs B), `door` : objets près des portes, `bench` : banc aux croisements,
# `pocket` : petits coins entre les bâtiments (liste de « grappes » : (poids, [éléments])).
STYLES = {
    "Kweebec": {
        "path": "Soil_Pathway", "speck": ("Soil_Gravel_Mossy", 0.07),
        "light": [("P", NPC + f"Lampposts/Kweebec_Oak_Lampposts_{i:03d}") for i in range(1, 10)],
        "door": [("B", "Furniture_Village_Crate"), ("B", "Furniture_Kweebec_Stool"), ("B", "Plant_Flower_Bushy_Purple"),
                 ("B", "Plant_Flower_Tall_Yellow"), ("B", "Plant_Fern")],
        "bench": [("P", NPC + f"Seats/Small/Kweebec_Oak_Seats_Small_{i:03d}") for i in (1, 2, 3)],
        "pocket": [
            (6, "garden"),  # un des 88 petits jardins vanilla Kweebec_Oak_Garden_Small_0xx
            (3, ["Plant_Flower_Common_Yellow", "Plant_Flower_Common_White", "Plant_Flower_Common_Pink",
                 "Plant_Flower_Common_Blue", "Plant_Flower_Bushy_Purple", "Plant_Fern", "Plant_Grass_Sharp"]),
            (1, ["Plant_Bush", "Plant_Bush_Green", "Plant_Fern", "Plant_Flower_Tall_Yellow"]),
        ],
    },
    "Trork": {
        "path": "Soil_Dirt", "speck": ("Soil_Gravel", 0.12),
        "light": [("B", "Furniture_Crude_Torch")],
        "door": [("B", "Furniture_Ancient_Barrel"), ("B", "Deco_Bone_Pile"), ("B", "Furniture_Village_Crate"),
                 ("B", "Plant_Hay_Bundle")],
        "bench": [("B", "Deco_Campfire_Off")],
        "pocket": [
            (3, ["Deco_Bone_Pile", "Deco_Bone_Skulls", "Deco_Bone_Spike", "Rubble_Stone_Medium"]),
            (2, ["Furniture_Ancient_Barrel", "Furniture_Village_Crate", "Plant_Hay_Bundle", "Deco_Trash_Pile_Small"]),
            (2, ["Rubble_Stone", "Rubble_Stone_Medium", "Rubble_Basalt", "Plant_Bush_Bramble"]),
        ],
    },
    "Feran": {
        "path": "Soil_Gravel_Sand", "speck": ("Soil_Sand", 0.15),
        "light": [("B", "Furniture_Feran_Torch_Tall")],
        "door": [("B", "Furniture_Feran_Pot"), ("B", "Furniture_Feran_Pot_Secondary"), ("B", "Furniture_Feran_Planter")],
        "bench": [("B", "Furniture_Feran_Bench")],
        "pocket": [
            (3, ["Plant_Bush_Arid", "Plant_Bush_Arid_Palm", "Plant_Grass_Arid", "Plant_Grass_Arid_Short", "Plant_Fern_Arid"]),
            (2, ["Furniture_Feran_Pot", "Furniture_Feran_Pot_Secondary", "Furniture_Feran_Planter", "Plant_Bush_Arid_Red"]),
            (1, ["Deco_Bone_Skulls_Feran", "Deco_Bone_Ribs_Feran", "Plant_Bush_Arid_Sharp"]),
        ],
    },
    "Renonce": {
        "path": "Soil_Gravel", "speck": ("Soil_Snow", 0.12),
        "light": [("B", "Furniture_Lumberjack_Lantern")],
        "door": [("B", "Furniture_Tavern_Barrel"), ("B", "Furniture_Village_Crate"), ("B", "Plant_Hay_Bundle"),
                 ("B", "Deco_Bucket")],
        "bench": [("B", "Furniture_Tavern_Bench")],
        "pocket": [
            (3, ["Plant_Bush_Winter", "Plant_Bush_Winter_Red", "Plant_Fern_Winter", "Plant_Grass_Winter_Tall"]),
            (2, ["Furniture_Tavern_Barrel", "Furniture_Village_Crate", "Plant_Hay_Bundle", "Rubble_Stone"]),
            (1, ["Rubble_Stone", "Rubble_Stone_Medium", "Plant_Bush_Winter_Sharp"]),
        ],
    },
    "Slothian": {
        "path": "Rock_Basalt_Cobble", "speck": ("Soil_Mud_Dry", 0.15),
        "light": [("B", "Furniture_Jungle_Torch")],
        "door": [("B", "Furniture_Jungle_Pot"), ("B", "Furniture_Jungle_Pot_Secondary"), ("B", "Furniture_Jungle_Planter")],
        "bench": [("B", "Furniture_Jungle_Bench")],
        "pocket": [
            (3, ["Plant_Bush_Jungle", "Plant_Fern_Jungle", "Plant_Grass_Jungle_Tall", "Plant_Grass_Jungle"]),
            (2, ["Furniture_Jungle_Planter", "Furniture_Jungle_Pot", "Plant_Fern_Jungle", "Rubble_Basalt"]),
        ],
    },
}

GARDENS = [NPC + f"Garden_Small/Kweebec_Oak_Garden_Small_{i:03d}" for i in range(1, 89)]

# Espacements.
LIGHT_EVERY = 10   # blocs de sentier entre deux lumières
POCKET_GAP = 7     # écart minimal entre deux coins de décor
POCKET_PATH = 2    # écart minimal d'un coin au sentier
POCKET_WALL = 3    # écart minimal d'un coin à une emprise


def _rect_dist(x, z, r):
    dx = max(r[0] - x, 0, x - r[1])
    dz = max(r[2] - z, 0, z - r[3])
    return max(dx, dz)


class _Noise:
    """Bruit de valeur lissé 2D (déterministe), pour faire serpenter les chemins."""

    def __init__(self, rng, cell=7):
        self.cell = cell
        self.values = {}
        self.rng = rng

    def _v(self, i, j):
        if (i, j) not in self.values:
            self.values[(i, j)] = self.rng.random()
        return self.values[(i, j)]

    def __call__(self, x, z):
        fx, fz = x / self.cell, z / self.cell
        i, j = math.floor(fx), math.floor(fz)
        tx, tz = fx - i, fz - j
        tx, tz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
        a = self._v(i, j) * (1 - tx) + self._v(i + 1, j) * tx
        b = self._v(i, j + 1) * (1 - tx) + self._v(i + 1, j + 1) * tx
        return a * (1 - tz) + b * tz


def _door(rect, plaza_center=(0, 0)):
    """Case devant l'emprise, côté place (même règle que generate_village_layouts.spot « front »), et la normale."""
    x0, x1, z0, z1 = rect
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    if abs(cx) >= abs(cz):
        return ((x0 - WALL - 1, cz), (-1, 0)) if cx > 0 else ((x1 + WALL + 1, cz), (1, 0))
    return ((cx, z0 - WALL - 1), (0, -1)) if cz > 0 else ((cx, z1 + WALL + 1), (0, 1))


def _chaikin(points, rounds=2):
    for _ in range(rounds):
        if len(points) < 3:
            return points
        out = [points[0]]
        for (ax, az), (bx, bz) in zip(points, points[1:]):
            out.append((0.75 * ax + 0.25 * bx, 0.75 * az + 0.25 * bz))
            out.append((0.25 * ax + 0.75 * bx, 0.25 * az + 0.75 * bz))
        out.append(points[-1])
        points = out
    return points


def _densify(points, step=0.5):
    out = []
    for (ax, az), (bx, bz) in zip(points, points[1:]):
        n = max(1, int(math.hypot(bx - ax, bz - az) / step))
        for k in range(n):
            out.append((ax + (bx - ax) * k / n, az + (bz - az) * k / n))
    out.append(points[-1])
    return out


def build(layout_id, people, plaza, buildings, plot_rects, radius, block_ids=None, prefab_bounds=None):
    """Pas `Streets` du plan.

    buildings : [(id, palier, (x0, x1, z0, z1), petit)] ; plot_rects : [(id, palier, rect)] ; plaza : demi-côté de la
    place. Rend (streets, errors, preview) où preview sert à l'aperçu PNG.
    """
    style = STYLES.get(people)
    errors = []
    if style is None:
        return [], [f"{layout_id} : pas de style de sentiers pour {people}"], None
    rng = random.Random(f"streets:{layout_id}")
    noise = _Noise(random.Random(f"noise:{layout_id}"))
    R = radius + 4
    rects = [(bid, tier, rect) for bid, tier, rect, _ in buildings] + list(plot_rects)

    def in_plaza(x, z, pad=0):
        return abs(x) <= plaza + pad and abs(z) <= plaza + pad

    blocked = set()
    near_wall = set()
    for _, _, r in rects:
        for x in range(r[0] - WALL, r[1] + WALL + 1):
            for z in range(r[2] - WALL, r[3] + WALL + 1):
                blocked.add((x, z))
        for x in range(r[0] - WALL - 2, r[1] + WALL + 3):
            for z in range(r[2] - WALL - 2, r[3] + WALL + 3):
                near_wall.add((x, z))

    def inside_any(x, z, pad=0):
        return any(_rect_dist(x, z, r) <= pad for _, _, r in rects)

    # Réseau : case -> palier ; la couronne de la place est le point de départ de tout.
    network = {}
    ring = {(x, z) for x in range(-plaza - 1, plaza + 2) for z in range(-plaza - 1, plaza + 2)
            if max(abs(x), abs(z)) == plaza + 1}
    lines = []  # (palier, points lissés, largeur)

    def route(start, tier):
        goals = ring | {c for c, t in network.items() if t <= tier}
        if start in goals:
            return [start]
        dist = {start: 0.0}
        prev = {}
        heap = [(0.0, start)]
        while heap:
            d, cur = heapq.heappop(heap)
            if d > dist.get(cur, 1e18):
                continue
            if cur in goals:
                path = [cur]
                while path[-1] in prev:
                    path.append(prev[path[-1]])
                return path[::-1]
            x, z = cur
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, nz = x + dx, z + dz
                if abs(nx) > R or abs(nz) > R or in_plaza(nx, nz) or ((nx, nz) in blocked and (nx, nz) != start):
                    continue
                if dx and dz and ((x + dx, z) in blocked or (x, z + dz) in blocked):
                    continue
                step = math.sqrt(2) if dx and dz else 1.0
                cost = step * (1.0 + 1.2 * noise(nx, nz))
                if (nx, nz) in near_wall:
                    cost += 0.6
                if network.get((nx, nz), 99) <= tier:
                    cost *= 0.35
                nd = d + cost
                if nd < dist.get((nx, nz), 1e18):
                    dist[(nx, nz)] = nd
                    prev[(nx, nz)] = cur
                    heapq.heappush(heap, (nd, (nx, nz)))
        return None

    targets = []
    for bid, tier, rect, small in buildings:
        if small:
            continue
        targets.append((tier, bid, rect))
    for pid, tier, rect in plot_rects:
        targets.append((tier, pid, rect))
    targets.sort(key=lambda t: (t[0], _rect_dist(0, 0, t[2])))
    doors = []
    for tier, bid, rect in targets:
        (dx_, dz_), normal = _door(rect)
        if in_plaza(dx_, dz_):
            continue  # bâtiment collé à la place : la place sert de parvis
        blocked.discard((dx_, dz_))
        path = route((dx_, dz_), tier)
        if path is None:
            errors.append(f"{layout_id}/{bid} : aucun sentier possible vers la place")
            continue
        doors.append((tier, bid, (dx_, dz_), normal, rect))
        width = 1.5 if tier == 0 else 1.0
        lines.append((tier, _chaikin([(float(x), float(z)) for x, z in path]), width, bid))
        for c in path:
            network[c] = min(network.get(c, 99), tier)

    # Épaissit les lignes : cases à moins de `width` de la ligne, bord effiloché (1 case sur 3 du bord gardée en herbe).
    cells = {}
    edge = {}
    for tier, pts, width, _ in lines:
        for px, pz in _densify(pts):
            for x in range(math.floor(px - width - 1), math.ceil(px + width + 2)):
                for z in range(math.floor(pz - width - 1), math.ceil(pz + width + 2)):
                    d = math.hypot(x - px, z - pz)
                    if d > width + 0.35 or in_plaza(x, z) or inside_any(x, z, 0):
                        continue
                    if cells.get((x, z), 99) > tier:
                        cells[(x, z)] = tier
                    core = d <= width - 0.5
                    edge[(x, z)] = edge.get((x, z), True) and not core
    paths_by_tier = {}
    path_set = set()
    for (x, z), tier in sorted(cells.items()):
        if edge[(x, z)] and rng.random() < 0.3:
            continue
        block = style["path"]
        speck, share = style["speck"]
        if rng.random() < share:
            block = speck
        paths_by_tier.setdefault(tier, []).append(f"{x} {z} {block}")
        path_set.add((x, z))

    # Décor.
    taken = set()
    decor_by_tier = {}

    def decor_tier(x, z, base, natural):
        # Le terrassement d'un bâtiment à venir rabote les colonnes naturelles (plantes, os, éboulis, petits jardins)
        # jusqu'à TALUS blocs, mais garde celles que surmonte un meuble (village/Grading.untouched).
        reach = TALUS if natural else 3
        t = base
        for _, rt, r in rects:
            if _rect_dist(x, z, r) <= reach:
                t = max(t, rt)
        return t

    def footprint(kind, ident, x, z, rot):
        if kind == "B":
            return [(x, z)]
        b = prefab_bounds.get(ident) if prefab_bounds else None
        if b is None:
            errors.append(f"{layout_id} : prefab de décor inconnu {ident}")
            return None
        out = []
        for ax in range(b[0], b[1] + 1):
            for az in range(b[4], b[5] + 1):
                rx, rz = ax, az
                for _ in range(rot % 4):
                    rx, rz = rz, -rx
                out.append((x + rx, z + rz))
        return out

    def free(cellset, path_gap=0, wall_gap=1):
        for x, z in cellset:
            if (x, z) in taken or in_plaza(x, z, 1) or inside_any(x, z, wall_gap) or max(abs(x), abs(z)) > R:
                return False
            for dx in range(-path_gap, path_gap + 1):
                for dz in range(-path_gap, path_gap + 1):
                    if (x + dx, z + dz) in path_set:
                        return False
        return True

    def place(kind, ident, x, z, rot, base_tier, path_gap=0, wall_gap=2, halo=1):
        fp = footprint(kind, ident, x, z, rot)
        if fp is None or not free(fp, path_gap, wall_gap):
            return False
        for fx, fz in fp:
            for dx in range(-halo, halo + 1):
                for dz in range(-halo, halo + 1):
                    taken.add((fx + dx, fz + dz))
        natural = ident in GARDENS or ident.startswith(("Plant_", "Rubble_", "Deco_Bone"))
        tier = decor_tier(x, z, base_tier, natural)
        decor_by_tier.setdefault(tier, []).append(f"{x} {z} {rot} {kind} {ident}")
        return True

    def facing(nx, nz):
        """Lacet (0 S, 1 E, 2 N, 3 O) d'un objet qui regarde dans la direction (nx, nz)."""
        if abs(nx) >= abs(nz):
            return 1 if nx > 0 else 3
        return 0 if nz > 0 else 2

    # 1. Lumières le long des sentiers, en alternant les côtés.
    for tier, pts, width, _ in lines:
        dense = _densify(pts, 1.0)
        side = 1 if rng.random() < 0.5 else -1
        walked = LIGHT_EVERY // 2
        for i in range(1, len(dense) - 1):
            walked += 1
            if walked < LIGHT_EVERY:
                continue
            (ax, az), (bx, bz) = dense[i - 1], dense[i + 1]
            tx, tz = bx - ax, bz - az
            n = math.hypot(tx, tz) or 1.0
            nx, nz = -tz / n * side, tx / n * side
            for off in (width + 1.2, width + 2.2):
                lx, lz = round(dense[i][0] + nx * off), round(dense[i][1] + nz * off)
                kind, ident = rng.choice(style["light"])
                if place(kind, ident, lx, lz, facing(-nx, -nz), tier):
                    walked = 0
                    side = -side
                    break

    # 2. Objets près des portes : un ou deux, de part et d'autre de l'arrivée du sentier.
    for tier, bid, (dx_, dz_), (nx, nz), rect in doors:
        tx, tz = -nz, nx  # le long du mur
        sides = [1, -1]
        rng.shuffle(sides)
        for k, s in enumerate(sides[: rng.choice((1, 2, 2))]):
            for off in (2, 3):
                ox, oz = dx_ + tx * s * off - nx, dz_ + tz * s * off - nz
                kind, ident = rng.choice(style["door"])
                if place(kind, ident, ox, oz, facing(nx, nz), tier, wall_gap=0, halo=0):
                    break

    # 3. Bancs aux croisements (cases de sentier où se rejoignent des lignes de bâtiments différents).
    counts = {}
    for tier, pts, width, bid in lines:
        for c in {(round(x), round(z)) for x, z in pts}:
            counts.setdefault(c, set()).add(bid)
    junctions = sorted((c for c, s in counts.items() if len(s) >= 2), key=lambda c: (abs(c[0]) + abs(c[1]), c))
    benches = 0
    for jx, jz in junctions:
        if benches >= 4 + len(lines) // 6:
            break
        jt = min(network.get((jx, jz), 0), 3)
        for ox, oz in rng.sample([(3, 0), (-3, 0), (0, 3), (0, -3), (3, 3), (-3, -3)], 6):
            kind, ident = rng.choice(style["bench"])
            if place(kind, ident, jx + ox, jz + oz, facing(-ox, -oz), jt, path_gap=0, wall_gap=2):
                benches += 1
                break

    # 4. Petits coins dans les espaces libres (échantillonnage de Poisson par grille).
    candidates = [(x, z) for x in range(-R, R + 1) for z in range(-R, R + 1)
                  if math.hypot(x, z) <= radius - 4 and not in_plaza(x, z, 2)]
    rng.shuffle(candidates)
    centers = []
    weights = [w for w, _ in style["pocket"]]
    for x, z in candidates:
        if any((x - cx) ** 2 + (z - cz) ** 2 < POCKET_GAP ** 2 for cx, cz in centers):
            continue
        if not free([(x, z)], POCKET_PATH, POCKET_WALL):
            continue
        # Un coin n'a de sens qu'au milieu du village bâti (pas au milieu de nulle part) : un sentier à moins de 12
        # blocs ou une emprise à moins de 7. Palier : celui du sentier voisin, sinon celui de l'emprise la plus proche.
        near_paths = [t for c, t in network.items() if abs(c[0] - x) <= 12 and abs(c[1] - z) <= 12]
        near_rects = [(_rect_dist(x, z, r), rt) for _, rt, r in rects if _rect_dist(x, z, r) <= 7]
        if not near_paths and not near_rects:
            continue
        base = min(near_paths) if near_paths else min(near_rects)[1]
        _, kind = rng.choices(style["pocket"], weights)[0]
        if kind == "garden":
            if place("P", rng.choice(GARDENS), x, z, rng.randrange(4), base, POCKET_PATH, POCKET_WALL):
                centers.append((x, z))
            continue
        n = rng.randint(2, 5)
        placed = 0
        for _ in range(n * 3):
            if placed >= n:
                break
            ox, oz = x + rng.randint(-2, 2), z + rng.randint(-2, 2)
            if place("B", rng.choice(kind), ox, oz, rng.randrange(4), base, 1, POCKET_WALL - 1, halo=0):
                placed += 1
        if placed:
            centers.append((x, z))

    # Vérifie les ids contre les listes vanilla (blocs du sentier et du décor, prefabs).
    if block_ids is not None:
        used = {style["path"], style["speck"][0]}
        for entries in decor_by_tier.values():
            for e in entries:
                _, _, _, kind, ident = e.split(" ", 4)
                if kind == "B":
                    used.add(ident)
        for b in sorted(used - block_ids):
            errors.append(f"{layout_id} : bloc vanilla inconnu dans les sentiers/décor : {b}")

    streets = []
    for tier in sorted(set(paths_by_tier) | set(decor_by_tier)):
        streets.append({"Tier": tier, "Paths": paths_by_tier.get(tier, []), "Decor": decor_by_tier.get(tier, [])})
    preview = {"paths": {tuple(map(int, e.split()[:2])): t for t, es in paths_by_tier.items() for e in es},
               "decor": [(t, e) for t, es in decor_by_tier.items() for e in es]}
    return streets, errors, preview


def load_block_ids():
    path = TOOLS / "vanilla-block-ids-0.7.2.txt"
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}
