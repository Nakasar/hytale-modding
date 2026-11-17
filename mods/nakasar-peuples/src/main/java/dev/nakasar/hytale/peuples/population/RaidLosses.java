package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import dev.nakasar.hytale.peuples.workshop.Workshop;
import dev.nakasar.hytale.peuples.workshop.Workshops;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Ce que coûte un raid perdu (décisions de Kevin, 16 novembre 2026, Claude Doc « Générations de villageois ») :
 * <ul>
 *   <li>un grand bâtiment debout est tiré au hasard, comme avant (parmi ceux du plus haut palier) ;</li>
 *   <li>un bâtiment à niveaux (bâtiment de métier, projet de terrain) au niveau II ou plus perd un niveau au lieu de
 *   brûler : personne ne meurt, le village garde son palier ;</li>
 *   <li>sinon il brûle (le village perd un palier, comme avant) : seul son responsable meurt (le titulaire du poste qui
 *   y travaille, sinon l'adulte le plus âgé du foyer), même s'il défendait ; les autres habitants vont au refuge
 *   désigné par l'Hôte, sinon au camp de réfugiés du bord du village (world/Camps).</li>
 * </ul>
 */
public final class RaidLosses {

    /** Ce que le raid a coûté : bâtiment touché, niveau perdu (sinon il a brûlé), mort du responsable. */
    public record Loss(VillageLayout.Building building, boolean levelLost, int levelNow, Inhabitant dead) {
    }

    private RaidLosses() {
    }

    /** Applique la perte du raid ; null si rien n'est debout (village sans plan). */
    public static Loss apply(World world, Store<EntityStore> store, Village village) {
        VillageLayout layout = Chantiers.layout(village);
        if (layout == null) {
            return null;
        }
        VillageLayout.Building target = pick(village, layout);
        if (target == null) {
            return null;
        }
        // Bâtiment à niveaux au-dessus du niveau I : il perd un niveau.
        Workshop w = workshopOf(village, target.id());
        WorkshopState ws = w == null ? null : village.workshop(w.getId());
        if (ws != null && ws.level() >= 2) {
            int level = ws.level() - 1;
            ws.clearUpgrade();
            ws.setLevel(level);
            ws.setKnowledge(0);
            ws.setMasterDone(false);
            Workshops.draw(store, village, w, ws, true);
            Message name = Message.translation(w.nameKey());
            Chantiers.announce(world, village, Message.translation(Population.KEYS + "raid.levelLost").param("village", village.name())
                            .param("building", name).param("level", Message.translation(Workshops.KEYS + "level." + level)),
                    null, NotificationStyle.Danger);
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples : raid perdu à %s, %s redescend au niveau %d", village.name(), w.getId(), level);
            return new Loss(target, true, level, null);
        }
        // Sinon il brûle : son responsable meurt, les autres partent au refuge ou au camp.
        Inhabitant dead = null;
        List<Inhabitant> homeless = new ArrayList<>();
        long day = GameClock.day(store);
        if (Population.applies(village)) {
            PopulationState p = village.population();
            dead = responsible(village, layout, p, target.id(), day);
            if (dead != null) {
                Population.die(world, village, p, dead, day, "fire", true);
            }
            for (Inhabitant h : p.living()) {
                if (target.id().equals(h.home)) {
                    homeless.add(h);
                }
            }
        }
        VillageLayout.Building b = Chantiers.burn(world, village, target.id(), true);
        if (b == null) {
            return null;
        }
        PopulationState p = village.population();
        if (!homeless.isEmpty() && Population.refugeOpen(village, p)) {
            for (Inhabitant h : homeless) {
                h.home = p.refuge;
                p.log(day, "rehoused", h.id, null, p.refuge);
            }
            dev.nakasar.hytale.peuples.world.Traces.raid(world, village, day);
            Population.announce(world, village, Message.translation(Population.KEYS + "raid.rehoused").param("village", village.name())
                    .param("count", homeless.size()).param("refuge", Message.translation(Chantiers.buildingKey(p.refuge))));
        } else {
            // Les habitants du bâtiment brûlé campent au bord du village jusqu'à sa reconstruction (world/Camps).
            dev.nakasar.hytale.peuples.world.Camps.refugees(world, store, village, b.id());
        }
        return new Loss(b, false, 0, dead);
    }

    /** Un grand bâtiment debout du plus haut palier, au hasard (comme Chantiers.burn sans cible). */
    static VillageLayout.Building pick(Village village, VillageLayout layout) {
        List<VillageLayout.Building> candidates = new ArrayList<>();
        int best = -1;
        for (VillageLayout.Building b : layout.buildings()) {
            if (b.small() || !village.isStanding(b.id())) {
                continue;
            }
            if (b.tier() > best) {
                best = b.tier();
                candidates.clear();
            }
            if (b.tier() == best) {
                candidates.add(b);
            }
        }
        return candidates.isEmpty() ? null : candidates.get(ThreadLocalRandom.current().nextInt(candidates.size()));
    }

    /** Bâtiment de métier (ou projet de terrain) logé dans le bâtiment du plan, ou null. */
    static Workshop workshopOf(Village village, String buildingId) {
        for (Workshop w : Workshops.all(village)) {
            if (buildingId.equals(w.building())) {
                return w;
            }
        }
        return null;
    }

    /**
     * Le responsable du bâtiment : le titulaire du poste qui y travaille (le premier du plan), sinon l'adulte (ou
     * l'ancien) le plus âgé qui y dort ; null s'il n'y a personne.
     */
    static Inhabitant responsible(Village village, VillageLayout layout, PopulationState p, String buildingId, long day) {
        for (VillageLayout.Job job : layout.jobs()) {
            if (buildingId.equals(job.building())) {
                Inhabitant h = p.holder(job.id());
                if (h != null && h.alive()) {
                    return h;
                }
            }
        }
        Inhabitant oldest = null;
        for (Inhabitant h : p.living()) {
            Ages.Stage s = h.stage(day);
            if (buildingId.equals(h.home) && (s == Ages.Stage.ADULT || s == Ages.Stage.ELDER) && (oldest == null || h.born < oldest.born)) {
                oldest = h;
            }
        }
        return oldest;
    }

    /** Raids : choisit les défenseurs parmi les habitants valides (titulaires de garde, puis les braves, puis les autres). */
    public static List<Inhabitant> defenders(Village village, long day, int count) {
        List<Inhabitant> out = new ArrayList<>();
        if (!Population.applies(village) || !village.population().seeded()) {
            return out;
        }
        List<Inhabitant> pool = new ArrayList<>();
        for (Inhabitant h : village.population().living()) {
            if (Population.ableAdult(h, day)) {
                pool.add(h);
            }
        }
        pool.sort((a, b) -> Integer.compare(rank(a), rank(b)));
        for (int i = 0; i < pool.size() && i < count; i++) {
            out.add(pool.get(i));
        }
        return out;
    }

    private static int rank(Inhabitant h) {
        if (h.hasJob() && Traits.matches(Traits.BRAVE, h.job)) {
            return 0;
        }
        return Traits.BRAVE.equals(h.trait) ? 1 : 2;
    }

    /** Un défenseur nommé est tombé : blessé, il se repose jusqu'au lendemain (pas de mort hors incendie). */
    public static void wound(Store<EntityStore> store, Village village, String id) {
        Inhabitant h = id == null ? null : village.population().byId(id);
        if (h == null || !h.alive()) {
            return;
        }
        long day = GameClock.day(store);
        h.wounded = day + 1;
        village.population().log(day, "wounded", h.id, null, null);
    }

    /** Ligne du bilan pour les défenseurs : niveau perdu, ou mort du responsable et relogement. */
    public static Message report(Village village, Loss loss) {
        String k = Population.KEYS + "raid.";
        if (loss.levelLost()) {
            return Message.translation(k + "reportLevel").param("building", Message.translation(Chantiers.buildingKey(loss.building().id())))
                    .param("level", Message.translation(Workshops.KEYS + "level." + loss.levelNow()));
        }
        if (loss.dead() == null) {
            return Message.translation(k + "reportNobody").param("building", Message.translation(Chantiers.buildingKey(loss.building().id())));
        }
        return Message.translation(k + "reportDead").param("name", loss.dead().fullName())
                .param("building", Message.translation(Chantiers.buildingKey(loss.building().id())));
    }
}
