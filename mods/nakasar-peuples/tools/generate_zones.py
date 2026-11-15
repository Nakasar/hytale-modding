#!/usr/bin/env python3
"""Zones 2 et 3 du mod Peuples d'Orbis (étape 8 du plan d'implémentation).

GDD, Progression des zones : zone 2 = Feran (amis) contre Scaraks (ruche), soif le jour ; zone 3 = Outlanders renoncés
(id « Renonce ») contre le culte, froid. Ce script écrit, pour chacun des deux peuples, tout ce que les Kweebecs ont
reçu aux étapes 2 à 6, à partir des mêmes fonctions :

  * le plan du village (Server/Nakasar/VillageLayouts/Feran_Oasis.json, Renonce_Givre.json ; prefabs vanilla
    Npc/Feran/* et Npc/Outlander/{Houses,Towers,Totems,Boats,Misc} sans marqueur d'apparition hostile) ;
  * les PNJ (crieur, guetteur, captif, marchand, chef, garde de raid, villageois à métier) sur des modèles vanilla
    (Server/Models/Intelligent/{Feran,Outlander}) ;
  * les dialogues (crieur, marchand, chef avec la chaîne du peuple, métiers) ;
  * les demandes du tableau et les étapes de chaîne (Server/Nakasar/Requests/<Peuple>) ;
  * les échoppes de troc, la faveur, la missive, le tableau, la bannière (et son icône de carte) ;
  * les groupes de PNJ et de réputation ;
  * les assaillants des raids (Scaraks, culte) et leur évènement de monde, leurs trophées ;
  * les objets de passage et de climat (Outre d'oasis, Bracelet de vent, Manteau du givre), les effets de soif et
    d'hypothermie (icônes copiées de la fractale Tempête de neige), la cause de dégâts du froid ;
  * le bloc « étape 8 » en tête des fichiers .lang fr-FR et en-US (entre deux marqueurs, réécrit à chaque passage).

Titres des demandes : courts (Kevin, 14 novembre 2026 : « tous les titres doivent tenir et ne pas être coupés » dans
le suivi d'objectifs du HUD), {@value TITLE_MAX} caractères au plus, vérifié ici.

Règle n° 1 (AGENTS.md) : aucun PNJ ne se soigne. Règle n° 2 : modèles, armes, attaques, butins, prefabs, sons vanilla.

    python3 tools/generate_zones.py [--preview /mnt/project-files/peuples/zones]
"""
import argparse
import copy
import json
import math
import shutil
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import generate_raids as gr  # noqa: E402
import generate_village_layouts as gl  # noqa: E402
import generate_villagers as gv  # noqa: E402

ROOT = TOOLS.parent
RES = ROOT / "src/main/resources/Server"
COMMON = ROOT / "src/main/resources/Common"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
ITEMS = RES / "Item/Items/Nakasar/Peuples"
FRACTAL_ICONS = ROOT.parent / "nakasar-fractals/src/main/resources/Common/UI/StatusEffects/Nakasar/Fractals"
STATUS_ICONS = COMMON / "UI/StatusEffects/Nakasar/Peuples"
TITLE_MAX = 24
LANG_BEGIN = "# ---- Étape 8 : zones 2 et 3 (généré par tools/generate_zones.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin de l'étape 8 ----"

FR = {}
EN = {}


def t(key, fr, en):
    """Une clé de traduction (sans le préfixe nakasar_peuples.)."""
    FR[key] = fr
    EN[key] = en


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------------------------------------------------
# Peuples
# ----------------------------------------------------------------------------------------------------------------------

FERAN_T1 = "Npc/Feran/Tier1/"
FERAN_T2 = "Npc/Feran/Tier2/"
FERAN_T3 = "Npc/Feran/Tier3/"
OASIS = "Npc/Feran/Portals_Oasis/"
OUT = "Npc/Outlander/"

PEOPLES = {
    "Feran": {
        "name": ("Feran", "Feran"),
        "adj": ("feran", "Feran"),
        "layout": "Feran_Oasis",
        "layout_spec": {
            "People": "Feran",
            "PlazaRadius": 6,
            "Banner": (0, -4),
            "Buildings": [
                # Palier 0 : deux huttes, le muret du vent.
                ("Hutte_Ouest", 0, FERAN_T3 + "Huts/Feran_Tier3_Huts_001", -16, 0, 0),
                ("Hutte_Est", 0, FERAN_T3 + "Huts/Feran_Tier3_Huts_001", 16, 0, 2),
                ("Muret_Du_Vent", 0, FERAN_T3 + "Walls/Feran_Tier3_Walls_001", 0, -16, 0),
                # Palier 1 : la grande hutte, l'entrée de l'oasis, une hutte au sud.
                ("Grande_Hutte", 1, FERAN_T2 + "Hut/Feran_Tier2_Hut_001", -32, 22, 0),
                ("Entree_Oasis", 1, FERAN_T2 + "Entrance/Feran_Tier2_Entrance_001", 0, 22, 0),
                ("Hutte_Sud", 1, FERAN_T3 + "Huts/Feran_Tier3_Huts_001", 18, 22, 0),
                # Bâtiments de métier, étape 3 : l'enclos de l'oasis (enclos du mod en blocs vanilla, barrière au sud).
                ("Enclos_Oasis", 1, gl.PEN + "Feran_Pen", -13, -20, 0),
                # Palier 2 : hutte du nord-ouest, hutte sur pilier, hutte du sud-est.
                ("Hutte_Nord_Ouest", 2, FERAN_T2 + "Hut/Feran_Tier2_Hut_002", -32, -24, 0),
                ("Hutte_Pilier", 2, OASIS + "Pillar_Hut/Feran_Tier3_Hut_001", 34, 0, 0),
                ("Hutte_Sud_Est", 2, FERAN_T2 + "Hut/Feran_Tier2_Hut_003", 40, 32, 0),
                # Palier 3 : la hutte du chef (lieu central du GDD) et celle du Windwalker.
                ("Hutte_Du_Chef", 3, FERAN_T2 + "Chieftain/Feran_Tier2_Chieftain_001", 0, -42, 0),
                ("Hutte_Du_Windwalker", 3, FERAN_T3 + "Chieftain/Feran_Tier3_Chieftain_001", 32, -32, 0),
            ],
            "Chantiers": [
                (1, 24, [("Rock_Sandstone", 24), ("Wood_Palm_Trunk", 16), ("Ingredient_Fabric_Scrap_Linen", 12)]),
                (2, 24, [("Rock_Sandstone", 48), ("Wood_Palm_Trunk", 32), ("Ingredient_Fabric_Scrap_Linen", 24),
                         ("Ingredient_Water_Essence", 6)]),
                (3, 24, [("Rock_Sandstone", 64), ("Ingredient_Feathers_Light", 16), ("Plant_Cactus_1", 16),
                         ("Ingredient_Water_Essence", 12)]),
            ],
            "Jobs": [
                ("Batisseur", 0, "Builder", None, None, "Hutte_Est"),
                ("Guetteur", 0, "Watcher", "Muret_Du_Vent", "front", "Hutte_Ouest"),
                ("Porteuse_Eau", 1, "WellKeeper", "Entree_Oasis", "front", "Grande_Hutte"),
                ("Eleveuse", 1, "Breeder", "Enclos_Oasis", "front", "Hutte_Ouest"),
                ("Garde", 2, "Guard", "Hutte_Pilier", "front", "Hutte_Nord_Ouest"),
                ("Ancien", 3, "Elder", "Hutte_Du_Chef", "front", "Hutte_Du_Chef"),
            ],
            "Woodpile": (-4, -3),
        },
        # (métier, apparence vanilla, animation de travail, rayon)
        "jobs": [
            ("Builder", "Feran_Burrower", "Crouch", 2),
            ("Watcher", "Feran_Sharptooth", "Alerted", 2),
            ("WellKeeper", "Feran_Civilian", "Crouch", 2),
            ("Breeder", "Feran_Burrower", "Crouch", 4),
            ("Guard", "Feran_Longtooth", "Alerted", 3),
            ("Elder", "Feran_Windwalker", "Sit", 2),
        ],
        "looks": {"Crier": "Feran_Civilian", "Lookout": "Feran_Sharptooth", "Captive": "Feran_Windwalker",
                  "Merchant": "Feran_Civilian", "Chief": "Feran_Windwalker"},
        "deposit": "Furniture_Feran_Chest_Small",
        "sign": "Furniture_Feran_Sign",
        "statue": "Furniture_Temple_Wind_Statue",
        "defender": ("Feran_Longtooth", "Weapon_Spear_Bone",
                     ["Feran_Longtooth_Spear_Swing_Left", "Feran_Longtooth_Spear_Swing_Right",
                      "Feran_Longtooth_Spear_Stab"], 3.2),
        "favor": {"Icon": "Icons/ItemsGenerated/Ingredient_Feathers_Light.png",
                  "Model": "Resources/Materials/Feather.blockymodel",
                  "Texture": "Resources/Materials/Feather_Textures/White.png",
                  "IconProperties": {"Scale": 0.6, "Translation": [4, 0], "Rotation": [22.5, 45, 22.5]},
                  "ItemSoundSetId": "ISS_Items_Cloth"},
        "vanilla_group": "Feran",
        "enemy": "Scarak",
    },
    "Renonce": {
        "name": ("Renoncés", "Forsworn"),
        "adj": ("renoncé", "Forsworn"),
        "layout": "Renonce_Givre",
        "layout_spec": {
            "People": "Renonce",
            "PlazaRadius": 5,
            "Banner": (0, -4),
            "Buildings": [
                # Palier 0 : l'abri des fuyards (maisons Tier 0), une tour de guet, le brasero.
                ("Abri_Des_Fuyards", 0, OUT + "Houses/Tier0/Outlander_Houses_Tier0_001", -15, 0, 0),
                ("Abri_Du_Guet", 0, OUT + "Houses/Tier0/Outlander_Houses_Tier0_003", 15, 0, 0),
                ("Tour_De_Guet_Givre", 0, OUT + "Towers/Tier1/Outlander_Towers_Tier1_001", 0, -14, 0),
                # Palier 1 : deux maisons Tier 1, le petit bateau ramené.
                ("Maison_Des_Repentis", 1, OUT + "Houses/Tier1/Outlander_Houses_Tier1_002", -18, 22, 0),
                ("Maison_Du_Chasseur", 1, OUT + "Houses/Tier1/Outlander_Houses_Tier1_005", 18, 22, 0),
                ("Petit_Bateau", 1, OUT + "Boats/Small/Outlander_Boats_Small_001", 0, 26, 0),
                # Bâtiments de métier, étape 3 : la bergerie du givre (enclos du mod en blocs vanilla, barrière à l'est).
                ("Bergerie_Du_Givre", 1, gl.PEN + "Renonce_Pen", -19, -15, 1),
                # Palier 2 : la grande maison, la tour du fort, le grand bateau.
                ("Grande_Maison_Givre", 2, OUT + "Houses/Tier2/Outlander_Houses_Tier2_003", -36, -14, 0),
                ("Tour_Du_Fort", 2, OUT + "Towers/Tier2/Outlander_Towers_Tier2_001", 30, -12, 0),
                ("Grand_Bateau", 2, OUT + "Boats/Large/Outlander_Boats_Large_001", 36, 22, 0),
                # Palier 3 : la maison du Sorcier et le totem brisé (lieu central du GDD).
                ("Maison_Du_Sorcier", 3, OUT + "Houses/Tier3/Outlander_Houses_Tier3_002", 0, -40, 0),
                ("Totem_Brise", 3, OUT + "Totems/Outlander_Totems_001", -30, 44, 0),
            ],
            "Chantiers": [
                (1, 24, [("Wood_Fir_Trunk", 24), ("Rock_Stone_Cobble", 16), ("Ingredient_Fabric_Scrap_Wool", 12)]),
                (2, 24, [("Wood_Fir_Trunk", 48), ("Wood_Hardwood_Planks", 32), ("Rock_Stone_Cobble", 24),
                         ("Ingredient_Leather_Light", 8)]),
                (3, 24, [("Wood_Fir_Trunk", 64), ("Ingredient_Bolt_Wool", 12), ("Ingredient_Ice_Essence", 12),
                         ("Ingredient_Fire_Essence", 12)]),
            ],
            "Jobs": [
                ("Batisseur", 0, "Builder", None, None, "Abri_Des_Fuyards"),
                ("Guetteur", 0, "Watcher", "Tour_De_Guet_Givre", "front", "Abri_Du_Guet"),
                ("Chasseur", 1, "Hunter", "Maison_Du_Chasseur", "front", "Maison_Du_Chasseur"),
                ("Berger", 1, "Breeder", "Bergerie_Du_Givre", "front", "Abri_Des_Fuyards"),
                ("Garde", 2, "Guard", "Tour_Du_Fort", "front", "Grande_Maison_Givre"),
                ("Ancien", 3, "Elder", "Maison_Du_Sorcier", "front", "Maison_Du_Sorcier"),
            ],
            "Woodpile": (-4, -3),
        },
        "jobs": [
            ("Builder", "Outlander_Peon", "Kneel", 2),
            ("Watcher", "Outlander_Hunter", "Alerted", 2),
            ("Hunter", "Outlander_Hunter", "Eat", 3),
            ("Breeder", "Outlander_Peon", "Kneel", 4),
            ("Guard", "Outlander_Hunter", "Alerted", 3),
            ("Elder", "Outlander_Sorcerer", "Kneel", 2),
        ],
        "looks": {"Crier": "Outlander_Peon", "Lookout": "Outlander_Hunter", "Captive": "Outlander_Peon",
                  "Merchant": "Outlander_Peon", "Chief": "Outlander_Sorcerer"},
        "deposit": "Furniture_Lumberjack_Chest_Small",
        "sign": "Furniture_Lumberjack_Sign",
        "statue": "Furniture_Human_Ruins_Banner",
        "defender": ("Outlander_Hunter", "Weapon_Daggers_Fang_Doomed",
                     ["Outlander_Hunter_Daggers_Swing_Left_Right", "Outlander_Hunter_Daggers_Swing_Right_Left"], 2.4),
        "favor": {"Icon": "Icons/ItemsGenerated/Ingredient_Ice_Essence.png",
                  "Model": "Resources/Ingredients/Essence.blockymodel",
                  "Texture": "Resources/Ingredients/Essence_Textures/Ice_Essence_Texture.png",
                  "IconProperties": {"Scale": 0.6, "Rotation": [0, 0, 0], "Translation": [0, -13]},
                  "ItemSoundSetId": "ISS_Items_Gems"},
        "vanilla_group": None,
        "enemy": "Cult",
    },
}

