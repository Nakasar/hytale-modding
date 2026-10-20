package dev.nakasar.hytale.fractals.progress;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * Dégâts d'agonie, une fois par seconde : chaque joueur sous l'effet {@value Agony#EFFECT} perd
 * {@link Agony#percentPerSecond} de ses PV maximum, multiplié par {@link Agony#factor} (sa résistance), en dégâts
 * {@value Agony#DAMAGE_CAUSE} qui passent les armures. Le joueur est prévenu une fois par application de l'effet :
 * part des PV perdue, sa résistance et la résistance conseillée.
 */
public final class AgonySystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 1f;
    private static final String MESSAGES = "nakasar_fractals_progress.agony.";
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());
    /** Joueurs déjà prévenus de l'application en cours, par monde. */
    private static final Map<World, Set<UUID>> NOTIFIED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        elapsed[0] = 0f;
        int effect = EntityEffect.getAssetMap().getIndexOrDefault(Agony.EFFECT, -1);
        if (effect < 0 || world.getPlayerRefs().isEmpty()) {
            return;
        }
        world.execute(() -> step(world, effect));
    }

    private static void step(World world, int effect) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Set<UUID> notified = NOTIFIED.computeIfAbsent(world, w -> new HashSet<>());
        Set<UUID> suffering = new HashSet<>();
        int level = Agony.levelOf(world);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                continue;
            }
            EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
            if (effects == null || !effects.hasEffect(effect)) {
                continue;
            }
            suffering.add(player.getUuid());
            int resistance = FractalProgress.resistance(store, ref);
            float part = Agony.percentPerSecond(level) * Agony.factor(level, resistance);
            if (notified.add(player.getUuid())) {
                player.sendMessage(message(level, resistance, part));
            }
            hurt(store, ref, part);
        }
        notified.retainAll(suffering);
    }

    private static Message message(int level, int resistance, float part) {
        if (level < Agony.FIRST_LEVEL) {
            return Message.translation(MESSAGES + "none").param("level", level);
        }
        String key = part <= 0f ? "resisted" : "hit";
        return Message.translation(MESSAGES + key).param("level", level)
                .param("percent", Math.round(part * 1000f) / 10f)
                .param("resistance", resistance).param("recommended", Agony.recommended(level));
    }

    private static void hurt(Store<EntityStore> store, Ref<EntityStore> ref, float part) {
        if (part <= 0f) {
            return;
        }
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        DamageCause cause = DamageCause.getAssetMap().getAsset(Agony.DAMAGE_CAUSE);
        if (health == null || cause == null) {
            return;
        }
        float amount = health.getMax() * part;
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(Agony.DAMAGE_CAUSE), cause, amount));
    }

    public static void clearAll() {
        NOTIFIED.clear();
    }
}
