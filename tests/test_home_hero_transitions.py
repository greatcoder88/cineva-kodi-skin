import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.65.zip"


class HomeHeroTransitionTests(unittest.TestCase):
    def test_four_hero_backdrops_fade_when_their_row_becomes_visible(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        controls = home.find("controls")
        backgrounds = [
            node for node in controls.findall("control")
            if node.get("type") == "image"
            and ".ListItem.Art(fanart)]" in node.findtext("texture", "")
        ]
        self.assertEqual(len(backgrounds), 4)
        for row, control in enumerate(backgrounds, start=1):
            fades = [
                node for node in control.findall("animation")
                if node.get("effect") == "fade" and (node.text or "").strip() == "Visible"
            ]
            self.assertEqual(len(fades), 1, f"Home row {row} backdrop must have one visibility fade")
            self.assertEqual(
                {key: fades[0].get(key) for key in ("start", "end", "time", "tween")},
                {"start": "0", "end": "100", "time": "220", "tween": "sine"},
            )

    def test_four_hero_metadata_groups_fade_in_as_a_single_composition(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        controls = home.find("controls")
        groups = [
            node for node in controls.findall("control")
            if node.get("type") == "group"
            and node.findtext("control/label", "").startswith("$INFO[Container(")
        ]
        self.assertEqual(len(groups), 4)
        for row, group in enumerate(groups, start=1):
            fades = [
                node for node in group.findall("animation")
                if node.get("effect") == "fade" and (node.text or "").strip() == "Visible"
            ]
            self.assertEqual(len(fades), 1, f"Home row {row} metadata must share one visibility fade")
            self.assertEqual(fades[0].get("start"), "0")
            self.assertEqual(fades[0].get("end"), "100")
            self.assertEqual(fades[0].get("time"), "220")
            self.assertEqual(fades[0].get("tween"), "sine")

    def test_poster_fallback_layers_share_the_same_transition(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        controls = home.find("controls")
        posters = [
            node for node in controls.findall("control")
            if node.get("type") == "image"
            and ".ListItem.Art(poster)]" in node.findtext("texture", "")
        ]
        self.assertEqual(len(posters), 4)
        for row, control in enumerate(posters, start=1):
            self.assertTrue(
                any(node.get("effect") == "fade" and (node.text or "").strip() == "Visible"
                    for node in control.findall("animation")),
                f"Home row {row} portrait fallback must fade with its hero",
            )


if __name__ == "__main__":
    unittest.main()
