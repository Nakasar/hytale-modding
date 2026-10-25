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
    "autumn": ("Wood_Maple_Trunk", "Plant_Leaves_Autumn"),
    "amber": ("Wood_Amber_Trunk", "Plant_Leaves_Amber"),
    "fir": ("Wood_Fir_Trunk", "Plant_Leaves_Fir"),
    "fir_snow": ("Wood_Fir_Trunk", "Plant_Leaves_Fir_Snow"),
    "cedar": ("Wood_Cedar_Trunk", "Plant_Leaves_Cedar"),
    "wisteria": ("Wood_Wisteria_Wild_Trunk", "Plant_Leaves_Wisteria_Wild"),
    "azure": ("Wood_Azure_Trunk", "Plant_Leaves_Azure"),
    "sallow": ("Wood_Sallow_Trunk", "Plant_Leaves_Sallow"),
    "windwillow": ("Wood_Windwillow_Trunk", "Plant_Leaves_Windwillow"),
    "banyan": ("Wood_Banyan_Trunk", "Plant_Leaves_Banyan"),
    "poisoned": ("Wood_Poisoned_Trunk", "Plant_Leaves_Poisoned"),
    "burnt": ("Wood_Burnt_Trunk", "Plant_Leaves_Burnt"),
    "ash": ("Wood_Ash_Trunk", "Plant_Leaves_Ash"),
    "petrified": ("Wood_Petrified_Trunk", "Plant_Leaves_Petrified"),
    "crystal": ("Wood_Crystal_Trunk", "Plant_Leaves_Crystal"),
}


def free(p, x, y, z):
    return (x, y, z) not in p.blocks


# --- arbres -------------------------------------------------------------------------------------------

def broadleaf(p, x, y, z, height, kind="oak", seed=0, droop=0.0, hanging=None):
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
    if droop:
        # Saule : des lianes pendent sous le houppier.
        hanging = hanging or HANGING
        for dx in range(-span, span + 1):
            for dz in range(-span, span + 1):
                for dy in range(-3, span):
                    at = (x + dx, top + dy, z + dz)
                    if p.blocks.get(at, ("",))[0] != leaves or not free(p, at[0], at[1] - 1, at[2]):
                        continue
                    if hash01(*at, seed + 31) < droop:
                        for k in range(1 + int(hash01(at[2], at[0], at[1], seed + 32) * 5)):
                            if not free(p, at[0], at[1] - 1 - k, at[2]) or at[1] - 1 - k <= y:
                                break
                            p.set(at[0], at[1] - 1 - k, at[2], hanging[int(hash01(at[0], k, at[2], seed) * len(hanging))])


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


def boulder(p, x, y, z, r, seed=0, rocks=None):
    """Rocher moussu à moitié enterré (centre en y - 1)."""
    n = int(math.ceil(r)) + 1
    for dx in range(-n, n + 1):
        for dz in range(-n, n + 1):
            for dy in range(-1, n + 1):
                d = math.sqrt(dx * dx + (dy * 1.4) ** 2 + dz * dz)
                if d <= r + 0.5 * vnoise3(x + dx, y + dy, z + dz, 1.6, seed):
                    top = dy >= r * 0.4
                    pool = rocks or ROCKS
                    p.set(x + dx, y - 1 + dy, z + dz,
                          pool[1] if top and hash01(x + dx, dy, z + dz, seed) < 0.6 else pool[
                              int(hash01(dx, y, dz, seed + 1) * len(pool))])


