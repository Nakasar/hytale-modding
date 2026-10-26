"""Terrain et décor du Pic de Sunqua (Sunqua Peak, GW2), d'après les guides MetaBattle et Hardstuck et la carte que
Kevin a envoyée (26 octobre 2026).

Un massif rocheux flotte au milieu d'un vide octogonal cerné de nuages ; sur ses flancs, des terrasses et des
corniches mènent au sommet. Du sud vers l'est, dans le sens des aiguilles d'une montre :

- l'îlot du départ (l'Esprit de la montagne) et l'escalier brisé : des îlots en marches qui montent vers le nord-ouest,
  trop hauts pour un saut ordinaire (Bond chargé), trois élémentaires d'air sur les plus grands ; le socle au bout ;
- une colonne de vent vers le plateau de la Voix de la montagne (disque de pierre au milieu de l'herbe), à l'ouest ;
- une seconde colonne vers la corniche des cascades, le long du flanc nord-ouest : deux cascades déferlent sur le
  chemin, trois élémentaires d'eau effrayés dans leurs niches, une barrière au bout ; des rochers flottants, puis la
  chute dans la terrasse de la Tristesse de la montagne (bassin, îlot moussu, rochers tombés) ;
- le sentier de lave vers l'est (trois murs de roche), le cratère de la Fureur de la montagne ;
- la montée vers l'arène ronde du sommet, à l'est (dalles, balustrade, arbres roses, cascade) : Ai.

Repère : x vers l'est, z vers le sud, y = GROUND_Y + y prefab. « debout à s » : le sol est en s - 1. Le massif est
écrit en coque (seulement les blocs visibles : fractal_nature.island). Rien n'est tiré au hasard sans graine : un
prefab régénéré est identique.
"""
import heapq
import math
from collections import deque

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

pick = fc.pick
AIR = go.AIR
hash01 = fn.hash01
fbm2 = fn.fbm2
WATER = "Water_Source"
LAVA = "Lava_Source"

# --- matières (vanilla) ----------------------------------------------------------------------------------------
GRASS = ["Soil_Grass_Deep", "Soil_Grass", "Soil_Grass_Full", "Soil_Grass_Sunny"]
DIRT = ["Soil_Dirt", "Soil_Dirt", "Soil_Clay"]
ROCK = ["Rock_Stone", "Rock_Stone_Mossy", "Rock_Slate", "Rock_Stone", "Rock_Shale", "Rock_Stone_Mossy"]
VOLCANIC_SOIL = ["Rock_Volcanic", "Soil_Ash", "Rock_Magma_Cooled", "Rock_Volcanic", "Soil_Grass_Burnt"]
VOLCANIC_DIRT = ["Rock_Volcanic", "Soil_Dirt_Burnt", "Rock_Basalt"]
VOLCANIC_DEEP = ["Rock_Volcanic", "Rock_Basalt", "Rock_Volcanic", "Rock_Magma_Cooled"]
TILE = ["Rock_Marble_Brick_Smooth", "Rock_Marble_Brick_Smooth", "Rock_Marble_Brick"]
TILE_RING = "Rock_Calcite_Brick_Smooth"
TILE_INLAY = "Rock_Quartzite_Brick_Ornate"
RAIL = "Rock_Marble_Brick_Wall"                  # balustrade (rotation selon la ligne : Prefab.orient)
PILLAR_BASE = "Rock_Marble_Brick_Pillar_Base"
PILLAR_MID = "Rock_Marble_Brick_Pillar_Middle"
DISC = ["Rock_Quartzite_Brick_Smooth", "Rock_Quartzite_Brick", "Rock_Quartzite_Brick_Smooth"]
LANTERN = "Furniture_Human_Ruins_Lantern"
BAMBOO = "Wood_Bamboo_Trunk"
BAMBOO_LEAVES = "Plant_Leaves_Bamboo"
MOSS = ["Plant_Moss_Rug_Green", "Plant_Moss_Rug_Lime", "Plant_Moss_Short_Green"]
PETALS = "Plant_Petals_Pink"
BARRIER = "Nakasar_Fractal_Mist_Barrier"          # barrière de brume de la Falaise
# Feuillage rose des cerisiers de Sunqua : la texture vanilla inutilisée Ball_Textures/Rhododendron_Pink sur le
# modèle de feuilles vanilla (generate_sunqua_peak.py écrit le bloc).
BLOSSOM = "Nakasar_Fractal_Sunqua_Blossom"
fn.TREES["blossom"] = ("Wood_Wisteria_Wild_Trunk", BLOSSOM)

