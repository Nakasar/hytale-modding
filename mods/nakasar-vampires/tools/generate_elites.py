#!/usr/bin/env python3
"""Génère l'armure enchantée et le Spectre, deux élites du Comté, avec leurs serviteurs.

    python3 mods/nakasar-vampires/tools/generate_elites.py [--preview DOSSIER]

Armure enchantée (Nakasar_Enchanted_Armor), dans une crypte sur deux, au fond de la salle enterrée :
- grosse armure vide animée (modèle vanilla Shadow_Knight, Server/Models/Nakasar/Nakasar_Enchanted_Armor.json)
  armée d'une massue ; n'est pas une morte-vivante (le feu purificateur ne la gêne pas) et ne prend aucun dégât de
  feu (groupe Nakasar_Fire_Immune, FireAffinitySystem) ;
- coups de massue, et un coup sismique annoncé (elle s'immobilise, rougeoie, une zone rouge de 4,5 blocs se charge
  au sol) ;
- fait apparaître trois rouages enchantés (Nakasar_Enchanted_Gear, tools/generate_gear_model.py) qui la soignent
  petit à petit tant qu'ils vivent (SummonMinionsInteraction, HealSummonerPerSecond) ; on peut les détruire, elle
  en refait venir toutes les 18 à 22 s ;
- lâche deux éclats de rune et son trophée.

Spectre (Nakasar_Spectre), dans un château hanté sur deux et un cimetière hanté sur trois :
- grand fantôme (modèle vanilla Wraith) qui flotte bas ; toucher glacial ;
- invoque trois fantômes (Nakasar_Spectral_Ghost) et reste invulnérable tant qu'il en reste (MinionShieldSystem) ;
  la vague suivante vient 14 à 16 s après la mort de la précédente ;
- vague de froid annoncée : il s'immobilise, une zone rouge de 6 blocs se charge au sol pendant 1,6 s, puis le
  froid ralentit fortement tous ceux qui y sont restés (Nakasar_Spectre_Frost) ;
- lâche un éclat de rune, une relique du manoir et son trophée.

Les deux ont une barre de boss (BossBarSystem) et un contrat de chasseurs (generate_contracts.py). Écrit les rôles,
groupes, interactions, effets, butins, marqueurs et blocs d'apparition, et l'icône d'effet du froid.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
SERVER = PACK / "Server"
COMMON = PACK / "Common"
ROLES = SERVER / "NPC/Roles/Nakasar"
GROUPS = SERVER / "NPC/Groups"
MARKERS = SERVER / "NPC/Spawn/Markers"
SPAWNERS = SERVER / "Item/Items/Spawner/Nakasar"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/NPC"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/NPC"
EFFECTS = SERVER / "Entity/Effects/Nakasar"
DROPS = SERVER / "Drops/Nakasar"

ARMOR = "Nakasar_Enchanted_Armor"
GEAR = "Nakasar_Enchanted_Gear"
SPECTRE = "Nakasar_Spectre"
SHADE = "Nakasar_Spectral_Ghost"
CONSTRUCTS = "Nakasar_Enchanted_Constructs"
FIRE_IMMUNE = "Nakasar_Fire_Immune"
SHADES = "Nakasar_Spectral_Ghosts"
FROST = "Nakasar_Spectre_Frost"
SHARD = "Ingredient_Rune_Shard"
RELIC = "Ingredient_Nakasar_Manor_Relic"
MACE = "Weapon_Mace_Onyxium"

ARMOR_SLAM_RADIUS = 4.5
COLD_WAVE_RADIUS = 6.0
# Feastmaster_Slam_Warning détaché : échelle ≈ 0,68 × rayon (vanilla 3,4 pour un AOECircle de 5).
WARNING_SCALE = 0.68


# --- briques communes ------------------------------------------------------------------------

def timer(name, start, restart):
    return {"Type": "TimerStart", "Name": name, "StartValueRange": list(start), "RestartValueRange": list(restart)}


def to_combat_on_sight(rng, los=True):
    filters = [{"Type": "Attitude", "Attitudes": ["Hostile"]}] + ([{"Type": "LineOfSight"}] if los else [])
    return [
        {"Sensor": {"Type": "Damage", "Combat": True, "TargetSlot": "LockedTarget"},
         "Actions": [{"Type": "State", "State": "Combat"}]},
        {"Sensor": {"Type": "Player", "Range": rng, "LockOnTarget": True, "Filters": filters},
         "Actions": [{"Type": "State", "State": "Combat"}]},
        {"$Comment": "Un mob hostile (chasseur de vampires, mob dominé…) : même réaction qu'envers un joueur.",
         "Sensor": {"Type": "Mob", "Range": rng, "LockOnTarget": True, "Filters": filters},
         "Actions": [{"Type": "State", "State": "Combat"}]},
    ]


def lost_target(rng, actions):
    return {"Sensor": {"Type": "Not", "Sensor": {"Type": "Target", "Range": rng, "Filters": [
        {"Type": "Attitude", "Attitudes": ["Hostile", "Neutral", "Ignore"]}]}},
        "Actions": [{"Type": "ReleaseTarget"}] + actions}


def timed_attack(timer_name, attack, rng=None, los=False, aim=None, comment=None):
    sensors = [{"Type": "Timer", "Name": timer_name, "State": "STOPPED"}]
    if rng is not None:
        target = {"Type": "Target", "Range": rng}
        if los:
            target["Filters"] = [{"Type": "LineOfSight"}]
        sensors.insert(0, target)
    attack_action = {"Type": "Attack", "Attack": attack}
    if aim is None:
        attack_action.update({"SkipAiming": True, "LineOfSight": False, "AvoidFriendlyFire": False})
    else:
        attack_action["AimingTimeRange"] = aim
    doc = {"Sensor": sensors[0] if len(sensors) == 1 else {"Type": "And", "Sensors": sensors},
           "ActionsBlocking": True,
           "Actions": [{"Type": "TimerRestart", "Name": timer_name}, attack_action]}
    if rng is not None:  # Watch exige une cible fournie par le capteur
        doc["HeadMotion"] = {"Type": "Watch", "RelativeTurnSpeed": 1.0}
    if comment:
        doc = {"$Comment": comment, **doc}
    return doc


def warning(radius, seconds):
    """Zone rouge qui se charge au sol (détachée du modèle : elle ne suit pas l'élite)."""
    return {"SystemId": "Feastmaster_Slam_Warning", "TargetEntityPart": "Entity", "TargetNodeName": "Origin",
            "Scale": round(WARNING_SCALE * radius, 2), "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0},
            "DetachedFromModel": True}


def ground_particles(system, scale):
    return {"SystemId": system, "TargetEntityPart": "Entity", "TargetNodeName": "Origin", "Scale": scale,
            "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0}, "DetachedFromModel": True}


def melee_tag(*names, comment=None):
    doc = {"Tags": {"Attack": ["Melee"]}, "Interactions": list(names)}
    return {"$Comment": comment, **doc} if comment else doc


def damage(amount, extra=None, sound=None, particles=None, knockback=None, interrupt=False):
    effects = {}
    if sound:
        effects["WorldSoundEventId"] = sound
    if particles:
        effects["WorldParticles"] = [{"SystemId": particles}]
    if knockback:
        effects["Knockback"] = {"Type": "Force", "Force": knockback, "VelocityType": "Set", "Direction": {"Y": 1}}
    doc = {"Parent": "DamageEntityParent_Hit_Interrupt" if interrupt else "DamageEntityParent",
           "DamageCalculator": {"BaseDamage": {"Physical": amount}, "RandomPercentageModifier": 0.1}}
    if effects:
        doc["DamageEffects"] = effects
    return [doc] + (extra or [])


# --- armure enchantée ------------------------------------------------------------------------

def armor_swing(side):
    direction = "ToLeft" if side == "Left" else "ToRight"
    return {
        "$Comment": f"Coup de massue ordinaire de l'armure enchantée ({'gauche' if side == 'Left' else 'droite'}).",
        "Type": "Simple",
        "RunTime": 0.45,
        "Effects": {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": f"Swing{side}",
                    "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"},
        "Next": {
            "Type": "Selector",
            "RunTime": 0.15,
            "Selector": {"Id": "Horizontal", "Direction": direction, "TestLineOfSight": True, "ExtendTop": 0.8,
                         "ExtendBottom": 0.8, "StartDistance": 0.3, "EndDistance": 3.8, "Length": 100,
                         "RollOffset": 15, "YawStartOffset": 50 if side == "Left" else -50},
            "HitEntity": {"Interactions": damage(28, sound="SFX_T1_Impact_Blunt", particles="Impact_Sword_Basic_Stronk")},
        },
    }


def armor_slam():
    return {
        "$Comment": f"Coup sismique annoncé de l'armure enchantée : elle s'immobilise 1,4 s, rougeoie et lève sa massue pendant qu'une zone rouge de {ARMOR_SLAM_RADIUS} blocs se charge au sol, puis frappe le sol (40 dégâts, projection). On l'évite en sortant de la zone.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "ApplyEffect", "EffectId": "Dungeon_Goblin_Mace_Slam_Charge"},
            {"Type": "Simple", "RunTime": 1.4, "Effects": {
                "ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharging",
                "WorldSoundEventId": "SFX_Spear_Throw_Charge",
                "Particles": [warning(ARMOR_SLAM_RADIUS, 1.4)]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharged",
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.0)]},
             "Selector": {"Id": "AOECircle", "Range": ARMOR_SLAM_RADIUS},
             "HitEntity": {"Interactions": damage(40, sound="SFX_Mace_T2_Signature_Impact", knockback=9)}},
            {"Type": "Simple", "RunTime": 0.7},
        ],
    }


