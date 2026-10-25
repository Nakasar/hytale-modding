package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * La Lumière de Deldrimor (la touche d'action spéciale de GW2), donnée à chacun quand les deux orbes sont au cristal :
 * clic droit, un éclat de {@value #RADIUS} blocs autour du joueur, recharge {@value #COOLDOWN} s. Il dévoile le
 * Minotaure ({@link Minotaur}), le chemin du gouffre et ses orbes ({@link AbyssPit}), refait les dalles de l'arène et
 * donne un Courant ascendant ({@link Voice}), et révèle les dix trésors cachés des nains (objets vanilla au sol ; un
 * scintillement discret les trahit à qui passe près).
 */
final class DeepLight {

    static final float COOLDOWN = 5f;
    static final double RADIUS = 6;
    static final double SPARKLE_RANGE = 16;
    /** Butin d'un trésor caché : deux objets vanilla au hasard. */
    static final String[] TREASURE = {"Ingredient_Bar_Mithril", "Ingredient_Bar_Gold", "Ingredient_Bar_Silver",
            "Rock_Gem_Sapphire", "Rock_Gem_Diamond", "Ingredient_Crystal_Cyan", "Ingredient_Crystal_White"};

    private final Map<UUID, Long> ready = new HashMap<>();
    private final boolean[] found = new boolean[DeepstoneLayout.TREASURES.length];
    private float sparkle;

    void step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        sparkle += dt;
        if (sparkle < 2.5f) {
            return;
        }
        sparkle = 0f;
        for (int i = 0; i < found.length; i++) {
            Vector3d at = Spawns.point(DeepstoneLayout.TREASURES[i]);
            if (!found[i] && !Deepstone.near(store, players, at, SPARKLE_RANGE).isEmpty()) {
                Telegraphs.particle(store, "Nakasar_Fractal_Treasure_Sparkle", new Vector3d(at).add(0, 0.6, 0), 0.6f);
            }
        }
    }

    void use(World world, Store<EntityStore> store, Deepstone.State st, PlayerRef player) {
        if (Carried.count(store, player.getReference(), Deepstone.LIGHT) == 0) {
            return;
        }
        long now = System.nanoTime();
        Long next = ready.get(player.getUuid());
        if (next != null && now < next) {
            Deepstone.tell(st, player, "light.cooldown");
            return;
        }
        Vector3d at = Telegraphs.position(store, player.getReference());
        if (at == null) {
            return;
        }
        Vector3d c = new Vector3d(at);
        ready.put(player.getUuid(), now + Telegraphs.seconds(COOLDOWN));
        Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Flash", c, (float) (RADIUS / 4));
        Telegraphs.sound(store, "SFX_Crystal_Break", c);
        for (int i = 0; i < found.length; i++) {
            Vector3d t = Spawns.point(DeepstoneLayout.TREASURES[i]);
            if (!found[i] && Telegraphs.horizontal(t, c) <= RADIUS && Math.abs(t.y() - c.y()) < 4) {
                found[i] = true;
                Telegraphs.particle(store, "Nakasar_Fractal_Treasure_Burst", t, 1f);
                for (int k = 0; k < 2; k++) {
                    Carried.drop(store, TREASURE[(int) (Math.random() * TREASURE.length)], t);
                }
                player.sendMessage(Message.translation(Deepstone.MESSAGES + "treasure.found"));
            }
        }
        st.minotaur.light(world, store, c);
        st.pit.light(world, store, st, c);
        st.voice.light(world, store, st, player, c);
    }
}
