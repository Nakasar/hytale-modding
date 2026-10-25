"""Terrain et décor de la Tempête de neige, d'après la carte GW2 de Snowblind que Kevin a envoyée (25 octobre 2026).

Une vallée de montagne fermée, toujours de nuit : on part des ruines en bois au nord, on descend la colline jusqu'au
grand feu (rencontre 1), on passe le col du mur de glace, on monte les escaliers de glace jusqu'au camp Svanir et ses
tentes (la Source élémentaire), puis la forêt fait le grand tour par l'est (plaine aux rochers, plateau, vallée) et
revient par le sud jusqu'à la grotte de glace du Chaman légendaire, sous le dôme de neige du sud-ouest.

Repère : x vers l'est, z vers le sud, un bloc = 5 px de la carte (origine au milieu). « debout à s » : le sol est en
s - 1. Le sol des lieux praticables est un champ de hauteurs au demi-bloc (neige pleine + demi-dalles de neige :
pentes douces sans saut) ; tout le reste est montagne : falaises d'au moins cinq blocs au bord, qui montent ensuite,
couvertes de sapins enneigés. Rien n'est posé au hasard : un prefab régénéré est identique.
"""
import math
from collections import deque

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

pick = fc.pick
AIR = go.AIR
THEME = fn.THEMES["snow"]

SNOW = "Soil_Snow"
SNOW_HALF = "Soil_Snow_Half"
UNDER = ["Soil_Snow", "Soil_Dirt", "Rock_Ice_Permafrost"]
ROCK = ["Rock_Stone", "Rock_Slate", "Rock_Stone", "Rock_Ice_Permafrost", "Rock_Slate"]
CAVE_ROCK = ["Rock_Ice", "Rock_Ice_Permafrost", "Rock_Ice", "Rock_Crystal_White_Block", "Rock_Ice_Permafrost"]
ICE = "Rock_Ice"
PLANKS = "Wood_Softwood_Planks"
DARK_PLANKS = "Wood_Darkwood_Planks"
LOG = "Wood_Fir_Trunk"
BANNER = "Cloth_Block_Wool_Red"
TENT = ["Cloth_Block_Wool_White", "Cloth_Block_Wool_Gray_Light", "Cloth_Block_Wool_Gray_Light"]
TENT_BAND = "Cloth_Block_Wool_Gray"
TORCH_POST = "Furniture_Crude_Torch"
STALACTITE = "Rock_Ice_Stalactite_Large"
HANGING = 8                                     # bloc retourné (stalactites des prefabs de grottes vanilla)
DMAX = 34                                       # montagne posée jusqu'à cette distance des lieux praticables

# --- la carte -------------------------------------------------------------------------------------------
# Taches (lieux ouverts) : (nom, cx, cz, rx, rz, debout, rayon plat). Le sol est plat (debout entier) dans le
# rayon plat autour du centre, et ondule doucement au-delà.
BLOBS = [
    ("start", -50, -112, 24, 9, 8, 7),
    ("bowl", -46, -63, 27, 19, 0, 22),
    ("bowl_west", -76, -70, 11, 10, 0.5, 0),
    ("bowl_east", -16, -72, 11, 9, 0.5, 0),
    ("camp", -72, 40, 31, 30, 9, 26),
    ("glade", 4, 30, 13, 11, 6, 5),
    ("plain", 36, 2, 30, 19, 5, 0),
    ("plateau", 118, 0, 14, 16, 12, 6),
    ("den", 88, 62, 14, 12, 7, 5),
    ("hollow", 40, 106, 26, 11, 3, 5),
    ("outpost", -16, 104, 11, 9, 2, 7),
    ("cave", -84, 104, 20, 20, -2, 20),
]
CAVE_BLOBS = {"cave"}
# Chemins : points (x, z, debout, demi-largeur) lissés en courbe.
PATHS = {
    "hill": [(-50, -112, 8, 11), (-49, -100, 7, 13), (-48, -88, 3, 13), (-46, -72, 0, 12)],
    "pass": [(-46, -63, 0, 5), (-50, -46, 0, 4.5), (-54, -36, 0, 4), (-54, -28, 0, 4), (-53, -22, 0, 4.5)],
    "approach": [(-52, -4, 9, 4.5), (-55, 4, 9, 5), (-60, 12, 9, 5.5), (-66, 20, 9, 6)],
    "forest": [(-72, 40, 9, 5), (-50, 44, 9, 4.5), (-36, 46, 9, 3.5), (-24, 48, 8, 4.5), (-10, 42, 7, 5),
               (4, 30, 6, 5), (16, 14, 5, 5), (30, 2, 5, 5), (50, -8, 5, 5), (70, -16, 7, 4.5), (90, -12, 10, 4.5),
               (106, -6, 12, 5), (118, 0, 12, 5), (119, 20, 11, 4.5), (108, 42, 9, 5), (90, 62, 7, 5),
               (77, 84, 5, 4.5), (60, 100, 4, 5), (38, 108, 3, 5), (14, 112, 3, 4.5), (-6, 108, 2, 5),
               (-16, 104, 2, 5), (-30, 102, 2, 3.5)],
    "tunnel": [(-30, 102, 2, 3.5), (-42, 101, 1, 3.5), (-54, 103, 0, 3.5), (-64, 104, -2, 4)],
}
CAVE_PATHS = {"tunnel"}
CAVE_FROM_X = -33                               # le tunnel est couvert à l'ouest de cette ligne

