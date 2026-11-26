# CINÉVA Nimbus-reference rebuild

## Decision

Rebuild the presentation layer from the current Nimbus skin architecture instead of continuing to layer bespoke Home-screen fixes onto the existing CINÉVA package. Nimbus is the visual and interaction reference; CINÉVA remains a separately branded Kodi 22 skin.

Reference source:
- Repository: https://github.com/ivarbrandt/skin.nimbus
- Pinned inspection revision: 8b5071b8cd0db3a8e813eb00e9a821d3efad2454
- Relevant implementation: `xml/Home.xml`, `xml/Includes_Home.xml`, `xml/Includes_HomeLayouts.xml`, `xml/View_54_Flix.xml`, `xml/View_55_FlixScape.xml`, `xml/View_56_FlixList.xml`, `xml/SkinSettings.xml`, `xml/Includes.xml`, `xml/VideoOSD.xml`.

## Non-negotiable CINÉVA requirements

- Target Kodi 22 (Piers), not Kodi 21.
- Keep CINÉVA branding and the existing per-screen widget model: four independently configurable slots on Home, Movies and TV Shows.
- Keep the first-install Home defaults editable and clearable; Movies and TV Shows remain user-configurable.
- Keep POV and Umbrella as Kodi video add-on content providers. Skin code must render Kodi ListItems/plugin folders and must not add direct Trakt, TMDb, MDBList or Real-Debrid API clients.
- Keep standard Kodi dialogs and playback ownership with Kodi.
- Keep D-pad focus paths explicit, deterministic and usable with a Fire TV remote.

## Rebuild approach

1. Treat Nimbus Home composition, widget presentation, focus transitions, list item layouts, poster/Flix views, and settings navigation as the source of truth.
2. Replace the current custom Home composition rather than stacking further conditional overlays and special-case focus repairs on it.
3. Port only the skinning layer and the Kodi-native interaction patterns. Do not import Nimbus helper API behavior that violates CINÉVA's provider boundary.
4. Adapt Nimbus's view and widget patterns to CINÉVA's four-slot-per-screen configuration and current widget picker.
5. Update the package identity, branding, assets and Kodi 22 dependency declarations only after the runtime dependency graph has been audited.
6. Validate clean install, update, empty slots, all twelve widget slots, poster selection, playback handoff, search keyboard, settings, Back behavior and all D-pad directions in Kodi 22 GUI. Then perform the physical Fire TV Stick test.

## Release rule

A source-level port or Linux GUI smoke pass is not a production certification. Do not publish a new stable package until the Kodi 22 GUI checks pass and the package can be installed and upgraded from the repository feed. Do not claim physical Fire TV validation unless it was actually performed.

## Current implementation note

The existing package is a generated ZIP and its editable skin XML is patched by `tools/build_skin_archive.py`. The rebuild must change the source/build pipeline and the distributable together; editing a generated ZIP alone is not a maintainable fix.
