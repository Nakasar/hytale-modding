package dev.nakasar.hytale.vampires.arena;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.event.events.ecs.BreakBlockEvent;
import com.hypixel.hytale.server.core.event.events.ecs.DamageBlockEvent;
import com.hypixel.hytale.server.core.event.events.ecs.UseBlockEvent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.telegraph.TelegraphSystem;
import dev.nakasar.hytale.vampires.telegraph.Telegraphs;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

/**
 * Décor des combats d'élites (Kevin, 20 octobre 2026), réglé sur les coups et les clics des joueurs :
 *
 * <ul>
 *   <li><b>Cellules du Capitaine</b> : la porte ({@value #CELL_DOOR}, deux blocs l'un sur l'autre) encaisse
 *   {@value #DOOR_HITS} coups puis tombe ; le reste de la cellule (murs, barreaux, sol, plafond autour d'un bloc
 *   {@value #CELL_MARKER}) est indestructible. Le levier ({@code Deco_Lever}) à côté ouvre la porte
 *   {@value #LEVER_OPEN} s (clic ou coup). Une porte tombée revient au bout de {@value #DOOR_RESTORE} s.</li>
 *   <li><b>Cloche d'alarme</b> ({@value #BELL}) : sonne à chaque coup, tombe au bout de {@value #BELL_HITS} coups ;
 *   détruite, le Capitaine ne peut plus appeler de renforts ({@code Nakasar_AlarmBell}). Revient au bout de
 *   {@value #BELL_RESTORE} s.</li>
 *   <li><b>Lanternes-citrouilles</b> ({@value #LANTERN}) : un coup les renverse ; le sol prend feu dans un rayon de
 *   {@value #FIRE_RADIUS} blocs pendant {@value #FIRE_SECONDS} s ({@value #FIRE_DPS} dégâts de feu par seconde, doublés
 *   sur les vrilles par {@code FireAffinitySystem}). Elles reviennent au bout de {@value #LANTERN_RESTORE} s.</li>
 *   <li><b>Braseros du Spectre</b> ({@link Braziers}) : un clic ou un coup les allume ; on ne peut pas les casser.</li>
 * </ul>
 */
public final class ArenaBlocks {

    public static final String CELL_DOOR = "Nakasar_Cell_Door";
    public static final String CELL_MARKER = "Nakasar_Prison_Cell";
    public static final String LEVER = "Deco_Lever";
    public static final String BELL = "Nakasar_Alarm_Bell";
    public static final String LANTERN = "Nakasar_Pumpkin_Lantern";
    static final int DOOR_HITS = 10;
    static final float LEVER_OPEN = 6f;
    static final float DOOR_RESTORE = 45f;
    static final int BELL_HITS = 5;
    static final float BELL_RESTORE = 180f;
    static final double FIRE_RADIUS = 3.0;
    static final float FIRE_SECONDS = 6f;
    static final float FIRE_DPS = 6f;
    static final float LANTERN_RESTORE = 90f;
    private static final float FIRE_TICK = 0.5f;
    private static final String FIRE_PARTICLE = "Nakasar_Ground_Fire";
    private static final String HIT_PARTICLE = "Impact_Sword_Basic_Stronk";
    private static final String DOOR_SOUND = "SFX_T1_Impact_Blunt";
    private static final String DOOR_BREAK_SOUND = "SFX_Mace_T2_Signature_Impact";
    private static final String BELL_SOUND = "SFX_Goblin_Mace_Club_Slam_Impact";
    private static final String FIRE_SOUND = "SFX_Goblin_Feastmaster_Slam";

    /** Coups reçus par porte ou cloche, par monde (clé du bloc du bas). */
    private static final Map<World, Map<Long, Integer>> HITS = Collections.synchronizedMap(new WeakHashMap<>());

    private ArenaBlocks() {
    }

    public static void clearAll() {
        HITS.clear();
    }

