#!/usr/bin/env python3
"""Génère le Pic de Sunqua (Sunqua Peak), fractale de la saison 2 (docs/fractales/gdd.md), d'après GW2
(metabattle.com/wiki/Guide:Sunqua_Peak et hardstuck.gg/gw2/guides/fractal-maps/sunqua-peak) et la carte que Kevin a
envoyée (26 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_sunqua_peak.py [--preview DOSSIER]

Ai, la gardienne du pic, a confié ses émotions aux esprits de la montagne. Dans l'ordre :

1. l'îlot du départ et l'Esprit de la montagne ; les orbes de foudre donnent le Bond chargé (sauts plus hauts) ;
   l'escalier brisé, trois élémentaires d'air ; le socle refait l'escalier ;
2. une colonne de vent vers le plateau de la Voix de la montagne (ondes d'orbes, décharge) ; à 66 et 33 % elle se
   retire dans une tornade : quatre nuages d'orage à disperser d'un bond chargé, sous une pluie de zones rouges ;
3. une seconde colonne vers la corniche des cascades : les cascades déferlent et jettent dans le vide, trois
   élémentaires d'eau effrayés à rassurer (accroupi près d'eux), des esprits de l'eau enragés (sol glissant) ; les
   rochers flottants, la chute dans la terrasse de la Tristesse de la montagne : rochers tombés à briser sous le
   Marché des marées (lien de l'orbe sombre, qui s'intercepte) ;
4. le sentier de lave : trois murs gardés par des élémentaires de lave (qui explosent et se divisent), des tigres ;
   la Fureur de la montagne : coups brûlants, bond, ruée ; météores et frappe extrême (se cacher derrière un
   météore), défiance ; météores qui suivent deux joueurs ;
5. l'arène du sommet : Ai, gardienne du pic. Air (ondes d'orbes et défiance, bombes, balayage), front d'orage ;
   feu (vagues de météores, frappe extrême), pluie de météores ; eau (Marché des marées, zone partagée). Au rang
   Maître, Ai s'assombrit encore (craintes qui suivent les joueurs).

Le générateur écrit les prefabs (tronçons de 64 blocs), l'instance `Nakasar_Fractal_SunquaPeak`, les blocs (feuillage
rose, orbe de foudre), effets, particules, modèles (parents vanilla), rôles, le temps (ciel clair du pic), la langue
`nakasar_fractals_sunqua_peak.lang` et `sunquapeak/SunquaPeakLayout.java`. Repère : y monde = GROUND_Y + y prefab,
« debout à y » : le sol est en y - 1.
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
import sunqua_peak_scenery as sc

LANG = "nakasar_fractals_sunqua_peak"
GENERATOR = "generate_sunqua_peak.py"
INSTANCE = "Nakasar_Fractal_SunquaPeak"
WEATHER = "Nakasar_Fractal_Weather_SunquaPeak"
PREFAB_DIR = "SunquaPeak"
JAVA_LAYOUT = go.MOD / "src/main/java/dev/nakasar/hytale/fractals/sunquapeak/SunquaPeakLayout.java"
PARTICLES = fc.SERVER / "Particles/Nakasar/Fractals/SunquaPeak"
CAUSE = "Nakasar_Fractal_Sunqua"

# --- blocs et rôles ------------------------------------------------------------------------------------------
BLOSSOM = sc.BLOSSOM
ORB = "Nakasar_Fractal_Sunqua_Lightning_Orb"
SPIRIT = "Nakasar_Fractal_Spirit_Of_The_Mountain"
AIR_ELEMENTAL = "Nakasar_Fractal_Sunqua_Air_Elemental"
VOICE = "Nakasar_Fractal_Voice_Of_The_Mountain"
WATER_SPRITE = "Nakasar_Fractal_Enraged_Water_Sprite"
FRIGHTENED = "Nakasar_Fractal_Frightened_Water_Elemental"
SORROW = "Nakasar_Fractal_Sorrow_Of_The_Mountain"
BOULDER = "Nakasar_Fractal_Fallen_Boulder"
LAVA_ELEMENTAL = "Nakasar_Fractal_Sunqua_Lava_Elemental"
LAVA_EMBER = "Nakasar_Fractal_Sunqua_Lava_Ember"
TIGER = "Nakasar_Fractal_Sunqua_Tiger"
FURY = "Nakasar_Fractal_Fury_Of_The_Mountain"
AI = "Nakasar_Fractal_Ai_Keeper_Of_The_Peak"
AI_DARK = "Nakasar_Fractal_Ai_Dark"
FEAR = "Nakasar_Fractal_Sunqua_Fear"
FOE_ROLES = [AIR_ELEMENTAL, VOICE, WATER_SPRITE, BOULDER, LAVA_ELEMENTAL, LAVA_EMBER, TIGER, FURY, AI, AI_DARK, FEAR]
# Lignes posées en Java : tools/generate_warnings.JAVA_LINES.
ORB_LINE_LENGTH = 2 * sc.SUMMIT_R      # ondes d'orbes d'Ai : bandes en travers de l'arène
ORB_LINE_WIDTH = 4

ORB_TEXTURE = "Resources/Crystals/Crystal_Big_Textures/Blue.png"   # cristal cyan vanilla


# --- blocs ---------------------------------------------------------------------------------------------------------

def write_blocks():
    """Feuillage rose : le modèle de feuilles vanilla (boule) et la texture vanilla inutilisée Rhododendron_Pink, avec
    les réglages des feuilles de chêne. Orbe de foudre : petit cristal cyan vanilla qu'on traverse (Java : on la
    ramasse en passant)."""
    leaves = {
        "TranslationProperties": {"Name": f"{LANG}.items.{BLOSSOM}.name",
                                  "Description": f"{LANG}.items.{BLOSSOM}.description"},
        "Categories": ["Blocks.Plants"],
        "Icon": "Icons/ItemsGenerated/Plant_Rhododendron_Pink_Leaves.png",
        "PlayerAnimationsId": "Item",
        "Interactions": {"Primary": "Block_Primary", "Secondary": "Block_Secondary"},
        "BlockType": {
            "DrawType": "Model",
            "CustomModel": "Blocks/Foliage/Leaves/Ball.blockymodel",
            "CustomModelTexture": [{"Texture": "Blocks/Foliage/Leaves/Ball_Textures/Rhododendron_Pink.png", "Weight": 1}],
            "Opacity": "Cutout",
            "Group": "Leaves",
            "Effect": ["Wind"],
            "Flags": {},
            "RandomRotation": "YawPitchRollStep1",
            "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
            "BlockParticleSetId": "Leaves",
            "ParticleColor": "#e070a8",
            "BlockSoundSetId": "Leaves",
            "PhysicalMaterialId": "Foliage",
            "IgnoreSupportWhenPlaced": True,
            "TextureComputedColor": "#a13858",
        },
        "Tags": {"Type": ["Plant"], "Family": ["Leaves"]},
        "ItemSoundSetId": "ISS_Items_Foliage",
    }
    fc.write_json(go.ITEMS / "SunquaPeak" / f"{BLOSSOM}.json", leaves)
    doc = go.block_item(ORB, ORB, "#8cf", None, solid=False, particle="#a0e0ff")
    doc["TranslationProperties"] = {"Name": f"{LANG}.items.{ORB}.name", "Description": f"{LANG}.items.{ORB}.description"}
    doc["Icon"] = "Icons/ItemsGenerated/Rock_Crystal_Cyan_Small.png"
    block = doc["BlockType"]
    block.pop("Textures", None)
    block.update({"DrawType": "Model", "Opacity": "Transparent",
                  "CustomModel": "Resources/Crystals/Crystal_Small.blockymodel",
                  "CustomModelTexture": [{"Texture": ORB_TEXTURE, "Weight": 1}], "RequiresAlphaBlending": True,
                  "BlockParticleSetId": "Crystal", "BlockSoundSetId": "Crystal",
                  "Particles": [{"SystemId": "Nakasar_Fractal_Lightning_Orb_Glow", "Scale": 1,
                                 "PositionOffset": {"Y": 0.4}}]})
    fc.write_json(go.ITEMS / "SunquaPeak" / f"{ORB}.json", doc)


# --- effets ---------------------------------------------------------------------------------------------------------

LEAP_STACKS = 3
TIDAL_STACKS = 10
TIDAL_SLOW = 0.04            # ralenti par charge du Marché des marées
TIDAL_MIGHT = 0.05           # dégâts infligés en plus par charge (Java, filtre de dégâts)


def effects():
    L = LANG
    out = {}
    for n in range(1, LEAP_STACKS + 1):
        out[f"Nakasar_Fractal_Charged_Leap_{n}"] = fc.effect(
            L, f"Nakasar_Fractal_Charged_Leap_{n}", f"Bond chargé ({n}) : sauts plus hauts, pas de dégâts de chute "
            "(Java, sunquapeak.ChargedLeap, force de saut du joueur).", f"Charged_Leap_{n}", 20.0)
    for n in range(1, TIDAL_STACKS + 1):
        out[f"Nakasar_Fractal_Tidal_Bargain_{n}"] = fc.effect(
            L, f"Nakasar_Fractal_Tidal_Bargain_{n}", f"Marché des marées ({n}) : {int(n * TIDAL_MIGHT * 100)} % de "
            f"dégâts infligés en plus (Java), {int(n * TIDAL_SLOW * 100)} % plus lent ; à {TIDAL_STACKS}, la marée "
            "vous submerge.", f"Tidal_Bargain_{n}", 12.0, debuff=True,
            ApplicationEffects={"HorizontalSpeedMultiplier": round(1 - n * TIDAL_SLOW, 2), "EntityTopTint": "#3080c0"})
    out["Nakasar_Fractal_Sunqua_Burning"] = fc.effect(
        L, "Nakasar_Fractal_Sunqua_Burning", "Brûlure de la montagne : la vie s'en va (Java).", "Sunqua_Burning", 5.0,
        debuff=True, ApplicationEffects={"EntityBottomTint": "#ff6a1a"})
    out["Nakasar_Fractal_Knocked_Down"] = fc.effect(
        L, "Nakasar_Fractal_Knocked_Down", "À terre : on ne peut plus bouger ni agir.", "Knocked_Down", 2.0,
        debuff=True, ApplicationEffects={"MovementEffects": {"DisableAll": True}, "EntityTopTint": "#c0a080"})
    out["Nakasar_Fractal_Storm_Marked"] = fc.effect(
        L, "Nakasar_Fractal_Storm_Marked", "Bombe d'Ai : un cercle vous suit ; il éclate à vos pieds (Java). Restez à "
        "l'écart des autres.", "Storm_Marked", 4.0, debuff=True, ApplicationEffects={"EntityTopTint": "#a0d0ff"})
    out["Nakasar_Fractal_Meteor_Marked"] = fc.effect(
        L, "Nakasar_Fractal_Meteor_Marked", "Un météore vous suit (Java). Croisez-le avec l'autre pour les briser.",
        "Meteor_Marked", 3.0, debuff=True, ApplicationEffects={"EntityTopTint": "#ff9040"})
    out["Nakasar_Fractal_Shared_Tide"] = fc.effect(
        L, "Nakasar_Fractal_Shared_Tide", "Marée partagée : un cercle sur vous ; ses dégâts se partagent entre ceux "
        "qui s'y tiennent (Java).", "Shared_Tide", 5.0, debuff=True, ApplicationEffects={"EntityTopTint": "#60e0a0"})
    return out


def status_icons():
    icons = fc.COMMON / fc.STATUS_ICONS
    for n in range(1, LEAP_STACKS + 1):
        fc.status_icon(icons / f"Charged_Leap_{n}.png", (150, 220, 255), "feather")
    for n in range(1, TIDAL_STACKS + 1):
        fc.status_icon(icons / f"Tidal_Bargain_{n}.png", (60, 130, 210), "minus")
    for name, color, glyph in (("Sunqua_Burning", (255, 110, 40), "flame"), ("Knocked_Down", (200, 170, 130), "stone"),
                               ("Storm_Marked", (160, 210, 255), "minus"), ("Meteor_Marked", (255, 140, 60), "flame"),
                               ("Shared_Tide", (90, 220, 160), "minus")):
        fc.status_icon(icons / f"{name}.png", color, glyph)


def sunqua_cause():
    return fc.cause("Foudre, marées, lave et météores du Pic de Sunqua : une part des PV max, l'armure ne la réduit "
                    "pas.", "#8cf")


# --- particules -----------------------------------------------------------------------------------------------------

S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Lightning_Orb_Glow": ("Orbe de foudre : étincelles bleues autour du cristal.",
                                          [("Spark", S("#ffffff", "#60c0ff", 4, (0.3, 0.9), (-90, 90), 0.4, 0.6,
                                                       life=(0.3, 0.5), size=(0.06, 0.12)), 1.0)]),
    "Nakasar_Fractal_Charged_Leap_Spark": ("Bond chargé : éclair bleu sous les pieds au saut et à la prise d'une orbe.",
                                           [("Burst", S("#ffffff", "#40a0ff", 30, (2.0, 5.0), (-10, 70), 0.5, 0.3,
                                                        life=(0.3, 0.6), size=(0.1, 0.2)), 0.2)]),
    "Nakasar_Fractal_Wind_Column": ("Colonne de vent : volutes blanches qui montent (le Java en pose le long).",
                                    [("Swirl", S("#ffffff", "#c8e8ff", 14, (2.0, 4.0), (70, 90), 1.4, 1.0,
                                                 life=(0.8, 1.2), size=(0.2, 0.4)), 0.6)]),
    "Nakasar_Fractal_Storm_Cloud": ("Nuage d'orage : boules grises et éclairs bleus (Java, toutes les demi-secondes).",
                                    [("Cloud", S("#808898", "#30343c", 14, (0.2, 0.6), (-30, 30), 2.2, 1.2,
                                                 life=(0.8, 1.2), size=(0.6, 1.0), blend="BlendLinear"), 0.6),
                                     ("Spark", S("#ffffff", "#60b0ff", 6, (1.0, 3.0), (-90, -40), 1.4, 0.6,
                                                 life=(0.2, 0.4), size=(0.1, 0.2)), 0.6)]),
    "Nakasar_Fractal_Storm_Disperse": ("Nuage dispersé : éclat blanc et bleu.",
                                       [("Burst", S("#ffffff", "#80c8ff", 60, (4.0, 9.0), (-60, 90), 1.5, 0.5,
                                                    life=(0.4, 0.8), size=(0.2, 0.4)), 0.3)]),
    "Nakasar_Fractal_Tornado": ("Tornade de la Voix : colonne blanche qui tourne autour d'elle.",
                                [("Whirl", S("#ffffff", "#b0d8ff", 40, (3.0, 6.0), (0, 80), 3.0, 3.0,
                                             life=(0.6, 1.0), size=(0.2, 0.4)), 0.8)]),
    "Nakasar_Fractal_Waterfall_Surge": ("Cascade qui déferle : gerbe d'eau blanche et bleue.",
                                        [("Splash", S("#ffffff", "#4090e0", 70, (3.0, 8.0), (-10, 70), 2.0, 1.2,
                                                      life=(0.5, 0.9), size=(0.2, 0.45)), 0.5)]),
    "Nakasar_Fractal_Calm_Glow": ("Élémentaire d'eau rassuré : lueur bleu pâle qui monte.",
                                  [("Glow", S("#e0f8ff", "#60c0ff", 20, (0.5, 1.4), (60, 90), 0.8, 1.4,
                                              life=(0.8, 1.2), size=(0.15, 0.3)), 0.4)]),
    "Nakasar_Fractal_Tidal_Beam": ("Lien de l'orbe sombre (Marché des marées) : un point du rayon (le Java en pose le "
                                   "long).", [("Beam", S("#c0f0ff", "#204080", 3, (0.0, 0.2), (-90, 90), 0.1, 0.1,
                                                         life=(0.3, 0.5), size=(0.2, 0.3)), 0.0)]),
    "Nakasar_Fractal_Dark_Orb": ("Orbe sombre de la Tristesse : sphère bleu nuit.",
                                 [("Core", S("#80a0ff", "#101830", 8, (0.0, 0.3), (-90, 90), 0.5, 0.5,
                                             life=(0.4, 0.6), size=(0.5, 0.8), blend="BlendLinear"), 0.0)]),
    "Nakasar_Fractal_Tide_Burst": ("La marée submerge un joueur : vague bleue.",
                                   [("Wave", S("#ffffff", "#2070d0", 60, (4.0, 9.0), (-5, 30), 1.0, 0.4,
                                               life=(0.5, 0.8), size=(0.3, 0.5)), 0.3)]),
    "Nakasar_Fractal_Shared_Mark": ("Marée partagée : volutes vertes au-dessus du joueur visé.",
                                    [("Mark", S("#e0fff0", "#30c080", 10, (0.6, 1.2), (60, 90), 0.4, 0.2,
                                                life=(0.5, 0.8), size=(0.15, 0.25)), 0.5)]),
    "Nakasar_Fractal_Boulder_Burst": ("Rocher tombé brisé : éclats de pierre et d'eau.",
                                      [("Rock", S("#c0b8a8", "#606058", 40, (2.0, 5.0), (10, 90), 1.0, 0.6,
                                                  life=(0.6, 1.0), size=(0.2, 0.4), blend="BlendLinear"), 0.3)]),
    "Nakasar_Fractal_Lava_Blast": ("Élémentaire de lave qui explose : gerbe de braises.",
                                   [("Blast", S("#fff0a0", "#ff4010", 60, (3.0, 7.0), (-10, 90), 1.0, 0.4,
                                                life=(0.5, 0.9), size=(0.2, 0.4)), 0.3)]),
    "Nakasar_Fractal_Meteor_Trail": ("Météore qui tombe : traînée de feu (le Java la pose de plus en plus bas).",
                                     [("Fire", S("#fff0a0", "#ff5010", 20, (0.5, 2.0), (60, 90), 1.2, 0.8,
                                                 life=(0.3, 0.6), size=(0.4, 0.8)), 0.0)]),
    "Nakasar_Fractal_Shockwave": ("Onde de choc du météore : un point de l'anneau (le Java en pose tout autour).",
                                  [("Dust", S("#ffd090", "#a04010", 3, (0.2, 0.6), (40, 90), 0.2, 0.2,
                                              life=(0.3, 0.5), size=(0.25, 0.4)), 0.0)]),
    "Nakasar_Fractal_Fear_Mist": ("Crainte d'Ai : brume violette autour d'elle.",
                                  [("Mist", S("#c080ff", "#200030", 12, (0.3, 0.8), (-10, 60), 0.8, 1.2,
                                              life=(0.6, 1.0), size=(0.3, 0.5), blend="BlendLinear"), 0.6)]),
}


# --- modèles --------------------------------------------------------------------------------------------------------

def boulder_parts():
    rock, moss = (128, 122, 112), (90, 120, 70)
    return [("Base", (0, 14, 0), (56, 28, 52), 10, fm.smooth(rock), "flat"),
            ("Top", (-4, 34, 2), (40, 18, 38), -20, fm.smooth(rock), "flat"),
            ("Side", (18, 12, -10), (24, 22, 22), 35, fm.smooth(rock), "flat"),
            ("Moss", (-2, 44, 4), (30, 4, 28), 5, fm.smooth(moss), "flat")]


def models():
    """Parents vanilla d'abord : cerf, esprits de foudre, de givre et de braise, golems de cristal et d'acier de feu,
    tigre à dents de sabre, spectre ; Ai en humanoïde habillé de cosmétiques vanilla ; les rochers tombés en boîtes
    (aucun rocher vanilla n'est un PNJ)."""
    v = lambda comment, parent, scale, light=None: {k: val for k, val in (
        ("$Comment", comment), ("Parent", parent), ("MinScale", scale), ("MaxScale", scale),
        ("Light", light)) if val is not None}
    m = {
        SPIRIT: v("Esprit de la montagne : grand cerf vanilla (x 1,4), lueur turquoise.", "Model_Deer_Stag", 1.4,
                  {"Color": "#8fe", "Radius": 5}),
        AIR_ELEMENTAL: v("Élémentaire d'air de l'escalier : esprit de foudre vanilla (x 2).", "Spirit_Thunder", 2.0,
                         {"Color": "#bdf", "Radius": 4}),
        VOICE: v("Voix de la montagne (émotion d'Ai, l'air) : golem de cristal de foudre vanilla (x 1,6).",
                 "Golem_Crystal_Thunder", 1.6, {"Color": "#bdf", "Radius": 6}),
        WATER_SPRITE: v("Esprit de l'eau enragé : esprit de givre vanilla, lueur bleue.", "Spirit_Frost", 1.0,
                        {"Color": "#6af", "Radius": 3}),
        FRIGHTENED: v("Élémentaire d'eau effrayé : grand esprit de givre vanilla (x 1,5), lueur pâle.", "Spirit_Frost",
                      1.5, {"Color": "#cef", "Radius": 4}),
        SORROW: v("Tristesse de la montagne (émotion d'Ai, l'eau) : golem de cristal de givre vanilla (x 1,6).",
                  "Golem_Crystal_Frost", 1.6, {"Color": "#6af", "Radius": 6}),
        LAVA_ELEMENTAL: v("Élémentaire de lave : grand esprit de braise vanilla (x 1,8).", "Spirit_Ember", 1.8,
                          {"Color": "#f80", "Radius": 4}),
        LAVA_EMBER: v("Petit élémentaire de lave (division) : esprit de braise vanilla (x 0,8).", "Spirit_Ember", 0.8,
                      {"Color": "#f60", "Radius": 2}),
        TIGER: v("Tigre du pic : tigre à dents de sabre vanilla.", "Tiger_Sabertooth", 1.0),
        FURY: v("Fureur de la montagne (émotion d'Ai, le feu) : golem d'acier de feu vanilla (x 1,4).", "Golem_Firesteel",
                1.4, {"Color": "#f84", "Radius": 6}),
        FEAR: v("Crainte d'Ai (rang Maître) : spectre vanilla, lueur violette.", "Wraith", 0.9,
                {"Color": "#a6f", "Radius": 3}),
    }
    m[BOULDER] = fc.character_model("Fallen_Boulder", boulder_parts(), 97, "Rocher tombé (PNJ fixe) : gros rocher "
                                    "moussu posé sur la Tristesse.", 0.8, (0.9, 1.6))
    robe = [("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            ("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            ("Cosmetics/Shoes/AngledBoots.blockymodel",
             "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots_Green.png")]
    m[AI] = fr.humanoid("Ai, gardienne du pic (x 1,3) : élémentaliste en robe de mage, lueur changeante (le Java "
                        "colore ses attaques).", "11", "Face_Sunken", robe, scale=(1.3, 1.3),
                        light={"Color": "#9df", "Radius": 6})
    m[AI_DARK] = fr.humanoid("Ai assombrie (rang Maître) : la même, lueur violette.", "11", "Face_Sunken", robe,
                             scale=(1.3, 1.3), light={"Color": "#a4f", "Radius": 6})
    return m


# --- attaques et rôles ----------------------------------------------------------------------------------------------

CI, RF = gc.CLEAR_INTERRUPT, gc.ROOTED_FX
R = fc.root


def interactions():
    T = fr.telegraph
    out = {}
    out["Nakasar_Fractal_Air_Whirlwind"] = {
        "$Comment": "Élémentaire d'air : tourbillon autour de lui, cercle rouge de 3,5 blocs (1,6 s), 16 dégâts et "
                    "projection (gare au vide).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Radius=3.5, Damage=16, Knockback=9, KnockUp=5,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Storm_Disperse"),
                                           fc.windup(1.6, "SFX_Ability_Wind_Strike_Slash")]}
    out["Nakasar_Fractal_Air_Shock"] = {
        "$Comment": "Élémentaire d'air : décharge (10 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Décharge.", None, None, 0.35, 10, end=2.6, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Voice_Orb_Wave"] = {
        "$Comment": "Voix de la montagne : onde d'orbes devant elle, cône de 70° sur 12 blocs (2 s), 24 dégâts.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 2.0, Angle=70, Radius=12, Damage=24, PlayersOnly=True,
                                                     ImpactParticle="Nakasar_Fractal_Storm_Disperse"),
                                           fc.windup(2.0, "SFX_Ability_Wind_Strike_Slash")]}
    out["Nakasar_Fractal_Voice_Discharge"] = {
        "$Comment": "Voix de la montagne : décharge autour d'elle, cercle rouge de 5 blocs (2,2 s), 26 dégâts et Hébété "
                    "3 s (aveuglé).",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 2.2, Radius=5, Damage=26, EffectId="Nakasar_Fractal_Dazed",
                                                     EffectDuration=3, PlayersOnly=True,
                                                     ImpactParticle="Nakasar_Fractal_Storm_Disperse"),
                                           fc.windup(2.2, "SFX_Spear_Throw_Charge")]}
    out["Nakasar_Fractal_Voice_Strike"] = {
        "$Comment": "Voix de la montagne, au contact : coup de foudre (22 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de foudre.", None, None, 0.45, 22, end=3.6, extend_bottom=1.6)]}
    out["Nakasar_Fractal_Sprite_Slippery"] = {
        "$Comment": "Esprit de l'eau enragé : sol glissant devant lui, cône de 90° sur 5 blocs (1,5 s), 12 dégâts et "
                    "À terre 1,5 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.5, Angle=90, Radius=5, Damage=12, Knockback=4,
                                                     EffectId="Nakasar_Fractal_Knocked_Down", EffectDuration=1.5,
                                                     PlayersOnly=True, ImpactParticle="Water_Splash"),
                                           fc.windup(1.5)]}
    out["Nakasar_Fractal_Sprite_Splash"] = {
        "$Comment": "Esprit de l'eau enragé : gifle d'eau (9 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Gifle d'eau.", None, None, 0.35, 9, end=2.4, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Lava_Burst"] = {
        "$Comment": "Élémentaire de lave : jet de flammes autour de lui, cercle rouge de 3 blocs (1,6 s), 18 dégâts et "
                    "Brûlure 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Radius=3, Damage=18,
                                                     EffectId="Nakasar_Fractal_Sunqua_Burning", EffectDuration=4,
                                                     PlayersOnly=True, ImpactParticle="Fire_AoE_Spawn"),
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Lava_Touch"] = {
        "$Comment": "Élémentaire de lave : coup brûlant (12 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup brûlant.", None, None, 0.35, 12, end=2.6, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Ember_Touch"] = {
        "$Comment": "Petit élémentaire de lave : étincelle (7 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Étincelle.", None, None, 0.3, 7, end=2.2, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Tiger_Swipe"] = {
        "$Comment": "Tigre du pic : deux coups de griffes (14 dégâts chacun), animations du tigre vanilla.",
        "Type": "Serial", "Interactions": [
            fr.swing("Griffe gauche.", "Tiger_Sabertooth_Default", "SwipeLeft", 0.35, 14, end=3.0, sound="SFX_Unarmed_Swing"),
            fr.swing("Griffe droite.", "Tiger_Sabertooth_Default", "SwipeRight", 0.35, 14, end=3.0, direction="ToRight",
                     yaw=-50, sound="SFX_Unarmed_Swing")]}
    out["Nakasar_Fractal_Tiger_Pounce"] = {
        "$Comment": "Tigre du pic : bond sur sa cible lointaine, cercle rouge de 2,5 blocs (1,4 s), 20 dégâts et "
                    "À terre 1 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.4, Anchor="Farthest", OffsetMax=14, Radius=2.5, Damage=20,
                                                     TeleportCaster=True, EffectId="Nakasar_Fractal_Knocked_Down",
                                                     EffectDuration=1, PlayersOnly=True,
                                                     ImpactParticle="Stick_Slam_Ground_Large"),
                                           fc.windup(1.4)]}
    out["Nakasar_Fractal_Fury_Strikes"] = {
        "$Comment": "Fureur de la montagne, au contact : deux coups brûlants (22 dégâts et Brûlure 4 s chacun).",
        "Type": "Serial", "Interactions": [
            fr.swing("Coup brûlant gauche.", "Golem_Firesteel_Default", "SwingLeft", 0.5, 22, end=4.0,
                     extra=[fr.effect_on_target("Nakasar_Fractal_Sunqua_Burning", 4)]),
            fr.swing("Coup brûlant droit.", "Golem_Firesteel_Default", "SwingRight", 0.5, 22, end=4.0,
                     direction="ToRight", yaw=-50, extra=[fr.effect_on_target("Nakasar_Fractal_Sunqua_Burning", 4)])]}
    out["Nakasar_Fractal_Fury_Leap"] = {
        "$Comment": "Fureur de la montagne : bond brûlant sur sa cible lointaine, cercle rouge de 4 blocs (1,6 s), 30 "
                    "dégâts, À terre 2 s et Brûlure 4 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Circle", 1.6, Anchor="Farthest", OffsetMax=20, Radius=4, Damage=30,
                                                     TeleportCaster=True, EffectId="Nakasar_Fractal_Knocked_Down",
                                                     EffectDuration=2, PlayersOnly=True,
                                                     ImpactParticle="Fire_AoE_Spawn",
                                                     ImpactSound="SFX_Goblin_Feastmaster_Slam"),
                                           fc.windup(1.6, "SFX_Spear_Throw_Charge", "Golem_Firesteel_Default",
                                                     "GroundSlam")]}
    out["Nakasar_Fractal_Fury_Lunge"] = {
        "$Comment": "Fureur de la montagne : ruée fumante, ligne rouge de 14 x 3 blocs (1,6 s), 28 dégâts et projection.",
        "Type": "Serial", "Interactions": [CI, RF, {"Type": "Nakasar_Fractal_Charge", "Length": 14, "Width": 3,
                                                     "Seconds": 1.6, "Speed": 14, "Damage": 28, "Knockback": 7,
                                                     "ImpactSound": "SFX_Goblin_Feastmaster_Slam"},
                                           fc.windup(1.6)]}
    out["Nakasar_Fractal_Ai_Strike"] = {
        "$Comment": "Ai, au contact : coup de bâton élémentaire (20 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bâton.", "Staff", "SwingLeft", 0.4, 20, end=3.4)]}
    out["Nakasar_Fractal_Ai_Gust"] = {
        "$Comment": "Ai : rafale devant elle, cône de 60° sur 9 blocs (1,6 s), 22 dégâts et recul.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.6, Angle=60, Radius=9, Damage=22, Knockback=7,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Storm_Disperse"),
                                           fc.windup(1.6, "SFX_Spear_Throw_Charge", "Staff", "CastSummonCharging")]}
    out["Nakasar_Fractal_Ai_Dark_Wave"] = {
        "$Comment": "Ai assombrie : vague d'ombre devant elle, cône de 100° sur 8 blocs (1,8 s), 30 dégâts et agonie 3 s.",
        "Type": "Serial", "Interactions": [CI, RF, T("Cone", 1.8, Angle=100, Radius=8, Damage=30, AgonySeconds=3,
                                                     PlayersOnly=True, ImpactParticle="Nakasar_Fractal_Fear_Mist"),
                                           fc.windup(1.8, "SFX_Spear_Throw_Charge", "Staff", "CastSummonCharging")]}
    out["Nakasar_Fractal_Fear_Touch"] = {
        "$Comment": "Crainte : toucher glacé (8 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Toucher.", None, None, 0.4, 8, end=2.4, sound="SFX_Unarmed_Swing")]}
    return out


