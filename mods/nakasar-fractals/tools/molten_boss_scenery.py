"""Carte et décor de la Fonderie en fusion (Molten Boss, GW2), d'après le guide Hardstuck et la carte que Kevin a
envoyée (28 octobre 2026).

La Fonderie de l'Alliance en fusion (Légion de la Flamme et Draguerre) flotte dans les Brumes : un bloc d'ateliers de
basalte posé sur une île de roche volcanique, cerné de nuages. On la parcourt comme sur la carte de GW2 :

- le surplomb du départ (Braham et Rox), au centre ; une rampe descend vers le sud dans la cour des scories (meute 1) ;
- à l'ouest, l'atelier : trois travées en lacet (meutes 2 et 3), la travée nord (meute 4 : résonateur draguerre et
  chaman de la flamme d'élite) ; au nord, un canal de lave que le pont franchit quand la meute 4 tombe ;
- la fonderie du nord-ouest et ses bassins de lave : l'Effigie en fusion, son Protecteur, un second résonateur ;
- la cour des wagonnets (groupe 5), puis la passerelle des cuves vers l'est, au-dessus du vide (groupes 6 à 8) ;
- la salle des chaudières, au nord-est (point de retour) ; un pont descend au sud vers la plate-forme ronde du
  creuset, au-dessus du vide : le Berserker et la Tempête de feu en fusion.

Repère : x vers l'est, z vers le sud, y monde = GROUND_Y + y prefab. « debout à s » : le sol est en s - 1. Rien n'est
tiré au hasard sans graine : un prefab régénéré est identique.
"""
import math
from collections import deque

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

AIR = go.AIR
pick = fc.pick
hash01 = fn.hash01
fbm2 = fn.fbm2
LAVA = "Lava_Source"

# --- matières (vanilla) ----------------------------------------------------------------------------------------
FLOOR = ["Rock_Volcanic_Brick_Smooth", "Rock_Volcanic_Brick_Smooth", "Rock_Basalt_Brick_Smooth", "Rock_Volcanic_Brick"]
FLOOR_WORN = ["Rock_Volcanic_Cobble", "Rock_Basalt_Cobble", "Rock_Volcanic", "Soil_Ash", "Rock_Magma_Cooled"]
YARD = ["Soil_Ash", "Rock_Volcanic", "Rock_Volcanic_Cobble", "Soil_Ash", "Rock_Magma_Cooled", "Soil_Dirt_Burnt"]
DECK = ["Rock_Basalt_Brick_Smooth", "Rock_Basalt_Brick", "Rock_Basalt_Brick_Smooth"]
ARENA_TILE = ["Rock_Volcanic_Brick_Smooth", "Rock_Basalt_Brick_Smooth", "Rock_Volcanic_Brick_Smooth"]
ARENA_RING = "Rock_Volcanic_Brick_Ornate"
GLOW = "Rock_Volcanic_Cracked_Incandescent"     # fissures incandescentes (lumière)
LAVA_CRACK = "Rock_Volcanic_Cracked_Lava"
WALL = ["Rock_Volcanic_Brick", "Rock_Basalt_Brick", "Rock_Volcanic_Brick", "Rock_Volcanic_Brick_Decorative"]
WALL_TOP = "Rock_Volcanic_Brick_Roof_Flat"
PILLAR_BASE = "Rock_Volcanic_Brick_Pillar_Base"
PILLAR_MID = "Rock_Volcanic_Brick_Pillar_Middle"
BEAM = "Rock_Basalt_Brick_Beam"
RAIL = "Rock_Volcanic_Brick_Wall"               # balustrade (rotation 0 : ligne le long de X, 1 : le long de Z)
BARS = "Deco_Iron_Bars"                         # garde-corps de fer (même rotation)
ROCK = ["Rock_Volcanic", "Rock_Basalt", "Rock_Volcanic", "Rock_Magma_Cooled", "Rock_Slate"]
CHAINS = "Deco_Iron_Chains_Vertical"
BRAZIER = "Furniture_Crude_Brazier"
TORCH = "Furniture_Crude_Torch"
PROPS = ["Furniture_Ancient_Crate", "Furniture_Ancient_Barrel", "Furniture_Village_Crate", "Deco_Iron_Stack"]
ORE = ["Ore_Iron_Volcanic", "Ore_Iron_Basalt", "Ore_Iron_Basalt_Cracked"]
BARRIER = "Nakasar_Fractal_Mist_Barrier"          # barrière de brume de la Falaise
VOLCANIC = fn.THEMES["volcanic"]

