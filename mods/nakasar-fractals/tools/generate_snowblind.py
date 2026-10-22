#!/usr/bin/env python3
"""Génère la Tempête de neige (Snowblind), sixième fractale de la saison 1 (étape 8 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_snowblind.py [--preview DOSSIER]

Une fractale d'environnement (wiki.guildwars2.com/wiki/Snowblind_Fractal) : le froid tue plus que les ennemis.
Loin d'un feu, chaque joueur cumule de l'Hypothermie (dégâts selon les piles, éclat de glace au maximum) ; près d'un
feu allumé, la Chaleur la fait redescendre. Dans l'ordre :

1. le mur de glace : allumer le grand feu de camp, qui fait fondre le mur bloquant la route, d'autant plus vite qu'il
   est bien nourri. Les fagots se ramassent sous les arbres du camp. Des élémentaires de glace courent éteindre le
   feu pendant que loups et cultistes du givre arrivent ;
2. la Source élémentaire : un géant de glace entouré de cinq foyers à allumer avec une torche (râtelier à l'entrée)
   et à nourrir avec les fagots des huttes. Chaque foyer éteint lui donne une pile de bouclier de givre. Orbe lent qui
   repousse, tourbillon. À 75, 50 et 25 %, il frappe les foyers (la moitié de leur bois). Tous éteints : blizzard ;
3. les traces : une forêt sombre, torche en main, en suivant les empreintes jusqu'au village ; deux embuscades ;
4. le Chaman légendaire : coups d'épée qui ajoutent de l'hypothermie, pluie de glace, anneau de pics, souffle glacé ;
   trois cristaux corrompus le protègent à chaque phase au contact. À 75 et 50 %, il saute sur le balcon et fait
   pleuvoir des pics tant que l'Effigie de glace tient ; à 25 %, il devient ours.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Snowblind`, le fagot et la
torche portés, les blocs (feu de camp, foyers, tas de fagots, râtelier, empreintes), les effets, les particules, les
modèles et rôles, la langue `nakasar_fractals_snowblind.lang` et `snowblind/SnowblindLayout.java`. Repère comme la
Falaise : y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_common as fc
import fractal_models as fm
import fractal_nature as fn
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go
import generate_swampland as gs
import generate_volcanic as gv

LANG = "nakasar_fractals_snowblind"
GENERATOR = "generate_snowblind.py"
INSTANCE = "Nakasar_Fractal_Snowblind"
WEATHER = "Nakasar_Fractal_Weather_Snowblind"
PREFAB_DIR = "Snowblind"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/snowblind/SnowblindLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/Snowblind"

# --- blocs, objets et rôles ------------------------------------------------------------------------------
FIREWOOD = "Nakasar_Fractal_Firewood"            # fagot porté
TORCH = "Nakasar_Fractal_Torch"                  # torche portée (lumière, ralentit l'hypothermie en main)
BONFIRE = "Nakasar_Fractal_Bonfire"
BONFIRE_OUT = "Nakasar_Fractal_Bonfire_Out"
BRAZIER = "Nakasar_Fractal_Frost_Brazier"
BRAZIER_OUT = "Nakasar_Fractal_Frost_Brazier_Out"
PILE = "Nakasar_Fractal_Firewood_Pile"
TORCH_RACK = "Nakasar_Fractal_Torch_Rack"
FOOTPRINTS = "Nakasar_Fractal_Footprints"
ICE = "Rock_Ice"
MIST = gc.MIST_BARRIER
ELEMENTAL = "Nakasar_Fractal_Ice_Elemental"
WOLF = "Nakasar_Fractal_Frost_Wolf"
CULTIST = "Nakasar_Fractal_Frost_Cultist"
ICE_CASTER = "Nakasar_Fractal_Frost_Caster"
SOURCE = "Nakasar_Fractal_Elemental_Source"
SHAMAN = "Nakasar_Fractal_Legendary_Shaman"
BEAR = "Nakasar_Fractal_Shaman_Bear"
EFFIGY = "Nakasar_Fractal_Ice_Effigy"
CRYSTAL = "Nakasar_Fractal_Corrupted_Crystal"
SHARD = "Nakasar_Fractal_Ice_Shard"
FOE_ROLES = [ELEMENTAL, WOLF, CULTIST, ICE_CASTER, SOURCE, SHAMAN, BEAR, EFFIGY, CRYSTAL, SHARD]
COLD_CAUSE = "Nakasar_Fractal_Cold"
FROST_CAUSE = "Nakasar_Fractal_Frost"
HYPOTHERMIA_TIERS = 5

THEME = fn.THEMES["snow"]
GROUND = ["Soil_Snow", "Soil_Snow", "Soil_Snow", "Rock_Ice_Permafrost"]
UNDER = ["Soil_Snow", "Soil_Dirt", "Rock_Ice_Permafrost"]
ROCK = ["Rock_Stone", "Rock_Slate", "Rock_Stone", "Rock_Ice_Permafrost"]
PLANK = "Wood_Fir_Trunk"
pick = fc.pick

# --- lieux (y = debout à) ---------------------------------------------------------------------------
SPAWN = (0, 0, 32)
CAMP = (0, 10)                          # centre de la clairière du camp
CAMP_RADIUS = 25
BONFIRE_AT = (0, 0, 6)
BONFIRE_HEAT = 7.0
FIREWOOD_SPOTS = [(-19, 2), (-17, -8), (-10, -13), (10, -13), (17, -8), (19, 2), (-20, 14), (20, 14)]
ELEMENTAL_SPAWNS = [(-23, 4), (-18, -9), (18, -9), (23, 4), (-22, 18), (22, 18)]
WAVE_SPAWNS = [(-20, -6), (20, -6), (-22, 12), (22, 12)]
ROAD = (-4, 4, -47, -14)                # x0, x1, z0 (nord), z1 (sud)
ICE_WALL = [(x, y, z) for x in range(-4, 5) for y in range(0, 7) for z in range(-27, -24)]
SOURCE_C = (0, -68)
SOURCE_RADIUS = 20
SOURCE_AT = (0, 0, -70)
BRAZIERS = [(round(SOURCE_C[0] + math.cos(math.radians(-90 + k * 72)) * 13),
             round(SOURCE_C[1] + math.sin(math.radians(-90 + k * 72)) * 13)) for k in range(5)]
BRAZIER_HEAT = 5.0
TORCH_RACK_AT = (5, 0, -50)
HUTS = [(-15, -56), (15, -56)]          # huttes et leurs tas de fagots
GATE_SOURCE = [(x, y, -89) for x in range(-2, 3) for y in range(0, 5)]
FOREST_Z = (-89, -156)                  # sentier dans la forêt, du sud au nord
VILLAGE_C = (0, -178)
VILLAGE_RADIUS = 20
VILLAGE_FIRES = [(-13, -172), (13, -172)]
BALCONY = (0, 7, -196)                  # le balcon du Chaman (debout à y = 7)
EFFIGY_AT = (0, 0, -180)
SHAMAN_AT = (0, 0, -184)
REWARD_AT = (-2, 0, -170)
END_EXIT_AT = (2, 0, -170)


def path_x(z):
    """Le sentier serpente dans la forêt (centre x selon z)."""
    return round(6 * math.sin((FOREST_Z[0] - z) / 11.0))


GATE_VILLAGE = [(path_x(-158) + dx, y, -158) for dx in range(-3, 4) for y in range(0, 5)]
# Remparts qui barrent toute l'île de part et d'autre des passages (sinon on contourne par la forêt du pourtour) :
# (rangées z, bloc, x laissés au passage).
BARRIERS = [((-27, -26, -25), ICE, range(-4, 5)), ((-89, -90), "Rock_Ice_Permafrost", range(-2, 3)),
            ((-158, -159), "Rock_Ice_Permafrost", range(path_x(-158) - 3, path_x(-158) + 4))]
BARRIER_HEIGHT = 10


def near_barrier(z, margin=5):
    return any(min(zs) - margin <= z <= max(zs) + margin for zs, _, _ in BARRIERS)
SPURS = [(-108, -1), (-130, 1)]         # fausses pistes : (z de départ, côté)
AMBUSHES = [(-110, [(path_x(-122) - 2, -122), (path_x(-122) + 2, -123), (path_x(-124), -125)]),
            (-136, [(path_x(-148) - 2, -148), (path_x(-148) + 2, -149), (path_x(-150), -151)])]


def footprints():
    """Empreintes au milieu du sentier, tous les trois blocs, en alternant gauche et droite."""
    out = []
    for k, z in enumerate(range(FOREST_Z[0] - 2, FOREST_Z[1], -3)):
        out.append((path_x(z) + (1 if k % 2 else -1) * 0, z))
    return out


FOOTPRINT_CELLS = footprints()


# --- prefab ----------------------------------------------------------------------------------------------

def ground(p, x, z, stand=0, depth=4):
    p.set(x, stand - 1, z, pick(GROUND, x, stand - 1, z))
    for y in range(stand - depth, stand - 1):
        p.set(x, y, z, pick(UNDER, x, y, z))


def hut(p, cx, cz, facing):
    """Hutte de rondins ouverte vers l'arène (`facing` +1 : vers l'est), toit de neige ; le tas de fagots devant."""
    for dz in range(-2, 3):
        for y in range(0, 3):
            p.set(cx - 2 * facing, y, cz + dz, PLANK)
    for dx in range(-2, 2):
        for y in range(0, 3):
            for z in (cz - 2, cz + 2):
                p.set(cx + dx * facing, y, z, PLANK)
    for dx in range(-3, 3):
        for dz in range(-3, 4):
            p.set(cx + dx * facing, 3, cz + dz, "Soil_Snow")
    p.set(cx, 0, cz, PILE)


def course_prefab():
    p = go.Prefab()
    # Camp : clairière de neige, grand feu au centre, route vers le nord bouchée par le mur de glace.
    cx, cz = CAMP
    fc.disc(p, cx, cz, CAMP_RADIUS, 0, lambda x, z: pick(GROUND, x, -1, z), UNDER, 6)
    bx, _, bz = BONFIRE_AT
    for x in range(bx - 2, bx + 3):
        for z in range(bz - 2, bz + 3):
            if math.hypot(x - bx, z - bz) <= 2.3:
                p.set(x, -1, z, "Rock_Stone_Cobble" if (x, z) != (bx, bz) else "Rock_Stone")
    p.set(*BONFIRE_AT, BONFIRE_OUT)
    for x, z in FIREWOOD_SPOTS:
        p.set(x, 0, z, PILE)
    x0, x1, z0, z1 = ROAD
    for z in range(z0, z1 + 1):
        for x in range(x0 - 1, x1 + 2):
            ground(p, x, z)
            if x in (x0 - 1, x1 + 1):
                for y in range(0, 8):
                    p.set(x, y, z, pick(ROCK, x, y, z))
    for cell in ICE_WALL:
        p.set(*cell, ICE)
    # Arène de la Source : cinq foyers en pentagone, huttes et râtelier de torches à l'entrée.
    sx, sz = SOURCE_C
    fc.disc(p, sx, sz, SOURCE_RADIUS, 0, lambda x, z: pick(GROUND, x, -1, z), UNDER, 8)
    for x, z in BRAZIERS:
        p.set(x, -1, z, "Rock_Stone_Cobble")
        p.set(x, 0, z, BRAZIER_OUT)
    for k, (x, z) in enumerate(HUTS):
        hut(p, x, z, 1 if x < 0 else -1)
    p.set(*TORCH_RACK_AT, TORCH_RACK)
    for (x, y, z) in GATE_SOURCE:
        p.set(x, y, z, MIST)
    # Forêt : sentier sinueux, fausses pistes, empreintes au sol.
    for z in range(FOREST_Z[0] + 1, FOREST_Z[1] - 3, -1):
        c = path_x(z)
        for x in range(c - 2, c + 3):
            ground(p, x, z)
    for z_start, side in SPURS:
        for k in range(14):
            z = z_start - k // 2
            x = path_x(z_start) + side * (3 + k)
            for dz in (-1, 0, 1):
                ground(p, x, z + dz)
    for x, z in FOOTPRINT_CELLS:
        p.set(x, -1, z, FOOTPRINTS)
    # Village du Chaman : arène ronde, feux du village, balcon au nord (on n'y monte pas).
    vx, vz = VILLAGE_C
    fc.disc(p, vx, vz, VILLAGE_RADIUS, 0, lambda x, z: pick(GROUND, x, -1, z), UNDER, 8)
    for x, z in VILLAGE_FIRES:
        p.set(x, -1, z, "Rock_Stone_Cobble")
        p.set(x, 0, z, BRAZIER)
    bx, by, bz = BALCONY
    for x in range(bx - 4, bx + 5):
        for z in range(bz - 3, bz + 3):
            p.set(x, by - 1, z, "Wood_Darkwood_Planks" if (x + z) % 2 else PLANK)
    for x in (bx - 4, bx + 4):
        for z in (bz - 3, bz + 2):
            for y in range(0, by - 1):
                p.set(x, y, z, PLANK)
    for x in range(bx - 4, bx + 5):
        p.set(x, by, bz + 2, "Wood_Darkwood_Fence" if abs(x - bx) < 4 else PLANK)
    for k, a in enumerate(range(200, 341, 35)):     # huttes du village sur le pourtour nord
        hx = round(vx + math.cos(math.radians(a)) * (VILLAGE_RADIUS - 3))
        hz = round(vz + math.sin(math.radians(a)) * (VILLAGE_RADIUS - 3))
        if abs(hx - bx) > 6:
            hut(p, hx, hz, 1 if hx < 0 else -1)
            p.set(hx, 0, hz, "Plant_Bush_Winter_Snow")
    for (x, y, z) in GATE_VILLAGE:
        p.set(x, y, z, go.AIR)
    dress(p)
    return p


def dress(p):
    """Forêt de sapins enneigés autour de tout le parcours (dense le long du sentier), rochers et glace, îlots de
    neige au loin. Rien sur les lieux de jeu : feux, foyers, tas de fagots, empreintes, mur, portes."""
    footprint = {(x, z): -1 for (x, y, z) in p.blocks if y == -1}
    keep = set()
    for x, z in FIREWOOD_SPOTS + BRAZIERS + HUTS + VILLAGE_FIRES + ELEMENTAL_SPAWNS + WAVE_SPAWNS:
        keep |= {(x + dx, z + dz) for dx in range(-2, 3) for dz in range(-2, 3)}
    keep |= {(x, z) for x, _, z in ICE_WALL}
    keep |= {(x, z) for x in range(-3, 4) for z in range(SPAWN[2] - 3, SPAWN[2] + 4)}
    keep |= {(x, z) for x, z in FOOTPRINT_CELLS}
    for name_cells in (GATE_SOURCE, GATE_VILLAGE):
        keep |= {(x, z) for x, _, z in name_cells}
    cells = [(x, -1, z) for (x, z) in footprint if (x, z) not in keep and p.blocks.get((x, -1, z), ("",))[0] in GROUND]
    # Clairières et arènes : herbe de neige et buissons seulement ; forêt : sapins le long du sentier.
    forest = [c for c in cells if FOREST_Z[1] < c[2] < FOREST_Z[0] and abs(c[0] - path_x(c[2])) >= 2]
    fn.flora(p, [c for c in cells if c not in forest], seed=81, density=0.3, flowers=0.0, theme=THEME)
    ring = fn.rim(footprint, 6, 14, seed=83)
    tops = {c: 0 for c in ring}
    edge = fn.edge_distance({**tops, **{c: -1 for c in footprint}})
    ground_cells = fn.island(p, {c: -1 for c in ring}, lambda x, z: 5 + min(10, edge.get((x, z), 0)), 85,
                             hang=0.2, theme=THEME)
    ground_cells = [c for c in ground_cells if not near_barrier(c[2])]
    fn.dress(p, ground_cells, THEME, 85, trees=0.22, spacing=3, bushes=0.08, boulders=0.01, density=0.4, flowers=0.0)
    # Sapins serrés de part et d'autre du sentier, sous lesquels il fait sombre.
    for x, y, z in ground_cells + forest:
        if FOREST_Z[1] - 4 < z < FOREST_Z[0] + 2 and abs(x - path_x(z)) >= 3 and not near_barrier(z, 4) and fn.hash01(x, z, 7, 87) < 0.18 \
                and fn.free(p, x, 0, z) and all(not p.blocks.get((x + dx, 0, z + dz), ("Empty",))[0].startswith("Wood_")
                                                for dx in (-2, -1, 0, 1, 2) for dz in (-2, -1, 0, 1, 2)):
            fn.conifer(p, x, 0, z, 9 + int(fn.hash01(z, x, 3, 88) * 8), "fir_snow", seed=x * 13 + z)
    fn.scatter_islets(p, (-120, 120, -260, 110), 20, (-32, 10), (3, 9), THEME, seed=89)
    barriers(p)


def barriers(p):
    """Remparts de glace sur toute la largeur de l'île, sauf au passage (mur fondant, brume, porte du village)."""
    for zs, block, gap in BARRIERS:
        for z in zs:
            columns = {x for (x, y, z2) in p.blocks if z2 == z and y == -1}
            for x in columns - set(gap):
                for y in range(0, BARRIER_HEIGHT):
                    p.set(x, y, z, pick([block, block, "Rock_Ice_Permafrost", block], x, y, z))