def flora(p, cells, seed=0, density=0.55, flowers=0.16, theme=None):
    """Herbes et fleurs sur les cases d'herbe `cells` [(x, y_sol, z)] : herbe courte partout, haute par endroits,
    massifs de fleurs d'une couleur selon le bruit. Ne pose que sur l'air. `theme` : palettes d'un décor (THEMES)."""
    t = theme or THEMES["meadow"]
    GRASS_SHORT, GRASS_TALL, FLOWER_PATCHES = t["short"], t["tall"], t["flowers"]
    for x, y, z in cells:
        if not free(p, x, y + 1, z):
            continue
        h = hash01(x, y, z, seed)
        patch = fbm2(x, z, 9, 2, seed + 3)
        if FLOWER_PATCHES and patch > 0.25 and h < flowers + (patch - 0.25):
            colors = FLOWER_PATCHES[int((fbm2(x, z, 23, 1, seed + 5) + 1) / 2 * len(FLOWER_PATCHES)) % len(FLOWER_PATCHES)]
            p.set(x, y + 1, z, colors[int(hash01(z, x, y, seed + 6) * len(colors))])
        elif h < density:
            tall = fbm2(x, z, 6, 2, seed + 11) > 0.2
            pool = GRASS_TALL if tall else GRASS_SHORT
            p.set(x, y + 1, z, pool[int(hash01(x, z, y, seed + 12) * len(pool))])


# --- îles flottantes ----------------------------------------------------------------------------------

