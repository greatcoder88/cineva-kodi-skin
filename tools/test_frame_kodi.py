#!/usr/bin/env python3
"""Run Frame's packaged skin in Kodi against two deterministic add-on rows."""

from bisect import bisect_left
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import statistics
import tempfile
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
PLAYBACK_FIXTURE = PROFILE / "userdata/frame-playback.mkv"
BASELINE = "d5b65b5b816ae6266d20ebb367b14d3fa129003a"
METRICS = {}
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
    if not target.exists():
        with urlopen(url, timeout=30) as response, target.open("wb") as output:
            shutil.copyfileobj(response, output)
    with ZipFile(target) as archive:
        archive.extractall(PROFILE / "addons")


def stage_profile(packages):
    addons = PROFILE / "addons"
    addons.mkdir(parents=True, exist_ok=True)
    for addon_id in ("skin.frame", "script.frame.nimbus"):
        package, = packages.glob(f"{addon_id}-*.zip")
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
            ("movie.widget.1", MOVIES + "_in_progress", "In Progress", "WidgetListPoster", "In Progress"),
            ("movie.widget.2", SHOWS, "Fixture shows", "WidgetListLandscape", "Fixture shows"),
        ))
    captions = PLAYBACK_FIXTURE.with_suffix(".srt")
    captions.write_text("1\n00:00:02,000 --> 00:00:06,000\nFrame embedded subtitle\n")
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "smptebars=size=640x360:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440", "-f", "lavfi", "-i", "sine=frequency=660",
        "-i", str(captions), "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:s", "-t", "75",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "srt",
        "-metadata:s:a:0", "language=eng", "-metadata:s:a:1", "language=hin",
        "-metadata:s:s:0", "language=eng", str(PLAYBACK_FIXTURE),
    ], check=True)
    captions.unlink()


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


def cpu_snapshot():
    """Read per-thread CPU counters from the one Kodi process in this runner."""
    for process in Path("/proc").glob("[0-9]*"):
        try:
            if (process / "comm").read_text().strip() != "kodi.bin":
                continue
        except OSError:
            continue
        counters = {}
        for task in (process / "task").iterdir():
            try:
                line = (task / "stat").read_text()
                name, fields = line.split("(", 1)[1].rsplit(")", 1)
                fields = fields.split()
                counters[task.name] = (name, int(fields[11]) + int(fields[12]))
            except (OSError, ValueError, IndexError):
                continue
        return counters
    return {}


def render_profile(start, end, before, after, inputs):
    trace = PROFILE / "frame-swaps.tsv"
    rows = [line.split() for line in trace.read_text().splitlines()] if trace.exists() else []
    swaps = [(int(a), int(b), api) for a, b, api in rows if start <= int(a) <= end]
    gaps = [(b[0] - a[0]) / 1e6 for a, b in zip(swaps, swaps[1:])]
    completed = sorted(b for _, b, _ in swaps)
    after_focus = []
    for sent, observed in inputs:
        first = bisect_left(completed, observed)
        if first < len(completed):
            after_focus.append((completed[first] - sent) / 1e6)
    threads = {}
    for ident, (name, ticks) in after.items():
        if ident in before:
            threads[name] = threads.get(name, 0) + ticks - before[ident][1]
    tick_rate = os.sysconf("SC_CLK_TCK")
    heavy = sorted(threads, key=threads.get, reverse=True)[:5]
    return {
        "swap_samples": len(swaps),
        "post_focus_swap_samples": len(after_focus),
        "median_input_to_post_focus_swap_ms": round(statistics.median(after_focus), 2) if after_focus else None,
        "swap_api": sorted({api for _, _, api in swaps}),
        "median_swap_gap_ms": round(statistics.median(gaps), 2) if gaps else None,
        "p95_swap_gap_ms": round(sorted(gaps)[int((len(gaps) - 1) * 0.95)], 2) if gaps else None,
        "p95_swap_call_ms": round(sorted((b - a) / 1e6 for a, b, _ in swaps)[int((len(swaps) - 1) * 0.95)], 2) if swaps else None,
        "swap_gaps_over_33ms": sum(gap > 33.33 for gap in gaps),
        "thread_cpu_ms": {name: round(threads[name] * 1000 / tick_rate) for name in heavy},
    }


