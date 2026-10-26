#!/usr/bin/env python3
"""Génère Pierre-Profonde (Deepstone), fractale de la saison 2 (docs/fractales/gdd.md), d'après GW2
(metabattle.com/wiki/Guide:Deepstone et hardstuck.gg/gw2/guides/fractal-maps/deepstone) et la carte que Kevin a
envoyée (25 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_deepstone.py [--preview DOSSIER]

Torin et Kay cherchent l'entrée du caveau des nains de Deldrimor, au fond d'une montagne enneigée. Dans l'ordre :

1. la descente des corniches enneigées (chauves-souris), la salle du cristal ;
2. à l'ouest, la grille de runes (motifs lumineux qui glissent du nord vers le sud), deux runes à presser ensemble,
   puis la Sentinelle de Pierre-Profonde sur sa corniche ouverte au vide (spirale de vent, souffle, esprits du vent qui
   emportent les joueurs vers le bord : à briser) ; son orbe de lumière ramène au cristal ;
3. à l'est, les nids d'araignées, le pont balayé par le vent (deux runes l'arrêtent), deux mères de couvée puis la Reine
   de la couvée (estocades, toiles, charge ; invulnérable un instant à 50 %) ; son orbe aussi ;
4. les deux orbes au cristal : la Lumière de Deldrimor (objet, clic droit), puis le Minotaure des ombres, invulnérable
   tant que la Lumière ne le dévoile pas ;
5. la salle du gouffre : le chemin de dalles se révèle à la Lumière, d'orbe en orbe ; des flammes spectrales condamnent
   les dalles, des ombres rôdent ;
6. l'ascenseur : la plate-forme descend de 30 blocs, deux vagues d'ombres à mi-chemin ;
7. l'arène de dalles de la Voix (Torin consumé par les ombres) : orbe rebondissante qui brise les dalles, bombes
   d'ombre, siphon spirituel (défiance), ombres, flammes spectrales à 60 et 20 % ; la Lumière refait les dalles et donne
   des Courants ascendants (une chute sauvée par charge).

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_Deepstone`, les blocs (cristal,
orbes, rune de l'ascenseur), la Lumière de Deldrimor, effets, particules, modèles (parents vanilla), rôles, le temps
(ciel gris de montagne), la langue `nakasar_fractals_deepstone.lang` et `deepstone/DeepstoneLayout.java`. Repère :
y monde = GROUND_Y + y prefab, « debout à y » : le sol est en y - 1.
"""
import colorsys
import sys
from pathlib import Path

from PIL import Image

import deepstone_scenery as sc
import fractal_common as fc
import fractal_models as fm
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

LANG = "nakasar_fractals_deepstone"
GENERATOR = "generate_deepstone.py"
INSTANCE = "Nakasar_Fractal_Deepstone"
WEATHER = "Nakasar_Fractal_Weather_Deepstone"
PREFAB_DIR = "Deepstone"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/deepstone/DeepstoneLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/Deepstone"
CAUSE = "Nakasar_Fractal_Deepstone"

# --- blocs, objet, rôles -----------------------------------------------------------------------------------------
CRYSTAL = sc.CRYSTAL
PIT_ORB = sc.PIT_ORB
PIT_ORB_LIT = "Nakasar_Fractal_Deepstone_Pit_Orb_Lit"
LIGHT_ORB = "Nakasar_Fractal_Deepstone_Light_Orb"
LIFT_RUNE = sc.LIFT_RUNE
LIGHT = "Nakasar_Fractal_Light_Of_Deldrimor"
TORIN = "Nakasar_Fractal_Torin"
KAY = "Nakasar_Fractal_Kay"
BAT = "Nakasar_Fractal_Cave_Bat"                       # chauve-souris du Volcanique
SPIDERLING = "Nakasar_Fractal_Cave_Spiderling"         # araignée et mère de couvée du Ressac silencieux
BROOD_MOTHER = "Nakasar_Fractal_Brood_Mother"
SENTINEL = "Nakasar_Fractal_Deepstone_Sentinel"
WIND_SPRITE = "Nakasar_Fractal_Wind_Sprite"
NEST = "Nakasar_Fractal_Spider_Nest"
QUEEN = "Nakasar_Fractal_Brood_Queen"
IMP = "Nakasar_Fractal_Shadow_Imp"
MAULER = "Nakasar_Fractal_Shadow_Mauler"
BLOODSUCKER = "Nakasar_Fractal_Shadow_Bloodsucker"
MINOTAUR = "Nakasar_Fractal_Shadow_Minotaur"
SHADE = "Nakasar_Fractal_Deepstone_Shade"
FLAME = "Nakasar_Fractal_Spectral_Flame"
VOICE = "Nakasar_Fractal_The_Voice"
FOE_ROLES = [SENTINEL, WIND_SPRITE, NEST, QUEEN, IMP, MAULER, BLOODSUCKER, MINOTAUR, SHADE, FLAME, VOICE]
# Vent du pont (Java, deepstone.EastPath) : une bande en travers du pont ; tools/generate_warnings.JAVA_LINES.
WIND_LENGTH = 11
WIND_WIDTH = 5
# Lancer de l'ombre (Voix) : ligne de 12 x 2 (déjà dans JAVA_LINES, Source de Tempête de neige).

CRYSTAL_TEXTURE = "Blocks/Nakasar/Fractals/Deepstone_Crystal_Big.png"
CRYSTAL_DIM_TEXTURE = "Blocks/Nakasar/Fractals/Deepstone_Crystal_Dim.png"
LIGHT_ICON = f"{go.ICONS}/Light_Of_Deldrimor.png"


# --- textures : les cristaux de jade (eux-mêmes ceux du Néant vanilla) passés au bleu pâle des nains ----------------

def recolor(src, dst, hue, lift, saturation):
    img = Image.open(src).convert("RGBA")
    out = []
    for r, g, b, a in img.getdata():
        _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        r2, g2, b2 = colorsys.hsv_to_rgb(hue, min(1.0, s * saturation), min(1.0, v * lift))
        out.append((int(r2 * 255), int(g2 * 255), int(b2 * 255), a))
    img.putdata(out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst)


def textures():
    common = fc.COMMON
    jade = common / "Blocks/Nakasar/Fractals/Jade_Crystal_Big.png"
    recolor(jade, common / CRYSTAL_TEXTURE, 205 / 360, 1.35, 0.55)
    recolor(jade, common / CRYSTAL_DIM_TEXTURE, 220 / 360, 0.7, 0.35)
    for size, name in (("Large", "Deepstone_Crystal"), ("Medium", "Deepstone_Pit_Orb"), ("Small", "Deepstone_Light_Orb")):
        recolor(common / go.ICONS / f"Jade_Crystal_{size}.png", common / go.ICONS / f"{name}.png", 205 / 360, 1.35, 0.55)
    recolor(common / go.ICONS / "Jade_Crystal_Medium.png", common / go.ICONS / "Deepstone_Pit_Orb_Lit.png", 48 / 360,
            1.5, 0.6)
    recolor(common / go.ICONS / "Jade_Crystal_Small.png", common / LIGHT_ICON, 48 / 360, 1.6, 0.7)


# --- blocs ----------------------------------------------------------------------------------------------------------

CRYSTALS = {  # id : (modèle vanilla, texture, lumière, interaction, icône)
    CRYSTAL: ("Resources/Crystals/Crystal_Large_Pointy.blockymodel", CRYSTAL_TEXTURE, "#9cf",
              "Nakasar_Fractal_Use_Deepstone_Crystal", "Deepstone_Crystal"),
    PIT_ORB: ("Resources/Crystals/Crystal_Medium_Pointy.blockymodel", CRYSTAL_DIM_TEXTURE, None, None,
              "Deepstone_Pit_Orb"),
    PIT_ORB_LIT: ("Resources/Crystals/Crystal_Medium_Pointy.blockymodel", CRYSTAL_TEXTURE, "#fe9", None,
                  "Deepstone_Pit_Orb_Lit"),
    LIGHT_ORB: ("Resources/Crystals/Crystal_Small_Pointy.blockymodel", CRYSTAL_TEXTURE, "#fff",
                "Nakasar_Fractal_Use_Deepstone_Orb", "Deepstone_Light_Orb"),
}


