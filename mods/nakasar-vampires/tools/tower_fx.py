"""Effets de lecture des combats de la Tour de l'Alchimiste (Kevin, 20 octobre 2026 : « lisibilité d'abord »).

Une zone rouge au sol annonce toujours un effet négatif (tools/tower_warnings.py) ; ces particules disent le reste sans
changer cette couleur :

- `Nakasar_Trans_Ground_<élément>` : sol d'un quadrant actif du golem de cristal, au ras du sol (moins d'un bloc et
  demi) et peu dense, dans la couleur de l'élément : étincelles rasantes (Air), flammèches (Feu), éclats de roche et
  poussière (Terre), flocons qui filent au sol (Glace). Jamais de brouillard. Jouées par les volumes Trans_<élément>
  (alchemist_traps.py) toutes les TRANS_PULSE secondes, autant de temps.
- `Nakasar_Crackle_<élément>` : crépitements de l'élément dans un cercle rouge de l'Alchimiste (flammes, givre,
  étincelles, radicelles), pendant les 2,5 s de l'annonce. Rayon de 1,47 bloc à l'échelle 1, comme les cercles.
- `Nakasar_Flask_<élément>` : la fiole qu'il lève avant de lancer, lueur de la couleur de l'élément au-dessus de sa main.
- `Nakasar_Bucket_Glow` : seau plein d'un porteur de la Chimère (lueur verte, rejouée par le Java).
- `Nakasar_Acid_Puddle` : flaque d'un seau renversé (acide vert bordé de rouge : elle blesse), 1,47 bloc de rayon à
  l'échelle 1, rejouée chaque seconde.
- `Nakasar_Lectern_<sort>` : pupitre d'un livre de chapitre, dans la couleur du sort qui partira (rouge feu, bleu givre,
  blanc pluie de livres), rejoué chaque seconde tant que le livre vit.
- `Nakasar_Ink_Trace` : trait sombre au sol qui annonce une ligne d'encre du Codex, une seconde avant qu'elle coure.

`write()` écrit tout dans Server/Particles/Nakasar/Tower/Fx."""

import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Particles" / "Nakasar" / "Tower" / "Fx"
BALL = "Particles/Textures/Basic/Ball5.png"
SPARK = "Particles/Textures/Basic/Spark.png"
EDGE = "Particles/Textures/Indicators/Warning_Circle_Base.png"
RED = "#ff0000"       # rouge des annonces Deepworks (tower_warnings.RED)
BASE = 6.25          # disque de 1,47 bloc de rayon à l'échelle 1 (comme tower_warnings)
FLAT = {"X": {"Min": 90, "Max": 90}}
TRANS_PULSE = 3.0    # = alchemist_traps.TRANS_PULSE

# Couleurs (claire, profonde) des éléments : golem (Earth, Air, Ice, Fire) et Alchimiste (Fire, Frost, Thunder, Root).
COLORS = {
    "Fire": ("#ffb347", "#ff4a12"),
    "Frost": ("#d8f4ff", "#5fb8ff"),
    "Ice": ("#e8f8ff", "#7cc8ff"),
    "Thunder": ("#fff6a0", "#ffd21a"),
    "Air": ("#fff6a0", "#ffd21a"),
    "Root": ("#b8f070", "#3f8f2a"),
    "Earth": ("#c8a878", "#6b4f32"),
}


def _range(lo, hi=None):
    return {"Min": lo, "Max": lo if hi is None else hi}


def spawner(texture, life, animation, initial, *, blend="BlendAdd", rotation="Billboard", count=None, rate=None,
            emit=None, speed=(0.01, 0.01), yaw=(-180, 180), pitch=None, gravity=None, burst=False, max_particles=None,
            soft=False):
    s = {
        "RenderMode": blend,
        "ParticleRotationInfluence": rotation,
        "ParticleLifeSpan": _range(*life),
        "ParticleRotateWithSpawner": rotation != "Billboard",
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "LinearFiltering": True,
        "Particle": {
            "Texture": texture,
            "ScaleRatioConstraint": "OneToOne",
            "UVOption": "None" if texture in (BALL, EDGE) else "RandomFlipUV",
            "SoftParticles": "Enable" if soft else "Disable",
            "Animation": animation,
            "InitialAnimationFrame": initial,
        },
        "Shape": "Sphere",
        "SpawnBurst": burst,
    }
    if emit:
        s["EmitOffset"] = {"X": _range(0, emit[0]), "Y": _range(*emit[1]), "Z": _range(0, emit[0])}
    velocity = {"Speed": _range(*speed), "Yaw": _range(*yaw)}
    if pitch:
        velocity["Pitch"] = _range(*pitch)
    s["InitialVelocity"] = velocity
    if count:
        s["TotalParticles"] = _range(*count)
    if rate:
        s["SpawnRate"] = _range(*rate)
    if max_particles:
        s["MaxConcurrentParticles"] = max_particles
    if gravity:
        s["Attractors"] = [{"LinearAcceleration": {"Y": gravity}}]
    return s


