#!/usr/bin/env python3
"""Génère le modèle de la Chimère du laboratoire (mini-boss de la Tour de l'Alchimiste) : un dragon qui ne vole pas
(Kevin, 19 octobre 2026 : « plus impressionnant »).

    python3 mods/nakasar-vampires/tools/generate_dragon_models.py [--preview SQUELETTE.json DOSSIER]

- Server/Models/Nakasar/Nakasar_Lab_Chimera.json : le modèle et la texture du dragon de feu vanilla
  (Server/Models/Elemental/Dragon_Fire.json, lu dans Assets.zip 0.7.2), ses animations vanilla de repos, marche,
  course, saut, blessure et mort (pas de vol : il reste au sol), une taille un peu réduite pour le laboratoire.
- Common/NPC/Nakasar/Lab_Dragon/Animations/{Bite,Slam,Tail}.blockyanim : ses trois attaques, jouées par ses
  interactions (Effects.ItemAnimationId) via Server/Item/Animations/Nakasar/Nakasar_Lab_Chimera.json :
  « Bite » (il ramasse son élan et mord, gueule grande ouverte), « Slam » (il se cabre, ailes à demi déployées, et
  retombe de tout son poids sur ses pattes avant), « Tail » (il se ramasse puis tourne sur lui-même, la queue fauche).

Les nœuds sont ceux du modèle vanilla (Pelvis > Tail1-4, Chest > Neck 1 > Neck2 > Head > Top Jaw > BotJaws, ailes
L-/R-Wing > Wing2 > Wing3, pattes). Une animation vanilla donne l'écart de chaque nœud à sa pose de modélisation ; au
repos le dragon replie ses ailes (BASE, premières images de son Idle) : nos attaques partent de cette pose, sinon les
ailes se déplieraient d'un coup. Rotation positive autour de X : le nez plonge et la mâchoire du bas s'ouvre.
--preview prend le squelette du modèle vanilla (nœuds, positions, boîtes, en JSON) et dessine les images clés.
"""
import json
import math
import sys
from pathlib import Path

import generate_pumpkin_models as gpm
from generate_pumpkin_models import keys, qeuler, qjson, qmul, qrot, vjson, write_json

VANILLA = "NPC/Elemental/Dragon_Fire"
BASE_PATH = "NPC/Nakasar/Lab_Dragon"
ROLE = "Nakasar_Lab_Chimera"
SCALE = 1.1
FPS = gpm.FPS

# Pose de repos du dragon vanilla (premières images de son Idle) : ailes repliées, cou et queue au naturel.
BASE = {
    "Neck2": (-0.01149, 0.00679, 0.01825, 0.99974),
    "BotJaws": (-0.08768, 0.01242, -0.00593, 0.99605),
    "Neck 1": (0.06836, -0.03849, -0.00625, 0.9969),
    "Tail1": (-0.08682, -0.08053, -0.03332, 0.9924),
    "Tail2": (-0.04343, -0.0735, -0.04683, 0.99525),
    "Tail3": (0.08699, -0.07713, -0.0404, 0.9924),
    "Tail4": (0.13017, -0.08379, -0.02398, 0.98765),
    "Head": (0.06975, 0.00115, 0.0071, 0.99754),
    "L-Wing": (-0.15035, 0.18744, -0.47686, 0.8455),
    "R-Wing": (-0.15035, -0.18744, 0.47686, 0.8455),
    "L-Wing2": (-0.55451, -0.4566, 0.29899, 0.6282),
    "R-Wing2": (-0.55451, 0.4566, -0.299, 0.6282),
    "L-Wing3": (0, 0, -0.08716, 0.9962),
    "R-Wing3": (0, 0, 0.08716, 0.9962),
}
PELVIS_BASE = (0, -2, 0)
PELVIS_BIND = (-0.1305, 0, 0, 0.9914)      # orientation du bassin dans le modèle vanilla
PELVIS_POS = (0, 80, -50)
BODY_CENTER = (0, 80, 0)                   # axe de la vrille de « Tail » : le milieu du corps
WINGS = ("L-Wing", "R-Wing", "L-Wing2", "R-Wing2", "L-Wing3", "R-Wing3")
TAILS = ("Tail1", "Tail2", "Tail3", "Tail4")
IDENTITY = (0.0, 0.0, 0.0, 1.0)


