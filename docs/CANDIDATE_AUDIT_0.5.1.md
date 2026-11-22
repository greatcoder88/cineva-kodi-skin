# Audit of the available CINÉVA 0.5.1 candidate

Audited from the locally available `CINEVA_v0.5.1_StaticFix_Kodi23.zip` and its extracted working source on 2026-11-22.

## What is present
- Add-on ID is `skin.cineva`; manifest currently declares version `0.5.0`, Kodi GUI dependency `5.18.0`, and Skin Shortcuts dependency `3.0.0`.
- Candidate archive contains a skin directory, XML windows, Roboto fonts, basic textures and artwork.
- Static report records 69 XML files with no XML parse errors, no missing include definitions, font references, texture references, or standard-window filename coverage errors.

## Blocking gaps against the agreed requirements
1. **Widgets are fixed-slot, not dynamic.** The home widget settings page exposes exactly six numbered slots (`Cineva.Widget1` through `Cineva.Widget6`). Movie and TV pages similarly reference fixed numbered properties. This does not meet the requirement for an arbitrary practical number of widgets.
2. **No complete per-screen widget manager.** The current source has separate home/movie/show settings screens, but it does not implement a data-backed ordered collection with add/remove/reorder/rename operations.
3. **Picker behavior is not runtime-verified.** The XML invokes `script.skinshortcuts` with `type=skinstring`; that does not by itself prove enumeration of all installed add-on folders/nodes or correct persistence of all widget fields.
4. **Static validation is not a Kodi runtime test.** XML parsing and asset-reference checks cannot verify Kodi 23 window behavior, focus movement, container content loading, dialogs, Fire TV memory use or remote responsiveness.
5. **The candidate is not a finished release.** It must not be described as a tested, install-ready CINÉVA release.

## Next engineering work
- Treat this candidate only as a source/reference snapshot, not as the final architecture.
- Design a generic widget registry per screen, with stable IDs and an ordered list, so the number of widgets is not capped by hard-coded XML slots.
- Keep add-on content retrieval outside the skin; use Kodi ListItems and add-on-provided properties.
- Implement a proper picker/editor flow and validate it against Kodi 23 and the installed Skin Shortcuts version.
- Re-run static checks, package checks, then perform actual Kodi runtime testing before calling it a release.