def write_blocks():
    for name, (model, texture, light, use, icon) in CRYSTALS.items():
        doc = go.block_item(name, icon, light, use, solid=True, particle="#c0e0ff")
        doc["TranslationProperties"] = {"Name": f"{LANG}.items.{name}.name",
                                        "Description": f"{LANG}.items.{name}.description"}
        doc["Icon"] = f"{go.ICONS}/{icon}.png"
        block = doc["BlockType"]
        block.pop("Textures", None)
        block.update({"DrawType": "Model", "Opacity": "Transparent", "CustomModel": model,
                      "CustomModelTexture": [{"Texture": texture, "Weight": 1}], "RequiresAlphaBlending": True,
                      "BlockParticleSetId": "Crystal", "BlockSoundSetId": "Crystal"})
        fc.write_json(go.ITEMS / "Deepstone" / f"{name}.json", doc)
    # Médaillons des murs : la brique runique bleue vanilla, qui luit turquoise (salles sombres des captures de GW2).
    doc = go.block_item(sc.RUNE_GLOW, "Deepstone_Rune_Glow", "#3fc8b8", None, solid=True, particle="#3fc8b8")
    # icône à nous (l'icône vanilla Icons/ItemsGenerated/Rock_Runic_Blue_Brick.png n'existe pas : asset rejeté en jeu)
    icon = fc.COMMON / go.ICONS / "Deepstone_Rune_Glow.png"
    go.icon(icon, fc.texture(icon, (40, 52, 70), (80, 230, 210), "rune"))
    doc["TranslationProperties"] = {"Name": f"{LANG}.items.{sc.RUNE_GLOW}.name",
                                    "Description": f"{LANG}.items.{sc.RUNE_GLOW}.description"}
    doc["BlockType"]["Textures"] = [{"All": "BlockTextures/Rock_Runic_Blue_Brick.png", "Weight": 1}]
    fc.write_json(go.ITEMS / "Deepstone" / f"{sc.RUNE_GLOW}.json", doc)
    fc.write_block(LANG, LIFT_RUNE, "Deepstone_Lift_Rune", (40, 44, 60), (130, 210, 255), "rune", "#8cf",
                   "Nakasar_Fractal_Use_Deepstone_Lift_Rune")


