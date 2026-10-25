"""Carte et décor du Ressac silencieux (Silent Surf), d'après la carte GW2 que Kevin a envoyée (25 octobre 2026).

On part de la mer de jade pétrifiée, près de l'épave d'un navire luxon (au nord-est), et l'on descend sous la mer par une
crevasse : une immense grotte de jade sombre, sans fond, que l'on traverse de plate-forme en plate-forme vers l'ouest,
puis le sud, puis l'est, avec l'équipement de prospection (grappin, parachute, charge de poudre noire, fusée
éclairante), les tyroliennes, les champignons rebondissants et les canons à vent. Tout au bout, au-dessus d'un gouffre
violet, l'arène de Kanaxai et ses îles.

Repère : x vers l'est, z vers le sud ; « debout à s » : le sol est en s - 1 (y monde = 100 + s). Rien n'est posé au
hasard : un prefab régénéré est identique. Le gouffre n'a pas de fond : on tombe jusqu'au filet anti-chute (y monde 40,
s = -60), qui ramène au dernier point de contrôle (la Garde de Thess).
"""
import math

import fractal_common as fc
import fractal_nature as fn
import generate_observatory as go

AIR = go.AIR
pick = fc.pick
hash01 = fn.hash01
fbm2 = fn.fbm2

# --- matières ---------------------------------------------------------------------------------------------
JADE = "Nakasar_Fractal_Jade_Crystal_Block"         # jade lumineux (vert) de l'Océan solide
JADE_LARGE = "Nakasar_Fractal_Jade_Crystal_Large"
JADE_MEDIUM = "Nakasar_Fractal_Jade_Crystal_Medium"
JADE_SMALL = "Nakasar_Fractal_Jade_Crystal_Small"
WALL_ROCK = ["Rock_Slate", "Rock_Stone", "Rock_Slate", "Rock_Aqua", "Rock_Basalt", "Rock_Slate"]
CEILING_ROCK = ["Rock_Slate", "Rock_Aqua", "Rock_Stone", "Rock_Slate"]
SEA = ["Rock_Aqua", "Soil_Clay_Ocean", "Rock_Aqua", "Rock_Stone_Aqua", "Soil_Clay_Ocean"]   # mer de jade pétrifiée
SEA_CREST = ["Rock_Crystal_Green_Block", "Rock_Aqua_Cobble", "Rock_Crystal_Green_Block"]
PLANKS = "Wood_Darkwood_Planks"
PLANKS_LIGHT = "Wood_Softwood_Planks"
LOG = "Wood_Fir_Trunk"
SAIL = ["Cloth_Block_Wool_White", "Cloth_Block_Wool_Gray_Light", "Cloth_Block_Wool_White"]
NIGHTMARE = ["Rock_Basalt", "Rock_Volcanic", "Rock_Basalt", "Rock_Slate"]   # arène de Kanaxai
NIGHTMARE_CRYSTALS = ["Rock_Crystal_Purple_Large", "Rock_Crystal_Purple_Medium", "Rock_Crystal_Purple_Small"]
STALACTITES = ["Rock_Aqua_Stalactite_Large", "Rock_Slate_Stalactite_Large", "Rock_Aqua_Stalactite_Small",
               "Rock_Stone_Stalactite_Large"]
HANGING = 8                                     # bloc retourné (stalactites des prefabs de grottes vanilla)
GLOW_MUSHROOMS = ["Plant_Crop_Mushroom_Glowing_Blue", "Plant_Crop_Mushroom_Glowing_Green",
                  "Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Violet"]
BOUNCE_CAP = "Nakasar_Fractal_Bounce_Cap"
SUPPLIES = "Nakasar_Fractal_Leftover_Supplies"
ZIP_ANCHOR = "Nakasar_Fractal_Zipline_Anchor"
WIND_CANNON = "Nakasar_Fractal_Wind_Cannon"
CHECKPOINT_RING = "Nakasar_Fractal_Survey_Mark"
LANTERN = "Deco_Lantern"

