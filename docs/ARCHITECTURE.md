# CINÉVA architecture

## Separation of concerns
Kodi video add-ons and library nodes own content retrieval. They populate Kodi ListItems and properties. CINÉVA owns navigation, layout, focus behavior and presentation only. No direct Trakt/TMDb/MDBList/Real-Debrid API integration belongs in the skin.

## Generic widget model
Each screen owns an ordered list of widget definitions. A widget definition contains a user-facing title, a source path/target, visibility and presentation settings. The editor must enumerate installed video add-ons, their exposed folders/nodes, Kodi library nodes and playlists; it must not assume POV is installed. Users can add, rename, reorder and remove entries without an artificial fixed slot count.

Initial POV defaults (first-run convenience only):

- Home — `plugin://plugin.video.pov/?mode=build_movie_list&action=in_progress_movies&name=Continue%20Watching%20Movies`
- Home — `plugin://plugin.video.pov/?mode=build_tvshow_list&action=in_progress_tvshows&name=Continue%20Watching%20TV%20Shows`
- Home — `plugin://plugin.video.pov/?mode=build_movie_list&action=tmdb_movies_trending&name=Trending%20Movies`
- Home — `plugin://plugin.video.pov/?mode=build_tvshow_list&action=tmdb_tv_trending&name=Trending%20TV%20Shows`

These defaults are user-configurable and must never reset POV's own watched-provider settings.

## Performance principles
- Prefer native Kodi containers and built-in list item properties.
- Avoid expensive blur, glass effects, continuously running animations and unnecessary background artwork reloads.
- Keep focus movement deterministic and remote-friendly.
- Do not duplicate content retrieval in skin code.