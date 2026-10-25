"""Terrain et décor du Récif de la Sirène (Siren's Reef, GW2), d'après les guides MetaBattle et Hardstuck.

Une île de jungle entourée de mer et fermée par une barrière de corail. Du sud au nord : la plage du naufrage (le
capitaine Strohm et le mousse Weyandt), le rivage aux camps de sauriens, la clairière de Tête-de-pierre, le ravin miné
(le canon des ombres sur sa corniche), le fort englouti de Black Peter la Mèche, le sentier de jungle aux raptors, la
grande tête de pierre dont la bouche s'ouvre sur le labyrinthe des trésors maudits, puis la crique : la plage sud, le
Fierté du Kraken d'Arabella Crowe au mouillage, la plage nord.

Repère : x vers l'est, z vers le sud, y = GROUND_Y + y prefab. « debout à s » : le sol est en s - 1. La mer : surface
de l'eau en y = -1, fond de sable de -2 à -4 selon la distance au rivage. Les lieux praticables (taches et chemins
courbes) ont un sol plat par lieu ; tout le reste est mer (autour des lieux du rivage) ou falaise de jungle (autour des
lieux de l'intérieur) : au moins six blocs au bord, puis elle monte. Rien n'est tiré au hasard : un prefab régénéré est
identique.
"""
import math
import random
import heapq
from collections import deque

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

pick = fc.pick
AIR = go.AIR
WATER = "Water_Source"

SAND = ["Soil_Sand", "Soil_Sand", "Soil_Sand_White", "Soil_Sand", "Soil_Gravel_Sand"]
SEA_FLOOR = ["Soil_Sand", "Soil_Gravel_Sand", "Soil_Sand", "Soil_Clay_Ocean", "Soil_Sand"]
GRASS = ["Soil_Grass_Deep", "Soil_Grass", "Soil_Grass_Full", "Soil_Grass_Deep"]
DIRT = ["Soil_Dirt", "Soil_Dirt", "Soil_Clay"]
CLIFF = ["Rock_Stone_Mossy", "Rock_Stone", "Rock_Shale", "Rock_Stone_Mossy", "Rock_Slate", "Rock_Stone_Cobble_Mossy"]
REEF = ["Plant_Coral_Block_Pink", "Rock_Stone_Mossy", "Plant_Coral_Block_Orange", "Rock_Shale",
        "Plant_Coral_Block_Purple", "Plant_Coral_Block_Red", "Rock_Stone"]
CORALS = ["Plant_Coral_Bush_Pink", "Plant_Coral_Model_Orange", "Plant_Coral_Bush_Purple", "Plant_Coral_Model_Yellow",
          "Plant_Coral_Bush_Red", "Plant_Coral_Model_Pink", "Plant_Coral_Bush_Orange"]
SHELLS = ["Deco_Coral_Shell", "Deco_Coral_Shell_Purple", "Deco_Coral_Shell_Sanddollar", "Deco_Coral_Shell_Swirly",
          "Deco_Coral_Shell_Urchin"]
FORT = ["Rock_Sandstone_Brick", "Rock_Sandstone_Cobble", "Rock_Stone_Brick_Mossy", "Rock_Sandstone_Brick",
        "Rock_Stone_Cobble_Mossy"]
FORT_FLOOR = ["Rock_Sandstone_Brick_Smooth", "Soil_Sand", "Rock_Sandstone_Cobble", "Soil_Sand"]
HEAD = ["Rock_Stone", "Rock_Stone_Mossy", "Rock_Stone", "Rock_Stone_Cobble_Mossy"]
TEETH = "Rock_Stone_Brick_Mossy"
HULL = "Wood_Darkwood_Planks"
DECK = ["Wood_Darkwood_Planks", "Wood_Deadwood_Planks", "Wood_Darkwood_Planks"]
MAST = "Wood_Fir_Trunk"
SAIL = ["Cloth_Block_Wool_Black", "Cloth_Block_Wool_Gray", "Cloth_Block_Wool_Black"]
SAIL_MARK = "Cloth_Block_Wool_White"
HANG = ["Plant_Vine_Green_Hanging", "Plant_Vine_Hanging"]
TORCH = "Furniture_Crude_Torch"
BRAZIER = "Furniture_Crude_Brazier"

JUNGLE_FLORA = fn._theme(
    soil=GRASS, dirt=DIRT, deep=CLIFF,
    short=["Plant_Grass_Jungle_Short", "Plant_Grass_Jungle", "Plant_Grass_Lush_Short"],
    tall=["Plant_Grass_Jungle_Tall", "Plant_Grass_Jungle", "Plant_Fern_Jungle"],
    flowers=[["Plant_Fern_Jungle", "Plant_Bush_Jungle"], ["Plant_Grass_Jungle_Tall", "Plant_Fern_Jungle"]],
    bushes=["Plant_Bush_Jungle", "Plant_Fern_Jungle", "Plant_Bush_Lush"], hang=HANG,
    rocks=["Rock_Stone_Mossy", "Rock_Stone_Cobble_Mossy", "Rock_Stone", "Rock_Shale"])

DMAX = 22                       # falaise posée jusqu'à cette distance des lieux praticables
SEA_BAND = 20                   # mer jusqu'à cette distance du rivage ; les trois dernières rangées : barrière de corail

