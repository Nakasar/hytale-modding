package dev.nakasar.hytale.runes.interaction;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.data.AbilityAttributeBinding;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * {@code "Type": "Nakasar_RootNpc"} : immobilise l'IA du PNJ ciblé pendant {@code Duration} secondes en lui
 * posant le composant {@link Frozen} (celui de {@code /npc freeze}), puis le retire à l'expiration.
 *
 * <p>Un effet de statut avec {@code MovementEffects.DisableAll} n'arrête que les joueurs (leur mouvement
 * est piloté par le client) ; l'IA d'un PNJ continue de se déplacer. Cette interaction complète donc
 * l'{@code ApplyEffect} de la rune Chaînes spectrales : chaque mécanisme est sans effet sur l'autre type
 * d'entité, on applique les deux.
 *
 * <p>Clés JSON : {@code Duration} (float, défaut 3) et {@code DurationAttribute} (string). Sans PNJ en
 * cible, l'interaction ne fait rien et laisse la chaîne continuer.
 */
public class RootNpcInteraction extends SimpleInstantInteraction implements AbilityAttributeBinding {

    public static final String TYPE_ID = "Nakasar_RootNpc";

    public static final BuilderCodec<RootNpcInteraction> CODEC = BuilderCodec
            .builder(RootNpcInteraction.class, RootNpcInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Gele l'IA du PNJ cible pendant Duration secondes (composant Frozen), sans effet sur un joueur.")
            .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
            .documentation("Duree en secondes.")
            .add()
            .append(new KeyedCodec<>("DurationAttribute", Codec.STRING), (i, v) -> i.durationAttribute = v, i -> i.durationAttribute)
            .documentation("Attribut d'ability qui remplace Duration quand le lancer en porte un.")
            .add()
            .build();

    /** Échéance (nanoTime) du gel par entité, pour ne pas dégeler trop tôt quand deux gels se chevauchent. */
    private static final Map<Ref<EntityStore>, Long> EXPIRIES = new ConcurrentHashMap<>();

    protected float duration = 3f;
    protected String durationAttribute;

    public RootNpcInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> target = context.getTargetEntity();
        if (buffer == null || target == null || !target.isValid()) {
            return;
        }
        NPCEntity npc = buffer.getComponent(target, NPCEntity.getComponentType());
        if (npc == null) {
            return; // joueur ou autre entité : l'effet de statut s'en charge
        }
        float seconds = AbilityAttributes.resolve(context, AbilityAttributes.caster(context), buffer, durationAttribute, duration);
        if (seconds <= 0) {
            return;
        }

        World world = buffer.getExternalData().getWorld();
        long expiry = System.nanoTime() + (long) (seconds * 1_000_000_000L);
        EXPIRIES.merge(target, expiry, Math::max);

        if (buffer.getComponent(target, Frozen.getComponentType()) == null) {
            buffer.addComponent(target, Frozen.getComponentType(), Frozen.get());
        }

        long delayMs = (long) Math.ceil(seconds * 1000) + 50;
        world.scheduleAfter(() -> world.execute(() -> unfreeze(world, target)), delayMs, TimeUnit.MILLISECONDS);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    @Override
    public void collectAbilityAttributes(Consumer<String> out) {
        AbilityAttributeBinding.collect(out, durationAttribute);
    }

    private static void unfreeze(World world, Ref<EntityStore> target) {
        Long expiry = EXPIRIES.get(target);
        if (expiry != null && System.nanoTime() < expiry - 10_000_000L) {
            return; // un gel plus long a été posé entre-temps, sa propre tâche s'en chargera
        }
        EXPIRIES.remove(target);
        if (!target.isValid()) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        store.tryRemoveComponent(target, Frozen.getComponentType());
    }

    /** Oublie les échéances en cours (arrêt du plugin). Les composants restants partent avec le monde. */
    public static void clearAll() {
        EXPIRIES.clear();
    }
}
