# CINÉVA Widget Source Picker

This Kodi Python helper backs the per-screen widget slots exposed in CINÉVA Skin Settings. It is not a separate navigation destination.

- Screens: Home, Movies and TV Shows.
- Four numbered slots per screen, matching the current skin renderer.
- First-install Home defaults: POV Continue Watching Movies, In Progress Shows, Trending Movies and Trending TV Shows.
- Defaults are written only when the registry file is first created. Clearing all Home slots does not restore defaults.
- The picker lists enabled Kodi video add-ons and browses their folders through Kodi JSON-RPC.
- A selected `plugin://` folder is persisted in the profile registry and mirrored into the skin string properties.
- Existing selections can be kept, changed or cleared. Internal empty slots retain their slot numbers.

Skin Settings invokes the helper with:

```
RunScript(script.cineva.widgets,action=configure&screen=home&slot=1)
```

Use `screen=movies` or `screen=tvshows` and `slot=1..4` for other slots.

## Runtime contract

The manager stores source paths; it does not call add-on APIs or own presentation. The skin's native containers render the selected paths. Add-ons can expose different directory structures, so validate the picker against the installed POV/Umbrella versions. A deterministic CI fixture validates Kodi startup and the Home renderer, but does not replace interactive picker testing or the physical Fire TV Stick test.
