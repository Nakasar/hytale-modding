package dev.nakasar.hytale.peuples.population;

import java.util.List;
import java.util.Locale;

/**
 * Les six traits (un par habitant, tiré à la naissance, une fois sur deux celui d'un parent). Ils orientent la vocation
 * (mots du métier dans l'id du poste) et le volontariat en raid ; ils ne touchent jamais aux PV ni aux dégâts.
 */
public final class Traits {

    public static final String BRAVE = "brave";
    public static final String WORKER = "worker";
    public static final String CURIOUS = "curious";
    public static final String CAREFUL = "careful";
    public static final String GENEROUS = "generous";
    public static final String DREAMER = "dreamer";

    public static final List<String> ALL = List.of(BRAVE, WORKER, CURIOUS, CAREFUL, GENEROUS, DREAMER);

    private Traits() {
    }

    /** Mots des ids de poste qui vont avec le trait (vocation, troisième choix). */
    public static List<String> jobWords(String trait) {
        return switch (trait == null ? "" : trait) {
            case BRAVE -> List.of("guard", "watcher", "hunter", "warrior", "scout", "sentry");
            case WORKER -> List.of("builder", "mason", "smith", "miner", "lumber", "carpenter");
            case CURIOUS -> List.of("breeder", "fisher", "herb", "explorer", "trader", "keeper");
            case CAREFUL -> List.of("well", "keeper", "store", "gardener", "farmer", "weaver");
            case GENEROUS -> List.of("healer", "cook", "gardener", "baker", "shaman");
            case DREAMER -> List.of("elder", "sage", "singer", "priest", "shaman", "weaver");
            default -> List.of();
        };
    }

    public static boolean matches(String trait, String jobId) {
        String id = jobId == null ? "" : jobId.toLowerCase(Locale.ROOT);
        for (String w : jobWords(trait)) {
            if (id.contains(w)) {
                return true;
            }
        }
        return false;
    }
}