# --- la carte -------------------------------------------------------------------------------------------
# Taches : (nom, cx, cz, rx, rz, debout, au bord de la mer).
BLOBS = [
    ("beach", 40, 146, 25, 15, 1, True),
    ("camp_a", 26, 121, 10, 9, 1, True),
    ("camp_b", -4, 117, 10, 9, 2, False),
    ("camp_c", -12, 88, 11, 9, 2, False),
    ("bend", -40, 84, 8, 7, 2, False),
    ("clearing", -54, 60, 18, 15, 2, False),
    ("ledge", -64, 46, 4, 4, 6, False),
    ("fort", 4, -40, 22, 19, 1, True),
    ("rampart", 14, -54, 5, 3, 5, True),
    ("glade_a", -30, -70, 9, 8, 2, False),
    ("glade_b", -46, -92, 8, 8, 2, False),
    ("plaza", -44, -108, 10, 7, 2, False),
    ("south_beach", 26, -175, 30, 8, 1, True),
    ("north_beach", 30, -223, 30, 8, 1, True),
]
SEA_BLOBS = {name for name, *_, sea in BLOBS if sea}
FLAT = {"ledge", "rampart"}                     # bord net : plates-formes surélevées
# Chemins : points (x, z, debout, demi-largeur) lissés en courbe ; la mer longe ceux de SEA_PATHS.
PATHS = {
    # Le rivage serpente d'un camp à l'autre (pas de ligne droite de la plage à la clairière).
    "shore": [(40, 146, 1, 7), (34, 132, 1, 6), (26, 121, 1, 5.5), (12, 116, 2, 5), (-4, 117, 2, 5), (-12, 104, 2, 5),
              (-12, 88, 2, 5), (-26, 86, 2, 5), (-40, 84, 2, 5), (-50, 72, 2, 5), (-54, 60, 2, 5)],
    "ledge_ramp": [(-58, 56, 2, 1.8), (-60, 53, 3, 1.8), (-62, 50, 4, 1.8), (-63, 48, 5, 1.8), (-64, 46, 6, 1.8)],
    # Le ravin ondule à peine (± 3 blocs) : le canon de la corniche doit voir ses mines.
    "ravine": [(-55, 47, 2, 3.5), (-52, 36, 2, 3.5), (-41, 25, 2, 3.5), (-34, 12, 2, 3.5), (-20, 3, 2, 3.5),
               (-15, -10, 2, 3.5), (-6, -19, 1, 4)],
    "rampart_ramp": [(6, -44, 1, 1.8), (8, -47, 2, 1.8), (10, -50, 3, 1.8), (12, -52, 4, 1.8), (14, -54, 5, 1.8)],
    "jungle": [(-15, -48, 1, 4.5), (-27, -55, 2, 4.5), (-30, -70, 2, 4.5), (-25, -81, 2, 4), (-38, -87, 2, 4),
               (-46, -92, 2, 4), (-38, -100, 2, 4), (-44, -106, 2, 4.5)],
    "mouth": [(-44, -108, 2, 2.6), (-44, -118, 2, 2.6), (-44, -126, 2, 2.6)],
    "exit": [(-18, -170, 2, 2.6), (-8, -173, 2, 3.5), (4, -175, 1, 4.5)],
}
SEA_PATHS = set()
RAMPS = {"ledge_ramp", "rampart_ramp"}

# --- lieux de jeu (debout à y) -----------------------------------------------------------------------------
SPAWN = (46, 1, 152)
STROHM_AT = (50, 1, 149)
WEYANDT_AT = (48, 1, 154)
WRECK = (60, 152)                                # épave échouée sur la plage, à l'est
CAMPS = {  # nom : (centre, rôles)
    "camp_a": ((26, 121), ["bristleback", "bristleback"]),
    "camp_b": ((-4, 117), ["bonebreaker"]),
    "camp_c": ((-12, 88), ["smokescale", "smokescale"]),
}
RAPTOR_ROAM = (-40, 84)                          # meute de raptors de poche du rivage
CLEARING = (-54, 60)
CLEARING_RADIUS = 16
STONEHEAD_AT = (-56, 2, 64)
WALL1_AT = (-54, 50)                             # barrière de rochers entre la clairière et le ravin (Tête-de-pierre la brise)
CANNON_LEDGE = (-64, 6, 46)                      # canon des ombres sur sa corniche, face au ravin
MINE_FRACTIONS = (0.2, 0.45, 0.7)                # mines du ravin, le long du chemin
WALL2_AT = (-8, -17)                             # palissade au bout du ravin, que le canon doit abattre
FORT_C = (4, -40)
FORT_RADIUS = 18
PETER_AT = (6, 1, -38)
FORT_CANNON = (14, 5, -55)
FORT_GATE_AT = (-14, -47)                        # sortie vers la jungle, ouverte à la mort de Black Peter
GLADES = [(-30, -70), (-46, -92)]
PLAZA = (-44, -108)
HEAD_Z = -116                                    # la face de la tête de pierre (rangée z)
HEAD_HALF = 12
MOUTH_HALF = 2                                   # bouche : 5 de large
MOUTH_HEIGHT = 5
MAZE = (-78, -14, -180, -128)                    # x0, x1, z0, z1
MAZE_CELL = 8
MAZE_STAND = 2
SHIP_X = (8, 52)                                 # proue à l'est
SHIP_Z = -199
SHIP_HALF = 6
DECK_STAND = 5
DECK_C = (30, DECK_STAND, -199)
GANGPLANKS = [(30, -184, -193), (30, -214, -205)]  # (x, z sur la plage, z au bastingage)
SOUTH_TREASURE = (6, 1, -176)
NORTH_TREASURE = (52, 1, -224)
REWARD_AT = (26, DECK_STAND, -197)
END_EXIT_AT = (26, DECK_STAND, -201)


# --- courbes ---------------------------------------------------------------------------------------------

def curve(points, step=0.5):
    """Catmull-Rom par les points (x, z, debout, demi-largeur) : échantillons tous les `step` blocs, debout et largeur
    interpolés linéairement."""
    pts = [points[0]] + list(points) + [points[-1]]
    dense = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(4, int(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) * 2))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            x, z = (0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                           + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1))
            dense.append((x, z, p1[2] + (p2[2] - p1[2]) * t, p1[3] + (p2[3] - p1[3]) * t))
    dense.append(tuple(points[-1]))
    out, run = [dense[0]], 0.0
    for a, b in zip(dense, dense[1:]):
        run += math.hypot(b[0] - a[0], b[1] - a[1])
        if run >= step:
            out.append(b)
            run = 0.0
    return out


def along(name, fraction):
    """Point (x, z) à `fraction` de la longueur du chemin `name`."""
    s = curve(PATHS[name])
    return s[min(len(s) - 1, int(fraction * (len(s) - 1)))]


