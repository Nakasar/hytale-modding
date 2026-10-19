#!/usr/bin/env python3
"""Génère le lore implicite du Comté Vampire : notes, épitaphes et tableau de contrats de la brèche.

    python3 mods/nakasar-vampires/tools/generate_lore.py [--preview DOSSIER]

Aucun dialogue de PNJ : l'histoire se lit sur des blocs. Chaque texte est un bloc dont l'objet porte un nom (titre)
et une description (le texte) ; utiliser le bloc (touche F) ouvre la page de lore du jeu (interaction
`OpenCustomUI`, page `BlockLore`), qui affiche ce titre et cette description. Ramassée ou trouvée dans un coffre, une
note se lit aussi dans l'infobulle de l'inventaire. Trois sortes de blocs :

- les notes (`Nakasar_Lore_<Nom>`) : feuille posée au sol, lettre cachetée ou bout de toile, non bloquantes. Posées
  par generate_prefabs.py et tirées dans les coffres par generate_loot.py (NOTES_BY_PLACE) ;
- les épitaphes (`Nakasar_Epitaph_<Nom>`) : pierres tombales gravées, posées dans les cimetières ;
- le tableau de contrats de la brèche (`Nakasar_Contract_Board`), posé par generate_breach.py : sa note appelle à
  l'aide et, à l'usage, remet le premier contrat (`FIRST_CONTRACT`) : une seule prime par brèche, pour tout
  le serveur (interaction Java `Nakasar_ClaimBreachContract`).

Écrit les modèles, textures, icônes, hitboxes, objets, interactions et les fichiers de langue nakasar_lore.lang
(fr-FR et en-US). Les textes vivent ici, dans LORE, EPITAPHS et BOARD. Le générateur est déterministe.
"""

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import generate_assets as gx

PACK = Path(__file__).resolve().parent.parent / "src" / "main" / "resources"
COMMON = PACK / "Common"
SERVER = PACK / "Server"
MODELS = COMMON / "Blocks" / "Nakasar" / "Lore"
TEXTURES = COMMON / "BlockTextures" / "Nakasar" / "Lore"
ICONS = COMMON / "Icons" / "Items" / "Nakasar" / "Lore"
ITEMS = SERVER / "Item" / "Items" / "Deco" / "Nakasar" / "Lore"
HITBOXES = SERVER / "Item" / "Block" / "Hitboxes" / "Nakasar"
INTERACTIONS = SERVER / "Item" / "Interactions" / "Nakasar" / "Lore"
LANG = SERVER / "Languages"
LANG_FILE = "nakasar_lore"

BOARD = "Nakasar_Contract_Board"
# Premier contrat, remis par le tableau de la brèche : la Bête de la ferme, clé de fragment de prime de la voie des
# chasseurs (tools/generate_contracts.py). Tant que l'objet n'existe pas, le tableau n'affiche que sa note.
FIRST_CONTRACT = "Nakasar_Contract_Farm"
READ = "Nakasar_Read_Lore"
TAKE_CONTRACT = "Nakasar_Take_First_Contract"

# --- textes -----------------------------------------------------------------------------------
# Ton : phrases courtes, rien n'est tout expliqué. « \n » = retour à la ligne dans la page.
# id -> (style, titre fr, texte fr, titre en, texte en)

