"""Génère les runes et objets de soutien des fractales (Kevin, 26 octobre 2026 : lots 1, 2 et 3 du document
« Fractales : runes et armes de soutien »).

    python3 mods/nakasar-fractals/tools/generate_support.py [--preview DOSSIER]

- 14 runes de capacité `Rune_Nakasar_Fractal_<Id>` (modèle et texture Rune_Ability vanilla, icône dessinée ici) :
  emplacement Core, mana et recharge du jeu ; l'effet est le Java `Nakasar_Fractal_Support` (support.SupportCastInteraction,
  clé `Skill`) qui échoue sans cible, et alors ni mana ni recharge ne partent ;
- 3 armes `Weapon_Nakasar_Fractal_*` sur une arme vanilla (Parent : modèle, icône, attaques gardés) : clic droit = Java
  de soutien ; leurs effets au coup sont dans support.SupportHitSystem ;
- 5 consommables (totems, bombes, fiole de purge) et 2 bannières, eux aussi sur un objet vanilla ;
- 9 échos `Nakasar_Fractal_Echo_<Fractale>` (coffre de fin, party.ClaimRewardInteraction) et le noyau stable ;
- les effets d'état, les particules qui ne viennent pas du jeu (soin, feu, givre et glace sont vanilla, support.Skills),
  la cause de dégâts `Nakasar_Fractal_Support`, le leurre (modèle sur le joueur vanilla, rôle) ;
- les recettes du Creuset des Brumes (onglets Runes et Soutien, déclarés par tools/generate_observatory.py) et leurs
  icônes ; les prix de l'Alchimiste sont dans tools/generate_potions.py (SUPPORT_TRADES) ;
- la langue `nakasar_fractals_support.lang`.

Les nombres des descriptions sont ceux de support.Skills / support.SupportHitSystem : les deux se modifient ensemble.
Zones des joueurs sans couleur (décision de Kevin) : seules leurs particules les montrent ; le rouge reste aux menaces.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import fractal_common as fc
import generate_cliffside as gc
import generate_observatory as go
import generate_potions as gp
import generate_progression as gpr

GENERATOR = "generate_support.py"
LANG = "nakasar_fractals_support"
SERVER = fc.SERVER
COMMON = fc.COMMON
ITEMS = SERVER / "Item/Items/Nakasar/Fractals/Support"
RUNE_ITEMS = SERVER / "Item/Items/Rune/Nakasar/Fractals"
ROOTS = SERVER / "Item/RootInteractions/Nakasar/Fractals/Support"
INTERACTIONS = SERVER / "Item/Interactions/Nakasar/Fractals/Support"
RECIPES = SERVER / "Item/Recipes/Nakasar/Fractals/Support"
EFFECTS = SERVER / "Entity/Effects/Nakasar/Fractals/Support"
PARTICLES = SERVER / "Particles/Nakasar/Fractals/Support"
ICONS = "Icons/Items/Nakasar/Fractals/Support"
STATUS = "Support"   # sous-dossier de fc.STATUS_ICONS
CATEGORY_ICONS = go.CATEGORY_ICONS
FORGE = gpr.FORGE
SHARD = gpr.SHARD
CAT_RUNES = "Nakasar_Fractal_Runes"
CAT_SUPPORT = "Nakasar_Fractal_Support"
CAUSE = "Nakasar_Fractal_Support"
DECOY = "Nakasar_Fractal_Decoy"
STABLE_CORE = "Nakasar_Fractal_Stable_Core"
RUNE_SHARD = "Ingredient_Rune_Shard"

FRACTALS = {fid: (name_fr, name_en, color) for fid, name_fr, name_en, color in go.FRACTALS}

RANKS = {  # rang : (nom fr, nom en, qualité, recette)
    "Initiate": ("Initié", "Initiate", "Uncommon", lambda e: [(e, 2), (SHARD, 15)]),
    "Adept": ("Adepte", "Adept", "Rare", lambda e: [(e, 4), (SHARD, 40), (RUNE_SHARD, 1)]),
    "Expert": ("Expert", "Expert", "Epic", lambda e: [(e, 6), (SHARD, 80), (RUNE_SHARD, 2)]),
    "Master": ("Maître", "Master", "Legendary", lambda e: [(e, 8), (SHARD, 150), (STABLE_CORE, 1)]),
}


def echo(fractal):
    return f"Nakasar_Fractal_Echo_{fractal}"


# --- runes -----------------------------------------------------------------------------------------
# Id (= clé Skill du Java), fractale, rang, mana, recharge, glyphe de l'icône, noms (fr, en), effets (fr, en), animation.

RUNES = [
    ("HealingBreath", "Swampland", "Initiate", 35, 10, "breath", ("Souffle régénérant", "Healing Breath"),
     ("Cône de 6 blocs et 60° devant vous : +20 PV et régénération de 4 PV/s pendant 5 s pour chaque joueur touché, "
      "vous compris.",
      "6-block, 60° cone in front of you: +20 HP and 4 HP/s regeneration for 5 s to each player hit, yourself "
      "included."), "SwingRight"),
    ("HealingWell", "Swampland", "Initiate", 40, 20, "well", ("Puits de soin", "Healing Well"),
     ("Zone de 4 blocs de rayon à vos pieds, 6 s : les joueurs dedans regagnent 5 PV et 3 d'endurance par seconde.",
      "4-block radius zone at your feet, 6 s: players inside regain 5 HP and 3 stamina per second."), "SwingDown"),
    ("Shockwave", "Cliffside", "Initiate", 35, 15, "shock", ("Onde de choc", "Shockwave"),
     ("Les ennemis à 4 blocs sont repoussés et subissent 8 dégâts. Sur un boss : 3 coups dans la barre de défiance.",
      "Enemies within 4 blocks are knocked back and take 8 damage. On a boss: 3 hits on the defiance bar."),
     "SwingDown"),
    ("FrostGlyph", "Snowblind", "Initiate", 35, 18, "frost", ("Glyphe de gel", "Frost Glyph"),
     ("Disque de givre de 4 blocs de rayon au point visé (12 blocs), 8 s : les ennemis dedans sont ralentis de 50 %.",
      "4-block radius frost disc at the aimed spot (12 blocks), 8 s: enemies inside are slowed by 50%."),
     "SwingDown"),
    ("Transfusion", "Uncategorized", "Adept", 30, 15, "beam", ("Transfusion", "Transfusion"),
     ("Lien de 3 s vers l'allié visé (16 blocs, rompu au-delà de 20) : il gagne 10 PV/s, vous en perdez 5/s sans "
      "jamais tomber sous 1 PV. Traverse les barreaux des cages.",
      "3 s link to the aimed ally (16 blocks, breaks beyond 20): they gain 10 HP/s, you lose 5/s but never drop "
      "below 1 HP. Goes through cage bars."), "SwingRight"),
    ("Brazier", "Volcanic", "Adept", 40, 15, "flame", ("Brasier des Brumes", "Mist Brazier"),
     ("Flammes de 3 blocs de rayon au point visé, 5 s : 6 dégâts par seconde aux ennemis dedans, brûlure 3 s en sortant.",
      "3-block radius flames at the aimed spot, 5 s: 6 damage per second to enemies inside, 3 s burn when leaving."),
     "SwingDown"),
    ("Daze", "SirensReef", "Adept", 30, 12, "daze", ("Hébètement", "Daze"),
     ("Ennemi visé à 20 blocs : son attaque en cours est coupée et il n'attaque plus pendant 3 s. Sur un boss : 2 coups "
      "dans la barre de défiance.",
      "Aimed enemy within 20 blocks: its current attack is interrupted and it cannot attack for 3 s. On a boss: 2 hits "
      "on the defiance bar."), "SwingRight"),
    ("Aegis", "Cliffside", "Expert", 45, 25, "ward", ("Égide des Brumes", "Mist Aegis"),
     ("Vous et les joueurs à 5 blocs, 8 s : le prochain coup direct d'un ennemi est annulé. N'arrête ni l'agonie, ni "
      "les dégâts continus, ni les pièges et mécaniques des fractales.",
      "You and players within 5 blocks, 8 s: the next direct hit from an enemy is cancelled. Does not stop agony, "
      "damage over time, traps or fractal mechanics."), "SwingDown"),
    ("FrostLine", "Snowblind", "Expert", 45, 30, "line", ("Ligne de givre", "Frost Line"),
     ("Barrière de glace de 7 × 1 blocs en travers de votre regard, 3 blocs devant vous, 8 s : le premier ennemi qui la "
      "franchit est immobilisé 1,5 s (une fois par ennemi).",
      "7 × 1 ice barrier across your view, 3 blocks ahead, 8 s: each enemy crossing it is rooted for 1.5 s (once per "
      "enemy)."), "SwingRight"),
    ("GravityWell", "SolidOcean", "Expert", 45, 25, "gravity", ("Puits gravitationnel", "Gravity Well"),
     ("Tourbillon de 4 blocs de rayon au point visé : au bout de 1,5 s, attire les ennemis au centre et les étourdit 1 s. "
      "Sur un boss : 4 coups dans la barre de défiance.",
      "4-block radius vortex at the aimed spot: after 1.5 s, pulls enemies to the centre and stuns them for 1 s. On a "
      "boss: 4 hits on the defiance bar."), "SwingDown"),
    ("Decoy", "SilentSurf", "Expert", 40, 30, "decoy", ("Leurre des Brumes", "Mist Decoy"),
     ("Un double de vous (80 PV) au point visé attire les ennemis à 12 blocs pendant 6 s. Les boss l'ignorent.",
      "A double of you (80 HP) at the aimed spot draws enemies within 12 blocks for 6 s. Bosses ignore it."),
     "SwingDown"),
    ("Sanctuary", "Uncategorized", "Master", 50, 40, "dome", ("Sanctuaire", "Sanctuary"),
     ("Dôme de 4 blocs de rayon autour de vous, 5 s : les projectiles des ennemis ordinaires qui y entrent sont "
      "détruits (pas ceux des boss, des élites ni des mécaniques).",
      "4-block radius dome around you, 5 s: projectiles from ordinary enemies entering it are destroyed (not those of "
      "bosses, elites or mechanics)."), "SwingDown"),
    ("Reprieve", "SirensReef", "Master", 50, 60, "reprieve", ("Sursis", "Reprieve"),
     ("10 s : le premier joueur à 6 blocs (vous compris) qui tomberait à 0 PV reste à 1 PV et ne subit plus rien "
      "pendant 1,5 s. Une seule fois par lancer.",
      "10 s: the first player within 6 blocks (yourself included) who would drop to 0 HP stays at 1 HP and takes no "
      "damage for 1.5 s. Once per cast."), "SwingDown"),
    ("Fear", "SilentSurf", "Master", 40, 20, "fear", ("Épouvante", "Fear"),
     ("Les ennemis à 6 blocs fuient loin de vous pendant 2 s. Sur un boss : 2 coups dans la barre de défiance.",
      "Enemies within 6 blocks flee from you for 2 s. On a boss: 2 hits on the defiance bar."), "SwingDown"),
]


def rune_id(skill):
    return f"Rune_Nakasar_Fractal_{skill}"


def rune_item(skill, rank, mana, cooldown):
    rid = rune_id(skill)
    return {
        "$Comment": f"Rune de soutien des fractales ({skill}). Généré par tools/{GENERATOR}.",
        "TranslationProperties": {"Name": f"{LANG}.items.{rid}.name", "Description": f"{LANG}.items.{rid}.description"},
        "Icon": f"{ICONS}/{rid}.png",
        "Model": "Items/Runes/Rune_Ability.blockymodel",
        "Texture": "Items/Runes/Rune_Textures/Rune_Ability_Fireball.png",
        "Quality": RANKS[rank][2],
        "Categories": ["Items.Ingredients"],
        "PlayerAnimationsId": "Item",
        "Scale": 0.8,
        "ItemSoundSetId": "ISS_Items_Gems",
        "MaxStack": 1,
        "Ability": {
            "Slot": "Core",
            "Cooldown": cooldown,
            "Cost": mana,
            "CostType": "Mana",
            "AbilityKeywords": ["Nakasar_Fractal_Support"],
            "Attributes": {},
            "Cast": f"Root_{rid}",
        },
    }


def rune_cast(skill, anim):
    """Comme les runes du mod Vampires : mana vérifié, puis le Java ; mana, recharge et animation seulement s'il réussit."""
    return {
        "$Comment": f"Lancer de la rune {skill} : sans cible le Java échoue et rien n'est dépensé. Généré par tools/{GENERATOR}.",
        "Type": "StatsCondition",
        "UseAbilityCost": True,
        "Failed": "Ability_Cast_Fail",
        "Next": {
            "Type": "Nakasar_Fractal_Support",
            "Skill": skill,
            "Next": {"Type": "Parallel", "Interactions": [
                {"Interactions": [{"Type": "Simple", "RunTime": 0.3, "Effects": {
                    "ItemAnimationId": anim, "WorldSoundEventId": "SFX_Light_Melee_T2_Swing"}}]},
                {"Interactions": [{"Type": "TriggerCooldown", "UseAbilityCooldown": True}]},
                {"Interactions": [{"Type": "ChangeStat", "UseAbilityCost": True}]},
            ]},
        },
    }


