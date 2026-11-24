import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.3.zip"


class HomeHeroActionTests(unittest.TestCase):
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


    def test_hero_metadata_rating_and_synopsis_form_a_left_aligned_stack(self):
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
                self.assertEqual(metadata.findtext("width"), "430")
                self.assertEqual(metadata.findtext("top"), "128")
                plot = hero.find("./control[@type='textbox']")
                self.assertEqual((plot.findtext("top"), plot.findtext("height")), ("194", "56"))
                self.assertEqual(
                    (badge.findtext("left"), badge.findtext("top"), badge.findtext("width"), badge.findtext("height")),
                    ("0", "158", "148", "32"),
                )
                self.assertEqual(
                    (logo.findtext("left"), logo.findtext("top"), logo.findtext("width"), logo.findtext("height")),
                    ("8", "162", "48", "24"),
                )
                self.assertEqual(
                    (score.findtext("left"), score.findtext("top"), score.findtext("width"), score.findtext("height")),
                    ("62", "158", "84", "32"),
                )

    def test_home_uses_compact_poster_rails_to_preview_the_next_shelf(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            includes = ET.fromstring(archive.read("skin.cineva/xml/Includes.xml"))
            controls = home.find("controls")
            rail = controls.find("./control[@type='grouplist'][@id='9050']")
            self.assertEqual(
                (rail.findtext("left"), rail.findtext("top"), rail.findtext("width"), rail.findtext("height")),
                ("105", "444", "1710", "670"),
            )
            for row in range(1, 5):
                group = rail.find(f"./control[@type='group'][@id='{9060 + row}']")
                shelf = group.find(f"./control[@type='fixedlist'][@id='{9000 + row}']")
                self.assertEqual(group.findtext("height"), "460")
                self.assertEqual((shelf.findtext("top"), shelf.findtext("height")), ("52", "408"))
                self.assertEqual(
                    [(node.get("width"), node.get("height"))
                     for node in shelf.findall("itemlayout") + shelf.findall("focusedlayout")],
                    [("285", "408"), ("285", "408")],
                )
            poster = includes.find("./include[@name='CinevaPosterItem']")
            image = poster.find("./control[@type='image']")
            title = poster.find("./control[@type='textbox']")
            progress = poster.find("./control[@type='progress']")
            self.assertEqual(
                (image.findtext("left"), image.findtext("top"), image.findtext("width"), image.findtext("height")),
                ("22", "0", "240", "320"),
            )
            self.assertEqual(
                (title.findtext("top"), title.findtext("height"), title.findtext("width")),
                ("322", "56", "285"),
            )
            self.assertEqual(
                (progress.findtext("left"), progress.findtext("top"), progress.findtext("width"), progress.findtext("height")),
                ("28", "309", "228", "5"),
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
                ("19", "-3", "246", "327"),
            )
            self.assertEqual(
                (focused_title.findtext("top"), focused_title.findtext("height")),
                ("340", "56"),
            )
            self.assertEqual(
                (focus_accent.findtext("left"), focus_accent.findtext("top"),
                 focus_accent.findtext("width"), focus_accent.findtext("height")),
                ("101", "399", "84", "4"),
            )


if __name__ == "__main__":
    unittest.main()
