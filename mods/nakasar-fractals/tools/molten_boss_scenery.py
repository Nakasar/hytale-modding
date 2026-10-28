"""Carte et décor de la Fonderie en fusion (Molten Boss, GW2), d'après le guide Hardstuck, la carte que Kevin a
envoyée et ses captures de GW2 (28 octobre 2026).

La Fonderie de l'Alliance en fusion (Légion de la Flamme et Draguerre) est creusée sous un volcan : une immense caverne
fermée par une voûte bosselée d'où pendent des stalactites, aux parois semées de cristaux bleus, où des chutes de lave
tombent dans une mer de lave au fond du gouffre. On la parcourt comme sur la carte de GW2, en descendant :

- le surplomb du départ (Braham et Rox), haut sur la paroi (debout à 16), au bord du grand gouffre ; une rampe de
  roche descend vers le sud dans la grotte des scories (debout à 6, meute 1) ;
- une galerie descend vers l'ouest jusqu'à l'atelier (debout à 0) : trois travées (meutes 2 et 3), la travée nord
  (meute 4 : gardien résonateur et chaman de la flamme d'élite) ; au nord, un canal de lave que le pont franchit
  quand la meute 4 tombe ;
- la fonderie du nord-ouest et ses bassins de lave : l'Effigie en fusion, son Protecteur, un second gardien ;
- la grotte des wagonnets (groupe 5), puis la passerelle des cuves : un tablier de dalles sombres à garde-corps de
  fer, suspendu à la voûte par des chaînes au-dessus du gouffre, qui descend par paliers (trois cuves rondes, groupes
  6 à 8, à 3, 6 et 9 blocs sous la grotte) ;
- la salle des chaudières (debout à -10, point de retour) ; un pont descend au sud vers la plate-forme ronde du
  creuset (debout à -14), pendue à six chaînes au-dessus du gouffre : le Berserker et la Tempête de feu en fusion.

Qui tombe dans le gouffre finit dans la mer de lave : le Java le brûle puis le ramène au dernier point de retour.

Repère : x vers l'est, z vers le sud, y monde = GROUND_Y + y prefab. « debout à s » : le sol est en s - 1 (un
demi-bloc par-dessus quand s a une demie). Rien n'est tiré au hasard sans graine : un prefab régénéré est identique.
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
CAVE_FLOOR = ["Soil_Ash", "Rock_Volcanic", "Rock_Volcanic_Cobble", "Soil_Ash", "Rock_Magma_Cooled", "Soil_Dirt_Burnt"]
DECK = ["Rock_Basalt_Brick_Smooth", "Rock_Basalt_Brick_Smooth", "Rock_Basalt_Brick"]
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
BARS = "Deco_Iron_Bars"                         # garde-corps de fer grillagé (même rotation)
ROCK = ["Rock_Volcanic", "Rock_Basalt", "Rock_Volcanic", "Rock_Magma_Cooled", "Rock_Slate"]
CHAINS = "Deco_Iron_Chains_Vertical"
BRAZIER = "Furniture_Crude_Brazier"
TORCH = "Furniture_Crude_Torch"
PROPS = ["Furniture_Ancient_Crate", "Furniture_Ancient_Barrel", "Furniture_Village_Crate", "Deco_Iron_Stack"]
ORE = ["Ore_Iron_Volcanic", "Ore_Iron_Basalt", "Ore_Iron_Basalt_Cracked"]
CRYSTAL_BLOCK = "Rock_Crystal_Blue_Block"
CRYSTALS = ["Rock_Crystal_Blue_Large", "Rock_Crystal_Blue_Medium", "Rock_Crystal_Blue_Small", "Rock_Crystal_Cyan_Medium"]
STALACTITES = ["Rock_Volcanic_Stalactite_Large", "Rock_Volcanic_Stalactite_Small", "Rock_Basalt_Stalactite_Large"]
HALF = {"cave": "Rock_Volcanic_Half", "hall": "Rock_Volcanic_Brick_Smooth_Half", "deck": "Rock_Basalt_Brick_Smooth_Half"}
BARRIER = "Nakasar_Fractal_Mist_Barrier"          # barrière de brume de la Falaise
VOLCANIC = fn.THEMES["volcanic"]

# --- hauteurs -----------------------------------------------------------------------------------------------------
CAMP_S = 16
CAVE_S = 6
FLOOR_S = 0
POD_S = [-3, -6, -9]
BOILERS_S = -10
ARENA_S = -14
LAVA_SEA = -34                                   # surface de la mer de lave, au fond du gouffre
ABYSS_S = -24                                    # pieds sous ce niveau : tombé dans le gouffre (le Java ramène)
CEILING = 30                                     # voûte : hauteur moyenne (bosselée de +- 8)
SHELL = 3                                        # épaisseur des parois et de la voûte
BBOX = (-132, 122, -108, 80)                     # étendue de la caverne (x0, x1, z0, z1)
CHASM_ZONES = [(-9, 52, -60, 24)]                # grand gouffre central, sous le surplomb du départ
CHASM_REACH = 14                                 # vide autour de la passerelle et de la plate-forme

# --- la carte (x0, x1, z0, z1, debout) -------------------------------------------------------------------------
# Genres : "hall" (salles bâties : dalles et parement de briques), "cave" (grotte : sol de cendre et de roche, parois
# naturelles), "deck" (passerelle suspendue, garde-corps de fer), "open" (bord sur le vide, sans rien : l'arène).
CAMP = (-36, -6, -14, 8, CAMP_S)
SPAWN = (-21, CAMP_S, -2)
BRAHAM_AT = (-25, CAMP_S, -9)
ROX_AT = (-17, CAMP_S, -9)
RAMP = (-30, -22, 9, 33)                          # x0, x1, z0, z1 : de debout 16 (nord) à 6 (sud)
YARD_H = (-42, -4, 29, 58, CAVE_S)
PASSAGE = (-62, -37, 38, 50)                      # galerie : de debout 6 (est) à 0 (ouest)
WORKSHOP = (-112, -62, -18, 64, FLOOR_S)
# Cloisons de l'atelier : (z, x0, x1) murs pleins, la baie libre est le reste de la largeur.
PARTITIONS = [(33, -97, -62), (7, -112, -77)]
CHANNEL = (-114, -60, -31, -19)                   # canal de lave (x0, x1, z0, z1)
CHANNEL_LAVA_TOP = -2                             # surface de la lave (bloc d'air rempli de lave), deux blocs sous le sol
BRIDGE = (-90, -84, -31, -19)                     # pont posé par le Java (meute 4 vaincue)
FOUNDRY = (-114, -56, -84, -32, FLOOR_S)
FOUNDRY_POOLS = [(-104, -76, 6), (-98, -44, 4)]   # bassins de lave (x, z, rayon) : le Java brûle qui s'y tient
EFFIGY_C = (-82, -58)
EFFIGY_R = 18
FOUNDRY_GATE = (-56, -56, -76, -66)               # barrière à l'est (l'Effigie l'ouvre)
YARD_B = (-55, -26, -82, -60, FLOOR_S)
# Passerelle des cuves : axe z = DECK_Z + ondulation, de x = DECK_X0 à DECK_X1, trois cuves rondes à POD_S.
DECK_X0, DECK_X1, DECK_Z, DECK_HALF = -30, 60, -71, 2
PODS = [(-6, -71, 7), (18, -73, 7), (41, -70, 7)]
# Paliers de la passerelle (x, debout) : on descend entre les cuves, à plat sur chacune.
DECK_PROFILE = [(-27, FLOOR_S), (-14, POD_S[0]), (1, POD_S[0]), (10, POD_S[1]), (26, POD_S[1]), (33, POD_S[2]),
                (49, POD_S[2]), (57, BOILERS_S)]
BOILERS = (58, 92, -92, -54, BOILERS_S)
BOILERS_GATE = (72, 78, -54, -54)                 # barrière au sud de la salle des chaudières (groupe 8 vaincu)
ARENA_BRIDGE = (72, 78, -53, -36)                 # de debout -10 (nord) à -14 (sud)
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
CHECKPOINT_B = (-50, FLOOR_S, -71)
CHECKPOINT_D = (75, BOILERS_S, -62)
BRAHAM_END = (70, BOILERS_S, -60)
ROX_END = (80, BOILERS_S, -60)
REWARD_AT = (72, ARENA_S, -2)
END_EXIT_AT = (78, ARENA_S, -2)


def deck_z(x):
    """Axe de la passerelle : légère ondulation (Kevin n'aime pas les passages tout droits)."""
    return DECK_Z + round(1.5 * math.sin((x - DECK_X0) / 13.0))


def deck_stand(x):
    """Debout sur la passerelle en x : paliers de DECK_PROFILE, pente d'un demi-bloc au plus par case."""
    pts = DECK_PROFILE
    if x <= pts[0][0]:
        return float(pts[0][1])
    for (xa, sa), (xb, sb) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return half(sa + (sb - sa) * (x - xa) / (xb - xa))
    return float(pts[-1][1])


def half(v):
    """Arrondi au demi-bloc (vers le bas)."""
    return math.floor(v * 2) / 2


def ramp_stand(z):
    """Rampe du départ : 16 au nord, 6 au sud, un demi-bloc par case."""
    return max(float(CAVE_S), min(float(CAMP_S), CAMP_S - (z - RAMP[2]) * 0.5))


def passage_stand(x):
    """Galerie vers l'atelier : 6 à l'est, 0 à l'ouest, un demi-bloc toutes les deux cases."""
    return max(float(FLOOR_S), min(float(CAVE_S), half(CAVE_S - (PASSAGE[1] - x) * 0.25)))


def bridge_stand(z):
    """Pont du creuset : -10 au nord, -14 au sud."""
    return max(float(ARENA_S), half(BOILERS_S - (z - ARENA_BRIDGE[2]) * 0.25))


# --- grille ----------------------------------------------------------------------------------------------------

class Terrain:
    """Cases praticables : debout (stand), genre (kind), zone (area) ; gouffre, voûte."""

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

    def stand_at(self, x, z):
        """Debout en (x, z), ou celui de la case praticable la plus proche (points posés au bord)."""
        if (x, z) in self.stand:
            return self.stand[(x, z)]
        best = min(self.stand, key=lambda c: (c[0] - x) ** 2 + (c[1] - z) ** 2)
        return self.stand[best]


def layout():
    t = Terrain()
    # grottes d'abord (bords rongés), puis ce qui s'y raccorde par-dessus
    t.rect(*YARD_H, "cave", "yard_h", ragged=3, seed=11)
    t.rect(*YARD_B, "cave", "yard_b", ragged=2.5, seed=13)
    t.rect(*CAMP, "hall", "camp")
    x0, x1, z0, z1 = RAMP
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            t.put(x, z, ramp_stand(z), "cave", "ramp")
    x0, x1, z0, z1 = PASSAGE
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            t.put(x, z, passage_stand(x), "cave", "passage")
    t.rect(*WORKSHOP, "hall", "workshop")
    for z, a, b in PARTITIONS:
        for x in range(a, b + 1):
            for dz in (0, 1):
                t.stand.pop((x, z + dz), None)
    t.rect(*FOUNDRY, "hall", "foundry")
    t.rect(FOUNDRY_GATE[0] - 1, FOUNDRY_GATE[1] + 4, FOUNDRY_GATE[2], FOUNDRY_GATE[3], FLOOR_S, "hall", "foundry")
    for x in range(DECK_X0, DECK_X1 + 1):
        zc = deck_z(x)
        for z in range(zc - DECK_HALF, zc + DECK_HALF + 1):
            t.put(x, z, deck_stand(x), "deck", "deck")
    for k, (cx, cz, r) in enumerate(PODS):
        t.disc(cx, cz, r, POD_S[k], "deck", f"pod{k}")
    t.rect(*BOILERS, "hall", "boilers")
    x0, x1, z0, z1 = ARENA_BRIDGE
    for z in range(z0, z1 + 1):
        for x in range(x0, x1 + 1):
            t.put(x, z, bridge_stand(z), "deck", "arena_bridge")
    t.disc(*ARENA_C, ARENA_R, ARENA_S, "open", "arena")
    for cx, cz, r in FOUNDRY_POOLS + [LAVA_POOL_H, LAVA_POOL_G]:
        for x in range(cx - r - 1, cx + r + 2):
            for z in range(cz - r - 1, cz + r + 2):
                if math.hypot(x - cx, z - cz) <= r * (0.85 + 0.3 * (fbm2(x, z, 4, 1, cx) + 1) / 2) and (x, z) in t.stand:
                    t.lava.add((x, z))
    classify(t)
    return t


def in_channel(x, z):
    x0, x1, z0, z1 = CHANNEL
    return x0 <= x <= x1 and z0 <= z <= z1


def in_partition(x, z):
    return any(a <= x <= b and zp <= z <= zp + 1 for zp, a, b in PARTITIONS)


def bfs(sources, cells, limit):
    """Distance (pas de 8 voisins) depuis `sources`, dans `cells`, jusqu'à `limit`."""
    dist = {c: 0 for c in sources}
    q = deque(sources)
    while q:
        c = q.popleft()
        d = dist[c]
        if d >= limit:
            continue
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                n = (c[0] + dx, c[1] + dz)
                if n in cells and n not in dist:
                    dist[n] = d + 1
                    q.append(n)
    return dist


def classify(t):
    """Chaque colonne de la caverne : sol praticable, gouffre (vide jusqu'à la mer de lave), canal, cloison, ou paroi
    (roche pleine, seule sa peau de SHELL blocs est posée)."""
    x0, x1, z0, z1 = BBOX
    every = {(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)}
    air = [c for c in t.stand if t.kind[c] in ("deck", "open")]
    near_air = bfs(air, every, CHASM_REACH)
    t.chasm = set()
    for x, z in every:
        if (x, z) in t.stand or in_channel(x, z) or in_partition(x, z):
            continue
        noisy = CHASM_REACH * (0.75 + 0.25 * fbm2(x, z, 9, 2, 43))
        if (x, z) in near_air and near_air[(x, z)] <= noisy or any(
                min(x - a, b - x, z - c, d - z) >= 6 * (fbm2(x, z, 7, 2, 44) + 1) / 2 - 1 for a, b, c, d in CHASM_ZONES):
            t.chasm.add((x, z))
    t.open = set(t.stand) | t.chasm | {c for c in every if in_channel(*c) or in_partition(*c)}
    t.wall = every - t.open
    t.shell = bfs([c for c in t.open], every, SHELL)
    t.near_chasm = bfs(list(t.chasm) + [c for c in every if in_channel(*c)], every, 2)


def ceiling(x, z):
    """Dessous de la voûte en (x, z) : bosselée, toujours à 12 blocs au moins au-dessus du surplomb."""
    return int(round(max(CEILING + 8 * fbm2(x, z, 22, 3, 81), CAMP_S + 12)))


# --- pose ------------------------------------------------------------------------------------------------------

def cave(p, t):
    """La caverne : peau des parois (de sous la mer de lave à la voûte), voûte au-dessus du vide et des salles, sol
    plein sous les salles et les grottes (jusqu'à la lave au bord du gouffre), mer de lave au fond."""
    for (x, z), d in t.shell.items():
        c = ceiling(x, z)
        if (x, z) in t.wall:
            if d == 0:
                continue
            for y in range(LAVA_SEA - 3, c + SHELL + 2):
                p.set(x, y, z, pick(ROCK, x, y, z))
            continue
        top = max(ceiling(x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)) + SHELL
        for y in range(c, top):
            p.set(x, y, z, pick(ROCK, x, y, z))
        if (x, z) in t.chasm:
            p.fluid(x, LAVA_SEA, z, LAVA)
            for y in range(LAVA_SEA - 3, LAVA_SEA):
                p.set(x, y, z, LAVA_CRACK if y == LAVA_SEA - 1 else pick(ROCK, x, y, z))
        elif (x, z) in t.stand and t.kind[(x, z)] in ("cave", "hall"):
            s = math.floor(t.stand[(x, z)])
            bottom = LAVA_SEA - 3 if (x, z) in t.near_chasm else s - 5
            for y in range(bottom, s - 1):
                p.set(x, y, z, pick(ROCK, x, y, z))


def floors(p, t):
    """Sol de chaque case : dalles dans les salles, cendre et roche dans les grottes, dalles sombres sur les
    passerelles, fissures incandescentes çà et là ; les pentes en demi-blocs."""
    for (x, z), level in t.stand.items():
        kind, area = t.kind[(x, z)], t.area[(x, z)]
        s = math.floor(level)
        if (x, z) in t.lava:
            p.fluid(x, s - 1, z, LAVA)
            p.set(x, s - 2, z, LAVA_CRACK)
            continue
        if kind == "cave":
            b = pick(CAVE_FLOOR, x, s - 1, z)
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
        if level - s >= 0.5:
            p.set(x, s, z, HALF.get(kind, HALF["hall"]))


def arena_tile(x, z):
    d = math.hypot(x - ARENA_C[0], z - ARENA_C[1])
    if abs(d - (ARENA_R - 1.5)) < 0.6 or abs(d - 12) < 0.5:
        return ARENA_RING
    if abs(d - 18) < 0.5 and hash01(x, z, 2, 79) < 0.6:
        return GLOW
    return pick(ARENA_TILE, x, -1, z)


def channel(p):
    """Canal de lave entre l'atelier et la fonderie : lave à deux blocs sous le sol, berges de basalte."""
    x0, x1, z0, z1 = CHANNEL
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(CHANNEL_LAVA_TOP - 5, CHANNEL_LAVA_TOP - 1):
                p.set(x, y, z, pick(ROCK, x, y, z))
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


def walls(p, t):
    """Contre une salle bâtie, la paroi reçoit un parement de briques sur 7 blocs (piliers tous les sept, faîte
    plat) ; au bord du gouffre, garde-corps de fer (passerelles), balustrade (salles) ou muret de roche (grottes) ;
    rien autour de l'arène (le vent de la Tempête doit pouvoir jeter dans le vide)."""
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    cells = {}
    for (x, z), level in t.stand.items():
        kind = t.kind[(x, z)]
        if kind == "open":
            continue
        for dx, dz in sides + ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (x + dx, z + dz)
            if n in t.stand or in_channel(*n) or in_partition(*n):
                continue
            s = math.floor(level)
            prev = cells.get(n)
            if prev is None or prev[0] < s:
                cells[n] = (s, kind)
    for (x, z), (s, kind) in cells.items():
        if (x, z) in t.chasm:
            along_z = (x + 1, z) in t.stand or (x - 1, z) in t.stand
            if kind == "cave":
                p.set(x, s - 1, z, pick(ROCK, x, s - 1, z))
                p.set(x, s, z, pick(ROCK, x, s, z))
            else:
                p.set(x, s - 1, z, pick(DECK, x, s - 1, z))
                p.set(x, s, z, BARS if kind == "deck" else RAIL, 1 if along_z else 0)
            continue
        if kind != "hall":
            continue
        pillar = (x + z) % 7 == 0
        for y in range(s - 1, s + 7):
            if pillar:
                b = PILLAR_BASE if y == s else PILLAR_MID
            else:
                b = pick(WALL, x, y, z)
                if y == s + 4 and (x * 3 + z) % 11 == 0:
                    b = GLOW
            p.set(x, y, z, b)
        p.set(x, s + 7, z, WALL_TOP)


def partitions(p):
    for z, a, b in PARTITIONS:
        for x in range(a, b + 1):
            for dz in (0, 1):
                for y in range(-5, 7):
                    p.set(x, y, z + dz, PILLAR_MID if x % 6 == 0 and y >= 0 else pick(WALL, x, y, z + dz))
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
    """Margelle d'un demi-bloc autour des bassins de lave (on ne tombe pas dedans par mégarde ; le Java brûle quand
    même)."""
    for (x, z) in t.lava:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in t.stand and n not in t.lava:
                s = math.floor(t.stand[n])
                if fn.free(p, n[0], s, n[1]):
                    p.set(n[0], s, n[1], "Rock_Volcanic_Brick_Smooth_Half")


def chain(p, x, z, y0, y1):
    for y in range(y0, y1):
        p.set(x, y, z, CHAINS)


def arena(p, t):
    """La plate-forme du creuset : creuset muré au centre, dalle épaisse au dessous en cône ; six chaînes la pendent
    à la voûte, ancrées sur des corbeaux hors du bord (ils ne retiennent personne)."""
    cx, cz = PIT_C
    s = ARENA_S
    for x in range(cx - PIT_R - 2, cx + PIT_R + 3):
        for z in range(cz - PIT_R - 2, cz + PIT_R + 3):
            d = math.hypot(x - cx, z - cz)
            if d <= PIT_R + 0.3:
                p.fluid(x, s - 1, z, LAVA)
                p.set(x, s - 2, z, LAVA_CRACK)
            elif d <= PIT_R + 1.3:
                p.set(x, s, z, "Rock_Volcanic_Brick_Wall")
                p.set(x, s - 1, z, ARENA_RING)
    ax, az = ARENA_C
    for x in range(ax - ARENA_R - 1, ax + ARENA_R + 2):
        for z in range(az - ARENA_R - 1, az + ARENA_R + 2):
            d = math.hypot(x - ax, z - az)
            if d > ARENA_R + 0.3:
                continue
            depth = 2 + int(10 * (1 - (d / (ARENA_R + 0.3)) ** 1.5) * (0.8 + 0.2 * fbm2(x, z, 5, 2, 47)))
            for y in range(s - 1 - depth, s - 1):
                if (x, y, z) not in p.blocks:
                    p.set(x, y, z, pick(WALL if y > s - 4 else ROCK, x, y, z))
    for k in range(6):
        a = k * math.pi / 3 + 0.4
        px = round(ax + math.cos(a) * (ARENA_R + 1.5))
        pz = round(az + math.sin(a) * (ARENA_R + 1.5))
        if ARENA_BRIDGE[0] - 3 <= px <= ARENA_BRIDGE[1] + 3 and pz < az:
            continue
        for y in range(s - 3, s):
            p.set(px, y, pz, PILLAR_MID)
        p.set(px, s, pz, BRAZIER)
        chain(p, px, pz, s + 1, ceiling(px, pz))


def camp(p):
    """Surplomb du départ : braseros aux coins, caisses ; on voit d'en haut le gouffre, la passerelle et le creuset."""
    x0, x1, z0, z1, s = CAMP
    for x, z in ((x0 + 1, z0 + 1), (x0 + 1, z1 - 1), (x1 - 1, z0 + 1)):
        p.set(x, s, z, BRAZIER)
    for k, (x, z) in enumerate(((x0 + 3, z0 + 1), (x0 + 4, z0 + 1), (x0 + 1, z0 + 4))):
        p.set(x, s, z, PROPS[k % len(PROPS)])


def workshop(p, t):
    """L'atelier : rails et wagonnets, piles de fer, minerai, chaînes qui pendent des poutres, braseros contre les murs.
    Rien au milieu des travées (on s'y bat)."""
    x0, x1, z0, z1, s = WORKSHOP
    for zr in (60, 28, -14):
        for x in range(x0 + 2, x1 - 1):
            if t.walkable(x, zr) and fn.free(p, x, 0, zr):
                p.set(x, 0, zr, "Rail")
        p.set(x0 + 6, 0, zr, "Rail_Kart") if fn.free(p, x0 + 6, 1, zr) else None
    for x in range(x0 + 4, x1, 10):
        for z in range(z0, z1 + 1):
            if (x, z) in t.stand:
                p.set(x, 8, z, BEAM)
        for z in range(z0 + 3, z1, 9):
            if (x, z) in t.stand:
                chain(p, x, z, 5, 8)
                chain(p, x, z, 9, ceiling(x, z))
    props_along_walls(p, t, "workshop", 0.07, 61)


def props_along_walls(p, t, area, rate, seed):
    for (x, z), level in sorted(t.stand.items()):
        if t.area[(x, z)] != area or (x, z) in t.lava:
            continue
        s = math.floor(level)
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
        crucible(p, vx, vz, FLOOR_S)
    for x, z in ((-110, -82), (-58, -82), (-110, -34), (-58, -34)):
        for y in range(0, 12):
            p.set(x, y, z, PILLAR_MID if y else PILLAR_BASE)
        p.set(x, 12, z, BRAZIER)
    props_along_walls(p, t, "foundry", 0.05, 63)


def crucible(p, cx, cz, s, r=2):
    """Cuve de fonte : anneau de briques de 3 blocs de haut, lave dedans, fissures incandescentes."""
    for x in range(cx - r - 1, cx + r + 2):
        for z in range(cz - r - 1, cz + r + 2):
            d = math.hypot(x - cx, z - cz)
            if d <= r - 0.4:
                p.fluid(x, s + 2, z, LAVA)
                p.set(x, s + 1, z, LAVA_CRACK)
                p.set(x, s, z, LAVA_CRACK)
            elif d <= r + 0.7:
                for y in range(s, s + 3):
                    p.set(x, y, z, GLOW if y == s + 1 and (x + z) % 3 == 0 else pick(WALL, x, y, z))
                p.set(x, s + 3, z, "Rock_Volcanic_Brick_Half")


def boilers(p, t):
    x0, x1, z0, z1, s = BOILERS
    for vx, vz in ((x0 + 5, z0 + 5), (x1 - 5, z0 + 5), (x0 + 5, z1 - 8), (x1 - 5, z1 - 8)):
        crucible(p, vx, vz, s)
    props_along_walls(p, t, "boilers", 0.06, 65)


def caves(p, t):
    """Grottes : tas de scories (rochers), arbres calcinés au pied des parois, herbes sèches ; grappes de cristaux
    bleus contre les parois (captures de GW2)."""
    cells = [(x, math.floor(s) - 1, z) for (x, z), s in t.stand.items()
             if t.kind[(x, z)] == "cave" and (x, z) not in t.lava and not near_pack(x, z) and s == math.floor(s)]
    fn.dress(p, cells, VOLCANIC, seed=71, trees=0.006, spacing=11, bushes=0.03, boulders=0.006, density=0.25,
             flowers=0.0)
    for (x, z), level in sorted(t.stand.items()):
        if t.kind[(x, z)] != "cave" or (x, z) in t.lava or near_pack(x, z, 5) or level != math.floor(level):
            continue
        s = math.floor(level)
        against = sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) in t.wall)
        if against and hash01(x, z, 5, 73) < 0.035 and fn.free(p, x, s, z):
            fn.crystal_spire(p, x, s, z, 3 + int(hash01(z, x, 6, 73) * 4), color="blue", seed=73)


