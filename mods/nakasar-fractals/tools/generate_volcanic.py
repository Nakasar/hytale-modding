#!/usr/bin/env python3
"""Génère le Volcanique (Volcanic), troisième fractale de la saison 1 (étape 6 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_volcanic.py [--preview DOSSIER]

Le déroulé de GW2, dans l'ordre :

1. le camp des grawls : des vagues de grawls autour du totem du rituel (sa vie montre ce qu'il reste à abattre), des
   rochers qui tombent du volcan (cercles rouges) ;
2. le couloir aux rochers : des rochers en feu dévalent toutes les 5 s, on s'abrite dans les niches ; un rocher coûte
   60 % des PV, brûle et laisse une traînée de feu ;
3. le Champion chaman des grawls : huit charges de protection que seules les pierres imprégnées (lâchées par les
   rochers qui tombent) retirent ; ses vétérans marchent vers les quatre captifs au bord de la lave ;
4. la mine : des rails sur des planches au-dessus de la lave, des chauves-souris ; une chute ramène au départ du
   tronçon ;
5. le Chamane imprégné : pieds brûlants (rester immobile ou sauter brûle), puits de lave silencieux, flèche
   enflammée qui se propage, piqué, souffle des ailes, tempête de feu ; à chaque quart de sa vie, un bouclier de 40
   coups, des larves de braise, et il plane vers un villageois pour s'en nourrir.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Volcanic`, la pierre imprégnée
(clic droit : la lancer), les effets, la cause de dégâts du feu, les particules, les modèles et rôles, la langue
`nakasar_fractals_volcanic.lang` et `volcanic/VolcanicLayout.java`. Repère comme la Falaise : y monde = GROUND_Y + y
prefab, « debout à y » : le sol est en y - 1.
"""
import math
import sys
from pathlib import Path

import fractal_common as fc
import fractal_models as fm
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

LANG = "nakasar_fractals_volcanic"
GENERATOR = "generate_volcanic.py"
INSTANCE = "Nakasar_Fractal_Volcanic"
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
CAPTIVE_ANGLES = [45, 135, 225, 315]
CAPTIVE_RADIUS = 12
VETERAN_GATES = [(-34, -81), (-34, -107)]
GATE_CH = [(-49, y, z) for y in range(0, 5) for z in range(-96, -91)]
MINE = (-118, -50)                      # x de fin (ouest) et de départ (est) de la mine
MINE_Z = (-96, -92)
LAVA_Y = -7
END_PAD = (-124, -116, -98, -90)        # x0, x1, z0, z1, debout à 2
AR_CENTER = (-140, -94)
AR_RADIUS = 16
AR_STAND = 2
VILLAGER_ANGLES = [30, 150, 210, 330]
VILLAGER_RADIUS = 14
REWARD_AT = (-142, AR_STAND, -94)
END_EXIT_AT = (-138, AR_STAND, -94)
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


def ring_point(center, radius, angle, rounded=True):
    x = center[0] + math.cos(math.radians(angle)) * radius
    z = center[1] + math.sin(math.radians(angle)) * radius
    return (round(x), round(z)) if rounded else (round(x, 1), round(z, 1))


