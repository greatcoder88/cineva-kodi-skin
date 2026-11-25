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
        self.assertEqual(buttons["1005"].findtext("onclick"), "ActivateWindow(11113)")
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
                    down_actions = button.findall("ondown")
                    widget_prefix = "Cineva.ShowWidget" if filename == "custom11118.xml" else "Cineva.MovieWidget"
                    self.assertEqual(
                        [(node.get("condition"), node.text) for node in down_actions],
                        [
                            ("!String.IsEmpty(Skin.String({}{}.Path))".format(widget_prefix, slot),
                             "SetFocus({})".format(9200 + slot))
                            for slot in range(1, 5)
                        ] + [(None, "SetFocus(1009)")],
                    )
                    self.assertEqual(button.findtext("onleft"),
                                     "SetFocus({})".format(1001 + max(0, index - 1)))
                    self.assertEqual(button.findtext("onright"),
                                     "SetFocus({})".format(1001 + min(9, index + 1)))
                self.assertEqual(len({button.get("id") for button in buttons.values()}), 10)


    def test_catalogue_pages_keep_focus_with_empty_optional_widget_slots(self):
        with ZipFile(ARCHIVE) as archive:
            for filename, page_title in (
                ("custom11117.xml", "MOVIES"),
                ("custom11118.xml", "TV SHOWS"),
            ):
                root = ET.fromstring(archive.read(f"skin.cineva/xml/{filename}"))
                self.assertEqual(root.findtext("defaultcontrol"), "1001", filename)
                self.assertIsNone(root.find("onload"), filename)
                title_nodes = [
                    node for node in root.findall("./controls/control[@type='label']")
                    if node.findtext("label", "").strip().upper() == page_title
                ]
                self.assertEqual(len(title_nodes), 1, filename)
                self.assertEqual(title_nodes[0].get("id"), "9211", filename)


    def test_catalogue_navigation_matches_home_header_geometry(self):
        with ZipFile(ARCHIVE) as archive:
            for filename in ("custom11117.xml", "custom11118.xml"):
                root = ET.fromstring(archive.read(f"skin.cineva/xml/{filename}"))
                nav = next(
                    node for node in root.findall("./controls/control")
                    if node.get("type") == "group"
                    and node.find("./control[@id='1001']") is not None
                )
                self.assertEqual(
                    (nav.findtext("left"), nav.findtext("top"),
                     nav.findtext("width"), nav.findtext("height")),
                    ("280", "32", "1080", "48"),
                    filename,
                )
                buttons = nav.findall("./control[@type='button']")
                self.assertEqual(len(buttons), 10, filename)
                self.assertTrue(all(button.findtext("font") == "font12" for button in buttons))
                self.assertLessEqual(
                    max(int(button.findtext("left")) + int(button.findtext("width")) for button in buttons),
                    1080,
                )

    def test_visible_skin_labels_are_english_only(self):
        with ZipFile(ARCHIVE) as archive:
            for filename in archive.namelist():
                if not filename.startswith("skin.cineva/xml/") or not filename.endswith(".xml"):
                    continue
                root = ET.fromstring(archive.read(filename))
                for label in root.findall(".//label"):
                    value = label.text or ""
                    self.assertFalse(
                        any("\\u0900" <= character <= "\\u097F" for character in value),
                        f"{filename} contains non-English visible label text: {value!r}",
                    )


    def test_custom_window_xml_ids_use_kodis_home_relative_offset(self):
        # Kodi's custom-window loader registers WINDOW_HOME + the XML id.
        # Thus custom11117.xml must declare id=1117 to become window 11117.
        with ZipFile(ARCHIVE) as archive:
            for window_id in range(11111, 11119):
                path = f"skin.cineva/xml/custom{window_id}.xml"
                root = ET.fromstring(archive.read(path))
                self.assertEqual(
                    root.get("id"),
                    str(window_id - 10000),
                    f"{path} must use the XML id offset expected by Kodi",
                )


if __name__ == "__main__":
    unittest.main()