    /** Coup d'un joueur sur un bloc : vrai si le décor l'a pris en charge (le bloc ne s'abîme pas). */
    static boolean onHit(World world, Store<EntityStore> store, Vector3i at, String name) {
        ChunkStore chunks = world.getChunkStore();
        if (CELL_DOOR.equals(name)) {
            hitDoor(world, store, chunks, at);
            return true;
        }
        if (LEVER.equals(name)) {
            return pullLever(world, store, chunks, at);
        }
        if (BELL.equals(name)) {
            hitBell(world, store, chunks, at);
            return true;
        }
        if (LANTERN.equals(name)) {
            tipLantern(world, store, chunks, at);
            return true;
        }
        if (Braziers.isUnlit(name)) {
            Braziers.light(chunks, at);
            return true;
        }
        if (Braziers.LIT.contains(name)) {
            return true;
        }
        return inCell(chunks, at);
    }

    /** Clic d'un joueur sur un bloc : vrai si le décor l'a pris en charge (l'interaction vanilla est annulée). */
    static boolean onUse(World world, Store<EntityStore> store, Vector3i at, String name) {
        ChunkStore chunks = world.getChunkStore();
        if (LEVER.equals(name)) {
            return pullLever(world, store, chunks, at);
        }
        if (Braziers.isUnlit(name)) {
            Braziers.light(chunks, at);
            return true;
        }
        return CELL_DOOR.equals(name);
    }

    /** Vrai si le bloc fait partie d'une cellule (à 2 blocs d'un marqueur de cellule, du sol au plafond). */
    static boolean inCell(ChunkStore chunks, Vector3i at) {
        for (Vector3i cell : WorldBlocks.find(chunks, new Vector3d(at.x + 0.5, at.y + 0.5, at.z + 0.5), 4, List.of(CELL_MARKER))) {
            int dy = at.y - cell.y;
            if (Math.abs(at.x - cell.x) <= 2 && Math.abs(at.z - cell.z) <= 2 && dy >= -1 && dy <= 3) {
                return true;
            }
        }
        return false;
    }

    // --- porte de cellule et levier ----------------------------------------------------------

    /** Blocs de porte de la colonne de `at` (bas puis haut). */
    private static List<Vector3i> doorColumn(ChunkStore chunks, Vector3i at) {
        int bottom = at.y;
        while (CELL_DOOR.equals(WorldBlocks.name(chunks, at.x, bottom - 1, at.z)) && bottom > at.y - 3) {
            bottom--;
        }
        List<Vector3i> out = new ArrayList<>();
        for (int y = bottom; y < bottom + 3 && CELL_DOOR.equals(WorldBlocks.name(chunks, at.x, y, at.z)); y++) {
            out.add(new Vector3i(at.x, y, at.z));
        }
        return out;
    }

    private static void hitDoor(World world, Store<EntityStore> store, ChunkStore chunks, Vector3i at) {
        List<Vector3i> door = doorColumn(chunks, at);
        if (door.isEmpty()) {
            return;
        }
        Vector3i bottom = door.get(0);
        long key = WorldBlocks.key(bottom.x, bottom.y, bottom.z);
        Map<Long, Integer> hits = HITS.computeIfAbsent(world, w -> new HashMap<>());
        int count = hits.merge(key, 1, Integer::sum);
        Vector3d center = WorldBlocks.center(at);
        Telegraphs.particle(store, HIT_PARTICLE, center, 1f);
        if (count < DOOR_HITS) {
            Telegraphs.sound(store, DOOR_SOUND, center);
            return;
        }
        hits.remove(key);
        Telegraphs.sound(store, DOOR_BREAK_SOUND, center);
        open(world, chunks, door, DOOR_RESTORE);
    }

    /** Levier d'une cellule : ouvre la porte la plus proche ; faux (levier ordinaire, laissé au jeu) sans porte. */
    private static boolean pullLever(World world, Store<EntityStore> store, ChunkStore chunks, Vector3i lever) {
        Vector3d from = WorldBlocks.center(lever);
        Vector3i nearest = WorldBlocks.nearest(WorldBlocks.find(chunks, from, 3, List.of(CELL_DOOR)), from);
        if (nearest == null) {
            return false;
        }
        Telegraphs.sound(store, DOOR_SOUND, from);
        open(world, chunks, doorColumn(chunks, nearest), LEVER_OPEN);
        return true;
    }

