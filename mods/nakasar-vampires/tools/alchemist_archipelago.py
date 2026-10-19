"""L'archipel de la Tour de l'Alchimiste, à l'échelle du donjon vanilla Deepworks : les îles du parcours, les ponts qui
les relient, la grande île de la tour et sa forêt, les îlots et le décor du ciel. Utilisé par
generate_alchemist_tower.py.

Parcours (Kevin, 19 octobre 2026 : « archipel en étapes », puis « petites îles successives, ponts soigneusement décorés
dans un style elfique, îles rapprochées ») : île d'arrivée, halte de la fontaine, halte du kiosque, Jardins des
Alambics, halte des sources, Ruines du premier laboratoire (point de contrôle), halte des arches, puis la grande île de la
tour, où un chemin traverse la forêt jusqu'au parvis. Toutes les places et tous les ponts sont fermés par un garde-corps
de 2 blocs. Au-dessus, des blocs `Barrier` marquent jusqu'à 4 blocs au-dessus du sol la barrière qu'il faut :
generate_alchemist_tower.py les retire des prefabs et en fait des volumes de repoussée, comme dans Deepworks.

Repère : x vers l'est, z vers le sud ; les positions (x, z) sont celles du monde, le sol des îles est à GROUND_Y.
"""
import math
import random

import generate_prefabs as pf

AIR = pf.AIR
BARRIER = "Barrier"  # marque une barrière ; remplacé par un volume de repoussée (generate_alchemist_tower.py)
WALL_TOP = 4         # les garde-corps (parapet + Barrier) montent à 4 blocs au-dessus du sol où l'on marche
GROUND_Y = 100       # première couche d'air au-dessus du sol des îles (generate_alchemist_tower.GROUND_Y)

BRIDGE_HALF = 2      # ponts de 5 blocs de large
PATH_HALF = 3        # chemin de la forêt : 7 blocs, comme l'ouverture du parvis de la tour (alchemist_tower.BRIDGE_HALF)

ARRIVAL = {"center": (0, 0), "radius": 24.0, "flat": 17.0}
PLAZA_EDGE = 10      # le parapet du parvis d'arrivée est à 10 blocs du point d'apparition

# Îles du parcours, dans l'ordre. `plaza` : rayon de la place (le garde-corps est juste au-delà) ; `gates` : entrée puis
# sortie, soit un point cardinal (N, S, E, O), soit le nom de l'île voisine (ouverture tournée vers son centre, pont
# droit et en biais) ; `dy` : hauteur du sol de l'île au-dessus de GROUND_Y (Kevin : « des hauteurs un peu
# différentes », les ponts montent ou descendent en pente douce). Les haltes sont de petites îles ; les Jardins et les
# Ruines, des étapes plus grandes.
HALTS = [
    {"name": "HaltFountain", "center": (0, -40), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("S", "HaltKiosk"),
     "feature": "fountain", "dy": 3},
    {"name": "HaltKiosk", "center": (-36, -70), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("HaltFountain", "N"),
     "feature": "kiosk", "dy": 8},
    {"name": "Gardens", "center": (-36, -122), "radius": 31.0, "flat": 26.0, "plaza": 22, "gates": ("S", "HaltSprings"),
     "feature": "gardens", "dy": 4},
    {"name": "HaltSprings", "center": (8, -146), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("Gardens", "N"),
     "feature": "springs", "dy": 9},
    {"name": "Ruins", "center": (8, -200), "radius": 31.0, "flat": 26.0, "plaza": 22, "gates": ("S", "HaltArches"),
     "feature": "ruins", "dy": 5},
    {"name": "HaltArches", "center": (-22, -244), "radius": 16.0, "flat": 12.0, "plaza": 9, "gates": ("Ruins", "N"),
     "feature": "arches", "dy": 1},
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


COMPASS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "O": (-1, 0)}


