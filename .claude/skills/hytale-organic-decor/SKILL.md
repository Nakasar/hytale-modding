---
name: hytale-organic-decor
description: Concevoir et générer des décors Hytale organiques, naturels et crédibles (îles, falaises, forêts, villages, ruines, arènes, donjons, chemins, prefabs et worldgen) au lieu de plateformes rectangulaires et de couloirs droits sans âme. À utiliser dès qu'une tâche crée ou modifie un prefab, une instance, une fractale, un fragment, un donjon, une arène ou un générateur de décor, ou quand Kevin trouve un lieu "moche", "vide", "trop carré", "pas naturel", même si la demande parle surtout de gameplay ("ajoute une salle pour le boss", "fais un chemin jusqu'à…").
---

# Décors organiques et crédibles

Kevin l'a dit plusieurs fois après des tests en jeu : une Falaise faite de plates-formes droites était
« terriblement moche », il « n'aime pas les plates-formes droites », il veut une nature « digne de Hytale ».
Un décor de Hytale vanilla se lit comme un lieu qui existe : le terrain a été érodé, la végétation pousse là où
c'est logique, les bâtiments ont vieilli, le chemin contourne les obstacles. Un générateur qui pose des boîtes
alignées produit l'inverse : des couloirs de test. Le gameplay (sauts, arènes, lignes de vue) doit être
**habillé** par le décor, pas montré nu.

## Le processus

1. **Raconter le lieu en deux phrases** avant tout code : qu'est-ce que c'est, qu'est-ce qui s'y est passé,
   d'où vient le vent / l'eau / la lumière. (« Un camp de grawls adossé au flanc du volcan ; la lave a coulé
   vers le sud et brûlé la forêt. ») Chaque choix de forme et de matière en découle.
2. **Poser le gameplay en squelette** : points de passage, arènes et leurs rayons, sauts, zones interdites
   (pièges, portes, leviers, marqueurs). C'est un graphe, pas encore une géométrie.
3. **Donner une forme naturelle au squelette** avec les techniques de
   [references/techniques.md](references/techniques.md) : contours par champs de distance déformés par le
   bruit, chemins en courbes de largeur variable, relief, transitions de matières, érosion des bords.
4. **Habiller** : végétation par thème, rochers, débris, détails de récit (traces de feu, objets abandonnés),
   lumière et ciel. Respecter les zones interdites du squelette.
5. **Rendre l'aperçu et l'auditer**, puis corriger avant de montrer (voir plus bas).

## Règles qui comptent

- **Pas de ligne droite longue.** Un contour, un mur, un chemin qui reste droit plus de ~8 blocs doit avoir
  une raison (rempart, mur de château, quai). Sinon : courbe, renflement, encoche, rocher qui déborde.
- **Pas de plateau plat rectangulaire.** Le sol varie d'1-2 blocs avec un bruit lent, les bords descendent en
  pente ou en falaise irrégulière, les dessous d'îles pendent (stalactites de terre, racines).
- **Les chemins sont ronds** : coins arrondis, largeur qui respire, bulles de bruit ; gardés à ≥ 3 blocs de tout
  autre élément et ≥ 6 des barrières (`curve_walkways` de la Falaise). Un éperon rocheux naturel
  (`buttress_rock`) plutôt qu'un pilier carré.
- **Matières en transition** : herbe → terre → gravier → roche selon la pente, l'altitude et l'usure (chemins
  plus usés au centre). Jamais une seule matière à > 60 % de la surface vue de dessus, jamais de damier
  (utiliser des taches de bruit lisse, `fractal_common.pick`).
- **Végétation logique** : arbres en bosquets de tailles variées, buissons et fleurs en lisière, rien sur un
  piège, une ligne de mur, une faille ou un point de passage ; plantes posées sur un sol qui les porte (pas de
  corail hors de l'eau, pas de touffe en l'air). Arbres au style vanilla (prefabs `Trees/…` ou
  `fractal_nature.broadleaf/conifer`), tronc plein, aucun bloc flottant (`floating_blocks()` vide).