CAVERN = fn._theme(soil=["Rock_Stone_Mossy", "Plant_Moss_Block_Green_Dark", "Rock_Slate", "Rock_Stone_Mossy"],
                   dirt=["Rock_Slate", "Rock_Stone"], deep=["Rock_Slate", "Rock_Aqua", "Rock_Slate", "Rock_Basalt"],
                   short=["Plant_Moss_Short_Green_Dark", "Plant_Moss_Short_Green", "Plant_Moss_Rug_Green_Dark"],
                   tall=["Plant_Moss_Cave_Green_Dark", "Plant_Moss_Short_Green_Dark"],
                   flowers=[GLOW_MUSHROOMS[:2], GLOW_MUSHROOMS[2:]], bushes=["Plant_Crop_Mushroom_Flatcap_Green",
                                                                           JADE_SMALL, "Plant_Crop_Mushroom_Glowing_Blue"],
                   hang=["Plant_Vine_Green_Hanging", "Plant_Vine_Hanging"], trees=[], conifers=[],
                   rocks=["Rock_Slate", "Rock_Aqua", "Rock_Stone"],
                   fertile={"Rock_Stone_Mossy", "Plant_Moss_Block_Green_Dark"})

ABYSS = -62                                     # bas des parois (le filet anti-chute est à s = -60)
SURFACE = 40                                    # debout sur la mer de jade

# --- la grotte ------------------------------------------------------------------------------------------------
# Tube : points (x, z, plafond, rayon) ; la grotte est l'union des tubes et du gouffre de l'arène.
TUBE = [
    (54, -104, 22, 16), (40, -97, 22, 20), (14, -92, 22, 20), (-14, -86, 22, 20), (-30, -80, 20, 20),
    (-50, -62, 24, 22), (-60, -46, 18, 24), (-60, -24, 10, 20), (-58, -6, 14, 20), (-57, 10, 14, 20),
    (-56, 30, 12, 20), (-55, 40, 12, 20), (-52, 60, 10, 24), (-38, 80, 18, 20), (-16, 92, 14, 20),
    (2, 100, 6, 20), (16, 106, 4, 20), (34, 110, 6, 20), (50, 108, 6, 20), (60, 106, 6, 20), (80, 102, 8, 20),
    (100, 100, 22, 20), (106, 86, 22, 18), (104, 66, 16, 22),
]
ARENA_C = (66, 34)
ARENA_CAVE = (60, 8)                            # rayon et plafond du gouffre de l'arène

# --- la surface : mer de jade et épave ----------------------------------------------------------------------
SPAWN = (72, SURFACE, -124)
SEA_C, SEA_R = (64, -116), 56
CREVASSE = [(70, -110, 3), (60, -106, 4.5), (50, -102, 5), (42, -99, 4)]   # (x, z, demi-largeur)
WRECK_C, WRECK_LEN, WRECK_W = (88, -136), 26, 9

# --- plates-formes : nom -> (cx, cz, rayon, debout, genre) ------------------------------------------------------
PLATFORMS = {
    "cp1": (42, -96, 7, 10, "ledge"),
    "p1": (14, -93, 5, 12, "jade"),
    "p2": (-30, -80, 6, 2, "jade"),
    "cp2": (-60, -46, 12, -16, "rock"),
    "p3": (-57, 10, 9, -16, "rock"),
    "cp3": (-52, 66, 12, -12, "rock"),
    "p4": (40, 112, 6, -30, "rock"),
    "p5": (100, 100, 6, -16, "rock"),
    "cp4": (104, 64, 12, -10, "rock"),
}
# Points de contrôle : plate-forme, cercle blanc (x, z, rayon), provisions, Thess (debout calculé).
CHECKPOINTS = [
    ("start", (66, -120, 4), (74, -118), (70, -117)),
    ("cp1", (42, -96, 3), (46, -99), (45, -95)),
    ("cp2", (-60, -46, 4), (-55, -53), (-56, -50)),
    ("cp3", (-52, 66, 4), (-59, 60), (-58, 63)),
    ("cp4", (104, 64, 4), (110, 60), (108, 63)),
]

