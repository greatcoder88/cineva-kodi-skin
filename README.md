# CINÉVA — Kodi Skin

CINÉVA is an independent, remote-first cinematic Kodi skin. It is a presentation layer: Kodi video add-ons and library sources provide content; CINÉVA renders it. The skin does not call Trakt, TMDb, MDBList or Real-Debrid APIs directly.

## Supported target

- Kodi 22 (Piers) — CI GUI smoke-tested on the Linux desktop runtime.
- Amazon Fire TV Stick 4K (2024 generation) — target device; physical-device validation is still required before a production release.
- POV and Umbrella are supported as add-on sources through Kodi's video add-on interfaces; the skin does not hard-code their APIs.

Kodi 21 is not a supported target for this project.

## Current product surface

- Cinematic Home hero driven by the focused item, with clearlogo/title fallback, fanart/poster fallback and hero actions.
- Four configurable widget slots on each of Home, Movies and TV Shows.
- First-install Home defaults: Continue Watching Movies, In Progress Shows, Trending Movies and Trending TV Shows (POV paths). Defaults are seeded once only; cleared slots remain empty.
- Per-screen widget selection from enabled Kodi video add-ons using the widget manager's folder picker.
- Poster shelves, progress, ratings and metadata with remote-first D-pad navigation.
- Standard Kodi dialogs and player surfaces remain Kodi-owned.

## Build and validation

Run the local checks:

```sh
python -m unittest discover -s tests -v
python tools/build_skin_archive.py
python -m py_compile tools/script.cineva.widgets/default.py tools/script.cineva.widgets/resources/lib/manager.py
```

The GitHub Actions workflows validate XML/assets/package structure and launch Kodi with a deterministic video add-on fixture. The GUI workflow checks Home rendering, hero changes, poster fallback, shelf scrolling and focus paths. It does not emulate a physical Fire TV Stick or prove compatibility with every third-party add-on.

## Release status

The current work is in the open pull request linked below; it is not yet a signed/stable production release. Before calling it production-ready, the release candidate must pass:
1. CI static/unit checks and the Kodi Piers GUI workflow.
2. An interactive Kodi test of all 12 Skin Settings slots, including add-on folder browsing, replacement, clear, persistence and empty-slot behavior.
3. A physical Fire TV Stick 4K test covering install/update, remote navigation, resume/playback hand-off, memory and responsiveness with the intended add-ons enabled.

A successful Linux GUI run is useful evidence, not a substitute for item 2 or 3.

## Repository layout

- `skin.cineva-0.5.3.zip` — distributable skin package.
- `tools/build_skin_archive.py` — deterministic package builder and source patcher.
- `tools/script.cineva.widgets/` — per-screen widget source picker.
- `tests/` and `.github/workflows/` — automated validation.
- `docs/` — architecture and implementation status.
