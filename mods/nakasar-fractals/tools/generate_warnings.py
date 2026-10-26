"""Zones d'annonce des boss de fractales : cercle rouge au sol dont le disque se remplit pendant toute l'annonce et
touche le bord à l'instant du coup ; rectangle des lignes et secteur des cônes. Copie de tools/tower_warnings.py du mod
Vampires (pas de bibliothèque commune, Kevin, 20 octobre 2026) avec les ids préfixés Nakasar_Fractal_.

Un système de particules par durée d'annonce, `Nakasar_Fractal_Warning_<dixièmes>` (ex. Nakasar_Fractal_Warning_18
pour 1,8 s), sur le modèle de Gobliterator_Slam_Warning (contour Warning_Circle_Base et disque Ball5). Échelle 0,68 par
bloc de rayon (`scale(r)`), à plat sur le sol. Toutes les durées de WARNING_TENTHS sont écrites : le Java
(combat.Telegraphs.circle) en choisit une à la volée.

Lignes et cônes (Kevin, 24 octobre 2026 : « une ligne droite en rectangle, un cône en cône, comme les Deepworks », plus
de pastilles alignées) : une seule particule à plat, tournée par le Java vers l'attaque, sur le modèle du lance-flammes
du Gobliterator (Gobliterator_Flamethrower_Warning : contour fixe et remplissage qui s'allonge depuis le lanceur, origine
de la texture au centre du quad, Rotation X 90 / Y 180 pour que le haut de la texture pointe devant) et de son quadrant
(Warning_Cone_Base / _Fill, le remplissage grandit depuis le sommet).

- `Nakasar_Fractal_Line_<rapport>_<dixièmes>` : rectangle dont la longueur vaut <rapport>/10 fois la largeur ; le Java
  le pose à l'échelle `LINE_SCALE * largeur`.
- `Nakasar_Fractal_Sector_<angle>_<dixièmes>` : secteur de <angle> degrés ; échelle `SCALE * rayon`, comme les cercles.

Les rapports et les angles sont ceux des interactions du pack (Shape Line / Cone de Nakasar_Fractal_Telegraph,
Nakasar_Fractal_Charge) et des lignes posées en Java (JAVA_LINES) : relancer ce script après en avoir ajouté. Ils sont
exportés dans combat/WarningShapes.java ; une forme absente prend le rapport ou l'angle le plus proche. Textures : la
ligne reprend Warning_Square_Base vanilla (celle du lance-flammes) ; les secteurs, dont seul l'angle de 90° existe en
vanilla, Common/Particles/Textures/Nakasar/Fractals/Warning_Sector_<angle>_{Base,Fill}.png, blanches (teintes en rouge
par la particule).

Couleur et opacité (Kevin, 26 octobre 2026 : « une zone d'annonce ennemie/danger doit être rouge orangée légère »,
jamais blanche) : celles des annonces du donjon Deepworks vanilla (Assets.zip 0.7.2 : Gobliterator_Slam_Warning,
Gobliterator_Quadrant_Warning, Gobliterator_Flamethrower_Warning), rouge pur #ff0000, contour à 0,5 qui pulse entre 1
et 0,25, remplissage à 0,75 qui pulse entre 1 et 0,5. Mais en mélange normal (BlendLinear), pas additif comme les
Deepworks : l'additif n'ajoute rien à un sol presque blanc (dalles de quartzite de la Voix de la montagne, neige), où la
zone paraissait blanche ; le mélange normal teint en rouge n'importe quel sol (choix de Kevin, 26 octobre 2026). La
couleur est écrite sur chaque image clé ; ValidateAssets refuse toute zone d'annonce qui s'en écarte.

Usage : python3 tools/generate_warnings.py"""

