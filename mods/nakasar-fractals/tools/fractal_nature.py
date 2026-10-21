"""Décor naturel des fractales : bruit lisse, arbres, buissons, fleurs, rochers, îles flottantes.

Tout est déterministe (aucun hasard) : un prefab régénéré est identique. Les fonctions écrivent dans un
`generate_observatory.Prefab` et ne posent jamais rien sur une case déjà prise, sauf mention contraire, pour ne pas
abîmer le parcours posé avant elles. Ids vanilla relevés dans tools/vanilla-block-ids-0.7.2.txt.
"""
import math

# --- bruit -----------------------------------------------------------------------------------------

def hash01(x, y, z=0, seed=0):
    """Valeur pseudo-aléatoire stable dans [0, 1) pour une case entière."""
    h = (x * 374761393 + y * 668265263 + z * 2147483647 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(1 << 24)


def _smooth(t):
    return t * t * (3 - 2 * t)


def vnoise2(x, y, scale, seed=0):
    """Bruit de valeur lisse en 2D, dans [-1, 1]."""
    fx, fy = x / scale, y / scale
    x0, y0 = math.floor(fx), math.floor(fy)
    tx, ty = _smooth(fx - x0), _smooth(fy - y0)
    a = hash01(x0, y0, 0, seed)
    b = hash01(x0 + 1, y0, 0, seed)
    c = hash01(x0, y0 + 1, 0, seed)
    d = hash01(x0 + 1, y0 + 1, 0, seed)
    v = a + (b - a) * tx + (c - a) * ty + (a - b - c + d) * tx * ty
    return v * 2 - 1


def fbm2(x, y, scale, octaves=3, seed=0):
    """Somme de bruits (octaves de plus en plus fines), dans [-1, 1] environ."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * vnoise2(x, y, scale / (2 ** o), seed + o * 101)
        norm += amp
        amp *= 0.5
    return total / norm


def vnoise3(x, y, z, scale, seed=0):
    fx, fy, fz = x / scale, y / scale, z / scale
    x0, y0, z0 = math.floor(fx), math.floor(fy), math.floor(fz)
    tx, ty, tz = _smooth(fx - x0), _smooth(fy - y0), _smooth(fz - z0)

    def lerp(a, b, t):
        return a + (b - a) * t
    c = [[[hash01(x0 + i, y0 + j, z0 + k, seed) for k in (0, 1)] for j in (0, 1)] for i in (0, 1)]
    v = lerp(lerp(lerp(c[0][0][0], c[0][0][1], tz), lerp(c[0][1][0], c[0][1][1], tz), ty),
             lerp(lerp(c[1][0][0], c[1][0][1], tz), lerp(c[1][1][0], c[1][1][1], tz), ty), tx)
    return v * 2 - 1


# --- palettes ---------------------------------------------------------------------------------------

GRASS_SHORT = ["Plant_Grass_Lush_Short", "Plant_Grass_Lush_Short", "Plant_Grass_Sharp_Short", "Plant_Grass_Lush"]
GRASS_TALL = ["Plant_Grass_Lush", "Plant_Grass_Lush_Tall", "Plant_Grass_Sharp_Tall", "Plant_Grass_Sharp_Wild"]
# Massifs de fleurs : une couleur dominante par massif, comme dans les prairies vanilla.
FLOWER_PATCHES = [
    ["Plant_Flower_Common_Yellow", "Plant_Flower_Common_Yellow2", "Plant_Flower_Bushy_Yellow"],
    ["Plant_Flower_Common_White", "Plant_Flower_Common_White2", "Plant_Flower_Bushy_White"],
    ["Plant_Flower_Common_Blue", "Plant_Flower_Common_Blue2", "Plant_Flower_Flax_Blue"],
    ["Plant_Flower_Common_Purple", "Plant_Flower_Common_Violet", "Plant_Flower_Tall_Purple"],
    ["Plant_Flower_Common_Pink", "Plant_Flower_Common_Pink2", "Plant_Flower_Flax_Pink"],
    ["Plant_Flower_Common_Red", "Plant_Flower_Common_Red2", "Plant_Flower_Bushy_Red"],
    ["Plant_Flower_Common_Orange", "Plant_Flower_Flax_Orange", "Plant_Flower_Common_Orange2"],
]
BUSHES = ["Plant_Bush_Lush", "Plant_Bush_Green", "Plant_Bush", "Plant_Fern_Forest", "Plant_Fern"]
GRASS_SOIL = ["Soil_Grass", "Soil_Grass_Full", "Soil_Grass_Sunny", "Soil_Grass_Deep"]
ROCKS = ["Rock_Stone", "Rock_Stone_Mossy", "Rock_Stone_Cobble_Mossy", "Rock_Slate"]
DIRT = ["Soil_Dirt", "Soil_Dirt", "Soil_Clay"]
DEEP = ["Rock_Stone", "Rock_Stone", "Rock_Slate", "Rock_Shale"]
HANGING = ["Plant_Vine_Green_Hanging", "Plant_Vine_Hanging"]

TREES = {
    # nom : (tronc, feuilles)
    "oak": ("Wood_Oak_Trunk", "Plant_Leaves_Oak"),
    "birch": ("Wood_Birch_Trunk", "Plant_Leaves_Birch"),
    "beech": ("Wood_Beech_Trunk", "Plant_Leaves_Beech"),
    "maple": ("Wood_Maple_Trunk", "Plant_Leaves_Maple"),
    "fir": ("Wood_Fir_Trunk", "Plant_Leaves_Fir"),
    "cedar": ("Wood_Cedar_Trunk", "Plant_Leaves_Cedar"),
}


def soil(x, z, seed=0):
    """Herbe du dessus : grandes plaques de teintes voisines."""
    n = fbm2(x, z, 14, 2, seed)
    return GRASS_SOIL[min(len(GRASS_SOIL) - 1, int((n + 1) / 2 * len(GRASS_SOIL)))]


def free(p, x, y, z):
    return (x, y, z) not in p.blocks


# --- arbres -------------------------------------------------------------------------------------------

def broadleaf(p, x, y, z, height, kind="oak", seed=0):
    """Feuillu : tronc droit (évasé au pied s'il est grand), deux ou trois branches montantes, houppier fait de
    boules de feuilles rongées par le bruit. `y` est la première case d'air au-dessus du sol."""
    trunk, leaves = TREES[kind]
    for k in range(height):
        p.set(x, y + k, z, trunk)
    if height >= 7:
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if hash01(x + dx, y, z + dz, seed) < 0.6:
                p.set(x + dx, y, z + dz, trunk)
    top = y + height
    blobs = [(0, 0, 0, 2.6 + height * 0.18)]
    for b in range(2 + int(hash01(x, y, z, seed + 1) * 2)):
        a = hash01(x, b, z, seed + 2) * math.tau
        r = 1.6 + hash01(b, x, z, seed + 3) * 1.2
        bx, bz = round(math.cos(a) * r), round(math.sin(a) * r)
        by = -1 - int(hash01(z, b, x, seed + 4) * 2)
        blobs.append((bx, by, bz, 2.0 + hash01(x, z, b, seed + 5) * 0.9))
        # branche : du tronc vers la boule, en marches verticales
        for t in range(1, max(abs(bx), abs(bz)) + 1):
            cx = x + round(bx * t / max(abs(bx), abs(bz), 1))
            cz = z + round(bz * t / max(abs(bx), abs(bz), 1))
            p.set(cx, top + by - 1 - (1 if t == 1 else 0), cz, trunk)
    span = int(max(b[3] for b in blobs)) + 3
    for dx in range(-span, span + 1):
        for dz in range(-span, span + 1):
            for dy in range(-3, span):
                inside = False
                for bx, by, bz, r in blobs:
                    d = math.sqrt((dx - bx) ** 2 + ((dy - by) * 1.25) ** 2 + (dz - bz) ** 2)
                    if d <= r + 0.45 * vnoise3(x + dx, top + dy, z + dz, 2.3, seed + 7):
                        inside = True
                        break
                if inside and free(p, x + dx, top + dy, z + dz):
                    p.set(x + dx, top + dy, z + dz, leaves)
    p.set(x, top - 1, z, trunk)


def conifer(p, x, y, z, height, kind="fir", seed=0):
    """Résineux : tronc jusqu'à la pointe, étages de branches en cônes qui rétrécissent, bord irrégulier."""
    trunk, leaves = TREES[kind]
    for k in range(height):
        p.set(x, y + k, z, trunk)
    base = y + max(2, height // 4)
    top = y + height + 1
    for yy in range(base, top + 1):
        t = (yy - base) / max(1, top - base)
        tier = 0.55 + 0.45 * (((yy - base) % 3) / 2)       # étages : large en bas de chaque étage
        r = (1 - t) * (1.6 + height * 0.22) * tier + 0.4
        n = int(math.ceil(r)) + 1
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                d = math.hypot(dx, dz)
                if d <= r + 0.35 * vnoise2(x + dx + yy * 7, z + dz, 1.7, seed) and free(p, x + dx, yy, z + dz):
                    p.set(x + dx, yy, z + dz, leaves)
    p.set(x, top, z, leaves)


def shrub(p, x, y, z, seed=0, leaves="Plant_Leaves_Oak"):
    """Petit massif : une à trois feuilles au sol et un buisson vanilla à côté."""
    p.set(x, y, z, leaves) if free(p, x, y, z) else None
    for dx, dz in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        if hash01(x + dx, y, z + dz, seed) < 0.45 and free(p, x + dx, y, z + dz):
            p.set(x + dx, y, z + dz, leaves)
    if hash01(x, y, z, seed + 9) < 0.5 and free(p, x, y + 1, z):
        p.set(x, y + 1, z, leaves)


def boulder(p, x, y, z, r, seed=0):
    """Rocher moussu à moitié enterré (centre en y - 1)."""
    n = int(math.ceil(r)) + 1
    for dx in range(-n, n + 1):
        for dz in range(-n, n + 1):
            for dy in range(-1, n + 1):
                d = math.sqrt(dx * dx + (dy * 1.4) ** 2 + dz * dz)
                if d <= r + 0.5 * vnoise3(x + dx, y + dy, z + dz, 1.6, seed):
                    top = dy >= r * 0.4
                    p.set(x + dx, y - 1 + dy, z + dz,
                          "Rock_Stone_Mossy" if top and hash01(x + dx, dy, z + dz, seed) < 0.6 else ROCKS[
                              int(hash01(dx, y, dz, seed + 1) * len(ROCKS))])


def flora(p, cells, seed=0, density=0.55, flowers=0.16):
    """Herbes et fleurs sur les cases d'herbe `cells` [(x, y_sol, z)] : herbe courte partout, haute par endroits,
    massifs de fleurs d'une couleur selon le bruit. Ne pose que sur l'air."""
    for x, y, z in cells:
        if not free(p, x, y + 1, z):
            continue
        h = hash01(x, y, z, seed)
        patch = fbm2(x, z, 9, 2, seed + 3)
        if patch > 0.25 and h < flowers + (patch - 0.25):
            colors = FLOWER_PATCHES[int((fbm2(x, z, 23, 1, seed + 5) + 1) / 2 * len(FLOWER_PATCHES)) % len(FLOWER_PATCHES)]
            p.set(x, y + 1, z, colors[int(hash01(z, x, y, seed + 6) * len(colors))])
        elif h < density:
            tall = fbm2(x, z, 6, 2, seed + 11) > 0.2
            pool = GRASS_TALL if tall else GRASS_SHORT
            p.set(x, y + 1, z, pool[int(hash01(x, z, y, seed + 12) * len(pool))])


# --- îles flottantes ----------------------------------------------------------------------------------

def island(p, tops, depth_of, seed=0, grass=None, hang=0.12):
    """Île flottante : `tops` {(x, z): y_sol} (dessus du sol), `depth_of(x, z)` profondeur du dessous. Écrit le sol
    (herbe), trois couches de terre puis la roche, seulement là où la roche se voit (bords, dessous), et laisse
    pendre quelques lianes sous les bords. Rend les cases d'herbe [(x, y, z)] pour `flora`."""
    bottoms = {}
    for (x, z), top in tops.items():
        bottoms[(x, z)] = top - max(2, int(depth_of(x, z)))
    grass_cells = []
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for (x, z), top in tops.items():
        bottom = bottoms[(x, z)]
        edge = any((x + dx, z + dz) not in tops for dx, dz in sides)
        # plus haut fond voisin : en dessous, la roche se voit de côté
        side = max([bottoms[(x + dx, z + dz)] for dx, dz in sides if (x + dx, z + dz) in bottoms] or [top])
        for y in range(bottom, top + 1):
            if not (edge or y <= bottom + 1 or y < side or y >= top - 3):
                continue
            if y == top:
                block = grass(x, z) if grass else soil(x, z, seed)
            elif y >= top - 3:
                block = DIRT[int(hash01(x, y, z, seed) * len(DIRT))]
            else:
                band = int((y + 3 * vnoise2(x, z, 11, seed)) // 3)
                block = DEEP[band % len(DEEP)]
            if free(p, x, y, z):
                p.set(x, y, z, block)
        if p.blocks.get((x, top, z), ("",))[0].startswith("Soil_Grass"):
            grass_cells.append((x, top, z))
        if (edge or bottom <= min(bottoms.values()) + 2) and hash01(x, bottom, z, seed + 21) < hang:
            vine = HANGING[int(hash01(x, z, 3, seed) * len(HANGING))]
            for k in range(1 + int(hash01(z, x, bottom, seed + 22) * 4)):
                if free(p, x, bottom - 1 - k, z):
                    p.set(x, bottom - 1 - k, z, vine)
    return grass_cells
