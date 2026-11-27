#!/usr/bin/env python3
"""Run Frame's packaged skin in Kodi against two deterministic add-on rows."""

import json
import shutil
import socket
import sqlite3
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PROFILE = Path.home() / ".var/app/tv.kodi.Kodi/data"
ARTIFACTS = ROOT / "artifacts/frame-gui"
MOVIES = "plugin://plugin.video.pov/?action=movies"
SHOWS = "plugin://plugin.video.pov/?action=tvshows"
DEPENDENCIES = {
    "certifi": "2023.5.7",
    "chardet": "5.1.0",
    "idna": "3.4.0",
    "urllib3": "1.26.16+matrix.1",
    "requests": "2.31.0",
}


def stage_dependency(item):
    name, version = item
    addon_id = f"script.module.{name}"
    filename = f"{addon_id}-{version}.zip"
    url = f"https://mirrors.kodi.tv/addons/omega/{addon_id}/{filename}"
    target = ROOT / "dist/frame-dependencies" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=30) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)
    with ZipFile(target) as archive:
        archive.extractall(PROFILE / "addons")


def stage_profile():
    addons = PROFILE / "addons"
    addons.mkdir(parents=True, exist_ok=True)
    for addon_id in ("skin.frame", "script.frame.nimbus"):
        package, = (ROOT / "dist/frame").glob(f"{addon_id}-*.zip")
        with ZipFile(package) as archive:
            archive.extractall(addons)
    with ThreadPoolExecutor() as pool:
        list(pool.map(stage_dependency, DEPENDENCIES.items()))

    fixture = addons / "plugin.video.pov"
    shutil.copytree(ROOT / "tools/test-fixtures/plugin.video.pov", fixture)
    posters = fixture / "resources/posters"
    posters.mkdir(parents=True)
    colors = ("#35556f", "#935950", "#53715a", "#75688c")
    for kind, geometry in (("movie", "320x480"), ("tv", "320x480"),
                           ("backdrop", "640x360"), ("tv-backdrop", "640x360")):
        for index in range(1, 9):
            color = colors[(index + len(kind)) % len(colors)]
            subprocess.run(["convert", "-size", geometry, f"gradient:{color}-#151619",
                            str(posters / f"{kind}-{index}.jpg")], check=True)
    subprocess.run(["convert", "-size", "320x80", "xc:none", "-fill", "white", "-draw",
                    "roundrectangle 12,12 308,68 12,12", str(posters / "clearlogo-tv-1.png")], check=True)

    # Exercise the real Nimbus helper's first-run XML generation. Populate only
    # fixture paths in its persisted schema, as if selected through Skin Settings.
    profile = PROFILE / "userdata/addon_data/script.frame.nimbus"
    profile.mkdir(parents=True)
    with sqlite3.connect(profile / "cpath_cache.db") as db:
        db.execute("""CREATE TABLE custom_paths (cpath_setting text unique,
                   cpath_path text, cpath_header text, cpath_type text, cpath_label text)""")
        db.executemany("INSERT INTO custom_paths VALUES (?, ?, ?, ?, ?)", (
            ("movie.main_menu", MOVIES, "Movies", "", "Movies"),
            ("movie.widget.1", MOVIES, "Fixture movies", "WidgetListLandscape", "Fixture movies"),
            ("movie.widget.2", SHOWS, "Fixture shows", "WidgetListLandscape", "Fixture shows"),
        ))


def rpc(method, **params):
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    decoder = json.JSONDecoder()
    with socket.create_connection(("127.0.0.1", 9090), timeout=3) as connection:
        connection.sendall(payload.encode())
        buffer = bytearray()
        position = 0
        while chunk := connection.recv(65536):
            buffer.extend(chunk)
            try:
                incoming = buffer.decode()
            except UnicodeDecodeError:
                continue
            while position < len(incoming):
                while position < len(incoming) and incoming[position].isspace():
                    position += 1
                try:
                    response, position = decoder.raw_decode(incoming, position)
                except json.JSONDecodeError:
                    break
                if response.get("id") != 1:
                    continue
                if "error" in response:
                    raise RuntimeError(f"{method}: {response['error']}")
                return response["result"]
    raise RuntimeError(f"No result for {method}")


def wait_for(description, probe, timeout=25):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            last = probe()
            if last:
                print(f"PASS: {description}", flush=True)
                return last
        except (OSError, RuntimeError) as exc:
            last = exc
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {description}; last observation: {last}")


def gui():
    return rpc("GUI.GetProperties", properties=["skin", "currentwindow", "currentcontrol"])


def window_id():
    return gui()["currentwindow"]["id"]


def press(action):
    rpc("Input.ExecuteAction", action=action)


def screenshot(name):
    subprocess.run(["import", "-window", "root", str(ARTIFACTS / f"{name}.png")], check=True)