def slerp(a, b, t):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0:
        b, dot = tuple(-x for x in b), -dot
    if dot > 0.9995:
        q = tuple(x + (y - x) * t for x, y in zip(a, b))
    else:
        th = math.acos(dot)
        s = math.sin(th)
        q = tuple((math.sin((1 - t) * th) * x + math.sin(t * th) * y) / s for x, y in zip(a, b))
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def spread(s):
    """Ailes : de la pose repliée (s = 0) vers la pose de modélisation, grandes ouvertes (s = 1)."""
    return {w: slerp(BASE[w], IDENTITY, s) for w in WINGS}


def pose(extra, pelvis_rot=IDENTITY, pelvis_off=(0, 0, 0), wings=0.0):
    """Écarts de tous les nœuds : la pose de repos, tournée de `extra` {nœud: (x, y, z) en degrés}."""
    out = {n: q for n, q in BASE.items()}
    out.update(spread(wings))
    for n, (x, y, z) in extra.items():
        out[n] = qmul(out.get(n, IDENTITY), qeuler(x, y, z))
    out["Pelvis"] = pelvis_rot
    return out, {"Pelvis": tuple(b + o for b, o in zip(PELVIS_BASE, pelvis_off))}


def bite(t):
    # Il ramasse son élan (0 à 0,3 s), se jette en avant gueule ouverte et claque des mâchoires à 0,45 s.
    lunge = keys(t, [(0, 0), (0.3, -1), (0.45, 1), (0.8, 0)])
    neck = keys(t, [(0, 0), (0.3, -18), (0.45, 22), (0.8, 0)])
    jaw = keys(t, [(0, 0), (0.3, 38), (0.42, 42), (0.47, -2), (0.8, 0)])
    return pose({"Chest": (3 * lunge, 0, 0), "Neck 1": (neck, 0, 0), "Neck2": (0.5 * neck, 0, 0),
                 "Head": (keys(t, [(0, 0), (0.3, -12), (0.45, 10), (0.8, 0)]), 0, 0), "BotJaws": (jaw, 0, 0),
                 **{n: (0, 6 * math.sin(t * 9 + i), 0) for i, n in enumerate(TAILS)}},
                pelvis_off=(0, 0, 14 * lunge), wings=0.15 * max(0.0, -lunge))


def slam(t):
    # Il se cabre (0 à 0,85 s), ailes à demi déployées, gueule ouverte, puis retombe sur ses pattes avant à 1,15 s.
    rear = keys(t, [(0, 0), (0.85, 1), (1.0, 1.05), (1.15, -0.2), (1.6, 0)])
    roar = keys(t, [(0, 0), (0.85, 40), (1.15, 30), (1.6, 0)])
    return pose({"Chest": (-12 * rear, 0, 0), "Neck 1": (-10 * rear, 0, 0),
                 "Head": (keys(t, [(0, 0), (0.85, -15), (1.15, 22), (1.6, 0)]), 0, 0), "BotJaws": (roar, 0, 0),
                 "L-Thigh": (20 * rear, 0, 0), "R-Thigh": (20 * rear, 0, 0),
                 # la queue se relève à mesure qu'il se cabre : elle ne passe pas sous le sol
                 "Tail1": (24 * max(rear, 0.0), 0, 0), "Tail2": (12 * max(rear, 0.0), 0, 0),
                 "Tail3": (keys(t, [(0, 0), (0.85, -6), (1.15, 6), (1.6, 0)]), 0, 0)},
                pelvis_rot=qeuler(-22 * rear, 0, 0), pelvis_off=(0, 6 * max(rear, 0.0) - 6 * max(-rear, 0.0), 0),
                wings=keys(t, [(0, 0), (0.6, 0.75), (1.1, 0.75), (1.6, 0)]))