def measure_focus(name, field, forward, reverse):
    """Measure action-to-Kodi-focus, and sample Kodi's rolling GUI FPS."""
    fps_field = "System.FPS"
    wait_for(f"{name} has a selected item", lambda: rpc("XBMC.GetInfoLabels", labels=[field])[field])
    delays, fps, inputs = [], [], []
    before = cpu_snapshot()
    profile_start = time.monotonic_ns()
    for action in (forward, reverse) * 12:
        previous = rpc("XBMC.GetInfoLabels", labels=[field])[field]
        start = time.perf_counter()
        sent = time.monotonic_ns()
        press(action)
        while time.perf_counter() - start < 1:
            values = rpc("XBMC.GetInfoLabels", labels=[field, fps_field])
            if values[field] and values[field] != previous:
                inputs.append((sent, time.monotonic_ns()))
                delays.append(round((time.perf_counter() - start) * 1000, 1))
                try:
                    value = float(values[fps_field])
                    if value > 0:
                        fps.append(value)
                except ValueError:
                    pass
                break
            time.sleep(0.005)
        time.sleep(0.12)
    profile_end = time.monotonic_ns()
    after = cpu_snapshot()
    METRICS[name] = {
        "profile": render_profile(profile_start, profile_end, before, after, inputs),
        "sample_count": len(delays),
        "timeouts": 24 - len(delays),
        "median_focus_ms": statistics.median(delays) if delays else None,
        "p95_focus_ms": sorted(delays)[int((len(delays) - 1) * 0.95)] if delays else None,
        "median_reported_fps": statistics.median(fps) if fps else None,
    }


def measure_addon_browser():
    rpc("GUI.ActivateWindow", window="addonbrowser", parameters=["addons://user/"])
    wait_for("Add-on Browser is open", lambda: window_id() == 10040)
    measure_focus("addon_browser", "Container.ListItem.Label", "down", "up")


def screenshot(name):
    # Kodi exposes the new window and focus before its fade completes.
    time.sleep(0.65)
    subprocess.run(["import", "-window", "root", str(ARTIFACTS / f"{name}.png")], check=True)


def has_focus(container):
    condition = f"Control.HasFocus({container})"
    return rpc("XBMC.GetInfoBooleans", booleans=[condition])[condition]


def focused_card(container, prefix):
    if not has_focus(container):
        return False
    field = f"Container({container}).ListItem.Label"
    return rpc("XBMC.GetInfoLabels", labels=[field])[field].startswith(prefix)


