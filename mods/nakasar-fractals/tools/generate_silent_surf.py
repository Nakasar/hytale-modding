#!/usr/bin/env python3
"""Génère le Ressac silencieux (Silent Surf), fractale de la saison 2 (docs/fractales/gdd.md), d'après GW2
(wiki.guildwars2.com/wiki/Silent_Surf_Fractal et hardstuck.gg/gw2/guides/fractal-maps/silent-surf).

    python3 mods/nakasar-fractals/tools/generate_silent_surf.py [--preview DOSSIER]

Une fractale de parcours : sous la mer de jade pétrifiée, une grotte sans fond que l'on traverse avec l'équipement de
prospection des Luxons (grappin, parachute, charge de poudre noire, fusée éclairante), recharges aux provisions
abandonnées de chaque point de contrôle. La Garde de Thess ramène au dernier point de contrôle qui tombe. Dans l'ordre :

1. la descente : parachute dans la crevasse, grappin, deux tyroliennes, chauves-souris au premier point de contrôle,
   la Mère de couvée et ses araignées au deuxième ;
2. les champignons rebondissants, le grappin sur la grande stalactite de jade, le canon à vent qui traverse le mur de
   jade ; les nagas au troisième point de contrôle ;
3. canon, tyrolienne, champignons, canon en l'air, piliers de jade, champignons, tyrolienne, canon, tyrolienne ; les
   Luxons corrompus et le second Dolus au quatrième ;
4. Kanaxai, Lame de l'Écueil, et ses Aspects, au-dessus du gouffre violet : Visage de l'effroi, Tempête déchirante,
   Tir de tourment, Ombres rassemblées (défiance), Fantasmagorie (Aspects privés sur les îles), Fendeur de mondes à 66
   et 33 %, Vitesse effrayante.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_SilentSurf`, les quatre objets
d'équipement, les blocs (champignon, provisions, ancres, canons, cercle, fusée, carnets), effets, particules, modèles,
rôles, le temps (grotte sombre, brume de jade), la langue `nakasar_fractals_silent_surf.lang` et
`silentsurf/SilentSurfLayout.java`. Repère : y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
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
import silent_surf_scenery as sc

LANG = "nakasar_fractals_silent_surf"
GENERATOR = "generate_silent_surf.py"
INSTANCE = "Nakasar_Fractal_SilentSurf"
WEATHER = "Nakasar_Fractal_Weather_SilentSurf"
PREFAB_DIR = "SilentSurf"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/silentsurf/SilentSurfLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/SilentSurf"
PARTICLE_TEXTURES = fc.COMMON / "Particles/Textures/Nakasar/Fractals"
pick = fc.pick

# --- objets, blocs, rôles ----------------------------------------------------------------------------------
GRAPPLE = "Nakasar_Fractal_Survey_Grapple"
PARACHUTE = "Nakasar_Fractal_Survey_Parachute"
POWDER = "Nakasar_Fractal_Survey_Powder"
FLARE = "Nakasar_Fractal_Survey_Flare"
GEAR = [GRAPPLE, PARACHUTE, POWDER, FLARE]
FLARE_LIGHT = "Nakasar_Fractal_Flare_Light"
BOUNCE_CAP, SUPPLIES, ZIP_ANCHOR = sc.BOUNCE_CAP, sc.SUPPLIES, sc.ZIP_ANCHOR
WIND_CANNON, RING = sc.WIND_CANNON, sc.CHECKPOINT_RING
JOURNAL = "Nakasar_Fractal_Sailor_Journal_"           # + numéro
THESS = "Nakasar_Fractal_Thess"
BAT = "Nakasar_Fractal_Cave_Bat"                       # celle du Volcanique (generate_volcanic)
SPIDERLING = "Nakasar_Fractal_Cave_Spiderling"
BROOD_MOTHER = "Nakasar_Fractal_Brood_Mother"
NAGA_RAIDER = "Nakasar_Fractal_Naga_Raider"
NAGA_STORMCALLER = "Nakasar_Fractal_Naga_Stormcaller"
NAGA_VENOMCALLER = "Nakasar_Fractal_Naga_Venomcaller"
NAGA_WAVECALLER = "Nakasar_Fractal_Naga_Wavecaller"
LUXON_SAILOR = "Nakasar_Fractal_Luxon_Sailor"
DOLUS = "Nakasar_Fractal_First_Mate_Dolus"
KANAXAI = "Nakasar_Fractal_Kanaxai"
ASPECT = "Nakasar_Fractal_Aspect_"                     # + Death, Exposure, Fear, Lethargy, Torment
ASPECTS = [ASPECT + k for k in sc.ASPECT_KINDS]
FOE_ROLES = [SPIDERLING, BROOD_MOTHER, NAGA_RAIDER, NAGA_STORMCALLER, NAGA_VENOMCALLER, NAGA_WAVECALLER,
             LUXON_SAILOR, DOLUS, KANAXAI] + ASPECTS
TORMENT_CAUSE = "Nakasar_Fractal_Torment"

# --- trajets guidés -------------------------------------------------------------------------------------------
ZIP_SPEED = 12.0
BOUNCE_HEIGHT = 9.0
RIDE_KINDS = {"zip": 0, "cannon": 1, "bounce": 2}
# Rencontre à finir avant chaque engin (indice du point de contrôle : 1 = chauves-souris, 2 = araignées...).
RIDE_LOCKS = {"z1": 1, "z2": 1, "c1": 2, "c2": 3, "z3": 3, "c3": 3, "z4": 3, "c4": 3, "z5": 3}
FIGHTS = {  # point de contrôle -> [(rôle, nombre)] (un de plus par paire de joueurs : Java)
    1: [(BAT, 4)],
    2: [(BROOD_MOTHER, 1), (SPIDERLING, 5), (BAT, 2)],
    3: [(NAGA_RAIDER, 2), (NAGA_STORMCALLER, 1), (NAGA_VENOMCALLER, 1), (NAGA_WAVECALLER, 1)],
    4: [(LUXON_SAILOR, 4)],
}


def catmull(points, step=0.5):
    """Courbe lisse (Catmull-Rom) passant par `points`, un point tous les `step` blocs environ."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        n = max(2, int(math.dist(p1, p2) / step))
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(tuple(points[-1]))
    return out


def arc(a, b, height, step=0.5):
    """Saut en cloche de `a` à `b` (pieds), sommet à `height` au-dessus du plus haut des deux."""
    n = max(4, int(math.dist(a, b) / step))
    top = max(a[1], b[1]) + height
    out = []
    for k in range(n + 1):
        t = k / n
        base = a[1] + (b[1] - a[1]) * t
        lift = (top - max(a[1], b[1])) * 4 * t * (1 - t) + (max(a[1], b[1]) - base) * math.sin(math.pi * t) * 0.9
        out.append((a[0] + (b[0] - a[0]) * t, base + lift, a[2] + (b[2] - a[2]) * t))
    return out


class Ride:
    def __init__(self, name, kind, path, speed, nxt=None, release=(0.0, 0.0, 0.0), lock=0):
        self.name, self.kind, self.path, self.speed = name, kind, path, speed
        self.next, self.release, self.lock = nxt, release, lock


class Course:
    """Le parcours posé : le prefab et ce que le Java doit connaître (trajets, cercles, apparitions...)."""

    def __init__(self):
        self.p = go.Prefab()
        self.cave = sc.Cave()
        self.tops = {}                  # (x, z) -> sol des plates-formes marchables
        self.keep = set()               # colonnes à laisser libres au plafond (trajets)
        self.rides = {}                 # nom -> Ride
        self.anchors = {}               # bloc (x, y, z) -> nom du trajet (tyroliennes, canons)
        self.caps = []                  # [(cases du chapeau, nom du trajet)]
        self.rings = []                 # [(centre (x, debout, z), rayon)]
        self.supplies = []
        self.thess = []
        self.fight_spawns = {}          # point de contrôle -> [(x, debout, z)]
        self.journals = []
        self.islands = []               # [(centre (x, debout, z), cases du chapeau du champignon de retour)]
        self.shell = set()              # cases de la grotte (pour l'aperçu en coupe)

    def stand(self, x, z):
        return self.tops[(round(x), round(z))] + 1

    def at(self, x, z):
        return (x, self.stand(x, z), z)


def build_course():
    c = Course()
    p = c.p
    before = set(p.blocks)
    c.cave.build(p)
    c.shell = set(p.blocks) - before
    sc.surface(p, c.cave)
    sc.wreck(p)
    for k, name in enumerate(sc.PLATFORMS):
        tops, _ = sc.platform(p, name, 740 + k * 7)
        c.tops.update(tops)
    features(c)
    rides(c)
    checkpoints(c)
    arena(c)
    journals(c)
    decor(c)
    c.cave.dress_ceiling(p, c.keep)
    return c


def features(c):
    """Grande stalactite de jade, mur de jade percé, piliers, anneau du canon en l'air."""
    p = c.p
    x, z, top, tip, r = sc.STALACTITE
    sc.big_stalactite(p, x, z, top, top - tip, r, 760,
                      block=lambda xx, yy, zz: sc.JADE if fn.hash01(xx, yy, zz, 761) < 0.75 else "Rock_Aqua")
    sc.jade_wall(p, c.cave)
    for k, (px, pz, ptop, pr) in enumerate(sc.PILLARS):
        sc.pillar(p, px, pz, ptop, pr, 770 + k)
        n = int(math.ceil(pr))
        for dx in range(-n, n + 1):
            for dz in range(-n, n + 1):
                if math.hypot(dx, dz) <= pr * 0.85:
                    c.tops[(px + dx, pz + dz)] = ptop - 1
    sc.jade_ring(p, *sc.C3_RING)


