package dev.nakasar.hytale.vampires.contract;

import com.hypixel.hytale.builtin.portals.resources.PortalWorld;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.modules.entity.item.ItemComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Prime des contrats de chasseurs : quand la cible d'un contrat meurt dans son mini-fragment (type de portail
 * {@code Nakasar_Contract_*}, voir {@code tools/generate_contracts.py}), elle lâche le sac de prime du contrat, un seul
 * pour tout le groupe, à côté de son butin habituel (trophée compris). Les joueurs présents sont prévenus.
 * Le sac s'ouvre avec {@link OpenBountyBagInteraction}.
 *
 * <p>Une seule prime par fragment : la cible revient au bout de 30 minutes (marqueur d'apparition), après la fin du
 * contrat (15 minutes), mais on ne paie de toute façon pas deux fois le même monde.
 */
public final class ContractBounties extends DeathSystems.OnDeathSystem {

    /** Contrat : rôle de la cible, sac de prime, clé du message. */
    record Contract(String targetRole, String bag, String messageKey) {
    }

    static final Map<String, Contract> CONTRACTS = Map.of(
            "Nakasar_Contract_Farm", new Contract("Nakasar_Zombie_Abomination", "Nakasar_Bounty_Bag_Farm",
                    "nakasar_hunters.contract.farm.fulfilled"),
            "Nakasar_Contract_Pumpkin", new Contract("Nakasar_Giant_Pumpkin", "Nakasar_Bounty_Bag_Pumpkin",
                    "nakasar_hunters.contract.pumpkin.fulfilled"),
            "Nakasar_Contract_Garrison", new Contract("Nakasar_Guard_Captain", "Nakasar_Bounty_Bag_Garrison",
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
        TransformComponent transform = buffer.getComponent(ref, TransformComponent.getComponentType());
        if (contract == null || npc == null || transform == null || !contract.targetRole().equals(npc.getRoleName())) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (!PAID.add(world)) {
            return;
        }
        Vector3d position = new Vector3d(transform.getPosition()).add(0, 1, 0);
        buffer.addEntities(ItemComponent.generateItemDrops(buffer, List.of(new ItemStack(contract.bag(), 1)),
                position, new Rotation3f(transform.getRotation())), AddReason.SPAWN);
        world.sendMessage(Message.translation(contract.messageKey()));
    }

    public static void clearAll() {
        PAID.clear();
    }
}
