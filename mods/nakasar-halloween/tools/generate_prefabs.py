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
import re
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
# Blocs en ligne (clôtures, murets, grilles) : orientés à l'écriture par Prefab.orient_lines.
LINE_BLOCK = re.compile(r"(_Fence|_Brick_Wall|_Cobble_Wall|Iron_Bars|Iron_Railing)$")


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
        """Flèche pyramidale à degrés ; chaque anneau monte de `step` blocs.

        La base est une dalle pleine et le haut de chaque anneau déborde d'un cran vers l'intérieur :
        l'anneau suivant repose dessus (sinon les anneaux ne se touchent que par les arêtes et la
        flèche flotte en jeu).
        """
        for x in range(cx - half, cx + half + 1):
            for z in range(cz - half, cz + half + 1):
                self.set(x, y, z, self.pick(palette))
        y += 1
        for r in range(half, -1, -1):
            layers = step if r > 0 else 3
            for dy in range(layers):
                for x in range(cx - r, cx + r + 1):
                    for z in range(cz - r, cz + r + 1):
                        ring = max(abs(x - cx), abs(z - cz))
                        if r == 0 or ring == r or (dy == layers - 1 and ring == r - 1):
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

    def steep_roof(self, x0, z0, x1, z1, y, full, half, ridge="x", gable_wall=None):
        """Toit gothique à deux pans à 45° : un bloc de montée par rangée, adouci d'une demi-dalle.

        `ridge` = axe du faîte ("x" : pignons à l'est et à l'ouest, "z" : pignons au nord et au sud).
        Chaque rangée fait deux blocs d'épaisseur pour toucher la suivante par une face. Les pignons
        sont remplis avec `gable_wall`. Renvoie la hauteur du faîte.
        """
        if ridge == "x":
            lo, hi, a0, a1 = z0, z1, x0, x1
            at = lambda u, v: (v, u)  # u le long de la pente (z), v le long du faîte (x)
        else:
            lo, hi, a0, a1 = x0, x1, z0, z1
            at = lambda u, v: (u, v)
        rows = (hi - lo) // 2 + 1
        top = y
        for i in range(rows):
            h = y + i
            top = h
            for u in {lo + i, hi - i}:
                for v in range(a0, a1 + 1):
                    x, z = at(u, v)
                    for k in range(max(y, h - 1), h + 1):
                        self.set(x, k, z, self.pick(full))
                    self.set(x, h + 1, z, half)
            if gable_wall:
                for v in (a0, a1):
                    for u in range(lo + i + 1, hi - i):
                        x, z = at(u, v)
                        self.set(x, h, z, self.pick(gable_wall))
        return top + 1

    def ruin(self, chance, keep_below=0, names=None):
        """Effrite la structure : garde environ `chance` % des blocs visés, surtout en bas.

        Les blocs retirés le sont à la génération du prefab (pas de bloc probabiliste, tiré à chaque
        pose, qui laissait des pans de mur suspendus dans le vide). Plus un bloc est haut, plus il a
        de chances de tomber ; puis tout ce qui ne rejoint plus le sol de face en face est retiré
        aussi. Les blocs sous `keep_below` (sol, fondations) restent pleins.
        """
        targets = [pos for pos, (name, _) in self.blocks.items()
                   if name != AIR and pos[1] >= keep_below and (names is None or name in names)]
        if not targets:
            return
        top = max(pos[1] for pos in targets)
        for pos in targets:
            h = (pos[1] - keep_below) / max(1, top - keep_below)
            if self.rng.random() < (100 - chance) / 100 * (0.3 + 1.4 * h):
                self.blocks[pos] = (AIR, 0)
        for pos in floating_blocks(self):
            del self.blocks[pos]

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

    def orient_lines(self):
        """Tourne clôtures, murets et grilles dans le sens de leur ligne.

        Ces blocs (VariantRotation Wall / NESW) se dessinent le long de l'axe x en rotation 0 et
        le long de z en rotation 1 ; en jeu ils ne se raccordent pas seuls dans un prefab. Le sens
        se lit sur les voisins de la même famille, à défaut sur les blocs pleins qui les tiennent.
        """
        def line(name):
            return LINE_BLOCK.search(name.split("%")[-1]) is not None

        for (x, y, z), (name, rot) in list(self.blocks.items()):
            if rot or not line(name):
                continue
            def count(pred, axis):
                ds = ((1, 0), (-1, 0)) if axis == "x" else ((0, 1), (0, -1))
                return sum(1 for dx, dz in ds if pred(self.blocks.get((x + dx, y, z + dz), (AIR, 0))[0]))
            along_x, along_z = count(line, "x"), count(line, "z")
            if along_x == along_z:
                solid = lambda n: n != AIR and not n.split("%")[-1].startswith(("Plant_", "Deco_Halloween"))
                along_x, along_z = count(solid, "x"), count(solid, "z")
            if along_z > along_x:
                self.blocks[(x, y, z)] = (name, 1)

    def write(self, path):
        self.orient_lines()
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
    # essence : (poids, feuilles mortes de l'essence, posées sur le dessus des branches)
    "Ash": (5, "Plant_Leaves_Dead"),        # frêne mort, brun sombre (comme Trees/Ash_Dead du jeu)
    "Petrified": (3, "Plant_Leaves_Petrified"),  # gris pâle, ressort la nuit
    "Burnt": (2, "Plant_Leaves_Burnt"),      # calciné, noir
}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
FACES = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))


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
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n in wood and n not in seen:
                seen.add(n)
                todo.append(n)
    return seen == wood