# --- armes, consommables, bannières -----------------------------------------------------------------
# Id, base vanilla (Parent), clé Skill, qualité, noms, descriptions, recette (ou None : vendu par l'Alchimiste), pile.

STAFF = "Weapon_Nakasar_Fractal_Mending_Staff"
GRIMOIRE = "Weapon_Nakasar_Fractal_Frost_Grimoire"
WAND = "Weapon_Nakasar_Fractal_Root_Wand"
HEAL_TOTEM = "Nakasar_Fractal_Healing_Totem"
SLOW_TOTEM = "Nakasar_Fractal_Slowness_Totem"
DAZE_BOMB = "Nakasar_Fractal_Daze_Bomb"
SMOKE_BOMB = "Nakasar_Fractal_Smoke_Bomb"
PURGE = "Nakasar_Fractal_Purge_Flask"
BANNER_MIGHT = "Weapon_Nakasar_Fractal_Banner_Might"
BANNER_GUARD = "Weapon_Nakasar_Fractal_Banner_Guard"

WEAPONS = [
    (STAFF, "Weapon_Staff_Crystal_Purple", "StaffMend", "Rare",
     ("Bâton de guérison des Brumes", "Mist Mending Staff"),
     ("Attaque : chaque coup porté soigne de 6 PV le joueur le plus blessé à 8 blocs (vous compris), au plus deux fois "
      "par seconde. Clic droit : régénération de 6 PV/s pendant 3 s sur l'allié visé (12 blocs), toutes les 8 s.",
      "Attack: each hit heals the most injured player within 8 blocks (yourself included) for 6 HP, at most twice per "
      "second. Right click: 6 HP/s regeneration for 3 s on the aimed ally (12 blocks), every 8 s."),
     [("Weapon_Staff_Crystal_Purple", 1), (SHARD, 60), (echo("Swampland"), 3), (echo("Uncategorized"), 3)]),
    (GRIMOIRE, "Weapon_Spellbook_Frost", "GrimoireGlyph", "Rare",
     ("Grimoire de givre des Brumes", "Mist Frost Grimoire"),
     ("Attaque : chaque coup ralentit l'ennemi de 10 % de plus (5 piles, 4 s). Clic droit : glyphe de gel de 2,5 blocs "
      "de rayon au point visé, 5 s, toutes les 15 s.",
      "Attack: each hit slows the enemy by another 10% (5 stacks, 4 s). Right click: 2.5-block radius frost glyph at "
      "the aimed spot, 5 s, every 15 s."),
     [("Weapon_Spellbook_Frost", 1), (SHARD, 60), (echo("Snowblind"), 3), (echo("SolidOcean"), 3)]),
    (WAND, "Weapon_Wand_Root", "WandVines", "Epic",
     ("Baguette des racines des Brumes", "Mist Root Wand"),
     ("Attaque : un coup enracine l'ennemi 2 s, une fois toutes les 8 s par ennemi. Clic droit : vrilles en ligne de "
      "6 × 1 blocs devant vous, enracinent 1 s (2 coups de défiance sur un boss), toutes les 15 s.",
      "Attack: a hit roots the enemy for 2 s, once every 8 s per enemy. Right click: 6 × 1 line of vines in front of "
      "you, roots for 1 s (2 defiance hits on a boss), every 15 s."),
     [("Weapon_Wand_Root", 1), (SHARD, 100), (echo("Swampland"), 3), (echo("Deepstone"), 3)]),
    (BANNER_MIGHT, "Weapon_Staff_Wood", "BannerMight", "Legendary",
     ("Bannière de puissance des Brumes", "Mist Banner of Might"),
     ("Clic droit : plantée à vos pieds 30 s, les joueurs à 8 blocs infligent 10 % de dégâts en plus. Une bannière par "
      "fractale, toutes les 60 s.",
      "Right click: planted at your feet for 30 s, players within 8 blocks deal 10% more damage. One banner per "
      "fractal, every 60 s."),
     [("Weapon_Staff_Wood", 1), (SHARD, 80)] + [(echo(f), 4) for f in
                                               ("Cliffside", "Uncategorized", "Volcanic", "SolidOcean", "Swampland")]),
    (BANNER_GUARD, "Weapon_Staff_Wood", "BannerGuard", "Legendary",
     ("Bannière de garde des Brumes", "Mist Banner of Guard"),
     ("Clic droit : plantée à vos pieds 30 s, les joueurs à 8 blocs subissent 10 % de dégâts en moins (pas l'agonie). "
      "Une bannière par fractale, toutes les 60 s.",
      "Right click: planted at your feet for 30 s, players within 8 blocks take 10% less damage (not agony). One "
      "banner per fractal, every 60 s."),
     [("Weapon_Staff_Wood", 1), (SHARD, 80)] + [(echo(f), 4) for f in
                                               ("Snowblind", "SilentSurf", "SirensReef", "Deepstone", "Cliffside")]),
]

