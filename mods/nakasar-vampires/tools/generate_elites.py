#!/usr/bin/env python3
"""Génère l'armure enchantée et le Spectre, deux élites du Comté, avec leurs serviteurs.

    python3 mods/nakasar-vampires/tools/generate_elites.py [--preview DOSSIER]

Armure enchantée (Nakasar_Enchanted_Armor), dans une crypte sur deux, au fond de la salle enterrée :
- grosse armure vide animée (modèle vanilla Shadow_Knight, Server/Models/Nakasar/Nakasar_Enchanted_Armor.json)
  armée d'une massue ; n'est pas une morte-vivante (le feu purificateur ne la gêne pas) et ne prend aucun dégât de
  feu (groupe Nakasar_Fire_Immune, FireAffinitySystem) ;
- coups de massue ; coups lourds (frappe écrasante, furie de trois coups) ; coup sismique annoncé (elle s'immobilise,
  rougeoie, une zone rouge de 4,5 blocs se charge au sol) ; brasier bleu annoncé (zone rouge de 6,5 blocs, feu et
  flammes bleues Nakasar_Blue_Flame) ;
- fait apparaître trois rouages enchantés (Nakasar_Enchanted_Gear, tools/generate_gear_model.py) qui la soignent
  petit à petit tant qu'ils vivent (SummonMinionsInteraction, HealSummonerPerSecond) ; on peut les détruire, elle
  en refait venir toutes les 18 à 22 s ;
- lâche deux éclats de rune et son trophée.

Spectre (Nakasar_Spectre), dans un château hanté sur deux et un cimetière hanté sur trois :
- grand fantôme (modèle vanilla Wraith) qui flotte bas, vif : il tourne autour de sa cible, plonge sur elle
  (téléportation et coup de griffes), rafale de griffes et toucher glacial ;
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

import elite_fx
import tower_warnings as tw

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
BLUE_FLAME = "Nakasar_Blue_Flame"
SHARD = "Ingredient_Rune_Shard"
RELIC = "Ingredient_Nakasar_Manor_Relic"
MACE = "Weapon_Mace_Onyxium"

ARMOR_SLAM_RADIUS = 4.5
INFERNO_RADIUS = 6.5
GEAR_ALCOVE = "Nakasar_Gear_Alcove"
COLD_WAVE_RADIUS = 6.0


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
    """Cercle rouge de la Tour autour de l'élite, plein au bout de `seconds` (détaché du modèle : il ne la suit pas).
    Pour les cercles centrés sur l'élite, le coup reste celui du sélecteur AOECircle de même rayon."""
    return {"SystemId": tw.system(seconds), "TargetEntityPart": "Entity", "TargetNodeName": "Origin",
            "Scale": tw.scale(radius), "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0}, "DetachedFromModel": True}


def telegraph(shape, seconds, comment=None, **keys):
    """Attaque annoncée calculée en Java (Nakasar_Telegraph) : zone rouge de la taille exacte du coup, puis le coup
    sur ce qui s'y trouve encore. Instantanée : la chaîne continue aussitôt (pose de même durée)."""
    doc = {"Type": "Nakasar_Telegraph", "Shape": shape, "Seconds": seconds, **keys}
    return {"$Comment": comment, **doc} if comment else doc


def half_health():
    """Capteur : l'élite est sous la moitié de sa vie (seconde phase)."""
    return {"Type": "Self", "Filters": [{"Type": "Stat", "Stat": "Health", "StatTarget": "Value", "RelativeTo": "Health",
                                         "RelativeToTarget": "Max", "ValueRange": [0, 0.5]}]}


def windup(seconds, effects):
    return {"Type": "Simple", "RunTime": seconds, "Effects": effects}


def ground_particles(system, scale):
    return {"SystemId": system, "TargetEntityPart": "Entity", "TargetNodeName": "Origin", "Scale": scale,
            "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0}, "DetachedFromModel": True}


def hand_flame(node="R-Hand", scale=2.0):
    """Flammes bleues sur une main pendant qu'un coup lourd se prépare."""
    return {"SystemId": "Fire_Blue", "TargetNodeName": node, "Scale": scale, "PositionOffset": {"Y": 0.3},
            "RotationOffset": {"Pitch": 180}}


def burn(seconds):
    """Flammes bleues sur la cible touchée (ennemis seulement)."""
    return {"Type": "Nakasar_ApplyEffectToFoes", "EffectId": BLUE_FLAME, "Duration": seconds}


def melee_tag(*names, comment=None):
    doc = {"Tags": {"Attack": ["Melee"]}, "Interactions": list(names)}
    return {"$Comment": comment, **doc} if comment else doc


def damage(amount, extra=None, sound=None, particles=None, knockback=None, interrupt=False, kind="Physical"):
    effects = {}
    if sound:
        effects["WorldSoundEventId"] = sound
    if particles:
        effects["WorldParticles"] = [{"SystemId": particles}]
    if knockback:
        effects["Knockback"] = {"Type": "Force", "Force": knockback, "VelocityType": "Set", "Direction": {"Y": 1}}
    doc = {"Parent": "DamageEntityParent_Hit_Interrupt" if interrupt else "DamageEntityParent",
           "DamageCalculator": {"BaseDamage": {kind: amount}, "RandomPercentageModifier": 0.1}}
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
        "$Comment": f"Coup sismique annoncé de l'armure enchantée : elle s'immobilise 1,4 s, rougeoie et lève sa massue pendant qu'une zone rouge de {ARMOR_SLAM_RADIUS} blocs se charge au sol, puis frappe le sol (40 dégâts, projection, flammes bleues 3 s). On l'évite en sortant de la zone.",
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
                "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.0), ground_particles("Fire_Blue", 2.5)]},
             "Selector": {"Id": "AOECircle", "Range": ARMOR_SLAM_RADIUS},
             "HitEntity": {"Interactions": damage(40, sound="SFX_Mace_T2_Signature_Impact", knockback=9,
                                                  extra=[burn(3)])}},
            {"Type": "Simple", "RunTime": 0.7},
        ],
    }


