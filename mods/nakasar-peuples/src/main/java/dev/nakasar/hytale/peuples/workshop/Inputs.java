package dev.nakasar.hytale.peuples.workshop;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageBoard;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.WorkshopState;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Les ateliers sont des raffineries (Kevin, 2026-11-16, doc « Structurer les types de bâtiments ») : chaque matin, un
 * atelier d'artisanat prend au dépôt du village ses ressources du jour ({@code Inputs} de l'asset Workshop, quantité par
 * niveau). Sans elles il est « à l'arrêt » ce jour-là : boutique fermée et pas de Part de l'Hôte. Ses commandes et sa
 * montée de niveau restent ouvertes : les joueurs peuvent le faire grandir en le nourrissant eux-mêmes. Les ressources
 * arrivent par le convoi d'un avant-poste, une route commerciale ou les joueurs.
 */
public final class Inputs {

    private Inputs() {
    }

    /** Ressources du jour de l'atelier à son niveau actuel (objet → quantité). Vide : rien à consommer. */
    public static Map<String, Integer> needs(Village village, Workshop w) {
        Map<String, Integer> out = new LinkedHashMap<>();
        if (w.inputs().length == 0) {
            return out;
        }
        WorkshopState ws = village.workshopIfPresent(w.getId());
        int level = ws == null ? 1 : Math.max(1, ws.level());
        for (VillageLayout.Material m : w.inputs()) {
            out.merge(m.itemId(), m.quantity() * level, Integer::sum);
        }
        return out;
    }

    /** Vrai si l'atelier tourne ce jour (pas de ressources à consommer, ou elles ont été prises ce matin). */
    public static boolean running(Village village, Workshop w) {
        WorkshopState ws = village.workshopIfPresent(w.getId());
        return w.inputs().length == 0 || ws == null || !ws.stopped();
    }

    /** Prélèvement du matin pour tous les ateliers ouverts des villages (thread du monde, une fois par jour de jeu). */
    public static void morning(World world, Store<EntityStore> store) {
        long day = GameClock.day(store);
        for (Village village : Villages.registry(world).all()) {
            for (Workshop w : Workshops.opened(village)) {
                if (w.inputs().length > 0) {
                    consume(world, village, w, day);
                }
            }
        }
    }

    /** Prend les ressources du jour au dépôt, ou met l'atelier à l'arrêt (annonce au changement d'état). */
    static void consume(World world, Village village, Workshop w, long day) {
        WorkshopState ws = village.workshop(w.getId());
        if (ws.inputDay() == day) {
            return;
        }
        boolean wasStopped = ws.stopped() && ws.inputDay() != Long.MIN_VALUE;
        Map<String, Integer> needs = needs(village, w);
        Map<String, Integer> deposit = Villages.depositContents(world, village);
        ItemContainer chest = Villages.depositChest(world, village);
        if (deposit == null || chest == null) {
            // Dépôt pas chargé : on ne juge pas l'atelier, il garde l'état de la veille et réessaie au prochain matin.
            return;
        }
        Map<String, Integer> missing = new LinkedHashMap<>();
        for (Map.Entry<String, Integer> e : needs.entrySet()) {
            int have = deposit.getOrDefault(e.getKey(), 0);
            if (have < e.getValue()) {
                missing.put(e.getKey(), e.getValue() - have);
            }
        }
        if (missing.isEmpty()) {
            for (Map.Entry<String, Integer> e : needs.entrySet()) {
                Requests.take(chest, e.getKey(), e.getValue());
            }
            ws.setInputs(day, false);
            if (wasStopped) {
                Chantiers.announce(world, village, Message.translation(Workshops.KEYS + "inputsBack")
                        .param("building", Message.translation(w.nameKey())), null, NotificationStyle.Success);
            }
            return;
        }
        ws.setInputs(day, true);
        if (!wasStopped) {
            Chantiers.announce(world, village, Message.translation(Workshops.KEYS + "inputsStopped")
                    .param("building", Message.translation(w.nameKey())).param("list", list(missing)), null, NotificationStyle.Warning);
        }
    }

    /** « 4 Peau légère, 2 Sel » pour les messages. */
    public static Message list(Map<String, Integer> items) {
        Message out = Message.empty();
        boolean first = true;
        for (Map.Entry<String, Integer> e : items.entrySet()) {
            if (!first) {
                out.insert(Message.raw(", "));
            }
            first = false;
            out.insert(Message.translation(Workshops.KEYS + "materialLine").param("count", e.getValue())
                    .param("item", VillageBoard.itemName(e.getKey())));
        }
        return out;
    }
}
