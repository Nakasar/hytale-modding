package dev.nakasar.hytale.peuples;

import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.server.core.asset.HytaleAssetStore;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.peuples.command.VillageCommand;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.raid.RaidAttitudeSystem;
import dev.nakasar.hytale.peuples.raid.RaidDeathSystem;
import dev.nakasar.hytale.peuples.raid.RaidLocationCondition;
import dev.nakasar.hytale.peuples.raid.RaidSystem;
import dev.nakasar.hytale.peuples.raid.Raids;
import com.hypixel.hytale.builtin.adventure.worldevents.WorldEventsPlugin;
import dev.nakasar.hytale.peuples.request.Criers;
import dev.nakasar.hytale.peuples.request.RequestDeathSystem;
import dev.nakasar.hytale.peuples.request.RequestHud;
import dev.nakasar.hytale.peuples.request.RequestSpawns;
import dev.nakasar.hytale.peuples.request.RequestSystem;
import dev.nakasar.hytale.peuples.request.RequestTemplate;
import dev.nakasar.hytale.peuples.request.VillagerUseSystem;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.reputation.VillageAttitudeSystem;
import dev.nakasar.hytale.peuples.reputation.VillageBlockSystem;
import dev.nakasar.hytale.peuples.reputation.VillagerHarmSystems;
import dev.nakasar.hytale.peuples.village.OpenBoardInteraction;
import dev.nakasar.hytale.peuples.village.VillageEntrySystem;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageLifeSystem;
import dev.nakasar.hytale.peuples.village.Villagers;
import dev.nakasar.hytale.peuples.village.VillageNoRegenSystem;
import dev.nakasar.hytale.peuples.village.VillageRegistry;
import dev.nakasar.hytale.peuples.village.VillageSeeder;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.village.TrorkCampSeeder;
import dev.nakasar.hytale.peuples.trork.MeatOfferings;
import dev.nakasar.hytale.peuples.trork.WarPaintInteraction;
import dev.nakasar.hytale.peuples.trork.WarPaintSystem;
import dev.nakasar.hytale.peuples.klops.Klops;
import dev.nakasar.hytale.peuples.klops.KlopsSystem;

