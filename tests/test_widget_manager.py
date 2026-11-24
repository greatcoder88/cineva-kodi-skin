import importlib.util
import json
import pathlib
import sys
import types
import unittest
import xml.etree.ElementTree as ET

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
    def select(self, *args, **kwargs): return -1
    def ok(self, *args, **kwargs): pass
    def input(self, *args, **kwargs): return ""
    def yesno(self, *args, **kwargs): return False

class KodiManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builtins = []
        xbmc = types.ModuleType("xbmc")
        xbmc.LOGINFO, xbmc.LOGWARNING = 1, 2
        xbmc.executeJSONRPC = lambda payload: json.dumps({"result": {"addons": []}})
        xbmc.executebuiltin = lambda command: cls.builtins.append(command)
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

    def test_invalid_sources_are_filtered(self):
        FakeVFS.files["special://profile/addon_data/script.cineva.widgets/widget_registry.json"] = json.dumps({"home":[
            {"name":"Good","path":"plugin://plugin.video.good/","id":"g"},
            {"name":"Bad","path":"https://example.com","id":"b"},
            "not-a-dict"
        ]})
        registry = self.module.WidgetManager().load()
        self.assertEqual([w["name"] for w in registry["home"] if w], ["Good"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
