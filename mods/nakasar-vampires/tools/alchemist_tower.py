"""La Tour de l'Alchimiste elle-même (étape 2 du donjon) : prefab de la tour, utilisé par generate_alchemist_tower.py.

Échelle Deepworks (Kevin, 19 octobre 2026) : environ 67 blocs de diamètre (balcons 95) et 220 de haut ;
generate_alchemist_tower.py coupe le prefab en tranches empilées.

Repère du prefab : centré sur l'axe de la tour, y = 0 = première couche d'air au-dessus du sol de l'île (y = -1 : sol).
Les angles sont en degrés : x = r cos(a), z = r sin(a), donc 0 = est, 90 = sud, 180 = ouest, 270 = nord.

Parcours, de bas en haut (niveaux = première couche d'air du sol de chaque salle) :

- parvis au sud, porte du Hall des Alambics (niveau 0) ; rampe le long du mur de 200 à 300° ;
- Couloir des fuites (22) : anneau autour d'un cœur plein, barré à 240°, on en fait les trois quarts jusqu'à la porte
  ouest ; tuyaux, niches et grilles de vapeur (les jets viendront avec les pièges) ;
- Serre suspendue (22) : balcon extérieur d'ouest en est par le nord, verrière à l'ouest, belvédère au nord ; une rampe
  extérieure monte de 0 à 50° jusqu'à la porte de la bibliothèque ;
- Bibliothèque (36) : rotonde à deux galeries, étagères, salle secrète en encorbellement à 320° ; rampe de 70 à 205° ;
- Salle des Transmutations (66) : salle carrée en quatre quadrants (feu, glace, acide, foudre) ; escalier le long du
  mur nord vers le laboratoire ;
- Laboratoire (84) : cuve centrale ; porte nord vers l'Escalier des vents ;
- Escalier des vents : rampe extérieure de 262 à 602° (presque un tour), de 84 à l'Observatoire (144) ;
- Observatoire (144) : terrasse ronde au sommet, antichambre sur l'arrivée de l'escalier, Bureau de l'Alchimiste au sud.

Toutes les rampes montent en demi-dalles (pas de bloc orienté à deviner) et tous les bords extérieurs ont un parapet de
2 blocs au moins. `walkable_path` vérifie, hors ligne, qu'on va du parvis au bureau en passant par chaque point de
contrôle.
"""
import math
from collections import deque

import generate_prefabs as pf

AIR = pf.AIR
# Échelle de Deepworks (Kevin, 19 octobre 2026) : tout est deux fois plus grand que le premier jet, en largeur comme en
# hauteur, pour garder la pente des rampes (au plus un demi-bloc par bloc).
R_IN = 29.5        # intérieur de la tour : d < R_IN
R_OUT = 33.5       # mur : R_IN <= d < R_OUT
F_HALL, F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_DECK = 0, 22, 36, 66, 84, 144
DECK_R = 45.5      # terrasse de l'observatoire : d < DECK_R, parapet jusqu'à DECK_R + 1
BALCONY_R = 47.5   # serre : R_OUT <= d < BALCONY_R, parapet jusqu'à BALCONY_R + 1
BALCONY_ARC = (176, 360)
GREENHOUSE_ARC = (195, 285)
SQUARE = 18        # Salle des Transmutations : |x|, |z| <= SQUARE
COURT_HALF = 16    # parvis : x de -16 à 16
COURT_END = 79     # le parvis va jusqu'à z = 79 ; le pont arrive en z = 80
BRIDGE_HALF = 3    # demi-largeur du pont (generate_alchemist_tower.BRIDGE_HALF)

WALL = [("Rock_Marble_Brick", 7), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
FLOOR = [("Rock_Marble_Brick_Smooth", 4), ("Rock_Marble_Brick", 3)]
HALF = "Rock_Marble_Brick_Half"
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
PARAPET, PARAPET_TOP = "Rock_Marble_Brick", "Rock_Marble_Brick_Wall"
GLASS = "Nakasar_Stained_Glass_Violet"
STATUE = "Furniture_Temple_Light_Statue"
SHELF = "Furniture_Bookshelf_Single"
LANTERN = "Furniture_Temple_Light_Lantern"
GLOW = "Furniture_Royal_Magic_Potion_Glow"
BRAZIER = "Furniture_Temple_Dark_Brazier"
CHANDELIER = "Furniture_Feran_Chandelier"

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
START = (0, 0, 70)  # parvis devant la porte du hall : (x, surface en demi-blocs, z) dans le repère du prefab


def polar(x, z):
    return math.hypot(x, z), math.degrees(math.atan2(z, x)) % 360


def in_arc(a, a0, a1):
    """L'angle a est-il sur l'arc parcouru dans le sens positif de a0 à a1 (a1 - a0 <= 360) ?"""
    return (a - a0) % 360 <= a1 - a0


def ring(r0, r1, reach=None):
    """Cases (x, z) avec r0 <= d < r1."""
    reach = math.ceil(r1) + 1 if reach is None else reach
    for x in range(-reach, reach + 1):
        for z in range(-reach, reach + 1):
            d, a = polar(x, z)
            if r0 <= d < r1:
                yield x, z, d, a


def facing_center(x, z):
    """Lacet d'un meuble posé en (x, z) pour qu'il regarde l'axe de la tour (0 = sud, 1 = est, 2 = nord, 3 = ouest)."""
    if abs(x) > abs(z):
        return pf.WEST if x > 0 else pf.EAST
    return pf.NORTH if z > 0 else pf.SOUTH


def at(r, a):
    return round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))


