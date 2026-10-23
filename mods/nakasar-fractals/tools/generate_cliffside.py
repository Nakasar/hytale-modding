#!/usr/bin/env python3
"""Génère la Falaise (Cliffside), première fractale de la saison 1 (étape 4 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_cliffside.py [--preview DOSSIER]

Un colosse enchaîné, adossé à une falaise des Brumes. Le groupe monte le long de son corps et brise cinq sceaux avec
le marteau des cultistes, jusqu'à l'Archidevin sur la plate-forme suspendue devant sa tête :

1. le camp au pied du colosse : les cultistes, le Chercheur, le râtelier du marteau ;
2. l'escalier d'échafaudage jusqu'à la passerelle des genoux : deux sceaux (genoux), vagues de cultistes ;
3. le tunnel aux plaques de pointes, puis le saut des gargouilles le long de la falaise (souffles qui poussent dans le
   vide, leviers en haut qui les coupent ; une chute ramène à la dernière plate-forme sûre) ;
4. la passerelle du torse : le sceau de la poitrine, trois foyers dont deux s'embrasent à chaque cycle ;
5. l'escalier jusqu'aux épaules et les deux bras : les sceaux des poignets, protégés à tour de rôle par une bulle,
   que les incantateurs réparent ; vagues sans fin ;
6. les rampes aux bombes devant le cou (leviers en haut qui les arrêtent) ;
7. l'arène de l'Archidevin : le sceau du cou au centre, six cages au bord.

Le générateur écrit :
- trois prefabs posés ensemble au même point (falaise, colosse, parcours) et l'instance `Nakasar_Fractal_Cliffside`
  (biome, structure du monde) qui remplace l'ébauche de l'étape 2 ;
- les blocs du mod (sceau gravé, barrière de brume, plate-forme sûre, plaque, râtelier, gargouille, levier, porte de
  cage) avec leurs textures et icônes ;
- le marteau du culte (`Nakasar_Fractal_Cult_Hammer`), les effets (Corruption, enraciné, hâte, protection, forme
  démoniaque), la cause de dégâts de la Corruption, les particules (souffle, pointes, marteau chargé, sceau) ;
- les modèles et rôles des cultistes (fanatique, incantateur), du Chercheur, des dévoreurs, des sceaux (PNJ fixes :
  le jeu refuse les coups sur les blocs dans nos instances) et de l'Archidevin, leurs attaques ;
- la langue `nakasar_fractals_cliffside.lang` (objets, PNJ, messages du Java) ;
- `cliffside/CliffsideLayout.java` : toutes les positions dont le Java a besoin.

Repère : celui de l'Observatoire (x vers l'est, z vers le sud, y vers le haut). Les prefabs sont posés en
(0, GROUND_Y, 0) ; leur y = 0 est la première couche d'air au-dessus du plateau du camp. Dans le Java, y monde =
GROUND_Y + y prefab. « Debout à y » veut dire : le sol est en y - 1.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_models as fm
import fractal_nature as fn
import fractal_roles as fr
import generate_block_models as block_models
import generate_observatory as go

MOD = go.MOD
SERVER = go.SERVER
COMMON = go.COMMON
LANG = "nakasar_fractals_cliffside"
JAVA_LAYOUT = MOD / "src/main/java/dev/nakasar/hytale/fractals/cliffside/CliffsideLayout.java"
INSTANCE = "Nakasar_Fractal_Cliffside"
WEATHER = "Nakasar_Fractal_Weather_Cliffside"
PREFAB_DIR = "Cliffside"
GENERATOR = "generate_cliffside.py"
ITEMS = go.ITEMS / "Cliffside"
INTERACTIONS = go.INTERACTIONS / "Cliffside"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/Fractals"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Fractals"
PARTICLES = SERVER / "Particles/Nakasar/Fractals/Cliffside"
MODELS = SERVER / "Models/Nakasar/Fractals"
ROLES = SERVER / "NPC/Roles/Nakasar/Fractals"
NPC_MODELS = "NPC/Nakasar/Fractals"
STATUS_ICONS = "UI/StatusEffects/Nakasar/Fractals"
GROUND_Y = go.GROUND_Y

# --- hauteurs (y prefab, « debout à ») ------------------------------------------------------------
KNEES = 22          # passerelle des genoux
SEGMENTS = 6        # tronçons du saut des gargouilles, +5 blocs chacun
CHEST = KNEES + 5 * SEGMENTS   # passerelle du torse (52)
SHOULDERS = CHEST + 20         # épaules et bras (72)
ARENA = SHOULDERS + 18         # arène de l'Archidevin (90)

# --- lieux ----------------------------------------------------------------------------------------
SPAWN = (0, 0, 20)
START_EXIT = (3, 0, 23)
CAMP_CENTER = (0, -10)
ALTAR_AT = (0, -30)               # autel du camp ; le râtelier du marteau est posé dessus
RACK = (0, 1, -30)
SEEKER = (3.5, 0, -27.5)
CAMP_WAVE = [(-6, -14), (6, -14), (-3, -20), (3, -20), (0, -8)]

PLATEAU = (-30, 30, -58, 26)      # x0, x1, z0, z1, sol en y = -1
CLIFF_Z = -58                     # face de la falaise (la roche est en z <= CLIFF_Z)

S1 = (25, -37)                    # escalier d'échafaudage du camp aux genoux (centre)
D1 = (-18, 20, -41, -33)          # passerelle des genoux (x0, x1, z0, z1), debout à KNEES
KNEE_SEALS = [(-8.5, KNEES, -39.5), (8.5, KNEES, -39.5)]
KNEE_WAVES = [[(-11, -36), (-6, -36), (-9, -34)], [(11, -36), (6, -36), (9, -34)]]
BUTTRESS = (-42, -19, -41, -32, 14, 28)   # contrefort percé du tunnel (x0, x1, z0, z1, y0, y1)
TUNNEL = (-42, -19, -38, -35)             # tunnel aux plaques, sol en KNEES - 1, haut de 4
GATE1 = [(-18, y, z) for y in range(KNEES, KNEES + 4) for z in range(-38, -34)]
PATH = (-47, -43, -49, -35)               # du tunnel au saut des gargouilles, debout à KNEES

PUZZLE_EAST = (-50, -46)          # plates-formes est du saut (x0, x1)
PUZZLE_WEST = (-66, -62)          # plates-formes ouest
PUZZLE_Z = (-56, -50)             # plates-formes (z0, z1)
STONE_Z = [(-55, -54), (-52, -51)]   # pierres des tronçons pairs / impairs (z0, z1)
STONES_WEST = [(-52, -53), (-55, -56), (-58, -59), (-60, -61)]   # pierres d'un tronçon vers l'ouest (x)
GARGOYLE_X = [-54, -59]           # gargouilles d'un tronçon, dans la falaise (z = CLIFF_Z + 1)
LEVERS_TOP = [(-49, CHEST, -56), (-48, CHEST, -56), (-47, CHEST, -56)]   # un levier par groupe de gargouilles
WALK_TOP = [(-45, -20, -52, -50), (-21, -19, -52, -40), (-21, -17, -41, -39)]   # du saut au torse, debout à CHEST

D2 = (-18, 18, -42, -31)          # passerelle du torse, debout à CHEST
CHEST_SEAL = (0.5, CHEST, -40.5)
CHEST_WAVES = [(-8, -33), (8, -33), (-4, -32), (4, -32)]
FIRES = [(-9, -37), (0, -35), (9, -37)]
FIRE_RADIUS = 4.5
S2 = (0, -26)                     # escalier du torse aux épaules
GATE2 = [(x, y, -31) for x in range(-4, 5) for y in range(CHEST, CHEST + 3)]
BRIDGE_S2 = (-1, 1, -43, -31)     # pont du haut de S2 aux épaules, debout à SHOULDERS

WRIST_SEALS = [(-44.5, SHOULDERS, -51.5), (45.5, SHOULDERS, -51.5)]
WRIST_WAVES = [[(-40, -54), (-38, -50), (-42, -50)], [(41, -54), (39, -50), (43, -50)]]
P1 = (-18, -12, -43, -37)         # départ des rampes, debout à SHOULDERS
GATE3 = [(x, y, -43) for x in range(-18, -11) for y in range(SHOULDERS, SHOULDERS + 3)]
R1 = (-12, 14, -39, -37, SHOULDERS, SHOULDERS + 9)        # x départ, x arrivée, z0, z1, debout départ / arrivée
LA = (15, 19, -41, -31)
R2 = (14, -13, -35, -33, SHOULDERS + 9, ARENA)
LB = (-18, -14, -37, -27)
RAMP_LEVERS = [(-17, ARENA, -36), (-15, ARENA, -36)]

ARENA_CENTER = (0, -12)
ARENA_RADIUS = 16
ARENA_ENTRY = (-11, -23)          # là où le pont de LB touche l'arène
NECK_SEAL = (0.5, ARENA, -11.5)
BOSS_SPAWN = (0.5, ARENA, -2.5)
CAGE_ANGLES = [255, 315, 15, 75, 135, 195]   # degrés (0 = +x, sens z+), l'entrée est vers 225°
CAGE_RADIUS = 13
REWARD_AT = (-2, ARENA, -19)
END_EXIT_AT = (2, ARENA, -19)

# Zones de saut : une chute à plus de 4 blocs sous la dernière plate-forme sûre de la zone y ramène (x0, x1, y0, y1,
# z0, z1). La zone des rampes commence sous les épaules : la passerelle du torse et l'escalier S2 restent hors zone.
JUMP_ZONES = [(-70, -40, -60, CHEST + 8, -60, -44), (-22, 22, SHOULDERS - 8, ARENA + 6, -44, -26)]
GUST_REACH = 13                   # portée d'un souffle de gargouille vers le sud (blocs)

# --- blocs ----------------------------------------------------------------------------------------
SEAL_STONE = "Nakasar_Fractal_Seal_Stone"
MIST_BARRIER = "Nakasar_Fractal_Mist_Barrier"
LANDING = "Nakasar_Fractal_Landing"
PLATE = "Nakasar_Fractal_Pressure_Plate"
RACK_BLOCK = "Nakasar_Fractal_Hammer_Rack"
GARGOYLE = "Nakasar_Fractal_Gargoyle"
LEVER = "Nakasar_Fractal_Lever"
CAGE_DOOR = "Nakasar_Fractal_Cage_Door"
CAGE_CELL = go.CAGE_CELL
EXIT_STONE = go.EXIT_STONE

HAMMER = "Nakasar_Fractal_Cult_Hammer"
CORRUPTION = "Nakasar_Fractal_Corruption"

ROLE_FANATIC = "Nakasar_Fractal_Cultist_Fanatic"
ROLE_CHANTER = "Nakasar_Fractal_Cultist_Chanter"
ROLE_SEEKER = "Nakasar_Fractal_Seeker"
ROLE_DEVOURER = "Nakasar_Fractal_Devourer"
ROLE_SEAL = "Nakasar_Fractal_Seal"
ROLE_BOSS = "Nakasar_Fractal_Archdiviner"
FOE_ROLES = [ROLE_FANATIC, ROLE_CHANTER, ROLE_DEVOURER, ROLE_SEAL, ROLE_BOSS]

PLANKS = "Wood_Darkwood_Planks"
PLANKS_HALF = "Wood_Darkwood_Planks_Half"
BEAM = "Wood_Darkwood_Beam"
AIR = go.AIR


# --- géométrie -------------------------------------------------------------------------------------

def step_blocks(p, x, z, level, full=PLANKS, half=PLANKS_HALF):
    """Marche dont le dessus est à `level` (entier ou demi) : bloc plein dessous, demi-bloc pour le demi."""
    base = math.floor(level)
    p.set(x, base - 1, z, full)
    if level - base >= 0.5:
        p.set(x, base, z, half)


def floor(p, x0, x1, z0, z1, stand, block=PLANKS, edge=None):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for z in range(min(z0, z1), max(z0, z1) + 1):
            border = x in (x0, x1) or z in (z0, z1)
            p.set(x, stand - 1, z, edge if edge and border else block)


def spiral(p, cx, cz, y0, y1, landing=PLANKS):
    """Escalier d'échafaudage autour d'un pilier : anneau de 2 blocs (distances 3 et 4 du centre), +0,5 par case,
    départ au nord-ouest, sens horaire vu du dessus. Plancher plein en haut (sauf au-dessus des dernières marches).
    Rend la liste des cases (x, z, debout) des marches."""
    ring = []
    for i in range(-3, 3):
        ring.append((i, -3))
    for i in range(-3, 3):
        ring.append((3, i))
    for i in range(3, -3, -1):
        ring.append((i, 3))
    for i in range(3, -3, -1):
        ring.append((-3, i))
    steps = []
    n = int((y1 - y0) * 2)
    for k in range(n):
        rx, rz = ring[k % len(ring)]
        level = y0 + 0.5 * (k + 1)
        out = (rx + (1 if rx == 3 else -1 if rx == -3 else 0), rz + (1 if rz == 3 else -1 if rz == -3 else 0))
        for (dx, dz) in ((rx, rz), out):
            step_blocks(p, cx + dx, cz + dz, level)
        steps.append((cx + rx, cz + rz, level))
    # Pilier central et poteaux d'angle.
    for y in range(y0 - 1, y1 + 3):
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) == 2 or abs(dz) == 2:
                    p.set(cx + dx, y, cz + dz, BEAM if (abs(dx) == 2 and abs(dz) == 2) else PLANKS)
    for dx, dz in ((-5, -5), (5, -5), (5, 5), (-5, 5)):
        for y in range(y0 - 1, y1):
            p.set(cx + dx, y, cz + dz, BEAM)
    # Plancher du haut, troué au-dessus des marches qui y arrivent.
    last = {(x, z) for x, z, lv in steps if lv > y1 - 4}
    for dx in range(-5, 6):
        for dz in range(-5, 6):
            x, z = cx + dx, cz + dz
            if max(abs(dx), abs(dz)) >= 3 and (x, z) not in last and not ((x - (1 if dx == 4 else -1 if dx == -4 else 0),
                                                                          z - (1 if dz == 4 else -1 if dz == -4 else 0)) in last):
                p.set(x, y1 - 1, z, landing)
    return steps


CLIFF_HALF = 92                   # demi-largeur de la falaise
CLIFF_BACK = -76                  # dos de la falaise (jamais vu, pas écrit)
CLIFF_STRATA = ["Rock_Stone", "Rock_Slate", "Rock_Stone", "Rock_Shale", "Rock_Stone", "Rock_Slate"]
BASALT_STRATA = ["Rock_Basalt", "Rock_Basalt", "Rock_Slate", "Rock_Basalt", "Rock_Shale"]
# Pas de corniche là où elle gênerait le parcours : saut des gargouilles, colosse, bras.
NO_LEDGE = [(-72, -38, KNEES - 6, CHEST + 12), (-24, 24, -60, ARENA + 40), (-54, -16, SHOULDERS - 12, SHOULDERS + 2),
            (16, 54, SHOULDERS - 12, SHOULDERS + 2), (-44, 44, -60, 6)]


def rock(x, y, z):
    """Roche de la falaise : strates lisses et un peu penchées, plaques moussues."""
    if fn.vnoise3(x, y, z, 7, 17) > 0.42:
        return "Rock_Stone_Mossy"
    band = math.floor((y + x * 0.07 + 3 * fn.fbm2(x, z, 26, 2, 5)) / 4)
    return CLIFF_STRATA[band % len(CLIFF_STRATA)]


def basalt(x, y, z):
    """Pierre du colosse : basalte en couches lisses."""
    band = math.floor((y + 2.5 * fn.fbm2(x + z, z, 18, 2, 9)) / 3)
    return BASALT_STRATA[band % len(BASALT_STRATA)]


def cliff_wrap(x):
    """Recul vers le sud des deux bouts de la falaise (amphithéâtre autour du colosse)."""
    return ((abs(x) - 68) / 24) ** 2 * 34 if abs(x) > 68 else 0.0


def cliff_face(x, y):
    """z de la face de la falaise (case de roche la plus au sud) en (x, y)."""
    protected = -72 <= x <= -38 and KNEES - 6 <= y <= CHEST + 12
    recess = 0 if protected else round(2.5 + 2.5 * fn.fbm2(x, y, 9, 3, 41))
    return CLIFF_Z - max(0, min(5, recess)) + round(cliff_wrap(x))


def cliff_crest(x):
    return ARENA + 12 + round(5 * fn.fbm2(x, 0, 20, 2, 3)) - round(cliff_wrap(x) * 0.35)


def cliff_bottom(x):
    return -40 + round(8 * fn.fbm2(x, 7, 15, 2, 4))


def cliff_prefab():
    """Falaise des Brumes derrière le colosse : masse rocheuse en amphithéâtre (seule la coque visible est écrite),
    strates, mousse, corniches herbues avec fleurs et lianes, crête boisée, gargouilles."""
    p = go.Prefab()
    faces = {}
    for x in range(-CLIFF_HALF, CLIFF_HALF + 1):
        for y in range(cliff_bottom(x), cliff_crest(x) + 1):
            faces[(x, y)] = cliff_face(x, y)
    for (x, y), f in faces.items():
        crest = cliff_crest(x)
        around = [faces.get((x + dx, y + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        zs = range(CLIFF_BACK, f + 1) if None in around else range(min(min(around) + 1, f), f + 1)
        for z in zs:
            if y == crest:
                block = fn.soil(x, z, 3)
            elif y >= crest - 2:
                block = fn.DIRT[int(fn.hash01(x, y, z, 2) * len(fn.DIRT))]
            else:
                block = rock(x, y, z)
            p.set(x, y, z, block)
    # Crête : herbe, fleurs et résineux.
    crest_cells = []
    for x in range(-CLIFF_HALF, CLIFF_HALF + 1):
        crest = cliff_crest(x)
        for z in range(CLIFF_BACK, faces[(x, crest)] + 1):
            crest_cells.append((x, crest, z))
    for x in range(-CLIFF_HALF + 3, CLIFF_HALF - 2, 5):
        if fn.hash01(x, 0, 0, 51) < 0.7:
            crest = cliff_crest(x)
            z = faces[(x, crest)] - 2 - int(fn.hash01(x, 1, 0, 52) * 8)
            if fn.hash01(x, 2, 0, 53) < 0.65:
                fn.conifer(p, x, crest + 1, z, 8 + int(fn.hash01(x, 3, 0, 54) * 6), "fir" if x % 2 else "cedar", seed=x)
            else:
                fn.broadleaf(p, x, crest + 1, z, 5 + int(fn.hash01(x, 3, 0, 55) * 3), "oak", seed=x)
    fn.flora(p, crest_cells, seed=61, density=0.6, flowers=0.12)
    # Corniches : bandes herbues qui sortent de 1 à 3 blocs, fleuries, lianes dessous.
    ledge_cells = []
    for gy in range(-28, ARENA + 4, 7):
        for gx in range(-CLIFF_HALF + 4, CLIFF_HALF - 3, 9):
            cx = gx + int(fn.hash01(gx, gy, 0, 71) * 5) - 2
            cy = gy + int(fn.hash01(gx, gy, 1, 72) * 4) - 2
            if fn.hash01(gx, gy, 2, 73) > 0.62 or cy >= cliff_crest(cx) - 6:
                continue
            w = 3 + int(fn.hash01(gx, gy, 3, 74) * 6)
            depth = 1 + int(fn.hash01(gx, gy, 4, 75) * 3)
            if any(x0 - 3 <= cx + i <= x1 + 3 and y0 <= cy <= y1 for x0, x1, y0, y1 in NO_LEDGE for i in (-w, 0, w)):
                continue
            for i in range(-w, w + 1):
                x = cx + i
                d = round(depth * (1 - (abs(i) / (w + 1)) ** 2))
                if d < 1 or (x, cy) not in faces:
                    continue
                f = faces[(x, cy)]
                for dz in range(1, d + 1):
                    p.set(x, cy, f + dz, fn.soil(x, f + dz, 3))
                    ledge_cells.append((x, cy, f + dz))
                    if dz < d:
                        p.set(x, cy - 1, f + dz, rock(x, cy - 1, f + dz))
                    elif fn.hash01(x, cy, dz, 76) < 0.4:
                        vine = fn.HANGING[int(fn.hash01(x, dz, cy, 77) * len(fn.HANGING))]
                        for k in range(1 + int(fn.hash01(cy, x, dz, 78) * 5)):
                            if fn.free(p, x, cy - 1 - k, f + dz):
                                p.set(x, cy - 1 - k, f + dz, vine)
                if fn.hash01(x, cy, 0, 79) < 0.12:
                    fn.shrub(p, x, cy + 1, f + 1, seed=x, leaves="Plant_Leaves_Oak")
    fn.flora(p, ledge_cells, seed=81, density=0.7, flowers=0.22)
    # Gargouilles : une statue par pierre de tronçon, adossée à la roche (bloc plein derrière).
    for g in gargoyles():
        x, y, z = g["at"]
        p.set(x, y, z - 1, "Rock_Stone_Brick")
        p.set(x, y, z, GARGOYLE)
        p.set(x, y - 1, z, "Rock_Stone_Brick_Half")
    return p


def colossus_cells():
    """Le colosse : union de boîtes (x0, x1, y0, y1, z0, z1), et les cases de ses yeux."""
    K, C, S = KNEES, CHEST, SHOULDERS
    boxes = [
        (-13, -4, 0, 5, -56, -38), (4, 13, 0, 5, -56, -38),            # pieds
        (-12, -5, 5, K, -55, -44), (5, 12, 5, K, -55, -44),            # tibias
        (-13, -4, K, K + 8, -55, -42), (4, 13, K, K + 8, -55, -42),    # genoux
        (-14, -3, K + 8, C - 6, -56, -44), (3, 14, K + 8, C - 6, -56, -44),   # cuisses
        (-16, 16, C - 8, C - 2, -57, -45),                             # bassin
        (-17, 17, C - 2, S - 2, -58, -46),                             # torse
        (-12, 12, C, C + 12, -58, -43),                                # poitrine bombée (le sceau)
        (-20, 20, S - 6, S - 1, -56, -44),                             # épaules
        (-52, -18, S - 9, S - 1, -56, -48), (18, 52, S - 9, S - 1, -56, -48),   # bras tendus
        (-5, 5, S, S + 7, -56, -49),                                   # cou
        (-8, 8, S + 8, S + 22, -58, -45),                              # tête
        (-9, 9, S + 18, S + 24, -58, -46),                             # front et crâne
    ]
    cells = set()
    for x0, x1, y0, y1, z0, z1 in boxes:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    cells.add((x, y, z))
    eyes = {(x, y, -45) for x in (-5, -4, -3, 3, 4, 5) for y in (S + 15, S + 16)}
    return cells, eyes


def colossus_prefab(avoid=()):
    """Le colosse de basalte, mousse sur ses faces du dessus et lianes sous les bras et le menton. `avoid` : cases
    prises par le parcours (pas de mousse ni de liane dessus)."""
    p = go.Prefab()
    cells, eyes = colossus_cells()
    for (x, y, z) in cells:
        if all((x + dx, y + dy, z + dz) in cells for dx, dy, dz in
               ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
            continue
        p.set(x, y, z, "Rock_Crystal_Purple_Block" if (x, y, z) in eyes else basalt(x, y, z))
    for (x, y, z) in cells:
        above, below = (x, y + 1, z), (x, y - 1, z)
        if above not in cells and above not in avoid and fn.fbm2(x + 3 * z, y, 7, 2, 23) > 0.15 and fn.hash01(x, y, z, 24) < 0.7:
            p.set(*above, "Plant_Moss_Rug_Green" if fn.hash01(z, x, y, 25) < 0.7 else "Plant_Moss_Short_Green")
        if below not in cells and y > 2 and fn.hash01(x, y, z, 26) < 0.14:
            vine = fn.HANGING[int(fn.hash01(z, y, x, 27) * len(fn.HANGING))]
            for k in range(1 + int(fn.hash01(y, z, x, 28) * 4)):
                at = (x, y - 1 - k, z)
                if at in cells or at in avoid or not fn.free(p, *at):
                    break
                p.set(*at, vine)
    # Fers aux poignets (anneaux de basalte taillé) et chaînes qui pendent vers la falaise.
    S = SHOULDERS
    for sx in (-1, 1):
        for x in (sx * 47, sx * 48):
            for y in range(S - 10, S + 1):
                for z in range(-57, -46):
                    if y in (S - 10, S) or z in (-57, -47):
                        p.set(x, y, z, "Rock_Basalt_Brick_Ornate")
        for x in (sx * 40, sx * 50):
            for y in range(S - 30, S - 10):
                p.set(x, y, -52, "Deco_Iron_Chains_Vertical")
    # Runes violettes gravées sur le torse et les genoux (lueurs du culte).
    for x, y in ((-6, CHEST + 4), (6, CHEST + 4), (0, CHEST + 9), (-9, KNEES + 4), (9, KNEES + 4)):
        p.set(x, y, -43 if y >= CHEST else -42, "Rock_Crystal_Purple_Block")
    return p


def puzzle_layout():
    """Le saut des gargouilles : plates-formes (x0, x1, debout) et pierres (x, z0, z1, debout), de bas en haut."""
    landings = [(PUZZLE_EAST, KNEES)]
    stones = []
    level = KNEES
    for s in range(SEGMENTS):
        westward = s % 2 == 0
        z0, z1 = STONE_Z[s % 2]
        order = STONES_WEST if westward else [tuple(reversed(c)) for c in reversed(STONES_WEST)]
        for k, pair in enumerate(order):
            for x in pair:
                stones.append((x, z0, z1, level + k + 1, s))
        level += 5
        landings.append((PUZZLE_WEST if westward else PUZZLE_EAST, level))
    assert level == CHEST, (level, CHEST)
    return landings, stones


def gargoyles():
    """Gargouilles : position (bloc dans la falaise), groupe (2 tronçons par groupe), décalage de cycle."""
    _, stones = puzzle_layout()
    out = []
    for s in range(SEGMENTS):
        levels = {x: lv for x, _, _, lv, seg in stones if seg == s}
        for k, gx in enumerate(GARGOYLE_X):
            near = min(levels, key=lambda x: abs(x - gx))
            out.append({"at": (gx, levels[near] + 1, CLIFF_Z + 1), "group": s // 2, "offset": round((s * 1.7 + k * 2.5) % 5, 2)})
    return out


def plates():
    """Plaques du tunnel : (x, z, piégée). Deux sur trois sont piégées (choix déterministe, les mêmes à chaque partie)."""
    out = []
    x0, x1, z0, z1 = TUNNEL
    for x in range(x0 + 1, x1):
        for z in range(z0, z1 + 1):
            if (x * 7 + z * 3) % 5 in (0, 2):
                out.append((x, z, (x * 31 + z * 17) % 3 != 0))
    return out


def cages():
    out = []
    cx, cz = ARENA_CENTER
    for a in CAGE_ANGLES:
        r = math.radians(a)
        x, z = round(cx + math.cos(r) * CAGE_RADIUS), round(cz + math.sin(r) * CAGE_RADIUS)
        # La porte regarde le centre, sur l'axe dominant.
        dx, dz = cx - x, cz - z
        door = (1 if dx > 0 else -1, 0) if abs(dx) >= abs(dz) else (0, 1 if dz > 0 else -1)
        out.append((x, z, door))
    return out


def ramp_cells(ramp):
    """Cases d'une rampe : (x, z, debout), du départ à l'arrivée ; +0,5 au plus par case."""
    xa, xb, z0, z1, ya, yb = ramp
    n = abs(xb - xa)
    step = 1 if xb > xa else -1
    out = []
    for k in range(n + 1):
        level = ya + math.floor((yb - ya) * k / n * 2 + 1e-9) / 2
        for z in range(z0, z1 + 1):
            out.append((xa + k * step, z, level))
    return out


def course_prefab():
    p = go.Prefab()
    # Plateau du camp au pied du colosse : île au contour irrégulier (sol en y = -1, bosses sur le pourtour), dessous
    # rocheux plus profond au centre, chemins de terre battue et sol usé du camp.
    tops = plateau_tops()
    edge = edge_distance(tops)
    fn.island(p, tops, lambda x, z: 3 + min(24, edge[(x, z)] * 1.2) + 2 * fn.fbm2(x, z, 6, 2, 13), seed=7,
              grass=plateau_ground, hang=0.14)
    # Camp : autel de basalte et râtelier, braseros, caisses, tentes de toile (blocs simples).
    ax, az = ALTAR_AT
    p.fill(ax - 1, 0, az - 1, ax + 1, 0, az + 1, "Rock_Basalt_Brick_Ornate")
    p.set(*RACK, RACK_BLOCK)
    for bx, bz in ((-4, -28), (4, -28), (-8, -10), (8, -10), (-3, 16), (3, 16)):
        p.set(bx, 0, bz, "Furniture_Temple_Dark_Brazier")
    for bx, bz in ((-12, -6), (-12, -5), (12, -6), (13, -6), (-11, 2), (11, 3)):
        p.set(bx, 0, bz, "Furniture_Ancient_Crate" if (bx + bz) % 2 else "Furniture_Ancient_Barrel")
    for tx, tz in ((-16, -2), (16, -2)):
        for k, h in enumerate((2, 3, 3, 2)):
            for dz in range(-2, 3):
                p.set(tx - 3 + k, h, tz + dz, "Wood_Darkwood_Planks_Half")
        p.set(tx - 3, 0, tz - 2, BEAM)
        p.set(tx, 0, tz - 2, BEAM)
    p.set(-7, 0, 3, "Bench_Campfire")
    p.set(*START_EXIT, EXIT_STONE)
    for sx in range(-2, 3):
        for sz in range(17, 25):
            p.set(sx, -1, sz, "Rock_Stone_Brick_Smooth")
    # Escalier S1 du camp aux genoux, puis passerelle D1.
    spiral(p, S1[0], S1[1], 0, KNEES)
    floor(p, *D1, KNEES, block=PLANKS, edge=BEAM)
    for x in range(D1[0], D1[1] + 1, 6):
        for y in range(0, KNEES - 1):
            p.set(x, y, D1[3], BEAM)
    # Contrefort et tunnel aux plaques.
    bx0, bx1, bz0, bz1, by0, by1 = BUTTRESS
    tx0, tx1, tz0, tz1 = TUNNEL
    for x in range(bx0, bx1 + 1):
        for y in range(by0, by1 + 1):
            for z in range(bz0, bz1 + 1):
                inside = tx0 <= x <= tx1 and tz0 <= z <= tz1 and KNEES <= y <= KNEES + 3
                shell = x in (bx0, bx1) or y in (by0, by1) or z in (bz0, bz1) or (
                    tx0 - 1 <= x <= tx1 + 1 and tz0 - 1 <= z <= tz1 + 1 and KNEES - 1 <= y <= KNEES + 4)
                if inside:
                    p.set(x, y, z, AIR)
                elif shell:
                    p.set(x, y, z, rock(x, y, z))
    for x in range(tx0, tx1 + 1):
        for z in range(tz0, tz1 + 1):
            p.set(x, KNEES - 1, z, "Rock_Stone_Brick")
    for x, z, _ in plates():
        p.set(x, KNEES - 1, z, PLATE)
    for x in range(tx0, tx1 + 1, 5):
        p.set(x, KNEES + 3, tz0, "Deco_Lantern")
    for at in GATE1:
        p.set(*at, MIST_BARRIER)
    # Du tunnel au saut des gargouilles.
    floor(p, *PATH, KNEES, block=PLANKS, edge=BEAM)
    # Saut des gargouilles : plates-formes sûres (dalles d'arrivée) et pierres.
    landings, stones = puzzle_layout()
    for (lx0, lx1), stand in landings:
        for x in range(lx0, lx1 + 1):
            for z in range(PUZZLE_Z[0], PUZZLE_Z[1] + 1):
                p.set(x, stand - 1, z, LANDING)
                p.set(x, stand - 2, z, "Rock_Stone_Brick")
    for x, sz0, sz1, stand, _ in stones:
        for z in range(sz0, sz1 + 1):
            p.set(x, stand - 1, z, "Rock_Stone_Brick_Smooth")
            p.set(x, stand - 2, z, "Rock_Stone_Brick_Half")
    for at in LEVERS_TOP:
        p.set(*at, LEVER)
    # Du haut du saut au torse (debout à CHEST).
    for box in WALK_TOP:
        floor(p, *box, CHEST, block=PLANKS)
    floor(p, *D2, CHEST, block=PLANKS, edge=BEAM)
    for x in range(-4, 5):
        p.set(x, CHEST - 1, -31, PLANKS)
    for fx, fz in FIRES:
        for x in range(fx - 4, fx + 5):
            for z in range(fz - 4, fz + 5):
                if math.hypot(x - fx, z - fz) <= FIRE_RADIUS - 0.5 and D2[2] <= z <= D2[3]:
                    p.set(x, CHEST - 1, z, "Rock_Basalt_Brick")
        p.set(fx, CHEST - 1, fz, "Rock_Basalt_Brick_Ornate")
    for x in range(D2[0], D2[1] + 1, 6):
        for y in range(KNEES, CHEST - 1):
            p.set(x, y, D2[3] - 1, BEAM)
    # Escalier S2, barrière G2 à son pied, pont vers les épaules.
    spiral(p, S2[0], S2[1], CHEST, SHOULDERS)
    for at in GATE2:
        p.set(*at, MIST_BARRIER)
    floor(p, *BRIDGE_S2, SHOULDERS, block=PLANKS)
    # Départ des rampes (P1), barrière G3, rampes R1 et R2, paliers LA et LB.
    for x in range(P1[0], P1[1] + 1):
        for z in range(P1[2], P1[3] + 1):
            p.set(x, SHOULDERS - 1, z, LANDING)
    for at in GATE3:
        p.set(*at, MIST_BARRIER)
    for ramp in (R1, R2):
        for x, z, level in ramp_cells(ramp):
            step_blocks(p, x, z, level, full="Rock_Stone_Brick", half="Rock_Stone_Brick_Half")
    for box, stand in ((LA, SHOULDERS + 9), (LB, ARENA)):
        for x in range(box[0], box[1] + 1):
            for z in range(box[2], box[3] + 1):
                p.set(x, stand - 1, z, LANDING)
                p.set(x, stand - 2, z, "Rock_Stone_Brick")
    for at in RAMP_LEVERS:
        p.set(*at, LEVER)
    # Arène : disque de basalte, garde-corps (ouvert vers le pont), dessous en cône, pont depuis LB.
    cx, cz = ARENA_CENTER
    entry = math.atan2(ARENA_ENTRY[1] - cz, ARENA_ENTRY[0] - cx)
    for x in range(cx - ARENA_RADIUS - 1, cx + ARENA_RADIUS + 2):
        for z in range(cz - ARENA_RADIUS - 1, cz + ARENA_RADIUS + 2):
            d = math.hypot(x - cx, z - cz)
            if d > ARENA_RADIUS + 0.5:
                continue
            ring = (d // 3) % 2
            p.set(x, ARENA - 1, z, "Rock_Basalt_Brick_Smooth" if ring else "Rock_Basalt_Brick")
            bottom = ARENA - 2 - int(9 * (1 - (d / (ARENA_RADIUS + 0.5)) ** 1.5))
            for y in range(bottom, ARENA - 1):
                p.set(x, y, z, basalt(x, y, z))
            a = math.atan2(z - cz, x - cx)
            gap = abs(math.atan2(math.sin(a - entry), math.cos(a - entry))) < 0.2
            if d > ARENA_RADIUS - 0.5 and not gap:
                p.set(x, ARENA, z, "Rock_Basalt_Brick_Half")
    for k in range(9):
        t = k / 8
        bxz = (LB[0] + 2 + (ARENA_ENTRY[0] - LB[0] - 2) * t, LB[3] + (ARENA_ENTRY[1] - LB[3]) * t)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                p.set(round(bxz[0] + dx), ARENA - 1, round(bxz[1] + dz), "Rock_Basalt_Brick_Smooth")
    # Chaînes de l'arène vers la tête du colosse (décor).
    for x in (-6, 6):
        for z in range(-44, cz - ARENA_RADIUS + 1):
            p.set(x, ARENA + 3 + (z + 44) // 6, z, "Deco_Iron_Chains")
    # Cages : bloc de cage aux pieds, barreaux sur trois côtés, porte de 2 blocs vers le centre, toit.
    for x, z, (ddx, ddz) in cages():
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                p.set(x + dx, ARENA + 2, z + dz, "Rock_Basalt_Brick")
                if dx == 0 and dz == 0:
                    continue
                for y in (ARENA, ARENA + 1):
                    if (dx, dz) == (ddx, ddz):
                        p.set(x + dx, y, z + dz, CAGE_DOOR)
                    elif dx != 0 and dz != 0:
                        p.set(x + dx, y, z + dz, "Rock_Basalt_Brick_Pillar_Middle")
                    else:
                        # Barreaux le long de z (côtés est et ouest) : rotation 1.
                        p.set(x + dx, y, z + dz, "Deco_Iron_Bars", 1 if dx != 0 else 0)
        p.set(x, ARENA, z, CAGE_CELL)
        p.set(x, ARENA + 1, z, AIR)
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            p.set(x, ARENA - 1, z, SEAL_STONE)
    plateau_vegetation(p, tops, edge)
    return p


def plateau_tops():
    """Dessus du plateau {(x, z): y} : le rectangle PLATEAU (sol en y = -1) et un pourtour irrégulier de 2 à 11 blocs
    (pas au nord, la falaise y est), avec quelques bosses."""
    x0, x1, z0, z1 = PLATEAU
    tops = {}
    for x in range(x0 - 11, x1 + 12):
        for z in range(z0, z1 + 12):
            dx = max(x0 - x, 0, x - x1)
            dz = max(0, z - z1)
            out = math.hypot(dx, dz)
            reach = 2 + 9 * (fn.fbm2(x, z, 13, 3, 31) + 1) / 2
            if out > reach:
                continue
            bump = 1 if out > 1.5 and fn.fbm2(x, z, 5, 2, 33) > 0.35 else 0
            tops[(x, z)] = -1 + bump
    return tops


def edge_distance(tops):
    """Distance (en cases, pas de 4 voisins) de chaque case du plateau au vide."""
    from collections import deque
    dist = {}
    queue = deque()
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


# Chemins de terre battue : du départ au camp, du camp à l'autel, du camp à l'escalier S1 (segments, largeur).
PATHS = [((0, 17), (0, -4), 1.6), ((0, -4), (2, -14), 1.6), ((0, -22), (0, -27), 1.4), ((4, -18), (20, -32), 1.4)]
CAMP_GROUND = (0, -14, 9.5)       # sol usé du camp (centre x, z, rayon)


def _segment_distance(x, z, a, b):
    (ax, az), (bx, bz) = a, b
    vx, vz = bx - ax, bz - az
    t = max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / float(vx * vx + vz * vz)))
    return math.hypot(x - ax - vx * t, z - az - vz * t)


def plateau_ground(x, z):
    """Bloc du dessus du plateau : terre battue sur les chemins, sol usé du camp, herbe ailleurs."""
    wobble = 0.5 * fn.fbm2(x, z, 4, 2, 37)
    for a, b, w in PATHS:
        d = _segment_distance(x, z, a, b)
        if d <= w + wobble:
            return "Soil_Pathway"
        if d <= w + 1.2 + wobble and fn.hash01(x, z, 1, 38) < 0.5:
            return "Soil_Gravel_Mossy"
    cx, cz, r = CAMP_GROUND
    d = math.hypot(x - cx, z - cz) - 2 * fn.fbm2(x, z, 7, 2, 39)
    if d <= r:
        n = fn.fbm2(x, z, 4, 2, 40)
        return "Soil_Pathway" if n > 0.25 else "Soil_Dirt" if n > -0.2 else "Soil_Gravel"
    if d <= r + 2 and fn.hash01(x, z, 2, 41) < 0.5:
        return "Soil_Gravel_Mossy"
    return fn.soil(x, z, 7)


# Pas d'arbre ici (camp, chemin du départ, escalier S1, devant le colosse, contrefort).
NO_TREE = [(-21, 21, -34, 8), (-5, 5, 6, 34), (16, 34, -46, -28), (-25, 25, -62, -30), (-47, -14, -62, -27)]


def plateau_vegetation(p, tops, edge):
    """Arbres (feuillus variés, quelques résineux), buissons, rochers moussus, puis herbes et fleurs partout où il
    reste de l'herbe à l'air libre."""
    trees = []
    kinds = ["oak", "oak", "birch", "beech", "maple", "oak", "birch"]
    for gx in range(-40, 41, 3):
        for gz in range(-30, 36, 3):
            x = gx + int(fn.hash01(gx, gz, 0, 91) * 3) - 1
            z = gz + int(fn.hash01(gx, gz, 1, 92) * 3) - 1
            if (x, z) not in tops or edge[(x, z)] < 2 or fn.hash01(gx, gz, 2, 93) > 0.55:
                continue
            if any(a <= x <= b and c <= z <= d for a, b, c, d in NO_TREE):
                continue
            if any(math.hypot(x - tx, z - tz) < 6 for tx, tz in trees):
                continue
            y = tops[(x, z)]
            if not p.blocks.get((x, y, z), ("",))[0].startswith("Soil_Grass") or not fn.free(p, x, y + 1, z):
                continue
            trees.append((x, z))
            h = fn.hash01(x, z, 3, 94)
            if h < 0.18:
                fn.conifer(p, x, y + 1, z, 9 + int(h * 20), "fir", seed=x * 7 + z)
            else:
                kind = kinds[int(fn.hash01(x, z, 4, 95) * len(kinds))]
                fn.broadleaf(p, x, y + 1, z, 5 + int(fn.hash01(x, z, 5, 96) * 4), kind, seed=x * 7 + z)
    for (x, z), y in sorted(tops.items()):
        if any(a <= x <= b and c <= z <= d for a, b, c, d in NO_TREE[:2]):
            continue
        if not p.blocks.get((x, y, z), ("",))[0].startswith("Soil_Grass") or not fn.free(p, x, y + 1, z):
            continue
        h = fn.hash01(x, y, z, 97)
        if h < 0.02:
            fn.shrub(p, x, y + 1, z, seed=x + z, leaves="Plant_Leaves_Oak" if (x + z) % 3 else "Plant_Leaves_Beech")
        elif h < 0.05:
            p.set(x, y + 1, z, fn.BUSHES[int(fn.hash01(z, x, y, 98) * len(fn.BUSHES))])
        elif h < 0.056 and edge[(x, z)] >= 1:
            fn.boulder(p, x, y + 1, z, 1.0 + fn.hash01(x, z, 6, 99) * 1.2, seed=x * 3 + z)
    cells = [(x, y, z) for (x, z), y in tops.items() if p.blocks.get((x, y, z), ("",))[0].startswith("Soil_Grass")]
    fn.flora(p, cells, seed=101, density=0.55, flowers=0.16)


# --- blocs, textures, objets ------------------------------------------------------------------------

def texture(path, base, accent, glyph):
    """Textures propres à la Falaise ; les autres glyphes viennent de l'Observatoire."""
    if glyph not in ("seal", "mist", "landing", "plate", "rack", "gargoyle", "lever", "bars"):
        return go.texture(path, base, accent, glyph)
    img = Image.new("RGBA", (32, 32), base + (255,))
    d = ImageDraw.Draw(img)
    dark = tuple(int(c * 0.65) for c in base) + (255,)
    acc = accent + (255,)
    d.rectangle((0, 0, 31, 31), outline=dark)
    if glyph == "seal":
        d.ellipse((5, 5, 26, 26), outline=acc, width=2)
        d.polygon(((16, 7), (24, 21), (8, 21)), outline=acc)
        d.polygon(((16, 25), (8, 11), (24, 11)), outline=acc)
    elif glyph == "mist":
        for k in range(6):
            d.arc((2 + k * 2, 4 + k * 3, 30 - k * 2, 22 + k), 200, 340, fill=acc, width=1)
    elif glyph == "landing":
        d.rectangle((3, 3, 28, 28), outline=acc, width=2)
        d.line((16, 7, 16, 25), fill=acc, width=2)
        d.line((7, 16, 25, 16), fill=acc, width=2)
    elif glyph == "plate":
        d.rectangle((4, 4, 27, 27), outline=dark, width=2)
        for k in range(3):
            d.rectangle((8 + k * 6, 8, 10 + k * 6, 23), fill=dark)
    elif glyph == "rack":
        d.rectangle((6, 6, 25, 9), fill=acc)
        d.line((10, 9, 10, 27), fill=acc, width=2)
        d.line((21, 9, 21, 27), fill=acc, width=2)
        d.rectangle((13, 12, 18, 18), outline=acc)
    elif glyph == "gargoyle":
        d.polygon(((6, 26), (10, 8), (16, 14), (22, 8), (26, 26)), fill=dark)
        d.ellipse((10, 14, 14, 18), fill=acc)
        d.ellipse((18, 14, 22, 18), fill=acc)
        d.line((11, 22, 21, 22), fill=acc, width=2)
    elif glyph == "lever":
        d.rectangle((8, 20, 23, 27), fill=dark)
        d.line((16, 22, 22, 6), fill=acc, width=3)
        d.ellipse((19, 3, 25, 9), fill=acc)
    elif glyph == "bars":
        for x in range(5, 30, 6):
            d.line((x, 2, x, 29), fill=acc, width=2)
        d.line((2, 8, 29, 8), fill=acc, width=2)
        d.line((2, 23, 29, 23), fill=acc, width=2)
    img.save(path)
    return img


