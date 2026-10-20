package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Bouclier à compteur de coups (chaman imprégné du Volcanique : 40 coups ; porte de cellule du Capitaine dans le mod
 * Vampires) : tant qu'il tient, tous les dégâts sont annulés ; chaque coup d'un joueur en retire un, quelle que soit
 * sa force. À zéro, il tombe et le Java est prévenu. Lu par {@code stage.StageDamageFilter} ; affiché dans le nom de la
 * barre de boss ({@link #label}).
 */
public final class HitShield {

    public static final String PARTICLE = "Nakasar_Fractal_Shield_Glow";

    private static final class Shield {
        int hits;
        final int max;
        final Runnable onBroken;

        Shield(int hits, Runnable onBroken) {
            this.hits = hits;
            this.max = hits;
            this.onBroken = onBroken;
        }
    }

    private static final Map<Ref<EntityStore>, Shield> SHIELDS = Collections.synchronizedMap(new WeakHashMap<>());

    private HitShield() {
    }

    /** Lève un bouclier de `hits` coups sur `ref` ; `onBroken` est appelé sur le thread du monde quand il tombe. */
    public static void raise(Ref<EntityStore> ref, int hits, Runnable onBroken) {
        SHIELDS.put(ref, new Shield(Math.max(1, hits), onBroken));
    }

    public static void drop(Ref<EntityStore> ref) {
        SHIELDS.remove(ref);
    }

    /** Coups qui restent, -1 sans bouclier. */
    public static int hits(Ref<EntityStore> ref) {
        Shield shield = SHIELDS.get(ref);
        return shield == null ? -1 : shield.hits;
    }

    /** Texte de la barre de boss : coups restants (null sans bouclier). */
    public static String label(Ref<EntityStore> ref) {
        Shield shield = SHIELDS.get(ref);
        return shield == null ? null : "◆ " + shield.hits + "/" + shield.max;
    }

    /** Coup sur `victim` : vrai (et le coup annulé) si un bouclier l'arrête. */
    public static boolean absorb(World world, Store<EntityStore> store, Ref<EntityStore> victim, boolean byPlayer, Damage damage) {
        Shield shield = SHIELDS.get(victim);
        if (shield == null) {
            return false;
        }
        damage.setCancelled(true);
        if (!byPlayer) {
            return true;
        }
        shield.hits--;
        if (shield.hits % 5 == 0) {
            Vector3d at = Telegraphs.position(store, victim);
            if (at != null) {
                Telegraphs.particle(store, PARTICLE, new Vector3d(at).add(0, 1, 0), 1.6f);
            }
        }
        if (shield.hits <= 0) {
            SHIELDS.remove(victim);
            world.execute(shield.onBroken);
        }
        return true;
    }

    public static void clearAll() {
        SHIELDS.clear();
    }
}
