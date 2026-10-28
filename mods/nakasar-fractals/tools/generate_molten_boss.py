#!/usr/bin/env python3
"""Génère le Boss en fusion (Molten Boss), fractale de la saison 1 de GW2 (docs/fractales/gdd.md), d'après le guide
Hardstuck (hardstuck.gg/gw2/guides/fractal-maps/molten-boss) et la carte que Kevin a envoyée (28 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_molten_boss.py [--preview DOSSIER]

L'Alliance en fusion (Légion de la Flamme et Draguerres) forge ses armes dans une caverne sous un volcan. Avec Braham et
Rox, dans l'ordre :

1. le surplomb du départ, la rampe, la cour et l'atelier : quatre meutes ; on peut courir jusqu'à la quatrième (un
   résonateur draguerre rend invulnérable le chaman de la flamme d'élite) ; la meute 4 vaincue, le pont du canal de
   lave se pose ;
2. la fonderie : l'Effigie en fusion (championne), protégée par son Protecteur, lui-même protégé par un second
   résonateur ; elle prend des avantages (Puissance) et lance des ondes de choc qui repoussent (on les saute) ;
3. la cour des wagonnets et la passerelle des cuves : les groupes 5 à 8 ; puis la salle des chaudières (point de
   retour) et le pont vers la plate-forme du creuset ;
4. le Berserker en fusion (se téléporte, enchaînement qui finit en onde de choc frontale, ondes blanches au sol à
   sauter, ondes bleues en l'air sous lesquelles rester au sol) et la Tempête de feu en fusion (vole autour de la
   plate-forme, flammes qui restent au sol). Quand l'un perd 25 %, l'autre enrage. Le premier tombé, l'autre rejoint son
   corps et se renforce : le Berserker fait aussi pleuvoir des débris, la Tempête lève un vent qui jette du bord. Une
   défaite dans cette seconde phase y fait revenir, pas au début du combat.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_MoltenBoss`, effets, particules,
modèles (parents vanilla), rôles, le temps (ciel de fournaise), la langue `nakasar_fractals_molten_boss.lang` et
`moltenboss/MoltenBossLayout.java`. Repère : y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
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
import molten_boss_scenery as sc

LANG = "nakasar_fractals_molten_boss"
GENERATOR = "generate_molten_boss.py"
INSTANCE = "Nakasar_Fractal_MoltenBoss"
WEATHER = "Nakasar_Fractal_Weather_MoltenBoss"
PREFAB_DIR = "MoltenBoss"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/moltenboss/MoltenBossLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/MoltenBoss"
CAUSE = "Nakasar_Fractal_Molten"

# --- rôles ---------------------------------------------------------------------------------------------------------
BRAHAM = "Nakasar_Fractal_Braham"
ROX = "Nakasar_Fractal_Rox"
MINER = "Nakasar_Fractal_Molten_Dredge_Miner"
SONIC = "Nakasar_Fractal_Molten_Dredge_Sonic"
WARRIOR = "Nakasar_Fractal_Molten_Legion_Warrior"
LEGION_SHAMAN = "Nakasar_Fractal_Molten_Legion_Shaman"
RESONATOR = "Nakasar_Fractal_Dredge_Resonator"
ELITE_SHAMAN = "Nakasar_Fractal_Elite_Flame_Shaman"
PROTECTOR = "Nakasar_Fractal_Molten_Protector"
EFFIGY = "Nakasar_Fractal_Molten_Effigy"
BERSERKER = "Nakasar_Fractal_Molten_Berserker"
FIRESTORM = "Nakasar_Fractal_Molten_Firestorm"
BERSERKER_2 = "Nakasar_Fractal_Molten_Berserker_Empowered"
FIRESTORM_2 = "Nakasar_Fractal_Molten_Firestorm_Empowered"
FOE_ROLES = [MINER, SONIC, WARRIOR, LEGION_SHAMAN, RESONATOR, ELITE_SHAMAN, PROTECTOR, EFFIGY, BERSERKER, FIRESTORM,
             BERSERKER_2, FIRESTORM_2]

# Vie (Kevin : des boss de fractale bien plus courts qu'au début ; la vie suit ensuite le groupe et le niveau).
HP = {MINER: 240, SONIC: 200, WARRIOR: 300, LEGION_SHAMAN: 220, RESONATOR: 300, ELITE_SHAMAN: 700, PROTECTOR: 600,
      EFFIGY: 2500, BERSERKER: 1600, FIRESTORM: 1400, BERSERKER_2: 1600, FIRESTORM_2: 1600}

# Meutes : (centre, [(rôle, dx, dz)]). Les quatre premières dans l'atelier ; puis les groupes 5 à 8 (cour des wagonnets,
# trois cuves). La quatrième garde le résonateur et le chaman d'élite (sc.RESONATOR_1, sc.SHAMAN_AT, posés à part).
PACKS = [
    (sc.PACK_CENTERS[0], [(MINER, -2, 0), (MINER, 2, 1), (SONIC, 0, -3)]),
    (sc.PACK_CENTERS[1], [(WARRIOR, -2, 0), (MINER, 2, -1), (LEGION_SHAMAN, 0, 3)]),
    (sc.PACK_CENTERS[2], [(WARRIOR, -3, 0), (SONIC, 2, 2), (MINER, 1, -3), (LEGION_SHAMAN, -1, 4)]),
    (sc.PACK_CENTERS[3], [(WARRIOR, 3, 2), (SONIC, -3, 3)]),
    (sc.GROUP_CENTERS[0], [(WARRIOR, -2, 0), (MINER, 2, 1), (LEGION_SHAMAN, 0, -3)]),
    (sc.GROUP_CENTERS[1], [(MINER, -2, 1), (SONIC, 2, -1)]),
    (sc.GROUP_CENTERS[2], [(WARRIOR, -2, 0), (LEGION_SHAMAN, 2, 2)]),
    (sc.GROUP_CENTERS[3], [(WARRIOR, -2, -1), (WARRIOR, 2, 1), (SONIC, 0, 3)]),
]
# Renforts de l'Effigie : deux par point (sc.EFFIGY_ADDS).
EFFIGY_ADD_ROLES = [WARRIOR, MINER, SONIC, LEGION_SHAMAN, MINER, WARRIOR]

# --- mécaniques (Java) --------------------------------------------------------------------------------------------
SHOCK_SPEED = 8.0            # ondes de choc : vitesse de l'anneau (blocs/s)
SHOCK_BAND = 0.75            # demi-épaisseur de l'anneau
AIR_RING_HEIGHT = 1.6        # onde bleue : hauteur de l'anneau au-dessus du sol (on la prend en sautant)
SHOCK_REACH_EFFIGY = sc.EFFIGY_R + 4      # l'onde de l'Effigie court jusqu'au-delà du bord de la fonderie
SHOCK_REACH_DUO = 2 * sc.ARENA_R + 4      # celle du Berserker traverse toute la plate-forme, d'un bord à l'autre
RING_SCALE = 0.68            # anneau d'onde de choc : échelle de particule par bloc de rayon (generate_warnings.SCALE)
RING_BASE = 6.25             # taille de la particule à l'échelle 1 (generate_warnings.BASE)
FIRE_POOL_R = 3.0            # flammes de la Tempête : rayon de la zone (rouge à l'annonce, flammes ensuite)
FIRE_POOL_SECONDS = 8.0
DEBRIS_R = 2.5               # débris du Berserker renforcé
WIND_BAND = 6.0              # vent de la Tempête renforcée : couronne du bord de la plate-forme
WIND_SEGMENTS = 24           # la couronne est dessinée en 24 bandes rouges (Telegraphs.Strip)
WIND_LENGTH = round(2 * math.pi * sc.ARENA_R / WIND_SEGMENTS + 0.05, 1)
FIRESTORM_ORBIT = 17.0       # rayon du vol de la Tempête autour du centre
FIRESTORM_HOVER = 1.5        # hauteur de vol (on l'atteint encore au contact)


# --- effets ---------------------------------------------------------------------------------------------------------

def effects():
    L = LANG
    out = {}
    out["Nakasar_Fractal_Molten_Burning"] = fc.effect(
        L, "Nakasar_Fractal_Molten_Burning", "Brûlure de la fonderie : la vie s'en va (Java, moltenboss).",
        "Molten_Burning", 4.0, debuff=True, ApplicationEffects={"EntityBottomTint": "#ff5a10"})
    out["Nakasar_Fractal_Molten_Enraged"] = fc.effect(
        L, "Nakasar_Fractal_Molten_Enraged", "Enragé : l'autre boss a perdu un quart de sa vie ; ses attaques "
        "reviennent plus vite (Java, moltenboss.MoltenDuo).", "Molten_Enraged", 12.0,
        ApplicationEffects={"EntityTopTint": "#ff2000"})
    out["Nakasar_Fractal_Molten_Shielded"] = fc.effect(
        L, "Nakasar_Fractal_Molten_Shielded", "Protégé : un allié le rend invulnérable tant qu'il vit (Java, "
        "moltenboss.Packs, moltenboss.Effigy).", "Molten_Shielded", 1.5,
        ApplicationEffects={"EntityTopTint": "#ffd060"})
    return out


def status_icons():
    icons = fc.COMMON / fc.STATUS_ICONS
    for name, color, glyph in (("Molten_Burning", (255, 100, 30), "flame"), ("Molten_Enraged", (230, 40, 20), "flame"),
                               ("Molten_Shielded", (255, 200, 90), "stone")):
        fc.status_icon(icons / f"{name}.png", color, glyph)


def molten_cause():
    return fc.cause("Lave, flammes et ondes de choc de la fonderie en fusion : une part des PV max, l'armure ne la "
                    "réduit pas.", "#ff8030")


# --- particules -----------------------------------------------------------------------------------------------------

S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Molten_Ring_Ground": ("Onde de choc au sol (à sauter) : un point de l'anneau blanc (le Java en pose "
                                           "tout autour).",
                                           [("Dust", S("#ffffff", "#c8b8a0", 6, (0.6, 1.6), (50, 90), 0.2, 0.6,
                                                       life=(0.4, 0.7), size=(0.35, 0.6), blend="BlendLinear"), 0.0),
                                            ("Ember", S("#fff0a0", "#ff5010", 4, (0.8, 2.0), (60, 90), 0.2, 0.4,
                                                        life=(0.3, 0.6), size=(0.15, 0.3)), 0.1)]),
    "Nakasar_Fractal_Molten_Ring_Air": ("Onde de choc en l'air (rester au sol) : un point de l'anneau bleu, à hauteur de "
                                        "saut.",
                                        [("Spark", S("#e0f0ff", "#3070ff", 6, (0.1, 0.4), (-20, 20), 0.2, 0.3,
                                                     life=(0.4, 0.7), size=(0.35, 0.55)), 0.0)]),
    "Nakasar_Fractal_Molten_Windup_Ground": ("Le Berserker prépare une onde au sol : poussière blanche à ses pieds.",
                                             [("Dust", S("#ffffff", "#b0a090", 30, (0.5, 2.0), (0, 40), 1.5, 0.4,
                                                         life=(0.5, 0.9), size=(0.2, 0.4), blend="BlendLinear"), 0.1)]),
    "Nakasar_Fractal_Molten_Windup_Air": ("Le Berserker prépare une onde en l'air : éclairs bleus autour de ses épaules.",
                                          [("Spark", S("#ffffff", "#2060ff", 30, (0.5, 2.0), (-30, 60), 1.5, 1.0,
                                                       life=(0.4, 0.7), size=(0.15, 0.3)), 2.0)]),
    "Nakasar_Fractal_Molten_Fire_Pool": ("Flammes de la Tempête au sol (le Java les repose toutes les demi-secondes, "
                                         "échelle = rayon : les flammes couvrent exactement la zone qui brûle).",
                                         [("Flame", S("#fff0a0", "#ff3a00", 26, (0.6, 1.6), (70, 90), 1.0, 0.1,
                                                      life=(0.5, 0.8), size=(0.08, 0.16)), 0.0)]),
    "Nakasar_Fractal_Molten_Impact": ("Coup qui tombe dans un cercle (boule de feu, bond, pluie de flammes) : gerbe de "
                                      "flammes dans un rayon d'un bloc à l'échelle 1 ; posée à l'échelle du rayon de la "
                                      "zone (ImpactParticleScale), elle ne déborde jamais du cercle rouge.",
                                      [("Flame", S("#fff0a0", "#ff3a00", 36, (0.3, 1.0), (75, 90), 0.85, 0.3,
                                                   life=(0.4, 0.6), size=(0.08, 0.16)), 0.0),
                                       ("Ember", S("#fff4c0", "#ff5010", 16, (2.0, 4.0), (82, 90), 0.5, 0.2,
                                                   life=(0.3, 0.6), size=(0.04, 0.08)), 0.1)]),
    "Nakasar_Fractal_Molten_Fire_Bolt": ("Trait de feu de la Tempête qui tombe : boule de flammes.",
                                         [("Fire", S("#fff0a0", "#ff5010", 24, (0.5, 2.0), (80, 90), 0.7, 0.6,
                                                     life=(0.3, 0.6), size=(0.15, 0.3)), 0.0)]),
    "Nakasar_Fractal_Molten_Link": ("Lien du résonateur ou du Protecteur : un point du rayon doré (le Java en pose le "
                                    "long).",
                                    [("Beam", S("#fff4c0", "#ff9020", 3, (0.0, 0.2), (-90, 90), 0.1, 0.1,
                                                life=(0.3, 0.5), size=(0.25, 0.35)), 0.0)]),
    "Nakasar_Fractal_Molten_Debris": ("Débris qui tombent sur la plate-forme : éclats de roche et de braises.",
                                      [("Rock", S("#c0b0a0", "#503020", 40, (2.0, 3.5), (80, 90), 0.4, 0.6,
                                                  life=(0.6, 1.0), size=(0.1, 0.2), blend="BlendLinear"), 0.3),
                                       ("Ember", S("#fff0a0", "#ff4010", 20, (2.0, 3.5), (80, 90), 0.6, 0.4,
                                                   life=(0.4, 0.7), size=(0.05, 0.1)), 0.3)]),
    "Nakasar_Fractal_Molten_Wind": ("Vent de la Tempête : volutes de cendre qui filent vers le vide.",
                                    [("Ash", S("#e8e0d8", "#806858", 12, (5.0, 9.0), (-5, 15), 1.5, 1.6,
                                               life=(0.6, 1.0), size=(0.15, 0.3), blend="BlendLinear"), 0.4)]),
    "Nakasar_Fractal_Molten_Upgrade": ("Le survivant absorbe la flamme de l'autre : colonne de feu.",
                                       [("Pillar", S("#fff4c0", "#ff3000", 80, (3.0, 8.0), (70, 90), 1.5, 0.5,
                                                     life=(0.6, 1.2), size=(0.3, 0.6)), 0.0)]),
    "Nakasar_Fractal_Molten_Teleport": ("Le Berserker se téléporte : gerbe de braises.",
                                        [("Burst", S("#fff0a0", "#ff4010", 40, (2.0, 6.0), (-10, 90), 1.0, 1.4,
                                                     life=(0.4, 0.7), size=(0.15, 0.3)), 0.4)]),
}


def shock_rings():
    """Anneaux d'onde de choc (retour de Kevin, 28 octobre 2026 : « elle doit être visible, comme le Gobliterator des
    Deepworks ») : un seul anneau à plat (contour Warning_Circle_Base des annonces Deepworks), lumineux, qui grandit du
    centre jusqu'à la portée de l'onde en `portée / SHOCK_SPEED` s. Posé à l'échelle RING_SCALE * portée, il est à chaque
    instant au rayon de l'anneau qui frappe (Java, moltenboss.Shockwaves). Un système par (sorte, portée)."""
    out = {}
    flat = {"X": {"Min": 90, "Max": 90}}
    size = {"X": {"Min": RING_BASE, "Max": RING_BASE}}
    for kind, edge, glow in (("Ground", "#fff4d0", "#ff7020"), ("Air", "#e8f4ff", "#3070ff")):
        for reach in (SHOCK_REACH_EFFIGY, SHOCK_REACH_DUO):
            life = round(reach / SHOCK_SPEED, 3)
            name = f"Nakasar_Fractal_Molten_Shock_{kind}_{round(reach)}"
            frames = {"0": {"Opacity": 1, "Color": edge, "Scale": {"X": {"Min": 0.02, "Max": 0.02}}},
                      "70": {"Opacity": 1, "Color": glow},
                      "100": {"Opacity": 0.4, "Color": glow, "Scale": {"X": {"Min": 1, "Max": 1}}}}
            spawners = []
            for suffix, texture, y in (("Ring", "Particles/Textures/Indicators/Warning_Circle_Base.png", 0.15),
                                       ("Glow", "Particles/Textures/Indicators/Warning_Circle_Base.png", 0.35)):
                doc = {
                    "RenderMode": "BlendAdd",
                    "ParticleRotationInfluence": "Velocity",
                    "ParticleLifeSpan": {"Min": life, "Max": life},
                    "ParticleRotateWithSpawner": True,
                    "TrailSpawnerPositionMultiplier": 1,
                    "TrailSpawnerRotationMultiplier": 1,
                    "Particle": {"Texture": texture, "ScaleRatioConstraint": "OneToOne", "UVOption": "None",
                                 "Animation": frames, "SoftParticles": "Disable",
                                 "InitialAnimationFrame": {"Opacity": 1, "Color": edge, "Rotation": flat,
                                                           "Scale": size}},
                    "Shape": "Sphere",
                    "TotalParticles": {"Min": 1, "Max": 1},
                    "SpawnRate": {"Min": 1, "Max": 1},
                    "LinearFiltering": True,
                    "MaxConcurrentParticles": 1,
                    "InitialVelocity": {"Speed": {"Min": 0.01, "Max": 0.01}},
                    "SpawnBurst": True,
                }
                spawners.append({"SpawnerId": f"{name}_{suffix}", "PositionOffset": {"Y": y}})
                out[f"{name}_{suffix}.particlespawner"] = doc
            out[f"{name}.particlesystem"] = {
                "$Comment": f"Onde de choc {'en l’air' if kind == 'Air' else 'au sol'} de {reach} blocs : anneau qui "
                            f"grandit en {life:g} s (Java, moltenboss.Shockwaves). Généré par tools/{GENERATOR}.",
                "Spawners": spawners, "CullDistance": 128, "IsImportant": True}
    return out


