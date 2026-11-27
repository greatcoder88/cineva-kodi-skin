"""Apply the Frame TV theme to stock Nimbus before packaging the skin."""

import struct
import xml.etree.ElementTree as ET
import zlib


PALETTE = {
    "primary_background": "FF121316",
    "primary_content_panel_bg": "FF202226",
    "background": "FF0E0F11",
    "dialog_tint": "FF17181B",
    "dialog_bg": "F517181B",
    "dialog_bg2": "FA17181B",
    "dialog_bg3": "FF17181B",
    "button_focus": "FFF5F5F5",
    "button_focus2": "FF343B48",
    "frame_card_focus": "FFE1E5EF",
    "frame_osd_control": "EE262B34",
    "frame_panel": "F5222630",
    "frame_selection": "FF343B48",
    "focused_text": "FF141414",
    "unfocused_text": "FFF5F5F5",
    "artwork_dim": "FFFFFFFF",
    "accent_color": "FFE50914",
    "selected": "FFE50914",
    "keyboard_selected": "FF505050",
    "bg_overlay": "55000000",
    "grey": "FFB6B8BE",
    "red": "FFE50914",
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
            ("FrameHeroTitle", "Inter-Bold.ttf" if inter else title, "61"),
            ("FrameTVLabel", "Inter-SemiBold.ttf" if inter else label, "27"),
            ("FrameBody", label, "29"),
            ("FrameTab", "Inter-SemiBold.ttf" if inter else label, "26"),
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

    # Keep all generated widget paths and list IDs. Present them below the
    # feature artwork and bring them up as soon as a shelf takes focus.
    set_fields(widgets, {"top": "735"})
    widgets.remove(widgets.find("include[.='MainMenuAnimations']"))
    animation = ET.SubElement(widgets, "animation", {
        "type": "Conditional", "condition": "ControlGroup(2000).HasFocus", "reversible": "true",
    })
    ET.SubElement(animation, "effect", {"type": "slide", "start": "0,0", "end": "0,-92",
                                         "time": "125", "tween": "cubic", "easing": "out"})

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
        "Genre": ("Genre", ",  •  "), "Plot": ("Plot", ""), "Logo": ("Art(clearlogo)", ""),
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


def apply_search(xml):
    path = xml / "Custom_1121_SearchResults.xml"
    tree = read_xml(path)
    root = tree.getroot()
    controls = root.find("controls")
    add_section_header(controls, "$LOCALIZE[137]")
    set_fields(find_control(root, 2000), {"top": "430"})

    history = find_control(root, 9000)
    set_fields(history, {"top": "254", "width": "590", "scrolltime": "200"})
    for label in root.iter("label"):
        if label.text == "$VAR[RecentSearchesCaseVar]":
            heading = next(control for control in root.iter("control") if label in control)
            set_fields(heading, {"top": "182", "height": "65", "font": "FrameTVLabel"})
        elif label.text and label.text.startswith("Search results for:"):
            heading = next(control for control in root.iter("control") if label in control)
            label.text = "Results for ‘$INFO[Window(home).Property(nimbus.search.input)]’"
            set_fields(heading, {"left": "64", "top": "436", "font": "FrameTVLabel", "textcolor": "grey"})
        elif label.text == "$INFO[Window(home).Property(nimbus.search.history.empty)]":
            message = next(control for control in root.iter("control") if label in control)
            set_fields(message, {"left": "570", "top": "205", "width": "960", "height": "95",
                                 "font": "FrameTVLabel", "textcolor": "grey"})
    write_xml(tree, path)

    path = xml / "Includes_Search.xml"
    tree = read_xml(path)
    results = tree.getroot().find("include[@name='SearchWidgets']")
    for widget in results.findall("include"):
        list_id = widget.find("param[@name='list_id']")
        if list_id is not None and list_id.get("value") in {"19011", "19012"}:
            widget.set("content", "WidgetListLandscape")
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
            metadata = next(group for group in root.iter("control") if control in group)
            set_fields(metadata, {"width": "610"})
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
                control.find("texture").attrib.update({"border": "22", "colordiffuse": "frame_selection"})
            elif control.get("type") == "button":
                set_fields(control, {"font": "FrameTVLabel"})
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
    set_fields(default_osd, {"height": "280"})
    for event in ("onload", "onunload"):
        ET.SubElement(tree.getroot(), event).text = "ClearProperty(FrameTracksRevision)"
    for group in default_osd.findall("control[@type='grouplist']"):
        if group.findtext("top") == "120":
            set_fields(group, {"top": "131", "height": "120"})
    transport = find_control(default_osd, 700)
    set_fields(transport, {"itemgap": "12"})
    play = find_control(transport, 703)
    set_fields(play, {"width": "96"})
    utilities = find_control(default_osd, 707)
    for group in utilities.findall("control[@type='grouplist']"):
        set_fields(group, {"itemgap": "1"})
        for label in group.findall("control[@type='label']"):
            set_fields(label, {"width": "68", "height": "30", "textcolor": "grey", "font": "FrameTab"})
    for button_id, list_id, kind, availability in (
        (708, 8708, "audio", "Integer.IsGreater(VideoPlayer.AudioStreamCount,0)"),
        (709, 8709, "subtitle", "VideoPlayer.HasSubtitles"),
    ):
        for button in controls.findall(f".//control[@id='{button_id}']"):
            parent = next(group for group in controls.iter("control") if button in group)
            visible = parent.find("visible")
            if visible is not None:
                visible.text = f"[{visible.text}] | {availability}"
            for action in button.findall("onclick"):
                action.set("condition", f"[{action.get('condition', 'true')}] + !{availability}")
            ET.SubElement(button, "onclick", {"condition": availability}).text = f"SetFocus({list_id})"
            ET.SubElement(button, "onup", {"condition": availability}).text = str(list_id)
        picker = ET.SubElement(controls, "include", {"content": "FramePlaybackTracks"})
        for name, value in (("button", button_id), ("id", list_id), ("kind", kind),
                            ("available", availability), ("title", "$LOCALIZE[292]" if kind == "audio" else "$LOCALIZE[287]")):
            ET.SubElement(picker, "param", {"name": name, "value": str(value)})
    write_xml(tree, path)

    path = xml / "Includes_Seekbar.xml"
    tree = read_xml(path)
    seekbar = tree.getroot().find("include[@name='Seekbar']")
    for animation in seekbar.findall(".//animation[@time='500']"):
        animation.set("time", "125")
    for control in tree.getroot().iter("control"):
        label = control.findtext("label", "")
        if control.get("type") == "label" and any(
            token in label for token in ("$INFO[VideoPlayer.Title]", "$INFO[Player.Title]", "$VAR[PlayerTitle", "$VAR[NowPlayingLabelVar]")
        ):
            set_fields(control, {"font": "FrameTVLabel", "textcolor": "osd_light"})
        for midtexture in control.findall("midtexture[@colordiffuse='accent_color']"):
            midtexture.set("colordiffuse", "red")
    write_xml(tree, path)

    path = xml / "Includes_Buttons.xml"
    tree = read_xml(path)
    buttons = tree.getroot()
    player = buttons.find("include[@name='PlayerButton']")
    set_fields(player, {"width": "68", "height": "68", "align": "center", "aligny": "center",
                        "textoffsetx": "0", "textoffsety": "0",
                        "textcolor": "osd_light", "focusedcolor": "focused_text"})
    for tag in ("texturefocus", "alttexturefocus"):
        texture = player.find(tag)
        texture.text = "masks/focus.png"
        texture.attrib.update({"colordiffuse": "button_focus", "border": "22"})
    for tag in ("texturenofocus", "alttexturenofocus"):
        ET.SubElement(player, tag, {"colordiffuse": "frame_osd_control", "border": "22"}).text = "masks/focus.png"
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


def write_feature_scrim(skin):
    # One small stretchable texture keeps the title legible over bright artwork.
    # Fade the edge of the artwork into the matching solid skin background.
    width, height = 224, 82
    color = bytes.fromhex(PALETTE["background"][2:])
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            horizontal = 1 - min(1, x / (width - 1) / 0.40)
            horizontal = horizontal ** 2 * (3 - 2 * horizontal)
            vertical = max(0, (y / (height - 1) - 0.65) / 0.35) ** 2
            alpha = round(255 * (1 - (1 - horizontal) * (1 - vertical)))
            rows.extend(color)
            rows.append(alpha)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    path = skin / "media/frame/feature-scrim.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def apply_video_cards(xml):
    path = xml / "Includes_Home.xml"
    tree = read_xml(path)
    root = tree.getroot()
    for kind, original, width, movement in (
        ("Landscape", "FlixScapeWidgetMovieLayout", "326", "5"),
        ("Poster", "FlixWidgetMovieLayout", "208", "7"),
    ):
        layout = root.find(f"include[@name='WidgetList{kind}']/definition")
        fixedlist = layout.find("control[@type='fixedlist']")
        set_fields(fixedlist, {"movement": movement})
        for tag in ("itemlayout", "focusedlayout"):
            item = fixedlist.find(tag)
            item.set("width", width)
            group = item.find("control")
            set_fields(group, {"left": "64", "top": "12"})
            group.find(f"include[@content='{original}']").set("content", f"Frame{kind}Card")
    category = root.find("include[@name='CategoryLabel']/definition/control")
    set_fields(category, {"left": "64", "top": "52"})
    for control in category.findall("control[@type='label']"):
        set_fields(control, {"top": "0", "height": "40", "aligny": "center",
                             "font": "FrameTVLabel", "textcolor": "unfocused_text",
                             "label": "$PARAM[label]", "scroll": "false"})
        if control.find("left") is not None:
            set_fields(control, {"left": "0"})
        for animation in control.findall("animation"):
            control.remove(animation)
    write_xml(tree, path)


def apply_motion(xml):
    path = xml / "Includes_Animations.xml"
    tree = read_xml(path)
    root = tree.getroot()
    dialogs = root.find("include[@name='Animation_DialogPopupOpenClose']")
    for animation in dialogs.findall("animation"):
        is_opening = animation.get("type") == "WindowOpen"
        for effect in animation.findall("effect"):
            effect.attrib.pop("delay", None)
            effect.set("time", "135" if is_opening else "95")
            if effect.get("type") == "zoom":
                effect.attrib.update({"tween": "cubic", "easing": "out",
                                      "start": "98" if is_opening else "100",
                                      "end": "100" if is_opening else "99"})
    widgets = root.find("include[@name='WidgetVisibilityAnimations']")
    for effect in widgets.findall(".//effect"):
        effect.set("time", "150" if effect.get("type") == "fade" else "105")
    write_xml(tree, path)


def apply_theme(skin, theme_source):
    xml = skin / "xml"
    apply_palette(skin)
    apply_typography(xml)
    apply_home(xml)
    apply_search(xml)
    apply_title_details(xml)
    apply_settings_and_dialogs(xml)
    apply_playback(xml)
    apply_video_cards(xml)
    apply_motion(xml)
    write_feature_scrim(skin)
    target = xml / theme_source.name
    theme = read_xml(theme_source)
    feature_metadata(theme.getroot())
    write_xml(theme, target)
    include_path = xml / "Includes.xml"
    includes = read_xml(include_path)
    ET.SubElement(includes.getroot(), "include", {"file": target.name})
    write_xml(includes, include_path)

    path = xml / "Includes_Home.xml"
    widgets = read_xml(path)
    list_common = widgets.getroot().find("include[@name='WidgetListCommon']")
    set_fields(list_common, {"scrolltime": "150"})
    landscape = widgets.getroot().find("include[@name='WidgetListLandscape']/definition/control[@type='fixedlist']/visible")
    landscape.text += " | [Window.IsVisible(11121) + String.IsEqual(Window(Home).Property(nimbus.search.refreshing),true)]"
    write_xml(widgets, path)
