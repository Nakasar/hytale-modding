package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

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
            .build();

    private final List<Village> villages = new ArrayList<>();

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

    @Override
    public Resource<EntityStore> clone() {
        VillageRegistry copy = new VillageRegistry();
        for (Village v : villages) {
            copy.villages.add(v.copy());
        }
        return copy;
    }
}