# Escaliers de glace : du col (debout 0) au camp (debout 9), un demi-bloc par case.
STAIRS = (-53, -22, -52, -4, 0, 9, 4.5)         # x0, z0, x1, z1, debout bas, debout haut, demi-largeur

# --- lieux de jeu (debout à y) -----------------------------------------------------------------------------
SPAWN = (-50, 8, -114)
BONFIRE_AT = (-46, 0, -63)
CAMP = (-46, -63)
CAMP_RADIUS = 27
BONFIRE_HEAT = 7.0
FIREWOOD_SPOTS = [(round(CAMP[0] + math.cos(math.radians(a)) * r), round(CAMP[1] + math.sin(math.radians(a)) * r))
                  for a, r in ((-160, 18), (-120, 16), (-60, 16), (-20, 19), (20, 19), (160, 19), (200, 17), (-90, 17))]
ELEMENTAL_SPAWNS = [(round(CAMP[0] + math.cos(math.radians(a)) * 23), round(CAMP[1] + math.sin(math.radians(a)) * 17))
                    for a in (-170, -135, -100, -45, -10, 25, 155)]
WAVE_SPAWNS = [(-70, -70), (-20, -74), (-58, -80), (-23, -62)]
WALL_Z = (-31, -29)                             # rangées z du mur de glace, dans le col
WALL_HEIGHT = 7
WALL_CHECKPOINT = (-53, 0, -25)

SOURCE_C = (-72, 40)
SOURCE_RADIUS = 20
SOURCE_AT = (-72, 9, 40)
BRAZIERS = [(round(SOURCE_C[0] + math.cos(math.radians(-90 + k * 72)) * 13),
             round(SOURCE_C[1] + math.sin(math.radians(-90 + k * 72)) * 13)) for k in range(5)]
BRAZIER_HEAT = 5.0
TEEPEES = [(a, 25) for a in (-160, -125, -30, 50, 90, 130, 170)]   # (angle, rayon) autour de la Source
PILE_TEEPEES = (-125, 90, 170)                  # tentes devant lesquelles on trouve un tas de fagots
TORCH_RACK_AT = (-61, 9, 13)
GATE_SOURCE_AT = (-36, 46)

PACKS = [  # (centre, rôles) : groupes de la forêt autour de leur feu de camp
    ((4, 30), ["cultist", "cultist", "wolf", "wolf"]),
    ((42, -6), ["caster", "cultist", "wolf", "wolf", "wolf"]),
    ((118, 0), ["cultist", "cultist", "caster", "wolf", "wolf"]),
    ((90, 62), ["wolf", "wolf", "wolf", "wolf"]),
    ((38, 108), ["cultist", "cultist", "caster", "wolf", "wolf"]),
]
OUTPOST = (-16, 104)
FOREST_CHECKPOINT = (-30, 9, 47)
PLATEAU_CHECKPOINT = (86, -13)                  # sur le sentier, avant le plateau : hors de portée du groupe 2
VILLAGE_CHECKPOINT = (-68, 104)                 # dans la grotte, côté arène de la brume (debout calculé)