def armor_summon():
    return {
        "$Comment": "L'armure enchantée appelle ses rouages : elle lève sa massue, des runes bleues s'allument au sol et jusqu'à trois rouages enchantés (Nakasar_Enchanted_Gear) apparaissent entre 2,5 et 5 blocs d'elle. Chaque rouage vivant lui rend 5 PV par seconde (Nakasar_SummonMinions, HealSummonerPerSecond) : il faut les détruire.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "Simple", "RunTime": 0.8, "Effects": {
                "ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "Guard",
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted"}},
            {"Type": "Simple", "RunTime": 0.2, "Effects": {
                "WorldSoundEventId": "SFX_Spirit_Root_Spawn",
                "Particles": [ground_particles("Praetorian_Summon_Ground", 1.6)]},
             "Next": {"Type": "Nakasar_SummonMinions", "MinionRole": GEAR, "Count": 3, "MaxAlive": 3,
                      "MinDistance": 2.5, "MaxDistance": 5, "MinSpacing": 2, "HealSummonerPerSecond": 5}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def armor_role():
    return {
        "$Comment": "Armure enchantée (élite) d'une crypte sur deux, au fond de la salle enterrée, avec barre de vie de boss (BossBarSystem). Grosse armure vide animée, armée d'une massue : ce n'est pas une morte-vivante (le feu purificateur ne la gêne pas) et le feu ne lui fait rien (groupe Nakasar_Fire_Immune). Coups de massue, coup sismique annoncé par une zone rouge de 4,5 blocs, et toutes les 18 à 22 s elle complète ses trois rouages enchantés qui la soignent de 5 PV par seconde chacun tant qu'ils vivent. Immobile comme une statue tant que rien ne passe ; retourne à sa place et regagne sa vie si on fuit à plus de 24 blocs. Générée par tools/generate_elites.py.",
        "Type": "Generic",
        "Appearance": ARMOR,
        "NameTranslationKey": "nakasar_mobs.npc.Enchanted_Armor.name",
        "MaxHealth": 900,
        "DropList": "Nakasar_Drop_Enchanted_Armor",
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [CONSTRUCTS],
        "KnockbackScale": 0.1,
        "DeathAnimationTime": 2.0,
        "HotbarItems": [MACE],
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 3.4, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "StateTransitions": [{
            "$Comment": "Entrée en combat : chaque attaque spéciale a sa propre recharge ; les rouages viennent vite.",
            "States": [{"From": ["Idle", "ReturnHome"], "To": ["Combat"]}],
            "Actions": [timer("Summon", (2, 3), (18, 22)), timer("Slam", (6, 8), (11, 14))],
        }],
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"},
             "Instructions": to_combat_on_sight(14) + [{"Actions": []}]},
            {"Sensor": {"Type": "State", "State": "Combat"}, "Instructions": [
                {"$Comment": "Cible perdue ou partie trop loin : elle retourne à sa place.",
                 **lost_target(24, [{"Type": "State", "State": "ReturnHome"}])},
                timed_attack("Summon", "Root_Nakasar_NPC_Armor_Summon",
                             comment="Rouages enchantés : elle complète la vague (trois au plus) dès l'entrée en combat, puis toutes les 18 à 22 s."),
                timed_attack("Slam", "Root_Nakasar_NPC_Armor_Slam", rng=4.5, los=True,
                             comment="Coup sismique annoncé quand la cible est à moins de 4,5 blocs."),
                {"Sensor": {"Type": "Target", "Range": 3.6, "Filters": [{"Type": "LineOfSight"}]},
                 "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 1.2},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "Attack", "Attack": "Root_Nakasar_NPC_Armor_Attack", "AttackPauseRange": [1.2, 1.8]},
                             {"Type": "Timeout", "Delay": [0.2, 0.2]}]},
                {"Sensor": {"Type": "Target", "Range": 24},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.9, "SlowDownDistance": 3, "StopDistance": 2.6,
                                "UsePathfinder": True},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.2}},
            ]},
            {"Sensor": {"Type": "State", "State": "ReturnHome"}, "Instructions": [
                {"Sensor": {"Type": "Damage", "Combat": True, "TargetSlot": "LockedTarget"},
                 "Actions": [{"Type": "State", "State": "Combat"}]},
                {"Sensor": {"Type": "Leash", "Range": 2},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.7, "SlowDownDistance": 3, "StopDistance": 1,
                                "UsePathfinder": True}},
                {"$Comment": "De retour à sa place : elle récupère toute sa vie.",
                 "Actions": [{"Type": "SetStat", "Stat": "Health", "Value": 1000000}, {"Type": "State", "State": "Idle"}]},
            ]},
        ],
    }


