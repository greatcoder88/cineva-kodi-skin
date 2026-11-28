"""Apply the Frame TV theme to stock Nimbus before packaging the skin."""

from copy import deepcopy
import math
import struct
import xml.etree.ElementTree as ET
import zlib


OSD_BUTTON_WIDTH = 112
OSD_BUTTON_HEIGHT = 82
OSD_BUTTON_GAP = 38
TRACK_PANEL_WIDTH = 540
TRACK_ROW_HEIGHT = 70
TRACK_HEADER_HEIGHT = 96

PALETTE = {
    "primary_background": "FF091221",
    "primary_content_panel_bg": "FF1B232D",
    "background": "FF091221",
    "dialog_tint": "FF161E27",
    "dialog_bg": "F5161E27",
    "dialog_bg2": "FA161E27",
    "dialog_bg3": "FF161E27",
    "button_focus": "FFF5F5F5",
    "button_focus2": "FF293844",
    "frame_card_focus": "FF72EBC5",
    "frame_osd_control": "EE262B34",
    "frame_panel": "FF161E27",
    "frame_selection": "FF293844",
    "frame_track_accent": "FF72EBC5",
    "frame_track_focus": "FF2B4153",
    "focused_text": "FF141414",
    "unfocused_text": "FFF5F5F5",
    "artwork_dim": "FFFFFFFF",
    "accent_color": "FF72EBC5",
    "selected": "FF72EBC5",
    "keyboard_selected": "FF505050",
    "bg_overlay": "55000000",
    "grey": "FFB6B8BE",
    "red": "FF72EBC5",
    "osd_dark": "E6191919",
    "player_cache": "FF666666",
}


def read_xml(path):
    return ET.parse(path, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))


def write_xml(tree, path):
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def set_fields(parent, fields):
    for tag, value in fields.items():
        element = parent.find(tag)
        if element is None:
            element = ET.SubElement(parent, tag)
        element.text = value


def find_control(root, control_id):
    return root.find(f".//control[@id='{control_id}']")


def add_section_header(controls, title):
    header = ET.SubElement(controls, "include", {"content": "FrameSectionHeader"})
    ET.SubElement(header, "param", {"name": "title", "value": title})


def apply_palette(skin):
    path = skin / "colors/defaults.xml"
    tree = read_xml(path)
    root = tree.getroot()
    for name, value in PALETTE.items():
        color = root.find(f"color[@name='{name}']")
        if color is None:
            color = ET.SubElement(root, "color", {"name": name})
        color.text = value
    write_xml(tree, path)


def apply_typography(xml):
    path = xml / "Font.xml"
    tree = read_xml(path)
    for fontset in tree.getroot().findall("fontset"):
        # Keep Nimbus' script-specific faces. Use each set's existing title face
        # so the new TV labels accept the same character sets as stock Nimbus.
        title = fontset.find("font[name='font52_title']/filename").text
        label = fontset.find("font[name='font27_title']/filename").text
        for name, size in (("PlayerIcon", "49"), ("PlayerIconSmall", "40")):
            fontset.find(f"font[name='{name}']/size").text = size
        inter = title == "Inter-Regular.ttf"
        fonts = (
            ("FrameHeroTitle", "Inter-Bold.ttf" if inter else title, "72"),
            ("FrameTVLabel", "Inter-SemiBold.ttf" if inter else label, "27"),
            ("FrameBody", label, "29"),
            ("FrameTab", "Inter-SemiBold.ttf" if inter else label, "26"),
            ("FrameProgress", label, "21"),
            ("FramePanelTitle", "Inter-SemiBold.ttf" if inter else label, "33"),
            ("FramePlaybackTitle", "Inter-Bold.ttf" if inter else title, "44"),
        )
        for name, face, size in fonts:
            set_fields(ET.SubElement(fontset, "font"), {"name": name, "filename": face, "size": size})
    write_xml(tree, path)


def apply_home(xml):
    path = xml / "Home.xml"
    tree = read_xml(path)
    root = tree.getroot()
    menu = find_control(root, 9000)
    widgets = find_control(root, 2000)
    menu_group = next(group for group in root.iter("control") if menu in group)
    for element in list(menu_group):
        if element.tag in {"animation", "include"}:
            menu_group.remove(element)
        elif element.tag == "control" and element.findtext("./control/label") == "[LIGHT]$INFO[System.Time][/LIGHT]":
            menu_group.remove(element)
    set_fields(menu_group, {"left": "-580"})
    panel = ET.Element("include")
    panel.text = "FrameSideMenuPanel"
    menu_group.insert(0, panel)
    slide = ET.SubElement(menu_group, "animation", {
        "type": "Conditional", "condition": "Control.HasFocus(9000) | ControlGroup(700).HasFocus",
        "reversible": "true",
    })
    ET.SubElement(slide, "effect", {"type": "slide", "start": "0,0", "end": "580,0",
                                     "time": "150", "tween": "cubic", "easing": "out"})
    set_fields(menu, {"left": "50", "width": "420", "scrolltime": "180"})
    menu.remove(menu.find("include[@content='List']"))
    items = ET.Element("include")
    items.text = "FrameSideMenuItems"
    menu.insert(list(menu).index(menu.find("content")), items)

    # Use a stable shelf viewport. Kodi brings the focused row into view.
    set_fields(widgets, {"top": "490"})
    widgets.remove(widgets.find("include[.='MainMenuAnimations']"))
    for shelf in widgets.iter("control"):
        slide = shelf.find("include[@content='Animation_Widget_Poster_Slide']")
        if slide is None or shelf.find("include[.='WidgetGroupListCommon']") is None:
            continue
        shelf.remove(slide)
        shelf.insert(0, ET.Element("itemgap"))
        shelf.insert(0, ET.Element("height"))
        set_fields(shelf, {"height": "574", "itemgap": "0"})

    content = next(group for group in root.iter("control") if widgets in group)
    top_bar = content.find("include[@content='TopBar']")
    if top_bar is not None:
        content.remove(top_bar)
    content.insert(list(content).index(widgets), ET.Element("include"))
    content[list(content).index(widgets) - 1].text = "FrameHomeFeature"
    # The Home feature owns artwork. Keep the built-in backdrop for Kodi's
    # non-video pages and if the user's existing artwork setting hides it.
    controls = root.find("controls")
    backdrop = next(group for group in controls.findall("control")
                    if any(element.text == "$VAR[HomeFanartVar]" for element in group.iter("imagepath")))
    ET.SubElement(backdrop, "visible").text = "!$EXP[FrameFeatureVisible]"
    old_info = next(group for group in content.iter("control") if group.find("include[.='FlixPanel']") is not None)
    ET.SubElement(old_info, "visible").text = "!$EXP[FrameFeatureVisible]"
    write_xml(tree, path)