def heavy_hit(amount, end, length, knockback, burn_seconds=None, sound="SFX_Mace_T2_Signature_Impact"):
    """Coup lourd devant l'armure : balayage horizontal large."""
    return {"Selector": {"Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": True, "ExtendTop": 1.0,
                         "ExtendBottom": 1.0, "StartDistance": 0.3, "EndDistance": end, "Length": length,
                         "RollOffset": 0, "YawStartOffset": length // 2},
            "HitEntity": {"Interactions": damage(amount, sound=sound, particles="Impact_Sword_Basic_Stronk",
                                                 knockback=knockback, interrupt=True,
                                                 extra=[burn(burn_seconds)] if burn_seconds else None)}}


def armor_crush():
    return {
        "$Comment": "Frappe écrasante de l'armure enchantée (coup lourd annoncé) : elle s'immobilise et lève sa massue 1,4 s, la main en flammes bleues, pendant qu'un cône rouge de 120° et 4,6 blocs se charge devant elle ; puis elle l'abat (55 dégâts, projection, flammes bleues 3 s). On l'évite en reculant ou en passant derrière elle.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            telegraph("Cone", 1.4, Angle=120, Radius=4.6, Damage=55, Knockback=8, KnockUp=5, EffectId=BLUE_FLAME,
                      EffectDuration=3, HitParticle="Impact_Sword_Basic_Stronk", ImpactSound="SFX_Mace_T2_Signature_Impact"),
            windup(1.4, {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharging",
                         "WorldSoundEventId": "SFX_Spear_Throw_Charge", "Particles": [hand_flame()]}),
            windup(0.15, {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharged",
                          "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam"}),
            {"Type": "Simple", "RunTime": 0.6},
        ],
    }


