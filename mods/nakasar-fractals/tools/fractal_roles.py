"""Briques des rôles de PNJ et de leurs attaques, copiées du mod Vampires (tools/generate_elites.py et
tools/generate_tower_mobs.py ; pas de bibliothèque commune, Kevin, 20 octobre 2026). Ids propres au mod Fractales :
camp Nakasar_Fractal_Foes, attaques annoncées Nakasar_Fractal_Telegraph, effets Nakasar_Fractal_*.

Les fonctions rendent des dictionnaires JSON ; generate_cliffside.py (et les fractales suivantes) les assemblent.
"""
import json

import generate_mob_loot as loot
import generate_warnings as gw

FOES = "Nakasar_Fractal_Foes"
ROOTED = "Nakasar_Fractal_Rooted"   # effet de pose : l'élite ne recule plus pendant une annonce


def write_json(path, doc):
    if path.parent.name == "Fractals" and path.parent.parent.parent.name == "Roles":
        doc = loot.with_drop_list(path.stem, doc)   # butin des mobs (generate_mob_loot.py)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- capteurs et instructions -------------------------------------------------------------------

def timer(name, start, restart):
    return {"Type": "TimerStart", "Name": name, "StartValueRange": list(start), "RestartValueRange": list(restart)}


def to_combat_on_sight(rng, los=True):
    filters = [{"Type": "Attitude", "Attitudes": ["Hostile"]}] + ([{"Type": "LineOfSight"}] if los else [])
    return [
        {"Sensor": {"Type": "Damage", "Combat": True, "TargetSlot": "LockedTarget"},
         "Actions": [{"Type": "State", "State": "Combat"}]},
        {"Sensor": {"Type": "Player", "Range": rng, "LockOnTarget": True, "Filters": filters},
         "Actions": [{"Type": "State", "State": "Combat"}]},
    ]


def lost_target(rng, actions):
    return {"Sensor": {"Type": "Not", "Sensor": {"Type": "Target", "Range": rng, "Filters": [
        {"Type": "Attitude", "Attitudes": ["Hostile", "Neutral", "Ignore"]}]}},
        "Actions": [{"Type": "ReleaseTarget"}] + actions}


def health_between(low, high):
    """Capteur : la vie du PNJ est entre `low` et `high` (fractions de sa vie max)."""
    return {"Type": "Self", "Filters": [{"Type": "Stat", "Stat": "Health", "StatTarget": "Value", "RelativeTo": "Health",
                                         "RelativeToTarget": "Max", "ValueRange": [low, high]}]}


def timed_attack(timer_name, attack, rng=None, los=False, aim=None, comment=None, extra_sensors=None):
    sensors = [{"Type": "Timer", "Name": timer_name, "State": "STOPPED"}] + list(extra_sensors or [])
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


def walk(speed, jump=1.0):
    return [{"Type": "Walk", "MaxWalkSpeed": speed, "Gravity": 10, "MaxFallSpeed": 10, "Acceleration": 10,
             "JumpHeight": jump}]


def melee(attack, rng, pause, turn=1.5, extra_sensors=None):
    target = {"Type": "Target", "Range": rng, "Filters": [{"Type": "LineOfSight"}]}
    sensor = target if not extra_sensors else {"Type": "And", "Sensors": [target] + list(extra_sensors)}
    return {"Sensor": sensor,
            "HeadMotion": {"Type": "Aim", "RelativeTurnSpeed": turn},
            "ActionsBlocking": True,
            "Actions": [{"Type": "Attack", "Attack": attack, "AttackPauseRange": list(pause)},
                        {"Type": "Timeout", "Delay": [0.2, 0.2]}]}


def cast(timer_name, attack, rng, comment):
    """Tir visé quand la cible est en vue à moins de rng blocs, à chaque fin de recharge."""
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


def role(role_id, comment, appearance, name_key, hp, combat, motion, generator, drop=None, sight=16, los=True,
         leash=28, idle=None, timers=None, home=True, heal=False, **extra):
    """Rôle Generic : repos (il guette, attaque à vue ou quand on le frappe), combat, retour au poste si la cible fuit."""
    after_lost = [{"Type": "State", "State": "ReturnHome" if home else "Idle"}]
    doc = {
        "$Comment": f"{comment} Généré par tools/{generator}.",
        "Type": "Generic",
        "Appearance": appearance,
        "NameTranslationKey": name_key,
        "MaxHealth": hp,
    }
    if drop:
        doc["DropList"] = drop
    doc.update({
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Hostile",
        "DefaultNPCAttitude": "Ignore",
        "DisableDamageGroups": [FOES],
        "MotionControllerList": motion,
    })
    doc.update(extra)
    if timers:
        doc["StateTransitions"] = [{"$Comment": "Entrée en combat : chaque attaque spéciale a sa propre recharge.",
                                    "States": [{"From": ["Idle", "ReturnHome"] if home else ["Idle"], "To": ["Combat"]}],
                                    "Actions": timers}]
    states = [
        {"Sensor": {"Type": "State", "State": "Idle"},
         "Instructions": to_combat_on_sight(sight, los=los) + [idle or {"Actions": []}]},
        {"Sensor": {"Type": "State", "State": "Combat"},
         "Instructions": [{"$Comment": f"Cible perdue ou partie à plus de {leash} blocs.", **lost_target(leash, after_lost)}]
         + combat},
    ]
    if home:
        states.append(return_home(heal))
    doc["Instructions"] = states
    return doc