def blocks():
    """(id, texture, fond, couleur, glyphe, lumière, interaction, plein)."""
    stone = (70, 66, 92)
    return [
        (SEAL_STONE, "Seal_Stone", (54, 40, 78), (196, 120, 255), "seal", "#a6f", None, True),
        (MIST_BARRIER, "Mist_Barrier", (60, 46, 110), (200, 170, 255), "mist", "#86d", None, True),
        (LANDING, "Landing", (88, 96, 120), (150, 200, 255), "landing", None, None, True),
        (PLATE, "Pressure_Plate", (96, 90, 84), (140, 130, 120), "plate", None, None, True),
        (RACK_BLOCK, "Hammer_Rack", (80, 56, 40), (196, 120, 255), "rack", "#a6f", "Nakasar_Fractal_Use_Hammer_Rack", True),
        (GARGOYLE, "Gargoyle", (96, 96, 104), (220, 230, 255), "gargoyle", None, None, True),
        (LEVER, "Lever", stone, (230, 200, 120), "lever", None, "Nakasar_Fractal_Use_Cliffside_Lever", True),
        (CAGE_DOOR, "Cage_Door", (40, 36, 44), (150, 140, 170), "bars", None, "Nakasar_Fractal_Use_Cage_Door", True),
    ]


def hammer_item():
    return {
        "$Comment": "Marteau du culte (Falaise) : la masse d'onyx vanilla, seule arme qui brise les sceaux. Tenu en main, "
                    "il fait monter la Corruption d'un cran toutes les 10 s (rangé, elle redescend) ; un ennemi frappé "
                    "avec, ou tué après avoir été frappé par le porteur, ou tué à moins de 10 blocs, le charge "
                    "(Brise-sceau). Retiré quand on quitte la fractale (dev.nakasar.hytale.fractals.hammer.HammerSystem). "
                    "Généré par tools/generate_cliffside.py.",
        "Parent": "Weapon_Mace_Onyxium",
        "TranslationProperties": {"Name": f"{LANG}.items.{HAMMER}.name", "Description": f"{LANG}.items.{HAMMER}.description"},
        "Quality": "Legendary",
        "MaxStack": 1,
    }


