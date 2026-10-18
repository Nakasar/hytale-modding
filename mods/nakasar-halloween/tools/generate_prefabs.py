#!/usr/bin/env python3
"""Génère les prefabs du Fragment halloween (format .prefab.json version 8).

Les structures sont décrites procéduralement (murs, tours, toits, mobilier) puis écrites dans
pack/Server/Prefabs/Nakasar/Halloween/<Catégorie>/<Nom>.prefab.json. Le générateur est
déterministe : relancer le script reproduit exactement les mêmes fichiers.

    python3 mods/nakasar-halloween/tools/generate_prefabs.py

Repère des prefabs : x vers l'est, z vers le sud, y vers le haut. Le worldgen pose le prefab sur
le premier bloc d'air au-dessus du sol : y = 0 est donc la première couche d'air, y = -1 le sol
(remplacé par le dallage de la structure) et y < -1 les fondations et les souterrains.

Un nom de bloc peut être préfixé par une probabilité (« 70%Rock_Stone_Brick ») : le serveur ne
pose alors le bloc qu'avec cette probabilité, à chaque génération. C'est ce qui rend chaque ruine
différente.

Ids de blocs : tous viennent de tools/vanilla-block-ids-0.7.2.txt (vérifié par validateAssets). Un
état de bloc s'écrit « *<Bloc>_State_Definitions_<État> » (clé générée par StateData du serveur),
par exemple une citrouille mûre : *Plant_Crop_Pumpkin_Block_State_Definitions_StageFinal.
"""

import json
import random
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "pack"
OUT = PACK / "Server" / "Prefabs" / "Nakasar" / "Halloween"

AIR = "Empty"

# Rotations de bloc : index RotationTuple = tangage × 4 + lacet.
# Lacet seul (meubles, souches de branche) : 0 nord, 1 est, 2 sud, 3 ouest pour les meubles ; une
# souche de branche (VariantRotation NESW) s'accroche au nord, à l'ouest, au sud puis à l'est.
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
# Tuyaux (troncs, branches longues, VariantRotation Pipe) : 0 debout, 4 couché nord-sud, 5 couché est-ouest.
UPRIGHT, ALONG_Z, ALONG_X = 0, 4, 5


def pumpkin_crop(stage):
    return f"*Plant_Crop_Pumpkin_Block_State_Definitions_{stage}"


