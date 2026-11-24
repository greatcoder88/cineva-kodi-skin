# CINÉVA Kodi Add-on Repository

CINÉVA ships as two independently versioned Kodi add-ons:

- `skin.cineva` — the skin.
- `script.cineva.widgets` — the widget source picker required by the skin.

The repository feed is assembled from the exact packages produced by the build. It contains Kodi's `addons.xml`, its MD5 checksum, versioned ZIPs and the `repository.cineva` installer add-on. The feed is intended for Kodi 22 (Piers).

## Hosting

The source repository is private. Kodi cannot authenticate to a private GitHub repository when it fetches repository metadata or packages. The generated feed therefore must be published at the public GitHub Pages URL configured in `tools/build_repository.py`.

Before the first deployment, enable GitHub Pages for this repository with **Build and deployment → Source: GitHub Actions**. The workflow `.github/workflows/repository.yml` then builds and deploys the feed from `main`. If this GitHub account does not allow Pages for a private repository, publish the generated `repository-site/` directory to a separate public static host/repository; do not make the source repository public merely to expose the feed.

## Kodi installation

After the Pages deployment is live, download `repository.cineva-0.1.0.zip` from the published site's `zips/repository.cineva/` directory. In Kodi:

1. **Add-ons → Install from ZIP file** and select that repository ZIP.
2. Open **Install from repository → CINÉVA Add-on Repository**.
3. Install **CINÉVA Skin**. Kodi will install the Widget Helper dependency automatically.
4. Future repository refreshes provide normal Kodi add-on updates.

Do not advertise the feed URL or instruct users to add it as a source until the first Pages deployment is confirmed successful.

## Release discipline

- Bump the skin version in the source add-on manifest/build script and the helper version in `tools/script.cineva.widgets/addon.xml` for releases.
- Keep the skin's declared helper dependency version aligned with the helper package version.
- Never publish a package from an untested or draft build.
- The repository workflow validates package IDs, ZIP presence and feed checksum; it does not replace Kodi GUI, POV/Umbrella or physical Fire TV validation.
