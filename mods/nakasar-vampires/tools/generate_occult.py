#!/usr/bin/env python3
"""Génère les assets de la voie occulte (joueur vampire) : objets, recettes de l'autel, effets, sons.

Usage : python3 mods/nakasar-vampires/tools/generate_occult.py [--preview DOSSIER]

Le code Java est dans dev.nakasar.hytale.vampires.vampirism (VampireSystem, VampireDamageSystem,
interactions Nakasar_VampireRitual, Nakasar_BloodFeed, Nakasar_DrinkBlood). Ce script écrit :

- les modèles, textures et icônes des objets occultes (fioles, potions, calice, encensoir, notes,
  ingrédients), avec le moteur de generate_altar.py (boîtes, 32 unités = 1 bloc) ;
- les objets (Server/Item/Items/Occult/Nakasar), leurs interactions de consommation et leurs recettes
  à l'autel sacrificiel (onglets Sang et Rituels, paliers 2 à 4) ;
- les effets de statut (paliers de faim de sang, soleil, protections, rituels) et leurs icônes,
  l'éblouissement du soleil (ScreenEffects), les causes de dégâts du soleil et de la lumière ;
- les sons (battement de cœur, rituel, gorgée), synthétisés puis encodés en Ogg Vorbis par ffmpeg ;
- les listes de butin des morts-vivants du Comté qui donnent des cendres.

Les vêtements occultes héritent (Parent) de vêtements vanilla : seul leur nom change, la protection
solaire est lue par VampireSystem d'après leur id. La rune Nova de sang reprend le modèle des runes vanilla.
"""
import json
import math
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import generate_altar as ga

ROOT = ga.ROOT
SERVER = ROOT / "Server"
COMMON = ROOT / "Common"
ITEMS = SERVER / "Item/Items/Occult/Nakasar"
RECIPES = SERVER / "Item/Recipes/Nakasar/Occult"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Occult"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/Occult"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Occult"
DAMAGE = SERVER / "Entity/Damage/Nakasar"
SOUND_EVENTS = SERVER / "Audio/SoundEvents/Nakasar"
DROPS = SERVER / "Drops/Nakasar/Occult"
MODELS = COMMON / "Items/Nakasar/Occult"
ICONS = COMMON / "Icons/Items/Nakasar/Occult"
STATUS = COMMON / "UI/StatusEffects/Nakasar/Occult"
SCREEN = COMMON / "ScreenEffects/Nakasar"
CATEGORIES = COMMON / "Icons/CraftingCategories/Nakasar"
SOUNDS = COMMON / "Sounds/Nakasar"

LANG = "nakasar_vampire"
ALTAR = "Nakasar_Sacrificial_Altar"
CAT_BLOOD = "Nakasar_Altar_Blood"
CAT_RITUALS = "Nakasar_Altar_Rituals"
CAT_RUNES = "Nakasar_Altar_Runes"

random.seed(13)

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
GLASS = (196, 214, 222)
CORK = (150, 108, 70)
BLOOD = (128, 14, 26)
BLOOD_LIGHT = (190, 36, 48)
ASH = (128, 124, 122)
ASH_DARK = (88, 84, 84)
LEATHER = (98, 66, 46)
GOLD = (212, 170, 72)
GOLD_DARK = (150, 112, 44)
RUBY = (196, 30, 52)
SILVER = (196, 204, 214)
SILVER_DARK = (128, 136, 150)
PAPER = (226, 214, 180)
PAPER_DARK = (180, 160, 120)
INK = (60, 30, 30)
SUN = [None, (224, 150, 60), (236, 112, 40), (255, 222, 120)]


def flat(color, top=None):
    return lambda w, h, kind, face: ga.paint_flat(w, h, color, kind, top_color=top)


def liquid(color):
    """Verre teinté : la couleur du liquide, un reflet clair sur les côtés."""
    def painter(w, h, kind, face):
        img = ga.paint_flat(w, h, color, kind, top_color=ga.shade(color, 1.2))
        if kind == "side" and w >= 3 and h >= 4:
            d = ImageDraw.Draw(img)
            d.line((1, 1, 1, h - 2), fill=ga.mix(color, (255, 255, 255), 0.55) + (255,))
        return img
    return painter


