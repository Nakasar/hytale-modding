#!/usr/bin/env python3
"""Nouveaux types de quêtes du mod Peuples d'Orbis (Kevin, 15 novembre 2026) : caravane, récolte escortée,
destruction et boss, pour les cinq peuples.

Écrit :
  * les PNJ escortés de chaque peuple, copies du captif (suit le joueur le plus proche, ne se bat pas) :
    Nakasar_Peuples_<Peuple>_Caravaneer et Nakasar_Peuples_<Peuple>_Gatherer, apparences vanilla du peuple ;
  * les chefs des demandes de boss, Nakasar_Peuples_Boss_<Peuple> : apparence, attaques et butin vanilla (chef de guerre
    trork, grizzli, colosse des sables, yéti, ours dévoré par le Vide), sur le modèle des pillards de raid
    (generate_raids.raider) : ils gardent leur repaire (point d'attache) et frappent à vue. Les coups annoncés, les
    renforts et la barre de vie sont en Java (boss/QuestBosses, boss/QuestBossBar) ;
  * les zones d'annonce rouges des chefs (Server/Particles/Nakasar/Peuples/Warnings), copie de
    nakasar-fractals/tools/generate_warnings.py avec les ids préfixés Nakasar_Peuples_ et seulement les formes en usage
    (cercle, ligne 14 × 3, cône de 90°), et boss/WarningShapes.java ;
  * les vingt modèles de demande (Server/Nakasar/Requests/<Peuple>/<Peuple>_{Caravan,Harvest,Destroy,Boss}_*.json) ;
  * le bloc « Quêtes » des fichiers .lang fr-FR et en-US (entre deux marqueurs, réécrit à chaque passage).

Règles d'AGENTS.md : aucun de ces PNJ ne se soigne (pas de SetStat Health ; VillageNoRegenSystem coupe la régénération
vanilla) ; tout est vanilla (apparences, attaques, butins, blocs à détruire, textures des zones sauf le secteur de 90°,
dessiné comme celui des fractales) ; les zones rouges ont la taille des coups (constantes de QuestBosses ci-dessous).

    python3 tools/generate_quests.py
"""
import copy
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import generate_raids as gr  # noqa: E402

ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
REQUESTS = RES / "Nakasar/Requests"
PARTICLES = RES / "Particles/Nakasar/Peuples/Warnings"
TEXTURES = ROOT / "src/main/resources/Common/Particles/Textures/Nakasar/Peuples"
JAVA = ROOT / "src/main/java/dev/nakasar/hytale/peuples/boss/WarningShapes.java"
TITLE_MAX = 24
LANG_BEGIN = "# ---- Quêtes : caravane, récolte escortée, destruction, boss (généré par tools/generate_quests.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin des quêtes ----"

# Mêmes valeurs que boss/QuestBosses.java (la zone rouge et le test de touche viennent de ces constantes).
# Quête « Baliser une route » : mêmes valeurs que annex/Routes.java (BEACON) ; villages voisins à 700 blocs au plus
# (une balise tous les 32 blocs : une vingtaine de balises).
BEACON = "Nakasar_Peuples_Route_Beacon"
ROUTE_KIT = 4
ROUTE_MAX = 700
ROUTE_TEXT = ("Baliser une route", "Mark out a road",
              "Relie {place} par des balises de route, à 32 blocs au plus l'une de l'autre : encore {gap} blocs à baliser. "
              "{place} : {distance} blocs, {direction}.",
              "Link {place} with road beacons, at most 32 blocks apart: {gap} more blocks to mark out. "
              "{place}: {distance} blocks, {direction}.")

LINE_LENGTH = 14
LINE_WIDTH = 3
CONE_DEGREES = 90

FR = {}
EN = {}


def t(key, fr, en):
    FR[key] = fr
    EN[key] = en


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


R = "Nakasar_Peuples_Raider_"