# --- tyroliennes : nom -> (ancre (x, z, plate-forme), départ et arrivée des pieds (x, y, z)) ---------------------
ZIPLINES = {
    "z1": ((10, -92, "p1"), (9.5, 13.0, -91.5), (-26.5, 3.0, -81.5)),
    "z2": ((-33, -77, "p2"), (-33.5, 3.0, -76.5), (-55.5, 1.0, -55.5)),
    "z3": (None, (-34.5, 6.0, 84.5), (2.5, -8.0, 100.5)),
    "z4": (None, (68.5, -2.0, 104.5), (97.5, -13.0, 99.5)),
    "z5": (None, (104.5, 10.0, 104.5), (104.5, 2.0, 74.5)),
}
ZIP_SAG = 0.06                                  # flèche du câble (part de la longueur)

# --- canons à vent : nom -> (bloc (x, z, plate-forme) ou None, trajet des pieds, suite) ----------------------------
CANNONS = {
    "c1": ((-57, 16, "p3"), [(-56.5, -15.0, 17.5), (-56.5, -4.0, 28.5), (-56.0, -3.0, 40.5), (-54.0, -6.0, 52.0),
                             (-52.5, -11.0, 59.5)], None),
    "c2": ((-42, 70, "cp3"), [(-41.5, -11.0, 70.5), (-39.0, 2.0, 77.0), (-34.5, 6.0, 84.5)], "z3"),
    "c3": (None, [(14.0, -10.0, 106.0), (20.0, -6.0, 108.0), (26.0, -6.0, 110.0)], None),
    "c4": ((102, 97, "p5"), [(102.5, -15.0, 97.5), (106.0, 4.0, 104.0), (104.5, 10.0, 104.5)], "z5"),
}
CANNON_SPEED = 14.0                             # blocs par seconde le long du trajet
C3_RING = (14, -10, 106)                        # anneau de jade du canon en l'air (centre)
C3_RELEASE = (9.0, 2.0, 1.0)                    # vitesse en sortie du canon c3 (vers les piliers)

# --- champignons rebondissants : (cx, cz, rayon du chapeau, debout sur le chapeau, cible) -------------------------
# Cible : ("apex", (x, y, z), (vx, vy, vz) à la sortie) ; ("cannon", nom) ; ("zip", nom) ; ("arena",) centre de l'arène.
MUSHROOMS = [
    (-63, -28, 2, -34, ("apex", (-58.0, -11.0, -8.0), (0.0, 1.0, 6.0))),
    (-57, -27, 2, -35, ("apex", (-58.0, -11.0, -8.0), (0.0, 1.0, 6.0))),
    (-60, -22, 2, -33, ("apex", (-58.0, -11.0, -8.0), (0.0, 1.0, 6.0))),
    (0, 99, 2, -25, ("cannon", "c3")),
    (5, 102, 2, -24, ("cannon", "c3")),
    (-3, 103, 2, -26, ("cannon", "c3")),
    (58, 106, 2, -25, ("zip", "z4")),
    (62, 110, 2, -26, ("zip", "z4")),
    (57, 112, 2, -24, ("zip", "z4")),
]
BOUNCE_SECONDS = 1.1

# --- grand stalactite de jade, mur de jade, piliers ----------------------------------------------------------------
STALACTITE = (-58, 4, 14, -14, 4.0)             # x, z, haut (plafond), pointe, rayon en haut
JADE_WALL = (40, 2, (-56, -3), 3.5)              # z, épaisseur, trou (x, y), rayon du trou
PILLARS = [(34, 112, -2, 2.2), (48, 108, -4, 2.2)]   # x, z, sommet, rayon

# --- l'arène de Kanaxai ----------------------------------------------------------------------------------------------
ARENA_STAND = -46
ARENA_R = 22
ISLAND_R = 6
ISLANDS = [(2, 42, -44), (74, 42, -40), (146, 42, -42), (218, 42, -37), (290, 42, -43)]   # angle, rayon, debout
EDGE_ASPECTS = [0, 72, 144, 216, 288]           # angles des Aspects au bord (rayon ARENA_R - 2)
ASPECT_KINDS = ["Death", "Exposure", "Fear", "Lethargy", "Torment"]

# --- carnets des marins (Enquête sinistre) ---------------------------------------------------------------------------
JOURNALS = [("cp1", 2, 4), ("p2", -3, 2), ("cp2", -8, -5), ("p3", 5, -4), ("cp3", 7, 6), ("cp4", -5, 8)]


