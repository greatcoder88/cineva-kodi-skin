import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.6.zip"
HUB_WINDOW = "skin.cineva/xml/CinevaWidgetHub.xml"


class HomeNavigationTests(unittest.TestCase):
    def test_home_uses_per_screen_settings_without_a_separate_widget_hub(self):
        self.assertTrue(ARCHIVE.is_file(), "release skin archive must be built before this test")
        with ZipFile(ARCHIVE) as archive:
            names = set(archive.namelist())
            self.assertNotIn(HUB_WINDOW, names, "legacy standalone widget hub must not ship")
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))

        nav = next(
            node for node in home.findall("./controls/control")
            if node.get("type") == "group"
            and node.find("./control[@id='1001']") is not None
        )
        buttons = {
            button.get("id"): button
            for button in nav.findall("./control[@type='button']")
        }
        self.assertNotIn("1006", buttons, "obsolete navigation control must not remain")
        self.assertIn("1005", buttons, "Settings must occupy the reclaimed navigation slot")
        self.assertEqual(buttons["1005"].findtext("label"), "SETTINGS")
        self.assertEqual(buttons["1005"].findtext("left"), "670")
        self.assertFalse(
            any((button.findtext("label") or "").strip().upper() == "MY WIDGETS"
                for button in buttons.values())
        )
        self.assertNotIn("ActivateWindow(11119)", ET.tostring(home, encoding="unicode"))


if __name__ == "__main__":
    unittest.main()
