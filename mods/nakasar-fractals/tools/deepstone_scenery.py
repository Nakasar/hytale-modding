"""Carte et décor de Pierre-Profonde (Deepstone), d'après la carte GW2 que Kevin a envoyée (25 octobre 2026).

On arrive en haut d'une montagne enneigée et l'on descend une suite de corniches jusqu'à la porte du caveau des nains
de Deldrimor. Dedans :

- la salle du cristal (au centre), dont la porte nord reste fermée ;
- à l'ouest, le couloir de la grille de runes (les motifs lumineux glissent du nord vers le sud) et, au bout, la
  corniche de la Sentinelle de Pierre-Profonde, ouverte sur le vide à l'ouest ;
- à l'est, le couloir des toiles, puis le pont étroit balayé par le vent au-dessus du gouffre, et la salle de la Reine
  de la couvée ;
- au nord de la salle du cristal, la salle du gouffre (le chemin de dalles se révèle à la Lumière de Deldrimor), puis
  la salle de l'ascenseur, dont la plate-forme descend de 30 blocs ;
- en bas, un couloir et une passerelle mènent à l'arène de dalles de la Voix, au-dessus d'un gouffre.

Repère : x vers l'est, z vers le sud ; « debout à s » : le sol est en s - 1 (y monde = 100 + s). Les gouffres n'ont
pas de fond : on tombe jusqu'au filet anti-chute (y monde 40, s = -60) ; le Java ramène avant (dalles, pont).
Rien n'est tiré au hasard sans graine : un prefab régénéré est identique.
"""
import math

import numpy as np

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

AIR = go.AIR
pick = fc.pick
hash01 = fn.hash01
fbm2 = fn.fbm2

# --- matières (vanilla) ------------------------------------------------------------------------------------------
ROCK = ["Rock_Slate", "Rock_Basalt", "Rock_Stone", "Rock_Slate", "Rock_Shale"]
DEEP_ROCK = ["Rock_Slate", "Rock_Basalt", "Rock_Slate", "Rock_Shale"]
SNOW = "Soil_Snow"
SNOW_HALF = "Soil_Snow_Half"
ICE = "Rock_Ice"
BRICK = ["Rock_Basalt_Brick", "Rock_Runic_Dark_Brick", "Rock_Basalt_Brick", "Rock_Basalt_Brick_Decorative"]
FLOOR = ["Rock_Basalt_Brick_Smooth", "Rock_Basalt_Brick_Smooth", "Rock_Runic_Dark_Brick", "Rock_Basalt_Brick_Smooth"]
TRIM = "Rock_Runic_Teal_Brick"
PILLAR_BASE = "Rock_Basalt_Brick_Pillar_Base"
PILLAR_MID = "Rock_Basalt_Brick_Pillar_Middle"
BEAM = "Rock_Basalt_Brick_Beam"
RUNE_TILE = "Rock_Runic_Brick"                  # grille de runes de l'ouest (éteinte)
RUNE_INLAY = "Rock_Runic_Blue_Brick"
TILE_EDGE = "Rock_Basalt_Brick_Smooth"           # dalles du gouffre et de l'arène (le centre en rune)
TILE_CORE = "Rock_Runic_Teal_Brick"
LANTERN = "Deco_Lantern"
BRAZIER = "Furniture_Temple_Light_Brazier"
WEBS = ["Deco_SpiderWeb", "Deco_SpiderWeb_Full", "Deco_SpiderWeb"]
WEB_FLAT = "Deco_SpiderWeb_Flat"
CRYSTALS = ["Rock_Crystal_Blue_Small", "Rock_Crystal_Cyan_Small", "Rock_Crystal_White_Small", "Rock_Crystal_Blue_Medium"]
ICICLES = "Rock_Ice_Icicles"
# Blocs du mod (écrits par generate_deepstone.py, ou déjà là).
CRYSTAL = "Nakasar_Fractal_Deepstone_Crystal"
PIT_ORB = "Nakasar_Fractal_Deepstone_Pit_Orb"
RUNE_PLATE = "Nakasar_Fractal_Pressure_Plate"     # plaque de la Falaise (pierre runique)
LIFT_RUNE = "Nakasar_Fractal_Deepstone_Lift_Rune"
BARRIER = "Nakasar_Fractal_Mist_Barrier"          # barrière de brume de la Falaise
SPIDER_EGGS = "Nakasar_Fractal_Spider_Eggs"       # œufs du Marais (modèle vanilla EggSacks_Scarak_Medium)

