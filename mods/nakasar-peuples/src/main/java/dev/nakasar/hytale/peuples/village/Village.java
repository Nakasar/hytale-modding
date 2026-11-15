package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import dev.nakasar.hytale.peuples.request.VillageRequest;

/**
 * Un village : son état sauvegardé avec le monde (ressource {@link VillageRegistry}), ancré sur le bloc cœur invisible
 * {@value Villages#HEART_BLOCK} (GDD, section Villages vivants). Le dépôt (coffre vanilla du peuple) et le tableau
 * (panneau du peuple) sont posés à côté du cœur et retrouvés par leurs coordonnées.
 *
 * <p>Étape 1 : nom, peuple, palier et jauge d'essor. Étape 3 : les demandes du tableau. La réputation de village (étape 4), les
 * bâtiments posés (étape 5) et les raids (étape 6, {@link RaidRecord}) s'ajoutent à ce même objet.
 */
public final class Village {

    public static final BuilderCodec<Village> CODEC = BuilderCodec.builder(Village.class, Village::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (v, s) -> v.id = s, v -> v.id)
            .documentation("Identifiant unique du village.")
            .add()
            .append(new KeyedCodec<>("Name", Codec.STRING), (v, s) -> v.name = s, v -> v.name)
            .documentation("Nom du village, affiché en titre du tableau.")
            .add()
            .append(new KeyedCodec<>("People", Codec.STRING), (v, s) -> v.people = s, v -> v.people)
            .documentation("Peuple du village (Kweebec...).")
            .add()
            .append(new KeyedCodec<>("X", Codec.INTEGER), (v, i) -> v.x = i, v -> v.x).add()
            .append(new KeyedCodec<>("Y", Codec.INTEGER), (v, i) -> v.y = i, v -> v.y).add()
            .append(new KeyedCodec<>("Z", Codec.INTEGER), (v, i) -> v.z = i, v -> v.z).add()
            .append(new KeyedCodec<>("DepositX", Codec.INTEGER), (v, i) -> v.depositX = i, v -> v.depositX).add()
            .append(new KeyedCodec<>("DepositY", Codec.INTEGER), (v, i) -> v.depositY = i, v -> v.depositY).add()
            .append(new KeyedCodec<>("DepositZ", Codec.INTEGER), (v, i) -> v.depositZ = i, v -> v.depositZ).add()
            .append(new KeyedCodec<>("BoardX", Codec.INTEGER), (v, i) -> v.boardX = i, v -> v.boardX).add()
            .append(new KeyedCodec<>("BoardY", Codec.INTEGER), (v, i) -> v.boardY = i, v -> v.boardY).add()
            .append(new KeyedCodec<>("BoardZ", Codec.INTEGER), (v, i) -> v.boardZ = i, v -> v.boardZ).add()
            .append(new KeyedCodec<>("Tier", Codec.INTEGER), (v, i) -> v.tier = Tiers.clamp(i), v -> v.tier)
            .documentation("Palier : 0 campement, 1 hameau, 2 village, 3 bourg.")
            .add()
            .append(new KeyedCodec<>("Essor", Codec.INTEGER), (v, i) -> v.essor = Math.max(0, i == null ? 0 : i), v -> v.essor)
            .documentation("Jauge d'essor partagée par tous les joueurs, vers le palier suivant.")
            .add()
            .append(new KeyedCodec<>("Created", Codec.LONG), (v, l) -> v.created = l == null ? 0L : l, v -> v.created)
            .documentation("Date de fondation (epoch, ms).")
            .add()
            .append(new KeyedCodec<>("Layout", Codec.STRING), (v, s) -> v.layout = s, v -> v.layout)
            .documentation("Plan du village (VillageLayout) s'il a été généré, sinon absent (village fondé à la main).")
            .add()
            .append(new KeyedCodec<>("Auto", Codec.BOOLEAN), (v, b) -> v.auto = b != null && b, v -> v.auto)
            .documentation("Vrai pour le village posé automatiquement près du point d'apparition (VillageSeeder).")
            .add()
            .append(new KeyedCodec<>("Built", new ArrayCodec<>(Codec.STRING, String[]::new)), (v, a) -> v.built = a == null ? new String[0] : a, v -> v.built)
            .documentation("Bâtiments du plan déjà collés (ids VillageLayout.Building).")
            .add()
            .append(new KeyedCodec<>("Banner", Codec.BOOLEAN), (v, b) -> v.banner = b != null && b, v -> v.banner)
            .documentation("Vrai si la bannière de carte a été posée (BannerX/Y/Z).")
            .add()
            .append(new KeyedCodec<>("BannerX", Codec.INTEGER), (v, i) -> v.bannerX = i == null ? 0 : i, v -> v.bannerX).add()
            .append(new KeyedCodec<>("BannerY", Codec.INTEGER), (v, i) -> v.bannerY = i == null ? 0 : i, v -> v.bannerY).add()
            .append(new KeyedCodec<>("BannerZ", Codec.INTEGER), (v, i) -> v.bannerZ = i == null ? 0 : i, v -> v.bannerZ).add()
            .append(new KeyedCodec<>("Requests", new ArrayCodec<>(VillageRequest.CODEC, VillageRequest[]::new)),
                    (v, a) -> v.requests = a == null ? new VillageRequest[0] : a, v -> v.requests)
            .documentation("Demandes du tableau du jour (étape 3), trois au plus.")
            .add()
            .append(new KeyedCodec<>("RequestDay", Codec.LONG), (v, l) -> v.requestDay = l == null ? Long.MIN_VALUE : l, v -> v.requestDay)
            .documentation("Jour de jeu du dernier tirage des demandes (GameClock.day).")
            .add()
            .append(new KeyedCodec<>("Sites", new ArrayCodec<>(Site.CODEC, Site[]::new)), (v, a) -> v.sites = a == null ? new Site[0] : a, v -> v.sites)
            .documentation("Hauteur de pose de chaque bâtiment collé (étape 5).")
            .add()
            .append(new KeyedCodec<>("Burnt", new ArrayCodec<>(Codec.STRING, String[]::new)), (v, a) -> v.burnt = a == null ? new String[0] : a, v -> v.burnt)
            .documentation("Bâtiments brûlés (étape 5) : en ruine jusqu'au prochain chantier.")
            .add()
            .append(new KeyedCodec<>("Chantier", ChantierState.CODEC), (v, c) -> v.chantier = c, v -> v.chantier)
            .documentation("Chantier en cours, ou absent (étape 5).")
            .add()
            .append(new KeyedCodec<>("HeartTier", Codec.INTEGER), (v, i) -> v.heartTier = i == null ? -1 : i, v -> v.heartTier)
            .documentation("Dernier palier du cœur de village appliqué (VillageHeart), -1 : place d'avant les cœurs par peuple.")
            .add()
            .append(new KeyedCodec<>("Raid", RaidRecord.CODEC), (v, r) -> v.raid = r == null ? new RaidRecord() : r, v -> v.raid)
            .documentation("Raids du village (étape 6) : raid attendu, raid en cours, bilan du dernier.")
            .add()
            .append(new KeyedCodec<>("Workshops", new ArrayCodec<>(WorkshopState.CODEC, WorkshopState[]::new)),
                    (v, a) -> v.workshops = a == null ? new WorkshopState[0] : a, v -> v.workshops)
            .documentation("Bâtiments de métier : niveau, savoir-faire, spécialité, commandes du jour, panneau.")
            .add()
            .append(new KeyedCodec<>("Plots", new ArrayCodec<>(PlotState.CODEC, PlotState[]::new)),
                    (v, a) -> v.plots = a == null ? new PlotState[0] : a, v -> v.plots)
            .documentation("Terrains libres E1 et E2 : projet, chantier, démolition, piquets.")
            .add()
            .append(new KeyedCodec<>("Annexes", new ArrayCodec<>(AnnexState.CODEC, AnnexState[]::new)),
                    (v, a) -> v.annexes = a == null ? new AnnexState[0] : a, v -> v.annexes)
            .documentation("Avant-postes de métier rattachés au village : fondation, place, travaux, bâtiment debout.")
            .add()
            .append(new KeyedCodec<>("SettlerDay", Codec.LONG), (v, l) -> v.settlerDay = l == null ? Long.MIN_VALUE : l, v -> v.settlerDay)
            .documentation("Jour de jeu où le dernier colon est apparu (outpost/Settlers : un tous les 7 jours au palier max).")
            .add()
            .append(new KeyedCodec<>("SettlerActive", Codec.BOOLEAN), (v, b) -> v.settlerActive = b != null && b, v -> v.settlerActive)
            .documentation("Vrai tant que le colon attend au village ou suit un joueur (pas encore parti fonder).")
            .add()
            .append(new KeyedCodec<>("SettlerOwner", Codec.STRING), (v, s) -> v.settlerOwner = s, v -> v.settlerOwner)
            .documentation("UUID du joueur que le colon suit, ou absent s'il attend au village.")
            .add()
            .build();