def armor_fury():
    swings = []
    for side, direction, yaw in (("Left", "ToLeft", 60), ("Right", "ToRight", -60)):
        swings += [
            {"Type": "Simple", "RunTime": 0.3, "Effects": {
                "ItemPlayerAnimationsId": "Mace", "ItemAnimationId": f"Swing{side}",
                "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"}},
            {"Type": "Selector", "RunTime": 0.15,
             "Selector": {"Id": "Horizontal", "Direction": direction, "TestLineOfSight": True, "ExtendTop": 0.8,
                          "ExtendBottom": 0.8, "StartDistance": 0.3, "EndDistance": 4.0, "Length": 120,
                          "RollOffset": 15, "YawStartOffset": yaw},
             "HitEntity": {"Interactions": damage(32, sound="SFX_T1_Impact_Blunt", particles="Impact_Sword_Basic_Stronk",
                                                  interrupt=True)}},
        ]
    return {
        "$Comment": "Furie de l'armure enchantée : deux grands revers de massue toujours dans le même ordre, sans annonce au sol (32 dégâts chacun, 4 blocs, 120°), puis elle lève la massue en flammes pendant qu'un cône rouge de 90° et 4,2 blocs se charge 1 s devant elle, et l'abat (45 dégâts, projection, flammes bleues 3 s). Reculez dès le premier revers.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            *swings,
            telegraph("Cone", 1.0, Angle=90, Radius=4.2, Damage=45, Knockback=7, KnockUp=5, EffectId=BLUE_FLAME,
                      EffectDuration=3, HitParticle="Impact_Sword_Basic_Stronk", ImpactSound="SFX_Mace_T2_Signature_Impact"),
            windup(1.0, {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharging",
                         "WorldSoundEventId": "SFX_Spear_Throw_Charge", "Particles": [hand_flame()]}),
            windup(0.15, {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharged",
                          "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam"}),
            {"Type": "Simple", "RunTime": 0.7},
        ],
    }


def inferno_strike(**keys):
    return telegraph("Circle", 2.0, Radius=INFERNO_RADIUS, Damage=20, DamageCause="Fire", Knockback=6, KnockUp=6,
                     EffectId=BLUE_FLAME, EffectDuration=5, Cover=True, HitParticle="Impact_Sword_Basic_Stronk",
                     ImpactParticle="Fire_Blue", ImpactParticleScale=5.0, ImpactSound="SFX_Goblin_Feastmaster_Slam", **keys)


INFERNO_POSE = {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "Guard", "WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                "Particles": [hand_flame("R-Hand", 2.5), hand_flame("L-Hand", 2.5),
                              {"SystemId": "Fire_Blue", "TargetNodeName": "Belly", "Scale": 3.0}]}
INFERNO_BLAST = {"ItemPlayerAnimationsId": "Mace", "ItemAnimationId": "SwingDownCharged",
                 "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.4)]}


def armor_inferno():
    return {
        "$Comment": f"Brasier bleu de l'armure enchantée, annoncé : elle se fige 2 s, les flammes bleues de son corps grandissent et un cercle rouge de {INFERNO_RADIUS:g} blocs se charge au sol ; puis le brasier jaillit autour d'elle (20 dégâts de feu, projection, flammes bleues {BLUE_FLAME} : 5 dégâts de feu par seconde pendant 5 s). Un pilier ou un sarcophage entre elle et un joueur le protège (Nakasar_Telegraph, Cover). On l'évite en sortant du cercle ou en se cachant.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "ApplyEffect", "EffectId": "Dungeon_Goblin_Mace_Slam_Charge"},
            inferno_strike(),
            windup(2.0, INFERNO_POSE),
            windup(0.15, INFERNO_BLAST),
            {"Type": "Simple", "RunTime": 0.8},
        ],
    }


def armor_inferno_double():
    return {
        "$Comment": f"Seconde moitié de l'armure enchantée (sous 50 % de vie) : deux brasiers bleus d'affilée. Le premier comme d'habitude, cercle rouge de {INFERNO_RADIUS:g} blocs autour d'elle pendant 2 s ; le second se dessine 1,6 s après, décalé de 7 blocs vers le joueur le plus éloigné, et éclate 2 s plus tard. Les piliers et les sarcophages protègent des deux.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "ApplyEffect", "EffectId": "Dungeon_Goblin_Mace_Slam_Charge"},
            inferno_strike(),
            inferno_strike(Anchor="Farthest", OffsetMax=7, Delay=1.6),
            windup(2.0, INFERNO_POSE),
            windup(0.15, INFERNO_BLAST),
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            windup(1.45, INFERNO_POSE),
            windup(0.15, INFERNO_BLAST),
            {"Type": "Simple", "RunTime": 0.8},
        ],
    }


