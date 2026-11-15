package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.codec.validation.ValidationResults;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.VillageLayout;

import java.util.ArrayList;
import java.util.List;

/**
 * Un bâtiment de métier (GDD des bâtiments de métier), asset JSON {@value #PATH}/&lt;id&gt;.json généré par
 * {@code tools/generate_workshops.py} : un bâtiment d'un plan de village dont le villageois à métier produit quelque
 * chose. Il a son niveau et son savoir-faire ({@link dev.nakasar.hytale.peuples.village.WorkshopState}) et ses
 * commandes (modèles de demande dont {@code Workshop} vaut cet id).
 *
 * <pre>
 * { "People": "Kweebec", "Layout": "Kweebec_Oak", "Building": "Enclos", "Job": "Eleveur", "Icon": "Ingredient_Hay",
 *   "NameKey": "nakasar_peuples.workshop.Kweebec_Enclos.name", "Board": [30, -13, 3] }
 * </pre>
 * {@code Board} : place du panneau {@code [x, z, lacet]} relative au cœur (la hauteur est prise au sol) ; lacet 0 face
 * au sud, 1 à l'est, 2 au nord, 3 à l'ouest.
 */
public final class Workshop implements JsonAssetWithMap<String, DefaultAssetMap<String, Workshop>> {

    public static final String PATH = "Nakasar/Workshops";

    /**
     * Le chantier d'amélioration vers le niveau {@code Level} (étape 2) : matériaux pris au dépôt, durée en heures de
     * jeu, et décor vanilla posé à la fin ({@code "dx dy dz lacet Bloc"} relatifs au panneau, seulement dans l'air).
     */
    public static final class Upgrade {
        public static final BuilderCodec<Upgrade> CODEC = BuilderCodec.builder(Upgrade.class, Upgrade::new)
                .append(new KeyedCodec<>("Level", Codec.INTEGER), (u, v) -> u.level = v == null ? 2 : v, u -> u.level).add()
                .append(new KeyedCodec<>("Hours", Codec.INTEGER), (u, v) -> u.hours = v == null ? 12 : Math.max(0, v), u -> u.hours).add()
                .append(new KeyedCodec<>("Materials", new ArrayCodec<>(VillageLayout.Material.CODEC, VillageLayout.Material[]::new)),
                        (u, v) -> u.materials = v == null ? new VillageLayout.Material[0] : v, u -> u.materials).add()
                .append(new KeyedCodec<>("Decor", Codec.STRING_ARRAY), (u, v) -> u.decor = v == null ? new String[0] : v, u -> u.decor).add()
                .build();

        int level = 2;
        int hours = 12;
        VillageLayout.Material[] materials = new VillageLayout.Material[0];
        String[] decor = new String[0];

        public int level() {
            return level;
        }

        public int hours() {
            return hours;
        }

        public VillageLayout.Material[] materials() {
            return materials;
        }

        public String[] decor() {
            return decor;
        }
    }

    /**
     * Une spécialité (étape 3), choisie au niveau II par un joueur de rang Ami, pour tout le village : son nom, sa ligne
     * de description, son icône vanilla et, pour un enclos, les bêtes qu'elle y met (rôles vanilla Tamed_* ou du mod).
     */
    /** Effet en raid d'une spécialité de garde (étape 5). */
    public static final class Raid {
        public static final BuilderCodec<Raid> CODEC = BuilderCodec.builder(Raid.class, Raid::new)
                .append(new KeyedCodec<>("Guards", Codec.INTEGER), (r, v) -> r.guards = v == null ? 0 : Math.max(0, v), r -> r.guards).add()
                .append(new KeyedCodec<>("Posted", Codec.INTEGER), (r, v) -> r.posted = v == null ? 0 : Math.max(0, v), r -> r.posted).add()
                .append(new KeyedCodec<>("Health", Codec.FLOAT), (r, v) -> r.health = v == null ? 1f : Math.max(1f, v), r -> r.health).add()
                .build();

        int guards;
        int posted;
        float health = 1f;

        /** Gardes de plus autour du cœur. */
        public int guards() {
            return guards;
        }

        /** Gardes postés au bâtiment. */
        public int posted() {
            return posted;
        }

        /** Multiplicateur des PV maximaux des gardes. */
        public float health() {
            return health;
        }
    }

