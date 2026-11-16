package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.command.system.CommandContext;
import com.hypixel.hytale.server.core.command.system.arguments.system.OptionalArg;
import com.hypixel.hytale.server.core.command.system.arguments.types.ArgTypes;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractCommandCollection;
import com.hypixel.hytale.server.core.command.system.basecommands.AbstractPlayerCommand;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

import java.util.List;
import java.util.Locale;
import java.util.Random;

/**
 * {@code /monde} : l'état du monde vivant et, pour les opérateurs ({@value #ADMIN}), de quoi lancer chaque élément
 * sans attendre (voyageur, embuscade, campement, auberge, relation, escarmouche, fête, foire, migration).
 */
public final class WorldCommand extends AbstractCommandCollection {

    public static final String ADMIN = "nakasar.peuples.admin";
    static final String KEYS = WorldLife.KEYS + "command.";
    /** Le village le plus proche du joueur, à moins de cette distance. */
    static final int RANGE = 600;

    public WorldCommand() {
        super("monde", KEYS + "desc");
        setPermissionGroups("hytale:Adventurer");
        addSubCommand(new StateCommand());
        addSubCommand(new TravellerCommand());
        addSubCommand(new AmbushCommand());
        addSubCommand(new CampCommand());
        addSubCommand(new InnCommand());
        addSubCommand(new HamletCommand());
        addSubCommand(new HamletTripCommand());
        addSubCommand(new RelationCommand());
        addSubCommand(new SkirmishCommand());
        addSubCommand(new CalendarCommand("fete"));
        addSubCommand(new CalendarCommand("foire"));
        addSubCommand(new CalendarCommand("migration"));
        addSubCommand(new CalendarCommand("arret"));
    }

    static Village nearest(World world, PlayerRef player) {
        Vector3d at = player.getTransform().getPosition();
        Village v = WorldLife.nearestVillage(world, at.x(), at.z(), RANGE);
        if (v == null) {
            player.sendMessage(Message.translation(KEYS + "noVillage").param("range", RANGE));
        }
        return v;
    }

    /**
     * La liaison du village vers `dest` (nom ou id d'un village, sans tenir compte des majuscules, accents, espaces et
     * tirets), ou vers son voisin le plus proche si `dest` est null ; null avec un message sinon.
     */
    static Links.Link link(World world, PlayerRef player, Village v, String dest) {
        if (dest == null || dest.isBlank()) {
            return link(world, player, v);
        }
        Village to = byName(world, dest);
        if (to == null) {
            player.sendMessage(Message.translation(KEYS + "noSuchVillage").param("name", dest));
            return null;
        }
        Links.Link l = Links.of(world, v.id(), to.id());
        if (l == null) {
            player.sendMessage(Message.translation(KEYS + "noLinkTo").param("village", v.name()).param("to", to.name())
                    .param("max", Links.MAX_LENGTH));
        }
        return l;
    }

    /** Le village dont l'id ou le nom correspond à `name`, ou null. */
    static Village byName(World world, String name) {
        Village exact = Villages.registry(world).byId(name);
        if (exact != null) {
            return exact;
        }
        String wanted = normalize(name);
        for (Village v : Villages.registry(world).all()) {
            if (normalize(v.name()).equals(wanted) || normalize(v.id()).equals(wanted)) {
                return v;
            }
        }
        return null;
    }

    private static String normalize(String s) {
        String n = java.text.Normalizer.normalize(s, java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        return n.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]", "");
    }

    /** La liaison du village vers son voisin le plus proche (ou null, avec un message). */
    static Links.Link link(World world, PlayerRef player, Village v) {
        List<Links.Link> links = Links.of(world, v);
        if (links.isEmpty()) {
            player.sendMessage(Message.translation(KEYS + "noLink").param("village", v.name()).param("max", Links.MAX_LENGTH));
            return null;
        }
        return links.get(0);
    }

    private abstract static class AdminCommand extends AbstractPlayerCommand {
        AdminCommand(String name, String desc) {
            super(name, desc);
            requirePermission(ADMIN);
        }
    }