CONSUMABLES = [
    (HEAL_TOTEM, "Weapon_Deployable_Healing_Totem", "HealingTotem", "Uncommon",
     ("Totem de soin des Brumes", "Mist Healing Totem"),
     ("Utiliser : zone de soin de 5 blocs de rayon à vos pieds, 15 s, +4 PV/s aux joueurs. Un par fractale : le "
      "dernier posé remplace l'autre.",
      "Use: 5-block radius healing zone at your feet, 15 s, +4 HP/s to players. One per fractal: the last one placed "
      "replaces the other.")),
    (SLOW_TOTEM, "Weapon_Deployable_Slowness_Totem", "SlownessTotem", "Uncommon",
     ("Totem de lenteur des Brumes", "Mist Slowness Totem"),
     ("Utiliser : zone de 5 blocs de rayon à vos pieds, 15 s, ennemis dedans ralentis de 40 %. Un par fractale.",
      "Use: 5-block radius zone at your feet, 15 s, enemies inside slowed by 40%. One per fractal.")),
    (DAZE_BOMB, "Weapon_Bomb_Stun", "DazeBomb", "Uncommon",
     ("Bombe hébétante des Brumes", "Mist Daze Bomb"),
     ("Lancer au point visé (12 blocs) : les ennemis à 3 blocs de l'impact sont étourdis 2 s (3 coups de défiance sur "
      "un boss).",
      "Throw at the aimed spot (12 blocks): enemies within 3 blocks of the impact are stunned for 2 s (3 defiance hits "
      "on a boss).")),
    (SMOKE_BOMB, "Weapon_Bomb_Continuous", "SmokeBomb", "Rare",
     ("Fumigène des Brumes", "Mist Smoke Bomb"),
     ("Lancer au point visé : nuage de 4 blocs de rayon, 6 s ; les ennemis ordinaires dedans perdent leur cible.",
      "Throw at the aimed spot: 4-block radius cloud, 6 s; ordinary enemies inside lose their target.")),
    (PURGE, "Potion_Purify", "Purge", "Uncommon",
     ("Fiole de purge des Brumes", "Mist Purge Flask"),
     ("Boire (clic droit maintenu) : retire poison, brûlure, saignement, ralentissement et tourment, et 2 piles "
      "d'Hypothermie. Jamais l'agonie, la Corruption ni la malédiction des trésors.",
      "Drink (hold right click): removes poison, burn, bleeding, slow and torment, and 2 Hypothermia stacks. Never "
      "agony, Corruption or the treasure curse.")),
]