ABYSS = -50                                      # bas des parois des gouffres (filet anti-chute : s = -60)
TOP = 18                                         # dessus des parois du caveau
EMPRISE = (-90, 120, -204, 104)                   # x0, x1, z0, z1

# --- l'arrivée : corniches de neige du sommet jusqu'à la porte du caveau ------------------------------------------
SPAWN = (0, 24, 78)
TORIN_AT = (-3, 24, 72)
KAY_AT = (3, 24, 72)
# (x0, x1, z0, z1, debout) : chaque corniche est 3 blocs sous la précédente.
DESCENT = [
    (-12, 12, 66, 86, 24),
    (6, 18, 54, 66, 21),
    (8, 20, 44, 54, 18),
    (-4, 10, 38, 46, 15),
    (-16, -2, 32, 40, 12),
    (-20, -8, 24, 32, 9),
    (-12, 0, 20, 26, 6),
    (-6, 4, 18, 22, 3),
]
BAT_SPOTS = [(13, 21, 60), (14, 18, 48), (2, 15, 42), (-10, 12, 36), (-14, 9, 28)]

# --- la salle du cristal --------------------------------------------------------------------------------------------
HALL = (-18, 18, -6, 18)                          # x0, x1, z0, z1 (debout 0)
HALL_C = (0, 0, 5)
ENTRY = (-4, 4, 18, 22)                           # porte sud (debout 0)
CRYSTAL_AT = (0, 0, 14)
RETURN_AT = (0, 0, 10)                            # où ramènent les orbes de lumière
MINOTAUR_AT = (0, 0, 0)
NORTH_GATE = (-3, 3, -7, -6)                      # porte nord (fermée jusqu'au Minotaure)

# --- l'ouest : couloir, grille de runes, corniche de la Sentinelle --------------------------------------------------
WEST_HALL = (-38, -18, 2, 9)
GRID_X0, GRID_Z0 = -38, -38                       # coin nord-ouest de la grille
GRID_COLS, GRID_ROWS, GRID_TILE = 5, 20, 2        # 10 x 40 blocs
GRID_START = (-33.5, 0, 5.5)                      # retour au départ de la grille
GRID_END = (-38, -29, -46, -39)                   # palier au nord (les deux runes)
WEST_RUNES = [(-36, 0, -42), (-31, 0, -42)]
WEST_GATE = (-38, -29, -47, -47)                  # barrière de brume vers la corniche
SENTINEL_C = (-48, -61)
SENTINEL_R = 13
SENTINEL_EDGE_X = -60                              # au-delà : le vide
WEST_ORB = (-42, 0, -54)

# --- l'est : couloir des toiles, pont du vent, salle de la Reine ----------------------------------------------------
EAST_HALL = (18, 36, 0, 10)
CORRIDOR_NEST = (30, 0, 2)
BRIDGE_X0, BRIDGE_X1 = 36, 74
BRIDGE_Z0, BRIDGE_Z1 = 4, 6                       # 3 blocs de large
BRIDGE_START = (34.5, 0, 5.5)
BRIDGE_NESTS = [(44, 0, 2), (55, 0, 8), (66, 0, 2)]
BRIDGE_BAYS = [(42, 46, 1, 3), (53, 57, 7, 9), (64, 68, 1, 3)]   # élargissements (x0, x1, z0, z1) des nids
EAST_RUNES = [(54, 0, 1), (54, 0, 9)]
RUNE_BAYS = [(53, 55, 1, 3), (53, 55, 7, 9)]
QUEEN_C = (88, 5)
QUEEN_R = 14
QUEEN_NESTS = [(82, 0, -4), (94, 0, 14)]
EAST_ORB = (92, 0, -2)
EAST_GATE = (73, 73, 3, 7)                        # barrière de brume au bout du pont (les runes l'ouvrent)

