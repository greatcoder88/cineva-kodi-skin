# CINÉVA Nimbus foundation

## Why the base is changing

The previous CINÉVA package was assembled from a small legacy skin archive and a large patching script. That produced a custom Home screen, but it did not inherit Nimbus's actual navigation, view system, Home composition or shared include architecture.

The new foundation is built from the pinned upstream Nimbus source tree:

- Skin: ivarbrandt/skin.nimbus at 8b5071b8cd0db3a8e813eb00e9a821d3efad2454
- Helper source: ivarbrandt/script.nimbus.helper at e42d2ffffbccaa58386ef2e4a054049e5fcb7664
- Kodi target: 22 (Piers), with xbmc.gui 5.18.0

The build keeps Nimbus's actual xml/Home.xml, xml/Includes_Home.xml,
xml/Includes_HomeLayouts.xml, shared view definitions, fonts, textures and
dialogs. The add-on identity becomes skin.cineva.

## Licensing and attribution

Nimbus code is GPL-2.0-only. Nimbus artwork is CC BY-SA 4.0. The upstream
LICENSE.txt is retained in the skin package, and a notice is included
in both packages. The helper bridge also carries a copy of the upstream license
notice.

## API boundary

The upstream Nimbus Helper includes an MDBList/TMDb ratings service and API
modules. Those are deliberately excluded from the CINÉVA bridge:

- no MDBList/TMDb ratings monitor, API module or ratings database is packaged;
- a minimal local-only xbmc.service entry remains so Kodi can resolve and enable
  the Nimbus bridge dependency; it only waits for Kodi shutdown and performs no
  network requests;
- API-key and rating-cache controls are removed from the skin settings;
- the bridge retains local menu-path/widget XML generation, search history,
  local cache cleanup and non-network UI actions.

The skin should consume Kodi ListItems supplied by POV, Umbrella or Kodi library
sources. It should not fetch metadata or ratings directly from Trakt, TMDb,
MDBList or Real-Debrid.

## Current migration stage

This branch is the first architecture stage, not a finished CINÉVA redesign.

1. Build a Nimbus-derived skin.cineva package from pinned upstream source.
2. Rename the Nimbus helper to script.cineva.nimbus and remove its API service.
3. Validate Kodi 22 package loading and capture the real Nimbus-derived Home.
4. Next: map CINÉVA's four configurable Home, Movies and TV Shows slots onto
   Nimbus's widget/menu system; then apply the CINÉVA hero, rating and artwork
   treatment without replacing Nimbus's navigation and view foundations.

The old 0.5.x build remains untouched during this validation stage. Do not
publish the Nimbus-derived package as the default repository release until its
Kodi GUI smoke test and widget-source integration pass.