# Peuple -> apparences des PNJ escortés, assaillants (embuscades, gardes, renforts), boss, récolte, cible à détruire.
PEOPLES = {
    "Kweebec": {
        "caravaneer": "Kweebec_Rootling", "gatherer": "Kweebec_Sapling_Green",
        "foes": [R + "Trork_Warrior", R + "Trork_Warrior", R + "Trork_Brawler"],
        "boss": ("Trork_Chieftain", "Weapon_Battleaxe_Stone_Trork", "Drop_Trork_Chieftain", 700, 30, 4.6,
                 ["Trork_Chieftain_Battleaxe_Swing_Left", "Trork_Chieftain_Battleaxe_Swing_Right",
                  "Trork_Chieftain_Battleaxe_Swing_Down"], 3.0, None),
        "harvest": ("Plant_Fruit_Berries_Red", 12),
        "destroy": ("Furniture_Crude_Brazier", 5),
    },
    "Trork": {
        "caravaneer": "Trork", "gatherer": "Trork_Hunter",
        "foes": [R + "Trork_Warrior", R + "Trork_Mauler", R + "Trork_Brawler"],
        "boss": ("Bear_Grizzly", None, "Drop_Bear_Grizzly", 650, 28, 5.2, ["Root_NPC_Bear_Grizzly_Attack"], 2.8, None),
        "harvest": ("Wood_Oak_Trunk", 12),
        "destroy": ("Deco_Trork_Cage", 4),
    },
    "Feran": {
        "caravaneer": "Feran_Civilian", "gatherer": "Feran_Burrower",
        "foes": [R + "Scarak_Fighter", R + "Scarak_Fighter", R + "Scarak_Louse"],
        "boss": ("Golem_Crystal_Sand", None, "Drop_Golem_Crystal_Sand", 800, 30, 4.4, ["Root_NPC_Golem_Crystal_Attack"], 2.6,
                 "golem"),
        "harvest": ("Plant_Cactus_1", 8),
        "destroy": ("Deco_Scarak_Eggsacks", 5),
    },
    "Renonce": {
        "caravaneer": "Outlander_Peon", "gatherer": "Outlander_Peon",
        "foes": [R + "Cult_Cultist", R + "Cult_Berserker", R + "Cult_Cultist"],
        "boss": ("Yeti", None, "Drop_Yeti", 750, 30, 5.0, ["Root_NPC_Yeti_Attack"], 3.25, None),
        "harvest": ("Wood_Fir_Trunk", 12),
        "destroy": ("Furniture_Outlander_Banner", 5),
    },
    "Slothian": {
        "caravaneer": "Slothian_Villager", "gatherer": "Slothian_Villager",
        "foes": [R + "Void_Larva", R + "Void_Larva", R + "Void_Crawler"],
        "boss": ("Bear_Grizzly_Voidtaken", None, "Drop_Bear_Grizzly", 850, 30, 5.0, ["Root_NPC_Bear_Grizzly_Attack"], 2.8, None),
        "harvest": ("Soil_Ash", 16),
        "destroy": ("Rock_Crystal_Void_Large", 5),
    },
}

GOLEM_VARS = ["Swing_Left", "Swing_Right", "Spin", "Ground_Slam", "Stomp", "Spin_Heavy", "Clap"]


# ----------------------------------------------------------------------------------------------------------------------
# PNJ
# ----------------------------------------------------------------------------------------------------------------------

def escorted(pid, kind, look, hp, follow):
    src = json.loads((ROLES / "Nakasar_Peuples_Kweebec_Captive.json").read_text(encoding="utf-8"))
    doc = copy.deepcopy(src)
    what = "Caravanier" if kind == "Caravaneer" else "Cueilleur"
    doc.pop("$Comment", None)
    doc["Appearance"] = look
    doc["NameTranslationKey"] = f"nakasar_peuples.npc.{pid}_{kind}.name"
    doc["MaxHealth"] = hp
    # Il suit le joueur le plus proche (comme le captif), d'un peu plus loin.
    for inst in doc["Instructions"][0]["Instructions"]:
        sensor = inst.get("Sensor", {})
        if sensor.get("Type") == "Player":
            sensor["Range"] = follow
    comment = (f"{what} {pid} d'une demande de {'caravane' if kind == 'Caravaneer' else 'récolte escortée'}, généré par "
               f"tools/generate_quests.py : copie du captif kweebec sur l'apparence vanilla {look}. Posé par "
               f"request/Expeditions au cœur du village ; il suit le joueur le plus proche à moins de {follow} blocs "
               "et ne se bat pas. Les assaillants de sa demande le visent (RaidAttitudeSystem). Ne régénère jamais "
               "(VillageNoRegenSystem).")
    write(ROLES / f"Nakasar_Peuples_{pid}_{kind}.json", {"$Comment": comment, **doc})


