package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.builtin.adventure.reputation.ReputationGroupComponent;
import com.hypixel.hytale.builtin.adventure.reputation.ReputationPlugin;
import com.hypixel.hytale.builtin.adventure.reputation.assets.ReputationGroup;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

/**
 * La réputation d'un joueur (GDD, Boucle de jeu, Jauges ; étape 4 du plan) : deux jauges personnelles.
 * <ul>
 *   <li><b>réputation de village</b>, gardée par le mod avec le joueur ({@link PeuplesPlayer}) : monte par les demandes
 *       remplies, descend quand on frappe ou tue un villageois et quand on casse un bâtiment du village ; elle décline
 *       vers « toléré » après {@value #ABSENCE_DAYS} jours de jeu d'absence, jamais en dessous ;</li>
 *   <li><b>réputation de peuple</b>, gardée par le ReputationPlugin vanilla (groupe {@code Nakasar_Peuples_<Peuple>},
 *       assets {@code Server/NPC/Reputation/Groups}) : un tiers de chaque gain ou perte de village. Le plugin vanilla
 *       en tire l'attitude de tous les PNJ du peuple envers le joueur, où qu'ils soient (villages vanilla compris).</li>
 * </ul>
 * Dans un village, le rang du joueur est celui de la plus haute des deux jauges : un ami du peuple est accueilli comme
 * tel dans un village où il n'a encore rien fait, un habitué garde son rang même si le peuple lui en veut ailleurs.
 * L'attitude des PNJ à moins de {@value #ATTITUDE_RADIUS} blocs d'un village suit ce rang
 * ({@link VillageAttitudeSystem}).
 *
 * <p>La valeur de peuple ne se lit et ne s'écrit par joueur que si le monde garde la réputation par joueur
 * (GameplayConfig {@code Reputation.ReputationStorage}, {@code PerPlayer} par défaut).
 */
public final class Reputations {

    public static final String KEYS = "nakasar_peuples.reputation.";
    /** Les PNJ du peuple à moins de cette distance (horizontale) d'un de ses villages suivent le rang de ce village. */
    public static final int ATTITUDE_RADIUS = 96;
    /** Jours de jeu d'absence avant le déclin de la réputation de village. */
    public static final int ABSENCE_DAYS = 10;
    /** Réputation perdue par jour d'absence au-delà de {@value #ABSENCE_DAYS} jours. */
    public static final int DECAY_PER_DAY = 10;
    /** La réputation de peuple reçoit 1/{@value #PEOPLE_SHARE} de chaque gain ou perte de village. */
    public static final int PEOPLE_SHARE = 3;

    /** Préfixe des groupes de réputation du mod : {@code Nakasar_Peuples_<Peuple>}. */
    private static final String GROUP_PREFIX = "Nakasar_Peuples_";

    private Reputations() {
    }

    /** Ce que vaut un joueur dans un village : ses deux jauges, et le rang retenu (la plus haute). */
    public record Standing(int village, int people, Rank rank) {
        public int value() {
            return Math.max(village, people);
        }

        public Rank villageRank() {
            return Rank.of(village);
        }

        public Rank peopleRank() {
            return Rank.of(people);
        }
    }

    // ---- Lecture ----

    /** Groupe de réputation vanilla du peuple. */
    public static String groupId(People people) {
        return GROUP_PREFIX + people.id();
    }

    /** Peuple d'un groupe de réputation du mod, ou null (groupe d'un autre mod, ou aucun). */
    public static People peopleOfGroup(String groupId) {
        if (groupId == null || !groupId.startsWith(GROUP_PREFIX)) {
            return null;
        }
        return People.byId(groupId.substring(GROUP_PREFIX.length()));
    }

    /** Réputation de peuple du joueur (ReputationPlugin vanilla ; 0 si le groupe manque). */
    public static int peopleValue(Store<EntityStore> store, Ref<EntityStore> ref, People people) {
        if (ref == null || !ref.isValid() || ReputationGroup.getAssetMap().getAsset(groupId(people)) == null) {
            return 0;
        }
        try {
            int value = ReputationPlugin.get().getReputationValue(store, ref, groupId(people));
            return value == ReputationPlugin.NO_REPUTATION_GROUP ? 0 : value;
        } catch (RuntimeException e) {
            return 0;
        }
    }

