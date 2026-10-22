"""Génère les assets de progression des fractales (étape 3 du GDD, docs/fractales/gdd.md).

    python3 mods/nakasar-fractals/tools/generate_progression.py [--preview DOSSIER]

- Éclats de Brume (`Nakasar_Fractal_Mist_Shard`) : la monnaie des fractales ;
- 15 infusions (`Nakasar_Fractal_Infusion_01` à `_15`) : +1 à +15 de résistance à l'agonie, une par emplacement de
  l'Autel des infusions (pile max 1). Deux infusions identiques et des éclats donnent la suivante, au Creuset des
  Brumes ; le Creuset refait aussi un Fragment des Brumes avec des éclats ;
- 4 sacs de fin de fractale, un par rang (`Nakasar_Fractal_Reward_Bag_<Rang>`), et leurs listes de butin ;
- le coffre des fractales du jour (`Nakasar_Fractal_Daily_Bag`, étape 9), donné en plus la première fois du jour
  qu'un joueur termine une des 3 fractales du jour (Java `party.DailyFractals`) ;
- l'effet `Nakasar_Fractal_Agony` (marqueur ; les dégâts sont calculés en Java selon le niveau et la résistance) et
  la cause de dégâts `Nakasar_Fractal_Agony` (ignore l'armure) ;
- la boutique de troc de l'Archiviste (`BarterShops/Nakasar_Fractal_Archivist`, dont les cosmétiques de saison de
  tools/generate_cosmetics.py), son modèle et son rôle ;
- les recettes (fusions, fragment, autel et creuset à l'établi) ;
- les langues `nakasar_fractals_progress.lang` (objets et messages Java de l'étape 3).

Les blocs (autel, creuset, coffre de fin, comptoir) et leur place dans l'Observatoire viennent de
tools/generate_observatory.py.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_models as fm
import generate_cosmetics as gcos

MOD = Path(__file__).resolve().parent.parent
PACK = MOD / "src" / "main" / "resources"
SERVER = PACK / "Server"
COMMON = PACK / "Common"
LANG = "nakasar_fractals_progress"
ITEM_MODELS = "Items/Nakasar/Fractals"
ICONS = "Icons/Items/Nakasar/Fractals"
CATEGORY_ICONS = "Icons/CraftingCategories/Nakasar/Fractals"

KEY = "PortalKey_Nakasar_Fractal"
SHARD = "Nakasar_Fractal_Mist_Shard"
ALTAR = "Nakasar_Fractal_Infusion_Altar"
FORGE = "Nakasar_Fractal_Mist_Forge"
AGONY = "Nakasar_Fractal_Agony"
SHOP = "Nakasar_Fractal_Archivist"
ARCHIVIST = "Nakasar_Fractal_Archivist"
MAX_INFUSION = 15
CAT_INFUSIONS = "Nakasar_Fractal_Infusions"
CAT_FRAGMENTS = "Nakasar_Fractal_Fragments"


def infusion(n):
    return f"Nakasar_Fractal_Infusion_{n:02d}"


def bag(rank):
    return f"Nakasar_Fractal_Reward_Bag_{rank}"


# Rangs (GDD) : id, nom fr, nom en, couleur du lien du sac.
RANKS = [
    ("Initiate", "Initié", "Initiate", (120, 190, 255)),
    ("Adept", "Adepte", "Adept", (90, 220, 150)),
    ("Expert", "Expert", "Expert", (190, 110, 255)),
    ("Master", "Maître", "Master", (255, 196, 70)),
]

# Contenu des sacs : éclats (min, max), un matériau vanilla au choix, une chance d'infusion.
# Ids vanilla déjà employés par les listes de butin du mod Vampires.
LOOT = {
    "Initiate": ((4, 6), [("Ingredient_Bar_Iron", 2, 4, 2), ("Rock_Gem_Topaz", 1, 1, 1), ("Potion_Health_Lesser", 2, 2, 1)],
                 [(infusion(1), 1), (None, 9)]),
    "Adept": ((7, 10), [("Ingredient_Bar_Silver", 2, 3, 2), ("Rock_Gem_Sapphire", 1, 1, 1), ("Ingredient_Rune_Shard", 1, 2, 1)],
              [(infusion(1), 1), (None, 3)]),
    "Expert": ((11, 15), [("Ingredient_Bar_Gold", 2, 3, 2), ("Rock_Gem_Ruby", 1, 1, 1), ("Ingredient_Rune_Shard", 2, 2, 1)],
               [(infusion(1), 2), (infusion(2), 1), (None, 3)]),
    "Master": ((16, 22), [("Rock_Gem_Emerald", 1, 2, 2), ("Ingredient_Rune_Shard", 3, 3, 2), ("Ingredient_Voidheart", 1, 1, 1)],
               [(infusion(2), 2), (infusion(3), 1), (None, 2)]),
}

# Fusion : 2 × infusion n + n × FUSION_SHARDS éclats → infusion n + 1.
FUSION_SHARDS = 4
# Fragment refait au Creuset, sans repasser par les Deepworks (GDD).
FRAGMENT_INPUTS = [(SHARD, 25), ("Ingredient_Rune_Shard", 1)]
ALTAR_INPUTS = [(SHARD, 30), ("Rock_Gem_Sapphire", 2), ("Ingredient_Bar_Silver", 4)]
FORGE_INPUTS = [(SHARD, 20), ("Ingredient_Bar_Iron", 6), ("Ingredient_Fire_Essence", 2)]
# Troc de l'Archiviste : objet, quantité, prix en éclats ; puis les cosmétiques de saison.
TRADES = [(infusion(1), 1, 10), (infusion(2), 1, 25), (infusion(4), 1, 120), (KEY, 1, 30)] + \
    [(item_id, 1, price) for item_id, price in gcos.PRICES.items()]
DAILY_BAG = "Nakasar_Fractal_Daily_Bag"
DAILY_TIE = (255, 220, 110)
# Coffre des fractales du jour : éclats, une infusion sûre, un matériau, une petite chance de cosmétique.
DAILY_LOOT = ((12, 18), [(infusion(1), 3), (infusion(2), 1)],
              [("Ingredient_Rune_Shard", 1, 2, 2), ("Rock_Gem_Sapphire", 1, 1, 1), ("Ingredient_Bar_Gold", 1, 2, 1)],
              [(c, 1) for c in gcos.PRICES] + [(None, 27)])


# --- couleurs et modèles --------------------------------------------------------------------------

def infusion_color(n):
    """Du cyan (+1) au violet puis à l'or (+15)."""
    stops = [(0, (90, 210, 255)), (5, (90, 120, 255)), (10, (190, 90, 255)), (14, (255, 200, 80))]
    t = n - 1
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            return fm.mix(ca, cb, (t - a) / (b - a))
    return stops[-1][1]