    /** Retire la porte et la remet au bout de `seconds` secondes (si la place est restée vide). */
    private static void open(World world, ChunkStore chunks, List<Vector3i> door, float seconds) {
        int rotation = door.isEmpty() ? 0 : WorldBlocks.rotation(chunks, door.get(0).x, door.get(0).y, door.get(0).z);
        for (Vector3i block : door) {
            WorldBlocks.clear(chunks, block.x, block.y, block.z);
        }
        restoreLater(world, door, CELL_DOOR, rotation, seconds);
    }

    private static void restoreLater(World world, List<Vector3i> blocks, String name, int rotation, float seconds) {
        long[] at = {-1};
        TelegraphSystem.start(world, (w, s, now) -> {
            if (at[0] < 0) {
                at[0] = now + Telegraphs.seconds(seconds);
            }
            if (now < at[0]) {
                return false;
            }
            ChunkStore chunks = w.getChunkStore();
            for (Vector3i block : blocks) {
                if (WorldBlocks.id(chunks, block.x, block.y, block.z) == BlockType.EMPTY_ID) {
                    WorldBlocks.set(chunks, block.x, block.y, block.z, name, rotation);
                }
            }
            return true;
        });
    }

    // --- cloche d'alarme -----------------------------------------------------------------------

    private static void hitBell(World world, Store<EntityStore> store, ChunkStore chunks, Vector3i at) {
        long key = WorldBlocks.key(at.x, at.y, at.z);
        Map<Long, Integer> hits = HITS.computeIfAbsent(world, w -> new HashMap<>());
        int count = hits.merge(key, 1, Integer::sum);
        Vector3d center = WorldBlocks.center(at);
        Telegraphs.sound(store, BELL_SOUND, center);
        Telegraphs.particle(store, HIT_PARTICLE, center, 1f);
        if (count < BELL_HITS) {
            return;
        }
        hits.remove(key);
        int rotation = WorldBlocks.rotation(chunks, at.x, at.y, at.z);
        WorldBlocks.clear(chunks, at.x, at.y, at.z);
        Telegraphs.particle(store, "Stick_Slam_Ground_Large", center, 0.8f);
        restoreLater(world, List.of(at), BELL, rotation, BELL_RESTORE);
    }

    /** Cloche intacte la plus proche de `from` dans un rayon de `radius` blocs, ou null. */
    public static Vector3i bellNear(ChunkStore chunks, Vector3d from, int radius) {
        return WorldBlocks.nearest(WorldBlocks.find(chunks, from, radius, List.of(BELL)), from);
    }

    // --- lanternes-citrouilles -------------------------------------------------------------------

    private static void tipLantern(World world, Store<EntityStore> store, ChunkStore chunks, Vector3i at) {
        int rotation = WorldBlocks.rotation(chunks, at.x, at.y, at.z);
        WorldBlocks.clear(chunks, at.x, at.y, at.z);
        Vector3d center = new Vector3d(at.x + 0.5, at.y, at.z + 0.5);
        Telegraphs.sound(store, FIRE_SOUND, center);
        TelegraphSystem.start(world, new Fire(center));
        restoreLater(world, List.of(at), LANTERN, rotation, LANTERN_RESTORE);
    }

    /** Sol en feu autour d'une lanterne renversée : brûle tout ce qui s'y tient. */
    private static final class Fire implements TelegraphSystem.Task {
        private final Vector3d center;
        private long end = -1;
        private long next;

        Fire(Vector3d center) {
            this.center = center;
        }

        @Override
        public boolean step(World world, Store<EntityStore> store, long now) {
            if (end < 0) {
                end = now + Telegraphs.seconds(FIRE_SECONDS);
            }
            if (now >= end) {
                return true;
            }
            if (now < next) {
                return false;
            }
            next = now + Telegraphs.seconds(FIRE_TICK);
            Telegraphs.particle(store, FIRE_PARTICLE, new Vector3d(center).add(0, 0.05, 0), 1f);
            DamageCause fire = DamageCause.getAssetMap().getAsset("Fire");
            if (fire == null) {
                return false;
            }
            for (Ref<EntityStore> ref : inside(world, store)) {
                DamageSystems.executeDamage(ref, store, new Damage(new Damage.EnvironmentSource(LANTERN), fire, FIRE_DPS * FIRE_TICK));
            }
            return false;
        }