    String id = "";
    String name = "";
    String people = People.KWEEBEC.id();
    int x;
    int y;
    int z;
    int depositX;
    int depositY;
    int depositZ;
    int boardX;
    int boardY;
    int boardZ;
    int tier;
    int heartTier = -1;
    int essor;
    long created;
    String layout;
    boolean auto;
    String[] built = new String[0];
    boolean banner;
    int bannerX;
    int bannerY;
    int bannerZ;
    VillageRequest[] requests = new VillageRequest[0];
    long requestDay = Long.MIN_VALUE;
    Site[] sites = new Site[0];
    String[] burnt = new String[0];
    ChantierState chantier;
    RaidRecord raid = new RaidRecord();
    PlotState[] plots = new PlotState[0];
    WorkshopState[] workshops = new WorkshopState[0];
    AnnexState[] annexes = new AnnexState[0];
    long settlerDay = Long.MIN_VALUE;
    boolean settlerActive;
    String settlerOwner;

    Village() {
    }

    Village(String id, String name, People people, int x, int y, int z) {
        this.id = id;
        this.name = name;
        this.people = people.id();
        this.x = x;
        this.y = y;
        this.z = z;
        this.created = System.currentTimeMillis();
    }

    Village copy() {
        Village v = new Village();
        v.id = id;
        v.name = name;
        v.people = people;
        v.x = x;
        v.y = y;
        v.z = z;
        v.depositX = depositX;
        v.depositY = depositY;
        v.depositZ = depositZ;
        v.boardX = boardX;
        v.boardY = boardY;
        v.boardZ = boardZ;
        v.tier = tier;
        v.heartTier = heartTier;
        v.essor = essor;
        v.created = created;
        v.layout = layout;
        v.auto = auto;
        v.built = built.clone();
        v.banner = banner;
        v.bannerX = bannerX;
        v.bannerY = bannerY;
        v.bannerZ = bannerZ;
        v.requests = new VillageRequest[requests.length];
        for (int i = 0; i < requests.length; i++) {
            v.requests[i] = requests[i] == null ? null : requests[i].copy();
        }
        v.requestDay = requestDay;
        v.sites = sites.clone();
        v.burnt = burnt.clone();
        v.chantier = chantier == null ? null : chantier.copy();
        v.raid = raid == null ? new RaidRecord() : raid.copy();
        v.settlerDay = settlerDay;
        v.settlerActive = settlerActive;
        v.settlerOwner = settlerOwner;
        v.annexes = new AnnexState[annexes.length];
        for (int i = 0; i < annexes.length; i++) {
            v.annexes[i] = annexes[i] == null ? null : annexes[i].copy();
        }
        v.workshops = new WorkshopState[workshops.length];
        for (int i = 0; i < workshops.length; i++) {
            v.workshops[i] = workshops[i] == null ? null : workshops[i].copy();
        }
        return v;
    }