# --- la carte (x0, x1, z0, z1, debout, genre) ------------------------------------------------------------------
# Genres : "hall" (atelier : murs de briques), "yard" (cour : sol de cendre, murets de roche), "deck" (passerelle,
# garde-corps), "open" (bord sur le vide, sans rien : l'arène).
CAMP = (-36, -6, -14, 8, 10)
SPAWN = (-21, 10, -2)
BRAHAM_AT = (-25, 10, -9)
ROX_AT = (-17, 10, -9)
RAMP = (-30, -22, 9, 33)                          # x0, x1, z0, z1 : de debout 10 (nord) à 0 (sud)
YARD_H = (-42, -4, 29, 58, 0)
PASSAGE = (-62, -37, 38, 50, 0)
WORKSHOP = (-112, -62, -18, 64, 0)
# Cloisons de l'atelier : (z, x0, x1) murs pleins, la baie libre est le reste de la largeur.
PARTITIONS = [(33, -97, -62), (7, -112, -77)]
CHANNEL = (-114, -60, -31, -19)                   # canal de lave (x0, x1, z0, z1)
CHANNEL_LAVA_TOP = -2                             # surface de la lave (bloc d'air rempli de lave), deux blocs sous le sol
BRIDGE = (-90, -84, -31, -19)                     # pont posé par le Java (meute 4 vaincue)
FOUNDRY = (-114, -56, -84, -32, 0)
FOUNDRY_POOLS = [(-104, -76, 6), (-98, -44, 4)]   # bassins de lave (x, z, rayon) : le Java brûle qui s'y tient
EFFIGY_C = (-82, -58)
EFFIGY_R = 18
FOUNDRY_GATE = (-56, -56, -76, -66)               # barrière à l'est (l'Effigie l'ouvre)
YARD_B = (-55, -26, -82, -60, 0)
# Passerelle des cuves : axe z = DECK_Z + ondulation, de x = DECK_X0 à DECK_X1, trois cuves rondes.
DECK_X0, DECK_X1, DECK_Z, DECK_HALF = -30, 60, -71, 2
PODS = [(-6, -71, 7), (18, -73, 7), (41, -70, 7)]
BOILERS = (58, 92, -92, -54, 0)
BOILERS_GATE = (72, 78, -54, -54)                 # barrière au sud de la salle des chaudières (groupe 8 vaincu)
ARENA_BRIDGE = (72, 78, -53, -36)
ARENA_C = (75, -10)
ARENA_R = 26
PIT_C = (69, -15)                                 # creuset : bassin de lave muré au milieu de l'arène
PIT_R = 4
# Points de jeu
LAVA_POOL_H = (-14, 49, 4)
LAVA_POOL_G = (-72, 56, 4)

# Meutes (centre x, z) : leurs membres se placent autour (generate_molten_boss.PACKS).
PACK_CENTERS = [(-22, 42), (-86, 50), (-90, 20), (-86, -6)]
RESONATOR_1 = (-78, -10)
SHAMAN_AT = (-90, -4)
PROTECTOR_AT = (-82, -66)
RESONATOR_2 = (-70, -72)
EFFIGY_ADDS = [(-96, -64), (-70, -50), (-94, -48)]
GROUP_CENTERS = [(-40, -70), PODS[0][:2], PODS[1][:2], PODS[2][:2]]
CHECKPOINT_B = (-50, 0, -71)
CHECKPOINT_D = (75, 0, -62)
BRAHAM_END = (70, 0, -60)
ROX_END = (80, 0, -60)
REWARD_AT = (72, 0, -2)
END_EXIT_AT = (78, 0, -2)


def deck_z(x):
    """Axe de la passerelle : légère ondulation (Kevin n'aime pas les passages tout droits)."""
    return DECK_Z + round(1.5 * math.sin((x - DECK_X0) / 13.0))


# --- grille ----------------------------------------------------------------------------------------------------

