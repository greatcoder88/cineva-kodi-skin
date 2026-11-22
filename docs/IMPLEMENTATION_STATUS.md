# Implementation status

## Initial baseline
- [x] Private GitHub repository created and access verified.
- [x] Product requirements and architectural constraints recorded.
- [ ] Audit current CINÉVA candidate source against this contract.
- [ ] Bring the audited add-on source into `skin.cineva/` without using Nimbus as a renamed base.
- [ ] Implement unbounded per-screen widget configuration and picker flow.
- [ ] Validate Kodi 23 XML/includes/assets and package layout.
- [ ] Install and test on Kodi 23; separately test on Fire TV Stick 4K.

## Validation honesty
Static checks can verify XML well-formedness, references and archive structure. They cannot certify Kodi rendering, add-on picker behavior, focus navigation, memory use or Fire TV performance. Those require actual Kodi runtime tests.