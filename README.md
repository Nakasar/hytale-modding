# hytale-modding

Mods pour **Hytale** (serveur `0.7.x`, « Update 7 »), développés par Nakasar.

Deux mods, chacun avec son dossier de documentation :

| Mod | Code | Documentation |
|-----|------|---------------|
| **Vampires** : le domaine du Comte vampire (plugin Java + pack d'assets, artefact `Nakasar-Vampires-<version>.jar`) | `mods/nakasar-vampires` | [docs/vampires](docs/vampires/) |
| **Fractales des Brumes** : les fractales de Guild Wars 2 transposées dans Hytale, pour 1 à 5 joueurs (en cours : socle, Observatoire, progression, instabilités, fractales Falaise, Inclassable, Volcanique, Océan solide, Marais et Tempête de neige, fractales du jour, cosmétiques, wiki) | `mods/nakasar-fractals` | [docs/fractales](docs/fractales/) |

Les notes communes aux deux mods (API serveur, PNJ) restent à la racine de `docs/`.

### Vampires

| Partie | Contenu |
|--------|---------|
| Fragment Halloween | Fragment d'Orbis ouvert depuis l'Ancienne passerelle : manoir du Comte, village abandonné, fermes délaissées, ancien poste de garde, cryptes, châteaux hantés, cimetières, forêts mortes |
| Mobs | Comte et Comtesse Vampire (boss qui lancent les sorts des runes), rejetons, fantômes, morts-vivants du domaine et leurs élites ; tous les mobs du fragment sont alliés entre eux |
| Runes et autel | 4 runes d'abilities (Baiser du Vampire, Domination, Téléportation, Chaînes spectrales) et l'autel sacrificiel qui les fabrique ; la Domination fait changer de camp le mob visé |
| Établi des chasseurs | Établi à 2 niveaux : torches et lanternes de feu purificateur, runes Aura de lumière et Invisibilité, fragment du Comté Vampire |
| Lance | Lance de fer à deux mains : enchaînement, coup chargé, compétence ultime |
| Armes en argent | Version en argent de chaque arme standard, de la lance du mod et des flèches : double dégâts contre les vampires (Comte, Comtesse, rejetons) |

Le guide du joueur (fragment, structures, bestiaire, brèches, objets) est un wiki publié sur GitHub Pages : https://nakasar.github.io/hytale-modding/ (sources Markdown dans [docs/wiki](docs/wiki/README.md), site Docusaurus dans [wiki](wiki/), aperçu local : `cd wiki && npm ci && npm start`).
Le détail du mod (fichiers, chaînes d'interactions, camps, réglages) est dans [docs/vampires/mods.md](docs/vampires/mods.md).
L'histoire et la progression visées (voie des chasseurs, voie occulte, joueur vampire, zones à venir) : [docs/vampires/histoire-progression.md](docs/vampires/histoire-progression.md).

### Fractales des Brumes

Le game design document (Observatoire, fragment d'instance, niveaux 1 à 100, agonie et Autel des infusions, 6 fractales de la saison 1 avec leurs boss, transposition des mécaniques GW2, étapes d'implémentation) est dans [docs/fractales/gdd.md](docs/fractales/gdd.md). Le développement commence par la fractale de la Falaise.

Étape 1 (socle) : le mod `mods/nakasar-fractals` (manifest `Nakasar:Fractals`, jar `Nakasar-Fractals-<version>.jar`,
plugin `dev.nakasar.hytale.fractals.FractalsPlugin`). Il ne dépend pas du mod Vampires : ses briques de combat y sont
copiées, sans bibliothèque commune, sous des ids `Nakasar_Fractal_` (un correctif d'un côté se reporte à la main de
l'autre) :

| Brique (copie de) | Dans le mod Fractales |
| --- | --- |
| attaques annoncées `Nakasar_Telegraph` | `Nakasar_Fractal_Telegraph` (`combat/`), sans braseros ni Domination ; ses alliés sont le groupe `Nakasar_Fractal_Foes` |
| charge `Nakasar_Charge` | `Nakasar_Fractal_Charge`, sans poteaux de grange |
| étourdissement `EliteStun`, `Nakasar_StunSelf` | `BossStun`, `Nakasar_Fractal_StunSelf`, effet `Nakasar_Fractal_Stunned` |
| serviteurs et bouclier `Nakasar_SummonMinions`, `MinionShieldSystem` | `Nakasar_Fractal_SummonMinions`, `MinionShieldSystem.register(rôle, vague)` (`minions/`) |
| cellules du Capitaine `Nakasar_ImprisonPlayer` | `Nakasar_Fractal_Cage`, bloc invisible `Nakasar_Fractal_Cage_Cell` (cages de l'Archidevin) |
| barre de boss, vie selon le groupe | `BossBarSystem.register(rôle)`, `GroupHealth` (`boss/`) |
| remise en place du décor `Restores`, `WorldBlocks` | `arena/` |
| zones rouges `tools/tower_warnings.py` | `tools/generate_warnings.py` (`Nakasar_Fractal_Warning_*`, `Nakasar_Fractal_Cone_*`) |

Les validateurs hors jeu (`tools/ValidateAssets.java`, `tools/ValidateRoles.java` et les listes vanilla) sont copiés
de même et tournent sur le pack du mod à chaque `build`.

Étape 2 (entrée) : le **Fragment des Brumes** (`PortalKey_Nakasar_Fractal`, établi : 4 éclats de rune + 1 cœur du
Vide) se pose dans l'Ancienne passerelle et ouvre l'**Observatoire**, une île dans les Brumes générée par
`tools/generate_observatory.py` (prefab, blocs et textures, instances, portail, langues et
`observatory/ObservatoryLayout.java` ; `--preview DIR` dessine le plan).

- Le premier joueur arrivé **mène**. Les joueurs debout sur le **cercle d'harmonisation** autour de l'Astrolabe forment
  le groupe (5 au plus) ; le meneur part toujours, même hors du cercle (seul si le cercle est vide).
- **Sélection** (refaite le 21 octobre 2026 : une arche par fractale ne tenait pas à des dizaines de fractales) : à
  l'entrée du cercle, le **distributeur de noyaux** donne le noyau d'une fractale (`Nakasar_Fractal_Core_<Id>`) et le
  **distributeur de diapasons** celui d'un niveau (`Nakasar_Fractal_Level_<1-100>`, rangs Initié, Adepte, Expert,
  Maître), gratuits (boutiques de troc sans prix `Nakasar_Fractal_Cores` et `Nakasar_Fractal_Levels`).
- Les joueurs posent un noyau et un diapason dans la **console de sélection** (sur le socle de l'Astrolabe, deux
  emplacements partagés par tout l'Observatoire, objets gardés d'une partie à l'autre) : le cercle est **harmonisé**,
  annoncé en titre à tous.
- Le meneur utilise un des 4 **résonateurs** au bord intérieur du cercle : tout le cercle part dans une instance de
  la fractale, propre au groupe, si le niveau ne dépasse pas son plus haut niveau débloqué. Une nouvelle fractale ne
  demande qu'une ligne dans `FRACTALS` (son noyau) et son id dans `FractalCatalog`.
- La **pierre de retour** (ou `/fractale quitter`) ramène à l'Observatoire, gardé ouvert tant que la fractale vit.
- Le **golem d'essai** (ouest) annonce les dégâts reçus et reprend ses PV ; son **pupitre** lui fait rejouer les zones
  rouges (cercle, cône, ligne, puis la cage d'essai).
- `/fractale niveau <n>`, `groupe`, `lancer <fractale>`, `quitter`, `infos` : secours des blocs, ouvert aux joueurs.
- Un joueur tombé dans le vide revient au point d'apparition du monde.

À vérifier en jeu : textures des blocs, golem (modèle `Golem_Firesteel` sans flammes), liste des 100 diapasons dans
la fenêtre de troc, fenêtre de la console (partagée entre joueurs), titre d'harmonisation, modèles des noyaux et
diapasons en main.

Étape 3 (progression) : `tools/generate_progression.py` (éclats, infusions, coffres de rang, recettes, agonie,
boutique et PNJ de l'Archiviste, modèles et icônes) et le paquet Java `progress/`.

- **Niveaux débloqués par joueur**, sauvegardés avec lui (composant `Nakasar_Fractal_Progress`) : on commence au
  niveau 1, finir une fractale à son plus haut niveau débloque le suivant. Le meneur ne lance qu'un niveau qu'il a
  débloqué ; si un nouveau meneur en a débloqué moins, le niveau redescend.
- **Agonie** (`Nakasar_Fractal_Agony`, à partir du niveau 26) : 4 %, 6 % puis 8 % des PV max par seconde selon le rang,
  réduits par la **résistance** jusqu'à zéro à la résistance conseillée (10 à 40 en Adepte, 50 à 100 en Expert, 110 à
  150 en Maître). Le premier cercle du pupitre d'essai pose de l'agonie au niveau harmonisé, pour tester.
- **Autel des infusions** (portable, recette à l'établi) : ouvre les 12 emplacements d'infusion du joueur ; la somme
  des infusions posées est sa résistance. Infusions +1 à +15 ; au **Creuset des Brumes** (établi, recette à l'établi),
  2 × infusion n + 4n éclats donnent l'infusion n+1, et 25 éclats + 1 éclat de rune refont un Fragment des Brumes.
- **Coffre de fin** : chaque membre du groupe y prend une fois le coffre de son rang (éclats de Brume, matériaux,
  chance d'infusion), qu'il ouvre en main. Il apparaît une fois le boss de la fractale vaincu.
- **L'Archiviste** (est de l'Observatoire, invulnérable) et son comptoir : troc d'éclats contre infusions +1, +2, +4 et
  Fragment des Brumes.
- `/fractale infos` : niveau débloqué et résistance.

À vérifier en jeu : fenêtre de l'autel (glisser une infusion, sauvegarde à la reconnexion), PNJ Archiviste (rôle
`OpenBarterShop` accepté ? sinon le comptoir), dégâts et message d'agonie, coffre de rang.

Étape 4, **la Falaise** (`tools/generate_cliffside.py` écrit le décor, les blocs, les PNJ, les effets et
`cliffside/CliffsideLayout.java` ; `--preview DIR` dessine la face et le dessus) : un colosse de pierre enchaîné à
une falaise, qu'on escalade par des échafaudages.
- **Camp** au pied : le Chercheur et une vague de cultistes ; le **râtelier** ne donne le marteau du culte qu'une fois
  le camp nettoyé, et à un seul joueur à la fois.
- **Marteau du culte** (`hammer/`) : le prendre coûte 10 % des PV. La **Corruption** avance par crans de 10 s : en
  main, le cran 1 s'ouvre et son effet se vide sous les yeux du joueur ; vidé, le cran monte si le marteau est encore
  en main, sinon il redescend. Par cran, dégâts subis +8 % ; dès le cran 2, on ne fait plus que 70 % de ses dégâts ;
  le cran 3 étourdit 2 s, et vouloir monter au-delà fait échapper le marteau (étourdi 3 s). Toucher un cultiste avec,
  puis le voir mourir dans les 15 s (même tombé loin), ou voir un ennemi mourir à moins de 10 blocs, le **charge** ;
  un coup chargé fissure un sceau. Les cultistes ne subissent plus de recul et sont ramenés à leur poste s'ils
  tombent de leur plate-forme.
- **5 sceaux** (PNJ fixes, nos instances refusant les coups sur les blocs) : genoux (2 coups chacun), poitrine (3),
  poignets (3, bulle alternée : frapper l'un protège l'autre ; les incantateurs proches réparent un coup toutes les
  20 s). Les vagues se renouvellent tant que le sceau tient ; chaque palier brisé ouvre une barrière de brume et
  déplace le point de retour.
- **Puzzles de saut** (`cliffside/Traps`, `SafeLandings`) : tunnel aux dalles piégées (18 % des PV), escalade sous le
  souffle des gargouilles (trois leviers en haut les coupent), foyers de la passerelle du torse (deux sur trois
  s'embrasent toutes les 7 s), rampes aux bombes (leviers R1 et R2). Tomber dans une zone de saut ramène à la
  dernière **plate-forme sûre**. Tirer un levier fige 4 s.
- **L'Archidevin** (`cliffside/Archdiviner`, barre de boss et **barre de défiance** ◆/◇ : ouverte pendant ses attaques
  annoncées, elle se brise en 8 coups + 4 par joueur de plus, 3 au marteau, et l'étourdit 5 s) : transitions à 75, 50,
  25 % et 1 PV, invulnérable tant que le sceau du cou n'a pas reçu un coup chargé (incantateurs et marteau fournis) ;
  entre 50 et 25 %, protection, **cages** (cercle rouge, alliés qui forcent la porte en 5 utilisations, sortie seule
  au bout de 15 s) et dévoreurs ; sous 25 %, hâte et frappes marquées. Niveau 25 : ruée ; 51 : mur anti-projectiles ;
  71 : forme démoniaque. Vaincu, le coffre de fin et la pierre de retour apparaissent.
- PV des ennemis × (1 + 25 % par joueur de plus) × (1 + niveau / 100) ; leurs dégâts × (1 + niveau / 150) ; annonces
  plus courtes avec le niveau (jusqu'à −25 %).

À vérifier en jeu : modèle des sceaux, force du souffle des gargouilles, escaliers en colimaçon praticables, modèle
provisoire du dévoreur (`Zombie_Aberrant_Small`), blocs utilisables (râtelier, leviers, portes) dans une instance
sans modification de blocs, rotation des barreaux de cage.
Décor (`tools/fractal_nature.py`, partagé par les fractales : bruit lisse, feuillus et résineux vanilla, buissons,
rochers moussus, herbes et massifs de fleurs, îles flottantes) : falaise en amphithéâtre à strates et mousse,
corniches fleuries et lianes, crête boisée, plateau du camp au contour irrégulier avec chemins de terre battue et
feu de camp, colosse de basalte moussu, matinée claire (`Nakasar_Fractal_Weather_Cliffside`, 10 h 30). À vérifier
en jeu : lianes et fleurs bien posées (pas de plantes en l'air), teinte de l'herbe et des feuilles, lumière du jour,
mousse sur le colosse sans gêner les passages.

Étape 5, **les instabilités** (`instability/`) : 0 en Initié, 1 en Adepte, 2 en Expert, 3 en Maître, tirées une fois
par jour et par fractale pour tout le serveur (les rangs hauts gardent celles des rangs bas). Un joueur seul en tire
une autre à la place de celles qui demandent un groupe. Les 8 : Dernier rire (les ennemis explosent à leur mort),
Traînée toxique, Malaise social, Restez groupés, Bombe de flux, Vengeance, Pente glissante (recul accru), Oiseaux
(nuées de corbeaux). `/fractale instabilites` donne celles de la partie en cours ou du jour.

Étape 6, **Inclassable et Volcanique** (`tools/generate_uncategorized.py`, `tools/generate_volcanic.py`, paquets
`uncategorized/` et `volcanic/`), avec les briques réutilisables : portes et points de retour (`arena/Gates`),
consoles simultanées (`Consoles`, fenêtre 12/8/4 s selon le groupe), objets portés ou lancés (`Carried`,
`Nakasar_Fractal_ThrowItem`), bouclier à compteur de coups (`HitShield`), charges +/- (`Polarity`).
- **Inclassable** : plateformes des harpies (recul hors des plateformes, retour à la dernière plateforme sûre),
  cour de la prison (générateur, puis prisonniers libérés un par un : lapin enragé, saboteur, chaman du feu, ettin),
  escalier sous le feu de 4 tourelles (couloirs annoncés), 3 consoles à activer ensemble ; **Vieux Tom** et son gaz
  (le ventilateur le chasse, il faut dès le niveau 12 deux batteries chargées de larmes des Brumes) ; plateformes de
  lumière ; l'**Asura délirant** : 4 golems de cristal réveillés un à un puis ensemble, charges + et − à alterner,
  éclairs sous les joueurs et orbes à tête chercheuse.
- **Volcanique** : camp grawl autour d'un totem (la barre du totem compte les morts restantes), couloir aux
  **rochers roulants** (niches pour s'abriter, traînée de feu), **Champion chaman** (8 piles qui réduisent ses dégâts
  subis, retirées une à une par les **pierres imprégnées** lancées, tombées des chutes de pierres ; des vétérans
  marchent vers 4 captifs à protéger, 5 éclats de Brume en plus si tous survivent), mine sur rails au-dessus de la
  lave, puis le **Chaman imprégné** : Pieds brûlants (bouger ou rester au sol), puits de lave, flamme qui se propage ;
  à 75/50/25 % il plane vers un villageois sous un bouclier à compteur de coups (le briser l'étourdit, l'atteindre le
  soigne de 25 %).

Modèles provisoires : harpies (chauve-souris ×2), lapin (boîte), saboteur, chaman du feu, grawls, captifs et Chaman
imprégné (humanoïdes ; celui de GW2 est une harpie géante), ettin (`Zombie_Aberrant_Big`), corbeaux et chauves-souris
(`Bat`), larves (`Spirit_Ember`).

À vérifier en jeu : recul des harpies, portes des cellules, couloirs des tourelles le long de l'escalier, gaz et
ventilateur de Tom, transparence des plateformes de lumière, lancer de la pierre imprégnée (clic droit vers le
Champion), vétérans qui rejoignent les captifs, rochers et niches, Pieds brûlants au saut, vol plané du Chaman.

Étape 7, **Océan solide et Marais** (`tools/generate_solid_ocean.py`, `tools/generate_swampland.py`, paquets
`solidocean/` et `swampland/`). `SafeLandings` accepte désormais plusieurs blocs d'atterrissage (fragments de jade).
- **Océan solide** : fragments de jade à sauter au-dessus de l'océan (une chute ramène au fragment d'avant),
  irukandjis en chemin, puis l'**Abîme de Jade**, immobile et invulnérable : phase 1, deux tentacules à abattre et un
  test d'agonie (niveau 26+) ; phase 2, des **colosses de jade** (3 + 1 par joueur) qui renvoient les projectiles sauf
  étourdis et lâchent les **cristaux réfléchissants** ; fin, les tentacules lâchent les cristaux. Toutes les 11 s, un
  crâne marque un joueur ; quand il disparaît, le rayon se fixe sur sa place (0,7 s pour s'écarter) : tenir un cristal
  l'absorbe et charge le joueur, qui lance alors le cristal sur l'Abîme (-5 %, tentacule -3 %). Sous 8 %, dernier
  rayon sur tout le monde, sans esquive.
- **Marais** : trois feux-follets à rapporter dans leurs failles (minuteur 64 s, 38 s dès le niveau 26, 30 s dès le
  51) ; des murs surgissent au premier pris ; fils tendus, pièges à loup, plaques à piques, œufs d'araignée ; deux
  fusils revigorants (rapidité). Raté : tout s'éteint, les feux-follets changent de place. Embuscade du **Moussu**
  (loups, furtivité puis attaque surgie en ligne rouge avec défiance ouverte, forme sauvage sous 50 %), puis
  **Carnasse** : vulnérable, lui et ses esprits, seulement dans le **cercle vert** qui saute de faille en faille ;
  assauts à 75/50 % (esprits à abattre, pluie de poison, puis fleurs de poison), à 25 % quatre feux-follets à
  rapporter en 35 s, sinon purge corporelle (60 %, mortelle dès le niveau 76).

Modèles provisoires : Abîme de Jade et tentacules (boîtes), colosses (`Golem_Crystal_Thunder`), irukandjis
(`Spirit_Frost`), loups du Moussu et esprits animaux (boîtes), le Moussu (humanoïde), Carnasse (`Spirit_Root` ×2,4).

À vérifier en jeu : sauts entre fragments de jade, crâne et cercle du rayon, absorption par le cristal tenu, lancer
du cristal (clic droit vers l'Abîme), renvoi des colosses ; murs et pièges du marais, fusils, furtivité et
réapparition du Moussu, cercle vert (particules) et vigueur, assauts et fleurs, feux-follets des coins.

Étape 8, **Tempête de neige** (`tools/generate_snowblind.py`, paquet `snowblind/`, thème de décor `snow`). Partout,
l'**Hypothermie** (`Frost`) : loin d'un feu allumé, une pile toutes les 5 s (2,5 s dans le blizzard, deux fois moins
vite torche en main), jusqu'à 10 ; près d'un feu (Chaleur), une pile en moins toutes les 1,2 s. Chaque pile coûte
0,3 % des PV max par seconde (cause `Nakasar_Fractal_Cold`), la course ralentit dès 5 piles. À 10 piles, le joueur est
pris dans un **éclat de glace** que ses alliés doivent briser (ses propres coups ne comptent pas) ; il repart à 6 piles.
- **Camp** : le grand feu s'allume et se nourrit de **fagots** (tas sous les arbres, 3 portés au plus, repoussent en
  20 s) ; il brûle 1,5 %/s et fait fondre le **mur de glace** rangée par rangée (90 s à mi-bois, plus vite bien
  nourri). Toutes les 14 s, des **élémentaires de glace** marchent vers le feu et lui retirent 35 % en l'atteignant ;
  toutes les 25 s, loups ou cultistes attaquent le camp.
- **Source élémentaire** : cinq **foyers** à allumer torche en inventaire (râtelier à l'entrée) puis à nourrir de
  fagots (tas des huttes). Chaque foyer éteint donne une pile de **bouclier de givre** (−18 % de dégâts, ❄ sur la
  barre) ; à 75/50/25 % elle frappe les foyers allumés (cercles rouges, −50 % de bois) ; tous éteints : **blizzard**.
- **Forêt sombre** : sentier sinueux sous les sapins, empreintes au sol, fausses pistes, deux embuscades de cultistes.
- **Chaman légendaire** : la porte du village se ferme ; trois **cristaux corrompus** le protègent à chaque phase au
  sol ; ses coups d'épée ajoutent 2 piles (ses attaques annoncées ont la cause `Nakasar_Fractal_Frost`) ; pluie de
  glace, anneau de pics, souffle glacé. À 75 et 50 %, il saute sur son **balcon**, invulnérable, et fait pleuvoir des
  pics sous chaque joueur ; l'**Effigie de glace** (défiance ouverte) brisée ou détruite le fait redescendre. À 25 %,
  **forme d'ours** (bonds qui renversent 3 s).

Des remparts de glace barrent toute l'île de part et d'autre du mur, de la brume de la Source et de la porte du
village : on ne contourne plus un passage par la forêt du pourtour. Modèles provisoires : élémentaires et Source
(`Spirit_Frost`), cultistes (humanoïdes), Chaman (grawl ×1,45), loups, ours, Effigie, cristaux et éclat (boîtes).

À vérifier en jeu : fumée et lumière du grand feu et des foyers, fonte du mur, élémentaires qui rejoignent le feu
(point d'attache), râtelier et torche en main (lumière), blizzard et neige (particules), éclat de glace (immobile,
brisé par les alliés), saut au balcon et retour, forme d'ours, obscurité de la forêt (17 h 30).

Étape 9, **finitions** :
- **Fractales du jour** (`party/DailyFractals`) : 3 fractales ouvertes tirées chaque jour (graine = date du serveur).
  La première fois du jour qu'un joueur en termine une, le coffre de fin lui donne en plus le **coffre des fractales
  du jour** (`Nakasar_Fractal_Daily_Bag` : 12 à 18 éclats, une infusion +1 ou +2, un matériau, 1 chance sur 10 d'un
  cosmétique). Le jour et les fractales déjà récompensées sont sauvegardés dans `Nakasar_Fractal_Progress`
  (`DailyDay`, `DailyDone`). **Tableau des fractales du jour** au nord du Registre (`Nakasar_Fractal_DailyBoard`) et
  `/fractale jour`.
- **Cosmétiques de saison** (`tools/generate_cosmetics.py`, sans protection) : Couronne des Brumes (tête, 150
  éclats), Capuche de l'Archidevin (tête, 200), Mantelet des Brumes (torse, 250), vendus par l'Archiviste.
- **Wiki joueur** : onglet **Fractales** (`docs/wiki/fractales/` : présentation, Observatoire, progression,
  instabilités, les 6 fractales, cosmétiques) ; le site s'appelle désormais « Wiki des mods Nakasar » et copie aussi
  les icônes du mod Fractales.

À vérifier en jeu : tableau du jour, coffre du jour reçu une seule fois par fractale et par jour (même après
reconnexion), cosmétiques portés (placement sur la tête et le torse, cape), trocs de l'Archiviste.

**Décor de toutes les fractales** (`tools/fractal_nature.py` : thèmes prairie, Brumes, volcan, marais et jade ;
`rim` pour un pourtour naturel autour d'un lieu, `natural_ground`, `dress`, `islet` et `scatter_islets` pour des îlots
loin du parcours, jamais un raccourci) : les matières de `fractal_common.pick` sont tirées par plaques lisses et non
plus en damier, les dessous d'îles sont irréguliers. Chaque fractale a son ciel figé (`Nakasar_Fractal_Weather_*`).
- **Observatoire** : jardins de glycines et d'arbres bleus hors du garde-corps, cristaux, îles flottantes autour.
- **Inclassable** (11 h) : jardins autour du départ, de la cour, de la salle de Vieux Tom et de l'arène (jamais entre
  deux sauts), roche et lianes sous les plates-formes des harpies, îlots fleuris.
- **Volcanique** (ciel de fumée, 15 h) : terres brûlées et arbres morts, falaises du canyon et de la mine, volcan au
  sud-ouest avec coulées de lave figée et cratère.
- **Océan solide** (midi) : l'océan de jade (houle, récifs de corail, aiguilles de cristal) passe sous le filet
  anti-chute (y 34 dans le monde), on n'y reste pas ; pourtour de sable et de corail autour de l'arène.
- **Marais** (brume, 15 h) : saules à lianes, roseaux, champignons (pas sur les pièges, les lignes de mur ni les
  failles), falaises moussues et boisées tout autour ; la cachette du Moussu est enfouie dans la falaise.

À vérifier en jeu : plantes qui tiennent sur sable et cendre, coraux hors de l'eau, lianes sous les saules sans gêner
le passage, couleurs des ciels, lisibilité des pièges du marais.

### Notes communes

Les points d'API serveur vérifiés dans le jar `Server-0.7.2` sont notés dans [docs/api-0.7.2.md](docs/api-0.7.2.md).
Création de PNJ (rôles, IA, modèles, apparitions) : [docs/npc-0.7.2.md](docs/npc-0.7.2.md), et la référence complète des 179 briques d'IA générée depuis le jar : [docs/npc-reference-0.7.2.md](docs/npc-reference-0.7.2.md).

## Prérequis

- **JDK 25** (les classes du serveur 0.7.2 sont compilées en Java 25). Le build utilise une
  *toolchain* Gradle : si aucun JDK 25 n'est installé, le plugin `foojay-resolver` le télécharge.
- Rien d'autre : le wrapper Gradle (`./gradlew`) télécharge Gradle 9.8.1, et l'artefact serveur
  `com.hypixel.hytale:Server:0.7.2` vient du Maven officiel `https://maven.hytale.com/release`.

## Construire

```bash
./gradlew build
```

- `mods/nakasar-vampires/build/libs/Nakasar-Vampires-0.1.0.jar`
- `mods/nakasar-fractals/build/libs/Nakasar-Fractals-0.1.0.jar`

`build` lance aussi `validateJson`, qui vérifie la syntaxe de tous les JSON d'assets (le parseur du
serveur est strict : une virgule en trop fait échouer le chargement du mod).

`build` lance aussi, pour chaque mod, `validateRoles` (`mods/<mod>/tools/ValidateRoles.java`, rôles de PNJ) et
`validateAssets` (`mods/<mod>/tools/ValidateAssets.java`) :
il décode chaque asset du pack (biome, structure de monde, instance, portail, objets, environnements, météo,
spawns, modèles, effets, butins, interactions, y compris celles écrites en ligne dans `Next` ou `Parallel`)
avec les codecs du jar serveur et signale les clés inconnues et les valeurs invalides (par exemple un
`Parallel` à une seule branche), sans démarrer le jeu. Il vérifie aussi que
chaque bloc des prefabs et du générateur existe dans `tools/vanilla-block-ids-0.7.2.txt` (un id inconnu
devient un damier rose et noir en jeu). Il vérifie enfin les références vers les listes de butin (`DropList`, `DroplistId`, coffres des prefabs), les rôles
de PNJ (marqueurs et apparitions, invocations `Kind`) et les marqueurs d'apparition (`SpawnMarker`) : chaque id doit
exister dans le pack ou figurer dans `tools/vanilla-refs-0.7.2.txt`. En jeu, une liste de butin inconnue rejette le
rôle qui la cite, puis le marqueur qui fait apparaître ce rôle fait échouer tout le mod. Les autres ids référencés (sons, stats, `PortalKey_Taiga`,
`Env_Zone1_Plains`) ne sont pas vérifiés, ni les interactions de type Java de nos plugins et les assets
qui héritent d'un parent vanilla (notés « non vérifiable hors jeu »).

Les prefabs et la génération du monde sont produits par des scripts (déterministes) :

```bash
python3 mods/nakasar-vampires/tools/generate_prefabs.py    # 65 prefabs dans src/main/resources/Server/Prefabs/Nakasar/Halloween
python3 mods/nakasar-vampires/tools/generate_lore.py       # notes, épitaphes et tableau de la brèche (avant prefabs et butin)
python3 mods/nakasar-vampires/tools/generate_loot.py       # listes de butin des coffres
python3 mods/nakasar-vampires/tools/generate_worldgen.py   # biome + structure de monde
python3 mods/nakasar-vampires/tools/generate_pumpkin_models.py  # modèles animés de la citrouille géante et de ses vrilles (--preview DOSSIER : rendus)
```

## Déployer sur un serveur local

Indiquez le dossier `mods/` de votre serveur dans `gradle-local.properties` (fichier non versionné) :

```properties
hytale.modsDir=/chemin/vers/Server/mods
```

puis :

```bash
./gradlew deployToServer
```

(ou en une fois : `./gradlew deployToServer -Phytale.modsDir=/chemin/vers/Server/mods`).

Dans un monde solo, activez **Vampires** dans la liste des mods du monde.

**Mise à jour depuis les anciens mods séparés** : supprimez du dossier `mods/` les fichiers `Nakasar-Runes-*.jar`,
`Nakasar-Spear-*.zip`, `Nakasar-Halloween-*.zip` et `Nakasar-Mobs-*.jar` avant d'y mettre `Nakasar-Vampires-*.jar`
(ils déclarent les mêmes assets), puis activez Vampires dans les mondes qui utilisaient les anciens mods. Les ids
d'objets, de blocs, de PNJ et de prefabs n'ont pas changé : runes, autels posés, coffres et fragments déjà générés
restent valides.

### Pack de tous les mods

`./gradlew packMods` construit `build/distributions/Nakasar-Mods-Pack-<version>.zip`, qui contient les jars et
zips de tous les mods à sa racine (aujourd'hui le seul `Nakasar-Vampires-<version>.jar`) : il s'extrait directement dans le dossier `mods/` d'une save ou d'un serveur.
La CI publie le même contenu dans l'artefact `Nakasar-Mods-Pack` (onglet « Actions », en bas du run) : le zip
téléchargé s'extrait lui aussi directement dans `mods/`.

## Tester en jeu

Démarrer le serveur avec `--validate-assets` la première fois : il vérifie les références d'assets et les
« promesses » des mots-clés de runes, et s'arrête avec la liste des erreurs s'il y en a.

```text
/abilities give                      # donne toutes les runes (dont les 4 du mod)
/give Rune_Nakasar_VampireKiss       # ou une seule
/give Rune_Nakasar_Domination
/give Rune_Nakasar_Blink
/give Rune_Nakasar_SpectralChains
/give Weapon_Nakasar_Spear_Iron      # la lance
/give Weapon_Nakasar_Spear_Silver    # la lance en argent (toutes les armes en argent : Weapon_Nakasar_*_Silver)
/give Weapon_Nakasar_Arrow_Silver 40 # flèches en argent, munitions de tous les arcs et arbalètes
/give Ingredient_Bar_Silver 20       # lingots d'argent vanilla pour tester les recettes
/give Nakasar_Sacrificial_Altar      # l'autel sacrificiel
/give Ingredient_Rune_Shard 8        # éclats de rune pour tester les recettes
```

Fragment Halloween :

```text
/give PortalKey_Nakasar_Halloween    # la clé, à poser dans une Ancienne passerelle (Portal_Device)
/instances spawn Nakasar_Halloween_Fragment   # ou ouvrir l'instance directement, sans portail
```

Mobs (le manoir du comte, dans le fragment, contient déjà le Comte ou la Comtesse, une chance sur deux, et deux rejetons dans sa crypte) :

```text
/npc spawn Nakasar_Vampire_Count     # le boss
/npc spawn Nakasar_Vampire_Countess  # la boss
/npc spawn Nakasar_Vampire_Spawn     # un rejeton
/npc spawn Nakasar_Ghost             # un fantôme
/npc spawn Nakasar_Zombie_Villager   # villageois zombifié (aussi _Zombie_Farmer, _Zombie_Rebel, _Skeleton_Guard)
/npc spawn Nakasar_Zombie_Abomination  # élite des fermes : écrasement annoncé
/npc spawn Nakasar_Guard_Captain     # élite du poste de garde : fendant, tourbillon, emprisonnement
/npc spawn Nakasar_Giant_Pumpkin     # élite du champ de citrouilles : vrilles combattantes, poison, piège annoncé
/npc spawn Nakasar_Vampire_Hunter_Crossbow  # chasseurs de vampires (aussi _Gunner, _Blade) : neutres, ennemis des mobs du fragment
/give Nakasar_Prison_Cell            # bloc invisible : cellule où le capitaine envoie le joueur
/give Nakasar_Spawner_Vampire_Count  # bloc invisible qui fait (ré)apparaître le comte là où il est posé
```

Brèches des chasseurs de vampires (monde principal, toutes les 30 min, la nuit). Le monde doit autoriser les
évènements de monde et l'apparition des PNJ, sinon le camp reste vide (vu en jeu le 2026-10-18) :

```text
/time midnight                                       # les brèches ne s'ouvrent que la nuit
/worldevent start asset Nakasar_Hunter_Breach_Test   # ouvre tout de suite un campement près de vous, une fois
/worldevent list                                     # l'évènement Nakasar_Hunter_Breach et son étape en cours
```

Voie des chasseurs (trophées, contrats, sacs de prime, argent infusé) :

```text
/give Nakasar_Hunter_Workbench       # l'établi des chasseurs (3 niveaux, améliorés par des trophées précis)
/give Nakasar_Trophy_Vampire_Fang 10 # crocs (aussi _Abomination_Heart, _Captain_Insignia, _Pumpkin_Seed)
/give Nakasar_Bounty_Bag_Farm       # sac de prime, clic droit pour l'ouvrir (aussi _Pumpkin, _Garrison)
/give Nakasar_Contract_Farm          # contrat, à poser dans un Portal_Device (aussi _Pumpkin, _Garrison)
/instances spawn Nakasar_Contract_Farm   # ou ouvrir le mini-fragment directement
/give Weapon_Nakasar_Longsword_Infused   # armes en argent infusé : Weapon_Nakasar_*_Infused
```

### Recettes

- **Autel sacrificiel** (`Nakasar_Sacrificial_Altar`) : à l'atelier de base (`Workbench`, onglet
  `Workbench_Crafting`, palier 1) avec 10 pierres (ressource `Rock`), 2 lingots de fer et 1 éclat de rune.
  Une fois posé, un clic d'utilisation ouvre son interface de craft.
- **Runes** : chaque rune du mod coûte **2 éclats de rune** (`Ingredient_Rune_Shard`) sur l'autel, comme les
  runes de capacités du jeu.
- **Lance** : à l'établi de forgeron de base (`Weapon_Bench`, onglet « Épées » `Weapon_Sword`, palier 1 ; il n'y a
  pas d'onglet lance) avec 4 lingots de fer, 2 bûches (ressource `Wood_Trunk`) et 2 cuirs légers.

- **Armes en argent** : au `Weapon_Bench` (onglets Épées, Massues, Haches de combat, Dagues et Arcs), avec des
  lingots d'argent vanilla (`Ingredient_Bar_Silver`) à la place des lingots de fer de l'arme en fer. Flèches en
  argent : 8 flèches grossières + 1 lingot d'argent donnent 8 flèches en argent. Liste et recettes dans
  `mods/nakasar-vampires/tools/generate_silver_weapons.py`.

Les recettes (sauf celles des armes en argent, voir plus bas) sont des fichiers séparés (`Server/Item/Recipes/Nakasar/`), `KnowledgeRequired: false` (visibles sans
avoir été apprises). Séparées plutôt qu'inline dans les objets : le serveur valide chaque `ItemId` d'ingrédient et
rejette l'asset entier en cas d'id inconnu, donc un id d'ingrédient faux ne fait perdre que la recette, pas la rune.

Les armes en argent héritent (`Parent`) de l'arme en fer : elles portent donc leur recette dans l'objet, sinon elles
hériteraient de la recette en fer. Elles sont générées par `tools/generate_silver_weapons.py` (à relancer avec le
chemin de l'`Assets.zip` du jeu : il y lit les textures et icônes en fer à repeindre en argent).

Les runes se lancent avec les touches d'abilities (Ability2 / Ability3) en tenant une arme. La lance :
clic pour l'enchaînement, maintenir le clic (~0,8 s) pour le coup circulaire, touche Ability1 quand la
jauge de signature est pleine pour l'ultime.

## Points à vérifier en jeu (non vérifiables hors jeu)

Les assets client (modèles, animations, icônes) ne sont pas dans le jar serveur, donc quelques ids sont
repris de la documentation communautaire sans avoir pu être contrôlés :

- **Animations de la lance** : les ids `SwingLeft`, `SwingRight`, `SwingDown` existent sur les rigs
  standards mais pas forcément sur le rig `Spear`. Si un coup ne joue pas d'animation, remplacer l'id
  dans `Nakasar_Spear_Swing_*.json` / `Nakasar_Spear_Thrust.json`.
- **Modèle / icône de la lance** : `Items/Weapons/Spear/Iron.blockymodel` et
  `Icons/ItemsGenerated/Weapon_Spear_Iron.png` sont les chemins de la lance vanilla. Un modèle dédié
  pourra être ajouté ensuite dans le pack.
- **Visuel des runes** : les 4 runes réutilisent l'icône et la texture de `Rune_Fireball`.
- **Particules des runes** (chaînes vertes, gouttes de sang) : le format est celui du serveur 0.7.2 (décodé
  sans erreur par ses codecs), mais l'unité de `Scale` n'est pas documentée. Si les chaînes sont trop
  grandes ou trop petites, ajuster `InitialAnimationFrame.Scale` dans
  `Server/Particles/Nakasar/Nakasar_Spectral_Chain_Rise.particlespawner` (idem `Nakasar_Blood_Drain`).
  La hauteur de départ (sous le sol) est le `PositionOffset.Y` du `.particlesystem`.
- **Ruée de l'ultime** (`Nakasar_Spear_Signature_Dash.json`) : poussée continue de 0,55 s (`Duration`)
  lancée en parallèle des estocs. `Z: -1` doit pousser vers l'avant ; inverser le signe si le joueur
  recule. Régler la distance avec `Force` (vitesse) et `Duration`.
- **Identifiants vanilla** : `Weapon_Bench` / `Weapon_Sword`, `Workbench` / `Workbench_Crafting`,
  `Ingredient_Bar_Iron`, `Ingredient_Leather_Light`, ressources `Rock` et `Wood_Trunk`, `PlayerAnimationsId: Block`,
  `BlockSoundSetId: Stone`, `BlockParticleSetId: Stone`, `ISS_Blocks_Wood`, `GatherType: Benches` et
  `Furniture.Benches` sont lus dans `Server/Item/Items/Bench/Bench_Weapon.json` des assets 0.7.2 du jeu ;
  `Ingredient_Rune_Shard` existe (`Server/Item/Items/Ingredient/Goblin/Ingredient_Rune_Shard.json`).
  Restent non vérifiés : `BlockBreakingDecalId: Breaking_Decals_Rock` et les sons `SFX_Workbench_Open` /
  `SFX_Workbench_Craft` (documentation communautaire). Le serveur valide ces ids au
  chargement : un id inconnu rejette l'asset entier et le journal le nomme.
- **Modèle de l'autel** : modèle, texture, hitbox et icône sont générés par
  `mods/nakasar-vampires/tools/generate_altar.py` (format JSON du plugin Blockbench officiel, 32 unités = 1 bloc).
  À vérifier en jeu : l'autel occupe 2×2×1 blocs (large × haut × profond) et doit se poser avec ses blocs de
  remplissage ; le sens des pièces pivotées (`orientation`), le côté « avant » (crâne et dague d'un côté de la
  dalle) et le cadrage de l'icône 3D (`IconProperties`, repris de l'établi d'alchimie). Si le rendu ou les UV
  sont faux, ouvrir le `.blockymodel` dans Blockbench avec le plugin Hytale, ou corriger le script et le
  relancer.
- **Établi des chasseurs** (`tools/generate_hunter_bench.py`) : à vérifier en jeu, le bouton d'amélioration vers
  le niveau 2 et son coût, `BlockParticleSetId: Wood` (id supposé), le cadrage de l'icône, et pour les runes :
  la lumière portée par l'Aura (copie de la torche), le rendu des particules autour du lanceur, la disparition du
  lanceur invisible pour les autres joueurs et le retour à la normale quand il bouge, frappe ou se déconnecte.

Fragment Halloween :

- **Ids des PNJ** : `Skeleton`, `Skeleton_Archer`, `Skeleton_Soldier`, `Skeleton_Archmage`,
  `Skeleton_Elite`, `Zombie`, `Zombie_Aberrant`, `Spider`, `Spider_Cave`, `Ghoul`, `Wraith`,
  `Werewolf`, `Bat`, `Crow` viennent du wiki. `/npc spawn` sans argument liste les vrais ids : corriger
  `NPC/Spawn/World/Nakasar_Halloween_*.json` si l'un manque.
- **Clé de fragment** : elle hérite de `PortalKey_Taiga` (modèle, icône) et ne change que le texte et le
  type de portail.
- **Météo** : `Nakasar_Weather_Halloween` définit brouillard, ciel et lumière (violet / orange) mais
  pas de nuages, d'étoiles ni de texture de lune (chemins inconnus). La densité du brouillard
  (`FogDensities`, `FogDistance`) et la densité de spawn des environnements sont à régler à l'œil.
- **Prefabs** : orientation des meubles déduite des hitboxes et des villages du jeu (lacet 0 = sud) :
  à vérifier en jeu sur le village, la ferme et le poste de garde (portes, lits, chaises autour des
  tables, toits à 45°). Les troncs tombés utilisent les rotations 4 (nord-sud) et 5 (est-ouest) :
  s'ils apparaissent debout, inverser `ALONG_Z` et `ALONG_X` dans `generate_prefabs.py`.
- **Coffres** : remplis à la pose du prefab par le serveur (`ItemContainerBlock.Droplist`) ; si un
  coffre apparaît vide, vérifier que `IsBlockSpawnersEnabled` n'est pas désactivé dans la config du monde.
- **Arbres du jeu** : le worldgen pioche surtout dans les arbres vanilla (sapins et frênes morts,
  chênes moussus en forêt ; frênes tordus, calcinés, pétrifiés isolés), dossiers lus dans Assets.zip
  0.7.2 et listés dans `FOREST_TREES` et `LONE_TREES` (`generate_worldgen.py`). Un dossier renommé par une mise à jour ne place
  plus rien, sans erreur : vérifier cette liste après chaque mise à jour du jeu. Les châteaux et cryptes sont posés à plat grâce à un terrain aplani autour des structures.
- **Manoir et crypte d'arrivée** : les blocs générés par `tools/generate_assets.py` (vitraux,
  gargouille, grille à lances, vantail de portail) sont à vérifier en jeu : transparence des vitraux,
  sens des gargouilles (elles doivent regarder vers l'extérieur : sinon, corriger `FACING` dans
  `generate_prefabs.py`), grille alignée avec le muret, vantaux ouverts. On doit apparaître au centre
  de la crypte, portail de retour compris, la porte donnant au nord vers le manoir.
- **Liste des blocs** : `tools/vanilla-block-ids-0.7.2.txt` vient des fichiers du jeu publiés par
  hytale.isaacguru.com (ids d'objets qui ont un `BlockType`, états compris). Si un bloc récent manque,
  l'ajouter à la main ; si un bloc de la liste s'affiche en damier rose, le signaler pour l'en retirer.
- **Temps** : l'instance démarre à 20 h, avec des jours de 5 min et des nuits de 20 min.

Mobs (voir [docs/npc-0.7.2.md](docs/npc-0.7.2.md)) :

- **Apparence** : le Comte, la Comtesse et le rejeton sont des humanoïdes sur le squelette du joueur
  (vêtements du créateur de personnage recolorés, peau blafarde, yeux rouges) avec un col victorien dédié
  généré par `mods/nakasar-vampires/tools/generate_vampire_models.py`. À vérifier : place et orientation du
  col, couleurs des vêtements. Le fantôme reste sur le modèle vanilla `Wraith`.
- **Icônes d'effets** : Domination, Chaînes spectrales et Toucher glacial ont une icône dédiée
  (`Common/UI/StatusEffects/Nakasar/`) ; elle doit remplacer la croix rouge.
- **Attaques** : les animations (`SwingRight`, `SwingDown`) et le visé des sorts à distance (sélecteur
  `Stab` en ligne droite depuis le regard du PNJ, joueurs seulement) sont à confirmer.
- **Domination** : quand le comte vous fixe (teinte violette), vos coups ne doivent plus le blesser
  pendant 6 s ; ceux des autres joueurs, si.
- **Téléportation** : le comte et les fantômes doivent réapparaître face à leur cible.
- **Marqueurs du manoir** : le bloc invisible `Nakasar_Spawner_*` (composant `SpawnMarkerBlock`) n'a pas
  pu être décodé hors jeu. Si le boss n'apparaît pas au manoir, le poser à la main avec `/give`.
- **Densité** : poids des fantômes et rejetons dans l'environnement hanté à régler à l'œil.
- **Camps** : dans le fragment, aucun mob ne doit en attaquer un autre, et une flèche de squelette perdue ne doit
  plus blesser un zombie. Si un mob vanilla du fragment en attaque encore un autre, son id manque dans
  `NPC/Groups/Nakasar_Halloween_Faction.json` (le journal signale aussi les ids de ce groupe qui n'existent pas).
- **Domination sur un mob** (rune) : pendant l'effet, le mob visé doit se détourner de vous et attaquer les mobs
  du fragment à moins de 16 blocs, qui doivent riposter ; à la fin, il redevient hostile envers vous et cesse de
  frapper ses alliés. Les mobs du mod sont réglés pour ça ; pour les mobs vanilla (squelettes, zombies...), cela
  dépend de leurs rôles : s'ils restent passifs une fois dominés, il faudra leur donner un coup de pouce en Java.

- **Armes en argent** : contre le Comte, la Comtesse ou un rejeton, un coup doit faire environ le double des dégâts
  de la même arme en fer (le bonus vient de `SilverDamageSystem`, qui lit le tag `Material: Silver` de l'arme tenue).
  Flèches en argent : tout arc ou arbalète (vanilla compris), en mode Aventure, doit les tirer avant les flèches
  simples ; relâcher l'arc sans tirer ou changer d'objet arbalète chargée doit rendre les mêmes flèches (argent ou
  simples). Au chargement, le journal ne doit pas signaler d'erreur sur `Nakasar_TakeArrow` / `Nakasar_ReturnArrow`. Teinte des textures repeintes à juger à l'œil.

- **Brèches** : au démarrage du monde principal, la carte doit afficher « Brèche des chasseurs : prochaine dans
  30:00 ». La nuit, un message prévient, puis un campement s'ouvre à 48–160 blocs d'un joueur, avec titre, son
  et épingle sur la carte et la boussole (icône `Nakasar_HunterBreach.png`). À vérifier : que la faille est bien
  rouge (copies rouges des particules de la brèche gobeline), que la traverser mène dans la crypte d'un Comté Vampire
  et que son portail de retour ramène devant l'arche, que le campement est posé au ras du sol et tourné dans tous les
  sens sans chasseur dans un mur, que les chasseurs ne vous attaquent pas mais ripostent, et qu'à la fermeture
  (10 min) le terrain revient et les chasseurs disparaissent. Si rien ne démarre, chercher `Nakasar_Hunter_Breach`
  et `Nakasar_NightCondition` dans le journal.
- **Citrouille géante et vrilles** (`tools/generate_pumpkin_models.py`) : premiers modèles animés écrits à la main
  (sans Blockbench). À vérifier : sens des rotations (la vrille doit se pencher vers sa cible pour le coup normal,
  le haut de la citrouille se soulever par l'avant), yeux et bouche lumineux (plaque `*_Glow` transparente hors des
  découpes), animations d'attaque jouées par `ItemAnimationId` (`Server/Item/Animations/Nakasar/`). Si un sens est
  inversé, changer le signe dans la pose de l'animation concernée et relancer le script.
- **Joueur vampire** (`vampirism/`, `tools/generate_occult.py`) : améliorer l'autel au niveau 3, fabriquer le
  calice et le boire près de l'autel. Lu dans Assets.zip 0.7.2 : en survie, la vie ne remonte que par les effets des
  repas (`Server/Entity/Effects/Food`, préfixes `Food_`, `FruitVeggie_Buff_`, `HealthRegen_Buff_`, `Meat_Buff_`,
  retirés au vampire ; les soins instantanés `Food_Health_Restore_*` peuvent passer avant), les paliers de soif
  reprennent leurs débits, et les potions boivent comme `Potion_Template`. À vérifier : la brûlure au soleil cesse
  sous un toit et pendant l'orage (ids de météo reconnus par mots-clés dans `SunExposure`), l'éblouissement
  (`ScreenEffects/Nakasar/Sun_Glare.png`), la lumière de nuit visible du seul vampire (envoyée à son seul client par
  `PrivateNightLightSystem`, invisible des autres joueurs, renvoyée toutes les 2 s), le battement de cœur quand affamé,
  l'état gardé après reconnexion, la capuche et le voile portés. Le malus de vitesse d'attaque réduit les dégâts
  des coups trop rapprochés (le serveur ne peut pas ralentir l'animation).

- **Voie des chasseurs** (`tools/generate_trophies.py`, `generate_contracts.py`, `generate_infused_weapons.py`) :
  modèles des trophées et sacs de prime écrits comme l'autel (format `prop`, 32 unités = 1 bloc), à vérifier en main et au
  sol (taille, à corriger avec `Scale` dans l'objet). L'amélioration de l'établi doit demander le cœur d'Abomination
  puis la graine et l'insigne. Les contrats doivent ouvrir une petite île de nuit : crypte d'arrivée au centre avec le
  portail de retour, lieu de la cible au nord (vérifier que la cible apparaît, `IsSpawningNPC` est à vrai). Tuer la
  cible doit lâcher un seul sac de prime avec le message « Contrat rempli », et le clic droit
  (`Nakasar_OpenBountyBag`) doit l'ouvrir ; sinon chercher une erreur
  de `ContractBounties` dans le journal (ressource `PortalWorld` du fragment). Argent infusé : teinte dorée et dégâts
  ×2,5 contre les vampires, ×1,5 contre les zombies et squelettes.

- **Tour de l'Alchimiste, socle** (`tools/generate_alchemist_tower.py`, `tower/TowerFallSystem.java`) : la clé se
  fabrique à l'établi des chasseurs niveau 3 et à l'autel niveau 3 (éclats de rune, essences du vide et élémentaires).
  L'instance ouvre de nuit (19 h figée, ciel violet), sans limite de temps ni d'entrées (`AllowedEntryCount` 0 comme
  Deepworks), blocs non modifiables. Vérifié en jeu : confirmation du portail de sortie `Nakasar_Tower_Exit`, retour
  au parvis après une chute. À vérifier : les anneaux de fumée du portail, descendus au ras du socle par la copie de
  particules `Nakasar_Tower_Exit_Portal` (spawners `MagicPortal_VoidSmokeMiddle` et `MagicPortal_VoidGlowSmoke`).
- **Tour de l'Alchimiste, l'archipel et la tour** (`tools/alchemist_archipelago.py`, `tools/alchemist_tower.py`) :
  à l'échelle de Deepworks. Parcours : île d'arrivée, puis une chaîne de petites
  îles reliées par des ponts courts de style elfique (arches, lanternes, fleurs, lianes) : halte de la fontaine, halte
  du kiosque, Jardins des Alambics, halte des sources, Ruines du premier laboratoire (premier point de contrôle),
  halte des arches. La grande île de la tour (340 blocs de large) est couverte d'une forêt traversée par un chemin
  jusqu'au parvis. Le ciel est peuplé d'îlots, de géodes, de rochers et de cristaux flottants du jeu. La tour fait
  environ 67 blocs de diamètre et 220 de haut, posée en quatre tranches empilées (`Tower0` à `Tower3`), et ses salles
  sont meublées selon leur thème. Au-dessus des garde-corps qui bordent le vide (places, ponts, coursives et escaliers
  extérieurs de la tour), des volumes de repoussée comme les `Player_Pushback` de Deepworks
  (`Server/Instances/Nakasar_Alchemist_Tower/resources/TriggerVolumeData.json`) renvoient le joueur vers l'intérieur.
  Vérifié hors ligne : parcours continu de l'arrivée au parvis sans accès au vide, chaque salle et chaque point de
  contrôle de la tour atteignables. À vérifier en jeu : que les grands prefabs se posent entiers et que les tranches
  s'emboîtent, que le monde d'instance reprend bien les volumes de repoussée et qu'ils renvoient le joueur (y compris
  en grimpant), l'eau des fontaines (sources `Water_Source` dans les bassins et sur les vasques), les arbres et
  sous-bois du jeu dans la forêt, les géodes flottantes (prefabs `Geode_Floating` du jeu), les demi-dalles des rampes,
  l'orientation des statues de contrôle de Deepworks (elles s'allument, soignent et la précédente s'éteint), les
  émanations `Nakasar_Tower_Emanation_*`, et qu'on réapparaisse au dernier point de contrôle, après une mort comme après
  une chute.
- **Tour de l'Alchimiste, les mobs** (`tools/generate_tower_mobs.py`, placement dans `alchemist_tower.Tower.mobs`) :
  créatures de l'Alchimiste sur des modèles du jeu. Homoncules (petits zombies difformes, en groupe), golems de plomb
  (frappe au sol annoncée), fioles vivantes de poison et de feu (elles éclatent au contact après une zone rouge),
  apprentis en robe de mage verte (lancent des fioles), vrilles carnivores et Snapdragons dans la serre, élémentaires
  de feu, de glace, de foudre et de racine (esprits du jeu), golem de cristal instable en élite de la Salle des
  Transmutations (barre de boss) et gargouilles (chauve-souris de pierre) sur l'Escalier des vents. Ils lâchent les
  trois réactifs (Sel philosophal, Soufre ardent, Mercure vif) et les essences du jeu. L'instance reprend les réglages
  de Deepworks : mode Aventure, aucune perte d'objets à la mort, marqueurs d'apparition actifs. À vérifier en jeu : que
  les mobs apparaissent (marqueurs dans une instance), les animations empruntées (morsure, golem, lancer de l'apprenti,
  sort des esprits), la taille des fioles vivantes et de la gargouille, la tenue des apprentis.
  Petits groupes d'ennemis variés sur chaque île du parcours (`alchemist_archipelago.ISLAND_MOBS`). Cour de la tour :
  quatre gardiens d'airain (golem de pierre-feu du jeu teint en laiton, 520 PV, frappes lourdes et coup au sol annoncé)
  gardent les portes de la tour ; `tower/CourtGuardSystem` les fait tomber (volume `Court_Door`) quand les quatre sont
  morts. À vérifier en jeu : que les quatre morts sont bien comptées (le système voit le cadavre pendant l'animation de
  mort) et que les portes tombent.
- **Tour de l'Alchimiste, pièges et énigmes** (`tools/alchemist_traps.py`, blocs posés par
  `alchemist_tower.Tower.traps`) : volumes déclencheurs comme ceux de Deepworks, vérifiés hors ligne par ValidateAssets.
  Hall (dégagé autour du grand alambic) : rallumer les trois athanors (braseros éteints devant leurs fours) ; chaque
  athanor a sa couleur (rouge, bleu, vert : gemmes sur son estrade) et allume de cette couleur son tuyau de verre
  jusqu'à l'alambic, son tube, sa prise sur la colonne relais et sa prise sur le sceau du couloir ; les trois allument
  le conduit maître et la colonne relais, qui perce le plafond de verre sous le sceau, puis le sceau se dissout.
  Couloir : buses de gaz en laiton (`Nakasar_Tower_Gas_Nozzle`, droites et diagonales, tuyau luisant au-dessus) dans
  les deux murs ; elles crachent en cône à tour de rôle (mur intérieur puis mur extérieur, toutes les 3 s), chaque
  cône annoncé par trois cercles rouges et rempli d'un nuage taillé à leur rayon : on avance dans le couloir de
  sécurité de l'autre mur. Vanne au fond (derrière la porte ouest) : la fermer coupe les buses, éteint les tuyaux et
  ouvre un raccourci vers la rampe du hall. Les fuites du décor sont des émanations (`Nakasar_Tower_Emanation_Leak`)
  qu'on ne ramasse plus (le bloc vanilla avait une hitbox « Rubble » ramassable). Serre : cinq grands champignons
  violets animés (`Nakasar_Spore_Shroom`, texture pixel art à la Hytale) crachent leurs spores à tour de rôle tant
  qu'on est dans la serre : le champignon enfle en tremblant pendant que sa zone rouge se remplit (2 s), puis lâche un
  nuage (`Nakasar_Spore_Cloud_30`) exactement du rayon de la zone rouge, qui reste 3 s, ralentit et empoisonne.
  Bibliothèque : le brasero met le feu à la haie de ronces qui barre la rampe ; les livres ne tombent que pendant le
  combat du Codex (`ArenaGate` active le volume quand la barrière se lève, le coupe à la fin). Salle des
  Transmutations (ronde, arène du golem de cristal, `tower/TransmutationSystem.java`) : trois quadrants sur quatre sont
  actifs (Feu : flammes intenses ; Glace : blizzard ; Air : vents forts vers le mur ; Terre : pics de pierre), le
  quatrième est calme avec un effet léger (petits dégâts, ralentissement, vents légers, petits pics). Toutes les 16 s le
  calme change de quadrant : 5 s avant, le quadrant calme s'annonce (cercles rouges, son) et le nouveau devient calme,
  puis l'ancien s'active et fait apparaître ses esprits. La mort du golem éteint les quadrants et dissout le sceau de
  l'escalier en spirale vers le laboratoire. Les esprits qui passent sous le sol ou sortent de la salle sont ramenés
  (`tower/FlyerGuardSystem.java` pour tous les volants de la tour). Escalier des vents (s'éveille à la porte nord du laboratoire) : flammes qui balaient les
  marches, rafales qui plaquent contre le mur (jamais vers le vide), foudre sur des cercles annoncés. À vérifier en
  jeu : que l'usage des braseros et de la vanne déclenche bien les volumes (et que les blocs posés par PlaceBlock
  allument conduits et tubes), la conduite luisante qui passe à l'état éteint, la taille des zones rouges du gaz, les particules empruntées (taille, sens),
  les dégâts, le feu des ronces (Fluid_Fire) et le sceau qui se dissout, l'animation des champignons (repos, enflure,
  crachat) et l'épaisseur du nuage.
- **Tour de l'Alchimiste, attaques annoncées** (`tools/tower_warnings.py`) : toutes les attaques de zone de la tour
  (pièges, sorts des boss, coups au sol des mobs) s'annoncent par le même cercle rouge au sol dont le disque se remplit
  jusqu'au bord à l'instant du coup (`Nakasar_Warning_<dixièmes>`, une durée par système) ; les coups au sol des mobs
  durent au moins 1,6 s. À vérifier en jeu : la taille des cercles (même rayon que les annonces vanilla) et le
  remplissage.
- **Tour de l'Alchimiste, arènes des boss** (`tower/ArenaGate.java`, volumes `<boss>_Gate` dans
  `alchemist_traps.Traps.arena_gate`) : comme le Festin de Deepworks, la statue de sauvegarde est hors de l'arène (palier
  de la rampe de la serre devant la bibliothèque, Escalier des vents à la porte nord du laboratoire, antichambre de la
  terrasse ; la Salle des Transmutations n'en a plus). Un joueur vivant entre dans l'arène : la porte s'illumine en rouge et, 4 s plus tard, la barrière
  `Nakasar_Arena_Barrier` (champ de force cramoisi, visible) la ferme. Qui meurt revient à la statue et ne peut plus
  rejoindre le combat. Plus aucun joueur vivant dans l'arène : le boss se remet à zéro, puis la barrière s'abaisse et le
  groupe peut retenter ; le boss vaincu, elle s'abaisse pour de bon. À vérifier en jeu : la fermeture (et qu'elle ne
  coince personne dans la porte), la réouverture après la mort du groupe, les particules de la porte.
  Décor des arènes (`alchemist_tower.Tower.decor_*`) : les meubles muraux font face à l'intérieur
  (`wall_facing`), les statues des points de contrôle regardent l'endroit où le joueur s'arrête (`facing_to`), deux
  braseros encadrent chaque porte d'arène. Bibliothèque : doubles rayonnages alignés sur les axes, dos à dos face aux
  allées, marqueterie d'or reliant le centre aux trois pupitres, tables de lecture. Laboratoire : sol dégagé pour le
  combat, anneaux de pierre, conduits de cristal vert vers quatre alcôves d'alambics et trois alcôves d'établis, cuve
  d'acide vert (`Poison_Source`, comme les gobelins de Deepworks) et quatre bassins secondaires, plafond à caissons de
  la Salle des Transmutations en dessous. Terrasse : cercle de transmutation (triangle et carré inscrits), rosaces de
  cristal de la couleur de chaque pilier, socles d'or des fioles de soin, dalles fissurées sur les zones qui
  s'effondrent ; statues de l'antichambre symétriques, rien devant la porte. Vues : `/mnt/project-files/donjons/vues/
  9-arene-*.png`. À vérifier en jeu : l'orientation des rayonnages et des statues, la lisibilité des dalles fissurées.
- **Tour de l'Alchimiste, le Codex vivant** (`tools/generate_codex_models.py`, rôles dans `generate_tower_mobs.py`,
  zones dans `alchemist_traps.Traps.codex`, combat dans `tower/CodexSystem.java`) : boss de la bibliothèque, grimoire
  flottant (œil, fermoir d'or, chaînes brisées, runes) au centre de la rotonde entre trois pupitres, barre de boss.
  Nuée de pages dans un cône annoncé au sol ; toutes les 28 à 32 s il ouvre un chapitre : un livre apparaît sur un
  pupitre (feu, givre ou pluie de livres) et le détruire en 6 s étourdit le Codex 6 s (+50 % de dégâts subis), sinon
  le sort part sur des zones annoncées. Trois phases (titre à l'écran ; à 70 % et 40 % de vie une onde annoncée de 8
  blocs part de lui) : jets d'encre (ligne de six cercles rouges vers un joueur, l'encre court du Codex vers la cible,
  éclabousse, ralentit et laisse des flaques 4 s ; toutes les 10, 8 puis 6,5 s, deux jets en dernière phase),
  tourbillons de pages coupantes dès la phase 2 (`Nakasar_Codex_Page_Vortex`, 50 PV, annoncés au sol, poursuivent les
  joueurs, entaillent à 1,8 bloc, durent 22 s, au plus 4), en phase 3 deux chapitres à la fois (il faut détruire les
  deux livres pour l'étourdir, chaque livre restant lance son sort) et un pan de rayonnages qui s'effondre toutes les
  14 s (zones annoncées puis bloc d'éboulis `Nakasar_Codex_Rubble`). Groupe mort ou sorti de l'arène 8 s : éboulis,
  livres, tourbillons et flaques retirés, vie pleine, retour en phase 1. Sa mort dissout le sceau de la rampe vers la Salle des Transmutations ; trophée Fermoir du
  Codex (sans usage pour l'instant). À vérifier en jeu : le modèle et ses animations (Pages, Chapter, vol), le sens des
  marques du cône, l'apparition des livres sur les pupitres, l'étourdissement, les zones de sorts et d'éboulement, la
  remise à zéro et le sceau ; les titres de phase, l'encre (éclaboussure, flaque), le modèle du tourbillon et sa
  poursuite, l'équilibre des dégâts.
- **Tour de l'Alchimiste, la Chimère du laboratoire** (`tools/generate_dragon_models.py`, rôles dans
  `generate_tower_mobs.py`, arène dans `alchemist_tower.Tower.chimera`, acide dans `alchemist_traps.Traps.chimera`,
  combat dans `tower/ChimeraSystem.java`) : second mini-boss, un dragon qui ne vole pas (modèle et texture du dragon de
  feu vanilla, ailes repliées, animations Morsure/Coup/Queue générées), barre de boss. Morsure, coup au sol annoncé
  (5,5 blocs), fauchage de la queue annoncé (5 blocs, poison). Des zombies porteurs d'acide apparaissent près des quatre
  bassins secondaires (un toutes les 7 s, 5 s sous la moitié de sa vie, au plus 4), remplissent leur seau 2,5 s puis
  marchent vers la cuve centrale : s'ils y versent leur acide, la Chimère regagne 5 % de sa vie ; tués avant, pas de
  soin. La cuve crache de l'acide sur des cercles annoncés pendant tout le combat. Remise à zéro si le groupe meurt ou
  quitte le laboratoire 8 s. Sa mort dissout le sceau de la porte nord (vers l'Escalier des vents) ; trophée Cœur de
  chimère (sans usage pour l'instant). La barrière d'entrée est un couvercle horizontal sur le haut de l'escalier en
  spirale. À vérifier en jeu : les animations du dragon, le seau des zombies, leur marche vers la cuve, l'acide vert
  dans les bassins, la barrière d'entrée.
- **Tour de l'Alchimiste, l'Alchimiste** (`tools/generate_alchemist_models.py`, rôles dans `generate_tower_mobs.py`,
  arène dans `alchemist_tower.Tower.alchemist`, volumes dans `alchemist_traps.Traps.alchemist`, combat dans
  `tower/AlchemistSystem.java` et `tower/AlchemistFlaskInteraction.java`) : boss final, sur la terrasse de
  l'Observatoire. Grand et maigre (squelette du joueur, 1,14), robe de mage violette, chapeau à large bord, masque de
  cuir à bec et verres violets, tablier taché, ceinture de fioles lumineuses ; bâton de cristal ; barre de boss. Vie
  ×(1 + 0,55 par joueur de plus dans l'arène), ×1,5 si le levier de l'antichambre a été tiré avant le combat (mode
  difficile : fioles doublées, dégâts +25 %, plus d'homoncules, éléments plus rapides). Phase 1, Transmutation : coups
  de bâton et fioles des quatre éléments vers chaque joueur (zones annoncées, 2 s). Phase 2, Grand Œuvre (67 %) : trois
  pans du rebord s'effondrent (qui tombe revient au bord intérieur, blessé), il s'enferme dans l'athanor central,
  invulnérable, avec 4 homoncules (+2 par joueur de plus) ; le dernier tué, il ressort 30 s puis s'y renferme. Phase 3,
  Convergence (34 %) : quatre piliers (feu, givre, foudre, racines) ; il prend l'élément d'un pilier debout toutes les
  20 s (teinte de l'élément) et le fait tomber sur chaque joueur toutes les 5 s (flammes au sol, ralentissement,
  étourdissement, racines) ; les quatre détruits, il s'effondre 8 s (+50 % de dégâts subis). Fioles de soin sur six
  socles toutes les 40 s. Remise à zéro si le groupe meurt ou quitte l'arène 10 s (rebord reconstruit, levier
  déverrouillé). Sa mort dissout le sceau du bureau, donne à chaque joueur de l'instance une sacoche
  (`Nakasar_Alchemist_Bag`, `_Hard` en mode difficile) et lâche le Masque de l'Alchimiste (passage de l'établi des
  chasseurs au niveau 4). À vérifier en jeu : les pièces du masque et du tablier sur le squelette, la teinte des
  éléments, le levier, l'effondrement et la reconstruction du rebord, le retour après une chute, la sortie de
  l'athanor, les piliers, les fioles de soin, la vie selon le groupe.
- **Tour de l'Alchimiste, butin** (`tools/generate_alchemist_loot.py`, `tower/TakePhilosopherStoneInteraction.java`,
  `tower/ElementalLanternSystem.java`, `tower/AlchemistGlovesSystem.java`) : dans le bureau, la pierre philosophale
  repose sur un piédestal (`Nakasar_Philosopher_Pedestal_Stone`) ; chaque joueur prend la sienne une fois par
  instance et elle reste visible pour les autres. La pierre sert à passer l'autel sacrificiel au niveau 4 et au calice
  du rituel. Sacoches : principes et essences (plus en difficile), objet unique 15 % (40 % en difficile), lunettes
  cosmétiques 10 % en difficile seulement. Objets uniques : flasque sans fond (jamais vide, 90 s entre deux gorgées),
  gants de l'Alchimiste (fioles et bombes lancées ×1,4 plus vite), lanterne élémentaire (lumière qui change d'élément,
  en main ou en main secondaire). Potions de l'établi d'alchimie : grand élixir, garde élémentaire, breuvage de
  vif-argent. Deux coffres secrets (`Nakasar_Loot_Tower_Secret`) au fond de niches dans le mur extérieur : couloir des
  fuites et escalier du vent (`alchemist_tower.Tower.secrets`). À vérifier en jeu : le piédestal et la pierre, les
  sacoches à la mort du boss, la recharge de la flasque, la lumière de la lanterne, la portée des fioles avec les
  gants, les lunettes sur la tête, les potions, les niches secrètes.
- **Tour de l'Alchimiste, histoire** (`tools/generate_lore.py`, placement par `alchemist_tower.Tower.lore`) : le journal
  de l'Alchimiste en 7 pages réparties de la cour à l'antichambre, les ordres des chasseurs, la note de l'apprenti, et
  dans le bureau la supplique d'un chasseur et la lettre du Comte restée sans réponse. À vérifier en jeu : la lecture
  des notes posées au sol.

## Organisation du dépôt

```text
build.gradle.kts            # config commune : toolchain Java 25, dépendance serveur, validateJson, deployToServer, packMods
settings.gradle.kts         # dépôts Maven (Hytale), liste des mods
gradle.properties           # version serveur ciblée, identité des mods
mods/<mod>/                 # un sous-projet Gradle par mod
  src/main/java             # (plugin) code Java
  src/main/resources        # (plugin) manifest.json + Server/** (pack d'assets embarqué)
  pack/                     # (pack pur) manifest.json + Server/**
  tools/                    # générateurs (prefabs, worldgen, butin, modèles), validateurs hors jeu
                            # ValidateAssets.java (assets) et ValidateRoles.java (rôles PNJ)
docs/                       # notes de conception et d'API
```

### Skills Claude (`.claude/skills/`)

Sept skills de projet, chargées automatiquement par Claude Code dans ce dépôt :

| Skill | Sert à |
|---|---|
| `hytale-vanilla-research` | trouver comment vanilla fait une chose (Assets.zip, jar serveur décompilé, ids) avant de la coder |
| `hytale-mod-reuse` | retrouver et réutiliser les briques des deux mods (`scripts/index_code.py --grep MOT`) |
| `hytale-3d-assets` | modèles, textures, animations et icônes au style vanilla, avec aperçu rendu |
| `hytale-organic-decor` | décors naturels et crédibles ; aperçu iso + audit des prefabs (`scripts/render_prefab.py`) |
| `hytale-load-pitfalls` | vérifications avant push (`./gradlew check`, `scripts/lint_diff.py`) et catalogue des pièges de chargement |
| `hytale-encounter-design` | élites et boss lisibles (règles de lisibilité, échelle de groupe, récompenses) |
| `hytale-ingame-feedback` | traiter un retour de test en jeu, tenir à jour les points à vérifier, le wiki et la mémoire |

## Ajouter un mod

1. Créer `mods/<nom>` avec un `build.gradle.kts` (copier `nakasar-vampires` pour un plugin ; pour un pack pur,
   une tâche `Zip` sur un dossier `pack/`, voir l'historique de `mods/nakasar-spear`).
2. L'ajouter dans `settings.gradle.kts` (`include(":mods:<nom>")`).
3. Préfixer tous les ids d'assets par `Nakasar_` (ou `<Mod>_`) pour éviter les collisions avec le jeu.
