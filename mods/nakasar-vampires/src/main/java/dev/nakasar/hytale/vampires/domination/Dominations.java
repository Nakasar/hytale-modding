package dev.nakasar.hytale.vampires.domination;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Qui domine qui : joueurs dominés par le Comte ({@code Nakasar_DominatePlayer}) comme PNJ dominés par la rune
 * ({@code Nakasar_Dominate}). Une victime n'a qu'un dominateur à la fois (la dernière domination remplace la
 * précédente).
 *
 * <p>Une domination finie n'est plus lue comme active, mais reste dans la table jusqu'au passage de
 * {@link DominationExpirySystem}, qui rend alors le PNJ libéré à son camp.
 */
public final class Dominations {

    private record Entry(Ref<EntityStore> dominator, long expiresAtNanos) {
        boolean active(long now) {
            return now - expiresAtNanos < 0 && dominator.isValid();
        }
    }

    private static final Map<Ref<EntityStore>, Entry> BY_VICTIM = new ConcurrentHashMap<>();

    private Dominations() {
    }

    public static void dominate(Ref<EntityStore> victim, Ref<EntityStore> dominator, float seconds) {
        // Purge les victimes disparues (joueurs partis, mondes déchargés) pour ne pas retenir leurs Ref.
        BY_VICTIM.keySet().removeIf(ref -> !ref.isValid());
        BY_VICTIM.put(victim, new Entry(dominator, System.nanoTime() + (long) (seconds * 1_000_000_000L)));
    }

    /** Le dominateur actuel de {@code victim}, ou {@code null} si elle n'est pas dominée en ce moment. */
    public static Ref<EntityStore> dominatorOf(Ref<EntityStore> victim) {
        if (victim == null || BY_VICTIM.isEmpty()) {
            return null;
        }
        Entry entry = BY_VICTIM.get(victim);
        return entry != null && victim.isValid() && entry.active(System.nanoTime()) ? entry.dominator() : null;
    }

    /** Vrai si {@code attacker} est dominé par {@code target} en ce moment. */
    public static boolean isDominatedBy(Ref<EntityStore> attacker, Ref<EntityStore> target) {
        Ref<EntityStore> dominator = dominatorOf(attacker);
        return dominator != null && dominator.equals(target);
    }

    /** Retire de la table les dominations finies des victimes de {@code store} et renvoie ces victimes. */
    static List<Ref<EntityStore>> drainExpired(Store<EntityStore> store) {
        if (BY_VICTIM.isEmpty()) {
            return List.of();
        }
        long now = System.nanoTime();
        List<Ref<EntityStore>> expired = new ArrayList<>();
        BY_VICTIM.forEach((victim, entry) -> {
            if (!victim.isValid()) {
                BY_VICTIM.remove(victim, entry);
            } else if (victim.getStore() == store && !entry.active(now) && BY_VICTIM.remove(victim, entry)) {
                expired.add(victim);
            }
        });
        return expired;
    }

    public static void clearAll() {
        BY_VICTIM.clear();
    }
}