SUNQUA = fn._theme(
    soil=GRASS, dirt=DIRT, deep=ROCK,
    short=["Plant_Grass_Lush_Short", "Plant_Grass_Lush", "Plant_Grass_Sharp_Short"],
    tall=["Plant_Grass_Lush_Tall", "Plant_Grass_Lush", "Plant_Fern_Forest"],
    flowers=[[PETALS, "Plant_Flower_Common_Pink", "Plant_Flower_Flax_Pink"],
             [PETALS, "Plant_Moss_Rug_Pink", "Plant_Flower_Orchid_Pink"],
             ["Plant_Flower_Common_White", "Plant_Flower_Common_Pink2", PETALS]],
    bushes=["Plant_Bush_Lush", "Plant_Fern_Forest", "Plant_Bush_Green", "Plant_Fern"],
    trees=["blossom", "blossom", "blossom", "oak"], conifers=[], droop=0.12,
    rocks=["Rock_Stone_Mossy", "Rock_Stone", "Rock_Stone_Cobble_Mossy", "Rock_Slate"])
VOLCANIC = fn.THEMES["volcanic"]

# --- la carte --------------------------------------------------------------------------------------------------
C = (0, -20)                    # centre du massif
R_MASSIF = 58                   # rayon du massif (à ± 4 près selon l'angle)
PEAK = 96                       # sommet du massif (y prefab)
DOME_EDGE = 14                  # hauteur du massif à son bord
CLIFF_LIP = 5                   # une falaise monte d'au moins cinq blocs au-dessus d'un lieu praticable du flanc
SKIRT = 9                       # le flanc remonte jusqu'à cette distance d'un lieu du flanc, côté montagne


def polar(theta, r):
    """Point (x, z) à l'angle `theta` (degrés, 0 à l'est, 90 au sud) et à `r` blocs du centre du massif."""
    a = math.radians(theta)
    return (C[0] + r * math.cos(a), C[1] + r * math.sin(a))


# Lieux ronds : (nom, x, z, rayon, debout, flanc). Un lieu du flanc s'adosse au massif (falaise côté montagne).
SPAWN = (0, 1, 136)
AREAS = [
    ("start", 0, 128, 12, 1, False),
    ("plinth", -70, 34, 8, 24, False),
    ("voice", -98, 4, 16, 40, False),
    ("sorrow", -2, -80, 15, 30, True),
    ("crater", 55, -52, 14, 36, True),
    ("summit", 88, 0, 18, 48, False),
]
AREA = {a[0]: a for a in AREAS}
# L'escalier brisé : îlots (x, z, debout, rayon) du départ au socle. Les trois grands portent un élémentaire d'air.
STEPS = [(-2, 111, 3, 3), (-7, 102, 5, 3), (-14, 92, 7, 5), (-21, 82, 10, 3), (-28, 75, 12, 3), (-36, 66, 14, 5),
         (-44, 57, 17, 3), (-50, 51, 19, 3), (-58, 44, 21, 5)]
ELEMENTAL_STEPS = [2, 5, 8]
STEP_GAP = (1, 4.5)             # bord à bord entre deux marches (blocs)
STEP_RISE = 3                   # montée la plus haute d'une marche : il faut deux charges de Bond chargé
# Chemins : points (x, z, debout, demi-largeur) lissés en courbe.
WATER_S = 50
LAVA_PATH = [(*polar(281, 62), 30, 3), (*polar(292, 63), 31, 3), (*polar(303, 64), 33, 3), (*polar(313, 64), 35, 3),
             (*polar(321, 64), 36, 3)]
PATHS = {
    "water": [(*polar(170, 62), WATER_S, 3.5), (*polar(185, 62), WATER_S, 3.5), (*polar(200, 62), WATER_S, 3.5),
              (*polar(215, 62), WATER_S, 3.5), (*polar(229, 62), WATER_S, 3.5)],
    "lava": LAVA_PATH,
    "rise": [(*polar(338, 66), 36, 3), (72, -36, 38, 3), (78, -29, 41, 3), (83, -23, 44, 3), (87, -17, 48, 3)],
}
FLANK_PATHS = {"water", "lava", "rise"}
# Niches des élémentaires d'eau effrayés (côté montagne de la corniche) : (x, z, rayon).
NOOKS = [(*polar(181, 55), 3.2), (*polar(205, 55), 3.2), (*polar(223, 55), 3.2)]
# Cascades qui déferlent sur la corniche : angle (degrés) ; la bande part du pied de la falaise vers le vide.
SURGES = [192, 213]
SURGE_LENGTH = 11               # Java : bande rouge de SURGE_LENGTH x SURGE_WIDTH (tools/generate_warnings.JAVA_LINES)
SURGE_WIDTH = 4
SURGE_FROM = 57.5               # rayon du départ de la bande (pied de la falaise)
WATER_GATE_THETA = 233
# Rochers flottants après la barrière : (theta, r, debout, rayon), puis le surplomb au-dessus de la Tristesse.
ROCKS = [(239, 64, 50, 2.5), (245, 66, 49, 2.5), (251, 66, 48, 2.5), (257, 67, 47, 2.5)]
BRINK = (-12, -88, 46, 2.5)     # x, z, debout, rayon : au-dessus du bord de la terrasse (chute amortie)
# Murs de lave : fractions du sentier.
LAVA_WALLS = (0.32, 0.62, 0.9)
LAVA_WALL_HEIGHT = 5
TIGERS = (0.68, 0.72)        # fractions du sentier de lave, entre le deuxième et le troisième mur

