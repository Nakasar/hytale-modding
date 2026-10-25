"""Génère les potions des Brumes et l'Alchimiste de Dessa (comme les « Mist potions » de GW2, Kevin, 25 octobre 2026).

    python3 mods/nakasar-fractals/tools/generate_potions.py [--preview DOSSIER]

- 6 potions : Offensive, Mobilité et Défensive des Brumes (`Nakasar_Fractal_Mist_Potion_<Type>`, une pile) et leurs
  grandes versions (`Nakasar_Fractal_Mist_Potion_Large_<Type>`, cinq piles). Boire (clic droit tenu 1,5 s, comme les
  potions du jeu) passe par le Java `Nakasar_Fractal_DrinkMistPotion` (potion.DrinkMistPotionInteraction) : piles
  ajoutées (5 au plus), durée remise à 1 h ;
- les effets affichés `Nakasar_Fractal_Mist_<Type>_<piles>` (actifs, dans une fractale) et
  `Nakasar_Fractal_Mist_<Type>_<piles>_Dormant` (hors des fractales : icône grise, aucun bonus). Seul l'effet de
  Mobilité active porte un bonus moteur (vitesse de course) ; les dégâts et l'endurance sont comptés en Java
  (potion.MistPotionDamageFilter, potion.MistPotionSystem) ;
- le son de gorgée `SFX_Nakasar_Fractal_Drink` (mono, généré) ;
- l'Alchimiste de Dessa : modèle, rôle et boutique de troc (`BarterShops/Nakasar_Fractal_Alchemist`, en éclats de
  Brume, grande potion = 5 × la petite, comme dans GW2). Sa place dans l'Observatoire vient de
  tools/generate_observatory.py (ALCHEMIST_SPOT) et il est posé par observatory.ObservatoryNpcSystem ;
- la langue `nakasar_fractals_potions.lang` (objets, effets, PNJ, messages Java).
"""
import json
import math
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_models as fm
import generate_observatory as go

MOD = Path(__file__).resolve().parent.parent
PACK = MOD / "src" / "main" / "resources"
SERVER = PACK / "Server"
COMMON = PACK / "Common"
LANG = "nakasar_fractals_potions"
ITEM_MODELS = "Items/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"
STATUS_ICONS = "UI/StatusEffects/Nakasar/Fractals/Potions"
ITEMS = SERVER / "Item/Items/Nakasar/Fractals/Potions"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/Fractals"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Fractals/Potions"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Fractals/Potions"
SOUND_EVENTS = SERVER / "Audio/SoundEvents/Nakasar/Fractals"
SOUNDS = COMMON / "Sounds/Nakasar/Fractals"
SHARD = "Nakasar_Fractal_Mist_Shard"
SHOP = "Nakasar_Fractal_Alchemist"
ALCHEMIST = "Nakasar_Fractal_Alchemist"
DRINK_SOUND = "SFX_Nakasar_Fractal_Drink"

MAX_STACKS = 5
LARGE_STACKS = 5
DURATION = 3600
SPEED_PER_STACK = 0.05     # Mobilité : course +5 % par pile (le Java lit les piles, pas cette valeur)

# Type, nom fr, nom en, couleur du liquide, glyphe de l'icône, prix (petite ; la grande coûte 5 fois plus),
# description du bonus par pile (fr, en). Bonus de GW2 (captures de Kevin) : repris tels quels par le Java.
KINDS = [
    ("Offensive", "offensive", "Offensive", (236, 84, 150), "sword", 4,
     "dégâts infligés dans les fractales +3 % par pile (dégâts d'états compris)",
     "outgoing damage in fractals +3% per stack (conditions included)"),
    ("Mobility", "de mobilité", "Mobility", (156, 96, 236), "feather", 3,
     "vitesse de déplacement dans les fractales +5 % par pile, récupération d'endurance +10 % par pile",
     "movement speed in fractals +5% per stack, endurance recharge +10% per stack"),
    ("Defensive", "défensive", "Defensive", (86, 214, 120), "shield", 3,
     "dégâts subis dans les fractales -5 % par pile (l'agonie n'est pas réduite)",
     "incoming damage in fractals -5% per stack (agony is not reduced)"),
]
EFFECT_NAMES = {"Offensive": ("Offensive des Brumes", "Fractal Offensive"),
                "Mobility": ("Mobilité des Brumes", "Fractal Mobility"),
                "Defensive": ("Défense des Brumes", "Fractal Defensive")}


def potion(kind, large):
    return f"Nakasar_Fractal_Mist_Potion_{'Large_' if large else ''}{kind}"


