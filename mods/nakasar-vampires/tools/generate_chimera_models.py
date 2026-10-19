#!/usr/bin/env python3
"""Génère les modèles animés de la Chimère du laboratoire (mini-boss de la Tour de l'Alchimiste) et des étagères de
réactifs qui la nourrissent.

    python3 mods/nakasar-vampires/tools/generate_chimera_models.py [--preview DOSSIER]

- Common/NPC/Nakasar/Lab_Chimera/ : grand quadrupède rapiécé de 2,2 blocs au garrot. Corps de bête aux pièces de peau
  cousues (fourrure brune, peau grise glabre, écailles vertes), la patte avant droite est un bras de golem de plomb
  (riveté, poing massif), une queue de serpent se termine par une tête de serpent, trois tubes de verre plantés dans
  le dos luisent d'un liquide vert. Yeux dépareillés (un vert, un ambre), une corne de bélier d'un seul côté.
- Common/NPC/Nakasar/Chimera_Reagent_Shelf/ : étagère de bois cerclée de fer, chargée de bocaux de réactifs qui
  luisent ; elle tremble au repos et s'effondre quand on la détruit.
- Animations de la Chimère : repos, marche, course, blessure, mort, et pour ses attaques « Bite » (morsure), « Slam »
  (le poing de golem s'abat), « Tail » (elle tourne sur elle-même, la queue fauche), jouées par ses interactions
  (Effects.ItemAnimationId) via Server/Item/Animations/Nakasar/Nakasar_Lab_Chimera.json.
- Server/Models/Nakasar/Nakasar_Lab_Chimera.json et Nakasar_Chimera_Reagent_Shelf.json : modèles (hitbox, lumière).

Même repère et même écriture que tools/generate_pumpkin_models.py (64 unités = 1 bloc, face avant vers +Z ; une
rotation négative autour de X lève l'avant).
--preview DOSSIER écrit des rendus PNG (repos et images clés) pour vérifier les modèles.
"""
import math
import sys
from pathlib import Path

from PIL import Image

import generate_pumpkin_models as gpm
from generate_pumpkin_models import Anim, Box, Joint, keys, mix, p_glow, p_round, shade, soft_noise, solid

FUR = (110, 78, 54)
FUR_DARK = (64, 42, 30)
FUR_LIGHT = (156, 118, 84)
SKIN = (150, 140, 136)
SKIN_DARK = (96, 86, 86)
SKIN_LIGHT = (196, 186, 178)
SCALE = (70, 120, 70)
SCALE_DARK = (34, 70, 40)
SCALE_LIGHT = (130, 176, 100)
LEAD = (88, 90, 104)
LEAD_DARK = (46, 48, 58)
LEAD_LIGHT = (140, 144, 160)
STITCH = (34, 20, 18)
BONE = (230, 220, 196)
GOLD = (210, 166, 70)
GOLD_DARK = (128, 92, 30)
GOLD_LIGHT = (255, 224, 130)
LIQUID = (150, 255, 120)
LIQUID_DEEP = (40, 190, 70)
WOOD = (120, 84, 52)
WOOD_DARK = (70, 46, 28)
WOOD_LIGHT = (160, 120, 80)
IRON = (70, 72, 82)
IRON_DARK = (36, 38, 46)
IRON_LIGHT = (124, 128, 140)

TORSO_Y = 92           # centre du tronc au-dessus du sol
TAIL_SEGMENTS = 6


# --- peintres -----------------------------------------------------------------------------------

