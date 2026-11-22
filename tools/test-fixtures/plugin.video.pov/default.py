# -*- coding: utf-8 -*-
"""Deterministic, test-only POV-compatible directory provider for CINÉVA GUI tests."""
import os
import sys
from urllib.parse import parse_qs

import xbmcaddon
import xbmcgui
import xbmcplugin

MOVIES = [
    ("The Shawshank Redemption", 1994, "Drama"),
    ("The Dark Knight", 2008, "Action / Crime"),
    ("Interstellar", 2014, "Sci-Fi / Drama"),
    ("Inception", 2010, "Sci-Fi / Thriller"),
    ("The Matrix", 1999, "Sci-Fi / Action"),
    ("Dune: Part Two", 2024, "Sci-Fi / Adventure"),
]
SHOWS = [
    ("Breaking Bad", 2008, "Crime / Drama"),
    ("Dark", 2017, "Sci-Fi / Mystery"),
    ("Severance", 2022, "Sci-Fi / Thriller"),
    ("The Last of Us", 2023, "Drama / Horror"),
    ("The Bear", 2022, "Comedy / Drama"),
    ("Sherlock", 2010, "Crime / Mystery"),
]


def main():
    handle = int(sys.argv[1])
    query = parse_qs(sys.argv[2].lstrip("?")) if len(sys.argv) > 2 else {}
    action = query.get("action", [""])[-1]
    is_tv = "tv" in action or "tvshow" in action
    records = SHOWS if is_tv else MOVIES
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    poster_dir = os.path.join(addon_path, "resources", "posters")
    entries = []
    for index, (title, year, genre) in enumerate(records, 1):
        poster = os.path.join(poster_dir, "{}.png".format(index))
        play_url = "plugin://plugin.video.pov/play?id={}".format(index)
        item = xbmcgui.ListItem(label=title, path=play_url)
        item.setInfo("video", {
            "title": title,
            "year": year,
            "genre": genre,
            "plot": "CINÉVA GUI test fixture item — {}".format(title),
            "mediatype": "tvshow" if is_tv else "movie",
            "rating": 8.4,
        })
        item.setArt({"poster": poster, "thumb": poster, "fanart": poster})
        item.setProperty("Cineva.TestFixture", "true")
        entries.append((play_url, item, False))
    xbmcplugin.addDirectoryItems(handle, entries, len(entries))
    xbmcplugin.setPluginCategory(handle, "TV Shows" if is_tv else "Movies")
    xbmcplugin.setContent(handle, "tvshows" if is_tv else "movies")
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


if __name__ == "__main__":
    main()