def label(color, band):
    """Fiole de potion : liquide et étiquette de papier au milieu."""
    def painter(w, h, kind, face):
        img = liquid(color)(w, h, kind, face)
        if kind == "side" and h >= 6:
            d = ImageDraw.Draw(img)
            y = h // 2 - 1
            d.rectangle((0, y, w - 1, y + 2), fill=PAPER + (255,))
            d.point((w // 2, y + 1), fill=band + (255,))
        return img
    return painter


def scroll(w, h, kind, face):
    img = ga.paint_flat(w, h, PAPER, kind, top_color=PAPER)
    if kind == "top":
        d = ImageDraw.Draw(img)
        for y in range(2, h - 1, 2):
            d.line((2, y, w - 3 - (y * 3) % 4, y), fill=INK + (255,))
    return img


def cup_top(w, h, kind, face):
    if kind == "top":
        img = Image.new("RGBA", (w, h), GOLD_DARK + (255,))
        ImageDraw.Draw(img).rectangle((1, 1, w - 2, h - 2), fill=BLOOD + (255,))
        return img
    return ga.paint_flat(w, h, GOLD, kind, top_color=GOLD)


def bottle(color, band=None, big=True):
    """Pièces d'une fiole : panse, épaule, col et bouchon."""
    body = label(color, band) if band else liquid(color)
    if big:
        return [
            ("Body", (0, 4.5, 0), (8, 9, 8), 0, body, "flat"),
            ("Shoulder", (0, 10, 0), (6, 2, 6), 0, liquid(ga.mix(color, GLASS, 0.4)), "flat"),
            ("Neck", (0, 12.5, 0), (3, 3, 3), 0, flat(GLASS), "flat"),
            ("Cork", (0, 15, 0), (4, 2, 4), 0, flat(CORK), "flat"),
        ]
    return [
        ("Body", (0, 3.5, 0), (5, 7, 5), 0, body, "flat"),
        ("Neck", (0, 8, 0), (2, 2, 2), 0, flat(GLASS), "flat"),
        ("Cork", (0, 9.5, 0), (3, 1, 3), 0, flat(CORK), "flat"),
    ]


MODEL_PARTS = {
    "Blood_Drop": bottle(BLOOD, big=False),
    "Undead_Ash": [
        ("Sack", (0, 3.5, 0), (8, 7, 8), 0, flat(ASH, ASH_DARK), "flat"),
        ("Sack_Neck", (0, 8, 0), (4, 2, 4), 0, flat(ASH_DARK), "flat"),
        ("String", (0, 9.5, 0), (5, 1, 5), 0, flat(LEATHER), "flat"),
        ("Tuft", (0, 10.5, 0), (3, 1, 3), 0, flat(ASH), "flat"),
    ],
    "Manor_Relic": [
        ("Base", (0, 2.5, 0), (10, 5, 7), 0, flat(GOLD, GOLD_DARK), "flat"),
        ("Lid", (0, 6, 0), (11, 2, 8), 0, flat(GOLD_DARK, GOLD), "flat"),
        ("Gem", (0, 8.5, 0), (3, 3, 3), 45, flat(RUBY), "fullbright"),
        ("Foot_L", (-4, 0.5, 0), (2, 1, 8), 0, flat(GOLD_DARK), "flat"),
        ("Foot_R", (4, 0.5, 0), (2, 1, 8), 0, flat(GOLD_DARK), "flat"),
    ],
    "Blood_Vial": bottle(BLOOD, band=BLOOD_LIGHT),
    "Sun_Potion_1": bottle(SUN[1], band=(200, 120, 30)),
    "Sun_Potion_2": bottle(SUN[2], band=(150, 60, 20)),
    "Sun_Potion_3": bottle(SUN[3], band=(255, 255, 255)),
    "Ritual_Chalice": [
        ("Foot", (0, 0.5, 0), (8, 1, 8), 0, flat(GOLD_DARK, GOLD), "flat"),
        ("Stem", (0, 4, 0), (2, 6, 2), 0, flat(GOLD), "flat"),
        ("Knot", (0, 4, 0), (4, 2, 4), 45, flat(GOLD_DARK), "flat"),
        ("Gem", (0, 4, 2.2), (1.5, 1.5, 0.5), 0, flat(RUBY), "fullbright"),
        ("Cup", (0, 10, 0), (8, 6, 8), 0, cup_top, "flat"),
        ("Rim", (0, 13.5, 0), (9, 1, 9), 0, flat(GOLD_DARK, BLOOD), "flat"),
    ],
    "Purification_Censer": [
        ("Base", (0, 1, 0), (6, 2, 6), 0, flat(SILVER_DARK), "flat"),
        ("Body", (0, 5, 0), (8, 6, 8), 0, flat(SILVER, SILVER_DARK), "flat"),
        ("Lid", (0, 9, 0), (6, 2, 6), 0, flat(SILVER_DARK, SILVER), "flat"),
        ("Flame", (0, 10.5, 0), (2, 1, 2), 0, flat((236, 244, 255)), "fullbright"),
        ("Knob", (0, 12, 0), (2, 2, 2), 0, flat(SILVER), "flat"),
        ("Chain", (0, 17, 0), (1, 8, 1), 0, flat(SILVER_DARK), "flat"),
    ],
    "Note": [
        ("Sheet", (0, 0.5, 0), (12, 1, 9), 0, scroll, "flat"),
        ("Seal", (3, 1.25, 2.5), (2, 0.5, 2), 0, flat(BLOOD), "flat"),
    ],
}


def build_models(preview):
    MODELS.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    for name, parts in MODEL_PARTS.items():
        ga.PARTS = parts
        ga.TEX_W, ga.TEX_H = 64, 64
        atlas, uv = ga.build_atlas()
        atlas.save(MODELS / f"{name}.png")
        model = ga.build_model(uv)
        model["nodes"][0]["name"] = name
        (MODELS / f"{name}.blockymodel").write_text(json.dumps(model, indent=2) + "\n")
        top = max(c[1] + s[1] / 2 for _, c, s, *_ in parts)
        span = max(max(s[0], s[2]) for _, c, s, *_ in parts)
        scale = min(200 / max(top, 1), 170 / max(span, 1))
        big = ga.render(atlas, uv, 256, yaw=-35, pitch=28, scale=scale, center=(0, top / 2, 0))
        big.resize((64, 64), Image.LANCZOS).save(ICONS / f"{name}.png")
        if preview:
            ga.render(atlas, uv, 512, yaw=-35, pitch=28, scale=scale * 2, center=(0, top / 2, 0)).save(
                preview / f"occult_{name}.png")


# --------------------------------------------------------------------------
# Icônes d'effets, onglets de l'autel, éblouissement
# --------------------------------------------------------------------------

def disc(size, fill, outline):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, size - 6, size - 6), fill=fill + (235,), outline=outline + (255,), width=6)
    return img, d


