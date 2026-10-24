#!/usr/bin/env python3
"""Génère l'entrée des Fractales des Brumes (étape 2 du GDD, docs/fractales/gdd.md) : le Fragment des Brumes, son
portail, l'instance de l'Observatoire des fractales et son île (la Falaise vient de tools/generate_cliffside.py).

    python3 mods/nakasar-fractals/tools/generate_observatory.py [--preview DOSSIER]

- la clé `PortalKey_Nakasar_Fractal` (« Fragment des Brumes ») : 4 éclats de rune + 1 cœur du Vide à l'établi
  vanilla (recette dans un fichier à part : un id inconnu ne retire que la recette, pas l'objet) ;
- le type de portail et l'instance de l'Observatoire : monde vide (comme Deepworks), ciel des Brumes figé, ni pose
  ni casse de blocs, aucune perte d'objets à la mort ;
- l'île de l'Observatoire, un prefab posé à hauteur fixe dans le vide : parvis d'arrivée et portail de retour au sud,
  l'Astrolabe au centre (console de sélection), le cercle d'harmonisation autour (quatre résonateurs), les
  distributeurs de noyaux et de diapasons à l'entrée du cercle, le golem d'essai et son pupitre à l'ouest, le registre des fractales à l'est ;
- les blocs du décor (textures et icônes dessinées ici), leurs interactions, le golem d'essai, les langues ;
- les objets de sélection : un noyau par fractale, un diapason par niveau (1 à 100), et les deux boutiques de troc
  gratuites des distributeurs ;
- `observatory/ObservatoryLayout.java` : les positions dont le Java a besoin (cercle, golem, cage, préfixes des objets de sélection).

Repère : x vers l'est, z vers le sud, y vers le haut ; le centre de l'Astrolabe est en (0, GROUND_Y, 0), GROUND_Y étant
la première couche d'air au-dessus du dallage. À l'est, le coin de l'Archiviste : comptoir, Autel des infusions,
Creuset des Brumes (leurs objets viennent de tools/generate_progression.py).
"""
import json
import shutil
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_models as fm
import fractal_nature as fn
import generate_block_models as block_models

MOD = Path(__file__).resolve().parent.parent
PACK = MOD / "src" / "main" / "resources"
SERVER = PACK / "Server"
COMMON = PACK / "Common"
JAVA_LAYOUT = MOD / "src/main/java/dev/nakasar/hytale/fractals/observatory/ObservatoryLayout.java"
LANG = "nakasar_fractals"

KEY = "PortalKey_Nakasar_Fractal"
OBSERVATORY = "Nakasar_Fractal_Observatory"
WEATHER = "Nakasar_Fractal_Weather_Mists"
ENVIRONMENT = "Nakasar_Fractal_Env_Mists"
PREFABS = "Nakasar/Fractals"
TEXTURES = "BlockTextures/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"
# Icônes des onglets d'établi : le moteur les veut sous Icons/CraftingCategories (Infusions.png vient de
# generate_progression.py, Fragments.png est l'icône du fragment).
CATEGORY_ICONS = "Icons/CraftingCategories/Nakasar/Fractals"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Fractals"
ITEMS = SERVER / "Item/Items/Deco/Nakasar/Fractals"
SELECTION_ITEMS = SERVER / "Item/Items/Nakasar/Fractals/Selection"
ITEM_MODELS = "Items/Nakasar/Fractals"
GOLEM = "Nakasar_Fractal_Trial_Golem"

# Recette du fragment (GDD, validée par Kevin le 20 octobre 2026) : après le premier donjon vanilla.
KEY_INPUTS = [("Ingredient_Rune_Shard", 4), ("Ingredient_Voidheart", 1)]

GROUND_Y = 100
ISLAND_RADIUS = 30
ASTROLABE_RADIUS = 3          # socle de l'Astrolabe
CIRCLE_INNER, CIRCLE_OUTER = 5, 8   # cercle d'harmonisation (dalles lumineuses)
ARRIVAL = (0, GROUND_Y, 24)   # point d'apparition, sur le parvis au sud
RETURN_PORTAL = (0, 0, 28)    # portail de retour (prefab), derrière le point d'apparition
GOLEM_SPOT = (-19, GROUND_Y, 9)
TRIAL_PANEL = (-15, 0, 7)
TRIAL_CAGE = (-24, 0, 14)     # cage d'essai (bloc Nakasar_Fractal_Cage_Cell)
REGISTRY = (16, 0, 8)
# Coin de l'Archiviste (est, étape 3) : comptoir devant lui, autel des infusions et creuset des Brumes à côté.
ARCHIVIST_SPOT = (18, GROUND_Y, 11)
COUNTER = (16, 0, 11)
DAILY_BOARD = (16, 0, 5)                # tableau des fractales du jour (étape 9), au nord du Registre
ALTAR_SPOT = (13, 0, 13)
FORGE_SPOT = (15, 0, 15)
CAGE_CELL = "Nakasar_Fractal_Cage_Cell"

# Les fractales (GDD) : id (FractalCatalog), nom français, nom anglais, couleur de leur noyau. Une nouvelle fractale ne
# demande qu'une ligne ici (son noyau au distributeur) et son id dans FractalCatalog.
FRACTALS = [
    ("Cliffside", "Falaise", "Cliffside", (176, 120, 210)),
    ("Uncategorized", "Inclassable", "Uncategorized", (232, 150, 200)),
    ("Volcanic", "Volcanique", "Volcanic", (226, 96, 50)),
    ("SolidOcean", "Océan solide", "Solid Ocean", (70, 200, 180)),
    ("Swampland", "Marais", "Swampland", (110, 170, 70)),
    ("Snowblind", "Tempête de neige", "Snowblind", (170, 210, 240)),
]
FLAVOR = {
    "Cliffside": ("Un sentier taillé dans la falaise, le long d'un colosse enchaîné. Cinq sceaux à briser au marteau "
                  "des cultistes, jusqu'à l'Archidevin.",
                  "A path carved into the cliff, along a chained colossus. Five seals to break with the cultists' "
                  "hammer, up to the Archdiviner."),
    "Uncategorized": ("Des plateformes sous les harpies, une prison, un escalier mortel et un Asura qui a perdu la "
                      "raison.", "Platforms under harpies, a prison, a deadly staircase and an Asura who lost his mind."),
    "Volcanic": ("Des vagues de grawls, un couloir à rochers et un chaman nourri par le volcan.",
                 "Waves of grawls, a boulder corridor and a shaman fed by the volcano."),
    "SolidOcean": ("Des plateformes de jade au-dessus d'un océan figé, et l'Abîme de Jade.",
                   "Jade platforms over a frozen ocean, and the Jade Maw."),
    "Swampland": ("Trois feux-follets à guider à travers le marais, le Moussu et Carnasse.",
                  "Three wisps to guide through the swamp, the Mossman and Bloomhunger."),
    "Snowblind": ("Un feu de camp à nourrir dans la tempête, la Source élémentaire et un chaman grawl.",
                  "A campfire to feed in the blizzard, the Elemental Source and a grawl shaman."),
}

# Pierres du décor (ids vanilla de tools/vanilla-block-ids-0.7.2.txt).
FLOOR = ["Rock_Marble_Brick_Smooth", "Rock_Marble_Brick_Smooth", "Rock_Marble_Brick"]
TRIM = "Rock_Gold_Brick_Smooth"
EDGE = "Rock_Quartzite_Brick"
EDGE_TOP = "Rock_Quartzite_Brick_Half"
POST_BASE, POST = "Rock_Quartzite_Brick_Pillar_Base", "Rock_Quartzite_Brick_Pillar_Middle"
LANTERN = "Furniture_Temple_Light_Lantern"
UNDERSIDE = ["Rock_Stone", "Rock_Slate", "Rock_Marble", "Rock_Shale"]
MIST_CRYSTALS = ["Rock_Crystal_Blue_Small", "Rock_Crystal_Purple_Small", "Rock_Crystal_White_Small"]
AIR = "Empty"

# Blocs du mod.
CONSOLE = "Nakasar_Fractal_Selection_Console"
RESONATOR = "Nakasar_Fractal_Resonator"
CORE_DISTRIBUTOR = "Nakasar_Fractal_Core_Distributor"
LEVEL_DISTRIBUTOR = "Nakasar_Fractal_Level_Distributor"
ASTROLABE_RING = "Nakasar_Fractal_Astrolabe_Ring"
HARMONY = "Nakasar_Fractal_Harmony_Tile"
TRIAL = "Nakasar_Fractal_Trial_Panel"
REGISTRY_BLOCK = "Nakasar_Fractal_Registry"
DAILY_BLOCK = "Nakasar_Fractal_Daily_Board"
EXIT_STONE = "Nakasar_Fractal_Exit_Stone"
ALTAR = "Nakasar_Fractal_Infusion_Altar"
FORGE = "Nakasar_Fractal_Mist_Forge"
# Portail des Brumes : arche fabriquée au Creuset et posée chez soi, toujours ouverte vers un Observatoire (sans fragment).
PORTAL = "Nakasar_Fractal_Mists_Portal"
PORTAL_INPUTS = [(KEY, 4), ("Nakasar_Fractal_Mist_Shard", 50)]
PORTAL_HITBOX = SERVER / "Item/Block/Hitboxes/Nakasar/Fractals" / f"{PORTAL}.json"
REWARD_CHEST = "Nakasar_Fractal_Reward_Chest"
COUNTER_BLOCK = "Nakasar_Fractal_Archivist_Counter"
PROGRESS_LANG = "nakasar_fractals_progress"   # langue des objets de tools/generate_progression.py