def effect_id(kind, n, dormant):
    return f"Nakasar_Fractal_Mist_{kind}_{n}{'_Dormant' if dormant else ''}"


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_lang(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k} = {v}\n" for k, v in entries.items()), encoding="utf-8")


# --- modèles ---------------------------------------------------------------------------------------

GLASS = (196, 216, 236)
CORK = (150, 104, 62)
GOLD = (232, 190, 92)


def bottle_parts(color, large):
    """Fiole ronde à bouchon de liège : liquide lumineux, épaules et col de verre, bague dorée ; la grande est plus
    ventrue, porte deux bagues et un cachet de cire."""
    light = fm.mix(color, (255, 255, 255), 0.5)
    dark = fm.shade(color, 0.55)
    glass = fm.smooth(GLASS)
    if not large:
        return [
            ("Liquid", (0, 4, 0), (7, 6, 7), 45, fm.crystal(dark, light), "fullbright"),
            ("Belly", (0, 4, 0), (8, 4, 8), 0, fm.crystal(dark, color), "fullbright"),
            ("Base", (0, 0.5, 0), (6, 1, 6), 0, glass, "flat"),
            ("Shoulder", (0, 8, 0), (6, 2, 6), 0, glass, "flat"),
            ("Neck", (0, 10, 0), (3, 2, 3), 0, glass, "flat"),
            ("Band", (0, 4, 0), (8.6, 1.4, 8.6), 0, fm.flat(GOLD), "flat"),
            ("Cork", (0, 11.6, 0), (3.6, 1.8, 3.6), 0, fm.smooth(CORK), "flat"),
        ]
    return [
        ("Liquid", (0, 5.5, 0), (10, 9, 10), 45, fm.crystal(dark, light), "fullbright"),
        ("Belly", (0, 5.5, 0), (11.4, 6, 11.4), 0, fm.crystal(dark, color), "fullbright"),
        ("Base", (0, 0.5, 0), (9, 1, 9), 0, glass, "flat"),
        ("Shoulder", (0, 11, 0), (8, 2, 8), 0, glass, "flat"),
        ("Neck", (0, 13, 0), (4, 2.4, 4), 0, glass, "flat"),
        ("Lip", (0, 14.4, 0), (5, 0.8, 5), 0, glass, "flat"),
        ("Band_Low", (0, 3.5, 0), (12, 1.2, 12), 0, fm.flat(GOLD), "flat"),
        ("Band_High", (0, 8, 0), (12, 1.2, 12), 0, fm.flat(GOLD), "flat"),
        ("Seal", (0, 5.5, 5.9), (3, 3, 1), 0, fm.crystal(fm.shade(GOLD, 0.6), GOLD), "flat"),
        ("Cork", (0, 15.6, 0), (4.6, 2.2, 4.6), 0, fm.smooth(CORK), "flat"),
    ]


# --- icônes d'état ---------------------------------------------------------------------------------

