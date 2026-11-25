#!/usr/bin/env python3
"""Assemble a Kodi add-on repository from the tested CINÉVA packages."""
from __future__ import annotations
import hashlib
import html
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "repository-site"
REPO_ID = "repository.cineva"
REPO_VERSION = "0.1.4"
FEED_BASE = "https://greatcoder88.github.io/cineva-kodi-skin"


def addon_xml_from_zip(path: Path) -> tuple[str, bytes]:
    with ZipFile(path) as archive:
        candidates = [n for n in archive.namelist() if n.endswith("/addon.xml")]
        if len(candidates) != 1:
            raise RuntimeError(f"{path}: expected one addon.xml, found {candidates}")
        raw = archive.read(candidates[0])
    root = ET.fromstring(raw)
    return root.attrib["id"], raw


def zip_directory(source: Path, destination: Path, root_name: str) -> None:
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, f"{root_name}/{path.relative_to(source).as_posix()}")


def write_http_directory_index(directory: Path, title: str, entries: list[tuple[str, str]]) -> None:
    """Write the Apache-style autoindex format Kodi HTTPDirectory recognizes."""
    lines = ['<a href="../">../</a>']
    for href, label in entries:
        # Kodi's HTTPDirectory parser expects Apache autoindex-style anchors
        # inside PRE, with visible link text matching the relative href.
        lines.append(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')
    page = (
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">'
        '<html><head><title>Index of /</title></head><body>'
        f'<h1>Index of {html.escape(title)}</h1><hr><pre>'
        + "\n".join(lines)
        + '</pre><hr></body></html>'
    )
    (directory / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    skin_zip = ROOT / "skin.cineva-0.5.28.zip"
    helper_dir = ROOT / "tools/script.cineva.widgets"
    if not skin_zip.is_file():
        raise SystemExit("Build the skin ZIP before assembling the repository.")
    OUT.mkdir(exist_ok=True)
    zips = OUT / "zips"
    for child in (zips,):
        if child.exists():
            shutil.rmtree(child)
        child.mkdir(parents=True)
    skin_id, skin_xml = addon_xml_from_zip(skin_zip)
    helper_xml_path = helper_dir / "addon.xml"
    helper_root = ET.parse(helper_xml_path).getroot()
    helper_id = helper_root.attrib["id"]
    if skin_id != "skin.cineva" or helper_id != "script.cineva.widgets":
        raise SystemExit(f"Unexpected add-on IDs: {skin_id}, {helper_id}")
    helper_version = helper_root.attrib["version"]
    skin_root = ET.fromstring(skin_xml)
    skin_version = skin_root.attrib["version"]
    expected_skin_version = "0.5.28"
    if skin_version != expected_skin_version:
        raise SystemExit(
            f"Skin archive manifest version is {skin_version!r}; "
            f"expected {expected_skin_version!r}. Rebuild the release archive first."
        )
    if skin_zip.name != f"{skin_id}-{skin_version}.zip":
        raise SystemExit(f"Skin archive filename/version mismatch: {skin_zip.name}")
    packages = [
        (skin_id, skin_version, skin_zip),
        (helper_id, helper_version, None),
    ]
    helper_zip = zips / helper_id / f"{helper_id}-{helper_version}.zip"
    helper_zip.parent.mkdir(parents=True)
    skin_package_dir = zips / skin_id
    skin_package_dir.mkdir(parents=True)
    zip_directory(helper_dir, helper_zip, helper_id)
    # Preserve the exact tested release archive name; do not silently publish
    # a differently-versioned package based on stale manifest metadata.
    shutil.copy2(skin_zip, skin_package_dir / skin_zip.name)
    addons = ET.Element("addons")
    for addon_id, version, package in packages:
        raw = skin_xml if addon_id == skin_id else helper_xml_path.read_bytes()
        node = ET.fromstring(raw)
        addons.append(node)
    ET.indent(addons, space="  ")
    addons_bytes = ET.tostring(addons, encoding="utf-8", xml_declaration=True)
    (OUT / "addons.xml").write_bytes(addons_bytes)
    (OUT / "addons.xml.md5").write_text(hashlib.md5(addons_bytes).hexdigest(), encoding="ascii")
    (OUT / ".nojekyll").write_text("", encoding="ascii")
    repo_dir = OUT / "zips" / REPO_ID
    repo_dir.mkdir(parents=True)
    repo_addon = ET.Element("addon", {
        "id": REPO_ID, "name": "CINÉVA Add-on Repository",
        "version": REPO_VERSION, "provider-name": "CINÉVA"
    })
    repository_extension = ET.SubElement(repo_addon, "extension", {
        "point": "xbmc.addon.repository", "name": "CINÉVA Repository"
    })
    directory = ET.SubElement(repository_extension, "dir")
    ET.SubElement(directory, "info").text = f"{FEED_BASE}/addons.xml"
    ET.SubElement(directory, "checksum").text = f"{FEED_BASE}/addons.xml.md5"
    ET.SubElement(directory, "datadir", {"zip": "true"}).text = f"{FEED_BASE}/zips/"
    metadata = ET.SubElement(repo_addon, "extension", {"point": "xbmc.addon.metadata"})
    ET.SubElement(metadata, "summary", {"lang": "en_GB"}).text = "Official CINÉVA add-on repository"
    ET.SubElement(metadata, "description", {"lang": "en_GB"}).text = "Install and update CINÉVA skin and widget helper."
    ET.SubElement(metadata, "platform").text = "all"
    ET.indent(repo_addon, space="  ")
    repo_xml = ET.tostring(repo_addon, encoding="utf-8", xml_declaration=True)
    (repo_dir / "addon.xml").write_bytes(repo_xml)
    with ZipFile(repo_dir / f"{REPO_ID}-{REPO_VERSION}.zip", "w", ZIP_DEFLATED) as archive:
        archive.write(repo_dir / "addon.xml", f"{REPO_ID}/addon.xml")
    repo_zip = repo_dir / f"{REPO_ID}-{REPO_VERSION}.zip"
    # Put the installer at the source root so the standard Kodi file-source
    # workflow is one level deep: Add source -> Install from ZIP -> Install from repo.
    shutil.copy2(repo_zip, OUT / repo_zip.name)
    write_http_directory_index(
        OUT,
        "CINÉVA Kodi Repository",
        [(repo_zip.name, repo_zip.name), ("zips/", "zips/")],
    )
    package_ids = (REPO_ID, skin_id, helper_id)
    write_http_directory_index(
        zips,
        "CINÉVA add-on packages",
        [(f"{addon_id}/", f"{addon_id}/") for addon_id in package_ids],
    )
    for addon_id in package_ids:
        package_dir = zips / addon_id
        package_files = sorted(path.name for path in package_dir.glob("*.zip"))
        write_http_directory_index(
            package_dir,
            f"CINÉVA {addon_id} packages",
            [(name, name) for name in package_files],
        )
    print(f"Repository assembled: {OUT}")
    print(f"Packages: {skin_id}-{skin_version}, {helper_id}-{helper_version}, {REPO_ID}-{REPO_VERSION}")


if __name__ == "__main__":
    main()