# --- le nord : la salle du gouffre, l'ascenseur ------------------------------------------------------------------
NORTH_HALL = (-3, 3, -28, -6)
PIT_ROOM = (-20, 20, -72, -26)                     # avec les murs
PIT_X0, PIT_Z0 = -16, -67                          # coin nord-ouest des dalles
PIT_COLS, PIT_ROWS, PIT_TILE = 11, 13, 3           # 33 x 39 blocs
PIT_LEDGE = (-16, 16, -28, -27)                    # palier sud, à l'entrée
# Orbes (case de dalle) : départ au sud, puis ouest, nord-est, nord-ouest (ordre du guide).
PIT_ORBS = [(5, 12), (0, 8), (10, 4), (1, 0)]
PIT_EXIT = (-3, 3, -72, -68)
LIFT_HALL = (-3, 3, -84, -72)
LIFT_ROOM = (-9, 9, -96, -84)
LIFT = (-4, 4, -96, -88)                           # plate-forme (debout 0 en haut)
LIFT_TOP, LIFT_STOP, LIFT_BOTTOM = 0, -15, -30
LIFT_RUNE_AT = (7, 0, -92)
LIFT_LANDING = (0, -30, -99)

# --- l'arène de la Voix ---------------------------------------------------------------------------------------------
VOICE_STAND = -30
TUNNEL = (-3, 3, -116, -97)                         # couloir creusé au pied du puits (debout -30)
ARENA_X0, ARENA_Z0 = -22, -173
ARENA_N, ARENA_TILE = 15, 3                         # 45 x 45 blocs
ARENA_C = (0, -150)
WALKWAY = (-1, 1, -128, -117)                       # passerelle du couloir à l'arène
REWARD_AT = (-3, VOICE_STAND, -151)                 # coffre et pierre de sortie (dalles du centre)
END_EXIT_AT = (3, VOICE_STAND, -151)

# --- trésors cachés de la Lumière de Deldrimor (10, comme dans GW2) ------------------------------------------------
TREASURES = [(9, 18, 50), (-16, 9, 27), (15, 0, 15), (-34, 0, 7), (-54, 0, -60), (32, 0, 8), (95, 0, 11),
             (-15, 0, -28), (8, 0, -98), (2, -30, -110)]


# --- grille ---------------------------------------------------------------------------------------------------------

