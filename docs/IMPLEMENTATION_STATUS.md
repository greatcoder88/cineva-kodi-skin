# Implementation status

## Widget settings redesign
- [x] Remove the separate My Widgets destination from the Home navigation model.
- [x] Restrict widget configuration data to Home, Movies and TV Shows.
- [x] Add four independently configurable slot actions per screen to the widget helper.
- [x] Preserve editable POV Home defaults on first install.
- [x] Ensure clearing all widgets does not silently restore defaults.
- [x] Persist selected plugin paths into the skin string properties consumed by the current shelf renderer.
- [x] Wire each numbered slot into the actual CINÉVA Skin Settings UI (12 direct slot actions generated into SkinSettings.xml).
- [ ] Verify the settings picker can browse POV, Umbrella and other installed add-ons on Kodi 23.
- [ ] Complete rendering for all screen slots and verify empty-slot behavior in the installed skin.
- [x] Validate generated Kodi XML/includes/assets and release package layout in automated checks; full interactive settings validation remains pending.
- [ ] Install and test on Kodi 23; separately test on Fire TV Stick 4K.

## Validation honesty
Unit tests can verify registry behavior and persistence. Static checks can verify XML references and archive structure. They cannot certify Kodi rendering, add-on picker behavior, focus navigation, memory use or Fire TV performance. Those require actual Kodi runtime tests.
