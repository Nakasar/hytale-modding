"""Décor de l'Observatoire à la manière de l'Observatoire des Brumes de Guild Wars 2 (Kevin, 25 octobre 2026, quatre
captures du jeu) : îles flottantes de roche sombre aux dessous épais et abrupts, dessus d'herbe et de mousse, arbres
d'automne rouges et orangés, ponts de roche naturels en arc, grande porte asura en anneau de pierre au voile violet,
tours gothiques en ruine et aiguilles de roche à l'arrière-plan.

Ce module ne pose que des formes (île, pont, anneau, tour, aiguille, grand arbre) ; tools/generate_observatory.py les
place autour des blocs de jeu. Toutes les formes suivent le repère du prefab : x vers l'est, z vers le sud, le dessus
du sol en y = -1."""

import math

import fractal_nature as fn

AIR = "Empty"

# --- palettes ---------------------------------------------------------------------------------------------------

# Dessus moussu (herbe profonde, plaques de mousse), dessous de roche sombre gris-bleu comme les falaises de GW2.
SOIL = ["Soil_Grass_Deep", "Soil_Grass", "Soil_Grass_Deep", "Soil_Grass_Full", "Plant_Moss_Block_Green_Dark"]
DEEP = ["Rock_Slate", "Rock_Stone", "Rock_Slate", "Rock_Basalt", "Rock_Shale"]
ROCKS = ["Rock_Stone_Mossy", "Rock_Stone", "Rock_Stone_Cobble_Mossy", "Rock_Slate"]
AUTUMN_TREES = ["autumn", "maple", "amber", "autumn"]
# Tapis de feuilles mortes et de mousse au sol, rares fleurs chaudes.
LEAF_LITTER = ["Plant_Leaves_Autumn_Floor"]
THEME = fn._theme(
    soil=SOIL,
    fertile={"Soil_Grass_Deep", "Soil_Grass", "Soil_Grass_Full"},
    dirt=["Soil_Dirt", "Soil_Dirt", "Rock_Stone"],
    deep=DEEP,
    short=["Plant_Grass_Lush_Short", "Plant_Grass_Sharp_Short", "Plant_Moss_Short_Green", "Plant_Grass_Lush_Short"],
    tall=["Plant_Grass_Dry_Tall", "Plant_Grass_Lush_Tall", "Plant_Grass_Sharp_Wild", "Plant_Grass_Dry_Tall"],
    flowers=[LEAF_LITTER, ["Plant_Moss_Rug_Green", "Plant_Moss_Rug_Green_Dark"], LEAF_LITTER,
             ["Plant_Flower_Common_Orange", "Plant_Flower_Common_Yellow"]],
    bushes=["Plant_Bush_Winter_Red", "Plant_Fern_Forest", "Plant_Bush_Lush", "Plant_Bush_Arid_Red"],
    hang=["Plant_Vine_Hanging", "Plant_Vine_Red_Hanging"],
    trees=AUTUMN_TREES, conifers=[], rocks=ROCKS,
)
RUIN = ["Rock_Stone_Brick", "Rock_Stone_Brick", "Rock_Stone_Brick_Mossy", "Rock_Shale_Brick", "Rock_Stone_Brick"]
RUIN_TRIM = "Rock_Shale_Brick_Smooth"


def pick(options, x, y, z, seed=0):
    """Matière par plaques lisses (bruit), pas de damier."""
    n = fn.vnoise3(x, y, z, 4.5, len(options) * 7 + 3 + seed) * 0.75 + fn.vnoise3(x, y, z, 1.7, 5 + seed) * 0.25
    return options[min(len(options) - 1, int((n + 1) / 2 * len(options)))]


# --- empreintes -------------------------------------------------------------------------------------------------

def blob_footprint(blobs, seed, wobble=0.22, top=-1):
    """Union de taches rondes au bord bruité : `blobs` [(cx, cz, r)]. Rend {(x, z): y_sol}."""
    tops = {}
    for cx, cz, r in blobs:
        n = int(r * (1 + wobble)) + 2
        for x in range(cx - n, cx + n + 1):
            for z in range(cz - n, cz + n + 1):
                d = math.hypot(x - cx, z - cz)
                a = math.atan2(z - cz, x - cx)
                edge = r * (1 + wobble * fn.fbm2(math.cos(a) * 6 + cx, math.sin(a) * 6 + cz, 4, 2, seed))
                if d <= edge:
                    tops[(x, z)] = top
    return tops


def bezier(a, c, b, t):
    return ((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1])


