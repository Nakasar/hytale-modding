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
        };
    }
}