        private List<Ref<EntityStore>> inside(World world, Store<EntityStore> store) {
            List<Ref<EntityStore>> out = new ArrayList<>();
            for (PlayerRef player : world.getPlayerRefs()) {
                Vector3d at = Telegraphs.position(store, player.getReference());
                if (at != null && burns(at)) {
                    out.add(player.getReference());
                }
            }
            store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
                for (int i = 0; i < chunk.size(); i++) {
                    TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                    if (transform != null && burns(transform.getPosition())) {
                        out.add(chunk.getReferenceTo(i));
                    }
                }
            });
            return out;
        }

        private boolean burns(Vector3d at) {
            double dy = at.y() - center.y();
            return Telegraphs.horizontal(at, center) <= FIRE_RADIUS && dy >= -1.5 && dy <= 2.5;
        }
    }

    // --- systèmes ---------------------------------------------------------------------------------

    private static World world(Store<EntityStore> store) {
        return store.getExternalData().getWorld();
    }

    private static boolean isPlayer(ArchetypeChunk<EntityStore> chunk, int index) {
        return chunk.getComponent(index, Player.getComponentType()) != null;
    }

    /** Coup d'un joueur sur un bloc du décor : on garde la main (le bloc ne s'abîme pas). */
    public static final class Hit extends EntityEventSystem<EntityStore, DamageBlockEvent> {

        public Hit() {
            super(DamageBlockEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, DamageBlockEvent event) {
            BlockType type = event.getBlockType();
            Vector3i at = event.getTargetBlock();
            if (type == null || at == null || event.isCancelled() || !isPlayer(chunk, index) || !relevant(type.getId(), store, at)) {
                return;
            }
            event.setCancelled(true);
            Vector3i block = new Vector3i(at);
            String name = type.getId();
            World world = world(store);
            // Les blocs changent après le traitement en cours du store.
            world.execute(() -> onHit(world, world.getEntityStore().getStore(), block, name));
        }

        private static boolean relevant(String name, Store<EntityStore> store, Vector3i at) {
            return Set.of(CELL_DOOR, LEVER, BELL, LANTERN).contains(name) || Braziers.isUnlit(name)
                    || Braziers.LIT.contains(name) || inCell(world(store).getChunkStore(), at);
        }
    }

    /** Un bloc de cellule ne casse jamais (dernier filet si un coup est passé). */
    public static final class Break extends EntityEventSystem<EntityStore, BreakBlockEvent> {

        public Break() {
            super(BreakBlockEvent.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, BreakBlockEvent event) {
            BlockType type = event.getBlockType();
            Vector3i at = event.getTargetBlock();
            if (type == null || at == null || event.isCancelled() || !isPlayer(chunk, index)) {
                return;
            }
            String name = type.getId();
            if (Set.of(CELL_DOOR, LEVER, BELL).contains(name) || Braziers.LIT.contains(name) || Braziers.isUnlit(name)
                    || inCell(world(store).getChunkStore(), at)) {
                event.setCancelled(true);
            }
        }
    }

    /** Clic d'un joueur : levier, brasero éteint ; une porte de cellule ne s'ouvre pas à la main. */
    public static final class Use extends EntityEventSystem<EntityStore, UseBlockEvent.Pre> {

        public Use() {
            super(UseBlockEvent.Pre.class);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, UseBlockEvent.Pre event) {
            BlockType type = event.getBlockType();
            Vector3i at = event.getTargetBlock();
            if (type == null || at == null || event.isCancelled() || !isPlayer(chunk, index)) {
                return;
            }
            String name = type.getId();
            if (!LEVER.equals(name) && !CELL_DOOR.equals(name) && !Braziers.isUnlit(name)) {
                return;
            }
            event.setCancelled(true);
            Vector3i block = new Vector3i(at);
            World world = world(store);
            world.execute(() -> onUse(world, world.getEntityStore().getStore(), block, name));
        }
    }
}