def verify_home(has_track_picker, redesigned):
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
    press("right")
    wait_for("Right from the side menu focuses the first movie card",
             lambda: focused_card(19011, "The Shawshank Redemption"))
    panel = "Control.IsVisible(8985)"
    wait_for("the side menu hides while browsing cards",
             lambda: not rpc("XBMC.GetInfoBooleans", booleans=[panel])[panel])
    rating = f"Control.GetLabel({8991 if redesigned else 8984})"
    wait_for("the focused title's Kodi rating is present in the hero",
             lambda: "8.4" in rpc("XBMC.GetInfoLabels", labels=[rating])[rating])
    fanart = "Control.IsVisible(8983)"
    wait_for("the focused movie's fanart is shown in the hero",
             lambda: rpc("XBMC.GetInfoBooleans", booleans=[fanart])[fanart])
    screenshot("home-first-widget")
    measure_focus("home_poster", "Container(19011).ListItem.Label", "right", "left")
    press("right")
    wait_for("Right moves to a second movie card", lambda: focused_card(19011, "The Dark Knight"))
    if has_track_picker:
        rpc("Files.GetDirectory", directory="plugin://plugin.video.pov/?action=hold_ratings", media="files")
        if redesigned:
            missing_rt, rt_badge = "Control.GetLabel(8992)", "Control.IsVisible(8972)"
            wait_for("Rotten Tomatoes icon stays visible with a dash while its score is missing",
                     lambda: rpc("XBMC.GetInfoBooleans", booleans=[rt_badge])[rt_badge]
                     and rpc("XBMC.GetInfoLabels", labels=[missing_rt])[missing_rt] == "—")
            slot = "Control.GetLabel(8991)"
            wait_for("IMDb stays on the focused item's native score instead of switching to the delayed response",
                     lambda: rpc("XBMC.GetInfoLabels", labels=[slot])[slot] in {"9", "9.0"})
            press("left")
            wait_for("The same rating slot updates to the previous title immediately",
                     lambda: focused_card(19011, "The Shawshank Redemption")
                     and "8.4" in rpc("XBMC.GetInfoLabels", labels=[slot])[slot])
        else:
            fallback = "Control.IsVisible(8984)"
            wait_for("Enriched ratings are shown only for their matching title",
                     lambda: not rpc("XBMC.GetInfoBooleans", booleans=[fallback])[fallback])
            press("left")
            wait_for("Previous title uses its own rating even while the old response remains",
                     lambda: focused_card(19011, "The Shawshank Redemption")
                     and rpc("XBMC.GetInfoBooleans", booleans=[fallback])[fallback]
                     and "8.4" in rpc("XBMC.GetInfoLabels", labels=[rating])[rating])
        press("right")
        wait_for("Return to the second title", lambda: focused_card(19011, "The Dark Knight"))
    press("info")
    wait_for("Kodi opens the selected movie's title details", lambda: window_id() == 12003)
    title = "Control.IsVisible(8982)"
    wait_for("the title details screen renders the movie title",
             lambda: rpc("XBMC.GetInfoBooleans", booleans=[title])[title])
    screenshot("title-details")
    press("back")
    wait_for("closing title details restores the selected movie card",
             lambda: window_id() == 10000 and focused_card(19011, "The Dark Knight"))
    press("down")
    wait_for("Down focuses the second widget row", lambda: focused_card(19012, "Breaking Bad"))
    wait_for("a title without fanart keeps its hero text and uses a neutral background", lambda: (
        rpc("XBMC.GetInfoBooleans", booleans=[feature, fanart]) == {feature: True, fanart: False}
    ))
    screenshot("home-second-widget")
    measure_focus("home_landscape", "Container(19012).ListItem.Label", "right", "left")
    press("contextmenu")
    wait_for("context action opens Kodi's context menu", lambda: window_id() == 10106)
    screenshot("home-context-menu")
    press("back")
    wait_for("closing context menu restores card focus",
             lambda: window_id() == 10000 and focused_card(19012, "Breaking Bad"))


def verify_search_and_settings(redesigned):
    press("back")
    wait_for("Home side menu regains focus", lambda: has_focus(9000))
    press("up")
    wait_for("Home shortcuts receive focus", lambda: any(has_focus(control) for control in (801, 802, 803)))
    for _ in range(2):
        if has_focus(803):
            break
        press("right")
        time.sleep(0.15)
    wait_for("Home Search shortcut is focused", lambda: has_focus(803))
    press("select")
    wait_for("Search opens from Home", lambda: window_id() == 11121)
    wait_for("new-search button is focused", lambda: has_focus(802))
    screenshot("search")
    press("left")
    wait_for("search provider selector is focused", lambda: has_focus(801))
    field = "Skin.String(current_search_provider)"
    for expected in ("1", "3"):
        press("select")
        wait_for(f"provider cycles to {expected}", lambda: rpc("XBMC.GetInfoLabels", labels=[field])[field] == expected)
    press("right")
    wait_for("search button regains focus", lambda: has_focus(802))
    press("select")
    wait_for("Search opens Kodi's keyboard", lambda: window_id() == 10103)
    screenshot("search-keyboard")
    rpc("Input.SendText", text="Dark", done=True)
    movie, show = (f"Container({control}).ListItem.Label" for control in (19011, 19012))
    wait_for("POV fixture search renders matching movies and TV shows", lambda: (
        window_id() == 11121 and rpc("XBMC.GetInfoLabels", labels=[movie, show]) == {
            movie: "The Dark Knight", show: "Dark",
        }
    ))
    if redesigned:
        year, details = "Control.GetLabel(8892)", "Control.IsVisible(8893)"
        wait_for("Search shows the movie's release year and description panel",
                 lambda: "2008" in rpc("XBMC.GetInfoLabels", labels=[year])[year]
                 and rpc("XBMC.GetInfoBooleans", booleans=[details])[details])
        if not has_focus(19011):
            press("down")
            wait_for("Down from search controls focuses the movie results", lambda: has_focus(19011))
        press("down")
        wait_for("Moving to TV results shows that title's release year",
                 lambda: has_focus(19012) and "2017" in rpc("XBMC.GetInfoLabels", labels=[year])[year])
        screenshot("search-tv-result-details")
        press("up")
        wait_for("Returning to movies restores the movie details", lambda: has_focus(19011))
    screenshot("search-results")

    rpc("GUI.ActivateWindow", window="skinsettings")
    wait_for("Skin Settings opens and the category list is focused", lambda: window_id() == 10035 and has_focus(9000))
    screenshot("skin-settings")
    measure_focus("skin_settings", "Container(9000).ListItem.Label", "down", "up")


