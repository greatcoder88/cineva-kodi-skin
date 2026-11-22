import importlib.util
import json
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANAGER = ROOT / "tools/script.cineva.widgets/resources/lib/manager.py"

class FakeAddon:
    def __init__(self): self.settings = {}
    def getSettingString(self, key): return self.settings.get(key, "")
    def setSettingString(self, key, value): self.settings[key] = value

class FakeDialog:
    def select(self, *args, **kwargs): return -1
    def ok(self, *args, **kwargs): pass
    def input(self, *args, **kwargs): return ""
    def yesno(self, *args, **kwargs): return False

class KodiManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addon = FakeAddon()
        xbmc = types.ModuleType("xbmc")
        xbmc.LOGINFO = 1
        xbmc.executeJSONRPC = lambda payload: json.dumps({"result": {"addons": []}})
        xbmc.executebuiltin = lambda command: None
        xbmc.log = lambda *args: None
        addon_mod = types.ModuleType("xbmcaddon")
        addon_mod.Addon = lambda: cls.addon
        gui = types.ModuleType("xbmcgui")
        gui.Dialog = FakeDialog
        sys.modules.update({"xbmc": xbmc, "xbmcaddon": addon_mod, "xbmcgui": gui})
        spec = importlib.util.spec_from_file_location("cineva_manager", MANAGER)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self): self.addon.settings.clear()

    def test_default_home_has_four_pov_widgets(self):
        registry = self.module.WidgetManager().load()
        self.assertEqual(len(registry["home"]), 4)
        self.assertTrue(all(w["path"].startswith("plugin://plugin.video.pov/") for w in registry["home"]))

    def test_all_screens_exist_and_are_independent(self):
        registry = self.module.WidgetManager().load()
        self.assertEqual(set(registry), set(self.module.SCREENS))
        registry["movies"].append({"id":"x","name":"X","path":"plugin://plugin.video.example/","addon":"plugin.video.example","content":"videos"})
        self.module.WidgetManager().save(registry)
        again = self.module.WidgetManager().load()
        self.assertEqual(len(again["movies"]), 1)
        self.assertEqual(len(again["tvshows"]), 0)

    def test_invalid_entries_are_filtered(self):
        self.addon.settings["widget_registry"] = json.dumps({"home":[
            {"name":"Good","path":"plugin://plugin.video.good/","id":"g"},
            {"name":"Bad","path":"https://example.com","id":"b"},
            "not-a-dict"
        ]})
        registry = self.module.WidgetManager().load()
        self.assertEqual([w["name"] for w in registry["home"]], ["Good"])

    def test_registry_persists_more_than_six_widgets(self):
        manager = self.module.WidgetManager()
        registry = {screen: [] for screen in self.module.SCREENS}
        registry["home"] = [
            {"id":str(i),"name":"W"+str(i),"path":"plugin://plugin.video.x/"+str(i),"addon":"plugin.video.x","content":"videos"}
            for i in range(12)
        ]
        manager.save(registry)
        again = manager.load()
        self.assertEqual(len(again["home"]), 12)

if __name__ == "__main__": unittest.main(verbosity=2)