def items():
    """La Lumière de Deldrimor : un petit cristal des nains qui luit d'or (modèle de cristal vanilla)."""
    return {LIGHT: {
        "TranslationProperties": {"Name": f"{LANG}.items.{LIGHT}.name", "Description": f"{LANG}.items.{LIGHT}.description"},
        "Icon": LIGHT_ICON,
        "IconProperties": {"Scale": 0.6, "Rotation": [4, 183, 1], "Translation": [-1, -14]},
        "Model": "Resources/Crystals/Crystal_Small_Pointy.blockymodel",
        "Texture": CRYSTAL_TEXTURE,
        "Scale": 0.6,
        "Light": {"Color": "#fe9", "Radius": 4},
        "Quality": "Legendary",
        "Categories": ["Items.Misc"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
        "Interactions": {"Secondary": "Root_Nakasar_Fractal_Deepstone_Light"},
        "Utility": {"Compatible": False},
    }}


def action_interactions():
    out = {"Nakasar_Fractal_Deepstone_Light": {
        "$Comment": "Lumière de Deldrimor : clic droit, éclat de lumière autour du joueur (recharge 5 s, Java "
                    "deepstone.DeepLight) : dévoile le Minotaure, les trésors cachés et le chemin du gouffre, allume les "
                    "orbes, protège et refait les dalles, donne un Courant ascendant dans l'arène de la Voix.",
        "Type": "Nakasar_Fractal_DeepstoneAction", "Action": "Light"}}
    for action, comment in (("Deepstone_Crystal", "Cristal de la salle centrale : y déposer l'orbe de lumière."),
                            ("Deepstone_Orb", "Orbe de lumière d'un boss vaincu : la prendre, retour au cristal."),
                            ("Deepstone_Lift_Rune", "Rune de l'ascenseur : rejoindre la plate-forme.")):
        out[f"Nakasar_Fractal_Use_{action}"] = fc.use_interaction(action, comment)
    return out


# --- effets ---------------------------------------------------------------------------------------------------------

def effects():
    L = LANG
    out = {
        "Nakasar_Fractal_Captured": fc.effect(
            L, "Nakasar_Fractal_Captured", "Emporté par un esprit du vent : on ne peut plus bouger ni agir (Java).",
            "Captured", 1.0, debuff=True, ApplicationEffects={"MovementEffects": {"DisableAll": True},
                                                              "EntityTopTint": "#e0f0ff"}),
        "Nakasar_Fractal_Shadow_Veil": fc.effect(
            L, "Nakasar_Fractal_Shadow_Veil", "Voile d'ombre : aucun dégât tant que la Lumière de Deldrimor ne l'a pas "
            "dissipé (Java).", "Shadow_Veil", 1.5, ApplicationEffects={"EntityTopTint": "#100820",
                                                                       "EntityBottomTint": "#000000"}),
        "Nakasar_Fractal_Light_Vulnerability": fc.effect(
            L, "Nakasar_Fractal_Light_Vulnerability", "Exposé à la Lumière : +25 % de dégâts subis et ralenti.",
            "Light_Vulnerability", 8.0, debuff=True,
            DamageResistance={k: [{"CalculationType": "Percent", "Amount": -0.25}]
                              for k in ("Physical", "Projectile", "Elemental")},
            ApplicationEffects={"HorizontalSpeedMultiplier": 0.8, "EntityTopTint": "#fff0a0"}),
        "Nakasar_Fractal_Shadow_Touch": fc.effect(
            L, "Nakasar_Fractal_Shadow_Touch", "Toucher des ombres (près du Minotaure voilé) : ralenti, la vie s'en va "
            "(Java).", "Shadow_Touch", 1.5, debuff=True,
            ApplicationEffects={"HorizontalSpeedMultiplier": 0.7, "EntityBottomTint": "#301040"}),
        "Nakasar_Fractal_Brood_Venom": fc.effect(
            L, "Nakasar_Fractal_Brood_Venom", "Venin de la couvée : la vie s'en va (Java).", "Brood_Venom", 5.0,
            debuff=True, ApplicationEffects={"EntityBottomTint": "#60a020"}),
        "Nakasar_Fractal_Brood_Protection": fc.effect(
            L, "Nakasar_Fractal_Brood_Protection", "Protection de la Reine (à 50 %) : dégâts subis réduits d'un tiers.",
            "Brood_Protection", 15.0,
            DamageResistance={k: [{"CalculationType": "Percent", "Amount": 0.33}]
                              for k in ("Physical", "Projectile", "Elemental")},
            ApplicationEffects={"EntityTopTint": "#c0e080"}),
        "Nakasar_Fractal_Siphoned": fc.effect(
            L, "Nakasar_Fractal_Siphoned", "Siphon spirituel de la Voix : la vie s'en va et la dalle s'effrite (Java).",
            "Siphoned", 1.5, debuff=True, ApplicationEffects={"EntityTopTint": "#c02040"}),
        "Nakasar_Fractal_Shadow_Bomb": fc.effect(
            L, "Nakasar_Fractal_Shadow_Bomb", "Bombe d'ombre : elle tombe à vos pieds dans un instant (Java).",
            "Shadow_Bomb", 2.0, debuff=True, ApplicationEffects={"EntityTopTint": "#6020a0"}),
    }
    for n in range(1, 5):
        out[f"Nakasar_Fractal_Updraft_{n}"] = fc.effect(
            L, f"Nakasar_Fractal_Updraft_{n}", f"Courant ascendant résiduel ({n}) : une chute dans l'arène de la Voix "
            "est rattrapée par charge (Java).", f"Updraft_{n}", 600.0)
    return out


def status_icons():
    icons = fc.COMMON / fc.STATUS_ICONS
    for name, color, glyph in (("Captured", (220, 240, 255), "minus"), ("Shadow_Veil", (90, 50, 140), "plus"),
                               ("Light_Vulnerability", (255, 230, 140), "minus"),
                               ("Shadow_Touch", (110, 60, 150), "minus"), ("Brood_Venom", (120, 190, 60), "minus"),
                               ("Brood_Protection", (190, 220, 120), "plus"), ("Siphoned", (210, 40, 70), "minus"),
                               ("Shadow_Bomb", (130, 60, 200), "minus")):
        fc.status_icon(icons / f"{name}.png", color, glyph)
    for n in range(1, 5):
        fc.status_icon(icons / f"Updraft_{n}.png", (150, 220, 255), "plus")


def deep_cause():
    return fc.cause("Grille de runes, vent, venin, ombres, siphon et bombes de Pierre-Profonde : une part des PV max, "
                    "l'armure ne la réduit pas.", "#9cf")


# --- particules -----------------------------------------------------------------------------------------------------

S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Deldrimor_Flash": ("Lumière de Deldrimor : éclat d'or et de blanc autour du joueur.",
                                        [("Burst", S("#ffffff", "#ffd860", 60, (3.0, 7.0), (-10, 60), 0.6, 0.6,
                                                     life=(0.4, 0.8), size=(0.2, 0.4)), 0.2),
                                         ("Glow", S("#fff8d0", "#ffc040", 20, (0.4, 1.0), (40, 90), 2.0, 0.6,
                                                    life=(0.8, 1.2), size=(0.3, 0.5)), 0.4)]),
    "Nakasar_Fractal_Deldrimor_Glow": ("Lueur dorée sur ce que la Lumière dévoile (Minotaure exposé, orbe allumée).",
                                       [("Glow", S("#fff8d0", "#ffc040", 8, (0.3, 0.8), (40, 90), 0.8, 1.6,
                                                   life=(0.6, 1.0), size=(0.1, 0.2)), 1.0)]),
    "Nakasar_Fractal_Treasure_Sparkle": ("Trésor caché des nains : un scintillement discret.",
                                         [("Sparkle", S("#ffffff", "#ffe080", 3, (0.2, 0.5), (60, 90), 0.4, 0.4,
                                                        life=(0.4, 0.7), size=(0.08, 0.14)), 0.3)]),
    "Nakasar_Fractal_Treasure_Burst": ("Trésor caché dévoilé : gerbe d'or.",
                                       [("Gold", S("#fff0a0", "#c08020", 40, (2.0, 5.0), (40, 90), 0.4, 0.4,
                                                   life=(0.6, 1.0), size=(0.12, 0.22)), 0.3)]),
    "Nakasar_Fractal_Rune_Glow": ("Rune pressée : lueur bleue.",
                                  [("Glow", S("#e0f8ff", "#40a0ff", 16, (0.6, 1.6), (60, 90), 0.6, 0.2,
                                              life=(0.6, 1.0), size=(0.15, 0.3)), 0.3)]),
    "Nakasar_Fractal_Wind_Gust": ("Rafale du pont : un souffle blanc qui balaie le travers.",
                                  [("Gust", S("#ffffff", "#c0e0ff", 40, (6.0, 10.0), (-5, 15), 2.5, 0.8,
                                              life=(0.4, 0.7), size=(0.2, 0.4)), 0.5)]),
    "Nakasar_Fractal_Sentinel_Burst": ("Spirale de la Sentinelle : éclat de vent.",
                                       [("Burst", S("#ffffff", "#a0d0ff", 30, (2.0, 5.0), (-5, 60), 1.0, 0.4,
                                                    life=(0.4, 0.7), size=(0.2, 0.35)), 0.3)]),
    "Nakasar_Fractal_Sprite_Whirl": ("Esprit du vent : tourbillon blanc autour de lui.",
                                     [("Whirl", S("#ffffff", "#b0d8ff", 16, (1.5, 3.0), (-5, 40), 1.0, 1.6,
                                                  life=(0.5, 0.8), size=(0.15, 0.3)), 0.6)]),
    "Nakasar_Fractal_Nest_Burst": ("Nid d'araignées détruit : éclats d'œufs et de soie.",
                                   [("Burst", S("#f0f0d8", "#a0a070", 30, (2.0, 4.0), (10, 90), 0.6, 0.4,
                                                life=(0.5, 0.9), size=(0.15, 0.3)), 0.3)]),
    "Nakasar_Fractal_Shadow_Aura": ("Voile du Minotaure : fumée noire de 4 blocs autour de lui (zone du toucher des "
                                    "ombres).",
                                    [("Smoke", S("#402060", "#000000", 30, (0.2, 0.6), (-5, 30), 4.0, 0.3,
                                                 life=(0.6, 1.0), size=(0.4, 0.7), blend="BlendLinear"), 0.6)]),
    "Nakasar_Fractal_Shadow_Rise": ("Une créature des ombres surgit.",
                                    [("Rise", S("#a080ff", "#100020", 30, (0.6, 1.6), (40, 90), 0.8, 1.6,
                                                life=(0.8, 1.2), size=(0.3, 0.5), blend="BlendLinear"), 0.3)]),
    "Nakasar_Fractal_Siphon_Beam": ("Siphon spirituel : un point du rayon rouge de la Voix (le Java en pose le long).",
                                    [("Beam", S("#ffffff", "#ff2040", 3, (0.0, 0.2), (-90, 90), 0.1, 0.1,
                                                life=(0.3, 0.5), size=(0.2, 0.3)), 0.0)]),
    "Nakasar_Fractal_Bomb_Mark": ("Bombe d'ombre accrochée à un joueur : volutes violettes qui montent.",
                                  [("Mark", S("#e0c0ff", "#6020a0", 10, (0.6, 1.2), (60, 90), 0.4, 0.2,
                                              life=(0.5, 0.8), size=(0.15, 0.25)), 0.5)]),
    "Nakasar_Fractal_Bomb_Blast": ("Explosion d'une bombe d'ombre.",
                                   [("Blast", S("#e0c0ff", "#300060", 50, (3.0, 7.0), (-10, 90), 1.2, 0.4,
                                                life=(0.5, 0.9), size=(0.3, 0.6)), 0.3)]),
    "Nakasar_Fractal_Voice_Orb": ("Orbe de la Voix en vol : sphère violette (le Java la déplace).",
                                  [("Core", S("#ffffff", "#a040ff", 6, (0.0, 0.2), (-90, 90), 0.3, 0.3,
                                              life=(0.3, 0.4), size=(0.5, 0.7)), 0.0)]),
    "Nakasar_Fractal_Tile_Crumble": ("Une dalle s'effondre dans le gouffre.",
                                     [("Dust", S("#c0c0d0", "#404050", 30, (0.5, 2.0), (-90, -20), 1.6, 0.2,
                                                 life=(0.8, 1.4), size=(0.2, 0.4), blend="BlendLinear"), 0.3)]),
    "Nakasar_Fractal_Flame_Absorb": ("Une flamme spectrale atteint la Voix : grande déflagration violette.",
                                     [("Wave", S("#ffffff", "#8040ff", 80, (8.0, 16.0), (-5, 15), 1.2, 0.4,
                                                 life=(0.6, 1.0), size=(0.3, 0.6)), 0.4)]),
    "Nakasar_Fractal_Lift_Dust": ("Plate-forme de l'ascenseur qui descend : poussière.",
                                  [("Dust", S("#d0c8c0", "#605850", 10, (0.3, 1.0), (-30, 30), 4.0, 0.2,
                                              life=(0.6, 1.0), size=(0.2, 0.4), blend="BlendLinear"), 0.4)]),
}


# --- modèles --------------------------------------------------------------------------------------------------------

def nest_parts():
    egg, silk = (226, 222, 196), (240, 240, 232)
    return [("Base", (0, 3, 0), (40, 6, 40), 0, fm.smooth(silk), "flat"),
            ("Egg_A", (-8, 14, -6), (18, 22, 18), 20, fm.smooth(egg), "flat"),
            ("Egg_B", (10, 12, 4), (16, 18, 16), -30, fm.smooth(egg), "flat"),
            ("Egg_C", (-2, 10, 12), (14, 14, 14), 45, fm.smooth(egg), "flat"),
            ("Silk", (0, 22, 0), (34, 4, 34), 10, fm.smooth(silk), "flat")]


