package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.assetstore.AssetExtraInfo;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.assetstore.AssetStore;
import com.hypixel.hytale.assetstore.codec.AssetBuilderCodec;
import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.assetstore.map.JsonAssetWithMap;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import dev.nakasar.hytale.peuples.village.People;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Un genre de lieu-dit d'un peuple (Kevin, 16 novembre 2026), asset JSON {@value #PATH}/&lt;Peuple&gt;_&lt;Type&gt;.json généré
 * par {@code tools/generate_hamlets.py} depuis {@code tools/hamlets.py} : un groupe de 1 à 3 prefabs vanilla (mine,
 * ferme, moulin, caserne et ses deux tours, forge avec mine et comptoir ou tour tirés au sort...), ses habitants, son
 * dialogue et son troc. Le lieu-dit posé dans le monde est un état du monde vivant ({@link Hamlets}).
 *
 * <p>Repère local : la place du lieu-dit à l'origine, le bâtiment principal au nord (-z) ; chaque bâtiment est une ligne
 * {@code "chemin x z rot côté chance x0 x1 z0 z1 haut"} (côté M principal, W ou E ; un tirage par côté).
 */
public final class Hamlet implements JsonAssetWithMap<String, DefaultAssetMap<String, Hamlet>> {

    public static final String PATH = "Nakasar/Hamlets";

