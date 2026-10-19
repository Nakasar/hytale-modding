"""La Tour de l'Alchimiste elle-même (étape 2 du donjon) : prefab de la tour, utilisé par generate_alchemist_tower.py.

Échelle Deepworks (Kevin, 19 octobre 2026) : environ 67 blocs de diamètre (balcons 95) et 220 de haut ;
generate_alchemist_tower.py coupe le prefab en tranches empilées.

Repère du prefab : centré sur l'axe de la tour, y = 0 = première couche d'air au-dessus du sol de l'île (y = -1 : sol).
Les angles sont en degrés : x = r cos(a), z = r sin(a), donc 0 = est, 90 = sud, 180 = ouest, 270 = nord.

Parcours, de bas en haut (niveaux = première couche d'air du sol de chaque salle) :

- parvis au sud, porte du Hall des Alambics (niveau 0) ; rampe le long du mur de 200 à 300° ;
- Couloir des fuites (22) : anneau autour d'un cœur plein, barré à 240°, on en fait les trois quarts jusqu'à la porte
  ouest ; buses de gaz sur les deux murs, alimentées par des tuyaux luisants (`gas_nozzles`, jets en cône : `traps`) ;
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
contrôle. Au bord du vide extérieur, des blocs Barrier marquent au-dessus des parapets, jusqu'à 4 blocs au-dessus de
la plus haute surface voisine, la barrière nécessaire (Kevin, 19 octobre 2026 : on ne saute pas des coursives) ;
generate_alchemist_tower.py les remplace par des volumes de repoussée comme dans Deepworks ; chaque
salle est meublée selon son thème (`decorate`), sans gêner le parcours.
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
# Salle des Transmutations, ronde : escalier en hélice le long du mur nord, de l'arrivée de la rampe de la bibliothèque
# (205°) au laboratoire (340°), entre TRANS_STAIR_R et le mur.
TRANS_STAIR_ARC = (212, 340)
TRANS_STAIR_R = 24.5
COURT_HALF = 16    # parvis : x de -16 à 16
COURT_END = 79     # le parvis va jusqu'à z = 79 ; le pont arrive en z = 80
BRIDGE_HALF = 3    # demi-largeur du pont (generate_alchemist_tower.BRIDGE_HALF)

WALL = [("Rock_Marble_Brick", 7), ("Rock_Marble_Brick_Smooth", 2), ("Rock_Marble_Cobble", 1)]
FLOOR = [("Rock_Marble_Brick_Smooth", 4), ("Rock_Marble_Brick", 3)]
HALF = "Rock_Marble_Brick_Half"
CRACKED = "Rock_Marble_Cobble"   # dallage des pans du rebord qui s'effondrent au Grand Œuvre (alchemist_traps les repose)
TRIM = "Rock_Gold_Brick_Decorative"
GOLD = "Rock_Gold_Brick"
PARAPET, PARAPET_TOP = "Rock_Marble_Brick", "Rock_Marble_Brick_Wall"
GLASS = "Nakasar_Stained_Glass_Violet"
# Statue des points de contrôle de Deepworks, éteinte ; le volume du point de contrôle la fait changer d'état.
STATUE = "*Dungeon_Checkpoint_Statue_State_Definitions_Inactive"
SHELF = "Furniture_Bookshelf_Single"
LANTERN = "Furniture_Temple_Light_Lantern"
GLOW = "Furniture_Royal_Magic_Potion_Glow"
BRAZIER = "Furniture_Temple_Dark_Brazier"
CHANDELIER = "Furniture_Feran_Chandelier"
BARRIER = "Barrier"  # bloc vanilla plein et invisible (Server/Item/Items/Hypixel/Barrier.json)
# Pièges et énigmes (étape 4, tools/alchemist_traps.py écrit leurs volumes) : sceau alchimique et haie de ronces ferment
# un passage jusqu'à ce que l'énigme soit résolue ; on allume un brasero éteint (athanor, foyer) ou on tire le levier.
SEAL = "Nakasar_Alchemical_Seal"
HEDGE = "Nakasar_Thorn_Hedge"
LEVER = "Nakasar_Valve_Lever"
VALVE = "Nakasar_Tower_Valve"   # vanne de la conduite de gaz du Couloir des fuites (deux blocs de haut)
FOYER = "*Furniture_Temple_Dark_Brazier_State_Definitions_Off"
DOOR = "Nakasar_Tower_Door"   # portes de la tour : elles tombent quand les gardiens d'airain de la cour sont abattus
GATE_BLOCKS = (SEAL, HEDGE, DOOR)
# Barrière des arènes (comme les portes de Deepworks) : posée en jeu par les volumes (tools/alchemist_traps.py,
# Traps.arena_gate) quelques secondes après l'entrée du groupe, retirée quand il a péri ou que le boss est vaincu.
ARENA_BARRIER = "Nakasar_Arena_Barrier"
SPORE_SHROOM = "Nakasar_Spore_Shroom"   # champignon animé de la serre : il enfle puis lâche son nuage de spores
# Hall des Alambics : trois athanors autour du grand alambic. Chacun a sa couleur (gemmes sur son estrade) ; allumé, il
# fait courir sa couleur dans un tuyau de verre suspendu jusqu'à l'alambic, remplit son tube, allume sa gemme sur la
# colonne relais et sur le sceau du Couloir des fuites. Les trois ensemble allument le tuyau maître et la colonne, qui
# traverse le plafond sous le sceau (dalle de verre), puis le sceau se dissout. (Kevin : « pas assez clair que les
# athanors alimentent le mur de sceau ».)
HALL_ATHANOR_ANGLES = (30, 150, 270)
HALL_ATHANOR_R = 13            # brasero de l'athanor
HALL_FURNACE_R = 17    # four de l'athanor, derrière le brasero
ALEMBIC_R = 5             # grand alambic : verre pour 2,5 <= d < ALEMBIC_R
ALEMBIC_TOP = 13
CONDUIT_LIT = "Rock_Crystal_Purple_Block"   # tuyau maître et colonne relais allumés (les trois couleurs mêlées)
HALL_COLOURS = ("Red", "Blue", "Green")     # couleur de chaque athanor (HALL_ATHANOR_ANGLES)
SOCKET = "Rock_Gold_Brick_Ornate"           # gemme éteinte (colonne relais et sceau)
PIPE_Y = 11      # tuyaux suspendus des athanors à l'alambic
MAIN_Y = 14      # tuyau maître du chapiteau de l'alambic à la colonne relais
EMANATION_LIT = "Nakasar_Tower_Emanation_Spiral"   # posée au-dessus d'un athanor allumé
EMANATION_FED = "Nakasar_Tower_Emanation_Arc"      # au sommet de l'alambic quand les trois athanors brûlent
RELAY = (306, 20.5)       # colonne relais (angle, rayon), sous le sceau du Couloir des fuites (HALL_SEAL_ARC)
PIPE = "Metal_Goblin_Iron_Pipe_Large"
PIPE_GLOW = "Metal_Goblin_Iron_Pipe_Large_Glowy"   # luit tant que la vanne est ouverte (état Off une fois coupée)
PIPE_THIN = "Metal_Goblin_Iron_Pipe_Long"
LEAK = "Nakasar_Tower_Emanation_Leak"   # fuite de gaz (pas le bloc vanilla : il se ramasse)
# Cour : gardiens d'airain sur leurs socles (x, z).
GUARDIANS = ((-8, 44), (8, 44), (-8, 60), (8, 60))
RUBBLE = "Nakasar_Codex_Rubble"  # éboulis de livres et d'étagères, posé en jeu par les volumes du combat du Codex
HALL_SEAL_ARC = (304, 308)    # sceau du couloir des fuites, juste après l'arrivée de la rampe du hall (300°)
JET_ARC = (310, 530)          # zone des jets de gaz : de l'arrivée à la porte ouest (180°)
# Buses de gaz du Couloir des fuites (Kevin : « rajoute des tuyaux visibles et des embouts desquels le gaz sort, avec des
# zones rouges qui préviennent de la sortie du gaz en cône »). Une buse tous les 15°, tour à tour sur le mur intérieur
# (groupe A, elle souffle vers l'extérieur) et sur le mur extérieur (groupe B, vers l'intérieur) ; chaque buse vise l'une
# des huit directions (modèle droit ou diagonal) et son cône est fait de trois cercles (distance à la buse, rayon).
NOZZLE = "Nakasar_Tower_Gas_Nozzle"
NOZZLE_DIAG = "Nakasar_Tower_Gas_Nozzle_Diagonal"
NOZZLE_ANGLES = tuple(range(315, 526, 15))
GAS_CONE = ((1.3, 1.0), (3.3, 1.5), (5.7, 2.1))
SHORTCUT_ARC = (236.5, 243.5)  # barrage du couloir : le levier y ouvre un raccourci
HEDGE_ARC = (72, 84)          # haie de ronces au pied de la rampe de la bibliothèque (elle part de 70°)
# Quadrants élémentaires de l'arène du golem de cristal (signes de x et z), séparés par la croix d'or du sol, dans
# l'ordre du tour (TransmutationSystem passe le répit d'un quadrant à un voisin).
TRANS_QUADRANTS = {"Earth": (1, 1), "Air": (-1, 1), "Ice": (-1, -1), "Fire": (1, -1)}
TRANS_COLOURS = {"Fire": "Red", "Earth": "Green", "Air": "Yellow", "Ice": "Cyan"}
TRANS_ZONE_HEIGHT = 6    # hauteur des volumes des quadrants : le haut de l'hélice reste hors de leurs effets
FLAME_ANGLES = (295, 340, 385, 430, 475, 520, 565)  # angles de l'Escalier des vents (262 à 602°)
GUST_SECTORS = (318, 408, 498, 585)
STRIKE_ANGLES = tuple(range(282, 595, 22))
# Codex vivant (étape 5) : trois pupitres autour de la rotonde, sceau en haut de la rampe de la bibliothèque, pans
# d'étagères qui s'effondrent sous 50 % de vie (hors rampe, portes, point de contrôle et passage secret).
LECTERN = "Rock_Gold_Brick_Ornate"
LECTERN_R = 9.5
LECTERN_ANGLES = (30, 150, 270)
CODEX_SEAL_ARC = (190, 199)
COLLAPSE_ARCS = ((220, 248), (252, 282), (286, 312), (328, 358), (2, 24))
COLLAPSE_R = (21.5, 28.4)
# Chimère du laboratoire (étape 6) : étagères de réactifs (PNJ posés par tower.ChimeraSystem, les homoncules y prennent
# de quoi la régénérer), cases où elle ressort de la cuve, sceau de la porte nord jusqu'à sa mort.
# Butin et lore (étapes 8 et 9 du donjon, tools/generate_alchemist_loot.py et generate_lore.py).
PEDESTAL_STONE = "Nakasar_Philosopher_Pedestal_Stone"   # pierre philosophale posée sur le piédestal du Bureau
SECRET_CHEST = "Furniture_Royal_Magic_Chest_Small"
SECRET_LOOT = "Nakasar_Loot_Tower_Secret"
# Coffres secrets, au fond d'une niche creusée dans le mur extérieur, sous des lianes : (angle, étage) d'un point de
# vue du balcon de la serre et d'un palier de l'Escalier des vents.
SECRETS = ((352, F_LEAKS), (548, None))
# Notes de lore (generate_lore.LORE, sans le préfixe Nakasar_Lore_) : (nom, (rayon, étage, angle) ou (x, étage, z)
# pour le Bureau). Chaque note va sur la case libre au sol la plus proche, hors des cases réservées.
TOWER_NOTES = (
    ("Tower_Hunter_Orders", ("xz", 5, F_HALL, 70)),
    ("Alchemist_Journal_1", ("polar", 22, F_HALL, 210)),
    ("Tower_Apprentice", ("polar", 27, F_LEAKS, 200)),
    ("Alchemist_Journal_2", ("polar", 41, F_LEAKS, 240)),
    ("Alchemist_Journal_3", ("polar", 22, F_LIBRARY, 100)),
    ("Alchemist_Journal_4", ("polar", 26, F_TRANS, 120)),
    ("Alchemist_Journal_5", ("polar", 26, F_LAB, 110)),
    ("Alchemist_Journal_6", ("polar", 34, F_DECK, 238)),
    ("Alchemist_Journal_7", ("xz", 2, F_DECK, 30)),
    ("Tower_Count_Letter", ("xz", 4, F_DECK, 31)),
    ("Tower_Hunter_Plea", ("xz", -3, F_DECK, 30)),
)
CHIMERA_BASIN_R = 21      # bassins d'acide secondaires : les zombies y remplissent leurs seaux
CHIMERA_BASIN_ANGLES = (0, 45, 135, 225)   # entre les alcôves (LAB_ALCOVES), loin de l'hélice et de la porte nord
CHIMERA_BASIN_SIZE = 1.6  # rayon du bassin (acide pour d < CHIMERA_BASIN_SIZE), margelle d'or d'un bloc autour
ACID = "Poison_Source"    # eau acide verte de Deepworks
CHIMERA_DOOR_Z = -30
# Alcôves du laboratoire (angle, genre), le long du mur, symétriques autour de la cuve ; ni devant la porte nord (270°)
# ni sur l'arrivée de l'escalier des transmutations (environ 320 à 345°).
LAB_ALCOVES = {22.5: "alembic", 67.5: "bench", 112.5: "alembic", 157.5: "bench", 202.5: "alembic", 247.5: "bench",
               297.5: "alembic"}
# Combat de l'Alchimiste (étape 7), sur la terrasse de l'Observatoire.
ATHANOR_R = 3.6          # athanor central : murs pour d < ATHANOR_R, chambre (où il s'enferme) pour d < ATHANOR_ROOM
ATHANOR_ROOM = 1.6
ALCHEMIST_EXIT_R = 6
PILLAR_R = 17
PILLAR_ANGLES = (20, 150, 295, 340)   # piliers de la Convergence : feu, glace, foudre, racine
HEAL_R = 26
HEAL_ANGLES = (0, 45, 130, 165, 300, 325)
SAFE_R = 28              # points de retour sur la terrasse pour qui tombe dans un trou
DECK_COLLAPSE_ARCS = ((282, 322), (346, 362), (18, 52))  # loin de l'antichambre, du bureau, des pieds des arcs
DECK_COLLAPSE_R = (34.5, 41.4)
STUDY_DOOR_Z = 26
ANTECHAMBER_ARC = (200, 275)

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


DIRS_ROT = {pf.SOUTH: (0, 1), pf.EAST: (1, 0), pf.NORTH: (0, -1), pf.WEST: (-1, 0)}  # devant d'un meuble selon son lacet


def facing_to(x, z, tx, tz):
    """Lacet d'un meuble posé en (x, z) pour qu'il regarde la case (tx, tz)."""
    dx, dz = tx - x, tz - z
    if abs(dx) > abs(dz):
        return pf.EAST if dx > 0 else pf.WEST
    return pf.SOUTH if dz > 0 else pf.NORTH


def wall_facing(x, z, inner=28.4):
    """Lacet d'un meuble adossé au mur rond (rayon >= inner) : vers le centre, mais toujours vers une case dégagée.
    Sur les tronçons en diagonale, regarder droit vers le centre mettait le devant contre le meuble voisin."""
    order = sorted(DIRS_ROT.items(), key=lambda kv: -(kv[1][0] * -x + kv[1][1] * -z))
    for rot, (dx, dz) in order:
        if math.hypot(x + dx, z + dz) < inner:
            return rot
    return order[0][0]


def at(r, a):
    return round(r * math.cos(math.radians(a))), round(r * math.sin(math.radians(a)))


def quadrant(x, z):
    """Quadrant élémentaire de la Salle des Transmutations sous la case (x, z), None sur la croix d'or."""
    if x == 0 or z == 0:
        return None
    sign = (1 if x > 0 else -1, 1 if z > 0 else -1)
    return next(el for el, q in TRANS_QUADRANTS.items() if q == sign)