    /** Réputation de village du joueur. */
    public static int villageValue(PeuplesPlayer data, Village village) {
        return data == null || village == null ? 0 : data.villageReputation(village.id());
    }

    public static Standing standing(Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        int v = villageValue(data, village);
        int p = peopleValue(store, ref, village.people());
        return new Standing(v, p, Rank.of(Math.max(v, p)));
    }

    /** Rang du joueur dans le village. */
    public static Rank rank(Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        return village == null ? Rank.ETRANGER : standing(store, ref, village).rank();
    }

    /** Rang du joueur auprès du peuple (hors village). */
    public static Rank peopleRank(Store<EntityStore> store, Ref<EntityStore> ref, People people) {
        return Rank.of(peopleValue(store, ref, people));
    }

    /**
     * Attitude d'un PNJ du peuple envers un joueur près d'un village de ce peuple (rang du joueur dans ce village), ou
     * null : PNJ hors d'un village, cible qui n'est pas un joueur, PNJ d'aucun groupe du mod (le plugin vanilla décide
     * alors, avec la réputation de peuple).
     */
    public static Attitude villageAttitude(Store<EntityStore> store, Ref<EntityStore> npc, Ref<EntityStore> target,
                                           ComponentAccessor<EntityStore> accessor) {
        if (npc == null || target == null || !npc.isValid() || !target.isValid()) {
            return null;
        }
        ReputationGroupComponent group = accessor.getComponent(npc, ReputationGroupComponent.getComponentType());
        People people = group == null ? null : peopleOfGroup(group.getReputationGroupId());
        if (people == null || accessor.getComponent(target, Player.getComponentType()) == null) {
            return null;
        }
        TransformComponent transform = accessor.getComponent(npc, TransformComponent.getComponentType());
        if (transform == null) {
            return null;
        }
        Vector3d at = transform.getPosition();
        World world = store.getExternalData().getWorld();
        Village village = Villages.registry(world).nearestOf(people, at.x(), at.z(), ATTITUDE_RADIUS);
        if (village == null) {
            return null;
        }
        PeuplesPlayer data = accessor.getComponent(target, PeuplesPlayer.getComponentType());
        int value = Math.max(villageValue(data, village), peopleValue(store, target, people));
        return Rank.of(value).attitude();
    }

    // ---- Écriture ----

    /**
     * Ajoute `amount` (négatif : retire) à la réputation du joueur dans `village`, et un tiers à sa réputation de peuple.
     * Une notification donne le gain ou la perte et sa raison (`reasonKey`, ou rien) ; un changement de rang est
     * annoncé à part. Thread du monde.
     */
    public static void change(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                              int amount, String reasonKey) {
        change(world, store, ref, player, village, amount, reasonKey, true);
    }

    /** Comme {@link #change(World, Store, Ref, PlayerRef, Village, int, String)}, notification facultative (le rang est toujours annoncé). */
    public static void change(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                              int amount, String reasonKey, boolean notify) {
        if (amount == 0 || village == null || ref == null || !ref.isValid()) {
            return;
        }
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        Standing before = standing(store, ref, village);
        data.setVillageReputation(village.id(), Rank.clamp((long) before.village() + amount));
        data.setLastVisit(village.id(), GameClock.day(store));
        changePeople(store, ref, village.people(), amount / PEOPLE_SHARE);
        Standing after = standing(store, ref, village);
        int shown = after.village() - before.village();
        if (shown != 0 && notify) {
            Message m = Message.translation(KEYS + (shown > 0 ? "gained" : "lost"))
                    .param("amount", Math.abs(shown)).param("village", village.name())
                    .param("reason", reasonKey == null ? Message.empty() : Message.translation(reasonKey));
            NotificationUtil.sendNotification(player.getPacketHandler(), m, shown > 0 ? NotificationStyle.Success : NotificationStyle.Warning);
        }
        announceRank(player, village, before.rank(), after.rank());
    }

