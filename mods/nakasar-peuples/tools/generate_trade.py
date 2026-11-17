#!/usr/bin/env python3
"""Routes commerciales et luxes (proposition « routes commerciales », Kevin, 16 novembre 2026).

    python3 tools/generate_trade.py

Écrit :
  Common/UI/Custom/Pages/Nakasar/Peuples/TradePage_<Peuple>.ui, TradePage.ui   onglet Commerce (world/TradePage.java)
  Server/Nakasar/Requests/<Peuple>/Luxe/<Peuple>_Luxe_<luxe>.json               demandes « Luxe d'ailleurs »
  Server/Nakasar/Dialogues/Monde/Monde_Commerce.json                            caravaniers (world/TradeCaravans)
  Server/Languages/{fr-FR,en-US}/nakasar_peuples.lang                           bloc des textes du commerce

Les luxes (objets vanilla, terroir) sont ceux de world/TradeGoods.LUXURIES : changer l'un, c'est changer l'autre.
"""
import json
from pathlib import Path

from generate_board_ui import COMMON, MEMORIES, OUT, PANEL_HEIGHT, PANEL_WIDTH, THEMES, label, tab_strip

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
RES = ROOT / "src/main/resources"

LANG_BEGIN = "# ---- Routes commerciales (généré par tools/generate_trade.py, ne pas modifier à la main) ----"
LANG_END = "# ---- Fin des routes commerciales ----"

ROUTES = 3       # world/TradePage.ROUTES (trois places au palier 3 ; la Halle marchande en ajoutera)
CANDIDATES = 3   # world/TradePage.CANDIDATES
STALL = 4        # world/TradePage.STALL
CASES = 3        # niveau III : trois cases de chaque côté

PEOPLES = ("Kweebec", "Trork", "Feran", "Renonce", "Slothian")

# (objet vanilla, terroir, clé, fr, en) : world/TradeGoods.LUXURIES, dans le même ordre.
LUXURIES = [
    ("Plant_Fruit_Azure", "Kweebec", "azure", "Fruits azur", "Azure fruit"),
    ("Ingredient_Leather_Heavy", "Trork", "leather", "Cuir épais", "Heavy leather"),
    ("Ingredient_Spices", "Feran", "spices", "Épices", "Spices"),
    ("Food_Cheese", "Renonce", "cheese", "Fromage", "Cheese"),
    ("Ingredient_Crystal_Purple", "Slothian", "crystals", "Cristaux pourpres", "Purple crystals"),
    ("Ingredient_Bar_Gold", None, "gold", "Or", "Gold"),
    ("Ingredient_Bolt_Silk", None, "silk", "Soie", "Silk"),
    ("Food_Fish_Raw_Rare", None, "fish", "Poisson rare", "Rare fish"),
    ("Food_Pie_Apple", None, "pastries", "Tartes", "Pies"),
]
METAL = {"Ingredient_Bar_Gold"}  # les Kweebecs n'échangent aucun métal

FR = {}
EN = {}


def t(key, fr, en):
    if key in FR:
        raise SystemExit(f"clé en double : {key}")
    FR[key] = fr
    EN[key] = en


# ---- Onglet Commerce ----

