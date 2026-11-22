# CINÉVA — Kodi Skin

CINÉVA is an independent, remote-first cinematic skin for Kodi. It is designed as a presentation layer: video add-ons and Kodi library nodes provide content; the skin renders it. The skin must not call Trakt, TMDb, MDBList or Real-Debrid APIs directly.

## Target
- Kodi 23 (Piers), with compatibility verified against the user's Kodi build before release
- Amazon Fire TV Stick 4K (2024 generation)
- POV and Umbrella as initial data sources, without hard-coding either add-on into the skin architecture

## Product requirements
- Cinematic Home hero driven by the focused item
- Poster shelves, resume progress, ratings and metadata without overlap
- Home, Movies, TV Shows, Search, My List, details, player OSD and standard Kodi dialogs
- Generic configurable widgets: choose installed video add-ons/nodes/playlists, add multiple widgets, reorder, rename and remove them; separate configuration per screen; no fixed six-slot ceiling
- POV defaults: Continue Watching Movies, Continue Watching TV Shows, Trending Movies and Trending TV Shows
- Lightweight focus/navigation behavior for Fire TV remote and limited memory

## Repository status
This repository has just been initialized. The first source commit establishes the product contract and implementation plan. It is not an installable release yet. No Kodi GUI runtime or Fire TV device test is claimed by this repository until such a test is actually performed.

## Layout
- `skin.cineva/` — Kodi skin add-on source
- `docs/` — architecture, compatibility and test notes
- `tools/` — repeatable static validation/build scripts

## Release policy
A release ZIP must preserve the `skin.cineva/` add-on root and include all required XML, media, fonts and metadata. Static XML/asset checks are necessary but do not replace installation and runtime testing in Kodi.