def system(name, comment, spawners, cull=64):
    """Fichiers d'un système : {nom de fichier: document} ; `spawners` = [(suffixe, émetteur, décalage y)]."""
    out = {f"{name}.particlesystem": {
        "$Comment": f"{comment} Généré par tools/tower_fx.py.",
        "Spawners": [{"SpawnerId": f"{name}_{suffix}", "PositionOffset": {"Y": dy}} for suffix, _, dy in spawners],
        "CullDistance": cull,
    }}
    for suffix, s, _ in spawners:
        out[f"{name}_{suffix}.particlespawner"] = s
    return out


def motes(light, deep, *, life=(0.5, 1.0), size=(0.25, 0.45), emit=(4.0, (0.0, 0.3)), rate=(10, 14), speed=(0.2, 0.8),
          pitch=(0, 20), gravity=None, duration=TRANS_PULSE, texture=SPARK, max_particles=24):
    """Particules rasantes émises en continu pendant `duration` s : peu nombreuses, jamais plus haut que ~1,5 bloc."""
    s = spawner(texture, life, {
        "0": {"Opacity": 0, "Color": light},
        "20": {"Opacity": 0.9},
        "100": {"Opacity": 0, "Color": deep},
    }, {"Opacity": 0.9, "Scale": {"X": _range(*size)}}, rate=rate, emit=emit, speed=speed, pitch=pitch,
        gravity=gravity, max_particles=max_particles)
    s["LifeSpan"] = duration
    return s


def trans_ground():
    """Sol des quadrants actifs : une source par point du quadrant (alchemist_traps.transmutation), 4 blocs de rayon."""
    out = {}
    air = motes(*COLORS["Air"], life=(0.15, 0.35), size=(0.2, 0.4), rate=(12, 16), speed=(1.5, 3.0), pitch=(0, 8))
    out.update(system("Nakasar_Trans_Ground_Air", "Sol électrifié d'un quadrant d'air actif (golem de cristal).",
                      [("Sparks", air, 0.1)]))
    flames = motes(*COLORS["Fire"], life=(0.5, 0.9), size=(0.35, 0.6), rate=(8, 12), speed=(0.3, 0.8), pitch=(70, 90))
    embers = motes("#ffe2a0", "#ff6a1a", life=(0.8, 1.2), size=(0.12, 0.2), rate=(5, 8), speed=(0.4, 1.0),
                   pitch=(60, 90), gravity=-0.6)
    out.update(system("Nakasar_Trans_Ground_Fire", "Flammes au sol d'un quadrant de feu actif (golem de cristal).",
                      [("Flames", flames, 0.1), ("Embers", embers, 0.2)]))
    rocks = motes(*COLORS["Earth"], texture=BALL, life=(0.6, 1.0), size=(0.12, 0.22), rate=(6, 9), speed=(1.0, 2.2),
                  pitch=(0, 10), gravity=-6, max_particles=16)
    dust = motes("#b89a70", "#7a6448", texture=BALL, life=(0.8, 1.3), size=(0.4, 0.7), rate=(4, 6), speed=(0.1, 0.3),
                 pitch=(0, 30), max_particles=12)
    dust["RenderMode"] = "BlendLinear"
    dust["Particle"]["Animation"]["20"]["Opacity"] = 0.35
    out.update(system("Nakasar_Trans_Ground_Earth", "Rochers et fractures d'un quadrant de terre actif (golem de cristal).",
                      [("Rocks", rocks, 0.1), ("Dust", dust, 0.1)]))
    snow = motes(*COLORS["Ice"], texture=BALL, life=(0.8, 1.4), size=(0.08, 0.16), rate=(12, 16), speed=(1.5, 2.8),
                 pitch=(-5, 5), emit=(4.0, (0.1, 1.0)), max_particles=28)
    out.update(system("Nakasar_Trans_Ground_Ice", "Blizzard rasant, sans brouillard, d'un quadrant de glace actif "
                      "(golem de cristal).", [("Snow", snow, 0.1)]))
    return out