def across(name, at, half, extra=0):
    """Cases d'une barrière en travers du chemin `name` au point `at` : la perpendiculaire à la courbe, de -half-extra à
    half+extra."""
    s = curve(PATHS[name])
    i = min(range(len(s)), key=lambda k: (s[k][0] - at[0]) ** 2 + (s[k][1] - at[1]) ** 2)
    a, b = s[max(0, i - 2)], s[min(len(s) - 1, i + 2)]
    dx, dz = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dz) or 1
    px, pz = -dz / n, dx / n
    cells = []
    for k in range(-int(half + extra) * 2, int(half + extra) * 2 + 1):
        c = (round(s[i][0] + px * k / 2), round(s[i][1] + pz * k / 2))
        if c not in cells:
            cells.append(c)
    return cells


# --- le labyrinthe -----------------------------------------------------------------------------------------

class Maze:
    """Labyrinthe des trésors maudits : grille de cellules de MAZE_CELL blocs, arbre couvrant tiré d'une graine fixe ;
    chaque passage est une courbe qui serpente entre les deux centres (jamais de couloir droit)."""

    def __init__(self):
        x0, x1, z0, z1 = MAZE
        self.nx = (x1 - x0) // MAZE_CELL
        self.nz = (z1 - z0) // MAZE_CELL
        self.ox = x0 + ((x1 - x0) - self.nx * MAZE_CELL) // 2 + MAZE_CELL // 2
        self.oz = z0 + ((z1 - z0) - self.nz * MAZE_CELL) // 2 + MAZE_CELL // 2
        rng = random.Random(9137)
        self.entry = self.cell_near(PATHS["mouth"][-1][:2])
        self.exit = self.cell_near(PATHS["exit"][0][:2])
        seen, stack, self.edges = {self.entry}, [self.entry], []
        while stack:
            c = stack[-1]
            nbs = [(c[0] + dx, c[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nbs = [n for n in nbs if 0 <= n[0] < self.nx and 0 <= n[1] < self.nz and n not in seen]
            if not nbs:
                stack.pop()
                continue
            n = nbs[rng.randrange(len(nbs))]
            seen.add(n)
            self.edges.append((c, n))
            stack.append(n)
        # Deux boucles : on peut se croiser sans revenir sur ses pas.
        extra = 0
        for i in range(self.nx - 1):
            for j in range(self.nz):
                a, b = (i, j), (i + 1, j)
                if extra < 2 and (a, b) not in self.edges and (b, a) not in self.edges and rng.random() < 0.12:
                    self.edges.append((a, b))
                    extra += 1
        self.degree = {}
        for a, b in self.edges:
            self.degree[a] = self.degree.get(a, 0) + 1
            self.degree[b] = self.degree.get(b, 0) + 1
        self.depth = self._depths()

    def cell_near(self, at):
        i = min(self.nx - 1, max(0, round((at[0] - self.ox) / MAZE_CELL)))
        j = min(self.nz - 1, max(0, round((at[1] - self.oz) / MAZE_CELL)))
        return (i, j)

    def center(self, c):
        jitter = 1.6
        return (self.ox + c[0] * MAZE_CELL + jitter * fn.fbm2(c[0] * 13, c[1] * 7, 3, 1, 9140),
                self.oz + c[1] * MAZE_CELL + jitter * fn.fbm2(c[1] * 11, c[0] * 5, 3, 1, 9141))

    def _depths(self):
        nb = {}
        for a, b in self.edges:
            nb.setdefault(a, []).append(b)
            nb.setdefault(b, []).append(a)
        depth, queue = {self.entry: 0}, deque([self.entry])
        while queue:
            c = queue.popleft()
            for n in nb.get(c, []):
                if n not in depth:
                    depth[n] = depth[c] + 1
                    queue.append(n)
        return depth

    def paths(self):
        """Passages : (x, z, debout, demi-largeur), du centre d'une cellule à l'autre par un point de côté."""
        out = []
        for a, b in self.edges:
            (ax, az), (bx, bz) = self.center(a), self.center(b)
            mx, mz = (ax + bx) / 2, (az + bz) / 2
            side = 2.2 * fn.fbm2(a[0] * 17 + b[0], a[1] * 19 + b[1], 2, 1, 9142)
            if a[0] != b[0]:
                mz += side
            else:
                mx += side
            out.append([(ax, az, MAZE_STAND, 2.0), (mx, mz, MAZE_STAND, 1.8), (bx, bz, MAZE_STAND, 2.0)])
        return out

    def treasure_cells(self):
        """Les trois culs-de-sac les plus éloignés de l'entrée (ni l'entrée ni la sortie)."""
        ends = [c for c, d in self.degree.items() if d == 1 and c not in (self.entry, self.exit)]
        ends.sort(key=lambda c: (-self.depth.get(c, 0), c))
        picked = []
        for c in ends:
            if all(abs(c[0] - p[0]) + abs(c[1] - p[1]) >= 2 for p in picked):
                picked.append(c)
            if len(picked) == 3:
                break
        return picked

    def orb_cells(self):
        """Où partent les orbes spectrales : quatre carrefours éloignés les uns des autres."""
        cross = sorted([c for c, d in self.degree.items() if d >= 3 and c not in (self.entry, self.exit)],
                       key=lambda c: (-self.depth.get(c, 0), c))
        picked = []
        for c in cross + sorted(self.degree):
            if c not in picked and all(abs(c[0] - p[0]) + abs(c[1] - p[1]) >= 3 for p in picked):
                picked.append(c)
            if len(picked) == 4:
                break
        return picked


# --- le champ de hauteurs ----------------------------------------------------------------------------------

class Terrain:
    """Lieux praticables (`stand` {(x, z): debout}), mer (`sea` {(x, z): distance au rivage}), falaises (`top`)."""

    def __init__(self):
        self.maze = Maze()
        self.stand = {}
        self.blob_of = {}
        self.center = {}            # (x, z) -> (chemin, distance au milieu)
        self.coastal = set()        # cases praticables au bord de la mer
        self._paths()
        self._blobs()
        self._spread()

    def _paths(self):
        paths = dict(PATHS)
        for k, pts in enumerate(self.maze.paths()):
            paths[f"maze_{k}"] = pts
        self.all_paths = paths
        for name, pts in paths.items():
            for sx, sz, ss, half in curve(pts):
                reach = half + 1.2
                for x in range(math.floor(sx - reach), math.ceil(sx + reach) + 1):
                    for z in range(math.floor(sz - reach), math.ceil(sz + reach) + 1):
                        d = math.hypot(x - sx, z - sz)
                        wobble = 0 if name in RAMPS else 0.6 * fn.fbm2(x, z, 5, 2, 9201)
                        if d > half + wobble:
                            continue
                        old = self.center.get((x, z))
                        if old is None or d < old[1] or name in RAMPS:
                            if name in RAMPS or old is None or old[0] not in RAMPS:
                                self.center[(x, z)] = (name, d)
                                level = round(ss)
                                self.stand[(x, z)] = max(self.stand.get((x, z), 0), level) if name in RAMPS else level
                        if name in SEA_PATHS:
                            self.coastal.add((x, z))

    def _blobs(self):
        for name, cx, cz, rx, rz, stand, sea in BLOBS:
            for x in range(cx - rx - 4, cx + rx + 5):
                for z in range(cz - rz - 4, cz + rz + 5):
                    d = math.hypot((x - cx) / rx, (z - cz) / rz)
                    edge = 1.0 if name in FLAT else 1.0 + 0.14 * fn.fbm2(x, z, 8, 2, 9202 + cx)
                    if d > edge:
                        continue
                    if name not in FLAT and self.blob_of.get((x, z)) in FLAT:
                        continue
                    self.stand[(x, z)] = stand
                    self.blob_of[(x, z)] = name
                    if sea:
                        self.coastal.add((x, z))
                    else:
                        self.coastal.discard((x, z))

    def _spread(self):
        """Distance (8 voisins, diagonale 1,41) au lieu praticable le plus proche : mer autour du rivage, falaise
        ailleurs. La mer suit le rivage à distance (bande bruitée) et reste à quelques blocs des chemins de jungle :
        bords en courbes décalées, jamais les lignes droites d'un partage entre plage et chemin."""
        reach = max(DMAX, SEA_BAND + 6)
        self.dist, self.near = self._dijkstra(self.stand, reach)
        coast, _ = self._dijkstra(self.coastal, SEA_BAND + 6)
        land, _ = self._dijkstra([c for c in self.stand if c not in self.coastal], SEA_BAND + 6)
        self.sea, self.top = {}, {}
        for (x, z), d in self.dist.items():
            if d == 0:
                continue
            n = self.near[(x, z)]
            corridor = self.center.get(n, ("",))[0].startswith("maze_")
            c = coast.get((x, z))
            if c is not None and not corridor and c <= self.band(x, z) \
                    and land.get((x, z), 99) >= 4 + 1.5 * (fn.fbm2(x, z, 7, 2, 9209) + 1):
                self.sea[(x, z)] = c
                continue
            base = self.stand[n]
            lip = 6 + 6 * (fn.fbm2(x, z, 13, 2, 9204) + 1) / 2
            crag = 4 * abs(fn.fbm2(x, z, 6, 2, 9205))
            top = math.floor(base + lip + 0.9 * (d - 1) + crag + 3 * fn.fbm2(x, z, 23, 2, 9206))
            if corridor and d <= 3:
                top = base + 6 + (1 if fn.hash01(x, 0, z, 9207) < 0.3 else 0)   # haies du labyrinthe : pas d'escalade
            self.top[(x, z)] = max(top, base + 6)
        # La tête de pierre et le ravin : falaises plus hautes.
        for c, t in list(self.top.items()):
            if self.center.get(self.near[c], ("",))[0] == "ravine":
                self.top[c] = max(t, self.stand[self.near[c]] + 9 + math.floor(min(6, self.dist[c])))

    @staticmethod
    def _dijkstra(sources, reach):
        dist, near, heap = {}, {}, []
        for c in sources:
            dist[c] = 0
            near[c] = c
            heap.append((0, c))
        heapq.heapify(heap)
        while heap:
            d, (x, z) = heapq.heappop(heap)
            if d > dist[(x, z)] or d >= reach:
                continue
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (x + dx, z + dz)
                nd = d + (1.414 if dx and dz else 1)
                if nd < dist.get(n, 1e9):
                    dist[n] = nd
                    near[n] = near[(x, z)]
                    heapq.heappush(heap, (nd, n))
        return dist, near

    @staticmethod
    def band(x, z):
        """Largeur de la mer en (x, z) : SEA_BAND à ±3 près, pour un récif extérieur sinueux."""
        return SEA_BAND + 3 * fn.fbm2(x, z, 17, 2, 9210)

    def floor(self, x, z):
        """Dessus du fond de la mer (y du bloc de sable) en (x, z)."""
        d = self.sea[(x, z)]
        if d <= 2:
            return -2
        if d <= 6:
            return -3
        return -4 + (1 if fn.fbm2(x, z, 9, 2, 9208) > 0.45 else 0)

    def is_reef(self, x, z):
        return (x, z) in self.sea and self.sea[(x, z)] >= self.band(x, z) - 2.5

    def ground_top(self, x, z):
        """Hauteur du dessus de la case : y du plus haut bloc + 1 (l'eau compte comme vide)."""
        if (x, z) in self.stand:
            return self.stand[(x, z)]
        if (x, z) in self.top:
            return self.top[(x, z)]
        if (x, z) in self.sea:
            return self.floor(x, z) + 1
        return None


# --- pose du terrain ---------------------------------------------------------------------------------------

def lay_ground(p, t):
    """Sol des lieux praticables : sable au rivage, herbe de jungle ailleurs ; dessous jusqu'au plus bas voisin."""
    soils = []
    for (x, z), s in t.stand.items():
        coastal = (x, z) in t.coastal
        blob = t.blob_of.get((x, z))
        if blob == "fort":
            top = pick(FORT_FLOOR, x, s - 1, z)
        elif blob in FLAT or t.center.get((x, z), ("",))[0] in RAMPS:
            top = pick(FORT, x, s - 1, z) if blob == "rampart" or t.center.get((x, z), ("",))[0] == "rampart_ramp" else \
                pick(CLIFF, x, s - 1, z)
        elif coastal:
            top = pick(SAND, x, s - 1, z)
        else:
            top = pick(GRASS, x, s - 1, z)
            soils.append((x, s - 1, z))
        p.set(x, s - 1, z, top)
        nbs = [t.ground_top(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        low = min([v for v in nbs if v is not None] + [s]) - 3
        if any(v is None for v in nbs):
            low = min(low, -5)
        for y in range(low, s - 1):
            p.set(x, y, z, pick(SAND if coastal else DIRT, x, y, z) if y >= s - 4 else pick(CLIFF, x, y, z))
    return soils


def lay_sea(p, t):
    """Fond de sable, eau jusqu'en y = -1, barrière de corail sur les trois dernières rangées."""
    for (x, z), d in t.sea.items():
        if t.is_reef(x, z):
            top = -1 + int((fn.fbm2(x, z, 7, 2, 9301) + 1) * 1.8)
            for y in range(-6, top + 1):
                p.set(x, y, z, pick(REEF, x, y, z))
            if top >= 0 and fn.hash01(x, top, z, 9302) < 0.25:
                p.set(x, top + 1, z, CORALS[int(fn.hash01(z, x, top, 9303) * len(CORALS))])
            continue
        f = t.floor(x, z)
        nbs = [t.ground_top(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        low = min([v - 1 for v in nbs if v is not None] + [f]) - 1
        for y in range(low, f + 1):
            p.set(x, y, z, pick(SEA_FLOOR, x, y, z))
        for y in range(f + 1, 0):
            p.fluid(x, y, z, WATER)
        if f <= -3 and fn.hash01(x, f, z, 9304) < 0.06:
            p.set(x, f + 1, z, CORALS[int(fn.hash01(x, z, f, 9305) * len(CORALS))])
            p.fluids[(x, f + 1, z)] = (WATER, 1)


def lay_cliffs(p, t):
    """Falaises de jungle : roche moussue en bandes du sommet jusqu'au plus bas voisin, herbe sur le dessus, lianes."""
    tops = []
    for (x, z), top in t.top.items():
        nbs = [t.ground_top(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        known = [v for v in nbs if v is not None]
        low = min(known + [top]) - 1
        if len(known) < 4:
            low = min(low, top - 6)
        if any((x + dx, z + dz) in t.sea for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            low = min(low, -5)
        for y in range(low, top - 1):
            band = int((y + 3 * fn.vnoise2(x, z, 11, 9401)) // 3)
            p.set(x, y, z, CLIFF[band % len(CLIFF)] if fn.hash01(x, y, z, 9402) < 0.8 else pick(CLIFF, x, y, z))
        p.set(x, top - 1, z, pick(GRASS, x, top - 1, z))
        tops.append((x, top - 1, z))
        # lianes sur la face qui donne sur un lieu praticable
        drop = top - min(known + [top])
        if drop >= 4 and fn.hash01(x, top, z, 9403) < 0.16:
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, z + dz)
                if n in t.stand or n in t.sea:
                    for k in range(1 + int(fn.hash01(z, x, top, 9404) * min(6, drop - 2))):
                        y = top - 2 - k
                        if fn.free(p, x + dx, y, z + dz) and y > t.ground_top(*n):
                            p.set(x + dx, y, z + dz, HANG[int(fn.hash01(x, k, z, 9405) * 2)])
                    break
    return tops


# --- arbres et plantes ---------------------------------------------------------------------------------------

def palm(p, x, y, z, height, seed):
    """Palmier : tronc qui s'incline peu à peu, couronne de six palmes qui retombent, noix de coco sous la couronne."""
    a = fn.hash01(x, y, z, seed) * math.tau
    lean = 0.18 + fn.hash01(z, y, x, seed + 1) * 0.22
    cx, cz = float(x), float(z)
    for k in range(height):
        cx += math.cos(a) * lean * (k / height) * 1.6
        cz += math.sin(a) * lean * (k / height) * 1.6
        p.set(round(cx), y + k, round(cz), "Wood_Palm_Trunk")
    tx, ty, tz = round(cx), y + height, round(cz)
    p.set(tx, ty, tz, "Plant_Leaves_Palm")
    for f in range(6):
        b = f * math.tau / 6 + fn.hash01(f, x, z, seed + 2) * 0.5
        for r in range(1, 5):
            dy = 0 if r < 2 else -(r - 1) // 2
            fx, fz = tx + round(math.cos(b) * r), tz + round(math.sin(b) * r)
            if fn.free(p, fx, ty + dy, fz):
                p.set(fx, ty + dy, fz, "Plant_Leaves_Palm")
    for dx, dz in ((1, 0), (-1, 0), (0, 1)):
        if fn.hash01(tx + dx, ty, tz + dz, seed + 3) < 0.6 and fn.free(p, tx + dx, ty - 1, tz + dz):
            p.set(tx + dx, ty - 1, tz + dz, "Plant_Fruit_Coconut")


def jungle_tree(p, x, y, z, height, seed):
    """Grand arbre de jungle : tronc à contreforts, houppier large d'où pendent des lianes."""
    fn.broadleaf(p, x, y, z, height, "jungle", seed, droop=0.14, hanging=HANG)
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if fn.hash01(x + dx, y, z + dz, seed + 5) < 0.5:
            p.set(x + dx, y, z + dz, "Wood_Jungle_Trunk")
            if fn.hash01(x + dx, y + 1, z + dz, seed + 6) < 0.5:
                p.set(x + dx, y + 1, z + dz, "Wood_Jungle_Trunk")


def driftwood(p, x, y, z, seed):
    """Bois flotté couché sur le sable (trois ou quatre bûches de bois mort)."""
    horizontal = fn.hash01(x, y, z, seed) < 0.5
    for k in range(3 + int(fn.hash01(z, x, y, seed + 1) * 2)):
        cx, cz = (x + k, z) if horizontal else (x, z + k)
        if fn.free(p, cx, y, cz):
            p.set(cx, y, cz, "Wood_Deadwood_Planks" if k % 2 else "Wood_Palm_Trunk")


def ok_spot(t, x, z, keep):
    return not any(math.hypot(x - kx, z - kz) <= r for kx, kz, r in keep)


def dress_beaches(p, t, keep):
    """Palmiers et coquillages sur le sable, bois flotté, rochers ; jamais dans les cercles `keep` (x, z, r)."""
    placed = []
    for (x, z), s in sorted(t.stand.items()):
        if (x, z) not in t.coastal or not fn.free(p, x, s, z) or not ok_spot(t, x, z, keep):
            continue
        path = t.center.get((x, z))
        if path and path[1] < 3.5:
            continue
        h = fn.hash01(x, s, z, 9501)
        if h < 0.012 and all(math.hypot(x - a, z - b) >= 7 for a, b in placed):
            placed.append((x, z))
            palm(p, x, s, z, 6 + int(fn.hash01(z, x, s, 9502) * 5), 9503 + x * 3 + z)
        elif h < 0.03:
            p.set(x, s, z, SHELLS[int(fn.hash01(z, s, x, 9504) * len(SHELLS))])
        elif h < 0.034:
            driftwood(p, x, s, z, 9505)
        elif h < 0.04:
            fn.boulder(p, x, s, z, 0.9 + fn.hash01(x, z, s, 9506) * 0.8, 9507 + x, rocks=JUNGLE_FLORA["rocks"])


def dress_jungle(p, t, soils, cliff_tops, keep):
    """Jungle : grands arbres sur les falaises, palmiers et fougères aux lisières, herbes partout."""
    trees = []
    for x, y, z in sorted(cliff_tops):
        if not ok_spot(t, x, z, keep) or not fn.free(p, x, y + 1, z):
            continue
        h = fn.hash01(x, y, z, 9601)
        if h < 0.045 and all(math.hypot(x - a, z - b) >= 6 for a, b in trees):
            trees.append((x, z))
            if fn.hash01(z, y, x, 9602) < 0.7:
                jungle_tree(p, x, y + 1, z, 8 + int(fn.hash01(x, z, y, 9603) * 6), 9604 + x + z * 7)
            else:
                palm(p, x, y + 1, z, 7 + int(fn.hash01(x, z, y, 9605) * 5), 9606 + x * 5 + z)
        elif h < 0.12:
            p.set(x, y + 1, z, JUNGLE_FLORA["bushes"][int(fn.hash01(z, x, y, 9607) * 3)])
    fn.flora(p, [c for c in cliff_tops if fn.free(p, c[0], c[1] + 1, c[2])], 9608, 0.6, 0.1, theme=JUNGLE_FLORA)
    edge = []
    for x, y, z in soils:
        path = t.center.get((x, z))
        if path and path[0].startswith("maze"):
            continue
        if path and path[1] < max(2.0, half_of(t, path[0]) - 1.5):
            continue
        if ok_spot(t, x, z, keep):
            edge.append((x, y, z))
    for x, y, z in edge:
        h = fn.hash01(x, y, z, 9609)
        if h < 0.05 and fn.free(p, x, y + 1, z):
            p.set(x, y + 1, z, JUNGLE_FLORA["bushes"][int(fn.hash01(z, x, y, 9610) * 3)])
    fn.flora(p, [c for c in soils if fn.free(p, c[0], c[1] + 1, c[2]) and ok_spot(t, c[0], c[2], keep)], 9611, 0.5,
             0.08, theme=JUNGLE_FLORA)


def half_of(t, name):
    pts = t.all_paths.get(name)
    return max(pt[3] for pt in pts) if pts else 4


# --- constructions ---------------------------------------------------------------------------------------

def wreck(p, t):
    """Épave échouée sur la plage du départ : coque éventrée de bois sombre couchée sur le flanc, mât brisé."""
    cx, cz = WRECK
    for k in range(-9, 10):
        w = 3.5 * math.sqrt(max(0.0, 1 - (k / 10) ** 2))
        for side in (-1, 1):
            for h in range(0, 4):
                zz = cz + round(side * (w - h * 0.4))
                if fn.hash01(cx + k, h, zz, 9701) < (0.25 if h == 3 else 0.12):
                    continue
                y = t.stand.get((cx + k, zz), 1) - 1 + h + (1 if side > 0 else 0)
                p.set(cx + k, y, zz, HULL if fn.hash01(k, h, side, 9702) < 0.7 else "Wood_Deadwood_Planks")
        if k % 3 == 0:
            y = t.stand.get((cx + k, cz), 1)
            p.set(cx + k, y - 1, cz, "Wood_Deadwood_Planks")
    for k in range(5):
        p.set(cx - 2 + k, t.stand.get((cx, cz), 1) + 1 + k // 2, cz + 1, MAST)
    for dx, dz, block in ((-4, -2, "Furniture_Tavern_Barrel"), (3, 3, "Furniture_Village_Crate"),
                          (-6, 2, "Furniture_Ancient_Crate"), (5, -3, "Deco_Rope")):
        x, z = cx + dx, cz + dz
        p.set(x, t.stand.get((x, z), 1), z, block)


def boulder_wall(p, t, cells, height, seed):
    """Barrière de rochers moussus en travers d'un chemin (Tête-de-pierre la brise)."""
    out = []
    for x, z in cells:
        s = t.stand.get((x, z))
        if s is None:
            continue
        for y in range(s, s + height):
            p.set(x, y, z, pick(["Rock_Stone_Mossy", "Rock_Stone_Cobble_Mossy", "Rock_Stone"], x, y, z))
            out.append((x, y, z))
    return out


def palisade(p, t, cells, height):
    """Palissade de rondins du bout du ravin (le canon des ombres l'abat)."""
    out = []
    for x, z in cells:
        s = t.stand.get((x, z))
        if s is None:
            continue
        for y in range(s, s + height + (1 if fn.hash01(x, 0, z, 9711) < 0.4 else 0)):
            p.set(x, y, z, "Wood_Jungle_Trunk")
            out.append((x, y, z))
    return out


def saurian_camp(p, t, cx, cz, seed):
    """Camp de sauriens : feu de braises, totems de rondins coiffés de crânes, tas d'os."""
    s = t.stand[(cx, cz)]
    p.set(cx, s, cz, BRAZIER)
    for k in range(3):
        a = k * math.tau / 3 + fn.hash01(cx, cz, k, seed) * 0.8
        x, z = round(cx + math.cos(a) * 6), round(cz + math.sin(a) * 6)
        if (x, z) not in t.stand:
            continue
        ss = t.stand[(x, z)]
        for y in range(3):
            p.set(x, ss + y, z, "Wood_Jungle_Trunk")
        p.set(x, ss + 3, z, "Deco_Bone_Skulls")
    for k in range(4):
        a = fn.hash01(cz, k, cx, seed + 1) * math.tau
        x, z = round(cx + math.cos(a) * 4), round(cz + math.sin(a) * 4)
        if (x, z) in t.stand and fn.free(p, x, t.stand[(x, z)], z):
            p.set(x, t.stand[(x, z)], z, ("Deco_Bone_Pile", "Deco_Bone_Ribs", "Deco_Bone_Skulls", "Deco_Bone_Spike")[k])


def fort(p, t):
    """Fort englouti : enceinte de grès en ruine (brèches, tours rongées), flaques d'eau de mer, rempart du canon."""
    cx, cz = FORT_C
    keep_open = [(-6, -20), FORT_GATE_AT, (8, -46)]    # entrée du ravin, sortie jungle, rampe du rempart
    for a10 in range(0, 3600, 7):
        a = math.radians(a10 / 10)
        r = FORT_RADIUS + 0.8 * fn.fbm2(a10, 0, 40, 2, 9801)
        x, z = round(cx + math.cos(a) * r * 1.12), round(cz + math.sin(a) * r)
        if (x, z) not in t.stand or any(math.hypot(x - kx, z - kz) < 4.5 for kx, kz in keep_open):
            continue
        s = t.stand[(x, z)]
        height = 1 + int((fn.fbm2(a10, 3, 70, 2, 9802) + 1) * 2.6)
        if fn.fbm2(a10, 5, 90, 1, 9803) > 0.5:
            height = 0                                  # brèche
        for y in range(s, s + height):
            p.set(x, y, z, pick(FORT, x, y, z))
    for k in range(4):
        a = math.radians(45 + k * 90 + 10)
        tx, tz = round(cx + math.cos(a) * FORT_RADIUS * 1.12), round(cz + math.sin(a) * FORT_RADIUS)
        if (tx, tz) not in t.stand:
            continue
        s = t.stand[(tx, tz)]
        top = 5 + int(fn.hash01(tx, k, tz, 9804) * 4)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) + abs(dz) > 3 or (tx + dx, tz + dz) not in t.stand:
                    continue
                for y in range(s, s + top - (abs(dx) + abs(dz)) - int(fn.hash01(dx, k, dz, 9805) * 3)):
                    p.set(tx + dx, y, tz + dz, pick(FORT, tx + dx, y, tz + dz))
    # flaques : eau d'un bloc dans le dallage (hors du centre où se bat Black Peter)
    for (x, z), s in t.stand.items():
        if t.blob_of.get((x, z)) != "fort" or math.hypot(x - cx, z - cz) < 7:
            continue
        if fn.fbm2(x, z, 6, 2, 9806) > 0.55 and all(t.stand.get((x + dx, z + dz)) == s
                                                   for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            p.set(x, s - 2, z, pick(SAND, x, s - 2, z))
            p.fluid(x, s - 1, z, WATER)
    # le rempart : parapet sur le bord nord, la rampe reste ouverte
    for (x, z), s in t.stand.items():
        if t.blob_of.get((x, z)) != "rampart":
            continue
        if any(t.stand.get((x + dx, z + dz), 0) < s - 1 and (x + dx, z + dz) not in t.center
               for dx, dz in ((1, 0), (-1, 0), (0, -1))) and z <= -54:
            p.set(x, s, z, pick(FORT, x, s, z))
    for dx, dz in ((-3, 2), (3, 2)):
        p.set(FORT_CANNON[0] + dx, FORT_CANNON[1], FORT_CANNON[2] + dz, "Furniture_Tavern_Barrel")


def stone_head(p, t):
    """La grande tête de pierre : visage taillé dans la falaise au nord de la place, orbites à braises, nez, et la
    bouche (cinq de large, cinq de haut) fermée de dents de pierre que le Java retire."""
    cx = PLAZA[0]
    z = HEAD_Z
    base = t.stand.get((cx, z), 2)
    teeth = []
    for dx in range(-HEAD_HALF, HEAD_HALF + 1):
        w = abs(dx) / HEAD_HALF
        height = round(20 * math.sqrt(max(0.0, 1 - w ** 2.4))) + 2
        for y in range(base - 1, base + height):
            for dz in (0, -1, -2):
                cell = (cx + dx, y, z + dz)
                if abs(dx) <= MOUTH_HALF and y < base + MOUTH_HEIGHT:
                    if dz == 0:
                        if y >= base:
                            p.set(*cell, TEETH)
                            teeth.append(cell)
                        continue
                    if y >= base:
                        continue                        # gorge : passage derrière les dents
                p.set(*cell, pick(HEAD, cell[0], y, cell[2]))
    # relief : arcades sourcilières, orbites creuses avec braises, nez
    for side in (-1, 1):
        ex = cx + side * 5
        for dx in range(-2, 3):
            for y in range(base + 11, base + 14):
                p.set(ex + dx, y, z + 1, pick(HEAD, ex + dx, y, z))
        for dx in range(-1, 2):
            for y in range(base + 8, base + 11):
                p.set(ex + dx, y, z, AIR)
        p.set(ex, base + 8, z - 1, BRAZIER)
    for y in range(base + 6, base + 11):
        p.set(cx, y, z + 1, pick(HEAD, cx, y, z))
        if y < base + 8:
            for dx in (-1, 1):
                p.set(cx + dx, y, z + 1, pick(HEAD, cx + dx, y, z))
    for dx in range(-MOUTH_HALF - 1, MOUTH_HALF + 2):
        p.set(cx + dx, base + MOUTH_HEIGHT, z + 1, pick(HEAD, cx + dx, base, z))
    for dx in (-MOUTH_HALF - 3, MOUTH_HALF + 3):
        p.set(cx + dx, base, z + 2, TORCH)
    return teeth


def maze_decor(p, t, keep):
    """Labyrinthe : os et trésors épars dans les recoins, lanternes aux carrefours."""
    for c in t.maze.degree:
        x, z = (round(v) for v in t.maze.center(c))
        if (x, z) not in t.stand or not ok_spot(t, x, z, keep):
            continue
        s = t.stand[(x, z)]
        d = t.maze.degree[c]
        for k, (dx, dz) in enumerate(((2, 1), (-2, -1), (1, -2))):
            cx, cz = x + dx, z + dz
            if (cx, cz) in t.stand and fn.free(p, cx, s, cz) and fn.hash01(cx, k, cz, 9901) < (0.5 if d == 1 else 0.25):
                p.set(cx, s, cz, ("Deco_Bone_Pile", "Deco_Treasure_Pile_Small", "Deco_Bone_Skulls")[k])
        if d >= 3:
            p.set(x + 2, s, z - 2, "Deco_Lantern") if (x + 2, z - 2) in t.stand else None


def ship(p, t):
    """Le Fierté du Kraken : coque de bois sombre (proue fine à l'est, poupe carrée à l'ouest), pont plat, bastingage
    ouvert aux passerelles, trois mâts aux voiles noires. Rend les cases du pont {(x, z)}."""
    x0, x1 = SHIP_X
    deck = {}
    gaps = {(gx, s) for gx, _, s in GANGPLANKS for gx in range(gx - 1, gx + 2)}
    for x in range(x0, x1 + 1):
        u = (x - x0) / (x1 - x0)
        half = SHIP_HALF * (math.sqrt(max(0.0, 1 - ((u - 0.55) / 0.45) ** 2)) if u > 0.55 else 1.0)
        half = max(1.0, half) if u <= 1 else 0
        for z in range(SHIP_Z - SHIP_HALF - 1, SHIP_Z + SHIP_HALF + 2):
            off = abs(z - SHIP_Z)
            if off > half + 0.4:
                continue
            edge = off > half - 0.6 or x in (x0, x1)
            keel = -3 + round((off / max(half, 1)) ** 2 * 2)
            if edge:
                for y in range(keel, DECK_STAND):
                    p.set(x, y, z, HULL if y != 1 else "Wood_Deadwood_Planks")
                if (x, z) not in gaps:
                    p.set(x, DECK_STAND, z, HULL)
            else:
                p.set(x, keel, z, HULL)
            p.set(x, DECK_STAND - 1, z, pick(DECK, x, 0, z))
            for y in range(keel + 1, DECK_STAND - 1):
                if not edge:
                    p.set(x, y, z, AIR)
            if not edge:
                deck[(x, z)] = DECK_STAND
    # mâts et voiles
    for mx, h in ((x0 + 9, 16), (30, 20), (x1 - 12, 15)):
        for y in range(DECK_STAND, DECK_STAND + h):
            p.set(mx, y, SHIP_Z, MAST)
        for k, y in enumerate(range(DECK_STAND + 6, DECK_STAND + h - 2)):
            w = 4 if k < 2 else 5
            for dz in range(-w, w + 1):
                if dz != 0:
                    mark = abs(dz) <= 1 and (DECK_STAND + h // 2) <= y <= (DECK_STAND + h // 2 + 1)
                    p.set(mx + 1, y, SHIP_Z + dz, SAIL_MARK if mark else pick(SAIL, mx, y, dz))
        for dz in range(-5, 6):
            p.set(mx + 1, DECK_STAND + h - 2, SHIP_Z + dz, MAST)
    for k in range(6):
        p.set(x1 + 1 + k, DECK_STAND + k // 2, SHIP_Z, MAST)                # beaupré
    p.set(x0 + 1, DECK_STAND, SHIP_Z, "Deco_Lantern")
    for dx, dz in ((-3, -4), (4, 4), (-8, 4), (10, -4)):
        p.set(30 + dx, DECK_STAND, SHIP_Z + dz, ("Furniture_Tavern_Barrel", "Furniture_Village_Crate")[(dx + dz) % 2])
    # passerelles
    for gx, beach_z, rail_z in GANGPLANKS:
        n = abs(rail_z - beach_z)
        step = -1 if rail_z < beach_z else 1
        for k in range(n + 1):
            z = beach_z + step * k
            stand = 1 + min(DECK_STAND - 1, round((k + 0.5) * (DECK_STAND - 1) / n))
            for dx in (-1, 0, 1):
                p.set(gx + dx, stand - 1, z, "Wood_Deadwood_Planks")
                for y in range(stand, stand + 3):
                    if (gx + dx, y, z) in p.blocks:
                        p.set(gx + dx, y, z, AIR)
                deck.setdefault((gx + dx, z), stand) if k == n else None
            for dx in (-2, 2):
                if k % 3 == 0:
                    for y in range(-3, stand):
                        p.set(gx + dx, y, z, MAST)
    return deck


def beach_camp(p, t, cx, cz, seed):
    """Ancien camp de pirates sur une plage de la crique : tonneaux, caisses, feu, cordages."""
    s = t.stand.get((cx, cz), 1)
    p.set(cx, s, cz, BRAZIER)
    for k in range(5):
        a = k * math.tau / 5 + fn.hash01(cx, k, cz, seed) * 0.6
        x, z = round(cx + math.cos(a) * 3.5), round(cz + math.sin(a) * 2.5)
        if (x, z) in t.stand and fn.free(p, x, t.stand[(x, z)], z):
            p.set(x, t.stand[(x, z)], z, ("Furniture_Tavern_Barrel", "Furniture_Village_Crate", "Deco_Rope",
                                          "Furniture_Ancient_Sack", "Deco_Treasure_Pile_Small")[k])
