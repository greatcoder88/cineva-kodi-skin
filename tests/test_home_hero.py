import struct
import unittest
import xml.etree.ElementTree as ET
import zlib
from zipfile import ZipFile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.26.zip"


class HomeHeroActionTests(unittest.TestCase):
    def test_release_changelog_uses_real_line_breaks(self):
        with ZipFile(ARCHIVE) as archive:
            lines = archive.read("skin.cineva/changelog.txt").decode("utf-8").splitlines()
        self.assertEqual(lines[0], "0.5.26 - Clean up Home hero progress rendering")
        self.assertEqual(lines[1], "- Keep the Continue Watching progress bar and watched percentage in the Home hero.")
        self.assertEqual(lines[2], "- Remove an unused overlay texture reference to avoid missing-texture warnings.")
        self.assertEqual(lines[3], "- Preserve the synopsis, progress and Resume/Play action hierarchy.")
        self.assertIn("0.5.25 - Surface continue-watching progress in the Home hero", lines)
        self.assertIn("0.5.24 - Restore native Kodi Add-on Browser focus", lines)
        self.assertIn("0.5.23 - Complete Settings and Add-ons D-pad navigation", lines)
        self.assertIn("0.5.20 - Compact Home shelves for denser browsing", lines)
        history = {line for line in lines if line.startswith("0.5.")}
        self.assertIn("0.5.19 - Refined Home navigation focus", history)
        self.assertIn("0.5.18 - Centered Home shelf focus for continuous browsing", history)
        self.assertIn("0.5.17 - Polished live Home shelf navigation", history)
        self.assertIn("0.5.16 - Live Home shelf position and scroll cues", history)
        self.assertIn("0.5.15 - Reliable empty-state D-pad entry", history)
        self.assertIn("0.5.14 - Catalogue empty states and contextual focus", history)
        self.assertIn("0.5.13 - Unified catalogue navigation styling", history)
        self.assertIn("0.5.12 - Full-width Home poster rails with next-card preview", history)
        self.assertIn("0.5.11 - Restore Home shelf focus after playback", history)
        self.assertIn("0.5.10 - Reliable URL-escaped Home playback handoff", history)
        index_12 = lines.index("0.5.12 - Full-width Home poster rails with next-card preview")
        self.assertTrue(lines[index_12 + 1].startswith("- Widen all four Home shelves to an 1800px viewport"))
        self.assertTrue(lines[index_12 + 2].startswith("- Reveal a partial seventh poster to signal horizontal browsing"))
        index_11 = lines.index("0.5.11 - Restore Home shelf focus after playback")
        self.assertTrue(lines[index_11 + 1].startswith("- Return remote focus to the originating Home shelf"))
        self.assertTrue(lines[index_11 + 2].startswith("- Preserve the selected title context when a resolver returns"))

    def test_all_home_heroes_use_branded_nine_slice_action_surfaces(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            for container_id, play_id in ((9001, 9111), (9002, 9113), (9003, 9115), (9004, 9117)):
                hero = next(
                    group for group in controls.findall("control")
                    if group.get("type") == "group"
                    and group.find(f"./control[@id='{play_id}']") is not None
                )
                buttons = hero.findall("./control[@type='button']")
                self.assertEqual(len(buttons), 2)
                self.assertEqual(
                    [(button.findtext("left"), button.findtext("top"),
                      button.findtext("width"), button.findtext("height")) for button in buttons],
                    [("0", "260", "190", "54"), ("212", "260", "220", "54")],
                )
                self.assertEqual(
                    [button.findtext("texturefocus") for button in buttons],
                    ["hero-primary-focus.png", "hero-secondary-focus.png"],
                )
                self.assertEqual(
                    [button.findtext("texturenofocus") for button in buttons],
                    ["hero-primary.png", "hero-secondary.png"],
                )
                for button in buttons:
                    self.assertEqual(button.findtext("textcolor"), "white")
                    self.assertEqual(button.find("texturefocus").attrib.get("border"), "8")
                    self.assertEqual(button.find("texturenofocus").attrib.get("border"), "8")

            for asset_name in (
                "hero-primary.png", "hero-primary-focus.png",
                "hero-secondary.png", "hero-secondary-focus.png",
            ):
                asset = archive.read(f"skin.cineva/media/{asset_name}")
                self.assertEqual(asset[:8], bytes.fromhex("89504e470d0a1a0a"))
                self.assertEqual(
                    (int.from_bytes(asset[16:20], "big"), int.from_bytes(asset[20:24], "big")),
                    (32, 32),
                )

    def test_hero_play_actions_pass_url_escaped_selected_file_paths(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            for container_id, play_id in ((9001, 9111), (9002, 9113), (9003, 9115), (9004, 9117)):
                button = home.find(f".//control[@id='{play_id}']")
                self.assertIsNotNone(button, f"Missing hero Play/Resume button {play_id}")
                self.assertEqual(
                    button.findtext("onclick"),
                    f"RunScript(script.cineva.widgets,action=play&container={container_id}&path=$ESCINFO[Container({container_id}).ListItem.FileNameAndPath])",
                    "Hero Play/Resume must delegate the selected shelf item URL to Kodi's Player API",
                )

    def test_generated_settings_and_catalogue_hero_controls_do_not_duplicate(self):
        with ZipFile(ARCHIVE) as archive:
            settings = ET.fromstring(archive.read("skin.cineva/xml/SkinSettings.xml"))
            controls = settings.find("controls")
            expected_headings = {"HOME WIDGETS", "MOVIES WIDGETS", "TV SHOWS WIDGETS"}
            for heading in expected_headings:
                self.assertEqual(
                    sum(node.findtext("label") == heading for node in controls.findall("control")),
                    1,
                    f"{heading} must appear exactly once",
                )
            slot_buttons = [
                node for node in controls.findall("control")
                if (node.findtext("onclick") or "").startswith(
                    "RunScript(script.cineva.widgets,action=configure&screen="
                )
            ]
            self.assertEqual(len(slot_buttons), 12)
            self.assertEqual(len({node.get("id") for node in slot_buttons}), 12)

            for path in ("skin.cineva/xml/custom11117.xml", "skin.cineva/xml/custom11118.xml"):
                page = ET.fromstring(archive.read(path))
                page_controls = page.find("controls")
                for control_id in range(9210, 9217):
                    self.assertEqual(
                        len(page_controls.findall(f"./control[@id='{control_id}']")),
                        1,
                        f"{path} must contain exactly one generated hero control {control_id}",
                    )


    def test_text_only_hero_titles_use_bold_display_typography(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            fonts = ET.fromstring(archive.read("skin.cineva/xml/Font.xml"))
            fontset = fonts.find("./fontset[@id='Default']")
            display_font = next(node for node in fontset.findall("font")
                                if node.findtext("name") == "font22")
            self.assertEqual(display_font.findtext("filename"), "Poppins-ExtraBold.ttf")
            self.assertEqual(display_font.findtext("size"), "40")
            controls = home.find("controls")
            for container_id, play_id in ((9001, 9111), (9002, 9113), (9003, 9115), (9004, 9117)):
                hero = next(
                    group for group in controls.findall("control")
                    if group.get("type") == "group"
                    and group.find(f"./control[@id='{play_id}']") is not None
                )
                title = next(
                    node for node in hero.findall("control")
                    if node.get("type") == "label"
                    and f"$INFO[Container({container_id}).ListItem.Label]" in node.findtext("label", "")
                )
                self.assertEqual(
                    (title.findtext("font"), title.findtext("width"), title.findtext("height")),
                    ("font22", "1200", "82"),
                )
                self.assertEqual(
                    title.findtext("visible"),
                    f"String.IsEmpty(Container({container_id}).ListItem.Art(clearlogo))",
                )


    def test_hero_metadata_and_inline_rating_precede_synopsis(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            for container_id, play_id in ((9001, 9111), (9002, 9113), (9003, 9115), (9004, 9117)):
                hero = next(
                    group for group in controls.findall("control")
                    if group.get("type") == "group"
                    and group.find(f"./control[@id='{play_id}']") is not None
                )
                metadata = next(
                    node for node in hero.findall("control")
                    if node.get("type") == "label"
                    and f"$INFO[Container({container_id}).ListItem.Year]" in node.findtext("label", "")
                )
                rating_id = 9340 + (container_id - 9001) * 3
                badge = hero.find(f"./control[@id='{rating_id}']")
                logo = hero.find(f"./control[@id='{rating_id + 1}']")
                score = hero.find(f"./control[@id='{rating_id + 2}']")
                self.assertEqual(metadata.findtext("width"), "340")
                self.assertEqual(metadata.findtext("top"), "128")
                self.assertEqual(int(badge.findtext("left")) - int(metadata.findtext("width")), 20)
                plot = hero.find("./control[@type='textbox']")
                self.assertEqual((plot.findtext("top"), plot.findtext("height")), ("172", "56"))
                self.assertEqual(
                    (badge.findtext("left"), badge.findtext("top"), badge.findtext("width"), badge.findtext("height")),
                    ("360", "126", "148", "32"),
                )
                self.assertEqual(
                    (logo.findtext("left"), logo.findtext("top"), logo.findtext("width"), logo.findtext("height")),
                    ("368", "130", "48", "24"),
                )
                self.assertEqual(
                    (score.findtext("left"), score.findtext("top"), score.findtext("width"), score.findtext("height")),
                    ("422", "126", "84", "32"),
                )

    def test_continue_watching_hero_exposes_item_progress_and_watched_percentage(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            for index, container_id in enumerate((9001, 9002, 9003, 9004), start=1):
                play_id = 9111 + (index - 1) * 2
                hero = next(
                    group for group in controls.findall("control")
                    if group.get("type") == "group"
                    and group.find(f"./control[@id='{play_id}']") is not None
                )
                expected_visible = (
                    f"String.Contains(Skin.String(Cineva.Widget{index}.Path),in_progress)"
                    f" + Container({container_id}).ListItem.IsResumable"
                )
                progress = hero.find(f"./control[@id='{9380 + index - 1}']")
                caption = hero.find(f"./control[@id='{9384 + index - 1}']")
                self.assertIsNotNone(progress)
                self.assertIsNotNone(caption)
                self.assertIsNone(progress.find("overlaytexture"))
                self.assertEqual(
                    (progress.get("type"), progress.findtext("left"), progress.findtext("top"),
                     progress.findtext("width"), progress.findtext("height"), progress.findtext("info"),
                     progress.findtext("visible"), progress.findtext("texturebg"),
                     progress.findtext("midtexture")),
                    ("progress", "0", "234", "300", "6",
                     f"Container({container_id}).ListItem.PercentPlayed", expected_visible,
                     "resume-track.png", "focus-bar.png"),
                )
                self.assertEqual(
                    (caption.get("type"), caption.findtext("left"), caption.findtext("top"),
                     caption.findtext("width"), caption.findtext("height"), caption.findtext("font"),
                     caption.findtext("textcolor"), caption.findtext("label"), caption.findtext("visible")),
                    ("label", "316", "226", "210", "22", "font9", "silver",
                     f"$INFO[Container({container_id}).ListItem.PercentPlayed]% WATCHED", expected_visible),
                )

    def test_home_has_soft_right_edge_vignette_for_full_bleed_hero_art(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            shade = controls.find("./control[@id='9109']")
            self.assertIsNotNone(shade, "Home must package the right-edge hero vignette")
            self.assertEqual(
                (shade.findtext("left"), shade.findtext("top"),
                 shade.findtext("width"), shade.findtext("height")),
                ("0", "0", "1920", "750"),
            )
            self.assertEqual(shade.findtext("texture"), "hero-right-shade.png")
            data = archive.read("skin.cineva/media/hero-right-shade.png")

        self.assertEqual(data[:8], bytes.fromhex("89504e470d0a1a0a"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (1920, 750))
        offset = 8
        compressed = bytearray()
        while offset < len(data):
            length = int.from_bytes(data[offset:offset + 4], "big")
            kind = data[offset + 4:offset + 8]
            payload = data[offset + 8:offset + 8 + length]
            crc = int.from_bytes(data[offset + 8 + length:offset + 12 + length], "big")
            self.assertEqual(zlib.crc32(kind + payload) & 0xffffffff, crc)
            if kind == b"IDAT":
                compressed.extend(payload)
            offset += length + 12
        decoded = zlib.decompress(bytes(compressed))
        stride = 1 + width * 4

        def alpha_at(x, y):
            row = y * stride
            self.assertEqual(decoded[row], 0, "vignette PNG must use deterministic unfiltered rows")
            return decoded[row + 1 + x * 4 + 3]

        self.assertEqual(alpha_at(1050, 375), 0, "long-title safe area must remain untouched")
        self.assertGreater(alpha_at(1200, 375), 0, "right-side fade must begin gradually after the title-safe area")
        self.assertGreaterEqual(alpha_at(1500, 375), 55, "mid-right artwork must receive a readable contrast fade")
        self.assertGreaterEqual(alpha_at(1800, 375), 120, "outer-right artwork must be visibly subdued")
        self.assertGreaterEqual(alpha_at(1919, 375), 135, "outer edge must receive the full cinematic vignette")

    def test_home_uses_balanced_native_2_3_posters_with_clear_heading_spacing(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            includes = ET.fromstring(archive.read("skin.cineva/xml/Includes.xml"))
            controls = home.find("controls")
            rail = controls.find("./control[@type='grouplist'][@id='9050']")
            self.assertEqual(
                (rail.findtext("left"), rail.findtext("top"), rail.findtext("width"), rail.findtext("height")),
                ("60", "444", "1800", "670"),
            )
            first_row_height = 472
            visible_next_shelf_preview = (
                1080 - int(rail.findtext("top")) - first_row_height - int(rail.findtext("itemgap"))
            )
            self.assertEqual(visible_next_shelf_preview, 152)
            visible_next_poster_peek = int(rail.findtext("width")) - 6 * 270 - 32
            self.assertEqual(visible_next_poster_peek, 148)
            for row in range(1, 5):
                group = rail.find(f"./control[@type='group'][@id='{9060 + row}']")
                shelf = group.find(f"./control[@type='fixedlist'][@id='{9000 + row}']")
                self.assertEqual(group.findtext("height"), "472")
                self.assertEqual((shelf.findtext("top"), shelf.findtext("height")), ("55", "400"))
                self.assertEqual(
                    [(node.get("width"), node.get("height"))
                     for node in shelf.findall("itemlayout") + shelf.findall("focusedlayout")],
                    [("270", "400"), ("270", "400")],
                )
            poster = includes.find("./include[@name='CinevaPosterItem']")
            image = poster.find("./control[@type='image']")
            title = poster.find("./control[@type='textbox']")
            progress = poster.find("./control[@type='progress']")
            self.assertEqual(
                (image.findtext("left"), image.findtext("top"), image.findtext("width"), image.findtext("height")),
                ("35", "0", "200", "300"),
            )
            self.assertEqual(
                (title.findtext("top"), title.findtext("height"), title.findtext("width")),
                ("302", "58", "270"),
            )
            self.assertEqual(
                (progress.findtext("left"), progress.findtext("top"), progress.findtext("width"), progress.findtext("height")),
                ("40", "289", "190", "5"),
            )
            focused = includes.find("./include[@name='CinevaFocusedPosterItem9001']")
            focused_image = next(
                node for node in focused.findall("./control[@type='image']")
                if node.findtext("visible") == "Control.HasFocus(9001)"
            )
            focused_title = next(
                node for node in focused.findall("./control[@type='textbox']")
                if node.findtext("visible") == "Control.HasFocus(9001)"
            )
            focus_accent = next(
                node for node in focused.findall("./control[@type='image']")
                if node.findtext("texture") == "focus-bar.png"
            )
            self.assertEqual(
                (focused_image.findtext("left"), focused_image.findtext("top"),
                 focused_image.findtext("width"), focused_image.findtext("height")),
                ("29", "-4", "212", "318"),
            )
            self.assertEqual(focused_image.findtext("bordersize"), "4")
            self.assertEqual(focused_image.find("bordertexture").attrib.get("border"), "4")
            row_group = rail.find("./control[@type='group'][@id='9061']")
            row_accent = next(node for node in row_group.findall("./control[@type='image']")
                              if node.findtext("texture") == "focus-bar.png")
            heading_to_poster_gap = (int(shelf.findtext("top"))
                                     + int(focused_image.findtext("top"))
                                     - int(row_accent.findtext("top"))
                                     - int(row_accent.findtext("height")))
            self.assertEqual((row_accent.findtext("top"), heading_to_poster_gap), ("42", 6))
            focus_png = archive.read("skin.cineva/media/poster-focus.png")
            offset = 8
            compressed = bytearray()
            while offset < len(focus_png):
                length = int.from_bytes(focus_png[offset:offset + 4], "big")
                kind = focus_png[offset + 4:offset + 8]
                payload = focus_png[offset + 8:offset + 8 + length]
                if kind == b"IDAT":
                    compressed.extend(payload)
                offset += length + 12
            decoded = zlib.decompress(bytes(compressed))
            stride = 1 + 8 * 4
            self.assertEqual(decoded[stride + 1 + 1 * 4 + 3], 228)
            self.assertEqual(decoded[3 * stride + 1 + 3 * 4 + 3], 0)
            self.assertEqual(
                (focused_title.findtext("top"), focused_title.findtext("height")),
                ("326", "58"),
            )
            self.assertEqual(
                (focus_accent.findtext("left"), focus_accent.findtext("top"),
                 focus_accent.findtext("width"), focus_accent.findtext("height")),
                ("95", "390", "80", "4"),
            )
            focus_progresses = focused.findall("./control[@type='progress']")
            self.assertEqual(len(focus_progresses), 2)
            self.assertEqual(
                {node.findtext("visible") for node in focus_progresses},
                {"!Control.HasFocus(9001) + ListItem.IsResumable", "Control.HasFocus(9001) + ListItem.IsResumable"},
            )
            self.assertEqual(
                [(node.findtext("left"), node.findtext("top"), node.findtext("width"), node.findtext("height"))
                 for node in focus_progresses],
                [("40", "289", "190", "5"), ("34", "302", "202", "5")],
            )

    def test_home_shelves_keep_focus_in_a_stable_browsing_lane(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            rail = home.find("./controls/control[@type='grouplist'][@id='9050']")
            self.assertIsNotNone(rail)
            for row in range(1, 5):
                shelf = rail.find(
                    f"./control[@type='group'][@id='{9060 + row}']"
                    f"/control[@type='fixedlist'][@id='{9000 + row}']"
                )
                self.assertIsNotNone(shelf, f"Home shelf {row} is missing")
                self.assertEqual(shelf.findtext("focusposition"), "3",
                                 f"Home shelf {row} must keep focus in the central browsing lane")
                self.assertEqual(shelf.findtext("movement"), "3",
                                 f"Home shelf {row} must retain edge-aware movement")

    def test_home_shelves_show_live_position_and_directional_scroll_cues(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            rail = controls.find("./control[@type='grouplist'][@id='9050']")
            self.assertIsNotNone(rail)
            ids = []
            for row in range(1, 5):
                container_id = 9000 + row
                counter_id = 9360 + (row - 1) * 3
                group = rail.find(f"./control[@type='group'][@id='{9060 + row}']")
                self.assertIsNotNone(group)
                pill = group.find(f"./control[@id='{9372 + row - 1}']")
                position = group.find(f"./control[@id='{counter_id}']")
                previous = group.find(f"./control[@id='{counter_id + 1}']")
                following = group.find(f"./control[@id='{counter_id + 2}']")
                self.assertEqual(
                    (pill.get("type"), pill.findtext("texture"), pill.findtext("visible"),
                     pill.findtext("left"), pill.findtext("top"), pill.findtext("width"), pill.findtext("height")),
                    ("image", "shelf-navigation-pill.png",
                     f"Control.HasFocus({container_id}) + !String.IsEmpty(Container({container_id}).ListItem.Label)",
                     "1578", "-1", "212", "40"),
                )
                self.assertEqual(
                    (position.findtext("label"), position.findtext("visible"),
                     position.findtext("left"), position.findtext("width")),
                    (f"$INFO[Container({container_id}).CurrentItem] / $INFO[Container({container_id}).NumItems]",
                     f"Control.HasFocus({container_id}) + !String.IsEmpty(Container({container_id}).ListItem.Label)",
                     "1590", "104"),
                )
                self.assertEqual(
                    (previous.findtext("label"), previous.findtext("visible")),
                    ("‹", f"Control.HasFocus({container_id}) + Container({container_id}).HasPrevious"),
                )
                self.assertEqual(
                    (following.findtext("label"), following.findtext("visible")),
                    ("›", f"Control.HasFocus({container_id}) + Container({container_id}).HasNext"),
                )
                ids.extend(node.get("id") for node in (pill, position, previous, following))
            self.assertEqual(len(ids), 16)
            self.assertEqual(len(set(ids)), 16)
            for control_id in ids:
                self.assertIsNone(
                    controls.find(f"./control[@id='{control_id}']"),
                    f"Home shelf cue {control_id} must remain nested in its row group",
                )
            pill_asset = archive.read("skin.cineva/media/shelf-navigation-pill.png")
            self.assertEqual(pill_asset[:8], bytes.fromhex("89504e470d0a1a0a"))
            self.assertEqual(
                (int.from_bytes(pill_asset[16:20], "big"), int.from_bytes(pill_asset[20:24], "big")),
                (212, 40),
            )


if __name__ == "__main__":
    unittest.main()
