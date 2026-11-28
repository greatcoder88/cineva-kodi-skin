"""Provide the Frame OSD with the current player's audio and subtitle tracks."""

import json
import re
import sys
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin


ACCENTS = (
    ("Mint", "72EBC5"),
    ("Glacier", "79C8FF"),
    ("Rose", "FF91AA"),
    ("Amber", "FFCA75"),
    ("Lilac", "C3ACFF"),
    ("Pearl", "EEEFF2"),
)


def choose_accent():
    dialog = xbmcgui.Dialog()
    labels = [label for label, _ in ACCENTS]
    default = xbmc.getInfoLabel("Skin.String(Frame.AccentLabel)") or "Mint"
    options = labels + ["Custom hex color"]
    choice = dialog.select("Frame accent color", options, preselect=labels.index(default) if default in labels else len(labels))
    if choice < 0:
        return
    if choice == len(labels):
        old = xbmc.getInfoLabel("Skin.String(Frame.Accent)").removeprefix("FF")
        color = dialog.input("Enter a hex color (RRGGBB)", defaultt=old).strip().lstrip("#").upper()
        if not color:
            return
        if not re.fullmatch(r"[0-9A-F]{6}", color):
            dialog.ok("Frame accent color", "Enter six hexadecimal digits, for example 79C8FF.")
            return
        label = f"#{color}"
    else:
        label, color = ACCENTS[choice]
    xbmc.executebuiltin(f"Skin.SetString(Frame.Accent,FF{color})")
    xbmc.executebuiltin(f"Skin.SetString(Frame.AccentLabel,{label})")


def request(method, **params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(payload))).get("result")


def add_track(handle, row, index, secondary=""):
    item = xbmcgui.ListItem(label=row, label2=secondary)
    item.setProperty("FrameTrackIndex", str(index))
    xbmcplugin.addDirectoryItem(handle, sys.argv[0], item)


def main():
    handle = int(sys.argv[1])
    options = parse_qs(sys.argv[2].lstrip("?"))
    kind = options.get("kind", [""])[0]
    if kind == "accent":
        choose_accent()
        return
    player = next((entry["playerid"] for entry in request("Player.GetActivePlayers") or []
                   if entry["type"] == "video"), None)
    if kind not in {"audio", "subtitle"} or player is None:
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
        return

    audio = kind == "audio"
    listing, current = ("audiostreams", "currentaudiostream") if audio else ("subtitles", "currentsubtitle")
    properties = [listing, current] if audio else [listing, current, "subtitleenabled"]
    state = request("Player.GetProperties", playerid=player, properties=properties) or {}
    tracks = state.get(listing, [])
    active = (state.get(current) or {}).get("index") if audio or state.get("subtitleenabled") else None

    window = xbmcgui.Window(12901)
    active_property = f"FrameActiveTrack.{kind}"
    selection = options.get("select", [""])[0]
    if selection:
        index = next((track["index"] for track in tracks if str(track["index"]) == selection), None)
        result = None
        if audio and index is not None:
            result = request("Player.SetAudioStream", playerid=player, stream=index)
        elif not audio and (selection == "off" or index is not None):
            result = request("Player.SetSubtitle", playerid=player,
                             subtitle="off" if selection == "off" else index, enable=selection != "off")
        if result == "OK":
            # Keep the list and its focus intact while reflecting the new selection.
            window.setProperty(active_property, selection)
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
        return

    window.setProperty(active_property, str(active) if active is not None else "off")
    if not audio:
        add_track(handle, xbmc.getLocalizedString(351), "off")
    for track in tracks:
        language = track.get("language", "")
        language = xbmc.convertLanguage(language, xbmc.ENGLISH_NAME) or language
        label = " · ".join(dict.fromkeys(filter(None, (language, track.get("name", "")))))
        channels = f"{track['channels']} ch" if audio and track.get("channels") else ""
        if not label:
            label = str(track["index"] + 1)
        add_track(handle, label, track["index"], channels)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


if __name__ == "__main__":
    main()
