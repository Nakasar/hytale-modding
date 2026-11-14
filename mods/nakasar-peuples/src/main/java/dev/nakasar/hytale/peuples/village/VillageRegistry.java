package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
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
            .build();

    private final List<Village> villages = new ArrayList<>();
    private boolean seeded;
    private int seedAttempts;
    private final Set<String> seededPeople = new LinkedHashSet<>();

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
        return null;
    }

    /** Village dont le tableau est en (x, y, z), ou null. */
    public Village byBoard(int x, int y, int z) {
        for (Village v : villages) {
            if (v.isBoard(x, y, z)) {
                return v;
            }
        }
        return null;
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
        return copy;
    }
}
