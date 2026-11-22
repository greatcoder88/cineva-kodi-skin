#!/usr/bin/env python3
"""Build the distributable CINÉVA ZIP with runtime-critical XML fixes."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
import tempfile
import xml.etree.ElementTree as ET

ARCHIVE = Path(__file__).resolve().parents[1] / "skin.cineva-0.5.3.zip"


def set_child_text(parent, tag, value):
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = str(value)


def update_xml(data, path):
    root = ET.fromstring(data)
    if path == "skin.cineva/addon.xml":
        root.set("version", "0.5.3")
        for imp in root.findall("./requires/import"):
            if imp.get("addon") == "script.cineva.widgets":
                imp.set("version", "0.1.3")
    elif path == "skin.cineva/xml/Home.xml":
        default = root.find("defaultcontrol")
        if default is None:
            default = ET.Element("defaultcontrol", {"always": "true"})
            root.insert(0, default)
        default.set("always", "true")
        default.text = "1001"
        onload = root.find("onload")
        if onload is None:
            onload = ET.Element("onload")
            root.insert(0, onload)
        onload.attrib.clear()
        onload.text = "RunScript(script.cineva.widgets,action=init)"
        # Rebuild Home as a cinematic hero plus large, breathable content rails.
        # Two full large-poster rails fit above the fold; remaining shelves stay reachable by D-pad navigation.
        controls = root.find("controls")
        if controls is None:
            raise SystemExit("Home.xml is missing its controls container")
        # The archive builder runs twice in CI. Unwrap an existing rail grouplist
        # before rebuilding it so the transformation remains idempotent.
        previous_rail_list = controls.find("./control[@type='grouplist'][@id='9050']")
        if previous_rail_list is not None:
            row_insert_index = list(controls).index(previous_rail_list)
            controls.remove(previous_rail_list)
            for child in list(previous_rail_list.findall("control")):
                previous_rail_list.remove(child)
                # Newer builds wrap each heading/shelf pair in a row group.
                # Unwrap those groups before rebuilding so two consecutive
                # archive builds remain structurally identical.
                if child.get("type") == "group" and child.get("id", "").startswith("906"):
                    for row_child in list(child.findall("control")):
                        child.remove(row_child)
                        controls.insert(row_insert_index, row_child)
                        row_insert_index += 1
                else:
                    controls.insert(row_insert_index, child)
                    row_insert_index += 1
        # Cinematic hero: give artwork room to breathe and fade it cleanly into the catalogue.
        for control in controls.findall("control"):
            if control.get("type") == "image" and control.findtext("texture", "").startswith("$INFO[Container("):
                set_child_text(control, "height", 440)
            if control.get("type") == "image" and control.findtext("texture") == "hero-shade.png":
                set_child_text(control, "height", 490)
        # Add a mirrored top fade so the logo/date remain legible over bright fanart.
        hero_shade = next((node for node in controls.findall("control")
                           if node.get("type") == "image" and node.findtext("texture") == "hero-shade.png"), None)
        if hero_shade is None:
            raise SystemExit("Home.xml is missing the hero fade texture")
        previous_top_shade = controls.find("./control[@id='9100']")
        if previous_top_shade is not None:
            controls.remove(previous_top_shade)
        top_shade = ET.Element("control", {"type": "image", "id": "9100"})
        for tag, value in (("left", 0), ("top", 0), ("width", 1920), ("height", 260)):
            set_child_text(top_shade, tag, value)
        top_texture = ET.SubElement(top_shade, "texture", {"flipy": "true"})
        top_texture.text = "hero-shade.png"
        set_child_text(top_shade, "aspectratio", "scale")
        controls.insert(list(controls).index(hero_shade) + 1, top_shade)
        # Keep navigation above full-bleed artwork; it was previously painted first
        # and then hidden beneath the hero image controls.
        topbar = next((node for node in list(controls)
                       if node.tag == "include" and (node.text or "").strip() == "CinevaTopBar"), None)
        if topbar is not None:
            controls.remove(topbar)
            hero_end = max((i for i, node in enumerate(list(controls))
                            if node.tag == "control" and node.get("type") == "image"), default=-1)
            controls.insert(hero_end + 1, topbar)
        for group in controls.findall("control"):
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "top", 124)
                labels = [child for child in group.findall("control") if child.get("type") == "label"]
                if labels:
                    # Title first, metadata second: separate vertical baselines.
                    set_child_text(labels[0], "top", 30)
                    set_child_text(labels[0], "font", "font36")
                    set_child_text(labels[0], "height", 64)
                if len(labels) > 1:
                    set_child_text(labels[1], "top", 8)
                    set_child_text(labels[1], "height", 30)
                for child in group.findall("control"):
                    if child.get("type") == "textbox":
                        set_child_text(child, "top", 112)
                        set_child_text(child, "height", 58)
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "width", 1200)
        # Hero actions follow whichever Home rail supplies the current hero item.
        # The play command uses the selected ListItem.File; Info first returns focus
        # to that rail so Kodi opens the correct item's information dialog.
        for control in list(controls):
            if control.get("id") in {"9101", "9102", "9103", "9104"}:
                controls.remove(control)
        action_specs = ((9001, 9111, 1001), (9002, 9113, 1001),
                        (9003, 9115, 1002), (9004, 9117, 1003))
        nav_focus = " | ".join(f"Control.HasFocus({button_id})" for button_id in range(1001, 1007))
        action_groups = []
        for container_id, play_id, nav_target in action_specs:
            info_id = play_id + 1
            group_id = 9100 + container_id - 9000
            action_group = ET.Element("control", {"type": "group", "id": str(group_id)})
            for tag, value in (("left", 72), ("top", 310), ("width", 500), ("height", 48)):
                set_child_text(action_group, tag, value)
            visible_terms = [f"Control.HasFocus({container_id})",
                             f"Control.HasFocus({play_id})", f"Control.HasFocus({info_id})"]
            if container_id == 9001:
                visible_terms.insert(0, nav_focus)
            set_child_text(action_group, "visible", " | ".join(visible_terms))
            for button_id, label, left, width in (
                (play_id, "PLAY", 0, 180), (info_id, "MORE INFO", 204, 230)
            ):
                button = ET.SubElement(action_group, "control",
                                       {"type": "button", "id": str(button_id)})
                for tag, value in (
                    ("left", left), ("top", 0), ("width", width), ("height", 44),
                    ("label", label), ("font", "font12"),
                    ("onup", f"SetFocus({nav_target})"),
                    ("ondown", f"SetFocus({container_id})"),
                    ("onleft", f"SetFocus({play_id})" if button_id == play_id else f"SetFocus({play_id})"),
                    ("onright", f"SetFocus({info_id})"),
                    ("texturefocus", "focus-bar.png"),
                    ("texturenofocus", "white.png" if button_id == play_id else "black.png"),
                    ("textcolor", "black" if button_id == play_id else "white"), ("focusedcolor", "white"),
                    ("align", "center"), ("aligny", "center")
                ):
                    set_child_text(button, tag, value)
                if button_id == play_id:
                    set_child_text(button, "onclick",
                                   f"PlayMedia($INFO[Container({container_id}).ListItem.File])")
                else:
                    set_child_text(button, "onclick", f"SetFocus({container_id})")
                    ET.SubElement(button, "onclick").text = "Action(Info)"
            action_groups.append(action_group)
        first_heading = next((node for node in controls.findall("control")
                              if node.get("type") == "label"
                              and node.findtext("label") == "$INFO[Skin.String(Cineva.Widget1.Name)]"), None)
        if first_heading is None:
            raise SystemExit("Home.xml is missing the first widget heading")
        insert_at = list(controls).index(first_heading)
        for action_group in action_groups:
            controls.insert(insert_at, action_group)
            insert_at += 1
        # Keep hero metadata visible while either action button in its row is focused.
        for hero_group in controls.findall("control"):
            if hero_group.get("type") != "group":
                continue
            source_label = hero_group.findtext("control/label", "")
            if not source_label.startswith("$INFO[Container("):
                continue
            current_visible = hero_group.findtext("visible", "")
            if "Control.HasFocus(1001)" in current_visible:
                continue
            container_id = int(source_label.split("Container(", 1)[1].split(")", 1)[0])
            play_id = 9111 + (container_id - 9001) * 2
            set_child_text(hero_group, "visible",
                           f"Control.HasFocus({container_id}) | Control.HasFocus({play_id}) | Control.HasFocus({play_id + 1})")
        # Keep the cinematic hero pinned while the four Home rails scroll as one catalogue.
        # Each row is a single grouplist child so its non-focusable heading cannot
        # intercept Up from the nested fixedlist before the shelf's explicit route.
        rail_list = ET.Element("control", {"type": "grouplist", "id": "9050"})
        for tag, value in (("left", 72), ("top", 370), ("width", 1776), ("height", 680)):
            set_child_text(rail_list, tag, value)
        set_child_text(rail_list, "orientation", "vertical")
        set_child_text(rail_list, "itemgap", 4)
        set_child_text(rail_list, "scrolltime", 220)
        set_child_text(rail_list, "usecontrolcoords", "false")
        first_row_index = None
        for index in range(1, 5):
            heading_label = f"$INFO[Skin.String(Cineva.Widget{index}.Name)]"
            heading = next((c for c in controls.findall("control")
                            if c.get("type") == "label" and c.findtext("label") == heading_label), None)
            shelf = controls.find(f"./control[@type='fixedlist'][@id='{9000 + index}']")
            if heading is None or shelf is None:
                raise SystemExit(f"Home.xml is missing widget row {index}")
            if first_row_index is None:
                first_row_index = list(controls).index(heading)
            controls.remove(heading)
            controls.remove(shelf)
            row_group = ET.Element("control", {"type": "group", "id": str(9060 + index)})
            for tag, value in (("left", 0), ("top", 0), ("width", 1776), ("height", 304)):
                set_child_text(row_group, tag, value)
            play_id = 9111 + (index - 1) * 2
            next_target = 9000 + index + 1 if index < 4 else 1001
            set_child_text(row_group, "onup", f"SetFocus({play_id})")
            set_child_text(row_group, "ondown", f"SetFocus({next_target})")
            # The grouplist places each row group in sequence; children use local coordinates.
            set_child_text(heading, "left", 0)
            set_child_text(heading, "top", 0)
            set_child_text(heading, "width", 1100)
            set_child_text(heading, "height", 32)
            set_child_text(heading, "font", "font16")
            set_child_text(shelf, "left", 0)
            set_child_text(shelf, "top", 32)
            set_child_text(shelf, "width", 1776)
            set_child_text(shelf, "height", 272)
            set_child_text(shelf, "onup", f"SetFocus({play_id})")
            set_child_text(shelf, "ondown", f"SetFocus({next_target})")
            for layout in shelf.findall("./itemlayout") + shelf.findall("./focusedlayout"):
                layout.set("width", "222")
                layout.set("height", "272")
            focused_layout = shelf.find("./focusedlayout")
            focused_include = focused_layout.find("include") if focused_layout is not None else None
            if focused_include is not None:
                focused_include.text = f"CinevaFocusedPosterItem{9000 + index}"
            row_group.append(heading)
            row_group.append(shelf)
            rail_list.append(row_group)
        if first_row_index is None:
            raise SystemExit("Home.xml has no widget rows to place in the scrolling rail list")
        controls.insert(first_row_index, rail_list)
        nav_group = next((node for node in controls.findall("control") if node.get("type") == "group" and node.find("./control[@id='1001']") is not None), None)
        if nav_group is not None:
            for button in nav_group.findall("./control[@type='button']"):
                # Text-first navigation: remove the heavy black button slabs.
                action_targets = {"1001": "9111", "1002": "9115", "1003": "9117"}
                if button.get("id") in action_targets:
                    set_child_text(button, "ondown", f"SetFocus({action_targets[button.get('id')]})")
                for tag, value in (("texturefocus", "focus-bar.png"), ("texturenofocus", "-"), ("textcolor", "lightgrey"), ("focusedcolor", "white"), ("align", "center"), ("aligny", "center")):
                    set_child_text(button, tag, value)
            # Keep a persistent red section marker under HOME even after focus
            # moves into the catalogue, so users never lose their location.
            old_marker = nav_group.find("./control[@id='9201']")
            if old_marker is not None:
                nav_group.remove(old_marker)
            active_marker = ET.Element("control", {"type": "image", "id": "9201"})
            for tag, value in (("left", 34), ("top", 42), ("width", 62), ("height", 4)):
                set_child_text(active_marker, tag, value)
            set_child_text(active_marker, "texture", "focus-bar.png")
            set_child_text(active_marker, "visible", "Window.IsActive(home)")
            nav_group.append(active_marker)
        # The top navigation already has a My Widgets destination. The extra
        # floating button obscured the fourth shelf and is intentionally removed.
        for control in list(controls):
            if control.get("id") == "9010" or control.findtext("label") == "MORE WIDGETS  ›":
                controls.remove(control)
    elif path == "skin.cineva/xml/Includes.xml":
        normal = root.find("./include[@name='CinevaPosterItem']")
        focused = root.find("./include[@name='CinevaFocusedPosterItem']")
        if normal is None or focused is None:
            raise SystemExit("Includes.xml is missing CINÉVA poster layouts")
        normal_image = normal.find("./control[@type='image']")
        normal_label = normal.find("./control[@type='label']")
        focused_image = focused.find("./control[@type='image']")
        focused_label = focused.find("./control[@type='label']")
        progress = focused.find("./control[@type='progress']")
        if any(node is None for node in (normal_image, normal_label, focused_image, progress)):
            raise SystemExit("Includes.xml has an incomplete poster layout")
        if focused_label is None:
            focused_label = ET.fromstring(ET.tostring(normal_label, encoding="unicode"))
        for tag, value in (("left", 33), ("top", 0), ("width", 156), ("height", 234)):
            set_child_text(normal_image, tag, value)
        for tag, value in (("left", 0), ("top", 236), ("width", 222), ("height", 34), ("align", "center"), ("font", "font9"), ("textcolor", "lightgrey")):
            set_child_text(normal_label, tag, value)
        stale_visibility = normal_label.find("visible")
        if stale_visibility is not None:
            normal_label.remove(stale_visibility)
        set_child_text(normal_label, "wrapmultiline", "true")
        set_child_text(normal_label, "visible", "!ListItem.IsSelected")
        for tag, value in (("left", 29), ("top", -6), ("width", 164), ("height", 246)):
            set_child_text(focused_image, tag, value)
        focus_animation = focused_image.find("./animation[@effect='zoom']")
        if focus_animation is None:
            raise SystemExit("Includes.xml focused poster is missing its zoom animation")
        focus_animation.set("end", "108")
        focus_animation.set("time", "150")
        for tag, value in (("left", 33), ("width", 156), ("top", 225)):
            set_child_text(progress, tag, value)
        if focused_label is not None and focused_label in list(focused):
            focused.remove(focused_label)
        for container_id in (9001, 9002, 9003, 9004):
            include_name = f"CinevaFocusedPosterItem{container_id}"
            previous = root.find(f"./include[@name='{include_name}']")
            if previous is not None:
                root.remove(previous)
            clone = ET.fromstring(ET.tostring(focused, encoding="unicode"))
            clone.set("name", include_name)
            # A fixed list remembers a selected item even while another rail has
            # focus. Give that inactive selection its normal poster/title, and
            # show the zoom/border/bright title only in the actively focused rail.
            fallback_image = ET.fromstring(ET.tostring(normal_image, encoding="unicode"))
            active_image = ET.fromstring(ET.tostring(focused_image, encoding="unicode"))
            fallback_label = ET.fromstring(ET.tostring(normal_label, encoding="unicode"))
            active_label = ET.fromstring(ET.tostring(focused_label, encoding="unicode"))
            clone_progress = ET.fromstring(ET.tostring(progress, encoding="unicode"))
            set_child_text(fallback_image, "visible", f"!Control.HasFocus({container_id})")
            set_child_text(active_image, "visible", f"Control.HasFocus({container_id})")
            set_child_text(fallback_label, "visible", f"!Control.HasFocus({container_id})")
            for tag, value in (("left", 0), ("top", 236), ("width", 222), ("height", 34), ("align", "center"), ("font", "font9"), ("textcolor", "white")):
                set_child_text(active_label, tag, value)
            set_child_text(active_label, "wrapmultiline", "true")
            set_child_text(active_label, "visible", f"Control.HasFocus({container_id})")
            set_child_text(clone_progress, "visible", f"Control.HasFocus({container_id}) + ListItem.IsResumable")
            focus_accent = ET.Element("control", {"type": "image"})
            for tag, value in (("left", 33), ("top", 230), ("width", 156), ("height", 4)):
                set_child_text(focus_accent, tag, value)
            set_child_text(focus_accent, "texture", "focus-bar.png")
            set_child_text(focus_accent, "visible", f"Control.HasFocus({container_id})")
            for child in list(clone.findall("control")):
                clone.remove(child)
            for child in (fallback_image, active_image, fallback_label, active_label, clone_progress, focus_accent):
                clone.append(child)
            root.append(clone)
    elif path == "skin.cineva/xml/DialogConfirm.xml":
        default = root.find("defaultcontrol")
        if default is None:
            default = ET.Element("defaultcontrol")
            root.insert(0, default)
        # Runtime JSON-RPC confirms control 11 is Yes and control 10 is No.
        default.set("always", "true")
        default.text = "11"
        # The skin has no bundled default button textures. Supply explicit
        # textures and colors so Yes/No are actually visible in the modal.
        for button in root.findall(".//control[@type='button']"):
            values = {
                "texturefocus": "focus-bar.png",
                "texturenofocus": "black.png",
                "textcolor": "white",
                "focusedcolor": "white",
                "align": "center",
                "aligny": "center",
            }
            for tag, value in values.items():
                node = button.find(tag)
                if node is None:
                    node = ET.SubElement(button, tag)
                node.text = value
    elif path == "skin.cineva/xml/Startup.xml":
        # The old startup panel had no content but was the default focus target.
        root.clear()
        root.set("id", "12999")
        # Startup remains the topmost window after a skin switch unless it
        # explicitly hands off to Home. This leaves the Home UI underneath but
        # keeps currentwindow=Startup and prevents Home navigation focus.
        ET.SubElement(root, "onload").text = "ActivateWindow(Home)"
        controls = ET.SubElement(root, "controls")
        ET.SubElement(controls, "include").text = "CinevaBackground"
        ET.SubElement(controls, "include").text = "CinevaTopBar"
    elif path == "skin.cineva/xml/MyVideoNav.xml":
        # Unified cinematic catalogue: larger portrait cards, generous gutters,
        # restrained metadata and a full-width grid that uses the screen.
        panel = root.find("./controls/control[@type='panel']")
        if panel is not None:
            set_child_text(panel, "left", 54)
            set_child_text(panel, "top", 252)
            set_child_text(panel, "width", 1812)
            set_child_text(panel, "height", 790)
            for layout in panel.findall("./itemlayout") + panel.findall("./focusedlayout"):
                layout.set("width", "300")
                layout.set("height", "350")
                for child in layout.findall("control"):
                    if child.get("type") == "image":
                        set_child_text(child, "left", 34)
                        set_child_text(child, "top", 0)
                        set_child_text(child, "width", 220)
                        set_child_text(child, "height", 318)
                    elif child.get("type") == "label":
                        set_child_text(child, "left", 12)
                        set_child_text(child, "top", 320)
                        set_child_text(child, "width", 276)
                        set_child_text(child, "height", 28)
                        set_child_text(child, "align", "center")
        title = root.find("./controls/control[@type='label']")
        if title is not None:
            set_child_text(title, "left", 72)
            set_child_text(title, "top", 126)
            set_child_text(title, "font", "font30")
    elif path == "skin.cineva/xml/DialogVideoInfo.xml":
        # Full-bleed detail composition with readable copy and a clear primary action.
        for node in root.findall("./controls/control"):
            kind = node.get("type")
            if kind == "image":
                if node.findtext("texture", "").startswith("$INFO[ListItem.Art(poster)]"):
                    for tag, value in (("left", 1260), ("top", 116), ("width", 430), ("height", 650)):
                        set_child_text(node, tag, value)
            elif kind == "label":
                label = node.findtext("label", "")
                if "$INFO[ListItem.Label]" in label:
                    for tag, value in (("left", 100), ("top", 150), ("width", 1060), ("height", 100)):
                        set_child_text(node, tag, value)
                    set_child_text(node, "font", "font36")
                elif "$INFO[ListItem.Year]" in label:
                    for tag, value in (("left", 104), ("top", 270), ("width", 1040), ("height", 44)):
                        set_child_text(node, tag, value)
            elif kind == "textbox":
                for tag, value in (("left", 104), ("top", 350), ("width", 1000), ("height", 300)):
                    set_child_text(node, tag, value)
            elif kind == "button":
                for tag, value in (("left", 104), ("top", 760), ("width", 300), ("height", 70)):
                    set_child_text(node, tag, value)
                set_child_text(node, "font", "font16")
                set_child_text(node, "texturefocus", "focus-bar.png")
                set_child_text(node, "texturenofocus", "black.png")
                set_child_text(node, "textcolor", "white")
    elif path == "skin.cineva/xml/VideoOSD.xml":
        # Premium, low-profile playback overlay with a long seek bar and legible controls.
        for node in root.findall("./controls/control"):
            if node.get("type") == "image":
                set_child_text(node, "top", 720)
                set_child_text(node, "height", 360)
            elif node.get("type") == "label":
                set_child_text(node, "left", 80)
                if "$INFO[VideoPlayer.Title]" in node.findtext("label", ""):
                    set_child_text(node, "top", 770)
                    set_child_text(node, "font", "font20")
                else:
                    set_child_text(node, "top", 826)
            elif node.get("type") == "progress":
                set_child_text(node, "left", 80)
                set_child_text(node, "top", 880)
                set_child_text(node, "width", 1760)
            elif node.get("type") == "group":
                set_child_text(node, "left", 80)
                set_child_text(node, "top", 920)
                for button in node.findall("./control[@type='button']"):
                    set_child_text(button, "height", 64)
                    set_child_text(button, "texturefocus", "focus-bar.png")
                    set_child_text(button, "texturenofocus", "black.png")
                    set_child_text(button, "textcolor", "white")
    elif path == "skin.cineva/xml/custom11112.xml":
        # Search hub: keep the search action prominent and align results to the catalogue grid.
        for node in root.findall(".//control[@type='button']"):
            set_child_text(node, "texturefocus", "focus-bar.png")
            set_child_text(node, "texturenofocus", "black.png")
            set_child_text(node, "textcolor", "white")
            set_child_text(node, "focusedcolor", "white")
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True)


def main():
    if not ARCHIVE.is_file() or ARCHIVE.stat().st_size == 0:
        raise SystemExit("Missing skin.cineva-0.5.3.zip")
    fd, tmp_name = tempfile.mkstemp(prefix="cineva-skin-", suffix=".zip", dir=str(ARCHIVE.parent))
    os.close(fd)
    tmp = Path(tmp_name)
    changed = []
    try:
        with ZipFile(ARCHIVE, "r") as source, ZipFile(tmp, "w", ZIP_DEFLATED, compresslevel=9) as target:
            names = set(source.namelist())
            required = {
                "skin.cineva/addon.xml",
                "skin.cineva/xml/Home.xml",
                "skin.cineva/xml/DialogConfirm.xml",
                "skin.cineva/xml/Includes.xml",
                "skin.cineva/xml/MyVideoNav.xml",
                "skin.cineva/xml/DialogVideoInfo.xml",
                "skin.cineva/xml/VideoOSD.xml",
                "skin.cineva/xml/custom11112.xml",
                "skin.cineva/xml/Startup.xml",
            }
            missing = sorted(required - names)
            if missing:
                raise SystemExit("Skin archive is missing: " + ", ".join(missing))
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename in required:
                    updated = update_xml(data, info.filename)
                    if updated != data:
                        changed.append(info.filename)
                    data = updated
                target.writestr(info, data)
        if changed:
            os.replace(tmp, ARCHIVE)
            print("Updated release ZIP entries:", ", ".join(changed))
        else:
            print("Release ZIP already contains all runtime fixes; no rewrite needed.")
    finally:
        if tmp.exists():
            tmp.unlink()


if __name__ == "__main__":
    main()
