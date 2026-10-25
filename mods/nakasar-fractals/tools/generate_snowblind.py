#!/usr/bin/env python3
"""Génère la Tempête de neige (Snowblind), sixième fractale de la saison 1 (étape 8 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_snowblind.py [--preview DOSSIER]

Une fractale d'environnement (wiki.guildwars2.com/wiki/Snowblind_Fractal) : le froid tue plus que les ennemis.
Loin d'un feu, chaque joueur cumule de l'Hypothermie (dégâts selon les piles, éclat de glace au maximum) ; près d'un
feu allumé, la Chaleur la fait redescendre. Toujours la nuit. La carte (snowblind_scenery.py) suit celle de GW2 :
une vallée de montagne fermée, des ruines du nord à la grotte de glace du sud-ouest. Dans l'ordre :

1. le mur de glace : au pied de la colline, allumer le grand feu, qui fait fondre le mur barrant le col, d'autant plus
   vite qu'il est bien nourri. Les fagots se ramassent sous les sapins de la lisière. Des élémentaires de glace courent
   éteindre le feu pendant que les meutes de loups des neiges (et des Fils de Svanir une vague sur deux) attaquent ;
2. la Source élémentaire, au camp Svanir en haut des escaliers de glace : un géant de glace entouré de cinq foyers à
   allumer avec une torche (râtelier à l'entrée) et à nourrir avec les fagots posés devant les tentes. Chaque foyer
   éteint lui donne une pile de bouclier de givre. À 75, 50 et 25 %, il frappe les foyers (la moitié de leur bois).
   Tous éteints : blizzard (brume blanche, la tempête jette les joueurs ailleurs dans le camp) jusqu'à ce qu'on en
   rallume un ;
3. la forêt : le grand tour par l'est en suivant les empreintes, cinq groupes de Svanir et de loups autour de leurs feux ;
4. le Chaman légendaire, dans la grotte de glace : coups d'épée qui ajoutent de l'hypothermie, pluie de glace, anneau
   de pics, souffle glacé ; trois cristaux corrompus le protègent à chaque phase au contact. À 75 et 50 %, il saute sur
   sa corniche et fait pleuvoir des pics tant que l'Effigie de glace tient ; à 25 %, il devient ours.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Snowblind`, le fagot et la
torche portés, les blocs (feu de camp, foyers, tas de fagots, râtelier, empreintes), les effets, les particules, les
modèles et rôles, les deux temps (nuit, blizzard), la langue `nakasar_fractals_snowblind.lang` et `snowblind/SnowblindLayout.java`. Repère comme la
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
import snowblind_scenery as ss

LANG = "nakasar_fractals_snowblind"
GENERATOR = "generate_snowblind.py"
INSTANCE = "Nakasar_Fractal_Snowblind"
WEATHER = "Nakasar_Fractal_Weather_Snowblind"
BLIZZARD_WEATHER = "Nakasar_Fractal_Weather_Snowblind_Blizzard"
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

# --- lieux (y = debout à) : la carte est dans snowblind_scenery ---------------------------------------------
SPAWN = ss.SPAWN
CAMP, CAMP_RADIUS = ss.CAMP, ss.CAMP_RADIUS
BONFIRE_AT, BONFIRE_HEAT = ss.BONFIRE_AT, ss.BONFIRE_HEAT
FIREWOOD_SPOTS, ELEMENTAL_SPAWNS, WAVE_SPAWNS = ss.FIREWOOD_SPOTS, ss.ELEMENTAL_SPAWNS, ss.WAVE_SPAWNS
SOURCE_C, SOURCE_RADIUS, SOURCE_AT = ss.SOURCE_C, ss.SOURCE_RADIUS, ss.SOURCE_AT
BRAZIERS, BRAZIER_HEAT, TORCH_RACK_AT = ss.BRAZIERS, ss.BRAZIER_HEAT, ss.TORCH_RACK_AT
VILLAGE_C, VILLAGE_RADIUS, VILLAGE_FIRES = ss.VILLAGE_C, ss.VILLAGE_RADIUS, ss.VILLAGE_FIRES
BALCONY, EFFIGY_AT, SHAMAN_AT = ss.BALCONY, ss.EFFIGY_AT, ss.SHAMAN_AT
REWARD_AT, END_EXIT_AT = ss.REWARD_AT, ss.END_EXIT_AT
PACK_ROLES = {"cultist": CULTIST, "caster": ICE_CASTER, "wolf": WOLF}
PACK_TRIGGER = 30.0
FOREST_FIRE_HEAT = 6.0


class Course:
    """Le parcours posé : le prefab et les cases que le Java doit connaître (mur, portes, tas, groupes...)."""

    def __init__(self):
        self.t = ss.Terrain()
        self.p = go.Prefab()
        self.keep = ss.Keep()
        self.ice_wall = []
        self.gate_source = []
        self.gate_village = []
        self.huts = []
        self.packs = []                 # [(centre (x, y, z), [(rôle, (x, y, z))])]
        self.forest_fires = []
        self.blizzard_spots = []
        self.footprints = []

    def s(self, x, z):
        """Debout (entier, au-dessus d'une demi-dalle) sur la case (x, z)."""
        return math.ceil(self.t.stand[(x, z)])

    def at(self, x, z):
        return (x, self.s(x, z), z)


def gate_cells(t, center, path, top_of):
    """Barrière en travers du chemin `path` près de `center` : les cases praticables à moins d'un bloc de la ligne
    perpendiculaire au chemin, de debout à `top_of(x, z)` exclu."""
    samples = ss.curve(ss.PATHS[path])
    i, _ = ss.nearest_sample(samples, *center)
    a, b = samples[max(0, i - 3)], samples[min(len(samples) - 1, i + 3)]
    length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    tx, tz = (b[0] - a[0]) / length, (b[1] - a[1]) / length
    cx, cz = samples[i][0], samples[i][1]
    cells = []
    for (x, z), s in t.stand.items():
        along = (x - cx) * tx + (z - cz) * tz
        across = abs(-(x - cx) * tz + (z - cz) * tx)
        if -0.5 <= along <= 1.5 and across <= 9:
            for y in range(math.ceil(s), top_of(x, z)):
                cells.append((x, y, z))
    return cells


def course_prefab():
    return build_course().p


def build_course():
    c = Course()
    t, p, keep = c.t, c.p, c.keep
    ss.lay_ground(p, t)
    ss.lay_mountains(p, t)
    ss.lay_ceilings(p, t)
    start(c)
    camp(c)
    source_camp(c)
    woods(c)
    cave(c)
    for x, z in c.footprints:
        p.set(x, c.s(x, z) - 1, z, FOOTPRINTS)
    ss.forest(p, t, keep)
    ss.ground_cover(p, t, keep)
    for cell in c.gate_source + c.gate_village:
        p.set(*cell, MIST)
    return c


def start(c):
    """Le départ : replat des ruines en bois (échafaudages, caisses), la colline qui descend vers le grand feu."""
    p, keep = c.p, c.keep
    keep.disc(SPAWN[0], SPAWN[2], 6)
    for k, (x, z, w, d, h) in enumerate(((-70, -118, 4, 3, 5), (-34, -119, 5, 3, 6), (-64, -108, 3, 3, 4),
                                        (-28, -108, 3, 4, 4))):
        if all((xx, zz) in c.t.stand for xx in (x, x + w) for zz in (z, z + d)):
            ss.scaffold(p, x, z, w, d, h, c.s(x, z), 340 + k)
            keep.disc(x + w / 2, z + d / 2, max(w, d) / 2 + 2)
    for k, (x, z) in enumerate(((-58, -116), (-41, -117), (-45, -104), (-60, -102))):
        if (x, z) in c.t.stand:
            p.set(x, c.s(x, z), z, "Furniture_Village_Crate" if k % 2 else "Furniture_Tavern_Barrel")
            keep.disc(x, z, 1.5)


def camp(c):
    """Rencontre 1 : le grand feu au fond du bol, tas de fagots sous les sapins de la lisière, le col et son mur."""
    p, t, keep = c.p, c.t, c.keep
    bx, by, bz = BONFIRE_AT
    ss.campfire_ring(p, bx, bz, by, BONFIRE_OUT)
    keep.disc(bx, bz, 6)
    for k, (x, z) in enumerate(FIREWOOD_SPOTS):
        assert (x, z) in t.stand, f"tas de fagots hors du bol : {(x, z)}"
        p.set(x, c.s(x, z), z, PILE)
        keep.disc(x, z, 2)
        # le sapin qui l'abrite, un peu plus loin du feu
        a = math.atan2(z - bz, x - bx)
        tx, tz = round(x + math.cos(a) * 3), round(z + math.sin(a) * 3)
        if (tx, tz) in t.stand and fn.free(p, tx, c.s(tx, tz), tz):
            fn.conifer(p, tx, c.s(tx, tz), tz, 13 + k % 4, "fir_snow", seed=tx * 13 + tz)
        keep.disc(tx, tz, 2.5)
    for x, z in ELEMENTAL_SPAWNS + WAVE_SPAWNS:
        assert (x, z) in t.stand, f"apparition hors du bol : {(x, z)}"
        keep.disc(x, z, 2)
    # Planches et caisses brisées autour du feu (le camp ravagé des captures).
    for k, (dx, dz) in enumerate(((7, -4), (-8, 5), (5, 8), (-6, -7))):
        x, z = bx + dx, bz + dz
        for j in range(3):
            p.set(x + (j if k % 2 else 0), c.s(x, z), z + (0 if k % 2 else j), ss.PLANKS)
    # Le mur de glace barre tout le col.
    c.ice_wall = [(x, y, z) for (x, z), s in t.stand.items() if ss.WALL_Z[0] <= z <= ss.WALL_Z[1]
                  and t.center.get((x, z), ("",))[0] == "pass" for y in range(math.ceil(s), math.ceil(s) + ss.WALL_HEIGHT)]
    for cell in c.ice_wall:
        p.set(*cell, ICE)
    keep.cells |= {(x, z) for x, _, z in c.ice_wall}
    # Escaliers : bannières rouges en haut, de part et d'autre.
    for x, z in ((-58, -3), (-46, -3), (-60, 9), (-50, 7)):
        if (x, z) in t.stand:
            ss.banner(p, x, z, c.s(x, z), 0, 1)
            keep.disc(x, z, 2)


def source_camp(c):
    """Rencontre 2 : le camp Svanir. Cinq foyers autour de la Source, tentes en cercle (tas de fagots devant trois
    d'entre elles), palissade, bannières, pics de glace à l'entrée nord, râtelier de torches."""
    p, t, keep = c.p, c.t, c.keep
    sx, sz = SOURCE_C
    keep.disc(sx, sz, SOURCE_RADIUS + 1)
    for x, z in BRAZIERS:
        p.set(x, c.s(x, z) - 1, z, "Rock_Stone_Cobble")
        p.set(x, c.s(x, z), z, BRAZIER_OUT)
    for a, r in ss.TEEPEES:
        x = round(sx + math.cos(math.radians(a)) * r)
        z = round(sz + math.sin(math.radians(a)) * r)
        if (x, z) not in t.stand:
            continue
        ss.teepee(p, x, z, c.s(x, z), a + 180)
        keep.disc(x, z, 5)
        if a in ss.PILE_TEEPEES:
            px = round(sx + math.cos(math.radians(a)) * (r - 5))
            pz = round(sz + math.sin(math.radians(a)) * (r - 5))
            p.set(px, c.s(px, pz), pz, PILE)
            c.huts.append((px, pz))
    assert len(c.huts) == len(ss.PILE_TEEPEES), "un tas de fagots du camp est hors du sol"
    # Palissade sur le pourtour, ouverte au nord (escaliers) et à l'est (forêt).
    ring = []
    for k in range(0, 360, 3):
        if any(abs((k - g + 180) % 360 - 180) < 16 for g in (-74, 8)):
            continue
        x = round(sx + math.cos(math.radians(k)) * 29)
        z = round(sz + math.sin(math.radians(k)) * 29)
        ring.append((x, z))
    ss.palisade(p, t, ring, c.s)
    for k in range(0, 360, 40):
        x = round(sx + math.cos(math.radians(k + 12)) * 27.5)
        z = round(sz + math.sin(math.radians(k + 12)) * 27.5)
        if (x, z) in t.stand:
            ss.banner(p, x, z, c.s(x, z), sx - x, sz - z, 7)
    for x, z in ((-68, 12), (-56, 18)):
        if (x, z) in t.stand:
            ss.ice_spikes(p, x, z, c.s(x, z), 350 + x, 6, 2.5)
            keep.disc(x, z, 4)
    x, y, z = TORCH_RACK_AT
    assert (x, z) in t.stand and c.s(x, z) == y, "râtelier hors du chemin du camp"
    p.set(x, y, z, TORCH_RACK)
    keep.disc(x, z, 2)
    for k, (dx, dz) in enumerate(((-24, -8), (20, 18), (-10, 24), (22, -14))):
        x, z = sx + dx, sz + dz
        if (x, z) in t.stand and (x, z) not in keep:
            p.set(x, c.s(x, z), z, "Deco_Bone_Skulls" if k % 2 else "Deco_Bone_Spike")
    # Brume à la sortie est, jusqu'à la victoire.
    c.gate_source = gate_cells(t, ss.GATE_SOURCE_AT, "forest", lambda x, z: c.s(x, z) + 5)
    keep.cells |= {(x, z) for x, _, z in c.gate_source}
    # Taches de neige tassée où se pose le blizzard : points de téléportation.
    for r, n in ((6, 6), (11, 8), (16, 10)):
        for k in range(n):
            a = math.radians(k * 360 / n + r * 7)
            x, z = round(sx + math.cos(a) * r), round(sz + math.sin(a) * r)
            if (x, z) in t.stand and all(math.hypot(x - bx, z - bz) > 3 for bx, bz in BRAZIERS):
                c.blizzard_spots.append(c.at(x, z))


def woods(c):
    """La forêt : sentier aux empreintes, torches plantées, cinq groupes (Svanir et loups) autour de leurs feux, le
    plateau de l'est, l'avant-poste Svanir devant la grotte."""
    p, t, keep = c.p, c.t, c.keep
    samples = ss.curve(ss.PATHS["forest"], step=1.0)
    for i, (x, z, _, half) in enumerate(samples):
        keep.disc(x, z, 1.5)
        if 20 < i < len(samples) - 10 and i % 24 == 0:
            side = 1 if (i // 24) % 2 else -1
            a, b = samples[i - 2], samples[i + 2]
            length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            nx, nz = -(b[1] - a[1]) / length * side, (b[0] - a[0]) / length * side
            tx, tz = round(x + nx * (half - 0.5)), round(z + nz * (half - 0.5))
            if (tx, tz) in t.stand and fn.free(p, tx, c.s(tx, tz), tz):
                p.set(tx, c.s(tx, tz), tz, ss.TORCH_POST)
                keep.disc(tx, tz, 1.2)
    for k, ((x, z), roles) in enumerate(ss.PACKS):
        ss.campfire_ring(p, x, z, c.s(x, z), BONFIRE)
        keep.disc(x, z, 5)
        c.forest_fires.append((x, c.s(x, z), z))
        spawns = []
        for j, role in enumerate(roles):
            a = math.radians(j * 360 / len(roles) + k * 40)
            sx, sz = round(x + math.cos(a) * 4), round(z + math.sin(a) * 4)
            assert (sx, sz) in t.stand, f"groupe {k} : apparition hors du sol {(sx, sz)}"
            spawns.append((PACK_ROLES[role], c.at(sx, sz)))
        c.packs.append((c.at(x, z), spawns))
        if roles.count("wolf") == len(roles):
            for dx, dz, deco in ((3, -5, "Deco_Bone_Pile"), (-4, 4, "Deco_Bone_Ribs"), (5, 3, "Deco_Bone_Skulls")):
                if (x + dx, z + dz) in t.stand:
                    p.set(x + dx, c.s(x + dx, z + dz), z + dz, deco)
        else:
            a = math.radians(k * 70 + 30)
            tx, tz = round(x + math.cos(a) * 9), round(z + math.sin(a) * 9)
            if all((tx + dx, tz + dz) in t.stand for dx in (-3, 3) for dz in (-3, 3)):
                ss.teepee(p, tx, tz, c.s(tx, tz), math.degrees(a) + 180, 3.0, 6)
                keep.disc(tx, tz, 4.5)
            bx, bz = round(x - math.cos(a) * 7), round(z - math.sin(a) * 7)
            if (bx, bz) in t.stand:
                ss.banner(p, bx, bz, c.s(bx, bz), x - bx, z - bz)
                keep.disc(bx, bz, 1.5)
    # Avant-poste devant la grotte : feu, palissade, bannières, une tente.
    ox, oz = ss.OUTPOST
    ss.campfire_ring(p, ox, oz, c.s(ox, oz), BONFIRE)
    c.forest_fires.append((ox, c.s(ox, oz), oz))
    keep.disc(ox, oz, 6)
    ss.palisade(p, t, [(ox + 8, oz + dz) for dz in range(-6, 7) if abs(dz) > 1] +
                [(ox - 2 + dx, oz + 8) for dx in range(-6, 7)], c.s)
    for x, z in ((-25, 99), (-25, 106), (-10, 98)):
        if (x, z) in t.stand:
            ss.banner(p, x, z, c.s(x, z), 1, 0)
            keep.disc(x, z, 1.5)
    if all((ox + dx, oz + dz) in t.stand for dx in (-12, -6) for dz in (-6, -2)):
        ss.teepee(p, ox - 8, oz - 5, c.s(ox - 8, oz - 5), 45, 3.0, 6)
    c.footprints = ss.footprints(t, keep.cells - {(round(x), round(z)) for x, z, _, _ in samples})
    c.footprints = [f for f in c.footprints if t.stand[f] == math.floor(t.stand[f])]


def cave(c):
    """La grotte de glace : tunnel (brume à mi-chemin), arène sous le dôme, aiguilles et grappes de cristal au bord,
    trois foyers, la corniche du Chaman contre la paroi ouest."""
    p, t, keep = c.p, c.t, c.keep
    vx, vz = VILLAGE_C
    keep.disc(vx, vz, VILLAGE_RADIUS + 2)
    for x, z in VILLAGE_FIRES:
        p.set(x, c.s(x, z) - 1, z, "Rock_Stone_Cobble")
        p.set(x, c.s(x, z), z, BRAZIER)
    for k in range(14):
        a = math.radians(k * 360 / 14 + 9)
        r = VILLAGE_RADIUS - 2.5 - 2 * fn.hash01(k, 1, 0, 360)
        x, z = round(vx + math.cos(a) * r), round(vz + math.sin(a) * r)
        if (x, z) not in t.stand or x > vx + 12 and abs(z - vz) < 7:
            continue                    # l'entrée (est) reste dégagée
        if any(math.hypot(x - fx, z - fz) < 5 for fx, fz in VILLAGE_FIRES):
            continue
        color = ("Cyan", "Blue", "White")[k % 3]
        fn.crystal_spire(p, x, c.s(x, z), z, 5 + int(fn.hash01(k, 2, 0, 361) * 6), color, seed=362 + k)
    for (x, z) in sorted(t.cave):
        if (x, z) in t.stand and fn.hash01(x, 3, z, 363) < 0.025 and math.hypot(x - vx, z - vz) > 12 \
                and fn.free(p, x, c.s(x, z), z):
            p.set(x, c.s(x, z), z, ("Rock_Crystal_Cyan_Medium", "Rock_Crystal_Blue_Small", "Rock_Crystal_White_Large",
                                     "Rubble_Ice")[int(fn.hash01(z, 3, x, 364) * 4)])
    # Corniche du Chaman : plate-forme de glace sur piliers, au pied de la paroi ouest (on n'y monte pas).
    bx, by, bz = BALCONY
    for x in range(bx - 4, bx + 4):
        for z in range(bz - 4, bz + 5):
            if (x, z) in t.stand:
                p.set(x, by - 1, z, ICE if (x + z) % 2 else "Rock_Ice_Permafrost")
                if x == bx + 3 and abs(z - bz) <= 4:
                    p.set(x, by, z, "Rock_Ice_Icicles")
    for x, z in ((bx + 3, bz - 4), (bx + 3, bz + 4), (bx - 2, bz - 4), (bx - 2, bz + 4)):
        for y in range(c.s(x, z), by - 1):
            p.set(x, y, z, ICE)
    # Brume au milieu du tunnel : elle se ferme quand on entre dans l'arène.
    c.gate_village = gate_cells(t, ss.GATE_VILLAGE_AT, "tunnel", lambda x, z: t.ceiling.get((x, z), c.s(x, z) + 5))
    keep.cells |= {(x, z) for x, _, z in c.gate_village}


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
                       (CULTIST, "Fils de Svanir", "Son of Svanir"), (ICE_CASTER, "Incantateur de Svanir", "Svanir frost caster"),
                       (SOURCE, "Source élémentaire", "Elemental Source"), (SHAMAN, "Chaman légendaire", "Legendary Shaman"),
                       (BEAR, "Chaman légendaire (ours)", "Legendary Shaman (bear)"), (EFFIGY, "Effigie de glace", "Ice Effigy"),
                       (CRYSTAL, "Cristal de glace corrompu", "Corrupted ice crystal"), (SHARD, "Éclat de glace", "Ice shard")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Warmth", "Chaleur", "Warmth")
    t.put("effects.Nakasar_Fractal_Encased", "Pris dans la glace", "Encased in ice")
    for tier in range(1, HYPOTHERMIA_TIERS + 1):
        t.put(f"effects.Nakasar_Fractal_Hypothermia_{tier}", f"Hypothermie {tier * 2}", f"Hypothermia {tier * 2}")
    msgs = {
        "intro": ("Tempête de neige : loin d'un feu, le froid s'accumule (Hypothermie). Descendez la colline jusqu'au grand "
                  "feu et allumez-le avec un fagot pris sous les sapins : il fera fondre le mur de glace du col.",
                  "Snowblind: away from a fire, the cold builds up (Hypothermia). Go down the hill to the great campfire "
                  "and light it with firewood from under the firs: it will melt the ice wall in the pass."),
        "fire.need": ("Il faut un fagot pour l'allumer.", "You need firewood to light it."),
        "fire.lit": ("Le grand feu prend : le mur de glace commence à fondre. Nourrissez-le !",
                     "The great fire catches: the ice wall starts to melt. Keep feeding it!"),
        "fire.fed": ("Fagot ajouté : {fuel} %.", "Firewood added: {fuel} %."),
        "fire.full": ("Le feu est déjà au plus fort.", "The fire is already at its strongest."),
        "fire.out": ("Le grand feu s'est éteint ! Rallumez-le avec un fagot.", "The great fire went out! Relight it with firewood."),
        "fire.doused": ("Un élémentaire de glace atteint le feu et l'étouffe !", "An ice elemental reaches the fire and smothers it!"),
        "fire.elementals": ("Des élémentaires de glace sortent de la forêt : arrêtez-les avant le feu !",
                            "Ice elementals come out of the forest: stop them before the fire!"),
        "fire.wolves": ("Une meute de loups des neiges fond sur le feu !", "A pack of snow wolves rushes the fire!"),
        "fire.wave": ("Loups et Fils de Svanir attaquent le feu !", "Wolves and Sons of Svanir attack the fire!"),
        "wall.melted": ("Le mur de glace a fondu : le col est libre. Montez les escaliers de glace jusqu'au camp Svanir.",
                        "The ice wall has melted: the pass is clear. Climb the ice stairs to the Svanir camp."),
        "wood.taken": ("Fagot pris ({count}/3).", "Firewood taken ({count}/3)."),
        "wood.full": ("Vous portez déjà trois fagots.", "You already carry three bundles of firewood."),
        "torch.taken": ("Torche prise : allumez les foyers autour de la Source.", "Torch taken: light the braziers around the Source."),
        "torch.has": ("Vous avez déjà une torche.", "You already have a torch."),
        "brazier.need": ("Il faut une torche pour allumer ce foyer.", "You need a torch to light this brazier."),
        "brazier.lit": ("Foyer allumé ({count}/5) : le bouclier de givre de la Source faiblit.",
                        "Brazier lit ({count}/5): the Source's frost shield weakens."),
        "brazier.fed": ("Foyer nourri : {fuel} %.", "Brazier fed: {fuel} %."),
        "brazier.wood": ("Il faut un fagot (devant les tentes) pour nourrir ce foyer.",
                         "You need firewood (in front of the tents) to feed this brazier."),
        "brazier.full": ("Ce foyer brûle déjà au plus fort.", "This brazier already burns at its strongest."),
        "brazier.out": ("Un foyer s'éteint ({count}/5 allumés).", "A brazier goes out ({count}/5 lit)."),
        "source.enter": ("La Source élémentaire ! Allumez les foyers (torche au râtelier) : chaque foyer éteint lui donne "
                         "une pile de bouclier de givre.", "The Elemental Source! Light the braziers (torch at the rack): "
                         "each unlit brazier gives it a stack of frost shield."),
        "source.strike": ("La Source frappe les foyers !", "The Source strikes the braziers!"),
        "source.blizzard": ("Tous les foyers sont éteints : BLIZZARD ! On n'y voit plus rien et la tempête va vous emporter. "
                            "Rallumez un foyer avec une torche.",
                            "Every brazier is out: BLIZZARD! You can't see a thing and the storm will sweep you away. "
                            "Relight a brazier with a torch."),
        "source.scatter": ("La tempête vous emporte !", "The storm sweeps you away!"),
        "source.calm": ("Un foyer brûle : le blizzard retombe.", "A brazier burns: the blizzard dies down."),
        "source.reset": ("La Source se fige dans la glace.", "The Source freezes in the ice."),
        "source.victory": ("La Source élémentaire se brise : la brume de l'est s'ouvre sur la forêt. Prenez une torche et "
                           "suivez les traces jusqu'à la grotte de glace.", "The Elemental Source shatters: the eastern "
                           "mist opens onto the forest. Take a torch and follow the tracks to the ice cave."),
        "shaman.enter": ("Le Chaman légendaire, au fond de la grotte de glace ! Ses coups d'épée glacent : restez près des "
                         "foyers.", "The Legendary Shaman, deep in the ice cave! His sword strikes freeze: stay near the "
                         "braziers."),
        "shaman.crystals": ("Le Chaman invoque trois cristaux corrompus : il ne prend aucun dégât tant qu'ils tiennent.",
                            "The Shaman summons three corrupted crystals: he takes no damage while they stand."),
        "shaman.exposed": ("Les cristaux sont brisés : le Chaman est vulnérable !", "The crystals are shattered: the Shaman is vulnerable!"),
        "shaman.balcony": ("Le Chaman saute sur sa corniche de glace et fait pleuvoir des pics : détruisez l'Effigie de "
                           "glace !", "The Shaman leaps onto his ice ledge and rains spikes: destroy the Ice Effigy!"),
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


def java_layout(c):
    J = fc
    cx, cz = CAMP
    rows = sorted({y for _, y, _ in c.ice_wall}, reverse=True)
    wall_rows = "{" + ", ".join(J.jblocks([w for w in c.ice_wall if w[1] == y]) for y in rows) + "}"
    sx, sz = SOURCE_C
    sy = SOURCE_AT[1]
    vx, vz = VILLAGE_C
    vy = EFFIGY_AT[1]
    pack_centers = J.jpoints([center for center, _ in c.packs])
    pack_spawns = "{" + ", ".join(J.jpoints([at for _, at in spawns]) for _, spawns in c.packs) + "}"
    pack_roles = "{" + ", ".join("{" + ", ".join(f'"{role}"' for role, _ in spawns) + "}" for _, spawns in c.packs) + "}"
    plateau = ss.PLATEAU_CHECKPOINT
    return f"""package dev.nakasar.hytale.fractals.snowblind;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions de la Tempête de neige, écrites par tools/generate_snowblind.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SnowblindLayout {{

    public static final double[] SPAWN = {J.jpoint(SPAWN)};
    /** Le bol du grand feu, au pied de la colline. */
    public static final Box CAMP = {J.jbox(cx - CAMP_RADIUS, cx + CAMP_RADIUS, -1, 14, cz - CAMP_RADIUS, cz + CAMP_RADIUS)};
    public static final int[] BONFIRE = {J.jblock(BONFIRE_AT)};
    public static final double BONFIRE_HEAT = {BONFIRE_HEAT};
    /** Tas de fagots sous les sapins de la lisière. */
    public static final int[][] CAMP_PILES = {J.jblocks([c.at(x, z) for x, z in FIREWOOD_SPOTS])};
    /** Lisière d'où sortent les élémentaires de glace, et les vagues de loups et de Svanir. */
    public static final double[][] ELEMENTAL_SPAWNS = {J.jpoints([c.at(x, z) for x, z in ELEMENTAL_SPAWNS])};
    public static final double[][] WAVE_SPAWNS = {J.jpoints([c.at(x, z) for x, z in WAVE_SPAWNS])};
    /** Mur de glace du col, rangée par rangée, du haut vers le bas (il fond dans cet ordre). */
    public static final int[][][] ICE_WALL = {wall_rows};
    public static final double[] WALL_CHECKPOINT = {J.jpoint(ss.WALL_CHECKPOINT)};

    /** Le camp Svanir et la Source élémentaire. */
    public static final Box SOURCE_ARENA = {J.jbox(sx - SOURCE_RADIUS, sx + SOURCE_RADIUS, sy - 1, sy + 14, sz - SOURCE_RADIUS, sz + SOURCE_RADIUS)};
    public static final double[] SOURCE = {J.jpoint(SOURCE_AT)};
    public static final int[][] BRAZIERS = {J.jblocks([c.at(x, z) for x, z in BRAZIERS])};
    public static final double BRAZIER_HEAT = {BRAZIER_HEAT};
    public static final int[][] HUT_PILES = {J.jblocks([c.at(x, z) for x, z in c.huts])};
    public static final int[] TORCH_RACK = {J.jblock(TORCH_RACK_AT)};
    public static final int[][] GATE_SOURCE = {J.jblocks(c.gate_source)};
    /** Où le blizzard jette les joueurs (neige tassée de l'arène, loin des foyers). */
    public static final double[][] BLIZZARD_SPOTS = {J.jpoints(c.blizzard_spots)};

    /** La forêt : groupes de Svanir et de loups autour de leurs feux (toujours allumés), éveillés à l'approche. */
    public static final double[] FOREST_CHECKPOINT = {J.jpoint(ss.FOREST_CHECKPOINT)};
    public static final double[] PLATEAU_CHECKPOINT = {J.jpoint(plateau)};
    public static final double PACK_TRIGGER = {PACK_TRIGGER};
    public static final double[][] PACK_CENTERS = {pack_centers};
    public static final double[][][] PACK_SPAWNS = {pack_spawns};
    public static final String[][] PACK_ROLES = {pack_roles};
    public static final int[][] FOREST_FIRES = {J.jblocks(c.forest_fires)};
    public static final double FOREST_FIRE_HEAT = {FOREST_FIRE_HEAT};

    /** La grotte de glace du Chaman légendaire. */
    public static final Box VILLAGE = {J.jbox(vx - VILLAGE_RADIUS, vx + VILLAGE_RADIUS, vy - 1, vy + 24, vz - VILLAGE_RADIUS, vz + VILLAGE_RADIUS)};
    public static final double[] VILLAGE_CENTER = {J.jpoint((vx, vy, vz))};
    public static final double VILLAGE_RADIUS = {VILLAGE_RADIUS};
    public static final int[][] VILLAGE_FIRES = {J.jblocks([c.at(x, z) for x, z in VILLAGE_FIRES])};
    public static final int[][] GATE_VILLAGE = {J.jblocks(c.gate_village)};
    public static final double[] VILLAGE_CHECKPOINT = {J.jpoint(ss.VILLAGE_CHECKPOINT)};
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

    course = build_course()
    p = course.p
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Toujours la nuit (Kevin, 25 octobre 2026) : ciel bleu nuit, brume bleutée, clair de lune froid.
    counts = fc.write_instance(INSTANCE, "Tempête de neige", PREFAB_DIR, sections, SPAWN, "#7a9a8a",
                               WEATHER, fc.weather("#060c1c", "#1a2a46", "#1e2c44", (14, 150), 0.5, "#5a72a8",
                                                   sun="#c8d8ff"), "00:30")
    # Blizzard de la Source (tous les foyers éteints) : brume blanche à quelques blocs, posé par le Java.
    fc.write_json(fc.SERVER / "Weathers" / f"{BLIZZARD_WEATHER}.json",
                  fc.weather("#7a8aa0", "#b8c4d4", "#c4d0de", (1, 9), 0.97, "#8a9ac0", sun="#c8d8ff"))
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(course), encoding="utf-8")
    print(f"Tempête de neige : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules")
    if preview:
        fc.top_view(p, preview / "tempete_dessus.png", color_of)


if __name__ == "__main__":
    main()
