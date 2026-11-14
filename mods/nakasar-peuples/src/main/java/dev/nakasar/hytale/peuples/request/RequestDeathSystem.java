package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.UUID;

/**
 * Les morts de PNJ qui comptent pour les demandes :
 * <ul>
 *   <li>un membre de la bande d'une chasse ou de l'attaque d'une défense : +1 à la demande de son joueur, quel que
 *       soit le tueur (un garde du village qui aide compte aussi) ;</li>
 *   <li>un PNJ d'un rôle de chasse ({@link RequestTemplate#roles()}) tué par un joueur à moins de
 *       {@value RequestSystem#HUNT_RADIUS} blocs du village de sa demande : +1 aussi (les Trorks qui rôdent déjà) ;</li>
 *   <li>le captif d'une escorte : la demande échoue ;</li>
 *   <li>le crieur d'un village : il reviendra au matin.</li>
 * </ul>
 * Le travail se fait juste après le tick ({@code world.execute}) : il peut donner des objets et retirer des PNJ.
 */
public final class RequestDeathSystem extends DeathSystems.OnDeathSystem {

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        World world = store.getExternalData().getWorld();
        RequestSpawns.Owner owner = RequestSpawns.owner(ref);
        if (Criers.isPosted(ref)) {
            Criers.died(store, ref);
            return;
        }
        if (owner != null) {
            RequestSpawns.forget(ref);
            String[] parts = owner.key().split("\\|", 2);
            if (parts.length < 2) {
                return;
            }
            UUID playerId;
            try {
                playerId = UUID.fromString(parts[0]);
            } catch (IllegalArgumentException e) {
                return;
            }
            String requestId = parts[1];
            switch (owner.kind()) {
                case FOE -> world.execute(() -> withRequest(world, playerId, requestId, (p, r, data) -> {
                    Requests.advance(world, world.getEntityStore().getStore(), p.getReference(), p, data, r, 1);
                }));
                case CAPTIVE -> world.execute(() -> withRequest(world, playerId, requestId, (p, r, data) -> {
                    RequestSystem.forget(world, owner.key());
                    Requests.fail(world, world.getEntityStore().getStore(), p.getReference(), p, data, r, Requests.KEYS + "escort.lost");
                }));
                default -> {
                }
            }
            return;
        }
        // Chasse : un PNJ d'un rôle chassé, tué par un joueur.
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        TransformComponent transform = buffer.getComponent(ref, TransformComponent.getComponentType());
        Damage info = death.getDeathInfo();
        if (npc == null || transform == null || info == null || !(info.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> killer = source.getRef();
        PlayerRef player = killer == null || !killer.isValid() ? null : buffer.getComponent(killer, PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        String role = npc.getRoleName();
        Vector3d where = new Vector3d(transform.getPosition());
        world.execute(() -> creditHunt(world, player, role, where));
    }

    private static void creditHunt(World world, PlayerRef player, String role, Vector3d where) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Ref<EntityStore> ref = player.getReference();
        PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.get(store, ref);
        if (data == null) {
            return;
        }
        for (PlayerRequest r : new ArrayList<>(data.requests())) {
            RequestTemplate t = r.template();
            Village village = Villages.registry(world).byId(r.villageId());
            if (t == null || village == null || t.type() != RequestType.HUNT || !Arrays.asList(t.roles()).contains(role)) {
                continue;
            }
            if (village.horizontalDistanceSquared(where.x(), where.z()) <= (double) RequestSystem.HUNT_RADIUS * RequestSystem.HUNT_RADIUS) {
                Requests.advance(world, store, ref, player, data, r, 1);
                return;
            }
        }
    }

    @FunctionalInterface
    private interface RequestAction {
        void run(PlayerRef player, PlayerRequest request, PeuplesPlayer data);
    }

    /** Lance `action` sur la demande `requestId` du joueur `playerId` s'il est dans ce monde et l'a toujours. */
    private static void withRequest(World world, UUID playerId, String requestId, RequestAction action) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (PlayerRef p : world.getPlayerRefs()) {
            if (!p.getUuid().equals(playerId)) {
                continue;
            }
            Ref<EntityStore> ref = p.getReference();
            PeuplesPlayer data = ref == null || !ref.isValid() ? null : PeuplesPlayer.get(store, ref);
            PlayerRequest r = data == null ? null : data.request(requestId);
            if (r != null) {
                action.run(p, r, data);
            }
            return;
        }
    }
}
