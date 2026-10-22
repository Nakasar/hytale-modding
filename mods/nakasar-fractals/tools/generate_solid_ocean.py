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
JADE_LANDING = "Nakasar_Fractal_Jade_Landing"
CRYSTAL = "Nakasar_Fractal_Reflecting_Crystal"
MAW = "Nakasar_Fractal_Jade_Maw"
TENTACLE = "Nakasar_Fractal_Jade_Tentacle"
COLOSSUS = "Nakasar_Fractal_Jade_Colossus"
IRUKANDJI = "Nakasar_Fractal_Irukandji"
FOE_ROLES = [MAW, TENTACLE, COLOSSUS, IRUKANDJI]
BEAM_CAUSE = "Nakasar_Fractal_Jade_Beam"

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
AR_RADIUS = 18
MAW_BACK = 7                            # l'Abîme flotte au nord de l'arène, hors de portée de mêlée
TENTACLE_ANGLES = [235, 305, 200, 340, 160, 20]   # deux premiers : phase 1 (au nord, sous l'Abîme)
TENTACLE_RADIUS = 11
COLOSSUS_ANGLES = [150, 30, 270, 90]
COLOSSUS_RADIUS = 8
ARENA_IRUKANDJI = [120, 60, 200, 340]


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
    # Fragments de jade : dessus sûr, dessous en cône de jade et d'argile marine.
    for k, (x, z, r, stand) in enumerate(PATH):
        fc.disc(p, x, z, r, stand, JADE_LANDING, UNDER, 3 + r * 2)
        for dx, dz in ((r - 1, 0), (-r + 1, 1), (0, -r + 1)):
            if r >= 3 and (k + dx) % 2 == 0:
                p.set(x + dx, stand, z + dz, pick(DECO, x + dx, stand, z + dz))
    # Arène de l'Abîme : grand fragment, bordure de cristaux, coin sûr à l'entrée (sud-ouest).
    ax, az = AR_CENTER
    fc.disc(p, ax, az, AR_RADIUS, AR_STAND, JADE_LANDING, UNDER, 12)
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
    dress(p)
    return p


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
    tops = fn.rim(arena, 3, 8, seed=53, block=lambda x, z: z > az + 8)
    fn.natural_ground(p, tops, THEME, seed=53, trees=0.04, spacing=6, bushes=0.08, density=0.25, flowers=0.2)


# --- objets, blocs, effets, particules ------------------------------------------------------------------

def crystal_parts():
    jade, light = (90, 220, 170), (220, 255, 240)
    return [("Core", (0, 6, 0), (5, 12, 5), 45, fm.crystal(jade, light), "fullbright"),
            ("Shard_A", (3, 3, 1), (3, 6, 3), 20, fm.crystal(jade, light), "fullbright"),
            ("Shard_B", (-3, 2, -1), (3, 5, 3), -30, fm.crystal(jade, light), "fullbright")]


def crystal_item():
    root = "Root_Nakasar_Fractal_Throw_Reflecting_Crystal"
    return fc.held_item(LANG, CRYSTAL, "Reflecting_Crystal", crystal_parts(), 61, (0, 6, 0), 14.0, quality="Epic", stack=1,
                        extra={"Interactions": {"Secondary": root}, "Categories": ["Items.Misc"]})


def throw_interaction():
    return {"$Comment": "Cristal réfléchissant : clic droit, le lancer sur l'Abîme de Jade (48 blocs, cône de 35°). "
                        "Chargé par le rayon, il lui retire 5 % de sa vie ; sinon il revient (Java, solidocean.JadeMaw).",
            "Type": "Nakasar_Fractal_ThrowItem", "Item": CRYSTAL, "Roles": MAW, "Range": 48, "Cone": 35,
            "Particle": "Nakasar_Fractal_Crystal_Trail", "Action": "Crystal",
            "NoTargetMessage": f"{LANG}.crystal.noTarget"}


def blocks():
    return [(JADE_LANDING, "Jade_Landing", (70, 168, 130), (180, 255, 214), "cracks", None, None, True, 255, None)]


