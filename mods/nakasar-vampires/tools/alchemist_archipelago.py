"""L'archipel de la Tour de l'Alchimiste, à l'échelle du donjon vanilla Deepworks : les îles du parcours, les ponts qui
les relient, la grande île de la tour et sa forêt, les îlots et le décor du ciel. Utilisé par
generate_alchemist_tower.py.

Parcours (Kevin, 19 octobre 2026 : « archipel en étapes », puis « petites îles successives, ponts soigneusement décorés
dans un style elfique, îles rapprochées ») : île d'arrivée, halte de la fontaine, halte du kiosque, Jardins des
Alambics, halte des sources, Ruines du premier laboratoire (point de contrôle), halte des arches, puis la grande île de la
tour, où un chemin traverse la forêt jusqu'au parvis. Toutes les places et tous les ponts sont fermés par un garde-corps
de 2 blocs surmonté de blocs `Barrier` (solides et invisibles) jusqu'à 4 blocs au-dessus du sol : on ne peut ni sauter
par-dessus ni grimper dessus.

Repère : x vers l'est, z vers le sud ; les positions (x, z) sont celles du monde, le sol des îles est à GROUND_Y.
"""
import math
import random

import generate_prefabs as pf

AIR = pf.AIR
BARRIER = "Barrier"  # bloc vanilla solide et invisible (Server/Item/Items/Hypixel/Barrier.json)
WALL_TOP = 4         # les garde-corps (parapet + Barrier) montent à 4 blocs au-dessus du sol où l'on marche
GROUND_Y = 100       # première couche d'air au-dessus du sol des îles (generate_alchemist_tower.GROUND_Y)

BRIDGE_HALF = 2      # ponts de 5 blocs de large
PATH_HALF = 3        # chemin de la forêt : 7 blocs, comme l'ouverture du parvis de la tour (alchemist_tower.BRIDGE_HALF)

ARRIVAL = {"center": (0, 0), "radius": 24.0, "flat": 17.0}
PLAZA_EDGE = 10      # le parapet du parvis d'arrivée est à 10 blocs du point d'apparition

# Îles du parcours, dans l'ordre. `plaza` : rayon de la place (le garde-corps est juste au-delà) ; `gates` : entrée puis
# sortie (N, S, E, O). Les haltes sont de petites îles ; les Jardins et les Ruines, des étapes plus grandes.
HALTS = [
    {"name": "HaltFountain", "center": (0, -40), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("S", "O"),
     "feature": "fountain"},
    {"name": "HaltKiosk", "center": (-36, -70), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("S", "N"),
     "feature": "kiosk"},
    {"name": "Gardens", "center": (-36, -122), "radius": 31.0, "flat": 26.0, "plaza": 22, "gates": ("S", "E"),
     "feature": "gardens"},
    {"name": "HaltSprings", "center": (8, -146), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("S", "N"),
     "feature": "springs"},
    {"name": "Ruins", "center": (8, -200), "radius": 31.0, "flat": 26.0, "plaza": 22, "gates": ("S", "N"),
     "feature": "ruins"},
    {"name": "HaltArches", "center": (-22, -244), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("E", "N"),
     "feature": "arches"},
]
HALT = {h["name"]: h for h in HALTS}
GARDENS, RUINS = HALT["Gardens"], HALT["Ruins"]

# La grande île de la tour : forêt entre la tour et le muret du bord, chemin de l'entrée sud au parvis.
TOWER = {"center": (0, -440), "radius": 170.0, "flat": 158.0}
TOWER_RIM = 150      # muret du bord de l'île (rayon), sur le plat
COURT_ENTRY = 81     # le chemin rejoint le parvis de la tour ici (alchemist_tower.COURT_END + 2, repère de la tour)
FOREST = (68, 144)   # rayons intérieur et extérieur de la forêt autour de la tour
COURT = (-22, 22, 30, 88)  # parvis de la tour et ses abords, sans arbres (x0, x1, z0, z1, repère de la tour)
TOWER_GATE_X = -22   # le dernier pont arrive au muret du bord à cette abscisse


def _gate(island, direction):
    """Point (x, z) au milieu de l'ouverture du garde-corps d'une île, côté `direction` (N, S, E, O)."""
    (cx, cz), r = island["center"], island["plaza"]
    return {"N": (cx, cz - r), "S": (cx, cz + r), "E": (cx + r, cz), "O": (cx - r, cz)}[direction]