    /** Ajoute `amount` à la réputation de peuple du joueur (ReputationPlugin vanilla). Rend la nouvelle valeur. */
    public static int changePeople(Store<EntityStore> store, Ref<EntityStore> ref, People people, int amount) {
        if (amount == 0 || ref == null || !ref.isValid() || ReputationGroup.getAssetMap().getAsset(groupId(people)) == null) {
            return peopleValue(store, ref, people);
        }
        Player player = store.getComponent(ref, Player.getComponentType());
        if (player == null) {
            return 0;
        }
        try {
            return ReputationPlugin.get().changeReputation(player, groupId(people), amount, store);
        } catch (RuntimeException e) {
            PeuplesPlugin.get().getLogger().atWarning().log("Peuples : réputation de peuple %s non modifiée (%s)", people.id(), e);
            return peopleValue(store, ref, people);
        }
    }

    /** Fixe la réputation de village du joueur (commande d'essai). */
    public static void setVillage(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, int value) {
        Rank before = rank(store, ref, village);
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        data.setVillageReputation(village.id(), Rank.clamp(value));
        data.setLastVisit(village.id(), GameClock.day(store));
        announceRank(player, village, before, rank(store, ref, village));
    }

    /** Fixe la réputation de peuple du joueur (commande d'essai). */
    public static void setPeople(Store<EntityStore> store, Ref<EntityStore> ref, People people, int value) {
        changePeople(store, ref, people, Rank.clamp(value) - peopleValue(store, ref, people));
    }

    /**
     * Le joueur entre dans le village : après plus de {@value #ABSENCE_DAYS} jours de jeu d'absence, sa réputation de
     * village recule de {@value #DECAY_PER_DAY} par jour en trop, sans descendre sous le rang toléré (GDD : « revenir
     * ne coûte qu'une ou deux demandes »). Le jour de la visite est noté.
     */
    public static void visit(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village) {
        if (ref == null || !ref.isValid()) {
            return;
        }
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        long today = GameClock.day(store);
        Long last = data.lastVisit(village.id());
        int value = data.villageReputation(village.id());
        if (last != null && today - last > ABSENCE_DAYS && value > Rank.TOLERE.min()) {
            long loss = Math.min(value - Rank.TOLERE.min(), (today - last - ABSENCE_DAYS) * (long) DECAY_PER_DAY);
            if (loss > 0) {
                Rank before = rank(store, ref, village);
                data.setVillageReputation(village.id(), (int) (value - loss));
                player.sendMessage(Message.translation(KEYS + "decay").param("village", village.name())
                        .param("days", today - last).param("amount", loss));
                announceRank(player, village, before, rank(store, ref, village));
            }
        }
        data.setLastVisit(village.id(), today);
    }

    private static void announceRank(PlayerRef player, Village village, Rank before, Rank after) {
        if (before == after) {
            return;
        }
        boolean up = after.ordinal() > before.ordinal();
        Message m = Message.translation(KEYS + (up ? "rankUp" : "rankDown")).param("village", village.name())
                .param("rank", Message.translation(after.nameKey()))
                .param("people", Message.translation(village.people().nameKey()));
        player.sendMessage(m);
        player.sendMessage(Message.translation(KEYS + "perks").param("perks", Message.translation(after.perksKey())));
        NotificationUtil.sendNotification(player.getPacketHandler(), m, up ? NotificationStyle.Success : NotificationStyle.Danger);
    }

    // ---- Affichage ----

    /** « Ami (260 / 500) » : rang et progression vers le suivant. */
    public static Message describe(Rank rank, int value) {
        Rank next = rank.next();
        if (next == null) {
            return Message.translation(KEYS + "describeMax").param("rank", Message.translation(rank.nameKey())).param("value", value);
        }
        return Message.translation(KEYS + "describe").param("rank", Message.translation(rank.nameKey())).param("value", value)
                .param("next", next.min()).param("nextRank", Message.translation(next.nameKey()));
    }
}