def verify_source_picker():
    rpc("Player.Open", item={"file": "plugin://plugin.video.pov/?action=source_picker"})
    wait_for("Kodi opens the simulated source list", lambda: window_id() == 12000 and has_focus(3))
    measure_focus("source_picker", "Container(3).ListItem.Label", "down", "up")
    for index in range(2, 5):
        press("down")
        field = "Container(3).ListItem.Label"
        wait_for(f"Source focus moves to row {index}",
                 lambda: rpc("XBMC.GetInfoLabels", labels=[field])[field].startswith(f"Source {index:02d}"))
    screenshot("source-picker")
    press("select")
    prop = "Window(Home).Property(FrameSourceFixtureSelection)"
    wait_for("The source picker returns the selected result",
             lambda: rpc("XBMC.GetInfoLabels", labels=[prop])[prop] == "3")


def verify_playback_osd(has_track_picker):
    rpc("Player.Open", item={"file": str(PLAYBACK_FIXTURE)})
    wait_for("Kodi starts the local video fixture", lambda: window_id() == 12005 and rpc("Player.GetActivePlayers"))
    rpc("Input.ShowOSD")
    wait_for("playback controls appear and Play/Pause receives focus",
             lambda: window_id() == 12901 and has_focus(703))
    screenshot("playback-osd")
    player = next(item["playerid"] for item in rpc("Player.GetActivePlayers") if item["type"] == "video")
    press("select")
    wait_for("Play/Pause pauses the video", lambda: rpc("Player.GetProperties", playerid=player, properties=["speed"])["speed"] == 0)
    press("select")
    wait_for("Play/Pause resumes the video", lambda: rpc("Player.GetProperties", playerid=player, properties=["speed"])["speed"] == 1)
    if not has_track_picker:
        press("right")
        wait_for("OSD focus moves to Stop", lambda: has_focus(704))
        return
    press("right")
    wait_for("OSD focus moves to Forward", lambda: has_focus(705))
    press("right")
    wait_for("OSD focus moves to Stop", lambda: has_focus(704))
    # Traverse the native control groups to the audio utility.
    def move_to_audio():
        if has_focus(708):
            return True
        press("right")
        return False

    wait_for("Audio button can receive remote focus", move_to_audio, timeout=8)
    audio_count = "Container(8708).NumItems"
    wait_for("Hovering Audio lists both embedded tracks",
             lambda: rpc("XBMC.GetInfoLabels", labels=[audio_count])[audio_count] == "2")
    screenshot("playback-audio-tracks")
    press("up")
    wait_for("Up enters the audio selector", lambda: has_focus(8708))
    press("down")
    press("select")
    wait_for("Selecting the second track switches audio",
             lambda: rpc("Player.GetProperties", playerid=player,
                         properties=["currentaudiostream"])["currentaudiostream"]["index"] == 1)
    wait_for("Audio selector stays focused after selection", lambda: has_focus(8708))
    press("back")
    wait_for("Back returns to the audio button", lambda: has_focus(708))
    press("right")
    wait_for("Subtitle button can receive remote focus", lambda: has_focus(709))
    sub_count = "Container(8709).NumItems"
    wait_for("Subtitles preview lists Off and the embedded track",
             lambda: rpc("XBMC.GetInfoLabels", labels=[sub_count])[sub_count] == "2")
    screenshot("playback-subtitle-tracks")
    press("up")
    wait_for("Up enters the subtitle selector", lambda: has_focus(8709))
    press("down")
    press("select")
    wait_for("Selecting the embedded subtitle enables it",
             lambda: rpc("Player.GetProperties", playerid=player,
                         properties=["subtitleenabled"])["subtitleenabled"])
    wait_for("Subtitle selector stays focused after selection", lambda: has_focus(8709))
    selected = "Container(8709).ListItem.Property(FrameTrackIndex)"
    if rpc("XBMC.GetInfoLabels", labels=[selected])[selected] != "off":
        press("up")
    wait_for("The Off row is focused before selecting",
             lambda: rpc("XBMC.GetInfoLabels", labels=[selected])[selected] == "off")
    press("select")
    wait_for("Off disables subtitles",
             lambda: not rpc("Player.GetProperties", playerid=player,
                             properties=["subtitleenabled"])["subtitleenabled"])
    press("back")
    wait_for("Back exits the subtitle picker", lambda: has_focus(709))
    press("right")
    wait_for("Settings follows CC in the three-button row", lambda: has_focus(716))
    screenshot("playback-settings-focus")