# Assaillants : (suffixe, apparence, arme ou None, butin, PV, dégâts, vitesse, attaques, portée)
SCARAK_SWIPES = ["Root_NPC_Scarak_Fighter_Attack"]
RAIDERS = {
    "Scarak": [
        ("Scarak_Fighter", "Scarak_Fighter", None, "Drop_Scarak_Fighter", 81, 18, 6.0, SCARAK_SWIPES, 2.2),
        ("Scarak_Louse", "Scarak_Louse", None, "Drop_Scarak_Louse", 21, 8, 6.5, ["Scarak_Louse_Bite"], 1.6),
        ("Scarak_Defender", "Scarak_Defender", None, "Drop_Scarak_Defender", 103, 24, 4.4, ["Scarak_Defender_Bite"], 2.4),
        ("Scarak_Broodmother", "Scarak_Broodmother", None, "Drop_Scarak_Broodmother", 160, 26, 4.2,
         ["Scarak_Defender_Bite"], 2.8),
    ],
    "Cult": [
        ("Cult_Cultist", "Outlander_Cultist", "Weapon_Daggers_Doomed", "Drop_Outlander_Cultist", 81, 21, 5.0,
         ["Outlander_Cultist_Daggers_Swing_Left_Right", "Outlander_Cultist_Daggers_Stab_Right_Left",
          "Outlander_Cultist_Daggers_Swing_Right_Left"], 2.4),
        ("Cult_Berserker", "Outlander_Berserker", "Weapon_Axe_Doomed", "Drop_Outlander_Berserker", 103, 27, 5.2,
         ["Outlander_Berserker_Axe_Swing_Left", "Outlander_Berserker_Axe_Swing_Right",
          "Outlander_Berserker_Axe_Swing_Down"], 2.6),
        ("Cult_Brute", "Outlander_Brute", "Weapon_Battleaxe_Doomed", "Drop_Outlander_Brute", 124, 28, 4.2,
         ["Outlander_Berserker_Axe_Swing_Down", "Outlander_Berserker_Axe_Swing_Left"], 2.8),
        ("Cult_Marauder", "Outlander_Marauder", "Weapon_Sword_Doomed", "Drop_Outlander_Marauder", 160, 28, 4.6,
         ["Outlander_Marauder_Sword_Swing_Left", "Outlander_Marauder_Sword_Swing_Right",
          "Outlander_Marauder_Sword_Swing_Down"], 2.6),
    ],
}
ENEMY_SOUND = {"Scarak": "SFX_Scarak_Fighter_Alerted", "Cult": "SFX_Trork_Chieftain_Alerted"}


# ----------------------------------------------------------------------------------------------------------------------
# PNJ
# ----------------------------------------------------------------------------------------------------------------------

def service_roles(pid, spec):
    """Crieur, guetteur, captif, marchand, chef : copies des rôles kweebec sur une apparence du peuple."""
    for kind, look in spec["looks"].items():
        src = json.loads((ROLES / f"Nakasar_Peuples_Kweebec_{kind}.json").read_text(encoding="utf-8"))
        doc = copy.deepcopy(src)
        doc["$Comment"] = (f"{kind} d'un village {spec['adj'][0]} (étape 8), généré par tools/generate_zones.py : copie du "
                           f"rôle kweebec sur l'apparence vanilla {look}. Ne régénère jamais (VillageNoRegenSystem).")
        doc["Appearance"] = look
        doc["NameTranslationKey"] = f"nakasar_peuples.npc.{pid}_{kind}.name"
        write(ROLES / f"Nakasar_Peuples_{pid}_{kind}.json", {"$Comment": doc.pop("$Comment"), **doc})


def job_roles(pid, spec):
    for job, look, anim, radius in spec["jobs"]:
        rid, doc = gv.role(pid, job, look, anim, radius)
        doc["$Comment"] = doc["$Comment"].replace("generate_villagers.py", "generate_zones.py (étape 8)")
        write(ROLES / f"{rid}.json", doc)
        did, ddoc = gv.dialogue(pid, job)
        ddoc["$Comment"] = f"Dialogue du villageois à métier {job} (étape 8), généré par tools/generate_zones.py."
        write(RES / "Nakasar/Dialogues" / pid / f"{did}.json", ddoc)


def defender(pid, spec):
    look, weapon, swings, reach = spec["defender"]
    rid, doc = gr.defender(pid)
    doc["$Comment"] = (f"Garde de raid {spec['adj'][0]} (étape 8), généré par tools/generate_zones.py : apparence, arme et "
                       f"attaques vanilla ({look}). Tient son poste autour du cœur et se bat contre les assaillants. "
                       "Ne se soigne jamais.")
    doc["Appearance"] = look
    doc["HotbarItems"] = [weapon]
    doc["DisableDamageGroups"] = [f"Nakasar_Peuples_{pid}"]
    replace_attacks(doc, swings, reach)
    write(ROLES / f"{rid}.json", doc)


def replace_attacks(doc, swings, reach):
    """Remplace l'instruction d'attaque (celle qui chaîne les Attack) par celle des attaques vanilla données."""
    def walk(node):
        if isinstance(node, dict):
            insts = node.get("Instructions")
            if isinstance(insts, list):
                for i, inst in enumerate(insts):
                    if isinstance(inst, dict) and any(a.get("Type") == "Attack" for a in inst.get("Actions", [])
                                                      if isinstance(a, dict)):
                        pause = [0.9, 1.4]
                        for a in inst["Actions"]:
                            if a.get("Type") == "Timeout":
                                pause = a.get("Delay", pause)
                        insts[i] = gr.attack_instruction(swings, reach, pause)
                    else:
                        walk(inst)
            for v in node.values():
                if isinstance(v, (dict, list)) and v is not insts:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(doc)


def raiders(enemy):
    for suffix, look, weapon, drops, hp, dmg, speed, swings, reach in RAIDERS[enemy]:
        rid, doc = gr.raider(suffix, look, weapon or "Weapon_Club_Crude", drops, hp, dmg, speed)
        what = "scarak" if enemy == "Scarak" else "du culte outlander"
        prey = "Feran" if enemy == "Scarak" else "Renoncés"
        doc["$Comment"] = (f"Assaillant {what} d'un raid (étape 8), généré par tools/generate_zones.py. Apparence, attaques "
                           f"et butin vanilla ({look}). Posé par raid/Raids au camp ; il marche sur le cœur du village et "
                           f"frappe à vue joueurs et {prey} (RaidAttitudeSystem). Retiré à la fin du raid. Ne se soigne "
                           "jamais.")
        if weapon is None:
            doc.pop("HotbarItems", None)
        else:
            doc["HotbarItems"] = [weapon]
        replace_attacks(doc, swings, reach)
        write(ROLES / f"{rid}.json", doc)


# ----------------------------------------------------------------------------------------------------------------------
# Dialogues du crieur et du marchand (copies kweebec), du chef (chaîne)
# ----------------------------------------------------------------------------------------------------------------------