def bridge_footprint(a, c, b, width, seed):
    """Pont de roche courbe (courbe de Bézier a → c → b) : rend ({(x, z): y_sol}, {(x, z): t}) où t (0 à 1) dit où la
    case tombe le long du pont (pour creuser l'arche dessous)."""
    length = math.hypot(c[0] - a[0], c[1] - a[1]) + math.hypot(b[0] - c[0], b[1] - c[1])
    tops, along = {}, {}
    steps = int(length * 4) + 2
    for k in range(steps + 1):
        t = k / steps
        x, z = bezier(a, c, b, t)
        half = width / 2 + 0.8 * fn.vnoise2(x, z, 3.5, seed)
        n = int(half) + 1
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= half:
                    cell = (round(x) + dx, round(z) + dz)
                    tops[cell] = -1
                    along[cell] = min(along.get(cell, 1.0), abs(2 * t - 1))
    return tops, along


def path_cells(points, width, seed):
    """Allée dallée qui suit la ligne brisée lissée `points` (pas de couloir droit) : rend {(x, z)}."""
    cells = set()
    for (ax, az), (bx, bz) in zip(points, points[1:]):
        steps = int(math.hypot(bx - ax, bz - az) * 3) + 1
        for k in range(steps + 1):
            t = k / steps
            x, z = ax + (bx - ax) * t, az + (bz - az) * t
            half = width / 2 + 0.6 * fn.vnoise2(x, z, 2.5, seed)
            n = int(half) + 1
            for dx in range(-n, n + 1):
                for dz in range(-n, n + 1):
                    if math.hypot(dx, dz) <= half:
                        cells.add((round(x) + dx, round(z) + dz))
    return cells


def smooth_line(points, passes=3):
    """Coins arrondis (Chaikin) : la ligne brisée devient une courbe."""
    for _ in range(passes):
        out = [points[0]]
        for (ax, az), (bx, bz) in zip(points, points[1:]):
            out.append((ax * 0.75 + bx * 0.25, az * 0.75 + bz * 0.25))
            out.append((ax * 0.25 + bx * 0.75, az * 0.25 + bz * 0.75))
        out.append(points[-1])
        points = out
    return points


# --- îles -------------------------------------------------------------------------------------------------------

def landmass(p, tops, depth_of, seed, hang=0.16):
    """Sol, terre et dessous de roche sombre (`depth_of(x, z)` blocs sous le dessus) ; rend les cases d'herbe."""
    return fn.island(p, tops, depth_of, seed, hang=hang, theme=THEME)


def cliff_depth(tops, base, slope, cap, seed, extra=None):
    """Profondeur de falaise de GW2 : déjà épaisse au bord (paroi abrupte), plus profonde vers le centre, en dents
    irrégulières dessous. `extra(x, z)` ajoute ou retire des blocs (arches des ponts)."""
    edge = fn.edge_distance(tops)

    def depth(x, z):
        d = base + min(cap, edge[(x, z)] * slope) + 3 * fn.fbm2(x, z, 7, 2, seed + 13)
        d += 4 * max(0.0, fn.vnoise2(x, z, 3, seed + 17))      # pointes rocheuses sous l'île
        if extra:
            d = extra(x, z, d)
        return max(2, d)
    return depth


def floating_rock(p, cx, cz, top, r, seed, depth=(10, 1.8, 46), trees=0.04, bare=False):
    """Grand rocher flottant d'arrière-plan : dessus moussu (ou nu), paroi abrupte, quelques arbres d'automne."""
    tops = {c: top for c in blob_footprint([(cx, cz, r)], seed, wobble=0.3)}
    for (x, z) in list(tops):
        tops[(x, z)] = top + (1 if fn.fbm2(x, z, 6, 2, seed + 3) > 0.35 else 0)
    cells = landmass(p, tops, cliff_depth(tops, *depth, seed), seed)
    if not bare:
        fn.dress(p, cells, THEME, seed, trees=trees, spacing=6, bushes=0.05, boulders=0.01, density=0.5, flowers=0.2)
    return tops


# --- arbres -----------------------------------------------------------------------------------------------------

