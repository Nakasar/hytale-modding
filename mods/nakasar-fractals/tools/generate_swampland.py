#!/usr/bin/env python3
"""Génère le Marais (Swampland), cinquième fractale de la saison 1 (étape 7 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_swampland.py [--preview DOSSIER]

Le déroulé de GW2 (wiki.guildwars2.com/wiki/Swampland_Fractal), dans l'ordre :

1. les feux-follets : ramener trois feux-follets dans leurs failles avant la fin du minuteur, lancé au premier
   ramassé (1 min 04 en Initié, 38 s en Adepte, 30 s au-delà). Dès qu'un feu-follet est pris, des murs surgissent
   entre les arbres : il faut sauter par-dessus ou contourner. Pièges au sol : fils tendus (renversent et estropient),
   pièges à loup, plaques à piques (dangereuses quand elles rougissent), œufs d'araignée. Des fusils revigorants près
   des failles accélèrent les alliés et ralentissent les ennemis. Raté : tout se remet en place, les feux-follets
   changent de place ;
2. le Moussu (The Mossman) : embuscade dans le passage, qui se ferme. Il invoque des loups, frappe fort, disparaît en
   furtivité puis surgit avec une attaque chargée de longue portée ; affaibli, il prend une forme sauvage (bonds, gros
   dégâts). Barre de défiance ;
3. Carnasse (Bloomhunger) : quatre failles en cercle, un feu-follet près de l'entrée à y déposer pour lancer le
   combat. Un cercle vert entoure une faille, rétrécit puis passe à la suivante (sens horaire) : Carnasse et ses
   esprits ne sont vulnérables que dedans, et il redonne de l'endurance. Charge, bond suivi du martèlement (défiance
   ouverte), pluie de poison, tir de poison. À 75 et 50 % : assaut d'esprits animaux, puis fleurs de poison. À 25 % :
   il se charge au centre, quatre feux-follets apparaissent aux coins, à rapporter avant la fin de sa charge, sinon
   la purge corporelle frappe tout le monde.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Swampland`, le feu-follet porté,
les blocs (failles, pièges, fusils), les effets, les particules, les modèles et rôles, la langue
`nakasar_fractals_swampland.lang` et `swampland/SwamplandLayout.java`. Repère comme la Falaise : y monde = GROUND_Y
+ y prefab, « debout à y » : le sol est en y - 1.
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

LANG = "nakasar_fractals_swampland"
GENERATOR = "generate_swampland.py"
INSTANCE = "Nakasar_Fractal_Swampland"
WEATHER = "Nakasar_Fractal_Weather_Swampland"
PREFAB_DIR = "Swampland"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/swampland/SwamplandLayout.java"
INTERACTIONS = go.INTERACTIONS / "Swampland"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/Swampland"

# --- blocs, objets et rôles ------------------------------------------------------------------------------
WISP = "Nakasar_Fractal_Wisp"                    # objet porté
WISP_BLOCK = "Nakasar_Fractal_Wisp_Light"        # feu-follet posé au sol (Utiliser : le prendre)
CLEFT = "Nakasar_Fractal_Wisp_Cleft"
CLEFT_LIT = "Nakasar_Fractal_Wisp_Cleft_Lit"
TRIPWIRE = "Nakasar_Fractal_Tripwire"
BEAR_TRAP = "Nakasar_Fractal_Bear_Trap"
SPIKE_PLATE = "Nakasar_Fractal_Spike_Plate"
SPIDER_EGGS = "Nakasar_Fractal_Spider_Eggs"
RACK = "Nakasar_Fractal_Invigorator_Rack"
MIST = gc.MIST_BARRIER
MOSSMAN = "Nakasar_Fractal_Mossman"
MOSSMAN_BEAST = "Nakasar_Fractal_Mossman_Beast"
MOSS_WOLF = "Nakasar_Fractal_Moss_Wolf"
BLOOMHUNGER = "Nakasar_Fractal_Bloomhunger"
# Esprits animaux de Carnasse : animaux vanilla en teintes spectrales (Kevin, 2026-10-24). animal : (modèle parent,
# échelle, vie, attaque vanilla, portée, variables d'interaction de l'attaque).
SPIRIT_PREFIX = "Nakasar_Fractal_Spirit_"
SPIRIT_ANIMALS = ["Wolf", "Fox", "Bear"]
SPIRITS = [SPIRIT_PREFIX + a for a in SPIRIT_ANIMALS]
BLOOM = "Nakasar_Fractal_Poison_Bloom"
FOE_ROLES = [MOSSMAN, MOSSMAN_BEAST, MOSS_WOLF, BLOOMHUNGER, BLOOM] + SPIRITS
PURGE_CAUSE = "Nakasar_Fractal_Purge"

GROUND = ["Soil_Mud", "Soil_Grass_Wet", "Soil_Mud", "Plant_Moss_Block_Green", "Soil_Grass_Deep", "Soil_Mud_Dry"]
UNDER = ["Soil_Dirt", "Soil_Mud", "Soil_Clay"]
ROCK = ["Rock_Stone_Mossy", "Rock_Stone_Mossy", "Rock_Stone", "Rock_Shale"]
TRUNK = "Wood_Sallow_Trunk"
LEAVES = "Plant_Leaves_Sallow"
DECO = ["Plant_Reeds_Marsh", "Plant_Grass_Wet_Tall", "Plant_Fern_Wet_Big", "Plant_Moss_Rug_Green", "Plant_Grass_Wet",
        "Plant_Reeds_Wet", "Plant_Crop_Mushroom_Glowing_Green", "Plant_Moss_Rug_Green_Dark"]
pick = fc.pick

# --- lieux (y = debout à) ---------------------------------------------------------------------------
SPAWN = (0, 0, 26)
SWAMP = (-38, 38, -40, 38)               # x0, x1, z0, z1
CLEFTS = [(-10, -35), (0, -37), (10, -35)]
WISP_SPOTS = [[(-33, 27), (-34, -14)], [(33, 27), (34, -14)], [(-13, 34), (13, 34)]]   # un feu-follet par groupe
WALLS = [(-30, -6, 20), (6, 30, 20), (-20, 20, 5), (-34, -10, -11), (10, 34, -11), (-22, 22, -24)]   # x0, x1, z
RACKS = [(-17, -34), (17, -34)]
GATE_SWAMP = [(x, y, -41) for x in range(-2, 3) for y in range(0, 5)]
PASSAGE = (-3, 3, -92, -42)             # x0, x1, z0 (nord), z1 (sud)
ROOM = (-9, 9, -84, -54)                # salle de l'embuscade du Moussu
AMBUSH_Z = -60                          # passer cette ligne déclenche l'embuscade
GATE_BEHIND = [(x, y, -51) for x in range(-2, 3) for y in range(0, 5)]
GATE_AHEAD = [(x, y, -86) for x in range(-2, 3) for y in range(0, 5)]
MOSSMAN_AT = (0, 0, -76)
POCKET = (16, -14, -68)                 # cachette fermée dans la falaise : la furtivité du Moussu
CL_CENTER = (0, -116)
CL_RADIUS = 20
CL_CLEFTS = [(0, -129), (13, -116), (0, -103), (-13, -116)]   # N, E, S, O : sens horaire
CL_WISP = (3, -99)
CL_CORNERS = [(12, -128), (12, -104), (-12, -104), (-12, -128)]
REWARD_AT = (-2, 0, -112)
END_EXIT_AT = (2, 0, -112)


def traps():
    """Pièges (x, z, sorte) le long des routes des feux-follets vers les failles : 30, 55 et 80 % du trajet, en
    décalant d'un bloc de côté une fois sur deux ; jamais sur un mur ni au pied d'une faille."""
    kinds = [TRIPWIRE, BEAR_TRAP, SPIKE_PLATE, SPIDER_EGGS]
    out, k = [], 0
    for group, (cx, cz) in zip(WISP_SPOTS, CLEFTS):
        for sx, sz in group:
            for t in (0.3, 0.55, 0.8):
                x = round(sx + (cx - sx) * t) + (1 if k % 2 else -1)
                z = round(sz + (cz - sz) * t)
                if any(z == wz and x0 <= x <= x1 for x0, x1, wz in WALLS):
                    z += 2
                out.append((x, z, kinds[k % len(kinds)]))
                k += 1
    return out


def trees():
    """Arbres du marais : grille décalée de 9 blocs, loin des feux-follets, des failles, des murs et du départ."""
    keep = [p for g in WISP_SPOTS for p in g] + CLEFTS + RACKS + [(SPAWN[0], SPAWN[2])]
    out = []
    for gx in range(-33, 34, 9):
        for gz in range(-30, 35, 9):
            x = gx + (gz * 7 % 5) - 2
            z = gz + (gx * 3 % 5) - 2
            if any(math.hypot(x - a, z - b) < 5 for a, b in keep):
                continue
            if any(abs(z - wz) <= 1 and x0 - 1 <= x <= x1 + 1 for x0, x1, wz in WALLS):
                continue
            if abs(x) <= 4 and z < -30:
                continue
            out.append((x, z, 6 + (x * 5 + z) % 3))
    return out


TRAPS = traps()
TREES = trees()


def tree(p, x, z, h):
    """Saule du marais (feuillage sallow ou windwillow) dont les lianes pendent, pied au sol (y = 0)."""
    fn.broadleaf(p, x, 0, z, h, "sallow" if (x + z) % 3 else "windwillow", seed=x * 7 + z, droop=0.16,
                 hanging=THEME["hang"])


THEME = fn.THEMES["swamp"]


def course_prefab():
    p = go.Prefab()
    x0, x1, z0, z1 = SWAMP
    # Marais : sol de boue et de mousse, bords rocheux et boisés.
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = min(x - x0, x1 - x, z - z0, z1 - z)
            p.set(x, -1, z, pick(GROUND, x, -1, z))
            for y in range(-4, -1):
                p.set(x, y, z, pick(UNDER, x, y, z))
            if edge == 0 and not (z == z0 and abs(x) <= 2):
                for y in range(0, 6 + (x * 3 + z) % 3):
                    p.set(x, y, z, pick(ROCK, x, y, z))
            elif edge > 1 and (x * 31 + z * 17) % 11 == 0:
                p.set(x, 0, z, pick(DECO, x, 0, z))
    for x, z, h in TREES:
        tree(p, x, z, h)
    for x, z in CLEFTS:
        p.set(x, 0, z, CLEFT)
        p.set(x, -1, z, "Rock_Stone_Mossy")
    for x, z in RACKS:
        p.set(x, 0, z, RACK)
    for x, z, kind in TRAPS:
        p.set(x, -1, z, kind)
    for (x, y, z) in GATE_SWAMP:
        p.set(x, y, z, MIST)
    # Passage vers le nord, et la salle de l'embuscade.
    px0, px1, pz0, pz1 = PASSAGE
    rx0, rx1, rz0, rz1 = ROOM
    for z in range(pz0, pz1 + 1):
        wide = rz0 <= z <= rz1
        a, b = (rx0, rx1) if wide else (px0, px1)
        for x in range(a - 1, b + 2):
            p.set(x, -1, z, pick(GROUND, x, -1, z))
            for y in range(-4, -1):
                p.set(x, y, z, pick(UNDER, x, y, z))
            if x in (a - 1, b + 1):
                for y in range(0, 7):
                    p.set(x, y, z, pick(ROCK, x, y, z))
    for x in range(rx0 - 1, rx1 + 2):   # fond et entrée de la salle
        for z in (rz0 - 1, rz1 + 1):
            if abs(x) > 3:
                for y in range(0, 7):
                    p.set(x, y, z, pick(ROCK, x, y, z))
    for x, z in ((rx0 + 1, rz0 + 1), (rx1 - 1, rz0 + 1), (rx0 + 1, rz1 - 1), (rx1 - 1, rz1 - 1)):
        tree(p, x, z, 5)
    for (x, y, z) in GATE_BEHIND + GATE_AHEAD:
        p.set(x, y, z, go.AIR)
    # Cachette du Moussu : une boîte fermée sous le marais.
    cx, cy, cz = POCKET
    for x in range(cx - 2, cx + 3):
        for y in range(cy - 1, cy + 4):
            for z in range(cz - 2, cz + 3):
                inside = abs(x - cx) <= 1 and abs(z - cz) <= 1 and cy <= y <= cy + 2
                p.set(x, y, z, go.AIR if inside else "Rock_Stone")
    # Clairière de Carnasse.
    ax, az = CL_CENTER
    fc.disc(p, ax, az, CL_RADIUS, 0, lambda x, z: pick(GROUND, x, -1, z), UNDER, 4)
    for a in range(0, 360, 6):
        x = round(ax + math.cos(math.radians(a)) * (CL_RADIUS + 1))
        z = round(az + math.sin(math.radians(a)) * (CL_RADIUS + 1))
        if abs(x - ax) <= 3 and z > az:
            continue   # entrée au sud
        for y in range(-1, 8):
            p.set(x, y, z, pick(ROCK, x, y, z))
    for a in range(15, 360, 40):
        x = round(ax + math.cos(math.radians(a)) * (CL_RADIUS - 2))
        z = round(az + math.sin(math.radians(a)) * (CL_RADIUS - 2))
        if abs(x - ax) > 4 or z < az:
            tree(p, x, z, 7)
    for x, z in CL_CLEFTS:
        p.set(x, 0, z, CLEFT)
        p.set(x, -1, z, "Rock_Stone_Mossy")
    for z in range(az + CL_RADIUS - 2, pz0 + 1):   # raccord passage → clairière
        for x in range(-4, 5):
            p.set(x, -1, z, pick(GROUND, x, -1, z))
            for y in range(0, 5):
                p.set(x, y, z, go.AIR)
    dress(p)
    stumps(p)
    return p


# Feux-follets posés sur une souche (Kevin, 2026-10-24) : on voit de loin où le prendre. Souche de saule des marais
# (tronc vanilla, cernes sur le dessus) sur le sol, le feu-follet un bloc plus haut ; racines au pied si la place est libre.
WISP_Y = 1
STUMP = "Wood_Sallow_Trunk"
STUMP_ROOTS = "Wood_Sallow_Roots"


def stumps(p):
    for k, (x, z) in enumerate([q for g in WISP_SPOTS for q in g] + [CL_WISP] + CL_CORNERS):
        for y in range(0, WISP_Y):
            p.set(x, y, z, STUMP)
        p.set(x, WISP_Y, z, go.AIR)
        for i, (dx, dz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
            if (k + i) % 2 == 0 and not p.solid_at(x + dx, 0, z + dz):
                p.set(x + dx, 0, z + dz, STUMP_ROOTS)


def cliffs(p, cells, low, high, seed):
    """Falaises moussues autour du marais : dessus irrégulier entre `low` et `high`, arbres et lianes."""
    tops = {(x, z): low + round((high - low) * (fn.fbm2(x, z, 8, 3, seed) + 1) / 2) for (x, z) in cells}
    inland = fn.edge_distance(tops)
    # la cachette du Moussu reste enfouie dans la roche
    deep = lambda x, z: 22 if abs(x - POCKET[0]) <= 5 and abs(z - POCKET[2]) <= 5 else 6
    ground = fn.island(p, tops, lambda x, z: tops[(x, z)] + deep(x, z) + min(12, inland[(x, z)] * 1.5), seed,
                       hang=0.3, theme=THEME)
    fn.dress(p, ground, THEME, seed, trees=0.05, spacing=6, bushes=0.06, boulders=0.006, density=0.6, flowers=0.1)


def dress(p):
    """Herbes, roseaux et champignons sur le sol du marais (jamais sur un piège, une ligne de mur, une faille ni un
    feu-follet), falaises moussues et boisées autour du marais, du passage et de la clairière, îlots de marais au
    loin."""
    keep = set()
    for x, z, _ in TRAPS:
        keep |= {(x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
    for x0, x1, wz in WALLS:
        keep |= {(x, wz) for x in range(x0, x1 + 1)}
    for x, z in [q for g in WISP_SPOTS for q in g] + CLEFTS + RACKS + CL_CLEFTS + [CL_WISP] + CL_CORNERS:
        keep |= {(x + dx, z + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
    keep |= {(x, z) for x in range(-3, 4) for z in range(SPAWN[2] - 3, SPAWN[2] + 4)}
    ground = [(x, -1, z) for (x, y, z), (name, _) in list(p.blocks.items())
              if y == -1 and (x, z) not in keep and name in GROUND]
    fn.flora(p, ground, seed=71, density=0.45, flowers=0.12, theme=THEME)
    # Falaises tout autour du sol du parcours (marais, passage, salle, clairière), loin de la cachette du Moussu.
    footprint = {(x, z): -1 for (x, y, z) in p.blocks if y == -1}
    ring = set(fn.rim(footprint, 5, 12, seed=73))
    ring |= {(x, z) for x in range(POCKET[0] - 5, POCKET[0] + 6) for z in range(POCKET[2] - 5, POCKET[2] + 6)
             if (x, z) not in footprint}
    cliffs(p, ring, 6, 14, 75)
    fn.scatter_islets(p, (-110, 110, -200, 100), 20, (-30, 12), (3, 9), THEME, seed=77)


# --- objets, blocs, effets, particules ------------------------------------------------------------------

def wisp_parts():
    core, light = (150, 255, 210), (240, 255, 250)
    return [("Core", (0, 6, 0), (6, 6, 6), 0, fm.crystal(core, light), "fullbright"),
            ("Halo", (0, 6, 0), (9, 2, 9), 45, fm.crystal((90, 220, 190), light), "fullbright")]


def wisp_item():
    return fc.held_item(LANG, WISP, "Wisp", wisp_parts(), 81, (0, 6, 0), 14.0, quality="Rare", stack=1,
                        extra={"Categories": ["Items.Misc"], "Light": {"Color": "#9fd", "Radius": 4}})


def blocks():
    """(id, texture, fond, couleur, glyphe, lumière, action, plein, alpha, opacité)."""
    use = lambda action: f"Nakasar_Fractal_Use_{action}"
    return [
        (WISP_BLOCK, "Wisp_Light", (120, 230, 200), (240, 255, 250), "rune", "#9fd", use("Swampland_Wisp"), True, 255, None),
        (CLEFT, "Wisp_Cleft", (60, 70, 60), (140, 220, 190), "rune", None, use("Swampland_Cleft"), True, 255, None),
        (CLEFT_LIT, "Wisp_Cleft_Lit", (60, 90, 80), (200, 255, 230), "rune", "#9fd", use("Swampland_Cleft"), True, 255, None),
        (TRIPWIRE, "Tripwire", (92, 76, 52), (110, 190, 255), "glimmer", None, None, True, 255, None),
        (BEAR_TRAP, "Bear_Trap", (86, 74, 56), (170, 170, 176), "cracks", None, None, True, 255, None),
        (SPIKE_PLATE, "Spike_Plate", (80, 66, 60), (200, 90, 80), "pylon", None, None, True, 255, None),
        (SPIDER_EGGS, "Spider_Eggs", (88, 80, 60), (230, 226, 200), "battery", None, None, True, 255, None),
        (RACK, "Invigorator_Rack", (90, 70, 50), (255, 210, 120), "console", "#fc8", use("Swampland_Rack"), True, 255, None),
    ]


def purge_cause():
    return fc.cause("Purge corporelle de Carnasse (feux-follets non rapportés à temps) : une part des PV max, l'armure ne "
                    "la réduit pas.", "#a8ff60")


def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Swiftness": fc.effect(
            L, "Nakasar_Fractal_Swiftness", "Rapidité (fusil revigorant du Marais) : course plus rapide.", "Haste", 8,
            ApplicationEffects={"HorizontalSpeedMultiplier": 1.33, "EntityTopTint": "#ffe08a"}),
        "Nakasar_Fractal_Crippled": fc.effect(
            L, "Nakasar_Fractal_Crippled", "Estropié (fil tendu, fusil revigorant) : déplacement ralenti.", "Crippled", 3,
            debuff=True, ApplicationEffects={"HorizontalSpeedMultiplier": 0.6, "EntityBottomTint": "#6a5a40"}),
        "Nakasar_Fractal_Bear_Trapped": fc.effect(
            L, "Nakasar_Fractal_Bear_Trapped", "Pris dans un piège à loup : immobile.", "Rooted", 2.5, debuff=True,
            ApplicationEffects={"MovementEffects": {"DisableAll": True}}),
        "Nakasar_Fractal_Wisp_Vigor": fc.effect(
            L, "Nakasar_Fractal_Wisp_Vigor", "Vigueur du feu-follet : dans le cercle vert de Carnasse, l'endurance "
            "revient vite (Java).", "Wisp_Vigor", 1.5, ApplicationEffects={"EntityBottomTint": "#7dffb0"}),
    }


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Wisp_Glow": ("Feu-follet : lueur verte qui monte.",
                                  [("Glow", S("#f0fff8", "#60ffc0", 8, (0.3, 0.8), (60, 90), 0.4, 1.2), 0.5)]),
    "Nakasar_Fractal_Wisp_Ring": ("Cercle vert de Carnasse : lueurs vertes posées au sol (zone favorable).",
                                  [("Ring", S("#d0ffe0", "#30e070", 6, (0.6, 1.2), (80, 90), 0.2, 0.9,
                                              life=(0.6, 0.9), size=(0.35, 0.55)), 0.1)]),
    "Nakasar_Fractal_Wall_Rise": ("Un mur surgit entre les arbres : terre et racines.",
                                  [("Dirt", S("#a08060", "#3a2a18", 10, (1.0, 2.5), (40, 90), 0.8, 0.4,
                                              life=(0.4, 0.7), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Trap_Snap": ("Un piège se déclenche : éclats et poussière.",
                                  [("Snap", S("#e0d0b0", "#5a4a30", 14, (1.0, 2.5), (20, 90), 0.6, 0.3,
                                              life=(0.3, 0.5), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Egg_Burst": ("Œufs d'araignée qui éclatent : nuage de poison.",
                                  [("Cloud", S("#d0ff80", "#3a6a10", 18, (0.5, 1.5), (0, 90), 1.6, 0.8,
                                               life=(0.8, 1.2), blend="BlendLinear"), 0.4)]),
    "Nakasar_Fractal_Invigorate": ("Fusil revigorant : étincelles dorées.",
                                   [("Sparks", S("#fff0c0", "#ffb040", 16, (1.0, 3.0), (-90, 90), 1.0, 1.2,
                                                 life=(0.3, 0.6)), 1.0)]),
    "Nakasar_Fractal_Stealth_Smoke": ("Le Moussu disparaît ou surgit : fumée verte.",
                                      [("Smoke", S("#a0c090", "#203018", 24, (0.6, 1.6), (-20, 90), 1.4, 2.0,
                                                   life=(0.8, 1.4), blend="BlendLinear"), 0.8)]),
    "Nakasar_Fractal_Bloom_Pulse": ("Fleur de poison : bouffée verte autour d'elle.",
                                    [("Puff", S("#d0ff90", "#407010", 14, (0.6, 1.4), (0, 60), 2.8, 0.6,
                                                life=(0.8, 1.2), blend="BlendLinear"), 0.4)]),
    "Nakasar_Fractal_Bloom_Charge": ("Carnasse se charge au centre : spirale verte.",
                                     [("Spiral", S("#e0ffd0", "#40c040", 24, (1.0, 2.5), (-10, 90), 1.8, 3.0,
                                                   life=(0.6, 1.0)), 1.0)]),
    "Nakasar_Fractal_Purge": ("Purge corporelle de Carnasse : onde verte sur toute la clairière.",
                              [("Wave", S("#f0ffe0", "#40ff40", 60, (6.0, 12.0), (0, 30), 4.0, 1.0,
                                          life=(0.6, 1.0)), 0.5)]),
}


# --- modèles ----------------------------------------------------------------------------------------------

def bite(start, start_anims, damage_parent, damage, knockback):
    """Variables d'une morsure vanilla (Wolf_White, Fox) : animation de départ et dégâts."""
    return {"Melee_Start": {"Interactions": [{"Parent": start, "Effects": {"ItemPlayerAnimationsId": start_anims,
                                                                           "ItemAnimationId": "Bite"}, "RunTime": 0.167}]},
            "Bite_Damage": {"Interactions": [{"Parent": damage_parent, "DamageCalculator": {
                "Type": "Absolute", "BaseDamage": {"Physical": damage}, "RandomPercentageModifier": 0.1},
                "DamageEffects": {"Knockback": {"Force": knockback}}}]}}


