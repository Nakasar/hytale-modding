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
    "Totem_Heal_AttachOnStatue",
}
SOUNDS = {
    "SFX_Emit_Goblin_Steam_A", "SFX_Env_Geyzer_Burst", "SFX_Lever_Metal_On", "SFX_Emit_Goblin_Pipes_Activate",
    "SFX_Crystal_Break", "SFX_Flame_Ignite", "SFX_Effect_Burn_World", "SFX_Drop_Weapons_Books",
    "SFX_Emit_Goblin_Steam_B", "SFX_Emit_Goblin_Pipes_Flame_Ignite", "SFX_Staff_Flame_Flamethrower",
    "SFX_Emit_Goblin_Flame_Quadrant_Blast", "SFX_Ice_Break", "SFX_Emit_Goblin_Liquid_Bubbling_Steam_Bursts",
    "SFX_Emit_Goblin_Electric_Fence_Zap", "SFX_Emit_Wind_Gusts", "SFX_Emit_Dungeon_Goblin_Void_Thunder",
    "SFX_Dungeon_Checkpoint_Activate",
}
EFFECTS = {"Poison_T1", "Poison_T2", "Burn", "Slow", "Hazard_Electric_Stun", "Health_Pack"}
BLOCKS = {"Empty", "Fluid_Fire", at.SEAL, at.HEDGE, at.RUBBLE, at.DOOR, "Rock_Marble_Brick", "Rock_Marble_Brick_Smooth",
          "Rock_Marble_Cobble", at.CONDUIT_LIT, at.EMANATION_LIT, at.EMANATION_FED, at.PIPE_GLOW, at.LEAK}
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
# Zone rouge des jets de gaz : cercle d'annonce du coup de masse des gobelins, échelle 0,68 par bloc de rayon (comme
# les sorts du Codex), affiché pendant toute l'annonce.
GAS_WARNING_SCALE = 0.68
GAS_WARN = 1.6


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