def status_icon(path, color, glyph):
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 121, 121), fill=(28, 16, 40, 255), outline=color + (255,), width=6)
    if glyph == "corruption":
        for k in range(5):
            a = math.radians(k * 72 + 90)
            d.line((64, 64, 64 + math.cos(a) * 44, 64 - math.sin(a) * 44), fill=color + (255,), width=8)
        d.ellipse((50, 50, 78, 78), fill=(255, 220, 255, 255))
    elif glyph == "rooted":
        for k in range(4):
            d.arc((24 + k * 8, 40, 104 - k * 8, 120), 180, 360, fill=color + (255,), width=6)
    elif glyph == "haste":
        for k in range(3):
            d.polygon(((30 + k * 22, 36), (52 + k * 22, 64), (30 + k * 22, 92)), fill=color + (255,))
    elif glyph == "shield":
        d.polygon(((64, 24), (100, 38), (94, 86), (64, 108), (34, 86), (28, 38)), outline=color + (255,), width=8)
    elif glyph == "demon":
        d.polygon(((30, 40), (44, 18), (52, 46)), fill=color + (255,))
        d.polygon(((98, 40), (84, 18), (76, 46)), fill=color + (255,))
        d.ellipse((40, 54, 56, 70), fill=color + (255,))
        d.ellipse((72, 54, 88, 70), fill=color + (255,))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


