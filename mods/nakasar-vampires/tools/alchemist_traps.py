#!/usr/bin/env python3
"""Pièges et énigmes de la Tour de l'Alchimiste (étape 4 du donjon), sur le modèle de Deepworks.

    python3 mods/nakasar-vampires/tools/alchemist_traps.py [--preview DOSSIER]

écrit les trois blocs des énigmes (sceau alchimique, haie de ronces, levier de vanne). Les volumes déclencheurs, eux,
sont écrits par generate_alchemist_tower.py (`trap_volumes`) dans resources/TriggerVolumeData.json de l'instance, avec
les barrières de repoussée et les points de contrôle ; tools/alchemist_tower.py pose les blocs dans la tour et garde
leurs positions (`Tower.trap`).

Tout passe par les volumes du jeu, comme dans The_Deepworks (lu dans Assets.zip 0.7.2) :
- les énigmes : un brasero éteint (`Furniture_Temple_Dark_Brazier`, état Off) ou un levier qu'on utilise déclenche
  l'événement BLOCK_USED de son volume (comme les braseros de la salle des araignées et le levier du générateur) ; le
  volume marque d'une étiquette le volume du passage, qui dissout son sceau (ReplaceBlockType dans sa forme) quand toutes
  ses étiquettes sont là (comme la porte des déchets, alimentée par deux tuyaux) ;
- les pièges : un volume « contrôleur » qui couvre la salle envoie des signaux à intervalle régulier tant qu'un joueur
  s'y trouve ; chaque zone de piège reçoit le sien, s'annonce (particules, son), puis frappe un court instant (comme les
  quadrants de Deepworks : étiquettes Busy et Dmg). Les livres de la bibliothèque et la foudre de l'Escalier des vents ne
  frappent qu'une fois sur trois ou quatre (RandomChanceCondition, comme les tas de nourriture du Feastmaster).

Les pièges :
- Hall des Alambics : rallumer les trois athanors dissout le sceau du Couloir des fuites ;
- Couloir des fuites : 21 bouches de vapeur toxique, par groupes de trois qui jettent en alternance (A puis B) ; des
  niches dans le mur extérieur abritent entre deux groupes. Au fond, derrière la porte ouest, le levier coupe la vanne
  (les jets cessent) et ouvre le barrage en raccourci vers la rampe du hall ;
- Serre suspendue : nappes de spores qui ralentissent qui s'y attarde ;
- Bibliothèque : brûler la haie de ronces au brasero ouvre la rampe ; des livres tombent sur des zones annoncées ;
- Salle des Transmutations : les quadrants se transmutent à tour de rôle (feu, glace, acide, foudre), les croix d'or du
  sol restent sûres ; allumer le foyer d'un quadrant l'apaise mais en fait sortir un élémentaire ; les quatre foyers
  allumés dissolvent le sceau de l'escalier du laboratoire ;
- Laboratoire (combat de la Chimère, tower.ChimeraSystem) : la cuve crache de l'acide sur des cercles annoncés ; le
  sceau de la porte nord se dissout à la mort de la Chimère ;
- Escalier des vents (s'éveille quand on franchit la porte nord du laboratoire) : flammes alchimiques qui balaient les
  marches, rafales qui plaquent contre le mur de la tour (jamais vers le vide), foudre sur des cercles annoncés.

Aucun piège ne repousse vers le vide. Les volumes ne visent que les joueurs.
"""
import json
import math
import random
import sys
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

import alchemist_tower as at
import tower_warnings as tw
import generate_assets as gx

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
LANG = "nakasar_alchemist"
ITEMS = SERVER / "Item" / "Items" / "Alchemist" / "Nakasar"
TEXTURES = COMMON / "BlockTextures" / "Nakasar" / "Alchemist"
ICONS = COMMON / "Icons" / "Items" / "Nakasar" / "Alchemist"
BRAZIER = "Furniture_Temple_Dark_Brazier"

# Ids du jeu employés par les volumes, tous vus dans Assets.zip 0.7.2 (la plupart dans les volumes de The_Deepworks) :
# un id inconnu ferait rejeter le volume en jeu, `check_ids` refuse tout ce qui n'est pas ici.
PARTICLES = {
    "Goblin_Decorative_Steam", "Dungeon_Goblin_Smoke_Pipe_Large", "Effect_Poison", "Magic_Sparks_Heavy_GS",
    "Fire_Green", "Dungeon_Goblin_Mace_Slam_Warning", "Block_Break_Dust", "Smoke_Floor", "Dungeon_Goblin_Spores_Green",
    "Fire_Trap_Preview", "Fire_AoE", "Weapon_Frost_Mist", "Ice_Blast", "Dungeon_Goblin_Toxic_Water", "Impact_Poison",
    "Goblin_Decorative_Sparks", "Lightning", "Dungeon_Goblin_Electric_Fence_Hit", "Fire_Charge_Charging1",
    "Leaves_Oak_Wind", "Wind", "Goblin_Decorative_Lightning", "Ability_Ice_Explosion", "Effect_Health_Pack",
    "Totem_Heal_AttachOnStatue", "Dungeon_Goblin_Energy_Barrier_Red_Large", "Dungeon_Goblin_Energy_Barrier_Reveal",
    "Dungeon_Goblin_Smoke_Pipe_Large",
}
SOUNDS = {
    "SFX_Emit_Goblin_Steam_A", "SFX_Env_Geyzer_Burst", "SFX_Lever_Metal_On", "SFX_Emit_Goblin_Pipes_Activate",
    "SFX_Crystal_Break", "SFX_Flame_Ignite", "SFX_Effect_Burn_World", "SFX_Drop_Weapons_Books",
    "SFX_Emit_Goblin_Steam_B", "SFX_Emit_Goblin_Pipes_Flame_Ignite", "SFX_Staff_Flame_Flamethrower",
    "SFX_Emit_Goblin_Flame_Quadrant_Blast", "SFX_Ice_Break", "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts",
    "SFX_Emit_Goblin_Electric_Fence_Zap", "SFX_Emit_Wind_Gusts", "SFX_Emit_Dungeon_Goblin_Void_Thunder",
    "SFX_Dungeon_Checkpoint_Activate", "SFX_Gobliterator_Arena_Door_Warning",
}
EFFECTS = {"Poison_T1", "Poison_T2", "Burn", "Slow", "Hazard_Electric_Stun", "Health_Pack"}
BLOCKS = {"Empty", "Fluid_Fire", at.SEAL, at.HEDGE, at.RUBBLE, at.DOOR, "Rock_Marble_Brick", "Rock_Marble_Brick_Smooth",
          "Rock_Marble_Cobble", at.ARENA_BARRIER, at.SPORE_SHROOM, at.CONDUIT_LIT, *map(at.lit_block, at.HALL_COLOURS), at.EMANATION_LIT, at.EMANATION_FED, at.PIPE_GLOW, at.LEAK}
NPCS = {"Nakasar_Elemental_Fire", "Nakasar_Elemental_Frost", "Nakasar_Elemental_Root", "Nakasar_Elemental_Thunder"}

# Quadrants de la Salle des Transmutations : (signe de x, signe de z), élémentaire du foyer, particules d'annonce et de
# frappe, son, effets pendant la frappe.
QUADRANTS = {
    "Fire": ((1, -1), "Nakasar_Elemental_Fire", "Fire_Trap_Preview", "Fire_AoE", "SFX_Emit_Goblin_Flame_Quadrant_Blast",
             [("Burn", 4.0, 0.0)], 6.0),
    "Ice": ((-1, -1), "Nakasar_Elemental_Frost", "Weapon_Frost_Mist", "Ice_Blast", "SFX_Ice_Break",
            [("Slow", 3.0, 0.0)], 4.0),
    "Acid": ((1, 1), "Nakasar_Elemental_Root", "Dungeon_Goblin_Spores_Green", "Dungeon_Goblin_Toxic_Water",
             "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts", [("Poison_T2", 5.0, 0.0)], 5.0),
    "Lightning": ((-1, 1), "Nakasar_Elemental_Thunder", "Goblin_Decorative_Sparks", "Lightning",
                  "SFX_Emit_Goblin_Electric_Fence_Zap", [("Hazard_Electric_Stun", 0.8, 1.2)], 6.0),
}
QUADRANT_ORDER = ("Fire", "Ice", "Acid", "Lightning")
ZERO = {"X": 0.0, "Y": 0.0, "Z": 0.0}
# Jets de gaz du couloir : annonce (zone rouge qui se remplit, comme toutes les annonces de la tour : tower_warnings.py),
# durée du gaz, cadence (le mur intérieur souffle, puis le mur extérieur une demi-période plus tard).
GAS_WARN = 1.8
GAS_ACTIVE = 1.4
GAS_PERIOD = 6.0
# Champignons de la serre : annonce (il enfle), nuage, cadence de chaque moitié, rayon du nuage.
SPORE_WARN = 2.0
SPORE_CLOUD_S = 3.0
SPORE_PERIOD = 7.0
SPORE_R = 3.0
# Barrière d'une arène : elle se lève ces secondes après que le groupe est entré (Deepworks : 4 s).
ARENA_CLOSE_DELAY = 4.0
ARENAS = ("Codex", "Chimera", "Alchemist")


# --- volumes : briques reprises des volumes de The_Deepworks --------------------------------------------------------

def vid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nakasar/alchemist-tower/trap/{name}"))


def vec(x, y, z):
    return {"X": float(x), "Y": float(y), "Z": float(z)}


def box(hx, hy, hz):
    return {"Type": "Box", "Min": vec(-hx, -hy, -hz), "Max": vec(hx, hy, hz)}


def cylinder(radius, height):
    """Cylindre posé sur la position du volume (sa base), haut de `height`."""
    return {"Type": "Cylinder", "Center": dict(ZERO), "Radius": float(radius), "Height": float(height)}


def effect(kind, event, delay=0.0, entry=None, interval=0.0, **fields):
    e = {"Type": kind, "Event": event, "Interval": float(interval), "Delay": round(float(delay), 2)}
    if entry is not None:
        e["Entry"] = entry
    e.update(fields)
    return e


def vfx(event, system, delay=0.0, entry=None, offset=(0, 0, 0), scale=1.0, duration=0.0, anchor="Volume"):
    return effect("PlayVfx", event, delay, entry, ParticleSystem=system, Offset=vec(*offset), Anchor=anchor,
                  Scale=float(scale), Rotation=dict(ZERO), Duration=float(duration))


def mark(radius, seconds, event="", offset=(0, 0.1, 0), delay=0.0):
    """Zone rouge d'annonce au sol (tools/tower_warnings.py) : son disque se remplit en `seconds` secondes, jusqu'au
    coup ; `radius` en blocs."""
    return vfx(event, tw.system(seconds), delay, offset=offset, scale=tw.scale(radius))


def sound(event, name, delay=0.0, entry=None, location="VolumeCenter"):
    return effect("PlaySound", event, delay, entry, SoundEvent=name, Location=location, Offset=dict(ZERO))


def tags(event, key, value, delay=0.0, entry=None, match="", match_value="", radius=1.0, operation="Set"):
    return effect("ModifyTags", event, delay, entry, Operation=operation, TagKey=key, TagValue=value, MatchKey=match,
                  MatchValue=match_value, Radius=float(radius), Center="Volume")


def signal(event, key, match, match_value="", delay=0.0, radius=60.0, interval=0.0):
    return effect("SendSignal", event, delay, interval=interval, MatchKey=match, MatchValue=match_value,
                  Radius=float(radius), Center="Volume", SignalKeys=[key])


def toggle(kind, event, match, match_value="", delay=0.0, entry=None, radius=60.0):
    """EnableVolume ou DisableVolume des volumes qui portent l'étiquette `match` (de valeur match_value si donnée)."""
    return effect(kind, event, delay, entry, MatchKey=match, MatchValue=match_value, Radius=float(radius),
                  Center="Volume")


def damage(percent, interval):
    return effect("DamageEntity", "TICK", interval=interval, Mode="PercentMax", Amount=float(percent))


def status(name, duration, event="TICK", delay=0.0, interval=0.0):
    return effect("EntityEffect", event, delay, interval=interval, Effect=name, Mode="Apply", Duration=float(duration))


def velocity(vx, vy, vz):
    return effect("SetVelocity", "TICK", Velocity=vec(vx, vy, vz), Additive=False, RelativeMode="Absolute")


def place(event, block, pos, delay=0.0, entry=None, state=""):
    return effect("PlaceBlock", event, delay, entry, BlockType=block, BlockState=state, Position=vec(*pos),
                  Origin="WorldAbsolute", ReplaceMode="Always", Rotation="None", Pitch="None", Roll="None")


def replace(event, sources, target, delay=0.0, entry=None, from_state="", to_state=""):
    """Remplace, dans la forme du volume, les blocs `sources` par `target` (forme par défaut : celle du volume)."""
    return effect("ReplaceBlockType", event, delay, entry, FromBlockTypes=list(sources), FromBlockState=from_state,
                  ToBlockType=target, ToBlockState=to_state, Offset=dict(ZERO), Origin="VolumeOrigin", Rotation="None",
                  Pitch="None", Roll="None")


def title(event, name, delay=0.0, entry=None):
    return effect("ShowEventTitle", event, delay, entry, PrimaryTitle=f"{LANG}.trap.{name}.title",
                  SecondaryTitle=f"{LANG}.trap.{name}.subtitle", Style="Major", Duration=3.0, FadeInDuration=0.5,
                  FadeOutDuration=1.0, Recipient="AllPlayers")


def spawn(event, npc, offset, delay=0.0, entry=None):
    return effect("SpawnNpc", event, delay, entry, NpcType=npc, GroupType="", Origin="VolumeOrigin",
                  Offset=vec(*offset), Count=1, Yaw=0.0)