MELEE = ["Air_Whirlwind", "Air_Shock", "Voice_Orb_Wave", "Voice_Discharge", "Voice_Strike", "Sprite_Slippery",
         "Sprite_Splash", "Lava_Burst", "Lava_Touch", "Ember_Touch", "Tiger_Swipe", "Tiger_Pounce", "Fury_Strikes",
         "Fury_Leap", "Fury_Lunge", "Ai_Strike", "Ai_Gust", "Ai_Dark_Wave", "Fear_Touch"]
RANGED = []


def roles():
    n = lambda role: fc.npc_name(LANG, role)
    out = {}
    out[SPIRIT] = fc.static_role(LANG, SPIRIT, "Esprit de la montagne : accueille le groupe ; on ne peut pas le blesser "
                                 "(Java).", GENERATOR, 1000, attitude="Neutral", foe=False)
    out[FRIGHTENED] = fc.static_role(LANG, FRIGHTENED, "Élémentaire d'eau effrayé : rassuré par un joueur accroupi près "
                                     "de lui ; on ne peut pas le blesser (Java, sunquapeak.WaterPath).", GENERATOR, 1000,
                                     attitude="Neutral", foe=False)
    out[SORROW] = fc.static_role(LANG, SORROW, "Tristesse de la montagne : prisonnière des rochers tombés ; on ne peut "
                                 "pas la blesser (Java, sunquapeak.Sorrow).", GENERATOR, 1000, attitude="Neutral",
                                 foe=False)
    out[BOULDER] = fc.static_role(LANG, BOULDER, "Rocher tombé : à briser ; chaque coup peut faire jaillir une zone "
                                  "(Java, sunquapeak.Sorrow).", GENERATOR, 1600)
    out[AIR_ELEMENTAL] = fr.role(
        AIR_ELEMENTAL, "Élémentaire d'air de l'escalier brisé : décharge, tourbillon qui projette.", AIR_ELEMENTAL,
        n(AIR_ELEMENTAL), 900, [fr.timed_attack("Whirl", R("Air_Whirlwind"), rng=3.5, comment="Tourbillon."),
                                fr.melee(R("Air_Shock"), 2.6, (0.7, 1.1)), fr.chase(16, stop=1.6)],
        fr.walk(3.0), GENERATOR, sight=14, leash=12, home=False, timers=[fr.timer("Whirl", (2, 4), (7, 9))],
        KnockbackScale=0.3, DeathAnimationTime=1.0)
    out[VOICE] = fr.role(
        VOICE, "Voix de la montagne, barre de boss : ondes d'orbes, décharge, coup de foudre. Tornade et nuages d'orage "
        "à 66 et 33 % : Java (sunquapeak.VoiceOfTheMountain).", VOICE, n(VOICE), 10000,
        [fr.timed_attack("Wave", R("Voice_Orb_Wave"), rng=12, los=True, comment="Onde d'orbes."),
         fr.timed_attack("Discharge", R("Voice_Discharge"), rng=5, comment="Décharge."),
         fr.melee(R("Voice_Strike"), 3.6, (0.8, 1.2)), fr.chase(30, stop=3.0)], fr.walk(2.6), GENERATOR, sight=30,
        leash=36, home=False, timers=[fr.timer("Wave", (3, 5), (7, 9)), fr.timer("Discharge", (6, 8), (11, 14))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[WATER_SPRITE] = fr.role(
        WATER_SPRITE, "Esprit de l'eau enragé : sol glissant (à terre), gifles.", WATER_SPRITE, n(WATER_SPRITE), 520,
        [fr.timed_attack("Slip", R("Sprite_Slippery"), rng=5, los=True, comment="Sol glissant."),
         fr.melee(R("Sprite_Splash"), 2.4, (0.7, 1.0)), fr.chase(24, stop=1.6)], fr.walk(3.6), GENERATOR, sight=20,
        leash=24, home=False, timers=[fr.timer("Slip", (2, 4), (7, 9))], KnockbackScale=0.6, DeathAnimationTime=1.0)
    out[LAVA_ELEMENTAL] = fr.role(
        LAVA_ELEMENTAL, "Élémentaire de lave : jet de flammes, coup brûlant ; il explose et se divise en mourant (Java, "
        "sunquapeak.LavaPath).", LAVA_ELEMENTAL, n(LAVA_ELEMENTAL), 1100,
        [fr.timed_attack("Burst", R("Lava_Burst"), rng=3, comment="Jet de flammes."),
         fr.melee(R("Lava_Touch"), 2.6, (0.7, 1.1)), fr.chase(24, stop=1.6)], fr.walk(3.0), GENERATOR, sight=18,
        leash=24, home=False, timers=[fr.timer("Burst", (3, 5), (8, 10))], KnockbackScale=0.2, DeathAnimationTime=0.6)
    out[LAVA_EMBER] = fr.role(
        LAVA_EMBER, "Petit élémentaire de lave (division) : étincelles ; il explose en mourant (Java).", LAVA_EMBER,
        n(LAVA_EMBER), 300, [fr.melee(R("Ember_Touch"), 2.2, (0.6, 0.9)), fr.chase(24, stop=1.2)], fr.walk(4.2),
        GENERATOR, sight=24, leash=28, home=False, KnockbackScale=0.8, DeathAnimationTime=0.4)
    out[TIGER] = fr.role(
        TIGER, "Tigre du pic : griffes, bond.", TIGER, n(TIGER), 1000,
        [fr.timed_attack("Pounce", R("Tiger_Pounce"), rng=14, los=True, comment="Bond."),
         fr.melee(R("Tiger_Swipe"), 2.8, (0.7, 1.0)), fr.chase(24, stop=1.8)], fr.walk(5.0), GENERATOR, sight=18,
        leash=24, home=False, timers=[fr.timer("Pounce", (3, 5), (9, 12))], KnockbackScale=0.4, DeathAnimationTime=1.2)
    out[FURY] = fr.role(
        FURY, "Fureur de la montagne, barre de boss et de défiance : coups brûlants, bond, ruée. Météores, frappe extrême "
        "et météores qui suivent : Java (sunquapeak.FuryOfTheMountain).", FURY, n(FURY), 14000,
        [fr.timed_attack("Leap", R("Fury_Leap"), rng=20, los=True, comment="Bond brûlant."),
         fr.timed_attack("Lunge", R("Fury_Lunge"), rng=14, los=True, comment="Ruée fumante."),
         fr.melee(R("Fury_Strikes"), 4.0, (0.8, 1.2)), fr.chase(30, stop=3.0)], fr.walk(3.4), GENERATOR, sight=30,
        leash=36, home=False, timers=[fr.timer("Leap", (5, 7), (11, 14)), fr.timer("Lunge", (8, 10), (13, 16))],
        KnockbackScale=0.0, DeathAnimationTime=2.0)
    out[AI] = fr.role(
        AI, "Ai, gardienne du pic, barre de boss et de défiance : coup de bâton, rafale. Air, feu et eau (ondes d'orbes, "
        "bombes, balayage, front d'orage, météores, frappe extrême, Marché des marées, marée partagée) : Java "
        "(sunquapeak.Ai).", AI, n(AI), 22000,
        [fr.timed_attack("Gust", R("Ai_Gust"), rng=9, los=True, comment="Rafale."),
         fr.melee(R("Ai_Strike"), 3.4, (0.8, 1.2)), fr.chase(36, speed=0.8, stop=3.0)], fr.walk(3.0), GENERATOR,
        sight=40, leash=50, home=False, timers=[fr.timer("Gust", (4, 6), (8, 11))], KnockbackScale=0.0,
        DeathAnimationTime=2.0)
    out[AI_DARK] = fr.role(
        AI_DARK, "Ai assombrie (rang Maître), barre de boss : vague d'ombre, coup de bâton ; craintes (Java, "
        "sunquapeak.Ai).", AI_DARK, n(AI_DARK), 9000,
        [fr.timed_attack("Wave", R("Ai_Dark_Wave"), rng=8, los=True, comment="Vague d'ombre."),
         fr.melee(R("Ai_Strike"), 3.4, (0.8, 1.2)), fr.chase(36, speed=0.8, stop=3.0)], fr.walk(3.0), GENERATOR,
        sight=40, leash=50, home=False, timers=[fr.timer("Wave", (4, 6), (9, 12))], KnockbackScale=0.0,
        DeathAnimationTime=2.5)
    out[FEAR] = fr.role(
        FEAR, "Crainte d'Ai : suit un joueur 15 s puis éclate (Java) ; la tuer avant.", FEAR, n(FEAR), 500,
        [fr.melee(R("Fear_Touch"), 2.4, (0.8, 1.2)), fr.chase(40, stop=1.2)], fr.walk(3.4), GENERATOR, sight=40,
        leash=50, home=False, KnockbackScale=0.5, DeathAnimationTime=0.8)
    return out


# --- langue ---------------------------------------------------------------------------------------------------------

def lang():
    t = fc.Lang()
    t.item(BLOSSOM, "Fleurs de Sunqua", "Le feuillage rose des cerisiers du pic.", "Sunqua blossoms",
           "The pink foliage of the peak's cherry trees.")
    t.item(ORB, "Orbe de foudre", "Passez dessus : Bond chargé, des sauts plus hauts.", "Lightning orb",
           "Walk through it: Charged Leap, higher jumps.")
    for role, f, e in ((SPIRIT, "Esprit de la montagne", "Spirit of the Mountain"),
                       (AIR_ELEMENTAL, "Élémentaire d'air", "Air Elemental"),
                       (VOICE, "Voix de la montagne", "Voice of the Mountain"),
                       (WATER_SPRITE, "Esprit de l'eau enragé", "Enraged Water Sprite"),
                       (FRIGHTENED, "Élémentaire d'eau effrayé", "Frightened Water Elemental"),
                       (SORROW, "Tristesse de la montagne", "Sorrow of the Mountain"),
                       (BOULDER, "Rocher tombé", "Fallen Boulder"),
                       (LAVA_ELEMENTAL, "Élémentaire de lave", "Lava Elemental"),
                       (LAVA_EMBER, "Petit élémentaire de lave", "Lesser Lava Elemental"),
                       (TIGER, "Tigre du pic", "Peak Tiger"),
                       (FURY, "Fureur de la montagne", "Fury of the Mountain"),
                       (AI, "Ai, gardienne du pic", "Ai, Keeper of the Peak"),
                       (AI_DARK, "Ai assombrie", "Ai, Darkened"),
                       (FEAR, "Crainte", "Fear")):
        t.npc(role, f, e)
    effects_lang = [("Sunqua_Burning", "Brûlure de la montagne", "Mountain burn"),
                    ("Knocked_Down", "À terre", "Knocked down"),
                    ("Storm_Marked", "Bombe d'orage", "Storm bomb"),
                    ("Meteor_Marked", "Météore en approche", "Incoming meteor"),
                    ("Shared_Tide", "Marée partagée", "Shared tide")]
    effects_lang += [(f"Charged_Leap_{n}", f"Bond chargé ({n})", f"Charged Leap ({n})") for n in range(1, LEAP_STACKS + 1)]
    effects_lang += [(f"Tidal_Bargain_{n}", f"Marché des marées ({n})", f"Tidal Bargain ({n})")
                     for n in range(1, TIDAL_STACKS + 1)]
    for eid, f, e in effects_lang:
        t.put(f"effects.Nakasar_Fractal_{eid}", f, e)
    msgs = {
        "intro": ("L'Esprit de la montagne : « Ai a confié au pic ce qu'elle ne pouvait plus porter : sa voix, sa "
                  "tristesse, sa fureur. Montez jusqu'à elle. »",
                  "Spirit of the Mountain: \"Ai entrusted the peak with what she could no longer bear: her voice, her "
                  "sorrow, her fury. Climb up to her.\""),
        "leap.intro": ("Passez sur les orbes de foudre : chaque orbe donne une charge de Bond chargé (3 au plus, 20 s). "
                       "Il en faut deux pour l'escalier brisé.",
                       "Walk through the lightning orbs: each orb gives a Charged Leap stack (3 at most, 20 s). The "
                       "broken stairs take two."),
        "leap.gain": ("Bond chargé : {stacks} charge(s).", "Charged Leap: {stacks} stack(s)."),
        "stairs.elementals": ("Des élémentaires d'air gardent l'escalier : leurs orbes vous porteront plus haut.",
                              "Air elementals guard the stairs: their orbs will carry you higher."),
        "stairs.mended": ("Le socle s'éveille : l'escalier se reforme derrière vous.",
                          "The plinth awakens: the stairs reform behind you."),
        "stairs.waiting": ("Le socle attend que les trois élémentaires d'air soient vaincus.",
                           "The plinth waits until the three air elementals are defeated."),
        "checkpoint": ("Point de retour atteint.", "Checkpoint reached."),
        "column.open": ("Une colonne de vent se lève : avancez dedans.", "A wind column rises: step into it."),
        "voice.enter": ("La Voix de la montagne gronde au-dessus du plateau.", "The Voice of the Mountain rumbles over "
                        "the plateau."),
        "voice.storm": ("La Voix se retire dans une tornade : dispersez les quatre nuages d'orage d'un bond chargé !",
                        "The Voice withdraws into a tornado: disperse the four storm clouds with a charged leap!"),
        "voice.cloud": ("Un nuage d'orage se disperse ({count}/{total}).", "A storm cloud disperses ({count}/{total})."),
        "voice.back": ("La tornade retombe : la Voix redevient vulnérable.", "The tornado dies down: the Voice is "
                       "vulnerable again."),
        "voice.reset": ("La Voix se tait... pour l'instant.", "The Voice falls silent... for now."),
        "voice.victory": ("La Voix de la montagne se tait. Une colonne de vent mène à la corniche des cascades.",
                          "The Voice of the Mountain falls silent. A wind column leads to the waterfall ledge."),
        "water.intro": ("La corniche des cascades : quand l'eau gronde, quittez les bandes rouges. Trois élémentaires "
                        "d'eau ont peur : accroupissez-vous près d'eux pour les rassurer.",
                        "The waterfall ledge: when the water roars, leave the red strips. Three water elementals are "
                        "scared: crouch near them to calm them."),
        "water.surge": ("La cascade déferle !", "The waterfall surges!"),
        "water.calming": ("Restez accroupi près de l'élémentaire...", "Stay crouched near the elemental..."),
        "water.calmed": ("L'élémentaire d'eau se calme et s'en va ({count}/{total}).",
                         "The water elemental calms down and leaves ({count}/{total})."),
        "water.sprites": ("Des esprits de l'eau enragés surgissent !", "Enraged water sprites burst out!"),
        "water.done": ("Les trois élémentaires sont rassurés : la barrière s'ouvre. Plus loin, les rochers flottants.",
                       "All three elementals are calm: the barrier opens. Further on, the floating rocks."),
        "sorrow.enter": ("La Tristesse de la montagne est prisonnière des rochers tombés : brisez-les. L'orbe sombre lie "
                         "le plus proche : passez dans le rayon pour prendre le lien.",
                         "The Sorrow of the Mountain is trapped under fallen boulders: break them. The dark orb "
                         "tethers the closest player: step into the beam to take the tether."),
        "sorrow.tether": ("L'orbe sombre vous lie : le Marché des marées monte !", "The dark orb tethers you: the Tidal "
                          "Bargain rises!"),
        "sorrow.taken": ("{name} prend le lien.", "{name} takes the tether."),
        "tide.drowned": ("La marée submerge {name} !", "The tide drowns {name}!"),
        "sorrow.boulder": ("Un rocher tombé se brise ({count}/{total}).", "A fallen boulder breaks ({count}/{total})."),
        "sorrow.reset": ("Les rochers retombent sur la Tristesse.", "The boulders fall back onto the Sorrow."),
        "sorrow.victory": ("La Tristesse de la montagne est libérée : le sentier de lave s'ouvre.",
                           "The Sorrow of the Mountain is free: the lava path opens."),
        "lava.wall": ("Des élémentaires de lave gardent ce mur : abattez-les.", "Lava elementals guard this wall: bring "
                      "them down."),
        "lava.split": ("L'élémentaire explose et se divise !", "The elemental explodes and splits!"),
        "lava.open": ("Le mur de roche s'effondre.", "The rock wall collapses."),
        "fury.enter": ("La Fureur de la montagne jaillit du cratère !", "The Fury of the Mountain bursts from the crater!"),
        "fury.meteors": ("La Fureur appelle des météores : écartez-vous des cercles, puis cachez-vous derrière un "
                         "météore !", "The Fury calls meteors: leave the circles, then hide behind a meteor!"),
        "fury.extreme": ("Frappe extrême ! Cachez-vous derrière un météore !", "Extreme strike! Hide behind a meteor!"),
        "fury.tracking": ("Deux météores suivent {a} et {b} : croisez-les pour qu'ils se brisent !",
                          "Two meteors follow {a} and {b}: cross them so they shatter each other!"),
        "fury.shattered": ("Les deux météores se brisent l'un l'autre.", "The two meteors shatter each other."),
        "fury.defiance": ("La Fureur s'embrase : brisez sa défiance !", "The Fury flares up: break its defiance!"),
        "fury.inferno": ("La défiance tient : la Fureur déchaîne un brasier !", "The defiance holds: the Fury unleashes "
                         "an inferno!"),
        "fury.reset": ("La Fureur retourne au cratère.", "The Fury returns to the crater."),
        "fury.victory": ("La Fureur de la montagne s'éteint : la montée vers le sommet s'ouvre.",
                         "The Fury of the Mountain dies out: the climb to the summit opens."),
        "ai.enter": ("Ai, gardienne du pic : « Vous avez traversé mes émotions. Voyons si vous me supportez tout "
                     "entière. »", "Ai, Keeper of the Peak: \"You crossed my emotions. Let's see if you can bear all "
                     "of me.\""),
        "ai.lines": ("Ai file au bord de l'arène : des ondes d'orbes balaient le sol. Brisez sa défiance !",
                     "Ai dashes to the edge of the arena: orb waves sweep the floor. Break her defiance!"),
        "ai.lines.broken": ("La défiance d'Ai cède : elle vacille !", "Ai's defiance breaks: she staggers!"),
        "ai.bombs": ("Bombes d'orage : un cercle vous suit. Écartez-vous des autres !",
                     "Storm bombs: a circle follows you. Spread out!"),
        "ai.sweep": ("Ai balaie l'arène !", "Ai sweeps the arena!"),
        "ai.storm": ("Front d'orage : Ai se protège ; dispersez les nuages d'un bond chargé !",
                     "Storm front: Ai shields herself; disperse the clouds with a charged leap!"),
        "ai.fire": ("Ai s'embrase : place au feu.", "Ai bursts into flame: fire takes over."),
        "ai.meteors": ("Ai appelle des météores !", "Ai calls meteors!"),
        "ai.rain": ("Pluie de météores : Ai se protège, tenez bon !", "Meteor rain: Ai shields herself, hold on!"),
        "ai.water": ("Ai se fait marée : place à l'eau.", "Ai becomes the tide: water takes over."),
        "ai.shared": ("Marée partagée sur {name} : rejoignez-le pour partager les dégâts !",
                      "Shared tide on {name}: join them to share the damage!"),
        "ai.dark": ("Ai s'assombrit : sa dernière émotion, la peur, prend le dessus !",
                    "Ai darkens: her last emotion, fear, takes over!"),
        "ai.fears": ("Des craintes vous suivent : tuez-les avant qu'elles n'éclatent !",
                     "Fears follow you: kill them before they burst!"),
        "ai.fear.burst": ("Une crainte éclate !", "A fear bursts!"),
        "ai.vulnerable": ("Ai redevient vulnérable.", "Ai is vulnerable again."),
        "ai.reset": ("Ai se retire dans le calme du pic.", "Ai withdraws into the calm of the peak."),
        "ai.victory": ("Ai s'apaise : « Merci. » Le trésor du Pic de Sunqua est à vous.",
                       "Ai calms down: \"Thank you.\" The treasure of Sunqua Peak is yours."),
        "title.victory": ("Pic de Sunqua terminé", "Sunqua Peak complete"),
    }
    for k, (f, e) in msgs.items():
        t.put(k, f, e)
    return t


# --- Java -----------------------------------------------------------------------------------------------------------

def java_layout(p, t):
    J, jd = fc, fc.jd
    stand = lambda x, z: t.stand[(round(x), round(z))]
    at = lambda x, z: (round(x), stand(x, z), round(z))
    steps = [(x, s, z) for x, z, s, r in sc.STEPS]
    elementals = [steps[k] for k in sc.ELEMENTAL_STEPS]
    step_orbs = [(x + 2, s, z) for x, s, z in elementals]
    voice_c = (sc.VOICE_C[0], sc.VOICE_STAND, sc.VOICE_C[1])
    clouds = [(sc.VOICE_C[0] + round(math.cos(a) * sc.CLOUD_RING), sc.VOICE_STAND + sc.CLOUD_HEIGHT,
               sc.VOICE_C[1] + round(math.sin(a) * sc.CLOUD_RING)) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    voice_orbs = [(sc.VOICE_C[0] + round(math.cos(a) * 12), sc.VOICE_STAND, sc.VOICE_C[1] + round(math.sin(a) * 12))
                  for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)]
    summit_c = (sc.SUMMIT_C[0], sc.SUMMIT_STAND, sc.SUMMIT_C[1])
    summit_clouds = [(sc.SUMMIT_C[0] + round(math.cos(a) * 11), sc.SUMMIT_STAND + sc.CLOUD_HEIGHT,
                      sc.SUMMIT_C[1] + round(math.sin(a) * 11)) for a in (0.3, 0.3 + math.pi / 2, 0.3 + math.pi,
                                                                          0.3 + 3 * math.pi / 2)]
    summit_orbs = [(sc.SUMMIT_C[0] + round(math.cos(a) * 15), sc.SUMMIT_STAND, sc.SUMMIT_C[1] + round(math.sin(a) * 15))
                   for a in (0.3 + math.pi / 4, 0.3 + 3 * math.pi / 4, 0.3 + 5 * math.pi / 4, 0.3 + 7 * math.pi / 4)]
    nooks = [at(x, z) for x, z, r in sc.NOOKS]
    surges = []
    for theta in sc.SURGES:
        x, z = sc.polar(theta, sc.SURGE_FROM)
        surges.append((x, sc.WATER_S, z, math.radians(theta)))
    sorrow_c = (sc.SORROW_C[0], sc.SORROW_STAND, sc.SORROW_C[1])
    boulders = [at(sc.SORROW_C[0] + math.cos(math.radians(a)) * sc.BOULDER_RING,
                   sc.SORROW_C[1] + math.sin(math.radians(a)) * sc.BOULDER_RING) for a in (20, 92, 164, 236, 308)]
    dark_orb = (sc.SORROW_C[0], sc.SORROW_STAND + 6, sc.SORROW_C[1])
    guards = []
    for f in sc.LAVA_WALLS:
        before = sc.along("lava", max(0.0, f - 0.1))
        guards.append([at(before[0] + dx, before[1] + dz) for dx, dz in ((-1, 0), (1, 1), (0, -1))])
    tigers = [at(*sc.along("lava", f)[:2]) for f in sc.TIGERS]
    crater_c = (sc.CRATER_C[0], sc.CRATER_STAND, sc.CRATER_C[1])
    water_start = (round(sc.polar(171, 62)[0]), sc.WATER_S, round(sc.polar(171, 62)[1]))
    water_end = at(*sc.along("water", 0.9)[:2])
    rise_end = at(*sc.along("rise", 0.97)[:2])
    reward = (sc.SUMMIT_C[0] + 3, sc.SUMMIT_STAND, sc.SUMMIT_C[1])
    exit_at = (sc.SUMMIT_C[0] + 5, sc.SUMMIT_STAND, sc.SUMMIT_C[1])
    soft = [(sc.SORROW_C[0], sc.SORROW_STAND, sc.SORROW_C[1], sc.SORROW_R + 4)]
    box = lambda x0, x1, z0, z1, y0, y1: fc.jbox(x0, x1, y0, y1, z0, z1)
    water_zone = box(-80, -30, -80, 0, sc.WATER_S - 12, sc.WATER_S + 12)
    stairs_zone = box(-82, 14, 30, 142, -10, 40)
    return f"""package dev.nakasar.hytale.fractals.sunquapeak;

import dev.nakasar.hytale.fractals.arena.Box;

/**
 * Positions du Pic de Sunqua, écrites par tools/generate_sunqua_peak.py (ne pas modifier à la main : relancer le
 * générateur). Repère du monde : x vers l'est, z vers le sud. Points {{x, y, z}} : pieds ; blocs {{x, y, z}} : coins.
 */
public final class SunquaPeakLayout {{

    public static final double[] SPAWN = {J.jpoint(sc.SPAWN)};
    public static final double[] SPIRIT = {J.jpoint(sc.SPIRIT_AT)};
    /** Orbes de foudre du départ (blocs, les pieds dedans). */
    public static final int[][] START_ORBS = {J.jblocks(sc.START_ORBS)};

    /** L'escalier brisé : îlots (centre, pieds), élémentaires d'air, orbes de leurs îlots, socle. */
    public static final double[][] STEPS = {J.jpoints(steps)};
    public static final double[][] AIR_ELEMENTALS = {J.jpoints(elementals)};
    public static final int[][] STEP_ORBS = {J.jblocks(step_orbs)};
    public static final double[] PLINTH = {J.jpoint((sc.PLINTH_C[0], sc.AREA["plinth"][4], sc.PLINTH_C[1]))};
    public static final double PLINTH_RADIUS = {jd(sc.AREA["plinth"][3])};
    /** Escalier refait : dalles posées par le Java quand les trois élémentaires sont vaincus. */
    public static final int[][] STAIRS = {J.jblocks(t.stairs)};
    public static final Box STAIRS_ZONE = {stairs_zone};

    /** Colonnes de vent : départ, points du trajet (pieds), le dernier est l'arrivée. */
    public static final double[][] COLUMN_1 = {J.jpoints(sc.COLUMN_1)};
    public static final double[][] COLUMN_2 = {J.jpoints(sc.COLUMN_2)};

    /** Le plateau de la Voix : centre, rayon, nuages d'orage (à {sc.CLOUD_HEIGHT} blocs du sol), orbes. */
    public static final double[] VOICE = {J.jpoint(voice_c)};
    public static final double VOICE_RADIUS = {jd(sc.VOICE_R)};
    public static final double[][] VOICE_CLOUDS = {J.jpoints(clouds)};
    public static final int[][] VOICE_ORBS = {J.jblocks(voice_orbs)};

    /** La corniche des cascades : départ, niches des élémentaires effrayés, cascades (départ et angle de la bande). */
    public static final double[] WATER_START = {J.jpoint(water_start)};
    public static final double[] WATER_END = {J.jpoint(water_end)};
    public static final double[][] NOOKS = {J.jpoints(nooks)};
    public static final double[][] SURGES = {{{", ".join("{" + f"{jd(x)}, {jd(fc.GROUND_Y + y)}, {jd(z)}, {jd(a)}" + "}" for x, y, z, a in surges)}}};
    public static final double SURGE_LENGTH = {jd(sc.SURGE_LENGTH)};
    public static final double SURGE_WIDTH = {jd(sc.SURGE_WIDTH)};
    public static final int[][] WATER_GATE = {J.jblocks(t.gates["water"])};
    public static final Box WATER_ZONE = {water_zone};

    /** La terrasse de la Tristesse : centre, rayon, rochers tombés, orbe sombre, barrière du sentier de lave. */
    public static final double[] SORROW = {J.jpoint(sorrow_c)};
    public static final double SORROW_RADIUS = {jd(sc.SORROW_R)};
    public static final double[][] BOULDERS = {J.jpoints(boulders)};
    public static final double[] DARK_ORB = {J.jpoint(dark_orb)};
    public static final int[][] SORROW_GATE = {J.jblocks(t.gates["sorrow"])};
    /** Chute amortie (x, y du sol, z, rayon) : pas de dégâts de chute dedans. */
    public static final double[][] SOFT_LANDINGS = {{{", ".join("{" + f"{jd(x + 0.5)}, {jd(fc.GROUND_Y + y)}, {jd(z + 0.5)}, {jd(r)}" + "}" for x, y, z, r in soft)}}};

    /** Le sentier de lave : murs (cases), gardes de chaque mur, tigres. */
    public static final int[][][] LAVA_WALLS = {{{", ".join(J.jblocks(w) for w in t.walls)}}};
    public static final double[][][] WALL_GUARDS = {{{", ".join(J.jpoints(g) for g in guards)}}};
    public static final double[][] TIGERS = {J.jpoints(tigers)};

    /** Le cratère de la Fureur : centre, rayon, barrière de la montée. */
    public static final double[] CRATER = {J.jpoint(crater_c)};
    public static final double CRATER_RADIUS = {jd(sc.CRATER_R)};
    public static final int[][] CRATER_GATE = {J.jblocks(t.gates["crater"])};

    /** L'arène du sommet : centre, rayon, haut de la montée, nuages et orbes du front d'orage, coffre, sortie. */
    public static final double[] SUMMIT = {J.jpoint(summit_c)};
    public static final double SUMMIT_RADIUS = {jd(sc.SUMMIT_R)};
    public static final double[] RISE_END = {J.jpoint(rise_end)};
    public static final double[][] SUMMIT_CLOUDS = {J.jpoints(summit_clouds)};
    public static final int[][] SUMMIT_ORBS = {J.jblocks(summit_orbs)};
    /** Ondes d'orbes d'Ai : bandes de {ORB_LINE_LENGTH} x {ORB_LINE_WIDTH} blocs (Telegraphs.Strip, JAVA_LINES). */
    public static final double ORB_LINE_LENGTH = {jd(ORB_LINE_LENGTH)};
    public static final double ORB_LINE_WIDTH = {jd(ORB_LINE_WIDTH)};
    public static final int[] REWARD = {J.jblock(reward)};
    public static final int[] END_EXIT = {J.jblock(exit_at)};

    private SunquaPeakLayout() {{
    }}
}}
"""


# --- aperçus --------------------------------------------------------------------------------------------------------

def color_of(name):
    c = fn.nature_color(name)
    if c:
        return c
    if name == BLOSSOM:
        return (240, 130, 190)
    if name == ORB:
        return (140, 220, 255)
    if name == sc.BARRIER:
        return (200, 120, 255)
    if "Lava" in name:
        return (255, 100, 20)
    if any(k in name for k in ("Volcanic", "Magma", "Basalt", "Ash", "Burnt")):
        return (70, 60, 58)
    if any(k in name for k in ("Marble", "Calcite", "Quartzite")):
        return (230, 225, 215)
    if name.startswith("Soil_Grass"):
        return (90, 170, 70)
    if "Bamboo" in name:
        return (120, 190, 80)
    if name.startswith(("Soil", "Rock")):
        return (125, 122, 118)
    return (200, 200, 200)


def course_prefab():
    """Pour la carte du wiki (render_wiki_maps)."""
    p, _ = sc.build_all()
    return p


def preview_images(p, folder):
    q = go.Prefab()
    q.blocks = dict(p.blocks)
    for (x, y, z), (f, _) in p.fluids.items():
        if (x, y + 1, z) not in p.fluids and (x, y + 1, z) not in q.blocks:
            q.blocks[(x, y, z)] = (f, 0)
    fc.top_view(q, folder / "pic_de_sunqua_dessus.png",
                lambda n: (50, 120, 220) if n == "Water_Source" else (255, 100, 20) if n == "Lava_Source" else color_of(n),
                scale=2)


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    write_blocks()
    for name, doc in effects().items():
        fc.write_json(fc.EFFECTS / f"{name}.json", doc)
    status_icons()
    fc.write_json(fc.SERVER / f"Entity/Damage/{CAUSE}.json", sunqua_cause())
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    for name, doc in interactions().items():
        fc.write_json(go.INTERACTIONS / "SunquaPeak" / f"{name}.json", doc)
    fc.write_roots(MELEE, RANGED)
    for role, doc in models().items():
        fc.write_json(fc.MODELS / f"{role}.json", doc)
    for role, doc in roles().items():
        fr.write_json(fc.ROLES / f"{role}.json", doc)
    fc.add_foes(FOE_ROLES)

    p, t = sc.build_all()
    sections = fc.split_sections(p, min(z for _, _, z in p.blocks))
    # Ciel clair et bleu du pic, brume blanche lointaine (le vide cerné de nuages de la carte), plein jour.
    counts = fc.write_instance(INSTANCE, "Pic de Sunqua", PREFAB_DIR, sections, sc.SPAWN, "#6ab060",
                               WEATHER, fc.weather("#5a9ae0", "#d8eaf8", "#e8f0f8", (70, 260), 0.3, "#fff4e0",
                                                   sun="#fff8e8"), "11:00")
    lang().write(LANG)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(p, t), encoding="utf-8")
    print(f"Pic de Sunqua : {sum(counts.values())} blocs et {len(p.fluids)} cases de fluide en {len(counts)} tronçons, "
          f"{len(roles())} rôles, {len(PARTICLE_SYSTEMS)} particules")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        preview_images(p, preview)


if __name__ == "__main__":
    main()