def rides(c):
    """Tyroliennes (câble de corde, ancres), canons à vent, champignons rebondissants."""
    p = c.p
    for name, (anchor, a, b) in sc.ZIPLINES.items():
        path = sc.zipline_points(name, 0.5)
        c.rides[name] = Ride(name, "zip", path, ZIP_SPEED, lock=RIDE_LOCKS.get(name, 0))
        for x, y, z in sc.cable_cells(name):
            if fn.free(p, x, y, z):
                p.set(x, y, z, "Deco_Rope")
        if anchor:
            ax, az, _ = anchor
            cell = (ax, c.stand(ax, az), az)
            p.set(*cell, ZIP_ANCHOR)
            c.anchors[cell] = name
        keep_path(c, path)
    for name, (block, pts, chain) in sc.CANNONS.items():
        path = catmull(pts)
        release = sc.C3_RELEASE if name == "c3" else (0.0, 0.0, 0.0)
        c.rides[name] = Ride(name, "cannon", path, sc.CANNON_SPEED, chain, release, RIDE_LOCKS.get(name, 0))
        if block:
            bx, bz, _ = block
            cell = (bx, c.stand(bx, bz), bz)
            # Canon du Gobliterator (vanilla) : bouche vers +Z du modèle, tournée vers le départ de la trajectoire.
            ahead = path[min(len(path) - 1, 8)]
            dx, dz = ahead[0] - bx, ahead[2] - bz
            p.set(*cell, WIND_CANNON, max(range(4), key=lambda k: go.FRONTS[k][0] * dx + go.FRONTS[k][1] * dz))
            c.anchors[cell] = name
        keep_path(c, path)
    for k, (mx, mz, r, s, target) in enumerate(sc.MUSHROOMS):
        cells = sc.mushroom(p, mx, mz, r, s, 780 + k, stem_to=sc.ABYSS)
        start = (mx + 0.5, s, mz + 0.5)
        name = f"b{k}"
        if target[0] == "apex":
            path, nxt, release = arc(start, target[1], 3.0), None, target[2]
        elif target[0] == "cannon":
            path, nxt, release = arc(start, c.rides[target[1]].path[0], BOUNCE_HEIGHT), target[1], (0.0, 0.0, 0.0)
        else:
            path, nxt, release = arc(start, c.rides[target[1]].path[0], 4.0), target[1], (0.0, 0.0, 0.0)
        length = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
        c.rides[name] = Ride(name, "bounce", path, length / sc.BOUNCE_SECONDS, nxt, release,
                             2 if k < 3 else 3)
        c.caps.append((cells, name))
        keep_path(c, path)


def keep_path(c, path):
    for x, _, z in path:
        for dx in (-2, -1, 0, 1, 2):
            for dz in (-2, -1, 0, 1, 2):
                c.keep.add((math.floor(x) + dx, math.floor(z) + dz))


def checkpoints(c):
    """Cercles blancs (marques de relevé), provisions abandonnées, Thess, et où apparaissent les ennemis."""
    p = c.p
    for k, (name, (rx, rz, rr), (sx, sz), (tx, tz)) in enumerate(sc.CHECKPOINTS):
        if name == "start":
            s = sc.SURFACE
            ground = lambda x, z: sc.sea_level(x, z)
        else:
            ground = lambda x, z: c.stand(x, z)
            s = ground(rx, rz)
        for dx in range(-rr - 1, rr + 2):
            for dz in range(-rr - 1, rr + 2):
                d = math.hypot(dx, dz)
                if rr - 0.6 <= d <= rr + 0.4:
                    x, z = rx + dx, rz + dz
                    p.set(x, ground(x, z) - 1, z, RING)
        c.rings.append(((rx, s, rz), rr))
        c.supplies.append((sx, ground(sx, sz), sz))
        p.set(sx, ground(sx, sz), sz, SUPPLIES)
        c.thess.append((tx, ground(tx, tz), tz))
        if k in FIGHTS:
            n = sum(count for _, count in FIGHTS[k]) + 2
            spots = []
            for j in range(n):
                a = math.radians(j * 360 / n + k * 23)
                for r in (7, 6, 5, 4):
                    x, z = round(rx + math.cos(a) * r), round(rz + math.sin(a) * r)
                    if (x, z) in c.tops:
                        spots.append(c.at(x, z))
                        break
            assert len(spots) >= n - 1, f"point de contrôle {name} : apparitions hors du sol"
            c.fight_spawns[k] = spots


def arena(c):
    """L'arène de Kanaxai : disque de pierre du cauchemar au-dessus du gouffre violet, cristaux violets au bord ; cinq
    îles autour, chacune avec un champignon qui ramène à l'arène."""
    p = c.p
    ax, az = sc.ARENA_C
    s = sc.ARENA_STAND
    tops = {}
    for x in range(ax - sc.ARENA_R - 3, ax + sc.ARENA_R + 4):
        for z in range(az - sc.ARENA_R - 3, az + sc.ARENA_R + 4):
            if math.hypot(x - ax, z - az) <= sc.ARENA_R + 0.8 * fn.fbm2(x, z, 5, 2, 790):
                tops[(x, z)] = s - 1
    for (x, z), y in tops.items():
        d = math.hypot(x - ax, z - az)
        ring = 9.5 <= d <= 10.5 or 15.5 <= d <= 16.2
        p.set(x, y, z, "Rock_Crystal_Purple_Block" if ring else pick(sc.NIGHTMARE, x, y, z))
    edge = fn.edge_distance(tops)
    fn.island(p, tops, lambda x, z: 3 + min(20, edge[(x, z)] * 1.4) + 3 * fn.fbm2(x, z, 6, 2, 791), 792, hang=0.1,
              theme=sc.CAVERN)
    c.tops.update(tops)
    for (x, z), y in tops.items():
        if edge[(x, z)] == 1 and fn.hash01(x, y, z, 793) < 0.18 and fn.free(p, x, y + 1, z):
            p.set(x, y + 1, z, sc.NIGHTMARE_CRYSTALS[int(fn.hash01(z, y, x, 794) * 3)])
    # îles : rocher sombre et jade, champignon de retour vers le bord de l'arène
    for k, (cx, cz, st) in enumerate(sc.island_centers()):
        itops = {}
        for x in range(cx - sc.ISLAND_R - 2, cx + sc.ISLAND_R + 3):
            for z in range(cz - sc.ISLAND_R - 2, cz + sc.ISLAND_R + 3):
                if math.hypot(x - cx, z - cz) <= sc.ISLAND_R * (1 + 0.15 * fn.fbm2(x, z, 4, 2, 795 + k)):
                    itops[(x, z)] = st - 1
        iedge = fn.edge_distance(itops)
        for (x, z), y in itops.items():
            p.set(x, y, z, pick(sc.NIGHTMARE, x, y, z) if fn.hash01(x, y, z, 796) < 0.7 else sc.JADE)
        fn.island(p, itops, lambda x, z: 3 + iedge[(x, z)] * 1.6, 797 + k, hang=0.2, theme=sc.CAVERN)
        c.tops.update(itops)
        # le champignon, au fond de l'île, à l'opposé de l'arène : on arrive du côté de l'arène (grappin) sans retomber
        # dessus, il ne renvoie qu'à qui va le chercher (Kevin, 25 octobre 2026 : il prenait trop de place et renvoyait
        # aussitôt à l'arrivée)
        a = math.atan2(az - cz, ax - cx)
        mx, mz = round(cx - math.cos(a) * (sc.ISLAND_R - 2.5)), round(cz - math.sin(a) * (sc.ISLAND_R - 2.5))
        cells = sc.mushroom(p, mx, mz, 1, st + 1, 798 + k, stem_to=st - 1)
        land = (ax + 0.5 + (cx - ax) * 0.25, s, az + 0.5 + (cz - az) * 0.25)
        path = arc((mx + 0.5, st + 1, mz + 0.5), land, 6.0)
        length = sum(math.dist(a1, b1) for a1, b1 in zip(path, path[1:]))
        name = f"i{k}"
        c.rides[name] = Ride(name, "bounce", path, length / 1.6)
        c.caps.append((cells, name))
        keep_path(c, path)
        c.islands.append(((cx, st, cz), name))
        for dx, dz in ((-3, -2), (2, 3)):
            x, z = cx + dx, cz + dz
            if (x, z) in itops and fn.free(p, x, st, z):
                p.set(x, st, z, sc.NIGHTMARE_CRYSTALS[(k + dx) % 3])


def journals(c):
    """Six carnets de marins luxons (Enquête sinistre), posés sur les plates-formes."""
    for k, (name, dx, dz) in enumerate(sc.JOURNALS):
        cx, cz = sc.PLATFORMS[name][:2]
        x, z = cx + dx, cz + dz
        assert (x, z) in c.tops, f"carnet {k} hors de sa plate-forme"
        c.p.set(x, c.stand(x, z), z, f"{JOURNAL}{k + 1}")
        c.journals.append((x, c.stand(x, z), z))


def decor(c):
    """Toiles au repaire des araignées, campement naga, cordages et caisses luxons, lanternes, mousse et champignons
    lumineux sur les plates-formes."""
    p = c.p
    occupied = set(c.anchors) | {tuple(x) for x in c.supplies} | {tuple(x) for x in c.journals}
    reserved = set()
    for (rx, s, rz), rr in c.rings:
        for dx in range(-rr - 2, rr + 3):
            for dz in range(-rr - 2, rr + 3):
                reserved.add((rx + dx, rz + dz))
    for x, _, z in c.thess + c.supplies + c.journals + list(c.anchors):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                reserved.add((x + dx, z + dz))

    def place(x, z, block, rot=0):
        if (x, z) in c.tops and (x, z) not in reserved and fn.free(p, x, c.stand(x, z), z):
            p.set(x, c.stand(x, z), z, block, rot)
            reserved.add((x, z))
            return True
        return False

    cx, cz = sc.PLATFORMS["cp2"][:2]
    for k in range(18):
        a = math.radians(k * 20 + 7)
        r = 8 + 3 * fn.hash01(k, 1, 0, 800)
        place(round(cx + math.cos(a) * r), round(cz + math.sin(a) * r),
              ("Deco_SpiderWeb", "Deco_SpiderWeb_Full", "Deco_Bone_Pile", "Deco_SpiderWeb_Flat")[k % 4])
    cx, cz = sc.PLATFORMS["cp3"][:2]
    for k in range(14):
        a = math.radians(k * 26 + 11)
        r = 8 + 3 * fn.hash01(k, 2, 0, 801)
        place(round(cx + math.cos(a) * r), round(cz + math.sin(a) * r),
              ("Plant_Coral_Bush_Cyan", "Deco_Coral_Shell", "Plant_Seaweed_Grass_Green", "Plant_Coral_Model_Green",
               "Furniture_Outlander_Banner")[k % 5])
    cx, cz = sc.PLATFORMS["cp4"][:2]
    for k in range(14):
        a = math.radians(k * 26 + 3)
        r = 8 + 3 * fn.hash01(k, 3, 0, 802)
        place(round(cx + math.cos(a) * r), round(cz + math.sin(a) * r),
              ("Furniture_Village_Crate", "Rock_Crystal_Purple_Medium", "Furniture_Tavern_Barrel", "Deco_Rope",
               "Rock_Crystal_Purple_Small")[k % 5])
    for name, (px, pz, pr, _, _) in sc.PLATFORMS.items():
        for k in range(3):
            a = math.radians(k * 120 + px)
            place(round(px + math.cos(a) * (pr - 1.5)), round(pz + math.sin(a) * (pr - 1.5)), sc.LANTERN)
        for (x, z) in sorted(c.tops):
            if math.hypot(x - px, z - pz) > pr * 1.3 or (x, z) in reserved:
                continue
            h = fn.hash01(x, 5, z, 803)
            if h < 0.05:
                place(x, z, sc.GLOW_MUSHROOMS[int(fn.hash01(z, 5, x, 804) * 4)])
            elif h < 0.1:
                place(x, z, ("Plant_Moss_Short_Green_Dark", "Plant_Moss_Rug_Green_Dark")[int(h * 40) % 2])
            elif h < 0.115:
                place(x, z, sc.JADE_SMALL)


