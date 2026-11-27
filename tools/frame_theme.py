"""Apply the Frame TV theme to stock Nimbus before packaging the skin."""

import xml.etree.ElementTree as ET


PALETTE = {
    "primary_background": "FF141414",
    "primary_content_panel_bg": "FF1F1F1F",
    "background": "FF141414",
    "dialog_tint": "FF181818",
    "dialog_bg": "F5181818",
    "dialog_bg2": "FA181818",
    "dialog_bg3": "FF181818",
    "button_focus": "FFF5F5F5",
    "button_focus2": "FF353535",
    "focused_text": "FF141414",
    "unfocused_text": "FFF5F5F5",
    "artwork_dim": "FFFFFFFF",
    "accent_color": "FFE50914",
    "selected": "FFE50914",
    "keyboard_selected": "FF505050",
    "bg_overlay": "55000000",
    "grey": "FFB3B3B3",
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
    for color in tree.getroot().findall("color"):
        name = color.get("name")
        if name in PALETTE:
            color.text = PALETTE[name]
    write_xml(tree, path)


def apply_typography(xml):
    path = xml / "Font.xml"
    tree = read_xml(path)
    for fontset in tree.getroot().findall("fontset"):
        # Keep Nimbus' script-specific faces. Use each set's existing title face
        # so the new TV labels accept the same character sets as stock Nimbus.
        title = fontset.find("font[name='font52_title']/filename").text
        label = fontset.find("font[name='font27_title']/filename").text
        for name, face, size in (("FrameHeroTitle", title, "64"), ("FrameTVLabel", label, "27")):
            set_fields(ET.SubElement(fontset, "font"), {"name": name, "filename": face, "size": size})
    write_xml(tree, path)


def apply_home(xml):
    path = xml / "Home.xml"
    tree = read_xml(path)
    root = tree.getroot()
    menu = find_control(root, 9000)
    shortcuts = find_control(root, 700)
    widgets = find_control(root, 2000)
    menu_group = next(group for group in root.iter("control") if menu in group)
    shortcut_group = next(group for group in menu_group.findall("control") if shortcuts in group)
    for element in list(menu_group):
        if element.tag in {"animation", "include"}:
            menu_group.remove(element)
        elif element.tag == "control" and element.findtext("./control/label") == "[LIGHT]$INFO[System.Time][/LIGHT]":
            menu_group.remove(element)

    set_fields(menu_group, {"left": "0"})
    menu_group.insert(0, ET.Element("include"))
    menu_group[0].text = "FrameTopBar"
    set_fields(menu, {
        "left": "230", "top": "22", "width": "1256", "height": "70", "orientation": "horizontal",
        "movement": "7", "onleft": "9000", "onright": "9000", "onup": "700",
        "ondown": "SetFocus($INFO[Container(9000).ListItem.Property(menu_id)])", "scrolltime": "180",
    })
    menu.remove(menu.find("include[@content='List']"))
    ET.SubElement(menu, "include").text = "FrameTopMenuItems"
    set_fields(shortcut_group, {"left": "1528", "top": "5"})
    set_fields(shortcuts, {"onup": "9000", "ondown": "9000", "onright": "9000", "height": "95"})

    # Keep all generated widget paths and list IDs. Present them below the
    # feature artwork and bring them up as soon as a shelf takes focus.
    set_fields(widgets, {"top": "735"})
    widgets.remove(widgets.find("include[.='MainMenuAnimations']"))
    animation = ET.SubElement(widgets, "animation", {
        "type": "Conditional", "condition": "ControlGroup(2000).HasFocus", "reversible": "true",
    })
    ET.SubElement(animation, "effect", {"type": "slide", "start": "0,0", "end": "0,-174", "time": "170"})

    content = next(group for group in root.iter("control") if widgets in group)
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
    fields = {
        "Title": ("Label", ""), "Art": ("Art(fanart)", ""), "Year": ("Year", ""),
        "Genre": ("Genre", ",  •  "), "Plot": ("Plot", ""),
    }
    for name, (field, prefix) in fields.items():
        variable = ET.SubElement(theme, "variable", {"name": f"FrameFeature{name}"})
        condition = "ControlGroup(2000).HasFocus"
        if name == "Art":
            condition += " + !String.IsEmpty(ListItem.Art(fanart))"
        ET.SubElement(variable, "value", {"condition": condition}).text = (
            f"$INFO[ListItem.{field}{prefix}]"
        )
        if name == "Art":
            ET.SubElement(variable, "value", {
                "condition": "ControlGroup(2000).HasFocus + !String.IsEmpty(ListItem.Art(poster))",
            }).text = "$INFO[ListItem.Art(poster)]"
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
            set_fields(heading, {"top": "485", "font": "FrameTVLabel", "textcolor": "grey"})
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
            set_fields(control, {"align": "left", "font": "FrameTVLabel", "textcolor": "unfocused_text"})
        elif label in {"$INFO[ListItem.TagLine]", "[I]$INFO[ListItem.Genre][/I]"}:
            set_fields(control, {"align": "left", "font": "FrameTVLabel", "textcolor": "grey"})
        texture = control.find("texture")
        if texture is not None and texture.text == "$INFO[ListItem.Art(fanart)]":
            texture.set("colordiffuse", "FF4A4A4A")
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
    write_xml(tree, path)

    path = xml / "Includes_Seekbar.xml"
    tree = read_xml(path)
    for control in tree.getroot().iter("control"):
        label = control.findtext("label", "")
        if control.get("type") == "label" and any(
            token in label for token in ("$INFO[VideoPlayer.Title]", "$INFO[Player.Title]", "$VAR[PlayerTitle")
        ):
            set_fields(control, {"font": "FrameTVLabel", "textcolor": "osd_light"})
        for midtexture in control.findall("midtexture[@colordiffuse='accent_color']"):
            midtexture.set("colordiffuse", "red")
    write_xml(tree, path)

    path = xml / "Includes_Buttons.xml"
    tree = read_xml(path)
    buttons = tree.getroot()
    player = buttons.find("include[@name='PlayerButton']")
    set_fields(player, {"textcolor": "osd_light", "focusedcolor": "focused_text"})
    for tag in ("texturefocus", "alttexturefocus"):
        player.find(tag).set("colordiffuse", "button_focus")
    for name in ("DefaultDialogButton", "DefaultSettingButton", "DefaultAddonSettingsButton"):
        definition = buttons.find(f"include[@name='{name}']/definition")
        for font in definition.iter("font"):
            if font.text == "font32":
                font.text = "FrameTVLabel"
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
    set_fields(list_common, {"scrolltime": "220"})
    landscape = widgets.getroot().find("include[@name='WidgetListLandscape']/definition/control[@type='fixedlist']/visible")
    landscape.text += " | [Window.IsVisible(11121) + String.IsEqual(Window(Home).Property(nimbus.search.refreshing),true)]"
    write_xml(widgets, path)