def mine_segments():
    """Tronçons de rails de la mine : (x0, x1, debout), d'est en ouest ; trous de 2 à 3 blocs entre eux."""
    out, x, k = [], MINE[1], 0
    levels = [0, 1, 1, 2, 1, 2, 3, 2, 2, 3, 2, 2]
    while x > MINE[0] + 2:
        length = 5 if k % 3 else 4
        out.append((x - length + 1, x, levels[k % len(levels)]))
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
    chx, chz = CH_CENTER
    fc.disc(p, chx, chz, CH_RADIUS, 0, lambda x, z: pick(GROUND, x, 0, z), ROCK, 8)
    for a in range(0, 360, 6):
        x, z = ring_point(CH_CENTER, CH_RADIUS + 1, a)
        if abs(z - chz) <= 3:
            continue
        for y in range(-1, 4):
            p.set(x, y, z, pick(ROCK, x, y, z))
    for a in CAPTIVE_ANGLES:   # ledges des captifs, au bord de la lave
        x, z = ring_point(CH_CENTER, CAPTIVE_RADIUS, a)
        p.set(x, -1, z, "Rock_Magma_Cooled")
        p.set(x + (1 if x > chx else -1), 0, z, "Deco_Trork_Cage")
        x2, z2 = ring_point(CH_CENTER, CH_RADIUS + 1, a)
        for y in range(-1, 4):
            p.set(x2, y, z2, LAVA if y < 0 else go.AIR)
    for x, z in VETERAN_GATES:
        for dx in (-1, 0, 1):
            for y in range(0, 3):
                p.set(x + dx, y, z, go.AIR)
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
            p.set(x, AR_STAND - 1, z, LANDING if x >= ex1 - 2 else pick(GROUND, x, AR_STAND - 1, z))
            for y in range(LAVA_Y, AR_STAND - 1):
                p.set(x, y, z, pick(ROCK, x, y, z))
    p.set(ex1 - 1, AR_STAND, ez0, "Deco_Bone_Skulls")
    p.set(ex1 - 2, AR_STAND, ez0, "Deco_Bone_Pile")
    p.set(ex1, AR_STAND, ez0, "Furniture_Ancient_Crate")
    # Arène du Chamane imprégné.
    ax, az = AR_CENTER
    fc.disc(p, ax, az, AR_RADIUS, AR_STAND,
            lambda x, z: "Rock_Volcanic_Brick_Smooth" if abs(math.hypot(x - ax, z - az) - 8) < 0.5 else pick(GROUND, x, AR_STAND, z),
            ROCK, 10)
    for a in range(0, 360, 20):
        x, z = ring_point(AR_CENTER, AR_RADIUS - 1, a)
        if x > ax + 12 and abs(z - az) < 5:
            continue   # entrée est
        p.set(x, AR_STAND, z, "Rock_Volcanic_Brick_Pillar_Base")
        p.set(x, AR_STAND + 1, z, "Rock_Volcanic_Brick_Pillar_Middle")
        p.set(x, AR_STAND + 2, z, "Furniture_Crude_Brazier")
    for a in VILLAGER_ANGLES:
        x, z = ring_point(AR_CENTER, VILLAGER_RADIUS, a)
        p.set(x + (1 if x > ax else -1), AR_STAND, z, "Deco_Trork_Cage")
    return p


# --- objets, effets, particules -----------------------------------------------------------------------

def stone_parts():
    rock, glow = (90, 70, 60), (255, 150, 60)
    return [("Rock", (0, 4, 0), (7, 7, 6), 20, fm.smooth(rock), "flat"),
            ("Vein_A", (0, 4, 3.1), (5, 1, 1), 0, fm.crystal((160, 60, 20), glow), "fullbright"),
            ("Vein_B", (2.1, 5, 0), (1, 4, 1), 0, fm.crystal((160, 60, 20), glow), "fullbright")]


def stone_item():
    root = "Root_Nakasar_Fractal_Throw_Imbued_Stone"
    return fc.held_item(LANG, STONE, "Imbued_Stone", stone_parts(), 41, (0, 4, 0), 16.0, quality="Epic", stack=4,
                        extra={"Interactions": {"Secondary": root}, "Categories": ["Items.Misc"]})


def throw_interaction():
    return {"$Comment": "Pierre imprégnée : clic droit, la lancer sur le Champion chaman visé (24 blocs, cône de 30°) ; "
                        "elle lui retire une charge de protection (Java, volcanic.Champion).",
            "Type": "Nakasar_Fractal_ThrowItem", "Item": STONE, "Roles": CHAMPION, "Range": 24, "Cone": 30,
            "Particle": "Nakasar_Fractal_Imbued_Trail", "Action": "ImbuedStone",
            "NoTargetMessage": f"{LANG}.stone.noTarget"}


def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Burning_Feet": fc.effect(
            L, "Nakasar_Fractal_Burning_Feet", "Pieds brûlants (Chamane imprégné) : immobile plus d'une seconde, ou en "
            "l'air, le sol brûle (Java, volcanic.ImbuedShaman).", "Burning_Feet", 1.5, debuff=True,
            ApplicationEffects={"EntityBottomTint": "#ff6a1a"}),
        "Nakasar_Fractal_Spreading_Flame": fc.effect(
            L, "Nakasar_Fractal_Spreading_Flame", "Flèche enflammée du Chamane imprégné : brûle et passe aux joueurs "
            "à moins de 2,5 blocs (Java).", "Spreading_Flame", 6, debuff=True,
            ApplicationEffects={"EntityTopTint": "#ff8a2a", "EntityBottomTint": "#5a1000"}),
    }