def models():
    """Parents vanilla d'abord : esprits de givre et de braise, araignée des cavernes, loup-garou, aberrations,
    chauve-souris, spectre ; Torin, Kay et la Voix en humanoïdes habillés de cosmétiques vanilla."""
    v = lambda comment, parent, scale, light=None: {k: val for k, val in (
        ("$Comment", comment), ("Parent", parent), ("MinScale", scale), ("MaxScale", scale),
        ("Light", light)) if val is not None}
    shadow = {"Color": "#a6f", "Radius": 3}
    m = {
        SENTINEL: v("Sentinelle de Pierre-Profonde (élémentaire d'air de GW2) : grand esprit de givre vanilla (x 2,4), "
                    "lueur d'orage.", "Spirit_Frost", 2.4, {"Color": "#bdf", "Radius": 5}),
        WIND_SPRITE: v("Esprit du vent (tornade de la Sentinelle) : petit esprit de givre vanilla, lueur blanche.",
                       "Spirit_Frost", 0.9, {"Color": "#fff", "Radius": 3}),
        QUEEN: v("Reine de la couvée : très grande araignée des cavernes vanilla (x 2,8).", "Spider_Cave", 2.8,
                 {"Color": "#9f6", "Radius": 4}),
        IMP: v("Diablotin des ombres vétéran : petite aberration vanilla, lueur violette.", "Zombie_Aberrant_Small", 1.0,
               shadow),
        MAULER: v("Écharpeur des ombres : grande aberration vanilla, lueur violette.", "Zombie_Aberrant_Big", 1.1, shadow),
        BLOODSUCKER: v("Suceur de sang des ombres (élite de l'ascenseur) : grande chauve-souris vanilla (x 2,2).", "Bat",
                       2.2, {"Color": "#f46", "Radius": 3}),
        MINOTAUR: v("Esprit du Minotaure des ombres : loup-garou vanilla (x 1,5), lueur violette.", "Werewolf", 1.5,
                    {"Color": "#a6f", "Radius": 4}),
        SHADE: v("Ombre de Pierre-Profonde : le spectre vanilla, lueur violette.", "Wraith", 1.1, shadow),
        FLAME: v("Flamme spectrale : petit esprit de braise vanilla, lueur bleue.", "Spirit_Ember", 0.8,
                 {"Color": "#8af", "Radius": 4}),
    }
    m[NEST] = fc.character_model("Spider_Nest", nest_parts(), 93, "Nid d'araignées (PNJ fixe posé sur les œufs vanilla "
                                 "du Marais) : grappe d'œufs et de soie.", 0.6, (0.7, 1.0))
    coat = [("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Capes/Cape_Scavenger_NoNeck.blockymodel", "Cosmetics/Capes/Cape_Scavenger_Texture.png",
             gc.CLOTH, "Blue"),
            ("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png"),
            ("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
             "Faded_Leather", "Black")]
    m[TORIN] = fr.humanoid("Torin (provisoire) : explorateur emmitouflé, capuche et cape bleue.", "05", "Face_Scar", coat)
    m[KAY] = fr.humanoid("Kay (provisoire) : exploratrice en long manteau et bandana.", "11", "Face_Sunken",
                         [("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png"),
                          ("Cosmetics/Face_Accessories/Bandana.blockymodel", "Cosmetics/Face_Accessories/Bandana.png"),
                          coat[2], coat[3]])
    m[VOICE] = fr.humanoid("La Voix : Torin consumé par les ombres (x 1,5), robe de mage, lueur violette.", "16",
                           "Face_Scar", [coat[0], ("Cosmetics/Overtops/Robe_Wizard.blockymodel",
                                                   "Cosmetics/Overtops/Blazen_Wizard_Coat.png"), coat[1], coat[3]],
                           scale=(1.5, 1.5), light={"Color": "#a4f", "Radius": 5})
    return m


