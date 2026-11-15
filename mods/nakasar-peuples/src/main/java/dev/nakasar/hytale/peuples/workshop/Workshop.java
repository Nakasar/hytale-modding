package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.validation.ValidationResults;
import dev.nakasar.hytale.peuples.village.People;

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
