---
name: hytale-load-pitfalls
description: Éviter qu'un mod Hytale refuse de charger ou casse en jeu, et vérifier une branche avant de pousser — validateurs Gradle (validateJson, validateRoles, validateAssets), lint des pièges connus, catalogue des erreurs déjà rencontrées en 0.7.2 (dépendance REQUIRED, sons stéréo, drop inconnu, Despawn Force, enums, Fly seul, SystemDependency non enregistrée, durabilité…). À utiliser avant chaque commit/push/PR qui touche un mod, et dès que Kevin dit "le mod ne charge pas", "le monde plante", "rien n'apparaît", "damier rose", ou colle un log serveur/client, même si l'erreur semble sans rapport.
---

# Pièges de chargement et vérification avant push

Dans Hytale 0.7.2, une petite erreur d'asset ne casse presque jamais « juste cet asset » : un id inconnu fait
rejeter l'objet, qui fait rejeter le rôle qui le cite, qui fait échouer la validation des marqueurs… et le mod
entier ne charge plus ; une dépendance manquante dans le manifest empêche même vanilla de charger. Kevin ne le
découvre qu'en lançant le jeu, ce qui coûte un aller-retour complet. Presque chaque piège de la liste
ci-dessous a coûté une PR de correctif. Le but : **qu'aucun ne revienne**, et que chaque nouveau piège devienne
une vérification automatique.

## Avant chaque push

1. **Régénérer** ce que la branche a changé (les assets générés viennent des `tools/generate_*.py`) et vérifier
   que la régénération est stable : relancer une seconde fois ne doit rien changer (`git status`). Exception
   connue : `generate_alchemist_tower.py` réécrit `Tower0.prefab.json` de façon non déterministe → `git checkout`
   ce fichier après.
2. **Valider** :
   ```bash
   ./gradlew check          # validateJson + validateRoles + validateAssets de chaque mod (codecs du vrai serveur)
   ./gradlew build          # compile le Java, produit les jars
   ```
   `validateAssets` décode tous les assets avec les codecs serveur et vérifie les ids de blocs, gradients, drops,
   rôles, marqueurs et sons mono contre `tools/vanilla-*.txt`. `validateRoles` charge les rôles PNJ comme le
   serveur (briques inconnues, `Despawn Force`, une seule interaction `AimingReference` par chaîne d'attaque,
   contrôleur Walk requis…). Lire la sortie : un échec ici est un échec en jeu.
3. **Lint du diff** pour les pièges que les validateurs ne voient pas :
   ```bash
   python3 .claude/skills/hytale-load-pitfalls/scripts/lint_diff.py            # contre origin/main
   ```
   Une ERREUR se corrige ; un AVERTISSEMENT se lit et se justifie.
4. **`git diff --stat`** : aucune taille aberrante (un README est déjà passé à 56 000 lignes par un remplacement
   avec une chaîne vide).
5. **Points à vérifier en jeu** : tout ce qui n'est pas vérifiable hors jeu (id vanilla supposé, rotation, rendu,
   animation) est listé dans le README et dans la PR, avec quoi regarder et quoi changer si c'est faux.

## Quand Kevin signale que ça ne charge pas

1. Demander (ou relire) **le log** : client `%APPDATA%\Hytale\UserData\Logs`, ou serveur. La première erreur
   d'asset compte plus que la cascade qui suit.
2. Chercher le symptôme dans [references/catalogue.md](references/catalogue.md) : la plupart des symptômes y
   sont déjà (« GameplayConfig 'Default' doesn't exist » = dépendance REQUIRED manquante, damier rose = id de bloc
   inconnu, crash « Invalid entity reference » = Despawn Force…).
3. Si c'est nouveau : trouver la cause dans le jar (skill `hytale-vanilla-research`, `server_jar.sh decompile`
   sur la classe qui logge l'erreur), corriger, puis **rendre le piège impossible à refaire** : une vérification
   dans `ValidateAssets.java` / `ValidateRoles.java` (des deux mods), une règle dans `scripts/lint_diff.py`, ou à
   défaut une ligne dans le catalogue. Ajouter aussi une ligne dans la mémoire du projet.

## Règles de conception qui évitent les pièges

- Entre mods Nakasar : `OptionalDependencies` seulement, jamais `Dependencies`.
- Un asset fragile (recette avec un ingrédient vanilla, drop) dans son propre fichier : s'il est rejeté, il
  n'emporte pas l'objet avec lui.
- N'écrire dans `tools/vanilla-refs-0.7.2.txt` que des ids vus dans les fichiers du jeu ou en jeu.
- Entités temporaires (serviteurs, vrilles, marqueurs) : `NonSerialized` ou composants sans codec, et nettoyage
  au déchargement ; sinon l'état reste coincé après un redémarrage (élite invulnérable, joueur gelé).
- Systèmes ECS : ne jamais enregistrer deux instances de la même classe de système ; ne dépendre que de
  systèmes enregistrés.