def place(event, block, pos, delay=0.0, entry=None):
    return effect("PlaceBlock", event, delay, entry, BlockType=block, BlockState="", Position=vec(*pos),
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
        """Les trois athanors : chacun allumé fait courir la lumière dans son conduit jusqu'à l'alambic, remplit son
        tube et fait vibrer le sceau du Couloir des fuites ; les trois ensemble allument le conduit maître et la colonne
        relais jusqu'au plafond, puis le sceau se dissout."""
        g = self.group("Tower_Hall_Athanors", 16737843)
        parts = self.t["hall"]
        seal = self.t["hall_seal"]
        seal_center, _ = self.bounds(seal)
        keys = []
        for i, pos in enumerate(self.t["athanors"], 1):
            keys.append(f"Athanor_{i}")
            x, y, z = pos
            conduit = sorted(parts["conduits"][i - 1], key=lambda c: -math.hypot(c[0], c[2]))  # de l'athanor à l'alambic
            tube = sorted(parts["tubes"][i - 1], key=lambda c: c[1])
            fx = [sound("BLOCK_USED", "SFX_Flame_Ignite"),
                  vfx("BLOCK_USED", "Magic_Sparks_Heavy_GS", offset=(0, 0.5, 0)),
                  place("BLOCK_USED", at.EMANATION_LIT, self.world(x, y + 2, z), 0.3)]
            fx += self.light(conduit, at.CONDUIT_LIT, 0.4, 0.12)
            fx += self.light(tube, at.CONDUIT_LIT, 0.4 + 0.12 * len(conduit), 0.1)
            done = 0.4 + 0.12 * len(conduit) + 0.1 * len(tube)
            fx += [sound("BLOCK_USED", "SFX_Emit_Goblin_Pipes_Activate", 0.4),
                   tags("BLOCK_USED", f"Athanor_{i}", "On", done, match="Hall_Seal", radius=80)]
            self.usable(f"Hall_Athanor_{i}", g, pos, fx)
        # Le sceau vibre à chaque athanor allumé.
        self.add("Hall_Seal_Pulse", g, seal_center, box(1, 1, 1), [
            vfx("TAG_ADDED", "Magic_Sparks_Heavy_GS", scale=2.0),
            vfx("TAG_ADDED", "Goblin_Decorative_Lightning", 0.2, scale=1.5),
            sound("TAG_ADDED", "SFX_Emit_Dungeon_Goblin_Void_Thunder")],
            volume_tags={"Hall_Seal": "Pulse", **{k: "Off" for k in keys}})
        main = sorted(parts["main"], key=lambda c: math.hypot(c[0], c[2]))  # de l'alambic à la colonne
        relay = sorted(parts["relay"], key=lambda c: c[1])
        opened = self.light(main, at.CONDUIT_LIT, 0.2, 0.08, "TAG_ADDED")
        opened += self.light(relay, at.CONDUIT_LIT, 0.2 + 0.08 * len(main), 0.08, "TAG_ADDED")
        rise = 0.2 + 0.08 * (len(main) + len(relay))
        top = self.world(0, at.ALEMBIC_TOP + 4, 0)
        opened += [place("TAG_ADDED", at.EMANATION_FED, top, 0.2),
                   sound("TAG_ADDED", "SFX_Emit_Goblin_Pipes_Activate", 0.2),
                   title("TAG_ADDED", "hall", rise)]
        self.gate("Hall_Seal", g, seal, keys, opened, delay=rise)

    def leaks(self):
        g = self.group("Tower_Leaks_Steam", 7864183)
        y = at.F_LEAKS
        self.controller("Leaks_Controller", g, self.world(0, y, 0), cylinder(at.R_IN, at.F_LIBRARY - at.F_LEAKS - 1),
                        [("Steam", "Leaks_Pair", "A", 0.0), ("Steam", "Leaks_Pair", "B", 3.0)], interval=6.0)
        for k, pair in self.t["jets"]:
            mouth = at.at(16.5, k)
            for j, r in enumerate((20.5, 24.0, 27.5)):
                cx = r * math.cos(math.radians(k))
                cz = r * math.sin(math.radians(k))
                base = (cx + self.origin[0], y + self.origin[1], cz + self.origin[2])
                # Zone rouge au sol pendant l'annonce, comme les jets de flammes de The_Deepworks.
                warn = [vfx("", "Dungeon_Goblin_Mace_Slam_Warning", offset=(0, 0.1, 0), scale=GAS_WARNING_SCALE * 3.3,
                            duration=GAS_WARN)]
                hit = []
                if j == 1:  # une seule bouche joue les particules et le son
                    off = (mouth[0] + 0.5 - cx, 1.0, mouth[1] + 0.5 - cz)
                    warn += [vfx("", "Goblin_Decorative_Steam", offset=off, duration=GAS_WARN),
                             sound("", "SFX_Emit_Goblin_Steam_A")]
                    hit = [vfx("", "Dungeon_Goblin_Smoke_Pipe_Large", offset=off, duration=1.6),
                           vfx("", "Effect_Poison", offset=(0, 1, 0), duration=1.6),
                           sound("", "SFX_Env_Geyzer_Burst")]
                self.pulse(f"Leaks_Jet_{k:03d}_{j}", g, base, cylinder(3.3, 4), "Steam", "Leaks_Pair", pair,
                           warn=GAS_WARN, active=1.6, warn_fx=warn, hit_fx=hit,
                           hits=[status("Poison_T1", 6.0), damage(8, 0.8)])
        lever = self.t["lever"]
        self.usable("Leaks_Valve", g, lever, [
            sound("BLOCK_USED", "SFX_Lever_Metal_On"),
            sound("BLOCK_USED", "SFX_Emit_Goblin_Pipes_Activate", 0.4),
            toggle("DisableVolume", "BLOCK_USED", "Leaks_Controller", delay=0.5, radius=80),
            tags("BLOCK_USED", "Valve", "On", 0.5, match="Leaks_Shortcut", radius=80),
            tags("BLOCK_USED", "Valve", "On", 0.5, match="Leaks_Pipes", radius=80)], flag="Pulled")
        # La conduite de gaz s'éteint et les fuites de la tuyauterie se tarissent quand la vanne est fermée.
        pipes = self.t["valve_pipes"] + self.t["valve_leaks"]
        center, shape = self.bounds(pipes)
        self.add("Leaks_Pipes", g, center, shape, [
            replace("TAG_ADDED", [at.PIPE_GLOW], at.PIPE_GLOW, 0.2, to_state="Off"),
            replace("TAG_ADDED", [at.LEAK], "Empty", 0.4)],
            [tag_is("TAG_ADDED", "Valve", "On")], volume_tags={"Leaks_Pipes": "Open", "Valve": "Off"})
        self.gate("Leaks_Shortcut", g, self.t["shortcut_seal"], ["Valve"], [title("TAG_ADDED", "valve")])

    def greenhouse(self):
        g = self.group("Tower_Greenhouse_Spores", 6280509)
        for i, pos in enumerate(self.t["spores"]):
            self.add(f"Greenhouse_Spores_{i + 1}", g, self.foot(*pos), cylinder(2.5, 3), [
                vfx("ENTER", "Dungeon_Goblin_Spores_Green", offset=(0, 0.5, 0), duration=2.5),
                sound("ENTER", "SFX_Emit_Goblin_Steam_B"),
                status("Slow", 3.0, event="ENTER", delay=0.8)],
                [cooldown("ENTER", 5.0)], CancelDelayedOnExit=True)

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
        self.controller("Library_Books_Controller", g, self.world(0, y, 0), cylinder(at.R_IN, 13),
                        [("Books", "Library_Books", "", 0.0)], interval=3.0)
        for i, pos in enumerate(self.t["books"]):
            self.pulse(f"Library_Books_{i + 1}", g, self.foot(*pos), cylinder(1.6, 3), "Books", "Library_Books",
                       "Zone", warn=1.4, active=0.4,
                       warn_fx=[vfx("", "Dungeon_Goblin_Mace_Slam_Warning", offset=(0, 0.1, 0), duration=1.4)],
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
            self.pulse(f"Quadrant_{el}", g, center, shape, "Transmute", "Quadrant", el, warn=1.6, active=2.4,
                       warn_fx=[vfx("", warn_p, offset=o, duration=1.6) for o in spots],
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
                warn = [vfx("", "Fire_Trap_Preview", offset=(0, 0.1, 0), duration=1.5)]
                hit = [vfx("", "Fire_AoE", offset=(0, 0.2, 0), duration=1.6)]
                if j == 0:
                    warn.append(vfx("", "Fire_Charge_Charging1", offset=off, duration=1.5))
                    hit.append(sound("", "SFX_Emit_Goblin_Pipes_Flame_Ignite"))
                self.pulse(f"Wind_Flame_{a}_{j}", g, base, cylinder(2.0, 3), "Flame", "Wind_Flame", pair, warn=1.5,
                           active=1.6, warn_fx=warn, hit_fx=hit, hits=[status("Burn", 3.0), damage(12, 1.0)])
        for a, pair, cells in self.t["gusts"]:
            for j, cell in enumerate(cells):
                base = self.foot(*cell)
                # vers l'axe de la tour, donc contre son mur : jamais vers le vide
                d = math.hypot(base[0] - self.origin[0], base[2] - self.origin[2])
                push = (-(base[0] - self.origin[0]) / d * 7.0, 0.0, -(base[2] - self.origin[2]) / d * 7.0)
                warn = [vfx("", "Leaves_Oak_Wind", offset=(0, 1, 0), duration=1.0)]
                hit = [vfx("", "Wind", offset=(0, 1, 0), duration=1.8)]
                if j == 2:
                    hit.append(sound("", "SFX_Emit_Wind_Gusts"))
                self.pulse(f"Wind_Gust_{a}_{j}", g, base, cylinder(2.6, 3), "Gust", "Wind_Gust", pair, warn=1.0,
                           active=1.8, warn_fx=warn, hit_fx=hit, hits=[velocity(*push)])
        for i, cell in enumerate(self.t["strikes"]):
            self.pulse(f"Wind_Strike_{i + 1}", g, self.foot(*cell), cylinder(1.8, 3), "Strike", "Wind_Strike", "Zone",
                       warn=1.5, active=0.5,
                       warn_fx=[vfx("", "Dungeon_Goblin_Mace_Slam_Warning", offset=(0, 0.1, 0), duration=1.5)],
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
        - Codex_Collapse_<pan>, Collapse=On sous 50 % de vie : un pan d'étagères s'annonce puis s'effondre en éboulis
          (Nakasar_Codex_Rubble) qui réduisent l'arène ;
        - Codex_Arena, Reset=On quand le groupe a fui ou péri : les éboulis disparaissent et les pans se relèvent."""
        g = self.group("Tower_Codex", 9055202)
        c = self.t["codex"]
        cx, y, cz = c["center"]
        self.gate("Codex_Seal", g, c["seal"], ["Codex"], [title("TAG_ADDED", "codex")])
        warning = "Dungeon_Goblin_Mace_Slam_Warning"

        def spell(name, foot, radius, warn_fx, hit_fx, hits, warn=2.0, active=0.8):
            self.add(name, g, foot, cylinder(radius, 5), [
                sound("TAG_ADDED", "SFX_Crystal_Break"),
                vfx("TAG_ADDED", warning, offset=(0, 0.1, 0), scale=round(0.68 * radius, 2), duration=warn),
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
        spell("Codex_Fire", self.foot(cx, y, cz), 10, around((3, 6.5, 9), 6, "Fire_Trap_Preview", duration=2.0),
              around((0, 4, 8), 5, "Fire_AoE") + [sound("", "SFX_Emit_Goblin_Flame_Quadrant_Blast")],
              [damage(18, 1.0), status("Burn", 4.0)])
        # Onde de givre : autour du pupitre du chapitre, on s'en sort en passant de l'autre côté de la salle.
        for k, pos in enumerate(c["lecterns"]):
            spell(f"Codex_Frost_{k}", self.foot(*pos), 11, around((4, 8), 5, "Weapon_Frost_Mist", duration=2.0),
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
                           warn=1.6, active=0.5,
                           warn_fx=[vfx("", warning, offset=(0, 0.1, 0), scale=1.3, duration=1.6)],
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
                marks += [vfx("TAG_ADDED", warning, offset=offset, scale=2.0, duration=2.5),
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
        warning = "Dungeon_Goblin_Mace_Slam_Warning"
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
                           "Zone", warn=1.8, active=0.6,
                           warn_fx=[vfx("", warning, offset=(0, 0.1, 0), scale=1.3, duration=1.8),
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
        warning = "Dungeon_Goblin_Mace_Slam_Warning"
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
                    marks += [vfx("TAG_ADDED", warning, offset=offset, scale=2.0, duration=2.5),
                              vfx("TAG_ADDED", "Block_Break_Dust", 2.5, offset=offset)]
            self.add(f"Alchemist_Collapse_{i}", g, center, shape, [
                sound("TAG_ADDED", "SFX_Crystal_Break"), sound("TAG_ADDED", "SFX_Crystal_Break", 2.4), *marks,
                signal("TAG_ADDED", "Collapse", "Alchemist_Pile", str(i), radius=70.0),
                tags("TAG_ADDED", "Collapse", "Off", 3.0)],
                [tag_is("TAG_ADDED", "Collapse", "On")], volume_tags={"Collapse": "Off"})
            for layer, restore in ((y - 1, "Rock_Marble_Brick_Smooth"), (y - 2, "Rock_Marble_Brick")):
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
        check_ids(self.volumes)
        return self.volumes, self.groups


def check_ids(volumes):
    """Refuse un id du jeu qui ne serait pas dans les listes vérifiées (PARTICLES, SOUNDS, EFFECTS, BLOCKS, NPCS)."""
    known = {"ParticleSystem": PARTICLES, "SoundEvent": SOUNDS, "Effect": EFFECTS, "ToBlockType": BLOCKS,
             "BlockType": BLOCKS, "NpcType": NPCS}
    for v in volumes.values():
        for e in v["Effects"]:
            for field, ids in known.items():
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
    door, door_icon = TEXTURES / "Tower_Door.png", ICONS / "Tower_Door.png"
    door_img = door_texture()
    door_img.save(door)
    door_img.resize((64, 64), Image.NEAREST).save(door_icon)
    write_json(ITEMS / f"{at.DOOR}.json", door_item(door.relative_to(COMMON).as_posix(),
                                                    door_icon.relative_to(COMMON).as_posix()))
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
        for state in textures:
            valve_render(textures, uv, 512, state).save(preview / f"Valve_{state}.png")
    print("blocs des énigmes générés")


if __name__ == "__main__":
    main()