class Terrain:
    """Cases praticables : debout (stand), genre (kind), zone (area)."""

    def __init__(self):
        self.stand = {}
        self.kind = {}
        self.area = {}
        self.lava = set()        # cases de lave à hauteur du sol (bassins)

    def put(self, x, z, s, kind, area):
        self.stand[(x, z)] = s
        self.kind[(x, z)] = kind
        self.area[(x, z)] = area

    def rect(self, x0, x1, z0, z1, s, kind, area, ragged=0.0, seed=0):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if ragged:
                    edge = min(x - x0, x1 - x, z - z0, z1 - z)
                    if edge < ragged * (fbm2(x, z, 5, 2, seed) + 1) / 2:
                        continue
                self.put(x, z, s, kind, area)

    def disc(self, cx, cz, r, s, kind, area):
        n = int(r) + 1
        for x in range(cx - n, cx + n + 1):
            for z in range(cz - n, cz + n + 1):
                if math.hypot(x - cx, z - cz) <= r + 0.3:
                    self.put(x, z, s, kind, area)

    def walkable(self, x, z):
        return (x, z) in self.stand and (x, z) not in self.lava


def layout():
    t = Terrain()
    # cours d'abord (bords rongés), puis ce qui s'y raccorde par-dessus
    t.rect(*YARD_H, "yard", "yard_h", ragged=3, seed=11)
    t.rect(*YARD_B, "yard", "yard_b", ragged=2.5, seed=13)
    t.rect(*CAMP, "hall", "camp")
    x0, x1, z0, z1 = RAMP
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            t.put(x, z, ramp_stand(z), "hall", "ramp")
    t.rect(*PASSAGE, "hall", "passage")
    t.rect(*WORKSHOP, "hall", "workshop")
    for z, a, b in PARTITIONS:
        for x in range(a, b + 1):
            for dz in (0, 1):
                t.stand.pop((x, z + dz), None)
    t.rect(*FOUNDRY, "hall", "foundry")
    t.rect(FOUNDRY_GATE[0] - 1, FOUNDRY_GATE[1] + 4, FOUNDRY_GATE[2], FOUNDRY_GATE[3], 0, "hall", "foundry")
    for x in range(DECK_X0, DECK_X1 + 1):
        zc = deck_z(x)
        for z in range(zc - DECK_HALF, zc + DECK_HALF + 1):
            t.put(x, z, 0, "deck", "deck")
    for k, (cx, cz, r) in enumerate(PODS):
        t.disc(cx, cz, r, 0, "deck", f"pod{k}")
    t.rect(*BOILERS, "hall", "boilers")
    t.rect(*ARENA_BRIDGE, 0, "deck", "arena_bridge")
    t.disc(*ARENA_C, ARENA_R, 0, "open", "arena")
    for cx, cz, r in FOUNDRY_POOLS + [LAVA_POOL_H, LAVA_POOL_G]:
        for x in range(cx - r - 1, cx + r + 2):
            for z in range(cz - r - 1, cz + r + 2):
                if math.hypot(x - cx, z - cz) <= r * (0.85 + 0.3 * (fbm2(x, z, 4, 1, cx) + 1) / 2) and (x, z) in t.stand:
                    t.lava.add((x, z))
    return t


def ramp_stand(z):
    """Rampe du départ : 10 au nord, 0 au sud, un demi-bloc par case."""
    return max(0.0, min(10.0, 10 - (z - RAMP[2]) * 0.5))


# --- pose ------------------------------------------------------------------------------------------------------

def depth_of(t, edge):
    def f(x, z):
        base = 4 if t.kind[(x, z)] in ("hall", "yard") else 2
        return base + min(26, edge[(x, z)] * 0.9) + 2 * fbm2(x, z, 6, 2, 31)
    return f