def armor_summon():
    return {
        "$Comment": "L'armure enchantée appelle ses rouages : elle lève sa massue, des runes bleues s'allument au sol et jusqu'à trois rouages enchantés (Nakasar_Enchanted_Gear) sortent des alcôves de la crypte (blocs Nakasar_Gear_Alcove ; à défaut, entre 2,5 et 5 blocs d'elle). Un lien bleu va de chaque rouage à l'armure : chaque rouage vivant lui rend 5 PV par seconde (Nakasar_SummonMinions, HealSummonerPerSecond), il faut les détruire.",
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
                      "MinDistance": 2.5, "MaxDistance": 5, "MinSpacing": 2, "HealSummonerPerSecond": 5,
                      "SpawnBlock": GEAR_ALCOVE, "TetherParticle": "Nakasar_Tether_Gear"}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def armor_role():
    return {
        "$Comment": "Armure enchantée (élite) d'une crypte sur deux, au fond de la salle enterrée, avec barre de vie de boss (BossBarSystem). Grosse armure vide animée par des flammes bleues, armée d'une massue : ce n'est pas une morte-vivante (le feu purificateur ne la gêne pas) et le feu ne lui fait rien (groupe Nakasar_Fire_Immune). Coups de massue sans annonce ; frappe écrasante annoncée par un cône rouge de 120° (1,4 s, 55 dégâts) ; furie (deux revers, puis un coup abattu annoncé par un cône de 90°) ; coup sismique annoncé par un cercle rouge de 4,5 blocs ; brasier bleu annoncé par un cercle rouge de 6,5 blocs (2 s, feu, flammes bleues 5 s) dont les piliers et les sarcophages protègent ; sous 50 % de vie, deux brasiers d'affilée, le second vers le joueur le plus éloigné. Toutes les 18 à 22 s elle complète ses trois rouages enchantés, qui sortent des alcôves et la soignent de 5 PV par seconde chacun tant qu'ils vivent (lien bleu). Immobile comme une statue tant que rien ne passe ; retourne à sa place et regagne sa vie si on fuit à plus de 24 blocs. Générée par tools/generate_elites.py.",
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
            "Actions": [timer("Summon", (2, 3), (18, 22)), timer("Slam", (6, 8), (11, 14)),
                        timer("Crush", (3, 4), (7, 9)), timer("Fury", (9, 11), (12, 15)),
                        timer("Inferno", (12, 14), (16, 20))],
        }],
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"},
             "Instructions": to_combat_on_sight(14) + [{"Actions": []}]},
            {"Sensor": {"Type": "State", "State": "Combat"}, "Instructions": [
                {"$Comment": "Cible perdue ou partie trop loin : elle retourne à sa place.",
                 **lost_target(24, [{"Type": "State", "State": "ReturnHome"}])},
                timed_attack("Summon", "Root_Nakasar_NPC_Armor_Summon",
                             comment="Rouages enchantés : elle complète la vague (trois au plus) dès l'entrée en combat, puis toutes les 18 à 22 s."),
                {"$Comment": "Seconde moitié (sous 50 % de vie) : le brasier bleu devient double, le second décalé vers le joueur le plus éloigné.",
                 "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": 10}, half_health(),
                                                       {"Type": "Timer", "Name": "Inferno", "State": "STOPPED"}]},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.0},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "TimerRestart", "Name": "Inferno"},
                             {"Type": "Attack", "Attack": "Root_Nakasar_NPC_Armor_Inferno_Double", "SkipAiming": True,
                              "LineOfSight": False, "AvoidFriendlyFire": False}]},
                timed_attack("Inferno", "Root_Nakasar_NPC_Armor_Inferno", rng=8, los=True,
                             comment="Brasier bleu annoncé quand la cible est à moins de 8 blocs."),
                timed_attack("Slam", "Root_Nakasar_NPC_Armor_Slam", rng=4.5, los=True,
                             comment="Coup sismique annoncé quand la cible est à moins de 4,5 blocs."),
                timed_attack("Fury", "Root_Nakasar_NPC_Armor_Fury", rng=3.8, los=True,
                             comment="Furie (coups lourds enchaînés) quand la cible est au contact."),
                timed_attack("Crush", "Root_Nakasar_NPC_Armor_Crush", rng=4.2, los=True,
                             comment="Frappe écrasante (coup lourd) quand la cible est à moins de 4,2 blocs."),
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