- **Ne jamais aider à tricher** : aucun sol, îlot ou décor ne doit créer un raccourci entre deux sauts ou
  contourner une barrière (les îlots gardent une marge à tout bloc existant ; une bordure laisse des trous
  vers les sauts ; si le décor du bord permet de passer, faire un vrai rempart sur toute la largeur).
- **Échelle et passage** : portes et couloirs ≥ hauteur de la hitbox du plus grand mob qui y passe ; rien de
  cassable (`Material Empty`, marqueurs, notes) dans le battant d'une porte.
- **Lieux mémorables** : un repère visible de loin par zone (arbre géant, flèche de cristal, ruine), des vues
  dégagées sur le panorama aux points d'arrivée, une variation de hauteur entre les zones.
- **Ciel et lumière** font la moitié de l'ambiance : météo figée par fractale (`fractal_common.weather`),
  teintes du biome qui gardent l'herbe verte (pas de vert violacé), lumières chaudes près des lieux habités.
- **Déterminisme** : tout le décor vient du générateur avec des graines fixes ; un prefab régénéré est
  identique (sinon les diffs sont illisibles et les positions Java dérivent).

## Réutiliser

Avant d'écrire une fonction de décor, chercher dans `mods/nakasar-fractals/tools/fractal_nature.py` (bruit,
arbres, buissons, rochers, fleurs, `rim`, `natural_ground`, `dress`, `island`, `islet`, `scatter_islets`,
THEMES meadow/mists/volcanic/swamp/jade), `generate_cliffside.py` (`curve_walkways`, `buttress_rock`),
`mods/nakasar-vampires/tools/generate_prefabs.py` (bâtiments, toits, ruines, `floating_blocks`, `is_connected`)
et `generate_worldgen.py`. Voir aussi la skill `hytale-mod-reuse`.

## Aperçu et audit, à chaque itération

```bash
python3 .claude/skills/hytale-organic-decor/scripts/render_prefab.py \
    mods/nakasar-fractals/src/main/resources/Server/Prefabs/Nakasar/Fractals/Volcanic \
    --out /tmp/apercu-volcanique --quarters 0,2 --k 2
```

Le script assemble un prefab ou un dossier de sections, écrit des vues isométriques (`iso_q*.png`, quatre côtés
possibles) et de dessus (`top.png`), et un `audit.txt` : bords rectilignes ≥ 8 blocs, plus grands plateaux plats
et leur ressemblance à un rectangle, relief, part de la matière dominante. Ces mesures sont des signaux : un
bord droit peut être voulu, un bord droit non voulu doit disparaître. **Regarder les images** (lire les PNG),
de deux côtés au moins, et se demander : est-ce que ça ressemble à un endroit de Hytale, ou à un niveau de test ?

Ensuite seulement, copier les aperçus dans `/mnt/project-files/<sujet>/` et les joindre au message à Kevin,
avec une avant/après quand c'est une reprise. Noter dans « Points à vérifier en jeu » ce qui ne se juge qu'en
jeu (couleurs du ciel, lisibilité des pièges, plantes sur sable ou cendre, orientation des branches).

## Pièges techniques connus

- Worldgen : `wg.column()` force Y = 81 avant `distance_to` ; les positions de distance doivent être à Y = 81,
  sinon l'écart vertical s'ajoute à la distance (des îles se sont enfoncées).
- Ids de blocs : tout id inconnu = damier rose et noir en jeu ; `validateAssets` vérifie contre
  `tools/vanilla-block-ids-0.7.2.txt`. États de bloc : `*<Objet>_State_Definitions_<État>`.
- Rotations en prefab : yaw 0 regarde le sud (+Z) ; clôtures, murs et barreaux : 0 = ligne le long de X,
  1 = le long de Z ; troncs/branches couchés 4 le long de Z, 5 le long de X (supposé).
- Mobilier multi-blocs : les cellules de remplissage (`filler`) suivent la rotation ; voir mémoire
  `hytale-block-ids`.
- Fluides (lave, eau) : liste `fluids` du prefab (bloc AIR + fluide, niveau 1), pas un bloc solide.
