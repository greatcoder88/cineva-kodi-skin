# CINÉVA architecture

## Separation of concerns

Kodi video add-ons and library nodes own content retrieval. They populate Kodi ListItems and properties. CINÉVA owns navigation, layout, focus behavior and presentation only. No direct Trakt/TMDb/MDBList/Real-Debrid API integration belongs in the skin.

## Catalogue navigation

Movies and TV Shows expose a shared, remote-first navigation rail. The rail links Home, both catalogue screens, Search and the relevant widget editor, plus direct Kodi video-database nodes. Movies provide titles, genres, years, sets and recently added movies; TV Shows provide titles, genres, years, studios/networks and recently added episodes. These destinations use Kodi's native Video window and database URLs rather than hard-coded third-party plug-in routes, so Kodi retains its own folder history and Back behavior. A category may be empty when the local Kodi library has no matching content; provider-backed shelves remain independently configurable.

## Widget configuration model

Widgets are configured from CINÉVA Skin Settings, not from a separate My Widgets destination. Home, Movies and TV Shows each expose four numbered widget slots to match the current renderer. Each slot can be selected, changed or cleared independently.

The current source picker enumerates enabled Kodi video plug-ins and browses the folders they expose through Kodi JSON-RPC. It persists a selected `plugin://` folder in the profile registry and mirrors its values into skin strings. Kodi library nodes and playlists are not currently exposed by this picker and must not be represented as supported selection types until implemented and tested.

Initial Home defaults (first-install convenience only):

- Home / Widget 1 — POV Continue Watching Movies
- Home / Widget 2 — POV In Progress Shows
- Home / Widget 3 — POV Trending Movies
- Home / Widget 4 — POV Trending TV Shows

Defaults are seeded only when the registry file is first created. They are editable and removable. An intentionally empty slot or screen must remain empty after restart; defaults must never be silently restored. Movies and TV Shows start empty. Defaults must never reset any add-on's watched-provider settings.

## Rendering and performance

- Prefer native Kodi containers and built-in list item properties.
- Keep each screen's widget slots independent.
- Empty slots render nothing; non-empty slots render the selected source.
- Avoid expensive blur, glass effects, continuously running animations and unnecessary background artwork reloads.
- Keep focus movement deterministic and remote-friendly.
- Do not duplicate content retrieval in skin code.

## Runtime failure behavior

The widget helper treats malformed JSON-RPC responses, Kodi-side RPC errors and execution exceptions as unavailable results rather than allowing them to crash the settings flow. A failed folder listing must leave the current selection unchanged. Third-party plug-in folder semantics remain an integration boundary and require testing with real installed versions.