def p_patch(base, dark, light, seam=True, scales=False):
    """Pièce de peau cousue : dégradé arrondi, points de couture sombres en tirets le long des bords des grandes faces,
    écailles en losanges si `scales`."""
    under = p_round(base, dark, light, amp=0.07)

    def paint(rng, w, h, face):
        img = under(rng, w, h, face)
        px = img.load()
        if scales:
            for y in range(h):
                for x in range(w):
                    if (x + (y // 3) * 2) % 6 == 0 or y % 3 == 0 and (x // 3) % 2 == 0:
                        px[x, y] = shade(px[x, y][:3], 0.8) + (255,)
        if seam and w >= 8 and h >= 8:
            for x in range(1, w - 1):
                if x % 3 != 2:
                    for y in (1, h - 2):
                        px[x, y] = STITCH + (255,)
            for y in range(1, h - 1):
                if y % 3 != 2:
                    for x in (1, w - 2):
                        px[x, y] = STITCH + (255,)
        return img

    return paint


def p_stitch_line(base, dark, light, axis="x"):
    """Peau traversée d'une cicatrice cousue au milieu (en long si axis = x, en travers sinon)."""
    under = p_round(base, dark, light, amp=0.06)

    def paint(rng, w, h, face):
        img = under(rng, w, h, face)
        px = img.load()
        if face in ("front", "back", "left", "right", "top"):
            if axis == "x" and h >= 6:
                y0 = h // 2
                for x in range(w):
                    px[x, y0] = shade(dark, 0.7) + (255,)
                    if x % 3 == 0:
                        for dy in (-1, 1):
                            if 0 <= y0 + dy < h:
                                px[x, y0 + dy] = STITCH + (255,)
            elif w >= 6:
                x0 = w // 2
                for y in range(h):
                    px[x0, y] = shade(dark, 0.7) + (255,)
                    if y % 3 == 0:
                        for dx in (-1, 1):
                            if 0 <= x0 + dx < w:
                                px[x0 + dx, y] = STITCH + (255,)
        return img

    return paint


def p_rivets(base, dark, light):
    """Plomb du golem : dégradé arrondi semé de rivets clairs."""
    under = p_round(base, dark, light, amp=0.05)

    def paint(rng, w, h, face):
        img = under(rng, w, h, face)
        px = img.load()
        for y in range(2, h - 2, 6):
            for x in range(2, w - 2, 6):
                px[x, y] = light + (255,)
                if x + 1 < w:
                    px[x + 1, y] = shade(light, 0.8) + (255,)
        return img

    return paint


def p_planks():
    """Planches de l'étagère : veinures dans la longueur."""

    def paint(rng, w, h, face):
        n = soft_noise(rng, w, h, amp=0.08)

        def c(x, y):
            col = mix(WOOD, WOOD_DARK, 0.5 if (y % 5 == 0) else abs(math.sin(x * 0.7 + y * 0.1)) * 0.25)
            return shade(col, n[y][x])

        return solid(Image.new("RGBA", (w, h)), c)

    return paint


def flat(color):
    return lambda rng, w, h, face: solid(Image.new("RGBA", (w, h)), lambda x, y: color)


# --- la Chimère -------------------------------------------------------------------------------

def leg(name, pos, golem=False, back=False):
    """Patte en deux segments (épaule puis genou) ; la patte de golem est plus grosse, en plomb riveté, avec un poing."""
    if golem:
        paint = p_rivets(LEAD, LEAD_DARK, LEAD_LIGHT)
        upper = [Box(f"{name}_Upper", (0, -20, 0), (30, 44, 30), paint),
                 Box(f"{name}_Pauldron", (2, 0, 0), (36, 14, 36), paint),
                 Box(f"{name}_Seam", (-1, 8, 0), (32, 4, 32), flat(STITCH))]
        lower = [Box(f"{name}_Lower", (0, -12, 0), (28, 30, 28), paint),
                 Box(f"{name}_Fist", (0, -27, 4), (36, 14, 38), paint),
                 *[Box(f"{name}_Knuckle{k}", (-12 + 8 * k, -24, 22), (6, 8, 4), p_round(LEAD_LIGHT, LEAD, (190, 194, 210)))
                   for k in range(4)]]
    else:
        fur = p_patch(FUR, FUR_DARK, FUR_LIGHT, seam=False)
        skin = p_stitch_line(SKIN, SKIN_DARK, SKIN_LIGHT, axis="y")
        upper = [Box(f"{name}_Upper", (0, -20, 0), (22, 44, 26), skin if back else fur)]
        lower = [Box(f"{name}_Lower", (0, -14, 0), (18, 30, 20), fur if back else skin),
                 Box(f"{name}_Paw", (0, -29, 4), (24, 10, 30), p_round(FUR_DARK, (36, 24, 18), FUR)),
                 *[Box(f"{name}_Claw{k}", (-7 + 7 * k, -31, 20), (3, 4, 6), flat(BONE)) for k in range(3)]]
    knee = Joint(f"{name}2", (0, -38, 0), lower)
    return Joint(name, pos, upper + [knee])


def tail():
    """Queue de serpent : segments de plus en plus fins, la tête du serpent au bout, gueule tournée vers l'arrière."""
    child = None
    sizes = [16, 14, 12, 11, 10, 9]
    paint = p_patch(SCALE, SCALE_DARK, SCALE_LIGHT, seam=False, scales=True)
    for i in range(TAIL_SEGMENTS, 0, -1):
        s = sizes[i - 1]
        parts = [Box(f"Tail{i}_Seg", (0, 0, -12), (s, s, 26), paint)]
        if i == TAIL_SEGMENTS:
            parts += [
                Box("Snake_Head", (0, 1, -30), (16, 11, 20), paint),
                Box("Snake_Jaw", (0, -5, -28), (12, 3, 16), p_round(SCALE_LIGHT, SCALE, (190, 220, 150))),
                Box("Snake_Eye_L", (-8.3, 4, -32), (1, 3, 4), p_glow((255, 250, 140), (230, 160, 20)), shading="fullbright"),
                Box("Snake_Eye_R", (8.3, 4, -32), (1, 3, 4), p_glow((255, 250, 140), (230, 160, 20)), shading="fullbright"),
                Box("Snake_Fang_L", (-3, -3, -39), (1.5, 4, 1.5), flat(BONE)),
                Box("Snake_Fang_R", (3, -3, -39), (1.5, 4, 1.5), flat(BONE)),
            ]
        if child:
            parts.append(child)
        child = Joint(f"Tail{i}", (0, 0, -22) if i > 1 else (0, 10, -76), parts, rot=(-12, 0, 0) if i == 1 else (4, 0, 0))
    return child


def tube(k, x, z, height):
    """Tube de verre planté dans le dos : bague d'or à la base, liquide vert lumineux, bouchon d'or."""
    gold = p_round(GOLD, GOLD_DARK, GOLD_LIGHT)
    return [
        Box(f"Tube{k}_Base", (x, 34, z), (16, 5, 16), gold),
        Box(f"Tube{k}_Liquid", (x, 34 + height / 2, z), (10, height, 10), p_glow(LIQUID, LIQUID_DEEP), shading="fullbright"),
        Box(f"Tube{k}_Ring", (x, 34 + height * 0.6, z), (12, 3, 12), gold),
        Box(f"Tube{k}_Cap", (x, 34 + height + 2, z), (13, 5, 13), gold),
        Box(f"Tube{k}_Spout", (x, 34 + height + 6, z), (4, 4, 4), p_glow(LIQUID, LIQUID_DEEP), shading="fullbright"),
    ]


def chimera_model():
    fur = p_patch(FUR, FUR_DARK, FUR_LIGHT)
    skin = p_patch(SKIN, SKIN_DARK, SKIN_LIGHT)
    scales = p_patch(SCALE, SCALE_DARK, SCALE_LIGHT, scales=True)
    eye_green = p_glow((220, 255, 200), (60, 220, 90))
    eye_amber = p_glow((255, 240, 160), (240, 140, 20))
    jaw = Joint("Jaw", (0, -14, 34), [
        Box("Jaw_Bone", (0, -4, 18), (34, 9, 40), skin),
        *[Box(f"Tooth_Low{k}", (-13 + 6.5 * k, 2, 34), (3, 5, 3), flat(BONE)) for k in range(5)],
    ])
    head = Joint("Head", (0, 18, 72), [
        Box("Neck", (0, -6, -6), (42, 40, 30), fur),
        Box("Skull", (0, 2, 18), (54, 44, 40), fur),
        Box("Snout", (0, -6, 46), (38, 24, 26), skin),
        Box("Nose", (0, 0, 60), (14, 8, 3), flat((40, 26, 26))),
        *[Box(f"Tooth_Up{k}", (-13 + 6.5 * k, -19, 52), (3, 6, 3), flat(BONE)) for k in range(5)],
        Box("Fang_L", (-15, -21, 50), (4, 10, 4), flat(BONE)),
        Box("Fang_R", (15, -21, 50), (4, 10, 4), flat(BONE)),
        Box("Eye_L", (-27.3, 8, 30), (1, 7, 8), eye_green, shading="fullbright"),
        Box("Eye_R", (27.3, 8, 30), (1, 7, 8), eye_amber, shading="fullbright"),
        Box("Brow_Scar", (-14, 22, 24), (22, 4, 20), p_stitch_line(SKIN, SKIN_DARK, SKIN_LIGHT)),
        Box("Horn_Base", (22, 22, 12), (12, 12, 14), p_round(BONE, (170, 150, 120), (250, 244, 226))),
        Box("Horn_Mid", (30, 26, 2), (10, 10, 14), p_round(BONE, (170, 150, 120), (250, 244, 226)), rot=(0, 30, 20)),
        Box("Horn_Tip", (34, 20, -6), (7, 12, 7), p_round(BONE, (170, 150, 120), (250, 244, 226)), rot=(25, 0, 30)),
        Box("Ear_L", (-22, 26, 8), (8, 14, 6), fur, rot=(0, 0, 25)),
        jaw,
    ])
    torso = Joint("Torso", (0, TORSO_Y, 0), [
        Box("Belly", (0, -4, -10), (72, 58, 128), skin),
        Box("Chest", (0, 2, 44), (82, 70, 52), fur),
        Box("Hump", (0, 30, 20), (70, 14, 70), fur),
        Box("Haunch", (0, 4, -56), (76, 62, 40), scales),
        Box("Patch_Side_L", (-36.6, 0, -6), (1, 40, 54), scales),
        Box("Patch_Side_R", (36.6, 6, 10), (1, 34, 46), fur),
        Box("Scar_Spine", (0, 31.6, -24), (14, 1, 60), p_stitch_line(SKIN_DARK, STITCH, SKIN, axis="y")),
        *[Box(f"Strap{k}", (0, 0, z), (76, 62, 4), p_round(IRON, IRON_DARK, IRON_LIGHT)) for k, z in enumerate((-30, 16))],
        *tube(0, -12, -40, 34), *tube(1, 12, -10, 42), *tube(2, -8, 22, 30),
        head,
        leg("Leg_FL", (-30, -20, 50)),
        leg("Leg_FR", (34, -18, 50), golem=True),
        leg("Leg_BL", (-30, -20, -58), back=True),
        leg("Leg_BR", (30, -20, -58), back=True),
        tail(),
    ])
    return Joint("Body", (0, 0, 0), [torso])


CHIMERA_JOINTS = (["Body", "Torso", "Head", "Jaw"]
                  + [f"Leg_{p}{s}" for p in ("FL", "FR", "BL", "BR") for s in ("", "2")]
                  + [f"Tail{i}" for i in range(1, TAIL_SEGMENTS + 1)])


def chimera_anims():
    def tail_sway(t, speed=2.0, amp=10, lift=0):
        return {f"Tail{i}": ((lift if i == 1 else 0, amp * math.sin(t * speed - 0.6 * i) * (0.6 + 0.1 * i), 0), (0, 0, 0))
                for i in range(1, TAIL_SEGMENTS + 1)}

    def gait(t, period, swing, lift, bounce):
        """Marche en diagonale : avant gauche et arrière droite ensemble, puis les deux autres."""
        phase = 2 * math.pi * t / period
        pose = {}
        for name, off in (("Leg_FL", 0), ("Leg_BR", 0), ("Leg_FR", math.pi), ("Leg_BL", math.pi)):
            s = math.sin(phase + off)
            pose[name] = ((-swing * s, 0, 0), (0, 0, 0))
            pose[name + "2"] = ((lift * max(0.0, math.cos(phase + off)), 0, 0), (0, 0, 0))
        pose["Torso"] = ((2 * math.sin(2 * phase), 2 * math.sin(phase), 0), (0, bounce * abs(math.sin(phase)), 0))
        pose["Head"] = ((-3 * math.sin(2 * phase), 0, 0), (0, 0, 0))
        return pose

    def idle(t):
        u = t / 2.4
        b = math.sin(2 * math.pi * u)
        return {"Torso": ((0, 0, 0), (0, 1.5 * b, 0)),
                "Head": ((3 * math.sin(2 * math.pi * u + 1), 6 * math.sin(math.pi * u), 0), (0, 0, 0)),
                "Jaw": ((8 + 4 * math.sin(4 * math.pi * u), 0, 0), (0, 0, 0)),
                **tail_sway(2 * math.pi * u, 1.0, 14)}

    def walk(t):
        return {**gait(t, 1.0, 24, 30, 2), **tail_sway(t * 2 * math.pi, 1.0, 12),
                "Jaw": ((6, 0, 0), (0, 0, 0))}

    def run(t):
        pose = gait(t, 0.6, 36, 45, 5)
        rot, off = pose["Torso"]
        pose["Torso"] = ((rot[0] - 4, rot[1], rot[2]), off)
        return {**pose, **tail_sway(t * 2 * math.pi / 0.6, 1.0, 18, lift=-10), "Jaw": ((14, 0, 0), (0, 0, 0))}

    def hurt(t):
        k = keys(t, [(0, 0), (0.08, 1), (0.35, 0)])
        return {"Torso": ((6 * k, 0, -5 * k), (0, -3 * k, -6 * k)), "Head": ((-15 * k, 10 * k, 0), (0, 0, 0)),
                "Jaw": ((25 * k, 0, 0), (0, 0, 0)), **tail_sway(t * 30, 1.0, 20 * k)}

    def death(t):
        # Elle se cabre, hurle, puis s'effondre sur le flanc gauche, les tubes vers la salle.
        rear = keys(t, [(0, 0), (0.4, -18), (0.8, 4), (1.8, 0)])
        roll = keys(t, [(0, 0), (0.6, 0), (1.4, -82), (1.8, -86)])
        drop = keys(t, [(0, 0), (0.6, 4), (1.4, -50), (1.8, -52)])
        legs = keys(t, [(0, 0), (0.8, 0), (1.5, 1)])
        return {"Torso": ((rear, 0, roll), (keys(t, [(0, 0), (1.4, -14)]), drop, 0)),
                "Head": ((keys(t, [(0, 0), (0.4, -30), (1.2, 10), (1.8, 24)]), 0, keys(t, [(0, 0), (1.4, 20)])), (0, 0, 0)),
                "Jaw": ((keys(t, [(0, 0), (0.4, 40), (1.0, 10), (1.8, 18)]), 0, 0), (0, 0, 0)),
                **{n: ((-30 * legs, 0, 0), (0, 0, 0)) for n in ("Leg_FL", "Leg_FR")},
                **{n: ((30 * legs, 0, 0), (0, 0, 0)) for n in ("Leg_BL", "Leg_BR")},
                **{n + "2": ((40 * legs, 0, 0), (0, 0, 0)) for n in ("Leg_FL", "Leg_FR", "Leg_BL", "Leg_BR")},
                **tail_sway(t * 4, 1.0, 20 * (1 - legs))}

    def bite(t):
        # Morsure : elle ramasse son élan (0 à 0,3 s), se jette gueule ouverte et claque des mâchoires à 0,45 s.
        lunge = keys(t, [(0, 0), (0.3, -10), (0.45, 22), (0.8, 0)])
        jaw = keys(t, [(0, 8), (0.3, 50), (0.42, 52), (0.47, 0), (0.8, 8)])
        head = keys(t, [(0, 0), (0.3, -20), (0.45, 12), (0.8, 0)])
        return {"Torso": ((keys(t, [(0, 0), (0.3, -4), (0.45, 6), (0.8, 0)]), 0, 0), (0, 0, lunge)),
                "Head": ((head, 0, 0), (0, 0, lunge * 0.4)), "Jaw": ((jaw, 0, 0), (0, 0, 0)),
                "Leg_FL": ((keys(t, [(0, 0), (0.3, 15), (0.45, -25), (0.8, 0)]), 0, 0), (0, 0, 0)),
                "Leg_FR": ((keys(t, [(0, 0), (0.3, 15), (0.45, -25), (0.8, 0)]), 0, 0), (0, 0, 0)),
                **tail_sway(t * 8, 1.0, 14)}

    def slam(t):
        # Coup du poing de golem : elle se cabre (0 à 1,0 s), le poing levé haut, puis l'abat devant elle à 1,15 s.
        rear = keys(t, [(0, 0), (0.8, -24), (1.0, -26), (1.15, 6), (1.6, 0)])
        lift = keys(t, [(0, 0), (0.8, -95), (1.0, -100), (1.15, -10), (1.6, 0)])
        elbow = keys(t, [(0, 0), (0.8, 40), (1.0, 45), (1.15, 0)])
        return {"Torso": ((rear, 0, keys(t, [(0, 0), (0.8, 6), (1.15, -4), (1.6, 0)])),
                          (0, keys(t, [(0, 0), (0.8, 10), (1.15, -4), (1.6, 0)]), keys(t, [(0, 0), (1.15, 10), (1.6, 0)]))),
                "Leg_FR": ((lift, 0, keys(t, [(0, 0), (0.8, -10), (1.15, 0)])), (0, 0, 0)),
                "Leg_FR2": ((elbow, 0, 0), (0, 0, 0)),
                "Leg_FL": ((keys(t, [(0, 0), (0.8, -30), (1.15, 0)]), 0, 0), (0, 0, 0)),
                "Leg_BL": ((keys(t, [(0, 0), (0.8, 20), (1.15, 0)]), 0, 0), (0, 0, 0)),
                "Leg_BR": ((keys(t, [(0, 0), (0.8, 20), (1.15, 0)]), 0, 0), (0, 0, 0)),
                "Head": ((keys(t, [(0, 0), (0.8, -25), (1.15, 15), (1.6, 0)]), 0, 0), (0, 0, 0)),
                "Jaw": ((keys(t, [(0, 8), (0.9, 45), (1.15, 30), (1.6, 8)]), 0, 0), (0, 0, 0)),
                **tail_sway(t * 3, 1.0, 10, lift=keys(t, [(0, 0), (1.0, -25), (1.6, 0)]))}

    def tail_lash(t):
        # Fauchage de la queue : elle se ramasse, queue dressée (0 à 0,6 s), puis tourne sur elle-même (0,6 à 0,95 s).
        spin = keys(t, [(0, 0), (0.6, -20), (0.95, 360), (1.2, 360)])
        crouch = keys(t, [(0, 0), (0.6, -8), (0.95, 0)])
        return {"Body": ((0, spin, 0), (0, 0, 0)),
                "Torso": ((0, 0, 0), (0, crouch, 0)),
                **{f"Tail{i}": ((keys(t, [(0, 0), (0.6, -20 if i == 1 else -6), (0.8, 10), (1.2, 0)]),
                                 keys(t, [(0, 0), (0.6, 0), (0.75, 20), (0.95, 30), (1.2, 0)]) * (0.5 + 0.1 * i), 0), (0, 0, 0))
                   for i in range(1, TAIL_SEGMENTS + 1)},
                "Head": ((keys(t, [(0, 0), (0.6, 10), (1.2, 0)]), 0, 0), (0, 0, 0)),
                "Jaw": ((keys(t, [(0, 8), (0.6, 30), (1.2, 8)]), 0, 0), (0, 0, 0))}

    return [
        Anim("Idle", 2.4, idle, step=6, loop=True),
        Anim("Walk", 1.0, walk, step=3, loop=True),
        Anim("Run", 0.6, run, step=2, loop=True),
        Anim("Hurt", 0.35, hurt, step=3),
        Anim("Death", 1.8, death, step=4, hold=True),
        Anim("Bite", 0.8, bite, step=2),
        Anim("Slam", 1.6, slam, step=2),
        Anim("Tail", 1.2, tail_lash, step=2),
    ]


# --- étagère de réactifs ----------------------------------------------------------------------

def shelf_model():
    planks = p_planks()
    iron = p_round(IRON, IRON_DARK, IRON_LIGHT)
    jars = []
    colours = [((150, 255, 120), (40, 190, 70)), ((255, 240, 150), (220, 160, 30)), ((200, 220, 255), (110, 140, 220))]
    for row, y in enumerate((26, 62, 98)):
        for k, x in enumerate((-16, 0, 16)):
            c0, c1 = colours[(row + k) % 3]
            h = 14 + 4 * ((row + 2 * k) % 2)
            jars.append(Box(f"Jar{row}{k}", (x, y + h / 2, 2), (10, h, 10), p_glow(c0, c1), shading="fullbright"))
            jars.append(Box(f"Lid{row}{k}", (x, y + h + 1.5, 2), (11, 3, 11), iron))
    frame = Joint("Frame", (0, 0, 0), [
        Box("Side_L", (-25, 64, 0), (4, 128, 26), planks),
        Box("Side_R", (25, 64, 0), (4, 128, 26), planks),
        Box("Back", (0, 64, -11), (46, 124, 2), planks),
        *[Box(f"Board{k}", (0, y, 0), (46, 4, 24), planks) for k, y in enumerate((2, 24, 60, 96, 126))],
        *[Box(f"Band{k}", (0, y, 12.5), (54, 3, 1), iron) for k, y in enumerate((14, 80, 118))],
        *jars,
    ])
    return Joint("Body", (0, 0, 0), [frame])


SHELF_JOINTS = ["Body", "Frame"]


def shelf_anims():
    def idle(t):
        u = t / 3.0
        k = max(0.0, math.sin(2 * math.pi * u * 3)) ** 8
        return {"Frame": ((0, 0, 1.2 * k * math.sin(t * 60)), (0, 0, 0))}

    def hurt(t):
        k = keys(t, [(0, 0), (0.06, 1), (0.3, 0)])
        return {"Frame": ((-4 * k, 0, 3 * k), (0, 0, 0))}

    def death(t):
        k = keys(t, [(0, 0), (0.8, 1)])
        return {"Frame": ((88 * k, 0, 10 * k), (0, keys(t, [(0, 0), (0.8, -6)]), 0))}

    return [
        Anim("Idle", 3.0, idle, step=3, loop=True),
        Anim("Hurt", 0.3, hurt, step=3),
        Anim("Death", 0.8, death, step=3, hold=True),
    ]


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    view = {"size": 360, "scale": 1.3, "center": (0, 80, 0)}
    gpm.build("Lab_Chimera", chimera_model(), CHIMERA_JOINTS, chimera_anims(), 61, 512, {
        "$Comment": "Chimère du laboratoire (mini-boss de la Tour de l'Alchimiste), générée par tools/generate_chimera_models.py : quadrupède rapiécé aux coutures visibles, patte avant droite de golem de plomb, queue de serpent, tubes de liquide vert lumineux dans le dos.",
        "EyeHeight": 1.7,
        "HitBox": {"Max": {"X": 0.8, "Y": 2.2, "Z": 1.6}, "Min": {"X": -0.8, "Y": 0, "Z": -1.4}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#7dff6a", "Radius": 5},
    }, ["Bite", "Slam", "Tail"], preview, [
        ("repos", None, 0, view),
        ("profil", None, 0, dict(view, yaw=90, pitch=5)),
        ("marche", "Walk", 0.25, view),
        ("course", "Run", 0.15, dict(view, yaw=60)),
        ("morsure", "Bite", 0.42, dict(view, yaw=70)),
        ("poing", "Slam", 0.95, dict(view, yaw=60)),
        ("queue", "Tail", 0.8, view),
        ("mort", "Death", 1.8, dict(view, center=(0, 50, 0))),
    ])
    gpm.build("Chimera_Reagent_Shelf", shelf_model(), SHELF_JOINTS, shelf_anims(), 62, 128, {
        "$Comment": "Étagère de réactifs du laboratoire, générée par tools/generate_chimera_models.py : bois cerclé de fer, bocaux lumineux. Les homoncules y prennent les réactifs qui régénèrent la Chimère ; la détruire raccourcit sa régénération.",
        "EyeHeight": 1.0,
        "HitBox": {"Max": {"X": 0.45, "Y": 2.0, "Z": 0.35}, "Min": {"X": -0.45, "Y": 0, "Z": -0.35}},
        "MinScale": 1,
        "MaxScale": 1,
        "Light": {"Color": "#9dff8a", "Radius": 3},
    }, [], preview, [
        ("repos", None, 0, {"size": 240, "scale": 1.6, "center": (0, 64, 0)}),
        ("mort", "Death", 0.8, {"size": 240, "scale": 1.6, "center": (0, 40, 0), "yaw": 70}),
    ])


if __name__ == "__main__":
    main()
