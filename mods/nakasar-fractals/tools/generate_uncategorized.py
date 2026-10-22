#!/usr/bin/env python3
"""Génère l'Inclassable (Uncategorized), deuxième fractale de la saison 1 (étape 6 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_uncategorized.py [--preview DOSSIER]

Le déroulé de GW2, dans l'ordre :

1. les plates-formes des harpies : vingt plates-formes de marbre qui montent d'un bloc chacune ; les harpies visent
   un joueur (cercle rouge) et, dès le niveau 10, le projettent (pas dos au vide) ; une chute ramène au départ ;
2. la cour de la prison : le générateur à détruire, puis les quatre prisonniers libérés l'un après l'autre (lapin
   enragé, saboteur aux bombes, chaman du feu, ettin) ;
3. l'escalier mortel : quatre tourelles balaient l'escalier de lignes rouges ; en haut, trois consoles à activer
   ensemble (fenêtre de 12 s seul, 8 s à deux, 4 s au-delà) les éteignent ;
4. Vieux Tom (golem de forge) : rafale de cercles, attraction, éclair qui rebondit ; le gaz monte toutes les 40 s,
   le ventilateur l'évacue (dès le niveau 12, deux batteries à recharger avec des larmes de Brume) ;
5. les plates-formes de lueur, translucides, au-dessus du vide ;
6. l'Asura fou, invulnérable sur son estrade : salves, orbes qui poursuivent, et ses golems de cristal réveillés un à
   un puis tous ensemble ; charges + et - pendant tout le combat (seul : deux pylônes).

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Uncategorized`, les blocs, la larme
de Brume, les effets, les particules, les modèles et rôles des ennemis, la langue `nakasar_fractals_uncategorized.lang`
et `uncategorized/UncategorizedLayout.java`. Repère et hauteurs comme la Falaise : y monde = GROUND_Y + y prefab,
« debout à y » : le sol est en y - 1.
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

LANG = "nakasar_fractals_uncategorized"
GENERATOR = "generate_uncategorized.py"
INSTANCE = "Nakasar_Fractal_Uncategorized"
WEATHER = "Nakasar_Fractal_Weather_Uncategorized"
PREFAB_DIR = "Uncategorized"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/uncategorized/UncategorizedLayout.java"
ITEMS = go.ITEMS / "Uncategorized"
INTERACTIONS = go.INTERACTIONS / "Uncategorized"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/Uncategorized"
GROUND_Y = fc.GROUND_Y
AIR = go.AIR

# --- lieux (y = debout à) ---------------------------------------------------------------------------
SPAWN = (0, 0, 44)
START = (0, 40, 6)                      # disque de départ (x, z, rayon), debout à 0
PATH1 = [(0, 30), (0, 26), (3, 23), (7, 23), (10, 20), (10, 16), (7, 13), (3, 13), (-1, 13), (-4, 10), (-4, 6),
         (-1, 3), (3, 3), (6, 0), (6, -4), (3, -7), (-1, -7), (-4, -10), (-4, -14), (-4, -18)]
YARD = 20                               # cour de la prison
PLAZA = (-12, 12, -40, -21)
GENERATOR_AT = (0, YARD, -31)
CELLS = [(-1, -26), (1, -26), (-1, -35), (1, -35)]   # (côté, z du centre) : lapin, saboteur, chaman, ettin
GATE_YARD = [(x, y, -41) for x in range(-3, 4) for y in range(YARD, YARD + 5)]
STAIRS = (-3, 3, -42, -89)              # x0, x1, z du bas, z du haut ; +0,5 par case
TOP = YARD + 24                         # palier des consoles (44)
LANDING_TOP = (-7, 7, -100, -90)
TURRETS_X = [-3, -1, 1, 3]
TURRET_Z = -91
CONSOLES = [(-5, TOP, -99), (0, TOP, -99), (5, TOP, -99)]
GATE_TOP = [(x, y, -101) for x in range(-3, 4) for y in range(TOP, TOP + 4)]
ROOM = (-15, 15, -135, -105)            # salle de Vieux Tom, debout à TOP
TOM_AT = (0.5, TOP, -122.5)
FAN = (6, TOP, -134)
BATTERIES = [(13, TOP, -133), (-13, TOP, -107)]
GATE_TOM = [(x, y, -136) for x in range(-3, 4) for y in range(TOP, TOP + 4)]
PAD2 = (-3, 3, -143, -140)              # départ des plates-formes de lueur, debout à TOP
ARENA = TOP + 20                        # arène de l'Asura (64)
ARENA_CENTER = (0, -214)
ARENA_RADIUS = 17
ASURA_AT = (0.5, ARENA + 2, -228.5)
GOLEM_ANGLES = [45, 135, 225, 315]
GOLEM_RADIUS = 11
PYLONS = [(-6, -218, 1), (6, -218, -1)]
REWARD_AT = (-2, ARENA, -212)
END_EXIT_AT = (2, ARENA, -212)

# Zones de saut : une chute ramène à la dernière plate-forme sûre (seul le départ en porte).
JUMP_ZONES = [(-12, 16, -16, YARD + 6, -22, 47), (-12, 12, TOP - 14, ARENA + 6, -197, -139)]

# --- blocs et rôles -------------------------------------------------------------------------------------
LANDING = gc.LANDING
MIST = gc.MIST_BARRIER
CONSOLE = "Nakasar_Fractal_Console"
FAN_BLOCK = "Nakasar_Fractal_Fan"
BATTERY = "Nakasar_Fractal_Battery"
BATTERY_ON = "Nakasar_Fractal_Battery_Charged"
GLIMMER = "Nakasar_Fractal_Glimmer"
PYLON = "Nakasar_Fractal_Charge_Pylon"
TEAR = "Nakasar_Fractal_Mist_Tear"

HARPY = "Nakasar_Fractal_Harpy"
GENERATOR_ROLE = "Nakasar_Fractal_Prison_Generator"
RABBIT = "Nakasar_Fractal_Rabid_Rabbit"
SABOTEUR = "Nakasar_Fractal_Saboteur"
SHAMAN = "Nakasar_Fractal_Fire_Shaman"
ETTIN = "Nakasar_Fractal_Ettin"
TURRET = "Nakasar_Fractal_Turret"
TOM = "Nakasar_Fractal_Old_Tom"
ASURA = "Nakasar_Fractal_Mad_Asura"
CRYSTAL_GOLEM = "Nakasar_Fractal_Crystal_Golem"
FOE_ROLES = [HARPY, GENERATOR_ROLE, RABBIT, SABOTEUR, SHAMAN, ETTIN, TURRET, TOM, ASURA, CRYSTAL_GOLEM]

MARBLE = ["Rock_Marble_Brick_Smooth", "Rock_Marble_Brick_Smooth", "Rock_Marble_Brick"]
UNDER = ["Rock_Marble", "Rock_Marble_Cobble", "Rock_Stone", "Rock_Marble"]
WALL = "Rock_Marble_Brick"
TRIM = "Rock_Gold_Brick_Smooth"
PINK = "Rock_Crystal_Pink_Block"
LAB = ["Rock_Stone_Brick", "Rock_Stone_Brick", "Rock_Quartzite_Brick"]
pick = fc.pick


# --- géométrie -----------------------------------------------------------------------------------------

def stair_level(z):
    """Hauteur (debout) de l'escalier à la case z : 20,5 en bas (z = -42), 44 en haut (z = -89)."""
    return YARD + 0.5 * (STAIRS[2] - z + 1)