VILLAGE_C = (-84, 104)
VILLAGE_RADIUS = 20
GATE_VILLAGE_AT = (-60, 104)                   # au bout du tunnel, juste avant la grotte
GATES = [(-54, -30), GATE_SOURCE_AT, GATE_VILLAGE_AT]
VILLAGE_FIRES = [(-74, 94), (-74, 114), (-96, 104)]
BALCONY = (-100, 5, 104)                        # corniche de glace du Chaman, 7 blocs au-dessus de l'arène
EFFIGY_AT = (-82, -2, 104)
SHAMAN_AT = (-90, -2, 104)
REWARD_AT = (-86, -2, 98)
END_EXIT_AT = (-82, -2, 98)


# --- courbes ---------------------------------------------------------------------------------------------

def curve(points, step=0.5):
    """Catmull-Rom par les points (x, z, debout, demi-largeur) : échantillons (x, z, debout, demi-largeur) tous les
    `step` blocs ; debout et largeur suivent la courbe linéairement (en flottant)."""
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


def nearest_sample(samples, x, z):
    best = min(range(len(samples)), key=lambda i: (samples[i][0] - x) ** 2 + (samples[i][1] - z) ** 2)
    return best, math.hypot(samples[best][0] - x, samples[best][1] - z)


def path_x(name, z):
    """x du centre du chemin `name` à la hauteur z (premier passage)."""
    s = curve(PATHS[name])
    return round(min(s, key=lambda p: abs(p[1] - z))[0])


# --- le champ de hauteurs ----------------------------------------------------------------------------------

