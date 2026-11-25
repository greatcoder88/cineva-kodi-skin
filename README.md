# CINÉVA — Kodi Skin

CINÉVA is an independent, remote-first cinematic Kodi skin. Kodi video add-ons and library sources provide content; CINÉVA renders it. The skin does not call Trakt, TMDb, MDBList or Real-Debrid APIs directly.

## Supported target

- Kodi 22 (Piers).
- Amazon Fire TV Stick 4K (2024 generation) is the target hardware.
- POV and Umbrella are intended as video add-on sources through Kodi's plugin interfaces; behavior must be checked against the installed add-on versions.
- Kodi 21 is not a supported target.

## Product surface

- Cinematic Home hero driven by the focused item, with a bold 40px ExtraBold text-title fallback, clearlogo support, fanart/poster fallback and a selected-item plugin URL playback handoff.
- Four configurable widget slots on each of Home, Movies and TV Shows.
- Movies and TV Shows catalogue rails with direct Kodi library shortcuts for titles, genres, years, movie sets, TV studios and recently added items; D-pad left/right paths are explicit.
- First-install Home defaults: Continue Watching Movies, In Progress Shows, Trending Movies and Trending TV Shows (POV paths).
- Per-screen widget selection from enabled Kodi video add-ons using the widget manager's folder picker.
- Compact native 2:3 Home poster shelves with three-line captions, resume progress and a restrained 108% crimson D-pad selection state.
- Standard Kodi dialogs and player surfaces remain Kodi-owned.


## Install from Kodi File Manager

Add this source in Kodi's **Settings → File manager → Add source**:

`https://greatcoder88.github.io/cineva-kodi-skin/`

Then open **Add-ons → Install from ZIP file → CINÉVA**, choose `repository.cineva-0.1.3.zip` at the source root, and finish through **Install from repository → CINÉVA Add-on Repository**. No separate browser download or custom domain is required. The repository workflow publishes the generated feed to the `gh-pages` branch root. GitHub Pages must serve the `gh-pages` branch from `/(root)`. The root page is a Kodi-compatible directory listing, not this README.

See [the complete Kodi installation guide](docs/KODI_REPOSITORY.md) for details.

## Build and automated validation

```sh
python -m unittest discover -s tests -v
python tools/build_skin_archive.py
python -m py_compile tools/script.cineva.widgets/default.py tools/script.cineva.widgets/resources/lib/manager.py
```

GitHub Actions validates XML/assets/package structure, unit tests the widget manager with mocked Kodi APIs, and launches Kodi Piers with a deterministic video add-on fixture. The GUI smoke test verifies startup, active-skin selection and selected Home rendering paths. It is not a complete interactive test of all screens, all 12 settings slots, third-party add-ons or Fire TV hardware.

## Release status

**Not yet certified production-ready.** Automated checks and the Linux Kodi Piers GUI smoke test provide useful regression coverage, but neither certifies every add-on or physical device. The remaining release gates are:

1. Interactive Kodi validation of all 12 slots: browse, select, replace, clear, persistence, restart and intentionally empty slots.
2. Real POV and Umbrella validation on the exact installed add-on versions, including their directory responses and resulting shelf rendering.
3. Physical Fire TV Stick 4K validation: clean install and update, D-pad focus across every screen, playback/resume hand-off, memory use, responsiveness and recovery after add-on errors.
4. A final release build and install/upgrade test from the distributable ZIP.

A Linux GUI pass is useful evidence, not a substitute for these checks. Do not publish a stable release or describe the build as production-ready until all gates pass.

## Repository layout

- `skin.cineva-0.5.29.zip` — distributable skin package.
- `tools/build_skin_archive.py` — deterministic package builder and source patcher.
- `tools/script.cineva.widgets/` — per-screen widget source picker.
- `tests/` and `.github/workflows/` — automated validation.
- `docs/` — architecture, implementation status and release gates.