def gear_role():
    return {
        "$Comment": "Rouage enchanté, appelé par l'armure enchantée (Nakasar_SummonMinions) : il flotte sans bouger ni attaquer et, tant qu'il vit, rend 5 PV par seconde à son armure. Fragile (30 PV), insensible au feu comme elle. Disparaît avec son armure, ou au bout de 30 s sans personne à proximité. Généré par tools/generate_elites.py.",
        "Type": "Generic",
        "Appearance": GEAR,
        "NameTranslationKey": "nakasar_mobs.npc.Enchanted_Gear.name",
        "MaxHealth": 30,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [CONSTRUCTS],
        "KnockbackScale": 0,
        "DeathAnimationTime": 1.0,
        "SpawnLockTime": 0.5,
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 12, "JumpHeight": 0}],
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": to_combat_on_sight(16, los=False) + [
                {"$Comment": "Personne pendant 30 s (armure rendormie, cible partie) : il s'éteint.",
                 "Actions": [{"Type": "Timeout", "Delay": [30, 30], "Action": {"Type": "Despawn"}}]}]},
            {"Sensor": {"Type": "State", "State": "Combat"}, "Instructions": [
                lost_target(20, [{"Type": "State", "State": "Idle"}]),
                {"Sensor": {"Type": "Target", "Range": 20}, "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.0}},
            ]},
        ],
    }