def status_icon(path, color, glyph, n, dormant):
    """Cercle sombre, glyphe du type et nombre de piles en bas à droite ; grisé en sommeil (hors fractale)."""
    if dormant:
        grey = sum(color) // 3
        color = fm.mix(color, (grey, grey, grey), 0.75)
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    dark = (26, 20, 34, 255)
    d.ellipse((6, 6, 121, 121), fill=dark, outline=c, width=6)
    if glyph == "sword":
        d.polygon(((86, 26), (98, 30), (52, 76), (44, 68)), fill=c)
        d.polygon(((34, 64), (64, 94), (58, 100), (28, 70)), fill=c)
        d.line((44, 84, 30, 98), fill=c, width=9)
    elif glyph == "feather":
        d.polygon(((44, 92), (46, 62), (66, 38), (98, 24), (90, 56), (68, 80)), fill=c)
        d.line((30, 106, 90, 34), fill=dark, width=4)
        d.line((30, 106, 46, 88), fill=c, width=5)
        for k in range(4):
            d.line((54 + k * 9, 76 - k * 11, 72 + k * 9, 76 - k * 11), fill=dark, width=3)
    elif glyph == "shield":
        d.polygon(((64, 22), (98, 34), (94, 72), (64, 104), (34, 72), (30, 34)), fill=c)
        d.polygon(((64, 36), (84, 44), (82, 70), (64, 90)), fill=fm.mix(color, (255, 255, 255), 0.45) + (255,))
    # Nombre de piles, en chiffres pixel (ceux des diapasons de l'Observatoire).
    cell, text = 7, str(n)
    x0, y0 = 118 - 3 * cell, 120 - 5 * cell
    d.rounded_rectangle((x0 - 6, y0 - 6, x0 + 3 * cell + 5, y0 + 5 * cell + 5), 6, fill=dark, outline=c, width=3)
    for i, bit in enumerate(go.DIGITS[text]):
        if bit == "1":
            x, y = x0 + (i % 3) * cell, y0 + (i // 3) * cell
            d.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(255, 255, 255, 255) if not dormant else (190, 190, 190, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --- son de gorgée (copie du générateur du mod Vampires, tools/generate_occult.py) -----------------

RATE = 44100


def drink_samples():
    """Trois gorgées : petits glouglous filtrés."""
    out = []
    for i in range(int(RATE * 0.8)):
        t = i / RATE
        v = 0.0
        for start in (0.0, 0.25, 0.5):
            u = t - start
            if 0 <= u < 0.2:
                v += 0.6 * math.sin(2 * math.pi * (300 - 600 * u) * u) * math.exp(-u * 14)
        out.append(v)
    return out


def write_ogg(samples, path):
    """Écrit un ogg MONO (le validateur du serveur refuse un WorldSoundEventId stéréo)."""
    peak = max(1e-6, max(abs(s) for s in samples))
    data = b"".join(struct.pack("<h", int(32000 * s / peak)) for s in samples)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "s.wav"
        with open(wav, "wb") as f:
            f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt ")
            f.write(struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16))
            f.write(b"data" + struct.pack("<I", len(data)) + data)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-c:a", "libvorbis", "-q:a", "4",
                        "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", str(path)],
                       check=True)


# --- assets JSON -----------------------------------------------------------------------------------

# Animation de boisson des potions du jeu (Potion_Template, Assets.zip 0.7.2 ; déjà employée par le mod Vampires).
DRINK_ANIMATIONS = {"Parent": "Item", "Animations": {"Consume": {
    "FirstPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink_FPS.blockyanim",
    "ThirdPerson": "Characters/Animations/Items/Main_Handed/Item/Attacks/Drink/Drink.blockyanim",
    "Speed": 1, "Looping": True}}}


def potion_item(item_id, model, large):
    return {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
        "Icon": f"{ICONS}/{model}.png",
        "Model": f"{ITEM_MODELS}/{model}.blockymodel",
        "Texture": f"{ITEM_MODELS}/{model}.png",
        "Quality": "Epic" if large else "Rare",
        "Categories": ["Items.Potions"],
        "PlayerAnimationsId": DRINK_ANIMATIONS,
        "ItemSoundSetId": "ISS_Items_Gems",
        "Consumable": True,
        "Utility": {"Compatible": False},
        "MaxStack": 25,
        "Interactions": {"Secondary": f"Root_{item_id}"},
    }


def drink_chain(kind, stacks):
    """Comme Consume_Charge_Potion_Fast du jeu : animation de boisson tenue 1,5 s (relâcher annule), puis le Java ajoute
    les piles et la potion est retirée (seulement si le Java réussit)."""
    return {
        "$Comment": f"Boire : {stacks} pile(s) de {kind} des Brumes. Généré par tools/generate_potions.py.",
        "Type": "Charging",
        "FailOnDamage": False,
        "Effects": {"ItemAnimationId": "Consume", "WorldSoundEventId": DRINK_SOUND,
                    "ClearAnimationOnFinish": True, "ClearSoundEventOnFinish": True},
        "HorizontalSpeedMultiplier": 0.75,
        "Next": {"1.5": {
            "Type": "Nakasar_Fractal_DrinkMistPotion", "Potion": kind, "Stacks": stacks,
            "Next": {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1},
        }},
        "Failed": {"Type": "Simple"},
    }


def effect(kind, n, dormant, icon):
    doc = {
        "$Comment": (f"{kind} des Brumes, {n} pile(s){' en sommeil (hors fractale, sans bonus)' if dormant else ''} : "
                     "posé et retiré par potion.MistPotionSystem, qui garde la durée. Généré par tools/generate_potions.py."),
        "Name": f"{LANG}.effects.{effect_id(kind, n, dormant)}",
        "StatusEffectIcon": f"{STATUS_ICONS}/{icon}.png",
    }
    if kind == "Mobility" and not dormant:
        doc["ApplicationEffects"] = {"HorizontalSpeedMultiplier": round(1 + SPEED_PER_STACK * n, 2)}
    doc.update({"OverlapBehavior": "Overwrite", "Infinite": False, "Duration": DURATION})
    return doc