LORE = {
    # Les chasseurs : leur traque, leurs pertes, leurs méthodes.
    "Hunter_Orders": ("parchment", "Ordres du camp",
        "Personne ne touche au maître du manoir, ni à sa dame.\nIls nous regardent passer et ne bougent pas. Tant qu'ils ne bougent pas, nous non plus.\nQui frappe l'un d'eux nous condamne tous : ils ne font pas de détail.",
        "Camp orders",
        "Nobody touches the master of the manor, nor his lady.\nThey watch us pass and do not move. As long as they stay still, so do we.\nWhoever strikes one of them dooms us all: they make no distinction."),
    "Hunter_Log": ("parchment", "Journal de traque, page arrachée",
        "Troisième nuit dans le Comté. Bertrand n'est pas revenu de la ferme brûlée.\nOn a retrouvé sa lanterne, encore allumée. Les morts n'avaient pas osé l'approcher.\nLe feu blanc marche. Il nous faut plus d'huile.",
        "Hunting log, torn page",
        "Third night in the County. Bertrand did not come back from the burnt farm.\nWe found his lantern, still lit. The dead had not dared come near it.\nThe white fire works. We need more oil."),
    "Hunter_Silver": ("parchment", "Note sur l'argent",
        "Ne gaspillez pas les carreaux d'argent sur les cadavres qui marchent : le fer suffit pour eux.\nGardez l'argent pour ceux qui ont des crocs. Il les mord deux fois plus fort.",
        "A note on silver",
        "Do not waste silver bolts on walking corpses: iron is enough for them.\nKeep the silver for those with fangs. It bites them twice as hard."),
    "Hunter_Missing": ("scrap", "Liste des disparus",
        "Bertrand : la ferme brûlée.\nAlix : le poste de garde. Les cellules, sans doute.\nMathurin : le manoir. Il voulait « parler » au Comte.\nOn ne parle pas au Comte.",
        "List of the missing",
        "Bertrand: the burnt farm.\nAlix: the guard post. The cells, most likely.\nMathurin: the manor. He wanted to \"talk\" to the Count.\nOne does not talk to the Count."),
    "Hunter_Pumpkins": ("scrap", "Avertissement griffonné",
        "Les champs de citrouilles ne sont pas des champs.\nSi la terre bouge sous vos pieds, courez. Si une vrille vous tient, coupez-la avant qu'elle ne vous tire sous terre.\nLe feu les fait hurler.",
        "Scribbled warning",
        "The pumpkin fields are not fields.\nIf the ground moves under your feet, run. If a vine grabs you, cut it before it drags you under.\nFire makes them scream."),
    # Le point d'arrivée : un mot laissé par les chasseurs pour ceux qui passent la faille.
    "Arrival": ("parchment", "À qui passe la faille",
        "Te voilà dans le Comté. Les morts ne t'aiment pas, les gardes non plus.\nLe Comte, lui, te regardera passer. Ne le provoque pas : sa colère tombe sur tous ceux qui sont là.\nNotre camp brûle d'un feu blanc. Cherche-le.",
        "To whoever crosses the rift",
        "Here you are in the County. The dead do not like you, nor do the guards.\nThe Count will watch you pass. Do not provoke him: his wrath falls on everyone present.\nOur camp burns with a white fire. Look for it."),
    # Les anciens habitants : la vie avant, la chute.
    "Village_Letter": ("letter", "Lettre jamais envoyée",
        "Ma chère sœur,\nLe Comte a fait sonner la cloche du manoir trois soirs de suite. Personne ne sait pourquoi.\nLes moissons sont belles cette année. Viens pour la fête des citrouilles, nous t'attendons.",
        "A letter never sent",
        "My dear sister,\nThe Count had the manor bell rung three evenings in a row. Nobody knows why.\nThe harvest is fine this year. Come for the pumpkin feast, we are waiting for you."),
    "Village_Curfew": ("parchment", "Avis du bailli",
        "Par ordre du Comte : couvre-feu dès la tombée du jour.\nLes portes restent closes. Ceux qui sortent la nuit ne sont plus sous Sa protection.",
        "The bailiff's notice",
        "By order of the Count: curfew from nightfall.\nDoors stay shut. Those who go out at night are no longer under His protection."),
    "Farm_Ledger": ("parchment", "Registre de la ferme",
        "Récolte : quarante boisseaux.\nDîme au manoir : vingt boisseaux, et une fiole de sang par foyer.\nLe père Anselme dit que c'est le prix de la paix.",
        "Farm ledger",
        "Harvest: forty bushels.\nTithe to the manor: twenty bushels, and one vial of blood per household.\nFather Anselme says it is the price of peace."),
    "Farm_Diary": ("scrap", "Carnet d'une fermière",
        "Les citrouilles poussent trop vite depuis que la terre a bu le sang de la dîme.\nLa nuit, elles bougent. Joseph dit que je rêve.\nJoseph n'est pas rentré du champ.",
        "A farmer's notebook",
        "The pumpkins grow too fast since the earth drank the blood of the tithe.\nAt night, they move. Joseph says I am dreaming.\nJoseph has not come back from the field."),
    "Village_Last": ("scrap", "Mot gratté sur une porte",
        "Ils sont revenus du cimetière.\nIls ont frappé à nos portes avec les mains de nos pères.\nNe leur ouvrez pas.",
        "Words scratched on a door",
        "They came back from the graveyard.\nThey knocked on our doors with our fathers' hands.\nDo not open."),
    # Les gardes : la loi du Comte, les prisonniers.
    "Guard_Orders": ("parchment", "Consignes de garde",
        "Toute personne surprise dehors la nuit sera conduite aux cellules.\nLe Capitaine choisit qui monte au manoir.\nNe posez pas de questions sur ceux qui montent.",
        "Guard instructions",
        "Anyone caught outside at night is to be taken to the cells.\nThe Captain chooses who goes up to the manor.\nAsk no questions about those who go up."),
    "Guard_Oath": ("parchment", "Serment de la garde",
        "Je sers le Comte de mon vivant\net au-delà.",
        "The guard's oath",
        "I serve the Count in life\nand beyond."),
    "Prisoner": ("scrap", "Griffonné sur un bout de toile",
        "Ils m'ont pris à la lisière. Le Capitaine dit que je suis « réservé ».\nLa nuit, j'entends chanter au manoir.\nSi quelqu'un trouve ceci : le Capitaine ne quitte jamais ses cellules de vue.",
        "Scrawled on a scrap of cloth",
        "They caught me at the edge of the woods. The Captain says I am \"reserved\".\nAt night I hear singing from the manor.\nIf anyone finds this: the Captain never lets his cells out of sight."),
    # Le manoir : le Comte, la Comtesse et leurs serviteurs.
    "Count_Journal": ("letter", "Journal du Comte",
        "Ils reviennent, avec leurs torches blanches et leur argent. Qu'ils viennent.\nJe ne les combats pas : je les regarde. Parmi eux, il en est toujours un qui finit par écouter ce que le sang murmure.\nCelui-là, je l'attends.",
        "The Count's journal",
        "They come back, with their white torches and their silver. Let them come.\nI do not fight them: I watch them. Among them there is always one who ends up listening to what the blood whispers.\nThat one, I wait for."),
    "Countess_Letter": ("letter", "Lettre de la Comtesse",
        "Mon cher époux,\nVous êtes trop patient avec ces chasseurs. Mais je reconnais votre sagesse : un ennemi qui vous craint est un ennemi qui vous apprend.\nL'autel a encore soif. Faites monter le prochain.",
        "The Countess's letter",
        "My dear husband,\nYou are too patient with these hunters. But I grant you your wisdom: an enemy who fears you is an enemy who teaches you.\nThe altar is thirsty again. Have the next one brought up."),
    "Servant_Rules": ("parchment", "Règles de la maison",
        "Ne jamais ouvrir les rideaux de la chambre du Maître.\nNe jamais servir d'ail à table.\nNe jamais lever la main sur le Maître. Le dernier qui l'a fait a entraîné tout le village avec lui.",
        "House rules",
        "Never open the curtains of the Master's room.\nNever serve garlic at table.\nNever raise a hand against the Master. The last one who did took the whole village down with him."),
    "Ritual_Page": ("letter", "Page de rituel",
        "Le sang offert ouvre la porte.\nLe sang bu la referme derrière toi.\nAu matin, le soleil te sera étranger.",
        "Ritual page",
        "Blood offered opens the door.\nBlood drunk closes it behind you.\nIn the morning, the sun will be a stranger to you."),
    "Blood_Pact": ("letter", "Le pacte",
        "Nous, gens du Comté, offrons au Seigneur la dîme du sang.\nLe Seigneur nous garde de la nuit.\nSigné de cent croix.",
        "The pact",
        "We, the people of the County, offer the Lord the tithe of blood.\nThe Lord keeps us from the night.\nSigned with a hundred crosses."),
    # La Tour de l'Alchimiste : son journal, les lettres qu'il a reçues, la peur d'un apprenti. Posées par
    # alchemist_tower.Tower.lore (TOWER_NOTES), une par salle, trois dans le Bureau.
    "Tower_Hunter_Orders": ("parchment", "Ordre de mission",
        "L'Alchimiste de la tour ne sera plus consulté. Le hameau du col a perdu onze âmes cet automne, et leurs traces montent toutes vers son île.\nNous lui avons acheté le secret de l'argent infusé. Nous avons eu tort de fermer les yeux sur le prix.\nAllez-y à plusieurs. Ne buvez rien de ce qu'il distille.\nL'Ordre des chasseurs",
        "Mission orders",
        "The Alchemist of the tower is no longer to be consulted. The hamlet by the pass lost eleven souls this autumn, and all their tracks climb towards his island.\nWe bought the secret of infused silver from him. We were wrong to look away from the price.\nGo in numbers. Drink nothing he distils.\nThe Order of Hunters"),
    "Alchemist_Journal_1": ("letter", "Journal de l'Alchimiste, page I",
        "Le sel fixe, le soufre brûle, le mercure fuit. Tout le Grand Œuvre tient dans ces trois verbes.\nCeux d'en bas appellent cela de la magie. Ils ont tort. C'est une recette, et je suis le seul à savoir la suivre jusqu'au bout.\nTrois athanors allumés, et la tour respire.",
        "The Alchemist's journal, page I",
        "Salt fixes, sulphur burns, mercury flees. The whole Great Work lies in those three verbs.\nThose below call it magic. They are wrong. It is a recipe, and I alone know how to follow it to the end.\nThree athanors lit, and the tower breathes."),
    "Alchemist_Journal_2": ("letter", "Journal de l'Alchimiste, page II",
        "Les chasseurs sont revenus. Toujours les mêmes bottes boueuses, les mêmes questions : comment faire mordre l'argent plus fort.\nJe leur ai vendu la réponse. Ils paient bien, et ils ne demandent jamais ce que j'en fais, de leur or.\nLes plantes de la serre ont faim. Elles ne mangent plus de terreau.",
        "The Alchemist's journal, page II",
        "The hunters came back. The same muddy boots, the same questions: how to make silver bite harder.\nI sold them the answer. They pay well, and they never ask what I do with their gold.\nThe greenhouse plants are hungry. They no longer eat compost."),
    "Alchemist_Journal_3": ("letter", "Journal de l'Alchimiste, page III",
        "Un serviteur du Comte, cette nuit, pâle comme son maître. Le Comte voudrait marcher au soleil, et il croit que ma pierre le lui permettra.\nJ'ai refusé. Le lendemain, trois de mes cahiers manquaient.\nLes chasseurs volent pour tuer, le Comte vole pour vivre. Je ne prête plus mes livres : ils se défendent seuls, à présent.",
        "The Alchemist's journal, page III",
        "A servant of the Count, tonight, as pale as his master. The Count wishes to walk in the sun, and believes my stone will let him.\nI refused. The next day, three of my notebooks were missing.\nHunters steal to kill, the Count steals to live. I no longer lend my books: they defend themselves now."),
    "Alchemist_Journal_4": ("letter", "Journal de l'Alchimiste, page IV",
        "Distillé le feu, la glace, la foudre et la racine jusqu'à ce qu'ils tiennent debout. Ils obéissent mieux que mes apprentis.\nLe golem de cristal garde l'escalier. Il ne dort pas, il ne mange pas, il ne pose pas de questions.\nMais aucun ne vit vraiment. Il manque quelque chose, et je sais déjà quoi.",
        "The Alchemist's journal, page IV",
        "Distilled fire, ice, lightning and root until they could stand. They obey better than my apprentices.\nThe crystal golem guards the stair. It does not sleep, it does not eat, it asks no questions.\nBut none of them truly lives. Something is missing, and I already know what."),
    "Alchemist_Journal_5": ("letter", "Journal de l'Alchimiste, page V",
        "La bête a cessé de voler le jour où je lui ai cousu le cœur. Elle reste au sol, au fond du laboratoire, et elle boit l'acide comme d'autres boivent du vin.\nLes morts du hameau portent les seaux. Ils ne se plaignent pas.\nJ'appelle cela une chimère. Les chasseurs appelleraient cela un crime.",
        "The Alchemist's journal, page V",
        "The beast stopped flying the day I stitched its heart. It stays on the ground, at the back of the laboratory, and drinks acid as others drink wine.\nThe dead of the hamlet carry the buckets. They do not complain.\nI call it a chimera. The hunters would call it a crime."),
    "Alchemist_Journal_6": ("letter", "Journal de l'Alchimiste, page VI",
        "Ce qui manque à la pierre, c'est la vie. Une vie par goutte de rouge.\nLe hameau du col en a assez pour finir l'œuvre. Ils ne savent rien faire de leurs vies, de toute façon.\nSi l'on vient me chercher, je fermerai la terrasse. Que les éléments décident.",
        "The Alchemist's journal, page VI",
        "What the stone lacks is life. One life for each drop of red.\nThe hamlet by the pass has enough to finish the work. They do nothing with their lives anyway.\nIf they come for me, I will close the terrace. Let the elements decide."),
    "Alchemist_Journal_7": ("letter", "Journal de l'Alchimiste, dernière page",
        "Elle est rouge. Elle est chaude. Elle bat, je le jure, comme un cœur qu'on tient dans la main.\nJ'en ai fait assez pour tous ceux qui monteront jusqu'ici : qu'ils la prennent. Qu'ils sachent seulement ce qu'elle a coûté.\nOnze noms. Je ne les ai pas écrits. J'aurais dû.",
        "The Alchemist's journal, last page",
        "It is red. It is warm. It beats, I swear it, like a heart held in the hand.\nI made enough for everyone who climbs this far: let them take it. Let them only know what it cost.\nEleven names. I did not write them down. I should have."),
    "Tower_Count_Letter": ("letter", "Lettre au cachet de sang, jamais ouverte",
        "Maître alchimiste,\nJe ne vous demande pas votre science, seulement son fruit. Une pierre, une seule, et ma maison vous protégera de l'Ordre aussi longtemps que vous vivrez.\nJe sais attendre. Ne me faites pas attendre trop longtemps.\nLe Comte",
        "Letter with a blood seal, never opened",
        "Master alchemist,\nI do not ask for your science, only its fruit. One stone, a single one, and my house will shield you from the Order for as long as you live.\nI know how to wait. Do not make me wait too long.\nThe Count"),
    "Tower_Hunter_Plea": ("letter", "Lettre de l'Ordre",
        "Ami,\nNos carreaux d'argent infusé ont sauvé plus de vies cet hiver que nos épées en dix ans. Nous vous en devons beaucoup.\nC'est pourquoi nous vous écrivons au lieu de monter : des gens disparaissent au col. On dit qu'on vous a vu là-bas, la nuit.\nDites-nous que c'est faux.",
        "Letter from the Order",
        "Friend,\nOur infused silver bolts saved more lives this winter than our swords did in ten years. We owe you a great deal.\nThat is why we write instead of climbing: people are vanishing at the pass. They say you were seen there, at night.\nTell us it is not true."),
    "Tower_Apprentice": ("scrap", "Mot d'un apprenti, plié en quatre",
        "Le maître a ramené Élise du hameau. Il a dit qu'elle allait m'aider au laboratoire.\nJe ne l'ai pas revue. Ce soir, la cuve est plus rouge.\nSi quelqu'un trouve ce mot : je suis parti par le couloir. Le gaz ne m'arrêtera pas.",
        "An apprentice's note, folded in four",
        "The master brought Élise back from the hamlet. He said she would help me in the laboratory.\nI have not seen her since. Tonight, the vat is redder.\nIf anyone finds this note: I left through the corridor. The gas will not stop me."),
}

