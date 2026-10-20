# Citrouille géante

<Infobox title="Citrouille géante" kind="Élite immobile" image={require("../images/lieux/citrouille_geante_combat.jpg").default} caption="La Citrouille géante et ses vrilles dans un champ du Comté, en jeu">
<Info label="Points de vie">**750**</Info>
<Info label="Barre de vie">barre de boss en combat</Info>
<Info label="Attitude">Hostile, ne bouge jamais</Info>
<Info label="Lieu">[Champ de citrouilles géant](../fragment/champs-de-citrouilles.md)</Info>
<Info label="Réapparition">30 min</Info>
<Info label="Faiblesses">Feu ×2</Info>
<Info label="Butin">citrouilles, graines, essence, [Graine de la Citrouille géante](../objets/trophees.md)</Info>
<Info label="Id">`Nakasar_Giant_Pumpkin`</Info>
</Infobox>

![Rendu 3D du modèle : au repos et bouche ouverte (crachat)](../images/pnj/Nakasar_Giant_Pumpkin.png)

Une citrouille sculptée de plus de deux blocs de large, éclairée de l'intérieur. Le haut se soulève comme une mâchoire pour cracher du poison. Elle ne bouge jamais : elle fait pousser autour d'elle des [vrilles combattantes](vrille-de-citrouille.md) et enracine ceux qui s'approchent trop.

> Le modèle 3D est en cours de retouche (version plus lisse, vrilles plus espacées). Les rendus de cette page montrent la version actuelle.

## Fiche

| | |
|---|---|
| Points de vie | **750**, affichés dans une **barre de vie de boss** pendant le combat |
| Déplacement | **aucun** (ne bouge pas, insensible au recul) |
| Taille | 2,3 × 2,1 × 2,3 blocs, lumière orange (rayon 10) |
| Détection | 14 blocs (ligne de vue) |
| Abandon | plus de cible à 20 blocs : **récupère tous ses PV** |
| Faiblesse | **feu ×2** (brûlure, lave, bâton de feu...) |
| Groupe | Carré de citrouilles. Ni morte-vivante (le feu purificateur ne l'affecte pas), ni vampire (pas de bonus d'argent). |

## Attaques

| Attaque | Portée | Effet | Fréquence |
|---|---|---|---|
| **Invocation des vrilles** | **n'importe où** de 3 à 11 blocs autour d'elle | une vague de **5** [vrilles de citrouille](vrille-de-citrouille.md) (**6** sous 50 % de vie) ; le sol **bouillonne 1 s** là où chacune va sortir | dès le début du combat (ou au premier coup reçu), puis **10 à 12 s après la destruction** de la vague précédente |
| **Piège de vrilles** (annoncé) | cercle rouge de **6,5 blocs**, **2,2 s** | chaque ennemi touché est saisi par des [vrilles](vrilles.md) : **immobilisé** tant qu'elles ne sont pas détruites (10 s au plus) | toutes les 14 à 18 s (premier après 8 à 10 s), si vous êtes à 6 blocs ou moins |
| **Crachat de poison** | 16 blocs (ligne de vue) | **8** dégâts de poison à l'impact + [Poison de citrouille](../effets.md#poison-de-citrouille) **4 dégâts/s pendant 6 s** | toutes les 7 à 9 s ; sous 50 % de vie, **en éventail de trois** (au centre et 20° de chaque côté) |

**Invulnérable tant que ses vrilles vivent :** tant qu'il reste une vrille de la vague, la citrouille ne subit **aucun dégât** : un **halo doré** l'entoure, sa barre de vie passe en mode invulnérable et un **lien vert** va de chaque vrille à elle. Détruisez d'abord toutes les vrilles, puis frappez-la pendant les 10 à 12 s de répit avant la vague suivante.

**Le piège se voit venir :** le cercle rouge de la [Tour de l'Alchimiste](../donjons/tour-de-l-alchimiste.md), de la taille exacte du piège (6,5 blocs), se remplit au sol pendant **2,2 s**. Sortez-en avant qu'il soit plein. Si vous êtes pris, frappez les vrilles à vos pieds (12 PV) pour vous libérer.

### Seconde moitié

Sous **50 %** de vie, chaque vague compte **6 vrilles** et le crachat part **en éventail de trois** : décalez-vous de biais, pas simplement sur le côté.

### Les lanternes-citrouilles

Quatre **lanternes-citrouilles** se dressent dans la clairière, en diagonale à 4 blocs d'elle. **Un coup les renverse** : le sol prend feu dans un rayon de **3 blocs** pendant **6 s** (**6 dégâts de feu par seconde**, doublés sur les vrilles et la citrouille). Elles se redressent au bout de **90 s**. Attirez les vrilles sur une lanterne avant de la renverser.

## Butin

| Objet | Quantité | Chance |
|---|---|---|
| Citrouille | 3 à 6 | 100 % |
| Graines de citrouille | 2 à 4 | 100 % |
| Essence de vie de citrouille | 1 à 2 | 100 % |
| [Graine de la Citrouille géante](../objets/trophees.md) | 1 | 100 % |

## Où la trouver

Au centre de la clairière d'un [champ de citrouilles géant](../fragment/champs-de-citrouilles.md) (rayon 7), entre quatre lanternes-citrouilles. Un champ de citrouilles sur deux est de ce type. Réapparition : **30 minutes**.

Aussi la cible du [contrat « le Champ maudit »](../objets/contrats.md).

## Conseils

- Le **feu double ses dégâts**, et ceux de ses vrilles : renversez une lanterne-citrouille au milieu d'une vague.
- Surveillez le sol qui bouillonne : une vrille en sort une seconde plus tard.
- Les vrilles d'abord : la citrouille est intouchable tant qu'il en reste une.
- Combattez-la à distance, au-delà de 6,5 blocs : seul le crachat vous atteint, et il se voit partir.
- Si vous vous éloignez à plus de 20 blocs, elle se soigne entièrement.
