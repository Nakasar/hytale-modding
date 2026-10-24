#!/usr/bin/env python3
"""Génère le Volcanique (Volcanic), troisième fractale de la saison 1 (étape 6 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_volcanic.py [--preview DOSSIER]

Le déroulé de GW2, dans l'ordre :

1. le camp des grawls : des groupes de 7 grawls qui chargent, autour du totem du rituel (sa vie, fixée par le Java,
   montre ce qu'il reste à abattre ; sa barre se voit de toute la fractale), des rochers qui tombent du volcan ;
2. le couloir aux rochers, galerie courbe qui descend : des rochers en feu dévalent la pente derrière les joueurs
   toutes les 5 s, on s'abrite dans les niches ; un rocher coûte 60 % des PV, brûle et laisse une traînée de feu ;
   toute la fractale descend peu à peu, du camp au lac de lave (galeries naturelles courbes, Kevin 2026-10-24) ;
3. le Champion chaman des grawls, au bord d'une falaise au-dessus du lac de lave du volcan : huit charges de
   protection que seules les pierres imprégnées (lâchées par les rochers qui tombent, ramassées accroupi et gardées en
   main) retirent ; ses vétérans sortent des grottes du sud et marchent lentement vers les trois captifs du bord nord ;
   pierres seulement tant qu'il est protégé, vétérans seulement dans la première phase de protection, une charge de
   protection reprise à 50 % ;
4. la mine : des rails sur des planches au-dessus de la lave, des chauves-souris ; une chute ramène au départ du
   tronçon ; au bout, une descente jusqu'au lac ;
5. le Chamane imprégné, sur une île au milieu du lac (on la voit du bord de la falaise du Champion) : petits cratères
   qui rougissent puis crachent de la lave, flèche enflammée qui se propage, piqué, souffle des ailes, tempête de feu ;
   à chaque quart de sa vie, un bouclier de 50 coups, des larves de braise, et il plane lentement vers un villageois
   pour s'en nourrir.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Volcanic`, la pierre imprégnée
(clic droit : la lancer), les effets, la cause de dégâts du feu, les particules, les modèles et rôles, les blocs des
cratères, la langue `nakasar_fractals_volcanic.lang` et `volcanic/VolcanicLayout.java`. Repère comme la Falaise :
y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
"""
import math
import sys
from pathlib import Path

import fractal_common as fc
import fractal_models as fm
import fractal_nature as fn
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

LANG = "nakasar_fractals_volcanic"
GENERATOR = "generate_volcanic.py"
INSTANCE = "Nakasar_Fractal_Volcanic"
WEATHER = "Nakasar_Fractal_Weather_Volcanic"
PREFAB_DIR = "Volcanic"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/volcanic/VolcanicLayout.java"
INTERACTIONS = go.INTERACTIONS / "Volcanic"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/Volcanic"
GROUND_Y = fc.GROUND_Y

# --- lieux (y = debout à) ---------------------------------------------------------------------------
SPAWN = (0, 0, 26)
CAMP = (-20, 20, -20, 32)               # x0, x1, z0, z1
TOTEM_AT = (0.5, 0, -5.5)
CAMP_SPAWNS = [(-14, -12), (14, -12), (-16, 8), (16, 8), (0, -16), (-8, 0), (8, 0)]
GATE_CAMP = [(x, y, -21) for x in range(-3, 4) for y in range(0, 5)]
# Galeries naturelles courbes qui descendent peu à peu, du camp (debout à 0) au lac (Kevin, 2026-10-24) : points de
# passage (x, z, debout) d'une courbe lissée ; le sol descend d'un bloc à la fois, jamais plus d'un bloc par 5 blocs.
# Couloir aux rochers : du camp au palier nord ; les rochers dévalent la pente depuis la bouche du haut (au sud).
CORRIDOR_PATH = [(0, -22, 0), (1, -31, 0), (8, -43, -2), (8, -56, -3), (0, -66, -5), (-7, -77, -6), (-6, -89, -8),
                 (-4, -97, -9)]
CORRIDOR_HALF = 3.5                     # demi-largeur de la voie (le rocher la balaie toute)
ALCOVE_EVERY = 11                       # une niche tous les 11 blocs de couloir, d'un côté puis de l'autre
LANDING_N = (-4, -98, 5, -9)            # palier nord : centre x, z, rayon, debout
PASSAGE_PATH = [(-4, -98, -9), (-10, -104, -10), (-17, -100, -12), (-22, -95, -13)]
GALLERY_HALF = 3.0
CH_CENTER = (-34, -94)
CH_RADIUS = 14
CH_STAND = -13
CAPTIVE_ANGLES = [240, 270, 300]       # au nord, au bord de la falaise qui tombe dans la lave du volcan
CAPTIVE_RADIUS = 12
VETERAN_GATES = [(-41, -80), (-27, -80)]   # grottes du côté sud, en face des captifs
GATE_CH = [(-49, CH_STAND + y, z) for y in range(0, 5) for z in range(-96, -91)]
# Mine : galerie courbe d'est en ouest, rails sur planches au-dessus d'une coulée de lave qui descend avec eux.
MINE = (-118, -50)                      # x de fin (ouest) et de départ (est) de la mine
MINE_CURVE = [(-50, -94), (-64, -91), (-80, -97), (-96, -92), (-110, -96), (-118, -94)]   # (x, z) du milieu
MINE_HALF = 6                           # demi-largeur de la coulée de lave
MINE_DROP = 7                           # la lave, 7 blocs sous les rails
END_PAD = (-124, -116, -98, -90)        # x0, x1, z0, z1, debout à PAD_STAND
PAD_STAND = -21
# Lac de lave du volcan, en bas de la falaise du Champion : surface en LAKE_Y, union de disques (centre x, z, rayon).
LAKE_Y = -36
LAKE_DISCS = [(-84, -146, 40), (-38, -124, 20), (-122, -122, 16)]
# Île du Chamane imprégné au milieu du lac, deux blocs au-dessus de la lave ; on la voit du bord de la falaise.
AR_CENTER = (-84, -146)
AR_RADIUS = 22
AR_STAND = LAKE_Y + 3
VILLAGER_ANGLES = [45, 135, 225, 315]
VILLAGER_RADIUS = 19
ENTRY_ANGLE = 180
# Descente du bout de la mine à l'île : (x, z, debout) ; chaussée au-dessus de la lave en bas.
DESCENT = [(-120, -99, PAD_STAND), (-122, -114, PAD_STAND - 4), (-114, -132, PAD_STAND - 8), (-105, -146, AR_STAND)]
DESCENT_WIDTH = 2.6
# Petits cratères de l'île (rayon CRATER_RADIUS) : chauffent puis deviennent de la lave active (Java).
CRATER_RADIUS = 2.3
CRATER_COUNT = 11
CRATER_STAGES = ["Nakasar_Fractal_Crater_Cold", "Nakasar_Fractal_Crater_Warm_1", "Nakasar_Fractal_Crater_Warm_2",
                 "Nakasar_Fractal_Crater_Warm_3", "Nakasar_Fractal_Crater_Lava"]
REWARD_AT = (-86, AR_STAND, -146)
END_EXIT_AT = (-82, AR_STAND, -146)

# --- blocs et rôles -------------------------------------------------------------------------------------
LANDING = gc.LANDING
MIST = gc.MIST_BARRIER
STONE = "Nakasar_Fractal_Imbued_Stone"
WARRIOR = "Nakasar_Fractal_Grawl_Warrior"
GRAWL_SHAMAN = "Nakasar_Fractal_Grawl_Shaman"
TOTEM = "Nakasar_Fractal_Grawl_Totem"
VETERAN = "Nakasar_Fractal_Grawl_Veteran"
CHAMPION = "Nakasar_Fractal_Champion_Shaman"
CAPTIVE = "Nakasar_Fractal_Captive"
BAT = "Nakasar_Fractal_Cave_Bat"
IMBUED = "Nakasar_Fractal_Imbued_Shaman"
LARVA = "Nakasar_Fractal_Ember_Larva"
FOE_ROLES = [WARRIOR, GRAWL_SHAMAN, TOTEM, VETERAN, CHAMPION, BAT, IMBUED, LARVA]

ROCK = ["Rock_Volcanic", "Rock_Volcanic", "Rock_Volcanic_Cobble", "Rock_Basalt"]
GROUND = ["Soil_Ash", "Soil_Ash", "Rock_Volcanic_Cobble", "Rock_Magma_Cooled"]
BRICK = ["Rock_Volcanic_Brick", "Rock_Volcanic_Brick_Smooth"]
LAVA = "Rock_Volcanic_Cracked_Lava"
LAVA_FLUID = "Lava_Source"              # vraie lave vanilla (fluide des prefabs de grottes volcaniques), lac de l'île
EMBER = "Rock_Volcanic_Cracked_Incandescent"
CAVE_ROCK = ["Rock_Basalt", "Rock_Volcanic", "Rock_Basalt_Cobble", "Rock_Volcanic", "Rock_Magma_Cooled"]
PLANKS = "Wood_Darkwood_Planks"
BEAM = "Wood_Darkwood_Beam"
pick = fc.pick
CAMP_SIGHT = 56                          # les grawls du camp voient tout le camp (40 x 52)


def ring_point(center, radius, angle, rounded=True):
    x = center[0] + math.cos(math.radians(angle)) * radius
    z = center[1] + math.sin(math.radians(angle)) * radius
    return (round(x), round(z)) if rounded else (round(x, 1), round(z, 1))


def smooth_path(points, step=1.0):
    """Courbe lissée (Catmull-Rom) par les points (x, z, debout) : échantillons (x, z, debout) tous les `step` blocs ;
    le debout descend linéairement entre deux points, arrondi : des marches d'un bloc."""
    dense = []
    pts = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(40):
            t = k / 40
            t2, t3 = t * t, t * t * t
            x, z = (0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                           + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1))
            dense.append((x, z, p1[2] + (p2[2] - p1[2]) * t))
    dense.append(tuple(points[-1]))
    out, run = [dense[0]], 0.0
    for (x0, z0, _), (x1, z1, s1) in zip(dense, dense[1:]):
        run += math.hypot(x1 - x0, z1 - z0)
        if run >= step:
            out.append((x1, z1, s1))
            run = 0.0
    if out[-1] != dense[-1]:
        out.append(dense[-1])
    return [(x, z, round(stand)) for x, z, stand in out]


