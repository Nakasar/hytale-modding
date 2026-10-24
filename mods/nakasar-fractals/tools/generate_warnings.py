"""Zones d'annonce des boss de fractales : cercle rouge au sol dont le disque se remplit pendant toute l'annonce et
touche le bord à l'instant du coup ; pastilles des cônes, anneaux et lignes. Copie de tools/tower_warnings.py du mod
Vampires (pas de bibliothèque commune, Kevin, 20 octobre 2026) avec les ids préfixés Nakasar_Fractal_.

Un système de particules par durée d'annonce, `Nakasar_Fractal_Warning_<dixièmes>` (ex. Nakasar_Fractal_Warning_18
pour 1,8 s), sur le modèle de Gobliterator_Slam_Warning (contour Warning_Circle_Base et disque Ball5). Échelle 0,68 par
bloc de rayon (`scale(r)`), à plat sur le sol. Toutes les durées de WARNING_TENTHS sont écrites : le Java
(combat.Telegraphs.circle) en choisit une à la volée.

Cônes, anneaux et lignes : combat.Telegraphs les dessine en pastilles rouges posées à plat, du bord de départ au bord
d'arrivée ; chaque pastille reste jusqu'à l'instant du coup. `Nakasar_Fractal_Cone_<dixièmes>` est une pastille qui
dure autant, `Nakasar_Fractal_Cone_Edge_<dixièmes>` un point du contour, posé dès le début.

Usage : python3 tools/generate_warnings.py"""

import json
from pathlib import Path

PARTICLES = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Particles" / "Nakasar" / "Fractals" / "Warnings"
PREFIX = "Nakasar_Fractal_Warning_"
SCALE = 0.68           # échelle de particule par bloc de rayon
BASE = 6.25            # taille de la particule à l'échelle 1 (comme Dungeon_Goblin_Mace_Slam_Warning)
RED = "#ff2a1a"
CONE_PREFIX = "Nakasar_Fractal_Cone_"
CONE_TENTHS = range(2, 61)   # Telegraphs.CONE_MIN / CONE_MAX en dixièmes de seconde
WARNING_TENTHS = range(5, 61)   # Telegraphs.WARNING_MIN / WARNING_MAX : toutes écrites, le Java en demande à la volée

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
        "$Comment": f"Zone d'annonce de {life:g} s : contour rouge et disque qui se remplit jusqu'au coup. Généré par tools/generate_warnings.py.",
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
            "$Comment": f"Cône, anneau ou ligne d'annonce ({life:g} s jusqu'au coup), dessiné par combat.Telegraphs. "
                        "Généré par tools/generate_warnings.py.",
            "Spawners": [{"SpawnerId": f"{name}_Dot", "PositionOffset": {"Y": dy}}],
            "CullDistance": 96,
            "IsImportant": True,
        }
        out[f"{name}_Dot.particlespawner"] = spawner
    return out


GREEN = "#3dff7a"
GREEN_ZONE = "Nakasar_Fractal_Green_Zone"
GREEN_LIFE = 0.6       # le Java le repose toutes les 0,5 s (combat.Telegraphs.greenZone) : pas de trou


def _green_zone_files():
    """Zone favorable (cercle vert de Carnasse) : même contour et même disque que les zones rouges, en vert, à opacité
    fixe ; posée de nouveau toutes les 0,5 s à l'échelle du rayon du moment (le cercle rétrécit)."""
    flat = {"X": {"Min": 90, "Max": 90}}
    edge = _spawner(GREEN_LIFE, "Particles/Textures/Indicators/Warning_Circle_Base.png", {
        "0": {"Opacity": 0.6, "Color": GREEN},
        "15": {"Opacity": 1},
        "85": {"Opacity": 1},
        "100": {"Opacity": 0.6, "Color": GREEN},
    }, {"Opacity": 1, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    fill = _spawner(GREEN_LIFE, "Particles/Textures/Basic/Ball5.png", {
        "0": {"Opacity": 0.25, "Color": GREEN},
        "15": {"Opacity": 0.4},
        "85": {"Opacity": 0.4},
        "100": {"Opacity": 0.25, "Color": GREEN},
    }, {"Opacity": 0.4, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    return {f"{GREEN_ZONE}.particlesystem": {
                "$Comment": "Zone favorable (cercle vert de Carnasse) : contour et disque verts, reposés par le Java toutes "
                            "les 0,5 s. Généré par tools/generate_warnings.py.",
                "Spawners": [{"SpawnerId": f"{GREEN_ZONE}_Edge", "PositionOffset": {"Y": 0.03}},
                             {"SpawnerId": f"{GREEN_ZONE}_Fill", "PositionOffset": {"Y": 0.02}}],
                "CullDistance": 96,
                "IsImportant": True},
            f"{GREEN_ZONE}_Edge.particlespawner": edge,
            f"{GREEN_ZONE}_Fill.particlespawner": fill}


def write():
    PARTICLES.mkdir(parents=True, exist_ok=True)
    files = _green_zone_files()
    for t in sorted(set(WARNING_TENTHS) | _wanted):
        files.update(_files(t))
    for t in CONE_TENTHS:
        files.update(_cone_files(t))
    for fname, doc in files.items():
        (PARTICLES / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return sorted(_wanted)


if __name__ == "__main__":
    write()
    print(f"Zones d'annonce écrites dans {PARTICLES}")
