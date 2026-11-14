package dev.nakasar.hytale.peuples.trork;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.village.People;

/**
 * La Peinture de guerre (étape 7 ; GDD, Progression des zones : objet de passage de la route trork). Le chef trork la
 * donne au champion de son peuple. L'utiliser (clic secondaire) la met ou l'ôte ; elle reste mise (drapeau
 * {@value #FLAG} du joueur, sauvegardé) et se voit : teinte ocre rouge et icône d'effet ({@value #EFFECT}, entretenus
 * par {@link WarPaintSystem}).
 * <ul>
 *   <li>hors d'un camp, les Trorks ne sont plus hostiles au joueur peint (au moins neutres : ils le saluent) ;</li>
 *   <li>les Kweebecs voient le joueur peint un rang plus bas (une échoppe ou une étape de chaîne peut se fermer).</li>
 * </ul>
 * Les pillards d'un raid restent hostiles (raid/RaidAttitudeSystem, priorité 80).
 */
public final class WarPaint {

    public static final String ITEM = "Nakasar_Peuples_War_Paint";
    public static final String EFFECT = "Nakasar_Peuples_War_Paint";
    /** Drapeau du joueur : peinture mise. */
    public static final String FLAG = "Trork_War_Paint";
    public static final String KEYS = "nakasar_peuples.warPaint.";

    private WarPaint() {
    }

    /** Vrai si le joueur `ref` porte la peinture. */
    public static boolean worn(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref) {
        if (ref == null || !ref.isValid()) {
            return false;
        }
        PeuplesPlayer data = accessor.getComponent(ref, PeuplesPlayer.getComponentType());
        return data != null && data.hasFlag(FLAG);
    }

    /** Rang `rank` vu par le peuple `people` : un cran plus bas chez les Kweebecs si le joueur est peint. */
    public static Rank adjust(Rank rank, People people, ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref) {
        if (people != People.KWEEBEC || rank == Rank.HONNI || !worn(accessor, ref)) {
            return rank;
        }
        return Rank.values()[rank.ordinal() - 1];
    }

    /**
     * Attitude d'un Trork hors d'un camp envers le joueur `target` : neutre au lieu d'hostile s'il est peint, sinon null
     * (le ReputationPlugin vanilla décide avec la réputation de peuple).
     */
    public static Attitude wildAttitude(Store<EntityStore> store, Ref<EntityStore> target, People people,
                                        ComponentAccessor<EntityStore> accessor) {
        if (people != People.TRORK || !worn(accessor, target)) {
            return null;
        }
        Attitude attitude = Rank.of(Reputations.peopleValue(store, target, people)).attitude();
        return attitude == Attitude.HOSTILE || attitude == Attitude.IGNORE ? Attitude.NEUTRAL : attitude;
    }

    /** Met ou ôte la peinture ; rend vrai si elle est mise. Thread du monde. */
    public static boolean toggle(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, PlayerRef player) {
        PeuplesPlayer data = PeuplesPlayer.ensure(accessor, ref);
        boolean on = !data.hasFlag(FLAG);
        data.setFlag(FLAG, on);
        sync(accessor, ref, on);
        NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(KEYS + (on ? "on" : "off")),
                on ? NotificationStyle.Warning : NotificationStyle.Default);
        return on;
    }

    /** Met l'effet visible d'accord avec le drapeau. */
    static void sync(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> ref, boolean on) {
        EffectControllerComponent effects = accessor.getComponent(ref, EffectControllerComponent.getComponentType());
        EntityEffect effect = EntityEffect.getAssetMap().getAsset(EFFECT);
        int index = EntityEffect.getAssetMap().getIndexOrDefault(EFFECT, -1);
        if (effects == null || effect == null || index < 0) {
            if (effect == null) {
                PeuplesPlugin.get().getLogger().atWarning().log("Peuples : effet %s introuvable", EFFECT);
            }
            return;
        }
        boolean has = effects.hasEffect(index);
        if (on && !has) {
            effects.addInfiniteEffect(ref, index, effect, accessor);
        } else if (!on && has) {
            effects.removeEffect(ref, index, accessor);
        }
    }
}
