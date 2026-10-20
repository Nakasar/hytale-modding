"""Effets de lecture des combats d'élites du Comté (Kevin, 20 octobre 2026 : « attaques claires et prévisibles »).

Les zones rouges des attaques sont celles de la Tour (tools/tower_warnings.py, dessinées par telegraph.Telegraphs) ;
ces particules disent le reste :

- `Nakasar_Tether_<élite>` : un point lumineux d'un lien entre un serviteur et l'élite qu'il protège ou soigne
  (SummonMinionsInteraction, clé TetherParticle, rejoué toutes les 250 ms de loin en loin) : vert pour les vrilles de
  la citrouille, bleu pour les rouages de l'armure, blanc pâle pour les fantômes du Spectre, rouge sombre pour les
  gardes appelés par la cloche.
- `Nakasar_Shield_Glow` : halo doré de l'élite protégée par ses serviteurs (MinionShieldSystem).
- `Nakasar_Ground_Bubbles` : le sol bouillonne là où une vrille va sortir (SummonMinionsInteraction, DelayParticle).
- `Nakasar_Ground_Fire` : sol en feu d'une lanterne-citrouille renversée (arena.ArenaBlocks), 3 blocs de rayon,
  rejoué toutes les 0,5 s.
- `Nakasar_Mist_Column` : colonne de brume pâle au point où le Spectre va surgir (Nakasar_Telegraph, MarkParticle).
- `Nakasar_Blood_Column` : colonne de brume de sang au point où le Comte ou la Comtesse va surgir.
- `Nakasar_Chains_Mark` : chaînes au-dessus d'un joueur que le Capitaine va emprisonner.

`write()` écrit tout dans Server/Particles/Nakasar/Elites."""

import json
from pathlib import Path

from tower_fx import BALL, SPARK, FLAT, _range, spawner

FOLDER = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Particles" / "Nakasar" / "Elites"
TETHERS = {
    "Vine": ("#c8ff7a", "#3f9a1a"),
    "Gear": ("#bfe8ff", "#2f7dff"),
    "Ghost": ("#ffffff", "#9fb8d8"),
    "Guard": ("#ff9a7a", "#8a1a10"),
}


def system(name, comment, spawners, cull=64):
    out = {f"{name}.particlesystem": {
        "$Comment": f"{comment} Généré par tools/elite_fx.py.",
        "Spawners": [{"SpawnerId": f"{name}_{suffix}", "PositionOffset": {"Y": dy}} for suffix, _, dy in spawners],
        "CullDistance": cull,
    }}
    for suffix, s, _ in spawners:
        out[f"{name}_{suffix}.particlespawner"] = s
    return out


