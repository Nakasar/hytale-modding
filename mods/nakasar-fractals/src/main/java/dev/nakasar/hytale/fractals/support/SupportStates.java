package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * États posés par les runes et objets de soutien, lus par les systèmes ({@link SupportSteeringSystem},
 * {@link SupportDamageFilter}) : échéances en {@code System.nanoTime()}. Rien n'est sauvegardé ; une entité disparue est
 * oubliée au passage suivant.
 */
public final class SupportStates {

    /** Ralentissement d'un ennemi : part de vitesse retirée (0..1), jusqu'à `until`. */
    record Slow(float part, long until) {
    }

    /** Ennemi effrayé : fuit le point `from` jusqu'à `until`. */
    record Fear(Vector3d from, long until) {
    }

    /** Bannière plantée : bonus pour les joueurs à `radius` de `at`, jusqu'à `until`. */
    record Banner(Vector3d at, double radius, boolean might, long until) {
    }

    /** Ralentissements par ennemi et par source (le plus fort s'applique). */
    static final Map<Ref<EntityStore>, Map<String, Slow>> SLOWS = new ConcurrentHashMap<>();
    static final Map<Ref<EntityStore>, Fear> FEARS = new ConcurrentHashMap<>();
    /** Égide : le prochain coup direct d'un PNJ est annulé. */
    static final Map<Ref<EntityStore>, Long> AEGIS = new ConcurrentHashMap<>();
    /** Sursis : le premier de ces joueurs qui tomberait à 0 PV reste à 1 PV ; un seul par lancer (clé = lancer). */
    static final Map<Ref<EntityStore>, Reprieve> REPRIEVE = new ConcurrentHashMap<>();
    /** Invulnérabilité courte donnée par le Sursis. */
    static final Map<Ref<EntityStore>, Long> SPARED = new ConcurrentHashMap<>();
    /** Une bannière par monde (la dernière plantée remplace l'autre). */
    static final Map<World, Banner> BANNERS = new ConcurrentHashMap<>();

    /** Un lancer de Sursis : partagé par les joueurs couverts, consommé une fois. */
    static final class Reprieve {
        final long until;
        boolean used;

        Reprieve(long until) {
            this.until = until;
        }
    }

    private SupportStates() {
    }

    static void slow(Ref<EntityStore> ref, String source, float part, long until) {
        SLOWS.computeIfAbsent(ref, r -> new ConcurrentHashMap<>()).merge(source, new Slow(part, until),
                (a, b) -> new Slow(Math.max(a.part(), b.part()), Math.max(a.until(), b.until())));
    }

    /** Part de vitesse retirée à l'ennemi maintenant (0 : aucune). */
    static float slowOf(Ref<EntityStore> ref, long now) {
        Map<String, Slow> mine = SLOWS.get(ref);
        if (mine == null) {
            return 0f;
        }
        float best = 0f;
        for (var it = mine.entrySet().iterator(); it.hasNext(); ) {
            Slow s = it.next().getValue();
            if (now >= s.until()) {
                it.remove();
            } else {
                best = Math.max(best, s.part());
            }
        }
        if (mine.isEmpty()) {
            SLOWS.remove(ref);
        }
        return best;
    }

    static boolean active(Map<Ref<EntityStore>, Long> map, Ref<EntityStore> ref, long now) {
        Long until = map.get(ref);
        if (until == null) {
            return false;
        }
        if (now >= until) {
            map.remove(ref);
            return false;
        }
        return true;
    }

    /** Oublie les entités disparues (appelé de temps en temps par le système de pilotage). */
    static void prune() {
        SLOWS.keySet().removeIf(r -> !r.isValid());
        FEARS.keySet().removeIf(r -> !r.isValid());
        AEGIS.keySet().removeIf(r -> !r.isValid());
        REPRIEVE.keySet().removeIf(r -> !r.isValid());
        SPARED.keySet().removeIf(r -> !r.isValid());
    }

    public static void clearAll() {
        SLOWS.clear();
        FEARS.clear();
        AEGIS.clear();
        REPRIEVE.clear();
        SPARED.clear();
        BANNERS.clear();
    }
}