import json
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent
RESOURCES = MOD / "src" / "main" / "resources"
PARTICLES = RESOURCES / "Server" / "Particles" / "Nakasar" / "Fractals" / "Warnings"
INTERACTIONS = RESOURCES / "Server" / "Item" / "Interactions"
TEXTURES = RESOURCES / "Common" / "Particles" / "Textures" / "Nakasar" / "Fractals"
JAVA = MOD / "src" / "main" / "java" / "dev" / "nakasar" / "hytale" / "fractals" / "combat" / "WarningShapes.java"
PREFIX = "Nakasar_Fractal_Warning_"
SCALE = 0.68           # échelle de particule par bloc de rayon
BASE = 6.25            # taille de la particule à l'échelle 1 (comme Dungeon_Goblin_Mace_Slam_Warning)
RED = "#ff0000"        # rouge des annonces Deepworks
EDGE_OPACITY = 0.5     # opacité de départ du contour (Gobliterator_*_Warning_Cone / _Line / _Circle)
FILL_OPACITY = 0.75    # opacité de départ du remplissage (Gobliterator_Slam_Warning_Circle_Fill, _Flamethrower_Warning_Line_Fill)
# Pulsations Deepworks (image clé -> opacité) ; HIT : le remplissage touche le bord à l'instant du coup.
EDGE_PULSE = {0: 0, 15: 1, 30: 0.25, 45: 1, 60: 0.25, 75: 1, 90: 0.25, 95: 0.25, 100: 0}
FILL_PULSE = {0: 0, 15: 1, 30: 0.5, 45: 1, 60: 0.5, 75: 1, 90: 0.5, 95: 0.5, 97: 0.5, 100: 0}
HIT = 97
LINE_PREFIX = "Nakasar_Fractal_Line_"
SECTOR_PREFIX = "Nakasar_Fractal_Sector_"
SHAPE_TENTHS = range(5, 31)   # WarningShapes.MIN_TENTHS / MAX_TENTHS : toutes les annonces de ligne et de cône durent moins de 3 s
LINE_SCALE = SCALE / 2        # échelle d'une ligne par bloc de largeur : le quad fait BASE de large
LINE_TEXTURE = "Particles/Textures/Indicators/Warning_Square_Base.png"   # rectangle dans la moitié haute du quad
SECTOR_TEXTURE = "Particles/Textures/Nakasar/Fractals/Warning_Sector"
# Lignes posées en Java (longueur, largeur, où) : celles des interactions sont lues dans le pack.
JAVA_LINES = [
    (9, 3, "swampland.Mossman STRIKE_LENGTH x STRIKE_WIDTH"),
    (12, 2, "cliffside.Traps gargouilles : GUST_REACH - 1 x GUST_WIDTH"),
    (1, 2, "uncategorized.Uncategorized tourelles : une marche x 2 * TURRET_HALF_WIDTH"),
    (16, 2, "snowblind.Source lances de glace : LANCE_LENGTH x LANCE_WIDTH"),
    (14, 8, "sirensreef.ReefShip courants fantômes : DRAFT_LENGTH x DRAFT_WIDTH"),
    (11, 5, "deepstone.EastPath vent du pont : WIND_LENGTH x WIND_WIDTH"),
    (11, 4, "sunquapeak.WaterPath cascades : SURGE_LENGTH x SURGE_WIDTH"),
    (36, 4, "sunquapeak.Ai ondes d'orbes : ORB_LINE_LENGTH x ORB_LINE_WIDTH"),
]
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