def feature_metadata(theme):
    sections = (("movies", 19011), ("tvshows", 22011), ("custom1", 23011),
                ("custom2", 24011), ("custom3", 25011))
    section_labels = [
        f"[String.IsEqual(Container(9000).ListItem.Property(id),{section}) + "
        f"!String.IsEmpty(Container({container}).ListItem.Label)]"
        for section, container in sections
    ]
    focused_card = "[ControlGroup(2000).HasFocus + !String.IsEmpty(ListItem.Label)]"
    source_visible = " | ".join([focused_card, *section_labels])
    visibility = ET.SubElement(theme, "expression", {"name": "FrameFeatureVisible"})
    visibility.text = f"!Player.HasMedia + !String.IsEqual(Skin.String(HomeArtworkChoice),2) + [{source_visible}]"
    ET.SubElement(theme, "expression", {"name": "FrameRatingCurrent"}).text = (
        "!String.IsEmpty(Window(Home).Property(nimbus.frameRatingPath)) + "
        "String.IsEqual(Window(Home).Property(nimbus.frameRatingPath),ListItem.FilenameAndPath) + "
        "String.IsEqual(Window(Home).Property(nimbus.frameRatingLabel),ListItem.Label) + "
        "String.IsEqual(Window(Home).Property(nimbus.frameRatingYear),ListItem.Year)"
    )
    art_sources = ["[ControlGroup(2000).HasFocus + !String.IsEmpty(ListItem.Art(fanart))]"]
    art_sources.extend(
        f"[!ControlGroup(2000).HasFocus + String.IsEqual(Container(9000).ListItem.Property(id),{section}) + "
        f"!String.IsEmpty(Container({container}).ListItem.Art(fanart))]"
        for section, container in sections
    )
    ET.SubElement(theme, "expression", {"name": "FrameFeatureHasFanart"}).text = " | ".join(art_sources)
    logo_sources = [f"[{focused_card} + !String.IsEmpty(ListItem.Art(clearlogo))]"]
    logo_sources.extend(
        f"[!ControlGroup(2000).HasFocus + String.IsEqual(Container(9000).ListItem.Property(id),{section}) + "
        f"!String.IsEmpty(Container({container}).ListItem.Art(clearlogo))]"
        for section, container in sections
    )
    logo_visible = ET.SubElement(theme, "expression", {"name": "FrameFeatureHasLogo"})
    logo_visible.text = f"Skin.HasSetting(Enable.Clearlogo) + [{' | '.join(logo_sources)}]"
    fields = {
        "Title": ("Label", ""), "Art": ("Art(fanart)", ""), "Year": ("Year", ""),
        "Genre": ("Genre", ",  •  "), "Runtime": ("Duration", ",  •  "), "Plot": ("Plot", ""), "Logo": ("Art(clearlogo)", ""),
        "Rating": ("Rating", ",★  "),
        "Tomatometer": ("Property(Rating.tomatoes.Percent)", ",   ·   RT  ,%"),
    }
    for name, (field, prefix) in fields.items():
        variable = ET.SubElement(theme, "variable", {"name": f"FrameFeature{name}"})
        if name == "Rating":
            ET.SubElement(variable, "value", {
                "condition": "ControlGroup(2000).HasFocus + Integer.IsGreater(ListItem.Votes(imdb),0)",
            }).text = "$INFO[ListItem.Rating(imdb),IMDb  ]"
        ET.SubElement(variable, "value", {"condition": "ControlGroup(2000).HasFocus"}).text = (
            f"$INFO[ListItem.{field}{prefix}]"
        )
        for section, container in sections:
            condition = f"String.IsEqual(Container(9000).ListItem.Property(id),{section})"
            ET.SubElement(variable, "value", {"condition": condition}).text = (
                f"$INFO[Container({container}).ListItem.{field}{prefix}]"
            )


def search_detail_variables(theme):
    use_show = "Control.HasFocus(19012) | String.IsEmpty(Container(19011).ListItem.Label)"
    for name, field in (("Title", "Label"), ("Year", "Year"), ("Genre", "Genre"), ("Plot", "Plot")):
        var = ET.SubElement(theme, "variable", {"name": f"FrameSearch{name}"})
        for container, condition in ((19012, use_show), (19011, "")):
            attrs = {"condition": condition} if condition else {}
            ET.SubElement(var, "value", attrs).text = f"$INFO[Container({container}).ListItem.{field}{',  •  ' if name == 'Genre' else ''}]"