def support_item(item_id, parent, quality, stack, interactions, comment, extra=None):
    doc = {
        "$Comment": f"{comment} Généré par tools/{GENERATOR}.",
        "Parent": parent,
        "TranslationProperties": {"Name": f"{LANG}.items.{item_id}.name", "Description": f"{LANG}.items.{item_id}.description"},
        "Quality": quality,
        "MaxStack": stack,
        "Interactions": interactions,
    }
    doc.update(extra or {})
    return doc


def use_chain(skill, consume, sound="SFX_Light_Melee_T2_Swing"):
    nxt = {"Type": "Simple", "RunTime": 0.3, "Effects": {"WorldSoundEventId": sound}}
    if consume:
        nxt = {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1, "Next": nxt}
    return {
        "$Comment": f"Soutien {skill} : le Java échoue sans cible ou en recharge, et alors rien n'est {'consommé' if consume else 'lancé'}. "
                    f"Généré par tools/{GENERATOR}.",
        "Type": "Nakasar_Fractal_Support",
        "Skill": skill,
        "Next": nxt,
    }


def drink_chain(skill):
    """La gorgée des potions des Brumes (tools/generate_potions.py) : animation tenue 1,5 s, puis le Java et la fiole retirée."""
    return {
        "$Comment": f"Boire : {skill}. Généré par tools/{GENERATOR}.",
        "Type": "Charging",
        "FailOnDamage": False,
        "Effects": {"ItemAnimationId": "Consume", "WorldSoundEventId": gp.DRINK_SOUND,
                    "ClearAnimationOnFinish": True, "ClearSoundEventOnFinish": True},
        "HorizontalSpeedMultiplier": 0.75,
        "Next": {"1.5": {"Type": "Nakasar_Fractal_Support", "Skill": skill,
                         "Next": {"Type": "ModifyInventory", "AdjustHeldItemQuantity": -1}}},
        "Failed": {"Type": "Simple"},
    }