EPITAPHS = {
    "Anselme": ("Ci-gît le père Anselme",
        "Il a béni la dîme.\nQu'il repose, s'il le peut.",
        "Here lies Father Anselme", "He blessed the tithe.\nMay he rest, if he can."),
    "Joseph": ("Ici repose Joseph, laboureur",
        "Enterré deux fois.",
        "Here rests Joseph, ploughman", "Buried twice."),
    "Rose": ("À notre fille Rose",
        "Emportée par la fièvre pâle.\nElle ne craignait plus que la lumière du jour.",
        "To our daughter Rose", "Taken by the pale fever.\nIn the end she feared only daylight."),
    "Morvan": ("Famille Morvan",
        "Le caveau est vide.\nNe le refermez pas.",
        "The Morvan family", "The vault is empty.\nDo not close it again."),
    "Gauvain": ("Sire Gauvain, capitaine de la garde",
        "Fidèle au Comte,\npar-delà la mort.",
        "Sir Gauvain, captain of the guard", "Faithful to the Count,\nbeyond death."),
    "Nameless": ("Sans nom",
        "Un chasseur. Nous n'avons pas pu emporter le corps.",
        "Nameless", "A hunter. We could not carry the body away."),
}

BOARD_TEXT = ("Tableau des chasseurs",
    "Nous cherchons des bras. Passez la faille.\n\nDe l'autre côté s'étend le Comté : des morts qui marchent, une garde d'os, et au manoir, ceux qu'on ne nomme pas.\nL'argent mord leur chair. Le feu blanc les tient à distance.\n\nUn contrat est épinglé ici, un seul par passage de la faille : le premier qui le prend part pour une ferme du Comté, et la bête qui garde sa grange. Pose-le dans une passerelle ancienne, abats-la, et la prime est à toi.\n\nL'Ordre des chasseurs",
    "Hunters' board",
    "We need hands. Cross the rift.\n\nBeyond it lies the County: walking dead, a guard of bones, and in the manor, those we do not name.\nSilver bites their flesh. White fire keeps them at bay.\n\nOne contract is pinned here, only one each time the rift opens: whoever takes it first heads for a County farm, and the beast guarding its barn. Place it in an ancient gateway, slay the beast, and the bounty is yours.\n\nThe Order of Hunters")

