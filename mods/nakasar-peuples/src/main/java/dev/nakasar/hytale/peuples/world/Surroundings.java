package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Étape 2 : la vie autour du village, seulement sous les yeux d'un joueur (à moins de {@value #WATCH} blocs du cœur ;
 * rien n'est sauvé, tout se repose à son retour).
 * <ul>
 *   <li>Sorties : de {@value #OUT_FROM} h à {@value #OUT_TO} h, un villageois par palier (trois au plus) part cueillir,
 *       pêcher, couper du bois ou garder les bêtes à l'orée du village, travaille un moment puis rentre : ce qu'il
 *       rapporte entre au dépôt. Une sortie sur quatre croise un monstre (un pillard de la zone) : à défendre.</li>
 *   <li>Patrouilles : dès le palier 2, deux gardes font le tour du village ({@value #PATROL_OUT} blocs au-delà de son
 *       rayon). Pas pendant un raid (les gardes du raid sont au cœur).</li>
 *   <li>Enfants : un par palier (trois au plus), de jour et hors raid, jouent sur la place. On peut jouer à cache-cache
 *       avec eux une fois par jour : trois enfants à trouver en {@value #HIDE_SECONDS} s.</li>
 * </ul>
 */
public final class Surroundings {

    public static final int WATCH = 128;
    public static final int OUT_FROM = 8;
    public static final int OUT_TO = 18;
    public static final int PATROL_OUT = 20;
    public static final int HIDE_SECONDS = 180;
    public static final int HIDE_CHILDREN = 3;
    public static final int HIDE_REPUTATION = 10;
    public static final String KEYS = WorldLife.KEYS + "village.";
    public static final String CHILD_DIALOGUE = "Monde_Enfants";
    public static final String HIDE_FLAG = "HideSeek:";

    /** Les sorties : {clé, objet rapporté, nombre}. */
    /** Dialogue des villageois en sortie (tools/generate_world_life.py), un nœud par travail de {@link #JOBS}. */
    public static final String OUTING_DIALOGUE = "Monde_Sortie";

    private static final String[][] JOBS = {
            {"gather", "Ingredient_Fibre", "4"},
            {"fish", "Food_Fish_Raw", "2"},
            {"wood", "Ingredient_Stick", "6"},
            {"herd", "Food_Egg", "2"},
    };

    private static final class Outing {
        Ref<EntityStore> npc;
        Ref<EntityStore> monster;
        Vector3d target;
        int job;
        /** 0 aller, 1 au travail, 2 retour. */
        int phase;
        long until;
    }

    private static final class Life {
        final String village;
        final Outing[] outings = new Outing[3];
        final long[] nextOuting = new long[3];
        final List<Ref<EntityStore>> patrol = new ArrayList<>();
        int waypoint;
        final List<Ref<EntityStore>> children = new ArrayList<>();
        long nextPlay;
        boolean hiding;

        Life(String village) {
            this.village = village;
        }
    }

    private static final Map<String, Life> LIVES = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, String> CHILD_OF = Collections.synchronizedMap(new IdentityHashMap<>());

    private Surroundings() {
    }

    public static String outingRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Outing";
    }

    public static String childRole(People people) {
        return "Nakasar_Peuples_" + people.id() + "_Child";
    }

    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        int hour = GameClock.hour(store);
        boolean night = GameClock.isNight(store);
        long now = System.currentTimeMillis();
        for (Village v : Villages.registry(world).all()) {
            Life life = LIVES.get(v.id());
            boolean watched = WorldLife.near(players, v.x(), v.z(), WATCH);
            if (!watched) {
                if (life != null) {
                    clear(store, life);
                    LIVES.remove(v.id());
                }
                continue;
            }
            if (life == null) {
                life = new Life(v.id());
                LIVES.put(v.id(), life);
            }
            boolean raid = Raids.isActive(v);
            int slots = Math.max(1, Math.min(3, v.tier()));
            int radius = radius(v);
            outings(world, store, v, life, slots, radius, hour >= OUT_FROM && hour < OUT_TO && !raid, now);
            patrol(world, store, v, life, radius, v.tier() >= 2 && !raid);
            if (!life.hiding) {
                children(world, store, v, life, slots, !night && !raid, now);
            }
        }
    }

    private static int radius(Village v) {
        VillageLayout layout = Chantiers.layout(v);
        return layout == null ? Villages.RADIUS : layout.radius();
    }

    // ---- Sorties ----

    private static void outings(World world, Store<EntityStore> store, Village v, Life life, int slots, int radius, boolean open, long now) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        for (int i = 0; i < 3; i++) {
            Outing o = life.outings[i];
            if (o != null && (o.npc == null || !o.npc.isValid())) {
                // Mort en route (ou retiré) : rien n'est rapporté ; la bête repart avec lui.
                if (o.monster != null) {
                    WorldLife.remove(store, o.monster);
                }
                life.outings[i] = null;
                life.nextOuting[i] = now + 180_000L;
                continue;
            }
            if (o == null) {
                if (open && i < slots && now >= life.nextOuting[i] && WorldLife.budget(world, 2)) {
                    start(world, store, v, life, i, radius, random);
                }
                continue;
            }
            Vector3d at = Requests.position(store, o.npc);
            if (at == null) {
                continue;
            }
            if (o.phase == 0 && at.distanceSquared(o.target) <= 16) {
                o.phase = 1;
                o.until = now + random.nextLong(40_000L, 80_000L);
                if (random.nextInt(4) == 0) {
                    monster(world, store, v, o, i);
                }
            } else if (o.phase == 1 && now >= o.until && (o.monster == null || !o.monster.isValid())) {
                o.phase = 2;
                WorldLife.leash(store, o.npc, home(world, v));
            } else if (o.phase == 2 && v.horizontalDistanceSquared(at.x(), at.z()) <= 100) {
                String[] job = JOBS[o.job];
                ItemContainer chest = Villages.depositChest(world, v);
                if (chest != null) {
                    chest.addItemStack(new ItemStack(job[1], Integer.parseInt(job[2])));
                }
                WorldLife.remove(store, o.npc);
                life.outings[i] = null;
                life.nextOuting[i] = now + random.nextLong(90_000L, 180_000L);
            }
        }
        if (!open) {
            for (int i = 0; i < 3; i++) {
                Outing o = life.outings[i];
                if (o != null && o.phase < 2 && (o.monster == null || !o.monster.isValid())) {
                    o.phase = 2; // le soir (ou un raid) : tout le monde rentre
                    WorldLife.leash(store, o.npc, home(world, v));
                }
            }
        }
    }

    private static void start(World world, Store<EntityStore> store, Village v, Life life, int slot, int radius, ThreadLocalRandom random) {
        double angle = random.nextDouble() * Math.PI * 2;
        int d = radius + 10 + random.nextInt(20);
        Vector3d target = WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(angle) * d), v.z() + (int) Math.round(Math.sin(angle) * d), 8);
        Vector3d from = WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(angle) * 8), v.z() + (int) Math.round(Math.sin(angle) * 8), 6);
        if (target == null || from == null) {
            life.nextOuting[slot] = System.currentTimeMillis() + 60_000L;
            return;
        }
        Ref<EntityStore> npc = WorldLife.spawn(store, outingRole(v.people()), from, (float) angle);
        if (npc == null) {
            life.nextOuting[slot] = System.currentTimeMillis() + 300_000L;
            return;
        }
        WorldLife.leash(store, npc, target);
        Outing o = new Outing();
        o.npc = npc;
        o.target = target;
        o.job = random.nextInt(JOBS.length);
        WorldLife.talker(npc, (w, s, p, pr, n) -> outingTalk(w, s, p, pr, n, JOBS[o.job][0]));
        life.outings[slot] = o;
    }

    /** Dialogue d'un villageois en sortie : il dit où il va, dans la fenêtre de dialogue (nœud = son travail). */
    private static void outingTalk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef,
                                   Ref<EntityStore> npc, String job) {
        Dialogue dialogue = Dialogue.get(OUTING_DIALOGUE);
        if (dialogue == null || dialogue.node(job) == null) {
            playerRef.sendMessage(Message.translation(KEYS + "outing." + job));
            return;
        }
        Dialogues.openPage(world, store, player, playerRef, dialogue, npc, job, List.of());
    }

    private static void monster(World world, Store<EntityStore> store, Village v, Outing o, int slot) {
        String role = Raids.raiders(v.people())[0];
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Vector3d at = WorldLife.ground(world, (int) o.target.x() + random.nextInt(-10, 11), (int) o.target.z() + random.nextInt(-10, 11), 6);
        Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, role, at, 0f);
        if (ref == null) {
            return;
        }
        String side = "OUT:" + v.id() + ":" + slot;
        WorldLife.side(ref, side, 1);
        WorldLife.side(o.npc, side, 0);
        WorldLife.leash(store, ref, o.target);
        o.monster = ref;
        WorldLife.announce(world, store, o.target.x(), o.target.z(), WorldLife.REAL_RANGE,
                Message.translation(KEYS + "monster").param("village", v.name()), NotificationStyle.Warning);
    }

    private static Vector3d home(World world, Village v) {
        Vector3d h = WorldLife.ground(world, v.x() + 3, v.z() + 3, 6);
        return h == null ? new Vector3d(v.x() + 0.5, v.y() + 1, v.z() + 0.5) : h;
    }

    // ---- Patrouilles ----

    private static void patrol(World world, Store<EntityStore> store, Village v, Life life, int radius, boolean on) {
        life.patrol.removeIf(r -> !r.isValid());
        if (!on) {
            life.patrol.forEach(r -> WorldLife.remove(store, r));
            life.patrol.clear();
            return;
        }
        int r = radius + PATROL_OUT;
        if (life.patrol.isEmpty()) {
            if (!WorldLife.budget(world, 2)) {
                return;
            }
            Vector3d at = waypoint(world, v, r, life.waypoint);
            if (at == null) {
                return;
            }
            for (int i = 0; i < 2; i++) {
                Ref<EntityStore> ref = WorldLife.spawn(store, Relations.fighterRole(v.people()),
                        new Vector3d(at.x() + i * 1.5, at.y(), at.z()), 0f);
                if (ref != null) {
                    life.patrol.add(ref);
                }
            }
            return;
        }
        Vector3d lead = Requests.position(store, life.patrol.get(0));
        Vector3d next = waypoint(world, v, r, life.waypoint);
        if (lead != null && next != null && lead.distanceSquared(next) <= 25) {
            life.waypoint = (life.waypoint + 1) % 8;
            next = waypoint(world, v, r, life.waypoint);
        }
        if (next != null) {
            for (int i = 0; i < life.patrol.size(); i++) {
                WorldLife.leash(store, life.patrol.get(i), new Vector3d(next.x() + i * 1.5, next.y(), next.z()));
            }
        }
    }

    private static Vector3d waypoint(World world, Village v, int r, int i) {
        double a = i * Math.PI / 4;
        return WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(a) * r), v.z() + (int) Math.round(Math.sin(a) * r), 6);
    }

    // ---- Enfants ----

    private static void children(World world, Store<EntityStore> store, Village v, Life life, int count, boolean out, long now) {
        life.children.removeIf(r -> {
            if (r.isValid()) {
                return false;
            }
            CHILD_OF.remove(r);
            return true;
        });
        if (!out) {
            removeChildren(store, life);
            return;
        }
        ThreadLocalRandom random = ThreadLocalRandom.current();
        if (life.children.size() < count && WorldLife.budget(world, 1)) {
            Vector3d at = WorldLife.ground(world, v.x() + random.nextInt(-8, 9), v.z() + random.nextInt(-8, 9), 6);
            Ref<EntityStore> ref = at == null ? null : WorldLife.spawn(store, childRole(v.people()), at, 0f);
            if (ref != null) {
                WorldLife.talker(ref, Surroundings::talk);
                CHILD_OF.put(ref, v.id());
                life.children.add(ref);
            }
        }
        if (now >= life.nextPlay) {
            // Ils changent de jeu : un nouveau coin de la place.
            life.nextPlay = now + random.nextLong(20_000L, 40_000L);
            for (Ref<EntityStore> ref : life.children) {
                Vector3d to = WorldLife.ground(world, v.x() + random.nextInt(-10, 11), v.z() + random.nextInt(-10, 11), 4);
                if (to != null) {
                    WorldLife.leash(store, ref, to);
                }
            }
        }
    }

    private static void removeChildren(Store<EntityStore> store, Life life) {
        for (Ref<EntityStore> r : life.children) {
            CHILD_OF.remove(r);
            WorldLife.remove(store, r);
        }
        life.children.clear();
    }

    static void talk(World world, Store<EntityStore> store, Ref<EntityStore> player, PlayerRef playerRef, Ref<EntityStore> npc) {
        Dialogue dialogue = Dialogue.get(CHILD_DIALOGUE);
        if (dialogue != null) {
            Dialogues.openPage(world, store, player, playerRef, dialogue, npc);
        }
    }

    /** Village de l'enfant à qui parle le joueur. */
    static Village childVillage(World world, Ref<EntityStore> npc) {
        String id = npc == null ? null : CHILD_OF.get(npc);
        return id == null ? null : Villages.registry(world).byId(id);
    }

    /** Cache-cache : les enfants se cachent, le joueur a {@value #HIDE_SECONDS} s pour les trouver (une fois par jour). */
    static boolean hideAndSeek(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village v) {
        Life life = v == null ? null : LIVES.get(v.id());
        if (life == null || life.hiding) {
            DialogueSpeech.say(player, Message.translation(KEYS + "hideBusy"));
            return false;
        }
        long day = GameClock.day(store);
        PeuplesPlayer data = PeuplesPlayer.ensure(store, ref);
        String flag = HIDE_FLAG + v.id() + ":" + day;
        if (data.hasFlag(flag) || Hunts.playing(player.getUuid())) {
            DialogueSpeech.say(player, Message.translation(KEYS + "hideTired"));
            return false;
        }
        for (String f : new ArrayList<>(data.flags())) {
            if (f.startsWith(HIDE_FLAG + v.id() + ":")) {
                data.setFlag(f, false);
            }
        }
        data.setFlag(flag, true);
        removeChildren(store, life);
        life.hiding = true;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        int radius = Math.min(radius(v), 32);
        List<Hunts.Spot> spots = new ArrayList<>();
        for (int i = 0; i < HIDE_CHILDREN; i++) {
            double a = random.nextDouble() * Math.PI * 2;
            int d = 10 + random.nextInt(Math.max(1, radius - 8));
            Vector3d at = WorldLife.ground(world, v.x() + (int) Math.round(Math.cos(a) * d), v.z() + (int) Math.round(Math.sin(a) * d), 6);
            Ref<EntityStore> child = at == null ? null : WorldLife.spawn(store, childRole(v.people()), at, 0f);
            if (child == null) {
                continue;
            }
            spots.add(new Hunts.Spot(child, at, () -> WorldLife.remove(store, child)));
        }
        if (spots.isEmpty()) {
            life.hiding = false;
            return false;
        }
        DialogueSpeech.say(player, Message.translation(KEYS + "hideStart").param("count", spots.size()).param("seconds", HIDE_SECONDS));
        UUID uuid = player.getUuid();
        Hunts.start("hide:" + v.id(), player, spots, HIDE_SECONDS, KEYS + "hideFound", (w, s, p, won) -> {
            life.hiding = false;
            if (p == null) {
                return; // joueur parti : les enfants reviennent jouer près du cœur
            }
            Message m = Message.translation(KEYS + (won ? "hideWon" : "hideLost"));
            p.sendMessage(m);
            NotificationUtil.sendNotification(p.getPacketHandler(), m, won ? NotificationStyle.Success : NotificationStyle.Default);
            Ref<EntityStore> pr = p.getReference();
            if (won && pr != null && pr.isValid() && p.getUuid().equals(uuid)) {
                Requests.give(s, pr, new ItemStack(v.people().favorItem(), 1));
                Reputations.change(w, s, pr, p, v, HIDE_REPUTATION, KEYS + "hideReason");
            }
        });
        return true;
    }

    private static void clear(Store<EntityStore> store, Life life) {
        for (Outing o : life.outings) {
            if (o != null) {
                WorldLife.remove(store, o.npc);
                WorldLife.remove(store, o.monster);
            }
        }
        life.patrol.forEach(r -> WorldLife.remove(store, r));
        removeChildren(store, life);
    }

    /** Le PNJ n'est plus (retiré ou mort). */
    static void forget(Ref<EntityStore> ref) {
        CHILD_OF.remove(ref);
    }

    public static void clearAll() {
        LIVES.clear();
        CHILD_OF.clear();
    }
}