def apply_home_rating_slots(xml):
    """Keep configured Nimbus slots and use media-item scores before remote scores."""
    path = xml / "Variables_Ratings.xml"
    tree = read_xml(path)
    root = tree.getroot()
    template = deepcopy(root.find("include[@name='HorizontalRatingSlotTemplate']"))
    template.set("name", "FrameHomeRatingSlot")
    layout = template.find("control")
    layout.find("visible").text = "$PARAM[rating_visible]"
    layout.find("control[@type='label']").set("id", "$PARAM[control_id]")
    root.append(template)

    local_scores = (
        ("imdb", "Rating(imdb)", "Integer.IsGreater(ListItem.Votes(imdb),0)", "", "imdb.png"),
        ("rtc", "Property(Rating.tomatoes.Percent)", "!String.IsEmpty(ListItem.Property(Rating.tomatoes.Percent))",
         "%", "rtfresh.png"),
    )
    slots = ET.SubElement(root, "include", {"name": "FrameHomeRatings"})
    group = ET.SubElement(slots, "control", {"type": "grouplist"})
    set_fields(group, {"orientation": "horizontal", "width": "1100", "height": "42",
                       "itemgap": "12", "align": "left"})
    for slot in range(1, 7):
        available_scores = []
        label = ET.SubElement(root, "variable", {"name": f"FrameRating{slot}Value"})
        icon = ET.SubElement(root, "variable", {"name": f"FrameRating{slot}Image"})
        for source, field, present, suffix, image in local_scores:
            available = f"String.IsEqual(Skin.String(RatingSlot{slot}),{source}) + {present}"
            available_scores.append(available)
            ET.SubElement(label, "value", {"condition": available}).text = f"$INFO[ListItem.{field},,{suffix}]"
            ET.SubElement(icon, "value", {"condition": available}).text = f"special://skin/resources/rating_images/{image}"
        stock = root.find(f"variable[@name='Rating{slot}ValueVar']")
        for value in stock.findall("value"):
            field = value.text.split("$INFO[", 1)[1].split("]", 1)[0]
            test = f"$EXP[FrameRatingCurrent] + {value.get('condition')} + !String.IsEmpty({field})"
            available_scores.append(test)
            ET.SubElement(label, "value", {"condition": test}).text = value.text
        ET.SubElement(icon, "value", {"condition": "$EXP[FrameRatingCurrent]"}).text = f"$VAR[Rating{slot}ImageVar]"
        control = ET.SubElement(group, "include", {"content": "FrameHomeRatingSlot"})
        for name, value in (("rating_slot", f"RatingSlot{slot}"), ("rating_image", f"$VAR[FrameRating{slot}Image]"),
                            ("rating_value", f"$VAR[FrameRating{slot}Value]"), ("control_id", str(8990 + slot)),
                            ("rating_visible", " | ".join(f"[{test}]" for test in available_scores))):
            ET.SubElement(control, "param", {"name": name, "value": value})
    write_xml(tree, path)


def apply_search(xml):
    path = xml / "Custom_1121_SearchResults.xml"
    tree = read_xml(path)
    root = tree.getroot()
    controls = root.find("controls")
    add_section_header(controls, "$LOCALIZE[137]")
    artwork = next(group for group in controls.findall("control[@type='group']")
                   if group.find("include[.='MediaMenuAnimations']") is not None)
    controls.remove(artwork)
    results_group = find_control(root, 2000)
    set_fields(results_group, {"top": "233"})
    results_list = find_control(results_group, 19001)
    results_list.remove(results_list.find("include[@content='Animation_Widget_Poster_Slide']"))
    results_list.insert(0, ET.Element("itemgap"))
    results_list.insert(0, ET.Element("height"))
    set_fields(results_list, {"height": "827", "itemgap": "10"})
    content = next(group for group in controls.findall("control") if results_group in group)
    content.remove(content.find("include[@content='TopBar']"))
    preview = next(group for group in content.iter("control") if group.find("include[.='FlixPanel']") is not None)
    preview_parent = next(group for group in content.iter("control") if preview in group)
    preview_parent.remove(preview)
    chrome = ET.Element("control", {"type": "group"})
    set_fields(chrome, {"left": "72", "top": "153", "width": "1090", "height": "76",
                        "visible": "!String.IsEmpty(Window(Home).Property(nimbus.search.input))"})
    ET.SubElement(chrome, "include").text = "SearchMenuAnimations"
    surface = ET.SubElement(chrome, "control", {"type": "image"})
    ET.SubElement(surface, "texture", {"border": "24", "colordiffuse": "primary_content_panel_bg"}).text = (
        "masks/focus-long.png"
    )
    query = ET.SubElement(chrome, "control", {"type": "label"})
    set_fields(query, {"left": "28", "right": "28", "height": "76", "aligny": "center",
                       "font": "FramePanelTitle", "textcolor": "unfocused_text",
                       "label": "$INFO[Window(Home).Property(nimbus.search.input)]"})
    content.insert(list(content).index(results_group), chrome)
    details = ET.SubElement(content, "include")
    details.text = "FrameSearchDetails"

    history = find_control(root, 9000)
    set_fields(history, {"top": "300", "width": "555", "scrolltime": "175"})
    history_group = next(group for group in root.iter("control") if history in group)
    history_group.find("animation/effect").set("time", "135")
    for label in root.iter("label"):
        if label.text == "$VAR[RecentSearchesCaseVar]":
            heading = next(control for control in root.iter("control") if label in control)
            set_fields(heading, {"top": "235", "height": "54", "font": "FramePanelTitle", "textcolor": "unfocused_text"})
        elif label.text and label.text.startswith("Search results for:"):
            heading = next(control for control in root.iter("control") if label in control)
            content.remove(heading)
        elif label.text == "$INFO[Window(home).Property(nimbus.search.history.empty)]":
            message = next(control for control in root.iter("control") if label in control)
            set_fields(message, {"left": "84", "top": "286", "width": "476", "height": "105",
                                 "font": "FrameTVLabel", "textcolor": "grey"})
    write_xml(tree, path)

    path = xml / "DialogKeyboard.xml"
    tree = read_xml(path)
    root = tree.getroot()
    for control in root.iter("control"):
        font = control.find("font")
        if font is not None and font.text == "font45":
            font.text = "FramePanelTitle"
        texture = control.find("texture")
        if texture is not None and texture.get("colordiffuse") == "$VAR[FocusColorTheme]":
            texture.set("colordiffuse", "button_focus2")
    write_xml(tree, path)

    path = xml / "Includes_Search.xml"
    tree = read_xml(path)
    results = tree.getroot().find("include[@name='SearchWidgets']")
    for widget in results.findall("include"):
        list_id = widget.find("param[@name='list_id']")
        if list_id is not None and list_id.get("value") in {"19011", "19012"}:
            widget.set("content", "FrameSearchPosters")
    write_xml(tree, path)

    path = xml / "Variables_Search.xml"
    tree = read_xml(path)
    collections = tree.getroot().find("variable[@name='SearchProviderCollectionsVar']")
    fen = collections.find("value[@conditiom]")
    fen.set("condition", f"!String.IsEmpty(Window(home).Property(nimbus.search.input.encoded)) + {fen.attrib.pop('conditiom')}")
    write_xml(tree, path)


