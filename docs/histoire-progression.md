# Comté Vampire — Histoire et progression

Document de design, 18 octobre 2026 (Kevin). Version éditable : [Claude Doc](https://claude.ai/code/artifact/77b470d3-a744-4674-8a7e-5f2ac6fdddcd).

## Vision et principes

Le joueur vit sa vie normale dans Hytale, puis la nuit le Comté Vampire vient à lui par une brèche. Il progresse ensuite librement entre deux voies qui se cumulent : celle des chasseurs et celle de l'occultisme.

- **Histoire implicite.** Aucun dialogue de PNJ. Le récit passe par l'environnement, les objets, les déblocages, et des notes ou textes courts, dans l'esprit des gobelins du Chapitre 1 de Hytale.
- **Deux voies non exclusives.** Un joueur peut être chasseur et vampire à la fois. Les chasseurs traitent un vampire comme n'importe quel joueur.
- **Progression portée par les objets.** Trophées, clés, runes et potions sont dans l'inventaire : pas d'état de monde global débloqué par un seul joueur.
- **Pleinement jouable en multijoueur**, sur serveur comme en solo.
- **Le Comte et la Comtesse sont l'horizon.** Intouchables au départ, ils sont vaincus à terme dans un donjon épique.

## Le fil de l'histoire

Le parcours type va de la première brèche au donjon du Comte, en passant par les deux voies au rythme que le joueur choisit.

1. **La brèche.** Après une attente dans le monde par défaut, une nuit, une faille rouge s'ouvre et un camp de chasseurs s'installe autour. C'est l'événement de brèche déjà en place.
2. **L'appel.** Dans le camp, un tableau de contrats porte une note courte, par exemple : « Nous cherchons des bras. Passez la faille. » Un premier contrat facile y est épinglé.
3. **Le Comté.** En traversant la faille, le joueur arrive dans le fragment Comté Vampire. Il y trouve les villages zombies, les fermes, les postes de garde, les champs de citrouilles et le manoir, ainsi que le camp des chasseurs avec son feu purificateur.
4. **Les premiers trophées.** Les élites (Abomination, Capitaine de la garde, Citrouille géante) donnent des trophées et des ressources occultes.
5. **Les deux voies s'ouvrent.** Les trophées font monter l'établi des chasseurs. Le sang, les cendres et les reliques nourrissent l'autel sacrificiel.
6. **Les zones suivantes.** Les contrats ouvrent des mini-fragments de primes, et les rites ouvrent des mini-fragments occultes. Plus tard viennent les donjons.
7. **Le choix de devenir vampire.** À tout moment après le palier occulte requis, le joueur peut accomplir le rituel. Il peut aussi revenir en arrière.
8. **Le donjon du Comte.** C'est la fin de partie : un donjon épique où le Comte et la Comtesse peuvent enfin être vaincus.

## Voie des chasseurs

Le joueur progresse avec les chasseurs en rapportant des trophées. Ceux-ci débloquent les paliers de leur établi, avec ses armes, ses compétences (runes de lumière) et ses clés de zones. Il n'y a pas de réputation cachée : tout passe par des objets, ce qui reste lisible et marche en multijoueur.

**Trophées proposés :** crocs de vampire (rejetons), cœur d'Abomination, insigne du Capitaine de la garde, graine de la Citrouille géante, plus tard des trophées de donjon.

| Palier | Débloqué par | Contenu |
| --- | --- | --- |
| 1. Recrue | Premier contrat de la brèche | Établi de chasseur, armes et flèches en argent, torches purificatrices |
| 2. Traqueur | Crocs de vampire + un trophée d'élite | Rune d'aura de lumière, clé du fragment Comté Vampire, premiers contrats de primes |
| 3. Chasseur | Deux autres trophées d'élite | Rune d'invisibilité, armes en argent améliorées, contrats plus durs |
| 4. Maître chasseur | Trophées de donjon | Clé du donjon du Comte, équipement de fin de partie |

Les **contrats** sont des clés fabriquées à l'établi. Chacune ouvre un mini-fragment de prime (une cible, un lieu, une récompense), et tout le groupe peut y entrer. Le découpage exact des paliers est à caler avec l'établi en cours de développement.

## Voie occulte

La voie occulte part de l'autel sacrificiel, qui existe déjà, et transforme les ressources du Comté en pouvoirs vampiriques. Elle culmine avec le rituel qui fait du joueur un vampire.

**Ressources occultes proposées :** sang (pris aux êtres vivants via le Baiser du Vampire), cendres de mort-vivant, reliques du manoir, éclats de rune.

| Palier | Contenu à l'autel |
| --- | --- |
| 1. Initié | Runes existantes : Baiser du Vampire, Domination, Téléportation, Chaînes spectrales |
| 2. Adepte | Fioles de sang, potion de protection solaire niveau 1, premières clés de mini-fragments occultes |
| 3. Rituel | Rituel de transformation en vampire, potion solaire niveau 2 |
| 4. Seigneur de la nuit | Potion solaire niveau 3, runes de sang avancées, clés de donjons occultes |

**Le rituel de transformation** se fait à l'autel, avec des ingrédients rares du manoir et du sang. Il doit marquer le joueur : un effet visuel, un son, une note qui apparaît dans l'inventaire.

**Le rituel inverse** existe aussi à l'autel. Il est coûteux (ingrédients purifiants, argent, flamme purificatrice) pour que devenir vampire reste un vrai choix, sans être définitif.

## Le joueur vampire

Après le rituel, le vampire est fort la nuit et quand il est bien nourri, mais fragile au soleil, face à l'argent et quand il a faim.

**Gains**

- Vision nocturne légère.
- Runes de sang plus fortes.

**Faim de sang.** La nourriture normale n'a plus aucun effet. Le vampire se nourrit sur des êtres vivants avec le Baiser du Vampire, ou en buvant des fioles de sang fabriquées à l'autel. On passe de rassasié à affamé en environ une journée et demie de jeu.

| État | Régénération naturelle | Autres effets |
| --- | --- | --- |
| Rassasié | Comme une nourriture de rang 4 | Aucun |
| Faim rang 3 | Comme une nourriture de rang 3 | Aucun |
| Faim rang 2 | Comme une nourriture de rang 2 | Aucun |
| Faim rang 1 | Comme une nourriture de rang 1 | Aucun |
| Affamé | Bloquée | Malus de vitesse d'attaque, battements de cœur des êtres vivants proches |

**Soleil.** Il s'applique de jour, à ciel ouvert. Ses effets sont des dégâts légers sur la durée, un malus de vitesse d'attaque, une vulnérabilité à tous les dégâts et un léger éblouissement.

| Situation | Soleil |
| --- | --- |
| Nuit, ou sous un toit | Aucun effet |
| Jour à ciel ouvert, temps clair | Effets complets |
| Pluie ou nuages | Effets atténués |
| Orage | Aucun effet |

**Autres faiblesses**

- L'argent inflige des dégâts doublés.
- La lumière purificatrice (torches et lanternes des chasseurs) inflige des dégâts très légers sur la durée : supportable longtemps, mais désagréable.

**Protections contre le soleil**

- Objets occultes (capuche, voile) qui atténuent les effets sans les annuler.
- Potion de protection solaire fabriquée à l'autel, en 3 niveaux : les niveaux 1 et 2 atténuent de plus en plus, le niveau 3 annule les effets pendant quelques minutes.

## Le Comte et la Comtesse

Dans le Comté, le Comte et la Comtesse sont trop puissants pour être combattus et restent pacifiques envers les joueurs. On ne pourra les vaincre que plus tard, dans un donjon épique.

- **Dans le fragment.** Ils ignorent les joueurs mais ripostent s'ils sont attaqués. En multijoueur, la riposte vise tout le groupe présent, pas seulement l'attaquant.
- **Un rôle d'observateur.** Leur présence calme, qui laisse les joueurs passer, raconte quelque chose : ils tolèrent, voire attendent, ceux qui s'intéressent à l'occulte. Les notes du manoir peuvent le suggérer.
- **Le donjon du Comte.** C'est la fin de partie, ouverte par une clé de maître chasseur ou de seigneur de la nuit, au choix. Le combat est pensé pour un groupe.

La façon de rendre le Comte pacifique dans le fragment (rôle neutre avec riposte) est à traiter dans le fil des mobs.

## Zones à venir

De nouvelles zones s'ouvrent par des clés fabriquées sur l'une ou l'autre voie. Toutes sont des instances où le groupe entre ensemble.

| Zone | Voie | Format | Clé |
| --- | --- | --- | --- |
| Contrats de primes | Chasseurs | Mini-fragment court : une cible, un lieu, une récompense | Contrat fabriqué à l'établi |
| Rites occultes | Occulte | Mini-fragment court : récolte rare, épreuve ou rituel | Clé fabriquée à l'autel |
| Donjons de chasseurs | Chasseurs | Donjon en plusieurs salles avec boss | Palier 3 ou 4 de l'établi |
| Donjons occultes | Occulte | Donjon en plusieurs salles avec boss | Palier 4 de l'autel |
| Donjon du Comte | Les deux | Donjon épique de fin de partie | Maître chasseur ou Seigneur de la nuit |

D'autres idées restent ouvertes : des brèches vers d'autres lieux, ou des contrats spéciaux pour les joueurs vampires.

## Lore implicite

L'histoire du Comté se raconte par fragments : des notes de quelques lignes, placées là où le joueur passe déjà.

| Où | Qui parle | Ce que ça raconte |
| --- | --- | --- |
| Tableau du camp de brèche | Les chasseurs | L'appel à l'aide, les premiers contrats |
| Coffres du camp des chasseurs | Les chasseurs | Leur traque, leurs pertes, leurs méthodes (argent, feu purificateur) |
| Villages et fermes | Les anciens habitants | La vie avant la malédiction, la chute du Comté |
| Tombes et cimetières | Épitaphes | Des noms et des destins, des indices sur les zombies |
| Postes de garde, prison | Les gardes | La loi du Comte, les prisonniers |
| Manoir | Le Comte, la Comtesse, leurs serviteurs | Leurs rites, leur pacte, ce qu'ils attendent des visiteurs |
| Après le rituel | Une voix intérieure | La note qui marque la transformation |

Le ton visé : des phrases courtes, sans tout expliquer, pour que le joueur reconstitue l'histoire lui-même. Le support technique (livre lisible, panneau, objet avec description) est à vérifier dans Hytale 0.7.2.

## Multijoueur, existant et suite

**Multijoueur.** La progression vit dans l'inventaire de chaque joueur, donc on peut s'entraider et échanger trophées et fioles. Les instances (contrats, rites, donjons) accueillent tout le groupe. Mordre un autre joueur avec le Baiser du Vampire n'est possible que si le serveur active le PvP.

**Déjà en place et réutilisé :** brèche des chasseurs, fragment Comté Vampire et ses lieux, mobs et élites, chasseurs neutres, armes et flèches en argent, feu purificateur, autel sacrificiel et runes, clé de portail. L'établi de chasseur à paliers et le wiki joueur sont en cours dans d'autres fils.

**Questions ouvertes**

- Les noms définitifs des paliers et des trophées.
- Le support des notes en jeu (livre, panneau, description d'objet).
- Les ingrédients exacts du rituel de transformation et du rituel inverse.
- Le thème du premier mini-fragment de contrat et du premier rite occulte.

**Prochaines étapes proposées**

- [ ] Rendre le Comte et la Comtesse pacifiques avec riposte de groupe
- [ ] Ajouter le tableau de contrats et la première note dans le camp de brèche
- [ ] Ajouter les trophées d'élite et les brancher sur les paliers de l'établi
- [ ] Créer le statut vampire : rituel, faim de sang, soleil, faiblesses
- [ ] Créer les fioles de sang, la potion solaire en 3 niveaux et le rituel inverse
- [ ] Écrire les premières notes de lore
- [ ] Concevoir le premier mini-fragment de contrat
