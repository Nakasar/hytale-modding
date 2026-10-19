#!/usr/bin/env python3
"""Génère les mobs de la Tour de l'Alchimiste (étape 3 du donjon), leurs attaques, leurs butins et les trois réactifs.

    python3 mods/nakasar-vampires/tools/generate_tower_mobs.py [--preview DOSSIER] [--vanilla-textures ASSETS.zip|Potion_Onion_Poison.png]
        [--firesteel-texture Golem_Firesteel/Models/Texture.png] [--frost-texture Spirit_Frost/Models/Model_Texture.png]

Ce sont des créatures que l'Alchimiste a fabriquées ou distillées ; elles ne se blessent pas entre elles (groupe
Nakasar_Alchemist_Creations). Toutes sont des rôles Generic du mod, sur des modèles vanilla :

- homoncule (Zombie_Aberrant_Small, plus petit) : rapide, fragile, en groupe, morsure ;
- golem de plomb (Golem_Firesteel sans flammes) : lent et solide, coups de poing, frappe au sol annoncée par une zone
  rouge de 4 blocs ;
- fioles vivantes, de poison et de feu (la fiole lancée vanilla Potion_Onion, en grand) : elles roulent vers le joueur,
  s'arrêtent, grésillent 1,2 s au-dessus d'une zone rouge de 3 blocs puis éclatent (poison ou brûlure) ; tuées avant,
  elles lâchent leur sel ;
- apprenti (humanoïde en robe de mage verte) : garde ses distances et lance des fioles ;
- plantes carnivores de la serre : la vrille indépendante (modèle de la vrille de la citrouille géante, mêmes attaques)
  et le Snapdragon vanilla, enraciné, à morsure empoisonnée ;
- élémentaires (esprits vanilla, en vol) : feu (boules de feu), glace (traits de glace), foudre (décharge annoncée autour
  de lui, étourdit), racine (épines) et eau (orbes d'eau, esprit de givre teinté de bleu, sur l'île des sources) ;
- gardien d'airain (Golem_Firesteel retexturé en laiton à lueur cyan, plus grand) : gardien mécanique de la cour de la
  tour, très solide ; il en faut abattre tous les gardiens pour ouvrir la porte du hall (tower/CourtGuardSystem.java) ;
- golem de cristal instable (élite de la Salle des Transmutations, Golem_Crystal_Thunder en grand, barre de boss) :
  combo vanilla du golem de cristal et onde de foudre annoncée par une zone rouge de 6 blocs ;
- gargouille (chauve-souris vanilla taillée dans la pierre, en grand) : vole autour de l'Escalier des vents, plonge sur
  sa cible et la griffe. Pas de recul : elle ne doit jamais pousser personne dans le vide ;
- Codex vivant (boss de la bibliothèque, modèle tools/generate_codex_models.py, barre de boss) : flotte au centre de la
  rotonde, lance des nuées de pages tranchantes dans un cône annoncé au sol et ouvre un chapitre toutes les 28 à 32 s
  (interaction Java Nakasar_CodexChapter, combat suivi par tower/CodexSystem.java) : un livre de chapitre (rôles
  Nakasar_Codex_Chapter_<sort>, sans marqueur) apparaît sur un pupitre ; le détruire avant la fin de l'incantation
  étourdit le Codex (Nakasar_Codex_Stunned, dégâts subis +50 %), sinon le sort part (volumes de l'instance) ;
  CodexSystem mène aussi ses trois phases (jets d'encre, tourbillons de pages Nakasar_Codex_Page_Vortex, deux
  chapitres à la fois en dernière phase) ;
- Chimère du laboratoire (mini-boss, barre de boss) : un dragon qui ne vole pas (modèle du dragon de feu vanilla,
  attaques de tools/generate_dragon_models.py) : morsure, cabré qui retombe annoncé, fauchage de la queue annoncé ; les
  zombies porteurs d'acide (Nakasar_Chimera_Feeder) qui la soignent, posés en jeu sans marqueur, sont menés par
  tower/ChimeraSystem.java.

Réactifs (les trois principes) : Sel philosophal (golems, fioles, gargouilles), Soufre ardent (élémentaires de feu et
de foudre), Mercure vif (homoncules, apprentis) ; les élémentaires lâchent aussi les essences vanilla de leur élément.
Pas d'éclats de rune sur ces mobs (Kevin).

Les blocs d'apparition (Nakasar_Spawner_<mob>) sont posés dans la tour par alchemist_tower.Tower.mobs().
Les textures dérivées de textures vanilla (fiole de feu, gardien d'airain) ne sont recalculées qu'avec --vanilla-textures ; sinon le
fichier déjà présent dans le pack est gardé.
"""
import colorsys
import io
import json
import random
import sys
import zipfile
from pathlib import Path

from PIL import Image

import generate_altar as ga
import generate_elites as ge
import generate_occult as go
import tower_warnings as tw

PACK = ge.PACK
SERVER = ge.SERVER
COMMON = ge.COMMON
ROLES = ge.ROLES
GROUPS = ge.GROUPS
MARKERS = ge.MARKERS
SPAWNERS = ge.SPAWNERS
ROOTS = ge.ROOTS
DROPS = SERVER / "Drops/Nakasar/Alchemist"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/NPC/Alchemist"
PROJECTILES = SERVER / "Projectiles/Nakasar"
MODELS = SERVER / "Models/Nakasar/Alchemist"
ITEMS = SERVER / "Item/Items/Alchemist/Nakasar"
NPC_TEXTURES = COMMON / "NPC/Nakasar/Alchemist"
ITEM_MODELS = COMMON / "Items/Nakasar/Alchemist"
ICONS = COMMON / "Icons/Items/Nakasar/Alchemist"

LANG = "nakasar_alchemist"
CREATIONS = "Nakasar_Alchemist_Creations"
FIRE_ELEMENTALS = "Nakasar_Fire_Elementals"

HOMUNCULUS = "Nakasar_Homunculus"
GOLEM = "Nakasar_Lead_Golem"
FLASK_POISON = "Nakasar_Living_Flask_Poison"
FLASK_FIRE = "Nakasar_Living_Flask_Fire"
APPRENTICE = "Nakasar_Alchemist_Apprentice"
VINE = "Nakasar_Carnivorous_Vine"
SNAPDRAGON = "Nakasar_Snapdragon"
FIRE = "Nakasar_Elemental_Fire"
FROST = "Nakasar_Elemental_Frost"
THUNDER = "Nakasar_Elemental_Thunder"
ROOT = "Nakasar_Elemental_Root"
WATER = "Nakasar_Elemental_Water"
CRYSTAL_GOLEM = "Nakasar_Crystal_Golem"
BRASS_GUARDIAN = "Nakasar_Brass_Guardian"
GARGOYLE = "Nakasar_Tower_Gargoyle"
CODEX = "Nakasar_Living_Codex"
CHIMERA = "Nakasar_Lab_Chimera"
ALCHEMIST = "Nakasar_Alchemist"
ALL = [HOMUNCULUS, GOLEM, BRASS_GUARDIAN, FLASK_POISON, FLASK_FIRE, APPRENTICE, VINE, SNAPDRAGON, FIRE, FROST, THUNDER, ROOT, WATER,
       CRYSTAL_GOLEM, GARGOYLE, CODEX, CHIMERA, ALCHEMIST]
# Combat de l'Alchimiste (AlchemistSystem, Java) : homoncules du Grand Œuvre et piliers de la Convergence, jamais posés
# par un marqueur ; état d'épuisement et aspects élémentaires (teinte et particules de l'élément du moment).
ATHANOR_HOMUNCULUS = "Nakasar_Athanor_Homunculus"
ELEMENTS = ("Fire", "Frost", "Thunder", "Root")
PILLARS = [f"Nakasar_Alchemist_Pillar_{element}" for element in ELEMENTS]
ALCHEMIST_EXHAUSTED = "Nakasar_Alchemist_Exhausted"
ASPECTS = {element: f"Nakasar_Alchemist_Aspect_{element}" for element in ELEMENTS}
MASK_DROP = "Nakasar_Drop_Trophy_Alchemist_Mask"
# Zombies porteurs d'acide de la Chimère : posés par ChimeraSystem (Java), jamais par un marqueur.
FEEDER = "Nakasar_Chimera_Feeder"
HEART_DROP = "Nakasar_Drop_Trophy_Chimera_Heart"
# Livres de chapitre du Codex : apparus par CodexSystem (Java) sur un pupitre, jamais par un marqueur.
CHAPTERS = [f"Nakasar_Codex_Chapter_{spell}" for spell in ("Fire", "Frost", "Rain")]
CODEX_STUNNED = "Nakasar_Codex_Stunned"
# Tourbillons de pages coupantes : invoqués par CodexSystem (Java) dès la deuxième phase, qui inflige aussi leurs dégâts.
VORTEX = "Nakasar_Codex_Page_Vortex"
CLASP_DROP = "Nakasar_Drop_Trophy_Codex_Clasp"

SALT = "Ingredient_Nakasar_Philosophers_Salt"
SULFUR = "Ingredient_Nakasar_Burning_Sulfur"
MERCURY = "Ingredient_Nakasar_Quicksilver"

GOLEM_SLAM_RADIUS = 4.0
BRASS_SLAM_RADIUS = 4.5
FLASK_RADIUS = 3.0
DISCHARGE_RADIUS = 3.5
SURGE_RADIUS = 6.0
PAGES_RANGE = 7.0
PAGES_ARC = 70
CHAPTER_CAST = 6.0
CHIMERA_SLAM_RADIUS = 5.5
CHIMERA_TAIL_RADIUS = 5.0
RESPAWN = 7200  # une instance vit bien moins longtemps : les mobs tués ne reviennent pas

timer = ge.timer
damage = ge.damage
warning = ge.warning
ground_particles = ge.ground_particles
melee_tag = ge.melee_tag
single = ge.single
write_json = ge.write_json


def name_key(role):
    return f"{LANG}.npc.{role.removeprefix('Nakasar_')}.name"


def ranged_tag(*names):
    return {"Tags": {"Attack": ["Ranged"]}, "Interactions": list(names)}


# --- briques de rôle ------------------------------------------------------------------------

def walk(speed, jump=1.0):
    return [{"Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "MaxFallSpeed": 10, "Acceleration": 10,
             "JumpHeight": jump}]


def melee(attack, rng, pause, turn=1.5):
    return {"Sensor": {"Type": "Target", "Range": rng, "Filters": [{"Type": "LineOfSight"}]},
            "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": turn},
            "ActionsBlocking": True,
            "Actions": [{"Type": "Attack", "Attack": attack, "AttackPauseRange": list(pause)},
                        {"Type": "Timeout", "Delay": [0.2, 0.2]}]}


def cast(timer_name, attack, rng, comment):
    """Tir visé (projectile) quand la cible est en vue à moins de rng blocs, à chaque fin de recharge."""
    return {"$Comment": comment,
            "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": rng, "Filters": [{"Type": "LineOfSight"}]},
                                                  {"Type": "Timer", "Name": timer_name, "State": "STOPPED"}]},
            "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 2},
            "ActionsBlocking": True,
            "Actions": [{"Type": "TimerRestart", "Name": timer_name},
                        {"Type": "Attack", "Attack": attack, "AimingTimeRange": [0.2, 0.4]}]}


