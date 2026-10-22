#!/usr/bin/env python3
"""Génère les assets des instabilités (étape 5 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_instabilities.py

Le tirage et les effets sont en Java (dev.nakasar.hytale.fractals.instability) ; ce générateur écrit ce qu'ils
utilisent :
- les effets Vengeance (ennemi renforcé), Bombe de flux (joueur marqué), Ensemble / Isolé (Restez groupés) et leurs
  icônes ;
- la cause de dégâts des instabilités (une part des PV max, l'armure ne la réduit pas) ;
- les particules (flaque toxique, marque et impulsion de la bombe de flux, rire d'un ennemi qui va exploser) ;
- le corbeau de la Nuée (modèle, rôle, attaque) ajouté au camp des fractales ;
- la langue `nakasar_fractals_instabilities.lang` (noms, effets, messages du Java, commande).
"""
import json
import math

from PIL import Image, ImageDraw

import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

SERVER = go.SERVER
COMMON = go.COMMON
LANG = "nakasar_fractals_instabilities"
GENERATOR = "generate_instabilities.py"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Fractals"
PARTICLES = SERVER / "Particles/Nakasar/Fractals/Instabilities"
STATUS_ICONS = gc.STATUS_ICONS
CROW = "Nakasar_Fractal_Crow"
CAUSE = "Nakasar_Fractal_Instability"

# id Java, nom fr, description fr, nom en, description en
INSTABILITIES = [
    ("LastLaugh", "Dernier rire", "les ennemis explosent à leur mort : sortez du cercle rouge.",
     "Last Laugh", "enemies explode when they die: leave the red circle."),
    ("ToxicTrail", "Traînée toxique", "vous laissez des flaques de poison derrière vous.",
     "Toxic Trail", "you leave poison puddles behind you."),
    ("SocialAwkwardness", "Malaise social", "un allié à moins de 2 blocs vous blesse.",
     "Social Awkwardness", "an ally within 2 blocks hurts you."),
    ("StickTogether", "Restez groupés", "dégâts +15 % près d'un allié (6 blocs), -15 % loin de tous.",
     "Stick Together", "+15% damage near an ally (6 blocks), -15% away from everyone."),
    ("FluxBomb", "Bombe de flux", "un joueur au hasard pulse quatre fois : écartez-vous de lui.",
     "Flux Bomb", "a random player pulses four times: stay away from them."),
    ("Vengeance", "Vengeance", "à la mort d'un ennemi, ses alliés proches frappent plus fort.",
     "Vengeance", "when an enemy dies, its nearby allies hit harder."),
    ("SlipperySlope", "Pente glissante", "les coups ennemis vous projettent loin.",
     "Slippery Slope", "enemy hits knock you far away."),
    ("Birds", "Nuée", "des corbeaux fondent sur le groupe en combat.",
     "Birds", "crows swoop on the group during fights."),
]


