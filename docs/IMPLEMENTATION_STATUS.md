# Implementation status

## Target and release scope

- Target runtime: Kodi 22 (Piers).
- Kodi 21 is explicitly out of scope.
- Amazon Fire TV Stick 4K (2024 generation) is the target hardware; physical-device validation is a release gate.

## Widget settings

- [x] Remove the separate My Widgets destination from Home navigation.
- [x] Restrict widget configuration to Home, Movies and TV Shows.
- [x] Provide four independently configurable slots per screen in native Skin Settings.
- [x] Seed the four POV Home defaults only on first install.
- [x] Preserve internal empty slots and prevent cleared defaults from reappearing.
- [x] Persist selected plugin paths and mirror them into skin strings used by the shelf renderers.
- [x] Add Keep Current, Choose/Change Source, Clear and Cancel actions.
- [x] Add nested-folder parent navigation and reject malformed/out-of-range slot arguments.
- [x] Handle malformed JSON-RPC responses, Kodi RPC errors and runtime exceptions without crashing the helper.
- [x] Cover registry normalization, defaults, persistence, clearing, settings generation and JSON-RPC failure handling with automated tests.
- [ ] Exercise the picker interactively in Kodi against real enabled POV and Umbrella installations.
- [ ] Verify all 12 slots render and refresh correctly on their respective screens.
- [ ] Verify add-on-specific Files.GetDirectory behavior with the exact installed add-on versions.

## Visual/runtime validation

- [x] Build the distributable ZIP and validate generated Kodi XML, includes, fonts and image assets.
- [x] Run automated Python/unit checks.
- [x] Launch Kodi Piers in CI, verify CINÉVA becomes the active skin through JSON-RPC, and capture GUI screenshots.
- [x] Verify the deterministic fixture's Home hero, dynamic fanart, poster fallback, shelf scrolling, lower-row safe area and selected D-pad paths.
- [x] Surface optional season/episode metadata in the In Progress Shows hero and validate it in the live Kodi GUI fixture.
- [x] Add direct Movies and TV Shows navigation to Kodi library titles, genres, years, movie sets, TV studios and recently added items, with explicit left/right focus and a down path into the first widget shelf.
- [x] Enlarge Home poster rails to native 2:3 240×360 artwork, tighten the gutters, align two-line captions and resume progress, and retain a visible next-shelf preview; verified in Kodi GUI screenshots.
- [ ] Complete interactive Skin Settings and widget-picker testing in Kodi.
- [ ] Test Movies and TV Shows screens with populated and empty sources.
- [ ] Install and test on a physical Fire TV Stick 4K, including remote navigation, playback hand-off, memory, responsiveness and install/update behavior.

## Release decision

**Not production-ready yet.** CI proves package integrity, mocked helper behavior and a deterministic Linux Kodi 22 Home smoke test. It does not certify all screens, all widget slots, real POV/Umbrella behavior or Fire TV hardware. Stable release approval requires every unchecked gate above to pass.
