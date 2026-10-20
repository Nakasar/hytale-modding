package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Annonces et coups des combats de la Tour de l'Alchimiste (Kevin, 20 octobre 2026 : « lisibilité d'abord »).
 *
 * <ul>
 *   <li>{@link #circle} : petit cercle rouge qui se remplit jusqu'au coup ({@code Nakasar_Warning_<dixièmes>},
 *   tools/tower_warnings.py).</li>
 *   <li>{@link Sweep} : cône (secteur) ou anneau rouge qui se charge d'un bord à l'autre, comme les cônes de Deepworks.
 *   Il est dessiné en pastilles rouges à plat ({@code Nakasar_Cone_<dixièmes>}), anneau après anneau au rythme de la
 *   charge ; chaque pastille reste jusqu'à l'instant du coup. Le contour ({@code Nakasar_Cone_Edge_<dixièmes>}) est posé
 *   dès le début, pour qu'on voie tout de suite la zone entière. Les pastilles sont placées en coordonnées du monde :
 *   aucune rotation de particule n'entre en jeu.</li>
 *   <li>Coups en part de la vie maximale, effets, projection, sons.</li>
 * </ul>
 *
 * <p>Une zone rouge annonce toujours un effet négatif ; les autres couleurs (tools/tower_fx.py) disent l'élément ou un
 * soin.
 */
final class TowerFx {

    static final float WARNING_SCALE = 0.68f;
    /** Durées des pastilles de cône (tools/tower_warnings.py, CONE_TENTHS). */
    private static final int CONE_MIN = 2;
    private static final int CONE_MAX = 60;
    private static final int WARNING_MIN = 5;
    private static final String CONE = "Nakasar_Cone_";
    private static final String CONE_EDGE = "Nakasar_Cone_Edge_";
    /** Écart entre deux pastilles, leur rayon, et l'écart des points du contour (blocs). */
    private static final double DOT_STEP = 2.0;
    private static final double DOT_RADIUS = 1.35;
    private static final double EDGE_STEP = 1.5;
    private static final double EDGE_RADIUS = 0.3;

    private TowerFx() {
    }

    /** Cercle rouge de `radius` blocs au sol en `at`, plein au bout de `seconds` (arrondi au dixième). */
    static void circle(Store<EntityStore> store, Vector3d at, double radius, float seconds) {
        int tenths = Math.max(WARNING_MIN, Math.round(seconds * 10));
        particle(store, "Nakasar_Warning_" + tenths, new Vector3d(at).add(0, 0.1, 0), (float) (WARNING_SCALE * radius));
    }

    static void particle(Store<EntityStore> store, String id, Vector3d at, float scale) {
        ParticleUtil.spawnParticleEffect(id, at, 0f, 0f, 0f, scale, 1f, store);
    }