# --- Spectre ---------------------------------------------------------------------------------

def spectre_touch():
    return {
        "$Comment": "Toucher glacial du Spectre : plus fort que celui d'un fantôme, il ralentit aussi (Nakasar_Ghost_Chill).",
        "Type": "Simple",
        "RunTime": 0.4,
        "Effects": {"ItemAnimationId": "SwingDown", "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"},
        "Next": {
            "Type": "Selector",
            "RunTime": 0.1,
            "Selector": {"Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": False, "ExtendTop": 1.0,
                         "ExtendBottom": 1.0, "StartDistance": 0.1, "EndDistance": 3.2, "Length": 90,
                         "RollOffset": 0, "YawStartOffset": -45},
            "HitEntity": {"Interactions": damage(16, interrupt=True, particles="Impact_Ice", extra=[
                {"Type": "ApplyEffect", "EffectId": "Nakasar_Ghost_Chill", "Entity": "Target", "Duration": 3}])},
        },
    }


def spectre_cold_wave():
    return {
        "$Comment": f"Vague de froid du Spectre, annoncée : il s'immobilise 1,6 s, la glace se forme autour de lui et une zone rouge de {COLD_WAVE_RADIUS:g} blocs se charge au sol ; puis le froid éclate (10 dégâts) et ralentit fortement tous ceux restés dans la zone pendant 6 s ({FROST}). On l'évite en sortant de la zone.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.6, "Effects": {
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                "Particles": [warning(COLD_WAVE_RADIUS, 1.6),
                              {"SystemId": "Ice_Staff_Charging", "TargetNodeName": "Chest", "Scale": 1.5}]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Ice_Blast", 1.6), ground_particles("Rings_Rings_Ice", 2.0)]},
             "Selector": {"Id": "AOECircle", "Range": COLD_WAVE_RADIUS},
             "HitEntity": {"Interactions": damage(10, particles="Impact_Ice", extra=[
                 {"Type": "Nakasar_ApplyEffectToFoes", "EffectId": FROST, "Duration": 6}])}},
            {"Type": "Simple", "RunTime": 0.6},
        ],
    }