    private static final class StateCommand extends AbstractPlayerCommand {
        StateCommand() {
            super("etat", KEYS + "state.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            long day = GameClock.day(store);
            player.sendMessage(Message.translation(KEYS + "state.header").param("npcs", WorldLife.alive())
                    .param("links", Links.all(world).size()).param("structures", Sites.count(world)));
            for (Travellers.Traveller t : Travellers.all(world)) {
                player.sendMessage(Travellers.describe(world, t));
            }
            for (Camps.Camp c : Camps.all(world)) {
                Village v = Villages.registry(world).byId(c.village());
                player.sendMessage(Message.translation(KEYS + "state.camp").param("type", Message.translation(Camps.KEYS + "type." + c.type().key()))
                        .param("village", v == null ? "?" : v.name()).param("x", c.x()).param("z", c.z()));
            }
            for (Inns.Inn inn : Inns.all(world)) {
                player.sendMessage(Message.translation(KEYS + "state.inn").param("link", inn.link()).param("level", inn.level())
                        .param("open", inn.open() ? 1 : 0).param("x", inn.x()).param("z", inn.z()));
            }
            List<Hamlets.Place> hamlets = Hamlets.all(world);
            List<HamletTrips.Trip> trips = HamletTrips.all(world);
            player.sendMessage(Message.translation(Hamlets.KEYS + "state").param("count", hamlets.size())
                    .param("built", (int) hamlets.stream().filter(h -> h.stage() == Hamlets.BUILT).count()).param("trips", trips.size()));
            for (HamletTrips.Trip t : trips) {
                player.sendMessage(HamletTrips.describe(world, store, t));
            }
            for (Links.Link l : Links.all(world)) {
                int value = Relations.value(world, l.a(), l.b());
                player.sendMessage(Message.translation(KEYS + "state.link").param("a", l.a().name()).param("b", l.b().name())
                        .param("length", (int) l.length()).param("relation", value)
                        .param("state", Message.translation(Relations.KEYS + "state." + Relations.state(value)))
                        .param("traffic", Links.traffic(world, l.key(), day)));
            }
            player.sendMessage(Message.translation(KEYS + "state.calendar")
                    .param("feast", Calendar.next(day, Calendar.FEAST_EVERY, 3) - day)
                    .param("fair", Calendar.next(day, Calendar.FAIR_EVERY, 7) - day)
                    .param("migration", Calendar.next(day, Calendar.MIGRATION_EVERY, 5) - day)
                    .param("running", String.join(", ", Calendar.running())));
        }
    }

    private static final class TravellerCommand extends AdminCommand {
        private final OptionalArg<String> kind = withOptionalArg("genre", KEYS + "traveller.arg", ArgTypes.STRING);
        private final OptionalArg<String> to = withOptionalArg("vers", KEYS + "to.arg", ArgTypes.STRING);

        TravellerCommand() {
            super("voyageur", KEYS + "traveller.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village v = nearest(world, player);
            Links.Link l = v == null ? null : link(world, player, v, to.get(context));
            if (l == null) {
                return;
            }
            Travellers.Kind k = Travellers.Kind.CARAVAN;
            String arg = kind.get(context);
            if (arg != null) {
                String a = arg.toLowerCase(Locale.ROOT);
                k = a.startsWith("m") && a.contains("ss") ? Travellers.Kind.MESSENGER : a.startsWith("m") ? Travellers.Kind.MERCHANT
                        : a.startsWith("p") ? Travellers.Kind.PILGRIM : Travellers.Kind.CARAVAN;
            }
            Travellers.start(world, k, v, l.other(v.id()));
            player.sendMessage(Message.translation(KEYS + "traveller.done").param("kind", Message.translation(Travellers.KEYS + "kind." + k.key()))
                    .param("to", l.other(v.id()).name()));
        }
    }

    private static final class AmbushCommand extends AdminCommand {
        AmbushCommand() {
            super("embuscade", KEYS + "ambush.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Vector3d me = player.getTransform().getPosition();
            Travellers.Traveller best = null;
            double bestD = Double.MAX_VALUE;
            Routes.Path bestPath = null;
            for (Travellers.Traveller t : Travellers.all(world)) {
                Village from = Villages.registry(world).byId(t.from());
                Village to = Villages.registry(world).byId(t.to());
                if (from == null || to == null) {
                    continue;
                }
                Routes.Path p = Links.path(world, from, to);
                double[] at = p.point(t.at);
                double d = Math.hypot(at[0] - me.x(), at[1] - me.z());
                if (d < bestD) {
                    bestD = d;
                    best = t;
                    bestPath = p;
                }
            }
            if (best == null || bestD > Ambushes.WITNESS) {
                player.sendMessage(Message.translation(KEYS + "ambush.none").param("range", Ambushes.WITNESS));
                return;
            }
            Village from = Villages.registry(world).byId(best.from());
            Walk walk = Walk.of(best.walkKey());
            if (Ambushes.force(world, store, best.walkKey(), bestPath.point(best.at), bestPath.dir(best.at), from.people(), walk.alive(),
                    WorldLife.players(world, store))) {
                best.ambush = 2;
                Travellers.save(world, best);
            }
        }
    }