def floors(p, t):
    """Sol de chaque case : dalles dans les ateliers, cendre dans les cours, briques sur les passerelles, fissures
    incandescentes çà et là ; la rampe en demi-blocs."""
    for (x, z), s in t.stand.items():
        kind, area = t.kind[(x, z)], t.area[(x, z)]
        if area == "ramp":
            level = s
            base = math.floor(level)
            p.set(x, base - 1, z, pick(FLOOR, x, base - 1, z))
            if level - base >= 0.5:
                p.set(x, base, z, "Rock_Volcanic_Brick_Smooth_Half")
            continue
        s = int(s)
        if (x, z) in t.lava:
            p.fluid(x, s - 1, z, LAVA)
            p.set(x, s - 2, z, LAVA_CRACK)
            continue
        if kind == "yard":
            b = pick(YARD, x, s - 1, z)
        elif kind == "deck":
            b = pick(DECK, x, s - 1, z)
        elif area == "arena":
            b = arena_tile(x, z)
        elif fbm2(x, z, 7, 2, 5) > 0.45:
            b = pick(FLOOR_WORN, x, s - 1, z)
        else:
            b = pick(FLOOR, x, s - 1, z)
        if kind != "deck" and area != "arena" and hash01(x, z, 1, 77) < 0.012:
            b = GLOW
        p.set(x, s - 1, z, b)


def arena_tile(x, z):
    d = math.hypot(x - ARENA_C[0], z - ARENA_C[1])
    if abs(d - (ARENA_R - 1.5)) < 0.6 or abs(d - 12) < 0.5:
        return ARENA_RING
    if abs(d - 18) < 0.5 and hash01(x, z, 2, 79) < 0.6:
        return GLOW
    return pick(ARENA_TILE, x, -1, z)


def underside(p, t):
    """Dessous de l'île : roche volcanique, plus profonde loin des bords."""
    tops = {}
    for (x, z), s in t.stand.items():
        tops[(x, z)] = math.floor(s) - 1
    for x in range(CHANNEL[0], CHANNEL[1] + 1):
        for z in range(CHANNEL[2], CHANNEL[3] + 1):
            tops[(x, z)] = CHANNEL_LAVA_TOP - 2
    for z, a, b in PARTITIONS:
        for x in range(a, b + 1):
            for dz in (0, 1):
                tops[(x, z + dz)] = -1
    edge = fn.edge_distance(tops)
    fn.island(p, tops, depth_of_cells(tops, edge), seed=41, hang=0.0, theme=VOLCANIC)


def depth_of_cells(tops, edge):
    return lambda x, z: 3 + min(28, edge[(x, z)] * 0.9) + 2 * fbm2(x, z, 6, 2, 31)


def channel(p):
    """Canal de lave entre l'atelier et la fonderie : lave à deux blocs sous le sol, berges de basalte."""
    x0, x1, z0, z1 = CHANNEL
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            p.set(x, CHANNEL_LAVA_TOP - 1, z, LAVA_CRACK)
            p.fluid(x, CHANNEL_LAVA_TOP, z, LAVA)
            for y in range(CHANNEL_LAVA_TOP + 1, 0):
                if z in (z0, z1):
                    p.set(x, y, z, pick(WALL, x, y, z))


def bridge_cells():
    """Cases du pont du canal (le Java les pose quand la meute 4 tombe) : tablier et garde-corps."""
    x0, x1, z0, z1 = BRIDGE
    deck = [(x, -1, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)]
    rails = [(x, 0, z) for x in (x0, x1) for z in range(z0, z1 + 1)]
    return deck, rails


WALL_HEIGHT = {"hall": 7, "yard": 3}


def walls(p, t):
    """Murs au bord des ateliers et des cours (hauteur selon le genre), garde-corps sur les passerelles, rien autour de
    l'arène. Un mur ne se pose que sur une case hors du parcours ; piliers tous les sept blocs, faîte plat."""
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    cells = {}
    for (x, z), s in t.stand.items():
        kind = t.kind[(x, z)]
        if kind == "open":
            continue
        for dx, dz in sides + ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (x + dx, z + dz)
            if n in t.stand or in_channel(*n):
                continue
            h = WALL_HEIGHT.get(kind, 1)
            if t.area[(x, z)] == "camp" and n[0] >= CAMP[1]:
                h = 1                                  # surplomb : balustrade côté creuset (on voit l'arène)
            prev = cells.get(n)
            if prev is None or prev[1] < h:
                cells[n] = (int(math.floor(s)), h, kind)
    for (x, z), (s, h, kind) in cells.items():
        if kind == "deck" or h == 1:
            along_z = (x + 1, z) in t.stand or (x - 1, z) in t.stand
            p.set(x, s - 1, z, pick(DECK, x, s - 1, z))
            p.set(x, s, z, BARS if kind == "deck" else RAIL, 1 if along_z else 0)
            continue
        top = s + h
        if kind == "yard":
            top = s + h + int(2 * (fbm2(x, z, 4, 1, 17) + 1) / 2)
        pillar = (x + z) % 7 == 0 and kind == "hall"
        for y in range(s - 1, top):
            if pillar:
                b = PILLAR_BASE if y == s else PILLAR_MID
            elif kind == "yard":
                b = pick(ROCK, x, y, z)
            else:
                b = pick(WALL, x, y, z)
                if y == s + 4 and (x * 3 + z) % 11 == 0:
                    b = GLOW
            p.set(x, y, z, b)
        if kind == "hall":
            p.set(x, top, z, WALL_TOP)


