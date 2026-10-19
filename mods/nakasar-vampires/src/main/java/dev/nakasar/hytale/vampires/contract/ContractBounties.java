package dev.nakasar.hytale.vampires.contract;

import com.hypixel.hytale.builtin.portals.resources.PortalWorld;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Prime des contrats de chasseurs : quand la cible d'un contrat meurt dans son mini-fragment (type de portail
 * {@code Nakasar_Contract_*}, voir {@code tools/generate_contracts.py}), chaque joueur présent dans le fragment reçoit
 * la prime dans son inventaire (au sol s'il est plein) et un message. La progression des chasseurs passe par des
 * objets que chacun garde : en groupe, tout le monde repart avec son trophée.
 *
 * <p>Une seule prime par fragment : la cible revient au bout de 30 minutes (marqueur d'apparition), après la fin du
 * contrat (15 minutes), mais on ne paie de toute façon pas deux fois le même monde.
 */
public final class ContractBounties extends DeathSystems.OnDeathSystem {

    private static final String FANG = "Nakasar_Trophy_Vampire_Fang";
    private static final String SILVER = "Ingredient_Bar_Silver";
    private static final String SHARD = "Ingredient_Rune_Shard";

    /** Contrat : type de portail, rôle de la cible, prime par joueur, clé du message. */
    record Contract(String portalType, String targetRole, List<ItemStack> bounty, String messageKey) {
    }

    static final Map<String, Contract> CONTRACTS = Map.of(
            "Nakasar_Contract_Farm", new Contract("Nakasar_Contract_Farm", "Nakasar_Zombie_Abomination", List.of(
                    new ItemStack("Nakasar_Trophy_Abomination_Heart", 1), new ItemStack(FANG, 1),
                    new ItemStack(SILVER, 2), new ItemStack(SHARD, 2)),
                    "nakasar_hunters.contract.farm.fulfilled"),
            "Nakasar_Contract_Pumpkin", new Contract("Nakasar_Contract_Pumpkin", "Nakasar_Giant_Pumpkin", List.of(
                    new ItemStack("Nakasar_Trophy_Pumpkin_Seed", 1), new ItemStack(FANG, 1),
                    new ItemStack(SILVER, 2), new ItemStack(SHARD, 2)),
                    "nakasar_hunters.contract.pumpkin.fulfilled"),
            "Nakasar_Contract_Garrison", new Contract("Nakasar_Contract_Garrison", "Nakasar_Guard_Captain", List.of(
                    new ItemStack("Nakasar_Trophy_Captain_Insignia", 1), new ItemStack(FANG, 2),
                    new ItemStack(SILVER, 3), new ItemStack(SHARD, 3), new ItemStack("Rock_Gem_Topaz", 1)),
                    "nakasar_hunters.contract.garrison.fulfilled"));

    private static final Set<World> PAID = Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>()));

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store,
                                 CommandBuffer<EntityStore> buffer) {
        PortalWorld portal = store.getResource(PortalWorld.getResourceType());
        if (portal == null || !portal.exists() || portal.getPortalType() == null) {
            return;
        }
        Contract contract = CONTRACTS.get(portal.getPortalType().getId());
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        if (contract == null || npc == null || !contract.targetRole().equals(npc.getRoleName())) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (!PAID.add(world)) {
            return;
        }
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> playerRef = player.getReference();
            if (playerRef == null || !playerRef.isValid()) {
                continue;
            }
            var inventory = InventoryComponent.getCombined(buffer, playerRef, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            for (ItemStack stack : contract.bounty()) {
                SimpleItemContainer.addOrDropItemStack(buffer, playerRef, inventory,
                        new ItemStack(stack.getItemId(), stack.getQuantity()));
            }
            player.sendMessage(Message.translation(contract.messageKey()));
        }
    }

    public static void clearAll() {
        PAID.clear();
    }
}
