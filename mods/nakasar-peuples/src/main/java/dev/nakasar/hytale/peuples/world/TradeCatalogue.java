package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.builtin.adventure.shop.barter.BarterItemStack;
import com.hypixel.hytale.builtin.adventure.shop.barter.BarterShopAsset;
import com.hypixel.hytale.builtin.adventure.shop.barter.BarterTrade;
import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.village.AnnexState;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.WorkshopState;
import dev.nakasar.hytale.peuples.workshop.Workshop;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Ce qu'un village peut exporter (routes commerciales, Kevin, 16 novembre 2026) : sa propre production, quelle que soit
 * la ressource. Sources : les lots et livraisons de ses avant-postes debout, les spécialités de ses ateliers au niveau
 * II et plus, le tribut des lieux-dits qu'il tient, le luxe de son terroir dès le palier 2, et la réexportation de toute
 * ressource importée par une autre route active. Un lieu-dit exporte ce que vend son bâtiment de métier.
 */
public final class TradeCatalogue {

    /** D'où vient une marchandise du catalogue. */
    public enum Source {
        /** Avant-poste (lot ou livraison). */
        ANNEX,
        /** Atelier spécialisé, ou bâtiment de métier d'un lieu-dit. */
        WORKSHOP,
        /** Tribut d'un lieu-dit tenu. */
        TRIBUTE,
        /** Luxe du terroir (toujours disponible, sans prendre au dépôt). */
        TERROIR,
        /** Réexportation d'une ressource importée. */
        REEXPORT;

        /** Une source « produite » : sans dépôt chargé, la caravane part avec un chargement plein. */
        boolean produced() {
            return this != REEXPORT;
        }
    }

    private TradeCatalogue() {
    }

    /**
     * Catalogue du village (objet → source), filtré par ce que son peuple échange ({@link TradeGoods#allowed}).
     * `exceptRoute` : la route dont on calcule les exportations (ce qu'elle importe ne se réexporte pas vers elle), ou null.
     */
    public static Map<String, Source> of(World world, Village v, String exceptRoute, long day) {
        Map<String, Source> out = new LinkedHashMap<>();
        if (v.isHamlet()) {
            for (WorkshopState ws : v.workshops()) {
                Workshop w = Workshop.get(ws.id());
                if (w == null) {
                    continue;
                }
                shop(out, w.baseShop(), Source.WORKSHOP);
                Workshop.Specialty s = ws.level() >= 2 ? w.specialty(ws.specialty()) : null;
                if (s != null) {
                    shop(out, s.shop(ws.level()), Source.WORKSHOP);
                }
            }
            filter(out, v);
            return out;
        }
        TradeGoods.Luxury own = TradeGoods.terroir(v.people());
        if (own != null && v.tier() >= 2) {
            out.put(own.item(), Source.TERROIR);
        }
        for (AnnexState a : v.annexes()) {
            Workshop w = a.built() ? Workshop.get(a.id()) : null;
            if (w == null || w.annex() == null) {
                continue;
            }
            for (VillageLayout.Material m : w.annex().lots()) {
                out.putIfAbsent(m.itemId(), Source.ANNEX);
            }
            VillageLayout.Material d = w.annex().delivery();
            if (d != null) {
                out.putIfAbsent(d.itemId(), Source.ANNEX);
            }
        }
        for (WorkshopState ws : v.workshops()) {
            Workshop w = ws.level() >= 2 ? Workshop.get(ws.id()) : null;
            Workshop.Specialty s = w == null ? null : w.specialty(ws.specialty());
            if (s != null) {
                shop(out, s.shop(ws.level()), Source.WORKSHOP);
            }
        }
        for (Hamlets.Place h : Allegiance.holdings(world, v)) {
            Hamlet type = h.type();
            String item = type == null ? null : Allegiance.tributeItem(type.type());
            if (item != null) {
                out.putIfAbsent(item, Source.TRIBUTE);
            }
        }
        // Réexportation (Kevin : toute ressource importée, dès le niveau I, tant que sa route d'origine est active).
        for (String item : TradeRoutes.importedElsewhere(world, v, exceptRoute)) {
            out.putIfAbsent(item, Source.REEXPORT);
        }
        filter(out, v);
        return out;
    }

    private static void filter(Map<String, Source> out, Village v) {
        out.keySet().removeIf(item -> !TradeGoods.allowed(v.people(), item));
    }

    private static void shop(Map<String, Source> out, String shopId, Source source) {
        BarterShopAsset shop = shopId == null ? null : BarterShopAsset.getAssetMap().getAsset(shopId);
        BarterTrade[] trades = shop == null ? null : shop.getTrades();
        if (trades == null) {
            return;
        }
        for (BarterTrade t : trades) {
            BarterItemStack o = t == null ? null : t.getOutput();
            if (o != null && o.getItemId() != null) {
                out.putIfAbsent(o.getItemId(), source);
            }
        }
    }
}
