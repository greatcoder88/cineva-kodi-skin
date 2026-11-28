#!/usr/bin/env python3
"""Package the Nimbus-based Frame skin and helper under separate Kodi add-on IDs."""

import argparse
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from build_nimbus_base import (
    extract_archive, fetch_archive, patch_nimbus_timer_start_conditions, write_deterministic_zip,
)
from frame_theme import apply_theme


ROOT = Path(__file__).resolve().parents[1]
THEME_SOURCE = ROOT / "tools/frame-theme/Includes_FrameTheme.xml"
SKIN_ID = "skin.frame"
SKIN_VERSION = "0.1.59"
HELPER_VERSION = "0.0.54"
HELPER_ID = "script.frame.nimbus"
ADDONS = (
    ("ivarbrandt/skin.nimbus", "8b5071b8cd0db3a8e813eb00e9a821d3efad2454", SKIN_ID, "Frame"),
    ("ivarbrandt/script.nimbus.helper", "e42d2ffffbccaa58386ef2e4a054049e5fcb7664", HELPER_ID, "Frame Nimbus Helper"),
)


def package_addon(archive, root, output, addon_id, name):
    extract_archive(archive, root)
    manifest_path = root / "addon.xml"
    upstream_name = ET.parse(manifest_path).getroot().attrib["name"].encode()
    for path in root.rglob("*"):
        if path.suffix not in {".xml", ".py"} or not path.is_file():
            continue
        original = path.read_bytes()
        contents = original.replace(b"script.nimbus.helper", HELPER_ID.encode())
        contents = contents.replace(b"skin.nimbus", SKIN_ID.encode())
        if addon_id == SKIN_ID and path.name in {"Includes_Home.xml", "SkinSettings.xml"}:
            # Kodi registers the custom welcome window relative to Home (10000).
            contents = contents.replace(b"ActivateWindow(1112)", b"ActivateWindow(11112)")
        if path.suffix == ".xml" and addon_id == SKIN_ID:
            contents = contents.replace(b"ActivateWindow(1107)", b"ActivateWindow(11107)")
            contents = contents.replace(b"Window.IsActive(1121)", b"Window.IsActive(11121)")
            contents = contents.replace(b"Window.IsVisible(1121)", b"Window.IsVisible(11121)")
        if addon_id == HELPER_ID and path.name == "search_utils.py":
            contents = contents.replace(b"ActivateWindow(1121)", b"ActivateWindow(11121)")
        if path == manifest_path:
            contents = contents.replace(b'name="' + upstream_name + b'"',
                                        b'name="' + name.encode() + b'"', 1)
        if path.suffix == ".xml":
            ET.fromstring(contents)
        else:
            compile(contents, str(path), "exec")
        if contents != original:
            path.write_bytes(contents)

    manifest = ET.parse(manifest_path).getroot()
    if manifest.get("id") != addon_id or manifest.get("name") != name:
        raise RuntimeError(f"Unexpected manifest identity for {addon_id}")
    if addon_id == SKIN_ID and manifest.find(f"./requires/import[@addon='{HELPER_ID}']") is None:
        raise RuntimeError(f"{SKIN_ID} must depend on {HELPER_ID}")
    if addon_id == SKIN_ID:
        manifest.attrib["version"] = SKIN_VERSION
        manifest.find(f"./requires/import[@addon='{HELPER_ID}']").set("version", HELPER_VERSION)
        ET.ElementTree(manifest).write(manifest_path, encoding="utf-8", xml_declaration=True)
        patch_nimbus_timer_start_conditions(root)
        apply_theme(root, THEME_SOURCE)
    else:
        manifest.set("version", HELPER_VERSION)
        extension = ET.SubElement(manifest, "extension", {
            "point": "xbmc.python.pluginsource", "library": "resources/lib/playback_tracks.py",
        })
        ET.SubElement(extension, "provides").text = "executable"
        source = THEME_SOURCE.with_name("playback_tracks.py").read_bytes()
        target = root / "resources/lib/playback_tracks.py"
        compile(source, str(target), "exec")
        target.write_bytes(source)
        ET.ElementTree(manifest).write(manifest_path, encoding="utf-8", xml_declaration=True)

    destination = output / f"{addon_id}-{manifest.attrib['version']}.zip"
    write_deterministic_zip(root, destination)
    with ZipFile(destination) as package:
        corrupt_member = package.testzip()
        if corrupt_member is not None:
            raise RuntimeError(f"Invalid ZIP member in {destination.name}: {corrupt_member}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "frame")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="frame-build-") as workspace:
        for repository, commit, addon_id, name in ADDONS:
            source = fetch_archive(repository, commit)
            path = package_addon(source, Path(workspace) / addon_id, args.output, addon_id, name)
            print(f"Built and verified {path}", flush=True)


if __name__ == "__main__":
    main()