def focused_card(container, prefix):
    condition = f"Control.HasFocus({container})"
    if not rpc("XBMC.GetInfoBooleans", booleans=[condition])[condition]:
        return False
    field = f"Container({container}).ListItem.Label"
    return rpc("XBMC.GetInfoLabels", labels=[field])[field].startswith(prefix)


def verify_home():
    wait_for("Kodi JSON-RPC is ready", lambda: rpc("JSONRPC.Ping") == "pong", timeout=100)
    for name in DEPENDENCIES:
        rpc("Addons.SetAddonEnabled", addonid=f"script.module.{name}", enabled=True)
    for addon_id in ("plugin.video.pov", "script.frame.nimbus", "skin.frame"):
        rpc("Addons.SetAddonEnabled", addonid=addon_id, enabled=True)
    for directory in (MOVIES, SHOWS):
        files = rpc("Files.GetDirectory", directory=directory, media="files")["files"]
        if len(files) != 8:
            raise RuntimeError(f"Expected eight fixture items in {directory}, received {len(files)}")
    rpc("Settings.SetSettingValue", setting="lookandfeel.skin", value="skin.frame")

    def keep_skin_confirmation():
        state = gui()
        if state["skin"]["id"] == "skin.frame" and state["currentwindow"]["id"] == 10100:
            return state["currentcontrol"]["label"].strip().lower()

    # The welcome window can appear briefly before Kodi's confirmation overlays
    # it. A Select during that transition can choose the default No button.
    choice = wait_for("Kodi opens the Keep Skin confirmation", keep_skin_confirmation, timeout=30)
    if choice == "no":
        press("left")
    wait_for("Keep Skin confirmation focuses Yes", lambda: keep_skin_confirmation() == "yes", timeout=5)
    press("select")
    wait_for("Nimbus welcome opens after keeping Frame", lambda: window_id() == 11112)
    press("select")

    settings = PROFILE / "addons/skin.frame/xml/script-nimbus-widget_movies.xml"
    setup_confirmation_dismissed = False

    def populated_home():
        nonlocal setup_confirmation_dismissed
        state = gui()
        if (not setup_confirmation_dismissed and state["currentwindow"]["id"] == 12002
                and state["currentcontrol"]["label"].strip().lower() == "ok"):
            setup_confirmation_dismissed = True
            press("select")
            return False
        field = "Container(9000).ListItem.Property(id)"
        return (state["skin"]["id"] == "skin.frame" and state["currentwindow"]["id"] == 10000
                and settings.is_file() and "Fixture shows" in settings.read_text()
                and rpc("XBMC.GetInfoLabels", labels=[field])[field] == "movies")

    wait_for("stock helper creates the configured widget rows and Home opens", populated_home, timeout=70)
    feature = "Control.IsVisible(8980)"
    wait_for("Home renders the featured title panel",
             lambda: rpc("XBMC.GetInfoBooleans", booleans=[feature])[feature])
    screenshot("home-feature")
    press("down")
    wait_for("Down from the top menu focuses the first movie card",
             lambda: focused_card(19011, "The Shawshank Redemption"))
    screenshot("home-first-widget")
    press("right")
    wait_for("Right moves to a second movie card", lambda: focused_card(19011, "The Dark Knight"))
    press("down")
    wait_for("Down focuses the second widget row", lambda: focused_card(19012, "Breaking Bad"))
    screenshot("home-second-widget")
    press("contextmenu")
    wait_for("context action opens Kodi's context menu", lambda: window_id() == 10106)
    screenshot("home-context-menu")
    press("back")
    wait_for("closing context menu restores card focus",
             lambda: window_id() == 10000 and focused_card(19012, "Breaking Bad"))


def main():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stage_profile()
    with (ARTIFACTS / "kodi-console.log").open("w") as console:
        kodi = subprocess.Popen(["flatpak", "run", "--user", "tv.kodi.Kodi//beta",
                                 "--standalone", "--windowing=x11"], stdout=console, stderr=subprocess.STDOUT)
        try:
            verify_home()
        except Exception:
            try:
                print(f"Final Kodi GUI state: {gui()}", flush=True)
            except (OSError, RuntimeError) as exc:
                print(f"Could not read final Kodi GUI state: {exc}", flush=True)
            subprocess.run(["import", "-window", "root", str(ARTIFACTS / "failure.png")], check=False)
            raise
        finally:
            subprocess.run(["flatpak", "kill", "tv.kodi.Kodi"], check=False)
            if kodi.poll() is None:
                kodi.terminate()
                kodi.wait(timeout=10)
            log = PROFILE / "temp/kodi.log"
            if log.is_file():
                shutil.copy2(log, ARTIFACTS / "kodi.log")


if __name__ == "__main__":
    main()