CORRUPTION_TIERS = [(1, "#d8c040", "#5a4a10"), (2, "#e08030", "#5a2a08"), (3, "#e03030", "#4a0808")]


def effects():
    out = {}
    for tier, top, bottom in CORRUPTION_TIERS:
        out[f"{CORRUPTION}_{tier}"] = {
            "$Comment": f"Corruption du marteau, cran {tier} : {tier * 8} % de dégâts subis en plus. Posé par HammerSystem "
                        f"pour un cran entier (10 s) : la jauge se vide, puis le cran monte (marteau en main) ou descend.",
            "Name": f"{LANG}.effects.{CORRUPTION}_{tier}",
            "Debuff": True,
            "StatusEffectIcon": f"{STATUS_ICONS}/Corruption_{tier}.png",
            "ApplicationEffects": {"EntityTopTint": top, "EntityBottomTint": bottom},
            "DamageResistance": {k: [{"CalculationType": "Percent", "Amount": -0.08 * tier}]
                                 for k in ("Physical", "Projectile", "Elemental")},
            "OverlapBehavior": "Overwrite",
            "Infinite": False,
            "Duration": 2,
        }
    out[fr.ROOTED] = {
        "$Comment": "Posé sur un PNJ des fractales pendant qu'il arme une attaque annoncée : il ne recule plus sous les "
                    "coups. Copie de Nakasar_Elite_Rooted du mod Vampires.",
        "Duration": 2.5, "OverlapBehavior": "Overwrite", "RemovalBehavior": "Duration", "Debuff": False,
        "ApplicationEffects": {"KnockbackMultiplier": 0},
    }
    out["Nakasar_Fractal_Lever_Rooted"] = {
        "$Comment": "Joueur qui tire un levier de la Falaise : immobile quelques secondes (le levier est dur).",
        "Name": f"{LANG}.effects.Nakasar_Fractal_Lever_Rooted",
        "Debuff": True,
        "StatusEffectIcon": f"{STATUS_ICONS}/Rooted.png",
        "ApplicationEffects": {"MovementEffects": {"DisableAll": True}},
        "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 4,
    }
    out["Nakasar_Fractal_Archdiviner_Haste"] = {
        "$Comment": "Archidevin sous 25 % de vie : il accélère.",
        "Name": f"{LANG}.effects.Nakasar_Fractal_Archdiviner_Haste",
        "StatusEffectIcon": f"{STATUS_ICONS}/Haste.png",
        "ApplicationEffects": {"HorizontalSpeedMultiplier": 1.35, "EntityTopTint": "#ff9a4a"},
        "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 6,
    }
    out["Nakasar_Fractal_Archdiviner_Protection"] = {
        "$Comment": "Archidevin entre 50 et 25 % de vie : protection (un tiers des dégâts en moins).",
        "Name": f"{LANG}.effects.Nakasar_Fractal_Archdiviner_Protection",
        "StatusEffectIcon": f"{STATUS_ICONS}/Protection.png",
        "DamageResistance": {k: [{"CalculationType": "Percent", "Amount": 0.33}] for k in ("Physical", "Projectile", "Elemental")},
        "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 6,
    }
    out["Nakasar_Fractal_Archdiviner_Demon"] = {
        "$Comment": "Forme démoniaque de l'Archidevin (niveau 71 et plus, sous 25 % de vie) : teinte rouge sombre, dégâts "
                    "infligés × 1,3 (Java).",
        "Name": f"{LANG}.effects.Nakasar_Fractal_Archdiviner_Demon",
        "StatusEffectIcon": f"{STATUS_ICONS}/Demon.png",
        "ApplicationEffects": {"EntityTopTint": "#7a0a1a", "EntityBottomTint": "#1a0004"},
        "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 6,
    }
    return out


def corruption_cause():
    return {"$Comment": "Dégâts de la Corruption du marteau (prise en main : 10 % des PV max), que l'armure ne réduit pas.",
            "BypassResistances": True, "DurabilityLoss": False, "StaminaLoss": False, "DamageTextColor": "#c070ff"}