class Prefab:
    """Grille de blocs creuse ; la dernière écriture d'une case l'emporte."""

    def __init__(self, seed):
        self.blocks = {}
        self.rng = random.Random(seed)

    # --- primitives -------------------------------------------------------------------------

    def set(self, x, y, z, name, rot=0):
        if name is None:
            self.blocks.pop((x, y, z), None)
        else:
            self.blocks[(x, y, z)] = (name, rot)

    def get(self, x, y, z):
        b = self.blocks.get((x, y, z))
        return b[0] if b else None

    def free(self, x, y, z):
        return self.get(x, y, z) in (None, AIR)

    def fill(self, x0, y0, z0, x1, y1, z1, name, rot=0):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, self.pick(name), rot)

    def hollow(self, x0, y0, z0, x1, y1, z1, wall, inside=AIR):
        """Boîte : murs latéraux en `wall`, intérieur en `inside` (sol et plafond non compris)."""
        self.fill(x0, y0, z0, x1, y1, z1, inside)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, z0, self.pick(wall))
                self.set(x, y, z1, self.pick(wall))
            for z in range(z0, z1 + 1):
                self.set(x0, y, z, self.pick(wall))
                self.set(x1, y, z, self.pick(wall))

    def pick(self, palette):
        """Une palette est un nom, ou une liste de (nom, poids) tirée à chaque bloc."""
        if isinstance(palette, str) or palette is None:
            return palette
        names = [p[0] for p in palette]
        weights = [p[1] for p in palette]
        return self.rng.choices(names, weights)[0]

    def floor(self, x0, z0, x1, z1, y, palette, foundation=None, depth=5):
        """Dallage à la hauteur y, avec des fondations sous le dallage (cache les bords flottants)."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                self.set(x, y, z, self.pick(palette))
                if foundation:
                    for d in range(1, depth + 1):
                        self.set(x, y - d, z, self.pick(foundation))

    def clear(self, x0, y0, z0, x1, y1, z1):
        self.fill(x0, y0, z0, x1, y1, z1, AIR)

    def crenellate(self, x0, z0, x1, z1, y, palette):
        """Merlons un bloc sur deux sur le pourtour du rectangle."""
        for x in range(x0, x1 + 1):
            if (x - x0) % 2 == 0:
                self.set(x, y, z0, self.pick(palette))
                self.set(x, y, z1, self.pick(palette))
        for z in range(z0, z1 + 1):
            if (z - z0) % 2 == 0:
                self.set(x0, y, z, self.pick(palette))
                self.set(x1, y, z, self.pick(palette))

    def spire(self, cx, cz, half, y, palette, step=2):
        """Flèche pyramidale à degrés (anneaux pleins) ; chaque anneau monte de `step` blocs."""
        for r in range(half, -1, -1):
            for dy in range(step if r > 0 else 3):
                for x in range(cx - r, cx + r + 1):
                    for z in range(cz - r, cz + r + 1):
                        if r == 0 or abs(x - cx) == r or abs(z - cz) == r:
                            self.set(x, y, z, self.pick(palette))
                y += 1
        return y

    def gable(self, x0, z0, x1, z1, y, full, half, gable_wall=None):
        """Toit à deux pans en demi-dalles (faîte nord-sud) posé sur un rectangle à la hauteur y.

        Chaque pas vers le faîte monte d'une demi-dalle : pas d'orientation de bloc à deviner. Les
        pignons (murs nord et sud sous le toit) sont remplis avec `gable_wall`.
        """
        width = x1 - x0 + 1
        for i in range((width + 1) // 2):
            h2 = i + 1  # hauteur en demi-blocs au-dessus de y
            for x in (x0 + i, x1 - i):
                for z in range(z0 - 1, z1 + 2):
                    for k in range(h2 // 2):
                        if k == h2 // 2 - 1 or z in (z0 - 1, z1 + 1) or x in (x0, x1):
                            self.set(x, y + k, z, self.pick(full))
                    if h2 % 2:
                        self.set(x, y + h2 // 2, z, self.pick(half))
                if gable_wall:
                    for k in range((h2 + 1) // 2):
                        for z in (z0, z1):
                            if self.free(x, y + k, z):
                                self.set(x, y + k, z, self.pick(gable_wall))

    def ruin(self, chance, keep_below=0, names=None):
        """Transforme une partie des blocs en blocs probabilistes (pierre qui s'effrite).

        Les blocs sous `keep_below` (sol, fondations) restent pleins pour que la structure tienne.
        """
        for pos, (name, rot) in list(self.blocks.items()):
            if name == AIR or "%" in name or pos[1] < keep_below:
                continue
            if names is not None and name not in names:
                continue
            self.blocks[pos] = (f"{chance}%{name}", rot)

    def scatter(self, x0, y, z0, x1, z1, count, palette, require_air=True, rot=None):
        """Pose `count` décorations sur des cases libres d'une surface."""
        placed = 0
        for _ in range(count * 12):
            if placed >= count:
                break
            x = self.rng.randint(min(x0, x1), max(x0, x1))
            z = self.rng.randint(min(z0, z1), max(z0, z1))
            if require_air and not self.free(x, y, z):
                continue
            if self.free(x, y - 1, z):
                continue
            self.set(x, y, z, self.pick(palette), self.rng.randint(0, 3) if rot is None else rot)
            placed += 1

    def paste(self, other, dx, dy, dz, min_y=None, only_free=True):
        """Copie un autre prefab (un arbre dans un cimetière...) décalé de (dx, dy, dz)."""
        for (bx, by, bz), (name, rot) in other.blocks.items():
            if min_y is not None and by < min_y:
                continue
            if only_free and not self.free(bx + dx, by + dy, bz + dz):
                continue
            self.set(bx + dx, by + dy, bz + dz, name, rot)

    # --- export -----------------------------------------------------------------------------

    def write(self, path):
        blocks = []
        for (x, y, z), (name, rot) in sorted(self.blocks.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            entry = {"x": x, "y": y, "z": z, "name": name}
            if rot:
                entry["rotation"] = rot
            blocks.append(entry)
        doc = {"version": 8, "blockIdVersion": 8, "anchorX": 0, "anchorY": 0, "anchorZ": 0}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write("{\n")
            for key, value in doc.items():
                f.write(f'  "{key}": {json.dumps(value)},\n')
            f.write('  "blocks": [\n')
            f.write(",\n".join("    " + json.dumps(b, separators=(",", ":")) for b in blocks))
            f.write("\n  ]\n}\n")
        return len(blocks)


# --- palettes ---------------------------------------------------------------------------------

STONE_WALL = [("Rock_Stone_Brick", 6), ("Rock_Stone_Brick_Mossy", 3), ("Rock_Stone_Cobble", 1), ("Rock_Stone_Cobble_Mossy", 1)]
STONE_FLOOR = [("Rock_Stone_Brick_Smooth", 4), ("Rock_Stone_Cobble", 2), ("Rock_Stone_Cobble_Mossy", 1)]
SLATE_WALL = [("Rock_Slate_Cobble", 6), ("Rock_Slate", 2), ("Rock_Shale_Cobble", 1)]
SLATE_FLOOR = [("Rock_Shale_Brick_Smooth", 3), ("Rock_Slate_Cobble", 1)]
BASALT_WALL = [("Rock_Basalt_Brick", 7), ("Rock_Basalt_Cobble", 2), ("Rock_Basalt_Brick_Decorative", 1)]
BASALT_FLOOR = [("Rock_Basalt_Brick_Smooth", 4), ("Rock_Basalt_Cobble", 1)]
SHALE_WALL = [("Rock_Shale_Brick", 6), ("Rock_Shale_Cobble", 3)]
SHALE_FLOOR = [("Rock_Shale_Brick_Smooth", 3), ("Rock_Shale_Cobble", 1)]
FOUNDATION = [("Rock_Stone_Cobble", 3), ("Rock_Stone", 2)]
DEADWOOD = "Wood_Deadwood_Planks"
GRAVE_DIRT = [("Soil_Dirt_Burnt", 3), ("Soil_Dirt", 1), ("Soil_Gravel", 1)]
GROUND = [("Soil_Grass_Burnt", 6), ("Soil_Dirt_Burnt", 2), ("Soil_Gravel_Mossy", 1)]
PATH = [("Soil_Pathway", 5), ("Soil_Gravel", 2), ("Rock_Stone_Cobble_Mossy", 1)]
WEBS = [("Deco_SpiderWeb_Full", 3), ("Deco_SpiderWeb", 4)]
BONES = [("Deco_Bone_Pile", 4), ("Deco_Bone_Skulls", 2), ("Deco_Bone_Ribs", 2), ("Deco_Bone_Full", 2), ("Deco_Bone_Spine", 1)]
CANDLES = [("Furniture_Ancient_Candle", 3), ("Furniture_Temple_Dark_Candle", 2), ("Furniture_Crude_Candle", 1)]
PUMPKINS = [("Deco_Halloween_Pumpkin_Scary", 5), ("Deco_Halloween_Pumpkin_Cute", 1), ("Deco_Halloween_Pumpkin_Hypixel", 1)]
DEAD_PLANTS = [("Plant_Bush_Dead", 3), ("Plant_Grass_Gnarled", 4), ("Plant_Grass_Gnarled_Short", 3), ("Plant_Grass_Gnarled_Tall", 2),
               ("Plant_Bush_Dead_Twisted", 1), ("Plant_Bramble_Dead_Twisted", 1)]
GLOW_MUSHROOMS = [("Plant_Crop_Mushroom_Glowing_Purple", 3), ("Plant_Crop_Mushroom_Glowing_Violet", 2), ("Plant_Crop_Mushroom_Glowing_Green", 1)]
PUMPKIN_CROPS = [(pumpkin_crop("StageFinal"), 5), (pumpkin_crop("Stage3"), 2), (pumpkin_crop("Stage2"), 1)]

MATERIALS = {
    # murs, sol, bloc plein, bloc décoratif, demi-dalle (escaliers et toits)
    "stone": (STONE_WALL, STONE_FLOOR, "Rock_Stone_Brick", "Rock_Stone_Brick_Ornate", "Rock_Stone_Brick_Half"),
    "slate": (SLATE_WALL, SLATE_FLOOR, "Rock_Slate_Cobble", "Rock_Shale_Brick_Ornate", "Rock_Slate_Cobble_Half"),
    "basalt": (BASALT_WALL, BASALT_FLOOR, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Ornate", "Rock_Basalt_Brick_Half"),
    "shale": (SHALE_WALL, SHALE_FLOOR, "Rock_Shale_Brick", "Rock_Shale_Brick_Ornate", "Rock_Shale_Brick_Half"),
}


def stairs_down(p, start, direction, depth, base, half, wall, width=3, headroom=3):
    """Escalier en demi-dalles (pas de 0,5 bloc : aucune orientation de bloc à deviner).

    Part du sol (y = -1) en `start` = (x, z) et descend de `depth` blocs en avançant d'un bloc par
    demi-pas dans `direction` = (dx, dz) ; `width` cases de large vers la droite de la marche.
    Le tunnel est muré (`wall`) là où il traverse le terrain. Renvoie la dernière case (x, z) ; on y
    marche à la hauteur y = -depth.
    """
    dx, dz = direction
    side = (-dz, dx)  # perpendiculaire
    x, z = start
    for i in range(1, 2 * depth + 1):
        x, z = start[0] + dx * (i - 1), start[1] + dz * (i - 1)
        if i % 2 == 0:
            k = -(i // 2)  # première case d'air au-dessus de la marche
            steps = [(k - 1, base)]
        else:
            k = -((i - 1) // 2)
            steps = [(k - 1, half), (k - 2, base)]
        for w in range(-1, width + 1):
            cx, cz = x + side[0] * w, z + side[1] * w
            if w in (-1, width):
                for y in range(k - 2, k + headroom + 1):
                    if p.get(cx, y, cz) is None:
                        p.set(cx, y, cz, p.pick(wall))
                continue
            for y in range(k, k + headroom):
                p.set(cx, y, cz, AIR)
            for y, name in steps:
                p.set(cx, y, cz, name)
            if k + headroom <= -1 and p.get(cx, k + headroom, cz) is None:
                p.set(cx, k + headroom, cz, p.pick(wall))
    return x, z


# --- dead trees -------------------------------------------------------------------------------
#
# Un arbre est fait de troncs pleins (cubes) et de branches en tube. Chaque morceau touche le
# précédent par une face : tronc debout, tronc couché (rotation 4 ou 5) pour le départ d'une
# branche, coude en tronc debout quand la branche remonte, tube debout ou couché ensuite et souche
# courte (Branch_Short, accrochée au bloc précédent) au bout. Rien ne flotte.

SPECIES = {
    # essence : (poids, feuillage mort possible)
    "Ash": (5, True),        # brun sombre, tordu
    "Petrified": (3, False),  # gris pâle, ressort la nuit
    "Burnt": (2, False),      # calciné, noir
}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def lying(d):
    return ALONG_X if d[0] else ALONG_Z


def stub_rotation(d):
    """Souche de branche qui pointe vers d : elle s'accroche au bloc derrière elle."""
    return {(0, 1): 0, (1, 0): 1, (0, -1): 2, (-1, 0): 3}[d]


def wood_blocks(p):
    return {pos for pos, (name, _) in p.blocks.items() if name.startswith("Wood_") and "Gnarled" not in name}


def is_connected(p):
    """Tous les blocs de bois d'un arbre se touchent par une face (vérifié à la génération)."""
    wood = wood_blocks(p)
    if not wood:
        return True
    start = min(wood, key=lambda b: (b[1], abs(b[0]) + abs(b[2])))
    seen, todo = {start}, [start]
    while todo:
        x, y, z = todo.pop()
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            n = (x + d[0], y + d[1], z + d[2])
            if n in wood and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen == wood


def dead_tree(seed, size="medium", species=None, hanging=None, webs=False):
    """Arbre mort : `size` small / medium / large, `hanging` None / "lantern" / "cage" / "noose"."""
    p = Prefab(seed)
    r = p.rng
    if species is None:
        species = r.choices(list(SPECIES), [w for w, _ in SPECIES.values()])[0]
    trunk, full = f"Wood_{species}_Trunk", f"Wood_{species}_Trunk_Full"
    long_branch, stub = f"Wood_{species}_Branch_Long", f"Wood_{species}_Branch_Short"
    height = {"small": r.randint(5, 7), "medium": r.randint(8, 11), "large": r.randint(12, 15)}[size]

    # pied élargi : contreforts en tronc plein, racines dessous
    if size != "small":
        for d in DIRS:
            if r.random() < (0.85 if size == "large" else 0.55):
                p.set(d[0], 0, d[1], full)
                p.set(d[0], -1, d[1], f"Wood_{species}_Roots")
                if size == "large" and r.random() < 0.5:
                    p.set(d[0], 1, d[1], full)
    if size == "large":
        for y in range(0, 4):
            for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1)):
                p.set(dx, y, dz, full)

    # fût penché : à chaque décalage, deux troncs côte à côte à la même hauteur (contact par la face)
    lean = r.choice(DIRS)
    x = z = 0
    column = {}
    for y in range(0, height):
        if 3 <= y < height - 2 and r.random() < 0.28:
            p.set(x, y, z, trunk)
            if r.random() < 0.3:
                lean = r.choice(DIRS)
            x, z = x + lean[0], z + lean[1]
        p.set(x, y, z, trunk)
        column[y] = (x, z)
    top = (x, height, z)
    for k in range(r.randint(1, 2)):
        p.set(x, height + k, z, long_branch, UPRIGHT)

    # branches
    elbows = []
    count = {"small": r.randint(2, 3), "medium": r.randint(3, 4), "large": r.randint(4, 6)}[size]
    dirs = DIRS[:]
    r.shuffle(dirs)
    for i in range(count):
        d = dirs[i % 4]
        y = r.randint(max(2, height // 3), height - 2)
        bx, bz = column[y]
        length = r.randint(2, 3) + {"small": 0, "medium": 1, "large": 3}[size]
        thick = 2 if size == "large" else 1
        cells = []
        for k in range(1, length + 1):
            cx, cz = bx + d[0] * k, bz + d[1] * k
            if not p.free(cx, y, cz) or p.get(cx, y + 1, cz) or p.get(cx, y - 1, cz):
                break
            cells.append((cx, cz))
        if len(cells) < 2:
            continue
        for k, (cx, cz) in enumerate(cells[:-1]):
            p.set(cx, y, cz, trunk if k < thick else long_branch, lying(d))
        ex, ez = cells[-1]
        if r.random() < 0.55:
            # coude puis tube qui remonte
            p.set(ex, y, ez, trunk)
            elbows.append((ex, y, ez))
            rise = r.randint(1, 3)
            for k in range(1, rise + 1):
                if p.free(ex, y + k, ez):
                    p.set(ex, y + k, ez, long_branch, UPRIGHT)
            # rameau latéral sur le coude
            side = (d[1], d[0]) if r.random() < 0.5 else (-d[1], -d[0])
            if p.free(ex + side[0], y, ez + side[1]):
                p.set(ex + side[0], y, ez + side[1], stub, stub_rotation(side))
        else:
            p.set(ex, y, ez, stub, stub_rotation(d))
            if len(cells) >= 3:
                # sous le départ de la branche (tronc couché, plein) : de quoi suspendre
                elbows.append((cells[0][0], y, cells[0][1]))

    # feuillage mort clairsemé autour du sommet et des coudes (essences qui en portent)
    if SPECIES[species][1] and r.random() < 0.6:
        for cx, cy, cz in elbows + [top]:
            for _ in range(r.randint(2, 5)):
                lx, ly, lz = cx + r.randint(-1, 1), cy + r.randint(0, 2), cz + r.randint(-1, 1)
                if p.free(lx, ly, lz):
                    p.set(lx, ly, lz, "Plant_Leaves_Dead")

    # ce qui pend sous les coudes (troncs pleins) : buissons morts, toiles, lanterne, cage, corde
    hung = False
    for ex, ey, ez in elbows:
        below = (ex, ey - 1, ez)
        if not p.free(*below) or ey < 4:
            continue
        drop = {"lantern": 2, "cage": 3, "noose": 2}.get(hanging, 0)
        if hanging and not hung and all(p.free(ex, ey - k, ez) for k in range(1, drop + 2)):
            hung = True
            if hanging == "lantern":
                p.set(ex, ey - 1, ez, "Deco_Iron_Chains_Vertical")
                p.set(ex, ey - 2, ez, "Deco_Lantern_Ceiling")
            elif hanging == "cage":
                p.set(ex, ey - 1, ez, "Deco_Iron_Chains_Vertical")
                p.set(ex, ey - 2, ez, "Deco_Iron_Bars")
                p.set(ex, ey - 3, ez, "Deco_Iron_Bars")
                p.set(ex, 0, ez + 1, "Deco_Bone_Skulls")
            else:
                for k in range(1, 3):
                    p.set(ex, ey - k, ez, "Deco_Rope")
            continue
        if webs and r.random() < 0.7:
            p.set(*below, p.pick(WEBS))
        elif r.random() < 0.5:
            p.set(*below, "Plant_Bush_Dead_Hanging")

    # au pied : herbes tordues, racines noueuses, parfois des os ou des champignons qui luisent
    for _ in range(r.randint(2, 5)):
        gx, gz = r.randint(-2, 2), r.randint(-2, 2)
        if p.free(gx, 0, gz) and (gx, gz) != (0, 0):
            p.set(gx, 0, gz, r.choice(["Wood_Gnarled_Roots", "Plant_Grass_Gnarled", "Plant_Grass_Gnarled_Short", "Plant_Bush_Dead"]))
    if r.random() < 0.3:
        gx, gz = r.choice([(-2, 1), (2, -1), (1, 2), (-1, -2)])
        if p.free(gx, 0, gz):
            p.set(gx, 0, gz, p.pick(GLOW_MUSHROOMS if r.random() < 0.6 else BONES), r.randint(0, 3))
    assert is_connected(p), f"arbre {seed} : bois détaché"
    return p


# --- pumpkin fields ---------------------------------------------------------------------------

def lantern_post(p, x, z, height=2, top="Deco_Lantern"):
    p.fill(x, 0, z, x, height - 1, z, "Wood_Deadwood_Beam")
    p.set(x, height, z, top)


def shed(p, x0, z0, w, d):
    """Cabane en planches de bois mort, toit à deux pans, porte au sud."""
    x1, z1 = x0 + w - 1, z0 + d - 1
    p.floor(x0, z0, x1, z1, -1, DEADWOOD)
    p.hollow(x0, 0, z0, x1, 2, z1, [("Wood_Deadwood_Planks", 5), ("Wood_Deadwood_Decorative", 1)])
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.fill(cx, 0, cz, cx, 2, cz, "Wood_Deadwood_Beam")
    door = (x0 + x1) // 2
    p.clear(door, 0, z1, door, 1, z1)
    p.set(x0, 1, (z0 + z1) // 2, AIR)  # fenêtre
    p.gable(x0, z0, x1, z1, 3, "Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half", gable_wall=DEADWOOD)
    p.set(door + 1, 0, z0 + 1, "Furniture_Crude_Chest_Small", SOUTH)
    p.set(x0 + 1, 0, z0 + 1, "Ingredient_Hay")
    p.set(x0 + 1, 1, z0 + 1, "Furniture_Crude_Candle")
    p.set(x1 - 1, 2, z1 - 1, p.pick(WEBS))
    if p.free(door, 2, z1 + 1):
        p.set(door, 2, z1 + 1, "Deco_Lantern_Ceiling")


def pumpkin_field(seed, w=23, d=19):
    p = Prefab(seed)
    r = p.rng
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0 - 1, 0, z0 - 1, x1 + 1, 5, z1 + 1)
    # sillons est-ouest : deux rangs de terre labourée, un rang de terre brûlée ; allée centrale nord-sud
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            aisle = abs(x) <= 1
            on_row = (z - z0) % 3 != 2
            if aisle:
                p.set(x, -1, z, p.pick(PATH))
                continue
            p.set(x, -1, z, "Soil_Dirt_Tilled" if on_row else p.pick(GRAVE_DIRT))
            p.set(x, -2, z, "Soil_Dirt")
            if on_row and r.random() < 0.72:
                p.set(x, 0, z, p.pick(PUMPKIN_CROPS))
            elif not on_row and r.random() < 0.12:
                p.set(x, 0, z, p.pick(PUMPKINS), r.randint(0, 3))
            elif not on_row and r.random() < 0.08:
                p.set(x, 0, z, p.pick(DEAD_PLANTS))
    # clôture de bois mort, ouverte au milieu des côtés nord et sud
    for x in range(x0 - 1, x1 + 2):
        for z in (z0 - 1, z1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
            if abs(x) > 1:
                p.set(x, 0, z, "Wood_Deadwood_Fence")
    for z in range(z0 - 1, z1 + 2):
        for x in (x0 - 1, x1 + 1):
            p.set(x, -1, z, "Soil_Grass_Burnt")
            p.set(x, 0, z, "Wood_Deadwood_Fence")
    # poteaux : citrouille-lanterne aux coins, lanternes de part et d'autre des entrées et le long de l'allée
    for cx, cz in ((x0 - 1, z0 - 1), (x1 + 1, z0 - 1), (x0 - 1, z1 + 1), (x1 + 1, z1 + 1)):
        lantern_post(p, cx, cz, 2, "Deco_Halloween_Pumpkin_Scary")
    for cz in (z0 - 1, z1 + 1):
        for cx in (-2, 2):
            lantern_post(p, cx, cz, 2)
    for x in (x0 - 1, x1 + 1):
        lantern_post(p, x, 0, 2, "Deco_Halloween_Pumpkin_Scary")
    for z in range(z0 + 3, z1 - 2, 6):
        lantern_post(p, 2 if (z // 6) % 2 else -2, z, 2)
    # épouvantails dans les rangs
    for sx, sz in ((x0 + 4, z0 + 3), (x1 - 4, z1 - 4), (r.choice([x0 + 5, x1 - 5]), 0)):
        p.set(sx, -1, sz, "Soil_Dirt")
        p.set(sx, 0, sz, "Deco_Scarecrow", r.choice([SOUTH, EAST, WEST]))
        p.set(sx, 1, sz, AIR)
    # charrette de la récolte près de l'entrée sud, paniers et meules de foin
    p.set(x1 - 3, 0, z1 - 1, "Halloween_Wagon", WEST)
    for hx, hz, hh in ((x1 - 1, z1 - 1, 2), (x1 - 1, z1 - 2, 1), (x1 - 2, z1 - 1, 1), (x0 + 1, z1 - 1, 1)):
        p.fill(hx, 0, hz, hx, hh - 1, hz, "Ingredient_Hay")
        p.set(hx, hh, hz, p.pick(PUMPKINS), r.randint(0, 3))
    p.set(2, 0, z1 - 1, "Halloween_Basket_Pumpkin")
    p.set(-2, 0, z1 - 1, "Halloween_Basket_Straw")
    p.set(x0 + 2, 0, z1 - 1, "Halloween_Basket_Pumpkin")
    # cabane de fermier dans un coin
    sw, sd = 5, 4
    sx0 = x0 + 1 if r.random() < 0.5 else x1 - sw
    shed(p, sx0, z0 + 1, sw, sd)
    p.ruin(90, keep_below=1, names={"Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half", "Wood_Deadwood_Fence"})
    # un arbre mort penché sur la clôture
    p.paste(dead_tree(r.randint(0, 1 << 30), "medium", hanging="noose"), x1 + 4, 0, z0 + 2, min_y=0)
    return p


# --- cemeteries -------------------------------------------------------------------------------

def stone_cross(p, x, z, wall="Rock_Stone_Brick_Wall"):
    """Croix de pierre : les murets se raccordent tout seuls en croix."""
    p.set(x, 0, z, wall)
    p.set(x, 1, z, wall)
    p.set(x, 2, z, wall)
    p.set(x - 1, 1, z, wall)
    p.set(x + 1, 1, z, wall)


def grave(p, x, z, r, theme):
    """Une sépulture tête au nord (z), pied au sud (z + 1, z + 2)."""
    kind = r.choices(["stele", "cross", "obelisk", "sarcophagus", "broken", "open"],
                     [5, 2, 1, 2, 2, 4 if theme == "undead" else 0.5])[0]
    if kind == "stele":
        p.set(x, 0, z, "Furniture_Village_Tombstone", SOUTH)
    elif kind == "cross":
        stone_cross(p, x, z)
    elif kind == "obelisk":
        p.set(x, 0, z, "Rock_Stone_Brick_Pillar_Base")
        p.set(x, 1, z, "Rock_Stone_Brick_Pillar_Middle")
        p.set(x, 2, z, "Rock_Stone_Brick_Ornate")
        p.set(x, 3, z, p.pick(CANDLES))
    elif kind == "sarcophagus":
        p.set(x, 0, z, "Furniture_Village_Tombstone", SOUTH)
        for dz in (1, 2):
            p.set(x, 0, z + dz, "Rock_Stone_Brick_Smooth")
            p.set(x, 1, z + dz, "Rock_Stone_Brick_Half")
        return
    elif kind == "broken":
        p.set(x, 0, z, r.choice(["Furniture_Village_Tombstone", "Furniture_Human_Ruins_Statue_Broken"]), r.randint(0, 3))
        p.set(x + r.choice([-1, 1]), 0, z + 1, "Rock_Stone_Cobble_Mossy_Half")
    if kind == "open":
        # tombe ouverte : fosse, cercueil au fond, terre rejetée sur le côté
        p.set(x, 0, z, "Furniture_Village_Tombstone", r.randint(0, 3))
        for dz in (1, 2):
            p.set(x, -1, z + dz, AIR)
            p.set(x, -2, z + dz, AIR)
            p.set(x, -3, z + dz, p.pick(GRAVE_DIRT))
            if r.random() < 0.6:
                p.set(x + 1, 0, z + dz, "Soil_Dirt_Burnt")
        p.set(x, -2, z + 1, "Furniture_Village_Coffin", SOUTH)
        p.set(x, -2, z + 2, p.pick(BONES), r.randint(0, 3))
        return
    for dz in (1, 2):
        p.set(x, -1, z + dz, p.pick(GRAVE_DIRT))
    if theme == "haunted" and r.random() < 0.6:
        p.set(x, 0, z + 1, r.choice([p.pick(CANDLES), "Plant_Petals_Blood", p.pick(PUMPKINS)]), r.randint(0, 3))
    elif theme == "spiders" and r.random() < 0.5:
        p.set(x, 1 if kind == "stele" else 0, z + (0 if kind == "stele" else 1), p.pick(WEBS))
    elif theme == "undead" and r.random() < 0.4:
        p.set(x, 0, z + 1, p.pick(BONES), r.randint(0, 3))
    elif r.random() < 0.2:
        p.set(x, 0, z + 2, p.pick(DEAD_PLANTS))


def mausoleum(p, x0, z0, r, door_south=True):
    """Petit caveau 5 × 5 en pierre, toit en demi-dalles, grille à l'entrée."""
    x1, z1 = x0 + 4, z0 + 4
    p.floor(x0, z0, x1, z1, -1, STONE_FLOOR)
    p.hollow(x0, 0, z0, x1, 3, z1, STONE_WALL)
    for cx in (x0, x1):
        for cz in (z0, z1):
            p.set(cx, 0, cz, "Rock_Stone_Brick_Pillar_Base")
            p.fill(cx, 1, cz, cx, 3, cz, "Rock_Stone_Brick_Pillar_Middle")
    p.gable(x0, z0, x1, z1, 4, "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half")
    dz = z1 if door_south else z0
    p.clear(x0 + 2, 0, dz, x0 + 2, 1, dz)
    p.set(x0 + 2, 0, dz, "Deco_Iron_Bars")
    p.set(x0 + 2, 2, dz, "Rock_Stone_Brick_Ornate")
    p.set(x0 + 2, 0, (z0 + z1) // 2, "Furniture_Ancient_Coffin", SOUTH)
    p.set(x0 + 1, 0, z0 + 1, p.pick(CANDLES))
    p.set(x1 - 1, 0, z0 + 1, p.pick(CANDLES))
    p.set(x1 - 1, 2, z1 - 1, p.pick(WEBS))
    outside = dz + (1 if door_south else -1)
    p.set(x0 + 1, 0, outside, "Furniture_Village_Brazier")
    p.set(x1 - 1, 0, outside, "Furniture_Village_Brazier")


def chapel(p, cx, z0, r, theme):
    """Chapelle 9 × 13 : nef au toit pentu, clocher sur la façade sud, autel et bancs."""
    x0, x1, z1 = cx - 4, cx + 4, z0 + 12
    p.floor(x0, z0, x1, z1, -1, STONE_FLOOR, FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 5, z1, STONE_WALL)
    for z in range(z0, z1 + 1, 3):
        for x in (x0, x1):
            p.set(x, 0, z, "Rock_Stone_Brick_Pillar_Base")
            p.fill(x, 1, z, x, 5, z, "Rock_Stone_Brick_Pillar_Middle")
        if z0 < z < z1:
            for x in (x0, x1):
                p.fill(x, 2, z + 1, x, 3, z + 1, "Deco_Iron_Bars")  # vitraux brisés
    p.gable(x0 - 1, z0, x1 + 1, z1, 6, "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half", gable_wall=STONE_WALL)
    # clocher : tour 5 × 5 sur la façade sud
    tx0, tz0 = cx - 2, z1 - 2
    p.hollow(tx0, 0, tz0, tx0 + 4, 12, tz0 + 4, STONE_WALL)
    for y in (6, 11):
        p.fill(tx0 + 1, y, tz0 + 1, tx0 + 3, y, tz0 + 3, "Wood_Deadwood_Planks")
    for y in range(8, 11):
        for (wx, wz) in ((cx, tz0), (cx, tz0 + 4), (tx0, tz0 + 2), (tx0 + 4, tz0 + 2)):
            p.set(wx, y, wz, AIR)  # baies du beffroi
    p.set(cx, 10, tz0 + 2, "Deco_Iron_Chains_Vertical")
    p.set(cx, 9, tz0 + 2, "Deco_Lantern_Ceiling")
    p.crenellate(tx0, tz0, tx0 + 4, tz0 + 4, 13, STONE_WALL)
    p.spire(cx, tz0 + 2, 1, 13, "Rock_Slate_Cobble", step=2)
    # porche
    p.clear(cx - 1, 0, tz0 + 4, cx + 1, 2, tz0 + 4)
    p.clear(cx - 1, 0, tz0, cx + 1, 2, tz0)
    p.fill(cx - 1, 3, tz0 + 4, cx + 1, 3, tz0 + 4, "Rock_Stone_Brick_Ornate")
    p.set(cx, 2, tz0 + 3, "Deco_Lantern_Ceiling")
    p.set(cx - 2, 0, tz0 + 5, "Furniture_Village_Brazier")
    p.set(cx + 2, 0, tz0 + 5, "Furniture_Village_Brazier")
    # intérieur : allée, bancs, autel, cercueil
    for z in range(z0 + 1, tz0):
        p.set(cx, -1, z, "Cloth_Block_Wool_Purple" if theme == "haunted" else "Rock_Stone_Brick_Smooth")
    for z in range(z0 + 4, tz0 - 1, 2):
        for x in (cx - 2, cx + 2):
            p.set(x, 0, z, "Furniture_Ancient_Bench", NORTH)
    p.fill(cx - 1, 0, z0 + 1, cx + 1, 0, z0 + 1, "Rock_Stone_Brick_Smooth")
    p.set(cx, 1, z0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
    p.set(cx - 1, 1, z0 + 1, p.pick(CANDLES))
    p.set(cx + 1, 1, z0 + 1, p.pick(CANDLES))
    p.set(cx, 0, z0 + 2, "Furniture_Ancient_Coffin", EAST)
    p.set(cx - 3, 0, z0 + 1, "Furniture_Temple_Dark_Brazier")
    p.set(cx + 3, 0, z0 + 1, "Furniture_Temple_Dark_Brazier")
    p.set(cx, 5, z0 + 6, "Furniture_Tavern_Chandelier")
    for _ in range(10):
        x, z = r.randint(x0 + 1, x1 - 1), r.randint(z0 + 1, tz0 - 1)
        if p.free(x, 5, z):
            p.set(x, 5, z, p.pick(WEBS))
    p.scatter(x0 + 1, 0, z0 + 3, x1 - 1, tz0 - 1, 4, BONES if theme == "undead" else CANDLES)


def cemetery(seed, theme):
    p = Prefab(seed)
    r = p.rng
    w, d = r.choice([(31, 33), (33, 31), (29, 33)])
    x0, z0, x1, z1 = -w // 2, -d // 2, w // 2, d // 2
    p.clear(x0, 0, z0, x1, 6, z1)
    # sol : herbe brûlée en plaques, allée principale nord-sud et allée transversale
    blobs = [(r.randint(x0, x1), r.randint(z0, z1), r.randint(2, 5)) for _ in range(9)]
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            near = any((x - bx) ** 2 + (z - bz) ** 2 <= br * br for bx, bz, br in blobs)
            p.set(x, -1, z, r.choice(["Soil_Dirt_Burnt", "Soil_Gravel_Mossy", "Soil_Ash"]) if near else p.pick(GROUND))
    cross_z = z0 + 18
    for z in range(z0 + 1, z1 + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    for x in range(x0 + 1, x1):
        p.set(x, -1, cross_z, p.pick(PATH))
    # muret, grille et piliers, avec des brèches
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if z == z1 and abs(x) <= 2:
                continue
            p.set(x, 0, z, "Rock_Stone_Brick_Wall")
            p.set(x, 1, z, "Deco_Iron_Bars")
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            p.set(x, 0, z, "Rock_Stone_Brick_Wall")
            p.set(x, 1, z, "Deco_Iron_Bars")
    for k in range(r.randint(2, 4)):  # brèches
        if r.random() < 0.5:
            bx, bz, along = r.randint(x0 + 3, x1 - 3), r.choice([z0, z1]), (1, 0)
        else:
            bx, bz, along = r.choice([x0, x1]), r.randint(z0 + 3, z1 - 3), (0, 1)
        if bz == z1 and abs(bx) <= 4:
            continue
        for i in range(r.randint(1, 3)):
            p.set(bx + along[0] * i, 1, bz + along[1] * i, AIR)
            if r.random() < 0.6:
                p.set(bx + along[0] * i, 0, bz + along[1] * i, "Rock_Stone_Cobble_Mossy_Half")
    posts = [(x, z) for x in range(x0, x1 + 1, 4) for z in (z0, z1)] + [(x, z) for z in range(z0 + 4, z1, 4) for x in (x0, x1)]
    for i, (px, pz) in enumerate(posts):
        if pz == z1 and abs(px) <= 2:
            continue
        p.set(px, 0, pz, "Rock_Stone_Brick_Pillar_Base")
        p.set(px, 1, pz, "Rock_Stone_Brick_Pillar_Middle")
        p.set(px, 2, pz, "Rock_Stone_Brick_Ornate")
        if i % 2 == 0:
            p.set(px, 3, pz, "Deco_Spider_Cocoon" if theme == "spiders" else p.pick(PUMPKINS), r.randint(0, 3))
        elif r.random() < 0.6:
            p.set(px, 3, pz, p.pick(CANDLES))
    # portail : deux hauts piliers, linteau, lanterne suspendue
    for gx in (-3, 3):
        p.set(gx, 0, z1, "Rock_Stone_Brick_Pillar_Base")
        p.fill(gx, 1, z1, gx, 4, z1, "Rock_Stone_Brick_Pillar_Middle")
        p.set(gx, 5, z1, "Rock_Stone_Brick_Ornate")
        p.set(gx, 6, z1, "Deco_Halloween_Pumpkin_Scary", SOUTH)
        p.set(gx, 0, z1 + 1, "Furniture_Village_Brazier")
    p.fill(-2, 5, z1, 2, 5, z1, "Rock_Stone_Brick_Ornate")
    p.set(0, 6, z1, "Rock_Stone_Brick_Pillar_Middle")
    p.set(0, 7, z1, "Rock_Stone_Brick_Ornate")
    p.set(0, 4, z1, "Deco_Iron_Chains_Vertical")
    p.set(0, 3, z1, "Deco_Lantern_Ceiling")
    # chapelle au fond
    chapel(p, 0, z0 + 1, r, theme)
    # caveaux de famille près du portail
    mausoleum(p, x0 + 2, z1 - 7, r)
    if r.random() < 0.7:
        mausoleum(p, x1 - 6, z1 - 7, r)
    # rangées de tombes de part et d'autre de l'allée, en dehors de la chapelle et des caveaux
    for x in list(range(x0 + 3, -3, 3)) + list(range(4, x1 - 1, 3)):
        for z in range(z0 + 3, z1 - 9, 4):
            if abs(x) <= 6 and z <= z0 + 15:  # chapelle
                continue
            if z in (cross_z - 2, cross_z - 1, cross_z):
                continue
            if r.random() < 0.85:
                grave(p, x, z, r, theme)
    # lanternes le long de l'allée
    for z in range(z0 + 16, z1 - 1, 5):
        lantern_post(p, 2, z, 2)
        lantern_post(p, -2, z + 2, 2)
    # arbres morts et décor selon le thème
    tree_spots = [(x0 + 2, cross_z + 1), (x1 - 2, cross_z - 4), (x0 + 3, z0 + 3), (x1 - 3, z0 + 4)]
    for tx, tz in tree_spots:
        if r.random() < 0.75:
            t = dead_tree(r.randint(0, 1 << 30), r.choice(["small", "medium"]), webs=theme == "spiders",
                          hanging="lantern" if theme == "haunted" and r.random() < 0.5 else None)
            p.paste(t, tx, 0, tz, min_y=0)
    if theme == "haunted":
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 14, CANDLES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, PUMPKINS)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 10, GLOW_MUSHROOMS)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 10, DEAD_PLANTS)
    elif theme == "spiders":
        for _ in range(6):
            cx, cz = r.randint(x0 + 2, x1 - 2), r.randint(z0 + 16, z1 - 2)
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) + abs(dz) <= 3 and r.random() < 0.6 and p.free(cx + dx, 0, cz + dz):
                        p.set(cx + dx, 0, cz + dz, "Deco_SpiderWeb_Flat")
            p.set(cx, 0, cz, "Deco_Spider_Cocoon")
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 22, WEBS)
        p.scatter(x0 + 1, 1, z0 + 1, x1 - 1, z1 - 1, 10, WEBS, require_air=True)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, [("Deco_Spider_Cocoon", 2), ("Deco_Bone_Pile", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 6, GLOW_MUSHROOMS)
    else:
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 18, BONES)
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 5, [("Deco_Bone_Spike", 2), ("Deco_Bone_Ribs_Long", 1), ("Deco_Bone_Spike_Large", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, [("Plant_Crop_Mushroom_Glowing_Green", 2), ("Plant_Crop_Mushroom_Glowing_Purple", 1)])
        p.scatter(x0 + 1, 0, z0 + 1, x1 - 1, z1 - 1, 8, DEAD_PLANTS)
    p.ruin(85, keep_below=1, names={"Rock_Stone_Brick", "Rock_Stone_Brick_Mossy", "Rock_Stone_Cobble", "Rock_Stone_Cobble_Mossy",
                                    "Deco_Iron_Bars", "Rock_Stone_Brick_Wall"})
    return p


# --- crypts -----------------------------------------------------------------------------------

def crypt(seed, material):
    """Mausolée en surface et salle voûtée enterrée au nord, reliés par un escalier."""
    p = Prefab(seed)
    r = p.rng
    wall, flr, brick, ornate, half = MATERIALS[material]
    depth = 7
    # salle enterrée : sol à y = -depth - 1, voûte à y = -depth + 4 (sous la couche de terre)
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = -6, 6, -23, -12
    for x in range(cx0 - 1, cx1 + 2):
        for y in range(cy0, cy0 + 6):
            for z in range(cz0 - 1, cz1 + 2):
                p.set(x, y, z, p.pick(wall))
    p.floor(cx0, cz0, cx1, cz1, cy0, flr)
    p.clear(cx0, cy0 + 1, cz0, cx1, cy0 + 4, cz1)
    for px in (cx0 + 3, cx1 - 3):
        for pz in (cz0 + 3, cz1 - 3):
            p.fill(px, cy0 + 1, pz, px, cy0 + 4, pz, ornate)
            p.set(px + (1 if px < 0 else -1), cy0 + 1, pz, "Furniture_Temple_Dark_Brazier")
    # mausolée 9 x 11
    x0, x1, z0, z1 = -4, 4, -5, 5
    p.floor(x0 - 1, z0 - 1, x1 + 1, z1 + 1, -1, flr, FOUNDATION, depth=2)
    p.hollow(x0, 0, z0, x1, 5, z1, wall)
    for x in (x0, x1):
        for z in (z0, z1):
            p.fill(x, 0, z, x, 6, z, ornate)
    p.fill(x0, 6, z0, x1, 6, z1, brick)
    p.crenellate(x0, z0, x1, z1, 7, wall)
    # fronton et porte au sud
    p.clear(-1, 0, z1, 1, 3, z1)
    p.fill(-2, 4, z1 + 1, 2, 4, z1 + 1, ornate)
    p.fill(-2, 0, z1 + 1, -2, 3, z1 + 1, ornate)
    p.fill(2, 0, z1 + 1, 2, 3, z1 + 1, ornate)
    p.set(-2, 5, z1 + 1, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(2, 5, z1 + 1, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(0, 3, z1, "Deco_Lantern_Ceiling")
    p.set(0, 7, z1, "Furniture_Ancient_Statue", SOUTH)
    p.set(-3, 0, z1 - 1, p.pick(CANDLES))
    p.set(3, 0, z1 - 1, p.pick(CANDLES))
    p.set(-3, 4, z0 + 1, p.pick(WEBS))
    p.set(3, 4, z0 + 1, p.pick(WEBS))
    # escalier : part du fond du mausolée et descend vers le nord jusqu'à la salle
    stairs_down(p, (-1, 2), (0, -1), depth, brick, half, wall, width=3)
    # cercueils le long des murs, coffre au fond, os et toiles
    for z in range(cz0 + 1, cz1, 3):
        p.set(cx0 + 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Human_Ruins_Coffin"]), EAST)
        p.set(cx1 - 1, cy0 + 1, z, r.choice(["Furniture_Ancient_Coffin", "Furniture_Temple_Dark_Coffin", "Furniture_Village_Coffin"]), WEST)
    p.set(0, cy0 + 1, cz0 + 1, "Furniture_Temple_Dark_Chest_Large", SOUTH)
    p.set(-1, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    p.set(1, cy0 + 1, cz0 + 1, p.pick(CANDLES))
    if r.random() < 0.5:
        p.set(0, cy0 + 1, cz0 + 5, "Furniture_Temple_Dark_Statue", SOUTH)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 9, BONES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 5, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 1, cz1 - 1, 4, [("Rock_Crystal_Purple_Small", 1)])
    for _ in range(14):
        x, z = r.randint(cx0, cx1), r.randint(cz0, cz1)
        if p.get(x, cy0 + 4, z) == AIR:
            p.set(x, cy0 + 4, z, p.pick(WEBS))
    # tombes, braseros et citrouilles devant l'entrée
    for x in (-4, 4):
        p.set(x, 0, z1 + 3, "Furniture_Village_Tombstone", SOUTH)
        p.set(x, -1, z1 + 4, p.pick(GRAVE_DIRT))
        p.set(x, -1, z1 + 5, p.pick(GRAVE_DIRT))
    for x in (-3, 3):
        p.set(x, 0, z1 + 1, "Furniture_Village_Brazier")
    for z in range(z1 + 1, z1 + 7):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    p.set(-1, 0, z1 + 4, p.pick(PUMPKINS), r.randint(0, 3))
    p.paste(dead_tree(r.randint(0, 1 << 30), "medium", webs=True), 7, 0, z1 + 3, min_y=0)
    p.ruin(85, keep_below=0, names={n for n, _ in wall})
    return p


# --- castles ----------------------------------------------------------------------------------

def ladder(p, x, y0, y1, z):
    """Échelle contre le mur est, de y0 à y1 (inclus) ; la case y1 est la trappe du plancher."""
    for y in range(y0, y1 + 1):
        p.set(x, y, z, "Furniture_Human_Ruins_Ladder", WEST)


def tower(p, cx, cz, half, height, wall, flr, roof, ornate, spire=False, webs=True):
    x0, x1, z0, z1 = cx - half, cx + half, cz - half, cz + half
    p.floor(x0, z0, x1, z1, -1, flr, FOUNDATION, depth=4)
    p.hollow(x0, 0, z0, x1, height, z1, wall)
    bottom = 0
    for y in range(4, height, 5):
        p.fill(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, flr)
        ladder(p, x1 - 1, bottom, y, cz)
        bottom = y + 1
        # meurtrières
        for (wx, wz) in ((cx, z0), (cx, z1), (x0, cz), (x1, cz)):
            p.set(wx, y + 2, wz, "Deco_Iron_Bars")
    p.fill(x0, height + 1, z0, x1, height + 1, z1, flr)
    if not spire:
        ladder(p, x1 - 1, bottom, height + 1, cz)  # jusqu'aux créneaux
    if spire:
        p.spire(cx, cz, half + 1, height + 2, roof)
    else:
        p.crenellate(x0, z0, x1, z1, height + 2, wall)
        p.set(cx, height + 2, cz, "Furniture_Village_Brazier")
    if webs:
        p.set(x0 + 1, height, z0 + 1, p.pick(WEBS))
        p.set(x1 - 1, height, z1 - 1, p.pick(WEBS))


def curtain_wall(p, x0, z0, x1, z1, height, wall, gate_half=2):
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if z == z1 and abs(x) <= gate_half:
                continue
            p.fill(x, 0, z, x, height, z, p.pick(wall))
            p.set(x, -1, z, p.pick(FOUNDATION))
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            p.fill(x, 0, z, x, height, z, p.pick(wall))
            p.set(x, -1, z, p.pick(FOUNDATION))
    # chemin de ronde
    for x in range(x0 + 1, x1):
        p.set(x, height, z0 + 1, p.pick(wall))
        p.set(x, height, z1 - 1, p.pick(wall))
    for z in range(z0 + 1, z1):
        p.set(x0 + 1, height, z, p.pick(wall))
        p.set(x1 - 1, height, z, p.pick(wall))
    p.crenellate(x0, z0, x1, z1, height + 1, wall)


def gatehouse(p, z, height, wall, ornate, gate_half=2):
    p.fill(-gate_half - 1, 0, z, -gate_half - 1, height + 2, z, ornate)
    p.fill(gate_half + 1, 0, z, gate_half + 1, height + 2, z, ornate)
    p.fill(-gate_half, height - 1, z, gate_half, height + 1, z, p.pick(wall))
    for x in range(-gate_half, gate_half + 1):
        p.set(x, height - 2, z, "Deco_Iron_Bars")  # herse relevée
    p.set(-gate_half - 1, height + 3, z, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(gate_half + 1, height + 3, z, "Deco_Halloween_Pumpkin_Scary", SOUTH)
    p.set(0, height - 3, z - 1, "Deco_Lantern_Ceiling")
    for x in (-gate_half - 2, gate_half + 2):
        p.set(x, 0, z + 1, "Furniture_Village_Brazier")


def keep(p, x0, z0, x1, z1, height, wall, flr, roof, ornate, levels=2):
    p.floor(x0, z0, x1, z1, -1, flr, FOUNDATION, depth=4)
    p.hollow(x0, 0, z0, x1, height, z1, wall)
    level_h = height // levels
    for lv in range(1, levels):
        y = lv * level_h
        p.fill(x0 + 1, y, z0 + 1, x1 - 1, y, z1 - 1, flr)
        # trémie d'escalier (échelle) dans un coin
        p.fill(x1 - 2, y, z0 + 1, x1 - 1, y, z0 + 2, AIR)
        ladder(p, x1 - 1, y - level_h + 1, y, z0 + 1)
    # fenêtres
    for lv in range(levels):
        y = lv * level_h + 2
        for x in range(x0 + 2, x1 - 1, 3):
            p.set(x, y, z0, "Deco_Iron_Bars")
            p.set(x, y, z1, "Deco_Iron_Bars")
        for z in range(z0 + 2, z1 - 1, 3):
            p.set(x0, y, z, "Deco_Iron_Bars")
            p.set(x1, y, z, "Deco_Iron_Bars")
    # porte
    p.clear(-1, 0, z1, 1, 2, z1)
    p.fill(-2, 3, z1, 2, 3, z1, ornate)
    # toit
    p.fill(x0, height + 1, z0, x1, height + 1, z1, flr)
    p.crenellate(x0, z0, x1, z1, height + 2, wall)
    return level_h


def haunted_castle(seed, material):
    p = Prefab(seed)
    r = p.rng
    wall, flr, roof, ornate, _ = MATERIALS[material]
    s = 16
    p.clear(-s, 0, -s, s, 12, s)
    # cour : terre et pavés
    for x in range(-s, s + 1):
        for z in range(-s, s + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Rock_Stone_Cobble_Mossy", "Soil_Gravel_Mossy"]))
    for z in range(-4, s + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(flr))
    curtain_wall(p, -s, -s, s, s, 8, wall)
    gatehouse(p, s, 8, wall, ornate)
    for cx in (-s, s):
        for cz in (-s, s):
            tower(p, cx, cz, 3, 14, wall, flr, roof, ornate, spire=r.random() < 0.5)
    # donjon
    level_h = keep(p, -6, -12, 6, -2, 12, wall, flr, roof, ornate, levels=2)
    # salle du bas : longue table, chandelier, bannières
    p.fill(-1, 0, -10, 1, 0, -5, "Furniture_Human_Ruins_Table")
    for z in range(-10, -4):
        p.set(-2, 0, z, "Furniture_Human_Ruins_Chair", EAST)
        p.set(2, 0, z, "Furniture_Human_Ruins_Chair", WEST)
    for z in (-10, -7, -5):
        p.set(0, 1, z, p.pick(CANDLES))
    p.set(0, level_h - 1, -7, "Furniture_Tavern_Chandelier")
    for x in (-4, 4):
        p.set(x, 3, -11, "Furniture_Human_Ruins_Banner", SOUTH)
    p.set(-4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(4, 0, -11, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(-5, 0, -3, "Furniture_Temple_Dark_Brazier")
    p.set(5, 0, -3, "Furniture_Temple_Dark_Brazier")
    # étage : chambre abandonnée
    y = level_h + 1
    p.set(-4, y, -10, "Furniture_Ancient_Bed", EAST)
    p.set(-4, y, -6, "Furniture_Human_Ruins_Wardrobe", EAST)
    p.set(3, y, -10, "Furniture_Ancient_Chest_Large", SOUTH)
    p.set(0, y, -9, "Furniture_Ancient_Painting", SOUTH)
    p.scatter(-5, y, -11, 5, -3, 6, CANDLES)
    # toiles d'araignée partout sous les plafonds
    for _ in range(40):
        x, z = r.randint(-5, 5), r.randint(-11, -3)
        for yy in (level_h - 1, 2 * level_h - 1):
            if p.get(x, yy, z) == AIR and r.random() < 0.5:
                p.set(x, yy, z, p.pick(WEBS))
    # cour : puits, tombes, arbres morts, citrouilles
    p.hollow(8, 0, 6, 10, 1, 8, wall)
    p.fill(9, -4, 7, 9, 1, 7, AIR)
    p.set(9, -5, 7, "Soil_Mud")
    for y in range(-4, -1):
        for (wx, wz) in ((8, 7), (10, 7), (9, 6), (9, 8)):
            p.set(wx, y, wz, p.pick(wall))
    p.gable(8, 6, 10, 8, 2, "Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half")
    p.set(8, 2, 6, "Wood_Deadwood_Beam")
    p.set(10, 2, 8, "Wood_Deadwood_Beam")
    for x in range(-13, -7, 2):
        for z in (6, 10):
            grave(p, x, z, r, "haunted")
    for tx, tz, size in ((-10, 13, "medium"), (12, 12, "medium"), (-12, 2, "small")):
        p.paste(dead_tree(r.randint(0, 1 << 30), size, webs=True), tx, 0, tz, min_y=0)
    p.scatter(-s + 2, 0, -s + 2, s - 2, s - 2, 12, PUMPKINS)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 10, DEAD_PLANTS)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 8, BONES)
    p.scatter(-s + 2, 0, -1, s - 2, s - 2, 6, GLOW_MUSHROOMS)
    p.ruin(78, keep_below=1, names={n for n, _ in wall})
    return p


def dracula_castle(seed):
    """Château du comte vampire : basalte et ardoise, flèches, salle du trône, crypte aux cercueils."""
    p = Prefab(seed)
    r = p.rng
    wall, flr, roof, ornate, half = MATERIALS["basalt"]
    s = 20
    p.clear(-s, 0, -s, s, 16, s)
    for x in range(-s, s + 1):
        for z in range(-s, s + 1):
            p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Dirt_Burnt", "Rock_Basalt_Cobble", "Soil_Grass_Burnt"]))
    # allée de pavés bordée de roses de sang
    for z in range(-6, s + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(flr))
        for x in (-3, 3):
            p.set(x, -1, z, "Soil_Dirt")
            if z % 2 == 0:
                p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Petals_Blood", "Plant_Crop_Health1"]))
        if z % 6 == 0 and z > -6:
            for x in (-4, 4):
                lantern_post(p, x, z, 2)
    curtain_wall(p, -s, -s, s, s, 10, wall)
    gatehouse(p, s, 10, wall, ornate)
    slate_roof = "Rock_Slate_Cobble"
    for cx in (-s, s):
        for cz in (-s, s):
            tower(p, cx, cz, 3, 18, wall, flr, slate_roof, ornate, spire=True)
    # tours de flanc
    for cx, cz in ((-s, 0), (s, 0)):
        tower(p, cx, cz, 2, 14, wall, flr, slate_roof, ornate, spire=True)
    # donjon
    x0, x1, z0, z1 = -9, 9, -17, -5
    keep(p, x0, z0, x1, z1, 16, wall, flr, slate_roof, ornate, levels=2)
    p.spire(x0 + 2, z0 + 2, 2, 19, slate_roof)
    p.spire(x1 - 2, z0 + 2, 2, 19, slate_roof)
    p.fill(0, 18, z0 + 4, 0, 24, z0 + 4, ornate)
    p.spire(0, z0 + 4, 3, 25, slate_roof)
    # salle du trône : tapis rouge, trône, piliers, chandeliers
    for z in range(z0 + 2, z1 + 1):
        for x in (-1, 0, 1):
            p.set(x, -1, z, "Cloth_Block_Wool_Red")
    for z in range(z0 + 3, z1, 3):
        for x in (-5, 5):
            p.fill(x, 0, z, x, 7, z, "Rock_Basalt_Brick_Pillar_Middle")
            p.set(x - 1 if x > 0 else x + 1, 0, z, p.pick(CANDLES))
    p.fill(-2, 0, z0 + 1, 2, 0, z0 + 2, "Rock_Basalt_Brick_Smooth")
    p.set(0, 1, z0 + 1, "Furniture_Royal_Magic_Carpet")
    p.fill(-1, 1, z0 + 1, 1, 1, z0 + 1, "Cloth_Block_Wool_Red")
    p.fill(-1, 2, z0 + 1, 1, 3, z0 + 1, "Rock_Basalt_Brick_Ornate")
    p.set(0, 1, z0 + 2, "Furniture_Temple_Dark_Coffin", SOUTH)
    for x in (-3, 3):
        p.set(x, 1, z0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
        p.set(x, 4, z0 + 1, "Furniture_Outlander_Banner", SOUTH)
        p.set(x, 0, z0 + 3, "Furniture_Temple_Dark_Brazier")
    for z in (z0 + 4, z0 + 9):
        p.set(0, 7, z, "Furniture_Feran_Chandelier")
    # le comte attend sur le tapis, devant son trône (marqueur invisible du mod nakasar-mobs)
    p.set(0, 0, z0 + 5, "Nakasar_Spawner_Vampire_Count")
    for x in (-7, 7):
        for z in range(z0 + 2, z1 - 1, 4):
            p.set(x, 2, z, "Cloth_Block_Wool_Red")
            p.set(x, 3, z, "Cloth_Block_Wool_Red")
    # étage : bibliothèque et chambre du comte
    y = 9
    for x in range(x0 + 1, -2):
        p.set(x, y, z0 + 1, "Furniture_Human_Ruins_Bookshelf", SOUTH)
        p.set(x, y + 1, z0 + 1, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(4, y, z0 + 3, "Furniture_Temple_Dark_Coffin", WEST)
    p.set(6, y, z0 + 3, "Furniture_Temple_Dark_Chest_Large", WEST)
    p.set(4, y, z1 - 2, "Alchemy_Cauldron_Big")
    p.scatter(x0 + 1, y, z0 + 1, x1 - 1, z1 - 1, 8, CANDLES)
    for _ in range(30):
        x, z = r.randint(x0 + 1, x1 - 1), r.randint(z0 + 1, z1 - 1)
        if p.get(x, 15, z) == AIR:
            p.set(x, 15, z, p.pick(WEBS))
    # crypte sous le donjon : un escalier part de la salle du trône et plonge le long du mur sud
    # (le plafond de la crypte est le dallage de la salle du trône)
    depth = 5
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = x0 + 1, x1 - 1, z0 + 1, z1 - 1
    for x in range(cx0 - 1, cx1 + 2):
        for z in range(cz0 - 1, cz1 + 2):
            p.set(x, cy0, z, p.pick(wall))
            p.set(x, cy0 - 1, z, p.pick(FOUNDATION))
    p.floor(cx0, cz0, cx1, cz1, cy0, flr)
    p.clear(cx0, cy0 + 1, cz0, cx1, -2, cz1)
    stairs_down(p, (cx1 - 1, cz1), (0, -1), depth, "Rock_Basalt_Brick", half, wall, width=2)
    for x in range(cx0 + 1, cx1 - 3, 3):
        p.set(x, cy0 + 1, cz0 + 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), SOUTH)
        p.set(x, cy0 + 1, cz1 - 1, r.choice(["Furniture_Temple_Dark_Coffin", "Furniture_Ancient_Coffin"]), NORTH)
    mid = (cz0 + cz1) // 2
    p.set(0, cy0 + 1, mid, "Furniture_Ancient_Chest_Large", SOUTH)
    for x in (-1, 1):
        p.set(x, cy0 + 1, mid, "Deco_Treasure_Pile_Small")
    # ses rejetons gardent la crypte (marqueurs invisibles du mod nakasar-mobs)
    for x in (cx0 + 2, cx1 - 5):
        p.set(x, cy0 + 1, mid + 1, "Nakasar_Spawner_Vampire_Spawn")
    for px in (-4, 3):
        p.fill(px, cy0 + 1, mid, px, -2, mid, "Rock_Basalt_Brick_Pillar_Middle")
        p.set(px, cy0 + 1, mid - 1, "Furniture_Temple_Dark_Brazier")
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 10, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 8, BONES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 4, [("Rock_Crystal_Red_Small", 1)])
    # cour : jardin de roses de sang, cercueils dressés, gibets
    for x in range(-16, -6):
        for z in range(6, 16):
            if (x + z) % 2 == 0:
                p.set(x, -1, z, "Soil_Dirt")
                p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Crop_Health2", "Plant_Crop_Health3", "Plant_Petals_Blood"]))
    for x in range(8, 17, 3):
        p.set(x, 0, 10, "Furniture_Village_Coffin", SOUTH)
        grave(p, x, 13, r, "undead")
    for tx, tz, hanging in ((12, 3, "cage"), (-12, 2, "noose")):
        p.paste(dead_tree(r.randint(0, 1 << 30), "medium", species="Burnt", hanging=hanging), tx, 0, tz, min_y=0)
    p.scatter(-s + 2, 0, -3, s - 2, s - 2, 8, PUMPKINS)
    p.scatter(-s + 2, 0, -3, s - 2, s - 2, 8, BONES)
    p.ruin(92, keep_below=1, names={n for n, _ in wall})
    return p


# --- small decorations ------------------------------------------------------------------------

def bone_pile(seed):
    p = Prefab(seed)
    r = p.rng
    for _ in range(r.randint(4, 8)):
        x, z = r.randint(-2, 2), r.randint(-2, 2)
        p.set(x, 0, z, p.pick(BONES), r.randint(0, 3))
    p.set(0, 0, 0, "Deco_Bone_Spike_Large" if r.random() < 0.5 else "Deco_Bone_Spike")
    for x, z in ((-1, -1), (1, 1), (1, -2)):
        p.set(x, -1, z, r.choice(["Soil_Dirt_Burnt", "Soil_Ash", "Soil_Gravel"]))
    if r.random() < 0.5:
        p.set(r.choice([-2, 2]), 0, r.choice([-2, 2]), p.pick(GLOW_MUSHROOMS))
    return p


def lone_grave(seed):
    p = Prefab(seed)
    r = p.rng
    grave(p, 0, 0, r, r.choice(["haunted", "undead", "plain"]))
    if r.random() < 0.5:
        p.set(1, 0, 0, p.pick(CANDLES))
    if r.random() < 0.4:
        p.set(-1, 0, 1, p.pick(PUMPKINS), r.randint(0, 3))
    if r.random() < 0.5:
        lantern_post(p, -1, -1, 1)
    return p


def spider_nest(seed):
    p = Prefab(seed)
    r = p.rng
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if dx * dx + dz * dz <= 10 and r.random() < 0.7:
                p.set(dx, 0, dz, "Deco_SpiderWeb_Flat")
    p.set(0, 0, 0, "Deco_Spider_Cocoon")
    for _ in range(3):
        p.set(r.randint(-2, 2), 0, r.randint(-2, 2), r.choice(["Deco_Spider_Cocoon", "Deco_Spider_Cocoon", "Deco_Bone_Pile"]))
    p.paste(dead_tree(r.randint(0, 1 << 30), "small", webs=True), r.choice([-3, 3]), 0, r.choice([-3, 3]), min_y=0)
    return p


def pumpkin_patch(seed):
    p = Prefab(seed)
    r = p.rng
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if dx * dx + dz * dz <= 5 and r.random() < 0.7:
                p.set(dx, -1, dz, "Soil_Dirt_Burnt")
                if r.random() < 0.6:
                    p.set(dx, 0, dz, p.pick(PUMPKIN_CROPS) if r.random() < 0.75 else p.pick(PUMPKINS), r.randint(0, 3))
    return p


def rock_outcrop(seed):
    """Affleurement rocheux : un tas de blocs de roche moussue, parfois des cristaux qui luisent."""
    p = Prefab(seed)
    r = p.rng
    rock = r.choice([
        [("Rock_Stone", 4), ("Rock_Stone_Mossy", 3), ("Rock_Stone_Cobble_Mossy", 1)],
        [("Rock_Slate", 4), ("Rock_Slate_Cobble", 2), ("Rock_Stone_Mossy", 1)],
        [("Rock_Shale", 4), ("Rock_Shale_Cobble", 2), ("Rock_Basalt", 1)],
    ])
    cx, cz = 0, 0
    for _ in range(r.randint(2, 4)):
        rad = r.uniform(1.5, 3.2)
        h = r.randint(2, 5)
        for x in range(-4, 5):
            for z in range(-4, 5):
                dist = ((x - cx) ** 2 + (z - cz) ** 2) ** 0.5
                if dist > rad:
                    continue
                top = int(round(h * (1 - dist / (rad + 0.5)))) + r.randint(-1, 0)
                for y in range(-2, top):
                    p.set(x, y, z, p.pick(rock))
        cx += r.randint(-2, 2)
        cz += r.randint(-2, 2)
    # dessus : mousse, demi-dalles, herbes ; pied : cailloux et cristaux
    for (x, y, z), (name, _) in list(p.blocks.items()):
        if y >= 0 and p.free(x, y + 1, z):
            roll = r.random()
            if roll < 0.15:
                p.set(x, y + 1, z, "Rock_Stone_Cobble_Mossy_Half")
            elif roll < 0.35:
                p.set(x, y + 1, z, p.pick(DEAD_PLANTS))
    crystal = r.random() < 0.45
    for _ in range(r.randint(3, 7)):
        x, z = r.randint(-5, 5), r.randint(-5, 5)
        if p.free(x, 0, z) and (not p.free(x + 1, 0, z) or not p.free(x - 1, 0, z)):
            p.set(x, 0, z, "Rock_Crystal_Purple_Small" if crystal and r.random() < 0.6 else p.pick(DEAD_PLANTS))
    return p


def mushroom_ring(seed):
    """Cercle de champignons luisants autour d'une pierre levée et de bougies."""
    p = Prefab(seed)
    r = p.rng
    rad = r.choice([2.5, 3.0, 3.5])
    kind = r.choice(["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Violet", "Plant_Crop_Mushroom_Glowing_Green"])
    for x in range(-4, 5):
        for z in range(-4, 5):
            d = (x * x + z * z) ** 0.5
            if abs(d - rad) < 0.6 and r.random() < 0.85:
                p.set(x, 0, z, kind)
            elif d < rad - 0.5:
                p.set(x, -1, z, r.choice(["Soil_Grass_Burnt", "Soil_Ash", "Soil_Dirt_Burnt"]))
    p.set(0, 0, 0, "Rock_Stone_Mossy")
    p.set(0, 1, 0, "Rock_Stone_Cobble_Mossy_Half")
    for x, z in ((1, 0), (-1, 1), (0, -1)):
        if r.random() < 0.7:
            p.set(x, 0, z, p.pick(CANDLES))
    if r.random() < 0.5:
        p.set(r.choice([-1, 1]), 0, r.choice([-1, 1]), p.pick(BONES))
    return p


def wayside_shrine(seed):
    """Petit autel au bord du chemin : stèle, lanterne, offrandes de citrouilles et de bougies."""
    p = Prefab(seed)
    r = p.rng
    for x in range(-1, 2):
        for z in range(-1, 2):
            p.set(x, -1, z, p.pick(PATH))
    p.set(0, 0, -1, "Rock_Stone_Brick_Pillar_Base")
    p.set(0, 1, -1, "Rock_Stone_Brick_Pillar_Middle")
    p.set(0, 2, -1, "Rock_Stone_Brick_Ornate")
    p.set(0, 3, -1, p.pick(PUMPKINS), SOUTH)
    p.set(-1, 0, -1, p.pick(CANDLES))
    p.set(1, 0, -1, p.pick(CANDLES))
    p.set(0, 0, 0, r.choice(["Furniture_Village_Tombstone", p.pick(PUMPKINS)]), SOUTH)
    lantern_post(p, 2, 1, 2)
    p.set(-1, 0, 1, r.choice(["Halloween_Basket_Pumpkin", "Halloween_Basket_Straw"]))
    return p


def fallen_log(seed):
    """Tronc mort couché, couvert de champignons et d'herbes."""
    p = Prefab(seed)
    r = p.rng
    species = r.choice(["Ash", "Ash", "Petrified", "Burnt"])
    length = r.randint(4, 7)
    along_x = r.random() < 0.5
    for k in range(length):
        x, z = (k - length // 2, 0) if along_x else (0, k - length // 2)
        p.set(x, 0, z, f"Wood_{species}_Trunk", ALONG_X if along_x else ALONG_Z)
        if r.random() < 0.35:
            p.set(x, 1, z, r.choice(["Plant_Crop_Mushroom_Glowing_Green", "Plant_Crop_Mushroom_Glowing_Purple", "Plant_Grass_Gnarled_Short"]))
    end = (length - length // 2, 0) if along_x else (0, length - length // 2)
    p.set(end[0], 0, end[1], "Wood_Gnarled_Roots")
    for _ in range(3):
        x, z = r.randint(-3, 3), r.choice([-1, 1])
        if not along_x:
            x, z = z, x
        if p.free(x, 0, z):
            p.set(x, 0, z, p.pick(DEAD_PLANTS))
    return p


# --- main -------------------------------------------------------------------------------------

def main():
    jobs = []
    sizes = ["small", "small", "medium", "medium", "medium", "large"]
    for i in range(12):
        jobs.append((f"Trees/Dead_Tree_{i + 1}", dead_tree(1000 + i, sizes[i % len(sizes)], webs=i % 4 == 0)))
    for i, hanging in enumerate(("lantern", "cage", "noose", "lantern")):
        jobs.append((f"Trees/Hanging_Tree_{i + 1}", dead_tree(1100 + i, "medium" if i % 2 else "large", hanging=hanging, webs=True)))
    for i in range(3):
        jobs.append((f"PumpkinFields/Pumpkin_Field_{i + 1}", pumpkin_field(2000 + i, *[(23, 19), (27, 17), (19, 23)][i])))
    for t, theme in enumerate(("haunted", "spiders", "undead")):
        for i in range(2):
            jobs.append((f"Cemeteries/{theme.capitalize()}/Cemetery_{theme.capitalize()}_{i + 1}", cemetery(3000 + t * 100 + i, theme)))
    for i, material in enumerate(("stone", "slate", "shale")):
        jobs.append((f"Crypts/Crypt_{material.capitalize()}", crypt(4000 + i, material)))
    jobs.append(("HauntedCastles/Haunted_Castle_Stone", haunted_castle(5000, "stone")))
    jobs.append(("HauntedCastles/Haunted_Castle_Slate", haunted_castle(5001, "slate")))
    jobs.append(("DraculaCastle/Dracula_Castle", dracula_castle(6000)))
    for i in range(3):
        jobs.append((f"Decor/BonePiles/Bone_Pile_{i + 1}", bone_pile(7000 + i)))
        jobs.append((f"Decor/Graves/Lone_Grave_{i + 1}", lone_grave(7100 + i)))
        jobs.append((f"Decor/SpiderNests/Spider_Nest_{i + 1}", spider_nest(7200 + i)))
        jobs.append((f"Decor/PumpkinPatches/Pumpkin_Patch_{i + 1}", pumpkin_patch(7300 + i)))
        jobs.append((f"Decor/MushroomRings/Mushroom_Ring_{i + 1}", mushroom_ring(7500 + i)))
        jobs.append((f"Decor/Shrines/Wayside_Shrine_{i + 1}", wayside_shrine(7600 + i)))
        jobs.append((f"Decor/FallenLogs/Fallen_Log_{i + 1}", fallen_log(7700 + i)))
    for i in range(5):
        jobs.append((f"Decor/Outcrops/Rock_Outcrop_{i + 1}", rock_outcrop(7400 + i)))

    if OUT.exists():
        for old in OUT.rglob("*.prefab.json"):
            old.unlink()
    total = 0
    for name, prefab in jobs:
        count = prefab.write(OUT / f"{name}.prefab.json")
        total += count
        print(f"{name}: {count} blocs")
    print(f"{len(jobs)} prefabs, {total} blocs")


if __name__ == "__main__":
    main()