def icon(path, color, glyph):
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    d.ellipse((6, 6, 121, 121), fill=(24, 18, 36, 255), outline=c, width=6)
    if glyph == "vengeance":
        d.polygon(((64, 22), (80, 58), (64, 50), (48, 58)), fill=c)
        d.polygon(((40, 64), (88, 64), (64, 108)), fill=c)
    elif glyph == "flux":
        for r in (16, 30, 44):
            d.ellipse((64 - r, 64 - r, 64 + r, 64 + r), outline=c, width=6)
    elif glyph == "together":
        for x in (42, 86):
            d.ellipse((x - 14, 34, x + 14, 62), fill=c)
            d.pieslice((x - 22, 64, x + 22, 108), 180, 360, fill=c)
    elif glyph == "alone":
        d.ellipse((50, 30, 78, 58), fill=c)
        d.pieslice((42, 62, 86, 106), 180, 360, fill=c)
        d.line((24, 104, 104, 24), fill=c, width=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def effects():
    return {
        "Nakasar_Fractal_Vengeance": {
            "$Comment": "Instabilité Vengeance : un ennemi des fractales dont un allié vient de mourir à moins de 10 "
                        "blocs ; ses coups font 25 % de dégâts en plus (Java, Instabilities.filter). Teinte rouge.",
            "Name": f"{LANG}.effects.Nakasar_Fractal_Vengeance",
            "StatusEffectIcon": f"{STATUS_ICONS}/Vengeance.png",
            "ApplicationEffects": {"EntityTopTint": "#ff5a3a", "EntityBottomTint": "#5a0a00"},
            "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 12,
        },
        "Nakasar_Fractal_Flux_Bomb": {
            "$Comment": "Instabilité Bombe de flux : le joueur marqué pulse quatre fois (InstabilitySystem).",
            "Name": f"{LANG}.effects.Nakasar_Fractal_Flux_Bomb",
            "Debuff": True,
            "StatusEffectIcon": f"{STATUS_ICONS}/Flux_Bomb.png",
            "ApplicationEffects": {"EntityTopTint": "#b07aff"},
            "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 5,
        },
        "Nakasar_Fractal_Together": {
            "$Comment": "Instabilité Restez groupés : un allié est à moins de 6 blocs, dégâts infligés +15 % (Java).",
            "Name": f"{LANG}.effects.Nakasar_Fractal_Together",
            "StatusEffectIcon": f"{STATUS_ICONS}/Together.png",
            "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 1.5,
        },
        "Nakasar_Fractal_Alone": {
            "$Comment": "Instabilité Restez groupés : aucun allié à moins de 6 blocs, dégâts infligés -15 % (Java).",
            "Name": f"{LANG}.effects.Nakasar_Fractal_Alone",
            "Debuff": True,
            "StatusEffectIcon": f"{STATUS_ICONS}/Alone.png",
            "OverlapBehavior": "Overwrite", "Infinite": False, "Duration": 1.5,
        },
    }


def cause():
    return {"$Comment": "Dégâts des instabilités (Dernier rire, Malaise social, Bombe de flux) et des charges : une "
                        "part des PV max, que l'armure ne réduit pas.",
            "BypassResistances": True, "DurabilityLoss": False, "StaminaLoss": False, "DamageTextColor": "#d090ff"}


S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Toxic_Puddle": ("Flaque de la Traînée toxique : nappe rouge sombre et bulles vertes au sol.",
                                     [("Pool", S("#c03030", "#401010", 10, (0.05, 0.2), (-5, 5), 1.2, 0.05,
                                                 life=(0.9, 1.2), size=(0.5, 0.8), blend="BlendLinear"), 0.05),
                                      ("Bubbles", S("#9aff6a", "#2a5a10", 5, (0.3, 0.6), (70, 90), 1.0, 0.1,
                                                    life=(0.6, 1.0)), 0.1)]),
    "Nakasar_Fractal_Flux_Mark": ("Bombe de flux : marque violette au-dessus du joueur.",
                                  [("Mark", S("#ffffff", "#9a5aff", 8, (0.1, 0.3), (-90, 90), 0.3, 0.3,
                                              life=(0.8, 1.0), size=(0.3, 0.5)), 0.0)]),
    "Nakasar_Fractal_Flux_Pulse": ("Impulsion de la bombe de flux : anneau violet qui s'étend.",
                                   [("Ring", S("#e0c8ff", "#5a1aff", 24, (3.0, 4.0), (-5, 5), 0.4, 0.3,
                                               life=(0.4, 0.6)), 0.3)]),
    "Nakasar_Fractal_Last_Laugh": ("Dernier rire : étincelles orange qui grésillent sur l'ennemi qui va exploser.",
                                   [("Fuse", S("#fff0a0", "#ff5a1a", 12, (0.5, 1.2), (30, 90), 0.6, 0.8,
                                               life=(0.4, 0.8)), 0.2)]),
}


def particle_files():
    out = {}
    for sid, (comment, spawners) in PARTICLE_SYSTEMS.items():
        out[f"{sid}.particlesystem"] = {
            "$Comment": f"{comment} Généré par tools/{GENERATOR}.",
            "Spawners": [{"SpawnerId": f"{sid}_{suffix}", "PositionOffset": {"Y": y}} for suffix, _, y in spawners],
            "CullDistance": 64,
        }
        for suffix, doc, _ in spawners:
            out[f"{sid}_{suffix}.particlespawner"] = doc
    return out


def crow_model():
    return {"$Comment": "Corbeau de la Nuée (provisoire) : la chauve-souris vanilla, en petit. Modèle de corbeau à "
                        "vérifier dans Assets.zip (le rôle vanilla Crow existe).",
            "Parent": "Bat", "MinScale": 0.9, "MaxScale": 1.0}


def crow_interactions():
    return {"Nakasar_Fractal_Crow_Peck": {
        "$Comment": "Corbeau de la Nuée : coup de bec (6 dégâts).",
        "Type": "Serial", "Interactions": [fr.swing("Coup de bec.", None, None, 0.3, 6, end=2.0, length=70, yaw=35,
                                                     sound="SFX_Unarmed_Swing")]}}