def tethers():
    out = {}
    for name, (light, deep) in TETHERS.items():
        dot = spawner(BALL, (0.35, 0.35), {
            "0": {"Opacity": 0.2, "Color": light}, "40": {"Opacity": 0.9, "Color": deep}, "100": {"Opacity": 0, "Color": deep},
        }, {"Opacity": 0.6, "Scale": {"X": _range(0.35)}}, count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
        out.update(system(f"Nakasar_Tether_{name}", f"Point d'un lien entre un serviteur ({name}) et son élite.",
                          [("Dot", dot, 0.0)], cull=48))
    return out


def shield_glow():
    halo = spawner(BALL, (0.6, 0.6), {
        "0": {"Opacity": 0.15, "Color": "#ffe08a"}, "50": {"Opacity": 0.45, "Color": "#ffb020"},
        "100": {"Opacity": 0, "Color": "#ffe08a"},
    }, {"Opacity": 0.3, "Scale": {"X": _range(4.0)}}, count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
    sparks = spawner(SPARK, (0.4, 0.7), {
        "0": {"Opacity": 0, "Color": "#fff2b0"}, "30": {"Opacity": 1}, "100": {"Opacity": 0, "Color": "#ffb020"},
    }, {"Opacity": 1, "Scale": {"X": _range(0.2, 0.35)}}, count=(3, 4), rate=(8, 8), emit=(1.2, (0.0, 1.5)),
        speed=(0.3, 0.6), pitch=(60, 90), max_particles=4)
    return system("Nakasar_Shield_Glow", "Halo doré d'une élite protégée par ses serviteurs.",
                  [("Halo", halo, 1.2), ("Sparks", sparks, 0.5)], cull=64)


def bubbles():
    disc = spawner(BALL, (0.55, 0.55), {
        "0": {"Opacity": 0.5, "Color": "#5a3a1a"}, "50": {"Opacity": 0.8, "Color": "#3a2410"},
        "100": {"Opacity": 0, "Color": "#5a3a1a"},
    }, {"Opacity": 0.6, "Rotation": FLAT, "Scale": {"X": _range(3.0)}}, blend="BlendLinear", rotation="Velocity",
        count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
    blobs = spawner(BALL, (0.4, 0.6), {
        "0": {"Opacity": 0, "Color": "#9adf4a"}, "30": {"Opacity": 0.9, "Color": "#4f8a1a"}, "100": {"Opacity": 0},
    }, {"Opacity": 0.9, "Scale": {"X": _range(0.2, 0.35)}}, count=(5, 7), rate=(12, 12), emit=(0.6, (0.0, 0.1)),
        speed=(0.4, 0.9), pitch=(80, 90), gravity=-3, max_particles=7)
    return system("Nakasar_Ground_Bubbles", "Le sol bouillonne : une vrille va sortir ici.",
                  [("Disc", disc, 0.04), ("Blobs", blobs, 0.1)], cull=48)


def ground_fire():
    flames = spawner(SPARK, (0.5, 0.9), {
        "0": {"Opacity": 0, "Color": "#ffd27a"}, "20": {"Opacity": 1}, "100": {"Opacity": 0, "Color": "#ff3a10"},
    }, {"Opacity": 1, "Scale": {"X": _range(0.5, 0.9)}}, count=(14, 18), rate=(30, 30), emit=(3.0, (0.0, 0.2)),
        speed=(0.6, 1.4), pitch=(75, 90), max_particles=18)
    glow = spawner(BALL, (0.55, 0.55), {
        "0": {"Opacity": 0.35, "Color": "#ff7a20"}, "100": {"Opacity": 0.35, "Color": "#ff4a10"},
    }, {"Opacity": 0.35, "Rotation": FLAT, "Scale": {"X": _range(13.0)}}, rotation="Velocity", count=(1, 1),
        rate=(1, 1), burst=True, max_particles=1)
    return system("Nakasar_Ground_Fire", "Sol en feu d'une lanterne-citrouille renversée (3 blocs de rayon).",
                  [("Flames", flames, 0.1), ("Glow", glow, 0.04)], cull=64)


def column(name, comment, light, deep):
    mist = spawner(BALL, (0.5, 0.8), {
        "0": {"Opacity": 0, "Color": light}, "30": {"Opacity": 0.7}, "100": {"Opacity": 0, "Color": deep},
    }, {"Opacity": 0.7, "Scale": {"X": _range(0.6, 1.0)}}, blend="BlendLinear", count=(10, 14), rate=(30, 30),
        emit=(0.5, (0.0, 2.6)), speed=(0.1, 0.4), pitch=(80, 90), max_particles=14)
    return system(name, comment, [("Mist", mist, 0.0)], cull=64)


def chains_mark():
    links = spawner(BALL, (0.45, 0.45), {
        "0": {"Opacity": 0.3, "Color": "#c8c8d0"}, "50": {"Opacity": 1, "Color": "#ff3a2a"}, "100": {"Opacity": 0.2, "Color": "#c8c8d0"},
    }, {"Opacity": 0.8, "Scale": {"X": _range(0.3, 0.4)}}, count=(6, 6), rate=(20, 20), emit=(0.6, (0.0, 0.2)),
        speed=(0.0, 0.05), max_particles=6, burst=True)
    return system("Nakasar_Chains_Mark", "Chaînes rouges au-dessus d'un joueur que le Capitaine va emprisonner.",
                  [("Links", links, 0.0)], cull=64)


def files():
    out = {}
    for part in (tethers(), shield_glow(), bubbles(), ground_fire(),
                 column("Nakasar_Mist_Column", "Colonne de brume : le Spectre va surgir ici.", "#e8f2ff", "#8aa8d0"),
                 column("Nakasar_Blood_Column", "Colonne de brume de sang : le Comte ou la Comtesse va surgir ici.",
                        "#ff5a5a", "#5a0008"),
                 chains_mark()):
        out.update(part)
    return out


def ids():
    return {name[:-len(".particlesystem")] for name in files() if name.endswith(".particlesystem")}


def write():
    FOLDER.mkdir(parents=True, exist_ok=True)
    docs = files()
    for old in FOLDER.glob("*"):
        if old.name not in docs:
            old.unlink()
    for name, doc in docs.items():
        (FOLDER / name).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sorted(ids())


if __name__ == "__main__":
    print(write())