# --- objets ---------------------------------------------------------------------------------------------------

def flare_parts():
    tube, cap, glow = (170, 40, 40), (60, 60, 64), (255, 120, 80)
    return [("Tube", (0, 5, 0), (3, 10, 3), 0, fm.smooth(tube), "flat"),
            ("Cap", (0, 10.5, 0), (3.4, 1.5, 3.4), 0, fm.smooth(cap), "flat"),
            ("Glow", (0, 12.5, 0), (2, 2.5, 2), 45, fm.crystal(glow, (255, 230, 200)), "fullbright")]


GEAR_STACK = {GRAPPLE: 3, PARACHUTE: 3, POWDER: 2, FLARE: 1}


def items():
    out = {}
    # Visuels vanilla (Kevin, 25 octobre 2026) : bombe gobeline pour la poudre, grappin (Tool_Hookshot) et planeur
    # (Template_Glider) du jeu ; notre mécanique ne change pas. id -> (modèle, texture, icône, réglages d'icône).
    looks = {
        POWDER: ("NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire.blockymodel",
                 "NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire_Texture.png",
                 "Icons/ItemsGenerated/Weapon_Bomb_Fire_Goblin.png",
                 {"Scale": 0.87, "Translation": [-7.11, -7.7], "Rotation": [4.685, 6.935, 315]}),
        GRAPPLE: ("Items/Tools/Hookshot/Scrap.blockymodel", "Items/Tools/Hookshot/Scrap_Texture.png",
                  "Icons/ItemsGenerated/Tool_Hookshot.png", {"Scale": 0.4, "Rotation": [333, 64, 0], "Translation": [-18, -24]}),
        PARACHUTE: ("Items/Glider/Bone_Closed.blockymodel", "Items/Glider/Bone_Texture.png",
                    "Icons/ItemsGenerated/Template_Glider.png", {"Scale": 0.275, "Rotation": [29, 48, 33], "Translation": [8, -18]}),
    }
    for item_id, model, parts, seed, center, scale in (
            (FLARE, "Survey_Flare", flare_parts(), 104, (0, 7, 0), 13.0),):
        root = f"Root_{item_id}"
        out[item_id] = fc.held_item(LANG, item_id, model, parts, seed, center, scale, quality="Rare",
                                    stack=GEAR_STACK[item_id],
                                    extra={"Interactions": {"Secondary": root}, "Utility": {"Compatible": False},
                                           "Categories": ["Items.Misc"]})
    for item_id, look in looks.items():
        out[item_id] = vanilla_held(item_id, *look, f"Root_{item_id}")
    return out


def vanilla_held(item_id, model, texture, icon, icon_properties, root):
    name = item_id.removeprefix("Nakasar_Fractal_")
    for stale in (fc.COMMON / fc.ITEM_MODELS / f"{name}.blockymodel", fc.COMMON / fc.ITEM_MODELS / f"{name}.png",
                  fc.COMMON / go.ICONS / f"{name}.png"):
        stale.unlink(missing_ok=True)
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
        "Icon": icon, "Model": model, "Texture": texture, "Quality": "Rare", "Categories": ["Items.Misc"],
        "PlayerAnimationsId": "Item", "ItemSoundSetId": "ISS_Items_Gems", "MaxStack": GEAR_STACK[item_id],
        "IconProperties": icon_properties,
        "Interactions": {"Secondary": root}, "Utility": {"Compatible": False},
    }


def gear_interactions():
    names = {GRAPPLE: "Grapple", PARACHUTE: "Parachute", POWDER: "Powder", FLARE: "Flare"}
    comments = {
        GRAPPLE: "Grappin : clic droit, le crochet file vers la roche visée (32 blocs) et tire le joueur jusqu'à elle "
                 "(Java, silentsurf.SurveyGear). Une charge.",
        PARACHUTE: "Parachute : clic droit en l'air, descente lente dans la direction du regard jusqu'au sol ; "
                   "s'accroupir le referme (Java). Une charge.",
        POWDER: "Charge de poudre noire : clic droit, l'explosion projette le joueur loin devant lui et vers le haut, "
                "sans dégâts de chute à l'arrivée (Java). Une charge.",
        FLARE: "Fusée éclairante : clic droit, une fusée file droit devant et éclaire la roche où elle se plante "
               "(40 s). Illimitée (Java).",
    }
    out = {}
    for item_id, gear in names.items():
        out[f"Nakasar_Fractal_Survey_{gear}"] = {"$Comment": comments[item_id], "Type": "Nakasar_Fractal_SurveyGear",
                                                 "Gear": gear}
    return out


# --- blocs ------------------------------------------------------------------------------------------------------

def blocks():
    """(id, texture, fond, couleur, glyphe, lumière, action, plein, alpha, opacité)."""
    use = lambda action: f"Nakasar_Fractal_Use_{action}"
    out = [
        (BOUNCE_CAP, "Bounce_Cap", (120, 50, 160), (220, 140, 255), "dots", "#a6f", None, True, 255, None),
        (SUPPLIES, "Leftover_Supplies", (110, 80, 50), (60, 190, 130), "rack", "#6c9", use("SilentSurf_Supplies"),
         True, 255, None),
        (ZIP_ANCHOR, "Zipline_Anchor", (90, 70, 50), (210, 180, 120), "rack", "#fc8", use("SilentSurf_Ride"), True,
         255, None),
        (WIND_CANNON, "Wind_Cannon", (70, 90, 96), (180, 240, 230), "rune", "#8fe", use("SilentSurf_Ride"), True,
         255, None),
        (RING, "Survey_Mark", (220, 224, 230), (255, 255, 255), "rune", "#fff", None, True, 255, None),
        (FLARE_LIGHT, "Flare_Light", (255, 120, 80), (255, 230, 200), "dots", "#f96", None, False, 0, None),
    ]
    for k in range(len(sc.JOURNALS)):
        out.append((f"{JOURNAL}{k + 1}", "Sailor_Journal", (60, 70, 66), (200, 190, 150), "book", None,
                    "Nakasar_Fractal_Read_Registry", True, 255, None))
    return out


def ride_interactions():
    return {
        "Nakasar_Fractal_Use_SilentSurf_Supplies": fc.use_interaction(
            "SilentSurf_Supplies", "Provisions abandonnées : rendent toutes les charges de l'équipement de "
            "prospection (et le donnent à qui ne l'a plus)."),
        "Nakasar_Fractal_Use_SilentSurf_Ride": fc.use_interaction(
            "SilentSurf_Ride", "Ancre de tyrolienne ou canon à vent : départ du trajet guidé (Java, silentsurf.Rides)."),
    }


# --- effets -----------------------------------------------------------------------------------------------------

def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Parachute_Open": fc.effect(
            L, "Nakasar_Fractal_Parachute_Open", "Parachute ouvert : descente lente (Java, vitesse posée à chaque pas).",
            "Parachute", 1.0),
        "Nakasar_Fractal_Thess_Ward": fc.effect(
            L, "Nakasar_Fractal_Thess_Ward", "Garde de Thess : une chute ramène au dernier point de contrôle (Java).",
            "Thess_Ward", 3600.0),
        "Nakasar_Fractal_Phantasmagoria": fc.effect(
            L, "Nakasar_Fractal_Phantasmagoria", "Fantasmagorie : un Aspect que vous seul voyez vous attend sur une île "
            "(Java, silentsurf.Aspects).", "Phantasmagoria", 30.0, debuff=True,
            ApplicationEffects={"EntityTopTint": "#7a3aa0", "EntityBottomTint": "#200830"}),
        "Nakasar_Fractal_Torment": fc.effect(
            L, "Nakasar_Fractal_Torment", "Tourment : dégâts chaque seconde, doublés quand on bouge (Java).", "Torment",
            6.0, debuff=True, ApplicationEffects={"EntityTopTint": "#5a2a7a"}),
        "Nakasar_Fractal_Exposure": fc.effect(
            L, "Nakasar_Fractal_Exposure", "Exposition : +50 % de dégâts subis.", "Exposure", 8.0, debuff=True,
            DamageResistance={k: [{"CalculationType": "Percent", "Amount": -0.5}]
                              for k in ("Physical", "Projectile", "Elemental")},
            ApplicationEffects={"EntityTopTint": "#c08040"}),
        "Nakasar_Fractal_Lethargy": fc.effect(
            L, "Nakasar_Fractal_Lethargy", "Léthargie : déplacement très ralenti.", "Lethargy", 5.0, debuff=True,
            ApplicationEffects={"HorizontalSpeedMultiplier": 0.5, "EntityTopTint": "#6a8a9a"}),
        "Nakasar_Fractal_Fear": fc.effect(
            L, "Nakasar_Fractal_Fear", "Peur : on fuit sans pouvoir rien faire (Java pousse le joueur loin de ce qui "
            "l'effraie).", "Fear", 2.0, debuff=True,
            ApplicationEffects={"MovementEffects": {"DisableAll": True}, "EntityTopTint": "#3a0a4a",
                                "EntityBottomTint": "#100018"}),
        "Nakasar_Fractal_Bleeding": fc.effect(
            L, "Nakasar_Fractal_Bleeding", "Saignement (flaque de la Tempête déchirante) : dégâts tant qu'on y reste "
            "(Java).", "Bleeding", 1.5, debuff=True, ApplicationEffects={"EntityBottomTint": "#8a1010"}),
    }