def apply_title_details(xml):
    path = xml / "DialogVideoInfo.xml"
    tree = read_xml(path)
    root = tree.getroot()
    controls = root.find("controls")
    backdrop = ET.Element("control", {"type": "image"})
    set_fields(backdrop, {"width": "100%", "height": "100%", "depth": "DepthBackground"})
    ET.SubElement(backdrop, "texture", {"colordiffuse": "background"}).text = "colors/white.png"
    controls.insert(0, backdrop)
    actions = find_control(root, 20000)
    stock_items = actions.find("include[@content='List']")
    actions.remove(stock_items)
    items = ET.Element("include")
    items.text = "FrameDetailsActionItems"
    actions.insert(list(actions).index(actions.find("content")), items)
    action_group = next(group for group in root.iter("control") if actions in group)
    poster = next(control for control in action_group.findall("control[@type='image']")
                  if control.findtext("texture") == "$VAR[FlixPosterVar]")
    set_fields(poster, {"width": "790", "height": "565", "right": "66", "top": "211"})
    poster.remove(poster.find("bottom"))
    artwork = poster.find("texture")
    artwork.text = "$INFO[ListItem.Art(fanart)]"
    artwork.attrib.update({"diffuse": "masks/giant-landscape.png", "fallback": "$VAR[FlixPosterVar]",
                           "background": "true"})
    poster.remove(poster.find("bordertexture"))
    for control in root.iter("control"):
        label = control.findtext("label")
        if label == "[B]$VAR[DialogInfoTitle][/B]":
            control.set("id", "8982")
            set_fields(control, {"font": "FrameHeroTitle", "align": "left"})
            # Stock Nimbus omits the closing group delimiter in this expression.
            visible = control.find("visible")
            if visible.text.endswith("$EXP[isEpisode]"):
                visible.text += "]"
        elif label == "$INFO[ListItem.Plot]":
            set_fields(control, {"align": "left", "font": "FrameBody", "textcolor": "unfocused_text"})
        elif label in {"$INFO[ListItem.TagLine]", "[I]$INFO[ListItem.Genre][/I]"}:
            set_fields(control, {"align": "left", "font": "FrameTVLabel", "textcolor": "grey"})
            if label == "[I]$INFO[ListItem.Genre][/I]":
                control.find("label").text = "$INFO[ListItem.Year]$INFO[ListItem.Genre,  •  ]"
        texture = control.find("texture")
        if control is not poster and texture is not None and texture.text == "$INFO[ListItem.Art(fanart)]":
            texture.set("colordiffuse", "FF575757")
            texture.set("diffuse", "overlays/netflixfanartdiffuse.png")
            set_fields(control, {"aspectratio": "scale", "fadetime": "165"})
    write_xml(tree, path)


def apply_settings_and_dialogs(xml):
    path = xml / "SkinSettings.xml"
    tree = read_xml(path)
    root = tree.getroot()
    controls = root.find("controls")
    controls.remove(controls.find("include[@content='TopBar']"))
    add_section_header(controls, "$LOCALIZE[166]")
    categories = find_control(root, 9000)
    for layout in (categories.find("itemlayout"), categories.find("focusedlayout")):
        layout.set("height", "75")
        for control in layout.findall("control"):
            set_fields(control, {"height": "75"})
            if control.get("type") == "label":
                set_fields(control, {"font": "FrameTVLabel", "aligny": "center", "textoffsety": "0"})
            elif control.get("type") == "image":
                control.find("texture").set("border", "22")
    accent = find_control(root, 63703)
    set_fields(accent, {"label": "Frame accent color", "label2": "$VAR[FrameAccentLabel]",
                         "onclick": "RunPlugin(plugin://script.frame.nimbus/?kind=accent)"})
    write_xml(tree, path)

    for name in ("Settings.xml", "SettingsCategory.xml", "Custom_1107_SearchDialog.xml"):
        path = xml / name
        tree = read_xml(path)
        for control in tree.getroot().iter("control"):
            font = control.find("font")
            if font is not None and font.text in {"font36_title", "font45", "font45_title"}:
                font.text = "FramePanelTitle"
        write_xml(tree, path)

    path = xml / "DialogContextMenu.xml"
    tree = read_xml(path)
    root = tree.getroot()
    template = find_control(root, 1000)
    set_fields(template, {"font": "FrameTVLabel", "textcolor": "unfocused_text"})
    set_fields(template, {"align": "left", "aligny": "center", "textoffsetx": "32"})
    header = next(control for control in root.iter("control")
                  if control.findtext("label") == "$VAR[ContextMenuTitleVar]")
    set_fields(header, {"font": "font32_title", "scroll": "true", "scrollspeed": "35"})
    write_xml(tree, path)


