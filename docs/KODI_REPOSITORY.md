# CINÉVA Kodi Add-on Repository

CINÉVA ships as two independently versioned Kodi add-ons:

- `skin.cineva` — the skin.
- `script.cineva.widgets` — the widget source picker required by the skin.

The repository feed is assembled from the exact packages produced by the build. It contains Kodi's `addons.xml`, its MD5 checksum, versioned ZIPs and the `repository.cineva` installer add-on. The feed is intended for Kodi 22 (Piers).

## Hosting

GitHub Pages currently builds the `main` branch root. The repository workflow commits the generated feed into the `repository-site/` subdirectory, so the feed is served at:

`https://greatcoder88.github.io/cineva-kodi-skin/repository-site/`

No Pages source change or custom domain is needed. The custom-domain field should remain blank. Each generated directory contains an HTML index with relative links whose visible names match their hrefs, matching Kodi's HTTPDirectory parser.

## Install through Kodi's Add file source flow

Do not download the installer in a separate browser. Use Kodi's own File Manager:

1. Open **Settings → File manager → Add source**.
2. Enter `https://greatcoder88.github.io/cineva-kodi-skin/repository-site/` as the source location and name it `CINÉVA`.
3. Open **Add-ons → Install from ZIP file → CINÉVA**.
4. Select `repository.cineva-0.1.1.zip` at the source root.
5. Open **Install from repository → CINÉVA Add-on Repository**.
6. Open **Look and feel → Skin → CINÉVA** and install it. Kodi installs the Widget Helper dependency automatically.
7. After installation, future feed refreshes provide normal Kodi add-on updates.

The root source index exposes the repository installer directly. The `zips/` directory also contains browsable folders for the repository, skin and helper packages. The repository add-on reads `addons.xml`, `addons.xml.md5` and `zips/` from the same Pages base URL.

## Release discipline

- Bump the skin version in the source add-on manifest/build script and the helper version in `tools/script.cineva.widgets/addon.xml` for releases.
- Keep the skin's declared helper dependency version aligned with the helper package version.
- Never publish a package from an untested or draft build.
- The repository workflow validates package IDs, ZIP presence, feed checksum and the browsable source indexes; it does not replace Kodi GUI, POV/Umbrella or physical Fire TV validation.
