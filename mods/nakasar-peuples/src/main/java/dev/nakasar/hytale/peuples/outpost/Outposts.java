package dev.nakasar.hytale.peuples.outpost;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.trork.WarPaint;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNames;
import dev.nakasar.hytale.peuples.zone.ZoneRegistry;

import java.util.ArrayList;
import java.util.List;

/**
 * L'avant-poste du champion (étape 9, GDD « Récompenses », maquette avant_poste.png).
 * <ul>
 *   <li>Un joueur qui devient Champion d'un peuple reçoit une fois une Pierre de fondation (drapeau
 *   {@code Foundation_<peuple>}) ;</li>
 *   <li>utilisée en main, elle ouvre {@link OutpostPage} là où il se tient : il choisit l'avant-poste d'un peuple dont il
 *   est Champion (les Trorks acceptent aussi la Peinture de guerre) puis « Fonder » ; la pierre est prise et l'avant-poste
 *   attend ses colons ;</li>
 *   <li>au matin suivant (6 h d'un jour plus tard), le plan du peuple est bâti au palier 0 à cet endroit, sous un nom tiré
 *   par le peuple : c'est un village ordinaire qui grandit avec ses chantiers ;</li>
 *   <li>si la fondation échoue (site pris entre-temps, chunks non chargés), la pierre est rendue (au retour du joueur
 *   s'il est absent).</li>
 * </ul>
 * Une seule fondation en attente par joueur. Tout se passe sur le thread du monde.
 */
public final class Outposts {

    public static final String STONE = "Nakasar_Peuples_Foundation_Stone";
    public static final String KEYS = "nakasar_peuples.outpost.";
    public static final String FLAG_PREFIX = "Foundation_";

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();

    private Outposts() {
    }