def in_channel(x, z):
    x0, x1, z0, z1 = CHANNEL
    return x0 <= x <= x1 and z0 <= z <= z1


def partitions(p):
    for z, a, b in PARTITIONS:
        for x in range(a, b + 1):
            for dz in (0, 1):
                for y in range(-1, 7):
                    p.set(x, y, z + dz, PILLAR_MID if x % 6 == 0 else pick(WALL, x, y, z + dz))
                p.set(x, 7, z + dz, WALL_TOP)


def gate(p, box, s=0, height=5):
    x0, x1, z0, z1 = box
    cells = []
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(s, s + height):
                p.set(x, y, z, BARRIER)
                cells.append((x, y, z))
    return cells


def pools(p, t):
    """Margelle d'un bloc autour des bassins de lave (on ne tombe pas dedans par mégarde ; le Java brûle quand même)."""
    for (x, z) in t.lava:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in t.stand and n not in t.lava and fn.free(p, n[0], 0, n[1]):
                p.set(n[0], 0, n[1], "Rock_Volcanic_Brick_Smooth_Half")


def arena(p, t):
    """La plate-forme du creuset : creuset muré au centre, cercle de braseros autour (hors du bord : la tempête doit
    pouvoir jeter dans le vide), chaînes qui pendent des pylônes de l'extérieur."""
    cx, cz = PIT_C
    for x in range(cx - PIT_R - 2, cx + PIT_R + 3):
        for z in range(cz - PIT_R - 2, cz + PIT_R + 3):
            d = math.hypot(x - cx, z - cz)
            if d <= PIT_R + 0.3:
                p.fluid(x, -1, z, LAVA)
                p.set(x, -2, z, LAVA_CRACK)
            elif d <= PIT_R + 1.3:
                p.set(x, 0, z, "Rock_Volcanic_Brick_Wall")
                p.set(x, -1, z, ARENA_RING)
    # pylônes sur de petits îlots, hors de l'arène (ils ne retiennent personne)
    for k in range(6):
        a = k * math.pi / 3 + 0.4
        px = round(ARENA_C[0] + math.cos(a) * (ARENA_R + 7))
        pz = round(ARENA_C[1] + math.sin(a) * (ARENA_R + 7))
        if px <= ARENA_BRIDGE[1] + 3 and px >= ARENA_BRIDGE[0] - 3 and pz < ARENA_C[1]:
            continue
        for y in range(-6, 12):
            p.set(px, y, pz, PILLAR_MID if y > -6 else PILLAR_BASE)
        p.set(px, 12, pz, BRAZIER)
        for y in range(-10, -6):
            p.set(px, y, pz, pick(ROCK, px, y, pz))


def camp(p):
    """Surplomb du départ : braseros aux coins, caisses ; un regard sur le creuset à l'est."""
    x0, x1, z0, z1, s = CAMP
    for x, z in ((x0 + 1, z0 + 1), (x0 + 1, z1 - 1), (x1 - 1, z0 + 1)):
        p.set(x, s, z, BRAZIER)
    for k, (x, z) in enumerate(((x0 + 3, z0 + 1), (x0 + 4, z0 + 1), (x0 + 1, z0 + 4))):
        p.set(x, s, z, PROPS[k % len(PROPS)])