def boss(pid, spec):
    look, weapon, drops, hp, dmg, speed, swings, reach, kit = spec["boss"]
    _, doc = gr.raider("Boss_" + pid, look, weapon or "Weapon_Club_Crude", drops, hp, dmg, speed)
    doc["$Comment"] = (f"Chef de la demande de boss {pid}, généré par tools/generate_quests.py : apparence, attaques et "
                       f"butin vanilla ({look}), comportement des pillards de raid (generate_raids.raider). Posé par "
                       "request/Expeditions dans son repaire (point d'attache) ; ses coups annoncés, ses renforts et sa "
                       "barre de vie sont en Java (boss/QuestBosses, boss/QuestBossBar). Ne se soigne jamais.")
    doc["NameTranslationKey"] = f"nakasar_peuples.npc.Boss_{pid}.name"
    doc["KnockbackScale"] = 0.2
    if weapon is None:
        doc.pop("HotbarItems", None)
    if kit == "golem":
        doc["InteractionVars"] = {f"{v}_Damage": {"Interactions": [{
            "Parent": f"Golem_Crystal_{v}_Damage",
            "DamageCalculator": {"Type": "Absolute", "BaseDamage": {"Physical": dmg}, "RandomPercentageModifier": 0.1},
            "DamageEffects": {"Knockback": {"Force": -10}}}]} for v in GOLEM_VARS}

    def walk(node):
        if isinstance(node, dict):
            insts = node.get("Instructions")
            if isinstance(insts, list):
                for i, inst in enumerate(insts):
                    if isinstance(inst, dict) and any(isinstance(a, dict) and a.get("Type") == "Attack"
                                                      for a in inst.get("Actions", [])):
                        insts[i] = gr.attack_instruction(swings, reach, [1.0, 1.6])
                    else:
                        walk(inst)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(doc)
    write(ROLES / f"Nakasar_Peuples_Boss_{pid}.json", {"$Comment": doc.pop("$Comment"), **doc})


# ----------------------------------------------------------------------------------------------------------------------
# Modèles de demande
# ----------------------------------------------------------------------------------------------------------------------

def request(pid, tid, kind, extra, min_tier, essor, favors):
    doc = {
        "$Comment": f"Demande du tableau d'un village {pid} ({kind}), générée par tools/generate_quests.py : voir "
                    "RequestTemplate et request/Expeditions.",
        "People": pid,
        "Type": kind,
        "MinTier": min_tier,
        "MaxTier": 3,
        "Weight": 1,
        "TitleKey": f"nakasar_peuples.request.{tid}.title",
        "TaskKey": f"nakasar_peuples.request.{tid}.task",
    }
    doc.update(extra)
    doc.update({"Essor": essor, "Favors": favors})
    write(REQUESTS / pid / f"{tid}.json", doc)


def requests(pid, spec):
    foes = spec["foes"]
    request(pid, f"{pid}_Caravan_Trade", "Caravan",
            {"Members": 3, "Waves": 3, "Spawns": foes, "MinDistance": 150, "MaxDistance": 2400}, 1, 35, 6)
    item, qty = spec["harvest"]
    request(pid, f"{pid}_Harvest_Escort", "Harvest",
            {"Members": 3, "Waves": 2, "Duration": 60, "Spawns": foes[:2], "ItemId": item, "Quantity": qty,
             "MinDistance": 60, "MaxDistance": 110}, 0, 20, 3)
    block, count = spec["destroy"]
    request(pid, f"{pid}_Destroy_Camp", "Destroy",
            {"TargetBlock": block, "Quantity": count, "Spawns": foes, "MinDistance": 90, "MaxDistance": 150}, 0, 20, 3)
    request(pid, f"{pid}_Boss_Lair", "Boss",
            {"Boss": f"Nakasar_Peuples_Boss_{pid}", "Spawns": foes[:2], "MinDistance": 110, "MaxDistance": 170}, 1, 40, 8)
    # Baliser une route (Kevin, 15 novembre 2026) : vers un avant-poste du village ou un village voisin pas encore relié
    # (request/RouteQuests). Le village donne des balises pour commencer (ItemId × Quantity).
    request(pid, f"{pid}_Route_Build", "Route",
            {"ItemId": BEACON, "Quantity": ROUTE_KIT, "MinDistance": 48, "MaxDistance": ROUTE_MAX}, 0, 25, 4)
    REQUEST_TEXTS[f"{pid}_Route_Build"] = ROUTE_TEXT


