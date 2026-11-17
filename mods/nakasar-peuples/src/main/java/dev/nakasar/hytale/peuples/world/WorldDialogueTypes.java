package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.dialogue.DialogueCondition;
import dev.nakasar.hytale.peuples.dialogue.DialogueContext;
import dev.nakasar.hytale.peuples.dialogue.DialogueEffect;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import dev.nakasar.hytale.peuples.dialogue.DialogueSpeech;

import java.util.concurrent.ThreadLocalRandom;

/**
 * Effets et conditions de dialogue du monde vivant, enregistrés à part des effets de base ({@code DialogueTypes}).
 * Le PNJ qui parle est celui que le joueur a utilisé en dernier ({@link WorldLife#talkingTo}).
 * <ul>
 *   <li>{@code {"Type": "WorldAction", "Action": "..."}} : Shop, Rumour, Escort, Letter, Parley (voyageurs) ; InnShop,
 *       InnTravel, InnLetter (aubergiste) ; CampTurnIn, CampDefend, CampDonate, CampShop (campements) ; HideAndSeek
 *       (enfants) ; FeastOffering, FairRace (hôtes du calendrier).</li>
 *   <li>Commerce : TradeShop, TradeWhere (caravaniers des routes commerciales).</li>
 *   <li>Conquête : HamletOwner (« à qui appartient ce lieu ? »), HamletRally (lettre de ralliement ; aussi en
 *   WorldCheck).</li>
 *   <li>{@code {"Type": "WorldCheck", "Check": "..."}} : InnLevel2, InnLevel3, Parley (villages rivaux et joueur Ami des
 *       deux), CampOpen (quête du campement pas encore faite).</li>
 * </ul>
 */
public final class WorldDialogueTypes {

    private WorldDialogueTypes() {
    }

    public static void register() {
        DialogueEffect.CODEC.register("WorldAction", ActionEffect.class, ActionEffect.CODEC);
        DialogueCondition.CODEC.register("WorldCheck", CheckCondition.class, CheckCondition.CODEC);
    }

    private static Ref<EntityStore> npc(DialogueContext c) {
        return WorldLife.talkingTo(c.playerRef().getUuid());
    }

    public static final class ActionEffect extends DialogueEffect {
        public static final BuilderCodec<ActionEffect> CODEC = BuilderCodec.builder(ActionEffect.class, ActionEffect::new)
                .append(new KeyedCodec<>("Action", Codec.STRING), (e, v) -> e.action = v, e -> e.action)
                .documentation("Action du monde vivant (voir WorldDialogueTypes).")
                .add()
                .build();

        String action;

