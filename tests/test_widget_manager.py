import importlib.util
import json
import pathlib
import sys
import struct
import types
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANAGER = ROOT / "tools/script.cineva.widgets/resources/lib/manager.py"
SETTINGS = ROOT / "tools/script.cineva.widgets/resources/settings.xml"

class FakeVFS:
    files = {}
    @staticmethod
    def translatePath(path): return path
    @classmethod
    def exists(cls, path): return path in cls.files
    @staticmethod
    def mkdirs(path): return True
    class File:
        def __init__(self, path, mode):
            self.path = path
            self.buffer = FakeVFS.files.get(path, "") if mode == "r" else ""
        def read(self): return self.buffer
        def write(self, value):
            self.buffer += value
            FakeVFS.files[self.path] = self.buffer
        def close(self): pass

class FakeDialog:
    selection = -1
    def select(self, *args, **kwargs): return self.selection
    def ok(self, *args, **kwargs): pass
    def input(self, *args, **kwargs): return ""
    def yesno(self, *args, **kwargs): return False

class KodiManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builtins = []
        cls.info_labels = {}
        cls.played = []
        xbmc = types.ModuleType("xbmc")
        xbmc.LOGINFO, xbmc.LOGWARNING = 1, 2
        xbmc.executeJSONRPC = lambda payload: json.dumps({"result": {"addons": []}})
        xbmc.executebuiltin = lambda command: cls.builtins.append(command)
        xbmc.getInfoLabel = lambda label: cls.info_labels.get(label, "")
        class FakePlayer:
            def play(self, path):
                cls.played.append(path)
        xbmc.Player = FakePlayer
        xbmc.getCondVisibility = lambda condition: True
        xbmc.log = lambda *args: None
        addon_mod = types.ModuleType("xbmcaddon")
        addon_mod.Addon = lambda: object()
        gui = types.ModuleType("xbmcgui")
        gui.Dialog = FakeDialog
        vfs = types.ModuleType("xbmcvfs")
        vfs.translatePath, vfs.exists = FakeVFS.translatePath, FakeVFS.exists
        vfs.mkdirs, vfs.File = FakeVFS.mkdirs, FakeVFS.File
        sys.modules.update({"xbmc": xbmc, "xbmcaddon": addon_mod,
                            "xbmcgui": gui, "xbmcvfs": vfs})
        spec = importlib.util.spec_from_file_location("cineva_manager", MANAGER)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        FakeVFS.files.clear()
        self.builtins.clear()
        self.info_labels.clear()
        self.played.clear()

    def test_skin_settings_exposes_twelve_numbered_widget_slots(self):
        builder_path = ROOT / "tools/build_skin_archive.py"
        spec = importlib.util.spec_from_file_location("cineva_builder", builder_path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        source = b'<window id="10035"><controls><control type="button" id="6"><label>OLD</label></control></controls></window>'
        rendered = ET.fromstring(builder.update_xml(source, "skin.cineva/xml/SkinSettings.xml"))
        controls = rendered.find("controls")
        buttons = controls.findall("control[@type='button']")
        self.assertEqual(len(buttons), 12)
        labels = [button.findtext("label", "") for button in buttons]
        for prefix in ("Cineva.Widget", "Cineva.MovieWidget", "Cineva.ShowWidget"):
            for slot in range(1, 5):
                self.assertTrue(any(f"$INFO[Skin.String({prefix}{slot}.Name)]" in label
                                    for label in labels))
        actions = [button.findtext("onclick", "") for button in buttons]
        for screen in ("home", "movies", "tvshows"):
            for slot in range(1, 5):
                self.assertTrue(any(f"screen={screen}&amp;slot={slot}" in action or
                                    f"screen={screen}&slot={slot}" in action for action in actions))
        self.assertFalse(any("screen=search" in action or "screen=mylist" in action for action in actions))
        self.assertFalse(any(button.get("id") == "6" for button in buttons))

    def test_poster_fallback_is_cinematic_art_not_a_play_icon(self):
        builder_path = ROOT / "tools/build_skin_archive.py"
        spec = importlib.util.spec_from_file_location("cineva_builder_poster_art", builder_path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        artwork = builder.poster_placeholder_png()
        self.assertTrue(artwork.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack(">II", artwork[16:24]), (342, 513))
        self.assertNotIn(b"play glyph", builder.poster_placeholder_png.__doc__.encode("utf-8"))

    def test_home_navigation_uses_no_missing_dash_texture(self):
        builder_path = ROOT / "tools/build_skin_archive.py"
        spec = importlib.util.spec_from_file_location("cineva_builder_home_texture", builder_path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        root = ET.fromstring(
            b'<window><controls>'
            b'<control type="button" id="1001"><texturenofocus>-</texturenofocus><label>HOME</label></control>'
            b'<control type="button" id="1002"><texturenofocus>black.png</texturenofocus><label>MOVIES</label></control>'
            b'</controls></window>'
        )
        builder.remove_missing_no_focus_textures(root)
        home = root.find(".//control[@id='1001']")
        movies = root.find(".//control[@id='1002']")
        self.assertIsNone(home.find("texturenofocus"))
        self.assertEqual(movies.findtext("texturenofocus"), "black.png")

    def test_skin_and_widget_helper_versions_are_upgradeable_and_consistent(self):
        helper = ET.parse(ROOT / "tools/script.cineva.widgets/addon.xml").getroot()
        with ZipFile(ROOT / "skin.cineva-0.5.8.zip") as archive:
            skin = ET.fromstring(archive.read("skin.cineva/addon.xml"))
        dependency = skin.find("./requires/import[@addon='script.cineva.widgets']")
        self.assertEqual(skin.attrib.get("version"), "0.5.8")
        self.assertEqual(helper.attrib.get("version"), "0.1.4")
        self.assertIsNotNone(dependency)
        self.assertEqual(dependency.attrib.get("version"), helper.attrib["version"])

    def test_widget_helper_is_not_advertised_as_a_video_plugin(self):
        addon_xml = ET.parse(ROOT / "tools/script.cineva.widgets/addon.xml").getroot()
        self.assertIsNone(addon_xml.find("./extension[@point='xbmc.python.pluginsource']"))
        self.assertIsNotNone(addon_xml.find("./extension[@point='xbmc.python.script']"))

    def test_json_rpc_handles_non_object_and_invalid_responses(self):
        original = self.module.xbmc.executeJSONRPC
        try:
            for raw in ('not-json', '[]', 'null', '{"error":{"message":"bad"}}'):
                self.module.xbmc.executeJSONRPC = lambda payload, value=raw: value
                self.assertIsNone(self.module.KodiRPC.call('Files.GetDirectory'))
        finally:
            self.module.xbmc.executeJSONRPC = original

    def test_json_rpc_handles_runtime_exceptions(self):
        original = self.module.xbmc.executeJSONRPC
        try:
            def fail(payload):
                raise RuntimeError("Kodi JSON-RPC unavailable")
            self.module.xbmc.executeJSONRPC = fail
            self.assertIsNone(self.module.KodiRPC.call('Addons.GetAddons'))
        finally:
            self.module.xbmc.executeJSONRPC = original

    def test_play_action_uses_selected_container_item_with_kodi_player(self):
        path = "plugin://plugin.video.pov/?action=play&id=1"
        self.info_labels["Container(9002).ListItem.File"] = path
        self.module.WidgetManager().run(action="play", container="9002")
        self.assertEqual(self.played, [path])

    def test_play_action_rejects_invalid_container_and_empty_item(self):
        self.info_labels["Container(9001).ListItem.File"] = ""
        manager = self.module.WidgetManager()
        manager.run(action="play", container="9999")
        manager.run(action="play", container="9001")
        manager.run(action="play", container="not-a-number")
        self.assertEqual(self.played, [])

    def test_screens_are_only_home_movies_tvshows(self):
        self.assertEqual(set(self.module.SCREENS), {"home", "movies", "tvshows"})

    def test_first_install_seeds_editable_pov_home_defaults(self):
        registry = self.module.WidgetManager().load()
        self.assertEqual(len(registry["home"]), 4)
        self.assertEqual(registry["home"][1]["name"], "In Progress Shows")
        self.assertTrue(all(w["path"].startswith("plugin://plugin.video.pov/") for w in registry["home"]))

    def test_clearing_all_home_widgets_does_not_restore_defaults(self):
        manager = self.module.WidgetManager()
        registry = manager.load()
        registry["home"] = []
        manager.save(registry)
        self.assertEqual(manager.load()["home"], [])

    def test_each_screen_has_independent_slots(self):
        manager = self.module.WidgetManager()
        registry = manager.load()
        registry["movies"] = [{"id":"m1","name":"Movies","path":"plugin://plugin.video.example/","addon":"plugin.video.example","content":"videos"}]
        manager.save(registry)
        again = manager.load()
        self.assertEqual(len(again["movies"]), 1)
        self.assertEqual(again["tvshows"], [])

    def test_empty_middle_slot_keeps_later_slot_number(self):
        manager = self.module.WidgetManager()
        registry = manager.load()
        registry['home'] = [registry['home'][0], {}, registry['home'][2]]
        manager.save(registry)
        reloaded = manager.load()
        self.assertEqual(reloaded['home'][1], {})
        self.assertEqual(reloaded['home'][2]['name'], 'Trending Movies')

    def test_empty_slots_are_mirrored_to_skin_strings(self):
        manager = self.module.WidgetManager()
        manager.save({screen: [] for screen in self.module.SCREENS})
        self.assertTrue(any('Cineva.Widget1.Path,"")' in command for command in self.builtins))
        self.assertTrue(any('Cineva.MovieWidget1.Path,"")' in command for command in self.builtins))
        self.assertTrue(any('Cineva.ShowWidget1.Path,"")' in command for command in self.builtins))

    def test_current_slot_menu_entry_keeps_existing_widget(self):
        manager = self.module.WidgetManager()
        registry = manager.load()
        original = dict(registry["home"][0])
        self.builtins.clear()  # Ignore first-install Skin.String initialization.
        manager.dialog.selection = 0
        manager.configure_slot(registry, "home", 1)
        self.assertEqual(manager.load()["home"][0], original)
        self.assertEqual(self.builtins, [])

    def test_malformed_and_out_of_range_slot_arguments_are_ignored(self):
        manager = self.module.WidgetManager()
        manager.load()
        self.builtins.clear()  # Ignore first-install Skin.String initialization.
        for slot in ("oops", "0", "5", "-1"):
            manager.run(action="configure", screen="home", slot=slot)
            manager.run(action="clear", screen="home", slot=slot)
        self.assertEqual(len(manager.load()["home"]), 4)
        self.assertEqual(self.builtins, [])

    def test_back_from_nested_addon_folder_returns_to_parent(self):
        manager = self.module.WidgetManager()
        paths = []
        responses = {
            "plugin://plugin.video.example/": {"files": [
                {"file": "plugin://plugin.video.example/collections/", "filetype": "directory", "label": "Collections"}
            ]},
            "plugin://plugin.video.example/collections/": {"files": []},
        }
        original_call = self.module.KodiRPC.call
        self.module.KodiRPC.call = staticmethod(lambda method, params=None: (
            paths.append(params["directory"]) or responses.get(params["directory"], {})
        ))
        selections = iter([1, 2, 0])  # Open folder, Back to parent, select root.
        manager.dialog.select = lambda *args, **kwargs: next(selections)
        try:
            chosen = manager._browse_directory("plugin://plugin.video.example/", "plugin.video.example")
        finally:
            self.module.KodiRPC.call = original_call
        self.assertEqual(paths, [
            "plugin://plugin.video.example/",
            "plugin://plugin.video.example/collections/",
            "plugin://plugin.video.example/",
        ])
        self.assertEqual(chosen, {"path": "plugin://plugin.video.example/", "title": ""})

    def test_picker_ignores_playable_files_and_only_opens_directories(self):
        manager = self.module.WidgetManager()
        seen = {"calls": []}
        original_call = self.module.KodiRPC.call
        def fake_call(method, params=None):
            if params["directory"].endswith("/collections/"):
                return {"files": [
                    {"file": "plugin://plugin.video.example/play/123", "filetype": "file", "label": "A Movie"}
                ]}
            return {"files": [
                {"file": "plugin://plugin.video.example/play/123", "filetype": "file", "label": "A Movie"},
                {"file": "plugin://plugin.video.example/collections/", "filetype": "directory", "label": "Collections"}
            ]}
        self.module.KodiRPC.call = staticmethod(fake_call)
        def choose(title, choices, **kwargs):
            seen["calls"].append(list(choices))
            return 1 if len(seen["calls"]) == 1 else 0
        manager.dialog.select = choose
        try:
            chosen = manager._browse_directory("plugin://plugin.video.example/", "plugin.video.example")
        finally:
            self.module.KodiRPC.call = original_call
        self.assertEqual(seen["calls"][0], [
            "✓  Use this folder as widget",
            "📁  Collections",
            "←  Back"
        ])
        self.assertEqual(seen["calls"][1], [
            "✓  Use this folder as widget",
            "↑  Parent folder",
            "←  Back"
        ])
        self.assertEqual(chosen, {
            "path": "plugin://plugin.video.example/collections/",
            "title": ""
        })

    def test_picker_rejects_self_referential_directory_links(self):
        manager = self.module.WidgetManager()
        original_call = self.module.KodiRPC.call
        notices = []
        self.module.KodiRPC.call = staticmethod(lambda *args, **kwargs: {"files": [
            {"file": "plugin://plugin.video.example/", "filetype": "directory", "label": "Root"}
        ]})
        manager.dialog.select = lambda *args, **kwargs: 1
        manager.dialog.ok = lambda title, message: notices.append(message)
        try:
            chosen = manager._browse_directory("plugin://plugin.video.example/", "plugin.video.example")
        finally:
            self.module.KodiRPC.call = original_call
        self.assertIsNone(chosen)
        self.assertEqual(len(notices), 1)
        self.assertIn("already open", notices[0])

    def test_invalid_sources_are_filtered(self):
        FakeVFS.files["special://profile/addon_data/script.cineva.widgets/widget_registry.json"] = json.dumps({"home":[
            {"name":"Good","path":"plugin://plugin.video.good/","id":"g"},
            {"name":"Bad","path":"https://example.com","id":"b"},
            "not-a-dict"
        ]})
        registry = self.module.WidgetManager().load()
        self.assertEqual([w["name"] for w in registry["home"] if w], ["Good"])
        self.assertEqual(registry["home"][1], {})  # Bad source keeps its slot empty.

if __name__ == "__main__":
    unittest.main(verbosity=2)