# --- interactions --------------------------------------------------------------------------------

def warning(radius, seconds):
    """Cercle rouge autour de l'élite, plein au bout de `seconds` (détaché du modèle : il ne la suit pas)."""
    return {"SystemId": gw.system(seconds), "TargetEntityPart": "Entity", "TargetNodeName": "Origin",
            "Scale": gw.scale(radius), "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0}, "DetachedFromModel": True}


def telegraph(shape, seconds, comment=None, **keys):
    """Attaque annoncée calculée en Java (Nakasar_Fractal_Telegraph) : zone rouge de la taille exacte du coup, puis
    le coup sur ce qui s'y trouve encore. Instantanée : la chaîne continue aussitôt (pose de même durée)."""
    doc = {"Type": "Nakasar_Fractal_Telegraph", "Shape": shape, "Seconds": seconds, **keys}
    return {"$Comment": comment, **doc} if comment else doc


def windup(seconds, effects):
    return {"Type": "Simple", "RunTime": seconds, "Effects": effects}


def ground_particles(system, scale):
    return {"SystemId": system, "TargetEntityPart": "Entity", "TargetNodeName": "Origin", "Scale": scale,
            "PositionOffset": {"X": 0, "Y": 0.1, "Z": 0}, "DetachedFromModel": True}


def melee_tag(*names, comment=None):
    doc = {"Tags": {"Attack": ["Melee"]}, "Interactions": list(names)}
    return {"$Comment": comment, **doc} if comment else doc


def ranged_tag(*names, comment=None):
    doc = {"Tags": {"Attack": ["Ranged"]}, "Interactions": list(names)}
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


def effect_on_target(effect, seconds):
    return {"Type": "ApplyEffect", "EffectId": effect, "Entity": "Target", "Duration": seconds}


def swing(comment, anim_set, anim, run_time, amount, end=2.8, length=100, direction="ToLeft", yaw=50, extra=None,
          sound="SFX_Light_Melee_T2_Swing", impact="SFX_T1_Impact_Blunt", knockback=None, interrupt=False,
          extend_bottom=0.8):
    """Coup au contact : balayage horizontal à hauteur des yeux de l'attaquant ; `extend_bottom` le fait descendre
    (grands monstres dont les yeux sont au-dessus de la tête d'un joueur)."""
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
                         "ExtendBottom": extend_bottom, "StartDistance": 0.2, "EndDistance": end, "Length": length,
                         "RollOffset": 0, "YawStartOffset": yaw},
            "HitEntity": {"Interactions": damage(amount, sound=impact, particles="Impact_Sword_Basic_Stronk",
                                                 knockback=knockback, extra=extra, interrupt=interrupt)},
        },
    }


def throw(projectile, comment, anim_set="Throwing_Knife", anim="Throw", wind_up=0.4, sound="SFX_Unarmed_Swing"):
    return {"$Comment": comment, "Type": "Simple", "RunTime": wind_up,
            "Effects": {"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": anim},
            "Next": {"Type": "LaunchProjectile", "RunTime": 0.3, "Effects": {"WorldSoundEventId": sound},
                     "ProjectileId": projectile, "Tags": {"AimingReference": []}}}


# --- apparences humanoïdes (squelette du joueur, cosmétiques vanilla) --------------------------------

FACE = "Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel"


def humanoid(comment, skin, face, attachments, scale=None, light=None):
    """Modèle humanoïde sur le squelette du joueur : la face détachée est obligatoire (tête transparente sinon)."""
    doc = {
        "$Comment": comment,
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": skin,
    }
    if scale:
        doc["MinScale"], doc["MaxScale"] = scale
    if light:
        doc["Light"] = light
    doc["DefaultAttachments"] = [
        {"Model": FACE, "Texture": f"Characters/Body_Attachments/Faces/Faces_Detached_Textures/{face}.png",
         "GradientSet": "Skin", "GradientId": skin},
        {"Model": "Characters/Body_Attachments/Eyes/Eyes.blockymodel",
         "Texture": "Characters/Body_Attachments/Eyes/Eyes_Textures/Greyscale.png",
         "GradientSet": "Eyes_Gradient", "GradientId": "Red"},
    ] + [attach(*a) for a in attachments]
    return doc


def attach(model, texture, gradient_set=None, gradient_id=None):
    doc = {"Model": model, "Texture": texture}
    if gradient_set:
        doc["GradientSet"], doc["GradientId"] = gradient_set, gradient_id
    return doc