def tag_is(event, key, value, inverted=False, entry=None, source="Self"):
    c = {"Type": "TagCondition", "Event": event}
    if entry is not None:
        c["Entry"] = entry
    c.update({"Source": source, "TagKey": key, "Comparison": "Exactly", "CompareAgainst": "Value", "TagValue": value,
              "Inverted": inverted, "MatchKey": "", "MatchValue": "", "Radius": 50.0, "Center": "Volume"})
    return c


def chance(event, p, entry=None):
    c = {"Type": "RandomChanceCondition", "Event": event}
    if entry is not None:
        c["Entry"] = entry
    c["Chance"] = float(p)
    return c


def cooldown(event, seconds):
    return {"Type": "CooldownCondition", "Event": event, "Cooldown": float(seconds), "Scope": "WHOLE_VOLUME"}


def volume(name, group, position, shape, effects, conditions=(), volume_tags=None, enabled=True, **extra):
    v = {"Position": vec(*position), "Shape": shape}
    if conditions:
        v["Conditions"] = list(conditions)
    v["Effects"] = list(effects)
    v.update(extra)
    v.update({"TargetTypes": ["Player"], "Enabled": enabled, "GroupId": group, "KeepLoaded": False})
    if volume_tags:
        v["Tags"] = dict(volume_tags)
    v["Name"] = name
    return v