class Terrain:
    """Lieux praticables (`stand` : {(x, z): debout au demi-bloc}), lieux couverts (`ceiling`), montagne (`top` :
    {(x, z): hauteur du sommet}), et pour chaque case : le chemin le plus proche (`center` : distance au milieu)."""

    def __init__(self):
        self.raw = {}           # (x, z) -> debout brut
        self.fixed = set()      # cases à debout imposé (lieux de jeu plats, escaliers, mur)
        self.center = {}        # (x, z) -> (nom du chemin, distance au milieu du chemin)
        self.cave = set()
        self.blob_of = {}
        self._paths()
        self._blobs()
        self._stairs()
        self._flatten_spots()
        self.stand = self._smooth()
        self._mountains()
        self._ceilings()

    # Chemins puis taches (les taches l'emportent : leur centre porte le même debout que le point du chemin).
    def _paths(self):
        for name, pts in PATHS.items():
            samples = curve(pts)
            for i, (sx, sz, ss, half) in enumerate(samples):
                reach = half + 1.2
                for x in range(math.floor(sx - reach), math.ceil(sx + reach) + 1):
                    for z in range(math.floor(sz - reach), math.ceil(sz + reach) + 1):
                        d = math.hypot(x - sx, z - sz)
                        if d > half + 0.6 * fn.fbm2(x, z, 5, 2, 301):
                            continue
                        old = self.center.get((x, z))
                        if old is None or d < old[1]:
                            self.center[(x, z)] = (name, d)
                            self.raw[(x, z)] = ss
                        if name in CAVE_PATHS and x <= CAVE_FROM_X:
                            self.cave.add((x, z))

    def _blobs(self):
        for name, cx, cz, rx, rz, stand, flat in BLOBS:
            for x in range(cx - rx - 6, cx + rx + 7):
                for z in range(cz - rz - 6, cz + rz + 7):
                    d = math.hypot((x - cx) / rx, (z - cz) / rz)
                    edge = 1.0 if name in CAVE_BLOBS else 1.0 + 0.16 * fn.fbm2(x, z, 8, 2, 302 + cx)
                    if d > edge:
                        continue
                    self.raw[(x, z)] = stand
                    self.blob_of[(x, z)] = name
                    if math.hypot(x - cx, z - cz) <= flat:
                        self.fixed.add((x, z))
                    else:
                        self.fixed.discard((x, z))
                    if name in CAVE_BLOBS:
                        self.cave.add((x, z))

    def _stairs(self):
        x0, z0, x1, z1, s0, s1, half = STAIRS
        length = z1 - z0
        for z in range(z0, z1 + 1):
            t = (z - z0) / length
            cx = x0 + (x1 - x0) * t
            level = s0 + math.floor(t * (s1 - s0) * 2 + 1e-6) / 2
            for x in range(math.floor(cx - half - 1), math.ceil(cx + half + 1) + 1):
                if abs(x - cx) <= half:
                    self.raw[(x, z)] = level
                    self.fixed.add((x, z))
                    self.center[(x, z)] = ("stairs", abs(x - cx))

    def _flatten_spots(self):
        """Debout entier imposé autour du mur (col), des portes, des feux et des tas."""
        for x, z in list(self.raw):
            if WALL_Z[0] - 3 <= z <= WALL_Z[1] + 3 and self.center.get((x, z), ("",))[0] == "pass":
                self.raw[(x, z)] = 0
                self.fixed.add((x, z))
        spots = [(GATE_SOURCE_AT, 9, 4), (GATE_VILLAGE_AT, None, 4), (OUTPOST, 2, 6)]
        spots += [(c, None, 4) for c, _ in PACKS]
        spots += [(c, round(self.raw[c]), 4) for c in WAVE_SPAWNS]     # vagues du grand feu : formation de 4 x 3 à plat
        for (cx, cz), level, r in spots:
            for x in range(cx - r, cx + r + 1):
                for z in range(cz - r, cz + r + 1):
                    if (x, z) in self.raw and math.hypot(x - cx, z - cz) <= r:
                        if level is not None:
                            self.raw[(x, z)] = level
                        self.raw[(x, z)] = round(self.raw[(x, z)])
                        self.fixed.add((x, z))

    def _smooth(self):
        """Pentes douces : moyenne des voisins (cases libres), puis petites ondulations, arrondi au demi-bloc."""
        s = dict(self.raw)
        free = [c for c in s if c not in self.fixed]
        for _ in range(60):
            nxt = {}
            for x, z in free:
                vals = [s[(x + dx, z + dz)] for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) in s]
                nxt[(x, z)] = (s[(x, z)] + sum(vals)) / (1 + len(vals))
            s.update(nxt)
        near_fixed = self._distance(self.fixed, s, 5)
        out = {}
        for (x, z), v in s.items():
            if (x, z) in self.fixed:
                out[(x, z)] = math.floor(v * 2 + 1e-6) / 2
                continue
            w = min(1.0, near_fixed.get((x, z), 5) / 5)
            path = self.center.get((x, z))
            if path and path[1] < 2.5:
                w *= 0.3
            v += 0.9 * w * fn.fbm2(x, z, 10, 2, 303)
            out[(x, z)] = round(v * 2) / 2
        # Jamais plus d'un demi-bloc entre deux cases voisines hors escaliers et marches : on rabote.
        for _ in range(6):
            for (x, z) in sorted(out):
                if (x, z) in self.fixed:
                    continue
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, z + dz)
                    if n in out and out[(x, z)] - out[n] > 0.5:
                        out[(x, z)] = out[n] + 0.5
        return out

    @staticmethod
    def _distance(sources, cells, cap):
        dist, queue = {}, deque()
        for c in sources:
            dist[c] = 0
            queue.append(c)
        while queue:
            x, z = queue.popleft()
            if dist[(x, z)] >= cap:
                continue
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, z + dz)
                if n in cells and n not in dist:
                    dist[n] = dist[(x, z)] + 1
                    queue.append(n)
        return dist

    def _mountains(self):
        """Distance (8 voisins) de chaque case de montagne au lieu praticable le plus proche, et son sommet : une falaise
        de 5 à 11 blocs au bord, qui monte d'un bloc par case ensuite, crêtes rocheuses par le bruit."""
        dist, near, queue = {}, {}, deque()
        for c in self.stand:
            dist[c] = 0
            near[c] = c
            queue.append(c)
        while queue:
            x, z = queue.popleft()
            if dist[(x, z)] >= DMAX:
                continue
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                n = (x + dx, z + dz)
                if n not in dist:
                    dist[n] = dist[(x, z)] + 1
                    near[n] = near[(x, z)]
                    queue.append(n)
        self.dist, self.near = dist, near
        self.top = {}
        for (x, z), d in dist.items():
            if d == 0:
                continue
            base = self.stand[near[(x, z)]]
            lip = 5 + 6 * (fn.fbm2(x, z, 13, 2, 304) + 1) / 2
            crag = 4 * abs(fn.fbm2(x, z, 6, 2, 305))
            top = math.floor(base + lip + 1.05 * (d - 1) + crag + 3 * fn.fbm2(x, z, 23, 2, 306))
            # Jamais franchissable : 5 blocs au moins au bord, 10 autour des portes et du mur.
            low = 5 + d - 1
            if any(math.hypot(x - gx, z - gz) < 9 for gx, gz in GATES):
                low = WALL_HEIGHT + 3 + d - 1
            self.top[(x, z)] = max(top, math.floor(base) + low)

    def _ceilings(self):
        """Voûtes : le tunnel (6 à 8 blocs) et le dôme de la grotte (20 blocs au centre)."""
        self.ceiling = {}
        cx, cz = VILLAGE_C
        for x, z in self.cave:
            s = math.ceil(self.stand[(x, z)])
            if self.blob_of.get((x, z)) in CAVE_BLOBS:
                d = min(1.0, math.hypot(x - cx, z - cz) / VILLAGE_RADIUS)
                c = s + 9 + 13 * (1 - d * d) + 2 * fn.fbm2(x, z, 7, 2, 307)
            else:
                c = s + 6 + 2 * (fn.fbm2(x, z, 6, 2, 308) + 1) / 2
            self.ceiling[(x, z)] = math.floor(c)
        # Montagne autour de la grotte : toujours au-dessus de la voûte.
        for c, t in list(self.top.items()):
            n = self.near.get(c)
            if n in self.ceiling:
                self.top[c] = max(t, self.ceiling[n] + 3 + min(4, self.dist[c]))

    def ground_top(self, x, z):
        """Hauteur du dessus de la case (le bloc le plus haut est en top - 1, demi-dalle comprise)."""
        if (x, z) in self.stand:
            return math.ceil(self.stand[(x, z)])
        return self.top.get((x, z))