# --- objets, blocs, effets, particules ------------------------------------------------------------------

def firewood_parts():
    bark, wood, rope = (110, 78, 48), (196, 158, 108), (200, 180, 120)
    return [("Log_A", (0, 3, -2.5), (14, 4, 4), 0, fm.smooth(bark, wood), "flat"),
            ("Log_B", (0, 3, 2.5), (14, 4, 4), 0, fm.smooth(bark, wood), "flat"),
            ("Log_C", (0, 7, 0), (14, 4, 4), 0, fm.smooth(bark, wood), "flat"),
            ("Rope_A", (-4, 5, 0), (1.5, 9, 10), 0, fm.flat(rope), "flat"),
            ("Rope_B", (4, 5, 0), (1.5, 9, 10), 0, fm.flat(rope), "flat")]


def torch_parts():
    wood, cloth, flame, core = (96, 66, 40), (150, 120, 80), (255, 140, 40), (255, 236, 160)
    return [("Handle", (0, 7, 0), (2, 14, 2), 0, fm.smooth(wood), "flat"),
            ("Wrap", (0, 14.5, 0), (3, 3, 3), 0, fm.smooth(cloth), "flat"),
            ("Flame", (0, 18, 0), (3.5, 5, 3.5), 45, fm.crystal(flame, core), "fullbright"),
            ("Tip", (0, 21, 0), (2, 2, 2), 45, fm.crystal(flame, core), "fullbright")]


