# Comte Vampire

<Infobox title="Comte Vampire" kind="Boss" image={require("../images/pnj/Nakasar_Vampire_Count.jpg").default} caption="Le Comte Vampire en jeu">
<Info label="Points de vie">**900**</Info>
<Info label="Barre de vie">barre de boss en combat</Info>
<Info label="Attitude">Neutre, hostile à tous les joueurs une fois frappé</Info>
<Info label="Lieu">[Manoir du Comte](../fragment/manoir-du-comte.md), 1 par monde</Info>
<Info label="Réapparition">30 min</Info>
<Info label="Faiblesses">Argent ×2, feu purificateur</Info>
<Info label="Butin">1 [rune](../objets/runes.md)</Info>
<Info label="Id">`Nakasar_Vampire_Count`</Info>
</Infobox>

Le maître du Comté. Grand (×1,22), pâle, yeux rouges, couronne noire, long manteau à liseré d'or et cape royale rouge. Il règne sur le [Manoir du Comte](../fragment/manoir-du-comte.md) et partage son trône avec la [Comtesse Vampire](comtesse-vampire.md) : à chaque apparition, c'est l'un ou l'autre (une chance sur deux).

Il se bat à distance comme au corps à corps : il paralyse ses proies avec des chaînes spectrales, leur ôte toute volonté de le frapper, apparaît à côté d'elles en une gerbe de sang et se soigne en mordant. Sous la moitié de ses PV, il appelle ses rejetons.

## Un hôte qui vous laisse passer

Dans le Comté, le Comte **ne vous attaque pas** : il vous regarde passer. Tant que personne ne le frappe, vous pouvez traverser le manoir et combattre ses gardes sous ses yeux.

**Mais ne levez pas la main sur lui.** Au premier coup porté par un joueur (arme, flèche ou sort), il entre en colère contre **tous les joueurs présents**, pas seulement l'attaquant : il change de cible tant qu'un autre joueur est à portée. Sa colère retombe **45 secondes** après le dernier coup échangé ; il rentre alors à son trône, récupère ses PV et redevient pacifique.

On ne pourra le vaincre pour de bon que plus tard, dans un donjon qui lui sera consacré.

## Fiche

| | |
|---|---|
| Points de vie | **900**, affichés dans une **barre de vie de boss** pendant le combat |
| Vitesse | 4,5 |
| Recul subi | ×0,2 |
| Détection | aucune tant qu'on ne le frappe pas ; en colère : 14 blocs (ligne de vue), 20 blocs pour changer de cible |
| Abandon | plus de cible à 40 blocs : rentre à son point d'apparition et **récupère tous ses PV** |
| Attitude | **neutre envers les joueurs** tant qu'aucun ne le frappe, puis hostile à tous pendant sa colère ; allié de toutes les créatures du Comté ; ennemi juré des [chasseurs de vampires](chasseur-epee.md) |
| Groupes | Vampires (argent ×2), Morts-vivants (feu purificateur) |

## Attaques et capacités

| Capacité | Portée | Effet | Fréquence |
|---|---|---|---|
| **Baiser du Vampire** (mêlée) | 3,2 blocs, balayage de 90° | **22** dégâts physiques (±10 %) par cible, et le Comte **récupère 30 PV par cible touchée** | pause de 1,2 à 1,8 s entre deux coups |
| **Chaînes spectrales** | trait de 18 blocs, joueurs seulement | [Chaînes spectrales](../effets.md#chaines-spectrales) **3 s** : immobilisé, plus d'attaque, plus de capacité, plus d'esquive | toutes les 9 à 12 s (première après 4 à 6 s) |
| **Domination** | trait de 12 blocs, joueurs seulement | [Domination du Comte](../effets.md#domination-du-comte) **6 s** : vos coups et vos projectiles ne le blessent plus (vous pouvez toujours bouger et frapper les autres) | toutes les 16 à 20 s (première après 7 à 9 s) |
| **Téléportation** | cible entre 7 et 30 blocs | réapparaît à 1,5 à 2,5 blocs de vous, tourné vers vous | toutes les 10 à 14 s |
| **Appel des rejetons** | sous **50 % de PV** | fait surgir **2 ou 3** [rejetons de vampire](rejeton-de-vampire.md) autour de lui, s'il en reste 2 ou moins dans les 40 blocs | toutes les 30 s |

Chaque attaque à distance est précédée d'un temps de visée (0,3 à 0,6 s) puis d'une courte préparation : c'est le moment de rompre la ligne de vue.

## Butin

| Objet | Quantité | Chance |
|---|---|---|
| Une [rune](../objets/runes.md) parmi Baiser du Vampire, Domination, Téléportation, Chaînes spectrales | 1 | 100 % (25 % chacune) |

## Où le trouver

- Dans le [Manoir du Comte](../fragment/manoir-du-comte.md), un seul par monde (marqueur Comte **ou** Comtesse).
- Réapparition : **30 minutes** (temps réel) après sa mort ; le tirage Comte/Comtesse est refait.

## Conseils

- Avant de le frapper, assurez-vous que **tout le groupe** est prêt : sa colère vise chacun de vous.
- Les **armes en argent** lui infligent **le double de dégâts** ([armes en argent](../objets/armes-en-argent.md)), flèches d'argent comprises.
- Il est un mort-vivant : il fuit le [feu purificateur](../objets/feu-purificateur.md) et y brûle s'il s'y attarde.
- Tuez vite les rejetons : ils sont fragiles mais se soignent en mordant.
- S'il vous perd de vue à plus de 40 blocs, il rentre et se soigne entièrement.
