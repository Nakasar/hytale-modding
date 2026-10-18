package dev.nakasar.hytale.mobs.domination;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Qui domine qui : un joueur dominé ne peut plus blesser son dominateur jusqu'à l'expiration.
 * Un joueur n'a qu'un dominateur à la fois (la dernière domination remplace la précédente).
 */
public final class Dominations {

    private record Entry(Ref<EntityStore> dominator, long expiresAtNanos) {
    }

    private static final Map<Ref<EntityStore>, Entry> BY_VICTIM = new ConcurrentHashMap<>();

    private Dominations() {
    }

    public static void dominate(Ref<EntityStore> victim, Ref<EntityStore> dominator, float seconds) {
        long now = System.nanoTime();
        // Purge les dominations finies (joueurs partis, mondes déchargés) pour ne pas retenir leurs Ref.
        BY_VICTIM.entrySet().removeIf(e -> now - e.getValue().expiresAtNanos() >= 0
                || !e.getKey().isValid() || !e.getValue().dominator().isValid());
        BY_VICTIM.put(victim, new Entry(dominator, now + (long) (seconds * 1_000_000_000L)));
    }

    /** Vrai si {@code attacker} est dominé par {@code target} en ce moment. */
    public static boolean isDominatedBy(Ref<EntityStore> attacker, Ref<EntityStore> target) {
        Entry entry = BY_VICTIM.get(attacker);
        if (entry == null) {
            return false;
        }
        if (System.nanoTime() - entry.expiresAtNanos() >= 0 || !attacker.isValid() || !entry.dominator().isValid()) {
            BY_VICTIM.remove(attacker, entry);
            return false;
        }
        return entry.dominator().equals(target);
    }

    public static void clearAll() {
        BY_VICTIM.clear();
    }
}