def copy_dialogue(pid, kind):
    src = (RES / f"Nakasar/Dialogues/Kweebec/Kweebec_{kind}.json").read_text(encoding="utf-8")
    doc = json.loads(src.replace("Kweebec_", f"{pid}_").replace('"Kweebec"', f'"{pid}"'))
    doc["$Comment"] = f"Dialogue {kind.lower()} d'un village {pid} (étape 8), généré par tools/generate_zones.py (copie du kweebec)."
    write(RES / f"Nakasar/Dialogues/{pid}/{pid}_{kind}.json", doc)
    keys = set()

    def collect(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if k.endswith("Key") and isinstance(x, str):
                    keys.add(x)
                collect(x)
        elif isinstance(v, list):
            for x in v:
                collect(x)
    collect(doc)
    return keys


def chain_dialogue(pid, steps, reward):
    """Le chef : une étape par rang. `steps` : liste de (n, nœud, clé, modèle ou None, rang, réponse spéciale ou None).

    Étape 1 : objets rendus au chef. Étapes 2 à 4 : demandes de chaîne. Étape 5 : Feran = demande de chaîne puis le
    bracelet ; Renoncés = le manteau donné au rang Champion.
    """
    K = f"nakasar_peuples.dialogue.{pid}_Chef."
    flag = lambda n: f"{pid}_Chain_{n}"
    bye = {"TextKey": K + "aurevoir"}
    news = {"TextKey": K + "nouvelles", "Effects": [{"Type": "RaidStatus"}], "Next": "Nouvelles"}

    def node(nid, key, responses):
        return {"Id": nid, "TextKey": K + key, "Responses": responses}

    def start(tid, rank, nxt="Accepte"):
        return {"TextKey": K + "accepter", "HintKey": "nakasar_peuples.dialogue.hint.chain",
                "Conditions": [{"Type": "Rank", "Min": rank}], "FailKey": f"nakasar_peuples.dialogue.fail.rank.{rank}.{pid}",
                "Effects": [{"Type": "StartChainRequest", "Template": tid}], "Next": nxt}

    entries = [
        {"Node": "AuxArmes", "Conditions": [{"Type": "Raid", "State": "Active"}]},
        {"Node": "Honni", "Conditions": [{"Type": "Rank", "Max": "Honni"}]},
        {"Node": "Etranger", "Conditions": [{"Type": "Rank", "Max": "Etranger"}]},
    ]
    nodes = [
        node("AuxArmes", "auxArmes", [news, bye]),
        node("Honni", "honni", [bye]),
        node("Etranger", "etranger", [{"TextKey": K + "commentAider", "Next": "Conseil"}, bye]),
        node("Conseil", "conseil", [
            {"TextKey": K + "voirDemandes", "HintKey": "nakasar_peuples.dialogue.hint.openRequests",
             "Conditions": [{"Type": "InVillage", "People": pid}], "FailKey": "nakasar_peuples.dialogue.fail.inVillage",
             "Effects": [{"Type": "OpenRequests"}]}, bye]),
        node("Accepte", "accepte", [bye]),
        node("Nouvelles", "nouvellesTexte", [bye]),
    ]
    tail = []
    item, qty, rep = steps["give"]
    # Étape 5 et récompense.
    if reward["mode"] == "request":
        entries_tail = [
            {"Node": "Fin", "Conditions": [{"Type": "Flag", "Flag": f"{pid}_Reward"}]},
            {"Node": "Recompense", "Conditions": [{"Type": "Flag", "Flag": flag(5)}]},
            {"Node": "Etape5EnCours", "Conditions": [{"Type": "ChainRequest", "Template": reward["template"]}]},
            {"Node": "Etape5", "Conditions": [{"Type": "Flag", "Flag": flag(4)}]},
        ]
        nodes += [
            node("Etape5", "etape5", [start(reward["template"], "Champion"), news, bye]),
            node("Etape5EnCours", "etape5EnCours", [news, bye]),
            node("Recompense", "recompense", [
                {"TextKey": K + "recevoir", "HintKey": f"nakasar_peuples.dialogue.hint.reward.{pid}",
                 "Effects": [{"Type": "GiveItem", "ItemId": reward["item"], "Quantity": 1},
                             {"Type": "SetFlag", "Flag": f"{pid}_Reward"}], "Next": "Fin"}, news, bye]),
        ]
    else:
        entries_tail = [
            {"Node": "Fin", "Conditions": [{"Type": "Flag", "Flag": flag(5)}]},
            {"Node": "Recompense", "Conditions": [{"Type": "Flag", "Flag": flag(4)}]},
        ]
        nodes += [
            node("Recompense", "recompense", [
                {"TextKey": K + "recevoir", "HintKey": f"nakasar_peuples.dialogue.hint.reward.{pid}",
                 "Conditions": [{"Type": "Rank", "Min": "Champion"}],
                 "FailKey": f"nakasar_peuples.dialogue.fail.rank.Champion.{pid}",
                 "Effects": [{"Type": "GiveItem", "ItemId": reward["item"], "Quantity": 1},
                             {"Type": "SetFlag", "Flag": flag(5)}], "Next": "Fin"}, news, bye]),
        ]
    nodes.append(node("Fin", "fin", [news, bye]))
    entries += entries_tail
    # Étapes 4, 3, 2 (demandes de chaîne), de la plus avancée à la première.
    for n in (4, 3, 2):
        tid, rank = steps[n]
        entries.append({"Node": f"Etape{n}EnCours", "Conditions": [{"Type": "ChainRequest", "Template": tid}]})
        building = CHAIN_BUILDINGS.get(tid)
        if building:
            entries.append({"Node": f"Etape{n}Attente", "Conditions": [{"Type": "Flag", "Flag": flag(n - 1)},
                                                                       {"Type": "Building", "Id": building, "Standing": False}]})
            nodes.append(node(f"Etape{n}Attente", f"etape{n}Attente", [
                {"TextKey": K + "accepter", "HintKey": "nakasar_peuples.dialogue.hint.chain",
                 "Conditions": [{"Type": "Building", "Id": building}],
                 "FailKey": f"nakasar_peuples.dialogue.fail.building.{building}"}, news, bye]))
        entries.append({"Node": f"Etape{n}", "Conditions": [{"Type": "Flag", "Flag": flag(n - 1)}]})
        nodes.append(node(f"Etape{n}", f"etape{n}", [start(tid, rank), news, bye]))
        nodes.append(node(f"Etape{n}EnCours", f"etape{n}EnCours", [news, bye]))
    # Étape 1 : objets rendus au chef.
    entries.append({"Node": "Etape1"})
    nodes.append(node("Etape1", "etape1", [
        {"TextKey": K + "donner", "HintKey": f"nakasar_peuples.dialogue.hint.chainGive.{pid}",
         "Conditions": [{"Type": "Rank", "Min": "Tolere"}, {"Type": "HasItem", "ItemId": item, "Quantity": qty}],
         "FailKey": K + "failDonner",
         "Effects": [{"Type": "TakeItem", "ItemId": item, "Quantity": qty}, {"Type": "AddReputation", "Amount": rep},
                     {"Type": "SetFlag", "Flag": flag(1)}],
         "Next": "Etape2"},
        news, bye]))
    return {
        "$Comment": f"Le chef d'un village {pid} (étape 8), généré par tools/generate_zones.py : la chaîne du peuple (GDD, "
                    "La chaîne de chaque peuple), une étape par rang. Raid en cours → « Aux armes ! », puis l'étape en "
                    "cours ou la suivante ; une étape au-dessus du rang du joueur reste visible, grisée.",
        "NpcNameKey": K + "npc",
        "RoleKey": K + "role",
        "People": pid,
        "Entries": entries,
        "Nodes": nodes,
    }


# ----------------------------------------------------------------------------------------------------------------------
# Demandes
# ----------------------------------------------------------------------------------------------------------------------

REQUESTS = {
    "Feran": [
        ("Feran_Gather_Water", "Gather", {"ItemId": "Ingredient_Water_Essence", "Quantity": 6}, 15, 2),
        ("Feran_Gather_Cactus", "Gather", {"ItemId": "Plant_Cactus_1", "Quantity": 8}, 10, 1),
        ("Feran_Gather_Linen", "Gather", {"ItemId": "Ingredient_Fabric_Scrap_Linen", "Quantity": 12}, 10, 1),
        ("Feran_Gather_Feathers", "Gather", {"ItemId": "Ingredient_Feathers_Light", "Quantity": 10}, 10, 1),
        ("Feran_Craft_Buckets", "Craft", {"ItemId": "Container_Bucket", "Quantity": 2}, 15, 2),
        ("Feran_Hunt_Scaraks", "Hunt", {"Spawns": ["Scarak_Fighter", "Scarak_Fighter", "Scarak_Fighter", "Scarak_Louse"],
                                         "Roles": ["Scarak_Fighter", "Scarak_Louse", "Scarak_Defender"],
                                         "MinDistance": 90, "MaxDistance": 150}, 20, 3),
        ("Feran_Delivery_Missive", "Delivery", {"MinDistance": 90, "MaxDistance": 150}, 10, 1),
        ("Feran_Escort_Scout", "Escort", {"Spawns": ["Scarak_Fighter", "Scarak_Fighter"], "MinDistance": 80,
                                          "MaxDistance": 140}, 20, 3),
        ("Feran_Defense_Gate", "Defense", {}, 25, 3),
    ],
    "Renonce": [
        ("Renonce_Gather_Fir", "Gather", {"ItemId": "Wood_Fir_Trunk", "Quantity": 16}, 10, 2),
        ("Renonce_Gather_Meat", "Gather", {"ItemId": "Food_Wildmeat_Raw", "Quantity": 6}, 10, 1),
        ("Renonce_Gather_Wool", "Gather", {"ItemId": "Ingredient_Fabric_Scrap_Wool", "Quantity": 10}, 10, 1),
        ("Renonce_Craft_Mittens", "Craft", {"ItemId": "Armor_Wool_Hands", "Quantity": 1}, 15, 2),
        ("Renonce_Hunt_Cultists", "Hunt", {"Spawns": ["Outlander_Cultist", "Outlander_Cultist", "Outlander_Hunter"],
                                           "Roles": ["Outlander_Cultist", "Outlander_Hunter", "Outlander_Berserker"],
                                           "MinDistance": 90, "MaxDistance": 150}, 20, 3),
        ("Renonce_Delivery_Missive", "Delivery", {"MinDistance": 90, "MaxDistance": 150}, 10, 1),
        ("Renonce_Escort_Fugitive", "Escort", {"Spawns": ["Outlander_Cultist", "Outlander_Cultist"], "MinDistance": 80,
                                               "MaxDistance": 140}, 20, 3),
        ("Renonce_Defense_Night", "Defense", {}, 25, 3),
    ],
}

# Étapes de chaîne qui se jouent autour d'un bâtiment du plan : sans lui debout, le chef attend (« Attente »).
CHAIN_BUILDINGS = {"Renonce_Chain_Fort": "Tour_Du_Fort"}

# Chaînes : étape 1 = (objet, quantité, réputation) ; 2 à 4 (et 5 chez les Feran) = demandes de chaîne.
CHAINS = {
    "Feran": {
        "give": ("Ingredient_Water_Essence", 8, 80),
        "templates": [
            (2, "Feran_Chain_Totems", "Plant", {"ItemId": "Furniture_Temple_Wind_Statue", "Quantity": 4,
                                                "MinDistance": 50, "MaxDistance": 90}, 120, 5, "Ami"),
            (3, "Feran_Chain_Hive", "Hunt", {"Spawns": ["Scarak_Defender", "Scarak_Fighter", "Scarak_Fighter", "Scarak_Louse"],
                                             "Roles": ["Scarak_Defender", "Scarak_Fighter", "Scarak_Louse"],
                                             "MinDistance": 110, "MaxDistance": 170}, 150, 5, "Ami"),
            (4, "Feran_Chain_Windwalker", "Escort", {"Spawns": ["Scarak_Fighter", "Scarak_Fighter", "Scarak_Defender"],
                                                     "MinDistance": 110, "MaxDistance": 170}, 200, 6, "Hote"),
            (5, "Feran_Chain_Broodmother", "Hunt", {"Spawns": ["Scarak_Broodmother", "Scarak_Louse", "Scarak_Louse"],
                                                    "Roles": ["Scarak_Broodmother"], "MinDistance": 120,
                                                    "MaxDistance": 180}, 250, 8, "Champion"),
        ],
        "reward": {"mode": "request", "template": "Feran_Chain_Broodmother", "item": "Nakasar_Peuples_Wind_Bracelet"},
    },
    "Renonce": {
        "give": ("Food_Wildmeat_Cooked", 8, 80),
        "templates": [
            (2, "Renonce_Chain_Totems", "Hunt", {"Spawns": ["Outlander_Priest", "Outlander_Cultist", "Outlander_Cultist"],
                                                 "Roles": ["Outlander_Priest"], "MinDistance": 100,
                                                 "MaxDistance": 160}, 120, 5, "Ami"),
            (3, "Renonce_Chain_Boats", "Gather", {"ItemId": "Wood_Fir_Trunk", "Quantity": 32}, 150, 5, "Ami"),
            (4, "Renonce_Chain_Fort", "Defense", {}, 200, 6, "Hote"),
        ],
        "reward": {"mode": "give", "item": "Nakasar_Peuples_Frost_Mantle"},
    },
}


def request_doc(pid, tid, kind, extra, essor, favors):
    doc = {
        "$Comment": f"Demande du tableau d'un village {pid} (étape 8), générée par tools/generate_zones.py.",
        "People": pid,
        "Type": kind,
        "MinTier": 0,
        "MaxTier": 3,
        "Weight": 1,
        "TitleKey": f"nakasar_peuples.request.{tid}.title",
        "TaskKey": f"nakasar_peuples.request.{tid}.task",
    }
    doc.update(extra)
    doc.update({"Essor": essor, "Favors": favors})
    return doc


def chain_doc(pid, n, tid, kind, extra, reputation, favors):
    doc = {
        "$Comment": f"Étape {n} de la chaîne {pid} (étape 8), générée par tools/generate_zones.py : donnée par le chef "
                    f"(StartChainRequest), jamais tirée au tableau (Weight 0). Remplie, elle pose {pid}_Chain_{n}.",
        "People": pid,
        "Type": kind,
        "Weight": 0,
        "TitleKey": f"nakasar_peuples.request.{tid}.title",
        "TaskKey": f"nakasar_peuples.request.{tid}.task",
    }
    doc.update(extra)
    doc.update({"Essor": 0, "Favors": favors, "Reputation": reputation, "Flag": f"{pid}_Chain_{n}"})
    return doc


# ----------------------------------------------------------------------------------------------------------------------
# Objets, échoppes, groupes, évènements
# ----------------------------------------------------------------------------------------------------------------------

def people_items(pid, spec):
    lower = pid
    favor = {
        "$Comment": f"Faveur des {spec['name'][0]} (étape 8) : payée pour une demande remplie, dépensée aux échoppes.",
        "TranslationProperties": {"Name": f"nakasar_peuples.items.Nakasar_Peuples_Favor_{lower}.name",
                                  "Description": f"nakasar_peuples.items.Nakasar_Peuples_Favor_{lower}.description"},
        "Icon": spec["favor"]["Icon"],
        "Categories": ["Items.Ingredients"],
        "Model": spec["favor"]["Model"],
        "Texture": spec["favor"]["Texture"],
        "PlayerAnimationsId": "Item",
        "Quality": "Uncommon",
        "IconProperties": spec["favor"]["IconProperties"],
        "ItemEntity": {"ParticleSystemId": None},
        "ItemSoundSetId": spec["favor"]["ItemSoundSetId"],
        "DropOnDeath": True,
    }
    write(ITEMS / f"Nakasar_Peuples_Favor_{pid}.json", favor)
    missive = json.loads((ITEMS / "Nakasar_Peuples_Missive_Kweebec.json").read_text(encoding="utf-8"))
    missive["$Comment"] = f"Missive des demandes de livraison d'un village {pid} (étape 8), généré par tools/generate_zones.py."
    missive["TranslationProperties"] = {"Name": f"nakasar_peuples.items.Nakasar_Peuples_Missive_{pid}.name",
                                        "Description": f"nakasar_peuples.items.Nakasar_Peuples_Missive_{pid}.description"}
    write(ITEMS / f"Nakasar_Peuples_Missive_{pid}.json", missive)
    board = json.loads((ITEMS / "Nakasar_Peuples_Board_Kweebec.json").read_text(encoding="utf-8"))
    board["$Comment"] = f"Tableau d'un village {pid} (étape 8) : panneau vanilla {spec['sign']}, interaction du tableau."
    board["Parent"] = spec["sign"]
    board["TranslationProperties"] = {"Name": f"nakasar_peuples.items.Nakasar_Peuples_Board_{pid}.name",
                                      "Description": f"nakasar_peuples.items.Nakasar_Peuples_Board_{pid}.description"}
    write(ITEMS / f"Nakasar_Peuples_Board_{pid}.json", board)
    banner = json.loads((ITEMS / "Nakasar_Peuples_Banner_Kweebec.json").read_text(encoding="utf-8"))
    banner["$Comment"] = f"Bannière d'un village {pid} (étape 8) : bloc vanilla {spec['statue']}, marqueur de carte du mod."
    banner["Parent"] = spec["statue"]
    banner["TranslationProperties"] = {"Name": f"nakasar_peuples.items.Nakasar_Peuples_Banner_{pid}.name",
                                       "Description": f"nakasar_peuples.items.Nakasar_Peuples_Banner_{pid}.description"}
    marker = banner["BlockType"]["BlockEntity"]["Components"]["BlockMapMarker"]
    marker.update({"Name": f"nakasar_peuples.marker.{pid}", "Icon": f"Nakasar_Peuples_{pid}.png",
                   "CompassIcon": f"Nakasar_Peuples_{pid}Compass.png"})
    write(ITEMS / f"Nakasar_Peuples_Banner_{pid}.json", banner)
    write(RES / f"NPC/Groups/Nakasar/Peuples/Nakasar_Peuples_{pid}.json",
          {"$Comment": f"Les PNJ du mod du peuple {pid} (étape 8).", "IncludeRoles": [f"Nakasar_Peuples_{pid}*"]})
    groups = [g for g in (spec["vanilla_group"], f"Nakasar_Peuples_{pid}") if g]
    write(RES / f"NPC/Reputation/Groups/Nakasar_Peuples_{pid}.json",
          {"$Comment": f"Réputation de peuple {pid} (étape 8) : ReputationPlugin vanilla"
                       + (", Feran vanilla compris." if spec["vanilla_group"] else " (les Outlanders vanilla sont le culte : exclus)."),
           "NPCGroups": groups, "InitialReputationValue": 0})


def shop(pid, rank, slots, fav, title_fr, title_en):
    t(f"barter.{pid}_{rank}.title", title_fr, title_en)
    trades = []
    for item, qty, price, stock in slots:
        trades.append({"Type": "Fixed", "Trade": {"Output": {"ItemId": item, "Quantity": qty},
                                                  "Input": [{"ItemId": fav, "Quantity": price}], "Stock": stock}})
    write(RES / f"BarterShops/Nakasar_Peuples_{pid}_{rank}.json",
          {"$Comment": f"Échoppe {pid} du rang {rank} (étape 8), générée par tools/generate_zones.py.",
           "DisplayNameKey": f"nakasar_peuples.barter.{pid}_{rank}.title", "RefreshInterval": {"Days": 3},
           "RestockHour": 6, "TradeSlots": trades})


def shops():
    f = "Nakasar_Peuples_Favor_Feran"
    shop("Feran", "Tolere", [("Nakasar_Peuples_Oasis_Waterskin", 1, 1, 10), ("Ingredient_Fabric_Scrap_Linen", 4, 1, 10),
                             ("Furniture_Temple_Wind_Statue", 1, 1, 8), ("Food_Kebab_Fruit", 1, 1, 6)],
         f, "Échoppe feran", "Feran stall")
    shop("Feran", "Ami", [("Nakasar_Peuples_Oasis_Waterskin", 3, 2, 8), ("Ingredient_Water_Essence", 2, 2, 8),
                          ("Ingredient_Feathers_Light", 4, 1, 10), ("Weapon_Spear_Bone", 1, 6, 2)],
         f, "Échoppe feran des amis", "Feran friends' stall")
    shop("Feran", "Hote", [("Armor_Cloth_Linen_Head", 1, 6, 2), ("Armor_Cloth_Linen_Chest", 1, 8, 2),
                           ("Ingredient_Lightning_Essence", 2, 3, 6), ("Weapon_Sword_Bone", 1, 8, 2)],
         f, "Réserve de l'hôte feran", "Feran host's reserve")
    f = "Nakasar_Peuples_Favor_Renonce"
    shop("Renonce", "Tolere", [("Food_Wildmeat_Cooked", 2, 1, 10), ("Ingredient_Fabric_Scrap_Wool", 4, 1, 10),
                               ("Furniture_Crude_Brazier", 1, 2, 4), ("Wood_Fir_Trunk", 8, 1, 10)],
         f, "Échoppe des Renoncés", "Forsworn stall")
    shop("Renonce", "Ami", [("Armor_Wool_Hands", 1, 3, 3), ("Armor_Wool_Head", 1, 3, 3),
                            ("Ingredient_Ice_Essence", 2, 2, 8), ("Ingredient_Fire_Essence", 2, 2, 8)],
         f, "Échoppe des amis renoncés", "Forsworn friends' stall")
    shop("Renonce", "Hote", [("Armor_Wool_Chest", 1, 6, 2), ("Armor_Wool_Legs", 1, 5, 2),
                             ("Weapon_Daggers_Fang_Doomed", 1, 8, 2), ("Weapon_Shortbow_Doomed", 1, 8, 2)],
         f, "Réserve de l'hôte renoncé", "Forsworn host's reserve")


def raid_event(pid, enemy):
    eid = f"Nakasar_Peuples_Raid_{pid}"
    k = "nakasar_peuples.raid."
    ev = gr.event()
    ev["$Comment"] = f"Raid sur un village {pid} (étape 8), généré par tools/generate_zones.py (même principe que {gr.event()['Root']})."
    ev["Root"] = f"{eid}_Warn"
    ev["Name"] = f"{k}event.name.{pid}"
    write(RES / f"WorldEvent/Event/Nakasar/Peuples/{eid}.json", ev)
    warn = gr.stage_warn()
    fork = warn["Forks"][0]
    fork["Conditions"][1]["MapIntervalKey"] = f"{k}map.arrivesIn.{pid}"
    fork["Actions"][0]["PrimaryTitle"] = f"{k}title.wave.{pid}"
    fork["Actions"][1]["SoundFX"]["Effect"] = ENEMY_SOUND[enemy]
    fork["Next"] = f"{eid}_Fight"
    write(RES / f"WorldEvent/Stage/Nakasar/Peuples/{eid}_Warn.json", warn)
    write(RES / f"WorldEvent/Stage/Nakasar/Peuples/{eid}_Fight.json", gr.stage_fight())


def trophies():
    scarak = gr.trophy()
    scarak.update({
        "$Comment": "Trophée scarak : donné au bilan d'un raid gagné sur un village feran (étape 8). Chitine vanilla.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Scarak.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Scarak.description"},
        "Icon": "Icons/ItemsGenerated/Ingredient_Chitin_Sturdy.png",
        "Model": "Resources/Materials/Chitin_Sturdy.blockymodel",
        "Texture": "Resources/Materials/Chitin_Sturdy_Texture.png",
        "IconProperties": {"Scale": 0.6, "Rotation": [22.5, 45, 22.5], "Translation": [-4, 1]},
    })
    write(ITEMS / "Nakasar_Peuples_Trophy_Scarak.json", scarak)
    cult = gr.trophy()
    cult.update({
        "$Comment": "Trophée du culte : donné au bilan d'un raid gagné sur le hameau des Renoncés (étape 8). Crânes vanilla.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Cult.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Cult.description"},
    })
    write(ITEMS / "Nakasar_Peuples_Trophy_Cult.json", cult)