def chase(rng, speed=1.0, stop=1.4, pathfinder=True):
    return {"Sensor": {"Type": "Target", "Range": rng},
            "BodyMotion": {"Type": "Seek", "RelativeSpeed": speed, "SlowDownDistance": max(2, stop + 1), "StopDistance": stop,
                           "UsePathfinder": pathfinder},
            "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5}}


def keep_distance(rng, near, far):
    return {"$Comment": f"Garde ses distances : entre {near:g} et {far:g} blocs de sa cible, en se décalant sur le côté.",
            "Sensor": {"Type": "Target", "Range": rng},
            "BodyMotion": {"Type": "MaintainDistance", "DesiredDistanceRange": [near, far], "MoveThreshold": 0.5,
                           "RelativeForwardsSpeed": 0.8, "RelativeBackwardsSpeed": 0.8,
                           "StrafingDurationRange": [0.8, 1.6], "StrafingFrequencyRange": [1.5, 3.0]},
            "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5}}


def watch(rng):
    return {"Sensor": {"Type": "Target", "Range": rng}, "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5}}


def wander(radius=4):
    return {"BodyMotion": {"Type": "WanderInCircle", "Radius": radius, "RelativeSpeed": 0.25, "MaxHeadingChange": 50}}


def return_home(heal):
    actions = [{"Type": "State", "State": "Idle"}]
    if heal:
        actions.insert(0, {"Type": "SetStat", "Stat": "Health", "Value": 1000000})
    return {"Sensor": {"Type": "State", "State": "ReturnHome"}, "Instructions": [
        {"Sensor": {"Type": "Damage", "Combat": True, "TargetSlot": "LockedTarget"},
         "Actions": [{"Type": "State", "State": "Combat"}]},
        {"Sensor": {"Type": "Leash", "Range": 2},
         "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.7, "SlowDownDistance": 3, "StopDistance": 1,
                        "UsePathfinder": True}},
        {"$Comment": "De retour à son poste." + (" Il récupère toute sa vie." if heal else ""), "Actions": actions},
    ]}


def role(role_id, comment, appearance, hp, combat, motion, drop=None, sight=14, los=True, leash=24, idle=None,
         timers=None, home=True, heal=False, **extra):
    """Rôle Generic : repos (il guette, attaque à vue ou quand on le frappe), combat, retour au poste si la cible fuit."""
    after_lost = [{"Type": "State", "State": "ReturnHome" if home else "Idle"}]
    doc = {
        "$Comment": comment + " Généré par tools/generate_tower_mobs.py.",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": name_key(role_id),
        "MaxHealth": hp,
    }
    if drop:
        doc["DropList"] = drop
    doc.update({
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [CREATIONS],
        "MotionControllerList": motion,
    })
    doc.update(extra)
    if timers:
        doc["StateTransitions"] = [{"$Comment": "Entrée en combat : chaque attaque spéciale a sa propre recharge.",
                                    "States": [{"From": ["Idle", "ReturnHome"] if home else ["Idle"], "To": ["Combat"]}],
                                    "Actions": timers}]
    states = [
        {"Sensor": {"Type": "State", "State": "Idle"},
         "Instructions": ge.to_combat_on_sight(sight, los=los) + [idle or {"Actions": []}]},
        {"Sensor": {"Type": "State", "State": "Combat"},
         "Instructions": [{"$Comment": f"Cible perdue ou partie à plus de {leash} blocs.", **ge.lost_target(leash, after_lost)}]
         + combat},
    ]
    if home:
        states.append(return_home(heal))
    doc["Instructions"] = states
    return doc


# --- interactions ---------------------------------------------------------------------------

def swing(comment, anim_set, anim, run_time, amount, end=2.8, length=100, direction="ToLeft", yaw=50, extra=None,
          sound="SFX_Light_Melee_T2_Swing", impact="SFX_T1_Impact_Blunt", knockback=None):
    effects = {"WorldSoundEventId": sound}
    if anim_set:
        effects.update({"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": anim})
    return {
        "$Comment": comment,
        "Type": "Simple",
        "RunTime": run_time,
        "Effects": effects,
        "Next": {
            "Type": "Selector",
            "RunTime": 0.15,
            "Selector": {"Id": "Horizontal", "Direction": direction, "TestLineOfSight": True, "ExtendTop": 0.8,
                         "ExtendBottom": 0.8, "StartDistance": 0.2, "EndDistance": end, "Length": length,
                         "RollOffset": 0, "YawStartOffset": yaw},
            "HitEntity": {"Interactions": damage(amount, sound=impact, particles="Impact_Sword_Basic_Stronk",
                                                 knockback=knockback, extra=extra)},
        },
    }


def effect_on_target(effect, seconds):
    return {"Type": "ApplyEffect", "EffectId": effect, "Entity": "Target", "Duration": seconds}


def golem_slam(who="du golem de plomb", amount=30, radius=GOLEM_SLAM_RADIUS):
    return {
        "$Comment": f"Frappe au sol annoncée {who} : il s'immobilise 1,4 s, rougeoie et une zone rouge de {radius:g} blocs se charge au sol, puis il frappe le sol ({amount} dégâts, projection). On l'évite en sortant de la zone.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "ApplyEffect", "EffectId": "Dungeon_Goblin_Mace_Slam_Charge"},
            {"Type": "Simple", "RunTime": 1.4, "Effects": {
                "WorldSoundEventId": "SFX_Spear_Throw_Charge", "Particles": [warning(radius, 1.4)]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "ItemPlayerAnimationsId": "Golem_Firesteel_Default", "ItemAnimationId": "GroundSlam",
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.0)]},
             "Selector": {"Id": "AOECircle", "Range": radius},
             "HitEntity": {"Interactions": damage(amount, sound="SFX_Mace_T2_Signature_Impact", knockback=7)}},
            {"Type": "Simple", "RunTime": 0.8},
        ],
    }


def flask_burst(kind):
    effect, seconds, label = {"Poison": ("Poison_T2", 6, "empoisonne"), "Fire": ("Burn", 4, "enflamme")}[kind]
    particles = [ground_particles("Explosion_Medium", 1.0)]
    if kind == "Poison":
        particles.append(ground_particles("Effect_Poison", 1.5))
    return {
        "$Comment": f"Une fiole vivante arrivée au contact s'immobilise et grésille 1,2 s au-dessus d'une zone rouge de {FLASK_RADIUS:g} blocs, puis éclate : 16 dégâts et {label} ({effect}, {seconds} s) tous ceux restés dans la zone. Elle disparaît dans l'explosion (sans butin).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.2, "Effects": {
                "WorldSoundEventId": "SFX_Bomb_Fuse", "Particles": [warning(FLASK_RADIUS, 1.2)]}},
            {"Type": "Selector", "RunTime": 0.1, "Effects": {
                "WorldSoundEventId": "SFX_Goblin_Lobber_Bomb_Death",
                "Particles": particles},
             "Selector": {"Id": "AOECircle", "Range": FLASK_RADIUS},
             "HitEntity": {"Interactions": damage(16, extra=[effect_on_target(effect, seconds)])}},
            {"Type": "RemoveEntity", "Entity": "User"},
        ],
    }


def throw(projectile, comment, anim_set="Throwing_Knife", anim="Throw", wind_up=0.4, sound="SFX_Unarmed_Swing"):
    return {"$Comment": comment, "Type": "Simple", "RunTime": wind_up,
            "Effects": {"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": anim},
            "Next": {"Type": "LaunchProjectile", "RunTime": 0.3, "Effects": {"WorldSoundEventId": sound},
                     "ProjectileId": projectile, "Tags": {"AimingReference": []}}}


def discharge():
    return {
        "$Comment": f"Décharge de l'élémentaire de foudre, annoncée : il se fige 1 s, crépite et une zone rouge de {DISCHARGE_RADIUS:g} blocs se charge au sol, puis la foudre éclate autour de lui (14 dégâts, étourdit 1 s, Hazard_Electric_Stun).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.0, "Effects": {
                "ItemPlayerAnimationsId": "Spirit_Root_Default", "ItemAnimationId": "SporeGas",
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted", "Particles": [warning(DISCHARGE_RADIUS, 1.0)]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Explosion_Medium", 0.8)]},
             "Selector": {"Id": "AOECircle", "Range": DISCHARGE_RADIUS},
             "HitEntity": {"Interactions": damage(14, extra=[effect_on_target("Hazard_Electric_Stun", 1)])}},
            {"Type": "Simple", "RunTime": 0.5},
        ],
    }


def surge():
    return {
        "$Comment": f"Onde de foudre du golem de cristal instable, annoncée : il se fige 1,6 s, ses cristaux crépitent et une zone rouge de {SURGE_RADIUS:g} blocs se charge au sol ; puis il frappe le sol (28 dégâts, projection, étourdit 1,5 s). On l'évite en sortant de la zone.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "ApplyEffect", "EffectId": "Dungeon_Goblin_Mace_Slam_Charge"},
            {"Type": "Simple", "RunTime": 1.6, "Effects": {
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted", "Particles": [warning(SURGE_RADIUS, 1.6)]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "ItemPlayerAnimationsId": "Golem_Crystal_Thunder_Default", "ItemAnimationId": "GroundSlam",
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.4), ground_particles("Explosion_Medium", 1.2)]},
             "Selector": {"Id": "AOECircle", "Range": SURGE_RADIUS},
             "HitEntity": {"Interactions": damage(28, knockback=7,
                                                  extra=[effect_on_target("Hazard_Electric_Stun", 1.5)])}},
            {"Type": "Simple", "RunTime": 0.8},
        ],
    }


def gargoyle_dive():
    return {
        "$Comment": "Piqué de la gargouille : elle surgit à 1,5-2,5 blocs de sa cible (téléportation du rôle) et la griffe aussitôt (16 dégâts, sans recul : jamais dans le vide).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "Simple", "RunTime": 0.3, "Effects": {"WorldSoundEventId": "SFX_Spirit_Root_Alerted"}},
            {"Type": "Selector", "RunTime": 0.1, "Effects": {"WorldSoundEventId": "SFX_Light_Melee_T2_Swing"},
             "Selector": {"Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": False, "ExtendTop": 1.2,
                          "ExtendBottom": 1.2, "StartDistance": 0.1, "EndDistance": 3.2, "Length": 120,
                          "RollOffset": 0, "YawStartOffset": 60},
             "HitEntity": {"Interactions": damage(16, particles="Impact_Sword_Basic_Stronk")}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def codex_pages():
    marks = [{"SystemId": "Feastmaster_Slam_Warning", "TargetEntityPart": "Entity", "TargetNodeName": "Origin",
              "Scale": round(ge.WARNING_SCALE * r, 2), "PositionOffset": {"X": 0, "Y": 0.1, "Z": z},
              "DetachedFromModel": True} for z, r in ((2, 1.4), (4, 2.0), (6, 2.6))]
    return {
        "$Comment": f"Nuée de pages du Codex vivant, annoncée : il se fige 1,1 s, ses pages s'agitent et un cône de {PAGES_RANGE:g} blocs se marque au sol devant lui (trois zones rouges) ; puis les pages tranchent tout le cône ({PAGES_ARC} degrés, 16 dégâts, sans recul).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.1, "Effects": {
                "ItemPlayerAnimationsId": CODEX, "ItemAnimationId": "Pages",
                "WorldSoundEventId": "SFX_Skeleton_Mage_Spellbook_Charge", "Particles": marks}},
            {"Type": "Selector", "RunTime": 0.2, "Effects": {"WorldSoundEventId": "SFX_Light_Melee_T2_Swing"},
             "Selector": {"Id": "Horizontal", "Direction": "ToLeft", "TestLineOfSight": False, "ExtendTop": 1.5,
                          "ExtendBottom": 2.5, "StartDistance": 0.2, "EndDistance": PAGES_RANGE, "Length": PAGES_ARC,
                          "RollOffset": 0, "YawStartOffset": PAGES_ARC // 2},
             "HitEntity": {"Interactions": damage(16, particles="Impact_Sword_Basic_Stronk")}},
            {"Type": "Simple", "RunTime": 0.4},
        ],
    }


