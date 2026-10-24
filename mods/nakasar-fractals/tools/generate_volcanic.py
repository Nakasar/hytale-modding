#!/usr/bin/env python3
"""Génère le Volcanique (Volcanic), troisième fractale de la saison 1 (étape 6 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_volcanic.py [--preview DOSSIER]

Le déroulé de GW2, dans l'ordre :

1. le camp des grawls : des groupes de 7 grawls qui chargent, autour du totem du rituel (sa vie, fixée par le Java,
   montre ce qu'il reste à abattre ; sa barre se voit de toute la fractale), des rochers qui tombent du volcan ;
2. le couloir aux rochers : des rochers en feu dévalent toutes les 5 s, on s'abrite dans les niches ; un rocher coûte
   60 % des PV, brûle et laisse une traînée de feu ;
3. le Champion chaman des grawls, au bord d'une falaise au-dessus du lac de lave du volcan : huit charges de
   protection que seules les pierres imprégnées (lâchées par les rochers qui tombent, ramassées accroupi et gardées en
   main) retirent ; ses vétérans sortent des grottes du sud et marchent lentement vers les trois captifs du bord nord ;
   vétérans et pierres seulement tant qu'il est protégé, nouvelle phase de protection complète à 50 % ;
4. la mine : des rails sur des planches au-dessus de la lave, des chauves-souris ; une chute ramène au départ du
   tronçon ; au bout, une descente jusqu'au lac ;
5. le Chamane imprégné, sur une île au milieu du lac (on la voit du bord de la falaise du Champion) : petits cratères
   qui rougissent puis crachent de la lave, flèche enflammée qui se propage, piqué, souffle des ailes, tempête de feu ;
   à chaque quart de sa vie, un bouclier de 40 coups, des larves de braise, et il plane lentement vers un villageois
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
CORRIDOR = (-3, 3, -91, -22)            # x0, x1, z0 (nord), z1 (sud)
ALCOVES = [(-32, 1), (-44, -1), (-56, 1), (-68, -1), (-80, 1)]   # (z de départ, côté)
LANDING_N = (-3, 3, -97, -92)
BOULDER_START = (0.5, 0, -95.5)
BOULDER_END_Z = -21.5
PASSAGE = (-20, -4, -96, -92)
CH_CENTER = (-34, -94)
CH_RADIUS = 14
CAPTIVE_ANGLES = [240, 270, 300]       # au nord, au bord de la falaise qui tombe dans la lave du volcan
CAPTIVE_RADIUS = 12
VETERAN_GATES = [(-41, -80), (-27, -80)]   # grottes du côté sud, en face des captifs
GATE_CH = [(-49, y, z) for y in range(0, 5) for z in range(-96, -91)]
MINE = (-118, -50)                      # x de fin (ouest) et de départ (est) de la mine
MINE_Z = (-96, -92)
LAVA_Y = -7
END_PAD = (-124, -116, -98, -90)        # x0, x1, z0, z1, debout à 2
PAD_STAND = 2
# Lac de lave du volcan, en bas de la falaise du Champion : surface en LAKE_Y, union de disques (centre x, z, rayon).
LAKE_Y = -18
LAKE_DISCS = [(-84, -146, 40), (-38, -124, 20), (-122, -122, 16)]
# Île du Chamane imprégné au milieu du lac, deux blocs au-dessus de la lave ; on la voit du bord de la falaise.
AR_CENTER = (-84, -146)
AR_RADIUS = 22
AR_STAND = LAKE_Y + 3
VILLAGER_ANGLES = [45, 135, 225, 315]
VILLAGER_RADIUS = 19
ENTRY_ANGLE = 180
# Descente du bout de la mine à l'île : (x, z, debout) ; chaussée au-dessus de la lave en bas.
DESCENT = [(-120, -99, PAD_STAND), (-122, -114, -5), (-114, -132, -11), (-105, -146, AR_STAND)]
DESCENT_WIDTH = 2.6
# Petits cratères de l'île (rayon CRATER_RADIUS) : chauffent puis deviennent de la lave active (Java).
CRATER_RADIUS = 2.3
CRATER_COUNT = 11
CRATER_STAGES = ["Nakasar_Fractal_Crater_Cold", "Nakasar_Fractal_Crater_Warm_1", "Nakasar_Fractal_Crater_Warm_2",
                 "Nakasar_Fractal_Crater_Warm_3", "Nakasar_Fractal_Crater_Lava"]
REWARD_AT = (-86, AR_STAND, -146)
END_EXIT_AT = (-82, AR_STAND, -146)
JUMP_ZONES = [(-120, -48, LAVA_Y - 4, 14, -101, -87)]

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
PLANKS = "Wood_Darkwood_Planks"
BEAM = "Wood_Darkwood_Beam"
pick = fc.pick
CAMP_SIGHT = 56                          # les grawls du camp voient tout le camp (40 x 52)


def ring_point(center, radius, angle, rounded=True):
    x = center[0] + math.cos(math.radians(angle)) * radius
    z = center[1] + math.sin(math.radians(angle)) * radius
    return (round(x), round(z)) if rounded else (round(x, 1), round(z, 1))


def mine_segments():
    """Tronçons de rails de la mine : (x0, x1, debout), d'est en ouest ; trous de 2 à 3 blocs entre eux. Le dernier
    s'arrête un bloc avant le palier d'arrivée : jamais de rail sur le palier (point de retour)."""
    out, x, k = [], MINE[1], 0
    levels = [0, 1, 1, 2, 1, 2, 3, 2, 2, 3, 2, 2]
    stop = END_PAD[1] + 2
    while x >= stop:
        length = 5 if k % 3 else 4
        out.append((max(x - length + 1, stop), x, levels[k % len(levels)]))
        x -= length + (3 if k % 2 else 2)
        k += 1
    return out


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
    for (x, y, z) in GATE_CAMP:
        p.set(x, y, z, MIST)
    # Couloir aux rochers (ouvert sur le ciel), niches, palier nord.
    cx0, cx1, cz0, cz1 = CORRIDOR
    for z in range(LANDING_N[2], cz1 + 1):
        for x in range(cx0 - 1, cx1 + 2):
            p.set(x, -1, z, pick(ROCK, x, -1, z) if cx0 <= x <= cx1 else pick(BRICK, x, -1, z))
            p.set(x, -2, z, pick(ROCK, x, -2, z))
            if x in (cx0 - 1, cx1 + 1):
                for y in range(0, 8):
                    p.set(x, y, z, pick(ROCK, x, y, z))
    for zs, side in ALCOVES:
        wall = cx1 + 1 if side > 0 else cx0 - 1
        for z in range(zs - 2, zs + 1):
            for dx in range(0, 3):
                x = wall + side * dx
                p.set(x, -1, z, pick(GROUND, x, -1, z))
                for y in range(0, 4):
                    p.set(x, y, z, go.AIR)
                for y in range(4, 8):
                    p.set(x, y, z, pick(ROCK, x, y, z))
            p.set(wall + side * 3, 0, z, pick(ROCK, 0, 0, z))
            for y in range(0, 8):
                p.set(wall + side * 3, y, z, pick(ROCK, wall, y, z))
        for dx in range(0, 4):
            for y in range(0, 8):
                p.set(wall + side * dx, y, zs - 3, pick(ROCK, dx, y, zs))
                p.set(wall + side * dx, y, zs + 1, pick(ROCK, dx, y, zs))
        p.set(wall + side * 2, 3, zs - 1, "Furniture_Crude_Torch")
    lx0, lx1, lz0, lz1 = LANDING_N
    for x in range(lx0 - 1, lx1 + 2):   # bouche du volcan au nord : d'où sortent les rochers
        for y in range(0, 9):
            p.set(x, y, lz0 - 1, pick(ROCK, x, y, lz0))
        p.set(x, 5, lz0, pick(ROCK, x, 5, lz0))
    for y in range(0, 4):
        for x in range(-1, 3):
            p.set(x, y, lz0 - 1, LAVA if y < 3 else pick(ROCK, x, y, lz0))
    # Passage vers l'ouest et arène du Champion.
    px0, px1, pz0, pz1 = PASSAGE
    for x in range(px0, cx0):
        for z in range(pz0, pz1 + 1):
            p.set(x, -1, z, pick(GROUND, x, -1, z))
            p.set(x, -2, z, pick(ROCK, x, -2, z))
        for z in (pz0 - 1, pz1 + 1):
            for y in range(0, 6):
                p.set(x, y, z, pick(ROCK, x, y, z))
    for y in range(0, 8):   # le mur ouest du couloir s'ouvre sur le passage
        for z in range(pz0, pz1 + 1):
            p.set(cx0 - 1, y, z, go.AIR if y < 5 else pick(ROCK, 0, y, z))
    # Arène du Champion : au nord, le bord d'une falaise au-dessus du lac de lave du volcan (la vue
    # reste dégagée sur l'île du Chamane, sans muret) ; au sud, le mur de roche et les grottes des vétérans.
    chx, chz = CH_CENTER
    fc.disc(p, chx, chz, CH_RADIUS, 0, lambda x, z: pick(GROUND, x, 0, z), ROCK, 8)
    for a in range(0, 360, 6):
        x, z = ring_point(CH_CENTER, CH_RADIUS + 1, a)
        if abs(z - chz) <= 3 or z < chz - 4 or any(abs(x - gx) <= 2 and z > chz for gx, _ in VETERAN_GATES):
            continue   # nord : rien entre l'arène et le vide, la vue sur l'île reste dégagée
        for y in range(-1, 4):
            p.set(x, y, z, pick(ROCK, x, y, z))
    for a in CAPTIVE_ANGLES:   # cages des captifs, au bord de la falaise
        x, z = ring_point(CH_CENTER, CAPTIVE_RADIUS, a)
        p.set(x, -1, z, "Rock_Magma_Cooled")
        p.set(x, 0, z - 1, "Deco_Trork_Cage")
    for gx, gz in VETERAN_GATES:   # grottes : un porche de roche, ouvert vers l'arène
        for dx in range(-3, 4):
            for dz in range(-2, 7):
                x, z = gx + dx, gz + dz
                p.set(x, -1, z, pick(GROUND, x, -1, z))
                p.set(x, -2, z, pick(ROCK, x, -2, z))
                if dz < 1:
                    continue
                inside = abs(dx) <= 1 and dz <= 5
                for y in range(0, 6):
                    p.set(x, y, z, go.AIR if inside and y < 3 else pick(ROCK, x, y, z))
        p.set(gx, 2, gz + 1, "Furniture_Crude_Torch")
    for (x, y, z) in GATE_CH:
        p.set(x, y, z, MIST)
    for x in range(-49, chx - CH_RADIUS + 1):
        for z in range(MINE_Z[0], MINE_Z[1] + 1):
            p.set(x, -1, z, pick(GROUND, x, -1, z))
    # Mine : rails sur planches au-dessus de la lave.
    mz0, mz1 = MINE_Z
    for x in range(MINE[0] - 2, MINE[1] + 1):
        for z in range(mz0 - 4, mz1 + 5):
            p.set(x, LAVA_Y, z, LAVA if (x * 5 + z * 3) % 7 else "Rock_Magma_Cooled")
            p.set(x, LAVA_Y - 1, z, pick(ROCK, x, LAVA_Y - 1, z))
        for z in (mz0 - 5, mz1 + 5):
            for y in range(LAVA_Y, 12):
                p.set(x, y, z, pick(ROCK, x, y, z))
    for x in range(MINE[1] - 3, MINE[1] + 1):   # départ de la mine : plate-forme sûre
        for z in range(mz0, mz1 + 1):
            p.set(x, -1, z, LANDING)
    for x0, x1, stand in mine_segments():
        for x in range(x0, x1 + 1):
            for z in range(mz0 + 1, mz1):
                p.set(x, stand - 1, z, PLANKS)
            p.set(x, stand, mz0 + 2, "Rail")
        for x in (x0, x1):
            for y in range(LAVA_Y + 1, stand - 1):
                p.set(x, y, mz0 + 1, BEAM)
                p.set(x, y, mz1 - 1, BEAM)
    ex0, ex1, ez0, ez1 = END_PAD
    for x in range(ex0, ex1 + 1):
        for z in range(ez0, ez1 + 1):
            p.set(x, PAD_STAND - 1, z, LANDING if x >= ex1 - 2 else pick(GROUND, x, PAD_STAND - 1, z))
            for y in range(LAVA_Y, PAD_STAND - 1):
                p.set(x, y, z, pick(ROCK, x, y, z))
    p.set(ex1 - 1, PAD_STAND, ez1, "Deco_Bone_Skulls")
    p.set(ex1 - 2, PAD_STAND, ez1, "Deco_Bone_Pile")
    p.set(ex1, PAD_STAND, ez1, "Furniture_Ancient_Crate")
    island(p)
    dress(p)
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
VOLCANO = (-78, -28, 34, 64)            # centre x, z, rayon, hauteur : le volcan d'où viennent les rochers


def ridge(p, x0, x1, z0, z1, low, high, seed):
    """Crête rocheuse irrégulière (falaise du canyon) sur la boîte, dessus entre `low` et `high`."""
    tops = {}
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for z in range(min(z0, z1), max(z0, z1) + 1):
            tops[(x, z)] = low + round((high - low) * (fn.fbm2(x, z, 7, 3, seed) + 1) / 2)
    inland = fn.edge_distance(tops)
    cells = fn.island(p, tops, lambda x, z: tops[(x, z)] - LAVA_Y + 4 + min(10, inland[(x, z)] * 2), seed, hang=0.0,
                      theme=THEME)
    fn.dress(p, cells, THEME, seed, trees=0.03, spacing=7, bushes=0.05, boulders=0.004)


def volcano(p):
    """Cône du volcan : pentes de cendre et de roche, coulées de lave figée qui luisent, cratère de lave."""
    cx, cz, r, h = VOLCANO
    tops = {}
    for x in range(cx - r - 4, cx + r + 5):
        for z in range(cz - r - 4, cz + r + 5):
            d = math.hypot(x - cx, z - cz)
            reach = r * (0.9 + 0.2 * (fn.fbm2(x, z, 12, 2, 61) + 1) / 2)
            if d > reach:
                continue
            t = 1 - d / reach
            y = LAVA_Y + round(h * t ** 1.25 + 3 * fn.fbm2(x, z, 6, 2, 62))
            if d < 7:
                y = LAVA_Y + h - 8 + round(d * 0.6)     # cratère
            tops[(x, z)] = y
    lava = lambda x, z: (math.hypot(x - cx, z - cz) < 6 or
                         abs(math.sin(math.atan2(z - cz, x - cx) * 3 + fn.fbm2(x, z, 9, 2, 63))) < 0.06)
    inland = fn.edge_distance(tops)
    cells = fn.island(p, tops, lambda x, z: tops[(x, z)] - LAVA_Y + 4 + min(30, inland[(x, z)] * 1.3), 61, hang=0.0,
                      theme=THEME,
                      grass=lambda x, z: "Rock_Volcanic_Cracked_Lava" if lava(x, z) else fn.soil(x, z, 61, THEME["soil"]))
    fn.dress(p, [c for c in cells if math.hypot(c[0] - cx, c[2] - cz) > r * 0.45], THEME, 64, trees=0.02, spacing=8,
             bushes=0.04, boulders=0.008, density=0.25)


def dress(p):
    """Terres brûlées autour du camp et des arènes, falaises du canyon aux rochers et de la mine, volcan au loin,
    îlots de roche volcanique. Jamais de sol en plus au-dessus de la lave de la mine ni entre deux sauts."""
    def footprint(y, x0, x1, z0, z1):
        return {(x, z): y for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) if (x, y, z) in p.blocks}

    # Camp : terres brûlées et arbres morts autour des murets, pas au nord (couloir).
    x0, x1, z0, z1 = CAMP
    camp = footprint(-1, x0, x1, z0, z1)
    tops = fn.rim(camp, 4, 13, seed=21, block=lambda x, z: z < z0 + 2 and abs(x) < 10)
    fn.natural_ground(p, tops, THEME, seed=21, trees=0.03, spacing=7, density=0.3)
    # Canyon aux rochers : falaises de part et d'autre (les niches restent creusées dans le mur).
    cx0, cx1, cz0, cz1 = CORRIDOR
    ridge(p, cx1 + 2, cx1 + 12, LANDING_N[2] - 2, z0 - 1, 7, 14, 23)
    ridge(p, cx0 - 2, cx0 - 12, PASSAGE[3] + 3, z0 - 1, 7, 14, 24)
    ridge(p, LANDING_N[0] - 3, LANDING_N[1] + 12, LANDING_N[2] - 10, LANDING_N[2] - 2, 9, 18, 25)
    # Arène du Champion : terres brûlées autour du cercle (les brèches des vétérans restent ouvertes).
    chx, chz = CH_CENTER
    ring = {}
    for x in range(chx - CH_RADIUS - 2, chx + CH_RADIUS + 3):
        for z in range(chz - CH_RADIUS - 2, chz + CH_RADIUS + 3):
            if math.hypot(x - chx, z - chz) <= CH_RADIUS + 1.5:
                ring[(x, z)] = -1
    tops = fn.rim(ring, 4, 12, seed=27, block=lambda x, z: abs(z - chz) <= 6 or z < chz)   # nord : la falaise
    tops = {c: y for c, y in tops.items() if not any((c[0], yy, c[1]) in p.blocks for yy in range(-1, 6))}
    fn.natural_ground(p, tops, THEME, seed=27, trees=0.025, spacing=7, density=0.3)
    # Mine : hautes parois rocheuses au-dessus des murs de la coulée de lave.
    mz0, mz1 = MINE_Z
    ridge(p, MINE[0] - 2, MINE[1], mz0 - 13, mz0 - 6, 12, 20, 29)
    ridge(p, MINE[0] - 2, MINE[1], mz1 + 6, mz1 + 13, 12, 20, 30)
    # Bout de la mine : une crête à l'ouest du palier, d'où part la descente vers le lac.
    ex0, ex1, ez0, ez1 = END_PAD
    ridge(p, ex0 - 12, ex0 - 1, ez0 + 1, ez1 + 8, 8, 15, 35)
    volcano(p)
    caldera(p)
    fn.scatter_islets(p, (-200, 70, -200, 90), 22, (LAVA_Y - 20, 20), (3, 9), THEME, seed=33)


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
    tout autour. La lave du lac brûle (Java : Volcanic.lavaFloor)."""
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
    for x, z in lake:
        p.set(x, LAKE_Y, z, LAVA if fn.hash01(x, 3, z, 83) > 0.12 else "Rock_Magma_Cooled")
        p.set(x, LAKE_Y - 1, z, pick(ROCK, x, LAKE_Y - 1, z))
    near = lambda x, z, d: any((x + dx, z + dz) in lake for dx in range(-d, d + 1) for dz in range(-d, d + 1))
    for (x, z), low in columns.items():   # falaises : ce qui borde le lac descend jusqu'au fond
        if low > LAKE_Y - 1 and near(x, z, 2):
            for y in range(LAKE_Y - 1, low):
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
    fn.dress(p, [c for c in cells if inland[(c[0], c[2])] > 1], THEME, 88, trees=0.02, spacing=8, bushes=0.04,
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
        "corridor.enter": ("Des rochers dévalent le couloir : abritez-vous dans les niches !",
                           "Boulders roll down the corridor: shelter in the alcoves!"),
        "boulder.hit": ("Écrasé par un rocher en feu !", "Crushed by a burning boulder!"),
        "champion.enter": ("Le Champion chaman est protégé : ramassez les pierres imprégnées (accroupi) et lancez-les-lui "
                           "(clic droit). Ne laissez pas ses vétérans rejoindre les captifs !",
                           "The Champion shaman is protected: pick up the imbued stones (crouch) and throw them at him "
                           "(right-click). Don't let his veterans reach the captives!"),
        "champion.stack": ("Une charge de protection en moins ({count} restantes).", "One protection stack fewer ({count} left)."),
        "champion.shield": ("Le Champion se protège de nouveau : toutes ses charges sont revenues, ses vétérans repartent !",
                            "The Champion protects himself again: all his stacks are back, his veterans march again!"),
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
    captives = J.jpoints([(x, 0, z) for x, z in (ring_point(CH_CENTER, CAPTIVE_RADIUS, a) for a in CAPTIVE_ANGLES)])
    vgates = J.jpoints([(x, 0, z + 4) for x, z in VETERAN_GATES])
    crater_list = craters()
    crater_points = J.jpoints([(x, AR_STAND, z) for x, z in crater_list])
    crater_cells_java = ",\n".join("            " + J.jblocks(crater_cells(c)) for c in crater_list)
    stages = ", ".join(f'"{name}"' for name in CRATER_STAGES)
    villagers = J.jpoints([(ring_point(AR_CENTER, VILLAGER_RADIUS, a)[0], AR_STAND, ring_point(AR_CENTER, VILLAGER_RADIUS, a)[1])
                           for a in VILLAGER_ANGLES])
    alcoves = ", ".join(f"{{{zs - 2}, {zs}, {side}}}" for zs, side in ALCOVES)
    zones = ",\n".join("            " + J.jbox(*b[:2], b[2], b[3], *b[4:]) for b in JUMP_ZONES)
    cx0, cx1, cz0, cz1 = CORRIDOR
    lx0, lx1, lz0, lz1 = LANDING_N
    ex0, ex1, ez0, ez1 = END_PAD
    mx0, mx1 = MINE
    bats = J.jpoints([(x, 4, -94) for x in (-62, -78, -94, -108)])
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

    /** Couloir aux rochers : voie (x0..x1, z nord..sud), niches {{z0, z1, côté}}, palier nord, départ des rochers. */
    public static final Box CORRIDOR = {J.jbox(cx0, cx1, -1, 5, lz0, cz1)};
    public static final int CORRIDOR_X0 = {cx0};
    public static final int CORRIDOR_X1 = {cx1};
    public static final int[][] ALCOVES = {{{alcoves}}};
    public static final double[] BOULDER_START = {J.jpoint(BOULDER_START, False)};
    public static final double BOULDER_END_Z = {BOULDER_END_Z};
    public static final double[] CORRIDOR_CHECKPOINT = {J.jpoint((0, 0, -19))};
    public static final double[] LANDING_CHECKPOINT = {J.jpoint((-6, 0, -94))};

    /** Arène du Champion chaman : captifs au bord nord (falaise), vétérans au fond des grottes du sud. */
    public static final double[] CHAMPION = {J.jpoint((CH_CENTER[0], 0, CH_CENTER[1]))};
    public static final double CHAMPION_RADIUS = {CH_RADIUS};
    public static final double[][] CAPTIVES = {captives};
    public static final double[][] VETERAN_GATES = {vgates};
    public static final int[][] GATE_CHAMPION = {J.jblocks(GATE_CH)};

    /** Mine. */
    public static final Box MINE = {J.jbox(mx0 - 2, mx1 + 2, -2, 8, MINE_Z[0] - 3, MINE_Z[1] + 3)};
    public static final List<Box> JUMP_ZONES = List.of(
{zones});
    public static final double[][] BATS = {bats};
    public static final Box END_PAD = {J.jbox(ex0, ex1, PAD_STAND - 1, PAD_STAND + 4, ez0, ez1)};
    public static final double[] END_CHECKPOINT = {J.jpoint((ex0 + 4, PAD_STAND, -94))};

    /** Île du Chamane imprégné, au milieu du lac de lave. */
    public static final double[] ARENA_CENTER = {J.jpoint((AR_CENTER[0], AR_STAND, AR_CENTER[1]))};
    public static final double ARENA_RADIUS = {AR_RADIUS};
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