def near_pack(x, z, r=6):
    return any(math.hypot(x - a, z - b) < r for a, b in PACK_CENTERS + GROUP_CENTERS)


def deck(p, t):
    """Passerelle des cuves : poutres sous le tablier, chaînes qui la pendent à la voûte tous les huit blocs, pylône à
    brasero au bord de chaque cuve, cuves en cône renversé."""
    for x in range(DECK_X0, DECK_X1 + 1):
        zc = deck_z(x)
        s = math.floor(deck_stand(x))
        if x % 6 == 0:
            for z in range(zc - DECK_HALF - 1, zc + DECK_HALF + 2):
                p.set(x, s - 2, z, BEAM)
        if x % 8 == 0:
            for z in (zc - DECK_HALF - 1, zc + DECK_HALF + 1):
                if (x, z) not in t.stand:
                    chain(p, x, z, s + 1, ceiling(x, z))
    x0, x1, z0, z1 = ARENA_BRIDGE
    for z in range(z0, z1 + 1, 6):
        s = math.floor(bridge_stand(z))
        for x in range(x0 - 1, x1 + 2):
            p.set(x, s - 2, z, BEAM)
        for x in (x0 - 1, x1 + 1):
            chain(p, x, z, s + 1, ceiling(x, z))
    for k, (cx, cz, r) in enumerate(PODS):
        s = POD_S[k]
        for a in (0.8, 0.8 + math.pi):
            x, z = round(cx + math.cos(a) * (r - 1)), round(cz + math.sin(a) * (r - 1))
            for y in range(s, s + 6):
                p.set(x, y, z, PILLAR_MID if y > s else PILLAR_BASE)
            p.set(x, s + 6, z, BRAZIER)
            chain(p, x, z, s + 7, ceiling(x, z))
        for dy in range(1, 7):
            y = s - 1 - dy
            for x in range(cx - r, cx + r + 1):
                for z in range(cz - r, cz + r + 1):
                    if math.hypot(x - cx, z - cz) <= r - dy * 0.9:
                        p.set(x, y, z, pick(WALL, x, y, z))