def swipes(damage):
    """Variables des coups du grizzly vanilla (Root_NPC_Bear_Grizzly_Attack) : dégâts, recul faible."""
    return {f"{v}_Damage": {"Interactions": [{"Parent": f"Bear_Grizzly_{v}_Damage", "DamageCalculator": {
        "Type": "Absolute", "BaseDamage": {"Physical": damage}, "RandomPercentageModifier": 0.1},
        "DamageEffects": {"Knockback": {"Force": 0.5}}}]} for v in ("Swipe_Left", "Swipe_Right", "Stomp")}


# Attaques vanilla des animaux (lues dans Assets.zip 0.7.2, rôles Wolf_White, Fox, Bear_Grizzly) : nos coups en boîtes
# ne touchaient pas toujours (même leçon que les colosses de l'Océan solide).
WILD = {
    "Wolf": ("Wolf_Black", 0.9, 70, "Root_NPC_Wolf_Attack", 2.5, bite("Wolf_Bite", "Wolf_Black_Default", "Wolf_Bite_Damage", 8, 1)),
    "Fox": ("Fox", 1.1, 55, "Root_NPC_Fox_Attack", 2.5, bite("Fox_Bite", "Fox_Default", "Fox_Bite_Damage", 7, 0.5)),
    "Bear": ("Bear_Grizzly", 0.9, 90, "Root_NPC_Bear_Grizzly_Attack", 3.25, swipes(12)),
}