class Traps:
    """Volumes des pièges, en coordonnées du monde (`origin` : position du repère de la tour)."""

    def __init__(self, tower, origin):
        self.t = tower.trap
        self.origin = origin
        self.volumes = {}
        self.groups = {}

    def world(self, x, y, z):
        ox, oy, oz = self.origin
        return x + ox, y + oy, z + oz

    def group(self, name, color):
        gid = vid(f"group/{name}")
        self.groups[gid] = {"Origin": vec(*self.world(0, 0, 0)), "TargetTypes": ["Player"], "Enabled": True,
                            "Color": color, "Name": name}
        return gid

    def add(self, name, *args, **kwargs):
        if vid(name) in self.volumes:
            raise RuntimeError(f"pièges : volume en double {name}")
        self.volumes[vid(name)] = volume(name, *args, **kwargs)

    def block_center(self, x, y, z):
        wx, wy, wz = self.world(x, y, z)
        return wx + 0.5, wy + 0.5, wz + 0.5

    def bounds(self, cells):
        """Boîte qui couvre exactement les blocs `cells` (pour un ReplaceBlockType dans la forme du volume)."""
        xs, ys, zs = zip(*cells)
        lo, hi = self.world(min(xs), min(ys), min(zs)), self.world(max(xs) + 1, max(ys) + 1, max(zs) + 1)
        center = tuple((a + b) / 2 for a, b in zip(lo, hi))
        return center, box(*((b - a) / 2 - 0.05 for a, b in zip(lo, hi)))

    def foot(self, x, y, z):
        """Base d'un cylindre posé sur le sol de la case (x, z), y = première couche d'air."""
        wx, wy, wz = self.world(x, y, z)
        return wx + 0.5, wy, wz + 0.5

    def controller(self, name, group, position, shape, sends, interval, enabled=True, radius=80.0):
        """Tant qu'un joueur s'y trouve, envoie toutes les `interval` secondes les signaux `sends` :
        [(signal, étiquette des cibles, valeur, délai)]."""
        self.add(name, group, position, shape,
                 [signal("TICK", key, match, value, delay, radius, interval) for key, match, value, delay in sends],
                 volume_tags={name: "On"}, enabled=enabled, ConditionTiming="BeforeVolumeDelay",
                 CancelDelayedOnExit=False, Cooldown=0.1)

    def pulse(self, name, group, position, shape, key, match, match_value, warn, active, warn_fx, hit_fx, hits,
              odds=None):
        """Zone de piège : au signal `key`, s'annonce (warn_fx), frappe `active` secondes après `warn` (hit_fx, puis
        `hits` sur les joueurs présents à chaque tick), sans se relancer avant d'avoir fini (étiquette Busy)."""
        conditions = [tag_is("SIGNAL_RECEIVED", key, "", entry=1, source="Event"),
                      tag_is("SIGNAL_RECEIVED", "Busy", "On", inverted=True, entry=1),
                      tag_is("TICK", "Dmg", "True")]
        if odds is not None:
            conditions.append(chance("SIGNAL_RECEIVED", odds, entry=1))
        effects = [tags("SIGNAL_RECEIVED", "Busy", "On", entry=1)]
        effects += [dict(e, Event="SIGNAL_RECEIVED", Entry=1) for e in warn_fx]
        effects += [dict(e, Event="SIGNAL_RECEIVED", Entry=1, Delay=round(e["Delay"] + warn, 2)) for e in hit_fx]
        effects += [tags("SIGNAL_RECEIVED", "Dmg", "True", warn, entry=1),
                    tags("SIGNAL_RECEIVED", "Dmg", "False", warn + active, entry=1),
                    tags("SIGNAL_RECEIVED", "Busy", "Off", warn + active, entry=1)]
        effects += hits
        self.add(name, group, position, shape, effects, conditions,
                 volume_tags={match: match_value, "Busy": "Off", "Dmg": "False"}, ConditionTiming="BeforeVolumeDelay",
                 Cooldown=0.1)

    def usable(self, name, group, pos, used_effects, flag="Lit"):
        """Volume d'un bloc qu'on utilise (brasero, levier) : ses effets ne jouent qu'une fois."""
        center = self.block_center(*pos)
        self.add(name, group, center, box(0.5, 0.5, 0.5),
                 [tags("BLOCK_USED", flag, "Yes", 0.1)] + used_effects,
                 [tag_is("BLOCK_USED", flag, "No")], volume_tags={flag: "No"}, ConditionTiming="BeforeVolumeDelay")

    def gate(self, name, group, cells, keys, opened, block=at.SEAL, delay=0.0, sfx="SFX_Crystal_Break"):
        """Passage fermé par `block` : s'ouvre (`delay` secondes plus tard) quand toutes les étiquettes `keys` valent On."""
        center, shape = self.bounds(cells)
        conditions = [tag_is("TAG_ADDED", k, "On") for k in keys] + [tag_is("TAG_ADDED", name, "Closed")]
        effects = [tags("TAG_ADDED", name, "Open"),
                   sound("TAG_ADDED", sfx, delay + 0.6),
                   replace("TAG_ADDED", [block], "Empty", delay + 0.8)] + opened
        self.add(name, group, center, shape, effects, conditions,
                 volume_tags={name: "Closed", **{k: "Off" for k in keys}})

    def arena_gate(self, name, group, cells, fight=()):
        """Barrière d'arène, comme les portes du Festin de Deepworks. Le Java (tower.ArenaGate) pose Gate=Close quand
        un joueur vivant est entré dans l'arène : l'annonce rouge clignote dans la porte, puis la barrière se lève
        ARENA_CLOSE_DELAY secondes plus tard. Gate=Open quand le groupe a péri (ou est sorti) ou que le boss est vaincu :
        elle s'abaisse. Les blocs sont posés par pans (ReplaceBlockType agit sur toute la boîte d'un volume)."""
        piece = f"{name}_Barrier"
        center, shape = self.bounds(cells)
        self.add(f"{name}_Gate", group, center, shape, [
            vfx("TAG_ADDED", "Dungeon_Goblin_Energy_Barrier_Red_Large", duration=ARENA_CLOSE_DELAY),
            sound("TAG_ADDED", "SFX_Gobliterator_Arena_Door_Warning"),
            signal("TAG_ADDED", "Close", piece, delay=ARENA_CLOSE_DELAY),
            vfx("TAG_ADDED", "Dungeon_Goblin_Energy_Barrier_Reveal", ARENA_CLOSE_DELAY),
            sound("TAG_ADDED", "SFX_Crystal_Break", ARENA_CLOSE_DELAY),
            dict(signal("TAG_ADDED", "Open", piece), Entry=1),
            sound("TAG_ADDED", "SFX_Crystal_Break", entry=1),
            # Pièges de l'arène (`fight`) : actifs seulement pendant le combat, barrière levée.
            *[toggle("EnableVolume", "TAG_ADDED", v, delay=ARENA_CLOSE_DELAY, radius=80) for v in fight],
            *[toggle("DisableVolume", "TAG_ADDED", v, entry=1, radius=80) for v in fight]],
            [tag_is("TAG_ADDED", "Gate", "Close"), tag_is("TAG_ADDED", "Gate", "Open", entry=1)],
            volume_tags={"Gate": "Open"}, ConditionTiming="BeforeVolumeDelay")
        for j, pile in enumerate(piles(cells)):
            pc, ps = self.bounds(pile)
            self.add(f"{piece}_{j}", group, pc, ps, [
                replace("SIGNAL_RECEIVED", ["Empty"], at.ARENA_BARRIER),
                replace("SIGNAL_RECEIVED", [at.ARENA_BARRIER], "Empty", entry=1)],
                [tag_is("SIGNAL_RECEIVED", "Close", "", source="Event"),
                 tag_is("SIGNAL_RECEIVED", "Open", "", entry=1, source="Event")],
                volume_tags={piece: "Piece"}, ConditionTiming="BeforeVolumeDelay")

    def arenas(self):
        g = self.group("Tower_Arenas", 12597547)
        fight = {"Codex": ("Library_Books_Controller",)}
        for name in ARENAS:
            self.arena_gate(name, g, self.t["arenas"][name], fight.get(name, ()))

    # --- les pièges ----------------------------------------------------------------------------------------------

    def court(self):
        """Portes de la tour : tower.CourtGuardSystem pose Guardians=On quand les gardiens d'airain sont tous abattus."""
        g = self.group("Tower_Court_Guardians", 13148746)
        self.gate("Court_Door", g, self.t["court_door"], ["Guardians"],
                  [title("TAG_ADDED", "court", 0.4), vfx("TAG_ADDED", "Block_Break_Dust", 0.8, scale=3.0),
                   sound("TAG_ADDED", "SFX_Emit_Goblin_Pipes_Activate")],
                  block=at.DOOR, delay=0.4, sfx="SFX_Lever_Metal_On")

    def light(self, cells, block, delay, step, event="BLOCK_USED"):
        """Allume une suite de blocs l'un après l'autre (PlaceBlock), à partir de `delay`, un bloc toutes les `step` s."""
        return [place(event, block, self.world(*c), delay + i * step) for i, c in enumerate(cells)]

    def hall(self):
        """Les trois athanors : chacun allumé fait courir sa couleur dans son tuyau suspendu jusqu'à l'alambic, remplit son
        tube, allume sa gemme sur la colonne relais puis sur le sceau du Couloir des fuites, qui vibre. Les trois ensemble
        allument le tuyau maître et la colonne relais jusqu'au sceau, puis le sceau se dissout."""
        g = self.group("Tower_Hall_Athanors", 16737843)
        parts = self.t["hall"]
        seal = self.t["hall_seal"]
        sockets = self.t["hall_seal_sockets"]
        seal_center, _ = self.bounds(seal + sockets)
        keys = []
        for i, (pos, colour) in enumerate(zip(self.t["athanors"], at.HALL_COLOURS), 1):
            keys.append(f"Athanor_{i}")
            x, y, z = pos
            lit = at.lit_block(colour)
            pipe = parts["conduits"][i - 1]  # de la cheminée à l'alambic
            tube = sorted(parts["tubes"][i - 1], key=lambda c: c[1])
            fx = [sound("BLOCK_USED", "SFX_Flame_Ignite"),
                  vfx("BLOCK_USED", "Magic_Sparks_Heavy_GS", offset=(0, 0.5, 0)),
                  place("BLOCK_USED", at.EMANATION_LIT, self.world(x, y + 2, z), 0.3)]
            fx += self.light(pipe, lit, 0.5, 0.12)
            t = 0.5 + 0.12 * len(pipe)
            fx += self.light(tube, lit, t, 0.1)
            t += 0.1 * len(tube)
            fx += [place("BLOCK_USED", lit, self.world(*parts["relay_sockets"][i - 1]), t),
                   place("BLOCK_USED", lit, self.world(*sockets[i - 1]), t + 0.3),
                   sound("BLOCK_USED", "SFX_Emit_Goblin_Pipes_Activate", 0.4),
                   tags("BLOCK_USED", f"Athanor_{i}", "On", t + 0.3, match="Hall_Seal", radius=80)]
            self.usable(f"Hall_Athanor_{i}", g, pos, fx)
        # Le sceau vibre à chaque gemme allumée.
        self.add("Hall_Seal_Pulse", g, seal_center, box(1, 1, 1), [
            vfx("TAG_ADDED", "Magic_Sparks_Heavy_GS", scale=2.0),
            vfx("TAG_ADDED", "Goblin_Decorative_Lightning", 0.2, scale=1.5),
            sound("TAG_ADDED", "SFX_Emit_Dungeon_Goblin_Void_Thunder")],
            volume_tags={"Hall_Seal": "Pulse", **{k: "Off" for k in keys}})
        main = parts["main"]  # de l'alambic à la colonne
        relay = sorted(parts["relay"], key=lambda c: c[1])
        opened = self.light(main, at.CONDUIT_LIT, 0.2, 0.08, "TAG_ADDED")
        opened += self.light(relay, at.CONDUIT_LIT, 0.2 + 0.08 * len(main), 0.08, "TAG_ADDED")
        rise = 0.2 + 0.08 * (len(main) + len(relay))
        top = self.world(0, at.ALEMBIC_TOP + 4, 0)
        opened += [place("TAG_ADDED", at.EMANATION_FED, top, 0.2),
                   sound("TAG_ADDED", "SFX_Emit_Goblin_Pipes_Activate", 0.2),
                   replace("TAG_ADDED", [at.lit_block(c) for c in at.HALL_COLOURS], "Empty", rise + 0.8),
                   title("TAG_ADDED", "hall", rise)]
        self.gate("Hall_Seal", g, seal + sockets, keys, opened, delay=rise)

    def leaks(self):
        """Buses de gaz : tant qu'un joueur est dans le couloir, celles du mur intérieur (A) puis celles du mur extérieur
        (B) soufflent toutes les GAS_PERIOD / 2 secondes. Chaque buse siffle et fume, son cône (trois cercles qui
        grandissent depuis la buse) se remplit de rouge GAS_WARN secondes, puis le gaz le remplit GAS_ACTIVE secondes.
        Pendant qu'un mur souffle, l'autre côté du couloir et les espaces entre deux cônes sont sûrs."""
        g = self.group("Tower_Leaks_Steam", 7864183)
        y = at.F_LEAKS
        self.controller("Leaks_Controller", g, self.world(0, y, 0), cylinder(at.R_IN, at.F_LIBRARY - at.F_LEAKS - 1),
                        [("Steam", "Leaks_Pair", "A", 0.0), ("Steam", "Leaks_Pair", "B", GAS_PERIOD / 2)],
                        interval=GAS_PERIOD)
        for n in self.t["nozzles"]:
            (x, _, z), (ux, uz) = n["cell"], n["dir"]
            for j, (dist, rad) in enumerate(at.GAS_CONE):
                cx, cz = x + 0.5 + ux * dist, z + 0.5 + uz * dist
                base = (cx + self.origin[0], y + self.origin[1], cz + self.origin[2])
                warn = [mark(rad, GAS_WARN)]
                hit = [vfx("", gas_cloud(rad), offset=(0, 0.1, 0), duration=GAS_ACTIVE)]
                if j == 0:  # la buse elle-même : sifflement et fumée pendant l'annonce, jet et poison au coup
                    mouth = (-ux * (dist - 0.5), 1.5, -uz * (dist - 0.5))
                    warn += [vfx("", "Goblin_Decorative_Steam", offset=mouth, duration=GAS_WARN),
                             sound("", "SFX_Emit_Goblin_Steam_A")]
                    hit += [vfx("", "Dungeon_Goblin_Smoke_Pipe_Large", offset=mouth, duration=GAS_ACTIVE),
                            vfx("", "Effect_Poison", offset=(0, 1, 0), duration=GAS_ACTIVE),
                            sound("", "SFX_Env_Geyzer_Burst")]
                self.pulse(f"Leaks_Gas_{n['angle']:03d}_{j}", g, base, cylinder(rad, 3), "Steam", "Leaks_Pair",
                           n["group"], warn=GAS_WARN, active=GAS_ACTIVE, warn_fx=warn, hit_fx=hit,
                           hits=[status("Poison_T1", 6.0), damage(5, 0.8)])
        lever = self.t["lever"]
        self.usable("Leaks_Valve", g, lever, [
            sound("BLOCK_USED", "SFX_Lever_Metal_On"),
            sound("BLOCK_USED", "SFX_Emit_Goblin_Pipes_Activate", 0.4),
            toggle("DisableVolume", "BLOCK_USED", "Leaks_Controller", delay=0.5, radius=80),
            tags("BLOCK_USED", "Valve", "On", 0.5, match="Leaks_Shortcut", radius=80),
            tags("BLOCK_USED", "Valve", "On", 0.5, match="Leaks_Pipes", radius=80)], flag="Pulled")
        # Les tuyaux luisants (vanne et buses) s'éteignent et les fuites se tarissent quand la vanne est fermée.
        pipes = self.t["valve_pipes"] + self.t["valve_leaks"] + [c for n in self.t["nozzles"] for c in n["pipe"]]
        center, shape = self.bounds(pipes)
        self.add("Leaks_Pipes", g, center, shape, [
            replace("TAG_ADDED", [at.PIPE_GLOW], at.PIPE_GLOW, 0.2, to_state="Off"),
            replace("TAG_ADDED", [at.LEAK], "Empty", 0.4)],
            [tag_is("TAG_ADDED", "Valve", "On")], volume_tags={"Leaks_Pipes": "Open", "Valve": "Off"})
        self.gate("Leaks_Shortcut", g, self.t["shortcut_seal"], ["Valve"], [title("TAG_ADDED", "valve")])

    def greenhouse(self):
        """Champignons de la serre : tant qu'un joueur est dans la serre, ils lâchent leurs spores à tour de rôle (A puis
        B, toutes les SPORE_PERIOD secondes). Chacun s'annonce : il enfle (état Swelling, animation du bloc) et sa zone
        rouge se remplit SPORE_WARN secondes, puis il crache un vrai nuage (Nakasar_Spore_Cloud) qui reste SPORE_CLOUD_S
        secondes : qui est dedans est ralenti et empoisonné."""
        g = self.group("Tower_Greenhouse_Spores", 6280509)
        cells = [(x, at.F_LEAKS, z) for x, z, d, a in at.ring(at.R_OUT, at.BALCONY_R) if at.in_arc(a, *at.GREENHOUSE_ARC)]
        center, _ = self.bounds(cells)
        _, shape = self.bounds([(x, y + k, z) for x, y, z in cells for k in (0, 4)])
        self.controller("Greenhouse_Controller", g, center, shape,
                        [("Spores", "Greenhouse_Spores", "A", 0.0), ("Spores", "Greenhouse_Spores", "B", SPORE_PERIOD / 2)],
                        interval=SPORE_PERIOD)
        for i, pos in enumerate(self.t["spores"]):
            here = self.world(*pos)
            self.pulse(f"Greenhouse_Spores_{i + 1}", g, self.foot(*pos), cylinder(SPORE_R, 3), "Spores",
                       "Greenhouse_Spores", "AB"[i % 2], warn=SPORE_WARN, active=SPORE_CLOUD_S,
                       warn_fx=[place("", at.SPORE_SHROOM, here, state="Swelling"), mark(SPORE_R, SPORE_WARN),
                                sound("", "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts")],
                       hit_fx=[vfx("", gas_cloud(SPORE_R, "Spore"), offset=(0, 0.1, 0), duration=SPORE_CLOUD_S),
                               sound("", "SFX_Env_Geyzer_Burst"), sound("", "SFX_Emit_Goblin_Steam_B", 0.2),
                               place("", at.SPORE_SHROOM, here, SHROOM_PUFF_END - SPORE_WARN)],
                       hits=[status("Slow", 2.0, interval=1.0), status("Poison_T1", 3.0, interval=1.0)])

    def library(self):
        g = self.group("Tower_Library", 11817792)
        hedge = self.t["hedge"]
        self.usable("Library_Brazier", g, self.t["hedge_brazier"], [
            sound("BLOCK_USED", "SFX_Flame_Ignite"),
            tags("BLOCK_USED", "Fire", "On", 0.5, match="Library_Brambles", radius=60)])
        center, shape = self.bounds(hedge)
        # Comme les toiles de la salle des araignées : la haie flambe (Fluid_Fire), puis il n'en reste rien.
        self.add("Library_Brambles", g, center, shape, [
            tags("TAG_ADDED", "Library_Brambles", "Burnt"),
            sound("TAG_ADDED", "SFX_Effect_Burn_World", 0.3),
            replace("TAG_ADDED", [at.HEDGE], "Fluid_Fire", 0.5),
            replace("TAG_ADDED", ["Fluid_Fire"], "Empty", 3.5),
            replace("TAG_ADDED", [at.HEDGE], "Empty", 3.6),
            title("TAG_ADDED", "brambles", 3.6)],
            [tag_is("TAG_ADDED", "Fire", "On"), tag_is("TAG_ADDED", "Library_Brambles", "Intact")],
            volume_tags={"Library_Brambles": "Intact", "Fire": "Off"})
        y = at.F_LIBRARY
        # Livres qui tombent des rayonnages : seulement pendant le combat du Codex (la barrière de l'arène active ce
        # volume quand elle se lève et le coupe quand elle s'abaisse, `arena_gate`).
        self.controller("Library_Books_Controller", g, self.world(0, y, 0), cylinder(at.R_IN, 13),
                        [("Books", "Library_Books", "", 0.0)], interval=3.0, enabled=False)
        for i, pos in enumerate(self.t["books"]):
            self.pulse(f"Library_Books_{i + 1}", g, self.foot(*pos), cylinder(1.6, 3), "Books", "Library_Books",
                       "Zone", warn=2.0, active=0.4,
                       warn_fx=[mark(1.6, 2.0)],
                       hit_fx=[vfx("", "Block_Break_Dust", offset=(0, 1.5, 0)), vfx("", "Smoke_Floor"),
                               sound("", "SFX_Drop_Weapons_Books")],
                       hits=[damage(12, 1.0), status("Slow", 2.0)], odds=0.3)

    def transmutation(self):
        g = self.group("Tower_Transmutation", 13421619)
        y = at.F_TRANS
        side = at.SQUARE
        height = at.F_LAB - at.F_TRANS - 1
        self.controller("Transmutation_Controller", g, self.world(0.5, y + height / 2, 0.5),
                        box(side + 0.5, height / 2, side + 0.5),
                        [("Transmute", "Quadrant", el, 4.0 * i) for i, el in enumerate(QUADRANT_ORDER)], interval=16.0)
        keys = []
        for el in QUADRANT_ORDER:
            (sx, sz), npc, warn_p, hit_p, snd, statuses, pct = QUADRANTS[el]
            # Le quadrant, de la croix d'or (x ou z = 0, toujours sûre) au mur, sur 3 blocs de haut.
            x0, x1 = (1, side) if sx > 0 else (-side, -1)
            z0, z1 = (1, side) if sz > 0 else (-side, -1)
            cells = [(x0, y, z0), (x1, y + 2, z1)]
            center, shape = self.bounds(cells)
            spots = [(sx * a - (center[0] - self.origin[0]) + 0.5, 0.2, sz * b - (center[2] - self.origin[2]) + 0.5)
                     for a in (5, 13) for b in (5, 13)]
            spots = [(dx, -1.4, dz) for dx, _, dz in spots]  # le centre de la boîte est 1,5 bloc au-dessus du sol
            self.pulse(f"Quadrant_{el}", g, center, shape, "Transmute", "Quadrant", el, warn=2.5, active=2.4,
                       warn_fx=[vfx("", warn_p, offset=o, duration=2.5) for o in spots]
                       + [mark(4.6, 2.5, offset=(dx, -1.4, dz)) for dx, _, dz in spots],
                       hit_fx=[vfx("", hit_p, offset=o, duration=2.4) for o in spots] + [sound("", snd)],
                       hits=[status(n, d, interval=i) for n, d, i in statuses] + [damage(pct, 0.5)])
            # Le foyer du quadrant : l'allumer apaise le quadrant, mais un élémentaire sort des dalles.
            keys.append(f"Foyer_{el}")
            self.usable(f"Transmutation_Foyer_{el}", g, self.t["foyers"][el], [
                sound("BLOCK_USED", "SFX_Flame_Ignite"),
                vfx("BLOCK_USED", "Magic_Sparks_Heavy_GS", offset=(0, 0.5, 0)),
                toggle("DisableVolume", "BLOCK_USED", "Quadrant", el, delay=0.5),
                spawn("BLOCK_USED", npc, (sx * -3, 0, sz * -3), delay=1.5),
                vfx("BLOCK_USED", hit_p, delay=1.2, offset=(sx * -3, 0, sz * -3)),
                tags("BLOCK_USED", f"Foyer_{el}", "On", 0.5, match="Transmutation_Seal", radius=60)])
        self.gate("Transmutation_Seal", g, self.t["trans_seal"], keys,
                  [title("TAG_ADDED", "transmutation"),
                   toggle("DisableVolume", "TAG_ADDED", "Transmutation_Controller", delay=0.5)])

    def wind_stair(self):
        g = self.group("Tower_Wind_Stair", 10079487)
        y = at.F_LAB
        self.controller("Wind_Controller", g, self.world(0, y, 0), cylinder(at.BALCONY_R - 1, at.F_DECK - at.F_LAB + 2),
                        [("Flame", "Wind_Flame", "A", 0.0), ("Gust", "Wind_Gust", "A", 1.0),
                         ("Strike", "Wind_Strike", "", 2.0), ("Flame", "Wind_Flame", "B", 3.0),
                         ("Gust", "Wind_Gust", "B", 4.0), ("Strike", "Wind_Strike", "", 5.0)],
                        interval=6.0, enabled=False, radius=100.0)
        # Le contrôleur s'éveille quand on franchit la porte nord du laboratoire.
        door = [(x, y, z) for x in range(-2, 3) for z in range(-35, -27)] + [(0, y + 4, -31)]
        center, shape = self.bounds(door)
        self.add("Wind_Activation", g, center, shape,
                 [toggle("EnableVolume", "ENTER", "Wind_Controller", radius=100)])
        for a, pair, cells, nozzle in self.t["flames"]:
            noz = self.block_center(*nozzle)
            for j, cell in enumerate(cells):
                base = self.foot(*cell)
                off = tuple(n - b for n, b in zip(noz, base))
                warn = [vfx("", "Fire_Trap_Preview", offset=(0, 0.1, 0), duration=2.0), mark(2.0, 2.0)]
                hit = [vfx("", "Fire_AoE", offset=(0, 0.2, 0), duration=1.6)]
                if j == 0:
                    warn.append(vfx("", "Fire_Charge_Charging1", offset=off, duration=2.0))
                    hit.append(sound("", "SFX_Emit_Goblin_Pipes_Flame_Ignite"))
                self.pulse(f"Wind_Flame_{a}_{j}", g, base, cylinder(2.0, 3), "Flame", "Wind_Flame", pair, warn=2.0,
                           active=1.6, warn_fx=warn, hit_fx=hit, hits=[status("Burn", 3.0), damage(12, 1.0)])
        for a, pair, cells in self.t["gusts"]:
            for j, cell in enumerate(cells):
                base = self.foot(*cell)
                # vers l'axe de la tour, donc contre son mur : jamais vers le vide
                d = math.hypot(base[0] - self.origin[0], base[2] - self.origin[2])
                push = (-(base[0] - self.origin[0]) / d * 7.0, 0.0, -(base[2] - self.origin[2]) / d * 7.0)
                warn = [vfx("", "Leaves_Oak_Wind", offset=(0, 1, 0), duration=1.8), mark(2.6, 1.8)]
                hit = [vfx("", "Wind", offset=(0, 1, 0), duration=1.8)]
                if j == 2:
                    hit.append(sound("", "SFX_Emit_Wind_Gusts"))
                self.pulse(f"Wind_Gust_{a}_{j}", g, base, cylinder(2.6, 3), "Gust", "Wind_Gust", pair, warn=1.8,
                           active=1.8, warn_fx=warn, hit_fx=hit, hits=[velocity(*push)])
        for i, cell in enumerate(self.t["strikes"]):
            self.pulse(f"Wind_Strike_{i + 1}", g, self.foot(*cell), cylinder(1.8, 3), "Strike", "Wind_Strike", "Zone",
                       warn=2.0, active=0.5,
                       warn_fx=[mark(1.8, 2.0)],
                       hit_fx=[vfx("", "Lightning"), vfx("", "Goblin_Decorative_Lightning", offset=(0, 1, 0)),
                               sound("", "SFX_Emit_Dungeon_Goblin_Void_Thunder")],
                       hits=[status("Hazard_Electric_Stun", 1.0, interval=1.0), damage(15, 1.0)], odds=0.3)

    def codex(self):
        """Combat du Codex vivant (étape 5). Le Java (tower.CodexSystem) pose une étiquette sur ces volumes, ids dans
        TowerLayout.java (`codex_ids`) :
        - Codex_Seal, Codex=On à la mort du Codex : le sceau du haut de la rampe se dissout ;
        - Codex_Fire / Codex_Frost_<pupitre> / Codex_Rain, Cast=On quand un chapitre n'a pas été interrompu : cercle de
          feu autour du centre, onde de givre autour du pupitre, pluie de livres sur des cercles au hasard, toujours
          annoncés (zones rouges) ;
        - Codex_Collapse_<pan>, Collapse=On en dernière phase (sous 40 % de vie) : un pan d'étagères s'annonce puis s'effondre en éboulis
          (Nakasar_Codex_Rubble) qui réduisent l'arène ;
        - Codex_Arena, Reset=On quand le groupe a fui ou péri : les éboulis disparaissent et les pans se relèvent."""
        g = self.group("Tower_Codex", 9055202)
        c = self.t["codex"]
        cx, y, cz = c["center"]
        self.gate("Codex_Seal", g, c["seal"], ["Codex"], [title("TAG_ADDED", "codex")])

        def spell(name, foot, radius, warn_fx, hit_fx, hits, warn=2.5, active=0.8):
            self.add(name, g, foot, cylinder(radius, 5), [
                sound("TAG_ADDED", "SFX_Crystal_Break"),
                mark(radius, warn, "TAG_ADDED"),
                *[dict(e, Event="TAG_ADDED") for e in warn_fx],
                *[dict(e, Event="TAG_ADDED", Delay=round(e["Delay"] + warn, 2)) for e in hit_fx],
                tags("TAG_ADDED", "Dmg", "True", warn), tags("TAG_ADDED", "Dmg", "False", warn + active),
                tags("TAG_ADDED", "Cast", "Off", warn + active + 0.5),
                *hits],
                [tag_is("TAG_ADDED", "Cast", "On"), tag_is("TICK", "Dmg", "True")],
                volume_tags={"Cast": "Off", "Dmg": "False"}, ConditionTiming="BeforeVolumeDelay")

        def around(radii, count, system, dy=0.3, **kw):
            return [vfx("", system, offset=(r * math.cos(2 * math.pi * k / count + r), dy, r * math.sin(2 * math.pi * k / count + r)), **kw)
                    for r in radii for k in range(count)]

        # Cercle de feu : tout le centre de la rotonde brûle, on s'en sort en gagnant le pourtour.
        spell("Codex_Fire", self.foot(cx, y, cz), 10, around((3, 6.5, 9), 6, "Fire_Trap_Preview", duration=2.5),
              around((0, 4, 8), 5, "Fire_AoE") + [sound("", "SFX_Emit_Goblin_Flame_Quadrant_Blast")],
              [damage(18, 1.0), status("Burn", 4.0)])
        # Onde de givre : autour du pupitre du chapitre, on s'en sort en passant de l'autre côté de la salle.
        for k, pos in enumerate(c["lecterns"]):
            spell(f"Codex_Frost_{k}", self.foot(*pos), 11, around((4, 8), 5, "Weapon_Frost_Mist", duration=2.5),
                  around((0, 5, 9), 4, "Ice_Blast") + [vfx("", "Ability_Ice_Explosion", offset=(0, 0.5, 0)),
                                                         sound("", "SFX_Ice_Break")],
                  [damage(12, 1.0), status("Slow", 4.0)])
        # Pluie de livres : à son signal, environ la moitié des cercles de la rotonde reçoivent des livres.
        self.add("Codex_Rain", g, self.foot(cx, y, cz), cylinder(at.R_IN, 6), [
            sound("TAG_ADDED", "SFX_Drop_Weapons_Books"),
            signal("TAG_ADDED", "Rain", "Codex_Rain", "Zone", radius=60.0),
            tags("TAG_ADDED", "Cast", "Off", 3.0)],
            [tag_is("TAG_ADDED", "Cast", "On")], volume_tags={"Cast": "Off"})
        n = 0
        for r, count in ((4, 3), (8.5, 6), (13, 9), (17.5, 12), (21.5, 14)):
            for k in range(count):
                a = 360 * k / count + 17 * r
                x, z = cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))
                wx, wy, wz = self.world(x, y, z)
                n += 1
                self.pulse(f"Codex_Rain_{n}", g, (wx + 0.5, wy, wz + 0.5), cylinder(1.8, 3), "Rain", "Codex_Rain", "Zone",
                           warn=2.0, active=0.5,
                           warn_fx=[mark(1.9, 2.0)],
                           hit_fx=[vfx("", "Block_Break_Dust", offset=(0, 1.5, 0)), vfx("", "Smoke_Floor"),
                                   sound("", "SFX_Drop_Weapons_Books")],
                           hits=[damage(14, 1.0), status("Slow", 2.0)], odds=0.5)
        # Pans d'étagères : le pan s'annonce (zones rouges le long du mur), puis ses éboulis tombent par blocs.
        for i, cells in enumerate(c["rubble"]):
            center, shape = self.bounds(cells)
            a0, a1 = at.COLLAPSE_ARCS[i]
            span = (a1 - a0) % 360
            marks = []
            for k in range(4):
                a = math.radians(a0 + span * (k + 0.5) / 4)
                mx, mz = 24.5 * math.cos(a), 24.5 * math.sin(a)
                wx, wy, wz = self.world(mx, y, mz)
                offset = (wx + 0.5 - center[0], wy + 0.1 - center[1], wz + 0.5 - center[2])
                marks += [mark(2.9, 2.5, "TAG_ADDED", offset=offset),
                          vfx("TAG_ADDED", "Block_Break_Dust", offset=(offset[0], offset[1] + 4, offset[2]))]
            self.add(f"Codex_Collapse_{i}", g, center, shape, [
                sound("TAG_ADDED", "SFX_Drop_Weapons_Books"), *marks,
                signal("TAG_ADDED", "Collapse", "Codex_Pile", str(i), radius=60.0)],
                [tag_is("TAG_ADDED", "Collapse", "On")], volume_tags={"Codex_Sector": str(i), "Collapse": "Off"})
            for j, pile in enumerate(piles(cells)):
                pc, ps = self.bounds(pile)
                self.pulse(f"Codex_Pile_{i}_{j}", g, pc, ps, "Collapse", "Codex_Pile", str(i), warn=2.5, active=0.6,
                           warn_fx=[], hit_fx=[replace("", ["Empty"], at.RUBBLE), vfx("", "Block_Break_Dust")],
                           hits=[damage(20, 1.0), status("Slow", 3.0)])
        # Remise à zéro de l'arène : éboulis retirés, pans prêts à retomber.
        lo, hi = -int(at.R_IN), int(at.R_IN)
        center, shape = self.bounds([(cx + lo, y, cz + lo), (cx + hi, y + 1, cz + hi)])
        self.add("Codex_Arena", g, center, shape, [
            replace("TAG_ADDED", [at.RUBBLE], "Empty"),
            tags("TAG_ADDED", "Collapse", "Off", 0.2, match="Codex_Sector", radius=60),
            tags("TAG_ADDED", "Reset", "Off", 1.0)],
            [tag_is("TAG_ADDED", "Reset", "On")], volume_tags={"Reset": "Off"})

    def chimera(self):
        """Combat de la Chimère du laboratoire (étape 6). Le Java (tower.ChimeraSystem) pose une étiquette sur ces
        volumes, ids dans TowerLayout.java (`chimera_ids`) :
        - Chimera_Seal, Chimera=On à la mort de la Chimère : le sceau de la porte nord se dissout ;
        - Chimera_Acid, Cast=On à intervalles pendant le combat (plus souvent quand elle se régénère dans la cuve) :
          la cuve crache de l'acide sur environ un tiers des cercles du laboratoire, chacun annoncé au sol."""
        g = self.group("Tower_Chimera", 4569930)
        c = self.t["chimera"]
        cx, y, cz = c["vat"]
        self.gate("Chimera_Seal", g, c["seal"], ["Chimera"], [title("TAG_ADDED", "chimera")])
        self.add("Chimera_Acid", g, self.foot(cx, y, cz), cylinder(at.R_IN, 8), [
            sound("TAG_ADDED", "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts"),
            vfx("TAG_ADDED", "Dungeon_Goblin_Toxic_Water", offset=(0, 0.5, 0), scale=2.0),
            signal("TAG_ADDED", "Acid", "Chimera_Acid", "Zone", radius=60.0),
            tags("TAG_ADDED", "Cast", "Off", 3.0)],
            [tag_is("TAG_ADDED", "Cast", "On")], volume_tags={"Cast": "Off"})
        n = 0
        for r, count in ((12, 8), (16.5, 11), (21, 14), (25.5, 17)):
            for k in range(count):
                a = 360 * k / count + 23 * r
                x, z = cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a))
                wx, wy, wz = self.world(x, y, z)
                n += 1
                self.pulse(f"Chimera_Acid_{n}", g, (wx + 0.5, wy, wz + 0.5), cylinder(1.8, 3), "Acid", "Chimera_Acid",
                           "Zone", warn=2.2, active=0.6,
                           warn_fx=[mark(1.9, 2.2),
                                    vfx("", "Dungeon_Goblin_Spores_Green", offset=(0, 0.2, 0))],
                           hit_fx=[vfx("", "Impact_Poison", offset=(0, 0.5, 0)), vfx("", "Effect_Poison"),
                                   sound("", "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts")],
                           hits=[damage(10, 1.0), status("Poison_T1", 4.0)], odds=0.35)

    def alchemist(self):
        """Combat de l'Alchimiste sur la terrasse de l'Observatoire (étape 7). Le Java (tower.AlchemistSystem) pose
        une étiquette sur ces volumes et lit celle du levier, ids dans TowerLayout.java (`alchemist_ids`) :
        - Alchemist_Seal, Alchemist=On à sa mort : le sceau de la porte du bureau se dissout ;
        - Alchemist_Lever : le levier de l'antichambre (BLOCK_USED) met Hard=On tant que le combat n'a pas commencé
          (Locked, posé par le Java à l'engagement) ; le Java le lit pour le mode difficile ;
        - Alchemist_Collapse_<pan>, Collapse=On au Grand Œuvre : le pan du rebord s'annonce puis ses blocs
          (Alchemist_Pile_*) tombent dans le vide ;
        - Alchemist_Heal_<k>, Pack=On : une fiole de soin (comme Health_Pack_Volume de Deepworks) attend 25 s qu'un
          joueur la ramasse ;
        - Alchemist_Phase_2 / _3, Cast=On : titre de la phase ;
        - Alchemist_Arena, Reset=On (groupe parti ou mort, ou Alchimiste vaincu) : le rebord se reconstruit, les
          fioles s'éteignent."""
        g = self.group("Tower_Alchemist", 7091352)
        c = self.t["alchemist"]
        cx, y, cz = c["center"]
        self.gate("Alchemist_Seal", g, c["seal"], ["Alchemist"], [title("TAG_ADDED", "alchemist")])
        # Levier du mode difficile : une seule fois, et seulement avant le combat.
        self.add("Alchemist_Lever", g, self.block_center(*c["lever"]), box(0.5, 0.5, 0.5), [
            tags("BLOCK_USED", "Hard", "On", 0.1),
            sound("BLOCK_USED", "SFX_Lever_Metal_On"),
            sound("BLOCK_USED", "SFX_Emit_Dungeon_Goblin_Void_Thunder", 0.5),
            vfx("BLOCK_USED", "Goblin_Decorative_Lightning", 0.4, offset=(0, 1, 0)),
            title("BLOCK_USED", "alchemist_hard", 0.6)],
            [tag_is("BLOCK_USED", "Hard", "On", inverted=True), tag_is("BLOCK_USED", "Locked", "On", inverted=True)],
            volume_tags={"Hard": "Off", "Locked": "Off"}, ConditionTiming="BeforeVolumeDelay")
        # Pans du rebord : annoncés par des zones rouges, puis les blocs tombent ; la remise à zéro les repose.
        sources = sorted({n for n, _ in at.FLOOR} | {n for n, _ in at.WALL})
        for i, cells in enumerate(c["collapse"]):
            center, shape = self.bounds(cells)
            a0, a1 = at.DECK_COLLAPSE_ARCS[i]
            span = (a1 - a0) % 360
            marks = []
            for r in (36, 40):
                for k in range(max(2, span // 9)):
                    a = math.radians(a0 + span * (k + 0.5) / max(2, span // 9))
                    wx, wy, wz = self.world(cx + r * math.cos(a), y, cz + r * math.sin(a))
                    offset = (wx + 0.5 - center[0], wy + 0.1 - center[1], wz + 0.5 - center[2])
                    marks += [mark(2.9, 2.5, "TAG_ADDED", offset=offset),
                              vfx("TAG_ADDED", "Block_Break_Dust", 2.5, offset=offset)]
            self.add(f"Alchemist_Collapse_{i}", g, center, shape, [
                sound("TAG_ADDED", "SFX_Crystal_Break"), sound("TAG_ADDED", "SFX_Crystal_Break", 2.4), *marks,
                signal("TAG_ADDED", "Collapse", "Alchemist_Pile", str(i), radius=70.0),
                tags("TAG_ADDED", "Collapse", "Off", 3.0)],
                [tag_is("TAG_ADDED", "Collapse", "On")], volume_tags={"Collapse": "Off"})
            for layer, restore in ((y - 1, at.CRACKED), (y - 2, "Rock_Marble_Brick")):
                for j, pile in enumerate(piles([cell for cell in cells if cell[1] == layer])):
                    pc, ps = self.bounds(pile)
                    self.add(f"Alchemist_Pile_{i}_{y - layer}_{j}", g, pc, ps, [
                        replace("SIGNAL_RECEIVED", sources, "Empty", 2.5),
                        replace("SIGNAL_RECEIVED", ["Empty"], restore, entry=1)],
                        [tag_is("SIGNAL_RECEIVED", "Collapse", "", source="Event"),
                         tag_is("SIGNAL_RECEIVED", "Restore", "", entry=1, source="Event")],
                        volume_tags={"Alchemist_Pile": str(i)}, ConditionTiming="BeforeVolumeDelay")
        # Fioles de soin : allumées par le Java, ramassées en passant dessus (ou éteintes au bout de 25 s).
        flasks = ["Effect_Health_Pack", "Totem_Heal_AttachOnStatue"]
        for k, pos in enumerate(c["heals"]):
            self.add(f"Alchemist_Heal_{k}", g, self.foot(*pos), cylinder(1.2, 2.5), [
                vfx("TAG_ADDED", "Effect_Health_Pack", scale=1.2, duration=25.0),
                vfx("TAG_ADDED", "Totem_Heal_AttachOnStatue", scale=0.5, duration=25.0),
                tags("TAG_ADDED", "Pack", "Off", 25.0),
                status("Health_Pack", -1.0),
                tags("TICK", "Pack", "Off"),
                effect("CancelParticles", "TICK", ParticleSystems=flasks)],
                [tag_is("TAG_ADDED", "Pack", "On"), tag_is("TICK", "Pack", "On")],
                volume_tags={"Alchemist_Heal": str(k), "Pack": "Off"}, ConditionTiming="BeforeVolumeDelay")
        # Titres des phases.
        for phase, sfx in ((2, "SFX_Emit_Goblin_Pipes_Activate"), (3, "SFX_Emit_Dungeon_Goblin_Void_Thunder")):
            self.add(f"Alchemist_Phase_{phase}", g, self.foot(cx, y, cz), cylinder(at.DECK_R, 8), [
                title("TAG_ADDED", f"alchemist_phase{phase}"), sound("TAG_ADDED", sfx),
                tags("TAG_ADDED", "Cast", "Off", 3.0)],
                [tag_is("TAG_ADDED", "Cast", "On")], volume_tags={"Cast": "Off"})
        # Remise à zéro : le rebord se reconstruit, les fioles s'éteignent.
        self.add("Alchemist_Arena", g, self.foot(cx, y, cz), cylinder(at.DECK_R, 8), [
            signal("TAG_ADDED", "Restore", "Alchemist_Pile", radius=70.0),
            tags("TAG_ADDED", "Pack", "Off", match="Alchemist_Heal", radius=70),
            effect("CancelParticles", "TAG_ADDED", ParticleSystems=flasks),
            tags("TAG_ADDED", "Reset", "Off", 1.0)],
            [tag_is("TAG_ADDED", "Reset", "On")], volume_tags={"Reset": "Off"})

    def build(self):
        self.court()
        self.hall()
        self.leaks()
        self.greenhouse()
        self.library()
        self.codex()
        self.chimera()
        self.alchemist()
        self.transmutation()
        self.wind_stair()
        self.arenas()
        check_ids(self.volumes)
        return self.volumes, self.groups


def check_ids(volumes):
    """Refuse un id du jeu qui ne serait pas dans les listes vérifiées (PARTICLES, SOUNDS, EFFECTS, BLOCKS, NPCS)."""
    known = {"ParticleSystem": PARTICLES, "SoundEvent": SOUNDS, "Effect": EFFECTS, "ToBlockType": BLOCKS,
             "BlockType": BLOCKS, "NpcType": NPCS}
    for v in volumes.values():
        for e in v["Effects"]:
            for field, ids in known.items():
                if field == "ParticleSystem" and e.get(field, "").startswith((tw.PREFIX, "Nakasar_Gas_Cloud_",
                                                                               "Nakasar_Spore_Cloud_")):
                    continue  # zones d'annonce et nuages de la tour, écrits par tower_warnings.write() et write_clouds()
                if field in e and e[field] not in ids:
                    raise RuntimeError(f"pièges : {field} inconnu {e[field]!r} dans {v['Name']}")
            for b in e.get("FromBlockTypes", ()):
                if b not in BLOCKS:
                    raise RuntimeError(f"pièges : bloc inconnu {b!r} dans {v['Name']}")


def piles(cells):
    """Découpe des blocs (x, y, z) en boîtes pleines : colonnes de même hauteur regroupées en bandes, puis en
    rectangles quand des bandes voisines coïncident."""
    height = {}
    for x, y, z in cells:
        height.setdefault((x, z), []).append(y)
    cols = {xz: (min(ys), max(ys)) for xz, ys in height.items()}
    rows = {}
    for (x, z), span in sorted(cols.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        runs = rows.setdefault((z, span), [])
        if runs and runs[-1][1] == x - 1:
            runs[-1][1] = x
        else:
            runs.append([x, x])
    boxes = {}
    for (z, span), runs in sorted(rows.items()):
        for x0, x1 in runs:
            key = (x0, x1, span)
            if key in boxes and boxes[key][-1][1] == z - 1:
                boxes[key][-1][1] = z
            else:
                boxes.setdefault(key, []).append([z, z])
    out = []
    for (x0, x1, (y0, y1)), zs in sorted(boxes.items()):
        for z0, z1 in zs:
            out.append([(x0, y0, z0), (x1, y1, z1)])
    assert sum((b[1][0] - b[0][0] + 1) * (b[1][1] - b[0][1] + 1) * (b[1][2] - b[0][2] + 1) for b in out) == len(cells)
    return out


def codex_ids():
    """Ids des volumes que tower.CodexSystem étiquette (TowerLayout.java)."""
    return {"seal": vid("Codex_Seal"), "arena": vid("Codex_Arena"), "fire": vid("Codex_Fire"),
            "rain": vid("Codex_Rain"), "frost": [vid(f"Codex_Frost_{k}") for k in range(len(at.LECTERN_ANGLES))],
            "collapse": [vid(f"Codex_Collapse_{i}") for i in range(len(at.COLLAPSE_ARCS))]}


def court_ids():
    """Id du volume des portes de la tour que tower.CourtGuardSystem étiquette (TowerLayout.java)."""
    return {"door": vid("Court_Door")}


def arena_ids():
    """Ids des volumes des barrières d'arène que tower.ArenaGate étiquette (TowerLayout.java)."""
    return {name: vid(f"{name}_Gate") for name in ARENAS}


def chimera_ids():
    """Ids des volumes que tower.ChimeraSystem étiquette (TowerLayout.java)."""
    return {"seal": vid("Chimera_Seal"), "acid": vid("Chimera_Acid")}


def alchemist_ids():
    """Ids des volumes que tower.AlchemistSystem étiquette ou lit (TowerLayout.java)."""
    arcs = range(len(at.DECK_COLLAPSE_ARCS))
    return {"seal": vid("Alchemist_Seal"), "lever": vid("Alchemist_Lever"), "arena": vid("Alchemist_Arena"),
            "phase2": vid("Alchemist_Phase_2"), "phase3": vid("Alchemist_Phase_3"),
            "collapse": [vid(f"Alchemist_Collapse_{i}") for i in arcs],
            "heals": [vid(f"Alchemist_Heal_{k}") for k in range(len(at.HEAL_ANGLES))]}


def trap_volumes(tower, origin):
    """{id: volume} et {id: groupe} des pièges de la tour, pour TriggerVolumeData.json."""
    return Traps(tower, origin).build()


# --- blocs ------------------------------------------------------------------------------------------------------

def seal_texture(seed=4401):
    """Verre alchimique vert et or, translucide : cercle, triangle et carré de la transmutation, liseré d'or."""
    rng = random.Random(seed)
    n = 32
    img = Image.new("RGBA", (n, n))
    px = img.load()
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - 15.5, y - 15.5) / 16
            g = 150 + int(70 * (1 - d)) + rng.randint(-10, 10)
            px[x, y] = (40 + rng.randint(0, 20), min(255, g), 110 + rng.randint(-10, 10), 150)
    gold = (236, 196, 84, 235)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, n - 1, n - 1), outline=gold)
    draw.ellipse((5, 5, 26, 26), outline=gold)
    draw.polygon([(15.5, 7), (24, 22), (7, 22)], outline=gold)
    draw.rectangle((12, 14, 19, 20), outline=(255, 238, 160, 240))
    draw.point([(15, 15), (16, 16), (15, 16), (16, 15)], fill=(255, 255, 220, 255))
    return img


def block_item(block_id, icon, block_type):
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{block_id}.name"},
        "Icon": icon,
        "Categories": ["Blocks.Deco"],
        "Quality": "Technical",
        "PlayerAnimationsId": "Block",
        "BlockType": block_type,
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Blocks_Stone",
    }


def seal_item(texture, icon):
    return block_item(at.SEAL, icon, {
        "Material": "Solid",
        "DrawType": "Cube",
        "Opacity": "Semitransparent",
        "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Rocks"}},
        "Light": {"Color": "#4c8"},
        "BlockParticleSetId": "Crystal",
        "BlockSoundSetId": "Crystal",
        "ParticleColor": "#58d68d",
    })