def path_cells(samples, half, seed):
    """{(x, z): (debout, i, distance)} des cases à moins de `half` (± bruit) de la courbe : le sol suit l'échantillon le
    plus proche."""
    xs = [x for x, _, _ in samples]
    zs = [z for _, z, _ in samples]
    cells = {}
    for x in range(math.floor(min(xs) - half - 3), math.ceil(max(xs) + half + 4)):
        for z in range(math.floor(min(zs) - half - 3), math.ceil(max(zs) + half + 4)):
            best = min(range(len(samples)), key=lambda i: (samples[i][0] - x) ** 2 + (samples[i][1] - z) ** 2)
            d = math.hypot(samples[best][0] - x, samples[best][1] - z)
            if d <= half + 0.4 + 0.9 * (fn.fbm2(x, z, 6, 2, seed) + 1) / 2 - (0.5 if best in (0, len(samples) - 1) else 0):
                cells[(x, z)] = (samples[best][2], best, d)
    return cells


def tangent(samples, i):
    a, b = samples[max(0, i - 2)], samples[min(len(samples) - 1, i + 2)]
    length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    return (b[0] - a[0]) / length, (b[1] - a[1]) / length


def corridor_samples():
    return smooth_path(CORRIDOR_PATH)


def alcoves():
    """Niches du couloir : (i, côté) — un échantillon de la courbe, -1 à gauche, +1 à droite de la descente."""
    samples = corridor_samples()
    return [(i, 1 if k % 2 == 0 else -1) for k, i in enumerate(range(12, len(samples) - 8, ALCOVE_EVERY))]


def alcove_cells(i, side):
    """{(x, z): debout} d'une niche : 3 blocs de large, creusée de 4 blocs dans la paroi, au niveau de la voie."""
    samples = corridor_samples()
    x, z, stand = samples[i]
    tx, tz = tangent(samples, i)
    nx, nz = -tz * side, tx * side
    cells = {}
    for d10 in range(int((CORRIDOR_HALF - 0.5) * 10), int((CORRIDOR_HALF + 4.6) * 10)):
        for l10 in range(-15, 16):
            d, lat = d10 / 10, l10 / 10
            cells[(round(x + nx * d + tx * lat), round(z + nz * d + tz * lat))] = stand
    return cells


def mine_z(x):
    """z du milieu de la mine en x (MINE_CURVE, lissé en cosinus)."""
    pts = sorted(MINE_CURVE)
    x = min(max(x, pts[0][0]), pts[-1][0])
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0) if x1 != x0 else 0
            return z0 + (z1 - z0) * (1 - math.cos(math.pi * t)) / 2
    return pts[-1][1]


def mine_base(x):
    """Debout « moyen » des rails en x : de CH_STAND au départ (est) à PAD_STAND au bout (ouest)."""
    t = (MINE[1] - x) / (MINE[1] - MINE[0])
    return CH_STAND + (PAD_STAND - CH_STAND) * min(1.0, max(0.0, t))


def mine_lava_y(x):
    return math.floor(mine_base(x)) - MINE_DROP


def mine_segments():
    """Tronçons de rails de la mine : (x0, x1, debout, z du milieu), d'est en ouest ; trous de 2 à 3 blocs entre
    eux ; ils descendent peu à peu (une marche d'un bloc vers le haut au plus) et suivent la courbe d'un bloc de côté au
    plus. Le dernier s'arrête un bloc avant le
    palier d'arrivée : jamais de rail sur le palier (point de retour)."""
    out, x, k = [], MINE[1] - 7, 0
    bumps = [0, 1, 0, 0, 1, 0, 1, 0, 0]
    stop = END_PAD[1] + 2
    while x >= stop:
        length = 5 if k % 3 else 4
        x0 = max(x - length + 1, stop)
        stand = math.floor(mine_base((x0 + x) / 2)) + bumps[k % len(bumps)]
        if out:
            stand = min(stand, out[-1][2] + 1)
        zc = round(mine_z((x0 + x) / 2))
        if out:   # un bloc de côté au plus d'un tronçon au suivant : les sauts restent droits et courts
            zc = max(out[-1][3] - 1, min(out[-1][3] + 1, zc))
        out.append((x0, x, stand, zc))
        x -= length + (3 if k % 2 else 2)
        k += 1
    return out


def mine_cells():
    """{(x, z): y de la lave} du fond de la mine."""
    return {(x, z): mine_lava_y(x) for x in range(MINE[0] - 2, MINE[1] + 1)
            for z in range(math.floor(mine_z(x) - MINE_HALF), math.ceil(mine_z(x) + MINE_HALF) + 1)
            if abs(z - mine_z(x)) <= MINE_HALF - 0.5 + 1.2 * (fn.fbm2(x, z, 7, 2, 41) + 1) / 2}


# Parois des galeries : montées jusqu'à la voûte par cavern() (des tubes de roche, pas des murets).
GALLERY_WALLS = set()


def mine_start():
    """Plate-forme sûre du départ de la mine (est), au niveau de l'arène du Champion."""
    zc = round(mine_z(MINE[1]))
    return {(x, z): CH_STAND for x in range(MINE[1] - 4, MINE[1] + 1) for z in range(zc - 2, zc + 3)}


def galleries(p):
    """Couloir aux rochers, palier nord, passage vers le Champion, arène du Champion, mine et palier d'arrivée :
    galeries courbes creusées dans le volcan, qui descendent peu à peu."""
    floors = {}                                         # (x, z) -> debout
    corridor = path_cells(corridor_samples(), CORRIDOR_HALF, 51)
    gate_z = GATE_CAMP[0][2]
    corridor = {(x, z): v for (x, z), v in corridor.items() if z < gate_z or (z == gate_z and abs(x) <= 3)}
    floors.update({c: v[0] for c, v in corridor.items()})
    for i, side in alcoves():
        for c, stand in alcove_cells(i, side).items():
            floors.setdefault(c, stand)
    lx, lz, lr, ls = LANDING_N
    for x in range(lx - lr - 1, lx + lr + 2):
        for z in range(lz - lr - 1, lz + lr + 2):
            if math.hypot(x - lx, z - lz) <= lr + 0.5:
                floors[(x, z)] = ls
    for c, v in path_cells(smooth_path(PASSAGE_PATH), GALLERY_HALF, 52).items():
        floors.setdefault(c, v[0])
    for x in range(-49, CH_CENTER[0] - CH_RADIUS + 1):   # seuil vers la mine
        for z in range(-96, -91):
            floors[(x, z)] = CH_STAND
    floors.update(mine_start())
    ex0, ex1, ez0, ez1 = END_PAD
    pad = {(x, z): PAD_STAND for x in range(ex0, ex1 + 1) for z in range(ez0, ez1 + 1)}
    chx, chz = CH_CENTER
    disc = lambda x, z: math.hypot(x - chx, z - chz) <= CH_RADIUS + 0.5      # sol de l'arène (fc.disc)
    arena = lambda x, z: math.hypot(x - chx, z - chz) <= CH_RADIUS + 1.5     # avec son anneau de roche
    camp = lambda x, z: CAMP[0] <= x <= CAMP[1] and CAMP[2] <= z <= CAMP[3]
    for (x, z), stand in floors.items():
        if disc(x, z) or camp(x, z):
            continue
        p.set(x, stand - 1, z, pick(GROUND, x, stand - 1, z))
        for y in range(stand - 4, stand - 1):
            p.set(x, y, z, pick(ROCK, x, y, z))
        for y in range(stand, stand + 4):
            p.set(x, y, z, go.AIR)
    lava = mine_cells()
    for (x, z), y in lava.items():
        if (x, z) in floors or (x, z) in pad:
            continue
        p.set(x, y, z, LAVA if fn.hash01(x, 3, z, 42) < 0.8 else "Rock_Magma_Cooled")
        p.set(x, y - 1, z, pick(ROCK, x, y - 1, z))
    # Parois : tout ce qui borde un sol ou la coulée, à 2 blocs, sauf les arènes, le camp et le palier d'arrivée.
    ground = dict(floors)
    bottom = {c: stand - 4 for c, stand in floors.items()}
    for (x, z), y in lava.items():
        if (x, z) not in floors:
            ground[(x, z)] = math.floor(mine_base(x))
            bottom[(x, z)] = y - 1
    near, low = {}, {}
    for (x, z), stand in ground.items():
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                c = (x + dx, z + dz)
                if c not in ground and c not in pad and not arena(*c) and not camp(*c):
                    near[c] = max(near.get(c, stand), stand)
                    low[c] = min(low.get(c, bottom[(x, z)]), bottom[(x, z)])
    for (x, z), stand in near.items():
        for y in range(low[(x, z)], stand + 3):
            if fn.free(p, x, y, z):
                p.set(x, y, z, cave_rock(x, y, z))
        GALLERY_WALLS.add((x, z))
    # Bouche du volcan en haut du couloir : la roche y luit (les rochers en sortent).
    x, z, stand = corridor_samples()[2]
    for (cx, cz) in [c for c in near if math.hypot(c[0] - x, c[1] - z) <= 6]:
        for y in range(stand, stand + 3):
            if p.blocks.get((cx, y, cz), (go.AIR,))[0] != go.AIR:
                p.set(cx, y, cz, LAVA if (cx + y + cz) % 3 else EMBER)
    for i, side in alcoves():
        x, z, stand = corridor_samples()[i]
        tx, tz = tangent(corridor_samples(), i)
        d = CORRIDOR_HALF + 4.2   # au fond de la niche, sur le côté
        p.set(round(x - tz * side * d + tx), stand, round(z + tx * side * d + tz), "Furniture_Crude_Torch")
    champion_arena(p)
    # Mine : plate-forme sûre au départ, rails sur planches.
    for (x, z), stand in mine_start().items():
        p.set(x, stand - 1, z, LANDING)
    for x0, x1, stand, zc in mine_segments():
        for x in range(x0, x1 + 1):
            for z in range(zc - 1, zc + 2):
                p.set(x, stand - 1, z, PLANKS)
            p.set(x, stand, zc, "Rail")
        for x in (x0, x1):
            for y in range(mine_lava_y(x) + 1, stand - 1):
                p.set(x, y, zc - 1, BEAM)
                p.set(x, y, zc + 1, BEAM)
    for (x, z), stand in pad.items():
        p.set(x, stand - 1, z, LANDING if x >= ex1 - 2 else pick(GROUND, x, stand - 1, z))
        for y in range(mine_lava_y(MINE[0]) - 1, stand - 1):
            p.set(x, y, z, pick(ROCK, x, y, z))
        for y in range(stand, stand + 4):
            p.set(x, y, z, go.AIR)
    p.set(ex1 - 1, PAD_STAND, ez1, "Deco_Bone_Skulls")
    p.set(ex1 - 2, PAD_STAND, ez1, "Deco_Bone_Pile")
    p.set(ex1, PAD_STAND, ez1, "Furniture_Ancient_Crate")


