package dev.nakasar.hytale.vampires.rune;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;
import org.joml.Vector4d;

/**
 * {@code "Type": "Nakasar_TeleportCasterToImpact"} : téléporte le propriétaire de la chaîne (le lanceur)
 * à la position de l'entité qui exécute la chaîne (le projectile).
 *
 * <p>À utiliser dans la chaîne {@code ProjectileHit} / {@code ProjectileMiss} d'un {@code ProjectileConfig}
 * lancé par {@code LaunchAbilityProjectile}. Clés JSON :
 * <ul>
 *   <li>{@code BackOffset} (float, défaut 0.6) : recule l'arrivée de N blocs vers le lanceur, pour ne pas
 *       finir dans le mur touché ;</li>
 *   <li>{@code VerticalOffset} (float, défaut 0.05) : léger décalage vertical à l'arrivée ;</li>
 *   <li>{@code MaxDistance} (float, défaut 0 = illimitée) : portée maximale ; un impact plus lointain
 *       ramène l'arrivée sur la droite lanceur → impact, à cette distance du lanceur.</li>
 * </ul>
 */
public class TeleportCasterToImpactInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_TeleportCasterToImpact";

    public static final BuilderCodec<TeleportCasterToImpactInteraction> CODEC = BuilderCodec
            .builder(TeleportCasterToImpactInteraction.class, TeleportCasterToImpactInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Teleporte le lanceur (entite proprietaire) a la position du projectile qui execute la chaine.")
            .append(new KeyedCodec<>("BackOffset", Codec.FLOAT),
                    (i, v) -> i.backOffset = v, i -> i.backOffset)
            .documentation("Distance (blocs) de recul de l'arrivee vers le lanceur, pour eviter de finir dans un mur.")
            .add()
            .append(new KeyedCodec<>("VerticalOffset", Codec.FLOAT),
                    (i, v) -> i.verticalOffset = v, i -> i.verticalOffset)
            .documentation("Decalage vertical ajoute a l'arrivee.")
            .add()
            .append(new KeyedCodec<>("MaxDistance", Codec.FLOAT),
                    (i, v) -> i.maxDistance = v, i -> i.maxDistance)
            .documentation("Portee maximale (blocs) de la teleportation ; 0 = illimitee.")
            .add()
            .build();

    protected float backOffset = 0.6f;
    protected float verticalOffset = 0.05f;
    protected float maxDistance = 0f;

    public TeleportCasterToImpactInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> projectile = context.getEntity();
        Ref<EntityStore> caster = context.getOwningEntity();
        if (buffer == null || caster == null || !caster.isValid() || projectile == null || !projectile.isValid()) {
            fail(context);
            return;
        }

        Vector3d target = impactPosition(context, buffer, projectile);
        if (target == null) {
            fail(context);
            return;
        }

        TransformComponent casterTransform = buffer.getComponent(caster, TransformComponent.getComponentType());
        Rotation3f rotation = casterTransform != null ? casterTransform.getRotation() : new Rotation3f();

        if (maxDistance > 0 && casterTransform != null) {
            Vector3d from = casterTransform.getPosition();
            Vector3d dir = new Vector3d(target).sub(from);
            double len = dir.length();
            if (len > maxDistance) {
                target.set(from).add(dir.mul(maxDistance / len));
            }
        }
        if (backOffset > 0 && casterTransform != null) {
            Vector3d from = casterTransform.getPosition();
            Vector3d dir = new Vector3d(target).sub(from);
            double len = dir.length();
            if (len > 1e-6) {
                // Recule d'au plus BackOffset, sans jamais dépasser le lanceur lui-même.
                dir.div(len).mul(Math.min(backOffset, len));
                target.sub(dir);
            }
        }
        target.add(0, verticalOffset, 0);

        Teleport teleport = Teleport.createForPlayer(target, rotation);
        HeadRotation head = buffer.getComponent(caster, HeadRotation.getComponentType());
        if (head != null) {
            teleport.setHeadRotation(head.getRotation());
        }
        buffer.putComponent(caster, Teleport.getComponentType(), teleport);
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Rien côté client : la chaîne d'un projectile est simulée serveur uniquement.
    }

    private static Vector3d impactPosition(InteractionContext context, CommandBuffer<EntityStore> buffer, Ref<EntityStore> projectile) {
        TransformComponent transform = buffer.getComponent(projectile, TransformComponent.getComponentType());
        if (transform != null) {
            return new Vector3d(transform.getPosition());
        }
        Vector4d hit = context.getMetaStore().getMetaObject(Interaction.HIT_LOCATION);
        if (hit != null) {
            return new Vector3d(hit.x, hit.y, hit.z);
        }
        return null;
    }

    private static void fail(InteractionContext context) {
        context.getState().state = InteractionState.Failed;
    }
}