def spectre_summon():
    return {
        "$Comment": "Le Spectre appelle ses fantômes : il se fige dans une brume de givre, puis trois fantômes (Nakasar_Spectral_Ghost) apparaissent entre 2,5 et 5 blocs de lui (Nakasar_SummonMinions). Tant qu'il en reste un, il est invulnérable (MinionShieldSystem).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "Simple", "RunTime": 0.8, "Effects": {
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                "Particles": [{"SystemId": "Weapon_Frost_Mist", "TargetNodeName": "Chest", "Scale": 2.0}]}},
            {"Type": "Simple", "RunTime": 0.2, "Effects": {
                "WorldSoundEventId": "SFX_Spirit_Root_Spawn",
                "Particles": [ground_particles("Praetorian_Summon_Ground", 1.6)]},
             "Next": {"Type": "Nakasar_SummonMinions", "MinionRole": SHADE, "Count": 3, "MaxAlive": 3,
                      "MinDistance": 2.5, "MaxDistance": 5, "MinSpacing": 2}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def fly(speed, min_h, max_h):
    return [{"Type": "Fly", "MaxHorizontalSpeed": speed, "MaxClimbSpeed": 3, "MaxSinkSpeed": 3, "Acceleration": 3,
             "Deceleration": 3, "Gravity": 1, "MinHeightOverGround": min_h, "MaxHeightOverGround": max_h}]


def blink(rng):
    return {"$Comment": "Apparition soudaine près de la cible quand elle s'éloigne.",
            "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": rng},
                                                  {"Type": "Not", "Sensor": {"Type": "Target", "Range": 7}},
                                                  {"Type": "Timer", "Name": "Blink", "State": "STOPPED"}]},
            "BodyMotion": {"Type": "Teleport", "OffsetRange": [2, 3], "MaxYOffset": 1, "Orientation": "TowardsTarget"},
            "Actions": [{"Type": "TimerRestart", "Name": "Blink"}]}