def root(name):
    return {"Interactions": [name], "RequireNewClick": True}


# --- échos ----------------------------------------------------------------------------------------

def echo_item(fractal):
    eid = echo(fractal)
    return {
        "$Comment": f"Écho de la fractale {fractal} : coffre de fin (party.ClaimRewardInteraction), ingrédient des runes "
                    f"et armes de soutien. Modèle de l'éclat de rune vanilla. Généré par tools/{GENERATOR}.",
        "Parent": RUNE_SHARD,
        "TranslationProperties": {"Name": f"{LANG}.items.{eid}.name", "Description": f"{LANG}.items.{eid}.description"},
        "Icon": f"{ICONS}/{eid}.png",
        "Quality": "Rare",
        "Categories": ["Items.Ingredients"],
        "MaxStack": 99,
    }


def core_item():
    return {
        "$Comment": f"Noyau stable : coffre de fin au rang Maître, une fois sur trois ; ingrédient des runes Maître. "
                    f"Modèle du cœur du Vide vanilla. Généré par tools/{GENERATOR}.",
        "Parent": "Ingredient_Voidheart",
        "TranslationProperties": {"Name": f"{LANG}.items.{STABLE_CORE}.name",
                                  "Description": f"{LANG}.items.{STABLE_CORE}.description"},
        "Icon": f"{ICONS}/{STABLE_CORE}.png",
        "Quality": "Legendary",
        "MaxStack": 20,
    }


# --- icônes ---------------------------------------------------------------------------------------

DARK = (26, 20, 34, 255)


