#!/usr/bin/env python3
"""Build the distributable CINÉVA ZIP with runtime-critical XML fixes."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os
import tempfile
import xml.etree.ElementTree as ET

ARCHIVE = Path(__file__).resolve().parents[1] / "skin.cineva-0.5.3.zip"


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
    elif path == "skin.cineva/xml/DialogConfirm.xml":
        default = root.find("defaultcontrol")
        if default is None:
            default = ET.Element("defaultcontrol")
            root.insert(0, default)
        # Kodi DialogConfirm: control 10 is Yes ($LOCALIZE[186]); 11 is No.
        default.text = "10"
    elif path == "skin.cineva/xml/Startup.xml":
        # The old startup panel had no content but was the default focus target.
        root.clear()
        root.set("id", "12999")
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