class Terrain:
    """Grille 2D de la carte : sol (debout) des cases praticables, gouffres, tunnels ; parois autour."""

    NONE = -999

    def __init__(self):
        x0, x1, z0, z1 = EMPRISE
        self.x0, self.z0 = x0, z0
        self.w, self.h = x1 - x0 + 1, z1 - z0 + 1
        self.stand = np.full((self.w, self.h), self.NONE, dtype=np.int32)
        self.kind = np.zeros((self.w, self.h), dtype=np.int8)        # 0 roche, 1 ouvert, 2 tunnel, 3 gouffre, 4 pont
        self.built = np.zeros((self.w, self.h), dtype=bool)          # salle des nains (murs de briques)

    OPEN, TUNNEL, ABYSS_K, BRIDGE = 1, 2, 3, 4

    def idx(self, x, z):
        return x - self.x0, z - self.z0

    def rect(self, x0, x1, z0, z1, stand, kind=OPEN, built=True):
        i0, k0 = self.idx(min(x0, x1), min(z0, z1))
        i1, k1 = self.idx(max(x0, x1), max(z0, z1))
        self.stand[i0:i1 + 1, k0:k1 + 1] = stand
        self.kind[i0:i1 + 1, k0:k1 + 1] = kind
        self.built[i0:i1 + 1, k0:k1 + 1] = built

    def disc(self, cx, cz, r, stand, kind=OPEN, built=False, noise=0.0, seed=0):
        for x in range(cx - r - 3, cx + r + 4):
            for z in range(cz - r - 3, cz + r + 4):
                rr = r + noise * fbm2(x, z, 6, 2, seed)
                if math.hypot(x - cx, z - cz) <= rr:
                    i, k = self.idx(x, z)
                    self.stand[i, k] = stand
                    self.kind[i, k] = kind
                    self.built[i, k] = built

    def blob(self, cx, cz, rx, rz, stand, kind=OPEN, built=False, noise=0.18, seed=0):
        """Ellipse au bord irrégulier (gouffres, corniches naturelles)."""
        for x in range(int(cx - rx * 1.4) - 2, int(cx + rx * 1.4) + 3):
            for z in range(int(cz - rz * 1.4) - 2, int(cz + rz * 1.4) + 3):
                d = math.hypot((x - cx) / rx, (z - cz) / rz)
                if d <= 1 + noise * fbm2(x, z, 9, 3, seed):
                    i, k = self.idx(x, z)
                    if 0 <= i < self.w and 0 <= k < self.h:
                        self.stand[i, k] = stand
                        self.kind[i, k] = kind
                        self.built[i, k] = built

    def ledge(self, x0, x1, z0, z1, stand, seed=0):
        """Corniche rectangulaire aux bords rongés (arrivée)."""
        for x in range(x0 - 2, x1 + 3):
            for z in range(z0 - 2, z1 + 3):
                inset = 1.6 * fbm2(x, z, 5, 2, seed)
                dx = max(x0 - x, x - x1, 0)
                dz = max(z0 - z, z - z1, 0)
                inside = min(x - x0, x1 - x, z - z0, z1 - z)
                if (dx == 0 and dz == 0 and inside >= inset - 0.6) or (math.hypot(dx, dz) < inset):
                    i, k = self.idx(x, z)
                    if self.kind[i, k] == 0 or self.stand[i, k] < stand:
                        self.stand[i, k] = stand
                        self.kind[i, k] = self.OPEN
                        self.built[i, k] = False

    def walkable(self, x, z):
        i, k = self.idx(x, z)
        if not (0 <= i < self.w and 0 <= k < self.h):
            return False
        return self.kind[i, k] in (self.OPEN, self.TUNNEL, self.BRIDGE)

    def stand_at(self, x, z):
        i, k = self.idx(round(x), round(z))
        return int(self.stand[i, k]) if self.walkable(round(x), round(z)) else None

    def near_abyss(self, reach):
        """Cases à moins de `reach` blocs (carré) d'un gouffre : leur sol descend jusqu'au bas des parois."""
        abyss = self.kind == self.ABYSS_K
        out = np.zeros_like(abyss)
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                sx = slice(max(dx, 0), self.w + min(dx, 0))
                tx = slice(max(-dx, 0), self.w + min(-dx, 0))
                sz = slice(max(dz, 0), self.h + min(dz, 0))
                tz = slice(max(-dz, 0), self.h + min(-dz, 0))
                out[sx, sz] |= abyss[tx, tz]
        return out

    def carved(self):
        return self.kind > 0

    def distance(self, limit=14):
        """Distance (chanfrein 1 / 1,4) de chaque case de roche à la case creusée la plus proche, et le plus bas sol
        des cases creusées à moins de 3,5 blocs (bas des parois)."""
        big = 1e9
        dist = np.where(self.carved(), 0.0, big)
        low = np.where(self.carved(), np.where(self.kind == self.ABYSS_K, ABYSS, self.stand), 10 ** 6).astype(np.float64)
        low_reach = np.where(self.carved(), 0.0, big)
        steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4), (1, -1, 1.4), (-1, 1, 1.4), (-1, -1, 1.4)]
        for _ in range(limit + 2):
            for dx, dz, c in steps:
                shifted = np.full_like(dist, big)
                shifted_low = np.full_like(low, 10 ** 6)
                shifted_reach = np.full_like(low_reach, big)
                sx = slice(max(dx, 0), self.w + min(dx, 0))
                tx = slice(max(-dx, 0), self.w + min(-dx, 0))
                sz = slice(max(dz, 0), self.h + min(dz, 0))
                tz = slice(max(-dz, 0), self.h + min(-dz, 0))
                shifted[sx, sz] = dist[tx, tz] + c
                shifted_reach[sx, sz] = low_reach[tx, tz] + c
                shifted_low[sx, sz] = low[tx, tz]
                dist = np.minimum(dist, shifted)
                ok = shifted_reach <= 3.5
                better = ok & (shifted_low < low)
                low = np.where(better, shifted_low, low)
                low_reach = np.where(better, np.minimum(low_reach, shifted_reach), low_reach)
        return dist, low