# ----------------------------------------------------------------------------------------------------------------------
# Zones d'annonce (copie de nakasar-fractals/tools/generate_warnings.py)
# ----------------------------------------------------------------------------------------------------------------------

SCALE = 0.68
BASE = 6.25
RED = "#ff0000"
EDGE_OPACITY = 0.5
FILL_OPACITY = 0.75
EDGE_PULSE = {0: 0, 15: 1, 30: 0.25, 45: 1, 60: 0.25, 75: 1, 90: 0.25, 95: 0.25, 100: 0}
FILL_PULSE = {0: 0, 15: 1, 30: 0.5, 45: 1, 60: 0.5, 75: 1, 90: 0.5, 95: 0.5, 97: 0.5, 100: 0}
HIT = 97
PREFIX = "Nakasar_Peuples_Warning_"
LINE_PREFIX = "Nakasar_Peuples_Line_"
SECTOR_PREFIX = "Nakasar_Peuples_Sector_"
WARNING_TENTHS = range(5, 61)
SHAPE_TENTHS = range(5, 31)
LINE_SCALE = SCALE / 2
LINE_TEXTURE = "Particles/Textures/Indicators/Warning_Square_Base.png"
SECTOR_TEXTURE = "Particles/Textures/Nakasar/Peuples/Warning_Sector"
FORWARD = {"X": {"Min": 90, "Max": 90}, "Y": {"Min": 180, "Max": 180}}


def _spawner(life, texture, animation, initial):
    return {
        "RenderMode": "BlendLinear",
        "ParticleRotationInfluence": "Velocity",
        "ParticleLifeSpan": {"Min": life, "Max": life},
        "ParticleRotateWithSpawner": True,
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "Particle": {
            "Texture": texture,
            "ScaleRatioConstraint": "OneToOne",
            "UVOption": "None",
            "Animation": animation,
            "SoftParticles": "Disable",
            "InitialAnimationFrame": initial,
        },
        "Shape": "Sphere",
        "TotalParticles": {"Min": 1, "Max": 1},
        "SpawnRate": {"Min": 1, "Max": 1},
        "LinearFiltering": True,
        "MaxConcurrentParticles": 1,
        "InitialVelocity": {"Speed": {"Min": 0.01, "Max": 0.01}},
        "SpawnBurst": True,
    }


def _edge_animation():
    return {str(k): {"Opacity": v, "Color": RED} for k, v in EDGE_PULSE.items()}


def _fill_animation(start, full):
    frames = {}
    for k, v in FILL_PULSE.items():
        frame = {"Opacity": v, "Color": RED}
        if k == 0:
            frame["Scale"] = start
        elif k >= HIT:
            frame["Scale"] = full
        frames[str(k)] = frame
    return frames


def _initial(opacity, rotation, scale):
    return {"Opacity": opacity, "Color": RED, "Rotation": rotation, "Scale": scale}


def _xy(x, y):
    return {"X": {"Min": x, "Max": x}, "Y": {"Min": y, "Max": y}}


def _system(name, comment):
    return {
        "$Comment": f"{comment}, posé par boss.Telegraphs. Généré par tools/generate_quests.py.",
        "Spawners": [{"SpawnerId": f"{name}_Edge", "PositionOffset": {"Y": 0.03}},
                     {"SpawnerId": f"{name}_Fill", "PositionOffset": {"Y": 0.02}}],
        "CullDistance": 96,
        "IsImportant": True,
    }


