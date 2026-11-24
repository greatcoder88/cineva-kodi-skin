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
                    [("0", "250", "190", "54"), ("212", "250", "220", "54")],
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


if __name__ == "__main__":
    unittest.main()