def barrier_texture(seed=4405):
    """Champ de force des arènes : voile cramoisi translucide, mailles hexagonales violettes qui luisent."""
    rng = random.Random(seed)
    n = 32
    img = Image.new("RGBA", (n, n))
    px = img.load()
    for y in range(n):
        for x in range(n):
            wave = 0.5 + 0.5 * math.sin((x + y) * 0.45) * math.cos((x - y) * 0.3)
            px[x, y] = (150 + int(70 * wave) + rng.randint(-8, 8), 20 + rng.randint(0, 14),
                        60 + int(50 * wave) + rng.randint(-8, 8), 110 + int(40 * wave))
    draw = ImageDraw.Draw(img)
    mesh = (236, 120, 255, 230)
    for cy in (0, 16, 32):
        for cx in (0, 16, 32):
            ox = 8 if cy == 16 else 0
            pts = [(cx + ox + 7 * math.cos(math.radians(60 * k + 30)), cy + 7 * math.sin(math.radians(60 * k + 30)))
                   for k in range(6)]
            draw.polygon(pts, outline=mesh)
    draw.rectangle((0, 0, n - 1, n - 1), outline=(255, 90, 90, 240))
    return img


def barrier_item(texture, icon):
    return block_item(at.ARENA_BARRIER, icon, {
        "Material": "Solid",
        "DrawType": "Cube",
        "Opacity": "Semitransparent",
        "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Rocks"}},
        "Light": {"Color": "#c3a"},
        "BlockParticleSetId": "Crystal",
        "BlockSoundSetId": "Crystal",
        "ParticleColor": "#e0408a",
    })