def _circle_files(tn):
    life = tn / 10
    flat = {"X": {"Min": 90, "Max": 90}}
    edge = _spawner(life, "Particles/Textures/Indicators/Warning_Circle_Base.png", _edge_animation(),
                    _initial(EDGE_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png",
                    _fill_animation({"X": {"Min": 0.05, "Max": 0.05}}, {"X": {"Min": 1, "Max": 1}}),
                    _initial(FILL_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
    name = f"{PREFIX}{tn}"
    return {f"{name}.particlesystem": _system(name, f"Cercle d'annonce de {life:g} s"),
            f"{name}_Edge.particlespawner": edge, f"{name}_Fill.particlespawner": fill}


def _shape_spawner(life, texture, animation, initial, constraint):
    spawner = _spawner(life, texture, animation, initial)
    spawner["ParticleRotationInfluence"] = "None"
    spawner["Particle"]["ScaleRatioConstraint"] = constraint
    return spawner


def _line_files(aspect, tn):
    life = tn / 10
    size = _xy(BASE, 2 * aspect / 10 * BASE)
    edge = _shape_spawner(life, LINE_TEXTURE, _edge_animation(), _initial(EDGE_OPACITY, FORWARD, size), "None")
    fill = _shape_spawner(life, LINE_TEXTURE, _fill_animation(_xy(1, 0.02), _xy(1, 1)),
                          _initial(FILL_OPACITY, FORWARD, size), "None")
    name = f"{LINE_PREFIX}{aspect}_{tn}"
    return {f"{name}.particlesystem": _system(name, f"Ligne d'annonce rectangulaire ({life:g} s)"),
            f"{name}_Edge.particlespawner": edge, f"{name}_Fill.particlespawner": fill}


def _sector_files(angle, tn):
    life = tn / 10
    texture = f"{SECTOR_TEXTURE}_{angle}"
    size = {"X": {"Min": BASE, "Max": BASE}}
    edge = _shape_spawner(life, texture + "_Base.png", _edge_animation(), _initial(EDGE_OPACITY, FORWARD, size), "OneToOne")
    fill = _shape_spawner(life, texture + "_Fill.png",
                          _fill_animation({"X": {"Min": 0.03, "Max": 0.03}}, {"X": {"Min": 1, "Max": 1}}),
                          _initial(FILL_OPACITY, FORWARD, size), "OneToOne")
    name = f"{SECTOR_PREFIX}{angle}_{tn}"
    return {f"{name}.particlesystem": _system(name, f"Cône d'annonce de {angle}° ({life:g} s)"),
            f"{name}_Edge.particlespawner": edge, f"{name}_Fill.particlespawner": fill}


TEX = 256
TEX_EDGE = 5


def _sector_textures(angle):
    from PIL import Image
    base = Image.new("RGBA", (TEX, TEX), (255, 255, 255, 0))
    fill = Image.new("RGBA", (TEX, TEX), (255, 255, 255, 0))
    c = TEX / 2
    r_max = c - 2
    half = math.radians(angle) / 2
    for y in range(TEX):
        for x in range(TEX):
            dx, dy = x + 0.5 - c, c - (y + 0.5)
            r = math.hypot(dx, dy)
            if r > r_max:
                continue
            off = abs(math.atan2(dx, dy))
            if off > half:
                continue
            side = r * math.sin(half - off) if half - off < math.pi / 2 else r
            edge = min(r_max - r, side)
            k = r / r_max
            base.putpixel((x, y), (255, 255, 255, 235 if edge < TEX_EDGE else int(25 + 45 * k)))
            fill.putpixel((x, y), (255, 255, 255, int(40 + 130 * k)))
    return base, fill


def warnings():
    aspect = max(5, int(round(10 * LINE_LENGTH / LINE_WIDTH)))
    files = {}
    for tn in WARNING_TENTHS:
        files.update(_circle_files(tn))
    for tn in SHAPE_TENTHS:
        files.update(_line_files(aspect, tn))
        files.update(_sector_files(CONE_DEGREES, tn))
    PARTICLES.mkdir(parents=True, exist_ok=True)
    for old in PARTICLES.iterdir():
        if old.name not in files:
            old.unlink()
    for fname, doc in files.items():
        (PARTICLES / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    TEXTURES.mkdir(parents=True, exist_ok=True)
    b, f = _sector_textures(CONE_DEGREES)
    b.save(TEXTURES / f"Warning_Sector_{CONE_DEGREES}_Base.png")
    f.save(TEXTURES / f"Warning_Sector_{CONE_DEGREES}_Fill.png")
    JAVA.write_text(f"""package dev.nakasar.hytale.peuples.boss;

/**
 * Formes d'annonce dont les particules existent (tools/generate_quests.py, qui écrit ce fichier) : rapports
 * longueur/largeur des lignes en dixièmes ({{@code Nakasar_Peuples_Line_<rapport>_<dixièmes>}}) et angles des cônes en
 * degrés ({{@code Nakasar_Peuples_Sector_<angle>_<dixièmes>}}), pour des durées de {{@link #MIN_TENTHS}} à
 * {{@link #MAX_TENTHS}} dixièmes de seconde.
 */
final class WarningShapes {{

    static final int[] LINE_ASPECTS = {{{aspect}}};
    static final int[] SECTOR_ANGLES = {{{CONE_DEGREES}}};
    static final int MIN_TENTHS = {SHAPE_TENTHS.start};
    static final int MAX_TENTHS = {SHAPE_TENTHS.stop - 1};
    /** Échelle de particule d'une ligne par bloc de largeur. */
    static final float LINE_SCALE = {LINE_SCALE}f;

    private WarningShapes() {{
    }}
}}
""", encoding="utf-8")
    return len(files)


# ----------------------------------------------------------------------------------------------------------------------
# Textes
# ----------------------------------------------------------------------------------------------------------------------

NAMES = {
    "Kweebec": {"Caravaneer": ("Caravanier kweebec", "Kweebec caravaneer"), "Gatherer": ("Cueilleur kweebec", "Kweebec gatherer"),
                "Boss": ("Chef de guerre trork", "Trork warchief")},
    "Trork": {"Caravaneer": ("Porteur trork", "Trork porter"), "Gatherer": ("Bûcheron trork", "Trork woodcutter"),
              "Boss": ("Grand grizzli", "Great grizzly")},
    "Feran": {"Caravaneer": ("Caravanière feran", "Feran caravaneer"), "Gatherer": ("Glaneur feran", "Feran gleaner"),
              "Boss": ("Colosse des sables", "Sand colossus")},
    "Renonce": {"Caravaneer": ("Convoyeur renoncé", "Forsworn carter"), "Gatherer": ("Bûcheron renoncé", "Forsworn woodcutter"),
                "Boss": ("Yéti des cimes", "Peak yeti")},
    "Slothian": {"Caravaneer": ("Pèlerin slothian", "Slothian pilgrim"), "Gatherer": ("Ramasseur slothian", "Slothian collector"),
                 "Boss": ("Ours dévoré par le Vide", "Voidtaken bear")},
}

# (titre fr, titre en, tâche fr, tâche en) par modèle.
REQUEST_TEXTS = {
    "Kweebec_Caravan_Trade": ("Escorter la caravane", "Escort the caravan",
                              "Mène la caravane jusqu'à {village} : {distance} blocs, {direction}. Caravaniers : {count}/{needed}.",
                              "Lead the caravan to {village}: {distance} blocks, {direction}. Caravaneers: {count}/{needed}."),
    "Kweebec_Harvest_Escort": ("Escorter les cueilleurs", "Escort the gatherers",
                               "Mène les cueilleurs aux buissons de baies : {distance} blocs, {direction}.",
                               "Lead the gatherers to the berry bushes: {distance} blocks, {direction}."),
    "Kweebec_Destroy_Camp": ("Briser les braseros", "Smash the braziers",
                             "Brise les braseros de guerre des Trorks ({count}/{needed}) : {distance} blocs, {direction}.",
                             "Smash the Trork war braziers ({count}/{needed}): {distance} blocks, {direction}."),
    "Kweebec_Boss_Lair": ("Abattre le chef trork", "Slay the Trork chief",
                          "Le chef de guerre trork t'attend dans son repaire : {distance} blocs, {direction}.",
                          "The Trork warchief awaits in his lair: {distance} blocks, {direction}."),
    "Trork_Caravan_Trade": ("Escorter les porteurs", "Escort the porters",
                            "Mène les porteurs jusqu'à {village} : {distance} blocs, {direction}. Porteurs : {count}/{needed}.",
                            "Lead the porters to {village}: {distance} blocks, {direction}. Porters: {count}/{needed}."),
    "Trork_Harvest_Escort": ("Escorter les bûcherons", "Escort the woodcutters",
                             "Mène les bûcherons à la coupe : {distance} blocs, {direction}. Le clan rival rôde.",
                             "Lead the woodcutters to the felling site: {distance} blocks, {direction}. The rival clan prowls."),
    "Trork_Destroy_Camp": ("Briser les cages", "Break the cages",
                           "Brise les cages du clan rival ({count}/{needed}) : {distance} blocs, {direction}.",
                           "Break the rival clan's cages ({count}/{needed}): {distance} blocks, {direction}."),
    "Trork_Boss_Lair": ("Abattre le grand grizzli", "Slay the great grizzly",
                        "Le grand grizzli a sa tanière non loin : {distance} blocs, {direction}.",
                        "The great grizzly has its den nearby: {distance} blocks, {direction}."),
    "Feran_Caravan_Trade": ("Escorter la caravane", "Escort the caravan",
                            "Mène la caravane jusqu'à {village} : {distance} blocs, {direction}. Caravanières : {count}/{needed}.",
                            "Lead the caravan to {village}: {distance} blocks, {direction}. Caravaneers: {count}/{needed}."),
    "Feran_Harvest_Escort": ("Escorter les glaneurs", "Escort the gleaners",
                             "Mène les glaneurs aux cactus : {distance} blocs, {direction}.",
                             "Lead the gleaners to the cacti: {distance} blocks, {direction}."),
    "Feran_Destroy_Camp": ("Détruire les couvées", "Destroy the broods",
                           "Détruis les couvées scaraks ({count}/{needed}) : {distance} blocs, {direction}.",
                           "Destroy the Scarak broods ({count}/{needed}): {distance} blocks, {direction}."),
    "Feran_Boss_Lair": ("Abattre le colosse", "Slay the colossus",
                        "Un colosse des sables s'est levé dans les dunes : {distance} blocs, {direction}.",
                        "A sand colossus has risen in the dunes: {distance} blocks, {direction}."),
    "Renonce_Caravan_Trade": ("Escorter le convoi", "Escort the convoy",
                              "Mène le convoi jusqu'à {village} : {distance} blocs, {direction}. Convoyeurs : {count}/{needed}.",
                              "Lead the convoy to {village}: {distance} blocks, {direction}. Carters: {count}/{needed}."),
    "Renonce_Harvest_Escort": ("Escorter les bûcherons", "Escort the woodcutters",
                               "Mène les bûcherons aux sapins : {distance} blocs, {direction}.",
                               "Lead the woodcutters to the firs: {distance} blocks, {direction}."),
    "Renonce_Destroy_Camp": ("Abattre les bannières", "Tear down the banners",
                             "Abats les bannières du culte ({count}/{needed}) : {distance} blocs, {direction}.",
                             "Tear down the cult banners ({count}/{needed}): {distance} blocks, {direction}."),
    "Renonce_Boss_Lair": ("Abattre le yéti", "Slay the yeti",
                          "Le yéti des cimes est descendu jusqu'ici : {distance} blocs, {direction}.",
                          "The peak yeti has come down this far: {distance} blocks, {direction}."),
    "Slothian_Caravan_Trade": ("Escorter les pèlerins", "Escort the pilgrims",
                               "Mène les pèlerins jusqu'à {village} : {distance} blocs, {direction}. Pèlerins : {count}/{needed}.",
                               "Lead the pilgrims to {village}: {distance} blocks, {direction}. Pilgrims: {count}/{needed}."),
    "Slothian_Harvest_Escort": ("Escorter les ramasseurs", "Escort the collectors",
                                "Mène les ramasseurs aux champs de cendre : {distance} blocs, {direction}.",
                                "Lead the collectors to the ash fields: {distance} blocks, {direction}."),
    "Slothian_Destroy_Camp": ("Briser les cristaux", "Shatter the crystals",
                              "Brise les cristaux du Vide ({count}/{needed}) : {distance} blocs, {direction}.",
                              "Shatter the Void crystals ({count}/{needed}): {distance} blocks, {direction}."),
    "Slothian_Boss_Lair": ("Abattre l'ours du Vide", "Slay the Void bear",
                           "Un ours dévoré par le Vide rôde au bord du gouffre : {distance} blocs, {direction}.",
                           "A Voidtaken bear prowls at the chasm's edge: {distance} blocks, {direction}."),
}


def texts():
    t("request.type.Caravan", "Caravane", "Caravan")
    t("request.type.Harvest", "Récolte escortée", "Escorted harvest")
    t("request.type.Destroy", "Destruction", "Sabotage")
    t("request.type.Boss", "Chef", "Boss")
    t("request.type.Route", "Route", "Road")
    r = "request."
    t(r + "caravan.noDestination", "Aucun autre village ami n'est assez proche pour une caravane.",
      "No other friendly village is close enough for a caravan.")
    t(r + "caravan.start", "La caravane part : {count} caravaniers te suivent jusqu'à {village}. Reste près d'eux.",
      "The caravan sets off: {count} caravaneers follow you to {village}. Stay close to them.")
    t(r + "caravan.destReason", "caravane menée à bon port", "caravan brought in safely")
    t(r + "caravan.lost", "Toute la caravane est tombée : « {title} » échoue.", "The whole caravan has fallen: \"{title}\" fails.")
    t(r + "caravan.memberLost", "Un caravanier est tombé ! Il en reste {count}.", "A caravaneer has fallen! {count} left.")
    t(r + "harvest.start", "{count} cueilleurs te suivent : mène-les au lieu de récolte.",
      "{count} gatherers follow you: lead them to the harvest site.")
    t(r + "harvest.begin", "Les cueilleurs se mettent au travail : protège-les pendant {seconds} s, sans t'éloigner.",
      "The gatherers get to work: protect them for {seconds} s, and stay close.")
    t(r + "harvest.working", "Protège les cueilleurs : récolte {count}/{needed} s.",
      "Protect the gatherers: harvest {count}/{needed} s.")
    t(r + "harvest.full", "Les paniers sont pleins ! Ramène les cueilleurs au village.",
      "The baskets are full! Bring the gatherers back to the village.")
    t(r + "harvest.home", "Ramène les cueilleurs au cœur du village : {distance} blocs, {direction}.",
      "Bring the gatherers back to the village heart: {distance} blocks, {direction}.")
    t(r + "harvest.lost", "Tous les cueilleurs sont tombés : « {title} » échoue.", "All the gatherers have fallen: \"{title}\" fails.")
    t(r + "harvest.memberLost", "Un cueilleur est tombé ! Il en reste {count}.", "A gatherer has fallen! {count} left.")
    t(r + "group.behind", "Ton escorte t'attend en arrière : {distance} blocs, {direction}.",
      "Your escort is waiting behind you: {distance} blocks, {direction}.")
    t(r + "ambush", "Embuscade ! {count} assaillants surgissent.", "Ambush! {count} attackers burst out.")
    t(r + "destroy.found", "{count} × {item} à briser ici. Leurs gardes ne sont pas loin.",
      "{count} × {item} to smash here. Their guards are not far.")
    t(r + "boss.found", "Le chef est là : « {title} ». Sors des zones rouges avant le coup.",
      "The boss is here: \"{title}\". Leave the red zones before the blow.")
    t(r + "boss.summon", "Le chef appelle ses renforts ! Il ne prend aucun coup tant qu'ils vivent.",
      "The boss calls for reinforcements! It takes no damage while they live.")
    t(r + "route.noTarget", "Tous les avant-postes et villages voisins sont déjà reliés par une route.",
      "Every outpost and neighbouring village is already linked by a road.")
    t(r + "route.kit", "Le village te confie {count} balises de route pour commencer.",
      "The village hands you {count} road beacons to start with.")
    t(r + "route.progress", "Route vers {place} : encore {gap} blocs à baliser.",
      "Road to {place}: {gap} more blocks to mark out.")
    t(r + "route.done", "La route vers {place} est complète !", "The road to {place} is complete!")
    t(r + "route.gone", "Il n'y a plus rien à relier : « {title} » s'arrête.",
      "There is nothing left to link: \"{title}\" ends.")
    t(r + "boss.unshielded", "Ses renforts sont tombés : le chef est de nouveau vulnérable.",
      "Its reinforcements have fallen: the boss is vulnerable again.")
    for pid, names in NAMES.items():
        for kind, (fr, en) in names.items():
            key = f"npc.Boss_{pid}.name" if kind == "Boss" else f"npc.{pid}_{kind}.name"
            t(key, fr, en)
    for tid, (tf, te, kf, ke) in REQUEST_TEXTS.items():
        for title in (tf, te):
            if len(title) > TITLE_MAX:
                raise SystemExit(f"titre trop long ({len(title)} > {TITLE_MAX}) : {title}")
        t(f"request.{tid}.title", tf, te)
        t(f"request.{tid}.task", kf, ke)


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        before, after = "", text
        if LANG_BEGIN in text:
            # Le bloc reste à sa place dans le fichier (diff minimal).
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            text = before + after
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc des quêtes) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text(before + "\n".join(block) + after, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés des quêtes")


def main():
    for pid, spec in PEOPLES.items():
        escorted(pid, "Caravaneer", spec["caravaneer"], 150, 18)
        escorted(pid, "Gatherer", spec["gatherer"], 120, 16)
        boss(pid, spec)
        requests(pid, spec)
    n = warnings()
    texts()
    write_langs()
    print(f"{len(PEOPLES) * 3} rôles, {len(PEOPLES) * 5} demandes, {n} fichiers de zones d'annonce")


if __name__ == "__main__":
    main()