def codex_chapter():
    return {
        "$Comment": f"Le Codex vivant ouvre un chapitre : il se fige 1,2 s, s'ouvre en grand, puis un livre de chapitre apparaît sur un pupitre (Nakasar_CodexChapter, CodexSystem). Les joueurs ont {CHAPTER_CAST:g} s pour le détruire.",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.2, "Effects": {
                "ItemPlayerAnimationsId": CODEX, "ItemAnimationId": "Chapter",
                "WorldSoundEventId": "SFX_Skeleton_Mage_Spellbook_Charge"}},
            {"Type": "Nakasar_CodexChapter", "CastTime": CHAPTER_CAST},
            {"Type": "Simple", "RunTime": 0.3},
        ],
    }


def chimera_slam():
    return {
        "$Comment": f"Le dragon se cabre, annoncé : il se dresse 1,15 s, ailes à demi ouvertes, et une zone rouge de {CHIMERA_SLAM_RADIUS:g} blocs se charge au sol autour de lui ; puis il retombe de tout son poids (28 dégâts, ralentit 2 s, sans recul).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 1.15, "Effects": {
                "ItemPlayerAnimationsId": CHIMERA, "ItemAnimationId": "Slam",
                "WorldSoundEventId": "SFX_Spear_Throw_Charge", "Particles": [warning(CHIMERA_SLAM_RADIUS, 1.15)]}},
            {"Type": "Selector", "RunTime": 0.15, "Effects": {
                "WorldSoundEventId": "SFX_Goblin_Feastmaster_Slam",
                "Particles": [ground_particles("Stick_Slam_Ground_Large", 1.2)]},
             "Selector": {"Id": "AOECircle", "Range": CHIMERA_SLAM_RADIUS},
             "HitEntity": {"Interactions": damage(28, sound="SFX_Mace_T2_Signature_Impact",
                                                  extra=[effect_on_target("Slow", 2)])}},
            {"Type": "Simple", "RunTime": 0.45},
        ],
    }


def chimera_tail():
    return {
        "$Comment": f"Fauchage de la queue, annoncé : le dragon se ramasse 0,75 s, la queue ramenée sur le côté, et une zone rouge de {CHIMERA_TAIL_RADIUS:g} blocs se charge autour de lui ; puis il tourne sur lui-même et la queue fauche tout autour (14 dégâts, empoisonne 4 s, sans recul).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "ClearEntityEffect", "Entity": "User", "EntityEffectId": "Hit_Interrupt_Eligible"},
            {"Type": "ApplyEffect", "EffectId": "Nakasar_Elite_Rooted"},
            {"Type": "Simple", "RunTime": 0.75, "Effects": {
                "ItemPlayerAnimationsId": CHIMERA, "ItemAnimationId": "Tail",
                "WorldSoundEventId": "SFX_Spirit_Root_Alerted", "Particles": [warning(CHIMERA_TAIL_RADIUS, 0.75)]}},
            {"Type": "Selector", "RunTime": 0.2, "Effects": {"WorldSoundEventId": "SFX_Light_Melee_T2_Swing"},
             "Selector": {"Id": "AOECircle", "Range": CHIMERA_TAIL_RADIUS},
             "HitEntity": {"Interactions": damage(14, particles="Impact_Sword_Basic_Stronk",
                                                  extra=[effect_on_target("Poison_T1", 4)])}},
            {"Type": "Simple", "RunTime": 0.3},
        ],
    }


def alchemist_flask():
    return {
        "$Comment": "L'Alchimiste lance ses fioles : il arme son bras 0,45 s, puis l'interaction Java Nakasar_AlchemistFlask (AlchemistSystem) jette une fiole vers chaque joueur proche (une zone annoncée au sol, qui éclate 2 s plus tard selon l'élément : feu, givre, foudre ou racines).",
        "Type": "Serial",
        "Interactions": [
            {"Type": "Simple", "RunTime": 0.45, "Effects": {
                "ItemPlayerAnimationsId": "Throwing_Knife", "ItemAnimationId": "Throw",
                "WorldSoundEventId": "SFX_Unarmed_Swing"}},
            {"Type": "Nakasar_AlchemistFlask"},
            {"Type": "Simple", "RunTime": 0.3},
        ],
    }


def interactions():
    return {
        "Nakasar_NPC_Homunculus_Bite": swing("Morsure d'homoncule (8 dégâts).", "Hound_Bleached_Default", "Bite",
                                             0.33, 8, end=2.2, length=70, yaw=35, sound="SFX_Unarmed_Swing"),
        "Nakasar_NPC_Lead_Golem_Swing_Left": swing("Coup de poing du golem de plomb (gauche, 18 dégâts).",
                                                   "Golem_Firesteel_Default", "SwingLeft", 0.55, 18, end=3.2),
        "Nakasar_NPC_Lead_Golem_Swing_Right": swing("Coup de poing du golem de plomb (droite, 18 dégâts).",
                                                    "Golem_Firesteel_Default", "SwingRight", 0.55, 18, end=3.2,
                                                    direction="ToRight", yaw=-50),
        "Nakasar_NPC_Lead_Golem_Slam": golem_slam(),
        "Nakasar_NPC_Brass_Guardian_Swing_Left": swing("Coup de poing du gardien d'airain (gauche, 24 dégâts).",
                                                       "Golem_Firesteel_Default", "SwingLeft", 0.55, 24, end=3.6),
        "Nakasar_NPC_Brass_Guardian_Swing_Right": swing("Coup de poing du gardien d'airain (droite, 24 dégâts).",
                                                        "Golem_Firesteel_Default", "SwingRight", 0.55, 24, end=3.6,
                                                        direction="ToRight", yaw=-50),
        "Nakasar_NPC_Brass_Guardian_Slam": golem_slam("du gardien d'airain", 36, BRASS_SLAM_RADIUS),
        "Nakasar_NPC_Flask_Burst_Poison": flask_burst("Poison"),
        "Nakasar_NPC_Flask_Burst_Fire": flask_burst("Fire"),
        "Nakasar_NPC_Apprentice_Throw": throw("Nakasar_Apprentice_Flask",
                                              "L'apprenti lance une fiole qui éclate à l'impact (12 dégâts autour)."),
        "Nakasar_NPC_Snapdragon_Bite": swing("Morsure empoisonnée du Snapdragon (14 dégâts, poison Poison_T1 5 s).",
                                             "Tiger_Sabertooth_Default", "Bite", 0.4, 14, end=3.2, length=80, yaw=40,
                                             sound="SFX_Unarmed_Swing", extra=[effect_on_target("Poison_T1", 5)]),
        "Nakasar_NPC_Elemental_Fireball": throw("Nakasar_Elemental_Fireball",
                                                "Boule de feu de l'élémentaire de feu (12 dégâts autour de l'impact).",
                                                anim_set="Spirit_Root_Default", anim="SporeGas", wind_up=0.5,
                                                sound="SFX_Fireball_Bounce"),
        "Nakasar_NPC_Elemental_Ice_Bolt": throw("Nakasar_Elemental_Ice_Bolt",
                                                "Trait de glace de l'élémentaire de glace (10 dégâts).",
                                                anim_set="Spirit_Root_Default", anim="SporeGas", wind_up=0.5,
                                                sound="SFX_Ice_Break"),
        "Nakasar_NPC_Elemental_Water_Bolt": throw("Nakasar_Elemental_Water_Bolt",
                                                  "Orbe d'eau de l'élémentaire d'eau (9 dégâts).",
                                                  anim_set="Spirit_Root_Default", anim="SporeGas", wind_up=0.5,
                                                  sound="SFX_Water_MoveIn"),
        "Nakasar_NPC_Elemental_Thorns": throw("Nakasar_Pumpkin_Thorn",
                                              "Épine projetée par l'élémentaire de racine (celle des vrilles de la citrouille).",
                                              anim_set="Spirit_Root_Default", anim="SporeGas", wind_up=0.5,
                                              sound="SFX_Bramble_MoveIn"),
        "Nakasar_NPC_Elemental_Discharge": discharge(),
        "Nakasar_NPC_Crystal_Golem_Surge": surge(),
        "Nakasar_NPC_Gargoyle_Claw": swing("Coup de griffes de la gargouille (12 dégâts, sans recul).", None, None,
                                           0.35, 12, end=2.6, length=90, yaw=45),
        "Nakasar_NPC_Gargoyle_Dive": gargoyle_dive(),
        "Nakasar_NPC_Codex_Pages": codex_pages(),
        "Nakasar_NPC_Codex_Chapter": codex_chapter(),
        "Nakasar_NPC_Chimera_Bite": swing("Morsure du dragon (20 dégâts) : il se jette gueule ouverte.", CHIMERA, "Bite",
                                          0.45, 20, end=4.8, length=80, yaw=40, sound="SFX_Unarmed_Swing"),
        "Nakasar_NPC_Chimera_Slam": chimera_slam(),
        "Nakasar_NPC_Chimera_Tail": chimera_tail(),
        "Nakasar_NPC_Alchemist_Staff_Left": swing("Coup de bâton de l'Alchimiste (gauche, 18 dégâts, sans recul).",
                                                  "Staff", "SwingLeft", 0.5, 18, end=3.4),
        "Nakasar_NPC_Alchemist_Staff_Right": swing("Coup de bâton de l'Alchimiste (droite, 18 dégâts, sans recul).",
                                                   "Staff", "SwingRight", 0.5, 18, end=3.4, direction="ToRight", yaw=-50),
        "Nakasar_NPC_Alchemist_Flask": alchemist_flask(),
    }