def arena_point(angle, radius, stand):
    a = math.radians(angle)
    return (ARENA_C[0] + math.cos(a) * radius, stand, ARENA_C[1] + math.sin(a) * radius)


def island_centers():
    return [(round(ARENA_C[0] + math.cos(math.radians(a)) * r), round(ARENA_C[1] + math.sin(math.radians(a)) * r), s)
            for a, r, s in ISLANDS]


# --- la grotte : empreinte, plafond, parois --------------------------------------------------------------------------

def _seg_nearest(px, pz, a, b):
    ax, az = a[0], a[1]
    bx, bz = b[0], b[1]
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L))
    return math.hypot(px - (ax + dx * t), pz - (az + dz * t)), t


class Cave:
    """Empreinte de la grotte (`inside` : {(x, z): plafond}), puis parois et plafond en coquille d'un bloc ou deux."""

    def __init__(self):
        self.inside = {}
        xs = [w[0] for w in TUBE] + [ARENA_C[0] - ARENA_CAVE[0], ARENA_C[0] + ARENA_CAVE[0]]
        zs = [w[1] for w in TUBE] + [ARENA_C[1] - ARENA_CAVE[0], ARENA_C[1] + ARENA_CAVE[0]]
        for x in range(min(xs) - 30, max(xs) + 31):
            for z in range(min(zs) - 30, max(zs) + 31):
                c = self._ceiling(x, z)
                if c is not None:
                    self.inside[(x, z)] = c
        self.open_sky = set()
        for x, z in list(self.inside):
            if crevasse_half(x, z) is not None:
                self.open_sky.add((x, z))

    @staticmethod
    def _ceiling(x, z):
        best = None
        for a, b in zip(TUBE, TUBE[1:]):
            d, t = _seg_nearest(x, z, a, b)
            r = a[3] + (b[3] - a[3]) * t
            r += 4.5 * fbm2(x, z, 11, 2, 701) + 1.5 * fbm2(x, z, 4, 1, 702)
            if d <= r:
                c = a[2] + (b[2] - a[2]) * t
                c += 3 + 5 * abs(fbm2(x, z, 9, 2, 703)) + (1 - d / r) * 4
                best = c if best is None else max(best, c)
        ax, az = ARENA_C
        d = math.hypot(x - ax, z - az)
        r = ARENA_CAVE[0] + 6 * fbm2(x, z, 13, 2, 704)
        if d <= r:
            c = ARENA_CAVE[1] + 4 * abs(fbm2(x, z, 10, 2, 705)) + (1 - d / r) * 10
            best = c if best is None else max(best, c)
        return None if best is None else int(math.floor(best))

    def air(self, x, z, y):
        c = self.inside.get((x, z))
        if c is None:
            return False
        return (x, z) in self.open_sky or y < c

    def build(self, p):
        """Coquille : parois (cases pleines voisines de l'air de la grotte), plafond sur 2 blocs, et les marches de
        plafond entre colonnes voisines ; veines de jade lumineux dans la roche."""
        sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
        walls = {}
        for (x, z), c in self.inside.items():
            for dx, dz in sides:
                n = (x + dx, z + dz)
                if n in self.inside:
                    continue
                top = SURFACE if (x, z) in self.open_sky else c
                walls[n] = max(walls.get(n, ABYSS), top)
        for (x, z), top in walls.items():
            for y in range(ABYSS, top + 1):
                p.set(x, y, z, rock(x, y, z, WALL_ROCK, 0.025))
        for (x, z), c in self.inside.items():
            if (x, z) in self.open_sky:
                continue
            high = c + 1
            for dx, dz in sides:
                n = (x + dx, z + dz)
                if n in self.inside:
                    high = max(high, SURFACE - 1 if n in self.open_sky else self.inside[n] - 1)
            for y in range(c, high + 1):
                p.set(x, y, z, rock(x, y, z, CEILING_ROCK, 0.03))

    def dress_ceiling(self, p, keep):
        """Stalactites, grappes de jade et lianes lumineuses au plafond (hors des trajets `keep`)."""
        for (x, z), c in sorted(self.inside.items()):
            if (x, z) in self.open_sky or (x, z) in keep:
                continue
            h = hash01(x, c, z, 711)
            if not fn.free(p, x, c - 1, z):
                continue
            if h < 0.035:
                p.set(x, c - 1, z, STALACTITES[int(hash01(z, x, c, 712) * len(STALACTITES))], HANGING)
            elif h < 0.05:
                p.set(x, c - 1, z, (JADE_LARGE, JADE_MEDIUM)[int(hash01(z, c, x, 713) * 2)], HANGING)
            elif h < 0.075:
                for k in range(1 + int(hash01(x, z, 7, 714) * 6)):
                    if fn.free(p, x, c - 1 - k, z):
                        p.set(x, c - 1 - k, z, "Plant_Vine_Green_Hanging")
            elif h < 0.08:
                big_stalactite(p, x, z, c, 3 + int(hash01(x, z, 9, 715) * 7), 1.4, 716 + x)


