package dev.nakasar.hytale.fractals.arena;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

/**
 * Les PNJ ne tombent pas des plates-formes (Kevin, 25 octobre 2026 : Archidevin de la Falaise, monstres du Ressac
 * silencieux, dont la chute bloquait la progression). Appelé à chaque pas du Java : un PNJ sorti de sa plate-forme est
 * remis dessus aussitôt, avant d'avoir pu tomber bien loin.
 */
public final class Leash {

    private Leash() {
    }

    /**
     * Garde `ref` sur un disque de sol : centre `center` (y = niveau du sol), rayon `radius`. Sorti du disque ou plus de
     * `below` blocs sous le sol, il est ramené vers le centre, à `radius - margin` au plus, au niveau du sol.
     * Vrai s'il a été ramené.
     */
    public static boolean keepOnDisc(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d center, double radius,
                                     double margin, double below) {
        Vector3d at = Telegraphs.position(store, ref);
        if (at == null || store.getComponent(ref, Teleport.getComponentType()) != null) {
            return false;
        }
        double dx = at.x() - center.x();
        double dz = at.z() - center.z();
        double d = Math.sqrt(dx * dx + dz * dz);
        if (d <= radius && at.y() >= center.y() - below) {
            return false;
        }
        double keep = Math.min(d, Math.max(0, radius - margin));
        double k = d < 1e-6 ? 0 : keep / d;
        Vector3d back = new Vector3d(center.x() + dx * k, center.y(), center.z() + dz * k);
        put(store, ref, back, center);
        return true;
    }

    /** Ramène `ref` en `home` s'il est descendu de plus de `below` blocs sous lui. Vrai s'il a été ramené. */
    public static boolean keepAbove(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d home, double below) {
        Vector3d at = Telegraphs.position(store, ref);
        if (at == null || at.y() >= home.y() - below || store.getComponent(ref, Teleport.getComponentType()) != null) {
            return false;
        }
        put(store, ref, home, at);
        return true;
    }

    private static void put(Store<EntityStore> store, Ref<EntityStore> ref, Vector3d to, Vector3d face) {
        store.putComponent(ref, Teleport.getComponentType(),
                new Teleport(new Vector3d(to), new Rotation3f(0f, Telegraphs.yawToward(to, face), 0f)));
    }
}
