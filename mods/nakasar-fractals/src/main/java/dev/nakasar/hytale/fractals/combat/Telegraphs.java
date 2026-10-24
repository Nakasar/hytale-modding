package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Annonces au sol des boss de fractales, copiées du mod Vampires (Tour de l'Alchimiste et élites du Comté, Kevin,
 * 20 octobre 2026 : « mêmes codes de cercles, cônes et lignes rouges que la Tour »). Une zone rouge a la taille exacte
 * du coup et se remplit pendant toute l'annonce ; le rouge est réservé aux effets négatifs.
 *
 * <ul>
 *   <li>{@link #circle} : cercle rouge qui se remplit jusqu'au coup ({@code Nakasar_Fractal_Warning_<dixièmes>},
 *   tools/generate_warnings.py) ; {@link Circle} est la même zone avec son test d'appartenance.</li>
 *   <li>{@link Cone} : secteur rouge qui se remplit depuis le lanceur, et {@link Strip} : rectangle rouge qui s'allonge
 *   depuis le lanceur (Kevin, 24 octobre 2026 : « une ligne droite en rectangle, un cône en cône, comme les Deepworks »).
 *   Une seule particule à plat chacun, tournée vers l'attaque comme celles du Gobliterator
 *   ({@code Nakasar_Fractal_Sector_<angle>_<dixièmes>}, {@code Nakasar_Fractal_Line_<rapport>_<dixièmes>}, formes
 *   disponibles dans {@link WarningShapes}).</li>
 * </ul>
 */
public final class Telegraphs {

    public static final float WARNING_SCALE = 0.68f;
    /** Durées des cercles (tools/generate_warnings.py, WARNING_TENTHS). */
    private static final int WARNING_MIN = 5;
    private static final int WARNING_MAX = 60;
    private static final String LINE = "Nakasar_Fractal_Line_";
    private static final String SECTOR = "Nakasar_Fractal_Sector_";
    /** Hauteur d'une zone : on est touché de 1,5 bloc sous son sol à 3,5 blocs au-dessus. */
    private static final double BELOW = 1.5;
    private static final double ABOVE = 3.5;

    private Telegraphs() {
    }

    /** Zone d'annonce au sol : dessinée au fil de la charge ; dit qui est dedans au moment du coup. */
    public interface Shape {
        /** Dessine ce que la charge a atteint. Vrai une fois le coup venu. */
        boolean step(ComponentAccessor<EntityStore> store, long now);

        boolean contains(Vector3d p);

        /** Point de référence de la zone (centre d'un cercle, sommet d'un cône, départ d'une ligne). */
        Vector3d origin();
    }

    /** Cercle rouge de `radius` blocs au sol en `at`, plein au bout de `seconds` (arrondi au dixième). */
    public static void circle(ComponentAccessor<EntityStore> store, Vector3d at, double radius, float seconds) {
        int tenths = Math.min(WARNING_MAX, Math.max(WARNING_MIN, Math.round(seconds * 10)));
        particle(store, "Nakasar_Fractal_Warning_" + tenths, new Vector3d(at).add(0, 0.1, 0), (float) (WARNING_SCALE * radius));
    }

    public static void particle(ComponentAccessor<EntityStore> store, String id, Vector3d at, float scale) {
        ParticleUtil.spawnParticleEffect(id, at, 0f, 0f, 0f, scale, 1f, store);
    }

    public static void sound(ComponentAccessor<EntityStore> store, String id, Vector3d at) {
        if (id == null || id.isBlank()) {
            return;
        }
        int index = SoundEvent.getAssetMap().getIndexOrDefault(id, -1);
        if (index >= 0) {
            SoundUtil.playSoundEvent3d(index, SoundCategory.SFX, at.x(), at.y(), at.z(), store);
        }
    }