def items():
    return {
        FIREWOOD: fc.held_item(LANG, FIREWOOD, "Firewood", firewood_parts(), 91, (0, 5, 0), 12.0, quality="Common",
                               stack=3, extra={"Categories": ["Items.Misc"]}),
        TORCH: fc.held_item(LANG, TORCH, "Frost_Torch", torch_parts(), 92, (0, 11, 0), 9.0, quality="Uncommon", stack=1,
                            extra={"Categories": ["Items.Misc"], "Light": {"Color": "#fa6", "Radius": 7}}),
    }


def blocks():
    """(id, texture, fond, couleur, glyphe, lumière, action, plein, alpha, opacité)."""
    use = lambda action: f"Nakasar_Fractal_Use_{action}"
    return [
        (BONFIRE, "Bonfire", (70, 50, 40), (255, 150, 50), "fire", "#fa6", use("Snowblind_Bonfire"), True, 255, None),
        (BONFIRE_OUT, "Bonfire_Out", (70, 64, 60), (120, 110, 100), "fire", None, use("Snowblind_Bonfire"), True, 255, None),
        (BRAZIER, "Frost_Brazier", (80, 76, 72), (255, 160, 60), "fire", "#fa6", use("Snowblind_Brazier"), True, 255, None),
        (BRAZIER_OUT, "Frost_Brazier_Out", (80, 84, 92), (150, 190, 230), "fire", None, use("Snowblind_Brazier"), True,
         255, None),
        (PILE, "Firewood_Pile", (100, 72, 46), (200, 160, 110), "rack", None, use("Snowblind_Firewood"), True, 255, None),
        (TORCH_RACK, "Torch_Rack", (96, 70, 46), (255, 170, 70), "rack", "#fa6", use("Snowblind_Torch"), True, 255, None),
        (FOOTPRINTS, "Footprints", (236, 242, 248), (150, 160, 180), "feet", None, None, True, 255, None),
    ]


def footprint_texture(path):
    """Neige marquée de deux empreintes de pas (le glyphe « feet » des textures n'existe que pour les icônes)."""
    img = Image.new("RGBA", (32, 32), (236, 242, 248, 255))
    d = ImageDraw.Draw(img)
    for k in range(40):
        x, y = (k * 7) % 31, (k * 13) % 31
        d.point((x, y), fill=(220, 228, 240, 255))
    for x, y in ((9, 6), (21, 18)):
        d.ellipse((x - 3, y, x + 3, y + 9), fill=(160, 170, 192, 255))
        d.ellipse((x - 2, y - 4, x + 2, y - 1), fill=(160, 170, 192, 255))
    img.save(path)
    return img


def cold_cause():
    return fc.cause("Froid de la Tempête de neige (Hypothermie) : une part des PV max par seconde selon les piles, que "
                    "l'armure ne réduit pas.", "#a8d8ff")


def frost_cause():
    return {"$Comment": "Glace des attaques annoncées du Chaman (pluie, pics, souffle) : comme un coup physique (l'armure "
                        "compte), mais distincte de ses coups d'épée, les seuls qui ajoutent de l'hypothermie (Java).",
            "BypassResistances": False, "DamageTextColor": "#bfe6ff"}


def effects():
    L = LANG
    out = {
        "Nakasar_Fractal_Warmth": fc.effect(
            L, "Nakasar_Fractal_Warmth", "Chaleur (près d'un feu allumé) : l'hypothermie redescend (Java).", "Warmth", 1.5,
            ApplicationEffects={"EntityBottomTint": "#ffb060"}),
        "Nakasar_Fractal_Encased": fc.effect(
            L, "Nakasar_Fractal_Encased", "Pris dans un éclat de glace (hypothermie au maximum) : immobile tant que les "
            "alliés ne l'ont pas brisé (Java).", "Encased", 1.5, debuff=True,
            ApplicationEffects={"MovementEffects": {"DisableAll": True}, "EntityTopTint": "#bfe6ff",
                                "EntityBottomTint": "#7ab8ff"}),
    }
    for tier in range(1, HYPOTHERMIA_TIERS + 1):
        eid = f"Nakasar_Fractal_Hypothermia_{tier}"
        out[eid] = fc.effect(
            L, eid, f"Hypothermie, piles {tier * 2 - 1} et {tier * 2} : {0.3 * (tier * 2 - 1):.1f} à {0.6 * tier:.1f} % "
            "des PV max par seconde, course ralentie à partir de 5 piles (Java).", f"Hypothermia_{tier}", 1.5, debuff=True,
            ApplicationEffects={"HorizontalSpeedMultiplier": round(1.0 - 0.06 * max(0, tier - 2), 2),
                                "EntityTopTint": ["#e8f4ff", "#d0e8ff", "#b0d8ff", "#90c4ff", "#70b0ff"][tier - 1]})
    return out