def path2():
    """Plates-formes de lueur : (x, z, debout), 2 × 2, +1 chacune, de TOP + 1 à ARENA."""
    out = []
    n = ARENA - TOP
    for k in range(n):
        z = -146 - round(k * 48 / (n - 1))
        x = round(4 * math.sin(k * 0.85))
        out.append((x, z, TOP + 1 + k))
    return out


def golems():
    cx, cz = ARENA_CENTER
    return [(round(cx + math.cos(math.radians(a)) * GOLEM_RADIUS, 1), round(cz + math.sin(math.radians(a)) * GOLEM_RADIUS, 1))
            for a in GOLEM_ANGLES]


def cell_box(side, zc):
    """Cellule : x0..x1 (intérieur + murs), z0..z1 ; porte de barreaux sur x = ±13."""
    x0, x1 = (13, 18) if side > 0 else (-18, -13)
    return x0, x1, zc - 3, zc + 3


def door_cells(side, zc):
    x = 13 if side > 0 else -13
    return [(x, y, z) for y in range(YARD, YARD + 4) for z in range(zc - 1, zc + 2)]


def course_prefab():
    p = go.Prefab()
    # Départ : disque sûr au-dessus des Brumes.
    sx, sz, r = START
    fc.disc(p, sx, sz, r, 0, lambda x, z: LANDING if math.hypot(x - sx, z - sz) <= r - 1.5 else TRIM, UNDER, 6)
    # Plates-formes des harpies.
    for k, (x, z) in enumerate(PATH1):
        stand = k + 1
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                p.set(x + dx, stand - 1, z + dz, PINK if dx == dz == 0 else pick(MARBLE, x + dx, stand, z + dz))
                p.set(x + dx, stand - 2, z + dz, "Rock_Marble")
        p.set(x, stand - 3, z, "Rock_Marble_Brick_Pillar_Base")
    # Cour de la prison.
    x0, x1, z0, z1 = PLAZA
    fc.box_floor(p, x0, x1, z0, z1, YARD, lambda x, z: pick(MARBLE, x, YARD, z), TRIM)
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = min(x - x0, x1 - x, z - z0, z1 - z)
            for y in range(YARD - 2 - min(10, edge), YARD - 1):
                if edge < 2 or y == YARD - 2 - min(10, edge):
                    p.set(x, y, z, pick(UNDER, x, y, z))
    for side, zc in CELLS:
        cx0, cx1, cz0, cz1 = cell_box(side, zc)
        for x in range(cx0, cx1 + 1):
            for z in range(cz0, cz1 + 1):
                p.set(x, YARD - 1, z, "Rock_Marble_Brick")
                p.set(x, YARD + 5, z, WALL)
                p.set(x, YARD - 2, z, "Rock_Marble")
        fc.walls(p, cx0, cx1, cz0, cz1, YARD, YARD + 4, WALL)
        for (x, y, z) in door_cells(side, zc):
            p.set(x, y, z, "Deco_Iron_Bars")
        p.set((cx0 + cx1) // 2, YARD + 4, zc, "Deco_Lantern")
    # Murets du fond, lanternes de la cour, barrière vers l'escalier.
    for x in range(x0, x1 + 1):
        if abs(x) > 3:
            p.set(x, YARD, z0, "Rock_Marble_Brick_Half")
    for x, z in ((-11, -22), (11, -22), (-11, -39), (11, -39)):
        p.set(x, YARD, z, "Rock_Marble_Brick_Pillar_Middle")
        p.set(x, YARD + 1, z, "Furniture_Temple_Light_Lantern")
    for (x, y, z) in GATE_YARD:
        p.set(x, y, z, MIST)
    p.set(-4, YARD + 4, -41, TRIM)
    p.set(4, YARD + 4, -41, TRIM)
    # Escalier mortel.
    sx0, sx1, zb, zt = STAIRS
    for z in range(zt, zb + 1):
        level = stair_level(z)
        for x in range(sx0, sx1 + 1):
            fc.step_blocks(p, x, z, level, pick(MARBLE, x, 0, z), "Rock_Marble_Brick_Half")
            for y in range(math.floor(level) - 4, math.floor(level) - 1):
                if x in (sx0, sx1) or y == math.floor(level) - 4:
                    p.set(x, y, z, pick(UNDER, x, y, z))
        if z % 6 == 0:
            for x in (sx0 - 1, sx1 + 1):
                p.set(x, math.floor(level) - 1, z, TRIM)
    # Palier des consoles.
    lx0, lx1, lz0, lz1 = LANDING_TOP
    fc.box_floor(p, lx0, lx1, lz0, lz1, TOP, lambda x, z: pick(MARBLE, x, TOP, z), TRIM)
    for x in range(lx0, lx1 + 1):
        for z in range(lz0, lz1 + 1):
            p.set(x, TOP - 2, z, "Rock_Marble")
    for x in range(lx0, lx1 + 1):
        p.set(x, TOP, lz0, WALL)
    for x, y, z in CONSOLES:
        p.set(x, y, z, CONSOLE)
        p.set(x, y - 1, z, TRIM)
    for x in TURRETS_X:
        p.set(x, TOP - 1, TURRET_Z, "Rock_Gold_Brick_Smooth")
    # Couloir et salle de Vieux Tom.
    for z in range(-104, -100):
        for x in range(-4, 5):
            p.set(x, TOP - 1, z, pick(LAB, x, TOP, z) if abs(x) < 4 else WALL)
            if abs(x) == 4:
                for y in range(TOP, TOP + 5):
                    p.set(x, y, z, WALL)
            else:
                p.set(x, TOP + 4, z, WALL)
    for (x, y, z) in GATE_TOP:
        p.set(x, y, z, MIST)
    rx0, rx1, rz0, rz1 = ROOM
    fc.box_floor(p, rx0, rx1, rz0, rz1, TOP, lambda x, z: pick(LAB, x, TOP, z))
    openings = {(x, z) for x in range(-3, 4) for z in (rz0 - 1, rz1 + 1)}
    fc.walls(p, rx0 - 1, rx1 + 1, rz0 - 1, rz1 + 1, TOP - 1, TOP + 8,
             lambda x, y, z: PINK if y == TOP + 5 and (x + z) % 6 == 0 else pick(LAB, x, y, z), openings)
    for x in range(-3, 4):
        for z in (rz0 - 1, rz1 + 1):
            p.set(x, TOP - 1, z, pick(LAB, x, TOP, z))
            p.set(x, TOP + 4, z, "Rock_Stone_Brick")
            for y in range(TOP + 5, TOP + 9):
                p.set(x, y, z, pick(LAB, x, y, z))
    for (x, y, z) in GATE_TOM:
        p.set(x, y, z, MIST)
    for x in (-1, 0, 1):
        for y in (TOP + 5, TOP + 6, TOP + 7):
            p.set(x, y, rz0 - 1, FAN_BLOCK)
    p.set(*FAN, CONSOLE)
    for b in BATTERIES:
        p.set(*b, BATTERY)
    for x, z in ((-12, -110), (12, -110), (-12, -130), (12, -130), (-6, -120), (6, -120)):
        p.set(x, TOP, z, "Rock_Stone_Brick")
        p.set(x, TOP + 1, z, "Deco_Lantern")
    # Couloir vers les plates-formes de lueur.
    for z in range(-139, -136):
        for x in range(-3, 4):
            p.set(x, TOP - 1, z, pick(LAB, x, TOP, z))
    px0, px1, pz0, pz1 = PAD2
    fc.box_floor(p, px0, px1, pz0, pz1, TOP, LANDING, TRIM)
    for x, z, stand in path2():
        for dx in (0, 1):
            for dz in (0, 1):
                p.set(x + dx, stand - 1, z + dz, GLIMMER)
    # Arène de l'Asura.
    cx, cz = ARENA_CENTER
    fc.disc(p, cx, cz, ARENA_RADIUS, ARENA,
            lambda x, z: PINK if abs(math.hypot(x - cx, z - cz) - 12) < 0.5 else pick(MARBLE, x, ARENA, z), UNDER, 9)
    ax, ay, az = ASURA_AT
    for x in range(int(ax) - 2, int(ax) + 3):
        for z in range(int(az) - 2, int(az) + 3):
            p.set(x, ARENA, z, TRIM)
            p.set(x, ARENA + 1, z, pick(MARBLE, x, ARENA + 1, z))
    for x, z, _ in PYLONS:
        p.set(x, ARENA, z, PYLON)
        p.set(x, ARENA + 1, z, PYLON)
    for a in range(0, 360, 30):
        x = round(cx + math.cos(math.radians(a)) * (ARENA_RADIUS - 1))
        z = round(cz + math.sin(math.radians(a)) * (ARENA_RADIUS - 1))
        if z > cz + 12 and abs(x) < 6:
            continue   # entrée sud
        p.set(x, ARENA, z, "Rock_Marble_Brick_Pillar_Middle")
        p.set(x, ARENA + 1, z, "Furniture_Temple_Light_Lantern")
    dress(p)
    return p


# Décor : ruines de marbre au milieu de jardins suspendus des Brumes (glycines, bouleaux, prairies fleuries).
THEME = fn._theme(trees=["wisteria", "birch", "oak", "wisteria", "maple"],
                  deep=["Rock_Marble", "Rock_Stone", "Rock_Marble", "Rock_Marble_Cobble"])


def dress(p):
    """Pourtours herbus autour des lieux du parcours, dessous rocheux et lianes sous les plates-formes, lianes sous
    l'escalier, îlots de décor tout autour. Jamais de sol en plus entre deux sauts (les pourtours s'arrêtent avant
    les plates-formes des harpies et de lueur)."""
    def floor(cells):
        return {(x, z): y for (x, y, z) in cells}

    def top_cells(y, x0, x1, z0, z1, inside=lambda x, z: True):
        return [(x, y, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)
                if inside(x, z) and (x, y, z) in p.blocks]

    # Départ : prairie autour du disque, pas vers le nord (premières plates-formes).
    sx, sz, r = START
    start = floor(top_cells(-1, sx - r, sx + r, sz - r, sz + r))
    tops = fn.rim(start, 4, 11, seed=3, block=lambda x, z: z < sz - 4)
    fn.natural_ground(p, tops, THEME, seed=3, keep=[(sx - 2, sx + 2, sz, sz + 8)], trees=0.05)
    # Plates-formes des harpies : un bloc de roche dessous, des lianes qui pendent.
    for k, (x, z) in enumerate(PATH1):
        stand = k + 1
        plat = {(x + dx, z + dz): stand - 1 for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        fn.island(p, plat, lambda xx, zz: 4 + 2 * fn.hash01(xx, zz, k, 5), seed=k, hang=0.35, theme=THEME)
    # Cour de la prison : jardins à l'est, à l'ouest et au nord (hors de l'escalier), pas au sud (arrivée des sauts).
    x0, x1, z0, z1 = PLAZA
    yard = floor(top_cells(YARD - 1, x0 - 7, x1 + 7, z0, z1))
    tops = fn.rim(yard, 3, 10, seed=7, block=lambda x, z: z > z1 - 1 or (abs(x) <= 6 and z < z0))
    fn.natural_ground(p, tops, THEME, seed=7, trees=0.04)
    # Escalier : lianes sous ses bords.
    sx0, sx1, zb, zt = STAIRS
    for z in range(zt, zb + 1):
        y = math.floor(stair_level(z)) - 5
        for x in (sx0, sx1):
            if fn.hash01(x, y, z, 9) < 0.3:
                for k in range(1 + int(fn.hash01(z, x, y, 10) * 4)):
                    if fn.free(p, x, y - k, z):
                        p.set(x, y - k, z, fn.HANGING[k % 2])
    # Palier des consoles et salle de Vieux Tom : une île sous le tout, jardin hors des murs (pas vers les sauts).
    rx0, rx1, rz0, rz1 = ROOM
    lab = floor(top_cells(TOP - 1, rx0 - 1, rx1 + 1, rz0 - 1, LANDING_TOP[3]))
    inland = fn.edge_distance(lab)
    fn.island(p, lab, lambda x, z: 4 + min(14, inland[(x, z)] * 0.9), seed=11, hang=0.15, theme=THEME)
    tops = fn.rim(lab, 3, 9, seed=11, block=lambda x, z: z < rz0 - 2 or z > LANDING_TOP[3] - 2)
    fn.natural_ground(p, tops, THEME, seed=11, trees=0.05)
    # Arène de l'Asura : jardin autour, sauf au sud (arrivée des plates-formes de lueur).
    cx, cz = ARENA_CENTER
    arena = floor(top_cells(ARENA - 1, cx - ARENA_RADIUS, cx + ARENA_RADIUS, cz - ARENA_RADIUS, cz + ARENA_RADIUS))
    tops = fn.rim(arena, 3, 9, seed=13, block=lambda x, z: z > cz + 8)
    fn.natural_ground(p, tops, THEME, seed=13, trees=0.05)
    # Îlots des Brumes tout autour, loin du parcours.
    fn.scatter_islets(p, (-95, 95, -270, 90), 26, (-30, ARENA + 12), (3, 10), THEME, seed=17)


# --- blocs, objets, effets, particules ------------------------------------------------------------------

def blocks():
    """(id, texture, fond, couleur, glyphe, lumière, action, plein, alpha, opacité)."""
    use = lambda action: f"Nakasar_Fractal_Use_{action}"
    return [
        (CONSOLE, "Console", (70, 74, 96), (120, 230, 255), "console", "#6cf", use("Uncategorized_Console"), True, 255, None),
        (FAN_BLOCK, "Fan", (60, 62, 72), (210, 220, 230), "fan", None, None, True, 255, None),
        (BATTERY, "Battery", (52, 56, 70), (120, 180, 255), "battery", None, use("Uncategorized_Battery"), True, 255, None),
        (BATTERY_ON, "Battery_Charged", (52, 56, 70), (140, 240, 255), "battery_on", "#6ef", use("Uncategorized_Battery"),
         True, 255, None),
        (GLIMMER, "Glimmer", (255, 226, 120), (255, 248, 200), "glimmer", "#fe8", None, True, 150, "Semitransparent"),
        (PYLON, "Charge_Pylon", (60, 50, 90), (200, 160, 255), "pylon", "#c9f", None, True, 255, None),
    ]


def tear_parts():
    blue, light, dark = (120, 200, 255), (230, 250, 255), (50, 90, 170)
    return [("Drop", (0, 4, 0), (4, 6, 4), 45, fm.crystal(dark, light), "fullbright"),
            ("Tip", (0, 8, 0), (2, 3, 2), 45, fm.crystal(blue, light), "fullbright")]


def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Charge_Positive": fc.effect(
            L, "Nakasar_Fractal_Charge_Positive", "Charge + (Asura fou) : à moins de 3 blocs d'une charge -, les deux "
            "s'électrocutent (Java, combat.Polarity).", "Charge_Positive", 1.5, ApplicationEffects={"EntityTopTint": "#ffd040"}),
        "Nakasar_Fractal_Charge_Negative": fc.effect(
            L, "Nakasar_Fractal_Charge_Negative", "Charge - (Asura fou) : à moins de 3 blocs d'une charge +, les deux "
            "s'électrocutent.", "Charge_Negative", 1.5, ApplicationEffects={"EntityTopTint": "#40a0ff"}),
        "Nakasar_Fractal_Harried": fc.effect(
            L, "Nakasar_Fractal_Harried", "Harcelé par les harpies (à moins de 14 blocs de l'une d'elles) : un peu plus "
            "lent.", "Harried", 1.5, debuff=True, ApplicationEffects={"HorizontalSpeedMultiplier": 0.8}),
    }