def lights(p, t):
    """Torches au pied des murs des salles, tous les dix blocs environ."""
    for (x, z), level in t.stand.items():
        if t.kind[(x, z)] != "hall":
            continue
        s = math.floor(level)
        if not fn.free(p, x, s, z) or hash01(x, z, 9, 81) > 0.05:
            continue
        if sum(1 for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, z + dz) not in t.stand) == 1:
            p.set(x, s, z, TORCH)


def cavern_dressing(p, t):
    """Voûte et parois : stalactites au-dessus du vide et des grottes, fissures incandescentes et cristaux bleus sur
    les parois, chutes de lave le long des parois du gouffre (jamais sur le parcours)."""
    # stalactites (grille de 9, place tirée par case)
    for gx in range(BBOX[0], BBOX[1], 9):
        for gz in range(BBOX[2], BBOX[3], 9):
            x = gx + int(hash01(gx, gz, 1, 91) * 9)
            z = gz + int(hash01(gz, gx, 2, 91) * 9)
            if (x, z) not in t.open or hash01(x, z, 3, 91) > 0.55:
                continue
            floor = LAVA_SEA if (x, z) in t.chasm else (t.stand[(x, z)] if (x, z) in t.stand else 0)
            c = ceiling(x, z)
            room = c - floor - 7
            if (x, z) in t.stand or any((x + dx, z + dz) in t.stand for dx in range(-3, 4) for dz in range(-3, 4)):
                room = min(room, 6)
            if room < 3:
                continue
            length = 3 + int(hash01(x, z, 4, 91) * min(room - 2, 12))
            big_stalactite(p, x, z, c, length, 1.2 + length * 0.18, 93)
    # parois : fissures, cristaux
    for (x, z), d in t.shell.items():
        if d != 1 or (x, z) not in t.wall:
            continue
        c = ceiling(x, z)
        for y in range(LAVA_SEA + 1, c):
            h = hash01(x, y, z, 95)
            if not wall_face(p, x, y, z):
                continue
            if h < 0.012:
                p.set(x, y, z, GLOW)
            elif h < 0.02:
                for dy in range(0, 2 + int(h * 200) % 3):
                    p.set(x, y + dy, z, CRYSTAL_BLOCK)
    # chutes de lave : contre les parois du gouffre, loin du parcours
    falls = []
    for (x, z) in sorted(t.chasm):
        if hash01(x, z, 7, 97) > 0.02 or not any((x + dx, z + dz) in t.wall for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            continue
        if any((x + dx, z + dz) in t.stand for dx in range(-4, 5) for dz in range(-4, 5)):
            continue
        if any(math.hypot(x - a, z - b) < 18 for a, b in falls):
            continue
        falls.append((x, z))
        for y in range(LAVA_SEA + 1, ceiling(x, z)):
            p.fluid(x, y, z, LAVA)
    return falls


def wall_face(p, x, y, z):
    """Vrai si le bloc de paroi (x, y, z) touche l'air (face visible)."""
    if (x, y, z) not in p.blocks:
        return False
    return any(fn.free(p, x + dx, y, z + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def big_stalactite(p, x, z, top, length, radius, seed):
    """Stalactite en cône de roche, de la voûte `top` vers le bas sur `length` blocs, pointe en stalactite vanilla."""
    for k in range(length):
        r = radius * (1 - k / length) ** 0.9
        n = int(math.ceil(r))
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= r + 0.3 * fn.vnoise2(x + dx + k, z + dz, 1.6, seed):
                    y = top - 1 - k
                    if fn.free(p, x + dx, y, z + dz):
                        p.set(x + dx, y, z + dz, GLOW if hash01(x + dx, y, z + dz, seed) < 0.03
                              else pick(ROCK, x + dx, y, z + dz))
    if fn.free(p, x, top - 1 - length, z):
        p.set(x, top - 1 - length, z, STALACTITES[int(hash01(x, z, 8, seed) * len(STALACTITES))])


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
                if m in cells and m not in label and abs(t.stand.get(m, 0) - t.stand.get((x, z), 0)) <= 1:
                    label[m] = n
                    q.append(m)
    return label


def check(t, p):
    """Le parcours se fait d'un seul tenant une fois le pont posé (marches d'un bloc au plus) ; sans lui, le canal
    coupe ; rien de plein sur les points de jeu, voûte à 10 blocs au moins, chutes de lave loin du parcours."""
    deck_cells, _ = bridge_cells()
    bridge = {(x, z) for x, _, z in deck_cells} | {(x, z) for x in range(BRIDGE[0] + 1, BRIDGE[1])
                                                    for z in range(BRIDGE[2], BRIDGE[3] + 1)}
    for c in bridge:
        t.stand.setdefault(c, FLOOR_S)
    full = components(t, bridge)
    pts = [SPAWN[::2], PACK_CENTERS[0], PACK_CENTERS[3], EFFIGY_C, GROUP_CENTERS[0], PODS[2][:2], CHECKPOINT_D[::2],
           ARENA_C]
    labels = {full[(round(x), round(z))] for x, z in pts}
    assert len(labels) == 1, f"parcours coupé : {labels}"
    for c in bridge:
        if c not in t.kind:
            t.stand.pop(c, None)
    cut = components(t)
    assert cut[PACK_CENTERS[3]] != cut[EFFIGY_C], "le canal ne coupe pas l'atelier de la fonderie"
    for x, s, z in (SPAWN, BRAHAM_AT, ROX_AT, CHECKPOINT_B, CHECKPOINT_D, BRAHAM_END, ROX_END, REWARD_AT, END_EXIT_AT):
        for y in (s, s + 1):
            name = p.blocks.get((x, y, z), (AIR,))[0]
            assert name == AIR, f"{name} sur le point {(x, s, z)}"
    for (x, z), level in t.stand.items():
        s = math.floor(level)
        assert ceiling(x, z) - s >= 10, f"voûte trop basse en {(x, s, z)}"
    for fx, fz in t.falls:
        assert not any((fx + dx, fz + dz) in t.stand for dx in range(-3, 4) for dz in range(-3, 4)), \
            f"chute de lave sur le parcours en {(fx, fz)}"


def build_all():
    p = go.Prefab()
    t = layout()
    cave(p, t)
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
    caves(p, t)
    lights(p, t)
    t.falls = cavern_dressing(p, t)
    gates = {"foundry": gate(p, FOUNDRY_GATE, FLOOR_S), "boilers": gate(p, BOILERS_GATE, BOILERS_S)}
    check(t, p)
    t.gates = gates
    t.bridge = bridge_cells()
    return p, t
