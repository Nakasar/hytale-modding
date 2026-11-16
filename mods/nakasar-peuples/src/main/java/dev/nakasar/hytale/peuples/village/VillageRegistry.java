package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Les villages d'un monde : ressource du monde (id {@value #ID}), sauvegardée avec lui comme la réputation vanilla
 * ({@code ReputationDataResource}). Tout accès passe par le thread du monde.
 */
public final class VillageRegistry implements Resource<EntityStore> {

    public static final String ID = "Nakasar_Peuples_Villages";

    public static final BuilderCodec<VillageRegistry> CODEC = BuilderCodec.builder(VillageRegistry.class, VillageRegistry::new)
            .append(new KeyedCodec<>("Villages", new ArrayCodec<>(Village.CODEC, Village[]::new)),
                    (r, v) -> r.setAll(v), r -> r.villages.toArray(Village[]::new))
            .documentation("Villages du monde.")
            .add()
            .append(new KeyedCodec<>("Seeded", Codec.BOOLEAN), (r, b) -> r.seeded = b != null && b, r -> r.seeded)
            .documentation("Vrai une fois le premier village kweebec posé près du point d'apparition (VillageSeeder).")
            .add()
            .append(new KeyedCodec<>("SeedAttempts", Codec.INTEGER), (r, i) -> r.seedAttempts = i == null ? 0 : i, r -> r.seedAttempts)
            .documentation("Recherches de site déjà faites sans succès (chacune essaie un autre jeu de sites).")
            .add()
            .append(new KeyedCodec<>("SeededPeople", Codec.STRING_ARRAY),
                    (r, a) -> r.setSeededPeople(a), r -> r.seededPeople.toArray(String[]::new))
            .documentation("Peuples (ids) dont le lieu automatique est déjà posé, hors premier village kweebec (champ Seeded) : "
                    + "camp trork (étape 7), villages des zones 2 et 3 (étape 8).")
            .add()
            .append(new KeyedCodec<>("MoreSeeded", Codec.STRING_ARRAY),
                    (r, a) -> readCounts(r.moreSeeded, a), r -> writeCounts(r.moreSeeded))
            .documentation("Villages suivants posés tout seuls, par peuple (« Kweebec=2 ») : MoreVillagesSeeder, en plus du premier.")
            .add()
            .append(new KeyedCodec<>("MoreFailures", Codec.STRING_ARRAY),
                    (r, a) -> readCounts(r.moreFailures, a), r -> writeCounts(r.moreFailures))
            .documentation("Recherches de village suivant restées sans site, par peuple (on abandonne après quelques-unes).")
            .add()
            .append(new KeyedCodec<>("Beacons", Codec.STRING_ARRAY), (r, a) -> r.setBeacons(a), r -> r.writeBeacons())
            .documentation("Balises de route posées par les joueurs (« x,y,z ») : les convois des avant-postes les suivent (annex/Routes).")
            .add()
            .build();

    private final Map<String, Integer> moreSeeded = new LinkedHashMap<>();
    private final Map<String, Integer> moreFailures = new LinkedHashMap<>();
    private final List<Village> villages = new ArrayList<>();
    private boolean seeded;
    private int seedAttempts;
    private final Set<String> seededPeople = new LinkedHashSet<>();
    private final List<int[]> beacons = new ArrayList<>();
    private int beaconVersion;

    public VillageRegistry() {
    }

    private void setAll(Village[] all) {
        villages.clear();
        if (all != null) {
            for (Village v : all) {
                if (v != null) {
                    villages.add(v);
                }
            }
        }
    }

    public boolean isSeeded() {
        return seeded;
    }

    void setSeeded(boolean value) {
        seeded = value;
    }

    /** Vrai une fois le lieu automatique du peuple posé (le Kweebec garde son champ {@code Seeded}). */
    public boolean isSeeded(People people) {
        return people == People.KWEEBEC ? seeded : seededPeople.contains(people.id());
    }

    public void setSeeded(People people, boolean value) {
        if (people == People.KWEEBEC) {
            seeded = value;
        } else if (value) {
            seededPeople.add(people.id());
        } else {
            seededPeople.remove(people.id());
        }
    }

    private void setSeededPeople(String[] ids) {
        seededPeople.clear();
        if (ids != null) {
            for (String id : ids) {
                if (id != null && !id.isBlank()) {
                    seededPeople.add(id);
                }
            }
        }
    }

    /** Villages suivants (après le premier) déjà posés tout seuls pour ce peuple. */
    public int moreSeeded(People people) {
        return moreSeeded.getOrDefault(people.id(), 0);
    }

    public void countMoreSeeded(People people) {
        moreSeeded.merge(people.id(), 1, Integer::sum);
    }

    /** Recherches de village suivant sans site pour ce peuple. */
    public int moreFailures(People people) {
        return moreFailures.getOrDefault(people.id(), 0);
    }

    public void countMoreFailure(People people) {
        moreFailures.merge(people.id(), 1, Integer::sum);
    }

    public void resetMoreFailures(People people) {
        moreFailures.remove(people.id());
    }