def great_tree(p, x, y, z, height, seed, leaves="Plant_Leaves_Autumn", trunk="Wood_Maple_Trunk"):
    """Grand arbre noueux comme ceux des captures : tronc épais qui penche, longues branches presque horizontales,
    feuillage en nappes aplaties au bout des branches."""
    lean = (fn.hash01(x, z, 1, seed) - 0.5) * 0.5, (fn.hash01(z, x, 2, seed) - 0.5) * 0.5
    cx, cz = float(x), float(z)
    for k in range(height):
        cx += lean[0]
        cz += lean[1]
        thick = 1 if k < height * 0.6 else 0
        for dx in range(0, thick + 1):
            for dz in range(0, thick + 1):
                p.set(round(cx) + dx, y + k, round(cz) + dz, trunk)
    # racines au pied
    for dx, dz in ((-1, 0), (2, 0), (0, -1), (0, 2), (-1, 1), (2, 1)):
        if fn.hash01(x + dx, y, z + dz, seed + 3) < 0.7:
            p.set(x + dx, y, z + dz, trunk)
    top = (round(cx), y + height - 1, round(cz))
    branches = 4 + int(fn.hash01(x, y, z, seed + 4) * 2)
    pads = []
    for b in range(branches):
        a = (b + fn.hash01(b, x, z, seed + 5) * 0.6) / branches * math.tau
        length = 5 + int(fn.hash01(z, b, x, seed + 6) * 5)
        start = top[1] - int(fn.hash01(x, b, z, seed + 7) * height * 0.35)
        bx, by, bz = float(top[0]), float(start), float(top[2])
        for t in range(length):
            nx, nz = bx + math.cos(a), bz + math.sin(a)
            ny = by + (0.45 if t < length * 0.6 else 0.15)
            for yy in range(round(by), round(ny) + 1):
                p.set(round(nx), yy, round(nz), trunk)        # marches pleines : la branche reste accrochée
            bx, by, bz = nx, ny, nz
        pads.append((round(bx), round(by) + 1, round(bz), 2.6 + fn.hash01(b, z, x, seed + 8) * 1.6))
    pads.append((top[0], top[1] + 2, top[2], 3.2))
    for px, py, pz, r in pads:
        n = int(r) + 2
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                for dy in range(-2, 3):
                    d = math.sqrt(dx * dx + (dy * 2.0) ** 2 + dz * dz)
                    if d <= r + 0.6 * fn.vnoise3(px + dx, py + dy, pz + dz, 2.1, seed + 9) and \
                            fn.free(p, px + dx, py + dy, pz + dz):
                        p.set(px + dx, py + dy, pz + dz, leaves)
    return pads


def autumn_tree(p, x, y, z, seed, scale=1.0):
    kind = AUTUMN_TREES[int(fn.hash01(x, z, y, seed) * len(AUTUMN_TREES))]
    fn.broadleaf(p, x, y, z, round((5 + int(fn.hash01(x, y, z, seed + 2) * 4)) * scale), kind, seed)


# --- porte asura ------------------------------------------------------------------------------------------------

# Pierre de la porte : briques de schiste vanilla et leurs escaliers et demi-blocs, qui lissent le cercle au
# demi-bloc près (au lieu des marches d'un anneau en blocs pleins). Rotations vues dans les prefabs vanilla de
# Assets.zip 0.7.2 (rotation = quart de tour + 4 × bascule) : escalier 0-3 dos vers -z, -x, +z, +x, renversé 8-11
# dos vers +z, +x, -z, -x ; demi-bloc 0 en bas, 8 en haut, 5 côté -x, 7 côté +x.
GATE_BODY = "Rock_Shale_Brick"
GATE_RIM = "Rock_Shale_Brick_Ornate"
GATE_KEY = "Rock_Shale_Brick_Decorative"
GATE_STAIRS = "Rock_Shale_Brick_Stairs"
GATE_HALF = "Rock_Shale_Brick_Half"
GATE_INSET = "Rock_Crystal_Purple_Block"
# Quarts d'une case dans le plan de l'anneau : 0 bas -x, 1 bas +x, 2 haut -x, 3 haut +x.
GATE_SHAPES = [
    (frozenset(), None, 0),
    (frozenset({0, 1, 2, 3}), "full", 0),
    (frozenset({0, 1}), GATE_HALF, 0), (frozenset({2, 3}), GATE_HALF, 8),
    (frozenset({0, 2}), GATE_HALF, 5), (frozenset({1, 3}), GATE_HALF, 7),
    (frozenset({0, 1, 3}), GATE_STAIRS, 3), (frozenset({0, 1, 2}), GATE_STAIRS, 1),
    (frozenset({1, 2, 3}), GATE_STAIRS, 9), (frozenset({0, 2, 3}), GATE_STAIRS, 11),
]