def apply_playback(xml):
    path = xml / "VideoOSD.xml"
    tree = read_xml(path)
    controls = tree.getroot().find("controls")
    # The audio stream count is useful to Kodi internally, but is not a title
    # or playback status and should not appear at the top of the picture.
    for control in controls.findall("control"):
        if control.findtext("label") == "$INFO[VideoPlayer.AudioStreamCount]":
            controls.remove(control)
    default_osd = next(group for group in controls.findall("control[@type='group']")
                       if group.find("include[@content='Seekbar']") is not None)
    set_fields(default_osd, {"height": "295"})
    for event in ("onload", "onunload"):
        for kind in ("audio", "subtitle"):
            ET.SubElement(tree.getroot(), event).text = f"ClearProperty(FrameActiveTrack.{kind})"
        ET.SubElement(tree.getroot(), event).text = "ClearProperty(FrameTrackPicker)"
    width = str(OSD_BUTTON_WIDTH)
    height = str(OSD_BUTTON_HEIGHT)
    gap = str(OSD_BUTTON_GAP)
    for group in default_osd.findall("control[@type='grouplist']"):
        if group.findtext("top") == "120":
            set_fields(group, {"top": "169", "height": "122"})
    transport = find_control(default_osd, 700)
    set_fields(transport, {"left": "90", "width": "900", "align": "left", "itemgap": gap})
    play = find_control(transport, 703)
    set_fields(play, {"textcolor": "frame_track_accent", "focusedcolor": "focused_text"})
    include = play.find("include")
    play.remove(include)
    play.append(include)
    stop = find_control(transport, 704)
    forward = find_control(transport, 705)
    transport.remove(stop)
    transport.insert(list(transport).index(forward) + 1, stop)
    utilities = find_control(default_osd, 707)
    set_fields(utilities, {"left": "1328", "width": "506", "align": "right", "itemgap": gap})
    buttons = {
        708: ("audio", "$LOCALIZE[292]", 8708, "Integer.IsGreater(VideoPlayer.AudioStreamCount,0)"),
        709: ("subtitles", "$LOCALIZE[287]", 8709, "VideoPlayer.HasSubtitles"),
        716: ("settings", "$LOCALIZE[5]", None, None),
    }
    for group in utilities.findall("control[@type='grouplist']"):
        button = group.find("control[@type='button']")
        button_id = int(button.get("id")) if button is not None else None
        if button_id not in buttons:
            utilities.remove(group)
            continue
        kind, title, list_id, availability = buttons[button_id]
        set_fields(group, {"width": width, "height": "122", "itemgap": "5", "align": "left"})
        group.remove(group.find("control[@type='label']"))
        for tag in ("include", "font", "label", "textoffsety"):
            element = button.find(tag)
            if element is not None:
                button.remove(element)
        set_fields(button, {"width": width, "height": height, "description": title,
                            "texturefocus": f"frame/{kind}-focus.png",
                            "texturenofocus": f"frame/{kind}.png"})
        # Slot links make the three-button row independent of stock utility IDs.
        set_fields(button, {"onleft": str({708: 703, 709: 708, 716: 709}[button_id]),
                            "onright": str({708: 709, 709: 716, 716: 703}[button_id])})
        for direction in ("onleft", "onright"):
            for duplicate in button.findall(direction)[1:]:
                button.remove(duplicate)
            button.find(direction).attrib.clear()
        label = ET.SubElement(group, "control", {"type": "label"})
        focus = f"Control.HasFocus({button_id})"
        if list_id:
            focus += f" | Control.HasFocus({list_id})"
        set_fields(label, {"width": width, "height": "30", "align": "center", "aligny": "center",
                           "label": title, "font": "FrameProgress", "textcolor": "unfocused_text", "visible": focus})
        if list_id:
            for visible in group.findall("visible"):
                group.remove(visible)
            for action in button.findall("onclick"):
                action.set("condition", f"[{action.get('condition', 'true')}] + !{availability}")
            ET.SubElement(button, "onclick", {"condition": availability}).text = f"SetProperty(FrameTrackPicker,{kind})"
            ET.SubElement(button, "onclick", {"condition": availability}).text = f"SetFocus({list_id})"
            ET.SubElement(group, "onup").text = str(list_id)
            picker = ET.SubElement(controls, "include", {"content": "FramePlaybackTracks"})
            for name, value in (("button", button_id), ("id", list_id), ("kind", "audio" if button_id == 708 else "subtitle"),
                                ("available", availability), ("right", 86), ("title", title)):
                ET.SubElement(picker, "param", {"name": name, "value": str(value)})
            # The helper uses singular "subtitle" as its picker state.
            if button_id == 709:
                button.findall("onclick")[-2].text = "SetProperty(FrameTrackPicker,subtitle)"
    alternate_utilities = controls.findall(".//control[@id='707']")[1]
    alternate_osd = next(group for group in controls.iter("control") if alternate_utilities in group)
    alternate_osd.remove(alternate_utilities)
    alternate_row = deepcopy(utilities)
    alternate_row.remove(alternate_row.find("top"))
    set_fields(alternate_row, {"bottom": "15"})
    alternate_osd.append(alternate_row)
    alternate_transport = find_control(alternate_osd, 700)
    set_fields(alternate_transport, {"bottom": "55", "height": height, "left": "90",
                                     "width": "900", "itemgap": gap})
    alternate_play = find_control(alternate_transport, 703)
    set_fields(alternate_play, {"width": width, "height": height})
    hitbox = find_control(alternate_play, 7031)
    set_fields(hitbox, {"width": width, "height": height})
    hitbox.remove(hitbox.find("animation"))
    for tag, suffix in (("texturefocus", "-focus"), ("texturenofocus", "")):
        texture = hitbox.find(tag)
        texture.attrib.clear()
        texture.text = f"frame/transport{suffix}.png"
    for image in alternate_play.findall("control[@type='image']"):
        animation = image.find("animation")
        if animation is not None:
            image.remove(animation)
        set_fields(image, {"left": "36", "top": "21"})
        image.find("texture").set("colordiffuse", "focused_text" if image.findtext("visible") == "Control.HasFocus(7031)" else "frame_track_accent")
    write_xml(tree, path)

    path = xml / "Includes_Seekbar.xml"
    tree = read_xml(path)
    seekbar = tree.getroot().find("include[@name='Seekbar']")
    seek_controls = seekbar.find("control[@type='group']")
    for control in seek_controls.findall("control"):
        if control.get("type") in {"group", "ranges", "slider"} and control.findtext("width") == "1680":
            set_fields(control, {"left": "240", "width": "1415"})
        if control.get("type") == "group" and control.findtext("top") == "100":
            set_fields(control, {"height": "7"})
        if control.findtext("label") in {"$VAR[PlayerElapsedTimeVar]", "$VAR[PlayerTimeRemainingVar]"}:
            set_fields(control, {"top": "86", "height": "34", "font": "FrameProgress", "aligny": "center"})
    end_time = seek_controls.find("control[label='$VAR[PlayerEndTimeVar]']")
    if end_time is not None:
        seek_controls.remove(end_time)
    backgrounds = tree.getroot().find("include[@name='OSDBackgrounds']")
    first = backgrounds.find("control")
    first.find("visible").text = f"String.IsEqual(Skin.String(OSDStyleSetting),1) + [{first.findtext('visible')}]"
    scrim = ET.SubElement(backgrounds, "control", {"type": "image"})
    set_fields(scrim, {"bottom": "0", "width": "1920", "height": "362", "texture": "frame/playback-scrim.png",
                       "visible": "!String.IsEqual(Skin.String(OSDStyleSetting),1)"})
    for animation in seekbar.findall(".//animation[@time='500']"):
        animation.set("time", "125")
    for control in tree.getroot().iter("control"):
        label = control.findtext("label", "")
        if control.get("type") == "label" and any(
            token in label for token in ("$INFO[VideoPlayer.Title]", "$INFO[Player.Title]", "$VAR[PlayerTitle", "$VAR[NowPlayingLabelVar]")
        ):
            set_fields(control, {"font": "FramePlaybackTitle", "textcolor": "osd_light", "top": "20", "height": "63", "width": "1140", "scroll": "false"})
        for midtexture in control.findall("midtexture[@colordiffuse='accent_color']"):
            midtexture.set("colordiffuse", "frame_track_accent")
    write_xml(tree, path)

    path = xml / "Includes_Buttons.xml"
    tree = read_xml(path)
    buttons = tree.getroot()
    alternate = buttons.find("include[@name='OSDButton']")
    alternate.remove(alternate.find("animation"))
    set_fields(alternate, {"width": width, "height": height, "radioposx": "36", "radioposy": "21"})
    for texture in alternate:
        if texture.tag.startswith("textureradio") and texture.get("colordiffuse") != "disabled":
            texture.set("colordiffuse", "osd_light" if "nofocus" in texture.tag else "focused_text")
    player = buttons.find("include[@name='PlayerButton']")
    set_fields(player, {"width": width, "height": height, "align": "center", "aligny": "center",
                        "textoffsetx": "0", "textoffsety": "0",
                        "textcolor": "osd_light", "focusedcolor": "focused_text"})
    for button_include in (player, alternate):
        for tag in ("texturefocus", "alttexturefocus", "texturenofocus", "alttexturenofocus"):
            texture = button_include.find(tag)
            if texture is None:
                texture = ET.SubElement(button_include, tag)
            texture.attrib.clear()
            suffix = "-focus" if tag.endswith("focus") and "nofocus" not in tag else ""
            texture.text = f"frame/transport{suffix}.png"
    for name in ("DefaultDialogButton", "DefaultSettingButton", "DefaultAddonSettingsButton"):
        definition = buttons.find(f"include[@name='{name}']/definition")
        for font in definition.iter("font"):
            if font.text == "font32":
                font.text = "FrameTVLabel"
    icon_button = buttons.find("include[@name='IconButton']/definition/control")
    unfocused = icon_button.find("texturenofocus")
    unfocused.attrib.clear()
    unfocused.text = None
    write_xml(tree, path)