def _spawner(life, texture, animation, initial, blend="BlendLinear"):
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
    edge = _spawner(life, "Particles/Textures/Indicators/Warning_Circle_Base.png", _edge_animation(),
                    _initial(EDGE_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
    # Le disque grandit du centre jusqu'au contour : il le touche quand le coup tombe.
    fill = _spawner(life, "Particles/Textures/Basic/Ball5.png",
                    _fill_animation({"X": {"Min": 0.05, "Max": 0.05}}, {"X": {"Min": 1, "Max": 1}}),
                    _initial(FILL_OPACITY, flat, {"X": {"Min": BASE, "Max": BASE}}))
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


def _shape_spawner(life, texture, animation, initial, constraint):
    """Particule à plat tournée avec le lanceur (copie des avertissements du Gobliterator)."""
    spawner = _spawner(life, texture, animation, initial)
    spawner["ParticleRotationInfluence"] = "None"
    spawner["Particle"]["ScaleRatioConstraint"] = constraint
    return spawner


# Haut de la texture devant le lanceur : à plat (X 90) puis demi-tour (Y 180), comme Gobliterator_Flamethrower_Warning.
FORWARD = {"X": {"Min": 90, "Max": 90}, "Y": {"Min": 180, "Max": 180}}


def _xy(x, y):
    return {"X": {"Min": x, "Max": x}, "Y": {"Min": y, "Max": y}}


def _shape_system(name, life, comment):
    return {
        "$Comment": f"{comment} ({life:g} s jusqu'au coup), posé par combat.Telegraphs. Généré par tools/generate_warnings.py.",
        "Spawners": [{"SpawnerId": f"{name}_Edge", "PositionOffset": {"Y": 0.03}},
                     {"SpawnerId": f"{name}_Fill", "PositionOffset": {"Y": 0.02}}],
        "CullDistance": 96,
        "IsImportant": True,
    }


def _edge_animation():
    """Contour Deepworks : rouge sur chaque image clé, opacité qui pulse jusqu'au coup."""
    return {str(k): {"Opacity": v, "Color": RED} for k, v in EDGE_PULSE.items()}


def _fill_animation(start, full):
    """Remplissage Deepworks qui grandit de l'échelle `start` à `full` et touche le bord à l'image HIT."""
    frames = {}
    for k, v in FILL_PULSE.items():
        frame = {"Opacity": v, "Color": RED}
        if k == 0:
            frame["Scale"] = start
        elif k >= HIT:
            frame["Scale"] = full
        frames[str(k)] = frame
    return frames


def _initial(opacity, rotation, scale):
    return {"Opacity": opacity, "Color": RED, "Rotation": rotation, "Scale": scale}


def _line_files(aspect, t):
    """Rectangle de `aspect`/10 fois sa largeur : contour posé d'emblée, remplissage qui s'allonge depuis le lanceur
    (Warning_Square_Base occupe la moitié haute du quad, qui part du lanceur, d'où le quad deux fois plus long que la
    zone ; contour et remplissage sur la même texture, comme Gobliterator_Flamethrower_Warning)."""
    life = t / 10
    size = _xy(BASE, 2 * aspect / 10 * BASE)
    edge = _shape_spawner(life, LINE_TEXTURE, _edge_animation(), _initial(EDGE_OPACITY, FORWARD, size), "None")
    fill = _shape_spawner(life, LINE_TEXTURE, _fill_animation(_xy(1, 0.02), _xy(1, 1)),
                          _initial(FILL_OPACITY, FORWARD, size), "None")
    name = f"{LINE_PREFIX}{aspect}_{t}"
    return {f"{name}.particlesystem": _shape_system(name, life, "Ligne d'annonce rectangulaire"),
            f"{name}_Edge.particlespawner": edge, f"{name}_Fill.particlespawner": fill}


def _sector_files(angle, t):
    """Secteur de `angle` degrés, sommet au centre du quad : le remplissage grandit depuis le sommet."""
    life = t / 10
    texture = f"{SECTOR_TEXTURE}_{angle}"
    size = {"X": {"Min": BASE, "Max": BASE}}
    edge = _shape_spawner(life, texture + "_Base.png", _edge_animation(), _initial(EDGE_OPACITY, FORWARD, size),
                          "OneToOne")
    fill = _shape_spawner(life, texture + "_Fill.png",
                          _fill_animation({"X": {"Min": 0.03, "Max": 0.03}}, {"X": {"Min": 1, "Max": 1}}),
                          _initial(FILL_OPACITY, FORWARD, size), "OneToOne")
    name = f"{SECTOR_PREFIX}{angle}_{t}"
    return {f"{name}.particlesystem": _shape_system(name, life, f"Cône d'annonce de {angle}°"),
            f"{name}_Edge.particlespawner": edge, f"{name}_Fill.particlespawner": fill}


# --- textures --------------------------------------------------------------------------------------

TEX = 256              # côté des textures (le quad entier ; la zone part du centre vers le haut)
TEX_EDGE = 5           # épaisseur du contour (pixels)


def _sector_textures(angle):
    """Contour (bords droits et arc) et remplissage d'un secteur de `angle` degrés pointé vers le haut, sommet au
    centre ; le remplissage se renforce vers l'arc, comme Warning_Cone_Fill."""
    from PIL import Image
    import math
    base = Image.new("RGBA", (TEX, TEX), (255, 255, 255, 0))
    fill = Image.new("RGBA", (TEX, TEX), (255, 255, 255, 0))
    c = TEX / 2
    r_max = c - 2
    half = math.radians(angle) / 2
    for y in range(TEX):
        for x in range(TEX):
            dx, dy = x + 0.5 - c, c - (y + 0.5)
            r = math.hypot(dx, dy)
            if r > r_max:
                continue
            off = abs(math.atan2(dx, dy))     # écart à l'axe (vers le haut)
            if off > half:
                continue
            side = r * math.sin(half - off) if half - off < math.pi / 2 else r
            edge = min(r_max - r, side)
            t = r / r_max
            base.putpixel((x, y), (255, 255, 255, 235 if edge < TEX_EDGE else int(25 + 45 * t)))
            fill.putpixel((x, y), (255, 255, 255, int(40 + 130 * t)))
    return base, fill


# --- formes en usage ---------------------------------------------------------------------------

def _shapes_in_use():
    """Rapports longueur/largeur (dixièmes) et angles (degrés) des lignes et cônes du pack et de JAVA_LINES."""
    lines = {_aspect(length, width) for length, width, _ in JAVA_LINES}
    angles = set()

    def walk(o):
        if isinstance(o, dict):
            kind = o.get("Type")
            if kind == "Nakasar_Fractal_Telegraph" and o.get("Shape") == "Line":
                lines.add(_aspect(o.get("Length", 10), o.get("Width", 1.2)))
            elif kind == "Nakasar_Fractal_Telegraph" and o.get("Shape") == "Cone":
                angles.add(int(round(o.get("Angle", 90))))
            elif kind == "Nakasar_Fractal_Charge":
                lines.add(_aspect(o.get("Length", 12), o.get("Width", 2.4)))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for f in sorted(INTERACTIONS.rglob("*.json")):
        walk(json.loads(f.read_text(encoding="utf-8")))
    return sorted(lines), sorted(angles)


def _aspect(length, width):
    return max(5, int(round(10 * length / width)))


def _write_java(lines, angles):
    JAVA.write_text(f"""package dev.nakasar.hytale.fractals.combat;

/**
 * Formes d'annonce dont les particules existent (tools/generate_warnings.py, qui écrit ce fichier) : rapports
 * longueur/largeur des lignes en dixièmes ({{@code Nakasar_Fractal_Line_<rapport>_<dixièmes>}}) et angles des cônes en
 * degrés ({{@code Nakasar_Fractal_Sector_<angle>_<dixièmes>}}), pour des durées de {{@link #MIN_TENTHS}} à
 * {{@link #MAX_TENTHS}} dixièmes de seconde.
 */
final class WarningShapes {{

    static final int[] LINE_ASPECTS = {{{", ".join(map(str, lines))}}};
    static final int[] SECTOR_ANGLES = {{{", ".join(map(str, angles))}}};
    static final int MIN_TENTHS = {SHAPE_TENTHS.start};
    static final int MAX_TENTHS = {SHAPE_TENTHS.stop - 1};
    /** Échelle de particule d'une ligne par bloc de largeur (celle d'un secteur est {{@link Telegraphs#WARNING_SCALE}} par bloc de rayon). */
    static final float LINE_SCALE = {LINE_SCALE}f;

    private WarningShapes() {{
    }}
}}
""", encoding="utf-8")


GREEN = "#3dff7a"
GREEN_ZONE = "Nakasar_Fractal_Green_Zone"
GREEN_LIFE = 0.6       # le Java le repose toutes les 0,5 s (combat.Telegraphs.greenZone) : pas de trou


def _green_zone_files():
    """Zone favorable (cercle vert de Carnasse) : même contour que les zones rouges, en vert, à opacité fixe, sans
    disque (un sol vert jugé laid, Kevin 2026-10-24 : des émanations montent dans le cercle à la place) ; posée de
    nouveau toutes les 0,5 s à l'échelle du rayon du moment (le cercle rétrécit)."""
    flat = {"X": {"Min": 90, "Max": 90}}
    edge = _spawner(GREEN_LIFE, "Particles/Textures/Indicators/Warning_Circle_Base.png", {
        "0": {"Opacity": 0.6, "Color": GREEN},
        "15": {"Opacity": 1},
        "85": {"Opacity": 1},
        "100": {"Opacity": 0.6, "Color": GREEN},
    }, {"Opacity": 1, "Rotation": flat, "Scale": {"X": {"Min": BASE, "Max": BASE}}})
    return {f"{GREEN_ZONE}.particlesystem": {
                "$Comment": "Zone favorable (cercle vert de Carnasse) : contour vert, reposé par le Java toutes les 0,5 s. "
                            "Généré par tools/generate_warnings.py.",
                "Spawners": [{"SpawnerId": f"{GREEN_ZONE}_Edge", "PositionOffset": {"Y": 0.03}}],
                "CullDistance": 96,
                "IsImportant": True},
            f"{GREEN_ZONE}_Edge.particlespawner": edge}


def write():
    PARTICLES.mkdir(parents=True, exist_ok=True)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    files = _green_zone_files()
    for t in sorted(set(WARNING_TENTHS) | _wanted):
        files.update(_files(t))
    lines, angles = _shapes_in_use()
    for t in SHAPE_TENTHS:
        for aspect in lines:
            files.update(_line_files(aspect, t))
        for angle in angles:
            files.update(_sector_files(angle, t))
    for old in PARTICLES.iterdir():
        if old.name not in files:
            old.unlink()
    for fname, doc in files.items():
        (PARTICLES / fname).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    for old in TEXTURES.glob("Warning_Line_*.png"):
        old.unlink()   # la ligne prend Warning_Square_Base vanilla (26 octobre 2026)
    for angle in angles:
        base, fill = _sector_textures(angle)
        base.save(TEXTURES / f"Warning_Sector_{angle}_Base.png")
        fill.save(TEXTURES / f"Warning_Sector_{angle}_Fill.png")
    _write_java(lines, angles)
    return sorted(_wanted)


if __name__ == "__main__":
    write()
    print(f"Zones d'annonce écrites dans {PARTICLES}")
