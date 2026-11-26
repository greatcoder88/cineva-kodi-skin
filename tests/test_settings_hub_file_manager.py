import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.50.zip"


class SettingsHubFileManagerTests(unittest.TestCase):
    def test_settings_hub_exposes_native_file_manager_with_dpad_access(self):
        with ZipFile(ARCHIVE) as archive:
            settings = ET.fromstring(archive.read("skin.cineva/xml/Settings.xml"))
            file_manager = ET.fromstring(archive.read("skin.cineva/xml/FileManager.xml"))

        button = settings.find(".//control[@type='button'][@id='11409']")
        self.assertIsNotNone(button, "Settings hub must expose a ninth File Manager tile")
        self.assertEqual(button.findtext("label"), "FILE MANAGER")
        self.assertEqual(button.findtext("onclick"), "ActivateWindow(FileManager)")
        self.assertEqual(button.findtext("onup"), "SetFocus(11407)")
        self.assertEqual(button.findtext("ondown"), "SetFocus(11401)")
        self.assertEqual(button.findtext("onleft"), "SetFocus(11408)")
        self.assertEqual(button.findtext("onright"), "SetFocus(11401)")

        system_info = settings.find(".//control[@type='button'][@id='11407']")
        self.assertEqual(system_info.findtext("ondown"), "SetFocus(11409)")
        self.assertEqual(file_manager.findtext("views"), "50")
        self.assertIsNotNone(file_manager.find(".//control[@type='panel'][@id='50']"))

        ids = [node.get("id") for node in settings.findall(".//control") if node.get("id")]
        self.assertEqual(len(ids), len(set(ids)), "Settings hub control IDs must be unique")


if __name__ == "__main__":
    unittest.main()
