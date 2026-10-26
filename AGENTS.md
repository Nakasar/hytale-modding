# Consignes pour les agents

Ce dépôt contient les mods Hytale de Nakasar (`mods/nakasar-vampires`, `mods/nakasar-fractals`). La documentation est
rédigée en français.

## Règles permanentes (valables pour TOUS les mods)

Consignes de Kevin (25 octobre 2026), à respecter pour chaque mob, boss, élite, fractale ou zone, existants comme à venir :

1. **Les mobs ne se régénèrent JAMAIS hors combat ou quand ils sont invulnérables.**
   - La régénération vanilla des PNJ (`Server/Entity/Stats/Health.json`, condition `RegenHealth` : +5 % toutes les
     0,5 s après 15 s sans dégâts) est coupée par un `NoRegenSystem` dans chaque mod (`HealthRegenState` désactivé
     avant `NPCPlugin.NPCEntityRegenerateStatsSystem`).
   - Tout soin écrit en Java (régénération d'un boss, soigneurs, serviteurs) ne s'applique qu'en combat et jamais sous
     le composant `Invulnerable` (mod Vampires : `boss/RecentDamage.mayHeal`).
2. **Assets vanilla d'abord.** Avant de créer un bloc, un modèle 3D, une texture, une animation ou un monstre, chercher
   dans les assets vanilla du jeu (`Assets.zip`, listes `tools/vanilla-*-0.7.2.txt`) et réutiliser en priorité les
   assets et modèles existants. Un modèle généré n'est fait que si rien de vanilla ne convient.
3. **Les zones rouges d'alerte ont exactement la taille de la zone d'effet** (dégâts, poussée, effet, attaque) :
   même rayon pour un cercle, même largeur et longueur pour une ligne, même angle pour un cône, posées au niveau du
   sol où l'effet porte. La taille de l'alerte et celle du test de touche viennent de la même constante ; la seule
   marge admise est la demi-largeur du corps du joueur (`Telegraphs.BODY` = 0,3).
4. **Les zones d'annonce ennemies ont la couleur et l'opacité de celles du donjon Deepworks vanilla** (Kevin,
   26 octobre 2026 : rouge orangé léger, jamais blanc opaque) : rouge pur `#ff0000` en `BlendAdd`, contour à 0,5 qui
   pulse entre 1 et 0,25, remplissage à 0,75 qui pulse entre 1 et 0,5, couleur écrite sur chaque image clé. Les
   générateurs (`generate_warnings.py`, `tower_warnings.py`) portent ces valeurs ; `validateAssets` refuse tout émetteur
   d'un dossier `Warnings` ou à texture `Warning_*` qui s'en écarte. Seules les zones favorables listées dans
   `POSITIVE_ZONES` gardent une autre couleur.

## Vérifications

`./gradlew validateJson build` puis, par mod, `validateRoles` et `validateAssets`. Un id vanilla que le validateur ne
connaît pas s'ajoute dans `tools/vanilla-refs-0.7.2.txt`, uniquement après l'avoir vu dans les fichiers du jeu.
