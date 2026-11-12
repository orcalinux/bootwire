# BootWire Desktop

MODE: Operate. Native Qt Quick desktop; not a web surface.
THESIS: Firmware work should have a clear destination, an inspectable transaction, and an explicit outcome.
OWN-WORLD: Spacious workspace, light and dark themes (user-confirmed); the existing protocol documentation's navy host, blue commands, teal success vocabulary carries into the product.
STORY: Connect a target, inspect a binary, flash and verify, then inspect evidence. Device profiles, batch jobs, release catalog, diagnostics, and history extend this task.
FIRST VIEWPORT: Persistent connection strip; navigation rail for seven workspaces; primary firmware image and update controls beside the target overview and live session activity; persistent outcome/stop strip. At 1000x720 the work area scrolls and navigation remains visible.
FORM: Code-led QML. 214px navy navigation (184px below 1150px), cool light canvas, white bordered surfaces; dark variant uses the same hierarchy. 27px headings, 14px body, 12px secondary. Rounded controls with explicit focus and semantic state color. Seed reference seed:b3213b0139fb4b7c was explored; user-pinned clean spacious product shell governs implementation.
SIGNATURE: Erase → Write → Verify is represented by a compact stage strip and weighted progress, with frame-level evidence available in Inspector.
QUALITY BAR: Native engineering application with familiar Qt controls, responsive work areas, keyboard access, persistent state, and honest simulator labeling. No image comp; no decorative imagery.
CONFIRMED: User requested all workflows and light/dark spacious style. Single active connection and sequential batches are implementation decisions, not claims of concurrent target support.
REVIEW: Real Qt screenshots in .impeccable/review; captured through the software rendering backend. No HTML/CSS detector is applicable to QML.

REFINEMENT: User requested custom modern control skins and useful top menus while explicitly preserving colors and logo. Shared dropdown/check/numeric/menu/progress controls now replace default styling. The existing mark is packaged and assigned as the application and window icon.

TITLE BAR: User requested menus on the same row as the app icon and window controls, with normal hover switching. The shared 46px header replaces separate native title decoration and application menu row; Qt MenuBar supplies menu navigation, and system move/resize preserve window management.

DEVELOPER PANEL: Existing palette and shell are preserved. A resizable bottom panel provides filtered verbose output, shared-session BootWire commands with destructive-action review, and a real local PTY/ConPTY shell. Tabs, keyboard toggle, history, interruption, and cleanup are part of the working feature, not a visual mock.
