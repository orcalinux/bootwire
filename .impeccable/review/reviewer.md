# Fresh finishing review — BootWire Desktop

## Evidence

Reviewed actual native Qt software renders before reading implementation: `light-0.png`, `dark-0.png`, `compact.png`, and `light-1.png` through `light-6.png`. These cover all seven workspaces, theme parity, and the 1000×720 minimum window. Read `PRODUCT.md`, `.impeccable/surfaces/desktop.md`, and the impeccable craft floor. Sampled `Main.qml`, reusable QML controls/theme, `controller.py`, `session.py`, and protocol client verification. No browser detector applies to native QML. This is a code-led review without an image comp. The supplied test result is 98 passing, including actual Connect/Flash dialog interactions; I did not rerun tests or render.

## Requirement/fidelity matrix

| Requirement | Evidence | Assessment |
| --- | --- | --- |
| Python/PySide6/Qt Quick desktop | ApplicationWindow, controller/worker boundary | Present; real native surface |
| Clean, spacious, modern workspace | All desktop renders | Strong hierarchy, consistent rails/surfaces, restrained brand vocabulary |
| Light and dark themes | light-0/dark-0, Theme.qml | Clear parity and readable primary content |
| Firmware flashing | light-0, session flash path | Image details, address, protected destructive actions, CRC verification, optional RUN present |
| Advanced debugging | light-3/light-4, TraceTransport | Ping, custom commands, simulator faults, decoded/raw capture and exports present |
| Devices/releases | light-1/light-2 | Profiles, sequential batches, local catalog with hashes present; profile synchronization defect below |
| Explicit operation evidence/outcomes | Persistent status, activity, Inspector/history | Present, but phase indicators can claim phases not performed |
| Compact desktop | compact.png and ScrollView source | Navigation and connection persist; content scrolls. Primary flash action falls below initial fold at minimum size, acceptable but worth improving |
| Honest simulator scope | Target copy, simulator-only image guards | Clear; no production hardware certification implied |

## Material findings

1. **P2 — Profile connection leaves the visible connection settings inconsistent with the active session.** `desktop/src/bootwire_gui/qml/Main.qml:426` sets only the port before connecting with the complete saved profile. The baud combo and timeout/retry fields retain unrelated values. For example, a saved 9600-baud profile can connect while the header continues showing 115200; saving “the connection above” then serializes those stale fields through `connectionOptions()` and can overwrite a working profile with wrong settings. Apply all profile values to the editable fields when selecting a profile, or store/display the active options and use them when saving the current connection. Preserve arbitrary positive baud values accepted by the backend. Validate with a profile whose baud/timeouts/retries differ from defaults, then save and reconnect.

2. **P2 — The phase strip marks unperformed flash phases successful.** `desktop/src/bootwire_gui/qml/Main.qml:307` derives all three phase dots from a global numeric progress value. `desktop/src/bootwire_gui/controller.py:242` sets that value to 1 after erase-only or verify-only. Consequently “Erase → Write → Verify” all turn green after merely erasing a target, implying a written/verified application where none exists. Partial/failed batches can likewise finish with a full green strip. Track performed/completed phases separately for the current job, or show operation-specific phases. Validate erase-only, verify-only, write-only, cancelled flash, and a mixed-result batch. The persistent textual result helps, but should agree with the signature phase evidence.

## Polish notes

- `Main.qml:313` says “Every write is read back.” `session.py` and `bootwire/client.py:220` instead verify a target CRC-32. Use literal copy such as “Written images are verified with CRC-32.” Avoid implying a host readback capability.
- The compact screenshot places the principal flash button beneath the initial scroll area. Moving the operation action/progress closer to the image summary or keeping the main action available while scrolling would improve repeated work at 1000×720; this is not a compact-layout blocker because ScrollView exposes it.
- Preferences are visibly disabled while connected, but their explanatory copy says changes apply on the next connection. A short “Disconnect to edit connection defaults” hint would explain the disabled state.
- Search fields have useful initial empty states but no dedicated “no matches” feedback when a populated list filters to zero results. Small targeted copy would prevent a blank panel from looking broken.
- Palette, spacing, typography, semantic colors, native controls, and focus treatment form a coherent first release. No decorative imagery is needed, and no rebuild is justified.

## Verdict

**FIX**, limited to the two material state-accuracy issues above and the readback wording. The visual direction is ready to ship. After those corrections, perform focused behavioral checks and refresh screenshots only for any visibly changed states; a broad redesign or new art direction is unnecessary. Hardware validation and future concurrent sessions are outside this review’s first-release scope.


## Verdict pass — focused correction review

Re-inspected replacement `light-0.png`, `dark-0.png`, and `compact.png` before checking the targeted source changes. Visual hierarchy/theme parity remains intact. Supplied validation now reports 100 passing tests, including profile field synchronization and operation-specific phase distinctions.

| Prior finding | Score | Evidence |
| --- | --- | --- |
| Profile fields inconsistent with actual connection | **Partial** | `applyConnection()` now synchronizes all five options, and profile Connect invokes it. However, editable custom baud support creates a remaining restoration path: `baudField.currentIndex` clamps unknown saved baud to index 0. Saving defaults at 250000 and reopening therefore displays/uses 9600 because no initial `editText` assignment restores saved baud. Initialize editable baud from `s.preferences.baud` and check restoration with 250000. |
| Unperformed phases marked successful | **Resolved** | QML dots now use explicit `completedStages`; actual completion callbacks append phases; batch targets reset them and partial/error batches clear them. Tests distinguish flash, erase-only, verify-only, and partial batches. |
| Readback wording | **Resolved** | Caption explicitly says “Target read-back on writes. CRC-32 verification on the image.” `SimTarget._write` compares programmed target bytes before returning OK. The original review overstated the issue by omitting target-side readback semantics; the clarified wording is accurate for the implemented protocol. |

Focused verdict remains **FIX** solely for restoring a saved nonstandard baud. No redesign or broad recapture is needed. Once that initialization is corrected and checked, the original material findings are closed and this surface can receive **SHIP** for the scoped first release. Existing nonblocking polish notes remain optional.


## Final disposition

**Remaining startup-baud finding: RESOLVED.** `baudField.Component.onCompleted` now restores the saved editable baud text directly, including values outside the preset list. The targeted integration test initializes saved baud 250000 before QML loading, checks restoration, applies profile baud 256000, and checks the exact connection options for every field. Supplied focused validation reports all 9 controller integration tests passing. Inspected the refreshed light firmware capture; the established composition remains intact.

**Final verdict: SHIP** for the scoped first desktop release. All material findings from this finishing review are closed. Earlier FIX dispositions are superseded by this result. Nonblocking polish opportunities remain optional; no further recapture or rebuild is required by this review.
