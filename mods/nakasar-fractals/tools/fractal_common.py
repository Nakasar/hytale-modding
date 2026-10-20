"""Outils communs aux générateurs de fractales écrits après la Falaise (Inclassable, Volcanique) : prefab découpé en
tronçons, biome à plusieurs prefabs, modèles de PNJ fixes en boîtes, rôles fixes, textures à glyphes, particules,
icônes d'effets et sortie Java. La Falaise (generate_cliffside.py) garde ses propres fonctions.
"""
import json
import math

from PIL import Image, ImageDraw

import fractal_models as fm
import fractal_roles as fr
import generate_cliffside as gc
import generate_observatory as go

SERVER = go.SERVER
COMMON = go.COMMON
GROUND_Y = go.GROUND_Y
MODELS = gc.MODELS
ROLES = gc.ROLES
ROOTS = gc.ROOTS
EFFECTS = gc.EFFECTS
NPC_MODELS = gc.NPC_MODELS
STATUS_ICONS = gc.STATUS_ICONS
SECTION = 64   # longueur (z) d'un tronçon de prefab


def write_json(path, doc):
    fr.write_json(path, doc)


# --- prefab en tronçons -----------------------------------------------------------------------------

def split_sections(p, z_min):
    """Découpe le prefab `p` (coordonnées absolues) en tronçons de SECTION blocs le long de z ; rend
    [(nom, ancre_z, prefab relatif)]. Chaque tronçon est posé à (0, GROUND_Y, ancre_z)."""
    groups = {}
    for (x, y, z), value in p.blocks.items():
        k = (z - z_min) // SECTION
        groups.setdefault(k, {})[(x, y, z)] = value
    out = []
    for k in sorted(groups):
        anchor = z_min + k * SECTION + SECTION // 2
        part = go.Prefab()
        for (x, y, z), (name, rot) in groups[k].items():
            part.set(x, y, z - anchor, name, rot)
        out.append((f"Section_{k:02d}", anchor, part))
    return out


def biome(instance, prefab_dir, sections, tint):
    """Biome vide qui pose chaque tronçon à son ancre (x = 0, y = GROUND_Y, z = ancre)."""
    doc = go.biome(instance, "unused")
    doc["Props"] = [{
        "Runtime": 0,
        "ContextPrecision": "Prop",
        "PropDistribution": {
            "Type": "Assigned",
            "OverrideAllProps": True,
            "PropDistribution": {"Type": "Positions", "Positions": {"Type": "List", "Positions": [
                {"X": 0, "Y": GROUND_Y, "Z": anchor}]}},
            "Assignments": {"Type": "Constant", "Prop": {"Type": "Prefab", "WeightedPrefabPaths": [
                {"Path": f"{go.PREFABS}/{prefab_dir}/{name}", "Weight": 1.0}]}},
        },
    } for name, anchor, _ in sections]
    doc["TintProvider"] = {"Type": "Constant", "Color": tint}
    return doc


def write_instance(instance, display, prefab_dir, sections, spawn, tint):
    counts = {}
    old = SERVER / "Prefabs" / go.PREFABS / prefab_dir
    if old.exists():
        for d in old.iterdir():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    for name, _, part in sections:
        counts[name] = part.write(SERVER / "Prefabs" / go.PREFABS / prefab_dir / name / f"{name}.prefab.json")
    world_spawn = (spawn[0], GROUND_Y + spawn[1], spawn[2])
    write_json(SERVER / "Instances" / instance / "instance.bson",
               go.instance(instance, display, instance, portal=False, spawn=world_spawn, removal=60))
    write_json(SERVER / "HytaleGenerator/Biomes" / f"{instance}.json", biome(instance, prefab_dir, sections, tint))
    write_json(SERVER / "HytaleGenerator/WorldStructures" / f"{instance}.json", go.world_structure(instance, world_spawn))
    return counts


# --- géométrie ------------------------------------------------------------------------------------

def pick(options, x, y, z):
    return options[(x * 73856093 ^ y * 83492791 ^ z * 19349663) % len(options)]


def disc(p, cx, cz, r, stand, top, under=None, depth=0):
    """Disque de rayon `r` dont le dessus est en stand - 1 ; dessous en cône de `depth` blocs."""
    for x in range(cx - r - 1, cx + r + 2):
        for z in range(cz - r - 1, cz + r + 2):
            d = math.hypot(x - cx, z - cz)
            if d > r + 0.5:
                continue
            p.set(x, stand - 1, z, top(x, z) if callable(top) else top)
            if under and depth:
                bottom = stand - 2 - int(depth * (1 - (d / (r + 0.5)) ** 1.6))
                for y in range(bottom, stand - 1):
                    p.set(x, y, z, pick(under, x, y, z))