def climate_assets():
    """Objets de passage et de climat, effets de soif et d'hypothermie, cause de dégâts du froid."""
    write(ITEMS / "Nakasar_Peuples_Oasis_Waterskin.json", {
        "$Comment": "Outre d'oasis (étape 8, GDD Récompenses feran) : se boit comme la potion d'endurance vanilla "
                    "(Potion_Template) et pose Nakasar_Peuples_Quenched, qui annule la soif de la zone 2 (Java, zone/Climate).",
        "Parent": "Potion_Template",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Oasis_Waterskin.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Oasis_Waterskin.description"},
        "Quality": "Uncommon",
        "Icon": "Icons/ItemsGenerated/Potion_Cyan.png",
        "IconProperties": {"Scale": 0.9, "Rotation": [22.5, 45, 22.5], "Translation": [0, -9]},
        "Interactions": {"Primary": "Block_Primary", "Secondary": "Root_Secondary_Consume_Potion_Stamina"},
        "InteractionVars": {
            "RemoveEffect": {"Interactions": [{"Type": "Simple"}]},
            "Effect": {"Interactions": [{"Type": "Serial", "Interactions": [
                {"Type": "ApplyEffect", "EffectId": "Nakasar_Peuples_Quenched"}]}]},
            "ConsumeCooldown": {"Interactions": ["Consume_Potion_Stamina_Cooldown"]},
            "ConsumeSFX": {"Interactions": [{"Type": "Simple", "RunTime": 0, "Effects": {
                "LocalSoundEventId": "SFX_Health_Potion_Low_Drink", "ClearSoundEventOnFinish": True}}]},
            "ConsumedSFX": {"Interactions": [{"Type": "Simple"}]},
        },
        "BlockType": {
            "CustomModel": "Items/Consumables/Potions/Potion_Large.blockymodel",
            "CustomModelTexture": [{"Texture": "Items/Consumables/Potions/Potion_Textures/Cyan.png", "Weight": 1}],
            "BlockParticleSetId": "GlassMagic",
            "ParticleColor": "#7fd8e8",
            "TextureComputedColor": "#8CC8D6",
        },
        "MaxStack": 8,
        "DropOnDeath": True,
    })
    write(ITEMS / "Nakasar_Peuples_Wind_Bracelet.json", {
        "$Comment": "Bracelet de vent (étape 8) : fin de la chaîne feran. Porté dans l'inventaire, saut x1.35 (Java, "
                    "zone/Climate) ; la première fois, il révèle le hameau des Renoncés. Plumes bleues vanilla.",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Wind_Bracelet.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Wind_Bracelet.description"},
        "Icon": "Icons/ItemsGenerated/Ingredient_Feathers_Blue.png",
        "Categories": ["Items.Ingredients"],
        "Model": "Resources/Materials/Feather.blockymodel",
        "Texture": "Resources/Materials/Feather_Textures/Blue.png",
        "PlayerAnimationsId": "Item",
        "Quality": "Legendary",
        "MaxStack": 1,
        "IconProperties": {"Scale": 0.6, "Translation": [4, 0], "Rotation": [22.5, 45, 22.5]},
        "ItemEntity": {"ParticleSystemId": None},
        "ItemSoundSetId": "ISS_Items_Cloth",
        "DropOnDeath": False,
    })
    write(ITEMS / "Nakasar_Peuples_Frost_Mantle.json", {
        "$Comment": "Manteau du givre (étape 8) : fin de la chaîne des Renoncés. Porté (plastron), il annule le froid de "
                    "la zone 3 (Java, zone/Climate). Plastron de laine vanilla.",
        "Parent": "Armor_Wool_Chest",
        "TranslationProperties": {"Name": "nakasar_peuples.items.Nakasar_Peuples_Frost_Mantle.name",
                                  "Description": "nakasar_peuples.items.Nakasar_Peuples_Frost_Mantle.description"},
        "Quality": "Legendary",
        "MaxDurability": 400,
        "DropOnDeath": False,
    })
    # La Graine d'Écho (étape 6, generate_raids.py) se plante désormais : interaction du mod.
    write(RES / "Item/RootInteractions/Nakasar/Peuples/Root_Nakasar_Peuples_Plant_Echo_Seed.json",
          {"Interactions": ["Nakasar_Peuples_Plant_Echo_Seed"], "RequireNewClick": True})
    write(RES / "Item/Interactions/Nakasar/Peuples/Nakasar_Peuples_Plant_Echo_Seed.json",
          {"$Comment": "Plante la Graine d'Écho en zone 2 : abri d'eau et accueil des Feran (Java, zone/ZoneItemInteraction).",
           "Type": "Nakasar_Peuples_ZoneItem", "Action": "EchoSeed"})

    effects = RES / "Entity/Effects/Nakasar/Peuples"
    write(effects / "Nakasar_Peuples_Thirst.json", {
        "$Comment": "Soif (zone 2, le jour, hors de l'ombre et de l'eau) : l'endurance ne remonte plus (Java, zone/Climate).",
        "Name": "nakasar_peuples.effects.Nakasar_Peuples_Thirst",
        "Debuff": True,
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Peuples/Thirst.png",
        "ApplicationEffects": {"EntityTopTint": "#ffe0a8"},
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 1.5,
    })
    write(effects / "Nakasar_Peuples_Quenched.json", {
        "$Comment": "Désaltéré (Outre d'oasis) : pas de soif pendant 20 minutes.",
        "Name": "nakasar_peuples.effects.Nakasar_Peuples_Quenched",
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Peuples/Quenched.png",
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 1200,
    })
    write(effects / "Nakasar_Peuples_Warmth.json", {
        "$Comment": "Chaleur (zone 3, à l'abri ou près d'un feu) : l'hypothermie redescend (Java, zone/Climate).",
        "Name": "nakasar_peuples.effects.Nakasar_Peuples_Warmth",
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Peuples/Warmth.png",
        "ApplicationEffects": {"EntityBottomTint": "#ffb060"},
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 1.5,
    })
    for n in range(1, 6):
        write(effects / f"Nakasar_Peuples_Hypothermia_{n}.json", {
            "$Comment": f"Hypothermie, piles {2 * n - 1} et {2 * n} : {0.2 * (2 * n - 1):.1f} à {0.2 * 2 * n:.1f} % des PV "
                        "max par seconde (Java, zone/Climate ; copie de la fractale Tempête de neige).",
            "Name": f"nakasar_peuples.effects.Nakasar_Peuples_Hypothermia_{n}",
            "Debuff": True,
            "StatusEffectIcon": f"UI/StatusEffects/Nakasar/Peuples/Hypothermia_{n}.png",
            "ApplicationEffects": {"HorizontalSpeedMultiplier": 1.0, "EntityTopTint": "#e8f4ff"},
            "OverlapBehavior": "Overwrite",
            "Infinite": False,
            "Duration": 1.5,
        })
        t(f"effects.Nakasar_Peuples_Hypothermia_{n}", f"Hypothermie {2 * n}", f"Hypothermia {2 * n}")
    write(RES / "Entity/Damage/Nakasar_Peuples_Cold.json", {
        "$Comment": "Froid de la zone 3 (hypothermie) : une part des PV max par seconde selon les piles, que l'armure ne réduit pas.",
        "BypassResistances": True,
        "DurabilityLoss": False,
        "StaminaLoss": False,
        "DamageTextColor": "#a8d8ff",
    })
    # Icônes : hypothermie et chaleur copiées de la fractale Tempête de neige ; soif et désaltéré dessinées ici.
    STATUS_ICONS.mkdir(parents=True, exist_ok=True)
    for name in [f"Hypothermia_{n}" for n in range(1, 6)] + ["Warmth"]:
        shutil.copyfile(FRACTAL_ICONS / f"{name}.png", STATUS_ICONS / f"{name}.png")
    draw_status_icons()


def draw_status_icons():
    from PIL import Image, ImageDraw
    size, ss = 128, 4
    big = size * ss

    def drop(d, cx, cy, r, fill):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        d.polygon([(cx - r * 0.92, cy - r * 0.35), (cx, cy - r * 2.3), (cx + r * 0.92, cy - r * 0.35)], fill=fill)

    # Soif : soleil orangé et goutte barrée.
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = big // 2
    for i in range(12):
        a = i * math.pi / 6
        d.line([(c + math.cos(a) * 34 * ss, c + math.sin(a) * 34 * ss), (c + math.cos(a) * 54 * ss, c + math.sin(a) * 54 * ss)],
               fill=(240, 160, 60, 255), width=7 * ss)
    d.ellipse([c - 30 * ss, c - 30 * ss, c + 30 * ss, c + 30 * ss], fill=(250, 196, 80, 255), outline=(60, 30, 10, 255),
              width=3 * ss)
    drop(d, c, c + 8 * ss, 14 * ss, (90, 150, 210, 255))
    d.line([(c - 22 * ss, c + 26 * ss), (c + 22 * ss, c - 18 * ss)], fill=(160, 40, 30, 255), width=6 * ss)
    img.resize((size, size), Image.LANCZOS).save(STATUS_ICONS / "Thirst.png")
    # Désaltéré : grosse goutte bleue.
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    drop(d, c, c + 18 * ss, 32 * ss, (20, 40, 70, 255))
    drop(d, c, c + 18 * ss, 27 * ss, (100, 190, 240, 255))
    d.ellipse([c - 14 * ss, c + 4 * ss, c - 4 * ss, c + 14 * ss], fill=(220, 245, 255, 255))
    img.resize((size, size), Image.LANCZOS).save(STATUS_ICONS / "Quenched.png")