def wolf_parts(body, dark, eye, glow=False):
    """Loup en boîtes : loup de givre de la Tempête de neige (generate_snowblind)."""
    shade = "fullbright" if glow else "flat"
    paint = fm.crystal(body, (230, 255, 250)) if glow else fm.smooth(body)
    return [("Body", (0, 26, 0), (18, 16, 38), 0, paint, shade),
            ("Head", (0, 34, 24), (14, 13, 14), 0, paint, shade),
            ("Snout", (0, 30, 33), (7, 6, 8), 0, fm.smooth(dark), shade),
            ("Ear_L", (-4, 43, 22), (3, 6, 3), 0, fm.smooth(dark), shade),
            ("Ear_R", (4, 43, 22), (3, 6, 3), 0, fm.smooth(dark), shade),
            ("Eyes", (0, 36, 31.5), (10, 2, 1), 0, fm.crystal(eye, (255, 255, 255)), "fullbright"),
            ("Tail", (0, 30, -24), (5, 5, 14), 0, paint, shade)] + [
        (f"Leg_{k}", (x, 9, z), (5, 18, 5), 0, fm.smooth(dark), shade)
        for k, (x, z) in enumerate(((-6, 12), (6, 12), (-6, -12), (6, -12)))]


def bloom_parts():
    stem, petal, heart = (60, 120, 40), (170, 220, 70), (220, 255, 120)
    parts = [("Stem", (0, 14, 0), (6, 28, 6), 0, fm.smooth(stem), "flat"),
             ("Heart", (0, 32, 0), (10, 8, 10), 0, fm.crystal((120, 180, 30), heart), "fullbright")]
    for k in range(5):
        a = math.radians(k * 72)
        parts.append((f"Petal_{k}", (math.cos(a) * 9, 30, math.sin(a) * 9), (10, 3, 6), k * 72 + 90,
                      fm.smooth(petal), "flat"))
    return parts