def spectre_role():
    return {
        "$Comment": "Spectre (élite) d'un château hanté sur deux et d'un cimetière sur sept environ (Cemeteries/Spectre, poids 0,5), avec barre de vie de boss (BossBarSystem). Grand fantôme qui flotte bas. Dès le combat, il invoque trois fantômes et reste invulnérable tant qu'il en reste (MinionShieldSystem) ; une fois la vague détruite, il est vulnérable 14 à 16 s, puis en appelle une autre. Toucher glacial, et une vague de froid annoncée par une zone rouge de 6 blocs qui ralentit fortement ceux qui y restent. Disparaît et réapparaît près de sa cible quand elle s'éloigne. Si on le fuit, il se calme et regagne sa vie. Mort-vivant (feu purificateur). Généré par tools/generate_elites.py.",
        "Type": "Generic",
        "Appearance": SPECTRE,
        "NameTranslationKey": "nakasar_mobs.npc.Spectre.name",
        "MaxHealth": 550,
        "DropList": "Nakasar_Drop_Spectre",
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": ["Nakasar_Ghosts"],
        "KnockbackScale": 0.2,
        "DeathAnimationTime": 1.5,
        "MotionControllerList": fly(4.5, 0.3, 1.5),
        "StateTransitions": [{
            "$Comment": "Entrée en combat : chaque attaque spéciale a sa propre recharge ; les fantômes viennent tout de suite.",
            "States": [{"From": ["Idle"], "To": ["Combat"]}],
            "Actions": [timer("Summon", (0.3, 0.6), (14, 16)), timer("ColdWave", (5, 7), (13, 16)),
                        timer("Blink", (4, 6), (8, 11))],
        }],
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": to_combat_on_sight(16, los=False) + [
                {"BodyMotion": {"Type": "WanderInCircle", "Radius": 6, "RelativeSpeed": 0.25, "MaxHeadingChange": 50}}]},
            {"Sensor": {"Type": "State", "State": "Combat"}, "Instructions": [
                {"$Comment": "Cible perdue ou partie à plus de 28 blocs : il se calme et regagne toute sa vie.",
                 **lost_target(28, [{"Type": "SetStat", "Stat": "Health", "Value": 1000000},
                                    {"Type": "State", "State": "Idle"}])},
                {"$Comment": "Tant qu'il reste des fantômes, la prochaine vague attend : le délai repart à chaque instant, il ne s'écoule qu'une fois la vague détruite. Il continue ensuite ses autres attaques (Continue).",
                 "Continue": True,
                 "Sensor": {"Type": "Count", "Count": [1, 64], "Range": [0, 40], "IncludeGroups": [SHADES]},
                 "Actions": [timer("Summon", (14, 16), (14, 16))]},
                timed_attack("Summon", "Root_Nakasar_NPC_Spectre_Summon",
                             comment="Invocation des fantômes : dès l'entrée en combat, puis 14 à 16 s après la mort de la vague précédente."),
                timed_attack("ColdWave", "Root_Nakasar_NPC_Spectre_ColdWave", rng=6,
                             comment="Vague de froid annoncée quand la cible est à moins de 6 blocs."),
                blink(22),
                {"Sensor": {"Type": "Target", "Range": 3.0},
                 "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 1.5},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "Attack", "Attack": "Root_Nakasar_NPC_Spectre_Touch", "AttackPauseRange": [1.2, 1.8]},
                             {"Type": "Timeout", "Delay": [0.2, 0.2]}]},
                {"Sensor": {"Type": "Target", "Range": 28},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.75, "SlowDownDistance": 3, "StopDistance": 2.0,
                                "UsePathfinder": False},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.2}},
            ]},
        ],
    }


def shade_role():
    return {
        "$Comment": "Fantôme invoqué par le Spectre (Nakasar_SummonMinions) : comme un fantôme du Comté mais plus fragile (25 PV), sans butin. Tant qu'il en reste un, le Spectre est invulnérable. Disparaît avec son maître, ou au bout de 30 s sans combat. Généré par tools/generate_elites.py.",
        "Type": "Generic",
        "Appearance": SHADE,
        "NameTranslationKey": "nakasar_mobs.npc.Spectral_Ghost.name",
        "MaxHealth": 25,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": ["Nakasar_Ghosts"],
        "KnockbackScale": 1.5,
        "SpawnLockTime": 0.5,
        "MotionControllerList": fly(5, 0.5, 3),
        "StateTransitions": [{"States": [{"From": ["Idle"], "To": ["Combat"]}],
                              "Actions": [timer("Blink", (3, 5), (6, 9))]}],
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": to_combat_on_sight(18, los=False) + [
                {"$Comment": "Sans combat pendant 30 s (Spectre calmé, cible partie) : il se dissipe.",
                 "Actions": [{"Type": "Timeout", "Delay": [30, 30], "Action": {"Type": "Despawn"}}]}]},
            {"Sensor": {"Type": "State", "State": "Combat"}, "Instructions": [
                lost_target(28, [{"Type": "State", "State": "Idle"}]),
                blink(20),
                {"Sensor": {"Type": "Target", "Range": 2.6},
                 "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 1.5},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "Attack", "Attack": "Root_Nakasar_NPC_Ghost_Touch", "AttackPauseRange": [1.4, 2.0]},
                             {"Type": "Timeout", "Delay": [0.2, 0.2]}]},
                {"Sensor": {"Type": "Target", "Range": 28},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.8, "SlowDownDistance": 3, "StopDistance": 1.6,
                                "UsePathfinder": False},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.2}},
            ]},
        ],
    }


