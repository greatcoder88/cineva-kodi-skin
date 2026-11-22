# POV-compatible GUI test fixture

This test-only add-on is installed by `.github/workflows/kodi-gui-test.yml`. It exposes the `plugin.video.pov` ID and the four directory URL shapes used by CINÉVA's default Home widgets. It returns deterministic movie/TV ListItems with locally generated poster art so the GUI test can validate container loading and poster rendering without user credentials, Trakt, TMDb, Real-Debrid, or network APIs.

It is not the real POV add-on and is never included in the production skin ZIP.