    private static final class CampCommand extends AdminCommand {
        private final OptionalArg<String> type = withOptionalArg("genre", KEYS + "camp.arg", ArgTypes.STRING);

        CampCommand() {
            super("campement", KEYS + "camp.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village v = nearest(world, player);
            if (v == null) {
                return;
            }
            Camps.Type t = Camps.Type.HUNTERS;
            String arg = type.get(context);
            if (arg != null) {
                String a = arg.toLowerCase(Locale.ROOT);
                if (a.startsWith("chas") || a.startsWith("hunt")) {
                    t = Camps.Type.HUNTERS;
                } else if (a.startsWith("b") || a.startsWith("wood")) {
                    t = Camps.Type.WOODCUTTERS;
                } else if (a.startsWith("p")) {
                    t = Camps.Type.PROSPECTORS;
                } else if (a.startsWith("mar") || a.startsWith("mer")) {
                    t = Camps.Type.MERCHANTS;
                } else if (a.startsWith("r")) {
                    t = Camps.Type.REFUGEES;
                }
            }
            if (t == Camps.Type.REFUGEES) {
                Camps.refugees(world, store, v, "-");
                return;
            }
            Camps.Camp c = Camps.start(world, t, v, GameClock.day(store), new Random());
            player.sendMessage(c == null ? Message.translation(KEYS + "camp.noRoom")
                    : Message.translation(KEYS + "camp.done").param("x", c.x()).param("z", c.z()));
        }
    }

    private static final class InnCommand extends AdminCommand {
        private final OptionalArg<String> to = withOptionalArg("vers", KEYS + "to.arg", ArgTypes.STRING);
        InnCommand() {
            super("auberge", KEYS + "inn.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village v = nearest(world, player);
            Links.Link l = v == null ? null : link(world, player, v, to.get(context));
            if (l == null) {
                return;
            }
            Inns.Inn inn = Inns.get(world, l.key());
            if (inn == null) {
                inn = Inns.begin(world, store, l);
            }
            // Les travaux finissent tout de suite : l'auberge se pose à l'approche d'un joueur.
            inn.end = GameClock.seconds(store);
            WorldLife.registry(world).put(WorldLifeRegistry.Part.INNS, l.key(), inn.format());
            player.sendMessage(Message.translation(KEYS + "inn.done").param("x", inn.x()).param("z", inn.z()));
        }
    }

    private static final class RelationCommand extends AdminCommand {
        private final OptionalArg<Integer> value = withOptionalArg("valeur", KEYS + "relation.arg", ArgTypes.INTEGER);
        private final OptionalArg<String> to = withOptionalArg("vers", KEYS + "to.arg", ArgTypes.STRING);

        RelationCommand() {
            super("relation", KEYS + "relation.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village v = nearest(world, player);
            Links.Link l = v == null ? null : link(world, player, v, to.get(context));
            if (l == null) {
                return;
            }
            Integer n = value.get(context);
            if (n != null) {
                Relations.set(world, l.a(), l.b(), n);
            }
            int now = Relations.value(world, l.a(), l.b());
            player.sendMessage(Message.translation(KEYS + "relation.done").param("a", l.a().name()).param("b", l.b().name())
                    .param("value", now).param("state", Message.translation(Relations.KEYS + "state." + Relations.state(now))));
        }
    }

    private static final class SkirmishCommand extends AdminCommand {
        private final OptionalArg<String> to = withOptionalArg("vers", KEYS + "to.arg", ArgTypes.STRING);
        SkirmishCommand() {
            super("escarmouche", KEYS + "skirmish.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Village v = nearest(world, player);
            Links.Link l = v == null ? null : link(world, player, v, to.get(context));
            if (l != null) {
                Relations.start(world, store, l, WorldLife.players(world, store));
            }
        }
    }

    private static final class CalendarCommand extends AdminCommand {
        private final String what;

        CalendarCommand(String what) {
            super(what, KEYS + "calendar." + what + ".desc");
            this.what = what;
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            switch (what) {
                case "fete" -> player.sendMessage(Message.translation(KEYS + "calendar.feast").param("count", Calendar.startFeast(world, store)));
                case "foire" -> {
                    Village v = Calendar.startFair(world, store, GameClock.day(store));
                    player.sendMessage(v == null ? Message.translation(KEYS + "calendar.noFair")
                            : Message.translation(KEYS + "calendar.fair").param("village", v.name()));
                }
                case "migration" -> {
                    Village v = Calendar.startMigration(world, store, new Random());
                    player.sendMessage(v == null ? Message.translation(KEYS + "calendar.noMigration")
                            : Message.translation(KEYS + "calendar.migration").param("village", v.name()));
                }
                default -> {
                    Calendar.stopAll(world, store);
                    player.sendMessage(Message.translation(KEYS + "calendar.stopped"));
                }
            }
        }
    }

