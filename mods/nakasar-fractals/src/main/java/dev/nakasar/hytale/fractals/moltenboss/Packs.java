package dev.nakasar.hytale.fractals.moltenboss;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Les meutes du Boss en fusion ({@link MoltenBossLayout#PACKS}) : chacune paraît quand un joueur approche à
 * {@value #WAKE_RANGE} blocs. Les quatre premières remplissent l'atelier ; la quatrième garde aussi un résonateur qui
 * rend le chaman de la flamme d'élite invulnérable. Elle vaincue (chaman compris), le pont du canal de lave se pose.
 * Les groupes 5 à 8 (cour des wagonnets, passerelle des cuves) vaincus, le pont du creuset s'ouvre.
 */
final class Packs {

    static final double WAKE_RANGE = 34;
    /** Meutes de l'atelier (les suivantes sont les groupes de la passerelle). */
    static final int WORKSHOP_PACKS = 4;
    static final String DECK_BLOCK = "Rock_Basalt_Brick";
    static final String RAIL_BLOCK = "Deco_Iron_Bars";

    private final List<List<Ref<EntityStore>>> members = new ArrayList<>();
    private final boolean[] spawned = new boolean[MoltenBossLayout.PACKS.length];
    private final boolean[] cleared = new boolean[MoltenBossLayout.PACKS.length];
    private Ref<EntityStore> resonator;
    private Ref<EntityStore> shaman;
    private int beat;

    Packs() {
        for (int i = 0; i < MoltenBossLayout.PACKS.length; i++) {
            members.add(new ArrayList<>());
        }
    }

    boolean shamanShielded() {
        return resonator != null && resonator.isValid();
    }

    /** L'atelier : vrai quand la quatrième meute et son chaman sont tombés (le pont est posé). */
    boolean workshop(World world, Store<EntityStore> store, MoltenBoss.State st, List<PlayerRef> players) {
        wake(world, store, players, 0, WORKSHOP_PACKS);
        if (resonator != null && !Spawns.alive(store, resonator)) {
            resonator = null;
        }
        if (shaman != null && Spawns.alive(store, shaman)) {
            if (shamanShielded()) {
                MoltenBoss.link(store, resonator, shaman, ++beat % 4 == 0);
            }
        } else {
            shaman = null;
        }
        int last = WORKSHOP_PACKS - 1;
        if (!spawned[last] || !dead(store, last) || shaman != null || resonator != null) {
            return false;
        }
        var chunks = world.getChunkStore();
        for (int[] c : MoltenBossLayout.BRIDGE_DECK) {
            WorldBlocks.set(chunks, c[0], c[1], c[2], DECK_BLOCK, 0);
        }
        for (int[] c : MoltenBossLayout.BRIDGE_RAILS) {
            WorldBlocks.set(chunks, c[0], c[1], c[2], RAIL_BLOCK, 1);   // garde-corps le long de Z
        }
        int[] mid = MoltenBossLayout.BRIDGE_DECK[MoltenBossLayout.BRIDGE_DECK.length / 2];
        Telegraphs.particle(store, "Nakasar_Fractal_Molten_Upgrade", new Vector3d(mid[0] + 0.5, mid[1] + 1, mid[2] + 0.5), 1.5f);
        Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "bridge"));
        return true;
    }

    /** La cour et la passerelle : vrai quand les groupes 5 à 8 sont tous tombés. */
    boolean gauntlet(World world, Store<EntityStore> store, MoltenBoss.State st, List<PlayerRef> players) {
        int total = MoltenBossLayout.PACKS.length - WORKSHOP_PACKS;
        wake(world, store, players, WORKSHOP_PACKS, MoltenBossLayout.PACKS.length);
        int done = 0;
        for (int i = WORKSHOP_PACKS; i < MoltenBossLayout.PACKS.length; i++) {
            if (spawned[i] && dead(store, i)) {
                if (!cleared[i]) {
                    cleared[i] = true;
                    Spawns.tellAll(world, Message.translation(MoltenBoss.MESSAGES + "groups")
                            .param("count", count(WORKSHOP_PACKS)).param("total", total));
                }
                done++;
            }
        }
        return done == total;
    }

    private int count(int from) {
        int n = 0;
        for (int i = from; i < cleared.length; i++) {
            n += cleared[i] ? 1 : 0;
        }
        return n;
    }

    private void wake(World world, Store<EntityStore> store, List<PlayerRef> players, int from, int to) {
        for (int i = from; i < to; i++) {
            if (spawned[i]) {
                continue;
            }
            MoltenBossLayout.Pack pack = MoltenBossLayout.PACKS[i];
            Vector3d c = Spawns.point(pack.center());
            if (MoltenBoss.near(store, players, c, WAKE_RANGE).isEmpty()) {
                continue;
            }
            spawned[i] = true;
            Vector3d face = Spawns.point(MoltenBossLayout.SPAWN);
            for (int k = 0; k < pack.roles().length; k++) {
                Vector3d at = Spawns.point(pack.at()[k]);
                Ref<EntityStore> ref = Spawns.spawnFoe(world, store, pack.roles()[k], at, Telegraphs.yawToward(at, face));
                if (ref != null) {
                    members.get(i).add(ref);
                }
            }
            if (i == WORKSHOP_PACKS - 1) {
                resonator = Spawns.spawnFoe(world, store, MoltenBoss.RESONATOR, MoltenBossLayout.RESONATOR_1);
                shaman = Spawns.spawnFoe(world, store, MoltenBoss.ELITE_SHAMAN, MoltenBossLayout.ELITE_SHAMAN);
            }
        }
    }

    private boolean dead(Store<EntityStore> store, int pack) {
        for (Ref<EntityStore> ref : members.get(pack)) {
            if (Spawns.alive(store, ref)) {
                return false;
            }
        }
        return true;
    }
}