CRACKLE = {
    # flammèches qui montent, givre qui scintille, étincelles qui sautent, radicelles qui percent
    "Fire": dict(life=(0.4, 0.7), size=(0.25, 0.45), speed=(0.4, 1.0), pitch=(70, 90), gravity=None),
    "Frost": dict(life=(0.6, 1.0), size=(0.15, 0.3), speed=(0.05, 0.2), pitch=(60, 90), gravity=None),
    "Thunder": dict(life=(0.1, 0.25), size=(0.2, 0.4), speed=(1.5, 3.0), pitch=(0, 30), gravity=None),
    "Root": dict(life=(0.5, 0.8), size=(0.12, 0.22), speed=(0.6, 1.2), pitch=(80, 90), gravity=-2.5),
}


def crackles(warn=2.5):
    """Crépitements dans un cercle rouge de l'Alchimiste, pendant toute l'annonce (échelle = celle du cercle)."""
    out = {}
    for el, kw in CRACKLE.items():
        light, deep = COLORS[el]
        s = motes(light, deep, emit=(1.1, (0.0, 0.15)), rate=(10, 14), duration=warn, max_particles=20, **kw)
        out.update(system(f"Nakasar_Crackle_{el}", f"Crépitements ({el}) d'une fiole de l'Alchimiste dans son cercle "
                          "rouge.", [("Crackle", s, 0.1)]))
    return out


