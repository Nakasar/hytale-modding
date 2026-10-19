package dev.nakasar.hytale.vampires.contract;

import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventManager;
import com.hypixel.hytale.builtin.adventure.worldevents.context.ContextKey;
import com.hypixel.hytale.builtin.adventure.worldevents.context.IntervalContext;
import com.hypixel.hytale.builtin.adventure.worldevents.context.PrefabPasteContext;
import com.hypixel.hytale.builtin.adventure.worldevents.event.WorldEvent;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.BlockPosition;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.ItemUtils;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.CombinedItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.breach.HunterBreachStarter;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * {@code "Type": "Nakasar_ClaimBreachContract"} : le tableau des chasseurs d'une brèche porte une seule prime (le
 * premier contrat) pour tout le serveur. Le premier joueur qui l'utilise la reçoit ; les suivants sont prévenus
 * qu'elle est déjà prise et qu'il faut attendre la brèche suivante.
 *
 * <p>La prise est notée dans le contexte de l'évènement de la brèche ({@code Nakasar_Hunter_Breach}, ou sa version de
 * test) dont le campement est le plus proche du joueur, sous la clé {@value #CLAIM_KEY} (un {@link IntervalContext}
 * vanilla, seul moyen d'y ranger une valeur sans type à nous). Ce contexte est sauvegardé avec l'évènement (un
 * redémarrage du serveur ne rend pas la prime) et vidé quand l'évènement repart de zéro, c'est-à-dire à la fermeture
 * du campement : la brèche suivante a donc de nouveau sa prime. Un tableau posé hors d'une brèche (à la main) garde
 * sa prise en mémoire, par position, jusqu'au prochain démarrage.
 *
 * <p>Sac plein : rien n'est donné ni pris (la prime reste au tableau). Dans tous les cas la suite de la chaîne
 * ({@code Next}, la page de lore) s'ouvre.
 */
public class ClaimBreachContractInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_ClaimBreachContract";
    static final String CLAIM_KEY = "Nakasar_BreachContractClaimed";
    private static final ContextKey CLAIM = ContextKey.of(CLAIM_KEY);
    /** Le tableau est dans le campement (rayon 8) : l'évènement dont le prefab est posé à moins de cette distance. */
    private static final double CAMP_RANGE = 32;
    private static final String MESSAGES = "nakasar_hunters.board.";

    public static final BuilderCodec<ClaimBreachContractInteraction> CODEC = BuilderCodec
            .builder(ClaimBreachContractInteraction.class, ClaimBreachContractInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Donne la prime du tableau (une seule par brèche, pour tous les joueurs).")
            .append(new KeyedCodec<>("ItemId", Codec.STRING), (i, v) -> i.itemId = v, i -> i.itemId)
            .documentation("Id de l'objet donné.").add()
            .build();

    /** Tableaux hors brèche déjà vidés, par monde et par position. */
    private static final Map<World, Set<Long>> LOOSE_BOARDS = Collections.synchronizedMap(new WeakHashMap<>());

    private String itemId;

    public ClaimBreachContractInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getEntity();
        if (buffer == null || player == null || !player.isValid() || itemId == null
                || Item.getAssetMap().getAsset(itemId) == null) {
            return;
        }
        PlayerRef playerRef = buffer.getComponent(player, PlayerRef.getComponentType());
        TransformComponent transform = buffer.getComponent(player, TransformComponent.getComponentType());
        if (playerRef == null || transform == null) {
            return;
        }
        Vector3d position = transform.getPosition();
        WorldEvent breach = nearestBreach(buffer.getResource(WorldEventManager.getResourceType()), position);
        World world = buffer.getExternalData().getWorld();
        BlockPosition target = context.getTargetBlock();
        if (breach == null && target == null) {
            // Tableau hors brèche sans bloc visé : rien pour l'identifier, donc pas de prime à suivre.
            return;
        }
        long board = target != null ? boardKey(target) : 0L;
        if (breach != null ? breach.context.has(CLAIM, IntervalContext.class) : looseClaimed(world, board)) {
            playerRef.sendMessage(Message.translation(MESSAGES + "taken"));
            return;
        }
        CombinedItemContainer inventory = InventoryComponent.getCombined(buffer, player, InventoryComponent.EVERYTHING);
        ItemStack bounty = new ItemStack(itemId, 1);
        // Sac plein : interactivelyPickupItem jetterait l'objet au sol ; la prime reste au tableau.
        if (!inventory.canAddItemStack(bounty)) {
            playerRef.sendMessage(Message.translation(MESSAGES + "full"));
            return;
        }
        if (breach != null) {
            IntervalContext claimed = new IntervalContext();
            claimed.set(1f);
            breach.context.put(CLAIM, claimed);
        } else {
            LOOSE_BOARDS.computeIfAbsent(world, w -> Collections.synchronizedSet(new HashSet<>())).add(board);
        }
        ItemUtils.interactivelyPickupItem(player, bounty, position, buffer);
        playerRef.sendMessage(Message.translation(MESSAGES + "claimed"));
    }

    /** Évènement de brèche (normal ou de test) dont le campement posé est le plus proche, à moins de CAMP_RANGE. */
    static WorldEvent nearestBreach(WorldEventManager events, Vector3d position) {
        if (events == null) {
            return null;
        }
        WorldEvent[] best = {null};
        double[] bestDistance = {CAMP_RANGE * CAMP_RANGE};
        for (String asset : new String[]{HunterBreachStarter.EVENT, HunterBreachStarter.EVENT + "_Test"}) {
            for (WorldEvent event : events.allOf(asset)) {
                event.context.forEach(PrefabPasteContext.class, event, position, (paste, e, p) -> {
                    double dx = paste.origin().x() + 0.5 - p.x();
                    double dz = paste.origin().z() + 0.5 - p.z();
                    double distance = dx * dx + dz * dz;
                    if (distance < bestDistance[0]) {
                        bestDistance[0] = distance;
                        best[0] = e;
                    }
                });
            }
        }
        return best[0];
    }

    private static long boardKey(BlockPosition block) {
        int x = block.x;
        int y = block.y;
        int z = block.z;
        return ((long) x & 0x3FFFFFFL) << 38 | ((long) z & 0x3FFFFFFL) << 12 | ((long) y & 0xFFFL);
    }

    private static boolean looseClaimed(World world, long board) {
        Set<Long> claimed = LOOSE_BOARDS.get(world);
        return claimed != null && claimed.contains(board);
    }

    public static void clearAll() {
        LOOSE_BOARDS.clear();
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
