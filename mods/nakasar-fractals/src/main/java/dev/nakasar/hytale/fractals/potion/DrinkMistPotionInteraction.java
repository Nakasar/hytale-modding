package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.potion.MistPotions.Kind;

/**
 * {@code "Type": "Nakasar_Fractal_DrinkMistPotion"} : fin de la chaîne de boisson d'une potion des Brumes. Ajoute les
 * piles au joueur ({@link MistPotionState}, {@value MistPotions#MAX_STACKS} au plus) et remet la durée à 1 h ; les
 * effets suivent au prochain passage de {@link MistPotionSystem}. Échoue (la potion n'est pas retirée) si le type est
 * inconnu, si ce n'est pas un joueur ou hors des fractales et de l'Observatoire ({@link MistPotions#kept}).
 *
 * <p>Clés JSON : {@code Potion} (string) : {@code Offensive}, {@code Mobility} ou {@code Defensive} ; {@code Stacks}
 * (int, 1 par défaut) : piles ajoutées (5 pour une grande potion).
 */
public class DrinkMistPotionInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_DrinkMistPotion";

    public static final BuilderCodec<DrinkMistPotionInteraction> CODEC = BuilderCodec
            .builder(DrinkMistPotionInteraction.class, DrinkMistPotionInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Boit une potion des Brumes : piles ajoutées et duree remise a 1 h.")
            .append(new KeyedCodec<>("Potion", Codec.STRING), (i, v) -> i.potion = v, i -> i.potion)
            .documentation("Type de potion : Offensive, Mobility ou Defensive.")
            .add()
            .append(new KeyedCodec<>("Stacks", Codec.INTEGER), (i, v) -> i.stacks = v == null ? 1 : v, i -> i.stacks)
            .documentation("Piles ajoutees (1 pour la petite potion, 5 pour la grande).")
            .add()
            .build();

    protected String potion;
    protected int stacks = 1;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> player = context.getOwningEntity();
        Kind kind = Kind.of(potion);
        PlayerRef playerRef = buffer == null || player == null || !player.isValid() ? null
                : buffer.getComponent(player, PlayerRef.getComponentType());
        if (playerRef == null || kind == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        // Sur le fil du monde, hors du tampon : un premier état créé par le tampon ne serait visible qu'au vidage, et deux
        // gorgées finies dans le même tick en créeraient chacune un.
        int added = Math.max(1, stacks);
        World world = buffer.getExternalData().getWorld();
        if (!MistPotions.kept(world)) {
            // Dans le monde, la potion serait aussitôt retirée (MistPotionSystem) : refusée, elle n'est pas consommée.
            playerRef.sendMessage(Message.translation(MistPotions.MESSAGES + "refused"));
            context.getState().state = InteractionState.Failed;
            return;
        }
        world.execute(() -> {
            if (!player.isValid()) {
                return;
            }
            Store<EntityStore> store = world.getEntityStore().getStore();
            int now = store.ensureAndGetComponent(player, MistPotionState.getComponentType()).drink(kind, added);
            playerRef.sendMessage(Message.translation(MistPotions.MESSAGES + "drink").param("name", kind.displayName())
                    .param("stacks", now).param("max", MistPotions.MAX_STACKS));
        });
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