def flasks():
    """Fiole levée : une lueur de la couleur de l'élément et quelques étincelles, 1,2 s."""
    out = {}
    for el in ("Fire", "Frost", "Thunder", "Root"):
        light, deep = COLORS[el]
        glow = spawner(BALL, (1.2, 1.2), {
            "0": {"Opacity": 0, "Color": light, "Scale": {"X": _range(0.4)}},
            "20": {"Opacity": 1, "Scale": {"X": _range(1)}},
            "80": {"Opacity": 1, "Color": deep},
            "100": {"Opacity": 0, "Color": deep, "Scale": {"X": _range(0.6)}},
        }, {"Opacity": 1, "Scale": {"X": _range(0.9)}}, count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
        sparks = spawner(SPARK, (0.4, 0.8), {
            "0": {"Opacity": 1, "Color": light}, "100": {"Opacity": 0, "Color": deep},
        }, {"Opacity": 1, "Scale": {"X": _range(0.15, 0.3)}}, count=(10, 14), rate=(12, 12), emit=(0.3, (0.0, 0.3)),
            speed=(0.6, 1.4), max_particles=14)
        out.update(system(f"Nakasar_Flask_{el}", f"Fiole ({el}) que l'Alchimiste lève avant de lancer.",
                          [("Glow", glow, 0.0), ("Sparks", sparks, 0.0)]))
    return out


def bucket():
    glow = spawner(BALL, (0.7, 0.7), {
        "0": {"Opacity": 0.3, "Color": "#9dff6a"}, "50": {"Opacity": 0.9, "Color": "#4fd62a"},
        "100": {"Opacity": 0.3, "Color": "#9dff6a"},
    }, {"Opacity": 0.6, "Scale": {"X": _range(0.7)}}, count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
    drips = spawner(BALL, (0.4, 0.6), {
        "0": {"Opacity": 1, "Color": "#9dff6a"}, "100": {"Opacity": 0, "Color": "#2c8a14"},
    }, {"Opacity": 1, "Scale": {"X": _range(0.08, 0.14)}}, count=(2, 3), rate=(4, 4), emit=(0.25, (0.0, 0.1)),
        speed=(0.05, 0.2), pitch=(-90, -70), gravity=-4, max_particles=3)
    return system("Nakasar_Bucket_Glow", "Seau plein d'un porteur de la Chimère (lueur verte).",
                  [("Glow", glow, 0.0), ("Drips", drips, 0.0)])


def puddle():
    """Flaque d'acide : disque vert à plat, contour rouge (elle blesse) et bulles, 1,3 s (rejouée chaque seconde)."""
    disc = spawner(BALL, (1.3, 1.3), {
        "0": {"Opacity": 0.55, "Color": "#4fd62a"}, "30": {"Opacity": 0.8, "Color": "#2f9a12"},
        "80": {"Opacity": 0.8}, "100": {"Opacity": 0.55, "Color": "#4fd62a"},
    }, {"Opacity": 0.7, "Rotation": FLAT, "Scale": {"X": _range(BASE)}}, blend="BlendLinear", rotation="Velocity",
        count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
    # Contour rouge des zones Deepworks (tower_warnings), sans pulsation : la flaque est rejouée chaque seconde.
    edge = spawner(EDGE, (1.3, 1.3), {
        "0": {"Opacity": 1, "Color": RED}, "100": {"Opacity": 1, "Color": RED},
    }, {"Opacity": 0.5, "Color": RED, "Rotation": FLAT, "Scale": {"X": _range(BASE)}}, blend="BlendLinear", rotation="Velocity", count=(1, 1),
        rate=(1, 1), burst=True, max_particles=1)
    bubbles = spawner(SPARK, (0.5, 0.9), {
        "0": {"Opacity": 0, "Color": "#c8ff9a"}, "30": {"Opacity": 0.9}, "100": {"Opacity": 0, "Color": "#2f9a12"},
    }, {"Opacity": 0.9, "Scale": {"X": _range(0.25, 0.4)}}, count=(5, 7), rate=(8, 8), emit=(1.2, (0.0, 0.1)),
        speed=(0.2, 0.5), pitch=(80, 100), max_particles=7)
    return system("Nakasar_Acid_Puddle", "Flaque d'acide d'un seau renversé (Chimère du laboratoire).",
                  [("Disc", disc, 0.04), ("Edge", edge, 0.05), ("Bubbles", bubbles, 0.1)])


def lecterns():
    """Pupitre d'un chapitre : colonne de lumière douce et étincelles, dans la couleur du sort à venir."""
    out = {}
    for spell, (light, deep) in {"Fire": ("#ff8a5a", "#ff2a1a"), "Frost": ("#bfe6ff", "#3f9fff"),
                                 "Rain": ("#ffffff", "#d8d8e8")}.items():
        glow = spawner(BALL, (1.1, 1.1), {
            "0": {"Opacity": 0.4, "Color": light}, "50": {"Opacity": 0.9, "Color": deep},
            "100": {"Opacity": 0.4, "Color": light},
        }, {"Opacity": 0.6, "Scale": {"X": _range(1.6)}}, count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
        sparks = spawner(SPARK, (0.6, 1.0), {
            "0": {"Opacity": 0, "Color": light}, "30": {"Opacity": 1}, "100": {"Opacity": 0, "Color": deep},
        }, {"Opacity": 1, "Scale": {"X": _range(0.2, 0.35)}}, count=(6, 8), rate=(8, 8), emit=(0.6, (0.0, 0.2)),
            speed=(0.6, 1.2), pitch=(70, 90), max_particles=8)
        out.update(system(f"Nakasar_Lectern_{spell}", f"Pupitre d'un chapitre du Codex : sort {spell} à venir.",
                          [("Glow", glow, 0.3), ("Sparks", sparks, 0.2)]))
    return out


def ink_trace():
    dot = spawner(BALL, (1.4, 1.4), {
        "0": {"Opacity": 0, "Color": "#2a0f40"}, "15": {"Opacity": 0.85, "Color": "#12061c"},
        "90": {"Opacity": 0.85}, "100": {"Opacity": 0, "Color": "#2a0f40"},
    }, {"Opacity": 0.8, "Rotation": FLAT, "Scale": {"X": _range(BASE)}}, blend="BlendLinear", rotation="Velocity",
        count=(1, 1), rate=(1, 1), burst=True, max_particles=1)
    return system("Nakasar_Ink_Trace", "Trait sombre qui annonce une ligne d'encre du Codex.", [("Dot", dot, 0.03)])


def files():
    out = {}
    for part in (trans_ground(), crackles(), flasks(), bucket(), puddle(), lecterns(), ink_trace()):
        out.update(part)
    return out


def ids():
    """Ids des systèmes (pour les listes d'ids vérifiés des volumes)."""
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