    public String id() {
        return id;
    }

    public String name() {
        return name;
    }

    /** Peuple du village ; Kweebec si l'id sauvegardé n'existe plus. */
    public People people() {
        People p = People.byId(people);
        return p == null ? People.KWEEBEC : p;
    }

    public int x() {
        return x;
    }

    public int y() {
        return y;
    }

    public int z() {
        return z;
    }

    public int tier() {
        return tier;
    }

    public int essor() {
        return essor;
    }

    /** Plan du village, ou null pour un village fondé à la main ({@code /village fonder}). */
    public String layout() {
        return layout;
    }

    /** Vrai pour le village posé automatiquement près du point d'apparition. */
    public boolean isAuto() {
        return auto;
    }

    /** Ids des bâtiments du plan déjà collés. */
    public String[] built() {
        return built.clone();
    }

    public boolean hasBanner() {
        return banner;
    }

    public int[] banner() {
        return new int[] {bannerX, bannerY, bannerZ};
    }

    void setBanner(int bx, int by, int bz) {
        banner = true;
        bannerX = bx;
        bannerY = by;
        bannerZ = bz;
    }

    void clearBanner() {
        banner = false;
    }

    void markGenerated(String layoutId, boolean automatic, String[] buildings) {
        layout = layoutId;
        auto = automatic;
        built = buildings.clone();
    }

    /** Distance horizontale au carré du cœur à (px, pz). */
    public double horizontalDistanceSquared(double px, double pz) {
        double dx = px - (x + 0.5);
        double dz = pz - (z + 0.5);
        return dx * dx + dz * dz;
    }

    public boolean isBoard(int bx, int by, int bz) {
        return bx == boardX && by == boardY && bz == boardZ;
    }

    public boolean isDeposit(int bx, int by, int bz) {
        return bx == depositX && by == depositY && bz == depositZ;
    }