def map_icons():
    """Icônes de carte : hutte à plume (Feran), cabane à flocon (Renoncés), même style que generate_map_icons.py."""
    from PIL import Image, ImageDraw, ImageFilter
    import generate_map_icons as gmi
    S, SS = gmi.SIZE, gmi.SS
    out = COMMON / "UI/WorldMap/MapMarkers"

    def feran(s):
        mask = Image.new("L", (S * s, S * s), 0)
        d = ImageDraw.Draw(mask)
        d.pieslice([8 * s, 20 * s, 40 * s, 52 * s], 180, 360, fill=255)   # hutte en dôme
        d.rectangle([8 * s, 35 * s, 40 * s, 41 * s], fill=255)
        d.rectangle([21 * s, 31 * s, 27 * s, 41 * s], fill=0)              # porte
        gmi.leaf(d, (24 * s, 21 * s), math.radians(-70), 16 * s, 4 * s, 255)  # plume au faîte
        return mask

    def renonce(s):
        mask = Image.new("L", (S * s, S * s), 0)
        d = ImageDraw.Draw(mask)
        d.polygon([(8 * s, 32 * s), (24 * s, 22 * s), (40 * s, 32 * s), (36 * s, 35 * s), (24 * s, 27 * s), (12 * s, 35 * s)], fill=255)
        d.rectangle([13 * s, 33 * s, 35 * s, 42 * s], fill=255)
        d.rectangle([21 * s, 36 * s, 27 * s, 42 * s], fill=0)
        c = (24 * s, 12 * s)
        for i in range(3):                                                 # flocon
            a = i * math.pi / 3
            d.line([(c[0] - math.cos(a) * 8 * s, c[1] - math.sin(a) * 8 * s), (c[0] + math.cos(a) * 8 * s, c[1] + math.sin(a) * 8 * s)],
                   fill=255, width=3 * s)
        return mask

    for pid, fig, fill, cfill in (("Feran", feran, (250, 236, 200, 255), (240, 196, 110, 255)),
                                  ("Renonce", renonce, (226, 240, 255, 255), (150, 200, 245, 255))):
        for name, f, th in ((f"Nakasar_Peuples_{pid}.png", fill, 2), (f"Nakasar_Peuples_{pid}Compass.png", cfill, 3)):
            big = S * SS
            mask = fig(SS)
            ring = mask.filter(ImageFilter.MaxFilter(2 * th * SS + 1))
            img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
            img.paste(Image.new("RGBA", (big, big), (0, 0, 0, 255)), (0, 0), ring)
            img.paste(Image.new("RGBA", (big, big), f), (0, 0), mask)
            out.mkdir(parents=True, exist_ok=True)
            img.resize((S, S), Image.LANCZOS).save(out / name)


# ----------------------------------------------------------------------------------------------------------------------
# Textes
# ----------------------------------------------------------------------------------------------------------------------

def texts():
    # Peuples, bannières, tableaux, faveurs, missives, PNJ de service.
    t("people.Feran.name", "Feran", "Feran")
    t("people.Renonce.name", "Outlanders renoncés", "Forsworn Outlanders")
    t("marker.Feran", "Oasis feran", "Feran oasis")
    t("marker.Renonce", "Hameau des Renoncés", "Forsworn hamlet")
    for pid, fr, en in (("Feran", "de l'oasis feran", "Feran oasis"), ("Renonce", "du hameau renoncé", "Forsworn hamlet")):
        t(f"items.Nakasar_Peuples_Board_{pid}.name", f"Tableau {fr}", f"{en} board")
        t(f"items.Nakasar_Peuples_Board_{pid}.description", "Les demandes du village, sa jauge d'essor et le contenu de son dépôt.",
          "The village's requests, its growth gauge and the contents of its deposit.")
        t(f"items.Nakasar_Peuples_Banner_{pid}.name", f"Bannière {fr}", f"{en} banner")
        t(f"items.Nakasar_Peuples_Banner_{pid}.description", "Marque le village sur la carte des voyageurs qui passent à proximité.",
          "Marks the village on the map of travellers passing nearby.")
    t("items.Nakasar_Peuples_Favor_Feran.name", "Plume de vent", "Wind feather")
    t("items.Nakasar_Peuples_Favor_Feran.description",
      "La faveur des Feran : donnée pour une demande remplie, elle se dépense à leurs échoppes.",
      "The Feran's favour: given for a fulfilled request, spent at their stalls.")
    t("items.Nakasar_Peuples_Favor_Renonce.name", "Larme de givre", "Frost tear")
    t("items.Nakasar_Peuples_Favor_Renonce.description",
      "La faveur des Renoncés : donnée pour une demande remplie, elle se dépense à leurs échoppes.",
      "The Forsworn's favour: given for a fulfilled request, spent at their stalls.")
    t("items.Nakasar_Peuples_Missive_Feran.name", "Missive feran", "Feran missive")
    t("items.Nakasar_Peuples_Missive_Feran.description", "Un message noué d'un fil de lin. À remettre au guetteur indiqué par la demande.",
      "A message tied with linen thread. Give it to the lookout named by the request.")
    t("items.Nakasar_Peuples_Missive_Renonce.name", "Missive renoncée", "Forsworn missive")
    t("items.Nakasar_Peuples_Missive_Renonce.description", "Une écorce gravée en hâte. À remettre au guetteur indiqué par la demande.",
      "A hastily carved piece of bark. Give it to the lookout named by the request.")
    npcs = {
        "Feran": {"Crier": ("Crieuse feran", "Feran crier"), "Lookout": ("Guetteur feran", "Feran lookout"),
                  "Captive": ("Windwalker feran", "Feran Windwalker"), "Merchant": ("Marchande feran", "Feran merchant"),
                  "Chief": ("Cheffe feran", "Feran chieftain"), "Defender": ("Garde Longtooth", "Longtooth guard"),
                  "Builder": ("Bâtisseur feran", "Feran builder"), "Watcher": ("Guetteur feran", "Feran watcher"),
                  "WellKeeper": ("Porteuse d'eau feran", "Feran water carrier"), "Guard": ("Garde feran", "Feran guard"),
                  "Breeder": ("Éleveuse feran", "Feran herder"),
                  "Elder": ("Ancien feran", "Feran elder")},
        "Renonce": {"Crier": ("Crieur renoncé", "Forsworn crier"), "Lookout": ("Guetteuse renoncée", "Forsworn lookout"),
                    "Captive": ("Fuyard renoncé", "Forsworn fugitive"), "Merchant": ("Marchand renoncé", "Forsworn merchant"),
                    "Chief": ("Sorcier renoncé", "Forsworn sorcerer"), "Defender": ("Chasseur de garde", "Hunter on guard"),
                    "Builder": ("Bâtisseur renoncé", "Forsworn builder"), "Watcher": ("Guetteuse renoncée", "Forsworn watcher"),
                    "Hunter": ("Chasseur renoncé", "Forsworn hunter"), "Guard": ("Garde renoncé", "Forsworn guard"),
                    "Breeder": ("Berger renoncé", "Forsworn shepherd"),
                    "Elder": ("Ancienne renoncée", "Forsworn elder")},
    }
    for pid, d in npcs.items():
        for kind, (fr, en) in d.items():
            t(f"npc.{pid}_{kind}.name", fr, en)
    # Bâtiments et métiers nouveaux (les autres ids existent déjà chez les Kweebecs).
    for bid, fr, en in [
        ("Hutte_Ouest", "Hutte de l'ouest", "West hut"), ("Hutte_Est", "Hutte de l'est", "East hut"),
        ("Muret_Du_Vent", "Muret du vent", "Wind wall"), ("Grande_Hutte", "Grande hutte", "Great hut"),
        ("Entree_Oasis", "Entrée de l'oasis", "Oasis gate"), ("Hutte_Sud", "Hutte du sud", "South hut"),
        ("Hutte_Nord_Ouest", "Hutte du nord-ouest", "North-west hut"), ("Hutte_Pilier", "Hutte sur pilier", "Pillar hut"),
        ("Hutte_Sud_Est", "Hutte du sud-est", "South-east hut"), ("Hutte_Du_Chef", "Hutte du chef", "Chieftain's hut"),
        ("Hutte_Du_Windwalker", "Hutte du Windwalker", "Windwalker's hut"),
        ("Abri_Des_Fuyards", "Abri des fuyards", "Fugitives' shelter"), ("Abri_Du_Guet", "Abri du guet", "Watch shelter"),
        ("Tour_De_Guet_Givre", "Tour de guet", "Watchtower"), ("Brasero", "Brasero", "Brazier"),
        ("Maison_Des_Repentis", "Maison des repentis", "Penitents' house"),
        ("Maison_Du_Chasseur", "Maison du chasseur", "Hunter's house"), ("Petit_Bateau", "Petit bateau", "Small boat"),
        ("Grande_Maison_Givre", "Grande maison", "Great house"), ("Tour_Du_Fort", "Tour du fort", "Fort tower"),
        ("Grand_Bateau", "Grand bateau", "Large boat"), ("Maison_Du_Sorcier", "Maison du Sorcier", "Sorcerer's house"),
        ("Totem_Brise", "Totem brisé", "Broken totem"),
        ("Enclos_Oasis", "Enclos de l'oasis", "Oasis pen"), ("Bergerie_Du_Givre", "Bergerie du givre", "Frost fold"),
    ]:
        t(f"building.{bid}", fr, en)
    t("job.Porteuse_Eau", "Porteuse d'eau", "Water carrier")
    t("job.Eleveuse", "Éleveuse", "Herder")
    t("job.Berger", "Berger", "Shepherd")
    # job.Chasseur : déjà posé par l'étape 7 (chasseur trork).
    t("dialogue.hint.reward.Feran", "reçois le Bracelet de vent", "receive the Wind Bracelet")
    t("dialogue.hint.reward.Renonce", "reçois le Manteau du givre", "receive the Frost Mantle")
    t("dialogue.hint.chainGive.Feran", "rend 8 Essences d'eau (étape 1 de la chaîne)", "hand over 8 Water Essences (chain step 1)")
    t("dialogue.hint.chainGive.Renonce", "rend 8 Viandes cuites (étape 1 de la chaîne)", "hand over 8 Cooked Meat (chain step 1)")
    for pid, fr, en in (("Feran", "des Feran", "the Feran"), ("Renonce", "des Renoncés", "the Forsworn")):
        for rank, rfr, ren in (("Tolere", "Toléré", "Tolerated"), ("Ami", "Ami", "Friend"), ("Hote", "Hôte", "Host"),
                               ("Champion", "Champion", "Champion")):
            t(f"dialogue.fail.rank.{rank}.{pid}", f"il faut être {rfr} {fr}", f"you must be {ren} of {en}")
    t("dialogue.fail.building.Tour_Du_Fort", "il faut que la tour du fort soit debout (palier Village)",
      "the fort tower must be standing (Village tier)")

    # Crieur et marchand : textes propres à chaque peuple (voix du GDD : Feran formels, le vent et l'eau ; Renoncés
    # méfiants, chuchotent le culte).
    crier = {
        "Feran": {
            "npc": ("Souffle-Clair", "Clearbreath"), "role": ("Voix de l'oasis", "Voice of the oasis"),
            "accueil": ("Que le vent te soit doux, voyageur. Les besoins de l'oasis sont inscrits au tableau, derrière moi.",
                        "May the wind be gentle to you, traveller. The oasis's needs are written on the board behind me."),
            "voir": ("Montre-moi les besoins de l'oasis.", "Show me the oasis's needs."),
            "quoi": ("Comment puis-je aider ?", "How can I help?"),
            "explication": ("Chaque matin, trois besoins. Prends-en un, remplis-le avant l'aube suivante, et l'oasis grandit. L'eau et les biens se déposent dans le coffre de la place, ou se rendent ici.",
                            "Each morning, three needs. Take one, fulfil it before the next dawn, and the oasis grows. Water and goods go in the chest on the square, or are handed in here."),
            "encours": ("Le vent a-t-il porté ce que tu cherchais ?", "Has the wind carried what you were looking for?"),
            "rendre": ("Voici ce que j'apporte.", "Here is what I bring."),
            "rendu": ("L'oasis s'en souviendra, comme le sable se souvient de l'eau.", "The oasis will remember, as sand remembers water."),
            "aurevoir": ("Que l'eau te suive.", "May water follow you."),
            "honni": ("Le vent a porté ton nom jusqu'ici, et il n'était pas doux. Prouve-nous le contraire.",
                      "The wind carried your name here, and it was not gentle. Prove us wrong."),
            "racheter": ("Je veux réparer mes torts.", "I want to make amends."),
        },
        "Renonce": {
            "npc": ("Brise-Chaîne", "Chainbreaker"), "role": ("Voix du hameau", "Voice of the hamlet"),
            "accueil": ("Approche, et parle bas. Le culte a des oreilles partout. Ce qu'il nous faut est gravé sur le tableau.",
                        "Come closer, and speak softly. The cult has ears everywhere. What we need is carved on the board."),
            "voir": ("Montre-moi ce qu'il vous faut.", "Show me what you need."),
            "quoi": ("Comment vous aider ?", "How can I help you?"),
            "explication": ("Trois besoins chaque matin. Tu en prends un, tu le remplis avant l'aube, et le hameau tient un jour de plus. Le coffre de la place reçoit ce que tu rapportes.",
                            "Three needs each morning. Take one, fulfil it before dawn, and the hamlet holds one more day. The chest on the square takes what you bring back."),
            "encours": ("Tu as ce qu'il faut ? Montre, vite.", "Do you have it? Show me, quickly."),
            "rendre": ("Voilà.", "Here."),
            "rendu": ("Bien. Personne ne saura d'où ça vient.", "Good. No one will know where it came from."),
            "aurevoir": ("Ne te retourne pas en partant.", "Don't look back as you leave."),
            "honni": ("Tu sens le culte. Va-t'en avant que les autres ne te voient.", "You smell of the cult. Leave before the others see you."),
            "racheter": ("Je ne suis pas des leurs. Laisse-moi le prouver.", "I am not one of them. Let me prove it."),
        },
    }
    merchant = {
        "Feran": {
            "npc": ("Dune-Fine", "Finedune"), "role": ("marchande", "merchant"),
            "honni": ("Tu as troublé l'eau de l'oasis. Je ne commerce pas avec toi.", "You have muddied the oasis's water. I will not trade with you."),
            "etranger": ("Les Feran ne troquent pas avec les inconnus. Aide l'oasis, et nous parlerons.",
                         "The Feran do not trade with strangers. Help the oasis, and we will talk."),
            "commentAider": ("Comment me faire connaître ?", "How do I make myself known?"),
            "conseil": ("La crieuse, près du tableau, a toujours un besoin pour un étranger. Remplis-en un ou deux, et l'on te tolérera.",
                        "The crier by the board always has a need for a stranger. Fulfil one or two, and you will be tolerated."),
            "voirDemandes": ("Montre-moi les besoins", "Show me the needs"),
            "accueil": ("Le voyageur toléré ! Outres, lin, statuettes du vent : tout se paie en plumes de vent.",
                        "The tolerated traveller! Waterskins, linen, wind statuettes: all paid in wind feathers."),
            "ami": ("Pour un ami de l'oasis, j'ai de l'eau vive et les plumes des hauteurs.", "For a friend of the oasis, I have living water and feathers from the heights."),
            "hote": ("Notre hôte ! Les anciens m'ont permis d'ouvrir la réserve : le lin des Windwalkers t'irait bien.",
                     "Our host! The elders let me open the reserve: Windwalker linen would suit you."),
            "troc": ("Voyons ton troc", "Let's see your wares"), "avance": ("Et pour les amis ?", "And for friends?"),
            "reserve": ("Ouvre-moi la réserve", "Open the reserve for me"), "aurevoir": ("Que le vent te porte", "May the wind carry you"),
        },
        "Renonce": {
            "npc": ("Vieux-Silence", "Old Silence"), "role": ("marchand", "merchant"),
            "honni": ("Pas toi. Pas ici.", "Not you. Not here."),
            "etranger": ("Je ne vends rien aux inconnus. Les inconnus parlent au culte.", "I sell nothing to strangers. Strangers talk to the cult."),
            "commentAider": ("Comment gagner ta confiance ?", "How do I earn your trust?"),
            "conseil": ("Le crieur, près du tableau. Aide le hameau, une fois, deux fois. Après, on verra.",
                        "The crier, by the board. Help the hamlet, once, twice. Then we'll see."),
            "voirDemandes": ("Montre-moi les besoins", "Show me the needs"),
            "accueil": ("Viande, laine, un brasero si tu as froid. Tout se paie en larmes de givre.",
                        "Meat, wool, a brazier if you're cold. Everything is paid in frost tears."),
            "ami": ("Pour un ami : des moufles, et de quoi garder le feu.", "For a friend: mittens, and something to keep the fire going."),
            "hote": ("Toi, tu as tenu le fort. Prends ce qui reste des armes des fuyards.", "You held the fort. Take what is left of the fugitives' weapons."),
            "troc": ("Voyons ton troc", "Let's see your wares"), "avance": ("Et pour les amis ?", "And for friends?"),
            "reserve": ("Ouvre-moi la réserve", "Open the reserve for me"), "aurevoir": ("Fais attention", "Be careful"),
        },
    }
    return crier, merchant


