package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.prefab.PrefabRotation;
import com.hypixel.hytale.server.core.prefab.PrefabStore;
import com.hypixel.hytale.server.core.prefab.selection.buffer.PrefabBufferUtil;
import com.hypixel.hytale.server.core.prefab.selection.buffer.impl.IPrefabBuffer;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.PrefabUtil;
import org.joml.Vector3i;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.function.Consumer;

/**
 * Bâtit un village à partir de son plan ({@link VillageLayout}) : charge les chunks, aplanit la place et l'emprise de
 * chaque bâtiment du palier atteint, colle les prefabs VANILLA (avec leurs marqueurs d'apparition de Kweebecs), puis
 * pose le cœur du peuple ({@link VillageHeart}), le dépôt, le tableau ({@link Villages#found}) et la bannière de
 * carte aux places que le plan leur donne.
 *
 * <p>Les prefabs se collent par {@link PrefabUtil#paste} comme l'action vanilla {@code PrefabPasteAction} des
 * évènements de monde ; le chemin se résout dans tous les packs ({@link PrefabStore#findAssetPrefabPath}).
 */
public final class VillageBuilder {

    private static final HytaleLogger LOGGER = HytaleLogger.forEnclosingClass();
    private static final String MESSAGES = Villages.MESSAGES;

    /** Écart de hauteur maximal entre un bâtiment et la place (le village reste d'un seul tenant). */
    private static final int MAX_STEP = 4;
    /** Marge plate et fondu autour d'une emprise. */
    private static final int MARGIN = 2;
    private static final int BLEND = 4;

    private VillageBuilder() {
    }

    /** Résultat d'une génération : le village, ou le message d'échec. */
    public record Result(Village village, Message error) {
        static Result fail(String key) {
            return new Result(null, Message.translation(MESSAGES + key));
        }
    }

    /**
     * Génère un village du plan `layout` centré en (cx, cz) au palier 0, puis appelle `done` sur le thread du monde. À
     * appeler depuis le thread du monde. `auto` : village posé par {@link VillageSeeder} (et non par une commande).
     */
    public static void generate(World world, VillageLayout layout, String name, int cx, int cz, boolean auto, Consumer<Result> done) {
        Village near = tooClose(world, layout, cx, cz);
        if (near != null) {
            done.accept(new Result(null, Message.translation(MESSAGES + "tooClose").param("name", near.name())
                    .param("distance", (int) Math.sqrt(near.distanceSquared(cx, near.y(), cz))).param("min", spacing(layout))));
            return;
        }
        int r = layout.radiusUpTo(0) + MARGIN + 2 * BLEND + 18; // talus et couronnes des arbres retirés
        Terrain.load(world, cx - r, cx + r, cz - r, cz + r).whenComplete((ignored, error) -> world.execute(() -> {
            if (error != null) {
                LOGGER.atWarning().withCause(error).log("Nakasar Peuples : chunks du village %s non chargés", name);
                done.accept(Result.fail("loadFailed"));
                return;
            }
            done.accept(buildNow(world, layout, name, cx, cz, auto));
        }));
    }

    /** Distance minimale entre deux cœurs pour qu'un plan entier (tous paliers) tienne sans chevaucher l'autre. */
    public static int spacing(VillageLayout layout) {
        return Math.max(Villages.MIN_SPACING, 2 * layout.radius() + 16);
    }

    /** Village trop proche de (cx, cz) pour y générer ce plan, ou null. */
    public static Village tooClose(World world, VillageLayout layout, int cx, int cz) {
        int min = spacing(layout);
        for (Village other : Villages.registry(world).all()) {
            double dx = other.x() - cx;
            double dz = other.z() - cz;
            if (dx * dx + dz * dz < (double) min * min) {
                return other;
            }
        }
        return null;
    }

