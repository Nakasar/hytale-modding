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
| **Invocation des vrilles** | 3 à 7 blocs autour d'elle | une vague de **5** [vrilles de citrouille](vrille-de-citrouille.md) | dès le début du combat (ou au premier coup reçu), puis **10 à 12 s après la destruction** de la vague précédente |
| **Piège de vrilles** (annoncé) | cercle de **6,5 blocs** | chaque ennemi touché est saisi par des [vrilles](vrilles.md) : **immobilisé** tant qu'elles ne sont pas détruites (10 s au plus) | toutes les 14 à 18 s (premier après 8 à 10 s), si vous êtes à 6 blocs ou moins |
| **Crachat de poison** | 16 blocs (ligne de vue) | **8** dégâts de poison à l'impact + [Poison de citrouille](../effets.md#poison-de-citrouille) **4 dégâts/s pendant 6 s** | toutes les 7 à 9 s |

**Invulnérable tant que ses vrilles vivent :** tant qu'il reste une vrille de la vague, la citrouille ne subit **aucun dégât** (un message vous le rappelle). Détruisez d'abord toutes les vrilles, puis frappez-la pendant les 10 à 12 s de répit avant la vague suivante.

**Le piège se voit venir :** une zone rouge de 6,5 blocs apparaît au sol pendant **2,2 s**. Sortez-en. Si vous êtes pris, frappez les vrilles à vos pieds (12 PV) pour vous libérer.

## Butin

| Objet | Quantité | Chance |
|---|---|---|
| Citrouille | 3 à 6 | 100 % |
| Graines de citrouille | 2 à 4 | 100 % |
| Essence de vie de citrouille | 1 à 2 | 100 % |
| [Graine de la Citrouille géante](../objets/trophees.md) | 1 | 100 % |

## Où la trouver

Au centre de la clairière d'un [champ de citrouilles géant](../fragment/champs-de-citrouilles.md) (rayon 7). Un champ de citrouilles sur deux est de ce type. Réapparition : **30 minutes**.

Aussi la cible du [contrat « le Champ maudit »](../objets/contrats.md).

## Conseils

- Le **feu double ses dégâts**, et ceux de ses vrilles.
- Les vrilles d'abord : la citrouille est intouchable tant qu'il en reste une.
- Combattez-la à distance, au-delà de 6,5 blocs : seul le crachat vous atteint, et il se voit partir.
- Si vous vous éloignez à plus de 20 blocs, elle se soigne entièrement.
