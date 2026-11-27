#!/usr/bin/env python3
"""Package the stock Nimbus baseline under Frame's separate Kodi add-on IDs."""

import argparse
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from build_nimbus_base import extract_archive, fetch_archive, write_deterministic_zip


ROOT = Path(__file__).resolve().parents[1]
SKIN_ID = "skin.frame"
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