def workshop(p, t):
    """L'atelier : rails et wagonnets, piles de fer, minerai, chaînes qui pendent des poutres, braseros contre les murs.
    Rien au milieu des travées (on s'y bat)."""
    x0, x1, z0, z1, s = WORKSHOP
    # rails le long des travées (x), côté mur
    for zr in (60, 28, -14):
        for x in range(x0 + 2, x1 - 1):
            if t.walkable(x, zr) and fn.free(p, x, 0, zr):
                p.set(x, 0, zr, "Rail")
        p.set(x0 + 6, 0, zr, "Rail_Kart") if fn.free(p, x0 + 6, 1, zr) else None
    # poutres en travers (hautes) et chaînes
    for x in range(x0 + 4, x1, 10):
        for z in range(z0, z1 + 1):
            if (x, z) in t.stand:
                p.set(x, 8, z, BEAM)
        for z in range(z0 + 3, z1, 9):
            if (x, z) in t.stand:
                for y in range(5, 8):
                    p.set(x, y, z, CHAINS)
    props_along_walls(p, t, "workshop", 0.07, 61)


def props_along_walls(p, t, area, rate, seed):
    for (x, z), s in sorted(t.stand.items()):
        if t.area[(x, z)] != area or (x, z) in t.lava:
            continue
        s = int(s)
        if not fn.free(p, x, s, z):
            continue
        against = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) not in t.stand)
        if against != 1:
            continue
        h = hash01(x, z, 3, seed)
        if h < rate * 0.25:
            p.set(x, s, z, BRAZIER)
        elif h < rate:
            p.set(x, s, z, PROPS[int(h * 1000) % len(PROPS)])
            if hash01(z, x, 4, seed) < 0.3 and fn.free(p, x, s + 1, z):
                p.set(x, s + 1, z, PROPS[int(h * 10000) % len(PROPS)])
        elif h < rate * 1.5:
            p.set(x, s, z, ORE[int(h * 1000) % len(ORE)])


def foundry(p, t):
    """La fonderie : cuves de fonte (cylindres de briques à la lave), pilier-cheminées, braseros ; l'Effigie au milieu
    sur un cercle de dalles ornées."""
    cx, cz = EFFIGY_C
    for x in range(cx - 4, cx + 5):
        for z in range(cz - 4, cz + 5):
            if abs(math.hypot(x - cx, z - cz) - 3.5) < 0.6:
                p.set(x, -1, z, ARENA_RING)
    for vx, vz in ((-108, -56), (-62, -40), (-62, -80), (-108, -36)):
        crucible(p, vx, vz)
    for x, z in ((-110, -82), (-58, -82), (-110, -34), (-58, -34)):
        for y in range(0, 12):
            p.set(x, y, z, PILLAR_MID if y else PILLAR_BASE)
        p.set(x, 12, z, BRAZIER)
    props_along_walls(p, t, "foundry", 0.05, 63)


def crucible(p, cx, cz, r=2):
    """Cuve de fonte : anneau de briques de 3 blocs de haut, lave dedans, fissures incandescentes."""
    for x in range(cx - r - 1, cx + r + 2):
        for z in range(cz - r - 1, cz + r + 2):
            d = math.hypot(x - cx, z - cz)
            if d <= r - 0.4:
                p.fluid(x, 2, z, LAVA)
                p.set(x, 1, z, LAVA_CRACK)
                p.set(x, 0, z, LAVA_CRACK)
            elif d <= r + 0.7:
                for y in range(0, 3):
                    p.set(x, y, z, GLOW if y == 1 and (x + z) % 3 == 0 else pick(WALL, x, y, z))
                p.set(x, 3, z, "Rock_Volcanic_Brick_Half")


def boilers(p, t):
    x0, x1, z0, z1, s = BOILERS
    for vx, vz in ((x0 + 5, z0 + 5), (x1 - 5, z0 + 5), (x0 + 5, z1 - 8), (x1 - 5, z1 - 8)):
        crucible(p, vx, vz)
    props_along_walls(p, t, "boilers", 0.06, 65)


def yards(p, t):
    """Cours : tas de scories (rochers), arbres calcinés au pied des murs, herbes sèches."""
    cells = [(x, int(s) - 1, z) for (x, z), s in t.stand.items()
             if t.kind[(x, z)] == "yard" and (x, z) not in t.lava and not near_pack(x, z)]
    fn.dress(p, cells, VOLCANIC, seed=71, trees=0.01, spacing=9, bushes=0.03, boulders=0.004, density=0.25,
             flowers=0.0)


