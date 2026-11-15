package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.outpost.Outpost;
import dev.nakasar.hytale.peuples.outpost.Outposts;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.List;

/**
 * Les règles d'un site de village suivant, communes à la génération naturelle ({@link MoreVillagesSeeder}) et au colon
 * ({@code outpost/Settlers}) : écarts avec les autres villages, terre ferme de la zone du peuple, sol du peuple sans eau,
 * relief modéré. {@link #check} dit la première règle qui n'est pas remplie, avec de quoi l'expliquer au joueur.
 */
public final class SiteRules {

    public static final String KEYS = "nakasar_peuples.settler.site.";

    /** Pourquoi un site ne convient pas (OK : il convient). */
    public enum Reason { OK, TOO_CLOSE_SAME, TOO_CLOSE_OTHER, PLANNED, OUT_OF_ZONE, SHORE, WATER, GROUND, RELIEF, UNLOADED, NO_LAYOUT }

    /** Résultat d'un examen : la raison et le message qui l'explique. */
    public record Check(Reason reason, Message message) {
        public boolean ok() {
            return reason == Reason.OK;
        }
    }

    /** Ce que le sol du site donne : points sondés, sur le sol du peuple sans eau, sous l'eau, relief. */
    public record Ground(int samples, int ground, int water, int relief) {
    }

    private SiteRules() {
    }

    /** Part minimale du sol du peuple (comme le premier lieu : herbe à 80 % pour les Kweebecs). */
    public static double minGround(People people) {
        return people == People.KWEEBEC ? 0.8 : 0.6;
    }

    /** Relief maximal sur le campement (comme le premier lieu). */
    public static int maxRelief(People people) {
        return people == People.KWEEBEC || people == People.TRORK ? 9 : 10;
    }

    /** Écart minimal avec un village de `other` pour un village de `people`. */
    public static int minSpacing(People people, People other) {
        return other == people ? MoreVillagesSeeder.SAME_MIN : MoreVillagesSeeder.OTHER_MIN;
    }

    /** Le village le plus proche qui est trop près de (x, z) pour un village de `people`, ou null. */
    public static Village tooClose(List<Village> all, People people, int x, int z) {
        Village worst = null;
        double best = Double.MAX_VALUE;
        for (Village v : all) {
            double min = minSpacing(people, v.people());
            double d = v.horizontalDistanceSquared(x, z);
            if (d < min * min && d < best) {
                worst = v;
                best = d;
            }
        }
        return worst;
    }

    /** Sonde le sol du campement (palier 0) centré en (cx, cz), un point tous les 6 blocs. */
    public static Ground ground(World world, VillageLayout layout, People people, int cx, int cz) {
        Terrain terrain = new Terrain(world);
        int r = layout.radiusUpTo(0);
        int samples = 0;
        int ground = 0;
        int water = 0;
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        for (int dx = -r; dx <= r; dx += 6) {
            for (int dz = -r; dz <= r; dz += 6) {
                if (dx * dx + dz * dz > r * r) {
                    continue;
                }
                samples++;
                int x = cx + dx;
                int z = cz + dz;
                int h = terrain.surface(x, z);
                if (h == Terrain.NONE) {
                    continue;
                }
                boolean wet = terrain.hasFluid(x, h + 1, z);
                if (wet) {
                    water++;
                } else if (people.suitsSite(Blocks.name(world.getChunkStore(), x, h, z))) {
                    ground++;
                }
                min = Math.min(min, h);
                max = Math.max(max, h);
            }
        }
        return new Ground(samples, ground, water, min > max ? 0 : max - min);
    }

    /** Vrai si le sol du campement convient (règles du premier lieu du peuple). */
    public static boolean terrainOk(World world, VillageLayout layout, People people, int cx, int cz) {
        Ground g = ground(world, layout, people, cx, cz);
        return g.samples() > 0 && g.ground() >= minGround(people) * g.samples() && g.relief() <= maxRelief(people);
    }

    /** Examine le site (cx, cz) pour un village de `people` (thread du monde, terrain déjà chargé). */
    public static Check check(World world, People people, int cx, int cz) {
        VillageLayout layout = VillageLayout.get(people.layout());
        if (layout == null) {
            return new Check(Reason.NO_LAYOUT, Message.translation("nakasar_peuples.village.layoutMissing").param("layout", people.layout()));
        }
        Village near = tooClose(Villages.registry(world).all(), people, cx, cz);
        if (near != null) {
            boolean same = near.people() == people;
            return new Check(same ? Reason.TOO_CLOSE_SAME : Reason.TOO_CLOSE_OTHER,
                    Message.translation(KEYS + (same ? "tooCloseSame" : "tooCloseOther")).param("name", near.name())
                            .param("people", Message.translation(near.people().nameKey()))
                            .param("distance", (int) Math.sqrt(near.horizontalDistanceSquared(cx, cz)))
                            .param("min", minSpacing(people, near.people())));
        }
        for (Outpost o : Outposts.all(world)) {
            People other = People.byId(o.people());
            double dx = o.x() - cx;
            double dz = o.z() - cz;
            int min = other == null ? MoreVillagesSeeder.OTHER_MIN : minSpacing(people, other);
            if (o.waiting() && dx * dx + dz * dz < (double) min * min) {
                return new Check(Reason.PLANNED, Message.translation(KEYS + "planned")
                        .param("distance", (int) Math.sqrt(dx * dx + dz * dz)).param("min", min));
            }
        }
        if (Zones.generator(world) != null) {
            String zone = Zones.name(world, cx, cz);
            if (Zones.number(zone) == people.zone() && !Zones.inland(zone, people.zone())) {
                return new Check(Reason.SHORE, Message.translation(KEYS + "shore"));
            }
            if (!ZoneSeeder.inZone(world, people.zone(), cx, cz, layout.radius())) {
                return new Check(Reason.OUT_OF_ZONE, Message.translation(KEYS + "outOfZone")
                        .param("zone", people.zone()).param("here", Math.max(Zones.number(zone), 0)));
            }
        }
        Ground g = ground(world, layout, people, cx, cz);
        int need = (int) Math.ceil(minGround(people) * g.samples());
        if (g.samples() == 0 || g.ground() + g.water() == 0 && g.relief() == 0) {
            return new Check(Reason.UNLOADED, Message.translation(KEYS + "unloaded"));
        }
        if (g.ground() < need) {
            boolean wet = g.water() > 0 && g.ground() + g.water() >= need;
            return new Check(wet ? Reason.WATER : Reason.GROUND, Message.translation(KEYS + (wet ? "water" : "ground"))
                    .param("ground", Message.translation(KEYS + "soil." + people.id()))
                    .param("percent", 100 * g.ground() / g.samples()).param("need", (int) Math.round(minGround(people) * 100)));
        }
        if (g.relief() > maxRelief(people)) {
            return new Check(Reason.RELIEF, Message.translation(KEYS + "relief").param("relief", g.relief()).param("max", maxRelief(people)));
        }
        return new Check(Reason.OK, Message.translation(KEYS + "ok"));
    }
}