def barter_shop():
    trades = []
    for kind, *_, price, _, _ in KINDS:
        trades.append((potion(kind, False), price))
    for kind, *_, price, _, _ in KINDS:
        trades.append((potion(kind, True), price * LARGE_STACKS))
    return {
        "DisplayNameKey": f"{LANG}.shop.Alchemist.name",
        "RefreshInterval": {"Days": 1},
        "Trades": [{"Output": {"ItemId": i, "Quantity": 1}, "Input": [{"ItemId": SHARD, "Quantity": p}], "Stock": 99}
                   for i, p in trades],
    }


def alchemist_model():
    def att(model, texture, gradient_set=None, gradient=None):
        doc = {"Model": model, "Texture": texture}
        if gradient_set:
            doc.update({"GradientSet": gradient_set, "GradientId": gradient})
        return doc
    return {
        "$Comment": "L'Alchimiste de Dessa (GW2 : un asura du labo de Dessa) : petit savant en long manteau, lunettes de "
                    "gobelin sur le nez, gants de cuir. Humanoïde sur le squelette du joueur, réduit comme un asura.",
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": "05",
        "MinScale": 0.72,
        "MaxScale": 0.72,
        "DefaultAttachments": [
            att("Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel",
                "Characters/Body_Attachments/Faces/Faces_Detached_Textures/Almond_Eyes_Face.png", "Skin", "05"),
            att("Characters/Body_Attachments/Eyes/Eyes.blockymodel",
                "Characters/Body_Attachments/Eyes/Eyes_Textures/Greyscale.png", "Eyes_Gradient", "Green"),
            att("Cosmetics/Face_Accessories/GoblinGoggles.blockymodel", "Cosmetics/Face_Accessories/GoblinGoggles.png",
                "Fantasy_Cotton", "Green"),
            att("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png",
                "Faded_Leather", "BrownDark"),
            att("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png",
                "Faded_Leather", "Black"),
            att("Cosmetics/Gloves/Leather_Straps.blockymodel", "Cosmetics/Gloves/Leather_Straps_Greyscale.png",
                "Faded_Leather", "BrownDark"),
            att("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
                "Faded_Leather", "Black"),
        ],
    }


def alchemist_role():
    return {
        "$Comment": "L'Alchimiste de Dessa : posé par ObservatoryNpcSystem sur l'île asura de l'Observatoire, immobile et "
                    "invulnérable. L'utiliser ouvre sa boutique de troc (potions des Brumes contre éclats de Brume). "
                    "Généré par tools/generate_potions.py.",
        "Type": "Generic",
        "Appearance": ALCHEMIST,
        "NameTranslationKey": f"{LANG}.npc.Alchemist.name",
        "MaxHealth": 1000,
        "StartState": "Idle",
        "DefaultPlayerAttitude": "Neutral",
        "DefaultNPCAttitude": "Ignore",
        "MotionControllerList": [{"Type": "Walk", "MaxWalkSpeed": 0.1, "Gravity": 10, "MaxFallSpeed": 10,
                                  "Acceleration": 10, "JumpHeight": 1.0}],
        "KnockbackScale": 0,
        "Instructions": [{"Sensor": {"Type": "State", "State": "Idle"}, "Instructions": [{"Actions": []}]}],
        "InteractionInstruction": {"Instructions": [
            {"Continue": True, "Sensor": {"Type": "Any"},
             "Actions": [{"Type": "SetInteractable", "Interactable": True, "Hint": "interactionHints.trade"}]},
            {"Sensor": {"Type": "HasInteracted"}, "Actions": [{"Type": "OpenBarterShop", "Shop": SHOP}]},
        ]},
    }


# --- langues ---------------------------------------------------------------------------------------

