package dev.nakasar.hytale.peuples.population;

import dev.nakasar.hytale.peuples.village.People;

import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Réserves de prénoms et de noms de famille par peuple, dans la voix des noms déjà en jeu (Mousseline, Épine,
 * Vieux-Nœud chez les Kweebecs). Les noms propres ne se traduisent pas.
 */
public final class Names {

    private static final Map<String, List<String>> GIVEN = Map.of(
            "Kweebec", List.of("Mousse", "Brindille", "Pousse", "Ronce", "Fougère", "Bourgeon", "Sève", "Glandine", "Trèfle",
                    "Liseron", "Aubépine", "Gui", "Noisette", "Pistil", "Lichen", "Bouleau", "Ortie", "Myrtille", "Rameau",
                    "Feuillette", "Pétale", "Écorce", "Sureau", "Cresson", "Primevère", "Pomme-de-Pin", "Chardon", "Vrille",
                    "Mûre", "Lierre", "Saule", "Tilleul", "Coquelicot", "Bruyère", "Camomille", "Marjolaine", "Sorbier",
                    "Églantine", "Germe", "Radicelle"),
            "Trork", List.of("Grokk", "Murga", "Brakka", "Zug", "Hrunn", "Ogga", "Krusk", "Bagra", "Torg", "Uzga", "Drekk",
                    "Gorza", "Skarr", "Mabba", "Thrug", "Rukka", "Vorg", "Hagga", "Krom", "Zarra", "Bolg", "Grisha", "Dunk",
                    "Ugla", "Rogg", "Snaga", "Kurz", "Muzga", "Harrg", "Tozza", "Grub", "Azga", "Brog", "Lurza", "Gnarr",
                    "Shagga", "Morg", "Yurza", "Krag", "Drubba"),
            "Feran", List.of("Sahir", "Nayla", "Kadir", "Zahra", "Tarik", "Amina", "Rahim", "Leyla", "Faris", "Samira",
                    "Malik", "Yasmin", "Idris", "Noor", "Zayd", "Rania", "Haris", "Soraya", "Anwar", "Dalila", "Karim",
                    "Inaya", "Jalil", "Safiya", "Nadir", "Lina", "Omar", "Hana", "Rafiq", "Selma", "Basil", "Ilham",
                    "Tamir", "Zaina", "Kamil", "Aziza", "Fadi", "Mira", "Sami", "Ayla"),
            "Renonce", List.of("Ingvar", "Sigrun", "Halvar", "Ylva", "Bjorn", "Astrid", "Leif", "Runa", "Eskil", "Solveig",
                    "Torvald", "Freya", "Gunnar", "Hilde", "Arne", "Ragna", "Sten", "Liv", "Ulf", "Embla", "Knut", "Sigrid",
                    "Orm", "Thyra", "Egil", "Inga", "Vidar", "Ase", "Rurik", "Gerd", "Hakon", "Brynja", "Skeggi", "Tove",
                    "Alrik", "Saga", "Folke", "Ylvi", "Geir", "Ragnhild"),
            "Slothian", List.of("Lumo", "Pallo", "Vellu", "Moki", "Suvi", "Tahvo", "Ulla", "Kaapo", "Nuppu", "Oiva",
                    "Helmi", "Raimo", "Sanni", "Veikko", "Aino", "Lempi", "Toivo", "Hilla", "Paavo", "Iiris", "Onni", "Kerttu",
                    "Ukko", "Saimi", "Eero", "Tyyne", "Vilho", "Aili", "Jalo", "Martta", "Usko", "Senja", "Teuvo", "Elli",
                    "Vieno", "Lyyli", "Armas", "Sointu", "Tapio", "Hely"));

    private static final Map<String, List<String>> FAMILY = Map.of(
            "Kweebec", List.of("des Racines-Hautes", "du Grand-Chêne", "de la Mousse-Douce", "des Sept-Feuilles",
                    "du Vieux-Tronc", "de la Source-Verte", "des Ronces", "du Sous-Bois", "de l'Écorce-Claire", "des Glands",
                    "du Saule-Pleureur", "de la Clairière", "des Fougeraies", "du Lierre-Haut", "de la Rosée", "des Bourgeons",
                    "du Tertre", "des Haies", "de la Vieille-Souche", "du Ruisseau"),
            "Trork", List.of("Croc-Fendu", "Poing-de-Pierre", "Os-Rongé", "Mâche-Fer", "Crâne-Dur", "Dent-Noire",
                    "Hurle-Loup", "Brise-Roc", "Sang-Rouge", "Peau-de-Sanglier", "Œil-Torve", "Grogne-Fort", "Tranche-Bois",
                    "Pied-Lourd", "Gueule-Large", "Corne-Cassée", "Mord-Boue", "Griffe-Sale", "Ventre-Creux", "Feu-de-Camp"),
            "Feran", List.of("al-Rimal", "ibn Sahra", "al-Wadi", "du Puits-Clair", "al-Naji", "des Dunes", "al-Qamar",
                    "de l'Oasis", "al-Riyah", "du Palmier", "ibn Nahar", "al-Sabr", "des Sables-Rouges", "al-Najm",
                    "du Vent-Chaud", "al-Hilal", "des Caravanes", "al-Bahr", "du Mirage", "al-Fajr"),
            "Renonce", List.of("Givrefer", "Blanchecombe", "Hautneige", "Ventaigre", "Pierrefroide", "Longhiver",
                    "Gelemer", "Brumeval", "Rudeglace", "Loupblanc", "Sombrefjord", "Grisecorne", "Fendgivre", "Rochenoire",
                    "Clairfrimas", "Durecôte", "Bisefroide", "Ourscendré", "Valglacé", "Hivernel"),
            "Slothian", List.of("Lent-Rêveur", "Mousse-Lente", "Feuille-Pendue", "Dort-Tard", "Branche-Basse",
                    "Pas-Feutré", "Brume-Douce", "Sieste-Longue", "Bâille-Tôt", "Racine-Molle", "Doux-Vide", "Nuit-Calme",
                    "Pierre-Tiède", "Vase-Paisible", "Écho-Lent", "Ombre-Lente", "Souffle-Bas", "Goutte-Lente",
                    "Rive-Sombre", "Mare-Tranquille"));

    private Names() {
    }

    private static List<String> pool(Map<String, List<String>> map, People people) {
        List<String> l = people == null ? null : map.get(people.id());
        return l == null ? map.get("Kweebec") : l;
    }

    /** Un prénom pas encore porté par un habitant vivant du village si possible. */
    public static String given(People people, Random random, PopulationState state) {
        List<String> pool = pool(GIVEN, people);
        for (int i = 0; i < 12; i++) {
            String n = pool.get(random.nextInt(pool.size()));
            boolean used = false;
            for (Inhabitant h : state.inhabitants) {
                if (h.alive() && n.equals(h.given)) {
                    used = true;
                    break;
                }
            }
            if (!used) {
                return n;
            }
        }
        return pool.get(random.nextInt(pool.size()));
    }

    /** Trois prénoms différents pour le choix du parrain. */
    public static String[] proposals(People people, Random random, PopulationState state) {
        String[] out = new String[3];
        for (int i = 0; i < 3; i++) {
            String n;
            int guard = 0;
            do {
                n = given(people, random, state);
            } while (guard++ < 20 && (n.equals(out[0]) || n.equals(out[1])));
            out[i] = n;
        }
        return out;
    }

    public static String family(People people, Random random) {
        List<String> pool = pool(FAMILY, people);
        return pool.get(random.nextInt(pool.size()));
    }
}