def lit_block(colour):
    """Cristal allumé d'une couleur d'athanor (HALL_COLOURS)."""
    return f"Rock_Crystal_{colour}_Block"


def radial(a, r0, r1):
    """Colonnes (x, z) d'un trait droit à l'angle `a`, du rayon r0 au rayon r1, dans l'ordre, sans doublon."""
    out = []
    n = int(abs(r1 - r0) * 2) + 1
    for i in range(n):
        c = at(r0 + (r1 - r0) * i / (n - 1), a)
        if c not in out:
            out.append(c)
    return out


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
        self.statues = []        # ((x, y, z), lacet) des statues, dans le même ordre

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
        # Cœur plein du couloir des fuites, barrage à 240°.
        for x, z, d, a in ring(0, R_IN):
            for y in range(F_LEAKS, F_LIBRARY - 1):
                if d < 18 or (d < R_IN and in_arc(a, 237, 243)):
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
        # Porte du hall : arche dorée, fermée par les portes de la tour (5 × 8) au nu extérieur du mur.
        door = [(x, z) for x in range(-2, 3) for z in range(27, 35)]
        self.door(door, 0, 8)
        for x in (-3, 3):
            for z in (32, 33, 34):
                for y in range(0, 9):
                    p.set(x, y, z, GOLD)
        for x in range(-3, 4):
            for z in (32, 33, 34):
                p.set(x, 8, z, "Rock_Gold_Brick_Ornate")
        self.court_door = [(x, y, 33) for x in range(-2, 3) for y in range(0, 8)]
        for x, y, z in self.court_door:
            p.set(x, y, z, DOOR)
        # Socles des gardiens d'airain : dalle d'or ouvragée, lanternes de part et d'autre.
        for gx, gz in GUARDIANS:
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    p.set(gx + dx, -1, gz + dz, "Rock_Gold_Brick_Ornate" if (dx, dz) == (0, 0) else TRIM)

    def hall(self):
        """Hall des Alambics : le grand alambic au centre, trois athanors autour, reliés à lui par des tuyaux de verre
        suspendus, et la colonne relais sous le sceau du Couloir des fuites, reliée à l'alambic par le tuyau maître. Le
        sol est dégagé autour des athanors pour qu'on les voie en entrant."""
        cells = self.helix(200, 300, 23, R_IN, F_HALL, F_LEAKS)
        self.hall_ramp = cells
        p = self.p
        h = self.hall_parts = {"tubes": [], "conduits": [], "athanors": []}
        # Mosaïque du sol : deux cercles d'or autour de l'alambic et au pied des athanors.
        for x, z, d, a in ring(0, 22):
            if 7 <= d < 7.8 or 17.6 <= d < 18.4:
                p.set(x, -1, z, TRIM)
        # Grand alambic : socle, panse de verre, trois tubes vides (un par athanor) autour d'une âme d'or, col et chapiteau.
        for x, z, d, a in ring(0, ALEMBIC_R + 1.5):
            p.set(x, 0, z, "Rock_Gold_Brick_Ornate" if d < ALEMBIC_R else HALF)
        tubes = [at(1.6, k) for k in HALL_ATHANOR_ANGLES]
        for y in range(1, ALEMBIC_TOP):
            for x, z, d, a in ring(0, ALEMBIC_R):
                if (x, z) in tubes:
                    p.set(x, y, z, AIR)
                elif d < 1:
                    p.set(x, y, z, "Rock_Gold_Brick_Pillar_Middle")
                else:
                    p.set(x, y, z, GLASS if (d >= 2.5 or y % 4) else GOLD)
        for x, z in tubes:
            h["tubes"].append([(x, y, z) for y in range(1, ALEMBIC_TOP)])
        for x, z, d, a in ring(0, ALEMBIC_R):
            p.set(x, ALEMBIC_TOP, z, GOLD)
        for x, z, d, a in ring(0, 3.5):
            p.set(x, ALEMBIC_TOP + 1, z, GOLD)
        for x, z, d, a in ring(0, 2):
            p.set(x, ALEMBIC_TOP + 2, z, GLASS)
        p.set(0, ALEMBIC_TOP + 3, 0, "Rock_Gold_Brick_Ornate")
        p.set(0, ALEMBIC_TOP + 4, 0, "Nakasar_Tower_Emanation_Spiral")
        # Athanors : four de marbre cerclé d'or derrière un brasero (l'énigme : `traps`), sur une estrade dorée semée de
        # gemmes de sa couleur ; une cheminée d'or monte au plafond, des émanations flottent autour.
        for k, colour in zip(HALL_ATHANOR_ANGLES, HALL_COLOURS):
            fx, fz = at(HALL_FURNACE_R, k)
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    for y in range(0, 5):
                        corner = abs(dx) == 1 and abs(dz) == 1
                        p.set(fx + dx, y, fz + dz, (GOLD if y in (0, 4) else "Rock_Marble_Brick") if corner or y in (0, 4)
                              else "Rock_Marble_Brick_Smooth")
            mx, mz = at(HALL_FURNACE_R - 1.5, k)
            p.set(mx, 1, mz, "Furniture_Royal_Magic_Potion_Glow")  # gueule du four
            for y in range(5, F_LEAKS - 1):
                p.set(fx, y, fz, "Metal_Gold_Pipe_Large")  # cheminée jusqu'au plafond
            bx, bz = at(HALL_ATHANOR_R, k)
            for x, z, d, a in ring(0, 3.6):
                p.set(bx + x, -1, bz + z, TRIM if d >= 2.6 else "Rock_Marble_Brick_Smooth")
            for off in (45, 135, 225, 315):
                gx, gz = at(2.9, off)
                p.set(bx + gx, 0, bz + gz, f"Rock_Crystal_{colour}_Medium")
            for j, off in enumerate((-40, 40)):
                ex, ez = at(HALL_ATHANOR_R + 1.5, k + off * 0.35)
                p.set(ex, 2 + j, ez, "Nakasar_Tower_Emanation_Motes")
            # Tuyau de verre suspendu, de la cheminée au tube de l'alambic, cerclé d'or tous les quatre blocs.
            pipe = []
            for i, (x, z) in enumerate(radial(k, HALL_FURNACE_R - 1, 2.2)):
                if (x, z) in tubes:
                    break
                if i % 4 == 3 and math.hypot(x, z) > ALEMBIC_R:
                    p.set(x, PIPE_Y, z, GOLD)
                else:
                    p.set(x, PIPE_Y, z, GLASS)
                    pipe.append((x, PIPE_Y, z))
            h["conduits"].append(pipe)
        # Colonne relais sous le sceau du Couloir des fuites : verre cerclé d'or, trois gemmes éteintes (une par athanor)
        # sur la face qui regarde l'alambic ; son âme traverse le plafond, dallé de verre sous le sceau.
        ra, rr = RELAY
        rx, rz = at(rr, ra)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                p.set(rx + dx, -1, rz + dz, "Rock_Gold_Brick_Ornate")
                for y in range(0, F_LEAKS - 1):
                    if (dx, dz) == (0, 0):
                        p.set(rx, y, rz, AIR if y >= MAIN_Y else "Rock_Gold_Brick_Ornate")
                    else:
                        p.set(rx + dx, y, rz + dz, GOLD if (abs(dx) + abs(dz) == 2 or y % 5 == 0) else GLASS)
        for x, z, d, a in ring(18, R_IN):
            if in_arc(a, *HALL_SEAL_ARC):
                p.set(x, F_LEAKS - 1, z, GLASS)
        p.set(rx, F_LEAKS - 1, rz, GLASS)
        h["relay"] = [(rx, y, rz) for y in range(MAIN_Y, F_LEAKS)]
        sx, sz = at(rr - 1, ra)
        h["relay_sockets"] = [(sx, y, sz) for y in (4, 7, 10)]
        for c in h["relay_sockets"]:
            p.set(*c, SOCKET)
        # Tuyau maître : du chapiteau de l'alambic à la colonne relais.
        h["main"] = []
        for i, (x, z) in enumerate(radial(ra, 3.6, rr - 1.6)):
            if i % 4 == 3:
                p.set(x, MAIN_Y, z, GOLD)
            else:
                p.set(x, MAIN_Y, z, GLASS)
                h["main"].append((x, MAIN_Y, z))
        self.light_ring(27.5, 0, 15, skip=((195, 305), (82, 98)))
        for x, z in ((12, 12), (-12, 12), (12, -12), (-12, -12), (0, 18), (0, -18), (18, 0), (-18, 0)):
            self.place(x, 18, z, CHANDELIER)

    def leaks(self):
        """Couloir des fuites : anneau de 18 à 29,5 autour d'un cœur plein. La conduite de gaz court au plafond le long
        des deux murs ; dans la zone des jets, des descentes de tuyaux luisants alimentent les buses (`gas_nozzles`)."""
        p = self.p
        y = F_LEAKS
        for x, z, d, a in ring(27.5, R_IN):
            for dy in (9, 10):
                p.set(x, y + dy, z, GOLD)  # conduite qui court au plafond le long du mur extérieur
        for x, z, d, a in ring(18, 19.6):
            if in_arc(a, JET_ARC[0] - 4, JET_ARC[1] + 4):
                for dy in (9, 10):
                    p.set(x, y + dy, z, GOLD)  # et le long du cœur, au-dessus des buses intérieures
        for k in range(0, 360, 10):
            if in_arc(k + 5, JET_ARC[0] - 6, JET_ARC[1] + 6):
                continue
            xo, zo = at(28, k + 5)
            for dy in range(0, 9):
                if self.p.free(xo, y + dy, zo):
                    p.set(xo, y + dy, zo, "Rock_Gold_Brick_Pillar_Middle")  # colonne montante
        self.gas_nozzles()
        # Porte ouest vers la serre.
        door = [(x, z) for x in range(-35, -27) for z in range(-2, 3)]
        self.door(door, F_LEAKS, 5)

    def gas_nozzles(self):
        """Buses de gaz : montées à hauteur de poitrine sur le mur, sous une descente de tuyau luisant qui remonte à la
        conduite du plafond. `self.nozzles` garde, pour chaque buse, sa case, sa direction et son groupe (A ou B)."""
        p = self.p
        y = F_LEAKS + 1
        self.nozzles = []
        for i, a in enumerate(NOZZLE_ANGLES):
            inner = i % 2 == 0
            q = (round(a / 45) * 45 + (0 if inner else 180)) % 360
            u = (math.cos(math.radians(q)), math.sin(math.radians(q)))
            step = (round(u[0]), round(u[1]))
            radii = [r / 4 for r in range(64, 88)] if inner else [r / 4 for r in range(124, 100, -1)]
            x, z = next(c for c in (at(r, a) for r in radii) if p.free(c[0], y, c[1]) and p.free(c[0], y - 1, c[1]))
            bx, bz = x - step[0], z - step[1]
            for dy in (-1, 0, 1):  # la buse s'appuie sur le mur (bossage d'or si le mur courbe s'écarte)
                if p.free(bx, y + dy, bz):
                    p.set(bx, y + dy, bz, GOLD)
            if q % 90 == 0:
                name, rot = NOZZLE, next(r for r, f in DIRS_ROT.items() if f == step)
            else:  # modèle diagonal : son avant (+X, +Z) tourne comme l'avant (+Z) d'un meuble
                name = NOZZLE_DIAG
                rot = next(r for r, (fx, fz) in DIRS_ROT.items() if (fz + fx, fz - fx) == step)
            p.set(x, y, z, name, rot)
            pipe = [(x, k, z) for k in range(y + 1, F_LEAKS + 9)]
            for c in pipe:
                p.set(*c, PIPE_GLOW)
            cone = set()
            for dist, rad in GAS_CONE:
                cx, cz = x + 0.5 + u[0] * dist, z + 0.5 + u[1] * dist
                cone.update((gx, gz) for gx in range(math.floor(cx - rad), math.ceil(cx + rad))
                            for gz in range(math.floor(cz - rad), math.ceil(cz + rad))
                            if math.hypot(gx + 0.5 - cx, gz + 0.5 - cz) < rad + 0.5)
            self.keep_clear.update((gx, k, gz) for gx, gz in cone for k in range(F_LEAKS, F_LEAKS + 3)
                                   if p.free(gx, k, gz))
            self.nozzles.append({"angle": a, "group": "A" if inner else "B", "cell": (x, y, z), "dir": u,
                                 "pipe": pipe})

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
        self.library_vault()
        # Garde-corps intérieur de la rampe (muret d'un bloc).
        for (x, z), s in ramp.items():
            d, a = polar(x, z)
            if d < 24.5 and s > 2 * F_LIBRARY + 8:
                y = (s + 1) // 2
                if p.free(x, y, z):
                    p.set(x, y, z, PARAPET_TOP)
        # Étagères sur huit rangs le long du mur, hors rampe, porte et passage secret.
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 60, 215) or in_arc(a, 38, 62) or in_arc(a, 315, 325) or in_arc(a, 25, 35):
                continue
            for y in range(F_LIBRARY, F_LIBRARY + 8):
                self.place(x, y, z, SHELF, wall_facing(x, z))
        # Deux rayonnages doubles dans l'axe (nord et est), dos à dos : chaque face regarde l'allée, jamais le bout
        # du rang. Ils prolongent les pupitres du Codex vers le mur.
        for r in range(15, 24):
            for y in range(F_LIBRARY, F_LIBRARY + 4):
                self.place(-1, y, -r, SHELF, pf.WEST)
                self.place(0, y, -r, SHELF, pf.EAST)
                self.place(r, y, -1, SHELF, pf.NORTH)
                self.place(r, y, 0, SHELF, pf.SOUTH)
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
                    self.place(x, y, z, SHELF, wall_facing(x, z))
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

    def library_vault(self):
        """Coupole à gradins sous le plancher de la Salle des Transmutations (Kevin, 19 octobre 2026 : on ne doit plus
        voir le dessous de la salle du dessus) : oculus d'or, trois gradins de caissons clairs semés d'étoiles de
        cristal, seize nervures d'or en saillie, anneaux dorés à chaque gradin. Hors de la coupole, un bandeau ferme le
        haut, sauf au-dessus de la rampe (sa trémie reste ouverte). `vault_low` donne le bloc le plus bas par colonne."""
        p = self.p
        rng = self.rng
        top = F_TRANS - 2
        tiers = ((7, top), (14, top - 1), (20, top - 2), (23, top - 3))
        stars = ["Rock_Crystal_Blue_Block", "Rock_Crystal_Purple_Block", "Rock_Crystal_White_Block"]
        self.vault_low = {}
        for x, z, d, a in ring(0, R_IN):
            if (x, z) in self.library_ramp:
                continue
            if d >= 23:
                if self.p.free(x, top, z) and (x, top, z) not in self.keep_clear:
                    p.set(x, top, z, self.wall())
                    self.vault_low[(x, z)] = top
                continue
            k = next(i for i, (r, _) in enumerate(tiers) if d < r)
            low = tiers[k][1]
            edge = k > 0 and d >= tiers[k - 1][0] and d < tiers[k - 1][0] + 1  # gradin : anneau doré
            rib = k > 0 and min(abs(((a - n) + 180) % 360 - 180) for n in range(0, 360, 360 // 16)) * d * math.pi / 180 < 0.6
            for y in range(low, top + 1):
                p.set(x, y, z, "Rock_Quartzite_Brick")
            if d < 2.5:
                p.set(x, top, z, "Rock_Gold_Brick_Ornate")
            elif d < 4:
                p.set(x, top, z, GOLD)
            elif rib or edge:
                p.set(x, low, z, TRIM if edge else GOLD)
                if k >= 2:
                    p.set(x, low - 1, z, GOLD if rib else TRIM)
                    low -= 1
            else:
                p.set(x, low, z, rng.choice(stars) if rng.random() < 0.05 else "Rock_Quartzite_Brick_Smooth")
            self.vault_low[(x, z)] = low

    def transmutation(self):
        """Salle des Transmutations, ronde (Kevin, 19 octobre 2026) : l'arène du golem de cristal. Quatre quadrants
        élémentaires séparés par la croix d'or du sol (TRANS_QUADRANTS), un escalier en hélice le long du mur nord
        vers le laboratoire, un plafond à caissons (`trans_ceiling`)."""
        p = self.p
        y = F_TRANS
        for x, z, d, a in ring(0, R_IN):
            if p.get(x, y - 1, z) in (None, AIR):
                continue  # trémie de la rampe de la bibliothèque (dégagée par son escalier)
            el = quadrant(x, z)
            if el is None:
                p.set(x, y - 1, z, TRIM)
            elif d > 6 and (x + z) % 4 == 0 and (x - z) % 4 == 0:
                p.set(x, y - 1, z, lit_block(TRANS_COLOURS[el]))
            else:
                p.set(x, y - 1, z, self.floor())
        # Arrivée de la rampe de la bibliothèque : rien au-dessus des marches encore sous ce niveau (on butait en haut de
        # l'escalier quand un plancher refermait la trémie, Kevin, 19 octobre 2026).
        for (x, z), s in self.library_ramp.items():
            if s < 2 * y:
                for k in range(5):
                    p.set(x, y + k, z, AIR)
                    self.keep_clear.add((x, y + k, z))
        # Escalier en hélice le long du mur, de la rampe de la bibliothèque au laboratoire. Plein jusqu'au sol tant qu'il
        # est bas (pas de recoin d'un bloc de haut dessous) ; plus haut, on passe dessous.
        a0, a1 = TRANS_STAIR_ARC
        stair = {}
        for x, z, d, a in ring(TRANS_STAIR_R, R_IN):
            rel = (a - a0) % 360
            if rel > a1 - a0:
                continue
            t = min(1.0, max(0.0, (rel - 5) / (a1 - a0 - 10)))
            stair[(x, z)] = round(2 * (y + (F_LAB - y) * t))
        for (x, z), s in stair.items():
            self.step(x, z, s)
            if s < 2 * y + 10:
                for k in range(y, s // 2 - 1):
                    p.set(x, k, z, self.wall())
        for (x, z), s in stair.items():
            self.carve(x, z, s)
        # Muret côté salle, juste après le sceau du pied (`traps`) : même monté sur un décor d'un bloc, on n'y saute pas.
        for (x, z), s in stair.items():
            if polar(x, z)[0] < TRANS_STAIR_R + 1 and 2 * y + 3 < s < 2 * F_LAB:
                k = (s + 1) // 2
                if p.free(x, k, z):
                    p.set(x, k, z, PARAPET_TOP)
                    self.parapets.add((x, k, z))
        self.trans_stair = stair
        self.trans_ceiling()
        for a in (10, 50, 90, 130, 170):
            self.place(*at3(27, y, a), BRAZIER)

    def trans_ceiling(self):
        """Plafond à caissons de la Salle des Transmutations, sous le plancher du laboratoire (Kevin, 19 octobre 2026 :
        une couche de décor entre les deux) : rayons et anneaux d'or en saillie, caissons de quartzite semés de cristaux
        de la couleur du quadrant ; le fond de la cuve du laboratoire fait la rosace du centre (`lab`). L'hélice garde
        sa trémie."""
        p = self.p
        rng = self.rng
        top = F_LAB - 2
        near = {(x + dx, z + dz) for (x, z) in self.trans_stair for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
        for x, z, d, a in ring(0, R_IN):
            if (x, z) in near:
                continue
            rib = d > 9 and min(abs(((a - n) + 180) % 360 - 180) for n in range(0, 360, 30)) * d * math.pi / 180 < 0.6
            band = any(abs(d - r) < 0.5 for r in (10, 17, 24))
            if rib or band:
                p.set(x, top, z, GOLD)
                p.set(x, top - 1, z, TRIM if band else GOLD)
                continue
            el = quadrant(x, z)
            star = el is not None and d > 10 and rng.random() < 0.08
            p.set(x, top, z, lit_block(TRANS_COLOURS[el]) if star else "Rock_Quartzite_Brick_Smooth")
        for r, a in ((13.5, 15), (13.5, 75), (13.5, 105), (13.5, 165), (20.5, 45), (20.5, 135), (13.5, 255),
                     (13.5, 285), (20.5, 315), (20.5, 225)):
            self.hang(*at3(r, top - 1, a), CHANDELIER)

    def lab(self):
        p = self.p
        y = F_LAB
        # Cuve centrale : deux blocs d'eau acide verte (comme à Deepworks) dans une margelle de verre cerclée d'or. Son fond
        # fait la rosace du plafond de la Salle des Transmutations, où pend un lustre.
        for x, z, d, a in ring(0, 9):
            if d < 7.5:
                p.fluid(x, y - 1, z, ACID)
                p.fluid(x, y - 2, z, ACID)
                p.set(x, y - 3, z, "Rock_Gold_Brick_Ornate" if d < 2.5 else GOLD if d < 4 or d >= 6.5 else
                      "Rock_Crystal_Green_Block")
            else:
                p.set(x, y, z, GOLD)
                p.set(x, y + 1, z, GLASS)
                p.set(x, y - 2, z, GOLD)
                p.set(x, y - 3, z, TRIM)
        self.hang(0, y - 4, 0, CHANDELIER)
        # Bassins secondaires : les zombies de la Chimère y remplissent leurs seaux d'acide.
        for k in CHIMERA_BASIN_ANGLES:
            bx, bz = at(CHIMERA_BASIN_R, k)
            for x, z, d, a in ring(0, CHIMERA_BASIN_SIZE + 1, reach=3):
                if d < CHIMERA_BASIN_SIZE:
                    p.fluid(bx + x, y - 1, bz + z, ACID)
                    p.set(bx + x, y - 2, bz + z, GOLD)
                else:
                    p.set(bx + x, y, bz + z, GOLD)
                    self.keep_clear.update((bx + x, y + j, bz + z) for j in range(1, 3))
        # Rayonnages du mur entre les alcôves (decor_lab) : la salle reste dégagée pour le combat de la Chimère.
        for x, z, d, a in ring(28.4, R_IN):
            if in_arc(a, 255, 285) or in_arc(a, 300, 345):
                continue
            if any(abs(((a - k) + 180) % 360 - 180) < 7 for k in LAB_ALCOVES):
                continue
            for k in range(0, 6):
                self.place(x, y + k, z, SHELF, wall_facing(x, z))
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
            # Côtés du secteur : au moins un bloc d'épaisseur le long de chaque rayon, sans fente en diagonale (Kevin,
            # 19 octobre 2026 : la barrière de l'arène doit être le seul passage).
            margin = min((a - 200 + 180) % 360 - 180, (275 - a + 180) % 360 - 180)
            side = d * math.radians(margin)
            if side < -1.0:
                continue
            edge = d < 24 or side < 1.2
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
        """Bureau de l'Alchimiste, au sud de la terrasse, ouvert à la mort du boss : pierre philosophale, portail de fin."""
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
        # Piédestal de la pierre philosophale (chaque joueur y prend la sienne), bureau, portail de fin.
        p.set(0, y, 32, "Rock_Gold_Brick_Pillar_Base")
        p.set(0, y + 1, 32, "Rock_Gold_Brick_Ornate")
        p.set(0, y + 2, 32, PEDESTAL_STONE, pf.SOUTH)
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
        """Point de contrôle : statue de Deepworks sur un socle doré (son volume est écrit par generate_alchemist_tower) ;
        le joueur s'arrête en (x, y, z)."""
        sx, sz = statue_at
        for k in range(3):  # la statue peut prendre la place d'un bout de parapet
            if (sx, y + k, sz) in self.parapets:
                self.p.set(sx, y + k, sz, AIR)
        rot = facing_to(sx, sz, x, z)  # la statue regarde l'endroit où le joueur s'arrête
        self.p.set(sx, y - 1, sz, "Rock_Gold_Brick_Ornate")
        if not self.p.fits(sx, y, sz, STATUE, rot):
            raise RuntimeError(f"tour : pas de place pour la statue du point de contrôle {(sx, y, sz)}")
        self.p.set(sx, y, sz, STATUE, rot)
        self.checkpoints.append((x, y, z))
        self.statues.append(((sx, y, sz), rot))
        # Le décor laisse libre l'arrêt du joueur.
        self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3)
                               if self.p.free(x + dx, y + k, z + dz))

    # --- mobs (étape 3) ---------------------------------------------------------------------------

    def spawn_cell(self, x, y, z, height=3, reach=6):
        """Case libre la plus proche de (x, y, z) au même niveau : sol plein dessous, `height` blocs d'air au-dessus."""
        best = None
        for dx in range(-reach, reach + 1):
            for dz in range(-reach, reach + 1):
                cx, cz = x + dx, z + dz
                if not self.solid(cx, y - 1, cz) or (cx, y, cz) in self.keep_clear:
                    continue
                if all(self.p.free(cx, y + k, cz) for k in range(height)):
                    d = dx * dx + dz * dz
                    if best is None or d < best[0]:
                        best = (d, cx, cz)
        if best is None:
            raise RuntimeError(f"tour : pas de place pour un mob près de {(x, y, z)}")
        return best[1], best[2]

    def spawner(self, role, x, y, z, height=3):
        cx, cz = self.spawn_cell(x, y, z, height)
        self.p.set(cx, y, cz, SPAWNER_PREFIX + role)
        self.spawners.append((role, (cx, y, cz)))

    def ramp_cell(self, angle, d_target=37.0):
        """Case de l'Escalier des vents la plus proche de l'angle donné (degrés), et son premier bloc d'air."""
        best = None
        for (x, z), s in self.wind_ramp.items():
            d, a = polar(x, z)
            score = abs((a - angle + 180) % 360 - 180) * 2 + abs(d - d_target)
            if best is None or score < best[0]:
                best = (score, x, (s + 1) // 2, z)
        return best[1:]

    def mobs(self):
        """Blocs d'apparition des mobs (tools/generate_tower_mobs.py), salle par salle. Peu de mobs dans les phases de
        pièges (Couloir des fuites, Escalier des vents) pour qu'on lise bien le rythme des pièges."""
        self.spawners = []
        for role, (r, y, a), h in MOB_LAYOUT:
            self.spawner(role, *at3(r, y, a), height=h)
        for role, xyz, h in MOB_FIXED:
            self.spawner(role, *xyz, height=h)
        # Gardiens d'airain sur leurs socles de la cour : les abattre tous ouvre les portes de la tour (CourtGuardSystem).
        for gx, gz in GUARDIANS:
            self.spawner("Brass_Guardian", gx, 0, gz, height=5)
        # Le Codex vivant flotte au centre de la rotonde, entre ses trois pupitres (case réservée par `codex`).
        self.p.set(0, F_LIBRARY, 0, SPAWNER_PREFIX + "Living_Codex")
        self.spawners.append(("Living_Codex", (0, F_LIBRARY, 0)))
        # Le golem de cristal au centre de la Salle des Transmutations : ses esprits viennent avec les quadrants.
        self.p.set(0, F_TRANS, 0, SPAWNER_PREFIX + "Crystal_Golem")
        self.spawners.append(("Crystal_Golem", (0, F_TRANS, 0)))
        # La Chimère rôde au sud de la cuve, face à l'arrivée de l'escalier des transmutations.
        sx, sy, sz = self.trap["chimera"]["spawn"]
        self.p.set(sx, sy, sz, SPAWNER_PREFIX + "Lab_Chimera")
        self.spawners.append(("Lab_Chimera", (sx, sy, sz)))
        # L'Alchimiste attend sur la terrasse, face à la porte de l'antichambre (case réservée par `alchemist`).
        sx, sy, sz = self.trap["alchemist"]["spawn"]
        self.p.set(sx, sy, sz, SPAWNER_PREFIX + "Alchemist")
        self.spawners.append(("Alchemist", (sx, sy, sz)))
        # Gargouilles au-dessus de l'Escalier des vents : elles volent, on les pose deux blocs au-dessus des marches.
        for angle in GARGOYLE_ANGLES:
            x, y, z = self.ramp_cell(angle)
            if not all(self.p.free(x, y + k, z) for k in range(4)):
                raise RuntimeError(f"tour : pas de place pour une gargouille en {(x, y, z)}")
            self.p.set(x, y + 2, z, SPAWNER_PREFIX + "Tower_Gargoyle")
            self.spawners.append(("Tower_Gargoyle", (x, y + 2, z)))

    # --- pièges et énigmes (étape 4) --------------------------------------------------------------

    def seal(self, cells, y0, y1, force=False):
        """Sceau alchimique sur les colonnes (x, z), de y0 à y1 exclu (sur l'air seulement, sauf force) ; renvoie ses
        blocs. Le volume du sceau le dissout quand l'énigme est résolue."""
        out = []
        for x, z in cells:
            for y in range(y0, y1):
                if force or self.p.free(x, y, z):
                    self.p.set(x, y, z, SEAL)
                    out.append((x, y, z))
        return out

    def usable(self, x, y, z, name, rot=0, plinth="Rock_Gold_Brick_Ornate"):
        """Bloc à utiliser (brasero éteint, levier), sur un socle doré ; décor et mobs lui laissent la place autour."""
        if plinth:
            self.p.set(x, y - 1, z, plinth)
        if not self.p.fits(x, y, z, name, rot):
            raise RuntimeError(f"tour : pas de place pour {name} en {(x, y, z)}")
        self.p.set(x, y, z, name, rot)
        self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3)
                               if self.p.free(x + dx, y + k, z + dz))
        return x, y, z

    def traps(self):
        """Blocs des pièges et des énigmes ; `self.trap` garde leurs positions pour tools/alchemist_traps.py."""
        t = self.trap = {}
        p = self.p
        # Hall des Alambics : trois athanors éteints devant les fours. Tant qu'ils ne brûlent pas tous les trois, le
        # sceau ferme le Couloir des fuites juste après l'arrivée de la rampe.
        t["athanors"] = [self.usable(*at3(HALL_ATHANOR_R, F_HALL, k), FOYER) for k in HALL_ATHANOR_ANGLES]
        t["hall"] = self.hall_parts
        t["court_door"] = self.court_door
        t["hall_seal"] = self.seal([(x, z) for x, z, d, a in ring(18, R_IN) if in_arc(a, *HALL_SEAL_ARC)],
                                   F_LEAKS, F_LIBRARY - 1)
        # Trois gemmes éteintes sur la face du sceau qui regarde l'arrivée de la rampe, une par athanor.
        seal_cells = t["hall_seal"]
        sockets = []
        for r in (21.5, 23.5, 25.5):
            row = [c for c in seal_cells if c[1] == F_LEAKS + 2 and abs(math.hypot(c[0], c[2]) - r) < 0.75]
            c = min(row, key=lambda c: polar(c[0], c[2])[1])
            p.set(*c, SOCKET)
            seal_cells.remove(c)
            sockets.append(c)
        t["hall_seal_sockets"] = sockets
        # Couloir des fuites : les buses de gaz (`gas_nozzles`).
        t["nozzles"] = self.nozzles
        # Au fond, derrière la porte ouest, le levier coupe la vanne : les jets cessent et le barrage de 240° s'ouvre
        # en raccourci vers l'arrivée de la rampe du hall.
        lx, lz = at(25, 220)
        t["lever"] = self.usable(lx, F_LEAKS, lz, VALVE, facing_center(lx, lz), plinth=None)
        # Tuyauterie de la vanne : la conduite de gaz luisante monte du sol au plafond juste derrière la vanne, entre deux
        # grosses conduites et deux tuyaux fins ; deux fuites crachent de la vapeur tant que la vanne est ouverte.
        top = F_LIBRARY - 2
        for y in range(F_LEAKS + 2, top + 1):  # la vanne (deux blocs de haut) est montée sur sa conduite
            p.set(lx, y, lz, PIPE)
        glow, leaks = [], []
        for r, da, name in ((26.6, 0, PIPE_GLOW), (27.4, -5, PIPE), (27.4, 5, PIPE), (28.4, -9, PIPE_THIN),
                            (28.4, 9, PIPE_THIN)):
            px, pz = at(r, 220 + da)
            for y in range(F_LEAKS, top + 1):
                p.set(px, y, pz, name)
                if name == PIPE_GLOW:
                    glow.append((px, y, pz))
        for da, dy in ((-3, 3), (3, 6)):
            vx, vz = at(25.6, 220 + da)
            if p.free(vx, F_LEAKS + dy, vz):
                p.set(vx, F_LEAKS + dy, vz, LEAK)
                leaks.append((vx, F_LEAKS + dy, vz))
        t["valve_pipes"], t["valve_leaks"] = glow, leaks
        t["shortcut_seal"] = self.seal([(x, z) for x, z, d, a in ring(20.5, 27.5) if in_arc(a, *SHORTCUT_ARC)],
                                       F_LEAKS, F_LEAKS + 4, force=True)
        # Serre suspendue : un grand champignon par nappe de spores, origine visible du nuage qu'il lâche.
        t["spores"] = [(x, F_LEAKS, z) for x, z in (self.spawn_cell(*at3(40, F_LEAKS, a), reach=3)
                                                    for a in (205, 225, 245, 265, 285))]
        for x, y, z in t["spores"]:
            p.set(x, y, z, SPORE_SHROOM)
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2)
                                   for k in range(3) if (dx, dz, k) != (0, 0, 0) and p.free(x + dx, y + k, z + dz))
        # Bibliothèque : une haie de ronces barre le pied de la rampe, jusqu'à ce que la rampe soit trop haute pour qu'on
        # y saute depuis le sol ; le brasero éteint devant elle y met le feu. Des livres tombent des rayonnages.
        hedge = []
        for x, z, d, a in ring(18, R_IN):
            if not in_arc(a, *HEDGE_ARC):
                continue
            s = self.library_ramp.get((x, z))
            y0 = (s + 1) // 2 if s is not None else F_LIBRARY
            for y in range(y0, y0 + 4):
                if p.free(x, y, z):
                    p.set(x, y, z, HEDGE)
                    hedge.append((x, y, z))
        t["hedge"] = hedge
        t["hedge_brazier"] = self.usable(*at3(20, F_LIBRARY, 62), FOYER)
        t["books"] = [(x, F_LIBRARY, z) for x, z in
                      (self.spawn_cell(*at3(13 if i % 2 else 18, F_LIBRARY, a), reach=3)
                       for i, a in enumerate((15, 50, 100, 145, 190, 225, 245, 265, 290, 315)))]
        # Salle des Transmutations : le golem de cristal et ses quatre quadrants (TransmutationSystem). Le sceau ferme le
        # pied de l'hélice (les marches d'un demi-bloc à un bloc et demi : plus haut, on n'y saute pas depuis le sol)
        # jusqu'à la mort du golem.
        y = F_TRANS
        t["trans_seal"] = []
        for (x, z), s in sorted(self.trans_stair.items()):
            if 2 * y < s <= 2 * y + 3:
                t["trans_seal"] += self.seal([(x, z)], (s + 1) // 2, y + 6)
        zones, spirits = {}, {}
        for el, (sx, sz) in TRANS_QUADRANTS.items():
            xs = sorted((sx * 1, sx * math.floor(R_IN)))
            zs = sorted((sz * 1, sz * math.floor(R_IN)))
            zones[el] = ((xs[0], y, zs[0]), (xs[1], y + TRANS_ZONE_HEIGHT - 1, zs[1]))
            angle = math.degrees(math.atan2(sz, sx)) % 360
            spirits[el] = [(x, y, z) for x, z in (self.spawn_cell(*at3(r, y, angle + da), reach=3)
                                                   for r, da in ((12, -12), (17, 10), (21, -20), (21, 20)))]
        golem = (0, y, 0)
        self.keep_clear.update((x, y + k, z) for x in range(-2, 3) for z in range(-2, 3) for k in range(5))
        t["trans"] = {"center": golem, "zones": zones, "spirits": spirits}
        # Escalier des vents : bouches de flammes dans le mur de la tour, secteurs de rafales (vers le mur, jamais vers le
        # vide), points d'impact de la foudre.
        t["flames"] = []
        for i, a in enumerate(FLAME_ANGLES):
            cells = [self.ramp_cell(a, r) for r in (35.5, 39.0)]
            nx, nz = at(33, a)
            ny = cells[0][1] + 1
            p.set(nx, ny, nz, "Rock_Gold_Brick_Ornate")
            t["flames"].append((a, "A" if i % 2 == 0 else "B", cells, (nx, ny, nz)))
        t["gusts"] = [(a, "A" if i % 2 == 0 else "B", [self.ramp_cell(a + k, 37.2) for k in (-10, -5, 0, 5, 10)])
                      for i, a in enumerate(GUST_SECTORS)]
        t["strikes"] = [self.ramp_cell(a, 35.5 if i % 2 else 38.8) for i, a in enumerate(STRIKE_ANGLES)]

    # --- Codex vivant (étape 5) -------------------------------------------------------------------

    def codex(self):
        """Arène du Codex vivant, au centre de la rotonde de la bibliothèque ; `self.trap["codex"]` garde ses positions
        pour tools/alchemist_traps.py et TowerLayout.java : trois pupitres (le Codex y ouvre ses chapitres), le sceau
        qui ferme le haut de la rampe jusqu'à sa mort, et les éboulis des pans d'étagères qui s'effondrent."""
        p = self.p
        y = F_LIBRARY
        lecterns = []
        for a in LECTERN_ANGLES:
            x, z = at(LECTERN_R, a)
            if not p.free(x, y, z):
                raise RuntimeError(f"tour : pas de place pour un pupitre du Codex en {(x, y, z)}")
            p.set(x, y, z, LECTERN)
            lecterns.append((x, y, z))
            # Le chapitre flotte au-dessus du pupitre : le décor laisse la place et le passage autour.
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2)
                                   for k in range(4) if (dx, dz, k) != (0, 0, 0))
        # Le Codex flotte au centre : rien n'y est posé.
        self.keep_clear.update((x, y + k, z) for x in range(-3, 4) for z in range(-3, 4) for k in range(5)
                               if math.hypot(x, z) < 3.5)
        seal = []
        for (x, z), s in sorted(self.library_ramp.items()):
            if in_arc(polar(x, z)[1], *CODEX_SEAL_ARC):
                seal += self.seal([(x, z)], (s + 1) // 2, F_TRANS + 3)
        rubble = []
        for a0, a1 in COLLAPSE_ARCS:
            cells = []
            for x, z, d, a in ring(*COLLAPSE_R):
                if not in_arc(a, a0, a1) or not self.solid(x, y - 1, z):
                    continue
                for k in range(2 if d >= 25 else 1):
                    if not p.free(x, y + k, z) or (x, y + k, z) in self.keep_clear:
                        break
                    cells.append((x, y + k, z))
                    self.keep_clear.add((x, y + k, z))
            rubble.append(cells)
        self.trap["codex"] = {"center": (0, y, 0), "lecterns": lecterns, "seal": seal, "rubble": rubble}

    # --- Chimère du laboratoire (étape 6) ---------------------------------------------------------

    def chimera(self):
        """Arène de la Chimère (un dragon qui ne vole pas), tout le laboratoire autour de la cuve centrale ;
        `self.trap["chimera"]` garde ses positions pour tools/alchemist_traps.py et TowerLayout.java : les bassins
        secondaires et, devant chacun, la case où un zombie apparaît pour remplir son seau d'acide (ChimeraSystem), et
        le sceau de la porte nord (vers l'Escalier des vents) qui tient jusqu'à sa mort."""
        y = F_LAB
        basins, fills = [], []
        for a in CHIMERA_BASIN_ANGLES:
            bx, bz = at(CHIMERA_BASIN_R, a)
            basins.append((bx, y, bz))
            # Le zombie apparaît du côté de la cuve, contre la margelle ; le décor laisse la place et le passage.
            x, z = self.spawn_cell(*at3(CHIMERA_BASIN_R - CHIMERA_BASIN_SIZE - 2, y, a), height=3, reach=2)
            fills.append((x, y, z))
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(3))
        # Elle rôde au sud de la cuve, face à l'arrivée de l'hélice : place libre pour sa carrure.
        sx, sz = self.spawn_cell(*at3(15, y, 60), height=4, reach=3)
        self.keep_clear.update((sx + dx, y + k, sz + dz) for dx in range(-3, 4) for dz in range(-3, 4) for k in range(4))
        seal = self.seal([(x, CHIMERA_DOOR_Z) for x in range(-2, 3)], y, y + 5)
        if len(seal) != 25:
            raise RuntimeError(f"tour : le sceau de la Chimère ne ferme pas la porte nord ({len(seal)} blocs)")
        self.trap["chimera"] = {"vat": (0, y, 0), "spawn": (sx, y, sz), "basins": basins, "fills": fills, "seal": seal}

    # --- l'Alchimiste (étape 7) --------------------------------------------------------------------

    def alchemist(self):
        """Arène de l'Alchimiste, toute la terrasse de l'Observatoire ; `self.trap["alchemist"]` garde ses positions pour
        tools/alchemist_traps.py et TowerLayout.java :
        - l'athanor au centre : un four d'or et de verre dont la chambre (3 × 3, 5 de haut) l'enferme au Grand Œuvre ;
        - les cases libres autour où il en ressort, les quatre piliers de la Convergence, les fioles de soin ;
        - les pans du rebord en encorbellement qui s'effondrent (blocs du sol et du dessous), loin de l'antichambre, du
          bureau et de l'arrivée de l'Escalier des vents ;
        - le levier du mode difficile dans l'antichambre et le sceau de la porte du bureau, qui tient jusqu'à sa mort."""
        p = self.p
        y = F_DECK
        # Athanor : murs d'or, fenêtres de verre violet, coupole et cheminée.
        for x, z, d, a in ring(0, ATHANOR_R):
            if d < ATHANOR_ROOM:
                p.set(x, y - 1, z, "Rock_Crystal_Purple_Block")
                for k in range(5):
                    p.set(x, y + k, z, AIR)
                    self.keep_clear.add((x, y + k, z))
                p.set(x, y + 5, z, GOLD)
            else:
                window = int(a + 22.5) % 90 < 30
                for k in range(6):
                    p.set(x, y + k, z, GLASS if window and 1 <= k <= 3 else (TRIM if k in (0, 5) else GOLD))
                if d < ATHANOR_R - 1:
                    p.set(x, y + 6, z, TRIM)
            self.keep_clear.update((x, y + k, z) for k in range(12))
        for k in range(6, 11):
            p.set(0, y + k, 0, "Rock_Gold_Brick_Pillar_Middle")
        p.set(0, y + 11, 0, "Nakasar_Tower_Emanation_Smoke")
        # Le décor laisse un tour libre autour de l'athanor.
        self.keep_clear.update((x, y + k, z) for x, z, d, a in ring(ATHANOR_R, ATHANOR_R + 2.5) for k in range(4))

        def spot(r, a, height=3, reach=2, clear=1):
            x, z = self.spawn_cell(*at3(r, y, a), height=height, reach=reach)
            self.keep_clear.update((x + dx, y + k, z + dz) for dx in range(-clear, clear + 1)
                                   for dz in range(-clear, clear + 1) for k in range(height))
            return x, y, z

        exits = [spot(ALCHEMIST_EXIT_R, a) for a in range(0, 360, 45)]
        pillars = [spot(PILLAR_R, a, height=4) for a in PILLAR_ANGLES]
        heals = [spot(HEAL_R, a) for a in HEAL_ANGLES]
        spawn = spot(10, 245, height=3, clear=1)
        # Pans du rebord : le sol (y - 1) et le dessous de l'encorbellement (y - 2), seulement là où le sol est libre.
        collapse = []
        for a0, a1 in DECK_COLLAPSE_ARCS:
            cells = []
            for x, z, d, a in ring(*DECK_COLLAPSE_R):
                if not in_arc(a, a0, a1) or p.get(x, y - 1, z) not in [n for n, _ in FLOOR]:
                    continue
                if any(not p.free(x, y + k, z) for k in range(3)):
                    continue
                cells.append((x, y - 1, z))
                if p.get(x, y - 2, z) in [n for n, _ in WALL]:
                    cells.append((x, y - 2, z))
                self.keep_clear.update((x, y + k, z) for k in range(4))
            if len(cells) < 40:
                raise RuntimeError(f"tour : pan du rebord trop petit ({a0}-{a1}° : {len(cells)} blocs)")
            collapse.append(cells)
        safe = []
        for a in range(0, 360, 15):
            if in_arc(a, *ANTECHAMBER_ARC) or in_arc(a, 60, 120):
                continue
            x, z = at(SAFE_R, a)
            if self.solid(x, y - 1, z) and all(p.free(x, y + k, z) for k in range(2)):
                safe.append((x, y, z))
        # Levier du mode difficile, dans l'antichambre, avant la porte de la terrasse.
        lx, lz = at(31, 228)
        lever = self.usable(lx, y, lz, LEVER, facing_center(lx, lz), plinth=None)
        seal = self.seal([(x, STUDY_DOOR_Z) for x in range(-2, 3)], y, y + 5)
        if len(seal) != 25:
            raise RuntimeError(f"tour : le sceau du bureau ne ferme pas sa porte ({len(seal)} blocs)")
        self.trap["alchemist"] = {"center": (0, y, 0), "exits": exits, "pillars": pillars, "heals": heals,
                                  "spawn": spawn, "collapse": collapse, "safe": safe, "lever": lever, "seal": seal}

    def arenas(self):
        """Barrières des trois arènes de boss, hors de l'arène, là où l'on y entre : couche extérieure de la porte de la
        bibliothèque, couvercle sur la trémie de l'hélice des transmutations, au niveau du plancher du laboratoire, côté antichambre
        de la porte de la terrasse. Cases libres que le décor laisse vides ; `self.trap["arenas"]` les donne par boss."""
        library = [(x, y, z) for x, z, d, a in ring(R_IN - 0.5, R_OUT + 0.5) if abs(a - 50) < 5 and d >= R_OUT - 1
                   for y in range(F_LIBRARY, F_LIBRARY + 5)]
        # Laboratoire : un couvercle à plat sur la trémie de l'hélice, au niveau du plancher (Kevin, 19 octobre 2026 : la
        # barrière debout en travers des marches ne fermait pas vraiment le passage).
        lab = [(x, F_LAB - 1, z) for (x, z) in self.trans_stair if self.p.free(x, F_LAB - 1, z)]
        deck = [(x, y, z) for x, z, d, a in ring(21.5, 24.6) if abs(a - 245) < 5 and d >= 23
                for y in range(F_DECK, F_DECK + 5)]
        arenas = {"Codex": library, "Chimera": lab, "Alchemist": deck}
        for name, cells in arenas.items():
            taken = [c for c in cells if not self.p.free(*c)]
            if taken:
                raise RuntimeError(f"tour : la barrière de l'arène {name} tombe sur des blocs {taken[:4]}")
            self.keep_clear.update(cells)
        self.trap["arenas"] = arenas

    # --- décor -----------------------------------------------------------------------------------

    def hang(self, x, y, z, name, rot=0):
        """Pend un lustre ou une lanterne au plafond : cases libres, plafond plein juste au-dessus de (x, y, z)."""
        cells = pf.footprint(name, rot)
        if any((x + dx, y + dy, z + dz) in self.keep_clear or not self.p.free(x + dx, y + dy, z + dz)
               or (x + dx, y + dy, z + dz) in self.p.claims for dx, dy, dz in cells):
            return False
        if not self.solid(x, y + 1, z):
            return False
        self.p.set(x, y, z, name, rot)
        return True

    def chain(self, x, y, z, length, name="Deco_Iron_Chains_Vertical", end=None):
        """Chaîne (ou liane) qui pend du plafond plein en y + 1, terminée par `end` (lanterne...)."""
        if not self.solid(x, y + 1, z):
            return
        for k in range(length):
            cell = (x, y - k, z)
            if cell in self.keep_clear or not self.p.free(*cell):
                return
            self.p.set(*cell, end if (end and k == length - 1) else name)

    def table(self, x, y, z, name, tops, chairs=None):
        """Table de 2 × 2 (coin nord-ouest en x, z) garnie de `tops` (un objet par case du dessus), chaises autour."""
        if not self.place(x, y, z, name):
            return False
        for (dx, dz), top in zip(((0, 0), (1, 0), (0, 1), (1, 1)), tops):
            if top:
                self.place(x + dx, y + 1, z + dz, top)
        if chairs:
            for cx, cz, rot in ((x - 1, z, pf.EAST), (x + 2, z + 1, pf.WEST), (x + 1, z - 1, pf.SOUTH),
                                (x, z + 2, pf.NORTH)):
                self.place(cx, y, cz, chairs, rot)
        return True

    def flask(self, cx, y, cz, liquid="Rock_Crystal_Green_Block", height=4):
        """Alambic : socle d'or, panse de verre au cœur de cristal coloré, col d'or et émanation au sommet."""
        cells = [(cx + dx, y + k, cz + dz) for dx in range(-1, 2) for dz in range(-1, 2) for k in range(height + 4)]
        if any(c in self.keep_clear or not self.p.free(*c) for c in cells):
            return False
        p = self.p
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                p.set(cx + dx, y, cz + dz, GOLD if (dx, dz) != (0, 0) else "Rock_Gold_Brick_Ornate")
                for k in range(1, height):
                    p.set(cx + dx, y + k, cz + dz, liquid if (dx, dz) == (0, 0) else GLASS)
                p.set(cx + dx, y + height, cz + dz, TRIM if (dx * dz) else GOLD)
        p.set(cx, y + height + 1, cz, GLASS)
        p.set(cx, y + height + 2, cz, "Rock_Gold_Brick_Pillar_Middle")
        p.set(cx, y + height + 3, cz, "Nakasar_Tower_Emanation_Motes")
        return True

    def inlay(self, cells, y, block, over=None):
        """Incruste `block` dans le sol (y - 1) des cases (x, z) : seulement sur le dallage (ou les blocs `over`)."""
        allowed = set(over) if over else {n for n, _ in FLOOR} | {TRIM}
        for x, z in cells:
            if self.p.get(x, y - 1, z) in allowed and self.p.free(x, y, z):
                self.p.set(x, y - 1, z, block)

    def ring_cells(self, r0, r1):
        return [(x, z) for x, z, d, a in ring(r0, r1)]

    @staticmethod
    def segment(x0, z0, x1, z1):
        """Cases d'un trait droit de (x0, z0) à (x1, z1)."""
        n = max(abs(x1 - x0), abs(z1 - z0), 1)
        return sorted({(round(x0 + (x1 - x0) * t / n), round(z0 + (z1 - z0) * t / n)) for t in range(n + 1)})

    def gate_braziers(self, y, r, a, spread):
        """Deux braseros allumés encadrent l'entrée d'une arène, côté arène : le même repère pour les trois boss."""
        for k in (a - spread, a + spread):
            x, z = at(r, k)
            if not self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On"):
                raise RuntimeError(f"tour : pas de place pour le brasero de l'entrée de l'arène en {(x, y, z)}")

    def wall_ring(self, y0, y1, arcs_out, every=20, fill=12, names=(SHELF,)):
        """Meubles adossés au mur intérieur (r 28,4 à 29,5) de y0 à y1, par tronçons de `fill` degrés sur `every`."""
        for x, z, d, a in ring(28.4, R_IN):
            if any(in_arc(a, a0, a1) for a0, a1 in arcs_out) or int(a) % every >= fill:
                continue
            name = names[(int(a) // every) % len(names)]
            for y in range(y0, y1):
                self.place(x, y, z, name, wall_facing(x, z))

    def scatter(self, y, r0, r1, density, names, arcs_out=()):
        """Petit bric-à-brac d'un bloc semé sur le sol (r0 <= d < r1), hors des arcs `arcs_out` et des passages."""
        rng = self.rng
        for x, z, d, a in ring(r0, r1):
            if any(in_arc(a, a0, a1) for a0, a1 in arcs_out) or rng.random() >= density:
                continue
            self.place(x, y, z, rng.choice(names))

    def stations(self, y, r, angles, potions):
        """Postes d'alchimiste : établi tourné vers le centre, chaudron, tonneau et fioles de part et d'autre."""
        for k in angles:
            x, z = at(r, k)
            self.place(x, y, z, "Bench_Alchemy", facing_center(x, z))
            for dk, name in ((-6, "Alchemy_Cauldron"), (6, "Furniture_Ancient_Barrel"), (9, "Furniture_Temple_Wind_Pot")):
                cx, cz = at(r, k + dk)
                self.place(cx, y, cz, name)
            for dk in (-3, 3):
                cx, cz = at(r + 1.5, k + dk)
                self.place(cx, y, cz, self.rng.choice(potions))

    def decor_hall(self):
        """Hall dégagé : le regard va de la porte au grand alambic et aux trois athanors. Le mobilier reste contre le
        mur (étagères, postes d'alchimiste, chaudrons), hors des estrades des athanors et de la colonne relais."""
        y = F_HALL
        rng = self.rng
        potions = ["Deco_Potion", "Potion_Mana_Large", "Potion_Health_Large", "Potion_Poison_Large",
                   "Potion_Stamina_Large", "Potion_Empty_Large", "Potion_Regen_Mana_Large", "Potion_Signature_Greater"]
        busy = [(k - 22, k + 22) for k in HALL_ATHANOR_ANGLES] + [(RELAY[0] - 10, RELAY[0] + 10), (75, 105), (195, 305)]
        # Alambics de verre entre les athanors, loin des passages.
        for k, liquid in ((60, "Rock_Crystal_Green_Block"), (120, "Rock_Crystal_Cyan_Block"),
                          (210, "Rock_Crystal_Pink_Block"), (345, "Rock_Crystal_Yellow_Block")):
            x, z = at(21, k)
            self.flask(x, y, z, liquid)
        # Étagères de réactifs le long du mur, fioles dessus.
        self.wall_ring(y, y + 4, ((195, 305), (78, 102)), every=18, fill=12,
                       names=("Furniture_Village_Shelf_Full", SHELF, "Furniture_Village_Shelf_Full"))
        for x, z, d, a in ring(28.4, R_IN):
            if self.p.get(x, y + 3, z) in ("Furniture_Village_Shelf_Full", SHELF) and rng.random() < 0.6:
                self.place(x, y + 4, z, rng.choice(potions + ["Deco_Book_Pile_Small", "Furniture_Royal_Magic_Potion_Glow"]))
        # Postes d'alchimiste et chaudrons contre le mur, de part et d'autre de la porte et entre les athanors.
        self.stations(y, 24.5, (60, 120, 190, 330), potions)
        for k in (0, 45, 135, 180):
            x, z = at(26, k)
            self.place(x, y, z, "Alchemy_Cauldron_Big")
        self.scatter(y, 22, 27.5, 0.03, ["Deco_Book_Pile_Small", "Deco_Bucket", "Furniture_Ancient_Sack",
                                         "Rock_Crystal_Purple_Small"], busy)
        # Tapis du portail au grand alambic.
        for z in range(8, 26, 2):
            for x in (-2, 0):
                self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        # Lustres et fioles lumineuses au plafond (le plafond est le sol du couloir des fuites).
        top = F_LEAKS - 2
        for r, step, off in ((10, 60, 0), (22, 30, 15)):
            for k in range(off, 360 + off, step):
                x, z = at(r, k)
                self.hang(x, top, z, CHANDELIER)
        for k in range(10, 370, 30):
            x, z = at(17, k + 15)
            self.chain(x, top, z, 3, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")

    def decor_leaks(self):
        """Couloir des fuites : la zone des jets reste dégagée (on doit y lire les buses et les cônes) ; tonneaux,
        caisses et flaques de réactifs après la porte ouest, autour de la vanne."""
        y = F_LEAKS
        rng = self.rng
        top = F_LIBRARY - 2
        jets = (JET_ARC[0] - 8, JET_ARC[1] + 8)
        # Tonneaux, caisses et sacs de réactifs contre le mur extérieur, par grappes.
        for k in range(5, 360, 22):
            if in_arc(k, 225, 255) or in_arc(k, 165, 195) or in_arc(k, *jets):
                continue
            for j, name in enumerate(rng.sample(["Furniture_Ancient_Barrel", "Furniture_Tavern_Barrel",
                                                 "Furniture_Ancient_Crate", "Furniture_Ancient_Sack",
                                                 "Furniture_Ancient_Pot"], 3)):
                x, z = at(26.5 + (j % 2), k + 2.5 * j)
                self.place(x, y, z, name)
                if name == "Furniture_Ancient_Crate" and rng.random() < 0.7:
                    self.place(x, y + 1, z, rng.choice(["Furniture_Ancient_Barrel", "Deco_Bucket", "Furniture_Ancient_Crate"]))
        # Flaques de réactif.
        for k in range(0, 360, 30):
            if in_arc(k + 15, *jets) or in_arc(k + 15, 232, 248):
                continue
            px, pz = at(20, k + 15)
            self.place(px, y, pz, rng.choice(["Rock_Crystal_Green_Small", "Plant_Crop_Mushroom_Glowing_Green",
                                              "Rock_Crystal_Yellow_Small"]))
        self.scatter(y, 24, 28.4, 0.08, ["Deco_Bucket", "Furniture_Ancient_Sack", "Rock_Crystal_Green_Small",
                                         "Deco_Bone_Pile", "Deco_Trash_Pile_Small"], ((228, 252), jets))
        # Chaînes et lanternes qui pendent du plafond.
        for k in range(0, 360, 15):
            if in_arc(k, 232, 248):
                continue
            x, z = at(23, k)
            if k % 30:
                self.chain(x, top, z, 2 + (k // 15) % 3)
            else:
                self.chain(x, top, z, 2, end="Deco_Lantern_Ceiling")

    def decor_greenhouse(self):
        y = F_LEAKS
        rng = self.rng
        # Pots et jarres contre le mur de la tour.
        for x, z, d, a in ring(R_OUT, R_OUT + 1):
            if in_arc(a, *BALCONY_ARC) and int(a) % 9 == 0:
                self.place(x, y, z, "Furniture_Temple_Wind_Pot" if int(a) % 18 == 0 else "Furniture_Royal_Magic_Pot")
        # Sous la verrière : massifs de champignons et de fleurs lumineuses, lianes qui pendent du toit de verre.
        plants = ["Plant_Crop_Mushroom_Glowing_Purple", "Plant_Crop_Mushroom_Glowing_Green", "Plant_Crop_Mushroom_Glowing_Blue",
                  "Plant_Flower_Tall_Cyan", "Plant_Flower_Orchid_Purple", "Plant_Crop_Mushroom_Glowing_Violet"]
        for k in range(GREENHOUSE_ARC[0] + 8, GREENHOUSE_ARC[1] - 4, 16):
            cx, cz = at(39.5, k)
            bed = [(cx + dx, cz + dz) for dx in range(-1, 2) for dz in range(-1, 2)]
            if any((bx, y + kk, bz) in self.keep_clear or not self.p.free(bx, y, bz) for bx, bz in bed for kk in range(2)):
                continue
            for bx, bz in bed:
                self.p.set(bx, y, bz, "Soil_Grass_Full" if (bx, bz) != (cx, cz) else "Plant_Crop_Mushroom_Block_Purple_Trunk")
                if (bx, bz) != (cx, cz):
                    self.p.set(bx, y + 1, bz, rng.choice(plants))
                if (bx, bz) in self.walk:
                    self.walk[(bx, bz)].discard(2 * y)
            for kk in range(1, 4):
                self.p.set(cx, y + kk, cz, "Plant_Crop_Mushroom_Block_Purple_Trunk")
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    self.p.set(cx + dx, y + 4, cz + dz, "Plant_Crop_Mushroom_Block_Purple")
        for x, z, d, a in ring(R_OUT, BALCONY_R):
            if in_arc(a, *GREENHOUSE_ARC) and rng.random() < 0.18:
                self.chain(x, y + 10, z, rng.randint(1, 4), name="Plant_Vine_Hanging")
            elif in_arc(a, *BALCONY_ARC) and d < 44 and rng.random() < 0.06:
                self.place(x, y, z, rng.choice(["Plant_Moss_Rug_Green", "Plant_Moss_Rug_Blue", "Plant_Moss_Rug_Pink"]))
        # Bancs au belvédère nord, tournés vers le large.
        for k in (262, 278):
            x, z = at(42, k)
            self.place(x, y, z, "Furniture_Temple_Light_Bench", pf.NORTH)

    def decor_library(self):
        y = F_LIBRARY
        rng = self.rng
        reading = ["Deco_Book_Pile_Small", "Deco_Scroll", "Furniture_Temple_Wind_Candle", "Deco_Book_Pile_Small",
                   "Furniture_Ancient_Candle", "Deco_Scroll", "Potion_Mana_Large"]
        # Coins de lecture, de part et d'autre des deux rayonnages doubles (dans les quarts libres de la salle).
        for k in (232, 308, 338):
            x, z = at(19, k)
            self.table(x - 1, y, z - 1, "Furniture_Temple_Light_Table", rng.sample(reading, 4), "Furniture_Ancient_Chair")
        # Au centre, l'arène du Codex vivant, lisible d'un coup d'œil : cœur d'or sous le Codex, anneau de cristal violet,
        # trois rayons d'or jusqu'aux pupitres (cerclés d'or), et l'anneau d'or du bord de l'arène.
        self.inlay([(0, 0)], y, "Rock_Gold_Brick_Ornate")
        self.inlay([c for c in self.ring_cells(1, 2)], y, GOLD)
        self.inlay(self.ring_cells(2.6, 3.6), y, "Rock_Crystal_Purple_Block")
        for a in LECTERN_ANGLES:
            lx, lz = at(LECTERN_R, a)
            sx, sz = at(3.6, a)
            ray = self.segment(sx, sz, *at(LECTERN_R - 1.5, a))
            around = [(lx + dx, lz + dz) for dx in range(-1, 2) for dz in range(-1, 2) if (dx, dz) != (0, 0)]
            self.inlay(ray, y, GOLD)
            self.inlay(around, y, TRIM)
            self.keep_clear.update((cx, y, cz) for cx, cz in ray + around)  # pas de tapis par-dessus
        self.inlay(self.ring_cells(12.5, 13.5), y, TRIM)
        # Tapis entre le cœur et l'anneau, sans recouvrir les rayons ni les pupitres.
        for x in range(-12, 12, 2):
            for z in range(-12, 12, 2):
                if 4.5 <= math.hypot(x + 0.5, z + 0.5) < 11:
                    self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        # Entrée de l'arène : deux braseros allumés de part et d'autre de la porte.
        self.gate_braziers(y, 27, 50, 9)
        # Échelles contre les étagères, piles de livres au pied des murs.
        for k in (232, 300, 345):
            x, z = at(27.4, k)
            for yy in range(y, y + 6):
                self.place(x, yy, z, "Furniture_Temple_Light_Ladder", facing_center(x, z))
        for x, z, d, a in ring(26.5, 28.4):
            if not in_arc(a, 60, 215) and rng.random() < 0.12:
                self.place(x, y, z, rng.choice(["Deco_Book_Pile_Small", "Deco_Book_Pile_Large", "Deco_Scroll"]))
        # Lustres sous la coupole, fioles lumineuses sous les galeries.
        low = self.vault_low
        self.hang(0, low[(0, 0)] - 1, 0, "Furniture_Temple_Wind_Chandelier")
        for r, step, off in ((10, 60, 30), (18, 45, 0)):
            for k in range(off, 360 + off, step):
                x, z = at(r, k)
                self.chain(x, low[(x, z)] - 1, z, 5, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")
        for g in (14, 22):
            for k in range(0, 360, 20):
                if not in_arc(k, 60, 215):
                    x, z = at(26, k)
                    self.chain(x, y + g - 1, z, 1, name="Furniture_Royal_Magic_Potion_Glow_Ceiling")
        # Salle secrète : crânes, grimoires, rouleaux, bougies.
        cx, cz = at(39, 320)
        for (dx, dz), name in zip(((-4, -4), (4, -4), (-4, 4), (4, 4), (-2, -4), (2, 4), (0, -4)),
                                  ("Deco_Bone_Skulls", "Deco_Book_Pile_Large", "Furniture_Ancient_Candle",
                                   "Deco_Scroll", "Deco_Book_Pile_Small", "Furniture_Ancient_Candle", "Deco_Treasure_Pile_Small")):
            self.place(cx + dx, y, cz + dz, name)

    def decor_transmutation(self):
        """Salle ronde du golem : le centre reste dégagé pour le combat, chaque quadrant a son décor élémentaire contre le
        mur (sous l'hélice au nord) ; quatre colonnes d'or sur la croix portent le plafond."""
        y = F_TRANS
        p = self.p
        rng = self.rng
        # Cercle de transmutation : deux anneaux d'or au sol, sceau au centre.
        for x, z, d, a in ring(0, 11):
            if 4.5 <= d < 5.4 or 9.5 <= d < 10.4:
                p.set(x, y - 1, z, GOLD)
        p.set(0, y - 1, 0, "Rock_Gold_Brick_Ornate")
        # Colonnes d'or sur la croix, coiffées de cristal violet sous le plafond.
        for a in (0, 90, 180, 270):
            cx, cz = at(20, a)
            for k in range(0, F_LAB - 3 - y):
                if (cx, y + k, cz) in self.keep_clear or not p.free(cx, y + k, cz):
                    break
                p.set(cx, y + k, cz, "Rock_Gold_Brick_Pillar_Base" if k == 0 else
                      "Rock_Crystal_Purple_Block" if k == F_LAB - 4 - y else "Rock_Gold_Brick_Pillar_Middle")
        # Sol élémentaire en couronne (au-delà du cercle) et objets du quadrant.
        floors = {"Fire": "Rock_Magma_Cooled", "Ice": "Rock_Ice_Permafrost", "Earth": "Rock_Basalt_Cobble",
                  "Air": "Rock_Chalk_Brick"}
        props = {"Fire": [BRAZIER, "Rock_Crystal_Red_Large", "Rock_Crystal_Red_Medium", "Rock_Magma_Cooled_Half"],
                 "Ice": ["Rock_Crystal_White_Large", "Rock_Crystal_Cyan_Large", "Rock_Crystal_Cyan_Medium",
                         "Rock_Crystal_White_Medium"],
                 "Earth": ["Furniture_Dungeon_Earth_Brazier", "Rock_Crystal_Green_Large", "Rock_Crystal_Green_Medium",
                           "Rock_Basalt_Cobble_Half"],
                 "Air": ["Furniture_Temple_Wind_Pot", "Furniture_Temple_Wind_Candle", "Rock_Crystal_Yellow_Large",
                         "Rock_Crystal_Yellow_Medium"]}
        for x, z, d, a in ring(14, R_IN):
            el = quadrant(x, z)
            if el is None or p.get(x, y - 1, z) in (None, AIR) or (x, z) in self.trans_stair:
                continue
            if p.get(x, y - 1, z) in {n for n, _ in FLOOR} and rng.random() < (0.25 if d < 19 else 0.6):
                p.set(x, y - 1, z, floors[el])
            if d >= 19 and rng.random() < 0.12:
                self.place(x, y, z, rng.choice(props[el]))
        # Une pièce maîtresse par quadrant, contre le mur ou devant l'hélice.
        pieces = {"Earth": (24, 45), "Air": (24, 135), "Ice": (16, 225), "Fire": (16, 315)}
        for el, (r, a) in pieces.items():
            cx, cz = at(r, a)
            if el == "Air":
                self.place(cx, y, cz, "Furniture_Temple_Wind_Statue", facing_center(cx, cz))
                for da in (-9, 9):
                    self.place(*at3(r, y, a + da), "Furniture_Temple_Wind_Candle")
                continue
            if el == "Earth":
                self.place(cx, y, cz, "Furniture_Dungeon_Earth_Brazier")
            else:
                crystal = {"Ice": ("Rock_Crystal_Cyan_Block", "Rock_Crystal_White_Block"),
                           "Fire": ("Rock_Crystal_Red_Block", "Rock_Magma_Cooled")}[el]
                for x, z, d, _ in ring(0, 2.3, reach=3):  # aiguille de 5 blocs : on ne l'escalade pas
                    for k in range(5 if d < 0.5 else 2 if d < 1.5 else 1):
                        c = (cx + x, y + k, cz + z)
                        if c not in self.keep_clear and p.free(*c):
                            p.set(*c, crystal[(x + z + k) % 2])
            for da in (-7, 7):
                self.place(*at3(r, y, a + da), props[el][1])

    def decor_lab(self):
        """Laboratoire, arène de la Chimère : sol dégagé autour de la cuve, deux anneaux d'or et des conduits de cristal
        vert qui relient la cuve aux grands alambics des alcôves ; le décor est contre le mur, dans des alcôves
        symétriques (alambics et postes d'alchimiste), et devant chaque bassin d'acide, une flaque de cristal vert marque où le zombie remplit son seau."""
        y = F_LAB
        p = self.p
        rng = self.rng
        top = F_LAB + 22
        # Condenseur : colonnes d'or de la cuve au plafond, bulbe de verre au cœur de cristal suspendu au centre.
        for k in (45, 135, 225, 315):
            x, z = at(8, k)
            for yy in range(y + 2, top + 1):
                if p.free(x, yy, z):
                    p.set(x, yy, z, "Rock_Gold_Brick_Pillar_Middle" if yy % 6 else TRIM)
        for x, z, d, a in ring(0, 3.6):
            for yy in range(top - 7, top + 1):
                edge = d >= 2.5 or yy in (top - 7, top)
                p.set(x, yy, z, (GOLD if yy in (top - 7, top - 3, top) else GLASS) if edge else "Rock_Crystal_Green_Block")
        p.set(0, top - 8, 0, "Nakasar_Tower_Emanation_Motes")
        # Sol : anneaux d'or, conduits de cristal de la cuve aux alambics, cercles des étagères de réactifs.
        self.inlay(self.ring_cells(11, 12), y, TRIM)
        self.inlay(self.ring_cells(20, 21), y, TRIM)
        for k, kind in LAB_ALCOVES.items():
            if kind == "alembic":
                self.inlay(self.segment(*at(9.5, k), *at(23.5, k)), y, "Rock_Crystal_Green_Block", over={n for n, _ in FLOOR} | {TRIM})
        for x, _, z in self.trap["chimera"]["fills"]:
            self.inlay([(x + dx, z + dz) for dx in range(-1, 2) for dz in range(-1, 2)], y, "Rock_Crystal_Green_Block",
                       over={n for n, _ in FLOOR} | {TRIM})
        # Alcôves : un grand alambic (verre et cristal de la couleur de son conduit) ou un poste d'alchimiste (établi
        # tourné vers la cuve, chaudron et tonneau de part et d'autre, fioles au mur).
        potions = ["Potion_Empty_Large", "Potion_Empty", "Deco_Potion", "Potion_Poison_Large", "Potion_Mana",
                   "Potion_Regen_Health_Large", "Deco_Scroll"]
        for k, kind in LAB_ALCOVES.items():
            if kind == "alembic":
                x, z = at(25.5, k)
                if not self.flask(x, y, z, "Rock_Crystal_Green_Block", height=5):
                    raise RuntimeError(f"tour : pas de place pour l'alambic de l'alcôve {k}° du laboratoire")
                continue
            x, z = at(26.5, k)
            if not self.place(x, y, z, "Bench_Alchemy", facing_center(x, z)):
                raise RuntimeError(f"tour : pas de place pour l'établi de l'alcôve {k}° du laboratoire")
            for dk, name in ((-7, "Alchemy_Cauldron"), (7, "Furniture_Ancient_Barrel")):
                cx, cz = at(26.5, k + dk)
                self.place(cx, y, cz, name)
            for dk in (-4, 4):
                cx, cz = at(27.5, k + dk)
                self.place(cx, y, cz, rng.choice(potions))
        # Fioles sur le haut des rayonnages du mur.
        for x, z, d, a in ring(28.4, R_IN):
            if p.get(x, y + 5, z) == SHELF and rng.random() < 0.5:
                self.place(x, y + 6, z, rng.choice(potions[:6] + ["Furniture_Royal_Magic_Potion_Glow", "Deco_Bone_Skulls"]))
        # Entrée de l'arène : deux braseros allumés de part et d'autre de l'arrivée de l'hélice des transmutations.
        for x, z in (at(27.5, 347), at(22, 324)):
            if not self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On"):
                raise RuntimeError(f"tour : pas de place pour le brasero de l'entrée du laboratoire en {(x, y, z)}")
        # Lustres et lanternes au plafond.
        for k in range(0, 360, 45):
            x, z = at(17, k + 22)
            self.hang(x, top, z, CHANDELIER)
        for k in range(0, 360, 20):
            x, z = at(23, k)
            self.chain(x, top, z, 4, end="Furniture_Royal_Magic_Potion_Glow_Ceiling")

    def decor_observatory(self):
        y = F_DECK
        rng = self.rng
        alch = self.trap["alchemist"]
        # L'arène de l'Alchimiste se lit au sol : cercle de transmutation d'or autour de l'athanor (anneau, triangle et
        # carré inscrits), rosace de cristal de la couleur de chaque pilier élémentaire, socle d'or et de cristal blanc
        # sous chaque fiole de soin, et dallage fissuré (pavés) sur les pans du rebord qui s'effondrent.
        circle = 14
        self.inlay(self.ring_cells(circle - 0.5, circle + 0.5), y, GOLD)
        for poly in (3, 4):
            corners = [at(circle, 90 + 360 * i / poly) for i in range(poly)]
            for (x0, z0), (x1, z1) in zip(corners, corners[1:] + corners[:1]):
                self.inlay(self.segment(x0, z0, x1, z1), y, TRIM)
        for (x, _, z), crystal in zip(alch["pillars"], ("Red", "Cyan", "Yellow", "Green")):
            self.inlay([(x + dx, z + dz) for dx in range(-1, 2) for dz in range(-1, 2)], y, f"Rock_Crystal_{crystal}_Block",
                       over={n for n, _ in FLOOR} | {TRIM, GOLD})
        for x, _, z in alch["heals"]:
            self.inlay([(x + dx, z + dz) for dx in range(-1, 2) for dz in range(-1, 2) if (dx, dz) != (0, 0)], y, GOLD,
                       over={n for n, _ in FLOOR} | {TRIM})
            self.inlay([(x, z)], y, "Rock_Crystal_White_Block", over={n for n, _ in FLOOR} | {TRIM, GOLD})
        for cells in alch["collapse"]:
            for x, yy, z in cells:
                if yy == y - 1:
                    self.p.set(x, yy, z, CRACKED)
        # Entrée de l'arène : deux braseros allumés de part et d'autre de la porte de l'antichambre.
        self.gate_braziers(y, 19.5, 245, 9)
        # Le centre est l'arène de l'Alchimiste, autour de son athanor : le décor reste au pourtour.
        for k in (20, 160, 300):
            self.telescope(k, 38)
        # Massifs de fleurs lumineuses entre les arcs, braseros le long du parapet, cristaux sur socles d'or.
        flowers = ["Plant_Flower_Tall_Cyan", "Plant_Flower_Orchid_Purple", "Plant_Crop_Mushroom_Glowing_Blue",
                   "Plant_Crop_Mushroom_Glowing_Purple", "Plant_Grass_Lush"]
        for k in (0, 45, 135, 170, 300, 330):
            cx, cz = at(31, k)
            bed = [(cx + dx, cz + dz) for dx in range(-2, 3) for dz in range(-1, 2)]
            if any((bx, y + kk, bz) in self.keep_clear or not self.p.free(bx, y, bz) for bx, bz in bed for kk in range(2)):
                continue
            for bx, bz in bed:
                edge = abs(bx - cx) == 2 or abs(bz - cz) == 1
                self.p.set(bx, y, bz, TRIM if edge else "Soil_Grass_Full")
                if not edge:
                    self.p.set(bx, y + 1, bz, rng.choice(flowers))
                self.walk.get((bx, bz), set()).discard(2 * y)
        for k in range(0, 360, 12):
            if in_arc(k, 195, 280) or in_arc(k, 70, 110):
                continue
            x, z = at(43, k)
            self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On")
        for k, crystal in ((25, "Rock_Crystal_Purple_Large"), (115, "Rock_Crystal_Blue_Large"),
                           (155, "Rock_Crystal_Pink_Large"), (290, "Rock_Crystal_Green_Large")):
            x, z = at(36, k)
            if self.place(x, y, z, "Rock_Gold_Brick_Ornate"):
                self.place(x, y + 1, z, crystal)
        # Lanternes sur l'anneau d'or, pots de fleurs le long du parapet.
        for k in range(0, 360, 20):
            if in_arc(k, 195, 280) or in_arc(k, 60, 120):
                continue
            x, z = at(22, k)
            self.place(x, y, z, LANTERN)
        for x, z, d, a in ring(DECK_R - 1.5, DECK_R):
            if int(a) % 16 == 0 and not in_arc(a, 195, 280):
                self.place(x, y, z, "Furniture_Royal_Magic_Pot")

    def decor_antechamber(self):
        y = F_DECK
        top = F_DECK + 9
        for k in range(204, 274, 10):
            if abs(k - 245) < 12:
                continue  # rien devant la porte de la terrasse
            x, z = at(25.5, k)
            self.place(x, y, z, "*Furniture_Temple_Light_Brazier_State_Definitions_On")
        # Deux gardiens de pierre encadrent la porte de l'arène, tournés vers qui arrive par l'antichambre.
        for k in (233, 257):
            x, z = at(27.5, k)
            if not self.place(x, y, z, "Furniture_Temple_Wind_Statue", facing_to(x, z, *at(34, 245))):
                raise RuntimeError(f"tour : pas de place pour la statue de l'antichambre en {(x, y, z)}")
        for k in (215, 235, 255):
            x, z = at(40, k)
            self.hang(x, top, z, "Furniture_Temple_Wind_Chandelier")
        for k in range(205, 272, 8):
            x, z = at(43, k)
            self.place(x, y, z, "Furniture_Temple_Wind_Pot")

    def decor_study(self):
        y = F_DECK
        rng = self.rng
        # Le piédestal de la pierre (étape du butin) reste dégagé.
        self.keep_clear.update((x, y + k, z) for x in range(-1, 2) for z in range(31, 34) for k in range(4))
        # Bibliothèque du fond, de part et d'autre du portail de fin.
        for x in range(-8, 9):
            if abs(x) <= 2:
                continue
            for k in range(0, 4):
                self.place(x, y + k, 41, SHELF, pf.NORTH)
            if rng.random() < 0.6:
                self.place(x, y + 4, 41, rng.choice(["Deco_Bone_Skulls", "Potion_Signature_Greater", "Deco_Book_Pile_Small",
                                                     "Furniture_Royal_Magic_Potion_Glow", "Deco_Treasure_Pile_Small"]))
        # Bureau garni, tapis, curiosités.
        for x, top in ((6, "Deco_Scroll"), (7, "Furniture_Temple_Wind_Candle")):
            self.place(x, y + 1, 30, top)
        self.place(6, y, 29, "Furniture_Royal_Magic_Chair", pf.SOUTH)
        for x in (-6, -4, 2, 4):
            for z in (34, 36):
                self.place(x, y, z, "Furniture_Royal_Magic_Carpet")
        self.place(-7, y, 40, "Furniture_Temple_Emerald_Statue", pf.EAST)
        self.place(7, y, 40, "Furniture_Temple_Emerald_Statue", pf.WEST)
        self.place(-7, y, 27, "Deco_Treasure_Pile_Large")
        self.place(7, y, 37, "Alchemy_Cauldron")
        self.place(-7, y, 33, "Furniture_Temple_Wind_Pot")
        self.place(-6, y, 37, "Deco_Bone_Skulls")
        self.hang(0, y + 9, 35, "Furniture_Temple_Wind_Chandelier")

    def secrets(self):
        """Coffres secrets : une niche de deux blocs de haut creusée dans le mur extérieur de la tour (jamais jusqu'à la salle
        de derrière), le coffre au fond, des lianes qui pendent devant. `self.secret_chests` donne les coffres."""
        p = self.p
        self.secret_chests = []
        for a, floor in SECRETS:
            # Étage : celui donné, ou le palier (marche pleine, pas une demi-marche) de l'Escalier des vents le plus
            # proche de cet angle.
            if floor is None:
                landing = None
                for da in sorted(range(-30, 31), key=abs):
                    step = self.wind_ramp.get(at(R_OUT + 0.6, a + da))
                    if step is not None and step % 2 == 0:
                        landing = (a + da, step // 2)
                        break
                if landing is None:
                    raise RuntimeError(f"tour : pas de palier de l'Escalier des vents vers {a}°")
                a, floor = landing
            mouth = at(R_OUT + 0.6, a)
            # La niche s'enfonce droit vers l'intérieur, selon l'axe le plus proche de la direction du centre.
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            step = (-round(math.copysign(1, ca)), 0) if abs(ca) >= abs(sa) else (0, -round(math.copysign(1, sa)))
            deep = []
            x, z = mouth
            while len(deep) < 2:
                x, z = x + step[0], z + step[1]
                if math.hypot(x, z) < R_OUT:
                    deep.append((x, z))
            if not p.free(mouth[0], floor, mouth[1]) or self.free_below(mouth[0], floor, mouth[1]):
                raise RuntimeError(f"tour : pas de sol libre devant la niche secrète à {a}°")
            self.keep_clear.update((mouth[0], floor + k, mouth[1]) for k in range(3))
            for x, z in deep:
                if math.hypot(x, z) < R_IN + 1.5:
                    raise RuntimeError(f"tour : la niche secrète à {a}° perce le mur")
                for k in range(2):
                    p.set(x, floor + k, z, AIR)
                    self.keep_clear.add((x, floor + k, z))
                p.set(x, floor - 1, z, GOLD)
                p.set(x, floor + 2, z, TRIM)
            cx, cz = deep[-1]
            p.chest(cx, floor, cz, SECRET_CHEST, facing_to(cx, cz, *mouth), SECRET_LOOT)
            for x, z in deep[:-1]:
                p.set(x, floor + 1, z, "Plant_Vine_Hanging")
            self.secret_chests.append((cx, floor, cz))

    def free_below(self, x, y, z):
        return self.p.free(x, y - 1, z)

    def lore(self):
        """Notes de lore (TOWER_NOTES) : sur la case libre au sol la plus proche de leur point, posée sur un bloc plein,
        hors des cases gardées libres et des cases des pièges, sceaux et barrières (`self.trap`)."""
        p = self.p
        reserved = set(self.keep_clear)

        def cells(value):
            if isinstance(value, dict):
                for v in value.values():
                    yield from cells(v)
            elif isinstance(value, (list, tuple, set)):
                if len(value) == 3 and all(isinstance(v, int) for v in value):
                    yield tuple(value)
                else:
                    for v in value:
                        yield from cells(v)

        reserved.update(cells(self.trap))
        self.notes = {}
        for name, (kind, u, y, v) in TOWER_NOTES:
            x0, z0 = (u, v) if kind == "xz" else at(u, v)
            spot = None
            for radius in range(0, 7):
                ring_cells = sorted(((x0 + dx, z0 + dz) for dx in range(-radius, radius + 1) for dz in range(-radius, radius + 1)
                                     if max(abs(dx), abs(dz)) == radius), key=lambda c: (abs(c[0] - x0) + abs(c[1] - z0), c))
                for x, z in ring_cells:
                    below = p.get(x, y - 1, z) or ""
                    if ((x, y, z) in reserved or not p.free(x, y, z) or not pf.NOTE_FLOOR.match(below)
                            or pf.NOT_FLOOR.search(below)):
                        continue
                    spot = (x, y, z)
                    break
                if spot:
                    break
            if spot is None:
                raise RuntimeError(f"tour : pas de place pour la note {name}")
            p.set(*spot, f"Nakasar_Lore_{name}", self.rng.randint(0, 3))
            self.notes[name] = spot

    def decorate(self):
        self.decor_hall()
        self.decor_leaks()
        self.decor_greenhouse()
        self.decor_library()
        self.decor_transmutation()
        self.decor_lab()
        self.decor_observatory()
        self.decor_antechamber()
        self.decor_study()

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
        # Points de contrôle : bibliothèque, Escalier des vents, antichambre (pas dans la Salle des Transmutations, Kevin,
        # 19 octobre 2026). Comme Deepworks, chaque statue est hors de l'arène de son boss : palier de la rampe de la
        # serre devant la porte de la bibliothèque.
        self.checkpoint(*at3(36.5, F_LIBRARY, 47), statue_at=at(40, 48))
        self.checkpoint(*at3(37, F_LAB, 272), statue_at=at(39, 262))
        self.checkpoint(*at3(33, F_DECK, 255), statue_at=at(37, 265))
        self.traps()
        self.codex()
        self.chimera()
        self.alchemist()
        self.arenas()
        self.secrets()
        self.decorate()
        self.lore()
        self.mobs()
        self.secure()
        self.barriers()
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


    # --- murs invisibles ---------------------------------------------------------------------------

    def ground_solid(self, x, y, z):
        """Plein, en comptant l'île sous le prefab (y < 0 hors des blocs posés)."""
        return self.solid(x, y, z) or (y < 0 and self.p.get(x, y, z) is None)

    def barrier_needs(self):
        """Piles au bord du vide extérieur trop basses pour un joueur à côté : {(x, haut actuel, z): haut voulu}.

        Pour chaque surface atteignable, une colonne voisine pleine à hauteur des pieds (parapet, verrière, lanterne...)
        doit l'être jusqu'à 4 blocs au-dessus de la surface si, à 2 cases au plus, une colonne hors de la tour (d >=
        R_OUT) n'a rien de plein de 6 blocs sous les pieds à 3 au-dessus : le vide. Les trémies intérieures n'en ont pas
        besoin."""
        _, seen = walkable_path(self.p, START, {})
        levels = {}
        for x, s, z in seen:
            levels.setdefault((x, z), set()).add(s)
        void = {}

        def is_void(x, z, fy):
            key = (x, z, fy)
            if key not in void:
                void[key] = polar(x, z)[0] >= R_OUT and not any(self.ground_solid(x, yy, z)
                                                               for yy in range(fy - 6, fy + 4))
            return void[key]

        need = {}
        for x, s, z in seen:
            fy = (s + 1) // 2           # premier bloc d'air au-dessus de la surface
            want = fy + 3               # dernier bloc plein voulu : 4 blocs au-dessus de la surface
            for dx, dz in DIRS8:
                nx, nz = x + dx, z + dz
                # voisin au même niveau, marche plus haute de la même rampe, ou trou : pas un mur
                if any(-2 <= o - s <= 16 for o in levels.get((nx, nz), ())) or not self.ground_solid(nx, fy, nz):
                    continue
                if not any(is_void(nx + ex, nz + ez, fy) for ex in range(-2, 3) for ez in range(-2, 3)):
                    continue
                top = fy
                while self.ground_solid(nx, top + 1, nz) or (nx, top + 1, nz) in self.p.claims:
                    top += 1
                if top < want:
                    need[(nx, top, nz)] = max(want, need.get((nx, top, nz), want))
        return need

    def barriers(self):
        """Murs invisibles (bloc vanilla Barrier : plein, sans rendu) au-dessus des parapets qui bordent le vide, pour
        qu'on ne puisse sauter par-dessus ni des coursives, ni des rampes extérieures, ni de la terrasse."""
        for _ in range(3):
            need = self.barrier_needs()
            if not need:
                return
            for (x, top, z), want in need.items():
                for y in range(top + 1, want + 1):
                    if (x, y, z) in self.keep_clear or not self.p.free(x, y, z):
                        break
                    self.p.set(x, y, z, BARRIER)
        need = self.barrier_needs()
        if need:
            raise RuntimeError(f"tour : murs invisibles trop bas au bord du vide {sorted(need.items())[:8]}")
        _, seen = walkable_path(self.p, START, {})
        perched = [(x, s, z) for x, s, z in seen if self.p.get(x, (s - 1) // 2, z) == BARRIER]
        if perched:
            raise RuntimeError(f"tour : on peut marcher sur des murs invisibles {perched[:8]}")


# Mobs (alchemist_tower.Tower.mobs, rôles de tools/generate_tower_mobs.py) : (rôle sans le préfixe Nakasar_,
# (rayon, niveau, angle), hauteur libre demandée). La case exacte est la plus proche libre au même niveau.
SPAWNER_PREFIX = "Nakasar_Spawner_"
MOB_LAYOUT = [
    # Hall des Alambics : deux groupes d'homoncules, deux golems de plomb, une fiole de poison.
    ("Homunculus", (12, F_HALL, 40), 2), ("Homunculus", (13, F_HALL, 52), 2), ("Homunculus", (11, F_HALL, 64), 2),
    ("Homunculus", (14, F_HALL, 150), 2), ("Homunculus", (15, F_HALL, 162), 2),
    ("Lead_Golem", (16, F_HALL, 345), 4), ("Lead_Golem", (17, F_HALL, 210), 4),
    ("Living_Flask_Poison", (9, F_HALL, 265), 2),
    # Couloir des fuites (pièges) : deux fioles seulement.
    ("Living_Flask_Poison", (25, F_LEAKS, 120), 2), ("Living_Flask_Fire", (25, F_LEAKS, 30), 2),
    # Serre suspendue : plantes carnivores (vrilles et Snapdragons) sous la verrière, élémentaires de racine.
    ("Snapdragon", (41, F_LEAKS, 205), 2), ("Carnivorous_Vine", (40, F_LEAKS, 222), 3),
    ("Snapdragon", (42, F_LEAKS, 240), 2), ("Carnivorous_Vine", (40, F_LEAKS, 258), 3),
    ("Snapdragon", (41, F_LEAKS, 276), 2),
    ("Elemental_Root", (40, F_LEAKS, 300), 3), ("Elemental_Root", (40, F_LEAKS, 330), 3),
    # Bibliothèque : apprentis et homoncules.
    ("Alchemist_Apprentice", (14, F_LIBRARY, 150), 2), ("Alchemist_Apprentice", (14, F_LIBRARY, 300), 2),
    ("Homunculus", (10, F_LIBRARY, 220), 2), ("Homunculus", (11, F_LIBRARY, 235), 2),
    ("Elemental_Frost", (16, F_LIBRARY, 20), 3),
    # Laboratoire : l'arène de la Chimère, sans autre mob.
]
MOB_FIXED = []
GARGOYLE_ANGLES = (320, 40, 130, 220)


# Salles à atteindre depuis le parvis (x, niveau, z), en plus des points de contrôle.
GOALS = {"hall": (0, F_HALL, 16), "leaks_exit": (-31, F_LEAKS, 0), "balcony_north": (0, F_LEAKS, -40),
         "library": (0, F_LIBRARY, 12), "transmutation": (0, F_TRANS, 0), "lab": (10, F_LAB, 10),
         "deck": (0, F_DECK, -10), "study": (0, F_DECK, 34)}


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
    # Chaque énigme ferme bien son passage : sceaux et ronces fermés, on ne va pas plus loin que la salle.
    cps = tower.checkpoints
    for name, start, goal in (("portail de la cour", START, GOALS["hall"]),
                              ("sceau du hall", (0, 2 * F_HALL, 16), GOALS["leaks_exit"]),
                              ("ronces de la bibliothèque", (cps[0][0], 2 * cps[0][1], cps[0][2]), GOALS["transmutation"]),
                              ("sceau des transmutations", (0, 2 * F_TRANS, 4), GOALS["lab"])):
        missing, _ = walkable_path(prefab, start, {"goal": goal}, gates_open=False)
        if not missing:
            raise RuntimeError(f"tour : le {name} ne ferme pas le passage")
    # Le sceau du Codex seul (ronces brûlées) ferme le haut de la rampe ; les éboulis de toutes les étagères effondrées
    # ne ferment ni la rampe ni le centre de l'arène.
    codex = tower.trap["codex"]
    library = (cps[0][0], 2 * cps[0][1], cps[0][2])
    missing, _ = walkable_path(prefab, library, {"goal": GOALS["transmutation"]}, solid_cells=codex["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau du Codex ne ferme pas la rampe de la bibliothèque")
    rubble = [c for cells in codex["rubble"] for c in cells]
    missing, _ = walkable_path(prefab, library, {"transmutation": GOALS["transmutation"], "arena": (0, F_LIBRARY, 3),
                                                 "vault": at3(37, F_LIBRARY, 320)}, solid_cells=rubble)
    if missing:
        raise RuntimeError(f"tour : les éboulis du Codex ferment le passage : {missing}")
    # Le sceau de la Chimère seul ferme la porte nord du laboratoire (vers l'Escalier des vents).
    missing, _ = walkable_path(prefab, (10, 2 * F_LAB, 10), {"goal": cps[1]}, solid_cells=tower.trap["chimera"]["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau de la Chimère ne ferme pas la porte nord du laboratoire")
    # Le sceau de l'Alchimiste seul ferme la porte du bureau depuis la terrasse.
    deck = GOALS["deck"]
    missing, _ = walkable_path(prefab, (deck[0], 2 * deck[1], deck[2]), {"goal": GOALS["study"]},
                               solid_cells=tower.trap["alchemist"]["seal"])
    if not missing:
        raise RuntimeError("tour : le sceau de l'Alchimiste ne ferme pas la porte du bureau")
    # Chaque barrière d'arène ferme l'entrée : depuis sa statue, on n'entre plus dans l'arène.
    arenas = tower.trap["arenas"]
    for name, start, goal in (("Codex", cps[0], (0, F_LIBRARY, 3)), ("Chimera", (0, F_TRANS, 8), GOALS["lab"]),
                              ("Alchemist", cps[2], GOALS["deck"])):
        missing, _ = walkable_path(prefab, (start[0], 2 * start[1], start[2]), {"goal": goal}, solid_cells=arenas[name])
        if not missing:
            raise RuntimeError(f"tour : la barrière de l'arène {name} ne ferme pas son entrée")
    return tower


def at3(r, y, a):
    x, z = at(r, a)
    return x, y, z


# --- vérification du parcours --------------------------------------------------------------------

PASSABLE_PREFIXES = ("Nakasar_Spawner_", "VFX_", "Plant_Grass", "Plant_Flower", "Plant_Crop_Mushroom_Glowing", "Nakasar_Tower_Emanation", "Deco_Potion",
                     "Deco_Scroll", "Plant_Moss_Rug", "Plant_Vine", "Furniture_Royal_Magic_Carpet",
                     "Nakasar_Lore_")


def passable(name):
    return name in (None, AIR) or name.startswith(PASSABLE_PREFIXES)


def walkable_path(prefab, start, goals, ground_y=0, bounds=(-70, 70, -70, 82), gates_open=True, solid_cells=()):
    """Parcours en largeur sur les surfaces du prefab (demi-blocs) : un joueur de 2 blocs de haut monte d'un demi-bloc
    en marchant, d'un bloc en sautant, et peut descendre de 4 blocs. Hors du prefab, sous ground_y c'est l'île (plein),
    au-dessus de l'air. Sceaux et ronces (GATE_BLOCKS) sont ouverts si gates_open, comme une fois les énigmes
    résolues ; `solid_cells` sont pleins quoi qu'il y ait (un sceau seul, des éboulis posés en jeu). Renvoie les buts
    non atteints."""
    blocks = prefab.blocks
    claims = prefab.claims
    solid_cells = set(solid_cells)

    def cell(x, y, z):
        if (x, y, z) in solid_cells:
            return "solid"
        if (x, y, z) in claims:
            return "air" if passable(blocks[claims[(x, y, z)]][0]) else "solid"
        b = blocks.get((x, y, z))
        if b is None:
            return "solid" if y < ground_y else "air"
        name = b[0]
        if name in GATE_BLOCKS:
            return "air" if gates_open else "solid"
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
