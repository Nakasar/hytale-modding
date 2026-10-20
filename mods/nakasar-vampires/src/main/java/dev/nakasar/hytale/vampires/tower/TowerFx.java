package dev.nakasar.hytale.vampires.tower;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.OverlapBehavior;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.VampiresPlugin;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Annonces et coups des combats de la Tour de l'Alchimiste (Kevin, 20 octobre 2026 : « lisibilité d'abord »).
 *
 * <ul>
 *   <li>{@link #circle} : petit cercle rouge qui se remplit jusqu'au coup ({@code Nakasar_Warning_<dixièmes>},
 *   tools/tower_warnings.py).</li>
 *   <li>{@link Telegraphs.Sweep} : cône (secteur) ou anneau rouge qui se charge d'un bord à l'autre (commun avec les
 *   élites du Comté).</li>
 *   <li>Coups en part de la vie maximale, effets, projection, sons.</li>
 * </ul>
 *
 * <p>Une zone rouge annonce toujours un effet négatif ; les autres couleurs (tools/tower_fx.py) disent l'élément ou un
 * soin.
 */
final class TowerFx {

    static final float WARNING_SCALE = Telegraphs.WARNING_SCALE;

    private TowerFx() {
    }

    /** Cercle rouge de `radius` blocs au sol en `at`, plein au bout de `seconds` (arrondi au dixième). */
    static void circle(Store<EntityStore> store, Vector3d at, double radius, float seconds) {
        Telegraphs.circle(store, at, radius, seconds);
    }

    static void particle(Store<EntityStore> store, String id, Vector3d at, float scale) {
        Telegraphs.particle(store, id, at, scale);
    }

    static void sound(Store<EntityStore> store, String id, Vector3d at) {
        Telegraphs.sound(store, id, at);
    }

    /** Part `fraction` de la vie maximale de `ref`, cause `causeId`, signée `source`. */
    static void damage(Store<EntityStore> store, Ref<EntityStore> ref, String causeId, float fraction, String source) {
        DamageCause cause = DamageCause.getAssetMap().getAsset(causeId);
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (cause == null || health == null || fraction <= 0f) {
            return;
        }
        float amount = (float) Math.ceil(health.getMax() * fraction);
        DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(source), cause, amount));
    }

    static void effect(Store<EntityStore> store, Ref<EntityStore> ref, String id, float seconds) {
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(id);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effect == null) {
            VampiresPlugin.get().getLogger().atWarning().log("Tour : effet '%s' introuvable", id);
            return;
        }
        if (effects != null) {
            effects.addEffect(ref, effect, seconds, OverlapBehavior.OVERWRITE, store);
        }
    }

    /** Projette `ref` vers le haut (pic de pierre). */
    static void launch(Store<EntityStore> store, Ref<EntityStore> ref, double up) {
        Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
        if (velocity != null) {
            velocity.addInstruction(new Vector3d(0, up, 0), null, ChangeVelocityType.Set);
        }
    }

    /** Joueurs vivants dans le cylindre de rayon `radius` posé en `at` (de 1 bloc dessous à 3 blocs dessus). */
    static List<Ref<EntityStore>> playersIn(World world, Store<EntityStore> store, Vector3d at, double radius) {
        List<Ref<EntityStore>> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d position = position(store, ref);
            if (position == null) {
                continue;
            }
            double dy = position.y() - at.y();
            if (horizontal(position, at) <= radius && dy >= -1 && dy <= 3) {
                out.add(ref);
            }
        }
        return out;
    }

    /** Position d'une entité vivante (null si elle est morte ou disparue). */
    static Vector3d position(Store<EntityStore> store, Ref<EntityStore> ref) {
        return Telegraphs.position(store, ref);
    }

    static double horizontal(Vector3d a, Vector3d b) {
        return Telegraphs.horizontal(a, b);
    }

    /** Angle horizontal de `p` vu de `center`, en radians (atan2(dz, dx), comme les secteurs de TowerLayout). */
    static double angle(Vector3d center, Vector3d p) {
        return Telegraphs.angle(center, p);
    }

    static long seconds(float s) {
        return Telegraphs.seconds(s);
    }
}
