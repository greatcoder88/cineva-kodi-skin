"""Provide the Frame OSD with the current player's audio and subtitle tracks."""

import json
import sys
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin


def request(method, **params):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    return json.loads(xbmc.executeJSONRPC(json.dumps(payload))).get("result")


def add_track(handle, row, index):
    item = xbmcgui.ListItem(label=row)
    item.setProperty("FrameTrackIndex", str(index))
    xbmcplugin.addDirectoryItem(handle, sys.argv[0], item)


def main():
    handle = int(sys.argv[1])
    options = parse_qs(sys.argv[2].lstrip("?"))
    kind = options.get("kind", [""])[0]
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

    selection = options.get("select", [""])[0]
    if selection:
        index = next((track["index"] for track in tracks if str(track["index"]) == selection), None)
        if audio and index is not None:
            request("Player.SetAudioStream", playerid=player, stream=index)
        elif not audio and (selection == "off" or index is not None):
            request("Player.SetSubtitle", playerid=player,
                    subtitle="off" if selection == "off" else index, enable=selection != "off")
        window = xbmcgui.Window(12901)
        revision = int(window.getProperty("FrameTracksRevision") or 0) + 1
        window.setProperty("FrameTracksRevision", str(revision))
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
        return

    if not audio:
        add_track(handle, ("✓  " if active is None else "") + xbmc.getLocalizedString(351), "off")
    for track in tracks:
        language = track.get("language", "")
        language = xbmc.convertLanguage(language, xbmc.ENGLISH_NAME) or language
        label = " · ".join(dict.fromkeys(filter(None, (language, track.get("name", "")))))
        if audio and track.get("channels"):
            label = f"{label}  ·  {track['channels']} ch".strip(" ·")
        if not label:
            label = str(track["index"] + 1)
        add_track(handle, ("✓  " if track["index"] == active else "") + label, track["index"])
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


if __name__ == "__main__":
    main()