def gas_cause():
    return fc.cause("Gaz de la salle de Vieux Tom (une part des PV max par seconde, l'armure ne le réduit pas).", "#9aff6a")


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Lightning_Arc": ("Arc électrique (charges opposées, rebond de l'éclair de Vieux Tom, tourelles).",
                                      [("Arc", S("#ffffff", "#60c0ff", 14, (1.0, 3.0), (-60, 60), 0.6, 0.6,
                                                 life=(0.15, 0.35), size=(0.15, 0.3)), 0.0)]),
    "Nakasar_Fractal_Charge_Plus": ("Pylône chargé + : étincelles dorées.",
                                    [("Spark", S("#fff0a0", "#ffb020", 8, (0.4, 1.0), (40, 90), 0.4, 0.6), 0.0)]),
    "Nakasar_Fractal_Charge_Minus": ("Pylône chargé - : étincelles bleues.",
                                     [("Spark", S("#c0e8ff", "#2060ff", 8, (0.4, 1.0), (40, 90), 0.4, 0.6), 0.0)]),
    "Nakasar_Fractal_Gas": ("Gaz de la salle de Vieux Tom : nappe verte qui monte.",
                            [("Fog", S("#b0ff80", "#2a5a10", 18, (0.1, 0.4), (60, 90), 6.0, 1.5, life=(1.5, 2.2),
                                       size=(1.0, 1.6), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Gas_Warning": ("Le gaz va monter : bulles vertes aux bouches d'aération.",
                                    [("Bubbles", S("#d0ffb0", "#5a9a30", 10, (0.5, 1.2), (70, 90), 1.0, 0.3,
                                                   life=(0.6, 1.0)), 0.1)]),
    "Nakasar_Fractal_Fan_Gust": ("Ventilateur : souffle blanc qui aspire le gaz.",
                                 [("Wind", S("#ffffff", "#c8d8ff", 24, (4.0, 7.0), (70, 90), 4.0, 1.0,
                                             life=(0.6, 1.0)), 0.3)]),
    "Nakasar_Fractal_Battery_Charge": ("Batterie rechargée : éclair bleu.",
                                       [("Bolt", S("#e0f8ff", "#40b0ff", 16, (1.0, 2.5), (40, 90), 0.4, 1.2), 0.3)]),
    "Nakasar_Fractal_Tear_Glint": ("Larme de Brume tombée : scintillement bleu.",
                                   [("Glint", S("#ffffff", "#80c8ff", 6, (0.2, 0.5), (60, 90), 0.3, 0.6), 0.2)]),
    "Nakasar_Fractal_Asura_Orb": ("Orbe de l'Asura fou : boule violette qui suit sa cible.",
                                  [("Core", S("#ffffff", "#c040ff", 10, (0.1, 0.3), (-90, 90), 0.25, 0.3,
                                              life=(0.25, 0.35), size=(0.35, 0.55)), 0.0)]),
    "Nakasar_Fractal_Asura_Bolt": ("Salve de l'Asura : étincelles violettes au point d'impact.",
                                   [("Burst", S("#f0c0ff", "#7a20ff", 18, (2.0, 4.0), (0, 90), 0.6, 0.4,
                                                life=(0.3, 0.6)), 0.2)]),
    "Nakasar_Fractal_Golem_Wake": ("Un golem de cristal s'éveille : éclats roses.",
                                   [("Shards", S("#ffffff", "#ff70c0", 22, (2.0, 4.0), (-20, 90), 1.0, 2.5,
                                                 life=(0.5, 0.9)), 0.5)]),
    "Nakasar_Fractal_Generator_Pulse": ("Générateur de la prison : pulsation bleue.",
                                        [("Pulse", S("#e0f8ff", "#3080ff", 12, (0.6, 1.4), (-10, 60), 0.8, 1.4), 0.4)]),
}


# --- modèles ----------------------------------------------------------------------------------------------

def turret_parts():
    steel, glow = (88, 92, 110), (140, 220, 255)
    return [("Base", (0, 10, 0), (40, 20, 40), 0, fm.smooth(steel), "flat"),
            ("Head", (0, 34, 0), (30, 22, 30), 0, fm.smooth(fm.shade(steel, 1.2)), "flat"),
            ("Barrel", (0, 36, 22), (10, 10, 24), 0, fm.smooth(fm.shade(steel, 0.7)), "flat"),
            ("Eye", (0, 38, 15.5), (12, 6, 1), 0, fm.crystal((40, 120, 200), glow), "fullbright")]


def generator_parts():
    metal, glow = (72, 76, 96), (150, 220, 255)
    parts = [("Base", (0, 8, 0), (64, 16, 64), 0, fm.smooth(metal), "flat"),
             ("Core", (0, 60, 0), (30, 80, 30), 0, fm.crystal((50, 110, 220), glow), "fullbright"),
             ("Cap", (0, 106, 0), (50, 12, 50), 0, fm.smooth(metal), "flat")]
    for k in range(4):
        a = math.radians(90 * k + 45)
        parts.append((f"Coil_{k}", (math.cos(a) * 26, 56, math.sin(a) * 26), (10, 80, 10), 0,
                      fm.smooth(fm.shade(metal, 1.3)), "flat"))
    return parts


def rabbit_parts():
    fur, belly, eye = (200, 190, 180), (236, 230, 222), (255, 60, 60)
    return [("Body", (0, 26, 0), (34, 30, 48), 0, fm.smooth(fur), "flat"),
            ("Belly", (0, 22, 10), (26, 20, 30), 0, fm.smooth(belly), "flat"),
            ("Head", (0, 50, 22), (26, 24, 24), 0, fm.smooth(fur), "flat"),
            ("Ear_L", (-7, 74, 18), (6, 26, 4), 0, fm.smooth(fur), "flat"),
            ("Ear_R", (7, 74, 18), (6, 26, 4), 0, fm.smooth(fur), "flat"),
            ("Eye_L", (-8, 54, 34.5), (5, 5, 1), 0, fm.crystal((140, 0, 0), eye), "fullbright"),
            ("Eye_R", (8, 54, 34.5), (5, 5, 1), 0, fm.crystal((140, 0, 0), eye), "fullbright"),
            ("Teeth", (0, 42, 34.5), (8, 6, 1), 0, fm.flat((250, 250, 240)), "flat"),
            ("Foot_L", (-12, 6, 6), (10, 12, 26), 0, fm.smooth(fur), "flat"),
            ("Foot_R", (12, 6, 6), (10, 12, 26), 0, fm.smooth(fur), "flat"),
            ("Tail", (0, 30, -26), (12, 12, 8), 0, fm.smooth(belly), "flat")]


def models():
    m = {}
    m[HARPY] = {"$Comment": "Harpie (provisoire) : la chauve-souris vanilla, deux fois plus grande. Modèle de harpie à "
                            "vérifier dans Assets.zip.", "Parent": "Bat", "MinScale": 2.0, "MaxScale": 2.0}
    m[GENERATOR_ROLE] = fc.character_model("Prison_Generator", generator_parts(), 21,
                                           "Générateur de la prison (PNJ fixe) : socle d'acier, cœur de cristal bleu. "
                                           "Généré par tools/generate_uncategorized.py.", 1.2, (0.9, 1.8),
                                           light={"Color": "#6cf", "Radius": 4})
    m[TURRET] = fc.character_model("Turret", turret_parts(), 22, "Tourelle de l'escalier mortel (PNJ fixe, invulnérable).",
                                   0.6, (0.4, 0.8), light={"Color": "#6cf", "Radius": 2})
    m[RABBIT] = fc.character_model("Rabid_Rabbit", rabbit_parts(), 23, "Lapin enragé (prisonnier) : gros lapin gris aux "
                                   "yeux rouges, modèle en boîtes sans animation (provisoire).", 0.8, (0.5, 1.2), scale=1.3)
    m[SABOTEUR] = fr.humanoid(
        "Saboteur (prisonnier) : bandit masqué, manteau sombre, bombes.", "08", "Face_Scar", [
            ("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
            ("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png", "Faded_Leather", "Black"),
            ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Black")])
    m[SHAMAN] = fr.humanoid(
        "Chaman du feu (prisonnier) : robe de mage rouge, mains qui brûlent.", "19", "Face_Sunken", [
            ("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            ("Cosmetics/Shoes/AngledBoots.blockymodel", "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots_Green.png")],
        light={"Color": "#f84", "Radius": 2})
    m[ETTIN] = {"$Comment": "Ettin (prisonnier, provisoire) : la grande aberration vanilla × 1,15 en attendant un modèle à "
                            "deux têtes.", "Parent": "Zombie_Aberrant_Big", "MinScale": 1.15, "MaxScale": 1.15}
    m[TOM] = {"$Comment": "Vieux Tom (boss de l'Inclassable) : le golem de forge vanilla, × 1,5.", "Parent": "Golem_Firesteel",
              "MinScale": 1.5, "MaxScale": 1.5, "Light": {"Color": "#f96", "Radius": 4}}
    m[ASURA] = fr.humanoid(
        "L'Asura fou : tout petit (× 0,65), couronne de travers, manteau d'érudit, yeux rouges. Invulnérable.", "02",
        "Almond_Eyes_Face", [
            ("Cosmetics/Head/KingsCrown.blockymodel", "Cosmetics/Head/KingsCrown_Red.png"),
            ("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png", "Faded_Leather", "Brown"),
            ("Cosmetics/Shoes/AngledBoots.blockymodel", "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots_Green.png")],
        scale=(0.65, 0.65), light={"Color": "#c6f", "Radius": 3})
    m[CRYSTAL_GOLEM] = {"$Comment": "Golem de cristal de l'Asura : le golem de cristal vanilla.", "Parent": "Golem_Crystal_Thunder",
                        "Light": {"Color": "#f6c", "Radius": 3}}
    return m


# --- attaques -----------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
TOM_ANIMS = "Golem_Firesteel_Default"
GOLEM_ANIMS = "Golem_Crystal_Thunder_Default"


def interactions():
    out = {}
    T = fr.telegraph
    out["Nakasar_Fractal_Harpy_Peck"] = {
        "$Comment": "Harpie au contact : serres (8 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Serres.", None, None, 0.3, 8, end=2.4, length=80, yaw=40,
                                                     sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Harpy_Dive"] = {
        "$Comment": "Harpie : piqué sur sa cible, cercle rouge de 1,8 bloc (1,3 s), 12 dégâts ; dès le niveau 10, "
                    "projection (sauf dos au vide : comme dans GW2, on n'est pas poussé hors d'une plate-forme sans sol "
                    "derrière soi).",
        "Type": "Serial", "Interactions": [
            CI, RF,
            T("Circle", 1.3, Anchor="Target", Radius=1.8, Damage=12, Knockback=10, KnockUp=4, KnockbackMinLevel=10,
              KnockbackNeedsGround=True, PlayersOnly=True, ImpactSound="SFX_Unarmed_Swing"),
            fc.windup(1.3, "SFX_Spirit_Root_Alerted")]}
    out["Nakasar_Fractal_Rabbit_Bite"] = {
        "$Comment": "Lapin enragé : morsure (11 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.3, 11, end=2.2, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Rabbit_Leap"] = {
        "$Comment": "Lapin enragé : bond sur sa cible, cercle rouge de 2,5 blocs (1,2 s), 22 dégâts.",
        "Type": "Serial", "Interactions": [
            CI, RF, T("Circle", 1.2, Anchor="Target", Radius=2.5, Damage=22, TeleportCaster=True, Knockback=5, KnockUp=3,
                      PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large", ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            fc.windup(1.2)]}
    out["Nakasar_Fractal_Saboteur_Stab"] = {
        "$Comment": "Saboteur au contact : coup de lame (8 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de lame.", "Mace", "SwingLeft", 0.3, 8)]}
    out["Nakasar_Fractal_Saboteur_Bombs"] = {
        "$Comment": "Saboteur : trois bombes autour de sa cible, cercles rouges de 2,2 blocs (1,6 s), 18 dégâts et "
                    "projection.",
        "Type": "Serial", "Interactions": [
            T("Circle", 1.6, Anchor="Target", Radius=2.2, Damage=18, Knockback=6, KnockUp=4, PlayersOnly=True,
              ImpactParticle="Nakasar_Fractal_Bomb_Blast", ImpactSound="SFX_Goblin_Lobber_Bomb_Death"),
            T("Circle", 1.6, Anchor="Target", OffsetMin=2.5, OffsetMax=4.5, Radius=2.2, Damage=18, Knockback=6, KnockUp=4,
              PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Bomb_Blast"),
            T("Circle", 1.6, Anchor="Target", OffsetMin=2.5, OffsetMax=4.5, Radius=2.2, Damage=18, Knockback=6, KnockUp=4,
              PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Bomb_Blast"),
            fc.windup(1.0, "SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Fire_Shaman_Staff"] = {
        "$Comment": "Chaman du feu au contact : coup de bâton (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bâton.", "Staff", "SwingLeft", 0.4, 6)]}
    out["Nakasar_Fractal_Fire_Shaman_Flames"] = {
        "$Comment": "Chaman du feu : flammes sous chaque joueur, cercles rouges de 2 blocs (1,6 s), 12 dégâts et brûlure.",
        "Type": "Serial", "Interactions": [
            T("Circle", 1.6, Anchor="EachPlayer", Radius=2.0, Damage=12, EffectId="Burn", EffectDuration=3,
              PlayersOnly=True, ImpactParticle="Fire_Blue"),
            {"Type": "Simple", "RunTime": 1.6, "Effects": {"ItemPlayerAnimationsId": "Staff", "ItemAnimationId": "SwingRight",
                                                           "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Ettin_Club"] = {
        "$Comment": "Ettin : coup de poing (16 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de poing.", None, None, 0.45, 16, end=3.2, knockback=4)]}
    out["Nakasar_Fractal_Ettin_Smash"] = {
        "$Comment": "Ettin : écrasement en cône de 120° et 5 blocs (1,6 s), 35 dégâts et projection.",
        "Type": "Serial", "Interactions": [
            CI, RF, T("Cone", 1.6, Angle=120, Radius=5, Damage=35, Knockback=8, KnockUp=5,
                      ImpactParticle="Stick_Slam_Ground_Large", ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            fc.windup(1.6, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Tom_Swings"] = {
        "$Comment": "Vieux Tom : deux revers de ses poings de forge (20 dégâts chacun), sans annonce.",
        "Type": "Serial", "Interactions": [
            fr.swing("Revers gauche.", TOM_ANIMS, "SwingLeft", 0.5, 20, end=4.0),
            fr.swing("Revers droit.", TOM_ANIMS, "SwingRight", 0.5, 20, end=4.0, direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Tom_Burst"] = {
        "$Comment": "Vieux Tom : rafale, huit cercles rouges de 1,8 bloc semés autour de lui (3 à 12 blocs, 1,6 s), 22 "
                    "dégâts chacun.",
        "Type": "Serial", "Interactions": [
            CI, RF, T("Circle", 1.6, Anchor="Scatter", Count=8, OffsetMin=3, OffsetMax=12, Radius=1.8, Damage=22,
                      PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Bomb_Blast", ImpactSound="SFX_Goblin_Lobber_Bomb_Death"),
            fc.windup(1.6, "SFX_Spear_Throw_Charge", TOM_ANIMS, "GroundSlam")]}
    out["Nakasar_Fractal_Tom_Pull"] = {
        "$Comment": "Vieux Tom : marque sa cible (1,4 s, 10 dégâts), puis l'attire contre lui et frappe le sol (cercle de "
                    "3 blocs, 1,2 s, 24 dégâts) : s'éloigner vite après l'attraction.",
        "Type": "Serial", "Interactions": [
            CI, RF,
            T("Mark", 1.4, Damage=10, MarkParticle="Nakasar_Fractal_Lightning_Arc", MarkParticleScale=1.2,
              HitParticle="Nakasar_Fractal_Lightning_Arc"),
            fc.windup(1.4, "SFX_Spirit_Root_Alerted"),
            {"Type": "Nakasar_Fractal_Pull", "Range": 22, "StopDistance": 2.5, "Up": 4, "Particle": "Nakasar_Fractal_Lightning_Arc"},
            T("Circle", 1.2, Radius=3, Damage=24, Knockback=6, KnockUp=4, ImpactParticle="Stick_Slam_Ground_Large",
              ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            fc.windup(1.2, "SFX_Spear_Throw_Charge", TOM_ANIMS, "GroundSlam")]}
    out["Nakasar_Fractal_Tom_Lightning"] = {
        "$Comment": "Vieux Tom : éclair sur sa cible, cercle rouge de 2 blocs (1,4 s), 18 dégâts et étourdissement 0,8 s ; "
                    "il rebondit trois fois sur le joueur le plus proche (10 blocs) : écartez-vous les uns des autres.",
        "Type": "Serial", "Interactions": [
            T("Circle", 1.4, Anchor="Target", Radius=2.0, Damage=18, EffectId="Hazard_Electric_Stun", EffectDuration=0.8,
              Bounces=3, BounceRange=10, PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Lightning_Arc"),
            fc.windup(1.4, "SFX_Spirit_Root_Alerted")]}
    out["Nakasar_Fractal_Crystal_Golem_Slam"] = {
        "$Comment": "Golem de cristal : frappe le sol, cercle rouge de 4 blocs autour de lui (1,4 s), 25 dégâts et "
                    "projection.",
        "Type": "Serial", "Interactions": [
            CI, RF, T("Circle", 1.4, Radius=4, Damage=25, Knockback=7, KnockUp=4, ImpactParticle="Stick_Slam_Ground_Large",
                      ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            fc.windup(1.4, "SFX_Spear_Throw_Charge", GOLEM_ANIMS, "GroundSlam")]}
    out["Nakasar_Fractal_Crystal_Golem_Strike"] = {
        "$Comment": "Golem de cristal au contact : coup de cristal (14 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de cristal.", GOLEM_ANIMS, "GroundSlam", 0.6, 14, end=3.2)]}
    for action, comment in (("Uncategorized_Console", "Console de l'Inclassable (escalier mortel, ventilateur)."),
                            ("Uncategorized_Battery", "Batterie de la salle de Vieux Tom : y verser une larme de Brume.")):
        out[f"Nakasar_Fractal_Use_{action}"] = fc.use_interaction(action, comment)
    return out


MELEE = ["Harpy_Peck", "Harpy_Dive", "Rabbit_Bite", "Rabbit_Leap", "Saboteur_Stab", "Fire_Shaman_Staff", "Ettin_Club",
         "Ettin_Smash", "Tom_Swings", "Tom_Burst", "Tom_Pull", "Crystal_Golem_Slam", "Crystal_Golem_Strike"]
RANGED = ["Saboteur_Bombs", "Fire_Shaman_Flames", "Tom_Lightning"]
R = fc.root


# --- rôles ----------------------------------------------------------------------------------------------

def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[HARPY] = fr.role(
        HARPY, "Harpie des plates-formes : tourne au-dessus du groupe, pique sur un joueur (cercle rouge, projection dès "
        "le niveau 10). Posée par le Java, jamais sauvegardée.", HARPY, n(HARPY), 70,
        [fr.timed_attack("Dive", R("Harpy_Dive"), rng=14, los=True, comment="Piqué annoncé."),
         fr.melee(R("Harpy_Peck"), 2.4, (0.9, 1.4)), fr.chase(30, stop=1.6, pathfinder=False)],
        fc.fly(6, 1, 6), GENERATOR, sight=18, leash=30, home=True,
        timers=[fr.timer("Dive", (2, 4), (6, 8))], KnockbackScale=0.6, DeathAnimationTime=0.8)
    gen = fc.static_role(LANG, GENERATOR_ROLE, "Générateur de la prison : tant qu'il tient, les cellules restent closes. "
                         "Barre de boss.", GENERATOR, 600)
    out[GENERATOR_ROLE] = gen
    out[RABBIT] = fr.role(
        RABBIT, "Lapin enragé (premier prisonnier) : bond annoncé sur sa cible, morsures.", RABBIT, n(RABBIT), 380,
        [fr.timed_attack("Leap", R("Rabbit_Leap"), rng=14, los=True, comment="Bond annoncé."),
         fr.melee(R("Rabbit_Bite"), 2.2, (0.6, 1.0)), fr.chase(40, speed=1.0, stop=1.5)],
        fr.walk(5.5, jump=1.5), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Leap", (2, 3), (7, 9))], KnockbackScale=0.6, DeathAnimationTime=1.0)
    out[SABOTEUR] = fr.role(
        SABOTEUR, "Saboteur (deuxième prisonnier) : garde ses distances et sème trois bombes autour de sa cible.",
        SABOTEUR, n(SABOTEUR), 300,
        [fr.cast("Bombs", R("Saboteur_Bombs"), 18, "Trois bombes annoncées."),
         fr.melee(R("Saboteur_Stab"), 2.2, (0.7, 1.1)), fr.keep_distance(40, 5, 9)],
        fr.walk(4.2), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Bombs", (1, 2), (5, 7))], HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.9,
        DeathAnimationTime=1.0)
    out[SHAMAN] = fr.role(
        SHAMAN, "Chaman du feu (troisième prisonnier) : flammes annoncées sous chaque joueur.", SHAMAN, n(SHAMAN), 320,
        [fr.timed_attack("Flames", R("Fire_Shaman_Flames"), comment="Flammes sous chaque joueur."),
         fr.melee(R("Fire_Shaman_Staff"), 2.0, (0.9, 1.3)), fr.keep_distance(40, 6, 10)],
        fr.walk(3.8), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Flames", (2, 3), (6, 8))], HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=0.9,
        DeathAnimationTime=1.0)
    out[ETTIN] = fr.role(
        ETTIN, "Ettin (dernier prisonnier) : coups de poing, écrasement en cône annoncé.", ETTIN, n(ETTIN), 700,
        [fr.timed_attack("Smash", R("Ettin_Smash"), rng=4.5, los=True, comment="Écrasement annoncé."),
         fr.melee(R("Ettin_Club"), 3.0, (1.0, 1.4)), fr.chase(40, stop=2.2)],
        fr.walk(3.4), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Smash", (3, 5), (8, 11))], KnockbackScale=0.2, DeathAnimationTime=1.5)
    turret = fc.static_role(LANG, TURRET, "Tourelle de l'escalier mortel : immobile, invulnérable ; le Java tire ses "
                            "lignes.", GENERATOR, 1000)
    out[TURRET] = turret
    out[TOM] = fr.role(
        TOM, "Vieux Tom (boss de l'Inclassable), barre de boss : revers sans annonce, rafale de cercles, marque puis "
        "attraction et frappe au sol, éclair qui rebondit. Le gaz, le ventilateur et les batteries sont menés par le "
        "Java (uncategorized.OldTom).", TOM, n(TOM), 3200,
        [fr.timed_attack("Burst", R("Tom_Burst"), comment="Rafale de cercles autour de lui."),
         fr.timed_attack("Pull", R("Tom_Pull"), rng=20, los=True, comment="Marque, attraction, frappe au sol."),
         fr.timed_attack("Lightning", R("Tom_Lightning"), rng=22, los=True, comment="Éclair qui rebondit."),
         fr.melee(R("Tom_Swings"), 3.6, (0.9, 1.3)), fr.chase(30, stop=2.6)],
        fr.walk(3.2), GENERATOR, sight=20, leash=26, home=True,
        timers=[fr.timer("Burst", (5, 7), (13, 16)), fr.timer("Pull", (8, 10), (16, 20)), fr.timer("Lightning", (3, 5), (9, 12))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    asura = fc.static_role(LANG, ASURA, "L'Asura fou : immobile sur son estrade, invulnérable ; ses salves et ses orbes "
                           "sont lancées par le Java (uncategorized.MadAsura).", GENERATOR, 1000)
    out[ASURA] = asura
    out[CRYSTAL_GOLEM] = fr.role(
        CRYSTAL_GOLEM, "Golem de cristal de l'Asura : figé jusqu'à son réveil (Java), puis frappe le sol (cercle "
        "annoncé) et au contact.", CRYSTAL_GOLEM, n(CRYSTAL_GOLEM), 900,
        [fr.timed_attack("Slam", R("Crystal_Golem_Slam"), rng=5, los=True, comment="Frappe au sol annoncée."),
         fr.melee(R("Crystal_Golem_Strike"), 3.2, (1.0, 1.4)), fr.chase(40, stop=2.4)],
        fr.walk(3.4), GENERATOR, sight=40, leash=40, home=False,
        timers=[fr.timer("Slam", (3, 5), (8, 10))], KnockbackScale=0.1, DeathAnimationTime=1.5)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(CONSOLE, "Console", "Utiliser : l'activer. Certaines doivent l'être ensemble.", "Console",
           "Use: activate it. Some must be activated together.")
    t.item(FAN_BLOCK, "Ventilateur", "Aspire le gaz de la salle quand on l'allume.", "Fan", "Pulls the gas out of the room when switched on.")
    t.item(BATTERY, "Batterie vide", "Utiliser avec une larme de Brume : la recharger.", "Empty battery",
           "Use with a Mist tear: recharge it.")
    t.item(BATTERY_ON, "Batterie chargée", "Prête à alimenter le ventilateur.", "Charged battery", "Ready to power the fan.")
    t.item(GLIMMER, "Lueur", "Plate-forme de lumière solide.", "Glimmer", "A platform of solid light.")
    t.item(PYLON, "Pylône de charge", "Seul face à l'Asura, il porte la charge opposée.", "Charge pylon",
           "When alone against the Asura, it carries the opposite charge.")
    t.item(TEAR, "Larme de Brume", "Recharge une batterie de la salle de Vieux Tom. Se dissipe hors de l'Inclassable.",
           "Mist tear", "Recharges a battery in Old Tom's room. Fades outside the Uncategorized fractal.")
    for role, f, e in ((HARPY, "Harpie", "Harpy"), (GENERATOR_ROLE, "Générateur de la prison", "Prison generator"),
                       (RABBIT, "Lapin enragé", "Rabid rabbit"), (SABOTEUR, "Saboteur", "Saboteur"),
                       (SHAMAN, "Chaman du feu", "Fire shaman"), (ETTIN, "Ettin", "Ettin"), (TURRET, "Tourelle", "Turret"),
                       (TOM, "Vieux Tom", "Old Tom"), (ASURA, "L'Asura fou", "The Mad Asura"),
                       (CRYSTAL_GOLEM, "Golem de cristal", "Crystal golem")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Charge_Positive", "Charge +", "Charge +")
    t.put("effects.Nakasar_Fractal_Charge_Negative", "Charge -", "Charge -")
    t.put("effects.Nakasar_Fractal_Harried", "Harcelé", "Harried")
    msgs = {
        "intro": ("Inclassable : des plates-formes sous les harpies, une prison, un escalier mortel et un Asura qui a perdu "
                  "la tête. Une chute ramène au départ.",
                  "Uncategorized: platforms under the harpies, a prison, a deadly staircase and an Asura who lost his mind. "
                  "A fall brings you back to the start."),
        "landing.back": ("Rattrapé par les Brumes : retour au départ.", "Caught by the Mists: back to the start."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "yard.enter": ("La cour de la prison : détruisez le générateur.", "The prison yard: destroy the generator."),
        "yard.release": ("Une cellule s'ouvre : {name} est libre !", "A cell opens: {name} is free!"),
        "yard.done": ("Les prisonniers sont vaincus : la barrière se dissipe.", "The prisoners are defeated: the barrier fades."),
        "stairs.enter": ("L'escalier mortel : les tourelles balaient les marches. En haut, activez les trois consoles "
                         "ensemble ({seconds} s).",
                         "The deadly staircase: the turrets sweep the steps. At the top, activate the three consoles "
                         "together ({seconds} s)."),
        "console.lit": ("Console activée ({count}/{total}).", "Console activated ({count}/{total})."),
        "console.late": ("Trop lent : les consoles s'éteignent.", "Too slow: the consoles go dark."),
        "console.done": ("Les tourelles s'éteignent, la barrière se dissipe.", "The turrets shut down, the barrier fades."),
        "tom.enter": ("Vieux Tom ! Le gaz monte régulièrement : allumez le ventilateur au fond de la salle.",
                      "Old Tom! The gas rises regularly: switch on the fan at the back of the room."),
        "tom.batteries": ("Dès ce niveau, le ventilateur a besoin de ses deux batteries : versez-y les larmes de Brume.",
                          "At this level, the fan needs both batteries: pour the Mist tears into them."),
        "gas.warning": ("Le gaz va monter !", "The gas is about to rise!"),
        "gas.rising": ("Le gaz monte : allumez le ventilateur !", "The gas is rising: switch on the fan!"),
        "gas.vented": ("Le ventilateur aspire le gaz.", "The fan pulls the gas out."),
        "gas.calm": ("Pas de gaz à évacuer pour l'instant.", "No gas to vent for now."),
        "fan.batteries": ("Le ventilateur n'a pas de courant : rechargez les deux batteries.",
                          "The fan has no power: recharge both batteries."),
        "battery.charged": ("Batterie chargée ({count}/2).", "Battery charged ({count}/2)."),
        "battery.full": ("Cette batterie est déjà chargée.", "This battery is already charged."),
        "battery.needTear": ("Il faut une larme de Brume.", "You need a Mist tear."),
        "tear.drop": ("Des larmes de Brume tombent dans la salle.", "Mist tears fall into the room."),
        "tom.reset": ("Vieux Tom se remet en marche.", "Old Tom starts up again."),
        "tom.victory": ("Vieux Tom s'effondre : la barrière se dissipe.", "Old Tom collapses: the barrier fades."),
        "asura.enter": ("L'Asura fou réveille ses golems. Les charges + et - ne doivent pas se toucher !",
                        "The Mad Asura wakes his golems. + and - charges must not touch!"),
        "asura.wake": ("Un golem de cristal s'éveille.", "A crystal golem awakens."),
        "asura.all": ("L'Asura les réveille tous à la fois !", "The Asura wakes them all at once!"),
        "asura.reset": ("L'Asura fou recolle les morceaux de ses golems.", "The Mad Asura glues his golems back together."),
        "asura.victory": ("L'Asura fou s'enfuit dans les Brumes en hurlant.", "The Mad Asura flees into the Mists, screaming."),
        "charge.positive": ("Vous portez une charge + : tenez-vous loin des charges -.", "You carry a + charge: keep away from - charges."),
        "charge.negative": ("Vous portez une charge - : tenez-vous loin des charges +.", "You carry a - charge: keep away from + charges."),
        "charge.flip.positive": ("Votre charge s'inverse : +.", "Your charge flips: +."),
        "charge.flip.negative": ("Votre charge s'inverse : -.", "Your charge flips: -."),
        "title.victory": ("Inclassable terminée", "Uncategorized complete"),
        "bossbar.batteries": ("batteries", "batteries"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -------------------------------------------------------------------------------------------------

def java_layout():
    J = fc
    cells = ",\n".join(f"            {J.jpoint((side * 15.5, YARD, zc + 0.5), False)}" for side, zc in CELLS)
    doors = ",\n".join("            " + J.jblocks(door_cells(side, zc)) for side, zc in CELLS)
    zones = ",\n".join("            " + J.jbox(*b[:2], b[2], b[3], *b[4:]) for b in JUMP_ZONES)
    gol = J.jpoints([(x, ARENA, z) for x, z in golems()], False)
    pylons = ", ".join("{" + f"{J.jd(x + 0.5)}, {J.jd(GROUND_Y + ARENA)}, {J.jd(z + 0.5)}, {s}" + "}" for x, z, s in PYLONS)
    harpies = J.jpoints([(x + (4 if k % 2 else -4), k + 5, z) for k, (x, z) in enumerate(PATH1) if k % 3 == 2], False)
    harpies2 = J.jpoints([(x + 4, stand + 3, z) for k, (x, z, stand) in enumerate(path2()) if k % 5 == 2], False)
    lx0, lx1, lz0, lz1 = LANDING_TOP
    rx0, rx1, rz0, rz1 = ROOM
    cx, cz = ARENA_CENTER
    return f"""package dev.nakasar.hytale.fractals.uncategorized;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions de l'Inclassable, écrites par tools/generate_uncategorized.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class UncategorizedLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Harpies des premières et des secondes plates-formes. */
    public static final double[][] HARPIES = {harpies};
    public static final double[][] HARPIES_2 = {harpies2};
    public static final List<Box> JUMP_ZONES = List.of(
{zones});

    /** Cour de la prison. */
    public static final Box YARD = {J.jbox(PLAZA[0], PLAZA[1], YARD - 1, YARD + 4, PLAZA[2], PLAZA[3])};
    public static final double[] YARD_CHECKPOINT = {J.jpoint((0, YARD, -24))};
    public static final double[] GENERATOR = {J.jpoint(GENERATOR_AT)};
    /** Prisonniers (pieds, dans leur cellule) et portes de barreaux, dans l'ordre de libération. */
    public static final double[][] PRISONERS = {{
{cells}}};
    public static final int[][][] CELL_DOORS = {{
{doors}}};
    public static final int[][] GATE_YARD = {J.jblocks(GATE_YARD)};

    /** Escalier mortel : bas (z) et haut, x des voies des tourelles, hauteur debout d'une case. */
    public static final int STAIRS_BOTTOM_Z = {STAIRS[2]};
    public static final int STAIRS_TOP_Z = {STAIRS[3]};
    public static final int STAIRS_X0 = {STAIRS[0]};
    public static final int STAIRS_X1 = {STAIRS[1]};
    public static final int[] TURRETS_X = {{{", ".join(str(x) for x in TURRETS_X)}}};
    public static final double TURRET_Y = {GROUND_Y + TOP}.0;
    public static final double TURRET_Z = {TURRET_Z + 0.5};
    public static final Box STAIRS = {J.jbox(STAIRS[0] - 1, STAIRS[1] + 1, YARD - 1, TOP + 4, STAIRS[3], STAIRS[2] + 1)};
    public static final Box LANDING_TOP = {J.jbox(lx0, lx1, TOP - 1, TOP + 4, lz0, lz1)};
    public static final int[][] CONSOLES = {J.jblocks(CONSOLES)};
    public static final int[][] GATE_TOP = {J.jblocks(GATE_TOP)};
    public static final double[] TOP_CHECKPOINT = {J.jpoint((0, TOP, -95))};

    /** Salle de Vieux Tom. */
    public static final Box ROOM = {J.jbox(rx0, rx1, TOP - 1, TOP + 8, rz0, rz1)};
    public static final double[] TOM = {J.jpoint(TOM_AT, False)};
    public static final int[] FAN = {J.jblock(FAN)};
    public static final int[][] BATTERIES = {J.jblocks(BATTERIES)};
    public static final int[][] GATE_TOM = {J.jblocks(GATE_TOM)};
    public static final double[] VENT = {J.jpoint((0, TOP + 5, rz0))};
    public static final double[] ROOM_CENTER = {J.jpoint((0, TOP, -120))};

    /** Plates-formes de lueur et arène de l'Asura. */
    public static final double[] PAD2_CHECKPOINT = {J.jpoint((0, TOP, -141))};
    public static final double[] ARENA_CENTER = {J.jpoint((cx, ARENA, cz))};
    public static final double ARENA_RADIUS = {ARENA_RADIUS};
    public static final double[] ASURA = {J.jpoint(ASURA_AT, False)};
    public static final double[][] GOLEMS = {gol};
    /** Pylônes de charge (x, y, z, signe), actifs seulement quand on est seul. */
    public static final double[][] PYLONS = {{{pylons}}};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private UncategorizedLayout() {{
    }}
}}
"""


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name in (LANDING, GLIMMER):
        return (255, 230, 140) if name == GLIMMER else (120, 200, 255)
    if name in (MIST, PINK):
        return (230, 140, 220)
    if name in (CONSOLE, BATTERY, FAN_BLOCK, PYLON):
        return (120, 230, 255)
    if "Gold" in name:
        return (230, 190, 90)
    if "Marble" in name or "Quartzite" in name:
        return (220, 216, 210)
    return (140, 140, 150)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, tex, base, accent, glyph, light, use, solid, alpha, opacity in blocks():
        fc.write_block(LANG, name, tex, base, accent, glyph, light, use, solid, alpha, opacity)
    tear = fc.held_item(LANG, TEAR, "Mist_Tear", tear_parts(), 31, (0, 5, 0), 14.0, quality="Rare", stack=8)
    fc.write_json(fc.OBJECTS / f"{TEAR}.json", tear)
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Charge_Positive.png", (255, 208, 64), "plus")
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Charge_Negative.png", (64, 160, 255), "minus")
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Harried.png", (220, 200, 160), "feather")
    fc.write_json(fc.SERVER / "Entity/Damage/Nakasar_Fractal_Gas.json", gas_cause())
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
    counts = fc.write_instance(INSTANCE, "Inclassable", PREFAB_DIR, sections, SPAWN, "#6ab04a",
                                WEATHER, fc.weather("#4a78d8", "#f0d0ec", "#e0c8e8", (60, 380), 0.2, "#fff2e8"), "11:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Inclassable : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules ; cour {YARD}, palier {TOP}, arène {ARENA}")
    if preview:
        fc.top_view(p, preview / "inclassable_dessus.png", color_of)


if __name__ == "__main__":
    main()