    public int[] deposit() {
        return new int[] {depositX, depositY, depositZ};
    }

    public int[] board() {
        return new int[] {boardX, boardY, boardZ};
    }

    void setDeposit(int dx, int dy, int dz) {
        depositX = dx;
        depositY = dy;
        depositZ = dz;
    }

    void setBoard(int bx, int by, int bz) {
        boardX = bx;
        boardY = by;
        boardZ = bz;
    }

    /** Distance au carré du cœur à (px, py, pz). */
    public double distanceSquared(double px, double py, double pz) {
        double dx = px - (x + 0.5);
        double dy = py - (y + 0.5);
        double dz = pz - (z + 0.5);
        return dx * dx + dy * dy + dz * dz;
    }

    /**
     * Ajoute `amount` (négatif : retire) à la jauge d'essor, bornée entre 0 et le seuil du palier suivant : une jauge
     * pleine attend son chantier (étape 5) au lieu de déborder. Rend le gain réel.
     */
    int addEssor(int amount) {
        int before = essor;
        essor = Math.max(0, Math.min(Tiers.threshold(tier), essor + amount));
        return essor - before;
    }

    /** Demandes du tableau (copie du tableau ; les cases vides sont null). */
    public VillageRequest[] requests() {
        return requests.clone();
    }

    /** Jour du dernier tirage des demandes. */
    public long requestDay() {
        return requestDay;
    }

    void setRequests(VillageRequest[] value, long day) {
        requests = value == null ? new VillageRequest[0] : value.clone();
        requestDay = day;
    }

    void setRequest(int slot, VillageRequest request) {
        if (slot >= 0 && slot < requests.length) {
            requests[slot] = request;
        }
    }

    /** États des bâtiments de métier connus du village (copie du tableau, objets sauvegardés). */
    public WorkshopState[] workshops() {
        return workshops.clone();
    }

    /** État sauvegardé du bâtiment de métier `workshopId`, créé au niveau I s'il manque (thread du monde). */
    public WorkshopState workshop(String workshopId) {
        for (WorkshopState w : workshops) {
            if (w != null && w.id.equals(workshopId)) {
                return w;
            }
        }
        WorkshopState created = new WorkshopState(workshopId);
        WorkshopState[] grown = java.util.Arrays.copyOf(workshops, workshops.length + 1);
        grown[workshops.length] = created;
        workshops = grown;
        return created;
    }

    /** Avant-postes connus du village (copie du tableau, objets sauvegardés). */
    public AnnexState[] annexes() {
        return java.util.Arrays.stream(annexes).filter(java.util.Objects::nonNull).toArray(AnnexState[]::new);
    }

    /** Avant-poste du bâtiment de métier `workshopId`, ou null. */
    public AnnexState annex(String workshopId) {
        for (AnnexState a : annexes) {
            if (a != null && a.id.equals(workshopId)) {
                return a;
            }
        }
        return null;
    }

    /** Avant-poste du bâtiment de métier `workshopId`, créé (fondation pas encore remise) s'il manque (thread du monde). */
    public AnnexState ensureAnnex(String workshopId) {
        AnnexState found = annex(workshopId);
        if (found != null) {
            return found;
        }
        AnnexState created = new AnnexState(workshopId);
        AnnexState[] grown = java.util.Arrays.copyOf(annexes, annexes.length + 1);
        grown[annexes.length] = created;
        annexes = grown;
        return created;
    }

    /** Oublie l'avant-poste `workshopId` et l'état de son bâtiment de métier (commande d'administration). */
    public void forgetAnnex(String workshopId) {
        annexes = java.util.Arrays.stream(annexes).filter(a -> a != null && !a.id.equals(workshopId)).toArray(AnnexState[]::new);
        forgetWorkshop(workshopId);
    }

    /** État sauvegardé du terrain `plotId` (E1, E2), créé vide s'il manque (thread du monde). */
    public PlotState plot(String plotId) {
        for (PlotState p : plots) {
            if (p != null && p.id.equals(plotId)) {
                return p;
            }
        }
        PlotState created = new PlotState(plotId);
        PlotState[] grown = java.util.Arrays.copyOf(plots, plots.length + 1);
        grown[plots.length] = created;
        plots = grown;
        return created;
    }

    /** Oublie l'état du bâtiment de métier `workshopId` (bâtiment d'emplacement démoli : il repartira au niveau I). */
    void forgetWorkshop(String workshopId) {
        workshops = java.util.Arrays.stream(workshops).filter(w -> w != null && !w.id.equals(workshopId)).toArray(WorkshopState[]::new);
    }

