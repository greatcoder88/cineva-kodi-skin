# Implementation status

## Target and release scope

- Target runtime: Kodi 22 (Piers).
- Kodi 21 is explicitly out of scope.
- Amazon Fire TV Stick 4K (2024 generation) is the target hardware; physical-device validation is still a release gate.

## Widget settings redesign

- [x] Remove the separate My Widgets destination from Home navigation.
- [x] Restrict widget configuration to Home, Movies and TV Shows.
- [x] Provide four independently configurable slots per screen in native Skin Settings.
- [x] Seed the four POV Home defaults only on first install.
- [x] Preserve internal empty slots and prevent cleared defaults from reappearing.
- [x] Persist selected plugin paths and mirror them into skin strings used by the shelf renderers.
- [x] Add Keep Current, Choose/Change Source, Clear and Cancel actions.
- [x] Add nested-folder parent navigation and reject malformed/out-of-range slot arguments.
- [x] Cover registry normalization, defaults, persistence, clearing and generated settings structure with unit/static tests.
- [ ] Exercise the picker interactively in Kodi against real enabled POV and Umbrella installations.
- [ ] Verify all 12 slots render and refresh correctly on their respective screens.
- [ ] Verify add-on-specific Files.GetDirectory behavior with the user's actual add-on versions.

## Visual/runtime validation

- [x] Build the distributable ZIP and validate generated Kodi XML, includes, fonts and image assets.
- [x] Run automated Python/unit checks.
- [x] Launch Kodi Piers in CI, verify CINÉVA becomes the active skin through JSON-RPC, and capture GUI screenshots.
- [x] Verify Home hero, dynamic fanart, poster fallback, shelf scrolling, lower-row safe area and key D-pad paths in the deterministic CI fixture.
- [ ] Complete interactive Skin Settings and widget-picker testing in Kodi.
- [ ] Install and test on a physical Fire TV Stick 4K, including remote navigation, playback hand-off, memory and responsiveness.

## Release decision

**Not production-ready until the remaining interactive picker and physical Fire TV gates pass.** The CI environment is a Linux desktop runtime with a deterministic fixture; it cannot certify third-party add-on behavior or Fire TV hardware performance. Do not label a build stable or publish a production release based on CI alone.