def _gate_dir(island, direction):
    """Direction (ux, uz) unitaire d'une ouverture : point cardinal, ou vers le centre de l'île nommée."""
    if direction in COMPASS:
        return COMPASS[direction]
    (cx, cz), (tx, tz) = island["center"], HALT[direction]["center"]
    d = math.hypot(tx - cx, tz - cz)
    return (tx - cx) / d, (tz - cz) / d


def _gate(island, direction):
    """Point (x, z) au milieu de l'ouverture du garde-corps d'une île, côté `direction` (point cardinal ou île voisine)."""
    (cx, cz), r = island["center"], island["plaza"]
    ux, uz = _gate_dir(island, direction)
    return cx + round(r * ux), cz + round(r * uz)


def stage_y(island):
    """Première couche d'air au-dessus du sol d'une île du parcours."""
    return GROUND_Y + island.get("dy", 0)


def stage_trees(island):
    """Quatre arbres entre le garde-corps et le bord d'une grande île, en diagonale, écartés des ouvertures."""
    (cx, cz), r = island["center"], island["plaza"] + 5
    gates = [math.degrees(math.atan2(uz, ux)) for ux, uz in (_gate_dir(island, g) for g in island["gates"])]
    out = []
    for a in (35, 145, 215, 325):
        for g in gates:
            diff = (a - g + 180) % 360 - 180
            if abs(diff) < 28:
                a = g + (28 if diff >= 0 else -28)
        out.append((cx + round(r * math.cos(math.radians(a))), cz + round(r * math.sin(math.radians(a)))))
    return out


_TC = TOWER["center"]
# Ponts : chacun est droit, d'une ouverture à la suivante, avec la hauteur du sol à ses deux bouts (relative à
# GROUND_Y) ; il monte ou descend en pente régulière, par demi-blocs.
BRIDGES = [
    [(0, -PLAZA_EDGE), _gate(HALTS[0], "S")],
    [_gate(HALTS[0], "HaltKiosk"), _gate(HALTS[1], "HaltFountain")],
    [_gate(HALTS[1], "N"), _gate(GARDENS, "S")],
    [_gate(GARDENS, "HaltSprings"), _gate(HALTS[3], "Gardens")],
    [_gate(HALTS[3], "N"), _gate(RUINS, "S")],
    [_gate(RUINS, "HaltArches"), _gate(HALTS[5], "Ruins")],
    [_gate(HALTS[5], "N"), (TOWER_GATE_X, _TC[1] + TOWER_RIM)],
]
_DY = [h["dy"] for h in HALTS]
BRIDGE_LEVELS = [(0, _DY[0]), (_DY[0], _DY[1]), (_DY[1], _DY[2]), (_DY[2], _DY[3]), (_DY[3], _DY[4]),
                 (_DY[4], _DY[5]), (_DY[5], 0)]
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
HALF = "Rock_Quartzite_Brick_Smooth_Half"  # demi-marche des ponts en pente
# Statue des points de contrôle de Deepworks, éteinte ; le volume du point de contrôle la fait changer d'état.
STATUE = "*Dungeon_Checkpoint_Statue_State_Definitions_Inactive"
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

def _axis(a, b):
    return a[0] == b[0] or a[1] == b[1]


def _unit(a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dz)
    return dx / d, dz / d


def _segment_cells(a, b, half):
    """Cases du tablier d'un segment. À angle droit : le rectangle, qui déborde de `half` aux deux bouts (les coudes se
    remplissent). En biais : la bande de largeur 2 * half + 1, coupée net aux deux bouts."""
    (x0, z0), (x1, z1) = a, b
    if _axis(a, b):
        for x in range(min(x0, x1) - half, max(x0, x1) + half + 1):
            for z in range(min(z0, z1) - half, max(z0, z1) + half + 1):
                yield x, z
        return
    ux, uz = _unit(a, b)
    length = math.hypot(x1 - x0, z1 - z0)
    for x in range(min(x0, x1) - half - 1, max(x0, x1) + half + 2):
        for z in range(min(z0, z1) - half - 1, max(z0, z1) + half + 2):
            along = (x - x0) * ux + (z - z0) * uz
            if 0 <= along <= length and abs((x - x0) * uz - (z - z0) * ux) <= half + 0.5:
                yield x, z