def trade_page(theme_id):
    th = THEMES[theme_id]
    acc, band, title = th["accent"], th["band"], th["title"]
    emblem = (f'Background: (TexturePath: "{MEMORIES}{th["emblem"]}.png", Color: {acc});' if th["emblem"]
              else "Visible: false;")
    L = []
    w = L.append
    w('$C = "../../../Common.ui";')
    w("")
    w(f"// Généré par tools/generate_trade.py (thème {theme_id or 'neutre'}) : ne pas modifier à la main.")
    w("")
    w(f"@Accent = {acc};")
    w(f"@Section = LabelStyle(FontSize: 15, RenderBold: true, RenderUppercase: true, TextColor: {title}, VerticalAlignment: Center);")
    w("@Body = LabelStyle(FontSize: 14, TextColor: #c9d1d9, Wrap: true);")
    w("@Small = LabelStyle(FontSize: 13, TextColor: #96a9be, VerticalAlignment: Center);")
    w("@SmallWrap = LabelStyle(FontSize: 13, TextColor: #96a9be, Wrap: true);")
    w("@Mark = LabelStyle(FontSize: 11, RenderBold: true, TextColor: #7f93a8, HorizontalAlignment: Center, VerticalAlignment: Center);")
    w("")
    w("$C.@PageOverlay {")
    w("  LayoutMode: Middle;")
    w("")
    w("  $C.@DecoratedContainer {")
    w(f"    Anchor: (Width: {PANEL_WIDTH}, Height: {PANEL_HEIGHT});")
    w("")
    w("    #Title {")
    w("      Group {")
    w("        LayoutMode: Center;")
    w(f"        Group #TitleEmblem {{ Anchor: (Width: 26, Height: 26, Right: 8); {emblem} }}")
    w(f'        Label #PageTitle {{ Style: (...$C.@TitleStyle, FontSize: 16, TextColor: {title}); }}')
    w("      }")
    w("    }")
    w("")
    w("    #Content {")
    w("      LayoutMode: Top;")
    w("      Padding: (Full: 17, Top: 12);")
    tab_strip(w, acc, "Trade")
    # Luxes
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        Anchor: (Height: 96);")
    w("        Padding: (Horizontal: 14, Vertical: 6);")
    w(f"        Background: (Color: {band}(0.75));")
    w("        Group {")
    w("          LayoutMode: Top;")
    w("          Anchor: (Width: 300, Right: 10);")
    w(f'          {label("LuxHeader", "@Section", anchor="Height: 22")}')
    w(f'          {label("LuxLine", "@SmallWrap", anchor="Top: 4", extra=" FlexWeight: 1;")}')
    w("        }")
    for i in range(len(LUXURIES)):
        w("        Group {")
        w("          LayoutMode: Top;")
        w("          Anchor: (Width: 70, Right: 2);")
        w("          Group {")
        w("            LayoutMode: Full;")
        w("            Anchor: (Width: 56, Height: 56, Left: 7);")
        w(f'            Background: (TexturePath: "{COMMON}IngredientSlot.png", Border: 24);')
        w(f"            ItemIcon #LuxIcon{i} {{ Anchor: (Full: 7); ShowItemTooltip: true; }}")
        w("          }")
        w(f'          {label(f"LuxMark{i}", "@Mark", anchor="Height: 22, Top: 2")}')
        w("        }")
    w("      }")
    # Routes
    w(f'      {label("RoutesHeader", "@Section", anchor="Height: 24, Top: 10, Bottom: 4")}')
    w(f'      {label("NoRoute", "@Body", anchor="Height: 36")}')
    w("      Group #Routes {")
    w("        LayoutMode: Top;")
    for i in range(ROUTES):
        w(f"        Group #Route{i} {{")
        w("          LayoutMode: Left;")
        w(f"          Anchor: (Height: 100, Bottom: {4 if i < ROUTES - 1 else 0});")
        w("          Padding: (Horizontal: 12, Vertical: 4);")
        w(f"          Background: (Color: {band}(0.55));")
        w("          Group {")
        w("            LayoutMode: Top;")
        w("            FlexWeight: 1;")
        w(f'            {label(f"RouteName{i}", f"LabelStyle(FontSize: 15, RenderBold: true, TextColor: {acc}, VerticalAlignment: Center)", anchor="Height: 20")}')
        w(f'            {label(f"RouteState{i}", "@Small", anchor="Height: 18")}')
        for side in ("Out", "In"):
            w("            Group {")
            w("              LayoutMode: Left;")
            w("              Anchor: (Height: 26, Top: 4);")
            w(f'              {label(f"Route{side}Label{i}", "@Small", anchor="Width: 90")}')
            for j in range(CASES):
                w(f'              $C.@SmallSecondaryTextButton #Route{side}{i}_{j} {{ @Text = ""; @Anchor = Anchor(Width: 190, Height: 26, Right: 6); }}')
            w("            }")
        w("          }")
        w("          Group {")
        w("            LayoutMode: Top;")
        w("            Anchor: (Width: 190, Left: 10);")
        w(f'            $C.@SmallSecondaryTextButton #RouteRaise{i} {{ @Text = ""; @Anchor = Anchor(Height: 28, Bottom: 3); }}')
        w(f'            $C.@SmallSecondaryTextButton #RoutePay{i} {{ @Text = ""; @Anchor = Anchor(Height: 28, Bottom: 3); }}')
        w(f'            $C.@SmallSecondaryTextButton #RouteClose{i} {{ @Text = ""; @Anchor = Anchor(Height: 28); }}')
        w("          }")
        w("        }")
    w("      }")
    w("      Group { FlexWeight: 1; }")
    # Partenaires et étal
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        Anchor: (Height: 150, Top: 8);")
    w("        Group {")
    w("          LayoutMode: Top;")
    w("          FlexWeight: 1;")
    w("          Anchor: (Right: 12);")
    w("          Padding: (Horizontal: 12, Vertical: 6);")
    w(f"          Background: (Color: {band}(0.75));")
    w(f'          {label("CandHeader", "@Section", anchor="Height: 22")}')
    w(f'          {label("NoCand", "@SmallWrap", anchor="Height: 36")}')
    for i in range(CANDIDATES):
        w(f"          Group #Cand{i} {{")
        w("            LayoutMode: Left;")
        w("            Anchor: (Height: 32, Top: 4);")
        w(f'            {label(f"CandName{i}", "@Small", extra=" FlexWeight: 1;")}')
        w(f'            $C.@SmallSecondaryTextButton #CandOpen{i} {{ @Text = ""; @Anchor = Anchor(Width: 200, Height: 30); }}')
        w("          }")
    w("        }")
    w("        Group {")
    w("          LayoutMode: Top;")
    w("          Anchor: (Width: 420);")
    w("          Padding: (Horizontal: 12, Vertical: 6);")
    w(f"          Background: (Color: {band}(0.75));")
    w(f'          {label("StallHeader", "@Section", anchor="Height: 22")}')
    w(f'          {label("NoStall", "@SmallWrap", anchor="Height: 36")}')
    w("          Group {")
    w("            LayoutMode: Left;")
    w("            Anchor: (Height: 96, Top: 4);")
    for i in range(STALL):
        w(f"            Group #Stall{i} {{")
        w("              LayoutMode: Top;")
        w("              Anchor: (Width: 96, Right: 2);")
        w("              Group {")
        w("                LayoutMode: Full;")
        w("                Anchor: (Width: 56, Height: 56, Left: 20);")
        w(f'                Background: (TexturePath: "{COMMON}IngredientSlot.png", Border: 24);')
        w(f"                ItemIcon #StallIcon{i} {{ Anchor: (Full: 7); ShowItemTooltip: true; }}")
        w("              }")
        w(f'              $C.@SmallSecondaryTextButton #StallBuy{i} {{ @Text = ""; @Anchor = Anchor(Height: 28, Top: 4); }}')
        w("            }")
    w("          }")
    w("        }")
    w("      }")
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        Anchor: (Height: 48, Top: 8);")
    w(f'        {label("Rule", "@SmallWrap", extra=" FlexWeight: 1;")}')
    w("      }")
    w("    }")
    w("  }")
    w("}")
    w("")
    w("$C.@BackButton {}")
    return "\n".join(L).replace("Style: LabelStyle(", "Style: (") + "\n"