# Sélection de la fractale (Kevin, 21 octobre 2026 : une arche par fractale ne tient pas à des dizaines de fractales) :
# deux distributeurs donnent le noyau d'une fractale et le diapason d'un niveau, la console de sélection les reçoit et
# harmonise le cercle, le meneur lance depuis un résonateur du cercle.
CORE_SHOP = "Nakasar_Fractal_Cores"
LEVEL_SHOP = "Nakasar_Fractal_Levels"
CORE_PREFIX = "Nakasar_Fractal_Core_"
LEVEL_PREFIX = "Nakasar_Fractal_Level_"
MAX_LEVEL = 100
RANK_SIZE = 25
# Rangs (Observatory.RANKS) : id, métal du diapason (base, reflet), lueur.
LEVEL_RANKS = [("Initiate", (150, 96, 56), (236, 180, 120), (120, 190, 255)),
               ("Adept", (150, 158, 176), (236, 242, 255), (110, 230, 200)),
               ("Expert", (186, 140, 40), (255, 228, 130), (255, 170, 80)),
               ("Master", (96, 60, 150), (210, 170, 255), (255, 110, 200))]
CONSOLE_SPOT = (0, 1, ASTROLABE_RADIUS)    # sur le socle de l'Astrolabe, côté sud
RESONATORS = [(0, 0, CIRCLE_INNER - 1), (CIRCLE_INNER - 1, 0, 0), (0, 0, 1 - CIRCLE_INNER), (1 - CIRCLE_INNER, 0, 0)]
CORE_DISTRIBUTOR_SPOT = (-3, 0, CIRCLE_OUTER + 3)   # de part et d'autre du chemin d'arrivée
LEVEL_DISTRIBUTOR_SPOT = (3, 0, CIRCLE_OUTER + 3)


def core_item(fid):
    return CORE_PREFIX + fid


def level_item(n):
    return f"{LEVEL_PREFIX}{n}"


