#!/usr/bin/env python3
"""Fetch distinct movie/TV posters and real landscape fanart for the Kodi GUI fixture.

Artwork is downloaded only on the CI runner. Movie posters use fixed TMDB image
paths; series posters come from TVmaze. Movie fanart paths are resolved from
TMDB's movie-details API so stale hand-copied image URLs cannot break the GUI
test. The public read-only TMDB key below is published by the open-source
lacymorrow/movie-art project; it is not a repository secret.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

MOVIES = [
    ("movie-1.jpg", "The Shawshank Redemption", "q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg"),
    ("movie-2.jpg", "The Dark Knight", "qJ2tW6WMUDux911r6m7haRef0WH.jpg"),
    ("movie-3.jpg", "Interstellar", "gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"),
    ("movie-4.jpg", "Inception", "oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg"),
    ("movie-5.jpg", "The Matrix", "p96dm7sCMn4VYAStA6siNz30G1r.jpg"),
    ("movie-6.jpg", "Dune: Part Two", "6izwz7rsy95ARzTR3poZ8H6c5pp.jpg"),
]
SHOWS = [
    ("tv-1.jpg", "Breaking Bad"),
    ("tv-2.jpg", "Dark"),
    ("tv-3.jpg", "Severance"),
    ("tv-4.jpg", "The Last of Us"),
    ("tv-5.jpg", "The Bear"),
    ("tv-6.jpg", "Sherlock"),
]
MOVIE_BACKDROPS = [
    ("backdrop-1.jpg", "The Shawshank Redemption", 278),
    ("backdrop-2.jpg", "The Dark Knight", 155),
    ("backdrop-3.jpg", "Interstellar", 157336),
    ("backdrop-4.jpg", "Inception", 27205),
    ("backdrop-5.jpg", "The Matrix", 603),
    ("backdrop-6.jpg", "Dune: Part Two", 693134),
]
TMDB_API_KEY = "9d2bff12ed955c7f1f74b83187f188ae"
TMDB_DETAILS = "https://api.themoviedb.org/3/movie/{}?api_key=" + TMDB_API_KEY
TMDB_IMAGE = "https://image.tmdb.org/t/p/w500/{}"
TMDB_BACKDROP = "https://image.tmdb.org/t/p/w1280{}"
TVMAZE_SEARCH = "https://api.tvmaze.com/singlesearch/shows?q={}"
USER_AGENT = "CINEVA-Kodi-Skin-CI/1.0 (https://github.com/greatcoder88/cineva-kodi-skin)"


def request_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def request_json(url):
    return json.loads(request_bytes(url).decode("utf-8"))


def convert_and_validate(raw, target, width, height):
    subprocess.run([
        "convert", str(raw), "-auto-orient", "-resize",
        "{}x{}^".format(width, height), "-gravity", "center",
        "-extent", "{}x{}".format(width, height), "-strip",
        "-quality", "88", str(target),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw.unlink(missing_ok=True)
    data = target.read_bytes()
    if len(data) < 5000 or not data.startswith(b"\\xff\\xd8\\xff"):
        raise SystemExit("Downloaded artwork is empty or not a valid JPEG: " + target.name)
    dimensions = subprocess.check_output(
        ["identify", "-format", "%wx%h", str(target)], text=True
    ).strip()
    expected = "{}x{}".format(width, height)
    if dimensions != expected:
        raise SystemExit("Unexpected dimensions for {}: {} (expected {})".format(
            target.name, dimensions, expected
        ))
    return hashlib.sha256(data).hexdigest(), len(data)


def save_artwork(url, target, width, height):
    raw = target.with_suffix(target.suffix + ".download")
    raw.write_bytes(request_bytes(url))
    return convert_and_validate(raw, target, width, height)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: download_test_posters.py POSTER_DIRECTORY")
    output = pathlib.Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    poster_hashes = set()

    for filename, title, poster_path in MOVIES:
        target = output / filename
        digest, size = save_artwork(TMDB_IMAGE.format(poster_path), target, 342, 513)
        if digest in poster_hashes:
            raise SystemExit("Duplicate poster artwork returned for: " + title)
        poster_hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    for filename, title in SHOWS:
        query = urllib.parse.quote(title, safe="")
        show = request_json(TVMAZE_SEARCH.format(query))
        if show.get("name", "").casefold() != title.casefold():
            raise SystemExit("TVmaze returned the wrong show for {}: {}".format(
                title, show.get("name")
            ))
        image = show.get("image") or {}
        image_url = image.get("original") or image.get("medium")
        if not image_url:
            raise SystemExit("TVmaze returned no poster artwork for: " + title)
        target = output / filename
        digest, size = save_artwork(image_url, target, 342, 513)
        if digest in poster_hashes:
            raise SystemExit("Duplicate poster artwork returned for: " + title)
        poster_hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    # Match the fixture's exact backdrop-1.jpg ... backdrop-6.jpg contract.
    backdrop_hashes = set()
    for filename, title, movie_id in MOVIE_BACKDROPS:
        details = request_json(TMDB_DETAILS.format(movie_id))
        if details.get("title", "").casefold() != title.casefold():
            raise SystemExit("TMDB returned the wrong movie for {}: {}".format(
                title, details.get("title")
            ))
        backdrop_path = details.get("backdrop_path")
        if not backdrop_path:
            raise SystemExit("TMDB returned no landscape backdrop for: " + title)
        target = output / filename
        digest, size = save_artwork(
            TMDB_BACKDROP.format(backdrop_path), target, 1280, 720
        )
        if digest in backdrop_hashes:
            raise SystemExit("Duplicate landscape fanart returned for: " + title)
        backdrop_hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    if len(poster_hashes) != len(MOVIES) + len(SHOWS):
        raise SystemExit("Expected 12 distinct poster images; got {}".format(len(poster_hashes)))
    if len(backdrop_hashes) != len(MOVIE_BACKDROPS):
        raise SystemExit("Expected six distinct landscape backdrops; got {}".format(
            len(backdrop_hashes)
        ))
    print("Downloaded and verified 12 distinct posters and six landscape backdrops.")


if __name__ == "__main__":
    main()
