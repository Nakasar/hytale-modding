#!/usr/bin/env python3
"""Génère le modèle animé du rouage enchanté, serviteur de l'armure enchantée.

    python3 mods/nakasar-vampires/tools/generate_gear_model.py [--preview DOSSIER]

- Common/NPC/Nakasar/Enchanted_Gear/ : deux roues dentées de bronze qui flottent à hauteur de poitrine, l'une
  devant l'autre et tournant en sens contraires, autour d'un cœur runique bleu qui luit (fullbright). Elles
  sortent du sol en tournoyant, tremblent quand on les frappe, puis retombent et se couchent à leur mort.
- Server/Models/Nakasar/Nakasar_Enchanted_Gear.json : modèle (hitbox, lumière, particules de soin, AnimationSets).

Mêmes outils et même repère que tools/generate_pumpkin_models.py (64 unités = 1 bloc, origine au sol, face avant
vers +Z, 60 images par seconde). --preview DOSSIER écrit des rendus PNG.
"""
import math
import sys
from pathlib import Path

import generate_pumpkin_models as gp
from generate_pumpkin_models import Anim, Box, Joint

BRONZE = (176, 120, 58)
BRONZE_DARK = (98, 62, 30)
BRONZE_LIGHT = (232, 184, 104)
IRON = (92, 96, 108)
IRON_DARK = (46, 48, 58)
IRON_LIGHT = (150, 156, 170)
RUNE_HOT = (220, 246, 255)
RUNE = (90, 170, 255)

HUB_Y = 78          # centre des roues : un peu plus d'un bloc au-dessus du sol
TEETH_A = 10
TEETH_B = 8


def cog(prefix, radius, teeth, thickness, z, metal, tooth_len=7):
    """Roue dentée dans le plan XY : jante (segments tournés), dents, rayons et moyeu, autour de son nœud."""
    base, dark, light = metal
    paint = gp.p_round(base, dark, light, amp=0.05)
    parts = []
    seg = 2 * math.pi * radius / teeth
    for k in range(teeth):
        a = 360.0 * k / teeth
        r = math.radians(a)
        mid = 360.0 * (k + 0.5) / teeth
        rm = math.radians(mid)
        # segment de jante entre deux dents, tangent au cercle
        parts.append(Box(f"{prefix}_Rim{k}", (math.cos(rm) * radius, math.sin(rm) * radius, 0),
                         (seg + 1.5, 6, thickness), paint, rot=(0, 0, mid + 90)))
        # dent, dans l'axe du rayon
        parts.append(Box(f"{prefix}_Tooth{k}", (math.cos(r) * (radius + tooth_len / 2 + 1.5), math.sin(r) * (radius + tooth_len / 2 + 1.5), 0),
                         (5, tooth_len, thickness - 1), gp.p_round(light, base, light, amp=0.04), rot=(0, 0, a - 90)))
    for k in range(4):
        a = 45.0 * (2 * k + 1) if teeth % 4 else 90.0 * k
        r = math.radians(a)
        parts.append(Box(f"{prefix}_Spoke{k}", (math.cos(r) * radius / 2, math.sin(r) * radius / 2, 0),
                         (3, radius - 2, thickness - 2), gp.p_round(dark, dark, base), rot=(0, 0, a - 90)))
    parts.append(Box(f"{prefix}_Hub", (0, 0, 0), (10, 10, thickness + 1), gp.p_round(base, dark, light)))
    return Joint(prefix, (0, 0, z), parts)