def roots():
    return {
        "Root_Nakasar_NPC_Homunculus_Bite": melee_tag("Nakasar_NPC_Homunculus_Bite"),
        "Root_Nakasar_NPC_Lead_Golem_Attack": {
            "$Comment": "Coups de poing du golem de plomb : gauche puis droite.",
            "Tags": {"Attack": ["Melee"]},
            "Interactions": [{"Type": "Chaining", "ChainId": "Nakasar_Lead_Golem", "ChainingAllowance": 15,
                              "Next": ["Nakasar_NPC_Lead_Golem_Swing_Left", "Nakasar_NPC_Lead_Golem_Swing_Right"]}]},
        "Root_Nakasar_NPC_Lead_Golem_Slam": melee_tag("Nakasar_NPC_Lead_Golem_Slam"),
        "Root_Nakasar_NPC_Brass_Guardian_Attack": {
            "$Comment": "Coups de poing du gardien d'airain : gauche puis droite.",
            "Tags": {"Attack": ["Melee"]},
            "Interactions": [{"Type": "Chaining", "ChainId": "Nakasar_Brass_Guardian", "ChainingAllowance": 15,
                              "Next": ["Nakasar_NPC_Brass_Guardian_Swing_Left", "Nakasar_NPC_Brass_Guardian_Swing_Right"]}]},
        "Root_Nakasar_NPC_Brass_Guardian_Slam": melee_tag("Nakasar_NPC_Brass_Guardian_Slam"),
        "Root_Nakasar_NPC_Flask_Burst_Poison": melee_tag("Nakasar_NPC_Flask_Burst_Poison"),
        "Root_Nakasar_NPC_Flask_Burst_Fire": melee_tag("Nakasar_NPC_Flask_Burst_Fire"),
        "Root_Nakasar_NPC_Apprentice_Throw": ranged_tag("Nakasar_NPC_Apprentice_Throw"),
        "Root_Nakasar_NPC_Snapdragon_Bite": melee_tag("Nakasar_NPC_Snapdragon_Bite"),
        "Root_Nakasar_NPC_Elemental_Fireball": ranged_tag("Nakasar_NPC_Elemental_Fireball"),
        "Root_Nakasar_NPC_Elemental_Ice_Bolt": ranged_tag("Nakasar_NPC_Elemental_Ice_Bolt"),
        "Root_Nakasar_NPC_Elemental_Thorns": ranged_tag("Nakasar_NPC_Elemental_Thorns"),
        "Root_Nakasar_NPC_Elemental_Water_Bolt": ranged_tag("Nakasar_NPC_Elemental_Water_Bolt"),
        "Root_Nakasar_NPC_Elemental_Discharge": melee_tag("Nakasar_NPC_Elemental_Discharge"),
        "Root_Nakasar_NPC_Crystal_Golem_Surge": melee_tag("Nakasar_NPC_Crystal_Golem_Surge"),
        "Root_Nakasar_NPC_Gargoyle_Claw": melee_tag("Nakasar_NPC_Gargoyle_Claw"),
        "Root_Nakasar_NPC_Gargoyle_Dive": melee_tag("Nakasar_NPC_Gargoyle_Dive"),
        "Root_Nakasar_NPC_Codex_Pages": melee_tag("Nakasar_NPC_Codex_Pages"),
        "Root_Nakasar_NPC_Codex_Chapter": melee_tag("Nakasar_NPC_Codex_Chapter"),
        "Root_Nakasar_NPC_Chimera_Bite": melee_tag("Nakasar_NPC_Chimera_Bite"),
        "Root_Nakasar_NPC_Chimera_Slam": melee_tag("Nakasar_NPC_Chimera_Slam"),
        "Root_Nakasar_NPC_Chimera_Tail": melee_tag("Nakasar_NPC_Chimera_Tail"),
        "Root_Nakasar_NPC_Alchemist_Staff": {
            "$Comment": "Coups de bâton de l'Alchimiste : gauche puis droite.",
            "Tags": {"Attack": ["Melee"]},
            "Interactions": [{"Type": "Chaining", "ChainId": "Nakasar_Alchemist_Staff", "ChainingAllowance": 15,
                              "Next": ["Nakasar_NPC_Alchemist_Staff_Left", "Nakasar_NPC_Alchemist_Staff_Right"]}]},
        "Root_Nakasar_NPC_Alchemist_Flask": ranged_tag("Nakasar_NPC_Alchemist_Flask"),
    }


def projectiles():
    small_blast = {"DamageEntities": True, "DamageBlocks": False, "BlockDamageRadius": 0, "EntityDamageRadius": 2.5,
                   "EntityDamageFalloff": 1.0}
    return {
        "Nakasar_Apprentice_Flask": {"$Comment": "Fiole lancée par un apprenti : la fiole de poison vanilla, souffle réduit.",
                                     "Parent": "Bomb_Potion_Poison", "Damage": 12, "ExplosionConfig": small_blast},
        "Nakasar_Elemental_Fireball": {"$Comment": "Boule de feu de l'élémentaire de feu : celle du sort vanilla, bien plus faible.",
                                       "Parent": "Fireball", "Damage": 12, "MuzzleVelocity": 22,
                                       "ExplosionConfig": small_blast},
        "Nakasar_Elemental_Ice_Bolt": {"$Comment": "Trait de glace de l'élémentaire de glace.",
                                       "Parent": "Ice_Bolt", "Damage": 10, "MuzzleVelocity": 30},
        "Nakasar_Elemental_Water_Bolt": {"$Comment": "Orbe d'eau de l'élémentaire d'eau : la boule de glace vanilla en vol, éclaboussure d'eau à l'impact.",
                                         "Parent": "Ice_Bolt", "Appearance": "Ice_Ball", "Damage": 9, "MuzzleVelocity": 24,
                                         "HitParticles": {"SystemId": "Dungeon_Goblin_Water_Spout_Splash"},
                                         "DeathParticles": {"SystemId": "Dungeon_Goblin_Water_Spout_Splash"},
                                         "HitSoundEventId": "SFX_Water_MoveIn", "DeathSoundEventId": "SFX_Water_MoveIn"},
    }


# --- rôles ----------------------------------------------------------------------------------

def homunculus_role():
    return role(HOMUNCULUS, "Homoncule : petite créature de chair cultivée en cuve, rapide et fragile, qui chasse en groupe et mord.",
                HOMUNCULUS, 38, [melee("Root_Nakasar_NPC_Homunculus_Bite", 1.8, (0.7, 1.1)), chase(24, stop=1.0)],
                walk(6.5), drop="Nakasar_Drop_Homunculus", sight=14, idle=wander(3), KnockbackScale=1.2,
                DeathAnimationTime=1.0)


def golem_role():
    return role(GOLEM, "Golem de plomb : lent et très solide (380 PV), coups de poing, et frappe au sol annoncée par une zone rouge de 4 blocs toutes les 9 à 12 s.",
                GOLEM, 380, [
                    ge.timed_attack("Slam", "Root_Nakasar_NPC_Lead_Golem_Slam", rng=3.8, los=True,
                                    comment="Frappe au sol annoncée quand la cible est à moins de 3,8 blocs."),
                    melee("Root_Nakasar_NPC_Lead_Golem_Attack", 2.8, (1.3, 1.9), turn=0.8),
                    chase(24, speed=0.9, stop=2.2)],
                walk(2.8, jump=0.5), drop="Nakasar_Drop_Lead_Golem", timers=[timer("Slam", (3, 5), (9, 12))],
                heal=True, KnockbackScale=0.1, DeathAnimationTime=2.0)


def brass_guardian_role():
    return role(BRASS_GUARDIAN, "Gardien d'airain : automate de laiton qui garde la cour de la tour, très solide ; coups de poing lourds et frappe au sol annoncée par une zone rouge de 4,5 blocs dès l'engagement, puis toutes les 6 à 8 s (Kevin : avant, il mourait avant de la lancer). Tous les gardiens abattus, la porte du hall s'ouvre (tower/CourtGuardSystem.java). Il ne quitte pas la cour.",
                BRASS_GUARDIAN, 520, [
                    ge.timed_attack("Slam", "Root_Nakasar_NPC_Brass_Guardian_Slam", rng=4.2, los=True,
                                    comment="Frappe au sol annoncée quand la cible est à moins de 4,2 blocs."),
                    melee("Root_Nakasar_NPC_Brass_Guardian_Attack", 3.2, (1.2, 1.7), turn=0.8),
                    chase(30, speed=0.95, stop=2.6)],
                walk(3.2, jump=0.5), drop="Nakasar_Drop_Brass_Guardian", timers=[timer("Slam", (0.5, 1.5), (6, 8))],
                sight=18, leash=30, heal=True, KnockbackScale=0.0, DeathAnimationTime=2.0)


def flask_role(role_id, kind):
    label = {"Poison": "de poison", "Fire": "de feu"}[kind]
    return role(role_id, f"Fiole vivante {label} : roule vers sa cible et, arrivée au contact, grésille 1,2 s au-dessus d'une zone rouge de 3 blocs puis éclate. Tuée avant, elle lâche son sel.",
                role_id, 24, [
                    {"$Comment": "Au contact : elle éclate (une seule fois, elle disparaît).",
                     "Sensor": {"Type": "Target", "Range": 2.2},
                     "ActionsBlocking": True,
                     "Actions": [{"Type": "Attack", "Attack": f"Root_Nakasar_NPC_Flask_Burst_{kind}", "SkipAiming": True,
                                  "LineOfSight": False, "AvoidFriendlyFire": False}]},
                    chase(24, speed=1.0, stop=1.2)],
                walk(5.0, jump=0.6), drop="Nakasar_Drop_Living_Flask", sight=12, KnockbackScale=1.0,
                DeathAnimationTime=0.3, DeathParticles="Explosion_Medium", home=False)


def apprentice_role():
    return role(APPRENTICE, "Apprenti de l'Alchimiste : mage en robe verte qui garde ses distances et lance des fioles explosives toutes les 2,5 à 3,5 s ; il recule si on le colle.",
                APPRENTICE, 140, [
                    cast("Throw", "Root_Nakasar_NPC_Apprentice_Throw", 14,
                         "Lance une fiole quand sa cible est en vue à moins de 14 blocs."),
                    keep_distance(16, 5, 9),
                    chase(24, stop=8)],
                walk(4.5), drop="Nakasar_Drop_Apprentice", sight=16, timers=[timer("Throw", (0.5, 1.2), (2.5, 3.5))],
                heal=True, HotbarItems=["Weapon_Bomb_Potion_Poison"], KnockbackScale=0.8, DeathAnimationTime=2.0)


def vine_role():
    return role(VINE, "Vrille carnivore de la serre : la vrille de la citrouille géante, mais indépendante. Enracinée, elle projette des épines à distance, fouette et balaie autour d'elle (zone rouge de 3,5 blocs).",
                VINE, 55, [
                    ge.timed_attack("Sweep", "Root_Nakasar_NPC_Pumpkin_Sweep", rng=3,
                                    comment="Balayage circulaire annoncé quand la cible est à moins de 3 blocs."),
                    {"Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": 3},
                                                           {"Type": "Timer", "Name": "Strike", "State": "STOPPED"}]},
                     "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": 2}, "ActionsBlocking": True,
                     "Actions": [{"Type": "TimerRestart", "Name": "Strike"},
                                 {"Type": "Attack", "Attack": "Root_Nakasar_NPC_Pumpkin_Vine_Strike",
                                  "AimingTimeRange": [0.1, 0.2]}]},
                    cast("Thorns", "Root_Nakasar_NPC_Pumpkin_Thorns", 14, "Deux épines projetées jusqu'à 14 blocs."),
                    watch(18)],
                walk(1, jump=0), drop="Nakasar_Drop_Carnivorous_Plant", sight=14, leash=18, home=False,
                timers=[timer("Sweep", (2, 3), (7, 10)), timer("Strike", (0.3, 0.8), (1.8, 2.6)),
                        timer("Thorns", (0.5, 1.5), (3.5, 5))],
                KnockbackScale=0, DeathAnimationTime=0.8, DeathParticles="Block_Break_Leaves")


