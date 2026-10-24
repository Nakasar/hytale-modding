#!/usr/bin/env python3
"""Génère l'Océan solide (Solid Ocean), quatrième fractale de la saison 1 (étape 7 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_solid_ocean.py [--preview DOSSIER]

Le déroulé de GW2 (wiki.guildwars2.com/wiki/Solid_Ocean_Fractal), dans l'ordre :

1. la traversée : des fragments de jade flottent au-dessus d'un océan figé ; des irukandjis gardent les plus grands,
   on peut les combattre ou les éviter. Tomber ramène à la plateforme d'avant, pas au début ;
2. l'Abîme de Jade (Jade Maw), invulnérable (écailles denses), en trois temps :
   - phase 1 : un test d'agonie à l'arrivée, puis abattre deux tentacules (et les irukandjis autour) ;
   - phase 2 : des colosses de jade arrivent, les tuer remplit une barre ; ils renvoient les projectiles, renversent
     autour d'eux et lâchent des cristaux réfléchissants ;
   - fin : tentacules et Abîme seuls, les tentacules lâchent les cristaux ;
   l'Abîme marque un joueur d'un crâne rouge puis tire son rayon mortel : on s'écarte quand le crâne disparaît, ou on
   tient un cristal qui l'absorbe et charge le joueur ; un cristal lancé par un joueur chargé retire 5 % de la vie de
   l'Abîme, un tentacule abattu environ 3 %. Près de la mort, un dernier rayon frappe tout le monde : il faut tenir un
   cristal.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_SolidOcean`, le cristal
réfléchissant (clic droit : le lancer), la plateforme de jade sûre, la cause de dégâts du rayon, les particules, les
modèles et rôles, la langue `nakasar_fractals_solid_ocean.lang` et `solidocean/SolidOceanLayout.java`. Repère comme la
Falaise : y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
"""
import math
import sys
from pathlib import Path

import fractal_anim as fa
import fractal_common as fc
import fractal_models as fm
import fractal_nature as fn
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

LANG = "nakasar_fractals_solid_ocean"
GENERATOR = "generate_solid_ocean.py"
INSTANCE = "Nakasar_Fractal_SolidOcean"
WEATHER = "Nakasar_Fractal_Weather_SolidOcean"
PREFAB_DIR = "SolidOcean"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/solidocean/SolidOceanLayout.java"
INTERACTIONS = go.INTERACTIONS / "SolidOcean"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/SolidOcean"

# --- blocs et rôles -------------------------------------------------------------------------------------
# Dessus des fragments (atterrissage sûr) : le bloc de cristal de jade (Kevin, 2026-10-24 : plus de dalle à fissures).
JADE_CRYSTAL = "Nakasar_Fractal_Jade_Crystal"
JADE_LANDING = f"{JADE_CRYSTAL}_Block"
CRYSTAL = "Nakasar_Fractal_Reflecting_Crystal"
MAW = "Nakasar_Fractal_Jade_Maw"
TENTACLE = "Nakasar_Fractal_Jade_Tentacle"
COLOSSUS = "Nakasar_Fractal_Jade_Colossus"
IRUKANDJI = "Nakasar_Fractal_Irukandji"
FOE_ROLES = [MAW, TENTACLE, COLOSSUS, IRUKANDJI]
BEAM_CAUSE = "Nakasar_Fractal_Jade_Beam"
TARGETED = "Nakasar_Fractal_Jade_Targeted"

JADE = ["Rock_Crystal_Green_Block", "Rock_Crystal_Green_Block", "Plant_Coral_Block_Green", "Rock_Crystal_Cyan_Block"]
UNDER = ["Soil_Clay_Ocean", "Soil_Clay_Ocean", "Rock_Crystal_Green_Block", "Soil_Clay_Smooth_Green"]
SEA = ["Soil_Clay_Smooth_Cyan", "Soil_Clay_Smooth_Green", "Soil_Clay_Ocean", "Rock_Crystal_Cyan_Block"]
DECO = ["Plant_Coral_Bush_Green", "Plant_Coral_Bush_Cyan", "Plant_Coral_Model_Green", "Deco_Coral_Shell",
        "Plant_Coral_Bush_Lime", "Deco_Coral_Shell_Swirly"]
pick = fc.pick

# --- lieux (y = debout à) ---------------------------------------------------------------------------
START = (0, 40, 5, 0)                   # x, z, rayon, debout
SPAWN = (0, 0, 42)
SEA_Y = -66                             # l'océan figé, sous le filet anti-chute (y monde 40) : on n'y reste pas
GAP = 2.6                               # vide entre deux bords de plateformes (sauts d'environ 3 blocs)
STANDS = [0, 1, 1, 2, 1, 2, 3, 2, 3, 3, 4, 3, 4, 5, 4, 5, 5]
RADII = [3, 2, 3, 4, 2, 3, 2, 4, 3, 2, 3, 4, 2, 3, 3, 4, 3]
AR_RADIUS = 27                          # ×1,5 (Kevin, 2026-10-24)
MAW_BACK = 7                            # l'Abîme flotte au nord de l'arène, hors de portée de mêlée
# Tentacules (dx, dz depuis le centre ; z vers le sud) : répartis sur toute l'arène plutôt qu'en cercle (Kevin,
# 2026-10-24), le sud (l'entrée) restant libre. Deux en phase 1 (au nord), quatre en phase 2, six en phase 3.
TENTACLE_SPOTS = [(-8, -15), (8, -15)]
TENTACLE_SPOTS_P2 = [(-16, -8), (16, -8), (-10, 9), (10, 9)]
TENTACLE_SPOTS_P3 = [(0, -22), (-20, -1), (20, -1), (0, -4), (-12, 13), (12, 13)]
COLOSSUS_ANGLES = [150, 30, 270, 90]
COLOSSUS_RADIUS = 12
TREE_ANGLES = (50, 125, 220, 300)       # cerisiers en fleurs (arbres de cristal vanilla, feuilles roses)
SCAFFOLD_ARCS = ((150, 192), (322, 355), (8, 38))
ARENA_IRUKANDJI = [200, 340]           # deux seulement : ils ont 600 PV


def platforms():
    """Fragments de jade (x, z, rayon, debout) du départ vers le nord : chaque centre est posé à rayon + GAP + rayon du
    précédent, le cap ondule autour du nord ; jamais plus d'un bloc à monter d'un fragment à l'autre."""
    out = [START]
    x, z = START[0], START[1]
    for k, (stand, r) in enumerate(zip(STANDS, RADII), start=1):
        prev = out[-1]
        heading = math.radians(-90 + 38 * math.sin(k * 0.9))
        d = prev[2] + r + GAP
        x, z = x + math.cos(heading) * d, z + math.sin(heading) * d
        out.append((round(x), round(z), r, stand))
    for a, b in zip(out, out[1:]):
        assert b[3] - a[3] <= 1, (a, b)
        edge = math.hypot(b[0] - a[0], b[1] - a[1]) - a[2] - b[2]
        assert 1.5 <= edge <= 4.0, (a, b, edge)
    return out


PATH = platforms()
LAST = PATH[-1]
AR_STAND = LAST[3]
AR_CENTER = (LAST[0], round(LAST[1] - LAST[2] - GAP - AR_RADIUS - 1))
assert math.hypot(AR_CENTER[0] - LAST[0], AR_CENTER[1] - LAST[1]) - LAST[2] - AR_RADIUS <= 4
MAW_AT = (AR_CENTER[0], AR_STAND, AR_CENTER[1] - AR_RADIUS - MAW_BACK)
REWARD_AT = (AR_CENTER[0] - 2, AR_STAND, AR_CENTER[1] + 6)
END_EXIT_AT = (AR_CENTER[0] + 2, AR_STAND, AR_CENTER[1] + 6)


def ring_point(center, radius, angle):
    return (round(center[0] + math.cos(math.radians(angle)) * radius),
            round(center[1] + math.sin(math.radians(angle)) * radius))


def jump_zone():
    xs = [p[0] for p in PATH] + [AR_CENTER[0] - AR_RADIUS, AR_CENTER[0] + AR_RADIUS]
    zs = [p[1] for p in PATH] + [AR_CENTER[1] - AR_RADIUS, AR_CENTER[1] + AR_RADIUS]
    return (min(xs) - 16, max(xs) + 16, SEA_Y - 6, AR_STAND + 14, min(zs) - 8, max(zs) + 8)


