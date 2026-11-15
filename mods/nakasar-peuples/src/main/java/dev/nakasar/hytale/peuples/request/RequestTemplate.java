package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.codec.validation.ValidationResults;

import java.util.ArrayList;
import java.util.List;

/**
 * Un modèle de demande du tableau, asset JSON du mod ({@value #PATH}/&lt;peuple&gt;/&lt;id&gt;.json ; GDD, section Les
 * demandes du tableau). Chaque matin, le village tire ses trois demandes parmi les modèles de son peuple et de son
 * palier, au poids.
 *
 * <pre>
 * {
 *   "People": "Kweebec", "Type": "Gather", "MinTier": 0, "MaxTier": 3, "Weight": 3,
 *   "TitleKey": "...",            titre (tableau, suivi à l'écran)
 *   "TaskKey": "...",             ligne de tâche du suivi ({count}, {needed}, {item}, {distance}, {direction})
 *   "ItemId": "...", "Quantity": 20,           récolte et fabrication : objets à déposer
 *   "Roles": [ ... ],                          chasse : rôles dont la mort compte aussi hors du repaire
 *   "Spawns": [ ... ],                         chasse, défense : la bande ; escorte : les gardiens du captif
 *   "MinDistance": 80, "MaxDistance": 140,     chasse, livraison, escorte : distance du lieu au cœur
 *   "Essor": 10, "Favors": 2                   récompenses : essor du village, faveurs du peuple au joueur
 *   "Reputation": 10                           réputation de village du joueur (défaut : l'essor ; étape 4)
 *   "Members": 3, "Waves": 2, "Duration": 60   caravane, récolte escortée : PNJ escortés, embuscades, durée de récolte (s)
 *   "TargetBlock": "Furniture_Crude_Brazier"   destruction : bloc vanilla posé au lieu (Quantity exemplaires)
 *   "Boss": "Nakasar_Peuples_Boss_Kweebec"     boss : rôle du chef du repaire ; Spawns : ses renforts
 * }
 * </pre>
 */
public final class RequestTemplate implements JsonAssetWithMap<String, DefaultAssetMap<String, RequestTemplate>> {

    public static final String PATH = "Nakasar/Requests";

    private static final ArrayCodec<String> STRINGS = new ArrayCodec<>(Codec.STRING, String[]::new);