# --- lieux de jeu --------------------------------------------------------------------------------------------
SPIRIT_AT = (0, 1, 121)
START_ORBS = [(-4, 1, 119), (0, 1, 118), (4, 1, 119)]
PLINTH_C = (-70, 34)
# Colonnes de vent : départ (pieds), points du trajet (pieds), le dernier est l'arrivée.
COLUMN_1 = [(-73, 24, 29), (-73, 47, 29), (-86, 47, 15), (-88, 40, 13)]
VOICE_C = (-98, 4)
VOICE_R = 16
VOICE_STAND = 40
CLOUD_RING = 8.5                # nuages d'orage : à cette distance du centre, aux points cardinaux
CLOUD_HEIGHT = 5                # au-dessus du sol (il faut deux charges)
COLUMN_2 = [(-86, 40, -6), (-86, 56, -6), (-70, 56, -10), (round(polar(171, 62)[0]), WATER_S, round(polar(171, 62)[1]))]
SORROW_C = AREA["sorrow"][1:3]
SORROW_R = AREA["sorrow"][3]
SORROW_STAND = AREA["sorrow"][4]
POND_IN = 5                     # îlot moussu au milieu (Tristesse), bassin de POND_IN à POND_OUT
POND_OUT = 8.5
BOULDER_RING = 11.5
CRATER_C = AREA["crater"][1:3]
CRATER_R = AREA["crater"][3]
CRATER_STAND = AREA["crater"][4]
SUMMIT_C = AREA["summit"][1:3]
SUMMIT_R = AREA["summit"][3]
SUMMIT_STAND = AREA["summit"][4]


# --- courbes -----------------------------------------------------------------------------------------------

def curve(points, step=0.5):
    """Catmull-Rom par les points (x, z, debout, demi-largeur), échantillons tous les `step` blocs."""
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
    s = curve(PATHS[name])
    return s[min(len(s) - 1, int(fraction * (len(s) - 1)))]


def across(name, at, half):
    """Cases (x, z) d'une barrière en travers du chemin `name` au point `at` (perpendiculaire à la courbe)."""
    s = curve(PATHS[name])
    i = min(range(len(s)), key=lambda k: (s[k][0] - at[0]) ** 2 + (s[k][1] - at[1]) ** 2)
    a, b = s[max(0, i - 2)], s[min(len(s) - 1, i + 2)]
    dx, dz = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dz) or 1
    px, pz = -dz / n, dx / n
    cells = []
    for k in range(-int(half) * 2 - 1, int(half) * 2 + 2):
        c = (round(s[i][0] + px * k / 2), round(s[i][1] + pz * k / 2))
        if c not in cells:
            cells.append(c)
    return cells


def r_massif(x, z):
    """Rayon du bord du massif dans la direction de (x, z)."""
    a = math.atan2(z - C[1], x - C[0])
    return R_MASSIF + 9 * fbm2(math.cos(a) * 40, math.sin(a) * 40, 22, 3, 9801)


# --- le champ de hauteurs ----------------------------------------------------------------------------------

