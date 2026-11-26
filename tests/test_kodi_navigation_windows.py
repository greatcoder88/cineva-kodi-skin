import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.35.zip"
XML = "skin.cineva/xml/"


class KodiNavigationWindowTests(unittest.TestCase):
    def test_media_windows_register_their_real_directory_view(self):
        with ZipFile(ARCHIVE) as archive:
            for filename in ("MyVideoNav.xml", "MyMusicNav.xml", "MyPrograms.xml", "FileManager.xml"):
                root = ET.fromstring(archive.read(XML + filename))
                self.assertEqual(root.findtext("views"), "50", filename)
                self.assertEqual(root.findtext("defaultcontrol"), "50", filename)
                self.assertIsNotNone(
                    root.find(".//control[@type='panel'][@id='50']"),
                    f"{filename} must contain the registered native panel",
                )

    def test_dialog_default_focus_matches_existing_controls(self):
        with ZipFile(ARCHIVE) as archive:
            for filename in ("FileBrowser.xml", "DialogAddonSettings.xml"):
                root = ET.fromstring(archive.read(XML + filename))
                focus_id = root.findtext("defaultcontrol")
                self.assertEqual(focus_id, "3", filename)
                self.assertIsNotNone(
                    root.find(f".//control[@id='{focus_id}']"),
                    f"{filename} default focus must point to a real control",
                )

            addon_info = ET.fromstring(archive.read(XML + "DialogAddonInfo.xml"))
            self.assertEqual(addon_info.findtext("defaultcontrol"), "9000")
            action_group = addon_info.find(".//control[@type='grouplist'][@id='9000']")
            self.assertIsNotNone(action_group, "Add-on information needs a focusable action group")
            for control_id in ("12", "9", "10", "7", "8", "14", "6"):
                self.assertIsNotNone(
                    action_group.find(f"./control[@id='{control_id}']"),
                    f"Missing native Kodi add-on action control {control_id}",
                )


if __name__ == "__main__":
    unittest.main()