def write_feature_mask(skin):
    # Bake both gradients into the diffuse texture for a single hero image.
    width, height = 224, 96
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        vertical = min(1, (height - 1 - y) / 24)
        for x in range(width):
            horizontal = min(1, x / 86)
            alpha = round(255 * horizontal ** 1.6 * vertical ** 1.5)
            rows.extend((255, 255, 255, alpha))
    write_rgba_png(skin / "media/frame/feature-mask.png", width, height, rows)


def write_rgba_png(path, width, height, rows):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    path.parent.mkdir(parents=True, exist_ok=True)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def write_focus_glow(skin, name, width, height):
    """Bake the accent ring and its falloff into a single focus-only texture."""
    inset = 6
    radius = 13
    render_width, render_height = width + 2 * inset, height + 2 * inset
    rows = bytearray()
    for y in range(render_height):
        rows.append(0)
        for x in range(render_width):
            dx = abs(x - (render_width - 1) / 2) - (width / 2 - radius)
            dy = abs(y - (render_height - 1) / 2) - (height / 2 - radius)
            distance = math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0) - radius
            if -2.5 <= distance <= 1.25:
                alpha = 255
            elif 1.25 < distance < 6:
                alpha = round(148 * ((6 - distance) / 4.75) ** 1.4)
            else:
                alpha = round(max(0, 1 - abs(distance + 2.5)) * 220)
            rows.extend((255, 255, 255, alpha))
    write_rgba_png(skin / f"media/frame/focus-{name}.png", render_width, render_height, rows)