def models():
    m = {}
    hood = ("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png")
    norn = [hood,
            ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png", gc.CLOTH, "Green"),
            ("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Brown"),
            ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
             "Faded_Leather", "Brown"),
            ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Brown")]
    m[MOSSMAN] = fr.humanoid("Le Moussu (boss du Marais, provisoire) : norn géant (× 1,35), capuche et cape de mousse.",
                             "07", "Face_Scar", norn, scale=(1.35, 1.35))
    m[MOSSMAN_BEAST] = fr.humanoid("Le Moussu, forme sauvage (provisoire) : encore plus grand (× 1,55), yeux rouges ; GW2 "
                                   "en fait une bête des esprits du Sauvage (ours, loup, léopard, corbeau).", "07",
                                   "Face_Scar", norn, scale=(1.55, 1.55), light={"Color": "#f44", "Radius": 2})
    m[MOSS_WOLF] = {"$Comment": "Loup du Moussu : le loup noir vanilla (modèle et animations du jeu).",
                    "Parent": "Wolf_Black", "MinScale": 0.9, "MaxScale": 0.9}
    for animal in SPIRIT_ANIMALS:
        parent, scale = WILD[animal][:2]
        m[SPIRIT_PREFIX + animal] = {
            "$Comment": f"Esprit animal de Carnasse : {parent} vanilla (modèle et animations du jeu), texture spectrale "
                        "vert d'eau translucide (tools/generate_spirit_textures.py).",
            "Parent": parent, "Texture": f"{fc.NPC_MODELS}/Spirits/{animal}.png", "MinScale": scale, "MaxScale": scale,
            "Light": {"Color": "#9fd", "Radius": 2}}
    m[BLOOMHUNGER] = {"$Comment": "Carnasse (boss du Marais) : l'esprit de racine vanilla, très grand ; GW2 en fait un "
                                  "tréant des esprits.", "Parent": "Spirit_Root", "MinScale": 2.4, "MaxScale": 2.4,
                      "Light": {"Color": "#9f6", "Radius": 5}}
    m[BLOOM] = fc.character_model("Poison_Bloom", bloom_parts(), 84, "Fleur de poison (après les assauts de Carnasse) : "
                                  "PNJ fixe qui empoisonne autour d'elle et protège les ennemis proches (Java).", 0.6,
                                  (0.4, 0.8), light={"Color": "#bf6", "Radius": 2}, scale=1.4)
    return m