def drop(d, c, r, color):
    """Goutte de sang centrée en (c, c) ; color RVB, ou un entier sur un masque."""
    ink = color if isinstance(color, int) else color + (255,)
    d.polygon([(c, c - r * 1.5), (c + r * 0.85, c), (c - r * 0.85, c)], fill=ink)
    d.ellipse((c - r, c - r * 0.6, c + r, c + r * 1.4), fill=ink)


def sun_disc(d, c, r, color):
    for k in range(12):
        a = math.radians(30 * k)
        d.line((c + math.cos(a) * r * 1.15, c + math.sin(a) * r * 1.15,
                c + math.cos(a) * r * 1.7, c + math.sin(a) * r * 1.7), fill=color + (255,), width=6)
    d.ellipse((c - r, c - r, c + r, c + r), fill=color + (255,))


def status_icons(size=128):
    STATUS.mkdir(parents=True, exist_ok=True)
    c = size // 2
    # Faim de sang : une goutte qui se vide palier après palier.
    for name, fill in [("Blood_Sated", 1.0), ("Blood_Hunger_3", 0.75), ("Blood_Hunger_2", 0.5),
                       ("Blood_Hunger_1", 0.25), ("Blood_Starving", 0.0)]:
        img, d = disc(size, (40, 10, 16), (196, 40, 52) if fill > 0 else (120, 120, 120))
        drop(d, c, 30, (70, 30, 34))
        if fill > 0:
            mask = Image.new("L", (size, size), 0)
            drop(ImageDraw.Draw(mask), c, 30, 255)
            level = int(c + 42 - 84 * fill)
            ImageDraw.Draw(mask).rectangle((0, 0, size, level), fill=0)
            red = Image.new("RGBA", (size, size), (200, 24, 40, 255))
            img.paste(red, (0, 0), mask)
        if fill == 0:
            # cœur barré : affamé
            d.line((30, 30, size - 30, size - 30), fill=(230, 230, 230, 255), width=8)
        img.save(STATUS / f"{name}.png")
    img, d = disc(size, (90, 40, 10), (255, 200, 90))
    sun_disc(d, c, 22, (255, 214, 110))
    img.save(STATUS / "Sunburn.png")
    for level in (1, 2, 3):
        img, d = disc(size, (30, 26, 40), SUN[level])
        sun_disc(d, c, 20, SUN[level])
        # voile : un croissant sombre qui masque le soleil, plus grand à chaque niveau
        shift = 30 - 8 * level
        d.ellipse((c - 30 + shift, c - 30, c + 30 + shift, c + 30), fill=(30, 26, 40, 255))
        for k in range(level):
            d.ellipse((24 + 16 * k, size - 30, 34 + 16 * k, size - 20), fill=(255, 255, 255, 255))
        img.save(STATUS / f"Sun_Protection_{level}.png")
    img, d = disc(size, (30, 6, 12), (160, 20, 40))
    # deux crocs
    for x in (c - 16, c + 16):
        d.polygon([(x - 9, c - 18), (x + 9, c - 18), (x, c + 26)], fill=(240, 236, 226, 255))
    drop(d, c + 16, 6, (200, 24, 40))
    img.save(STATUS / "Vampire_Awakening.png")
    img, d = disc(size, (40, 44, 60), (230, 240, 255))
    sun_disc(d, c, 18, (255, 250, 230))
    img.save(STATUS / "Purified.png")
    img, d = disc(size, (30, 50, 24), (140, 190, 90))
    for k in range(3):
        d.arc((26 + 8 * k, 30 + 14 * k, size - 26 - 8 * k, 60 + 14 * k), 200, 340, fill=(170, 220, 110, 255), width=7)
    img.save(STATUS / "Blood_Nausea.png")