class Terrain:
    """`stand` {(x, z): debout} des lieux praticables, `top` {(x, z): y du bloc du dessus} de tout le relief (sol
    compris), `bottom` {(x, z): y du dessous}, `flank` (lieux adossés au massif), `kind` {(x, z): nom du lieu}."""

    def __init__(self):
        self.stand = {}
        self.kind = {}
        self.flank = set()
        self.center = {}
        self._areas()
        self._paths()
        self._relief()

    def _put(self, x, z, s, name, flank):
        self.stand[(x, z)] = s
        self.kind[(x, z)] = name
        if flank:
            self.flank.add((x, z))
        else:
            self.flank.discard((x, z))

    def _areas(self):
        for name, cx, cz, r, s, flank in AREAS:
            for x in range(cx - r - 3, cx + r + 4):
                for z in range(cz - r - 3, cz + r + 4):
                    d = math.hypot(x - cx, z - cz)
                    edge = r + (0 if name in ("summit", "voice", "crater") else 1.2 * fbm2(x, z, 7, 2, 9802 + cx))
                    if d <= edge:
                        self._put(x, z, s, name, flank)
        for k, (cx, cz, s, r) in enumerate(STEPS):
            self._blob(f"step_{k}", cx, cz, r, s, False, 9803 + k)
        for k, (theta, rr, s, r) in enumerate(ROCKS):
            cx, cz = (round(v) for v in polar(theta, rr))
            self._blob(f"rock_{k}", cx, cz, r, s, False, 9810 + k)
        self._blob("brink", BRINK[0], BRINK[1], BRINK[3], BRINK[2], False, 9820)
        for k, (cx, cz, r) in enumerate(NOOKS):
            self._blob(f"nook_{k}", round(cx), round(cz), r, WATER_S, True, 9821 + k)

    def _blob(self, name, cx, cz, r, s, flank, seed):
        n = int(r) + 3
        for x in range(cx - n, cx + n + 1):
            for z in range(cz - n, cz + n + 1):
                if math.hypot(x - cx, z - cz) <= r + 0.6 * fbm2(x, z, 4, 2, seed):
                    self._put(x, z, s, name, flank)

    def _paths(self):
        for name, pts in PATHS.items():
            for sx, sz, ss, half in curve(pts):
                reach = half + 1.2
                for x in range(math.floor(sx - reach), math.ceil(sx + reach) + 1):
                    for z in range(math.floor(sz - reach), math.ceil(sz + reach) + 1):
                        d = math.hypot(x - sx, z - sz)
                        if d > half + 0.6 * fbm2(x, z, 5, 2, 9830):
                            continue
                        old = self.center.get((x, z))
                        if (x, z) in self.stand and old is None:
                            continue                       # un lieu rond garde son sol
                        if old is None or d < old[1]:
                            self.center[(x, z)] = (name, d)
                            self._put(x, z, round(ss), name, name in FLANK_PATHS)

    def _relief(self):
        """Le massif : dôme (bord à DOME_EDGE, sommet PEAK) dans son rayon, et partout à moins de SKIRT blocs d'un
        lieu du flanc, côté montagne, une falaise d'au moins CLIFF_LIP blocs qui monte en s'éloignant."""
        dist, near = self._dijkstra(self.flank, 34)
        self.top, self.bottom = {}, {}
        cells = set()
        x0, x1 = C[0] - R_MASSIF - 10, C[0] + R_MASSIF + 10
        z0, z1 = C[1] - R_MASSIF - 10, C[1] + R_MASSIF + 10
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if math.hypot(x - C[0], z - C[1]) <= r_massif(x, z):
                    cells.add((x, z))
        for c, d in dist.items():
            if d == 0 or d > SKIRT:
                continue
            n = near[c]
            # côté montagne : plus près du centre que le lieu dont il borde
            if math.hypot(c[0] - C[0], c[1] - C[1]) < math.hypot(n[0] - C[0], n[1] - C[1]) - 0.5:
                cells.add(c)
        for (x, z) in cells:
            if (x, z) in self.stand:
                continue
            r = math.hypot(x - C[0], z - C[1])
            u = min(1.0, r / r_massif(x, z))
            # crêtes et ravines : bruit « en arête » (1 - |n|), fort au milieu des pentes
            ridge = 1 - abs(fbm2(x, z, 17, 3, 9846))
            dome = (DOME_EDGE + (PEAK - DOME_EDGE) * (1 - u * u) ** 1.25 + 5 * fbm2(x, z, 13, 2, 9840)
                    + 14 * (ridge - 0.5) * math.sin(math.pi * min(1.0, u)))
            top = dome
            d = dist.get((x, z))
            if d is not None:
                base = self.stand[near[(x, z)]]
                lip = CLIFF_LIP + 2 * (fbm2(x, z, 9, 2, 9841) + 1)
                cliff = base + lip + 0.9 * (d - 1) + 3 * abs(fbm2(x, z, 6, 2, 9842))
                top = max(top, cliff) if d > 3 else max(cliff, base + CLIFF_LIP)
            self.top[(x, z)] = math.floor(top)
            depth = 1 - min(1.0, r / R_MASSIF) ** 2
            self.bottom[(x, z)] = math.floor(-4 - 54 * max(0.0, depth) ** 0.7 + 5 * fbm2(x, z, 9, 2, 9843))
        for (x, z), s in self.stand.items():
            self.top[(x, z)] = s - 1
            if (x, z) in self.flank:
                self.bottom[(x, z)] = s - 14 - int(3 * (fbm2(x, z, 7, 2, 9844) + 1))

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

    def lava(self, x, z):
        """Le quart volcanique (sentier de lave, cratère et leurs flancs)."""
        if self.kind.get((x, z), "").startswith(("lava", "crater")):
            return True
        a = math.degrees(math.atan2(z - C[1], x - C[0])) % 360
        r = math.hypot(x - C[0], z - C[1])
        return 276 <= a <= 340 and r >= 38 + 4 * fbm2(x, z, 9, 2, 9845)


# --- pose ----------------------------------------------------------------------------------------------------