def rubble_texture(seed=4402):
    """Éboulis de bibliothèque : livres pêle-mêle (dos de couleur, tranches crème), éclats de bois sombre."""
    rng = random.Random(seed)
    n = 32
    img = Image.new("RGBA", (n, n), (58, 40, 30, 255))
    draw = ImageDraw.Draw(img)
    spines = [(122, 34, 40), (44, 70, 120), (60, 100, 52), (110, 76, 40), (84, 44, 100), (30, 30, 36)]
    y = 0
    while y < n:
        h = rng.randint(4, 7)
        x = rng.randint(-3, 0)
        while x < n:
            w = rng.randint(3, 6)
            if rng.random() < 0.25:  # livre couché : la tranche des pages
                draw.rectangle((x, y + 1, x + w + 3, y + h - 1), fill=(222, 206, 168), outline=(150, 128, 96))
                x += w + 4
                continue
            c = rng.choice(spines)
            draw.rectangle((x, y, x + w - 1, y + h - 1), fill=c, outline=tuple(int(v * 0.6) for v in c))
            if h > 4:
                draw.line((x + 1, y + 2, x + w - 2, y + 2), fill=(214, 172, 70))
            x += w
        y += h
    for _ in range(6):  # planches cassées
        x0, y0 = rng.randint(0, n - 1), rng.randint(0, n - 1)
        draw.line((x0, y0, x0 + rng.randint(-8, 8), y0 + rng.randint(-3, 3)), fill=(40, 26, 18), width=2)
    return img


def rubble_item(texture, icon):
    """Éboulis du combat du Codex : bloc plein (on ne le traverse pas), posé et retiré par les volumes de l'arène."""
    return block_item(at.RUBBLE, icon, {
        "Material": "Solid",
        "DrawType": "Cube",
        "Opacity": "Solid",
        "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "BlockParticleSetId": "Wood",
        "BlockSoundSetId": "Wood",
        "ParticleColor": "#6b4a32",
    })