SAFE = 5.0   # arena.Braziers.SAFE_RADIUS
CHILL = {"EffectId": "Nakasar_Ghost_Chill", "EffectDuration": 3}


def spectre_swoop():
    return {
        "$Comment": f"Piqué du Spectre, annoncé : il se dissout en brume pendant qu'un petit cercle rouge de 1,5 bloc se remplit 1,2 s sous sa cible (à l'endroit où elle était), puis il surgit au centre du cercle et frappe de ses griffes glacées (22 dégâts, recul, frisson Nakasar_Ghost_Chill 3 s). Il suffit de sortir du cercle. Impossible à moins de {SAFE:g} blocs d'un brasero allumé (SafeFromBraziers) : la chaîne échoue.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            telegraph("Circle", 1.2, Anchor="Target", Radius=1.5, TeleportCaster=True, SafeFromBraziers=SAFE, Damage=22,
                      Knockback=4, KnockUp=4, HitParticle="Impact_Ice", ImpactSound="SFX_Light_Melee_T2_Swing", **CHILL),
            windup(1.2, {"WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                         "Particles": [{"SystemId": "Weapon_Frost_Mist", "TargetNodeName": "Chest", "Scale": 2.5},
                                       {"SystemId": "Nakasar_Mist_Column", "TargetEntityPart": "Entity",
                                        "TargetNodeName": "Origin", "Scale": 1.0}]}),
            windup(0.3, {"ItemAnimationId": "SwingDown"}),
            {"Type": "Simple", "RunTime": 0.3},
        ],
    }


def spectre_blink():
    return {
        "$Comment": f"Clignement du Spectre quand sa cible s'éloigne : une colonne de brume marque 0,6 s avant le point où il va surgir (à 2-3,5 blocs d'elle), puis il y apparaît. Impossible à moins de {SAFE:g} blocs d'un brasero allumé.",
        "Type": "Serial",
        "Interactions": [
            telegraph("Column", 0.6, Anchor="Target", OffsetMin=2, OffsetMax=3.5, TeleportCaster=True,
                      SafeFromBraziers=SAFE, MarkParticle="Nakasar_Mist_Column", MarkInterval=0.2, MarkHeight=0),
            windup(0.6, {"Particles": [{"SystemId": "Weapon_Frost_Mist", "TargetNodeName": "Chest", "Scale": 2.0}]}),
            {"Type": "Simple", "RunTime": 0.2},
        ],
    }


