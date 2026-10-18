package dev.nakasar.hytale.vampires.pumpkin;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * {@code "Type": "Nakasar_RootTrap"} : fait jaillir une vrille aux pieds de l'entité ciblée (le {@code HitEntity}
 * d'un {@code Selector}) et l'immobilise tant que cette vrille vit (piège de la citrouille géante).
 *
 * <p>La vrille est un PNJ à part entière ({@code TendrilRole}) avec ses propres points de vie : la victime (ou un
 * allié) la détruit en un ou deux coups, ce qui la libère. Un joueur est immobilisé par l'effet de statut
 * {@code EffectId} ({@code MovementEffects.DisableAll}), un PNJ par le composant {@link Frozen} (l'effet n'arrête
 * pas l'IA). On surveille chaque piège toutes les {@value #POLL_MS} ms : vrille morte ou disparue, victime morte, ou
 * {@code MaxDuration} écoulée (la vrille est alors retirée) libèrent la victime. À chaque passage on reconduit
 * l'immobilisation : l'effet du joueur ne dure que {@value #EFFECT_SECONDS} s (un joueur déconnecté en plein piège
 * n'en garde presque rien) et le gel d'un PNJ est reposé si un autre sort l'a retiré (fin des Chaînes spectrales).
 *
 * <p>La vrille n'est pas sauvegardée ({@code NonSerialized}) et la victime porte {@link RootTrapped}, qui retire le
 * gel posé par le piège si elle quitte le monde en plein piège ({@link RootTrapUnloadSystem}).
 *
 * <p>Sont épargnés : le lanceur, ses alliés (mobs du fragment ; sous Domination, son dominateur et les autres PNJ
 * du même maître), une victime déjà prise et les vrilles.
 *
 * <p>Clés JSON : {@code TendrilRole} (string, défaut {@code Nakasar_Pumpkin_Tendril}), {@code EffectId}
 * (string, défaut {@code Nakasar_Tendril_Rooted}), {@code MaxDuration} (float, défaut 20).
 */
public class RootTrapInteraction extends SimpleInstantInteraction {

    public static final String TYPE_ID = "Nakasar_RootTrap";

    public static final BuilderCodec<RootTrapInteraction> CODEC = BuilderCodec
            .builder(RootTrapInteraction.class, RootTrapInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Fait jaillir une vrille (PNJ) aux pieds de la cible et l'immobilise tant que la vrille vit.")
            .append(new KeyedCodec<>("TendrilRole", Codec.STRING), (i, v) -> i.tendrilRole = v, i -> i.tendrilRole)
            .documentation("Role du PNJ vrille.")
            .add()
            .append(new KeyedCodec<>("EffectId", Codec.STRING), (i, v) -> i.effectId = v, i -> i.effectId)
            .documentation("Effet de statut qui immobilise un joueur.")
            .add()
            .append(new KeyedCodec<>("MaxDuration", Codec.FLOAT), (i, v) -> i.maxDuration = v, i -> i.maxDuration)
            .documentation("Duree maximale du piege en secondes ; la vrille est retiree ensuite.")
            .add()
            .build();

    private static final long POLL_MS = 250;
    private static final float EFFECT_SECONDS = 1f;

    /** Piège en cours par victime. */
    private static final Map<Ref<EntityStore>, Trap> TRAPS = new ConcurrentHashMap<>();

    private record Trap(Ref<EntityStore> tendril, boolean player, EntityEffect effect, long deadline) {
    }

    protected String tendrilRole = "Nakasar_Pumpkin_Tendril";
    protected String effectId = "Nakasar_Tendril_Rooted";
    protected float maxDuration = 20f;

    public RootTrapInteraction() {
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        CommandBuffer<EntityStore> buffer = context.getCommandBuffer();
        Ref<EntityStore> owner = context.getOwningEntity();
        Ref<EntityStore> caster = owner != null && owner.isValid() ? owner : context.getEntity();
        Ref<EntityStore> victim = context.getTargetEntity();
        if (buffer == null || victim == null || !victim.isValid() || victim.equals(caster) || TRAPS.containsKey(victim)
                || buffer.getComponent(victim, DeathComponent.getComponentType()) != null
                || isTendril(victim, buffer)
                || (caster != null && caster.isValid() && isAlly(caster, victim, buffer))) {
            return;
        }
        TransformComponent transform = buffer.getComponent(victim, TransformComponent.getComponentType());
        if (transform == null) {
            return;
        }
        Vector3d feet = new Vector3d(transform.getPosition());
        Rotation3f rotation = new Rotation3f(transform.getRotation());
        boolean player = buffer.getComponent(victim, Player.getComponentType()) != null;
        if (!player && buffer.getComponent(victim, NPCEntity.getComponentType()) == null) {
            return; // ni joueur ni PNJ (objet au sol, projectile…)
        }
        World world = buffer.getExternalData().getWorld();
        // Le store est en plein traitement : on fait apparaître la vrille juste après.
        world.execute(() -> spring(world, victim, player, feet, rotation));
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldownHandler) {
        // Serveur uniquement.
    }

    private void spring(World world, Ref<EntityStore> victim, boolean player, Vector3d feet, Rotation3f rotation) {
        if (!victim.isValid() || TRAPS.containsKey(victim)) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, tendrilRole, null, feet, rotation);
        if (spawned == null || spawned.first() == null) {
            VampiresPlugin.get().getLogger().atWarning().log("%s : impossible de faire apparaître '%s'", TYPE_ID, tendrilRole);
            return;
        }
        Ref<EntityStore> tendril = spawned.first();
        // Jamais sauvegardée : un chunk déchargé en plein piège ne ramène pas de vrille orpheline.
        store.ensureAndGetComponent(tendril, EntityStore.REGISTRY.getNonSerializedComponentType());

        EntityEffect effect = null;
        if (player) {
            effect = EntityEffect.getAssetMap().getAsset(effectId);
            if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("%s : effet '%s' introuvable", TYPE_ID, effectId);
            }
        }
        store.ensureAndGetComponent(victim, RootTrapped.getComponentType());
        Trap trap = new Trap(tendril, player, effect, System.nanoTime() + (long) (maxDuration * 1_000_000_000L));
        TRAPS.put(victim, trap);
        hold(store, victim, trap);
        world.scheduleAfter(() -> watch(world, victim), POLL_MS, TimeUnit.MILLISECONDS);
    }

    /** (Re)pose l'immobilisation : effet court pour un joueur, gel pour un PNJ s'il n'est plus gelé. */
    private static void hold(Store<EntityStore> store, Ref<EntityStore> victim, Trap trap) {
        if (trap.player()) {
            EffectControllerComponent effects = store.getComponent(victim, EffectControllerComponent.getComponentType());
            if (trap.effect() != null && effects != null) {
                effects.addEffect(victim, trap.effect(), EFFECT_SECONDS, OverlapBehavior.OVERWRITE, store);
            }
        } else if (store.getComponent(victim, Frozen.getComponentType()) == null) {
            // Gel absent (jamais posé, ou retiré par la fin des Chaînes spectrales) : c'est désormais le nôtre.
            // Déjà gelé par quelqu'un d'autre (/npc freeze) : on ne touche pas à son gel.
            store.ensureAndGetComponent(victim, Frozen.getComponentType());
            RootTrapped marker = store.getComponent(victim, RootTrapped.getComponentType());
            if (marker != null) {
                marker.frozenByUs = true;
            }
        }
    }

    /** Libère la victime quand sa vrille n'est plus là ; sinon repasse plus tard. Tourne sur le thread du monde. */
    private static void watch(World world, Ref<EntityStore> victim) {
        Trap trap = TRAPS.get(victim);
        if (trap == null) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        boolean tendrilAlive = alive(trap.tendril(), store);
        boolean expired = System.nanoTime() >= trap.deadline();
        if (tendrilAlive && alive(victim, store) && !expired) {
            hold(store, victim, trap);
            world.scheduleAfter(() -> watch(world, victim), POLL_MS, TimeUnit.MILLISECONDS);
            return;
        }
        TRAPS.remove(victim);
        if (tendrilAlive) {
            store.removeEntity(trap.tendril(), RemoveReason.REMOVE);
        }
        release(store, victim, trap);
    }

    private static void release(Store<EntityStore> store, Ref<EntityStore> victim, Trap trap) {
        if (!victim.isValid()) {
            return;
        }
        if (trap.effect() != null) {
            int index = EntityEffect.getAssetMap().getIndex(trap.effect().getId());
            EffectControllerComponent effects = store.getComponent(victim, EffectControllerComponent.getComponentType());
            if (effects != null && effects.hasEffect(index)) {
                effects.removeEffect(victim, index, store);
            }
        }
        RootTrapped marker = store.getComponent(victim, RootTrapped.getComponentType());
        if (marker != null && marker.frozenByUs) {
            store.tryRemoveComponent(victim, Frozen.getComponentType());
        }
        store.tryRemoveComponent(victim, RootTrapped.getComponentType());
    }

    private static boolean alive(Ref<EntityStore> ref, Store<EntityStore> store) {
        return ref.isValid() && store.getComponent(ref, DeathComponent.getComponentType()) == null;
    }

    /**
     * Allié du lanceur : sous Domination, son maître et les autres PNJ du même maître (et non plus ses anciens
     * alliés du fragment) ; sinon, les autres mobs du fragment.
     */
    private static boolean isAlly(Ref<EntityStore> caster, Ref<EntityStore> victim, CommandBuffer<EntityStore> buffer) {
        Attitude domination = Allegiances.dominationAttitude(caster, victim, buffer);
        if (domination != null) {
            return domination == Attitude.FRIENDLY;
        }
        return Allegiances.bothInFaction(caster, victim, buffer);
    }

    private boolean isTendril(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        NPCEntity npc = buffer.getComponent(ref, NPCEntity.getComponentType());
        return npc != null && tendrilRole.equals(npc.getRoleName());
    }

    /** Oublie les pièges en cours (arrêt du plugin). Les vrilles et les gels partent avec le monde. */
    public static void clearAll() {
        TRAPS.clear();
    }
}