def screen_effects():
    """Éblouissement du soleil : voile chaud plus fort vers le haut et les bords de l'écran."""
    SCREEN.mkdir(parents=True, exist_ok=True)
    w, h = 512, 288
    for name, strength in [("Sun_Glare", 1.0), ("Sun_Glare_Light", 0.5)]:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        for y in range(h):
            for x in range(w):
                dx = (x - w / 2) / (w / 2)
                dy = (y - h * 0.62) / (h * 0.62)
                edge = min(1.0, math.sqrt(dx * dx + dy * dy))
                top = max(0.0, 1.0 - y / h)
                a = (0.16 + 0.34 * edge ** 2 + 0.22 * top ** 2) * strength
                px[x, y] = (255, 236, 196, int(255 * min(0.75, a)))
        img.filter(ImageFilter.GaussianBlur(6)).save(SCREEN / f"{name}.png")


def category_icons():
    CATEGORIES.mkdir(parents=True, exist_ok=True)
    blood = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    drop(ImageDraw.Draw(blood), 32, 16, (190, 24, 40))
    blood.save(CATEGORIES / "Blood.png")
    ritual = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(ritual)
    d.polygon([(32, 6), (39, 25), (58, 25), (43, 37), (49, 57), (32, 45), (15, 57), (21, 37), (6, 25), (25, 25)],
              outline=(196, 30, 52, 255), width=4)
    d.ellipse((24, 24, 40, 40), fill=(120, 14, 26, 255))
    ritual.save(CATEGORIES / "Rituals.png")


# --------------------------------------------------------------------------
# Sons : synthèse (wave 16 bits mono) puis Ogg Vorbis
# --------------------------------------------------------------------------
RATE = 44100


def thump(t, freq, decay):
    return math.sin(2 * math.pi * freq * t * (1 - 0.3 * t)) * math.exp(-t * decay)


def heartbeat():
    """« Lub-dub » sourd : deux coups graves, le second plus faible."""
    n = int(RATE * 0.75)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        if t < 0.25:
            v += 0.9 * thump(t, 52, 18)
        if t >= 0.2:
            v += 0.6 * thump(t - 0.2, 64, 22)
        out.append(v)
    return out


def ritual():
    """Bourdon grave et montée inquiétante, deux secondes et demie."""
    n = int(RATE * 2.5)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.4) * min(1.0, (2.5 - t) / 0.8)
        f = 55 + 30 * t
        v = 0.45 * math.sin(2 * math.pi * f * t) + 0.25 * math.sin(2 * math.pi * f * 1.5 * t)
        v += 0.15 * math.sin(2 * math.pi * 220 * t) * math.sin(2 * math.pi * 3 * t)
        v += 0.1 * (random.random() * 2 - 1) * env
        out.append(v * env)
    return out


def drink():
    """Trois gorgées : petits glouglous filtrés."""
    n = int(RATE * 0.8)
    out = []
    for i in range(n):
        t = i / RATE
        v = 0.0
        for k, start in enumerate((0.0, 0.25, 0.5)):
            u = t - start
            if 0 <= u < 0.2:
                v += 0.6 * math.sin(2 * math.pi * (300 - 600 * u) * u) * math.exp(-u * 14)
        out.append(v)
    return out