def box_floor(p, x0, x1, z0, z1, stand, block, edge=None):
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for z in range(min(z0, z1), max(z0, z1) + 1):
            border = x in (x0, x1) or z in (z0, z1)
            p.set(x, stand - 1, z, edge if edge and border else block(x, z) if callable(block) else block)


def walls(p, x0, x1, z0, z1, y0, y1, block, openings=()):
    """Murs sur le pourtour de la boîte (x0..x1, z0..z1), de y0 à y1 ; `openings` : cases (x, z) laissées libres."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            if x not in (x0, x1) and z not in (z0, z1):
                continue
            if (x, z) in openings:
                continue
            for y in range(y0, y1 + 1):
                p.set(x, y, z, block(x, y, z) if callable(block) else block)


def step_blocks(p, x, z, level, full, half):
    base = math.floor(level)
    p.set(x, base - 1, z, full)
    if level - base >= 0.5:
        p.set(x, base, z, half)


# --- blocs et textures ----------------------------------------------------------------------------

def texture(path, base, accent, glyph, alpha=255):
    img = Image.new("RGBA", (32, 32), base + (alpha,))
    d = ImageDraw.Draw(img)
    dark = tuple(int(c * 0.65) for c in base) + (255,)
    acc = accent + (255,)
    d.rectangle((0, 0, 31, 31), outline=dark if alpha == 255 else acc)
    if glyph == "console":
        d.rectangle((5, 6, 26, 20), fill=dark, outline=acc)
        for k in range(3):
            d.rectangle((8 + k * 6, 23, 11 + k * 6, 27), fill=acc)
        d.line((8, 13, 23, 13), fill=acc, width=2)
    elif glyph == "fan":
        d.ellipse((4, 4, 27, 27), outline=acc, width=2)
        for k in range(4):
            a = math.radians(k * 90 + 20)
            d.polygon(((16, 16), (16 + math.cos(a) * 11, 16 + math.sin(a) * 11),
                       (16 + math.cos(a + 0.6) * 11, 16 + math.sin(a + 0.6) * 11)), fill=acc)
    elif glyph in ("battery", "battery_on"):
        d.rectangle((9, 6, 22, 27), outline=acc, width=2)
        d.rectangle((13, 3, 18, 6), fill=acc)
        if glyph == "battery_on":
            d.rectangle((12, 9, 19, 24), fill=acc)
    elif glyph == "glimmer":
        d.line((4, 28, 28, 4), fill=acc, width=1)
        d.line((4, 16, 16, 4), fill=acc, width=1)
    elif glyph == "pylon":
        d.polygon(((16, 3), (24, 16), (16, 29), (8, 16)), outline=acc)
        d.line((16, 8, 16, 24), fill=acc, width=2)
    elif glyph == "fire":
        d.polygon(((16, 4), (24, 20), (16, 28), (8, 20)), fill=acc)
        d.polygon(((16, 12), (20, 21), (16, 25), (12, 21)), fill=(255, 240, 160, 255))
    elif glyph == "rune":
        d.ellipse((6, 6, 25, 25), outline=acc, width=2)
        d.line((16, 8, 16, 24), fill=acc, width=2)
        d.line((10, 13, 22, 19), fill=acc, width=2)
    elif glyph == "cracks":
        for (a, b, c, e) in ((3, 8, 14, 15), (14, 15, 12, 28), (14, 15, 27, 10), (20, 13, 29, 24)):
            d.line((a, b, c, e), fill=acc, width=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


def write_block(lang, name, tex, base, accent, glyph, light=None, use=None, solid=True, alpha=255, opacity=None,
                quality="Technical"):
    img = texture(COMMON / go.TEXTURES / f"{tex}.png", base, accent, glyph, alpha)
    go.icon(COMMON / go.ICONS / f"{tex}.png", img)
    doc = go.block_item(name, tex, light, use, solid=solid, particle=go.hexcolor(accent), quality=quality)
    doc["TranslationProperties"] = {"Name": f"{lang}.items.{name}.name", "Description": f"{lang}.items.{name}.description"}
    if opacity:
        doc["BlockType"]["Opacity"] = opacity
        doc["BlockType"]["BlockParticleSetId"] = "Crystal"
        doc["BlockType"]["BlockSoundSetId"] = "Crystal"
    write_json(go.ITEMS / f"{name}.json", doc)


def use_interaction(action, comment):
    return {"$Comment": comment, "Type": "Nakasar_Fractal_Use", "Action": action}


# --- effets ----------------------------------------------------------------------------------------

def status_icon(path, color, glyph):
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    d.ellipse((6, 6, 121, 121), fill=(26, 20, 34, 255), outline=c, width=6)
    if glyph == "plus":
        d.rectangle((56, 30, 72, 98), fill=c)
        d.rectangle((30, 56, 98, 72), fill=c)
    elif glyph == "minus":
        d.rectangle((30, 56, 98, 72), fill=c)
    elif glyph == "feather":
        d.polygon(((34, 98), (90, 30), (98, 38), (42, 104)), fill=c)
        for k in range(4):
            d.line((50 + k * 10, 80 - k * 12, 40 + k * 10, 66 - k * 12), fill=(26, 20, 34, 255), width=4)
    elif glyph == "flame":
        d.polygon(((64, 20), (92, 70), (64, 108), (36, 70)), fill=c)
        d.polygon(((64, 56), (78, 80), (64, 100), (50, 80)), fill=(255, 236, 160, 255))
    elif glyph == "feet":
        for x in (44, 78):
            d.ellipse((x - 12, 40, x + 12, 96), fill=c)
        d.polygon(((30, 108), (64, 84), (98, 108)), fill=(255, 140, 60, 255))
    elif glyph == "stone":
        d.polygon(((40, 40), (88, 34), (98, 80), (60, 100), (30, 78)), fill=c)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --- particules ---------------------------------------------------------------------------------------

def particle_files(systems, generator, cull=72):
    out = {}
    for sid, (comment, spawners) in systems.items():
        out[f"{sid}.particlesystem"] = {
            "$Comment": f"{comment} Généré par tools/{generator}.",
            "Spawners": [{"SpawnerId": f"{sid}_{suffix}", "PositionOffset": {"Y": y}} for suffix, _, y in spawners],
            "CullDistance": cull,
        }
        for suffix, doc, _ in spawners:
            out[f"{sid}_{suffix}.particlespawner"] = doc
    return out


# --- modèles et rôles -----------------------------------------------------------------------------

def character_model(name, parts, seed, comment, eye, hitbox, light=None, scale=1.0, tex_w=256):
    """Modèle de PNJ en boîtes (64 unités par bloc), sans animation : `hitbox` = (demi-largeur, hauteur)."""
    atlas, uv = fm.build_atlas(parts, seed, tex_w=tex_w)
    out = COMMON / NPC_MODELS / name
    out.mkdir(parents=True, exist_ok=True)
    atlas.save(out / "Texture.png")
    model = fm.build_model("Body", parts, uv)
    model["format"] = "character"
    (out / "Model.blockymodel").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    w, h = hitbox
    doc = {
        "$Comment": comment,
        "Model": f"{NPC_MODELS}/{name}/Model.blockymodel",
        "Texture": f"{NPC_MODELS}/{name}/Texture.png",
        "EyeHeight": eye,
        "HitBox": {"Max": {"X": w, "Y": h, "Z": w}, "Min": {"X": -w, "Y": 0, "Z": -w}},
        "MinScale": scale, "MaxScale": scale,
    }
    if light:
        doc["Light"] = light
    return doc


def static_role(lang, role_id, comment, generator, hp, attitude="Hostile", foe=True):
    doc = {
        "$Comment": f"{comment} Généré par tools/{generator}.",
        "Type": "Generic",
        "Appearance": role_id,
        "NameTranslationKey": npc_name(lang, role_id),
        "MaxHealth": hp,
        "StartState": "Idle",
        "DefaultPlayerAttitude": attitude,
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "SpawnLockTime": 0.2,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
    }
    if foe:
        doc["DisableDamageGroups"] = [fr.FOES]
    return doc


def npc_name(lang, role_id):
    return f"{lang}.npc.{role_id.removeprefix('Nakasar_Fractal_')}.name"


def fly(speed, low=1, high=8):
    return [{"Type": "Fly", "MaxHorizontalSpeed": speed, "MaxClimbSpeed": 3, "MaxSinkSpeed": 3, "Acceleration": 3,
             "Deceleration": 3, "Gravity": 1, "MinHeightOverGround": low, "MaxHeightOverGround": high}]


def root(name):
    return f"Root_Nakasar_Fractal_NPC_{name}"


def write_roots(melee_roots, ranged_roots):
    for name in melee_roots:
        write_json(ROOTS / f"{root(name)}.json", fr.melee_tag(f"Nakasar_Fractal_{name}"))
    for name in ranged_roots:
        write_json(ROOTS / f"{root(name)}.json", fr.ranged_tag(f"Nakasar_Fractal_{name}"))


def add_foes(roles):
    group = SERVER / "NPC/Groups" / f"{fr.FOES}.json"
    doc = json.loads(group.read_text(encoding="utf-8"))
    doc["IncludeRoles"] = sorted(set(doc.get("IncludeRoles", [])) | set(roles))
    write_json(group, doc)


def windup(seconds, sound="SFX_Spear_Throw_Charge", anim_set=None, anim=None):
    effects = {"WorldSoundEventId": sound}
    if anim_set:
        effects.update({"ItemPlayerAnimationsId": anim_set, "ItemAnimationId": anim})
    return {"Type": "Simple", "RunTime": seconds, "Effects": effects}


# --- Java -----------------------------------------------------------------------------------------

def jd(v):
    return f"{float(v)}"


def jpoint(at, center=True):
    """Pieds (centre du bloc si entier) en coordonnées du monde."""
    x, y, z = at
    if center and float(x).is_integer():
        x += 0.5
    if center and float(z).is_integer():
        z += 0.5
    return "{" + f"{jd(x)}, {jd(GROUND_Y + y)}, {jd(z)}" + "}"


def jpoints(points, center=True):
    return "{" + ", ".join(jpoint(p, center) for p in points) + "}"


def jblock(at):
    return "{" + f"{at[0]}, {GROUND_Y + at[1]}, {at[2]}" + "}"


def jblocks(cells):
    return "{" + ", ".join(jblock(c) for c in cells) + "}"


def jbox(x0, x1, y0, y1, z0, z1):
    return f"new Box({min(x0, x1)}, {max(x0, x1)}, {GROUND_Y + y0}, {GROUND_Y + y1}, {min(z0, z1)}, {max(z0, z1)})"


def top_view(prefab, path, color_of, scale=3):
    best = {}
    for (x, y, z), (name, _) in prefab.blocks.items():
        if name == go.AIR:
            continue
        if (x, z) not in best or y > best[(x, z)][0]:
            best[(x, z)] = (y, name)
    xs = [k[0] for k in best]
    zs = [k[1] for k in best]
    ys = [v[0] for v in best.values()]
    img = Image.new("RGB", ((max(xs) - min(xs) + 1) * scale, (max(zs) - min(zs) + 1) * scale), (12, 14, 34))
    d = ImageDraw.Draw(img)
    for (x, z), (y, name) in best.items():
        c = color_of(name)
        shade = max(0.35, min(1.0, 0.35 + (y - min(ys)) / max(1, max(ys) - min(ys)) * 0.65))
        c = tuple(int(v * shade) for v in c)
        px, pz = (x - min(xs)) * scale, (z - min(zs)) * scale
        d.rectangle((px, pz, px + scale - 1, pz + scale - 1), fill=c)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --- objets tenus -----------------------------------------------------------------------------------

ITEM_MODELS = "Items/Nakasar/Fractals"
OBJECTS = SERVER / "Item/Items/Nakasar/Fractals"


def held_item(lang, item_id, model, parts, seed, center, scale, quality="Rare", stack=1, extra=None):
    """Objet en boîtes (modèle, atlas, icône rendue) que l'on porte dans l'inventaire ; rend le JSON de l'objet."""
    fm.write_item_model(model, parts, COMMON / ITEM_MODELS, COMMON / go.ICONS, seed, center, scale)
    doc = {
        "TranslationProperties": {"Name": f"{lang}.items.{item_id}.name", "Description": f"{lang}.items.{item_id}.description"},
        "Icon": f"{go.ICONS}/{model}.png",
        "Model": f"{ITEM_MODELS}/{model}.blockymodel",
        "Texture": f"{ITEM_MODELS}/{model}.png",
        "Quality": quality,
        "Categories": ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": stack,
    }
    doc.update(extra or {})
    return doc