def hedge_item():
    """Haie de ronces : le feuillage de ronce du jeu en bloc plein, sans support, qui pique (comme le buisson de ronces)."""
    return block_item(at.HEDGE, "Icons/ItemsGenerated/Plant_Bramble_Leaves.png", {
        "Material": "Solid",
        "DrawType": "Model",
        "Opacity": "Cutout",
        "CustomModel": "Blocks/Foliage/Leaves/UpShapeSoft.blockymodel",
        "CustomModelTexture": [{"Texture": "Blocks/Foliage/Leaves/UpShapeSoft_Textures/Gramble.png", "Weight": 1}],
        "RandomRotation": "YawStep1",
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "Interactions": {"CollisionEnter": "Environmental_Block_Damage"},
        "BlockParticleSetId": "Leaves",
        "BlockSoundSetId": "Bramble",
        "PhysicalMaterialId": "Foliage",
        "ParticleColor": "#b46b26",
    })


def lever_item():
    """Levier de vanne : le levier du jeu, qu'on peut utiliser (comme un brasero, il change d'état)."""
    return block_item(at.LEVER, "Icons/ItemsGenerated/Deco_Lever.png", {
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": "Blocks/Tinkering/Lever.blockymodel",
        "CustomModelTexture": [{"Texture": "Blocks/Tinkering/Lever_Texture.png", "Weight": 1}],
        "HitboxType": "Plant_Large",
        "VariantRotation": "NESW",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "BlockParticleSetId": "Metal",
        "BlockSoundSetId": "Metal",
        "PhysicalMaterialId": "Metal",
        "InteractionHint": "server.interactionHints.activate",
        "InteractionSoundEventId": "SFX_Lever_Metal_On",
        "Interactions": {"Use": {"Interactions": [{"Type": "ChangeState", "Changes": {"default": "On", "On": "default"}}]}},
        "State": {"Definitions": {"On": {"InteractionSoundEventId": "SFX_Lever_Metal_Off"}}},
    })


VALVE_IRON = (58, 60, 66)
VALVE_BRASS = (176, 132, 58)
VALVE_RED = (156, 30, 28)
VALVE_LAMPS = {"default": (255, 70, 40), "On": (90, 255, 120)}


def valve_parts(lamp):
    """Vanne de gaz : conduite verticale de fer (deux blocs de haut) avec ses brides, corps de laiton, volant rouge à
    rayons face au joueur (+Z), manomètre et voyant (rouge : gaz ouvert ; vert une fois la vanne fermée)."""
    iron, dark = gx.painter(VALVE_IRON, "iron"), gx.painter(gx.IRON_DARK, "iron")
    brass, red = gx.painter(VALVE_BRASS, "iron"), gx.painter(VALVE_RED, "iron")
    parts = [
        ("Base", (0, 1, -3), (14, 2, 14), 0, dark, "flat"),
        ("Pipe", (0, 32, -6), (8, 64, 8), 0, iron, "flat"),
        ("Body", (0, 30, -2), (12, 12, 10), 0, brass, "flat"),
        ("Stem", (0, 30, 6), (3, 3, 6), 0, brass, "flat"),
        ("Hub", (0, 30, 9.5), (4.5, 4.5, 2.5), 0, brass, "flat"),
        ("Spoke_H", (0, 30, 9.5), (17, 2, 1.5), 0, red, "flat"),
        ("Spoke_V", (0, 30, 9.5), (2, 17, 1.5), 0, red, "flat"),
        ("Gauge", (0, 46, -1), (7, 7, 3), 0, brass, "flat"),
        ("Lamp", (0, 46, 0.8), (4, 4, 1), 0, gx.painter(lamp, glow=True), "fullbright"),
    ]
    for k, y in enumerate((3, 20, 41, 62)):
        parts.append((f"Flange_{k}", (0, y, -6), (11, 3, 11), 0, dark, "flat"))
    for k in range(16):
        a = math.radians(k * 22.5)
        parts.append((f"Rim_{k}", (round(9 * math.cos(a), 2), round(30 + 9 * math.sin(a), 2), 9.5), (3.2, 3.2, 2.5), 0,
                      red, "flat"))
    return parts


def valve_render(textures, uv, size, state="default"):
    return gx.render(valve_parts(VALVE_LAMPS[state]), textures[state], uv, size, yaw=-35, pitch=18, scale=size / 84,
                     center=(0, 32, 0))


def valve_assets():
    """Modèle, textures (voyant rouge, puis vert), placement des textures et icône de la vanne ; le modèle est le même
    pour les deux états."""
    model = None
    textures = {}
    for state, lamp in VALVE_LAMPS.items():
        parts = valve_parts(lamp)
        atlas, uv = gx.build_atlas(parts, seed=4403, tex_w=64)
        model = gx.build_model("Valve", parts, uv)
        textures[state] = atlas
    return model, textures, uv, valve_render(textures, uv, 256).resize((64, 64), Image.LANCZOS)


def valve_item(model, textures, icon):
    """Vanne de la conduite de gaz du Couloir des fuites : on la ferme (Use) ; elle passe à l'état On, voyant vert."""
    return block_item(at.VALVE, icon, {
        "Material": "Solid",
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": model,
        "CustomModelTexture": [{"Texture": textures["default"], "Weight": 1}],
        "HitboxType": "Nakasar_Tower_Valve",
        "VariantRotation": "NESW",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "Light": {"Color": "#f42"},
        "BlockParticleSetId": "Metal",
        "BlockSoundSetId": "Metal",
        "PhysicalMaterialId": "Metal",
        "ParticleColor": "#b0843a",
        "InteractionHint": "server.interactionHints.activate",
        "InteractionSoundEventId": "SFX_Lever_Metal_On",
        "Interactions": {"Use": {"Interactions": [{"Type": "ChangeState", "Changes": {"default": "On", "On": "default"}}]}},
        "State": {"Definitions": {"On": {
            "CustomModelTexture": [{"Texture": textures["On"], "Weight": 1}],
            "Light": {"Color": "#4f6"},
            "InteractionSoundEventId": "SFX_Lever_Metal_Off"}}},
    })


# --- peinture façon Hytale ----------------------------------------------------------------------------------------

