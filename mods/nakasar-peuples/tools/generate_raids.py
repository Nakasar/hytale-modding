#!/usr/bin/env python3
"""Raids du mod Peuples d'Orbis (étape 6 du plan d'implémentation).

Écrit :
  * les assaillants trorks (Server/NPC/Roles/Nakasar/Peuples/Nakasar_Peuples_Raider_Trork_*.json) : apparences, armes,
    attaques et butins vanilla des Trorks (Server/NPC/Roles/Intelligent/Faction/Trork d'Assets.zip) ; ils marchent sur
    le cœur du village (point d'attache posé par le Java, raid/Raids) et frappent joueurs et Kweebecs à vue ;
  * le garde de raid kweebec (Nakasar_Peuples_Kweebec_Defender.json) : apparence, lance et attaques du Razorleaf
    vanilla ; il tient son poste autour du cœur et se bat contre les assaillants ;
  * le groupe de PNJ Nakasar_Peuples_Raiders (les assaillants ne se blessent pas entre eux) ;
  * l'évènement de monde Nakasar_Peuples_Raid et ses étapes (moteur des brèches vanilla) : compte à rebours sur la
    carte, titre et cri de guerre au camp trork, durée du combat.

Le Java mène le raid (minuterie, PNJ, bilan) ; l'évènement ne fait que l'annoncer. Règle n° 1 (AGENTS.md) : aucun de ces
PNJ ne se soigne, jamais (pas de SetStat Health). Règle n° 2 : tout ce qui est visible ou audible est vanilla.

    python3 tools/generate_raids.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "src/main/resources/Server"
ROLES = RES / "NPC/Roles/Nakasar/Peuples"
GROUPS = RES / "NPC/Groups/Nakasar/Peuples"
EVENTS = RES / "WorldEvent/Event/Nakasar/Peuples"
STAGES = RES / "WorldEvent/Stage/Nakasar/Peuples"
ITEMS = RES / "Item/Items/Nakasar/Peuples"

# Durées : mêmes valeurs que raid/Raids.java (WARN_SECONDS, FIGHT_SECONDS).
WARN_SECONDS = 60
FIGHT_SECONDS = 300

TRORK_SWINGS = [
    "Trork_Warrior_Battleaxe_Swing_Left",
    "Trork_Warrior_Battleaxe_Swing_Right",
    "Trork_Warrior_Battleaxe_Swing_Down",
    "Trork_Warrior_Battleaxe_Swing_Up_Left",
    "Trork_Warrior_Battleaxe_Swing_Up_Right",
]
SPEAR_SWINGS = [
    "Kweebec_Sapling_Razorleaf_Spear_Swing_Left",
    "Kweebec_Sapling_Razorleaf_Spear_Swing_Right",
    "Kweebec_Sapling_Razorleaf_Spear_Stab",
]

# (suffixe, apparence vanilla, arme vanilla, butin vanilla, PV, dégâts, vitesse)
RAIDERS = [
    ("Trork_Warrior", "Trork_Warrior", "Weapon_Battleaxe_Stone_Trork", "Drop_Trork_Warrior", 61, 23, 5.0),
    ("Trork_Mauler", "Trork_Mauler", "Weapon_Mace_Crude", "Drop_Trork_Mauler", 61, 23, 4.6),
    ("Trork_Brawler", "Trork_Brawler", "Weapon_Club_Crude", "Drop_Trork_Brawler", 80, 20, 5.4),
    ("Trork_Warlord", "Trork_Guard", "Weapon_Battleaxe_Stone_Trork", "Drop_Trork_Warrior", 150, 28, 4.6),
]


def damage(value):
    return {
        "Melee_Damage": {
            "Interactions": [
                {
                    "Parent": "NPC_Attack_Melee_Damage",
                    "DamageCalculator": {"BaseDamage": {"Physical": value}, "RandomPercentageModifier": 0.1},
                }
            ]
        }
    }


def attack_instruction(swings, reach, pause):
    """Enchaîne les attaques vanilla sur la cible à portée (comme Component_Instruction_Attack_Sequence_Trork_Warrior)."""
    return {
        "Sensor": {"Type": "Target", "Range": reach, "Filters": [{"Type": "LineOfSight"}]},
        "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 1.5},
        "ActionsBlocking": True,
        "Actions": [{"Type": "Attack", "Attack": a, "AttackPauseRange": pause} for a in swings],
    }


def to_combat_on_damage():
    return {"Sensor": {"Type": "Damage", "Combat": True, "TargetSlot": "LockedTarget"},
            "Actions": [{"Type": "State", "State": "Combat"}]}


def foes_in_sight(rng):
    return {
        "Sensor": {"Type": "Mob", "Range": rng, "LockOnTarget": True, "GetPlayers": True, "GetNPCs": True,
                   "Filters": [{"Type": "Attitude", "Attitudes": ["Hostile"]}, {"Type": "LineOfSight"}]},
        "Actions": [{"Type": "State", "State": "Combat"}],
    }


def lost_target(rng):
    return {
        "Sensor": {"Type": "Not", "Sensor": {"Type": "Target", "Range": rng,
                                             "Filters": [{"Type": "Attitude", "Attitudes": ["Hostile", "Neutral", "Ignore"]}]}},
        "Actions": [{"Type": "ReleaseTarget"}, {"Type": "State", "State": "Idle"}],
    }


def raider(suffix, appearance, weapon, drops, hp, dmg, speed):
    rid = f"Nakasar_Peuples_Raider_{suffix}"
    return rid, {
        "$Comment": f"Assaillant trork d'un raid (étape 6), généré par tools/generate_raids.py. Apparence, arme, attaques "
                    f"et butin vanilla ({appearance}). Posé par raid/Raids au camp ; son point d'attache est le cœur du "
                    "village : il y marche et frappe à vue joueurs et Kweebecs (attitude imposée par RaidAttitudeSystem). "
                    "Retiré à la fin du raid. Ne se soigne jamais.",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": f"nakasar_peuples.npc.Raider_{suffix}.name",
        "MaxHealth": hp,
        "DropList": drops,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": ["Nakasar_Peuples_Raiders"],
        "KnockbackScale": 0.6,
        "MotionControllerList": [
            {"Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "MaxFallSpeed": 15, "Acceleration": 10,
             "JumpHeight": 1.2}
        ],
        "HotbarItems": [weapon],
        "InteractionVars": damage(dmg),
        "Instructions": [
            {
                "Sensor": {"Type": "State", "State": "Idle"},
                "Instructions": [
                    to_combat_on_damage(),
                    foes_in_sight(18),
                    {
                        "$Comment": "En marche vers le cœur du village (point d'attache).",
                        "Sensor": {"Type": "Leash", "Range": 5},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.8, "SlowDownDistance": 3, "StopDistance": 2,
                                       "UsePathfinder": True},
                    },
                    {
                        "$Comment": "Au cœur du village : il rôde et cherche des proies.",
                        "BodyMotion": {"Type": "WanderInCircle", "Radius": 8, "RelativeSpeed": 0.6, "MaxHeadingChange": 60},
                    },
                ],
            },
            {
                "Sensor": {"Type": "State", "State": "Combat"},
                "Instructions": [
                    lost_target(28),
                    attack_instruction(TRORK_SWINGS, 2.8, [0.9, 1.4]),
                    {
                        "Sensor": {"Type": "Target", "Range": 28},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 1.0, "SlowDownDistance": 3, "StopDistance": 2.2,
                                       "UsePathfinder": True},
                        "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5},
                    },
                ],
            },
        ],
    }


def defender(people):
    rid = f"Nakasar_Peuples_{people}_Defender"
    return rid, {
        "$Comment": "Garde de raid d'un village kweebec (étape 6), généré par tools/generate_raids.py. Apparence, lance et "
                    "attaques du Razorleaf vanilla. Posé par raid/Raids autour du cœur pendant un raid : il se bat contre les "
                    "assaillants (attitude imposée par RaidAttitudeSystem) sans quitter son poste de plus de 24 blocs. "
                    "Comme tout Kweebec du mod, il compte pour la réputation (groupe Nakasar_Peuples_Kweebec). "
                    "Ne se soigne jamais (règle n° 1) : revenu à son poste, il garde ses blessures.",
        "Type": "Generic",
        "Appearance": "Kweebec_Sapling_Razorleaf",
        "NameTranslationKey": f"nakasar_peuples.npc.{people}_Defender.name",
        "MaxHealth": 105,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": ["Nakasar_Peuples_Kweebec"],
        "KnockbackScale": 0.5,
        "MotionControllerList": [
            {"Type": "Walk", "MaxWalkSpeed": 5.0, "Gravity": 10, "MaxFallSpeed": 15, "Acceleration": 12, "JumpHeight": 1.0}
        ],
        "HotbarItems": ["Weapon_Spear_Leaf"],
        "InteractionVars": damage(14),
        "Instructions": [
            {
                "Sensor": {"Type": "State", "State": "Idle"},
                "Instructions": [
                    to_combat_on_damage(),
                    foes_in_sight(20),
                    {
                        "Sensor": {"Type": "Leash", "Range": 3},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.7, "SlowDownDistance": 2, "StopDistance": 1,
                                       "UsePathfinder": True},
                    },
                    {
                        "$Comment": "À son poste : il guette.",
                        "BodyMotion": {"Type": "WanderInCircle", "Radius": 2, "RelativeSpeed": 0.3, "MaxHeadingChange": 50},
                    },
                ],
            },
            {
                "Sensor": {"Type": "State", "State": "Combat"},
                "Instructions": [
                    {
                        "$Comment": "Il ne s'éloigne pas du village : à plus de 24 blocs de son poste, il lâche sa cible.",
                        "Sensor": {"Type": "Leash", "Range": 24},
                        "Actions": [{"Type": "ReleaseTarget"}, {"Type": "State", "State": "Idle"}],
                    },
                    lost_target(26),
                    attack_instruction(SPEAR_SWINGS, 3.2, [0.8, 1.2]),
                    {
                        "Sensor": {"Type": "Target", "Range": 26},
                        "BodyMotion": {"Type": "Seek", "RelativeSpeed": 1.0, "SlowDownDistance": 3, "StopDistance": 2.6,
                                       "UsePathfinder": True},
                        "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5},
                    },
                ],
            },
        ],
    }


def event():
    return {
        "$Comment": "Raid d'un village (étape 6), généré par tools/generate_raids.py. Lancé par raid/Raids, une instance par "
                    "raid (plusieurs villages peuvent être attaqués la même nuit) ; le Java le stoppe au bilan. Il annonce "
                    "seulement : compte à rebours sur la carte, titre et cri de guerre au camp trork (lieu donné par la "
                    "condition Nakasar_Peuples_RaidLocation), durée du combat. Icône de la brèche gobeline vanilla.",
        "Root": "Nakasar_Peuples_Raid_Warn",
        "IterationCount": 1,
        "InstanceCountMax": -1,
        "Name": "nakasar_peuples.raid.event.name",
        "Icon": "UI/WorldMap/MapMarkers/GoblinBreach.png",
    }


def stage_warn():
    return {
        "$Comment": f"Annonce : {WARN_SECONDS} s avant l'arrivée de la bande (compte à rebours sur la carte), puis titre et "
                    "cri de guerre au camp trork, au moment où le Java fait apparaître la vague.",
        "Forks": [
            {
                "Conditions": [
                    {"Type": "Nakasar_Peuples_RaidLocation", "LocationKey": "RaidLocation"},
                    {"Type": "IntervalCondition", "IntervalKey": "RaidWarning", "MinSeconds": WARN_SECONDS,
                     "MaxSeconds": WARN_SECONDS, "ShowOnMap": True, "MapIntervalKey": "nakasar_peuples.raid.map.arrivesIn"},
                ],
                "Actions": [
                    {"Type": "ShowEventTitleAction", "LocationKey": "RaidLocation", "Radius": 160,
                     "PrimaryTitle": "nakasar_peuples.raid.title.wave", "SecondaryTitle": "nakasar_peuples.raid.title.waveEvent",
                     "FadeInDuration": 0.5},
                    {"Type": "EffectsAction", "LocationKey": "RaidLocation", "Radius": 120,
                     "Shape": {"Type": "Point", "Count": 1}, "SoundFX": {"Effect": "SFX_Trork_Chieftain_Alerted"}},
                ],
                "Next": "Nakasar_Peuples_Raid_Fight",
            }
        ],
    }


def stage_fight():
    return {
        "$Comment": f"Le combat : {FIGHT_SECONDS} s au plus (« … restant » sur la carte, marge de 30 s : le Java stoppe "
                    "l'évènement au bilan).",
        "Forks": [
            {
                "Conditions": [
                    {"Type": "IntervalCondition", "IntervalKey": "RaidFight", "MinSeconds": FIGHT_SECONDS + 30,
                     "MaxSeconds": FIGHT_SECONDS + 30, "ShowOnMap": True, "MapIntervalKey": "server.map.worldEvents.runsFor"}
                ]
            }
        ],
    }


def trophy():
    return {
        "$Comment": "Trophée trork : donné au bilan d'un raid gagné à chaque joueur qui a abattu un assaillant (étape 6). "
                    "Modèle, texture et icône des crânes vanilla (Deco_Bone_Skulls), sans usage pour l'instant.",
        "TranslationProperties": {
            "Name": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Trork.name",
            "Description": "nakasar_peuples.items.Nakasar_Peuples_Trophy_Trork.description",
        },
        "Icon": "Icons/ItemsGenerated/Bone_Skulls.png",
        "Categories": ["Items.Ingredients"],
        "Model": "Blocks/Dungeons/Bone_Skulls.blockymodel",
        "Texture": "Blocks/Dungeons/Bone_Skulls_Texture.png",
        "PlayerAnimationsId": "Item",
        "Quality": "Rare",
        "MaxStack": 25,
        "IconProperties": {"Scale": 0.58823, "Translation": [1.8, -9], "Rotation": [0, 293.625, 336.375]},
        "ItemSoundSetId": "ISS_Items_Bones",
    }


def echo_seed():
    return {
        "$Comment": "Graine d'Écho : fin de la chaîne de quêtes kweebec (étape 6). Plantée en zone 2 (clic droit, étape 8), "
                    "elle fait jaillir une source qui abrite de la soif (Java Nakasar_Peuples_ZoneItem, Action EchoSeed). "
                    "Modèle, texture et icône du sac de graines de chêne vanilla (Plant_Seeds_Oak).",
        "TranslationProperties": {
            "Name": "nakasar_peuples.items.Nakasar_Peuples_Echo_Seed.name",
            "Description": "nakasar_peuples.items.Nakasar_Peuples_Echo_Seed.description",
        },
        "Icon": "Icons/ItemsGenerated/Plant_Seeds_Oak.png",
        "Categories": ["Items.Ingredients"],
        "Model": "Resources/Plants/SeedBag.blockymodel",
        "Texture": "Resources/Plants/SeedBag_Textures/Oak.png",
        "PlayerAnimationsId": "Item",
        "Quality": "Legendary",
        "MaxStack": 1,
        "IconProperties": {"Scale": 1.1, "Rotation": [0, 30, 15], "Translation": [2.5, -11]},
        "ItemEntity": {"ParticleSystemId": None},
        "ItemSoundSetId": "ISS_Items_Foliage",
        "Interactions": {"Secondary": "Root_Nakasar_Peuples_Plant_Echo_Seed"},
    }


def write(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(path.relative_to(ROOT))


def main():
    for r in RAIDERS:
        rid, doc = raider(*r)
        write(ROLES / f"{rid}.json", doc)
    rid, doc = defender("Kweebec")
    write(ROLES / f"{rid}.json", doc)
    write(GROUPS / "Nakasar_Peuples_Raiders.json", {
        "$Comment": "Assaillants des raids (étape 6) : ils ne se blessent pas entre eux (DisableDamageGroups).",
        "IncludeRoles": ["Nakasar_Peuples_Raider_*"],
    })
    write(EVENTS / "Nakasar_Peuples_Raid.json", event())
    write(STAGES / "Nakasar_Peuples_Raid_Warn.json", stage_warn())
    write(STAGES / "Nakasar_Peuples_Raid_Fight.json", stage_fight())
    write(ITEMS / "Nakasar_Peuples_Trophy_Trork.json", trophy())
    write(ITEMS / "Nakasar_Peuples_Echo_Seed.json", echo_seed())


if __name__ == "__main__":
    main()
