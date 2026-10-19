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
import java.util.Locale;
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

    static final String PORTAL_PREFIX = "Nakasar_Contract_";

    /**
     * Rôle de la cible de chaque contrat, par nom court ({@code Nakasar_Contract_<X>}, {@code CONTRACTS} de
     * {@code tools/generate_contracts.py}). Le sac ({@code Nakasar_Bounty_Bag_<X>}) et le message
     * ({@code nakasar_hunters.contract.<x>.fulfilled}) se déduisent du nom court.
     */
    static final Map<String, String> TARGETS = Map.of(
            "Farm", "Nakasar_Zombie_Abomination",
            "Pumpkin", "Nakasar_Giant_Pumpkin",
            "Garrison", "Nakasar_Guard_Captain",
            "Crypt", "Nakasar_Enchanted_Armor",
            "Castle", "Nakasar_Spectre");

    /** Île des contrats ({@code generate_contracts.py}) : sol, rayon, et lieu de la cible où tombe le sac par défaut. */
    static final double GROUND_Y = 81;
    /** Profondeur sous le sol au-delà de laquelle une cible est tombée de l'île. */
    static final double UNDERGROUND_DEPTH = 24;
    static final double ISLAND_RADIUS = 112;
    static final Vector3d TARGET_SITE = new Vector3d(0, GROUND_Y + 1, -54);

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
        String portalId = portal.getPortalType().getId();
        if (portalId == null || !portalId.startsWith(PORTAL_PREFIX)) {
            return;
        }
        String contract = portalId.substring(PORTAL_PREFIX.length());
        String targetRole = TARGETS.get(contract);
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        TransformComponent transform = buffer.getComponent(ref, TransformComponent.getComponentType());
        if (targetRole == null || npc == null || transform == null || !targetRole.equals(npc.getRoleName())) {
            return;
        }
        World world = store.getExternalData().getWorld();
        if (!PAID.add(world)) {
            return;
        }
        Vector3d position = bagPosition(transform.getPosition());
        buffer.addEntities(ItemComponent.generateItemDrops(buffer, List.of(new ItemStack("Nakasar_Bounty_Bag_" + contract, 1)),
                position, new Rotation3f(transform.getRotation())), AddReason.SPAWN);
        world.sendMessage(Message.translation("nakasar_hunters.contract." + contract.toLowerCase(Locale.ROOT) + ".fulfilled"));
    }

    /**
     * Là où la cible est morte, sauf si elle est tombée de l'île (vide en dessous) : le sac tombe alors chez elle.
     * L'armure enchantée se bat dans la salle enterrée de la crypte (une dizaine de blocs sous le sol) : le seuil est
     * sous elle, et l'île a plus de 40 blocs d'épaisseur autour du lieu de la cible.
     */
    static Vector3d bagPosition(Vector3d death) {
        boolean offIsland = death.y() < GROUND_Y - UNDERGROUND_DEPTH || Math.hypot(death.x(), death.z()) > ISLAND_RADIUS - 4;
        return offIsland ? new Vector3d(TARGET_SITE) : new Vector3d(death).add(0, 1, 0);
    }

    public static void clearAll() {
        PAID.clear();
    }
}