def snapdragon_role():
    return role(SNAPDRAGON, "Snapdragon de la serre : la plante carnivore vanilla, enracinée dans son bac ; elle mord ce qui passe à portée et l'empoisonne.",
                "Snapdragon", 70, [melee("Root_Nakasar_NPC_Snapdragon_Bite", 3.0, (1.0, 1.5), turn=2), watch(16)],
                walk(1, jump=0), drop="Nakasar_Drop_Carnivorous_Plant", sight=10, leash=16, home=False,
                KnockbackScale=0, DeathAnimationTime=1.0, DeathParticles="Block_Break_Leaves")


def fly(speed, min_h, max_h):
    return ge.fly(speed, min_h, max_h)


def elemental_role(role_id, element):
    common = dict(KnockbackScale=0.8, DeathAnimationTime=1.0)
    if element == "Thunder":
        return role(role_id, "Élémentaire de foudre distillé par l'Alchimiste : fonce sur sa cible et se décharge autour de lui (zone rouge de 3,5 blocs, étourdit).",
                    "Nakasar_Elemental_Thunder", 110, [
                        ge.timed_attack("Discharge", "Root_Nakasar_NPC_Elemental_Discharge", rng=3.0,
                                        comment="Décharge annoncée quand la cible est à moins de 3 blocs."),
                        chase(24, stop=1.5, pathfinder=False)],
                    fly(6, 1.2, 3.5), drop="Nakasar_Drop_Elemental_Thunder", sight=16, los=False,
                    timers=[timer("Discharge", (1, 2), (5, 7))], heal=True, DeathParticles="Explosion_Medium", **common)
    attack, comment, hp, particles = {
        "Fire": ("Root_Nakasar_NPC_Elemental_Fireball", "Élémentaire de feu distillé par l'Alchimiste : vole à distance et lance des boules de feu.", 80, "Effect_Death_Flames"),
        "Frost": ("Root_Nakasar_NPC_Elemental_Ice_Bolt", "Élémentaire de glace distillé par l'Alchimiste : vole à distance et lance des traits de glace.", 70, "Explosion_Medium"),
        "Root": ("Root_Nakasar_NPC_Elemental_Thorns", "Élémentaire de racine distillé par l'Alchimiste : vole à distance et projette des épines.", 60, "Block_Break_Leaves"),
        "Water": ("Root_Nakasar_NPC_Elemental_Water_Bolt", "Élémentaire d'eau distillé par l'Alchimiste : vole à distance et lance des orbes d'eau.", 75, "Dungeon_Goblin_Water_Spout_Splash"),
    }[element]
    # Vol (comme les esprits vanilla, Template_Flying_Aggressive), à 1,5 bloc au moins du sol : en lévitation sur un
    # contrôleur Walk, ils marchaient au sol et leur modèle s'y enfonçait à moitié (vu en jeu par Kevin). Sans Walk,
    # pas de MaintainDistance : ils s'approchent à 7 blocs et tirent de là.
    return role(role_id, comment, role_id, hp, [
        cast("Cast", attack, 16, "Tir quand la cible est en vue à moins de 16 blocs."),
        chase(24, stop=7, pathfinder=False)],
        fly(5, 1.5, 3.5), drop=f"Nakasar_Drop_Elemental_{element}", sight=16, los=False,
        timers=[timer("Cast", (0.8, 1.6), (2.8, 3.8))], heal=True, DeathParticles=particles, **common)


def crystal_golem_role():
    hits = {"Swing_Left_Damage": "Golem_Crystal_Swing_Left_Damage", "Swing_Right_Damage": "Golem_Crystal_Swing_Right_Damage",
            "Spin_Damage": "Golem_Crystal_Spin_Damage", "Ground_Slam_Damage": "Golem_Crystal_Ground_Slam_Damage",
            "Stomp_Damage": "Golem_Crystal_Stomp_Damage", "Spin_Heavy_Damage": "Golem_Crystal_Spin_Heavy_Damage",
            "Clap_Damage": "Golem_Crystal_Clap_Damage"}
    variables = {var: {"Interactions": [{"Parent": parent, "DamageCalculator": {
        "Type": "Absolute", "BaseDamage": {"Physical": 22}, "RandomPercentageModifier": 0.1},
        "DamageEffects": {"Knockback": {"Force": -10}}}]} for var, parent in hits.items()}
    return role(CRYSTAL_GOLEM, "Golem de cristal instable (élite de la Salle des Transmutations), avec barre de vie de boss (BossBarSystem) : combo du golem de cristal vanilla (22 dégâts par coup) et onde de foudre annoncée par une zone rouge de 6 blocs toutes les 12 à 15 s (étourdit). Retourne à sa place et regagne sa vie si on fuit.",
                CRYSTAL_GOLEM, 800, [
                    ge.timed_attack("Surge", "Root_Nakasar_NPC_Crystal_Golem_Surge", rng=6, los=True,
                                    comment="Onde de foudre annoncée quand la cible est à moins de 6 blocs."),
                    melee("Root_NPC_Golem_Crystal_Attack", 3.2, (0.8, 1.5), turn=0.6),
                    chase(26, speed=0.9, stop=2.6)],
                walk(3.4, jump=0.5), drop="Nakasar_Drop_Crystal_Golem", sight=14, leash=26,
                timers=[timer("Surge", (5, 7), (12, 15))], heal=True, KnockbackScale=0.05, DeathAnimationTime=2.0,
                DeathParticles="Explosion_Medium", InteractionVars=variables)


def gargoyle_role():
    return role(GARGOYLE, "Gargouille animée de l'Escalier des vents : vole autour de la tour, pique sur sa cible toutes les 6 à 8 s et la griffe. Aucun recul (jamais dans le vide).",
                GARGOYLE, 65, [
                    {"$Comment": "Piqué : elle surgit près de sa cible (à moins de 16 blocs) et la griffe aussitôt.",
                     "Sensor": {"Type": "And", "Sensors": [{"Type": "Target", "Range": 16},
                                                           {"Type": "Not", "Sensor": {"Type": "Target", "Range": 4}},
                                                           {"Type": "Timer", "Name": "Dive", "State": "STOPPED"}]},
                     "BodyMotion": {"Type": "Teleport", "OffsetRange": [1.5, 2.5], "MaxYOffset": 1,
                                    "Orientation": "TowardsTarget"},
                     "HeadMotion": {"Type": "Watch", "RelativeTurnSpeed": 1.5},
                     "ActionsBlocking": True,
                     "Actions": [{"Type": "TimerRestart", "Name": "Dive"},
                                 {"Type": "Attack", "Attack": "Root_Nakasar_NPC_Gargoyle_Dive", "SkipAiming": True,
                                  "LineOfSight": False, "AvoidFriendlyFire": False}]},
                    melee("Root_Nakasar_NPC_Gargoyle_Claw", 2.4, (0.9, 1.4)),
                    chase(24, stop=1.5, pathfinder=False)],
                fly(6, 1, 5), drop="Nakasar_Drop_Gargoyle", sight=18, los=False,
                timers=[timer("Dive", (1.5, 2.5), (6, 8))], heal=True, KnockbackScale=0,
                DeathAnimationTime=1.2, DeathParticles="Effect_Death_Bones")


def codex_role():
    return role(CODEX, "Codex vivant, gardien de la bibliothèque (boss de l'étape 5), avec barre de vie de boss : flotte au centre de la rotonde entre les trois pupitres, nuée de pages dans un cône annoncé toutes les 4,5 à 6 s, chapitre toutes les 28 à 32 s (CodexSystem : livre à détruire sur un pupitre, sinon feu, givre ou pluie de livres). CodexSystem mène ses trois phases (70 % et 40 % de vie : onde annoncée qui tourne la page) : jets d'encre annoncés, tourbillons de pages dès la deuxième, deux chapitres à la fois et rayonnages qui s'effondrent dans la troisième. Ne quitte pas le centre de l'arène ; remise à zéro par CodexSystem si le groupe meurt ou sort.",
                CODEX, 1500, [
                    ge.timed_attack("Chapter", "Root_Nakasar_NPC_Codex_Chapter",
                                    comment="Ouvre un chapitre à chaque fin de recharge."),
                    ge.timed_attack("Pages", "Root_Nakasar_NPC_Codex_Pages", rng=PAGES_RANGE - 0.5,
                                    comment=f"Nuée de pages quand la cible est à moins de {PAGES_RANGE - 0.5:g} blocs."),
                    {"$Comment": "Ne s'éloigne jamais à plus de 5 blocs du centre de l'arène.",
                     "Sensor": {"Type": "Leash", "Range": 5},
                     "BodyMotion": {"Type": "Seek", "RelativeSpeed": 0.6, "SlowDownDistance": 2, "StopDistance": 1,
                                    "UsePathfinder": False}},
                    chase(12, speed=0.5, stop=3.5, pathfinder=False),
                    watch(40)],
                fly(3, 0.2, 0.8), drop="Nakasar_Drop_Living_Codex", sight=18, los=False, leash=40,
                timers=[timer("Chapter", (8, 10), (28, 32)), timer("Pages", (2, 3), (4.5, 6))], heal=True,
                KnockbackScale=0, DeathAnimationTime=1.6, DeathParticles="Explosion_Medium")


def chapter_role(role_id):
    spell = role_id.rsplit("_", 1)[1]
    return role(role_id, f"Livre de chapitre du Codex vivant ({spell}) : posé sur un pupitre par CodexSystem pendant l'incantation. Fragile, ne se défend pas ; le détruire à temps interrompt le sort et étourdit le Codex.",
                role_id, 40, [], fly(0.1, 0.2, 0.5), sight=0.5, los=False, home=False,
                DefaultPlayerAttitude="Neutral", KnockbackScale=0, DeathAnimationTime=0.3,
                DeathParticles="Explosion_Medium")


def vortex_role():
    return role(VORTEX, "Tourbillon de pages coupantes invoqué par le Codex vivant (CodexSystem, deuxième et troisième phases) : flotte vers le joueur le plus proche, un peu moins vite qu'un joueur qui court. Il n'attaque pas lui-même : CodexSystem entaille les joueurs à moins de 1,8 bloc et le dissipe au bout de 22 s. Fragile, on peut aussi le détruire.",
                VORTEX, 50, [chase(40, speed=0.75, stop=0.3, pathfinder=False)],
                fly(5, 0.2, 0.6), sight=40, los=False, leash=40, home=False,
                KnockbackScale=0.4, DeathAnimationTime=0.6, DeathParticles="Block_Break_Dust")


def chimera_role():
    return role(CHIMERA, "Chimère du laboratoire, second mini-boss de la Tour de l'Alchimiste, avec barre de vie de boss : un dragon qui ne vole pas. Morsure, cabré qui retombe annoncé toutes les 9 à 12 s, fauchage de la queue annoncé toutes les 10 à 13 s. ChimeraSystem (Java) mène les zombies porteurs d'acide qui la soignent, l'acide de la cuve et la remise à zéro.",
                CHIMERA, 1800, [
                    ge.timed_attack("Slam", "Root_Nakasar_NPC_Chimera_Slam", rng=CHIMERA_SLAM_RADIUS - 1,
                                    comment="Se cabre et retombe, annoncé, quand la cible est à portée."),
                    ge.timed_attack("Tail", "Root_Nakasar_NPC_Chimera_Tail", rng=CHIMERA_TAIL_RADIUS - 0.5,
                                    comment="Fauchage de la queue annoncé quand la cible est tout près."),
                    melee("Root_Nakasar_NPC_Chimera_Bite", 4.4, (0.6, 1.0), turn=1.2),
                    chase(36, speed=1.0, stop=3.4)],
                walk(4.5, jump=0.5), drop="Nakasar_Drop_Lab_Chimera", sight=16, leash=40,
                timers=[timer("Slam", (4, 6), (9, 12)), timer("Tail", (6, 8), (10, 13))], heal=True,
                KnockbackScale=0.1, DeathAnimationTime=1.8, DeathParticles="Explosion_Medium")