def infusion_parts(n):
    color = infusion_color(n)
    light = fm.mix(color, (255, 255, 255), 0.55)
    dark = fm.shade(color, 0.55)
    setting = (200, 170, 90) if n >= 12 else (170, 176, 196)
    size = 5 + min(4, n // 4)
    parts = [
        ("Base", (0, 1, 0), (size + 3, 2, size + 3), 45, fm.smooth(setting), "flat"),
        ("Core", (0, 2 + size / 2, 0), (size, size, size), 45, fm.crystal(dark, light), "fullbright"),
        ("Crown", (0, 2.5 + size, 0), (size - 2, 2, size - 2), 45, fm.crystal(color, light), "fullbright"),
    ]
    for k in range(min(4, 1 + n // 4)):
        a = math.radians(90 * k)
        parts.append((f"Prong_{k}", (math.cos(a) * (size / 2 + 1), 2.5, math.sin(a) * (size / 2 + 1)), (1, 3, 1), 0,
                      fm.flat(setting), "flat"))
    return parts, size


def shard_parts():
    blue, light, dark = (110, 150, 255), (220, 235, 255), (60, 50, 150)
    return [
        ("Shard_A", (0, 5, 0), (3, 10, 3), 20, fm.crystal(dark, light), "fullbright"),
        ("Shard_B", (2.5, 3, 1), (2, 6, 2), -30, fm.crystal(dark, blue), "fullbright"),
        ("Shard_C", (-2, 2.5, -1), (2, 5, 2), 60, fm.crystal(dark, blue), "fullbright"),
    ]


def bag_parts(tie):
    cloth, cloth_dark = (64, 70, 128), (42, 44, 92)
    return [
        ("Body", (0, 5, 0), (10, 9, 9), 0, fm.smooth(cloth), "flat"),
        ("Body_Wide", (0, 4, 0), (11, 6, 8), 0, fm.smooth(cloth), "flat"),
        ("Neck", (0, 10.5, 0), (5, 2, 5), 0, fm.smooth(cloth_dark), "flat"),
        ("Tie", (0, 11.8, 0), (6, 1, 6), 0, fm.flat(tie), "fullbright"),
        ("Top", (0, 13, 0), (4, 2, 4), 0, fm.smooth(cloth), "flat"),
        ("Seal", (2, 5, 4.6), (3, 3, 1), 0, fm.crystal(fm.shade(tie, 0.6), tie), "fullbright"),
    ]


def agony_icon(path):
    """Icône d'état de l'agonie : spirale violette sur un cercle sombre."""
    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 121, 121), fill=(36, 10, 48, 255), outline=(170, 70, 220, 255), width=6)
    pts = [(64 + math.cos(t / 6) * t / 1.4, 64 + math.sin(t / 6) * t / 1.4) for t in range(0, 70)]
    d.line(pts, fill=(230, 120, 255, 255), width=7)
    d.ellipse((56, 56, 72, 72), fill=(255, 210, 255, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --- assets JSON ---------------------------------------------------------------------------------

def held_item(item_id, model, quality, stack, extra=None, scale=1.0):
    doc = {
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
        "Icon": f"{ICONS}/{model}.png",
        "Model": f"{ITEM_MODELS}/{model}.blockymodel",
        "Texture": f"{ITEM_MODELS}/{model}.png",
        "Quality": quality,
        "Categories": ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "ItemSoundSetId": "ISS_Items_Gems",
        "Scale": scale,
        "MaxStack": stack,
    }
    doc.update(extra or {})
    return doc


def infusion_quality(n):
    return "Uncommon" if n <= 3 else "Rare" if n <= 7 else "Epic" if n <= 11 else "Legendary"


def droplist(rank):
    shards, materials, infusions = LOOT[rank]
    containers = [{"Type": "Single", "Item": {"ItemId": SHARD, "QuantityMin": shards[0], "QuantityMax": shards[1]}},
                  {"Type": "Choice", "Containers": [
                      {"Type": "Single", "Weight": w, "Item": {"ItemId": i, "QuantityMin": a, "QuantityMax": b}}
                      for i, a, b, w in materials]},
                  {"Type": "Choice", "Containers": [
                      {"Type": "Empty", "Weight": w} if i is None else
                      {"Type": "Single", "Weight": w, "Item": {"ItemId": i, "QuantityMin": 1, "QuantityMax": 1}}
                      for i, w in infusions]}]
    return {"$Comment": f"Sac de fin de fractale, rang {rank} : éclats de Brume, un matériau, une chance d'infusion.",
            "Container": {"Type": "Multiple", "Containers": containers}}


def daily_droplist():
    shards, infusions, materials, cosmetics = DAILY_LOOT

    def choice(entries):
        return {"Type": "Choice", "Containers": [
            {"Type": "Empty", "Weight": w} if i is None else
            {"Type": "Single", "Weight": w, "Item": {"ItemId": i, "QuantityMin": 1, "QuantityMax": 1}}
            for i, w in entries]}

    return {"$Comment": "Coffre des fractales du jour : éclats de Brume, une infusion, un matériau, une petite chance "
                        "d'un cosmétique de saison.",
            "Container": {"Type": "Multiple", "Containers": [
                {"Type": "Single", "Item": {"ItemId": SHARD, "QuantityMin": shards[0], "QuantityMax": shards[1]}},
                choice(infusions),
                {"Type": "Choice", "Containers": [
                    {"Type": "Single", "Weight": w, "Item": {"ItemId": i, "QuantityMin": a, "QuantityMax": b}}
                    for i, a, b, w in materials]},
                choice(cosmetics)]}}


def recipe(output, inputs, bench, category, seconds=3, quantity=1):
    return {
        "TimeSeconds": seconds,
        "KnowledgeRequired": False,
        "Input": [{"ItemId": k, "Quantity": q} for k, q in inputs],
        "PrimaryOutput": {"ItemId": output, "Quantity": quantity},
        "Output": [{"ItemId": output, "Quantity": quantity}],
        "BenchRequirement": [{"Type": "Crafting", "Id": bench, "Categories": [category], "RequiredTierLevel": 1}],
    }


def agony_effect():
    return {
        "$Comment": "Agonie des fractales (GDD) : marqueur visible ; dev.nakasar.hytale.fractals.progress.AgonySystem "
                    "retire chaque seconde un pourcentage des PV max selon le niveau de la fractale, réduit par la "
                    "résistance à l'agonie (infusions). Rien sous le niveau 26.",
        "Name": f"{LANG}.effects.{AGONY}",
        "Debuff": True,
        "StatusEffectIcon": "UI/StatusEffects/Nakasar/Fractals/Agony.png",
        "ApplicationEffects": {"EntityBottomTint": "#1a0624", "EntityTopTint": "#b04ae0"},
        "OverlapBehavior": "Overwrite",
        "Infinite": False,
        "Duration": 5,
    }


def agony_cause():
    return {
        "$Comment": "Dégâts d'agonie : un pourcentage des PV max, que l'armure ne réduit pas.",
        "BypassResistances": True,
        "DurabilityLoss": False,
        "StaminaLoss": False,
        "DamageTextColor": "#c070ff",
    }


def barter_shop():
    return {
        "DisplayNameKey": f"{LANG}.shop.Archivist.name",
        "RefreshInterval": {"Days": 1},
        "Trades": [{"Output": {"ItemId": i, "Quantity": q}, "Input": [{"ItemId": SHARD, "Quantity": price}], "Stock": 99}
                   for i, q, price in TRADES],
    }


def archivist_model():
    return {
        "$Comment": "L'Archiviste de l'Observatoire : vieux savant des Brumes, longue barbe grise, robe de mage, "
                    "chapeau à large bord. Humanoïde sur le squelette du joueur.",
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": "03",
        "DefaultAttachments": [
            {"Model": "Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel",
             "Texture": "Characters/Body_Attachments/Faces/Faces_Detached_Textures/Almond_Eyes_Face.png",
             "GradientSet": "Skin", "GradientId": "03"},
            {"Model": "Characters/Body_Attachments/Eyes/Eyes.blockymodel",
             "Texture": "Characters/Body_Attachments/Eyes/Eyes_Textures/Greyscale.png",
             "GradientSet": "Eyes_Gradient", "GradientId": "Green"},
            {"Model": "Characters/Body_Attachments/Eyebrows/Eyebrows_Medium.blockymodel",
             "Texture": "Characters/Body_Attachments/Eyebrows/Medium_Greyscale.png",
             "GradientSet": "Hair", "GradientId": "Grey"},
            {"Model": "Characters/Body_Attachments/Beards/SimpleLong.blockymodel",
             "Texture": "Characters/Body_Attachments/Beards/Handlebar_Greyscale.png",
             "GradientSet": "Hair", "GradientId": "Grey"},
            {"Model": "Cosmetics/Head/WideBrimHat.blockymodel", "Texture": "Cosmetics/Head/WideBrimHat.png",
             "GradientSet": "Faded_Leather", "GradientId": "Black"},
            {"Model": "Cosmetics/Overtops/Robe_Wizard.blockymodel", "Texture": "Cosmetics/Overtops/Blazen_Wizard_Coat.png"},
            {"Model": "Cosmetics/Gloves/BasicGloves.blockymodel", "Texture": "Cosmetics/Gloves/BasicGloves_Greyscale.png",
             "GradientSet": "Faded_Leather", "GradientId": "BrownDark"},
            {"Model": "Cosmetics/Shoes/AngledBoots.blockymodel",
             "Texture": "Cosmetics/Shoes/AngledBoots_Textures/Blazen_Wizard_Boots.png"},
        ],
    }


def archivist_role():
    return {
        "$Comment": "L'Archiviste : posé par ObservatoryNpcSystem derrière son comptoir, immobile et invulnérable. "
                    "L'utiliser ouvre sa boutique de troc (éclats de Brume contre infusions et fragments). Le comptoir "
                    "devant lui ouvre la même boutique. Généré par tools/generate_progression.py.",
        "Type": "Generic",
        "Appearance": ARCHIVIST,
        "NameTranslationKey": f"{LANG}.npc.Archivist.name",
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


# --- langues -------------------------------------------------------------------------------------

def lang():
    fr, en = {}, {}

    def item(item_id, name_fr, desc_fr, name_en, desc_en):
        fr[f"items.{item_id}.name"], fr[f"items.{item_id}.description"] = name_fr, desc_fr
        en[f"items.{item_id}.name"], en[f"items.{item_id}.description"] = name_en, desc_en

    item(SHARD, "Éclat de Brume", "Fragment cristallisé des Brumes, rapporté des fractales. Monnaie de l'Archiviste, "
         "il sert aussi au Creuset des Brumes.", "Mist Shard", "Crystallised fragment of the Mists, brought back from "
         "fractals. The Archivist's currency, also used at the Mist Crucible.")
    for n in range(1, MAX_INFUSION + 1):
        nxt_fr = (f"\n\nDeux infusions +{n} et {n * FUSION_SHARDS} éclats de Brume donnent une infusion +{n + 1} au "
                  "Creuset des Brumes.") if n < MAX_INFUSION else ""
        nxt_en = (f"\n\nTwo +{n} infusions and {n * FUSION_SHARDS} Mist Shards make a +{n + 1} infusion at the Mist "
                  "Crucible.") if n < MAX_INFUSION else ""
        item(infusion(n), f"Infusion des Brumes +{n}",
             f"+{n} de résistance à l'agonie, tant qu'elle est posée dans votre Autel des infusions." + nxt_fr,
             f"Mist Infusion +{n}", f"+{n} agony resistance while it sits in your Infusion Altar." + nxt_en)
    for rid, name_fr, name_en, _ in RANKS:
        item(bag(rid), f"Coffre de fractale ({name_fr})",
             "Récompense de fin de fractale. Clic droit : l'ouvrir (éclats de Brume, matériaux, parfois une infusion).",
             f"Fractal Chest ({name_en})",
             "End-of-fractal reward. Right click: open it (Mist Shards, materials, sometimes an infusion).")
    item(DAILY_BAG, "Coffre des fractales du jour",
         "Donné la première fois du jour que vous terminez une des trois fractales du jour. Clic droit : l'ouvrir "
         "(éclats de Brume, une infusion, un matériau, parfois un cosmétique de saison).",
         "Daily Fractal Chest",
         "Given the first time each day you complete one of the three daily fractals. Right click: open it (Mist "
         "Shards, an infusion, a material, sometimes a seasonal cosmetic).")
    fr[f"effects.{AGONY}"], en[f"effects.{AGONY}"] = "Agonie", "Agony"
    fr["npc.Archivist.name"], en["npc.Archivist.name"] = "L'Archiviste", "The Archivist"
    fr["shop.Archivist.name"], en["shop.Archivist.name"] = "Archives des Brumes", "Mist Archives"
    fr[f"benchCategories.{CAT_INFUSIONS.lower()}"], en[f"benchCategories.{CAT_INFUSIONS.lower()}"] = "Infusions", "Infusions"
    fr[f"benchCategories.{CAT_FRAGMENTS.lower()}"], en[f"benchCategories.{CAT_FRAGMENTS.lower()}"] = "Fragments", "Fragments"

    msgs = {
        "agony.hit": ("Agonie (niveau {level}) : {percent} % de vos PV par seconde. Résistance {resistance} sur "
                      "{recommended} conseillée.",
                      "Agony (level {level}): {percent}% of your HP per second. Resistance {resistance} of "
                      "{recommended} recommended."),
        "agony.none": ("Pas d'agonie sous le niveau 26 (niveau actuel : {level}).",
                       "No agony below level 26 (current level: {level})."),
        "agony.resisted": ("Agonie (niveau {level}) entièrement résistée ({resistance} sur {recommended} conseillée).",
                           "Agony (level {level}) fully resisted ({resistance} of {recommended} recommended)."),
        "infusions.open": ("Autel des infusions : résistance à l'agonie {resistance}.",
                           "Infusion Altar: agony resistance {resistance}."),
        "info": ("Niveau débloqué : {level}. Résistance à l'agonie : {resistance}.",
                 "Unlocked level: {level}. Agony resistance: {resistance}."),
        "unlocked": ("Niveau {level} débloqué !", "Level {level} unlocked!"),
        "level.locked": ("Niveau {level} verrouillé : {name} a débloqué jusqu'au niveau {max}.",
                         "Level {level} locked: {name} has unlocked up to level {max}."),
        "level.clamped": ("Le niveau redescend à {level}, le plus haut débloqué par {name}.",
                          "The level drops to {level}, the highest unlocked by {name}."),
        "reward.claimed": ("Vous prenez votre coffre de fractale (niveau {level}).",
                           "You take your fractal chest (level {level})."),
        "reward.notYet": ("Le coffre reste scellé tant que la fractale n'est pas terminée.",
                          "The chest stays sealed until the fractal is complete."),
        "reward.already": ("Vous avez déjà pris votre coffre.", "You already took your chest."),
        "reward.notMember": ("Ce coffre est pour le groupe parti de l'Observatoire.",
                             "This chest is for the group that left the Observatory."),
        "reward.lost": ("La partie a été interrompue (redémarrage du serveur) : pas de coffre.",
                        "The run was interrupted (server restart): no chest."),
        "daily.title": ("Fractales du jour (un coffre en plus la première fois du jour) :",
                        "Daily fractals (an extra chest the first time each day):"),
        "daily.claimed": ("{fractal} est une fractale du jour : coffre des fractales du jour reçu !",
                          "{fractal} is a daily fractal: Daily Fractal Chest received!"),
        "command.daily.desc": ("Affiche les fractales du jour et celles que vous avez déjà faites aujourd'hui.",
                               "Shows today's daily fractals and the ones you already did today."),
        "command.info.desc": ("Affiche votre niveau débloqué et votre résistance à l'agonie.",
                              "Shows your unlocked level and agony resistance."),
    }
    for k, (f, e) in msgs.items():
        fr[k], en[k] = f, e
    return fr, en


def write_lang(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k} = {v.replace(chr(10), chr(92) + 'n')}\n" for k, v in entries.items()), encoding="utf-8")


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    models, icons = COMMON / ITEM_MODELS, COMMON / ICONS
    items = SERVER / "Item/Items/Nakasar/Fractals"
    recipes = SERVER / "Item/Recipes/Nakasar/Fractals"
    rendered = []

    rendered.append(fm.write_item_model("Mist_Shard", shard_parts(), models, icons, 1, (0, 5, 0), 14.0))
    write_json(items / f"{SHARD}.json", held_item(SHARD, "Mist_Shard", "Uncommon", 250))

    for n in range(1, MAX_INFUSION + 1):
        parts, size = infusion_parts(n)
        name = f"Infusion_{n:02d}"
        rendered.append(fm.write_item_model(name, parts, models, icons, 100 + n, (0, 2 + size / 2, 0), 150 / (size + 6)))
        if n == 5:   # onglet Infusions de la Forge des Brumes (generate_observatory.py)
            (COMMON / CATEGORY_ICONS).mkdir(parents=True, exist_ok=True)
            rendered[-1].save(COMMON / CATEGORY_ICONS / "Infusions.png")
        write_json(items / f"{infusion(n)}.json", held_item(infusion(n), name, infusion_quality(n), 1,
                                                            {"Tags": {"Type": ["Nakasar_Fractal_Infusion"]}}))
        if n < MAX_INFUSION:
            write_json(recipes / f"Recipe_{infusion(n + 1)}.json",
                       recipe(infusion(n + 1), [(infusion(n), 2), (SHARD, n * FUSION_SHARDS)], FORGE, CAT_INFUSIONS))

    for rid, _, _, tie in RANKS:
        name = f"Reward_Bag_{rid}"
        rendered.append(fm.write_item_model(name, bag_parts(tie), models, icons, 200, (0, 7, 0), 11.0))
        root = f"Root_{bag(rid)}"
        write_json(items / f"{bag(rid)}.json", held_item(bag(rid), name, "Epic" if rid in ("Expert", "Master") else "Rare",
                                                         16, {"Interactions": {"Secondary": root}}))
        write_json(SERVER / "Item/RootInteractions/Nakasar/Fractals" / f"{root}.json",
                   {"Interactions": [f"{bag(rid)}_Open"], "RequireNewClick": True})
        write_json(SERVER / "Item/Interactions/Nakasar/Fractals" / f"{bag(rid)}_Open.json",
                   {"$Comment": f"Ouvre le coffre de fractale {rid} : il est retiré et sa liste de butin donnée.",
                    "Type": "Nakasar_Fractal_OpenBag", "Droplist": f"Nakasar_Fractal_Reward_{rid}"})
        write_json(SERVER / "Drops/Nakasar/Fractals" / f"Nakasar_Fractal_Reward_{rid}.json", droplist(rid))

    rendered.append(fm.write_item_model("Daily_Bag", bag_parts(DAILY_TIE), models, icons, 201, (0, 7, 0), 11.0))
    root = f"Root_{DAILY_BAG}"
    write_json(items / f"{DAILY_BAG}.json", held_item(DAILY_BAG, "Daily_Bag", "Epic", 16,
                                                      {"Interactions": {"Secondary": root}}))
    write_json(SERVER / "Item/RootInteractions/Nakasar/Fractals" / f"{root}.json",
               {"Interactions": [f"{DAILY_BAG}_Open"], "RequireNewClick": True})
    write_json(SERVER / "Item/Interactions/Nakasar/Fractals" / f"{DAILY_BAG}_Open.json",
               {"$Comment": "Ouvre le coffre des fractales du jour : il est retiré et sa liste de butin donnée.",
                "Type": "Nakasar_Fractal_OpenBag", "Droplist": "Nakasar_Fractal_Reward_Daily"})
    write_json(SERVER / "Drops/Nakasar/Fractals" / "Nakasar_Fractal_Reward_Daily.json", daily_droplist())

    write_json(recipes / f"Recipe_{KEY}_Mists.json", recipe(KEY, FRAGMENT_INPUTS, FORGE, CAT_FRAGMENTS, seconds=4))
    write_json(recipes / f"Recipe_{ALTAR}.json", recipe(ALTAR, ALTAR_INPUTS, "Workbench", "Workbench_Crafting", seconds=5))
    write_json(recipes / f"Recipe_{FORGE}.json", recipe(FORGE, FORGE_INPUTS, "Workbench", "Workbench_Crafting", seconds=5))

    write_json(SERVER / "Entity/Effects/Nakasar/Fractals" / f"{AGONY}.json", agony_effect())
    agony_icon(COMMON / "UI/StatusEffects/Nakasar/Fractals/Agony.png")
    write_json(SERVER / "Entity/Damage" / f"{AGONY}.json", agony_cause())
    write_json(SERVER / "BarterShops" / f"{SHOP}.json", barter_shop())
    write_json(SERVER / "Models/Nakasar/Fractals" / f"{ARCHIVIST}.json", archivist_model())
    write_json(SERVER / "NPC/Roles/Nakasar/Fractals" / f"{ARCHIVIST}.json", archivist_role())

    fr, en = lang()
    write_lang(SERVER / "Languages/fr-FR" / f"{LANG}.lang", fr)
    write_lang(SERVER / "Languages/en-US" / f"{LANG}.lang", en)
    print(f"Progression : {MAX_INFUSION} infusions, {len(RANKS)} coffres, {MAX_INFUSION - 1} fusions, "
          f"{len(TRADES)} trocs, {len(fr)} entrées de langue")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (66 * len(rendered), 66), (24, 24, 36, 255))
        for k, img in enumerate(rendered):
            sheet.alpha_composite(img, (66 * k + 1, 1))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(preview / "objets.png")


if __name__ == "__main__":
    main()