    /** Le bâtiment n'est plus là du tout (démoli) : ni collé ni brûlé, sa hauteur de pose oubliée. */
    void unmarkBuilt(String buildingId) {
        built = without(built, buildingId);
        burnt = without(burnt, buildingId);
        sites = java.util.Arrays.stream(sites).filter(s -> !s.id.equals(buildingId)).toArray(Site[]::new);
    }

    /** Bâtiment de métier dont le panneau est en (x, y, z), ou null. */
    public WorkshopState workshopAt(int bx, int by, int bz) {
        for (WorkshopState w : workshops) {
            if (w != null && w.isBoard(bx, by, bz)) {
                return w;
            }
        }
        return null;
    }

    /** Raids du village (étape 6) : l'objet sauvegardé, modifiable sur le thread du monde. */
    public RaidRecord raid() {
        if (raid == null) {
            raid = new RaidRecord();
        }
        return raid;
    }

    /** Chantier en cours, ou null. */
    public ChantierState chantier() {
        return chantier;
    }

    void setChantier(ChantierState value) {
        chantier = value;
    }

    /** Bâtiments brûlés (ids du plan). */
    public String[] burnt() {
        return burnt.clone();
    }

    public boolean isBuilt(String buildingId) {
        return contains(built, buildingId);
    }

    public boolean isBurnt(String buildingId) {
        return contains(burnt, buildingId);
    }

    /** Hauteur de pose du bâtiment, ou {@link Integer#MIN_VALUE} si elle n'a pas été gardée. */
    public int siteY(String buildingId) {
        for (Site s : sites) {
            if (s.id.equals(buildingId)) {
                return s.y;
            }
        }
        return Integer.MIN_VALUE;
    }

    void setSiteY(String buildingId, int value) {
        for (Site s : sites) {
            if (s.id.equals(buildingId)) {
                s.y = value;
                return;
            }
        }
        Site[] grown = java.util.Arrays.copyOf(sites, sites.length + 1);
        grown[sites.length] = new Site(buildingId, value);
        sites = grown;
    }

    /** Le bâtiment est debout (collé, pas brûlé). */
    void markBuilt(String buildingId) {
        if (!contains(built, buildingId)) {
            String[] grown = java.util.Arrays.copyOf(built, built.length + 1);
            grown[built.length] = buildingId;
            built = grown;
        }
        burnt = without(burnt, buildingId);
    }

    /** Le bâtiment a brûlé : il reste compté comme collé (ses ruines sont là) mais plus debout. */
    void markBurnt(String buildingId) {
        if (!contains(burnt, buildingId)) {
            String[] grown = java.util.Arrays.copyOf(burnt, burnt.length + 1);
            grown[burnt.length] = buildingId;
            burnt = grown;
        }
    }

    /** Bâtiment debout : collé et pas brûlé. */
    public boolean isStanding(String buildingId) {
        return contains(built, buildingId) && !contains(burnt, buildingId);
    }

    void setEssor(int value) {
        essor = Math.max(0, Math.min(Tiers.threshold(tier), value));
    }

    private static boolean contains(String[] values, String value) {
        for (String v : values) {
            if (v.equals(value)) {
                return true;
            }
        }
        return false;
    }

    private static String[] without(String[] values, String value) {
        return java.util.Arrays.stream(values).filter(v -> !v.equals(value)).toArray(String[]::new);
    }

    /** Dernier palier du cœur de village appliqué ({@link VillageHeart}), -1 avant les cœurs par peuple. */
    public int heartTier() {
        return heartTier;
    }

    void setHeartTier(int value) {
        heartTier = value;
    }

    void setTier(int value) {
        tier = Tiers.clamp(value);
        essor = Math.min(essor, Tiers.threshold(tier));
    }

    /** Jour où le dernier colon est apparu ({@code outpost/Settlers}), {@link Long#MIN_VALUE} jamais. */
    public long settlerDay() {
        return settlerDay;
    }

    /** Vrai tant que le colon du village attend ou suit un joueur. */
    public boolean settlerActive() {
        return settlerActive;
    }

    /** UUID du joueur que suit le colon, ou null. */
    public String settlerOwner() {
        return settlerOwner;
    }

    /** Un colon apparaît au village le jour `day`. */
    public void startSettler(long day) {
        settlerDay = day;
        settlerActive = true;
        settlerOwner = null;
    }

    /** Le colon suit `owner` (UUID), ou attend au village (null). */
    public void setSettlerOwner(String owner) {
        settlerOwner = owner;
    }

    /** Le colon est parti fonder (ou n'existe plus). */
    public void endSettler() {
        settlerActive = false;
        settlerOwner = null;
    }
}