def pixel_painter(base, patch=5, jitter=0.05, seam=0.14, rim=0.18, top=1.1, bottom=0.7, fibres=False, spots=None):
    """Peintre « pixel » dans l'esprit des textures du jeu (Mushroom_Block_*, 32 px par bloc) : pas de flou ni de
    dégradé lisse. La face est pavée de plaques irrégulières (Voronoï, une tous les `patch` px) de tons un peu
    différents, aux joints plus sombres, avec un grain d'un pixel ; bord de face assombri (`rim`), dessus plus clair et
    dessous plus sombre. `fibres` : traits verticaux d'un pixel (pieds, bois). `spots` : (couleur, densité) de petites
    taches claires cerclées, peintes dans la texture (chapeau)."""

    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h))
        px = img.load()
        n = max(2, (w * h) // (patch * patch))
        seeds = [(rng.uniform(0, w), rng.uniform(0, h), 1 + rng.uniform(-2.5, 2.5) * jitter) for _ in range(n)]
        cols = [1 + rng.uniform(-1, 1) * jitter * 0.6 for _ in range(w)] if fibres else None
        f_face = top if face == "top" else bottom if face == "bottom" else 1.0
        dots = set()
        if spots and face != "bottom":
            for _ in range(max(1, int(w * h * spots[1] / 100))):
                cx, cy, r = rng.randrange(w), rng.randrange(h), rng.choice((1, 1, 2))
                dots.add((cx, cy, r))
        for y in range(h):
            for x in range(w):
                d = sorted((((x + 0.5 - sx) ** 2 + (y + 0.5 - sy) ** 2), t) for sx, sy, t in seeds)
                f = d[0][1] * f_face * (1 + rng.uniform(-1, 1) * jitter * 0.5)
                if len(d) > 1 and math.sqrt(d[1][0]) - math.sqrt(d[0][0]) < 0.9:
                    f *= 1 - seam
                if cols:
                    f *= cols[x]
                if min(x, y, w - 1 - x, h - 1 - y) == 0 and min(w, h) > 3 and face != "top":
                    f *= 1 - rim
                c = gx.shade(base, f)
                for cx, cy, r in dots:
                    dd = math.hypot(x - cx, y - cy)
                    if dd <= r - 0.5:
                        c = gx.shade(spots[0], 1 + rng.uniform(-0.04, 0.04))
                    elif dd <= r + 0.6:
                        c = gx.mix(c, spots[0], 0.35)
                px[x, y] = c + (255,)
        return img

    return paint


# --- buses de gaz (couloir des fuites) ---------------------------------------------------------------------------

NOZZLE_BRASS = (168, 122, 54)
NOZZLE_IRON = (64, 62, 70)
NOZZLE_GLOW = (170, 255, 90)


def nozzle_parts(diagonal=False):
    """Buse de gaz, à hauteur de poitrine contre le mur (-Z) : patte de fixation boulonnée au mur, coude de fer qui
    reçoit la descente de tuyau luisant (en haut), pavillon de laiton évasé vers l'avant (+Z), gueule verte lumineuse.
    Le modèle diagonal est le même tourné de 45° (avant vers +X +Z)."""
    iron, dark = pixel_painter(NOZZLE_IRON, patch=4), pixel_painter(gx.IRON_DARK, patch=4)
    brass = pixel_painter(NOZZLE_BRASS, patch=4, seam=0.1)
    glow = gx.painter(NOZZLE_GLOW, glow=True)
    parts = [
        ("Plate", (0, 15, -14.5), (16, 16, 3), 0, dark, "flat"),
        ("Arm", (0, 15, -9), (6, 6, 8), 0, iron, "flat"),
        ("Elbow", (0, 17, -2), (11, 13, 11), 0, iron, "flat"),
        ("Riser", (0, 27, -2), (8, 10, 8), 0, iron, "flat"),
        ("Collar", (0, 15, 4.5), (9, 9, 3), 0, dark, "flat"),
        ("Horn_1", (0, 15, 7.5), (11, 11, 3), 0, brass, "flat"),
        ("Horn_2", (0, 15, 10.5), (14, 14, 3), 0, brass, "flat"),
        ("Horn_3", (0, 15, 13), (17, 17, 2), 0, brass, "flat"),
        ("Horn_Rim", (0, 15, 14.75), (18.5, 18.5, 1.5), 0, brass, "flat"),
        ("Throat", (0, 15, 15.1), (14, 14, 1), 0, dark, "flat"),
        ("Mouth", (0, 15, 15.8), (8, 8, 0.4), 0, glow, "fullbright"),
    ]
    for k, (bx, by) in enumerate(((-5.5, 20.5), (5.5, 20.5), (-5.5, 9.5), (5.5, 9.5))):
        parts.append((f"Bolt_{k}", (bx, by, -12.6), (2.5, 2.5, 1), 0, brass, "flat"))
    if diagonal:
        parts = [(n, tuple(round(v, 3) for v in gx.rot_y(c, 45)), size, rot + 45, paint, shading)
                 for n, c, size, rot, paint, shading in parts]
    return parts


def nozzle_assets():
    """Modèles (droit, diagonal), texture commune, icône de la buse."""
    out = {}
    for diag in (False, True):
        parts = nozzle_parts(diag)
        atlas, uv = gx.build_atlas(parts, seed=4407, tex_w=64)
        out[diag] = (gx.build_model("Gas_Nozzle", parts, uv), atlas, uv)
    model, atlas, uv = out[False]
    icon = gx.render(nozzle_parts(), atlas, uv, 256, yaw=-35, pitch=18, scale=256 / 40, center=(0, 15, 0))
    return out, icon.resize((64, 64), Image.LANCZOS)


def nozzle_item(block_id, model, texture, icon):
    """Buse de gaz : décor plein (on ne la traverse pas), lumière verte."""
    return block_item(block_id, icon, {
        "Material": "Solid",
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": model,
        "CustomModelTexture": [{"Texture": texture, "Weight": 1}],
        "HitboxType": "Full",
        "VariantRotation": "NESW",
        "Flags": {},
        "Gathering": {"Breaking": {"GatherType": "Unbreakable"}},
        "Light": {"Color": "#6c3"},
        "BlockParticleSetId": "Metal",
        "BlockSoundSetId": "Metal",
        "PhysicalMaterialId": "Metal",
        "ParticleColor": "#a87a36",
    })


# --- champignon des spores (serre) ----------------------------------------------------------------------------

SHROOM_FPS = 60                # images par seconde des .blockyanim (Boomshroom_Large_Exploding : 195 = mèche de 3,25 s)
SHROOM_PIVOT = 31              # bas du chapeau (pixels) : le chapeau enfle autour de ce point
SHROOM_COLORS = {"default": ((118, 52, 150), (150, 255, 110)), "Swelling": ((170, 60, 120), (225, 255, 90))}
# Enflure du chapeau (image, facteur) : souffle lent au repos ; à l'annonce il gonfle en tremblant pendant SPORE_WARN s,
# se vide d'un coup quand le nuage sort, puis reprend sa forme.
SHROOM_IDLE = [(0, 1.0), (90, 1.05), (180, 1.0)]
SHROOM_SWELL = [(0, 1.0), (30, 1.08), (60, 1.16), (90, 1.25), (110, 1.32), (118, 1.36), (124, 0.84), (150, 0.96),
                (180, 1.0)]
SHROOM_PUFF_END = SHROOM_SWELL[-1][0] / SHROOM_FPS


def shroom_parts(state):
    """Grand champignon violet de la serre, deux blocs de haut : pied crème sur sa volve, anneau, lamelles sombres,
    chapeau en trois étages semé de points lumineux (plus vifs et rougeâtres quand il enfle)."""
    cap, glow = SHROOM_COLORS[state]
    # Textures « pixel » comme les champignons du jeu (Kevin : les textures lisses ne font pas Hytale).
    cream = pixel_painter((214, 200, 172), patch=4, jitter=0.04, seam=0.06, fibres=True)
    dark = pixel_painter((58, 30, 70), patch=3, seam=0.2, fibres=True)
    hat = pixel_painter(cap, patch=5, jitter=0.06, seam=0.16, spots=(gx.mix(cap, (255, 236, 250), 0.45), 1.2))
    light = gx.painter(glow, glow=True)
    parts = [
        ("Volva", (0, 2, 0), (13, 4, 13), 0, cream, "flat"),
        ("Stem", (0, 16, 0), (8, 26, 8), 0, cream, "flat"),
        ("Ring", (0, 23, 0), (12, 2, 12), 0, cream, "flat"),
        ("Cap_Gills", (0, 31.5, 0), (26, 1, 26), 0, dark, "flat"),
        ("Cap", (0, 35, 0), (30, 6, 30), 0, hat, "flat"),
        ("Cap_Top", (0, 40.5, 0), (22, 5, 22), 0, hat, "flat"),
        ("Cap_Crown", (0, 44.5, 0), (12, 3, 12), 0, hat, "flat"),
    ]
    spots = [(-6, 43, 5), (7, 43, -4), (-3, 46.5, -2), (9, 38.5, 9), (-10, 38.5, -8), (11, 38.5, -10), (-11, 38.5, 9),
             (2, 43, 9)]
    for k, (x, y, z) in enumerate(spots):
        parts.append((f"Cap_Spot_{k}", (x, y, z), (3, 1.2, 3), 0, light, "fullbright"))
    for k in range(8):  # points sur le bord du chapeau
        a = math.radians(22.5 + 45 * k)
        parts.append((f"Cap_Dot_{k}", (round(15.2 * math.cos(a), 2), 35, round(15.2 * math.sin(a), 2)), (1, 2, 2), 0,
                      light, "fullbright"))
    return parts


def shroom_anim(keys, parts, wobble=False):
    """Animation du chapeau : chaque pièce du chapeau grandit du facteur et s'écarte du pivot d'autant ; le pied se
    tasse un peu quand le chapeau enfle."""
    nodes = {}
    if wobble:  # images toutes les 6 pendant l'enflure, pour le tremblement
        dense = dict(keys)
        for t in range(36, 118, 6):
            if t not in dense:
                (t0, f0), (t1, f1) = max((k for k in keys if k[0] < t)), min((k for k in keys if k[0] > t))
                dense[t] = round(f0 + (f1 - f0) * (t - t0) / (t1 - t0), 3)
        keys = sorted(dense.items())
    for name, c, _, _, _, _ in parts:
        cap = name.startswith("Cap")
        pos, stretch = [], []
        for t, f in keys:
            if cap:
                d = {"x": round(c[0] * (f - 1), 3), "y": round((c[1] - SHROOM_PIVOT) * (f - 1), 3),
                     "z": round(c[2] * (f - 1), 3)}
                if wobble and 36 <= t <= 118:  # de plus en plus fort jusqu'au crachat
                    amp = 0.25 + 0.75 * (t - 36) / 82
                    side = 1 if (t // 6) % 2 else -1
                    d["x"] = round(d["x"] + side * amp, 3)
                    d["z"] = round(d["z"] - side * amp * 0.6, 3)
                pos.append({"time": t, "delta": d, "interpolationType": "smooth"})
                stretch.append({"time": t, "delta": {"x": f, "y": f, "z": f}, "interpolationType": "smooth"})
            elif name == "Stem":
                squash = round(1 - 0.25 * (f - 1), 3)
                stretch.append({"time": t, "delta": {"x": round(1 + 0.3 * (f - 1), 3), "y": squash,
                                                     "z": round(1 + 0.3 * (f - 1), 3)}, "interpolationType": "smooth"})
        if pos or stretch:
            nodes[name] = {"position": pos, "orientation": [], "shapeStretch": stretch, "shapeVisible": [],
                           "shapeUvOffset": []}
    return {"formatVersion": 1, "duration": keys[-1][0], "holdLastKeyframe": False, "nodeAnimations": nodes}


def shroom_assets():
    """Modèle, animations, textures des deux états et icône du champignon des spores."""
    textures = {}
    model = uv = None
    for state in SHROOM_COLORS:
        parts = shroom_parts(state)
        atlas, uv = gx.build_atlas(parts, seed=4406, tex_w=64)
        model = gx.build_model("Spore_Shroom", parts, uv)
        textures[state] = atlas
    parts = shroom_parts("default")
    anims = {"Idle": shroom_anim(SHROOM_IDLE, parts), "Swelling": shroom_anim(SHROOM_SWELL, parts, wobble=True)}
    icon = gx.render(parts, textures["default"], uv, 256, yaw=-35, pitch=18, scale=256 / 60, center=(0, 26, 0))
    return model, anims, textures, uv, icon.resize((64, 64), Image.LANCZOS)


def shroom_item(model, anims, textures, icon):
    """Champignon des spores : il respire au repos ; les volumes de la serre le passent à l'état Swelling (il enfle et
    crache), puis le remettent à l'état par défaut. Il ne se cueille pas (bloc des pièges de la tour)."""
    return block_item(at.SPORE_SHROOM, icon, {
        "Material": "Solid",
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": model,
        "CustomModelTexture": [{"Texture": textures["default"], "Weight": 1}],
        "CustomModelAnimation": anims["Idle"],
        "HitboxType": "Nakasar_Spore_Shroom",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "Light": {"Color": "#848"},
        "BlockParticleSetId": "Dust",
        "BlockSoundSetId": "Mushroom",
        "PhysicalMaterialId": "Foliage",
        "ParticleColor": "#8a4fb0",
        "Particles": [{"SystemId": "Dungeon_Goblin_Spores_Green", "Scale": 0.6,
                       "PositionOffset": {"X": 0, "Y": 1.4, "Z": 0}}],
        "State": {"Definitions": {"Swelling": {
            "CustomModelTexture": [{"Texture": textures["Swelling"], "Weight": 1}],
            "CustomModelAnimation": anims["Swelling"],
            "Light": {"Color": "#c84"}}}},
    })


GAS_COLORS = {"Gas": ("#e4ff6a", "#a8d43a", "#6f8a2a", "#4a5a22"), "Spore": ("#c8ff5a", "#86d44a", "#7a3a9a", "#5a2a7a")}
_clouds = set()


def gas_cloud(radius, kind="Gas"):
    """Id du nuage (gaz du couloir ou spores de la serre) qui remplit un cercle de `radius` blocs, sans en déborder :
    la zone rouge d'annonce et la zone d'effet ont ce même rayon (Kevin : « la zone rouge doit correspondre à la zone
    d'effet des spores »). Écrit par `cloud_files`."""
    t = int(round(radius * 10))
    _clouds.add((kind, t))
    return f"Nakasar_{kind}_Cloud_{t}"


def cloud_files():
    """Nuages demandés par `gas_cloud` : fumée épaisse émise en continu tant que dure l'effet (d'après
    Explosion_Shroom_SporeCloud du jeu). Les particules naissent à moins de 0,7 rayon du centre et leur taille suit le
    rayon, pour que le bord du nuage tombe sur le bord du cercle rouge."""
    out = {}
    for kind, t in sorted(_clouds):
        r = t / 10
        c0, c1, c2, c3 = GAS_COLORS[kind]
        size = max(0.8, min(1.8, 0.6 * r))
        name = f"Nakasar_{kind}_Cloud_{t}"
        smoke = {
            "RenderMode": "BlendLinear",
            "EmitOffset": {"X": {"Min": 0, "Max": round(0.7 * r, 2)}, "Y": {"Min": 0.2, "Max": 1.6},
                           "Z": {"Min": 0, "Max": round(0.7 * r, 2)}},
            "ParticleRotationInfluence": "Billboard",
            "LinearFiltering": True,
            "LightInfluence": 0.3,
            "ParticleRotateWithSpawner": False,
            "TrailSpawnerPositionMultiplier": 1,
            "TrailSpawnerRotationMultiplier": 1,
            "MaxConcurrentParticles": max(8, int(48 * (r / 3) ** 2)),
            "ParticleLifeSpan": {"Min": 1.2, "Max": 2.0},
            "SpawnRate": {"Min": max(4, int(18 * (r / 3) ** 2)), "Max": max(5, int(22 * (r / 3) ** 2))},
            "InitialVelocity": {"Speed": {"Min": 0.02, "Max": 0.12}, "Yaw": {"Min": -180, "Max": 180},
                                "Pitch": {"Min": 60, "Max": 120}},
            "Particle": {
                "Texture": "Particles/Textures/Smoke/Smoke_Smooth2.png",
                "FrameSize": {"Width": 64, "Height": 64},
                "ScaleRatioConstraint": "None",
                "UVOption": "RandomFlipU",
                "Animation": {
                    "0": {"Opacity": 0, "Color": c0, "Scale": {"X": {"Min": 1, "Max": 1}, "Y": {"Min": 1, "Max": 1}}},
                    "15": {"Opacity": 0.8},
                    "50": {"Opacity": 0.85, "Color": c1},
                    "80": {"Opacity": 0.5, "Color": c2},
                    "100": {"Opacity": 0, "Color": c3,
                            "Scale": {"X": {"Min": 1.3, "Max": 1.2}, "Y": {"Min": 1.3, "Max": 1.2}}},
                },
                "InitialAnimationFrame": {
                    "Rotation": {"X": {"Min": 0, "Max": 0}, "Y": {"Min": 0, "Max": 0}, "Z": {"Min": -90, "Max": 90}},
                    "Scale": {"X": {"Min": size, "Max": round(size * 1.5, 2)},
                              "Y": {"Min": size, "Max": round(size * 1.5, 2)}},
                    "Opacity": 0.5,
                    "Color": "#ffffff",
                    "FrameIndex": {"Min": 0, "Max": 3},
                },
            },
            "UVMotion": {"Texture": "Particles/Textures/UVMotion/FlowMapSmoke.png", "SpeedY": 0.24, "Scale": 1.04,
                         "StrengthCurveType": "IncreaseQuartOut", "Strength": 7, "SpeedX": 0.08},
            "SpawnBurst": False,
        }
        # Spores qui flottent dans le nuage (Dungeon_Goblin_Spores_Green2 du jeu, ramenées dans le cercle).
        motes = {
            "RenderMode": "Erosion",
            "ParticleRotationInfluence": "Velocity",
            "MaxConcurrentParticles": max(4, int(10 * (r / 3) ** 2)),
            "ParticleLifeSpan": {"Min": 1.2, "Max": 2.2},
            "SpawnRate": {"Min": 3, "Max": 6},
            "Particle": {
                "Texture": "Particles/Textures/Basic/Spark.png",
                "ScaleRatioConstraint": "None",
                "SoftParticles": "Disable",
                "Animation": {
                    "0": {"Opacity": 0, "Scale": {"X": {"Min": 0, "Max": 0}, "Y": {"Min": 0, "Max": 0}}, "Color": c0},
                    "30": {"Opacity": 1, "Scale": {"X": {"Min": 1, "Max": 1}, "Y": {"Min": 1, "Max": 1}}},
                    "100": {"Opacity": 0, "Scale": {"X": {"Min": 0, "Max": 0}, "Y": {"Min": 0, "Max": 0}}, "Color": c1},
                },
                "InitialAnimationFrame": {"Scale": {"X": {"Min": 0.33, "Max": 0.47}, "Y": {"Min": 0.33, "Max": 0.47}},
                                          "Opacity": 1,
                                          "Rotation": {"X": {"Min": 0, "Max": 360}, "Y": {"Min": 0, "Max": 360},
                                                       "Z": {"Min": 0, "Max": 360}}},
                "UVOption": "RandomFlipUV",
            },
            "Shape": "Sphere",
            "EmitOffset": {"X": {"Min": 0, "Max": round(0.85 * r, 2)}, "Y": {"Min": 0, "Max": 1.5},
                           "Z": {"Min": 0, "Max": round(0.85 * r, 2)}},
            "Attractors": [{"DampingMultiplier": {"X": 0.94, "Y": 0.94, "Z": 0.94}, "LinearAcceleration": {"Y": -0.25}}],
            "InitialVelocity": {"Speed": {"Min": 0.05, "Max": 0.3}, "Yaw": {"Min": -180, "Max": 180},
                                "Pitch": {"Min": 0, "Max": -30}},
            "TrailSpawnerPositionMultiplier": 1,
            "TrailSpawnerRotationMultiplier": 1,
            "ParticleRotateWithSpawner": True,
        }
        out[f"{name}.particlesystem"] = {
            "$Comment": f"Nuage ({kind}) de {r:g} blocs de rayon de la Tour de l'Alchimiste. Généré par tools/alchemist_traps.py.",
            "Spawners": [{"SpawnerId": f"{name}_Smoke"}, {"SpawnerId": f"{name}_Motes"}],
            "CullDistance": 64,
        }
        out[f"{name}_Smoke.particlespawner"] = smoke
        out[f"{name}_Motes.particlespawner"] = motes
    return out


# Encre du Codex vivant (jets d'encre, CodexSystem) : flaque à plat d'un rayon de 1,47 bloc à l'échelle 1 (comme les
# cercles d'annonce, tools/tower_warnings.py), éclaboussure de gouttes au point d'impact.
INK_POOL = "Nakasar_Ink_Pool"
INK_SPLASH = "Nakasar_Ink_Splash"
INK = ("#3a1858", "#1c0a2c", "#a05aff")


def ink_files():
    """Particules d'encre jouées par CodexSystem (Java) : une seule bouffée chacune, le Java rejoue la flaque chaque
    seconde tant qu'elle reste au sol (ParticleUtil n'a pas de durée)."""
    deep, black, glow = INK
    flat = {"X": {"Min": 90, "Max": 90}}
    pool = {
        "RenderMode": "BlendLinear",
        "ParticleRotationInfluence": "Velocity",
        "ParticleLifeSpan": {"Min": 1.3, "Max": 1.3},
        "ParticleRotateWithSpawner": True,
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "Particle": {
            "Texture": "Particles/Textures/Basic/Ball5.png",
            "ScaleRatioConstraint": "OneToOne",
            "UVOption": "None",
            "SoftParticles": "Disable",
            "Animation": {"0": {"Opacity": 0.6, "Color": deep}, "20": {"Opacity": 0.9, "Color": black},
                          "80": {"Opacity": 0.9}, "100": {"Opacity": 0.6, "Color": deep}},
            "InitialAnimationFrame": {"Opacity": 0.8, "Rotation": flat, "Scale": {"X": {"Min": 6.25, "Max": 6.25}}},
        },
        "Shape": "Sphere",
        "TotalParticles": {"Min": 1, "Max": 1},
        "SpawnRate": {"Min": 1, "Max": 1},
        "LinearFiltering": True,
        "MaxConcurrentParticles": 1,
        "InitialVelocity": {"Speed": {"Min": 0.01, "Max": 0.01}},
        "SpawnBurst": True,
    }
    bubbles = {
        "RenderMode": "BlendAdd",
        "ParticleRotationInfluence": "Billboard",
        "ParticleLifeSpan": {"Min": 0.6, "Max": 1.1},
        "Particle": {
            "Texture": "Particles/Textures/Basic/Spark.png",
            "ScaleRatioConstraint": "OneToOne",
            "SoftParticles": "Disable",
            "Animation": {"0": {"Opacity": 0, "Color": glow}, "30": {"Opacity": 0.9}, "100": {"Opacity": 0, "Color": deep}},
            "InitialAnimationFrame": {"Opacity": 0.9, "Scale": {"X": {"Min": 0.3, "Max": 0.5}}},
            "UVOption": "RandomFlipUV",
        },
        "Shape": "Sphere",
        "EmitOffset": {"X": {"Min": 0, "Max": 1.1}, "Y": {"Min": 0, "Max": 0.1}, "Z": {"Min": 0, "Max": 1.1}},
        "TotalParticles": {"Min": 4, "Max": 6},
        "SpawnRate": {"Min": 6, "Max": 8},
        "MaxConcurrentParticles": 6,
        "InitialVelocity": {"Speed": {"Min": 0.2, "Max": 0.5}, "Pitch": {"Min": 80, "Max": 100}},
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "SpawnBurst": False,
    }
    drops = {
        "RenderMode": "BlendLinear",
        "ParticleRotationInfluence": "Billboard",
        "ParticleLifeSpan": {"Min": 0.5, "Max": 0.9},
        "Particle": {
            "Texture": "Particles/Textures/Basic/Ball5.png",
            "ScaleRatioConstraint": "OneToOne",
            "SoftParticles": "Disable",
            "Animation": {"0": {"Opacity": 1, "Color": deep}, "70": {"Opacity": 1, "Color": black},
                          "100": {"Opacity": 0, "Color": black}},
            "InitialAnimationFrame": {"Opacity": 1, "Scale": {"X": {"Min": 0.35, "Max": 0.7}}},
            "UVOption": "None",
        },
        "Shape": "Sphere",
        "EmitOffset": {"X": {"Min": 0, "Max": 0.5}, "Y": {"Min": 0, "Max": 0.3}, "Z": {"Min": 0, "Max": 0.5}},
        "TotalParticles": {"Min": 16, "Max": 20},
        "SpawnRate": {"Min": 20, "Max": 20},
        "MaxConcurrentParticles": 20,
        "InitialVelocity": {"Speed": {"Min": 3.0, "Max": 6.0}, "Yaw": {"Min": -180, "Max": 180},
                            "Pitch": {"Min": 40, "Max": 85}},
        "Attractors": [{"LinearAcceleration": {"Y": -14}}],
        "TrailSpawnerPositionMultiplier": 1,
        "TrailSpawnerRotationMultiplier": 1,
        "SpawnBurst": True,
    }
    comment = "du Codex vivant (tower/CodexSystem.java). Généré par tools/alchemist_traps.py."
    return {
        f"{INK_POOL}.particlesystem": {"$Comment": "Flaque d'encre " + comment, "CullDistance": 64,
                                       "Spawners": [{"SpawnerId": f"{INK_POOL}_Disc", "PositionOffset": {"Y": 0.04}},
                                                    {"SpawnerId": f"{INK_POOL}_Bubbles", "PositionOffset": {"Y": 0.1}}]},
        f"{INK_POOL}_Disc.particlespawner": pool,
        f"{INK_POOL}_Bubbles.particlespawner": bubbles,
        f"{INK_SPLASH}.particlesystem": {"$Comment": "Éclaboussure d'encre " + comment, "CullDistance": 64,
                                         "Spawners": [{"SpawnerId": f"{INK_SPLASH}_Drops", "PositionOffset": {"Y": 0.3}}]},
        f"{INK_SPLASH}_Drops.particlespawner": drops,
    }


def write_clouds():
    """Écrit les nuages demandés par les volumes (à appeler après `trap_volumes`) et retire les anciens, ainsi que
    l'encre du Codex."""
    folder = SERVER / "Particles" / "Nakasar" / "Tower"
    files = cloud_files()
    files.update(ink_files())
    for old in folder.glob("Nakasar_*_Cloud*"):
        if old.name not in files:
            old.unlink()
    for name, doc in files.items():
        write_json(folder / name, doc)
    return sorted(_clouds)


def door_texture(seed=4404):
    """Portes de la tour : planches de chêne sombre, bandes et rivets de laiton, sceau de la transmutation au centre."""
    rng = random.Random(seed)
    n = 32
    img = Image.new("RGBA", (n, n), (62, 40, 28, 255))
    px = img.load()
    for x in range(n):
        plank = x // 8
        base = (62 + 6 * (plank % 2), 40 + 3 * (plank % 2), 28)
        for y in range(n):
            g = 1 + 0.08 * math.sin(y * 0.7 + plank * 3 + rng.random() * 0.4)
            c = tuple(int(v * g) for v in base)
            if x % 8 == 0:
                c = tuple(int(v * 0.6) for v in c)
            px[x, y] = c + (255,)
    draw = ImageDraw.Draw(img)
    brass, rivet = (176, 132, 58, 255), (236, 196, 110, 255)
    for y0 in (3, 26):
        draw.rectangle((0, y0, n - 1, y0 + 2), fill=brass)
        for x in range(2, n, 6):
            draw.point((x, y0 + 1), fill=rivet)
    draw.ellipse((10, 10, 21, 21), outline=brass)
    draw.polygon([(15.5, 11), (20, 19), (11, 19)], outline=rivet)
    return img


def door_item(texture, icon):
    """Portes de la tour : bloc plein, posé au portail du hall et retiré par le volume de la cour (Traps.court)."""
    return block_item(at.DOOR, icon, {
        "Material": "Solid",
        "DrawType": "Cube",
        "Opacity": "Solid",
        "Textures": [{"Sides": texture, "UpDown": texture, "Weight": 1}],
        "HitboxType": "Full",
        "Flags": {},
        "Gathering": {"Soft": {}},
        "BlockParticleSetId": "Wood",
        "BlockSoundSetId": "Wood",
        "ParticleColor": "#3e281c",
    })


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    texture, icon = TEXTURES / "Alchemical_Seal.png", ICONS / "Alchemical_Seal.png"
    texture.parent.mkdir(parents=True, exist_ok=True)
    icon.parent.mkdir(parents=True, exist_ok=True)
    img = seal_texture()
    img.save(texture)
    img.resize((64, 64), Image.NEAREST).save(icon)
    write_json(ITEMS / f"{at.SEAL}.json", seal_item(texture.relative_to(COMMON).as_posix(),
                                                    icon.relative_to(COMMON).as_posix()))
    write_json(ITEMS / f"{at.HEDGE}.json", hedge_item())
    model, textures, uv, valve_icon = valve_assets()
    paths = {"model": COMMON / "Blocks" / "Nakasar" / "Alchemist" / "Valve.blockymodel",
             "default": TEXTURES / "Valve.png", "On": TEXTURES / "Valve_On.png", "icon": ICONS / "Valve.png"}
    write_json(paths["model"], model)
    for state, atlas in textures.items():
        atlas.save(paths[state])
    valve_icon.save(paths["icon"])
    rel = {k: v.relative_to(COMMON).as_posix() for k, v in paths.items()}
    write_json(ITEMS / f"{at.LEVER}.json", lever_item())
    write_json(ITEMS / f"{at.VALVE}.json", valve_item(rel["model"], {k: rel[k] for k in textures}, rel["icon"]))
    write_json(SERVER / "Item" / "Block" / "Hitboxes" / "Nakasar" / "Nakasar_Tower_Valve.json",
               {"Boxes": [gx.hitbox_box(-7, 0, -10, 7, 52, 12)]})
    nozzles, nozzle_icon = nozzle_assets()
    nozzle_icon.save(ICONS / "Gas_Nozzle.png")
    for diag, block_id in ((False, at.NOZZLE), (True, at.NOZZLE_DIAG)):
        model_path = COMMON / "Blocks" / "Nakasar" / "Alchemist" / f"{block_id.removeprefix('Nakasar_Tower_')}.blockymodel"
        tex_path = TEXTURES / f"{block_id.removeprefix('Nakasar_Tower_')}.png"
        write_json(model_path, nozzles[diag][0])
        nozzles[diag][1].save(tex_path)
        write_json(ITEMS / f"{block_id}.json", nozzle_item(block_id, model_path.relative_to(COMMON).as_posix(),
                                                            tex_path.relative_to(COMMON).as_posix(),
                                                            (ICONS / "Gas_Nozzle.png").relative_to(COMMON).as_posix()))
    door, door_icon = TEXTURES / "Tower_Door.png", ICONS / "Tower_Door.png"
    door_img = door_texture()
    door_img.save(door)
    door_img.resize((64, 64), Image.NEAREST).save(door_icon)
    write_json(ITEMS / f"{at.DOOR}.json", door_item(door.relative_to(COMMON).as_posix(),
                                                    door_icon.relative_to(COMMON).as_posix()))
    shroom_model, shroom_anims, shroom_textures, shroom_uv, shroom_icon = shroom_assets()
    shroom = {"model": COMMON / "Blocks" / "Nakasar" / "Alchemist" / "Spore_Shroom.blockymodel",
              "default": TEXTURES / "Spore_Shroom.png", "Swelling": TEXTURES / "Spore_Shroom_Swelling.png",
              "icon": ICONS / "Spore_Shroom.png",
              "Idle": COMMON / "Blocks" / "Nakasar" / "Alchemist" / "Spore_Shroom_Idle.blockyanim",
              "Swelling_Anim": COMMON / "Blocks" / "Nakasar" / "Alchemist" / "Spore_Shroom_Swelling.blockyanim"}
    write_json(shroom["model"], shroom_model)
    write_json(shroom["Idle"], shroom_anims["Idle"])
    write_json(shroom["Swelling_Anim"], shroom_anims["Swelling"])
    for state, atlas in shroom_textures.items():
        atlas.save(shroom[state])
    shroom_icon.save(shroom["icon"])
    srel = {k: v.relative_to(COMMON).as_posix() for k, v in shroom.items()}
    write_json(ITEMS / f"{at.SPORE_SHROOM}.json", shroom_item(
        srel["model"], {"Idle": srel["Idle"], "Swelling": srel["Swelling_Anim"]},
        {k: srel[k] for k in shroom_textures}, srel["icon"]))
    write_json(SERVER / "Item" / "Block" / "Hitboxes" / "Nakasar" / "Nakasar_Spore_Shroom.json",
               {"Boxes": [gx.hitbox_box(-5, 0, -5, 5, 30, 5), gx.hitbox_box(-14, 30, -14, 14, 46, 14)]})
    barrier, barrier_icon = TEXTURES / "Arena_Barrier.png", ICONS / "Arena_Barrier.png"
    barrier_img = barrier_texture()
    barrier_img.save(barrier)
    barrier_img.resize((64, 64), Image.NEAREST).save(barrier_icon)
    write_json(ITEMS / f"{at.ARENA_BARRIER}.json", barrier_item(barrier.relative_to(COMMON).as_posix(),
                                                               barrier_icon.relative_to(COMMON).as_posix()))
    rubble, rubble_icon = TEXTURES / "Codex_Rubble.png", ICONS / "Codex_Rubble.png"
    rubble_img = rubble_texture()
    rubble_img.save(rubble)
    rubble_img.resize((64, 64), Image.NEAREST).save(rubble_icon)
    write_json(ITEMS / f"{at.RUBBLE}.json", rubble_item(rubble.relative_to(COMMON).as_posix(),
                                                       rubble_icon.relative_to(COMMON).as_posix()))
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        img.resize((256, 256), Image.NEAREST).save(preview / "Alchemical_Seal.png")
        rubble_img.resize((256, 256), Image.NEAREST).save(preview / "Codex_Rubble.png")
        door_img.resize((256, 256), Image.NEAREST).save(preview / "Tower_Door.png")
        barrier_img.resize((256, 256), Image.NEAREST).save(preview / "Arena_Barrier.png")
        for state in shroom_textures:
            gx.render(shroom_parts(state), shroom_textures[state], shroom_uv, 512, yaw=-35, pitch=18, scale=512 / 60,
                      center=(0, 26, 0)).save(preview / f"Spore_Shroom_{state}.png")
        for state in textures:
            valve_render(textures, uv, 512, state).save(preview / f"Valve_{state}.png")
        for diag in (False, True):
            gx.render(nozzle_parts(diag), nozzles[diag][1], nozzles[diag][2], 512, yaw=-35, pitch=18, scale=512 / 40,
                      center=(0, 15, 0)).save(preview / f"Gas_Nozzle_{'diag' if diag else 'straight'}.png")
    print("blocs des énigmes générés")


if __name__ == "__main__":
    main()