def spikes_cause():
    return {"$Comment": "Dégâts des plaques à pointes et des pièges de la Falaise (une part des PV max).",
            "BypassResistances": True, "DurabilityLoss": False, "StaminaLoss": False, "DamageTextColor": "#e0e0e0"}


# --- particules ---------------------------------------------------------------------------------

def spawner(color0, color1, count, speed, pitch, spread, height, life=(0.5, 0.9), size=(0.2, 0.4),
            texture="Particles/Textures/Basic/Spark.png", blend="BlendAdd", gravity=None):
    doc = {
        "RenderMode": blend,
        "ParticleRotationInfluence": "Billboard",
        "ParticleLifeSpan": {"Min": life[0], "Max": life[1]},
        "ParticleRotateWithSpawner": False,
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "LinearFiltering": True,
        "Particle": {
            "Texture": texture,
            "ScaleRatioConstraint": "OneToOne",
            "UVOption": "RandomFlipUV",
            "SoftParticles": "Disable",
            "Animation": {"0": {"Opacity": 0, "Color": color0}, "25": {"Opacity": 1}, "100": {"Opacity": 0, "Color": color1}},
            "InitialAnimationFrame": {"Opacity": 1, "Scale": {"X": {"Min": size[0], "Max": size[1]}}},
        },
        "Shape": "Sphere",
        "SpawnBurst": True,
        "EmitOffset": {"X": {"Min": 0, "Max": spread}, "Y": {"Min": 0, "Max": height}, "Z": {"Min": 0, "Max": spread}},
        "InitialVelocity": {"Speed": {"Min": speed[0], "Max": speed[1]}, "Yaw": {"Min": -180, "Max": 180},
                            "Pitch": {"Min": pitch[0], "Max": pitch[1]}},
        "TotalParticles": {"Min": count, "Max": count},
        "MaxConcurrentParticles": count,
    }
    if gravity is not None:
        doc["Attractors"] = [{"LinearAcceleration": {"Y": gravity}}]
    return doc