def crow_role():
    return fr.role(
        CROW,
        "Corbeau de la Nuée (instabilité Birds) : posé par le Java près d'un joueur en combat, vole sur lui et le "
        "pique. Jamais sauvegardé.",
        CROW, f"{LANG}.npc.Crow.name", 30,
        [fr.melee("Root_Nakasar_Fractal_NPC_Crow_Peck", 2.2, (0.8, 1.2)), fr.chase(40, speed=1.0, stop=1.2, pathfinder=False)],
        [{"Type": "Fly", "MaxHorizontalSpeed": 7, "MaxClimbSpeed": 3, "MaxSinkSpeed": 3, "Acceleration": 3,
          "Deceleration": 3, "Gravity": 1, "MinHeightOverGround": 1, "MaxHeightOverGround": 6}],
        GENERATOR, sight=30, leash=40, home=False, KnockbackScale=0.5, DeathAnimationTime=0.8)


def lang():
    fr_, en = {}, {}

    def put(key, f, e):
        fr_[key], en[key] = f, e

    for iid, nf, df, ne, de in INSTABILITIES:
        put(f"{iid}.name", nf, ne)
        put(f"{iid}.description", df, de)
    put("none", "Aucune instabilité.", "No instability.")
    put("arrival", "Instabilités de cette fractale :", "Instabilities of this fractal:")
    put("today", "Instabilités du jour :", "Today's instabilities:")
    put("current", "{fractal}, niveau {level}, instabilités :", "{fractal}, level {level}, instabilities:")
    put("forecast", "Instabilités du jour au niveau {level} pour {size} joueur(s) :",
        "Today's instabilities at level {level} for {size} player(s):")
    put("nowhere", "Les instabilités se lisent dans une fractale ou dans l'Observatoire.",
        "Instabilities can be checked in a fractal or in the Observatory.")
    put("flux.marked", "Bombe de flux : vous allez pulser, écartez-vous du groupe !",
        "Flux bomb: you are about to pulse, move away from the group!")
    put("command.desc", "Les instabilités du jour (une par rang au-delà d'Initié).",
        "Today's instabilities (one per rank above Initiate).")
    put("effects.Nakasar_Fractal_Vengeance", "Vengeance", "Vengeance")
    put("effects.Nakasar_Fractal_Flux_Bomb", "Bombe de flux", "Flux bomb")
    put("effects.Nakasar_Fractal_Together", "Ensemble", "Together")
    put("effects.Nakasar_Fractal_Alone", "Isolé", "Alone")
    put("npc.Crow.name", "Corbeau de la Nuée", "Swarm Crow")
    return fr_, en


def main():
    for name, doc in effects().items():
        fr.write_json(EFFECTS / f"{name}.json", doc)
    icon(COMMON / STATUS_ICONS / "Vengeance.png", (255, 90, 58), "vengeance")
    icon(COMMON / STATUS_ICONS / "Flux_Bomb.png", (176, 122, 255), "flux")
    icon(COMMON / STATUS_ICONS / "Together.png", (120, 220, 140), "together")
    icon(COMMON / STATUS_ICONS / "Alone.png", (230, 150, 90), "alone")
    fr.write_json(SERVER / "Entity/Damage" / f"{CAUSE}.json", cause())
    for name, doc in particle_files().items():
        fr.write_json(PARTICLES / name, doc)
    for name, doc in crow_interactions().items():
        fr.write_json(go.INTERACTIONS / "Instabilities" / f"{name}.json", doc)
    fr.write_json(gc.ROOTS / "Root_Nakasar_Fractal_NPC_Crow_Peck.json", fr.melee_tag("Nakasar_Fractal_Crow_Peck"))
    fr.write_json(gc.MODELS / f"{CROW}.json", crow_model())
    fr.write_json(gc.ROLES / f"{CROW}.json", crow_role())
    group = SERVER / "NPC/Groups" / f"{fr.FOES}.json"
    doc = json.loads(group.read_text(encoding="utf-8"))
    doc["IncludeRoles"] = sorted(set(doc.get("IncludeRoles", [])) | {CROW})
    fr.write_json(group, doc)
    fr_, en = lang()
    go.write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr_)
    go.write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    print(f"Instabilités : {len(INSTABILITIES)} instabilités, {len(effects())} effets, {len(PARTICLE_SYSTEMS)} particules, "
          f"{len(fr_)} entrées de langue")


if __name__ == "__main__":
    main()