def rock(x, y, z, palette, jade):
    if hash01(x, y, z, 717) < jade and fbm2(x + y, z - y, 7, 1, 718) > 0.15:
        return JADE
    return pick(palette, x, y, z)


def crevasse_half(x, z):
    """Demi-largeur de la crevasse en (x, z), None hors de la crevasse."""
    best = None
    for a, b in zip(CREVASSE, CREVASSE[1:]):
        d, t = _seg_nearest(x, z, a, b)
        half = a[2] + (b[2] - a[2]) * t + 0.8 * fbm2(x, z, 4, 1, 719)
        if d <= half:
            best = half
    return best


def big_stalactite(p, x, z, top, length, radius, seed, block=None):
    """Stalactite en cône, du plafond `top` vers le bas sur `length` blocs (roche, ou jade si `block`)."""
    for k in range(length):
        r = radius * (1 - k / length) ** 0.9
        n = int(math.ceil(r))
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= r + 0.3 * fn.vnoise2(x + dx + k, z + dz, 1.6, seed):
                    y = top - 1 - k
                    if fn.free(p, x + dx, y, z + dz):
                        p.set(x + dx, y, z + dz, block(x + dx, y, z + dz) if block else rock(x + dx, y, z + dz, WALL_ROCK, 0.08))


# --- la surface ----------------------------------------------------------------------------------------------------

def sea_level(x, z):
    """Debout sur la mer pétrifiée : houle figée (vagues orientées), plat autour du départ."""
    if math.hypot(x - SPAWN[0], z - SPAWN[2]) < 7:
        return SURFACE
    wave = math.sin((x * 0.8 + z * 0.35) / 4.2 + 1.5 * fbm2(x, z, 13, 1, 720))
    h = 1.2 * max(0.0, wave) ** 2 + 0.9 * fbm2(x, z, 9, 2, 721)
    return SURFACE + int(round(h))


def surface(p, cave):
    """La mer de jade pétrifiée autour du départ : vagues figées, crêtes de jade, bord irrégulier qui retombe en
    falaise ; la crevasse s'ouvre sur la grotte."""
    cx, cz = SEA_C
    tops = {}
    for x in range(cx - SEA_R - 8, cx + SEA_R + 9):
        for z in range(cz - SEA_R - 8, cz + SEA_R + 9):
            if math.hypot(x - cx, z - cz) > SEA_R * (0.9 + 0.12 * fbm2(x, z, 12, 2, 722)):
                continue
            if crevasse_half(x, z) is not None:
                continue
            tops[(x, z)] = sea_level(x, z)
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for (x, z), s in tops.items():
        crest = s > SURFACE and hash01(x, s, z, 723) < 0.5
        p.set(x, s - 1, z, pick(SEA_CREST, x, s, z) if crest else pick(SEA, x, s, z))
        for y in range(SURFACE - 3, s - 1):
            p.set(x, y, z, pick(SEA, x, y, z))
        edge = any((x + dx, z + dz) not in tops for dx, dz in sides)
        if edge:
            # bord de la mer : falaise qui descend jusqu'au plafond de la grotte (ou un peu plus bas dehors)
            low = cave.inside.get((x, z), SURFACE - 10 - int(5 * abs(fbm2(x, z, 6, 1, 724))))
            for y in range(min(low, SURFACE - 4), SURFACE - 3):
                p.set(x, y, z, rock(x, y, z, WALL_ROCK, 0.04))
    return tops


