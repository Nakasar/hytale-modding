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
 *   <li>{@link Sweep} : cône (secteur) ou anneau rouge qui se charge d'un bord à l'autre, comme les cônes de Deepworks.
 *   Il est dessiné en pastilles rouges à plat ({@code Nakasar_Fractal_Cone_<dixièmes>}), anneau après anneau au rythme de la
 *   charge ; chaque pastille reste jusqu'à l'instant du coup. Le contour ({@code Nakasar_Fractal_Cone_Edge_<dixièmes>}) est posé
 *   dès le début, pour qu'on voie tout de suite la zone entière. Les pastilles sont placées en coordonnées du monde :
 *   aucune rotation de particule n'entre en jeu.</li>
 *   <li>{@link Strip} : ligne (bande) rouge qui se charge depuis le lanceur jusqu'au bout de sa portée, mêmes
 *   pastilles.</li>
 * </ul>
 */
public final class Telegraphs {

    public static final float WARNING_SCALE = 0.68f;
    /** Durées des pastilles de cône (tools/generate_warnings.py, CONE_TENTHS). */
    private static final int CONE_MIN = 2;
    private static final int CONE_MAX = 60;
    /** Durées des cercles (tools/generate_warnings.py, WARNING_TENTHS). */
    private static final int WARNING_MIN = 5;
    private static final int WARNING_MAX = 60;
    private static final String CONE = "Nakasar_Fractal_Cone_";
    private static final String CONE_EDGE = "Nakasar_Fractal_Cone_Edge_";
    /** Écart entre deux pastilles, leur rayon, et l'écart des points du contour (blocs). */
    private static final double DOT_STEP = 3.0;
    private static final double DOT_RADIUS = 2.0;
    private static final double EDGE_STEP = 2.5;
    private static final double EDGE_RADIUS = 0.3;
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