    /** Toutes les 5 s (ZoneSystem) : pierres des nouveaux champions, remboursements, colons du matin. */
    public static void step(World world, Store<EntityStore> store) {
        ZoneRegistry zones = ZoneRegistry.get(world);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            grantStones(store, ref, player);
            refund(world, store, ref, player, zones);
        }
        long day = GameClock.day(store);
        if (GameClock.hour(store) >= GameClock.MORNING) {
            for (Outpost o : new ArrayList<>(zones.outposts())) {
                if (o.waiting() && !o.building && day > o.day) {
                    build(world, o);
                }
            }
        }
    }

    private static void grantStones(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player) {
        PeuplesPlayer data = PeuplesPlayer.get(store, ref);
        for (People p : People.values()) {
            String flag = FLAG_PREFIX + p.id();
            if ((data != null && data.hasFlag(flag)) || Reputations.peopleRank(store, ref, p) != Rank.CHAMPION) {
                continue;
            }
            PeuplesPlayer.ensure(store, ref).setFlag(flag, true);
            data = PeuplesPlayer.get(store, ref);
            Requests.give(store, ref, new ItemStack(STONE, 1));
            NotificationUtil.sendNotification(player.getPacketHandler(),
                    Message.translation(KEYS + "stoneGiven").param("people", Message.translation(p.nameKey())),
                    NotificationStyle.Success);
            LOGGER.atInfo().log("Peuples : pierre de fondation donnée à %s (champion %s)", player.getUsername(), p.id());
        }
    }

    private static void refund(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, ZoneRegistry zones) {
        String uuid = player.getUuid().toString();
        zones.outposts().removeIf(o -> {
            if (!o.refund || !uuid.equals(o.owner)) {
                return false;
            }
            Requests.give(store, ref, new ItemStack(STONE, 1));
            return true;
        });
    }

    /** Vrai si le joueur remplit la condition de l'avant-poste de `people`. */
    public static boolean allowed(Store<EntityStore> store, Ref<EntityStore> ref, People people) {
        if (Reputations.peopleRank(store, ref, people) == Rank.CHAMPION) {
            return true;
        }
        return people == People.TRORK && WarPaint.worn(store, ref);
    }

    /** Fondation en attente de ce joueur, ou null. */
    public static Outpost pendingOf(World world, PlayerRef player) {
        String uuid = player.getUuid().toString();
        for (Outpost o : ZoneRegistry.get(world).outposts()) {
            if (o.waiting() && uuid.equals(o.owner)) {
                return o;
            }
        }
        return null;
    }

    /**
     * « Fonder » : vérifie la condition, l'écart avec les villages et la pierre, la prend et enregistre la fondation.
     * Rend vrai si l'avant-poste attend ses colons ; sinon le joueur a reçu le message d'échec.
     */
    public static boolean found(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, People people,
                                int x, int z) {
        if (people == null) {
            player.sendMessage(Message.translation(KEYS + "noChoice"));
            return false;
        }
        if (!allowed(store, ref, people)) {
            player.sendMessage(Message.translation(KEYS + "locked"));
            return false;
        }
        Outpost pending = pendingOf(world, player);
        if (pending != null) {
            player.sendMessage(Message.translation(KEYS + "alreadyPending").param("x", pending.x).param("z", pending.z));
            return false;
        }
        VillageLayout layout = VillageLayout.get(people.layout());
        if (layout == null) {
            player.sendMessage(Message.translation("nakasar_peuples.village.layoutMissing").param("layout", people.layout()));
            return false;
        }
        Village near = VillageBuilder.tooClose(world, layout, x, z);
        Outpost planned = plannedNear(world, layout, x, z);
        if (near != null || planned != null) {
            String name = near != null ? near.name() : planned.ownerName;
            double dx = (near != null ? near.x() : planned.x) - x;
            double dz = (near != null ? near.z() : planned.z) - z;
            player.sendMessage(Message.translation(KEYS + "tooClose").param("name", name == null ? "?" : name)
                    .param("distance", (int) Math.sqrt(dx * dx + dz * dz)).param("min", VillageBuilder.spacing(layout)));
            return false;
        }
        var inventory = InventoryComponent.getCombined(store, ref, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
        if (Requests.take(inventory, STONE, 1) < 1) {
            player.sendMessage(Message.translation(KEYS + "noStone"));
            return false;
        }
        Outpost o = new Outpost(people.id(), x, z, player.getUuid().toString(), player.getUsername(), GameClock.day(store));
        ZoneRegistry.get(world).outposts().add(o);
        NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation(KEYS + "pending")
                .param("people", Message.translation(people.nameKey())).param("x", x).param("z", z), NotificationStyle.Success);
        player.sendMessage(Message.translation(KEYS + "pending").param("people", Message.translation(people.nameKey()))
                .param("x", x).param("z", z));
        LOGGER.atInfo().log("Peuples : avant-poste %s prévu en %d %d par %s", people.id(), x, z, player.getUsername());
        return true;
    }

    /** Une autre fondation en attente trop proche de (x, z), ou null (deux pierres posées côte à côte). */
    private static Outpost plannedNear(World world, VillageLayout layout, int x, int z) {
        int min = VillageBuilder.spacing(layout);
        for (Outpost o : ZoneRegistry.get(world).outposts()) {
            double dx = o.x - x;
            double dz = o.z - z;
            if (o.waiting() && dx * dx + dz * dz < (double) min * min) {
                return o;
            }
        }
        return null;
    }

    /** Lance tout de suite les fondations en attente ({@code /village avantposte finir}) ; rend leur nombre. */
    public static int finishAll(World world) {
        int n = 0;
        for (Outpost o : new ArrayList<>(ZoneRegistry.get(world).outposts())) {
            if (o.waiting() && !o.building) {
                build(world, o);
                n++;
            }
        }
        return n;
    }

    /** Les avant-postes du monde (liste en lecture). */
    public static List<Outpost> all(World world) {
        return List.copyOf(ZoneRegistry.get(world).outposts());
    }

    private static void build(World world, Outpost o) {
        People people = People.byId(o.people);
        VillageLayout layout = people == null ? null : VillageLayout.get(people.layout());
        if (layout == null) {
            fail(world, o, Message.translation("nakasar_peuples.village.layoutMissing").param("layout", o.people));
            return;
        }
        o.building = true;
        String name = VillageNames.pick(world, people);
        VillageBuilder.generate(world, layout, name, o.x, o.z, false, result -> {
            o.building = false;
            if (result.village() == null) {
                fail(world, o, result.error());
                return;
            }
            Village v = result.village();
            o.villageId = v.id();
            LOGGER.atInfo().log("Peuples : avant-poste %s fondé : %s en %d %d (%s)", o.people, v.name(), v.x(), v.z(), o.ownerName);
            PlayerRef owner = online(world, o.owner);
            if (owner != null) {
                Message msg = Message.translation(KEYS + "built").param("name", v.name()).param("x", v.x()).param("z", v.z());
                NotificationUtil.sendNotification(owner.getPacketHandler(), msg, NotificationStyle.Success);
                owner.sendMessage(msg);
            }
        });
    }

    /**
     * Le colon d'un village au palier max part chercher les siens : la fondation attend le matin suivant comme un
     * avant-poste, sans pierre. Le site a déjà été examiné ({@code SiteRules}). Rend faux si le joueur a déjà une
     * fondation en attente (message envoyé).
     */
    public static boolean foundBySettler(World world, Store<EntityStore> store, PlayerRef player, Village home, int x, int z) {
        Outpost pending = pendingOf(world, player);
        if (pending != null) {
            player.sendMessage(Message.translation(KEYS + "alreadyPending").param("x", pending.x).param("z", pending.z));
            return false;
        }
        Outpost o = new Outpost(home.people().id(), x, z, player.getUuid().toString(), player.getUsername(), GameClock.day(store));
        o.from = home.id();
        ZoneRegistry.get(world).outposts().add(o);
        LOGGER.atInfo().log("Peuples : colon de %s : village %s prévu en %d %d par %s", home.name(), o.people, x, z, player.getUsername());
        return true;
    }

    private static void fail(World world, Outpost o, Message reason) {
        LOGGER.atWarning().log("Peuples : avant-poste %s en %d %d n'a pas pu être bâti", o.people, o.x, o.z);
        PlayerRef owner = online(world, o.owner);
        Message msg = Message.translation(KEYS + "failed").param("x", o.x).param("z", o.z)
                .param("reason", reason == null ? Message.raw("") : reason);
        if (o.from != null) {
            // Fondation d'un colon : pas de pierre à rendre, le colon rentre à son village et attendra un autre site.
            ZoneRegistry.get(world).outposts().remove(o);
            Settlers.returnHome(world, o.from);
            if (owner != null) {
                Message back = Message.translation(Settlers.KEYS + "failed").param("x", o.x).param("z", o.z)
                        .param("reason", reason == null ? Message.raw("") : reason);
                owner.sendMessage(back);
                NotificationUtil.sendNotification(owner.getPacketHandler(), back, NotificationStyle.Warning);
            }
            return;
        }
        if (owner != null && owner.getReference() != null && owner.getReference().isValid()) {
            Store<EntityStore> store = world.getEntityStore().getStore();
            Requests.give(store, owner.getReference(), new ItemStack(STONE, 1));
            ZoneRegistry.get(world).outposts().remove(o);
            owner.sendMessage(msg);
            NotificationUtil.sendNotification(owner.getPacketHandler(), msg, NotificationStyle.Warning);
        } else {
            o.refund = true;
        }
    }

    private static PlayerRef online(World world, String uuid) {
        if (uuid == null) {
            return null;
        }
        for (PlayerRef p : world.getPlayerRefs()) {
            if (uuid.equals(p.getUuid().toString())) {
                return p;
            }
        }
        return null;
    }
}
