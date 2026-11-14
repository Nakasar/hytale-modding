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
            .documentation("Gather, Craft, Hunt, Delivery, Escort ou Defense.")
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

    /** Modèles du peuple `people` tirables au palier `tier`. */
    public static List<RequestTemplate> forVillage(String people, int tier) {
        List<RequestTemplate> out = new ArrayList<>();
        AssetStore<String, RequestTemplate, DefaultAssetMap<String, RequestTemplate>> store = getAssetStore();
        if (store == null) {
            return out;
        }
        for (RequestTemplate t : store.getAssetMap().getAssetMap().values()) {
            if (t != null && t.people != null && t.people.equalsIgnoreCase(people) && tier >= t.minTier && tier <= t.maxTier
                    && t.weight > 0 && t.type() != null) {
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

    public int favors() {
        return favors;
    }

    /** Ce qu'il faut atteindre : objets déposés, morts de la bande, ou 1 (livraison, escorte). */
    public int needed() {
        RequestType t = type();
        if (t == null) {
            return 1;
        }
        return switch (t) {
            case GATHER, CRAFT -> Math.max(1, quantity);
            case HUNT, DEFENSE -> Math.max(1, spawns.length);
            case DELIVERY, ESCORT -> 1;
        };
    }

    private static void validate(RequestTemplate t, ValidationResults results) {
        RequestType type = t.type();
        if (type == null) {
            results.fail("Type inconnu : " + t.type + " (Gather, Craft, Hunt, Delivery, Escort, Defense)");
            return;
        }
        if (t.people == null || t.people.isBlank()) {
            results.fail("People manquant");
        }
        if (t.titleKey == null || t.taskKey == null) {
            results.fail("TitleKey et TaskKey sont obligatoires");
        }
        if (t.minTier < 0 || t.maxTier > 3 || t.minTier > t.maxTier) {
            results.fail("Paliers invalides : " + t.minTier + " à " + t.maxTier);
        }
        if (type.usesDeposit() && (t.itemId == null || t.quantity < 1)) {
            results.fail(type.id() + " : ItemId et Quantity (au moins 1) sont obligatoires");
        }
        if ((type == RequestType.HUNT || type == RequestType.DEFENSE) && t.spawns.length == 0) {
            results.fail(type.id() + " : Spawns (la bande) est obligatoire");
        }
        if (type.hasSite() && (t.minDistance < 48 || t.maxDistance < t.minDistance)) {
            results.fail(type.id() + " : MinDistance (48 au moins, hors du village) et MaxDistance (au moins MinDistance) sont obligatoires");
        }
    }
}