    public static final AssetBuilderCodec<String, RequestTemplate> CODEC = AssetBuilderCodec.builder(RequestTemplate.class, RequestTemplate::new,
                    Codec.STRING, (t, id) -> t.id = id, t -> t.id, (t, data) -> t.data = data, t -> t.data)
            .append(new KeyedCodec<>("People", Codec.STRING), (t, v) -> t.people = v, t -> t.people)
            .documentation("Peuple dont les villages tirent cette demande.")
            .add()
            .append(new KeyedCodec<>("Type", Codec.STRING), (t, v) -> t.type = v, t -> t.type)
            .documentation("Gather, Craft, Hunt, Delivery, Escort, Defense, Plant, Caravan, Harvest, Destroy ou Boss.")
            .add()
            .append(new KeyedCodec<>("MinTier", Codec.INTEGER), (t, v) -> t.minTier = v == null ? 0 : v, t -> t.minTier)
            .documentation("Palier minimal du village (0 campement).")
            .add()
            .append(new KeyedCodec<>("MaxTier", Codec.INTEGER), (t, v) -> t.maxTier = v == null ? 3 : v, t -> t.maxTier)
            .documentation("Palier maximal du village (3 bourg).")
            .add()
            .append(new KeyedCodec<>("Weight", Codec.INTEGER), (t, v) -> t.weight = v == null ? 1 : v, t -> t.weight)
            .documentation("Poids au tirage.")
            .add()
            .append(new KeyedCodec<>("TitleKey", Codec.STRING), (t, v) -> t.titleKey = v, t -> t.titleKey)
            .documentation("Titre de la demande.")
            .add()
            .append(new KeyedCodec<>("TaskKey", Codec.STRING), (t, v) -> t.taskKey = v, t -> t.taskKey)
            .documentation("Ligne de tâche ({count}, {needed}, {item}, {distance}, {direction}).")
            .add()
            .append(new KeyedCodec<>("ItemId", Codec.STRING), (t, v) -> t.itemId = v, t -> t.itemId)
            .documentation("Récolte, fabrication : objet à déposer.")
            .add()
            .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (t, v) -> t.quantity = v == null ? 1 : v, t -> t.quantity)
            .documentation("Récolte, fabrication : quantité à déposer.")
            .add()
            .append(new KeyedCodec<>("Roles", STRINGS), (t, v) -> t.roles = v == null ? new String[0] : v, t -> t.roles)
            .documentation("Chasse : rôles de PNJ dont la mort compte, même hors de la bande apparue.")
            .add()
            .append(new KeyedCodec<>("Spawns", STRINGS), (t, v) -> t.spawns = v == null ? new String[0] : v, t -> t.spawns)
            .documentation("Chasse, défense : la bande (un rôle par PNJ) ; escorte : les gardiens du captif.")
            .add()
            .append(new KeyedCodec<>("MinDistance", Codec.INTEGER), (t, v) -> t.minDistance = v == null ? 0 : v, t -> t.minDistance)
            .documentation("Distance minimale du lieu de la demande au cœur du village.")
            .add()
            .append(new KeyedCodec<>("MaxDistance", Codec.INTEGER), (t, v) -> t.maxDistance = v == null ? 0 : v, t -> t.maxDistance)
            .documentation("Distance maximale du lieu de la demande au cœur du village.")
            .add()
            .append(new KeyedCodec<>("Essor", Codec.INTEGER), (t, v) -> t.essor = v == null ? 0 : v, t -> t.essor)
            .documentation("Essor donné au village (une fois par demande).")
            .add()
            .append(new KeyedCodec<>("Favors", Codec.INTEGER), (t, v) -> t.favors = v == null ? 0 : v, t -> t.favors)
            .documentation("Faveurs du peuple données au joueur.")
            .add()
            .append(new KeyedCodec<>("Reputation", Codec.INTEGER), (t, v) -> t.reputation = v, t -> t.reputation)
            .documentation("Réputation de village donnée au joueur (un tiers va au peuple) ; absente : autant que l'essor.")
            .add()
            .append(new KeyedCodec<>("Flag", Codec.STRING), (t, v) -> t.flag = v, t -> t.flag)
            .documentation("Drapeau posé sur le joueur quand il remplit la demande (étapes de la chaîne du peuple).")
            .add()
            .append(new KeyedCodec<>("Workshop", Codec.STRING), (t, v) -> t.workshop = v == null || v.isBlank() ? null : v, t -> t.workshop)
            .documentation("Bâtiment de métier (Workshop) dont c'est une commande ; absent : demande du tableau du village.")
            .add()
            .append(new KeyedCodec<>("MinLevel", Codec.INTEGER), (t, v) -> t.minLevel = v == null ? 1 : v, t -> t.minLevel)
            .documentation("Commande : niveau minimal du bâtiment (1 à 3).")
            .add()
            .append(new KeyedCodec<>("MaxLevel", Codec.INTEGER), (t, v) -> t.maxLevel = v == null ? 3 : v, t -> t.maxLevel)
            .documentation("Commande : niveau maximal du bâtiment (1 à 3).")
            .add()
            .append(new KeyedCodec<>("Specialty", Codec.STRING), (t, v) -> t.specialty = v == null || v.isBlank() ? null : v, t -> t.specialty)
            .documentation("Commande : spécialité du bâtiment qui la propose ; absente : toutes.")
            .add()
            .append(new KeyedCodec<>("Knowledge", Codec.INTEGER), (t, v) -> t.knowledge = v == null ? 0 : v, t -> t.knowledge)
            .documentation("Commande : savoir-faire donné au bâtiment (une fois par commande, comme l'essor).")
            .add()
            .append(new KeyedCodec<>("Master", Codec.BOOLEAN), (t, v) -> t.master = v != null && v, t -> t.master)
            .documentation("Commande de maître (une par niveau, hors tirage du jour) : ouvre le chantier d'amélioration.")
            .add()
            .append(new KeyedCodec<>("Members", Codec.INTEGER), (t, v) -> t.members = v == null ? 3 : v, t -> t.members)
            .documentation("Caravane, récolte escortée : nombre de PNJ du village à escorter.")
            .add()
            .append(new KeyedCodec<>("Waves", Codec.INTEGER), (t, v) -> t.waves = v == null ? 2 : v, t -> t.waves)
            .documentation("Caravane : embuscades le long du chemin ; récolte escortée : attaques pendant la récolte (une de plus à l'aller).")
            .add()
            .append(new KeyedCodec<>("Duration", Codec.INTEGER), (t, v) -> t.duration = v == null ? 60 : v, t -> t.duration)
            .documentation("Récolte escortée : secondes de récolte, joueur présent.")
            .add()
            .append(new KeyedCodec<>("TargetBlock", Codec.STRING), (t, v) -> t.targetBlock = v, t -> t.targetBlock)
            .documentation("Destruction : bloc vanilla posé Quantity fois au lieu de la demande, à briser.")
            .add()
            .append(new KeyedCodec<>("Boss", Codec.STRING), (t, v) -> t.boss = v, t -> t.boss)
            .documentation("Boss : rôle du chef qui attend au repaire (Spawns : ses renforts aux deux tiers et au tiers de sa vie).")
            .add()
            .validator(RequestTemplate::validate)
            .build();

    private static AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> assetStore;

    protected AssetExtraInfo.Data data;
    protected String id;
    String people;
    String type;
    int minTier;
    int maxTier = 3;
    int weight = 1;
    String titleKey;
    String taskKey;
    String itemId;
    int quantity = 1;
    String[] roles = new String[0];
    String[] spawns = new String[0];
    int minDistance;
    int maxDistance;
    int essor;
    int favors;
    Integer reputation;
    String flag;
    String workshop;
    int minLevel = 1;
    int maxLevel = 3;
    String specialty;
    int knowledge;
    boolean master;
    int members = 3;
    int waves = 2;
    int duration = 60;
    String targetBlock;
    String boss;

    RequestTemplate() {
    }

    @SuppressWarnings("unchecked")
    public static AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> getAssetStore() {
        if (assetStore == null) {
            assetStore = (AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>>) (AssetStore<?, ?, ?>)
                    AssetRegistry.getAssetStore(RequestTemplate.class);
        }
        return assetStore;
    }

    /** Modèle d'id `id`, ou null. */
    public static RequestTemplate get(String id) {
        AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> store = getAssetStore();
        return store == null || id == null ? null : store.getAssetMap().getAsset(id);
    }

    /** Modèles du peuple `people` tirables au palier `tier` (tableau du village : sans les commandes des bâtiments). */
    public static List<RequestTemplate> forVillage(String people, int tier) {
        List<RequestTemplate> out = new ArrayList<>();
        AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> store = getAssetStore();
        if (store == null) {
            return out;
        }
        for (RequestTemplate t : store.getAssetMap().getAssetMap().values()) {
            if (t != null && t.people != null && t.people.equalsIgnoreCase(people) && tier >= t.minTier && tier <= t.maxTier
                    && t.weight > 0 && t.type() != null && t.workshop == null) {
                out.add(t);
            }
        }
        out.sort((a, b) -> a.id.compareTo(b.id));
        return out;
    }

    /**
     * Commandes du bâtiment de métier `workshop` tirables à son niveau `level` et pour sa spécialité `specialty` (null :
     * pas encore choisie, seules les commandes sans spécialité).
     */
    public static List<RequestTemplate> forWorkshop(String workshop, int level, String specialty) {
        List<RequestTemplate> out = new ArrayList<>();
        AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> store = getAssetStore();
        if (store == null || workshop == null) {
            return out;
        }
        for (RequestTemplate t : store.getAssetMap().getAssetMap().values()) {
            if (t != null && workshop.equals(t.workshop) && !t.master && level >= t.minLevel && level <= t.maxLevel && t.weight > 0
                    && t.type() != null && (t.specialty == null || t.specialty.equals(specialty))) {
                out.add(t);
            }
        }
        out.sort((a, b) -> a.id.compareTo(b.id));
        return out;
    }

    @Override
    public String getId() {
        return id;
    }

    /** Commande de maître du bâtiment `workshop` à son niveau `level` (spécialité d'abord, sinon commune), ou null. */
    public static RequestTemplate master(String workshop, int level, String specialty) {
        AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> store = getAssetStore();
        if (store == null || workshop == null) {
            return null;
        }
        RequestTemplate common = null;
        for (RequestTemplate t : store.getAssetMap().getAssetMap().values()) {
            if (t != null && t.master && workshop.equals(t.workshop) && level >= t.minLevel && level <= t.maxLevel && t.type() != null) {
                if (t.specialty != null && t.specialty.equals(specialty)) {
                    return t;
                }
                if (t.specialty == null && (common == null || t.id.compareTo(common.id) < 0)) {
                    common = t;
                }
            }
        }
        return common;
    }

    /** Vrai pour une commande de maître. */
    public boolean master() {
        return master;
    }

    /** Bâtiment de métier dont c'est une commande, ou null (demande du tableau). */
    public String workshop() {
        return workshop;
    }

    /** Savoir-faire donné au bâtiment de métier. */
    public int knowledge() {
        return knowledge;
    }

    public String specialty() {
        return specialty;
    }

    public RequestType type() {
        return RequestType.byId(type);
    }

    public String people() {
        return people;
    }

    public int weight() {
        return weight;
    }

    public String titleKey() {
        return titleKey;
    }

    public String taskKey() {
        return taskKey;
    }

    public String itemId() {
        return itemId;
    }

    public int quantity() {
        return quantity;
    }

    public String[] roles() {
        return roles;
    }

    public String[] spawns() {
        return spawns;
    }

    public int minDistance() {
        return minDistance;
    }

    public int maxDistance() {
        return Math.max(minDistance, maxDistance);
    }

    public int essor() {
        return essor;
    }

    /** Réputation de village gagnée par le joueur qui remplit la demande (l'essor si le modèle ne la donne pas). */
    public int reputation() {
        return reputation != null ? reputation : essor;
    }

    public int favors() {
        return favors;
    }

    /** Caravane, récolte escortée : PNJ du village escortés. */
    public int members() {
        return Math.max(1, members);
    }

    /** Caravane : embuscades en chemin ; récolte escortée : attaques pendant la récolte. */
    public int waves() {
        return Math.max(0, waves);
    }

    /** Récolte escortée : secondes de récolte. */
    public int duration() {
        return Math.max(10, duration);
    }

    /** Destruction : bloc à briser. */
    public String targetBlock() {
        return targetBlock;
    }

    /** Boss : rôle du chef du repaire. */
    public String boss() {
        return boss;
    }

    /** Drapeau posé sur le joueur à la fin, ou null. */
    public String flag() {
        return flag;
    }

    /** Ce qu'il faut atteindre : objets déposés, morts de la bande, pousses plantées, ou 1 (livraison, escorte, raid). */
    public int needed() {
        RequestType t = type();
        if (t == null) {
            return 1;
        }
        return switch (t) {
            case GATHER, CRAFT, PLANT, DESTROY -> Math.max(1, quantity);
            case HUNT -> Math.max(1, spawns.length);
            case DELIVERY, ESCORT, DEFENSE, CARAVAN, HARVEST, BOSS, ROUTE -> 1;
        };
    }

    private static void validate(RequestTemplate t, ValidationResults results) {
        RequestType type = t.type();
        if (type == null) {
            results.fail("Type inconnu : " + t.type + " (Gather, Craft, Hunt, Delivery, Escort, Defense, Plant, Caravan, Harvest, Destroy, Boss)");
            return;
        }
        if (t.people == null || t.people.isBlank()) {
            results.fail("People manquant");
        }
        if (t.titleKey == null || t.taskKey == null) {
            results.fail("TitleKey et TaskKey sont obligatoires");
        }
        if (t.workshop != null && (t.minLevel < 1 || t.maxLevel > 3 || t.minLevel > t.maxLevel)) {
            results.fail("Niveaux de bâtiment invalides : " + t.minLevel + " à " + t.maxLevel);
        }
        if (t.minTier < 0 || t.maxTier > 3 || t.minTier > t.maxTier) {
            results.fail("Paliers invalides : " + t.minTier + " à " + t.maxTier);
        }
        if ((type.usesDeposit() || type == RequestType.PLANT) && (t.itemId == null || t.quantity < 1)) {
            results.fail(type.id() + " : ItemId et Quantity (au moins 1) sont obligatoires");
        }
        if (type == RequestType.HUNT && t.spawns.length == 0) {
            results.fail(type.id() + " : Spawns (la bande) est obligatoire");
        }
        if ((type.hasSite() || type == RequestType.CARAVAN) && (t.minDistance < 48 || t.maxDistance < t.minDistance)) {
            results.fail(type.id() + " : MinDistance (48 au moins, hors du village) et MaxDistance (au moins MinDistance) sont obligatoires");
        }
        if ((type == RequestType.CARAVAN || type == RequestType.HARVEST) && (t.spawns.length == 0 || t.members < 1)) {
            results.fail(type.id() + " : Spawns (les assaillants des embuscades) et Members (au moins 1) sont obligatoires");
        }
        if (type == RequestType.DESTROY && (t.targetBlock == null || t.targetBlock.isBlank() || t.quantity < 1)) {
            results.fail("Destroy : TargetBlock et Quantity (au moins 1) sont obligatoires");
        }
        if (type == RequestType.ROUTE && t.maxDistance < 48) {
            results.fail("Route : MaxDistance (villages voisins à relier, 48 au moins) est obligatoire");
        }
        if (type == RequestType.BOSS && (t.boss == null || t.boss.isBlank())) {
            results.fail("Boss : le rôle Boss est obligatoire");
        }
    }
}