    public static final class Specialty {
        public static final BuilderCodec<Specialty> CODEC = BuilderCodec.builder(Specialty.class, Specialty::new)
                .append(new KeyedCodec<>("Id", Codec.STRING), (s, v) -> s.id = v, s -> s.id).add()
                .append(new KeyedCodec<>("NameKey", Codec.STRING), (s, v) -> s.nameKey = v, s -> s.nameKey).add()
                .append(new KeyedCodec<>("LineKey", Codec.STRING), (s, v) -> s.lineKey = v, s -> s.lineKey).add()
                .append(new KeyedCodec<>("Icon", Codec.STRING), (s, v) -> s.icon = v, s -> s.icon).add()
                .append(new KeyedCodec<>("Animals", Codec.STRING_ARRAY), (s, v) -> s.animals = v == null ? new String[0] : v, s -> s.animals).add()
                .append(new KeyedCodec<>("Shops", Codec.STRING_ARRAY), (s, v) -> s.shops = v == null ? new String[0] : v, s -> s.shops).add()
                .append(new KeyedCodec<>("ShareItem", Codec.STRING), (s, v) -> s.shareItem = v, s -> s.shareItem).add()
                .append(new KeyedCodec<>("ShareQuantity", Codec.INTEGER), (s, v) -> s.shareQuantity = v == null ? 1 : Math.max(1, v), s -> s.shareQuantity).add()
                .append(new KeyedCodec<>("Raid", Raid.CODEC), (s, v) -> s.raid = v, s -> s.raid).add()
                .build();

        String id;
        String nameKey;
        String lineKey;
        String icon;
        String[] animals = new String[0];
        /** Boutiques de la spécialité aux niveaux II et III (étape 4). */
        String[] shops = new String[0];
        /** Lot quotidien de la Part de l'Hôte (niveau III). */
        String shareItem;
        int shareQuantity = 1;
        Raid raid;

        /** Effet en raid (spécialité de garde), ou null. */
        public Raid raid() {
            return raid;
        }

        /** Boutique de la spécialité au niveau `level` (2 ou 3), ou null. */
        public String shop(int level) {
            int i = level - 2;
            return i >= 0 && i < shops.length ? shops[i] : null;
        }

        public String shareItem() {
            return shareItem;
        }

        public int shareQuantity() {
            return shareQuantity;
        }

        public String id() {
            return id;
        }

        public String nameKey() {
            return nameKey;
        }

        public String lineKey() {
            return lineKey;
        }

        public String icon() {
            return icon;
        }

        public String[] animals() {
            return animals;
        }
    }

    public static final AssetBuilderCodec<String, Workshop> CODEC = AssetBuilderCodec.builder(Workshop.class, Workshop::new,
                    Codec.STRING, (w, id) -> w.id = id, w -> w.id, (w, data) -> w.data = data, w -> w.data)
            .append(new KeyedCodec<>("People", Codec.STRING), (w, v) -> w.people = v, w -> w.people)
            .documentation("Peuple du bâtiment.")
            .add()
            .append(new KeyedCodec<>("Layout", Codec.STRING), (w, v) -> w.layout = v, w -> w.layout)
            .documentation("Plan de village (VillageLayout) qui porte le bâtiment.")
            .add()
            .append(new KeyedCodec<>("Building", Codec.STRING), (w, v) -> w.building = v, w -> w.building)
            .documentation("Bâtiment du plan.")
            .add()
            .append(new KeyedCodec<>("Job", Codec.STRING), (w, v) -> w.job = v, w -> w.job)
            .documentation("Métier du plan qui y travaille (son villageois tient le bâtiment).")
            .add()
            .append(new KeyedCodec<>("Icon", Codec.STRING), (w, v) -> w.icon = v, w -> w.icon)
            .documentation("Objet vanilla montré en tête de la page du bâtiment.")
            .add()
            .append(new KeyedCodec<>("NameKey", Codec.STRING), (w, v) -> w.nameKey = v, w -> w.nameKey)
            .documentation("Nom du bâtiment.")
            .add()
            .append(new KeyedCodec<>("Board", Codec.INT_ARRAY), (w, v) -> w.board = v, w -> w.board)
            .documentation("Place du panneau [x, z, lacet] relative au cœur du village.")
            .add()
            .append(new KeyedCodec<>("Upgrades", new ArrayCodec<>(Upgrade.CODEC, Upgrade[]::new)),
                    (w, v) -> w.upgrades = v == null ? new Upgrade[0] : v, w -> w.upgrades)
            .documentation("Chantiers d'amélioration vers les niveaux II et III.")
            .add()
            .append(new KeyedCodec<>("Specialties", new ArrayCodec<>(Specialty.CODEC, Specialty[]::new)),
                    (w, v) -> w.specialties = v == null ? new Specialty[0] : v, w -> w.specialties)
            .documentation("Spécialités au choix au niveau II.")
            .add()
            .append(new KeyedCodec<>("Livestock", Codec.STRING_ARRAY), (w, v) -> w.livestock = v == null ? new String[0] : v, w -> w.livestock)
            .documentation("Bêtes de base d'un enclos (niveau I, ou sans spécialité).")
            .add()
            .append(new KeyedCodec<>("LivestockCount", Codec.INT_ARRAY), (w, v) -> w.livestockCount = v, w -> w.livestockCount)
            .documentation("Nombre de bêtes par niveau (I, II, III).")
            .add()
            .append(new KeyedCodec<>("Pen", Codec.INT_ARRAY), (w, v) -> w.pen = v, w -> w.pen)
            .documentation("Intérieur de l'enclos [x0, x1, z0, z1] relatif au cœur.")
            .add()
            .append(new KeyedCodec<>("Shop", Codec.STRING), (w, v) -> w.shop = v, w -> w.shop)
            .documentation("Boutique de troc vanilla du niveau I (et sans spécialité).")
            .add()
            .validator(Workshop::validate)
            .build();

