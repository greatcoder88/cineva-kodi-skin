import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.7.zip"
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


    def test_movies_and_tv_catalogue_navigation_exposes_real_library_destinations(self):
        expected = {
            "custom11117.xml": {
                "1001": ("HOME", "ActivateWindow(Home)"),
                "1002": ("MOVIES", "ActivateWindow(11117)"),
                "1003": ("TV SHOWS", "ActivateWindow(11118)"),
                "1004": ("ALL MOVIES", "ActivateWindow(Videos,videodb://movies/titles/,return)"),
                "1005": ("GENRES", "ActivateWindow(Videos,videodb://movies/genres/,return)"),
                "1006": ("YEARS", "ActivateWindow(Videos,videodb://movies/years/,return)"),
                "1007": ("COLLECTIONS", "ActivateWindow(Videos,videodb://movies/sets/,return)"),
                "1008": ("RECENT", "ActivateWindow(Videos,videodb://movies/recentlyaddedmovies/,return)"),
                "1009": ("EDIT WIDGETS", "ActivateWindow(11115)"),
                "1010": ("SEARCH", "ActivateWindow(11112)"),
            },
            "custom11118.xml": {
                "1001": ("HOME", "ActivateWindow(Home)"),
                "1002": ("MOVIES", "ActivateWindow(11117)"),
                "1003": ("TV SHOWS", "ActivateWindow(11118)"),
                "1004": ("ALL SHOWS", "ActivateWindow(Videos,videodb://tvshows/titles/,return)"),
                "1005": ("GENRES", "ActivateWindow(Videos,videodb://tvshows/genres/,return)"),
                "1006": ("YEARS", "ActivateWindow(Videos,videodb://tvshows/years/,return)"),
                "1007": ("STUDIOS", "ActivateWindow(Videos,videodb://tvshows/studios/,return)"),
                "1008": ("RECENT", "ActivateWindow(Videos,videodb://tvshows/recentlyaddedepisodes/,return)"),
                "1009": ("EDIT WIDGETS", "ActivateWindow(11116)"),
                "1010": ("SEARCH", "ActivateWindow(11112)"),
            },
        }
        with ZipFile(ARCHIVE) as archive:
            for filename, actions in expected.items():
                root = ET.fromstring(archive.read("skin.cineva/xml/" + filename))
                nav = next(
                    node for node in root.findall("./controls/control")
                    if node.get("type") == "group"
                    and node.find("./control[@id='1001']") is not None
                )
                buttons = {
                    node.get("id"): node
                    for node in nav.findall("./control[@type='button']")
                }
                self.assertEqual(set(buttons), set(actions), filename)
                for index, (control_id, (label, action)) in enumerate(actions.items()):
                    button = buttons[control_id]
                    self.assertEqual(button.findtext("label"), label)
                    self.assertEqual(button.findtext("onclick"), action)
                    self.assertEqual(button.findtext("ondown"), "SetFocus(9201)")
                    self.assertEqual(button.findtext("onleft"),
                                     "SetFocus({})".format(1001 + max(0, index - 1)))
                    self.assertEqual(button.findtext("onright"),
                                     "SetFocus({})".format(1001 + min(9, index + 1)))
                self.assertEqual(len({button.get("id") for button in buttons.values()}), 10)


if __name__ == "__main__":
    unittest.main()