def _along(line):
    """Cases de l'axe de la ligne, dans l'ordre, avec leur direction (dx, dz) (entiers à angle droit, unitaire en
    biais)."""
    out = []
    for a, b in zip(line, line[1:]):
        (x0, z0), (x1, z1) = a, b
        last = 1 if b == line[-1] else 0
        if _axis(a, b):
            dx, dz = (x1 > x0) - (x1 < x0), (z1 > z0) - (z1 < z0)
            n = max(abs(x1 - x0), abs(z1 - z0))
            for i in range(n + last):
                out.append(((x0 + dx * i, z0 + dz * i), (dx, dz)))
        else:
            ux, uz = _unit(a, b)
            n = round(math.hypot(x1 - x0, z1 - z0))
            for i in range(n + last):
                out.append(((round(x0 + ux * i), round(z0 + uz * i)), (ux, uz)))
    return out


def _deck(lines, half):
    """Tablier et garde-corps d'un ensemble de lignes brisées ; les deux bouts de chaque ligne restent ouverts."""
    deck, ends = set(), []
    for line in lines:
        for a, b in zip(line, line[1:]):
            deck.update(_segment_cells(a, b, half))
        for end, nxt in ((line[0], line[1]), (line[-1], line[-2])):
            if _axis(end, nxt):
                dx, dz = (end[0] > nxt[0]) - (end[0] < nxt[0]), (end[1] > nxt[1]) - (end[1] < nxt[1])
                for k in range(1, half + 1):
                    for w in range(-half - 1, half + 2):
                        deck.discard((end[0] + dx * k + dz * w, end[1] + dz * k + dx * w))
                ends.append((end, (dx, dz)))
            else:
                ends.append((end, _unit(nxt, end)))

    def beyond_end(x, z):
        return any(0 < (x - ex) * dx + (z - ez) * dz <= half + 1.5 and abs((x - ex) * dz - (z - ez) * dx) <= half + 1.5
                   for (ex, ez), (dx, dz) in ends)

    rails = set()
    for x, z in deck:
        for ddx in (-1, 0, 1):
            for ddz in (-1, 0, 1):
                n = (x + ddx, z + ddz)
                if n not in deck and not beyond_end(*n):
                    rails.add(n)
    return deck, rails


def bridge_levels(cells):
    """Hauteur du sol de chaque case de pont, en demi-blocs au-dessus de GROUND_Y (pente régulière d'un bout à
    l'autre du pont le plus proche)."""
    out = {}
    for x, z in cells:
        best = None
        for (a, b), (ya, yb) in zip(BRIDGES, BRIDGE_LEVELS):
            d = _segment_distance(x, z, a, b)
            if best is None or d < best[0]:
                dx, dz = b[0] - a[0], b[1] - a[1]
                t = max(0.0, min(1.0, ((x - a[0]) * dx + (z - a[1]) * dz) / (dx * dx + dz * dz)))
                best = (d, round(2 * (ya + (yb - ya) * t)))
        out[(x, z)] = best[1]
    return out


