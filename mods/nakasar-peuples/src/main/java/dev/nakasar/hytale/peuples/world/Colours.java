package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Les couleurs qu'un joueur porte (GDD de la conquête, « Le rôle du joueur ») : un seul village à la fois, au rang Ami,
 * changeable tous les {@value #CHANGE_DAYS} jours, au tableau du village (onglet Domaine). Porter les couleurs d'un
 * village, c'est agir en son nom : ses commandes dans un lieu-dit lui gagnent de l'influence, ses méfaits lui en
 * coûtent, il escorte ses ambassades et brode son blason sur les bannières vierges.
 *
 * <p>Sauvé dans les drapeaux du joueur : {@code Colours=<village>@<jour>}.
 */
public final class Colours {

    public static final int CHANGE_DAYS = 3;
    private static final String FLAG = "Colours=";

    private Colours() {
    }

    private static String flag(PeuplesPlayer data) {
        if (data == null) {
            return null;
        }
        for (String f : data.flags()) {
            if (f.startsWith(FLAG)) {
                return f;
            }
        }
        return null;
    }

    /** L'id du village dont le joueur porte les couleurs, ou null. */
    public static String villageId(Store<EntityStore> store, Ref<EntityStore> ref) {
        String f = ref == null || !ref.isValid() ? null : flag(PeuplesPlayer.get(store, ref));
        if (f == null) {
            return null;
        }
        int at = f.indexOf('@');
        String id = at < 0 ? f.substring(FLAG.length()) : f.substring(FLAG.length(), at);
        return id.isEmpty() ? null : id;
    }

    /** Le village dont le joueur porte les couleurs (s'il existe encore), ou null. */
    public static Village of(World world, Store<EntityStore> store, Ref<EntityStore> ref) {
        String id = villageId(store, ref);
        return id == null ? null : Villages.registry(world).byId(id);
    }

    public static boolean wears(Store<EntityStore> store, Ref<EntityStore> ref, Village v) {
        return v != null && v.id().equals(villageId(store, ref));
    }

    private static long since(PeuplesPlayer data) {
        String f = flag(data);
        int at = f == null ? -1 : f.indexOf('@');
        if (at < 0) {
            return Long.MIN_VALUE;
        }
        try {
            return Long.parseLong(f.substring(at + 1));
        } catch (NumberFormatException e) {
            return Long.MIN_VALUE;
        }
    }

    /** Prend (ou rend, si on les porte déjà) les couleurs du village. Rend le message à dire. */
    public static Message toggle(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v) {
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        long day = GameClock.day(store);
        if (wears(store, ref, v)) {
            String was = flag(data);
            data.setFlag(was, false);
            // Le délai court toujours depuis la prise des couleurs : les rendre ne permet pas d'en prendre d'autres aussitôt.
            data.setFlag(FLAG + was.substring(was.indexOf('@') < 0 ? was.length() : was.indexOf('@')), true);
            return Message.translation(Heraldry.KEYS + "colours.dropped").param("village", v.name());
        }
        if (!Reputations.rank(store, ref, v).atLeast(Rank.AMI)) {
            return Message.translation(Heraldry.KEYS + "colours.rank").param("village", v.name());
        }
        long since = since(data);
        if (since != Long.MIN_VALUE && day < since + CHANGE_DAYS) {
            return Message.translation(Heraldry.KEYS + "colours.wait").param("days", since + CHANGE_DAYS - day);
        }
        String old = flag(data);
        if (old != null) {
            data.setFlag(old, false);
        }
        data.setFlag(FLAG + v.id() + "@" + day, true);
        return Message.translation(Heraldry.KEYS + "colours.taken").param("village", v.name())
                .param("arms", Heraldry.of(world, v).name());
    }
}