def write_ogg(samples, path):
    peak = max(1e-6, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(32000 * s / peak)) for s in samples)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "s.wav"
        with open(wav, "wb") as f:
            f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16))
            f.write(b"data" + struct.pack("<I", len(data)) + data)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "4",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", str(path)],
                       check=True)


SOUNDS_DEF = {
    # id : (fichier, générateur, volume dB, distance max)
    "SFX_Nakasar_Heartbeat": ("Heartbeat.ogg", heartbeat, -2, 16),
    "SFX_Nakasar_Ritual": ("Ritual.ogg", ritual, 0, 24),
    "SFX_Nakasar_Drink": ("Drink.ogg", drink, -4, 12),
}


def build_sounds():
    SOUNDS.mkdir(parents=True, exist_ok=True)
    for sound_id, (file, gen, volume, distance) in SOUNDS_DEF.items():
        write_ogg(gen(), SOUNDS / file)
        write(SOUND_EVENTS / f"{sound_id}.json", {
            "Volume": volume,
            "MaxDistance": distance,
            "Layers": [{"Files": [f"Sounds/Nakasar/{file}"], "Volume": 0}],
        })


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def names(item_id):
    return {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"}


def item(item_id, model, quality="Uncommon", stack=25, interactions=None, scale=1.0, categories=None):
    data = {
        "TranslationProperties": names(item_id),
        "Icon": f"Icons/Items/Nakasar/Occult/{model}.png",
        "Model": f"Items/Nakasar/Occult/{model}.blockymodel",
        "Texture": f"Items/Nakasar/Occult/{model}.png",
        "Quality": quality,
        "Categories": categories or ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "Scale": scale,
        "MaxStack": stack,
    }
    if interactions:
        data["Interactions"] = interactions
    write(ITEMS / f"{item_id}.json", data)


# Animation de boisson des potions du jeu (Potion_Template, Assets.zip 0.7.2).
DRINK_ANIMATIONS = {"Parent": "Item", "Animations": {"Consume": {
    "FirstPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink_FPS.blockyanim",
    "ThirdPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink.blockyanim",
    "Speed": 1, "Looping": True}}}


def consumable(item_id, model, root, quality="Uncommon", stack=10):
    item(item_id, model, quality, stack, interactions={"Secondary": root}, categories=["Items.Potions"])
    path = ITEMS / f"{item_id}.json"
    data = json.loads(path.read_text())
    data.update({"PlayerAnimationsId": DRINK_ANIMATIONS, "Consumable": True, "Utility": {"Compatible": False}})
    write(path, data)


def root(root_id, interaction_id):
    write(ROOTS / f"{root_id}.json", {"Interactions": [interaction_id], "RequireNewClick": True})


def drink_chain(interaction_id, action, give_back="Potion_Empty"):
    """Comme Consume_Charge_Potion_Fast du jeu : animation de boisson tenue 1,5 s (relâcher annule), puis l'action ;
    la fiole bue est remplacée par une fiole vide."""
    consume = {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1}
    if give_back:
        consume["ItemToAdd"] = {"Id": give_back, "Quantity": 1}
    action = dict(action)
    action["Next"] = consume
    write(INTERACTIONS / f"{interaction_id}.json", {
        "Type": "Charging",
        "FailOnDamage": False,
        "Effects": {"ItemAnimationId": "Consume", "WorldSoundEventId": "SFX_Nakasar_Drink",
                    "ClearAnimationOnFinish": True, "ClearSoundEventOnFinish": True},
        "HorizontalSpeedMultiplier": 0.75,
        "Next": {"1.5": action},
        "Failed": {"Type": "Simple"},
    })


def recipe(output, inputs, category, tier, seconds=2, quantity=1):
    write(RECIPES / f"Recipe_{output}.json", {
        "TimeSeconds": seconds,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": i, "Quantity": q} for i, q in inputs],
        "PrimaryOutput": {"ItemId": output, "Quantity": quantity},
        "Output": [{"ItemId": output, "Quantity": quantity}],
        "BenchRequirement": [{"Type": "Crafting", "Id": ALTAR, "Categories": [category], "RequiredTierLevel": tier}],
    })


def effect(effect_id, icon, duration=None, debuff=False, infinite=False, **application):
    data = {"Name": f"{LANG}.effects.{effect_id}"}
    if infinite:
        data["Infinite"] = True
    if duration is not None:
        data["Duration"] = duration
    data.update({"OverlapBehavior": "Overwrite", "Debuff": debuff,
                 "StatusEffectIcon": f"UI/StatusEffects/Nakasar/Occult/{icon}.png"})
    if application:
        data["ApplicationEffects"] = application
    write(EFFECTS / f"{effect_id}.json", data)


SUN_POTIONS = {
    # niveau : (palier de l'autel, durée en secondes, ingrédients)
    1: (2, 480, [("Potion_Empty", 1), ("Ingredient_Nakasar_Undead_Ash", 2), ("Ingredient_Life_Essence", 2)]),
    2: (3, 480, [("Potion_Empty", 1), ("Ingredient_Nakasar_Undead_Ash", 4), ("Ingredient_Life_Essence", 3),
                 ("Ingredient_Crystal_Red", 1)]),
    3: (4, 180, [("Potion_Empty", 1), ("Ingredient_Nakasar_Manor_Relic", 1), ("Ingredient_Nakasar_Undead_Ash", 6),
                 ("Ingredient_Crystal_Purple", 2)]),
}


def build_items():
    # Ingrédients occultes
    item("Ingredient_Nakasar_Blood", "Blood_Drop", "Common", 50)
    item("Ingredient_Nakasar_Undead_Ash", "Undead_Ash", "Common", 50)
    item("Ingredient_Nakasar_Manor_Relic", "Manor_Relic", "Rare", 25)

    # Fiole de sang : nourrit le vampire, écœure un vivant.
    consumable("Potion_Nakasar_Blood", "Blood_Vial", "Root_Nakasar_Drink_Blood")
    root("Root_Nakasar_Drink_Blood", "Nakasar_Drink_Blood")
    drink_chain("Nakasar_Drink_Blood", {"Type": "Nakasar_DrinkBlood", "Blood": 0.35,
                                        "NauseaEffectId": "Nakasar_Blood_Nausea", "NauseaSeconds": 12})
    recipe("Potion_Nakasar_Blood", [("Potion_Empty", 1), ("Ingredient_Nakasar_Blood", 3)], CAT_BLOOD, 2)

    # Potions de voile solaire I à III
    for level, (tier, seconds, inputs) in SUN_POTIONS.items():
        item_id = f"Potion_Nakasar_Sun_Protection_{level}"
        consumable(item_id, f"Sun_Potion_{level}", f"Root_Nakasar_Drink_Sun_Protection_{level}",
                   quality=["", "Uncommon", "Rare", "Epic"][level])
        root(f"Root_Nakasar_Drink_Sun_Protection_{level}", f"Nakasar_Drink_Sun_Protection_{level}")
        drink_chain(f"Nakasar_Drink_Sun_Protection_{level}", {
            "Type": "ApplyEffect", "EffectId": f"Nakasar_Sun_Protection_{level}", "Entity": "User",
            "Duration": seconds})
        recipe(item_id, inputs, CAT_BLOOD, tier)
        effect(f"Nakasar_Sun_Protection_{level}", f"Sun_Protection_{level}", duration=seconds)

    # Rituels : le calice fait un vampire, l'encensoir le guérit (à moins de 5 blocs de l'autel).
    consumable("Nakasar_Ritual_Chalice", "Ritual_Chalice", "Root_Nakasar_Ritual_Become", "Epic", 1)
    root("Root_Nakasar_Ritual_Become", "Nakasar_Ritual_Become")
    write(INTERACTIONS / "Nakasar_Ritual_Become.json", {
        "Type": "Nakasar_VampireRitual", "Mode": "Become", "AltarRadius": 5,
        "EffectId": "Nakasar_Vampire_Awakening", "EffectSeconds": 8,
        "SoundEventId": "SFX_Nakasar_Ritual", "NoteItemId": "Nakasar_Note_Vampire_Awakening",
        "Next": {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1},
    })
    recipe("Nakasar_Ritual_Chalice", [("Ingredient_Nakasar_Manor_Relic", 2), ("Potion_Nakasar_Blood", 3),
                                      ("Rock_Gem_Ruby", 2), ("Ingredient_Rune_Shard", 2)], CAT_RITUALS, 3, 5)
    consumable("Nakasar_Purification_Censer", "Purification_Censer", "Root_Nakasar_Ritual_Cure", "Epic", 1)
    root("Root_Nakasar_Ritual_Cure", "Nakasar_Ritual_Cure")
    write(INTERACTIONS / "Nakasar_Ritual_Cure.json", {
        "Type": "Nakasar_VampireRitual", "Mode": "Cure", "AltarRadius": 5,
        "EffectId": "Nakasar_Purified", "EffectSeconds": 8,
        "SoundEventId": "SFX_Nakasar_Ritual", "NoteItemId": "Nakasar_Note_Purification",
        "Next": {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1},
    })
    recipe("Nakasar_Purification_Censer", [("Ingredient_Bar_Silver", 6), ("Nakasar_Purifying_Torch", 2),
                                           ("Ingredient_Life_Essence", 8), ("Rock_Gem_Topaz", 2)], CAT_RITUALS, 3, 5)

    # Notes déposées par les rituels (lisibles dans leur description)
    item("Nakasar_Note_Vampire_Awakening", "Note", "Rare", 1, categories=["Items.Ingredients"])
    item("Nakasar_Note_Purification", "Note", "Rare", 1, categories=["Items.Ingredients"])

    # Vêtements occultes : vêtements vanilla renommés, protection lue par VampireSystem
    for item_id, parent, inputs in [
        ("Armor_Nakasar_Occult_Hood", "Armor_Leather_Soft_Head",
         [("Armor_Leather_Soft_Head", 1), ("Ingredient_Bolt_Shadoweave", 1), ("Ingredient_Nakasar_Undead_Ash", 4)]),
        ("Armor_Nakasar_Occult_Mantle", "Armor_Leather_Soft_Chest",
         [("Armor_Leather_Soft_Chest", 1), ("Ingredient_Bolt_Shadoweave", 2), ("Ingredient_Nakasar_Manor_Relic", 1)]),
    ]:
        write(ITEMS / f"{item_id}.json", {"Parent": parent, "TranslationProperties": names(item_id),
                                          "Quality": "Rare"})
        recipe(item_id, inputs, CAT_RITUALS, 2 if item_id.endswith("Hood") else 3, 4)

    # Rune Nova de sang (Seigneur de la nuit) : une onde autour du lanceur qui boit le sang des vivants.
    write(SERVER / "Item/Items/Rune/Nakasar/Rune_Nakasar_BloodNova.json", {
        "TranslationProperties": names("Rune_Nakasar_BloodNova"),
        "Icon": "Icons/ItemsGenerated/Rune_Fireball.png",
        "Model": "Items/Runes/Rune_Ability.blockymodel",
        "Texture": "Items/Runes/Rune_Textures/Rune_Ability_Fireball.png",
        "Quality": "Epic",
        "ItemLevel": 20,
        "Categories": ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "IconProperties": {"Scale": 0.75, "Rotation": [0, 30, 15], "Translation": [4, -18]},
        "Scale": 0.8,
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
        "Ability": {
            "Slot": "Core", "Cooldown": 12, "Cost": 45, "CostType": "Mana",
            "AbilityKeywords": ["Damage", "Physical", "Aoe", "Nakasar_Lifesteal"],
            "Attributes": {"Damage": 1, "AoeScale": 1},
            "Cast": "Root_Nakasar_Ability_BloodNova",
        },
    })
    write(SERVER / "Item/RootInteractions/Nakasar/Root_Nakasar_Ability_BloodNova.json",
          {"Interactions": ["Nakasar_Ability_BloodNova_Cast"], "RequireNewClick": True})
    write(SERVER / "Item/Interactions/Nakasar/Abilities/Nakasar_Ability_BloodNova_Hit.json", {
        "Parent": "DamageEntityParent_Hit_Interrupt",
        "DamageCalculator": {"BaseDamage": {"Physical": 10}, "RandomPercentageModifier": 0.1},
        "DamageAttribute": "Damage",
        "DamageEffects": {"WorldSoundEventId": "SFX_Sword_T2_Impact",
                          "WorldParticles": [{"SystemId": "Impact_Sword_Basic_Stronk"}]},
        "EntityStatsOnHit": [{"EntityStatId": "Health", "Amount": 6,
                              "MultipliersPerEntitiesHit": [1.0, 0.6, 0.4], "MultiplierPerExtraEntityHit": 0.2}],
    })
    write(SERVER / "Item/Interactions/Nakasar/Abilities/Nakasar_Ability_BloodNova_Cast.json", {
        "Type": "StatsCondition",
        "UseAbilityCost": True,
        "Failed": "Ability_Cast_Fail",
        "Next": {"Type": "Parallel", "Interactions": [
            {"Interactions": [
                {"Type": "Simple", "RunTime": 0.3,
                 "Effects": {"ItemAnimationId": "SwingRight", "WorldSoundEventId": "SFX_Nakasar_Ritual"}},
                {"Type": "Selector", "RunTime": 0.1,
                 "Selector": {"Id": "AOECircle", "Range": 5, "SizeAttribute": "AoeScale"},
                 "HitEntity": {"Interactions": [
                     "Nakasar_Ability_BloodNova_Hit",
                     {"Type": "Nakasar_BloodFeed", "BloodGain": 0.05, "VampireBonusDamage": 5,
                      "VampireBonusHeal": 3, "DropChance": 0.15},
                     {"Type": "Nakasar_DrainBeam", "SystemId": "Nakasar_Blood_Drain", "Steps": 8,
                      "StepDelay": 0.04, "HeightOffset": 1.0},
                 ]}},
            ]},
            {"Interactions": [{"Type": "TriggerCooldown", "UseAbilityCooldown": True}]},
            {"Interactions": [{"Type": "ChangeStat", "UseAbilityCost": True}]},
        ]},
    })
    recipe("Rune_Nakasar_BloodNova", [("Ingredient_Rune_Shard", 4), ("Potion_Nakasar_Blood", 2),
                                      ("Ingredient_Nakasar_Manor_Relic", 1)], CAT_RUNES, 4, 3)


def build_effects():
    # Aucun signe visible des autres joueurs : la faim ne se voit que dans la barre d'effets du vampire.
    for stage in ["Sated", "Hunger_3", "Hunger_2", "Hunger_1", "Starving"]:
        effect(f"Nakasar_Blood_{stage}", f"Blood_{stage}", infinite=True, debuff=stage != "Sated")
    effect("Nakasar_Sunburn", "Sunburn", duration=1, debuff=True,
           ScreenEffect="ScreenEffects/Nakasar/Sun_Glare.png",
           EntityTopTint="#ffd9a0", EntityBottomTint="#ff9a5a")
    effect("Nakasar_Sunburn_Light", "Sunburn", duration=1, debuff=True,
           ScreenEffect="ScreenEffects/Nakasar/Sun_Glare_Light.png")
    effect("Nakasar_Vampire_Awakening", "Vampire_Awakening", duration=8,
           EntityTopTint="#ff4d5e", EntityBottomTint="#4a0010",
           Particles=[{"SystemId": "Nakasar_Blood_Drain", "TargetEntityPart": "Entity",
                       "ClearParticlesOnRemove": True}])
    effect("Nakasar_Purified", "Purified", duration=8,
           EntityTopTint="#fff6d8", EntityBottomTint="#cfe4ff",
           Particles=[{"SystemId": "Nakasar_Light_Aura", "TargetEntityPart": "Entity",
                       "ClearParticlesOnRemove": True}])
    effect("Nakasar_Blood_Nausea", "Blood_Nausea", duration=12, debuff=True,
           EntityTopTint="#c8e6a0", EntityBottomTint="#6f8f3a", HorizontalSpeedMultiplier=0.8)
    for cause, color in [("Nakasar_Sunlight", "#ffcf6e"), ("Nakasar_Purifying_Light", "#e8f0ff")]:
        write(DAMAGE / f"{cause}.json", {"DamageTextColor": color,
                                         "DeathMessageKey": f"{LANG}.deathCause.{cause}"})


def build_drops():
    """Cendres de mort-vivant : les morts-vivants du Comté en laissent une fois sur trois."""
    for drop_id, vanilla in [("Nakasar_Drop_Undead_Zombie", "Drop_Zombie"),
                             ("Nakasar_Drop_Undead_Skeleton", "Drop_Skeleton_Knight")]:
        write(DROPS / f"{drop_id}.json", {"Container": {"Type": "Multiple", "Containers": [
            {"Type": "Droplist", "DroplistId": vanilla},
            {"Type": "Choice", "Containers": [
                {"Type": "Single", "Weight": 1,
                 "Item": {"ItemId": "Ingredient_Nakasar_Undead_Ash", "QuantityMin": 1, "QuantityMax": 2}},
                {"Type": "Empty", "Weight": 2},
            ]},
        ]}})


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview.mkdir(parents=True, exist_ok=True)
    build_models(preview)
    status_icons()
    screen_effects()
    category_icons()
    build_sounds()
    build_items()
    build_effects()
    build_drops()


if __name__ == "__main__":
    main()
