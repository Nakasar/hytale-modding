package dev.nakasar.hytale.runes.interaction;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

import java.util.concurrent.TimeUnit;

/**
 * {@code "Type": "Nakasar_DrainBeam"} : fait voyager un système de particules de la cible vers le lanceur,
 * pas à pas, pour montrer ce qui est dérobé (rune Vol de vie). Les positions sont relues à chaque pas :
 * le filet suit le lanceur s'il bouge.
 *
 * <p>Clés JSON :
 * <ul>
 *   <li>{@code SystemId} (string, requis) : système de particules joué à chaque pas ;</li>
 *   <li>{@code Steps} (int, défaut 8) : nombre de pas entre la cible et le lanceur ;</li>
 *   <li>{@code StepDelay} (float, défaut 0.04) : secondes entre deux pas ;</li>
 *   <li>{@code HeightOffset} (float, défaut 1.0) : hauteur au-dessus des pieds (torse).</li>
 * </ul>
 * Purement visuel : ne change jamais l'état de la chaîne.
 */
public class DrainBeamInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_DrainBeam";

    public static final BuilderCodec<DrainBeamInteraction> CODEC = BuilderCodec
            .builder(DrainBeamInteraction.class, DrainBeamInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Fait voyager un systeme de particules de la cible vers le lanceur.")
            .append(new KeyedCodec<>("SystemId", Codec.STRING), (i, v) -> i.systemId = v, i -> i.systemId)
            .documentation("Systeme de particules joue a chaque pas.")
            .add()
            .append(new KeyedCodec<>("Steps", Codec.INTEGER), (i, v) -> i.steps = v, i -> i.steps)
            .documentation("Nombre de pas entre la cible et le lanceur.")
            .add()
            .append(new KeyedCodec<>("StepDelay", Codec.FLOAT), (i, v) -> i.stepDelay = v, i -> i.stepDelay)
            .documentation("Secondes entre deux pas.")
            .add()
            .append(new KeyedCodec<>("HeightOffset", Codec.FLOAT), (i, v) -> i.heightOffset = v, i -> i.heightOffset)
            .documentation("Hauteur (blocs) au-dessus des pieds des deux entites.")
            .add()
            .build();

    protected String systemId;
    protected int steps = 8;
    protected float stepDelay = 0.04f;
    protected float heightOffset = 1.0f;

    public DrainBeamInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> target = context.getTargetEntity();
        Ref<EntityStore> caster = AbilityAttributes.caster(context);
        if (systemId == null || systemId.isBlank() || buffer == null || steps <= 0
                || target == null || !target.isValid() || caster == null || !caster.isValid() || target.equals(caster)) {
            return;
        }
        World world = buffer.getExternalData().getWorld();
        long delayMs = Math.max(1, Math.round(stepDelay * 1000));
        // Premier pas tout de suite (sur la cible), les suivants sur le thread du monde.
        step(buffer, target, caster, 0);
        for (int i = 1; i <= steps; i++) {
            int index = i;
            world.scheduleAfter(() -> {
                if (target.isValid() && caster.isValid()) {
                    step(world.getEntityStore().getStore(), target, caster, index);
                }
            }, delayMs * i, TimeUnit.MILLISECONDS);
        }
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement : les particules sont envoyées aux joueurs proches.
    }

    private void step(CommandBuffer<EntityStore> buffer, Ref<EntityStore> target, Ref<EntityStore> caster, int index) {
        Vector3d position = interpolate(
                buffer.getComponent(target, TransformComponent.getComponentType()),
                buffer.getComponent(caster, TransformComponent.getComponentType()), index);
        if (position != null) {
            ParticleUtil.spawnParticleEffect(systemId, position, buffer);
        }
    }

    private void step(Store<EntityStore> store, Ref<EntityStore> target, Ref<EntityStore> caster, int index) {
        Vector3d position = interpolate(
                store.getComponent(target, TransformComponent.getComponentType()),
                store.getComponent(caster, TransformComponent.getComponentType()), index);
        if (position != null) {
            ParticleUtil.spawnParticleEffect(systemId, position, store);
        }
    }

    private Vector3d interpolate(TransformComponent from, TransformComponent to, int index) {
        if (from == null || to == null) {
            return null;
        }
        double t = (double) index / steps;
        return new Vector3d(from.getPosition()).lerp(to.getPosition(), t).add(0, heightOffset, 0);
    }
}