def course_prefab():
    p = go.Prefab()
    # Fragments de jade : dessus sûr, dessous en strates de pierre moussue et de jade, débris flottants.
    for k, (x, z, r, stand) in enumerate(PATH):
        fc.disc(p, x, z, r, stand, JADE_LANDING, STRATA, 4 + r * 2)
        restrata(p, x, z, r + 1, stand)
        for dx, dz in ((r - 1, 0), (-r + 1, 1), (0, -r + 1)):
            if r >= 3 and (k + dx) % 2 == 0:
                p.set(x + dx, stand, z + dz, pick(DECO, x + dx, stand, z + dz))
        debris(p, x, z, r, stand, seed=k)
    lantern_posts(p)
    # Arène de l'Abîme : grand fragment, bordure de cristaux, coin sûr à l'entrée (sud-ouest).
    ax, az = AR_CENTER
    fc.disc(p, ax, az, AR_RADIUS, AR_STAND, JADE_LANDING, STRATA, 12)
    restrata(p, ax, az, AR_RADIUS + 1, AR_STAND)
    for a in range(0, 360, 9):
        x, z = ring_point(AR_CENTER, AR_RADIUS, a)
        if 60 <= a <= 120:
            continue   # entrée au sud
        p.set(x, AR_STAND, z, "Rock_Crystal_Green_Large" if a % 27 else "Rock_Crystal_Cyan_Medium")
    for a in (20, 160, 200, 340):
        x, z = ring_point(AR_CENTER, AR_RADIUS - 3, a)
        p.set(x, AR_STAND, z, "Plant_Coral_Model_Green")
    # Le socle de l'Abîme, au nord : une butte de jade qui sort de l'océan.
    mx, _, mz = MAW_AT
    for x in range(mx - 7, mx + 8):
        for z in range(mz - 7, mz + 8):
            d = math.hypot(x - mx, z - mz)
            if d > 7.5:
                continue
            top = AR_STAND - 1 - int(d * 0.6)
            for y in range(SEA_Y, top + 1):
                p.set(x, y, z, pick(JADE if y > top - 2 else UNDER, x, y, z))
    arena_ruins(p)
    dress(p)
    amphitheater(p)
    monoliths(p)
    jade_crystals(p)
    return p


# Cristaux du décor en cristal de jade (Kevin, 2026-10-24) : copies du bloc et des fragments du Néant vanilla (petit,
# moyen, grand ; Assets.zip 0.7.2, Server/Item/Items/Rock/Crystal/Rock_Crystal_Void_*) aux textures passées au vert
# jade par generate_jade_crystals.py. Le décor garde ses formes ; seuls les cristaux verts et cyan changent, au même
# calibre.
CRYSTAL_SIZES = ("Block", "Large", "Medium", "Small")


def jade_crystals(p):
    for pos, (name, rot) in list(p.blocks.items()):
        parts = name.split("_")
        if len(parts) == 4 and parts[:2] == ["Rock", "Crystal"] and parts[2] in ("Green", "Cyan") and parts[3] in CRYSTAL_SIZES:
            p.blocks[pos] = (f"{JADE_CRYSTAL}_{parts[3]}", rot)


# --- décor de nuit (retours du 2026-10-24, d'après les captures de GW2) ----------------------------------------------
# Fragments en strates de pierre moussue et de jade, débris de roche qui flottent dessous, poteaux à lanterne du côté
# opposé aux sauts (seule lumière de la nuit avec les cristaux), ruines de colonnes et échafaudage autour de l'arène,
# monolithes sombres qui sortent de l'océan figé au loin.
STRATA = ["Rock_Stone_Mossy", "Rock_Aqua", "Rock_Stone_Cobble_Mossy", "Soil_Clay_Ocean", "Rock_Crystal_Green_Block",
          "Rock_Stone_Mossy"]
MONOLITH = ["Rock_Slate", "Rock_Basalt", "Rock_Slate", "Rock_Stone_Mossy"]
BEAM = "Wood_Darkwood_Beam"
PLANKS = "Wood_Darkwood_Planks"
FENCE = "Wood_Darkwood_Fence"
LANTERN = "Deco_Lantern"
VINE = "Plant_Vine_Green_Hanging"


def stratum(x, y, z):
    """Strates horizontales de deux blocs, ondulées par le bruit (comme les fragments empilés de GW2)."""
    band = int(math.floor((y + 1.6 * fn.fbm2(x, z, 7, 2, 61)) / 2))
    return STRATA[band % len(STRATA)]


def restrata(p, cx, cz, r, stand):
    """Repeint le dessous d'un fragment en strates ; lianes pendues sous le rebord."""
    for x in range(cx - r - 1, cx + r + 2):
        for z in range(cz - r - 1, cz + r + 2):
            col = [y for y in range(stand - 2 * r - 20, stand - 1) if (x, y, z) in p.blocks]
            for y in col:
                p.set(x, y, z, stratum(x, y, z))
            if col and math.hypot(x - cx, z - cz) > r - 1.5 and fn.hash01(x, z, stand, 62) < 0.3 \
                    and fn.free(p, x, min(col) - 1, z):
                p.set(x, min(col) - 1, z, VINE)


def debris(p, cx, cz, r, stand, seed=0):
    """Deux à quatre éclats de roche qui flottent sous le fragment (jamais à hauteur de saut)."""
    for k in range(2 + int(fn.hash01(cx, cz, seed, 63) * 3)):
        a = fn.hash01(k, seed, 1, 64) * math.tau
        d = r * 0.6 + fn.hash01(k, seed, 2, 64) * (r + 2)
        x, z = round(cx + math.cos(a) * d), round(cz + math.sin(a) * d)
        y = stand - 2 * r - 5 - int(fn.hash01(k, seed, 3, 64) * 6)
        size = 1 + int(fn.hash01(k, seed, 4, 64) * 2)
        for dx in range(size):
            for dz in range(size):
                for dy in range(size):
                    if fn.free(p, x + dx, y + dy, z + dz):
                        p.set(x + dx, y + dy, z + dz, stratum(x + dx, y + dy, z + dz))


def lantern_posts(p):
    """Un poteau à lanterne sur chaque fragment de rayon 3 ou plus, au bord opposé aux sauts (prévu de la nuit)."""
    for k, (x, z, r, stand) in enumerate(PATH):
        if r < 3:
            continue
        vx = vz = 0.0
        for j in (k - 1, k + 1):
            if 0 <= j < len(PATH):
                d = math.hypot(PATH[j][0] - x, PATH[j][1] - z) or 1
                vx += (PATH[j][0] - x) / d
                vz += (PATH[j][1] - z) / d
        if k == len(PATH) - 1:
            vx, vz = vx + (AR_CENTER[0] - x), vz + (AR_CENTER[1] - z)
        a = math.atan2(-vz, -vx) if (vx or vz) else 0
        px, pz = round(x + math.cos(a) * (r - 1)), round(z + math.sin(a) * (r - 1))
        for y in range(stand, stand + 3):
            p.set(px, y, pz, BEAM)
        p.set(px, stand + 3, pz, LANTERN)


def column(p, x, y0, z, height, seed=0):
    """Colonne en ruine 3 × 3 : pierre moussue et jade, cassée en biais, cristal au sommet."""
    for dy in range(height):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                top = height - (1 if abs(dx) + abs(dz) == 2 else 0) - int(fn.hash01(dx, dz, seed, 65) * 2)
                if dy < top:
                    p.set(x + dx, y0 + dy, z + dz, "Rock_Crystal_Green_Block" if dy % 4 == 3 else stratum(x + dx, y0 + dy, z + dz))
    p.set(x, y0 + height, z, "Rock_Crystal_Cyan_Medium" if seed % 2 else "Rock_Crystal_Green_Large")


def arena_ruins(p):
    """Décor de l'arène d'après les captures de GW2 (Kevin, 2026-10-24) : cerisiers en fleurs, échafaudages de bois sur
    le bord (plancher, garde-corps, lanternes pendues, toiles rouges déchirées), gros cubes de jade sur le sol."""
    for k, a in enumerate(TREE_ANGLES):
        cherry(p, *ring_point(AR_CENTER, AR_RADIUS - 4, a), seed=k)
    for k, (a0, a1) in enumerate(SCAFFOLD_ARCS):
        scaffold(p, a0, a1, 4, seed=k)
    cubes(p)