def spectre_flurry():
    hits = []
    for k in range(3):
        hits.append({"Type": "Simple", "RunTime": 0.3, "Effects": {"ItemAnimationId": "SwingDown",
                                                                     "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"}})
    return {
        "$Comment": "Rafale de griffes du Spectre, annoncée : un cône rouge de 90° et 3 blocs se charge 0,8 s devant lui, puis trois coups rapides tombent dedans (10 dégâts chacun, à 0,8, 1,1 et 1,4 s) ; le dernier glace aussi (Nakasar_Ghost_Chill). Restez hors du cône jusqu'au troisième coup.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            telegraph("Cone", 0.8, Angle=90, Radius=3, Damage=10, HitParticle="Impact_Ice"),
            telegraph("Cone", 0.6, Angle=90, Radius=3, Delay=0.5, Damage=10, HitParticle="Impact_Ice"),
            telegraph("Cone", 0.6, Angle=90, Radius=3, Delay=0.8, Damage=10, HitParticle="Impact_Ice", **CHILL),
            windup(0.8, {"WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                         "Particles": [{"SystemId": "Weapon_Frost_Mist", "TargetNodeName": "Chest", "Scale": 1.5}]}),
            *hits,
            {"Type": "Simple", "RunTime": 0.2},
        ],
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


def spectre_gust():
    return {
        "$Comment": f"Seconde moitié du Spectre (sous 50 % de vie) : bourrasque glacée annoncée sur le brasero allumé le plus proche. Un cercle rouge de 3 blocs se charge 1,5 s autour du brasero, puis le vent l'éteint ; ceux qui sont restés dedans prennent 10 dégâts et le gel {FROST} 4 s. Sans brasero allumé, la chaîne échoue.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            telegraph("Circle", 1.5, Anchor="Brazier", Radius=3, Snuff=True, Damage=10, EffectId=FROST, EffectDuration=4,
                      HitParticle="Impact_Ice", ImpactParticle="Ice_Blast", ImpactParticleScale=1.2,
                      ImpactSound="SFX_Goblin_Feastmaster_Slam"),
            windup(1.5, {"ItemAnimationId": "SwingDown", "WorldSoundEventId": "SFX_Spirit_Root_Alerted",
                         "Particles": [{"SystemId": "Ice_Staff_Charging", "TargetNodeName": "Chest", "Scale": 1.5}]}),
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def spectre_summon():
    return {
        "$Comment": "Le Spectre appelle ses fantômes : il se fige dans une brume de givre, puis trois fantômes (Nakasar_Spectral_Ghost) apparaissent entre 2,5 et 5 blocs de lui (Nakasar_SummonMinions). Un lien pâle va de chaque fantôme au Spectre : tant qu'il en reste un, il est invulnérable (MinionShieldSystem, halo doré).",
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
                      "MinDistance": 2.5, "MaxDistance": 5, "MinSpacing": 2, "TetherParticle": "Nakasar_Tether_Ghost"}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def hover(speed, min_h, max_h):
    """Marche en lévitation, comme les spectres du Vide et les esprits vanilla (Template_Void_Spectre, Template_Spirit) :
    les mouvements qui gardent une distance (MaintainDistance) exigent un contrôleur Walk, refusé sinon au chargement
    du rôle (« Missing required motion controller: MotionControllerWalk »)."""
    return [{"Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "RunThreshold": 0.3, "MaxFallSpeed": 6,
             "MaxRotationSpeed": 360, "Acceleration": 10, "MinHover": min_h, "MinHoverDrop": 0, "FloatsDown": True,
             "MaxHover": max_h, "HoverFreq": 0.5}]


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
        "$Comment": "Spectre (élite) d'un château hanté sur deux et d'un cimetière sur sept environ (Cemeteries/Spectre, poids 0,5), avec barre de vie de boss (BossBarSystem). Grand fantôme qui flotte bas. Dès le combat (ou dès le premier coup reçu), il invoque trois fantômes et reste invulnérable tant qu'il en reste (MinionShieldSystem, barre de boss en mode invulnérable) ; une fois la vague détruite, il est vulnérable 14 à 16 s, puis en appelle une autre. Vif et mobile : il tourne autour de sa cible ; toutes les 5 à 7 s, piqué annoncé (petit cercle rouge sous la cible pendant 1,2 s, puis il y surgit et frappe) ; rafale de griffes annoncée par un cône rouge, toucher glacial ; vague de froid annoncée par un cercle rouge de 6 blocs qui ralentit fortement ceux qui y restent. Quand sa cible s'éloigne, une colonne de brume marque 0,6 s avant le point où il surgit. Près d'un brasero allumé (5 blocs), ni piqué ni clignement ; sous 50 % de vie, une bourrasque glacée annoncée éteint un brasero. Si on le fuit, il se calme et regagne sa vie. Mort-vivant (feu purificateur). Généré par tools/generate_elites.py.",
        "Type": "Generic",
        "Appearance": SPECTRE,
        "NameTranslationKey": "nakasar_mobs.npc.Spectre.name",
        "MaxHealth": 900,
        "DropList": "Nakasar_Drop_Spectre",
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": ["Nakasar_Ghosts"],
        "KnockbackScale": 0.2,
        "DeathAnimationTime": 1.5,
        "MotionControllerList": hover(7, 0.6, 1.2),
        "StateTransitions": [{
            "$Comment": "Entrée en combat : chaque attaque spéciale a sa propre recharge ; les fantômes viennent tout de suite.",
            "States": [{"From": ["Idle"], "To": ["Combat"]}],
            "Actions": [timer("Summon", (0.1, 0.2), (14, 16)), timer("ColdWave", (5, 7), (13, 16)),
                        timer("Blink", (4, 6), (8, 11)), timer("Swoop", (2, 3), (5, 7)),
                        timer("Flurry", (4, 5), (6, 8)), timer("Gust", (3, 5), (14, 18))],
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
                {"$Comment": "Seconde moitié (sous 50 % de vie) : bourrasque glacée annoncée qui éteint le brasero allumé le plus proche.",
                 "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": 24}, half_health(),
                                                       {"Type": "Timer", "Name": "Gust", "State": "STOPPED"}]},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "TimerRestart", "Name": "Gust"},
                             {"Type": "Attack", "Attack": "Root_Nakasar_NPC_Spectre_Gust", "SkipAiming": True,
                              "LineOfSight": False, "AvoidFriendlyFire": False}]},
                timed_attack("Swoop", "Root_Nakasar_NPC_Spectre_Swoop", rng=14,
                             comment="Piqué annoncé : petit cercle rouge sous sa cible (à moins de 14 blocs), puis il y surgit et frappe. Pas près d'un brasero allumé."),
                {"$Comment": "Clignement quand la cible s'éloigne (7 à 22 blocs) : une colonne de brume marque le point d'arrivée 0,6 s avant. Pas près d'un brasero allumé.",
                 "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": 22},
                                                       {"Type": "Not", "Sensor": {"Type": "Target", "Range": 7}},
                                                       {"Type": "Timer", "Name": "Blink", "State": "STOPPED"}]},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "TimerRestart", "Name": "Blink"},
                             {"Type": "Attack", "Attack": "Root_Nakasar_NPC_Spectre_Blink", "SkipAiming": True,
                              "LineOfSight": False, "AvoidFriendlyFire": False}]},
                timed_attack("Flurry", "Root_Nakasar_NPC_Spectre_Flurry", rng=3.0,
                             comment="Rafale de griffes au contact."),
                {"Sensor": {"Type": "Target", "Range": 3.0},
                 "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 1.5},
                 "ActionsBlocking": True,
                 "Actions": [{"Type": "Attack", "Attack": "Root_Nakasar_NPC_Spectre_Touch", "AttackPauseRange": [0.5, 0.9]},
                             {"Type": "Timeout", "Delay": [0.2, 0.2]}]},
                {"$Comment": "Entre deux coups, il tourne autour de sa cible au lieu de rester planté devant elle.",
                 "Sensor": {"Type": "Target", "Range": 6},
                 "BodyMotion": {"Type": "MaintainDistance", "DesiredDistanceRange": [2.0, 3.5], "MoveThreshold": 0.5,
                                "RelativeForwardsSpeed": 1.0, "RelativeBackwardsSpeed": 0.8,
                                "StrafingDurationRange": [0.8, 1.6], "StrafingFrequencyRange": [1.0, 2.0]},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5}},
                {"Sensor": {"Type": "Target", "Range": 28},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 1.0, "SlowDownDistance": 2, "StopDistance": 1.6,
                                "UsePathfinder": False},
                 "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5}},
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


