package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.BiPredicate;
import java.util.function.Consumer;

/**
 * Les chantiers d'un village (étape 5 ; GDD, Paliers) : quand la jauge d'essor est pleine et que le dépôt contient les
 * matériaux du palier suivant, le village les prend et ouvre le chantier. Les bâtiments du palier (et ceux qui ont
 * brûlé) s'entourent d'un chantier propre au peuple ({@link SiteStyle} : jardin et lianes des Kweebecs, rondins et
 * peaux des Trorks...) qui évolue en {@value SiteStyle#PHASES} phases pendant le jour de jeu des travaux, puis le prefab
 * vanilla est collé, le chantier disparaît et le village change de palier.
 *
 * <p>Un emplacement occupé par des blocs posés par un joueur est sauté (le tableau le signale) : on ne casse jamais une
 * construction de joueur. Toutes les méthodes tournent sur le thread du monde.
 */
public final class Chantiers {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    public static final String KEYS = "nakasar_peuples.chantier.";

    /** Les annonces vont aux joueurs à moins de cette distance du cœur. */
    public static final int ANNOUNCE_RADIUS = 160;
    /** Écart de hauteur maximal entre un bâtiment et la place (comme VillageBuilder). */
    private static final int MAX_STEP = 4;
    private static final int MARGIN = 2;
    private static final int BLEND = 4;

    /** Villages dont un chargement de chunks est en cours (pas deux opérations à la fois). */
    private static final Set<String> BUSY = Collections.synchronizedSet(new HashSet<>());
    /**
     * Phase du chantier déjà posée, par village (non sauvegardée : après un redémarrage la phase en cours est reposée,
     * ce qui ne change rien puisque le plan est le même).
     */
    private static final Map<String, Integer> PHASE = new ConcurrentHashMap<>();

    private Chantiers() {
    }

    /** Ce qui empêche un chantier de commencer. */
    public enum Block {
        NONE, NO_LAYOUT, MAX_TIER, ACTIVE, ESSOR, DEPOSIT, MATERIALS, BUSY, NOTHING_TO_BUILD
    }

    /** Plan du village, ou null (village fondé à la main : pas de chantier). */
    public static VillageLayout layout(Village village) {
        return village.layout() == null ? null : VillageLayout.get(village.layout());
    }

    /**
     * Bâtiments que le chantier du palier `tier` met en travaux : ceux des paliers 0 à `tier` qui ne sont pas debout
     * (jamais collés, ou brûlés).
     */
    public static List<VillageLayout.Building> pending(VillageLayout layout, Village village, int tier) {
        List<VillageLayout.Building> out = new ArrayList<>();
        for (VillageLayout.Building b : layout.buildings()) {
            if (b.tier() <= tier && !village.isStanding(b.id())) {
                out.add(b);
            }
        }
        return out;
    }

