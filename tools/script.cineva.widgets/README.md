# CINÉVA Widget Manager 0.1.0

A Kodi Python 3 helper prototype. It stores an ordered registry independently for Home, Movies, TV Shows, Search and My List. It discovers enabled video plugin add-ons using Kodi JSON-RPC, browses plugin folders with `Files.GetDirectory`, and supports add, rename, change-source, reorder and remove.

## Development invocation

Install the ZIP with `script.cineva.widgets/` at its root, then call:

```
RunScript(script.cineva.widgets,action=manage&screen=home)
```

Supported screens: `home`, `movies`, `tvshows`, `search`, `mylist`. To inspect the stored registry in the Kodi log, call `RunScript(script.cineva.widgets,action=list)`.

## Important limitation

This is the configuration and source-browser helper, not the finished skin-side dynamic renderer. Kodi skin XML does not instantiate an arbitrary number of controls from a JSON array by itself; the CINÉVA skin still needs its renderer strategy wired to this registry. Validate `Files.GetDirectory` against each target add-on and Kodi 23 before release. No Fire TV or Kodi runtime test is claimed.
