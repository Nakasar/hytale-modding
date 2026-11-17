package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Les générations de villageois (proposition validée par Kevin le 16 novembre 2026, Claude Doc « Peuples d'Orbis —
 * Générations de villageois ») : chaque villageois est un {@link Inhabitant} sauvegardé avec son village ; il naît,
 * grandit en apprenti auprès d'un adulte, prend un poste, vieillit et meurt, et son enfant reprend le poste.
 *
 * <p>Le pas du matin ({@link #step}) tourne quand un joueur est près du village : il traite chaque jour de jeu passé
 * depuis le dernier traité (rattrapage d'un village resté seul), avec un tirage fixe par village et par jour. On ne
 * meurt définitivement que de vieillesse, ou sur un raid perdu quand son bâtiment brûle ({@link RaidLosses}) ; un
 * villageois tué autrement revient au matin (village/Villagers), un défenseur tombé est blessé.
 */
public final class Population {

    public static final String KEYS = "nakasar_peuples.population.";

    /** Postes sans plan : le chef, le crieur et le marchand du village (request/Criers). */
    public static final String CHIEF = "@chief";
    public static final String CRIER = "@crier";
    public static final String MERCHANT = "@merchant";

    /** Habitants vivants au plus par village. */
    public static final int MAX_LIVING = 28;
    /** Lits d'une maison en plus de ceux de ses villageois à métier (la famille). */
    public static final int EXTRA_BEDS = 2;
    /** Une chance sur {@value} de naissance chaque matin. */
    public static final int BIRTH_CHANCE = 7;
    /** Jours au moins entre deux naissances. */
    public static final int BIRTH_GAP = 7;
    /** Vivres pris au dépôt à une naissance. */
    public static final int BIRTH_FOOD = 6;
    /** Un poste vide après une mort attire un arrivant au bout de ces jours. */
    public static final int VACANCY_DAYS = 3;
    /** Sous ce nombre d'adultes, un arrivant s'installe (tous les 3 jours au plus). */
    public static final int MIN_ADULTS = 4;
    /** Jours rattrapés au plus d'un coup (un village oublié très longtemps). */
    public static final int CATCH_UP = 200;
    /** Jours de deuil : mort de vieillesse, mort dans l'incendie. */
    public static final int MOURN_AGE = 1;
    public static final int MOURN_FIRE = 3;
    /** Réputation du parrain à chaque passage de stade de son filleul (s'il est connecté). */
    public static final int GODPARENT_REP = 20;
    /** Une orientation d'apprenti par village tous les {@value} jours. */
    public static final int ORIENT_DAYS = 7;
    /** Rangs : nommer un nouveau-né (Ami), orienter un apprenti et désigner le refuge (Hôte). */
    public static final Rank NAME_RANK = Rank.AMI;
    public static final Rank HOST_RANK = Rank.HOTE;
    /** Palier où l'Hôte peut désigner un refuge. */
    public static final int REFUGE_TIER = 2;
    /** Annonces de naissance, passation et mort aux joueurs à moins de cette distance. */
    public static final int ANNOUNCE = 160;

    /** Un poste du village : poste du plan, ou chef, crieur, marchand. */
    public record Post(String id, VillageLayout.Job job, String dialogue, String home) {

        /** Nom du métier (clé de langue du rôle de son dialogue). */
        public Message name() {
            Dialogue d = dialogue == null ? null : Dialogue.get(dialogue);
            if (d != null && d.roleKey() != null) {
                return Message.translation(d.roleKey());
            }
            return Message.translation(KEYS + "post." + id.replace("@", ""));
        }
    }

    private Population() {
    }

    public static PopulationState state(Village village) {
        return village.population();
    }

    /** Vrai si le village vit les générations : un vrai village avec un plan (pas un lieu-dit). */
    public static boolean applies(Village village) {
        return village != null && !village.isHamlet() && Chantiers.layout(village) != null;
    }

    // ---- Postes, foyers, lits ----

    /** Postes ouverts : métiers du plan au palier et dans un bâtiment debout, puis chef, crieur et marchand. */
    public static List<Post> posts(Village village) {
        List<Post> out = new ArrayList<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout != null) {
            for (VillageLayout.Job job : layout.jobs()) {
                if (job.tier() > village.tier() || (!job.building().isEmpty() && !village.isStanding(job.building()))) {
                    continue;
                }
                out.add(new Post(job.id(), job, job.dialogue(), job.home()));
            }
        }
        People p = village.people();
        String fallback = out.isEmpty() ? "" : out.get(0).home();
        out.add(new Post(CHIEF, null, p.chiefDialogue(), fallback));
        out.add(new Post(CRIER, null, p.crierDialogue(), fallback));
        out.add(new Post(MERCHANT, null, p.merchantDialogue(), fallback));
        return out;
    }

    public static Post post(Village village, String id) {
        for (Post p : posts(village)) {
            if (p.id().equals(id)) {
                return p;
            }
        }
        return null;
    }

    /** Lits par maison debout : un par villageois à métier qui y dort, plus {@value #EXTRA_BEDS} pour la famille. */
    public static Map<String, Integer> beds(Village village) {
        Map<String, Integer> beds = new LinkedHashMap<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return beds;
        }
        for (VillageLayout.Job job : layout.jobs()) {
            if (job.tier() > village.tier() || job.home().isEmpty() || !village.isStanding(job.home())) {
                continue;
            }
            beds.merge(job.home(), 1, Integer::sum);
        }
        beds.replaceAll((k, v) -> v + EXTRA_BEDS);
        return beds;
    }

    public static int totalBeds(Village village) {
        int n = 0;
        for (int b : beds(village).values()) {
            n += b;
        }
        return Math.min(MAX_LIVING, n);
    }

    private static int occupancy(PopulationState p, String home) {
        int n = 0;
        for (Inhabitant h : p.inhabitants) {
            if (h.alive() && home.equals(h.home)) {
                n++;
            }
        }
        return n;
    }

    /** Une maison avec un lit libre (la plus vide d'abord), ou null. */
    private static String freeHome(Village village, PopulationState p) {
        String best = null;
        int bestFree = 0;
        for (Map.Entry<String, Integer> e : beds(village).entrySet()) {
            int free = e.getValue() - occupancy(p, e.getKey());
            if (free > bestFree) {
                best = e.getKey();
                bestFree = free;
            }
        }
        return best;
    }

    // ---- Pas du matin ----

    /** Pas des générations (thread du monde) : fondateurs, puis chaque matin passé depuis le dernier traité. */
    public static void step(World world, Store<EntityStore> store, Village village) {
        if (!applies(village)) {
            return;
        }
        PopulationState p = state(village);
        long day = GameClock.day(store);
        if (!p.seeded) {
            seed(village, p, day);
        }
        if (p.lastDay == Inhabitant.NONE || p.lastDay > day) {
            p.lastDay = day;
        }
        if (p.lastDay < day) {
            refreshNeighbours(world);
            long from = Math.max(p.lastDay + 1, day - CATCH_UP);
            for (long d = from; d <= day; d++) {
                morning(world, store, village, p, d, d == day);
            }
            p.lastDay = day;
        }
        Cemetery.placePending(world, village, p);
    }

    /** Les villageois d'avant les générations reçoivent leur fiche : leurs noms sont gardés, leur âge tiré. */
    static void seed(Village village, PopulationState p, long day) {
        Random random = new Random(seedOf(village.id(), day) ^ 0x5eedL);
        for (Post post : posts(village)) {
            if (p.holder(post.id()) != null) {
                continue;
            }
            Inhabitant h = new Inhabitant();
            h.id = p.newId();
            Dialogue d = post.dialogue() == null ? null : Dialogue.get(post.dialogue());
            if (d != null && d.npcNameKey() != null) {
                h.nameKey = d.npcNameKey();
            } else {
                h.given = Names.given(village.people(), random, p);
            }
            h.family = Names.family(village.people(), random);
            // Âges étalés : les départs à la retraite ne tombent pas tous le même jour.
            int age = post.id().startsWith("@") ? Ages.ADULT + 40 + random.nextInt(50) : Ages.ADULT + 2 + random.nextInt(70);
            h.born = day - age;
            h.home = post.home() == null ? "" : post.home();
            h.job = post.id();
            h.trait = Traits.ALL.get(random.nextInt(Traits.ALL.size()));
            h.founder = true;
            p.inhabitants.add(h);
        }
        p.seeded = true;
        p.log(day, "founded", null, null, Integer.toString(p.inhabitants.size()));
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : %d fondateurs inscrits au village %s", p.inhabitants.size(), village.name());
    }

    /** Un matin de jeu : vieillesse, passages de stade, passations, postes, arrivants, orphelins, naissance. */
    static void morning(World world, Store<EntityStore> store, Village village, PopulationState p, long day, boolean live) {
        Random random = new Random(seedOf(village.id(), day));
        List<Post> posts = posts(village);
        // Fin du choix du prénom : le prénom tiré à la naissance reste.
        if (p.newborn != null && day > p.namingUntil) {
            p.newborn = null;
            p.proposals = new String[0];
        }
        // Vieillesse.
        for (Inhabitant h : new ArrayList<>(p.inhabitants)) {
            if (!h.alive()) {
                continue;
            }
            long age = h.age(day);
            if (age >= Ages.DEATH_SURE || (age >= Ages.DEATH_FROM && random.nextInt(Ages.DEATH_CHANCE) == 0)) {
                die(world, village, p, h, day, "age", live);
            }
        }
        // Passages de stade.
        for (Inhabitant h : p.living()) {
            Ages.Stage before = Ages.stage(h.age(day - 1));
            Ages.Stage now = h.stage(day);
            if (before == now) {
                continue;
            }
            switch (now) {
                case APPRENTICE -> {
                    chooseVocation(village, p, h, posts, random, day);
                    p.log(day, "apprentice", h.id, null, h.vocation);
                }
                case ADULT -> p.log(day, "adult", h.id, null, null);
                case ELDER -> p.log(day, "elder", h.id, null, h.job);
                default -> {
                }
            }
            if (live) {
                rewardGodparent(world, store, village, h);
            }
        }
        // Passations : un titulaire devenu ancien laisse son poste à l'apprenti devenu adulte.
        for (Inhabitant holder : p.living()) {
            if (!holder.hasJob() || holder.stage(day) != Ages.Stage.ELDER) {
                continue;
            }
            Inhabitant heir = heir(p, holder.job, day);
            if (heir != null) {
                String job = holder.job;
                holder.job = "";
                heir.job = job;
                p.log(day, "handover", heir.id, holder.id, job);
                if (live) {
                    announce(world, village, Message.translation(KEYS + "announce.handover").param("village", village.name())
                            .param("heir", heir.fullName()).param("elder", holder.given()).param("post", postName(village, job)));
                }
            }
        }
        // Postes sans titulaire.
        for (Post post : posts) {
            if (p.holder(post.id()) != null) {
                continue;
            }
            Inhabitant taker = heir(p, post.id(), day);
            if (taker == null) {
                taker = idleAdult(p, day);
            }
            long since = p.vacantSince(post.id());
            if (taker == null && (since == Inhabitant.NONE || day - since >= VACANCY_DAYS)) {
                taker = arrive(village, p, day, random, post);
            }
            if (taker != null) {
                taker.job = post.id();
                if (taker.home.isEmpty() && post.home() != null) {
                    taker.home = post.home();
                }
                p.clearVacant(post.id());
                if (since != Inhabitant.NONE) {
                    p.log(day, "takes", taker.id, null, post.id());
                }
            }
        }
        // Un village sans assez d'adultes attire un arrivant (tous les 3 jours au plus).
        if (adults(p, day) < MIN_ADULTS && Math.floorMod(day, 3) == 0 && p.living().size() < totalBeds(village)) {
            arrive(village, p, day, random, null);
        }
        // Orphelins et sans-logis : un enfant sans adulte dans son foyer est recueilli par un autre foyer.
        for (Inhabitant h : p.living()) {
            Ages.Stage s = h.stage(day);
            boolean young = s == Ages.Stage.CHILD || s == Ages.Stage.APPRENTICE;
            boolean homeless = h.home.isEmpty() || !village.isStanding(h.home);
            if ((young && !adultAt(p, h.home, day, h)) || (homeless && (p.refuge == null || !h.home.equals(p.refuge)))) {
                String home = homeless && refugeOpen(village, p) ? p.refuge : fosterHome(village, p, day, h);
                if (home != null && !home.equals(h.home)) {
                    h.home = home;
                    if (young) {
                        p.log(day, "fostered", h.id, null, home);
                    }
                }
            }
        }
        // Naissance.
        birth(world, village, p, day, random, live);
    }

    // ---- Naissances ----

    private static void birth(World world, Village village, PopulationState p, long day, Random random, boolean live) {
        if (day < p.nextBirth || day <= p.mourning || village.burnt().length > 0 || random.nextInt(BIRTH_CHANCE) != 0) {
            return;
        }
        if (p.living().size() >= totalBeds(village)) {
            return;
        }
        // Un foyer avec un lit libre et un adulte.
        List<String> homes = new ArrayList<>();
        for (Map.Entry<String, Integer> e : beds(village).entrySet()) {
            if (occupancy(p, e.getKey()) < e.getValue() && adultAt(p, e.getKey(), day, null)) {
                homes.add(e.getKey());
            }
        }
        if (homes.isEmpty()) {
            return;
        }
        ItemContainer chest = Villages.depositChest(world, village);
        if (chest == null || takeFood(chest, BIRTH_FOOD) < BIRTH_FOOD) {
            return;
        }
        String home = homes.get(random.nextInt(homes.size()));
        List<Inhabitant> parents = new ArrayList<>();
        for (Inhabitant h : p.living()) {
            Ages.Stage s = h.stage(day);
            if (home.equals(h.home) && (s == Ages.Stage.ADULT || s == Ages.Stage.ELDER)) {
                parents.add(h);
            }
        }
        parents.sort(Comparator.comparingInt(h -> h.stage(day) == Ages.Stage.ADULT ? 0 : 1));
        if (parents.size() > 2) {
            parents = new ArrayList<>(parents.subList(0, 2));
        }
        Inhabitant child = new Inhabitant();
        child.id = p.newId();
        child.given = Names.given(village.people(), random, p);
        Inhabitant from = parents.get(random.nextInt(parents.size()));
        child.family = from.family == null || from.family.isEmpty() ? Names.family(village.people(), random) : from.family;
        child.born = day;
        child.parents = parents.stream().map(h -> h.id).toArray(String[]::new);
        child.home = home;
        child.trait = random.nextBoolean() ? from.trait : Traits.ALL.get(random.nextInt(Traits.ALL.size()));
        p.inhabitants.add(child);
        p.nextBirth = day + BIRTH_GAP;
        p.newborn = child.id;
        p.namingUntil = day + 1;
        p.proposals = Names.proposals(village.people(), random, p);
        p.log(day, "birth", child.id, parents.get(0).id, parents.size() > 1 ? parents.get(1).id : null);
        if (live) {
            announce(world, village, Message.translation(KEYS + "announce.birth").param("village", village.name())
                    .param("child", child.fullName()).param("parents", parentsText(p, child)));
        }
    }

    /** Luxes des routes commerciales : les naissances ne les mangent pas (ils prolongent l'accès du village). */
    static final java.util.Set<String> LUXURIES = java.util.Set.of("Plant_Fruit_Azure", "Food_Cheese", "Food_Fish_Raw_Rare", "Food_Pie_Apple");

    /** Vivres du dépôt : nourriture et récoltes, hors luxes. */
    static boolean isFood(String itemId) {
        return itemId != null && !LUXURIES.contains(itemId)
                && (itemId.startsWith("Food_") || itemId.startsWith("Plant_Crop_") || itemId.startsWith("Plant_Fruit_"));
    }

    private static int takeFood(ItemContainer chest, int wanted) {
        Map<String, Integer> found = new LinkedHashMap<>();
        for (short slot = 0; slot < chest.getCapacity(); slot++) {
            ItemStack s = chest.getItemStack(slot);
            if (!ItemStack.isEmpty(s) && isFood(s.getItemId())) {
                found.merge(s.getItemId(), s.getQuantity(), Integer::sum);
            }
        }
        int total = found.values().stream().mapToInt(Integer::intValue).sum();
        if (total < wanted) {
            return 0;
        }
        int left = wanted;
        for (String id : found.keySet()) {
            if (left <= 0) {
                break;
            }
            left -= Requests.take(chest, id, left);
        }
        return wanted - left;
    }

    /** Un joueur de rang Ami choisit le prénom du nouveau-né parmi les trois proposés : il devient parrain. */
    public static boolean name(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village, int choice) {
        PopulationState p = state(village);
        Inhabitant child = p.byId(p.newborn);
        long day = GameClock.day(store);
        if (child == null || day > p.namingUntil || choice < 0 || choice >= p.proposals.length) {
            player.sendMessage(Message.translation(KEYS + "nameTooLate"));
            return false;
        }
        if (!Reputations.rank(store, ref, village).atLeast(NAME_RANK)) {
            player.sendMessage(Message.translation(KEYS + "rankNeeded").param("rank", Message.translation(NAME_RANK.nameKey())));
            return false;
        }
        child.given = p.proposals[choice];
        child.nameKey = null;
        child.godparent = player.getUuid().toString();
        child.godparentName = player.getUsername();
        p.newborn = null;
        p.proposals = new String[0];
        p.log(day, "named", child.id, null, player.getUsername());
        announce(world, village, Message.translation(KEYS + "announce.named").param("village", village.name())
                .param("child", child.fullName()).param("player", player.getUsername()));
        return true;
    }

    private static void rewardGodparent(World world, Store<EntityStore> store, Village village, Inhabitant h) {
        if (h.godparent == null) {
            return;
        }
        for (PlayerRef pr : world.getPlayerRefs()) {
            if (pr.getUuid().toString().equals(h.godparent)) {
                Ref<EntityStore> r = pr.getReference();
                if (r != null && r.isValid()) {
                    Reputations.change(world, store, r, pr, village, GODPARENT_REP, KEYS + "godparentReason");
                }
            }
        }
    }

    // ---- Vocation, succession, arrivants ----

    /** L'apprenti choisit sa vocation : un poste qui se libère, le métier d'un parent, celui de son trait, un autre. */
    static void chooseVocation(Village village, PopulationState p, Inhabitant h, List<Post> posts, Random random, long day) {
        List<String> needed = new ArrayList<>();
        for (Post post : posts) {
            Inhabitant holder = p.holder(post.id());
            boolean freeing = holder == null || holder.age(day) >= Ages.ELDER - Ages.APPRENTICE;
            if (freeing && !learnedBy(p, post.id(), h)) {
                needed.add(post.id());
            }
        }
        if (!needed.isEmpty()) {
            h.vocation = needed.get(random.nextInt(needed.size()));
            return;
        }
        if (random.nextBoolean()) {
            for (String pid : h.parents) {
                Inhabitant parent = p.byId(pid);
                String job = parent == null ? null : (parent.hasJob() ? parent.job : parent.diedJob);
                if (job != null && !job.isEmpty() && post(village, job) != null) {
                    h.vocation = job;
                    return;
                }
            }
        }
        List<String> trait = new ArrayList<>();
        for (Post post : posts) {
            if (Traits.matches(h.trait, post.id())) {
                trait.add(post.id());
            }
        }
        List<String> pool = trait.isEmpty() ? posts.stream().map(Post::id).toList() : trait;
        h.vocation = pool.isEmpty() ? "" : pool.get(random.nextInt(pool.size()));
    }

    private static boolean learnedBy(PopulationState p, String job, Inhabitant except) {
        for (Inhabitant h : p.inhabitants) {
            if (h != except && h.alive() && !h.hasJob() && job.equals(h.vocation)) {
                return true;
            }
        }
        return false;
    }

    /** L'apprenti devenu adulte, sans poste, qui a appris `job` ; null s'il n'y en a pas. */
    private static Inhabitant heir(PopulationState p, String job, long day) {
        for (Inhabitant h : p.inhabitants) {
            if (h.alive() && !h.hasJob() && job.equals(h.vocation) && h.stage(day) == Ages.Stage.ADULT) {
                return h;
            }
        }
        return null;
    }

    private static Inhabitant idleAdult(PopulationState p, long day) {
        for (Inhabitant h : p.inhabitants) {
            if (h.alive() && !h.hasJob() && h.stage(day) == Ages.Stage.ADULT && !h.convalescent(day)) {
                return h;
            }
        }
        return null;
    }

    private static int adults(PopulationState p, long day) {
        int n = 0;
        for (Inhabitant h : p.inhabitants) {
            if (h.alive() && h.stage(day) == Ages.Stage.ADULT) {
                n++;
            }
        }
        return n;
    }

    private static boolean adultAt(PopulationState p, String home, long day, Inhabitant except) {
        for (Inhabitant h : p.inhabitants) {
            Ages.Stage s = h.stage(day);
            if (h != except && h.alive() && home.equals(h.home) && (s == Ages.Stage.ADULT || s == Ages.Stage.ELDER)) {
                return true;
            }
        }
        return false;
    }

    private static String fosterHome(Village village, PopulationState p, long day, Inhabitant child) {
        for (Map.Entry<String, Integer> e : beds(village).entrySet()) {
            if (occupancy(p, e.getKey()) < e.getValue() && adultAt(p, e.getKey(), day, child)) {
                return e.getKey();
            }
        }
        return freeHome(village, p);
    }

    /** Un arrivant adulte s'installe (venu d'un autre village du même peuple si possible) ; `post` : le poste qu'il prend. */
    static Inhabitant arrive(Village village, PopulationState p, long day, Random random, Post post) {
        Inhabitant h = new Inhabitant();
        h.id = p.newId();
        h.given = Names.given(village.people(), random, p);
        h.family = Names.family(village.people(), random);
        h.born = day - Ages.ADULT - random.nextInt(40);
        h.trait = Traits.ALL.get(random.nextInt(Traits.ALL.size()));
        String home = post != null && post.home() != null && !post.home().isEmpty() ? post.home() : freeHome(village, p);
        h.home = home == null ? "" : home;
        h.from = elsewhere(village, random);
        p.inhabitants.add(h);
        p.log(day, "arrival", h.id, null, h.from);
        return h;
    }

    private static String elsewhere(Village village, Random random) {
        return otherVillages.getOrDefault(village.id(), List.of()).isEmpty() ? null
                : otherVillages.get(village.id()).get(random.nextInt(otherVillages.get(village.id()).size()));
    }

    /** Noms des autres villages du même peuple (mis à jour par {@link #refreshNeighbours}), pour les arrivants. */
    private static final Map<String, List<String>> otherVillages = new HashMap<>();

    public static void refreshNeighbours(World world) {
        otherVillages.clear();
        List<Village> all = Villages.registry(world).all();
        for (Village v : all) {
            List<String> names = new ArrayList<>();
            for (Village o : all) {
                if (o != v && o.people() == v.people() && !o.isHamlet()) {
                    names.add(o.name());
                }
            }
            otherVillages.put(v.id(), names);
        }
    }

    // ---- Morts ----

    /** Mort définitive : fiche close, poste vacant, deuil, tombe à poser, chronique. */
    static void die(World world, Village village, PopulationState p, Inhabitant h, long day, String cause, boolean live) {
        h.died = day;
        h.cause = cause;
        h.diedJob = h.hasJob() ? h.job : null;
        if (h.hasJob()) {
            p.setVacant(h.job, day);
        }
        String job = h.job;
        h.job = "";
        p.mourning = Math.max(p.mourning, day + ("fire".equals(cause) ? MOURN_FIRE : MOURN_AGE) - 1);
        if (h.id.equals(p.newborn)) {
            p.newborn = null;
        }
        p.log(day, "death_" + cause, h.id, null, job);
        if (live && world != null) {
            announce(world, village, Message.translation(KEYS + "announce.death_" + cause).param("village", village.name())
                    .param("name", h.fullName()).param("post", job == null || job.isEmpty() ? Message.translation(KEYS + "noPost")
                            : postName(village, job)));
        }
    }

    /** Mort par commande d'essai ({@code /village deces}). */
    public static boolean kill(World world, Store<EntityStore> store, Village village, String id, String cause) {
        PopulationState p = state(village);
        Inhabitant h = p.byId(id);
        if (h == null || !h.alive()) {
            return false;
        }
        die(world, village, p, h, GameClock.day(store), cause, true);
        return true;
    }

    /** Vieillit tout le village de `days` jours (commande d'essai) : les matins sont rejoués. */
    public static void age(World world, Store<EntityStore> store, Village village, int days) {
        PopulationState p = state(village);
        if (!p.seeded) {
            seed(village, p, GameClock.day(store));
        }
        long day = GameClock.day(store);
        for (Inhabitant h : p.inhabitants) {
            h.born -= days;
            if (!h.alive()) {
                h.died -= days;
            }
            if (h.wounded != Inhabitant.NONE) {
                h.wounded -= days;
            }
        }
        // Les matins sautés sont rejoués sur la nouvelle chronologie (sans rattrapage des naissances déjà possibles).
        for (int i = days - 1; i >= 0; i--) {
            morning(world, store, village, p, day - i, i == 0);
        }
        p.lastDay = day;
    }

    /** Naissance forcée (commande d'essai) : ignore le hasard et l'écart de 7 jours, pas les lits ni les vivres. */
    public static boolean forceBirth(World world, Store<EntityStore> store, Village village) {
        PopulationState p = state(village);
        long day = GameClock.day(store);
        int before = p.inhabitants.size();
        long next = p.nextBirth;
        long mourn = p.mourning;
        p.nextBirth = Inhabitant.NONE;
        p.mourning = Inhabitant.NONE;
        Random always = new Random(seedOf(village.id(), day)) {
            @Override
            public int nextInt(int bound) {
                return bound == BIRTH_CHANCE ? 0 : super.nextInt(bound);
            }
        };
        birth(world, village, p, day, always, true);
        if (p.inhabitants.size() == before) {
            p.nextBirth = next;
            p.mourning = mourn;
            return false;
        }
        return true;
    }

    // ---- Refuge, orientation ----

    public static boolean refugeOpen(Village village, PopulationState p) {
        return p.refuge != null && village.tier() >= REFUGE_TIER && village.isStanding(p.refuge);
    }

    /** Grands bâtiments debout que l'Hôte peut désigner comme refuge. */
    public static List<String> refugeChoices(Village village) {
        List<String> out = new ArrayList<>();
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return out;
        }
        for (VillageLayout.Building b : layout.buildings()) {
            if (!b.small() && village.isStanding(b.id())) {
                out.add(b.id());
            }
        }
        return out;
    }

    /** L'Hôte passe au refuge suivant (aucun après le dernier). */
    public static boolean cycleRefuge(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village) {
        if (village.tier() < REFUGE_TIER) {
            player.sendMessage(Message.translation(KEYS + "refugeTier").param("tier", Message.translation(dev.nakasar.hytale.peuples.village.Tiers.nameKey(REFUGE_TIER))));
            return false;
        }
        if (!Reputations.rank(store, ref, village).atLeast(HOST_RANK)) {
            player.sendMessage(Message.translation(KEYS + "rankNeeded").param("rank", Message.translation(HOST_RANK.nameKey())));
            return false;
        }
        PopulationState p = state(village);
        List<String> choices = refugeChoices(village);
        int i = p.refuge == null ? -1 : choices.indexOf(p.refuge);
        p.refuge = i + 1 < choices.size() ? choices.get(i + 1) : null;
        return true;
    }

    /** Postes vers lesquels l'apprenti peut être orienté. */
    public static List<Post> orientChoices(Village village) {
        return posts(village);
    }

    /** L'Hôte oriente un apprenti vers un poste (une fois tous les {@value #ORIENT_DAYS} jours par village). */
    public static boolean orient(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village village,
                                 String inhabitantId, String postId) {
        PopulationState p = state(village);
        Inhabitant h = p.byId(inhabitantId);
        long day = GameClock.day(store);
        if (h == null || !h.alive() || h.hasJob() || h.stage(day) != Ages.Stage.APPRENTICE || post(village, postId) == null) {
            return false;
        }
        if (!Reputations.rank(store, ref, village).atLeast(HOST_RANK)) {
            player.sendMessage(Message.translation(KEYS + "rankNeeded").param("rank", Message.translation(HOST_RANK.nameKey())));
            return false;
        }
        if (p.orientDay != Inhabitant.NONE && day < p.orientDay + ORIENT_DAYS) {
            player.sendMessage(Message.translation(KEYS + "orientWait").param("days", p.orientDay + ORIENT_DAYS - day));
            return false;
        }
        h.vocation = postId;
        p.orientDay = day;
        p.log(day, "oriented", h.id, null, postId);
        player.sendMessage(Message.translation(KEYS + "oriented").param("name", h.given()).param("post", postName(village, postId)));
        return true;
    }

    // ---- Textes ----

    public static Message postName(Village village, String postId) {
        Post post = post(village, postId);
        if (post != null) {
            return post.name();
        }
        if (postId != null && postId.startsWith("@")) {
            return Message.translation(KEYS + "post." + postId.substring(1));
        }
        // Poste d'un bâtiment qui n'est plus debout : le nom du métier du plan.
        VillageLayout layout = Chantiers.layout(village);
        if (layout != null && postId != null) {
            for (VillageLayout.Job job : layout.jobs()) {
                if (job.id().equals(postId)) {
                    return new Post(job.id(), job, job.dialogue(), job.home()).name();
                }
            }
        }
        return Message.raw(postId == null ? "?" : postId);
    }

    /** « Mousseline et Gland », « Mousseline », ou « parents inconnus » (fondateur, arrivant). */
    public static Message parentsText(PopulationState p, Inhabitant h) {
        List<Message> names = new ArrayList<>();
        for (String id : h.parents) {
            Inhabitant parent = p.byId(id);
            if (parent != null) {
                names.add(parent.given());
            }
        }
        if (names.isEmpty()) {
            return Message.translation(KEYS + "noParents");
        }
        if (names.size() == 1) {
            return names.get(0);
        }
        return Message.translation(KEYS + "and").param("a", names.get(0)).param("b", names.get(1));
    }

    /** Âge lisible : jours pour un enfant de moins d'une année, sinon années du village. */
    public static Message ageText(long age) {
        long years = Ages.years(age);
        return years < 1 ? Message.translation(KEYS + "ageDays").param("days", age) : Message.translation(KEYS + "ageYears").param("years", years);
    }

    /** Ligne de chronique lisible. */
    public static Message chronicleLine(Village village, PopulationState p, ChronicleEntry e, long today) {
        Message who = e.who() == null ? Message.raw("?") : nameOf(p, e.who());
        Message other = e.other() == null ? Message.raw("?") : nameOf(p, e.other());
        Message detail = Message.raw(e.detail() == null ? "" : e.detail());
        switch (e.kind()) {
            case "apprentice", "handover", "takes", "oriented", "elder", "death_age", "death_fire" ->
                    detail = e.detail() == null || e.detail().isEmpty() ? Message.translation(KEYS + "noPost") : postName(village, e.detail());
            case "fostered", "rehoused" -> detail = e.detail() == null ? Message.raw("?") : Message.translation(Chantiers.buildingKey(e.detail()));
            case "arrival" -> detail = e.detail() == null ? Message.translation(KEYS + "wilds") : Message.raw(e.detail());
            case "birth" -> other = Message.translation(KEYS + "and").param("a", other)
                    .param("b", e.detail() == null ? Message.translation(KEYS + "alone") : nameOf(p, e.detail()));
            default -> {
            }
        }
        long ago = Math.max(0, today - e.day());
        return Message.translation(KEYS + "chron." + e.kind()).param("who", who).param("other", other).param("detail", detail)
                .param("ago", ago == 0 ? Message.translation(KEYS + "today") : Message.translation(KEYS + "daysAgo").param("days", ago));
    }

    private static Message nameOf(PopulationState p, String id) {
        Inhabitant h = p.byId(id);
        return h == null ? Message.raw("?") : h.fullName();
    }

    static void announce(World world, Village village, Message message) {
        Chantiers.announce(world, village, message, null, NotificationStyle.Default);
    }

    static long seedOf(String villageId, long day) {
        return villageId.hashCode() * 0x9E3779B97F4A7C15L + day * 0xC2B2AE3D27D4EB4FL;
    }

    /** Rang d'âge : vrai si l'habitant est un adulte valide aujourd'hui (pour les volontaires de raid). */
    static boolean ableAdult(Inhabitant h, long day) {
        return h.alive() && h.stage(day) == Ages.Stage.ADULT && !h.convalescent(day);
    }

    // ---- Identité des PNJ ----

    /** Qui est un PNJ du village : son nom et une ligne sur lui (âge, parents, parrain), pour la fenêtre de dialogue. */
    public record Identity(Message name, Message about) {
    }

    /** PNJ posés hors de village/Villagers et request/Criers (enfants, défenseurs) -> {village, habitant}. */
    private static final Map<Ref<EntityStore>, String[]> BOUND = java.util.Collections.synchronizedMap(new java.util.IdentityHashMap<>());

    public static void bind(Ref<EntityStore> ref, String villageId, String inhabitantId) {
        BOUND.put(ref, new String[] {villageId, inhabitantId});
    }

    /** Id de l'habitant lié au PNJ `ref` par {@link #bind}, ou null. */
    public static String boundId(Ref<EntityStore> ref) {
        String[] b = ref == null ? null : BOUND.get(ref);
        return b == null ? null : b[1];
    }

    public static void unbind(Ref<EntityStore> ref) {
        BOUND.remove(ref);
    }

    public static void clearAll() {
        BOUND.clear();
    }

    /** L'habitant que montre le PNJ `npc`, ou null (PNJ d'un autre système, village sans générations). */
    public static Inhabitant inhabitantOf(World world, Ref<EntityStore> npc) {
        if (npc == null) {
            return null;
        }
        String villageId = null;
        String inhabitant = null;
        String post = null;
        String[] bound = BOUND.get(npc);
        dev.nakasar.hytale.peuples.village.Villagers.Posted posted = dev.nakasar.hytale.peuples.village.Villagers.posted(npc);
        if (bound != null) {
            villageId = bound[0];
            inhabitant = bound[1];
        } else if (posted != null) {
            villageId = posted.village();
            if (posted.slot().startsWith(dev.nakasar.hytale.peuples.village.Villagers.RESIDENT)) {
                inhabitant = posted.slot().substring(dev.nakasar.hytale.peuples.village.Villagers.RESIDENT.length());
            } else {
                post = posted.slot();
            }
        } else if ((villageId = dev.nakasar.hytale.peuples.request.Criers.villageOf(npc)) != null) {
            post = CRIER;
        } else if ((villageId = dev.nakasar.hytale.peuples.request.Criers.merchantVillageOf(npc)) != null) {
            post = MERCHANT;
        } else if ((villageId = dev.nakasar.hytale.peuples.request.Criers.chiefVillageOf(npc)) != null) {
            post = CHIEF;
        }
        Village village = villageId == null ? null : Villages.registry(world).byId(villageId);
        if (!applies(village) || !village.population().seeded()) {
            return null;
        }
        PopulationState p = state(village);
        return inhabitant != null ? p.byId(inhabitant) : post != null ? p.holder(post) : null;
    }

    /** Nom et ligne de présentation du PNJ `npc`, ou null s'il n'est pas un habitant. */
    public static Identity identity(World world, Store<EntityStore> store, Ref<EntityStore> npc) {
        Inhabitant h = inhabitantOf(world, npc);
        if (h == null || !h.alive()) {
            return null;
        }
        Village village = null;
        for (Village v : Villages.registry(world).all()) {
            if (applies(v) && v.population().all().contains(h)) {
                village = v;
                break;
            }
        }
        if (village == null) {
            return null;
        }
        PopulationState p = state(village);
        long day = GameClock.day(store);
        Ages.Stage stage = h.stage(day);
        Message what = stage == Ages.Stage.APPRENTICE && !h.vocation().isEmpty()
                ? Message.translation(KEYS + "about.apprentice").param("post", postName(village, h.vocation()))
                : stage == Ages.Stage.ELDER && !h.hasJob() ? Message.translation(KEYS + "about.retired")
                : Message.translation(KEYS + "stage." + stage.key());
        Message origin = h.parents().length > 0 ? Message.translation(KEYS + "about.parents").param("parents", parentsText(p, h))
                : h.from() != null ? Message.translation(KEYS + "about.from").param("village", h.from())
                : Message.translation(KEYS + "about.founder");
        Message about = Message.translation(KEYS + "about.line").param("what", what).param("age", ageText(h.age(day))).param("origin", origin);
        if (h.godparentName() != null) {
            about = Message.translation(KEYS + "about.godparent").param("line", about).param("player", h.godparentName());
        }
        return new Identity(h.fullName(), about);
    }

    /** Pour les journaux : nombre d'habitants vivants par stade. */
    public static Map<Ages.Stage, Integer> census(Village village, long day) {
        Map<Ages.Stage, Integer> out = new LinkedHashMap<>();
        for (Ages.Stage s : Ages.Stage.values()) {
            out.put(s, 0);
        }
        for (Inhabitant h : state(village).living()) {
            out.merge(h.stage(day), 1, Integer::sum);
        }
        return out;
    }
}
