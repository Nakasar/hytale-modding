package dev.nakasar.hytale.peuples.village;

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

import java.util.HashSet;
import java.util.Set;

/**
 * Plan d'un village : des prefabs VANILLA placés autour du cœur (asset {@value #PATH}/&lt;id&gt;.json, généré par
 * {@code tools/generate_village_layouts.py}). Chaque bâtiment a un palier : le campement (palier 0) est collé à la
 * génération du village, les autres viendront avec les chantiers (étape 5 du plan).
 *
 * <pre>
 * { "People": "Kweebec", "Radius": 65, "PlazaRadius": 5, "BannerX": 0, "BannerZ": -4,
 *   "Buildings": [ {"Id": "Abri_Ouest", "Tier": 0, "Prefab": "Npc/Kweebec/Oak/Houses_Small/Kweebec_Oak_Houses_Small_001",
 *                   "X": -20, "Z": 2, "Rotation": 0, "MinX": -7, "MaxX": 7, "MinZ": -8, "MaxZ": 9} ] }
 * </pre>
 * Les coordonnées sont relatives au cœur ; {@code Prefab} est un chemin sous {@code Server/Prefabs/} sans
 * {@code .prefab.json} ; {@code Rotation} compte les quarts de tour ({@code PrefabRotation}) ; les bornes
 * {@code MinX..MaxZ} sont l'emprise au sol après rotation, relative au point de collage.
 */
public final class VillageLayout implements JsonAssetWithMap<String, DefaultAssetMap<String, VillageLayout>> {

    public static final String PATH = "Nakasar/VillageLayouts";

    /** Un bâtiment du plan. */
    public static final class Building {
        public static final BuilderCodec<Building> CODEC = BuilderCodec.builder(Building.class, Building::new)
                .append(new KeyedCodec<>("Id", Codec.STRING), (b, v) -> b.id = v, b -> b.id)
                .documentation("Identifiant du bâtiment dans le plan (sauvegardé avec le village une fois bâti).")
                .add()
                .append(new KeyedCodec<>("Tier", Codec.INTEGER), (b, v) -> b.tier = v == null ? 0 : v, b -> b.tier)
                .documentation("Palier du village à partir duquel le bâtiment existe (0 campement ... 3 bourg).")
                .add()
                .append(new KeyedCodec<>("Prefab", Codec.STRING), (b, v) -> b.prefab = v, b -> b.prefab)
                .documentation("Prefab vanilla, chemin sous Server/Prefabs/ sans .prefab.json.")
                .add()
                .append(new KeyedCodec<>("X", Codec.INTEGER), (b, v) -> b.x = v == null ? 0 : v, b -> b.x).add()
                .append(new KeyedCodec<>("Z", Codec.INTEGER), (b, v) -> b.z = v == null ? 0 : v, b -> b.z).add()
                .append(new KeyedCodec<>("Rotation", Codec.INTEGER), (b, v) -> b.rotation = v == null ? 0 : Math.floorMod(v, 4), b -> b.rotation)
                .documentation("Quarts de tour (PrefabRotation : 1 = 90°).")
                .add()
                .append(new KeyedCodec<>("MinX", Codec.INTEGER), (b, v) -> b.minX = v == null ? 0 : v, b -> b.minX).add()
                .append(new KeyedCodec<>("MaxX", Codec.INTEGER), (b, v) -> b.maxX = v == null ? 0 : v, b -> b.maxX).add()
                .append(new KeyedCodec<>("MinZ", Codec.INTEGER), (b, v) -> b.minZ = v == null ? 0 : v, b -> b.minZ).add()
                .append(new KeyedCodec<>("MaxZ", Codec.INTEGER), (b, v) -> b.maxZ = v == null ? 0 : v, b -> b.maxZ).add()
                .build();

        String id;
        int tier;
        String prefab;
        int x;
        int z;
        int rotation;
        int minX;
        int maxX;
        int minZ;
        int maxZ;

        public String id() {
            return id;
        }

        public int tier() {
            return tier;
        }

        public String prefab() {
            return prefab;
        }

        public int x() {
            return x;
        }

        public int z() {
            return z;
        }

        public int rotation() {
            return rotation;
        }

        /** Emprise au sol relative au cœur : {x0, x1, z0, z1}. */
        public int[] rect() {
            return new int[] {x + minX, x + maxX, z + minZ, z + maxZ};
        }
    }

