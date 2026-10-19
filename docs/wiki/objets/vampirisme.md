# Devenir vampire

La voie occulte : à l'[autel sacrificiel](autel-sacrificiel.md), un rituel fait de vous un vampire, un autre vous rend la vie. Chaque joueur a son propre état, sauvegardé avec lui.

## Le rituel {#le-rituel}

| | Objet | Effet | Fabrication |
|---|---|---|---|
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Ritual_Chalice.png) | **Calice du sang éternel** | Vous devenez vampire, à moitié affamé | Autel niveau 3, onglet Rituels |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Purification_Censer.png) | **Encensoir de purification** | Vous redevenez vivant | Autel niveau 3, onglet Rituels |

Utilisez l'objet (clic droit) à **5 blocs au plus d'un autel sacrificiel**. Loin d'un autel, ou si vous êtes déjà dans l'état visé, rien ne se passe et l'objet n'est pas consommé. Le rituel affiche un titre, joue un son autour de vous et dépose une note dans votre inventaire.

## La soif de sang {#soif}

Un vampire ne se nourrit plus de nourriture : manger ne lui rend rien et ne régénère plus sa vie. Sa **réserve de sang** baisse de pleine à vide en **1,5 jour de jeu**. Le palier en cours s'affiche comme effet de statut.

| Palier | Réserve | Régénération |
|---|---|---|
| ![icône](/jeu/UI/StatusEffects/Nakasar/Occult/Blood_Sated.png) Rassasié de sang | 75 % et plus | 1 PV/s |
| ![icône](/jeu/UI/StatusEffects/Nakasar/Occult/Blood_Hunger_3.png) Soif légère | 50 à 75 % | 0,6 PV/s |
| ![icône](/jeu/UI/StatusEffects/Nakasar/Occult/Blood_Hunger_2.png) Soif | 25 à 50 % | 0,35 PV/s |
| ![icône](/jeu/UI/StatusEffects/Nakasar/Occult/Blood_Hunger_1.png) Soif dévorante | moins de 25 % | 0,15 PV/s |
| ![icône](/jeu/UI/StatusEffects/Nakasar/Occult/Blood_Starving.png) Affamé de sang | vide | aucune ; vos coups sont plus lents (dégâts réduits si vous frappez trop vite) et vous entendez battre le cœur du vivant le plus proche (14 blocs) |

Pour boire :

- **[Baiser du Vampire](runes.md#baiser-du-vampire)** sur un être vivant (joueur non vampire, animal, chasseur...) : +8 % de sang, 8 dégâts et 6 PV de plus. Les morts-vivants et les vampires n'ont pas de sang.
- **[Nova de sang](#nova-de-sang)** : +5 % de sang par cible vivante.
- ![icône](/jeu/Icons/Items/Nakasar/Occult/Blood_Vial.png) **Fiole de sang** : +35 % de sang. Elle ne se boit pas si votre réserve est pleine. Un vivant qui la boit a la nausée 12 s.

La nuit, un vampire voit dans le noir : une faible lumière rouge l'entoure.

## Le soleil {#soleil}

De jour, sous le ciel, le soleil brûle un vampire. Un toit au-dessus de la tête protège entièrement. La pluie, la neige, le brouillard ou les nuages réduisent le soleil de moitié ; l'orage l'annule. Le soleil est plus faible à l'aube et au crépuscule.

En plein soleil :

- jusqu'à **2 dégâts par seconde** ;
- vous subissez jusqu'à **+50 % de tous les dégâts** ;
- vos coups sont plus lents (dégâts réduits si vous frappez trop vite) ;
- l'écran s'éblouit (effet [Brûlé par le soleil](../effets.md#brule-par-le-soleil)).

Protections (elles ne se cumulent pas, la meilleure compte) :

| | Protection | Soleil retenu | Durée | Fabrication |
|---|---|---|---|---|
| | **Capuche occulte** (tête) | 30 % | portée | Autel niveau 2 : capuche en cuir souple, 1 rouleau de tisse-ombre, 4 cendres |
| | **Voile occulte** (torse) | 25 % | porté | Autel niveau 3 : tunique en cuir souple, 2 rouleaux de tisse-ombre, 1 relique |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Sun_Potion_1.png) | **Voile solaire I** | 40 % | 8 min | Autel niveau 2 |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Sun_Potion_2.png) | **Voile solaire II** | 70 % | 8 min | Autel niveau 3 |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Sun_Potion_3.png) | **Voile solaire III** | 100 % | 3 min | Autel niveau 4 |

## Autres faiblesses

- **Argent :** les [armes et flèches en argent](armes-en-argent.md) font **×2** dégâts à un joueur vampire, comme aux vampires du Comté.
- **Feu purificateur :** près d'une [torche ou lanterne purificatrice](feu-purificateur.md) (7 blocs), un vampire perd 1 PV par seconde.

## Nova de sang {#nova-de-sang}

Une rune de l'autel (niveau 4) : une onde de sang blesse les créatures à 5 blocs autour de vous (10 dégâts) et vous rend de la vie pour chaque cible touchée. Lancée par un vampire, elle fait 5 dégâts et rend 3 PV de plus par cible vivante, et le nourrit. Voir [Runes](runes.md).

## Ingrédients {#ingredients}

| | Ingrédient | Où le trouver |
|---|---|---|
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Blood_Drop.png) | **Sang frais** | Baiser du Vampire sur un vivant (30 % de chance), Nova de sang (15 %) |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Undead_Ash.png) | **Cendres de mort-vivant** | Zombies et gardes squelettes du Comté (1 sur 3, 1 ou 2) |
| ![icône](/jeu/Icons/Items/Nakasar/Occult/Manor_Relic.png) | **Relique du manoir** | [Fantômes](../pnj/fantome.md), coffres du trésor et de l'alchimie du [manoir](../fragment/manoir-du-comte.md) |
