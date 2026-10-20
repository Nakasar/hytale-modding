package dev.nakasar.hytale.fractals.combat;

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
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Boss étourdi : son IA est gelée ({@link Frozen}) pendant quelques secondes et un effet de statut le montre
 * (étoiles au-dessus de la tête ; {@value #EFFECT} lui fait aussi subir 50 % de dégâts en plus). Sert aux fenêtres de
 * punition (barre de défiance brisée, charge dans un mur) et à la charge elle-même (l'IA ne doit pas reprendre la main
 * pendant que le Java déplace le boss). Copie d'{@code EliteStun} du mod Vampires.
 *
 * <p>Le gel n'est jamais sauvegardé utilement : il est retiré quand un PNJ du mod ({@value #ROLE_PREFIX}…) quitte le
 * monde et quand il est rechargé ({@link Unload}).
 */
public final class BossStun {

    /** Effet de statut d'étourdissement par défaut. */
    public static final String EFFECT = "Nakasar_Fractal_Stunned";
    /** Rôles qu'{@link Unload} dégèle : tous les PNJ du mod (le mod ne gèle que les siens). */
    public static final String ROLE_PREFIX = "Nakasar_Fractal_";

    /** Fin du gel par boss (System.nanoTime), sur le thread du monde. */
    private static final Map<Ref<EntityStore>, Long> UNTIL = new ConcurrentHashMap<>();

    private BossStun() {
    }

    /** Gèle le boss `seconds` secondes (prolonge un gel en cours) et pose l'effet `effectId` s'il est donné. */
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
                FractalsPlugin.get().getLogger().atWarning().log("Étourdissement : effet '%s' introuvable", effectId);
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

    /** Dégèle un PNJ du mod qui quitte le monde ou qui est rechargé gelé. */
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
            if (npc != null && npc.getRoleName() != null && npc.getRoleName().startsWith(ROLE_PREFIX)) {
                holder.tryRemoveComponent(Frozen.getComponentType());
            }
        }
    }
}
