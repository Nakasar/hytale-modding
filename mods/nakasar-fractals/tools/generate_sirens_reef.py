#!/usr/bin/env python3
"""Génère le Récif de la Sirène (Siren's Reef), fractale de la saison 2 (docs/fractales/gdd.md), d'après GW2
(metabattle.com/wiki/Guide:Siren%27s_Reef et hardstuck.gg/gw2/guides/fractal-maps/sirens-reef).

    python3 mods/nakasar-fractals/tools/generate_sirens_reef.py [--preview DOSSIER]

Une île de jungle cernée par la mer, où l'équipage fantôme d'Arabella Crowe garde le trésor maudit. Dans l'ordre :

1. la plage du naufrage (le capitaine Strohm et le mousse Weyandt) et les camps de sauriens du rivage ;
2. Tête-de-pierre, champion des raptors : charges, meutes de raptors de poche à 75 et 50 % ; à 25 %, il rugit, brise
   la barrière de rochers et s'enfuit dans le ravin, où la première mine l'emporte ;
3. le ravin miné : le canon des ombres sur sa corniche (tir ricochet, mitraille, tir de glace) fait sauter les mines,
   qui reviennent, et abat la palissade du bout ;
4. le fort englouti : les fantômes, puis Black Peter la Mèche : bombes, mines sous les joueurs, mines semées à chaque
   quart de vie qu'il ramasse pour se renforcer (défiance), fantômes tous les 10 %, cyclone de cendres hors du fort ;
   le canon du rempart brise sa défiance et ses mines ;
5. le sentier de jungle (deux meutes de raptors), la grande tête de pierre dont la bouche s'ouvre ;
6. le labyrinthe : trois trésors maudits à rapporter au coffre de la sortie (la malédiction monte tant qu'on porte,
   on peut lancer le trésor à un autre joueur), orbes spectrales qui rebondissent dans les couloirs ;
7. la crique et le Fierté du Kraken : trésor de la plage sud (fantômes, escrocs, tireurs fantômes) puis Mad Jack
   Squall ; trésor de la plage nord puis le second Calix ; la défense du navire ; Arabella Crowe. Brouillard fétide
   sur les plages et piranhas dans l'eau pendant les combats du navire, courants fantômes sur le pont.

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_SirensReef`, les blocs (canon,
mine, coffre de la sirène), les objets (trésor maudit, trois boulets), effets, particules, modèles (parents vanilla),
rôles, le temps (plein soleil des tropiques), la langue `nakasar_fractals_sirens_reef.lang` et
`sirensreef/SirensReefLayout.java`. Repère : y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_common as fc
import fractal_nature as fn
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go
import sirens_reef_scenery as sc

LANG = "nakasar_fractals_sirens_reef"
GENERATOR = "generate_sirens_reef.py"
INSTANCE = "Nakasar_Fractal_SirensReef"
WEATHER = "Nakasar_Fractal_Weather_SirensReef"
PREFAB_DIR = "SirensReef"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/sirensreef/SirensReefLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/SirensReef"
REEF_CAUSE = "Nakasar_Fractal_Reef"

# --- blocs, objets, rôles ----------------------------------------------------------------------------------
CANNON = "Nakasar_Fractal_Shadow_Cannon"
MINE = "Nakasar_Fractal_Reef_Mine"
SIREN_CHEST = "Nakasar_Fractal_Siren_Chest"
TREASURE = "Nakasar_Fractal_Cursed_Treasure"
SHOTS = {"Ripple": "Nakasar_Fractal_Cannon_Ripple", "Scatter": "Nakasar_Fractal_Cannon_Scatter",
         "Ice": "Nakasar_Fractal_Cannon_Ice"}
STROHM = "Nakasar_Fractal_Captain_Strohm"
WEYANDT = "Nakasar_Fractal_Cabin_Boy_Weyandt"
BRISTLEBACK = "Nakasar_Fractal_Saurian_Bristleback"
BONEBREAKER = "Nakasar_Fractal_Saurian_Bonebreaker"
SMOKESCALE = "Nakasar_Fractal_Saurian_Smokescale"
RAPTOR = "Nakasar_Fractal_Pocket_Raptor"
STONEHEAD = "Nakasar_Fractal_Stonehead"
GHOST = "Nakasar_Fractal_Ghost_Pirate"
MARKSMAN = "Nakasar_Fractal_Phantom_Marksman"
SWINDLER = "Nakasar_Fractal_Ghostly_Swindler"
PETER = "Nakasar_Fractal_Blasting_Black_Peter"
JACK = "Nakasar_Fractal_Mad_Jack_Squall"
CALIX = "Nakasar_Fractal_First_Mate_Calix"
ARABELLA = "Nakasar_Fractal_Arabella_Crowe"
FOE_ROLES = [BRISTLEBACK, BONEBREAKER, SMOKESCALE, RAPTOR, STONEHEAD, GHOST, MARKSMAN, SWINDLER, PETER, JACK,
             CALIX, ARABELLA]
CAMP_ROLES = {"bristleback": BRISTLEBACK, "bonebreaker": BONEBREAKER, "smokescale": SMOKESCALE}
# Courants fantômes : une bande en travers du pont (Java, sirensreef.ReefShip) ; tools/generate_warnings.JAVA_LINES.
DRAFT_LENGTH = 2 * sc.SHIP_HALF + 2
DRAFT_WIDTH = 8


class Course:
    """La carte posée et ce que le Java doit connaître."""

    def __init__(self):
        self.p = go.Prefab()
        self.t = sc.Terrain()
        self.deck = {}
        self.cannons = []                # [(bloc (x, y, z), rotation, lieu)]
        self.wall1 = []
        self.wall2 = []
        self.fort_gate = []
        self.teeth = []
        self.maze_exit = []
        self.mines = []
        self.treasures = []
        self.orbs = []
        self.maze_chest = None

    def stand(self, x, z):
        return self.t.stand[(round(x), round(z))]

    def at(self, x, z):
        return (round(x), self.stand(x, z), round(z))


def build_course():
    c = Course()
    p, t = c.p, c.t
    soils = sc.lay_ground(p, t)
    sc.lay_sea(p, t)
    cliff_tops = sc.lay_cliffs(p, t)
    sc.wreck(p, t)
    for name, ((cx, cz), _) in sc.CAMPS.items():
        sc.saurian_camp(p, t, cx, cz, 9720 + cx)
    gates(c)
    sc.fort(p, t)
    c.teeth = sc.stone_head(p, t)
    c.deck = sc.ship(p, t)
    sc.beach_camp(p, t, 40, -172, 9730)
    sc.beach_camp(p, t, 14, -226, 9731)
    maze(c)
    cannons(c)
    keep = keep_out(c)
    sc.maze_decor(p, t, keep)
    sc.dress_beaches(p, t, keep)
    sc.dress_jungle(p, t, soils, cliff_tops, keep)
    check_sight(c)
    return c


def see_through(name):
    """Herbes, fougères et lianes : le regard (et le boulet) passe au travers."""
    return name == go.AIR or name.startswith(("Plant_Grass", "Plant_Fern", "Plant_Vine", "Plant_Flower"))


def check_sight(c):
    """Depuis la corniche, le canon doit toucher chaque mine du ravin et la palissade (même lancer de rayon que
    Moves.cast : premier bloc plein le long du regard), à portée, depuis n'importe où à 2,5 blocs du canon."""
    p = c.p
    cx, cy, cz = sc.CANNON_LEDGE
    eyes = [(x + 0.5, cy + 1.6, z + 0.5) for x in range(cx - 3, cx + 4) for z in range(cz - 3, cz + 4)
            if 1 <= math.hypot(x - cx, z - cz) <= 2.5 and c.t.stand.get((x, z)) == cy]
    assert eyes, "corniche : aucune place pour l'artilleur"

    def cast(a, b):
        d = [b[i] - a[i] for i in range(3)]
        n = math.sqrt(sum(v * v for v in d))
        u = [v / n for v in d]
        prev, k = a, 0.5
        while k <= sc.CANNON_RANGE:
            q = tuple(a[i] + u[i] * k for i in range(3))
            cell = tuple(math.floor(v) for v in q)
            if not see_through(p.blocks.get(cell, (go.AIR,))[0]):
                return prev
            prev, k = q, k + 0.25
        return None

    # visée : le sol au pied de chaque mine (souffle du ricochet : 2,5 blocs), le milieu de la palissade
    w = c.wall2[len(c.wall2) // 2]
    targets = [((x + 0.5, y + 0.05, z + 0.5), 2.5) for x, y, z in c.mines] + [((w[0] + 0.5, w[1] + 1.5, w[2] + 0.5), 2.5 + 3)]
    for eye in eyes:
        for at, tolerance in targets:
            hit = cast(eye, at)
            assert hit is not None and math.dist(hit, at) <= tolerance, \
                f"canon de la corniche : depuis {eye}, {at} caché (impact {hit})"


def gates(c):
    """Barrières : rochers devant le ravin, palissade au bout du ravin, porte de grès vers la jungle."""
    p, t = c.p, c.t
    c.wall1 = sc.boulder_wall(p, t, sc.across("ravine", sc.WALL1_AT, 4.5, 1), 4, 9741)
    c.wall2 = sc.palisade(p, t, sc.across("ravine", sc.WALL2_AT, 4.5, 1), 4)
    cells = sc.across("jungle", sc.FORT_GATE_AT, 5, 1)
    for x, z in cells:
        s = t.stand.get((x, z))
        if s is None:
            continue
        for y in range(s, s + 5):
            p.set(x, y, z, sc.pick(sc.FORT, x, y, z))
            c.fort_gate.append((x, y, z))
    s = sc.curve(sc.PATHS["ravine"])
    for f in sc.MINE_FRACTIONS:
        x, z, _, _ = s[int(f * (len(s) - 1))]
        c.mines.append(c.at(x, z))


def maze(c):
    """Le labyrinthe : trésors au fond de trois culs-de-sac, coffre de la sirène à la sortie, barrière de la sortie."""
    p, t = c.p, c.t
    m = t.maze
    for cell in m.treasure_cells():
        x, z = m.center(cell)
        c.treasures.append(c.at(x, z))
    for cell in m.orb_cells():
        x, z = m.center(cell)
        c.orbs.append(c.at(x, z))
    ex, ez = sc.PATHS["exit"][0][:2]
    chest = (round(ex) - 3, sc.MAZE_STAND, round(ez) + 2)
    if chest[::2] not in t.stand:
        chest = c.at(ex - 1, ez)
    p.set(*chest, SIREN_CHEST, 3)
    c.maze_chest = chest
    for x, z in sc.across("exit", sc.curve(sc.PATHS["exit"])[6][:2], 3.5, 1):
        s = t.stand.get((x, z))
        if s is None:
            continue
        for y in range(s, s + 5):
            p.set(x, y, z, "Rock_Stone_Brick_Mossy")
            c.maze_exit.append((x, y, z))
    p.set(sc.DECK_C[0], sc.DECK_STAND, sc.DECK_C[2], SIREN_CHEST, 0)


def cannons(c):
    """Canons des ombres : corniche du ravin, rempart du fort, quatre sur le pont (deux par bord)."""
    p = c.p
    spots = [(sc.CANNON_LEDGE, 1, "ravine"), (sc.FORT_CANNON, 3, "fort")]
    for x in (18, 42):
        spots.append(((x, sc.DECK_STAND, sc.SHIP_Z + sc.SHIP_HALF - 2), 0, "ship"))
        spots.append(((x, sc.DECK_STAND, sc.SHIP_Z - sc.SHIP_HALF + 2), 2, "ship"))
    for at, rot, where in spots:
        p.set(*at, CANNON, rot)
        c.cannons.append((at, rot, where))


def keep_out(c):
    """Cercles (x, z, r) sans arbre ni rocher : lieux de combat, canons, barrières, chemins du navire."""
    keep = [(sc.CLEARING[0], sc.CLEARING[1], 12), (sc.FORT_C[0], sc.FORT_C[1], 14), (sc.PLAZA[0], sc.PLAZA[1], 8),
            (sc.SPAWN[0], sc.SPAWN[2], 6), (sc.STROHM_AT[0], sc.STROHM_AT[2], 3)]
    keep += [(x, z, 6) for (x, z), _ in sc.CAMPS.values()]
    keep += [(x, z, 7) for x, z in sc.GLADES]
    keep += [(at[0], at[2], 4) for at, _, _ in c.cannons]
    keep += [(x, z, 3) for x, _, z in c.treasures + c.orbs + c.mines]
    keep += [(gx, bz + (rz - bz) / 2, 6) for gx, bz, rz in sc.GANGPLANKS]
    keep += [(sc.SOUTH_TREASURE[0], sc.SOUTH_TREASURE[2], 5), (sc.NORTH_TREASURE[0], sc.NORTH_TREASURE[2], 5)]
    keep += [(x, z, 2) for x, _, z in c.wall1 + c.wall2 + c.fort_gate + c.maze_exit]
    keep += [(c.maze_chest[0], c.maze_chest[2], 3)]
    # ligne de visée du canon de la corniche vers la palissade
    (ax, _, az), (bx, bz) = sc.CANNON_LEDGE, sc.WALL2_AT
    n = math.hypot(bx - ax, bz - az)
    keep += [(ax + (bx - ax) * k / n, az + (bz - az) * k / n, 3.5) for k in range(0, int(n), 3)]
    return keep


# --- blocs et objets ------------------------------------------------------------------------------------------------

# Vanilla d'abord (AGENTS.md) : le canon du Gobliterator, la bombe gobeline, le petit coffre ancien.
VANILLA_BLOCKS = {
    CANNON: {
        "Icon": "Icons/ItemsGenerated/Weapon_Bomb_Fire_Goblin.png",
        "BlockType": {"DrawType": "Model", "Opacity": "Transparent",
                      "CustomModel": "NPC/Boss/Goblin_Gobliterator/Models/Goblin_Cannon.blockymodel",
                      "CustomModelTexture": [{"Texture": "NPC/Boss/Goblin_Gobliterator/Models/Goblin_Cannon.png",
                                              "Weight": 1}],
                      "CustomModelScale": 0.55, "VariantRotation": "NESW", "BlockParticleSetId": "Stone",
                      "BlockSoundSetId": "Stone"},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    },
    MINE: {
        "Icon": "Icons/ItemsGenerated/Weapon_Bomb_Fire_Goblin.png",
        "BlockType": {"DrawType": "Model", "Opacity": "Transparent",
                      "CustomModel": "NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire.blockymodel",
                      "CustomModelTexture": [{"Texture": "NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire_Texture.png",
                                              "Weight": 1}],
                      "CustomModelScale": 1.4, "BlockParticleSetId": "Stone", "BlockSoundSetId": "Stone"},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    },
    SIREN_CHEST: {
        "Icon": "Icons/ItemsGenerated/Furniture_Ancient_Chest_Small.png",
        "BlockType": {"DrawType": "Model", "Opacity": "Transparent",
                      "CustomModel": "Blocks/Decorative_Sets/Ancient/Chest_Small.blockymodel",
                      "CustomModelTexture": [{"Texture": "Blocks/Decorative_Sets/Ancient/Chest_Small_Texture.png",
                                              "Weight": 1}],
                      "VariantRotation": "NESW", "BlockParticleSetId": "Wood", "BlockSoundSetId": "Wood"},
        "ItemSoundSetId": "ISS_Blocks_Wood",
    },
}
BLOCK_LOOKS = {  # id : (lumière, interaction, plein)
    CANNON: ("#a6f", "Nakasar_Fractal_Use_SirensReef_Cannon", True),
    MINE: ("#f84", None, False),
    SIREN_CHEST: ("#fc6", None, True),
}


def write_blocks():
    for name, look in VANILLA_BLOCKS.items():
        light, use, solid = BLOCK_LOOKS[name]
        doc = go.block_item(name, name, light, use, solid=solid)
        doc["TranslationProperties"] = {"Name": f"{LANG}.items.{name}.name",
                                        "Description": f"{LANG}.items.{name}.description"}
        doc["Icon"] = look["Icon"]
        doc["ItemSoundSetId"] = look["ItemSoundSetId"]
        block = doc["BlockType"]
        block.pop("Textures", None)
        block.update(look["BlockType"])
        fc.write_json(go.ITEMS / f"{name}.json", doc)


BOMB_MODEL = "NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire.blockymodel"
BOMB_TEXTURE = "NPC/Intelligent/Goblin/Models/Weapons/Bomb/Fire_Texture.png"
SHOT_ICONS = {"Ripple": "Icons/ItemsGenerated/Weapon_Bomb_Large_Fire.png",
              "Scatter": "Icons/ItemsGenerated/Weapon_Bomb_Fire_Goblin.png",
              "Ice": "Icons/ItemsGenerated/Weapon_Bomb_Popberry.png"}


def items():
    """Le trésor maudit (modèle et texture du trésor vanilla) et les trois boulets du canon (bombe gobeline vanilla)."""
    out = {TREASURE: {
        "TranslationProperties": {"Name": f"{LANG}.items.{TREASURE}.name", "Description": f"{LANG}.items.{TREASURE}.description"},
        "Icon": "Icons/ItemsGenerated/Deco_Scrap_Treasure.png",
        "IconProperties": {"Scale": 0.6, "Rotation": [358, 265, 341], "Translation": [-1, -10]},
        "Model": "Blocks/Dungeons/Treasure_Object.blockymodel",
        "Texture": "Blocks/Dungeons/Treasure_Pile_Texture.png",
        "Scale": 0.8,
        "Light": {"Color": "#fc6", "Radius": 2},
        "Quality": "Epic",
        "Categories": ["Items.Misc"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
        "Interactions": {"Secondary": "Root_Nakasar_Fractal_Reef_Throw", "SwapFrom": fc.KEEP_IN_HAND},
        "Utility": {"Compatible": False},
    }}
    for kind, item_id in SHOTS.items():
        out[item_id] = {
            "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
            "Icon": SHOT_ICONS[kind], "Model": BOMB_MODEL, "Texture": BOMB_TEXTURE, "Quality": "Rare",
            "Categories": ["Items.Misc"], "PlayerAnimationsId": "Item", "ItemSoundSetId": "ISS_Items_Gems", "MaxStack": 1,
            "IconProperties": {"Scale": 0.87, "Translation": [-7.11, -7.7], "Rotation": [4.685, 6.935, 315]},
            "Interactions": {"Secondary": f"Root_Nakasar_Fractal_Reef_{kind}"}, "Utility": {"Compatible": False},
        }
    return out


ACTIONS = {
    "Throw": "Trésor maudit : clic droit, le lancer au joueur visé (16 blocs) ; personne en vue : il tombe trois blocs "
             "devant. Le lanceur reçoit l'Allègement de la malédiction (Java, sirensreef.CursedTreasure).",
    "Ripple": "Canon des ombres, tir ricochet : trois impacts de 2,5 blocs qui rebondissent dans l'axe du tir (Java, "
              "sirensreef.ShadowCannon).",
    "Scatter": "Canon des ombres, mitraille : un impact de 4 blocs, gros dégâts et étourdissement (Java).",
    "Ice": "Canon des ombres, tir de glace : un impact de 5 blocs qui gèle les ennemis (Java).",
}


def action_interactions():
    out = {}
    for action, comment in ACTIONS.items():
        out[f"Nakasar_Fractal_Reef_{action}"] = {"$Comment": comment, "Type": "Nakasar_Fractal_ReefAction",
                                                 "Action": action}
    out["Nakasar_Fractal_Use_SirensReef_Cannon"] = fc.use_interaction(
        "SirensReef_Cannon", "Canon des ombres : s'y poster (les trois boulets en main) ou le quitter (Java, "
        "sirensreef.ShadowCannon).")
    return out


# --- effets -------------------------------------------------------------------------------------------------------

def effects():
    L = LANG
    return {
        "Nakasar_Fractal_Dazed": fc.effect(
            L, "Nakasar_Fractal_Dazed", "Hébété : on ne peut plus bouger ni agir.", "Dazed", 2.0, debuff=True,
            ApplicationEffects={"MovementEffects": {"DisableAll": True}, "EntityTopTint": "#d8d080"}),
        "Nakasar_Fractal_Chilled": fc.effect(
            L, "Nakasar_Fractal_Chilled", "Glacé (souffle de Mad Jack Squall) : déplacement ralenti.", "Chilled", 4.0,
            debuff=True, ApplicationEffects={"HorizontalSpeedMultiplier": 0.6, "EntityTopTint": "#9ad0ff"}),
        "Nakasar_Fractal_Cursed_1": fc.effect(
            L, "Nakasar_Fractal_Cursed_1", "Malédiction du trésor, premier degré : un peu ralenti (Java).", "Cursed_1",
            3.0, debuff=True, ApplicationEffects={"HorizontalSpeedMultiplier": 0.85, "EntityTopTint": "#c0a040"}),
        "Nakasar_Fractal_Cursed_2": fc.effect(
            L, "Nakasar_Fractal_Cursed_2", "Malédiction du trésor, deuxième degré : ralenti, la vie s'en va (Java).",
            "Cursed_2", 3.0, debuff=True,
            ApplicationEffects={"HorizontalSpeedMultiplier": 0.65, "EntityTopTint": "#a06020"}),
        "Nakasar_Fractal_Cursed_3": fc.effect(
            L, "Nakasar_Fractal_Cursed_3", "Malédiction du trésor, dernier degré : figé sur place, le trésor tombe "
            "(Java).", "Cursed_3", 2.0, debuff=True,
            ApplicationEffects={"MovementEffects": {"DisableAll": True}, "EntityTopTint": "#602000",
                                "EntityBottomTint": "#200800"}),
        "Nakasar_Fractal_Curse_Relief": fc.effect(
            L, "Nakasar_Fractal_Curse_Relief", "Allègement de la malédiction : la malédiction ne monte plus et retombe "
            "(Java).", "Curse_Relief", 8.0),
        "Nakasar_Fractal_Gunpowder": fc.effect(
            L, "Nakasar_Fractal_Gunpowder", "Poudre noire (Black Peter a avalé une mine) : dégâts subis réduits de "
            "moitié tant que sa défiance tient (Java).", "Gunpowder", 30.0,
            DamageResistance={k: [{"CalculationType": "Percent", "Amount": 0.5}]
                              for k in ("Physical", "Projectile", "Elemental")},
            ApplicationEffects={"EntityTopTint": "#ff8020"}),
        "Nakasar_Fractal_Cinders": fc.effect(
            L, "Nakasar_Fractal_Cinders", "Cyclone de cendres : brûlure qui s'aggrave tant que personne n'est dans le "
            "fort (Java).", "Cinders", 2.0, debuff=True, ApplicationEffects={"EntityBottomTint": "#ff6020"}),
        "Nakasar_Fractal_Fetid_Fog": fc.effect(
            L, "Nakasar_Fractal_Fetid_Fog", "Brouillard fétide : hors du navire pendant un combat, poison (Java).",
            "Fetid_Fog", 2.0, debuff=True, ApplicationEffects={"EntityTopTint": "#70a040"}),
        "Nakasar_Fractal_Piranhas": fc.effect(
            L, "Nakasar_Fractal_Piranhas", "Piranhas des profondeurs : dans l'eau pendant un combat du navire, morsures "
            "(Java).", "Piranhas", 2.0, debuff=True, ApplicationEffects={"EntityBottomTint": "#c02020"}),
        "Nakasar_Fractal_Grim_Lagoon": fc.effect(
            L, "Nakasar_Fractal_Grim_Lagoon", "Lagon sinistre : +30 % de dégâts subis et ralenti tant qu'on y reste ; les "
            "ennemis dedans sont protégés (Java).", "Grim_Lagoon", 1.5, debuff=True,
            DamageResistance={k: [{"CalculationType": "Percent", "Amount": -0.3}]
                              for k in ("Physical", "Projectile", "Elemental")},
            ApplicationEffects={"HorizontalSpeedMultiplier": 0.8, "EntityBottomTint": "#204040"}),
        "Nakasar_Fractal_Frozen_Shot": fc.effect(
            L, "Nakasar_Fractal_Frozen_Shot", "Gelé par le tir de glace du canon des ombres.", "Frozen_Shot", 4.0,
            debuff=True, ApplicationEffects={"EntityTopTint": "#b0e8ff", "EntityBottomTint": "#6090c0"}),
    }


def status_icons():
    icons = fc.COMMON / fc.STATUS_ICONS
    for name, color, glyph in (("Dazed", (220, 210, 120), "minus"), ("Chilled", (140, 200, 255), "feet"),
                               ("Cursed_1", (200, 170, 70), "minus"), ("Cursed_2", (190, 110, 40), "minus"),
                               ("Cursed_3", (140, 50, 20), "minus"), ("Curse_Relief", (255, 220, 120), "plus"),
                               ("Gunpowder", (255, 140, 40), "flame"), ("Cinders", (255, 100, 40), "flame"),
                               ("Fetid_Fog", (120, 170, 70), "minus"), ("Piranhas", (210, 40, 40), "minus"),
                               ("Grim_Lagoon", (40, 120, 120), "minus"), ("Frozen_Shot", (180, 230, 255), "feet")):
        fc.status_icon(icons / f"{name}.png", color, glyph)


def reef_cause():
    return fc.cause("Mines, malédiction, cyclone de cendres, brouillard, piranhas et dents des profondeurs du Récif de "
                    "la Sirène : une part des PV max, l'armure ne la réduit pas.", "#ffb040")


# --- particules -----------------------------------------------------------------------------------------------------

S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Cannon_Smoke": ("Canon des ombres : fumée violette à la bouche.",
                                     [("Smoke", S("#d0a0ff", "#301040", 24, (1.0, 3.0), (-10, 60), 0.6, 0.6,
                                                  life=(0.6, 1.2), size=(0.3, 0.6), blend="BlendLinear"), 1.0)]),
    "Nakasar_Fractal_Cannon_Trail": ("Boulet des ombres en vol : un point de sa traînée (le Java en pose le long du "
                                     "trajet).",
                                     [("Trail", S("#ffffff", "#9040ff", 3, (0.0, 0.3), (-90, 90), 0.1, 0.1,
                                                  life=(0.3, 0.5), size=(0.25, 0.35)), 0.0)]),
    "Nakasar_Fractal_Cannon_Blast": ("Impact d'un boulet des ombres : éclat violet et fumée.",
                                     [("Burst", S("#ffffff", "#a050ff", 40, (2.0, 6.0), (-10, 90), 0.8, 0.6,
                                                  life=(0.4, 0.8), size=(0.3, 0.6)), 0.3),
                                      ("Smoke", S("#a080c0", "#202030", 20, (0.6, 1.6), (20, 90), 1.4, 1.0,
                                                  life=(1.0, 1.6), size=(0.4, 0.8), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Ice_Burst": ("Tir de glace : éclats de givre.",
                                  [("Frost", S("#ffffff", "#80d0ff", 40, (2.0, 5.0), (-10, 90), 1.0, 0.6,
                                               life=(0.6, 1.0), size=(0.2, 0.4)), 0.3)]),
    "Nakasar_Fractal_Mine_Fuse": ("Mine armée : étincelles de la mèche.",
                                  [("Sparks", S("#fff0a0", "#ff6010", 6, (0.8, 2.0), (40, 90), 0.1, 0.1,
                                                life=(0.2, 0.4), size=(0.06, 0.12)), 0.8)]),
    "Nakasar_Fractal_Mine_Blast": ("Explosion d'une mine : feu et fumée noire.",
                                   [("Fire", S("#fff0a0", "#ff4010", 36, (2.5, 6.0), (-10, 90), 1.0, 0.6,
                                               life=(0.3, 0.6), size=(0.3, 0.7)), 0.3),
                                    ("Smoke", S("#808080", "#202020", 22, (0.6, 1.6), (20, 90), 1.6, 1.0,
                                                life=(1.0, 1.8), size=(0.5, 0.9), blend="BlendLinear"), 0.8)]),
    "Nakasar_Fractal_Ghost_Rise": ("Un fantôme pirate surgit : brume cyan.",
                                   [("Mist", S("#e0ffff", "#20a0b0", 24, (0.5, 1.6), (30, 90), 0.8, 2.0,
                                               life=(0.8, 1.4), blend="BlendLinear"), 0.2)]),
    "Nakasar_Fractal_Reef_Orb": ("Orbe spectrale du labyrinthe : boule blanche et halo.",
                                 [("Core", S("#ffffff", "#c0f0ff", 6, (0.0, 0.2), (-90, 90), 0.2, 0.2,
                                             life=(0.3, 0.4), size=(0.5, 0.7)), 1.0),
                                  ("Halo", S("#ffffff", "#80c0ff", 8, (0.4, 1.0), (-90, 90), 0.5, 0.5,
                                             life=(0.3, 0.5), size=(0.1, 0.2)), 1.0)]),
    "Nakasar_Fractal_Orb_Ring": ("Cercle blanc d'une orbe spectrale : là où elle touche, des fantômes se lèvent.",
                                 [("Ring", S("#ffffff", "#c0e0ff", 30, (1.6, 2.0), (-5, 5), 0.3, 0.1,
                                             life=(0.4, 0.5)), 0.1)]),
    "Nakasar_Fractal_Curse_Motes": ("Malédiction du trésor : poussière d'or et de suie autour du porteur.",
                                    [("Motes", S("#ffe080", "#402000", 6, (0.2, 0.6), (30, 90), 0.6, 1.2,
                                                 life=(0.6, 1.0), size=(0.08, 0.14)), 1.0)]),
    "Nakasar_Fractal_Treasure_Glow": ("Trésor maudit au sol : lueur d'or qui monte.",
                                      [("Glow", S("#fff0a0", "#c08020", 8, (0.4, 1.0), (60, 90), 0.4, 0.2,
                                                  life=(0.8, 1.2), size=(0.1, 0.2)), 0.2)]),
    "Nakasar_Fractal_Fetid_Fog": ("Brouillard fétide sur une plage : volutes vert-gris.",
                                  [("Fog", S("#a0b080", "#405030", 4, (0.2, 0.5), (-10, 30), 2.0, 0.8,
                                             life=(1.6, 2.4), size=(1.0, 1.6), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Grim_Lagoon": ("Lagon sinistre : eau noire et bulles.",
                                    [("Pool", S("#408080", "#001010", 16, (0.1, 0.4), (60, 90), 1.6, 0.1,
                                                life=(0.8, 1.2), size=(0.3, 0.5), blend="BlendLinear"), 0.1)]),
    "Nakasar_Fractal_Deep_Teeth": ("Dents des profondeurs : mâchoires d'eau qui jaillissent.",
                                   [("Jaws", S("#e0ffff", "#2080a0", 50, (3.0, 7.0), (40, 90), 1.6, 0.4,
                                               life=(0.5, 0.9), size=(0.2, 0.4)), 0.2)]),
    "Nakasar_Fractal_Draft_Gust": ("Courant fantôme : rafale blanche qui balaie le pont.",
                                   [("Gust", S("#ffffff", "#a0e0ff", 30, (5.0, 9.0), (-5, 15), 1.2, 0.8,
                                               life=(0.4, 0.7), size=(0.2, 0.4)), 0.6)]),
    "Nakasar_Fractal_Stonehead_Roar": ("Rugissement de Tête-de-pierre : onde de poussière.",
                                       [("Wave", S("#d0c0a0", "#605040", 40, (6.0, 10.0), (-5, 10), 0.8, 0.6,
                                                   life=(0.4, 0.7), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Peter_Bomb": ("Bombe de Black Peter : explosion orange.",
                                   [("Fire", S("#fff0a0", "#ff6010", 30, (2.0, 5.0), (-10, 90), 0.8, 0.5,
                                               life=(0.3, 0.6), size=(0.3, 0.6)), 0.3)]),
}


# --- modèles --------------------------------------------------------------------------------------------------------

def models():
    """Parents vanilla d'abord : pirates squelettes, sauriens et raptors du jeu ; Strohm et Weyandt en humanoïdes
    habillés de cosmétiques vanilla."""
    v = lambda comment, parent, scale, light=None: {k: val for k, val in (
        ("$Comment", comment), ("Parent", parent), ("MinScale", scale), ("MaxScale", scale),
        ("Light", light)) if val is not None}
    m = {
        GHOST: v("Fantôme pirate : le pirate squelette vanilla (Skeleton_Pirate_Striker), lueur cyan.",
                 "Skeleton_Pirate_Striker", 1.0, {"Color": "#7ef", "Radius": 2}),
        MARKSMAN: v("Tireur fantôme : le canonnier squelette vanilla, lueur cyan.", "Skeleton_Pirate_Gunner", 1.0,
                    {"Color": "#7ef", "Radius": 2}),
        SWINDLER: v("Escroc fantôme : petit pirate squelette vanilla, lueur d'or (il vole les trésors).",
                    "Skeleton_Pirate_Striker", 0.85, {"Color": "#fd6", "Radius": 2}),
        PETER: v("Black Peter la Mèche : grand canonnier squelette vanilla (x 1,6), lueur de poudre.",
                 "Skeleton_Pirate_Gunner", 1.6, {"Color": "#f84", "Radius": 4}),
        JACK: v("Mad Jack Squall : grand capitaine squelette vanilla (x 1,4), lueur de givre.",
                "Skeleton_Pirate_Captain", 1.4, {"Color": "#9cf", "Radius": 4}),
        CALIX: v("Le second Calix : grand pirate squelette vanilla (x 1,45), lueur verdâtre.",
                 "Skeleton_Pirate_Striker", 1.45, {"Color": "#9f9", "Radius": 4}),
        ARABELLA: v("Capitaine Arabella Crowe : très grand capitaine squelette vanilla (x 1,8), lueur rouge.",
                    "Skeleton_Pirate_Captain", 1.8, {"Color": "#f55", "Radius": 5}),
        BRISTLEBACK: v("Saurien hérissé vétéran : le crapaud-rhino vert vanilla.", "Toad_Rhino_Green", 1.15),
        BONEBREAKER: v("Saurien brise-os vétéran : le crocodile vanilla, plus grand.", "Crocodile", 1.25),
        SMOKESCALE: v("Saurien écaille-fumée vétéran : le crapaud-rhino de magma vanilla.", "Toad_Rhino_Magma", 1.1),
        RAPTOR: v("Raptor de poche : le raptor des cavernes vanilla, petit (x 0,6).", "Raptor_Cave", 0.6),
        STONEHEAD: v("Tête-de-pierre, champion des raptors : le rex des cavernes vanilla (x 1,25).", "Rex_Cave", 1.25),
    }
    m[STROHM] = fr.humanoid("Capitaine Strohm (provisoire) : marin humain en long manteau.", "05", "Face_Scar",
                            [("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png"),
                             ("Cosmetics/Pants/Pants_Straight.blockymodel",
                              "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png"),
                             ("Cosmetics/Shoes/Boots_Long.blockymodel",
                              "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png", "Faded_Leather", "Black")])
    m[WEYANDT] = fr.humanoid("Le mousse Weyandt (provisoire) : jeune marin au bandana.", "02", "Face_Sunken",
                             [("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
                              ("Cosmetics/Pants/Pants_Straight.blockymodel",
                               "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png")], scale=(0.85, 0.85))
    return m


# --- attaques et rôles ------------------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
R = fc.root


def absolute(parent, damage, knockback=None):
    doc = {"Parent": parent, "DamageCalculator": {"Type": "Absolute", "BaseDamage": {"Physical": damage},
                                                  "RandomPercentageModifier": 0.1}}
    if knockback is not None:
        doc["DamageEffects"] = {"Knockback": {"Force": knockback}}
    return {"Interactions": [doc]}


def bite_vars(anims, damage, sound=None):
    """Variables de Root_NPC_Attack_Melee (raptor, rex, crocodile vanilla) : animation de la morsure, dégâts."""
    effects = {"ItemPlayerAnimationsId": anims, "ItemAnimationId": "Bite"}
    if sound:
        effects["WorldSoundEventId"] = sound
    return {"Melee_Start": {"Interactions": [{"Parent": "NPC_Attack_Melee_Simple", "Effects": effects, "RunTime": 0.333}]},
            "Melee_Damage": absolute("NPC_Attack_Melee_Damage", damage)}


def toad_vars(prefix, tongue, headbutt):
    """Variables de Root_NPC_Toad_Rhino(_Magma)_Attack : langue et coup de tête vanilla, dégâts."""
    return {"Tongue_Damage": absolute(f"{prefix}_Tongue_Damage", tongue, 1),
            "Headbutt_Damage": absolute(f"{prefix}_Headbutt_Damage", headbutt, -6)}


def cutlass_vars(damage):
    """Variable de Root_NPC_Skeleton_Pirate_Captain_Attack (trois coups de coutelas vanilla) : dégâts."""
    return {"Melee_Damage": absolute("NPC_Attack_Melee_Damage", damage)}


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Bonebreaker_Sweep"] = {
        "$Comment": "Saurien brise-os : coup de queue, cône de 120° sur 4 blocs (1,6 s), 26 dégâts et recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.6, Angle=120, Radius=4, Damage=26, Knockback=6, KnockUp=2,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Smokescale_Vent"] = {
        "$Comment": "Saurien écaille-fumée : fumerolle sous sa cible, cercle rouge de 2,5 blocs (1,8 s), 20 dégâts.",
        "Type": "Serial", "Interactions": [T("Circle", 1.8, Anchor="Target", Radius=2.5, Damage=20, PlayersOnly=True,
                                             ImpactParticle="Nakasar_Fractal_Peter_Bomb"), fc.windup(1.8)]}
    out["Nakasar_Fractal_Stonehead_Charge"] = {
        "$Comment": "Tête-de-pierre : baisse la tête puis charge, ligne rouge de 14 x 3 blocs (1,6 s), 34 dégâts et "
                    "projection ; contre une falaise ou un rocher, il reste étourdi 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, {"Type": "Nakasar_Fractal_Charge", "Length": 14, "Width": 3,
                                                     "Seconds": 1.6, "Speed": 15, "Damage": 34, "Knockback": 8,
                                                     "StunSeconds": 4.0, "StunEffect": "Nakasar_Fractal_Stunned",
                                                     "ImpactSound": "SFX_Goblin_Feastmaster_Slam"},
                                           fc.windup(1.6, "SFX_Rex_Bite")]}
    out["Nakasar_Fractal_Stonehead_Stomp"] = {
        "$Comment": "Tête-de-pierre : piétinement, cercle rouge de 5 blocs autour de lui (2 s), 30 dégâts et recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 2.0, Radius=5, Damage=30, Knockback=7, KnockUp=3,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(2.0)]}
    out["Nakasar_Fractal_Peter_Bomb"] = {
        "$Comment": "Black Peter : bombe lancée sous sa cible, cercle rouge de 3 blocs (1,8 s), 30 dégâts et recul.",
        "Type": "Serial", "Interactions": [T("Circle", 1.8, Anchor="Target", Radius=3, Damage=30, Knockback=5, KnockUp=3,
                                             PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Peter_Bomb",
                                             ImpactSound="SFX_Weapon_Goblin_Cannon_Fire"),
                                           fc.windup(1.8, "SFX_Bomb_Fuse")]}
    out["Nakasar_Fractal_Jack_Chill"] = {
        "$Comment": "Mad Jack Squall : souffle glacial, cône de 90° sur 7 blocs (2 s), 22 dégâts et Glacé 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.0, Angle=90, Radius=7, Damage=22,
                                                     EffectId="Nakasar_Fractal_Chilled", EffectDuration=4,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Ice_Burst"),
                                           fc.windup(2.0)]}
    out["Nakasar_Fractal_Jack_Daze"] = {
        "$Comment": "Mad Jack Squall : coup de crosse sous sa cible, cercle rouge de 3 blocs (1,6 s), 18 dégâts et "
                    "Hébété 2 s.",
        "Type": "Serial", "Interactions": [T("Circle", 1.6, Anchor="Target", Radius=3, Damage=18,
                                             EffectId="Nakasar_Fractal_Dazed", EffectDuration=2, PlayersOnly=True,
                                             ImpactParticle="Stick_Slam_Ground_Large"), fc.windup(1.6)]}
    out["Nakasar_Fractal_Calix_Confetti"] = {
        "$Comment": "Le second Calix : confettis du cadavre, cône de 70° sur 8 blocs (2 s), 18 dégâts, projette haut "
                    "et loin.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.0, Angle=70, Radius=8, Damage=18, Knockback=10, KnockUp=9,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Ghost_Rise"),
                                           fc.windup(2.0)]}
    out["Nakasar_Fractal_Arabella_Bludgeon"] = {
        "$Comment": "Arabella Crowe : gourdin sanglant, cône de 100° sur 6 blocs (2 s), 34 dégâts et Hébété 2 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.0, Angle=100, Radius=6, Damage=34,
                                                     EffectId="Nakasar_Fractal_Dazed", EffectDuration=2,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(2.0)]}
    return out


MELEE = ["Bonebreaker_Sweep", "Stonehead_Charge", "Stonehead_Stomp", "Jack_Chill", "Calix_Confetti", "Arabella_Bludgeon"]
RANGED = ["Smokescale_Vent", "Peter_Bomb", "Jack_Daze"]
TOAD_ATTACK = "Root_NPC_Toad_Rhino_Attack"
MAGMA_ATTACK = "Root_NPC_Toad_Rhino_Magma_Attack"
BITE_ATTACK = "Root_NPC_Attack_Melee"
CUTLASS_ATTACK = "Root_NPC_Skeleton_Pirate_Captain_Attack"
GUN_ATTACK = "Skeleton_Pirate_Gunner_Gun_Shoot"


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[BRISTLEBACK] = fr.role(
        BRISTLEBACK, "Saurien hérissé vétéran : langue et coup de tête du crapaud-rhino vanilla.", BRISTLEBACK,
        n(BRISTLEBACK), 420, [fr.melee(TOAD_ATTACK, 5.5, (0.8, 1.2)), fr.chase(30, stop=3.0)], fr.walk(3.4), GENERATOR,
        sight=18, leash=30, KnockbackScale=0.5, DeathAnimationTime=1.0,
        InteractionVars=toad_vars("Toad_Rhino", 14, 24))
    out[SMOKESCALE] = fr.role(
        SMOKESCALE, "Saurien écaille-fumée vétéran : langue et coup de tête du crapaud-rhino de magma vanilla, "
        "fumerolles annoncées.", SMOKESCALE, n(SMOKESCALE), 380,
        [fr.cast("Vent", R("Smokescale_Vent"), 18, "Fumerolle."), fr.melee(MAGMA_ATTACK, 6, (0.8, 1.2)),
         fr.chase(30, stop=3.0)], fr.walk(3.2), GENERATOR, sight=18, leash=30,
        timers=[fr.timer("Vent", (2, 4), (7, 9))], KnockbackScale=0.5, DeathAnimationTime=1.0,
        InteractionVars=toad_vars("Toad_Rhino_Magma", 12, 22))
    out[BONEBREAKER] = fr.role(
        BONEBREAKER, "Saurien brise-os vétéran : morsure du crocodile vanilla, coup de queue annoncé.", BONEBREAKER,
        n(BONEBREAKER), 600,
        [fr.timed_attack("Sweep", R("Bonebreaker_Sweep"), rng=4, los=True, comment="Coup de queue."),
         fr.melee(BITE_ATTACK, 3.0, (0.8, 1.2)), fr.chase(30, stop=2.0)], fr.walk(3.0), GENERATOR, sight=18, leash=30,
        timers=[fr.timer("Sweep", (3, 5), (8, 10))], KnockbackScale=0.2, DeathAnimationTime=1.2,
        InteractionVars=bite_vars("Crocodile_Default", 30))
    out[RAPTOR] = fr.role(
        RAPTOR, "Raptor de poche : petit raptor rapide, morsure du raptor vanilla.", RAPTOR, n(RAPTOR), 90,
        [fr.melee(BITE_ATTACK, 2.0, (0.6, 1.0)), fr.chase(36, stop=1.2)], fr.walk(5.4), GENERATOR, sight=24, leash=40,
        home=False, KnockbackScale=1.0, DeathAnimationTime=0.6, InteractionVars=bite_vars("Raptor_Cave_Default", 9))
    out[STONEHEAD] = fr.role(
        STONEHEAD, "Tête-de-pierre, champion des raptors, barre de boss : morsure du rex vanilla, charge (étourdi contre "
        "un mur), piétinement. Meutes à 75 et 50 %, fuite à 25 % : Java (sirensreef.Stonehead).", STONEHEAD,
        n(STONEHEAD), 4000,
        [fr.timed_attack("Charge", R("Stonehead_Charge"), rng=16, los=True, comment="Charge."),
         fr.timed_attack("Stomp", R("Stonehead_Stomp"), rng=4.5, comment="Piétinement."),
         fr.melee(BITE_ATTACK, 3.6, (0.9, 1.3)), fr.chase(36, stop=2.6)], fr.walk(3.6), GENERATOR, sight=20, leash=40,
        home=False, timers=[fr.timer("Charge", (3, 5), (9, 12)), fr.timer("Stomp", (5, 7), (8, 11))],
        KnockbackScale=0.0, DeathAnimationTime=2.0, InteractionVars=bite_vars("Hyena_Default", 36, "SFX_Rex_Bite"))
    out[GHOST] = fr.role(
        GHOST, "Fantôme pirate : trois coups de coutelas du pirate squelette vanilla.", GHOST, n(GHOST), 170,
        [fr.melee(CUTLASS_ATTACK, 2.8, (0.7, 1.1)), fr.chase(30, stop=1.6)], fr.walk(3.8), GENERATOR, sight=24,
        leash=40, home=False, HotbarItems=["Weapon_Sword_Cutlass"], KnockbackScale=0.8, DeathAnimationTime=1.0,
        InteractionVars=cutlass_vars(12))
    out[SWINDLER] = fr.role(
        SWINDLER, "Escroc fantôme : coutelas ; près d'un trésor maudit au sol, il le rapporte à sa cachette (Java).",
        SWINDLER, n(SWINDLER), 130,
        [fr.melee(CUTLASS_ATTACK, 2.6, (0.7, 1.1)), fr.chase(30, stop=1.6)], fr.walk(4.4), GENERATOR, sight=24,
        leash=40, home=False, HotbarItems=["Weapon_Sword_Cutlass"], KnockbackScale=1.0, DeathAnimationTime=1.0,
        InteractionVars=cutlass_vars(9))
    out[MARKSMAN] = fr.role(
        MARKSMAN, "Tireur fantôme : tromblon du canonnier squelette vanilla, garde ses distances.", MARKSMAN,
        n(MARKSMAN), 150,
        [fr.cast("Shoot", GUN_ATTACK, 18, "Tir de tromblon."), fr.keep_distance(30, 8, 14)], fr.walk(3.2), GENERATOR,
        sight=26, leash=40, home=False, timers=[fr.timer("Shoot", (1, 2), (3, 4))],
        HotbarItems=["Weapon_Gun_Blunderbuss"], KnockbackScale=0.8, DeathAnimationTime=1.0)
    out[PETER] = fr.role(
        PETER, "Black Peter la Mèche, barre de boss et de défiance : tromblon vanilla, bombes annoncées. Mines sous les "
        "joueurs, mines semées, poudre noire, fantômes et cyclone de cendres : Java (sirensreef.BlackPeter).", PETER,
        n(PETER), 6000,
        [fr.timed_attack("Bomb", R("Peter_Bomb"), rng=20, comment="Bombe lancée."),
         fr.cast("Shoot", GUN_ATTACK, 16, "Tir de tromblon."), fr.chase(40, stop=6.0)], fr.walk(3.0), GENERATOR,
        sight=30, leash=50, home=False, timers=[fr.timer("Bomb", (2, 4), (6, 8)), fr.timer("Shoot", (3, 5), (5, 7))],
        HotbarItems=["Weapon_Gun_Blunderbuss"], KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[JACK] = fr.role(
        JACK, "Mad Jack Squall, barre de boss : coutelas vanilla, souffle glacial, coup qui hébète. Fantômes et courants "
        "fantômes : Java (sirensreef.ReefShip).", JACK, n(JACK), 5000,
        [fr.timed_attack("Chill", R("Jack_Chill"), rng=6, los=True, comment="Souffle glacial."),
         fr.timed_attack("Daze", R("Jack_Daze"), rng=16, comment="Coup qui hébète."),
         fr.melee(CUTLASS_ATTACK, 3.4, (0.8, 1.2)), fr.chase(30, stop=2.4)], fr.walk(3.6), GENERATOR, sight=30,
        leash=40, home=False, timers=[fr.timer("Chill", (3, 5), (8, 10)), fr.timer("Daze", (5, 7), (10, 12))],
        HotbarItems=["Weapon_Sword_Cutlass"], KnockbackScale=0.0, DeathAnimationTime=2.0,
        InteractionVars=cutlass_vars(24))
    out[CALIX] = fr.role(
        CALIX, "Le second Calix, barre de boss : coutelas vanilla, confettis du cadavre. Lagon sinistre et courants "
        "fantômes : Java (sirensreef.ReefShip).", CALIX, n(CALIX), 5000,
        [fr.timed_attack("Confetti", R("Calix_Confetti"), rng=7, los=True, comment="Confettis du cadavre."),
         fr.melee(CUTLASS_ATTACK, 3.4, (0.8, 1.2)), fr.chase(30, stop=2.4)], fr.walk(3.6), GENERATOR, sight=30,
        leash=40, home=False, timers=[fr.timer("Confetti", (3, 5), (8, 10))], HotbarItems=["Weapon_Sword_Cutlass"],
        KnockbackScale=0.0, DeathAnimationTime=2.0, InteractionVars=cutlass_vars(24))
    out[ARABELLA] = fr.role(
        ARABELLA, "Capitaine Arabella Crowe, barre de boss : coutelas vanilla, gourdin sanglant. Lagon sinistre, dents "
        "des profondeurs, fantômes, sauts d'un bout à l'autre du pont et courants fantômes : Java "
        "(sirensreef.ReefShip).", ARABELLA, n(ARABELLA), 9000,
        [fr.timed_attack("Bludgeon", R("Arabella_Bludgeon"), rng=6, los=True, comment="Gourdin sanglant."),
         fr.melee(CUTLASS_ATTACK, 3.8, (0.8, 1.2)), fr.chase(30, stop=2.6)], fr.walk(3.6), GENERATOR, sight=30,
        leash=40, home=False, timers=[fr.timer("Bludgeon", (3, 5), (7, 9))], HotbarItems=["Weapon_Sword_Cutlass"],
        KnockbackScale=0.0, DeathAnimationTime=2.5, InteractionVars=cutlass_vars(30))
    out[STROHM] = fc.static_role(LANG, STROHM, "Capitaine Strohm : attend sur la plage du naufrage ; on ne peut pas le "
                                 "blesser (Java).", GENERATOR, 1000, attitude="Neutral", foe=False)
    out[WEYANDT] = fc.static_role(LANG, WEYANDT, "Le mousse Weyandt : reste près du capitaine ; on ne peut pas le "
                                  "blesser (Java).", GENERATOR, 1000, attitude="Neutral", foe=False)
    return out


# --- langue ---------------------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(TREASURE, "Trésor maudit", "Se ramasse accroupi et reste en main. Plus on le porte, plus la malédiction monte. "
           "Clic droit : le lancer à un autre joueur. À rapporter au coffre de la sirène.", "Cursed treasure",
           "Crouch to pick it up; it stays in hand. The longer you carry it, the worse the curse. Right click: throw it "
           "to another player. Bring it to the siren's chest.")
    t.item(SHOTS["Ripple"], "Boulet ricochet", "Clic droit au canon : trois impacts qui rebondissent dans l'axe du tir.",
           "Ripple shot", "Right click at the cannon: three impacts bouncing along the line of fire.")
    t.item(SHOTS["Scatter"], "Mitraille", "Clic droit au canon : gros dégâts et étourdissement dans un rayon de 4 blocs.",
           "Scatter shot", "Right click at the cannon: heavy damage and stun in a 4-block radius.")
    t.item(SHOTS["Ice"], "Boulet de glace", "Clic droit au canon : gèle les ennemis dans un rayon de 5 blocs.",
           "Ice shot", "Right click at the cannon: freezes foes in a 5-block radius.")
    t.item(CANNON, "Canon des ombres", "Utiliser : se poster au canon (ou le quitter). Les boulets brisent les mines et la "
           "défiance.", "Shadow cannon", "Use: man the cannon (or leave it). Its shots blow up mines and break "
           "defiance.")
    t.item(MINE, "Mine", "Elle saute quand on s'approche.", "Mine", "It blows up when you come close.")
    t.item(SIREN_CHEST, "Coffre de la sirène", "Rapportez-y les trésors maudits.", "Siren's chest",
           "Bring the cursed treasure here.")
    for role, f, e in ((STROHM, "Capitaine Strohm", "Captain Strohm"), (WEYANDT, "Le mousse Weyandt", "Cabin Boy Weyandt"),
                       (BRISTLEBACK, "Saurien hérissé vétéran", "Veteran Saurian Bristleback"),
                       (BONEBREAKER, "Saurien brise-os vétéran", "Veteran Saurian Bonebreaker"),
                       (SMOKESCALE, "Saurien écaille-fumée vétéran", "Veteran Saurian Smokescale"),
                       (RAPTOR, "Raptor de poche", "Pocket Raptor"),
                       (STONEHEAD, "Tête-de-pierre", "Stonehead"),
                       (GHOST, "Fantôme pirate", "Pirate Ghost"), (MARKSMAN, "Tireur fantôme", "Phantom Marksman"),
                       (SWINDLER, "Escroc fantôme", "Ghostly Swindler"),
                       (PETER, "Black Peter la Mèche", "Blasting Black Peter"),
                       (JACK, "Mad Jack Squall", "Mad Jack Squall"), (CALIX, "Le second Calix", "First Mate Calix"),
                       (ARABELLA, "Capitaine Arabella Crowe", "Captain Arabella Crowe")):
        t.npc(role, f, e)
    for eid, f, e in (("Dazed", "Hébété", "Dazed"), ("Chilled", "Glacé", "Chilled"),
                      ("Cursed_1", "Malédiction I", "Curse I"), ("Cursed_2", "Malédiction II", "Curse II"),
                      ("Cursed_3", "Malédiction III", "Curse III"),
                      ("Curse_Relief", "Allègement de la malédiction", "Curse Relief"),
                      ("Gunpowder", "Poudre noire", "Black Powder"), ("Cinders", "Cyclone de cendres", "Cinder Cyclone"),
                      ("Fetid_Fog", "Brouillard fétide", "Fetid Fog"), ("Piranhas", "Piranhas des profondeurs",
                                                                         "Piranhas of the Deep"),
                      ("Grim_Lagoon", "Lagon sinistre", "Grim Lagoon"), ("Frozen_Shot", "Gelé", "Frozen")):
        t.put(f"effects.Nakasar_Fractal_{eid}", f, e)
    msgs = {
        "intro": ("Capitaine Strohm : « Bienvenue au Récif de la Sirène. L'équipage d'Arabella Crowe hante encore l'île : "
                  "son trésor est maudit, et son navire nous attend dans la crique, au nord. »",
                  "Captain Strohm: \"Welcome to Siren's Reef. Arabella Crowe's crew still haunts the island: her treasure "
                  "is cursed, and her ship waits for us in the cove to the north.\""),
        "weyandt": ("Weyandt : « Des sauriens sur le rivage, et Tête-de-pierre dans la clairière... on passe par le ravin, "
                    "capitaine ? »", "Weyandt: \"Saurians on the shore, and Stonehead in the clearing... we go through "
                    "the ravine, captain?\""),
        "checkpoint": ("Point de retour atteint.", "Checkpoint reached."),
        "stonehead.enter": ("Tête-de-pierre gronde : la clairière est à lui.", "Stonehead growls: the clearing is his."),
        "stonehead.pack": ("Tête-de-pierre appelle sa meute !", "Stonehead calls his pack!"),
        "stonehead.flee": ("Tête-de-pierre rugit, brise les rochers et s'enfuit dans le ravin !",
                           "Stonehead roars, smashes the rocks and flees into the ravine!"),
        "stonehead.mine": ("Une mine saute sous Tête-de-pierre ! Le ravin est miné : prenez le canon des ombres sur la "
                           "corniche.", "A mine goes off under Stonehead! The ravine is mined: take the shadow cannon on "
                           "the ledge."),
        "stonehead.reset": ("Tête-de-pierre retourne à sa clairière.", "Stonehead returns to his clearing."),
        "cannon.manned": ("Vous êtes au canon : clic droit avec un boulet pour tirer là où vous regardez. Utilisez le "
                          "canon de nouveau, ou éloignez-vous, pour le quitter.",
                          "You man the cannon: right click with a shot to fire where you look. Use the cannon again, or "
                          "walk away, to leave it."),
        "cannon.left": ("Vous quittez le canon.", "You leave the cannon."),
        "cannon.busy": ("Quelqu'un est déjà à ce canon.", "Someone already mans this cannon."),
        "cannon.reload": ("Ce boulet se recharge.", "This shot is reloading."),
        "cannon.miss": ("Le boulet se perd au loin.", "The shot is lost in the distance."),
        "mine.cleared": ("Une mine saute sous le boulet.", "A mine blows up under the shot."),
        "wall2.open": ("La palissade vole en éclats : la route du fort est ouverte.",
                       "The palisade is blown apart: the way to the fort is open."),
        "fort.ghosts": ("Des fantômes se lèvent des ruines du fort !", "Ghosts rise from the ruins of the fort!"),
        "peter.enter": ("Black Peter la Mèche : « Qui vient piétiner mes mines ? Boum ! »",
                        "Blasting Black Peter: \"Who's tramplin' my mines? Boom!\""),
        "peter.mines": ("Black Peter sème des mines ! Ne le laissez pas les avaler.",
                        "Black Peter scatters mines! Don't let him swallow them."),
        "peter.powder": ("Black Peter avale une mine : poudre noire ! Brisez sa défiance au canon.",
                         "Black Peter swallows a mine: black powder! Break his defiance with the cannon."),
        "peter.broken": ("La défiance de Black Peter est brisée : la poudre se disperse.",
                         "Black Peter's defiance is broken: the powder scatters."),
        "peter.ghosts": ("Black Peter appelle l'équipage !", "Black Peter calls the crew!"),
        "peter.cinders": ("Cyclone de cendres : revenez dans le fort !", "Cinder Cyclone: get back into the fort!"),
        "peter.reset": ("Black Peter disparaît dans la fumée.", "Black Peter vanishes in the smoke."),
        "peter.victory": ("Black Peter s'éteint comme une mèche mouillée. La porte de la jungle s'ouvre.",
                          "Black Peter fizzles out like a wet fuse. The jungle gate opens."),
        "head.open": ("La grande tête de pierre ouvre la bouche : le labyrinthe des trésors maudits.",
                      "The great stone head opens its mouth: the maze of cursed treasure."),
        "treasure.intro": ("Trois trésors maudits dorment dans le labyrinthe. Rapportez-les au coffre de la sirène, près "
                           "de la sortie. La malédiction monte tant qu'on les porte : passez-les-vous !",
                           "Three cursed treasures sleep in the maze. Bring them to the siren's chest by the exit. The "
                           "curse grows while you carry them: pass them around!"),
        "treasure.crouch": ("Accroupissez-vous pour ramasser le trésor maudit.", "Crouch to pick up the cursed treasure."),
        "treasure.already": ("Vous portez déjà un trésor.", "You already carry a treasure."),
        "treasure.grab": ("La malédiction vous mord quand vous saisissez le trésor.",
                          "The curse bites as you grab the treasure."),
        "treasure.thrown": ("Trésor lancé : la malédiction s'allège.", "Treasure thrown: the curse eases."),
        "treasure.caught": ("{name} vous lance le trésor maudit !", "{name} throws you the cursed treasure!"),
        "treasure.cursed": ("La malédiction vous fige : le trésor vous échappe !",
                            "The curse locks you in place: the treasure slips away!"),
        "treasure.deposit": ("Trésor déposé ({count}/{total}).", "Treasure delivered ({count}/{total})."),
        "treasure.swindled": ("Un escroc fantôme rapporte le trésor à sa cachette !",
                              "A ghostly swindler carries the treasure back to its hiding place!"),
        "orb.touch": ("L'orbe spectrale éclate : des fantômes se lèvent !", "The spectral orb bursts: ghosts rise!"),
        "maze.open": ("Le dernier trésor est au coffre : la sortie du labyrinthe s'ouvre sur la crique.",
                      "The last treasure is in the chest: the maze exit opens onto the cove."),
        "cove.enter": ("Le Fierté du Kraken mouille dans la crique. Montez à bord par la passerelle.",
                       "The Kraken's Pride lies at anchor in the cove. Board it by the gangplank."),
        "ship.south": ("Le trésor d'Arabella est sur la plage sud, gardé par ses fantômes. Rapportez-le au coffre du pont !",
                       "Arabella's treasure lies on the south beach, guarded by her ghosts. Bring it to the deck's "
                       "chest!"),
        "ship.north": ("Un autre trésor brille sur la plage nord. Au coffre du pont !",
                       "Another treasure gleams on the north beach. To the deck's chest!"),
        "ship.jack": ("Mad Jack Squall : « Qui touche au butin de la capitaine ? Par-dessus bord ! »",
                      "Mad Jack Squall: \"Who touches the captain's loot? Overboard with ye!\""),
        "ship.calix": ("Le second Calix : « La capitaine n'aime pas les voleurs. Moi non plus. »",
                       "First Mate Calix: \"The captain doesn't like thieves. Neither do I.\""),
        "ship.defend": ("L'équipage fantôme monte à l'abordage par les deux plages ! Tenez le pont.",
                        "The ghost crew boards from both beaches! Hold the deck."),
        "ship.progress": ("Défense du navire : {count}/{total}.", "Ship defense: {count}/{total}."),
        "ship.arabella": ("Capitaine Arabella Crowe : « Mon trésor, mon navire, mon récif. Vous ne repartirez pas. »",
                          "Captain Arabella Crowe: \"My treasure, my ship, my reef. You're not leaving.\""),
        "ship.ghosts": ("L'équipage fantôme répond à l'appel !", "The ghost crew answers the call!"),
        "ship.drafts": ("Courants fantômes : quittez les bandes rouges ou vous passerez par-dessus bord !",
                        "Phantom drafts: get off the red strips or go overboard!"),
        "ship.fog": ("Brouillard fétide : remontez à bord !", "Fetid fog: get back aboard!"),
        "ship.water": ("Les piranhas des profondeurs vous dévorent : sortez de l'eau !",
                       "The piranhas of the deep devour you: get out of the water!"),
        "ship.lagoon": ("Lagon sinistre : sortez du cercle d'eau noire, et tirez-en les ennemis.",
                        "Grim Lagoon: get out of the black water and pull the foes out of it."),
        "ship.teeth": ("Dents des profondeurs : serrez-vous dans le cercle vert pour partager le coup !",
                       "Teeth from the Deep: stack in the green circle to share the hit!"),
        "ship.leap": ("Arabella bondit à l'autre bout du pont !", "Arabella leaps to the other end of the deck!"),
        "ship.reset": ("L'équipage fantôme se dissipe : le combat reprendra au retour.",
                       "The ghost crew fades away: the fight will resume when you return."),
        "ship.victory": ("Arabella Crowe s'effondre : le trésor du récif est à vous.",
                         "Arabella Crowe falls: the reef's treasure is yours."),
        "title.victory": ("Récif de la Sirène terminé", "Siren's Reef complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -----------------------------------------------------------------------------------------------------------

def ring(center, radius, count, stand_of, start=0.0):
    out = []
    for k in range(count):
        a = start + k * math.tau / count
        x, z = round(center[0] + math.cos(a) * radius), round(center[1] + math.sin(a) * radius)
        s = stand_of(x, z)
        if s is not None:
            out.append((x, s, z))
    return out


def java_layout(c):
    J, jd = fc, fc.jd
    t = c.t
    stand_of = lambda x, z: t.stand.get((x, z))
    camps = list(sc.CAMPS.values())
    camp_roles = "{" + ", ".join("{" + ", ".join(f'"{CAMP_ROLES[r]}"' for r in roles) + "}" for _, roles in camps) + "}"
    camp_spots = "{" + ", ".join(J.jpoints(ring(cc, 3, max(2, len(roles)), stand_of)) for cc, roles in camps) + "}"
    ravine = [(x, t.stand.get((round(x), round(z)), 2), z) for x, z, _, _ in sc.curve(sc.PATHS["ravine"], 2.0)]
    fort_ring = ring(sc.FORT_C, 12, 8, stand_of, 0.3)
    mine_ring = ring(sc.FORT_C, 8, 8, stand_of, 0.0)
    glade_spots = "{" + ", ".join(J.jpoints(ring(g, 3, 4, stand_of)) for g in sc.GLADES) + "}"
    clearing_spots = ring(sc.CLEARING, 9, 6, stand_of)
    south = [(x, s, z) for x, s, z in ring((sc.SOUTH_TREASURE[0] + 10, sc.SOUTH_TREASURE[2]), 6, 6, stand_of)]
    north = [(x, s, z) for x, s, z in ring((sc.NORTH_TREASURE[0] - 10, sc.NORTH_TREASURE[2]), 6, 6, stand_of)]
    south_board = (sc.GANGPLANKS[0][0], 1, sc.GANGPLANKS[0][1] + 2)
    north_board = (sc.GANGPLANKS[1][0], 1, sc.GANGPLANKS[1][1] - 2)
    maze_ghosts = [c.at(*t.maze.center(cell)) for cell in sorted(t.maze.degree)
                   if t.maze.degree[cell] >= 3 and cell not in (t.maze.entry,)][:4]
    deck_x0, deck_x1 = sc.SHIP_X[0] + 3, sc.SHIP_X[1] - 6
    x0, x1, z0, z1 = sc.MAZE
    cannon_where = {"ravine": 0, "fort": 1, "ship": 2}
    return f"""package dev.nakasar.hytale.fractals.sirensreef;

/**
 * Positions du Récif de la Sirène, écrites par tools/generate_sirens_reef.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SirensReefLayout {{

    public static final double[] SPAWN = {J.jpoint(sc.SPAWN)};
    public static final double[] STROHM = {J.jpoint(sc.STROHM_AT)};
    public static final double[] WEYANDT = {J.jpoint(sc.WEYANDT_AT)};
    /** Surface de l'eau (y monde du dessus de l'eau) : en dessous, on nage. */
    public static final double SEA_TOP = {jd(fc.GROUND_Y)};

    /** Camps de sauriens du rivage (rôles, apparitions). */
    public static final String[][] CAMP_ROLES = {camp_roles};
    public static final double[][][] CAMP_SPOTS = {camp_spots};
    public static final double[] RAPTOR_ROAM = {J.jpoint((sc.RAPTOR_ROAM[0], t.stand[sc.RAPTOR_ROAM], sc.RAPTOR_ROAM[1]))};

    /** Tête-de-pierre : sa clairière, ses meutes, la barrière qu'il brise et le ravin où il fuit. */
    public static final double[] STONEHEAD = {J.jpoint(sc.STONEHEAD_AT)};
    public static final double[] CLEARING = {J.jpoint((sc.CLEARING[0], t.stand[sc.CLEARING], sc.CLEARING[1]))};
    public static final double CLEARING_RADIUS = {jd(sc.CLEARING_RADIUS)};
    public static final double[][] CLEARING_SPOTS = {J.jpoints(clearing_spots)};
    public static final int[][] WALL1 = {J.jblocks(c.wall1)};
    public static final double[][] RAVINE = {J.jpoints(ravine, center=False)};
    /** Mines du ravin (bloc posé par le Java), palissade du bout (le canon l'abat). */
    public static final int[][] RAVINE_MINES = {J.jblocks(c.mines)};
    public static final int[][] WALL2 = {J.jblocks(c.wall2)};

    /** Canons des ombres (bloc), sens du tir (rotation : 0 sud, 1 est, 2 nord, 3 ouest) et lieu (0 ravin, 1 fort, 2 navire). */
    public static final int[][] CANNONS = {J.jblocks([at for at, _, _ in c.cannons])};
    /** Portée du tir (blocs), vérifiée à la génération : de la corniche, on touche les mines et la palissade. */
    public static final double CANNON_RANGE = {jd(sc.CANNON_RANGE)};
    public static final int[] CANNON_FACING = {{{", ".join(str(r) for _, r, _ in c.cannons)}}};
    public static final int[] CANNON_PLACE = {{{", ".join(str(cannon_where[w]) for _, _, w in c.cannons)}}};

    /** Le fort englouti de Black Peter. */
    public static final double[] FORT = {J.jpoint((sc.FORT_C[0], t.stand[sc.FORT_C], sc.FORT_C[1]))};
    public static final double FORT_RADIUS = {jd(sc.FORT_RADIUS + 2)};
    public static final double[] PETER = {J.jpoint(sc.PETER_AT)};
    public static final double[][] FORT_GHOSTS = {J.jpoints(fort_ring)};
    public static final double[][] FORT_MINES = {J.jpoints(mine_ring)};
    public static final int[][] FORT_GATE = {J.jblocks(c.fort_gate)};

    /** Sentier de jungle : meutes de raptors des deux clairières ; la bouche de la tête de pierre. */
    public static final double[][][] GLADE_SPOTS = {glade_spots};
    public static final double[] PLAZA = {J.jpoint((sc.PLAZA[0], t.stand[sc.PLAZA], sc.PLAZA[1]))};
    public static final int[][] MOUTH = {J.jblocks(c.teeth)};

    /** Le labyrinthe : trésors, coffre, orbes, fantômes, sortie ; boîte (x0, x1, z0, z1) et debout. */
    public static final double[][] TREASURES = {J.jpoints(c.treasures)};
    public static final double[] MAZE_CHEST = {J.jpoint(c.maze_chest)};
    public static final double[][] ORBS = {J.jpoints(c.orbs)};
    public static final double[][] MAZE_GHOSTS = {J.jpoints(maze_ghosts)};
    public static final int[][] MAZE_EXIT = {J.jblocks(c.maze_exit)};
    public static final int[] MAZE_BOX = {{{x0}, {x1}, {z0}, {z1}}};
    public static final double MAZE_STAND = {jd(fc.GROUND_Y + sc.MAZE_STAND)};

    /** La crique et le Fierté du Kraken. */
    public static final double[] COVE = {J.jpoint((sc.PATHS['exit'][-1][0], 1, sc.PATHS['exit'][-1][1]))};
    public static final double[] DECK = {J.jpoint(sc.DECK_C)};
    /** Le pont praticable : x0, x1, z0, z1 (blocs) et debout. */
    public static final int[] DECK_BOX = {{{deck_x0}, {deck_x1}, {sc.SHIP_Z - sc.SHIP_HALF + 1}, {sc.SHIP_Z + sc.SHIP_HALF - 1}}};
    public static final double DECK_STAND = {jd(fc.GROUND_Y + sc.DECK_STAND)};
    public static final double[] DECK_EAST = {J.jpoint((deck_x1 - 4, sc.DECK_STAND, sc.SHIP_Z))};
    public static final double[] DECK_WEST = {J.jpoint((deck_x0 + 4, sc.DECK_STAND, sc.SHIP_Z))};
    /** La crique : x0, x1, z0, z1 (blocs) ; les plages y sont comptées pour le brouillard et les piranhas. */
    public static final int[] COVE_BOX = {{-10, 70, -235, -165}};
    public static final double[] SOUTH_TREASURE = {J.jpoint(sc.SOUTH_TREASURE)};
    public static final double[] NORTH_TREASURE = {J.jpoint(sc.NORTH_TREASURE)};
    public static final double[][] SOUTH_GHOSTS = {J.jpoints(south)};
    public static final double[][] NORTH_GHOSTS = {J.jpoints(north)};
    public static final double[] SOUTH_BOARD = {J.jpoint(south_board)};
    public static final double[] NORTH_BOARD = {J.jpoint(north_board)};
    public static final int[] REWARD = {J.jblock(sc.REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(sc.END_EXIT_AT)};

    private SirensReefLayout() {{
    }}
}}
"""


# --- aperçus --------------------------------------------------------------------------------------------------------

def color_of(name):
    if name in (CANNON, MINE):
        return (200, 60, 255)
    if name == SIREN_CHEST:
        return (255, 210, 60)
    if "Coral" in name:
        return (240, 120, 150)
    if name.startswith("Soil_Sand") or name == "Soil_Gravel_Sand":
        return (232, 214, 160)
    if "Sandstone" in name:
        return (200, 170, 110)
    if name == "Soil_Clay_Ocean":
        return (90, 140, 150)
    if name.startswith("Wood_Darkwood") or name.startswith("Wood_Deadwood"):
        return (90, 60, 40)
    if name.startswith("Cloth"):
        return (40, 40, 44)
    c = fn.nature_color(name)
    if c:
        return c
    if "Palm" in name or "Jungle" in name:
        return (60, 150, 60)
    if name.startswith("Rock"):
        return (110, 118, 110)
    return (200, 200, 200)


def course_prefab():
    """Pour la carte du wiki (render_wiki_maps) : la carte et l'eau (en bleu), sans les fluides."""
    c = build_course()
    out = go.Prefab()
    out.blocks = dict(c.p.blocks)
    for (x, y, z) in c.p.fluids:
        if (x, y + 1, z) not in c.p.fluids and (x, y + 1, z) not in out.blocks:
            out.blocks[(x, y, z)] = ("Water_Source", 0)
    return out


def preview_images(c, folder):
    path = folder / "recif_dessus.png"
    p = go.Prefab()
    p.blocks = dict(c.p.blocks)
    for (x, y, z) in c.p.fluids:
        if (x, y + 1, z) not in c.p.fluids and (x, y + 1, z) not in p.blocks:
            p.blocks[(x, y, z)] = ("Water_Source", 0)
    fc.top_view(p, path, lambda n: (50, 120, 200) if n == "Water_Source" else color_of(n), scale=2)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    write_blocks()
    for item_id, doc in items().items():
        fc.write_json(fc.OBJECTS / f"{item_id}.json", doc)
    for name, doc in action_interactions().items():
        fc.write_json(go.INTERACTIONS / "SirensReef" / f"{name}.json", doc)
        if not name.startswith("Nakasar_Fractal_Use_"):
            fc.write_json(fc.ROOTS / f"Root_{name}.json", {"Interactions": [name], "RequireNewClick": True})
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    status_icons()
    fc.write_json(fc.SERVER / f"Entity/Damage/{REEF_CAUSE}.json", reef_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "SirensReef" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fc.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    course = build_course()
    p = course.p
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Plein soleil des tropiques : ciel bleu, brume claire et lointaine.
    counts = fc.write_instance(INSTANCE, "Récif de la Sirène", PREFAB_DIR, sections, sc.SPAWN, "#4aa060",
                               WEATHER, fc.weather("#3a86d8", "#a8d8f0", "#b8e0f0", (60, 220), 0.25, "#fff4d8",
                                                   sun="#fff8e0"), "12:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(course), encoding="utf-8")
    print(f"Récif de la Sirène : {sum(counts.values())} blocs et {len(p.fluids)} cases d'eau en {len(counts)} tronçons, "
          f"{len(roles())} rôles, {len(PARTICLE_SYSTEMS)} particules")
    if preview:
        preview_images(course, preview)


if __name__ == "__main__":
    main()