    /** Position d'une entité vivante (null si elle est morte ou disparue). */
    public static Vector3d position(ComponentAccessor<EntityStore> store, Ref<EntityStore> ref) {
        if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return null;
        }
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        return transform == null ? null : transform.getPosition();
    }

    public static double horizontal(Vector3d a, Vector3d b) {
        double dx = a.x() - b.x();
        double dz = a.z() - b.z();
        return Math.sqrt(dx * dx + dz * dz);
    }

    /** Angle horizontal de `p` vu de `center`, en radians (atan2(dz, dx)). */
    public static double angle(Vector3d center, Vector3d p) {
        return Math.atan2(p.z() - center.z(), p.x() - center.x());
    }

    /** Lacet (radians) d'une entité tournée de `from` vers `to` : 0 regarde vers -Z, -π/2 vers +X. */
    public static float yawToward(Vector3d from, Vector3d to) {
        return (float) Math.atan2(-(to.x() - from.x()), -(to.z() - from.z()));
    }

    public static long seconds(float s) {
        return (long) (s * 1_000_000_000L);
    }

    private static boolean inHeight(Vector3d p, Vector3d ground) {
        double dy = p.y() - ground.y();
        return dy >= -BELOW && dy <= ABOVE;
    }

    /**
     * Pose à plat la forme `id` (ligne ou secteur) en `at`, son haut tourné vers `facing` (radians, atan2(dz, dx)) :
     * même lacet qu'une entité qui regarderait dans cette direction ({@link #yawToward}).
     */
    private static void shape(ComponentAccessor<EntityStore> store, String id, Vector3d at, double facing, float scale) {
        float yaw = (float) Math.atan2(-Math.cos(facing), -Math.sin(facing));
        ParticleUtil.spawnParticleEffect(id, new Vector3d(at).add(0, 0.08, 0), yaw, 0f, 0f, scale, 1f, store);
    }

    /** Durée de forme en dixièmes, bornée à celles qui existent. */
    private static int shapeTenths(float seconds) {
        return Math.min(WarningShapes.MAX_TENTHS, Math.max(WarningShapes.MIN_TENTHS, Math.round(seconds * 10)));
    }

    /** Valeur de `available` la plus proche de `wanted`. */
    private static int nearest(int[] available, int wanted) {
        int best = available[0];
        for (int v : available) {
            if (Math.abs(v - wanted) < Math.abs(best - wanted)) {
                best = v;
            }
        }
        return best;
    }

    /** Cercle rouge plein au bout de `seconds` : posé en une fois (le disque grandit tout seul). */
    public static final class Circle implements Shape {
        final Vector3d center;
        final double radius;
        final long end;
        private final float seconds;
        private boolean drawn;

        public Circle(Vector3d center, double radius, long now, float seconds) {
            this.center = new Vector3d(center);
            this.radius = radius;
            this.seconds = seconds;
            this.end = now + seconds(seconds);
        }

        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            if (!drawn) {
                drawn = true;
                circle(store, center, radius, seconds);
            }
            return now >= end;
        }

        @Override
        public boolean contains(Vector3d p) {
            return horizontal(p, center) <= radius + 0.3 && inHeight(p, center);
        }

        @Override
        public Vector3d origin() {
            return center;
        }
    }

    /**
     * Cône de `width` radians centré sur la direction `facing` (radians, atan2(dz, dx)), du lanceur à `radius` blocs :
     * secteur rouge posé d'un coup, dont le remplissage atteint l'arc à l'instant du coup.
     */
    public static final class Cone implements Shape {
        final Vector3d apex;
        final double facing;
        final double width;
        final double radius;
        final long end;
        private final float seconds;
        private boolean drawn;

        public Cone(Vector3d apex, double facing, double width, double radius, long now, float seconds) {
            this.apex = new Vector3d(apex);
            this.facing = facing;
            this.width = width;
            this.radius = radius;
            this.seconds = seconds;
            this.end = now + seconds(seconds);
        }

        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            if (!drawn) {
                drawn = true;
                int angle = nearest(WarningShapes.SECTOR_ANGLES, (int) Math.round(Math.toDegrees(width)));
                shape(store, SECTOR + angle + "_" + shapeTenths(seconds), apex, facing, (float) (WARNING_SCALE * radius));
            }
            return now >= end;
        }

        @Override
        public boolean contains(Vector3d p) {
            double d = horizontal(p, apex);
            if (d > radius + 0.5 || !inHeight(p, apex)) {
                return false;
            }
            if (d < 0.75) {
                return true;
            }
            double off = Math.abs(Math.IEEEremainder(angle(apex, p) - facing, Math.PI * 2));
            // Marge d'un demi-bloc sur les côtés, comme sur l'arc.
            return off <= width / 2 + Math.atan2(0.5, Math.max(d, 0.5));
        }

        @Override
        public Vector3d origin() {
            return apex;
        }
    }

    /**
     * Ligne rouge de `length` blocs et `width` de large, du point `start` dans la direction `facing` (radians,
     * atan2(dz, dx)) : rectangle posé d'un coup, dont le remplissage s'allonge du lanceur jusqu'au bout à l'instant du
     * coup.
     */
    public static final class Strip implements Shape {
        final Vector3d start;
        final double facing;
        final double length;
        final double width;
        final long end;
        private final float seconds;
        private boolean drawn;

        public Strip(Vector3d start, double facing, double length, double width, long now, float seconds) {
            this.start = new Vector3d(start);
            this.facing = facing;
            this.length = length;
            this.width = width;
            this.seconds = seconds;
            this.end = now + seconds(seconds);
        }

        /** Point à `along` blocs sur l'axe et `side` blocs sur le côté (positif à gauche du sens de la ligne). */
        public Vector3d at(double along, double side) {
            double cx = Math.cos(facing);
            double cz = Math.sin(facing);
            return new Vector3d(start.x() + cx * along - cz * side, start.y(), start.z() + cz * along + cx * side);
        }

        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            if (!drawn) {
                drawn = true;
                int aspect = nearest(WarningShapes.LINE_ASPECTS, (int) Math.round(10 * length / width));
                shape(store, LINE + aspect + "_" + shapeTenths(seconds), start, facing, (float) (WarningShapes.LINE_SCALE * width));
            }
            return now >= end;
        }

        @Override
        public boolean contains(Vector3d p) {
            double dx = p.x() - start.x();
            double dz = p.z() - start.z();
            double along = dx * Math.cos(facing) + dz * Math.sin(facing);
            double side = -dx * Math.sin(facing) + dz * Math.cos(facing);
            return along >= -0.5 && along <= length + 0.5 && Math.abs(side) <= width / 2 + 0.4 && inHeight(p, start);
        }

        @Override
        public Vector3d origin() {
            return start;
        }
    }
}