def wreck(p):
    """L'épave du navire luxon, échouée de travers sur la mer de jade : coque éventrée, mât brisé, voile en lambeaux,
    caisses et tonneaux de la cargaison."""
    cx, cz = WRECK_C
    half_l, half_w = WRECK_LEN / 2, WRECK_W / 2
    base = SURFACE
    for i in range(-int(half_l), int(half_l) + 1):
        t = i / half_l
        w = half_w * math.sqrt(max(0.0, 1 - t ** 4)) * (0.75 if t > 0.5 else 1.0)
        depth = 4 if abs(t) < 0.7 else 3
        tilt = int(round(t * 1.5))                       # la proue remonte
        for j in range(-int(w) - 1, int(w) + 2):
            if abs(j) > w + 0.4:
                continue
            x, z = cx + i, cz + j
            side = abs(j) > w - 1
            for k in range(depth):
                y = base - 1 + k + tilt + (1 if j > 0 else 0)          # couchée sur bâbord
                if side or k == 0:
                    if i == 3 and k >= 1 and abs(j) > w - 1 and j < 0:
                        continue                                       # brèche dans la coque
                    p.set(x, y, z, PLANKS if (k + i) % 4 else PLANKS_LIGHT)
            if not side and abs(i) < half_l - 2 and i % 5 != 0:
                p.set(x, base + tilt + (1 if j > 0 else 0), z, PLANKS_LIGHT)      # pont
    # mât brisé couché et bout de mât debout
    for k in range(5):
        p.set(cx - 2, base + 1 + k, cz, LOG)
    for k in range(10):
        p.set(cx - 4 - k, base + (1 if k < 3 else 0), cz + 3 + k // 3, LOG, 1)
    for k in range(6):
        for h in range(3):
            if hash01(k, h, 1, 725) < 0.75:
                p.set(cx - 6 - k, base + 1 + h, cz + 6 + k // 3, SAIL[(k + h) % len(SAIL)])
    for k, (dx, dz) in enumerate(((-16, 4), (-15, -3), (-19, 1), (14, 6), (16, -2), (-12, 8), (-21, -4))):
        x, z = cx + dx, cz + dz
        p.set(x, sea_level(x, z), z, ("Furniture_Village_Crate", "Furniture_Tavern_Barrel")[k % 2])


# --- plates-formes ---------------------------------------------------------------------------------------------------

def platform_cells(name):
    cx, cz, r, s, _ = PLATFORMS[name]
    cells = {}
    n = int(r * 1.3) + 2
    for x in range(cx - n, cx + n + 1):
        for z in range(cz - n, cz + n + 1):
            if math.hypot(x - cx, z - cz) <= r * (1 + 0.14 * fbm2(x, z, 6, 2, 730 + cx)):
                cells[(x, z)] = s - 1
    return cells


def platform(p, name, seed):
    """Plate-forme naturelle : dessus plat (debout s), dessous rocheux en cône, lianes ; une plate-forme de jade a son
    dessus et ses bords en jade lumineux."""
    cx, cz, r, s, kind = PLATFORMS[name]
    tops = platform_cells(name)
    edge = fn.edge_distance(tops)
    if kind == "jade":
        for (x, z), y in tops.items():
            p.set(x, y, z, JADE if edge[(x, z)] <= 1 or hash01(x, y, z, seed) < 0.35 else "Rock_Aqua")
    depth = (lambda x, z: 3 + min(r * 1.3, edge[(x, z)] * 1.6) + 2 * fbm2(x, z, 5, 2, seed + 1))
    cells = fn.island(p, tops, depth, seed, hang=0.25, theme=CAVERN)
    return tops, cells


def stand_of(tops, x, z):
    return tops[(x, z)] + 1


def mushroom(p, cx, cz, r, s, seed, stem_to=None):
    """Champignon rebondissant : pied violet qui sort de la roche (ou du vide) jusqu'au chapeau, chapeau bombé dont le
    dessus est fait de blocs rebondissants lumineux. Rend les cases du dessus [(x, y, z)]."""
    top_y = s - 1
    bottom = stem_to if stem_to is not None else top_y - 14
    for y in range(bottom, top_y - 1):
        for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1)) if r >= 2 else ((0, 0),):
            p.set(cx + dx - (1 if r >= 2 else 0) // 2, y, cz + dz - (1 if r >= 2 else 0) // 2,
                  "Plant_Crop_Mushroom_Block_Purple_Trunk")
    cells = []
    for dx in range(-r - 1, r + 2):
        for dz in range(-r - 1, r + 2):
            d = math.hypot(dx, dz)
            if d > r + 0.6:
                continue
            x, z = cx + dx, cz + dz
            if d <= r - 0.4:
                p.set(x, top_y, z, BOUNCE_CAP)
                cells.append((x, top_y, z))
            else:
                p.set(x, top_y - 1, z, "Plant_Crop_Mushroom_Block_Purple")
                p.set(x, top_y, z, BOUNCE_CAP)
                cells.append((x, top_y, z))
            p.set(x, top_y - 1, z, "Plant_Crop_Mushroom_Block_Purple")
    # petites lueurs sous le chapeau
    for dx, dz in ((r + 1, 0), (-r - 1, 0), (0, r + 1), (0, -r - 1)):
        if hash01(cx + dx, cz + dz, s, seed) < 0.5:
            p.set(cx + dx, top_y - 2, cz + dz, "Plant_Vine_Green_Hanging")
    return cells