def bridges_prefab(seed):
    """Tous les ponts du parcours, dans le repère du monde (origine posée en (0, GROUND_Y, 0)).

    Tablier de pierre claire au liseré d'or, en pente douce par demi-dalles d'une île à l'autre, garde-corps à poteaux
    et lanternes tous les 4 blocs, fleurs sur le garde-corps, arches tous les 12 blocs (lanterne suspendue, lianes,
    lucioles), corniche d'or et lianes sous le tablier, quille qui s'épaissit vers les îles (silhouette d'arche vue de
    côté) et lanternes suspendues dessous.
    """
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    deck, rails = _deck(BRIDGES, BRIDGE_HALF)
    level = bridge_levels(deck)
    for x, z in deck:
        s = level[(x, z)]
        y = s // 2
        p.set(x, y - 1, z, p.pick(FLOOR))
        p.set(x, y - 2, z, STONE)
        for k in range(y, y + 9):
            p.set(x, k, z, AIR)
        if s % 2:
            p.set(x, y, z, HALF)
    rail_level = {}
    for x, z in rails:
        near = [level[(x + dx, z + dz)] for dx in (-1, 0, 1) for dz in (-1, 0, 1) if (x + dx, z + dz) in level]
        rail_level[(x, z)] = max(near)
    for (x, z), s in rail_level.items():
        y = s // 2
        p.set(x, y - 1, z, STONE)
        p.set(x, y - 2, z, GOLD)
        for k in range(y, y + 9):
            p.set(x, k, z, AIR)
        post = (x + z) % 4 == 0
        guard(p, x, z, y, post=post)
        if not post and rng.random() < 0.35:
            p.set(x, y + 2, z, rng.choice(FLOWERS))
        if rng.random() < 0.3:
            p.set(x, y - 3, z, VINES)
    for line in BRIDGES:
        cells = _along(line)
        n = len(cells)
        for i, ((x, z), (dx, dz)) in enumerate(cells):
            sx, sz = -dz, dx  # en travers du pont
            y = level.get((x, z), 0) // 2
            if i % 3 == 0 and 2 < i < n - 3 and level.get((x, z), 0) % 2 == 0:
                p.set(x, y - 1, z, TRIM)
            depth = 1 + round(5 * (1 - math.sin(math.pi * min(i, n - 1 - i) / max(n - 1, 1))) ** 2)
            for w in (-1, 0, 1):
                cx, cz = round(x + sx * w), round(z + sz * w)
                p.fill(cx, y - 2 - depth, cz, cx, y - 3, cz, STONE)
            if i % 12 == 0 and 3 < i < n - 4:
                p.set(x, y - 3 - depth, z, LANTERN_HANGING)
            elif depth > 1:
                p.set(x, y - 3 - depth, z, "Rock_Quartzite_Stalactite_Small")
            if i % 12 == 6 and 3 < i < n - 4:
                _bridge_arch(p, x, y, z, sx, sz)
    return p


def _bridge_arch(p, x, y, z, sx, sz):
    """Arche en travers du pont : piliers sur les garde-corps, linteau d'or, lanterne suspendue, lianes, lucioles."""
    h = BRIDGE_HALF + 1

    def at(w):
        return round(x + sx * w), round(z + sz * w)

    for w in (-h, h):
        px, pz = at(w)
        p.set(px, y, pz, PILLAR_BASE)
        for k in range(1, 6):
            p.set(px, y + k, pz, PILLAR)
    for w in range(-h, h + 1):
        p.set(*_xyz(at(w), y + 6), GOLD if abs(w) < h else ORNATE)
    for w in (-h + 1, h - 1):
        p.set(*_xyz(at(w), y + 7), "Rock_Gold_Brick_Half")
    p.set(x, y + 7, z, "Nakasar_Tower_Emanation_Fireflies")
    p.set(x, y + 5, z, LANTERN_HANGING)
    for w in (-BRIDGE_HALF, BRIDGE_HALF):
        p.set(*_xyz(at(w), y + 5), VINES)


def _xyz(xz, y):
    return xz[0], y, xz[1]


# --- places des îles ---------------------------------------------------------------------------