def status_icons():
    icons = fc.COMMON / fc.STATUS_ICONS
    fc.status_icon(icons / "Parachute.png", (230, 222, 196), "feather")
    fc.status_icon(icons / "Thess_Ward.png", (110, 230, 170), "plus")
    fc.status_icon(icons / "Torment.png", (170, 90, 220), "minus")
    fc.status_icon(icons / "Exposure.png", (230, 150, 70), "minus")
    fc.status_icon(icons / "Lethargy.png", (130, 170, 190), "feet")
    fc.status_icon(icons / "Bleeding.png", (220, 40, 40), "flame")
    eye_icon(icons / "Phantasmagoria.png", (190, 110, 255))
    eye_icon(icons / "Fear.png", (120, 40, 160))


def eye_icon(path, color):
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    d.ellipse((6, 6, 121, 121), fill=(26, 20, 34, 255), outline=c, width=6)
    d.ellipse((22, 44, 106, 84), fill=c)
    d.ellipse((50, 50, 78, 78), fill=(20, 4, 30, 255))
    d.ellipse((58, 56, 66, 64), fill=(255, 255, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def torment_cause():
    return fc.cause("Tourment, saignement et Visage de l'effroi du Ressac silencieux : une part des PV max, l'armure "
                    "ne le réduit pas.", "#b070e0")


# --- particules -------------------------------------------------------------------------------------------------

def particle_textures():
    """Œil du Visage de l'effroi et chiffres de la Vitesse effrayante (I à V, comme les marques de GW2)."""
    PARTICLE_TEXTURES.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(2, 32), (16, 16), (32, 10), (48, 16), (62, 32), (48, 48), (32, 54), (16, 48)], fill=(255, 255, 255, 255))
    d.ellipse((20, 20, 44, 44), fill=(30, 0, 40, 255))
    d.ellipse((28, 24, 36, 40), fill=(255, 255, 255, 255))
    img.save(PARTICLE_TEXTURES / "Dread_Eye.png")
    numerals = ["I", "II", "III", "IV", "V"]
    for k, n in enumerate(numerals):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((2, 2, 61, 61), outline=(255, 255, 255, 255), width=4)
        strokes = roman_strokes(n)
        for (x0, y0, x1, y1) in strokes:
            d.line((x0, y0, x1, y1), fill=(255, 255, 255, 255), width=5)
        img.save(PARTICLE_TEXTURES / f"Numeral_{k + 1}.png")


def roman_strokes(n):
    """Traits des chiffres romains dans un carré de 64 (la police par défaut de PIL est trop petite)."""
    glyphs = []
    width = sum(14 if ch == "V" else 6 for ch in n) + 4 * (len(n) - 1)
    x = 32 - width / 2
    for ch in n:
        if ch == "I":
            glyphs.append((x + 3, 18, x + 3, 46))
            x += 10
        else:
            glyphs += [(x, 18, x + 7, 46), (x + 7, 46, x + 14, 18)]
            x += 18
    return glyphs


