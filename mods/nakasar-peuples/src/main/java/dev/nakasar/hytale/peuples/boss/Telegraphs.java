package dev.nakasar.hytale.peuples.boss;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * Annonces au sol des chefs des demandes de boss, copiées du mod Fractales ({@code combat.Telegraphs}, lui-même copié
 * du mod Vampires : pas de bibliothèque commune entre les mods). Une zone rouge a la taille exacte du coup (règle n° 3
 * d'AGENTS.md) : la forme qui dessine l'annonce est aussi celle qui dit qui est touché, avec pour seule marge la
 * demi-largeur du corps ({@link #BODY}). Couleurs et opacités des Deepworks (règle n° 4), particules écrites par
 * tools/generate_quests.py : {@code Nakasar_Peuples_Warning_<dixièmes>} (cercles), {@code Nakasar_Peuples_Line_<rapport>_<dixièmes>}
 * (lignes) et {@code Nakasar_Peuples_Sector_<angle>_<dixièmes>} (cônes).
 */
public final class Telegraphs {

    public static final float WARNING_SCALE = 0.68f;
    private static final int WARNING_MIN = 5;
    private static final int WARNING_MAX = 60;
    private static final String LINE = "Nakasar_Peuples_Line_";
    private static final String SECTOR = "Nakasar_Peuples_Sector_";
    private static final double BELOW = 1.5;
    private static final double ABOVE = 3.5;
    /** Demi-largeur du corps d'un joueur : seule marge admise entre la zone rouge et le test de touche. */
    public static final double BODY = 0.3;

    private Telegraphs() {
    }

    /** Zone d'annonce au sol : dessinée une fois ; dit qui est dedans au moment du coup. */
    public interface Shape {
        /** Dessine la zone (une fois). Vrai une fois le coup venu. */
        boolean step(ComponentAccessor<EntityStore> store, long now);

        boolean contains(Vector3d p);

        Vector3d origin();
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

    public static boolean inCircle(Vector3d p, Vector3d center, double radius) {
        return horizontal(p, center) <= radius + BODY && inHeight(p, center);
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

    public static long nanos(float s) {
        return (long) (s * 1_000_000_000L);
    }

    private static boolean inHeight(Vector3d p, Vector3d ground) {
        double dy = p.y() - ground.y();
        return dy >= -BELOW && dy <= ABOVE;
    }

    private static void shape(ComponentAccessor<EntityStore> store, String id, Vector3d at, double facing, float scale) {
        float yaw = (float) Math.atan2(-Math.cos(facing), -Math.sin(facing));
        ParticleUtil.spawnParticleEffect(id, new Vector3d(at).add(0, 0.08, 0), yaw, 0f, 0f, scale, 1f, store);
    }

    private static int shapeTenths(float seconds) {
        return Math.min(WarningShapes.MAX_TENTHS, Math.max(WarningShapes.MIN_TENTHS, Math.round(seconds * 10)));
    }

    private static int nearest(int[] available, int wanted) {
        int best = available[0];
        for (int v : available) {
            if (Math.abs(v - wanted) < Math.abs(best - wanted)) {
                best = v;
            }
        }
        return best;
    }

    /** Cercle rouge de `radius` blocs, plein au bout de `seconds`. */
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
            this.end = now + nanos(seconds);
        }

        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            if (!drawn) {
                drawn = true;
                int tenths = Math.min(WARNING_MAX, Math.max(WARNING_MIN, Math.round(seconds * 10)));
                particle(store, "Nakasar_Peuples_Warning_" + tenths, new Vector3d(center).add(0, 0.1, 0), (float) (WARNING_SCALE * radius));
            }
            return now >= end;
        }

        @Override
        public boolean contains(Vector3d p) {
            return inCircle(p, center, radius);
        }

        @Override
        public Vector3d origin() {
            return center;
        }
    }

    /** Cône de `width` radians centré sur `facing` (atan2(dz, dx)), du lanceur à `radius` blocs. */
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
            this.end = now + nanos(seconds);
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
            if (d > radius + BODY || !inHeight(p, apex)) {
                return false;
            }
            if (d < 0.75) {
                return true;
            }
            double off = Math.abs(Math.IEEEremainder(angle(apex, p) - facing, Math.PI * 2));
            return off <= width / 2 + Math.atan2(BODY, Math.max(d, 0.5));
        }

        @Override
        public Vector3d origin() {
            return apex;
        }
    }

    /** Ligne de `length` blocs et `width` de large depuis `start`, dans la direction `facing` (atan2(dz, dx)). */
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
            this.end = now + nanos(seconds);
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
            return along >= -BODY && along <= length + BODY && Math.abs(side) <= width / 2 + BODY && inHeight(p, start);
        }

        @Override
        public Vector3d origin() {
            return start;
        }
    }
}