def feeder_role():
    return {
        "$Comment": "Zombie porteur d'acide : ChimeraSystem le fait sortir près d'un bassin secondaire du laboratoire, où il remplit son seau (gelé quelques secondes), puis il marche vers la cuve centrale (son point d'attache, fixé par ChimeraSystem) ; il ne se bat pas. Arrivé à la margelle, il verse son seau (ChimeraSystem le retire et soigne la Chimère) ; tué avant, il ne soigne rien. Généré par tools/generate_tower_mobs.py.",
        "Type": "Generic",
        "Appearance": "Zombie",
        "NameTranslationKey": name_key(FEEDER),
        "MaxHealth": 30,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [CREATIONS],
        "MotionControllerList": walk(3.2),
        "HotbarItems": ["Container_Bucket"],
        "KnockbackScale": 1.0,
        "DeathAnimationTime": 0.8,
        "Instructions": [
            {"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [
                {"$Comment": "Marche vers la cuve.",
                 "Sensor": {"Type": "Leash", "Range": 0.8},
                 "BodyMotion": {"Type": "Seek", "RelativeSpeed": 1.0, "SlowDownDistance": 1.5, "StopDistance": 0.5,
                                "UsePathfinder": True}},
                {"Actions": []}]},
        ],
    }


def alchemist_role():
    return role(ALCHEMIST, "L'Alchimiste, boss final de la Tour, avec barre de vie de boss : coups de bâton, et fioles des quatre éléments lancées vers chaque joueur proche toutes les 6 à 8 s (Nakasar_AlchemistFlask, zones annoncées au sol). AlchemistSystem (Java) mène le reste : vie selon la taille du groupe et le levier du mode difficile, trois phases (Transmutation, Grand Œuvre dans l'athanor avec ses homoncules et le rebord qui s'effondre, Convergence des quatre piliers), fioles de soin, remise à zéro et sceau du bureau.",
                ALCHEMIST, 3200, [
                    ge.timed_attack("Flask", "Root_Nakasar_NPC_Alchemist_Flask", rng=30,
                                    comment="Lance ses fioles quand une cible est à moins de 30 blocs."),
                    melee("Root_Nakasar_NPC_Alchemist_Staff", 3.2, (0.9, 1.4), turn=1.4),
                    chase(48, speed=1.0, stop=2.4)],
                walk(5.0, jump=0.5), drop="Nakasar_Drop_Alchemist", sight=20, leash=50,
                timers=[timer("Flask", (2, 3), (6, 8))], HotbarItems=["Weapon_Staff_Crystal_Purple"],
                KnockbackScale=0, DeathAnimationTime=2.0, DeathParticles="Explosion_Medium")


def athanor_homunculus_role():
    return role(ATHANOR_HOMUNCULUS, "Homoncule du Grand Œuvre : sorti de l'athanor par AlchemistSystem pendant la deuxième phase de l'Alchimiste, qui reste invulnérable tant qu'il en reste. Chasse tout le groupe sur la terrasse, sans butin.",
                HOMUNCULUS, 45, [melee("Root_Nakasar_NPC_Homunculus_Bite", 1.8, (0.7, 1.1)), chase(60, stop=1.0)],
                walk(6.5), sight=60, los=False, leash=80, home=False, KnockbackScale=1.0, DeathAnimationTime=1.0)


def pillar_role(role_id):
    element = role_id.rsplit("_", 1)[1]
    return role(role_id, f"Pilier élémentaire de la Convergence ({element}) : posé par AlchemistSystem au début de la troisième phase de l'Alchimiste (gelé, immobile). Tant qu'il tient, l'Alchimiste peut prendre son élément ; le détruire le retire du cycle, et les quatre détruits l'épuisent.",
                role_id, 260, [], walk(0.1), sight=0.5, los=False, home=False,
                DefaultPlayerAttitude="Neutral", KnockbackScale=0, DeathAnimationTime=1.0,
                DeathParticles="Explosion_Medium")


def alchemist_exhausted_effect():
    return {
        "$Comment": "Alchimiste épuisé (les quatre piliers de la Convergence détruits) : il s'effondre (AlchemistSystem gèle aussi son IA) et subit 50 % de dégâts en plus pendant 8 s.",
        "ApplicationEffects": {"Particles": [{"SystemId": "Stunned", "TargetEntityPart": "Self", "TargetNodeName": "Head",
                                             "PositionOffset": {"Y": 0.6}}]},
        "DamageResistance": {cause: [{"CalculationType": "Percent", "Amount": -0.5}]
                             for cause in ("Physical", "Projectile", "Elemental")},
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 8,
    }


def aspect_effect(element):
    """Élément du moment de l'Alchimiste à la Convergence : teinte et particules (comme Burn, Freeze, Root et
    Hazard_Electric_Stun vanilla), posé et retiré par AlchemistSystem."""
    top, bottom, system, node = {
        "Fire": ("#ff6a1c", "#3a0800", "Effect_Fire", None),
        "Frost": ("#9fe8ff", "#2a6cc8", "Effect_Snow", None),
        "Thunder": ("#ffe066", "#ffbc00", "Hazard_Electric_Stun", "Chest"),
        "Root": ("#5cd04a", "#0c3a10", "Effect_Poison", None),
    }[element]
    particle = {"SystemId": system}
    if node:
        particle.update({"TargetEntityPart": "Entity", "TargetNodeName": node})
    return {
        "$Comment": f"Aspect {element} de l'Alchimiste pendant la Convergence : sa robe, ses fioles et ses verres prennent la couleur de l'élément.",
        "ApplicationEffects": {"EntityTopTint": top, "EntityBottomTint": bottom, "Particles": [particle]},
        "OverlapBehavior": "Overwrite",
        "Infinite": True,
    }


def codex_stunned_effect():
    return {
        "$Comment": "Codex vivant interrompu (livre de chapitre détruit à temps) : étourdi (CodexSystem gèle aussi son IA) et 50 % de dégâts en plus, comme le Festoyeur gobelin (Goblin_Feastmaster_Stunned).",
        "ApplicationEffects": {"Particles": [{"SystemId": "Stunned", "TargetEntityPart": "Self", "TargetNodeName": "Book",
                                             "PositionOffset": {"Y": 1.2}}]},
        "DamageResistance": {cause: [{"CalculationType": "Percent", "Amount": -0.5}]
                             for cause in ("Physical", "Projectile", "Elemental")},
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 6,
    }


def roles():
    return {
        HOMUNCULUS: homunculus_role(),
        GOLEM: golem_role(),
        BRASS_GUARDIAN: brass_guardian_role(),
        FLASK_POISON: flask_role(FLASK_POISON, "Poison"),
        FLASK_FIRE: flask_role(FLASK_FIRE, "Fire"),
        APPRENTICE: apprentice_role(),
        VINE: vine_role(),
        SNAPDRAGON: snapdragon_role(),
        FIRE: elemental_role(FIRE, "Fire"),
        FROST: elemental_role(FROST, "Frost"),
        THUNDER: elemental_role(THUNDER, "Thunder"),
        ROOT: elemental_role(ROOT, "Root"),
        WATER: elemental_role(WATER, "Water"),
        CRYSTAL_GOLEM: crystal_golem_role(),
        GARGOYLE: gargoyle_role(),
        CODEX: codex_role(),
        **{chapter: chapter_role(chapter) for chapter in CHAPTERS},
        VORTEX: vortex_role(),
        CHIMERA: chimera_role(),
        FEEDER: feeder_role(),
        ALCHEMIST: alchemist_role(),
        ATHANOR_HOMUNCULUS: athanor_homunculus_role(),
        **{pillar: pillar_role(pillar) for pillar in PILLARS},
    }


# --- modèles --------------------------------------------------------------------------------

BLAZEN = "Cosmetics/{}"


def apprentice_model():
    """Humanoïde sur le squelette du joueur, tenue de mage Blazen verte (cosmétiques vanilla, CharacterCreator)."""
    def att(model, texture, gradient_set=None, gradient=None):
        doc = {"Model": model, "Texture": texture}
        if gradient_set:
            doc.update({"GradientSet": gradient_set, "GradientId": gradient})
        return doc
    return {
        "$Comment": "Apprenti de l'Alchimiste : capuche, robe, gants et bottes de mage Blazen verts, lunettes de gobelin mage. Humanoïde sur le squelette du joueur.",
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": "03",
        "MinScale": 0.92,
        "MaxScale": 1.02,
        "DefaultAttachments": [
            att("Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel",
                "Characters/Body_Attachments/Faces/Faces_Detached_Textures/Almond_Eyes_Face.png", "Skin", "03"),
            att("Characters/Body_Attachments/Eyes/Eyes.blockymodel",
                "Characters/Body_Attachments/Eyes/Eyes_Textures/Greyscale.png", "Eyes_Gradient", "Green"),
            att("Cosmetics/Head/Hoodie_LongEnd.blockymodel", "Cosmetics/Head/Blazen_Wizard_Hoodie_Green_Texture.png"),
            att("Cosmetics/Face_Accessories/GoblinGoggles.blockymodel", "Cosmetics/Face_Accessories/GoblinGoggles.png",
                "Fantasy_Cotton", "Green"),
            att("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat_Green.png"),
            att("Cosmetics/Gloves/BasicGloves.blockymodel", "Cosmetics/Gloves/Blazen_Wizard_Glove_Green.png"),
            att("Cosmetics/Shoes/AngledBoots.blockymodel", "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots_Green.png"),
        ],
    }


def alchemist_model():
    """Grand et maigre, sur le squelette du joueur : robe de mage violette, chapeau à large bord noir, gants longs et
    bottes de cuir vanilla, et les pièces de tools/generate_alchemist_models.py (masque à bec, tablier, fioles)."""
    def att(model, texture, gradient_set=None, gradient=None):
        doc = {"Model": model, "Texture": texture}
        if gradient_set:
            doc.update({"GradientSet": gradient_set, "GradientId": gradient})
        return doc
    return {
        "$Comment": "L'Alchimiste : masque de cuir à bec et verres violets, chapeau à large bord, robe de mage violette, tablier de cuir taché, ceinture de fioles lumineuses, gants longs. Humanoïde sur le squelette du joueur, grand et maigre.",
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": "01",
        "MinScale": 1.14,
        "MaxScale": 1.14,
        "DefaultAttachments": [
            att("Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel",
                "Characters/Body_Attachments/Faces/Faces_Detached_Textures/Almond_Eyes_Face.png", "Skin", "01"),
            att("Cosmetics/Overtops/Robe_Wizard.blockymodel", "Cosmetics/Overtops/Blazen_Wizard_Coat.png"),
            att("Cosmetics/Head/WideBrimHat.blockymodel", "Cosmetics/Head/WideBrimHat.png", "Faded_Leather", "Black"),
            att("Cosmetics/Gloves/LongDetail_Gloves.blockymodel",
                "Cosmetics/Gloves/LongDetail_Gloves_Textures/Wasteland_Marauder_Texture.png", "Faded_Leather", "BrownDark"),
            att("Cosmetics/Shoes/AngledBoots.blockymodel", "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots.png"),
            att("NPC/Nakasar/Alchemist_Garb/Garb.blockymodel", "NPC/Nakasar/Alchemist_Garb/Texture.png"),
        ],
        "Light": {"Color": "#c47bff", "Radius": 4},
    }