# --- effets, butins, groupes, apparitions ----------------------------------------------------

def frost_effect():
    return {
        "$Comment": "Vague de froid du Spectre : fortement ralenti (60 %) pendant 6 s, givré.",
        "Name": "nakasar_mobs.effects.Nakasar_Spectre_Frost",
        "Duration": 6,
        "OverlapBehavior": "Overwrite",
        "Debuff": True,
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Spectre_Frost.png",
        "ApplicationEffects": {"EntityTopTint": "#f2fbff", "EntityBottomTint": "#7cc8ff", "HorizontalSpeedMultiplier": 0.4},
    }


def single(item, lo, hi=None):
    return {"Type": "Single", "Item": {"ItemId": item, "QuantityMin": lo, "QuantityMax": hi or lo}}


def drops():
    return {
        "Nakasar_Drop_Enchanted_Armor": {"$Comment": "Armure enchantée : deux éclats de rune (exception voulue : les mobs du mod n'en lâchent pas d'habitude), de la ferraille et son trophée.",
                                         "Container": {"Type": "Multiple", "Containers": [
                                             single(SHARD, 2), single("Ingredient_Bar_Iron", 2, 4),
                                             {"Type": "Droplist", "DroplistId": "Nakasar_Drop_Trophy_Armor_Core"}]}},
        "Nakasar_Drop_Spectre": {"$Comment": "Spectre : un éclat de rune, une relique du manoir et son trophée.",
                                 "Container": {"Type": "Multiple", "Containers": [
                                     single(SHARD, 1), single(RELIC, 1),
                                     {"Type": "Droplist", "DroplistId": "Nakasar_Drop_Trophy_Spectral_Shroud"}]}},
    }


def groups():
    return {
        CONSTRUCTS: {"$Comment": "L'armure enchantée et ses rouages : ils ne se blessent pas entre eux (DisableDamageGroups).",
                     "IncludeRoles": [ARMOR, GEAR]},
        FIRE_IMMUNE: {"$Comment": "Aucun dégât de feu (dev.nakasar.hytale.vampires.elite.FireAffinitySystem).",
                      "IncludeGroups": [CONSTRUCTS]},
        SHADES: {"$Comment": "Fantômes invoqués par le Spectre : il compte ceux qui restent (capteur Count) pour savoir quand en rappeler.",
                 "IncludeRoles": [SHADE]},
    }


def marker(role, comment):
    return {"$Comment": comment, "NPCs": [{"Name": role, "Weight": 1, "RealtimeRespawnTime": 1800}],
            "RealtimeRespawn": True, "ExclusionRadius": 0}


def spawner(role, where):
    return {
        "$Comment": f"Bloc invisible posé {where} : son composant SpawnMarkerBlock crée le marqueur d'apparition {role} à cet endroit.",
        "TranslationProperties": {"Name": f"nakasar_mobs.items.Nakasar_Spawner_{role.removeprefix('Nakasar_')}.name"},
        "Quality": "Developer",
        "MaxStack": 64,
        "BlockType": {"Material": "Empty", "DrawType": "Empty", "Opacity": "Transparent",
                      "BlockEntity": {"Components": {"SpawnMarkerBlock": {"Config": {"SpawnMarker": role}}}}},
    }


