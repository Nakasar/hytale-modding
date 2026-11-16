package dev.nakasar.hytale.peuples.village;

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
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.workshop.Workshop;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les terrains libres E1 et E2 des villages (GDD des bâtiments de métier, étape 6). Kevin (2026-11-15) : E1 s'ouvre au
 * palier 2, E2 au palier 3 ; les piquets du terrain réservé apparaissent un palier plus tôt. Au panneau du village
 * (page {@link PlotPage}), un joueur de rang {@link #CHOOSE_RANK Ami} choisit un des 5 projets du peuple ; tant que le
 * chantier n'est pas lancé, on peut en changer sans frais. Lancer le chantier prend ses matériaux au dépôt ;
 * {@value #DEFAULT_HOURS} h de jeu de travaux dans le style du peuple ({@link SiteStyle}), puis le prefab vanilla est
 * collé et le villageois du projet arrive : c'est un bâtiment de métier complet (workshop/). Démolir rend un quart des
 * matériaux, une fois tous les {@value #DEMOLISH_DAYS} jours de jeu par terrain ; le bâtiment repart au niveau I.
 *
 * <p>Un projet est un bâtiment du plan par terrain ({@code E1_<Projet>}, {@code E2_<Projet>}, champ {@code Plot}),
 * jamais collé par les chantiers de palier (sauf pour rebâtir ses ruines après un raid perdu).
 */
public final class Plots {

    public static final String KEYS = "nakasar_peuples.plot.";
    /** Rang qui choisit un projet, lance ou démolit (Kevin : Ami suffit). */
    public static final Rank CHOOSE_RANK = Rank.AMI;
    public static final int DEMOLISH_DAYS = 7;
    /** Part des matériaux rendue au dépôt à la démolition (un quart). */
    public static final int REFUND_DIVISOR = 4;
    static final int DEFAULT_HOURS = 24;
    /** Piquets du terrain réservé : barrière vanilla du peuple, écriteau vanilla au coin nord-ouest. */
    private static final Map<String, String> STAKES = Map.of("Kweebec", "Wood_Hardwood_Fence", "Trork", "Wood_Deadwood_Fence",
            "Feran", "Wood_Drywood_Fence", "Renonce", "Wood_Softwood_Fence", "Slothian", "Wood_Tropicalwood_Fence");
    private static final String SIGN = "Furniture_Construction_Sign";
    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    /** Phase d'échafaudage posée, par village et terrain (mémoire de session). */
    private static final Map<String, Integer> PHASE = new ConcurrentHashMap<>();

    private Plots() {
    }

    /** Terrains du plan du village (vide sans plan). */
    public static VillageLayout.Plot[] plots(Village village) {
        VillageLayout layout = Chantiers.layout(village);
        return layout == null ? new VillageLayout.Plot[0] : layout.plots();
    }

    /** Projets possibles sur le terrain : ses bâtiments du plan, dans l'ordre du catalogue. */
    public static List<VillageLayout.Building> projects(Village village, String plotId) {
        List<VillageLayout.Building> out = new ArrayList<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout != null) {
            for (VillageLayout.Building b : layout.buildings()) {
                if (plotId.equals(b.plot())) {
                    out.add(b);
                }
            }
        }
        return out;
    }

    /** Id du projet d'un bâtiment d'emplacement ({@code E1_Archerie} → {@code Archerie}). */
    public static String projectId(VillageLayout.Building b) {
        return b.plot() != null && b.id().startsWith(b.plot() + "_") ? b.id().substring(b.plot().length() + 1) : b.id();
    }

    public static boolean isOpen(Village village, VillageLayout.Plot plot) {
        return village.tier() >= plot.tier();
    }

    /** Bâtiment de métier d'un bâtiment d'emplacement, ou null. */
    public static Workshop workshop(Village village, String buildingId) {
        for (Workshop w : Workshop.forLayout(village.layout())) {
            if (w.building().equals(buildingId)) {
                return w;
            }
        }
        return null;
    }

    /** Vrai si le projet `projectId` est choisi, en chantier ou bâti sur un autre terrain que `plotId`. */
    public static boolean takenElsewhere(Village village, String plotId, String projectId) {
        for (VillageLayout.Plot p : plots(village)) {
            if (p.id().equals(plotId)) {
                continue;
            }
            PlotState s = village.plot(p.id());
            if (s.project() != null && s.project().equals(p.id() + "_" + projectId)) {
                return true;
            }
        }
        return false;
    }

    /** Un deuxième élevage peut être pris sur les deux terrains (GDD) : le seul projet qui peut se répéter. */
    static boolean repeatable(String projectId) {
        return projectId.startsWith("Deuxieme_");
    }

    // ---- Ce que le joueur peut faire ----

    /** Pourquoi le joueur ne peut rien décider sur le terrain (rang, terrain fermé), ou null. */
    public static Message block(Store<EntityStore> store, Ref<EntityStore> ref, Village village, VillageLayout.Plot plot) {
        if (!isOpen(village, plot)) {
            return Message.translation(KEYS + "locked").param("tier", Message.translation(Tiers.nameKey(plot.tier())));
        }
        if (!Reputations.rank(store, ref, village).atLeast(CHOOSE_RANK)) {
            return Message.translation(KEYS + "rank").param("rank", Message.translation(CHOOSE_RANK.nameKey()));
        }
        return null;
    }

    /** Choisit (ou change, sans frais tant que le chantier n'est pas lancé) le projet du terrain. */
    public static boolean choose(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                 VillageLayout.Plot plot, String buildingId) {
        Message block = block(store, ref, village, plot);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        PlotState s = village.plot(plot.id());
        if (s.working() || (s.project() != null && village.isBuilt(s.project()))) {
            player.sendMessage(Message.translation(KEYS + "busy"));
            return false;
        }
        VillageLayout layout = Chantiers.layout(village);
        VillageLayout.Building b = layout == null ? null : layout.building(buildingId);
        if (b == null || !plot.id().equals(b.plot())) {
            return false;
        }
        String project = projectId(b);
        if (!repeatable(project) && takenElsewhere(village, plot.id(), project)) {
            player.sendMessage(Message.translation(KEYS + "taken"));
            return false;
        }
        s.setProject(b.id());
        Chantiers.announce(world, village, Message.translation(KEYS + "chosen").param("player", player.getUsername())
                .param("plot", plot.id()).param("building", Message.translation(Chantiers.buildingKey(b.id()))), null,
                NotificationStyle.Default);
        LOGGER.atInfo().log("Nakasar Peuples : %s choisit %s pour le terrain %s (%s)", player.getUsername(), b.id(), plot.id(), village.name());
        return true;
    }

    /** Renonce au projet choisi (chantier pas encore lancé). */
    public static boolean clear(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, VillageLayout.Plot plot) {
        Message block = block(store, ref, village, plot);
        PlotState s = village.plot(plot.id());
        if (block != null || s.working() || s.project() == null || village.isBuilt(s.project())) {
            if (block != null) {
                player.sendMessage(block);
            }
            return false;
        }
        s.setProject(null);
        return true;
    }

    /** Matériaux qui manquent au dépôt pour le chantier du terrain (objet → quantité), ou null sans dépôt. */
    public static Map<String, Integer> missing(World world, Village village, VillageLayout.Plot plot) {
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        if (deposit == null) {
            return null;
        }
        Map<String, Integer> out = new LinkedHashMap<>();
        for (VillageLayout.Material m : plot.materials()) {
            int have = deposit.getOrDefault(m.itemId(), 0);
            if (have < m.quantity()) {
                out.put(m.itemId(), m.quantity() - have);
            }
        }
        return out;
    }

    /** Lance le chantier du projet choisi : matériaux pris au dépôt, terrain aplani, échafaudage, {@code Hours} h de travaux. */
    public static boolean start(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                VillageLayout.Plot plot) {
        Message block = block(store, ref, village, plot);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        PlotState s = village.plot(plot.id());
        VillageLayout layout = Chantiers.layout(village);
        VillageLayout.Building b = s.project() == null || layout == null ? null : layout.building(s.project());
        if (b == null || s.working() || village.isBuilt(b.id())) {
            player.sendMessage(Message.translation(KEYS + (b == null ? "noProject" : "busy")));
            return false;
        }
        Map<String, Integer> missing = missing(world, village, plot);
        if (missing == null) {
            player.sendMessage(Message.translation("nakasar_peuples.board.depositMissing"));
            return false;
        }
        if (!missing.isEmpty()) {
            player.sendMessage(Message.translation(KEYS + "missing").param("list", materialList(missing)));
            return false;
        }
        removeStakes(world, village, plot, s);
        int h = Chantiers.siteHeight(world, village, b);
        Chantiers.Obstacles o = Chantiers.obstacles(world, village, b, h);
        if (o.any()) {
            player.sendMessage(Chantiers.obstacleLine(b, o));
            return false;
        }
        ItemContainer chest = Requests.depositContainer(world, village);
        for (VillageLayout.Material m : plot.materials()) {
            Requests.take(chest, m.itemId(), m.quantity());
        }
        Chantiers.prepare(world, new Terrain(world), village, layout, b, h);
        village.setSiteY(b.id(), h);
        Chantiers.site(world, village, b, h, 1);
        PHASE.put(key(village, plot), 1);
        long now = GameClock.seconds(store);
        s.startWorks(now, now + plot.hours() * 3600L);
        Chantiers.announce(world, village, Message.translation(KEYS + "started").param("player", player.getUsername())
                .param("building", Message.translation(Chantiers.buildingKey(b.id()))).param("hours", plot.hours()), null,
                NotificationStyle.Success);
        LOGGER.atInfo().log("Nakasar Peuples : chantier de %s lancé sur le terrain %s (%s)", b.id(), plot.id(), village.name());
        return true;
    }

    /**
     * Démolit le bâtiment du terrain pour en bâtir un autre : blocs au-dessus du sol de son emprise retirés (sauf les
     * coffres et autres conteneurs, objets des joueurs), panneau retiré, niveau perdu, un quart des matériaux rendu au
     * dépôt. Une fois tous les {@value #DEMOLISH_DAYS} jours par terrain.
     */
    public static boolean demolish(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                   VillageLayout.Plot plot) {
        Message block = block(store, ref, village, plot);
        if (block != null) {
            player.sendMessage(block);
            return false;
        }
        PlotState s = village.plot(plot.id());
        VillageLayout layout = Chantiers.layout(village);
        VillageLayout.Building b = s.project() == null || layout == null ? null : layout.building(s.project());
        if (b == null || !village.isBuilt(b.id()) || s.working()) {
            player.sendMessage(Message.translation(KEYS + "nothing"));
            return false;
        }
        int left = demolishDaysLeft(store, s);
        if (left > 0) {
            player.sendMessage(Message.translation(KEYS + "cooldown").param("days", left));
            return false;
        }
        int h = Chantiers.siteHeight(world, village, b);
        Chantiers.clearRuins(world, village, b, h);
        Workshop w = workshop(village, b.id());
        if (w != null) {
            WorkshopState ws = village.workshop(w.getId());
            if (ws.hasBoard()) {
                int[] at = ws.board();
                dev.nakasar.hytale.peuples.workshop.Workshops.unhangBoard(world.getChunkStore(), at,
                        Blocks.rotation(world.getChunkStore(), at[0], at[1], at[2]));
                Blocks.set(world.getChunkStore(), at[0], at[1], at[2], null, 0);
            }
            village.forgetWorkshop(w.getId());
            dev.nakasar.hytale.peuples.workshop.Livestock.changed(store, village, w);
        }
        village.unmarkBuilt(b.id());
        ItemContainer chest = Requests.depositContainer(world, village);
        if (chest != null) {
            for (VillageLayout.Material m : plot.materials()) {
                int back = m.quantity() / REFUND_DIVISOR;
                if (back > 0) {
                    chest.addItemStack(new ItemStack(m.itemId(), back));
                }
            }
        }
        s.setProject(null);
        s.setDemolished(GameClock.day(store));
        Chantiers.announce(world, village, Message.translation(KEYS + "demolished").param("player", player.getUsername())
                .param("building", Message.translation(Chantiers.buildingKey(b.id()))).param("plot", plot.id()), null,
                NotificationStyle.Warning);
        LOGGER.atInfo().log("Nakasar Peuples : %s démolit %s sur le terrain %s (%s)", player.getUsername(), b.id(), plot.id(), village.name());
        return true;
    }

    /** Jours avant la prochaine démolition possible sur le terrain (0 : maintenant). */
    public static int demolishDaysLeft(Store<EntityStore> store, PlotState s) {
        if (s.demolished() == Long.MIN_VALUE) {
            return 0;
        }
        return (int) Math.max(0, s.demolished() + DEMOLISH_DAYS - GameClock.day(store));
    }

    // ---- Le pas du village (VillageLifeSystem) ----

    /** Piquets des terrains réservés, échafaudage, et fin des chantiers d'emplacement (thread du monde). */
    public static void step(World world, Store<EntityStore> store, Village village) {
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return;
        }
        for (VillageLayout.Plot plot : layout.plots()) {
            PlotState s = village.plot(plot.id());
            VillageLayout.Building b = s.project() == null ? null : layout.building(s.project());
            if (s.working() && b != null) {
                long now = GameClock.seconds(store);
                if (now >= s.end()) {
                    finish(world, store, village, plot, s, b);
                } else {
                    long span = Math.max(1, s.end() - s.start());
                    int phase = 1 + (int) Math.min(SiteStyle.PHASES - 1, (now - s.start()) * SiteStyle.PHASES / span);
                    Integer shown = PHASE.get(key(village, plot));
                    if (shown == null || shown != phase) {
                        Chantiers.site(world, village, b, Chantiers.siteHeight(world, village, b), phase);
                        PHASE.put(key(village, plot), phase);
                    }
                }
                continue;
            }
            boolean empty = b == null || !village.isBuilt(b.id());
            if (empty && !s.stakes() && village.tier() >= plot.tier() - 1) {
                placeStakes(world, village, plot, s);
            }
        }
    }

    private static void finish(World world, Store<EntityStore> store, Village village, VillageLayout.Plot plot, PlotState s,
                               VillageLayout.Building b) {
        int h = Chantiers.siteHeight(world, village, b);
        Chantiers.site(world, village, b, h, 0);
        PHASE.remove(key(village, plot));
        s.clearWorks();
        if (VillageBuilder.paste(world, store, b.prefab(), village.x() + b.x(), h, village.z() + b.z(), b.rotation())) {
            VillageLayout layout = Chantiers.layout(village);
            if (layout != null) {
                Chantiers.settle(world, village, layout, b, h);
            }
            village.markBuilt(b.id());
            village.setSiteY(b.id(), h);
            Villagers.forgetGround();
            Message name = Message.translation(Chantiers.buildingKey(b.id()));
            Chantiers.announce(world, village, Message.translation(KEYS + "done").param("building", name).param("village", village.name()),
                    Message.translation(KEYS + "doneTitle").param("building", name), NotificationStyle.Success);
            LOGGER.atInfo().log("Nakasar Peuples : %s bâti sur le terrain %s (%s)", b.id(), plot.id(), village.name());
        } else {
            LOGGER.atWarning().log("Nakasar Peuples : collage de %s impossible sur le terrain %s (%s)", b.prefab(), plot.id(), village.name());
        }
    }

    /** Quatre piquets aux coins du terrain réservé et un écriteau, posés seulement dans l'air au-dessus du sol. */
    private static void placeStakes(World world, Village village, VillageLayout.Plot plot, PlotState s) {
        ChunkStore chunks = world.getChunkStore();
        Terrain terrain = new Terrain(world);
        String fence = STAKES.getOrDefault(village.people().id(), "Wood_Hardwood_Fence");
        int placed = 0;
        for (int[] c : corners(village, plot)) {
            int y = terrain.surface(c[0], c[1]);
            if (y == Terrain.NONE) {
                return;
            }
            String current = Blocks.name(chunks, c[0], y + 1, c[1]);
            if (current == null || Terrain.isVegetation(current)) {
                Blocks.set(chunks, c[0], y + 1, c[1], fence, 0);
                placed++;
            }
        }
        int[] nw = corners(village, plot).get(0);
        int y = terrain.surface(nw[0] + 1, nw[1] + 1);
        if (y != Terrain.NONE && Blocks.name(chunks, nw[0] + 1, y + 1, nw[1] + 1) == null) {
            Blocks.set(chunks, nw[0] + 1, y + 1, nw[1] + 1, SIGN, 0);
        }
        s.setStakes(true);
        LOGGER.atInfo().log("Nakasar Peuples : terrain %s réservé à %s (%d piquets)", plot.id(), village.name(), placed);
    }

    /** Retire les piquets et l'écriteau (ce qui est encore là, des blocs du mod seulement). */
    static void removeStakes(World world, Village village, VillageLayout.Plot plot, PlotState s) {
        if (!s.stakes()) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        Terrain terrain = new Terrain(world);
        String fence = STAKES.getOrDefault(village.people().id(), "Wood_Hardwood_Fence");
        List<int[]> spots = new ArrayList<>(corners(village, plot));
        int[] nw = spots.get(0);
        spots.add(new int[] {nw[0] + 1, nw[1] + 1});
        for (int[] c : spots) {
            int y = terrain.surface(c[0], c[1]);
            for (int dy = -1; dy <= 2 && y != Terrain.NONE; dy++) {
                String current = Blocks.name(chunks, c[0], y + dy, c[1]);
                if (current != null && (Blocks.is(current, fence) || Blocks.is(current, SIGN))) {
                    Blocks.set(chunks, c[0], y + dy, c[1], null, 0);
                }
            }
        }
        s.setStakes(false);
    }

    private static List<int[]> corners(Village village, VillageLayout.Plot plot) {
        int[] r = plot.rect();
        int x0 = village.x() + r[0];
        int x1 = village.x() + r[1];
        int z0 = village.z() + r[2];
        int z1 = village.z() + r[3];
        return List.of(new int[] {x0, z0}, new int[] {x1, z0}, new int[] {x0, z1}, new int[] {x1, z1});
    }

    private static String key(Village village, VillageLayout.Plot plot) {
        return village.id() + "/" + plot.id();
    }

    /** « 12 × Rondin, 4 × Fibre » pour un message. */
    static Message materialList(Map<String, Integer> materials) {
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

    /** Commande {@code /village finir} : les chantiers d'emplacement en cours finissent au prochain pas ; leur nombre. */
    public static int hurry(Store<EntityStore> store, Village village) {
        int n = 0;
        for (VillageLayout.Plot plot : plots(village)) {
            PlotState s = village.plot(plot.id());
            if (s.working()) {
                s.startWorks(s.start(), GameClock.nowOrPast(store));
                n++;
            }
        }
        return n;
    }

    /** Oublie les phases d'échafaudage (rechargement du mod). */
    public static void clearAll() {
        PHASE.clear();
    }
}