    private static void dot(ComponentAccessor<EntityStore> store, double x, double y, double z, String prefix,
                            double radius, float left) {
        int tenths = Math.min(CONE_MAX, Math.max(CONE_MIN, Math.round(left * 10)));
        particle(store, prefix + tenths, new Vector3d(x, y + 0.08, z), (float) (WARNING_SCALE * radius));
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
     * Cône ou anneau qui se charge en `seconds` secondes, du rayon `from` au rayon `to` (vers l'extérieur si from &lt;
     * to, vers le centre sinon), sur le secteur qui part de l'angle `start` et tourne de `span` radians (2π : anneau
     * complet). {@link #step} le dessine au fil de la charge ; {@link #contains} dit qui est dedans au moment du coup.
     */
    public static final class Sweep implements Shape {
        public final Vector3d center;
        public final double start;
        public final double span;
        public final double from;
        public final double to;
        public final long begin;
        public final long end;
        private double drawn;
        private boolean edges;

        public Sweep(Vector3d center, double start, double span, double from, double to, long now, float seconds) {
            this.center = new Vector3d(center);
            this.start = start;
            this.span = span;
            this.from = from;
            this.to = to;
            this.begin = now;
            this.end = now + seconds(seconds);
            this.drawn = 0;
        }

        /** Secteur en degrés (atan2(dz, dx), de a0 à a1 dans le sens positif). */
        public static Sweep arc(Vector3d center, double a0, double a1, double from, double to, long now, float seconds) {
            double span = ((a1 - a0) % 360 + 360) % 360;
            return new Sweep(center, Math.toRadians(a0), Math.toRadians(span == 0 ? 360 : span), from, to, now, seconds);
        }

        /** Cône de `width` radians centré sur la direction `facing` (radians, atan2(dz, dx)), du lanceur à `radius`. */
        public static Sweep cone(Vector3d apex, double facing, double width, double radius, long now, float seconds) {
            return new Sweep(apex, facing - width / 2, width, 0, radius, now, seconds);
        }

        /** Pose le contour au premier appel, puis les anneaux que la charge a atteints. Vrai une fois le coup venu. */
        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            float left = (end - now) / 1e9f;
            if (!edges) {
                edges = true;
                drawEdges(store, left);
            }
            double length = Math.abs(to - from);
            double reached = length * Math.min(1.0, Math.max(0.0, (now - begin) / (double) (end - begin)));
            // Anneaux au milieu de chaque bande de DOT_STEP, du bord de départ au bord d'arrivée ; la dernière bande,
            // plus courte quand la longueur n'est pas un multiple de DOT_STEP, est posée au milieu de ce qui reste.
            while (drawn < length - 1e-6 && drawn + Math.min(DOT_STEP, length - drawn) / 2 <= reached + 1e-6) {
                double r = from + Math.signum(to - from) * (drawn + Math.min(DOT_STEP, length - drawn) / 2);
                drawRing(store, Math.min(Math.max(r, Math.min(from, to)), Math.max(from, to)), CONE, DOT_STEP, DOT_RADIUS, left);
                drawn += DOT_STEP;
            }
            return now >= end;
        }

        public boolean contains(Vector3d p) {
            double d = horizontal(p, center);
            if (d < Math.min(from, to) - 0.5 || d > Math.max(from, to) + 0.5 || !inHeight(p, center)) {
                return false;
            }
            if (span >= Math.PI * 2 - 1e-6 || d < 0.75) {
                return true;
            }
            double a = ((angle(center, p) - start) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
            // Marge d'un demi-bloc sur les côtés, comme sur les bords.
            double margin = Math.atan2(0.5, Math.max(d, 0.5));
            return a <= span + margin || a >= Math.PI * 2 - margin;
        }

        @Override
        public Vector3d origin() {
            return center;
        }

        private void drawEdges(ComponentAccessor<EntityStore> store, float left) {
            double inner = Math.min(from, to);
            double outer = Math.max(from, to);
            drawRing(store, outer, CONE_EDGE, EDGE_STEP, EDGE_RADIUS, left);
            if (inner > 0.5) {
                drawRing(store, inner, CONE_EDGE, EDGE_STEP, EDGE_RADIUS, left);
            }
            if (span < Math.PI * 2 - 1e-6) {
                for (double side : new double[]{start, start + span}) {
                    for (double r = inner; r <= outer + 1e-6; r += EDGE_STEP) {
                        polar(store, side, r, CONE_EDGE, EDGE_RADIUS, left);
                    }
                }
            }
        }

        private void drawRing(ComponentAccessor<EntityStore> store, double r, String prefix, double step, double radius, float left) {
            int n = Math.max(1, (int) Math.ceil(Math.abs(span) * r / step));
            for (int k = 0; k < n; k++) {
                polar(store, start + span * (k + 0.5) / n, r, prefix, radius, left);
            }
        }

        private void polar(ComponentAccessor<EntityStore> store, double angle, double r, String prefix, double radius, float left) {
            dot(store, center.x() + Math.cos(angle) * r, center.y(), center.z() + Math.sin(angle) * r, prefix, radius, left);
        }
    }

    /**
     * Ligne rouge de `length` blocs et `width` de large, du point `start` dans la direction `facing` (radians,
     * atan2(dz, dx)) : le contour est posé dès le début, puis la bande se remplit du lanceur vers le bout.
     */
    public static final class Strip implements Shape {
        final Vector3d start;
        final double facing;
        final double length;
        final double width;
        final long begin;
        final long end;
        private final double step;
        private final double dotRadius;
        private double drawn;
        private boolean edges;

        public Strip(Vector3d start, double facing, double length, double width, long now, float seconds) {
            this.start = new Vector3d(start);
            this.facing = facing;
            this.length = length;
            this.width = width;
            this.begin = now;
            this.end = now + seconds(seconds);
            this.dotRadius = Math.min(DOT_RADIUS, Math.max(0.6, width / 2));
            this.step = Math.max(1.0, dotRadius * 1.4);
        }

        /** Point à `along` blocs sur l'axe et `side` blocs sur le côté (positif à gauche du sens de la ligne). */
        public Vector3d at(double along, double side) {
            double cx = Math.cos(facing);
            double cz = Math.sin(facing);
            return new Vector3d(start.x() + cx * along - cz * side, start.y(), start.z() + cz * along + cx * side);
        }

        @Override
        public boolean step(ComponentAccessor<EntityStore> store, long now) {
            float left = (end - now) / 1e9f;
            if (!edges) {
                edges = true;
                for (double s = 0; s <= length + 1e-6; s += EDGE_STEP) {
                    for (double side : new double[]{-width / 2, width / 2}) {
                        Vector3d p = at(s, side);
                        dot(store, p.x(), p.y(), p.z(), CONE_EDGE, EDGE_RADIUS, left);
                    }
                }
                for (double side = -width / 2; side <= width / 2 + 1e-6; side += Math.max(0.6, width / 3)) {
                    Vector3d p = at(length, side);
                    dot(store, p.x(), p.y(), p.z(), CONE_EDGE, EDGE_RADIUS, left);
                }
            }
            double reached = length * Math.min(1.0, Math.max(0.0, (now - begin) / (double) (end - begin)));
            while (drawn < length - 1e-6 && drawn + Math.min(step, length - drawn) / 2 <= reached + 1e-6) {
                Vector3d p = at(drawn + Math.min(step, length - drawn) / 2, 0);
                dot(store, p.x(), p.y(), p.z(), CONE, dotRadius, left);
                drawn += step;
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