    static void sound(Store<EntityStore> store, String id, Vector3d at) {
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, at.x(), at.y(), at.z(), store);
        }
    }

    /** Part `fraction` de la vie maximale de `ref`, cause `causeId`, signée `source`. */
    static void damage(Store<EntityStore> store, Ref<EntityStore> ref, String causeId, float fraction, String source) {
        DamageCause cause = DamageCause.getAssetMap().getAsset(causeId);
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (cause == null || health == null || fraction <= 0f) {
            return;
        }
        float amount = (float) Math.ceil(health.getMax() * fraction);
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(source), cause, amount));
    }

    static void effect(Store<EntityStore> store, Ref<EntityStore> ref, String id, float seconds) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(id);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Tour : effet '%s' introuvable", id);
            return;
        }
        if (effects != null) {
            effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
        }
    }

    /** Projette `ref` vers le haut (pic de pierre). */
    static void launch(Store<EntityStore> store, Ref<EntityStore> ref, double up) {
        Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
        if (velocity != null) {
            velocity.addInstruction(new Vector3d(0, up, 0), null, ChangeVelocityType.Set);
        }
    }

    /** Joueurs vivants dans le cylindre de rayon `radius` posé en `at` (de 1 bloc dessous à 3 blocs dessus). */
    static List<Ref<EntityStore>> playersIn(World world, Store<EntityStore> store, Vector3d at, double radius) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d position = position(store, ref);
            if (position == null) {
                continue;
            }
            double dy = position.y() - at.y();
            if (horizontal(position, at) <= radius && dy >= -1 && dy <= 3) {
                out.add(ref);
            }
        }
        return out;
    }

    /** Position d'une entité vivante (null si elle est morte ou disparue). */
    static Vector3d position(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return null;
        }
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        return transform == null ? null : transform.getPosition();
    }

    static double horizontal(Vector3d a, Vector3d b) {
        double dx = a.x() - b.x();
        double dz = a.z() - b.z();
        return Math.sqrt(dx * dx + dz * dz);
    }

    /** Angle horizontal de `p` vu de `center`, en radians (atan2(dz, dx), comme les secteurs de TowerLayout). */
    static double angle(Vector3d center, Vector3d p) {
        return Math.atan2(p.z() - center.z(), p.x() - center.x());
    }

    static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    /**
     * Cône ou anneau qui se charge en `seconds` secondes, du rayon `from` au rayon `to` (vers l'extérieur si from &lt;
     * to, vers le centre sinon), sur le secteur qui part de l'angle `start` et tourne de `span` radians (2π : anneau
     * complet). {@link #step} le dessine au fil de la charge ; {@link #contains} dit qui est dedans au moment du coup.
     */
    static final class Sweep {
        final Vector3d center;
        final double start;
        final double span;
        final double from;
        final double to;
        final long begin;
        final long end;
        private double drawn;
        private boolean edges;

        Sweep(Vector3d center, double start, double span, double from, double to, long now, float seconds) {
            this.center = new Vector3d(center);
            this.start = start;
            this.span = span;
            this.from = from;
            this.to = to;
            this.begin = now;
            this.end = now + seconds(seconds);
            this.drawn = 0;
        }

        /** Secteur en degrés (comme TowerLayout : atan2(dz, dx), de a0 à a1 dans le sens positif). */
        static Sweep arc(Vector3d center, double a0, double a1, double from, double to, long now, float seconds) {
            double span = ((a1 - a0) % 360 + 360) % 360;
            return new Sweep(center, Math.toRadians(a0), Math.toRadians(span == 0 ? 360 : span), from, to, now, seconds);
        }

        /** Pose le contour au premier appel, puis les anneaux que la charge a atteints. Vrai une fois le coup venu. */
        boolean step(Store<EntityStore> store, long now) {
            float left = (end - now) / 1e9f;
            if (!edges) {
                edges = true;
                drawEdges(store, left);
            }
            double length = Math.abs(to - from);
            double reached = length * Math.min(1.0, Math.max(0.0, (now - begin) / (double) (end - begin)));
            // Anneaux au milieu de chaque bande de DOT_STEP, du bord de départ au bord d'arrivée.
            while (drawn < length && drawn + DOT_STEP / 2 <= reached + 1e-6) {
                double r = from + Math.signum(to - from) * (drawn + DOT_STEP / 2);
                drawRing(store, Math.min(Math.max(r, Math.min(from, to)), Math.max(from, to)), CONE, DOT_STEP, DOT_RADIUS, left);
                drawn += DOT_STEP;
            }
            return now >= end;
        }

        boolean contains(Vector3d p) {
            double d = horizontal(p, center);
            if (d < Math.min(from, to) - 0.5 || d > Math.max(from, to) + 0.5) {
                return false;
            }
            if (span >= Math.PI * 2 - 1e-6) {
                return true;
            }
            double a = ((angle(center, p) - start) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
            return a <= span;
        }

        private void drawEdges(Store<EntityStore> store, float left) {
            double inner = Math.min(from, to);
            double outer = Math.max(from, to);
            drawRing(store, outer, CONE_EDGE, EDGE_STEP, EDGE_RADIUS, left);
            if (inner > 0.5) {
                drawRing(store, inner, CONE_EDGE, EDGE_STEP, EDGE_RADIUS, left);
            }
            if (span < Math.PI * 2 - 1e-6) {
                for (double side : new double[]{start, start + span}) {
                    for (double r = inner; r <= outer + 1e-6; r += EDGE_STEP) {
                        dot(store, side, r, CONE_EDGE, EDGE_RADIUS, left);
                    }
                }
            }
        }

        private void drawRing(Store<EntityStore> store, double r, String prefix, double step, double radius, float left) {
            int n = Math.max(1, (int) Math.ceil(Math.abs(span) * r / step));
            for (int k = 0; k < n; k++) {
                dot(store, start + span * (k + 0.5) / n, r, prefix, radius, left);
            }
        }

        private void dot(Store<EntityStore> store, double angle, double r, String prefix, double radius, float left) {
            int tenths = Math.min(CONE_MAX, Math.max(CONE_MIN, Math.round(left * 10)));
            Vector3d at = new Vector3d(center.x() + Math.cos(angle) * r, center.y() + 0.08, center.z() + Math.sin(angle) * r);
            particle(store, prefix + tenths, at, (float) (WARNING_SCALE * radius));
        }
    }
}