def champion_arena(p):
    """Arène du Champion : au nord, le bord d'une falaise au-dessus du lac de lave du volcan (la vue reste dégagée
    sur l'île du Chamane, sans muret) ; au sud, le mur de roche et les grottes des vétérans."""
    chx, chz = CH_CENTER
    s = CH_STAND
    fc.disc(p, chx, chz, CH_RADIUS, s, lambda x, z: pick(GROUND, x, s, z), ROCK, 8)
    for a in range(0, 360, 6):
        x, z = ring_point(CH_CENTER, CH_RADIUS + 1, a)
        if abs(z - chz) <= 3 or z < chz - 4 or any(abs(x - gx) <= 2 and z > chz for gx, _ in VETERAN_GATES):
            continue   # nord : rien entre l'arène et le vide, la vue sur l'île reste dégagée
        for y in range(s - 1, s + 4):
            p.set(x, y, z, pick(ROCK, x, y, z))
    for a in CAPTIVE_ANGLES:   # cages des captifs, au bord de la falaise
        x, z = ring_point(CH_CENTER, CAPTIVE_RADIUS, a)
        p.set(x, s - 1, z, "Rock_Magma_Cooled")
        p.set(x, s, z - 1, "Deco_Trork_Cage")
    for gx, gz in VETERAN_GATES:   # grottes : un porche de roche, ouvert vers l'arène
        for dx in range(-3, 4):
            for dz in range(-2, 7):
                x, z = gx + dx, gz + dz
                p.set(x, s - 1, z, pick(GROUND, x, s - 1, z))
                p.set(x, s - 2, z, pick(ROCK, x, s - 2, z))
                if dz < 1:
                    continue
                inside = abs(dx) <= 1 and dz <= 5
                for y in range(s, s + 6):
                    p.set(x, y, z, go.AIR if inside and y < s + 3 else pick(ROCK, x, y, z))
        p.set(gx, s + 2, gz + 1, "Furniture_Crude_Torch")
    for (x, y, z) in GATE_CH:
        p.set(x, y, z, MIST)


def course_prefab():
    p = go.Prefab()
    # Camp des grawls.
    x0, x1, z0, z1 = CAMP
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = min(x - x0, x1 - x, z - z0, z1 - z)
            p.set(x, -1, z, pick(GROUND, x, -1, z))
            for y in range(-2 - min(12, edge), -1):
                if edge < 2 or y == -2 - min(12, edge):
                    p.set(x, y, z, pick(ROCK, x, y, z))
            if edge == 0 and not (z == z0 and abs(x) <= 3):
                for y in range(0, 3 + (x * 7 + z * 3) % 3):
                    p.set(x, y, z, pick(ROCK, x, y, z))
    for x, z in ((-12, -4), (12, -4), (-10, 14), (10, 14)):   # huttes : poteaux et crânes
        for dx, dz in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            for y in range(0, 4):
                p.set(x + dx, y, z + dz, BEAM)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                p.set(x + dx, 4, z + dz, "Wood_Darkwood_Planks_Half")
        p.set(x, 0, z, "Furniture_Crude_Brazier")
        p.set(x + 2, 4, z, "Deco_Bone_Skulls")
    for x, z in ((-5, -10), (5, -10), (0, 8)):
        p.set(x, 0, z, "Furniture_Crude_Torch")
    galleries(p)
    for (x, y, z) in GATE_CAMP:   # après les galeries : le couloir ne doit pas creuser la brume
        p.set(x, y, z, MIST)
    island(p)
    dress(p)
    cavern(p)
    contain_lava(p)
    return p


def craters():
    """Centres des petits cratères de l'île : à 7 blocs l'un de l'autre au moins, loin du centre (le Chamane y
    apparaît), des villageois et de l'arrivée de la chaussée."""
    villagers = [ring_point(AR_CENTER, VILLAGER_RADIUS, a) for a in VILLAGER_ANGLES]
    entry = ring_point(AR_CENTER, AR_RADIUS, ENTRY_ANGLE)
    out, k = [], 0
    while len(out) < CRATER_COUNT and k < 5000:
        k += 1
        a = fn.hash01(k, 7, 1, 71) * 360
        d = 5 + fn.hash01(k, 8, 2, 71) * (AR_RADIUS - 9)
        x, z = ring_point(AR_CENTER, d, a)
        if (any(math.hypot(x - cx, z - cz) < 7 for cx, cz in out) or
                any(math.hypot(x - vx, z - vz) < 5 for vx, vz in villagers) or math.hypot(x - entry[0], z - entry[1]) < 7):
            continue
        out.append((x, z))
    assert len(out) == CRATER_COUNT, "pas assez de place pour les cratères"
    return out


def crater_cells(center):
    """Cases (x, y, z) du dessus de l'île qui forment le cratère."""
    cx, cz = center
    r = int(CRATER_RADIUS) + 1
    return [(x, AR_STAND - 1, z) for x in range(cx - r, cx + r + 1) for z in range(cz - r, cz + r + 1)
            if math.hypot(x - cx, z - cz) <= CRATER_RADIUS]


def island(p):
    """Île du Chamane imprégné au milieu du lac de lave : bord irrégulier, roche jusqu'au fond du lac, anneau de
    briques, braseros au bord, cages des villageois, petits cratères (cendre froide au repos, cerclés de magma figé)."""
    ax, az = AR_CENTER
    holes = {(x, z) for c in craters() for x, _, z in crater_cells(c)}
    lips = {(x + dx, z + dz) for x, z in holes for dx in (-1, 0, 1) for dz in (-1, 0, 1)} - holes
    for x in range(ax - AR_RADIUS - 3, ax + AR_RADIUS + 4):
        for z in range(az - AR_RADIUS - 3, az + AR_RADIUS + 4):
            d = math.hypot(x - ax, z - az)
            if d > AR_RADIUS + 0.5 + 1.5 * fn.fbm2(x, z, 6, 2, 73):
                continue
            if (x, z) in holes:
                top = CRATER_STAGES[0]
            elif (x, z) in lips:
                top = "Rock_Magma_Cooled"
            elif abs(d - 8) < 0.5:
                top = "Rock_Volcanic_Brick_Smooth"
            else:
                top = pick(GROUND, x, AR_STAND - 1, z)
            p.set(x, AR_STAND - 1, z, top)
            for y in range(LAKE_Y - 1, AR_STAND - 1):
                p.set(x, y, z, pick(ROCK, x, y, z))
    entry = ring_point(AR_CENTER, AR_RADIUS, ENTRY_ANGLE)
    for a in range(0, 360, 20):
        x, z = ring_point(AR_CENTER, AR_RADIUS - 1, a)
        if math.hypot(x - entry[0], z - entry[1]) < 6:
            continue   # arrivée de la chaussée
        p.set(x, AR_STAND, z, "Rock_Volcanic_Brick_Pillar_Base")
        p.set(x, AR_STAND + 1, z, "Rock_Volcanic_Brick_Pillar_Middle")
        p.set(x, AR_STAND + 2, z, "Furniture_Crude_Brazier")
    for a in VILLAGER_ANGLES:
        x, z = ring_point(AR_CENTER, VILLAGER_RADIUS, a)
        p.set(x + (1 if x > ax else -1), AR_STAND, z, "Deco_Trork_Cage")


THEME = fn.THEMES["volcanic"]


def dress(p):
    """Terres brûlées autour du camp et de l'arène du Champion, la caldeira. Pas d'arbres : tout se passe dans le
    volcan (galleries, cavern). Jamais de sol en plus au-dessus de la lave de la mine ni entre deux sauts."""
    def footprint(y, x0, x1, z0, z1):
        return {(x, z): y for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if (x, y, z) in p.blocks}

    # Camp : terres brûlées et arbres morts autour des murets, pas au nord (couloir).
    x0, x1, z0, z1 = CAMP
    camp = footprint(-1, x0, x1, z0, z1)
    tops = fn.rim(camp, 4, 13, seed=21, block=lambda x, z: z < z0 + 2 and abs(x) < 10)
    fn.natural_ground(p, tops, THEME, seed=21, trees=0, spacing=7, density=0.3)
    # Arène du Champion : terres brûlées autour du cercle (les brèches des vétérans restent ouvertes).
    chx, chz = CH_CENTER
    ring = {}
    for x in range(chx - CH_RADIUS - 2, chx + CH_RADIUS + 3):
        for z in range(chz - CH_RADIUS - 2, chz + CH_RADIUS + 3):
            if math.hypot(x - chx, z - chz) <= CH_RADIUS + 1.5:
                ring[(x, z)] = CH_STAND - 1
    tops = fn.rim(ring, 4, 12, seed=27, block=lambda x, z: abs(z - chz) <= 6 or z < chz)   # nord : la falaise
    tops = {c: y for c, y in tops.items()
            if not any((c[0], yy, c[1]) in p.blocks for yy in range(CH_STAND - 1, CH_STAND + 6))}
    fn.natural_ground(p, tops, THEME, seed=27, trees=0, spacing=7, density=0.3)
    caldera(p)