    private static AssetStore<String, Workshop, DefaultAssetMap<String, Workshop>> assetStore;

    protected AssetExtraInfo.Data data;
    protected String id;
    String people;
    String layout;
    String building;
    String job;
    String icon;
    String nameKey;
    int[] board;
    Upgrade[] upgrades = new Upgrade[0];
    Specialty[] specialties = new Specialty[0];
    String[] livestock = new String[0];
    int[] livestockCount;
    int[] pen;
    String shop;

    Workshop() {
    }

    @SuppressWarnings("unchecked")
    public static AssetStore<String, Workshop, DefaultAssetMap<String, Workshop>> getAssetStore() {
        if (assetStore == null) {
            assetStore = (AssetStore<String, Workshop, DefaultAssetMap<String, Workshop>>) (AssetStore<?, ?, ?>)
                    AssetRegistry.getAssetStore(Workshop.class);
        }
        return assetStore;
    }

    /** Bâtiment d'id `id`, ou null. */
    public static Workshop get(String id) {
        AssetStore<String, Workshop, DefaultAssetMap<String, Workshop>> store = getAssetStore();
        return store == null || id == null ? null : store.getAssetMap().getAsset(id);
    }

    /** Bâtiments de métier du plan `layout`, triés par id. */
    public static List<Workshop> forLayout(String layout) {
        List<Workshop> out = new ArrayList<>();
        AssetStore<String, Workshop, DefaultAssetMap<String, Workshop>> store = getAssetStore();
        if (store == null || layout == null) {
            return out;
        }
        for (Workshop w : store.getAssetMap().getAssetMap().values()) {
            if (w != null && layout.equals(w.layout)) {
                out.add(w);
            }
        }
        out.sort((a, b) -> a.id.compareTo(b.id));
        return out;
    }

    @Override
    public String getId() {
        return id;
    }

    public People people() {
        People p = People.byId(people);
        return p == null ? People.KWEEBEC : p;
    }

    public String layout() {
        return layout;
    }

    public String building() {
        return building;
    }

    public String job() {
        return job;
    }

    public String icon() {
        return icon;
    }

    public String nameKey() {
        return nameKey != null ? nameKey : "nakasar_peuples.workshop." + id + ".name";
    }

    /** {@code [x, z, lacet]} du panneau, relatif au cœur, ou null. */
    public int[] board() {
        return board == null || board.length < 2 ? null : board;
    }

    /** Chantier d'amélioration vers le niveau `level`, ou null. */
    public Upgrade upgrade(int level) {
        for (Upgrade u : upgrades) {
            if (u != null && u.level == level) {
                return u;
            }
        }
        return null;
    }

    public Specialty[] specialties() {
        return specialties;
    }

    /** Spécialité `id` du bâtiment, ou null. */
    public Specialty specialty(String id) {
        if (id == null) {
            return null;
        }
        for (Specialty s : specialties) {
            if (s != null && id.equals(s.id)) {
                return s;
            }
        }
        return null;
    }

    /** Boutique de base (niveau I, ou bâtiment sans spécialité), ou null. */
    public String baseShop() {
        return shop;
    }

    /** Vrai si le bâtiment est un enclos (il a des bêtes et une emprise). */
    public boolean isPen() {
        return livestock.length > 0 && pen != null && pen.length == 4;
    }

    /** {@code [x0, x1, z0, z1]} de l'intérieur de l'enclos, relatif au cœur, ou null. */
    public int[] pen() {
        return isPen() ? pen : null;
    }

    /** Bêtes de l'enclos au niveau `level` avec la spécialité `specialty` (null : celles de base). */
    public String[] animals(int level, String specialty) {
        Specialty s = level >= 2 ? specialty(specialty) : null;
        return s != null && s.animals.length > 0 ? s.animals : livestock;
    }

    /** Nombre de bêtes de l'enclos au niveau `level` (3, 5 puis 7). */
    public int livestockCount(int level) {
        int[] counts = livestockCount == null || livestockCount.length == 0 ? new int[] {3, 5, 7} : livestockCount;
        return counts[Math.max(0, Math.min(counts.length - 1, level - 1))];
    }

    private static void validate(Workshop w, ValidationResults results) {
        if (People.byId(w.people) == null) {
            results.fail("Peuple inconnu : " + w.people);
        }
        if (w.layout == null || w.building == null || w.job == null) {
            results.fail("Layout, Building et Job sont obligatoires");
        }
        if (w.board == null || w.board.length < 2) {
            results.fail("Board [x, z, lacet] est obligatoire");
        }
    }
}
