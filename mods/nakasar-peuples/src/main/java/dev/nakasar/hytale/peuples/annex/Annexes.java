package dev.nakasar.hytale.peuples.annex;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.outpost.Outpost;
import dev.nakasar.hytale.peuples.outpost.Outposts;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Grading;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.SiteStyle;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Tiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les avant-postes de métier (Kevin, 2026-11-15) : un bâtiment isolé au rôle précis (ferme, mine, scierie, pêcherie,
 * pavillon de chasse, tour de guet), rattaché à un village de palier {@value #MIN_TIER} au moins.
 * <ol>
 *   <li>Au panneau du village, onglet « Avant-postes » ({@link AnnexPage}), un joueur de rang {@link #GRANT_RANK Ami}
 *   reçoit l'objet de fondation d'un type : ses matériaux sont pris au dépôt du village. Un avant-poste de chaque type
 *   par village ;</li>
 *   <li>il va poser la fondation là où il veut bâtir ({@link AnnexPlaceSystem}) : si la place ne convient pas
 *   ({@link #check}), le bloc n'est pas posé et le joueur lit pourquoi ; sinon la fondation reste, l'emprise est
 *   aplanie et marquée par le chantier du peuple ({@link SiteStyle}) ;</li>
 *   <li>une journée de jeu plus tard ({@code Hours}), les prefabs vanilla du peuple sont collés, la fondation devient le
 *   panneau de l'avant-poste et ses villageois arrivent ({@link Villagers}).</li>
 * </ol>
 * Debout, c'est un bâtiment de métier complet ({@link Workshops}) : commandes du jour, savoir-faire, niveaux I à III
 * (chantiers d'amélioration de 12 h), spécialité au niveau II, boutique, Part de l'Hôte. En plus, il livre chaque
 * matin un lot de sa production au dépôt du village ({@code Delivery}, multiplié par son niveau) et la tour de guet
 * annonce les raids plus tôt ({@code Warn}). Le plan de l'avant-poste est tourné vers le joueur qui pose la fondation.
 * Tout se passe sur le thread du monde.
 */
public final class Annexes {

    public static final String KEYS = "nakasar_peuples.annex.";
    /** Palier du village qu'il faut pour fonder un avant-poste (Kevin : palier 3 minimum). */
    public static final int MIN_TIER = 3;
    /** Rang qui reçoit une fondation au panneau du village. */
    public static final Rank GRANT_RANK = Rank.AMI;
    /** Rang qui pose la fondation. */
    public static final Rank PLACE_RANK = Rank.AMI;
    /** Écart minimal entre la fondation et le bord du plan du village (blocs). */
    public static final int VILLAGE_GAP = 20;
    /** Distance maximale entre la fondation et le cœur du village (blocs). */
    public static final int MAX_DISTANCE = 256;
    /** Écart minimal entre deux avant-postes (fondations). */
    public static final int ANNEX_SPACING = 48;
    /** Marge autour du plan d'un autre village. */
    public static final int OTHER_VILLAGE_GAP = 24;
    /** Relief maximal sur l'emprise (blocs). */
    public static final int MAX_RELIEF = 5;
    /** Joueur à moins de cette distance : le chantier avance et se termine (chunks chargés). */
    public static final int WATCH_RADIUS = 96;
    private static final int MARGIN = 2;
    private static final int BLEND = 3;
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    /** Phase de chantier posée par avant-poste (mémoire de session). */
    private static final Map<String, Integer> PHASE = new ConcurrentHashMap<>();
    private static final Set<String> BUSY = ConcurrentHashMap.newKeySet();

    private Annexes() {
    }

    // ---- Repères : plan local (rotation 0, fondation à l'origine) vers le monde ----

    /** Tourne (x, z) de `rotation` quarts de tour, comme PrefabRotation du serveur (1 : x' = z, z' = -x). */
    public static int[] rotate(int x, int z, int rotation) {
        int rx = x;
        int rz = z;
        for (int i = 0; i < (rotation & 3); i++) {
            int t = rx;
            rx = rz;
            rz = -t;
        }
        return new int[] {rx, rz};
    }

    /** Point du monde (x, z) du point local (lx, lz) de l'avant-poste. */
    public static int[] toWorld(AnnexState a, int lx, int lz) {
        return toWorld(a.x(), a.z(), a.rotation(), lx, lz);
    }

    static int[] toWorld(int ox, int oz, int rotation, int lx, int lz) {
        int[] r = rotate(lx, lz, rotation);
        return new int[] {ox + r[0], oz + r[1]};
    }

    /** Emprise du monde {@code [x0, x1, z0, z1]} de l'avant-poste posé en (ox, oz) avec cette rotation. */
    static int[] worldRect(Workshop.Annex spec, int ox, int oz, int rotation) {
        int[] r = spec.rect();
        int[] a = toWorld(ox, oz, rotation, r[0], r[2]);
        int[] b = toWorld(ox, oz, rotation, r[1], r[3]);
        return new int[] {Math.min(a[0], b[0]), Math.max(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[1], b[1])};
    }

    public static int[] worldRect(Workshop w, AnnexState a) {
        return worldRect(w.annex(), a.x(), a.z(), a.rotation());
    }

    /** Rotation du plan selon le côté où se tient le joueur : sud 0, est 1, nord 2, ouest 3. */
    public static int rotationFacing(double dx, double dz) {
        if (Math.abs(dx) > Math.abs(dz)) {
            return dx > 0 ? 1 : 3;
        }
        return dz >= 0 ? 0 : 2;
    }

    // ---- Catalogue et fondations (onglet du panneau) ----

    /** Avant-postes que le peuple du village peut fonder, triés par id. */
    public static List<Workshop> catalog(Village village) {
        return Workshop.annexes(village.people());
    }

    /** Pourquoi le joueur ne peut pas recevoir de fondation dans ce village, ou null. */
    public static Message block(Store<EntityStore> store, Ref<EntityStore> ref, Village village) {
        if (village.tier() < MIN_TIER) {
            return Message.translation(KEYS + "lockedTier").param("tier", Message.translation(Tiers.nameKey(MIN_TIER)));
        }
        if (!Reputations.rank(store, ref, village).atLeast(GRANT_RANK)) {
            return Message.translation(KEYS + "lockedRank").param("rank", Message.translation(GRANT_RANK.nameKey()));
        }
        return null;
    }

    /** Matériaux de la fondation qui manquent au dépôt (objet → quantité), ou null sans dépôt. */
    public static Map<String, Integer> missing(World world, Village village, Workshop w) {
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            return null;
        }
        Map<String, Integer> out = new LinkedHashMap<>();
        for (VillageLayout.Material m : w.annex().materials()) {
            int have = deposit.getOrDefault(m.itemId(), 0);
            if (have < m.quantity()) {
                out.put(m.itemId(), m.quantity() - have);
            }
        }
        return out;
    }

    /**
     * Donne la fondation de l'avant-poste `w` au joueur : matériaux pris au dépôt du village la première fois. Une
     * fondation remise et pas encore posée (perdue, oubliée dans un coffre) peut être reprise sans frais, une fois par
     * jour de jeu.
     */
    public static boolean grant(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                Workshop w) {
        Message block = block(store, ref, village);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        AnnexState a = village.annex(w.getId());
        long day = GameClock.day(store);
        if (a != null && !a.granted()) {
            player.sendMessage(Message.translation(KEYS + (a.built() ? "alreadyBuilt" : "alreadyWorks")));
            return false;
        }
        if (a != null) {
            if (a.grantedDay() == day) {
                player.sendMessage(Message.translation(KEYS + "regiveTomorrow").param("hour", GameClock.MORNING));
                return false;
            }
            a.grant(day, player.getUuid().toString(), player.getUsername());
            Requests.give(store, ref, new ItemStack(w.annex().item(), 1));
            player.sendMessage(Message.translation(KEYS + "regiven").param("building", Message.translation(w.nameKey())));
            return true;
        }
        Map<String, Integer> missing = missing(world, village, w);
        if (missing == null) {
            player.sendMessage(Message.translation("nakasar_peuples.board.depositMissing"));
            return false;
        }
        if (!missing.isEmpty()) {
            player.sendMessage(Message.translation(KEYS + "missing").param("list", materialList(missing)));
            return false;
        }
        ItemContainer chest = Villages.depositChest(world, village);
        for (VillageLayout.Material m : w.annex().materials()) {
            Requests.take(chest, m.itemId(), m.quantity());
        }
        village.ensureAnnex(w.getId()).grant(day, player.getUuid().toString(), player.getUsername());
        Requests.give(store, ref, new ItemStack(w.annex().item(), 1));
        Chantiers.announce(world, village, Message.translation(KEYS + "granted").param("player", player.getUsername())
                .param("building", Message.translation(w.nameKey())), null, NotificationStyle.Success);
        LOGGER.atInfo().log("Nakasar Peuples : fondation %s remise à %s (%s)", w.getId(), player.getUsername(), village.name());
        return true;
    }

    // ---- Pose de la fondation ----

    /** Une fondation à poser : le village qui l'a remise et son avant-poste. */
    public record Pending(Village village, Workshop workshop, AnnexState state) {
    }

    /**
     * La fondation `itemId` attendue le plus près de (x, z) : un village qui a remis cette fondation et ne l'a pas encore
     * vue posée, le plus proche (même au-delà de {@value #MAX_DISTANCE} blocs, {@link #check} le dira). Null : aucun
     * village n'attend cette fondation (objet copié, avant-poste déjà fondé).
     */
    public static Pending pending(World world, String itemId, int x, int z) {
        Pending best = null;
        double bestDistance = Double.MAX_VALUE;
        for (Village v : Villages.registry(world).all()) {
            for (AnnexState a : v.annexes()) {
                Workshop w = Workshop.get(a.id());
                if (!a.granted() || w == null || !w.isAnnex() || !w.annex().item().equals(itemId)) {
                    continue;
                }
                double d = v.horizontalDistanceSquared(x, z);
                if (d < bestDistance) {
                    best = new Pending(v, w, a);
                    bestDistance = d;
                }
            }
        }
        return best;
    }

    /** Vrai si `itemId` est une fondation d'avant-poste. */
    public static boolean isFoundation(String itemId) {
        return itemId != null && itemId.startsWith("Nakasar_Peuples_Annex_");
    }

    /**
     * Examine la place (x, y, z) de la fondation de `w` pour `village`, plan tourné de `rotation` : null si elle convient,
     * sinon le message qui dit la première règle non remplie. Terrain déjà chargé (le joueur est là).
     */
    public static Message check(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village village, Workshop w,
                                int x, int y, int z, int rotation) {
        Workshop.Annex spec = w.annex();
        if (village.tier() < MIN_TIER) {
            return Message.translation(KEYS + "lockedTier").param("tier", Message.translation(Tiers.nameKey(MIN_TIER)));
        }
        if (ref != null && !Reputations.rank(store, ref, village).atLeast(PLACE_RANK)) {
            return Message.translation(KEYS + "placeRank").param("rank", Message.translation(PLACE_RANK.nameKey()))
                    .param("village", village.name());
        }
        VillageLayout layout = Chantiers.layout(village);
        int radius = layout == null ? 64 : layout.radius();
        int distance = (int) Math.sqrt(village.horizontalDistanceSquared(x, z));
        if (distance < radius + VILLAGE_GAP) {
            return Message.translation(KEYS + "tooNear").param("village", village.name()).param("distance", distance)
                    .param("min", radius + VILLAGE_GAP);
        }
        if (distance > MAX_DISTANCE) {
            return Message.translation(KEYS + "tooFar").param("village", village.name()).param("distance", distance)
                    .param("max", MAX_DISTANCE);
        }
        int[] rect = worldRect(spec, x, z, rotation);
        int half = Math.max(rect[1] - rect[0], rect[3] - rect[2]) / 2 + 1;
        for (Village other : Villages.registry(world).all()) {
            if (other == village) {
                continue;
            }
            VillageLayout ol = Chantiers.layout(other);
            int min = (ol == null ? 64 : ol.radius()) + half + OTHER_VILLAGE_GAP;
            double d = other.horizontalDistanceSquared(x, z);
            if (d < (double) min * min) {
                return Message.translation(KEYS + "otherVillage").param("village", other.name()).param("distance", (int) Math.sqrt(d))
                        .param("min", min);
            }
        }
        for (Village v : Villages.registry(world).all()) {
            for (AnnexState other : v.annexes()) {
                if (other.granted()) {
                    continue;
                }
                double d = other.distanceSquared(x + 0.5, z + 0.5);
                if (d < (double) ANNEX_SPACING * ANNEX_SPACING) {
                    Workshop ow = Workshop.get(other.id());
                    return Message.translation(KEYS + "otherAnnex")
                            .param("building", ow == null ? Message.raw(other.id()) : Message.translation(ow.nameKey()))
                            .param("village", v.name()).param("distance", (int) Math.sqrt(d)).param("min", ANNEX_SPACING);
                }
            }
        }
        for (Outpost o : Outposts.all(world)) {
            double dx = o.x() - x;
            double dz = o.z() - z;
            int min = MAX_DISTANCE;
            if (o.waiting() && dx * dx + dz * dz < (double) min * min) {
                return Message.translation(KEYS + "outpostPlanned").param("distance", (int) Math.sqrt(dx * dx + dz * dz));
            }
        }
        // L'emprise : chargée, au sec, relief modéré, aucun bloc posé par un joueur.
        Terrain terrain = new Terrain(world);
        ChunkStore chunks = world.getChunkStore();
        int min = Integer.MAX_VALUE;
        int max = Integer.MIN_VALUE;
        int samples = 0;
        int wet = 0;
        for (int bx = rect[0] - MARGIN; bx <= rect[1] + MARGIN; bx += 2) {
            for (int bz = rect[2] - MARGIN; bz <= rect[3] + MARGIN; bz += 2) {
                int h = terrain.surface(bx, bz);
                if (h == Terrain.NONE) {
                    return Message.translation(KEYS + "unloaded");
                }
                samples++;
                if (terrain.hasFluid(bx, h + 1, bz) || terrain.hasFluid(bx, h, bz)) {
                    wet++;
                }
                min = Math.min(min, h);
                max = Math.max(max, h);
            }
        }
        if (wet > 0) {
            return Message.translation(KEYS + "water").param("count", wet);
        }
        if (max - min > MAX_RELIEF) {
            return Message.translation(KEYS + "relief").param("relief", max - min).param("max", MAX_RELIEF);
        }
        int ground = terrain.medianSurface(rect[0], rect[1], rect[2], rect[3], 2);
        for (int by = ground + 1; by <= ground + Math.min(spec.height(), 12); by++) {
            for (int bx = rect[0]; bx <= rect[1]; bx++) {
                for (int bz = rect[2]; bz <= rect[3]; bz++) {
                    String name = Blocks.name(chunks, bx, by, bz);
                    if (name != null && !natural(name)) {
                        return Message.translation(KEYS + "obstacle").param("block", name.startsWith("*") ? name.substring(1) : name)
                                .param("x", bx).param("y", by).param("z", bz);
                    }
                }
            }
        }
        Message rule = rule(world, terrain, village.people(), spec, rect, ground);
        if (rule != null) {
            return rule;
        }
        return null;
    }

    /** Ce que le terrain doit offrir selon le type (ferme, mine, scierie, pêcherie), ou null s'il l'offre. */
    static Message rule(World world, Terrain terrain, People people, Workshop.Annex spec, int[] rect, int ground) {
        ChunkStore chunks = world.getChunkStore();
        switch (spec.rule()) {
            case "FERTILE" -> {
                int total = 0;
                int fertile = 0;
                for (int x = rect[0]; x <= rect[1]; x += 2) {
                    for (int z = rect[2]; z <= rect[3]; z += 2) {
                        String top = terrain.surfaceBlock(x, z);
                        total++;
                        if (top != null && (top.startsWith("Soil_Grass") || top.startsWith("Soil_Dirt") || top.startsWith("Soil_Mud")
                                || people.suitsSite(top))) {
                            fertile++;
                        }
                    }
                }
                int percent = total == 0 ? 0 : 100 * fertile / total;
                return percent >= 60 ? null : Message.translation(KEYS + "rule.FERTILE").param("percent", percent).param("need", 60);
            }
            case "ROCK" -> {
                // Pierre affleurante ou flanc de colline à moins de 16 blocs de l'emprise.
                int total = 0;
                int rock = 0;
                int lo = Integer.MAX_VALUE;
                int hi = Integer.MIN_VALUE;
                for (int x = rect[0] - 16; x <= rect[1] + 16; x += 3) {
                    for (int z = rect[2] - 16; z <= rect[3] + 16; z += 3) {
                        int h = terrain.surface(x, z);
                        if (h == Terrain.NONE) {
                            continue;
                        }
                        total++;
                        String top = Blocks.name(chunks, x, h, z);
                        if (top != null && top.startsWith("Rock_")) {
                            rock++;
                        }
                        lo = Math.min(lo, h);
                        hi = Math.max(hi, h);
                    }
                }
                int percent = total == 0 ? 0 : 100 * rock / total;
                boolean ok = percent >= 15 || (hi - lo >= 8 && hi > ground + 4);
                return ok ? null : Message.translation(KEYS + "rule.ROCK").param("percent", percent);
            }
            case "TREES" -> {
                int trunks = 0;
                for (int x = rect[0] - 24; x <= rect[1] + 24; x += 2) {
                    for (int z = rect[2] - 24; z <= rect[3] + 24; z += 2) {
                        int h = terrain.surface(x, z);
                        if (h == Terrain.NONE) {
                            continue;
                        }
                        for (int y = h + 1; y <= h + 3; y++) {
                            String name = Blocks.name(chunks, x, y, z);
                            if (name != null && name.startsWith("Wood_") && name.contains("_Trunk")) {
                                trunks++;
                                break;
                            }
                        }
                    }
                }
                return trunks >= 6 ? null : Message.translation(KEYS + "rule.TREES").param("count", trunks).param("need", 6);
            }
            case "WATER" -> {
                int water = 0;
                for (int x = rect[0] - 12; x <= rect[1] + 12; x += 2) {
                    for (int z = rect[2] - 12; z <= rect[3] + 12; z += 2) {
                        if (x >= rect[0] && x <= rect[1] && z >= rect[2] && z <= rect[3]) {
                            continue;
                        }
                        int h = terrain.surface(x, z);
                        if (h != Terrain.NONE && terrain.hasFluid(x, h + 1, z)) {
                            water++;
                        }
                    }
                }
                return water >= 6 ? null : Message.translation(KEYS + "rule.WATER").param("distance", 12);
            }
            default -> {
                return null;
            }
        }
    }

    /** Bloc du monde naturel (relief, plante, arbre), comme les chantiers du village. */
    static boolean natural(String name) {
        String base = name.startsWith("*") ? name.substring(1) : name;
        if (base.startsWith("Plant_") || base.startsWith("Ore_") || base.startsWith("Rubble_") || base.startsWith("Fluid_")) {
            return true;
        }
        if (base.startsWith("Wood_")) {
            return base.contains("_Trunk") || base.contains("_Branch") || base.contains("_Roots");
        }
        if (base.startsWith("Deco_")) {
            return base.startsWith("Deco_Hive") || base.startsWith("Deco_Nest") || base.startsWith("Deco_SpiderWeb") || base.startsWith("Deco_Bone");
        }
        if (base.startsWith("Soil_") || base.startsWith("Rock_")) {
            return !base.contains("Brick") && !base.contains("Cobble") && !base.contains("Polished") && !base.contains("Smooth")
                    && !base.contains("Half") && !base.contains("Stairs") && !base.contains("Pathway");
        }
        return false;
    }

    /**
     * La fondation est posée et la place convient : on note la place, on lance une journée de travaux et, au pas
     * suivant (le bloc posé), on aplanit l'emprise et on dresse le chantier du peuple.
     */
    public static void start(World world, Store<EntityStore> store, PlayerRef player, Pending p, int x, int y, int z, int rotation) {
        Workshop.Annex spec = p.workshop().annex();
        int[] rect = worldRect(spec, x, z, rotation);
        int ground = new Terrain(world).medianSurface(rect[0], rect[1], rect[2], rect[3], 2);
        if (ground == Terrain.NONE) {
            ground = y - 1;
        }
        long now = GameClock.seconds(store);
        p.state().startWorks(x, y, z, rotation, ground, now, now + spec.hours() * 3600L);
        Village village = p.village();
        Workshop w = p.workshop();
        AnnexState a = p.state();
        world.execute(() -> {
            prepare(world, village, w, a);
            site(world, village, w, a, 1);
            PHASE.put(key(village, w), 1);
        });
        Message name = Message.translation(w.nameKey());
        Chantiers.announce(world, village, Message.translation(KEYS + "started").param("player", player.getUsername())
                .param("building", name).param("hours", spec.hours()), null, NotificationStyle.Success);
        player.sendMessage(Message.translation(KEYS + "startedHere").param("building", name).param("village", village.name())
                .param("hours", spec.hours()));
        LOGGER.atInfo().log("Nakasar Peuples : avant-poste %s fondé en %d %d %d (rotation %d) par %s pour %s", w.getId(), x, y, z,
                rotation, player.getUsername(), village.name());
    }

    /** Aplanit l'emprise de l'avant-poste (talus doux, arbres retirés en entier) sans toucher à la colonne de la fondation. */
    static void prepare(World world, Village village, Workshop w, AnnexState a) {
        int[] rect = worldRect(w, a);
        int fx = a.x();
        int fz = a.z();
        new Grading(world).pad(rect[0], rect[1], rect[2], rect[3], a.ground(), MARGIN, village.people().ground())
                .apply(BLEND, village.people().ground(), (x, z) -> x == fx && z == fz);
    }

    /** Pose le chantier du peuple sur l'emprise à la phase `phase` (0 : le retire), comme les chantiers du village. */
    static void site(World world, Village village, Workshop w, AnnexState a, int phase) {
        ChunkStore chunks = world.getChunkStore();
        int[] r = worldRect(w, a);
        People people = village.people();
        int h = a.ground();
        int height = w.annex().height();
        Map<Long, Set<String>> ours = SiteStyle.ours(people, r[0], r[1], r[2], r[3], h, height);
        Map<Long, SiteStyle.Placement> want = SiteStyle.plan(people, r[0], r[1], r[2], r[3], h, height, phase);
        List<Long> keys = new ArrayList<>(ours.keySet());
        keys.sort((p, q) -> Integer.compare(SiteStyle.keyY(q), SiteStyle.keyY(p)));
        for (long k : keys) {
            int x = SiteStyle.keyX(k);
            int y = SiteStyle.keyY(k);
            int z = SiteStyle.keyZ(k);
            String current = Blocks.name(chunks, x, y, z);
            SiteStyle.Placement p = want.get(k);
            if (ourBlock(current, ours.get(k)) && (p == null || !Blocks.is(current, p.block()))) {
                Blocks.set(chunks, x, y, z, null, 0);
            }
        }
        java.util.Collections.reverse(keys);
        for (long k : keys) {
            SiteStyle.Placement p = want.get(k);
            if (p == null) {
                continue;
            }
            int x = SiteStyle.keyX(k);
            int y = SiteStyle.keyY(k);
            int z = SiteStyle.keyZ(k);
            if (x == a.x() && z == a.z()) {
                continue; // la fondation
            }
            String current = Blocks.name(chunks, x, y, z);
            if (Blocks.is(current, p.block())) {
                continue;
            }
            boolean free = current == null || (current.startsWith("Plant_") && !current.startsWith("Plant_Leaves"));
            if (!free) {
                continue;
            }
            String below = Blocks.name(chunks, x, y - 1, z);
            if (p.grounded() && (below == null || below.startsWith("Plant_") || below.contains("Fluid_"))) {
                continue;
            }
            Blocks.set(chunks, x, y, z, p.block(), p.rotation());
        }
    }

    private static boolean ourBlock(String current, Set<String> ids) {
        if (current == null || ids == null) {
            return false;
        }
        for (String id : ids) {
            if (Blocks.is(current, id)) {
                return true;
            }
        }
        return false;
    }

    // ---- Le pas des avant-postes (VillageLifeSystem) ----

    /** Chantiers des avant-postes (phases, fin) et livraisons du matin, pour les avant-postes près d'un joueur. */
    public static void step(World world, Store<EntityStore> store, Village village, List<Vector3d> players, float dt) {
        long now = GameClock.seconds(store);
        for (AnnexState a : village.annexes()) {
            Workshop w = Workshop.get(a.id());
            if (w == null || !w.isAnnex() || a.granted()) {
                continue;
            }
            String key = key(village, w);
            if (a.built()) {
                // Livraison au dépôt du village : un convoi de porteurs part chaque matin.
                if (a.convoy()) {
                    Convoys.step(world, store, village, w, a, players, dt);
                } else {
                    deliver(world, store, village, w, a);
                }
                continue;
            }
            if (!watched(a, players)) {
                continue;
            }
            if (a.working()) {
                if (BUSY.contains(key)) {
                    continue;
                }
                if (now >= a.end()) {
                    finish(world, store, village, w, a);
                    continue;
                }
                long span = Math.max(1, a.end() - a.start());
                int phase = 1 + (int) Math.min(SiteStyle.PHASES - 1, (now - a.start()) * SiteStyle.PHASES / span);
                Integer shown = PHASE.get(key);
                if (shown == null || shown != phase) {
                    site(world, village, w, a, phase);
                    if (shown != null) {
                        Chantiers.announce(world, village, Message.translation(KEYS + "phase").param("building", Message.translation(w.nameKey()))
                                .param("phase", phase).param("phases", SiteStyle.PHASES), null, NotificationStyle.Default);
                    }
                    PHASE.put(key, phase);
                }
            }
        }
    }

    private static boolean watched(AnnexState a, List<Vector3d> players) {
        for (Vector3d p : players) {
            if (a.distanceSquared(p.x(), p.z()) <= (double) WATCH_RADIUS * WATCH_RADIUS) {
                return true;
            }
        }
        return false;
    }

    /** Fin des travaux : chantier retiré, prefabs collés, panneau à la place de la fondation, villageois attendus. */
    static void finish(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a) {
        String key = key(village, w);
        if (!BUSY.add(key)) {
            return;
        }
        try {
            site(world, village, w, a, 0);
            PHASE.remove(key);
            int pasted = 0;
            String[] prefabs = w.annex().prefabs();
            for (String line : prefabs) {
                String[] p = line.trim().split("\\s+");
                if (p.length < 4) {
                    continue;
                }
                try {
                    int[] at = toWorld(a, Integer.parseInt(p[1]), Integer.parseInt(p[2]));
                    int rot = (Integer.parseInt(p[3]) + a.rotation()) & 3;
                    if (VillageBuilder.paste(world, store, p[0], at[0], a.ground(), at[1], rot)) {
                        pasted++;
                    }
                } catch (NumberFormatException ignored) {
                    // Ligne mal formée : ValidateAssets la signale.
                }
            }
            if (pasted == 0) {
                // Zone pas chargée ou prefab introuvable : on réessaiera au prochain pas.
                LOGGER.atWarning().log("Nakasar Peuples : collage de l'avant-poste %s impossible (%s), nouvel essai", w.getId(), village.name());
                return;
            }
            a.markBuilt();
            WorkshopState ws = village.workshop(w.getId());
            placeBoard(world, village, w, ws);
            placeDecor(world, village, w, new int[] {a.x(), a.ground() + 1, a.z()}, w.annex().decor());
            Villagers.forgetGround();
            Message name = Message.translation(w.nameKey());
            Chantiers.announce(world, village, Message.translation(KEYS + "done").param("building", name).param("village", village.name()),
                    Message.translation(KEYS + "doneTitle").param("building", name), NotificationStyle.Success);
            announceNear(world, store, a, Message.translation(KEYS + "done").param("building", name).param("village", village.name()));
            LOGGER.atInfo().log("Nakasar Peuples : avant-poste %s bâti (%d/%d prefabs) pour %s", w.getId(), pasted, prefabs.length, village.name());
        } finally {
            BUSY.remove(key);
        }
    }

    /** Message aux joueurs près de l'avant-poste (ceux qui sont loin du village ne lisent pas les annonces du village). */
    private static void announceNear(World world, Store<EntityStore> store, AnnexState a, Message message) {
        for (PlayerRef player : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, player.getReference());
            if (at != null && a.distanceSquared(at.x(), at.z()) <= (double) WATCH_RADIUS * WATCH_RADIUS
                    && a.distanceSquared(at.x(), at.z()) > 0) {
                Ref<EntityStore> ref = player.getReference();
                if (ref != null) {
                    com.hypixel.hytale.server.core.util.NotificationUtil.sendNotification(player.getPacketHandler(), message,
                            NotificationStyle.Success);
                }
            }
        }
    }

    /**
     * Panneau de l'avant-poste à la place de sa fondation, tourné vers le joueur qui l'avait posée (appelé à la fin des
     * travaux, et par {@link Workshops#refresh} s'il manque). Sans effet tant que la colonne n'est pas chargée.
     */
    public static void placeBoard(World world, Village village, Workshop w, WorkshopState state) {
        AnnexState a = village.annex(w.getId());
        if (a == null || !a.built()) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        String board = village.people().boardBlock();
        int yaw = a.rotation();
        String current = Blocks.name(chunks, a.x(), a.y(), a.z());
        if (Blocks.id(chunks, a.x(), a.y(), a.z()) == Blocks.UNLOADED) {
            return;
        }
        int x = a.x();
        int y = a.y();
        int z = a.z();
        if (current != null && isFoundation(current.startsWith("*") ? current.substring(1) : current)) {
            Blocks.set(chunks, x, y, z, null, 0);
        } else if (current != null && !Terrain.isVegetation(current)) {
            int stand = Workshops.standY(chunks, new Terrain(world), x, z);
            if (stand == Workshops.UNLOADED_SPOT) {
                return;
            }
            if (stand == Terrain.NONE) {
                return;
            }
            y = stand;
        }
        if (Blocks.set(chunks, x, y, z, board, yaw)) {
            state.setBoard(x, y, z);
            Workshops.hangBoard(chunks, village, x, y, z, yaw);
            LOGGER.atInfo().log("Nakasar Peuples : panneau de l'avant-poste %s posé en %d %d %d (%s)", w.getId(), x, y, z, village.name());
        }
    }

    /** Décor vanilla ({@code "dx dy dz lacet Bloc"} locaux, relatifs à `origin`) tourné avec le plan, seulement dans l'air. */
    public static void placeDecor(World world, Village village, Workshop w, int[] origin, String[] decor) {
        AnnexState a = village.annex(w.getId());
        int rotation = a == null ? 0 : a.rotation();
        ChunkStore chunks = world.getChunkStore();
        for (String line : decor) {
            String[] p = line.trim().split("\\s+");
            if (p.length < 5) {
                continue;
            }
            try {
                int[] d = rotate(Integer.parseInt(p[0]), Integer.parseInt(p[2]), rotation);
                int x = origin[0] + d[0];
                int y = origin[1] + Integer.parseInt(p[1]);
                int z = origin[2] + d[1];
                int rot = (Integer.parseInt(p[3]) + rotation) & 3;
                String current = Blocks.name(chunks, x, y, z);
                if (Blocks.id(chunks, x, y, z) != Blocks.UNLOADED && (current == null || Terrain.isVegetation(current))
                        && Blocks.name(chunks, x, y - 1, z) != null) {
                    Blocks.set(chunks, x, y, z, p[4], rot);
                }
            } catch (NumberFormatException ignored) {
                // Ligne mal formée : ValidateAssets la signale.
            }
        }
    }

    /**
     * Lot du matin (production de l'avant-poste × son niveau), une fois par jour de jeu : il part en convoi vers le
     * dépôt du village ({@link Convoys}). Pas de nouveau convoi tant que celui de la veille est en route.
     */
    static void deliver(World world, Store<EntityStore> store, Village village, Workshop w, AnnexState a) {
        VillageLayout.Material lot = w.annex().delivery();
        long day = GameClock.day(store);
        if (lot == null || a.convoy() || a.deliveryDay() >= day || GameClock.hour(store) < GameClock.MORNING) {
            return;
        }
        int level = Math.max(1, village.workshop(w.getId()).level());
        Convoys.start(store, village, w, a, lot.quantity() * level);
    }

    /** Secondes d'annonce de plus avant un raid sur le village : tours de guet debout, par niveau. */
    public static int raidWarnBonus(Village village) {
        int bonus = 0;
        for (AnnexState a : village.annexes()) {
            Workshop w = Workshop.get(a.id());
            if (a.built() && w != null && w.isAnnex()) {
                bonus += w.annex().warn() * village.workshop(w.getId()).level();
            }
        }
        return bonus;
    }

    /** Commande {@code /village finir} : les travaux d'avant-poste en cours finissent au prochain pas ; leur nombre. */
    public static int hurry(Store<EntityStore> store, Village village) {
        int n = 0;
        for (AnnexState a : village.annexes()) {
            if (a.working()) {
                a.hurry(Math.max(1, GameClock.seconds(store)));
                n++;
            }
        }
        return n;
    }

    /** Heures de travaux restantes d'un avant-poste en chantier (arrondi au-dessus). */
    public static int hoursLeft(Store<EntityStore> store, AnnexState a) {
        return (int) Math.max(0, (a.end() - GameClock.seconds(store) + 3599) / 3600);
    }

    /** L'avant-poste dont l'emprise contient (x, z), ou null (blocs du bâtiment : réputation). */
    public static Village villageOfBlock(World world, int x, int y, int z) {
        for (Village v : Villages.registry(world).all()) {
            for (AnnexState a : v.annexes()) {
                Workshop w = Workshop.get(a.id());
                if (!a.built() || w == null || !w.isAnnex() || y < a.ground() - 1) {
                    continue;
                }
                int[] r = worldRect(w, a);
                if (x >= r[0] && x <= r[1] && z >= r[2] && z <= r[3]) {
                    return v;
                }
            }
        }
        return null;
    }

    public static Message materialList(Map<String, Integer> materials) {
        Message list = Message.empty();
        boolean first = true;
        for (Map.Entry<String, Integer> e : materials.entrySet()) {
            if (!first) {
                list.insert(", ");
            }
            first = false;
            list.insert(Message.translation(KEYS + "material").param("count", e.getValue()).param("item", VillageBoard.itemName(e.getKey())));
        }
        return list;
    }

    private static String key(Village village, Workshop w) {
        return village.id() + "/" + w.getId();
    }

    /** Oublie les phases de chantier (rechargement du mod). */
    public static void clearAll() {
        Convoys.clearAll();
        PHASE.clear();
        BUSY.clear();
    }
}