def effect(lang, effect_id, comment, icon=None, duration=2.0, debuff=False, **extra):
    doc = {"$Comment": comment, "Name": f"{lang}.effects.{effect_id}"}
    if debuff:
        doc["Debuff"] = True
    if icon:
        doc["StatusEffectIcon"] = f"{STATUS_ICONS}/{icon}.png"
    doc.update(extra)
    doc.update({"OverlapBehavior": "Overwrite", "Infinite": False, "Duration": duration})
    return doc


def cause(comment, color):
    return {"$Comment": comment, "BypassResistances": True, "DurabilityLoss": False, "StaminaLoss": False,
            "DamageTextColor": color}


class Lang:
    """Entrées de langue en français et en anglais."""

    def __init__(self):
        self.fr, self.en = {}, {}

    def put(self, key, f, e):
        self.fr[key], self.en[key] = f, e

    def item(self, item_id, nf, df, ne, de):
        self.put(f"items.{item_id}.name", nf, ne)
        self.put(f"items.{item_id}.description", df, de)

    def npc(self, role_id, f, e):
        self.put(f"npc.{role_id.removeprefix('Nakasar_Fractal_')}.name", f, e)

    def write(self, lang):
        go.write_lang(SERVER / "Languages/fr-FR" / f"{lang}.lang", self.fr)
        go.write_lang(SERVER / "Languages/en-US" / f"{lang}.lang", self.en)
