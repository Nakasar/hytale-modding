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
                .append(new KeyedCodec<>("MinY", Codec.INTEGER), (b, v) -> b.minY = v == null ? 0 : v, b -> b.minY)
                .documentation("Plus bas bloc du prefab sous son ancre (fondations).")
                .add()
                .append(new KeyedCodec<>("MaxY", Codec.INTEGER), (b, v) -> b.maxY = v == null ? 8 : v, b -> b.maxY)
                .documentation("Plus haut bloc du prefab au-dessus de son ancre (échafaudage, incendie).")
                .add()
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
        int minY;
        int maxY = 8;

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

        /** Hauteur du prefab au-dessus de son ancre. */
        public int height() {
            return Math.max(1, maxY);
        }

        /** Plus bas bloc du prefab sous son ancre (négatif : fondations). */
        public int depth() {
            return minY;
        }

        /** Petit décor (lanterne, banc) ou potager : collé sans échafaudage. */
        public boolean small() {
            return maxY < 4 || prefab == null || prefab.contains("/Garden") || prefab.contains("/Lampposts/") || prefab.contains("/Seats/");
        }

        /** Emprise au sol relative au cœur : {x0, x1, z0, z1}. */
        public int[] rect() {
            return new int[] {x + minX, x + maxX, z + minZ, z + maxZ};
        }
    }

    /** Un matériau d'un chantier : objet vanilla et quantité, pris au dépôt. */
    public static final class Material {
        public static final BuilderCodec<Material> CODEC = BuilderCodec.builder(Material.class, Material::new)
                .append(new KeyedCodec<>("ItemId", Codec.STRING), (m, v) -> m.itemId = v, m -> m.itemId).add()
                .append(new KeyedCodec<>("Quantity", Codec.INTEGER), (m, v) -> m.quantity = v == null ? 1 : Math.max(1, v), m -> m.quantity).add()
                .build();

        String itemId;
        int quantity = 1;

        public String itemId() {
            return itemId;
        }

        public int quantity() {
            return quantity;
        }
    }

    /** Le chantier d'un palier (étape 5) : matériaux à réunir au dépôt, puis durée des travaux en heures de jeu. */
    public static final class Chantier {
        public static final BuilderCodec<Chantier> CODEC = BuilderCodec.builder(Chantier.class, Chantier::new)
                .append(new KeyedCodec<>("Tier", Codec.INTEGER), (c, v) -> c.tier = v == null ? 1 : v, c -> c.tier)
                .documentation("Palier que le chantier fait atteindre (1 hameau ... 3 bourg).")
                .add()
                .append(new KeyedCodec<>("Hours", Codec.INTEGER), (c, v) -> c.hours = v == null ? 24 : Math.max(0, v), c -> c.hours)
                .documentation("Durée des travaux, en heures de jeu (GDD : un jour de jeu).")
                .add()
                .append(new KeyedCodec<>("Materials", new ArrayCodec<>(Material.CODEC, Material[]::new)), (c, v) -> c.materials = v == null ? new Material[0] : v, c -> c.materials)
                .documentation("Objets pris au dépôt quand le chantier commence.")
                .add()
                .build();

        int tier = 1;
        int hours = 24;
        Material[] materials = new Material[0];

        public int tier() {
            return tier;
        }

        public int hours() {
            return hours;
        }

        public Material[] materials() {
            return materials;
        }
    }

    /** Un métier du village (étape 5) : un villageois du mod avec son poste de jour et son logis de nuit. */
    public static final class Job {
        public static final BuilderCodec<Job> CODEC = BuilderCodec.builder(Job.class, Job::new)
                .append(new KeyedCodec<>("Id", Codec.STRING), (j, v) -> j.id = v, j -> j.id).add()
                .append(new KeyedCodec<>("Tier", Codec.INTEGER), (j, v) -> j.tier = v == null ? 0 : v, j -> j.tier)
                .documentation("Palier du village à partir duquel le métier existe.")
                .add()
                .append(new KeyedCodec<>("Role", Codec.STRING), (j, v) -> j.role = v, j -> j.role)
                .documentation("Rôle PNJ du mod (Nakasar_Peuples_<Peuple>_<Métier>).")
                .add()
                .append(new KeyedCodec<>("Dialogue", Codec.STRING), (j, v) -> j.dialogue = v, j -> j.dialogue).add()
                .append(new KeyedCodec<>("Building", Codec.STRING), (j, v) -> j.building = v == null ? "" : v, j -> j.building)
                .documentation("Bâtiment de travail (vide : la place). Le métier attend que ce bâtiment soit debout.")
                .add()
                .append(new KeyedCodec<>("WorkX", Codec.INTEGER), (j, v) -> j.workX = v == null ? 0 : v, j -> j.workX).add()
                .append(new KeyedCodec<>("WorkZ", Codec.INTEGER), (j, v) -> j.workZ = v == null ? 0 : v, j -> j.workZ).add()
                .append(new KeyedCodec<>("Home", Codec.STRING), (j, v) -> j.home = v == null ? "" : v, j -> j.home).add()
                .append(new KeyedCodec<>("HomeX", Codec.INTEGER), (j, v) -> j.homeX = v == null ? 0 : v, j -> j.homeX).add()
                .append(new KeyedCodec<>("HomeZ", Codec.INTEGER), (j, v) -> j.homeZ = v == null ? 0 : v, j -> j.homeZ).add()
                .append(new KeyedCodec<>("Builder", Codec.BOOLEAN), (j, v) -> j.builder = v != null && v, j -> j.builder)
                .documentation("Vrai pour le bâtisseur : pendant un chantier, il y travaille au lieu de son poste.")
                .add()
                .build();

        String id;
        int tier;
        String role;
        String dialogue;
        String building = "";
        int workX;
        int workZ;
        String home = "";
        int homeX;
        int homeZ;
        boolean builder;

        public String id() {
            return id;
        }

        public int tier() {
            return tier;
        }

        public String role() {
            return role;
        }

        public String dialogue() {
            return dialogue;
        }

        public String building() {
            return building;
        }

        public int[] work() {
            return new int[] {workX, workZ};
        }

        public String home() {
            return home;
        }

        public int[] homeSpot() {
            return new int[] {homeX, homeZ};
        }

        public boolean builder() {
            return builder;
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
            .append(new KeyedCodec<>("Chantiers", new ArrayCodec<>(Chantier.CODEC, Chantier[]::new)), (l, v) -> l.chantiers = v == null ? new Chantier[0] : v, l -> l.chantiers)
            .documentation("Chantiers des paliers 1 à 3 (étape 5).")
            .add()
            .append(new KeyedCodec<>("Jobs", new ArrayCodec<>(Job.CODEC, Job[]::new)), (l, v) -> l.jobs = v == null ? new Job[0] : v, l -> l.jobs)
            .documentation("Métiers du village (étape 5).")
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
    Chantier[] chantiers = new Chantier[0];
    Job[] jobs = new Job[0];

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

    public Job[] jobs() {
        return jobs;
    }

    /** Bâtiment d'id `id`, ou null. */
    public Building building(String id) {
        for (Building b : buildings) {
            if (b.id.equals(id)) {
                return b;
            }
        }
        return null;
    }

    /** Chantier qui fait atteindre le palier `tier`, ou null. */
    public Chantier chantier(int tier) {
        for (Chantier c : chantiers) {
            if (c.tier == tier) {
                return c;
            }
        }
        return null;
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
        for (int tier = 1; tier <= Tiers.MAX; tier++) {
            boolean needed = false;
            for (Building b : layout.buildings) {
                needed |= b != null && b.tier == tier;
            }
            if (needed && layout.chantier(tier) == null) {
                results.fail("Pas de chantier pour le palier " + tier);
            }
        }
        Set<String> jobIds = new HashSet<>();
        for (Job j : layout.jobs) {
            if (j == null) {
                continue;
            }
            if (j.id == null || !jobIds.add(j.id)) {
                results.fail("Métier sans id ou en double : " + j.id);
            }
            if (j.role == null || j.role.isBlank() || j.dialogue == null || j.dialogue.isBlank()) {
                results.fail("Métier " + j.id + " sans rôle ou sans dialogue");
            }
            if (!j.building.isEmpty() && !ids.contains(j.building)) {
                results.fail("Métier " + j.id + " : bâtiment inconnu " + j.building);
            }
            if (!ids.contains(j.home)) {
                results.fail("Métier " + j.id + " : logis inconnu " + j.home);
            }
        }
    }
}