def dialogue_texts(pid, crier, merchant):
    for kind, table in (("Crieur", crier[pid]), ("Marchand", merchant[pid])):
        for k, (fr, en) in table.items():
            t(f"dialogue.{pid}_{kind}.{k}", fr, en)


JOB_TEXTS = {
    "Feran": {
        "Builder": {"npc": ("Creuse-Sable", "Sanddigger"), "role": ("Bâtisseur", "Builder"),
                    "accueil": ("Le sable bouge, la hutte reste. C'est tout mon art.", "The sand moves, the hut stays. That is my whole art."),
                    "metier": ("Je monte les huttes et je les répare après les tempêtes. Le grès du dépôt devient nos murs.",
                               "I raise the huts and mend them after the storms. The sandstone in the deposit becomes our walls."),
                    "chantier": ("Un chantier est ouvert : je bâtis pendant que le vent dort.", "A building site is open: I build while the wind sleeps."),
                    "statut": ("Voilà où en est le chantier.", "Here is how the site is going.")},
        "Watcher": {"npc": ("Œil-de-Dune", "Duneeye"), "role": ("Guetteur", "Watcher"),
                    "accueil": ("Je regarde le sable. Le sable ment, mais pas ses ombres.", "I watch the sand. The sand lies, but not its shadows."),
                    "metier": ("Depuis le muret, je surveille la ruche. Quand le sable frémit, les Scaraks arrivent.",
                               "From the wall, I watch the hive. When the sand trembles, the Scaraks are coming."),
                    "auxArmes": ("Le sable frémit ! Les Scaraks sont sur nous, aux armes !", "The sand trembles! The Scaraks are upon us, to arms!"),
                    "rumeur": ("La ruche a grossi cette lune. Si personne ne la taille, elle viendra boire notre eau.",
                               "The hive has grown this moon. If no one cuts it back, it will come to drink our water.")},
        "WellKeeper": {"npc": ("Eau-Patiente", "Patientwater"), "role": ("Porteuse d'eau", "Water carrier"),
                       "accueil": ("Chaque goutte compte, voyageur. Chaque goutte.", "Every drop counts, traveller. Every drop."),
                       "metier": ("Je porte l'eau de la source aux huttes. Sans eau, pas de Feran. Bois à l'ombre, jamais au soleil.",
                                  "I carry water from the spring to the huts. Without water, no Feran. Drink in the shade, never in the sun.")},
        "Breeder": {"npc": ("Plume-Douce", "Softfeather"), "role": ("Éleveuse", "Herder"),
                    "accueil": ("Doucement près de l'enclos : mes poules pondent mieux dans le calme.",
                                "Gently near the pen: my hens lay better in the calm."),
                    "metier": ("J'élève les bêtes de l'oasis. Des œufs, du cuir, de la laine : rien ne se perd au désert.",
                               "I raise the oasis beasts. Eggs, leather, wool: nothing goes to waste in the desert.")},
        "Guard": {"npc": ("Longue-Dent", "Longfang"), "role": ("Garde", "Guard"),
                  "accueil": ("Halte. L'oasis te tolère, moi je te surveille.", "Halt. The oasis tolerates you; I watch you."),
                  "metier": ("Je tiens la porte de l'oasis. Ma lance a goûté la chitine plus souvent que le pain.",
                             "I hold the oasis gate. My spear has tasted chitin more often than bread."),
                  "auxArmes": ("La ruche attaque ! Tiens la porte avec moi !", "The hive attacks! Hold the gate with me!"),
                  "rumeur": ("Les éclaireurs scaraks tournent autour des dunes. Ils comptent nos lances.",
                             "Scarak scouts circle the dunes. They are counting our spears.")},
        "Elder": {"npc": ("Vent-Ancien", "Oldwind"), "role": ("Ancien", "Elder"),
                  "accueil": ("Assieds-toi. Le vent raconte mieux les choses à qui s'assoit.", "Sit down. The wind tells things better to those who sit."),
                  "metier": ("Je me souviens des oasis perdues. Je les raconte, pour que celle-ci ne le soit pas.",
                             "I remember the lost oases. I tell of them, so that this one will not be lost.")},
    },
    "Renonce": {
        "Builder": {"npc": ("Main-Gercée", "Crackedhand"), "role": ("Bâtisseur", "Builder"),
                    "accueil": ("Chut. Je cloue doucement : le bruit porte loin dans la neige.", "Hush. I nail softly: sound carries far in the snow."),
                    "metier": ("Je bâtis ce que le culte a brûlé. Du sapin, de la pierre, et pas de totem.",
                               "I build what the cult burned. Fir, stone, and no totem."),
                    "chantier": ("Un chantier est ouvert. Je travaille vite, avant le prochain blizzard.", "A site is open. I work fast, before the next blizzard."),
                    "statut": ("Voilà où on en est.", "Here's where we are.")},
        "Watcher": {"npc": ("Veille-Blanche", "Whitewatch"), "role": ("Guetteuse", "Watcher"),
                    "accueil": ("Ne reste pas à découvert. Ils voient loin, sur la neige.", "Don't stay in the open. They see far, on the snow."),
                    "metier": ("Je guette les feux du culte depuis la tour. Quand ils s'allument tous, ils viennent nous chercher.",
                               "I watch for the cult's fires from the tower. When they all light up, they come for us."),
                    "auxArmes": ("Les Marauders ! Ils sont là, aux armes !", "The Marauders! They're here, to arms!"),
                    "rumeur": ("Le Prêtre a planté de nouveaux totems au nord. Il veut nous ramener, de gré ou de force.",
                               "The Priest has planted new totems to the north. He wants us back, willing or not.")},
        "Hunter": {"npc": ("Pas-Feutré", "Softstep"), "role": ("Chasseur", "Hunter"),
                   "accueil": ("Tu marches trop fort. Le gibier t'entend, et le culte aussi.", "You walk too loud. The game hears you, and so does the cult."),
                   "metier": ("Je chasse pour le hameau. Sans viande, le froid gagne. Ne reste jamais loin d'un feu.",
                              "I hunt for the hamlet. Without meat, the cold wins. Never stray far from a fire.")},
        "Breeder": {"npc": ("Laine-Grise", "Greywool"), "role": ("Berger", "Shepherd"),
                    "accueil": ("Ferme la barrière derrière toi. Les mouflons connaissent le chemin du nord.",
                                "Close the gate behind you. The mouflons know the way north."),
                    "metier": ("Je garde le troupeau du hameau. Leur laine nous tient chaud, leur lait nous tient debout.",
                               "I keep the hamlet's flock. Their wool keeps us warm, their milk keeps us standing.")},
        "Guard": {"npc": ("Dos-Large", "Broadback"), "role": ("Garde", "Guard"),
                  "accueil": ("Tu es avec nous, ou avec eux ? Réponds vite.", "Are you with us, or with them? Answer fast."),
                  "metier": ("Je tiens la tour du fort. J'ai porté leurs couleurs, autrefois. Plus jamais.",
                             "I hold the fort tower. I wore their colours, once. Never again."),
                  "auxArmes": ("Le culte vient reprendre les siens ! Personne ne repart avec eux !", "The cult comes to take its own back! No one leaves with them!"),
                  "rumeur": ("Les Marauders aiguisent leurs lames. Ils n'aiment pas qu'on renonce.", "The Marauders are sharpening their blades. They don't like those who renounce.")},
        "Elder": {"npc": ("Mère-Givre", "Mother Frost"), "role": ("Ancienne", "Elder"),
                  "accueil": ("Approche du feu, enfant. Le froid ment : il dit qu'il ne fait pas mal.", "Come close to the fire, child. The cold lies: it says it doesn't hurt."),
                  "metier": ("Je me souviens d'avant le culte. Je le raconte aux jeunes, à voix basse.", "I remember before the cult. I tell the young about it, in a low voice.")},
    },
}


def job_texts(pid):
    for job, table in JOB_TEXTS[pid].items():
        for k, (fr, en) in table.items():
            t(f"dialogue.{pid}_{job}.{k}", fr, en)


