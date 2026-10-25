package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Restores;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;
import org.joml.Vector3i;

import java.util.List;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Cages de l'Archidevin ({@link CliffsideLayout#CAGES}) : le prisonnier est enfermé au centre d'une cage libre, porte
 * fermée ; il perd {@value #DRAIN_PART} de ses PV max par seconde. Ses alliés forcent la porte ({@value #PRIES}
 * utilisations, pas le prisonnier lui-même) ; au bout de {@value #MAX_SECONDS} s elle s'ouvre seule. Une porte ouverte
 * revient {@value #DOOR_BACK} s plus tard ({@link Restores}).
 */
final class Cages {

    static final String DOOR = "Nakasar_Fractal_Cage_Door";
    static final int PRIES = 5;
    static final float DRAIN_PART = 0.03f;
    static final float MAX_SECONDS = 15f;
    static final float DOOR_BACK = 30f;
    private static final String CAUSE = "Nakasar_Fractal_Corruption";

    private static final class Cell {
        final CliffsideLayout.Cage cage;
        UUID prisoner;
        Ref<EntityStore> ref;
        float time;
        float drain;
        int pries;

        Cell(CliffsideLayout.Cage cage) {
            this.cage = cage;
        }

        Vector3d center() {
            return new Vector3d(cage.x() + 0.5, CliffsideLayout.ARENA + 0.05, cage.z() + 0.5);
        }

        int doorX() {
            return cage.x() + cage.doorX();
        }

        int doorZ() {
            return cage.z() + cage.doorZ();
        }
    }

    private final Cell[] cells;

    Cages() {
        cells = new Cell[CliffsideLayout.CAGES.size()];
        for (int i = 0; i < cells.length; i++) {
            cells[i] = new Cell(CliffsideLayout.CAGES.get(i));
        }
    }

    /** Enferme le joueur dans une cage libre, porte fermée, au hasard. Faux s'il n'y en a pas (ou s'il y est déjà). */
    boolean imprison(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player) {
        ChunkStore chunks = world.getChunkStore();
        for (Cell cell : cells) {
            if (player.getUuid().equals(cell.prisoner)) {
                return false;
            }
        }
        int start = ThreadLocalRandom.current().nextInt(cells.length);
        for (int k = 0; k < cells.length; k++) {
            Cell cell = cells[(start + k) % cells.length];
            if (cell.prisoner != null || !DOOR.equals(WorldBlocks.name(chunks, cell.doorX(), CliffsideLayout.ARENA, cell.doorZ()))) {
                continue;
            }
            cell.prisoner = player.getUuid();
            cell.ref = ref;
            cell.time = 0f;
            cell.drain = 0f;
            cell.pries = 0;
            TransformComponent transform = store.getComponent(ref, TransformComponent.getComponentType());
            Rotation3f rotation = transform != null ? transform.getRotation() : new Rotation3f();
            store.putComponent(ref, Teleport.getComponentType(), Teleport.createForPlayer(cell.center(), rotation));
            Telegraphs.particle(store, "Nakasar_Fractal_Corruption_Pulse", cell.center(), 1f);
            return true;
        }
        return false;
    }

    void step(World world, Store<EntityStore> store, List<PlayerRef> players, float dt) {
        for (Cell cell : cells) {
            if (cell.prisoner == null) {
                continue;
            }
            Vector3d at = Telegraphs.position(store, cell.ref);
            cell.time += dt;
            boolean inside = at != null && Telegraphs.horizontal(at, cell.center()) <= 1.3
                    && Math.abs(at.y() - cell.center().y()) <= 2;
            if (!inside) {
                // Mort ou parti : la cage se libère (la première seconde laisse au téléport le temps d'arriver).
                if (at == null || cell.time > 1f) {
                    cell.prisoner = null;
                    cell.ref = null;
                }
                continue;
            }
            cell.drain += dt;
            if (cell.drain >= 1f) {
                cell.drain -= 1f;
                Hurt.percent(store, cell.ref, DRAIN_PART, CAUSE);
            }
            if (cell.time >= MAX_SECONDS) {
                open(world, store, cell);
            }
        }
    }

    /** Un joueur force la porte du bloc (x, y, z). */
    void pry(World world, Store<EntityStore> store, Cliffside.State st, PlayerRef player, int x, int y, int z) {
        for (Cell cell : cells) {
            if (cell.doorX() != x || cell.doorZ() != z || y < CliffsideLayout.ARENA || y > CliffsideLayout.ARENA + 1) {
                continue;
            }
            if (cell.prisoner == null || player.getUuid().equals(cell.prisoner)) {
                Cliffside.tell(st, player, cell.prisoner == null ? "cage.empty" : "cage.self");
                return;
            }
            cell.pries++;
            Telegraphs.sound(store, "SFX_T1_Impact_Blunt", new Vector3d(x + 0.5, y + 0.5, z + 0.5));
            if (cell.pries < PRIES) {
                player.sendMessage(Message.translation(Cliffside.MESSAGES + "cage.pried").param("left", PRIES - cell.pries));
                return;
            }
            open(world, store, cell);
            return;
        }
    }

    private void open(World world, Store<EntityStore> store, Cell cell) {
        ChunkStore chunks = world.getChunkStore();
        List<Vector3i> door = List.of(new Vector3i(cell.doorX(), CliffsideLayout.ARENA, cell.doorZ()),
                new Vector3i(cell.doorX(), CliffsideLayout.ARENA + 1, cell.doorZ()));
        for (Vector3i c : door) {
            WorldBlocks.clear(chunks, c.x, c.y, c.z);
        }
        // Barreaux vanilla (VariantRotation Wall) : porte sur un côté est/ouest = rotation 1, comme dans le préfab.
        Restores.add(world, door, DOOR, cell.cage.doorX() != 0 ? 1 : 0, DOOR_BACK);
        Telegraphs.sound(store, "SFX_Lever_Metal_Off", cell.center());
        for (PlayerRef p : world.getPlayerRefs()) {
            if (p.getUuid().equals(cell.prisoner)) {
                p.sendMessage(Message.translation(Cliffside.MESSAGES + "cage.open"));
            }
        }
        // Porte ouverte : le prisonnier est libre, la cage ne resservira qu'une fois la porte revenue.
        cell.prisoner = null;
        cell.ref = null;
        cell.pries = 0;
    }

    /** Libère toutes les cages (boss vaincu ou remis à zéro). */
    void releaseAll(World world, Store<EntityStore> store) {
        for (Cell cell : cells) {
            if (cell.prisoner != null) {
                open(world, store, cell);
            }
        }
    }
}