def rune_icon(path, color, glyph):
    """Pierre de rune sombre bordée de la couleur de la fractale, glyphe de l'effet au centre (64 × 64)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    light = tuple(min(255, int(v * 0.5 + 128)) for v in color) + (255,)
    d.polygon(((32, 3), (59, 20), (54, 52), (32, 61), (10, 52), (5, 20)), fill=(46, 40, 58, 255), outline=c, width=3)
    g = glyph
    if g in ("breath", "well"):
        d.rectangle((28, 16, 36, 48), fill=light)
        d.rectangle((16, 28, 48, 36), fill=light)
        if g == "well":
            d.arc((10, 10, 54, 54), 200, 340, fill=c, width=3)
    elif g == "beam":
        d.line((14, 46, 50, 18), fill=light, width=5)
        d.ellipse((10, 42, 20, 52), fill=c)
        d.ellipse((44, 12, 54, 22), fill=c)
    elif g == "ward":
        d.polygon(((32, 14), (48, 20), (46, 38), (32, 50), (18, 38), (16, 20)), fill=light)
    elif g == "reprieve":
        d.polygon(((32, 14), (48, 20), (46, 38), (32, 50), (18, 38), (16, 20)), outline=light, width=3)
        d.rectangle((30, 22, 34, 38), fill=light)
        d.rectangle((30, 41, 34, 44), fill=light)
    elif g == "shock":
        for r in (8, 15, 22):
            d.arc((32 - r, 32 - r, 32 + r, 32 + r), 0, 360, fill=light, width=3)
    elif g == "daze":
        for k, (x, y) in enumerate(((20, 24), (32, 18), (44, 24))):
            d.polygon(((x, y - 6), (x + 2, y - 2), (x + 6, y), (x + 2, y + 2), (x, y + 6), (x - 2, y + 2),
                       (x - 6, y), (x - 2, y - 2)), fill=light)
        d.arc((16, 26, 48, 50), 20, 160, fill=c, width=3)
    elif g == "gravity":
        for k in range(3):
            d.arc((12 + k * 6, 12 + k * 6, 52 - k * 6, 52 - k * 6), k * 70, k * 70 + 250, fill=light, width=3)
    elif g == "decoy":
        for dx, col in ((-7, c), (5, light)):
            d.ellipse((24 + dx, 14, 36 + dx, 26), fill=col)
            d.rounded_rectangle((21 + dx, 27, 39 + dx, 50), 5, fill=col)
    elif g == "fear":
        d.ellipse((18, 14, 46, 42), fill=light)
        d.rounded_rectangle((24, 36, 40, 50), 3, fill=light)
        d.ellipse((23, 24, 30, 31), fill=DARK)
        d.ellipse((34, 24, 41, 31), fill=DARK)
    elif g == "frost":
        for a in range(3):
            t = math.pi * a / 3
            dx, dy = math.cos(t) * 18, math.sin(t) * 18
            d.line((32 - dx, 32 - dy, 32 + dx, 32 + dy), fill=light, width=4)
    elif g == "flame":
        d.polygon(((32, 12), (46, 36), (32, 52), (18, 36)), fill=c)
        d.polygon(((32, 30), (39, 42), (32, 50), (25, 42)), fill=(255, 236, 160, 255))
    elif g == "line":
        d.rectangle((12, 29, 52, 35), fill=light)
        for x in (16, 26, 36, 46):
            d.polygon(((x - 4, 29), (x, 18), (x + 4, 29)), fill=light)
    elif g == "dome":
        d.chord((12, 16, 52, 56), 180, 360, fill=light)
        d.rectangle((10, 36, 54, 40), fill=c)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def echo_icon(path, color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = color + (255,)
    light = tuple(min(255, int(v * 0.45 + 140)) for v in color) + (255,)
    d.polygon(((32, 4), (46, 26), (38, 60), (26, 60), (18, 26)), fill=c, outline=DARK, width=2)
    d.polygon(((32, 8), (40, 26), (32, 54)), fill=light)
    for x, y in ((12, 14), (52, 20), (50, 48), (12, 44)):
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=light)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def core_icon(path):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r, col in ((26, (90, 60, 150, 120)), (20, (150, 110, 230, 255)), (12, (225, 205, 255, 255)), (5, (255, 255, 255, 255))):
        d.ellipse((32 - r, 32 - r, 32 + r, 32 + r), fill=col)
    d.arc((4, 14, 60, 50), 0, 360, fill=(240, 220, 140, 255), width=3)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


# --- effets d'état ----------------------------------------------------------------------------------
# Id, noms (fr, en), couleur et glyphe de l'icône, néfaste, particules sur l'entité (id ou None).

EFFECT_LIST = [
    ("Nakasar_Fractal_Support_Regen", ("Régénération des Brumes", "Mist Regeneration"), (120, 230, 120), "plus", False, None),
    ("Nakasar_Fractal_Support_Aegis", ("Égide des Brumes", "Mist Aegis"), (240, 210, 120), "stone", False,
     "Nakasar_Fractal_Support_Ward"),
    ("Nakasar_Fractal_Support_Reprieve", ("Sursis", "Reprieve"), (220, 200, 255), "plus", False, None),
    ("Nakasar_Fractal_Support_Spared", ("Épargné", "Spared"), (255, 240, 200), "stone", False,
     "Nakasar_Fractal_Support_Ward"),
    ("Nakasar_Fractal_Support_Might", ("Bannière : puissance", "Banner: might"), (255, 170, 90), "flame", False, None),
    ("Nakasar_Fractal_Support_Guard", ("Bannière : garde", "Banner: guard"), (130, 190, 255), "stone", False, None),
    ("Nakasar_Fractal_Support_Slowed", ("Ralenti", "Slowed"), (170, 210, 240), "feet", True,
     "Nakasar_Fractal_Support_Chill"),
    ("Nakasar_Fractal_Support_Feared", ("Effrayé", "Feared"), (170, 140, 220), "skull", True, None),
    ("Nakasar_Fractal_Support_Dazed", ("Hébété", "Dazed"), (240, 230, 160), "minus", True, "Stunned"),
    ("Nakasar_Fractal_Support_Rooted", ("Enraciné", "Rooted"), (150, 190, 90), "feet", True,
     "Nakasar_Fractal_Support_Roots"),
]


def status_effect(effect_id, color, glyph, debuff, particle):
    icon = f"{STATUS}/{effect_id.removeprefix('Nakasar_Fractal_Support_')}"
    fc.status_icon(COMMON / fc.STATUS_ICONS / f"{icon}.png", color, glyph)
    extra = {}
    if particle:
        extra["ApplicationEffects"] = {"Particles": [{"SystemId": particle, "TargetEntityPart": "Self"}]}
    return fc.effect(LANG, effect_id, f"Soutien des fractales : posé par le Java (support.Skills). Généré par tools/{GENERATOR}.",
                     icon=icon, duration=2.0, debuff=debuff, **extra)


# --- particules -------------------------------------------------------------------------------------
# Pas de couleur au sol pour nos zones (décision de Kevin) : des effets qui se lisent comme leur rôle, jamais rouges.

S = gc.spawner
PARTICLE_SYSTEMS = {
    "Nakasar_Fractal_Support_Sanctuary": ("Sanctuaire : étincelles dorées de la voûte.",
                                          [("Gold", S("#fff2b0", "#d8a840", 4, (0.1, 0.3), (-20, 60), 0.2, 0.3,
                                                      life=(0.5, 0.8), size=(0.15, 0.3)), 0)]),
    "Nakasar_Fractal_Support_Gravity": ("Puits gravitationnel et Épouvante : brume violette qui tourbillonne.",
                                        [("Mist", S("#d8c0ff", "#6040a0", 5, (0.3, 0.8), (-10, 20), 0.4, 0.4,
                                                    life=(0.4, 0.7), size=(0.25, 0.45), blend="BlendLinear"), 0.1)]),
    "Nakasar_Fractal_Support_Smoke": ("Fumigène : fumée grise épaisse.",
                                      [("Smoke", S("#c8c8c8", "#606060", 4, (0.1, 0.4), (40, 90), 0.6, 1.2,
                                                   life=(0.8, 1.3), size=(0.6, 1.0), blend="BlendLinear", gravity=0.4), 0.2)]),
    "Nakasar_Fractal_Support_Beam": ("Transfusion et bâton : filet de vie vert pâle.",
                                     [("Life", S("#e0ffd0", "#60c060", 2, (0.05, 0.2), (-30, 30), 0.1, 0.1,
                                                 life=(0.3, 0.5), size=(0.15, 0.25)), 0)]),
    "Nakasar_Fractal_Support_Banner": ("Bannière : flammèches dorées autour de la hampe et du cercle.",
                                       [("Gold", S("#fff0c0", "#c09040", 3, (0.2, 0.5), (60, 90), 0.2, 0.2,
                                                   life=(0.6, 1.0), size=(0.15, 0.3)), 0)]),
    "Nakasar_Fractal_Support_Ward": ("Égide et Sursis : éclat de lumière blanche.",
                                     [("Light", S("#ffffff", "#f0d890", 8, (0.6, 1.4), (-40, 60), 0.3, 0.6,
                                                  life=(0.3, 0.6), size=(0.15, 0.3)), 0)]),
    "Nakasar_Fractal_Support_Shock": ("Onde de choc : poussière soulevée.",
                                      [("Dust", S("#e8e0d0", "#8a8070", 4, (0.8, 1.6), (0, 30), 0.3, 0.2,
                                                  life=(0.4, 0.7), size=(0.25, 0.45), blend="BlendLinear"), 0.1)]),
    "Nakasar_Fractal_Support_Roots": ("Vrilles et racines : brins verts et bruns qui jaillissent du sol.",
                                      [("Vines", S("#a0d060", "#5a4020", 6, (1.0, 2.0), (70, 90), 0.4, 0.1,
                                                   life=(0.4, 0.7), size=(0.2, 0.35), blend="BlendLinear", gravity=-6), 0)]),
    "Nakasar_Fractal_Support_Flash": ("Bombe hébétante et leurre : éclair blanc bref.",
                                      [("Flash", S("#ffffff", "#c8d8ff", 6, (1.0, 2.5), (-60, 60), 0.3, 0.4,
                                                   life=(0.2, 0.4), size=(0.25, 0.5)), 0)]),
    "Nakasar_Fractal_Support_Trail": ("Traînée d'un objet lancé ou d'un sort visé : brume des Brumes.",
                                      [("Mist", S("#e8d8ff", "#9070d0", 2, (0.05, 0.2), (-30, 30), 0.1, 0.1,
                                                  life=(0.3, 0.5), size=(0.15, 0.25)), 0)]),
    "Nakasar_Fractal_Support_Chill": ("Ennemi ralenti : flocons sur lui.",
                                      [("Snow", S("#ffffff", "#b0d8ff", 3, (0.1, 0.3), (-90, -40), 0.4, 1.6,
                                                  life=(0.6, 1.0), size=(0.1, 0.2)), 0.2)]),
}


# --- leurre ---------------------------------------------------------------------------------------

def decoy_model():
    def att(model, texture, gradient_set=None, gradient=None):
        doc = {"Model": model, "Texture": texture}
        if gradient_set:
            doc.update({"GradientSet": gradient_set, "GradientId": gradient})
        return doc
    return {
        "$Comment": "Leurre des Brumes : un double humanoïde sur le joueur vanilla, en tenue claire des Brumes. "
                    f"Généré par tools/{GENERATOR}.",
        "Parent": "Player",
        "Model": "Characters/Player.blockymodel",
        "Texture": "Characters/Player_Textures/Player_Greyscale.png",
        "GradientSet": "Skin",
        "GradientId": "03",
        "DefaultAttachments": [
            att("Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel",
                "Characters/Body_Attachments/Faces/Faces_Detached_Textures/Almond_Eyes_Face.png", "Skin", "03"),
            att("Characters/Body_Attachments/Eyes/Eyes.blockymodel",
                "Characters/Body_Attachments/Eyes/Eyes_Textures/Greyscale.png", "Eyes_Gradient", "Green"),
            att("Cosmetics/Overtops/TrenchCoat.blockymodel", "Cosmetics/Overtops/TrenchCoat_Greyscale.png",
                "Fantasy_Cotton", "Green"),
            att("Cosmetics/Pants/Pants_Straight.blockymodel", "Cosmetics/Pants/Pants_Straight_Textures/Leather_Greyscale.png",
                "Faded_Leather", "Black"),
            att("Cosmetics/Shoes/Boots_Long.blockymodel", "Cosmetics/Shoes/Boots_Long_Textures/Leather_Greyscale.png",
                "Faded_Leather", "Black"),
        ],
    }


def decoy_role():
    doc = fc.static_role(LANG, DECOY, "Leurre des Brumes (rune) : immobile, attire les ennemis ordinaires 6 s "
                                      "(support.Decoys, qui le pose et le retire). Neutre envers les joueurs.",
                         GENERATOR, 80, attitude="Neutral", foe=False)
    return doc


# --- langue -----------------------------------------------------------------------------------------

def lang():
    lg = fc.Lang()
    for skill, fractal, rank, mana, cooldown, _, names, descs, _ in RUNES:
        rank_fr, rank_en = RANKS[rank][:2]
        f_fr, f_en, _ = FRACTALS[fractal]
        lg.item(rune_id(skill), f"Rune : {names[0]}", f"{descs[0]} Rune de rang {rank_fr} ({f_fr}). {mana} mana, "
                f"recharge {cooldown} s.", f"Rune: {names[1]}",
                f"{descs[1]} {rank_en} rune ({f_en}). {mana} mana, {cooldown} s cooldown.")
    for item_id, _, _, _, names, descs, _ in WEAPONS:
        lg.item(item_id, names[0], descs[0], names[1], descs[1])
    for item_id, _, _, _, names, descs in CONSUMABLES:
        lg.item(item_id, names[0], descs[0] + " Vendu par l'Alchimiste de Dessa.", names[1],
                descs[1] + " Sold by Dessa's Alchemist.")
    for fid, (f_fr, f_en, _) in FRACTALS.items():
        lg.item(echo(fid), f"Écho : {f_fr}", f"Souvenir de la fractale {f_fr}, trouvé dans son coffre de fin. "
                "Ingrédient des runes et armes de soutien, au Creuset des Brumes.",
                f"Echo: {f_en}", f"A memory of the {f_en} fractal, found in its end chest. Ingredient of support runes "
                "and weapons, at the Mist Forge.")
    lg.item(STABLE_CORE, "Noyau stable", "Un éclat des Brumes qui ne se dissipe pas. Coffre de fin au rang Maître "
            "seulement ; ingrédient des runes de rang Maître.", "Stable Core",
            "A Mist shard that does not fade. Master rank end chest only; ingredient of Master runes.")
    for effect_id, names, *_ in EFFECT_LIST:
        lg.put(f"effects.{effect_id}", *names)
    lg.npc(DECOY, "Leurre des Brumes", "Mist Decoy")
    lg.put(f"benchCategories.{CAT_RUNES.lower()}", "Runes de soutien", "Support runes")
    lg.put(f"benchCategories.{CAT_SUPPORT.lower()}", "Armes de soutien", "Support weapons")
    # Messages Java (support.Support).
    lg.put("cooldown", "Pas encore prêt : encore {seconds} s.", "Not ready yet: {seconds} s left.")
    lg.put("noAlly", "Aucun allié visé.", "No ally targeted.")
    lg.put("noTarget", "Aucun ennemi visé.", "No enemy targeted.")
    lg.put("reprieve.saved", "Sursis : vous tenez bon !", "Reprieve: you hold on!")
    return lg


# --- principal ----------------------------------------------------------------------------------------

def main():
    preview = Path(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
    icons = []
    for skill, fractal, rank, mana, cooldown, glyph, _, _, anim in RUNES:
        rid = rune_id(skill)
        rune_icon(COMMON / ICONS / f"{rid}.png", FRACTALS[fractal][2], glyph)
        icons.append(COMMON / ICONS / f"{rid}.png")
        fc.write_json(RUNE_ITEMS / f"{rid}.json", rune_item(skill, rank, mana, cooldown))
        fc.write_json(ROOTS / f"Root_{rid}.json", root(f"{rid}_Cast"))
        fc.write_json(INTERACTIONS / f"{rid}_Cast.json", rune_cast(skill, anim))
        fc.write_json(RECIPES / f"Recipe_{rid}.json",
                      gpr.recipe(rid, RANKS[rank][3](echo(fractal)), FORGE, CAT_RUNES, seconds=3))

    for item_id, parent, skill, quality, _, _, inputs in WEAPONS:
        fc.write_json(ITEMS / f"{item_id}.json", support_item(
            item_id, parent, quality, 1, {"Secondary": f"Root_{item_id}"},
            f"Arme de soutien sur {parent} (modèle, icône et attaque principale vanilla) ; clic droit : {skill}."))
        fc.write_json(ROOTS / f"Root_{item_id}.json", root(f"{item_id}_Use"))
        fc.write_json(INTERACTIONS / f"{item_id}_Use.json", use_chain(skill, consume=False))
        fc.write_json(RECIPES / f"Recipe_{item_id}.json", gpr.recipe(item_id, inputs, FORGE, CAT_SUPPORT, seconds=4))

    for item_id, parent, skill, quality, _, _ in CONSUMABLES:
        use = {"Primary": f"Root_{item_id}", "Secondary": f"Root_{item_id}"}
        extra = None
        chain = use_chain(skill, consume=True)
        if skill == "Purge":
            use = {"Secondary": f"Root_{item_id}"}
            extra = {"PlayerAnimationsId": gp.DRINK_ANIMATIONS}
            chain = drink_chain(skill)
        fc.write_json(ITEMS / f"{item_id}.json", support_item(
            item_id, parent, quality, 10, use,
            f"Consommable de soutien sur {parent} (modèle et icône vanilla) : {skill} remplace l'effet du jeu.", extra))
        fc.write_json(ROOTS / f"Root_{item_id}.json", root(f"{item_id}_Use"))
        fc.write_json(INTERACTIONS / f"{item_id}_Use.json", chain)

    for fid, (_, _, color) in FRACTALS.items():
        echo_icon(COMMON / ICONS / f"{echo(fid)}.png", color)
        icons.append(COMMON / ICONS / f"{echo(fid)}.png")
        fc.write_json(ITEMS / f"{echo(fid)}.json", echo_item(fid))
    core_icon(COMMON / ICONS / f"{STABLE_CORE}.png")
    icons.append(COMMON / ICONS / f"{STABLE_CORE}.png")
    fc.write_json(ITEMS / f"{STABLE_CORE}.json", core_item())

    for effect_id, _, color, glyph, debuff, particle in EFFECT_LIST:
        fc.write_json(EFFECTS / f"{effect_id}.json", status_effect(effect_id, color, glyph, debuff, particle))
    for name, doc in fc.particle_files(PARTICLE_SYSTEMS, GENERATOR).items():
        fc.write_json(PARTICLES / name, doc)
    fc.write_json(SERVER / "Entity/Damage" / f"{CAUSE}.json",
                  fc.cause("Dégâts des runes et objets de soutien (Onde de choc, Brasier) : comptés à part de la "
                           "défiance (defiance.DefianceDamageSystem les ignore).", "#f0e0a0"))
    fc.write_json(SERVER / "Models/Nakasar/Fractals" / f"{DECOY}.json", decoy_model())
    fc.write_json(SERVER / "NPC/Roles/Nakasar/Fractals" / f"{DECOY}.json", decoy_role())

    # Icônes des onglets du Creuset : une rune (Égide) et l'écho du Marais (armes).
    (COMMON / CATEGORY_ICONS).mkdir(parents=True, exist_ok=True)
    rune_icon(COMMON / CATEGORY_ICONS / "Runes.png", FRACTALS["Cliffside"][2], "ward")
    rune_icon(COMMON / CATEGORY_ICONS / "Support.png", FRACTALS["Swampland"][2], "breath")

    lg = lang()
    lg.write(LANG)
    print(f"Soutien : {len(RUNES)} runes, {len(WEAPONS)} armes et bannières, {len(CONSUMABLES)} consommables, "
          f"{len(FRACTALS)} échos, {len(EFFECT_LIST)} effets, {len(lg.fr)} entrées de langue")

    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGBA", (66 * 8, 66 * ((len(icons) + 7) // 8)), (24, 24, 36, 255))
        for k, p in enumerate(icons):
            sheet.alpha_composite(Image.open(p).convert("RGBA"), (66 * (k % 8) + 1, 66 * (k // 8) + 1))
        sheet.save(preview / "soutien.png")


if __name__ == "__main__":
    main()