def blue_flame_effect():
    return {
        "$Comment": "Flammes bleues de l'armure enchantée : 5 dégâts de feu par seconde pendant 5 s, teinte bleue.",
        "Name": "nakasar_mobs.effects.Nakasar_Blue_Flame",
        "Duration": 5,
        "OverlapBehavior": "Overwrite",
        "Debuff": True,
        "DamageCalculatorCooldown": 1,
        "DamageCalculator": {"BaseDamage": {"Fire": 5}},
        "ApplicationEffects": {"EntityTopTint": "#9fd0ff", "EntityBottomTint": "#1d3cff", "EntityAnimationId": "Hurt",
                               "Particles": [{"SystemId": "Fire_Blue", "Scale": 0.8}]},
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
                      "IncludeGroups": [CONSTRUCTS, "Nakasar_Fire_Elementals"]},
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
        "Nakasar_NPC_Armor_Crush": armor_crush(),
        "Nakasar_NPC_Armor_Fury": armor_fury(),
        "Nakasar_NPC_Armor_Inferno": armor_inferno(),
        "Nakasar_NPC_Armor_Inferno_Double": armor_inferno_double(),
        "Nakasar_NPC_Spectre_Blink": spectre_blink(),
        "Nakasar_NPC_Spectre_Gust": spectre_gust(),
        "Nakasar_NPC_Armor_Summon": armor_summon(),
        "Nakasar_NPC_Spectre_Touch": spectre_touch(),
        "Nakasar_NPC_Spectre_Swoop": spectre_swoop(),
        "Nakasar_NPC_Spectre_Flurry": spectre_flurry(),
        "Nakasar_NPC_Spectre_ColdWave": spectre_cold_wave(),
        "Nakasar_NPC_Spectre_Summon": spectre_summon(),
    }.items():
        write_json(INTERACTIONS / f"{name}.json", doc)
    write_json(ROOTS / "Root_Nakasar_NPC_Armor_Attack.json", {
        "$Comment": "Coups de massue ordinaires de l'armure enchantée : gauche puis droite.",
        "Tags": {"Attack": ["Melee"]},
        "Interactions": [{"Type": "Chaining", "ChainId": "Nakasar_Enchanted_Armor", "ChainingAllowance": 15,
                          "Next": ["Nakasar_NPC_Armor_Swing_Left", "Nakasar_NPC_Armor_Swing_Right"]}]})
    for name in ("Armor_Slam", "Armor_Crush", "Armor_Fury", "Armor_Inferno", "Armor_Inferno_Double", "Armor_Summon",
                 "Spectre_Touch", "Spectre_Swoop", "Spectre_Flurry", "Spectre_ColdWave", "Spectre_Summon",
                 "Spectre_Blink", "Spectre_Gust"):
        write_json(ROOTS / f"Root_Nakasar_NPC_{name}.json", melee_tag(f"Nakasar_NPC_{name}"))
    write_json(EFFECTS / f"{FROST}.json", frost_effect())
    write_json(EFFECTS / f"{BLUE_FLAME}.json", blue_flame_effect())
    for name, doc in drops().items():
        write_json(DROPS / f"{name}.json", doc)
    for name, doc in groups().items():
        write_json(GROUPS / f"{name}.json", doc)
    write_json(MARKERS / f"{ARMOR}.json", marker(ARMOR, "Armure enchantée (élite) au fond de la salle enterrée d'une crypte sur deux ; revient 30 minutes après sa mort."))
    write_json(MARKERS / f"{SPECTRE}.json", marker(SPECTRE, "Spectre (élite) d'un château hanté sur deux ou d'un cimetière hanté sur trois ; revient 30 minutes après sa mort."))
    write_json(SPAWNERS / f"Nakasar_Spawner_{ARMOR.removeprefix('Nakasar_')}.json", spawner(ARMOR, "dans la salle enterrée d'une crypte"))
    write_json(SPAWNERS / f"Nakasar_Spawner_{SPECTRE.removeprefix('Nakasar_')}.json", spawner(SPECTRE, "dans un château ou un cimetière hanté"))
    write_json(SPAWNERS / f"{GEAR_ALCOVE}.json", {
        "$Comment": "Bloc invisible et traversable posé dans une alcôve de la crypte : les rouages de l'armure enchantée en sortent (Nakasar_SummonMinions, SpawnBlock).",
        "TranslationProperties": {"Name": f"nakasar_mobs.items.{GEAR_ALCOVE}.name"},
        "Quality": "Developer",
        "MaxStack": 64,
        "BlockType": {"Material": "Empty", "DrawType": "Empty", "Opacity": "Transparent"},
    })
    # Zones d'annonce (cercles et cônes de la Tour, communs avec le Java des élites) et effets de lecture.
    tw.write()
    elite_fx.write()
    icon = frost_icon()
    (COMMON / "UI/StatusEffects/Nakasar").mkdir(parents=True, exist_ok=True)
    icon.save(COMMON / "UI/StatusEffects/Nakasar/Spectre_Frost.png")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        icon.resize((128, 128), Image.LANCZOS).save(preview / "Spectre_Frost.png")


if __name__ == "__main__":
    main()