/**
 * Point d'entrée du mod « Peuples d'Orbis » : des villages vivants des peuples d'Orbis qui grandissent avec l'aide du
 * joueur (GDD : https://claude.ai/artifact/FJ15VjWp3pgnt9kmRWjfV7, résumé dans docs/peuples/gdd.md).
 *
 * <p>Étape 1, le socle :
 * <ul>
 *   <li>les villages d'un monde ({@link VillageRegistry}, ressource sauvegardée avec le monde), ancrés sur le bloc cœur
 *       invisible {@value Villages#HEART_BLOCK}, avec un dépôt (coffre vanilla du peuple) et un tableau (panneau vanilla
 *       du peuple, interaction {@value OpenBoardInteraction#TYPE_ID} qui ouvre la page vanilla BlockLore remplie par
 *       le Java) ;</li>
 *   <li>les dialogues, assets JSON {@code Server/}{@value Dialogue#PATH} (conditions et effets par codec), menés dans
 *       la fenêtre du mod ({@code DialoguePage}, mise en page .ui du pack) ou par le tchat ;</li>
 *   <li>l'état du joueur ({@link PeuplesPlayer} : drapeaux de dialogue), sauvegardé avec lui ;</li>
 *   <li>la commande de test {@code /village}.</li>
 * </ul>
 * Étape 2, le premier village :
 * <ul>
 *   <li>les plans de village, assets JSON {@code Server/}{@value VillageLayout#PATH} (prefabs vanilla autour du cœur,
 *       générés par {@code tools/generate_village_layouts.py}), bâtis par {@code VillageBuilder} ;</li>
 *   <li>{@link VillageSeeder} : un village kweebec posé tout seul près du point d'apparition du monde par défaut ;</li>
 *   <li>{@link VillageEntrySystem} : titre d'écran à l'entrée d'un village, bannière de carte révélée à l'approche ;</li>
 *   <li>{@link VillageNoRegenSystem} : les Kweebecs des prefabs ne se régénèrent pas (règle permanente, AGENTS.md).</li>
 * </ul>
 * Étape 3, les demandes du tableau :
 * <ul>
 *   <li>les modèles de demande, assets JSON {@code Server/}{@value RequestTemplate#PATH} (six types : récolte,
 *       fabrication, chasse, livraison, escorte, défense), tirés chaque matin dans les trois cases du tableau ;</li>
 *   <li>{@link RequestSystem} : suivi des demandes prises (lecture du dépôt, lieux, bandes, captif, veille de nuit,
 *       échéance) et affichage dans le suivi d'objectifs vanilla du HUD ({@link RequestHud}) ;</li>
 *   <li>{@link RequestDeathSystem} : morts de PNJ qui comptent (bande, Trorks chassés, captif, crieur) ;</li>
 *   <li>{@link VillagerUseSystem} et {@link Criers} : le crieur de chaque village ouvre son dialogue, le guetteur prend
 *       la missive, le captif suit ;</li>
 *   <li>le tableau à boutons {@code BoardPage} (page .ui du pack), la page texte restant accessible accroupi.</li>
 * </ul>
 * Étape 4, la réputation :
 * <ul>
 *   <li>{@link Reputations} : réputation de village (avec le joueur) et de peuple (ReputationPlugin vanilla, groupes
 *       {@code Server/NPC/Reputation/Groups}), six rangs {@link Rank} (assets {@code Server/NPC/Reputation/Ranks}) ;</li>
 *   <li>{@link VillageAttitudeSystem} : les PNJ d'un village traitent le joueur selon son rang (gardes, jeunes) ;</li>
 *   <li>{@link VillagerHarmSystems}, {@link VillageBlockSystem} : frapper, tuer un villageois ou casser un bâtiment du
 *       village coûte de la réputation ;</li>
 *   <li>le marchand de chaque village et ses échoppes de troc vanilla par rang ({@code Server/BarterShops}).</li>
 * </ul>
 * Étape 5, les chantiers et les métiers :
 * <ul>
 *   <li>{@link VillageLifeSystem} : jauge pleine et matériaux au dépôt, le chantier du palier suivant s'ouvre
 *       (échafaudage en blocs vanilla, un jour de jeu), puis les prefabs vanilla sont collés et le village change de
 *       palier ({@code village/Chantiers}) ; un bâtiment peut brûler ({@code village/Burning}) et sera rebâti ;</li>
 *   <li>{@link Villagers} : les villageois à métier du plan (jardinière, bâtisseur, guetteur...), leur poste de jour et
 *       leur logis de nuit.</li>
 * </ul>
 * Étape 6, les raids :
 * <ul>
 *   <li>{@link Raids} : une nuit, une bande trork marche sur un village ; c'est un évènement de monde
 *       ({@value Raids#EVENT}, moteur des brèches vanilla, lieu donné par {@link RaidLocationCondition}) suivi par
 *       {@link RaidSystem} ; les gardes du village (rôles du mod) se battent aux côtés du joueur
 *       ({@link RaidAttitudeSystem}) ; {@link RaidDeathSystem} compte les morts ;</li>
 *   <li>le bilan : victoire (essor, réputation, faveurs, trophée) ou défaite (un bâtiment brûle, le village perd un
 *       palier) ;</li>
 *   <li>la chaîne de quêtes kweebec, jusqu'à la Graine d'Écho.</li>
 * </ul>
 * Étape 7, la deuxième route de la zone 1 :
 * <ul>
 *   <li>{@link TrorkCampSeeder} : un camp trork posé à l'écart du village kweebec ; il commence hostile et
 *       s'apprivoise par la viande ({@link MeatOfferings}, comportement vanilla des Trorks), puis par ses demandes et
 *       la chaîne du chef, jusqu'à la Peinture de guerre ({@code trork/WarPaint}) ;</li>
 *   <li>réputations croisées ({@code reputation/Rivals}) : aider un peuple coûte auprès de son rival ;</li>
 *   <li>{@link Klops} : le Klops errant va de village en village, troque et confie des colis.</li>
 * </ul>
 */