# --- l'intérieur du volcan (Kevin, 2026-10-24) -------------------------------------------------------------------------
# Toute la fractale se passe dans le volcan : une voûte de basalte au-dessus de chaque lieu (galeries de 7 à 16 blocs de
# haut, une vaste grotte en dôme au-dessus de la caldeira), des parois tout autour, des gouffres au fond de lave figée
# entre les lieux, des stalactites (blocs vanilla Rock_*_Stalactite_*, rotation 8 = pendue, comme dans les prefabs de
# grottes du jeu), des veines incandescentes et des coulées de lave sur les parois.
CEILING_THICKNESS = 2
WALL_THICKNESS = 3
OVERHANG = 3                            # la voûte déborde des lieux de 3 blocs (les gouffres entre deux lieux)
DOME_Y = LAKE_Y + 50                    # sommet de la grande grotte de la caldeira
STALACTITES = ["Rock_Basalt_Stalactite_Large", "Rock_Volcanic_Stalactite_Large", "Rock_Basalt_Stalactite_Small",
               "Rock_Volcanic_Stalactite_Small"]
HANGING = 8                             # rotation d'un bloc retourné (prefabs de grottes vanilla)


def disc_offsets(r):
    return [(dx, dz) for dx in range(-r, r + 1) for dz in range(-r, r + 1) if dx * dx + dz * dz <= r * r]


def cave_rock(x, y, z):
    """Roche de la voûte et des parois : basalte et roche volcanique en plaques, veines incandescentes."""
    vein = abs(fn.fbm2(x + 0.37 * y, z - 0.29 * y, 9, 2, 91))
    if vein < 0.012:
        return LAVA         # veines de roche en fusion : la lumière des galeries
    if vein < 0.035:
        return EMBER
    return pick(CAVE_ROCK, x, y, z)


def cavern(p):
    tops, bottoms = {}, {}
    for (x, y, z), (name, _) in p.blocks.items():
        if name == go.AIR and (x, y, z) not in p.fluids:
            continue
        tops[(x, z)] = max(tops.get((x, z), y), y)
        bottoms[(x, z)] = min(bottoms.get((x, z), y), y)
    inner = set(tops)
    for dx, dz in disc_offsets(OVERHANG):
        inner |= {(x + dx, z + dz) for x, z in tops}
    outer = set(inner)
    for dx, dz in disc_offsets(WALL_THICKNESS):
        outer |= {(x + dx, z + dz) for x, z in inner}
    walls = outer - inner
    # Plus haut et plus bas voisins de chaque colonne (la voûte passe au-dessus des crêtes, les parois descendent sous
    # les fonds), puis hauteur de voûte : dôme sur la caldeira, galeries ailleurs.
    near_top, near_bottom = {}, {}
    reach = disc_offsets(6)
    for x, z in outer:
        ts = [tops[(x + dx, z + dz)] for dx, dz in reach if (x + dx, z + dz) in tops]
        bs = [bottoms[(x + dx, z + dz)] for dx, dz in reach if (x + dx, z + dz) in bottoms]
        near_top[(x, z)] = max(ts) if ts else LAKE_Y
        near_bottom[(x, z)] = min(bs) if bs else LAKE_Y - 2
    raw = {}
    for x, z in outer:
        gallery = near_top[(x, z)] + 7 + round(9 * (fn.fbm2(x, z, 23, 2, 92) + 1) / 2)
        d = min(math.hypot(x - cx, z - cz) - r for cx, cz, r in LAKE_DISCS)
        dome = DOME_Y + round(5 * fn.fbm2(x, z, 17, 2, 93)) - max(0, d) * 0.8
        raw[(x, z)] = max(gallery, dome)
    ceiling = {}
    blur = disc_offsets(3)
    for x, z in outer:
        vals = [raw[(x + dx, z + dz)] for dx, dz in blur if (x + dx, z + dz) in raw]
        ceiling[(x, z)] = max(round(sum(vals) / len(vals)), near_top[(x, z)] + 5)
    # Gouffres entre les lieux : fond de lave figée qui luit, sous le plus bas voisin.
    for x, z in inner - set(tops):
        floor = near_bottom[(x, z)] - 3
        p.set(x, floor, z, LAVA if fn.hash01(x, 5, z, 94) < 0.5 else "Rock_Magma_Cooled")
        p.set(x, floor - 1, z, pick(ROCK, x, floor - 1, z))
    # Voûte.
    for x, z in inner:
        c = ceiling[(x, z)]
        for y in range(c, c + CEILING_THICKNESS):
            p.set(x, y, z, cave_rock(x, y, z))
    # Parois des galeries montées jusqu'à la voûte : des tubes de roche courbes.
    for x, z in GALLERY_WALLS:
        if (x, z) in ceiling:
            for y in range(tops[(x, z)] + 1, ceiling[(x, z)]):
                if fn.free(p, x, y, z):
                    p.set(x, y, z, cave_rock(x, y, z))
    # Parois, du fond des gouffres à la voûte.
    for x, z in walls:
        for y in range(near_bottom[(x, z)] - 5, ceiling[(x, z)] + CEILING_THICKNESS):
            if fn.free(p, x, y, z):
                p.set(x, y, z, cave_rock(x, y, z))
    lava_falls(p, walls, inner, ceiling, near_bottom)
    stalactites(p, inner, ceiling, tops)
    cave_flora(p, tops)


def lava_falls(p, walls, inner, ceiling, near_bottom):
    """Coulées de lave sur les parois qui bordent le lac de la caldeira et la coulée de la mine : une bande de roche en
    fusion de la voûte jusqu'en bas, sur la face tournée vers la grotte."""
    faces = sorted((x, z) for x, z in walls if any((x + dx, z + dz) in inner for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    mine = lambda x, z: MINE[0] - 2 <= x <= MINE[1] and abs(z - mine_z(x)) <= MINE_HALF + 8
    placed = []
    for x, z in faces:
        lake = any(math.hypot(x - cx, z - cz) <= r + 12 for cx, cz, r in LAKE_DISCS)
        if not (lake or mine(x, z)) or fn.hash01(x, 7, z, 95) > 0.08:
            continue
        if any(math.hypot(x - a, z - b) < 11 for a, b in placed):
            continue
        placed.append((x, z))
        width = 1 + int(fn.hash01(z, 7, x, 96) * 2)
        for k in range(width):
            fx, fz = (x + k, z) if (x + k, z) in walls else (x, z + k)
            for y in range(near_bottom[(x, z)] - 4, ceiling[(x, z)]):
                p.set(fx, y, fz, LAVA)
    # Coulées des hautes parois de la mine (côté rails : on ne s'y tient jamais).
    for x in range(MINE[0] + 4, MINE[1] - 4, 13):
        for side in (-1, 1):
            z = round(mine_z(x) + side * (MINE_HALF + 2))
            if (x, z) in GALLERY_WALLS:
                for y in range(mine_lava_y(x), math.floor(mine_base(x)) + 10):
                    p.set(x, y, z, LAVA)


def stalactites(p, inner, ceiling, tops):
    """Stalactites sous la voûte, loin au-dessus des têtes : cône de roche (large en haut) et pointe vanilla pendue."""
    for x, z in sorted(inner):
        h = fn.hash01(x, 9, z, 97)
        if h > 0.035:
            continue
        c = ceiling[(x, z)]
        room = c - tops.get((x, z), LAKE_Y - 2)
        if room < 10:
            continue
        length = 1 + int(fn.hash01(z, 9, x, 98) * min(7, room - 8))
        for k in range(1, length + 1):
            y = c - k
            p.set(x, y, z, cave_rock(x, y, z))
            if k <= length // 2:
                for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if fn.hash01(x + dx, y, z + dz, 99) < 0.7 and fn.free(p, x + dx, y, z + dz):
                        p.set(x + dx, y, z + dz, cave_rock(x + dx, y, z + dz))
        p.set(x, c - length - 1, z, STALACTITES[int(h / 0.035 * len(STALACTITES)) % len(STALACTITES)], HANGING)


def cave_flora(p, tops):
    """Roseaux de lave au bord du lac et des coulées, ronces de lave sur la cendre."""
    for (x, z), y in sorted(tops.items()):
        name = p.blocks.get((x, y, z), ("",))[0]
        if not fn.free(p, x, y + 1, z) or math.hypot(x - AR_CENTER[0], z - AR_CENTER[1]) <= AR_RADIUS + 1:
            continue
        lava_near = any(p.blocks.get((x + dx, y + dy, z + dz), ("",))[0] == LAVA or (x + dx, y + dy, z + dz) in p.fluids
                        for dx, dz in ((2, 0), (-2, 0), (0, 2), (0, -2)) for dy in (0, -1, -2, -3))
        h = fn.hash01(x, y, z, 100)
        if name.startswith("Soil_") and lava_near and h < 0.35:
            p.set(x, y + 1, z, "Plant_Reeds_Lava")
        elif name == "Soil_Ash" and h < 0.012:
            p.set(x, y + 1, z, "Plant_Bramble_Dead_Lavathorn")


def contain_lava(p):
    """La lave du lac ne doit couler nulle part : chaque case de fluide a de la lave ou de la roche à côté et dessous."""
    for (x, y, z) in list(p.fluids):
        for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, -1, 0)):
            at = (x + dx, y + dy, z + dz)
            if at not in p.fluids and not p.solid_at(*at):
                p.set(*at, pick(ROCK, at[0], at[1], at[2]))


def descent_cells():
    """{(x, z): debout} de la descente du bout de la mine jusqu'à l'île, le long de DESCENT (marches d'un bloc)."""
    cells = {}
    for (x0, z0, s0), (x1, z1, s1) in zip(DESCENT, DESCENT[1:]):
        n = int(math.hypot(x1 - x0, z1 - z0) * 3)
        for i in range(n + 1):
            t = i / n
            x, z, stand = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, round(s0 + (s1 - s0) * t)
            for gx in range(math.floor(x - DESCENT_WIDTH), math.ceil(x + DESCENT_WIDTH) + 1):
                for gz in range(math.floor(z - DESCENT_WIDTH), math.ceil(z + DESCENT_WIDTH) + 1):
                    if math.hypot(gx - x, gz - z) <= DESCENT_WIDTH:
                        cells[(gx, gz)] = max(cells.get((gx, gz), stand), stand)
    return cells


