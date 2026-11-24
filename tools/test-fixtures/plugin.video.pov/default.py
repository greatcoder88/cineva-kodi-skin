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
    ("Oppenheimer", 2023, "Biography / Drama"),
    ("Barbie", 2023, "Comedy / Fantasy"),
]
SHOWS = [
    ("Breaking Bad", 2008, "Crime / Drama"),
    ("Dark", 2017, "Sci-Fi / Mystery"),
    ("Severance", 2022, "Sci-Fi / Thriller"),
    ("The Last of Us", 2023, "Drama / Horror"),
    ("The Bear", 2022, "Comedy / Drama"),
    ("Sherlock", 2010, "Crime / Mystery"),
    ("Game of Thrones", 2011, "Fantasy / Drama"),
    ("Succession", 2018, "Drama"),
]


def main():
    handle = int(sys.argv[1])
    query = parse_qs(sys.argv[2].lstrip("?")) if len(sys.argv) > 2 else {}
    action = query.get("action", [""])[-1]
    is_tv = "tv" in action or "tvshow" in action
    records = SHOWS if is_tv else MOVIES
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    poster_dir = os.path.join(addon_path, "resources", "posters")
    poster_kind = "tv" if is_tv else "movie"
    entries = []
    for index, (title, year, genre) in enumerate(records, 1):
        poster = os.path.join(poster_dir, "{}-{}.jpg".format(poster_kind, index))
        if not os.path.isfile(poster):
            raise RuntimeError("Missing downloaded poster artwork: {}".format(poster))
        play_url = "plugin://plugin.video.pov/play?id={}".format(index)
        item = xbmcgui.ListItem(label=title, path=play_url)
        item.setInfo("video", {
            "title": title,
            "year": year,
            "genre": genre,
            "mediatype": "tvshow" if is_tv else "movie",
            "rating": 8.4,
            "plot": (
                "Framed for a murder he did not commit, a banker finds hope and friendship while enduring a brutal prison sentence."
                if title == "The Shawshank Redemption" else
                "A high-school chemistry teacher enters the criminal underworld, changing his family and himself forever."
                if title == "Breaking Bad" else
                "A richly detailed story of impossible choices, loyalty, and the consequences that follow."
            ),
        })
        # Keep poster art portrait and thumb/fanart landscape, matching common
        # provider metadata. This catches skins that accidentally use thumb as a poster.
        backdrop_name = "tv-backdrop-{}.jpg".format(index) if is_tv else "backdrop-{}.jpg".format(index)
        fanart = os.path.join(poster_dir, backdrop_name)
        if not os.path.isfile(fanart):
            raise RuntimeError("Missing landscape hero artwork: {}".format(fanart))
        # Breaking Bad deliberately has a poster but no landscape art. This
        # exercises the Home hero fallback while keeping its card fully usable.
        if is_tv and index == 1:
            artwork = {"poster": poster}
            item.setProperty("Cineva.TestMissingFanart", "true")
        else:
            artwork = {"thumb": fanart, "fanart": fanart, "landscape": fanart}
            # Interstellar deliberately omits poster art so the first shelf
            # exercises the branded portrait fallback while retaining fanart.
            if is_tv or index != 3:
                artwork["poster"] = poster
            else:
                item.setProperty("Cineva.TestMissingPoster", "true")
        if index == 1:
            clearlogo_name = "clearlogo-tv-1.png" if is_tv else "clearlogo-movie-1.png"
            clearlogo = os.path.join(poster_dir, clearlogo_name)
            if not os.path.isfile(clearlogo):
                raise RuntimeError("Missing generated clearlogo artwork: {}".format(clearlogo))
            artwork["clearlogo"] = clearlogo
        item.setArt(artwork)
        # Continue Watching fixtures need real resume metadata so the skin's
        # progress strips are exercised in both normal and focused card states.
        if "in_progress" in action:
            item.getVideoInfoTag().setResumePoint(90 + index * 80, 900)
        item.setProperty("Cineva.TestFixture", "true")
        entries.append((play_url, item, False))
    xbmcplugin.addDirectoryItems(handle, entries, len(entries))
    xbmcplugin.setPluginCategory(handle, "TV Shows" if is_tv else "Movies")
    xbmcplugin.setContent(handle, "tvshows" if is_tv else "movies")
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=False)


if __name__ == "__main__":
    main()