def fire_cause():
    return fc.cause("Feu du Volcanique (rochers, traînées, puits de lave, pieds brûlants, flamme qui se propage) : une "
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
        WARRIOR, "Guerrier grawl (vagues du camp) : deux coups, et un coup abattu annoncé.", WARRIOR, n(WARRIOR), 90,
        [fr.timed_attack("Slam", R("Grawl_Slam"), rng=2.8, los=True, comment="Coup abattu annoncé."),
         fr.melee(R("Grawl_Strike"), 2.4, (0.6, 1.0)), fr.chase(36, stop=1.6)],
        fr.walk(4.4), GENERATOR, sight=24, leash=40, home=False,
        timers=[fr.timer("Slam", (3, 5), (8, 11))], HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.9,
        DeathAnimationTime=1.0)
    out[GRAWL_SHAMAN] = fr.role(
        GRAWL_SHAMAN, "Chaman grawl : garde ses distances, feu annoncé sous sa cible.", GRAWL_SHAMAN, n(GRAWL_SHAMAN), 70,
        [fr.cast("Fire", R("Grawl_Shaman_Fire"), 16, "Feu annoncé."),
         fr.melee(R("Grawl_Shaman_Staff"), 2.0, (0.9, 1.3)), fr.keep_distance(36, 6, 10)],
        fr.walk(3.8), GENERATOR, sight=24, leash=40, home=False,
        timers=[fr.timer("Fire", (1, 3), (5, 7))], HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=1.0,
        DeathAnimationTime=1.0)
    out[TOTEM] = fc.static_role(LANG, TOTEM, "Totem du rituel grawl : les coups ne lui font rien ; sa vie montre les "
                                "grawls qu'il reste à abattre (Java). Barre de boss.", GENERATOR, 1000)
    vet = fr.role(
        VETERAN, "Vétéran grawl (Champion chaman) : part de sa grotte et marche vers un captif (point d'attache posé "
        "par le Java) ; il ne se bat que si on le frappe, ou une fois arrivé. À côté du captif 1,5 s, il le jette dans "
        "la lave.", VETERAN, n(VETERAN), 160,
        [fr.timed_attack("Slam", R("Grawl_Slam"), rng=2.8, los=True, comment="Coup abattu annoncé."),
         fr.melee(R("Grawl_Strike"), 2.4, (0.6, 1.0)), fr.chase(24, stop=1.6)],
        fr.walk(3.2), GENERATOR, sight=4, leash=14, home=True,
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
        "souffle des ailes, tempête de feu. Les pieds brûlants, les puits de lave, les boucliers, les larves et le vol "
        "vers les villageois sont menés par le Java (volcanic.ImbuedShaman).", IMBUED, n(IMBUED), 4000,
        [fr.timed_attack("Firestorm", R("Imbued_Firestorm"), rng=6, los=True, comment="Tempête de feu."),
         fr.timed_attack("Wings", R("Imbued_Wings"), rng=5.5, los=True, comment="Souffle des ailes."),
         fr.timed_attack("Dive", R("Imbued_Dive"), rng=20, los=True, comment="Piqué."),
         fr.timed_attack("Arrow", R("Imbued_Arrow"), rng=24, los=True, comment="Flèche enflammée."),
         fr.melee(R("Imbued_Staff"), 3.2, (0.9, 1.3)), fr.chase(34, stop=2.4)],
        fr.walk(3.6), GENERATOR, sight=22, leash=30, home=True,
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
    t.item(STONE, "Pierre imprégnée", "Clic droit en visant le Champion chaman : lui retire une charge de protection. "
           "Se dissipe hors du Volcanique.", "Imbued stone",
           "Right-click while aiming at the Champion shaman: removes one of his protection stacks. Fades outside the "
           "Volcanic fractal.")
    for role, f, e in ((WARRIOR, "Guerrier grawl", "Grawl warrior"), (GRAWL_SHAMAN, "Chaman grawl", "Grawl shaman"),
                       (TOTEM, "Totem du rituel", "Ritual totem"), (VETERAN, "Vétéran grawl", "Grawl veteran"),
                       (CHAMPION, "Champion chaman des grawls", "Champion grawl shaman"), (CAPTIVE, "Captif", "Captive"),
                       (BAT, "Chauve-souris de la mine", "Mine bat"), (IMBUED, "Le Chamane imprégné", "The Imbued Shaman"),
                       (LARVA, "Larve de braise", "Ember larva")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Burning_Feet", "Pieds brûlants", "Burning feet")
    t.put("effects.Nakasar_Fractal_Spreading_Flame", "Flamme qui se propage", "Spreading flame")
    msgs = {
        "intro": ("Volcanique : abattez les grawls du rituel ({count}), sous les rochers du volcan.",
                  "Volcanic: slay the grawls of the ritual ({count}), under the volcano's falling rocks."),
        "camp.done": ("Le totem du rituel s'effondre : la barrière se dissipe.", "The ritual totem collapses: the barrier fades."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "corridor.enter": ("Des rochers dévalent le couloir : abritez-vous dans les niches !",
                           "Boulders roll down the corridor: shelter in the alcoves!"),
        "boulder.hit": ("Écrasé par un rocher en feu !", "Crushed by a burning boulder!"),
        "champion.enter": ("Le Champion chaman est protégé : lancez-lui les pierres imprégnées (clic droit). Ne laissez "
                           "pas ses vétérans rejoindre les captifs !",
                           "The Champion shaman is protected: throw the imbued stones at him (right-click). Don't let his "
                           "veterans reach the captives!"),
        "champion.stack": ("Une charge de protection en moins ({count} restantes).", "One protection stack fewer ({count} left)."),
        "champion.shield": ("Le Champion se protège de nouveau !", "The Champion protects himself again!"),
        "champion.veterans": ("Des vétérans sortent des grottes et marchent vers les captifs !",
                              "Veterans leave the caves and march on the captives!"),
        "captive.lost": ("Un captif est jeté dans la lave ({count}/4 perdus).", "A captive is thrown into the lava ({count}/4 lost)."),
        "captive.allLost": ("Tous les captifs sont perdus : le Champion recommence son rituel.",
                            "All the captives are lost: the Champion starts his ritual again."),
        "champion.reset": ("Le Champion chaman reprend des forces.", "The Champion shaman regains his strength."),
        "champion.victory": ("Le Champion chaman tombe : la barrière se dissipe.", "The Champion shaman falls: the barrier fades."),
        "champion.bonus": ("Tous les captifs sont sauvés : ils vous remercient d'éclats de Brume.",
                           "Every captive is saved: they thank you with Mist shards."),
        "stone.noTarget": ("Visez le Champion chaman pour lancer la pierre.", "Aim at the Champion shaman to throw the stone."),
        "stone.drop": ("Un rocher se brise en laissant une pierre imprégnée.", "A rock shatters, leaving an imbued stone."),
        "mine.enter": ("La mine : sautez de rail en rail. Une chute ramène au départ.",
                       "The mine: jump from rail to rail. A fall brings you back to the start."),
        "landing.back": ("Rattrapé au-dessus de la lave : retour au départ de la mine.",
                         "Caught above the lava: back to the start of the mine."),
        "shaman.enter": ("Le Chamane imprégné ! Ne restez jamais immobile et ne sautez pas : le sol brûle.",
                         "The Imbued Shaman! Never stand still and don't jump: the ground burns."),
        "shaman.shield": ("Le Chamane se protège ({hits} coups) et plane vers un villageois : brisez le bouclier !",
                          "The Shaman shields himself ({hits} hits) and glides to a villager: break the shield!"),
        "shaman.broken": ("Bouclier brisé : le Chamane est étourdi.", "Shield broken: the Shaman is stunned."),
        "shaman.fed": ("Le Chamane se nourrit d'un villageois et reprend des forces.", "The Shaman feeds on a villager and regains strength."),
        "shaman.reset": ("Le Chamane imprégné reprend des forces.", "The Imbued Shaman regains his strength."),
        "shaman.victory": ("Le Chamane imprégné s'effondre dans la lave.", "The Imbued Shaman collapses into the lava."),
        "feet.burning": ("Pieds brûlants : bougez sans sauter !", "Burning feet: keep moving, don't jump!"),
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
    vgates = J.jpoints([(x, 0, z) for x, z in VETERAN_GATES])
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

    /** Arène du Champion chaman. */
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
    public static final Box END_PAD = {J.jbox(ex0, ex1, AR_STAND - 1, AR_STAND + 4, ez0, ez1)};
    public static final double[] END_CHECKPOINT = {J.jpoint((ex1 - 1, AR_STAND, -94))};

    /** Arène du Chamane imprégné. */
    public static final double[] ARENA_CENTER = {J.jpoint((AR_CENTER[0], AR_STAND, AR_CENTER[1]))};
    public static final double ARENA_RADIUS = {AR_RADIUS};
    public static final double[][] VILLAGERS = {villagers};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private VolcanicLayout() {{
    }}
}}
"""


def color_of(name):
    if name == LANDING:
        return (120, 200, 255)
    if name in (LAVA, "Rock_Magma_Cooled"):
        return (230, 90, 30)
    if name == MIST:
        return (230, 140, 220)
    if name.startswith("Wood_") or name == "Rail":
        return (150, 100, 60)
    if name.startswith("Soil_Ash"):
        return (110, 100, 96)
    return (70, 64, 66)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    fc.write_json(fc.OBJECTS / f"{STONE}.json", stone_item())
    fc.write_json(INTERACTIONS / "Nakasar_Fractal_Throw_Imbued_Stone.json", throw_interaction())
    fc.write_json(fc.ROOTS / "Root_Nakasar_Fractal_Throw_Imbued_Stone.json",
                  {"Interactions": ["Nakasar_Fractal_Throw_Imbued_Stone"], "RequireNewClick": True})
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Burning_Feet.png", (255, 120, 40), "feet")
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
    counts = fc.write_instance(INSTANCE, "Volcanique", PREFAB_DIR, sections, SPAWN, "#5a4440")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Volcanique : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules, {len(mine_segments())} tronçons de rails")
    if preview:
        fc.top_view(p, preview / "volcanique_dessus.png", color_of)


if __name__ == "__main__":
    main()