# Où trouver quoi : notes posées dans les prefabs et tirées dans les coffres (generate_prefabs.py, generate_loot.py).
# Les notes du manoir ne sont plus que posées (LORE_BY_SPOT).
NOTES_BY_PLACE = {
    "hunter": ["Hunter_Log", "Hunter_Silver", "Hunter_Missing", "Hunter_Pumpkins", "Hunter_Orders"],
    "village": ["Village_Letter", "Village_Curfew", "Farm_Ledger", "Village_Last"],
    "farm": ["Farm_Ledger", "Farm_Diary", "Village_Letter"],
    "guard": ["Guard_Orders", "Guard_Oath", "Prisoner"],
    "manor": ["Count_Journal", "Countess_Letter", "Servant_Rules", "Ritual_Page", "Blood_Pact"],
}

# Coffres qui portent du lore, par liste de butin : (lieu, notes posées à côté du coffre, chance d'en poser une,
# poids du tirage vide quand le coffre tire une note du lieu). Seule source pour generate_prefabs.py et generate_loot.py.
LORE_BY_LOOT = {
    "Nakasar_Loot_Hunter_Camp": ("hunter", ["Hunter_Orders"], 1.0, 4),
    "Nakasar_Loot_Hunter_Armory": ("hunter", NOTES_BY_PLACE["hunter"][:4], 1.0, 3),
    "Nakasar_Loot_Village_House": ("village", NOTES_BY_PLACE["village"], 0.4, 6),
    "Nakasar_Loot_Village_Rich": ("village", ["Village_Letter"], 1.0, 3),
    "Nakasar_Loot_Farm": ("farm", NOTES_BY_PLACE["farm"], 0.6, 6),
    "Nakasar_Loot_Farm_Burnt": ("farm", ["Farm_Diary", "Village_Last"], 0.6, 4),
    "Nakasar_Loot_Guard_Barracks": ("guard", ["Guard_Orders"], 1.0, 5),
    "Nakasar_Loot_Guard_Captain": ("guard", ["Guard_Oath"], 1.0, 2),
}