def snow_icon(path, color, tier=None):
    """Icône d'hypothermie (flocon, autant de pointes pleines que de crans) ou d'éclat de glace."""
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    d.ellipse((6, 6, 121, 121), fill=(18, 26, 40, 255), outline=c, width=6)
    if tier is None:
        d.polygon(((64, 18), (96, 52), (84, 108), (44, 108), (32, 52)), fill=c)
        d.line((64, 18, 64, 108), fill=(255, 255, 255, 255), width=3)
    else:
        for k in range(6):
            a = math.radians(k * 60 - 90)
            x, y = 64 + math.cos(a) * 44, 64 + math.sin(a) * 44
            d.line((64, 64, x, y), fill=c, width=8 if k < tier + 1 else 4)
            for s in (-1, 1):
                b = a + s * 0.6
                d.line((64 + math.cos(a) * 28, 64 + math.sin(a) * 28,
                        64 + math.cos(a) * 28 + math.cos(b) * 12, 64 + math.sin(a) * 28 + math.sin(b) * 12), fill=c, width=4)
        d.ellipse((54, 54, 74, 74), fill=c)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Bonfire_Flames": ("Grand feu de camp : flammes orange et braises qui montent.",
                                       [("Flames", S("#fff0a0", "#ff5010", 18, (0.8, 1.8), (70, 90), 0.8, 1.0,
                                                     life=(0.5, 0.9), size=(0.3, 0.6)), 0.2),
                                        ("Embers", S("#ffd080", "#ff4000", 8, (1.5, 3.0), (60, 90), 1.0, 1.4,
                                                     life=(1.0, 1.6), size=(0.08, 0.15)), 0.6)]),
    "Nakasar_Fractal_Brazier_Flames": ("Foyer allumé : petites flammes.",
                                       [("Flames", S("#fff0a0", "#ff6010", 10, (0.6, 1.4), (70, 90), 0.4, 0.6,
                                                     life=(0.4, 0.8), size=(0.2, 0.4)), 0.5)]),
    "Nakasar_Fractal_Fire_Doused": ("Feu éteint par le givre : fumée et éclats de glace.",
                                    [("Smoke", S("#c8c8c8", "#404048", 20, (0.5, 1.5), (40, 90), 1.4, 1.2,
                                                 life=(1.0, 1.6), blend="BlendLinear"), 0.3),
                                     ("Frost", S("#ffffff", "#80c0ff", 14, (1.0, 2.5), (0, 90), 1.0, 0.8,
                                                 life=(0.4, 0.8)), 0.4)]),
    "Nakasar_Fractal_Ice_Melt": ("Le mur de glace fond : vapeur et gouttes.",
                                 [("Steam", S("#ffffff", "#a0c0e0", 24, (0.6, 1.6), (50, 90), 4.0, 1.0,
                                              life=(0.8, 1.4), blend="BlendLinear"), 0.4)]),
    "Nakasar_Fractal_Snowfall": ("Neige qui tombe autour d'un joueur (Tempête de neige).",
                                 [("Flakes", S("#ffffff", "#d0e0ff", 30, (0.2, 0.6), (-90, -60), 9.0, 4.0,
                                               life=(2.0, 3.0), size=(0.06, 0.12), blend="BlendLinear"), 5.0)]),
    "Nakasar_Fractal_Blizzard": ("Blizzard : rafales de neige épaisses autour d'un joueur.",
                                 [("Gust", S("#ffffff", "#b8d0f0", 60, (3.0, 6.0), (-30, 10), 8.0, 4.0,
                                             life=(0.8, 1.4), size=(0.1, 0.25), blend="BlendLinear"), 1.0)]),
    "Nakasar_Fractal_Warm_Glow": ("Chaleur : lueur orangée aux pieds d'un joueur réchauffé.",
                                  [("Glow", S("#ffe0a0", "#ff8040", 4, (0.2, 0.5), (60, 90), 0.4, 0.4,
                                              life=(0.4, 0.7), size=(0.1, 0.2)), 0.1)]),
    "Nakasar_Fractal_Shard_Break": ("Éclat de glace brisé : éclats bleus.",
                                    [("Shards", S("#ffffff", "#60a8ff", 24, (2.0, 4.5), (0, 90), 0.6, 1.2,
                                                  life=(0.4, 0.8), size=(0.15, 0.3)), 0.6)]),
    "Nakasar_Fractal_Source_Pulse": ("Bouclier de givre de la Source : anneau de givre.",
                                     [("Ring", S("#e0f4ff", "#5090ff", 30, (2.0, 3.5), (-5, 5), 1.5, 0.4,
                                                 life=(0.6, 1.0)), 1.0)]),
}


# --- modèles ----------------------------------------------------------------------------------------------

def bear_parts():
    fur, dark, frost = (210, 216, 226), (120, 128, 140), (150, 210, 255)
    return [("Body", (0, 40, 0), (36, 30, 56), 0, fm.smooth(fur), "flat"),
            ("Hump", (0, 56, 10), (28, 10, 22), 0, fm.smooth(fur), "flat"),
            ("Head", (0, 50, 36), (22, 20, 20), 0, fm.smooth(fur), "flat"),
            ("Snout", (0, 45, 48), (11, 9, 10), 0, fm.smooth(dark), "flat"),
            ("Ear_L", (-8, 62, 34), (5, 5, 4), 0, fm.smooth(dark), "flat"),
            ("Ear_R", (8, 62, 34), (5, 5, 4), 0, fm.smooth(dark), "flat"),
            ("Eyes", (0, 53, 46.5), (14, 3, 1), 0, fm.crystal((40, 120, 255), frost), "fullbright"),
            ("Mane", (0, 52, 22), (30, 16, 8), 0, fm.crystal((120, 170, 230), frost), "fullbright")] + [
        (f"Leg_{k}", (x, 13, z), (11, 26, 11), 0, fm.smooth(dark), "flat")
        for k, (x, z) in enumerate(((-11, 18), (11, 18), (-11, -18), (11, -18)))]


def crystal_parts(color, light, height):
    return [("Core", (0, height / 2, 0), (12, height, 12), 45, fm.crystal(color, light), "fullbright"),
            ("Shard_A", (8, height * 0.3, 2), (6, height * 0.55, 6), 20, fm.crystal(color, light), "fullbright"),
            ("Shard_B", (-7, height * 0.25, -3), (6, height * 0.45, 6), -30, fm.crystal(color, light), "fullbright"),
            ("Base", (0, 2, 0), (20, 4, 20), 0, fm.smooth((180, 196, 214)), "flat")]