# ---- Demandes « Luxe d'ailleurs » ----

def requests():
    for people in PEOPLES:
        folder = RES / f"Server/Nakasar/Requests/{people}/Luxe"
        folder.mkdir(parents=True, exist_ok=True)
        for old in folder.glob("*.json"):
            old.unlink()
        for item, terroir, key, fr, en in LUXURIES:
            if terroir == people or (people == "Kweebec" and item in METAL):
                continue
            rid = f"{people}_Luxe_{key}"
            data = {
                "$Comment": "Demande « Luxe d'ailleurs » (routes commerciales), générée par tools/generate_trade.py : "
                            "tirée seulement si le village n'a pas ce luxe (world/TradeAccess.wanted).",
                "People": people,
                "Type": "Gather",
                "MinTier": 2,
                "MaxTier": 3,
                "Weight": 1,
                "TitleKey": f"nakasar_peuples.request.{rid}.title",
                "TaskKey": f"nakasar_peuples.request.{rid}.task",
                "ItemId": item,
                "Quantity": 4,
                "Essor": 15,
                "Favors": 2,
                "Reputation": 10,
            }
            (folder / f"{rid}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            t(f"request.{rid}.title", f"Luxe : {fr.lower()}", f"Luxury: {en.lower()}")
            t(f"request.{rid}.task",
              "Dépose {count}/{needed} {item} au dépôt du village ({distance} blocs, {direction}) : le village en vit trois jours de plus.",
              "Drop {count}/{needed} {item} in the village deposit ({distance} blocks, {direction}): the village enjoys it for three more days.")


# ---- Dialogue des caravaniers ----

def dialogue():
    did = "Monde_Commerce"
    k = f"nakasar_peuples.dialogue.{did}."
    data = {
        "$Comment": "Caravanier d'une route commerciale (world/TradeCaravans). Généré par tools/generate_trade.py ; effets WorldAction (world/WorldDialogueTypes).",
        "NpcNameKey": k + "npc",
        "RoleKey": k + "role",
        "Entries": [{"Node": "Accueil"}],
        "Nodes": [
            {"Id": "Accueil", "TextKey": k + "accueil", "Responses": [
                {"TextKey": k + "troc", "Effects": [{"Type": "WorldAction", "Action": "TradeShop"}]},
                {"TextKey": k + "cargaison", "Effects": [{"Type": "WorldAction", "Action": "TradeWhere"}], "Next": "Accueil"},
                {"TextKey": "nakasar_peuples.dialogue.Monde.rumeur", "Effects": [{"Type": "WorldAction", "Action": "Rumour"}], "Next": "Rumeur"},
                {"TextKey": "nakasar_peuples.dialogue.Monde.aurevoir"},
            ]},
            {"Id": "Rumeur", "TextKey": "nakasar_peuples.dialogue.Monde.rumeurTexte", "Responses": [
                {"TextKey": "nakasar_peuples.dialogue.Monde.rumeurAutre", "Effects": [{"Type": "WorldAction", "Action": "Rumour"}], "Next": "Rumeur"},
                {"TextKey": "nakasar_peuples.dialogue.Monde.retour", "Next": "Accueil"},
                {"TextKey": "nakasar_peuples.dialogue.Monde.aurevoir"},
            ]},
        ],
    }
    path = RES / f"Server/Nakasar/Dialogues/Monde/{did}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = f"dialogue.{did}."
    t(d + "npc", "Caravanier", "Caravan trader")
    t(d + "role", "Route commerciale", "Trade route")
    t(d + "accueil", "La route est longue et les bêtes sont chargées. Tu veux voir ce que je garde pour le troc ?",
      "The road is long and the pack beasts are loaded. Want to see what I keep for barter?")
    t(d + "troc", "Montre-moi ton troc.", "Show me your wares.")
    t(d + "cargaison", "Que portes-tu, et pour qui ?", "What are you carrying, and for whom?")


# ---- Textes du Java (clés nakasar_peuples.world.trade.<clé>) ----

TEXTS = [
    # Annonces
    ("opened", "Une route commerciale s'ouvre entre {a} et {b}.", "A trade route opens between {a} and {b}."),
    ("raised", "La route entre {a} et {b} passe au niveau {level}.", "The route between {a} and {b} reaches level {level}."),
    ("downgraded", "Trois caravanes perdues : la route entre {a} et {b} retombe au niveau {level}.",
     "Three caravans lost: the route between {a} and {b} drops back to level {level}."),
    ("closed", "La route commerciale entre {a} et {b} est fermée.", "The trade route between {a} and {b} is closed."),
    ("broken", "Quatorze jours de brouille : la route entre {a} et {b} est rompue.",
     "Fourteen days of quarrel: the route between {a} and {b} is broken."),
    ("suspended", "La route entre {a} et {b} est suspendue (rivalité ou embargo) ; elle sera rompue dans {days} jours.",
     "The route between {a} and {b} is suspended (rivalry or embargo); it breaks in {days} days."),
    ("empty", "La caravane vers {to} ne part pas : le dépôt n'a rien de ce qu'elle devait porter.",
     "The caravan to {to} does not leave: the deposit holds none of its goods."),
    ("arrived", "La caravane de {from} est arrivée : {goods}.", "The caravan from {from} has arrived: {goods}."),
    ("ambushedAway", "La caravane de {from} a été attaquée en chemin : un tiers de sa cargaison est perdu.",
     "The caravan from {from} was attacked on the way: a third of its cargo is lost."),
    ("lost", "La caravane entre {from} et {to} a été détruite ; sa cargaison gît sur la route.",
     "The caravan between {from} and {to} was destroyed; its cargo lies on the road."),
    ("goods", "{count} x {item}", "{count} x {item}"),
    ("goodsMore", "{a}, {b}", "{a}, {b}"),
    ("goodsNone", "rien", "nothing"),
    ("shopRank", "Je ne troque qu'avec les amis de {village} (Toléré).", "I only barter with friends of {village} (Tolerated)."),
    ("where", "Je viens de {from} et je porte {goods} à {to}.", "I come from {from} and carry {goods} to {to}."),
    ("rumour", "Une caravane de {from} est en route vers {to}, bien chargée.", "A caravan from {from} is on the road to {to}, well loaded."),
    ("board.luxuries", "Luxes : il en faut {need} pour ce chantier, il en manque {missing} (onglet Commerce).",
     "Luxuries: this building site needs {need}, {missing} missing (Trade tab)."),
    # Refus
    ("why.exists", "Une route relie déjà ces deux lieux.", "A route already links these two places."),
    ("why.slots", "{village} n'a plus de place de route ({slots}).", "{village} has no route slot left ({slots})."),
    ("why.partner", "{village} ne peut pas commercer avec ce village (trop loin, rival ou embargo).",
     "{village} cannot trade with this village (too far, rival or embargo)."),
    ("why.rankAmi", "Il faut être Ami de {village}.", "You must be a Friend of {village}."),
    ("why.rankTolere", "Il faut être Toléré de {village}.", "You must be Tolerated by {village}."),
    ("why.offering", "Il faut {count} faveurs du village.", "It takes {count} favours of the village."),
    ("why.maxLevel", "La route est déjà au niveau III.", "The route is already level III."),
    ("why.suspended", "La route est suspendue.", "The route is suspended."),
    ("why.beacons", "Le niveau II demande une route balisée de bout en bout.", "Level II needs a route marked with beacons end to end."),
    ("why.arrivals", "Il faut {need} caravanes arrivées ({count} pour l'instant).", "It takes {need} caravans arrived ({count} so far)."),
    ("why.tier2", "Le niveau II demande le palier 2 des deux côtés.", "Level II needs tier 2 at both ends."),
    ("why.tier3", "Le niveau III demande le palier 3 d'un des deux bouts.", "Level III needs tier 3 at one end."),
    ("why.inn", "Le niveau III demande une auberge ouverte sur une liaison de plus de {length} blocs.",
     "Level III needs an open inn on a link longer than {length} blocks."),
    ("why.slot", "Cette case n'est pas ouverte à ce niveau.", "This slot is not open at this level."),
    ("why.metal", "Les Kweebecs n'échangent aucun métal.", "Kweebecs trade no metal."),
    ("why.twice", "Cette marchandise est déjà dans une autre case.", "These goods are already in another slot."),
    # Onglet
    ("page.tab", "Commerce", "Trade"),
    ("page.title", "{village} : commerce", "{village}: trade"),
    ("page.lux.header", "Luxes : {count} sur {total}", "Luxuries: {count} of {total}"),
    ("page.lux.next", "le palier {tier} en demande {need}", "tier {tier} needs {need}"),
    ("page.lux.settler", "un colon en demande {need}", "a settler needs {need}"),
    ("page.lux.line", "{need} ; essor +{bonus} %. Un luxe compte 7 jours après sa livraison, celui du terroir dès le palier 2.",
     "{need}; growth +{bonus}%. A luxury counts for 7 days after delivery, the home terroir one from tier 2."),
    ("page.lux.terroir", "terroir", "terroir"),
    ("page.lux.days", "{days} j", "{days} d"),
    ("page.lux.missing", "manque", "missing"),
    ("page.lux.never", "interdit", "forbidden"),
    ("page.routes", "Routes : {count} sur {slots}", "Routes: {count} of {slots}"),
    ("page.noRoute", "Aucune route. Ouvre-en une vers un partenaire ci-dessous.", "No route. Open one to a partner below."),
    ("page.noRouteTier", "Un village commerce à partir du palier 1.", "A village trades from tier 1."),
    ("page.route.name", "{partner} · niveau {level}", "{partner} · level {level}"),
    ("page.level.1", "I", "I"),
    ("page.level.2", "II", "II"),
    ("page.level.3", "III", "III"),
    ("page.route.state", "Caravane dans {next} j · {arrivals} arrivées · {lost} pertes · crédit {credit} (manque {deficit})",
     "Caravan in {next} d · {arrivals} arrived · {lost} lost · credit {credit} (short {deficit})"),
    ("page.route.suspended", "Suspendue : rompue dans {days} j si rien ne change", "Suspended: breaks in {days} d unless things change"),
    ("page.route.auto", "{state} · choisie par le conseil", "{state} · chosen by the council"),
    ("page.route.out", "Exporte", "Exports"),
    ("page.route.in", "Importe", "Imports"),
    ("page.case.empty", "— vide —", "— empty —"),
    ("page.button.raise", "Niveau suivant ({count} faveurs)", "Next level ({count} favours)"),
    ("page.button.pay", "Verser 1 faveur (+{credit})", "Pay 1 favour (+{credit})"),
    ("page.button.close", "Fermer la route", "Close the route"),
    ("page.button.open", "Ouvrir ({count} faveurs)", "Open ({count} favours)"),
    ("page.button.buy", "Acheter {count} (1 faveur)", "Buy {count} (1 favour)"),
    ("page.candidates", "Partenaires possibles", "Possible partners"),
    ("page.noCandidate", "Aucun village ni lieu-dit à moins de {max} blocs avec qui commercer.",
     "No village or hamlet within {max} blocks to trade with."),
    ("page.candidate", "{partner} · {distance} blocs, {dir}", "{partner} · {distance} blocks, {dir}"),
    ("page.stall", "Étal des importations", "Import stall"),
    ("page.stallEmpty", "Rien d'importé au dépôt pour l'instant.", "Nothing imported in the deposit yet."),
    ("page.stallFar", "Le dépôt est trop loin pour que l'étal ouvre.", "The deposit is too far for the stall to open."),
    ("page.rule", "Ouvrir une route : Ami du village, Toléré du partenaire, {offering} faveurs. Les exportations doivent peser autant que les importations (commune 1, fine 2, luxe 3) ; une faveur versée donne {credit} de crédit.",
     "Opening a route: Friend of the village, Tolerated by the partner, {offering} favours. Exports must weigh as much as imports (common 1, fine 2, luxury 3); a favour paid gives {credit} credit."),
    ("page.raised", "La route monte d'un niveau.", "The route goes up one level."),
    ("page.paid", "Crédit de la route : +{credit}.", "Route credit: +{credit}."),
    ("page.bought", "Tu achètes {count} {item}.", "You buy {count} {item}."),
    ("page.nothing", "{village} n'a rien à exporter pour l'instant.", "{village} has nothing to export yet."),
    # Commande
    ("cmd.desc", "Routes commerciales du village le plus proche (liste, ouvrir, niveau, depart, acces, fermer)",
     "Trade routes of the nearest village (liste, ouvrir, niveau, depart, acces, fermer)"),
    ("cmd.what.arg", "liste, ouvrir, niveau, depart, acces ou fermer", "liste, ouvrir, niveau, depart, acces or fermer"),
    ("cmd.header", "{village} : {count}/{slots} routes, {luxuries} luxes, essor +{bonus} %", "{village}: {count}/{slots} routes, {luxuries} luxuries, growth +{bonus}%"),
    ("cmd.line", "{a} ↔ {b} : niveau {level}, {arrivals} arrivées, départ jour {next} ({auto}) ; {a} → {exportsA} ; {b} → {exportsB}",
     "{a} ↔ {b}: level {level}, {arrivals} arrived, leaves day {next} ({auto}); {a} → {exportsA}; {b} → {exportsB}"),
    ("cmd.caravan", "Caravane {from} → {to} : {at}/{length} blocs, {walkers} porteurs, {goods}",
     "Caravan {from} → {to}: {at}/{length} blocks, {walkers} porters, {goods}"),
    ("cmd.access", "{village} : accès aux neuf luxes pour 7 jours ({count} comptés, essor +{bonus} %).",
     "{village}: access to all nine luxuries for 7 days ({count} counted, growth +{bonus}%)."),
    ("cmd.noRoute", "Aucune route de ce village ne correspond.", "No route of this village matches."),
]


def texts():
    for key, fr, en in TEXTS:
        t("world.trade." + key, fr, en)
    t("chantier.blocker.LUXURY", "Le chantier attend des luxes : voir l'onglet Commerce du panneau.",
      "The building site waits for luxuries: see the Trade tab of the board.")


def write_langs():
    for locale, table in (("fr-FR", FR), ("en-US", EN)):
        path = RES / f"Server/Languages/{locale}/nakasar_peuples.lang"
        text = path.read_text(encoding="utf-8")
        block = "\n".join([LANG_BEGIN] + [f"{k} = {v}" for k, v in table.items()] + [LANG_END]) + "\n"
        if LANG_BEGIN in text:
            before, rest = text.split(LANG_BEGIN, 1)
            after = rest.split(LANG_END, 1)[1].lstrip("\n")
            outside = before + after
            text = before + block + after
        else:
            outside = text
            text = block + text
        existing = {line.split("=", 1)[0].strip() for line in outside.splitlines() if "=" in line and not line.startswith("#")}
        dup = sorted(k for k in table if k in existing)
        if dup:
            raise SystemExit(f"clés déjà présentes dans {locale} (hors bloc du commerce) : {dup[:10]}")
        path.write_text(text, encoding="utf-8")
        print(f"{path.relative_to(ROOT)} : {len(table)} clés du commerce")


def main():
    for theme_id in THEMES:
        name = f"TradePage_{theme_id}.ui" if theme_id else "TradePage.ui"
        (OUT / name).write_text(trade_page(theme_id), encoding="utf-8")
        print("écrit", name)
    requests()
    dialogue()
    texts()
    write_langs()


if __name__ == "__main__":
    main()
