"""Zones d'annonce de la Tour de l'Alchimiste : cercle rouge au sol dont le disque se remplit pendant toute l'annonce et
touche le bord à l'instant du coup (Kevin : « rendre les attaques et effets plus visibles et prévisibles »).

Un système de particules par durée d'annonce, `Nakasar_Warning_<dixièmes>` (ex. Nakasar_Warning_18 pour 1,8 s), sur le
modèle de Gobliterator_Slam_Warning (contour Warning_Circle_Base et disque Ball5, une particule chacun). Même rayon que
Feastmaster_Slam_Warning et Dungeon_Goblin_Mace_Slam_Warning à échelle égale : échelle 0,68 par bloc de rayon
(`scale(r)`), à plat sur le sol.

Les générateurs (alchemist_traps.py, generate_tower_mobs.py, generate_elites.py) demandent les durées avec `system(s)`
puis écrivent les fichiers avec `write()`. Toutes les durées de WARNING_TENTHS sont écrites : le Java
(telegraph.Telegraphs.circle, élites du Comté) en choisit une à la volée.

Cônes et anneaux (Kevin, 20 octobre 2026 : « cône rouge qui se charge », comme ceux de Deepworks) : telegraph.Telegraphs les
dessine en pastilles rouges posées à plat, anneau après anneau, du bord de départ au bord d'arrivée ; chaque pastille
reste jusqu'à l'instant du coup. `Nakasar_Cone_<dixièmes>` est une pastille qui dure autant, `Nakasar_Cone_Edge_<dixièmes>`
un point du contour, posé dès le début. Toutes les durées de CONE_TENTHS existent : le Java en choisit une à chaque
anneau."""

import json
from pathlib import Path

PARTICLES = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Particles" / "Nakasar" / "Tower" / "Warnings"
PREFIX = "Nakasar_Warning_"
SCALE = 0.68           # échelle de particule par bloc de rayon
BASE = 6.25            # taille de la particule à l'échelle 1 (comme Dungeon_Goblin_Mace_Slam_Warning)
RED = "#ff2a1a"
CONE_PREFIX = "Nakasar_Cone_"
CONE_TENTHS = range(2, 61)   # Telegraphs.CONE_MIN / CONE_MAX en dixièmes de seconde
WARNING_TENTHS = range(5, 61)   # Telegraphs.WARNING_MIN / WARNING_MAX : toutes écrites, les élites en demandent en Java

_wanted = set()


def tenths(seconds):
    return max(5, int(round(seconds * 10)))


def system(seconds):
    """Id du cercle d'annonce qui dure `seconds` (arrondi au dixième)."""
    t = tenths(seconds)
    _wanted.add(t)
    return f"{PREFIX}{t}"


def scale(radius):
    return round(SCALE * radius, 2)


def _spawner(life, texture, animation, initial, blend="BlendAdd"):
    return {
        "RenderMode": blend,
        "ParticleRotationInfluence": "Velocity",
        "ParticleLifeSpan": {"Min": life, "Max": life},
        "ParticleRotateWithSpawner": True,
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "Particle": {
            "Texture": texture,
            "ScaleRatioConstraint": "OneToOne",
            "UVOption": "None",
            "Animation": animation,
            "SoftParticles": "Disable",
            "InitialAnimationFrame": initial,
        },
        "Shape": "Sphere",
        "TotalParticles": {"Min": 1, "Max": 1},
        "SpawnRate": {"Min": 1, "Max": 1},
        "LinearFiltering": True,
        "MaxConcurrentParticles": 1,
        "InitialVelocity": {"Speed": {"Min": 0.01, "Max": 0.01}},
        "SpawnBurst": True,
    }


def _files(t):
    life = t / 10
    flat = {"X": {"Min": 90, "Max": 90}}
    edge = _spawner(life, "Particles/Textures/Indicators/Warning_Circle_Base.png", {
        "0": {"Opacity": 0, "Color": RED},
        "8": {"Opacity": 1},
        "92": {"Opacity": 1},
        "100": {"Opacity": 0, "Color": RED},
    }, {"Opacity": 1, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    # Le disque grandit du centre jusqu'au contour : il le touche quand le coup tombe.
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png", {
        "0": {"Opacity": 0.35, "Color": RED, "Scale": {"X": {"Min": 0.05, "Max": 0.05}}},
        "97": {"Opacity": 0.7, "Scale": {"X": {"Min": 1, "Max": 1}}},
        "100": {"Opacity": 0, "Color": RED, "Scale": {"X": {"Min": 1, "Max": 1}}},
    }, {"Opacity": 0.35, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    name = f"{PREFIX}{t}"
    system_doc = {
        "$Comment": f"Zone d'annonce de {life:g} s : contour rouge et disque qui se remplit jusqu'au coup. Généré par tools/tower_warnings.py.",
        "Spawners": [{"SpawnerId": f"{name}_Edge", "PositionOffset": {"Y": 0.03}},
                     {"SpawnerId": f"{name}_Fill", "PositionOffset": {"Y": 0.02}}],
        "CullDistance": 96,
        "IsImportant": True,
    }
    return {f"{name}.particlesystem": system_doc, f"{name}_Edge.particlespawner": edge,
            f"{name}_Fill.particlespawner": fill}


def _cone_files(t):
    """Pastille de cône (disque rouge à plat qui s'affirme jusqu'au coup) et point de contour, de t dixièmes."""
    life = t / 10
    flat = {"X": {"Min": 90, "Max": 90}}
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png", {
        "0": {"Opacity": 0, "Color": RED},
        "10": {"Opacity": 0.4},
        "95": {"Opacity": 0.6},
        "100": {"Opacity": 0, "Color": RED},
    }, {"Opacity": 0.4, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    edge = _spawner(life, "Particles/Textures/Basic/Ball5.png", {
        "0": {"Opacity": 0, "Color": RED},
        "8": {"Opacity": 0.9},
        "95": {"Opacity": 0.9},
        "100": {"Opacity": 0, "Color": RED},
    }, {"Opacity": 0.9, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    out = {}
    for name, spawner, dy in ((f"{CONE_PREFIX}{t}", fill, 0.02), (f"{CONE_PREFIX}Edge_{t}", edge, 0.03)):
        out[f"{name}.particlesystem"] = {
            "$Comment": f"Cône ou anneau d'annonce de la Tour ({life:g} s jusqu'au coup), dessiné par telegraph.Telegraphs. "
                        "Généré par tools/tower_warnings.py.",
            "Spawners": [{"SpawnerId": f"{name}_Dot", "PositionOffset": {"Y": dy}}],
            "CullDistance": 96,
            "IsImportant": True,
        }
        out[f"{name}_Dot.particlespawner"] = spawner
    return out


def write():
    PARTICLES.mkdir(parents=True, exist_ok=True)
    files = {}
    for t in sorted(set(WARNING_TENTHS) | _wanted):
        files.update(_files(t))
    for t in CONE_TENTHS:
        files.update(_cone_files(t))
    for fname, doc in files.items():
        (PARTICLES / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return sorted(_wanted)