_TC = TOWER["center"]
# Ponts : lignes brisées à angles droits, d'une ouverture à la suivante.
BRIDGES = [
    [(0, -PLAZA_EDGE), _gate(HALTS[0], "S")],
    [_gate(HALTS[0], "O"), (-36, -40), _gate(HALTS[1], "S")],
    [_gate(HALTS[1], "N"), _gate(GARDENS, "S")],
    [_gate(GARDENS, "E"), (8, -122), _gate(HALTS[3], "S")],
    [_gate(HALTS[3], "N"), _gate(RUINS, "S")],
    [_gate(RUINS, "N"), (8, -244), _gate(HALTS[5], "E")],
    [_gate(HALTS[5], "N"), (TOWER_GATE_X, _TC[1] + TOWER_RIM)],
]
# Chemin de la forêt, repère de la tour : du muret sud au parvis.
FOREST_PATH = [(TOWER_GATE_X, TOWER_RIM), (TOWER_GATE_X, 110), (0, 110), (0, COURT_ENTRY)]

# Style elfique : pierre claire, or, lanternes de lumière, fleurs et lianes.
FLOOR = [("Rock_Quartzite_Brick_Smooth", 5), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Quartzite_Brick", 1)]
STONE = "Rock_Quartzite_Brick"
PARAPET, PARAPET_TOP = "Rock_Quartzite_Brick", "Rock_Quartzite_Brick_Wall"
PILLAR_BASE, PILLAR = "Rock_Quartzite_Brick_Pillar_Base", "Rock_Quartzite_Brick_Pillar_Middle"
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
ORNATE = "Rock_Gold_Brick_Ornate"
GLASS = "Nakasar_Stained_Glass_Violet"
STATUE = "Furniture_Temple_Light_Statue"
LANTERN = "Furniture_Temple_Light_Lantern"
LANTERN_HANGING = "Furniture_Temple_Light_Lantern_Ceiling"
CRYSTALS = ["Rock_Crystal_Purple_Large", "Rock_Crystal_Purple_Medium", "Rock_Crystal_Green_Medium",
            "Rock_Crystal_Green_Large", "Rock_Crystal_Pink_Medium", "Rock_Crystal_Cyan_Medium"]
FLOWERS = ["Plant_Flower_Bushy_Violet", "Plant_Flower_Bushy_Cyan", "Plant_Flower_Bushy_White", "Plant_Flower_Orchid_Purple",
           "Plant_Flower_Tall_Cyan", "Plant_Flower_Common_Violet", "Plant_Flower_Orchid_Blue"]
PLANTS = ["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Blue", "Plant_Flower_Orchid_Purple",
          "Plant_Flower_Tall_Cyan", "Plant_Grass_Lush", "Plant_Flower_Bushy_Violet"]
VINES = "Plant_Vine_Green_Hanging"
WATER = "Water_Source"


def guard(p, x, z, y=0, post=False):
    """Garde-corps sur une case : parapet de 2 blocs, ou poteau surmonté d'une lanterne ; Barrier au-dessus jusqu'à
    WALL_TOP blocs (au-dessus de la lanterne pour un poteau)."""
    if post:
        p.set(x, y, z, PILLAR_BASE)
        p.set(x, y + 1, z, PILLAR)
        p.set(x, y + 2, z, ORNATE)
        p.set(x, y + 3, z, LANTERN)
        for k in (4, 5):
            p.set(x, y + k, z, BARRIER)
        return
    p.set(x, y, z, PARAPET)
    p.set(x, y + 1, z, PARAPET_TOP)
    for k in range(2, WALL_TOP):
        p.set(x, y + k, z, BARRIER)


# --- ponts ------------------------------------------------------------------------------------

def _segment_cells(a, b, half):
    (x0, z0), (x1, z1) = a, b
    for x in range(min(x0, x1) - half, max(x0, x1) + half + 1):
        for z in range(min(z0, z1) - half, max(z0, z1) + half + 1):
            yield x, z


def _along(line):
    """Cases de l'axe de la ligne, dans l'ordre, avec leur direction (dx, dz)."""
    out = []
    for (x0, z0), (x1, z1) in zip(line, line[1:]):
        dx, dz = (x1 > x0) - (x1 < x0), (z1 > z0) - (z1 < z0)
        n = max(abs(x1 - x0), abs(z1 - z0))
        for i in range(n + (1 if (x1, z1) == line[-1] else 0)):
            out.append(((x0 + dx * i, z0 + dz * i), (dx, dz)))
    return out


def _deck(lines, half):
    """Tablier et garde-corps d'un ensemble de lignes brisées ; les deux bouts de chaque ligne restent ouverts."""
    deck, ends = set(), []
    for line in lines:
        for a, b in zip(line, line[1:]):
            deck.update(_segment_cells(a, b, half))
        for end, nxt in ((line[0], line[1]), (line[-1], line[-2])):
            dx, dz = (end[0] > nxt[0]) - (end[0] < nxt[0]), (end[1] > nxt[1]) - (end[1] < nxt[1])
            ends.append((end, (dx, dz)))
    for (ex, ez), (dx, dz) in ends:
        for k in range(1, half + 1):
            for w in range(-half - 1, half + 2):
                deck.discard((ex + dx * k + dz * w, ez + dz * k + dx * w))

    def beyond_end(x, z):
        return any(1 <= (x - ex) * dx + (z - ez) * dz <= half + 1 and abs((x - ex) * dz - (z - ez) * dx) <= half + 1
                   for (ex, ez), (dx, dz) in ends)

    rails = set()
    for x, z in deck:
        for ddx in (-1, 0, 1):
            for ddz in (-1, 0, 1):
                n = (x + ddx, z + ddz)
                if n not in deck and not beyond_end(*n):
                    rails.add(n)
    return deck, rails


def bridges_prefab(seed):
    """Tous les ponts du parcours, dans le repère du monde (origine posée en (0, GROUND_Y, 0)).

    Tablier de pierre claire au liseré d'or, garde-corps à poteaux et lanternes tous les 4 blocs, fleurs sur le
    garde-corps, arches tous les 12 blocs (lanterne suspendue, lianes, lucioles), corniche d'or et lianes sous le
    tablier, quille qui s'épaissit vers les îles (silhouette d'arche vue de côté) et lanternes suspendues dessous.
    """
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    deck, rails = _deck(BRIDGES, BRIDGE_HALF)
    for x, z in deck:
        p.set(x, -1, z, p.pick(FLOOR))
        p.set(x, -2, z, STONE)
        for y in range(0, 8):
            p.set(x, y, z, AIR)
    for x, z in rails:
        p.set(x, -1, z, STONE)
        p.set(x, -2, z, GOLD)
        for y in range(0, 8):
            p.set(x, y, z, AIR)
        post = (x + z) % 4 == 0
        guard(p, x, z, post=post)
        if not post and rng.random() < 0.35:
            p.set(x, 2, z, rng.choice(FLOWERS))
        if rng.random() < 0.3:
            p.set(x, -3, z, VINES)
    for line in BRIDGES:
        cells = _along(line)
        n = len(cells)
        for i, ((x, z), (dx, dz)) in enumerate(cells):
            sx, sz = dz, dx  # en travers du pont
            if i % 3 == 0 and 2 < i < n - 3:
                p.set(x, -1, z, TRIM)
            depth = 1 + round(5 * (1 - math.sin(math.pi * min(i, n - 1 - i) / max(n - 1, 1))) ** 2)
            for w in (-1, 0, 1):
                p.fill(x + sx * w, -2 - depth, z + sz * w, x + sx * w, -3, z + sz * w, STONE)
            if i % 12 == 0 and 3 < i < n - 4:
                p.set(x, -3 - depth, z, LANTERN_HANGING)
            elif depth > 1:
                p.set(x, -3 - depth, z, "Rock_Quartzite_Stalactite_Small")
            if i % 12 == 6 and 3 < i < n - 4:
                _bridge_arch(p, x, z, sx, sz)
    return p


def _bridge_arch(p, x, z, sx, sz):
    """Arche en travers du pont : piliers sur les garde-corps, linteau d'or, lanterne suspendue, lianes, lucioles."""
    h = BRIDGE_HALF + 1
    for w in (-h, h):
        px, pz = x + sx * w, z + sz * w
        p.set(px, 0, pz, PILLAR_BASE)
        for y in range(1, 6):
            p.set(px, y, pz, PILLAR)
    for w in range(-h, h + 1):
        p.set(x + sx * w, 6, z + sz * w, GOLD if abs(w) < h else ORNATE)
    for w in (-h + 1, h - 1):
        p.set(x + sx * w, 7, z + sz * w, "Rock_Gold_Brick_Half")
    p.set(x, 7, z, "Nakasar_Tower_Emanation_Fireflies")
    p.set(x, 5, z, LANTERN_HANGING)
    for w in (-BRIDGE_HALF, BRIDGE_HALF):
        p.set(x + sx * w, 5, z + sz * w, VINES)


# --- places des îles ---------------------------------------------------------------------------

def _plaza(p, island, rng):
    """Place ronde dallée au liseré d'or, garde-corps percé aux ouvertures, poteaux à lanterne de part et d'autre des
    ouvertures, fleurs au pied du garde-corps. Renvoie les ouvertures (repère de l'île)."""
    (cx, cz), r = island["center"], island["plaza"]
    gates = [(gx - cx, gz - cz) for gx, gz in (_gate(island, g) for g in island["gates"])]
    open_cells = {(gx + dx, gz + dz) for gx, gz in gates
                  for dx in range(-BRIDGE_HALF, BRIDGE_HALF + 1) for dz in range(-BRIDGE_HALF, BRIDGE_HALF + 1)}
    for x in range(-r - 2, r + 3):
        for z in range(-r - 2, r + 3):
            d = math.hypot(x, z)
            if d < r + 0.5 or (x, z) in open_cells:
                p.set(x, -1, z, TRIM if r - 3.5 <= d < r - 2.7 else p.pick(FLOOR))
                p.fill(x, -3, z, x, -2, z, STONE)
                for y in range(0, 8):
                    p.set(x, y, z, AIR)
            elif d < r + 1.5:
                p.set(x, -1, z, STONE)
                guard(p, x, z, post=any(max(abs(x - gx), abs(z - gz)) == BRIDGE_HALF + 1 for gx, gz in gates))
    # Fleurs au pied du garde-corps, hors des ouvertures.
    for x in range(-r, r + 1):
        for z in range(-r, r + 1):
            d = math.hypot(x, z)
            if r - 0.5 <= d < r + 0.5 and rng.random() < 0.55 and \
                    all(max(abs(x - gx), abs(z - gz)) > BRIDGE_HALF + 1 for gx, gz in gates):
                p.set(x, -1, z, "Soil_Grass_Full")
                p.set(x, 0, z, rng.choice(FLOWERS))
    return gates


def _fountain(p, cx, cz, r, height, rng):
    """Fontaine : bassin d'eau cerclé d'or, colonne de quartzite et vasque d'où l'eau retombe en cascade."""
    for x in range(-r - 1, r + 2):
        for z in range(-r - 1, r + 2):
            d = math.hypot(x, z)
            if d < r - 0.5:
                p.set(cx + x, -2, cz + z, STONE)
                p.set(cx + x, -1, cz + z, "Rock_Quartzite_Brick_Smooth")
                p.fluid(cx + x, 0, cz + z, WATER)
            elif d < r + 0.5:
                p.set(cx + x, 0, cz + z, GOLD)
            elif d < r + 1.5:
                p.set(cx + x, -1, cz + z, TRIM)
    for y in range(0, height - 1):
        p.set(cx, y, cz, PILLAR if y else PILLAR_BASE)
    # Vasque : couronne de demi-dalles d'or autour de la source, l'eau déborde par les côtés et retombe dans le bassin.
    for x in (-1, 0, 1):
        for z in (-1, 0, 1):
            if (x, z) != (0, 0):
                p.set(cx + x, height - 1, cz + z, "Rock_Gold_Brick_Half")
    p.set(cx, height - 1, cz, ORNATE)
    p.fluid(cx, height, cz, WATER)
    p.set(cx, height + 2, cz, "Nakasar_Tower_Emanation_Motes")


def _kiosk(p, rng):
    """Kiosque : six colonnes fines, coupole d'or, lanterne suspendue, cristal et champignons lumineux."""
    for k in range(6):
        a = math.radians(30 + 60 * k)
        x, z = round(5 * math.cos(a)), round(5 * math.sin(a))
        p.set(x, 0, z, PILLAR_BASE)
        for y in range(1, 5):
            p.set(x, y, z, PILLAR)
        p.set(x, 5, z, ORNATE)
    for x in range(-6, 7):
        for z in range(-6, 7):
            d = math.hypot(x, z)
            if d < 6.3:
                top = 6 if d >= 4 else 7 if d >= 2 else 8
                for y in range(6, top + 1):
                    p.set(x, y, z, GOLD)
    p.set(0, 9, 0, "Nakasar_Tower_Emanation_Spiral")
    p.set(0, 5, 0, LANTERN_HANGING)
    p.set(0, -1, 0, ORNATE)
    p.set(0, 0, 0, "Rock_Crystal_Cyan_Large")
    for k in range(6):
        a = math.radians(60 * k)
        x, z = round(2.6 * math.cos(a)), round(2.6 * math.sin(a))
        p.set(x, 0, z, rng.choice(["Plant_Crop_Mushroom_Glowing_Blue", "Plant_Crop_Mushroom_Glowing_Purple"]))


def _springs(p, rng):
    """Halte des sources : trois petites vasques en triangle autour d'un cristal, lucioles."""
    for k in range(3):
        a = math.radians(90 + 120 * k)
        _fountain(p, round(4.5 * math.cos(a)), round(4.5 * math.sin(a)), 2, 3, rng)
    p.set(0, -1, 0, ORNATE)
    p.set(0, 0, 0, "Rock_Crystal_Pink_Large")
    p.set(0, 3, 0, "Nakasar_Tower_Emanation_Fireflies")


def _arches(p, rng):
    """Halte des arches : deux grandes arches croisées au-dessus de la place, cristaux à leurs pieds."""
    for axis in ("x", "z"):
        for s in (-6, 6):
            x, z = (s, 0) if axis == "x" else (0, s)
            p.set(x, 0, z, PILLAR_BASE)
            for y in range(1, 9):
                p.set(x, y, z, PILLAR)
        for t in range(-6, 7):
            y = 9 + (1 if abs(t) <= 4 else 0) + (1 if abs(t) <= 2 else 0)
            x, z = (t, 0) if axis == "x" else (0, t)
            for k in range(9, y + 1):
                p.set(x, k, z, GOLD if abs(t) < 6 else ORNATE)
            if axis == "x" and abs(t) in (3, 5):
                p.set(x, 8, z, VINES)
    p.set(0, 12, 0, ORNATE)
    p.set(0, 13, 0, "Nakasar_Tower_Emanation_Arc")
    p.set(0, 8, 0, LANTERN_HANGING)
    for x, z in ((-6, -1), (6, 1), (-1, 6), (1, -6)):
        p.set(x, 0, z, rng.choice(CRYSTALS))


def halt_prefab(island, seed):
    """Petite île de halte : place, garde-corps, et le motif de la halte au centre."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    _plaza(p, island, rng)
    {"fountain": lambda: _fountain(p, 0, 0, 3, 5, rng), "kiosk": lambda: _kiosk(p, rng),
     "springs": lambda: _springs(p, rng), "arches": lambda: _arches(p, rng)}[island["feature"]]()
    return p


def gardens_prefab(seed):
    """Jardins des Alambics : grande fontaine d'eau autour d'un alambic de verre, plates-bandes de plantes lumineuses,
    chaudrons, cristaux, tonnelles de glycine au-dessus des allées."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    gates = _plaza(p, GARDENS, rng)
    _fountain(p, 0, 0, 5, 2, rng)
    for y in range(0, 8):
        for x in range(-1, 2):
            for z in range(-1, 2):
                p.set(x, y, z, GLASS if (x, z) != (0, 0) else "Rock_Crystal_Green_Block")
    for x in range(-2, 3):
        for z in range(-2, 3):
            if max(abs(x), abs(z)) == 2:
                p.set(x, 8, z, "Rock_Gold_Brick_Half")
    p.set(0, 8, 0, ORNATE)
    p.set(0, 9, 0, "Nakasar_Tower_Emanation_Spiral")

    def in_alley(x, z):
        return any(abs(x - gx * t / 30) <= 3 and abs(z - gz * t / 30) <= 3 for gx, gz in gates for t in range(31))

    for x in range(-20, 21):
        for z in range(-20, 21):
            d = math.hypot(x, z)
            if in_alley(x, z):
                continue
            if 9 <= d < 12 or 16 <= d < 19:
                p.set(x, -1, z, "Soil_Grass_Full")
                p.set(x, 0, z, rng.choice(PLANTS) if rng.random() < 0.75 else AIR)
            elif 12 <= d < 16 and rng.random() < 0.04:
                p.set(x, 0, z, "Alchemy_Cauldron")
    for a in range(20, 360, 40):
        x, z = round(14 * math.cos(math.radians(a))), round(14 * math.sin(math.radians(a)))
        if not in_alley(x, z):
            p.set(x, 0, z, rng.choice(CRYSTALS))
            p.set(x, 3, z, "Nakasar_Tower_Emanation_Motes")
    # Tonnelles le long des allées : deux piliers, toit de glycine, lianes.
    for gx, gz in gates:
        for t in (0.45, 0.75):
            x, z = round(gx * t), round(gz * t)
            sx, sz = (1, 0) if gx == 0 else (0, 1)
            for w in (-3, 3):
                p.set(x + sx * w, 0, z + sz * w, PILLAR_BASE)
                for y in range(1, 5):
                    p.set(x + sx * w, y, z + sz * w, PILLAR)
            for w in range(-3, 4):
                p.set(x + sx * w, 5, z + sz * w, "Plant_Leaves_Wisteria_Wild")
                if abs(w) < 3 and rng.random() < 0.6:
                    p.set(x + sx * w, 4, z + sz * w, VINES)
    return p


def ruins_prefab(seed):
    """Ruines du premier laboratoire : tour écroulée, colonnes brisées, cristaux ; point de contrôle à la sortie nord.

    Renvoie (prefab, point de contrôle dans le repère de l'île)."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    gates = _plaza(p, RUINS, rng)
    for x in range(-21, 22):
        for z in range(-21, 22):
            if math.hypot(x, z) < 20 and rng.random() < 0.3:
                p.set(x, -1, z, rng.choice(["Rock_Marble_Cobble", "Rock_Stone_Mossy", "Soil_Grass_Full"]))
    # Tour écroulée à l'ouest : cylindre de 6 de rayon, sommet déchiqueté, brèches, restes du laboratoire.
    tx, tz = -10, 5
    for x in range(-7, 8):
        for z in range(-7, 8):
            d = math.hypot(x, z)
            if 5 <= d < 6.5:
                a = math.degrees(math.atan2(z, x)) % 360
                if 80 <= a <= 105 or 255 <= a <= 285:
                    continue
                top = 3 + int(9 * abs(math.sin(math.radians(a * 2.3))) + rng.random() * 4)
                for y in range(0, top):
                    p.set(tx + x, y, tz + z, rng.choice(["Rock_Marble_Brick", "Rock_Marble_Cobble", "Rock_Stone_Mossy"]))
            elif d < 5:
                p.set(tx + x, -1, tz + z, rng.choice(["Rock_Marble_Cobble", "Rock_Stone_Mossy", "Soil_Grass_Full"]))
                if rng.random() < 0.15:
                    p.set(tx + x, 0, tz + z, rng.choice(["Deco_Book_Pile_Small", "Deco_Scroll", "Deco_Potion",
                                                         "Plant_Crop_Mushroom_Glowing_Green"]))
    # Colonnes brisées en cercle, cristaux.
    for a in range(0, 360, 30):
        x, z = round(15 * math.cos(math.radians(a))), round(15 * math.sin(math.radians(a)))
        if abs(x) <= 4:
            continue  # allée nord-sud
        h = rng.randint(2, 7)
        p.set(x, 0, z, PILLAR_BASE)
        for y in range(1, h):
            p.set(x, y, z, "Rock_Marble_Brick_Pillar_Middle")
        if rng.random() < 0.5:
            p.set(x, h, z, "Plant_Flower_Bushy_Violet")
    for _ in range(16):
        a, r = rng.uniform(0, 360), rng.uniform(7, 20)
        x, z = round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))
        if abs(x) <= 3 or not p.free(x, 0, z):
            continue
        p.set(x, 0, z, rng.choice(CRYSTALS))
    for x, z in ((8, 8), (-16, -10), (6, -16)):
        p.set(x, 2, z, "Nakasar_Tower_Emanation_Mist")
    # Point de contrôle devant la sortie nord.
    gx, gz = gates[1]
    spot = (gx, 0, gz + 6)
    p.set(gx + 4, -1, gz + 6, ORNATE)
    p.set(gx + 4, 0, gz + 6, STATUE, pf.WEST)
    return p, spot


# --- île de la tour : muret du bord et chemin de la forêt ----------------------------------------

def grounds_prefab(seed):
    """Repère de la tour : muret du bord de l'île (Barrier au-dessus) et murets de l'entrée sud jusqu'au pont, chemin
    dallé à travers la forêt, lanternes, tonnelles de glycine, fontaine dans le coude du chemin."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    path, _ = _deck([FOREST_PATH], PATH_HALF)
    flat = TOWER["flat"]

    def wall(x, z):
        p.set(x, -1, z, "Rock_Stone_Mossy")
        p.set(x, 0, z, "Rock_Stone_Mossy")
        p.set(x, 1, z, "Rock_Marble_Cobble_Wall")
        for k in range(2, WALL_TOP + 1):
            p.set(x, k, z, BARRIER)

    for x in range(-TOWER_RIM - 2, TOWER_RIM + 3):
        for z in range(-TOWER_RIM - 2, TOWER_RIM + 3):
            d = math.hypot(x, z)
            if TOWER_RIM - 0.5 <= d < TOWER_RIM + 0.6 and (abs(x - TOWER_GATE_X) > PATH_HALF or z < 0):
                wall(x, z)
    # Entrée : deux murets du muret du bord jusqu'au-delà du plat de l'île, de part et d'autre du pont.
    for x in (TOWER_GATE_X - PATH_HALF - 1, TOWER_GATE_X + PATH_HALF + 1):
        for z in range(TOWER_RIM - 3, round(flat) + 2):
            if math.hypot(x, z) >= TOWER_RIM - 0.5:
                wall(x, z)
    for x, z in path:
        p.set(x, -1, z, rng.choice(["Rock_Marble_Cobble", "Rock_Quartzite_Brick_Smooth", "Rock_Quartzite_Brick",
                                    "Rock_Stone_Mossy"]))
        p.fill(x, -3, z, x, -2, z, "Rock_Stone")
        for y in range(0, 8):
            p.set(x, y, z, AIR)
    for i, ((x, z), (dx, dz)) in enumerate(_along(FOREST_PATH)):
        sx, sz = dz, dx
        border = [(x + sx * w, z + sz * w) for w in (-PATH_HALF - 1, PATH_HALF + 1)]
        border = [(bx, bz) for bx, bz in border if (bx, bz) not in path and math.hypot(bx, bz) < TOWER_RIM - 1.5]
        if i % 16 == 10 and len(border) == 2:
            for bx, bz in border:
                p.set(bx, 0, bz, PILLAR_BASE)
                for y in range(1, 6):
                    p.set(bx, y, bz, PILLAR)
            for w in range(-PATH_HALF - 1, PATH_HALF + 2):
                p.set(x + sx * w, 6, z + sz * w, "Plant_Leaves_Wisteria_Wild")
                if abs(w) <= PATH_HALF and rng.random() < 0.5:
                    p.set(x + sx * w, 5, z + sz * w, VINES)
            p.set(x, 5, z, LANTERN_HANGING)
            continue
        for bx, bz in border:
            if i % 8 == 4:
                p.set(bx, 0, bz, PILLAR_BASE)
                p.set(bx, 1, bz, PILLAR)
                p.set(bx, 2, bz, ORNATE)
                p.set(bx, 3, bz, LANTERN)
            elif rng.random() < 0.6:
                p.set(bx, 0, bz, rng.choice(FLOWERS))
    _fountain(p, FOUNTAIN[0], FOUNTAIN[1], 3, 4, rng)
    return p


FOUNTAIN = (-8, 122)  # fontaine dans le coude du chemin, repère de la tour


def forest_sites(seed=7, count=520):
    """Arbres de la forêt de la tour (repère de la tour) : (x, z, taille), loin du chemin, de la fontaine et du muret."""
    rng = random.Random(seed)
    path_cells = [c for c, _ in _along(FOREST_PATH)]
    out = []
    for _ in range(80000):
        if len(out) >= count:
            break
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform(FOREST[0] ** 2, FOREST[1] ** 2))
        x, z = r * math.cos(a), r * math.sin(a)
        size = rng.choices(["big", "medium", "small"], [3, 4, 3])[0]
        gap = {"big": 13, "medium": 9, "small": 6}[size]
        if any(math.hypot(x - px, z - pz) < PATH_HALF + 1 + gap * 0.6 for px, pz in path_cells):
            continue
        if math.hypot(x - FOUNTAIN[0], z - FOUNTAIN[1]) < 6 + gap * 0.5:
            continue
        if COURT[0] - gap / 2 <= x <= COURT[1] + gap / 2 and COURT[2] <= z <= COURT[3] + gap / 2:
            continue
        if any(math.hypot(x - o[0], z - o[1]) < (gap + o[3]) / 2 for o in out):
            continue
        out.append((round(x), round(z), size, gap))
    return [(x, z, size) for x, z, size, _ in out]


