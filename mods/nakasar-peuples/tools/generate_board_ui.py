#!/usr/bin/env python3
"""Tableau du village à boutons, une mise en page par peuple (maquettes
/mnt/project-files/peuples/maquettes/tableau-par-peuple/) : cadre vanilla DecoratedContainer, bandeau du peuple
(emblème vanilla de la page des Souvenirs teinté à la couleur du peuple, devise, rang), cartes des trois demandes
(icône d'objet vanilla du type, récompenses, jauge d'avancement), essor et chantier (vraies jauges, matériaux en
icônes d'objets), dépôt en icônes, alerte de raid.

    python3 tools/generate_board_ui.py

Sortie, dans src/main/resources/Common/UI/Custom/Pages/Nakasar/Peuples/ :
  BoardPage_<Peuple>.ui   une page par peuple (BoardPage.java choisit celle de People.id()),
  BoardPage.ui            la même page aux couleurs neutres, pour un peuple sans thème,
  Board/Bar_<Peuple>.png  remplissage des jauges à la couleur du peuple (dégradé uni, pas de texture inventée).

Les ids d'éléments sont ceux que remplit dev.nakasar.hytale.peuples.request.BoardPage : changer un id ici, c'est le
changer là-bas. Le thème d'un peuple (couleurs, emblème) vit seulement dans THEMES ; sa devise est la clé de langue
nakasar_peuples.boardPage.motto.<Peuple>.
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src/main/resources/Common/UI/Custom/Pages/Nakasar/Peuples"

# Emblèmes : icônes vanilla des catégories de la page des Souvenirs (Common/UI/Custom/Pages/Memories/categories/),
# blanches, teintées par la couleur du PatchStyle. Pas d'icône vanilla pour les Slothians : celle des Voidtaken.
MEMORIES = "../../Memories/categories/"
COMMON = "../../../Common/"

THEMES = {
    # accent : jauges, bandeau, nom du peuple ; band : fond du bandeau ; title : titre de la fenêtre.
    "Kweebec": dict(emblem="Kweebec", accent="#9ed36a", band="#2d4a26", title="#d9c48a"),
    "Trork": dict(emblem="Trork", accent="#e0773e", band="#4a2216", title="#e8b48a"),
    "Feran": dict(emblem="Feran", accent="#e6b552", band="#4a3a17", title="#ecd29a"),
    "Renonce": dict(emblem="Outlander", accent="#8fd0ea", band="#173246", title="#bfe2ee"),
    "Slothian": dict(emblem="Voidtaken", accent="#b99be8", band="#2b2043", title="#d6c6f0"),
    None: dict(emblem=None, accent="#7a9cc6", band="#1d2c40", title="#b4c8c9"),
}

CHANTIER_BAR = "#e8a93b"   # jauge des travaux en cours (or vanilla @ColorGoldHighlight)
REQUESTS = 3               # Requests.SLOTS
MATERIALS = 5              # matériaux d'un chantier (4 au plus dans les plans actuels)
BUILDINGS = 4              # bâtiments listés d'un chantier en cours (les autres : « et N autres »)
DEPOSIT = 9                # sortes d'objets montrées du dépôt

WIDTH, HEIGHT = 1060, 840   # PANEL_WIDTH x PANEL_HEIGHT : les quatre onglets du panneau ont la même taille
LEFT_WIDTH = 548
PANEL_WIDTH, PANEL_HEIGHT = WIDTH, HEIGHT

# Onglets du panneau du village (request/BoardTabs.java), dans l'ordre de la barre. Maquette Claude Design
# « Panneau du village — refonte » (16 novembre 2026) : les onglets en haut, toujours visibles.
TABS = ("Board", "Plots", "Annexes", "World", "Domain")
TAB_WIDTH = 150


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def bar_png(color, path):
    """Remplissage de jauge : la couleur, un liseré clair en haut et une ombre en bas (lu comme la jauge vanilla)."""
    r, g, b = rgb(color)
    w, h = 8, 24
    im = Image.new("RGBA", (w, h))
    for y in range(h):
        t = y / (h - 1)
        k = 1.25 if y < 3 else (0.72 if y > h - 4 else 1.05 - 0.25 * t)
        c = tuple(max(0, min(255, int(v * k))) for v in (r, g, b))
        for x in range(w):
            im.putpixel((x, y), c + (255,))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def label(id_, style, text='""', anchor=None, extra=""):
    a = f"Anchor: ({anchor}); " if anchor else ""
    i = f" #{id_}" if id_ else ""
    return f"Label{i} {{ {a}Style: {style}; Text: {text};{extra} }}"


def tab_strip(w, acc, active, indent="      "):
    """Barre des onglets en haut du contenu : l'onglet ouvert en aplat à la couleur du peuple (#Tab<X>On), les autres en
    boutons (#Tab<X>Button), l'heure du jeu à droite (#Clock), un filet de la couleur du peuple dessous. Chaque onglet
    porte les deux formes (#Tab<X>Off enveloppe le bouton) (seule la visibilité diffère d'une page à l'autre) : BoardTabs remplit les mêmes ids partout."""
    i = indent
    w(f"{i}Group #Tabs {{")
    w(f"{i}  LayoutMode: Left;")
    w(f"{i}  Anchor: (Height: 38);")
    for tab in TABS:
        on = tab == active
        w(f"{i}  Group #Tab{tab} {{")
        w(f"{i}    LayoutMode: Full;")
        w(f"{i}    Anchor: (Width: {TAB_WIDTH}, Height: 38, Right: 6);")
        w(f"{i}    Group #Tab{tab}Off {{")
        w(f"{i}      LayoutMode: Full;")
        w(f"{i}      Anchor: (Full: 0);")
        w(f"{i}      Visible: {'false' if on else 'true'};")
        w(f'{i}      $C.@SecondaryTextButton #Tab{tab}Button {{ @Text = ""; @Anchor = Anchor(Full: 0); }}')
        w(f"{i}    }}")
        w(f"{i}    Group #Tab{tab}On {{")
        w(f"{i}      Anchor: (Full: 0);")
        w(f"{i}      Background: (Color: {acc});")
        w(f"{i}      Visible: {'true' if on else 'false'};")
        w(f'{i}      {label(f"Tab{tab}Label", "LabelStyle(FontSize: 14, RenderBold: true, RenderUppercase: true, TextColor: #10180e, HorizontalAlignment: Center, VerticalAlignment: Center)", anchor="Full: 0")}')
        w(f"{i}    }}")
        w(f"{i}  }}")
    w(f"{i}  Group {{ FlexWeight: 1; }}")
    w(f'{i}  {label("Clock", "LabelStyle(FontSize: 14, RenderBold: true, TextColor: #96a9be, HorizontalAlignment: End, VerticalAlignment: Center)", anchor="Width: 200")}')
    w(f"{i}}}")
    w(f"{i}Group {{ Anchor: (Height: 2, Bottom: 12); Background: (Color: {acc}); }}")


def page(theme_id):
    t = THEMES[theme_id]
    acc, band, title = t["accent"], t["band"], t["title"]
    bar = f"Board/Bar_{theme_id}.png" if theme_id else "Board/Bar_Default.png"
    emblem = (f'Background: (TexturePath: "{MEMORIES}{t["emblem"]}.png", Color: {acc});' if t["emblem"]
              else "Visible: false;")
    L = []
    w = L.append
    w('$C = "../../../Common.ui";')
    w("")
    w(f"// Généré par tools/generate_board_ui.py (thème {theme_id or 'neutre'}) : ne pas modifier à la main.")
    w("")
    w(f"@Accent = {acc};")
    w("@Caption = LabelStyle(FontSize: 12, RenderBold: true, RenderUppercase: true, TextColor: #7f93a8, VerticalAlignment: Center);")
    w("@Section = LabelStyle(FontSize: 15, RenderBold: true, RenderUppercase: true, TextColor: #96a9be, VerticalAlignment: Center);")
    w("@Body = LabelStyle(FontSize: 14, TextColor: #c9d1d9, VerticalAlignment: Center);")
    w("@Small = LabelStyle(FontSize: 13, TextColor: #96a9be, VerticalAlignment: Center);")
    w("@SmallWrap = LabelStyle(FontSize: 13, TextColor: #96a9be, Wrap: true);")
    w("@Count = LabelStyle(FontSize: 14, RenderBold: true, TextColor: #e8c46a, HorizontalAlignment: Center, VerticalAlignment: Center);")
    w("@SlotCount = LabelStyle(FontSize: 12, RenderBold: true, TextColor: #ffffff, HorizontalAlignment: End, VerticalAlignment: End);")
    w("@RequestTitle = LabelStyle(FontSize: 18, RenderBold: true, TextColor: #e8c46a, VerticalAlignment: Center);")
    w("@TypeStyle = LabelStyle(FontSize: 11, RenderBold: true, RenderUppercase: true, TextColor: #c9d1d9, HorizontalAlignment: Center, VerticalAlignment: Center);")
    w("@PillStyle = LabelStyle(FontSize: 12, RenderBold: true, TextColor: @Accent, HorizontalAlignment: Center, VerticalAlignment: Center);")
    w("@RepPillStyle = LabelStyle(FontSize: 12, RenderBold: true, TextColor: #a9c4e6, HorizontalAlignment: Center, VerticalAlignment: Center);")
    w("")
    w("@Card = Group {")
    w("  Background: (Color: #0c151e(0.55));")
    w("};")
    w("")
    w("@Pill = Group {")
    w("  LayoutMode: Left;")
    w("  Anchor: (Height: 20, Right: 6);")
    w("  Padding: (Horizontal: 8);")
    w("  Background: (Color: #1a2836);")
    w("};")
    w("")
    w("@Bar = ProgressBar {")
    w(f'  Background: "{COMMON}ProgressBar.png";')
    w(f'  BarTexturePath: "{bar}";')
    w("  Value: 0;")
    w("};")
    w("")
    w("$C.@PageOverlay {")
    w("  LayoutMode: Middle;")
    w("")
    w("  $C.@DecoratedContainer {")
    w(f"    Anchor: (Width: {WIDTH}, Height: {HEIGHT});")
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
    w("")
    tab_strip(w, acc, "Board")
    # ---- Bandeau du peuple
    w("      Group #Band {")
    w("        LayoutMode: Full;")
    w("        Anchor: (Height: 104);")
    w(f"        Background: (Color: {band}(0.75));")
    w("")
    w(f"        Group {{ Anchor: (Left: 0, Top: 0, Bottom: 0, Width: 4); Background: (Color: {acc}); }}")
    w(f"        Group {{ Anchor: (Left: 0, Right: 0, Bottom: 0, Height: 1); Background: (Color: {acc}(0.35)); }}")
    if t["emblem"]:
        w("        // Filigrane : l'emblème en grand, très pâle, derrière le rang.")
        w(f'        Group #Watermark {{ Anchor: (Right: 330, Top: -23, Width: 150, Height: 150); '
          f'Background: (TexturePath: "{MEMORIES}{t["emblem"]}.png", Color: {acc}(0.13)); }}')
    w("")
    w("        Group {")
    w("          LayoutMode: Left;")
    w("          Anchor: (Full: 0);")
    w("          Padding: (Left: 18, Right: 18, Vertical: 10);")
    w("")
    w("          Group #EmblemFrame {")
    w("            LayoutMode: Full;")
    w("            Anchor: (Width: 84, Height: 84, Right: 20);")
    w(f'            Background: (TexturePath: "{COMMON}ContainerPanelPatch.png", Border: 4);')
    w(f"            Group #Emblem {{ Anchor: (Full: 0); {emblem} }}")
    w("          }")
    w("")
    w("          Group {")
    w("            LayoutMode: Top;")
    w("            FlexWeight: 1;")
    w(f'            {label("PeopleTier", f"LabelStyle(FontSize: 19, FontName: \"Secondary\", RenderBold: true, RenderUppercase: true, TextColor: {acc}, VerticalAlignment: Center)", anchor="Height: 30, Top: 2")}')
    w(f'            {label("Motto", "LabelStyle(FontSize: 15, TextColor: #c9b98f, VerticalAlignment: Center)", anchor="Height: 24")}')
    w("            Group {")
    w("              LayoutMode: Left;")
    w("              Anchor: (Height: 20, Top: 6);")
    w(f'              @Pill #VillagersPill {{ {label("Villagers", "@RepPillStyle")} }}')
    w(f'              @Pill #ClimatePill {{ Visible: false; {label("Climate", "@PillStyle")} }}')
    w("            }")
    w("          }")
    w("")
    w("          Group #RankBlock {")
    w("            LayoutMode: Top;")
    w("            Anchor: (Width: 290);")
    w(f'            {label("RankCaption", "@Caption", anchor="Height: 16")}')
    w("            Group {")
    w("              LayoutMode: Left;")
    w("              Anchor: (Height: 28);")
    w(f'              {label("RankName", "LabelStyle(FontSize: 22, FontName: \"Secondary\", RenderBold: true, RenderUppercase: true, TextColor: #e8c46a, VerticalAlignment: Center)", extra=" FlexWeight: 1;")}')
    w(f'              {label("RankNext", "LabelStyle(FontSize: 13, RenderBold: true, TextColor: #96a9be, HorizontalAlignment: End, VerticalAlignment: Center)")}')
    w("            }")
    w("            @Bar #RankBar { Anchor: (Height: 12, Top: 4, Bottom: 4); }")
    w(f'            {label("RankDetail", "@Small", anchor="Height: 18")}')
    w("          }")
    w("        }")
    w("      }")
    w("")
    # ---- Colonnes
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        FlexWeight: 1;")
    w("        Anchor: (Top: 14);")
    w("")
    w("        Group #RequestsColumn {")
    w("          LayoutMode: Top;")
    w(f"          Anchor: (Width: {LEFT_WIDTH}, Right: 22);")
    w("          Group {")
    w("            LayoutMode: Left;")
    w("            Anchor: (Height: 24, Bottom: 6);")
    w(f'            {label("RequestsHeader", "@Section", extra=" FlexWeight: 1;")}')
    w(f'            {label("RequestsRenew", "LabelStyle(FontSize: 13, TextColor: #5a6a7a, HorizontalAlignment: End, VerticalAlignment: Center)")}')
    w("          }")
    for i in range(REQUESTS):
        w("")
        w(f"          @Card #Request{i} {{")
        w("            LayoutMode: Full;")
        w("            Anchor: (Height: 108, Bottom: 10);")
        w(f"            Group #Stripe{i} {{ Anchor: (Left: 0, Top: 0, Bottom: 0, Width: 3); Background: (Color: {acc}); }}")
        w(f"            Group #StripeOff{i} {{ Anchor: (Left: 0, Top: 0, Bottom: 0, Width: 3); Background: (Color: #3a4656); Visible: false; }}")
        w("")
        w(f"            Group #TypeSlot{i} {{")
        w("              LayoutMode: Full;")
        w("              Anchor: (Left: 14, Top: 14, Width: 56, Height: 56);")
        w(f'              Background: (TexturePath: "{COMMON}IngredientSlot.png", Border: 24);')
        w(f"              ItemIcon #TypeIcon{i} {{ Anchor: (Full: 6); }}")
        # Quantité demandée en pastille de case (Kevin : « 10 × objet » dans le titre le rendait illisible).
        w(f'              {label(f"Qty{i}", "LabelStyle(FontSize: 15, RenderBold: true, TextColor: #ffffff, HorizontalAlignment: End, VerticalAlignment: End)", anchor="Right: 5, Bottom: 3")}')
        w(f"              Group #Lock{i} {{")
        w("                LayoutMode: Middle;")
        w("                Anchor: (Full: 0);")
        w("                Background: (Color: #000000(0.5));")
        w("                Visible: false;")
        w(f'                Group {{ Anchor: (Width: 27, Height: 27); Background: "{COMMON}RunicCheckLocked.png"; }}')
        w("              }")
        w("            }")
        w("")
        w(f"            Group #Check{i} {{ Anchor: (Right: 12, Top: 12, Width: 27, Height: 27); "
          f'Background: "{COMMON}RunicCheckReady.png"; Visible: false; }}')
        w("")
        w("            Group {")
        w("              LayoutMode: Top;")
        w("              Anchor: (Left: 84, Right: 14, Top: 12, Bottom: 10);")
        w("              Group {")
        w("                LayoutMode: Left;")
        w("                Anchor: (Height: 24);")
        w(f"                @Pill #TypePill{i} {{ Anchor: (Height: 20, Right: 8, Top: 2); {label(f'Type{i}', '@TypeStyle')} }}")
        w(f'                {label(f"Title{i}", "@RequestTitle", extra=" FlexWeight: 1;")}')
        w("              }")
        w("")
        w(f"              // Disponible : la récompense.")
        w(f"              Group #RewardBox{i} {{")
        w("                LayoutMode: Top;")
        w("                Anchor: (Top: 6);")
        w(f'                {label(f"RewardCaption{i}", "@Caption", anchor="Height: 16")}')
        w("                Group {")
        w("                  LayoutMode: Left;")
        w("                  Anchor: (Height: 30, Top: 4);")
        w(f"                  @Pill {{ Anchor: (Height: 20, Right: 6, Top: 5); {label(f'Essor{i}', '@PillStyle')} }}")
        w(f"                  @Pill {{ Anchor: (Height: 20, Right: 6, Top: 5); {label(f'Rep{i}', '@RepPillStyle')} }}")
        w(f"                  ItemIcon #Favor{i} {{ Anchor: (Width: 30, Height: 30, Right: 4); ShowItemTooltip: true; }}")
        w(f'                  {label(f"Favors{i}", "LabelStyle(FontSize: 15, RenderBold: true, TextColor: #d3d6db, VerticalAlignment: Center)", extra=" FlexWeight: 1;")}')
        w("                }")
        w("              }")
        w("")
        w(f"              // Prise : la tâche et son avancement.")
        w(f"              Group #TaskBox{i} {{")
        w("                LayoutMode: Top;")
        w("                Anchor: (Top: 4, Right: 150);")
        w("                Visible: false;")
        w(f'                {label(f"Task{i}", "LabelStyle(FontSize: 14, TextColor: #c9d1d9, Wrap: true)", anchor="Height: 36")}')
        w("                Group {")
        w("                  LayoutMode: Left;")
        w("                  Anchor: (Height: 16, Top: 2);")
        w(f"                  @Bar #Progress{i} {{ Anchor: (Width: 240, Height: 10, Top: 3); }}")
        w(f'                  {label(f"ProgressText{i}", "LabelStyle(FontSize: 13, RenderBold: true, TextColor: #96a9be, VerticalAlignment: Center)", anchor="Left: 10")}')
        w("                }")
        w("              }")
        w("")
        w(f"              // Fermée ou remplie : une ligne.")
        w(f'              {label(f"Detail{i}", "LabelStyle(FontSize: 14, TextColor: #6f7d8c, Wrap: true)", anchor="Top: 8, Right: 150", extra=" Visible: false;")}')
        w("            }")
        w("")
        w(f'            $C.@SmallSecondaryTextButton #Action{i} {{ @Text = ""; @Anchor = Anchor(Right: 14, Bottom: 14, Width: 136); }}')
        w("          }")
    w("")
    w("          Group { FlexWeight: 1; }")
    w(f'          {label("Perks", "@SmallWrap", anchor="Bottom: 2")}')
    w("        }")
    w("")
    # ---- Colonne droite
    w("        Group #StateColumn {")
    w("          LayoutMode: Top;")
    w("          FlexWeight: 1;")
    w(f'          {label("EssorHeader", "@Section", anchor="Height: 24, Bottom: 6")}')
    w("")
    # Colonne qui défile (LayoutMode TopScrolling, comme les listes vanilla CommandListPage/ItemRepairPage) : l'alerte
    # de raid puis la carte d'essor, toutes deux sans hauteur fixe (fond + Padding, enfant LayoutMode: Top, comme
    # #DeathData de RespawnPage). Rien ne peut se chevaucher : un contenu plus long fait défiler la colonne.
    w("          Group #StateScroll {")
    w("            FlexWeight: 1;")
    w("            LayoutMode: TopScrolling;")
    w("            ScrollbarStyle: $C.@DefaultScrollbarStyle;")
    w("")
    w("          Group #Alert {")
    w("            Anchor: (Bottom: 10, Right: 10);")
    w("            Padding: (Horizontal: 14, Vertical: 10);")
    w("            Background: (Color: #d9614c(0.18));")
    w("            Group {")
    w("              LayoutMode: Top;")
    w(f'              {label("AlertText", "LabelStyle(FontSize: 14, RenderBold: true, TextColor: #f0b0a0, Wrap: true)")}')
    w("            }")
    w("          }")
    w("")
    w("          @Card #EssorCard {")
    w("            Anchor: (Right: 10);")
    w("            Padding: (Horizontal: 16, Top: 12, Bottom: 12);")
    w("            Group {")
    w("            LayoutMode: Top;")
    w("")
    w("            Group {")
    w("              LayoutMode: Left;")
    w("              Anchor: (Height: 22);")
    w(f'              {label("EssorLabel", "LabelStyle(FontSize: 15, RenderBold: true, TextColor: #d3d6db, VerticalAlignment: Center)", extra=" FlexWeight: 1;")}')
    w(f'              {label("EssorValue", f"LabelStyle(FontSize: 15, RenderBold: true, TextColor: {acc}, HorizontalAlignment: End, VerticalAlignment: Center)")}')
    w("            }")
    w("            @Bar #EssorBar { Anchor: (Height: 16, Top: 6, Bottom: 6); }")
    w(f'            {label("EssorHint", "@SmallWrap")}')
    w("            $C.@PanelSeparatorFancy { @Anchor = Anchor(Top: 8, Bottom: 8); }")
    w(f'            {label("ChantierTitle", f"LabelStyle(FontSize: 13, RenderBold: true, RenderUppercase: true, TextColor: {title}, VerticalAlignment: Center)", anchor="Height: 18, Bottom: 6")}')
    w("")
    w("            // Prochain chantier : les matériaux attendus au dépôt.")
    w("            Group #Materials {")
    w("              LayoutMode: Left;")
    w("              Anchor: (Height: 86);")
    for j in range(MATERIALS):
        w(f"              Group #Mat{j} {{")
        w("                LayoutMode: Top;")
        w("                Anchor: (Width: 64, Right: 18);")
        w("                Group {")
        w("                  LayoutMode: Full;")
        w("                  Anchor: (Width: 64, Height: 64);")
        w(f'                  Group #MatSlot{j} {{ Anchor: (Full: 0); Background: (TexturePath: "{COMMON}IngredientSlot.png", Border: 24); }}')
        w(f'                  Group #MatOk{j} {{ Anchor: (Full: 0); Background: (TexturePath: "{COMMON}IngredientSlotValid.png", Border: 24); Visible: false; }}')
        w(f"                  ItemIcon #MatIcon{j} {{ Anchor: (Full: 6); ShowItemTooltip: true; }}")
        w("                }")
        w(f'                {label(f"MatCount{j}", "@Count", anchor="Height: 20, Top: 2")}')
        w("              }")
    w("            }")
    w(f'            {label("ChantierInfo", "@SmallWrap", anchor="Top: 4")}')
    w("")
    w("            // Chantier en cours : la fin des travaux et les bâtiments.")
    w("            Group #Works {")
    w("              LayoutMode: Top;")
    w("              Visible: false;")
    w(f'              {label("WorksLine", "LabelStyle(FontSize: 15, RenderBold: true, TextColor: #d3d6db, VerticalAlignment: Center)", anchor="Height: 22")}')
    w("              ProgressBar #WorksBar {")
    w("                Anchor: (Height: 12, Top: 4, Bottom: 8);")
    w(f'                Background: "{COMMON}ProgressBar.png";')
    w('                BarTexturePath: "Board/Bar_Chantier.png";')
    w("                Value: 0;")
    w("              }")
    for k in range(BUILDINGS):
        w(f"              Group #Building{k} {{")
        w("                LayoutMode: Left;")
        w("                Anchor: (Height: 22);")
        w(f'                Group #BuildingDone{k} {{ Anchor: (Width: 18, Height: 18, Right: 8); Background: "{COMMON}RunicCheckChecked.png"; Visible: false; }}')
        w(f'                Group #BuildingTodo{k} {{ Anchor: (Width: 18, Height: 18, Right: 8); Background: "{COMMON}RunicCheckEmpty.png"; }}')
        w(f'                {label(f"BuildingName{k}", "@Body", extra=" FlexWeight: 1;")}')
        w("              }")
    w("            }")
    w("")
    w(f'            {label("ChantierNotes", "LabelStyle(FontSize: 13, TextColor: #e8c46a, Wrap: true)", anchor="Top: 4")}')
    w("            $C.@PanelSeparatorFancy { @Anchor = Anchor(Top: 8, Bottom: 6); }")
    w(f'            {label("DepositHeader", "@Caption", anchor="Height: 16, Bottom: 6")}')
    w("            Group #DepositRow {")
    w("              LayoutMode: Left;")
    w("              Anchor: (Height: 36);")
    for k in range(DEPOSIT):
        w(f"              Group #Dep{k} {{")
        w("                LayoutMode: Full;")
        # 9 cases de 36 + 4 = 360 px : tiennent dans la colonne (≈ 410 px utiles avec la barre de défilement).
        w("                Anchor: (Width: 36, Height: 36, Right: 4);")
        w(f'                Background: (TexturePath: "{COMMON}IngredientSlot.png", Border: 24);')
        w(f"                ItemIcon #DepIcon{k} {{ Anchor: (Full: 3); ShowItemTooltip: true; }}")
        w(f'                {label(f"DepCount{k}", "@SlotCount", anchor="Right: 3, Bottom: 1")}')
        w("              }")
    w(f'              {label("DepMore", "@Small", anchor="Left: 4")}')
    w(f'              {label("DepEmpty", "@Small", extra=" Visible: false;")}')
    w("            }")
    w("            }")
    w("          }")
    w("          }")
    w("        }")
    w("      }")
    w("")
    # ---- Pied
    w("      Group {")
    w("        LayoutMode: Left;")
    w("        Anchor: (Height: 44, Top: 12);")
    # Absents en un paragraphe (Absences.boardSummary) dans une zone qui défile : un village où beaucoup manquent ne
    # pousse plus le texte hors de la fenêtre.
    w("        Group #AbsentScroll {")
    w("          LayoutMode: TopScrolling;")
    w("          ScrollbarStyle: $C.@DefaultScrollbarStyle;")
    w("          FlexWeight: 1;")
    w(f'          {label("Absent", "@SmallWrap", anchor="Right: 12")}')
    w("        }")
    w('        $C.@TextButton #TurnIn { @Text = ""; @Anchor = Anchor(Right: 12, Width: 210); }')
    w('        $C.@SecondaryTextButton #TextVersion { @Text = ""; @Anchor = Anchor(Width: 180); }')
    w("      }")
    w("    }")
    w("  }")
    w("}")
    w("")
    w("$C.@BackButton {}")
    # Styles en ligne au format des pages vanilla : « Style: (...) ».
    return "\n".join(L).replace("Style: LabelStyle(", "Style: (") + "\n"


def main():
    for theme_id, t in THEMES.items():
        name = f"BoardPage_{theme_id}.ui" if theme_id else "BoardPage.ui"
        (OUT / name).write_text(page(theme_id), encoding="utf-8")
        bar_png(t["accent"], OUT / "Board" / f"Bar_{theme_id or 'Default'}.png")
        print("écrit", name)
    bar_png(CHANTIER_BAR, OUT / "Board" / "Bar_Chantier.png")


if __name__ == "__main__":
    main()