def island(p, tops, depth_of, seed=0, grass=None, hang=0.12, theme=None):
    """Île flottante : `tops` {(x, z): y_sol} (dessus du sol), `depth_of(x, z)` profondeur du dessous. Écrit le sol
    (herbe), trois couches de terre puis la roche, seulement là où la roche se voit (bords, dessous), et laisse
    pendre quelques lianes sous les bords. Ne touche pas aux cases déjà prises (un dessus existant garde son bloc :
    on peut ainsi donner un dessous rocheux à une plate-forme). Rend les cases de sol fertile [(x, y, z)] pour
    `flora`."""
    t = theme or THEMES["meadow"]
    bottoms = {}
    for (x, z), top in tops.items():
        bottoms[(x, z)] = top - max(2, int(depth_of(x, z)))
    grass_cells = []
    sides = ((1, 0), (-1, 0), (0, 1), (0, -1))
    low = min(bottoms.values()) if bottoms else 0
    for (x, z), top in tops.items():
        bottom = bottoms[(x, z)]
        edge = any((x + dx, z + dz) not in tops for dx, dz in sides)
        # plus haut fond voisin : en dessous, la roche se voit de côté
        side = max([bottoms[(x + dx, z + dz)] for dx, dz in sides if (x + dx, z + dz) in bottoms] or [top])
        # plus bas dessus voisin : au-dessus, la paroi se voit (relief)
        wall = min([tops[(x + dx, z + dz)] for dx, dz in sides if (x + dx, z + dz) in tops] or [top])
        fertile = False
        for y in range(bottom, top + 1):
            if not (edge or y <= bottom + 1 or y < side or y >= top - 3 or y > wall - 1):
                continue
            if y == top:
                block = grass(x, z) if grass else soil(x, z, seed, t["soil"])
            elif y >= top - 3:
                block = t["dirt"][int(hash01(x, y, z, seed) * len(t["dirt"]))]
            else:
                band = int((y + 3 * vnoise2(x, z, 11, seed)) // 3)
                block = t["deep"][band % len(t["deep"])]
            if free(p, x, y, z):
                p.set(x, y, z, block)
                fertile = fertile or (y == top and block in t["fertile"])
        if fertile:
            grass_cells.append((x, top, z))
        if t["hang"] and (edge or bottom <= low + 2) and hash01(x, bottom, z, seed + 21) < hang:
            vine = t["hang"][int(hash01(x, z, 3, seed) * len(t["hang"]))]
            for k in range(1 + int(hash01(z, x, bottom, seed + 22) * 4)):
                if free(p, x, bottom - 1 - k, z):
                    p.set(x, bottom - 1 - k, z, vine)
    return grass_cells


# --- décors (thèmes) ----------------------------------------------------------------------------------

def _theme(**kw):
    t = {"soil": GRASS_SOIL, "dirt": DIRT, "deep": DEEP, "short": GRASS_SHORT, "tall": GRASS_TALL,
         "flowers": FLOWER_PATCHES, "bushes": BUSHES, "hang": HANGING, "trees": ["oak", "birch", "beech", "maple"],
         "conifers": ["fir"], "tree": "broadleaf", "droop": 0.0, "rocks": ROCKS, "fertile": None}
    t.update(kw)
    if t["fertile"] is None:
        t["fertile"] = set(t["soil"])
    return t


MUSHROOMS = ["Plant_Crop_Mushroom_Common_Brown", "Plant_Crop_Mushroom_Cap_Brown", "Plant_Crop_Mushroom_Cap_Red",
             "Plant_Crop_Mushroom_Flatcap_Green"]
THEMES = {
    "meadow": _theme(),
    # Brumes : feuillages bleus et glycines, fleurs froides, cristaux.
    "mists": _theme(trees=["wisteria", "azure", "birch", "wisteria"], conifers=["fir"],
                    flowers=[FLOWER_PATCHES[1], FLOWER_PATCHES[2], FLOWER_PATCHES[3], FLOWER_PATCHES[4]],
                    bushes=["Plant_Bush_Lush", "Plant_Fern_Forest", "Plant_Bush_Crystal", "Plant_Fern"]),
    "volcanic": _theme(soil=["Soil_Ash", "Soil_Ash", "Soil_Grass_Burnt", "Soil_Dirt_Burnt"],
                       dirt=["Soil_Dirt_Burnt", "Rock_Volcanic", "Soil_Ash"],
                       deep=["Rock_Volcanic", "Rock_Basalt", "Rock_Volcanic", "Rock_Magma_Cooled"],
                       short=["Plant_Grass_Dry", "Plant_Grass_Dry", "Plant_Grass_Arid_Short"],
                       tall=["Plant_Grass_Dry_Tall", "Plant_Reeds_Lava", "Plant_Grass_Arid_Tall"],
                       flowers=[], bushes=["Plant_Bush_Dead", "Plant_Bramble_Dead_Lavathorn", "Plant_Bush_Dead_Twisted",
                                           "Plant_Bush_Dead_Tall"],
                       hang=[], trees=["burnt", "burnt", "ash"], conifers=[], tree="dead",
                       rocks=["Rock_Volcanic", "Rock_Basalt", "Rock_Magma_Cooled", "Rock_Volcanic_Cobble"]),
    "swamp": _theme(soil=["Soil_Grass_Wet", "Soil_Mud", "Soil_Grass_Wet", "Soil_Grass_Deep"],
                    dirt=["Soil_Mud", "Soil_Dirt", "Soil_Clay"],
                    deep=["Rock_Stone_Mossy", "Rock_Stone", "Rock_Shale", "Soil_Clay"],
                    short=["Plant_Grass_Wet_Short", "Plant_Grass_Wet", "Plant_Moss_Short_Green"],
                    tall=["Plant_Grass_Wet_Tall", "Plant_Reeds_Marsh", "Plant_Grass_Wet_Wild", "Plant_Grass_Wet_Overgrown"],
                    flowers=[MUSHROOMS, ["Plant_Crop_Mushroom_Glowing_Green", "Plant_Crop_Mushroom_Common_Lime"],
                             ["Plant_Reeds_Wet", "Plant_Reeds_Marsh"], ["Plant_Flower_Common_White", "Plant_Flower_Hemlock"]],
                    bushes=["Plant_Bush_Wet", "Plant_Fern_Wet_Big", "Plant_Fern", "Plant_Bush_Jungle"],
                    hang=["Plant_Vine_Hanging", "Plant_Vine_Green_Hanging"], trees=["sallow", "windwillow", "sallow"],
                    conifers=[], droop=0.18,
                    rocks=["Rock_Stone_Mossy", "Rock_Stone_Cobble_Mossy", "Rock_Stone", "Rock_Shale"]),
    # Tempête de neige : neige, sapins enneigés, glace et stalactites sous les îles.
    "snow": _theme(soil=["Soil_Snow"], dirt=["Soil_Snow", "Soil_Dirt", "Rock_Ice_Permafrost"],
                   deep=["Rock_Stone", "Rock_Ice_Permafrost", "Rock_Slate", "Rock_Stone"],
                   short=["Plant_Grass_Snowy_Short"], tall=["Plant_Grass_Snowy", "Plant_Grass_Snowy_Tall"],
                   flowers=[], bushes=["Plant_Bush_Winter_Snow"], hang=["Rock_Ice_Icicles"],
                   trees=["fir_snow"], conifers=["fir_snow", "fir_snow", "fir"], tree="conifer",
                   rocks=["Rock_Stone", "Rock_Ice", "Rock_Slate", "Rock_Ice_Permafrost"]),
    "jade": _theme(soil=["Soil_Sand_White", "Soil_Sand_White", "Soil_Gravel_Sand_White"],
                   dirt=["Soil_Clay_Ocean", "Soil_Sand_White"],
                   deep=["Soil_Clay_Ocean", "Rock_Aqua", "Soil_Clay_Ocean", "Rock_Crystal_Green_Block"],
                   short=["Plant_Coral_Bush_Green", "Plant_Coral_Bush_Cyan"],
                   tall=["Plant_Coral_Model_Green", "Plant_Coral_Bush_Lime"],
                   flowers=[["Plant_Coral_Bush_Pink", "Plant_Coral_Model_Pink"], ["Plant_Coral_Bush_Orange", "Plant_Coral_Model_Orange"],
                            ["Plant_Coral_Bush_Violet", "Plant_Coral_Model_Purple"], ["Plant_Coral_Bush_Yellow", "Plant_Coral_Model_Yellow"]],
                   bushes=["Rock_Crystal_Green_Medium", "Rock_Crystal_Cyan_Small", "Plant_Coral_Model_Cyan"],
                   hang=[], trees=["green", "cyan"], conifers=[], tree="crystal",
                   rocks=["Rock_Aqua", "Rock_Crystal_Green_Block", "Rock_Aqua", "Soil_Clay_Ocean"]),
}


def soil(x, z, seed=0, palette=None):
    """Sol du dessus : grandes plaques de teintes voisines."""
    palette = palette or GRASS_SOIL
    n = fbm2(x, z, 14, 2, seed)
    return palette[min(len(palette) - 1, int((n + 1) / 2 * len(palette)))]


def dead_tree(p, x, y, z, height, kind="burnt", seed=0, leaves=0.0):
    """Arbre mort : tronc et trois ou quatre branches de bois plein qui montent en biais (toujours accrochées),
    quelques touffes de feuilles brûlées au bout si `leaves`."""
    trunk, leaf = TREES[kind]
    for k in range(height):
        p.set(x, y + k, z, trunk)
    for b in range(3 + int(hash01(x, y, z, seed) * 2)):
        a = hash01(x, b, z, seed + 1) * math.tau
        cx, cy, cz = x, y + height - 1 - int(hash01(b, x, z, seed + 2) * (height // 2)), z
        for t in range(2 + int(hash01(z, b, x, seed + 3) * 3)):
            nx, nz = x + round(math.cos(a) * (t + 1)), z + round(math.sin(a) * (t + 1))
            if (nx, nz) != (cx, cz):
                p.set(nx, cy, nz, trunk)      # pas de côté, à la même hauteur : la branche reste accrochée
                cx, cz = nx, nz
            cy += 1
            p.set(cx, cy, cz, trunk)
        if leaves and hash01(cx, cy, cz, seed + 4) < leaves and free(p, cx, cy + 1, cz):
            p.set(cx, cy + 1, cz, leaf)


def crystal_spire(p, x, y, z, height, color="green", seed=0):
    """Aiguille de cristal : colonne qui s'affine, éclats sur les flancs, pointe en petit cristal."""
    block = f"Rock_Crystal_{color.capitalize()}_Block"
    for k in range(height):
        r = (1 - k / height) * (1.4 + height * 0.08)
        n = int(math.ceil(r))
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= r + 0.25 * vnoise2(x + dx + k, z + dz, 1.5, seed):
                    p.set(x + dx, y + k, z + dz, block)
    p.set(x, y + height, z, f"Rock_Crystal_{color.capitalize()}_Large")
    for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        if hash01(x + dx, y, z + dz, seed) < 0.5 and free(p, x + dx, y, z + dz):
            p.set(x + dx, y, z + dz, f"Rock_Crystal_{color.capitalize()}_Medium")


def giant_mushroom(p, x, y, z, height, color="Brown", seed=0):
    """Champignon géant : pied de bloc de champignon, chapeau en disque bombé."""
    for k in range(height):
        p.set(x, y + k, z, f"Plant_Crop_Mushroom_Block_{color}_Trunk")
    r = 2 + height // 3
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            d = math.hypot(dx, dz)
            if d <= r + 0.3:
                p.set(x + dx, y + height + (1 if d < r - 1 else 0), z + dz, f"Plant_Crop_Mushroom_Block_{color}")


def tree(p, x, y, z, theme, seed=0, scale=1.0):
    """Un arbre du thème (feuillu, résineux, mort ou cristal) dont le pied est en (x, y, z)."""
    t = theme
    h = hash01(x, z, y, seed)
    if t["tree"] == "dead":
        dead_tree(p, x, y, z, round((5 + int(h * 5)) * scale), t["trees"][int(h * 97) % len(t["trees"])], seed, leaves=0.4)
    elif t["tree"] == "crystal":
        crystal_spire(p, x, y, z, round((4 + int(h * 6)) * scale), t["trees"][int(h * 97) % len(t["trees"])], seed)
    elif t["tree"] == "conifer":
        conifer(p, x, y, z, round((7 + int(h * 9)) * scale), t["conifers"][int(h * 97) % len(t["conifers"])], seed)
    elif t["conifers"] and h < 0.2:
        conifer(p, x, y, z, round((8 + int(h * 25)) * scale), t["conifers"][0], seed)
    else:
        kind = t["trees"][int(hash01(z, x, y, seed + 1) * len(t["trees"]))]
        broadleaf(p, x, y, z, round((5 + int(hash01(x, y, z, seed + 2) * 4)) * scale), kind, seed,
                  droop=t["droop"], hanging=t["hang"] or None)


def dress(p, cells, theme, seed=0, trees=0.03, spacing=6, bushes=0.04, boulders=0.006, density=0.55, flowers=0.16,
          keep=()):
    """Habille des cases de sol `cells` [(x, y, z)] : arbres espacés (pas dans les boîtes `keep` (x0, x1, z0, z1)),
    buissons, rochers, puis herbes et fleurs sur ce qui reste à l'air libre."""
    t = theme
    placed = []
    for x, y, z in sorted(cells):
        if any(a <= x <= b and c <= z <= d for a, b, c, d in keep) or not free(p, x, y + 1, z):
            continue
        h = hash01(x, y, z, seed + 41)
        if h < trees and all(math.hypot(x - a, z - b) >= spacing for a, b in placed):
            placed.append((x, z))
            tree(p, x, y + 1, z, t, seed + x * 7 + z)
        elif h < trees + bushes and t["bushes"]:
            p.set(x, y + 1, z, t["bushes"][int(hash01(z, x, y, seed + 42) * len(t["bushes"]))])
        elif h < trees + bushes + boulders:
            boulder(p, x, y + 1, z, 0.9 + hash01(x, z, y, seed + 43) * 1.1, seed + x + z, rocks=t["rocks"])
    flora(p, cells, seed + 44, density, flowers, theme=t)
    return placed


def rim(footprint, rmin, rmax, seed=0, block=None):
    """Pourtour naturel autour d'une empreinte {(x, z): y_sol} : cases à moins de rmin..rmax (selon le bruit) de
    l'empreinte, hors de l'empreinte, au niveau de la case d'empreinte la plus proche. `block(x, z)` vrai : case
    interdite (garder un vide, un passage). Rend {(x, z): y_sol}."""
    from collections import deque
    near = {c: (c, 0.0) for c in footprint}
    queue = deque(footprint)
    out = {}
    while queue:
        c = queue.popleft()
        src, _ = near[c]
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            n = (c[0] + dx, c[1] + dz)
            if n in near:
                continue
            d = math.hypot(n[0] - src[0], n[1] - src[1])
            reach = rmin + (rmax - rmin) * (fbm2(n[0], n[1], 9, 2, seed) + 1) / 2
            if d > reach or (block and block(*n)):
                continue
            near[n] = (src, d)
            out[n] = footprint[src]
            queue.append(n)
    return out


def edge_distance(tops):
    """Distance (pas de 4 voisins) de chaque case de `tops` au vide."""
    from collections import deque
    dist, queue = {}, deque()
    for (x, z) in tops:
        if any((x + dx, z + dz) not in tops for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            dist[(x, z)] = 0
            queue.append((x, z))
    while queue:
        x, z = queue.popleft()
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, z + dz)
            if n in tops and n not in dist:
                dist[n] = dist[(x, z)] + 1
                queue.append(n)
    return dist


def natural_ground(p, tops, theme, seed=0, depth=(3, 1.2, 24), hang=0.14, **dress_kw):
    """Île naturelle complète : sol, dessous plus profond vers le centre, lianes, puis végétation (`dress`)."""
    edge = edge_distance(tops)
    base, slope, cap = depth
    cells = island(p, tops, lambda x, z: base + min(cap, edge[(x, z)] * slope) + 2 * fbm2(x, z, 6, 2, seed + 13),
                   seed, hang=hang, theme=theme)
    dress(p, cells, theme, seed, **dress_kw)
    return cells


def islet(p, cx, cz, top, r, theme, seed=0):
    """Îlot de décor au contour irrégulier, bombé au centre, avec un ou plusieurs arbres selon sa taille."""
    tops = {}
    n = int(r * 1.5) + 2
    for x in range(cx - n, cx + n + 1):
        for z in range(cz - n, cz + n + 1):
            d = math.hypot(x - cx, z - cz)
            if d <= r * (0.8 + 0.4 * (fbm2(x, z, 5, 2, seed) + 1) / 2):
                tops[(x, z)] = top + (1 if d < r * 0.4 and fbm2(x, z, 4, 1, seed + 1) > 0 else 0)
    edge = edge_distance(tops)
    cells = island(p, tops, lambda x, z: 2 + min(r * 1.6, edge[(x, z)] * 1.5) + 2 * fbm2(x, z, 4, 2, seed + 2),
                   seed, hang=0.2, theme=theme)
    dress(p, cells, theme, seed, trees=0.05 if r > 4 else 0.0, spacing=5, bushes=0.06, boulders=0.01)
    if 2.5 < r <= 4:
        # petit îlot : un arbre seul, près du centre
        inner = [c for c in cells if math.hypot(c[0] - cx, c[2] - cz) < r * 0.5 and free(p, c[0], c[1] + 1, c[2])]
        if inner:
            c = inner[int(hash01(cx, cz, 0, seed) * len(inner))]
            tree(p, c[0], c[1] + 1, c[2], theme, seed, scale=0.8)
    return cells


def scatter_islets(p, area, count, y_range, r_range, theme, seed=0, margin=14):
    """Îlots de décor dans `area` (x0, x1, z0, z1), loin (`margin`) de tout ce que le prefab contient déjà : jamais
    un raccourci pour le parcours."""
    taken = {}
    for (x, y, z) in p.blocks:
        taken.setdefault((x // 4, z // 4), True)
    x0, x1, z0, z1 = area
    done, tries = [], 0
    while len(done) < count and tries < count * 40:
        tries += 1
        cx = x0 + int(hash01(tries, 1, 0, seed) * (x1 - x0))
        cz = z0 + int(hash01(tries, 2, 0, seed) * (z1 - z0))
        r = r_range[0] + hash01(tries, 3, 0, seed) * (r_range[1] - r_range[0])
        reach = int(r * 1.3) + margin
        if any((gx, gz) in taken for gx in range((cx - reach) // 4, (cx + reach) // 4 + 1)
               for gz in range((cz - reach) // 4, (cz + reach) // 4 + 1)):
            continue
        if any(math.hypot(cx - a, cz - b) < r + rb + 8 for a, b, rb in done):
            continue
        top = y_range[0] + int(hash01(tries, 4, 0, seed) * (y_range[1] - y_range[0]))
        islet(p, cx, cz, top, r, theme, seed + tries)
        done.append((cx, cz, r))
    return done


# --- aperçus ------------------------------------------------------------------------------------------

_FLOWER_COLORS = {"Yellow": (240, 220, 60), "White": (240, 240, 240), "Blue": (90, 130, 240), "Purple": (170, 90, 220),
                  "Violet": (150, 80, 220), "Pink": (240, 140, 190), "Red": (220, 50, 50), "Orange": (240, 150, 50),
                  "Lime": (170, 230, 80), "Cyan": (80, 220, 220), "Green": (80, 200, 120)}


def nature_color(name):
    """Couleur d'aperçu des blocs naturels (plantes, sols, roches) ; None pour les autres."""
    if name.startswith(("Plant_Flower", "Plant_Coral")):
        return next((c for k, c in _FLOWER_COLORS.items() if k in name), (230, 230, 120))
    if name.startswith("Plant_Leaves"):
        return {"Wisteria": (200, 140, 230), "Azure": (90, 150, 230), "Burnt": (60, 50, 45), "Crystal": (150, 230, 240),
                "Fir": (40, 100, 40), "Cedar": (40, 100, 40), "Sallow": (110, 140, 60), "Windwillow": (120, 170, 90),
                "Autumn": (200, 84, 40), "Maple": (186, 62, 36), "Amber": (226, 150, 52)}.get(
            next((k for k in ("Wisteria", "Azure", "Burnt", "Crystal", "Fir", "Cedar", "Sallow", "Windwillow", "Autumn",
                              "Maple", "Amber") if k in name), ""),
            (60, 130, 50))
    if "Snow" in name:
        return (236, 242, 248)
    if name.startswith(("Rock_Ice", "Rubble_Ice")):
        return (170, 210, 240)
    if name.startswith("Rock_Crystal"):
        return next((c for k, c in _FLOWER_COLORS.items() if k in name), (200, 200, 255))
    if name.startswith("Plant_Crop_Mushroom"):
        return (200, 150, 110) if "Glowing" not in name else (120, 255, 160)
    if name.startswith(("Plant_Grass", "Plant_Bush", "Plant_Fern", "Plant_Reeds")):
        return (150, 130, 80) if any(k in name for k in ("Dry", "Dead", "Lava", "Arid")) else (100, 170, 70)
    if name.startswith(("Plant_Vine", "Plant_Moss", "Plant_Bramble")) or name.endswith("_Mossy"):
        return (70, 120, 60)
    if name.endswith("_Trunk"):
        return (50, 45, 40) if "Burnt" in name else (110, 80, 50)
    if name.startswith("Soil_Grass"):
        return (60, 50, 40) if "Burnt" in name else (80, 140, 60)
    if name.startswith("Soil_Clay") and ("Cyan" in name or "Green" in name or "Ocean" in name):
        return (70, 170, 150)
    if name.startswith(("Soil_Pathway", "Soil_Dirt", "Soil_Clay", "Soil_Mud")):
        return (150, 115, 75)
    if name.startswith("Soil_Sand"):
        return (230, 220, 190)
    if name.startswith(("Soil_Gravel", "Soil_Ash")):
        return (120, 120, 105) if "Ash" not in name else (90, 85, 85)
    if "Volcanic" in name or "Magma" in name:
        return (230, 90, 30) if "Lava" in name else (60, 55, 55)
    if name.startswith("Rock_Aqua"):
        return (90, 160, 170)
    if name in ("Rock_Stone", "Rock_Slate", "Rock_Shale", "Rock_Basalt", "Rock_Marble"):
        return {"Rock_Stone": (130, 130, 130), "Rock_Slate": (95, 100, 110), "Rock_Shale": (120, 110, 100),
                "Rock_Basalt": (70, 70, 80), "Rock_Marble": (220, 216, 210)}[name]
    return None