# --- pose du terrain ---------------------------------------------------------------------------------------

def lay_ground(p, t):
    """Sol des lieux praticables : neige (demi-dalle aux demi-hauteurs), dessous jusqu'au plus bas voisin."""
    for (x, z), s in t.stand.items():
        base = math.floor(s)
        stairs = t.center.get((x, z), ("",))[0] == "stairs"
        cave = (x, z) in t.cave
        top_block = ICE if stairs else pick(["Rock_Ice_Permafrost", ICE, SNOW], x, base - 1, z) if cave else SNOW
        p.set(x, base - 1, z, top_block)
        if s - base >= 0.5:
            p.set(x, base, z, SNOW_HALF if not cave else "Soil_Snow_Half")
        low = min([math.floor(t.stand.get((x + dx, z + dz), s)) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))] + [base])
        for y in range(low - 3, base - 1):
            p.set(x, y, z, pick(CAVE_ROCK if cave else UNDER, x, y, z))


def lay_mountains(p, t):
    """Montagne : du sommet jusqu'au plus bas voisin (la face qui se voit), roche en bandes, neige sur les replats."""
    for (x, z), top in t.top.items():
        nbs = [t.ground_top(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        nbs = [v for v in nbs if v is not None]
        low = min(nbs + [top]) - 1
        near = t.near[(x, z)]
        if t.dist[(x, z)] <= 2:
            low = min(low, math.floor(t.stand[near]) - 3)
        icy = near in t.cave and t.dist[(x, z)] <= 4
        palette = CAVE_ROCK if icy else ROCK
        flat = max(nbs + [top]) - top <= 1
        for y in range(low, top):
            if y == top - 1 and flat and not icy:
                p.set(x, y, z, SNOW)
            else:
                band = int((y + 3 * fn.vnoise2(x, z, 11, 309)) // 3)
                p.set(x, y, z, palette[band % len(palette)] if fn.hash01(x, y, z, 310) < 0.8 else pick(palette, x, y, z))
        if not flat and not icy and fn.hash01(x, top, z, 311) < 0.55:
            p.set(x, top, z, SNOW_HALF)


def lay_ceilings(p, t):
    """Voûte de glace de la grotte et du tunnel (au moins 3 blocs, jusqu'au plus haut voisin), stalactites et glaçons ;
    à l'entrée du tunnel, la paroi monte jusqu'à la montagne."""
    for (x, z), c in t.ceiling.items():
        nbs = [t.ceiling.get((x + dx, z + dz), t.top.get((x + dx, z + dz), c)) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        hi = max([c + 3] + [v + 1 for v in nbs if v is not None])
        mouth = any((x + dx, z + dz) in t.stand and (x + dx, z + dz) not in t.cave
                    for dx in range(-3, 4) for dz in range(-3, 4))
        if mouth:
            hi = max(hi, c + 10)
        for y in range(c, hi):
            p.set(x, y, z, pick(CAVE_ROCK, x, y, z))
        p.set(x, hi, z, SNOW)
        h = fn.hash01(x, c, z, 312)
        room = c - math.ceil(t.stand[(x, z)])
        if room >= 9 and h < 0.05:
            length = 1 + int(fn.hash01(z, c, x, 313) * min(5, room - 7))
            for k in range(1, length + 1):
                p.set(x, c - k, z, ICE)
            p.set(x, c - length - 1, z, STALACTITE, HANGING)
        elif room >= 5 and h < 0.12:
            p.set(x, c - 1, z, "Rock_Ice_Icicles")


# --- constructions ---------------------------------------------------------------------------------------

def teepee(p, cx, cz, stand, door, r=3.5, h=7):
    """Tente Svanir : cône de toile grise, perches croisées qui dépassent, porte vers `door` (degrés), fourrures."""
    n = math.ceil(r) + 1
    for y in range(h):
        ry = r * (1 - y / h) + 0.3
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                d = math.hypot(dx, dz)
                if not ry - 1.1 < d <= ry:
                    continue
                a = math.degrees(math.atan2(dz, dx))
                if y < 3 and abs((a - door + 180) % 360 - 180) < 26:
                    continue
                p.set(cx + dx, stand + y, cz + dz, TENT_BAND if y == 1 else TENT[int(fn.hash01(dx, y, dz, cx) * 3)])
    for dx, dz in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
        for k in range(3):
            p.set(cx + dx * (k // 2), stand + h - 1 + k, cz + dz * (k // 2), LOG)
    p.set(cx, stand - 1, cz, "Cloth_Block_Wool_Gray")


def banner(p, x, z, stand, face_x, face_z, height=6):
    """Bannière Svanir : mât de sapin, étendard rouge de deux de large sur trois de haut, tourné vers (face_x, face_z)."""
    for y in range(height):
        p.set(x, stand + y, z, LOG)
    sx, sz = (1, 0) if abs(face_z) >= abs(face_x) else (0, 1)
    for k in (1, 2):
        for y in range(height - 4, height - 1):
            p.set(x + sx * k, stand + y, z + sz * k, BANNER)


def palisade(p, t, points, stand_of):
    """Palissade de rondins taillés : poteaux de 3 ou 4 blocs le long des points, sur le sol."""
    for x, z in points:
        if (x, z) not in t.stand:
            continue
        s = stand_of(x, z)
        tall = 3 + (1 if fn.hash01(x, 0, z, 314) < 0.5 else 0)
        for y in range(tall):
            p.set(x, s + y, z, LOG)


def scaffold(p, x0, z0, w, d, h, stand, seed):
    """Échafaudage de bois en ruine : poteaux d'angle, plancher troué, une planche tombée."""
    for x, z in ((x0, z0), (x0 + w, z0), (x0, z0 + d), (x0 + w, z0 + d)):
        top = h if fn.hash01(x, 1, z, seed) < 0.75 else h - 2
        for y in range(top):
            p.set(x, stand + y, z, LOG)
    for x in range(x0, x0 + w + 1):
        for z in range(z0, z0 + d + 1):
            if fn.hash01(x, 2, z, seed) < 0.72:
                p.set(x, stand + h, z, PLANKS if (x + z) % 3 else DARK_PLANKS)
    for k in range(3):
        p.set(x0 + w + 2, stand, z0 + k, PLANKS)


def ice_spikes(p, cx, cz, stand, seed, count=7, reach=3):
    """Pics de glace plantés de biais (barrage Svanir) : colonnes de glace qui penchent, pointe en glaçon."""
    for k in range(count):
        a = fn.hash01(k, 1, 0, seed) * math.tau
        r = fn.hash01(k, 2, 0, seed) * reach
        x, z = round(cx + math.cos(a) * r), round(cz + math.sin(a) * r)
        lx, lz = (1 if fn.hash01(k, 3, 0, seed) < 0.5 else -1), 0
        height = 3 + int(fn.hash01(k, 4, 0, seed) * 4)
        for y in range(height):
            sx = x + lx * (y // 3)
            p.set(sx, stand + y, z + lz, ICE)
        p.set(x + lx * (height // 3), stand + height, z, "Rock_Ice_Icicles")


def campfire_ring(p, x, z, stand, block):
    """Feu de camp sur un rond de pierres, avec bûches pour s'asseoir."""
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if math.hypot(dx, dz) <= 2.3:
                p.set(x + dx, stand - 1, z + dz, "Rock_Stone_Cobble" if (dx, dz) != (0, 0) else "Rock_Stone")
    p.set(x, stand, z, block)
    for dx, dz in ((3, 1), (-3, -1), (1, -3), (-1, 3)):
        p.set(x + dx, stand, z + dz, PLANKS)


# --- végétation et rochers ---------------------------------------------------------------------------------

def snowy_rock(p, x, y, z, r, seed):
    """Gros rocher anguleux (bloc de granit des captures) : boule bruitée, aplatie, neige sur le dessus."""
    n = int(math.ceil(r)) + 2
    cells = []
    for dx in range(-n, n + 1):
        for dz in range(-n, n + 1):
            for dy in range(-1, n + 1):
                d = math.sqrt(dx * dx + (dy * 1.3) ** 2 + dz * dz)
                if d <= r + 0.9 * fn.vnoise3(x + dx, y + dy, z + dz, 2.6, seed) - 0.3 * abs(fn.vnoise3(x + dx, y, z + dz, 1.3, seed + 1)):
                    cells.append((x + dx, y - 1 + dy, z + dz))
    keep = set(cells)
    for cx, cy, cz in cells:
        p.set(cx, cy, cz, pick(["Rock_Stone", "Rock_Slate", "Rock_Stone"], cx, cy, cz))
    for cx, cy, cz in cells:
        if (cx, cy + 1, cz) not in keep and fn.hash01(cx, cy, cz, seed) < 0.8:
            p.set(cx, cy + 1, cz, SNOW_HALF)


class Keep:
    """Cases où le décor ne pose rien (chemins, lieux de jeu)."""

    def __init__(self):
        self.cells = set()

    def disc(self, cx, cz, r):
        for x in range(math.floor(cx - r), math.ceil(cx + r) + 1):
            for z in range(math.floor(cz - r), math.ceil(cz + r) + 1):
                if math.hypot(x - cx, z - cz) <= r:
                    self.cells.add((x, z))

    def __contains__(self, c):
        return c in self.cells


def free_column(p, x, y, z, height):
    return all(fn.free(p, x, y + k, z) for k in range(height))


def forest(p, t, keep, seed=320):
    """Sapins enneigés : serrés au pied des falaises et sur les premières pentes, plus rares dans les clairières,
    jamais sur un chemin ni un lieu de jeu ; aucun dans la grotte."""
    placed = {}

    def room(x, z, gap):
        gx, gz = x // 4, z // 4
        for ax in (gx - 1, gx, gx + 1):
            for az in (gz - 1, gz, gz + 1):
                for bx, bz in placed.get((ax, az), ()):
                    if math.hypot(x - bx, z - bz) < gap:
                        return False
        return True

    count = 0
    for (x, z) in sorted(set(t.stand) | set(t.top)):
        if (x, z) in keep or (x, z) in t.cave or t.near.get((x, z)) in t.cave:
            continue
        d = t.dist.get((x, z), 0)
        if d > 12:
            continue
        path = t.center.get((x, z))
        if d == 0 and path and path[1] < 3.2:
            continue
        blob = t.blob_of.get((x, z))
        if d == 0:
            density, gap = (0.02, 6.0) if blob in ("bowl", "camp", "plain", "plateau", "start", "outpost") else (0.05, 4.5)
        else:
            density, gap = (0.10, 4.0) if d <= 6 else (0.05, 5.5)
        if fn.hash01(x, 7, z, seed) >= density or not room(x, z, gap):
            continue
        y = t.ground_top(x, z)
        if y is None or not free_column(p, x, y, z, 3):
            continue
        height = 9 + int(fn.hash01(z, x, 3, seed + 1) * 10) + (3 if d >= 3 else 0)
        kind = "fir_snow" if fn.hash01(x, z, 5, seed + 2) < 0.94 else "fir"
        fn.conifer(p, x, y, z, height, kind, seed=x * 13 + z)
        placed.setdefault((x // 4, z // 4), []).append((x, z))
        count += 1
    return count


def ground_cover(p, t, keep, seed=330):
    """Herbes de neige et buissons enneigés sur les lieux praticables (pas sur le milieu des chemins), rochers enneigés
    au bord et dans la plaine, fausses-pistes de pierres."""
    cells = []
    for (x, z), s in t.stand.items():
        if (x, z) in keep or (x, z) in t.cave:
            continue
        path = t.center.get((x, z))
        if path and path[1] < 2.0 and t.blob_of.get((x, z)) is None:
            continue
        y = math.ceil(s)
        if not fn.free(p, x, y, z):
            continue
        h = fn.hash01(x, 9, z, seed)
        if h < 0.035:
            p.set(x, y, z, "Plant_Bush_Winter_Snow")
        elif h < 0.17 and fn.fbm2(x, z, 7, 2, seed + 1) > -0.1:
            pool = ["Plant_Grass_Snowy_Short", "Plant_Grass_Snowy", "Plant_Grass_Snowy_Tall"]
            p.set(x, y, z, pool[int(fn.hash01(z, x, 1, seed) * 3)])
        cells.append((x, z))
    # Rochers : au bord des lieux (pied de falaise) et quelques gros blocs dans la plaine et le bol.
    for (x, z) in sorted(cells):
        edge = any((x + dx, z + dz) not in t.stand for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)))
        h = fn.hash01(x, 11, z, seed + 2)
        big = t.blob_of.get((x, z)) in ("plain", "bowl_west", "bowl_east", "plateau", "den")
        if (edge and h < 0.03) or (big and h < 0.006):
            r = 1.2 + fn.hash01(z, 11, x, seed + 3) * (3.4 if big else 1.6)
            if all((x + dx, z + dz) not in keep for dx in range(-4, 5) for dz in range(-4, 5)):
                snowy_rock(p, x, math.ceil(t.stand[(x, z)]), z, r, seed + x * 7 + z)


def footprints(t, block_cells):
    """Empreintes au milieu du sentier de la forêt, tous les trois blocs."""
    out = []
    samples = curve(PATHS["forest"], step=3.0)
    for sx, sz, _, _ in samples[6:-2]:
        c = (round(sx), round(sz))
        if c in t.stand and c not in block_cells:
            out.append(c)
    return out