def write_playback_textures(skin):
    media = skin / "media/frame"
    rows = b"".join(bytes((0, 4, 7, 12, round(253 * (1 - (1 - y / 127) ** 2.4)))) for y in range(128))
    write_rgba_png(media / "playback-scrim.png", 1, 128, rows)
    for kind, icon in (("transport", None), ("audio", waveform_pixel),
                       ("subtitles", captions_pixel), ("settings", gear_pixel)):
        for active in (False, True):
            write_utility_texture(media, kind, icon, active)

    for track_count in range(1, 5):
        write_track_panel(media, track_count)


def write_track_panel(media, track_count):
    width = TRACK_PANEL_WIDTH
    height = TRACK_HEADER_HEIGHT + TRACK_ROW_HEIGHT * track_count
    radius = 24
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            dx = max(radius - x, x - (width - radius - 1), 0)
            dy = max(radius - y, y - (height - radius - 1), 0)
            edge = min(radius - math.hypot(dx, dy), x, width - 1 - x, y, height - 1 - y)
            if edge < 0:
                rows.extend((0, 0, 0, 0))
            elif edge < 1:
                rows.extend((62, 76, 93, 255))
            else:
                rows.extend((14, 22, 33, 253))
    write_rgba_png(media / f"track-panel-{track_count}.png", width, height, rows)


def track_panel_geometry(theme):
    panel = theme.find("include[@name='FramePlaybackTracks']/definition/control")
    track_list = panel.find("control[@type='list']")
    set_fields(panel, {"width": str(TRACK_PANEL_WIDTH),
                       "height": str(TRACK_HEADER_HEIGHT + 4 * TRACK_ROW_HEIGHT)})
    for count in range(1, 5):
        found = f"Container($PARAM[id]).NumItems"
        condition = f"Integer.IsEqual({found},{count})" if count < 4 else f"!Integer.IsLess({found},4)"
        if count < 4:
            ET.SubElement(panel, "animation", {"effect": "slide", "end": f"0,{(4 - count) * TRACK_ROW_HEIGHT}",
                                                "time": "0", "condition": condition}).text = "Conditional"
        image = ET.Element("control", {"type": "image"})
        set_fields(image, {"width": str(TRACK_PANEL_WIDTH),
                           "height": str(TRACK_HEADER_HEIGHT + count * TRACK_ROW_HEIGHT),
                           "texture": f"frame/track-panel-{count}.png", "visible": condition})
        panel.insert(count - 1, image)
    set_fields(track_list, {"height": str(TRACK_ROW_HEIGHT * 4)})
    for tag in ("itemlayout", "focusedlayout"):
        track_list.find(tag).set("height", str(TRACK_ROW_HEIGHT))


def write_utility_texture(media, kind, icon, active):
    width, height, radius = OSD_BUTTON_WIDTH, OSD_BUTTON_HEIGHT, 21
    # A restrained surface becomes a solid, high-contrast pill on focus.
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            dx = max(35 - x, x - (width - 36), 0)
            dy = max(29 - y, y - (height - 30), 0)
            edge = 24 - math.hypot(dx, dy)
            if icon is not None and icon(x - width / 2, y - height / 2):
                rows.extend((20, 30, 43, 255) if active else (241, 246, 251, 255))
            elif edge > 0:
                color = (241, 246, 251) if active else (35, 47, 64)
                rows.extend((*color, round(min(edge, 1) * (255 if active else 177))))
            else:
                rows.extend((0, 0, 0, 0))
    name = f"{kind}-focus.png" if active else f"{kind}.png"
    write_rgba_png(media / name, width, height, rows)


def waveform_pixel(x, y):
    bars = ((-21, 5), (-14, 10), (-7, 16), (0, 21), (7, 15), (14, 10), (21, 5))
    return any(math.hypot(x - center, max(abs(y) - half, 0)) <= 2 for center, half in bars)


def captions_pixel(x, y):
    box = math.hypot(max(abs(x) - 20, 0), max(abs(y) - 11, 0))
    if 2.2 <= box <= 5.3:
        return True
    for center in (-9, 9):
        radius = math.hypot(x - center, y * 0.92)
        if 4.2 <= radius <= 7.4 and not (x - center > 2 and abs(y) < 4):
            return True
    return False


def gear_pixel(x, y):
    radius = math.hypot(x, y)
    angle = math.atan2(y, x)
    outside = 17.5 + 4 * (math.cos(8 * angle) > 0.32)
    inside = 14.2 + 4 * (math.cos(8 * angle) > 0.32)
    return inside <= radius <= outside or 6 <= radius <= 9.5