def layout():
    t = Terrain()
    for n, (x0, x1, z0, z1, s) in enumerate(DESCENT):
        t.ledge(x0, x1, z0, z1, s, seed=60 + n)
    t.rect(*ENTRY, 0)
    t.rect(*HALL, 0)
    # ouest
    t.rect(*WEST_HALL, 0)
    t.rect(GRID_X0, GRID_X0 + GRID_COLS * GRID_TILE - 1, GRID_Z0, 1, 0)
    t.rect(*GRID_END, 0)
    t.rect(WEST_GATE[0], WEST_GATE[1], WEST_GATE[2] - 1, WEST_GATE[3], 0)
    t.blob(-70, -60, 12, 28, 0, Terrain.ABYSS_K, seed=33)
    t.disc(SENTINEL_C[0], SENTINEL_C[1], SENTINEL_R, 0, noise=1.5, seed=31)
    t.rect(-80, SENTINEL_EDGE_X, -76, -46, 0, Terrain.ABYSS_K, built=False)
    # est
    t.rect(*EAST_HALL, 0)
    t.blob(55, 5, 21, 24, 0, Terrain.ABYSS_K, seed=35)
    t.rect(BRIDGE_X0, BRIDGE_X1, BRIDGE_Z0, BRIDGE_Z1, 0, Terrain.BRIDGE)
    for x0, x1, z0, z1 in BRIDGE_BAYS + RUNE_BAYS:
        t.rect(x0, x1, z0, z1, 0, Terrain.BRIDGE)
    t.disc(QUEEN_C[0], QUEEN_C[1], QUEEN_R, 0, noise=1.5, seed=37)
    t.rect(BRIDGE_X1 - 2, BRIDGE_X1 + 3, BRIDGE_Z0 - 1, BRIDGE_Z1 + 1, 0)
    # nord
    t.rect(*NORTH_HALL, 0)
    t.rect(PIT_ROOM[0] + 3, PIT_ROOM[1] - 3, PIT_ROOM[2] + 3, PIT_ROOM[3] - 1, 0)
    t.rect(PIT_X0, PIT_X0 + PIT_COLS * PIT_TILE - 1, PIT_Z0, PIT_Z0 + PIT_ROWS * PIT_TILE - 1, 0, Terrain.ABYSS_K)
    t.rect(*PIT_LEDGE, 0)
    t.rect(*PIT_EXIT, 0)
    t.rect(*LIFT_HALL, 0)
    t.rect(*LIFT_ROOM, 0)
    t.rect(*LIFT, LIFT_BOTTOM)
    # la Voix
    t.blob(ARENA_C[0], ARENA_C[1] - 2, 34, 36, 0, Terrain.ABYSS_K, noise=0.12, seed=39)
    t.rect(*TUNNEL, VOICE_STAND, Terrain.TUNNEL)
    t.rect(*WALKWAY, VOICE_STAND, Terrain.BRIDGE)
    return t


def top_height(x, z):
    """Dessus de la roche : parois du caveau, plus haut vers le sommet de l'arrivée."""
    h = TOP + 4 * fbm2(x, z, 18, 3, 71)
    if z > 14:
        h += min(12.0, (z - 14) * 0.5)
    return int(round(h))


# --- pose -----------------------------------------------------------------------------------------------------------

def build(p):
    """Pose la roche, les sols et les parois ; rend le terrain."""
    t = layout()
    dist, low = t.distance()
    cliff = t.near_abyss(2)
    for i in range(t.w):
        x = i + t.x0
        for k in range(t.h):
            z = k + t.z0
            kind = t.kind[i, k]
            if kind == Terrain.ABYSS_K:
                continue
            if kind in (Terrain.OPEN, Terrain.TUNNEL, Terrain.BRIDGE):
                s = int(t.stand[i, k])
                floor(p, t, x, z, s, kind, bool(t.built[i, k]), ABYSS - 3 if cliff[i, k] else s - 4)
                continue
            d = dist[i, k]
            if d > 14:
                continue
            top = top_height(x, z)
            if d > 11:
                top -= int((d - 11) * 4)
            if d <= 3.5:
                bottom = int(low[i, k]) - 3
            else:
                bottom = top - 1
            for y in range(bottom, top + 1):
                p.set(x, y, z, pick(DEEP_ROCK if y < -4 else ROCK, x, y, z))
            p.set(x, top + 1, z, SNOW if hash01(x, z, 0, 5) < 0.85 else SNOW_HALF)
    walls(p, t, dist)
    return t


def floor(p, t, x, z, s, kind, built, deep):
    """Sol d'une case praticable : dalles de basalte dans le caveau, roche et neige dehors, pont fin."""
    if kind == Terrain.BRIDGE:
        p.set(x, s - 1, z, pick(FLOOR, x, s, z))
        p.set(x, s - 2, z, BEAM if (x + z) % 4 else PILLAR_BASE)
        return
    if built:
        p.set(x, s - 1, z, pick(FLOOR, x, s - 1, z))
    else:
        outside = s > 0 or z > 18
        p.set(x, s - 1, z, SNOW if outside and hash01(x, z, 1, 9) < 0.8 else pick(ROCK, x, s - 1, z))
    for y in range(deep, s - 1):
        p.set(x, y, z, pick(DEEP_ROCK, x, y, z))
    if kind == Terrain.TUNNEL:
        top = top_height(x, z)
        for y in range(s + 5, top + 1):
            p.set(x, y, z, pick(DEEP_ROCK if y < -4 else ROCK, x, y, z))
        p.set(x, top + 1, z, SNOW)
        p.set(x, s + 4, z, BEAM if z % 5 else PILLAR_MID)