def run_gui(packages, has_track_picker=True, redesigned=True):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    stage_profile(packages)
    trace_library = ARTIFACTS / "frame-swap-trace.so"
    subprocess.run(["cc", "-shared", "-fPIC", "-O2", "-Wall", "-Wextra",
                    str(ROOT / "tools/frame_swap_trace.c"), "-ldl", "-o", str(trace_library)], check=True)
    with (ARTIFACTS / "kodi-console.log").open("w") as console:
        kodi = subprocess.Popen(["flatpak", "run", "--user",
                                 f"--filesystem={trace_library.parent}:ro",
                                 f"--env=LD_PRELOAD={trace_library}",
                                 "tv.kodi.Kodi//beta", "--standalone", "--windowing=x11"],
                                stdout=console, stderr=subprocess.STDOUT)
        try:
            verify_home(has_track_picker, redesigned)
            verify_search_and_settings(redesigned)
            measure_addon_browser()
            verify_source_picker()
            verify_playback_osd(has_track_picker)
            (ARTIFACTS / "performance.json").write_text(json.dumps(METRICS, indent=2) + "\n")
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
            trace = PROFILE / "frame-swaps.tsv"
            if trace.is_file():
                shutil.copy2(trace, ARTIFACTS / trace.name)
            trace_library.unlink(missing_ok=True)


def main():
    global ARTIFACTS
    run_gui(ROOT / "dist/frame")
    # CI has a disposable Kodi profile. Recreate it so the older skin is
    # measured with the same fixtures and without the candidate's caches.
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    with tempfile.TemporaryDirectory(prefix="frame-baseline-") as workspace:
        baseline = Path(workspace)
        subprocess.run(["git", "fetch", "--no-tags", "--depth=1", "origin", BASELINE], cwd=ROOT, check=True)
        archive = subprocess.check_output(["git", "archive", BASELINE, "tools"], cwd=ROOT)
        subprocess.run(["tar", "-xf", "-", "-C", workspace], input=archive, check=True)
        packages = baseline / "packages"
        subprocess.run(["python3", str(baseline / "tools/build_frame.py"), "--output", str(packages)], check=True)
        shutil.move(PROFILE, baseline / "candidate-profile")
        ARTIFACTS = ARTIFACTS / "baseline-0.1.69"
        METRICS.clear()
        run_gui(packages, redesigned=False)


if __name__ == "__main__":
    main()