REQUEST_TEXTS = {
    "Feran_Gather_Water": ("De l'eau pour l'oasis", "Water for the oasis", "deposit"),
    "Feran_Gather_Cactus": ("Cactus du désert", "Desert cactus", "deposit"),
    "Feran_Gather_Linen": ("Du lin pour les tentes", "Linen for the tents", "deposit"),
    "Feran_Gather_Feathers": ("Plumes pour le vent", "Feathers for the wind", "deposit"),
    "Feran_Craft_Buckets": ("Des seaux au puits", "Buckets for the well", "craft"),
    "Feran_Hunt_Scaraks": ("Chasser les Scaraks", "Hunt the Scaraks", ("Scaraks abattus", "Scaraks slain", "Ils rôdent", "They prowl")),
    "Feran_Delivery_Missive": ("Message au guetteur", "Word to the lookout", "missive"),
    "Feran_Escort_Scout": ("Ramener l'éclaireur", "Bring back the scout", ("Délivre l'éclaireur feran et ramène-le à l'oasis", "Free the Feran scout and bring them back to the oasis")),
    "Feran_Defense_Gate": ("Tenir la porte", "Hold the gate", "defense"),
    "Renonce_Gather_Fir": ("Du sapin pour le feu", "Fir for the fire", "deposit"),
    "Renonce_Gather_Meat": ("Viande pour l'hiver", "Meat for winter", "deposit"),
    "Renonce_Gather_Wool": ("De la laine", "Some wool", "deposit"),
    "Renonce_Craft_Mittens": ("Des moufles", "Mittens", "craft"),
    "Renonce_Hunt_Cultists": ("Chasser les cultistes", "Hunt the cultists", ("Cultistes abattus", "Cultists slain", "Leur camp est", "Their camp is")),
    "Renonce_Delivery_Missive": ("Message au guetteur", "Word to the lookout", "missive"),
    "Renonce_Escort_Fugitive": ("Ramener le fuyard", "Bring back the fugitive", ("Délivre le fuyard et ramène-le au hameau", "Free the fugitive and bring them back to the hamlet")),
    "Renonce_Defense_Night": ("Veiller cette nuit", "Keep watch tonight", "defense"),
    # Chaînes
    "Feran_Chain_Totems": ("Les totems du vent", "The wind totems", ("Totems posés", "Totems placed", "Le lieu est", "The spot is")),
    "Feran_Chain_Hive": ("L'entrée de la ruche", "The hive entrance", ("Scaraks abattus", "Scaraks slain", "L'entrée est", "The entrance is")),
    "Feran_Chain_Windwalker": ("Escorter le Windwalker", "Escort the Windwalker", ("Retrouve le Windwalker près de la ziggourat et ramène-le", "Find the Windwalker near the ziggurat and bring them back")),
    "Feran_Chain_Broodmother": ("La Broodmother", "The Broodmother", ("Broodmother abattue", "Broodmother slain", "Elle niche", "She nests")),
    "Renonce_Chain_Totems": ("Les totems du Prêtre", "The Priest's totems", ("Prêtre abattu", "Priest slain", "Son autel est", "His altar is")),
    "Renonce_Chain_Boats": ("Ramener les bateaux", "Bring back the boats", "deposit"),
    "Renonce_Chain_Fort": ("Tenir le fort", "Hold the fort", "defense"),
}


def request_texts():
    for tid, (fr, en, kind) in REQUEST_TEXTS.items():
        if len(fr) > TITLE_MAX or len(en) > TITLE_MAX:
            raise SystemExit(f"titre trop long ({TITLE_MAX} max) : {tid} « {fr} » / « {en} »")
        t(f"request.{tid}.title", fr, en)
        if kind == "deposit":
            task = ("Dépose {count}/{needed} {item} au dépôt du village ({distance} blocs, {direction}).",
                    "Drop {count}/{needed} {item} in the village deposit ({distance} blocks, {direction}).")
        elif kind == "craft":
            task = ("Fabrique et dépose {count}/{needed} {item} au dépôt ({distance} blocs, {direction}).",
                    "Craft and drop {count}/{needed} {item} in the deposit ({distance} blocks, {direction}).")
        elif kind == "missive":
            task = ("Remets la missive au guetteur, à {distance} blocs, {direction}.",
                    "Give the missive to the lookout, {distance} blocks away, {direction}.")
        elif kind == "defense":
            task = ("Repousse le raid de la nuit sur le village. Le cœur du village est à {distance} blocs, {direction}.",
                    "Repel tonight's raid on the village. The village heart is {distance} blocks away, {direction}.")
        elif len(kind) == 4:
            task = (kind[0] + " : {count}/{needed}. " + kind[2] + " à {distance} blocs, {direction}.",
                    kind[1] + ": {count}/{needed}. " + kind[3] + " {distance} blocks away, {direction}.")
        else:
            task = (kind[0] + " : {distance} blocs, {direction}.", kind[1] + ": {distance} blocks, {direction}.")
        t(f"request.{tid}.task", *task)


CHAIN_TEXTS = {
    "Feran": {
        "npc": ("Haute-Brise", "Highbreeze"), "role": ("Cheffe de l'oasis", "Oasis chieftain"),
        "aurevoir": ("Que le vent te garde.", "May the wind keep you."),
        "nouvelles": ("Et la ruche ?", "And the hive?"),
        "nouvellesTexte": ("Elle grossit quand on l'oublie. Taille-la, et elle se fâche. Il n'y a pas de bon choix, seulement du courage.",
                           "It grows when forgotten. Cut it back, and it gets angry. There is no good choice, only courage."),
        "accepter": ("Je m'en charge.", "I'll take care of it."),
        "accepte": ("Va. Le vent t'attendra.", "Go. The wind will wait for you."),
        "auxArmes": ("Les Scaraks sont dans l'oasis ! Défends l'eau, voyageur !", "The Scaraks are in the oasis! Defend the water, traveller!"),
        "honni": ("Tu as troublé l'eau. Va-t'en.", "You have muddied the water. Leave."),
        "etranger": ("La ruche avance sur l'oasis, étranger. Ce n'est pas à toi que je confierai notre eau.",
                     "The hive is advancing on the oasis, stranger. It is not to you that I will entrust our water."),
        "commentAider": ("Comment gagner votre confiance ?", "How do I earn your trust?"),
        "conseil": ("Les besoins du tableau. Quand on te tolérera, reviens me voir.", "The board's needs. When you are tolerated, come back to me."),
        "voirDemandes": ("Voir les besoins", "See the needs"),
        "etape1": ("Le bassin se vide : la ruche boit nos sources. Rapporte-nous huit essences d'eau, et nous verrons si le vent t'aime.",
                   "The basin is emptying: the hive drinks our springs. Bring us eight water essences, and we'll see if the wind likes you."),
        "donner": ("Voici huit essences d'eau.", "Here are eight water essences."),
        "failDonner": ("il faut être Toléré des Feran et porter 8 Essences d'eau", "you must be Tolerated by the Feran and carry 8 Water Essences"),
        "etape2": ("Le bassin se remplit. Pour tenir la ruche à distance, il nous faut du vent : pose quatre statues du vent à l'endroit que je t'indique, quand tu seras notre ami.",
                   "The basin fills. To keep the hive at bay, we need wind: set four wind statues at the spot I'll show you, once you are our friend."),
        "etape2EnCours": ("Quatre statues du vent, pas moins. La marchande en vend, si tu n'en as pas.", "Four wind statues, no fewer. The merchant sells them if you have none."),
        "etape3": ("Le vent souffle. Maintenant, frappe : une entrée de la ruche s'est ouverte près d'ici. Détruis ses gardiens.",
                   "The wind blows. Now strike: a hive entrance has opened nearby. Destroy its guardians."),
        "etape3EnCours": ("L'entrée de la ruche est gardée. Abats-les tous.", "The hive entrance is guarded. Slay them all."),
        "etape4": ("La ruche s'est fâchée. Notre Windwalker est parti voir la ziggourat et ne revient pas. Quand tu seras notre hôte, ramène-le.",
                   "The hive is angry. Our Windwalker went to see the ziggurat and has not returned. When you are our host, bring them back."),
        "etape4EnCours": ("Le Windwalker attend près de la ziggourat. Ramène-le jusqu'au cœur de l'oasis.", "The Windwalker waits near the ziggurat. Bring them back to the heart of the oasis."),
        "etape5": ("Le Windwalker l'a vue : la Broodmother sort de la ruche, à la surface. Seul un champion des Feran peut l'abattre.",
                   "The Windwalker saw her: the Broodmother has come out of the hive, to the surface. Only a champion of the Feran can slay her."),
        "etape5EnCours": ("La Broodmother niche à la surface. Abats-la.", "The Broodmother nests on the surface. Slay her."),
        "recompense": ("La Broodmother est tombée. Le vent te doit une dette : ce bracelet porte un peu de lui. Et le Windwalker a vu des fumées au nord, dans le froid…",
                       "The Broodmother has fallen. The wind owes you a debt: this bracelet carries a little of it. And the Windwalker saw smoke to the north, in the cold…"),
        "recevoir": ("Recevoir le Bracelet de vent", "Receive the Wind Bracelet"),
        "fin": ("Le vent te porte, champion. Au nord, dans la neige, des Outlanders ont renoncé au culte. Ils auront besoin de toi.",
                "The wind carries you, champion. To the north, in the snow, some Outlanders have renounced the cult. They will need you."),
    },
    "Renonce": {
        "npc": ("Celui-qui-a-Rompu", "He-Who-Broke"), "role": ("Sorcier renoncé", "Forsworn sorcerer"),
        "aurevoir": ("Reste près des feux.", "Stay close to the fires."),
        "nouvelles": ("Et le culte ?", "And the cult?"),
        "nouvellesTexte": ("Il ne pardonne pas. Mais il a peur du feu, et des gens qui n'ont plus peur de lui.",
                           "It does not forgive. But it fears fire, and people who no longer fear it."),
        "accepter": ("Je m'en charge.", "I'll take care of it."),
        "accepte": ("Va. Et ne parle de nous à personne.", "Go. And speak of us to no one."),
        "auxArmes": ("Ils viennent nous reprendre ! Défends le hameau !", "They're coming to take us back! Defend the hamlet!"),
        "honni": ("Tu sens leurs totems. Va-t'en.", "You smell of their totems. Leave."),
        "etranger": ("Un étranger… Le culte envoie souvent des étrangers. Prouve que tu n'en es pas.",
                     "A stranger… The cult often sends strangers. Prove you are not one of them."),
        "commentAider": ("Comment gagner votre confiance ?", "How do I earn your trust?"),
        "conseil": ("Le tableau. Aide le hameau. Après, on parlera.", "The board. Help the hamlet. Then we'll talk."),
        "voirDemandes": ("Voir les besoins", "See the needs"),
        "etape1": ("Les fuyards arrivent chaque nuit, affamés. Rapporte huit viandes cuites, et ils verront qu'on peut vivre sans le culte.",
                   "Fugitives arrive every night, starving. Bring eight cooked meats, and they'll see one can live without the cult."),
        "donner": ("Voici huit viandes cuites.", "Here are eight cooked meats."),
        "failDonner": ("il faut être Toléré des Renoncés et porter 8 Viandes cuites", "you must be Tolerated by the Forsworn and carry 8 Cooked Meat"),
        "etape2": ("Ils mangent, merci. Mais le Prêtre plante ses totems autour de nous, et les fuyards l'entendent la nuit. Quand tu seras notre ami, abats-le.",
                   "They eat, thank you. But the Priest plants his totems around us, and the fugitives hear him at night. When you are our friend, slay him."),
        "etape2EnCours": ("Le Prêtre garde son autel. Abats-le.", "The Priest guards his altar. Slay him."),
        "etape3": ("Le Prêtre est tombé, ses totems se taisent. Pour fuir plus loin, il nous faut des bateaux : trente-deux troncs de sapin au dépôt.",
                   "The Priest has fallen, his totems are silent. To flee further, we need boats: thirty-two fir trunks in the deposit."),
        "etape3EnCours": ("Trente-deux troncs de sapin, au dépôt. Les bateaux attendent.", "Thirty-two fir trunks, in the deposit. The boats are waiting."),
        "etape4": ("Les bateaux sont prêts, et les Marauders l'ont vu. Ils viendront une nuit. Quand tu seras notre hôte, tiens le fort avec nous.",
                   "The boats are ready, and the Marauders have seen it. They will come one night. When you are our host, hold the fort with us."),
        "etape4EnCours": ("Cette nuit, les Marauders viendront. Reste au fort, avec nos gardes.", "Tonight, the Marauders will come. Stay at the fort, with our guards."),
        "etape4Attente": ("Les bateaux sont prêts, et les Marauders l'ont vu. Mais nous n'avons pas encore de fort à tenir : aide le hameau à grandir jusqu'à ce que la tour se dresse.",
                          "The boats are ready, and the Marauders have seen it. But we have no fort to hold yet: help the hamlet grow until the tower rises."),
        "recompense": ("Tu as tenu le fort. J'ai tissé ce manteau avec ce qu'il me restait de magie : le froid ne te mordra plus. Je ne le donne qu'à un champion.",
                       "You held the fort. I wove this mantle with what was left of my magic: the cold will bite you no more. I give it only to a champion."),
        "recevoir": ("Recevoir le Manteau du givre", "Receive the Frost Mantle"),
        "fin": ("Le froid te laisse passer, maintenant. Plus loin, au-delà des cols, il y a un monastère. Ce que le Vide y garde, je ne veux pas le savoir.",
                "The cold lets you pass now. Further on, beyond the passes, there is a monastery. What the Void keeps there, I do not want to know."),
    },
}


def chain_texts(pid):
    for k, (fr, en) in CHAIN_TEXTS[pid].items():
        t(f"dialogue.{pid}_Chef.{k}", fr, en)
    steps = {
        "Feran": [("remplir le bassin (8 Essences d'eau, rang Toléré)", "fill the basin (8 Water Essences, Tolerated)"),
                  ("poser 4 statues du vent (rang Ami)", "place 4 wind statues (Friend)"),
                  ("détruire une entrée de la ruche (rang Ami)", "destroy a hive entrance (Friend)"),
                  ("escorter le Windwalker (rang Hôte)", "escort the Windwalker (Host)"),
                  ("abattre la Broodmother, puis recevoir le Bracelet de vent (rang Champion)",
                   "slay the Broodmother, then receive the Wind Bracelet (Champion)")],
        "Renonce": [("nourrir les fuyards (8 Viandes cuites, rang Toléré)", "feed the fugitives (8 Cooked Meat, Tolerated)"),
                    ("abattre le Prêtre et ses totems (rang Ami)", "slay the Priest and his totems (Friend)"),
                    ("ramener les bateaux (32 Troncs de sapin, rang Ami)", "bring back the boats (32 Fir Trunks, Friend)"),
                    ("tenir le fort contre les Marauders (rang Hôte)", "hold the fort against the Marauders (Host)"),
                    ("recevoir le Manteau du givre (rang Champion)", "receive the Frost Mantle (Champion)")],
    }[pid]
    for i, (fr, en) in enumerate(steps, start=1):
        t(f"chain.{pid}.step{i}", fr, en)


