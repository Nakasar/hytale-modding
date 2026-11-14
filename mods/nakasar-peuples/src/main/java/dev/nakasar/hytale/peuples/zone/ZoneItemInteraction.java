package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import org.joml.Vector3d;

/**
 * {@code "Type": "Nakasar_Peuples_ZoneItem"} : objets des zones utilisés en main (étape 8). Clé JSON {@code Action} :
 * <ul>
 *   <li>{@code Waterskin} (Outre d'oasis) : bue, elle est retirée et annule la soif {@value Climate#QUENCH_SECONDS} s ;</li>
 *   <li>{@code EchoSeed} (Graine d'Écho, fin de la chaîne kweebec) : plantée en zone 2 (les Dunes), elle fait pousser un
 *   abri d'eau (bassin kweebec vanilla {@value #POOL}, quatre blocs devant le joueur) où la soif ne prend pas, et les
 *   Feran reconnaissent le joueur : réputation de peuple feran portée au rang toléré au moins (GDD, Récompenses).</li>
 * </ul>
 */
public class ZoneItemInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Peuples_ZoneItem";
    public static final String POOL = "Npc/Kweebec/Oak/Water_Pool/Kweebec_Oak_Water_Pool_005";

    public static final BuilderCodec<ZoneItemInteraction> CODEC = BuilderCodec
            .builder(ZoneItemInteraction.class, ZoneItemInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Utilise un objet des zones 2 et 3 (outre d'oasis, graine d'Écho).")
            .append(new KeyedCodec<>("Action", Codec.STRING), (i, v) -> i.action = v, i -> i.action)
            .documentation("Waterskin ou EchoSeed.")
            .add()
            .build();

    protected String action;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> ref = context.getOwningEntity();
        ItemStack held = context.getHeldItem();
        if (buffer == null || ref == null || !ref.isValid() || action == null || ItemStack.isEmpty(held)) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        PlayerRef player = buffer.getComponent(ref, PlayerRef.getComponentType());
        if (player == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        World world = buffer.getExternalData().getWorld();
        Vector3d at = player.getTransform().getPosition();
        if ("EchoSeed".equals(action)) {
            Integer forced = Climate.forced(player.getUuid());
            int zone = forced != null ? forced : Zones.at(world, at.x(), at.z());
            if (zone != 2) {
                NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(Climate.KEYS + "seed.wrongZone"),
                        NotificationStyle.Warning);
                context.getState().state = InteractionState.Failed;
                return;
            }
        }
        var inventory = InventoryComponent.getCombined(buffer, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        if (!inventory.removeItemStack(new ItemStack(held.getItemId(), 1), true, true).succeeded()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        String what = action;
        world.execute(() -> {
            if (!ref.isValid()) {
                return;
            }
            Store<EntityStore> store = world.getEntityStore().getStore();
            if ("Waterskin".equals(what)) {
                Effects.clear(store, ref, Climate.THIRST);
                Effects.apply(store, ref, Climate.QUENCHED, Climate.QUENCH_SECONDS);
                NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(Climate.KEYS + "waterskin"),
                        NotificationStyle.Success);
            } else if ("EchoSeed".equals(what)) {
                plantSeed(world, store, ref, player, at);
            }
        });
    }

    private static void plantSeed(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Vector3d at) {
        int x = (int) Math.floor(at.x()) + 4;
        int z = (int) Math.floor(at.z());
        Terrain terrain = new Terrain(world);
        int y = terrain.surface(x, z);
        if (y == Terrain.NONE) {
            y = (int) Math.floor(at.y()) - 1;
        }
        boolean pasted = VillageBuilder.paste(world, store, POOL, x, y, z, 0);
        ZoneRegistry.get(world).addShelter(x, y, z);
        int before = Reputations.peopleValue(store, ref, People.FERAN);
        if (before < Rank.TOLERE.min()) {
            Reputations.setPeople(store, ref, People.FERAN, Rank.TOLERE.min());
        }
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : graine d'Écho plantée en %d %d %d (bassin %s)", x, y, z,
                pasted ? "collé" : "non collé");
        player.sendMessage(Message.translation(Climate.KEYS + "seed.planted").param("x", x).param("y", y).param("z", z));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }
}
