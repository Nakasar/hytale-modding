package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.chunk.section.FluidSection;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.VillageBuilder;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * La Source de l'Écho, l'oasis que fait naître la Graine d'Écho dans les Dunes (fin de la chaîne kweebec). Kevin
 * (2026-11-15) : l'ancien bassin kweebec vanilla collé tel quel faisait une dalle d'herbe posée sur le sable, avec deux
 * pousses kweebec, et rien ne disait à quoi il servait.
 *
 * <p>Construction : le site ({@value #HALF} blocs autour du centre) est aplani en sable à sa hauteur médiane, avec des
 * talus d'un bloc ({@link Terrain#flatten}) ; le prefab du mod {@value #PREFAB} (tools/generate_echo_spring.py : bassin
 * creusé, margelle, roseaux, herbes arides, dallage, colonne à torche feran, Jarre de la Source) est collé ancre à la
 * surface ; sable et gravier prennent la variante locale (rouge, blanc) ; enfin les palmiers et le rocher d'oasis
 * vanilla ({@link #PIECES}). Le centre est inscrit comme abri ({@link ZoneRegistry#addShelter}) : pas de soif à moins
 * de {@value Climate#SHELTER_RADIUS} blocs.
 */
public final class EchoSpring {

    public static final String KEYS = "nakasar_peuples.spring.";
    public static final String PREFAB = "Nakasar/Peuples/Oasis/Echo_Spring";
    /** Demi-côté du site aplani (generate_echo_spring.py, HALF). */
    static final int HALF = 6;
    /** Distance du centre de la source au joueur qui plante la graine (le site ne doit pas l'enterrer). */
    static final int OFFSET = 10;
    /** Écart de relief maximal sur le site, et distance minimale entre deux sources. */
    static final int MAX_RELIEF = 6;
    static final int MIN_SPACING = 24;
    /** Pièces vanilla (generate_echo_spring.py, PIECES) : prefab, x, y, z relatifs au centre et à la surface. */
    private static final Object[][] PIECES = {
            {"Orbis/Trees/Palm/Stage_3/Palm_Stage3_002", -4, 1, -3},
            {"Orbis/Trees/Palm/Stage_2/Palm_Stage2_001", 3, 1, -4},
            {"Orbis/Trees/Palm/Stage_3/Palm_Stage3_004", 4, 1, 2},
            {"Rock_Formations/Rocks/Sandstone/Oasis/Rock_Oasis_Small_01", -5, 1, 2},
    };
    /** Boîte de l'ancien bassin kweebec (Kweebec_Oak_Water_Pool_005, ancre au sol) autour du point inscrit. */
    private static final int OLD_REACH = 5;

    private EchoSpring() {
    }

    /** Centre de la source pour un joueur en `at` : {@value #OFFSET} blocs à l'est. */
    static int[] centreFor(Vector3d at) {
        return new int[] {(int) Math.floor(at.x()) + OFFSET, (int) Math.floor(at.z())};
    }

    /** Vrai si le site centré en (cx, cz) convient : chargé, relief doux, sans eau, loin d'une autre source. */
    static boolean siteOk(World world, int cx, int cz) {
        Terrain terrain = new Terrain(world);
        int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
        for (int x = cx - HALF; x <= cx + HALF; x += 2) {
            for (int z = cz - HALF; z <= cz + HALF; z += 2) {
                int y = terrain.surface(x, z);
                if (y == Terrain.NONE || terrain.hasFluid(x, y + 1, z)) {
                    return false;
                }
                lo = Math.min(lo, y);
                hi = Math.max(hi, y);
            }
        }
        if (hi - lo > MAX_RELIEF) {
            return false;
        }
        for (int[] s : ZoneRegistry.get(world).shelters()) {
            double dx = s[0] - cx, dz = s[2] - cz;
            if (dx * dx + dz * dz < MIN_SPACING * MIN_SPACING) {
                return false;
            }
        }
        return true;
    }

    /**
     * Construit la source centrée en (cx, cz) (thread du monde) et l'inscrit comme abri si `register`.
     *
     * @return la hauteur de la surface du site, ou {@link Terrain#NONE} si rien n'est chargé
     */
    static int build(World world, Store<EntityStore> store, int cx, int cz, boolean register) {
        Terrain terrain = new Terrain(world);
        int y0 = terrain.medianSurface(cx - HALF, cx + HALF, cz - HALF, cz + HALF, 2);
        if (y0 == Terrain.NONE) {
            return Terrain.NONE;
        }
        String sand = localSand(world, terrain, cx, cz);
        String gravel = "Soil_Gravel_" + sand.substring("Soil_".length());
        terrain.flatten(cx - HALF, cx + HALF, cz - HALF, cz + HALF, y0, 1, 3, sand, sand, (x, z) -> false);
        boolean pasted = VillageBuilder.paste(world, store, PREFAB, cx, y0, cz, 0);
        if (!"Soil_Sand".equals(sand)) {
            Map<String, String> swap = new HashMap<>();
            swap.put("Soil_Sand", sand);
            swap.put("Soil_Gravel_Sand", gravel);
            ChunkStore chunks = world.getChunkStore();
            for (int x = cx - HALF; x <= cx + HALF; x++) {
                for (int z = cz - HALF; z <= cz + HALF; z++) {
                    for (int y = y0 - 3; y <= y0; y++) {
                        String to = swap.get(Blocks.name(chunks, x, y, z));
                        if (to != null) {
                            Blocks.set(chunks, x, y, z, to, 0);
                        }
                    }
                }
            }
        }
        for (Object[] p : PIECES) {
            VillageBuilder.paste(world, store, (String) p[0], cx + (int) p[1], y0 + (int) p[2], cz + (int) p[3], 0);
        }
        if (register) {
            ZoneRegistry.get(world).addShelter(cx, y0, cz);
        }
        unstick(world, store, cx, cz);
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : Source de l'Écho en %d %d %d (sable %s, prefab %s)", cx, y0, cz,
                sand, pasted ? "collé" : "non collé");
        return y0;
    }

    /**
     * Reconstruit la source inscrite en `shelter` : retire d'abord l'ancien bassin kweebec (blocs au-dessus du sable,
     * eau), puis construit la nouvelle au même centre. Pour les mondes où la graine a été plantée avant le correctif.
     */
    static int rebuild(World world, Store<EntityStore> store, int[] shelter) {
        int cx = shelter[0], sy = shelter[1], cz = shelter[2];
        ChunkStore chunks = world.getChunkStore();
        for (int x = cx - OLD_REACH; x <= cx + OLD_REACH; x++) {
            for (int z = cz - OLD_REACH; z <= cz + OLD_REACH; z++) {
                for (int y = sy - 4; y <= sy + 6; y++) {
                    clearFluid(chunks, x, y, z);
                    String name = Blocks.name(chunks, x, y, z);
                    if (name != null && isOldPool(name)) {
                        // Au-dessus du sable d'origine : retiré ; dessous : du sable, pour que les rives du nouveau
                        // bassin ne montrent pas de terre.
                        Blocks.set(chunks, x, y, z, y >= sy ? "Empty" : "Soil_Sand", 0);
                    }
                }
            }
        }
        removeSprouts(store, cx, sy, cz);
        return build(world, store, cx, cz, false);
    }

    /** Les pousses kweebec nées des marqueurs de l'ancien bassin vanilla (rôle Kweebec_Sproutling*), à 24 blocs. */
    private static void removeSprouts(Store<EntityStore> store, int cx, int cy, int cz) {
        Vector3d at = new Vector3d(cx, cy, cz);
        List<Ref<EntityStore>> found = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                TransformComponent t = chunk.getComponent(i, TransformComponent.getComponentType());
                String role = npc == null ? null : npc.getRoleName();
                if (t != null && role != null && role.startsWith("Kweebec_Sproutling") && t.getPosition().distanceSquared(at) <= 24 * 24) {
                    found.add(chunk.getReferenceTo(i));
                }
            }
        });
        for (Ref<EntityStore> r : found) {
            if (r.isValid()) {
                store.removeEntity(r, RemoveReason.REMOVE);
            }
        }
    }

    /**
     * Reconstruit la source inscrite la plus proche de (x, z) à `radius` blocs (commande {@code /village source}).
     * `y[0]` reçoit la surface du site ({@link Terrain#NONE} si rien n'est chargé).
     *
     * @return l'abri reconstruit, ou null s'il n'y en a pas
     */
    public static int[] rebuildNearest(World world, Store<EntityStore> store, double x, double z, double radius, int[] y) {
        int[] s = nearest(world, x, z, radius);
        if (s != null) {
            y[0] = rebuild(world, store, s);
        }
        return s;
    }

    /** Blocs du bassin kweebec vanilla (Kweebec_Oak_Water_Pool_005). */
    private static boolean isOldPool(String name) {
        return name.equals("Soil_Dirt") || name.equals("Soil_Leaves") || name.startsWith("Soil_Pathway")
                || name.startsWith("Soil_Grass") || name.startsWith("Plant_Grass_Sharp");
    }

    private static void clearFluid(ChunkStore chunks, int x, int y, int z) {
        Ref<ChunkStore> ref = chunks.getChunkSectionReferenceAtBlock(x, y, z);
        if (ref == null || !ref.isValid()) {
            return;
        }
        FluidSection fluids = chunks.getStore().getComponent(ref, FluidSection.getComponentType());
        if (fluids != null && fluids.getFluidId(x, y, z) != 0) {
            fluids.setFluid(x, y, z, 0, (byte) 0);
        }
    }

    /** Sable le plus fréquent en surface autour du site (Soil_Sand, _Red ou _White ; Soil_Sand par défaut). */
    private static String localSand(World world, Terrain terrain, int cx, int cz) {
        Map<String, Integer> count = new HashMap<>();
        for (int x = cx - HALF - 4; x <= cx + HALF + 4; x += 2) {
            for (int z = cz - HALF - 4; z <= cz + HALF + 4; z += 2) {
                String b = terrain.surfaceBlock(x, z);
                if ("Soil_Sand".equals(b) || "Soil_Sand_Red".equals(b) || "Soil_Sand_White".equals(b)) {
                    count.merge(b, 1, Integer::sum);
                }
            }
        }
        return count.entrySet().stream().max(Map.Entry.comparingByValue()).map(Map.Entry::getKey).orElse("Soil_Sand");
    }

    /** Joueurs enterrés par le terrassement : remontés au point sûr le plus proche. */
    private static void unstick(World world, Store<EntityStore> store, int cx, int cz) {
        Terrain terrain = new Terrain(world);
        int reach = HALF + 10;
        for (PlayerRef p : world.getPlayerRefs()) {
            Ref<EntityStore> r = p.getReference();
            Vector3d at = r == null || !r.isValid() ? null : Requests.position(store, r);
            if (at == null || Math.abs(at.x() - cx) > reach || Math.abs(at.z() - cz) > reach) {
                continue;
            }
            int bx = (int) Math.floor(at.x()), by = (int) Math.floor(at.y()), bz = (int) Math.floor(at.z());
            if (terrain.bodyFree(bx, by, bz)) {
                continue;
            }
            int[] spot = terrain.safeSpot(bx, bz, 8);
            if (spot != null) {
                store.putComponent(r, Teleport.getComponentType(),
                        new Teleport(new Vector3d(spot[0] + 0.5, spot[1], spot[2] + 0.5), new Rotation3f(0f, 0f, 0f)));
            }
        }
    }

    /** L'abri inscrit le plus proche de (x, z) à `radius` blocs au plus, ou null. */
    static int[] nearest(World world, double x, double z, double radius) {
        int[] best = null;
        double bestD = radius * radius;
        for (int[] s : ZoneRegistry.get(world).shelters()) {
            double dx = s[0] - x, dz = s[2] - z;
            double d = dx * dx + dz * dz;
            if (d <= bestD) {
                bestD = d;
                best = s;
            }
        }
        return best;
    }
}
