import hashlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_nimbus_base as builder


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
    "xml/Home.xml": "<window><defaultcontrol>9000</defaultcontrol></window>",
    "xml/Includes.xml": "<includes><include file=\"Includes_Home.xml\"/></includes>",
    "xml/Includes_Home.xml": """<includes>
      <onload>RunScript(script.nimbus.helper,mode=check_for_update&amp;skin_id=skin.nimbus)</onload>
      <onload>RunScript(script.nimbus.helper,mode=check_for_profile_change&amp;skin_id=skin.nimbus)</onload>
      <onfocus>RunScript(script.nimbus.helper,mode=set_widget_count,$PARAM[list_id])</onfocus>
    </includes>""",
    "xml/Includes_HomeLayouts.xml": "<includes><include name=\"WidgetGroupListCommon\"/></includes>",
    "xml/Startup.xml": "<window><onload>RunScript(script.nimbus.helper,mode=refresh_search_history)</onload></window>",
    "xml/SkinSettings.xml": """<window><controls>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=manage_widgets&amp;cpath_setting=movie.widget)</onclick></control>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=set_api_key)</onclick></control>
      <control type="button"><onclick>RunScript(script.nimbus.helper,mode=delete_all_ratings)</onclick></control>
    </controls></window>""",
    "xml/Variables_Ratings.xml": "<includes><variable name=\"rating\"><value>$INFO[ListItem.Rating]</value></variable></includes>",
    "xml/View_54_Flix.xml": "<includes><include name=\"FlixView\"/></includes>",
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
    "resources/lib/modules/cpath_maker.py": 'settings_path = "special://profile/addon_data/script.nimbus.helper/"\n',
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
                self.assertIn("skin.cineva/xml/View_54_Flix.xml", names)
                self.assertIn("skin.cineva/fonts/Inter-Regular.ttf", names)
                self.assertIn("skin.cineva/LICENSE.txt", names)
                self.assertIn("skin.cineva/NOTICE.txt", names)
                manifest = archive.read("skin.cineva/addon.xml").decode()
                self.assertIn('id="skin.cineva"', manifest)
                self.assertIn('version="0.6.0"', manifest)
                self.assertIn('addon="xbmc.gui" version="5.18.0"', manifest)
                self.assertIn('addon="script.cineva.nimbus" version="0.1.0"', manifest)
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
    def test_first_boot_reads_kodis_actual_flatpak_log_location(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn('KODI_DATA="$HOME/.var/app/tv.kodi.Kodi/data"', source)
        self.assertIn('KODI_LOG="$KODI_DATA/temp/kodi.log"', source)
        self.assertNotIn('KODI_LOG="$USERDATA/temp/kodi.log"', source)

    def test_first_boot_uses_the_proven_kodi_process_cleanup(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn('pkill -TERM -x kodi.bin', source)
        self.assertIn('pkill -KILL -x kodi.bin', source)
        self.assertIn('kodi_processes()', source)
        self.assertIn('$2 !~ /^Z/', source)
        self.assertIn("Port 9090 remains occupied after first-boot cleanup", source)

    def test_second_boot_waits_for_jsonrpc_before_declaring_kodi_exit(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("for launch_attempt in 1 2; do", source)
        self.assertIn("kodi_processes | grep -q . && ss -ltn | grep -q ':9090'", source)
        self.assertIn("Kodi did not expose JSON-RPC after two detached Nimbus launch attempts.", source)
        self.assertIn('for name in ("kodi.bin", "kodi-x11", "kodi")', source)
        self.assertNotIn('subprocess.run(["pgrep","-x","kodi.bin"],capture_output=True).returncode != 0', source)

    def test_skin_is_enabled_and_selected_after_kodi_starts(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/nimbus-foundation.yml"
        source = workflow.read_text(encoding="utf-8")
        self.assertNotIn('"lookandfeel.skin": "skin.cineva"', source)
        self.assertIn('"addonid":"script.cineva.nimbus", "enabled":True', source)
        self.assertIn('"addonid":"skin.cineva", "enabled":True', source)
        self.assertIn('"setting":"lookandfeel.skin", "value":"skin.cineva"', source)
        self.assertIn("before_skin_loads", source)


if __name__ == "__main__":
    unittest.main()
