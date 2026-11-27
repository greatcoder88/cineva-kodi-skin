import ast
import struct
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.65.zip"
FIXTURE = ROOT / "tools/test-fixtures/plugin.video.pov/default.py"


class HomeHeroRatingTests(unittest.TestCase):
    def test_selected_inception_fixture_supplies_explicit_tomatoes_percent(self):
        fixture = ast.parse(FIXTURE.read_text(encoding="utf-8"))
        percent_map = next(
            ast.literal_eval(node.value)
            for node in fixture.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "TOMATO_PERCENT"
                    for target in node.targets)
        )
        self.assertEqual(percent_map.get("Inception"), "92")

        uses_title_mapping = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setProperty"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "Rating.tomatoes.Percent"
            and isinstance(node.args[1], ast.Subscript)
            and isinstance(node.args[1].value, ast.Name)
            and node.args[1].value.id == "TOMATO_PERCENT"
            for node in ast.walk(fixture)
        )
        self.assertTrue(
            uses_title_mapping,
            "the POV fixture must attach the explicit percent to the selected title",
        )

    def test_all_home_heroes_render_rotten_tomatoes_percent_and_native_fallback(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
            controls = home.find("controls")
            for container_id, play_id in ((9001, 9111), (9002, 9113), (9003, 9115), (9004, 9117)):
                hero = next(group for group in controls.findall("control")
                            if group.get("type") == "group"
                            and group.find(f"./control[@id='{play_id}']") is not None)
                base = 9440 + (container_id - 9001) * 4
                prop = f"Container({container_id}).ListItem.Property(Rating.tomatoes.Percent)"
                native = f"Container({container_id}).ListItem.Rating(tomatometerallcritics)"
                badge, logo = hero.find(f"./control[@id='{base}']"), hero.find(f"./control[@id='{base + 1}']")
                percent, fallback = hero.find(f"./control[@id='{base + 2}']"), hero.find(f"./control[@id='{base + 3}']")
                self.assertEqual((badge.findtext("left"), badge.findtext("top"), badge.findtext("width"),
                                  badge.findtext("height"), badge.findtext("texture"), badge.findtext("visible")),
                                 ("580", "126", "148", "32", "tomatoes-badge.png",
                                  f"!String.IsEmpty({prop}) | !String.IsEmpty({native})"))
                self.assertEqual((logo.findtext("left"), logo.findtext("top"), logo.findtext("width"),
                                  logo.findtext("height"), logo.findtext("texture")),
                                 ("588", "130", "48", "24", "tomatoes-logo.png"))
                self.assertEqual(percent.findtext("label"), f"$INFO[{prop}]%")
                self.assertEqual(percent.findtext("visible"), f"!String.IsEmpty({prop})")
                self.assertEqual(fallback.findtext("label"), f"$INFO[{native}]/10")
                self.assertEqual(fallback.findtext("visible"),
                                 f"String.IsEmpty({prop}) + !String.IsEmpty({native})")
            ids = [node.get("id") for node in home.iter()
                   if node.get("id") in {str(value) for value in range(9440, 9456)}]
            self.assertEqual(len(ids), 16)
            self.assertEqual(len(set(ids)), 16)
            badge_data = archive.read("skin.cineva/media/tomatoes-badge.png")
            logo_data = archive.read("skin.cineva/media/tomatoes-logo.png")
        self.assertEqual(badge_data[:8], bytes.fromhex("89504e470d0a1a0a"))
        self.assertEqual(struct.unpack(">II", badge_data[16:24]), (148, 32))
        self.assertEqual(logo_data[:8], bytes.fromhex("89504e470d0a1a0a"))
        self.assertEqual(struct.unpack(">II", logo_data[16:24]), (48, 24))


if __name__ == "__main__":
    unittest.main()