def tail(t):
    # Il se ramasse, la queue ramenée sur le côté (0 à 0,75 s), puis tourne sur lui-même (0,75 à 1,0 s) : la queue fauche.
    spin = keys(t, [(0, 0), (0.75, -25), (1.0, 360), (1.2, 360)])
    whip = keys(t, [(0, 0), (0.75, 22), (0.88, -30), (1.2, 0)])
    # Rotation autour de l'axe vertical du milieu du corps, exprimée dans le repère du bassin.
    yaw = qeuler(0, spin, 0)
    rot = qmul(qmul(qinv(PELVIS_BIND), yaw), PELVIS_BIND)
    rel = tuple(p - c for p, c in zip(PELVIS_POS, BODY_CENTER))
    moved = qrot(yaw, rel)
    off = tuple(c + m - p for c, m, p in zip(BODY_CENTER, moved, PELVIS_POS))
    crouch = keys(t, [(0, 0), (0.75, -5), (1.0, 0)])
    return pose({**{n: (0, whip * (0.6 + 0.2 * i), 0) for i, n in enumerate(TAILS)},
                 "Head": (keys(t, [(0, 0), (0.75, 10), (1.2, 0)]), 0, 0),
                 "BotJaws": (keys(t, [(0, 0), (0.75, 25), (1.2, 0)]), 0, 0)},
                pelvis_rot=rot, pelvis_off=(off[0], off[1] + crouch, off[2]))


ATTACKS = [("Bite", 0.8, bite), ("Slam", 1.6, slam), ("Tail", 1.2, tail)]


def anim_json(duration, fn, step=2):
    total = int(round(duration * FPS))
    times = list(range(0, total, step)) + [total]
    tracks = {}
    for fr in times:
        rots, offs = fn(fr / FPS)
        for n, q in rots.items():
            tracks.setdefault(n, {"position": [], "orientation": [], "shapeStretch": [], "shapeVisible": [],
                                  "shapeUvOffset": []})
            tracks[n]["orientation"].append({"time": fr, "delta": qjson(q), "interpolationType": "smooth"})
        for n, o in offs.items():
            tracks[n]["position"].append({"time": fr, "delta": vjson(o), "interpolationType": "smooth"})
    return {"formatVersion": 1, "duration": total, "holdLastKeyframe": False, "nodeAnimations": tracks}


def model_doc():
    def vanilla(name, **extra):
        return {"Animations": [dict({"Animation": f"{VANILLA}/Animations/{name}.blockyanim"}, **extra)]}
    jump = {"BlendingDuration": 0.1, "Looping": False, "Speed": 0.75}
    return {
        "$Comment": "Chimère du laboratoire (mini-boss de la Tour de l'Alchimiste) : le dragon de feu vanilla, sans le vol, "
                    "un peu plus petit ; ses attaques sont dans Server/Item/Animations/Nakasar/Nakasar_Lab_Chimera.json. "
                    "Généré par tools/generate_dragon_models.py.",
        "Model": f"{VANILLA}/Models/Model.blockymodel",
        "Texture": f"{VANILLA}/Models/Texture.png",
        "EyeHeight": 2.2,
        "HitBox": {"Max": {"X": 2, "Y": 2.8, "Z": 2}, "Min": {"X": -2, "Y": 0, "Z": -2}},
        "MinScale": SCALE,
        "MaxScale": SCALE,
        "Camera": {"Pitch": {"AngleRange": {"Max": 45, "Min": -30}, "TargetNodes": ["Head"]},
                   "Yaw": {"AngleRange": {"Max": 30, "Min": -30}, "TargetNodes": ["Head"]}},
        "AnimationSets": {
            "Idle": vanilla("Idle"),
            "Walk": vanilla("Walk"),
            "WalkBackward": vanilla("Walk_Backward"),
            "Run": vanilla("Run"),
            "Jump": vanilla("Jump", **jump),
            "JumpWalk": vanilla("Jump", **jump),
            "JumpRun": vanilla("Jump", **jump),
            "Fall": vanilla("Fall", BlendingDuration=0.4),
            "Hurt": vanilla("Hurt", BlendingDuration=0.1, Looping=False),
            "Death": vanilla("Death", Looping=False),
            "Alerted": vanilla("Idle"),
            "Wake": vanilla("Idle"),
        },
        "Particles": [
            {"PositionOffset": {"X": dx, "Y": 0.1, "Z": 0.48}, "SystemId": "Smoke_Black", "TargetNodeName": "Top Jaw"}
            for dx in (0.18, -0.18)],
    }


