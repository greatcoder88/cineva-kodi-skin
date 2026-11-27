# -*- coding: utf-8 -*-
"""Deterministic, test-only POV-compatible directory provider for CINÉVA GUI tests."""
import os
import sys
from urllib.parse import parse_qs

import xbmcaddon
import xbmcgui
import xbmcplugin

MOVIES = [
    ("The Shawshank Redemption: Special Collector's Edition", 1994, "Drama"),
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

TAGLINES = {
    "The Shawshank Redemption: Special Collector's Edition": "Hope can survive even behind the thickest walls.",
    "The Dark Knight": "When the city needs a hero, chaos answers first.",
    "Interstellar": "The farthest journey begins with a promise to come home.",
    "Inception": "",
    "The Matrix": "The world you know is only a carefully built illusion.",
    "Dune: Part Two": "A desert destiny rises with the power of a legend.",
    "Oppenheimer": "One discovery changes the world, then changes its maker.",
    "Barbie": "A perfect world changes when one question is asked.",
    "Breaking Bad": "A second life takes a chemistry teacher beyond control.",
    "Dark": "Four families uncover a mystery that spans generations.",
    "Severance": "Two separate lives share one unsettling secret.",
    "The Last of Us": "A fragile bond becomes humanity's last hope.",
    "The Bear": "A young chef returns home to rebuild a restaurant and himself.",
    "Sherlock": "A brilliant detective sees what everyone else misses.",
    "Game of Thrones": "Great houses battle for power in a world of dragons.",
    "Succession": "A media empire becomes a battlefield for its heirs.",
}
PLOTS = {
    "The Shawshank Redemption: Special Collector's Edition": "A banker sentenced for a crime he did not commit builds an unlikely friendship and a quiet plan for freedom.",
    "The Dark Knight": "Batman faces a criminal mastermind whose escalating attacks push Gotham and its heroes to their limits.",
    "Interstellar": "A team of explorers travels beyond this galaxy to discover whether mankind has a future among the stars.",
    "Inception": "A skilled thief enters dreams to steal secrets, then takes on an impossible job: plant an idea.",
    "The Matrix": "A computer hacker discovers that reality is a simulation and joins a rebellion against the machines controlling it.",
    "Dune: Part Two": "Paul Atreides unites with Chani and the Fremen while seeking revenge and confronting a destiny that could reshape the universe.",
    "Oppenheimer": "Theoretical physicist J. Robert Oppenheimer leads the Manhattan Project and wrestles with the consequences of creating the atomic bomb.",
    "Barbie": "After leaving Barbieland, Barbie and Ken discover the joys and complications of life in the real world.",
    "Breaking Bad": "A high-school chemistry teacher enters the criminal underworld, changing his family and himself forever.",
    "Dark": "A missing child exposes secrets connecting four families across several generations in a small German town.",
    "Severance": "Employees at Lumon undergo a procedure that separates their work memories from their personal lives.",
    "The Last of Us": "A hardened survivor escorts a teenage girl across a dangerous post-pandemic America.",
    "The Bear": "A fine-dining chef returns to Chicago to run his family's sandwich shop while navigating grief and a demanding kitchen.",
    "Sherlock": "A consulting detective and his flatmate solve unusual crimes across modern-day London.",
    "Game of Thrones": "Noble families struggle for the Iron Throne as an ancient threat gathers beyond the northern border.",
    "Succession": "The children of a powerful media owner compete for control as their family's empire faces an uncertain future.",
}
PLOT_OUTLINES = {
    "Inception": "A skilled thief enters dreams to steal secrets, then takes on an impossible job: plant an idea."
}
TOMATO_PERCENT = {
    # The GUI test selects Inception (the fourth item in a 1-based list).
    # Keep this explicit instead of relying on an index-parity shortcut.
    "Inception": "92",
}


def main():
    handle = int(sys.argv[1])
    query = parse_qs(sys.argv[2].lstrip("?")) if len(sys.argv) > 2 else {}
    action = query.get("action", [""])[-1]
    search_term = query.get("query", [""])[-1].strip().casefold()
    # Kodi invokes default.py with the add-on root in sys.argv[0]; nested
    # plugin:// paths are not preserved there. Route playback explicitly via
    # the query string so a real poster SELECT reaches this resolver.
    if action == "play" or sys.argv[0].rstrip("/").endswith("/play"):
        invoked_url = "{}{}".format(sys.argv[0], sys.argv[2] if len(sys.argv) > 2 else "")
        xbmc.log("CINEVA_TEST_PLAY_RESOLVER_INVOKED url={}".format(invoked_url), xbmc.LOGINFO)
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        return
    is_tv = "tv" in action or "tvshow" in action
    records = SHOWS if is_tv else MOVIES
    if action in ("tmdb_movies_search", "tmdb_tv_search"):
        records = [record for record in records if search_term in record[0].casefold()]
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    poster_dir = os.path.join(addon_path, "resources", "posters")
    poster_kind = "tv" if is_tv else "movie"
    entries = []
    for index, (title, year, genre) in enumerate(records, 1):
        poster = os.path.join(poster_dir, "{}-{}.jpg".format(poster_kind, index))
        if not os.path.isfile(poster):
            raise RuntimeError("Missing downloaded poster artwork: {}".format(poster))
        play_url = "plugin://plugin.video.pov/?action=play&id={}".format(index)
        item = xbmcgui.ListItem(label=title, path=play_url)
        video_info = {
            "title": title,
            "year": year,
            "genre": genre,
            "mediatype": "tvshow" if is_tv else "movie",
            "rating": 8.4,
            "tagline": TAGLINES[title],
            "plot": PLOTS[title],
            "plotoutline": PLOT_OUTLINES.get(title, ""),
        }
        if is_tv and "in_progress" in action:
            video_info["season"] = 2
            video_info["episode"] = 5
        item.setInfo("video", video_info)
        item.getVideoInfoTag().setRating(8.4, 1200, "imdb", True)
        # Exercise both supported Rotten Tomatoes paths with deterministic fixture data.
        item.getVideoInfoTag().setRating(9.2, 1800, "tomatometerallcritics", False)
        if title in TOMATO_PERCENT:
            item.setProperty("Rating.tomatoes.Percent", TOMATO_PERCENT[title])
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
        if index == 1 and is_tv:
            clearlogo_name = "clearlogo-tv-1.png" if is_tv else "clearlogo-movie-1.png"
            clearlogo = os.path.join(poster_dir, clearlogo_name)
            if not os.path.isfile(clearlogo):
                raise RuntimeError("Missing generated clearlogo artwork: {}".format(clearlogo))
            artwork["clearlogo"] = clearlogo
        item.setArt(artwork)
        # Kodi requires this flag before a non-folder plugin item is activated.
        # Without it, Select can expose the context menu instead of invoking
        # the plugin:// playback resolver from a Home shelf.
        item.setProperty("IsPlayable", "true")
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
