import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.52.zip"


class SettingsCategoryTests(unittest.TestCase):
    def test_interface_settings_window_contains_kodis_dynamic_control_templates(self):
        with ZipFile(ARCHIVE) as archive:
            root = ET.fromstring(archive.read("skin.cineva/xml/SettingsCategory.xml"))
            settings = ET.fromstring(archive.read("skin.cineva/xml/Settings.xml"))

        self.assertEqual(root.findtext("defaultcontrol"), "3")
        self.assertIsNotNone(root.find("./controls/include[.='CinevaBackground']"))
        self.assertIsNotNone(root.find("./controls/include[.='CinevaTopBar']"))
        self.assertIsNotNone(root.find(".//control[@type='grouplist'][@id='3']"))
        settings_list = root.find(".//control[@type='grouplist'][@id='5']")
        self.assertIsNotNone(settings_list)
        self.assertEqual(settings_list.findtext("pagecontrol"), "60")
        self.assertNotIn("DefaultSettingButton", [node.text for node in root.findall(".//include") if node.text])

        for control_id, control_type in (
            ("7", "button"), ("8", "radiobutton"), ("9", "spincontrolex"),
            ("10", "button"), ("11", "image"), ("13", "sliderex"),
            ("14", "label"), ("15", "colorbutton"), ("20", "radiobutton"),
            ("60", "scrollbar"), ("6", "textbox"), ("2", "label"),
        ):
            self.assertIsNotNone(
                root.find(f".//control[@id='{control_id}'][@type='{control_type}']"),
                f"Missing Kodi SettingsCategory control {control_type} id={control_id}",
            )

        interface = settings.find(".//control[@id='11404']")
        self.assertIsNotNone(interface)
        self.assertEqual(interface.findtext("onclick"), "ActivateWindow(InterfaceSettings)")


if __name__ == "__main__":
    unittest.main()
