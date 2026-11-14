package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Réputations croisées (étape 7 ; GDD, Progression des zones : « aider les Trorks coûte un rang chez les Kweebecs »).
 * Deux peuples rivaux ({@link People#rival()}) :
 * <ul>
 *   <li>chaque gain de réputation de village chez l'un retire la moitié ({@value #SHARE}) de ce gain à la réputation
 *       de peuple de l'autre ;</li>
 *   <li>étape 9 : un peuple allié ({@link People#ally()} : les Slothians pour les Feran et les Renoncés) gagne un
 *       quart de chaque gain, en réputation de peuple ;</li>
 *   <li>chaque étape de la chaîne de l'un (drapeau {@code <Peuple>_Chain_<n>}) fait perdre un rang chez l'autre :
 *       réputation de peuple et réputation de chacun de ses villages.</li>
 * </ul>
 */
public final class Rivals {

    /** Le rival perd 1/{@value #SHARE} de chaque gain. */
    public static final int SHARE = 2;
    /** Étape 9 : l'allié ({@link People#ally()}) gagne 1/{@value #ALLY_SHARE} de chaque gain, en réputation de peuple. */
    public static final int ALLY_SHARE = 4;
    private static final String CHAIN = "_Chain_";

    private Rivals() {
    }

    /** Le joueur a gagné `amount` de réputation de village chez `people`. */
    static void helped(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, People people, int amount) {
        People ally = people.ally();
        int gain = amount / ALLY_SHARE;
        if (ally != null && gain > 0) {
            Reputations.changePeople(store, ref, ally, gain);
            NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(Reputations.KEYS + "allyGain")
                    .param("amount", gain).param("people", Message.translation(ally.nameKey()))
                    .param("helped", Message.translation(people.nameKey())), NotificationStyle.Success);
        }
        People rival = people.rival();
        int loss = amount / SHARE;
        if (rival == null || loss <= 0) {
            return;
        }
        Reputations.changePeople(store, ref, rival, -loss);
        NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(Reputations.KEYS + "rivalLost")
                .param("amount", loss).param("people", Message.translation(rival.nameKey()))
                .param("helped", Message.translation(people.nameKey())), NotificationStyle.Warning);
    }

    /**
     * Le joueur vient de recevoir le drapeau `flag` : si c'est une étape de chaîne d'un peuple qui a un rival, il perd
     * un rang chez ce rival. Thread du monde.
     */
    public static void flagged(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, String flag) {
        int at = flag == null ? -1 : flag.indexOf(CHAIN);
        People people = at <= 0 ? null : People.byId(flag.substring(0, at));
        People rival = people == null ? null : people.rival();
        if (rival == null || ref == null || !ref.isValid()) {
            return;
        }
        Rank before = Reputations.peopleRank(store, ref, rival);
        int value = Reputations.peopleValue(store, ref, rival);
        Reputations.setPeople(store, ref, rival, rankDown(value));
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        for (Village village : Villages.registry(world).all()) {
            if (village.people() == rival) {
                data.setVillageReputation(village.id(), rankDown(Reputations.villageValue(data, village)));
            }
        }
        Rank after = Reputations.peopleRank(store, ref, rival);
        Message m = Message.translation(Reputations.KEYS + "rivalRank").param("people", Message.translation(rival.nameKey()))
                .param("helped", Message.translation(people.nameKey())).param("rank", Message.translation(after.nameKey()));
        player.sendMessage(m);
        NotificationUtil.sendNotification(player.getPacketHandler(), m, before == after ? NotificationStyle.Warning : NotificationStyle.Danger);
    }

    /** Valeur un rang plus bas : même place dans le rang d'en dessous, au plus juste sous son seuil ; Honni ne bouge plus. */
    static int rankDown(int value) {
        Rank rank = Rank.of(value);
        if (rank == Rank.HONNI) {
            return value;
        }
        Rank below = Rank.values()[rank.ordinal() - 1];
        int shifted = value - (rank.min() - below.min());
        return Math.max(below.min(), Math.min(rank.min() - 1, shifted));
    }
}
