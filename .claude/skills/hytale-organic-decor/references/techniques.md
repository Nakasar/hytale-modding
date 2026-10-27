# Techniques de formes organiques (Python, générateurs du dépôt)

Toutes ces recettes sont déterministes : le bruit vient de `fractal_nature.hash01/vnoise2/fbm2/vnoise3` avec une
graine fixe. Les exemples supposent `import fractal_nature as fn` et un objet prefab `p` (`p.set(x, y, z, nom)`
ou l'équivalent du générateur).

## 1. Contours : champ de distance + bruit

Une île, une clairière, une arène ou une salle se décrit par une fonction « intérieur » plutôt que par un
rectangle. Union de lobes (disques) dont le rayon est déformé par un bruit angulaire et un bruit de position :

```python
def inside(x, z, lobes, seed):
    """Vrai si (x, z) est dans l'union des lobes déformés. lobes = [(cx, cz, r), …]"""
    warp_x = 6 * (fn.fbm2(x, z, 40, seed=seed) - 0.5)        # domaine déformé : bords qui ondulent
    warp_z = 6 * (fn.fbm2(x, z, 40, seed=seed + 1) - 0.5)
    for cx, cz, r in lobes:
        d = math.hypot(x + warp_x - cx, z + warp_z - cz)
        if d < r * (0.85 + 0.3 * fn.fbm2(x, z, 18, seed=seed + 2)):
            return True
    return False
```

- 3 à 7 lobes de rayons différents donnent une forme crédible (les îles de contrats sont faites ainsi).
- Un « cou » entre deux lobes doit rester marchable : vérifier une largeur minimale le long du chemin.
- `fn.rim(footprint, rmin, rmax, seed, block=…)` ajoute une bordure naturelle autour d'une emprise existante,
  en laissant des trous (`block`) vers les sauts.

## 2. Relief

- Hauteur du sol = base + `amp * fbm2(x, z, échelle ≥ 24)` : amplitude 1-3 blocs sur un lieu marchable, plus
  sur les flancs. Arrondir à l'entier, puis lisser les marches isolées de 1 bloc si le passage doit rester fluide.
- Bord d'île : la hauteur descend avec la distance au bord (`fn.edge_distance(tops)`), avec un bruit pour que la
  falaise soit irrégulière ; dessous en cône bruité qui pend (`fn.island`, `hang`).
- Falaises : stries horizontales (couches de roche de matières alternées) + surplombs aléatoires + éboulis au
  pied.

## 3. Chemins

- Tracer une polyligne de points de passage, l'arrondir (Chaikin 2-3 fois ou spline de Catmull-Rom), puis
  balayer un disque dont le rayon varie lentement (`w0 + 1.5 * fbm2(t…)`) : coins ronds, largeur qui respire.
- Usure : centre en terre battue/gravier, bords en herbe, transition par bruit.
- Un chemin contourne les obstacles naturels (rocher, arbre) plutôt que de les traverser : les placer d'abord,
  puis faire passer le chemin entre.
- Plates-formes suspendues / passerelles : voir `generate_cliffside.curve_walkways` (coins arrondis, bulles de
  bruit, distances minimales aux autres éléments, seulement des passerelles reliées).

## 4. Matières

- Choisir la matière par règles physiques : pente forte → roche ; replat → herbe ; sous un arbre → terre et
  feuilles mortes ; près de l'eau → sable/argile ; zone brûlée → cendre et herbe brûlée, intensité décroissante
  depuis la source.
- Mélanger deux matières par taches de bruit lisse (seuil sur `fbm2` à échelle 6-12), jamais `hash01` pur (damier).
- Murs de bâtiments : 2-3 variantes de la même pierre (propre, fissurée, moussue), plus de mousse en bas et
  côté nord, plus d'usure aux angles.

## 5. Dispersion (arbres, rochers, fleurs, débris)

- Espacement minimal (échantillonnage de type Poisson : refuser un point trop près d'un autre) + densité
  modulée par un bruit lent : des bosquets et des clairières, pas une grille.
- Tailles variées dans un groupe (un grand, deux moyens, des petits), groupes en nombre impair.
- Lisières : buissons et fleurs plus denses à la frontière forêt/clairière et au pied des rochers.
- `fn.dress(p, cells, theme, …)` fait déjà tout cela par thème ; lui passer seulement les cellules autorisées
  (sans pièges, murs, failles, passages).

## 6. Ruines et vieillissement

- Partir du bâtiment intact (générateur de bâtiment), puis l'abîmer (`Prefab.ruin(chance, keep_below)` de
  `generate_prefabs.py` le fait déjà) : retirer des blocs selon un bruit plus fort
  en haut qu'en bas, faire tomber les blocs retirés en éboulis au pied, laisser des poutres qui dépassent.
- Supprimer ensuite tout bloc flottant (`floating_blocks`) et vérifier la connexité (`is_connected`).
- Végétation qui reprend : lierre et mousse sur les faces nord, herbes dans les fissures du sol.

## 7. Composition

- Un repère visible de loin par zone, et des vues cadrées : à l'arrivée dans une zone, le joueur doit voir où il
  va (le repère suivant) avant de voir comment y aller.
- Alterner espaces resserrés et ouverts, bas et hauts.
- Îlots et décor du ciel en arrière-plan (`fn.scatter_islets`, avec marge) pour la profondeur, jamais à portée
  de saut du parcours.