def lay_terrain(p, t):
    """Tout le relief en coque (fractal_nature.island) ; la part volcanique repeinte ensuite."""
    depth = {}
    for c, top in t.top.items():
        if c in t.bottom:
            depth[c] = top - t.bottom[c]
        else:
            # îlots flottants : dessous en cône
            depth[c] = None
    edge = fn.edge_distance(t.top)

    def depth_of(x, z):
        d = depth[(x, z)]
        if d is not None:
            return d
        return 3 + min(14, edge[(x, z)] * 1.4) + 2 * fbm2(x, z, 5, 2, 9850)

    def grass(x, z):
        top = t.top[(x, z)]
        if t.lava(x, z):
            return pick(VOLCANIC_SOIL, x, top, z)
        if (x, z) not in t.stand:
            # pentes raides : roche nue (les escarpements gris de la carte)
            drop = max(abs(top - t.top.get((x + dx, z + dz), top)) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if drop >= 2 or fbm2(x, z, 11, 2, 9853) > 0.35:
                return pick(ROCK, x, top, z)
        return fn.soil(x, z, 9851, GRASS)

    cells = fn.island(p, t.top, depth_of, 9852, grass=grass, hang=0.1, theme=SUNQUA)
    volcanic = {}
    for (x, y, z), (name, rot) in list(p.blocks.items()):
        if not t.lava(x, z):
            continue
        if name in DIRT:
            volcanic[(x, y, z)] = pick(VOLCANIC_DIRT, x, y, z)
        elif name in ROCK:
            volcanic[(x, y, z)] = pick(VOLCANIC_DEEP, x, y, z)
        elif name.startswith("Plant_Vine"):
            volcanic[(x, y, z)] = AIR
    for c, name in volcanic.items():
        p.set(*c, name)
    return [c for c in cells if not t.lava(c[0], c[2])]


def summit(p, t):
    """L'arène ronde du sommet : dalles de marbre en anneaux, rosace au centre, balustrade côté vide (ouverte vers
    la montée), colonnes, lanternes ; rend les cases de la balustrade."""
    cx, cz = SUMMIT_C
    s = SUMMIT_STAND
    for (x, z), name in t.kind.items():
        if name != "summit":
            continue
        d = math.hypot(x - cx, z - cz)
        ring = int(d) % 4 == 0
        a = math.degrees(math.atan2(z - cz, x - cx)) % 45
        if d < 3.5:
            block = TILE_INLAY
        elif ring:
            block = TILE_RING
        elif d < 6.5 and a < 4:
            block = TILE_INLAY
        else:
            block = pick(TILE, x, s - 1, z)
        p.set(x, s - 1, z, block)
    rail = []
    rise = curve(PATHS["rise"])[-6:]
    for k in range(360 * 2):
        a = math.radians(k / 2)
        x, z = round(cx + math.cos(a) * (SUMMIT_R - 0.2)), round(cz + math.sin(a) * (SUMMIT_R - 0.2))
        if (x, z) not in t.stand or any(math.hypot(x - rx, z - rz) < 5 for rx, rz, *_ in rise):
            continue
        if (x, s, z) not in p.blocks:
            p.set(x, s, z, RAIL)
            rail.append((x, s, z))
    for k in range(8):
        a = math.radians(k * 45 + 22.5)
        x, z = round(cx + math.cos(a) * (SUMMIT_R - 2)), round(cz + math.sin(a) * (SUMMIT_R - 2))
        if any(math.hypot(x - rx, z - rz) < 6 for rx, rz, *_ in rise):
            continue
        h = 4 + int(hash01(x, k, z, 9860) * 3)
        p.set(x, s, z, PILLAR_BASE)
        for y in range(s + 1, s + h):
            p.set(x, y, z, PILLAR_MID)
        if h < 6:
            p.set(x, s + h, z, LANTERN)
    return rail


def voice_disc(p):
    """Plateau de la Voix : disque de pierre claire au milieu de l'herbe (anneaux, rosace)."""
    cx, cz = VOICE_C
    s = VOICE_STAND
    for x in range(cx - 10, cx + 11):
        for z in range(cz - 10, cz + 11):
            d = math.hypot(x - cx, z - cz)
            if d > 9.5:
                continue
            block = TILE_INLAY if d < 1.5 else TILE_RING if abs(d - 6) < 0.6 or abs(d - 9) < 0.5 else pick(DISC, x, s, z)
            p.set(x, s - 1, z, block)


def plinth(p):
    """Le socle au bout de l'escalier : dallage et colonnes brisées."""
    cx, cz = PLINTH_C
    s = AREA["plinth"][4]
    for x in range(cx - 7, cx + 8):
        for z in range(cz - 7, cz + 8):
            if math.hypot(x - cx, z - cz) <= 6.5:
                p.set(x, s - 1, z, pick(TILE, x, s, z))
    for k in range(6):
        a = math.radians(k * 60 + 15)
        x, z = round(cx + math.cos(a) * 6), round(cz + math.sin(a) * 6)
        h = 1 + int(hash01(x, k, z, 9870) * 4)
        p.set(x, s, z, PILLAR_BASE)
        for y in range(s + 1, s + h):
            p.set(x, y, z, PILLAR_MID)


def stair_cells(t):
    """Escalier refait (Java) : passerelle de trois blocs de large d'un îlot à l'autre, une marche par bloc de
    montée ; cases (x, y, z) du sol à poser, qui ne touchent pas le relief déjà là."""
    chain = [(0, 128 - 12, 1)] + [(x, z, s) for x, z, s, _ in STEPS] + [(PLINTH_C[0], PLINTH_C[1], AREA["plinth"][4])]
    cells = []
    seen = set()
    for (ax, az, sa), (bx, bz, sb) in zip(chain, chain[1:]):
        n = max(2, int(math.hypot(bx - ax, bz - az) * 2))
        dx, dz = (bx - ax), (bz - az)
        L = math.hypot(dx, dz)
        px, pz = -dz / L, dx / L
        for k in range(n + 1):
            u = k / n
            x, z = ax + dx * u, az + dz * u
            s = round(sa + (sb - sa) * u)
            for w in (-1, 0, 1):
                c = (round(x + px * w), round(z + pz * w))
                if c in t.stand or c in seen:
                    continue
                seen.add(c)
                cells.append((c[0], s - 1, c[1]))
    return cells


def sorrow(p, t):
    """Terrasse de la Tristesse : bassin en anneau autour d'un îlot moussu, mousse sur l'îlot."""
    cx, cz = SORROW_C
    s = SORROW_STAND
    for (x, z), name in t.kind.items():
        if name != "sorrow":
            continue
        d = math.hypot(x - cx, z - cz)
        if POND_IN < d <= POND_OUT + 0.6 * fbm2(x, z, 4, 2, 9880):
            p.set(x, s - 3, z, pick(["Soil_Clay", "Soil_Gravel_Sand", "Rock_Stone_Mossy"], x, s - 3, z))
            p.set(x, s - 2, z, "Soil_Clay")
            p.fluid(x, s - 1, z, WATER)
        elif d <= POND_IN:
            p.set(x, s - 1, z, "Rock_Stone_Mossy" if hash01(x, z, 1, 9881) < 0.4 else "Soil_Grass_Deep")
            if hash01(x, z, 2, 9882) < 0.35 and d > 1.5:
                p.set(x, s, z, MOSS[int(hash01(z, x, 3, 9883) * len(MOSS))])


def nooks(p):
    """Niches des élémentaires d'eau : petite mare au fond, mousse."""
    for cx, cz, r in NOOKS:
        x, z = round(cx), round(cz)
        a = math.atan2(z - C[1], x - C[0])
        bx, bz = round(x - math.cos(a) * 1.5), round(z - math.sin(a) * 1.5)
        p.set(bx, WATER_S - 2, bz, "Soil_Clay")
        p.fluid(bx, WATER_S - 1, bz, WATER)


def waterfall(p, t, x, z, foot):
    """Cascade : colonne d'eau contre la falaise, du haut de la falaise au bassin `foot` (y du dessus de l'eau)."""
    top = t.top.get((x, z))
    if top is None:
        return
    for y in range(foot, top + 1):
        p.fluid(x, y, z, WATER)
    p.set(x, foot - 1, z, "Soil_Clay")


def waterfalls(p, t):
    """Les deux cascades de la corniche (bassin au pied de la falaise, côté montagne), celle de la Tristesse."""
    out = []
    for theta in SURGES:
        x, z = (round(v) for v in polar(theta, SURGE_FROM - 1.5))
        if (x, z) in t.top and (x, z) not in t.stand:
            for dx, dz in ((0, 0), (1, 0), (0, 1)):
                c = (x + dx, z + dz)
                if c in t.top and c not in t.stand:
                    waterfall(p, t, *c, WATER_S - 1)
                    out.append(c)
    cx, cz = SORROW_C
    a = math.atan2(C[1] - cz, C[0] - cx)
    x, z = round(cx + math.cos(a) * (SORROW_R + 1.5)), round(cz + math.sin(a) * (SORROW_R + 1.5))
    if (x, z) in t.top and (x, z) not in t.stand:
        for dx in (-1, 0, 1):
            if (x + dx, z) in t.top and (x + dx, z) not in t.stand:
                waterfall(p, t, x + dx, z, SORROW_STAND - 1)
                # bassin au pied
                for k in range(1, 3):
                    bx, bz = round(x + dx - math.cos(a) * k), round(z - math.sin(a) * k)
                    if t.kind.get((bx, bz)) == "sorrow":
                        p.set(bx, SORROW_STAND - 2, bz, "Soil_Clay")
                        p.fluid(bx, SORROW_STAND - 1, bz, WATER)
    return out


def lava_pools(p, t):
    """Mares de lave dans les replats du flanc volcanique, au-dessus du sentier (jamais sur le chemin)."""
    for (x, z), top in sorted(t.top.items()):
        if (x, z) in t.stand or not t.lava(x, z) or fbm2(x, z, 7, 2, 9890) < 0.45:
            continue
        nbs = [t.top.get((x + dx, z + dz)) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if any(v is None or v < top or (x + dx, z + dz) in t.stand
               for v, (dx, dz) in zip(nbs, ((1, 0), (-1, 0), (0, 1), (0, -1)))):
            continue
        p.fluid(x, top, z, LAVA)


def crater(p, t):
    """Cratère de la Fureur : sol de lave refroidie, fissures incandescentes, bord de roche volcanique."""
    cx, cz = CRATER_C
    s = CRATER_STAND
    for (x, z), name in t.kind.items():
        if name != "crater":
            continue
        h = hash01(x, z, 4, 9895)
        block = "Rock_Volcanic_Cracked_Lava" if h < 0.05 else pick(["Rock_Magma_Cooled", "Rock_Volcanic",
                                                                      "Rock_Basalt"], x, s, z)
        p.set(x, s - 1, z, block)


def lava_walls(p, t):
    """Trois murs de roche en travers du sentier de lave ; rend la liste des cases de chaque mur."""
    walls = []
    for f in LAVA_WALLS:
        at = along("lava", f)
        cells = []
        for x, z in across("lava", at, at[3] + 1):
            s = t.stand.get((x, z))
            if s is None:
                continue
            for y in range(s, s + LAVA_WALL_HEIGHT):
                p.set(x, y, z, pick(["Rock_Volcanic", "Rock_Basalt", "Rock_Volcanic_Cobble"], x, y, z))
                cells.append((x, y, z))
        walls.append(cells)
    return walls


def gate(p, t, name, at, half, height=5):
    """Barrière de brume en travers du chemin `name` au point `at` ; rend ses cases (le Java les retire)."""
    cells = []
    for x, z in across(name, at, half + 1):
        s = t.stand.get((x, z))
        if s is None:
            continue
        for y in range(s, s + height):
            p.set(x, y, z, BARRIER)
            cells.append((x, y, z))
    return cells


def bamboo(p, x, y, z, height, seed):
    """Touffe de bambous : trois à cinq tiges, feuilles en haut."""
    for k in range(3 + int(hash01(x, y, z, seed) * 3)):
        a = hash01(x, k, z, seed + 1) * math.tau
        bx, bz = x + round(math.cos(a) * 1.2), z + round(math.sin(a) * 1.2)
        if not fn.free(p, bx, y, bz) or fn.free(p, bx, y - 1, bz):
            continue
        h = height - int(hash01(bx, k, bz, seed + 2) * 3)
        for dy in range(h):
            p.set(bx, y + dy, bz, BAMBOO)
        for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            if fn.free(p, bx + dx, y + h, bz + dz):
                p.set(bx + dx, y + h, bz + dz, BAMBOO_LEAVES)


def keep_circles():
    """Cercles (x, z, r) où ni arbre ni rocher ne pousse : combats, chemins, colonnes de vent."""
    keep = [(VOICE_C[0], VOICE_C[1], VOICE_R + 1), (SORROW_C[0], SORROW_C[1], SORROW_R + 1),
            (CRATER_C[0], CRATER_C[1], CRATER_R + 1), (SUMMIT_C[0], SUMMIT_C[1], SUMMIT_R + 1),
            (PLINTH_C[0], PLINTH_C[1], 9), (SPIRIT_AT[0], SPIRIT_AT[2], 6), (SPAWN[0], SPAWN[2], 4)]
    for col in (COLUMN_1, COLUMN_2):
        keep.append((col[0][0], col[0][2], 4))
    for x, z, s, r in STEPS:
        keep.append((x, z, r + 0.5))
    return keep


def dress(p, t, cells):
    """Cerisiers roses et bambous sur les pentes, herbes et pétales partout ; les chemins restent dégagés."""
    keep = keep_circles()
    free_cells = []
    for x, y, z in cells:
        if any(math.hypot(x - kx, z - kz) <= kr for kx, kz, kr in keep):
            continue
        path = t.center.get((x, z))
        if path and path[1] < 2.6:
            continue
        free_cells.append((x, y, z))
    near_path = {(x + dx, z + dz) for (x, z) in t.center for dx in range(-2, 3) for dz in range(-2, 3)}
    placed = []
    for x, y, z in sorted(free_cells):
        if not fn.free(p, x, y + 1, z) or (x, z) in near_path:
            continue
        h = hash01(x, y, z, 9901)
        trees = 0.024 if (x, z) in t.stand else 0.007
        if h < trees and all(math.hypot(x - a, z - b) >= 8 for a, b in placed):
            placed.append((x, z))
            if hash01(z, y, x, 9902) < 0.75:
                fn.broadleaf(p, x, y + 1, z, 5 + int(hash01(x, z, y, 9903) * 4), "blossom", 9904 + x * 3 + z, droop=0.1)
            else:
                bamboo(p, x, y + 1, z, 6 + int(hash01(x, z, y, 9905) * 4), 9906 + x + z)
        elif h < 0.06:
            p.set(x, y + 1, z, SUNQUA["bushes"][int(hash01(z, x, y, 9907) * len(SUNQUA["bushes"]))])
        elif h < 0.064:
            fn.boulder(p, x, y + 1, z, 0.9 + hash01(x, z, y, 9908) * 1.0, 9909 + x, rocks=SUNQUA["rocks"])
    fn.flora(p, free_cells, 9910, 0.5, 0.18, theme=SUNQUA)


def dress_lava(p, t):
    """Flanc volcanique : arbres morts, herbes sèches, rochers."""
    cells = []
    for (x, z), top in t.top.items():
        if not t.lava(x, z) or not fn.free(p, x, top + 1, z) or (x, top, z) not in p.blocks:
            continue
        if any(math.hypot(x - kx, z - kz) <= kr for kx, kz, kr in keep_circles()):
            continue
        if any((x + dx, z + dz) in t.center for dx in range(-2, 3) for dz in range(-2, 3)):
            continue
        if p.blocks[(x, top, z)][0] in ("Lava_Source", AIR):
            continue
        cells.append((x, top, z))
    fn.dress(p, cells, VOLCANIC, 9920, trees=0.015, spacing=7, bushes=0.03, boulders=0.006, density=0.3, flowers=0.0)


def lanterns(p, t):
    """Lanternes de pierre le long des chemins (côté montagne) et autour du départ."""
    for name in ("water", "lava", "rise"):
        s = curve(PATHS[name])
        for k in range(8, len(s) - 4, 26):
            x, z, ss, half = s[k]
            a = math.atan2(C[1] - z, C[0] - x)
            lx, lz = round(x + math.cos(a) * (half - 0.6)), round(z + math.sin(a) * (half - 0.6))
            st = t.stand.get((lx, lz))
            if st is not None and fn.free(p, lx, st, lz):
                p.set(lx, st, lz, LANTERN)
    for dx in (-6, 6):
        p.set(SPAWN[0] + dx, 1, SPAWN[2] - 3, LANTERN)


def islets(p):
    """Îlots de décor dans le vide, autour du massif (cerisiers)."""
    area = (C[0] - 150, C[0] + 150, C[1] - 130, 150)
    return fn.scatter_islets(p, area, 22, (-10, 60), (3, 8), SUNQUA, 9930, margin=16)


# --- vérifications ------------------------------------------------------------------------------------------

def walk_components(t):
    """Composantes de marche : voisins à 4, on monte d'un bloc, on descend de trois."""
    comp, label = {}, 0
    for start in t.stand:
        if start in comp:
            continue
        label += 1
        comp[start] = label
        queue = deque([start])
        while queue:
            x, z = queue.popleft()
            s = t.stand[(x, z)]
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, z + dz)
                if n in comp or n not in t.stand:
                    continue
                if -3 <= t.stand[n] - s <= 1 and -3 <= s - t.stand[n] <= 1:
                    comp[n] = label
                    queue.append(n)
    return comp


def check(t, p, extra_solid=()):
    """Le parcours se fait : chaque lieu d'un seul tenant, les chemins le relient à ses lieux, l'escalier se saute avec
    deux charges, rien n'encombre le passage."""
    comp = walk_components(t)
    at = lambda x, z: comp[(round(x), round(z))]
    groups = [
        ("corniche", [polar(171, 62), *[(c[0], c[1]) for c in NOOKS], polar(229, 62)]),
        ("tristesse et lave", [SORROW_C, along("lava", 0.0)[:2], along("lava", 1.0)[:2], CRATER_C]),
        ("montée et sommet", [CRATER_C, along("rise", 0.5)[:2], SUMMIT_C]),
    ]
    for name, pts in groups:
        labels = {at(*pt) for pt in pts}
        assert len(labels) == 1, f"{name} : pas d'un seul tenant ({labels})"
    chain = [(0, 128, 1, 12)] + [(x, z, s, r) for x, z, s, r in STEPS] + [(PLINTH_C[0], PLINTH_C[1], 24, 8)]
    for a, b in zip(chain, chain[1:]):
        gap = math.hypot(a[0] - b[0], a[1] - b[1]) - a[3] - b[3]
        assert STEP_GAP[0] - 0.5 <= gap <= STEP_GAP[1] + 0.5, f"marche {a} -> {b} : écart {gap:.1f}"
        assert 0 <= b[2] - a[2] <= STEP_RISE, f"marche {a} -> {b} : montée {b[2] - a[2]}"
    # rien de plein sur les chemins (hors barrières et murs posés exprès)
    for (x, z), s in t.stand.items():
        if (x, z) not in t.center and t.kind[(x, z)] not in ("voice", "sorrow", "crater", "summit"):
            continue
        for y in (s, s + 1):
            name = p.blocks.get((x, y, z), (AIR,))[0]
            if name != AIR and (x, y, z) not in extra_solid and not name.startswith(("Plant_", "Furniture",
                                                                                    "Rock_Marble_Brick_Wall",
                                                                                    "Rock_Marble_Brick_Pillar")):
                if not t.kind.get((x, z), "").startswith(("nook", "summit", "plinth", "sorrow")):
                    raise AssertionError(f"bloc {name} sur le chemin en {(x, y, z)}")


def build_all():
    p = go.Prefab()
    t = Terrain()
    summit(p, t)
    voice_disc(p)
    plinth(p)
    sorrow(p, t)
    nooks(p)
    crater(p, t)
    cells = lay_terrain(p, t)
    falls = waterfalls(p, t)
    lava_pools(p, t)
    gates = {
        "water": gate(p, t, "water", along("water", 0.97), 3.5),
        "sorrow": gate(p, t, "lava", along("lava", 0.05), 3),
        "crater": gate(p, t, "rise", along("rise", 0.12), 3),
    }
    walls = lava_walls(p, t)
    lanterns(p, t)
    dress(p, t, cells)
    dress_lava(p, t)
    islets(p)
    extra = set(c for g in gates.values() for c in g) | set(c for w in walls for c in w)
    check(t, p, extra)
    t.gates = gates
    t.walls = walls
    t.falls = falls
    t.stairs = stair_cells(t)
    return p, t