def beam_cause():
    return fc.cause("Rayon de l'Abîme de Jade : mortel sans cristal (Java). L'armure ne le réduit pas.", "#7dffb0")


def effects():
    return {
        "Nakasar_Fractal_Crystal_Charged": fc.effect(
            LANG, "Nakasar_Fractal_Crystal_Charged", "Cristal chargé par le rayon de l'Abîme : le prochain cristal lancé "
            "le blesse (Java, solidocean.JadeMaw). Perdu quand l'Abîme choisit sa prochaine cible.", "Crystal_Charged", 30,
            ApplicationEffects={"EntityTopTint": "#8affc8"}),
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
    m[TENTACLE] = fc.character_model("Jade_Tentacle", tentacle_parts(), 72, "Tentacule de l'Abîme de Jade : colonne de jade "
                                     "segmentée, immobile, balaie autour de lui.", 2.4, (0.6, 2.9), scale=1.4)
    m[COLOSSUS] = {"$Comment": "Colosse de jade (phase 2) : le golem de cristal vanilla, plus grand.",
                   "Parent": "Golem_Crystal_Thunder", "MinScale": 1.25, "MaxScale": 1.25,
                   "Light": {"Color": "#6f9", "Radius": 3}}
    m[IRUKANDJI] = {"$Comment": "Irukandji (provisoire) : l'esprit de givre vanilla, en attendant une méduse vérifiée dans "
                                "Assets.zip.", "Parent": "Spirit_Frost", "MinScale": 0.9, "MaxScale": 0.9,
                    "Light": {"Color": "#7ff", "Radius": 2}}
    return m


# --- attaques et rôles ------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
GOLEM_ANIMS = "Golem_Crystal_Thunder_Default"


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Tentacle_Sweep"] = {
        "$Comment": "Tentacule : balayage annoncé, cône de 160° et 7 blocs (1,4 s), 22 dégâts et forte projection "
                    "(renversement de GW2).",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.4, Angle=160, Radius=7, Damage=22, Knockback=10, KnockUp=4,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Tentacle_Emerge",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.4, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Tentacle_Slam"] = {
        "$Comment": "Tentacule : s'abat devant lui, ligne de 8 × 2 blocs (1,2 s), 28 dégâts et étourdissement 1,5 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Line", 1.2, Length=8, Width=2, Damage=28, EffectId="Hazard_Electric_Stun",
                                                     EffectDuration=1.5, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.2, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Colossus_Slam"] = {
        "$Comment": "Colosse de jade : frappe le sol, cercle rouge de 5,5 blocs (1,5 s), 26 dégâts, projection et "
                    "étourdissement 1,5 s (renversement de GW2).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Radius=5.5, Damage=26, Knockback=7, KnockUp=4,
                                                     EffectId="Hazard_Electric_Stun", EffectDuration=1.5, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.5, "SFX_Spear_Throw_Charge", GOLEM_ANIMS, "GroundSlam")]}
    out["Nakasar_Fractal_Colossus_Strike"] = {
        "$Comment": "Colosse de jade au contact : coup de cristal (16 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de cristal.", GOLEM_ANIMS, "GroundSlam", 0.6, 16, end=3.4)]}
    out["Nakasar_Fractal_Irukandji_Sting"] = {
        "$Comment": "Irukandji au contact : piqûre (8 dégâts et poison 3 s).",
        "Type": "Serial", "Interactions": [fr.swing("Piqûre.", None, None, 0.3, 8, end=2.2, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing", extra=[fr.effect_on_target("Poison_T1", 3)])]}
    out["Nakasar_Fractal_Irukandji_Shock"] = {
        "$Comment": "Irukandji : décharge autour de lui, cercle rouge de 3 blocs (1,2 s), 14 dégâts.",
        "Type": "Serial", "Interactions": [T("Circle", 1.2, Radius=3, Damage=14, PlayersOnly=True,
                                             ImpactParticle="Nakasar_Fractal_Colossus_Reflect"),
                                           fc.windup(1.2, "SFX_Spirit_Root_Alerted")]}
    return out


MELEE = ["Tentacle_Sweep", "Tentacle_Slam", "Colossus_Slam", "Colossus_Strike", "Irukandji_Sting", "Irukandji_Shock"]
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
        "l'Abîme (Java).", TENTACLE, n(TENTACLE), 260,
        [fr.timed_attack("Sweep", R("Tentacle_Sweep"), rng=7, los=True, comment="Balayage annoncé."),
         fr.timed_attack("Slam", R("Tentacle_Slam"), rng=8, los=True, comment="Coup abattu annoncé.")],
        fr.walk(0.1, jump=0), GENERATOR, sight=12, leash=40, home=False,
        timers=[fr.timer("Sweep", (1, 3), (5, 7)), fr.timer("Slam", (3, 5), (6, 8))], KnockbackScale=0.0,
        DeathAnimationTime=1.0)
    out[TENTACLE] = tentacle
    out[COLOSSUS] = fr.role(
        COLOSSUS, "Colosse de jade (phase 2) : renvoie les projectiles tant qu'il n'est pas étourdi (Java), frappe le sol "
        "(cercle annoncé, renverse) ; il lâche des cristaux réfléchissants.", COLOSSUS, n(COLOSSUS), 700,
        [fr.timed_attack("Slam", R("Colossus_Slam"), rng=5, los=True, comment="Frappe au sol annoncée."),
         fr.melee(R("Colossus_Strike"), 3.4, (1.0, 1.4)), fr.chase(40, stop=2.6)],
        fr.walk(3.0), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Slam", (3, 5), (8, 10))], KnockbackScale=0.1, DeathAnimationTime=1.5)
    out[IRUKANDJI] = fr.role(
        IRUKANDJI, "Irukandji : flotte au-dessus des fragments de jade, pique et décharge autour de lui.", IRUKANDJI,
        n(IRUKANDJI), 60,
        [fr.timed_attack("Shock", R("Irukandji_Shock"), rng=3, los=True, comment="Décharge annoncée."),
         fr.melee(R("Irukandji_Sting"), 2.4, (0.8, 1.2)), fr.chase(24, speed=1.0, stop=1.4, pathfinder=False)],
        fc.fly(4.5, 1, 4), GENERATOR, sight=12, leash=24, home=True,
        timers=[fr.timer("Shock", (2, 4), (6, 9))], KnockbackScale=0.8, DeathAnimationTime=0.8)
    return out


# --- langue -----------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(CRYSTAL, "Cristal réfléchissant", "Le tenir en main absorbe le rayon de l'Abîme de Jade et vous charge ; "
           "clic droit en visant l'Abîme : le lancer. Tenu en main, il empêche d'attaquer.", "Reflecting crystal",
           "Holding it absorbs the Jade Maw's beam and charges you; right-click while aiming at the Maw: throw it. Held "
           "in hand, it keeps you from attacking.")
    t.item(JADE_LANDING, "Fragment de jade", "Une chute ramène au dernier fragment où l'on s'est tenu.", "Jade fragment",
           "A fall brings you back to the last fragment you stood on.")
    for role, f, e in ((MAW, "L'Abîme de Jade", "The Jade Maw"), (TENTACLE, "Tentacule de l'Abîme", "Jade Maw tentacle"),
                       (COLOSSUS, "Colosse de jade", "Jade colossus"), (IRUKANDJI, "Irukandji", "Irukandji")):
        t.npc(role, f, e)
    t.put("effects.Nakasar_Fractal_Crystal_Charged", "Cristal chargé", "Charged crystal")
    msgs = {
        "intro": ("Dessa : « Étrange. Les relevés disent que c'était de l'eau. Bonne nouvelle, la fractale semble "
                  "stable. » Traversez les fragments de jade : une chute ramène au fragment d'avant.",
                  "Dessa: \"How bizarre. The readings state that this was water once. Good news, this fractal appears "
                  "stable.\" Cross the jade fragments: a fall brings you back to the previous one."),
        "landing.back": ("Rattrapé au-dessus de l'océan figé : retour au dernier fragment.",
                         "Caught above the solid ocean: back to the last fragment."),
        "arena": ("Dessa : « Je retire ce que j'ai dit. Instabilité ! Juste devant vous ! » L'Abîme de Jade est "
                  "invulnérable : abattez ses deux tentacules.",
                  "Dessa: \"I retract my statement. Unstable event! Right in front of you!\" The Jade Maw is invulnerable: "
                  "slay its two tentacles."),
        "checkpoint": ("Point de retour déplacé.", "Respawn point moved."),
        "agony": ("L'Abîme vous écrase de son agonie !", "The Maw crushes you with agony!"),
        "phase.colossi": ("Des colosses de jade surgissent : abattez-les ({count}) et ramassez leurs cristaux. Tenez un "
                          "cristal quand le crâne rouge vous vise !",
                          "Jade colossi emerge: slay them ({count}) and pick up their crystals. Hold a crystal when the "
                          "red skull targets you!"),
        "phase.final": ("Les colosses sont tombés : l'Abîme rappelle ses tentacules, qui lâchent désormais les cristaux.",
                        "The colossi have fallen: the Maw calls back its tentacles, which now drop the crystals."),
        "skull": ("Le crâne rouge vous vise : tenez un cristal, ou écartez-vous quand il disparaît !",
                  "The red skull targets you: hold a crystal, or step aside when it vanishes!"),
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
        "reflect": ("Le colosse renvoie les projectiles : étourdissez-le ou frappez-le au contact.",
                    "The colossus reflects projectiles: stun it or strike it in melee."),
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
    bigs = [p for p in PATH[1:] if p[2] >= 4]
    path_iru = J.jpoints([(x + dx, stand + 2, z) for x, z, _, stand in bigs for dx in (-1, 1)])
    def ring(radius, angles, up=0):
        return J.jpoints([(x, AR_STAND + up, z) for x, z in (ring_point(AR_CENTER, radius, a) for a in angles)])

    arena_iru = ring(AR_RADIUS - 4, ARENA_IRUKANDJI, 2)
    tentacles = ring(TENTACLE_RADIUS, TENTACLE_ANGLES)
    colossi = ring(COLOSSUS_RADIUS, COLOSSUS_ANGLES)
    zx0, zx1, zy0, zy1, zz0, zz1 = jump_zone()
    entry = (LAST[0], LAST[3], LAST[1])
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
    /** Points des tentacules : les deux premiers sont ceux de la phase 1. */
    public static final double[][] TENTACLES = {tentacles};
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
    if name == JADE_LANDING:
        return (90, 220, 160)
    if name.startswith("Rock_Crystal") or name.startswith("Plant_Coral"):
        return (120, 240, 200)
    if name.startswith("Soil_Clay"):
        return (60, 110, 120)
    return (90, 120, 110)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, tex, base, accent, glyph, light, use, solid, alpha, opacity in blocks():
        fc.write_block(LANG, name, tex, base, accent, glyph, light, use, solid, alpha, opacity)
    fc.write_json(fc.OBJECTS / f"{CRYSTAL}.json", crystal_item())
    fc.write_json(INTERACTIONS / "Nakasar_Fractal_Throw_Reflecting_Crystal.json", throw_interaction())
    fc.write_json(fc.ROOTS / "Root_Nakasar_Fractal_Throw_Reflecting_Crystal.json",
                  {"Interactions": ["Nakasar_Fractal_Throw_Reflecting_Crystal"], "RequireNewClick": True})
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    fc.status_icon(fc.COMMON / fc.STATUS_ICONS / "Crystal_Charged.png", (120, 255, 180), "stone")
    fc.write_json(fc.SERVER / f"Entity/Damage/{BEAM_CAUSE}.json", beam_cause())
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
    counts = fc.write_instance(INSTANCE, "Océan solide", PREFAB_DIR, sections, SPAWN, "#70b8a8",
                                WEATHER, fc.weather("#2a7ad0", "#a8e8e0", "#a0d8d0", (50, 380), 0.2, "#fff8e8"), "12:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Océan solide : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(PATH)} fragments, arène en "
          f"{AR_CENTER} (debout à {AR_STAND}), Abîme en {MAW_AT}")
    if preview:
        fc.top_view(p, preview / "ocean_solide_dessus.png", color_of)


if __name__ == "__main__":
    main()