class Tower:
    def __init__(self, seed):
        self.p = pf.Prefab(seed)
        self.rng = self.p.rng
        self.walk = {}       # (x, z) -> {surface en demi-blocs} : sols des rampes, balcons, terrasse, portes
        self.keep_clear = set()  # cases (x, y, z) que le décor ne doit pas prendre
        self.parapets = set()    # blocs (x, y, z) de parapet (tout bloc posé par-dessus les en retire)
        place = self.p.set

        def set_block(x, y, z, *args, **kwargs):
            self.parapets.discard((x, y, z))
            return place(x, y, z, *args, **kwargs)
        self.p.set = set_block
        self.checkpoints = []    # (x, y, z) relatifs, dans l'ordre du parcours

    # --- primitives ---------------------------------------------------------------------------

    def wall(self):
        return self.p.pick(WALL)

    def floor(self):
        return self.p.pick(FLOOR)

    def solid(self, x, y, z):
        b = self.p.get(x, y, z)
        return b not in (None, AIR) and not passable(b)

    def register(self, x, z, s):
        self.walk.setdefault((x, z), set()).add(s)

    def step(self, x, z, s, support=2):
        """Sol de surface s (en demi-blocs) en (x, z) : demi-dalle si s est impair."""
        y = s // 2
        if s % 2:
            self.p.set(x, y, z, HALF)
            self.p.set(x, y - 1, z, self.floor())
        else:
            self.p.set(x, y - 1, z, self.floor())
        base = (y - 2) if s % 2 == 0 else (y - 2)
        for k in range(support):
            if not self.solid(x, base - k, z):
                self.p.set(x, base - k, z, self.wall())
        self.register(x, z, s)

    def carve(self, x, z, s, height=3):
        """Dégage `height` blocs au-dessus de la surface s (seulement les blocs déjà posés)."""
        y0 = (s + 1) // 2
        for y in range(y0, y0 + height):
            if self.p.get(x, y, z) not in (None, AIR):
                self.p.set(x, y, z, AIR)
            self.keep_clear.add((x, y, z))

    def door(self, cells, y, height=3):
        """Ouvre une baie dans un mur : les cases (x, z) deviennent un passage de sol y."""
        for x, z in cells:
            for k in range(height):
                self.p.set(x, y + k, z, AIR)
                self.keep_clear.add((x, y + k, z))
            if not self.solid(x, y - 1, z):
                self.p.set(x, y - 1, z, self.floor())
            self.register(x, z, 2 * y)

    def parapet(self, x, y, z, high=2):
        for k in range(high):
            if self.p.free(x, y + k, z):
                self.p.set(x, y + k, z, PARAPET if k < high - 1 else PARAPET_TOP)
                self.parapets.add((x, y + k, z))

    def helix(self, a0, a1, r0, r1, y0, y1, flat=6.0, support=2):
        """Rampe hélicoïdale de a0 à a1 (sens positif, moins d'un tour) entre les rayons r0 et r1, du sol y0 au sol
        y1 ; `flat` degrés de palier à chaque bout. Renvoie {(x, z): surface en demi-blocs}."""
        span = a1 - a0
        cells = {}
        for x, z, d, a in ring(r0, r1):
            rel = (a - a0) % 360
            if rel > span:
                continue
            t = min(1.0, max(0.0, (rel - flat) / (span - 2 * flat)))
            cells[(x, z)] = round(2 * (y0 + (y1 - y0) * t))
        for (x, z), s in cells.items():
            self.step(x, z, s, support)
        for (x, z), s in cells.items():
            self.carve(x, z, s)
        return cells

    def guard(self, cells):
        """Parapets autour d'un groupe de sols extérieurs : sur chaque voisin vide et sans sol au même niveau, et sur le
        bord haut d'une marche de plus d'un bloc (trémie d'escalier). Le haut de chaque parapet dépasse de 2 blocs la
        plus haute marche voisine, sinon une rampe qui monte le long du parapet permettrait de sauter dessus."""
        need = {}  # (x, z) -> [[bas, haut exclu], ...]
        for (x, z), s in sorted(cells.items()):
            y = (s + 1) // 2
            top = (s + 5) // 2
            for dx, dz in DIRS8:
                n = (x + dx, z + dz)
                levels = self.walk.get(n, set())
                if any(abs(o - s) <= 2 for o in levels):
                    continue
                if any(s - 12 <= o < s - 2 for o in levels):
                    target = (x, z)  # trémie : garde-corps sur la case haute
                elif self.p.get(n[0], y, n[1]) in (None, AIR) and not self.solid(n[0], y - 1, n[1]):
                    target = n
                else:
                    continue
                segs = need.setdefault(target, [])
                for seg in segs:
                    if seg[0] - 4 <= y <= seg[1] + 2:
                        seg[0], seg[1] = min(seg[0], y), max(seg[1], top)
                        break
                else:
                    segs.append([y, top])
                if target == (x, z):
                    break
        for (x, z), segs in need.items():
            for lo, hi in segs:
                for y in range(lo, hi):
                    if self.p.free(x, y, z):
                        self.p.set(x, y, z, PARAPET if y < hi - 1 else PARAPET_TOP)
                        self.parapets.add((x, y, z))

    def light_ring(self, r, y, every, name=LANTERN, skip=()):
        for k in range(0, 360, every):
            if any(in_arc(k, a0, a1) for a0, a1 in skip):
                continue
            x, z = at(r, k)
            if self.place(x, y, z, name):
                pass

    def place(self, x, y, z, name, rot=0):
        """Pose un meuble s'il tient (cases libres, sol plein) et ne gêne aucun passage."""
        cells = pf.footprint(name, rot)
        if any((x + dx, y + dy, z + dz) in self.keep_clear for dx, dy, dz in cells):
            return False
        if not self.p.fits(x, y, z, name, rot):
            return False
        self.p.set(x, y, z, name, rot)
        return True

    # --- gros œuvre ---------------------------------------------------------------------------

    def shell(self):
        p = self.p
        for x, z, d, a in ring(0, R_OUT):
            p.set(x, -1, z, self.floor() if d < R_IN else self.wall())
            for y in range(-6, -1):
                p.set(x, y, z, "Rock_Marble")
            if d >= R_IN:
                for y in range(0, F_DECK - 1):
                    p.set(x, y, z, self.wall())
            for f in (F_LEAKS, F_LIBRARY, F_TRANS, F_LAB, F_LAB + 24, F_DECK):
                p.set(x, f - 1, z, self.floor() if d < R_IN else TRIM)
        # Cœur plein du couloir des fuites, barrage à 240°, remplissage autour de la salle carrée.
        for x, z, d, a in ring(0, R_IN):
            for y in range(F_LEAKS, F_LIBRARY - 1):
                if d < 18 or (d < R_IN and in_arc(a, 237, 243)):
                    p.set(x, y, z, self.wall())
            if max(abs(x), abs(z)) > SQUARE:
                for y in range(F_TRANS, F_LAB - 1):
                    p.set(x, y, z, self.wall())
        # Fenêtres de verre (points de vue fermés) : hall, bibliothèque, laboratoire, fût.
        for y0, y1, step, a_off in ((5, 13, 30, 15), (42, 56, 20, 10), (89, 98, 30, 0), (112, 132, 30, 15)):
            for k in range(a_off, 360 + a_off, step):
                for x, z, d, a in ring(R_IN, R_OUT):
                    if abs(((a - k) + 180) % 360 - 180) < 2.2:
                        for y in range(y0, y1 + 1):
                            p.set(x, y, z, GLASS)

    def court(self):
        """Parvis au pied de la tour : dallage, parapets est, ouest et sud (ouvert sur le pont), porte du hall."""
        p = self.p
        x0, x1, z1 = -COURT_HALF, COURT_HALF, COURT_END
        for x in range(x0 - 1, x1 + 2):
            for z in range(16, z1 + 2):
                d, a = polar(x, z)
                if d < R_OUT:
                    continue
                edge = x in (x0 - 1, x1 + 1) or z == z1 + 1
                p.set(x, -1, z, TRIM if (x == 0 and z % 4 == 0) else self.floor())
                if edge and not (z == z1 + 1 and abs(x) <= BRIDGE_HALF):
                    self.parapet(x, 0, z)
                    if z % 8 == 0 or (z == z1 + 1 and abs(x) in (BRIDGE_HALF + 1, x1 + 1)):
                        p.set(x, 2, z, "Deco_Lantern")
                else:
                    self.register(x, z, 0)
        # Porte du hall : arche dorée.
        door = [(x, z) for x in range(-2, 3) for z in range(27, 35)]
        self.door(door, 0, 8)
        for x in (-3, 3):
            for z in (32, 33, 34):
                for y in range(0, 9):
                    p.set(x, y, z, GOLD)
        for x in range(-3, 4):
            for z in (32, 33, 34):
                p.set(x, 8, z, "Rock_Gold_Brick_Ornate")

    def hall(self):
        cells = self.helix(200, 300, 23, R_IN, F_HALL, F_LEAKS)
        self.hall_ramp = cells
        p = self.p
        # Alambic central : colonne de verre et d'or autour d'un cœur de cristal.
        for y in range(0, 14):
            for x, z, d, a in ring(0, 5):
                p.set(x, y, z, "Rock_Crystal_Green_Block" if d < 2.5 else (GLASS if 1 <= y <= 11 else GOLD))
        for x, z, d, a in ring(0, 3.5):
            p.set(x, 14, z, GOLD)
        for x, z, d, a in ring(0, 2):
            p.set(x, 15, z, GOLD)
        p.set(0, 16, 0, "Rock_Gold_Brick_Ornate")
        # Athanors (l'énigme des trois feux viendra avec les pièges), chaudrons, établis d'alchimie.
        for k in (30, 150, 330):
            x, z = at(14, k)
            self.place(x, 0, z, "Bench_Furnace", facing_center(x, z))
        for k in range(0, 200, 30):
            x, z = at(25, k)
            self.place(x, 0, z, "Alchemy_Cauldron_Big")
        for k in (90 - 20, 90 + 20, 15, 165):
            x, z = at(21, k)
            self.place(x, 0, z, "Bench_Alchemy", facing_center(x, z))
        self.light_ring(27.5, 0, 15, skip=((195, 305), (82, 98)))
        for x, z in ((12, 12), (-12, 12), (12, -12), (-12, -12), (0, 18), (0, -18), (18, 0), (-18, 0)):
            self.place(x, 18, z, CHANDELIER)

    def leaks(self):
        """Couloir des fuites : anneau de 9 à 14,5, tuyaux au plafond, niches et grilles de vapeur dans le cœur."""
        p = self.p
        y = F_LEAKS
        for x, z, d, a in ring(27.5, R_IN):
            for dy in (9, 10):
                p.set(x, y + dy, z, GOLD)  # conduite qui court au plafond le long du mur
        for k in range(0, 360, 10):
            if in_arc(k, 232, 248) or in_arc(k, 262, 305):
                continue
            x, z = at(17.5, k)
            if self.solid(x, y, z):
                for dy in range(0, 4):
                    p.set(x, y + dy, z, AIR)
                xi, zi = at(16.5, k)
                p.set(xi, y + 1, zi, "Deco_Iron_Bars")  # bouche de vapeur
                p.set(xi, y + 2, zi, "Deco_Iron_Bars")
                p.set(x, y, z, GLOW)
            xo, zo = at(28, k + 5)
            for dy in range(0, 9):
                if self.p.free(xo, y + dy, zo):
                    p.set(xo, y + dy, zo, "Rock_Gold_Brick_Pillar_Middle")  # colonne montante
        # Porte ouest vers la serre.
        door = [(x, z) for x in range(-35, -27) for z in range(-2, 3)]
        self.door(door, F_LEAKS, 5)

    def greenhouse(self):
        p = self.p
        cells = {}
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *BALCONY_ARC):
                continue
            if d < BALCONY_R:
                p.set(x, F_LEAKS - 1, z, TRIM if 39.5 <= d < 40.5 else self.floor())
                p.set(x, F_LEAKS - 2, z, self.wall())
                cells[(x, z)] = 2 * F_LEAKS
                self.register(x, z, 2 * F_LEAKS)
                if d >= 44.5 and int(a) % 12 < 9:  # plates-bandes le long du parapet
                    p.set(x, F_LEAKS, z, "Soil_Grass_Full")
                    del cells[(x, z)]
                    self.walk[(x, z)].discard(2 * F_LEAKS)
                    plant = self.rng.choice(["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green",
                                             "Plant_Flower_Orchid_Purple", "Plant_Flower_Tall_Cyan", "Plant_Grass_Lush"])
                    p.set(x, F_LEAKS + 1, z, plant)
            else:
                self.parapet(x, F_LEAKS, z)
                if int(a) % 15 == 0 and not in_arc(a, *GREENHOUSE_ARC):
                    p.set(x, F_LEAKS + 2, z, "Deco_Lantern")
            # Corbeaux sous le balcon.
            if d >= BALCONY_R - 1 and int(a) % 8 < 2:
                for k in range(2, 9):
                    p.set(x, F_LEAKS - 1 - k, z, self.wall())
        # Verrière : panneaux sur le parapet et toit de verre, arceaux dorés.
        for x, z, d, a in ring(R_OUT, BALCONY_R + 1):
            if not in_arc(a, *GREENHOUSE_ARC):
                continue
            if d >= BALCONY_R:
                for y in range(F_LEAKS + 2, F_LEAKS + 11):
                    p.set(x, y, z, GOLD if int(a) % 8 < 2 else GLASS)
            p.set(x, F_LEAKS + 11, z, GOLD if int(a) % 8 < 2 else GLASS)
        self.guard(cells)
        # Rampe extérieure de la serre à la porte de la bibliothèque.
        ramp = self.helix(0, 50, R_OUT, 41, F_LEAKS, F_LIBRARY, flat=5)
        self.lib_ramp = ramp
        door = {(x, z) for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.5) if abs(a - 50) < 5}
        self.door(door, F_LIBRARY, 5)
        self.guard(ramp)

    def library(self):
        p = self.p
        ramp = self.helix(70, 205, 23, R_IN, F_LIBRARY, F_TRANS, flat=4)
        self.library_ramp = ramp
        # Garde-corps intérieur de la rampe (muret d'un bloc).
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d < 24.5 and s > 2 * F_LIBRARY + 8:
                y = (s + 1) // 2
                if p.free(x, y, z):
                    p.set(x, y, z, PARAPET_TOP)
        # Étagères sur quatre rangs le long du mur, hors rampe, porte et passage secret.
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 60, 215) or in_arc(a, 44, 56) or in_arc(a, 315, 325) or in_arc(a, 25, 35):
                continue
            for y in range(F_LIBRARY, F_LIBRARY + 8):
                self.place(x, y, z, SHELF, facing_center(x, z))
        # Rayonnages en épis et piles de livres.
        for k in (235, 255, 275, 295, 340, 0):
            for r in range(15, 24):
                x, z = at(r, k)
                for y in range(F_LIBRARY, F_LIBRARY + 4):
                    self.place(x, y, z, SHELF, facing_center(x, z))
        for k in range(0, 360, 30):
            x, z = at(11, k + 15)
            self.place(x, F_LIBRARY, z, "Deco_Book_Pile_Large")
        self.place(0, F_TRANS - 4, 0, CHANDELIER)
        for x, z in ((12, 0), (-12, 0), (0, 12), (0, -12)):
            self.place(x, F_TRANS - 6, z, CHANDELIER)
        self.light_ring(21, F_LIBRARY, 30, skip=((60, 215),))
        # Galeries hautes : anneaux de planches sur corbeaux, avec rayonnages (décor).
        for g in (14, 22):
            for x, z, d, a in ring(25, R_IN):
                if in_arc(a, 60, 215):
                    continue
                p.set(x, F_LIBRARY + g, z, "Wood_Darkwood_Planks")
            for x, z, d, a in ring(28.4, R_IN):
                if in_arc(a, 60, 215):
                    continue
                for y in range(F_LIBRARY + g + 1, F_LIBRARY + g + 6):
                    self.place(x, y, z, SHELF, facing_center(x, z))
        # Salle secrète en encorbellement à 320° (le coffre viendra avec le butin).
        cx, cz = at(39, 320)
        y = F_LIBRARY
        for x in range(cx - 6, cx + 7):
            for z in range(cz - 6, cz + 7):
                edge = x in (cx - 6, cx + 6) or z in (cz - 6, cz + 6)
                if polar(x, z)[0] < R_OUT:
                    continue
                p.set(x, y - 1, z, "Wood_Darkwood_Planks")
                p.set(x, y - 2, z, self.wall())
                p.set(x, y + 7, z, self.wall())
                for k in range(0, 7):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
        for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.6):
            if abs(a - 320) < 2.2:
                self.door([(x, z)], y, 3)
        self.place(cx, y, cz, GLOW)

    def transmutation(self):
        p = self.p
        y = F_TRANS
        quadrants = {(1, -1): "Rock_Crystal_Red_Block", (-1, -1): "Rock_Crystal_Cyan_Block",
                     (1, 1): "Rock_Crystal_Green_Block", (-1, 1): "Rock_Crystal_Yellow_Block"}
        for x in range(-SQUARE, SQUARE + 1):
            for z in range(-SQUARE, SQUARE + 1):
                if x == 0 or z == 0:
                    p.set(x, y - 1, z, TRIM)
                    continue
                q = quadrants[(1 if x > 0 else -1, 1 if z > 0 else -1)]
                p.set(x, y - 1, z, q if (x + z) % 3 == 0 else self.floor())
        # Couloir depuis la rampe de la bibliothèque, à l'ouest.
        for x in range(-27, -SQUARE):
            for z in range(-13, -5):
                self.door([(x, z)], y, 5)
        # Escalier le long du mur nord, vers le laboratoire.
        stair = {}
        for x in range(-SQUARE, SQUARE + 1):
            for z in (-17, -16, -15, -14):
                stair[(x, z)] = 2 * y + (x + SQUARE)
        for (x, z), s in stair.items():
            self.step(x, z, s, support=0)
            # mur plein sous les marches
            for k in range(y, (s + 1) // 2 - 1):
                p.set(x, k, z, self.wall())
        for (x, z), s in stair.items():
            self.carve(x, z, s)
        for x in range(SQUARE + 1, SQUARE + 7):
            for z in (-17, -16, -15, -14):
                self.register(x, z, 2 * F_LAB)
                self.keep_clear.update((x, F_LAB + k, z) for k in range(3))
        self.trans_stair = stair
        for x, z in ((-SQUARE, SQUARE), (SQUARE, SQUARE), (-SQUARE, -12), (SQUARE, -12), (0, SQUARE), (-SQUARE, 0),
                     (SQUARE, 0)):
            self.place(x, y, z, BRAZIER)
        for x, z in ((0, 0), (9, 9), (-9, 9), (9, -9), (-9, -9)):
            self.place(x, F_LAB - 4, z, CHANDELIER)

    def lab(self):
        p = self.p
        y = F_LAB
        # Cuve centrale : liquide vert dans une margelle de verre cerclée d'or.
        for x, z, d, a in ring(0, 9):
            if d < 7.5:
                p.set(x, y - 1, z, "Rock_Crystal_Green_Block")
                p.set(x, y - 2, z, self.wall())
            else:
                p.set(x, y, z, GOLD)
                p.set(x, y + 1, z, GLASS)
        for k in range(0, 360, 30):
            x, z = at(16, k + 15)
            self.place(x, y, z, "Alchemy_Cauldron", 0)
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 255, 285) or (x > 0 and -22 <= z <= -10):
                continue
            if int(a) % 20 < 10:
                for k in range(0, 6):
                    self.place(x, y + k, z, SHELF, facing_center(x, z))
        for k in (100, 130, 200, 230):
            x, z = at(24, k)
            self.place(x, y, z, "Bench_Alchemy", facing_center(x, z))
        self.light_ring(22, y, 30, skip=((255, 285), (320, 355)))
        for x, z in ((0, 12), (0, -12), (12, 0), (-12, 0)):
            self.place(x, F_LAB + 20, z, CHANDELIER)
        # Porte nord vers l'Escalier des vents.
        door = [(x, z) for x in range(-2, 3) for z in range(-35, -27)]
        self.door(door, y, 5)

    def wind_stair(self):
        ramp = self.helix(262, 602, R_OUT, 41, F_LAB, F_DECK, flat=8)
        self.wind_ramp = ramp
        p = self.p
        # Corbeaux sous la rampe.
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d >= 39.5 and int(a) % 6 < 1:
                for k in range(2, 9):
                    if p.free(x, s // 2 - 1 - k, z):
                        p.set(x, s // 2 - 1 - k, z, self.wall())
        return ramp

    def observatory(self):
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(0, DECK_R + 1):
            if d < DECK_R:
                p.set(x, y - 1, z, TRIM if 21.5 <= d < 22.5 or 41.5 <= d < 42.5 else self.floor())
                if d >= R_OUT:
                    p.set(x, y - 2, z, self.wall())  # dessous de l'encorbellement
            else:
                self.parapet(x, y, z, 2)
                if int(a) % 15 == 0:
                    p.set(x, y + 2, z, "Deco_Lantern")
        # Trémie : la fin de l'Escalier des vents traverse la terrasse.
        for (x, z), s in self.wind_ramp.items():
            self.carve(x, z, s)
        deck = {}
        for x, z, d, a in ring(0, DECK_R):
            if p.get(x, y - 1, z) not in (None, AIR):
                deck[(x, z)] = 2 * y
                self.register(x, z, 2 * y)
        self.deck = deck
        self.guard(deck)
        self.antechamber()
        self.study()
        self.arches()
        self.chimneys()
        self.crystals()
        self.telescope(340, 34)

    def antechamber(self):
        """Antichambre sur l'arrivée de l'escalier : secteur de 200 à 275°, porte vers la terrasse à 245°."""
        p = self.p
        y = F_DECK
        for x, z, d, a in ring(22, DECK_R):
            if not in_arc(a, 200, 275):
                continue
            edge = d < 24 or not in_arc(a, 201.5, 273.5)
            for k in range(0, 10):
                if edge:
                    p.set(x, y + k, z, self.wall())
            p.set(x, y + 10, z, self.wall())
        for x, z, d, a in ring(22, DECK_R):
            if in_arc(a, 200, 275) and d >= 43.5:
                for k in range(3, 10):
                    p.set(x, y + k, z, self.wall())
        door = [(x, z) for x, z, d, a in ring(21.5, 24.6) if abs(a - 245) < 5]
        self.door(door, y, 5)
        for x, z in door:
            p.set(x, y + 5, z, "Rock_Gold_Brick_Ornate")

    def study(self):
        """Bureau de l'Alchimiste, au sud de la terrasse (ouvert à la mort du boss, plus tard)."""
        p = self.p
        y = F_DECK
        x0, x1, z0, z1 = -10, 10, 26, 42
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                p.set(x, y - 1, z, "Wood_Darkwood_Planks" if not edge else self.wall())
                for k in range(0, 10):
                    p.set(x, y + k, z, self.wall() if edge else AIR)
                p.set(x, y + 10, z, TRIM if edge else self.wall())
                if not edge:
                    self.walk.get((x, z), set()).discard(2 * y)
        for x in (x0 + 1, x1 - 1):
            for z in range(z0 + 1, z1):
                for k in range(0, 6):
                    self.place(x, y + k, z, SHELF, pf.EAST if x < 0 else pf.WEST)
        door = [(x, z0) for x in range(-2, 3)]
        self.door(door, y, 5)
        for x in range(-2, 3):
            self.register(x, z0, 2 * y)
        # Piédestal de la pierre philosophale (la pierre viendra avec le butin), bureau, portail de fin.
        p.set(0, y, 32, "Rock_Gold_Brick_Pillar_Base")
        p.set(0, y + 1, 32, "Rock_Gold_Brick_Ornate")
        self.place(6, y, 30, "Furniture_Human_Ruins_Desk", pf.NORTH)
        self.place(-6, y, 30, GLOW)
        for x in (-5, 5):
            for z in (31, 37):
                self.place(x, y + 9, z, "Deco_Lantern_Ceiling")
        for x in range(-1, 2):
            for z in range(37, 41):
                self.keep_clear.update((x, y + k, z) for k in range(4))
        p.set(0, y, 38, "Nakasar_Tower_Exit", pf.NORTH)

    def arches(self):
        """Deux arcs dorés en croix au-dessus de la terrasse, pieds hors de l'antichambre et du bureau."""
        p = self.p
        for k in (10, 155):
            for i in range(-420, 421):
                r = i / 10
                h = math.sqrt(max(0.0, 42.0 ** 2 - r ** 2))
                x, z = round(r * math.cos(math.radians(k))), round(r * math.sin(math.radians(k)))
                y = F_DECK + round(h * 0.9)
                for dy in (0, 1):
                    if (x, y + dy, z) not in self.keep_clear and p.get(x, y + dy, z) in (None, AIR):
                        p.set(x, y + dy, z, GOLD)

    def chimneys(self):
        p = self.p
        for k in (35, 125, 300):
            cx, cz = at(50, k)
            for y in range(F_DECK - 28, F_DECK + 32):
                for x in range(cx - 2, cx + 3):
                    for z in range(cz - 2, cz + 3):
                        inner = abs(x - cx) <= 1 and abs(z - cz) <= 1
                        if y < F_DECK - 20 and not inner:
                            continue  # pied en encorbellement
                        if not inner or y < F_DECK + 26:
                            p.set(x, y, z, TRIM if y % 8 == 0 else self.wall())
            # bras qui relie la cheminée au bord de la terrasse
            for r in range(46, 49):
                for w in (-1, 0, 1):
                    x, z = at(r, k + w * 1.2)
                    p.set(x, F_DECK - 2, z, self.wall())
                    p.set(x, F_DECK - 1, z, self.wall())
            p.set(cx, F_DECK + 32, cz, "Nakasar_Tower_Emanation_Smoke")

    def crystals(self):
        """Éclats de cristal en lévitation autour du sommet, et quelques émanations."""
        p = self.p
        for i, k in enumerate(range(15, 360, 60)):
            cx, cz = at(58 + 6 * (i % 2), k)
            cy = F_DECK + 24 + 8 * (i % 3)
            for dy in range(-5, 6):
                w = 2 if abs(dy) < 3 else (1 if abs(dy) < 5 else 0)
                for x in range(cx - w, cx + w + 1):
                    for z in range(cz - w, cz + w + 1):
                        p.set(x, cy + dy, z, "Rock_Crystal_Purple_Block" if i % 2 else "Rock_Crystal_Green_Block")
            p.set(cx, cy + 6, cz, "Nakasar_Tower_Emanation_Spiral" if i % 2 else "Nakasar_Tower_Emanation_Motes")
        p.set(0, F_DECK + 44, 0, "Nakasar_Tower_Emanation_Arc")

    def telescope(self, k, r):
        p = self.p
        x0, z0 = at(r, k)
        if (x0, F_DECK, z0) in self.keep_clear:
            return
        p.set(x0, F_DECK, z0, "Rock_Gold_Brick_Pillar_Base")
        p.set(x0, F_DECK + 1, z0, "Rock_Gold_Brick_Pillar_Middle")
        for i in range(0, 5):
            p.set(x0 + (i + 1) // 2, F_DECK + 2 + i // 2, z0 - i // 2, GOLD if i % 2 else "Rock_Gold_Brick_Ornate")

    def checkpoint(self, x, y, z, statue_at):
        """Point de contrôle : statue de lumière entre deux braseros ; le joueur s'arrête en (x, y, z)."""
        sx, sz = statue_at
        for k in range(3):  # la statue peut prendre la place d'un bout de parapet
            if (sx, y + k, sz) in self.parapets:
                self.p.set(sx, y + k, sz, AIR)
        rot = facing_center(sx, sz) if (sx, sz) != (0, 0) else 0
        self.p.set(sx, y - 1, sz, "Rock_Gold_Brick_Ornate")
        if not self.p.fits(sx, y, sz, STATUE, rot):
            raise RuntimeError(f"tour : pas de place pour la statue du point de contrôle {(sx, y, sz)}")
        self.p.set(sx, y, sz, STATUE, rot)
        self.checkpoints.append((x, y, z))

    def build(self):
        self.shell()
        self.court()
        self.hall()
        self.leaks()
        self.greenhouse()
        self.library()
        self.transmutation()
        self.lab()
        self.wind_stair()
        self.observatory()
        self.guard(self.wind_ramp)
        # Points de contrôle : bibliothèque, laboratoire, Escalier des vents, antichambre.
        self.checkpoint(*at3(22, F_LIBRARY, 45), statue_at=at(27, 36))
        self.checkpoint(22, F_LAB, -16, statue_at=(18, -20))
        self.checkpoint(*at3(37, F_LAB, 272), statue_at=at(39, 262))
        self.checkpoint(*at3(33, F_DECK, 255), statue_at=at(37, 265))
        self.secure()
        return self.p

    def secure(self, rounds=12):
        """Ferme les fuites que le parcours trouve encore : un parapet sur lequel on peut monter (depuis une marche plus
        haute de l'hélice, une jardinière, une lanterne) est rehaussé, et tout bord praticable au-dessus d'une chute de
        plus de 6 blocs reçoit un parapet. Recommence jusqu'à ce que le parcours ne trouve plus rien."""
        p = self.p

        def on_parapet(x, y, z):
            return (x, y, z) in self.parapets or (p.get(x, y, z) == "Deco_Lantern" and (x, y - 1, z) in self.parapets)
        def stack(x, y, z):
            """(bas, haut) de la pile de parapet de la colonne (x, z) qui touche la hauteur y, ou None."""
            for yy in range(y - 2, y + 3):
                if on_parapet(x, yy, z):
                    lo = hi = yy
                    while on_parapet(x, lo - 1, z):
                        lo -= 1
                    while self.solid(x, hi + 1, z) or (x, hi + 1, z) in p.claims:
                        hi += 1  # le parapet peut porter une verrière, un plancher...
                    return lo, hi
            return None

        for _ in range(rounds):
            _, seen = walkable_path(p, START, {})
            raise_to, walls, perched = {}, set(), set()
            for x, s, z in seen:
                foot = s // 2  # bloc des pieds (sur un demi-bloc : le bloc du demi-bloc)
                if on_parapet(x, (s - 1) // 2, z):
                    perched.add((x, s, z))
                    continue
                for dx, dz in DIRS8:
                    nx, nz = x + dx, z + dz
                    st = stack(nx, foot, nz)
                    if st and on_parapet(nx, st[1], nz) and 2 * (st[1] + 1) < s + 4 and p.free(nx, st[1] + 1, nz) and p.free(nx, st[1] + 2, nz):
                        key = (nx, st[0], nz)
                        raise_to[key] = max(raise_to.get(key, st[1]), (s + 5) // 2 - 1)
                        continue
                    if any((nx, foot + k, nz) in self.keep_clear for k in range(2)):
                        continue
                    if foot >= 6 and all(not self.solid(nx, yy, nz) or on_parapet(nx, yy, nz)
                                         for yy in range(foot - 6, foot + 2)):  # vide, ou un parapet où l'on tomberait
                        if p.free(nx, foot + (s % 2), nz):
                            walls.add((nx, foot + (s % 2), nz))
            if not raise_to and not walls:
                if perched:
                    raise RuntimeError(f"tour : on peut marcher sur des parapets {sorted(perched)[:8]}")
                return
            self.secure_log = (sorted(raise_to.items())[:8], sorted(walls)[:8], len(raise_to), len(walls))
            for (x, lo, z), top in raise_to.items():
                hi = lo
                while on_parapet(x, hi + 1, z):
                    hi += 1
                crown = p.get(x, hi, z)
                for y in range(hi, top + 1):
                    if not p.free(x, y + 1, z):
                        break
                    p.set(x, y, z, PARAPET)
                    p.set(x, y + 1, z, crown)
                    self.parapets |= {(x, y, z), (x, y + 1, z)}
            for x, y, z in walls:
                self.parapet(x, y, z, 2)
        raise RuntimeError(f"tour : fuites non refermées {self.secure_log}")


# Salles à atteindre depuis le parvis (x, niveau, z), en plus des points de contrôle.
GOALS = {"hall": (0, F_HALL, 16), "leaks_exit": (-31, F_LEAKS, 0), "balcony_north": (0, F_LEAKS, -40),
         "library": (0, F_LIBRARY, 12), "transmutation": (0, F_TRANS, 0), "lab": (10, F_LAB, 10),
         "deck": (0, F_DECK, 0), "study": (0, F_DECK, 34)}


def build_checked(seed):
    """Construit la tour et vérifie le parcours : chaque salle et chaque point de contrôle est atteignable à pied."""
    tower = Tower(seed)
    prefab = tower.build()
    goals = dict(GOALS)
    for i, c in enumerate(tower.checkpoints):
        goals[f"checkpoint_{i + 1}"] = c
    missing, _ = walkable_path(prefab, START, goals)
    if missing:
        raise RuntimeError(f"tour : inaccessible depuis le parvis : {missing}")
    return tower


def at3(r, y, a):
    x, z = at(r, a)
    return x, y, z


# --- vérification du parcours --------------------------------------------------------------------

PASSABLE_PREFIXES = ("Plant_Grass", "Plant_Flower", "Plant_Crop_Mushroom", "Nakasar_Tower_Emanation", "Deco_Potion")


def passable(name):
    return name in (None, AIR) or name.startswith(PASSABLE_PREFIXES)


def walkable_path(prefab, start, goals, ground_y=0, bounds=(-70, 70, -70, 82)):
    """Parcours en largeur sur les surfaces du prefab (demi-blocs) : un joueur de 2 blocs de haut monte d'un demi-bloc
    en marchant, d'un bloc en sautant, et peut descendre de 4 blocs. Hors du prefab, sous ground_y c'est l'île (plein),
    au-dessus de l'air. Renvoie les buts non atteints."""
    blocks = prefab.blocks
    claims = prefab.claims

    def cell(x, y, z):
        if (x, y, z) in claims:
            return "solid"
        b = blocks.get((x, y, z))
        if b is None:
            return "solid" if y < ground_y else "air"
        name = b[0]
        if passable(name):
            return "air"
        if name.endswith("_Half"):
            return "half"
        return "solid"

    def surfaces(x, z, near):
        """Surfaces praticables (demi-blocs) de la colonne autour de la surface `near`."""
        out = []
        for y in range(near // 2 - 6, near // 2 + 3):
            c = cell(x, y, z)
            if c == "solid" and cell(x, y + 1, z) != "solid":
                s = 2 * (y + 1)
                if cell(x, y + 1, z) == "half":
                    s += 1
                    if cell(x, y + 2, z) == "air" and cell(x, y + 3, z) == "air" and cell(x, y + 4, z) == "air":
                        out.append(s)
                    continue
                if cell(x, y + 1, z) == "air" and cell(x, y + 2, z) == "air":
                    out.append(s)
        return out

    seen = {start}
    queue = deque([start])
    while queue:
        x, s, z = queue.popleft()
        for dx, dz in DIRS4:
            if not (bounds[0] <= x + dx <= bounds[1] and bounds[2] <= z + dz <= bounds[3]):
                continue
            for s2 in surfaces(x + dx, z + dz, s):
                if s2 - s > 2 or s - s2 > 8:
                    continue
                if s2 - s == 2 and cell(x, (s + 1) // 2 + 2, z) == "solid":
                    continue  # pas la place de sauter
                if s2 < s and any(cell(x + dx, y, z + dz) != "air" for y in range((s2 + 1) // 2, s // 2 + 2)):
                    continue  # on ne tombe pas à travers un plancher
                n = (x + dx, s2, z + dz)
                if n not in seen:
                    seen.add(n)
                    queue.append(n)
    reached = {}
    for x, s, z in seen:
        reached.setdefault((x, z), set()).add(s)
    missing = []
    for name, (gx, gy, gz) in goals.items():
        if not any(abs(o - 2 * gy) <= 2 for dx in range(-1, 2) for dz in range(-1, 2)
                   for o in reached.get((gx + dx, gz + dz), ())):
            missing.append(name)
    return missing, seen