def apply_video_cards(xml):
    path = xml / "Includes_Home.xml"
    tree = read_xml(path)
    root = tree.getroot()
    for kind, original, width, movement in (
        ("Landscape", "FlixScapeWidgetMovieLayout", "442", "4"),
        ("Poster", "FlixWidgetMovieLayout", "298", "5"),
    ):
        layout = root.find(f"include[@name='WidgetList{kind}']/definition")
        fixedlist = layout.find("control[@type='fixedlist']")
        # The grouplist stacks the heading before the card list. This top offset
        # is additional padding, measured from the end of the heading control.
        set_fields(fixedlist, {"movement": movement, "top": "18"})
        set_fields(fixedlist, {"height": "428" if kind == "Poster" else "282"})
        for tag in ("itemlayout", "focusedlayout"):
            item = fixedlist.find(tag)
            item.set("width", width)
            item.set("height", fixedlist.findtext("height"))
            group = item.find("control")
            set_fields(group, {"left": "72", "top": "12"})
            group.find(f"include[@content='{original}']").set("content", f"Frame{kind}Card")
    search = deepcopy(root.find("include[@name='WidgetListPoster']"))
    search.set("name", "FrameSearchPosters")
    fixedlist = search.find("definition/control[@type='fixedlist']")
    set_fields(fixedlist, {"right": "772", "height": "287", "movement": "4"})
    for layout in (fixedlist.find("itemlayout"), fixedlist.find("focusedlayout")):
        layout.attrib.update(width="186", height="287")
        group = layout.find("control")
        group.find("include[@content='FramePosterCard']").set("content", "FrameSearchPosterCard")
        for name in ("HomeTrailerControl", "ClearLandscapeProperties"):
            include = group.find(f"include[.='{name}']")
            if include is not None:
                group.remove(include)
    root.append(search)
    category = root.find("include[@name='CategoryLabel']/definition/control")
    set_fields(category, {"left": "72", "top": "37", "height": "56"})
    for control in category.findall("control[@type='label']"):
        set_fields(control, {"left": "0", "top": "0", "height": "56", "aligny": "center",
                             "font": "FramePanelTitle", "textcolor": "unfocused_text",
                             "label": "$PARAM[label]", "scroll": "false"})
        for animation in control.findall("animation"):
            control.remove(animation)
    # Reserve the far-right gutter for widget navigation indicators.
    include_path = xml / "Includes.xml"
    includes = read_xml(include_path)
    arrows = includes.getroot().find("include[@name='WidgetUpDownArrows']/definition")
    for control in arrows.findall("control"):
        direction = control.find("texturefocus").get("flipy")
        set_fields(control, {"left": "1854", "top": "39" if direction else "70",
                             "width": "24", "height": "24"})
    write_xml(includes, include_path)
    write_xml(tree, path)


def apply_motion(xml):
    path = xml / "Includes_Animations.xml"
    tree = read_xml(path)
    root = tree.getroot()
    search_slide = root.find("include[@name='SearchMenuAnimations']/animation/effect")
    search_slide.set("time", "135")
    search_slide.set("end", "552,0")
    dialogs = root.find("include[@name='Animation_DialogPopupOpenClose']")
    for animation in dialogs.findall("animation"):
        is_opening = animation.get("type") == "WindowOpen"
        for effect in animation.findall("effect"):
            if effect.get("type") == "zoom":
                animation.remove(effect)
            else:
                effect.attrib.pop("delay", None)
                effect.set("time", "105" if is_opening else "75")
    widgets = root.find("include[@name='WidgetVisibilityAnimations']")
    for effect in widgets.findall(".//effect"):
        effect.set("time", "150" if effect.get("type") == "fade" else "105")
    write_xml(tree, path)


def apply_accent(xml):
    """Route Frame's accent aliases through the same saved color."""
    aliases = {name for name, color in PALETTE.items() if color == "FF72EBC5"}
    variable = "$VAR[FrameAccent]"
    for path in xml.glob("*.xml"):
        original = path.read_bytes()
        updated = original
        for name in sorted(aliases):
            for old, new in (
                (f'colordiffuse="{name}"', f'colordiffuse="{variable}"'),
                (f'>{name}<', f'>{variable}<'),
                (f'[COLOR {name}]', f'[COLOR {variable}]'),
            ):
                updated = updated.replace(old.encode(), new.encode())
        if updated != original:
            ET.fromstring(updated)
            path.write_bytes(updated)


def apply_theme(skin, theme_source):
    xml = skin / "xml"
    apply_palette(skin)
    apply_typography(xml)
    apply_home(xml)
    apply_home_rating_slots(xml)
    apply_search(xml)
    apply_title_details(xml)
    apply_settings_and_dialogs(xml)
    apply_playback(xml)
    apply_video_cards(xml)
    apply_motion(xml)
    write_feature_mask(skin)
    for name, width, height in (("poster", 276, 409), ("landscape", 420, 236), ("search", 168, 252)):
        write_focus_glow(skin, name, width, height)
    write_rgba_png(skin / "media/frame/landscape-empty.png", 1, 1, bytes((0, 27, 35, 45, 255)))
    write_playback_textures(skin)
    target = xml / theme_source.name
    theme = read_xml(theme_source)
    feature_metadata(theme.getroot())
    track_panel_geometry(theme.getroot())
    search_detail_variables(theme.getroot())
    write_xml(theme, target)
    include_path = xml / "Includes.xml"
    includes = read_xml(include_path)
    ET.SubElement(includes.getroot(), "include", {"file": target.name})
    write_xml(includes, include_path)

    path = xml / "Includes_Home.xml"
    widgets = read_xml(path)
    list_common = widgets.getroot().find("include[@name='WidgetListCommon']")
    set_fields(list_common, {"scrolltime": "220"})
    landscape = widgets.getroot().find("include[@name='WidgetListLandscape']/definition/control[@type='fixedlist']/visible")
    landscape.text += " | [Window.IsVisible(11121) + String.IsEqual(Window(Home).Property(nimbus.search.refreshing),true)]"
    write_xml(widgets, path)
    apply_accent(xml)