# --- attaques et rôles ------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
ROOT_ANIMS = "Spirit_Root_Default"


def bh_pose(seconds):
    return {"Type": "Simple", "RunTime": seconds, "Effects": {"ItemPlayerAnimationsId": ROOT_ANIMS,
                                                             "ItemAnimationId": "SporeGas",
                                                             "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}}


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Mossman_Slice"] = {
        "$Comment": "Le Moussu au contact : deux entailles (16 dégâts chacune).",
        "Type": "Serial", "Interactions": [fr.swing("Entaille gauche.", "Mace", "SwingLeft", 0.35, 16, end=3.2),
                                           fr.swing("Entaille droite.", "Mace", "SwingRight", 0.35, 16, end=3.2,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Mossman_Gouge"] = {
        "$Comment": "Le Moussu : éventration, ligne de 5 × 2 blocs (1,2 s), 38 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Line", 1.2, Length=5, Width=2, Damage=38, PlayersOnly=True,
                                                     HitParticle="Impact_Sword_Basic_Stronk",
                                                     ImpactSound="SFX_Mace_T2_Signature_Impact"),
                                           fc.windup(1.2, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    out["Nakasar_Fractal_Mossman_Dagger"] = {
        "$Comment": "Le Moussu : dague dansante, sa cible est marquée (1,3 s) puis touchée où qu'elle soit (14 dégâts) ; "
                    "elle rebondit sur deux joueurs proches. Agonie aux niveaux qui en ont.",
        "Type": "Serial", "Interactions": [T("Mark", 1.3, Damage=14, PlayersOnly=True, MarkParticle="Nakasar_Fractal_Trap_Snap",
                                             HitParticle="Impact_Sword_Basic_Stronk", Bounces=2, BounceRange=8,
                                             AgonySeconds=3),
                                           fc.windup(1.3, "SFX_Unarmed_Swing", "Mace", "SwingRight")]}
    out["Nakasar_Fractal_Mossman_Leap"] = {
        "$Comment": "Le Moussu, forme sauvage : bond sur sa cible, cercle rouge de 3,5 blocs (1,3 s), 40 dégâts et "
                    "étourdissement 1,5 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.3, Anchor="Target", Radius=3.5, Damage=40,
                                                     TeleportCaster=True, EffectId="Hazard_Electric_Stun",
                                                     EffectDuration=1.5, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.3, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Mossman_Maul"] = {
        "$Comment": "Le Moussu, forme sauvage, au contact : deux coups de griffes (24 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Griffe gauche.", "Mace", "SwingLeft", 0.3, 24, end=3.4),
                                           fr.swing("Griffe droite.", "Mace", "SwingRight", 0.3, 24, end=3.4,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Wolf_Bite"] = {
        "$Comment": "Morsure en boîte (8 dégâts) : loup de givre de la Tempête de neige (generate_snowblind) ; les loups "
                    "et esprits du Marais mordent comme les animaux vanilla.",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.3, 8, end=2.2, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Bloomhunger_Jab"] = {
        "$Comment": "Carnasse au contact : coup et revers (20 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup.", ROOT_ANIMS, "SporeGas", 0.45, 20, end=4.0),
                                           fr.swing("Revers.", ROOT_ANIMS, "SporeGas", 0.45, 20, end=4.0,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Bloomhunger_Charge"] = {
        "$Comment": "Carnasse : se cabre puis fonce sur sa cible, ligne rouge de 16 × 3 blocs (1,5 s), 32 dégâts et "
                    "projection ; il s'arrête au bout.",
        "Type": "Serial", "Interactions": [CI, RF, {"Type": "Nakasar_Fractal_Charge", "Length": 16, "Width": 3,
                                                     "Seconds": 1.5, "Speed": 14, "Damage": 32, "Knockback": 8,
                                                     "StunSeconds": 2.0, "StunEffect": "Nakasar_Fractal_Stunned",
                                                     "ImpactSound": "SFX_Goblin_Feastmaster_Slam"},
                                           bh_pose(1.5)]}
    out["Nakasar_Fractal_Bloomhunger_Leap"] = {
        "$Comment": "Carnasse : bond sur sa cible, grand cercle rouge de 5 blocs (1,7 s), 30 dégâts et projection ; "
                    "aussitôt après, le martèlement : défiance ouverte, cercle de 7 blocs (2,4 s), 36 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.7, Anchor="Target", Radius=5, Damage=30,
                                                     TeleportCaster=True, Knockback=6, KnockUp=3, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           bh_pose(1.7),
                                           {"Type": "Nakasar_Fractal_OpenDefiance", "Seconds": 2.6},
                                           T("Circle", 2.4, Radius=7, Damage=36, Knockback=4, KnockUp=2,
                                             ImpactParticle="Stick_Slam_Ground_Large",
                                             ImpactSound="SFX_Mace_T2_Signature_Impact"),
                                           bh_pose(2.4)]}
    out["Nakasar_Fractal_Bloomhunger_Rain"] = {
        "$Comment": "Carnasse : pluie de poison, 7 cercles rouges de 2,2 blocs autour de lui (1,6 s), 14 dégâts et "
                    "poison.",
        "Type": "Serial", "Interactions": [T("Circle", 1.6, Anchor="Scatter", Count=7, OffsetMin=3, OffsetMax=13,
                                             Radius=2.2, Damage=14, EffectId="Poison_T2", EffectDuration=4,
                                             PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Egg_Burst"),
                                           bh_pose(1.6)]}
    out["Nakasar_Fractal_Bloomhunger_Shoot"] = {
        "$Comment": "Carnasse : tir de poison sur sa cible, cercle rouge de 2,6 blocs (1,3 s), 18 dégâts et poison.",
        "Type": "Serial", "Interactions": [T("Circle", 1.3, Anchor="Target", Radius=2.6, Damage=18, EffectId="Poison_T1",
                                             EffectDuration=5, PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Egg_Burst"),
                                           bh_pose(1.3)]}
    for action, comment in (("Swampland_Wisp", "Feu-follet du Marais : le prendre."),
                            ("Swampland_Cleft", "Faille du Marais : y déposer le feu-follet porté."),
                            ("Swampland_Rack", "Fusil revigorant : accélère les alliés et ralentit les ennemis proches.")):
        out[f"Nakasar_Fractal_Use_{action}"] = fc.use_interaction(action, comment)
    return out


MELEE = ["Mossman_Slice", "Mossman_Gouge", "Mossman_Leap", "Mossman_Maul", "Wolf_Bite", "Bloomhunger_Jab",
         "Bloomhunger_Charge", "Bloomhunger_Leap"]
RANGED = ["Mossman_Dagger", "Bloomhunger_Rain", "Bloomhunger_Shoot"]
R = fc.root


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[MOSSMAN] = fr.role(
        MOSSMAN, "Le Moussu, barre de boss et de défiance : entailles, éventration annoncée, dague dansante. Ses loups, "
        "sa furtivité, son attaque surgie et sa forme sauvage sont menés par le Java (swampland.Mossman).", MOSSMAN,
        n(MOSSMAN), 2800,
        [fr.timed_attack("Gouge", R("Mossman_Gouge"), rng=4.5, los=True, comment="Éventration annoncée."),
         fr.timed_attack("Dagger", R("Mossman_Dagger"), rng=20, los=True, comment="Dague dansante."),
         fr.melee(R("Mossman_Slice"), 2.8, (0.7, 1.1)), fr.chase(30, stop=2.0)],
        fr.walk(4.0), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Gouge", (3, 5), (8, 11)), fr.timer("Dagger", (2, 4), (7, 9))],
        HotbarItems=["Weapon_Sword_Steel_Rusty"], KnockbackScale=0.2, DeathAnimationTime=2.0)
    out[MOSSMAN_BEAST] = fr.role(
        MOSSMAN_BEAST, "Le Moussu sous sa forme sauvage (sous 50 %) : bonds annoncés et griffes, gros dégâts.",
        MOSSMAN_BEAST, n(MOSSMAN_BEAST), 2800,
        [fr.timed_attack("Leap", R("Mossman_Leap"), rng=18, los=True, comment="Bond annoncé."),
         fr.melee(R("Mossman_Maul"), 3.0, (0.6, 1.0)), fr.chase(34, stop=2.2)],
        fr.walk(5.0), GENERATOR, sight=34, leash=40, home=False,
        timers=[fr.timer("Leap", (1, 3), (6, 8))], KnockbackScale=0.1, DeathAnimationTime=2.0)
    _, _, _, attack, reach, wolf_vars = WILD["Wolf"]
    out[MOSS_WOLF] = fr.role(
        MOSS_WOLF, "Loup du Moussu : appelé par lui, fonce et mord (morsure du loup vanilla, 8 dégâts).", MOSS_WOLF,
        n(MOSS_WOLF), 80, [fr.melee(attack, reach, (0.7, 1.1)), fr.chase(36, stop=1.4)],
        fr.walk(5.2), GENERATOR, sight=30, leash=40, home=False, KnockbackScale=0.8, DeathAnimationTime=0.8,
        InteractionVars=wolf_vars)
    for animal in SPIRIT_ANIMALS:
        _, _, hp, attack, reach, variables = WILD[animal]
        role = SPIRIT_PREFIX + animal
        out[role] = fr.role(
            role, "Esprit animal de Carnasse : invulnérable hors du cercle vert (Java), fonce et attaque comme l'animal "
            "vanilla.", role, n(role), hp, [fr.melee(attack, reach, (0.7, 1.1)), fr.chase(40, stop=1.4)],
            fr.walk(5.0), GENERATOR, sight=40, leash=44, home=False, KnockbackScale=0.8, DeathAnimationTime=0.8,
            InteractionVars=variables)
    out[BLOOMHUNGER] = fr.role(
        BLOOMHUNGER, "Carnasse, barre de boss et de défiance : coup et revers, charge, bond suivi du martèlement, pluie de "
        "poison, tir de poison. Le cercle vert, les assauts d'esprits, les fleurs de poison et les feux-follets à 25 % "
        "sont menés par le Java (swampland.Bloomhunger).", BLOOMHUNGER, n(BLOOMHUNGER), 5000,
        [fr.timed_attack("Leap", R("Bloomhunger_Leap"), rng=22, los=True, comment="Bond puis martèlement."),
         fr.timed_attack("Charge", R("Bloomhunger_Charge"), rng=16, los=True, comment="Charge."),
         fr.timed_attack("Rain", R("Bloomhunger_Rain"), rng=24, comment="Pluie de poison."),
         fr.timed_attack("Shoot", R("Bloomhunger_Shoot"), rng=22, los=True, comment="Tir de poison."),
         fr.melee(R("Bloomhunger_Jab"), 4.2, (1.0, 1.4)), fr.chase(40, stop=3.2)],
        fr.walk(3.4), GENERATOR, sight=40, leash=44, home=False,
        timers=[fr.timer("Leap", (2, 4), (16, 20)), fr.timer("Charge", (7, 9), (13, 16)),
                fr.timer("Rain", (10, 12), (14, 18)), fr.timer("Shoot", (4, 6), (7, 9))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[BLOOM] = fc.static_role(LANG, BLOOM, "Fleur de poison : ne bouge pas ; le Java empoisonne autour d'elle et protège "
                                "les ennemis proches.", GENERATOR, 120)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(WISP, "Feu-follet", "À rapporter dans une faille (Utiliser la faille).", "Wisp",
           "Bring it back to a cleft (use the cleft).")
    t.item(WISP_BLOCK, "Feu-follet", "Utiliser : le prendre.", "Wisp", "Use: pick it up.")
    t.item(CLEFT, "Faille des feux-follets", "Utiliser avec un feu-follet : l'y déposer.", "Wisp cleft",
           "Use while carrying a wisp: put it in.")
    t.item(CLEFT_LIT, "Faille illuminée", "Un feu-follet y brille.", "Lit cleft", "A wisp shines inside.")
    t.item(TRIPWIRE, "Fil tendu", "Renverse et estropie qui marche dessus.", "Tripwire", "Knocks down and cripples.")
    t.item(BEAR_TRAP, "Piège à loup", "Immobilise et blesse qui marche dessus.", "Bear trap", "Roots and wounds.")
    t.item(SPIKE_PLATE, "Plaque à piques", "Dangereuse quand elle rougit.", "Spike plate", "Dangerous when it glows red.")
    t.item(SPIDER_EGGS, "Œufs d'araignée", "Éclatent en nuage de poison.", "Spider eggs", "Burst into a poison cloud.")
    t.item(RACK, "Fusil revigorant", "Utiliser : accélère les alliés et ralentit les ennemis proches.", "Invigorator rifle",
           "Use: speeds up nearby allies and slows nearby foes.")
    for role, f, e in ((MOSSMAN, "Le Moussu", "The Mossman"), (MOSSMAN_BEAST, "Le Moussu (forme sauvage)", "The Mossman (wild form)"),
                       (MOSS_WOLF, "Loup du Moussu", "Mossman's wolf"), (BLOOMHUNGER, "Carnasse", "Bloomhunger"),
                       (SPIRITS[0], "Esprit du loup", "Wolf spirit"), (SPIRITS[1], "Esprit du renard", "Fox spirit"),
                       (SPIRITS[2], "Esprit de l'ours", "Bear spirit"), (BLOOM, "Fleur de poison", "Poison bloom")):
        t.npc(role, f, e)
    for eff, f, e in (("Swiftness", "Rapidité", "Swiftness"), ("Crippled", "Estropié", "Crippled"),
                      ("Bear_Trapped", "Pris au piège", "Trapped"), ("Wisp_Vigor", "Vigueur du feu-follet", "Wisp vigor")):
        t.put(f"effects.Nakasar_Fractal_{eff}", f, e)
    msgs = {
        "intro": ("Marais : ramenez les trois feux-follets dans leurs failles, au nord. Le minuteur part au premier pris : "
                  "{seconds} s.", "Swampland: bring the three wisps back to their clefts, to the north. The timer starts "
                  "with the first one: {seconds} s."),
        "wisp.taken": ("Feu-follet pris : des murs surgissent entre les arbres !", "Wisp taken: walls rise between the trees!"),
        "wisp.full": ("Vous portez déjà un feu-follet.", "You already carry a wisp."),
        "wisp.none": ("Il vous faut un feu-follet pour cette faille.", "You need a wisp for this cleft."),
        "cleft.lit": ("Un feu-follet rejoint sa faille ({count}/{total}).", "A wisp reaches its cleft ({count}/{total})."),
        "cleft.taken": ("Cette faille brille déjà.", "This cleft already shines."),
        "timer": ("{seconds} s", "{seconds} s"),
        "timer.title": ("Feux-follets", "Wisps"),
        "fail": ("Trop tard : les feux-follets s'enfuient et changent de place.", "Too late: the wisps flee and move."),
        "wisps.done": ("Les trois failles brillent : un passage s'ouvre au nord.", "The three clefts shine: a passage opens north."),
        "trap.tripwire": ("Un fil tendu vous renverse !", "A tripwire knocks you down!"),
        "trap.bear": ("Un piège à loup se referme sur vous !", "A bear trap snaps shut on you!"),
        "trap.spikes": ("Des piques jaillissent !", "Spikes burst out!"),
        "trap.eggs": ("Les œufs d'araignée éclatent !", "The spider eggs burst!"),
        "rack.used": ("Le fusil revigorant accélère vos alliés et ralentit les ennemis.", "The rifle speeds up your allies and slows foes."),
        "rack.cooldown": ("Le fusil se recharge.", "The rifle is recharging."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "mossman.ambush": ("Une embuscade ! Le passage se referme : le Moussu surgit.", "An ambush! The passage closes: the Mossman appears."),
        "mossman.stealth": ("Le Moussu disparaît dans la mousse… préparez-vous à esquiver !",
                            "The Mossman vanishes into the moss… get ready to dodge!"),
        "mossman.wolves": ("Le Moussu appelle ses loups.", "The Mossman calls his wolves."),
        "mossman.beast": ("Le Moussu prend sa forme sauvage !", "The Mossman takes his wild form!"),
        "mossman.reset": ("Le Moussu se retire dans la mousse.", "The Mossman withdraws into the moss."),
        "mossman.victory": ("Le Moussu tombe : le passage s'ouvre vers la clairière.", "The Mossman falls: the passage opens to the clearing."),
        "bloom.start": ("Un feu-follet attend à l'entrée de la clairière : déposez-le dans une faille pour réveiller Carnasse.",
                        "A wisp waits at the clearing's entrance: put it in a cleft to wake Bloomhunger."),
        "bloom.enter": ("Carnasse ! Il n'est vulnérable que dans le cercle vert, qui tourne de faille en faille.",
                        "Bloomhunger! He is only vulnerable inside the green circle, which moves from cleft to cleft."),
        "bloom.onslaught": ("Assaut ! Carnasse se retire au centre, ses esprits attaquent : abattez-les dans le cercle vert ({count}).",
                            "Onslaught! Bloomhunger retreats to the centre, his spirits attack: slay them in the green circle ({count})."),
        "bloom.back": ("Carnasse revient au combat ; des fleurs de poison poussent dans la clairière.",
                       "Bloomhunger returns to the fight; poison blooms grow in the clearing."),
        "bloom.wisps": ("Carnasse se charge ! Rapportez les quatre feux-follets des coins avant la fin de sa charge ({seconds} s) !",
                        "Bloomhunger is charging! Bring the four corner wisps back before his charge ends ({seconds} s)!"),
        "bloom.wisps.done": ("Les quatre failles brillent : Carnasse est étourdi dans un grand cercle vert !",
                             "The four clefts shine: Bloomhunger is stunned in a large green circle!"),
        "bloom.purge": ("Purge corporelle !", "Corporeal purge!"),
        "bloom.reset": ("Carnasse se rendort ; les failles s'éteignent.", "Bloomhunger falls asleep; the clefts go dark."),
        "bloom.victory": ("Carnasse se dessèche : le marais est purifié.", "Bloomhunger withers: the swamp is cleansed."),
        "title.victory": ("Marais terminé", "Swampland complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -------------------------------------------------------------------------------------------------

def java_layout():
    J = fc
    clefts = J.jblocks([(x, 0, z) for x, z in CLEFTS])
    spots = "{" + ", ".join(J.jpoints([(x, WISP_Y, z) for x, z in g]) for g in WISP_SPOTS) + "}"
    spot_blocks = "{" + ", ".join(J.jblocks([(x, WISP_Y, z) for x, z in g]) for g in WISP_SPOTS) + "}"
    walls = "{" + ", ".join(f"{{{a}, {b}, {GROUND_Y + 0}, {z}}}" for a, b, z in WALLS) + "}"
    kinds = {TRIPWIRE: 0, BEAR_TRAP: 1, SPIKE_PLATE: 2, SPIDER_EGGS: 3}
    traps_j = "{" + ", ".join(f"{{{x}, {GROUND_Y - 1}, {z}, {kinds[k]}}}" for x, z, k in TRAPS) + "}"
    racks = J.jblocks([(x, 0, z) for x, z in RACKS])
    sx0, sx1, sz0, sz1 = SWAMP
    rx0, rx1, rz0, rz1 = ROOM
    cl_clefts = J.jblocks([(x, 0, z) for x, z in CL_CLEFTS])
    corners = J.jblocks([(x, WISP_Y, z) for x, z in CL_CORNERS])
    return f"""package dev.nakasar.hytale.fractals.swampland;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions du Marais, écrites par tools/generate_swampland.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SwamplandLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Le marais des feux-follets. */
    public static final Box SWAMP = {J.jbox(sx0, sx1, -1, 8, sz0, sz1)};
    /** Failles des feux-follets, au nord. */
    public static final int[][] CLEFTS = {clefts};
    /** Places possibles des feux-follets : une par groupe, tirée à chaque essai (blocs et points). */
    public static final int[][][] WISP_SPOTS = {spot_blocks};
    public static final double[][][] WISP_POINTS = {spots};
    /** Murs qui surgissent dès qu'un feu-follet est pris : {{x0, x1, y, z}}, un bloc de haut. */
    public static final int[][] WALLS = {walls};
    /** Pièges : {{x, y, z, sorte}} ; sortes : 0 fil tendu, 1 piège à loup, 2 plaque à piques, 3 œufs d'araignée. */
    public static final int[][] TRAPS = {traps_j};
    public static final int[][] RACKS = {racks};
    public static final int[][] GATE_SWAMP = {J.jblocks(GATE_SWAMP)};
    public static final double[] SWAMP_CHECKPOINT = {J.jpoint((0, 0, -44))};

    /** Salle de l'embuscade du Moussu. */
    public static final Box ROOM = {J.jbox(rx0, rx1, -1, 8, rz0, AMBUSH_Z)};
    public static final int[][] GATE_BEHIND = {J.jblocks(GATE_BEHIND)};
    public static final int[][] GATE_AHEAD = {J.jblocks(GATE_AHEAD)};
    public static final double[] MOSSMAN = {J.jpoint(MOSSMAN_AT)};
    /** Cachette fermée où le Moussu attend pendant sa furtivité. */
    public static final double[] POCKET = {J.jpoint((POCKET[0], POCKET[1], POCKET[2]))};
    public static final double[] ROOM_CHECKPOINT = {J.jpoint((0, 0, -56))};

    /** Clairière de Carnasse. */
    public static final double[] CLEARING = {J.jpoint((CL_CENTER[0], 0, CL_CENTER[1]))};
    public static final double CLEARING_RADIUS = {CL_RADIUS};
    /** Failles de la clairière, dans le sens horaire (N, E, S, O). */
    public static final int[][] CLEARING_CLEFTS = {cl_clefts};
    public static final int[] CLEARING_WISP = {J.jblock((CL_WISP[0], WISP_Y, CL_WISP[1]))};
    public static final int[][] CORNER_WISPS = {corners};
    public static final double[] CLEARING_CHECKPOINT = {J.jpoint((0, 0, -95))};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private SwamplandLayout() {{
    }}
}}
"""


GROUND_Y = fc.GROUND_Y


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name in (CLEFT, CLEFT_LIT, WISP_BLOCK):
        return (160, 255, 220)
    if name in (TRIPWIRE, BEAR_TRAP, SPIKE_PLATE, SPIDER_EGGS):
        return (230, 90, 70)
    if name == RACK:
        return (255, 210, 120)
    if name == MIST:
        return (230, 140, 220)
    if name == LEAVES:
        return (70, 120, 60)
    if name == TRUNK:
        return (100, 80, 50)
    if name.startswith("Rock"):
        return (110, 116, 104)
    return (88, 96, 60)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, tex, base, accent, glyph, light, use, solid, alpha, opacity in blocks():
        fc.write_block(LANG, name, tex, base, accent, glyph, light, use, solid, alpha, opacity)
    fc.write_json(fc.OBJECTS / f"{WISP}.json", wisp_item())
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Crippled.png", (200, 170, 110), "feet")
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Wisp_Vigor.png", (120, 255, 190), "plus")
    fc.write_json(fc.SERVER / f"Entity/Damage/{PURGE_CAUSE}.json", purge_cause())
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
    counts = fc.write_instance(INSTANCE, "Marais", PREFAB_DIR, sections, SPAWN, "#5f8f45",
                                WEATHER, fc.weather("#5a7a6a", "#c0d0a8", "#90a888", (16, 170), 0.45, "#e8f0c8"), "15:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Marais : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(TREES)} arbres, {len(TRAPS)} pièges, "
          f"{len(roles())} rôles, {len(PARTICLE_SYSTEMS)} particules")
    if preview:
        fc.top_view(p, preview / "marais_dessus.png", color_of)


if __name__ == "__main__":
    main()
