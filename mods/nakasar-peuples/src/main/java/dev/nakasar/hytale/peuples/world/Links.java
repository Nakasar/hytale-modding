package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les liaisons entre villages : toute paire de villages à moins de {@value #MAX_LENGTH} blocs l'un de l'autre. Leur
 * route est celle des balises posées par les joueurs ({@link Routes}, recalculée quand les balises changent), sinon la
 * ligne droite d'un cœur à l'autre. Chaque passage (voyageur, caravane arrivés) est compté par jour
 * ({@link WorldLifeRegistry.Part#TRAFFIC}, sept derniers jours) : les auberges de relais naissent du trafic.
 */
public final class Links {

    public static final int MAX_LENGTH = 2400;
    public static final int WINDOW_DAYS = 7;

    /** Une liaison : `a` a l'id le plus petit. */
    public record Link(Village a, Village b, String key, double length) {

        public Village other(String villageId) {
            return a.id().equals(villageId) ? b : a;
        }

        public boolean has(String villageId) {
            return a.id().equals(villageId) || b.id().equals(villageId);
        }

        /** Milieu de la liaison (à vol d'oiseau). */
        public double[] middle() {
            return new double[] {(a.x() + b.x()) / 2.0, (a.z() + b.z()) / 2.0};
        }
    }

    private static final Map<String, Routes.Path> PATHS = new ConcurrentHashMap<>();

    private Links() {
    }

    public static String key(String a, String b) {
        return a.compareTo(b) <= 0 ? a + "|" + b : b + "|" + a;
    }

    /** Toutes les liaisons du monde, des plus courtes aux plus longues. */
    public static List<Link> all(World world) {
        List<Village> villages = new ArrayList<>(Villages.registry(world).all());
        villages.sort(Comparator.comparing(Village::id));
        List<Link> out = new ArrayList<>();
        for (int i = 0; i < villages.size(); i++) {
            for (int j = i + 1; j < villages.size(); j++) {
                Village a = villages.get(i);
                Village b = villages.get(j);
                double d = WorldLife.distance(a, b);
                if (d <= MAX_LENGTH) {
                    out.add(new Link(a, b, key(a.id(), b.id()), d));
                }
            }
        }
        out.sort(Comparator.comparingDouble(Link::length));
        return out;
    }

    /** La liaison entre deux villages (ou null s'ils sont trop loin ou disparus). */
    public static Link of(World world, String a, String b) {
        Village va = Villages.registry(world).byId(a);
        Village vb = Villages.registry(world).byId(b);
        if (va == null || vb == null || a.equals(b)) {
            return null;
        }
        double d = WorldLife.distance(va, vb);
        if (d > MAX_LENGTH) {
            return null;
        }
        return a.compareTo(b) <= 0 ? new Link(va, vb, key(a, b), d) : new Link(vb, va, key(a, b), d);
    }

    /** Liaisons d'un village. */
    public static List<Link> of(World world, Village village) {
        List<Link> out = new ArrayList<>();
        for (Link l : all(world)) {
            if (l.has(village.id())) {
                out.add(l);
            }
        }
        return out;
    }

    /** Route de `from` vers `to` (cœur à cœur), recalculée quand les balises changent. */
    public static Routes.Path path(World world, Village from, Village to) {
        String key = from.id() + ">" + to.id();
        int version = Villages.registry(world).beaconVersion();
        Routes.Path p = PATHS.get(key);
        if (p == null || p.version() != version) {
            p = Routes.path(world, from.x() + 0.5, from.z() + 0.5, to.x() + 0.5, to.z() + 0.5);
            PATHS.put(key, p);
        }
        return p;
    }

    /**
     * Recalcule la route de `from` vers `to` avec le terrain chargé maintenant (un joueur est près d'un voyageur : son
     * terrain réel, pont ou remblai, compte). Rend la nouvelle route.
     */
    public static Routes.Path refresh(World world, Village from, Village to) {
        Routes.Path p = Routes.path(world, from.x() + 0.5, from.z() + 0.5, to.x() + 0.5, to.z() + 0.5, true);
        PATHS.put(from.id() + ">" + to.id(), p);
        return p;
    }

    // ---- Trafic ----

    /** Un passage de plus sur la liaison, le jour `day`. */
    public static void pass(World world, String link, long day) {
        pass(world, link, day, 1);
    }

    /** `count` passages de plus sur la liaison, le jour `day` (une caravane : ses porteurs). */
    public static void pass(World world, String link, long day, int count) {
        WorldLifeRegistry r = WorldLife.registry(world);
        Map<Long, Integer> days = days(r.get(WorldLifeRegistry.Part.TRAFFIC, link), day);
        days.merge(day, count, Integer::sum);
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<Long, Integer> e : days.entrySet()) {
            if (sb.length() > 0) {
                sb.append(',');
            }
            sb.append(e.getKey()).append(':').append(e.getValue());
        }
        r.put(WorldLifeRegistry.Part.TRAFFIC, link, sb.toString());
    }

    /** Passages sur la liaison pendant les {@value #WINDOW_DAYS} derniers jours. */
    public static int traffic(World world, String link, long day) {
        int n = 0;
        for (int v : days(WorldLife.registry(world).get(WorldLifeRegistry.Part.TRAFFIC, link), day).values()) {
            n += v;
        }
        return n;
    }

    /** Dernier jour de passage sur la liaison (Long.MIN_VALUE : jamais). */
    public static long lastPass(World world, String link) {
        long last = Long.MIN_VALUE;
        for (long d : days(WorldLife.registry(world).get(WorldLifeRegistry.Part.TRAFFIC, link), Long.MAX_VALUE).keySet()) {
            last = Math.max(last, d);
        }
        return last;
    }

    private static Map<Long, Integer> days(String value, long today) {
        Map<Long, Integer> out = new java.util.TreeMap<>();
        if (value == null || value.isEmpty()) {
            return out;
        }
        for (String part : value.split(",")) {
            int cut = part.indexOf(':');
            if (cut <= 0) {
                continue;
            }
            try {
                long d = Long.parseLong(part.substring(0, cut));
                int n = Integer.parseInt(part.substring(cut + 1));
                if (today == Long.MAX_VALUE || d > today - WINDOW_DAYS) {
                    out.put(d, n);
                }
            } catch (NumberFormatException ignored) {
                // entrée abîmée : oubliée
            }
        }
        return out;
    }

    public static void clearAll() {
        PATHS.clear();
    }
}