def flask_model(kind):
    texture = {"Poison": "Items/Weapons/Bomb/Potion_Onion_Poison.png",
               "Fire": "NPC/Nakasar/Alchemist/Living_Flask_Fire.png"}[kind]
    light = {"Poison": "#7dff6a", "Fire": "#ff8a2a"}[kind]
    return {
        "$Comment": f"Fiole vivante ({kind}) : la fiole lancée vanilla (Potion_Onion) en grand, comme le baril explosif du Gobliterator ; elle luit.",
        "Model": "Items/Weapons/Bomb/Potion_Onion.blockymodel",
        "Texture": texture,
        "EyeHeight": 0.3,
        "CrouchOffset": 0.0,
        "HitBox": {"Max": {"X": 0.15, "Y": 0.3, "Z": 0.15}, "Min": {"X": -0.15, "Y": 0, "Z": -0.15}},
        "MinScale": 3.5,
        "MaxScale": 3.5,
        "Light": {"Color": light, "Radius": 3},
    }


def models():
    return {
        HOMUNCULUS: {"$Comment": "Homoncule : le petit zombie difforme vanilla, plus petit encore, lueur verdâtre de cuve.",
                     "Parent": "Zombie_Aberrant_Small", "MinScale": 0.7, "MaxScale": 0.8,
                     "Light": {"Color": "#9dff8a", "Radius": 2}},
        GOLEM: {"$Comment": "Golem de plomb : le golem d'acier vanilla (Golem_Firesteel), sans ses flammes.",
                "Parent": "Golem_Firesteel", "Particles": [], "Light": {"Color": "#6d6a80", "Radius": 1}},
        BRASS_GUARDIAN: {"$Comment": "Gardien d'airain : le golem d'acier vanilla retexturé en laiton, lueurs cyan au lieu des braises, plus grand.",
                         "Parent": "Golem_Firesteel", "Texture": "NPC/Nakasar/Alchemist/Brass_Guardian.png",
                         "Particles": [], "MinScale": 1.3, "MaxScale": 1.3, "Light": {"Color": "#5fe8ff", "Radius": 4}},
        FLASK_POISON: flask_model("Poison"),
        FLASK_FIRE: flask_model("Fire"),
        APPRENTICE: apprentice_model(),
        ALCHEMIST: alchemist_model(),
        VINE: {"$Comment": "Vrille carnivore : le modèle de la vrille de la citrouille géante, lueur verte.",
               "Parent": "Nakasar_Pumpkin_Vine", "Light": {"Color": "#8dff7a", "Radius": 3}},
        FIRE: {"$Comment": "Élémentaire de feu : l'esprit de braise vanilla.", "Parent": "Spirit_Ember",
               "MinScale": 1.2, "MaxScale": 1.2},
        FROST: {"$Comment": "Élémentaire de glace : l'esprit de givre vanilla.", "Parent": "Spirit_Frost",
                "MinScale": 1.2, "MaxScale": 1.2},
        THUNDER: {"$Comment": "Élémentaire de foudre : l'esprit de foudre vanilla.", "Parent": "Spirit_Thunder",
                  "MinScale": 1.2, "MaxScale": 1.2},
        ROOT: {"$Comment": "Élémentaire de racine : l'esprit de racine vanilla.", "Parent": "Spirit_Root",
               "MinScale": 1.2, "MaxScale": 1.2},
        WATER: {"$Comment": "Élémentaire d'eau : l'esprit de givre vanilla passé au bleu profond de l'eau (water_elemental_texture), lueur bleue.",
                "Parent": "Spirit_Frost", "Texture": "NPC/Nakasar/Alchemist/Elemental_Water.png",
                "MinScale": 1.2, "MaxScale": 1.2, "Light": {"Color": "#3a8cff", "Radius": 3}},
        CRYSTAL_GOLEM: {"$Comment": "Golem de cristal instable (élite) : le golem de cristal de foudre vanilla, plus grand, lueur électrique.",
                        "Parent": "Golem_Crystal_Thunder", "MinScale": 1.4, "MaxScale": 1.4,
                        "Light": {"Color": "#9fd8ff", "Radius": 6}},
        GARGOYLE: {"$Comment": "Gargouille : la chauve-souris vanilla taillée dans la pierre (texture recolorée en pierre), en grand.",
                   "Parent": "Bat", "Texture": "NPC/Nakasar/Alchemist/Gargoyle.png", "MinScale": 2.4, "MaxScale": 2.4},
    }


def gargoyle_texture():
    """Pierre grise sur tout l'atlas de la chauve-souris (160 × 96) : la gargouille est une statue, d'une seule
    teinte. Grain doux et taches plus sombres, comme la roche des blocs."""
    rng = random.Random(41)
    w, h = 160, 96
    noise = ga.soft_noise(w, h, scale=5, amp=0.16)
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            f = noise[y][x] + rng.uniform(-0.03, 0.03)
            px[x, y] = tuple(max(0, min(255, int(c * f))) for c in (128, 125, 118)) + (255,)
    return img


def brass_guardian_texture(assets):
    """Gardien d'airain : la texture du golem d'acier vanilla, métal sombre passé au laiton et braises passées au cyan
    alchimique. `assets` est Assets.zip, ou le PNG Common/NPC/Elemental/Golem_Firesteel/Models/Texture.png extrait."""
    if assets.suffix == ".png":
        src = Image.open(assets).convert("RGBA")
    else:
        with zipfile.ZipFile(assets) as z:
            src = Image.open(io.BytesIO(z.read("Common/NPC/Elemental/Golem_Firesteel/Models/Texture.png"))).convert("RGBA")

    def clamp(t):
        return max(0.0, min(1.0, t))

    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            hue, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            warm = 1.0 if (hue < 0.2 or hue > 0.92) else 0.0
            glow = max(warm * clamp((s - 0.25) / 0.35) * clamp((v - 0.35) / 0.35), clamp((v - 0.82) / 0.12))
            bv = clamp(0.10 + v * 1.25)
            brass = colorsys.hsv_to_rgb(0.1, 0.62 - 0.2 * bv, bv)
            cyan = colorsys.hsv_to_rgb(0.49, 0.75 - 0.4 * clamp((v - 0.8) / 0.2), clamp(0.55 + v * 0.5))
            px[x, y] = tuple(int(255 * (brass[i] * (1 - glow) + cyan[i] * glow)) for i in range(3)) + (a,)
    return src


def water_elemental_texture(assets):
    """Élémentaire d'eau : la texture de l'esprit de givre vanilla, bleus pâles passés au bleu profond de l'eau, reflets
    turquoise. `assets` est Assets.zip, ou le PNG Common/NPC/Elemental/Spirit_Frost/Models/Model_Texture.png extrait."""
    if assets.suffix == ".png":
        src = Image.open(assets).convert("RGBA")
    else:
        with zipfile.ZipFile(assets) as z:
            src = Image.open(io.BytesIO(z.read("Common/NPC/Elemental/Spirit_Frost/Models/Model_Texture.png"))).convert("RGBA")
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            hue, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            hue = 0.64 - 0.07 * v  # sombre : bleu profond ; clair : bleu d'eau
            r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(hue, min(1.0, 0.6 + s * 0.5), 0.12 + v * 0.72))
            px[x, y] = (r, g, b, a)
    return src


def fire_flask_texture(assets):
    """Fiole de feu : la texture de la fiole de poison vanilla, teintes vertes tournées vers l'orange. `assets` est
    Assets.zip, ou directement le PNG Common/Items/Weapons/Bomb/Potion_Onion_Poison.png qui en est extrait."""
    if assets.suffix == ".png":
        src = Image.open(assets).convert("RGBA")
    else:
        with zipfile.ZipFile(assets) as z:
            src = Image.open(io.BytesIO(z.read("Common/Items/Weapons/Bomb/Potion_Onion_Poison.png"))).convert("RGBA")
    px = src.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            hue, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if a and 0.15 < hue < 0.55 and s > 0.25:
                r, g, b = (int(c * 255) for c in colorsys.hsv_to_rgb(0.07, min(1.0, s * 1.2), v))  # vert -> orange
                px[x, y] = (r, g, b, a)
    return src


# --- réactifs -------------------------------------------------------------------------------

SALT_WHITE = (236, 236, 228)
SALT_SHADE = (196, 200, 206)
SULFUR_YELLOW = (232, 200, 54)
SULFUR_DARK = (184, 140, 30)
QUICKSILVER = (200, 210, 222)

REAGENT_PARTS = {
    "Philosophers_Salt": [
        ("Dish", (0, 0.5, 0), (10, 1, 10), 0, go.flat(go.GOLD_DARK, go.GOLD), "flat"),
        ("Crystal_A", (-1, 3, 0), (5, 5, 5), 45, go.flat(SALT_SHADE, SALT_WHITE), "flat"),
        ("Crystal_B", (2.5, 2.5, 2), (3, 4, 3), 20, go.flat(SALT_WHITE), "flat"),
        ("Crystal_C", (1.5, 2, -2.5), (3, 3, 3), 60, go.flat(SALT_SHADE), "flat"),
        ("Glint", (-1, 6, 0), (1.5, 1.5, 1.5), 45, go.flat((255, 255, 255)), "fullbright"),
    ],
    "Burning_Sulfur": [
        ("Chunk", (0, 2.5, 0), (7, 5, 6), 15, go.flat(SULFUR_DARK, SULFUR_YELLOW), "flat"),
        ("Spike_A", (-1.5, 6, 0.5), (3, 4, 3), 40, go.flat(SULFUR_YELLOW), "flat"),
        ("Spike_B", (2, 5.5, -1), (2, 3, 2), 10, go.flat(SULFUR_YELLOW), "flat"),
        ("Ember", (0.5, 5, 2), (1.5, 1.5, 1.5), 0, go.flat((255, 120, 40)), "fullbright"),
    ],
    "Quicksilver": go.bottle(QUICKSILVER, band=(150, 160, 175), big=False),
}


def build_reagents(preview):
    ITEM_MODELS.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    for name, parts in REAGENT_PARTS.items():
        ga.PARTS = parts
        ga.TEX_W, ga.TEX_H = 64, 64
        atlas, uv = ga.build_atlas()
        atlas.save(ITEM_MODELS / f"{name}.png")
        model = ga.build_model(uv)
        model["nodes"][0]["name"] = name
        (ITEM_MODELS / f"{name}.blockymodel").write_text(json.dumps(model, indent=2) + "\n")
        top = max(c[1] + s[1] / 2 for _, c, s, *_ in parts)
        span = max(max(s[0], s[2]) for _, c, s, *_ in parts)
        scale = min(200 / max(top, 1), 170 / max(span, 1))
        big = ga.render(atlas, uv, 256, yaw=-35, pitch=28, scale=scale, center=(0, top / 2, 0))
        big.resize((64, 64), Image.LANCZOS).save(ICONS / f"{name}.png")
        if preview:
            big.save(preview / f"reagent_{name}.png")
    for item_id, model in ((SALT, "Philosophers_Salt"), (SULFUR, "Burning_Sulfur"), (MERCURY, "Quicksilver")):
        write_json(ITEMS / f"{item_id}.json", {
            "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name",
                                      "Description": f"{LANG}.items.{item_id}.description"},
            "Icon": f"Icons/Items/Nakasar/Alchemist/{model}.png",
            "Model": f"Items/Nakasar/Alchemist/{model}.blockymodel",
            "Texture": f"Items/Nakasar/Alchemist/{model}.png",
            "Quality": "Uncommon",
            "Categories": ["Items.Ingredients"],
            "PlayerAnimationsId": "Item",
            "ItemSoundSetId": "ISS_Items_Gems",
            "Scale": 1.0,
            "MaxStack": 50,
        })


