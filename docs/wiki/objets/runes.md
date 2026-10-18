# Runes de capacité

Quatre runes de sorts, que l'on lance avec les **touches de capacité** en tenant une arme. Elles coûtent du **mana** et ont un temps de recharge. Elles reprennent pour l'instant l'icône et l'apparence de la rune de boule de feu du jeu.

## Obtenir une rune

| Source | Détail |
|---|---|
| **[Autel sacrificiel](autel-sacrificiel.md)**, onglet Runes | **2 éclats de rune** → 1 rune, **1 s**. Les quatre recettes sont connues d'office. |
| **[Comte](../pnj/comte-vampire.md) ou [Comtesse](../pnj/comtesse-vampire.md) Vampire** | une rune au hasard parmi les quatre à chaque victoire (25 % chacune) |

**Éclats de rune :** Comte et Comtesse (4 à 6), Capitaine de la garde (2 à 4), Citrouille géante et Abomination zombie (1 à 3), rejetons (25 %), fantômes (20 %), et les coffres des cryptes, des châteaux hantés et du manoir (alchimie, bibliothèque).

## Récapitulatif

| Rune | Rareté | Mana | Recharge | Effet |
|---|---|---|---|---|
| [Baiser du Vampire](#baiser-du-vampire) | Rare | 30 | 4 s | coup de mêlée, 18 dégâts, +12 PV |
| [Domination](#domination) | Épique | 45 | 12 s | une créature change de camp 6 s |
| [Téléportation](#teleportation) | Rare | 35 | 8 s | projectile qui vous téléporte (20 blocs max) |
| [Chaînes spectrales](#chaines-spectrales) | Épique | 40 | 10 s | immobilise la cible 3 s |

## Baiser du Vampire

> Un coup de mêlée qui draine le sang de la cible : vous récupérez 12 points de vie par cible touchée.

- **Coût :** 30 mana · **Recharge :** 4 s
- Balayage vers la droite, portée **2,8 blocs**, ligne de vue requise.
- **18 dégâts physiques** (±10 %) par cible.
- **Soin :** +12 PV pour la première cible, puis 6, 3, et 1,2 par cible supplémentaire.
- Un filet de sang file de la cible vers vous (visuel).
- Le bonus d'argent ne s'applique pas aux sorts.

## Domination

> Soumet la créature que vous regardez (8 blocs) : elle devient alliée pendant quelques secondes. Sans cible, rien n'est dépensé.

- **Coût :** 45 mana · **Recharge :** 12 s · **Durée :** 6 s
- Vise la créature la plus proche dans votre ligne de mire, à **8 blocs** au plus, sans mur entre vous. Ne fonctionne pas sur les joueurs.
- **Sans cible valide, ni mana ni recharge ne sont dépensés.**
- Pendant 6 s, la créature :
  - devient **amicale** envers vous et oublie qu'elle vous combattait ;
  - **change de camp** : elle attaque ses anciens alliés, et eux l'attaquent (leurs coups portent de nouveau) ;
  - ne peut pas vous blesser ;
  - est teintée de rose et de violet ([Dominé](../effets.md#domine)).
- À la fin, elle oublie les cibles prises parmi ses anciens alliés et retourne dans son camp.
- Aucune créature n'est exclue dans le code : boss et élites peuvent être dominés.

## Téléportation

> Lance un projectile et vous téléporte à son point d'impact, à 20 blocs au plus.

- **Coût :** 35 mana · **Recharge :** 8 s
- Le projectile vole **1,5 s** au plus. À l'impact (créature ou terrain), ou en fin de course, vous êtes téléporté à son point d'arrivée, un peu en retrait pour ne pas finir dans un mur, en gardant votre orientation.
- **Distance maximale : 20 blocs** (un impact plus lointain vous arrête à 20 blocs sur la même ligne).
- Petite explosion violette à l'arrivée. Le sort n'inflige pas de dégâts.

## Chaînes spectrales

> Un projectile qui fait jaillir des chaînes spectrales du sol et immobilise la cible touchée quelques secondes.

- **Coût :** 40 mana · **Recharge :** 10 s · **Durée :** 3 s
- Projectile à traînée verte (vol de 2 s au plus).
- La cible touchée est **immobilisée 3 s** : [Chaînes spectrales](../effets.md#chaines-spectrales) (un joueur ne peut plus bouger, attaquer, lancer de sort ni esquiver ; une créature est figée).
- Sans cible touchée, le sort ne fait rien.