    private static Result buildNow(World world, VillageLayout layout, String name, int cx, int cz, boolean auto) {
        if (tooClose(world, layout, cx, cz) != null) {
            return Result.fail("siteTaken");
        }
        Terrain terrain = new Terrain(world);
        int p = layout.plazaRadius();
        int h0 = terrain.medianSurface(cx - p, cx + p, cz - p, cz + p, 1);
        if (h0 == Terrain.NONE) {
            return Result.fail("terrainUnloaded");
        }

        // Emprises du palier 0 et hauteurs prises sur le relief naturel, avant toute retouche.
        List<VillageLayout.Building> buildings = new ArrayList<>();
        List<int[]> rects = new ArrayList<>();
        List<Integer> heights = new ArrayList<>();
        for (VillageLayout.Building b : layout.buildings()) {
            if (b.tier() > 0) {
                continue;
            }
            int[] r = b.rect();
            int[] rect = {cx + r[0], cx + r[1], cz + r[2], cz + r[3]};
            int h = terrain.medianSurface(rect[0], rect[1], rect[2], rect[3], 2);
            h = h == Terrain.NONE ? h0 : Math.max(h0 - MAX_STEP, Math.min(h0 + MAX_STEP, h));
            buildings.add(b);
            rects.add(rect);
            heights.add(h);
        }
        int[] plaza = {cx - p, cx + p, cz - p, cz + p};
        // Un seul terrassement pour la place et toutes les emprises : talus doux entre elles, arbres retirés en entier.
        Grading grading = new Grading(world).pad(plaza[0], plaza[1], plaza[2], plaza[3], h0, 1, layout.people().plaza());
        for (int i = 0; i < buildings.size(); i++) {
            int[] rect = rects.get(i);
            grading.pad(rect[0], rect[1], rect[2], rect[3], heights.get(i), MARGIN, layout.people().ground());
        }
        grading.apply(BLEND, layout.people().ground(), null);

        Store<EntityStore> store = world.getEntityStore().getStore();
        List<String> built = new ArrayList<>();
        List<Integer> builtHeights = new ArrayList<>();
        for (int i = 0; i < buildings.size(); i++) {
            VillageLayout.Building b = buildings.get(i);
            if (paste(world, store, b.prefab(), cx + b.x(), heights.get(i), cz + b.z(), b.rotation())) {
                built.add(b.id());
                builtHeights.add(heights.get(i));
            }
        }

        // Cœur du peuple (palier 0) : pièces vanilla et blocs de la place, puis dépôt, tableau et bannière à leurs places.
        VillageLayout.Heart heart = layout.heart();
        Villages.Founding founding;
        if (heart != null) {
            VillageHeart.apply(world, layout, null, cx, h0, cz, -1, 0, true);
            founding = Villages.found(world, name, layout.people(), cx, h0 + 1, cz,
                    VillageHeart.at(heart.deposit(), cx, h0, cz), VillageHeart.at(heart.board(), cx, h0, cz));
        } else {
            founding = Villages.found(world, name, layout.people(), cx, h0 + 1, cz);
        }
        if (founding.village() == null) {
            return new Result(null, founding.error());
        }
        Village village = founding.village();
        village.markGenerated(layout.getId(), auto, built.toArray(String[]::new));
        for (int i = 0; i < built.size(); i++) {
            village.setSiteY(built.get(i), builtHeights.get(i));
        }
        int[] banner = heart == null ? null : VillageHeart.at(heart.banner(), cx, h0, cz);
        if (banner != null) {
            village.setHeartTier(0);
            Villages.placeBanner(world, village, banner[0], banner[1], banner[2], banner[3]);
        } else {
            Villages.placeBanner(world, village, cx + layout.bannerX(), h0 + 1, cz + layout.bannerZ());
        }
        LOGGER.atInfo().log("Nakasar Peuples : village %s (%s, plan %s) généré en %d %d %d, %d/%d bâtiments collés%s",
                name, layout.people().id(), layout.getId(), cx, h0 + 1, cz, built.size(), buildings.size(), auto ? " (automatique)" : "");
        return new Result(village, null);
    }

    /**
     * Boîte {@code [x0, x1, y0, y1, z0, z1]} que couvrirait le prefab `prefab` collé en (x, y, z), un peu élargie
     * (l'ancre peut ne pas être comptée dans les bornes du buffer), ou null s'il est introuvable.
     */
    public static int[] bounds(String prefab, int x, int y, int z, int rotation) {
        IPrefabBuffer buffer = buffer(prefab);
        if (buffer == null) {
            return null;
        }
        PrefabRotation rot = PrefabRotation.VALUES[Math.floorMod(rotation, 4)];
        int ax = buffer.getAnchorX();
        int ay = buffer.getAnchorY();
        int az = buffer.getAnchorZ();
        int reach = Math.max(Math.abs(ax), Math.abs(az));
        return new int[]{
                x + buffer.getMinX(rot) - reach - 1, x + buffer.getMaxX(rot) + reach + 1,
                y + Math.min(buffer.getMinY(), buffer.getMinY() - ay) - 1, y + Math.max(buffer.getMaxY(), buffer.getMaxY() - ay) + 1,
                z + buffer.getMinZ(rot) - reach - 1, z + buffer.getMaxZ(rot) + reach + 1};
    }

    private static IPrefabBuffer buffer(String prefab) {
        Path path = PrefabStore.get().findAssetPrefabPath(prefab + ".prefab.json");
        if (path == null) {
            path = PrefabStore.get().findAssetPrefabPath(prefab);
        }
        return path == null ? null : PrefabBufferUtil.getCached(path);
    }

    /**
     * Colle le prefab vanilla `prefab` (chemin sous Server/Prefabs/ sans extension), son ancre (niveau du sol du
     * prefab) en (x, y, z). Faux si le prefab est introuvable ou que la zone n'est pas chargée.
     */
    public static boolean paste(World world, Store<EntityStore> store, String prefab, int x, int y, int z, int rotation) {
        Path path = PrefabStore.get().findAssetPrefabPath(prefab + ".prefab.json");
        if (path == null) {
            path = PrefabStore.get().findAssetPrefabPath(prefab);
        }
        if (path == null) {
            LOGGER.atWarning().log("Nakasar Peuples : prefab introuvable %s", prefab);
            return false;
        }
        IPrefabBuffer buffer = PrefabBufferUtil.getCached(path);
        if (buffer == null) {
            LOGGER.atWarning().log("Nakasar Peuples : prefab illisible %s", path);
            return false;
        }
        PrefabRotation rot = PrefabRotation.VALUES[Math.floorMod(rotation, 4)];
        Vector3i origin = new Vector3i(x, y, z);
        PrefabUtil.PasteRegion region = PrefabUtil.loadPasteRegionIfInMemory(buffer, world, origin, rot);
        if (region == null || !region.isFullyLoaded()) {
            LOGGER.atWarning().log("Nakasar Peuples : zone du prefab %s en %d %d %d pas chargée", prefab, x, y, z);
            return false;
        }
        PrefabUtil.paste(buffer, world, origin, rot.getRotation(), ThreadLocalRandom.current(), 1, 0, region,
                PrefabUtil.NOOP_BLOCK_ENTITY_CONSUMER, PrefabUtil.NOOP_ENTITY_CONSUMER, store);
        return true;
    }
}
