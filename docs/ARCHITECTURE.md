# CINÉVA architecture

## Separation of concerns
Kodi video add-ons and library nodes own content retrieval. They populate Kodi ListItems and properties. CINÉVA owns navigation, layout, focus behavior and presentation only. No direct Trakt/TMDb/MDBList/Real-Debrid API integration belongs in the skin.

## Widget configuration model
Widgets are configured from CINÉVA Skin Settings, not from a separate My Widgets destination. Home, Movies and TV Shows each expose four numbered widget slots to match the current renderer. Each slot can be selected, changed or cleared independently.

The source picker enumerates enabled Kodi video add-ons, then browses their exposed folders/nodes through Kodi JSON-RPC. It must also support Kodi library nodes and playlists as the settings UI is completed. Users choose the source folder/path; the skin displays that source in the matching native content shelf.

Initial Home defaults (first-install convenience only):
- Home / Widget 1 — POV Continue Watching Movies
- Home / Widget 2 — POV In Progress Shows
- Home / Widget 3 — POV Trending Movies
- Home / Widget 4 — POV Trending TV Shows

Defaults are seeded only when the widget registry is first created. They are editable and removable. An intentionally empty slot or screen must remain empty after restart; defaults must never be silently restored. Movies and TV Shows start empty unless defaults are explicitly added later. Defaults must never reset any add-on's watched-provider settings.

## Rendering and performance
- Prefer native Kodi containers and built-in list item properties.
- Keep each screen's widget slots independent.
- Empty slots render nothing; non-empty slots render the selected source.
- Avoid expensive blur, glass effects, continuously running animations and unnecessary background artwork reloads.
- Keep focus movement deterministic and remote-friendly.
- Do not duplicate content retrieval in skin code.