def undergrowth_sites(seed=8, count=280):
    """Sous-bois (repère de la tour) : (x, z, dossier du jeu) — buissons, fougères de cristal, champignons géants,
    rochers de mana."""
    rng = random.Random(seed)
    path_cells = [c for c, _ in _along(FOREST_PATH)]
    out = []
    while len(out) < count:
        a = rng.uniform(0, 2 * math.pi)
        r = math.sqrt(rng.uniform((FOREST[0] - 4) ** 2, (FOREST[1] - 2) ** 2))
        x, z = r * math.cos(a), r * math.sin(a)
        if any(math.hypot(x - px, z - pz) < PATH_HALF + 7 for px, pz in path_cells):
            continue
        if math.hypot(x - FOUNTAIN[0], z - FOUNTAIN[1]) < 9:
            continue
        if COURT[0] - 4 <= x <= COURT[1] + 4 and COURT[2] <= z <= COURT[3] + 4:
            continue
        out.append((round(x), round(z), rng.choices(UNDERGROWTH, [5, 3, 1, 2])[0]))
    return out


# --- îlots et ciel --------------------------------------------------------------------------------

# Prefabs du jeu (dossiers de Server/Prefabs d'Assets.zip, lus le 2026-10-19).
BIG_TREES = ["Trees/Jungle_Crystal/Stage_3", "Trees/Fig_Blue/Stage_3", "Trees/Zone5/Aqua/Large"]
MEDIUM_TREES = ["Trees/Azure/Stage_3", "Trees/Spiral/Stage_3", "Trees/Wisteria/Stage_2"]
SMALL_TREES = ["Trees/Crystal/Stage_3", "Trees/Silver/Stage_3", "Trees/Willow/Stage_3"]
FOREST_TREES = {
    "big": BIG_TREES + ["Trees/Oak/Stage_5", "Trees/Beech/Stage_4", "Trees/Oak_Moss/Stage_4"],
    "medium": MEDIUM_TREES + ["Trees/Oak/Stage_3", "Trees/Birch/Stage_3", "Trees/Wisteria/Stage_1"],
    "small": SMALL_TREES + ["Trees/Beech/Stage_2", "Trees/Fig_Blue/Stage_2"],
}
UNDERGROWTH = ["Plants/Bush/Lush", "Plants/Jungle/Crystal_Ferns", "Plants/Mushroom_Large/Purple",
               "Rock_Formations/Rocks/Stone_Mana"]
