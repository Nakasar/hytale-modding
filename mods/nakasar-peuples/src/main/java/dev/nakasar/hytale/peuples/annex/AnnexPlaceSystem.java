package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.event.events.ecs.PlaceBlockEvent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import org.joml.Vector3d;
import org.joml.Vector3i;

/**
 * Pose d'une fondation d'avant-poste : si la place ne convient pas (trop près ou trop loin du village, sur un autre
 * village, dans l'eau, relief trop fort, constructions de joueurs, sol qui ne va pas au métier...), le bloc n'est pas
 * posé et le joueur reçoit l'erreur. Sinon le bloc est posé, la zone est marquée par le chantier du peuple et les
 * travaux durent une journée ({@link Annexes#start}). Le plan est tourné selon le côté où se tient le joueur : il
 * regarde l'entrée.
 */
public final class AnnexPlaceSystem extends EntityEventSystem<EntityStore, PlaceBlockEvent> {

    public AnnexPlaceSystem() {
        super(PlaceBlockEvent.class);
    }

    @Override
    public Query<EntityStore> getQuery() {
        return PlayerRef.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store, CommandBuffer<EntityStore> buffer,
                       PlaceBlockEvent event) {
        if (event.isCancelled()) {
            return;
        }
        ItemStack stack = event.getItemInHand();
        if (stack == null || ItemStack.isEmpty(stack) || !Annexes.isFoundation(stack.getItemId())) {
            return;
        }
        Vector3i at = event.getTargetBlock();
        PlayerRef player = chunk.getComponent(index, PlayerRef.getComponentType());
        if (at == null || player == null) {
            return;
        }
        World world = store.getExternalData().getWorld();
        Annexes.Pending pending = Annexes.pending(world, stack.getItemId(), at.x, at.z);
        if (pending == null) {
            refuse(event, player, Message.translation(Annexes.KEYS + "unbound"));
            return;
        }
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        Vector3d pos = transform == null ? null : transform.getPosition();
        int rotation = pos == null ? 0 : Annexes.rotationFacing(pos.x - (at.x + 0.5), pos.z - (at.z + 0.5));
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        Message error = Annexes.check(world, store, ref, pending.village(), pending.workshop(), at.x, at.y, at.z, rotation);
        if (error != null) {
            refuse(event, player, error);
            return;
        }
        Annexes.start(world, store, player, pending, at.x, at.y, at.z, rotation);
    }

    private static void refuse(PlaceBlockEvent event, PlayerRef player, Message error) {
        event.setCancelled(true);
        player.sendMessage(error);
        NotificationUtil.sendNotification(player.getPacketHandler(), error, NotificationStyle.Danger);
    }
}