    private static void readCounts(Map<String, Integer> into, String[] entries) {
        into.clear();
        if (entries == null) {
            return;
        }
        for (String e : entries) {
            int eq = e == null ? -1 : e.indexOf('=');
            if (eq > 0) {
                try {
                    into.put(e.substring(0, eq), Integer.parseInt(e.substring(eq + 1).trim()));
                } catch (NumberFormatException ignored) {
                    // entrée abîmée : ignorée
                }
            }
        }
    }

    private static String[] writeCounts(Map<String, Integer> counts) {
        return counts.entrySet().stream().map(e -> e.getKey() + "=" + e.getValue()).toArray(String[]::new);
    }

    // ---- Balises de route (communes à tous les villages) ----

    private void setBeacons(String[] entries) {
        beacons.clear();
        if (entries != null) {
            for (String e : entries) {
                String[] p = e == null ? new String[0] : e.split(",");
                if (p.length == 3) {
                    try {
                        beacons.add(new int[] {Integer.parseInt(p[0].trim()), Integer.parseInt(p[1].trim()), Integer.parseInt(p[2].trim())});
                    } catch (NumberFormatException ignored) {
                        // entrée abîmée : ignorée
                    }
                }
            }
        }
        beaconVersion++;
    }

    private String[] writeBeacons() {
        return beacons.stream().map(b -> b[0] + "," + b[1] + "," + b[2]).toArray(String[]::new);
    }

    /** Balises de route du monde, {x, y, z} (lecture seule). */
    public List<int[]> beacons() {
        return Collections.unmodifiableList(beacons);
    }

    /** Change à chaque balise posée ou retirée (les convois recalculent alors leur route). */
    public int beaconVersion() {
        return beaconVersion;
    }

    public boolean isBeacon(int x, int y, int z) {
        for (int[] b : beacons) {
            if (b[0] == x && b[1] == y && b[2] == z) {
                return true;
            }
        }
        return false;
    }

    public void addBeacon(int x, int y, int z) {
        if (!isBeacon(x, y, z)) {
            beacons.add(new int[] {x, y, z});
            beaconVersion++;
        }
    }

    public boolean removeBeacon(int x, int y, int z) {
        boolean removed = beacons.removeIf(b -> b[0] == x && b[1] == y && b[2] == z);
        if (removed) {
            beaconVersion++;
        }
        return removed;
    }

    public int seedAttempts() {
        return seedAttempts;
    }

    void countSeedAttempt() {
        seedAttempts++;
    }

    public List<Village> all() {
        return Collections.unmodifiableList(villages);
    }

    void add(Village village) {
        villages.add(village);
    }

    boolean remove(Village village) {
        return villages.remove(village);
    }

    public Village byId(String id) {
        for (Village v : villages) {
            if (v.id().equals(id)) {
                return v;
            }
        }
        // Lieux-dits (sauvegardés à part) : leurs commandes et leur réputation passent par leur id « H:… ».
        return hamlets != null && HamletRegistry.isHamlet(id) ? hamlets.byId(id) : null;
    }

    /** Lieux-dits du monde, posés par {@link Villages#registry} (non sauvegardé ici). */
    transient HamletRegistry hamlets;

    /** Village dont le tableau est en (x, y, z), ou null. */
    public Village byBoard(int x, int y, int z) {
        for (Village v : villages) {
            if (v.isBoard(x, y, z)) {
                return v;
            }
        }
        return null;
    }

    /** Village dont un bâtiment de métier a son panneau en (x, y, z), ou null. */
    public Village byWorkshopBoard(int x, int y, int z) {
        for (Village v : villages) {
            if (v.workshopAt(x, y, z) != null) {
                return v;
            }
        }
        return hamlets == null ? null : hamlets.byWorkshopBoard(x, y, z);
    }

    /** Village dont le cœur est le plus proche de (x, y, z), à moins de `radius` blocs, ou null. */
    public Village nearest(double x, double y, double z, double radius) {
        Village best = null;
        double bestDistance = radius * radius;
        for (Village v : villages) {
            double d = v.distanceSquared(x, y, z);
            if (d <= bestDistance) {
                best = v;
                bestDistance = d;
            }
        }
        return best;
    }

    /** Village du peuple `people` (null : tous) dont le cœur est le plus proche à l'horizontale, à moins de `radius` blocs, ou null. */
    public Village nearestOf(People people, double x, double z, double radius) {
        Village best = null;
        double bestDistance = radius * radius;
        for (Village v : villages) {
            if (people != null && v.people() != people) {
                continue;
            }
            double d = v.horizontalDistanceSquared(x, z);
            if (d <= bestDistance) {
                best = v;
                bestDistance = d;
            }
        }
        return best;
    }

    @Override
    public Resource<EntityStore> clone() {
        VillageRegistry copy = new VillageRegistry();
        for (Village v : villages) {
            copy.villages.add(v.copy());
        }
        copy.seeded = seeded;
        copy.seedAttempts = seedAttempts;
        copy.seededPeople.addAll(seededPeople);
        copy.moreSeeded.putAll(moreSeeded);
        copy.moreFailures.putAll(moreFailures);
        for (int[] b : beacons) {
            copy.beacons.add(b.clone());
        }
        copy.beaconVersion = beaconVersion;
        return copy;
    }
}