    public static final AssetBuilderCodec<String, VillageLayout> CODEC = AssetBuilderCodec.builder(VillageLayout.class, VillageLayout::new,
                    Codec.STRING, (l, id) -> l.id = id, l -> l.id, (l, data) -> l.data = data, l -> l.data)
            .append(new KeyedCodec<>("People", Codec.STRING), (l, v) -> l.people = v, l -> l.people)
            .documentation("Peuple du village.")
            .add()
            .append(new KeyedCodec<>("Radius", Codec.INTEGER), (l, v) -> l.radius = v == null ? 0 : v, l -> l.radius)
            .documentation("Rayon du plan complet (tous paliers), en blocs depuis le cœur.")
            .add()
            .append(new KeyedCodec<>("PlazaRadius", Codec.INTEGER), (l, v) -> l.plazaRadius = v == null ? 5 : v, l -> l.plazaRadius)
            .documentation("Demi-côté de la place centrale aplanie autour du cœur.")
            .add()
            .append(new KeyedCodec<>("BannerX", Codec.INTEGER), (l, v) -> l.bannerX = v == null ? 0 : v, l -> l.bannerX).add()
            .append(new KeyedCodec<>("BannerZ", Codec.INTEGER), (l, v) -> l.bannerZ = v == null ? 0 : v, l -> l.bannerZ).add()
            .append(new KeyedCodec<>("Buildings", new ArrayCodec<>(Building.CODEC, Building[]::new)), (l, v) -> l.buildings = v, l -> l.buildings)
            .documentation("Bâtiments du plan.")
            .add()
            .validator(VillageLayout::validate)
            .build();

    private static AssetStore<String, VillageLayout, DefaultAssetMap<String, VillageLayout>> assetStore;

    protected AssetExtraInfo.Data data;
    protected String id;
    String people;
    int radius;
    int plazaRadius = 5;
    int bannerX;
    int bannerZ;
    Building[] buildings = new Building[0];

    VillageLayout() {
    }

    @SuppressWarnings("unchecked")
    public static AssetStore<String, VillageLayout, DefaultAssetMap<String, VillageLayout>> getAssetStore() {
        if (assetStore == null) {
            assetStore = (AssetStore<String, VillageLayout, DefaultAssetMap<String, VillageLayout>>) (AssetStore<?, ?, ?>) AssetRegistry.getAssetStore(VillageLayout.class);
        }
        return assetStore;
    }

    /** Plan d'id `id`, ou null. */
    public static VillageLayout get(String id) {
        AssetStore<String, VillageLayout, DefaultAssetMap<String, VillageLayout>> store = getAssetStore();
        return store == null || id == null ? null : store.getAssetMap().getAsset(id);
    }

    @Override
    public String getId() {
        return id;
    }

    public People people() {
        People p = People.byId(people);
        return p == null ? People.KWEEBEC : p;
    }

    public int radius() {
        return radius;
    }

    public int plazaRadius() {
        return plazaRadius;
    }

    public int bannerX() {
        return bannerX;
    }

    public int bannerZ() {
        return bannerZ;
    }

    public Building[] buildings() {
        return buildings;
    }

    /** Rayon des bâtiments des paliers 0 à `tier` (pour charger et juger le terrain). */
    public int radiusUpTo(int tier) {
        double r = plazaRadius;
        for (Building b : buildings) {
            if (b.tier <= tier) {
                int[] rect = b.rect();
                for (int px : new int[] {rect[0], rect[1]}) {
                    for (int pz : new int[] {rect[2], rect[3]}) {
                        r = Math.max(r, Math.hypot(px, pz));
                    }
                }
            }
        }
        return (int) Math.ceil(r);
    }

    private static void validate(VillageLayout layout, ValidationResults results) {
        if (People.byId(layout.people) == null) {
            results.fail("Peuple inconnu : " + layout.people);
        }
        Set<String> ids = new HashSet<>();
        for (Building b : layout.buildings) {
            if (b == null) {
                continue;
            }
            if (b.id == null || !ids.add(b.id)) {
                results.fail("Bâtiment sans id ou en double : " + b.id);
            }
            if (b.prefab == null || b.prefab.isBlank()) {
                results.fail("Bâtiment " + b.id + " sans prefab");
            }
            if (b.tier < 0 || b.tier > Tiers.MAX) {
                results.fail("Bâtiment " + b.id + " : palier hors de 0.." + Tiers.MAX);
            }
        }
    }
}
