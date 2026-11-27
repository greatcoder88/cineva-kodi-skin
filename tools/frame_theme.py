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
        for name, face, size in (("FrameHeroTitle", title, "64"), ("FrameTVLabel", label, "30")):
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
        "left": "230", "top": "22", "width": "1288", "height": "70", "orientation": "horizontal",
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
    fields = {
        "Title": ("Label", ""), "Art": ("Art(fanart)", ""), "Year": ("Year", ""),
        "Genre": ("Genre", ",  •  "), "Plot": ("Plot", ""),
    }
    for name, (field, prefix) in fields.items():
        variable = ET.SubElement(theme, "variable", {"name": f"FrameFeature{name}"})
        ET.SubElement(variable, "value", {"condition": "ControlGroup(2000).HasFocus"}).text = (
            f"$INFO[ListItem.{field}{prefix}]"
        )
        for section, container in sections:
            condition = f"String.IsEqual(Container(9000).ListItem.Property(id),{section})"
            ET.SubElement(variable, "value", {"condition": condition}).text = (
                f"$INFO[Container({container}).ListItem.{field}{prefix}]"
            )


def apply_theme(skin, theme_source):
    xml = skin / "xml"
    apply_palette(skin)
    apply_typography(xml)
    apply_home(xml)
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
    write_xml(widgets, path)