def _plaza(p, island, rng):
    """Place ronde dallée au liseré d'or, garde-corps percé aux ouvertures, poteaux à lanterne de part et d'autre des
    ouvertures, fleurs au pied du garde-corps. Renvoie les ouvertures (repère de l'île)."""
    (cx, cz), r = island["center"], island["plaza"]
    gates = [(gx - cx, gz - cz) for gx, gz in (_gate(island, g) for g in island["gates"])]
    dirs = [_gate_dir(island, g) for g in island["gates"]]

    def opening(x, z, width):
        """La case est dans l'ouverture (largeur `width` de part et d'autre de l'axe), du côté de l'ouverture."""
        return any(x * ux + z * uz >= r - 1 and abs(x * uz - z * ux) <= width for ux, uz in dirs)

    for x in range(-r - 2, r + 3):
        for z in range(-r - 2, r + 3):
            d = math.hypot(x, z)
            if d < r + 0.5 or opening(x, z, BRIDGE_HALF + 0.5):
                p.set(x, -1, z, TRIM if r - 3.5 <= d < r - 2.7 else p.pick(FLOOR))
                p.fill(x, -3, z, x, -2, z, STONE)
                for y in range(0, 8):
                    p.set(x, y, z, AIR)
            elif d < r + 1.5:
                p.set(x, -1, z, STONE)
                guard(p, x, z, post=opening(x, z, BRIDGE_HALF + 1.5))
    # Fleurs au pied du garde-corps, hors des ouvertures.
    for x in range(-r, r + 1):
        for z in range(-r, r + 1):
            d = math.hypot(x, z)
            if r - 0.5 <= d < r + 0.5 and rng.random() < 0.55 and not opening(x, z, BRIDGE_HALF + 1.5):
                p.set(x, -1, z, "Soil_Grass_Full")
                p.set(x, 0, z, rng.choice(FLOWERS))
    return gates


def _in_lane(x, z, gates, width):
    """La case est dans l'allée qui va du centre de l'île à l'une de ses ouvertures (demi-largeur `width`)."""
    for gx, gz in gates:
        n = math.hypot(gx, gz)
        ux, uz = gx / n, gz / n
        if -width <= x * ux + z * uz <= n + 1 and abs(x * uz - z * ux) <= width:
            return True
    return False


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


# Petits groupes d'ennemis des îles (Kevin : « des petits groupes d'ennemis divers ») : rôles de
# tools/generate_tower_mobs.py, posés en arc de cercle à `r` du centre, loin des allées ; un groupe par entrée de liste.
SPAWNER = "Nakasar_Spawner_"
ISLAND_MOBS = {
    "HaltFountain": (7.5, [["Homunculus", "Homunculus", "Living_Flask_Poison"]]),
    "HaltKiosk": (7.5, [["Alchemist_Apprentice", "Homunculus", "Homunculus"]]),
    "Gardens": (14.0, [["Snapdragon", "Carnivorous_Vine", "Snapdragon"], ["Elemental_Root", "Homunculus", "Homunculus"]]),
    "HaltSprings": (7.5, [["Living_Flask_Fire", "Elemental_Frost", "Living_Flask_Fire"]]),
    "Ruins": (12.0, [["Homunculus", "Lead_Golem", "Homunculus"], ["Alchemist_Apprentice", "Living_Flask_Poison"]]),
    "HaltArches": (7.5, [["Alchemist_Apprentice", "Living_Flask_Fire", "Alchemist_Apprentice"]]),
}
TALL_MOBS = {"Lead_Golem": 4}


