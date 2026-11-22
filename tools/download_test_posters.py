#!/usr/bin/env python3
"""Fetch distinct real movie and TV poster artwork for the Kodi GUI fixture.

Posters are downloaded only on the CI runner. Movies use public TMDB image CDN
poster paths; series artwork is resolved through TVmaze's keyless singlesearch
API. This avoids synthetic cards and does not commit third-party images.
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
    ("movie-4.jpg", "Inception", "pIkRyD18kl4FhoCNQuWxWu5cBLM.jpg"),
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
TMDB_IMAGE = "https://image.tmdb.org/t/p/w500/{}"
TVMAZE_SEARCH = "https://api.tvmaze.com/singlesearch/shows?q={}"
USER_AGENT = "CINEVA-Kodi-Skin-CI/1.0 (https://github.com/greatcoder88/cineva-kodi-skin)"


def request_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def normalize_poster(raw, target):
    raw.write_bytes(request_bytes(raw_url[0]))


def save_poster(url, target):
    raw = target.with_suffix(target.suffix + ".download")
    raw.write_bytes(request_bytes(url))
    subprocess.run([
        "convert", str(raw), "-auto-orient", "-resize", "342x513^",
        "-gravity", "center", "-extent", "342x513", "-strip",
        "-quality", "88", str(target),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw.unlink(missing_ok=True)
    data = target.read_bytes()
    if len(data) < 5000 or not data.startswith(b"\\xff\\xd8\\xff"):
        raise SystemExit("Downloaded poster is empty or not a valid JPEG: " + target.name)
    dimensions = subprocess.check_output(
        ["identify", "-format", "%wx%h", str(target)], text=True
    ).strip()
    if dimensions != "342x513":
        raise SystemExit("Unexpected poster dimensions for {}: {}".format(target.name, dimensions))
    return hashlib.sha256(data).hexdigest(), len(data)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: download_test_posters.py POSTER_DIRECTORY")
    output = pathlib.Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    hashes = set()

    for filename, title, poster_path in MOVIES:
        target = output / filename
        digest, size = save_poster(TMDB_IMAGE.format(poster_path), target)
        if digest in hashes:
            raise SystemExit("Duplicate poster artwork returned for: " + title)
        hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    for filename, title in SHOWS:
        query = urllib.parse.quote(title, safe="")
        show = json.loads(request_bytes(TVMAZE_SEARCH.format(query)))
        if show.get("name", "").casefold() != title.casefold():
            raise SystemExit("TVmaze returned the wrong show for {}: {}".format(title, show.get("name")))
        image = show.get("image") or {}
        image_url = image.get("original") or image.get("medium")
        if not image_url:
            raise SystemExit("TVmaze returned no poster artwork for: " + title)
        target = output / filename
        digest, size = save_poster(image_url, target)
        if digest in hashes:
            raise SystemExit("Duplicate poster artwork returned for: " + title)
        hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    if len(hashes) != len(MOVIES) + len(SHOWS):
        raise SystemExit("Expected 12 distinct poster images; got {}".format(len(hashes)))
    print("Downloaded and verified 12 distinct real poster images.")


if __name__ == "__main__":
    main()