        @Override
        public boolean apply(DialogueContext c) {
            World world = c.world();
            Ref<EntityStore> npc = npc(c);
            if (action == null || npc == null) {
                return false;
            }
            switch (action) {
                case "Rumour" -> {
                    DialogueSpeech.say(c.playerRef(), Rumours.random(world, c.store(), c.ref()));
                    return true;
                }
                case "Shop", "Escort", "Letter", "Parley" -> {
                    Travellers.Traveller t = Travellers.of(world, npc);
                    if (t == null) {
                        return false;
                    }
                    return switch (action) {
                        case "Shop" -> Travellers.openShop(world, c.store(), c.ref(), c.playerRef(), t);
                        case "Escort" -> Travellers.escort(world, c.playerRef(), t);
                        case "Letter" -> Travellers.letter(world, c.store(), c.ref(), c.playerRef(), t, false);
                        default -> Travellers.letter(world, c.store(), c.ref(), c.playerRef(), t, true);
                    };
                }
                case "InnShop", "InnTravel", "InnLetter" -> {
                    Inns.Inn inn = Inns.of(world, npc);
                    Village first = inn == null ? null : Inns.firstVillage(world, inn);
                    if (first == null) {
                        return false;
                    }
                    return switch (action) {
                        case "InnShop" -> dev.nakasar.hytale.peuples.reputation.Shops.open(c.store(), c.ref(), c.playerRef(), first, Inns.SHOP);
                        case "InnTravel" -> dev.nakasar.hytale.peuples.reputation.Shops.open(c.store(), c.ref(), c.playerRef(), first,
                                Travellers.shop(first.people()));
                        default -> {
                            String[] ids = inn.link().split("\\|");
                            Village to = Villages.registry(world).byId(ids[ThreadLocalRandom.current().nextInt(ids.length)]);
                            yield to != null && Travellers.giveLetter(world, c.store(), c.ref(), c.playerRef(), to, null);
                        }
                    };
                }
                case "HamletShop", "HamletVisits", "HamletOwner", "HamletRally", "HamletOffering", "HamletWork" -> {
                    Hamlets.Place h = Hamlets.of(world, npc);
                    if (h == null) {
                        return false;
                    }
                    return switch (action) {
                        case "HamletShop" -> Hamlets.openShop(world, c.store(), c.ref(), c.playerRef(), h);
                        case "HamletOwner" -> Allegiance.sayOwner(world, c.store(), c.playerRef(), h);
                        case "HamletRally" -> Allegiance.rally(world, c.store(), c.ref(), c.playerRef(), h);
                        case "HamletOffering" -> Hamlets.offer(world, c.store(), c.ref(), c.playerRef(), h);
                        case "HamletWork" -> Hamlets.sayWork(world, c.store(), c.playerRef(), h);
                        default -> Hamlets.sayVisits(world, c.store(), c.playerRef(), h);
                    };
                }
                case "TripShop", "TripWhere" -> {
                    HamletTrips.Trip t = HamletTrips.of(world, npc);
                    if (t == null) {
                        return false;
                    }
                    return action.equals("TripShop") ? HamletTrips.openShop(world, c.store(), c.ref(), c.playerRef(), t)
                            : HamletTrips.where(world, c.store(), c.playerRef(), t);
                }
                case "TradeShop", "TradeWhere" -> {
                    TradeCaravans.Caravan t = TradeCaravans.of(world, npc);
                    if (t == null) {
                        return false;
                    }
                    return action.equals("TradeShop") ? TradeCaravans.openShop(world, c.store(), c.ref(), c.playerRef(), t)
                            : TradeCaravans.where(world, c.store(), c.playerRef(), t);
                }
                case "CampTurnIn", "CampDefend", "CampDonate", "CampShop" -> {
                    Camps.Camp camp = Camps.of(world, npc);
                    if (camp == null) {
                        return false;
                    }
                    return switch (action) {
                        case "CampTurnIn" -> Camps.turnIn(world, c.store(), c.ref(), c.playerRef(), camp);
                        case "CampDefend" -> Camps.defend(world, c.store(), c.ref(), c.playerRef(), camp);
                        case "CampDonate" -> Camps.donate(world, c.store(), c.ref(), c.playerRef(), camp);
                        default -> Camps.shop(world, c.store(), c.ref(), c.playerRef(), camp);
                    };
                }
                case "HideAndSeek" -> {
                    return Surroundings.hideAndSeek(world, c.store(), c.ref(), c.playerRef(), Surroundings.childVillage(world, npc));
                }
                case "FeastOffering" -> {
                    return Calendar.feastOffering(world, c.store(), c.ref(), c.playerRef(), Calendar.hostVillage(world, npc));
                }
                case "FairRace" -> {
                    return Calendar.race(world, c.store(), c.ref(), c.playerRef(), Calendar.hostVillage(world, npc));
                }
                default -> {
                    c.playerRef().sendMessage(Message.raw("WorldAction inconnue : " + action));
                    return false;
                }
            }
        }

        @Override
        public boolean closesDialogue() {
            return action != null && (action.endsWith("Shop") || action.equals("InnTravel"));
        }
    }

    public static final class CheckCondition extends DialogueCondition {
        public static final BuilderCodec<CheckCondition> CODEC = BuilderCodec.builder(CheckCondition.class, CheckCondition::new)
                .append(new KeyedCodec<>("Check", Codec.STRING), (e, v) -> e.check = v, e -> e.check)
                .documentation("Test du monde vivant (voir WorldDialogueTypes).")
                .add()
                .build();

        String check;

        @Override
        public boolean test(DialogueContext c) {
            World world = c.world();
            Ref<EntityStore> npc = npc(c);
            if (check == null || npc == null) {
                return false;
            }
            return switch (check) {
                case "InnLevel2", "InnLevel3" -> {
                    Inns.Inn inn = Inns.of(world, npc);
                    yield inn != null && inn.level() >= (check.endsWith("3") ? 3 : 2);
                }
                case "Parley" -> {
                    Travellers.Traveller t = Travellers.of(world, npc);
                    Village a = t == null ? null : Villages.registry(world).byId(t.from());
                    Village b = t == null ? null : Villages.registry(world).byId(t.to());
                    yield a != null && b != null && Relations.value(world, a, b) <= Relations.RIVAL;
                }
                case "HamletRally" -> {
                    Hamlets.Place h = Hamlets.of(world, npc);
                    yield h != null && Allegiance.canRally(world, c.store(), c.ref(), h);
                }
                case "HamletWary" -> {
                    Hamlets.Place h = Hamlets.of(world, npc);
                    yield h != null && Hamlets.wary(world, c.store(), c.ref(), h);
                }
                case "CampOpen" -> {
                    Camps.Camp camp = Camps.of(world, npc);
                    yield camp != null && (c.player() == null || !c.player().hasFlag(Camps.FLAG + camp.id)) && camp.quest == 0;
                }
                default -> false;
            };
        }
    }
}