# Décor du ciel : géodes flottantes (40 blocs de large), rochers et cristaux flottants.
GEODES = ["Rock_Formations/Geode_Floating/Crystal", "Rock_Formations/Geode_Floating/Forest",
          "Rock_Formations/Geode_Floating/Base"]
FLOATING_ROCKS = "Rock_Formations/Rocks/Floating"
FLOATING_CRYSTAL = "Rock_Formations/Crystal_Floating"


def _segment_distance(px, pz, a, b):
    (x0, z0), (x1, z1) = a, b
    dx, dz = x1 - x0, z1 - z0
    t = 0.0 if dx == dz == 0 else max(0.0, min(1.0, ((px - x0) * dx + (pz - z0) * dz) / (dx * dx + dz * dz)))
    return math.hypot(px - (x0 + t * dx), pz - (z0 + t * dz))


def big_islands():
    """Îles du parcours : (centre (x, z), rayon, plat, nom)."""
    return [(ARRIVAL["center"], ARRIVAL["radius"], ARRIVAL["flat"], "Arrival"),
            (TOWER["center"], TOWER["radius"], TOWER["flat"], "Tower")] + \
           [(h["center"], h["radius"], h["flat"], h["name"]) for h in HALTS]


def _route_distance(x, z):
    """Distance horizontale au parcours (ponts et îles du parcours)."""
    d = min(_segment_distance(x, z, a, b) for line in BRIDGES for a, b in zip(line, line[1:]))
    for c, r, _, _ in big_islands():
        d = min(d, math.hypot(x - c[0], z - c[1]) - r)
    return d


