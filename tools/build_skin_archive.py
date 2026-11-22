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
        # Three rails are intentionally visible on a 1080p screen; the fourth
        # remains reachable by vertical navigation instead of shrinking cards.
        controls = root.find("controls")
        if controls is None:
            raise SystemExit("Home.xml is missing its controls container")
        # Cinematic hero: give artwork room to breathe and fade it cleanly into the catalogue.
        for control in controls.findall("control"):
            if control.get("type") == "image" and control.findtext("texture", "").startswith("$INFO[Container("):
                set_child_text(control, "height", 440)
            if control.get("type") == "image" and control.findtext("texture") == "hero-shade.png":
                set_child_text(control, "height", 490)
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
                set_child_text(group, "top", 136)
                labels = [child for child in group.findall("control") if child.get("type") == "label"]
                if labels:
                    # Title first, metadata second: separate vertical baselines.
                    set_child_text(labels[0], "top", 62)
                    set_child_text(labels[0], "font", "font36")
                    set_child_text(labels[0], "height", 64)
                if len(labels) > 1:
                    set_child_text(labels[1], "top", 30)
                    set_child_text(labels[1], "height", 30)
                for child in group.findall("control"):
                    if child.get("type") == "textbox":
                        set_child_text(child, "top", 132)
                        set_child_text(child, "height", 92)
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "width", 1200)
        # Three compact, consistently spaced catalogue rails; no giant dead zone between rows.
        row_positions = ((370, 406), (715, 751), (1060, 1096), (1405, 1441))
        for index, (heading_top, shelf_top) in enumerate(row_positions, 1):
            heading_label = f"$INFO[Skin.String(Cineva.Widget{index}.Name)]"
            heading = next((c for c in controls.findall("control")
                            if c.get("type") == "label" and c.findtext("label") == heading_label), None)
            shelf = controls.find(f"./control[@type='fixedlist'][@id='{9000 + index}']")
            if heading is None or shelf is None:
                raise SystemExit(f"Home.xml is missing widget row {index}")
            set_child_text(heading, "top", heading_top)
            set_child_text(heading, "height", 32)
            set_child_text(heading, "font", "font16")
            set_child_text(shelf, "top", shelf_top)
            set_child_text(shelf, "height", 245)
            for layout in shelf.findall("./itemlayout") + shelf.findall("./focusedlayout"):
                layout.set("width", "270")
                layout.set("height", "300")
                for child in layout.findall("control"):
                    if child.get("type") == "image":
                        set_child_text(child, "left", 30)
                        set_child_text(child, "width", 190)
                        set_child_text(child, "height", 276)
                    elif child.get("type") == "label":
                        set_child_text(child, "left", 0)
                        set_child_text(child, "top", 280)
                        set_child_text(child, "width", 270)
                        set_child_text(child, "height", 24)
                        set_child_text(child, "align", "center")
        nav_group = next((node for node in controls.findall("control") if node.get("type") == "group" and node.find("./control[@id='1001']") is not None), None)
        if nav_group is not None:
            for button in nav_group.findall("./control[@type='button']"):
                # Text-first navigation: remove the heavy black button slabs.
                for tag, value in (("texturefocus", "focus-bar.png"), ("texturenofocus", "-"), ("textcolor", "lightgrey"), ("focusedcolor", "white"), ("align", "center"), ("aligny", "center")):
                    set_child_text(button, tag, value)
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
        if any(node is None for node in (normal_image, normal_label, focused_image, focused_label, progress)):
            raise SystemExit("Includes.xml has an incomplete poster layout")
        for tag, value in (("left", 30), ("width", 190), ("height", 276)):
            set_child_text(normal_image, tag, value)
        for tag, value in (("left", 0), ("top", 280), ("width", 270), ("height", 24), ("align", "center")):
            set_child_text(normal_label, tag, value)
        for tag, value in (("left", 25), ("top", -7), ("width", 200), ("height", 290)):
            set_child_text(focused_image, tag, value)
        for tag, value in (("left", 0), ("top", 292), ("width", 270), ("height", 22), ("align", "center")):
            set_child_text(focused_label, tag, value)
        set_child_text(progress, "left", 30)
        set_child_text(progress, "width", 190)
        set_child_text(progress, "top", 266)
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
