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
                set_child_text(control, "height", 500)
            if control.get("type") == "image" and control.findtext("texture") == "hero-shade.png":
                set_child_text(control, "height", 510)
        for group in controls.findall("control"):
            if group.get("type") == "group" and group.findtext("control/label", "").startswith("$INFO[Container("):
                set_child_text(group, "top", 145)
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
                set_child_text(group, "width", 1120)
        row_positions = ((470, 505), (725, 760), (980, 1015), (1235, 1270))
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
            set_child_text(shelf, "height", 230)
            for layout in shelf.findall("./itemlayout") + shelf.findall("./focusedlayout"):
                layout.set("width", "190")
                layout.set("height", "230")
                for child in layout.findall("control"):
                    if child.get("type") == "image":
                        set_child_text(child, "width", 160)
                        set_child_text(child, "height", 190)
                    elif child.get("type") == "label":
                        set_child_text(child, "top", 194)
                        set_child_text(child, "height", 28)
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
        for tag, value in (("width", 160), ("height", 190)):
            set_child_text(normal_image, tag, value)
        for tag, value in (("top", 194), ("height", 28)):
            set_child_text(normal_label, tag, value)
        for tag, value in (("left", -6), ("top", -6), ("width", 172), ("height", 202)):
            set_child_text(focused_image, tag, value)
        for tag, value in (("left", -2), ("top", 204), ("width", 168), ("height", 24)):
            set_child_text(focused_label, tag, value)
        set_child_text(progress, "top", 184)
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