public final class PeuplesPlugin extends JavaPlugin {

    private static PeuplesPlugin instance;

    public PeuplesPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static PeuplesPlugin get() {
        return instance;
    }

    @Override
    protected void setup() {
        // Les dialogues : un magasin d'assets comme les rangs de réputation vanilla (ReputationPlugin).
        getAssetRegistry().register(HytaleAssetStore.builder(Dialogue.class, new DefaultAssetMap<String, Dialogue>())
                .setPath(Dialogue.PATH)
                .setCodec(Dialogue.CODEC)
                .setKeyFunction(Dialogue::getId)
                .build());

        getAssetRegistry().register(HytaleAssetStore.builder(VillageLayout.class, new DefaultAssetMap<String, VillageLayout>())
                .setPath(VillageLayout.PATH)
                .setCodec(VillageLayout.CODEC)
                .setKeyFunction(VillageLayout::getId)
                .build());

        getAssetRegistry().register(HytaleAssetStore.builder(RequestTemplate.class, new DefaultAssetMap<String, RequestTemplate>())
                .setPath(RequestTemplate.PATH)
                .setCodec(RequestTemplate.CODEC)
                .setKeyFunction(RequestTemplate::getId)
                .build());

        getCodecRegistry(Interaction.CODEC).register(OpenBoardInteraction.TYPE_ID, OpenBoardInteraction.class, OpenBoardInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register(WarPaintInteraction.TYPE_ID, WarPaintInteraction.class, WarPaintInteraction.CODEC);

        var entities = getEntityStoreRegistry();
        Villages.setResourceType(entities.registerResource(VillageRegistry.class, VillageRegistry.ID, VillageRegistry.CODEC));
        PeuplesPlayer.setComponentType(entities.registerComponent(PeuplesPlayer.class, PeuplesPlayer.ID, PeuplesPlayer.CODEC));
        entities.registerSystem(new VillageSeeder());
        entities.registerSystem(new VillageEntrySystem());
        entities.registerSystem(new VillageNoRegenSystem());
        entities.registerSystem(new RequestSystem());
        entities.registerSystem(new RequestDeathSystem());
        entities.registerSystem(new VillagerUseSystem());
        entities.registerSystem(new VillageAttitudeSystem());
        entities.registerSystem(new VillagerHarmSystems.Hit());
        entities.registerSystem(new VillagerHarmSystems.Kill());
        entities.registerSystem(new VillageBlockSystem());
        entities.registerSystem(new VillageLifeSystem());
        entities.registerSystem(new RaidSystem());
        entities.registerSystem(new RaidDeathSystem());
        entities.registerSystem(new RaidAttitudeSystem());
        // Étape 7 : camp trork, viande, Peinture de guerre, Klops errant.
        entities.registerSystem(new TrorkCampSeeder());
        entities.registerSystem(new MeatOfferings());
        entities.registerSystem(new WarPaintSystem());
        entities.registerSystem(new KlopsSystem());
        WorldEventsPlugin.registerCondition(this, RaidLocationCondition.TYPE, RaidLocationCondition.CODEC, RaidLocationCondition.Config.CODEC);

        getCommandRegistry().registerCommand(new VillageCommand());

        getLogger().atInfo().log("Nakasar Peuples : villages (%s), plans (Server/%s), tableau (%s), dialogues (Server/%s), demandes (Server/%s), /village enregistrés",
                VillageRegistry.ID, VillageLayout.PATH, OpenBoardInteraction.TYPE_ID, Dialogue.PATH, RequestTemplate.PATH);
    }

    @Override
    protected void shutdown() {
        Dialogues.clearAll();
        RequestSpawns.clearAll();
        Criers.clearAll();
        RequestHud.clearAll();
        VillageBlockSystem.clearAll();
        Villagers.clearAll();
        Raids.clearAll();
        MeatOfferings.clearAll();
        Klops.clearAll();
    }
}
