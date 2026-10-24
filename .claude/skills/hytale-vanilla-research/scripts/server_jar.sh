#!/usr/bin/env bash
# Fouille du jar serveur Hytale (com.hypixel.hytale:Server, compileOnly des mods) : classes, signatures, sources décompilées.
#
#   .claude/skills/hytale-vanilla-research/scripts/server_jar.sh path                 # chemin du jar (le télécharge via Gradle si absent)
#   .claude/skills/hytale-vanilla-research/scripts/server_jar.sh find REGEX           # classes dont le nom complet correspond
#   .claude/skills/hytale-vanilla-research/scripts/server_jar.sh javap CLASSE         # signatures publiques et privées (-p)
#   .claude/skills/hytale-vanilla-research/scripts/server_jar.sh decompile CLASSE     # source Java (Vineflower), dans $OUT/src
#   .claude/skills/hytale-vanilla-research/scripts/server_jar.sh grep REGEX [PAQUET]  # cherche REGEX dans les sources décompilées d'un paquet
#
# CLASSE = nom complet avec des points (com.hypixel.hytale.server.npc.…) ; `find` le donne.
# Version : gradle.properties (hytale_version). Décompilation dans $OUT (défaut : /tmp/hytale-server-src), hors du dépôt.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
VERSION="$(sed -n 's/^hytale_version=//p' "$ROOT/gradle.properties" 2>/dev/null || true)"
VERSION="${VERSION:-0.7.2}"
OUT="${OUT:-/tmp/hytale-server-src}"
VINEFLOWER_VERSION=1.10.1

jar_path() {
  local j
  j="$(find "${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2" -name "Server-$VERSION.jar" 2>/dev/null | head -1 || true)"
  if [[ -z "$j" ]]; then
    (cd "$ROOT" && ./gradlew -q :mods:nakasar-vampires:dependencies --configuration hytaleServer >/dev/null 2>&1 || true)
    (cd "$ROOT" && ./gradlew -q :mods:nakasar-vampires:validateRoles >/dev/null 2>&1 || true)
    j="$(find "${GRADLE_USER_HOME:-$HOME/.gradle}/caches/modules-2" -name "Server-$VERSION.jar" 2>/dev/null | head -1 || true)"
  fi
  [[ -n "$j" ]] || { echo "Server-$VERSION.jar introuvable (réseau vers maven.hytale.com ?)" >&2; exit 1; }
  echo "$j"
}

vineflower() {
  local v="$OUT/vineflower-$VINEFLOWER_VERSION.jar"
  if [[ ! -f "$v" ]]; then
    mkdir -p "$OUT"
    curl -fsSL -o "$v" "https://repo1.maven.org/maven2/org/vineflower/vineflower/$VINEFLOWER_VERSION/vineflower-$VINEFLOWER_VERSION.jar"
  fi
  echo "$v"
}

cmd="${1:-path}"; shift || true
case "$cmd" in
  path) jar_path ;;
  find) unzip -Z1 "$(jar_path)" | grep '\.class$' | grep -v '\$' | sed 's/\.class$//; s#/#.#g' | grep -E "${1:?REGEX}" | head -200 ;;
  javap) javap -p -cp "$(jar_path)" "${1:?CLASSE}" ;;
  decompile)
    cls="${1:?CLASSE}"; path="${cls//.//}"
    mkdir -p "$OUT/classes" "$OUT/src"
    (cd "$OUT/classes" && unzip -oq "$(jar_path)" "$path.class" "$path\$*.class" 2>/dev/null || unzip -oq "$(jar_path)" "$path.class")
    java -jar "$(vineflower)" -log=ERROR "$OUT/classes/$path.class" "$OUT/src/$(dirname "$path")/" >/dev/null
    echo "$OUT/src/$path.java" ;;
  grep)
    rx="${1:?REGEX}"; pkg="${2:-com.hypixel.hytale}"; dir="${pkg//.//}"
    if [[ ! -d "$OUT/pkg/$dir" ]]; then
      mkdir -p "$OUT/pkgjar" "$OUT/pkg"
      (cd "$OUT/pkgjar" && unzip -oq "$(jar_path)" "$dir/*")
      java -jar "$(vineflower)" -log=ERROR "$OUT/pkgjar/$dir" "$OUT/pkg/$dir" >/dev/null
    fi
    grep -rnE "$rx" "$OUT/pkg/$dir" | head -100 ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
