package dev.nakasar.hytale.peuples.trork;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefSystem;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/**
 * Apprivoiser un camp trork par la viande (étape 7 ; GDD : comportement vanilla Dropped_Meat). Les Trorks vanilla
 * repèrent la viande au sol à 15 blocs (capteur {@code DroppedItem "*meat*"}), vont la ramasser et la mangent ; un Trork
 * qui voit un joueur hostile le poursuit d'abord : il faut jeter la viande et s'éloigner.
 *
 * <p>Le mod suit la viande jetée par un joueur (à moins de {@value #DROPPER_REACH} blocs de lui) près d'un camp trork
 * (à moins de {@value #CAMP_REACH} blocs du cœur). Quand elle disparaît sans qu'un joueur la ramasse, avec un PNJ trork
 * à moins de {@value #EATER_REACH} blocs, le joueur qui l'a jetée gagne {@value #PER_MEAT} de réputation au camp par
 * morceau (au plus {@value #MAX_PER_STACK} par tas), jusqu'au rang Toléré : au-delà, le camp veut des demandes.
 */
public final class MeatOfferings extends RefSystem<EntityStore> {

    public static final int CAMP_REACH = 40;
    public static final double DROPPER_REACH = 4.0;
    public static final double EATER_REACH = 4.0;
    public static final int PER_MEAT = 15;
    public static final int MAX_PER_STACK = 4;
    public static final String KEYS = "nakasar_peuples.meat.";

    private record Offering(UUID player, String village, int quantity, Vector3d at) {
    }

    private static final Map<Ref<EntityStore>, Offering> TRACKED = Collections.synchronizedMap(new IdentityHashMap<>());

    @Override
    public Query<EntityStore> getQuery() {
        return ItemComponent.getComponentType();
    }

    /** Vrai si l'objet est de la viande (même motif que le capteur vanilla des Trorks). */
    public static boolean isMeat(String itemId) {
        return itemId != null && itemId.toLowerCase(Locale.ROOT).contains("meat");
    }

    @Override
    public void onEntityAdded(Ref<EntityStore> ref, AddReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (reason != AddReason.SPAWN) {
            return;
        }
        ItemComponent item = store.getComponent(ref, ItemComponent.getComponentType());
        ItemStack stack = item == null ? null : item.getItemStack();
        TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
        World world = store.getExternalData().getWorld();
        if (stack == null || stack.isEmpty() || !isMeat(stack.getItemId()) || transform == null || world == null) {
            return;
        }
        Vector3d at = new Vector3d(transform.getPosition());
        Village camp = Villages.registry(world).nearestOf(People.TRORK, at.x(), at.z(), CAMP_REACH);
        if (camp == null) {
            return;
        }
        UUID dropper = null;
        double best = DROPPER_REACH * DROPPER_REACH;
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> p = player.getReference();
            TransformComponent t = p == null || !p.isValid() ? null : store.getComponent(p, TransformComponent.getComponentType());
            if (t != null && t.getPosition().distanceSquared(at) <= best) {
                best = t.getPosition().distanceSquared(at);
                dropper = player.getUuid();
            }
        }
        if (dropper != null) {
            TRACKED.put(ref, new Offering(dropper, camp.id(), Math.min(MAX_PER_STACK, stack.getQuantity()), at));
        }
    }

    @Override
    public void onEntityRemove(Ref<EntityStore> ref, RemoveReason reason, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        Offering offering = TRACKED.remove(ref);
        if (offering == null || reason != RemoveReason.REMOVE) {
            return;
        }
        ItemComponent item = store.getComponent(ref, ItemComponent.getComponentType());
        if (item != null && item.isRemovedByPlayerPickup()) {
            return;
        }
        World world = store.getExternalData().getWorld();
        world.execute(() -> eaten(world, offering));
    }

    private static void eaten(World world, Offering offering) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        if (!trorkNear(store, offering.at())) {
            return;
        }
        Village camp = Villages.registry(world).byId(offering.village());
        PlayerRef player = null;
        for (PlayerRef p : world.getPlayerRefs()) {
            if (p.getUuid().equals(offering.player())) {
                player = p;
            }
        }
        Ref<EntityStore> ref = player == null ? null : player.getReference();
        if (camp == null || ref == null || !ref.isValid()) {
            return;
        }
        int current = Reputations.villageValue(PeuplesPlayer.get(store, ref), camp);
        int gain = Math.min(offering.quantity() * PER_MEAT, Rank.TOLERE.min() - current);
        if (gain <= 0) {
            NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(KEYS + "enough")
                    .param("village", camp.name()), NotificationStyle.Default);
            return;
        }
        Reputations.change(world, store, ref, player, camp, gain, KEYS + "reason");
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : viande mangée au camp %s, +%d pour %s", camp.name(), gain, player.getUsername());
    }

    /** Vrai si un PNJ trork (rôle *Trork*, comme le groupe vanilla) est à moins de {@value #EATER_REACH} blocs. */
    private static boolean trorkNear(Store<EntityStore> store, Vector3d at) {
        boolean[] found = {false};
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size() && !found[0]; i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                TransformComponent t = chunk.getComponent(i, TransformComponent.getComponentType());
                String role = npc == null ? null : npc.getRoleName();
                if (t != null && role != null && role.contains("Trork")
                        && t.getPosition().distanceSquared(at) <= EATER_REACH * EATER_REACH) {
                    found[0] = true;
                }
            }
        });
        return found[0];
    }

    public static void clearAll() {
        TRACKED.clear();
    }
}
