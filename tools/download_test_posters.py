#!/usr/bin/env python3
"""Fetch distinct real poster thumbnails for the deterministic Kodi GUI fixture.

Images are downloaded only on the CI runner and are not committed. Wikipedia
page-image thumbnails keep this test independent of API keys while exercising
Kodi's actual local poster rendering path.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.parse
import urllib.request

PAGES = [
    ("movie-1.jpg", "The Shawshank Redemption"),
    ("movie-2.jpg", "The Dark Knight (film)"),
    ("movie-3.jpg", "Interstellar (film)"),
    ("movie-4.jpg", "Inception"),
    ("movie-5.jpg", "The Matrix"),
    ("movie-6.jpg", "Dune: Part Two"),
    ("tv-1.jpg", "Breaking Bad"),
    ("tv-2.jpg", "Dark (TV series)"),
    ("tv-3.jpg", "Severance (TV series)"),
    ("tv-4.jpg", "The Last of Us (TV series)"),
    ("tv-5.jpg", "The Bear (TV series)"),
    ("tv-6.jpg", "Sherlock (TV series)"),
]
USER_AGENT = "CINEVA-Kodi-Skin-CI/1.0 (https://github.com/greatcoder88/cineva-kodi-skin)"


def request_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: download_test_posters.py POSTER_DIRECTORY")
    output = pathlib.Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    titles = "|".join(title for _, title in PAGES)
    query = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "pageimages",
        "piprop": "thumbnail", "pithumbsize": "600", "redirects": "1",
        "titles": titles,
    })
    payload = json.loads(request_bytes("https://en.wikipedia.org/w/api.php?" + query))
    query_data = payload.get("query", {})
    aliases = {}
    for mapping in query_data.get("normalized", []) + query_data.get("redirects", []):
        aliases[mapping["from"].casefold()] = mapping["to"]

    def resolve(title):
        seen = set()
        while title.casefold() in aliases and title.casefold() not in seen:
            seen.add(title.casefold())
            title = aliases[title.casefold()]
        return title

    pages = {page.get("title", "").casefold(): page
             for page in query_data.get("pages", {}).values()}
    hashes = set()
    for filename, requested_title in PAGES:
        canonical = resolve(requested_title)
        page = pages.get(canonical.casefold())
        image_url = (page.get("thumbnail", {}) if page else {}).get("source")
        if not image_url:
            raise SystemExit("Wikipedia returned no poster thumbnail for: " + requested_title)
        raw = output / (filename + ".download")
        raw.write_bytes(request_bytes(image_url))
        target = output / filename
        subprocess.run([
            "convert", str(raw), "-auto-orient", "-resize", "342x513^",
            "-gravity", "center", "-extent", "342x513", "-strip",
            "-quality", "88", str(target),
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw.unlink(missing_ok=True)
        data = target.read_bytes()
        if len(data) < 5000 or not data.startswith(b"\xff\xd8\xff"):
            raise SystemExit("Downloaded poster is empty or not a valid JPEG: " + filename)
        digest = hashlib.sha256(data).hexdigest()
        if digest in hashes:
            raise SystemExit("Duplicate poster artwork returned for: " + requested_title)
        hashes.add(digest)
        dimensions = subprocess.check_output(
            ["identify", "-format", "%wx%h", str(target)], text=True
        ).strip()
        if dimensions != "342x513":
            raise SystemExit("Unexpected poster dimensions for {}: {}".format(filename, dimensions))
        print("{}: {} -> {} ({} bytes)".format(requested_title, canonical, filename, len(data)))
    if len(hashes) != len(PAGES):
        raise SystemExit("Expected 12 distinct poster images; got {}".format(len(hashes)))
    print("Downloaded and verified 12 distinct real poster images.")


if __name__ == "__main__":
    main()