# --- aperçu ----------------------------------------------------------------------------------------------------

def render(skeleton, fn, t, out, yaw=90):
    from PIL import Image, ImageDraw
    rots, offs = fn(t)
    polys = []

    def go(n, ppos, prot):
        lp = tuple(a + b for a, b in zip(n["p"], offs.get(n["name"], (0, 0, 0))))
        wpos = tuple(a + b for a, b in zip(ppos, qrot(prot, lp)))
        wrot = qmul(qmul(prot, tuple(n["q"])), rots.get(n["name"], IDENTITY))
        if n["t"] == "box":
            hs = [abs(s) * abs(k) / 2 for s, k in zip(n["size"], n["st"])]
            corners = [tuple(a + b for a, b in zip(wpos, qrot(wrot, (n["off"][0] + sx * hs[0], n["off"][1] + sy * hs[1],
                                                                     n["off"][2] + sz * hs[2]))))
                       for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
            faces = [(0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)]
            shade = 120 + (hash(n["name"]) % 100)
            for f in faces:
                polys.append(([corners[i] for i in f], shade))
        for c in n.get("c", []):
            go(c, wpos, wrot)

    for root in skeleton:
        go(root, (0, 0, 0), IDENTITY)
    view = qeuler(0, yaw, 0)
    size, scale = 420, 0.9
    img = Image.new("RGB", (size, size), (24, 24, 32))
    d = ImageDraw.Draw(img)
    proj = []
    for pts, shade in polys:
        v = [qrot(qinv(view), p) for p in pts]
        depth = sum(p[2] for p in v) / 4
        proj.append((depth, [(size / 2 + p[0] * scale, size * 0.8 - p[1] * scale) for p in v], shade))
    for depth, pts, shade in sorted(proj, key=lambda x: x[0]):
        d.polygon(pts, fill=(shade, shade // 2 + 40, 60), outline=(20, 20, 20))
    d.line((0, size * 0.8, size, size * 0.8), fill=(90, 90, 90))
    img.save(out)


def main():
    write_json(gpm.SERVER / "Models" / "Nakasar" / f"{ROLE}.json", model_doc())
    for name, duration, fn in ATTACKS:
        write_json(gpm.COMMON / BASE_PATH / "Animations" / f"{name}.blockyanim", anim_json(duration, fn))
    write_json(gpm.SERVER / "Item" / "Animations" / "Nakasar" / f"{ROLE}.json",
               gpm.item_animations(BASE_PATH, [name for name, _, _ in ATTACKS]))
    print(f"{ROLE} : dragon vanilla, attaques {', '.join(n for n, _, _ in ATTACKS)}")
    if "--preview" in sys.argv:
        k = sys.argv.index("--preview")
        skeleton = json.loads(Path(sys.argv[k + 1]).read_text())
        out = Path(sys.argv[k + 2])
        out.mkdir(parents=True, exist_ok=True)
        for name, t, yaw in (("repos", 0, 90), ("morsure_elan", 0.3, 90), ("morsure", 0.45, 90),
                             ("cabre", 0.9, 90), ("cabre_face", 0.9, 30), ("retombe", 1.2, 90),
                             ("queue_ramasse", 0.75, 0), ("queue_vrille", 0.88, 0)):
            fn = {"repos": lambda tt: pose({})}.get(name) or {"m": bite, "c": slam, "r": slam, "q": tail}[name[0]]
            render(skeleton, fn, t, out / f"{name}.png", yaw)


if __name__ == "__main__":
    main()
