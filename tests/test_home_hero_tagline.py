import ast
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "skin.cineva-0.5.64.zip"
FIXTURE = ROOT / "tools/test-fixtures/plugin.video.pov/default.py"


class HomeHeroTaglineTests(unittest.TestCase):
    def test_all_four_heroes_prefer_tagline_then_outline_then_plot(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        controls = home.find("controls")
        for row, container_id in enumerate((9001, 9002, 9003, 9004), start=1):
            play_id = 9111 + (row - 1) * 2
            hero = next(
                group for group in controls.findall("control")
                if group.get("type") == "group"
                and group.find(f"./control[@id='{play_id}']") is not None
            )
            tagline = hero.find(f"./control[@id='{9430 + row}']")
            outline_id = 9400 + (row - 1) * 2
            outline = hero.find(f"./control[@id='{outline_id}']")
            plot = hero.find(f"./control[@id='{outline_id + 1}']")
            self.assertIsNotNone(tagline, f"Home hero {container_id} is missing Tagline")
            self.assertIsNotNone(outline, f"Home hero {container_id} is missing PlotOutline fallback")
            self.assertIsNotNone(plot, f"Home hero {container_id} is missing full Plot fallback")
            tagline_info = f"Container({container_id}).ListItem.Tagline"
            outline_info = f"Container({container_id}).ListItem.PlotOutline"
            plot_info = f"Container({container_id}).ListItem.Plot"
            for control in (tagline, outline, plot):
                self.assertEqual(control.get("type"), "textbox")
                self.assertEqual(
                    (control.findtext("left"), control.findtext("top"),
                     control.findtext("width"), control.findtext("height"),
                     control.findtext("font"), control.findtext("textcolor")),
                    ("0", "172", "760", "56", "font13", "white"),
                )
            self.assertEqual(tagline.findtext("label"), f"$INFO[{tagline_info}]")
            self.assertEqual(tagline.findtext("visible"), f"!String.IsEmpty({tagline_info})")
            self.assertEqual(outline.findtext("label"), f"$INFO[{outline_info}]")
            self.assertEqual(
                outline.findtext("visible"),
                f"String.IsEmpty({tagline_info}) + !String.IsEmpty({outline_info})",
            )
            self.assertEqual(plot.findtext("label"), f"$INFO[{plot_info}]")
            self.assertEqual(
                plot.findtext("visible"),
                f"String.IsEmpty({tagline_info}) + String.IsEmpty({outline_info}) + !String.IsEmpty({plot_info})",
            )

    def test_progress_eyebrows_distinguish_continue_watching_from_in_progress(self):
        with ZipFile(ARCHIVE) as archive:
            home = ET.fromstring(archive.read("skin.cineva/xml/Home.xml"))
        controls = home.find("controls")
        for row, expected_label in ((1, "CONTINUE WATCHING"), (2, "IN PROGRESS")):
            play_id = 9111 + (row - 1) * 2
            hero = next(
                group for group in controls.findall("control")
                if group.get("type") == "group"
                and group.find(f"./control[@id='{play_id}']") is not None
            )
            eyebrow = hero.find(f"./control[@id='{9300 + (row - 1) * 3}']")
            self.assertIsNotNone(eyebrow, f"Home hero row {row} is missing its in-progress eyebrow")
            self.assertEqual(eyebrow.findtext("label"), expected_label)
            self.assertEqual(
                eyebrow.findtext("visible"),
                f"String.Contains(Skin.String(Cineva.Widget{row}.Path),in_progress)",
            )

    def test_gui_fixture_has_distinct_provider_copy_for_every_movie_and_show(self):
        tree = ast.parse(FIXTURE.read_text(encoding="utf-8"))
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in {"TAGLINES", "PLOTS", "PLOT_OUTLINES"}:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(set(values), {"TAGLINES", "PLOTS", "PLOT_OUTLINES"})
        self.assertEqual(len(values["TAGLINES"]), 16)
        self.assertEqual(len(values["PLOTS"]), 16)
        self.assertEqual(set(values["TAGLINES"]), set(values["PLOTS"]))
        self.assertEqual(sum(bool(value) for value in values["TAGLINES"].values()), 15)
        self.assertEqual(len({value for value in values["TAGLINES"].values() if value}), 15)
        self.assertEqual(values["TAGLINES"]["Inception"], "")
        self.assertEqual(len(set(values["PLOTS"].values())), 16)
        self.assertEqual(values["PLOT_OUTLINES"]["Inception"],
                         "A skilled thief enters dreams to steal secrets, then takes on an impossible job: plant an idea.")


if __name__ == "__main__":
    unittest.main()