def in_lake(x, z):
    return any(math.hypot(x - cx, z - cz) <= r for cx, cz, r in LAKE_DISCS)


def caldera(p):
    """Le lac de lave au pied du volcan : la descente (sentier puis chaussée), la lave autour de l'île du Chamane,
    les falaises qui tombent jusqu'au lac (sous l'arène du Champion, la crête de la mine) et les parois du cratère
    tout autour. Le lac est de la vraie lave (fluide Lava_Source) ; y tomber brûle (Java : Volcanic.lavaFloor)."""
    path = descent_cells()
    for (x, z), stand in path.items():
        p.set(x, stand - 1, z, pick(GROUND, x, stand - 1, z))
        for y in range(LAKE_Y - 1, stand - 1):
            p.set(x, y, z, pick(ROCK, x, y, z))
    for (x, z), stand in path.items():   # le sentier traverse la crête et le mur de la mine : on le creuse
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if (x + dx, z + dz) in path or dx == dz == 0:
                    for y in range(path.get((x + dx, z + dz), stand), 30):
                        if (x + dx, y, z + dz) in p.blocks:
                            p.set(x + dx, y, z + dz, go.AIR)
    columns = {}
    for (x, y, z), (name, _) in p.blocks.items():
        if name != go.AIR and y >= LAKE_Y:
            columns[(x, z)] = min(columns.get((x, z), 99), y)
    xs = [cx - r - 4 for cx, _, r in LAKE_DISCS] + [cx + r + 4 for cx, _, r in LAKE_DISCS]
    zs = [cz - r - 4 for _, cz, r in LAKE_DISCS] + [cz + r + 4 for _, cz, r in LAKE_DISCS]
    lake = {(x, z) for x in range(min(xs), max(xs) + 1) for z in range(min(zs), max(zs) + 1)
            if in_lake(x, z) and (x, z) not in columns}
    for x, z in lake:   # vraie lave sur deux blocs de fond (Kevin, 2026-10-24)
        p.fluid(x, LAKE_Y, z, LAVA_FLUID)
        p.fluid(x, LAKE_Y - 1, z, LAVA_FLUID)
        p.set(x, LAKE_Y - 2, z, pick(ROCK, x, LAKE_Y - 2, z))
    near = lambda x, z, d: any((x + dx, z + dz) in lake for dx in range(-d, d + 1) for dz in range(-d, d + 1))
    for (x, z), low in columns.items():   # falaises : ce qui borde le lac descend jusqu'au fond
        if low > LAKE_Y - 2 and near(x, z, 2):
            for y in range(LAKE_Y - 2, low):
                p.set(x, y, z, pick(ROCK, x, y, z))
    # Parois du cratère autour du lac (pas sur ce qui existe déjà, ni contre la descente).
    tops = {}
    for x in range(min(xs) - 10, max(xs) + 11):
        for z in range(min(zs) - 10, max(zs) + 11):
            if (x, z) in lake or (x, z) in columns or any((x + dx, z + dz) in path for dx in (-2, 0, 2) for dz in (-2, 0, 2)):
                continue
            if z < CH_CENTER[1] and math.hypot(x - CH_CENTER[0], z - CH_CENTER[1]) < CH_RADIUS + 10:
                continue   # rien devant le bord de la falaise du Champion : la vue sur l'île reste dégagée
            reach = 4 + round(6 * (fn.fbm2(x, z, 11, 2, 85) + 1) / 2)
            if near(x, z, reach) and not in_lake(x, z):
                tops[(x, z)] = LAKE_Y + 6 + round(20 * (fn.fbm2(x, z, 13, 3, 86) + 1) / 2)
    inland = fn.edge_distance(tops)
    cells = fn.island(p, tops, lambda x, z: tops[(x, z)] - LAKE_Y + 2, 87, hang=0.0, theme=THEME)
    fn.dress(p, [c for c in cells if inland[(c[0], c[2])] > 1], THEME, 88, trees=0, spacing=8, bushes=0.04,
             boulders=0.006, density=0.25)


# --- objets, effets, particules -----------------------------------------------------------------------

def stone_parts():
    rock, glow = (90, 70, 60), (255, 150, 60)
    return [("Rock", (0, 4, 0), (7, 7, 6), 20, fm.smooth(rock), "flat"),
            ("Vein_A", (0, 4, 3.1), (5, 1, 1), 0, fm.crystal((160, 60, 20), glow), "fullbright"),
            ("Vein_B", (2.1, 5, 0), (1, 4, 1), 0, fm.crystal((160, 60, 20), glow), "fullbright")]


def stone_item():
    root = "Root_Nakasar_Fractal_Throw_Imbued_Stone"
    return fc.held_item(LANG, STONE, "Imbued_Stone", stone_parts(), 41, (0, 4, 0), 16.0, quality="Epic",
                        extra={"Interactions": {"Secondary": root, "SwapFrom": fc.KEEP_IN_HAND},
                               "Utility": {"Compatible": False}, "Categories": ["Items.Misc"]})


def throw_interaction():
    return {"$Comment": "Pierre imprégnée : clic droit, la lancer sur le Champion chaman visé (24 blocs, cône de 30°) ; "
                        "elle lui retire une charge de protection (Java, volcanic.Champion).",
            "Type": "Nakasar_Fractal_ThrowItem", "Item": STONE, "Roles": CHAMPION, "Range": 24, "Cone": 30,
            "Particle": "Nakasar_Fractal_Imbued_Trail", "Action": "ImbuedStone",
            "NoTargetMessage": f"{LANG}.stone.noTarget"}


def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Lava_Burn": fc.effect(
            L, "Nakasar_Fractal_Lava_Burn", "Dans la lave (lac du volcan, cratère en fusion de l'île du Chamane) : "
            "grosse brûlure tant qu'on y reste (Java, volcanic.Volcanic.lavaFloor et volcanic.ImbuedShaman).",
            "Lava_Burn", 1.0, debuff=True, ApplicationEffects={"EntityBottomTint": "#ff6a1a", "EntityTopTint": "#ffb040"}),
        "Nakasar_Fractal_Spreading_Flame": fc.effect(
            L, "Nakasar_Fractal_Spreading_Flame", "Flèche enflammée du Chamane imprégné : brûle et passe aux joueurs "
            "à moins de 2,5 blocs (Java).", "Spreading_Flame", 6, debuff=True,
            ApplicationEffects={"EntityTopTint": "#ff8a2a", "EntityBottomTint": "#5a1000"}),
    }


def crater_blocks():
    """Les cinq états d'un cratère (write_block) : du brun volcanique solide à la lave orange et jaune."""
    colors = [((74, 60, 54), (112, 84, 64), None), ((112, 66, 42), (196, 104, 46), None),
              ((158, 74, 32), (250, 142, 44), "#510"), ((212, 96, 26), (255, 196, 70), "#830"),
              ((255, 146, 30), (255, 236, 120), "#f80")]
    return [(name, name.removeprefix("Nakasar_Fractal_"), base, accent, "cracks", light)
            for name, (base, accent, light) in zip(CRATER_STAGES, colors)]


