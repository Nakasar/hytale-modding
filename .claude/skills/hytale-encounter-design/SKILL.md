---
name: hytale-encounter-design
description: Concevoir et régler des combats Hytale lisibles et justes pour les mods Nakasar — élites, boss, mini-boss, adds, phases, attaques annoncées, arènes, mise à l'échelle par groupe, récompenses. À utiliser dès qu'une tâche crée ou retouche un mob qui combat, un boss de donjon ou de fractale, une attaque, une phase ou une arène, ou quand Kevin dit qu'un combat est "illisible", "trop dur", "injuste", "ennuyeux", "les attaques ne touchent pas", même si la demande est formulée côté code ("ajoute une attaque au Champion", "le boss doit invoquer…").
---

# Design de rencontres

Les combats des mods Nakasar s'inspirent de Deepworks (donjon vanilla) et de Guild Wars 2 (fractales). Kevin a
posé des règles claires, après plusieurs reprises de boss : **la lisibilité d'abord**. Un joueur doit comprendre
ce qui va le toucher, pourquoi il a été touché, et ce qu'il doit faire. Un boss spectaculaire mais illisible
est refait ; un boss lisible mais plat se corrige en ajoutant une mécanique, pas des PV.

## Démarche

1. **Partir du design écrit.** Les documents de conception (GDD des fractales `docs/fractales/gdd.md`, docs
   Claude listés dans la mémoire du projet, `docs/vampires/`) font foi sur le code actuel quand Kevin l'a dit.
   Pour une fractale « d'après GW2 », relire le déroulé GW2 (wiki.guildwars2.com) et rester fidèle à l'idée
   de chaque mécanique, adaptée aux moyens de Hytale.
2. **Écrire la fiche de rencontre** avant de coder (dans la PR ou le doc) : rôle du combat dans le parcours,
   identité en une phrase, 2 à 4 mécaniques avec leur contre (esquiver, interrompre, se placer, porter un objet,
   tuer les adds…), phases et transitions, arène et décor utile, échelle de groupe, récompense. Quand un choix
   change l'expérience voulue (difficulté, punition, ce qui est obligatoire), le proposer à Kevin plutôt que de
   le trancher.
3. **Assembler avec les briques existantes** (skill `hytale-mod-reuse`) : télégraphes, charge, stun, barre de
   boss, vie par groupe, vie fixée, serviteurs et bouclier, cages, objets portés, arènes qui se ferment.
4. **Vérifier la lisibilité** avec la grille ci-dessous, puis `./gradlew check`.
5. **Lister les réglages** (PV, dégâts, délais, rayons) dans des constantes nommées et dans la PR, pour que
   Kevin puisse demander « 20 % de PV en moins » sans fouiller.

## Grille de lisibilité (règles de Kevin)

- **Rouge = négatif, toujours et seulement.** Les zones au sol rouges annoncent un coup ; les autres couleurs
  sont réservées aux effets positifs (zone sûre, soin, objet à prendre). L'élément d'une attaque se montre par
  le geste du lanceur (fiole levée de la bonne couleur, crépitements), pas par la couleur de la zone.
- **Les attaques majeures sont annoncées au sol ≥ 1,2 s**, à la taille exacte du coup (le moteur
  `Telegraph` applique le coup lui-même sur la zone dessinée). Cercles petits et nets, cônes qui se chargent
  comme Deepworks, lignes pour les charges. Rien d'aveuglant, pas d'écran saturé de particules.
- **Les coups simples peuvent frapper fort sans marque au sol** s'ils sont prévisibles : combos fixes, élan
  d'animation lisible (copier `Dungeon_Goblin_Mace_Slam` : effet d'ancrage + lueur de charge + avertissement).
- **Inévitable = annoncé sur la cible** (marque au-dessus de la tête, notification) : l'emprisonnement du
  Capitaine, les cages, le rayon de l'Abîme de Jade. Le joueur doit savoir que c'est lui et quoi faire.
- **Fenêtres de punition logiques** : le boss étourdi après une charge ratée contre un poteau, pas au hasard.
- **Deuxième phase à 50 % seulement si elle apporte quelque chose.** Transitions marquées (bouclier, message,
  changement d'arène).
- **Le décor sert le combat** : poteaux qui arrêtent une charge, braseros qui bloquent un plongeon, piliers qui
  coupent une vague, leviers de cellule. L'idée du décor se garde partout où l'élite apparaît, la disposition
  exacte peut varier.
- **Pas de découverte forcée par le chat** : pas d'indices dans le chat ni de descriptions qui expliquent la
  mécanique ; les joueurs découvrent (notifications courtes seulement pour les actions d'objet, ex.
  « accroupis-toi pour ramasser »).

## Mise à l'échelle et récompenses

- PV des boss de donjon et de fractale : +55 % par joueur de plus (`GroupHealth.PER_PLAYER`) ; ennemis des
  fractales +25 % par joueur de plus ; fractales : × (1 + niveau/100) en PV, dégâts × (1 + niveau/150), délais d'annonce × `windupFactor`.
- Adds : nombre ou PV selon le groupe ; serviteurs jamais sauvegardés, retirés au-delà d'une laisse.
- Difficulté visée pour les élites du monde : **défi modéré**, barre de boss pour toutes.
- Récompenses : un sac/coffre par joueur en fin de donjon ou fractale, un trophée par groupe ; ressources rares
  (éclats de rune, crocs…) seulement là où Kevin l'a décidé (voir mémoire du projet). Ne pas ajouter de
  source de loot rare sans le lui proposer.

## Pièges techniques fréquents

- Détecter une mort dans le groupe d'inspection : la vie est **déjà** diminuée (`health <= min`).
- Invulnérabilité conditionnelle = filtre de dégâts (groupe filter) ou `Invulnerable` vanilla (barre de boss en
  mode invulnérable) ; toujours retirer l'état au chargement et au premier coup si la condition a disparu.
- Une seule interaction `AimingReference` par chaîne d'attaque ; `SkipAiming true` exige `LineOfSight` /
  `AvoidFriendlyFire` false ; `HeadMotion Watch` exige un capteur qui fournit la cible.
- Le sélecteur de coup part des yeux : une frappe de colosse qui « rate » les joueurs au sol doit étendre le
  bas du volume (`fr.swing extend_bottom`).
- Gros mobs : portes et couloirs ≥ hitbox ; vol stationnaire en Walk (MinHover/MaxHover), pas Fly seul.
- Logs INFO nommés (`Nakasar_Fractal_Cage`, `Nakasar_RootTrap`…) sur chaque mécanique Java : quand Kevin dit
  « ça ne s'est pas produit », on lui demande ces lignes (skill `hytale-ingame-feedback`).
