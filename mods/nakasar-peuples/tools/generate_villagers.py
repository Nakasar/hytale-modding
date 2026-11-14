#!/usr/bin/env python3
"""Villageois à métier du mod Peuples d'Orbis (étape 5 du plan d'implémentation).

Écrit un rôle PNJ par métier (Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_<Peuple>_<Métier>.json) et son
dialogue (Server/Nakasar/Dialogues/<Peuple>/<Peuple>_<Métier>.json). Le plan du village
(tools/generate_village_layouts.py) dit où chaque métier travaille et dort ; le Java (village/Villagers) pose les PNJ
et déplace leur point d'attache (poste le jour, logis la nuit).

Règle n° 2 (AGENTS.md) : apparences vanilla seulement (Server/Models/Intelligent/Kweebec/*.json d'Assets.zip) et
animations vanilla du modèle Kweebec_Sapling (AnimationSets : Interact, Feed, Pet, LookAround, InspectWeapon, Rest).

    python3 tools/generate_villagers.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROLES = ROOT / "src/main/resources/Server/NPC/Roles/Nakasar/Peuples"
DIALOGUES = ROOT / "src/main/resources/Server/Nakasar/Dialogues"

# (peuple, métier, apparence vanilla, animation de travail, rayon d'errance autour du poste)
JOBS = [
    ("Kweebec", "Gardener", "Kweebec_Sapling_Green", "Feed", 3),
    ("Kweebec", "Builder", "Kweebec_Sapling_HardHat", "Interact", 2),
    ("Kweebec", "Watcher", "Kweebec_Sapling_Razorleaf", "LookAround", 2),
    ("Kweebec", "WellKeeper", "Kweebec_Sapling_Brown", "Interact", 2),
    ("Kweebec", "Breeder", "Kweebec_Sapling_Yellow", "Pet", 4),
    ("Kweebec", "Guard", "Kweebec_Sapling_Razorleaf", "InspectWeapon", 3),
    ("Kweebec", "Healer", "Kweebec_Sapling_Red", "Interact", 2),
    ("Kweebec", "Elder", "Kweebec_Sapling_Treesinger", "Rest", 2),
]



def role(people, job, appearance, animation, radius):
    rid = f"Nakasar_Peuples_{people}_{job}"
    return rid, {
        "$Comment": f"Villageois à métier ({job}) d'un village {people.lower()} (étape 5), généré par tools/generate_villagers.py. "
                    "Posé par village/Villagers quand un joueur approche ; le Java déplace son point d'attache (poste le jour, "
                    "logis la nuit) : loin de lui il y marche, près de lui il travaille (animation vanilla) ou flâne. "
                    "L'utiliser ouvre le dialogue de son métier. Ne régénère jamais (VillageNoRegenSystem).",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": f"nakasar_peuples.npc.{people}_{job}.name",
        "MaxHealth": 80,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [
            {"Type": "Walk", "MaxWalkSpeed": 3, "Gravity": 10, "RunThreshold": 0.6, "MaxFallSpeed": 15,
             "MaxRotationSpeed": 360, "Acceleration": 10, "JumpHeight": 1.0}
        ],
        "KnockbackScale": 0.5,
        "Instructions": [
            {
                "Sensor": {"Type": "State", "State": "Idle"},
                "Instructions": [
                    {
                        "$Comment": "Loin de son poste (le Java l'a déplacé) : il y marche.",
                        "Sensor": {"Type": "Leash", "Range": radius + 3},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.5, "SlowDownDistance": 2, "StopDistance": 1,
                                       "UsePathfinder": True},
                    },
                    {
                        "Type": "Random",
                        "Name": "Work",
                        "Instructions": [
                            {
                                "Weight": 45,
                                "Instructions": [
                                    {
                                        "$Comment": "Il travaille sur place.",
                                        "ActionsBlocking": True,
                                        "BodyMotion": {"Type": "Nothing"},
                                        "Actions": [
                                            {"Type": "PlayAnimation", "Slot": "Status", "Animation": animation},
                                            {"Type": "Timeout", "Delay": [4, 7]},
                                            {"Type": "PlayAnimation", "Slot": "Status"},
                                            {"Type": "ResetInstructions", "Instructions": ["Work"]},
                                        ],
                                    }
                                ],
                            },
                            {
                                "Weight": 55,
                                "Instructions": [
                                    {
                                        "Continue": True,
                                        "ActionsAtomic": True,
                                        "Actions": [
                                            {"Type": "Timeout", "Delay": [6, 10]},
                                            {"Type": "ResetInstructions", "Instructions": ["Work"]},
                                        ],
                                    },
                                    {
                                        "$Comment": "Il flâne autour de son poste.",
                                        "BodyMotion": {"Type": "WanderInCircle", "Radius": radius, "RelativeSpeed": 0.3,
                                                       "MaxHeadingChange": 50},
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
        "InteractionInstruction": {
            "Instructions": [
                {"Continue": True, "Sensor": {"Type": "Any"},
                 "Actions": [{"Type": "SetInteractable", "Interactable": True, "Hint": "nakasar_peuples.hint.talk"}]},
                {"Sensor": {"Type": "HasInteracted"}, "Actions": []},
            ]
        },
    }


def dialogue(people, job):
    did = f"{people}_{job}"
    k = f"nakasar_peuples.dialogue.{did}."
    bye = {"TextKey": "nakasar_peuples.dialogue.job.aurevoir"}
    metier = {"TextKey": "nakasar_peuples.dialogue.job.metier", "Next": "Metier"}
    entries = [{"Node": "Accueil"}]
    nodes = [
        {"Id": "Accueil", "TextKey": k + "accueil", "Responses": [metier, bye]},
        {"Id": "Metier", "TextKey": k + "metier", "Responses": [bye]},
    ]
    if job == "Builder":
        status = {"TextKey": "nakasar_peuples.dialogue.job.chantier", "Effects": [{"Type": "ChantierStatus"}],
                  "Next": "Statut"}
        entries = [{"Node": "Chantier", "Conditions": [{"Type": "Chantier"}]}, {"Node": "Accueil"}]
        nodes[0]["Responses"] = [status, metier, bye]
        nodes.insert(0, {"Id": "Chantier", "TextKey": k + "chantier", "Responses": [status, metier, bye]})
        nodes.append({"Id": "Statut", "TextKey": k + "statut", "Responses": [metier, bye]})
    if job in ("Guard", "Watcher"):
        # Étape 6 (GDD, Qui parle et de quoi : « alerte de raid, rumeur sur le camp ennemi ») : pendant un raid, « Aux
        # armes ! » ; sinon une rumeur et l'état du raid attendu (RaidStatus, dans le tchat).
        raid = {"TextKey": "nakasar_peuples.dialogue.job.raid", "Effects": [{"Type": "RaidStatus"}], "Next": "Rumeur"}
        entries.insert(0, {"Node": "AuxArmes", "Conditions": [{"Type": "Raid", "State": "Active"}]})
        nodes[0]["Responses"].insert(0, raid)
        nodes.append({"Id": "AuxArmes", "TextKey": k + "auxArmes", "Responses": [raid, bye]})
        nodes.append({"Id": "Rumeur", "TextKey": k + "rumeur", "Responses": [metier, bye]})
    return did, {
        "$Comment": f"Dialogue du villageois à métier {job} ({'étapes 5 et 6' if job in ('Guard', 'Watcher') else 'étape 5'}), "
                    "généré par tools/generate_villagers.py.",
        "NpcNameKey": k + "npc",
        "RoleKey": k + "role",
        "People": people,
        "Entries": entries,
        "Nodes": nodes,
    }


def main():
    ROLES.mkdir(parents=True, exist_ok=True)
    for people, job, appearance, animation, radius in JOBS:
        rid, doc = role(people, job, appearance, animation, radius)
        (ROLES / f"{rid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        did, ddoc = dialogue(people, job)
        out = DIALOGUES / people / f"{did}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ddoc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{rid} + dialogue {did}")


if __name__ == "__main__":
    main()
