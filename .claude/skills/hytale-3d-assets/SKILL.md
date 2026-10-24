---
name: hytale-3d-assets
description: Modéliser et texturer des assets 3D Hytale (.blockymodel, .blockyanim, atlas PNG, icônes) qui ont l'air vanilla — blocs en modèle, objets tenus, armes, cosmétiques, PNJ animés ou humanoïdes. À utiliser dès qu'une tâche crée ou retouche un modèle, une texture, une animation, une icône ou l'apparence d'un mob/boss, ou quand Kevin trouve un visuel "moche", "pas Hytale", "trop plat", "trop gros", même si la demande dit seulement "fais-lui une tête de…" ou "il faudrait un vrai modèle pour…".
---

# Modèles 3D et textures au style Hytale

Hytale vanilla a un style très reconnaissable : silhouettes trapues et lisibles faites de quelques boîtes,
petites textures peintes à la main avec un dégradé de lumière et des arêtes éclaircies, couleurs franches mais
pas saturées, densité de pixels constante. Un asset qui s'en écarte (cubes unis, texture bruitée façon photo,
centaines de micro-boîtes, pixels étirés) saute aux yeux en jeu, et Kevin le renvoie. Le but n'est pas
d'inventer un style mais de **se fondre dans celui du jeu**.

## Avant de modéliser

1. **Trouver le modèle vanilla le plus proche** (skill `hytale-vanilla-research`) : coffre, torche, établi,
   arme de la même famille, mob de taille voisine. En lire les dimensions, le nombre de boîtes, la taille de
   l'atlas, les noms de nœuds (les animations vanilla visent des noms : `Lid` du coffre…). Si on peut, regarder
   sa texture PNG (extraite d'Assets.zip) : c'est la meilleure référence de palette et d'ombrage.
2. **Choisir le bon moteur du dépôt** plutôt qu'écrire un exporteur (skill `hytale-mod-reuse`) :

   | Asset | Moteur | Unités |
   |---|---|---|
   | Bloc en modèle (DrawType Model), avec états/animation/particules | `mods/nakasar-fractals/tools/fractal_blocks.py` (+ `generate_block_models.py`) | 32 / bloc |
   | Objet tenu en main, arme, outil (format prop) | `fractal_models.py` + `generate_item_models.py` | 32 / bloc |
   | PNJ animé à squelette propre (citrouille, vrilles, Codex, Chimère) | `fractal_anim.py` (copie de V `generate_pumpkin_models.py`) | 64 / bloc |
   | Humanoïde (rig Player) + vêtements/attachements | modèle `Parent: Player` + `DefaultAttachments`, V `generate_vampire_models.py` | 64 / bloc |
   | Cosmétique porté | `generate_cosmetics.py` (deux mods), `preview_on_body` | 64 / bloc |

   Les règles de format (repères, pivots, enveloppe prop, faces, attachements) sont dans
   [references/formats.md](references/formats.md). Les lire avant de toucher un moteur ou d'écrire un format
   nouveau.

## Règles de style

Le détail et les recettes de peinture sont dans [references/style.md](references/style.md). L'essentiel :

- **Silhouette d'abord.** Lisible à 10 blocs de distance, de face et de profil. Peu de boîtes, bien placées ;
  les détails fins se peignent dans la texture, ils ne se modélisent pas. Proportions un peu exagérées (têtes,
  mains, pièces clés plus grosses) comme les PNJ vanilla.
- **1 texel par unité, partout.** Ne jamais étirer une texture sur une boîte plus grande : la densité de pixels
  est ce qui rend un modèle « Hytale ». Les moteurs du dépôt le garantissent si on passe par eux.
- **Texture peinte, pas bruitée.** 3 à 5 tons par matière : base, ombre en bas, lumière en haut, arêtes
  éclaircies (`rim`), quelques motifs (veinage du bois, joints de pierre, rivets). Bruit doux et faible, jamais de
  bruit blanc. Pas de noir pur ni de blanc pur sauf lumière.
- **Palettes cohérentes avec le biome et le mod** : bois sombre et or pour le noble, métal froid et rivets pour
  le garde, cristaux en dégradés cyan-rose, brume en violets. Les parties lumineuses en `glow`/fullbright, peu
  nombreuses.
- **Échelle juste** : un joueur fait ~1,85 bloc (102 unités sur le rig Player). Comparer chaque modèle à
  cette taille et aux blocs voisins ; un boss se lit par sa taille, un objet de décor ne doit pas écraser la
  pièce. Vérifier aussi la hitbox (une Abomination trop grande est restée coincée derrière une porte).

## Produire et vérifier

1. Écrire ou étendre le générateur (le modèle est du code, régénérable), jamais de JSON de modèle édité à la
   main.
2. **Rendre un aperçu** avec le moteur (`--preview DOSSIER` sur les générateurs, `render(...)` des moteurs) :
   au moins trois-quarts face, profil et dos, plus une vue à côté d'une silhouette de joueur pour l'échelle.
   Pour un PNJ animé, une planche de poses clés de chaque animation.
3. **Regarder l'aperçu soi-même** (lire le PNG) et le critiquer avant de le montrer : boîte flottante ou
   décollée, face manquante (tête vue de face transparente !), pixels étirés, couleurs hors palette,
   silhouette illisible, pivot d'animation au mauvais endroit.
4. Déposer les aperçus dans `/mnt/project-files/<sujet>/` et les joindre au message pour Kevin : il juge le
   style sur image, avant d'aller en jeu.
5. Lancer `./gradlew check` (les validateurs décodent modèles, particules et effets) et noter dans « Points à
   vérifier en jeu » du README ce qui ne se voit qu'en jeu : sens des rotations, transparence/alpha, orientation
   `FRONTS`, animations jouées, particules.

## Ce qu'on rend

Le générateur (et les assets qu'il écrit), la planche d'aperçu jointe, et une phrase sur l'analogue vanilla
suivi et ce qui reste à vérifier en jeu.
