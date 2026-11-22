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
        for control in controls.findall("control"):
            if control.get("type") == "image" and control.findtext("texture", "").startswith("$INFO[Container("):
                set_child_text(control, "height", 420)
            if control.get("type") == "image" and control.findtext("texture") == "hero-shade.png":
                set_child_text(control, "height", 440)
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
                set_child_text(group, "top", 128)
                labels = [child for child in group.findall("control") if child.get("type") == "label"]
                if labels:
                    # Title first, metadata second: separate vertical baselines.
                    set_child_text(labels[0], "top", 62)
                    set_child_text(labels[0], "font", "font36")
                    set_child_text(labels[0], "height", 58)
                if len(labels) > 1:
                    set_child_text(labels[1], "top", 34)
                    set_child_text(labels[1], "height", 28)
                for child in group.findall("control"):
                    if child.get("type") == "textbox":
                        set_child_text(child, "top", 130)
                        set_child_text(child, "height", 100)
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "width", 1200)
        row_positions = ((450, 488), (760, 798), (1070, 1108), (1380, 1418))
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
            set_child_text(shelf, "height", 260)
            for layout in shelf.findall("./itemlayout") + shelf.findall("./focusedlayout"):
                layout.set("width", "220")
                layout.set("height", "260")
                for child in layout.findall("control"):
                    if child.get("type") == "image":
                        set_child_text(child, "left", 20)
                        set_child_text(child, "width", 180)
                        set_child_text(child, "height", 225)
                    elif child.get("type") == "label":
                        set_child_text(child, "left", 0)
                        set_child_text(child, "top", 230)
                        set_child_text(child, "width", 220)
                        set_child_text(child, "height", 26)
                        set_child_text(child, "align", "center")
        nav_group = next((node for node in controls.findall("control") if node.get("type") == "group" and node.find("./control[@id='1001']") is not None), None)
        if nav_group is not None:
            for button in nav_group.findall("./control[@type='button']"):
                for tag, value in (("texturefocus", "focus-bar.png"), ("texturenofocus", "black.png"), ("textcolor", "white"), ("focusedcolor", "white"), ("align", "center"), ("aligny", "center")):
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
        for tag, value in (("left", 20), ("width", 180), ("height", 225)):
            set_child_text(normal_image, tag, value)
        for tag, value in (("left", 0), ("top", 230), ("width", 220), ("height", 26), ("align", "center")):
            set_child_text(normal_label, tag, value)
        for tag, value in (("left", 22), ("top", -6), ("width", 196), ("height", 241)):
            set_child_text(focused_image, tag, value)
        for tag, value in (("left", 0), ("top", 242), ("width", 220), ("height", 26), ("align", "center")):
            set_child_text(focused_label, tag, value)
        set_child_text(progress, "left", 20)
        set_child_text(progress, "width", 180)
        set_child_text(progress, "top", 214)
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