def frost_icon():
    """Icône d'effet : flocon de givre blanc-bleu sur un halo glacé (512², comme les icônes vanilla)."""
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    halo = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((40, 40, size - 40, size - 40), fill=(90, 170, 255, 150))
    img.alpha_composite(halo.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(img)
    c = size / 2
    for k in range(6):
        a = math.radians(60 * k + 90)
        ex, ey = c + math.cos(a) * 200, c - math.sin(a) * 200
        d.line((c, c, ex, ey), fill=(236, 250, 255, 255), width=34)
        for f in (0.55, 0.8):
            bx, by = c + math.cos(a) * 200 * f, c - math.sin(a) * 200 * f
            for s in (-1, 1):
                b = a + s * math.radians(45)
                d.line((bx, by, bx + math.cos(b) * 70, by - math.sin(b) * 70), fill=(200, 236, 255, 255), width=24)
    d.ellipse((c - 46, c - 46, c + 46, c + 46), fill=(150, 210, 255, 255), outline=(236, 250, 255, 255), width=12)
    return img


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    write_json(ROLES / f"{ARMOR}.json", armor_role())
    write_json(ROLES / f"{GEAR}.json", gear_role())
    write_json(ROLES / f"{SPECTRE}.json", spectre_role())
    write_json(ROLES / f"{SHADE}.json", shade_role())
    for name, doc in {
        "Nakasar_NPC_Armor_Swing_Left": armor_swing("Left"),
        "Nakasar_NPC_Armor_Swing_Right": armor_swing("Right"),
        "Nakasar_NPC_Armor_Slam": armor_slam(),
        "Nakasar_NPC_Armor_Summon": armor_summon(),
        "Nakasar_NPC_Spectre_Touch": spectre_touch(),
        "Nakasar_NPC_Spectre_ColdWave": spectre_cold_wave(),
        "Nakasar_NPC_Spectre_Summon": spectre_summon(),
    }.items():
        write_json(INTERACTIONS / f"{name}.json", doc)
    write_json(ROOTS / "Root_Nakasar_NPC_Armor_Attack.json", {
        "$Comment": "Coups de massue ordinaires de l'armure enchantée : gauche puis droite.",
        "Tags": {"Attack": ["Melee"]},
        "Interactions": [{"Type": "Chaining", "ChainId": "Nakasar_Enchanted_Armor", "ChainingAllowance": 15,
                          "Next": ["Nakasar_NPC_Armor_Swing_Left", "Nakasar_NPC_Armor_Swing_Right"]}]})
    for name in ("Armor_Slam", "Armor_Summon", "Spectre_Touch", "Spectre_ColdWave", "Spectre_Summon"):
        write_json(ROOTS / f"Root_Nakasar_NPC_{name}.json", melee_tag(f"Nakasar_NPC_{name}"))
    write_json(EFFECTS / f"{FROST}.json", frost_effect())
    for name, doc in drops().items():
        write_json(DROPS / f"{name}.json", doc)
    for name, doc in groups().items():
        write_json(GROUPS / f"{name}.json", doc)
    write_json(MARKERS / f"{ARMOR}.json", marker(ARMOR, "Armure enchantée (élite) au fond de la salle enterrée d'une crypte sur deux ; revient 30 minutes après sa mort."))
    write_json(MARKERS / f"{SPECTRE}.json", marker(SPECTRE, "Spectre (élite) d'un château hanté sur deux ou d'un cimetière hanté sur trois ; revient 30 minutes après sa mort."))
    write_json(SPAWNERS / f"Nakasar_Spawner_{ARMOR.removeprefix('Nakasar_')}.json", spawner(ARMOR, "dans la salle enterrée d'une crypte"))
    write_json(SPAWNERS / f"Nakasar_Spawner_{SPECTRE.removeprefix('Nakasar_')}.json", spawner(SPECTRE, "dans un château ou un cimetière hanté"))
    icon = frost_icon()
    (COMMON / "UI/StatusEffects/Nakasar").mkdir(parents=True, exist_ok=True)
    icon.save(COMMON / "UI/StatusEffects/Nakasar/Spectre_Frost.png")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        icon.resize((128, 128), Image.LANCZOS).save(preview / "Spectre_Frost.png")


if __name__ == "__main__":
    main()
