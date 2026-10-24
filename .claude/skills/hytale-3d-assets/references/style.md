# Style visuel Hytale : recettes

## Lire un modèle vanilla comme référence

Pour une famille d'asset nouvelle, extraire d'Assets.zip (skill `hytale-vanilla-research`, commande `extract`)
le `.blockymodel` et sa texture du plus proche analogue, puis noter :
- nombre de boîtes et taille de la plus petite (sous 2 unités, c'est presque toujours de la peinture) ;
- taille de l'atlas et nombre de tons par matière (compter les couleurs distinctes d'une face) ;
- où sont les lumières et les ombres peintes (haut clair, bas sombre, arêtes éclaircies) ;
- les couleurs dominantes, à reprendre comme base de palette.

## Peinture des textures (ce que font les peintres des moteurs)

Les peintres de `fractal_blocks.py` (`planks`, `stone`, `smooth_stone`, `metal`, `crystal`, `log`, `ground`,
`glass`, `cloth`, `paper`, `jade`, `mist`) et `fractal_anim.py` (`p_round`, `p_glow`, `p_plate`) suivent ces
recettes ; s'en servir et en ajouter plutôt que de peindre à la main dans un générateur :

- **Dégradé vertical** : la face du haut la plus claire, les côtés un peu plus sombres vers le bas, le dessous
  à ~70 % (`solid(color, f_bottom=0.7)`).
- **Arêtes éclaircies** : un liseré d'1 texel plus clair sur le pourtour des faces visibles (`rim=True`) : c'est
  lui qui donne l'aspect « jouet peint » de Hytale.
- **Motif de matière** à grande échelle : planches de 5 texels avec veinage, briques 8×5 avec joints, rivets
  sur le métal. Le motif suit la face, il ne traverse pas les arêtes au hasard.
- **Bruit doux** : amplitude ~0,10, échelle 4-8 texels. Jamais de bruit pixel par pixel fort (effet sable).
- **Palette serrée** : 3 à 5 tons par matière, dérivés d'une base par `shade`/`mix`. Deux matières voisines
  doivent contraster en valeur, pas seulement en teinte.
- **Lumineux** : dégradé chaud→clair (`p_glow`), en fullbright, sur peu de surface (yeux, flammes, runes).
- **Transparence** : un texel transparent est découpé en jeu ; les plaques de lueur à alpha partiel sont à
  vérifier en jeu.

## Silhouette et proportions

- Construire par masses : 3 à 8 boîtes principales, puis quelques boîtes d'accent (couronne, col, lame).
- Biseauter une forme ronde par boîtes en escalier (citrouille lobée, vrilles octogonales) plutôt qu'avec des
  rotations à 45° partout.
- Décaler, incliner légèrement, varier les tailles : une rangée de boîtes identiques alignées fait « placeholder ».
- PNJ : têtes et mains un peu grandes, pieds bien posés au sol (origine au sol), pas de membre qui traverse le
  corps dans les poses d'animation.

## Goûts déjà exprimés par Kevin

- Nobles (Comte, Comtesse) : allure noble et dominante, pas de coiffure enfantine (couettes refusées) ; couronne,
  cape royale, manteau à liseré d'or.
- Arbres et nature : ressembler au vanilla, troncs pleins, pas de morceaux flottants.
- Lisibilité des combats avant l'effet spectaculaire : rien d'aveuglant.
- Un visuel jugé « moche » se refait à fond (passe complète), il ne se retouche pas à la marge.