def amphitheater(p):
    """L'arène au fond d'une cuvette : gradins de gros blocs de jade et de pierre moussue qui montent tout autour (de 1 à
    16 blocs sur 12 de large), taillés en cubes de 3 ; ouverts au sud (l'entrée) et bas au nord, où flotte l'Abîme, entre
    deux grands piliers. Des cubes de jade flottent au-dessus."""
    ax, az = AR_CENTER
    reach = AR_RADIUS + 12
    for x in range(ax - reach, ax + reach + 1):
        for z in range(az - reach, az + reach + 1):
            # cubes de 3 : hauteur et rayon pris au coin de la case de 3, comme des blocs empilés
            cx, cz = x - (x - ax) % 3 + 1, z - (z - az) % 3 + 1
            d = math.hypot(cx - ax, cz - az)
            if d <= AR_RADIUS + 1 or d > reach:
                continue
            a = math.degrees(math.atan2(cz - az, cx - ax)) % 360
            if 55 <= a <= 125:
                continue   # entrée au sud
            t = (d - AR_RADIUS) / 12
            h = round(1 + 15 * t ** 1.3 + 3 * fn.hash01(cx, cz, 0, 73))
            if 245 <= a <= 295:
                h = min(h, 2)   # nord : on voit l'Abîme
            for y in range(AR_STAND - 4 - int(t * 10), AR_STAND - 1 + h):
                p.set(x, y, z, "Rock_Crystal_Green_Block" if fn.hash01(cx, y // 3, cz, 74) < 0.3 else stratum(x, y, z))
            if fn.hash01(cx, cz, 1, 75) < 0.04 and fn.free(p, x, AR_STAND - 1 + h, z):
                p.set(x, AR_STAND - 1 + h, z, VINE if h > 4 else "Plant_Coral_Bush_Green")
    for a in (240, 300):   # piliers de part et d'autre de l'Abîme
        x, z = ring_point(AR_CENTER, AR_RADIUS + 5, a)
        column(p, x, AR_STAND - 4, z, 22, seed=a)
    for k in range(26):   # cubes de jade qui flottent
        a = fn.hash01(k, 1, 0, 76) * 360
        r = AR_RADIUS + 6 + fn.hash01(k, 2, 0, 76) * 22
        x, z = ring_point(AR_CENTER, r, a)
        y = AR_STAND + 12 + int(fn.hash01(k, 3, 0, 76) * 22)
        size = 1 + int(fn.hash01(k, 4, 0, 76) * 3)
        for dx in range(size):
            for dy in range(size):
                for dz in range(size):
                    if fn.free(p, x + dx, y + dy, z + dz):
                        p.set(x + dx, y + dy, z + dz, "Rock_Crystal_Green_Block" if (dx + dy + dz) % 3 == 0 else
                              stratum(x + dx, y + dy, z + dz))


def cubes(p):
    """Gros cubes de jade (2 ou 3 de côté) posés sur le sol de l'arène, à l'écart des tentacules, des colosses et de
    l'allée de l'entrée : de quoi se mettre à couvert."""
    keep = [(AR_CENTER[0] + dx, AR_CENTER[1] + dz) for dx, dz in TENTACLE_SPOTS + TENTACLE_SPOTS_P2 + TENTACLE_SPOTS_P3]
    keep += [ring_point(AR_CENTER, COLOSSUS_RADIUS, a) for a in COLOSSUS_ANGLES]
    keep += [ring_point(AR_CENTER, AR_RADIUS - 4, a) for a in TREE_ANGLES]
    placed = []
    for k in range(200):
        if len(placed) >= 9:
            break
        a = fn.hash01(k, 5, 0, 77) * 360
        r = 7 + fn.hash01(k, 6, 0, 77) * (AR_RADIUS - 13)
        x, z = ring_point(AR_CENTER, r, a)
        if abs(x - AR_CENTER[0]) <= 3 and z > AR_CENTER[1]:
            continue   # allée de l'entrée
        if any(math.hypot(x - kx, z - kz) < 5 for kx, kz in keep + placed):
            continue
        placed.append((x, z))
        size = 2 + k % 2
        for dx in range(size):
            for dy in range(size):
                for dz in range(size):
                    p.set(x + dx, AR_STAND + dy, z + dz, "Rock_Crystal_Green_Block" if dy == size - 1 else
                          stratum(x + dx, AR_STAND + dy, z + dz))


# Cerisier en fleurs : pas de cerisier vanilla en 0.7.2 ; l'arbre de cristal (Wood_Crystal_Trunk, Plant_Leaves_Crystal
# roses) en a l'allure, avec un tapis de pétales roses (Plant_Petals_Pink) dessous.
PETALS = "Plant_Petals_Pink"


def cherry(p, x, z, seed=0):
    fn.broadleaf(p, x, AR_STAND, z, 6 + int(fn.hash01(x, z, seed, 71) * 2), kind="crystal", seed=70 + seed, droop=0.08,
                 hanging=["Plant_Leaves_Crystal"])
    for dx in range(-5, 6):
        for dz in range(-5, 6):
            if math.hypot(dx, dz) <= 4.5 and fn.hash01(x + dx, z + dz, seed, 72) < 0.45 \
                    and fn.free(p, x + dx, AR_STAND, z + dz) and not fn.free(p, x + dx, AR_STAND - 1, z + dz):
                p.set(x + dx, AR_STAND, z + dz, PETALS)


def scaffold(p, a0, a1, floor, seed=0):
    """Échafaudage de bois sur le bord de l'arène (rayons R-3 à R-1, poteaux posés sur le jade) : plancher à `floor`
    blocs, garde-corps devant, bras de bois avec une lanterne pendue à une chaîne, corde tendue entre les poteaux de
    devant et toiles rouges déchirées qui pendent dessous."""
    y = AR_STAND + floor
    step = math.degrees(0.8 / AR_RADIUS)
    a = a0
    while a <= a1:
        for r in (AR_RADIUS - 3, AR_RADIUS - 2, AR_RADIUS - 1):
            x, z = ring_point(AR_CENTER, r, a)
            if fn.hash01(x, z, seed, 67) < 0.9:
                p.set(x, y, z, PLANKS)
        x, z = ring_point(AR_CENTER, AR_RADIUS - 4, a)
        p.set(x, y + 1, z, FENCE)
        a += step
    posts = max(2, round((a1 - a0) / 8) + 1)
    front = []
    for k in range(posts):
        pa = a0 + (a1 - a0) * k / (posts - 1)
        for r in (AR_RADIUS - 4, AR_RADIUS - 1):
            x, z = ring_point(AR_CENTER, r, pa)
            for yy in range(AR_STAND - 3, y + 4):
                p.set(x, yy, z, BEAM)
            if r == AR_RADIUS - 4:
                front.append((x, z))
                if k % 2 == 0:   # bras vers l'arène, lanterne pendue
                    ix, iz = ring_point(AR_CENTER, r - 1, pa)
                    p.set(ix, y + 3, iz, BEAM)
                    p.set(ix, y + 2, iz, "Deco_Iron_Chains_Vertical")
                    p.set(ix, y + 1, iz, "Deco_Lantern_Ceiling")
    # Corde entre deux poteaux de devant, toiles rouges dessous (une case sur deux, longueurs inégales).
    for (x0, z0), (x1, z1) in zip(front, front[1:]):
        n = max(abs(x1 - x0), abs(z1 - z0))
        along_z = abs(z1 - z0) > abs(x1 - x0)
        for i in range(1, n):
            x, z = round(x0 + (x1 - x0) * i / n), round(z0 + (z1 - z0) * i / n)
            sag = round(1.5 * math.sin(math.pi * i / n))
            top = y + 3 - sag
            if fn.free(p, x, top, z):
                p.set(x, top, z, "Deco_Rope")
            if i % 2 and fn.hash01(x, z, seed, 68) < 0.8:
                for k in range(1 + int(fn.hash01(z, x, seed, 69) * 3)):
                    if fn.free(p, x, top - 1 - k, z):
                        p.set(x, top - 1 - k, z, "Cloth_Roof_Red_Vertical", 1 if along_z else 0)


def monoliths(p):
    """Monolithes sombres et moussus qui sortent de l'océan figé, loin du parcours (silhouettes dans la brume)."""
    path = [(q[0], q[1], q[2]) for q in PATH] + [(AR_CENTER[0], AR_CENTER[1], AR_RADIUS)]
    xs = [q[0] for q in PATH]
    zs = [q[1] for q in PATH] + [AR_CENTER[1]]
    placed = 0
    for k in range(60):
        if placed >= 9:
            break
        x = round(min(xs) - 60 + fn.hash01(k, 1, 0, 68) * (max(xs) - min(xs) + 120))
        z = round(min(zs) - 40 + fn.hash01(k, 2, 0, 68) * (max(zs) - min(zs) + 70))
        if any(math.hypot(x - a, z - b) < r + 30 for a, b, r in path):
            continue
        placed += 1
        r0 = 4 + fn.hash01(k, 3, 0, 68) * 5
        top = AR_STAND + 15 + int(fn.hash01(k, 4, 0, 68) * 45)
        lean = (fn.hash01(k, 5, 0, 68) - 0.5) * 0.25
        for y in range(SEA_Y - 2, top):
            t = (y - SEA_Y) / (top - SEA_Y)
            r = r0 * (1.15 - 0.55 * t) + 1.2 * fn.fbm2(y, k, 5, 2, 69)
            cx, cz = x + lean * (y - SEA_Y), z + lean * 0.6 * (y - SEA_Y)
            n = int(math.ceil(r))
            for dx in range(-n, n + 1):
                for dz in range(-n, n + 1):
                    if math.hypot(dx, dz) <= r:
                        bx, bz = round(cx) + dx, round(cz) + dz
                        p.set(bx, y, bz, pick(MONOLITH, bx, y, bz))
                        if math.hypot(dx, dz) > r - 1 and fn.hash01(bx, y, bz, 70) < 0.04 and fn.free(p, bx, y - 1, bz):
                            p.set(bx, y - 1, bz, VINE)


THEME = fn.THEMES["jade"]


def dress(p):
    """L'océan figé loin dessous (houle de jade, récifs de corail, aiguilles de cristal qui en sortent), un pourtour
    de sable et de corail autour de l'arène (pas au sud, arrivée des sauts), des îlots de jade tout autour."""
    xs = [q[0] for q in PATH] + [AR_CENTER[0]]
    zs = [q[1] for q in PATH] + [AR_CENTER[1] - AR_RADIUS - MAW_BACK]
    x0, x1, z0, z1 = min(xs) - 70, max(xs) + 70, min(zs) - 60, max(zs) + 50
    # Îlots d'abord (avant l'océan, qui remplirait tout l'espace libre autour).
    fn.scatter_islets(p, (x0 + 10, x1 - 10, z0 + 10, z1 - 10), 24, (SEA_Y + 8, AR_STAND + 10), (3, 9), THEME, seed=41)
    sea = {}
    mx, mz, rx, rz = (x0 + x1) / 2, (z0 + z1) / 2, (x1 - x0) / 2, (z1 - z0) / 2
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            # contour arrondi et irrégulier : l'océan se perd dans la brume plutôt qu'en rectangle
            if math.hypot((x - mx) / rx, (z - mz) / rz) > 0.88 + 0.12 * fn.fbm2(x, z, 17, 2, 44):
                continue
            sea[(x, z)] = SEA_Y + round(1.4 * fn.fbm2(x, z, 9, 2, 43))
    for (x, z), top in sea.items():
        if not fn.free(p, x, top, z):
            continue
        p.set(x, top, z, pick(SEA, x, top, z))
        p.set(x, top - 1, z, "Soil_Clay_Ocean")
    # Récifs : coraux sur la houle, par massifs.
    for (x, z), top in sea.items():
        reef = fn.fbm2(x, z, 13, 2, 45)
        h = fn.hash01(x, z, 0, 46)
        if reef > 0.3 and h < 0.35 and fn.free(p, x, top + 1, z):
            pool = THEME["flowers"][int((fn.fbm2(x, z, 21, 1, 47) + 1) / 2 * len(THEME["flowers"])) % len(THEME["flowers"])]
            p.set(x, top + 1, z, pool[int(fn.hash01(z, x, 1, 48) * len(pool))])
        elif h < 0.04 and fn.free(p, x, top + 1, z):
            p.set(x, top + 1, z, THEME["short"][int(fn.hash01(z, x, 2, 49) * len(THEME["short"]))])
    # Aiguilles de cristal qui sortent de l'océan, loin des fragments (jamais une marche de plus).
    path = [(q[0], q[1], q[2]) for q in PATH] + [(AR_CENTER[0], AR_CENTER[1], AR_RADIUS)]
    for k in range(70):
        x = x0 + int(fn.hash01(k, 1, 0, 51) * (x1 - x0))
        z = z0 + int(fn.hash01(k, 2, 0, 51) * (z1 - z0))
        if any(math.hypot(x - a, z - b) < r + 10 for a, b, r in path):
            continue
        h = 6 + int(fn.hash01(k, 3, 0, 51) * 16)
        if (x, z) not in sea:
            continue
        fn.crystal_spire(p, x, sea[(x, z)] + 1, z, h, "green" if k % 3 else "cyan", seed=k)
    # Pourtour de l'arène.
    ax, az = AR_CENTER
    arena = {(x, z): AR_STAND - 1 for x in range(ax - AR_RADIUS, ax + AR_RADIUS + 1)
             for z in range(az - AR_RADIUS, az + AR_RADIUS + 1) if (x, AR_STAND - 1, z) in p.blocks}
    tops = fn.rim(arena, 3, 8, seed=53, block=lambda x, z: z > az + 12)
    fn.natural_ground(p, tops, THEME, seed=53, trees=0.04, spacing=6, bushes=0.08, density=0.25, flowers=0.2)


# --- objets, blocs, effets, particules ------------------------------------------------------------------

def crystal_item():
    """Le cristal réfléchissant a le modèle du grand cristal de jade (modèle vanilla Crystal_Large_Pointy du cristal du
    Néant, texture passée au jade), réduit comme les objets vanilla tenus qui reprennent un modèle de bloc
    (Weapon_Deployable_Slowness_Totem, Scale 0.305). Icône et cadrage de l'icône : ceux du bloc."""
    root = "Root_Nakasar_Fractal_Throw_Reflecting_Crystal"
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{CRYSTAL}.name", "Description": f"{LANG}.items.{CRYSTAL}.description"},
        "Icon": f"{go.ICONS}/Jade_Crystal_Large.png",
        "IconProperties": {"Scale": 0.5, "Rotation": [4, 183, 1], "Translation": [-1, -25]},
        "Model": "Resources/Crystals/Crystal_Large_Pointy.blockymodel",
        "Texture": JADE_MODEL_TEXTURE,
        "Scale": CRYSTAL_SCALE,
        "Light": {"Color": JADE_LIGHT, "Radius": 2},
        "Quality": "Epic",
        "Categories": ["Items.Misc"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
        "Interactions": {"Secondary": root, "SwapFrom": fc.KEEP_IN_HAND},
        "Utility": {"Compatible": False},
    }


CRYSTAL_SCALE = 0.4
JADE_LIGHT = "#3c8"
JADE_MODEL_TEXTURE = "Blocks/Nakasar/Fractals/Jade_Crystal_Big.png"
# taille : (modèle vanilla ou None pour le cube, boîte de sélection, cadrage de l'icône vanilla)
JADE_SHAPES = {
    "Block": (None, None, {"Scale": 0.58823, "Rotation": [22.5, 45, 22.5], "Translation": [0, -13.5]}),
    "Large": ("Crystal_Large_Pointy", None, {"Scale": 0.5, "Rotation": [4, 183, 1], "Translation": [-1, -25]}),
    "Medium": ("Crystal_Medium_Pointy", "Plant_Large", {"Scale": 0.58823, "Rotation": [22.5, 18, 22.5], "Translation": [4, -14]}),
    "Small": ("Crystal_Small_Pointy", "Plant_Medium", {"Scale": 0.58823, "Rotation": [22.5, 170, 22.5], "Translation": [-2, -11]}),
}


def jade_crystal_items():
    """Bloc et fragments de cristal de jade : les Rock_Crystal_Void_* vanilla (lus dans Assets.zip 0.7.2), textures
    et lumière en jade, sans recette."""
    out = {}
    for size, (model, hitbox, icon) in JADE_SHAPES.items():
        name = f"{JADE_CRYSTAL}_{size}"
        block = {"Material": "Solid", "Opacity": "Transparent", "Flags": {},
                 "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
                 "BlockParticleSetId": "Crystal", "BlockSoundSetId": "Crystal", "PhysicalMaterialId": "Stone",
                 "Light": {"Color": JADE_LIGHT}, "RequiresAlphaBlending": True}
        if model:
            block.update({"DrawType": "Model", "CustomModel": f"Resources/Crystals/{model}.blockymodel",
                          "CustomModelTexture": [{"Texture": JADE_MODEL_TEXTURE, "Weight": 1}],
                          "VariantRotation": "DoublePipe", "RandomRotation": "YawStep1", "ParticleColor": "#b0f0d0",
                          "Support": {"Down": [{"FaceType": "Full"}]}, "TextureComputedColor": "#1c4934"})
            if hitbox:
                block["HitboxType"] = hitbox
        else:
            texture = f"{go.TEXTURES}/Jade_Crystal.png"
            block.update({"DrawType": "Cube", "Group": "Stone",
                          "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
                          "ParticleColor": "#398560", "CubeShadingMode": "Reflective", "VariantRotation": "Pipe",
                          "TextureComputedColor": "#425148"})
        out[name] = {
            "TranslationProperties": {"Name": f"{LANG}.items.{name}.name", "Description": f"{LANG}.items.{name}.description"},
            "Icon": f"{go.ICONS}/Jade_Crystal_{size}.png",
            "IconProperties": icon,
            "Categories": ["Blocks.Ores"],
            "Quality": "Technical",
            "PlayerAnimationsId": "Block",
            "BlockType": block,
            "Tags": {"Type": ["Rock"], "Family": ["Crystal"]},
            "ItemSoundSetId": "ISS_Blocks_Stone",
        }
    return out



def throw_interaction():
    return {"$Comment": "Cristal réfléchissant : clic droit, le lancer sur l'Abîme de Jade (48 blocs, cône de 35°). "
                        "Chargé par le rayon, il lui retire 5 % de sa vie ; sinon il revient (Java, solidocean.JadeMaw).",
            "Type": "Nakasar_Fractal_ThrowItem", "Item": CRYSTAL, "Roles": MAW, "Range": 72, "Cone": 35,
            "Particle": "Nakasar_Fractal_Crystal_Trail", "Action": "Crystal",
            "NoTargetMessage": f"{LANG}.crystal.noTarget"}


def beam_cause():
    return fc.cause("Rayon de l'Abîme de Jade : mortel sans cristal (Java). L'armure ne le réduit pas.", "#7dffb0")


def effects():
    return {
        "Nakasar_Fractal_Crystal_Charged": fc.effect(
            LANG, "Nakasar_Fractal_Crystal_Charged", "Cristal chargé par le rayon de l'Abîme : le prochain cristal lancé "
            "le blesse (Java, solidocean.JadeMaw). Perdu quand l'Abîme choisit sa prochaine cible.", "Crystal_Charged", 30,
            ApplicationEffects={"EntityTopTint": "#8affc8"}),
        TARGETED: fc.effect(
            LANG, TARGETED, "Visé par l'Abîme de Jade : tête de mort rouge dans la barre d'état, lueur orange (Java, "
            "solidocean.JadeMaw). À la fin, le rayon tue le joueur s'il ne tient pas de cristal, ou charge son cristal.",
            "Jade_Targeted", 8, debuff=True,
            ApplicationEffects={"EntityTopTint": "#ff9a30", "EntityBottomTint": "#ff5a10"}),
    }


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Jade_Skull": ("Crâne rouge au-dessus du joueur visé par l'Abîme : nuée rouge et noire.",
                                   [("Skull", S("#ff3030", "#300000", 14, (0.1, 0.4), (-90, 90), 0.5, 0.5,
                                                life=(0.3, 0.5), size=(0.25, 0.45)), 0.0),
                                    ("Eyes", S("#ffffff", "#ff8080", 4, (0.0, 0.1), (-10, 10), 0.3, 0.1,
                                               life=(0.3, 0.4), size=(0.1, 0.2)), 0.2)]),
    "Nakasar_Fractal_Jade_Beam": ("Rayon de l'Abîme : éclats vert vif le long du trait.",
                                  [("Beam", S("#e0fff0", "#30ff90", 6, (0.0, 0.3), (-90, 90), 0.4, 0.4,
                                              life=(0.3, 0.5), size=(0.3, 0.5)), 0.0)]),
    "Nakasar_Fractal_Crystal_Charge": ("Joueur chargé par le rayon : lueur verte.",
                                       [("Glow", S("#e0ffe8", "#40ff90", 10, (0.3, 0.8), (40, 90), 0.4, 1.6), 0.4)]),
    "Nakasar_Fractal_Crystal_Glow": ("Cristal réfléchissant au sol : lueur de jade.",
                                     [("Glow", S("#f0fff8", "#60ffb0", 6, (0.2, 0.5), (60, 90), 0.3, 0.6), 0.2)]),
    "Nakasar_Fractal_Crystal_Trail": ("Cristal lancé : traînée de jade.",
                                      [("Trail", S("#ffffff", "#50ffa0", 8, (0.1, 0.4), (-90, 90), 0.3, 0.3,
                                                   life=(0.2, 0.4)), 0.0)]),
    "Nakasar_Fractal_Maw_Hurt": ("L'Abîme est touché : gerbe d'éclats de jade.",
                                 [("Shards", S("#e0fff0", "#208050", 30, (2.0, 5.0), (0, 90), 2.0, 2.0,
                                               life=(0.5, 1.0), blend="BlendLinear"), 1.5)]),
    "Nakasar_Fractal_Tentacle_Emerge": ("Un tentacule sort du jade : éclats et poussière verte.",
                                        [("Burst", S("#c0ffe0", "#206040", 20, (1.5, 3.5), (40, 90), 1.2, 0.5,
                                                     life=(0.5, 0.9), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Colossus_Reflect": ("Un colosse renvoie un projectile : éclair blanc.",
                                         [("Flash", S("#ffffff", "#a0ffe0", 12, (1.0, 2.5), (-90, 90), 0.6, 0.6,
                                                      life=(0.2, 0.4)), 1.2)]),
}


# --- modèles ----------------------------------------------------------------------------------------------

def maw_parts():
    jade, deep, eye, tooth = (70, 170, 120), (30, 90, 70), (240, 255, 120), (230, 240, 220)
    parts = [("Body", (0, 60, 0), (120, 120, 110), 0, fm.smooth(jade, (120, 220, 170)), "flat"),
             ("Crown", (0, 126, -6), (90, 24, 80), 0, fm.smooth(deep), "flat"),
             ("Jaw", (0, 18, 30), (100, 36, 60), 0, fm.smooth(deep), "flat"),
             ("Eye", (0, 82, 56), (40, 34, 2), 0, fm.crystal((120, 160, 30), eye), "fullbright"),
             ("Pupil", (0, 82, 57.5), (10, 30, 1), 0, fm.flat((20, 30, 10)), "flat")]
    for k in range(6):
        x = -40 + k * 16
        parts.append((f"Tooth_{k}", (x, 40, 58), (8, 14, 4), 0, fm.smooth(tooth), "flat"))
    for k, (x, z) in enumerate(((-52, -30), (52, -30), (-46, 30), (46, 30))):
        parts.append((f"Spine_{k}", (x, 90, z), (14, 50, 14), 15 * (1 if x > 0 else -1), fm.crystal(jade, (200, 255, 230)), "flat"))
    return parts


# Tentacule animé (moteur fractal_anim) : peau bleu nuit à taches turquoise, ventouses orangées sur la face avant (+Z,
# tournée vers l'arène), griffe de cristal au bout, motte de jade fendue à la base. 64 unités = 1 bloc.
T_SKIN, T_DARK, T_LIGHT = (40, 46, 86), (14, 16, 32), (84, 100, 150)
T_SPOT, T_SPOT_HOT = (40, 210, 190), (190, 255, 240)
T_SUCKER, T_SUCKER_DARK = (232, 132, 72), (140, 62, 30)
T_JADE, T_JADE_DARK, T_JADE_LIGHT = (70, 168, 120), (26, 84, 60), (150, 236, 190)
T_SEGMENTS = [(34, 32), (32, 29), (31, 26), (30, 23), (28, 20), (26, 17), (24, 14), (22, 11)]   # longueur, épaisseur
T_JOINTS = ["Root"] + [f"Seg{i}" for i in range(1, len(T_SEGMENTS) + 1)] + ["Claw"]


def tentacle_model():
    skin = fa.p_round(T_SKIN, T_DARK, T_LIGHT, top=T_LIGHT, streaks=3)
    spot = fa.p_glow(T_SPOT_HOT, T_SPOT)
    sucker = fa.p_round(T_SUCKER, T_SUCKER_DARK, (255, 190, 130))
    jade = fa.p_round(T_JADE, T_JADE_DARK, T_JADE_LIGHT, top=T_JADE_LIGHT, amp=0.08)
    crystal = fa.p_glow((220, 255, 240), T_JADE)
    claw = fa.Joint("Claw", (0, T_SEGMENTS[-1][0], 0), [
        fa.Box("Claw_Base", (0, 5, 0), (12, 10, 12), skin, rot=(0, 30, 0)),
        fa.Box("Claw_Tip", (0, 18, 2), (5, 22, 5), crystal, shading="fullbright", rot=(14, 45, 0)),
        fa.Box("Claw_Hook_L", (-5, 12, 5), (3, 14, 3), sucker, rot=(30, 0, 25)),
        fa.Box("Claw_Hook_R", (5, 12, 5), (3, 14, 3), sucker, rot=(30, 0, -25)),
    ], rot=(10, 0, 0))
    child = claw
    for i in range(len(T_SEGMENTS), 0, -1):
        length, thick = T_SEGMENTS[i - 1]
        twist = 13 * i
        parts = [
            fa.Box(f"Seg{i}_Box", (0, length / 2, 0), (thick, length + 4, thick), skin, rot=(0, twist, 0)),
            fa.Box(f"Seg{i}_Edge", (0, length / 2, 0), (thick * 0.84, length + 3, thick * 0.84), skin,
                   rot=(0, twist + 45, 0)),
            # ventouses sur la face avant, taches lumineuses sur le dos et les flancs
            fa.Box(f"Seg{i}_Sucker", (0, length * 0.5, thick / 2 + 0.6), (thick * 0.45, thick * 0.45, 2), sucker),
            fa.Box(f"Seg{i}_Spot", (0, length * 0.45, -thick / 2 - 0.4), (thick * 0.3, length * 0.4, 1), spot,
                   shading="fullbright"),
        ]
        if i % 2 == 0:
            side = 1 if i % 4 == 0 else -1
            parts.append(fa.Box(f"Seg{i}_Side", (side * (thick / 2 + 0.4), length * 0.6, 0), (1, length * 0.3, thick * 0.3),
                                spot, shading="fullbright"))
        child = fa.Joint(f"Seg{i}", (0, 12 if i == 1 else T_SEGMENTS[i - 2][0], 0), parts + [child])
    base = [
        fa.Box("Mound", (0, 5, 0), (64, 10, 58), jade, rot=(0, 12, 0)),
        fa.Box("Mound_Top", (3, 12, -2), (44, 8, 40), jade, rot=(3, 38, 2)),
        fa.Box("Crack_A", (-20, 14, 10), (8, 20, 8), crystal, shading="fullbright", rot=(-20, 30, 25)),
        fa.Box("Crack_B", (22, 12, -12), (7, 16, 7), crystal, shading="fullbright", rot=(15, 60, -20)),
        fa.Box("Shard_C", (8, 10, 24), (10, 6, 12), jade, rot=(-12, 70, 0)),
    ]
    return fa.Joint("Root", (0, 0, 0), base + [child])


def tentacle_pose(segs, root_rot=(0, 0, 0), root_off=(0, 0, 0), claw=(0, 0, 0)):
    pose = {"Root": (root_rot, root_off), "Claw": (claw, (0, 0, 0))}
    for i, r in enumerate(segs, 1):
        pose[f"Seg{i}"] = (r, (0, 0, 0))
    return pose


def tentacle_anims():
    n = len(T_SEGMENTS)
    K = fa.keys

    def sway(t, ax, az):
        return [(ax * math.sin(2 * math.pi * t - i * 0.6), 0, az * math.sin(2 * math.pi * t - i * 0.5 + 1.1))
                for i in range(n)]

    def idle(t):
        # Ondulation qui remonte le long du tentacule (boucle de 2,4 s), la griffe s'ouvre et se ferme.
        return tentacle_pose(sway(t / 2.4, 5, 4), root_rot=(0, 8 * math.sin(math.pi * t / 1.2), 0),
                             claw=(10 * math.sin(math.pi * t / 0.6), 0, 0))

    def spawn(t):
        k = K(t, [(0, 0), (0.55, 1)])
        return tentacle_pose([(25 * (1 - k), 0, 0)] * n, root_off=(0, -260 * (1 - k), 0))

    def hurt(t):
        k = K(t, [(0, 0), (0.06, 1), (0.25, 0)])
        return tentacle_pose([(-8 * k, 0, 5 * k)] * n)

    def death(t):
        k = K(t, [(0, 0), (0.7, 1)])
        sink = K(t, [(0, 0), (0.5, 0), (1.0, -200)])
        return tentacle_pose([(30 * k if i == 0 else 9 * k, 0, 4 * k) for i in range(n)], root_off=(0, sink, 0))

    def sweep(t):
        # 1,4 s d'armement : il se tord en arrière et pivote à gauche en tremblant ; puis il se couche vers l'avant et
        # balaie le cône de 160° devant lui, de gauche à droite, avant de se redresser.
        shake = math.sin(t * 50) * K(t, [(0, 0), (1.3, 3.5), (1.4, 0)])
        yaw = K(t, [(0, 0), (1.3, -85), (1.4, -85), (1.62, 85), (1.75, 85), (2.1, 0)])
        low = K(t, [(0, 0), (1.3, -0.3), (1.42, 1), (1.7, 1), (2.0, 0)])
        segs = []
        for i in range(n):
            x = low * (55 if i == 0 else 10 if i < 3 else -3) if low >= 0 else low * 30
            segs.append((x + shake, 0, shake * 0.6))
        return tentacle_pose(segs, root_rot=(0, yaw, 0), claw=(low * 25, 0, 0))

    def slam(t):
        # 1,2 s d'armement : il se dresse et se cambre en arrière ; puis il s'abat de tout son long devant lui (la ligne
        # rouge) et reste couché un instant avant de se relever.
        shake = math.sin(t * 46) * K(t, [(0, 0), (1.1, 3), (1.2, 0)])
        rear = K(t, [(0, 0), (1.1, 1), (1.2, 1), (1.32, 0)])
        fall = K(t, [(0, 0), (1.2, 0), (1.32, 1), (1.6, 1), (2.0, 0)])
        segs = []
        for i in range(n):
            back = -rear * (14 if i < 3 else 6)
            down = fall * (72 if i == 0 else 4 if i < 5 else -2)
            segs.append((back + down + shake, 0, 0))
        return tentacle_pose(segs, claw=(fall * 30 - rear * 20, 0, 0))

    return [
        fa.Anim("Idle", 2.4, idle, step=6, loop=True),
        fa.Anim("Spawn", 0.6, spawn, step=3),
        fa.Anim("Hurt", 0.25, hurt, step=3),
        fa.Anim("Death", 1.0, death, step=4, hold=True),
        fa.Anim("Sweep", 2.1, sweep, step=2),
        fa.Anim("Slam", 2.0, slam, step=2),
    ]


def write_tentacle(preview):
    view = {"size": 300, "scale": 0.9, "center": (0, 130, 0)}
    fa.build("Jade_Tentacle", tentacle_model(), T_JOINTS, tentacle_anims(), 72, 256, {
        "$Comment": "Tentacule de l'Abîme de Jade, animé (tools/generate_solid_ocean.py, moteur fractal_anim) : huit "
                    "segments octogonaux bleu nuit à taches turquoise, ventouses orangées, griffe de cristal, motte de "
                    "jade fendue. Ondule au repos, balaie (Sweep) et s'abat (Slam).",
        "EyeHeight": 3.2,
        "HitBox": {"Max": {"X": 0.6, "Y": 3.9, "Z": 0.6}, "Min": {"X": -0.6, "Y": 0, "Z": -0.6}},
        "MinScale": 1, "MaxScale": 1,
        "Light": {"Color": "#4fd", "Radius": 3},
    }, ["Sweep", "Slam"], preview, [
        ("repos", None, 0, view),
        ("ondule", "Idle", 0.6, view),
        ("balayage arme", "Sweep", 1.3, view),
        ("balayage", "Sweep", 1.55, dict(view, pitch=35)),
        ("abattu arme", "Slam", 1.15, dict(view, yaw=90, pitch=5)),
        ("abattu", "Slam", 1.45, dict(view, yaw=90, pitch=5)),
    ])


def tentacle_parts():
    jade, deep, tip = (70, 170, 120), (30, 100, 70), (200, 255, 220)
    parts = []
    for k in range(6):
        w = 26 - k * 3
        parts.append((f"Seg_{k}", (math.sin(k * 0.8) * 6, 14 + k * 26, math.cos(k * 0.7) * 4), (w, 28, w), k * 12,
                      fm.smooth(jade if k % 2 else deep, (130, 230, 180)), "flat"))
    parts.append(("Tip", (math.sin(4.8) * 6, 172, 0), (8, 18, 8), 30, fm.crystal(jade, tip), "fullbright"))
    for k in range(4):
        parts.append((f"Sucker_{k}", (0, 30 + k * 30, 11 - k * 1.5), (6, 6, 2), 0, fm.flat((210, 240, 200)), "flat"))
    return parts


def models():
    m = {}
    m[MAW] = fc.character_model("Jade_Maw", maw_parts(), 71, "L'Abîme de Jade (boss de l'Océan solide) : tête de kraken "
                                "en jade, œil unique. Immobile ; ses écailles denses le rendent invulnérable (Java).",
                                3.0, (1.0, 2.2), light={"Color": "#9f6", "Radius": 6}, scale=3.0)
    m[COLOSSUS] = {"$Comment": "Colosse de jade (phase 2) : le golem de cristal vanilla, un peu plus grand.",
                   "Parent": "Golem_Crystal_Thunder", "MinScale": COLOSSUS_SCALE, "MaxScale": COLOSSUS_SCALE,
                   "Light": {"Color": "#6f9", "Radius": 3}}
    m[IRUKANDJI] = {"$Comment": "Irukandji (provisoire) : l'esprit de givre vanilla, en attendant une méduse vérifiée dans "
                                "Assets.zip.", "Parent": "Spirit_Frost", "MinScale": 0.9, "MaxScale": 0.9,
                    "Light": {"Color": "#7ff", "Radius": 2}}
    return m


# --- attaques et rôles ------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
GOLEM_ANIMS = "Golem_Crystal_Thunder_Default"
COLOSSUS_SCALE = 1.1           # ×1,25 : trop gros (Kevin, 2026-10-24)
COLOSSUS_DAMAGE = 16
# Combo du golem de cristal vanilla (Root_NPC_Golem_Crystal_Attack), comme le golem de la Tour du mod Vampires : notre
# balayage au contact ne touchait jamais (même descendu aux pieds). Ses coups gardent leurs zones et animations vanilla,
# on ne règle que les dégâts et un recul faible (pas de chute dans le vide).
GOLEM_HITS = {"Swing_Left_Damage": "Golem_Crystal_Swing_Left_Damage", "Swing_Right_Damage": "Golem_Crystal_Swing_Right_Damage",
              "Spin_Damage": "Golem_Crystal_Spin_Damage", "Ground_Slam_Damage": "Golem_Crystal_Ground_Slam_Damage",
              "Stomp_Damage": "Golem_Crystal_Stomp_Damage", "Spin_Heavy_Damage": "Golem_Crystal_Spin_Heavy_Damage",
              "Clap_Damage": "Golem_Crystal_Clap_Damage"}
TENTACLE_ANIMS = "Nakasar_Fractal_Jade_Tentacle"


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Tentacle_Sweep"] = {
        "$Comment": "Tentacule : balayage annoncé tout autour de lui, cercle de 7 blocs (1,4 s), 22 dégâts et forte "
                    "projection (renversement de GW2).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.4, Radius=7, Damage=22, Knockback=10, KnockUp=4,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Tentacle_Emerge",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.4, "SFX_Spear_Throw_Charge", TENTACLE_ANIMS, "Sweep"),
                                           fc.windup(0.7, "SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Tentacle_Slam"] = {
        "$Comment": "Tentacule : s'abat devant lui, ligne de 8 × 2 blocs (1,2 s), 28 dégâts et étourdissement 1,5 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Line", 1.2, Length=8, Width=2, Damage=28, EffectId="Hazard_Electric_Stun",
                                                     EffectDuration=1.5, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.2, "SFX_Spear_Throw_Charge", TENTACLE_ANIMS, "Slam"),
                                           fc.windup(0.8, "SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Colossus_Slam"] = {
        "$Comment": "Colosse de jade : frappe le sol, cercle rouge de 5,5 blocs (1,5 s), 26 dégâts, projection et "
                    "étourdissement 1,5 s (renversement de GW2).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Radius=5.5, Damage=26, Knockback=7, KnockUp=4,
                                                     EffectId="Hazard_Electric_Stun", EffectDuration=1.5, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.5, "SFX_Spear_Throw_Charge", GOLEM_ANIMS, "GroundSlam")]}
    out["Nakasar_Fractal_Irukandji_Sting"] = {
        "$Comment": "Irukandji au contact : piqûre (12 dégâts et poison 4 s).",
        "Type": "Serial", "Interactions": [fr.swing("Piqûre.", None, None, 0.3, 12, end=2.4, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing", extra=[fr.effect_on_target("Poison_T1", 4)])]}
    out["Nakasar_Fractal_Irukandji_Shock"] = {
        "$Comment": "Irukandji : décharge autour de lui, cercle rouge de 3,5 blocs (1,2 s), 16 dégâts et forte projection : "
                    "sur un fragment de jade, elle jette dans le vide (la chute ramène au fragment d'avant).",
        "Type": "Serial", "Interactions": [T("Circle", 1.2, Radius=3.5, Damage=16, Knockback=9, KnockUp=4, PlayersOnly=True,
                                             ImpactParticle="Nakasar_Fractal_Colossus_Reflect"),
                                           fc.windup(1.2, "SFX_Spirit_Root_Alerted")]}
    out["Nakasar_Fractal_Irukandji_Tether"] = {
        "$Comment": "Irukandji : filament sur sa cible (marque d'éclairs 1,2 s, 8 dégâts), puis il l'attire contre lui, "
                    "au-dessus du vide s'il flotte entre deux fragments ; une piqûre suit (cercle de 2 blocs, 0,8 s, 14 "
                    "dégâts et poison). S'éloigner hors de portée (12 blocs) ou l'abattre avant de sauter.",
        "Type": "Serial", "Interactions": [
            T("Mark", 1.2, Damage=8, MarkParticle="Nakasar_Fractal_Lightning_Arc", MarkParticleScale=1.0,
              HitParticle="Nakasar_Fractal_Lightning_Arc"),
            fc.windup(1.2, "SFX_Spirit_Root_Alerted"),
            {"Type": "Nakasar_Fractal_Pull", "Range": 12, "StopDistance": 1.5, "Up": 3,
             "Particle": "Nakasar_Fractal_Lightning_Arc"},
            T("Circle", 0.8, Radius=2, Damage=14, EffectId="Poison_T1", EffectDuration=4, PlayersOnly=True,
              ImpactParticle="Nakasar_Fractal_Colossus_Reflect"),
            fc.windup(0.8, "SFX_Spear_Throw_Charge")]}
    return out


MELEE = ["Tentacle_Sweep", "Tentacle_Slam", "Colossus_Slam", "Irukandji_Sting", "Irukandji_Shock",
         "Irukandji_Tether"]
RANGED = []
R = fc.root


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[MAW] = fc.static_role(LANG, MAW, "L'Abîme de Jade, barre de boss : immobile et invulnérable (écailles denses). "
                              "Son rayon, ses phases et sa vie (cristaux et tentacules) sont menés par le Java "
                              "(solidocean.JadeMaw).", GENERATOR, 1000)
    tentacle = fr.role(
        TENTACLE, "Tentacule de l'Abîme : ne bouge pas, balaie autour de lui et s'abat devant lui. L'abattre blesse "
        "l'Abîme (Java).", TENTACLE, n(TENTACLE), 900,
        [fr.timed_attack("Sweep", R("Tentacle_Sweep"), rng=7, los=True, comment="Balayage annoncé."),
         fr.timed_attack("Slam", R("Tentacle_Slam"), rng=8, los=True, comment="Coup abattu annoncé.")],
        fr.walk(0.1, jump=0), GENERATOR, sight=12, leash=40, home=False,
        timers=[fr.timer("Sweep", (1, 3), (5, 7)), fr.timer("Slam", (3, 5), (6, 8))], KnockbackScale=0.0,
        DeathAnimationTime=1.0)
    out[TENTACLE] = tentacle
    out[COLOSSUS] = fr.role(
        COLOSSUS, "Colosse de jade : en phase 2, un sort du jade toutes les 30 s (10 en tout), insensible aux attaques à "
        "distance (Java), frappe le sol (cercle annoncé, renverse) et enchaîne le combo du golem vanilla au contact ; il lâche un cristal "
        "réfléchissant (Java).", COLOSSUS, n(COLOSSUS), 490,
        [fr.timed_attack("Slam", R("Colossus_Slam"), rng=5, los=True, comment="Frappe au sol annoncée."),
         fr.melee("Root_NPC_Golem_Crystal_Attack", 3.0, (1.0, 1.4), turn=0.6), fr.chase(40, stop=2.4)],
        fr.walk(3.0), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Slam", (3, 5), (8, 10))], KnockbackScale=0.1, DeathAnimationTime=1.5,
        InteractionVars={var: {"Interactions": [{"Parent": parent, "DamageCalculator": {
            "Type": "Absolute", "BaseDamage": {"Physical": COLOSSUS_DAMAGE}, "RandomPercentageModifier": 0.1},
            "DamageEffects": {"Knockback": {"Force": -4}}}]} for var, parent in GOLEM_HITS.items()})
    out[IRUKANDJI] = fr.role(
        IRUKANDJI, "Irukandji : flotte au-dessus des fragments de jade et garde le passage (600 PV) : décharge qui jette "
        "dans le vide, filament qui attire au-dessus du vide, piqûre empoisonnée.", IRUKANDJI, n(IRUKANDJI), 600,
        [fr.timed_attack("Tether", R("Irukandji_Tether"), rng=12, los=True, comment="Filament : attire sa cible."),
         fr.timed_attack("Shock", R("Irukandji_Shock"), rng=3.5, los=True, comment="Décharge annoncée."),
         fr.melee(R("Irukandji_Sting"), 2.4, (0.8, 1.2)), fr.chase(24, speed=1.0, stop=1.4, pathfinder=False)],
        fc.fly(4.5, 1, 4), GENERATOR, sight=14, leash=24, home=True,
        timers=[fr.timer("Shock", (2, 4), (6, 8)), fr.timer("Tether", (2, 5), (9, 12))], KnockbackScale=0.3,
        DeathAnimationTime=0.8)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(CRYSTAL, "Cristal réfléchissant", "Se ramasse accroupi, se tient à deux mains et reste en main (un seul à la "
           "fois). Il absorbe le rayon de l'Abîme de Jade et vous charge ; clic droit en visant l'Abîme : le lancer.",
           "Reflecting crystal", "Picked up while crouching, held in both hands and kept in hand (one at a time). It "
           "absorbs the Jade Maw's beam and charges you; right-click while aiming at the Maw: throw it.")
    for size, f, e in (("Block", "Bloc de cristal de jade", "Jade crystal block"),
                       ("Large", "Grand cristal de jade", "Large jade crystal"),
                       ("Medium", "Cristal de jade", "Jade crystal"), ("Small", "Petit cristal de jade", "Small jade crystal")):
        t.item(f"{JADE_CRYSTAL}_{size}", f, "Une chute ramène au dernier fragment de jade où l'on s'est tenu.", e,
               "A fall brings you back to the last jade fragment you stood on.")
    for role, f, e in ((MAW, "L'Abîme de Jade", "The Jade Maw"), (TENTACLE, "Tentacule de l'Abîme", "Jade Maw tentacle"),
                       (COLOSSUS, "Colosse de jade", "Jade colossus"), (IRUKANDJI, "Irukandji", "Irukandji")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Crystal_Charged", "Cristal chargé", "Charged crystal")
    t.put(f"effects.{TARGETED}", "Visé par l'Abîme : tenez un cristal !", "Targeted by the Maw: hold a crystal!")
    msgs = {
        "intro": ("Dessa : « Étrange. Les relevés disent que c'était de l'eau. Bonne nouvelle, la fractale semble "
                  "stable. » Traversez les fragments de jade : une chute ramène au fragment d'avant.",
                  "Dessa: \"How bizarre. The readings state that this was water once. Good news, this fractal appears "
                  "stable.\" Cross the jade fragments: a fall brings you back to the previous one."),
        "landing.back": ("Rattrapé au-dessus de l'océan figé : retour au dernier fragment.",
                         "Caught above the solid ocean: back to the last fragment."),
        "arena": ("Dessa : « Je retire ce que j'ai dit. Instabilité ! Juste devant vous ! » L'Abîme de Jade est "
                  "invulnérable : abattez les deux tentacules qui le protègent.",
                  "Dessa: \"I retract my statement. Unstable event! Right in front of you!\" The Jade Maw is invulnerable: "
                  "slay the two tentacles guarding it."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "agony": ("L'Abîme vous écrase de son agonie !", "The Maw crushes you with agony!"),
        "phase.colossi": ("L'Abîme s'éveille : quatre tentacules percent le jade et des colosses surgissent ({count} en "
                          "tout). Colosses et tentacules lâchent un cristal : ramassez-le (accroupi) et, quand l'Abîme "
                          "vous vise, tenez-en un !",
                          "The Maw awakens: four tentacles pierce the jade and colossi emerge ({count} in all). Colossi "
                          "and tentacles drop a crystal: pick it up (crouch) and hold one when the Maw targets you!"),
        "phase.final": ("Le dernier colosse est tombé : de nouveaux tentacules surgissent et "
                        "repoussent 30 s après leur mort.", "The last colossus has fallen: new tentacles emerge and "
                        "regrow 30 s after they fall."),
        "skull": ("L'Abîme vous vise : tenez un cristal avant la fin du compte à rebours, sinon le rayon vous tue !",
                  "The Maw targets you: hold a crystal before the countdown ends, or the beam kills you!"),
        "crystal.crouch": ("Accroupissez-vous pour ramasser le cristal.", "Crouch to pick up the crystal."),
        "crystal.already": ("Vous portez déjà un cristal.", "You already carry a crystal."),
        "skull.other": ("L'Abîme vise {name}.", "The Maw targets {name}."),
        "absorbed": ("Le cristal absorbe le rayon : vous êtes chargé. Lancez-le sur l'Abîme (clic droit) !",
                     "The crystal absorbs the beam: you are charged. Throw it at the Maw (right-click)!"),
        "beam.hit": ("Le rayon de l'Abîme vous foudroie.", "The Maw's beam strikes you down."),
        "crystal.noTarget": ("Visez l'Abîme de Jade pour lancer le cristal.", "Aim at the Jade Maw to throw the crystal."),
        "crystal.uncharged": ("Le cristal n'est pas chargé : laissez d'abord le rayon le frapper.",
                              "The crystal isn't charged: let the beam hit it first."),
        "crystal.hit": ("Le cristal chargé frappe l'Abîme !", "The charged crystal strikes the Maw!"),
        "crystal.drop": ("Un cristal réfléchissant tombe au sol.", "A reflecting crystal falls to the ground."),
        "last.beam": ("L'Abîme vise tout le monde : TENEZ UN CRISTAL !", "The Maw targets everyone: HOLD A CRYSTAL!"),
        "reflect": ("Le colosse est insensible aux attaques à distance : frappez-le au contact.",
                    "The colossus is immune to ranged attacks: strike it in melee."),
        "reset": ("L'Abîme de Jade se referme : tout est à recommencer.", "The Jade Maw closes: everything starts over."),
        "victory": ("Dessa : « La fractale est stable, grâce à l'Alchimie. Partez avant que quelque chose d'autre "
                    "n'apparaisse. »", "Dessa: \"The fractal's stable, thank the Alchemy. Now, hurry up and exit before "
                    "something else appears.\""),
        "title.victory": ("Océan solide terminé", "Solid Ocean complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -------------------------------------------------------------------------------------------------

def java_layout():
    J = fc
    # Un irukandji au-dessus de chaque fragment de rayon 3, deux sur ceux de rayon 4 (pas sur le premier).
    guards = [(x + dx, stand + 2, z) for x, z, r, stand in PATH[1:] if r >= 3
              for dx in ((-1, 1) if r >= 4 else (0,))]
    path_iru = J.jpoints(guards)
    def ring(radius, angles, up=0):
        return J.jpoints([(x, AR_STAND + up, z) for x, z in (ring_point(AR_CENTER, radius, a) for a in angles)])

    arena_iru = ring(AR_RADIUS - 4, ARENA_IRUKANDJI, 2)
    colossi = ring(COLOSSUS_RADIUS, COLOSSUS_ANGLES)
    zx0, zx1, zy0, zy1, zz0, zz1 = jump_zone()
    entry = (LAST[0], LAST[3], LAST[1])
    def spots(offsets):
        return J.jpoints([(AR_CENTER[0] + dx, AR_STAND, AR_CENTER[1] + dz) for dx, dz in offsets])

    tentacles, tentacles_p2, tentacles_p3 = spots(TENTACLE_SPOTS), spots(TENTACLE_SPOTS_P2), spots(TENTACLE_SPOTS_P3)
    return f"""package dev.nakasar.hytale.fractals.solidocean;

import dev.nakasar.hytale.fractals.arena.Box;

import java.util.List;

/**
 * Positions de l'Océan solide, écrites par tools/generate_solid_ocean.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SolidOceanLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Les fragments de jade et l'arène : une chute y ramène au dernier fragment. */
    public static final List<Box> JUMP_ZONES = List.of({J.jbox(zx0, zx1, zy0, zy1, zz0, zz1)});
    /** Irukandjis des grands fragments. */
    public static final double[][] PATH_IRUKANDJI = {path_iru};
    /** Dernier fragment avant l'arène (point de retour). */
    public static final double[] ARENA_CHECKPOINT = {J.jpoint(entry)};

    /** Arène de l'Abîme de Jade. */
    public static final double[] ARENA_CENTER = {J.jpoint((AR_CENTER[0], AR_STAND, AR_CENTER[1]))};
    public static final double ARENA_RADIUS = {AR_RADIUS};
    public static final double[] MAW = {J.jpoint(MAW_AT)};
    /** Points des tentacules : phase 1, phase 2, phase 3. */
    public static final double[][] TENTACLES = {tentacles};
    public static final double[][] TENTACLES_P2 = {tentacles_p2};
    public static final double[][] TENTACLES_P3 = {tentacles_p3};
    public static final double[][] COLOSSI = {colossi};
    public static final double[][] ARENA_IRUKANDJI = {arena_iru};
    public static final int[] REWARD = {J.jblock(REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(END_EXIT_AT)};

    private SolidOceanLayout() {{
    }}
}}
"""


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name.startswith(JADE_CRYSTAL):
        return (90, 220, 160)
    if name.startswith("Rock_Crystal") or name.startswith("Plant_Coral"):
        return (120, 240, 200)
    if name.startswith("Soil_Clay"):
        return (60, 110, 120)
    return (90, 120, 110)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, doc in jade_crystal_items().items():
        fc.write_json(go.ITEMS / f"{name}.json", doc)
    fc.write_json(fc.OBJECTS / f"{CRYSTAL}.json", crystal_item())
    fc.write_json(INTERACTIONS / "Nakasar_Fractal_Throw_Reflecting_Crystal.json", throw_interaction())
    fc.write_json(fc.ROOTS / "Root_Nakasar_Fractal_Throw_Reflecting_Crystal.json",
                  {"Interactions": ["Nakasar_Fractal_Throw_Reflecting_Crystal"], "RequireNewClick": True})
    fc.write_keep_in_hand()
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Crystal_Charged.png", (120, 255, 180), "stone")
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Jade_Targeted.png", (255, 48, 48), "skull")
    fc.write_json(fc.SERVER / f"Entity/Damage/{BEAM_CAUSE}.json", beam_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(INTERACTIONS / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    write_tentacle(preview)
    for role, doc in roles().items():
        fc.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p = course_prefab()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    counts = fc.write_instance(INSTANCE, "Océan solide", PREFAB_DIR, sections, SPAWN, "#70b8a8",
                                WEATHER, fc.weather("#060b18", "#14303a", "#1c3a42", (24, 230), 0.45, "#5a7898",
                                                             sun="#c8d8ff"), "00:30")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Océan solide : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(PATH)} fragments, arène en "
          f"{AR_CENTER} (debout à {AR_STAND}), Abîme en {MAW_AT}")
    if preview:
        fc.top_view(p, preview / "ocean_solide_dessus.png", color_of)


if __name__ == "__main__":
    main()
