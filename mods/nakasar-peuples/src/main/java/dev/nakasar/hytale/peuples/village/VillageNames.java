package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.server.core.universe.world.World;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Noms des villages posés par le mod : une liste par peuple, tirée par le seed du monde, sans reprendre un nom déjà porté
 * par un village du monde.
 */
public final class VillageNames {

    private static final List<String> KWEEBEC = List.of(
            "Bosquet des Mousses",
            "Clairière de Sève-Douce",
            "Le Creux-aux-Glands",
            "Clos des Brindilles",
            "Ramée-Chantante",
            "Bosquet du Vieux-Chêne",
            "Les Pousses-Vertes",
            "Clairière des Lucioles",
            "Feuillée-Basse",
            "Le Nid-de-Ronces");

    /** Étape 7 : les camps trorks. */
    private static final List<String> TRORK = List.of(
            "Camp des Crocs-Brisés",
            "Foyer de la Viande-Crue",
            "Camp du Crâne-Fendu",
            "Les Tentes-Puantes",
            "Camp des Cogne-Dur",
            "Feu des Os-Rongés",
            "Camp de la Défense-Noire",
            "Bauge des Poings-Lourds");

    /** Étape 8 : oasis feran (formels, le vent et l'eau). */
    private static final List<String> FERAN = List.of(
            "Oasis du Vent-Clair",
            "Source des Dunes",
            "Halte de l'Eau-Douce",
            "Puits des Sept-Souffles",
            "Oasis de la Plume",
            "Bassin des Mirages",
            "Halte du Sable-Rouge",
            "Source des Longues-Dents");

    /** Étape 8 : hameau des Outlanders renoncés (méfiants, à l'écart du culte). */
    private static final List<String> RENONCE = List.of(
            "Le Refuge-du-Givre",
            "Hameau des Repentis",
            "Le Feu-Caché",
            "Les Cabanes-Muettes",
            "Abri du Col-Blanc",
            "Le Fort-des-Fuyards",
            "Hameau de la Glace-Noire",
            "La Halte-sans-Totem");

    /** Étape 9 : monastère et ermitages slothians (lents, la veille et la cendre). */
    private static final List<String> SLOTHIAN = List.of(
            "Monastère de la Veille-Lente",
            "Ermitage de la Cendre-Douce",
            "Monastère du Souffle-Long",
            "Refuge des Braises-Calmes",
            "Ermitage de la Mousse-Grise",
            "Monastère de la Faille-Endormie",
            "Halte du Pas-Paisible",
            "Ermitage du Brasero-Patient");

    private VillageNames() {
    }

    /** Nom libre pour un nouveau village du peuple dans ce monde. */
    public static String pick(World world, People people) {
        Set<String> used = Villages.registry(world).all().stream()
                .map(v -> v.name().toLowerCase(Locale.ROOT)).collect(Collectors.toSet());
        List<String> pool = new ArrayList<>(names(people));
        long seed = world.getWorldConfig().getSeed();
        java.util.Collections.shuffle(pool, new Random(seed * 131L + people.ordinal()));
        for (String name : pool) {
            if (!used.contains(name.toLowerCase(Locale.ROOT))) {
                return name;
            }
        }
        // Liste épuisée : on numérote.
        String base = pool.isEmpty() ? people.id() : pool.get(0);
        for (int i = 2; ; i++) {
            String name = base + " " + i;
            if (!used.contains(name.toLowerCase(Locale.ROOT))) {
                return name;
            }
        }
    }

    static List<String> names(People people) {
        return switch (people) {
            case KWEEBEC -> KWEEBEC;
            case TRORK -> TRORK;
            case FERAN -> FERAN;
            case RENONCE -> RENONCE;
            case SLOTHIAN -> SLOTHIAN;
        };
    }
}