def effigy_parts():
    ice, light = (110, 170, 230), (230, 245, 255)
    return [("Base", (0, 6, 0), (30, 12, 30), 45, fm.smooth((150, 170, 196)), "flat"),
            ("Body", (0, 40, 0), (22, 56, 16), 0, fm.crystal(ice, light), "fullbright"),
            ("Head", (0, 76, 0), (16, 16, 16), 45, fm.crystal(ice, light), "fullbright"),
            ("Horn_L", (-10, 88, 0), (4, 16, 4), 25, fm.crystal(ice, light), "fullbright"),
            ("Horn_R", (10, 88, 0), (4, 16, 4), -25, fm.crystal(ice, light), "fullbright"),
            ("Arm_L", (-17, 48, 0), (10, 34, 10), 0, fm.crystal(ice, light), "fullbright"),
            ("Arm_R", (17, 48, 0), (10, 34, 10), 0, fm.crystal(ice, light), "fullbright")]


def models():
    m = {}
    frost_hood = [("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
                  ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
                   gc.CLOTH, "Blue"),
                  ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
                   "Faded_Leather", "Black"),
                  ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
                   "Faded_Leather", "Black")]
    m[CULTIST] = fr.humanoid("Cultiste du givre (provisoire) : capuche et cape bleue, d'après les cultistes de la "
                             "Falaise.", "05", "Face_Scar", frost_hood)
    m[ICE_CASTER] = fr.humanoid("Incantateur du givre (provisoire) : robe de mage et cape bleue, lueur froide.", "11",
                                "Face_Sunken", [frost_hood[0], (
                                    "Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
                                    frost_hood[1]], light={"Color": "#8cf", "Radius": 2})
    m[SHAMAN] = gv.grawl("Le Chaman légendaire (provisoire) : grand grawl (× 1,45), couronne, cape bleue et robe ; GW2 en "
                         "fait un grawl couvert de fourrure.", "25", [
                             ("Cosmetics/Head/KingsCrown.blockymodel", "Cosmetics/Head/KingsCrown_Red.png"),
                             ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
                             frost_hood[1], frost_hood[2], frost_hood[3]],
                         scale=(1.45, 1.45), light={"Color": "#8cf", "Radius": 3})
    m[ELEMENTAL] = {"$Comment": "Élémentaire de glace (provisoire) : l'esprit de givre vanilla.", "Parent": "Spirit_Frost",
                    "MinScale": 1.1, "MaxScale": 1.1, "Light": {"Color": "#9cf", "Radius": 2}}
    m[SOURCE] = {"$Comment": "La Source élémentaire (provisoire) : l'esprit de givre vanilla, géant (× 3,2) ; GW2 en "
                             "fait un géant de glace.", "Parent": "Spirit_Frost", "MinScale": 3.2, "MaxScale": 3.2,
                 "Light": {"Color": "#9cf", "Radius": 6}}
    m[WOLF] = fc.character_model("Frost_Wolf", gs.wolf_parts((214, 220, 230), (130, 140, 156), (120, 200, 255)), 93,
                                 "Loup des neiges (provisoire) : loup en boîtes, sans animation.", 0.6, (0.5, 0.9))
    m[BEAR] = fc.character_model("Shaman_Bear", bear_parts(), 94, "Le Chaman légendaire en ours (provisoire) : ours "
                                 "polaire en boîtes, crinière de givre, sans animation.", 1.0, (0.9, 1.4),
                                 light={"Color": "#8cf", "Radius": 3}, scale=1.3)
    m[EFFIGY] = fc.character_model("Ice_Effigy", effigy_parts(), 95, "Effigie de glace (PNJ fixe) : tant qu'elle tient, "
                                   "le Chaman reste sur son balcon.", 1.4, (0.6, 1.6), light={"Color": "#9cf", "Radius": 4},
                                   scale=1.2)
    m[CRYSTAL] = fc.character_model("Corrupted_Crystal", crystal_parts((90, 40, 150), (200, 160, 255), 44), 96,
                                    "Cristal de glace corrompu (PNJ fixe) : protège le Chaman tant qu'il tient.", 0.8,
                                    (0.4, 1.0), light={"Color": "#a6f", "Radius": 3})
    m[SHARD] = fc.character_model("Ice_Shard", crystal_parts((120, 180, 240), (235, 248, 255), 60), 97,
                                  "Éclat de glace (PNJ fixe) : enferme un joueur gelé jusqu'à ce que ses alliés le "
                                  "brisent.", 1.0, (0.6, 1.4), light={"Color": "#9cf", "Radius": 2}, scale=1.2)
    return m


# --- attaques et rôles ------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
FROST_ANIMS = None   # l'esprit de givre vanilla n'a pas de jeu d'animations vérifié : poses sans animation


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Elemental_Touch"] = {
        "$Comment": "Élémentaire de glace au contact : toucher gelé (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Toucher gelé.", None, None, 0.35, 6, end=2.2, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Cultist_Frost_Slash"] = {
        "$Comment": "Cultiste du givre : deux entailles (9 dégâts chacune).",
        "Type": "Serial", "Interactions": [fr.swing("Entaille gauche.", "Mace", "SwingLeft", 0.35, 9, end=2.8),
                                           fr.swing("Entaille droite.", "Mace", "SwingRight", 0.35, 9, end=2.8,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Caster_Frost_Bolt"] = {
        "$Comment": "Incantateur du givre : trait de glace sous sa cible, cercle rouge de 2 blocs (1,3 s), 14 dégâts et "
                    "ralentissement.",
        "Type": "Serial", "Interactions": [T("Circle", 1.3, Anchor="Target", Radius=2, Damage=14, EffectId="Nakasar_Fractal_Crippled",
                                             EffectDuration=2.5, PlayersOnly=True, ImpactParticle="Ice_Blast"),
                                           fc.windup(1.3, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Source_Slam"] = {
        "$Comment": "La Source élémentaire au contact : coup de poing (26 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de poing.", None, None, 0.6, 26, end=5.0, length=110,
                                                     sound="SFX_Goblin_Feastmaster_Slam")]}
    out["Nakasar_Fractal_Source_Orb"] = {
        "$Comment": "La Source : orbe lent sur sa cible, cercle rouge de 3 blocs (2,2 s), 22 dégâts, repousse loin.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 2.2, Anchor="Target", Radius=3, Damage=22, Knockback=12,
                                                     KnockUp=4, PlayersOnly=True, ImpactParticle="Ice_Blast",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(2.2, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Source_Whirl"] = {
        "$Comment": "La Source : tourbillon autour d'elle, cercle rouge de 7 blocs (2,4 s), 18 dégâts, repousse ceux "
                    "qui restent dedans.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 2.4, Radius=7, Damage=18, Knockback=10, KnockUp=2,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Source_Pulse"),
                                           fc.windup(2.4, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Shaman_Slash"] = {
        "$Comment": "Le Chaman légendaire au contact : deux coups d'épée (16 dégâts chacun) ; chaque coup ajoute deux "
                    "piles d'hypothermie (Java).",
        "Type": "Serial", "Interactions": [fr.swing("Coup d'épée.", "Mace", "SwingLeft", 0.4, 16, end=3.6),
                                           fr.swing("Revers.", "Mace", "SwingRight", 0.4, 16, end=3.6,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Shaman_Ice_Rain"] = {
        "$Comment": "Le Chaman : pluie de glace, un cercle rouge de 2,5 blocs sous chaque joueur (1,6 s), 16 dégâts.",
        "Type": "Serial", "Interactions": [T("Circle", 1.6, Anchor="EachPlayer", Radius=2.5, Damage=16, DamageCause=FROST_CAUSE, PlayersOnly=True,
                                             ImpactParticle="Ice_Blast"),
                                           fc.windup(1.6, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Shaman_Spikes"] = {
        "$Comment": "Le Chaman : pics de glace, anneau autour de lui, cercle rouge de 5 blocs (1,5 s), 24 dégâts et "
                    "projection.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Radius=5, Damage=24, DamageCause=FROST_CAUSE, Knockback=6, KnockUp=3,
                                                     PlayersOnly=True, ImpactParticle="Ability_GroundSlam_Spike"),
                                           fc.windup(1.5, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    out["Nakasar_Fractal_Shaman_Breath"] = {
        "$Comment": "Le Chaman : il s'agenouille et souffle un cône glacé de 70° sur 11 blocs (2,2 s), 30 dégâts et "
                    "ralentissement.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.2, Angle=70, Radius=11, Damage=30, DamageCause=FROST_CAUSE, EffectId="Nakasar_Fractal_Crippled",
                                                     EffectDuration=3, PlayersOnly=True, HitParticle="Impact_Ice",
                                                     ImpactParticle="Weapon_Frost_Mist"),
                                           fc.windup(2.2, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    out["Nakasar_Fractal_Bear_Maul"] = {
        "$Comment": "Le Chaman en ours, au contact : deux coups de griffes (22 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Griffe gauche.", None, None, 0.35, 22, end=3.6, sound="SFX_Unarmed_Swing"),
                                           fr.swing("Griffe droite.", None, None, 0.35, 22, end=3.6, direction="ToRight",
                                                    yaw=-50, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Bear_Leap"] = {
        "$Comment": "Le Chaman en ours : bond sur sa cible, cercle rouge de 4 blocs (1,5 s), 34 dégâts et renversement "
                    "long (3 s).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Anchor="Target", Radius=4, Damage=34,
                                                     TeleportCaster=True, EffectId="Nakasar_Fractal_Stunned",
                                                     EffectDuration=3, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.5, "SFX_Spear_Throw_Charge")]}
    for action, comment in (("Snowblind_Bonfire", "Grand feu de camp : l'allumer ou le nourrir avec un fagot."),
                            ("Snowblind_Brazier", "Foyer : l'allumer avec une torche, le nourrir avec un fagot."),
                            ("Snowblind_Firewood", "Tas de fagots : en prendre un."),
                            ("Snowblind_Torch", "Râtelier : prendre une torche.")):
        out[f"Nakasar_Fractal_Use_{action}"] = fc.use_interaction(action, comment)
    return out


MELEE = ["Elemental_Touch", "Cultist_Frost_Slash", "Source_Slam", "Source_Orb", "Source_Whirl", "Shaman_Slash",
         "Shaman_Spikes", "Shaman_Breath", "Bear_Maul", "Bear_Leap"]
RANGED = ["Caster_Frost_Bolt", "Shaman_Ice_Rain"]
R = fc.root


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    elem = fr.role(
        ELEMENTAL, "Élémentaire de glace : sort de la forêt et court éteindre le grand feu (point d'attache posé par le "
        "Java) ; il ne se bat que si on le frappe. Arrivé au feu, il l'éteint en partie et disparaît (Java).", ELEMENTAL,
        n(ELEMENTAL), 60, [fr.melee(R("Elemental_Touch"), 2.2, (0.8, 1.2)), fr.chase(16, stop=1.4)],
        fr.walk(3.6), GENERATOR, sight=2, leash=10, home=True, KnockbackScale=1.0, DeathAnimationTime=0.8)
    elem["StartState"] = "ReturnHome"
    out[ELEMENTAL] = elem
    out[WOLF] = fr.role(
        WOLF, "Loup des neiges : arrive en meute sur le camp, fonce et mord.", WOLF, n(WOLF), 70,
        [fr.melee(R("Wolf_Bite"), 2.2, (0.7, 1.1)), fr.chase(40, stop=1.4)],
        fr.walk(5.2), GENERATOR, sight=40, leash=48, home=False, KnockbackScale=0.8, DeathAnimationTime=0.8)
    out[CULTIST] = fr.role(
        CULTIST, "Cultiste du givre : entailles au contact.", CULTIST, n(CULTIST), 110,
        [fr.melee(R("Cultist_Frost_Slash"), 2.4, (0.7, 1.1)), fr.chase(40, stop=1.6)],
        fr.walk(3.8), GENERATOR, sight=40, leash=48, home=False, HotbarItems=["Weapon_Sword_Steel_Rusty"],
        KnockbackScale=0.8, DeathAnimationTime=1.0)
    out[ICE_CASTER] = fr.role(
        ICE_CASTER, "Incantateur du givre : garde ses distances, trait de glace annoncé sous sa cible.", ICE_CASTER,
        n(ICE_CASTER), 80,
        [fr.cast("Bolt", R("Caster_Frost_Bolt"), 18, "Trait de glace annoncé."), fr.keep_distance(40, 6, 11)],
        fr.walk(3.6), GENERATOR, sight=40, leash=48, home=False, timers=[fr.timer("Bolt", (1, 3), (5, 7))],
        HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=1.0, DeathAnimationTime=1.0)
    out[SOURCE] = fr.role(
        SOURCE, "La Source élémentaire, barre de boss : orbe lent qui repousse, tourbillon, coups de poing. Les foyers, "
        "son bouclier de givre, ses frappes sur les foyers et le blizzard sont menés par le Java (snowblind.Source).",
        SOURCE, n(SOURCE), 6000,
        [fr.timed_attack("Whirl", R("Source_Whirl"), rng=6, los=True, comment="Tourbillon."),
         fr.timed_attack("Orb", R("Source_Orb"), rng=26, los=True, comment="Orbe lent."),
         fr.melee(R("Source_Slam"), 4.4, (1.2, 1.6)), fr.chase(36, stop=3.4)],
        fr.walk(1.6), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Whirl", (5, 7), (11, 14)), fr.timer("Orb", (2, 4), (6, 8))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[SHAMAN] = fr.role(
        SHAMAN, "Le Chaman légendaire, barre de boss : coups d'épée (hypothermie, Java), pluie de glace, pics de glace, "
        "souffle glacé. Les cristaux corrompus, le balcon, l'Effigie et la forme d'ours sont menés par le Java "
        "(snowblind.Shaman).", SHAMAN, n(SHAMAN), 7000,
        [fr.timed_attack("Breath", R("Shaman_Breath"), rng=10, los=True, comment="Souffle glacé."),
         fr.timed_attack("Spikes", R("Shaman_Spikes"), rng=4.5, los=True, comment="Pics de glace."),
         fr.timed_attack("Rain", R("Shaman_Ice_Rain"), rng=30, comment="Pluie de glace."),
         fr.melee(R("Shaman_Slash"), 3.0, (0.8, 1.2)), fr.chase(40, stop=2.2)],
        fr.walk(3.6), GENERATOR, sight=40, leash=44, home=False,
        timers=[fr.timer("Breath", (6, 8), (14, 17)), fr.timer("Spikes", (3, 5), (9, 12)),
                fr.timer("Rain", (9, 11), (15, 19))],
        HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.1, DeathAnimationTime=2.0)
    out[BEAR] = fr.role(
        BEAR, "Le Chaman légendaire en ours (sous 25 %) : bonds qui renversent longtemps, griffes.", BEAR, n(BEAR), 7000,
        [fr.timed_attack("Leap", R("Bear_Leap"), rng=20, los=True, comment="Bond annoncé."),
         fr.melee(R("Bear_Maul"), 3.2, (0.6, 1.0)), fr.chase(40, stop=2.4)],
        fr.walk(5.0), GENERATOR, sight=40, leash=44, home=False, timers=[fr.timer("Leap", (2, 4), (8, 10))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[EFFIGY] = fc.static_role(LANG, EFFIGY, "Effigie de glace : ne bouge pas, barre de défiance toujours ouverte ; "
                                 "brisée ou détruite, le Chaman redescend du balcon (Java).", GENERATOR, 900)
    out[CRYSTAL] = fc.static_role(LANG, CRYSTAL, "Cristal de glace corrompu : ne bouge pas ; tant qu'il en reste un, le "
                                  "Chaman ne prend aucun dégât (Java).", GENERATOR, 160)
    out[SHARD] = fc.static_role(LANG, SHARD, "Éclat de glace : enferme un joueur à l'hypothermie maximale ; ses alliés le "
                                "brisent, ses propres coups ne comptent pas (Java).", GENERATOR, 90)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(FIREWOOD, "Fagot", "Utiliser un feu ou un foyer : le nourrir.", "Firewood", "Use a fire or a brazier: feed it.")
    t.item(TORCH, "Torche", "Allume les foyers ; en main, elle éclaire et ralentit le froid.", "Torch",
           "Lights braziers; in hand, it lights the way and slows the cold.")
    t.item(BONFIRE, "Grand feu de camp", "Utiliser avec un fagot : le nourrir. Il fait fondre le mur de glace.",
           "Great campfire", "Use with firewood: feed it. It melts the ice wall.")
    t.item(BONFIRE_OUT, "Grand feu de camp (éteint)", "Utiliser avec un fagot : l'allumer.", "Great campfire (out)",
           "Use with firewood: light it.")
    t.item(BRAZIER, "Foyer", "Utiliser avec un fagot : le nourrir.", "Brazier", "Use with firewood: feed it.")
    t.item(BRAZIER_OUT, "Foyer (éteint)", "Utiliser avec une torche : l'allumer.", "Brazier (out)",
           "Use with a torch: light it.")
    t.item(PILE, "Tas de fagots", "Utiliser : prendre un fagot (trois au plus).", "Firewood pile",
           "Use: take firewood (three at most).")
    t.item(TORCH_RACK, "Râtelier de torches", "Utiliser : prendre une torche.", "Torch rack", "Use: take a torch.")
    t.item(FOOTPRINTS, "Empreintes", "Des traces de pas dans la neige.", "Footprints", "Tracks in the snow.")
    for role, f, e in ((ELEMENTAL, "Élémentaire de glace", "Ice elemental"), (WOLF, "Loup des neiges", "Snow wolf"),
                       (CULTIST, "Cultiste du givre", "Frost cultist"), (ICE_CASTER, "Incantateur du givre", "Frost caster"),
                       (SOURCE, "Source élémentaire", "Elemental Source"), (SHAMAN, "Chaman légendaire", "Legendary Shaman"),
                       (BEAR, "Chaman légendaire (ours)", "Legendary Shaman (bear)"), (EFFIGY, "Effigie de glace", "Ice Effigy"),
                       (CRYSTAL, "Cristal de glace corrompu", "Corrupted ice crystal"), (SHARD, "Éclat de glace", "Ice shard")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Warmth", "Chaleur", "Warmth")
    t.put("effects.Nakasar_Fractal_Encased", "Pris dans la glace", "Encased in ice")
    for tier in range(1, HYPOTHERMIA_TIERS + 1):
        t.put(f"effects.Nakasar_Fractal_Hypothermia_{tier}", f"Hypothermie {tier * 2}", f"Hypothermia {tier * 2}")
    msgs = {
        "intro": ("Tempête de neige : loin d'un feu, le froid s'accumule (Hypothermie). Allumez le grand feu avec un fagot "
                  "pris sous les arbres : il fera fondre le mur de glace au nord.",
                  "Snowblind: away from a fire, the cold builds up (Hypothermia). Light the great campfire with firewood "
                  "from under the trees: it will melt the ice wall to the north."),
        "fire.need": ("Il faut un fagot pour l'allumer.", "You need firewood to light it."),
        "fire.lit": ("Le grand feu prend : le mur de glace commence à fondre. Nourrissez-le !",
                     "The great fire catches: the ice wall starts to melt. Keep feeding it!"),
        "fire.fed": ("Fagot ajouté : {fuel} %.", "Firewood added: {fuel} %."),
        "fire.full": ("Le feu est déjà au plus fort.", "The fire is already at its strongest."),
        "fire.out": ("Le grand feu s'est éteint ! Rallumez-le avec un fagot.", "The great fire went out! Relight it with firewood."),
        "fire.doused": ("Un élémentaire de glace atteint le feu et l'étouffe !", "An ice elemental reaches the fire and smothers it!"),
        "fire.elementals": ("Des élémentaires de glace sortent de la forêt : arrêtez-les avant le feu !",
                            "Ice elementals come out of the forest: stop them before the fire!"),
        "fire.wave": ("Des ennemis attaquent le camp !", "Foes attack the camp!"),
        "wall.melted": ("Le mur de glace a fondu : la route est libre.", "The ice wall has melted: the road is clear."),
        "wood.taken": ("Fagot pris ({count}/3).", "Firewood taken ({count}/3)."),
        "wood.full": ("Vous portez déjà trois fagots.", "You already carry three bundles of firewood."),
        "torch.taken": ("Torche prise : allumez les foyers autour de la Source.", "Torch taken: light the braziers around the Source."),
        "torch.has": ("Vous avez déjà une torche.", "You already have a torch."),
        "brazier.need": ("Il faut une torche pour allumer ce foyer.", "You need a torch to light this brazier."),
        "brazier.lit": ("Foyer allumé ({count}/5) : le bouclier de givre de la Source faiblit.",
                        "Brazier lit ({count}/5): the Source's frost shield weakens."),
        "brazier.fed": ("Foyer nourri : {fuel} %.", "Brazier fed: {fuel} %."),
        "brazier.wood": ("Il faut un fagot (dans les huttes) pour nourrir ce foyer.",
                         "You need firewood (from the huts) to feed this brazier."),
        "brazier.full": ("Ce foyer brûle déjà au plus fort.", "This brazier already burns at its strongest."),
        "brazier.out": ("Un foyer s'éteint ({count}/5 allumés).", "A brazier goes out ({count}/5 lit)."),
        "source.enter": ("La Source élémentaire ! Allumez les foyers (torche au râtelier) : chaque foyer éteint lui donne "
                         "une pile de bouclier de givre.", "The Elemental Source! Light the braziers (torch at the rack): "
                         "each unlit brazier gives it a stack of frost shield."),
        "source.strike": ("La Source frappe les foyers !", "The Source strikes the braziers!"),
        "source.blizzard": ("Tous les foyers sont éteints : BLIZZARD ! Rallumez-en un vite.",
                            "Every brazier is out: BLIZZARD! Relight one quickly."),
        "source.calm": ("Un foyer brûle : le blizzard retombe.", "A brazier burns: the blizzard dies down."),
        "source.reset": ("La Source se fige dans la glace.", "The Source freezes in the ice."),
        "source.victory": ("La Source élémentaire se brise : le chemin de la forêt s'ouvre. Prenez une torche et suivez "
                           "les traces.", "The Elemental Source shatters: the forest path opens. Take a torch and follow "
                           "the tracks."),
        "forest.ambush": ("Des cultistes du givre surgissent entre les sapins !", "Frost cultists burst out between the firs!"),
        "shaman.enter": ("Le Chaman légendaire ! Ses coups d'épée glacent : restez près des feux du village.",
                         "The Legendary Shaman! His sword strikes freeze: stay near the village fires."),
        "shaman.crystals": ("Le Chaman invoque trois cristaux corrompus : il ne prend aucun dégât tant qu'ils tiennent.",
                            "The Shaman summons three corrupted crystals: he takes no damage while they stand."),
        "shaman.exposed": ("Les cristaux sont brisés : le Chaman est vulnérable !", "The crystals are shattered: the Shaman is vulnerable!"),
        "shaman.balcony": ("Le Chaman saute sur son balcon et fait pleuvoir des pics : détruisez l'Effigie de glace !",
                           "The Shaman leaps onto his balcony and rains spikes: destroy the Ice Effigy!"),
        "shaman.down": ("L'Effigie se brise : le Chaman redescend !", "The Effigy shatters: the Shaman comes down!"),
        "shaman.bear": ("Le Chaman prend sa forme d'ours !", "The Shaman takes his bear form!"),
        "shaman.reset": ("Le Chaman se retire dans le blizzard.", "The Shaman withdraws into the blizzard."),
        "shaman.victory": ("Le Chaman légendaire tombe : la tempête se calme.", "The Legendary Shaman falls: the storm calms."),
        "cold.encased": ("Le froid vous saisit : vous êtes pris dans un éclat de glace ! Vos alliés doivent le briser.",
                         "The cold takes you: you are encased in an ice shard! Your allies must break it."),
        "cold.freed": ("L'éclat de glace se brise : vous êtes libre.", "The ice shard breaks: you are free."),
        "cold.ally": ("{name} est pris dans la glace : brisez l'éclat !", "{name} is encased in ice: break the shard!"),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "title.victory": ("Tempête de neige terminée", "Snowblind complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -------------------------------------------------------------------------------------------------

GROUND_Y = fc.GROUND_Y


def java_layout():
    J = fc
    cx, cz = CAMP
    rows = sorted({y for _, y, _ in ICE_WALL}, reverse=True)
    wall_rows = "{" + ", ".join(J.jblocks([c for c in ICE_WALL if c[1] == y]) for y in rows) + "}"
    sx, sz = SOURCE_C
    vx, vz = VILLAGE_C
    ambush_lines = ", ".join(str(GROUND_Y * 0 + z) for z, _ in AMBUSHES)
    ambush_spawns = "{" + ", ".join(J.jpoints([(x, 0, z) for x, z in pts]) for _, pts in AMBUSHES) + "}"
    fz0, fz1 = FOREST_Z
    return f"""package dev.nakasar.hytale.fractals.snowblind;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions de la Tempête de neige, écrites par tools/generate_snowblind.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SnowblindLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Le camp et son grand feu. */
    public static final Box CAMP = {J.jbox(cx - CAMP_RADIUS, cx + CAMP_RADIUS, -1, 12, cz - CAMP_RADIUS, cz + CAMP_RADIUS)};
    public static final int[] BONFIRE = {J.jblock(BONFIRE_AT)};
    public static final double BONFIRE_HEAT = {BONFIRE_HEAT};
    /** Tas de fagots sous les arbres du camp. */
    public static final int[][] CAMP_PILES = {J.jblocks([(x, 0, z) for x, z in FIREWOOD_SPOTS])};
    /** Lisière d'où sortent les élémentaires de glace, et les vagues de loups et de cultistes. */
    public static final double[][] ELEMENTAL_SPAWNS = {J.jpoints([(x, 0, z) for x, z in ELEMENTAL_SPAWNS])};
    public static final double[][] WAVE_SPAWNS = {J.jpoints([(x, 0, z) for x, z in WAVE_SPAWNS])};
    /** Mur de glace, rangée par rangée, du haut vers le bas (il fond dans cet ordre). */
    public static final int[][][] ICE_WALL = {wall_rows};
    public static final double[] WALL_CHECKPOINT = {J.jpoint((0, 0, -42))};

    /** Arène de la Source élémentaire. */
    public static final Box SOURCE_ARENA = {J.jbox(sx - SOURCE_RADIUS, sx + SOURCE_RADIUS, -1, 14, sz - SOURCE_RADIUS, sz + SOURCE_RADIUS - 2)};
    public static final double[] SOURCE = {J.jpoint(SOURCE_AT)};
    public static final int[][] BRAZIERS = {J.jblocks([(x, 0, z) for x, z in BRAZIERS])};
    public static final double BRAZIER_HEAT = {BRAZIER_HEAT};
    public static final int[][] HUT_PILES = {J.jblocks([(x, 0, z) for x, z in HUTS])};
    public static final int[] TORCH_RACK = {J.jblock(TORCH_RACK_AT)};
    public static final int[][] GATE_SOURCE = {J.jblocks(GATE_SOURCE)};

    /** Forêt sombre : lignes d'embuscade (z) et apparitions des cultistes de chacune. */
    public static final Box FOREST = {J.jbox(-30, 30, -1, 20, fz1, fz0)};
    public static final double[] FOREST_CHECKPOINT = {J.jpoint((path_x(-92), 0, -92))};
    public static final int[] AMBUSH_LINES = {{{ambush_lines}}};
    public static final double[][][] AMBUSH_SPAWNS = {ambush_spawns};

    /** Village du Chaman légendaire. */
    public static final Box VILLAGE = {J.jbox(vx - VILLAGE_RADIUS, vx + VILLAGE_RADIUS, -1, 14, vz - VILLAGE_RADIUS, vz + VILLAGE_RADIUS - 4)};
    public static final double[] VILLAGE_CENTER = {J.jpoint((vx, 0, vz))};
    public static final double VILLAGE_RADIUS = {VILLAGE_RADIUS};
    public static final int[][] VILLAGE_FIRES = {J.jblocks([(x, 0, z) for x, z in VILLAGE_FIRES])};
    public static final int[][] GATE_VILLAGE = {J.jblocks(GATE_VILLAGE)};
    public static final double[] VILLAGE_CHECKPOINT = {J.jpoint((0, 0, -163))};
    public static final double[] BALCONY = {J.jpoint(BALCONY)};
    public static final double[] EFFIGY = {J.jpoint(EFFIGY_AT)};
    public static final double[] SHAMAN = {J.jpoint(SHAMAN_AT)};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private SnowblindLayout() {{
    }}
}}
"""


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name in (BONFIRE, BONFIRE_OUT, BRAZIER, BRAZIER_OUT):
        return (255, 140, 50)
    if name in (PILE, TORCH_RACK):
        return (200, 150, 90)
    if name == FOOTPRINTS:
        return (120, 130, 160)
    if name == MIST:
        return (230, 140, 220)
    if name.startswith("Wood"):
        return (110, 80, 50)
    if name.startswith("Rock"):
        return (120, 124, 132)
    return (220, 226, 236)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, tex, base, accent, glyph, light, use, solid, alpha, opacity in blocks():
        fc.write_block(LANG, name, tex, base, accent, glyph, light, use, solid, alpha, opacity)
    img = footprint_texture(fc.COMMON / go.TEXTURES / "Footprints.png")
    go.icon(fc.COMMON / go.ICONS / "Footprints.png", img)
    for item_id, doc in items().items():
        fc.write_json(fc.OBJECTS / f"{item_id}.json", doc)
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Warmth.png", (255, 170, 80), "flame")
    snow_icon(fc.COMMON / fc.STATUS_ICONS / "Encased.png", (150, 210, 255))
    for tier in range(1, HYPOTHERMIA_TIERS + 1):
        snow_icon(fc.COMMON / fc.STATUS_ICONS / f"Hypothermia_{tier}.png", (150, 210, 255), tier)
    fc.write_json(fc.SERVER / f"Entity/Damage/{COLD_CAUSE}.json", cold_cause())
    fc.write_json(fc.SERVER / f"Entity/Damage/{FROST_CAUSE}.json", frost_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "Snowblind" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fc.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p = course_prefab()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    counts = fc.write_instance(INSTANCE, "Tempête de neige", PREFAB_DIR, sections, SPAWN, "#7a9a8a",
                               WEATHER, fc.weather("#6a7a90", "#d8e0ea", "#c8d4e0", (10, 120), 0.6, "#d8e0f0"), "17:30")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Tempête de neige : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules")
    if preview:
        fc.top_view(p, preview / "tempete_dessus.png", color_of)


if __name__ == "__main__":
    main()