S = gc.spawner
TEX = "Particles/Textures/Nakasar/Fractals"
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Wind_Burst": ("Canon à vent : souffle blanc et vert qui projette.",
                                   [("Wind", S("#ffffff", "#80ffd0", 26, (4.0, 8.0), (-20, 60), 1.0, 1.5,
                                               life=(0.4, 0.8)), 0.4)]),
    "Nakasar_Fractal_Wind_Trail": ("Traînée de vent derrière un joueur porté par un canon.",
                                   [("Trail", S("#ffffff", "#a0ffe0", 5, (0.2, 0.6), (-90, 90), 0.4, 0.4,
                                                life=(0.3, 0.6), size=(0.1, 0.2)), 0.6)]),
    "Nakasar_Fractal_Bounce": ("Champignon rebondissant : spores violettes.",
                               [("Spores", S("#f0c0ff", "#7a20c0", 20, (1.5, 3.5), (30, 90), 1.2, 0.4,
                                             life=(0.6, 1.0), size=(0.1, 0.25)), 0.2)]),
    "Nakasar_Fractal_Grapple_Line": ("Corde du grappin : un point de la corde (le Java en pose le long du trajet).",
                                     [("Rope", S("#e8d8b0", "#9a8058", 1, (0.0, 0.1), (0, 0), 0.0, 0.0,
                                                 life=(0.3, 0.4), size=(0.12, 0.12), blend="BlendLinear"), 0.0)]),
    "Nakasar_Fractal_Zip_Spark": ("Tyrolienne : étincelles de la poulie.",
                                  [("Sparks", S("#fff0c0", "#ff9040", 4, (0.6, 1.4), (-60, 10), 0.2, 0.2,
                                                life=(0.2, 0.4), size=(0.06, 0.1)), 0.0)]),
    "Nakasar_Fractal_Powder_Blast": ("Charge de poudre noire : explosion et fumée.",
                                     [("Fire", S("#fff0a0", "#ff5010", 24, (2.0, 5.0), (-10, 90), 0.8, 0.6,
                                                 life=(0.3, 0.6), size=(0.3, 0.6)), 0.3),
                                      ("Smoke", S("#a0a0a0", "#303030", 18, (0.6, 1.6), (20, 90), 1.4, 1.0,
                                                  life=(1.0, 1.6), size=(0.4, 0.8), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Flare_Trail": ("Fusée éclairante en vol : point rouge vif.",
                                    [("Spark", S("#ffffff", "#ff4020", 3, (0.0, 0.3), (-90, 90), 0.1, 0.1,
                                                 life=(0.3, 0.5), size=(0.2, 0.3)), 0.0)]),
    "Nakasar_Fractal_Flare_Burst": ("Fusée plantée : gerbe rouge et étincelles qui retombent.",
                                    [("Burst", S("#ffffff", "#ff3010", 30, (1.5, 4.0), (-30, 90), 0.4, 0.4,
                                                 life=(0.8, 1.4), size=(0.08, 0.16), gravity=-4), 0.2)]),
    "Nakasar_Fractal_Parachute": ("Parachute ouvert : voile claire au-dessus du joueur.",
                                  [("Canopy", S("#f8f0d8", "#c8b890", 10, (0.0, 0.2), (-5, 5), 1.4, 0.2,
                                                life=(0.3, 0.4), size=(0.5, 0.7), blend="BlendLinear"), 2.6)]),
    "Nakasar_Fractal_Thess_Ward": ("Garde de Thess : lueur de jade qui ramène un joueur tombé.",
                                   [("Glow", S("#e0fff0", "#30c080", 30, (0.8, 2.0), (-10, 90), 0.8, 2.0,
                                               life=(0.8, 1.2)), 0.2)]),
    "Nakasar_Fractal_Checkpoint": ("Point de contrôle atteint : anneau blanc.",
                                   [("Ring", S("#ffffff", "#a0ffe0", 30, (2.0, 3.0), (-5, 5), 0.5, 0.2,
                                               life=(0.6, 1.0)), 0.2)]),
    "Nakasar_Fractal_Dread_Eye": ("Visage de l'effroi : grand œil violet au-dessus de celui qui le lance (ne pas le "
                                  "regarder).",
                                  [("Eye", S("#ffd0ff", "#a020ff", 1, (0.0, 0.0), (0, 0), 0.0, 0.0, life=(2.4, 2.6),
                                             size=(2.4, 2.4), texture=f"{TEX}/Dread_Eye.png"), 0.0)]),
    "Nakasar_Fractal_Dread_Wave": ("Visage de l'effroi lancé : onde d'ombre.",
                                   [("Wave", S("#c080ff", "#200030", 40, (6.0, 10.0), (-5, 10), 0.6, 0.8,
                                               life=(0.4, 0.7), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Tether": ("Lien d'un Aspect : un point du fil violet (le Java en pose le long du lien).",
                               [("Beam", S("#ffb0ff", "#7a00c0", 1, (0.0, 0.1), (0, 0), 0.0, 0.0, life=(0.3, 0.35),
                                           size=(0.18, 0.18)), 0.0)]),
    "Nakasar_Fractal_Bleeding_Pool": ("Flaque de la Tempête déchirante : sang sombre au sol.",
                                      [("Pool", S("#ff4040", "#400000", 14, (0.1, 0.4), (60, 90), 1.6, 0.1,
                                                  life=(0.8, 1.2), size=(0.3, 0.5), blend="BlendLinear"), 0.1)]),
    "Nakasar_Fractal_Cleaver": ("Fendeur de mondes : éclair orange qui s'abat sur l'arène.",
                                [("Blast", S("#fff0c0", "#ff6000", 60, (4.0, 9.0), (0, 90), 6.0, 2.0,
                                             life=(0.6, 1.2), size=(0.3, 0.7)), 0.4)]),
    "Nakasar_Fractal_Shadows": ("Ombres rassemblées : volutes noires qui convergent vers Kanaxai.",
                                [("Wisps", S("#8040c0", "#000000", 16, (0.4, 1.0), (-30, 90), 3.0, 3.0,
                                             life=(0.8, 1.4), size=(0.3, 0.6), blend="BlendLinear"), 0.4)]),
    "Nakasar_Fractal_Aspect_Rise": ("Un Aspect apparaît : brume violette.",
                                    [("Mist", S("#e0b0ff", "#30004a", 24, (0.5, 1.6), (30, 90), 1.0, 2.0,
                                                life=(0.8, 1.4), blend="BlendLinear"), 0.2)]),
}
for _k in range(1, 6):
    PARTICLE_SYSTEMS[f"Nakasar_Fractal_Numeral_{_k}"] = (
        f"Vitesse effrayante : marque {_k} au sol, dans l'ordre où Kanaxai (ou Dolus) va bondir.",
        [("Mark", S("#ffffff", "#ff8040", 1, (0.0, 0.0), (0, 0), 0.0, 0.0, life=(1.9, 2.1), size=(1.4, 1.4),
                    texture=f"{TEX}/Numeral_{_k}.png"), 1.2)])


# --- modèles ------------------------------------------------------------------------------------------------------

LUXON = [("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
         ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
          gc.CLOTH, "Green"),
         ("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png"),
         ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
          "Faded_Leather", "Black"),
         ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
          "Faded_Leather", "Black")]
NAGA = [("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat_Green.png"),
        ("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
        ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
         "Faded_Leather", "Turquoise")]
ASPECT_COLORS = {"Death": "#6a6", "Exposure": "#fa6", "Fear": "#a6f", "Lethargy": "#6ac", "Torment": "#f6a"}


def models():
    m = {}
    m[THESS] = fr.humanoid("Thess, prospecteur luxon (provisoire) : capuche verte et cape de jade.", "04", "Face_Scar",
                           LUXON[:1] + [LUXON[1]] + LUXON[2:], light={"Color": "#6c9", "Radius": 3})
    m[LUXON_SAILOR] = fr.humanoid("Marin luxon corrompu (provisoire) : tenue de marin et cape, lueur violette du "
                                  "cauchemar.", "08", "Face_Sunken",
                                  [LUXON[0], (LUXON[1][0], LUXON[1][1], gc.CLOTH, "Purple")] + LUXON[2:],
                                  light={"Color": "#a6f", "Radius": 2})
    m[DOLUS] = fr.humanoid("Le second Dolus corrompu (provisoire) : grand marin luxon (× 1,3), manteau long.", "10",
                           "Face_Scar", [("Cosmetics/Overtops/TrenchCoat.blockymodel",
                                          "Cosmetics/Overtops/TrenchCoat_Greyscale.png"),
                                         ("Cosmetics/Capes/Cape_King_NoNeck.blockymodel",
                                          "Cosmetics/Capes/Cape_King_Texture.png")] + LUXON[2:],
                           scale=(1.3, 1.3), light={"Color": "#a6f", "Radius": 3})
    m[KANAXAI] = fr.humanoid("Kanaxai, Faux de la maison Aurkus (provisoire) : grand Luxon du cauchemar (× 1,7), robe "
                             "sombre, couronne et cape royale ; GW2 en fait un spectre au visage voilé.", "13",
                             "Face_Sunken", [("Cosmetics/Head/KingsCrown.blockymodel",
                                              "Cosmetics/Head/KingsCrown_Red.png"),
                                             ("Cosmetics/Overtops/Robe_Wizard.blockymodel",
                                              "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
                                             ("Cosmetics/Capes/Cape_King_NoNeck.blockymodel",
                                              "Cosmetics/Capes/Cape_King_Texture.png")] + LUXON[3:],
                             scale=(1.7, 1.7), light={"Color": "#a4f", "Radius": 5})
    for role, skin, face, gid in ((NAGA_RAIDER, "16", "Face_Scar", "Turquoise"),
                                  (NAGA_STORMCALLER, "17", "Face_Sunken", "Blue"),
                                  (NAGA_VENOMCALLER, "18", "Face_Sunken", "Lime"),
                                  (NAGA_WAVECALLER, "16", "Face_Scar", "Purple")):
        m[role] = fr.humanoid("Naga (provisoire) : humanoïde à la peau d'écailles et robe des grands fonds ; GW2 en fait "
                              "un homme-serpent.", skin, face, NAGA[:2] + [(NAGA[2][0], NAGA[2][1], "Faded_Leather", gid)],
                              scale=(1.15, 1.15) if role == NAGA_WAVECALLER else None,
                              light={"Color": "#8cf" if role != NAGA_WAVECALLER else "#a6f", "Radius": 2})
    m[SPIDERLING] = fc.vanilla_npc_model("Cave_Spiderling", "Araignée des cavernes : l'araignée des cavernes vanilla, "
                                         "petite (Spider_Cave_Spiderling).", parent="Spider_Cave_Spiderling")
    m[BROOD_MOTHER] = fc.vanilla_npc_model("Brood_Mother", "Mère de couvée des cavernes : l'araignée des cavernes "
                                           "vanilla, deux fois plus grande.", parent="Spider_Cave",
                                           light={"Color": "#9f6", "Radius": 3}, scale=2.0)
    for kind in sc.ASPECT_KINDS:
        m[ASPECT + kind] = {"$Comment": f"Aspect ({kind}) de Kanaxai (provisoire) : le spectre vanilla, lueur de son "
                                        "aspect.", "Parent": "Wraith", "MinScale": 1.2, "MaxScale": 1.2,
                            "Light": {"Color": ASPECT_COLORS[kind], "Radius": 3}}
    return m


# --- attaques et rôles --------------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
R = fc.root


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Spiderling_Bite"] = {
        "$Comment": "Araignée des cavernes : morsure (8 dégâts) qui ralentit.",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.35, 8, end=2.0, length=70,
                                                     sound="SFX_Unarmed_Swing",
                                                     extra=[fr.effect_on_target("Nakasar_Fractal_Crippled", 2)])]}
    out["Nakasar_Fractal_Brood_Mother_Bite"] = {
        "$Comment": "Mère de couvée : morsure (22 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.5, 22, end=3.6, length=90,
                                                     sound="SFX_Unarmed_Swing", extend_bottom=2.0)]}
    out["Nakasar_Fractal_Brood_Mother_Web"] = {
        "$Comment": "Mère de couvée : toile crachée sous sa cible, cercle rouge de 3 blocs (1,6 s), 14 dégâts et "
                    "immobilise 2 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Anchor="Target", Radius=3, Damage=14,
                                                     EffectId="Nakasar_Fractal_Rooted", EffectDuration=2,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Bounce"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Naga_Slash"] = {
        "$Comment": "Pillard naga : deux coups de lance (10 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de lance.", "Mace", "SwingLeft", 0.35, 10, end=3.0),
                                           fr.swing("Revers.", "Mace", "SwingRight", 0.35, 10, end=3.0,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Naga_Storm_Bolt"] = {
        "$Comment": "Mande-tempête naga : éclair sous sa cible, cercle rouge de 2 blocs (1,3 s), 16 dégâts.",
        "Type": "Serial", "Interactions": [T("Circle", 1.3, Anchor="Target", Radius=2, Damage=16, PlayersOnly=True,
                                             ImpactParticle="Nakasar_Fractal_Wind_Burst"), fc.windup(1.3)]}
    out["Nakasar_Fractal_Naga_Venom_Spit"] = {
        "$Comment": "Mande-venin naga : crachat sous sa cible, cercle rouge de 2,5 blocs (1,4 s), 10 dégâts et "
                    "ralentissement.",
        "Type": "Serial", "Interactions": [T("Circle", 1.4, Anchor="Target", Radius=2.5, Damage=10,
                                             EffectId="Nakasar_Fractal_Crippled", EffectDuration=3, PlayersOnly=True,
                                             ImpactParticle="Nakasar_Fractal_Bleeding_Pool"), fc.windup(1.4)]}
    out["Nakasar_Fractal_Naga_Wave"] = {
        "$Comment": "Mande-vague naga corrompu : vague devant lui, cône de 70° sur 9 blocs (1,8 s), 20 dégâts, "
                    "repousse.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.8, Angle=70, Radius=9, Damage=20, Knockback=10, KnockUp=3,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Wind_Burst"),
                                           fc.windup(1.8)]}
    out["Nakasar_Fractal_Luxon_Slash"] = {
        "$Comment": "Marin luxon corrompu : deux coups de sabre (11 dégâts chacun).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de sabre.", "Mace", "SwingLeft", 0.35, 11, end=3.0),
                                           fr.swing("Revers.", "Mace", "SwingRight", 0.35, 11, end=3.0,
                                                    direction="ToRight", yaw=-50)]}
    out["Nakasar_Fractal_Dolus_Cleave"] = {
        "$Comment": "Dolus : grand coup de hache devant lui, cône de 100° sur 5 blocs (1,2 s), 28 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.2, Angle=100, Radius=5, Damage=28, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.2, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    # Kevin (25 octobre 2026) : attaques de Kanaxai plus claires. La faux se lève lentement (animations vanilla de la
    # hache de bataille qu'il porte : charge puis balayage), le cône part un peu plus tard et la salve s'annonce
    # par l'animation d'incantation ; chaque zone rouge est exactement celle du coup.
    out["Nakasar_Fractal_Kanaxai_Cleave"] = {
        "$Comment": "Kanaxai : coup de faux devant lui, cône de 120° sur 7 blocs (1,8 s, faux levée puis balayage), "
                    "34 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.8, Angle=120, Radius=7, Damage=34, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.8, "SFX_Battleaxe_T2_Raise", "Battleaxe", "SwingLeftCharging"),
                                           fc.windup(0.5, "SFX_Battleaxe_T2_Swing", "Battleaxe", "Sweep")]}
    out["Nakasar_Fractal_Kanaxai_Volley"] = {
        "$Comment": "Kanaxai, salve des aspects : un cercle rouge de 2 blocs sous chaque joueur (2 s, Kanaxai incante), "
                    "14 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 2.0, Anchor="EachPlayer", Radius=2, Damage=14,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Aspect_Rise"),
                                           fc.windup(2.0, "SFX_Spear_Throw_Charge", "Battleaxe", "CastLeftCharging")]}
    out["Nakasar_Fractal_Aspect_Strike"] = {
        "$Comment": "Aspect de Kanaxai au contact : griffe d'ombre (12 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Griffe d'ombre.", None, None, 0.4, 12, end=2.6,
                                                     sound="SFX_Unarmed_Swing")]}
    return out


MELEE = ["Spiderling_Bite", "Brood_Mother_Bite", "Brood_Mother_Web", "Naga_Slash", "Naga_Wave",
         "Luxon_Slash", "Dolus_Cleave", "Kanaxai_Cleave", "Aspect_Strike"]