    /** Matériaux qui manquent au dépôt pour le chantier `spec` (objet -> quantité manquante), ou null si le dépôt manque. */
    public static Map<String, Integer> missing(World world, Village village, VillageLayout.Chantier spec) {
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            return null;
        }
        Map<String, Integer> out = new LinkedHashMap<>();
        for (VillageLayout.Material m : spec.materials()) {
            int have = deposit.getOrDefault(m.itemId(), 0);
            if (have < m.quantity()) {
                out.put(m.itemId(), m.quantity() - have);
            }
        }
        return out;
    }

    /** Pourquoi le prochain chantier ne commence pas encore (NONE : il peut commencer). */
    public static Block blocker(World world, Village village, boolean force) {
        VillageLayout layout = layout(village);
        if (layout == null) {
            return Block.NO_LAYOUT;
        }
        if (village.chantier() != null) {
            return Block.ACTIVE;
        }
        if (village.tier() >= Tiers.MAX) {
            return Block.MAX_TIER;
        }
        if (BUSY.contains(village.id())) {
            return Block.BUSY;
        }
        int target = village.tier() + 1;
        VillageLayout.Chantier spec = layout.chantier(target);
        if (spec == null) {
            return Block.NO_LAYOUT;
        }
        if (force) {
            return Block.NONE;
        }
        if (village.essor() < Tiers.threshold(village.tier())) {
            return Block.ESSOR;
        }
        Map<String, Integer> missing = missing(world, village, spec);
        if (missing == null) {
            return Block.DEPOSIT;
        }
        return missing.isEmpty() ? Block.NONE : Block.MATERIALS;
    }

    /**
     * Ouvre le chantier du palier suivant si tout est prêt (`force` : sans jauge ni matériaux, commande de test). Les
     * matériaux sont pris au dépôt, puis les chunks chargés et la première phase du chantier posée ; `done` reçoit le résultat.
     */
    public static Block start(World world, Village village, boolean force, Consumer<ChantierState> done) {
        Block blocker = blocker(world, village, force);
        if (blocker != Block.NONE) {
            return blocker;
        }
        VillageLayout layout = layout(village);
        int target = village.tier() + 1;
        VillageLayout.Chantier spec = layout.chantier(target);
        List<VillageLayout.Building> buildings = pending(layout, village, target);
        if (!force) {
            ItemContainer chest = Requests.depositContainer(world, village);
            for (VillageLayout.Material m : spec.materials()) {
                Requests.take(chest, m.itemId(), m.quantity());
            }
        }
        BUSY.add(village.id());
        withChunks(world, village, layout, () -> {
            try {
                ChantierState state = open(world, village, layout, target, spec, buildings);
                if (done != null) {
                    done.accept(state);
                }
            } finally {
                BUSY.remove(village.id());
            }
        });
        return Block.NONE;
    }

    private static ChantierState open(World world, Village village, VillageLayout layout, int target, VillageLayout.Chantier spec,
                                      List<VillageLayout.Building> buildings) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Terrain terrain = new Terrain(world);
        List<String> working = new ArrayList<>();
        List<String> skipped = new ArrayList<>();
        Map<String, Obstacles> blocking = new LinkedHashMap<>();
        // Toutes les parcelles sont examinées avant de poser le moindre chantier : le chantier d'un bâtiment (1 bloc
        // autour de lui) ne doit pas faire sauter son voisin.
        List<VillageLayout.Building> free = new ArrayList<>();
        for (VillageLayout.Building b : buildings) {
            if (!village.isBuilt(b.id())) {
                Obstacles o = obstacles(world, village, b, siteHeight(world, village, b));
                if (o.any()) {
                    skipped.add(b.id());
                    blocking.put(b.id(), o);
                    continue;
                }
            }
            free.add(b);
        }
        for (VillageLayout.Building b : free) {
            boolean ruins = village.isBuilt(b.id());
            int h = siteHeight(world, village, b);
            if (ruins) {
                clearRuins(world, village, b, h);
            } else {
                prepare(world, terrain, village, layout, b, h);
            }
            village.setSiteY(b.id(), h);
            if (!b.small()) {
                site(world, village, b, h, 1);
            }
            working.add(b.id());
        }
        long now = GameClock.seconds(store);
        ChantierState state = new ChantierState(target, now, now + spec.hours() * 3600L, working.toArray(String[]::new),
                skipped.toArray(String[]::new));
        village.setChantier(state);
        PHASE.put(village.id(), 1);
        announce(world, village, Message.translation(KEYS + "started").param("village", village.name())
                .param("tier", Message.translation(Tiers.nameKey(target))).param("count", working.size())
                .param("hours", spec.hours()), null, NotificationStyle.Success);
        if (!skipped.isEmpty()) {
            announce(world, village, Message.translation(KEYS + "skipped").param("count", skipped.size()), null, NotificationStyle.Warning);
            for (String id : skipped) {
                announceChat(world, village, obstacleLine(layout.building(id), blocking.get(id)));
                Obstacle first = blocking.get(id).sample().get(0);
                LOGGER.atInfo().log("Nakasar Peuples : %s sauté à %s, %d bloc(s) gênant(s), dont %s en %d %d %d", id, village.name(),
                        blocking.get(id).total(), first.block(), first.x(), first.y(), first.z());
            }
            announceChat(world, village, Message.translation(KEYS + "obstacles.hint"));
        }
        LOGGER.atInfo().log("Nakasar Peuples : chantier du palier %d ouvert à %s (%d bâtiments, %d sautés)", target, village.name(),
                working.size(), skipped.size());
        return state;
    }

    /** Vrai si les travaux du chantier en cours sont finis (instant de jeu atteint). */
    public static boolean due(Store<EntityStore> store, Village village) {
        ChantierState c = village.chantier();
        return c != null && GameClock.seconds(store) >= c.end();
    }

    /**
     * Finit le chantier en cours : chantier retiré, prefabs collés, palier atteint, jauge remise à zéro, annonce. Faux
     * s'il n'y a pas de chantier ou qu'une opération est déjà en cours.
     */
    public static boolean finish(World world, Village village, Runnable done) {
        ChantierState c = village.chantier();
        VillageLayout layout = layout(village);
        if (c == null || layout == null || !BUSY.add(village.id())) {
            return false;
        }
        withChunks(world, village, layout, () -> {
            try {
                complete(world, village, layout, c);
                if (done != null) {
                    done.run();
                }
            } finally {
                BUSY.remove(village.id());
            }
        });
        return true;
    }

    private static void complete(World world, Village village, VillageLayout layout, ChantierState c) {
        if (village.chantier() != c) {
            return;
        }
        Store<EntityStore> store = world.getEntityStore().getStore();
        int pasted = 0;
        for (String id : c.buildings()) {
            VillageLayout.Building b = layout.building(id);
            if (b == null) {
                continue;
            }
            int h = siteHeight(world, village, b);
            site(world, village, b, h, 0);
            if (village.isBuilt(b.id())) {
                clearRuins(world, village, b, h);
            }
            if (VillageBuilder.paste(world, store, b.prefab(), village.x() + b.x(), h, village.z() + b.z(), b.rotation())) {
                village.markBuilt(b.id());
                village.setSiteY(b.id(), h);
                pasted++;
            }
        }
        Terrain terrain = new Terrain(world);
        for (String id : c.skipped()) {
            VillageLayout.Building b = layout.building(id);
            if (b == null || village.isStanding(id)) {
                continue;
            }
            int h = siteHeight(world, village, b);
            if (occupied(world, village, b, h)) {
                continue;
            }
            prepare(world, terrain, village, layout, b, h);
            if (VillageBuilder.paste(world, store, b.prefab(), village.x() + b.x(), h, village.z() + b.z(), b.rotation())) {
                village.markBuilt(b.id());
                village.setSiteY(b.id(), h);
                pasted++;
            }
        }
        VillageHeart.upgrade(world, village, layout, c.tier());
        village.setChantier(null);
        PHASE.remove(village.id());
        village.setTier(c.tier());
        village.setEssor(0);
        Message title = Message.translation(KEYS + "doneTitle").param("village", village.name())
                .param("tier", Message.translation(Tiers.nameKey(c.tier())));
        announce(world, village, Message.translation(KEYS + "done").param("village", village.name())
                .param("tier", Message.translation(Tiers.nameKey(c.tier()))).param("count", pasted), title, NotificationStyle.Success);
        LOGGER.atInfo().log("Nakasar Peuples : %s passe au palier %d (%d bâtiments collés)", village.name(), c.tier(), pasted);
    }

    /** Abandonne le chantier en cours sans le finir (chantier retiré ; matériaux perdus). */
    public static void cancel(World world, Village village) {
        ChantierState c = village.chantier();
        VillageLayout layout = layout(village);
        if (c == null) {
            return;
        }
        if (layout != null) {
            for (String id : c.buildings()) {
                VillageLayout.Building b = layout.building(id);
                if (b != null) {
                    site(world, village, b, siteHeight(world, village, b), 0);
                }
            }
        }
        village.setChantier(null);
        PHASE.remove(village.id());
    }

    /**
     * Commande de test : bâtit sur-le-champ, sans chantier, tout ce qui manque jusqu'au palier `tier`, et règle le
     * palier. Un chantier en cours est abandonné.
     */
    public static void buildNow(World world, Village village, int tier, Consumer<Integer> done) {
        VillageLayout layout = layout(village);
        int target = Tiers.clamp(tier);
        if (layout == null) {
            Villages.setTier(village, target);
            done.accept(0);
            return;
        }
        if (!BUSY.add(village.id())) {
            done.accept(-1);
            return;
        }
        withChunks(world, village, layout, () -> {
            try {
                cancel(world, village);
                Store<EntityStore> store = world.getEntityStore().getStore();
                Terrain terrain = new Terrain(world);
                int pasted = 0;
                for (VillageLayout.Building b : pending(layout, village, target)) {
                    boolean ruins = village.isBuilt(b.id());
                    int h = siteHeight(world, village, b);
                    if (!ruins && occupied(world, village, b, h)) {
                        continue;
                    }
                    if (ruins) {
                        clearRuins(world, village, b, h);
                    } else {
                        prepare(world, terrain, village, layout, b, h);
                    }
                    if (VillageBuilder.paste(world, store, b.prefab(), village.x() + b.x(), h, village.z() + b.z(), b.rotation())) {
                        village.markBuilt(b.id());
                        village.setSiteY(b.id(), h);
                        pasted++;
                    }
                }
                VillageHeart.upgrade(world, village, layout, target);
                Villages.setTier(village, target);
                village.setEssor(0);
                done.accept(pasted);
            } finally {
                BUSY.remove(village.id());
            }
        });
    }

    /**
     * Brûle un bâtiment debout du village (`buildingId` null : un des bâtiments du plus haut palier, au hasard, hors
     * petits décors). `dropTier` : le village redescend d'un palier et sa jauge repart de zéro (GDD, Raids). Le
     * bâtiment sera rebâti par le prochain chantier. Rend le bâtiment brûlé, ou null.
     */
    public static VillageLayout.Building burn(World world, Village village, String buildingId, boolean dropTier) {
        VillageLayout layout = layout(village);
        if (layout == null) {
            return null;
        }
        VillageLayout.Building target = null;
        if (buildingId != null) {
            target = layout.building(buildingId);
            if (target != null && !village.isStanding(target.id())) {
                target = null;
            }
        } else {
            List<VillageLayout.Building> candidates = new ArrayList<>();
            int best = -1;
            for (VillageLayout.Building b : layout.buildings()) {
                if (b.small() || !village.isStanding(b.id())) {
                    continue;
                }
                if (b.tier() > best) {
                    best = b.tier();
                    candidates.clear();
                }
                if (b.tier() == best) {
                    candidates.add(b);
                }
            }
            if (!candidates.isEmpty()) {
                target = candidates.get(ThreadLocalRandom.current().nextInt(candidates.size()));
            }
        }
        if (target == null) {
            return null;
        }
        cancel(world, village);
        int h = siteHeight(world, village, target);
        int[] r = target.rect();
        Burning.burn(world, village.x() + r[0], village.x() + r[1], village.z() + r[2], village.z() + r[3], h, target.height(),
                ThreadLocalRandom.current().nextLong());
        village.setSiteY(target.id(), h);
        village.markBurnt(target.id());
        if (dropTier) {
            Villages.setTier(village, village.tier() - 1);
            village.setEssor(0);
        }
        announce(world, village, Message.translation(KEYS + "burnt").param("village", village.name())
                .param("building", Message.translation(buildingKey(target.id())))
                .param("tier", Message.translation(Tiers.nameKey(village.tier()))), null, NotificationStyle.Danger);
        return target;
    }

    /** Clé de traduction du nom d'un bâtiment du plan. */
    public static String buildingKey(String buildingId) {
        return "nakasar_peuples.building." + buildingId;
    }

    /**
     * Hauteur de pose (ancre du prefab) d'un bâtiment : celle gardée avec le village, sinon le sol médian de son
     * emprise, à au plus {@value #MAX_STEP} blocs de la place (comme {@link VillageBuilder}).
     */
    public static int siteHeight(World world, Village village, VillageLayout.Building b) {
        int saved = village.siteY(b.id());
        if (saved != Integer.MIN_VALUE) {
            return saved;
        }
        int h0 = village.y() - 1;
        int[] r = b.rect();
        int h = new Terrain(world).medianSurface(village.x() + r[0], village.x() + r[1], village.z() + r[2], village.z() + r[3], 2);
        return h == Terrain.NONE ? h0 : Math.max(h0 - MAX_STEP, Math.min(h0 + MAX_STEP, h));
    }

    /** Un bloc qui gêne un chantier : position dans le monde et id du bloc (sans l'astérisque des variantes). */
    public record Obstacle(int x, int y, int z, String block) {
    }

    /** Les blocs qui gênent une parcelle : les {@value #OBSTACLE_SAMPLE} premiers trouvés et leur nombre total. */
    public record Obstacles(List<Obstacle> sample, int total) {
        public boolean any() {
            return total > 0;
        }
    }

    /** Nombre de blocs gênants gardés par parcelle (coordonnées dans le tchat, repères en jeu). */
    public static final int OBSTACLE_SAMPLE = 64;

    /**
     * Blocs de l'emprise, au-dessus du sol, qu'un joueur a pu poser (ni relief, ni plante, ni arbre) : la parcelle est
     * sautée s'il y en a un seul. Même zone que celle que le chantier examine : l'emprise du bâtiment, de
     * {@code h + 1} à {@code h + min(hauteur, 12)}.
     */
    public static Obstacles obstacles(World world, Village village, VillageLayout.Building b, int h) {
        ChunkStore chunks = world.getChunkStore();
        int[] r = b.rect();
        List<Obstacle> sample = new ArrayList<>();
        int total = 0;
        for (int y = h + 1; y <= h + scanHeight(b); y++) {
            for (int x = village.x() + r[0]; x <= village.x() + r[1]; x++) {
                for (int z = village.z() + r[2]; z <= village.z() + r[3]; z++) {
                    String name = Blocks.name(chunks, x, y, z);
                    if (name != null && !natural(name)) {
                        total++;
                        if (sample.size() < OBSTACLE_SAMPLE) {
                            sample.add(new Obstacle(x, y, z, name.startsWith("*") ? name.substring(1) : name));
                        }
                    }
                }
            }
        }
        return new Obstacles(sample, total);
    }

    /** Hauteur examinée au-dessus du sol d'une parcelle (blocs). */
    public static int scanHeight(VillageLayout.Building b) {
        return Math.min(b.height(), 12);
    }

    /** Blocs gênants d'un bâtiment du plan, à sa hauteur de pose. */
    public static Obstacles obstacles(World world, Village village, VillageLayout.Building b) {
        return obstacles(world, village, b, siteHeight(world, village, b));
    }

    /**
     * Bâtiments que des blocs empêchent de bâtir : ceux que le chantier en cours a sautés, sinon ceux qu'attend le
     * prochain chantier (hors ruines, que le chantier débarrasse lui-même). Seuls ceux qui ont encore des blocs gênants.
     */
    public static Map<VillageLayout.Building, Obstacles> blocked(World world, Village village) {
        Map<VillageLayout.Building, Obstacles> out = new LinkedHashMap<>();
        VillageLayout layout = layout(village);
        if (layout == null) {
            return out;
        }
        List<VillageLayout.Building> candidates = new ArrayList<>();
        ChantierState c = village.chantier();
        if (c != null) {
            for (String id : c.skipped()) {
                VillageLayout.Building b = layout.building(id);
                if (b != null) {
                    candidates.add(b);
                }
            }
        } else if (village.tier() < Tiers.MAX) {
            for (VillageLayout.Building b : pending(layout, village, village.tier() + 1)) {
                if (!village.isBuilt(b.id())) {
                    candidates.add(b);
                }
            }
        }
        for (VillageLayout.Building b : candidates) {
            Obstacles o = obstacles(world, village, b);
            if (o.any()) {
                out.put(b, o);
            }
        }
        return out;
    }

    static boolean occupied(World world, Village village, VillageLayout.Building b, int h) {
        return obstacles(world, village, b, h).any();
    }

    /** Bloc du monde naturel : relief, plante, arbre (pas de planches, de briques ni de meubles). */
    static boolean natural(String name) {
        String base = name.startsWith("*") ? name.substring(1) : name;
        if (base.startsWith("Plant_") || base.startsWith("Ore_") || base.startsWith("Rubble_") || base.startsWith("Fluid_")) {
            return true;
        }
        if (base.startsWith("Deco_")) {
            return base.startsWith("Deco_Hive") || base.startsWith("Deco_Nest") || base.startsWith("Deco_Coral")
                    || base.startsWith("Deco_SpiderWeb") || base.startsWith("Deco_Bone");
        }
        if (base.startsWith("Wood_")) {
            return base.contains("_Trunk") || base.contains("_Branch") || base.contains("_Roots");
        }
        if (base.startsWith("Soil_") || base.startsWith("Rock_")) {
            return !base.contains("Brick") && !base.contains("Cobble") && !base.contains("Polished") && !base.contains("Smooth")
                    && !base.contains("Half") && !base.contains("Stairs") && !base.contains("Pathway");
        }
        return false;
    }

    /** Aplanit l'emprise d'un bâtiment neuf (comme {@link VillageBuilder}) sans toucher aux autres emprises ni à la place. */
    private static void prepare(World world, Terrain terrain, Village village, VillageLayout layout, VillageLayout.Building b, int h) {
        int p = layout.plazaRadius();
        List<int[]> reserved = new ArrayList<>();
        reserved.add(new int[] {village.x() - p, village.x() + p, village.z() - p, village.z() + p});
        for (VillageLayout.Building other : layout.buildings()) {
            if (other != b) {
                int[] r = other.rect();
                reserved.add(new int[] {village.x() + r[0], village.x() + r[1], village.z() + r[2], village.z() + r[3]});
            }
        }
        BiPredicate<Integer, Integer> keep = (x, z) -> {
            for (int[] rect : reserved) {
                if (x >= rect[0] && x <= rect[1] && z >= rect[2] && z <= rect[3]) {
                    return true;
                }
            }
            return false;
        };
        int[] r = b.rect();
        terrain.flatten(village.x() + r[0], village.x() + r[1], village.z() + r[2], village.z() + r[3], h, MARGIN, BLEND,
                village.people().ground(), village.people().ground(), keep);
    }

    /**
     * Retire les ruines d'un bâtiment brûlé avant de le rebâtir : tout ce qui dépasse du sol dans l'emprise, sauf les
     * conteneurs (objets des joueurs).
     */
    private static void clearRuins(World world, Village village, VillageLayout.Building b, int h) {
        ChunkStore chunks = world.getChunkStore();
        int[] r = b.rect();
        for (int x = village.x() + r[0]; x <= village.x() + r[1]; x++) {
            for (int z = village.z() + r[2]; z <= village.z() + r[3]; z++) {
                for (int y = h + 1; y <= h + b.height(); y++) {
                    String name = Blocks.name(chunks, x, y, z);
                    if (name != null && !(name.contains("Furniture_") && Burning.isContainer(world, x, y, z))) {
                        Blocks.set(chunks, x, y, z, null, 0);
                    }
                }
            }
        }
    }

    /** Phase des travaux d'un chantier (1 à {@value SiteStyle#PHASES}), selon l'instant de jeu. */
    public static int phase(Store<EntityStore> store, ChantierState c) {
        long span = Math.max(1L, c.end() - c.start());
        long done = GameClock.seconds(store) - c.start();
        int p = 1 + (int) Math.floor((double) SiteStyle.PHASES * done / span);
        return Math.max(1, Math.min(SiteStyle.PHASES, p));
    }

    /**
     * Fait avancer le chantier en cours d'une phase quand le temps est venu (appelé par {@link VillageLifeSystem}) : le
     * chantier de chaque grand bâtiment passe à la phase suivante et les joueurs proches lisent ce que fait le peuple.
     */
    public static void grow(World world, Village village) {
        ChantierState c = village.chantier();
        VillageLayout layout = layout(village);
        if (c == null || layout == null || BUSY.contains(village.id())) {
            return;
        }
        int phase = phase(world.getEntityStore().getStore(), c);
        Integer known = PHASE.get(village.id());
        if (known != null && known >= phase) {
            return;
        }
        if (!BUSY.add(village.id())) {
            return;
        }
        withChunks(world, village, layout, () -> {
            try {
                if (village.chantier() != c) {
                    return;
                }
                for (String id : c.buildings()) {
                    VillageLayout.Building b = layout.building(id);
                    if (b != null && !b.small()) {
                        site(world, village, b, siteHeight(world, village, b), phase);
                    }
                }
                PHASE.put(village.id(), phase);
                if (known != null) {
                    announceChat(world, village, Message.translation(KEYS + "phase." + village.people().id() + "." + phase)
                            .param("village", village.name()));
                }
                LOGGER.atInfo().log("Nakasar Peuples : chantier de %s en phase %d", village.name(), phase);
            } finally {
                BUSY.remove(village.id());
            }
        });
    }

    /**
     * Pose le chantier d'un bâtiment à la phase `phase` (0 : le retire). On ne pose que dans l'air, dans les plantes
     * (hors feuillages) ou à la place de nos propres blocs d'une autre phase ; on ne retire que nos propres blocs. Les
     * retraits se font de haut en bas (ce qui pend avant ce qui le porte), les poses de bas en haut.
     */
    static void site(World world, Village village, VillageLayout.Building b, int h, int phase) {
        ChunkStore chunks = world.getChunkStore();
        People people = village.people();
        int[] r = b.rect();
        int x0 = village.x() + r[0];
        int x1 = village.x() + r[1];
        int z0 = village.z() + r[2];
        int z1 = village.z() + r[3];
        Map<Long, Set<String>> ours = SiteStyle.ours(people, x0, x1, z0, z1, h, b.height());
        Map<Long, SiteStyle.Placement> want = SiteStyle.plan(people, x0, x1, z0, z1, h, b.height(), phase);
        List<Long> keys = new ArrayList<>(ours.keySet());
        keys.sort((a, c) -> Integer.compare(SiteStyle.keyY(c), SiteStyle.keyY(a)));
        for (long k : keys) {
            int x = SiteStyle.keyX(k);
            int y = SiteStyle.keyY(k);
            int z = SiteStyle.keyZ(k);
            String current = Blocks.name(chunks, x, y, z);
            SiteStyle.Placement p = want.get(k);
            boolean mine = mine(current, ours.get(k));
            if (mine && (p == null || !Blocks.is(current, p.block()))) {
                Blocks.set(chunks, x, y, z, null, 0);
            }
        }
        Collections.reverse(keys);
        for (long k : keys) {
            SiteStyle.Placement p = want.get(k);
            if (p == null) {
                continue;
            }
            int x = SiteStyle.keyX(k);
            int y = SiteStyle.keyY(k);
            int z = SiteStyle.keyZ(k);
            String current = Blocks.name(chunks, x, y, z);
            if (Blocks.is(current, p.block())) {
                continue;
            }
            boolean free = current == null || (current.startsWith("Plant_") && !current.startsWith("Plant_Leaves"));
            if (!free) {
                continue;
            }
            if (p.grounded() && !solid(Blocks.name(chunks, x, y - 1, z))) {
                continue;
            }
            Blocks.set(chunks, x, y, z, p.block(), p.rotation());
        }
    }

    private static boolean mine(String current, Set<String> ids) {
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

    /** Un sol qui porte une plante ou un objet posé : ni air, ni plante, ni fluide. */
    private static boolean solid(String below) {
        return below != null && !below.startsWith("Plant_") && !below.startsWith("Fluid_") && !below.startsWith("*Fluid_");
    }

    /** Charge les chunks du plan entier puis lance `then` sur le thread du monde. */
    private static void withChunks(World world, Village village, VillageLayout layout, Runnable then) {
        int r = layout.radius() + MARGIN + BLEND + 2;
        Terrain.load(world, village.x() - r, village.x() + r, village.z() - r, village.z() + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null) {
                LOGGER.atWarning().withCause(error).log("Nakasar Peuples : chunks du village %s non chargés", village.name());
                BUSY.remove(village.id());
                return;
            }
            then.run();
        }));
    }

    /** Charge les chunks du village puis lance `then` sur le thread du monde (commandes ; ne touche pas aux travaux). */
    public static void loadThen(World world, Village village, Runnable then) {
        VillageLayout layout = layout(village);
        int r = (layout == null ? 32 : layout.radius()) + MARGIN + BLEND + 2;
        Terrain.load(world, village.x() - r, village.x() + r, village.z() - r, village.z() + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null) {
                LOGGER.atWarning().withCause(error).log("Nakasar Peuples : chunks du village %s non chargés", village.name());
                return;
            }
            then.run();
        }));
    }

    /**
     * Ligne de tchat d'une parcelle bloquée : bâtiment, nombre de blocs gênants et le premier (id et coordonnées, que
     * le joueur peut viser avec F3 / la boussole).
     */
    public static Message obstacleLine(VillageLayout.Building b, Obstacles o) {
        Obstacle first = o.sample().get(0);
        return Message.translation(KEYS + "obstacles.line").param("building", Message.translation(buildingKey(b.id())))
                .param("count", o.total()).param("block", first.block())
                .param("x", first.x()).param("y", first.y()).param("z", first.z());
    }

    /** Message de tchat seul (sans notification) aux joueurs proches du village. */
    static void announceChat(World world, Village village, Message message) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (PlayerRef player : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, player.getReference());
            if (at != null && village.horizontalDistanceSquared(at.x(), at.z()) <= (double) ANNOUNCE_RADIUS * ANNOUNCE_RADIUS) {
                player.sendMessage(message);
            }
        }
    }

    /** Message (tchat et notification) et titre facultatif aux joueurs proches du village. */
    public static void announce(World world, Village village, Message message, Message title, NotificationStyle style) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (PlayerRef player : world.getPlayerRefs()) {
            Vector3d at = Requests.position(store, player.getReference());
            if (at == null || village.horizontalDistanceSquared(at.x(), at.z()) > (double) ANNOUNCE_RADIUS * ANNOUNCE_RADIUS) {
                continue;
            }
            player.sendMessage(message);
            NotificationUtil.sendNotification(player.getPacketHandler(), message, style);
            if (title != null) {
                EventTitleUtil.showEventTitleToPlayer(player, title, Message.raw(village.name()), EventTitleStyle.Default, null, 4f, 0.5f, 1f);
            }
        }
    }

    /** Nombre d'objets `itemId` qu'un conteneur contient (pour l'affichage). */
    static int count(ItemContainer container, String itemId) {
        return container == null ? 0 : container.countItemStacks(s -> !ItemStack.isEmpty(s) && itemId.equals(s.getItemId()));
    }
}
