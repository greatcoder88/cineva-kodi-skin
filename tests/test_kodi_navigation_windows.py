import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.38.zip"
XML = "skin.cineva/xml/"


class KodiNavigationWindowTests(unittest.TestCase):
    def test_media_windows_register_their_real_directory_view(self):
        with ZipFile(ARCHIVE) as archive:
            for filename in ("MyVideoNav.xml", "MyMusicNav.xml", "MyPrograms.xml", "FileManager.xml"):
                root = ET.fromstring(archive.read(XML + filename))
                self.assertEqual(root.findtext("views"), "50", filename)
                if filename == "MyVideoNav.xml":
                    self.assertEqual(root.findtext("defaultcontrol"), "49", filename)
                    default_control = root.find("defaultcontrol")
                    self.assertNotIn("always", default_control.attrib)
                    back_control = root.find("./controls/control[@type='button'][@id='49']")
                    self.assertIsNotNone(back_control, "MyVideoNav needs a safe focus target while plugins load")
                    self.assertEqual(back_control.findtext("label"), "BACK TO ADD-ONS")
                    self.assertEqual(back_control.findtext("onclick"), "PreviousMenu")
                    self.assertEqual(
                        [(node.get("condition"), node.text) for node in back_control.findall("ondown")],
                        [
                            ("!String.IsEmpty(Container(50).ListItem.Label)", "SetFocus(50)"),
                            (None, "SetFocus(49)"),
                        ],
                    )
                else:
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
            self.assertIn(
                "ListItem.AddonName",
                addon_info.findtext("./controls/control[@type='label']/label", ""),
            )
            self.assertIn(
                "ListItem.AddonDescription",
                addon_info.findtext("./controls/control[@type='textbox']/label", ""),
            )
            action_group = addon_info.find(".//control[@type='grouplist'][@id='9000']")
            self.assertIsNotNone(action_group, "Add-on information needs a focusable action group")
            for control_id in ("12", "9", "10", "7", "8", "14", "6"):
                self.assertIsNotNone(
                    action_group.find(f"./control[@id='{control_id}']"),
                    f"Missing native Kodi add-on action control {control_id}",
                )


if __name__ == "__main__":
    unittest.main()