PARTICLE_SYSTEMS = {
    # id : (commentaire, [(suffixe, spawner, décalage Y)])
    "Nakasar_Fractal_Gust_Windup": ("Gargouille qui prend son souffle : poussière grise sur sa gueule.",
                                    [("Dust", spawner("#d8d4cc", "#8a8478", 10, (0.3, 0.8), (-20, 40), 1.0, 1.0,
                                                      blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Gust": ("Souffle de gargouille : traînée de vent blanc vers le sud.",
                             [("Wind", spawner("#ffffff", "#c8d8ff", 18, (4.0, 7.0), (-10, 10), 1.2, 2.0,
                                               life=(0.6, 1.1)), 0.3)]),
    "Nakasar_Fractal_Spikes": ("Plaque piégée : pointes de pierre qui jaillissent.",
                               [("Shards", spawner("#e8e4dc", "#7a7468", 12, (3.0, 5.0), (70, 90), 0.8, 0.2,
                                                   life=(0.3, 0.5), blend="BlendLinear"), 0.0)]),
    "Nakasar_Fractal_Hammer_Charged": ("Marteau chargé (Brise-sceau) : étincelles bleues autour du porteur.",
                                       [("Sparks", spawner("#c8e8ff", "#3a7aff", 6, (0.4, 0.9), (40, 90), 0.8, 1.8), 0.2)]),
    "Nakasar_Fractal_Corruption_Pulse": ("Corruption qui monte : volutes violettes sur le porteur du marteau.",
                                         [("Wisps", spawner("#e0a0ff", "#3a0a5a", 5, (0.2, 0.5), (60, 90), 0.6, 1.6,
                                                            blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Seal_Break": ("Un sceau se fissure : éclats violets et lumière blanche.",
                                   [("Burst", spawner("#ffffff", "#a040ff", 24, (2.0, 4.5), (-30, 90), 1.0, 2.5,
                                                      life=(0.5, 1.0), size=(0.3, 0.6)), 0.5)]),
    "Nakasar_Fractal_Seal_Mend": ("Un incantateur répare un sceau : fil violet sombre qui s'y enroule.",
                                  [("Mend", spawner("#7a2ab0", "#2a0040", 10, (0.3, 0.8), (60, 90), 1.0, 2.5,
                                                    blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Heal_Foes": ("Incantation de soin des cultistes : anneau vert-violet autour du lanceur.",
                                  [("Ring", spawner("#c0ffb0", "#7a40c0", 16, (1.5, 2.5), (-5, 5), 0.5, 0.3), 0.3)]),
    "Nakasar_Fractal_Bomb_Blast": ("Bombe des rampes qui éclate.",
                                   [("Blast", spawner("#fff0b0", "#ff5a1a", 20, (2.5, 5.0), (-10, 90), 0.8, 0.6,
                                                      life=(0.3, 0.6), size=(0.3, 0.6)), 0.2)]),
}


def particle_files():
    out = {}
    for sid, (comment, spawners) in PARTICLE_SYSTEMS.items():
        out[f"{sid}.particlesystem"] = {
            "$Comment": f"{comment} Généré par tools/{GENERATOR}.",
            "Spawners": [{"SpawnerId": f"{sid}_{suffix}", "PositionOffset": {"Y": y}} for suffix, _, y in spawners],
            "CullDistance": 72,
        }
        for suffix, doc, _ in spawners:
            out[f"{sid}_{suffix}.particlespawner"] = doc
    return out


# --- modèles ------------------------------------------------------------------------------------

CLOTH = "Fantasy_Cotton_Dark"


def fanatic_model():
    return fr.humanoid(
        "Fanatique du culte de la Falaise : capuche et robe violet sombre, bandeau rouge. Squelette du joueur.",
        "05", "Face_Scar", [
            ("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            ("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
            ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
             "Faded_Leather", "Black"),
            ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Black"),
        ])


def chanter_model():
    return fr.humanoid(
        "Incantateur du culte : robe de mage, cape violette, mains nues pour les incantations.",
        "11", "Face_Sunken", [
            ("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat_Green.png"),
            ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
             CLOTH, "Purple"),
            ("Cosmetics/Shoes/AngledBoots.blockymodel", "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots_Green.png"),
        ], light={"Color": "#a6f", "Radius": 2})


def seeker_model():
    doc = fr.humanoid(
        "Le Chercheur : érudit qui a suivi le culte jusqu'au colosse, manteau long et chapeau à large bord.",
        "03", "Almond_Eyes_Face", [
            ("Cosmetics/Head/WideBrimHat.blockymodel", "Cosmetics/Head/WideBrimHat.png", "Faded_Leather", "Brown"),
            ("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png",
             "Faded_Leather", "BrownDark"),
            ("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Brown"),
            ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Black"),
        ])
    doc["DefaultAttachments"][1]["GradientId"] = "Blue"   # yeux normaux (pas un cultiste)
    return doc


def boss_model():
    return fr.humanoid(
        "L'Archidevin : chef du culte, grand (× 1,35), couronne, cape royale violette et robe de mage, yeux rouges.",
        "28", "Face_Scar", [
            ("Cosmetics/Head/KingsCrown.blockymodel", "Cosmetics/Head/KingsCrown_Red.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            ("Cosmetics/Capes/Cape_King_NoNeck.blockymodel", "Cosmetics/Capes/Cape_King_Texture.png", "Fantasy_Cotton", "Purple"),
            ("Cosmetics/Gloves/LongDetail_Gloves.blockymodel",
             "Cosmetics/Gloves/LongDetail_Gloves_Textures/Wasteland_Marauder_Texture.png"),
            ("Cosmetics/Shoes/HeavyBoots.blockymodel", "Cosmetics/Shoes/HeavyBoots_Textures/HeavyLeather_Black.png"),
        ], scale=(1.35, 1.35), light={"Color": "#c6f", "Radius": 3})


def devourer_model():
    return {
        "$Comment": "Dévoreur (provisoire) : l'aberration vanilla petite, lueur violette du culte. À remplacer par un "
                    "modèle de scarabée quand l'id vanilla sera vérifié dans Assets.zip.",
        "Parent": "Zombie_Aberrant_Small",
        "Light": {"Color": "#a6f", "Radius": 2},
    }


def seal_parts():
    """Sceau : socle de basalte, pierre gravée, cristal violet, anneau de plaques. 64 unités par bloc."""
    basalt, rune, light = (54, 50, 64), (120, 60, 190), (230, 190, 255)
    parts = [
        ("Base", (0, 8, 0), (72, 16, 72), 45, fm.smooth(basalt), "flat"),
        ("Stone", (0, 70, 0), (52, 108, 30), 0, fm.smooth((70, 62, 92)), "flat"),
        ("Rune_Front", (0, 76, 15.5), (30, 60, 1), 0, fm.crystal(rune, light), "fullbright"),
        ("Rune_Back", (0, 76, -15.5), (30, 60, 1), 0, fm.crystal(rune, light), "fullbright"),
        ("Crystal", (0, 140, 0), (26, 34, 26), 45, fm.crystal(rune, light), "fullbright"),
        ("Crown", (0, 162, 0), (14, 12, 14), 45, fm.crystal(light, (255, 255, 255)), "fullbright"),
    ]
    for k in range(4):
        a = math.radians(90 * k + 45)
        parts.append((f"Plate_{k}", (math.cos(a) * 40, 120, math.sin(a) * 40), (10, 22, 4), 90 * k + 45,
                      fm.crystal(fm.shade(rune, 0.6), rune), "fullbright"))
    return parts


def write_seal_model():
    parts = seal_parts()
    atlas, uv = fm.build_atlas(parts, 7, tex_w=256)
    out = COMMON / NPC_MODELS / "Seal"
    out.mkdir(parents=True, exist_ok=True)
    atlas.save(out / "Texture.png")
    model = fm.build_model("Body", parts, uv)
    model["format"] = "character"
    (out / "Model.blockymodel").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    return {
        "$Comment": "Sceau du culte (PNJ fixe) : pierre gravée et cristal violet, générés par tools/generate_cliffside.py. "
                    "Seul un coup de marteau chargé le fissure (dev.nakasar.hytale.fractals.cliffside.Seals).",
        "Model": f"{NPC_MODELS}/Seal/Model.blockymodel",
        "Texture": f"{NPC_MODELS}/Seal/Texture.png",
        "EyeHeight": 1.5,
        "HitBox": {"Max": {"X": 0.6, "Y": 2.7, "Z": 0.6}, "Min": {"X": -0.6, "Y": 0, "Z": -0.6}},
        "MinScale": 1, "MaxScale": 1,
        "Light": {"Color": "#a6f", "Radius": 4},
    }


# --- attaques ----------------------------------------------------------------------------------

ROOTED_FX = {"Type": "ApplyEffect", "EffectId": fr.ROOTED}
CLEAR_INTERRUPT = {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"}


def charge_pose(seconds, anim_set="Mace", sound="SFX_Spear_Throw_Charge", particle_node="R-Hand"):
    return [{"Type": "Simple", "RunTime": seconds,
             "Effects": {"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": "SwingDownCharging",
                         "WorldSoundEventId": sound,
                         "Particles": [{"SystemId": "Fire_Blue", "TargetNodeName": particle_node, "Scale": 1.5,
                                        "PositionOffset": {"Y": 0.3}, "RotationOffset": {"Pitch": 180}}]}},
            {"Type": "Simple", "RunTime": 0.15,
             "Effects": {"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": "SwingDownCharged",
                         "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam"}},
            {"Type": "Simple", "RunTime": 0.5}]


def interactions():
    out = {}
    out["Nakasar_Fractal_Fanatic_Attack"] = {
        "$Comment": "Fanatique : deux revers d'épée rouillée (9 dégâts chacun), sans annonce.",
        "Type": "Serial", "Interactions": [
            fr.swing("Revers gauche.", "Mace", "SwingLeft", 0.35, 9),
            fr.swing("Revers droit.", "Mace", "SwingRight", 0.35, 9, direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Fanatic_Slam"] = {
        "$Comment": "Fanatique : coup abattu annoncé par un cercle rouge de 2,8 blocs (1,2 s, 22 dégâts, projection).",
        "Type": "Serial", "Interactions": [
            CLEAR_INTERRUPT, ROOTED_FX,
            fr.telegraph("Circle", 1.2, Radius=2.8, Damage=22, Knockback=6, KnockUp=4,
                         HitParticle="Impact_Sword_Basic_Stronk", ImpactSound="SFX_Mace_T2_Signature_Impact"),
        ] + charge_pose(1.2)}
    out["Nakasar_Fractal_Chanter_Attack"] = {
        "$Comment": "Incantateur au contact : coup de bâton (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bâton.", "Staff", "SwingLeft", 0.4, 6)]}
    out["Nakasar_Fractal_Chanter_Hex"] = {
        "$Comment": "Incantateur : maléfice sur sa cible, cercle rouge de 2 blocs à ses pieds (1,4 s) ; 14 dégâts et poison.",
        "Type": "Serial", "Interactions": [
            fr.telegraph("Circle", 1.4, Anchor="Target", Radius=2.0, Damage=14, EffectId="Poison_T2", EffectDuration=4,
                         PlayersOnly=True, ImpactParticle="Effect_Poison"),
            {"Type": "Simple", "RunTime": 1.4, "Effects": {"ItemPlayerAnimationsId": "Staff", "ItemAnimationId": "SwingRight",
                                                           "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Chanter_Heal"] = {
        "$Comment": "Incantateur : soigne les cultistes à moins de 10 blocs (25 PV chacun), anneau vert-violet.",
        "Type": "Serial", "Interactions": [
            {"Type": "Nakasar_Fractal_HealFoes", "Radius": 10, "Amount": 25, "Particle": "Nakasar_Fractal_Heal_Foes"},
            {"Type": "Simple", "RunTime": 1.0, "Effects": {"ItemPlayerAnimationsId": "Staff", "ItemAnimationId": "SwingLeft",
                                                           "WorldSoundEventId": "SFX_Spirit_Root_Spawn"}}]}
    out["Nakasar_Fractal_Devourer_Bite"] = {
        "$Comment": "Dévoreur au contact : morsure (8 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.35, 8, end=2.2)]}
    out["Nakasar_Fractal_Devourer_Spit"] = {
        "$Comment": "Dévoreur à distance : crachat de venin, cercle rouge de 1,8 bloc sous la cible (1,2 s), 10 dégâts et poison.",
        "Type": "Serial", "Interactions": [
            fr.telegraph("Circle", 1.2, Anchor="Target", Radius=1.8, Damage=10, EffectId="Poison_T2", EffectDuration=3,
                         PlayersOnly=True, ImpactParticle="Effect_Poison"),
            {"Type": "Simple", "RunTime": 1.2}]}
    out["Nakasar_Fractal_Archdiviner_Attack"] = {
        "$Comment": "Archidevin : deux coups de marteau d'onyx (18 dégâts chacun), sans annonce.",
        "Type": "Serial", "Interactions": [
            fr.swing("Revers gauche.", "Mace", "SwingLeft", 0.4, 18, end=3.4),
            fr.swing("Revers droit.", "Mace", "SwingRight", 0.4, 18, end=3.4, direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Archdiviner_Cone"] = {
        "$Comment": "Archidevin : coup de marteau annoncé par un cône rouge de 120° et 6 blocs (1,6 s, 45 dégâts, "
                    "projection). Sa barre de défiance s'ouvre pendant la préparation : la briser l'étourdit 5 s.",
        "Type": "Serial", "Interactions": [
            CLEAR_INTERRUPT, ROOTED_FX,
            {"Type": "Nakasar_Fractal_OpenDefiance", "Seconds": 1.8},
            fr.telegraph("Cone", 1.6, Angle=120, Radius=6, Damage=45, Knockback=8, KnockUp=5,
                         HitParticle="Impact_Sword_Basic_Stronk", ImpactSound="SFX_Mace_T2_Signature_Impact"),
        ] + charge_pose(1.6)}
    out["Nakasar_Fractal_Archdiviner_Ground"] = {
        "$Comment": "Archidevin (au-dessus de 25 % de vie) : sol corrompu sous chaque joueur, cercles rouges de 2,5 blocs "
                    "(1,5 s), 12 dégâts et poison.",
        "Type": "Serial", "Interactions": [
            fr.telegraph("Circle", 1.5, Anchor="EachPlayer", Radius=2.5, Damage=12, EffectId="Poison_T2",
                         EffectDuration=4, PlayersOnly=True, ImpactParticle="Effect_Poison"),
            {"Type": "Simple", "RunTime": 1.5, "Effects": {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "Guard",
                                                           "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}]}
    out["Nakasar_Fractal_Archdiviner_Breaker"] = {
        "$Comment": "Archidevin (sous 50 % de vie) : brise-échine, il bondit sur sa cible, cercle rouge de 3,5 blocs "
                    "(1,6 s) ; 40 dégâts et étourdissement 1,5 s (pas d'état à terre). Défiance ouverte pendant la "
                    "préparation.",
        "Type": "Serial", "Interactions": [
            CLEAR_INTERRUPT, ROOTED_FX,
            {"Type": "Nakasar_Fractal_OpenDefiance", "Seconds": 1.8},
            fr.telegraph("Circle", 1.6, Anchor="Target", Radius=3.5, Damage=40, TeleportCaster=True,
                         EffectId="Hazard_Electric_Stun", EffectDuration=1.5, PlayersOnly=True,
                         ImpactParticle="Stick_Slam_Ground_Large", ImpactSound="SFX_Goblin_Feastmaster_Slam"),
        ] + charge_pose(1.6)}
    # Blocs utilisables de la Falaise.
    for action, comment in (("Hammer_Rack", "Râtelier du camp : prendre le marteau du culte (un seul à la fois)."),
                            ("Cliffside_Lever", "Levier de la Falaise : coupe un groupe de gargouilles ou les bombes "
                                                "d'une rampe ; on reste figé 4 s à le tirer."),
                            ("Cage_Door", "Porte de cage de l'Archidevin : la forcer (5 fois) libère le prisonnier.")):
        out[f"Nakasar_Fractal_Use_{action}"] = {"$Comment": comment, "Type": "Nakasar_Fractal_CliffsideUse",
                                                 "Action": action}
    out["Nakasar_Fractal_PickUp_Hammer"] = {
        "$Comment": "Marteau du culte posé au sol : le ramasser avec la touche d'interaction (jamais en passant dessus, "
                    "hammer/HammerDropSystem).", "Type": "Nakasar_Fractal_PickUpHammer"}
    return out


def roots():
    melee_roots = ["Fanatic_Attack", "Fanatic_Slam", "Chanter_Attack", "Devourer_Bite", "Archdiviner_Attack",
                   "Archdiviner_Cone", "Archdiviner_Breaker"]
    ranged_roots = ["Chanter_Hex", "Chanter_Heal", "Devourer_Spit", "Archdiviner_Ground"]
    out = {}
    for name in melee_roots:
        out[f"Root_Nakasar_Fractal_NPC_{name}"] = fr.melee_tag(f"Nakasar_Fractal_{name}")
    for name in ranged_roots:
        out[f"Root_Nakasar_Fractal_NPC_{name}"] = fr.ranged_tag(f"Nakasar_Fractal_{name}")
    out["Root_Nakasar_Fractal_PickUp_Hammer"] = {"Interactions": ["Nakasar_Fractal_PickUp_Hammer"], "RequireNewClick": True}
    return out


def root(name):
    return f"Root_Nakasar_Fractal_NPC_{name}"


# --- rôles -------------------------------------------------------------------------------------

def npc_name(role_id):
    return f"{LANG}.npc.{role_id.removeprefix('Nakasar_Fractal_')}.name"


def fanatic_role():
    return fr.role(
        ROLE_FANATIC,
        "Fanatique du culte (vagues de la Falaise) : deux revers sans annonce, et toutes les 9 à 12 s un coup abattu "
        "annoncé par un cercle rouge. Posé par le Java (CliffsideWaves), jamais sauvegardé.",
        ROLE_FANATIC, npc_name(ROLE_FANATIC), 110,
        [fr.timed_attack("Slam", root("Fanatic_Slam"), rng=3.0, los=True, comment="Coup abattu annoncé."),
         fr.melee(root("Fanatic_Attack"), 2.4, (0.6, 1.0)),
         fr.chase(32, stop=1.6)],
        fr.walk(4.2), GENERATOR, sight=20, leash=40, home=False,
        timers=[fr.timer("Slam", (4, 6), (9, 12))],
        HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.0, DeathAnimationTime=1.0)


def chanter_role():
    return fr.role(
        ROLE_CHANTER,
        "Incantateur du culte : garde ses distances, maléfice annoncé sous sa cible toutes les 5 à 7 s, soigne les "
        "cultistes proches toutes les 7 à 9 s. Près d'un sceau, il le répare (CliffsideSeals).",
        ROLE_CHANTER, npc_name(ROLE_CHANTER), 80,
        [fr.timed_attack("Heal", root("Chanter_Heal"), comment="Soin des cultistes proches."),
         fr.cast("Hex", root("Chanter_Hex"), 16, "Maléfice annoncé sous sa cible."),
         fr.melee(root("Chanter_Attack"), 2.0, (0.9, 1.3)),
         fr.keep_distance(32, 6, 10)],
        fr.walk(3.6), GENERATOR, sight=20, leash=40, home=False,
        timers=[fr.timer("Heal", (3, 5), (7, 9)), fr.timer("Hex", (1, 3), (5, 7))],
        HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=0.0, DeathAnimationTime=1.0)


def devourer_role():
    return fr.role(
        ROLE_DEVOURER,
        "Dévoreur appelé par l'Archidevin (sous 50 % de vie) : crache du venin à distance (cercle rouge sous la cible), "
        "mord au contact.",
        ROLE_DEVOURER, npc_name(ROLE_DEVOURER), 70,
        [fr.cast("Spit", root("Devourer_Spit"), 14, "Crachat de venin annoncé."),
         fr.melee(root("Devourer_Bite"), 2.0, (0.8, 1.2)),
         fr.keep_distance(32, 5, 9)],
        fr.walk(3.8), GENERATOR, sight=24, leash=40, home=False,
        timers=[fr.timer("Spit", (1, 2), (4, 5))], KnockbackScale=0.0, DeathAnimationTime=1.0)


def static_role(role_id, comment, appearance, hp, attitude="Hostile"):
    return {
        "$Comment": f"{comment} Généré par tools/{GENERATOR}.",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": npc_name(role_id),
        "MaxHealth": hp,
        "StartState": "Idle",
        "DefaultPlayerAttitude": attitude,
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [fr.FOES],
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "SpawnLockTime": 0.2,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
    }


def seal_role():
    doc = static_role(ROLE_SEAL, "Sceau du culte : immobile et gelé, posé par le Java à sa place. Les coups ordinaires "
                      "ne lui font rien ; un coup de marteau chargé le fissure (sa vie montre ce qui reste).",
                      ROLE_SEAL, 300)
    doc["DisableDamageGroups"] = [fr.FOES]
    return doc


def seeker_role():
    doc = static_role(ROLE_SEEKER, "Le Chercheur : PNJ de décor au camp, invulnérable ; le Java annonce ce qu'il dit "
                      "à l'arrivée du groupe.", ROLE_SEEKER, 1000, attitude="Neutral")
    doc.pop("DisableDamageGroups")
    return doc


def boss_role():
    return fr.role(
        ROLE_BOSS,
        "L'Archidevin (boss de la Falaise), avec barre de vie de boss et barre de défiance : deux coups de marteau sans "
        "annonce ; cône de 120° annoncé (défiance ouverte) ; au-dessus de 25 % de vie, sol corrompu sous chaque joueur ; "
        "sous 50 %, brise-échine bondissant (défiance ouverte). Les transitions à 75/50/25 %, les cages, les dévoreurs, "
        "la ruée, les frappes marquées et la forme démoniaque sont menées par le Java (cliffside.Archdiviner).",
        ROLE_BOSS, npc_name(ROLE_BOSS), 2400,
        [fr.timed_attack("Cone", root("Archdiviner_Cone"), rng=5.5, los=True, comment="Cône annoncé, défiance ouverte."),
         fr.timed_attack("Breaker", root("Archdiviner_Breaker"), rng=18, los=True,
                         extra_sensors=[fr.health_between(0, 0.5)], comment="Brise-échine sous 50 % de vie."),
         fr.timed_attack("Ground", root("Archdiviner_Ground"), extra_sensors=[fr.health_between(0.25, 1.0)],
                         comment="Sol corrompu sous chaque joueur, au-dessus de 25 % de vie."),
         fr.melee(root("Archdiviner_Attack"), 3.2, (0.8, 1.2)),
         fr.chase(34, stop=2.2)],
        fr.walk(3.8), GENERATOR, sight=22, leash=34, home=True, heal=False,
        timers=[fr.timer("Cone", (5, 7), (11, 14)), fr.timer("Breaker", (6, 8), (14, 17)),
                fr.timer("Ground", (3, 5), (9, 11))],
        HotbarItems=["Weapon_Mace_Onyxium"], KnockbackScale=0.1, DeathAnimationTime=2.0)


# --- instance -----------------------------------------------------------------------------------

def biome(prefabs):
    doc = go.biome(INSTANCE, "unused")
    doc["Props"] = [{
        "Runtime": 0,
        "ContextPrecision": "Prop",
        "PropDistribution": {
            "Type": "Assigned",
            "OverrideAllProps": True,
            "PropDistribution": {"Type": "Positions", "Positions": {"Type": "List", "Positions": [
                {"X": 0, "Y": GROUND_Y, "Z": 0}]}},
            "Assignments": {"Type": "Constant", "Prop": {"Type": "Prefab", "WeightedPrefabPaths": [
                {"Path": f"{go.PREFABS}/{PREFAB_DIR}/{name}", "Weight": 1.0}]}},
        },
    } for name in prefabs]
    doc["TintProvider"] = {"Type": "Constant", "Color": "#62a83e"}
    return doc


def weather():
    """Matinée claire sur la Falaise : ciel bleu, soleil chaud, brume lavande des Brumes au loin seulement."""
    hours = lambda pairs: [{"Hour": h, "Color": c} for h, c in pairs]
    return {
        "FogDistance": [40, 360],
        "FogColors": hours([(0, "#b8b4e0"), (12, "#c8c4ec")]),
        "FogDensities": [{"Hour": 0, "Value": 0.25}, {"Hour": 12, "Value": 0.25}],
        "SkyTopColors": hours([(0, "#3a6ad0ff"), (12, "#3a6ad0ff")]),
        "SkyBottomColors": hours([(0, "#a8c8f0ff"), (12, "#a8c8f0ff")]),
        "SkySunsetColors": hours([(0, "#00000000"), (12, "#00000000")]),
        "SunlightColors": hours([(0, "#fff0d8"), (12, "#fff4e0")]),
        "SunColors": hours([(0, "#fff8e0"), (12, "#fff8e0")]),
        "MoonColors": hours([(0, "#e0e8ffff"), (12, "#e0e8ffff")]),
        "MoonGlowColors": hours([(0, "#7aa0ff60"), (12, "#7aa0ff60")]),
        "WaterTints": hours([(0, "#3a7ac0"), (12, "#3a7ac0")]),
    }


# --- langues -------------------------------------------------------------------------------------

def lang():
    fr_, en = {}, {}

    def put(key, f, e):
        fr_[key], en[key] = f, e

    def item(item_id, nf, df, ne, de):
        put(f"items.{item_id}.name", nf, ne)
        put(f"items.{item_id}.description", df, de)

    item(HAMMER, "Marteau du culte",
         "Seule arme capable de briser les sceaux du colosse. Le recevoir coûte 10 % des PV. Tenu en main, il corrompt : "
         "toutes les 10 s, la Corruption monte d'un cran (dégâts subis en hausse, faiblesse, étourdissement, puis il "
         "vous échappe) ; rangé, elle redescend d'un cran. Frapper un cultiste avec, ou voir mourir un cultiste qu'on a "
         "frappé, le charge : un coup chargé fissure un sceau.",
         "Cult Hammer",
         "The only weapon that can break the colossus' seals. Receiving it costs 10% HP. Held in hand, it corrupts: every "
         "10 s, Corruption rises one tier (more damage taken, weakness, stun, then you drop it); put away, it falls one "
         "tier. Hitting a cultist with it, or seeing a cultist you hit die, charges it: a charged blow cracks a seal.")
    item(SEAL_STONE, "Pierre de sceau", "Pierre gravée du culte, sous le sceau du cou.", "Seal stone",
         "Carved cult stone, under the neck seal.")
    item(MIST_BARRIER, "Barrière de brume", "Se dissipe quand les sceaux qui la tiennent sont brisés.", "Mist barrier",
         "Fades when the seals holding it are broken.")
    item(LANDING, "Plate-forme sûre", "Une chute ramène à la dernière plate-forme sûre où l'on s'est tenu.",
         "Safe platform", "A fall brings you back to the last safe platform you stood on.")
    item(PLATE, "Dalle du tunnel", "Certaines cachent des pointes.", "Tunnel slab", "Some of them hide spikes.")
    item(RACK_BLOCK, "Râtelier du culte", "Utiliser : prendre le marteau du culte (un seul à la fois).", "Cult rack",
         "Use: take the cult hammer (only one at a time).")
    item(GARGOYLE, "Gargouille", "Son souffle pousse dans le vide. Un levier en haut du saut la fait taire.",
         "Gargoyle", "Its breath pushes into the void. A lever at the top of the climb silences it.")
    item(LEVER, "Levier", "Utiliser : coupe un piège. Dur à tirer : on reste figé 4 s.", "Lever",
         "Use: shuts down a trap. Hard to pull: you are rooted for 4 s.")
    item(CAGE_DOOR, "Porte de cage", "Utiliser (5 fois) : forcer la porte et libérer le prisonnier.", "Cage door",
         "Use (5 times): force the door and free the prisoner.")
    for role_id, nf, ne in ((ROLE_FANATIC, "Fanatique du culte", "Cult Fanatic"),
                            (ROLE_CHANTER, "Incantateur du culte", "Cult Chanter"),
                            (ROLE_SEEKER, "Le Chercheur", "The Seeker"),
                            (ROLE_DEVOURER, "Dévoreur", "Devourer"),
                            (ROLE_SEAL, "Sceau du culte", "Cult Seal"),
                            (ROLE_BOSS, "L'Archidevin", "The Archdiviner")):
        put(f"npc.{role_id.removeprefix('Nakasar_Fractal_')}.name", nf, ne)
    for tier, *_ in CORRUPTION_TIERS:
        put(f"effects.{CORRUPTION}_{tier}", f"Corruption {tier}", f"Corruption {tier}")
    put("hints.takeHammer", "Ramasser le marteau", "Pick up the hammer")
    put("effects.Nakasar_Fractal_Lever_Rooted", "Levier tiré", "Pulling a lever")
    put("effects.Nakasar_Fractal_Archdiviner_Haste", "Hâte", "Haste")
    put("effects.Nakasar_Fractal_Archdiviner_Protection", "Protection", "Protection")
    put("effects.Nakasar_Fractal_Archdiviner_Demon", "Forme démoniaque", "Demon form")
    # Messages du Java (dev.nakasar.hytale.fractals.cliffside, hammer, defiance).
    msgs = {
        "camp.intro": ("Le Chercheur : « Les cultistes gardent leur marteau. Lui seul brise les sceaux qui enchaînent "
                       "le colosse. »", "The Seeker: \"The cultists guard their hammer. Only it can break the seals "
                                        "chaining the colossus.\""),
        "camp.guarded": ("Des cultistes gardent encore le râtelier.", "Cultists still guard the rack."),
        "hammer.taken": ("Le marteau du culte vous brûle les mains (10 % de vos PV).",
                         "The cult hammer burns your hands (10% of your HP)."),
        "hammer.already": ("Le marteau est déjà entre les mains de {name}.", "{name} already holds the hammer."),
        "hammer.have": ("Vous avez déjà le marteau.", "You already have the hammer."),
        "hammer.charged": ("Marteau chargé : frappez un sceau !", "Hammer charged: strike a seal!"),
        "hammer.stun": ("Cran 3 : la Corruption vous submerge un instant. Rangez le marteau !",
                        "Tier 3: Corruption overwhelms you for a moment. Put the hammer away!"),
        "hammer.dropped": ("Trop de Corruption : le marteau vous échappe.", "Too much Corruption: the hammer slips away."),
        "hammer.up": ("La Corruption monte : cran {tier}. Rangez le marteau pour la faire redescendre.",
                      "Corruption rises: tier {tier}. Put the hammer away to let it fall."),
        "hammer.down": ("La Corruption redescend : cran {tier}.", "Corruption falls: tier {tier}."),
        "hammer.cleansed": ("La Corruption se dissipe.", "The Corruption fades."),
        "hammer.removed": ("Le marteau du culte se dissipe hors de la Falaise.", "The cult hammer fades outside the Cliffside."),
        "seal.needHammer": ("Seul le marteau du culte, chargé, fissure ce sceau.",
                            "Only the charged cult hammer can crack this seal."),
        "seal.needCharge": ("Le marteau n'est pas chargé : frappez un cultiste avec.",
                            "The hammer is not charged: hit a cultist with it."),
        "seal.shielded": ("Une bulle protège ce sceau : frappez l'autre.", "A bubble shields this seal: strike the other one."),
        "seal.cracked": ("Sceau fissuré ({left} coup(s) encore).", "Seal cracked ({left} more blow(s))."),
        "seal.mended": ("Un incantateur répare le sceau !", "A chanter mends the seal!"),
        "seal.broken": ("Sceau brisé ({count}/5)", "Seal broken ({count}/5)"),
        "gate.open": ("La barrière de brume se dissipe.", "The mist barrier fades."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "lever.gargoyles": ("Les gargouilles de ce palier se taisent.", "The gargoyles of this tier fall silent."),
        "lever.bombs": ("Les bombes de cette rampe s'arrêtent.", "The bombs on this ramp stop."),
        "lever.done": ("Ce levier est déjà tiré.", "This lever is already pulled."),
        "cage.pried": ("La porte cède un peu ({left}).", "The door gives a little ({left})."),
        "cage.open": ("La cage s'ouvre !", "The cage opens!"),
        "cage.jailed": ("L'Archidevin vous jette en cage : vos alliés peuvent forcer la porte.",
                        "The Archdiviner cages you: your allies can force the door."),
        "cage.self": ("La porte ne s'ouvre pas de l'intérieur.", "The door does not open from the inside."),
        "cage.empty": ("Cette cage est vide.", "This cage is empty."),
        "landing.back": ("Rattrapé par les Brumes : retour à la dernière plate-forme sûre.",
                         "Caught by the Mists: back to the last safe platform."),
        "boss.transition": ("L'Archidevin se protège et puise dans le sceau du cou : brisez-le au marteau !",
                            "The Archdiviner shields himself and draws on the neck seal: break it with the hammer!"),
        "boss.transitionEnd": ("Le sceau du cou se fissure : l'Archidevin vacille.", "The neck seal cracks: the Archdiviner staggers."),
        "boss.final": ("L'Archidevin est à genoux : un dernier coup de marteau sur le sceau du cou !",
                       "The Archdiviner is on his knees: one last hammer blow on the neck seal!"),
        "boss.victory": ("Le colosse est libéré.", "The colossus is free."),
        "boss.reset": ("L'Archidevin reprend des forces.", "The Archdiviner regains his strength."),
        "defiance.broken": ("Défiance brisée !", "Defiance broken!"),
        "title.seal": ("Sceau brisé", "Seal broken"),
        "title.victory": ("Falaise terminée", "Cliffside complete"),
    }
    for k, (f, e) in msgs.items():
        put(k, f, e)
    put("bossbar.defiance", "Défiance", "Defiance")
    return fr_, en


# --- Java ---------------------------------------------------------------------------------------

def jd(v):
    return f"{float(v)}"


def world(at):
    return (at[0], GROUND_Y + at[1], at[2])


def java_point(at, center=True):
    x, y, z = world(at)
    if center and float(x).is_integer():
        x += 0.5
    if center and float(z).is_integer():
        z += 0.5
    return "{" + f"{jd(x)}, {jd(y)}, {jd(z)}" + "}"


def java_layout():
    landings, stones = puzzle_layout()
    g = gargoyles()
    rows = lambda items: ",\n".join("            " + s for s in items)
    garg = rows(f"new Gargoyle({x}, {GROUND_Y + y}, {z}, {d['group']}, {d['offset']}f)"
                for d in g for (x, y, z) in [d["at"]])
    pl = rows(f"new Plate({x}, {z}, {str(real).lower()})" for x, z, real in plates())
    cg = rows(f"new Cage({x}, {z}, {dx}, {dz})" for x, z, (dx, dz) in cages())
    zones = rows("new Box(" + ", ".join(str(v) for v in (x0, x1, GROUND_Y + y0, GROUND_Y + y1, z0, z1)) + ")"
                 for x0, x1, y0, y1, z0, z1 in JUMP_ZONES)

    def pts(points, y):
        return ", ".join("{" + f"{jd(x + 0.5)}, {jd(GROUND_Y + y)}, {jd(z + 0.5)}" + "}" for x, z in points)

    def blocks_of(cells):
        return ", ".join("{" + f"{x}, {GROUND_Y + y}, {z}" + "}" for x, y, z in cells)

    def box(b, stand):
        x0, x1, z0, z1 = b
        return f"new Box({x0}, {x1}, {GROUND_Y + stand - 1}, {GROUND_Y + stand + 3}, {z0}, {z1})"

    ramp1 = [(x, z, lv) for x, z, lv in ramp_cells(R1) if z == R1[2] + 1]
    ramp2 = [(x, z, lv) for x, z, lv in ramp_cells(R2) if z == R2[2] + 1]
    ramp_rows = lambda cells: ", ".join("{" + f"{jd(x + 0.5)}, {jd(GROUND_Y + lv)}, {jd(z + 0.5)}" + "}"
                                        for x, z, lv in reversed(cells))
    return f"""package dev.nakasar.hytale.fractals.cliffside;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions de la Falaise, écrites par tools/generate_cliffside.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud ; y monde (le plateau du camp est debout à {GROUND_Y}).
 * Les points {{x, y, z}} sont des pieds (centre du bloc) ; les blocs {{x, y, z}} des coins de bloc.
 */
public final class CliffsideLayout {{

    public static final int GROUND_Y = {GROUND_Y};
    /** Hauteurs (debout) : passerelle des genoux, du torse, épaules, arène. */
    public static final int KNEES = {GROUND_Y + KNEES};
    public static final int CHEST = {GROUND_Y + CHEST};
    public static final int SHOULDERS = {GROUND_Y + SHOULDERS};
    public static final int ARENA = {GROUND_Y + ARENA};

    public static final double[] SPAWN = {java_point(SPAWN)};
    public static final double[] CAMP = {java_point((CAMP_CENTER[0], 0, CAMP_CENTER[1]))};
    public static final double[] SEEKER = {{{jd(SEEKER[0])}, {jd(GROUND_Y + SEEKER[1])}, {jd(SEEKER[2])}}};
    public static final double[][] CAMP_WAVE = {{{pts(CAMP_WAVE, 0)}}};

    /** Points de retour (pieds) : passerelle des genoux, du torse, épaules, palier de l'arène. */
    public static final double[] CHECKPOINT_KNEES = {java_point((1, KNEES, -36))};
    public static final double[] CHECKPOINT_CHEST = {java_point((0, CHEST, -34))};
    public static final double[] CHECKPOINT_SHOULDERS = {java_point((0, SHOULDERS, -46))};
    public static final double[] CHECKPOINT_ARENA = {java_point((-16, ARENA, -32))};

    /** Zones où l'on déclenche une étape (pieds dedans). */
    public static final Box KNEES_DECK = {box(D1, KNEES)};
    public static final Box CHEST_DECK = {box(D2, CHEST)};
    public static final Box SHOULDERS_TOP = new Box(-52, 52, {GROUND_Y + SHOULDERS - 1}, {GROUND_Y + SHOULDERS + 3}, -56, -44);

    /** Sceaux (pieds du PNJ) : genou ouest, genou est, poitrine, poignet ouest, poignet est, cou. */
    public static final double[][] SEALS = {{{java_point(KNEE_SEALS[0], False)}, {java_point(KNEE_SEALS[1], False)}, {java_point(CHEST_SEAL, False)},
            {java_point(WRIST_SEALS[0], False)}, {java_point(WRIST_SEALS[1], False)}, {java_point(NECK_SEAL, False)}}};
    /** Points d'apparition des vagues, par sceau (mêmes index que {{@link #SEALS}}, le cou n'en a pas). */
    public static final double[][][] WAVES = {{
            {{{pts(KNEE_WAVES[0], KNEES)}}},
            {{{pts(KNEE_WAVES[1], KNEES)}}},
            {{{pts(CHEST_WAVES, CHEST)}}},
            {{{pts(WRIST_WAVES[0], SHOULDERS)}}},
            {{{pts(WRIST_WAVES[1], SHOULDERS)}}}}};

    /** Barrières de brume (blocs) : G1 après les genoux, G2 au pied de l'escalier du torse, G3 avant les rampes. */
    public static final int[][] GATE1 = {{{blocks_of(GATE1)}}};
    public static final int[][] GATE2 = {{{blocks_of(GATE2)}}};
    public static final int[][] GATE3 = {{{blocks_of(GATE3)}}};

    /** Tunnel : plaques (x, z) au sol en y = {GROUND_Y + KNEES - 1}, piégées ou non. */
    public static final int PLATE_Y = {GROUND_Y + KNEES - 1};
    public static final List<Plate> PLATES = List.of(
{pl});

    /** Gargouilles (bloc de la statue), groupe (levier) et décalage de cycle (s). Souffle vers +z sur {GUST_REACH} blocs. */
    public static final int GUST_REACH = {GUST_REACH};
    public static final List<Gargoyle> GARGOYLES = List.of(
{garg});
    /** Leviers (blocs) : trois du saut (un par groupe de gargouilles), puis R1 et R2. */
    public static final int[][] LEVERS = {{{blocks_of(LEVERS_TOP + RAMP_LEVERS)}}};
    public static final int GARGOYLE_LEVERS = {len(LEVERS_TOP)};

    /** Zones de saut : une chute à plus de 4 blocs sous la dernière plate-forme sûre y ramène. */
    public static final List<Box> JUMP_ZONES = List.of(
{zones});

    /** Foyers de la passerelle du torse (centre, pieds) et leur rayon. */
    public static final double[][] FIRES = {{{pts(FIRES, CHEST)}}};
    public static final double FIRE_RADIUS = {FIRE_RADIUS};

    /** Rampes : cases du haut vers le bas, au milieu de la rampe (pieds) ; les bombes les descendent. */
    public static final double[][][] RAMPS = {{
            {{{ramp_rows(ramp1)}}},
            {{{ramp_rows(ramp2)}}}}};

    /** Arène de l'Archidevin. */
    public static final double[] ARENA_CENTER = {java_point((ARENA_CENTER[0], ARENA, ARENA_CENTER[1]))};
    public static final double ARENA_RADIUS = {ARENA_RADIUS};
    public static final double[] BOSS_SPAWN = {java_point(BOSS_SPAWN, False)};
    public static final int[] REWARD = {{{REWARD_AT[0]}, {GROUND_Y + REWARD_AT[1]}, {REWARD_AT[2]}}};
    public static final int[] END_EXIT = {{{END_EXIT_AT[0]}, {GROUND_Y + END_EXIT_AT[1]}, {END_EXIT_AT[2]}}};
    /** Cages : bloc de cage aux pieds (x, z, y = {{@link #ARENA}}) et côté de la porte (dx, dz). */
    public static final List<Cage> CAGES = List.of(
{cg});

    private CliffsideLayout() {{
    }}

    public record Plate(int x, int z, boolean trapped) {{
    }}

    public record Gargoyle(int x, int y, int z, int group, float offset) {{
    }}

    public record Cage(int x, int z, int doorX, int doorZ) {{
    }}
}}
"""


# --- écriture -----------------------------------------------------------------------------------

def write_json(path, doc):
    fr.write_json(path, doc)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    (COMMON / go.TEXTURES).mkdir(parents=True, exist_ok=True)
    (COMMON / go.ICONS).mkdir(parents=True, exist_ok=True)

    # L'ébauche de l'étape 2 est remplacée.
    stub = SERVER / "Prefabs" / go.PREFABS / "Cliffside_Stub"
    if stub.exists():
        for f in stub.iterdir():
            f.unlink()
        stub.rmdir()

    for name, tex, base, accent, glyph, light, use, solid in blocks():
        img = texture(COMMON / go.TEXTURES / f"{tex}.png", base, accent, glyph)
        go.icon(COMMON / go.ICONS / f"{tex}.png", img)
        doc = go.block_item(name, tex, light, use, solid=solid, particle=go.hexcolor(accent))
        doc["TranslationProperties"] = {"Name": f"{LANG}.items.{name}.name", "Description": f"{LANG}.items.{name}.description"}
        block_models.apply(doc, tex)
        write_json(ITEMS / f"{name}.json", doc)
    write_json(SERVER / "Item/Items/Weapon/Nakasar/Fractals" / f"{HAMMER}.json", hammer_item())

    for name, doc in effects().items():
        write_json(EFFECTS / f"{name}.json", doc)
    for tier, top, _ in CORRUPTION_TIERS:
        status_icon(COMMON / STATUS_ICONS / f"Corruption_{tier}.png", tuple(int(top[i:i + 2], 16) for i in (1, 3, 5)), "corruption")
    status_icon(COMMON / STATUS_ICONS / "Rooted.png", (150, 200, 120), "rooted")
    status_icon(COMMON / STATUS_ICONS / "Haste.png", (255, 154, 74), "haste")
    status_icon(COMMON / STATUS_ICONS / "Protection.png", (200, 170, 255), "shield")
    status_icon(COMMON / STATUS_ICONS / "Demon.png", (220, 40, 60), "demon")
    write_json(SERVER / "Entity/Damage" / f"{CORRUPTION}.json", corruption_cause())
    write_json(SERVER / "Entity/Damage" / "Nakasar_Fractal_Spikes.json", spikes_cause())
    for name, doc in particle_files().items():
        write_json(PARTICLES / name, doc)

    for name, doc in interactions().items():
        write_json(INTERACTIONS / f"{name}.json", doc)
    for name, doc in roots().items():
        write_json(ROOTS / f"{name}.json", doc)

    write_json(MODELS / f"{ROLE_FANATIC}.json", fanatic_model())
    write_json(MODELS / f"{ROLE_CHANTER}.json", chanter_model())
    write_json(MODELS / f"{ROLE_SEEKER}.json", seeker_model())
    write_json(MODELS / f"{ROLE_BOSS}.json", boss_model())
    write_json(MODELS / f"{ROLE_DEVOURER}.json", devourer_model())
    write_json(MODELS / f"{ROLE_SEAL}.json", write_seal_model())
    write_json(ROLES / f"{ROLE_FANATIC}.json", fanatic_role())
    write_json(ROLES / f"{ROLE_CHANTER}.json", chanter_role())
    write_json(ROLES / f"{ROLE_DEVOURER}.json", devourer_role())
    write_json(ROLES / f"{ROLE_SEAL}.json", seal_role())
    write_json(ROLES / f"{ROLE_SEEKER}.json", seeker_role())
    write_json(ROLES / f"{ROLE_BOSS}.json", boss_role())
    group = SERVER / "NPC/Groups" / f"{fr.FOES}.json"
    doc = json.loads(group.read_text(encoding="utf-8"))
    doc["IncludeRoles"] = sorted(set(doc.get("IncludeRoles", [])) | set(FOE_ROLES))
    write_json(group, doc)

    course = course_prefab()
    prefabs = {"Cliff": cliff_prefab(), "Colossus": colossus_prefab(set(course.blocks)), "Course": course}
    counts = {}
    for name, p in prefabs.items():
        counts[name] = p.write(SERVER / "Prefabs" / go.PREFABS / PREFAB_DIR / name / f"{name}.prefab.json")
    write_json(SERVER / "Instances" / INSTANCE / "instance.bson",
               go.instance(INSTANCE, "Falaise", INSTANCE, portal=False, spawn=(SPAWN[0], GROUND_Y + SPAWN[1], SPAWN[2]),
                           removal=60, weather=WEATHER, time="10:30"))
    write_json(SERVER / "Weathers" / f"{WEATHER}.json", weather())
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{INSTANCE}.json", biome(list(prefabs)))
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{INSTANCE}.json",
               go.world_structure(INSTANCE, (SPAWN[0], GROUND_Y + SPAWN[1], SPAWN[2])))

    fr_, en = lang()
    go.write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr_)
    go.write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print("Falaise : " + ", ".join(f"{k} {v} blocs" for k, v in counts.items()) +
          f" ; genoux {KNEES}, torse {CHEST}, épaules {SHOULDERS}, arène {ARENA}")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        side_view(prefabs, preview / "falaise_face.png")
        top_view(prefabs, preview / "falaise_dessus.png")


def color_of(name):
    if name in (LANDING,):
        return (120, 200, 255)
    if name in (MIST_BARRIER, SEAL_STONE, "Rock_Crystal_Purple_Block"):
        return (190, 110, 255)
    if name == PLATE:
        return (230, 120, 90)
    if name == GARGOYLE:
        return (255, 255, 255)
    if name.startswith("Plant_Flower"):
        return {"Yellow": (240, 220, 60), "White": (240, 240, 240), "Blue": (90, 130, 240), "Purple": (170, 90, 220),
                "Violet": (150, 80, 220), "Pink": (240, 140, 190), "Red": (220, 50, 50), "Orange": (240, 150, 50)}.get(
            next((c for c in ("Yellow", "White", "Blue", "Purple", "Violet", "Pink", "Red", "Orange") if c in name), ""),
            (230, 230, 120))
    if name.startswith("Plant_Leaves"):
        return (40, 100, 40) if ("Fir" in name or "Cedar" in name) else (60, 130, 50)
    if name.startswith(("Plant_Grass", "Plant_Bush", "Plant_Fern")):
        return (100, 170, 70)
    if name.startswith(("Plant_Vine", "Plant_Moss")) or name.endswith("_Mossy"):
        return (70, 120, 60)
    if name.endswith("_Trunk"):
        return (110, 80, 50)
    if name.startswith("Wood_"):
        return (150, 100, 60)
    if name.startswith("Soil_Grass"):
        return (80, 140, 60)
    if name.startswith(("Soil_Pathway", "Soil_Dirt", "Soil_Clay")):
        return (150, 115, 75)
    if name.startswith("Soil_Gravel"):
        return (120, 120, 105)
    if "Slate" in name:
        return (95, 100, 110)
    if "Shale" in name:
        return (120, 110, 100)
    if "Basalt" in name:
        return (70, 70, 80)
    return (130, 130, 130)


def side_view(prefabs, path):
    """Vue de face (depuis le sud), le bloc le plus au sud de chaque colonne (x, y), 3 pixels par bloc."""
    best = {}
    for p in prefabs.values():
        for (x, y, z), (name, _) in p.blocks.items():
            if name == AIR:
                continue
            if (x, y) not in best or z > best[(x, y)][0]:
                best[(x, y)] = (z, name)
    xs = [k[0] for k in best]
    ys = [k[1] for k in best]
    s = 3
    img = Image.new("RGB", ((max(xs) - min(xs) + 1) * s, (max(ys) - min(ys) + 1) * s), (12, 14, 34))
    d = ImageDraw.Draw(img)
    for (x, y), (z, name) in best.items():
        c = color_of(name)
        shade = max(0.35, min(1.0, 0.45 + (z + 60) / 90))
        c = tuple(int(v * shade) for v in c)
        px, py = (x - min(xs)) * s, (max(ys) - y) * s
        d.rectangle((px, py, px + s - 1, py + s - 1), fill=c)
    img.save(path)


def top_view(prefabs, path):
    best = {}
    for p in prefabs.values():
        for (x, y, z), (name, _) in p.blocks.items():
            if name == AIR:
                continue
            if (x, z) not in best or y > best[(x, z)][0]:
                best[(x, z)] = (y, name)
    xs = [k[0] for k in best]
    zs = [k[1] for k in best]
    s = 4
    img = Image.new("RGB", ((max(xs) - min(xs) + 1) * s, (max(zs) - min(zs) + 1) * s), (12, 14, 34))
    d = ImageDraw.Draw(img)
    for (x, z), (y, name) in best.items():
        c = color_of(name)
        shade = max(0.3, min(1.0, 0.3 + y / 110))
        c = tuple(int(v * shade) for v in c)
        px, pz = (x - min(xs)) * s, (z - min(zs)) * s
        d.rectangle((px, pz, px + s - 1, pz + s - 1), fill=c)
    img.save(path)


if __name__ == "__main__":
    main()