def fire_cause():
    return fc.cause("Feu du Volcanique (rochers, traînées, lave, cratères en fusion, flamme qui se propage) : une "
                    "part des PV max, l'armure ne le réduit pas.", "#ff8a3a")


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Boulder": ("Rocher en feu qui dévale : éclats sombres et flammes.",
                                [("Rock", S("#5a4030", "#2a1a10", 14, (0.5, 1.5), (-30, 60), 1.4, 1.6, life=(0.3, 0.5),
                                            size=(0.5, 0.9), blend="BlendLinear"), 0.4),
                                 ("Fire", S("#fff0a0", "#ff4a10", 16, (1.0, 2.5), (40, 90), 1.4, 1.8, life=(0.3, 0.6)), 0.6)]),
    "Nakasar_Fractal_Boulder_Rumble": ("Un rocher arrive : poussière et braises à la bouche du volcan.",
                                       [("Dust", S("#c0a080", "#5a4030", 20, (1.0, 3.0), (-10, 50), 2.5, 2.5,
                                                   life=(0.8, 1.2), blend="BlendLinear"), 0.5)]),
    "Nakasar_Fractal_Fire_Trail": ("Traînée de feu laissée par un rocher.",
                                   [("Flames", S("#ffe080", "#ff3a00", 10, (0.3, 0.9), (70, 90), 1.4, 0.3,
                                                 life=(0.5, 0.9)), 0.1)]),
    "Nakasar_Fractal_Falling_Rock": ("Rocher qui tombe du ciel : poussière qui descend sur le cercle.",
                                     [("Dust", S("#d0b090", "#6a5040", 10, (2.0, 4.0), (-90, -70), 1.5, 0.5,
                                                 life=(0.6, 1.0), blend="BlendLinear"), 6.0)]),
    "Nakasar_Fractal_Rock_Impact": ("Impact d'un rocher : éclats et braises.",
                                    [("Shards", S("#e0c0a0", "#5a3a20", 20, (2.0, 4.5), (20, 90), 1.2, 0.4,
                                                  life=(0.4, 0.8), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Imbued_Glow": ("Pierre imprégnée au sol : lueur orange.",
                                    [("Glow", S("#ffd080", "#ff6a10", 6, (0.2, 0.5), (60, 90), 0.3, 0.6), 0.2)]),
    "Nakasar_Fractal_Imbued_Trail": ("Pierre imprégnée lancée : traînée orange.",
                                     [("Trail", S("#fff0c0", "#ff7a20", 8, (0.1, 0.4), (-90, 90), 0.3, 0.3,
                                                  life=(0.2, 0.4)), 0.0)]),
    "Nakasar_Fractal_Lava_Pit": ("Puits de lave silencieux : bulles de feu au sol (aucun cercle rouge).",
                                 [("Bubbles", S("#ffe080", "#ff3a00", 12, (0.4, 1.2), (70, 90), 2.0, 0.3,
                                                life=(0.5, 0.9)), 0.1)]),
    "Nakasar_Fractal_Spreading_Flame": ("Flamme qui se propage : feu sur le joueur.",
                                        [("Flames", S("#fff0a0", "#ff4a10", 8, (0.4, 1.0), (60, 90), 0.4, 1.6), 0.2)]),
    "Nakasar_Fractal_Totem_Pulse": ("Totem du rituel : pulsation rouge sombre.",
                                    [("Pulse", S("#ffb080", "#7a1a00", 10, (0.5, 1.2), (-10, 60), 0.6, 2.0), 0.4)]),
    "Nakasar_Fractal_Captive_Fall": ("Un captif tombe dans la lave : gerbe de flammes.",
                                     [("Burst", S("#fff0a0", "#ff3a00", 24, (2.0, 4.0), (40, 90), 0.8, 0.5,
                                                  life=(0.5, 0.9)), 0.2)]),
    "Nakasar_Fractal_Shaman_Glide": ("Le Chamane imprégné plane : ailes de feu.",
                                     [("Wings", S("#ffe0a0", "#ff5a10", 14, (0.6, 1.4), (-20, 40), 2.0, 2.0,
                                                  life=(0.4, 0.7)), 1.0)]),
    "Nakasar_Fractal_Shaman_Feed": ("Le Chamane imprégné se nourrit d'un villageois : spirale rouge.",
                                    [("Spiral", S("#ffd0c0", "#a00010", 24, (1.0, 2.0), (-10, 90), 1.0, 2.0,
                                                  life=(0.6, 1.0)), 0.5)]),
}


# --- modèles ----------------------------------------------------------------------------------------------

def grawl(comment, skin, attachments, scale=(0.9, 0.9), light=None):
    doc = fr.humanoid(comment, skin, "Face_Scar", attachments, scale=scale, light=light)
    return doc


def totem_parts():
    wood, paint, glow = (90, 60, 40), (170, 40, 30), (255, 140, 60)
    return [("Pole", (0, 60, 0), (16, 120, 16), 0, fm.smooth(wood), "flat"),
            ("Face_1", (0, 96, 8.5), (14, 18, 1), 0, fm.flat(paint), "flat"),
            ("Face_2", (0, 60, 8.5), (14, 18, 1), 0, fm.flat(paint), "flat"),
            ("Eyes", (0, 100, 9.2), (10, 3, 1), 0, fm.crystal((140, 30, 0), glow), "fullbright"),
            ("Wing_L", (-16, 112, 0), (18, 6, 4), 20, fm.smooth(wood), "flat"),
            ("Wing_R", (16, 112, 0), (18, 6, 4), -20, fm.smooth(wood), "flat"),
            ("Skull", (0, 126, 0), (12, 12, 12), 0, fm.smooth((226, 220, 200)), "flat")]


def models():
    m = {}
    tribal = [("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
              ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
               "Faded_Leather", "Brown"),
              ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
               "Faded_Leather", "Brown")]
    m[WARRIOR] = grawl("Guerrier grawl (provisoire) : humanoïde trapu à peinture de guerre, en attendant un modèle de "
                       "grawl.", "25", tribal)
    m[GRAWL_SHAMAN] = grawl("Chaman grawl (provisoire) : humanoïde trapu, cape et bâton.", "25", tribal + [
        ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
         gc.CLOTH, "Red")], light={"Color": "#f84", "Radius": 2})
    m[VETERAN] = grawl("Vétéran grawl (provisoire) : plus grand, cape rouge.", "25", tribal + [
        ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
         gc.CLOTH, "Red")], scale=(1.05, 1.05))
    m[CHAMPION] = grawl("Champion chaman des grawls (provisoire) : grand, couronne, robe de mage.", "25", [
        ("Cosmetics/Head/KingsCrown.blockymodel", "Cosmetics/Head/KingsCrown_Red.png"),
        ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png")] + tribal[1:],
        scale=(1.25, 1.25), light={"Color": "#f84", "Radius": 3})
    m[CAPTIVE] = fr.humanoid("Captif (provisoire) : villageois en haillons, prisonnier des grawls.", "05", "Almond_Eyes_Face", [
        ("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png",
         "Faded_Leather", "Brown")])
    m[CAPTIVE]["DefaultAttachments"][1]["GradientId"] = "Blue"
    m[TOTEM] = fc.character_model("Grawl_Totem", totem_parts(), 51, "Totem du rituel grawl (PNJ fixe) : sa vie montre les "
                                  "grawls qu'il reste à abattre.", 1.5, (0.5, 2.2), light={"Color": "#f84", "Radius": 3})
    m[BAT] = {"$Comment": "Chauve-souris de la mine : la chauve-souris vanilla, un peu plus grande.", "Parent": "Bat",
              "MinScale": 1.3, "MaxScale": 1.3}
    m[IMBUED] = fr.humanoid(
        "Le Chamane imprégné (boss du Volcanique, provisoire) : grand (× 1,35), cape royale rouge, mains et yeux de "
        "feu. GW2 en fait une harpie géante : à remplacer quand un modèle ailé sera vérifié.", "28", "Face_Scar", [
            ("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            ("Cosmetics/Capes/Cape_King_NoNeck.blockymodel", "Cosmetics/Capes/Cape_King_Texture.png", "Fantasy_Cotton", "Red")],
        scale=(1.35, 1.35), light={"Color": "#f62", "Radius": 4})
    m[LARVA] = {"$Comment": "Larve de braise (Chamane imprégné) : l'esprit de braise vanilla, petit.", "Parent": "Spirit_Ember",
                "MinScale": 0.7, "MaxScale": 0.7}
    return m


# --- attaques -----------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
SPREAD = "Nakasar_Fractal_Spreading_Flame"


def interactions():
    out = {}
    T = fr.telegraph
    out["Nakasar_Fractal_Grawl_Strike"] = {
        "$Comment": "Guerrier grawl : deux coups de lame (8 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup gauche.", "Mace", "SwingLeft", 0.35, 8),
                                           fr.swing("Coup droit.", "Mace", "SwingRight", 0.35, 8, direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Grawl_Slam"] = {
        "$Comment": "Guerrier grawl : coup abattu, cercle rouge de 2,5 blocs (1,2 s), 18 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.2, Radius=2.5, Damage=18, Knockback=5, KnockUp=3,
                                                     ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.2, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    out["Nakasar_Fractal_Grawl_Shaman_Staff"] = {
        "$Comment": "Chaman grawl au contact : coup de bâton (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bâton.", "Staff", "SwingLeft", 0.4, 6)]}
    out["Nakasar_Fractal_Grawl_Shaman_Fire"] = {
        "$Comment": "Chaman grawl : feu sous sa cible, cercle rouge de 2 blocs (1,4 s), 12 dégâts et brûlure.",
        "Type": "Serial", "Interactions": [T("Circle", 1.4, Anchor="Target", Radius=2.0, Damage=12, EffectId="Burn",
                                             EffectDuration=3, PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Fire_Trail"),
                                           {"Type": "Simple", "RunTime": 1.4, "Effects": {"ItemPlayerAnimationsId": "Staff",
                                            "ItemAnimationId": "SwingRight", "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Champion_Staff"] = {
        "$Comment": "Champion chaman au contact : deux coups de bâton (12 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup gauche.", "Staff", "SwingLeft", 0.4, 12, end=3.0),
                                           fr.swing("Coup droit.", "Staff", "SwingRight", 0.4, 12, end=3.0,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Champion_Flames"] = {
        "$Comment": "Champion chaman : flammes sous chaque joueur, cercles rouges de 2,2 blocs (1,6 s), 16 dégâts et "
                    "brûlure.",
        "Type": "Serial", "Interactions": [T("Circle", 1.6, Anchor="EachPlayer", Radius=2.2, Damage=16, EffectId="Burn",
                                             EffectDuration=3, PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Fire_Trail"),
                                           {"Type": "Simple", "RunTime": 1.6, "Effects": {"ItemPlayerAnimationsId": "Staff",
                                            "ItemAnimationId": "SwingRight", "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Bat_Bite"] = {
        "$Comment": "Chauve-souris de la mine : morsure (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.3, 6, end=2.0, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Imbued_Staff"] = {
        "$Comment": "Chamane imprégné au contact : deux coups (18 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup gauche.", "Staff", "SwingLeft", 0.45, 18, end=3.4),
                                           fr.swing("Coup droit.", "Staff", "SwingRight", 0.45, 18, end=3.4,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Imbued_Arrow"] = {
        "$Comment": "Chamane imprégné : flèche enflammée, sa cible est marquée (1,6 s) puis touchée où qu'elle soit "
                    "(20 dégâts) ; la flamme se propage aux joueurs proches (Java) : écartez-vous du joueur touché.",
        "Type": "Serial", "Interactions": [T("Mark", 1.6, Damage=20, DamageCause="Physical", EffectId=SPREAD,
                                             EffectDuration=6, PlayersOnly=True, MarkParticle=SPREAD, MarkParticleScale=1.0,
                                             HitParticle=SPREAD),
                                           {"Type": "Simple", "RunTime": 1.6, "Effects": {"ItemPlayerAnimationsId": "Staff",
                                            "ItemAnimationId": "SwingRight", "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Imbued_Dive"] = {
        "$Comment": "Chamane imprégné : piqué sur sa cible, cercle rouge de 3 blocs (1,5 s), 30 dégâts et projection.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Anchor="Target", Radius=3, Damage=30,
                                                     TeleportCaster=True, Knockback=6, KnockUp=4, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.5, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Imbued_Wings"] = {
        "$Comment": "Chamane imprégné : souffle des ailes, cône de 100° et 6 blocs (1,3 s), 20 dégâts et forte "
                    "projection.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.3, Angle=100, Radius=6, Damage=20, Knockback=12, KnockUp=5,
                                                     ImpactParticle="Nakasar_Fractal_Shaman_Glide"),
                                           fc.windup(1.3, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Imbued_Firestorm"] = {
        "$Comment": "Chamane imprégné : tempête de feu autour de lui, cercle rouge de 7 blocs (1,6 s), 28 dégâts et "
                    "brûlure.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Radius=7, Damage=28, EffectId="Burn", EffectDuration=4,
                                                     ImpactParticle="Nakasar_Fractal_Rock_Impact",
                                                     ImpactSound="SFX_Goblin_Lobber_Bomb_Death"),
                                           fc.windup(1.6, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Larva_Burn"] = {
        "$Comment": "Larve de braise au contact : brûlure (6 dégâts et brûlure 2 s).",
        "Type": "Serial", "Interactions": [fr.swing("Brûlure.", None, None, 0.3, 6, end=2.0, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing",
                                                     extra=[fr.effect_on_target("Burn", 2)])]}
    return out


MELEE = ["Grawl_Strike", "Grawl_Slam", "Grawl_Shaman_Staff", "Champion_Staff", "Bat_Bite", "Imbued_Staff",
         "Imbued_Dive", "Imbued_Wings", "Imbued_Firestorm", "Larva_Burn"]
RANGED = ["Grawl_Shaman_Fire", "Champion_Flames", "Imbued_Arrow"]
R = fc.root


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[WARRIOR] = fr.role(
        WARRIOR, "Guerrier grawl (groupes de 7 du camp) : voit tout le camp et charge aussitôt ; deux coups, et un coup "
        "abattu annoncé.", WARRIOR, n(WARRIOR), 90,
        [fr.timed_attack("Slam", R("Grawl_Slam"), rng=2.8, los=True, comment="Coup abattu annoncé."),
         fr.melee(R("Grawl_Strike"), 2.4, (0.6, 1.0)), fr.chase(60, stop=1.6)],
        fr.walk(5.2), GENERATOR, sight=CAMP_SIGHT, los=False, leash=64, home=False,
        timers=[fr.timer("Slam", (3, 5), (8, 11))], HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.9,
        DeathAnimationTime=1.0)
    out[GRAWL_SHAMAN] = fr.role(
        GRAWL_SHAMAN, "Chaman grawl : garde ses distances, feu annoncé sous sa cible.", GRAWL_SHAMAN, n(GRAWL_SHAMAN), 70,
        [fr.cast("Fire", R("Grawl_Shaman_Fire"), 16, "Feu annoncé."),
         fr.melee(R("Grawl_Shaman_Staff"), 2.0, (0.9, 1.3)), fr.keep_distance(60, 6, 10)],
        fr.walk(4.2), GENERATOR, sight=CAMP_SIGHT, los=False, leash=64, home=False,
        timers=[fr.timer("Fire", (1, 3), (5, 7))], HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=1.0,
        DeathAnimationTime=1.0)
    out[TOTEM] = fc.static_role(LANG, TOTEM, "Totem du rituel grawl : les coups ne lui font rien ; sa vie montre les "
                                "grawls qu'il reste à abattre (Java). Barre de boss.", GENERATOR, 1000)
    vet = fr.role(
        VETERAN, "Vétéran grawl (Champion chaman) : part de sa grotte et marche vers un captif (point d'attache posé "
        "par le Java) ; il ne se bat que si on le frappe, ou une fois arrivé. À côté du captif 1,5 s, il le jette dans "
        "la lave. Marche lente : on a le temps de l'intercepter.", VETERAN, n(VETERAN), 450,
        [fr.timed_attack("Slam", R("Grawl_Slam"), rng=2.8, los=True, comment="Coup abattu annoncé."),
         fr.melee(R("Grawl_Strike"), 2.4, (0.6, 1.0)), fr.chase(24, stop=1.6)],
        fr.walk(1.7), GENERATOR, sight=4, leash=14, home=True,
        timers=[fr.timer("Slam", (3, 5), (8, 11))], HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.6,
        DeathAnimationTime=1.0)
    vet["StartState"] = "ReturnHome"
    out[VETERAN] = vet
    out[CHAMPION] = fr.role(
        CHAMPION, "Champion chaman des grawls, barre de boss : coups de bâton, flammes sous chaque joueur. Ses charges "
        "de protection, les vétérans et les captifs sont menés par le Java (volcanic.Champion).", CHAMPION, n(CHAMPION),
        2400,
        [fr.timed_attack("Flames", R("Champion_Flames"), comment="Flammes sous chaque joueur."),
         fr.melee(R("Champion_Staff"), 2.8, (0.9, 1.3)), fr.chase(30, stop=2.2)],
        fr.walk(3.4), GENERATOR, sight=20, leash=22, home=True,
        timers=[fr.timer("Flames", (3, 5), (8, 10))], HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=0.1,
        DeathAnimationTime=2.0)
    cap = fc.static_role(LANG, CAPTIVE, "Captif des grawls : immobile, invulnérable, neutre ; le Java le jette dans la "
                         "lave si un vétéran le rejoint, ou le Chamane imprégné s'en nourrit.", GENERATOR, 100,
                         attitude="Neutral", foe=False)
    out[CAPTIVE] = cap
    out[BAT] = fr.role(
        BAT, "Chauve-souris de la mine : fond sur les joueurs qui sautent de rail en rail.", BAT, n(BAT), 40,
        [fr.melee(R("Bat_Bite"), 2.2, (0.8, 1.2)), fr.chase(30, speed=1.0, stop=1.2, pathfinder=False)],
        fc.fly(7, 1, 6), GENERATOR, sight=20, leash=36, home=False, KnockbackScale=0.6, DeathAnimationTime=0.8)
    out[IMBUED] = fr.role(
        IMBUED, "Le Chamane imprégné (boss du Volcanique), barre de boss : coups, flèche enflammée (marque), piqué, "
        "souffle des ailes, tempête de feu. Les cratères de lave, les boucliers, les larves et le vol (lent) vers les "
        "villageois sont menés par le Java (volcanic.ImbuedShaman).", IMBUED, n(IMBUED), 4000,
        [fr.timed_attack("Firestorm", R("Imbued_Firestorm"), rng=6, los=True, comment="Tempête de feu."),
         fr.timed_attack("Wings", R("Imbued_Wings"), rng=5.5, los=True, comment="Souffle des ailes."),
         fr.timed_attack("Dive", R("Imbued_Dive"), rng=20, los=True, comment="Piqué."),
         fr.timed_attack("Arrow", R("Imbued_Arrow"), rng=24, los=True, comment="Flèche enflammée."),
         fr.melee(R("Imbued_Staff"), 3.2, (0.9, 1.3)), fr.chase(34, stop=2.4)],
        fr.walk(2.4), GENERATOR, sight=26, leash=40, home=True,
        timers=[fr.timer("Firestorm", (9, 12), (16, 20)), fr.timer("Wings", (4, 6), (10, 13)),
                fr.timer("Dive", (6, 8), (13, 16)), fr.timer("Arrow", (2, 4), (8, 10))],
        HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[LARVA] = fr.role(
        LARVA, "Larve de braise : appelée par le Chamane imprégné quand il se protège ; fonce et brûle.", LARVA, n(LARVA), 50,
        [fr.melee(R("Larva_Burn"), 2.0, (0.8, 1.2)), fr.chase(40, speed=1.0, stop=1.2)],
        fr.walk(4.6), GENERATOR, sight=30, leash=40, home=False, KnockbackScale=1.0, DeathAnimationTime=0.6)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(STONE, "Pierre imprégnée", "Se ramasse accroupi et se garde en main. Clic droit en visant le Champion "
           "chaman : lui retire une charge de protection. Se dissipe hors du Volcanique.", "Imbued stone",
           "Picked up by crouching, kept in hand. Right-click while aiming at the Champion shaman: removes one of his "
           "protection stacks. Fades outside the Volcanic fractal.")
    for role, f, e in ((WARRIOR, "Guerrier grawl", "Grawl warrior"), (GRAWL_SHAMAN, "Chaman grawl", "Grawl shaman"),
                       (TOTEM, "Totem du rituel", "Ritual totem"), (VETERAN, "Vétéran grawl", "Grawl veteran"),
                       (CHAMPION, "Champion chaman des grawls", "Champion grawl shaman"), (CAPTIVE, "Captif", "Captive"),
                       (BAT, "Chauve-souris de la mine", "Mine bat"), (IMBUED, "Le Chamane imprégné", "The Imbued Shaman"),
                       (LARVA, "Larve de braise", "Ember larva")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Lava_Burn", "Dans la lave", "In the lava")
    for name, f, e in zip(CRATER_STAGES, ["Cratère refroidi", "Cratère tiède", "Cratère brûlant", "Cratère rougeoyant",
                                          "Cratère en fusion"],
                          ["Cooled crater", "Warm crater", "Hot crater", "Glowing crater", "Molten crater"]):
        t.item(name, f, "Île du Chamane imprégné : chauffe puis devient de la lave active.", e,
               "Imbued Shaman's island: heats up, then turns into active lava.")
    t.put("effects.Nakasar_Fractal_Spreading_Flame", "Flamme qui se propage", "Spreading flame")
    msgs = {
        "intro": ("Volcanique : abattez les grawls du rituel ({count}), sous les rochers du volcan.",
                  "Volcanic: slay the grawls of the ritual ({count}), under the volcano's falling rocks."),
        "camp.done": ("Le totem du rituel s'effondre : la barrière se dissipe.", "The ritual totem collapses: the barrier fades."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "corridor.enter": ("Des rochers dévalent la pente derrière vous : abritez-vous dans les niches !",
                           "Boulders roll down the slope behind you: shelter in the alcoves!"),
        "boulder.hit": ("Écrasé par un rocher en feu !", "Crushed by a burning boulder!"),
        "champion.enter": ("Le Champion chaman est protégé : ramassez les pierres imprégnées (accroupi) et lancez-les-lui "
                           "(clic droit). Ne laissez pas ses vétérans rejoindre les captifs !",
                           "The Champion shaman is protected: pick up the imbued stones (crouch) and throw them at him "
                           "(right-click). Don't let his veterans reach the captives!"),
        "champion.stack": ("Une charge de protection en moins ({count} restantes).", "One protection stack fewer ({count} left)."),
        "champion.shield": ("Le Champion se protège de nouveau : une charge de protection, lancez-lui une pierre imprégnée !",
                            "The Champion protects himself again: one protection stack, throw an imbued stone at him!"),
        "champion.exposed": ("Le Champion n'est plus protégé : frappez-le !", "The Champion is no longer protected: strike him!"),
        "champion.veterans": ("Des vétérans sortent des grottes du sud et marchent vers les captifs !",
                              "Veterans leave the southern caves and march on the captives!"),
        "captive.lost": ("Un captif est jeté dans la lave ({count}/{total} perdus).",
                         "A captive is thrown into the lava ({count}/{total} lost)."),
        "captive.allLost": ("Tous les captifs sont perdus : le Champion recommence son rituel.",
                            "All the captives are lost: the Champion starts his ritual again."),
        "champion.reset": ("Le Champion chaman reprend des forces.", "The Champion shaman regains his strength."),
        "champion.victory": ("Le Champion chaman tombe : la barrière se dissipe.", "The Champion shaman falls: the barrier fades."),
        "champion.bonus": ("Tous les captifs sont sauvés : ils vous remercient d'éclats de Brume.",
                           "Every captive is saved: they thank you with Mist shards."),
        "stone.noTarget": ("Visez le Champion chaman pour lancer la pierre.", "Aim at the Champion shaman to throw the stone."),
        "stone.drop": ("Un rocher se brise en laissant une pierre imprégnée.", "A rock shatters, leaving an imbued stone."),
        "stone.crouch": ("Accroupissez-vous pour ramasser la pierre imprégnée.", "Crouch to pick up the imbued stone."),
        "stone.already": ("Vous portez déjà une pierre imprégnée.", "You already carry an imbued stone."),
        "camp.group": ("Un groupe de grawls charge !", "A pack of grawls charges!"),
        "lava.burn": ("La lave vous brûle : sortez-en !", "The lava burns you: get out!"),
        "mine.enter": ("La mine : sautez de rail en rail. Une chute ramène au départ.",
                       "The mine: jump from rail to rail. A fall brings you back to the start."),
        "landing.back": ("Rattrapé au-dessus de la lave : retour au départ de la mine.",
                         "Caught above the lava: back to the start of the mine."),
        "shaman.enter": ("Le Chamane imprégné ! Les cratères de l'île rougissent avant de cracher de la lave : "
                         "écartez-vous-en.",
                         "The Imbued Shaman! The island's craters glow before they spew lava: stay away from them."),
        "shaman.shield": ("Le Chamane se protège ({hits} coups) et plane vers un villageois : brisez le bouclier !",
                          "The Shaman shields himself ({hits} hits) and glides to a villager: break the shield!"),
        "shaman.broken": ("Bouclier brisé : le Chamane est étourdi.", "Shield broken: the Shaman is stunned."),
        "shaman.fed": ("Le Chamane se nourrit d'un villageois et reprend des forces.", "The Shaman feeds on a villager and regains strength."),
        "shaman.reset": ("Le Chamane imprégné reprend des forces.", "The Imbued Shaman regains his strength."),
        "shaman.victory": ("Le Chamane imprégné s'effondre dans la lave.", "The Imbued Shaman collapses into the lava."),
        "title.victory": ("Volcanique terminée", "Volcanic complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -------------------------------------------------------------------------------------------------

def java_layout():
    J = fc
    camp = J.jpoints([(x, 0, z) for x, z in CAMP_SPAWNS])
    captives = J.jpoints([(x, CH_STAND, z) for x, z in (ring_point(CH_CENTER, CAPTIVE_RADIUS, a) for a in CAPTIVE_ANGLES)])
    vgates = J.jpoints([(x, CH_STAND, z + 4) for x, z in VETERAN_GATES])
    crater_list = craters()
    crater_points = J.jpoints([(x, AR_STAND, z) for x, z in crater_list])
    crater_cells_java = ",\n".join("            " + J.jblocks(crater_cells(c)) for c in crater_list)
    stages = ", ".join(f'"{name}"' for name in CRATER_STAGES)
    villagers = J.jpoints([(ring_point(AR_CENTER, VILLAGER_RADIUS, a)[0], AR_STAND, ring_point(AR_CENTER, VILLAGER_RADIUS, a)[1])
                           for a in VILLAGER_ANGLES])
    # Chemin des rochers : de la bouche (en haut, au sud) au palier nord, un point par bloc (centre de la voie).
    path = J.jpoints([(x + 0.5, stand, z + 0.5) for x, z, stand in corridor_samples()[2:]], False)
    lx, lz, _, ls = LANDING_N
    ex0, ex1, ez0, ez1 = END_PAD
    mx0, mx1 = MINE
    mzs = [mine_z(x) for x in range(mx0, mx1 + 1)]
    mz0, mz1 = math.floor(min(mzs)) - MINE_HALF - 2, math.ceil(max(mzs)) + MINE_HALF + 2
    lava_low = min(mine_lava_y(x) for x in range(mx0, mx1 + 1))
    mine_box = J.jbox(mx0 - 2, mx1 + 2, lava_low - 1, CH_STAND + 8, mz0, mz1)
    jump_box = J.jbox(mx0 - 2, mx1 + 2, lava_low - 4, CH_STAND + 10, mz0, mz1)
    bats = J.jpoints([(x, math.floor(mine_base(x)) + 4, round(mine_z(x))) for x in (-62, -78, -94, -108)])
    return f"""package dev.nakasar.hytale.fractals.volcanic;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions du Volcanique, écrites par tools/generate_volcanic.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class VolcanicLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Camp des grawls. */
    public static final Box CAMP = {J.jbox(CAMP[0], CAMP[1], -1, 6, CAMP[2], CAMP[3])};
    public static final double[] TOTEM = {J.jpoint(TOTEM_AT, False)};
    public static final double[][] CAMP_SPAWNS = {camp};
    public static final int[][] GATE_CAMP = {J.jblocks(GATE_CAMP)};

    /**
     * Couloir aux rochers, galerie courbe qui descend vers le nord : chemin des rochers (pieds, un point par bloc, de
     * la bouche du haut au palier nord) et demi-largeur de la voie ; les niches sont hors de la voie.
     */
    public static final double[][] BOULDER_PATH = {path};
    public static final double CORRIDOR_HALF_WIDTH = {CORRIDOR_HALF};
    public static final double[] CORRIDOR_CHECKPOINT = {J.jpoint((0, 0, -19))};
    public static final double[] LANDING_CHECKPOINT = {J.jpoint((lx - 4, ls, lz - 1))};

    /** Arène du Champion chaman : captifs au bord nord (falaise), vétérans au fond des grottes du sud. */
    public static final double[] CHAMPION = {J.jpoint((CH_CENTER[0], CH_STAND, CH_CENTER[1]))};
    public static final double CHAMPION_RADIUS = {CH_RADIUS};
    public static final double[][] CAPTIVES = {captives};
    public static final double[][] VETERAN_GATES = {vgates};
    public static final int[][] GATE_CHAMPION = {J.jblocks(GATE_CH)};

    /** Mine. */
    public static final Box MINE = {mine_box};
    public static final List<Box> JUMP_ZONES = List.of({jump_box});
    public static final double[][] BATS = {bats};
    public static final Box END_PAD = {J.jbox(ex0, ex1, PAD_STAND - 1, PAD_STAND + 4, ez0, ez1)};
    public static final double[] END_CHECKPOINT = {J.jpoint((ex0 + 4, PAD_STAND, -94))};

    /** Île du Chamane imprégné, au milieu du lac de lave. */
    public static final double[] ARENA_CENTER = {J.jpoint((AR_CENTER[0], AR_STAND, AR_CENTER[1]))};
    public static final double ARENA_RADIUS = {AR_RADIUS};
    /** Lac de vraie lave autour de l'île : disques {{x, z, rayon}} et dessus de la lave (y du monde). */
    public static final double[][] LAKE = {{{", ".join(f"{{{x}, {z}, {r}}}" for x, z, r in LAKE_DISCS)}}};
    public static final double LAKE_SURFACE = {fc.GROUND_Y + LAKE_Y + 1};
    public static final double[][] VILLAGERS = {villagers};
    /** Cratères de l'île : centres (pieds) et cases du dessus ; blocs du froid à la lave active. */
    public static final double[][] CRATERS = {crater_points};
    public static final double CRATER_RADIUS = {CRATER_RADIUS};
    public static final int[][][] CRATER_CELLS = {{
{crater_cells_java}}};
    public static final String[] CRATER_STAGES = {{{stages}}};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private VolcanicLayout() {{
    }}
}}
"""


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name == LANDING:
        return (120, 200, 255)
    if name in (LAVA, "Rock_Magma_Cooled"):
        return (230, 90, 30)
    if name in CRATER_STAGES:
        return (150, 90, 60)
    if name == MIST:
        return (230, 140, 220)
    if name.startswith("Wood_") or name == "Rail":
        return (150, 100, 60)
    if name.startswith("Soil_Ash"):
        return (110, 100, 96)
    return (70, 64, 66)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    fc.write_keep_in_hand()
    fc.write_json(fc.OBJECTS / f"{STONE}.json", stone_item())
    fc.write_json(INTERACTIONS / "Nakasar_Fractal_Throw_Imbued_Stone.json", throw_interaction())
    fc.write_json(fc.ROOTS / "Root_Nakasar_Fractal_Throw_Imbued_Stone.json",
                  {"Interactions": ["Nakasar_Fractal_Throw_Imbued_Stone"], "RequireNewClick": True})
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Lava_Burn.png", (255, 120, 40), "flame")
    for args in crater_blocks():
        fc.write_block(LANG, *args)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Spreading_Flame.png", (255, 140, 50), "flame")
    fc.write_json(fc.SERVER / "Entity/Damage/Nakasar_Fractal_Fire.json", fire_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(INTERACTIONS / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fc.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p = course_prefab()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    counts = fc.write_instance(INSTANCE, "Volcanique", PREFAB_DIR, sections, SPAWN, "#7a6a3a",
                                WEATHER, fc.weather("#5a2e28", "#d07040", "#9a5a40", (24, 260), 0.35, "#ffc890"), "15:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Volcanique : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules, {len(mine_segments())} tronçons de rails")
    if preview:
        fc.top_view(p, preview / "volcanique_dessus.png", color_of)


if __name__ == "__main__":
    main()