def raid_texts():
    for pid, fr_band, en_band, fr_en, en_en in (
            ("Feran", "un essaim scarak", "a Scarak swarm", "les Scaraks", "the Scaraks"),
            ("Renonce", "une bande du culte", "a cult war band", "le culte", "the cult")):
        Fr, En = fr_en[0].upper() + fr_en[1:], en_en[0].upper() + en_en[1:]
        t(f"raid.enemy.{pid}", fr_band, en_band)
        t(f"raid.event.name.{pid}", "Raid scarak" if pid == "Feran" else "Raid du culte",
          "Scarak raid" if pid == "Feran" else "Cult raid")
        t(f"raid.map.arrivesIn.{pid}", Fr + " arrivent dans {time}" if pid == "Feran" else Fr + " arrive dans {time}",
          En + " arrive in {time}" if pid == "Feran" else En + " arrives in {time}")
        verb = "approchent" if pid == "Feran" else "approche"
        t(f"raid.title.warningSub.{pid}", Fr + " " + verb + ", direction {direction}", En + " approach, from the {direction}")
        t(f"raid.title.wave.{pid}", (Fr + " attaquent !") if pid == "Feran" else (Fr + " attaque !"), En + " attack!")
        t(f"raid.report.lost.timeout.{pid}",
          "Bilan du raid sur {village} : défaite. " + Fr + " tenai" + ("ent" if pid == "Feran" else "t") + " encore le village au bout de l'assaut ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
          "Raid report for {village}: defeat. " + En + " still held the village at the end of the assault ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
        t(f"raid.report.lost.abandon.{pid}",
          "Bilan du raid sur {village} : défaite. Personne n'est resté pour défendre le village ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
          "Raid report for {village}: defeat. No one stayed to defend the village ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
        t(f"raid.report.lost.guards.{pid}",
          "Bilan du raid sur {village} : défaite. Tous les gardes sont tombés et " + fr_en + " " + ("ont" if pid == "Feran" else "a") + " atteint le cœur du village ({killed}/{raiders} abattus). Incendié : {building}. Le village perd un palier.",
          "Raid report for {village}: defeat. All the guards fell and " + en_en + " reached the village heart ({killed}/{raiders} slain). Burned: {building}. The village loses a tier.")
        t(f"raid.status.warn.{pid}", "Raid en approche : " + fr_en + " " + ("seront" if pid == "Feran" else "sera") + " là dans {seconds} s.",
          "Raid incoming: " + en_en + " will be here in {seconds} s.")
        t(f"raid.cause.Random.{pid}", "la ruche a faim" if pid == "Feran" else "le culte rôde",
          "the hive is hungry" if pid == "Feran" else "the cult is prowling")
    t("raid.cause.Hive", "la ruche riposte (elle a été taillée)", "the hive strikes back (it was cut down)")
    for suffix, fr, en in [("Scarak_Fighter", "Combattant scarak", "Scarak fighter"), ("Scarak_Louse", "Pou scarak", "Scarak louse"),
                           ("Scarak_Defender", "Défenseur scarak", "Scarak defender"),
                           ("Scarak_Broodmother", "Broodmother de raid", "Raiding Broodmother"),
                           ("Cult_Cultist", "Cultiste", "Cultist"), ("Cult_Berserker", "Berserker du culte", "Cult berserker"),
                           ("Cult_Brute", "Brute du culte", "Cult brute"), ("Cult_Marauder", "Marauder du culte", "Cult marauder")]:
        t(f"npc.Raider_{suffix}.name", fr, en)
    t("items.Nakasar_Peuples_Trophy_Scarak.name", "Trophée scarak", "Scarak trophy")
    t("items.Nakasar_Peuples_Trophy_Scarak.description", "Une plaque de chitine prise aux assaillants d'un raid repoussé.",
      "A plate of chitin taken from the attackers of a repelled raid.")
    t("items.Nakasar_Peuples_Trophy_Cult.name", "Trophée du culte", "Cult trophy")
    t("items.Nakasar_Peuples_Trophy_Cult.description", "Les fétiches des pillards du culte, repoussés loin du hameau.",
      "The fetishes of the cult raiders, driven far from the hamlet.")


def climate_texts():
    k = "climate."
    t("items.Nakasar_Peuples_Oasis_Waterskin.name", "Outre d'oasis", "Oasis waterskin")
    t("items.Nakasar_Peuples_Oasis_Waterskin.description", "Bue, elle chasse la soif des Dunes pendant 20 minutes.",
      "Drink it to keep the thirst of the Dunes away for 20 minutes.")
    t("items.Nakasar_Peuples_Wind_Bracelet.name", "Bracelet de vent", "Wind Bracelet")
    t("items.Nakasar_Peuples_Wind_Bracelet.description", "Un peu du vent des Feran : tant que tu le portes, tu sautes plus haut.",
      "A little of the Feran wind: while you carry it, you jump higher.")
    t("items.Nakasar_Peuples_Frost_Mantle.name", "Manteau du givre", "Frost Mantle")
    t("items.Nakasar_Peuples_Frost_Mantle.description", "Tissé par le Sorcier renoncé. Porté, le froid de la zone 3 ne te mord plus.",
      "Woven by the Forsworn Sorcerer. Worn, the cold of zone 3 no longer bites you.")
    t("effects.Nakasar_Peuples_Thirst", "Soif", "Thirst")
    t("effects.Nakasar_Peuples_Quenched", "Désaltéré", "Quenched")
    t("effects.Nakasar_Peuples_Warmth", "Chaleur", "Warmth")
    t(k + "thirst.start", "La soif te prend : ton endurance ne remonte plus. Cherche l'ombre ou l'eau.",
      "Thirst grips you: your stamina no longer recovers. Find shade or water.")
    t(k + "thirst.stop", "Tu respires mieux : ton endurance remonte.", "You breathe easier: your stamina recovers.")
    t(k + "cold.start", "Le froid te mord. Trouve un abri ou un feu, sinon il te gagnera.",
      "The cold bites. Find shelter or a fire, or it will take you.")
    t(k + "status.thirsty", "Climat : tu as soif (ton endurance ne remonte plus).", "Climate: you are thirsty (stamina does not recover).")
    t(k + "status.cold", "Climat : hypothermie, {stacks}/{max} piles.", "Climate: hypothermia, {stacks}/{max} stacks.")
    t(k + "status.quenched", "Climat : désaltéré.", "Climate: quenched.")
    t(k + "status.fine", "Climat : rien à craindre ici.", "Climate: nothing to fear here.")
    t(k + "seed.wrongZone", "La Graine d'Écho ne prendra que dans les Dunes (zone 2).", "The Echo Seed will only take root in the Dunes (zone 2).")
    t(k + "seed.planted",
      "La Graine d'Écho chante et un bassin naît du sable en {x} {y} {z}. Ici, la soif ne te prendra pas, et les Feran reconnaîtront son chant.",
      "The Echo Seed sings and a pool rises from the sand at {x} {y} {z}. Here thirst will not take you, and the Feran will know its song.")
    t(k + "reveal.Feran", "La Graine d'Écho frémit : elle sent l'eau de l'oasis {village}, en {x} {z} ({distance} blocs).",
      "The Echo Seed stirs: it senses the water of the {village} oasis, at {x} {z} ({distance} blocks).")
    t(k + "reveal.Renonce", "Le Bracelet de vent tire vers le nord : des feux brûlent au hameau {village}, en {x} {z} ({distance} blocs).",
      "The Wind Bracelet pulls north: fires burn at the {village} hamlet, at {x} {z} ({distance} blocks).")
    h = "hive."
    t(h + "status", "Ruche scarak : niveau {level} ({points}/{max} points) : +{extra} Scarak(s) par vague et +{chance} % de raid chaque matin sur les Feran.",
      "Scarak hive: level {level} ({points}/{max} points): +{extra} Scarak(s) per wave and +{chance}% raid chance each morning on the Feran.")
    t(h + "grew", "La ruche scarak grossit (niveau {level}). Les Feran auront plus d'ennemis à leurs portes.",
      "The Scarak hive grows (level {level}). The Feran will face more enemies at their gates.")
    t(h + "cut", "La ruche recule (niveau {level}).", "The hive recedes (level {level}).")
    t(h + "cutRevenge", "La ruche recule (niveau {level}), mais elle s'est fâchée : un raid se prépare contre {village}.",
      "The hive recedes (level {level}), but it is angry: a raid is gathering against {village}.")
    c = "command."
    # command.generate.people : posée par l'étape 7, complétée à la main (trork, feran, renonce).
    t(c + "zone.desc", "Ta zone, son climat, la ruche et les villages des zones 2 et 3", "Your zone, its climate, the hive and the zone 2 and 3 villages")
    t(c + "zone.where", "Tu es en {zone}{forced}.", "You are in {zone}{forced}.")
    t(c + "zone.village", "{people} : {name}, en {x} {z}.", "{people}: {name}, at {x} {z}.")
    t(c + "zone.noVillage", "{people} : pas encore de village dans ce monde.", "{people}: no village in this world yet.")
    t(c + "hive.desc", "État de la ruche scarak, ou ses points fixés (ops)", "Scarak hive status, or set its points (ops)")
    t(c + "hive.arg", "Points (0 à 100, un niveau tous les 20)", "Points (0 to 100, one level every 20)")
    t(c + "seed.desc", "Cherche un site dans la zone du peuple et y pose son village (ops)", "Find a site in the people's zone and place its village (ops)")
    t(c + "seed.arg", "feran ou renonce", "feran or renonce")
    t(c + "seed.unknown", "Peuple sans zone : {people} (feran ou renonce).", "People without a zone: {people} (feran or renonce).")
    t(c + "seed.searching", "Recherche d'un site pour les {people}… (une à deux minutes)", "Looking for a site for the {people}… (one or two minutes)")
    t(c + "seed.failed", "Aucun site trouvé pour les {people} (voir le journal du serveur).", "No site found for the {people} (see the server log).")
    t(c + "seed.done", "Village posé : {name} en {x} {y} {z}.", "Village placed: {name} at {x} {y} {z}.")
    t(c + "climate.desc", "Impose le climat d'une zone, où que tu sois (essai, ops)", "Force a zone's climate wherever you are (test, ops)")
    t(c + "climate.arg", "soif, froid ou aucun", "soif, froid or aucun")
    t(c + "climate.thirst", "Climat imposé : soif des Dunes (le jour, hors de l'ombre et de l'eau).", "Forced climate: Dunes thirst (by day, out of shade and water).")
    t(c + "climate.cold", "Climat imposé : froid de la zone 3 (hors abri et loin d'un feu).", "Forced climate: zone 3 cold (out of shelter and away from fire).")
    t(c + "climate.off", "Climat de la zone réelle rétabli.", "Real zone climate restored.")


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            text = before + after
        existing = {line.split("=", 1)[0].strip() for line in text.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc étape 8) : {dup[:10]}")
        block = [LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END, ""]
        path.write_text("\n".join(block) + text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés de l'étape 8")


# ----------------------------------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", type=Path, help="dossier où écrire l'aperçu PNG des plans")
    args = parser.parse_args()
    bounds = gl.load_bounds()
    failed = False
    crier, merchant = texts()
    for pid, spec in PEOPLES.items():
        doc, rects, errors = gl.build(spec["layout"], spec["layout_spec"], bounds)
        for e in errors:
            print("ERREUR", e)
        failed |= bool(errors)
        doc["$Comment"] = doc["$Comment"].replace("generate_village_layouts.py", "generate_zones.py (étape 8)")
        write(RES / f"Nakasar/VillageLayouts/{spec['layout']}.json", doc)
        print(f"plan {spec['layout']} : {len(doc['Buildings'])} bâtiments, rayon {doc['Radius']}")
        if args.preview:
            gl.preview(spec["layout"], doc, rects, args.preview)
        service_roles(pid, spec)
        job_roles(pid, spec)
        defender(pid, spec)
        raiders(spec["enemy"])
        raid_event(pid, spec["enemy"])
        copy_dialogue(pid, "Crieur")
        copy_dialogue(pid, "Marchand")
        dialogue_texts(pid, crier, merchant)
        job_texts(pid)
        for tid, kind, extra, essor, favors in REQUESTS[pid]:
            write(RES / f"Nakasar/Requests/{pid}/{tid}.json", request_doc(pid, tid, kind, extra, essor, favors))
        chain = CHAINS[pid]
        steps = {"give": chain["give"]}
        for n, tid, kind, extra, rep, fav, rank in chain["templates"]:
            write(RES / f"Nakasar/Requests/{pid}/{tid}.json", chain_doc(pid, n, tid, kind, extra, rep, fav))
            steps[n] = (tid, rank)
        write(RES / f"Nakasar/Dialogues/{pid}/{pid}_Chef.json", chain_dialogue(pid, steps, chain["reward"]))
        chain_texts(pid)
        people_items(pid, spec)
    shops()
    trophies()
    climate_assets()
    map_icons()
    request_texts()
    raid_texts()
    climate_texts()
    write_langs()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
