package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/**
 * {@code "Type": "Nakasar_Fractal_Pull"} : attire la cible du boss vers lui (Vieux Tom, Inclassable). La chaîne JSON
 * l'annonce d'abord (marque au-dessus de la cible) ; au moment du tirage, la cible à moins de {@code Range} blocs part
 * vers le boss, assez vite pour finir à {@code StopDistance} blocs de lui, avec {@code Particle} sur elle.
 */
public class PullInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_Pull";

    public static final BuilderCodec<PullInteraction> CODEC = BuilderCodec
            .builder(PullInteraction.class, PullInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Attire la cible verrouillee vers le lanceur.")
            .append(new KeyedCodec<>("Range", Codec.FLOAT), (i, v) -> i.range = v, i -> i.range).add()
            .append(new KeyedCodec<>("StopDistance", Codec.FLOAT), (i, v) -> i.stop = v, i -> i.stop).add()
            .append(new KeyedCodec<>("Up", Codec.FLOAT), (i, v) -> i.up = v, i -> i.up).add()
            .append(new KeyedCodec<>("Particle", Codec.STRING), (i, v) -> i.particle = v, i -> i.particle).add()
            .build();

    private float range = 20f;
    private float stop = 2.5f;
    private float up = 4f;
    private String particle;

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        if (buffer == null || caster == null || !caster.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }
        Ref<EntityStore> target = TelegraphInteraction.target(caster, context, buffer);
        Vector3d from = Telegraphs.position(buffer, caster);
        Vector3d at = Telegraphs.position(buffer, target);
        if (from == null || at == null || at.distance(from) > range) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        double distance = Math.max(0, Telegraphs.horizontal(at, from) - stop);
        double a = Telegraphs.angle(at, from);
        // Vitesse horizontale qui couvre la distance pendant un saut d'environ 0,8 s.
        double speed = Math.min(24, distance / 0.8);
        Vector3d push = new Vector3d(Math.cos(a) * speed, up, Math.sin(a) * speed);
        world.execute(() -> {
            var store = world.getEntityStore().getStore();
            Velocity velocity = target.isValid() ? store.getComponent(target, Velocity.getComponentType()) : null;
            if (velocity != null) {
                velocity.addInstruction(push, null, ChangeVelocityType.Set);
            }
            if (particle != null && !particle.isBlank()) {
                Vector3d p = Telegraphs.position(store, target);
                if (p != null) {
                    Telegraphs.particle(store, particle, new Vector3d(p).add(0, 1, 0), 1f);
                }
            }
        });
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }
}