    /** Un bâtiment du lieu-dit, dans le repère de la place. */
    public record Building(String prefab, int x, int z, int rotation, String side, double chance, int x0, int x1, int z0, int z1,
                           int height) {

        static Building parse(String line) {
            String[] p = line.trim().split("\\s+");
            if (p.length != 11) {
                return null;
            }
            try {
                return new Building(p[0], Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3]), p[4],
                        Double.parseDouble(p[5]), Integer.parseInt(p[6]), Integer.parseInt(p[7]), Integer.parseInt(p[8]),
                        Integer.parseInt(p[9]), Integer.parseInt(p[10]));
            } catch (NumberFormatException e) {
                return null;
            }
        }
    }

    public static final AssetBuilderCodec<String, Hamlet> CODEC = AssetBuilderCodec.builder(Hamlet.class, Hamlet::new,
                    Codec.STRING, (h, id) -> h.id = id, h -> h.id, (h, data) -> h.data = data, h -> h.data)
            .append(new KeyedCodec<>("People", Codec.STRING), (h, v) -> h.people = v, h -> h.people)
            .documentation("Peuple du lieu-dit (style de ses bâtiments, ses habitants).")
            .add()
            .append(new KeyedCodec<>("Type", Codec.STRING), (h, v) -> h.type = v, h -> h.type)
            .documentation("Genre : Mine, Ferme, Moulin, Caserne, Forge, Comptoir, Scierie, Chasse, Bosquet.")
            .add()
            .append(new KeyedCodec<>("NameKey", Codec.STRING), (h, v) -> h.nameKey = v, h -> h.nameKey)
            .documentation("Clé de langue du nom du genre.")
            .add()
            .append(new KeyedCodec<>("Icon", Codec.STRING), (h, v) -> h.icon = v, h -> h.icon)
            .documentation("Objet vanilla qui représente le lieu-dit.")
            .add()
            .append(new KeyedCodec<>("Rule", Codec.STRING), (h, v) -> h.rule = v == null ? "NONE" : v, h -> h.rule)
            .documentation("Terrain préféré (FERTILE, ROCK, TREES, NONE), comme les avant-postes.")
            .add()
            .append(new KeyedCodec<>("Weight", Codec.INTEGER), (h, v) -> h.weight = v == null ? 1 : Math.max(0, v), h -> h.weight)
            .documentation("Poids du tirage du genre parmi ceux du peuple.")
            .add()
            .append(new KeyedCodec<>("Buildings", Codec.STRING_ARRAY), (h, v) -> h.buildingLines = v == null ? new String[0] : v,
                    h -> h.buildingLines)
            .documentation("« chemin x z rot côté chance x0 x1 z0 z1 haut » dans le repère de la place.")
            .add()
            .append(new KeyedCodec<>("Decor", Codec.STRING_ARRAY), (h, v) -> h.decor = v == null ? new String[0] : v, h -> h.decor)
            .documentation("Blocs vanilla « dx dy dz lacet Bloc » relatifs à la place, posés seulement dans l'air.")
            .add()
            .append(new KeyedCodec<>("Residents", Codec.STRING_ARRAY), (h, v) -> h.residents = v == null ? new String[0] : v,
                    h -> h.residents)
            .documentation("Rôles des habitants (1 à 3), le premier est le tenancier.")
            .add()
            .append(new KeyedCodec<>("Dialogue", Codec.STRING), (h, v) -> h.dialogue = v, h -> h.dialogue)
            .documentation("Dialogue des habitants.")
            .add()
            .append(new KeyedCodec<>("Shop", Codec.STRING), (h, v) -> h.shop = v, h -> h.shop)
            .documentation("Troc du lieu-dit.")
            .add()
            .append(new KeyedCodec<>("ShopBusy", Codec.STRING), (h, v) -> h.shopBusy = v, h -> h.shopBusy)
            .documentation("Troc du lieu-dit animé.")
            .add()
            .build();

    private static AssetStore<String, Hamlet, DefaultAssetMap<String, Hamlet>> assetStore;

    protected AssetExtraInfo.Data data;
    protected String id;
    String people;
    String type;
    String nameKey;
    String icon;
    String rule = "NONE";
    int weight = 1;
    String[] buildingLines = new String[0];
    String[] decor = new String[0];
    String[] residents = new String[0];
    String dialogue;
    String shop;
    String shopBusy;
    private List<Building> buildings;

    Hamlet() {
    }

    @SuppressWarnings("unchecked")
    public static AssetStore<String, Hamlet, DefaultAssetMap<String, Hamlet>> getAssetStore() {
        if (assetStore == null) {
            assetStore = (AssetStore<String, Hamlet, DefaultAssetMap<String, Hamlet>>) (AssetStore<?, ?, ?>)
                    AssetRegistry.getAssetStore(Hamlet.class);
        }
        return assetStore;
    }

    public static Hamlet get(String id) {
        AssetStore<String, Hamlet, DefaultAssetMap<String, Hamlet>> store = getAssetStore();
        return store == null || id == null ? null : store.getAssetMap().getAsset(id);
    }

    /** Genres de lieux-dits du peuple, triés par id. */
    public static List<Hamlet> of(People people) {
        List<Hamlet> out = new ArrayList<>();
        AssetStore<String, Hamlet, DefaultAssetMap<String, Hamlet>> store = getAssetStore();
        if (store == null) {
            return out;
        }
        for (Hamlet h : store.getAssetMap().getAssetMap().values()) {
            if (people.id().equals(h.people)) {
                out.add(h);
            }
        }
        out.sort(java.util.Comparator.comparing(Hamlet::getId));
        return out;
    }

    /** Un genre du peuple tiré selon les poids, ou null s'il n'en a aucun. */
    public static Hamlet pick(People people, Random random) {
        List<Hamlet> all = of(people);
        int total = 0;
        for (Hamlet h : all) {
            total += h.weight;
        }
        if (total <= 0) {
            return null;
        }
        int r = random.nextInt(total);
        for (Hamlet h : all) {
            r -= h.weight;
            if (r < 0) {
                return h;
            }
        }
        return all.get(all.size() - 1);
    }

    @Override
    public String getId() {
        return id;
    }

    public People people() {
        People p = People.byId(people);
        return p == null ? People.KWEEBEC : p;
    }

    public String type() {
        return type;
    }

    public String nameKey() {
        return nameKey;
    }

    public String icon() {
        return icon;
    }

    public int weight() {
        return weight;
    }

    public String rule() {
        return rule;
    }

    public String[] decor() {
        return decor;
    }

    public String[] residents() {
        return residents;
    }

    public String dialogue() {
        return dialogue;
    }

    public String shop() {
        return shop;
    }

    public String shopBusy() {
        return shopBusy;
    }

    public synchronized List<Building> buildings() {
        if (buildings == null) {
            List<Building> out = new ArrayList<>();
            for (String line : buildingLines) {
                Building b = Building.parse(line);
                if (b != null) {
                    out.add(b);
                }
            }
            buildings = out;
        }
        return buildings;
    }

    /**
     * Tirage des bâtiments : le principal toujours, puis un tirage par côté (chaque choix a sa chance, au plus un par
     * côté). Rend les indices des bâtiments retenus, sous forme de masque (bit i : bâtiment i).
     */
    public int roll(Random random) {
        List<Building> all = buildings();
        Map<String, List<Integer>> sides = new LinkedHashMap<>();
        int mask = 0;
        for (int i = 0; i < all.size(); i++) {
            if ("M".equals(all.get(i).side())) {
                mask |= 1 << i;
            } else {
                sides.computeIfAbsent(all.get(i).side(), k -> new ArrayList<>()).add(i);
            }
        }
        for (List<Integer> options : sides.values()) {
            double r = random.nextDouble();
            for (int i : options) {
                r -= all.get(i).chance();
                if (r < 0) {
                    mask |= 1 << i;
                    break;
                }
            }
        }
        return mask;
    }

    /** Bâtiments retenus par le masque. */
    public List<Building> chosen(int mask) {
        List<Building> out = new ArrayList<>();
        List<Building> all = buildings();
        for (int i = 0; i < all.size(); i++) {
            if ((mask & (1 << i)) != 0) {
                out.add(all.get(i));
            }
        }
        return out;
    }

    /** Emprise locale {@code [x0, x1, z0, z1]} des bâtiments retenus, place comprise (l'origine). */
    public int[] rect(int mask) {
        int x0 = -3, x1 = 3, z0 = -1, z1 = 3;
        for (Building b : chosen(mask)) {
            x0 = Math.min(x0, b.x0());
            x1 = Math.max(x1, b.x1());
            z0 = Math.min(z0, b.z0());
            z1 = Math.max(z1, b.z1());
        }
        return new int[] {x0, x1, z0, z1};
    }
}
