# CINÉVA Widget Source Picker

This helper backs the per-screen widget slots exposed by CINÉVA Skin Settings.
It is not a separate navigation destination or a standalone "My Widgets" screen.

- Screens: Home, Movies, TV Shows.
- Four numbered slots per screen, matching the current skin renderer.
- First-install Home defaults use POV for Continue Watching Movies, In Progress Shows,
  Trending Movies and Trending TV Shows. Users can change or clear every slot.
- Defaults are seeded only when the registry file does not exist. Clearing all
  widgets is intentional and does not cause defaults to reappear.
- Each slot browses enabled Kodi video add-ons and their folders via JSON-RPC.
- The selected plugin:// source is persisted and mirrored into Skin.String properties.

Skin Settings should invoke:
`RunScript(script.cineva.widgets,action=configure&screen=home&slot=1)`
Use `screen=movies` or `screen=tvshows` for the other screens and slot=1..4.
The skin remains responsible for rendering the selected source in its native
containers. Runtime rendering and add-on-specific Files.GetDirectory compatibility
must be validated in Kodi 23 and separately on Fire TV Stick 4K.