def near_pack(x, z):
    return any(math.hypot(x - a, z - b) < 6 for a, b in PACK_CENTERS + GROUP_CENTERS)


def deck(p, t):
    """Passerelle des cuves : poutres sous le tablier, pylône de chaînes au bord de chaque cuve, brasero au centre."""
    for x in range(DECK_X0, DECK_X1 + 1, 6):
        zc = deck_z(x)
        for z in range(zc - DECK_HALF - 1, zc + DECK_HALF + 2):
            p.set(x, -2, z, BEAM)
    for k, (cx, cz, r) in enumerate(PODS):
        for a in (0.8, 0.8 + math.pi):
            x, z = round(cx + math.cos(a) * (r - 1)), round(cz + math.sin(a) * (r - 1))
            for y in range(0, 6):
                p.set(x, y, z, PILLAR_MID if y else PILLAR_BASE)
            p.set(x, 6, z, BRAZIER)
        for y in range(-1, -6, -1):
            for x in range(cx - 2, cx + 3):
                for z in range(cz - 2, cz + 3):
                    if math.hypot(x - cx, z - cz) <= 2.2 + y * 0.3:
                        p.set(x, y, z, pick(WALL, x, y, z))


def lights(p, t):
    """Torches au pied des murs des ateliers, tous les dix blocs environ."""
    for (x, z), s in t.stand.items():
        if t.kind[(x, z)] != "hall" or t.area[(x, z)] == "ramp":
            continue
        s = int(s)
        if not fn.free(p, x, s, z) or hash01(x, z, 9, 81) > 0.05:
            continue
        if sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) not in t.stand) == 1:
            p.set(x, s, z, TORCH)


def islets(p):
    fn.scatter_islets(p, (-170, 150, -150, 120), 14, (-40, 20), (3, 7), VOLCANIC, seed=91, margin=16)


# --- contrôle --------------------------------------------------------------------------------------------------

def components(t, extra=()):
    cells = set(c for c in t.stand if c not in t.lava) | set(extra)
    label, n = {}, 0
    for c in cells:
        if c in label:
            continue
        n += 1
        q = deque([c])
        label[c] = n
        while q:
            x, z = q.popleft()
            for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (x + dx, z + dz)
                if m in cells and m not in label:
                    label[m] = n
                    q.append(m)
    return label


def check(t, p):
    """Le parcours se fait d'un seul tenant une fois le pont posé ; sans lui, le canal coupe ; rien de plein sur les
    points de jeu."""
    deck_cells, _ = bridge_cells()
    bridge = {(x, z) for x, _, z in deck_cells} | {(x, z) for x in range(BRIDGE[0] + 1, BRIDGE[1])
                                                    for z in range(BRIDGE[2], BRIDGE[3] + 1)}
    full = components(t, bridge)
    pts = [SPAWN[::2], PACK_CENTERS[0], PACK_CENTERS[3], EFFIGY_C, GROUP_CENTERS[0], PODS[2][:2], CHECKPOINT_D[::2],
           ARENA_C]
    labels = {full[(round(x), round(z))] for x, z in pts}
    assert len(labels) == 1, f"parcours coupé : {labels}"
    cut = components(t)
    assert cut[PACK_CENTERS[3]] != cut[EFFIGY_C], "le canal ne coupe pas l'atelier de la fonderie"
    for x, s, z in (SPAWN, BRAHAM_AT, ROX_AT, CHECKPOINT_B, CHECKPOINT_D, BRAHAM_END, ROX_END, REWARD_AT, END_EXIT_AT):
        for y in (s, s + 1):
            name = p.blocks.get((x, y, z), (AIR,))[0]
            assert name == AIR, f"{name} sur le point {(x, s, z)}"


def build_all():
    p = go.Prefab()
    t = layout()
    floors(p, t)
    channel(p)
    walls(p, t)
    partitions(p)
    pools(p, t)
    arena(p, t)
    camp(p)
    workshop(p, t)
    foundry(p, t)
    boilers(p, t)
    deck(p, t)
    yards(p, t)
    lights(p, t)
    gates = {"foundry": gate(p, FOUNDRY_GATE), "boilers": gate(p, BOILERS_GATE)}
    underside(p, t)
    islets(p)
    check(t, p)
    t.gates = gates
    t.bridge = bridge_cells()
    return p, t