def walls(p, t, dist):
    """Parement de briques des salles des nains : la face de roche contre une salle, jusqu'à 7 blocs, liseré runique."""
    for i in range(t.w):
        for k in range(t.h):
            if t.kind[i, k] != 0 or dist[i, k] > 1.01:
                continue
            x, z = i + t.x0, k + t.z0
            near = [(x + dx, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            rooms = [(nx, nz) for nx, nz in near if t.walkable(nx, nz) and t.built[t.idx(nx, nz)]
                     and t.kind[t.idx(nx, nz)] != Terrain.BRIDGE]
            if not rooms:
                continue
            s = min(int(t.stand[t.idx(nx, nz)]) for nx, nz in rooms)
            tunnel = any(t.kind[t.idx(nx, nz)] == Terrain.TUNNEL for nx, nz in rooms)
            for y in range(s, s + (5 if tunnel else 7)):
                p.set(x, y, z, pick(BRICK, x, y, z))
            if not tunnel:
                p.set(x, s + 7, z, TRIM)
                if (x + z) % 7 == 0:
                    for y in range(s, s + 7):
                        p.set(x, y, z, PILLAR_BASE if y == s else PILLAR_MID)


# --- salles ---------------------------------------------------------------------------------------------------------

def hall(p):
    """Salle du cristal : rosace de runes, neuf cercles, piliers, braseros ; le cristal près de la porte sud."""
    x0, x1, z0, z1 = HALL
    cx, _, cz = HALL_C
    for gx in (-8, 0, 8):
        for gz in (-6, 1, 8):
            for x in range(cx + gx - 2, cx + gx + 3):
                for z in range(cz + gz - 2, cz + gz + 3):
                    d = math.hypot(x - cx - gx, z - cz - gz)
                    if 1.5 <= d <= 2.5:
                        p.set(x, -1, z, RUNE_INLAY)
                    elif d < 1.5:
                        p.set(x, -1, z, TRIM)
    for x, z in ((x0 + 3, z0 + 3), (x1 - 3, z0 + 3), (x0 + 3, z1 - 3), (x1 - 3, z1 - 3)):
        pillar(p, x, 0, z, 12)
        p.set(x + (1 if x < cx else -1), 0, z + (1 if z < cz else -1), BRAZIER)
    p.set(*CRYSTAL_AT, CRYSTAL)
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        p.set(CRYSTAL_AT[0] + dx, -1, CRYSTAL_AT[2] + dz, RUNE_INLAY)
    # porte nord : barrière de brume (le Minotaure l'ouvre)
    gate(p, NORTH_GATE, 0, 6)


def pillar(p, x, s, z, height):
    p.set(x, s, z, PILLAR_BASE)
    for y in range(s + 1, s + height):
        p.set(x, y, z, PILLAR_MID)
    p.set(x, s + height, z, BRICK[0])


def gate(p, box, s, height, block=BARRIER):
    """Barrière (bloc de brume) qui ferme un passage ; rend ses cases (le Java les retire)."""
    x0, x1, z0, z1 = box
    cells = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(s, s + height):
                p.set(x, y, z, block)
                cells.append((x, y, z))
    return cells


def gate_cells(box, s, height):
    x0, x1, z0, z1 = box
    return [(x, y, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) for y in range(s, s + height)]


def west(p):
    """Grille de runes (dalles de 2 blocs) et palier des deux runes, corniche de la Sentinelle."""
    for c in range(GRID_COLS):
        for r in range(GRID_ROWS):
            for dx in range(GRID_TILE):
                for dz in range(GRID_TILE):
                    x, z = GRID_X0 + c * GRID_TILE + dx, GRID_Z0 + r * GRID_TILE + dz
                    edge = dx == GRID_TILE - 1 or dz == GRID_TILE - 1
                    p.set(x, -1, z, RUNE_TILE if not edge else "Rock_Basalt_Brick_Smooth")
    for x, s, z in WEST_RUNES:
        p.set(x, s - 1, z, RUNE_INLAY)
        p.set(x, s, z, RUNE_PLATE)
    gate(p, WEST_GATE, 0, 6)
    # corniche : neige et glace, cristaux au pied des parois, rien sur le bord ouest (le vide)
    cx, cz = SENTINEL_C
    for x in range(cx - SENTINEL_R - 3, cx + SENTINEL_R + 4):
        for z in range(cz - SENTINEL_R - 3, cz + SENTINEL_R + 4):
            if (x, -1, z) in p.blocks and x < SENTINEL_EDGE_X + 3 and hash01(x, z, 2, 3) < 0.4:
                p.set(x, -1, z, ICE)
    for a in range(0, 360, 30):
        x = round(cx + math.cos(math.radians(a)) * (SENTINEL_R - 1))
        z = round(cz + math.sin(math.radians(a)) * (SENTINEL_R - 1))
        if x > SENTINEL_EDGE_X + 4 and (x, -1, z) in p.blocks and (x, 0, z) not in p.blocks:
            p.set(x, 0, z, CRYSTALS[a // 30 % len(CRYSTALS)])


def east(p):
    """Toiles du couloir, nids (œufs vanilla), runes du pont, salle de la Reine."""
    x0, x1, z0, z1 = EAST_HALL
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            h = hash01(x, z, 3, 17)
            if h < 0.09 and abs(z - 5) > 1:
                p.set(x, 0, z, WEBS[int(h * 100) % len(WEBS)])
            elif h > 0.94:
                p.set(x, 5, z, WEB_FLAT)
    for x, s, z in [CORRIDOR_NEST] + BRIDGE_NESTS + QUEEN_NESTS:
        p.set(x, s, z, SPIDER_EGGS)
    for x, s, z in EAST_RUNES:
        p.set(x, s - 1, z, RUNE_INLAY)
        p.set(x, s, z, RUNE_PLATE)
    gate(p, EAST_GATE, 0, 6)
    cx, cz = QUEEN_C
    for x in range(cx - QUEEN_R - 2, cx + QUEEN_R + 3):
        for z in range(cz - QUEEN_R - 2, cz + QUEEN_R + 3):
            if (x, -1, z) not in p.blocks or (x, 0, z) in p.blocks:
                continue
            h = hash01(x, z, 4, 23)
            d = math.hypot(x - cx, z - cz)
            if d > QUEEN_R - 3 and h < 0.12:
                p.set(x, 0, z, WEBS[int(h * 100) % len(WEBS)])


def pit_room(p):
    """Salle du gouffre : dalles autour des orbes (sûres) et orbes éteintes ; palier sud."""
    for c, r in PIT_ORBS:
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if 0 <= c + dc < PIT_COLS and 0 <= r + dr < PIT_ROWS:
                    tile(p, PIT_X0, PIT_Z0, PIT_TILE, c + dc, r + dr, 0)
        x, z = tile_center(PIT_X0, PIT_Z0, PIT_TILE, c, r)
        p.set(x, 0, z, PIT_ORB)
    for x in (PIT_ROOM[0] + 3, PIT_ROOM[1] - 3):
        for z in range(PIT_ROOM[2] + 4, PIT_ROOM[3] - 1, 8):
            pillar(p, x, 0, z, 9) if (x, -1, z) in p.blocks else None


def tile(p, x0, z0, size, c, r, s):
    for dx in range(size):
        for dz in range(size):
            x, z = x0 + c * size + dx, z0 + r * size + dz
            core = dx == size // 2 and dz == size // 2
            p.set(x, s - 1, z, TILE_CORE if core else TILE_EDGE)


def tile_center(x0, z0, size, c, r):
    return x0 + c * size + size // 2, z0 + r * size + size // 2


def lift(p):
    """Plate-forme de l'ascenseur (en haut), rune centrale, rune des retardataires, puits."""
    x0, x1, z0, z1 = LIFT
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            p.set(x, LIFT_TOP - 1, z, "Rock_Basalt_Brick" if edge else TILE_EDGE)
    cx, cz = (x0 + x1) // 2, (z0 + z1) // 2
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            p.set(cx + dx, LIFT_TOP - 1, cz + dz, RUNE_INLAY if dx or dz else TILE_CORE)
    p.set(*LIFT_RUNE_AT, LIFT_RUNE)
    # parois du puits sous l'anneau de la salle (le couloir du bas s'ouvre au nord)
    for x in range(x0 - 2, x1 + 3):
        for z in range(z0 - 2, z1 + 3):
            if x0 <= x <= x1 and z0 <= z <= z1:
                continue
            for y in range(LIFT_BOTTOM - 3, LIFT_TOP - 4):
                in_tunnel = TUNNEL[0] <= x <= TUNNEL[1] and z <= TUNNEL[3] and LIFT_BOTTOM <= y < LIFT_BOTTOM + 5
                if not in_tunnel:
                    p.set(x, y, z, pick(DEEP_ROCK, x, y, z))
    for x, z in ((LIFT_ROOM[0] + 1, LIFT_ROOM[2] + 1), (LIFT_ROOM[1] - 1, LIFT_ROOM[2] + 1),
                 (LIFT_ROOM[0] + 1, LIFT_ROOM[3] - 1), (LIFT_ROOM[1] - 1, LIFT_ROOM[3] - 1)):
        pillar(p, x, 0, z, 10)


def arena(p):
    """Arène de la Voix : dalles au centre (7 x 7) et vers la passerelle ; le reste se remplit au combat (Java)."""
    mid = ARENA_N // 2
    for c in range(ARENA_N):
        for r in range(ARENA_N):
            if (abs(c - mid) <= 3 and abs(r - mid) <= 3) or (c == mid and r > mid):
                tile(p, ARENA_X0, ARENA_Z0, ARENA_TILE, c, r, VOICE_STAND)
    # piliers brisés et cristaux autour du gouffre
    for a in range(0, 360, 24):
        x = round(ARENA_C[0] + math.cos(math.radians(a)) * 31)
        z = round(ARENA_C[1] + math.sin(math.radians(a)) * 31)
        h = 6 + int(hash01(x, z, 5, 3) * 10)
        for y in range(VOICE_STAND - 12, VOICE_STAND + h):
            p.set(x, y, z, PILLAR_MID if y > VOICE_STAND - 12 else PILLAR_BASE)
            p.set(x + 1, y, z, pick(BRICK, x + 1, y, z)) if y < VOICE_STAND + h - 3 else None


def lights(p, t):
    """Lanternes le long des parois des salles (une tous les 7 blocs environ), cristaux dans les coins."""
    for i in range(t.w):
        for k in range(t.h):
            if t.kind[i, k] not in (Terrain.OPEN, Terrain.TUNNEL) or not t.built[i, k]:
                continue
            x, z = i + t.x0, k + t.z0
            s = int(t.stand[i, k])
            if (x, s, z) in p.blocks or (x, s - 1, z) not in p.blocks:
                continue
            against = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, s + 1, z + dz) in p.blocks
                          and not t.walkable(x + dx, z + dz))
            if against == 1 and hash01(x, z, 6, 41) < 0.12 and not near_grid(x, z):
                p.set(x, s, z, LANTERN)
            elif against == 2 and hash01(x, z, 7, 43) < 0.5:
                p.set(x, s, z, CRYSTALS[int(hash01(x, z, 8, 1) * 4)])


def near_grid(x, z):
    """Cases où rien ne doit gêner : grille de runes, pont, dalles, plate-forme, alentours des runes."""
    if GRID_X0 - 1 <= x <= GRID_X0 + GRID_COLS * GRID_TILE and GRID_Z0 - 9 <= z <= 9:
        return True
    if LIFT[0] - 1 <= x <= LIFT[1] + 1 and LIFT[2] - 1 <= z <= LIFT[3] + 1:
        return True
    return False


def descent(p):
    """Le sommet : congères, glaçons et quelques sapins enneigés au bord des corniches."""
    for x0, x1, z0, z1, s in DESCENT:
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if (x, s, z) in p.blocks:
                    continue
                h = hash01(x, z, 9, 7)
                edge = x in (x0, x1) or z in (z0, z1)
                if edge and h < 0.25:
                    p.set(x, s, z, SNOW_HALF)
                elif h > 0.985:
                    p.set(x, s, z, CRYSTALS[2])


def build_all():
    p = go.Prefab()
    t = build(p)
    hall(p)
    west(p)
    east(p)
    pit_room(p)
    lift(p)
    arena(p)
    descent(p)
    lights(p, t)
    return p, t
