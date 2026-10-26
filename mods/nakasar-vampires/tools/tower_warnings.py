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
anneau.

Couleur et opacité (Kevin, 26 octobre 2026 : « une zone d'annonce ennemie/danger doit être rouge orangée légère »,
jamais blanche) : celles des annonces du donjon Deepworks vanilla (Assets.zip 0.7.2 : Gobliterator_Slam_Warning,
Gobliterator_Quadrant_Warning, Gobliterator_Flamethrower_Warning), rouge pur #ff0000 en mélange additif, contour à 0,5
qui pulse entre 1 et 0,25, remplissage à 0,75 qui pulse entre 1 et 0,5. En additif, des zones ou des pastilles
superposées ne cumulent que du rouge (l'ancien #ff2a1a cumulait aussi du vert et du bleu, jusqu'au blanc). La couleur
est écrite sur chaque image clé ; ValidateAssets refuse toute zone d'annonce qui s'en écarte. Même table que
tools/generate_warnings.py du mod Fractales."""

import json
from pathlib import Path

PARTICLES = Path(__file__).resolve().parent.parent / "src" / "main" / "resources" / "Server" / "Particles" / "Nakasar" / "Tower" / "Warnings"
PREFIX = "Nakasar_Warning_"
SCALE = 0.68           # échelle de particule par bloc de rayon
BASE = 6.25            # taille de la particule à l'échelle 1 (comme Dungeon_Goblin_Mace_Slam_Warning)
RED = "#ff0000"        # rouge des annonces Deepworks
EDGE_OPACITY = 0.5     # opacité de départ du contour (Gobliterator_*_Warning_Cone / _Line / _Circle)
FILL_OPACITY = 0.75    # opacité de départ du remplissage (Gobliterator_Slam_Warning_Circle_Fill, _Flamethrower_Warning_Line_Fill)
# Pulsations Deepworks (image clé -> opacité) ; HIT : le disque touche le bord à l'instant du coup.
EDGE_PULSE = {0: 0, 15: 1, 30: 0.25, 45: 1, 60: 0.25, 75: 1, 90: 0.25, 95: 0.25, 100: 0}
FILL_PULSE = {0: 0, 15: 1, 30: 0.5, 45: 1, 60: 0.5, 75: 1, 90: 0.5, 95: 0.5, 97: 0.5, 100: 0}
HIT = 97
# Voile en mélange normal sous chaque couche additive (Kevin, 26 octobre 2026 : zone blanche sur le plateau clair de la
# Voix de la montagne) : l'additif n'ajoute rien à un sol déjà presque blanc (quartzite, neige), le voile le teinte en
# rouge ; sur un sol sombre il ne fait que foncer le fond sous le rouge Deepworks. Même animation, opacité x TINT.
TINT = 0.45
TINT_SUFFIX = "_Tint"
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


def edge_animation():
    """Contour Deepworks : rouge sur chaque image clé, opacité qui pulse jusqu'au coup."""
    return {str(k): {"Opacity": v, "Color": RED} for k, v in EDGE_PULSE.items()}


def fill_animation(start=None, full=None):
    """Remplissage Deepworks ; s'il grandit, de l'échelle `start` à `full`, il touche le bord à l'image HIT."""
    frames = {}
    for k, v in FILL_PULSE.items():
        frame = {"Opacity": v, "Color": RED}
        if start is not None and k == 0:
            frame["Scale"] = start
        elif full is not None and k >= HIT:
            frame["Scale"] = full
        frames[str(k)] = frame
    return frames


def initial(opacity, rotation, scale):
    return {"Opacity": opacity, "Color": RED, "Rotation": rotation, "Scale": scale}


def _files(t):
    life = t / 10
    flat = {"X": {"Min": 90, "Max": 90}}
    edge = _spawner(life, "Particles/Textures/Indicators/Warning_Circle_Base.png", edge_animation(),
                    initial(EDGE_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
    # Le disque grandit du centre jusqu'au contour : il le touche quand le coup tombe.
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png",
                    fill_animation({"X": {"Min": 0.05, "Max": 0.05}}, {"X": {"Min": 1, "Max": 1}}),
                    initial(FILL_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
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
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png", fill_animation(),
                    initial(FILL_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
    edge = _spawner(life, "Particles/Textures/Basic/Ball5.png", edge_animation(),
                    initial(EDGE_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
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


def with_tints(files, skip=()):
    """Ajoute à chaque système d'annonce (sauf `skip`) un voile BlendLinear sous chacune de ses couches additives."""
    import copy
    out = dict(files)
    for fname, doc in files.items():
        if not fname.endswith(".particlesystem") or fname[:-len(".particlesystem")] in skip:
            continue
        spawners = []
        for entry in doc["Spawners"]:
            base = files.get(entry["SpawnerId"] + ".particlespawner")
            if base is None or base.get("RenderMode") != "BlendAdd":
                spawners.append(entry)
                continue
            tint = copy.deepcopy(base)
            tint["RenderMode"] = "BlendLinear"
            frame = tint["Particle"]["InitialAnimationFrame"]
            frame["Opacity"] = round(frame["Opacity"] * TINT, 3)
            out[entry["SpawnerId"] + TINT_SUFFIX + ".particlespawner"] = tint
            offset = entry.get("PositionOffset", {}).get("Y", 0)
            spawners.append({"SpawnerId": entry["SpawnerId"] + TINT_SUFFIX,
                             "PositionOffset": {"Y": round(max(0.0, offset - 0.005), 3)}})
            spawners.append(entry)
        doc["Spawners"] = spawners
    return out


def write():
    PARTICLES.mkdir(parents=True, exist_ok=True)
    files = {}
    for t in sorted(set(WARNING_TENTHS) | _wanted):
        files.update(_files(t))
    for t in CONE_TENTHS:
        files.update(_cone_files(t))
    files = with_tints(files)
    for fname, doc in files.items():
        (PARTICLES / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return sorted(_wanted)