# --- butins, groupes, apparitions -----------------------------------------------------------

def chance(item, weight, empty, lo=1, hi=None):
    return {"Type": "Choice", "Containers": [
        {"Type": "Single", "Weight": weight, "Item": {"ItemId": item, "QuantityMin": lo, "QuantityMax": hi or lo}},
        {"Type": "Empty", "Weight": empty}]}


def multiple(comment, *containers):
    return {"$Comment": comment, "Container": {"Type": "Multiple", "Containers": list(containers)}}


def drops():
    return {
        "Nakasar_Drop_Homunculus": {"$Comment": "Homoncule : du mercure vif, une fois sur trois.",
                                    "Container": chance(MERCURY, 1, 2)},
        "Nakasar_Drop_Lead_Golem": multiple("Golem de plomb : sel philosophal et parfois du fer.",
                                            single(SALT, 1, 2), chance("Ingredient_Bar_Iron", 1, 2, 1, 2)),
        "Nakasar_Drop_Living_Flask": {"$Comment": "Fiole vivante tuée avant d'éclater : son sel, une fois sur deux.",
                                      "Container": chance(SALT, 1, 1)},
        "Nakasar_Drop_Apprentice": multiple("Apprenti : du mercure vif et parfois une potion de soin.",
                                            single(MERCURY, 1, 2), chance("Potion_Health_Lesser", 1, 3)),
        "Nakasar_Drop_Carnivorous_Plant": {"$Comment": "Plantes carnivores : essence de vie, une fois sur deux.",
                                           "Container": chance("Ingredient_Life_Essence", 1, 1, 1, 2)},
        "Nakasar_Drop_Elemental_Fire": multiple("Élémentaire de feu : essence de feu, soufre ardent une fois sur deux.",
                                                single("Ingredient_Fire_Essence", 1, 2), chance(SULFUR, 1, 1)),
        "Nakasar_Drop_Elemental_Thunder": multiple("Élémentaire de foudre : essence de foudre, soufre ardent une fois sur deux.",
                                                   single("Ingredient_Lightning_Essence", 1, 2), chance(SULFUR, 1, 1)),
        "Nakasar_Drop_Elemental_Frost": {"$Comment": "Élémentaire de glace : essence de glace.",
                                         "Container": single("Ingredient_Ice_Essence", 1, 2)},
        "Nakasar_Drop_Elemental_Water": multiple("Élémentaire d'eau : mercure vif, et essence de glace une fois sur deux.",
                                                 single(MERCURY, 1, 2), chance("Ingredient_Ice_Essence", 1, 1)),
        "Nakasar_Drop_Elemental_Root": {"$Comment": "Élémentaire de racine : essence de vie.",
                                        "Container": single("Ingredient_Life_Essence", 1, 2)},
        "Nakasar_Drop_Crystal_Golem": multiple(
            "Golem de cristal instable (élite) : des essences des quatre éléments et les trois principes.",
            single("Ingredient_Lightning_Essence", 2, 3), single("Ingredient_Fire_Essence", 1, 2),
            single("Ingredient_Ice_Essence", 1, 2), single("Ingredient_Life_Essence", 1, 2),
            single(SALT, 2), single(SULFUR, 2), single(MERCURY, 2)),
        "Nakasar_Drop_Brass_Guardian": multiple("Gardien d'airain : du sel philosophal, du mercure et parfois du fer.",
                                                single(SALT, 1, 2), single(MERCURY, 1, 2),
                                                chance("Ingredient_Bar_Iron", 1, 1, 1, 3)),
        "Nakasar_Drop_Gargoyle": {"$Comment": "Gargouille : du sel philosophal, une fois sur deux.",
                                  "Container": chance(SALT, 1, 1)},
        "Nakasar_Drop_Living_Codex": multiple(
            "Codex vivant (boss de la bibliothèque) : son fermoir (trophée) et les trois principes.",
            {"Type": "Droplist", "DroplistId": CLASP_DROP},
            single(MERCURY, 2, 3), single(SALT, 2, 3), single(SULFUR, 1, 2)),
        "Nakasar_Drop_Lab_Chimera": multiple(
            "Chimère du laboratoire (mini-boss) : son cœur (trophée), les trois principes et de l'essence de vie.",
            {"Type": "Droplist", "DroplistId": HEART_DROP},
            single(SALT, 2, 3), single(SULFUR, 2, 3), single(MERCURY, 2, 3), single("Ingredient_Life_Essence", 1, 2)),
        "Nakasar_Drop_Alchemist": multiple(
            "L'Alchimiste (boss final) : son masque à bec (trophée) et un peu des trois principes pour le groupe ; chaque "
            "joueur reçoit en plus son sac de l'Alchimiste (AlchemistSystem, tools/generate_alchemist_loot.py).",
            {"Type": "Droplist", "DroplistId": MASK_DROP},
            single(SALT, 1, 2), single(SULFUR, 1, 2), single(MERCURY, 1, 2)),
    }


def groups():
    return {
        CREATIONS: {"$Comment": "Créatures de l'Alchimiste : elles ne se blessent pas entre elles (DisableDamageGroups).",
                    "IncludeRoles": ALL + CHAPTERS + [VORTEX, FEEDER, ATHANOR_HOMUNCULUS] + PILLARS},
        FIRE_ELEMENTALS: {"$Comment": "Créatures de feu de la tour : aucun dégât de feu (dans Nakasar_Fire_Immune).",
                          "IncludeRoles": [FIRE, FLASK_FIRE]},
    }


def marker(role_id):
    return {"$Comment": f"{role_id} dans la Tour de l'Alchimiste ; ne revient pas dans la vie d'une instance.",
            "NPCs": [{"Name": role_id, "Weight": 1, "RealtimeRespawnTime": RESPAWN}],
            "RealtimeRespawn": True, "ExclusionRadius": 0}


def spawner(role_id):
    return {
        "$Comment": f"Bloc invisible posé dans la Tour de l'Alchimiste (alchemist_tower.Tower.mobs) : son composant SpawnMarkerBlock crée le marqueur d'apparition {role_id} à cet endroit.",
        "TranslationProperties": {"Name": f"{LANG}.items.Nakasar_Spawner_{role_id.removeprefix('Nakasar_')}.name"},
        "Quality": "Developer",
        "MaxStack": 64,
        "BlockType": {"Material": "Empty", "DrawType": "Empty", "Opacity": "Transparent",
                      "BlockEntity": {"Components": {"SpawnMarkerBlock": {"Config": {"SpawnMarker": role_id}}}}},
    }


VANILLA_WARNINGS = ("Feastmaster_Slam_Warning", "Gobliterator_Slam_Warning")


def telegraph(node):
    """Annonces des attaques plus lisibles (Kevin : « plus visibles et prévisibles ») : toute étape qui marque le sol
    d'une zone rouge dure au moins 1,6 s (0,4 s de plus qu'avant), et ses zones deviennent celles de la tour, dont le
    disque se remplit jusqu'au coup (tools/tower_warnings.py)."""
    if isinstance(node, list):
        for item in node:
            telegraph(item)
        return node
    if not isinstance(node, dict):
        return node
    marks = [m for m in (node.get("Effects") or {}).get("Particles", []) if m.get("SystemId") in VANILLA_WARNINGS]
    if node.get("Type") == "Simple" and marks:
        node["RunTime"] = round(max(1.6, node["RunTime"] + 0.4), 2)
        for m in marks:
            m["SystemId"] = tw.system(node["RunTime"])
    for value in node.values():
        telegraph(value)
    return node


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    assets = Path(sys.argv[sys.argv.index("--vanilla-textures") + 1]) if "--vanilla-textures" in sys.argv else None
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
    for role_id, doc in roles().items():
        write_json(ROLES / f"{role_id}.json", doc)
    for model_id, doc in models().items():
        write_json(MODELS / f"{model_id}.json", doc)
    for name, doc in interactions().items():
        write_json(INTERACTIONS / f"{name}.json", telegraph(doc))
    for name, doc in roots().items():
        write_json(ROOTS / f"{name}.json", doc)
    for name, doc in projectiles().items():
        write_json(PROJECTILES / f"{name}.json", doc)
    for name, doc in drops().items():
        write_json(DROPS / f"{name}.json", doc)
    for name, doc in groups().items():
        write_json(GROUPS / f"{name}.json", doc)
    write_json(ge.EFFECTS / f"{CODEX_STUNNED}.json", codex_stunned_effect())
    write_json(ge.EFFECTS / f"{ALCHEMIST_EXHAUSTED}.json", alchemist_exhausted_effect())
    for element, effect_id in ASPECTS.items():
        write_json(ge.EFFECTS / f"{effect_id}.json", aspect_effect(element))
    for role_id in ALL:
        write_json(MARKERS / f"{role_id}.json", marker(role_id))
        write_json(SPAWNERS / f"Nakasar_Spawner_{role_id.removeprefix('Nakasar_')}.json", spawner(role_id))
    NPC_TEXTURES.mkdir(parents=True, exist_ok=True)
    gargoyle_texture().save(NPC_TEXTURES / "Gargoyle.png")
    if assets:
        fire_flask_texture(assets).save(NPC_TEXTURES / "Living_Flask_Fire.png")
    elif not (NPC_TEXTURES / "Living_Flask_Fire.png").exists():
        sys.exit("Living_Flask_Fire.png manquant : relancer avec --vanilla-textures <Assets.zip>")
    firesteel = Path(sys.argv[sys.argv.index("--firesteel-texture") + 1]) if "--firesteel-texture" in sys.argv else assets
    if firesteel and firesteel.suffix != ".png" or "--firesteel-texture" in sys.argv:
        brass_guardian_texture(firesteel).save(NPC_TEXTURES / "Brass_Guardian.png")
    elif not (NPC_TEXTURES / "Brass_Guardian.png").exists():
        sys.exit("Brass_Guardian.png manquant : relancer avec --vanilla-textures <Assets.zip> ou --firesteel-texture <PNG>")
    frost = Path(sys.argv[sys.argv.index("--frost-texture") + 1]) if "--frost-texture" in sys.argv else assets
    if frost:
        water_elemental_texture(frost).save(NPC_TEXTURES / "Elemental_Water.png")
    elif not (NPC_TEXTURES / "Elemental_Water.png").exists():
        sys.exit("Elemental_Water.png manquant : relancer avec --vanilla-textures <Assets.zip> ou --frost-texture <PNG>")
    build_reagents(preview)
    print(f"Zones d'annonce : {tw.write()} dixièmes de seconde")


if __name__ == "__main__":
    main()