def level_rank(n):
    return LEVEL_RANKS[min(len(LEVEL_RANKS) - 1, (n - 1) // RANK_SIZE)]


def heading_to_xz(heading, radius):
    """Cap en degrés (0 = nord = -z, 90 = est = +x) vers (x, z) arrondis."""
    a = math.radians(heading)
    return round(math.sin(a) * radius), round(-math.cos(a) * radius)


# --- prefab -------------------------------------------------------------------------------------

# Sens de la face avant (+Z du modèle) pour la rotation k d'un bloc VariantRotation NESW posé en prefab
# (quart de tour k). Non vérifié en jeu : si tous les blocs orientés regardent à 90° du bon côté, échanger
# (1, 0) et (-1, 0).
FRONTS = [(0, 1), (1, 0), (0, -1), (-1, 0)]


class Prefab:
    """Grille creuse de blocs ; la dernière écriture d'une case l'emporte. Blocs d'une seule case seulement (pas de
    meubles sur plusieurs cases : il faudrait écrire leurs remplissages)."""

    def __init__(self):
        self.blocks = {}
        self.fluids = {}      # (x, y, z) -> (fluide, niveau), dans une case d'air (lac de lave du Volcanique)

    def set(self, x, y, z, name, rot=0):
        if name != AIR:
            self.fluids.pop((x, y, z), None)
        self.blocks[(x, y, z)] = (name, rot)

    def fluid(self, x, y, z, name, level=1):
        """Fluide dans une case d'air, comme les sources des prefabs vanilla (Lava_Source, niveau 1)."""
        self.set(x, y, z, AIR)
        self.fluids[(x, y, z)] = (name, level)

    def fill(self, x0, y0, z0, x1, y1, z1, name):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name)

    def solid_at(self, x, y, z):
        name = self.blocks.get((x, y, z), (AIR,))[0]
        return name != AIR

    def orient(self):
        """Tourne les blocs en modèle 3D qui ont une face avant (block_models.ORIENT), sauf rotation donnée :
        "wall" dos au bloc plein voisin, "open" face au côté le plus dégagé, "line" le long des blocs identiques.
        Rotation k = quart de tour k ; la face avant du modèle (+Z) va vers FRONTS[k]."""
        for (x, y, z), (name, rot) in list(self.blocks.items()):
            mode = block_models.ORIENT.get(name)
            if not mode or rot:
                continue
            if mode == "line":
                along_z = self.blocks.get((x, y, z + 1), ("",))[0] == name or \
                    self.blocks.get((x, y, z - 1), ("",))[0] == name
                self.blocks[(x, y, z)] = (name, 1 if along_z else 0)
                continue
            best, best_score = 0, -1
            for k, (dx, dz) in enumerate(FRONTS):
                if mode == "wall":
                    score = 2 * self.solid_at(x - dx, y, z - dz) + (not self.solid_at(x + dx, y, z + dz))
                else:
                    score = sum(not self.solid_at(x + dx * d + dz * w, y + h, z + dz * d + dx * w)
                                for d in range(1, 6) for w in range(-d // 2, d // 2 + 1) for h in (0, 1))
                if score > best_score:
                    best, best_score = k, score
            self.blocks[(x, y, z)] = (name, best)

    def write(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.orient()
        blocks = []
        for (x, y, z), (name, rot) in sorted(self.blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            entry = {"x": x, "y": y, "z": z, "name": name}
            if rot:
                entry["rotation"] = rot
            blocks.append(entry)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write('{\n  "version": 8,\n  "blockIdVersion": 8,\n  "anchorX": 0,\n  "anchorY": 0,\n  "anchorZ": 0,\n')
            f.write('  "blocks": [\n')
            f.write(",\n".join("    " + json.dumps(b, separators=(",", ":")) for b in blocks))
            f.write("\n  ]")
            if self.fluids:
                fluids = [{"x": x, "y": y, "z": z, "name": name, "level": level} for (x, y, z), (name, level)
                          in sorted(self.fluids.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0]))]
                f.write(',\n  "fluids": [\n')
                f.write(",\n".join("    " + json.dumps(e, separators=(",", ":")) for e in fluids))
                f.write("\n  ]")
            f.write("\n}\n")
        return len(blocks)


def pick(options, x, z):
    """Choix déterministe dans `options` selon la case, par plaques lisses (pas de damier ni de hasard : le prefab ne
    change pas d'un tirage à l'autre)."""
    n = fn.vnoise2(x, z, 4.5, len(options) * 7 + 3) * 0.75 + fn.vnoise2(x, z, 1.7, 5) * 0.25
    return options[min(len(options) - 1, int((n + 1) / 2 * len(options)))]


def island(p, radius, depth):
    """Disque dallé de `radius` blocs (dessus en y = -1), dessous en cône de `depth` blocs, garde-corps au bord."""
    for x in range(-radius - 1, radius + 2):
        for z in range(-radius - 1, radius + 2):
            d = math.hypot(x, z)
            if d > radius + 0.5:
                continue
            p.set(x, -1, z, pick(FLOOR, x, z))
            # Dessous : se resserre vers le bas, irrégulier, comme les îles des Brumes de GW2.
            shape = 0.7 + 0.6 * (fn.fbm2(x, z, 5, 2, 3) + 1) / 2
            bottom = -2 - int(depth * (1 - (d / (radius + 0.5)) ** 1.6) * shape)
            for y in range(bottom, -1):
                p.set(x, y, z, fn.DEEP[int((y + 3 * fn.vnoise2(x, z, 11, 4)) // 3) % len(fn.DEEP)])
            if d > radius - 4 and fn.hash01(x, bottom, z, 5) < 0.25:
                for k in range(1 + int(fn.hash01(z, x, 6, 6) * 5)):
                    p.set(x, bottom - 1 - k, z, fn.HANGING[k % 2])
    # Garde-corps : muret de 1,5 bloc, poteaux à lanterne tous les 30 degrés.
    posts = {heading_to_xz(h, radius) for h in range(0, 360, 30)}
    for x in range(-radius - 1, radius + 2):
        for z in range(-radius - 1, radius + 2):
            d = math.hypot(x, z)
            if radius - 0.5 < d <= radius + 0.5:
                if (x, z) in posts:
                    p.set(x, 0, z, POST_BASE)
                    p.set(x, 1, z, POST)
                    p.set(x, 2, z, LANTERN)
                else:
                    p.set(x, 0, z, EDGE)
                    p.set(x, 1, z, EDGE_TOP)


def observatory_prefab():
    p = Prefab()
    island(p, ISLAND_RADIUS, 22)
    # Anneau d'or du cercle d'harmonisation et dalles lumineuses (couleur positive : bleu des Brumes).
    for x in range(-CIRCLE_OUTER - 1, CIRCLE_OUTER + 2):
        for z in range(-CIRCLE_OUTER - 1, CIRCLE_OUTER + 2):
            d = math.hypot(x, z)
            if CIRCLE_INNER - 0.5 <= d < CIRCLE_OUTER + 0.5:
                edge = d < CIRCLE_INNER + 0.5 or d >= CIRCLE_OUTER - 0.5
                p.set(x, -1, z, TRIM if edge else HARMONY)
    # Astrolabe : socle rond, anneaux armillaires (blocs lumineux) et cadran au sommet du socle, côté sud.
    for x in range(-ASTROLABE_RADIUS, ASTROLABE_RADIUS + 1):
        for z in range(-ASTROLABE_RADIUS, ASTROLABE_RADIUS + 1):
            if math.hypot(x, z) <= ASTROLABE_RADIUS + 0.3:
                p.set(x, 0, z, "Rock_Gold_Brick_Ornate" if math.hypot(x, z) > ASTROLABE_RADIUS - 0.7 else "Rock_Gold_Brick")
    p.fill(0, 1, 0, 0, 3, 0, "Rock_Gold_Brick_Pillar_Middle")
    for k in range(-2, 3):           # anneau vertical nord-sud
        p.set(0, 5 + round(math.sqrt(max(0, 4 - k * k))), k, ASTROLABE_RING)
        p.set(0, 5 - round(math.sqrt(max(0, 4 - k * k))), k, ASTROLABE_RING)
    for k in range(-2, 3):           # anneau vertical est-ouest
        p.set(k, 5 + round(math.sqrt(max(0, 4 - k * k))), 0, ASTROLABE_RING)
        p.set(k, 5 - round(math.sqrt(max(0, 4 - k * k))), 0, ASTROLABE_RING)
    p.set(0, 5, 0, "Rock_Crystal_White_Block")
    # Sélection : console sur le socle, quatre résonateurs au bord intérieur du cercle (le meneur lance depuis le
    # cercle), les deux distributeurs à l'entrée du cercle, de part et d'autre du chemin d'arrivée.
    p.set(*CONSOLE_SPOT, CONSOLE)
    for spot in RESONATORS:
        p.set(*spot, RESONATOR)
    for (x, y, z), block, crown in ((CORE_DISTRIBUTOR_SPOT, CORE_DISTRIBUTOR, "Rock_Crystal_Purple_Block"),
                                    (LEVEL_DISTRIBUTOR_SPOT, LEVEL_DISTRIBUTOR, "Rock_Crystal_Blue_Block")):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                p.set(x + dx, -1, z + dz, TRIM if dx == 0 or dz == 0 else "Rock_Gold_Brick_Ornate")
        p.set(x, y, z, block)
        p.set(x, y + 1, z, crown)
    # Parvis d'arrivée au sud : chemin de dalles d'or vers le cercle, portail de retour derrière le point d'apparition.
    for z in range(CIRCLE_OUTER + 1, ISLAND_RADIUS):
        for x in (-1, 0, 1):
            p.set(x, -1, z, TRIM if x == 0 else "Rock_Marble_Brick_Ornate")
    p.fill(-1, 0, RETURN_PORTAL[2] - 1, 1, 3, RETURN_PORTAL[2] + 1, AIR)
    p.set(*RETURN_PORTAL, "Portal_Return")
    # Golem d'essai (ouest) : aire dallée, pupitre de démonstration, cage d'essai fermée par des cristaux.
    gx, _, gz = GOLEM_SPOT
    for x in range(gx - 3, gx + 4):
        for z in range(gz - 3, gz + 4):
            if math.hypot(x - gx, z - gz) <= 3.4:
                p.set(x, -1, z, "Rock_Quartzite_Brick_Decorative")
    p.set(*TRIAL_PANEL, TRIAL)
    cx, _, cz = TRIAL_CAGE
    for x in range(cx - 1, cx + 2):
        for z in range(cz - 1, cz + 2):
            p.set(x, -1, z, "Rock_Gold_Brick")
            p.set(x, 3, z, "Rock_Gold_Brick")
            if (x, z) != (cx, cz):
                for y in (0, 1, 2):
                    p.set(x, y, z, "Rock_Crystal_Red_Block" if y == 1 else "Rock_Gold_Brick_Pillar_Middle")
    p.set(cx, 0, cz, CAGE_CELL)
    p.set(cx, 1, cz, AIR)
    p.set(cx, 2, cz, AIR)
    # Registre des fractales (est) : là où se tiendra l'Archiviste.
    p.set(*REGISTRY, REGISTRY_BLOCK)
    assert DAILY_BOARD not in p.blocks, "le tableau des fractales du jour tombe sur un bloc"
    p.set(*DAILY_BOARD, DAILY_BLOCK)
    # Coin de l'Archiviste : dallage, comptoir, autel des infusions et creuset des Brumes.
    ax, _, az = ARCHIVIST_SPOT
    for x in range(ax - 6, ax + 2):
        for z in range(az - 2, az + 6):
            if math.hypot(x, z) <= ISLAND_RADIUS - 3:
                p.set(x, -1, z, "Rock_Quartzite_Brick_Decorative")
    p.set(*COUNTER, COUNTER_BLOCK)
    p.set(*ALTAR_SPOT, ALTAR)
    p.set(*FORGE_SPOT, FORGE)
    # Cristaux de Brume semés sur le pourtour (décor).
    for k, h in enumerate(range(15, 360, 30)):
        x, z = heading_to_xz(h, ISLAND_RADIUS - 2)
        if p.blocks.get((x, 0, z), (AIR,))[0] == AIR:
            p.set(x, 0, z, MIST_CRYSTALS[k % len(MIST_CRYSTALS)])
    gardens(p)
    return p


def gardens(p):
    """Jardins des Brumes hors du garde-corps (glycines, arbres bleus, fleurs froides, cristaux) et îles flottantes
    tout autour, comme le décor de l'Observatoire de GW2."""
    theme = fn.THEMES["mists"]
    plaza = {(x, z): -1 for (x, y, z) in p.blocks if y == -1}
    tops = fn.rim(plaza, 4, 14, seed=91)
    cells = fn.natural_ground(p, tops, theme, seed=91, depth=(4, 1.3, 20), trees=0.05, spacing=6, flowers=0.2)
    for x, y, z in cells:
        if fn.hash01(x, y, z, 92) < 0.015 and fn.free(p, x, y + 1, z):
            p.set(x, y + 1, z, MIST_CRYSTALS[int(fn.hash01(z, x, y, 93) * len(MIST_CRYSTALS))])
    fn.scatter_islets(p, (-120, 120, -120, 120), 22, (-40, 25), (3, 11), theme, seed=95, margin=16)


# --- blocs, textures, icônes ------------------------------------------------------------------------

def texture(path, base, accent, glyph):
    img = Image.new("RGBA", (32, 32), base + (255,))
    d = ImageDraw.Draw(img)
    dark = tuple(int(c * 0.7) for c in base) + (255,)
    d.rectangle((0, 0, 31, 31), outline=dark)
    d.rectangle((2, 2, 29, 29), outline=tuple(min(255, int(c * 1.1)) for c in base) + (255,))
    acc = accent + (255,)
    if glyph == "ring":
        d.ellipse((6, 6, 25, 25), outline=acc, width=3)
    elif glyph == "tile":
        d.rectangle((6, 6, 25, 25), outline=acc, width=1)
        d.polygon(((16, 8), (24, 16), (16, 24), (8, 16)), outline=acc)
        d.ellipse((14, 14, 17, 17), fill=acc)
    elif glyph == "panel":
        d.rectangle((7, 7, 24, 24), outline=acc, width=2)
        d.ellipse((12, 12, 19, 19), outline=acc, width=2)
    elif glyph == "daily":
        for k, y in enumerate((8, 16, 24)):
            d.polygon(((9, y), (12, y - 3), (15, y), (12, y + 3)), fill=acc if k == 0 else None, outline=acc)
            d.line((18, y, 25, y), fill=acc, width=2)
    elif glyph == "book":
        d.rectangle((7, 6, 24, 25), fill=accent + (255,))
        d.line((16, 6, 16, 25), fill=dark, width=1)
        for y in (10, 14, 18):
            d.line((9, y, 14, y), fill=dark)
            d.line((18, y, 23, y), fill=dark)
    elif glyph == "altar":
        for k in range(3):
            for j in range(4):
                d.rectangle((6 + j * 5, 7 + k * 6, 9 + j * 5, 10 + k * 6), outline=acc)
        d.ellipse((13, 13, 18, 18), fill=acc)
    elif glyph == "forge":
        d.polygon(((8, 12), (24, 12), (21, 25), (11, 25)), outline=acc, fill=dark)
        d.ellipse((12, 6, 20, 13), fill=acc)
    elif glyph == "chest":
        d.rectangle((6, 10, 25, 25), outline=acc, width=2)
        d.line((6, 15, 25, 15), fill=acc, width=2)
        d.rectangle((14, 13, 17, 18), fill=acc)
    elif glyph == "counter":
        d.rectangle((5, 8, 26, 12), fill=acc)
        d.line((8, 12, 8, 26), fill=acc, width=2)
        d.line((23, 12, 23, 26), fill=acc, width=2)
        d.ellipse((13, 16, 18, 21), outline=acc)
    elif glyph == "console":
        d.rectangle((4, 9, 14, 22), outline=acc, width=2)
        d.rectangle((17, 9, 27, 22), outline=acc, width=2)
        d.polygon(((9, 12), (12, 16), (9, 20), (6, 16)), fill=acc)
        d.line((22, 12, 22, 20), fill=acc, width=2)
        d.line((5, 26, 26, 26), fill=acc)
    elif glyph == "resonator":
        for r in (12, 8, 4):
            d.ellipse((16 - r, 16 - r, 15 + r, 15 + r), outline=acc, width=1 if r > 4 else 2)
        for k in range(4):
            a = math.radians(45 + k * 90)
            d.line((16 + math.cos(a) * 9, 16 + math.sin(a) * 9, 16 + math.cos(a) * 14, 16 + math.sin(a) * 14),
                   fill=acc, width=2)
    elif glyph == "dispenser":
        d.rectangle((8, 5, 23, 17), outline=acc, width=2)
        d.polygon(((16, 7), (20, 11), (16, 15), (12, 11)), fill=acc)
        d.rectangle((11, 21, 20, 26), outline=acc, width=2)
        d.line((16, 18, 16, 21), fill=acc, width=2)
    elif glyph == "exit":
        d.ellipse((7, 7, 24, 24), outline=acc, width=3)
        d.polygon(((13, 11), (21, 16), (13, 21)), fill=acc)
    img.save(path)
    return img


def icon(path, tex):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    img.alpha_composite(tex.resize((48, 48), Image.NEAREST), (8, 8))
    img.save(path)


def block_item(name, tex, light=None, interaction=None, solid=True, quality="Technical", particle="#9aa7c8"):
    block = {
        "Material": "Solid" if solid else "Empty",
        "DrawType": "Cube",
        "Opacity": "Solid",
        "Textures": [{"Sides": f"{TEXTURES}/{tex}.png", "UpDown": f"{TEXTURES}/{tex}.png", "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
        "BlockParticleSetId": "Stone",
        "BlockSoundSetId": "Stone",
        "ParticleColor": particle,
    }
    if light:
        block["Light"] = {"Color": light}
    if interaction:
        block["Interactions"] = {"Use": {"Interactions": [interaction]}}
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{name}.name", "Description": f"{LANG}.items.{name}.description"},
        "Icon": f"{ICONS}/{tex}.png",
        "Categories": ["Blocks.Deco"],
        "Quality": quality,
        "PlayerAnimationsId": "Block",
        "BlockType": block,
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    }


def bench_item(name, tex):
    """Creuset des Brumes : établi en cube (fusion des infusions, fragment refait), cassable pour l'emporter."""
    doc = block_item(name, tex, light="#a8f", quality="Rare", particle="#8a6ad8")
    doc["Categories"] = ["Furniture.Benches"]
    doc["Tags"] = {"Type": ["Bench"]}
    doc["MaxStack"] = 1
    block = doc["BlockType"]
    block["Gathering"] = {"Breaking": {"GatherType": "Benches", "ItemId": name}}
    block["BlockEntity"] = {"Components": {"BenchBlock": {}}}
    block["State"] = {"Definitions": {"CraftCompleted": {"Looping": True}, "CraftCompletedInstant": {}}}
    block["Bench"] = {
        "Type": "Crafting",
        "Id": name,
        "LocalOpenSoundEventId": "SFX_Weapon_Bench_Open",
        "LocalCloseSoundEventId": "SFX_Weapon_Bench_Close",
        "CompletedSoundEventId": "SFX_Weapon_Bench_Craft",
        "Categories": [
            {"Id": "Nakasar_Fractal_Infusions", "Name": f"{PROGRESS_LANG}.benchCategories.nakasar_fractal_infusions",
             "Icon": f"{CATEGORY_ICONS}/Infusions.png"},
            {"Id": "Nakasar_Fractal_Fragments", "Name": f"{PROGRESS_LANG}.benchCategories.nakasar_fractal_fragments",
             "Icon": f"{CATEGORY_ICONS}/Fragments.png"},
        ],
    }
    return doc


def portable(doc, name):
    """Bloc fabricable (autel) : se casse et se rend, pour le poser chez soi."""
    doc["BlockType"]["Gathering"] = {"Breaking": {"GatherType": "Benches", "ItemId": name}}
    doc["Quality"] = "Rare"
    doc["MaxStack"] = 1
    return doc


def portal_item():
    """Portail des Brumes : arche de 3 × 4 blocs (cases de remplissage posées par le moteur selon la hitbox), traversable.
    La traverser mène à l'Observatoire du portail (TeleportInstance, comme la déchirure du mod Vampires) : le moteur garde
    l'instance sur le bloc et en rouvre une quand l'ancienne a fermé. Retour devant l'arche, en diagonale pour ne pas
    retomber dans la hitbox quelle que soit la rotation."""
    doc = portable(block_item(PORTAL, "Mists_Portal", "#a8f", particle="#a87ae8"), PORTAL)
    doc["Quality"] = "Epic"
    block = doc["BlockType"]
    block["Material"] = "Empty"
    block["HitboxType"] = PORTAL
    block["Interactions"] = {"CollisionEnter": {"Interactions": [{
        "Type": "TeleportInstance",
        "InstanceName": OBSERVATORY,
        "PersonalReturnPoint": True,
        "CloseOnBlockRemove": True,
        "OriginSource": "Block",
        "PositionOffset": {"X": 2.5, "Y": 0, "Z": 2.5},
        "Next": {"Type": "Simple", "Effects": {"LocalSoundEventId": "SFX_Portal_Neutral_Teleport_Local"}},
    }]}}
    return doc


def portal_hitbox():
    return {"Boxes": [{"Min": {"X": -1.0, "Y": 0.0, "Z": 0.375}, "Max": {"X": 2.0, "Y": 4.0, "Z": 0.625}}]}


def portal_recipe():
    return {
        "TimeSeconds": 6,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": k, "Quantity": q} for k, q in PORTAL_INPUTS],
        "PrimaryOutput": {"ItemId": PORTAL, "Quantity": 1},
        "Output": [{"ItemId": PORTAL, "Quantity": 1}],
        "BenchRequirement": [{"Type": "Crafting", "Id": FORGE, "Categories": ["Nakasar_Fractal_Fragments"],
                              "RequiredTierLevel": 1}],
    }


def hexcolor(rgb):
    return "#%02x%02x%02x" % rgb


# --- assets JSON ---------------------------------------------------------------------------------

def key_item():
    return {
        "Parent": "PortalKey_Taiga",
        "TranslationProperties": {"Name": f"{LANG}.items.{KEY}.name", "Description": f"{LANG}.items.{KEY}.description"},
        "Icon": f"{ICONS}/PortalKey_Fractal.png",
        "Quality": "Epic",
        "PortalKey": {"PortalType": OBSERVATORY, "TimeLimitSeconds": -1},
    }


def key_recipe():
    return {
        "TimeSeconds": 4,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": k, "Quantity": q} for k, q in KEY_INPUTS],
        "PrimaryOutput": {"ItemId": KEY, "Quantity": 1},
        "Output": [{"ItemId": KEY, "Quantity": 1}],
        "BenchRequirement": [{"Type": "Crafting", "Id": "Workbench", "Categories": ["Workbench_Crafting"],
                              "RequiredTierLevel": 1}],
    }


def portal_type():
    return {
        "InstanceId": OBSERVATORY,
        "GameplayConfig": OBSERVATORY,
        "Description": {
            "DisplayName": f"{LANG}.portal.name",
            "FlavorText": f"{LANG}.portal.flavor",
            "ThemeColor": "#4a7ad8",
            "DescriptionTags": [
                {"TranslationKey": f"{LANG}.portal.tag.hub", "Color": "#4a7ad8"},
                {"TranslationKey": f"{LANG}.portal.tag.group", "Color": "#2980b9"},
            ],
            "Objectives": [f"{LANG}.portal.objective"],
        },
        "Spawn": {
            # Le portail de retour est dans le prefab, derrière le point d'arrivée (pas dessus : voir le mod Vampires,
            # un joueur dont l'écran charge encore repartirait aussitôt).
            "SpawnReturnPortal": False,
            "SpawnProviderOverride": {"Id": "Global", "SpawnPoint": {"X": ARRIVAL[0] + 0.5, "Y": float(ARRIVAL[1]),
                                                                     "Z": ARRIVAL[2] + 0.5, "Yaw": 0.0}},
        },
        "TimeLimitSeconds": -1,
        "AllowedEntryCount": 0,
        "CloseWhenEmpty": True,
        "VoidInvasionEnabled": False,
        "AllowPlayersToLeaveViaMap": True,
    }


def gameplay_config():
    return {
        "Parent": "Default",
        "World": {"AllowBlockGathering": False, "AllowBlockPlacement": False, "AllowBlockBreaking": False,
                  "BlockedRootInteractionTags": ["Type=Rail_Kart", "Type=Bed"]},
        "Plugin": {"Portal": {}, "WorldEvents": {}},
        "Death": {"ItemsLossMode": "None", "ItemsAmountLossPercentage": 0, "ItemsDurabilityLossPercentage": 0},
        "WorldMap": {"DisplayDeathMarker": False},
    }


def weather():
    """Ciel des Brumes de GW2 : bleu nuit en haut, violet et turquoise à l'horizon, brume épaisse au loin."""
    hours = lambda pairs: [{"Hour": h, "Color": c} for h, c in pairs]
    return {
        "FogDistance": [-20, 220],
        "FogColors": hours([(0, "#141838"), (12, "#3a4a80"), (18, "#3a2a6a")]),
        "FogDensities": [{"Hour": 0, "Value": 0.5}, {"Hour": 12, "Value": 0.4}],
        "SkyTopColors": hours([(0, "#080a26ff"), (12, "#22306aff"), (18, "#1c1048ff")]),
        "SkyBottomColors": hours([(0, "#2a1a5aff"), (12, "#5a80c8ff"), (18, "#7a4ab0ff")]),
        "SkySunsetColors": hours([(0, "#00000000"), (18, "#c070e0a0"), (21, "#00000000")]),
        "SunlightColors": hours([(0, "#5a5aa8"), (12, "#c8d0f0"), (18, "#a890d8")]),
        "SunColors": hours([(0, "#ffffff"), (18, "#d8a0ff")]),
        "MoonColors": hours([(0, "#e0e8ffff"), (12, "#e0e8ffff")]),
        "MoonGlowColors": hours([(0, "#7aa0ff60"), (12, "#7aa0ff60")]),
        "WaterTints": hours([(0, "#1a2a5a"), (12, "#3a5a9a")]),
    }


def environment():
    return {
        "$Comment": "Brumes de l'Observatoire et des fractales : pas d'apparitions naturelles, ciel figé des Brumes.",
        "Parent": "Env_Zone1_Plains",
        "SpawnDensity": 0.0,
        "BlockModificationAllowed": False,
        "WaterTint": "#3a5a9a",
        "WeatherForecastSeed": ENVIRONMENT,
        "WeatherForecasts": {str(h): [{"WeatherId": WEATHER, "Weight": 1}] for h in range(24)},
    }


def instance(name, display, structure, portal=True, spawn=ARRIVAL, removal=300, weather=WEATHER, time="18:00"):
    """Instance figée à l'heure `time` sous le temps `weather` (par défaut le crépuscule des Brumes)."""
    doc = {
        "DisplayName": display,
        "WorldGen": {"Type": "HytaleGenerator", "WorldStructure": structure},
        "ForcedWeather": weather,
        "GameTime": f"0001-01-01T{time}:00Z",
        "IsGameTimePaused": True,
        "GameplayConfig": OBSERVATORY,
        "IsPvpEnabled": False,
        "IsSpawningNPC": True,
        "SpawnProvider": {"Id": "Global", "SpawnPoint": {"X": spawn[0] + 0.5, "Y": float(spawn[1]), "Z": spawn[2] + 0.5,
                                                         "Pitch": 0, "Yaw": 0, "Roll": 0}},
        "GameMode": "Adventure",
        "IsSpawnMarkersEnabled": True,
        "IsBlockSpawnersEnabled": True,
        "IsSavingPlayers": True,
        "DeleteOnRemove": True,
        # Vide pendant que le groupe est en fractale : il revient ensuite au même Observatoire (retiré au bout de
        # `removal` secondes ; le jeu en rouvre un neuf si le groupe revient plus tard).
        "Plugin": {"Instance": {"RemovalConditions": [{"Type": "WorldEmpty", "TimeoutSeconds": removal}]}},
    }
    if portal:
        doc["Plugin"]["PortalWorldConfig"] = {"Config": {"PortalType": OBSERVATORY, "TimeLimitSeconds": -1}}
    return doc


def biome(name, prefab):
    """Monde vide : aucune densité, le prefab posé à hauteur fixe porte toute l'île."""
    return {
        "Name": name,
        "Terrain": {"Type": "DAOTerrain", "Density": {"Type": "Constant", "Value": -1.0}},
        "MaterialProvider": {"Type": "Constant", "Material": {"Solid": "Empty"}},
        "Props": [{
            "Runtime": 0,
            "ContextPrecision": "Prop",
            "PropDistribution": {
                "Type": "Assigned",
                "OverrideAllProps": True,
                "PropDistribution": {"Type": "Positions", "Positions": {"Type": "List", "Positions": [
                    {"X": 0, "Y": GROUND_Y, "Z": 0}]}},
                "Assignments": {"Type": "Constant", "Prop": {"Type": "Prefab", "WeightedPrefabPaths": [
                    {"Path": f"{PREFABS}/{prefab}", "Weight": 1.0}]}},
            },
        }],
        "EnvironmentProvider": {"Type": "Constant", "Environment": ENVIRONMENT},
        "TintProvider": {"Type": "Constant", "Color": "#5aa86a"},
    }


def world_structure(biome_name, spawn):
    return {
        "Type": "NoiseRange",
        "DefaultBiome": biome_name,
        "DefaultTransitionDistance": 16,
        "MaxBiomeEdgeDistance": 0,
        "Density": {"Type": "Constant", "Value": 0.0},
        "Biomes": [],
        "SpawnPositions": {"Type": "List", "Positions": [{"X": spawn[0], "Y": spawn[1], "Z": spawn[2]}]},
    }


def interactions():
    out = {
        "Nakasar_Fractal_Use_Console": {
            "$Comment": "Console de sélection : ses deux emplacements (noyau de fractale, diapason de niveau), partagés "
                        "par tout l'Observatoire. Les deux posés, le cercle est harmonisé.",
            "Type": "Nakasar_Fractal_OpenConsole"},
        "Nakasar_Fractal_Use_Resonator": {
            "$Comment": "Résonateur du cercle : le meneur envoie le cercle harmonisé dans la fractale de la console.",
            "Type": "Nakasar_Fractal_Harmonize"},
        "Nakasar_Fractal_Use_Core_Distributor": {
            "$Comment": "Distributeur des noyaux : un noyau par fractale, gratuit (boutique de troc sans prix).",
            "Type": "Nakasar_Fractal_OpenShop", "Shop": CORE_SHOP},
        "Nakasar_Fractal_Use_Level_Distributor": {
            "$Comment": "Distributeur des diapasons : un diapason par niveau (1 à 100), gratuit.",
            "Type": "Nakasar_Fractal_OpenShop", "Shop": LEVEL_SHOP},
        "Nakasar_Fractal_Use_Trial_Panel": {
            "$Comment": "Pupitre du golem d'essai : le golem rejoue sur le joueur les attaques annoncées du mod "
                        "(cercle, cône, ligne, puis la cage), pour les voir et les tester.",
            "Type": "Nakasar_Fractal_TrialDemo"},
        "Nakasar_Fractal_Use_Exit": {
            "$Comment": "Pierre de retour d'une fractale : ramène le joueur à l'Observatoire.",
            "Type": "Nakasar_Fractal_Leave"},
        "Nakasar_Fractal_Use_Infusion_Altar": {
            "$Comment": "Autel des infusions : ouvre les 12 emplacements d'infusion du joueur (portés par lui).",
            "Type": "Nakasar_Fractal_OpenInfusions"},
        "Nakasar_Fractal_Use_Reward_Chest": {
            "$Comment": "Coffre de fin de fractale : un coffre par joueur du groupe, et le niveau suivant débloqué.",
            "Type": "Nakasar_Fractal_ClaimReward"},
        "Nakasar_Fractal_Use_Archivist_Counter": {
            "$Comment": "Comptoir de l'Archiviste : sa boutique de troc (comme lui parler).",
            "Type": "Nakasar_Fractal_OpenShop", "Shop": "Nakasar_Fractal_Archivist"},
        "Nakasar_Fractal_Use_Daily_Board": {
            "$Comment": "Tableau des fractales du jour : les trois fractales du jour, cochées si le joueur a déjà pris "
                        "leur coffre aujourd'hui.",
            "Type": "Nakasar_Fractal_DailyBoard"},
        "Nakasar_Fractal_Read_Registry": {
            "$Comment": "Registre des fractales : page de lore du jeu (nom et description du bloc).",
            "Type": "OpenCustomUI", "Page": {"Id": "BlockLore", "TextAlignment": "Left"}},
    }
    return out


def golem_model():
    return {
        "$Comment": "Golem d'essai de l'Observatoire : le golem d'acier vanilla (Golem_Firesteel), sans ses flammes, "
                    "lueur bleue des Brumes.",
        "Parent": "Golem_Firesteel",
        "Particles": [],
        "Light": {"Color": "#6a8aff", "Radius": 2},
    }


def golem_role():
    """Mannequin immobile : ne riposte pas, encaisse tout (le Java lui rend ses PV et annonce les dégâts)."""
    return {
        "$Comment": "Golem d'essai de l'Observatoire : posé par TrialGolemSystem, immobile, ne riposte jamais. Les "
                    "dégâts reçus sont annoncés au joueur et ses PV remontent après chaque série de coups. Son pupitre "
                    "lui fait rejouer les attaques annoncées du mod. Généré par tools/generate_observatory.py.",
        "Type": "Generic",
        "Appearance": GOLEM,
        "NameTranslationKey": f"{LANG}.npc.Trial_Golem.name",
        "MaxHealth": 100000,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "DeathAnimationTime": 1.0,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
    }


# --- objets de sélection : noyaux, diapasons, distributeurs ---------------------------------------

GOLD, GOLD_LIGHT = (186, 140, 40), (255, 228, 130)


def core_parts(color):
    dark, light = fm.shade(color, 0.42), fm.mix(color, (255, 255, 255), 0.55)
    return [
        ("Core", (0, 6.5, 0), (5, 9, 5), 45, fm.crystal(dark, light), "fullbright"),
        ("Core_Shard_A", (2.6, 4.5, 1), (2, 5, 2), 20, fm.crystal(dark, color), "fullbright"),
        ("Core_Shard_B", (-2.4, 4, -1), (2, 4, 2), -35, fm.crystal(dark, color), "fullbright"),
        ("Setting", (0, 1, 0), (7, 2, 7), 0, fm.smooth(GOLD, GOLD_LIGHT), "flat"),
        ("Setting_Rim", (0, 2.5, 0), (8, 1, 8), 45, fm.smooth(GOLD, GOLD_LIGHT), "flat"),
    ]


def fork_parts(metal, light, glow):
    paint = fm.smooth(metal, light)
    return [
        ("Handle", (0, 3, 0), (2, 6, 2), 0, paint, "flat"),
        ("Pommel", (0, 0.5, 0), (3, 1, 3), 45, fm.flat(glow), "fullbright"),
        ("Bow", (0, 6.5, 0), (7, 1.5, 2), 0, paint, "flat"),
        ("Prong_W", (-2.75, 10.5, 0), (1.5, 7, 1.5), 0, paint, "flat"),
        ("Prong_E", (2.75, 10.5, 0), (1.5, 7, 1.5), 0, paint, "flat"),
        ("Note", (0, 11.5, 0), (2, 2, 2), 45, fm.flat(glow), "fullbright"),
    ]


# Chiffres 3×5 pour le numéro des icônes de diapason.
DIGITS = {"0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
          "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001010010010",
          "8": "111101111101111", "9": "111101111001111"}


def number_icon(base, n, glow):
    """Icône du diapason avec son niveau en bas à droite (chiffres pixel, contour sombre)."""
    img = base.copy()
    d = ImageDraw.Draw(img)
    text, cell = str(n), 3
    w = len(text) * 4 * cell - cell
    x0, y0 = 62 - w, 62 - 5 * cell
    for pass_, fill in ((0, (16, 12, 30, 255)), (1, fm.mix(glow, (255, 255, 255), 0.5) + (255,))):
        for k, ch in enumerate(text):
            for i, bit in enumerate(DIGITS[ch]):
                if bit == "1":
                    x, y = x0 + (k * 4 + i % 3) * cell, y0 + (i // 3) * cell
                    pad = 1 if pass_ == 0 else 0
                    d.rectangle((x - pad, y - pad, x + cell - 1 + pad, y + cell - 1 + pad), fill=fill)
    return img


def selection_item(item_id, model, icon_name, quality):
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
        "Icon": f"{ICONS}/{icon_name}.png",
        "Model": f"{ITEM_MODELS}/{model}.blockymodel",
        "Texture": f"{ITEM_MODELS}/{model}.png",
        "Quality": quality,
        "Categories": ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
    }


def free_shop(name_key, items):
    """Boutique de troc sans prix (Input vide) : un distributeur."""
    return {
        "DisplayNameKey": name_key,
        "RefreshInterval": {"Days": 1},
        "Trades": [{"Output": {"ItemId": i, "Quantity": 1}, "Input": [], "Stock": 999} for i in items],
    }


def selection_items():
    """Noyaux et diapasons (modèles, icônes, objets) et les deux boutiques des distributeurs ; rend les icônes."""
    models, icons = COMMON / ITEM_MODELS, COMMON / ICONS
    for old in SELECTION_ITEMS.glob("*.json") if SELECTION_ITEMS.exists() else []:
        old.unlink()
    for old in icons.glob("Level_*.png"):
        if old.stem[len("Level_"):].isdigit():   # pas l'icône du distributeur
            old.unlink()
    rendered = []
    for k, (fid, _, _, color) in enumerate(FRACTALS):
        model = f"Core_{fid}"
        rendered.append(fm.write_item_model(model, core_parts(color), models, icons, 300 + k, (0, 5, 0), 13.0))
        write_json(SELECTION_ITEMS / f"{core_item(fid)}.json", selection_item(core_item(fid), model, model, "Rare"))
    rank_icons = {}
    for rid, metal, light, glow in LEVEL_RANKS:
        model = f"Level_Fork_{rid}"
        rank_icons[rid] = fm.write_item_model(model, fork_parts(metal, light, glow), models, icons, 320, (0, 7, 0), 10.5)
        (icons / f"{model}.png").unlink()   # chaque niveau a son icône numérotée
    for n in range(1, MAX_LEVEL + 1):
        rid, _, _, glow = level_rank(n)
        img = number_icon(rank_icons[rid], n, glow)
        img.save(icons / f"Level_{n}.png")
        if n % RANK_SIZE == 1:
            rendered.append(img)
        quality = {"Initiate": "Uncommon", "Adept": "Rare", "Expert": "Epic", "Master": "Legendary"}[rid]
        write_json(SELECTION_ITEMS / f"{level_item(n)}.json",
                   selection_item(level_item(n), f"Level_Fork_{rid}", f"Level_{n}", quality))
    write_json(SERVER / "BarterShops" / f"{CORE_SHOP}.json",
               free_shop(f"{LANG}.shop.{CORE_SHOP}.name", [core_item(fid) for fid, *_ in FRACTALS]))
    write_json(SERVER / "BarterShops" / f"{LEVEL_SHOP}.json",
               free_shop(f"{LANG}.shop.{LEVEL_SHOP}.name", [level_item(n) for n in range(1, MAX_LEVEL + 1)]))
    return rendered


# --- langues ------------------------------------------------------------------------------------

def lang():
    fr = {
        "items.Nakasar_Fractal_Cage_Cell.name": "Cage de fractale (cible de l'emprisonnement)",
        f"items.{KEY}.name": "Fragment des Brumes",
        f"items.{KEY}.description": "Un éclat des Brumes, figé dans la pierre runique. Posé dans l'Ancienne passerelle, "
                                    "il ouvre l'Observatoire des fractales.",
        "portal.name": "Observatoire des fractales",
        "portal.flavor": "Une île suspendue dans les Brumes, d'où l'on part vers les fractales.",
        "portal.tag.hub": "Brumes",
        "portal.tag.group": "1 à 5 joueurs",
        "portal.objective": "Harmoniser le cercle à la console de sélection et partir en fractale",
        f"items.{CONSOLE}.name": "Console de sélection",
        f"items.{CONSOLE}.description": "Utiliser : y poser le noyau d'une fractale et le diapason d'un niveau. Les "
                                        "deux posés, le cercle d'harmonisation s'accorde sur cette fractale.",
        f"items.{RESONATOR}.name": "Résonateur d'harmonisation",
        f"items.{RESONATOR}.description": "Utiliser (meneur) : le cercle harmonisé part pour la fractale de la console.",
        f"items.{CORE_DISTRIBUTOR}.name": "Distributeur de noyaux",
        f"items.{CORE_DISTRIBUTOR}.description": "Utiliser : prendre le noyau d'une fractale, gratuit.",
        f"items.{LEVEL_DISTRIBUTOR}.name": "Distributeur de diapasons",
        f"items.{LEVEL_DISTRIBUTOR}.description": "Utiliser : prendre le diapason d'un niveau (1 à 100), gratuit.",
        f"shop.{CORE_SHOP}.name": "Noyaux de fractale",
        f"shop.{LEVEL_SHOP}.name": "Diapasons de niveau",
        "observatory.harmonized.title": "Harmonisation : {fractal}",
        "observatory.harmonized.subtitle": "Niveau {level}, rang {rank}",
        "observatory.harmonized.lost": "La console n'est plus harmonisée : il lui faut un noyau et un diapason.",
        "observatory.notHarmonized": "Posez d'abord un noyau de fractale et un diapason de niveau dans la console de "
                                     "sélection.",
        f"items.{ASTROLABE_RING}.name": "Anneau de l'Astrolabe",
        f"items.{ASTROLABE_RING}.description": "Anneau armillaire de l'Astrolabe.",
        f"items.{HARMONY}.name": "Dalle d'harmonisation",
        f"items.{HARMONY}.description": "Les joueurs debout sur le cercle forment le groupe (5 au plus).",
        f"items.{TRIAL}.name": "Pupitre du golem d'essai",
        f"items.{TRIAL}.description": "Utiliser : le golem rejoue sur vous les attaques des fractales.",
        f"items.{PORTAL}.name": "Portail des Brumes",
        f"items.{PORTAL}.description": "Arche à poser chez soi, toujours ouverte : la traverser mène à l'Observatoire "
                                       "des fractales, sans Fragment des Brumes. Se casse et se reprend.",
        f"items.{EXIT_STONE}.name": "Pierre de retour",
        f"items.{EXIT_STONE}.description": "Utiliser : retour à l'Observatoire.",
        f"items.{ALTAR}.name": "Autel des infusions",
        f"items.{ALTAR}.description": "Utiliser : vos 12 emplacements d'infusion. Chaque infusion posée ajoute sa "
                                      "résistance à l'agonie, où que vous soyez ; la retirer l'enlève.",
        f"items.{FORGE}.name": "Creuset des Brumes",
        f"items.{FORGE}.description": "Fusionne deux infusions identiques en la suivante, et refait un Fragment des "
                                      "Brumes avec des éclats.",
        f"items.{REWARD_CHEST}.name": "Coffre de fin de fractale",
        f"items.{REWARD_CHEST}.description": "Utiliser : votre récompense (une par joueur du groupe). Terminer une "
                                             "fractale à votre plus haut niveau débloque le suivant.",
        f"items.{COUNTER_BLOCK}.name": "Comptoir de l'Archiviste",
        f"items.{COUNTER_BLOCK}.description": "Utiliser : échanger des éclats de Brume contre des infusions, des "
                                              "fragments et les cosmétiques de saison.",
        f"items.{DAILY_BLOCK}.name": "Tableau des fractales du jour",
        f"items.{DAILY_BLOCK}.description": "Utiliser : les trois fractales du jour. Terminer l'une d'elles donne, la "
                                            "première fois du jour, un coffre des fractales du jour en plus.",
        f"items.{REGISTRY_BLOCK}.name": "Registre des fractales",
        f"items.{REGISTRY_BLOCK}.description": (
            "Bienvenue dans l'Observatoire, voyageur des Brumes.\n\n"
            "1. Prenez le noyau d'une fractale et le diapason d'un niveau aux deux distributeurs, à l'entrée du cercle.\n"
            "2. Posez-les dans la console de sélection, sur l'Astrolabe : le cercle s'harmonise sur cette fractale.\n"
            "3. Montez sur le cercle d'harmonisation : les joueurs qui s'y tiennent forment le groupe, cinq au plus. "
            "Le premier arrivé dans l'Observatoire le mène.\n"
            "4. Le meneur utilise un résonateur du cercle : tout le cercle part.\n\n"
            "Saison 1 : Falaise, Inclassable, Volcanique, Océan solide, Marais, Tempête de neige.\n"
            "Le golem d'essai, à l'ouest, sert à tester ses coups, sa résistance à l'agonie et à voir les attaques "
            "des fractales.\n"
            "À l'est, l'Archiviste échange les éclats de Brume ; l'Autel des infusions porte votre résistance à "
            "l'agonie et le Creuset des Brumes fusionne les infusions.\n"
            "Chaque fractale terminée à votre plus haut niveau débloque le suivant ; le meneur ne peut choisir qu'un "
            "niveau qu'il a débloqué.\n\n"
            "Commande de secours : /fractale (niveau, groupe, lancer, quitter, infos)."),
        "npc.Trial_Golem.name": "Golem d'essai",
        "observatory.leader": "Vous menez le groupe de l'Observatoire.",
        "observatory.newLeader": "{name} mène désormais le groupe.",
        "observatory.joined": "Harmonisé avec le groupe ({count}/5).",
        "observatory.left": "Vous quittez le cercle d'harmonisation.",
        "observatory.full": "Le cercle d'harmonisation est complet (5 joueurs).",
        "observatory.level.title": "Niveau {level}",
        "observatory.level.rank": "Rang {rank}",
        "observatory.level.same": "Le niveau est déjà {level}.",
        "observatory.notLeader": "Seul le meneur, {name}, peut faire cela.",
        "observatory.notHere": "Cela se fait dans l'Observatoire des fractales.",
        "observatory.launch": "{fractal}, niveau {level} : le groupe part.",
        "observatory.soon": "{fractal} n'est pas encore ouverte.",
        "observatory.unknown": "Fractale inconnue : {fractal}.",
        "observatory.launchFailed": "La fractale n'a pas pu s'ouvrir.",
        "observatory.left.fractal": "Retour à l'Observatoire.",
        "observatory.notInFractal": "Vous n'êtes pas dans une fractale.",
        "observatory.group": "Groupe ({count}/5), niveau {level}, meneur {leader} : {names}",
        "observatory.fallRescue": "Les Brumes vous ramènent sur l'île.",
        "rank.Initiate": "Initié", "rank.Adept": "Adepte", "rank.Expert": "Expert", "rank.Master": "Maître",
        "trial.hit": "Golem d'essai : {damage} dégâts.",
        "trial.demo": "Le golem d'essai rejoue les attaques des fractales : cercle d'agonie, cône, ligne, puis la cage.",
        "trial.busy": "Le golem d'essai est déjà en démonstration.",
        "trial.noGolem": "Le golem d'essai n'est pas là.",
        "command.desc": "Fractales des Brumes : niveau, groupe, lancement et retour.",
        "command.level.desc": "Règle le niveau du groupe (meneur, dans l'Observatoire).",
        "command.level.arg": "Niveau de 1 à 100",
        "command.group.desc": "Affiche le groupe d'harmonisation.",
        "command.launch.desc": "Lance une fractale pour le cercle (meneur, dans l'Observatoire).",
        "command.launch.arg": "Fractale (Cliffside, Uncategorized, Volcanic, SolidOcean, Swampland, Snowblind)",
        "command.leave.desc": "Quitte la fractale et revient à l'Observatoire.",
    }
    en = {
        "items.Nakasar_Fractal_Cage_Cell.name": "Fractal Cage (imprisonment target)",
        f"items.{KEY}.name": "Mist Fragment",
        f"items.{KEY}.description": "A shard of the Mists, set in runestone. Placed in the Ancient Gateway, it opens the "
                                    "Fractal Observatory.",
        "portal.name": "Fractal Observatory",
        "portal.flavor": "An island hanging in the Mists, where fractal journeys begin.",
        "portal.tag.hub": "Mists",
        "portal.tag.group": "1 to 5 players",
        "portal.objective": "Attune the circle at the selection console and set off for a fractal",
        f"items.{CONSOLE}.name": "Selection Console",
        f"items.{CONSOLE}.description": "Use: place a fractal core and a level tuning fork in it. With both, the "
                                        "attunement circle tunes to that fractal.",
        f"items.{RESONATOR}.name": "Attunement Resonator",
        f"items.{RESONATOR}.description": "Use (leader): the attuned circle leaves for the console's fractal.",
        f"items.{CORE_DISTRIBUTOR}.name": "Core Dispenser",
        f"items.{CORE_DISTRIBUTOR}.description": "Use: take a fractal core, free.",
        f"items.{LEVEL_DISTRIBUTOR}.name": "Tuning Fork Dispenser",
        f"items.{LEVEL_DISTRIBUTOR}.description": "Use: take a level tuning fork (1 to 100), free.",
        f"shop.{CORE_SHOP}.name": "Fractal Cores",
        f"shop.{LEVEL_SHOP}.name": "Level Tuning Forks",
        "observatory.harmonized.title": "Attuned: {fractal}",
        "observatory.harmonized.subtitle": "Level {level}, {rank} rank",
        "observatory.harmonized.lost": "The console is no longer attuned: it needs a core and a tuning fork.",
        "observatory.notHarmonized": "First place a fractal core and a level tuning fork in the selection console.",
        f"items.{ASTROLABE_RING}.name": "Astrolabe Ring",
        f"items.{ASTROLABE_RING}.description": "Armillary ring of the Astrolabe.",
        f"items.{HARMONY}.name": "Attunement Tile",
        f"items.{HARMONY}.description": "Players standing on the circle form the group (5 at most).",
        f"items.{TRIAL}.name": "Training Golem Console",
        f"items.{TRIAL}.description": "Use: the golem replays the fractal attacks on you.",
        f"items.{PORTAL}.name": "Mists Portal",
        f"items.{PORTAL}.description": "An arch to place at home, always open: walking through leads to the Fractal "
                                       "Observatory, no Mists Fragment needed. Can be broken and picked up again.",
        f"items.{EXIT_STONE}.name": "Return Stone",
        f"items.{EXIT_STONE}.description": "Use: back to the Observatory.",
        f"items.{ALTAR}.name": "Infusion Altar",
        f"items.{ALTAR}.description": "Use: your 12 infusion slots. Each infusion placed adds its agony resistance, "
                                      "wherever you are; removing it takes it away.",
        f"items.{FORGE}.name": "Mist Crucible",
        f"items.{FORGE}.description": "Fuses two identical infusions into the next one, and remakes a Mist Fragment "
                                      "from shards.",
        f"items.{REWARD_CHEST}.name": "Fractal Reward Chest",
        f"items.{REWARD_CHEST}.description": "Use: your reward (one per group member). Completing a fractal at your "
                                             "highest level unlocks the next one.",
        f"items.{COUNTER_BLOCK}.name": "Archivist's Counter",
        f"items.{COUNTER_BLOCK}.description": "Use: trade Mist Shards for infusions, fragments and seasonal cosmetics.",
        f"items.{DAILY_BLOCK}.name": "Daily Fractals Board",
        f"items.{DAILY_BLOCK}.description": "Use: today's three daily fractals. Completing one gives, the first time "
                                            "each day, an extra Daily Fractal Chest.",
        f"items.{REGISTRY_BLOCK}.name": "Fractal Registry",
        f"items.{REGISTRY_BLOCK}.description": (
            "Welcome to the Observatory, traveller of the Mists.\n\n"
            "1. Take a fractal core and a level tuning fork from the two dispensers at the circle's entrance.\n"
            "2. Place them in the selection console on the Astrolabe: the circle attunes to that fractal.\n"
            "3. Step onto the attunement circle: players standing on it form the group, five at most. The first to "
            "arrive in the Observatory leads it.\n"
            "4. The leader uses a circle resonator: the whole circle leaves.\n\n"
            "Season 1: Cliffside, Uncategorized, Volcanic, Solid Ocean, Swampland, Snowblind.\n"
            "The training golem, to the west, lets you test your hits, your agony resistance and see the fractal "
            "attacks.\n"
            "To the east, the Archivist trades Mist Shards; the Infusion Altar holds your agony resistance and the "
            "Mist Crucible fuses infusions.\n"
            "Each fractal completed at your highest level unlocks the next; the leader can only pick a level they "
            "have unlocked.\n\n"
            "Fallback command: /fractale (niveau, groupe, lancer, quitter, infos)."),
        "npc.Trial_Golem.name": "Training Golem",
        "observatory.leader": "You lead the Observatory group.",
        "observatory.newLeader": "{name} now leads the group.",
        "observatory.joined": "Attuned with the group ({count}/5).",
        "observatory.left": "You leave the attunement circle.",
        "observatory.full": "The attunement circle is full (5 players).",
        "observatory.level.title": "Level {level}",
        "observatory.level.rank": "{rank} rank",
        "observatory.level.same": "The level is already {level}.",
        "observatory.notLeader": "Only the leader, {name}, can do that.",
        "observatory.notHere": "This is done in the Fractal Observatory.",
        "observatory.launch": "{fractal}, level {level}: the group sets off.",
        "observatory.soon": "{fractal} is not open yet.",
        "observatory.unknown": "Unknown fractal: {fractal}.",
        "observatory.launchFailed": "The fractal could not open.",
        "observatory.left.fractal": "Back to the Observatory.",
        "observatory.notInFractal": "You are not in a fractal.",
        "observatory.group": "Group ({count}/5), level {level}, leader {leader}: {names}",
        "observatory.fallRescue": "The Mists carry you back to the island.",
        "rank.Initiate": "Initiate", "rank.Adept": "Adept", "rank.Expert": "Expert", "rank.Master": "Master",
        "trial.hit": "Training golem: {damage} damage.",
        "trial.demo": "The training golem replays the fractal attacks: agony circle, cone, line, then the cage.",
        "trial.busy": "The training golem is already demonstrating.",
        "trial.noGolem": "The training golem is not here.",
        "command.desc": "Fractals of the Mists: level, group, launch and return.",
        "command.level.desc": "Sets the group level (leader, in the Observatory).",
        "command.level.arg": "Level from 1 to 100",
        "command.group.desc": "Shows the attunement group.",
        "command.launch.desc": "Launches a fractal for the circle (leader, in the Observatory).",
        "command.launch.arg": "Fractal (Cliffside, Uncategorized, Volcanic, SolidOcean, Swampland, Snowblind)",
        "command.leave.desc": "Leaves the fractal and returns to the Observatory.",
    }
    for fid, name_fr, name_en, *_ in FRACTALS:
        fr[f"fractal.{fid}.name"] = name_fr
        en[f"fractal.{fid}.name"] = name_en
        fr[f"items.{core_item(fid)}.name"] = f"Noyau : {name_fr}"
        en[f"items.{core_item(fid)}.name"] = f"Core: {name_en}"
        fr[f"items.{core_item(fid)}.description"] = FLAVOR[fid][0] + "\n\nÀ poser dans la console de sélection."
        en[f"items.{core_item(fid)}.description"] = FLAVOR[fid][1] + "\n\nPlace it in the selection console."
    rank_fr = {"Initiate": "Initié", "Adept": "Adepte", "Expert": "Expert", "Master": "Maître"}
    for n in range(1, MAX_LEVEL + 1):
        rid = level_rank(n)[0]
        fr[f"items.{level_item(n)}.name"] = f"Diapason : niveau {n}"
        en[f"items.{level_item(n)}.name"] = f"Tuning Fork: level {n}"
        fr[f"items.{level_item(n)}.description"] = (f"Rang {rank_fr[rid]}. À poser dans la console de sélection avec "
                                                    "un noyau ; le meneur doit avoir débloqué ce niveau.")
        en[f"items.{level_item(n)}.description"] = (f"{rid} rank. Place it in the selection console with a core; the "
                                                    "leader must have unlocked this level.")
    return fr, en


def write_lang(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in entries.items():
        lines.append(f"{k} = {v.replace(chr(10), chr(92) + 'n')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Java ---------------------------------------------------------------------------------------

def java_layout():
    return f"""package dev.nakasar.hytale.fractals.observatory;

/**
 * Positions de l'île de l'Observatoire, écrites par tools/generate_observatory.py (ne pas modifier à la main : relancer
 * le générateur). Repère du monde : x vers l'est, z vers le sud ; le centre de l'Astrolabe est en (0, {GROUND_Y}, 0).
 */
public final class ObservatoryLayout {{

    /** Première couche d'air au-dessus du dallage de l'île. */
    public static final int GROUND_Y = {GROUND_Y};
    public static final int ISLAND_RADIUS = {ISLAND_RADIUS};
    /** Cercle d'harmonisation : distance horizontale au centre de l'Astrolabe (blocs), bords compris. */
    public static final double CIRCLE_INNER = {CIRCLE_INNER - 0.5};
    public static final double CIRCLE_OUTER = {CIRCLE_OUTER + 0.5};
    /** Point d'arrivée (pieds) sur le parvis. */
    public static final double[] ARRIVAL = {{{ARRIVAL[0] + 0.5}, {float(ARRIVAL[1])}, {ARRIVAL[2] + 0.5}}};
    /** Golem d'essai (pieds). */
    public static final double[] GOLEM = {{{GOLEM_SPOT[0] + 0.5}, {float(GOLEM_SPOT[1])}, {GOLEM_SPOT[2] + 0.5}}};
    /** Bloc de la cage d'essai (Nakasar_Fractal_Cage_Cell, au niveau des pieds). */
    public static final int[] TRIAL_CAGE = {{{TRIAL_CAGE[0]}, {GROUND_Y + TRIAL_CAGE[1]}, {TRIAL_CAGE[2]}}};
    /** Où revient le joueur à l'ouverture de la cage d'essai (pieds), près du pupitre. */
    public static final double[] TRIAL_RELEASE = {{{TRIAL_PANEL[0] + 1.5}, {float(GROUND_Y + TRIAL_PANEL[1])}, {TRIAL_PANEL[2] + 2.5}}};
    /** L'Archiviste (pieds), derrière son comptoir, tourné vers l'ouest. */
    public static final double[] ARCHIVIST = {{{ARCHIVIST_SPOT[0] + 0.5}, {float(ARCHIVIST_SPOT[1])}, {ARCHIVIST_SPOT[2] + 0.5}}};
    /** Préfixes des objets de sélection : noyau d'une fractale ({{@code <préfixe><Id>}}) et diapason d'un niveau. */
    public static final String CORE_PREFIX = "{CORE_PREFIX}";
    public static final String LEVEL_PREFIX = "{LEVEL_PREFIX}";

    private ObservatoryLayout() {{
    }}
}}
"""


# --- écriture -----------------------------------------------------------------------------------

def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    (COMMON / TEXTURES).mkdir(parents=True, exist_ok=True)
    (COMMON / ICONS).mkdir(parents=True, exist_ok=True)

    stone = (74, 82, 120)
    blocks = [
        (CONSOLE, "Selection_Console", stone, (255, 214, 110), "console", "#fd8", "Nakasar_Fractal_Use_Console"),
        (RESONATOR, "Resonator", (40, 60, 110), (120, 190, 255), "resonator", "#6bf", "Nakasar_Fractal_Use_Resonator"),
        (CORE_DISTRIBUTOR, "Core_Distributor", stone, (200, 150, 255), "dispenser", "#b8f",
         "Nakasar_Fractal_Use_Core_Distributor"),
        (LEVEL_DISTRIBUTOR, "Level_Distributor", stone, (150, 200, 255), "dispenser", "#8cf",
         "Nakasar_Fractal_Use_Level_Distributor"),
        (ASTROLABE_RING, "Astrolabe_Ring", (150, 120, 60), (255, 230, 150), "ring", "#fe9", None),
        (HARMONY, "Harmony_Tile", (40, 60, 110), (120, 190, 255), "tile", "#6bf", None),
        (TRIAL, "Trial_Panel", stone, (140, 170, 255), "panel", "#8af", "Nakasar_Fractal_Use_Trial_Panel"),
        (EXIT_STONE, "Exit_Stone", stone, (190, 160, 255), "exit", "#b9f", "Nakasar_Fractal_Use_Exit"),
        (REGISTRY_BLOCK, "Registry", (90, 60, 40), (210, 190, 150), "book", None, "Nakasar_Fractal_Read_Registry"),
        (DAILY_BLOCK, "Daily_Board", (90, 60, 40), (255, 220, 110), "daily", "#fd8", "Nakasar_Fractal_Use_Daily_Board"),
    ]
    blocks += [
        (ALTAR, "Infusion_Altar", (60, 50, 100), (200, 140, 255), "altar", "#c8f", "Nakasar_Fractal_Use_Infusion_Altar"),
        (FORGE, "Mist_Forge", (50, 46, 70), (160, 120, 255), "forge", "#a8f", None),
        (REWARD_CHEST, "Reward_Chest", (70, 60, 110), (255, 210, 110), "chest", "#fd8", "Nakasar_Fractal_Use_Reward_Chest"),
        (COUNTER_BLOCK, "Archivist_Counter", (90, 60, 40), (150, 200, 255), "counter", None,
         "Nakasar_Fractal_Use_Archivist_Counter"),
    ]
    previews = []
    for name, tex, base, accent, glyph, light, use in blocks:
        img = texture(COMMON / TEXTURES / f"{tex}.png", base, accent, glyph)
        icon(COMMON / ICONS / f"{tex}.png", img)
        previews.append(img)
        if name == FORGE:
            doc = bench_item(name, tex)
        else:
            doc = block_item(name, tex, light, use, particle=hexcolor(accent))
            if name == ALTAR:
                doc = portable(doc, name)
        model = block_models.apply(doc, tex)
        if model:
            previews[-1] = model.resize((32, 32), Image.LANCZOS)
        write_json(ITEMS / f"{name}.json", doc)
    portal = portal_item()
    previews.append(block_models.apply(portal, "Mists_Portal").resize((32, 32), Image.LANCZOS))
    write_json(ITEMS / f"{PORTAL}.json", portal)
    write_json(PORTAL_HITBOX, portal_hitbox())
    write_json(SERVER / "Item/Recipes/Nakasar/Fractals" / f"Recipe_{PORTAL}.json", portal_recipe())
    key_tex = texture(COMMON / TEXTURES / "PortalKey_Fractal.png", (40, 50, 110), (150, 200, 255), "ring")
    icon(COMMON / ICONS / "PortalKey_Fractal.png", key_tex)
    (COMMON / CATEGORY_ICONS).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(COMMON / ICONS / "PortalKey_Fractal.png", COMMON / CATEGORY_ICONS / "Fragments.png")
    (COMMON / TEXTURES / "PortalKey_Fractal.png").unlink()

    items_preview = selection_items()
    write_json(SERVER / "Item/Items/Portal/Nakasar" / f"{KEY}.json", key_item())
    write_json(SERVER / "Item/Recipes/Nakasar" / f"Recipe_{KEY}.json", key_recipe())
    for name, doc in interactions().items():
        write_json(INTERACTIONS / f"{name}.json", doc)
    write_json(SERVER / "PortalTypes" / f"{OBSERVATORY}.json", portal_type())
    write_json(SERVER / "GameplayConfigs" / f"{OBSERVATORY}.json", gameplay_config())
    write_json(SERVER / "Weathers" / f"{WEATHER}.json", weather())
    write_json(SERVER / "Environments" / f"{ENVIRONMENT}.json", environment())

    write_json(SERVER / "Instances" / OBSERVATORY / "instance.bson",
               instance(OBSERVATORY, "Observatoire des fractales", OBSERVATORY))
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{OBSERVATORY}.json", biome(OBSERVATORY, "Observatory"))
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{OBSERVATORY}.json", world_structure(OBSERVATORY, ARRIVAL))
    obs = observatory_prefab()
    n = obs.write(SERVER / "Prefabs" / PREFABS / "Observatory" / "Observatory.prefab.json")

    write_json(SERVER / "Models" / "Nakasar" / "Fractals" / f"{GOLEM}.json", golem_model())
    write_json(SERVER / "NPC/Roles/Nakasar/Fractals" / f"{GOLEM}.json", golem_role())

    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    JAVA_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    JAVA_LAYOUT.write_text(java_layout(), encoding="utf-8")
    print(f"Observatoire : {n} blocs, {len(blocks)} blocs du mod")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (34 * len(previews), 34), (20, 20, 30, 255))
        for k, img in enumerate(previews):
            sheet.alpha_composite(img, (34 * k + 1, 1))
        sheet.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(preview / "blocs.png")
        sheet = Image.new("RGBA", (66 * len(items_preview), 66), (20, 20, 30, 255))
        for k, img in enumerate(items_preview):
            sheet.alpha_composite(img, (66 * k + 1, 1))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(preview / "objets.png")
        plan(obs, preview / "observatoire.png")


def plan(p, path):
    """Vue de dessus du prefab (dessus de chaque colonne), 6 pixels par bloc."""
    colors = {}
    def color(name):
        if name not in colors:
            h = abs(hash(name)) % 360
            colors[name] = tuple(int(100 + 80 * math.sin(math.radians(h + k * 120))) for k in range(3))
        return colors[name]
    r = ISLAND_RADIUS + 2
    img = Image.new("RGB", ((2 * r + 1) * 6, (2 * r + 1) * 6), (10, 12, 30))
    d = ImageDraw.Draw(img)
    top = {}
    for (x, y, z), (name, _) in p.blocks.items():
        if name != AIR and (x, z) not in top or name != AIR and y > top[(x, z)][0]:
            top[(x, z)] = (y, name)
    for (x, z), (_, name) in top.items():
        c = color(name)
        if name in (CONSOLE, RESONATOR, CORE_DISTRIBUTOR, LEVEL_DISTRIBUTOR):
            c = (255, 255, 255)
        if name == HARMONY:
            c = (90, 160, 255)
        d.rectangle(((x + r) * 6, (z + r) * 6, (x + r) * 6 + 5, (z + r) * 6 + 5), fill=c)
    img.save(path)


if __name__ == "__main__":
    main()