def gear_model():
    core = Joint("Core", (0, 0, 0), [
        Box("Rune_Core", (0, 0, 0), (7, 7, 15), gp.p_glow(RUNE_HOT, RUNE), shading="fullbright"),
        Box("Rune_Halo", (0, 0, 0), (11, 3, 13), gp.p_glow(RUNE, (40, 90, 200)), shading="fullbright"),
        Box("Rune_Halo_V", (0, 0, 0), (3, 11, 13), gp.p_glow(RUNE, (40, 90, 200)), shading="fullbright"),
    ])
    front = cog("Cog_A", 22, TEETH_A, 5, 4, (BRONZE, BRONZE_DARK, BRONZE_LIGHT))
    back = cog("Cog_B", 14, TEETH_B, 4, -4, (IRON, IRON_DARK, IRON_LIGHT), tooth_len=6)
    back.pos = (9, 8, -4)
    axle = Box("Axle", (0, 0, 0), (4, 4, 14), gp.p_round(IRON, IRON_DARK, IRON_LIGHT))
    floater = Joint("Float", (0, HUB_Y, 0), [front, back, core, axle])
    return Joint("Root", (0, 0, 0), [floater])


JOINTS = ["Root", "Float", "Cog_A", "Cog_B", "Core"]


def spin(t, speed=180.0):
    """Roues qui tournent en sens contraires (degrés par seconde) ; la petite tourne deux fois plus vite."""
    return {"Cog_A": ((0, 0, -speed * t), (0, 0, 0)), "Cog_B": ((0, 0, speed * 2 * t), (0, 0, 0))}


def bob(t):
    return math.sin(t * math.pi) * 4


def gear_anims():
    def idle(t):
        p = spin(t)
        p["Float"] = ((math.sin(t * math.pi) * 6, 0, 0), (0, bob(t), 0))
        p["Core"] = ((0, 0, 0), (0, 0, 0))
        return p

    def spawn(t):
        k = gp.smooth(t / 0.7)
        p = spin(t, 400.0)
        p["Float"] = ((0, 360 * (1 - k), 0), (0, -HUB_Y * (1 - k), 0))
        return p

    def hurt(t):
        p = spin(t)
        shake = math.sin(t * 60) * 7 * (1 - t / 0.3)
        p["Float"] = ((shake, 0, shake * 0.6), (0, 0, 0))
        return p

    def death(t):
        k = gp.smooth(t / 0.9)
        p = spin(t, 180.0 * (1 - k))
        p["Float"] = ((90 * k, 0, 25 * k), (0, -(HUB_Y - 8) * k, 0))
        return p

    # Idle : 2 s, les roues font un et deux tours entiers : la boucle ne saute pas.
    return [Anim("Idle", 2.0, idle, loop=True), Anim("Spawn", 0.8, spawn, hold=True), Anim("Hurt", 0.3, hurt),
            Anim("Death", 1.0, death, hold=True)]


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    view = {"size": 300, "scale": 3.0, "center": (0, HUB_Y, 0)}
    gp.build("Enchanted_Gear", gear_model(), JOINTS, gear_anims(), 57, 256, {
        "$Comment": "Rouage enchanté, serviteur de l'armure enchantée, généré par tools/generate_gear_model.py : deux roues dentées de bronze et de fer qui tournent en flottant autour d'un cœur runique bleu. Tant qu'il vit, il soigne l'armure (SummonMinionsInteraction, HealSummonerPerSecond) : particules de soin.",
        "EyeHeight": 1.2,
        "HitBox": {"Max": {"X": 0.45, "Y": 1.75, "Z": 0.3}, "Min": {"X": -0.45, "Y": 0.7, "Z": -0.3}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#5aaaff", "Radius": 4},
        "Particles": [{"SystemId": "Elite_Heal", "TargetNodeName": "Core", "Scale": 0.6}],
    }, [], preview, [
        ("face", None, 0, dict(view, yaw=0, pitch=0)),
        ("3/4", "Idle", 0.5, view),
        ("profil", "Idle", 1.0, dict(view, yaw=80, pitch=10)),
        ("mort", "Death", 1.0, dict(view, center=(0, 30, 0))),
    ])
    # Pas d'attaque, donc pas de jeu d'animations d'objet.
    (gp.SERVER / "Item" / "Animations" / "Nakasar" / "Nakasar_Enchanted_Gear.json").unlink()


if __name__ == "__main__":
    main()