def gate_solid(px, py, cy, inner, outer, layer):
    """Pierre de l'anneau au point (px, py) du plan de la porte (px depuis l'axe, py en hauteur) : anneau de rayons
    `inner` à `outer` avec une clé de voûte en bosse au sommet, posé au sol sur deux pieds évasés. Les faces avant et
    arrière (layer 1) sont en retrait d'un demi-bloc, ce qui arrondit le profil."""
    d = math.hypot(px, py - cy)
    theta = math.atan2(py - cy, px)
    ro = outer + 0.9 * max(0.0, math.sin(theta)) ** 60 - 0.5 * layer
    if inner + 0.5 * layer < d <= ro:
        return True
    foot = py < 2.6 - 0.4 * layer and abs(px) <= 6.4 - 1.3 * py - 0.5 * layer
    return foot and d > inner + 0.5 * layer


def gate_shape(x, y, cy, inner, outer, layer):
    """Forme de la case (x, y) (x depuis l'axe, case [x-½, x+½] × [y, y+1]) : celle des GATE_SHAPES la plus proche
    du remplissage de ses quatre quarts (16 points chacun)."""
    cover = []
    for q in range(4):
        qx, qy = (q % 2) * 0.5 - 0.5, (q // 2) * 0.5
        n = sum(gate_solid(x + qx + (i + 0.5) / 8, y + qy + (j + 0.5) / 8, cy, inner, outer, layer)
                for i in range(4) for j in range(4))
        cover.append(n / 16)
    return min(GATE_SHAPES, key=lambda s: (sum(abs(cover[q] - (q in s[0])) for q in range(4)), len(s[0]) % 4 != 0))


def asura_gate(p, gx, gz, cy, inner, outer, veil, heart):
    """Grande porte asura : anneau vertical entier (plan x-y, épaisseur 3 en z) centré en (gx, cy, gz), posé au sol sur
    deux pieds évasés, contours lissés par escaliers et demi-blocs, faces avant et arrière en retrait, pierres de
    cristal violet serties au bord intérieur, clé de voûte et cristaux vanilla. Une estrade en demi-marches monte de
    chaque côté jusqu'au bas de l'ouverture (on n'a jamais à sauter). Le disque intérieur du plan du milieu est rempli
    du voile `veil` (invisible, traversable), sa case centrale du bloc `heart` qui porte le tourbillon de particules.
    Rend les cases du voile."""
    veil_cells = []
    n = int(outer) + 2
    for x in range(gx - n, gx + n + 1):
        for y in range(0, math.ceil(cy + outer) + 2):
            for z in (gz - 1, gz, gz + 1):
                layer = abs(z - gz)
                quarters, block, rot = gate_shape(x - gx, y, cy, inner, outer, layer)
                d = math.hypot(x - gx, y + 0.5 - cy)
                if block is None:
                    if d < inner + 1:
                        if layer == 0:
                            p.set(x, y, z, heart if (x, y) == (gx, math.floor(cy)) else veil)
                            veil_cells.append((x, y, z))
                        else:
                            p.set(x, y, z, AIR)
                    continue
                if block == "full":
                    ang = math.degrees(math.atan2(y + 0.5 - cy, x - gx)) % 360
                    block = GATE_BODY
                    if d < inner + 1.0 + 0.5 * layer:
                        block = GATE_RIM
                        if layer == 0 and abs(ang - round(ang / 30) * 30) < 6 and not 225 < ang < 315:
                            block = GATE_INSET
                    elif abs(ang - 90) < 7:
                        block = GATE_KEY
                p.set(x, y, z, block, rot)
    # estrade : demi-marches de 0,5 bloc jusqu'au seuil (bas de l'ouverture, plan du milieu)
    sill = math.floor(cy - inner)
    while gate_shape(0, sill, cy, inner, outer, 0)[1] is not None:
        sill += 1
    for side in (-1, 1):
        for k in range(1, 2 * sill + 2):
            h = sill - k * 0.5                    # hauteur du dessus de la marche k
            z = gz + side * (1 + k)
            if h <= 0:
                break
            for x in range(gx - 2, gx + 3):
                for y in range(0, math.floor(h)):
                    p.set(x, y, z, GATE_BODY if abs(x - gx) < 2 else GATE_RIM)
                if h % 1:
                    p.set(x, math.floor(h), z, GATE_HALF, 0)
    # cristaux vanilla : couronne au sommet, gerbe sur chaque pied
    crest = max(y for (x, y, z), (b, _) in p.blocks.items() if x == gx and z == gz and b != AIR)
    p.set(gx, crest + 1, gz, "Rock_Crystal_Purple_Large")
    for side in (-1, 1):
        x = gx + side * 4
        y = max(y for y in range(0, 4) if p.blocks.get((x, y, gz), (AIR,))[0] in (GATE_BODY, GATE_RIM))
        p.set(x, y + 1, gz, "Rock_Crystal_Purple_Medium")
        p.set(x, y + 1, gz - 1, "Rock_Crystal_Blue_Small")
    return veil_cells


# --- ruines et aiguilles ----------------------------------------------------------------------------------------

def gothic_tower(p, cx, cz, y0, height, half, seed):
    """Tour gothique en ruine : plan carré creux à contreforts d'angle, fenêtres en arc brisé sur chaque face tous
    les 8 blocs, planchers effondrés, sommet cassé en dents irrégulières."""
    for x in range(cx - half - 1, cx + half + 2):
        for z in range(cz - half - 1, cz + half + 2):
            ex, ez = abs(x - cx), abs(z - cz)
            corner = ex >= half and ez >= half
            buttress = ex == half + 1 or ez == half + 1
            wall = ex == half or ez == half
            if buttress and not (ex >= half and ez >= half):
                continue
            if not (wall or corner or buttress):
                # planchers effondrés tous les 10 blocs
                for fy in range(y0 + 10, y0 + height - 6, 10):
                    if fn.hash01(x, fy, z, seed + 1) < 0.45:
                        p.set(x, fy, z, RUIN_TRIM)
                continue
            broken = height - int((fn.fbm2(x * 1.3, z * 1.3, 3, 2, seed) + 1) / 2 * height * 0.45)
            if corner:
                broken = min(height + 3, broken + 5)            # les angles tiennent mieux : pinacles
            for y in range(y0, y0 + broken):
                h = y - y0
                u = (x - cx) if ez == half else (z - cz)
                if wall and not corner and 4 <= h and abs(u) <= half - 2:
                    k = (h - 4) % 8
                    width = 1 if k < 4 else (0 if k == 4 else -1)
                    if abs(u) <= width:
                        continue                                  # fenêtre en arc brisé
                block = RUIN_TRIM if h % 8 == 0 else pick(RUIN, x, y, z, seed)
                p.set(x, y, z, block)
    # chapiteaux en saillie sur les pinacles d'angle
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = cx + sx * half, cz + sz * half
            top = max((y for (bx, y, bz) in p.blocks if bx == x and bz == z and y >= y0), default=y0)
            p.set(x, top + 1, z, "Rock_Stone_Brick_Pillar_Base")


def ruined_facade(p, x0, x1, z, y0, height, seed, arch_every=7):
    """Pan de mur gothique en ruine (le long de x) percé de grandes arcades brisées, haut irrégulier."""
    for x in range(x0, x1 + 1):
        top = height - int((fn.fbm2(x, z, 4, 2, seed) + 1) / 2 * height * 0.6)
        u = (x - x0) % arch_every
        for y in range(y0, y0 + top):
            h = y - y0
            half = arch_every // 2
            dist = abs(u - half)
            if 0 < u < arch_every - 0 and dist <= half - 1 and h < height * 0.55 + (half - 1 - dist) * 1.2:
                continue
            for dz in (0, 1):
                p.set(x, y, z + dz, RUIN_TRIM if h == 0 else pick(RUIN, x, y, z, seed))


def rock_spire(p, cx, cz, y0, height, r0, seed):
    """Aiguille de roche : colonne qui s'affine et penche un peu, bandes de roche sombre, sommet moussu."""
    lean = ((fn.hash01(cx, cz, 1, seed) - 0.5) * 0.3, (fn.hash01(cz, cx, 2, seed) - 0.5) * 0.3)
    for k in range(height):
        t = k / height
        r = r0 * (1 - t) ** 0.75 + 0.7
        ox, oz = cx + lean[0] * k, cz + lean[1] * k
        n = int(r) + 2
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                x, z = round(ox) + dx, round(oz) + dz
                if math.hypot(x - ox, z - oz) <= r + 0.6 * fn.vnoise3(x, y0 + k, z, 2.5, seed):
                    band = int((y0 + k + 3 * fn.vnoise2(x, z, 9, seed)) // 4)
                    block = DEEP[band % len(DEEP)]
                    if t > 0.85 and fn.hash01(x, k, z, seed) < 0.5:
                        block = "Rock_Stone_Mossy"
                    p.set(x, y0 + k, z, block)