# --- modèles --------------------------------------------------------------------------------------------------------

def models():
    """Parents vanilla d'abord : trorks (la Légion de la Flamme), gobelins (les Draguerres, mineurs), golem d'acier de
    feu (l'Effigie et le Berserker), esprit de braise (le Protecteur et la Tempête de feu), gobelin gardien pour le
    gardien résonateur ; Braham et Rox en humanoïdes habillés de cosmétiques vanilla."""
    v = lambda comment, parent, scale, light=None: {k: val for k, val in (
        ("$Comment", comment), ("Parent", parent), ("MinScale", scale), ("MaxScale", scale),
        ("Light", light)) if val is not None}
    m = {
        MINER: v("Mineur draguerre : gobelin mineur vanilla.", MODEL["miner"], 1.0),
        SONIC: v("Draguerre sonique : gobelin lanceur vanilla.", MODEL["sonic"], 1.0),
        WARRIOR: v("Guerrier de la Légion de la Flamme : trork guerrier vanilla.", MODEL["warrior"], 1.0),
        LEGION_SHAMAN: v("Chaman de la Légion de la Flamme : trork chaman vanilla, lueur de feu.", MODEL["shaman"], 1.0,
                         {"Color": "#f84", "Radius": 3}),
        ELITE_SHAMAN: v("Chaman de la flamme d'élite : trork chaman vanilla (x 1,4), lueur de feu.", MODEL["shaman"],
                        1.4, {"Color": "#f62", "Radius": 5}),
        PROTECTOR: v("Protecteur en fusion : grand esprit de braise vanilla (x 1,8).", "Spirit_Ember", 1.8,
                     {"Color": "#fc6", "Radius": 5}),
        EFFIGY: v("Effigie en fusion (championne) : golem d'acier de feu vanilla (x 2,2), lueur orange.",
                  "Golem_Firesteel", 2.2, {"Color": "#f60", "Radius": 8}),
        BERSERKER: v("Berserker en fusion : golem d'acier de feu vanilla (x 1,7).", "Golem_Firesteel", 1.7,
                     {"Color": "#f84", "Radius": 6}),
        BERSERKER_2: v("Berserker en fusion renforcé : le même (x 1,9), lueur blanche.", "Golem_Firesteel", 1.9,
                       {"Color": "#ffd", "Radius": 8}),
        FIRESTORM: v("Tempête de feu en fusion : esprit de braise vanilla (x 2,6), en vol.", "Spirit_Ember", 2.6,
                     {"Color": "#f60", "Radius": 7}),
        FIRESTORM_2: v("Tempête de feu en fusion renforcée : la même (x 3), lueur blanche.", "Spirit_Ember", 3.0,
                       {"Color": "#ffd", "Radius": 9}),
    }
    m[RESONATOR] = v("Gardien résonateur draguerre (retour de Kevin, 28 octobre 2026 : un monstre protecteur, pas un "
                     "bloc) : gobelin gardien vanilla (x 1,3), lueur d'ambre du bouclier qu'il entretient.",
                     MODEL["resonator"], 1.3, {"Color": "#fb4", "Radius": 4})
    coat = [("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png",
             "Faded_Leather", "BrownDark"),
            ("Cosmetics/Shoes/HeavyBoots.blockymodel", "Cosmetics/Shoes/HeavyBoots_Textures/HeavyLeather_Black.png"),
            ("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
             "Faded_Leather", "BrownDark")]
    m[BRAHAM] = fr.humanoid("Braham Eirsson (norn, x 1,25) : manteau et bottes vanilla.", "03", "Face_Scar", coat,
                            scale=(1.25, 1.25))
    scout = [("Cosmetics/Face_Accessories/GoblinGoggles.blockymodel", "Cosmetics/Face_Accessories/GoblinGoggles.png"),
             ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
              "Faded_Leather", "BrownDark"),
             ("Cosmetics/Pants/Pants_Straight.blockymodel",
              "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png", "Faded_Leather", "BrownDark")]
    m[ROX] = fr.humanoid("Rox (charr éclaireuse, x 1,1) : lunettes et bottes vanilla.", "07", "Face_Sunken", scout,
                         scale=(1.1, 1.1))
    return m


