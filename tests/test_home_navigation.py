import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.54.zip"
HUB_WINDOW = "skin.cineva/xml/CinevaWidgetHub.xml"


class HomeNavigationTests(unittest.TestCase):
    def test_home_uses_per_screen_settings_without_a_separate_widget_hub(self):
        self.assertTrue(ARCHIVE.is_file(), "release skin archive must be built before this test")
        with ZipFile(ARCHIVE) as archive:
            names = set(archive.namelist())
            self.assertNotIn(HUB_WINDOW, names, "legacy standalone widget hub must not ship")
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))

        home_default = home.find("defaultcontrol")
        self.assertIsNotNone(home_default)
        self.assertEqual((home_default.text or "").strip(), "1001")
        self.assertNotIn("always", home_default.attrib, "Home must restore the last focused control on re-entry")

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
        self.assertEqual(buttons["1005"].findtext("onclick"), "ActivateWindow(Settings)")
        self.assertFalse(
            any((button.findtext("label") or "").strip().upper() == "MY WIDGETS"
                for button in buttons.values())
        )
        self.assertNotIn("ActivateWindow(11119)", ET.tostring(home, encoding="unicode"))

    def test_each_configured_home_row_has_a_focusable_view_all_action(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        rail = home.find("./controls/control[@type='grouplist'][@id='9050']")
        self.assertIsNotNone(rail)
        for index in range(1, 5):
            container_id = 9000 + index
            play_id = 9111 + (index - 1) * 2
            view_all_id = 9159 + index
            row = rail.find(f"./control[@type='group'][@id='{9060 + index}']")
            self.assertIsNotNone(row, f"Home widget row {index} is missing")
            button = row.find(f"./control[@type='button'][@id='{view_all_id}']")
            self.assertIsNotNone(button, f"Home widget row {index} needs VIEW ALL")
            self.assertEqual(button.findtext("label"), "VIEW ALL")
            self.assertEqual(
                button.findtext("onclick"),
                f"ActivateWindow(Videos,$INFO[Skin.String(Cineva.Widget{index}.Path)],return)",
            )
            self.assertEqual(button.findtext("onup"), f"SetFocus({play_id})")
            self.assertEqual(button.findtext("ondown"), f"SetFocus({container_id})")
            self.assertEqual(button.findtext("onleft"), f"SetFocus({view_all_id})")
            self.assertEqual(button.findtext("onright"), f"SetFocus({view_all_id})")
            self.assertEqual(button.findtext("texturefocus"), "hero-secondary-focus.png")
            self.assertEqual(button.findtext("texturenofocus"), "hero-secondary.png")
            heading = row.find("./control[@type='label']")
            self.assertEqual(button.findtext("visible"), heading.findtext("visible"))
            shelf = row.find(f"./control[@type='fixedlist'][@id='{container_id}']")
            self.assertIsNotNone(shelf)
            expected_up = (
                [(None, f"SetFocus({view_all_id})")]
                if index == 1 else
                [
                    action
                    for previous in range(index - 1, 0, -1)
                    for action in (
                        (f"Integer.IsGreater(Container({9000 + previous}).NumItems,0)",
                         f"SetFocus({9000 + previous})"),
                        (f"!String.IsEmpty(Skin.String(Cineva.Widget{previous}.Path))",
                         f"SetFocus({9159 + previous})"),
                    )
                ] + [(None, f"SetFocus({view_all_id})")]
            )
            self.assertEqual(
                [(node.get("condition"), node.text) for node in shelf.findall("onup")],
                expected_up,
                f"Home row {index} must move Up to the nearest populated/configured shelf above it",
            )
            loading = row.find(f"./control[@type='group'][@id='{9400 + index}']")
            self.assertIsNotNone(loading, f"Home row {index} needs a non-focusable loading state")
            self.assertEqual(
                loading.findtext("visible"),
                f"!String.IsEmpty(Skin.String(Cineva.Widget{index}.Path)) + "
                f"Container({container_id}).IsUpdating + "
                f"Integer.IsEqual(Container({container_id}).NumItems,0)",
            )
            self.assertEqual(
                len(loading.findall("./control[@type='image']")), 5,
                "Loading state must preserve the poster-shelf geometry",
            )
            empty_state = row.find(f"./control[@type='group'][@id='{9520 + index}']")
            self.assertIsNotNone(empty_state, f"Home row {index} needs a completed-empty state")
            self.assertEqual(
                empty_state.findtext("visible"),
                f"!String.IsEmpty(Skin.String(Cineva.Widget{index}.Path)) + "
                f"!Container({container_id}).IsUpdating + "
                f"Integer.IsEqual(Container({container_id}).NumItems,0)",
            )

    def test_home_shows_first_run_initialization_state_without_stealing_focus(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        state = home.find("./controls/control[@type='group'][@id='9480']")
        self.assertIsNotNone(state)
        self.assertEqual(state.findtext("visible"), "!Skin.HasSetting(Cineva.Initialized)")
        self.assertEqual(state.findtext("./control[@id='9481']/label"), "PREPARING YOUR CINÉVA HOME")
        self.assertIsNone(state.find("./control[@type='button']"),
                          "Loading artwork must never steal D-pad focus")

    def test_kodi_settings_exposes_addons_and_native_skin_settings(self):
        with ZipFile(ARCHIVE) as archive:
            settings = ET.fromstring(archive.read("skin.cineva/xml/Settings.xml"))
        self.assertEqual(settings.get("id"), "10004")
        self.assertEqual(settings.findtext("defaultcontrol"), "11405")
        buttons = {node.get("id"): node for node in settings.findall("./controls/control[@type='button']")}
        self.assertEqual(set(buttons), {str(control_id) for control_id in range(11401, 11410)})
        self.assertEqual(buttons["11405"].findtext("label"), "ADD-ONS")
        self.assertEqual(buttons["11405"].findtext("onclick"), "ActivateWindow(AddonBrowser)")
        self.assertEqual(buttons["11408"].findtext("label"), "CINÉVA SKIN SETTINGS")
        self.assertEqual(buttons["11408"].findtext("onclick"), "ActivateWindow(SkinSettings)")
        for control_id, button in buttons.items():
            self.assertEqual(button.findtext("texturefocus"), "hero-secondary-focus.png")
            self.assertEqual(button.findtext("texturenofocus"), "hero-secondary.png")
            numeric_id = int(control_id)
            if numeric_id == 11409:
                self.assertEqual(button.findtext("onup"), "SetFocus(11407)")
                self.assertEqual(button.findtext("ondown"), "SetFocus(11401)")
                self.assertEqual(button.findtext("onleft"), "SetFocus(11408)")
                self.assertEqual(button.findtext("onright"), "SetFocus(11401)")
                self.assertEqual(button.findtext("onclick"), "ActivateWindow(FileManager)")
            else:
                row, column = divmod(numeric_id - 11401, 2)
                side_id = numeric_id + (1 if column == 0 else -1)
                up_id = numeric_id - 2 if row > 0 else numeric_id + 6
                down_id = 11409 if numeric_id == 11407 else (numeric_id - 6 if row == 3 else numeric_id + 2)
                self.assertEqual(button.findtext("onleft"), f"SetFocus({side_id})")
                self.assertEqual(button.findtext("onright"), f"SetFocus({side_id})")
                self.assertEqual(button.findtext("onup"), f"SetFocus({up_id})")
                self.assertEqual(button.findtext("ondown"), f"SetFocus({down_id})")

    def test_system_info_and_profiles_native_windows_are_packaged(self):
        with ZipFile(ARCHIVE) as archive:
            names = set(archive.namelist())
            system_info = ET.fromstring(archive.read("skin.cineva/xml/SettingsSystemInfo.xml"))
            profiles = ET.fromstring(archive.read("skin.cineva/xml/SettingsProfile.xml"))
        self.assertIn("skin.cineva/xml/SettingsSystemInfo.xml", names)
        self.assertIn("skin.cineva/xml/SettingsProfile.xml", names)
        self.assertEqual(system_info.findtext("defaultcontrol"), "95")
        self.assertIsNotNone(system_info.find(".//control[@id='30']"))
        self.assertEqual(profiles.findtext("defaultcontrol"), "9000")
        self.assertIsNotNone(profiles.find(".//control[@id='9000']"))

    def test_file_manager_keeps_kodis_native_dual_pane_focus(self):
        with ZipFile(ARCHIVE) as archive:
            file_manager = ET.fromstring(archive.read("skin.cineva/xml/FileManager.xml"))
        self.assertEqual(file_manager.findtext("defaultcontrol"), "20")
        self.assertIsNone(file_manager.find("views"),
                          "File Manager is a native dual-pane window, not a media view")
        controls = file_manager.find("controls")
        self.assertIsNotNone(controls)
        self.assertIsNotNone(controls.find("./control[@type='fixedlist'][@id='20']"),
                             "Left file pane must remain present")
        self.assertIsNotNone(controls.find("./control[@type='fixedlist'][@id='21']"),
                             "Right file pane must remain present")

    def test_addon_browser_uses_kodis_native_media_window_view(self):
        with ZipFile(ARCHIVE) as archive:
            addon_browser = ET.fromstring(archive.read("skin.cineva/xml/AddonBrowser.xml"))
        panel = addon_browser.find("./controls/control[@type='panel']")
        self.assertIsNotNone(panel)
        self.assertEqual(panel.get("id"), "50")
        self.assertEqual(addon_browser.findtext("defaultcontrol"), "50")
        self.assertEqual(addon_browser.findtext("views"), "50")
        self.assertIsNone(addon_browser.find("./controls/control[@type='panel'][@id='3']"))

    def test_search_is_provider_driven_with_separate_movie_and_tv_results(self):
        with ZipFile(ARCHIVE) as archive:
            search = ET.fromstring(archive.read("skin.cineva/xml/custom11112.xml"))
            settings = ET.fromstring(archive.read("skin.cineva/xml/SkinSettings.xml"))
        controls = search.find("controls")
        self.assertEqual(search.findtext("defaultcontrol"), "9705")
        self.assertEqual(controls.findtext("./control[@id='9703']/label"), "SEARCH")
        self.assertIsNotNone(controls.find("./control[@type='button'][@id='9705']"),
                             "Search must default to a focusable control, not the title label")
        self.assertEqual(controls.findtext("./control[@id='9705']/label"), "NEW SEARCH")
        self.assertEqual(controls.findtext("./control[@id='9705']/onclick"),
                         "RunScript(script.cineva.widgets,action=search)")
        movie = controls.find("./control[@type='panel'][@id='9701']")
        tv = controls.find("./control[@type='panel'][@id='9702']")
        self.assertIsNotNone(movie)
        self.assertIsNotNone(tv)
        self.assertEqual(movie.findtext("content"), "$INFO[Skin.String(Cineva.Search.MoviePath)]")
        self.assertEqual(tv.findtext("content"), "$INFO[Skin.String(Cineva.Search.ShowPath)]")
        self.assertEqual(movie.findtext("onright"), "SetFocus(9702)")
        self.assertEqual(tv.findtext("onleft"), "SetFocus(9701)")
        self.assertEqual(len(movie.findall("itemlayout/control[@type='image']")), 1)
        self.assertEqual(len(tv.findall("itemlayout/control[@type='image']")), 1)
        provider = settings.find("./controls/control[@id='45']")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.findtext("onclick"),
                         "RunScript(script.cineva.widgets,action=searchprovider)")
        self.assertIn("SEARCH PROVIDER", ET.tostring(settings, encoding="unicode"))

    def test_native_skin_settings_starts_on_the_first_widget_slot(self):
        with ZipFile(ARCHIVE) as archive:
            settings = ET.fromstring(archive.read("skin.cineva/xml/SkinSettings.xml"))
        self.assertEqual(settings.findtext("defaultcontrol"), "21")
        buttons = {node.get("id"): node for node in settings.findall("./controls/control[@type='button']")
                   if node.get("id") in {str(control_id) for control_id in range(21, 33)}}
        self.assertEqual(set(buttons), {str(control_id) for control_id in range(21, 33)})
        self.assertNotIn("5", buttons, "overlapping legacy OPEN CINÉVA SETTINGS button must be removed")
        for button_id, button in buttons.items():
            numeric_id = int(button_id)
            column = (numeric_id - 21) // 4
            row = (numeric_id - 21) % 4
            up_id = numeric_id - 1 if row > 0 else numeric_id + 3
            down_id = numeric_id + 1 if row < 3 else numeric_id - 3
            left_id = numeric_id - 4 if column > 0 else numeric_id + 8
            right_id = numeric_id + 4 if column < 2 else numeric_id - 8
            self.assertEqual(button.findtext("onup"), f"SetFocus({up_id})")
            self.assertEqual(button.findtext("ondown"), f"SetFocus({down_id})")
            self.assertEqual(button.findtext("onleft"), f"SetFocus({left_id})")
            self.assertEqual(button.findtext("onright"), f"SetFocus({right_id})")


    def test_home_header_focus_uses_transparent_tabs_and_tracking_underlines(self):
        with ZipFile(ARCHIVE) as archive:
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
        self.assertEqual(set(buttons), {str(control_id) for control_id in range(1001, 1006)})
        for button in buttons.values():
            self.assertIsNone(button.find("texturefocus"),
                              "Home tabs must not become solid red blocks when focused")
            self.assertIsNone(button.find("texturenofocus"),
                              "Home tabs must remain transparent when unfocused")
            self.assertEqual(button.findtext("focusedcolor"), "white")
        home_visible = "Window.IsActive(home) + " + " + ".join(
            f"!Control.HasFocus({control_id})" for control_id in (1002, 1003, 1004, 1005)
        )
        expected = {
            "9201": ("34", "42", "62", "4", "focus-bar.png", home_visible),
            "9202": ("194", "42", "62", "4", "focus-bar.png", "Control.HasFocus(1002)"),
            "9203": ("373", "42", "74", "4", "focus-bar.png", "Control.HasFocus(1003)"),
            "9204": ("554", "42", "62", "4", "focus-bar.png", "Control.HasFocus(1004)"),
            "9205": ("714", "42", "62", "4", "focus-bar.png", "Control.HasFocus(1005)"),
        }
        for marker_id, geometry in expected.items():
            marker = nav.find(f"./control[@type='image'][@id='{marker_id}']")
            self.assertIsNotNone(marker, f"Home navigation is missing focus marker {marker_id}")
            self.assertEqual(
                (marker.findtext("left"), marker.findtext("top"),
                 marker.findtext("width"), marker.findtext("height"),
                 marker.findtext("texture"), marker.findtext("visible")),
                geometry,
                f"Home navigation focus marker {marker_id} has incorrect geometry or visibility",
            )


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
                    self.assertEqual(
                        [(node.get("condition"), node.text) for node in down_actions],
                        [
                            (f"!String.IsEmpty(Container({9200 + slot}).ListItem.Label)",
                             f"SetFocus({9200 + slot})")
                            for slot in range(1, 5)
                        ] + [(None, "SetFocus(12114)")],
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
                expected_default = "1002" if filename == "custom11117.xml" else "1003"
                self.assertEqual(root.findtext("defaultcontrol"), expected_default, filename)
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
                expected_widths = {
                    "ALL MOVIES": 125, "ALL SHOWS": 125,
                    "COLLECTIONS": 130, "STUDIOS": 90, "EDIT WIDGETS": 140,
                }
                for button in buttons:
                    self.assertEqual(button.findtext("texturefocus"), "focus-bar.png")
                    self.assertIsNone(button.find("texturenofocus"),
                                      "inactive catalogue tabs must remain transparent")
                    label = button.findtext("label")
                    if label in expected_widths:
                        self.assertEqual(int(button.findtext("width")),
                                         expected_widths[label], label)
                marker_id, active_window, marker_left, marker_width = (
                    ("12001", 11117, 92, 56)
                    if filename == "custom11117.xml"
                    else ("12002", 11118, 183, 69)
                )
                marker = nav.find(f"./control[@type='image'][@id='{marker_id}']")
                self.assertIsNotNone(marker, filename)
                self.assertEqual(
                    (marker.findtext("left"), marker.findtext("top"),
                     marker.findtext("width"), marker.findtext("height"),
                     marker.findtext("texture"), marker.findtext("visible")),
                    (str(marker_left), "42", str(marker_width), "4",
                     "focus-bar.png", f"Window.IsActive({active_window})"),
                    filename,
                )
                self.assertLessEqual(
                    max(int(button.findtext("left")) + int(button.findtext("width"))
                        for button in buttons),
                    1080,
                )
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
