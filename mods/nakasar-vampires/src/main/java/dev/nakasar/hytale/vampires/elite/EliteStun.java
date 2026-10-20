package dev.nakasar.hytale.vampires.elite;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.Frozen;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.telegraph.TelegraphSystem;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Élite étourdie : son IA est gelée ({@link Frozen}) pendant quelques secondes et un effet de statut le montre
 * (étoiles au-dessus de la tête ; {@code Nakasar_Elite_Stunned} lui fait aussi subir 50 % de dégâts en plus). Sert aux
 * fenêtres de punition : l'Abomination qui a chargé dans un poteau, le Capitaine pris de vertige après son tourbillon,
 * et à la charge elle-même (l'IA ne doit pas reprendre la main pendant que le Java la déplace).
 *
 * <p>Le gel n'est jamais sauvegardé utilement : il est retiré quand l'élite quitte le monde et quand elle est rechargée
 * ({@link Unload}).
 */
public final class EliteStun {

    /** Rôles que ce gel peut toucher (et qu'{@link Unload} dégèle). */
    public static final Set<String> ROLES = Set.of("Nakasar_Zombie_Abomination", "Nakasar_Guard_Captain");

    /** Fin du gel par élite (System.nanoTime), sur le thread du monde. */
    private static final Map<Ref<EntityStore>, Long> UNTIL = new ConcurrentHashMap<>();

    private EliteStun() {
    }

    /** Gèle l'élite `seconds` secondes (prolonge un gel en cours) et pose l'effet `effectId` s'il est donné. */
    public static void stun(World world, Store<EntityStore> store, Ref<EntityStore> ref, float seconds, String effectId) {
        if (ref == null || !ref.isValid()) {
            return;
        }
        long until = System.nanoTime() + Telegraphs.seconds(seconds);
        boolean watched = UNTIL.containsKey(ref);
        UNTIL.merge(ref, until, Math::max);
        store.ensureAndGetComponent(ref, Frozen.getComponentType());
        if (effectId != null && !effectId.isBlank()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(effectId);
            EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
            if (effect == null) {
                VampiresPlugin.get().getLogger().atWarning().log("Étourdissement : effet '%s' introuvable", effectId);
            } else if (effects != null) {
                effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
            }
        }
        if (!watched) {
            TelegraphSystem.start(world, (w, s, now) -> {
                Long end = UNTIL.get(ref);
                if (!ref.isValid()) {
                    UNTIL.remove(ref);
                    return true;
                }
                if (end != null && now < end) {
                    return false;
                }
                UNTIL.remove(ref);
                s.tryRemoveComponent(ref, Frozen.getComponentType());
                return true;
            });
        }
    }

    public static boolean isStunned(Ref<EntityStore> ref) {
        return UNTIL.containsKey(ref);
    }

    public static void clearAll() {
        UNTIL.clear();
    }

    /** Dégèle une élite de {@link #ROLES} qui quitte le monde ou qui est rechargée gelée. */
    public static final class Unload extends HolderSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return Frozen.getComponentType();
        }

        @Override
        public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
            if (reason == AddReason.LOAD) {
                unfreeze(holder);
            }
        }

        @Override
        public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
            unfreeze(holder);
        }

        private static void unfreeze(Holder<EntityStore> holder) {
            NPCEntity npc = holder.getComponent(NPCEntity.getComponentType());
            if (npc != null && ROLES.contains(npc.getRoleName())) {
                holder.tryRemoveComponent(Frozen.getComponentType());
            }
        }
    }
}
