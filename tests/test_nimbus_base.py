import hashlib
import os
import io
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_nimbus_base as builder
import download_test_posters as poster_artwork


def make_archive(root_name, files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            payload = data if isinstance(data, bytes) else data.encode("utf-8")
            archive.writestr(f"{root_name}/{name}", payload)
    return stream.getvalue()


NIMBUS_FILES = {
    "LICENSE.txt": "Nimbus by Ivar Brandt\nGNU GPL-2.0 and CC BY-SA 4.0\n",
    "README.md": "Nimbus upstream source\n",
    "addon.xml": """<?xml version="1.0"?>
<addon id="skin.nimbus" name="Nimbus" version="0.1.43" provider-name="Ivar Brandt">
  <requires>
    <import addon="xbmc.gui" version="5.17.0"/>
    <import addon="script.nimbus.helper" version="0.0.50"/>
  </requires>
  <extension point="xbmc.gui.skin"><res width="1920" height="1080" aspect="16:9" default="true" folder="xml"/></extension>
  <extension point="xbmc.addon.metadata"><license>GPL-2.0-only</license><summary>Nimbus</summary><description>Nimbus Skin</description></extension>
</addon>""",
    "xml/Home.xml": "<window><defaultcontrol>9000</defaultcontrol><controls><include>DefaultBackground</include></controls></window>",
    "colors/defaults.xml": """<colors>
      <color name="primary_background">FF303232</color>
      <color name="dialog_tint">FF050505</color>
      <color name="dialog_bg">BF050505</color>
      <color name="dialog_bg2">F2050505</color>
      <color name="dialog_bg3">F7050505</color>
      <color name="button_focus">FFCCCCCC</color>
      <color name="button_focus2">FF040505</color>
      <color name="focused_text">FF141515</color>
      <color name="unfocused_text">FFE0E0E8</color>
      <color name="artwork_dim">FFE9E9E9</color>
      <color name="accent_color">FFCCCCCC</color>
      <color name="selected">FF1773CD</color>
      <color name="keyboard_selected">FF1773CD</color>
      <color name="primary_content_panel_bg">FF354CCF</color>
      <color name="background">FF000000</color>
      <color name="bg_overlay">4DFFFFFF</color>
      <color name="red">FFCE4421</color>
    </colors>""",
    "xml/Includes_FlixPanel.xml": """<includes>
      <include name="FlixPanel">
        <definition>
          <control type="grouplist">
            <include content="FlixInfoIcon">
              <param name="flixlabel" value="$INFO[Container($PARAM[id]).ListItem.Rating]★"/>
              <param name="visible" value="!String.IsEmpty(Container($PARAM[id]).ListItem.Rating) + !ListItem.IsCollection + [$EXP[isEpisode] | String.StartsWith(Container.PluginName,plugin.video.otaku)]"/>
            </include>
            <include content="HorizontalRatings" condition="!String.IsEmpty(Skin.String(valid_api_key))"/>
          </control>
        </definition>
      </include>
    </includes>""",
    "xml/Includes.xml": """<includes>
      <include file="Includes_Home.xml"/>
      <include content="FlixSquareLayout"><param name="fallback_image" value="DefaultAddon.png" /></include>
      <include content="FlixSquareLayout"><param name="fallback_image" value="DefaultAddon.png" /><param name="focused" value="true" /></include>
      <include name="PVRWidgetLayout"><animation effect="fade" start="100" end="50" time="40" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation></include>
      <include name="FileManagerPanel"><animation effect="fade" start="100" end="0" time="40" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation></include>
      <include name="WidgetNavigationArrows">
        <control type="button" id="$PARAM[list_id]500"><visible allowhiddenfocus="true">Container($PARAM[list_id]).HasPrevious + [Control.HasFocus($PARAM[list_id]) | Control.HasFocus($PARAM[list_id]500)]</visible></control>
        <control type="button" id="$PARAM[list_id]501"><visible allowhiddenfocus="true">Container($PARAM[list_id]).HasNext + [Control.HasFocus($PARAM[list_id]) | Control.HasFocus($PARAM[list_id]501)]</visible></control>
      </include>
      <include name="WallTimer"><control type="button"><onfocus>Skin.TimerStart(wall_scroll_timer)</onfocus></control></include>
      <include name="PosterFlowScrollTimer"><control type="button"><onfocus>Skin.TimerStart(posterflow_scroll_timer)</onfocus></control></include>
      <include name="HomeTrailerControl"><control type="button"><onfocus>Skin.TimerStart(autoplay_trailer_timer)</onfocus></control></include>
    </includes>""",
    "xml/Includes_Home.xml": """<includes>
      <onload>RunScript(script.nimbus.helper,mode=check_for_update&amp;skin_id=skin.nimbus)</onload>
      <onload>RunScript(script.nimbus.helper,mode=check_for_profile_change&amp;skin_id=skin.nimbus)</onload>
      <onfocus>RunScript(script.nimbus.helper,mode=set_widget_count,$PARAM[list_id])</onfocus>
    </includes>""",
    "xml/Includes_HomeLayouts.xml": """<includes>
      <include name="WidgetGroupListCommon"/>
      <include name="HomeLayoutFocus">
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(54)">Conditional</animation>
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(55)">Conditional</animation>
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(500)">Conditional</animation>
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(501)">Conditional</animation>
      </include>
    </includes>""",
    "xml/Startup.xml": "<window><onload>RunScript(script.nimbus.helper,mode=refresh_search_history)</onload></window>",
    "xml/SkinSettings.xml": """<window><controls>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=manage_widgets&amp;cpath_setting=movie.widget)</onclick></control>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=set_api_key)</onclick></control>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=delete_all_ratings)</onclick></control>
    </controls></window>""",
    "xml/Variables_Ratings.xml": "<includes><variable name=\"rating\"><value>$INFO[ListItem.Rating]</value></variable></includes>",
    "xml/View_54_Flix.xml": """<includes>
      <include name="FlixSquareLayout"><visible>Control.HasFocus($PARAM[list_id])</visible></include>
      <include name="FlixMovieLayout"><visible>Control.HasFocus($PARAM[list_id])</visible></include>
      <include>FlixMovieLayout</include>
      <include content="FlixMovieLayout"><param name="focused" value="true" /></include>
      <include name="FlixViewFocus">
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(54)">Conditional</animation>
      </include>
    </includes>""",
    "xml/View_500_Wall.xml": """<includes>
      <include>FlixMovieLayout</include>
      <include content="FlixMovieLayout"><param name="focused" value="true" /></include>
    </includes>""",
    "xml/View_55_FlixScape.xml": """<includes>
      <include>FlixScapeMovieLayout</include>
      <include content="FlixScapeMovieLayout"><param name="focused" value="true" /></include>
      <include name="FlixScapeFocus">
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(55)">Conditional</animation>
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(501)">Conditional</animation>
      </include>
    </includes>""",
    "xml/View_501_WallScape.xml": """<includes>
      <include>FlixScapeMovieLayout</include>
      <include content="FlixScapeMovieLayout"><param name="focused" value="true" /></include>
    </includes>""",
    "xml/View_51_PosterFlow.xml": """<includes>
      <include>PosterFlowLayout</include>
      <include content="PosterFlowLayout"><param name="focused" value="true" /></include>
      <include name="PosterFlowFocus">
        <animation condition="[$PARAM[focused] + Control.HasFocus($PARAM[list_id])] + Control.IsVisible(51)">Conditional</animation>
      </include>
    </includes>""",
    "xml/View_50_List.xml": """<includes>
      <include>ListLandscapeSlideAnimations</include>
      <include name="ListFocusAnimations">
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
        <animation effect="fade" start="100" end="0" time="300" condition="!Control.HasFocus($PARAM[list_id])">Conditional</animation>
      </include>
    </includes>""",
    "xml/Includes_PVR.xml": """<includes>
      <include name="ChannelManagerList"><animation effect="fade" start="100" end="60" time="0" condition="!Control.HasFocus($PARAM[list_id])">conditional</animation></include>
    </includes>""",
    "xml/Includes_Animations.xml": """<includes>
      <include name="WidgetVisibilityAnimations"><animation condition="!Control.HasFocus($PARAM[list_id]) + ControlGroup(2000).HasFocus" reversible="true"><effect type="faded" start="100" end="80" time="300" /></animation></include>
    </includes>""",
    "xml/Includes_MediaMenu.xml": """<includes><include name="AutoLockView"><control type="button"><onclick>Skin.TimerStart(autolock_view_timer)</onclick></control></include></includes>""",
    "xml/Timers.xml": """<timers>
      <timer><name>wall_scroll_timer</name><start reset="true">Control.HasFocus($PARAM[list_id])</start><stop>true</stop><onstop>Container.SetViewMode(54)</onstop><onstop>Container.SetViewMode(55)</onstop></timer>
      <timer><name>posterflow_scroll_timer</name><start reset="true">Control.HasFocus($PARAM[list_id])</start><stop>true</stop></timer>
      <timer><name>autolock_view_timer</name><start reset="true">Control.HasFocus($PARAM[list_id])</start><stop>true</stop><onstop>Skin.SetString(ViewLocked,true)</onstop><onstop>Skin.SetString(ViewLocked,true)</onstop><onstop>Skin.SetString(ViewLocked,true)</onstop></timer>
      <timer><name>autoplay_trailer_timer</name><start reset="true">Control.HasFocus($PARAM[list_id])</start><stop>true</stop><onstop>Skin.SetString(TrailerPlaying,true)</onstop><onstop>Skin.SetString(TrailerPlaying,true)</onstop></timer>
    </timers>""",
    "fonts/Inter-Regular.ttf": b"test-font",
    "resources/icon.png": b"test-icon",
}


HELPER_FILES = {
    "addon.xml": """<?xml version="1.0"?>
<addon id="script.nimbus.helper" name="Nimbus Helper" version="0.0.52" provider-name="Ivar Brandt">
  <requires>
    <import addon="xbmc.python" version="3.0.0"/>
    <import addon="script.module.requests" version="2.19.1"/>
    <import addon="script.module.pil" version="1.1.7"/>
  </requires>
  <extension point="xbmc.python.library" library="resources/lib/default.py"/>
  <extension point="xbmc.service" library="resources/lib/service.py" start="startup"/>
  <extension point="xbmc.addon.metadata"><license>GPL-2.0-only</license><description>Nimbus Helper</description><assets><icon>icon.png</icon></assets></extension>
</addon>""",
    "resources/lib/default.py": "from modules.router import routing\nrouting()\n",
    "resources/lib/modules/__init__.py": "",
    "resources/lib/modules/cpath_maker.py": """import xbmc
from modules import xmls
settings_path = "special://profile/addon_data/script.nimbus.helper/"
class CPaths:
    max_widgets = 50
    def __init__(self, setting):
        self.setting = setting
    def fetch_current_cpaths(self):
        return {}
    def add_cpath_to_database(self, *args):
        return None

(
    movies_widgets_xml,
    tvshows_widgets_xml,
    custom1_widgets_xml,
    custom2_widgets_xml,
    custom3_widgets_xml,
) = (
    "script-nimbus-widget_movies",
    "script-nimbus-widget_tvshows",
    "script-nimbus-widget_custom1",
    "script-nimbus-widget_custom2",
    "script-nimbus-widget_custom3",
)
default_xmls = {
    "movie.widget": (movies_widgets_xml, xmls.default_widget, "MovieWidgets"),
    "tvshow.widget": (tvshows_widgets_xml, xmls.default_widget, "TVShowWidgets"),
    "custom1.widget": (custom1_widgets_xml, xmls.default_widget, "Custom1Widgets"),
    "custom2.widget": (custom2_widgets_xml, xmls.default_widget, "Custom2Widgets"),
    "custom3.widget": (custom3_widgets_xml, xmls.default_widget, "Custom3Widgets"),
}
main_include_dict = {
    "movie": {"main_menu": None, "widget": "MovieWidgets"},
    "tvshow": {"main_menu": None, "widget": "TVShowWidgets"},
    "custom1": {"main_menu": None, "widget": "Custom1Widgets"},
    "custom2": {"main_menu": None, "widget": "Custom2Widgets"},
    "custom3": {"main_menu": None, "widget": "Custom3Widgets"},
}
    def make_widget_xml(self):
        media_type_to_xml = {
            "movie": movies_widgets_xml,
            "tvshow": tvshows_widgets_xml,
            "custom1": custom1_widgets_xml,
            "custom2": custom2_widgets_xml,
            "custom3": custom3_widgets_xml,
        }
        media_type_id = {
            "movie": 19010,
            "tvshow": 22010,
            "custom1": 23010,
            "custom2": 24010,
            "custom3": 25010,
        }
def remake_all_cpaths(silent=False):
    for item in (
        "movie.widget",
        "tvshow.widget",
        "custom1.widget",
        "custom2.widget",
        "custom3.widget",
    ):
        pass
""",
    "resources/lib/modules/search_utils.py": 'SETTINGS_PATH = "special://profile/addon_data/script.nimbus.helper/"\n',
    "resources/lib/modules/xmls.py": 'history = "RunScript(script.nimbus.helper,mode=re_search)"\n',
    "resources/lib/modules/custom_actions.py": """import requests
import sys
def check_api_key(api_key):
    return requests.get("https://mdblist.com/api/", timeout=5)
def validate_api_key(api_key, silent=True):
    return check_api_key(api_key)
def set_api_key():
    return validate_api_key("secret")
def check_api_key_on_load():
    return validate_api_key("")
def set_widget_count():
    return None
def show_changelog():
    return None
""",
    "resources/lib/service.py": "from modules.monitors.ratings import RatingsMonitor\n",
    "resources/lib/modules/apis/mdblist.py": "https://mdblist.com/api/",
    "resources/lib/modules/apis/tmdb.py": "https://api.themoviedb.org/3/",
    "resources/lib/modules/monitors/ratings.py": "class RatingsMonitor: pass\n",
}


class NimbusFoundationBuilderTests(unittest.TestCase):
    def build_fixture(self, destination):
        archives = {
            builder.NIMBUS_REPO: make_archive("skin.nimbus-test", NIMBUS_FILES),
            builder.HELPER_REPO: make_archive("script.nimbus.helper-test", HELPER_FILES),
        }

        def fake_fetch(repository, commit):
            self.assertIn(repository, archives)
            self.assertTrue(commit)
            return archives[repository]

        return builder.build(destination, fetcher=fake_fetch)

    def test_skin_is_a_real_nimbus_derived_package(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "dist"
            paths = self.build_fixture(output)
            with zipfile.ZipFile(paths["skin"]) as archive:
                names = set(archive.namelist())
                self.assertIn("skin.cineva/xml/Home.xml", names)
                self.assertIn("skin.cineva/xml/Includes_Home.xml", names)
                self.assertIn("skin.cineva/xml/Includes_HomeLayouts.xml", names)
                self.assertIn("skin.cineva/xml/script-nimbus-widget_home.xml", names)
                self.assertIn('<include name="HomeWidgets">', archive.read("skin.cineva/xml/script-nimbus-widget_home.xml").decode("utf-8"))
                flixpanel = archive.read("skin.cineva/xml/Includes_FlixPanel.xml").decode("utf-8")
                self.assertIn("IMDb ,", flixpanel)
                self.assertIn("Rating.tomatoes.Percent", flixpanel)
                self.assertIn("RT ,%", flixpanel)
                self.assertNotIn("plugin.video.otaku", flixpanel)
                self.assertIn("skin.cineva/xml/View_54_Flix.xml", names)
                for filename, include_name in builder.DEFAULT_SKIN_INCLUDE_NAMES.items():
                    member = f"skin.cineva/xml/{filename}.xml"
                    self.assertIn(member, names)
                    include_xml = archive.read(member).decode("utf-8")
                    self.assertIn(f'<include name="{include_name}">', include_xml)
                    ET.fromstring(include_xml)
                self.assertIn("skin.cineva/fonts/Inter-Regular.ttf", names)
                self.assertIn("skin.cineva/LICENSE.txt", names)
                self.assertIn("skin.cineva/NOTICE.txt", names)
                manifest = archive.read("skin.cineva/addon.xml").decode()
                self.assertIn('id="skin.cineva"', manifest)
                self.assertIn('version="0.8.3"', manifest)
                self.assertIn('addon="xbmc.gui" version="5.18.0"', manifest)
                self.assertIn('addon="script.cineva.nimbus" version="0.1.1"', manifest)
                self.assertNotIn("script.nimbus.helper", manifest)
                home_includes = archive.read("skin.cineva/xml/Includes_Home.xml").decode()
                self.assertNotIn("check_for_update", home_includes)
                self.assertNotIn("check_for_profile_change", home_includes)
                self.assertIn("mode=set_widget_count", home_includes)
                settings = archive.read("skin.cineva/xml/SkinSettings.xml").decode()
                self.assertIn("mode=manage_widgets", settings)
                self.assertNotIn("mode=set_api_key", settings)
                self.assertNotIn("mode=delete_all_ratings", settings)
                self.assertNotIn("skin.nimbus", settings)
                baseline = archive.read("skin.cineva/CINEVA_BASELINE.json").decode()
                self.assertIn(builder.NIMBUS_SHA, baseline)
                self.assertIn("CC BY-SA 4.0", baseline)
            with zipfile.ZipFile(paths["bridge"]) as archive:
                cpaths = archive.read(
                    "script.cineva.nimbus/resources/lib/modules/cpath_maker.py"
                ).decode("utf-8")
                self.assertIn("max_widgets = 4", cpaths)
                self.assertIn('"home.widget"', cpaths)
                self.assertIn('"home": 18010', cpaths)
                self.assertIn("CINEVA_NIMBUS_HOME_WIDGETS_READY=%d", cpaths)
                for title in (
                    "Continue Watching Movies",
                    "In Progress Shows",
                    "Trending Movies",
                    "Trending TV Shows",
                ):
                    self.assertIn(title, cpaths)


    def test_addon_ratings_are_rendered_without_a_skin_api_key(self):
        with tempfile.TemporaryDirectory() as temp:
            skin = Path(temp) / "skin.cineva"
            xml = skin / "xml"
            xml.mkdir(parents=True)
            (xml / "Includes_FlixPanel.xml").write_text(
                """<includes><include name="FlixPanel"><definition><control type="grouplist">
                <include content="FlixInfoIcon">
                  <param name="flixlabel" value="$INFO[Container($PARAM[id]).ListItem.Rating]★"/>
                  <param name="visible" value="!String.IsEmpty(Container($PARAM[id]).ListItem.Rating) + !ListItem.IsCollection + [$EXP[isEpisode] | String.StartsWith(Container.PluginName,plugin.video.otaku)]"/>
                </include>
                </control></definition></include></includes>""",
                encoding="utf-8",
            )
            builder.apply_cineva_addon_ratings(skin)
            root = ET.parse(xml / "Includes_FlixPanel.xml").getroot()
            labels = [
                {param.get("name"): param.get("value") for param in node.findall("param")}
                for node in root.findall(".//include[@content='FlixInfoIcon']")
            ]
            imdb = next(item for item in labels if "IMDb ," in item.get("flixlabel", ""))
            tomatoes = next(item for item in labels if "RT ,%" in item.get("flixlabel", ""))
            self.assertIn("ListItem.Rating", imdb["visible"])
            self.assertNotIn("valid_api_key", imdb["visible"])
            self.assertIn("Rating.tomatoes.Percent", tomatoes["flixlabel"])
            self.assertNotIn("valid_api_key", tomatoes["visible"])

    def test_flix_focus_layouts_receive_their_real_container_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.build_fixture(Path(temp) / "dist")
            with zipfile.ZipFile(paths["skin"]) as archive:
                expected = {
                    "Includes.xml": ("$PARAM[group_id]50", 2),
                    "View_54_Flix.xml": ("54", 2),
                    "View_500_Wall.xml": ("500", 2),
                    "View_55_FlixScape.xml": ("55", 2),
                    "View_501_WallScape.xml": ("501", 2),
                    "View_51_PosterFlow.xml": ("51", 2),
                    "View_50_List.xml": ("$PARAM[list_id]", 1),
                }
                for filename, (list_id, count) in expected.items():
                    xml = archive.read(f"skin.cineva/xml/{filename}").decode("utf-8")
                    self.assertEqual(
                        xml.count(f'<param name="list_id" value="{list_id}" />'),
                        count,
                        filename,
                    )
                    ET.fromstring(xml)
                includes = archive.read("skin.cineva/xml/Includes.xml").decode("utf-8")
                self.assertNotIn('name="fallback_image"', includes)
                self.assertIn('name="fallback_icon"', includes)


    def test_all_include_definitions_using_list_id_have_safe_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.build_fixture(Path(temp) / "dist")
            with zipfile.ZipFile(paths["skin"]) as archive:
                for filename in archive.namelist():
                    if not filename.endswith(".xml"):
                        continue
                    root = ET.fromstring(archive.read(filename))
                    for include in root.findall(".//include[@name]"):
                        block = ET.tostring(include, encoding="unicode")
                        if "$PARAM[list_id]" not in block:
                            continue
                        list_params = [
                            param for param in include.findall("param")
                            if param.get("name") == "list_id"
                        ]
                        self.assertEqual(
                            len(list_params), 1, f"{filename}:{include.get('name')}"
                        )
                        self.assertTrue(
                            list_params[0].get("default"),
                            f"{filename}:{include.get('name')} missing default",
                        )
                        self.assertNotIn(
                            "value", list_params[0].attrib,
                            f"{filename}:{include.get('name')} uses call-site value syntax",
                        )
                        self.assertIsNotNone(
                            include.find("definition"),
                            f"{filename}:{include.get('name')} body is not wrapped in definition",
                        )
                        self.assertFalse(
                            [
                                child for child in include
                                if child.tag not in ("param", "definition")
                            ],
                            f"{filename}:{include.get('name')} has content outside definition",
                        )


    def test_parameterized_focus_conditions_are_preserved_in_valid_include_definitions(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.build_fixture(Path(temp) / "dist")
            with zipfile.ZipFile(paths["skin"]) as archive:
                preserved = 0
                for filename in archive.namelist():
                    if not filename.endswith(".xml"):
                        continue
                    root = ET.fromstring(archive.read(filename))
                    for include in root.findall(".//include[@name]"):
                        block = ET.tostring(include, encoding="unicode")
                        count = block.count("Control.HasFocus($PARAM[list_id])")
                        if not count:
                            continue
                        list_params = [
                            param for param in include.findall("param")
                            if param.get("name") == "list_id"
                        ]
                        self.assertEqual(
                            len(list_params), 1, f"{filename}:{include.get('name')}"
                        )
                        self.assertTrue(
                            list_params[0].get("default"),
                            f"{filename}:{include.get('name')} missing list_id default",
                        )
                        self.assertIsNotNone(
                            include.find("definition"),
                            f"{filename}:{include.get('name')} body is not wrapped",
                        )
                        self.assertFalse(
                            [
                                child for child in include
                                if child.tag not in ("param", "definition")
                            ],
                            f"{filename}:{include.get('name')} has content outside definition",
                        )
                        preserved += count
                self.assertGreater(preserved, 0)

                animations = ET.fromstring(
                    archive.read("skin.cineva/xml/Includes_Animations.xml")
                )
                widget_visibility = animations.find(
                    './/include[@name="WidgetVisibilityAnimations"]/definition/animation'
                )
                self.assertEqual(
                    widget_visibility.get("condition"),
                    "!Control.HasFocus($PARAM[list_id]) + ControlGroup(2000).HasFocus",
                )
                expected_home_focus = {
                    "Includes_HomeLayouts.xml": 4,
                    "View_51_PosterFlow.xml": 1,
                    "View_54_Flix.xml": 1,
                    "View_55_FlixScape.xml": 2,
                }
                for filename, expected in expected_home_focus.items():
                    root = ET.fromstring(
                        archive.read("skin.cineva/xml/" + filename)
                    )
                    dynamic = [
                        animation for animation in root.findall(".//animation")
                        if "Control.HasFocus($PARAM[list_id])"
                        in animation.get("condition", "")
                    ]
                    self.assertEqual(len(dynamic), expected, filename)


    def test_global_timers_remove_unbound_include_parameters_and_keep_manual_starts(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.build_fixture(Path(temp) / "dist")
            with zipfile.ZipFile(paths["skin"]) as archive:
                timers_text = archive.read("skin.cineva/xml/Timers.xml").decode("utf-8")
                timers = ET.fromstring(timers_text)
                expected_onstop_counts = {
                    "wall_scroll_timer": 2,
                    "posterflow_scroll_timer": 0,
                    "autolock_view_timer": 3,
                    "autoplay_trailer_timer": 2,
                }
                timer_nodes = {
                    node.findtext("name"): node for node in timers.findall("timer")
                }
                self.assertEqual(set(timer_nodes), set(expected_onstop_counts))
                self.assertNotIn("$PARAM[list_id]", timers_text)
                for name, onstop_count in expected_onstop_counts.items():
                    node = timer_nodes[name]
                    self.assertIsNone(node.find("start"), name)
                    self.assertIsNotNone(node.find("stop"), name)
                    self.assertEqual(len(node.findall("onstop")), onstop_count, name)

                includes = archive.read("skin.cineva/xml/Includes.xml").decode("utf-8")
                for name in (
                    "wall_scroll_timer",
                    "posterflow_scroll_timer",
                    "autoplay_trailer_timer",
                ):
                    self.assertIn(f"Skin.TimerStart({name})", includes)
                media_menu = archive.read(
                    "skin.cineva/xml/Includes_MediaMenu.xml"
                ).decode("utf-8")
                self.assertIn("Skin.TimerStart(autolock_view_timer)", media_menu)


    def test_bridge_keeps_local_widget_logic_and_api_free_service_entry(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self.build_fixture(Path(temp) / "dist")
            with zipfile.ZipFile(paths["bridge"]) as archive:
                names = set(archive.namelist())
                self.assertIn("script.cineva.nimbus/resources/lib/modules/cpath_maker.py", names)
                self.assertIn("script.cineva.nimbus/resources/lib/modules/search_utils.py", names)
                self.assertIn("script.cineva.nimbus/resources/lib/modules/router.py", names)
                self.assertIn("script.cineva.nimbus/LICENSE-NIMBUS.txt", names)
                self.assertIn("script.cineva.nimbus/resources/lib/service.py", names)
                self.assertFalse(any("/apis/" in name or "/monitors/" in name for name in names))
                manifest = archive.read("script.cineva.nimbus/addon.xml").decode()
                self.assertIn('id="script.cineva.nimbus"', manifest)
                self.assertIn('point="xbmc.service"', manifest)
                self.assertIn('library="resources/lib/service.py"', manifest)
                self.assertNotIn("script.module.requests", manifest)
                self.assertNotIn("script.module.pil", manifest)
                router = archive.read("script.cineva.nimbus/resources/lib/modules/router.py").decode()
                self.assertIn('mode == "manage_widgets"', router)
                self.assertIn('"toggle_search_provider"', router)
                self.assertNotIn("MDbListClient", router)
                service = archive.read("script.cineva.nimbus/resources/lib/service.py").decode()
                self.assertIn("CINEVA_NIMBUS_BRIDGE_SERVICE_STARTED", service)
                self.assertNotIn("requests", service.lower())
                self.assertNotIn("urlopen", service.lower())
                self.assertNotIn("http://", service.lower())
                self.assertNotIn("https://", service.lower())
                actions = archive.read("script.cineva.nimbus/resources/lib/modules/custom_actions.py").decode()
                self.assertNotIn("import requests", actions)
                for name in builder.API_FUNCTIONS:
                    self.assertNotIn(f"def {name}(", actions)
                cpath = archive.read("script.cineva.nimbus/resources/lib/modules/cpath_maker.py").decode()
                self.assertIn("script.cineva.nimbus", cpath)
                self.assertNotIn("script.nimbus.helper", cpath)

    def test_cineva_visual_layer_adds_netflix_palette_and_brand_without_replacing_nimbus_controls(self):
        palette_names = (
            "primary_background", "dialog_tint", "dialog_bg", "dialog_bg2",
            "dialog_bg3", "button_focus", "button_focus2", "focused_text",
            "unfocused_text", "artwork_dim", "accent_color", "selected",
            "keyboard_selected", "primary_content_panel_bg", "background",
            "bg_overlay", "red",
        )
        with tempfile.TemporaryDirectory() as temp:
            skin = Path(temp)
            (skin / "colors").mkdir()
            (skin / "xml").mkdir()
            color_xml = "<colors>" + "".join(
                f'<color name="{name}">FFFFFFFF</color>' for name in palette_names
            ) + "</colors>"
            (skin / "colors/defaults.xml").write_text(color_xml, encoding="utf-8")
            home_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<window><defaultcontrol>9000</defaultcontrol><controls><include>DefaultBackground</include>'
                '<control type="fixedlist" id="9000"/></controls></window>'
            )
            (skin / "xml/Home.xml").write_text(home_xml, encoding="utf-8")

            builder.apply_cineva_visuals(skin)

            colors = ET.parse(skin / "colors/defaults.xml").getroot()
            values = {node.get("name"): node.text for node in colors.findall("color")}
            self.assertEqual(values["accent_color"], "FFE50914")
            self.assertEqual(values["button_focus"], "FFE50914")
            self.assertEqual(values["selected"], "FFE50914")
            self.assertEqual(values["background"], "FF000000")
            self.assertEqual(values["unfocused_text"], "FFF5F5F1")

            home = ET.parse(skin / "xml/Home.xml").getroot()
            self.assertEqual(home.findtext("defaultcontrol"), "20000")
            controls = home.find("controls")
            self.assertIsNotNone(controls.find("./include"))
            self.assertIsNotNone(controls.find("./control[@id='9000']"))
            brand = controls.find("./control[@id='19990']")
            self.assertIsNotNone(brand)
            self.assertEqual(brand.findtext("./control[@type='label']/label"), "[B]CINÉVA[/B]")
            self.assertEqual(brand.findtext("./control[@type='label']/font"), "font36_title")
            self.assertEqual(brand.findtext("./control[@type='image']/texture"), "colors/white.png")

    def test_cineva_home_layout_uses_horizontal_netflix_navigation_and_hero(self):
        with tempfile.TemporaryDirectory() as temp:
            skin = Path(temp)
            (skin / "xml").mkdir()
            menu = """<control type="group">
					<left>-540</left>
					<animation type="Conditional" condition="!ControlGroup(2000).HasFocus + !Control.IsVisible(20000) + !Control.IsVisible(20001)" reversible="true">
						<effect type="slide" start="0" end="540" time="500" tween="cubic" easing="inout" />
					</animation>
					<include>OpenClose_Left</include>
					<include content="MenuContentPanel">
						<param name="width" value="549"/>
					</include>
					<control type="fixedlist" id="9000">
						<left>25</left>
						<top>215</top>
            <width>825</width>
						<height>605</height>
						<movement>7</movement>
						<onright>SetFocus($INFO[Container(9000).ListItem.Property(menu_id)])</onright>
						<onback>700</onback>
						<onup>700</onup>
						<ondown>9000</ondown>
						<include content="List">
              <param name="id" value="9000" />
            </include>
					</control>
					<control type="group">
						<left>65</left>
						<top>70</top>
						<width>343</width>
					</control>
				</control>"""
            home = (
                '<window><defaultcontrol>20000</defaultcontrol><controls>'
                '<control type="group" id="2000"><top>510</top></control>'
                '<control type="group"><top>90</top><left>90</left><width>380</width>'
                '<control type="label"><label>$INFO[System.Time]</label></control></control>'
                + menu +
                '<control type="rss"></control></controls></window>'
            )
            (skin / "xml/Home.xml").write_text(home.replace("\n", "\r\n"), encoding="utf-8")
            (skin / "xml/Includes_FlixPanel.xml").write_text(
                '<includes><include name="FlixPanel"><definition><control type="group">'
                '<left>50</left>\n\t\t\t\t<width>815</width>\n\t\t\t\t<top>45</top>'
                '</control></definition></include></includes>',
                encoding="utf-8",
            )

            (skin / "xml/Includes.xml").write_text(
                '<includes><include file="Includes_Home.xml" /></includes>',
                encoding="utf-8",
            )
            (skin / "xml/Includes_Home.xml").write_text(
                '<includes>\n\t<include name="WidgetGroupListCommon">\n'
                '\t\t<orientation>vertical</orientation>\n'
                '\t\t<height>33000</height>\n\t\t<itemgap>-100</itemgap>\n'
                '\t\t<onup>20000</onup>\n\t\t<ondown>20001</ondown>\n'
                '\t\t<usecontrolcoords>true</usecontrolcoords>\n\t</include>\n</includes>',
                encoding="utf-8",
            )

            builder.apply_cineva_home_layout(skin)
            (skin / "xml/SkinSettings.xml").write_text(
                '<window><controls><control type="fixedlist" id="9000"><content><item><label>General</label></item><item><label>Home</label></item><item><label>Widget options</label></item></content><onright>10000</onright></control></controls></window>',
                encoding="utf-8",
            )
            (skin / "xml/script-nimbus-widget_home.xml").write_text("", encoding="utf-8")
            builder.apply_cineva_widget_dashboard(skin)

            root = ET.parse(skin / "xml/Home.xml").getroot()
            self.assertEqual(root.findtext("defaultcontrol"), "20000")
            self.assertEqual(root.find("./controls/control[@id='2000']/top").text, "575")
            menu_list = root.find(".//control[@id='9000']")
            self.assertEqual(menu_list.findtext("orientation"), "horizontal")
            self.assertEqual(menu_list.findtext("left"), "270")
            self.assertEqual(menu_list.findtext("top"), "26")
            self.assertEqual(menu_list.findtext("width"), "1260")
            self.assertIsNotNone(menu_list.find("./include[@content='CinevaMainMenuList']"))
            self.assertEqual(
                [item.findtext("label") for item in menu_list.findall("./content/item")],
                ["Home", "Movies", "TV Shows", "Add-ons"],
            )
            home_group = root.find(".//control[@id='18000']")
            self.assertIsNotNone(home_group)
            self.assertEqual(home_group.findtext("defaultcontrol"), "18001")
            delayed = home_group.find("./include[@content='Visible_Right_Delayed']")
            self.assertIsNotNone(delayed)
            self.assertEqual(delayed.find("param").get("value"), "home")
            widget_list = home_group.find("./control[@id='18001']")
            self.assertIsNotNone(widget_list.find("./include[.='WidgetGroupListCommon']"))
            self.assertIsNotNone(widget_list.find("./include[.='HomeWidgets']"))
            self.assertEqual(widget_list.findtext("pagecontrol"), "18099")
            animation = widget_list.find("./include[@content='Animation_Widget_Poster_Slide']")
            self.assertEqual(animation.find("param").get("name"), "container")
            arrows = home_group.find("./include[@content='WidgetUpDownArrows']")
            self.assertIsNotNone(arrows)
            self.assertEqual(arrows.find("param").get("value"), "18001")
            scrollbar = home_group.find("./include[@content='WidgetScrollbar']")
            self.assertIsNotNone(scrollbar)
            self.assertEqual(scrollbar.get("condition"), "Skin.HasSetting(touchmode)")
            self.assertEqual(scrollbar.find("param").get("name"), "scrollbar_id")
            self.assertIsNone(widget_list.find("./include[@content='WidgetUpDownArrows']"))
            self.assertIsNone(widget_list.find("./include[@content='WidgetScrollbar']"))
            placeholder = ET.parse(skin / "xml/script-nimbus-widget_home.xml").getroot()
            self.assertIsNotNone(placeholder.find("./include[@name='HomeWidgets']"))
            self.assertIsNone(home_group.find(".//control[@id='18005']"))
            self.assertIsNone(root.find(".//control[@id='19005']"))
            self.assertIsNone(root.find(".//control[@id='22005']"))
            clock_group = root.find(".//control[@type='group'][top='90'][left='90']")
            self.assertIsNotNone(clock_group)
            self.assertIn(
                "!String.IsEqual(Container(9000).ListItem.Property(id),home)",
                clock_group.findtext("visible"),
            )
            self.assertIsNone(root.find(".//include[@content='MenuContentPanel']"))
            flix = ET.parse(skin / "xml/Includes_FlixPanel.xml").getroot()
            self.assertEqual(flix.findtext(".//include[@name='FlixPanel']//left"), "72")
            self.assertEqual(flix.findtext(".//include[@name='FlixPanel']//top"), "150")
            ET.parse(skin / "xml/Includes_Cineva.xml")
            skin_includes = ET.parse(skin / "xml/Includes.xml").getroot()
            self.assertIsNotNone(skin_includes.find("./include[@file='Includes_Cineva.xml']"))
            self.assertIsNotNone(skin_includes.find("./include[@file='script-nimbus-widget_home.xml']"))
            settings = ET.parse(skin / "xml/SkinSettings.xml").getroot()
            manager_group = settings.find(".//control[@id='18000']")
            self.assertIsNotNone(manager_group)
            self.assertIn("MANAGE HOME WIDGETS", " ".join(
                button.findtext("label") or ""
                for button in manager_group.findall(".//control[@type='button']")
            ))
            home_includes = ET.parse(skin / "xml/Includes_Home.xml").getroot()
            common = home_includes.find(".//include[@name='WidgetGroupListCommon']")
            self.assertEqual(common.findtext("onback"), "SetFocus(9000)")

    def test_archives_are_byte_for_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "dist"
            first = self.build_fixture(output)
            first_hashes = {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in first.items()
            }
            second = self.build_fixture(output)
            second_hashes = {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in second.items()
            }
            self.assertEqual(first_hashes, second_hashes)



class NimbusWorkflowPathTests(unittest.TestCase):

    def test_gui_runtime_skips_unrelated_blocked_microsoft_apt_source(self):
        repo_root = Path(__file__).resolve().parents[1]
        for relative in (
            ".github/workflows/nimbus-foundation.yml",
            ".github/workflows/kodi-gui-test.yml",
        ):
            source = (repo_root / relative).read_text(encoding="utf-8")
            self.assertIn('grep -q "packages.microsoft.com"', source)
            self.assertIn('sudo rm -f "$source"', source)
            self.assertLess(
                source.index('sudo rm -f "$source"'),
                source.index("sudo apt-get update"),
            )

    def test_workflow_uses_the_builder_skin_version(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("skin.cineva-0.8.2-nimbus.zip", source)
        self.assertIn('manifest.get("version") == "0.8.2"', source)

    def test_first_boot_reads_kodis_actual_flatpak_log_location(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn('KODI_DATA="$HOME/.var/app/tv.kodi.Kodi/data"', source)
        self.assertIn('KODI_LOG="$KODI_DATA/temp/kodi.log"', source)
        self.assertNotIn('KODI_LOG="$USERDATA/temp/kodi.log"', source)

    def test_first_boot_session_stays_live_for_jsonrpc_activation(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        boot = source.index("if ! boot_kodi_once 1; then")
        activation = source.index('initial_skin = rpc_retry("Settings.GetSettingValue"')
        activation_preamble = source[boot:activation]
        self.assertIn("ss -ltn | grep -q ':9090'", activation_preamble)
        self.assertIn("First-boot Kodi JSON-RPC listener is ready", activation_preamble)
        self.assertNotIn("flatpak kill --user tv.kodi.Kodi", activation_preamble)
        self.assertNotIn("pkill -TERM -x kodi.bin", activation_preamble)
        self.assertNotIn("for launch_attempt in 1 2", source)
        self.assertNotIn("launch_kodi()", source)
        self.assertNotIn("stop_kodi_attempt()", source)

    def test_skin_is_enabled_and_selected_after_kodi_starts(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn('"addonid":"script.cineva.nimbus", "enabled":True', source)
        self.assertIn('"addonid":"skin.cineva", "enabled":True', source)
        self.assertIn('"setting":"lookandfeel.skin", "value":"skin.cineva"', source)
        self.assertIn("before_skin_loads", source)
        self.assertLess(source.index("if ! boot_kodi_once 1; then"), source.index('initial_skin = rpc_retry('))

    def test_skin_first_run_welcome_generates_includes_before_home_capture(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn('currentwindow",{}).get("id") in (1112, 11112)', source)
        self.assertIn("window_id == 12002 or (window_id == 10100 and control_label == \"ok\")", source)
        self.assertIn("Acknowledging Nimbus first-run welcome", source)
        self.assertIn("tools/test-fixtures/plugin.video.pov", source)
        self.assertLess(source.index('cp -a "$POV_FIXTURE"/. "$POV_ADDON"/'), source.index("if ! boot_kodi_once 1; then"))
        self.assertIn("required_default_includes", source)
        self.assertIn("script-nimbus-widget_home.xml", source)
        self.assertIn("CINEVA_NIMBUS_HOME_WIDGETS_READY=4", source)
        self.assertIn("before_welcome_home_inits", source)
        self.assertIn("Window Init (Home.xml)", source)
        self.assertNotIn("before_welcome_skin_loads", source)
        self.assertIn("Nimbus first-run defaults generated and skin reloaded", source)
        self.assertIn("window_id == 12002", source)
        self.assertIn("nimbus-first-run-failure.png", source)


    def test_nimbus_workflow_captures_addon_rating_badges(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("cineva-nimbus-home-ratings.png", source)
        self.assertIn("Container(18011).ListItem.Rating", source)
        self.assertIn("Rating.tomatoes.Percent", source)
        self.assertIn("CINEVA_NIMBUS_ADDON_RATINGS_READY=IMDb 8.4; RT 92%", source)

    def test_legacy_gui_scroll_probe_handles_empty_current_item_labels(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/kodi-gui-test.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("def info_int(values, key):", source)
        self.assertIn('scrolled_position = info_int(scrolled_labels, "Container(9001).CurrentItem")', source)
        self.assertIn('scrolled_item_label == "Barbie"', source)
        self.assertIn('restored_position = info_int(restored_labels, "Container(9001).CurrentItem")', source)

class PosterArtworkFontTests(unittest.TestCase):

    def test_legacy_poppins_remains_preferred_when_available(self):
        with tempfile.TemporaryDirectory() as temp:
            previous = Path.cwd()
            try:
                os.chdir(temp)
                fonts = Path("skin.cineva/fonts")
                fonts.mkdir(parents=True)
                (fonts / "Poppins-SemiBold.ttf").write_bytes(b"poppins")
                (fonts / "Inter-SemiBold.ttf").write_bytes(b"inter")
                self.assertEqual(
                    poster_artwork.resolve_clearlogo_font(),
                    Path("skin.cineva/fonts/Poppins-SemiBold.ttf"),
                )
            finally:
                os.chdir(previous)

    def test_nimbus_inter_semibold_is_used_when_poppins_is_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            previous = Path.cwd()
            try:
                os.chdir(temp)
                fonts = Path("skin.cineva/fonts")
                fonts.mkdir(parents=True)
                (fonts / "Inter-SemiBold.ttf").write_bytes(b"inter")
                self.assertEqual(
                    poster_artwork.resolve_clearlogo_font(),
                    Path("skin.cineva/fonts/Inter-SemiBold.ttf"),
                )
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
