package dev.nakasar.hytale.fractals.moltenboss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Ondes de choc du Boss en fusion : un anneau qui s'élargit de {@link MoltenBossLayout#SHOCK_SPEED} blocs par seconde.
 * L'onde blanche court au sol (on la saute : touché si on a les pieds au sol dans l'anneau) ; l'onde bleue court à
 * {@link MoltenBossLayout#AIR_RING_HEIGHT} blocs de haut (on reste au sol : touché si on est en l'air dans l'anneau).
 * L'anneau dessiné et l'anneau qui frappe sont les mêmes (rayon, demi-épaisseur {@link MoltenBossLayout#SHOCK_BAND}).
 */
final class Shockwaves {

    enum Kind { GROUND, AIR }

    /** Recul d'un joueur touché : vitesse horizontale et verticale. */
    static final double KNOCK = 9;
    static final double KNOCK_UP = 6;

    private static final class Wave {
        final Vector3d center;
        final double max;
        final Kind kind;
        final float part;
        double radius;
        final Set<UUID> hit = new HashSet<>();

        Wave(Vector3d center, double max, Kind kind, float part) {
            this.center = center;
            this.max = max;
            this.kind = kind;
            this.part = part;
        }
    }

    private final List<Wave> waves = new ArrayList<>();

    void add(Vector3d center, double max, Kind kind, float part) {
        waves.add(new Wave(new Vector3d(center), max, kind, part));
    }

    void clear() {
        waves.clear();
    }

    void tick(World world, Store<EntityStore> store, float dt) {
        if (waves.isEmpty()) {
            return;
        }
        List<PlayerRef> players = Spawns.alivePlayers(world, store);
        for (int i = waves.size() - 1; i >= 0; i--) {
            Wave wv = waves.get(i);
            double before = wv.radius;
            wv.radius += MoltenBossLayout.SHOCK_SPEED * dt;
            if (wv.radius > wv.max) {
                waves.remove(i);
                continue;
            }
            boolean air = wv.kind == Kind.AIR;
            // Redessiné tous les 1,5 bloc de rayon, 48 points au plus : l'anneau reste lisible sans noyer le client.
            if ((int) (before / 1.5) != (int) (wv.radius / 1.5)) {
                int n = Math.min(48, Math.max(8, (int) (wv.radius * 2.5)));
                double y = wv.center.y() + (air ? MoltenBossLayout.AIR_RING_HEIGHT : 0);
                String id = air ? "Nakasar_Fractal_Molten_Ring_Air" : "Nakasar_Fractal_Molten_Ring_Ground";
                for (int k = 0; k < n; k++) {
                    double a = k * Math.PI * 2 / n;
                    Telegraphs.particle(store, id, new Vector3d(wv.center.x() + Math.cos(a) * wv.radius, y,
                            wv.center.z() + Math.sin(a) * wv.radius), 0.6f);
                }
            }
            for (PlayerRef p : players) {
                if (wv.hit.contains(p.getUuid())) {
                    continue;
                }
                Ref<EntityStore> ref = p.getReference();
                Vector3d at = Telegraphs.position(store, ref);
                if (at == null || Math.abs(at.y() - wv.center.y()) > 3 || Moves.onGround(store, ref) == air) {
                    continue;
                }
                double d = Telegraphs.horizontal(at, wv.center);
                if (Math.abs(d - wv.radius) <= MoltenBossLayout.SHOCK_BAND + Telegraphs.BODY) {
                    wv.hit.add(p.getUuid());
                    Hurt.percent(store, ref, wv.part, MoltenBoss.CAUSE);
                    double k = d < 1e-3 ? 0 : KNOCK / d;
                    Moves.velocity(store, ref, new Vector3d((at.x() - wv.center.x()) * k, KNOCK_UP,
                            (at.z() - wv.center.z()) * k));
                }
            }
        }
    }
}
