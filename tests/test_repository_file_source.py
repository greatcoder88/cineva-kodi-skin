import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from tools import build_repository


class AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.label = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.label).strip()))
            self.href = None
            self.label = []


def read_links(path):
    parser = AnchorParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return set(parser.links)


class RepositoryFileSourceTests(unittest.TestCase):
    def test_root_source_exposes_repository_installer_and_browsable_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            output = temp_root / "repository-site"
            build_dir = temp_root / "dist" / "nimbus-foundation"
            build_dir.mkdir(parents=True)
            skin = build_dir / "skin.cineva-0.8.2-nimbus.zip"
            bridge = build_dir / "script.cineva.nimbus-0.1.1.zip"
            for archive_path, addon_id, version in (
                (skin, "skin.cineva", "0.8.2"),
                (bridge, "script.cineva.nimbus", "0.1.1"),
            ):
                with ZipFile(archive_path, "w") as archive:
                    manifest = f'<addon id="{addon_id}" version="{version}" name="{addon_id}"/>'
                    archive.writestr(f"{addon_id}/addon.xml", manifest)
            with patch.object(build_repository, "OUT", output), patch.object(build_repository, "ROOT", temp_root):
                build_repository.main()

            installer_name = f"repository.cineva-{build_repository.REPO_VERSION}.zip"
            self.assertIn(
                (installer_name, installer_name),
                read_links(output / "index.html"),
            )
            self.assertIn(("zips/", "zips/"), read_links(output / "index.html"))

            package_ids = (
                "repository.cineva",
                "skin.cineva",
                "script.cineva.nimbus",
            )
            expected_folders = {(f"{name}/", f"{name}/") for name in package_ids}
            self.assertTrue(expected_folders.issubset(read_links(output / "zips/index.html")))

            nested_installer = output / "zips/repository.cineva" / installer_name
            root_installer = output / installer_name
            self.assertEqual(root_installer.read_bytes(), nested_installer.read_bytes())

            for addon_id in package_ids:
                directory = output / "zips" / addon_id
                zip_files = sorted(directory.glob("*.zip"))
                self.assertTrue(zip_files, f"{addon_id} has no installable ZIP")
                visible_links = read_links(directory / "index.html")
                for package in zip_files:
                    self.assertIn((package.name, package.name), visible_links)

            with ZipFile(root_installer) as archive:
                manifest = ET.fromstring(archive.read("repository.cineva/addon.xml"))
            extension = manifest.find("./extension[@point='xbmc.addon.repository']")
            base = "https://greatcoder88.github.io/cineva-kodi-skin"
            self.assertIsNotNone(extension)
            directory = extension.find("dir")
            self.assertIsNotNone(directory)
            self.assertEqual(directory.findtext("info"), f"{base}/addons.xml")
            self.assertEqual(directory.findtext("checksum"), f"{base}/addons.xml.md5")
            datadir = directory.find("datadir")
            self.assertIsNotNone(datadir)
            self.assertEqual(datadir.text, f"{base}/zips/")
            self.assertEqual(datadir.get("zip"), "true")


if __name__ == "__main__":
    unittest.main()