def islets(seed=19, count=44):
    """Îlots (centre du dessus (x, y, z), rayon, arbre), loin du parcours et des grandes îles."""
    rng = random.Random(seed)
    out = []
    tries = 0
    while len(out) < count and tries < 40000:
        tries += 1
        x, z = rng.uniform(-300, 300), rng.uniform(-680, 90)
        r = rng.choice([7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 24])
        y = round(rng.uniform(80, 240 if r < 16 else 200))
        if _route_distance(x, z) < r + (14 if y > 150 or y < 88 else 24):
            continue
        if any(math.hypot(x - o[0][0], z - o[0][2]) < r + o[1] + 18 for o in out):
            continue
        trees = BIG_TREES if r >= 18 else MEDIUM_TREES if r >= 11 else SMALL_TREES
        out.append(((round(x), y, round(z)), float(r), rng.choice(trees)))
    return out


def sky_decor(islet_list, seed=23):
    """Décor flottant : [(position (x, y, z), dossier du jeu)]. Géodes loin du parcours ; rochers et cristaux
    flottants le long du parcours, à côté ou au-dessus, jamais sur le chemin."""
    rng = random.Random(seed)
    placed = []

    def clear_of(x, y, z, r):
        if any(math.hypot(x - c[0], z - c[2]) < r + ir + 8 and abs(y - c[1]) < r + 30 for c, ir, _ in islet_list):
            return False
        return all(math.dist((x, y, z), pos) > r + pr + 6 for pos, _, pr in placed)

    for kind, count, r, near, ys in (("geode", 14, 24, (40, 180), (150, 250)),
                                     ("rocks", 40, 6, (12, 70), (106, 200)),
                                     ("crystal", 24, 4, (10, 60), (100, 170))):
        n, tries = 0, 0
        while n < count and tries < 20000:
            tries += 1
            x, z, y = rng.uniform(-280, 280), rng.uniform(-660, 80), rng.uniform(*ys)
            if not near[0] + r <= _route_distance(x, z) <= near[1] + r or not clear_of(x, y, z, r):
                continue
            folder = rng.choice(GEODES) if kind == "geode" else FLOATING_ROCKS if kind == "rocks" else FLOATING_CRYSTAL
            placed.append(((round(x), round(y), round(z)), folder, r))
            n += 1
    return [(pos, folder) for pos, folder, _ in placed]
