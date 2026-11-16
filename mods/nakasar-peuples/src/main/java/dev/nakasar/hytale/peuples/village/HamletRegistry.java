package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.component.Resource;
import com.hypixel.hytale.component.ResourceType;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Les lieux-dits posés d'un monde, sauvegardés à part des villages (Kevin, 16 novembre 2026 : un lieu-dit n'est rattaché
 * à aucun village). Chacun est un petit « village » à lui (id {@code H:<lieu-dit>}) : sa propre réputation (clé de
 * réputation du joueur = son id), son dépôt, le panneau et l'état de son bâtiment de métier. Il n'est jamais dans
 * {@link VillageRegistry#all()} (ni raids, ni villageois, ni chantiers) ; {@link VillageRegistry#byId} et
 * {@link VillageRegistry#byWorkshopBoard} le trouvent, pour les commandes et le panneau.
 */
public final class HamletRegistry implements Resource<EntityStore> {

    public static final String ID = "Nakasar_Peuples_Hamlets";
    public static final String PREFIX = "H:";
    /** Palier donné au lieu-dit : ses niveaux ne dépendent d'aucun village (seulement savoir-faire et maître). */
    public static final int TIER = 3;

    public static final BuilderCodec<HamletRegistry> CODEC = BuilderCodec.builder(HamletRegistry.class, HamletRegistry::new)
            .append(new KeyedCodec<>("Hamlets", new ArrayCodec<>(Village.CODEC, Village[]::new)),
                    (r, v) -> r.set(v), r -> r.hamlets.toArray(Village[]::new))
            .documentation("Lieux-dits posés (world/Hamlets) : réputation, dépôt et bâtiment de métier de chacun.")
            .add()
            .build();

    private static ResourceType<EntityStore, HamletRegistry> resourceType;

    private final List<Village> hamlets = new ArrayList<>();

    public HamletRegistry() {
    }

    public static void setResourceType(ResourceType<EntityStore, HamletRegistry> type) {
        resourceType = type;
    }

    public static HamletRegistry of(World world) {
        return resourceType == null ? null : world.getEntityStore().getStore().getResource(resourceType);
    }

    public static boolean isHamlet(String id) {
        return id != null && id.startsWith(PREFIX);
    }

    private void set(Village[] all) {
        hamlets.clear();
        if (all != null) {
            for (Village v : all) {
                if (v != null) {
                    hamlets.add(v);
                }
            }
        }
    }

    public List<Village> all() {
        return Collections.unmodifiableList(hamlets);
    }

    public Village byId(String id) {
        for (Village v : hamlets) {
            if (v.id().equals(id)) {
                return v;
            }
        }
        return null;
    }

    public Village byWorkshopBoard(int x, int y, int z) {
        for (Village v : hamlets) {
            if (v.workshopAt(x, y, z) != null) {
                return v;
            }
        }
        return null;
    }

    /** L'état du lieu-dit `placeId` (créé s'il manque) : peuple, nom, place (x, y, z). */
    public Village ensure(String placeId, String name, People people, int x, int y, int z) {
        String id = PREFIX + placeId;
        Village v = byId(id);
        if (v == null) {
            v = new Village(id, name, people, x, y, z);
            v.tier = TIER;
            v.settled = true;
            v.depositY = NO_DEPOSIT;
            hamlets.add(v);
        }
        return v;
    }

    /** Hauteur du dépôt tant que son coffre n'est pas posé. */
    public static final int NO_DEPOSIT = Integer.MIN_VALUE;

    public static boolean hasDeposit(Village v) {
        return v.depositY != NO_DEPOSIT;
    }

    /** Dépôt du lieu-dit posé en (x, y, z). */
    public static void setDeposit(Village v, int x, int y, int z) {
        v.depositX = x;
        v.depositY = y;
        v.depositZ = z;
    }

    public void remove(String placeId) {
        hamlets.removeIf(v -> v.id().equals(PREFIX + placeId));
    }

    @Override
    public Resource<EntityStore> clone() {
        HamletRegistry r = new HamletRegistry();
        for (Village v : hamlets) {
            r.hamlets.add(v.copy());
        }
        return r;
    }
}
