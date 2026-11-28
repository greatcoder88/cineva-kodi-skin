"""Apply the Frame TV theme to stock Nimbus before packaging the skin."""

from copy import deepcopy
import math
import struct
import xml.etree.ElementTree as ET
import zlib


PALETTE = {
    "primary_background": "FF11161D",
    "primary_content_panel_bg": "FF1B232D",
    "background": "FF0B1016",
    "dialog_tint": "FF161E27",
    "dialog_bg": "F5161E27",
    "dialog_bg2": "FA161E27",
    "dialog_bg3": "FF161E27",
    "button_focus": "FFF5F5F5",
    "button_focus2": "FF293844",
    "frame_card_focus": "FFE1E5EF",
    "frame_osd_control": "EE262B34",
    "frame_panel": "FF161E27",
    "frame_selection": "FF293844",
    "frame_track_accent": "FFA1EBDD",
    "frame_track_ring": "FF74808C",
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

    # Widget headings and cards share a bounded shelf area below the hero.
    # Kodi scrolls the focused row into view, using its actual height.
    set_fields(widgets, {"top": "611"})
    widgets.remove(widgets.find("include[.='MainMenuAnimations']"))
    for shelf in widgets.iter("control"):
        slide = shelf.find("include[@content='Animation_Widget_Poster_Slide']")
        if slide is None or shelf.find("include[.='WidgetGroupListCommon']") is None:
            continue
        shelf.remove(slide)
        set_fields(shelf, {"height": "438", "scrolltime": "100"})
        height = shelf.find("height")
        shelf.remove(height)
        shelf.insert(0, height)

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
    set_fields(poster, {"width": "790", "height": "445", "right": "66", "top": "200"})
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
            set_fields(metadata, {"width": "610", "itemgap": "10"})
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
                set_fields(control, {"font": "FrameTVLabel", "aligny": "center",
                                     "textoffsety": "0", "textcolor": "unfocused_text"})
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


def apply_addon_browser(xml):
    """Keep repository browsing on a stable canvas while the list moves."""
    path = xml / "AddonBrowser.xml"
    tree = read_xml(path)
    controls = tree.getroot().find("controls")
    artwork = next(group for group in controls.findall("control[@type='group']")
                   if group.find("include[.='MediaMenuAnimations']") is not None)
    controls.remove(artwork)
    write_xml(tree, path)


def apply_source_dialogs(xml):
    path = xml / "DialogBusy.xml"
    tree = read_xml(path)
    root = tree.getroot()
    for animation in root.findall("animation"):
        root.remove(animation)
    busy = root.find("controls/control")
    for animation in busy.findall("animation"):
        busy.remove(animation)
    spinner = next(control for control in busy.iter("control")
                   if control.findtext("texture") == "loading.gif")
    spinner.find("texture").attrib.clear()
    set_fields(spinner, {"width": "56", "height": "56", "texture": "frame/loading-ring.png"})
    ET.SubElement(spinner, "animation", {"effect": "rotate", "start": "0", "end": "360",
                                         "center": "auto", "time": "850", "loop": "true",
                                         "condition": "true"}).text = "Conditional"
    write_xml(tree, path)

    path = xml / "DialogSelect.xml"
    tree = read_xml(path)
    tree.getroot().remove(tree.getroot().find("include[.='Animation_DialogPopupOpenClose']"))
    write_xml(tree, path)
    path = xml / "Includes_DialogSelect.xml"
    tree = read_xml(path)
    layouts = tree.getroot().find("include[@name='DefaultDialogSelectLayout']")
    for control in layouts.findall(".//control[@type='list']"):
        set_fields(control, {"scrolltime": "75"})
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
        ET.SubElement(tree.getroot(), event).text = "ClearProperty(FrameTracksRevision)"
        ET.SubElement(tree.getroot(), event).text = "ClearProperty(FrameTrackPicker)"
    for group in default_osd.findall("control[@type='grouplist']"):
        if group.findtext("top") == "120":
            set_fields(group, {"top": "169", "height": "122"})
    transport = find_control(default_osd, 700)
    set_fields(transport, {"left": "90", "width": "705", "align": "left", "itemgap": "24"})
    for button in transport.findall("control[@type='button']"):
        ET.SubElement(button, "texturenofocus").text = "frame/transparent.png"
        button.insert(0, button.find("texturenofocus"))
    play = find_control(transport, 703)
    stop = find_control(transport, 704)
    forward = find_control(transport, 705)
    transport.remove(stop)
    transport.insert(list(transport).index(forward) + 1, stop)
    play_include = play.find("include")
    play.remove(play_include)
    set_fields(play, {"width": "68", "textcolor": "focused_text"})
    for tag in ("texturefocus", "alttexturefocus", "texturenofocus", "alttexturenofocus"):
        ET.SubElement(play, tag, {
            "colordiffuse": "button_focus" if "nofocus" in tag else "frame_track_accent",
        }).text = "frame/play-disc.png"
    play.append(play_include)
    utilities = find_control(default_osd, 707)
    set_fields(utilities, {"left": "1328", "width": "506", "align": "right", "itemgap": "38"})
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
        set_fields(group, {"width": "112", "height": "122", "itemgap": "5", "align": "left"})
        group.remove(group.find("control[@type='label']"))
        for tag in ("include", "font", "label", "textoffsety"):
            element = button.find(tag)
            if element is not None:
                button.remove(element)
        set_fields(button, {"width": "112", "height": "82", "description": title,
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
        set_fields(label, {"width": "112", "height": "30", "align": "center", "aligny": "center",
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
                                ("available", availability), ("right", 253 if button_id == 708 else 103), ("title", title)):
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
    for tag, color in (("texturefocus", "button_focus"), ("texturenofocus", "frame_osd_control")):
        texture = alternate.find(tag)
        texture.attrib.update({"border": "22", "colordiffuse": color})
        texture.text = "masks/focus.png"
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


def write_feature_mask(skin):
    # One small stretchable texture keeps the title legible over bright artwork.
    # Fade the edge of the artwork into the matching solid skin background.
    width, height = 224, 82
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            horizontal = 1 - min(1, x / (width - 1) / 0.40)
            horizontal = horizontal ** 2 * (3 - 2 * horizontal)
            vertical = max(0, (y / (height - 1) - 0.65) / 0.35) ** 2
            alpha = round(255 * (1 - horizontal) * (1 - vertical))
            rows.extend((255, 255, 255))
            rows.append(alpha)

    write_rgba_png(skin / "media/frame/feature-mask.png", width, height, rows)


def write_rgba_png(path, width, height, rows):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    path.parent.mkdir(parents=True, exist_ok=True)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def write_playback_textures(skin):
    media = skin / "media/frame"
    write_rgba_png(media / "transparent.png", 1, 1, bytes(5))
    ring = bytearray()
    for y in range(56):
        ring.append(0)
        for x in range(56):
            dx, dy = x - 27.5, y - 27.5
            edge = max(0, min(1, 2 - abs(math.hypot(dx, dy) - 23)))
            sweep = (math.atan2(dy, dx) % math.tau) / math.tau
            ring.extend((161, 235, 221, round(255 * edge * (0.12 + 0.88 * sweep ** 2))))
    write_rgba_png(media / "loading-ring.png", 56, 56, ring)
    rows = b"".join(bytes((0, 4, 7, 12, round(253 * (1 - (1 - y / 127) ** 2.4)))) for y in range(128))
    write_rgba_png(media / "playback-scrim.png", 1, 128, rows)

    disc = bytearray()
    for y in range(68):
        disc.append(0)
        for x in range(68):
            distance = ((x - 33.5) ** 2 + (y - 33.5) ** 2) ** 0.5
            alpha = round(255 * max(0, min(1, 34 - distance)))
            disc.extend((255, 255, 255, alpha))
    write_rgba_png(media / "play-disc.png", 68, 68, disc)

    for kind, icon in (("audio", waveform_pixel), ("subtitles", captions_pixel), ("settings", gear_pixel)):
        for active in (False, True):
            write_utility_texture(media, kind, icon, active)

    pointer = bytearray()
    for y in range(14):
        pointer.append(0)
        for x in range(25):
            edge = 12 - abs(x - 12) - y
            pointer.extend((116, 128, 140, 255) if edge == 0 else
                           (22, 27, 35, 255) if edge > 0 else (0, 0, 0, 0))
    write_rgba_png(media / "track-pointer.png", 25, 14, pointer)


def write_utility_texture(media, kind, icon, active):
    width, height, radius = 112, 82, 21
    outline = (244, 248, 250) if active else (108, 124, 138)
    stroke = 3.2 if active else 2.4
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            dx = max(radius - x, x - (width - radius - 1), 0)
            dy = max(radius - y, y - (height - radius - 1), 0)
            distance = math.hypot(dx, dy)
            if icon(x - width / 2, y - height / 2):
                rows.extend((246, 250, 252, 255))
            elif distance >= radius:
                rows.extend((0, 0, 0, 0))
            elif distance >= radius - stroke or min(x, y, width - 1 - x, height - 1 - y) < stroke:
                rows.extend((*outline, 255))
            else:
                rows.extend((13, 21, 28, 220 if active else 185))
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
            if effect.get("type") == "zoom":
                animation.remove(effect)
            else:
                effect.attrib.pop("delay", None)
                effect.set("time", "105" if is_opening else "75")
    widgets = root.find("include[@name='WidgetVisibilityAnimations']")
    for animation in widgets.findall("animation"):
        if animation.find("effect[@type='fadediffuse']") is not None:
            widgets.remove(animation)
        else:
            for effect in animation.findall("effect"):
                effect.set("time", "80")
    navigation = root.find("include[@name='WidgetNavigationAnimations']")
    for animation in navigation.findall("animation"):
        animation.set("time", "100")
    write_xml(tree, path)


def apply_theme(skin, theme_source):
    xml = skin / "xml"
    apply_palette(skin)
    apply_typography(xml)
    apply_home(xml)
    apply_search(xml)
    apply_title_details(xml)
    apply_settings_and_dialogs(xml)
    apply_addon_browser(xml)
    apply_source_dialogs(xml)
    apply_playback(xml)
    apply_video_cards(xml)
    apply_motion(xml)
    write_feature_mask(skin)
    write_playback_textures(skin)
    target = xml / theme_source.name
    theme = read_xml(theme_source)
    feature_metadata(theme.getroot())
    write_xml(theme, target)
    include_path = xml / "Includes.xml"
    includes = read_xml(include_path)
    arrows = includes.getroot().find("include[@name='WidgetUpDownArrows']/definition")
    for control in arrows.findall("control"):
        texture = control.find("texturefocus")
        upward = texture.get("flipy") == "true"
        set_fields(control, {"left": "19", "top": "112" if upward else "145", "width": "20", "height": "20"})
        for tag in ("texturefocus", "texturenofocus"):
            control.find(tag).set("colordiffuse", "988F9CAB")
    ET.SubElement(includes.getroot(), "include", {"file": target.name})
    write_xml(includes, include_path)

    path = xml / "Includes_Home.xml"
    widgets = read_xml(path)
    list_common = widgets.getroot().find("include[@name='WidgetListCommon']")
    set_fields(list_common, {"scrolltime": "105"})
    landscape = widgets.getroot().find("include[@name='WidgetListLandscape']/definition/control[@type='fixedlist']/visible")
    landscape.text += " | [Window.IsVisible(11121) + String.IsEqual(Window(Home).Property(nimbus.search.refreshing),true)]"
    write_xml(widgets, path)
