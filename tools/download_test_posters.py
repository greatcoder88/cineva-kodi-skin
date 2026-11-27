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
    ("movie-7.jpg", "Oppenheimer", "ptpr0kGAckfQkJeJIt8st5dglvd.jpg"),
    ("movie-8.jpg", "Barbie", "iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg"),
]
SHOWS = [
    ("tv-1.jpg", "Breaking Bad"),
    ("tv-2.jpg", "Dark"),
    ("tv-3.jpg", "Severance"),
    ("tv-4.jpg", "The Last of Us"),
    ("tv-5.jpg", "The Bear"),
    ("tv-6.jpg", "Sherlock"),
    ("tv-7.jpg", "Game of Thrones"),
    ("tv-8.jpg", "Succession"),
]
MOVIE_BACKDROPS = [
    ("backdrop-1.jpg", "The Shawshank Redemption", 278),
    ("backdrop-2.jpg", "The Dark Knight", 155),
    ("backdrop-3.jpg", "Interstellar", 157336),
    ("backdrop-4.jpg", "Inception", 27205),
    ("backdrop-5.jpg", "The Matrix", 603),
    ("backdrop-6.jpg", "Dune: Part Two", 693134),
    ("backdrop-7.jpg", "Oppenheimer", 872585),
    ("backdrop-8.jpg", "Barbie", 346698),
]
SHOW_BACKDROPS = [
    ("tv-backdrop-1.jpg", "Breaking Bad", 1396),
    ("tv-backdrop-2.jpg", "Dark", 70523),
    ("tv-backdrop-3.jpg", "Severance", 95396),
    ("tv-backdrop-4.jpg", "The Last of Us", 100088),
    ("tv-backdrop-5.jpg", "The Bear", 136315),
    ("tv-backdrop-6.jpg", "Sherlock", 19885),
    ("tv-backdrop-7.jpg", "Game of Thrones", 1399),
    ("tv-backdrop-8.jpg", "Succession", 76331),
]
TMDB_API_KEY = "9d2bff12ed955c7f1f74b83187f188ae"
TMDB_DETAILS = "https://api.themoviedb.org/3/movie/{}?api_key=" + TMDB_API_KEY
TMDB_TV_DETAILS = "https://api.themoviedb.org/3/tv/{}?api_key=" + TMDB_API_KEY
TMDB_IMAGE = "https://image.tmdb.org/t/p/w500/{}"
TMDB_BACKDROP = "https://image.tmdb.org/t/p/w1280{}"
TVMAZE_SEARCH = "https://api.tvmaze.com/singlesearch/shows?q={}"
USER_AGENT = "CINEVA-Kodi-Skin-CI/1.0 (https://github.com/greatcoder88/cineva-kodi-skin)"
JPEG_SIGNATURE = bytes.fromhex("ffd8ff")


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
    if len(data) < 5000 or not data.startswith(JPEG_SIGNATURE):
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


def resolve_clearlogo_font():
    """Prefer the legacy Poppins face, then Nimbus's bundled Inter fonts."""
    candidates = (
        pathlib.Path("skin.cineva/fonts/Poppins-SemiBold.ttf"),
        pathlib.Path("skin.cineva/fonts/Inter-SemiBold.ttf"),
        pathlib.Path("skin.cineva/fonts/Inter-Bold.ttf"),
    )
    return next((font for font in candidates if font.is_file()), None)


def create_clearlogo(output, filename, title, point_size):
    """Create deterministic transparent title art for the GUI fixture."""
    font = resolve_clearlogo_font()
    if font is None:
        raise SystemExit(
            "CINÉVA requires Poppins-SemiBold.ttf or a bundled Nimbus Inter font "
            "to generate clearlogo fixtures"
        )
    target = output / filename
    subprocess.run([
        "convert", "-size", "1220x84", "xc:none",
        "-font", str(font), "-pointsize", str(point_size), "-fill", "#f5f5f5",
        "-gravity", "west", "-annotate", "+0+0", title,
        "-trim", "+repage", str(target),
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = target.read_bytes()
    if not data.startswith(bytes.fromhex("89504e470d0a1a0a")):
        raise SystemExit("Generated clearlogo is not a valid PNG: " + filename)
    dimensions = subprocess.check_output(
        ["identify", "-format", "%wx%h", str(target)], text=True
    ).strip()
    width, height = (int(value) for value in dimensions.split("x"))
    channels = subprocess.check_output(
        ["identify", "-format", "%[channels]", str(target)], text=True
    ).strip().lower()
    if width > 1220 or height > 84 or width < 100 or height < 20 or "a" not in channels:
        raise SystemExit("Generated clearlogo must be a bounded transparent PNG: " + filename)
    print("{} -> {} ({}x{}, transparent)".format(title, filename, width, height))


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

    # Match the fixture's exact backdrop-1.jpg ... backdrop-8.jpg contract.
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

    tv_backdrop_hashes = set()
    for filename, title, show_id in SHOW_BACKDROPS:
        details = request_json(TMDB_TV_DETAILS.format(show_id))
        if details.get("name", "").casefold() != title.casefold():
            raise SystemExit("TMDB returned the wrong show for {}: {}".format(
                title, details.get("name")
            ))
        backdrop_path = details.get("backdrop_path")
        if not backdrop_path:
            raise SystemExit("TMDB returned no landscape backdrop for: " + title)
        target = output / filename
        digest, size = save_artwork(
            TMDB_BACKDROP.format(backdrop_path), target, 1280, 720
        )
        if digest in tv_backdrop_hashes or digest in backdrop_hashes:
            raise SystemExit("Duplicate landscape fanart returned for: " + title)
        tv_backdrop_hashes.add(digest)
        print("{} -> {} ({} bytes)".format(title, filename, size))

    create_clearlogo(output, "clearlogo-movie-1.png", "THE SHAWSHANK REDEMPTION", 76)
    create_clearlogo(output, "clearlogo-tv-1.png", "BREAKING BAD", 120)

    if len(poster_hashes) != len(MOVIES) + len(SHOWS):
        raise SystemExit("Expected 16 distinct poster images; got {}".format(len(poster_hashes)))
    if len(backdrop_hashes) != len(MOVIE_BACKDROPS):
        raise SystemExit("Expected eight distinct movie backdrops; got {}".format(len(backdrop_hashes)))
    if len(tv_backdrop_hashes) != len(SHOW_BACKDROPS):
        raise SystemExit("Expected eight distinct TV backdrops; got {}".format(len(tv_backdrop_hashes)))
    print("Downloaded and verified 16 distinct posters plus 16 distinct movie/TV hero backdrops.")


if __name__ == "__main__":
    main()