# Lieux de lore sans coffre (Prefab.lore_spot) : le manoir du Comte n'a plus de coffres (le Comte est passif, on ne
# pille pas sa demeure), mais ses notes restent posées là où ils étaient : (notes posées, chance d'en poser une).
LORE_BY_SPOT = {
    "Manor_Library": (["Count_Journal"], 1.0),
    "Manor_Bedroom": (["Countess_Letter"], 1.0),
    "Manor_Kitchen": (["Servant_Rules"], 1.0),
    "Manor_Alchemy": (["Ritual_Page"], 1.0),
    "Manor_Treasure": (["Blood_Pact"], 1.0),
}


def note_id(name):
    return f"Nakasar_Lore_{name}"


def epitaph_id(name):
    return f"Nakasar_Epitaph_{name}"


# --- modèles ----------------------------------------------------------------------------------
# Repère de generate_assets.py : 32 unités = 1 bloc, origine au centre du bas, face avant vers +Z.

PAPER = (222, 204, 160)
PAPER_OLD = (196, 174, 128)
INK = (58, 40, 30)
WAX = (150, 22, 30)
CLOTH = (150, 140, 124)
WOOD = (104, 74, 50)
WOOD_DARK = (70, 48, 32)
STONE = (112, 110, 112)
STONE_DARK = (74, 72, 76)
NAIL = (60, 58, 62)


