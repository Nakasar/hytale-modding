package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.teleport.Teleport;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.TelegraphInteraction;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * {@code "Type": "Nakasar_Fractal_TrialDemo"} : pupitre du golem d'essai. Le golem rejoue sur le joueur les attaques
 * annoncées des fractales ({@link TelegraphInteraction#demo}), sans dégâts : un cercle sous ses pieds, un cône puis
 * une ligne vers lui (ils projettent), enfin un petit cercle qui l'envoie dans la cage d'essai, comme la cage de
 * l'Archidevin. La cage s'ouvre {@value #CAGE_SECONDS} secondes plus tard (le joueur revient près du pupitre).
 */
public class TrialDemoInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_TrialDemo";

    public static final BuilderCodec<TrialDemoInteraction> CODEC = BuilderCodec
            .builder(TrialDemoInteraction.class, TrialDemoInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Pupitre du golem d'essai : demonstration des attaques annoncees.")
            .build();

    /** Début de chaque annonce (s) ; chacune se remplit en {@value #CHARGE} s. */
    private static final float[] STARTS = {0f, 2.5f, 5f, 7.5f};
    private static final float CHARGE = 1.6f;
    private static final float CAGE_SECONDS = 5f;
    /** Durée de la démonstration complète, cage comprise (s). */
    private static final float LENGTH = 7.5f + CHARGE + CAGE_SECONDS;
    /** Fin de la démonstration en cours, par monde (nanosecondes). */
    private static final Map<World, Long> BUSY = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        if (!FractalCatalog.isObservatory(world)) {
            return;
        }
        long now = System.nanoTime();
        Long busy = BUSY.get(world);
        if (busy != null && now < busy) {
            playerRef.sendMessage(Message.translation("nakasar_fractals.trial.busy"));
            return;
        }
        world.execute(() -> start(world, player, playerRef, now));
    }

    private static void start(World world, Ref<EntityStore> player, PlayerRef playerRef, long now) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Ref<EntityStore> golem = TrialGolemSystem.find(store);
        Vector3d golemAt = Telegraphs.position(store, golem);
        Vector3d playerAt = Telegraphs.position(store, player);
        if (golemAt == null || playerAt == null) {
            playerRef.sendMessage(Message.translation("nakasar_fractals.trial.noGolem"));
            return;
        }
        BUSY.put(world, now + Telegraphs.seconds(LENGTH));
        playerRef.sendMessage(Message.translation("nakasar_fractals.trial.demo"));
        double facing = Telegraphs.angle(golemAt, playerAt);
        double reach = Telegraphs.horizontal(golemAt, playerAt) + 3;
        TelegraphInteraction.demo(world, golem, player, new Vector3d(playerAt), facing, "Circle", 3f, CHARGE, STARTS[0], 6f, false);
        TelegraphInteraction.demo(world, golem, player, new Vector3d(golemAt), facing, "Cone", (float) reach, CHARGE, STARTS[1], 6f, false);
        TelegraphInteraction.demo(world, golem, player, new Vector3d(golemAt), facing, "Line", (float) reach, CHARGE, STARTS[2], 6f, false);
        TelegraphSystem.start(world, new CagedPlayer(player, golem, now + Telegraphs.seconds(STARTS[3])));
    }

    /**
     * La cage : le petit cercle est posé sous le joueur où qu'il soit au moment voulu (il doit en sortir), puis le
     * joueur encore en cage est ramené près du pupitre.
     */
    private static final class CagedPlayer implements TelegraphSystem.Task {
        private final Ref<EntityStore> player;
        private final Ref<EntityStore> golem;
        private final long markAt;
        private long releaseAt = -1;

        CagedPlayer(Ref<EntityStore> player, Ref<EntityStore> golem, long markAt) {
            this.player = player;
            this.golem = golem;
            this.markAt = markAt;
        }

        @Override
        public boolean step(World world, Store<EntityStore> store, long now) {
            Vector3d at = Telegraphs.position(store, player);
            if (at == null || Telegraphs.position(store, golem) == null) {
                return true;
            }
            if (releaseAt < 0) {
                if (now < markAt) {
                    return false;
                }
                TelegraphInteraction.demo(world, golem, player, new Vector3d(at), 0, "Circle", 2f, CHARGE, 0f, 0f, true);
                releaseAt = now + Telegraphs.seconds(CHARGE + CAGE_SECONDS);
                return false;
            }
            if (now < releaseAt) {
                return false;
            }
            int[] cage = ObservatoryLayout.TRIAL_CAGE;
            if (Math.abs(at.x() - (cage[0] + 0.5)) < 1.5 && Math.abs(at.z() - (cage[2] + 0.5)) < 1.5) {
                double[] back = ObservatoryLayout.TRIAL_RELEASE;
                store.putComponent(player, Teleport.getComponentType(),
                        Teleport.createForPlayer(new Vector3d(back[0], back[1], back[2]), new Rotation3f()));
            }
            return true;
        }
    }
}