def lang():
    fr, en = {}, {}
    for kind, adj_fr, name_en, _, _, _, bonus_fr, bonus_en in KINDS:
        for large in (False, True):
            item_id = potion(kind, large)
            fr[f"items.{item_id}.name"] = f"{'Grande potion' if large else 'Potion'} {adj_fr} des Brumes"
            en[f"items.{item_id}.name"] = f"{'Large ' if large else ''}Mist {name_en} Potion"
            fr[f"items.{item_id}.description"] = (
                f"Boire (clic droit maintenu) : {'cinq piles' if large else 'une pile'} de {EFFECT_NAMES[kind][0]} "
                f"pendant 1 h ; {bonus_fr}. Se cumule jusqu'à {MAX_STACKS} fois, chaque gorgée remet la durée à 1 h. "
                "Sans effet hors des fractales. Vendue par l'Alchimiste de Dessa, à l'Observatoire.")
            en[f"items.{item_id}.description"] = (
                f"Drink (hold right click): {'five stacks' if large else 'one stack'} of {EFFECT_NAMES[kind][1]} for "
                f"1 h; {bonus_en}. Stacks up to {MAX_STACKS} times, each drink resets the duration to 1 h. No effect "
                "outside fractals. Sold by Dessa's Alchemist, in the Observatory.")
        for n in range(1, MAX_STACKS + 1):
            for dormant in (False, True):
                key = f"effects.{effect_id(kind, n, dormant)}"
                fr[key] = f"{EFFECT_NAMES[kind][0]} ×{n}{' (en sommeil hors des fractales)' if dormant else ''}"
                en[key] = f"{EFFECT_NAMES[kind][1]} ×{n}{' (dormant outside fractals)' if dormant else ''}"
        fr[f"kind.{kind}"], en[f"kind.{kind}"] = EFFECT_NAMES[kind]
    fr["npc.Alchemist.name"], en["npc.Alchemist.name"] = "L'Alchimiste de Dessa", "Dessa's Alchemist"
    fr["shop.Alchemist.name"], en["shop.Alchemist.name"] = "Potions des Brumes", "Mist Potions"
    # Messages Java (potion.DrinkMistPotionInteraction).
    fr["drink"] = "{name} : {stacks} pile(s) sur {max}, pendant 1 h. Actif dans les fractales seulement."
    en["drink"] = "{name}: {stacks} of {max} stack(s), for 1 h. Active in fractals only."
    return fr, en


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    models, icons = COMMON / ITEM_MODELS, COMMON / ICONS
    rendered = []
    for kind, _, _, color, glyph, _, _, _ in KINDS:
        for large in (False, True):
            item_id = potion(kind, large)
            model = item_id.removeprefix("Nakasar_Fractal_")
            stacks = LARGE_STACKS if large else 1
            center, scale = ((0, 8, 0), 9.0) if large else ((0, 6, 0), 12.0)
            rendered.append(fm.write_item_model(model, bottle_parts(color, large), models, icons, 400 + len(rendered),
                                                center, scale))
            write_json(ITEMS / f"{item_id}.json", potion_item(item_id, model, large))
            write_json(ROOTS / f"Root_{item_id}.json", {"Interactions": [f"{item_id}_Drink"], "RequireNewClick": True})
            write_json(INTERACTIONS / f"{item_id}_Drink.json", drink_chain(kind, stacks))
        for n in range(1, MAX_STACKS + 1):
            for dormant in (False, True):
                icon = f"{kind}_{n}{'_Dormant' if dormant else ''}"
                status_icon(COMMON / STATUS_ICONS / f"{icon}.png", color, glyph, n, dormant)
                write_json(EFFECTS / f"{effect_id(kind, n, dormant)}.json", effect(kind, n, dormant, icon))

    write_ogg(drink_samples(), SOUNDS / "Mist_Drink.ogg")
    write_json(SOUND_EVENTS / f"{DRINK_SOUND}.json", {
        "Volume": -4, "MaxDistance": 12, "Layers": [{"Files": ["Sounds/Nakasar/Fractals/Mist_Drink.ogg"], "Volume": 0}]})
    write_json(SERVER / "BarterShops" / f"{SHOP}.json", barter_shop())
    write_json(SERVER / "Models/Nakasar/Fractals" / f"{ALCHEMIST}.json", alchemist_model())
    write_json(SERVER / "NPC/Roles/Nakasar/Fractals" / f"{ALCHEMIST}.json", alchemist_role())

    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    print(f"Potions des Brumes : {len(rendered)} potions, {len(KINDS) * MAX_STACKS * 2} effets, {len(fr)} entrées de langue")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (66 * len(rendered), 66), (24, 24, 36, 255))
        for k, img in enumerate(rendered):
            sheet.alpha_composite(img, (66 * k + 1, 1))
        icons_row = [Image.open(COMMON / STATUS_ICONS / f"{kind}_{n}{s}.png").resize((48, 48))
                     for kind, *_ in KINDS for n in (1, 5) for s in ("", "_Dormant")]
        full = Image.new("RGBA", (max(sheet.width, 50 * len(icons_row)), 66 + 52), (24, 24, 36, 255))
        full.alpha_composite(sheet, (0, 0))
        for k, img in enumerate(icons_row):
            full.alpha_composite(img, (50 * k + 1, 68))
        full.save(preview / "potions.png")


if __name__ == "__main__":
    main()
