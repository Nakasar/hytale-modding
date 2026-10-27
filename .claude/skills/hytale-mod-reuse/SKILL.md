---
name: hytale-mod-reuse
description: Retrouver et réutiliser ce que les mods Nakasar (Vampires, Fractales) ont déjà écrit avant d'écrire du nouveau code Java ou un nouveau générateur Python — attaques annoncées, barres de boss, vie par groupe, serviteurs, cages, objets ramassés accroupi, décor naturel, moteurs de modèles 3D, rôles de PNJ, prefabs. À utiliser dès qu'une tâche ajoute une mécanique, un boss, un mob, un objet, un bloc ou un décor dans ce dépôt, même si la demande ne parle pas de réutilisation ("ajoute un boss qui…", "fais une nouvelle fractale", "il faudrait que le joueur porte…").
---

# Réutiliser le code des mods

Les deux mods du dépôt (`mods/nakasar-vampires`, `mods/nakasar-fractals`) ont déjà résolu beaucoup de problèmes
difficiles de Hytale 0.7.2, souvent après un retour en jeu de Kevin. Une mécanique réécrite de zéro perd ces
corrections et redécouvre les mêmes bugs (un objet porté perdu à cause de la durabilité, un bouclier resté
invulnérable après un rechargement, une annonce rouge à la mauvaise taille…). Le réflexe : **chercher, lire,
copier-adapter, puis seulement écrire du neuf**.

## 1. Chercher ce qui existe

Lancer l'index vivant (il lit le dépôt tel qu'il est, il ne vieillit pas) :

```bash
python3 .claude/skills/hytale-mod-reuse/scripts/index_code.py --grep télégraphe     # ou boss, ramass, cage, shield, prefab…
python3 .claude/skills/hytale-mod-reuse/scripts/index_code.py --mod fractals --out /tmp/index.md   # tout un mod
```

Il donne chaque classe Java avec sa Javadoc (en français, très descriptive), les types d'interaction
`"Type": "Nakasar_…"` utilisables depuis le JSON, les générateurs Python avec leurs fonctions, et la liste des
classes copiées entre les deux mods. Chercher avec plusieurs mots (français et termes Hytale : « annonce »,
« Telegraph », « zone rouge »), car le vocabulaire varie.

Pour s'orienter par besoin, lire [references/catalogue.md](references/catalogue.md) : il range les briques par
problème (« un boss doit être invulnérable tant que… », « un joueur doit porter un objet… », « un décor doit
avoir l'air naturel… ») et dit laquelle est la plus récente quand il en existe deux versions.

Penser aussi aux sources hors code :
- la mémoire du projet (`hytale-*`, `fractals-*`, `alchemist-*`) garde le pourquoi des choix et les pièges ;
- `docs/api-0.7.2.md`, `docs/npc-0.7.2.md`, `docs/npc-reference-0.7.2.md` (toutes les briques de rôles PNJ) ;
- `git log -S'NomDeClasse'` retrouve la PR qui a introduit ou corrigé une brique, et donc son retour en jeu.

## 2. Lire avant de copier

Ouvrir la classe ou la fonction trouvée et lire sa Javadoc en entier : elle dit les cas limites déjà réglés
(sauvegarde, déchargement de chunk, plusieurs joueurs, ordre des systèmes de dégâts). Vérifier :
- **Quelle version est la bonne.** Quand une brique existe dans les deux mods, la copie des Fractales est en
  général la plus récente (elle reprend celle des Vampires et l'améliore) ; comparer avec `diff` avant de choisir.
- **Ce qui est spécifique.** Les constantes de rencontre (rayons, PV, délais) et les ids (`Nakasar_Fractal_…`
  contre `Nakasar_…`) ne se recopient pas tels quels.
- **Les fichiers générés.** `*Layout.java` et beaucoup d'assets JSON sont écrits par un générateur (« ne pas
  modifier à la main : relancer le générateur ») : on change le générateur, puis on le relance.

## 3. Réutiliser selon la règle du dépôt

Il n'y a **pas de bibliothèque partagée** entre les mods (décision de Kevin, 20 octobre 2026) : chaque mod reste
un jar autonome. Donc :
- **Dans le même mod** : appeler la brique existante, l'étendre (paramètre, surcharge) plutôt que la dupliquer.
  Une deuxième classe qui fait presque la même chose est à éviter ; généraliser la première (comme
  `arena/CrouchPickup.register(Item)` sert au cristal et à la pierre imprégnée).
- **D'un mod à l'autre** : copier le fichier dans le paquet de l'autre mod, renommer les ids, et l'écrire dans
  la Javadoc ou la docstring : « Copie de `X` du mod Vampires ». L'index liste ces copies ; quand on corrige un
  bug dans l'une, corriger l'autre dans la même PR (ou dire clairement pourquoi non).
- **Python** : les générateurs importent les modules communs de leur mod (`fractal_common`, `fractal_nature`,
  `fractal_blocks`, `fractal_models`, `fractal_anim`, `fractal_roles` côté Fractales ; `generate_prefabs`,
  `generate_worldgen`, `tower_warnings`, `tower_fx` côté Vampires). Ajouter une fonction réutilisable au module
  commun plutôt que dans un générateur de niveau.

## 4. Quand rien n'existe

Avant d'écrire du neuf, regarder si vanilla le fait déjà (skill `hytale-vanilla-research`). Puis écrire la
nouvelle brique **réutilisable dès le départ** : nom générique, paramètres plutôt que constantes de rencontre,
Javadoc en français qui dit quoi, pourquoi (avec la date et la demande de Kevin si c'en est une), et les cas
limites. C'est cette Javadoc qui permettra au prochain fil de la retrouver avec l'index.

## Ce qu'on rend

Dans la réponse ou la PR, dire en une ligne ce qui a été réutilisé (« attaque annoncée via
`combat/TelegraphInteraction`, barre via `BossBarSystem.everywhere` ») et ce qui est neuf. Si une copie entre
mods a été corrigée d'un seul côté, le dire.