def _mobs(p, island, gates):
    """Blocs d'apparition des groupes de l'île : chaque groupe en arc, dans le secteur le plus loin des allées (et des
    autres groupes) ; chaque mob sur la case libre la plus proche (sol plein, air au-dessus, hors des allées)."""
    r, groups = ISLAND_MOBS[island["name"]]
    taken = [math.degrees(math.atan2(gz, gx)) for gx, gz in gates]
    spread = math.degrees(2.8 / r)  # environ trois blocs entre deux mobs du groupe

    def gap(a):
        return min(abs((a - t + 180) % 360 - 180) for t in taken)

    out = []
    for group in groups:
        a0 = max(range(0, 360, 5), key=gap)
        taken.append(a0)
        for j, role in enumerate(group):
            a = math.radians(a0 + (j - (len(group) - 1) / 2) * spread)
            x0, z0 = r * math.cos(a), r * math.sin(a)
            height = TALL_MOBS.get(role, 3)
            best = None
            for dx in range(-3, 4):
                for dz in range(-3, 4):
                    x, z = round(x0) + dx, round(z0) + dz
                    if (_in_lane(x, z, gates, BRIDGE_HALF + 1) or p.get(x, -1, z) in (None, AIR)
                            or not all(p.free(x, y, z) for y in range(height))
                            or any(abs(x - ox) + abs(z - oz) < 2 for ox, _, oz in out)):
                        continue
                    d = (x - x0) ** 2 + (z - z0) ** 2
                    if best is None or d < best[0]:
                        best = (d, x, z)
            if best is None:
                raise RuntimeError(f"îles : pas de place pour {role} sur {island['name']}")
            p.set(best[1], 0, best[2], SPAWNER + role)
            out.append((best[1], 0, best[2]))
    return out


def halt_prefab(island, seed):
    """Petite île de halte : place, garde-corps, le motif de la halte au centre, un petit groupe d'ennemis."""
    p = pf.Prefab(seed)
    rng = random.Random(seed)
    gates = _plaza(p, island, rng)
    {"fountain": lambda: _fountain(p, 0, 0, 3, 5, rng), "kiosk": lambda: _kiosk(p, rng),
     "springs": lambda: _springs(p, rng), "arches": lambda: _arches(p, rng)}[island["feature"]]()
    _mobs(p, island, gates)
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
            n = math.hypot(gx, gz)
            sx, sz = -gz / n, gx / n  # en travers de l'allée
            x, z = gx * t, gz * t
            for w in (-3, 3):
                px, pz = round(x + sx * w), round(z + sz * w)
                p.set(px, 0, pz, PILLAR_BASE)
                for y in range(1, 5):
                    p.set(px, y, pz, PILLAR)
            for w in range(-3, 4):
                px, pz = round(x + sx * w), round(z + sz * w)
                p.set(px, 5, pz, "Plant_Leaves_Wisteria_Wild")
                if abs(w) < 3 and rng.random() < 0.6:
                    p.set(px, 4, pz, VINES)
    _mobs(p, GARDENS, gates)
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
        if _in_lane(x, z, gates, 4):
            continue  # allées vers les ouvertures
        h = rng.randint(2, 7)
        p.set(x, 0, z, PILLAR_BASE)
        for y in range(1, h):
            p.set(x, y, z, "Rock_Marble_Brick_Pillar_Middle")
        if rng.random() < 0.5:
            p.set(x, h, z, "Plant_Flower_Bushy_Violet")
    for _ in range(16):
        a, r = rng.uniform(0, 360), rng.uniform(7, 20)
        x, z = round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))
        if _in_lane(x, z, gates, 3) or not p.free(x, 0, z):
            continue
        p.set(x, 0, z, rng.choice(CRYSTALS))
    for x, z in ((8, 8), (-16, -10), (6, -16)):
        p.set(x, 2, z, "Nakasar_Tower_Emanation_Mist")
    # Point de contrôle devant la sortie (vers la halte des arches), statue à l'est de l'allée, tournée vers elle.
    gx, gz = gates[1]
    n = math.hypot(gx, gz)
    sx, sz = round(gx - 6 * gx / n), round(gz - 6 * gz / n)
    spot = (sx, 0, sz)
    p.set(sx + 5, -1, sz, ORNATE)
    p.set(sx + 5, 0, sz, STATUE, pf.WEST)
    _mobs(p, RUINS, gates)
    return p, spot, ((sx + 5, 0, sz), pf.WEST)


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
