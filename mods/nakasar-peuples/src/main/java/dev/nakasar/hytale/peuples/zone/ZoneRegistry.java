package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.component.ResourceType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.List;

/**
 * État des zones 2 et 3 d'un monde (étape 8), ressource du monde (id {@value #ID}) sauvegardée avec lui : la ruche
 * scarak (points, dernier jour de croissance) et les abris d'eau nés des Graines d'Écho. Tout accès passe par le
 * thread du monde.
 */
public final class ZoneRegistry implements Resource<EntityStore> {

    public static final String ID = "Nakasar_Peuples_Zones";

    public static final BuilderCodec<ZoneRegistry> CODEC = BuilderCodec.builder(ZoneRegistry.class, ZoneRegistry::new)
            .append(new KeyedCodec<>("Hive", Codec.INTEGER), (r, v) -> r.hive = v == null ? Hive.START : v, r -> r.hive)
            .documentation("Points de la ruche scarak (0 à 100, un niveau tous les 20).")
            .add()
            .append(new KeyedCodec<>("HiveDay", Codec.LONG), (r, v) -> r.hiveDay = v == null ? -1L : v, r -> r.hiveDay)
            .documentation("Dernier jour de jeu où la ruche a grossi.")
            .add()
            .append(new KeyedCodec<>("Shelters", Codec.INT_ARRAY), (r, v) -> r.setShelters(v), r -> r.sheltersArray())
            .documentation("Abris d'eau des Graines d'Écho : x, y, z à la suite.")
            .add()
            .build();

    private static ResourceType<EntityStore, ZoneRegistry> resourceType;

    int hive = Hive.START;
    long hiveDay = -1L;
    private final List<int[]> shelters = new ArrayList<>();

    public ZoneRegistry() {
    }

    public static void setResourceType(ResourceType<EntityStore, ZoneRegistry> type) {
        resourceType = type;
    }

    public static ZoneRegistry get(World world) {
        return world.getEntityStore().getStore().getResource(resourceType);
    }

    public int hive() {
        return hive;
    }

    public List<int[]> shelters() {
        return shelters;
    }

    void addShelter(int x, int y, int z) {
        shelters.add(new int[] {x, y, z});
    }

    private void setShelters(int[] flat) {
        shelters.clear();
        if (flat != null) {
            for (int i = 0; i + 2 < flat.length; i += 3) {
                shelters.add(new int[] {flat[i], flat[i + 1], flat[i + 2]});
            }
        }
    }

    private int[] sheltersArray() {
        int[] flat = new int[shelters.size() * 3];
        for (int i = 0; i < shelters.size(); i++) {
            System.arraycopy(shelters.get(i), 0, flat, i * 3, 3);
        }
        return flat;
    }

    @Override
    public Resource<EntityStore> clone() {
        ZoneRegistry copy = new ZoneRegistry();
        copy.hive = hive;
        copy.hiveDay = hiveDay;
        for (int[] s : shelters) {
            copy.shelters.add(s.clone());
        }
        return copy;
    }
}