# Modèles vanilla des ennemis (vus dans Assets.zip 0.7.2 : Server/Models).
MODEL = {
    "miner": "Goblin_Miner",
    "sonic": "Goblin_Lobber",
    "warrior": "Trork_Warrior",
    "shaman": "Trork_Shaman",
    "resonator": "Goblin_Guardian",
}


# --- attaques et rôles ----------------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
R = fc.root
BURN = "Nakasar_Fractal_Molten_Burning"
# Impact des cercles : à l'échelle du rayon, la gerbe reste dans la zone rouge (AGENTS.md). Les cônes n'ont pas d'impact
# au lanceur (une gerbe ronde y débordait du cône) : des flammes sur chaque joueur touché.
IMPACT = "Nakasar_Fractal_Molten_Impact"


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Molten_Pick"] = {
        "$Comment": "Mineur draguerre : coup de pioche (12 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de pioche.", None, None, 0.35, 12, end=2.6,
                                                    sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Molten_Sonic_Blast"] = {
        "$Comment": "Draguerre sonique : onde sonore devant lui, cône de 60° sur 6 blocs (1,4 s), 14 dégâts et recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.4, Angle=60, Radius=6, Damage=14, Knockback=6,
                                                     PlayersOnly=True, HitParticle="Nakasar_Fractal_Storm_Disperse"),
                                           fc.windup(1.4)]}
    out["Nakasar_Fractal_Molten_Legion_Strike"] = {
        "$Comment": "Guerrier de la Légion : coup d'épée brûlant (14 dégâts, Brûlure 3 s).",
        "Type": "Serial", "Interactions": [fr.swing("Coup brûlant.", None, None, 0.4, 14, end=2.8,
                                                    extra=[fr.effect_on_target(BURN, 3)])]}
    out["Nakasar_Fractal_Molten_Legion_Leap"] = {
        "$Comment": "Guerrier de la Légion : bond sur sa cible lointaine, cercle rouge de 2,5 blocs (1,4 s), 18 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.4, Anchor="Farthest", OffsetMax=12, Radius=2.5,
                                                     Damage=18, TeleportCaster=True, PlayersOnly=True,
                                                     ImpactParticle=IMPACT, ImpactParticleScale=2.5),
                                           fc.windup(1.4)]}
    out["Nakasar_Fractal_Molten_Fireball"] = {
        "$Comment": "Chaman de la Légion : boule de feu sur sa cible, cercle rouge de 2,5 blocs (1,6 s), 16 dégâts et "
                    "Brûlure 3 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Anchor="Target", Radius=2.5, Damage=16,
                                                     EffectId=BURN, EffectDuration=3, PlayersOnly=True,
                                                     ImpactParticle=IMPACT, ImpactParticleScale=2.5),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Molten_Staff"] = {
        "$Comment": "Chamans : coup de bâton (8 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bâton.", "Staff", "SwingLeft", 0.4, 8, end=2.6)]}
    out["Nakasar_Fractal_Molten_Flame_Rain"] = {
        "$Comment": "Chaman de la flamme d'élite : pluie de flammes, quatre cercles rouges de 2,5 blocs autour de lui "
                    "(1,8 s), 18 dégâts et Brûlure 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.8, Anchor="Scatter", Count=4, OffsetMin=2,
                                                     OffsetMax=9, Radius=2.5, Damage=18, EffectId=BURN,
                                                     EffectDuration=4, PlayersOnly=True,
                                                     ImpactParticle=IMPACT, ImpactParticleScale=2.5),
                                           fc.windup(1.8, "SFX_Spear_Throw_Charge", "Staff", "CastSummonCharging")]}
    out["Nakasar_Fractal_Molten_Flame_Wave"] = {
        "$Comment": "Chaman de la flamme d'élite : vague de flammes devant lui, cône de 80° sur 8 blocs (1,6 s), 20 "
                    "dégâts et Brûlure 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.6, Angle=80, Radius=8, Damage=20, EffectId=BURN,
                                                     EffectDuration=4, PlayersOnly=True, HitParticle=IMPACT),
                                           fc.windup(1.6, "SFX_Spear_Throw_Charge", "Staff", "CastSummonCharging")]}
    out["Nakasar_Fractal_Molten_Resonator_Slam"] = {
        "$Comment": "Gardien résonateur : coup de marteau (14 dégâts) qui repousse.",
        "Type": "Serial", "Interactions": [fr.swing("Coup de marteau.", None, None, 0.45, 14, end=2.8,
                                                    sound="SFX_Unarmed_Swing", knockback=6)]}
    out["Nakasar_Fractal_Molten_Protector_Touch"] = {
        "$Comment": "Protecteur en fusion : toucher brûlant (12 dégâts, Brûlure 3 s).",
        "Type": "Serial", "Interactions": [fr.swing("Toucher brûlant.", None, None, 0.4, 12, end=2.8,
                                                    sound="SFX_Unarmed_Swing", extra=[fr.effect_on_target(BURN, 3)])]}
    out["Nakasar_Fractal_Molten_Effigy_Swipes"] = {
        "$Comment": "Effigie en fusion, au contact : deux coups (20 dégâts chacun), animations du golem vanilla.",
        "Type": "Serial", "Interactions": [
            fr.swing("Coup gauche.", "Golem_Firesteel_Default", "SwingLeft", 0.5, 20, end=4.4, extend_bottom=2.0),
            fr.swing("Coup droit.", "Golem_Firesteel_Default", "SwingRight", 0.5, 20, end=4.4, direction="ToRight",
                     yaw=-50, extend_bottom=2.0)]}
    out["Nakasar_Fractal_Molten_Effigy_Breath"] = {
        "$Comment": "Effigie en fusion : souffle de flammes devant elle, cône de 70° sur 10 blocs (1,8 s), 26 dégâts et "
                    "Brûlure 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.8, Angle=70, Radius=10, Damage=26, EffectId=BURN,
                                                     EffectDuration=4, PlayersOnly=True, HitParticle=IMPACT),
                                           fc.windup(1.8, "SFX_Spear_Throw_Charge", "Golem_Firesteel_Default",
                                                     "GroundSlam")]}
    out["Nakasar_Fractal_Molten_Berserker_Chain"] = {
        "$Comment": "Berserker en fusion : enchaînement de deux coups (18 dégâts chacun) qui finit par une onde de choc "
                    "devant lui, ligne rouge de 16 x 3 blocs (1,4 s), 26 dégâts et recul.",
        "Type": "Serial", "Interactions": [
            fr.swing("Coup gauche.", "Golem_Firesteel_Default", "SwingLeft", 0.45, 18, end=4.0, extend_bottom=1.8),
            fr.swing("Coup droit.", "Golem_Firesteel_Default", "SwingRight", 0.45, 18, end=4.0, direction="ToRight",
                     yaw=-50, extend_bottom=1.8),
            CI, RF, T("Line", 1.4, Anchor="Target", Length=16, Width=3, Damage=26, Knockback=8, PlayersOnly=True,
                      ImpactParticle="Stick_Slam_Ground_Large", ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            fc.windup(1.4, "SFX_Spear_Throw_Charge", "Golem_Firesteel_Default", "GroundSlam")]}
    out["Nakasar_Fractal_Molten_Berserker_Swipe"] = {
        "$Comment": "Berserker en fusion, au contact : coup (18 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup.", "Golem_Firesteel_Default", "SwingLeft", 0.45, 18, end=4.0,
                                                    extend_bottom=1.8)]}
    return out