    /** Distance où {@code /monde lieudit} et {@code /monde commerce} cherchent le lieu-dit le plus proche. */
    static final int HAMLET_RANGE = 200;

    /** Message d'état d'un lieu-dit (commande). */
    static Message describe(World world, Store<EntityStore> store, Hamlets.Place h) {
        Hamlet type = h.type();
        Village v = Hamlets.state(world, h);
        int level = 0;
        dev.nakasar.hytale.peuples.workshop.Workshop w = Hamlets.workshop(h);
        if (v != null && w != null && dev.nakasar.hytale.peuples.workshop.Workshops.known(v, w.getId())) {
            level = v.workshop(w.getId()).level();
        }
        return Message.translation(Hamlets.KEYS + "cmd.state").param("name", h.name())
                .param("people", Message.translation(type == null ? "?" : type.people().nameKey()))
                .param("level", level).param("x", h.x()).param("z", h.z())
                .param("stage", Message.translation(Hamlets.KEYS + "cmd.stage." + h.stage()))
                .param("visits", Hamlets.visits(world, h, GameClock.day(store)));
    }

    /**
     * {@code /monde lieudit [--genre]} : l'état du lieu-dit le plus proche ; avec un genre (ou s'il n'y en a aucun près),
     * en prévoit un à la place du joueur, du peuple du village le plus proche et tourné vers lui.
     */
    private static final class HamletCommand extends AdminCommand {
        private final OptionalArg<String> type = withOptionalArg("genre", Hamlets.KEYS + "cmd.hamlet.arg", ArgTypes.STRING);

        HamletCommand() {
            super("lieudit", Hamlets.KEYS + "cmd.hamlet.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Vector3d at = player.getTransform().getPosition();
            String arg = type.get(context);
            Hamlets.Place near = Hamlets.nearest(world, at.x(), at.z(), HAMLET_RANGE);
            if (arg == null && near != null) {
                player.sendMessage(describe(world, store, near));
                return;
            }
            Village v = nearest(world, player);
            if (v == null) {
                return;
            }
            Hamlet asset = null;
            if (arg != null) {
                List<String> names = new java.util.ArrayList<>();
                for (Hamlet h : Hamlet.of(v.people())) {
                    names.add(h.type());
                    if (h.type().equalsIgnoreCase(arg)) {
                        asset = h;
                    }
                }
                if (asset == null) {
                    player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.unknownType").param("type", arg).param("types", String.join(", ", names)));
                    return;
                }
            }
            int x = (int) Math.floor(at.x());
            int z = (int) Math.floor(at.z());
            Hamlets.Place h = Hamlets.create(world, "C" + Long.toString(System.currentTimeMillis(), 36), v, x, z, v.x(), v.z(), asset, new Random());
            if (h == null) {
                String why = Hamlets.blocked(world, x, z, null);
                player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.blocked").param("why", why == null ? "terrain" : why));
                return;
            }
            player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.created").param("name", h.name()).param("x", h.x()).param("z", h.z()));
        }
    }

    /** {@code /monde commerce [--genre caravane]} : un marchand du village le plus proche part vers le lieu-dit le plus proche. */
    private static final class HamletTripCommand extends AdminCommand {
        private final OptionalArg<String> kind = withOptionalArg("genre", Hamlets.KEYS + "cmd.trip.arg", ArgTypes.STRING);

        HamletTripCommand() {
            super("commerce", Hamlets.KEYS + "cmd.trip.desc");
        }

        @Override
        protected void execute(CommandContext context, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, World world) {
            Vector3d at = player.getTransform().getPosition();
            Hamlets.Place h = Hamlets.nearest(world, at.x(), at.z(), HAMLET_RANGE);
            if (h == null || h.stage() != Hamlets.BUILT) {
                player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.none").param("range", HAMLET_RANGE));
                return;
            }
            Village v = WorldLife.nearestVillage(world, h.x(), h.z(), HamletTrips.RANGE);
            String arg = kind.get(context);
            boolean caravan = arg != null && arg.toLowerCase(Locale.ROOT).startsWith("c");
            HamletTrips.Trip t = v == null ? null : HamletTrips.start(world, h, v, caravan);
            if (t == null) {
                player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.tripFailed").param("range", HamletTrips.RANGE));
                return;
            }
            player.sendMessage(Message.translation(Hamlets.KEYS + "cmd.tripStarted").param("village", v.name()).param("hamlet", h.name()));
        }
    }
}
