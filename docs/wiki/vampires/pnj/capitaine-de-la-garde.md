# Capitaine de la garde

<Infobox pending title="Capitaine de la garde" kind="Élite">
<Info label="Points de vie">**950**</Info>
<Info label="Barre de vie">barre de boss en combat</Info>
<Info label="Attitude">Hostile</Info>
<Info label="Lieu">[Poste de garde de la garnison](../fragment/postes-de-garde.md), 1 marqueur</Info>
<Info label="Réapparition">30 min</Info>
<Info label="Faiblesses">Feu purificateur</Info>
<Info label="Butin">[Insigne du Capitaine](../objets/trophees.md), hache rouillée (33 %)</Info>
<Info label="Id">`Nakasar_Guard_Captain`</Info>
</Infobox>

Le chef de la garnison du Comte : grand squelette d'élite (×1,3) en armure de prétorien, cape rouge, hache de bataille rouillée. Il commande le [poste de garde de la garnison](../fragment/postes-de-garde.md) et **jette les intrus dans ses cellules**.

## Fiche

| | |
|---|---|
| Points de vie | **950** (le plus robuste du mod), affichés dans une **barre de vie de boss** pendant le combat |
| Vitesse | 4,6 |
| Recul subi | ×0,3 |
| Arme | Hache de bataille en acier rouillée |
| Détection | 16 blocs (ligne de vue) |
| Abandon | plus de cible à 32 blocs : rentre et **récupère tous ses PV** |
| Groupes | Morts-vivants du domaine (feu purificateur) |

## Attaques

| Attaque | Portée | Effet | Fréquence |
|---|---|---|---|
| **Emprisonnement** (annoncé, **imparable**) | cible entre 4 et 16 blocs, en vue | vous **téléporte dans la cellule de prison la plus proche** de lui (dans un rayon de 24 blocs), où que vous soyez + [Emprisonné](../effets.md#emprisonne) **5 s** (vitesse ×0,6) | toutes les 45 à 60 s (première après 14 à 18 s) |
| **Tourbillon** (annoncé) | cercle rouge de **4 blocs** autour de lui, **1,5 s** | **32** dégâts physiques (±10 %), projection ; puis il reste **sonné 2 s** ([Vertige](../effets.md#vertige)) | toutes les 14 à 18 s, si vous êtes collé à lui |
| **Fendant** (annoncé) | cône rouge de **50°** et **5 blocs** devant lui, **1,3 s** | **45** dégâts physiques (±10 %), projection | toutes les 9 à 12 s |
| **Coups de hache** | 3,4 blocs, 100° | **22** dégâts physiques (±10 %), gauche puis droite | pause de 1 à 1,5 s |
| **Alarme** (sous 50 % de vie) | cloche d'alarme à 40 blocs au plus | il crie **2 s**, puis la cloche sonne et **3 [gardes squelettes](garde-squelette.md) par joueur** présent à 24 blocs accourent (12 au plus), reliés à lui par un fil rouge | **une fois** par combat, seulement si la cloche est encore debout |

**Comment lire ses attaques :** les zones rouges sont celles de la [Tour de l'Alchimiste](../donjons/tour-de-l-alchimiste.md) : elles ont la taille exacte du coup et se remplissent pendant toute la préparation. Le coup frappe ce qui est encore dedans quand elles sont pleines. Pendant la préparation il est insensible au recul.

**L'emprisonnement ne s'esquive pas :** des **chaînes rouges** apparaissent au-dessus de la tête de sa cible pendant **1,5 s**, puis elle est envoyée en cellule. Préparez-vous à en sortir.

### Sortir d'une cellule

- La **porte** de la cellule tombe au bout de **10 coups** ; elle revient au bout de **45 s**. Le reste de la cellule (murs, barreaux, sol, plafond) est indestructible.
- Un **levier**, dehors au pied du mur à côté de chaque porte, ouvre la porte **6 s** (clic ou coup) : un allié peut vous libérer.

### La cloche d'alarme

Une cloche se dresse dans la cour du poste. Elle sonne à chaque coup et **tombe au bout de 5 coups** (elle revient au bout de 3 minutes). Abattue avant que le Capitaine ne passe sous la moitié de sa vie, **personne ne répond à son alarme**.

## Butin

| Objet | Quantité | Chance |
|---|---|---|
| [Insigne du Capitaine](../objets/trophees.md) | 1 | 100 % |
| Hache de bataille en acier rouillée | 1 | 33 % |
| Butin habituel du chevalier squelette (`Drop_Skeleton_Knight`) | | |

## Où le trouver

[Poste de garde de la garnison](../fragment/postes-de-garde.md) : **1** marqueur, avec 6 [gardes squelettes](garde-squelette.md), 4 cellules de prison (porte et levier) et la cloche d'alarme. Réapparition : **30 minutes**.

Aussi la cible du [contrat « la Garnison du Capitaine »](../objets/contrats.md).

## Conseils

- **Abattez la cloche d'alarme** avant d'attaquer le Capitaine : sinon, sous la moitié de sa vie, trois gardes par joueur rejoignent le combat.
- Un joueur emprisonné atterrit dans une cellule du poste : frappez la porte (10 coups) ou comptez sur un allié resté dehors pour tirer le levier.
- Restez à moins de 4 blocs pour qu'il n'utilise pas l'emprisonnement, mais sortez du cercle quand il prépare son tourbillon, puis **frappez-le pendant ses 2 s de vertige**.
- Le fendant ne couvre qu'un cône étroit de 50° : un pas de côté suffit.