RANGED = ["Naga_Storm_Bolt", "Naga_Venom_Spit", "Kanaxai_Volley"]


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[SPIDERLING] = fr.role(SPIDERLING, "Araignée des cavernes : morsure qui ralentit.", SPIDERLING, n(SPIDERLING), 55,
                              [fr.melee(R("Spiderling_Bite"), 2.0, (0.7, 1.1)), fr.chase(30, stop=1.2)], fr.walk(4.6),
                              GENERATOR, sight=30, leash=40, home=False, KnockbackScale=1.0, DeathAnimationTime=0.6)
    out[BROOD_MOTHER] = fr.role(
        BROOD_MOTHER, "Mère de couvée des cavernes, barre de boss : toile qui immobilise, morsures ; elle pond des "
        "araignées (Java).", BROOD_MOTHER, n(BROOD_MOTHER), 2400,
        [fr.timed_attack("Web", R("Brood_Mother_Web"), rng=20, los=True, comment="Toile crachée."),
         fr.melee(R("Brood_Mother_Bite"), 3.6, (1.0, 1.4)), fr.chase(30, stop=2.6)],
        fr.walk(2.6), GENERATOR, sight=30, leash=40, home=False, timers=[fr.timer("Web", (3, 5), (8, 10))],
        KnockbackScale=0.0, DeathAnimationTime=1.5)
    out[NAGA_RAIDER] = fr.role(NAGA_RAIDER, "Pillard naga : coups de lance.", NAGA_RAIDER, n(NAGA_RAIDER), 140,
                               [fr.melee(R("Naga_Slash"), 2.6, (0.7, 1.1)), fr.chase(30, stop=1.6)], fr.walk(3.8),
                               GENERATOR, sight=30, leash=40, home=False, HotbarItems=["Weapon_Sword_Steel_Rusty"],
                               KnockbackScale=0.8, DeathAnimationTime=1.0)
    for role, attack, comment in ((NAGA_STORMCALLER, "Naga_Storm_Bolt", "Mande-tempête naga : éclairs annoncés."),
                                  (NAGA_VENOMCALLER, "Naga_Venom_Spit", "Mande-venin naga : crachats qui ralentissent.")):
        out[role] = fr.role(role, comment + " Il garde ses distances.", role, n(role), 100,
                            [fr.cast("Cast", R(attack), 20, "Sort annoncé."), fr.keep_distance(30, 6, 11)],
                            fr.walk(3.4), GENERATOR, sight=30, leash=40, home=False,
                            timers=[fr.timer("Cast", (1, 3), (5, 7))], HotbarItems=["Weapon_Staff_Crystal_Purple"],
                            KnockbackScale=1.0, DeathAnimationTime=1.0)
    out[NAGA_WAVECALLER] = fr.role(
        NAGA_WAVECALLER, "Mande-vague naga corrompu (élite), barre de boss : vague qui repousse, coups de bâton.",
        NAGA_WAVECALLER, n(NAGA_WAVECALLER), 1600,
        [fr.timed_attack("Wave", R("Naga_Wave"), rng=8, los=True, comment="Vague."),
         fr.melee(R("Naga_Slash"), 2.8, (0.8, 1.2)), fr.chase(30, stop=2.0)],
        fr.walk(3.0), GENERATOR, sight=30, leash=40, home=False, timers=[fr.timer("Wave", (3, 5), (9, 12))],
        HotbarItems=["Weapon_Staff_Crystal_Purple"], KnockbackScale=0.2, DeathAnimationTime=1.5)
    out[LUXON_SAILOR] = fr.role(LUXON_SAILOR, "Marin luxon corrompu : coups de sabre.", LUXON_SAILOR, n(LUXON_SAILOR), 170,
                                [fr.melee(R("Luxon_Slash"), 2.6, (0.7, 1.1)), fr.chase(30, stop=1.6)], fr.walk(3.8),
                                GENERATOR, sight=30, leash=40, home=False, HotbarItems=["Weapon_Sword_Steel_Rusty"],
                                KnockbackScale=0.8, DeathAnimationTime=1.0)
    out[DOLUS] = fr.role(
        DOLUS, "Le second Dolus corrompu, barre de boss : coups de hache ; Visage de l'effroi et Vitesse effrayante "
        "sont menés par le Java (silentsurf.Dolus).", DOLUS, n(DOLUS), 5000,
        [fr.timed_attack("Cleave", R("Dolus_Cleave"), rng=4.5, los=True, comment="Coup de hache."),
         fr.melee(R("Luxon_Slash"), 2.8, (0.8, 1.2)), fr.chase(30, stop=2.0)],
        fr.walk(3.6), GENERATOR, sight=30, leash=40, home=False, timers=[fr.timer("Cleave", (3, 5), (7, 9))],
        HotbarItems=["Weapon_Battleaxe_Steel_Rusty"], KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[KANAXAI] = fr.role(
        KANAXAI, "Kanaxai, Faux de la maison Aurkus, barre de boss : coups de faux, salve des aspects. Visage de "
        "l'effroi, Tempête déchirante, Ombres rassemblées, Fantasmagorie, Fendeur de mondes et Vitesse effrayante sont "
        "menés par le Java (silentsurf.Kanaxai). 8000 PV (Kevin, 25 octobre 2026 : trop long à 12000).", KANAXAI, n(KANAXAI),
        8000,
        [fr.timed_attack("Cleave", R("Kanaxai_Cleave"), rng=6, los=True, comment="Coup de faux."),
         fr.timed_attack("Volley", R("Kanaxai_Volley"), rng=40, comment="Salve des aspects."),
         fr.chase(40, stop=3.0)],
        fr.walk(3.4), GENERATOR, sight=40, leash=60, home=False,
        timers=[fr.timer("Cleave", (2, 4), (5, 7)), fr.timer("Volley", (6, 9), (13, 16))],
        HotbarItems=["Weapon_Battleaxe_Steel_Rusty"], KnockbackScale=0.0, DeathAnimationTime=2.0)
    for kind in sc.ASPECT_KINDS:
        role = ASPECT + kind
        out[role] = fr.role(role, f"Aspect ({kind}) de Kanaxai : griffe au contact ; son Tir de herse et son lien sont "
                            "menés par le Java (silentsurf.Aspects).", role, n(role), 700,
                            [fr.melee(R("Aspect_Strike"), 2.6, (1.0, 1.4)), fr.chase(6, stop=1.8)], fr.walk(1.2),
                            GENERATOR, sight=6, leash=10, home=False, KnockbackScale=0.0, DeathAnimationTime=1.0)
    out[THESS] = fc.static_role(LANG, THESS, "Thess, prospecteur luxon : guide les joueurs d'un point de contrôle à "
                                "l'autre (Java) ; on ne peut pas le blesser.", GENERATOR, 1000, attitude="Neutral",
                                foe=False)
    return out


# --- langue -------------------------------------------------------------------------------------------------------

JOURNAL_TEXTS = [
    ("Carnet de bord, page arrachée", "Torn logbook page",
     "Troisième jour sous la mer de jade. Dolus dit que la crevasse descend jusqu'au cœur du Ressac. Thess a tendu les "
     "premières cordes ; les hommes n'aiment pas le silence d'ici.",
     "Third day beneath the jade sea. Dolus says the crevasse runs down to the heart of the Surf. Thess has strung the "
     "first ropes; the crew dislikes the silence down here."),
    ("Carnet d'un mousse", "A deckhand's notebook",
     "Les champignons violets renvoient tout ce qui tombe dessus. J'y ai lâché une caisse : elle est remontée plus "
     "haut que le mât. Personne ne veut essayer le premier.",
     "The purple mushrooms throw back whatever lands on them. I dropped a crate on one: it flew higher than the mast. "
     "Nobody wants to try first."),
    ("Notes de prospection", "Survey notes",
     "Toiles partout près du deuxième relevé. Les araignées ont pondu dans nos caisses. On a laissé des provisions au "
     "cercle blanc pour ceux qui suivront.",
     "Webs everywhere near the second survey mark. The spiders laid eggs in our crates. We left supplies at the white "
     "circle for those who follow."),
    ("Lettre jamais envoyée", "A letter never sent",
     "Si tu lis ceci, Dessa, ne laisse pas Thess descendre plus bas. Il y a quelque chose sous le mur de jade. On "
     "l'entend respirer quand les canons se taisent.",
     "If you read this, Dessa, don't let Thess go any deeper. There is something beneath the jade wall. You can hear it "
     "breathe when the cannons fall quiet."),
    ("Journal du quartier-maître", "Quartermaster's journal",
     "Les nagas ont pris le troisième camp. Ils parlent d'une Faux qui rêve sous le gouffre et qui leur promet la mer. "
     "Dolus écoute leurs chants depuis trop longtemps.",
     "The naga took the third camp. They speak of a Scythe who dreams beneath the chasm and promises them the sea. "
     "Dolus has listened to their songs for too long."),
    ("Dernière page", "Last page",
     "Dolus nous a regardés et ses yeux n'étaient plus les siens. Ne le regardez pas en face. Ne regardez jamais le "
     "Visage. Kanaxai attend en bas, et il a faim.",
     "Dolus looked at us and his eyes were no longer his own. Do not look at him. Never look at the Visage. Kanaxai "
     "waits below, and he hungers."),
]


def lang():
    t = fc.Lang()
    t.item(GRAPPLE, "Grappin", "Clic droit : le crochet se plante dans la roche visée (32 blocs) et vous tire jusqu'à "
           "elle. Une charge.", "Grappling hook", "Right click: the hook bites into the rock you aim at (32 blocks) and "
           "pulls you to it. One charge.")
    t.item(PARACHUTE, "Parachute", "Clic droit en l'air : descente lente vers où vous regardez. S'accroupir le "
           "referme. Une charge.", "Parachute", "Right click in the air: glide down where you look. Crouch to close "
           "it. One charge.")
    t.item(POWDER, "Charge de poudre noire", "Clic droit : l'explosion vous projette loin devant, sans dégâts de "
           "chute. Une charge.", "Black powder charge", "Right click: the blast throws you far ahead, with no fall "
           "damage. One charge.")
    t.item(FLARE, "Fusée éclairante", "Clic droit : la fusée éclaire la roche où elle se plante.", "Flare",
           "Right click: the flare lights up the rock it hits.")
    t.item(BOUNCE_CAP, "Champignon rebondissant", "Sautez dessus : il vous renvoie au loin.", "Bouncing mushroom",
           "Jump on it: it sends you flying.")
    t.item(SUPPLIES, "Provisions abandonnées", "Utiliser : recharger l'équipement de prospection.", "Leftover supplies",
           "Use: refill your survey gear.")
    t.item(ZIP_ANCHOR, "Ancre de tyrolienne", "Utiliser : descendre la tyrolienne. S'accroupir pour lâcher.",
           "Zip line anchor", "Use: ride the zip line. Crouch to let go.")
    t.item(WIND_CANNON, "Canon à vent", "Utiliser : le vent vous emporte.", "Wind cannon", "Use: the wind carries you.")
    t.item(RING, "Marque de relevé", "Un cercle blanc des prospecteurs luxons : point de contrôle.", "Survey mark",
           "A white circle of the Luxon surveyors: checkpoint.")
    t.item(FLARE_LIGHT, "Lueur de fusée", "La lumière d'une fusée éclairante.", "Flare light", "The light of a flare.")
    for k, (nf, ne, df, de) in enumerate(JOURNAL_TEXTS):
        t.item(f"{JOURNAL}{k + 1}", nf, df, ne, de)
    for role, f, e in ((THESS, "Thess", "Thess"),
                       (SPIDERLING, "Araignée des cavernes", "Cave spiderling"),
                       (BROOD_MOTHER, "Mère de couvée des cavernes", "Cave spider brood mother"),
                       (NAGA_RAIDER, "Pillard naga", "Naga raider"), (NAGA_STORMCALLER, "Mande-tempête naga", "Naga stormcaller"),
                       (NAGA_VENOMCALLER, "Mande-venin naga", "Naga venomcaller"),
                       (NAGA_WAVECALLER, "Mande-vague naga corrompu", "Corrupted naga wavecaller"),
                       (LUXON_SAILOR, "Marin luxon corrompu", "Corrupted Luxon sailor"),
                       (DOLUS, "Le second Dolus corrompu", "Corrupted First Mate Dolus"),
                       (KANAXAI, "Kanaxai, Faux de la maison Aurkus", "Kanaxai, Scythe of House Aurkus"),
                       (ASPECT + "Death", "Aspect de la mort", "Aspect of Death"),
                       (ASPECT + "Exposure", "Aspect de l'exposition", "Aspect of Exposure"),
                       (ASPECT + "Fear", "Aspect de la peur", "Aspect of Fear"),
                       (ASPECT + "Lethargy", "Aspect de la léthargie", "Aspect of Lethargy"),
                       (ASPECT + "Torment", "Aspect du tourment", "Aspect of Torment")):
        t.npc(role, f, e)
    for eid, f, e in (("Parachute_Open", "Parachute ouvert", "Parachute open"),
                      ("Thess_Ward", "Garde de Thess", "Thess's Ward"),
                      ("Phantasmagoria", "Fantasmagorie", "Phantasmagoria"), ("Torment", "Tourment", "Torment"),
                      ("Exposure", "Exposition", "Exposure"), ("Lethargy", "Léthargie", "Lethargy"),
                      ("Fear", "Peur", "Fear"), ("Bleeding", "Saignement", "Bleeding")):
        t.put(f"effects.Nakasar_Fractal_{eid}", f, e)
    msgs = {
        "intro": ("Dessa : « Le Ressac silencieux. Thess vous attend en bas, avec l'équipement de prospection. »  "
                  "Thess : « Grappin, parachute, poudre noire, fusée : tout est à vous. Sautez dans la crevasse, "
                  "parachute ouvert ! »",
                  "Dessa: \"The Silent Surf. Thess is waiting below with the survey gear.\"  Thess: \"Grapple, "
                  "parachute, black powder, flare: all yours. Jump into the crevasse, parachute open!\""),
        "gear.given": ("Équipement de prospection reçu : grappin, parachute, poudre noire, fusée éclairante.",
                       "Survey gear received: grapple, parachute, black powder, flare."),
        "gear.refilled": ("Provisions abandonnées : équipement rechargé.", "Leftover supplies: gear refilled."),
        "gear.empty": ("Plus de charge : rechargez-vous aux provisions abandonnées d'un point de contrôle.",
                       "Out of charges: refill at the leftover supplies of a checkpoint."),
        "gear.noPowder": ("Thess : « Pas de poudre pour l'instant. Je vous en donne après le repaire des araignées. »",
                          "Thess: \"No powder yet. I'll give you some after the spider den.\""),
        "grapple.miss": ("Le grappin ne trouve aucune prise.", "The grapple finds no hold."),
        "parachute.ground": ("Le parachute ne s'ouvre qu'en l'air.", "The parachute only opens in the air."),
        "ride.locked": ("Thess : « Pas encore ! Débarrassez d'abord le camp. »", "Thess: \"Not yet! Clear the camp first.\""),
        "ward": ("Thess : « De justesse ! La Garde vous ramène au point de contrôle. »",
                 "Thess: \"That was close! The Ward brings you back to the checkpoint.\""),
        "checkpoint": ("Point de contrôle : la Garde de Thess vous y ramènera.",
                       "Checkpoint: Thess's Ward will bring you back here."),
        "cp1": ("Thess : « Premier relevé. Grappin vers la plate-forme de jade, puis la tyrolienne. Attention aux "
                "chauves-souris ! »", "Thess: \"First survey mark. Grapple to the jade platform, then the zip line. "
                "Watch out for the bats!\""),
        "cp2": ("Thess : « Le repaire des araignées. La mère de couvée ne va pas aimer ça. »",
                "Thess: \"The spider den. The brood mother won't like this.\""),
        "cp2.clear": ("Thess : « Voilà de la poudre noire. Sautez sur les champignons, puis grappin sur la grande "
                      "stalactite de jade. »", "Thess: \"Here's black powder. Jump on the mushrooms, then grapple the "
                      "great jade stalactite.\""),
        "cp3": ("Thess : « Des nagas ! Ils ont pris le camp. »", "Thess: \"Naga! They've taken the camp.\""),
        "cp3.clear": ("Thess : « Le canon à vent, puis la tyrolienne, les champignons, et les piliers de jade. »",
                      "Thess: \"The wind cannon, then the zip line, the mushrooms and the jade pillars.\""),
        "cp4": ("Thess : « Dolus ?! Qu'est-ce qu'ils t'ont fait... »", "Thess: \"Dolus?! What have they done to you...\""),
        "cp4.dolus": ("Le second Dolus corrompu : « Le Ressac a une voix, Thess. Elle chante pour moi. »",
                      "Corrupted First Mate Dolus: \"The Surf has a voice, Thess. It sings for me.\""),
        "cp4.clear": ("Thess : « Repose-toi, vieil ami. Kanaxai est en bas : parachute jusqu'à l'arène. »",
                      "Thess: \"Rest, old friend. Kanaxai is below: parachute down to the arena.\""),
        "fight.cleared": ("Le camp est dégagé.", "The camp is clear."),
        "dread": ("{name} : Visage de l'effroi ! Détournez le regard !", "{name}: Dread Visage! Look away!"),
        "dread.hit": ("Vous avez regardé le Visage de l'effroi !", "You looked at the Dread Visage!"),
        "speed": ("{name} : Vitesse effrayante ! Écartez-vous des marques I à V.",
                  "{name}: Frightening Speed! Stay off marks I to V."),
        "kanaxai.enter": ("Kanaxai : « Vous rêvez éveillés, mortels. Dans le Ressac, c'est moi qui rêve. »",
                          "Kanaxai: \"You dream awake, mortals. In the Surf, I am the one who dreams.\""),
        "kanaxai.thess": ("Thess tombe sous la faux de Kanaxai. Dessa : « Thess ! Non ! »",
                          "Thess falls to Kanaxai's scythe. Dessa: \"Thess! No!\""),
        "kanaxai.storm": ("Tempête déchirante : les joueurs marqués doivent s'écarter, leurs flaques restent au sol.",
                          "Rending Storm: marked players must spread out, their pools stay on the ground."),
        "kanaxai.harrow": ("Tir de herse : sortez des cercles des Aspects !", "Harrowshot: get out of the Aspects' circles!"),
        "kanaxai.shadows": ("Ombres rassemblées : brisez sa défiance !", "Gathering Shadows: break his defiance!"),
        "kanaxai.shadowsFail": ("Les ombres s'abattent : un Aspect s'éveille sur une île.",
                                "The shadows fall: an Aspect awakens on an island."),
        "kanaxai.tether": ("Un Aspect vous lie : coupez le lien avant qu'il ne vous emporte en Fantasmagorie !",
                           "An Aspect tethers you: break the link before it drags you into Phantasmagoria!"),
        "kanaxai.phantasm": ("Fantasmagorie : un Aspect que vous seul voyez vous attend sur l'île {island}. Grappin pour "
                             "y aller, champignon pour revenir.", "Phantasmagoria: an Aspect only you can see waits on "
                             "island {island}. Grapple there, mushroom back."),
        "kanaxai.cleaver": ("Kanaxai s'élève : Fendeur de mondes ! Tuez les Aspects avant qu'il ne frappe.",
                            "Kanaxai rises: World Cleaver! Kill the Aspects before he strikes."),
        "kanaxai.cleaverHit": ("Le Fendeur de mondes s'abat !", "The World Cleaver falls!"),
        "kanaxai.reset": ("Kanaxai se dissout dans le gouffre.", "Kanaxai dissolves into the chasm."),
        "kanaxai.victory": ("Kanaxai se brise : le Ressac retrouve son silence.", "Kanaxai shatters: the Surf falls "
                            "silent again."),
        "title.victory": ("Ressac silencieux terminé", "Silent Surf complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java ---------------------------------------------------------------------------------------------------------

def resample(path, step=1.5):
    """Points du trajet tous les `step` blocs le long de la courbe (le Java interpole entre eux)."""
    out = [path[0]]
    acc = 0.0
    for a, b in zip(path, path[1:]):
        acc += math.dist(a, b)
        if acc >= step:
            out.append(b)
            acc = 0.0
    if out[-1] != path[-1]:
        out.append(path[-1])
    return out


def reward_spots():
    ax, az = sc.ARENA_C
    a = math.atan2(sc.PLATFORMS["cp4"][1] - az, sc.PLATFORMS["cp4"][0] - ax)
    r = sc.ARENA_R - 5
    chest = (round(ax + math.cos(a) * r), sc.ARENA_STAND, round(az + math.sin(a) * r))
    exit_ = (round(ax + math.cos(a + 0.18) * r), sc.ARENA_STAND, round(az + math.sin(a + 0.18) * r))
    return chest, exit_


def java_layout(c):
    J = fc
    names = list(c.rides)
    index = {n: k for k, n in enumerate(names)}
    rides = [c.rides[n] for n in names]
    paths = "{" + ",\n            ".join(J.jpoints(resample(r.path), center=False) for r in rides) + "}"
    jd = J.jd
    release = "{" + ", ".join("{" + ", ".join(jd(v) for v in r.release) + "}" for r in rides) + "}"
    anchors = sorted(c.anchors)
    caps = [((sum(x for x, _, _ in cells) / len(cells) + 0.5, cells[0][1] + 1, sum(z for _, _, z in cells) / len(cells) + 0.5),
             name) for cells, name in c.caps]
    fights = []
    for k in range(len(c.rings)):
        fights.append(J.jpoints(c.fight_spawns.get(k, []), center=True))
    roles = "{" + ", ".join("{" + ", ".join(f'"{r}"' for r, _ in FIGHTS.get(k, [])) + "}" for k in range(len(c.rings))) + "}"
    counts = "{" + ", ".join("{" + ", ".join(str(n) for _, n in FIGHTS.get(k, [])) + "}" for k in range(len(c.rings))) + "}"
    ax, az = sc.ARENA_C
    chest, exit_ = reward_spots()
    edge = [sc.arena_point(a, sc.ARENA_R - 2, sc.ARENA_STAND) for a in sc.EDGE_ASPECTS]
    return f"""package dev.nakasar.hytale.fractals.silentsurf;

/**
 * Positions du Ressac silencieux, écrites par tools/generate_silent_surf.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SilentSurfLayout {{

    public static final double[] SPAWN = {J.jpoint(sc.SPAWN)};

    /** Points de contrôle (0 : départ sur la mer de jade, 1 à 4 : cercles blancs dans la grotte). */
    public static final double[][] RINGS = {J.jpoints([r[0] for r in c.rings])};
    public static final double[] RING_RADIUS = {{{", ".join(jd(r[1]) for r in c.rings)}}};
    public static final int[][] SUPPLIES = {J.jblocks(c.supplies)};
    public static final double[][] THESS = {J.jpoints(c.thess)};
    /** Ennemis de chaque point de contrôle (rôles, nombres, apparitions sur le pourtour du cercle). */
    public static final String[][] FIGHT_ROLES = {roles};
    public static final int[][] FIGHT_COUNTS = {counts};
    public static final double[][][] FIGHT_SPAWNS = {{{", ".join(fights)}}};

    /** Trajets guidés : tyroliennes (0), canons à vent (1), rebonds de champignon (2). */
    public static final String[] RIDE_NAMES = {{{", ".join(f'"{n}"' for n in names)}}};
    public static final int[] RIDE_KIND = {{{", ".join(str(RIDE_KINDS[r.kind]) for r in rides)}}};
    public static final double[] RIDE_SPEED = {{{", ".join(jd(round(r.speed, 2)) for r in rides)}}};
    /** Trajet qui suit (-1 : aucun) et vitesse à la sortie (blocs/s, zéro : on retombe). */
    public static final int[] RIDE_NEXT = {{{", ".join(str(index[r.next]) if r.next else "-1" for r in rides)}}};
    public static final double[][] RIDE_RELEASE = {release};
    /** Point de contrôle dont il faut avoir vaincu les ennemis pour partir (0 : libre). */
    public static final int[] RIDE_LOCK = {{{", ".join(str(r.lock) for r in rides)}}};
    public static final double[][][] RIDE_PATHS = {paths};
    /** Ancres de tyrolienne et canons à vent (bloc utilisé) -> trajet. */
    public static final int[][] RIDE_BLOCKS = {J.jblocks(anchors)};
    public static final int[] RIDE_BLOCK_RIDE = {{{", ".join(str(index[c.anchors[a]]) for a in anchors)}}};
    /** Chapeaux des champignons rebondissants (centre, debout dessus) -> trajet. */
    public static final double[][] CAPS = {J.jpoints([at for at, _ in caps], center=False)};
    public static final int[] CAP_RIDE = {{{", ".join(str(index[n]) for _, n in caps)}}};

    /** L'arène de Kanaxai. */
    public static final double[] ARENA_CENTER = {J.jpoint((ax, sc.ARENA_STAND, az))};
    public static final double ARENA_RADIUS = {jd(sc.ARENA_R)};
    /** Les cinq îles de la Fantasmagorie (centre, debout), dans l'ordre de leur numéro. */
    public static final double[][] ISLANDS = {J.jpoints([at for at, _ in c.islands])};
    /** Où se lèvent les Aspects au bord de l'arène (mort, exposition, peur, léthargie, tourment). */
    public static final double[][] EDGE_ASPECTS = {J.jpoints(edge, center=False)};
    public static final int[] REWARD = {J.jblock(chest)};
    public static final int[] END_EXIT = {J.jblock(exit_)};

    private SilentSurfLayout() {{
    }}
}}
"""


def color_of(name):
    c = fn.nature_color(name)
    if c and not name.startswith("Nakasar_"):
        return c
    if name in (BOUNCE_CAP,) or "Mushroom" in name:
        return (190, 90, 240)
    if name in (SUPPLIES, ZIP_ANCHOR, WIND_CANNON) or name.startswith(JOURNAL):
        return (240, 200, 80)
    if name == RING:
        return (255, 255, 255)
    if name == "Deco_Rope":
        return (255, 120, 60)
    if "Jade" in name or "Green" in name:
        return (60, 200, 140)
    if "Purple" in name:
        return (160, 80, 220)
    if name.startswith("Wood"):
        return (110, 80, 50)
    if name.startswith("Rock") or name.startswith("Soil"):
        return (90, 104, 110)
    return (200, 210, 220)


def cutaway(c):
    """La grotte sans son plafond ni la mer, pour les vues de dessus."""
    cut = go.Prefab()
    for cell, value in c.p.blocks.items():
        if cell in c.shell and (cell[0], cell[2]) in c.cave.inside:
            continue                    # plafond (les parois restent : elles dessinent le contour)
        if cell[1] >= sc.SURFACE - 4 and value[0] in sc.SEA + sc.SEA_CREST:
            continue
        cut.blocks[cell] = value
    return cut


def course_prefab():
    """Pour la carte du wiki (render_wiki_maps)."""
    return cutaway(build_course())


def preview_images(c, folder):
    """Vue de dessus en coupe (sans le plafond ni la mer) et trajets guidés en rouge."""
    cut = cutaway(c)
    path = folder / "ressac_dessus.png"
    fc.top_view(cut, path, color_of)
    img = Image.open(path)
    d = ImageDraw.Draw(img)
    xs = [k[0] for k in cut.blocks]
    zs = [k[2] for k in cut.blocks]
    x0, z0 = min(xs), min(zs)
    for r in c.rides.values():
        pts = [((x - x0) * 3, (z - z0) * 3) for x, _, z in r.path]
        d.line(pts, fill=(255, 40, 40), width=2)
    img.save(path)


# Kevin (25 octobre 2026) : modèles plus clairs, vanilla d'abord. Le chapeau rebondissant est un bloc de champignon violet
# vanilla (le reste du champignon aussi), les provisions la caisse ancienne vanilla (modèle 3D, différente des caisses du
# décor) ; leur lueur reste pour montrer qu'ils servent. Ces blocs n'ont plus de texture générée.
VANILLA_BLOCKS = {
    BOUNCE_CAP: {
        "Icon": "Icons/ItemsGenerated/Plant_Crop_Mushroom_Block_Purple.png",
        "BlockType": {"DrawType": "Cube", "Opacity": "Solid",
                      "Textures": [{"Weight": 1, "Sides": "BlockTextures/Mushroom_Block_Purple.png",
                                    "Up": "BlockTextures/Mushroom_Block_Top_Purple.png",
                                    "Down": "BlockTextures/Mushroom_Block_Purple_Trunk_Top.png"}],
                      "BlockParticleSetId": "Dust", "BlockSoundSetId": "Mushroom", "CubeShadingMode": "Flat"},
        "ItemSoundSetId": "ISS_Items_Foliage",
    },
    SUPPLIES: {
        "Icon": "Icons/ItemsGenerated/Furniture_Ancient_Crate.png",
        "BlockType": {"DrawType": "Model", "Opacity": "Transparent",
                      "CustomModel": "Blocks/Decorative_Sets/Ancient/Crate.blockymodel",
                      "CustomModelTexture": [{"Texture": "Blocks/Decorative_Sets/Ancient/Crate_Texture.png", "Weight": 1}],
                      "VariantRotation": "NESW", "BlockParticleSetId": "Wood", "BlockSoundSetId": "Wood"},
        "ItemSoundSetId": "ISS_Blocks_Wood",
    },
}


def write_vanilla_block(name, light, use):
    doc = go.block_item(name, name, light, use)
    doc["TranslationProperties"] = {"Name": f"{LANG}.items.{name}.name", "Description": f"{LANG}.items.{name}.description"}
    look = VANILLA_BLOCKS[name]
    doc["Icon"] = look["Icon"]
    doc["ItemSoundSetId"] = look["ItemSoundSetId"]
    block = doc["BlockType"]
    block.pop("Textures", None)
    block.update(look["BlockType"])
    fc.write_json(go.ITEMS / f"{name}.json", doc)
    for stale in (fc.COMMON / go.TEXTURES / f"{tex_of(name)}.png", fc.COMMON / go.ICONS / f"{tex_of(name)}.png"):
        stale.unlink(missing_ok=True)


def tex_of(name):
    return next(tex for n, tex, *_ in blocks() if n == name)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, tex, base, accent, glyph, light, use, solid, alpha, opacity in blocks():
        if name in VANILLA_BLOCKS:
            write_vanilla_block(name, light, use)
        else:
            fc.write_block(LANG, name, tex, base, accent, glyph, light, use, solid, alpha, opacity)
    for item_id, doc in items().items():
        fc.write_json(fc.OBJECTS / f"{item_id}.json", doc)
    for name, doc in gear_interactions().items():
        fc.write_json(go.INTERACTIONS / "SilentSurf" / f"{name}.json", doc)
        fc.write_json(fc.ROOTS / f"Root_{name}.json", {"Interactions": [name], "RequireNewClick": True})
    for name, doc in ride_interactions().items():
        fc.write_json(go.INTERACTIONS / "SilentSurf" / f"{name}.json", doc)
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    status_icons()
    fc.write_json(fc.SERVER / f"Entity/Damage/{TORMENT_CAUSE}.json", torment_cause())
    particle_textures()
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "SilentSurf" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fc.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    course = build_course()
    p = course.p
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Grotte de jade sombre : ciel noir (on ne le voit que depuis la mer), brume vert sombre, lumière faible.
    counts = fc.write_instance(INSTANCE, "Ressac silencieux", PREFAB_DIR, sections, sc.SPAWN, "#2a5a4a",
                               WEATHER, fc.weather("#02080a", "#0a1e1c", "#0c2420", (10, 110), 0.55, "#3a6a60",
                                                   sun="#a0e0c8"), "22:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(course), encoding="utf-8")
    print(f"Ressac silencieux : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(course.rides)} trajets, {len(PARTICLE_SYSTEMS)} particules")
    if preview:
        preview_images(course, preview)


if __name__ == "__main__":
    main()