def written(base, lines=True, edge=0.82):
    """Feuille écrite : dessus couleur papier avec des lignes d'encre, tranches plus sombres."""

    def paint(rng, w, h, face):
        img = Image.new("RGBA", (w, h))
        px = img.load()
        noise = gx.soft_noise(rng, w, h, scale=4, amp=0.06)
        for y in range(h):
            for x in range(w):
                f = noise[y][x] * (1.0 if face in ("top", "front") else edge)
                if min(x, y, w - 1 - x, h - 1 - y) == 0 and min(w, h) > 3:
                    f *= 0.9
                px[x, y] = gx.shade(base, f) + (255,)
        if lines and face in ("top", "front") and min(w, h) > 5:
            for y in range(2, h - 2, 2):
                end = w - 2 - rng.randint(0, max(1, w // 3))
                for x in range(2, max(3, end)):
                    if rng.random() > 0.12:
                        px[x, y] = gx.shade(INK, rng.uniform(0.9, 1.3)) + (255,)
        return img

    return paint


def engraved(base):
    """Pierre gravée : la face avant porte quelques lignes creusées."""
    stone = gx.painter(base, moss=0.25)

    def paint(rng, w, h, face):
        img = stone(rng, w, h, face)
        if face == "front" and w > 8 and h > 10:
            px = img.load()
            for y in range(4, h - 4, 3):
                x0, x1 = 3 + rng.randint(0, 1), w - 3 - rng.randint(0, 2)
                for x in range(x0, x1):
                    px[x, y] = gx.shade(STONE_DARK, 0.8) + (255,)
        return img

    return paint


def note_parts(style):
    if style == "letter":
        return [
            ("Sheet", (0, 0.25, 0), (13, 0.5, 17), 14, written(PAPER), "flat"),
            ("Fold", (0, 0.75, -4), (13, 0.5, 6), 14, written(PAPER_OLD, lines=False), "flat"),
            ("Seal", (0, 1.25, -1), (3, 0.5, 3), 14, gx.painter(WAX), "flat"),
        ]
    if style == "scrap":
        return [
            ("Cloth", (0, 0.25, 0), (12, 0.5, 14), -18, written(CLOTH), "flat"),
            ("Corner", (5, 0.25, 6), (5, 0.5, 5), 25, written(CLOTH, lines=False), "flat"),
        ]
    return [
        ("Sheet", (0, 0.25, 0), (14, 0.5, 18), 12, written(PAPER_OLD), "flat"),
        ("Sheet_Under", (-1, 0.25, 1), (14, 0.4, 18), -8, written(PAPER, lines=False), "flat"),
    ]


def headstone_parts():
    stone, dark = gx.painter(STONE, moss=0.3), gx.painter(STONE_DARK, moss=0.2)
    return [
        ("Base", (0, 1.5, 0), (20, 3, 10), 0, dark, "flat"),
        ("Stone", (0, 13, 0), (16, 20, 4), 0, engraved(STONE), "flat"),
        ("Arch", (0, 24.5, 0), (12, 3, 4), 0, stone, "flat"),
        ("Arch_Top", (0, 27, 0), (7, 2, 4), 0, stone, "flat"),
    ]


def board_parts():
    wood, dark = gx.painter(WOOD, kind="wood"), gx.painter(WOOD_DARK, kind="wood")
    parts = [
        ("Post_L", (-12, 27, -1), (3, 54, 3), 0, dark, "flat"),
        ("Post_R", (12, 27, -1), (3, 54, 3), 0, dark, "flat"),
        ("Board", (0, 40, 0), (27, 20, 1.5), 0, wood, "flat"),
        ("Frame_Top", (0, 50.5, 0.5), (29, 1.5, 2.5), 0, dark, "flat"),
        ("Frame_Bottom", (0, 29.5, 0.5), (29, 1.5, 2.5), 0, dark, "flat"),
        ("Roof", (0, 55, -0.5), (32, 2, 7), 0, dark, "flat"),
    ]
    sheets = [(-7, 44, 7, 9, PAPER_OLD), (1.5, 45, 6, 8, PAPER), (8, 39, 6, 9, PAPER_OLD), (-5, 35, 8, 6, CLOTH)]
    for k, (x, y, w, h, colour) in enumerate(sheets):
        parts.append((f"Sheet_{k}", (x, y, 1.05), (w, h, 0.6), 0, written(colour), "flat"))
        parts.append((f"Nail_{k}", (x, y + h / 2 - 1, 1.6), (1, 1, 0.6), 0, gx.painter(NAIL, "iron"), "flat"))
    # le premier contrat : rouge, cacheté
    parts.append(("Contract", (0, 36, 1.05), (6, 7, 0.6), 0, written((214, 186, 150)), "flat"))
    parts.append(("Contract_Seal", (0, 34, 1.6), (2, 2, 0.6), 0, gx.painter(WAX), "flat"))
    return parts


# style -> (fichier, pièces, hitbox, son du bloc, particules, couleur, centre du rendu, hauteur du rendu)
STYLES = {
    "parchment": ("Note_Parchment", lambda: note_parts("parchment"), "Nakasar_Lore_Note", "Wood", "Wood", "#c4ae80", (0, 1, 0), 22),
    "letter": ("Note_Letter", lambda: note_parts("letter"), "Nakasar_Lore_Note", "Wood", "Wood", "#decca0", (0, 1, 0), 22),
    "scrap": ("Note_Scrap", lambda: note_parts("scrap"), "Nakasar_Lore_Note", "Wood", "Wood", "#968c7c", (0, 1, 0), 22),
    "epitaph": ("Epitaph", headstone_parts, "Nakasar_Epitaph", "Stone", "Stone", "#706e70", (0, 14, 0), 34),
    "board": ("Contract_Board", board_parts, BOARD, "Wood", "Wood", "#684a32", (0, 30, 0), 62),
}


# --- objets -----------------------------------------------------------------------------------

def lore_item(block_id, style, files, use):
    _, _, hitbox, sound, particles, color, _, _ = STYLES[style]
    model, texture, icon = files
    flat = style in ("parchment", "letter", "scrap")
    bt = {
        # Une note au sol ne bloque pas le passage ; pierre tombale et tableau, si.
        "Material": "Empty" if flat else "Solid",
        "DrawType": "Model",
        "Opacity": "Transparent",
        "CustomModel": gx.rel(model),
        "CustomModelTexture": [{"Texture": gx.rel(texture), "Weight": 1}],
        "HitboxType": hitbox,
        "VariantRotation": "NESW",
        "PlacementSettings": {"RotationMode": "FacingPlayer"},
        "Support": {"Down": [{"FaceType": "Full"}]},
        # Les notes se ramassent (comme une note trouvée dans un coffre) ; tombes et tableau restent en place.
        "Gathering": {"Breaking": {"GatherType": "Benches" if flat else "Unbreakable"}},
        "BlockParticleSetId": particles,
        "BlockSoundSetId": sound,
        "ParticleColor": color,
        "Interactions": {"Use": use},
    }
    return {
        "TranslationProperties": {"Name": f"{LANG_FILE}.items.{block_id}.name",
                                  "Description": f"{LANG_FILE}.items.{block_id}.description"},
        "Icon": gx.rel(icon),
        "Categories": ["Blocks.Deco"],
        "PlayerAnimationsId": "Block",
        "Quality": "Uncommon" if flat else "Common",
        "BlockType": bt,
        "Tags": {"Type": ["Deco"]},
        "ItemSoundSetId": "ISS_Blocks_Wood" if sound == "Wood" else "ISS_Blocks_Stone",
    }


def lang_value(text):
    return text.replace("\n", "\\n")


def write_lang(entries):
    for lang, idx in (("fr-FR", 0), ("en-US", 1)):
        lines = [f"# Lore du Comté Vampire (notes, épitaphes, tableau de la brèche) : généré par tools/generate_lore.py",
                 f"# {'textes français' if idx == 0 else 'English texts'}"]
        for block_id, fr, en in entries:
            title, text = fr if idx == 0 else en
            lines.append(f"items.{block_id}.name = {lang_value(title)}")
            lines.append(f"items.{block_id}.description = {lang_value(text)}")
        path = LANG / lang / f"{LANG_FILE}.lang"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    preview = None
    if "--preview" in sys.argv:
        preview = Path(sys.argv[sys.argv.index("--preview") + 1])
        preview.mkdir(parents=True, exist_ok=True)
    for old in list(ITEMS.glob("*.json")) if ITEMS.exists() else []:
        old.unlink()
    files = {}
    for i, (style, (name, build, _, _, _, _, center, height)) in enumerate(STYLES.items()):
        parts = build()
        atlas, uv = gx.build_atlas(parts, seed=700 + i, tex_w=64)
        model, texture, icon = MODELS / f"{name}.blockymodel", TEXTURES / f"{name}.png", ICONS / f"{name}.png"
        for path in (model, texture, icon):
            path.parent.mkdir(parents=True, exist_ok=True)
        atlas.save(texture)
        model.write_text(json.dumps(gx.build_model(name, parts, uv), indent=2) + "\n", encoding="utf-8")
        scale = 256 / (height * 1.5)
        pitch = 55 if height < 30 else 18
        big = gx.render(parts, atlas, uv, 256, yaw=-30, pitch=pitch, scale=scale, center=center)
        big.resize((64, 64), Image.LANCZOS).save(icon)
        if preview:
            gx.render(parts, atlas, uv, 512, yaw=-30, pitch=pitch, scale=scale * 2, center=center).save(preview / f"{name}.png")
        files[style] = (model, texture, icon)

    # La page de lore du jeu lit le titre et le texte dans l'objet du bloc visé.
    gx.write_json(INTERACTIONS / f"{READ}.json", {
        "$Comment": "Ouvre la page de lore du jeu : nom de l'objet du bloc en titre, sa description en texte. Généré par tools/generate_lore.py.",
        "Type": "OpenCustomUI",
        "Page": {"Id": "BlockLore", "TextAlignment": "Left"},
    })
    gx.write_json(INTERACTIONS / f"{TAKE_CONTRACT}.json", {
        "$Comment": "Tableau de la brèche : remet le premier contrat, une seule fois par brèche pour tout le serveur, puis affiche la note. Généré par tools/generate_lore.py.",
        "Type": "Nakasar_ClaimBreachContract",
        "ItemId": FIRST_CONTRACT,
        "Next": {"Type": "OpenCustomUI", "Page": {"Id": "BlockLore", "TextAlignment": "Left"}},
    })
    read = {"Interactions": [READ]}
    entries = []
    for name, (style, fr_t, fr, en_t, en) in LORE.items():
        block_id = note_id(name)
        gx.write_json(ITEMS / f"{block_id}.json", lore_item(block_id, style, files[style], read))
        entries.append((block_id, (fr_t, fr), (en_t, en)))
    for name, (fr_t, fr, en_t, en) in EPITAPHS.items():
        block_id = epitaph_id(name)
        gx.write_json(ITEMS / f"{block_id}.json", lore_item(block_id, "epitaph", files["epitaph"], read))
        entries.append((block_id, (fr_t, fr), (en_t, en)))
    gx.write_json(ITEMS / f"{BOARD}.json", lore_item(BOARD, "board", files["board"], {"Interactions": [TAKE_CONTRACT]}))
    entries.append((BOARD, BOARD_TEXT[:2], BOARD_TEXT[2:]))
    write_lang(entries)

    # Hitboxes (unités de 32 par bloc, origine au centre du bas).
    gx.write_json(HITBOXES / "Nakasar_Lore_Note.json", {"Boxes": [gx.hitbox_box(-9, 0, -10, 9, 3, 10)]})
    gx.write_json(HITBOXES / "Nakasar_Epitaph.json", {"Boxes": [gx.hitbox_box(-10, 0, -5, 10, 29, 5)]})
    gx.write_json(HITBOXES / f"{BOARD}.json", {"Boxes": [gx.hitbox_box(-14, 0, -3, 14, 56, 3)]})
    print(f"lore : {len(LORE)} notes, {len(EPITAPHS)} épitaphes, tableau de contrats")


if __name__ == "__main__":
    main()