def jade_ring(p, cx, cy, cz, r=3.2):
    """Anneau de jade vertical (canon en l'air), ouvert d'est en ouest."""
    out = []
    for a in range(0, 360, 6):
        y = cy + 1 + math.sin(math.radians(a)) * r
        z = cz + math.cos(math.radians(a)) * r
        for t in (0, 1):
            cell = (cx + t, int(round(y)), int(round(z)))
            if cell not in out:
                out.append(cell)
                p.set(*cell, JADE)
    return out


def pillar(p, x, z, top, r, seed):
    """Pilier de jade qui monte du gouffre : fût irrégulier, dessus plat (debout à `top`), petits cristaux au bord."""
    for y in range(ABYSS, top):
        rr = r * (0.85 + 0.25 * fn.vnoise2(y, x + z, 3.0, seed))
        n = int(math.ceil(rr))
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= rr:
                    p.set(x + dx, y, z + dz, JADE if hash01(dx, y, dz, seed) < 0.7 else "Rock_Aqua")
    for dx, dz in ((2, 1), (-2, -1), (1, -2)):
        if fn.free(p, x + dx, top, z + dz) and math.hypot(dx, dz) <= r:
            p.set(x + dx, top, z + dz, JADE_SMALL)


def jade_wall(p, cave):
    """Mur de jade en travers du gouffre, percé d'un trou rond : le canon à vent y fait passer."""
    z0, thick, (hx, hy), hr = JADE_WALL
    for (x, z), c in cave.inside.items():
        if not z0 <= z < z0 + thick or x > 0:
            continue                    # le tunnel de l'ouest seulement (pas le gouffre de l'arène)
        for y in range(ABYSS, c):
            if math.hypot(x - hx, y - hy) <= hr + 0.4 * fn.vnoise2(x, y, 1.5, 731):
                continue
            p.set(x, y, z, JADE if hash01(x, y, z, 732) < 0.6 else pick(["Rock_Aqua", "Rock_Crystal_Green_Block"], x, y, z))


def zipline_points(name, step=1.0):
    """Points du câble (pieds du joueur) avec la flèche, tous les `step` blocs."""
    _, a, b = ZIPLINES[name]
    length = math.dist(a, b)
    n = max(2, int(length / step))
    pts = []
    for k in range(n + 1):
        t = k / n
        sag = 4 * ZIP_SAG * length * t * (1 - t)
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t - sag, a[2] + (b[2] - a[2]) * t))
    return pts


def cable_cells(name):
    """Cases du câble au-dessus des pieds (le joueur pend sous lui)."""
    out = []
    for x, y, z in zipline_points(name, 0.5):
        cell = (math.floor(x), math.floor(y + 2.6), math.floor(z))
        if cell not in out:
            out.append(cell)
    return out