# --- attaques et rôles ----------------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
R = fc.root


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Sentinel_Gust"] = {
        "$Comment": "Sentinelle : souffle glacé devant elle, cône de 90° sur 9 blocs (2 s), 26 dégâts, Glacé 3 s, "
                    "agonie 2 s et recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.0, Angle=90, Radius=9, Damage=26, Knockback=6, KnockUp=2,
                                                     EffectId="Nakasar_Fractal_Chilled", EffectDuration=3,
                                                     AgonySeconds=2, PlayersOnly=True,
                                                     ImpactParticle="Nakasar_Fractal_Sentinel_Burst"),
                                           fc.windup(2.0)]}
    out["Nakasar_Fractal_Sentinel_Slam"] = {
        "$Comment": "Sentinelle : coup de vent autour d'elle, cercle rouge de 4 blocs (1,6 s), 28 dégâts et projection.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Radius=4, Damage=28, Knockback=5, KnockUp=5,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Sentinel_Burst"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Queen_Stab"] = {
        "$Comment": "Reine de la couvée : deux estocades devant elle, deux cônes de 60° sur 6 blocs (1,3 s puis 1 s), "
                    "22 dégâts et venin 5 s chacune.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.3, Angle=60, Radius=6, Damage=22,
                                                     EffectId="Nakasar_Fractal_Brood_Venom", EffectDuration=5,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.3),
                                           T("Cone", 1.0, Angle=60, Radius=6, Damage=22,
                                             EffectId="Nakasar_Fractal_Brood_Venom", EffectDuration=5,
                                             PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.0)]}
    out["Nakasar_Fractal_Queen_Web"] = {
        "$Comment": "Reine de la couvée : quatre toiles autour d'elle, cercles rouges de 2,5 blocs (1,6 s) entre 3 et 10 "
                    "blocs, 12 dégâts et Estropié 3 s.",
        "Type": "Serial", "Interactions": [T("Circle", 1.6, Anchor="Scatter", Count=4, OffsetMin=3, OffsetMax=10,
                                             Radius=2.5, Damage=12, EffectId="Nakasar_Fractal_Crippled",
                                             EffectDuration=3, PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Bounce"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Queen_Charge"] = {
        "$Comment": "Reine de la couvée : charge, ligne rouge de 14 x 3 blocs (1,6 s), 30 dégâts et projection.",
        "Type": "Serial", "Interactions": [CI, RF, {"Type": "Nakasar_Fractal_Charge", "Length": 14, "Width": 3,
                                                     "Seconds": 1.6, "Speed": 14, "Damage": 30, "Knockback": 7,
                                                     "ImpactSound": "SFX_Goblin_Feastmaster_Slam"},
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Imp_Claw"] = {
        "$Comment": "Diablotin des ombres : griffe (12 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Griffe.", None, None, 0.35, 12, end=2.4, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Mauler_Slam"] = {
        "$Comment": "Écharpeur des ombres : coup de poings devant lui, cône de 90° sur 5 blocs (1,6 s), 32 dégâts et "
                    "recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.6, Angle=90, Radius=5, Damage=32, Knockback=8, KnockUp=3,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Bloodsucker_Bite"] = {
        "$Comment": "Suceur de sang : morsure (18 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Morsure.", None, None, 0.35, 18, end=2.6, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Minotaur_Gore"] = {
        "$Comment": "Minotaure des ombres, au contact : deux coups de griffes (24 dégâts chacun), animation du loup-garou "
                    "vanilla.",
        "Type": "Serial", "Interactions": [fr.swing("Griffe gauche.", "Outlander_Brute_Default", "Grab", 0.35, 24, end=3.8,
                                                    sound="SFX_Unarmed_Swing"),
                                           fr.swing("Griffe droite.", "Outlander_Brute_Default", "Grab", 0.35, 24, end=3.8,
                                                    direction="ToRight", yaw=-50, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Minotaur_Sweep"] = {
        "$Comment": "Minotaure des ombres : coup de cornes, cône de 120° sur 6 blocs (1,6 s), 30 dégâts et projection.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.6, Angle=120, Radius=6, Damage=30, Knockback=8, KnockUp=4,
                                                     PlayersOnly=True, ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Minotaur_Leap"] = {
        "$Comment": "Minotaure des ombres : bond sur sa cible lointaine, cercle rouge de 4 blocs (1,5 s), 30 dégâts et "
                    "Hébété 2 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.5, Anchor="Farthest", OffsetMax=18, Radius=4, Damage=30,
                                                     TeleportCaster=True, EffectId="Nakasar_Fractal_Dazed",
                                                     EffectDuration=2, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.5)]}
    out["Nakasar_Fractal_Shade_Strike"] = {
        "$Comment": "Ombre : griffe d'ombre (14 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Griffe d'ombre.", None, None, 0.4, 14, end=2.6,
                                                     sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Shade_Burst"] = {
        "$Comment": "Ombre : onde autour d'elle, cercle rouge de 3,5 blocs (1,6 s), 14 dégâts et Hébété 2 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Radius=3.5, Damage=14,
                                                     EffectId="Nakasar_Fractal_Dazed", EffectDuration=2,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Shadow_Rise"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Voice_Strike"] = {
        "$Comment": "La Voix, au contact : coup d'ombre (26 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup d'ombre.", "Mace", "SwingLeft", 0.4, 26, end=3.6,
                                                    extend_bottom=1.6)]}
    out["Nakasar_Fractal_Voice_Cleave"] = {
        "$Comment": "La Voix : vague d'ombre devant elle, cône de 100° sur 7 blocs (1,8 s), 32 dégâts et agonie 3 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.8, Angle=100, Radius=7, Damage=32, AgonySeconds=3,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Shadow_Rise"),
                                           fc.windup(1.8, "SFX_Spear_Throw_Charge", "Mace", "SwingDownCharging")]}
    out["Nakasar_Fractal_Voice_Quake"] = {
        "$Comment": "La Voix : un petit cercle rouge de 2 blocs sous chaque joueur (1,4 s), 14 dégâts, renverse.",
        "Type": "Serial", "Interactions": [T("Circle", 1.4, Anchor="EachPlayer", Radius=2, Damage=14, KnockUp=5,
                                             PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Shadow_Rise"),
                                           fc.windup(1.4)]}
    return out


MELEE = ["Sentinel_Gust", "Sentinel_Slam", "Queen_Stab", "Queen_Charge", "Imp_Claw", "Mauler_Slam",
         "Bloodsucker_Bite", "Minotaur_Gore", "Minotaur_Sweep", "Minotaur_Leap", "Shade_Strike", "Shade_Burst",
         "Voice_Strike", "Voice_Cleave"]
RANGED = ["Queen_Web", "Voice_Quake"]


def hover_role(role_id, comment, hp):
    """PNJ immobile qui flotte (le Java le pose et le déplace) : Fly seul, sans MaintainDistance ni TakeOff."""
    doc = fc.static_role(LANG, role_id, comment, GENERATOR, hp)
    doc["MotionControllerList"] = fc.fly(0.1, 0, 2)
    return doc


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[SENTINEL] = fr.role(
        SENTINEL, "Sentinelle de Pierre-Profonde, barre de boss : souffle glacé, coup de vent. Spirale de vent et "
        "esprits du vent à 80, 50 et 20 % : Java (deepstone.Sentinel).", SENTINEL, n(SENTINEL), 7000,
        [fr.timed_attack("Gust", R("Sentinel_Gust"), rng=9, los=True, comment="Souffle glacé."),
         fr.timed_attack("Slam", R("Sentinel_Slam"), rng=4, comment="Coup de vent."),
         fr.chase(30, stop=3.0)], fr.walk(2.8), GENERATOR, sight=26, leash=36, home=False,
        timers=[fr.timer("Gust", (3, 5), (8, 10)), fr.timer("Slam", (2, 3), (5, 7))], KnockbackScale=0.0,
        DeathAnimationTime=2.0)
    out[WIND_SPRITE] = fc.static_role(LANG, WIND_SPRITE, "Esprit du vent : emporte les joueurs pris dans son cercle vers le "
                                      "bord de la corniche ; barre de défiance (Java, deepstone.Sentinel).", GENERATOR, 600)
    out[NEST] = fc.static_role(LANG, NEST, "Nid d'araignées : ne bouge pas, pond des araignées tant qu'on est près "
                               "(Java, deepstone.EastPath).", GENERATOR, 420)
    out[QUEEN] = fr.role(
        QUEEN, "Reine de la couvée, barre de boss : estocades (venin), toiles, charge. Invulnérable un instant à 50 % "
        "(protection), araignées et diablotins : Java (deepstone.EastPath).", QUEEN, n(QUEEN), 8000,
        [fr.timed_attack("Charge", R("Queen_Charge"), rng=16, los=True, comment="Charge."),
         fr.timed_attack("Web", R("Queen_Web"), rng=20, comment="Toiles."),
         fr.timed_attack("Stab", R("Queen_Stab"), rng=5.5, los=True, comment="Estocades."),
         fr.chase(36, stop=3.0)], fr.walk(3.2), GENERATOR, sight=30, leash=40, home=False,
        timers=[fr.timer("Charge", (6, 8), (12, 15)), fr.timer("Web", (3, 5), (9, 11)), fr.timer("Stab", (1, 2), (4, 6))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[IMP] = fr.role(IMP, "Diablotin des ombres vétéran : griffes.", IMP, n(IMP), 260,
                       [fr.melee(R("Imp_Claw"), 2.2, (0.6, 1.0)), fr.chase(36, stop=1.4)], fr.walk(4.4), GENERATOR,
                       sight=30, leash=40, home=False, KnockbackScale=0.8, DeathAnimationTime=0.8)
    out[MAULER] = fr.role(MAULER, "Écharpeur des ombres : coup de poings annoncé.", MAULER, n(MAULER), 1100,
                          [fr.timed_attack("Slam", R("Mauler_Slam"), rng=4.5, los=True, comment="Coup de poings."),
                           fr.chase(36, stop=2.4)], fr.walk(3.0), GENERATOR, sight=30, leash=40, home=False,
                          timers=[fr.timer("Slam", (1, 2), (4, 6))], KnockbackScale=0.1, DeathAnimationTime=1.5)
    out[BLOODSUCKER] = fr.role(
        BLOODSUCKER, "Suceur de sang des ombres (élite de l'ascenseur) : morsures en vol.", BLOODSUCKER, n(BLOODSUCKER),
        1400, [fr.melee(R("Bloodsucker_Bite"), 2.6, (0.6, 1.0)), fr.chase(30, speed=1.0, stop=1.4, pathfinder=False)],
        fc.fly(6, 1, 4), GENERATOR, sight=30, leash=40, home=False, KnockbackScale=0.3, DeathAnimationTime=1.0)
    out[MINOTAUR] = fr.role(
        MINOTAUR, "Esprit du Minotaure des ombres, barre de boss : griffes, coup de cornes, bond. Voile d'ombre (aucun "
        "dégât sans la Lumière de Deldrimor) et diablotins : Java (deepstone.Minotaur).", MINOTAUR, n(MINOTAUR), 9000,
        [fr.timed_attack("Leap", R("Minotaur_Leap"), rng=20, los=True, comment="Bond."),
         fr.timed_attack("Sweep", R("Minotaur_Sweep"), rng=5.5, los=True, comment="Coup de cornes."),
         fr.melee(R("Minotaur_Gore"), 3.4, (0.7, 1.1)), fr.chase(36, stop=2.6)], fr.walk(4.0), GENERATOR, sight=30,
        leash=40, home=False, timers=[fr.timer("Leap", (5, 7), (11, 14)), fr.timer("Sweep", (3, 5), (8, 10))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[SHADE] = fr.role(SHADE, "Ombre de Pierre-Profonde : griffes, onde qui hébète.", SHADE, n(SHADE), 420,
                         [fr.timed_attack("Burst", R("Shade_Burst"), rng=3.5, comment="Onde d'ombre."),
                          fr.melee(R("Shade_Strike"), 2.4, (0.7, 1.1)), fr.chase(36, stop=1.6)], fr.walk(3.6),
                         GENERATOR, sight=30, leash=40, home=False, timers=[fr.timer("Burst", (3, 5), (9, 12))],
                         KnockbackScale=0.6, DeathAnimationTime=1.0)
    out[FLAME] = hover_role(FLAME, "Flamme spectrale : flotte ; au gouffre elle condamne la dalle sous elle, dans l'arène "
                            "elle file vers la Voix (Java, deepstone.AbyssPit et deepstone.Voice).", 160)
    out[VOICE] = fr.role(
        VOICE, "La Voix (Torin consumé par les ombres), barre de boss et de défiance : coup d'ombre, vague d'ombre, "
        "secousses. Orbe rebondissante, bombes d'ombre, siphon spirituel, ombres, flammes spectrales et téléportations : "
        "Java (deepstone.Voice).", VOICE, n(VOICE), 16000,
        [fr.timed_attack("Cleave", R("Voice_Cleave"), rng=7, los=True, comment="Vague d'ombre."),
         fr.timed_attack("Quake", R("Voice_Quake"), rng=30, comment="Secousses."),
         fr.melee(R("Voice_Strike"), 3.6, (0.8, 1.2)), fr.chase(30, speed=0.6, stop=3.0)], fr.walk(2.0), GENERATOR,
        sight=40, leash=50, home=False, timers=[fr.timer("Cleave", (4, 6), (9, 12)), fr.timer("Quake", (6, 8), (12, 15))],
        KnockbackScale=0.0, DeathAnimationTime=2.5)
    out[TORIN] = fc.static_role(LANG, TORIN, "Torin : guide l'expédition ; on ne peut pas le blesser (Java).", GENERATOR,
                                1000, attitude="Neutral", foe=False)
    out[KAY] = fc.static_role(LANG, KAY, "Kay : accompagne Torin ; on ne peut pas la blesser (Java).", GENERATOR, 1000,
                              attitude="Neutral", foe=False)
    return out


# --- langue ---------------------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(LIGHT, "Lumière de Deldrimor", "Clic droit : un éclat de lumière autour de vous (recharge 5 s). Elle dévoile "
           "ce que cachent les ombres de Pierre-Profonde.", "Light of Deldrimor",
           "Right click: a burst of light around you (5 s recharge). It reveals what Deepstone's shadows hide.")
    t.item(CRYSTAL, "Cristal de Deldrimor", "Utiliser : y déposer une orbe de lumière.", "Deldrimor crystal",
           "Use: place an orb of light in it.")
    t.item(LIGHT_ORB, "Orbe de lumière", "Utiliser : la prendre et revenir au cristal.", "Orb of light",
           "Use: take it back to the crystal.")
    t.item(PIT_ORB, "Orbe éteinte", "La Lumière de Deldrimor l'allume.", "Unlit orb", "The Light of Deldrimor lights it.")
    t.item(PIT_ORB_LIT, "Orbe allumée", "Un point de retour au-dessus du gouffre.", "Lit orb",
           "A checkpoint above the abyss.")
    t.item(sc.RUNE_GLOW, "Rune de Deldrimor", "Une rune des nains qui luit encore.", "Deldrimor rune",
           "A dwarven rune that still glows.")
    t.item(LIFT_RUNE, "Rune de l'ascenseur", "Utiliser : rejoindre la plate-forme.", "Lift rune",
           "Use: join the platform.")
    for role, f, e in ((TORIN, "Torin", "Torin"), (KAY, "Kay", "Kay"),
                       (SENTINEL, "Sentinelle de Pierre-Profonde", "Deepstone Sentinel"),
                       (WIND_SPRITE, "Esprit du vent", "Wind Sprite"), (NEST, "Nid d'araignées", "Spider Nest"),
                       (QUEEN, "Reine de la couvée", "Champion Brood Queen"),
                       (IMP, "Diablotin des ombres vétéran", "Veteran Shadow Imp"),
                       (MAULER, "Écharpeur des ombres", "Shadow Mauler"),
                       (BLOODSUCKER, "Suceur de sang des ombres", "Shadow Bloodsucker"),
                       (MINOTAUR, "Esprit du Minotaure des ombres", "Champion Minotaur Spirit"),
                       (SHADE, "Ombre", "Shade"), (FLAME, "Flamme spectrale", "Spectral Flame"),
                       (VOICE, "La Voix", "The Voice")):
        t.npc(role, f, e)
    for eid, f, e in (("Captured", "Emporté", "Captured"), ("Shadow_Veil", "Voile d'ombre", "Shadow Veil"),
                      ("Light_Vulnerability", "Exposé à la Lumière", "Light Vulnerability"),
                      ("Shadow_Touch", "Toucher des ombres", "Shadow Touch"),
                      ("Brood_Venom", "Venin de la couvée", "Brood Venom"),
                      ("Brood_Protection", "Protection de la Reine", "Queen's Protection"),
                      ("Siphoned", "Siphon spirituel", "Spirit Siphon"), ("Shadow_Bomb", "Bombe d'ombre", "Shadow Bomb"),
                      ("Updraft_1", "Courant ascendant (1)", "Residual Updraft (1)"),
                      ("Updraft_2", "Courant ascendant (2)", "Residual Updraft (2)"),
                      ("Updraft_3", "Courant ascendant (3)", "Residual Updraft (3)"),
                      ("Updraft_4", "Courant ascendant (4)", "Residual Updraft (4)")):
        t.put(f"effects.Nakasar_Fractal_{eid}", f, e)
    msgs = {
        "intro": ("Torin : « Le caveau de Pierre-Profonde est au pied de cette montagne. Les nains de Deldrimor y ont "
                  "enfermé quelque chose... descendons. »",
                  "Torin: \"The Deepstone vault lies at the foot of this mountain. The dwarves of Deldrimor sealed "
                  "something inside... let's go down.\""),
        "kay": ("Kay : « Attention aux corniches. Et aux chauves-souris. »",
                "Kay: \"Mind the ledges. And the bats.\""),
        "checkpoint": ("Point de retour atteint.", "Checkpoint reached."),
        "hall.enter": ("Torin : « La salle du cristal. Le cristal réclame deux orbes de lumière : une à l'ouest, une à "
                       "l'est. »", "Torin: \"The crystal chamber. The crystal needs two orbs of light: one to the west, "
                       "one to the east.\""),
        "grid.intro": ("Une grille de runes : ne touchez pas les dalles rouges. Au bout, deux runes à presser ensemble.",
                       "A rune grid: don't touch the red tiles. At the end, two runes to press together."),
        "grid.hit": ("Les runes vous brûlent !", "The runes burn you!"),
        "rune.one": ("Une rune s'allume... il faut presser l'autre en même temps.",
                     "A rune lights up... the other must be pressed at the same time."),
        "grid.solved": ("Les deux runes s'allument : la grille s'éteint et la barrière s'ouvre.",
                        "Both runes light up: the grid goes dark and the barrier opens."),
        "sentinel.enter": ("La Sentinelle de Pierre-Profonde se dresse au bord du vide.",
                           "The Deepstone Sentinel rises at the edge of the void."),
        "sentinel.spiral": ("La Sentinelle déchaîne une spirale de vent : restez sous elle !",
                            "The Sentinel unleashes a wind spiral: stay under it!"),
        "sentinel.sprites": ("Des esprits du vent se lèvent : brisez-les avant qu'ils n'emportent quelqu'un dans le vide !",
                             "Wind sprites rise: break them before they carry someone into the void!"),
        "sprite.caught": ("Un esprit du vent vous emporte vers le bord !", "A wind sprite carries you to the edge!"),
        "sprite.broken": ("L'esprit du vent se dissipe.", "The wind sprite dissipates."),
        "sprite.thrown": ("L'esprit du vent vous jette dans le vide !", "The wind sprite hurls you into the void!"),
        "sentinel.reset": ("La Sentinelle se fond dans le vent.", "The Sentinel melts into the wind."),
        "sentinel.victory": ("La Sentinelle s'effondre : une orbe de lumière reste sur la corniche.",
                             "The Sentinel collapses: an orb of light remains on the ledge."),
        "nest.down": ("Le nid éclate.", "The nest bursts."),
        "bridge.intro": ("Le vent balaie le pont : quittez les bandes rouges. Deux runes au milieu l'arrêtent.",
                         "Wind sweeps the bridge: leave the red strips. Two runes in the middle stop it."),
        "bridge.blown": ("Le vent vous emporte !", "The wind carries you away!"),
        "bridge.fall": ("Vous revoilà au début du pont.", "Back to the start of the bridge."),
        "bridge.solved": ("Les deux runes s'allument : le vent tombe et la barrière du bout s'ouvre.",
                          "Both runes light up: the wind dies down and the barrier at the end opens."),
        "queen.mothers": ("Deux mères de couvée gardent l'antre de la Reine.", "Two brood mothers guard the Queen's den."),
        "queen.enter": ("La Reine de la couvée sort de l'ombre !", "The Brood Queen emerges from the dark!"),
        "queen.protect": ("La Reine se protège et appelle sa couvée !", "The Queen shields herself and calls her brood!"),
        "queen.reset": ("La couvée se retire dans l'ombre.", "The brood withdraws into the dark."),
        "queen.victory": ("La Reine de la couvée s'effondre : une orbe de lumière reste dans son antre.",
                          "The Brood Queen collapses: an orb of light remains in her den."),
        "orb.taken": ("{name} rapporte une orbe de lumière au cristal.", "{name} brings an orb of light to the crystal."),
        "orb.carry": ("Déposez l'orbe au cristal, derrière vous.", "Place the orb in the crystal, behind you."),
        "crystal.empty": ("Le cristal attend une orbe de lumière.", "The crystal awaits an orb of light."),
        "crystal.one": ("Le cristal s'éclaire à moitié. Il en faut une seconde.",
                        "The crystal half lights up. It needs a second one."),
        "crystal.full": ("Le cristal resplendit : la Lumière de Deldrimor est à vous ! Clic droit pour la libérer.",
                         "The crystal blazes: the Light of Deldrimor is yours! Right click to release it."),
        "light.cooldown": ("La Lumière de Deldrimor se recharge.", "The Light of Deldrimor is recharging."),
        "treasure.found": ("La Lumière révèle un trésor des nains !", "The Light reveals a dwarven treasure!"),
        "minotaur.enter": ("Un Minotaure des ombres surgit, voilé : seule la Lumière de Deldrimor le rend vulnérable.",
                           "A shadow Minotaur appears, veiled: only the Light of Deldrimor makes it vulnerable."),
        "minotaur.revealed": ("La Lumière dissipe le voile du Minotaure !", "The Light dispels the Minotaur's veil!"),
        "minotaur.imps": ("Le Minotaure appelle les ombres !", "The Minotaur calls the shadows!"),
        "minotaur.reset": ("Le Minotaure se fond dans les ombres.", "The Minotaur melts into the shadows."),
        "minotaur.victory": ("Le Minotaure se dissipe : la porte nord s'ouvre.",
                             "The Minotaur dissipates: the north door opens."),
        "pit.intro": ("La salle du gouffre : le chemin se dévoile à la Lumière de Deldrimor. Allumez les quatre orbes.",
                      "The abyss chamber: the path reveals itself to the Light of Deldrimor. Light the four orbs."),
        "pit.orb": ("Une orbe s'allume ({count}/{total}).", "An orb lights up ({count}/{total})."),
        "pit.dark": ("Le chemin se perd dans l'ombre : approchez-vous de la dernière dalle et libérez la Lumière.",
                     "The path fades into shadow: get close to the last tile and release the Light."),
        "pit.flame": ("Une flamme spectrale condamne une dalle : la Lumière la sauve.",
                      "A spectral flame dooms a tile: the Light saves it."),
        "pit.fall": ("Vous revoilà à la dernière orbe allumée.", "Back to the last lit orb."),
        "pit.done": ("Les quatre orbes brillent : le chemin de la sortie se dessine.",
                     "All four orbs shine: the way out appears."),
        "lift.intro": ("Tout le monde sur la plate-forme : elle descendra.", "Everyone on the platform: it will go down."),
        "lift.start": ("La plate-forme s'ébranle.", "The platform starts moving."),
        "lift.wave": ("Des ombres attaquent l'ascenseur !", "Shadows attack the lift!"),
        "lift.elite": ("Un suceur de sang mène la seconde vague !", "A bloodsucker leads the second wave!"),
        "lift.resume": ("La plate-forme reprend sa descente.", "The platform resumes its descent."),
        "lift.bottom": ("Le fond du caveau. Un couloir mène à l'arène.", "The bottom of the vault. A corridor leads to the "
                        "arena."),
        "lift.rune": ("La rune vous ramène sur la plate-forme.", "The rune takes you back to the platform."),
        "voice.enter": ("Torin : « Il... il me parle. » Les ombres consument Torin : la Voix !",
                        "Torin: \"It... it speaks to me.\" The shadows consume Torin: the Voice!"),
        "voice.updraft": ("Courant ascendant : une chute vous sera pardonnée ({count}).",
                          "Residual Updraft: a fall will be forgiven ({count})."),
        "voice.saved": ("Le courant ascendant vous remonte !", "The updraft lifts you back up!"),
        "voice.bomb": ("Une bombe d'ombre s'accroche à vous !", "A shadow bomb latches onto you!"),
        "voice.siphon": ("La Voix siphonne vos esprits : brisez sa défiance !",
                         "The Voice siphons your spirits: break its defiance!"),
        "voice.siphon.broken": ("Le siphon est brisé : la Voix vacille !", "The siphon is broken: the Voice staggers!"),
        "voice.shades": ("Des ombres rampent sur les dalles !", "Shades crawl over the tiles!"),
        "voice.split": ("La Voix se retire dans les ombres : détruisez les flammes spectrales avant qu'elles ne "
                        "l'atteignent !", "The Voice withdraws into the shadows: destroy the spectral flames before "
                        "they reach it!"),
        "voice.absorb": ("Une flamme atteint la Voix : déflagration !", "A flame reaches the Voice: blast!"),
        "voice.back": ("La Voix redevient vulnérable.", "The Voice is vulnerable again."),
        "voice.teleport": ("La Voix se déplace dans les ombres.", "The Voice shifts through the shadows."),
        "voice.reset": ("La Voix se tait... pour l'instant.", "The Voice falls silent... for now."),
        "voice.victory": ("La Voix se tait : Torin s'effondre, libéré. Le trésor de Pierre-Profonde est à vous.",
                          "The Voice falls silent: Torin collapses, freed. Deepstone's treasure is yours."),
        "title.victory": ("Pierre-Profonde terminée", "Deepstone complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -----------------------------------------------------------------------------------------------------------

def java_layout(p, t):
    J, jd = fc, fc.jd
    stand = lambda x, z: t.stand_at(x, z)
    at = lambda x, z: (x, stand(x, z), z)
    hall_imps = [at(x, z) for x, z in ((-10, -1), (10, -1), (-10, 11), (10, 11), (0, -2), (0, 12))]
    mothers = [at(sc.QUEEN_C[0] - 4, sc.QUEEN_C[1] - 3), at(sc.QUEEN_C[0] + 4, sc.QUEEN_C[1] + 3)]
    lift_c = ((sc.LIFT[0] + sc.LIFT[1]) / 2, (sc.LIFT[2] + sc.LIFT[3]) / 2)
    west_gate = sc.gate_cells(sc.WEST_GATE, 0, 6)
    east_gate = sc.gate_cells(sc.EAST_GATE, 0, 6)
    north_gate = sc.gate_cells(sc.NORTH_GATE, 0, 6)
    pit_orbs = [(*sc.tile_center(sc.PIT_X0, sc.PIT_Z0, sc.PIT_TILE, c, r),) for c, r in sc.PIT_ORBS]
    pit_orb_blocks = [(x, 0, z) for x, z in pit_orbs]
    ledge = ((sc.PIT_LEDGE[0] + sc.PIT_LEDGE[1]) / 2, 0, sc.PIT_LEDGE[2] + 0.5)
    exit_c = ((sc.PIT_EXIT[0] + sc.PIT_EXIT[1]) / 2, 0, (sc.PIT_EXIT[2] + sc.PIT_EXIT[3]) / 2)
    arena_c = (sc.ARENA_C[0], sc.VOICE_STAND, sc.ARENA_C[1])
    walkway_end = (0, sc.VOICE_STAND, sc.WALKWAY[2])
    tiles = lambda name, x0, z0, cols, rows, size: (
        f"    public static final int {name}_X0 = {x0};\n    public static final int {name}_Z0 = {z0};\n"
        f"    public static final int {name}_COLS = {cols};\n    public static final int {name}_ROWS = {rows};\n"
        f"    public static final int {name}_TILE = {size};\n")
    return f"""package dev.nakasar.hytale.fractals.deepstone;

/**
 * Positions de Pierre-Profonde, écrites par tools/generate_deepstone.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 * Boîtes {{x0, x1, z0, z1}} en blocs.
 */
public final class DeepstoneLayout {{

    public static final double[] SPAWN = {J.jpoint(sc.SPAWN)};
    public static final double[] TORIN = {J.jpoint(sc.TORIN_AT)};
    public static final double[] KAY = {J.jpoint(sc.KAY_AT)};
    public static final double[][] BATS = {J.jpoints(sc.BAT_SPOTS)};
    /** Sol des salles du caveau (y monde du dessus des dalles : on y est debout). */
    public static final double VAULT_Y = {jd(fc.GROUND_Y)};

    /** La salle du cristal. */
    public static final int[] HALL = {{{sc.HALL[0]}, {sc.HALL[1]}, {sc.HALL[2]}, {sc.HALL[3]}}};
    public static final double[] HALL_CENTER = {J.jpoint(sc.HALL_C)};
    public static final double[] TORIN_HALL = {J.jpoint(at(-4, 13))};
    public static final double[] KAY_HALL = {J.jpoint(at(4, 13))};
    public static final int[] CRYSTAL = {J.jblock(sc.CRYSTAL_AT)};
    public static final double[] RETURN = {J.jpoint(sc.RETURN_AT)};
    public static final double[] MINOTAUR = {J.jpoint(sc.MINOTAUR_AT)};
    public static final double[][] HALL_IMPS = {J.jpoints(hall_imps)};
    public static final int[][] NORTH_GATE = {J.jblocks(north_gate)};

    /** L'ouest : grille de runes (dalles de {sc.GRID_TILE} blocs, rangée 0 au nord), runes, barrière, corniche. */
{tiles("GRID", sc.GRID_X0, sc.GRID_Z0, sc.GRID_COLS, sc.GRID_ROWS, sc.GRID_TILE)}    public static final int FLOOR_Y = {fc.GROUND_Y - 1};
    public static final double[] GRID_START = {J.jpoint(sc.GRID_START, center=False)};
    public static final double[] GRID_END = {J.jpoint(((sc.GRID_END[0] + sc.GRID_END[1]) / 2, 0, (sc.GRID_END[2] + sc.GRID_END[3]) / 2))};
    public static final double[][] WEST_RUNES = {J.jpoints(sc.WEST_RUNES)};
    public static final int[][] WEST_GATE = {J.jblocks(west_gate)};
    public static final double[] SENTINEL = {J.jpoint((sc.SENTINEL_C[0], 0, sc.SENTINEL_C[1]))};
    public static final double SENTINEL_RADIUS = {jd(sc.SENTINEL_R)};
    /** Bord ouest de la corniche : au-delà (x plus petit), le vide. */
    public static final double SENTINEL_EDGE_X = {jd(sc.SENTINEL_EDGE_X)};
    public static final int[] WEST_ORB = {J.jblock(sc.WEST_ORB)};

    /** L'est : nids (œufs du Marais, bloc), pont, runes, barrière, antre de la Reine. */
    public static final int[] CORRIDOR_NEST = {J.jblock(sc.CORRIDOR_NEST)};
    public static final int[][] BRIDGE_NESTS = {J.jblocks(sc.BRIDGE_NESTS)};
    public static final int[][] QUEEN_NESTS = {J.jblocks(sc.QUEEN_NESTS)};
    public static final int[] BRIDGE = {{{sc.BRIDGE_X0}, {sc.BRIDGE_X1}, {sc.BRIDGE_Z0}, {sc.BRIDGE_Z1}}};
    /** Zone du vent et des chutes du pont (x0, x1, z0, z1), baies comprises. */
    public static final int[] BRIDGE_ZONE = {{{sc.BRIDGE_X0 - 2}, {sc.BRIDGE_X1 + 2}, {min(b[2] for b in sc.BRIDGE_BAYS) - 1}, {max(b[3] for b in sc.BRIDGE_BAYS) + 1}}};
    public static final double[] BRIDGE_START = {J.jpoint(sc.BRIDGE_START, center=False)};
    public static final double[][] EAST_RUNES = {J.jpoints(sc.EAST_RUNES)};
    public static final int[][] EAST_GATE = {J.jblocks(east_gate)};
    public static final double[] QUEEN = {J.jpoint((sc.QUEEN_C[0], 0, sc.QUEEN_C[1]))};
    public static final double QUEEN_RADIUS = {jd(sc.QUEEN_R)};
    public static final double[][] MOTHERS = {J.jpoints(mothers)};
    public static final int[] EAST_ORB = {J.jblock(sc.EAST_ORB)};
    /** Vent du pont : bande de {WIND_LENGTH} x {WIND_WIDTH} blocs en travers (Telegraphs.Strip, JAVA_LINES). */
    public static final double WIND_LENGTH = {jd(WIND_LENGTH)};
    public static final double WIND_WIDTH = {jd(WIND_WIDTH)};

    /** Trésors cachés (Lumière de Deldrimor). */
    public static final double[][] TREASURES = {J.jpoints(sc.TREASURES)};

    /** La salle du gouffre : dalles de {sc.PIT_TILE} blocs (colonne 0 à l'ouest, rangée 0 au nord), orbes (case). */
{tiles("PIT", sc.PIT_X0, sc.PIT_Z0, sc.PIT_COLS, sc.PIT_ROWS, sc.PIT_TILE)}    public static final int[][] PIT_ORB_TILES = {{{", ".join("{" + f"{c}, {r}" + "}" for c, r in sc.PIT_ORBS)}}};
    public static final int[][] PIT_ORBS = {J.jblocks(pit_orb_blocks)};
    public static final double[] PIT_LEDGE = {J.jpoint(ledge, center=False)};
    public static final double[] PIT_EXIT = {J.jpoint(exit_c, center=False)};
    /** La salle (avec ses paliers) : x0, x1, z0, z1. */
    public static final int[] PIT_ROOM = {{{sc.PIT_ROOM[0]}, {sc.PIT_ROOM[1]}, {sc.PIT_ROOM[2]}, {sc.PIT_ROOM[3]}}};

    /** L'ascenseur : plate-forme (x0, x1, z0, z1), debout en haut, à l'arrêt, en bas (y prefab + {fc.GROUND_Y}). */
    public static final int[] LIFT = {{{sc.LIFT[0]}, {sc.LIFT[1]}, {sc.LIFT[2]}, {sc.LIFT[3]}}};
    public static final int LIFT_TOP = {fc.GROUND_Y + sc.LIFT_TOP};
    public static final int LIFT_STOP = {fc.GROUND_Y + sc.LIFT_STOP};
    public static final int LIFT_BOTTOM = {fc.GROUND_Y + sc.LIFT_BOTTOM};
    public static final double[] LIFT_CENTER = {J.jpoint((lift_c[0], 0, lift_c[1]), center=False)};
    public static final int[] LIFT_RUNE = {J.jblock(sc.LIFT_RUNE_AT)};
    public static final double[] LIFT_LANDING = {J.jpoint(sc.LIFT_LANDING)};

    /** L'arène de la Voix : dalles de {sc.ARENA_TILE} blocs. */
{tiles("ARENA", sc.ARENA_X0, sc.ARENA_Z0, sc.ARENA_N, sc.ARENA_N, sc.ARENA_TILE)}    public static final int ARENA_FLOOR_Y = {fc.GROUND_Y + sc.VOICE_STAND - 1};
    public static final double[] ARENA = {J.jpoint(arena_c)};
    public static final double[] WALKWAY_END = {J.jpoint(walkway_end)};
    public static final int[] REWARD = {J.jblock(sc.REWARD_AT)};
    public static final int[] END_EXIT = {J.jblock(sc.END_EXIT_AT)};

    private DeepstoneLayout() {{
    }}
}}
"""


# --- aperçus --------------------------------------------------------------------------------------------------------

def color_of(name):
    if name in (CRYSTAL, PIT_ORB, LIGHT_ORB, PIT_ORB_LIT):
        return (180, 230, 255)
    if name in (sc.BARRIER, sc.RUNE_PLATE, LIFT_RUNE):
        return (200, 120, 255)
    if name == sc.SPIDER_EGGS or name.startswith("Deco_SpiderWeb"):
        return (240, 240, 220)
    if name.startswith("Soil_Snow") or name == sc.ICE:
        return (236, 242, 248)
    if "Runic" in name:
        return (60, 150, 170)
    if "Brick" in name:
        return (70, 72, 84)
    if "Crystal" in name:
        return (140, 200, 255)
    if name.startswith("Rock"):
        return (105, 108, 116)
    return (200, 200, 200)


def course_prefab():
    """Pour la carte du wiki (render_wiki_maps)."""
    p, _ = sc.build_all()
    return p


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    textures()
    write_blocks()
    for item_id, doc in items().items():
        fc.write_json(fc.OBJECTS / f"{item_id}.json", doc)
    for name, doc in action_interactions().items():
        fc.write_json(go.INTERACTIONS / "Deepstone" / f"{name}.json", doc)
        if not name.startswith("Nakasar_Fractal_Use_"):
            fc.write_json(fc.ROOTS / f"Root_{name}.json", {"Interactions": [name], "RequireNewClick": True})
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    status_icons()
    fc.write_json(fc.SERVER / f"Entity/Damage/{CAUSE}.json", deep_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "Deepstone" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fr.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p, t = sc.build_all()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Tout sous terre (Kevin, 26 octobre 2026) : ciel noir, brume bleu nuit qui noie le fond des cavernes, lumière
    # froide et faible ; ce sont les runes, lanternes et cristaux qui éclairent.
    counts = fc.write_instance(INSTANCE, "Pierre-Profonde", PREFAB_DIR, sections, sc.SPAWN, "#3a4a5e",
                               WEATHER, fc.weather("#020408", "#08101a", "#0a1220", (12, 120), 0.5, "#4a5e78",
                                                   sun="#9ab4d0"), "22:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(p, t), encoding="utf-8")
    print(f"Pierre-Profonde : {sum(counts.values())} blocs en {len(counts)} tronçons, {len(roles())} rôles, "
          f"{len(PARTICLE_SYSTEMS)} particules")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        fc.top_view(p, preview / "pierre_profonde_dessus.png", color_of, scale=2)


if __name__ == "__main__":
    main()