MELEE = ["Molten_Pick", "Molten_Sonic_Blast", "Molten_Legion_Strike", "Molten_Legion_Leap", "Molten_Fireball",
         "Molten_Staff", "Molten_Flame_Rain", "Molten_Flame_Wave", "Molten_Resonator_Slam", "Molten_Protector_Touch",
         "Molten_Effigy_Swipes", "Molten_Effigy_Breath", "Molten_Berserker_Chain", "Molten_Berserker_Swipe"]
RANGED = []


def hover_role(role_id, comment, hp):
    """PNJ qui vole (le Java le pose et le déplace) : Fly seul, sans MaintainDistance ni TakeOff."""
    doc = fc.static_role(LANG, role_id, comment, GENERATOR, hp)
    doc["MotionControllerList"] = fc.fly(0.1, 0, 3)
    return doc


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    for role, comment in ((BRAHAM, "Braham Eirsson : accompagne le groupe ; on ne peut pas le blesser (Java)."),
                          (ROX, "Rox : accompagne le groupe ; on ne peut pas la blesser (Java).")):
        out[role] = fc.static_role(LANG, role, comment, GENERATOR, 1000, attitude="Neutral", foe=False)
    out[RESONATOR] = fr.role(
        RESONATOR, "Gardien résonateur draguerre : rend invulnérable l'allié qu'il relie (Java, moltenboss.Packs et "
        "moltenboss.Effigy) et le garde de près : il ne s'éloigne pas de son poste, frappe au marteau et repousse.",
        RESONATOR, n(RESONATOR), HP[RESONATOR],
        [fr.melee(R("Molten_Resonator_Slam"), 2.8, (0.9, 1.3)), fr.chase(14, stop=1.8)], fr.walk(3.0), GENERATOR,
        sight=14, leash=12, home=True, KnockbackScale=0.2, DeathAnimationTime=1.2)
    out[MINER] = fr.role(
        MINER, "Mineur draguerre : coups de pioche.", MINER, n(MINER), HP[MINER],
        [fr.melee(R("Molten_Pick"), 2.6, (0.7, 1.1)), fr.chase(20, stop=1.6)], fr.walk(3.6), GENERATOR, sight=16,
        leash=24, home=False, KnockbackScale=0.6, DeathAnimationTime=1.0)
    out[SONIC] = fr.role(
        SONIC, "Draguerre sonique : onde sonore qui repousse, coups de pioche.", SONIC, n(SONIC), HP[SONIC],
        [fr.timed_attack("Sonic", R("Molten_Sonic_Blast"), rng=6, los=True, comment="Onde sonore."),
         fr.melee(R("Molten_Pick"), 2.6, (0.7, 1.1)), fr.chase(20, stop=3.0)], fr.walk(3.2), GENERATOR, sight=16,
        leash=24, home=False, timers=[fr.timer("Sonic", (1, 3), (6, 8))], KnockbackScale=0.6, DeathAnimationTime=1.0)
    out[WARRIOR] = fr.role(
        WARRIOR, "Guerrier de la Légion de la Flamme : coups brûlants, bond.", WARRIOR, n(WARRIOR), HP[WARRIOR],
        [fr.timed_attack("Leap", R("Molten_Legion_Leap"), rng=12, los=True, comment="Bond."),
         fr.melee(R("Molten_Legion_Strike"), 2.8, (0.7, 1.1)), fr.chase(22, stop=1.8)], fr.walk(3.6), GENERATOR,
        sight=16, leash=24, home=False, timers=[fr.timer("Leap", (3, 5), (9, 12))], KnockbackScale=0.4,
        DeathAnimationTime=1.0)
    out[LEGION_SHAMAN] = fr.role(
        LEGION_SHAMAN, "Chaman de la Légion de la Flamme : boules de feu à distance.", LEGION_SHAMAN, n(LEGION_SHAMAN),
        HP[LEGION_SHAMAN],
        [fr.timed_attack("Fireball", R("Molten_Fireball"), rng=14, los=True, comment="Boule de feu."),
         fr.melee(R("Molten_Staff"), 2.6, (0.8, 1.2)), fr.keep_distance(18, 7, 11)], fr.walk(3.0), GENERATOR,
        sight=18, leash=26, home=False, timers=[fr.timer("Fireball", (1, 2), (4, 6))], KnockbackScale=0.6,
        DeathAnimationTime=1.0)
    out[ELITE_SHAMAN] = fr.role(
        ELITE_SHAMAN, "Chaman de la flamme d'élite : pluie de flammes, vague de flammes ; invulnérable tant que son "
        "résonateur vit (Java, moltenboss.Packs).", ELITE_SHAMAN, n(ELITE_SHAMAN), HP[ELITE_SHAMAN],
        [fr.timed_attack("Rain", R("Molten_Flame_Rain"), rng=16, los=True, comment="Pluie de flammes."),
         fr.timed_attack("Wave", R("Molten_Flame_Wave"), rng=8, los=True, comment="Vague de flammes."),
         fr.melee(R("Molten_Staff"), 3.0, (0.8, 1.2)), fr.chase(24, stop=2.5)], fr.walk(2.8), GENERATOR, sight=18,
        leash=26, home=False, timers=[fr.timer("Rain", (2, 4), (8, 10)), fr.timer("Wave", (5, 7), (9, 12))],
        KnockbackScale=0.2, DeathAnimationTime=1.5)
    out[PROTECTOR] = fr.role(
        PROTECTOR, "Protecteur en fusion : rend l'Effigie invulnérable tant qu'il vit ; lui-même protégé par le "
        "résonateur (Java, moltenboss.Effigy).", PROTECTOR, n(PROTECTOR), HP[PROTECTOR],
        [fr.melee(R("Molten_Protector_Touch"), 2.8, (0.8, 1.2)), fr.chase(24, stop=1.8)], fr.walk(3.0), GENERATOR,
        sight=20, leash=26, home=False, KnockbackScale=0.3, DeathAnimationTime=1.2)
    out[EFFIGY] = fr.role(
        EFFIGY, "Effigie en fusion, barre de boss : deux coups, souffle de flammes. Protecteur, avantages (Puissance) "
        "et ondes de choc : Java (moltenboss.Effigy).", EFFIGY, n(EFFIGY), HP[EFFIGY],
        [fr.timed_attack("Breath", R("Molten_Effigy_Breath"), rng=10, los=True, comment="Souffle de flammes."),
         fr.melee(R("Molten_Effigy_Swipes"), 4.4, (0.8, 1.2)), fr.chase(30, speed=0.9, stop=3.2)], fr.walk(2.8),
        GENERATOR, sight=26, leash=34, home=False, timers=[fr.timer("Breath", (4, 6), (9, 12))], KnockbackScale=0.0,
        DeathAnimationTime=2.0)
    for role, hp, extra in ((BERSERKER, HP[BERSERKER], ""), (BERSERKER_2, HP[BERSERKER_2], " Renforcé : ses ondes "
                                                                                           "font aussi pleuvoir des "
                                                                                           "débris.")):
        out[role] = fr.role(
            role, "Berserker en fusion, barre de boss : enchaînement qui finit en onde de choc devant lui. "
            "Téléportations, ondes blanches au sol et bleues en l'air : Java (moltenboss.MoltenDuo)." + extra, role,
            n(role), hp,
            [fr.timed_attack("Chain", R("Molten_Berserker_Chain"), rng=4.5, los=True, comment="Enchaînement."),
             fr.melee(R("Molten_Berserker_Swipe"), 4.0, (0.9, 1.3)), fr.chase(40, speed=0.9, stop=3.0)],
            fr.walk(3.2), GENERATOR, sight=40, leash=50, home=False, timers=[fr.timer("Chain", (3, 5), (8, 11))],
            KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[FIRESTORM] = hover_role(FIRESTORM, "Tempête de feu en fusion, barre de boss : vole autour de la plate-forme et "
                                "lance des flammes qui restent au sol (Java, moltenboss.MoltenDuo).", HP[FIRESTORM])
    out[FIRESTORM_2] = hover_role(FIRESTORM_2, "Tempête de feu en fusion renforcée, barre de boss : flammes et vent "
                                  "qui jette du bord de la plate-forme (Java, moltenboss.MoltenDuo).", HP[FIRESTORM_2])
    for role in (FIRESTORM, FIRESTORM_2):
        out[role]["NameTranslationKey"] = n(role)
    return out


# --- langue ---------------------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    for role, f, e in ((BRAHAM, "Braham Eirsson", "Braham Eirsson"),
                       (ROX, "Rox", "Rox"),
                       (MINER, "Mineur draguerre", "Dredge Miner"),
                       (SONIC, "Draguerre sonique", "Dredge Sonic Disruptor"),
                       (WARRIOR, "Guerrier de la Légion de la Flamme", "Flame Legion Warrior"),
                       (LEGION_SHAMAN, "Chaman de la Légion de la Flamme", "Flame Legion Shaman"),
                       (RESONATOR, "Gardien résonateur draguerre", "Dredge Resonator Guardian"),
                       (ELITE_SHAMAN, "Chaman de la flamme d'élite", "Elite Flame Shaman"),
                       (PROTECTOR, "Protecteur en fusion", "Molten Protector"),
                       (EFFIGY, "Effigie en fusion", "Molten Effigy"),
                       (BERSERKER, "Berserker en fusion", "Molten Berserker"),
                       (FIRESTORM, "Tempête de feu en fusion", "Molten Firestorm"),
                       (BERSERKER_2, "Berserker en fusion (renforcé)", "Molten Berserker (empowered)"),
                       (FIRESTORM_2, "Tempête de feu en fusion (renforcée)", "Molten Firestorm (empowered)")):
        t.npc(role, f, e)
    for eid, f, e in (("Molten_Burning", "Brûlure de la fonderie", "Foundry burn"),
                      ("Molten_Enraged", "Enragé", "Enraged"),
                      ("Molten_Shielded", "Protégé", "Protected")):
        t.put(f"effects.Nakasar_Fractal_{eid}", f, e)
    msgs = {
        "intro": ("Braham : « La Fonderie de l'Alliance en fusion. Ils forgent ici les armes qui brûleront la Tyrie. »",
                  "Braham: \"The Molten Alliance's facility. This is where they forge the weapons that will burn "
                  "Tyria.\""),
        "intro.rox": ("Rox : « Quatre meutes entre nous et le pont. La dernière a un gardien résonateur : "
                      "abattez-le d'abord. »", "Rox: \"Four packs between us and the bridge. The last one has a "
                      "resonator guardian: take it down first.\""),
        "shielded": ("Le gardien résonateur le protège : abattez le gardien !", "The resonator guardian protects "
                     "it: take the guardian down!"),
        "bridge": ("La meute est vaincue : le pont du canal de lave se pose.", "The pack is defeated: the bridge over "
                   "the lava channel lowers."),
        "lava": ("La lave vous brûle !", "The lava burns you!"),
        "lava.out": ("La lave vous rejette au dernier point de retour.", "The lava throws you back to the last "
                     "checkpoint."),
        "effigy.enter": ("L'Effigie en fusion s'éveille. Son Protecteur la rend invulnérable, et un gardien "
                         "résonateur protège le Protecteur : dans l'ordre !", "The Molten Effigy awakens. Its "
                         "Protector makes it invulnerable, and a resonator guardian protects the Protector: in order!"),
        "effigy.protected": ("Le Protecteur rend l'Effigie invulnérable : abattez-le d'abord !",
                             "The Protector makes the Effigy invulnerable: bring it down first!"),
        "effigy.protector": ("Le Protecteur tombe : l'Effigie est vulnérable.", "The Protector falls: the Effigy is "
                             "vulnerable."),
        "effigy.might": ("L'Effigie se renforce (Puissance {stacks}).", "The Effigy grows stronger (Might "
                         "{stacks})."),
        "effigy.shock": ("L'Effigie frappe le sol : sautez par-dessus l'onde !", "The Effigy pounds the ground: jump "
                         "over the shockwave!"),
        "effigy.victory": ("L'Effigie s'effondre : la porte de la fonderie s'ouvre.", "The Effigy collapses: the "
                           "foundry door opens."),
        "checkpoint": ("Point de retour atteint.", "Checkpoint reached."),
        "groups": ("Groupes vaincus : {count}/{total}.", "Groups defeated: {count}/{total}."),
        "boilers.open": ("Braham : « Le pont du creuset est ouvert. Les deux chefs nous attendent en bas. »",
                         "Braham: \"The crucible bridge is open. Both bosses are waiting below.\""),
        "duo.enter": ("Le Berserker et la Tempête de feu en fusion ! Quand l'un perd un quart de sa vie, l'autre "
                      "enrage. Abattez d'abord la Tempête.", "The Molten Berserker and Firestorm! When one loses a "
                      "quarter of its health, the other becomes enraged. Bring the Firestorm down first."),
        "duo.ground": ("Le Berserker frappe le sol : onde BLANCHE, sautez par-dessus !", "The Berserker smashes the "
                       "ground: WHITE wave, jump over it!"),
        "duo.air": ("Le Berserker frappe l'air : onde BLEUE, restez au sol !", "The Berserker strikes the air: BLUE "
                    "wave, stay on the ground!"),
        "duo.enraged": ("{name} enrage !", "{name} becomes enraged!"),
        "duo.upgrade": ("{name} absorbe la flamme de son allié et se renforce !", "{name} absorbs its ally's flame and "
                        "grows stronger!"),
        "duo.debris": ("Des débris tombent !", "Debris is falling!"),
        "duo.wind": ("La Tempête lève un vent brûlant au bord de la plate-forme : éloignez-vous du bord !",
                     "The Firestorm raises a scorching wind at the platform's edge: move away from the edge!"),
        "duo.victory": ("La fonderie s'éteint. Rox : « Plus de forge, plus d'armes. » Le trésor est à vous.",
                        "The foundry goes cold. Rox: \"No forge, no weapons.\" The treasure is yours."),
        "title.victory": ("Boss en fusion terminé", "Molten Boss complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -----------------------------------------------------------------------------------------------------------

def java_layout(p, t):
    J, jd = fc, fc.jd
    on = lambda x, z: (x, t.stand_at(x, z), z)
    deck, rails = t.bridge
    packs = []
    for (cx, cz), members in PACKS:
        packs.append("new Pack(new double[]" + J.jpoint(on(cx, cz)) + ", new String[]{" + ", ".join(f'"{r}"' for r, _, _ in members)
                     + "}, new double[][]" + J.jpoints([on(cx + dx, cz + dz) for _, dx, dz in members]) + ")")
    adds = [on(x + dx, z + dz) for x, z in sc.EFFIGY_ADDS for dx, dz in ((-1, 0), (1, 1))]
    px, pz = sc.PIT_C
    lava = {(x, z): fc.GROUND_Y + math.floor(t.stand[(x, z)]) for x, z in t.lava}
    lava.update({(x, z): fc.GROUND_Y + sc.ARENA_S for x in range(px - sc.PIT_R - 1, px + sc.PIT_R + 2)
                 for z in range(pz - sc.PIT_R - 1, pz + sc.PIT_R + 2) if math.hypot(x - px, z - pz) <= sc.PIT_R + 0.3})
    cx0, cx1, cz0, cz1 = sc.CHANNEL
    channel = fc.jbox(cx0, cx1, sc.CHANNEL_LAVA_TOP - 2, -1, cz0 + 1, cz1 - 1)
    return f"""package dev.nakasar.hytale.fractals.moltenboss;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions du Boss en fusion, écrites par tools/generate_molten_boss.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class MoltenBossLayout {{

    /** Une meute : centre (pieds), rôles et places de ses membres. */
    public record Pack(double[] center, String[] roles, double[][] at) {{
    }}

    public static final double[] SPAWN = {J.jpoint(sc.SPAWN)};
    public static final double[] BRAHAM = {J.jpoint(sc.BRAHAM_AT)};
    public static final double[] ROX = {J.jpoint(sc.ROX_AT)};
    public static final double[] BRAHAM_END = {J.jpoint(sc.BRAHAM_END)};
    public static final double[] ROX_END = {J.jpoint(sc.ROX_END)};

    /** Meutes 1 à 4 (atelier) puis groupes 5 à 8 (cour des wagonnets, passerelle des cuves). */
    public static final Pack[] PACKS = {{{", ".join(packs)}}};
    /** La meute 4 garde aussi le résonateur et le chaman de la flamme d'élite. */
    public static final double[] RESONATOR_1 = {J.jpoint(on(*sc.RESONATOR_1))};
    public static final double[] ELITE_SHAMAN = {J.jpoint(on(*sc.SHAMAN_AT))};
    /** Pont du canal de lave (tablier, garde-corps), posé quand la meute 4 tombe. */
    public static final int[][] BRIDGE_DECK = {J.jblocks(deck)};
    public static final int[][] BRIDGE_RAILS = {J.jblocks(rails)};
    /** Canal de lave : qui y tombe brûle puis revient au point de retour. */
    public static final Box CHANNEL = {channel};
    /** Cases de lave des bassins et du creuset (x, z, y du sol autour ; surface un bloc dessous) : la lave brûle. */
    public static final int[][] LAVA_CELLS = {{{", ".join("{" + f"{x}, {z}, {y}" + "}" for (x, z), y in sorted(lava.items()))}}};
    /** Pieds sous ce y : tombé dans le gouffre, vers la mer de lave (brûle, puis retour au dernier point de retour). */
    public static final double ABYSS_Y = {fc.GROUND_Y + sc.ABYSS_S};

    /** La fonderie : centre de l'Effigie, rayon du combat, Protecteur, second résonateur, renforts, porte est. */
    public static final double[] EFFIGY = {J.jpoint(on(*sc.EFFIGY_C))};
    public static final double EFFIGY_RADIUS = {jd(sc.EFFIGY_R)};
    public static final double[] PROTECTOR = {J.jpoint(on(*sc.PROTECTOR_AT))};
    public static final double[] RESONATOR_2 = {J.jpoint(on(*sc.RESONATOR_2))};
    public static final String[] EFFIGY_ADD_ROLES = {{{", ".join(f'"{r}"' for r in EFFIGY_ADD_ROLES)}}};
    public static final double[][] EFFIGY_ADDS = {J.jpoints(adds)};
    public static final int[][] FOUNDRY_GATE = {J.jblocks(t.gates["foundry"])};
    public static final double[] CHECKPOINT_B = {J.jpoint(sc.CHECKPOINT_B)};

    /** Salle des chaudières : barrière du pont du creuset, point de retour. */
    public static final int[][] BOILERS_GATE = {J.jblocks(t.gates["boilers"])};
    public static final double[] CHECKPOINT_D = {J.jpoint(sc.CHECKPOINT_D)};

    /** La plate-forme du creuset : centre, rayon, creuset de lave (muret compris). */
    public static final double[] ARENA = {J.jpoint(on(*sc.ARENA_C))};
    public static final double ARENA_RADIUS = {jd(sc.ARENA_R)};
    public static final double[] PIT = {J.jpoint(on(*sc.PIT_C))};
    public static final double PIT_RADIUS = {jd(sc.PIT_R + 1.3)};
    /** Ondes de choc : vitesse, demi-épaisseur, hauteur de l'onde bleue. */
    public static final double SHOCK_SPEED = {jd(SHOCK_SPEED)};
    public static final double SHOCK_BAND = {jd(SHOCK_BAND)};
    public static final double AIR_RING_HEIGHT = {jd(AIR_RING_HEIGHT)};
    public static final double SHOCK_REACH_EFFIGY = {jd(SHOCK_REACH_EFFIGY)};
    public static final double SHOCK_REACH_DUO = {jd(SHOCK_REACH_DUO)};
    public static final double RING_SCALE = {jd(RING_SCALE)};
    /** Flammes de la Tempête (rayon, durée), débris, couronne de vent ({WIND_SEGMENTS} bandes de {WIND_LENGTH} x {WIND_BAND} : JAVA_LINES). */
    public static final double FIRE_POOL_RADIUS = {jd(FIRE_POOL_R)};
    public static final float FIRE_POOL_SECONDS = {FIRE_POOL_SECONDS}f;
    public static final double DEBRIS_RADIUS = {jd(DEBRIS_R)};
    public static final double WIND_BAND = {jd(WIND_BAND)};
    public static final int WIND_SEGMENTS = {WIND_SEGMENTS};
    public static final double WIND_LENGTH = {jd(WIND_LENGTH)};
    public static final double FIRESTORM_ORBIT = {jd(FIRESTORM_ORBIT)};
    public static final double FIRESTORM_HOVER = {jd(FIRESTORM_HOVER)};
    public static final int[] REWARD = {J.jblock(sc.REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(sc.END_EXIT_AT)};

    private MoltenBossLayout() {{
    }}
}}
"""


# --- aperçus --------------------------------------------------------------------------------------------------------

def color_of(name):
    c = fn.nature_color(name)
    if c:
        return c
    if name == sc.BARRIER:
        return (200, 120, 255)
    if "Lava" in name or "Incandescent" in name:
        return (255, 100, 20)
    if "Iron" in name or name in ("Rail", "Rail_Kart"):
        return (150, 150, 160)
    if "Furniture" in name:
        return (170, 120, 70)
    if any(k in name for k in ("Volcanic", "Basalt", "Magma", "Ash", "Burnt")):
        return (70, 60, 58)
    if name.startswith(("Soil", "Rock", "Ore")):
        return (110, 105, 100)
    return (200, 200, 200)


def course_prefab():
    """Pour la carte du wiki (render_wiki_maps)."""
    p, _ = sc.build_all()
    return p


def preview_images(p, folder):
    q = go.Prefab()
    q.blocks = dict(p.blocks)
    for (x, y, z), (f, _) in p.fluids.items():
        if (x, y + 1, z) not in q.blocks:
            q.blocks[(x, y, z)] = (f, 0)
    fc.top_view(q, folder / "boss_en_fusion_dessus.png", color_of, scale=3)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    status_icons()
    fc.write_json(fc.SERVER / f"Entity/Damage/{CAUSE}.json", molten_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in shock_rings().items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "MoltenBoss" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fr.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p, t = sc.build_all()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Ciel de fournaise : haut brun fumée, horizon rouge braise, brume orangée ; soleil rouge et bas.
    weather = fc.weather("#1a0f0c", "#8a2a10", "#4a2418", (40, 220), 0.4, "#c08060", sun="#ff6a30")
    counts = fc.write_instance(INSTANCE, "Boss en fusion", PREFAB_DIR, sections, sc.SPAWN, "#7a6a40",
                               WEATHER, weather, "19:30")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(p, t), encoding="utf-8")
    print(f"Boss en fusion : {sum(counts.values())} blocs et {len(p.fluids)} cases de fluide en {len(counts)} tronçons, "
          f"{len(roles())} rôles, {len(PARTICLE_SYSTEMS)} particules")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        preview_images(p, preview)


if __name__ == "__main__":
    main()