def floating_blocks(p):
    """Blocs qui ne rejoignent pas le sol (y <= 0) de face en face : ils flotteraient en jeu."""
    solid = {pos for pos, (name, _) in p.blocks.items() if name != AIR}
    seen = {pos for pos in solid if pos[1] <= 0}
    todo = list(seen)
    while todo:
        x, y, z = todo.pop()
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n in solid and n not in seen:
                seen.add(n)
                todo.append(n)
    return solid - seen


def dead_tree(seed, size="medium", species=None, hanging=None, webs=False):
    """Arbre mort à la manière des arbres du jeu : `size` small / medium / large, `hanging` None /
    "lantern" / "cage" / "noose".

    Comme les arbres vanilla, tout le squelette est en blocs pleins : un fût droit de troncs, des
    branches en troncs pleins qui montent en escalier (chaque bloc touche le précédent par une face),
    et seulement au bout des rameaux des tubes fins (branche longue debout, souche sur le côté). Les
    feuilles mortes de l'essence se posent sur le dessus des branches. Aucun bloc ne flotte : c'est
    vérifié à la génération.
    """
    p = Prefab(seed)
    r = p.rng
    if species is None:
        species = r.choices(list(SPECIES), [w for w, _ in SPECIES.values()])[0]
    trunk, full = f"Wood_{species}_Trunk", f"Wood_{species}_Trunk_Full"
    twig, stub = f"Wood_{species}_Branch_Long", f"Wood_{species}_Branch_Short"
    leaves = SPECIES[species][1]
    height = {"small": r.randint(5, 7), "medium": r.randint(8, 10), "large": r.randint(11, 14)}[size]
    wide = {"small": 0, "medium": 1, "large": height // 2}[size]  # hauteur du pied élargi 2×2

    # fût : droit, élargi en 2×2 au pied des grands arbres, contreforts et racines au sol
    for y in range(height):
        p.set(0, y, 0, trunk)
    if size == "large":
        for y in range(wide):
            for dx, dz in ((1, 0), (0, 1), (1, 1)):
                p.set(dx, y, dz, trunk)
    foot = [(dx, dz) for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1)) if p.get(dx, 0, dz)]
    for fx, fz in foot:
        for d in DIRS:
            bx, bz = fx + d[0], fz + d[1]
            if p.free(bx, 0, bz) and r.random() < (0.6 if size != "small" else 0.3):
                p.set(bx, 0, bz, full)
                if size == "large" and r.random() < 0.4 and p.free(bx, 1, bz):
                    p.set(bx, 1, bz, full)
                p.set(bx, -1, bz, f"Wood_{species}_Roots")

    tips, limbs = [], []

    def touches_other_wood(cell, prev):
        x, y, z = cell
        for d in FACES:
            n = (x + d[0], y + d[1], z + d[2])
            if n != prev and n in p.blocks and p.blocks[n][0].startswith("Wood_"):
                return True
        return False

    def grow(start, d, length, rise, depth):
        """Branche en troncs pleins depuis `start` vers d ; `rise` = probabilité de monter d'un cran."""
        cell = start
        horizontal = 0
        for k in range(length):
            up = horizontal > 0 and r.random() < rise
            nxt = (cell[0], cell[1] + 1, cell[2]) if up else (cell[0] + d[0], cell[1], cell[2] + d[1])
            if not p.free(*nxt) or touches_other_wood(nxt, cell):
                break
            p.set(*nxt, full)
            horizontal = 0 if up else horizontal + 1
            if not up:
                limbs.append(nxt)
            cell = nxt
            rise = min(0.8, rise + 0.08)
            if depth == 0 and k == length // 2 and length >= 4 and r.random() < 0.6:
                side = (d[1], d[0]) if r.random() < 0.5 else (-d[1], -d[0])
                grow(cell, side, r.randint(2, 3), 0.45, 1)
        if cell != start:
            tips.append((cell, d))

    # branches le long du fût, tournées dans des directions différentes
    count = {"small": r.randint(2, 3), "medium": r.randint(3, 4), "large": r.randint(4, 5)}[size]
    dirs = DIRS[:]
    r.shuffle(dirs)
    low = max(wide + 2, height // 2 if size == "small" else height // 3 + 1)
    heights = sorted(r.sample(range(low, height - 1), min(count, height - 1 - low)))
    for i, y in enumerate(heights):
        length = r.randint(1, 2) + {"small": 0, "medium": 2, "large": 3}[size]
        grow((0, y, 0), dirs[i % 4], length, 0.25, 0)
    # couronne : deux ou trois rameaux qui partent du sommet en remontant
    for d in r.sample(DIRS, r.randint(2, 3) if size != "small" else 1):
        grow((0, height - 1, 0), d, r.randint(2, 3) + (size == "large"), 0.5, 1)

    # bouts de rameaux : tube fin debout, parfois une souche qui continue sur le côté
    for (x, y, z), d in tips + [((0, height - 1, 0), None)]:
        for k in range(1, r.randint(1, 2) + 1):
            if not p.free(x, y + k, z):
                break
            p.set(x, y + k, z, twig, UPRIGHT)
        if d and p.free(x + d[0], y, z + d[1]) and r.random() < 0.6:
            p.set(x + d[0], y, z + d[1], stub, stub_rotation(d))

    # feuilles mortes posées sur le dessus des branches (le modèle du jeu repose sur un bloc plein)
    if r.random() < 0.75:
        for x, y, z in limbs:
            if p.free(x, y + 1, z) and r.random() < 0.3:
                p.set(x, y + 1, z, leaves)

    # ce qui pend sous les branches : lanterne, cage, corde, toiles, buissons morts
    hung = False
    r.shuffle(limbs)
    for x, y, z in limbs:
        drop = {"lantern": 2, "cage": 3, "noose": 2}.get(hanging, 0)
        if hanging and not hung and y >= drop + 2 and all(p.free(x, y - k, z) for k in range(1, drop + 2)):
            hung = True
            if hanging == "lantern":
                p.set(x, y - 1, z, "Deco_Iron_Chains_Vertical")
                p.set(x, y - 2, z, "Deco_Lantern_Ceiling")
            elif hanging == "cage":
                p.set(x, y - 1, z, "Deco_Iron_Chains_Vertical")
                p.set(x, y - 2, z, "Deco_Iron_Bars")
                p.set(x, y - 3, z, "Deco_Iron_Bars")
                if p.free(x, 0, z):
                    p.set(x, 0, z, "Deco_Bone_Skulls")
            else:
                for k in range(1, 3):
                    p.set(x, y - k, z, "Deco_Rope")
            continue
        if not p.free(x, y - 1, z) or y < 3:
            continue
        if webs and r.random() < 0.35:
            p.set(x, y - 1, z, p.pick(WEBS))
        elif r.random() < 0.2:
            p.set(x, y - 1, z, "Plant_Bush_Dead_Hanging")

    # au pied : herbes tordues, racines noueuses, parfois des os ou des champignons qui luisent
    for _ in range(r.randint(2, 5)):
        gx, gz = r.randint(-2, 3), r.randint(-2, 3)
        if p.free(gx, 0, gz):
            p.set(gx, 0, gz, r.choice(["Wood_Gnarled_Roots", "Plant_Grass_Gnarled", "Plant_Grass_Gnarled_Short", "Plant_Bush_Dead"]))
    if r.random() < 0.3:
        gx, gz = r.choice([(-2, 1), (2, -1), (1, 2), (-1, -2)])
        if p.free(gx, 0, gz):
            p.set(gx, 0, gz, p.pick(GLOW_MUSHROOMS if r.random() < 0.6 else BONES), r.randint(0, 3))
    assert is_connected(p), f"arbre {seed} : bois détaché"
    assert not floating_blocks(p), f"arbre {seed} : blocs qui flottent {sorted(floating_blocks(p))[:5]}"
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
    p.ruin(90, keep_below=1, names={"Wood_Deadwood_Planks", "Wood_Deadwood_Planks_Half"})
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
    # chapelle et caveaux usés par le temps ; le muret et sa grille restent entiers (brèches à part)
    p.ruin(90, keep_below=1, names={"Rock_Stone_Brick", "Rock_Stone_Brick_Mossy", "Rock_Stone_Cobble", "Rock_Stone_Cobble_Mossy"})
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
    p.set(0, height - 1, z - 1, "Deco_Lantern_Ceiling")
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


# --- manoir du comte et crypte d'arrivée ------------------------------------------------------
#
# Blocs du pack (tools/generate_assets.py) : vitraux, gargouille, grille à lances, vantail de portail.
# Leurs modèles regardent vers +Z (le sud) sans rotation ; FACING donne la rotation (NESW) pour
# qu'ils regardent vers un autre côté.
GLASS_RED, GLASS_VIOLET = "Nakasar_Stained_Glass_Red", "Nakasar_Stained_Glass_Violet"
GARGOYLE, RAILING, GATE = "Nakasar_Gargoyle", "Nakasar_Iron_Railing", "Nakasar_Iron_Gate"
FACING = {"S": 0, "E": 1, "N": 2, "W": 3}
MANOR_WALL = [("Rock_Basalt_Brick", 8), ("Rock_Basalt_Brick_Decorative", 1), ("Rock_Basalt_Cobble", 1)]
MANOR_FLOOR = [("Rock_Basalt_Brick_Smooth", 5), ("Rock_Shale_Brick_Smooth", 2)]
MANOR_ROOF, MANOR_ROOF_HALF = "Rock_Slate_Cobble", "Rock_Slate_Cobble_Half"
MANOR_TRIM = "Rock_Basalt_Brick_Ornate"
WOOD_FLOOR = [("Wood_Deadwood_Planks", 4), ("Wood_Deadwood_Decorative", 1)]


def lancet(p, x, y, z, glass, height=3):
    """Fenêtre en ogive : vitrail de `height` blocs, clé de voûte ornée au-dessus, appui lisse dessous."""
    p.fill(x, y, z, x, y + height - 1, z, glass)
    p.set(x, y + height, z, MANOR_TRIM)
    p.set(x, y - 1, z, "Rock_Basalt_Brick_Smooth")


def rose_window(p, cx, cy, z=None, x=None):
    """Rosace 3 × 3 : couronne de vitraux rouges, cœur violet, dans le plan d'un mur (z ou x fixé)."""
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            glass = GLASS_VIOLET if a == b == 0 else GLASS_RED
            if z is not None:
                p.set(cx + a, cy + b, z, glass)
            else:
                p.set(x, cy + b, cx + a, glass)


def perched_gargoyle(p, x, y, z, facing):
    """Gargouille sur un corbeau en saillie : (x, y - 1, z) doit toucher un mur par une face."""
    p.set(x, y - 1, z, MANOR_TRIM)
    p.set(x, y, z, GARGOYLE, FACING[facing])


def stairs_up(p, x0, x1, z_start, dz, rise, base, half, floor_y=-1):
    """Escalier droit en demi-dalles qui monte de `rise` blocs vers `dz` (± 1), sur x0..x1.

    Une case par demi-bloc ; la dernière marche arrive au niveau du sol de l'étage. Les marches sont
    pleines jusqu'au sol (pas de vide dessous). Renvoie la liste des z des marches.
    """
    zs = []
    for i in range(2 * rise):
        z = z_start + dz * i
        h2 = i + 1  # hauteur de la marche en demi-blocs au-dessus du sol
        for x in range(x0, x1 + 1):
            for y in range(floor_y + 1, floor_y + 1 + h2 // 2):
                p.set(x, y, z, base)
            if h2 % 2:
                p.set(x, floor_y + 1 + h2 // 2, z, half)
        zs.append(z)
    return zs


def spawn_crypt(seed):
    """Crypte fermée autour du portail d'arrivée (centre en 0, 0, 0 : le portail apparaît là).

    11 × 11, toit pentu en ardoise, porte au nord (vers le manoir), vitraux, cercueils le long des
    murs, gargouilles aux angles. Le centre (3 × 3 × 3) reste libre : le jeu y vide la place et pose
    le portail de retour.
    """
    p = Prefab(seed)
    r = p.rng
    h = 5
    p.clear(-8, 0, -12, 8, 14, 8)
    for x in range(-8, 9):
        for z in range(-12, 9):
            p.set(x, -1, z, p.pick(GROUND))
    p.floor(-5, -5, 5, 5, -1, STONE_FLOOR, FOUNDATION, depth=3)
    p.hollow(-5, 0, -5, 5, h, 5, STONE_WALL)
    for cx in (-5, 5):
        for cz in (-5, 5):
            p.set(cx, 0, cz, "Rock_Stone_Brick_Pillar_Base")
            p.fill(cx, 1, cz, cx, h, cz, "Rock_Stone_Brick_Pillar_Middle")
    p.steep_roof(-5, -5, 5, 5, h + 1, MANOR_ROOF, MANOR_ROOF_HALF, ridge="z", gable_wall=STONE_WALL)
    # porte au nord, lanternes et chemin vers le manoir
    p.set(0, 0, -5, "Furniture_Temple_Dark_Door", NORTH)
    p.set(0, 1, -5, AIR)
    p.set(0, 2, -5, "Rock_Stone_Brick_Ornate")
    p.fill(-1, 3, -5, 1, 3, -5, "Rock_Stone_Brick_Ornate")
    for x in (-2, 2):
        lantern_post(p, x, -7, 2)
    for z in range(-12, -5):
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
    # vitraux : rosace au-dessus de la porte, ogives sur les côtés et derrière le portail
    rose_window(p, 0, 7, z=-5)
    for z in (-2, 2):
        p.fill(-5, 1, z, -5, 3, z, GLASS_VIOLET)
        p.fill(5, 1, z, 5, 3, z, GLASS_VIOLET)
    p.fill(0, 1, 5, 0, 3, 5, GLASS_RED)
    p.set(0, 4, 5, "Rock_Stone_Brick_Ornate")
    # intérieur : cercueils, bougies, braseros, toiles ; rien à moins de 2 blocs du centre
    for z in (-3, 3):
        p.set(-4, 0, z, "Furniture_Ancient_Coffin", EAST)
        p.set(4, 0, z, "Furniture_Ancient_Coffin", WEST)
    for x in (-4, 4):
        for z in (-4, 4):
            p.set(x, 0, z, p.pick(CANDLES))
    for x in (-3, 3):
        p.set(x, 0, 4, "Furniture_Temple_Dark_Brazier")
    p.set(-4, 0, 0, p.pick(BONES))
    p.set(4, 0, 0, "Deco_Bone_Skulls")
    for x, z in ((-4, -4), (4, 4), (-4, 4), (4, -4)):
        p.set(x, h, z, p.pick(WEBS))
    # gargouilles aux quatre angles, sur des corbeaux contre les pignons
    for x in (-5, 5):
        perched_gargoyle(p, x, h + 1, -6, "N")
        perched_gargoyle(p, x, h + 1, 6, "S")
    # abords : tombes et citrouilles
    for x, z in ((-7, -9), (7, -9), (-7, 7), (7, 7)):
        grave(p, x, z, r, r.choice(["haunted", "plain"]))
    p.scatter(-8, 0, -12, 8, 8, 6, PUMPKINS)
    p.scatter(-8, 0, -12, 8, 8, 6, DEAD_PLANTS)
    return p


def vampire_manor(seed):
    """Manoir gothique du comte : domaine clos de grilles à lances, jardin, corps de logis à étage.

    Plan (nord = -Z, la façade regarde le sud, vers le point d'apparition) :
    - domaine 57 × 51 fermé par une grille sur muret, portail en fer forgé au sud entre deux piliers
      à gargouille ;
    - corps de logis 27 × 17 (rez-de-chaussée et étage), deux ailes en avancée avec pignon sur
      la façade, tour-porche au centre avec rosace et flèche, tour d'angle au nord-ouest ;
    - rez-de-chaussée : grand hall à piliers et tapis rouge jusqu'au trône (marqueur du comte ou
      de la comtesse), cheminées, salle à manger (aile ouest), bibliothèque (aile est), escalier ;
    - étage : chambre du comte, boudoir de la comtesse, galerie de tableaux, balcon sur le porche ;
    - crypte sous le hall, où veillent les rejetons ;
    - jardin : allée bordée de lanternes, roses de sang, tombes de famille, mausolée, arbres morts.
    """
    p = Prefab(seed)
    r = p.rng
    X, Z0, Z1 = 28, -25, 25
    p.clear(-X, 0, Z0, X, 34, Z1)
    for x in range(-X, X + 1):
        for z in range(Z0, Z1 + 1):
            p.set(x, -1, z, p.pick(GROUND))

    # --- clôture : muret de basalte, grille à lances, piliers ; portail au sud -------------------
    gate_half = 2
    for x in range(-X, X + 1):
        for z in (Z0, Z1):
            if z == Z1 and abs(x) <= gate_half:
                continue
            p.set(x, -1, z, p.pick(FOUNDATION))
            p.set(x, 0, z, "Rock_Basalt_Brick")
            p.set(x, 1, z, RAILING)
    for z in range(Z0, Z1 + 1):
        for x in (-X, X):
            p.set(x, -1, z, p.pick(FOUNDATION))
            p.set(x, 0, z, "Rock_Basalt_Brick")
            p.set(x, 1, z, RAILING)
    posts = [(x, z) for x in range(-X, X + 1, 7) for z in (Z0, Z1)] + [(x, z) for z in range(Z0, Z1 + 1, 6) for x in (-X, X)]
    for x, z in posts:
        if z == Z1 and abs(x) <= gate_half + 1:
            continue
        p.fill(x, 0, z, x, 2, z, "Rock_Basalt_Brick")
        p.set(x, 3, z, MANOR_TRIM)
        p.set(x, 4, z, r.choice(["Deco_Lantern", "Deco_Halloween_Pumpkin_Scary"]), SOUTH)
    for x in (-gate_half - 1, gate_half + 1):
        p.fill(x, 0, Z1, x, 3, Z1, "Rock_Basalt_Brick")
        p.set(x, 4, Z1, MANOR_TRIM)
        p.set(x, 5, Z1, GARGOYLE, FACING["S"])
    for x in range(-gate_half, gate_half + 1):
        p.set(x, 4, Z1, RAILING)  # imposte en fer forgé entre les piliers
        p.set(x, -1, Z1, p.pick(PATH))
    p.set(0, 3, Z1, "Deco_Lantern_Ceiling")
    # vantaux ouverts vers l'intérieur, contre les piliers
    for x in (-gate_half, gate_half):
        p.set(x, 0, Z1 - 1, GATE, FACING["E"])
    for x in (-gate_half - 2, gate_half + 2):
        p.set(x, 0, Z1 - 1, "Furniture_Village_Brazier")

    # --- corps de logis ---------------------------------------------------------------------------
    mx0, mx1, mz0, mz1 = -13, 13, -20, -4   # bloc principal
    wings = [(-13, -7), (7, 13)]           # ailes en avancée jusqu'à z = 2
    wz1 = 2
    tx0, tx1, tz0, tz1 = -3, 3, -5, 1      # tour-porche
    top = 10                               # dernier rang de mur (étage : sol en y = 5)
    upper = 5

    p.floor(mx0, mz0, mx1, mz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    for wx0, wx1 in wings:
        p.floor(wx0, mz1, wx1, wz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    p.floor(tx0, tz0, tx1, tz1, -1, MANOR_FLOOR, FOUNDATION, depth=3)
    p.hollow(mx0, 0, mz0, mx1, top, mz1, MANOR_WALL)
    for wx0, wx1 in wings:
        p.hollow(wx0, 0, mz1, wx1, top, wz1, MANOR_WALL)
        p.clear(wx0 + 1, 0, mz1, wx1 - 1, top, mz1)   # l'aile s'ouvre sur le corps de logis
    th = 22                                # dernier rang de mur de la tour-porche
    p.hollow(tx0, 0, tz0, tx1, th, tz1, MANOR_WALL)
    p.clear(tx0 + 1, 0, tz0, tx1 - 1, top, tz0)      # la tour s'ouvre sur le hall
    # contreforts sur la façade et les pignons
    for x in (mx0, mx1, -7, 7, tx0, tx1):
        for zz in (wz1 + 1,) if x in (mx0, mx1, -7, 7) else (tz1 + 1,):
            p.fill(x, 0, zz, x, 3, zz, "Rock_Basalt_Brick")
            p.set(x, 4, zz, "Rock_Basalt_Brick_Half")
    # planchers de l'étage (bois) et plafonds
    p.fill(mx0 + 1, upper, mz0 + 1, mx1 - 1, upper, mz1 - 1, WOOD_FLOOR)
    for wx0, wx1 in wings:
        p.fill(wx0 + 1, upper, mz1, wx1 - 1, upper, wz1 - 1, WOOD_FLOOR)
    p.fill(tx0 + 1, upper, tz0, tx1 - 1, upper, tz1 - 1, WOOD_FLOOR)
    p.fill(mx0 + 1, top + 1, mz0 + 1, mx1 - 1, top + 1, mz1 - 1, MANOR_FLOOR)
    for wx0, wx1 in wings:
        p.fill(wx0 + 1, top + 1, mz1, wx1 - 1, top + 1, wz1 - 1, MANOR_FLOOR)
    # corniche ornée en haut des murs, cordon entre les niveaux
    for x in range(mx0, mx1 + 1):
        for z in (mz0, mz1):
            p.set(x, top + 1, z, MANOR_TRIM)
            p.set(x, upper, z, "Rock_Basalt_Brick_Smooth")
    for z in range(mz0, wz1 + 1):
        for x in (mx0, mx1):
            p.set(x, top + 1, z, MANOR_TRIM)
            p.set(x, upper, z, "Rock_Basalt_Brick_Smooth")
    for wx0, wx1 in wings:
        for x in range(wx0, wx1 + 1):
            p.set(x, top + 1, wz1, MANOR_TRIM)
            p.set(x, upper, wz1, "Rock_Basalt_Brick_Smooth")
        for z in range(mz1, wz1 + 1):
            p.set(wx1 if wx0 < 0 else wx0, top + 1, z, MANOR_TRIM)

    # toits pentus en ardoise : corps de logis (faîte est-ouest), ailes (pignons au sud), tour
    p.steep_roof(mx0, mz0, mx1, mz1, top + 2, MANOR_ROOF, MANOR_ROOF_HALF, ridge="x", gable_wall=MANOR_WALL)
    for wx0, wx1 in wings:
        p.steep_roof(wx0, mz1 - 2, wx1, wz1, top + 2, MANOR_ROOF, MANOR_ROOF_HALF, ridge="z", gable_wall=MANOR_WALL)
        cx = (wx0 + wx1) // 2
        p.set(cx, top + 4, wz1, GLASS_RED)       # œil-de-bœuf dans le pignon
        p.set(cx, top + 3, wz1, GLASS_RED)
        for x in (wx0, wx1):
            perched_gargoyle(p, x, top + 2, wz1 + 1, "S")
    p.fill(tx0, th + 1, tz0, tx1, th + 1, tz1, MANOR_FLOOR)
    for x in (tx0, tx1):
        for z in (tz0, tz1):
            p.set(x, th + 2, z, GARGOYLE, FACING["S" if z == tz1 else "N"])
    p.spire(0, (tz0 + tz1) // 2, 2, th + 2, MANOR_ROOF)
    for y in (top + 2, 17):                          # planchers de la tour au-dessus du toit
        p.fill(tx0 + 1, y, tz0 + 1, tx1 - 1, y, tz1 - 1, WOOD_FLOOR)
    # cheminées
    for x in (-9, 9):
        p.fill(x, top + 2, mz0 + 3, x, top + 9, mz0 + 3, "Rock_Basalt_Brick")
        p.set(x, top + 10, mz0 + 3, "Rock_Basalt_Brick_Half")
    # tour d'angle au nord-ouest, flèche
    tower(p, mx0, mz0, 3, 18, MANOR_WALL, MANOR_FLOOR, MANOR_ROOF, MANOR_TRIM, spire=True)
    # la tour mord sur l'angle du hall : passage au rez-de-chaussée par son mur est, et à l'étage
    # depuis le palier de l'escalier par son mur sud
    p.clear(mx0 + 3, 0, mz0 + 1, mx0 + 3, 2, mz0 + 2)
    p.clear(mx0 + 1, upper + 1, mz0 + 3, mx0 + 2, upper + 3, mz0 + 3)

    # --- façade : porche, porte, balcon, fenêtres -----------------------------------------------
    p.clear(-1, 0, tz1, 1, 3, tz1)
    p.fill(-2, 4, tz1, 2, 4, tz1, MANOR_TRIM)
    p.set(0, 5, tz1, MANOR_TRIM)
    for x in (-1, 1):
        p.set(x, 0, tz1 - 1, GATE, FACING["E"])  # vantaux ouverts dans l'embrasure
    for x in (-3, 3):
        p.set(x, 0, tz1 + 3, "Rock_Basalt_Brick_Pillar_Base")
        p.fill(x, 1, tz1 + 3, x, 3, tz1 + 3, "Rock_Basalt_Brick_Pillar_Middle")
    p.fill(-3, 4, tz1 + 1, 3, 4, tz1 + 3, "Rock_Basalt_Brick_Smooth")   # dalle du porche = balcon
    for x in range(-3, 4):
        p.set(x, 5, tz1 + 3, RAILING)
    for z in (tz1 + 1, tz1 + 2):
        p.set(-3, 5, z, RAILING)
        p.set(3, 5, z, RAILING)
    p.set(0, 3, tz1 + 2, "Deco_Lantern_Ceiling")
    p.clear(0, upper + 1, tz1, 0, upper + 2, tz1)         # porte-fenêtre sur le balcon
    p.set(0, upper + 3, tz1, MANOR_TRIM)
    rose_window(p, 0, 14, z=tz1)
    for x in (-2, 2):
        lancet(p, x, upper + 1, tz1, GLASS_VIOLET)
        lancet(p, x, 13, tz1, GLASS_VIOLET, height=3)
    for x in (-1, 1):
        lancet(p, x, 18, tz1, GLASS_RED, height=3)  # baies hautes de la tour
    for x in (tx0, tx1):
        lancet(p, x, 18, tz1 - 2, GLASS_RED, height=3)
    for wx0, wx1 in wings:
        for x in range(wx0 + 2, wx1 - 1, 2):
            lancet(p, x, 1, wz1, GLASS_RED)
            lancet(p, x, upper + 2, wz1, GLASS_RED)
        side = wx0 if wx0 < 0 else wx1
        for z in (mz1 + 2, wz1 - 2):
            lancet(p, side, 1, z, GLASS_VIOLET)
            lancet(p, side, upper + 2, z, GLASS_VIOLET)
    for x in (-5, 5):                                 # façade entre les ailes et la tour
        lancet(p, x, 1, mz1, GLASS_RED)
        lancet(p, x, upper + 2, mz1, GLASS_RED)
    for x in range(mx0 + 3, mx1 - 2, 4):              # façade nord
        lancet(p, x, 1, mz0, GLASS_VIOLET)
        lancet(p, x, upper + 2, mz0, GLASS_VIOLET)
    for z in range(mz0 + 4, mz1 - 1, 4):              # pignons est et ouest
        lancet(p, mx1, 1, z, GLASS_RED)
        lancet(p, mx1, upper + 2, z, GLASS_RED)
        if z > mz0 + 4:
            lancet(p, mx0, 1, z, GLASS_RED)
            lancet(p, mx0, upper + 2, z, GLASS_RED)
    rose_window(p, (mz0 + mz1) // 2, top + 4, x=mx1)
    rose_window(p, (mz0 + mz1) // 2, top + 4, x=mx0)

    # --- rez-de-chaussée --------------------------------------------------------------------------
    for z in range(mz0 + 1, tz1 + 1):                # tapis rouge de la porte au trône
        for x in (-1, 0, 1):
            p.set(x, -1, z, "Cloth_Block_Wool_Red")
    for z in range(mz0 + 3, mz1, 4):                 # piliers du hall
        for x in (-5, 5):
            p.set(x, 0, z, "Rock_Basalt_Brick_Pillar_Base")
            p.fill(x, 1, z, x, upper - 1, z, "Rock_Basalt_Brick_Pillar_Middle")
    for z in (mz0 + 5, mz0 + 11):
        p.set(0, upper - 1, z, "Furniture_Feran_Chandelier")
    # trône sur une estrade, au fond du hall
    p.fill(-3, 0, mz0 + 1, 3, 0, mz0 + 2, "Rock_Basalt_Brick_Smooth")
    p.fill(-1, 1, mz0 + 1, 1, 1, mz0 + 1, "Cloth_Block_Wool_Red")
    p.fill(-1, 2, mz0 + 1, 1, 3, mz0 + 1, MANOR_TRIM)
    p.set(0, 4, mz0 + 1, "Furniture_Outlander_Banner", SOUTH)
    p.set(0, 1, mz0 + 2, "Furniture_Royal_Magic_Chair", SOUTH)
    for x in (-3, 3):
        p.set(x, 1, mz0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
        p.set(x, 0, mz0 + 3, "Furniture_Temple_Dark_Brazier")
    # le comte ou la comtesse attend devant son trône (marqueur invisible du mod nakasar-mobs)
    p.set(0, 0, mz0 + 5, "Nakasar_Spawner_Vampire_Count")
    # cheminées monumentales sur le mur du fond
    for x in (-9, 9):
        p.clear(x - 1, 0, mz0, x + 1, 1, mz0)
        p.set(x, -1, mz0, "Rock_Basalt_Brick_Smooth")
        p.set(x, 0, mz0, "Furniture_Temple_Dark_Brazier")
        p.fill(x - 2, 2, mz0 + 1, x + 2, 2, mz0 + 1, MANOR_TRIM)
        p.fill(x - 2, 0, mz0 + 1, x - 2, 1, mz0 + 1, "Rock_Basalt_Brick")
        p.fill(x + 2, 0, mz0 + 1, x + 2, 1, mz0 + 1, "Rock_Basalt_Brick")
        p.set(x, 3, mz0 + 1, "Furniture_Ancient_Painting", SOUTH)
        p.set(x - 1, 3, mz0 + 1, p.pick(CANDLES))
        p.set(x + 1, 3, mz0 + 1, p.pick(CANDLES))
    # salle à manger (aile ouest)
    wx0, wx1 = wings[0]
    for z in range(mz1 - 3, wz1):
        p.set(-10, 0, z, "Furniture_Temple_Dark_Table")
        p.set(-11, 0, z, "Furniture_Royal_Magic_Chair", EAST)
        p.set(-9, 0, z, "Furniture_Royal_Magic_Chair", WEST)
    p.set(-10, upper - 1, mz1 - 1, "Furniture_Tavern_Chandelier")
    p.set(-12, 0, mz1 - 5, "Furniture_Temple_Dark_Wardrobe", EAST)
    p.set(-12, 0, wz1 - 1, p.pick(CANDLES))
    p.set(-8, 0, wz1 - 1, p.pick(CANDLES))
    # bibliothèque (aile est)
    for z in range(mz1 - 1, wz1):
        p.set(12, 0, z, "Furniture_Ancient_Bookshelf", WEST)
        p.set(12, 1, z, "Furniture_Ancient_Bookshelf", WEST)
    for x in range(9, 12):
        p.set(x, 0, mz1 - 6, "Furniture_Human_Ruins_Bookshelf", SOUTH)
    p.set(10, 0, wz1 - 2, "Furniture_Temple_Dark_Table")
    p.set(10, 0, wz1 - 1, "Furniture_Royal_Magic_Chair", NORTH)
    p.set(8, 0, wz1 - 1, "Furniture_Temple_Dark_Candle")
    p.set(10, upper - 1, mz1 - 1, "Furniture_Tavern_Chandelier")
    # escalier vers l'étage, le long du mur ouest du hall (monte vers le nord)
    sx0, sx1 = mx0 + 1, mx0 + 2
    zs = stairs_up(p, sx0, sx1, mz1 - 1, -1, upper + 1, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Half")
    for i, z in enumerate(zs):
        if (i + 1) / 2 >= 2:                         # trémie dans le plancher au-dessus des marches
            for x in (sx0, sx1):
                if p.get(x, upper, z) in [n for n, _ in WOOD_FLOOR]:
                    p.set(x, upper, z, AIR)
        if 4 <= i < len(zs) - 1:
            p.set(sx1 + 1, upper + 1, z, RAILING)       # garde-corps autour de la trémie
    # crypte sous le hall : un escalier descend de l'angle sud-est
    depth = 5
    cy0 = -depth - 1
    cx0, cx1, cz0, cz1 = -10, 10, mz0 + 1, mz1 - 1
    for x in range(cx0 - 1, cx1 + 2):
        for z in range(cz0 - 1, cz1 + 2):
            p.set(x, cy0, z, p.pick(MANOR_WALL))
            p.set(x, cy0 - 1, z, p.pick(FOUNDATION))
            for y in range(cy0 + 1, -1):
                if x in (cx0 - 1, cx1 + 1) or z in (cz0 - 1, cz1 + 1):
                    p.set(x, y, z, p.pick(MANOR_WALL))
    p.floor(cx0, cz0, cx1, cz1, cy0, MANOR_FLOOR)
    p.clear(cx0, cy0 + 1, cz0, cx1, -2, cz1)
    stairs_down(p, (cx1 - 1, cz1), (0, -1), depth, "Rock_Basalt_Brick", "Rock_Basalt_Brick_Half", MANOR_WALL, width=2)
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
    for px in (-5, 4):
        p.fill(px, cy0 + 1, mid, px, -2, mid, "Rock_Basalt_Brick_Pillar_Middle")
        p.set(px, cy0 + 1, mid - 1, "Furniture_Temple_Dark_Brazier")
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 10, CANDLES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 8, BONES)
    p.scatter(cx0 + 1, cy0 + 1, cz0 + 1, cx1 - 3, cz1 - 1, 4, [("Rock_Crystal_Red_Small", 1)])

    # --- étage ------------------------------------------------------------------------------------
    y = upper + 1
    # chambre du comte (est) : lit à baldaquin, cercueil, coffre
    p.fill(6, y, mz0 + 1, 6, top, mz1 - 1, MANOR_WALL)           # cloison
    p.clear(6, y, mz1 - 3, 6, y + 1, mz1 - 3)                     # porte
    p.set(10, y, mz0 + 2, "Furniture_Royal_Magic_Bed", SOUTH)
    p.set(8, y, mz0 + 1, "Furniture_Temple_Dark_Coffin", SOUTH)
    p.set(12, y, mz0 + 5, "Furniture_Temple_Dark_Chest_Large", WEST)
    p.set(12, y, mz0 + 8, "Furniture_Royal_Magic_Wardrobe", WEST)
    p.set(9, top, mz0 + 7, "Furniture_Feran_Chandelier")
    p.set(7, y, mz0 + 1, p.pick(CANDLES))
    # boudoir de la comtesse (ouest, derrière l'escalier) : lit, coiffeuse, banquette
    p.fill(-6, y, mz0 + 1, -6, top, mz1 - 1, MANOR_WALL)
    p.clear(-6, y, mz1 - 3, -6, y + 1, mz1 - 3)
    p.set(-10, y, mz0 + 2, "Furniture_Temple_Dark_Bed", SOUTH)
    p.set(-8, y, mz0 + 1, "Furniture_Royal_Magic_Couch", SOUTH)
    p.set(-8, y, mz0 + 7, "Furniture_Royal_Magic_Table", WEST)
    p.set(-8, y + 1, mz0 + 7, "Furniture_Royal_Magic_Potion_Glow")
    p.set(-9, top, mz0 + 7, "Furniture_Feran_Chandelier")
    # galerie centrale : tableaux et statues face aux fenêtres
    for x in (-3, 0, 3):
        p.set(x, y + 1, mz0 + 1, "Furniture_Ancient_Painting", SOUTH)
    for x in (-4, 4):
        p.set(x, y, mz0 + 1, "Furniture_Temple_Dark_Statue", SOUTH)
    for z in range(mz0 + 2, mz1, 2):
        p.set(0, y - 1, z, "Cloth_Block_Wool_Red")
    p.set(0, top, mz0 + 8, "Furniture_Feran_Chandelier")
    # chambres des ailes : armoires et coffres
    p.set(-12, y, wz1 - 1, "Furniture_Temple_Dark_Wardrobe", EAST)
    p.set(12, y, wz1 - 1, "Furniture_Temple_Dark_Wardrobe", WEST)
    p.set(-8, y, wz1 - 1, "Furniture_Temple_Dark_Chest_Large", NORTH)
    p.set(8, y, wz1 - 1, "Furniture_Ancient_Chest_Large", NORTH)
    # combles : toiles d'araignée sous le toit
    for _ in range(40):
        x, z = r.randint(mx0 + 1, mx1 - 1), r.randint(mz0 + 1, mz1 - 1)
        for yy in range(top + 2, top + 14):
            if p.get(x, yy, z) not in (None, AIR):
                if p.free(x, yy - 1, z) and yy - 1 > top + 1:
                    p.set(x, yy - 1, z, p.pick(WEBS))
                break

    # --- jardin -------------------------------------------------------------------------------------
    for z in range(tz1 + 1, Z1):                     # allée de la grille au porche
        for x in (-1, 0, 1):
            p.set(x, -1, z, p.pick(PATH))
        if z % 4 == 0 and z > tz1 + 4:
            for x in (-3, 3):
                lantern_post(p, x, z, 2)
    for x in (-5, 5):                                # statues sur socle et gargouilles dans l'allée
        p.set(x, 0, 14, "Rock_Basalt_Brick")
        p.set(x, 1, 14, MANOR_TRIM)
        p.set(x, 2, 14, GARGOYLE, FACING["E" if x < 0 else "W"])
    for x0b in (-24, 9):                              # roseraies de sang
        for x in range(x0b, x0b + 15):
            for z in range(7, 20):
                if (x % 3 == 0 and z % 2 == 0) and abs(x) > 6 and r.random() < 0.7:
                    p.set(x, -1, z, "Soil_Dirt")
                    p.set(x, 0, z, r.choice(["Plant_Crop_Health1", "Plant_Petals_Blood", "Plant_Crop_Health2", "Plant_Petals_Blood"]))
    for tx, tz, hanging in ((-18, 4, "noose"), (19, 4, "cage")):
        p.paste(dead_tree(r.randint(0, 1 << 30), "medium", species="Burnt", hanging=hanging), tx, 0, tz, min_y=0)
    # tombes de famille à l'est, mausolée à l'ouest, derrière le logis
    for x in range(17, 26, 3):
        for z in (-20, -16, -12):
            grave(p, x, z, r, r.choice(["undead", "haunted"]))
    mausoleum(p, -25, -21, r, door_south=True)
    p.scatter(-X + 2, 0, Z0 + 2, X - 2, Z1 - 2, 14, PUMPKINS)
    p.scatter(-X + 2, 0, Z0 + 2, X - 2, Z1 - 2, 10, BONES)
    p.scatter(-X + 2, 0, Z0 + 2, X - 2, Z1 - 2, 20, DEAD_PLANTS)
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
    jobs.append(("VampireManor/Vampire_Manor", vampire_manor(6000)))
    jobs.append(("SpawnCrypt/Spawn_Crypt", spawn_crypt(6100)))
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
