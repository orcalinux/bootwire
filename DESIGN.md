---
name: BootWire Desktop
description: Clean, spacious native firmware workspace with light and dark themes.
colors:
  light-canvas: "#F3F5F8"
  light-surface: "#FFFFFF"
  light-inset: "#F7F9FC"
  light-ink: "#182A3D"
  light-muted: "#586A7E"
  light-line: "#DCE3EC"
  light-accent: "#185DB8"
  light-accent-fill: "#E9F1FC"
  light-success: "#157657"
  light-warning: "#916013"
  light-error: "#B02F3C"
  dark-canvas: "#101923"
  dark-surface: "#182431"
  dark-inset: "#12202D"
  dark-ink: "#EBF1F8"
  dark-muted: "#A4B4C7"
  dark-line: "#344657"
  dark-accent: "#72B4FF"
  dark-accent-fill: "#24466B"
  dark-success: "#72D6B3"
  dark-warning: "#F3C879"
  dark-error: "#FFA3A3"
  rail: "#142C44"
  rail-text: "#B9CADB"
  rail-selected: "#2B4967"
  rail-hover: "#203D59"
  rail-focus: "#82B9F5"
  rail-dot-selected: "#8FC5FF"
  rail-dot: "#64809C"
  rail-divider: "#34506B"
  rail-caption: "#9DB4CB"
  white: "#FFFFFF"
  dark-primary-text: "#102337"
typography:
  headline:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "27px"
    fontWeight: 600
  section:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "17px"
    fontWeight: 600
  body:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "14px"
    fontWeight: 400
  supporting:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "13px"
    fontWeight: 400
  label:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "13px"
    fontWeight: 600
  secondary:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "12px"
    fontWeight: 400
  metadata:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "11px"
    fontWeight: 400
  caption:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "10px"
    fontWeight: 400
  brand:
    fontFamily: "Segoe UI (Windows), Helvetica Neue (macOS), DejaVu Sans (other platforms)"
    fontSize: "22px"
    fontWeight: 600
  mono:
    fontFamily: "DejaVu Sans Mono"
    fontSize: "12px"
rounded:
  control: "10px"
  navigation: "9px"
  inset: "10px"
  panel: "14px"
spacing:
  step-4: "4px"
  step-6: "6px"
  step-7: "7px"
  step-8: "8px"
  step-9: "9px"
  step-10: "10px"
  step-12: "12px"
  step-14: "14px"
  step-16: "16px"
  step-18: "18px"
  step-20: "20px"
  step-22: "22px"
  step-24: "24px"
  step-26: "26px"
  step-28: "28px"
  step-30: "30px"
  step-34: "34px"
components:
  button-primary-light:
    backgroundColor: "{colors.light-accent}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  button-secondary-light:
    backgroundColor: "{colors.light-surface}"
    textColor: "{colors.light-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  button-destructive-light:
    backgroundColor: "{colors.light-surface}"
    textColor: "{colors.light-error}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  field-light:
    backgroundColor: "{colors.light-surface}"
    textColor: "{colors.light-ink}"
    rounded: "{rounded.control}"
    height: "40px"
    padding: "0px 12px"
  panel-light:
    backgroundColor: "{colors.light-surface}"
    rounded: "{rounded.panel}"
  button-primary-dark:
    backgroundColor: "{colors.dark-accent}"
    textColor: "{colors.dark-primary-text}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  button-secondary-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  button-destructive-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-error}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px"
    height: "40px"
  field-dark:
    backgroundColor: "{colors.dark-surface}"
    textColor: "{colors.dark-ink}"
    rounded: "{rounded.control}"
    height: "40px"
    padding: "0px 12px"
  panel-dark:
    backgroundColor: "{colors.dark-surface}"
    rounded: "{rounded.panel}"
---
# Design System: BootWire Desktop

## Overview

BootWire uses a clean, spacious desktop workspace with light and dark themes. Persistent navy navigation anchors a cool neutral canvas; bordered surfaces organize firmware work and its evidence. Blue identifies actions and active protocol traffic, while semantic color supports explicit outcomes.

This is a native Qt Quick system. Theme.qml is the color authority, and QML components define geometry and behavior. No creative metaphor has been approved or inferred.

**Key Characteristics:**
- Spacious workspace and persistent navigation.
- Shared geometry across light and dark themes.
- Visible connection state, operation stages, and outcomes.
- Monospaced technical evidence beside readable interface text.

## Colors

Frontmatter records each implemented variant separately. `Theme.dark` switches the semantic palette together; shared rail colors remain constant.

### Primary

`accent` is command blue: primary buttons, active stages, focus borders, TX frames, and selection. `accent-fill` is the pale or muted blue hover and drag-target fill. Primary button text is white in light mode and deep navy in dark mode.

### Secondary

Semantic green marks successful operations, completed stages, connected state, and RX frames. Amber marks warnings; red marks errors, invalid traffic, and destructive action text. These are state roles rather than decorative accents.

### Neutral

`canvas` is the work area; `surface` is the connection strip, panels, controls, and status strip; `inset` separates the firmware drop area. `ink`, `muted`, and `line` provide text and structural hierarchy. The navy rail uses its own persistent text, hover, selection, focus, and dot tokens.

## Typography

The application selects Segoe UI on Windows, Helvetica Neue on macOS, and DejaVu Sans elsewhere. These are conditional platform choices, not a CSS fallback stack. Technical values use DejaVu Sans Mono. Sizes are QML logical pixels; font metrics depend on the installed fonts.

The main heading uses `headline`; panel headings generally use `section` (some use 16px). `body` is the BWText default, `supporting` carries descriptions, and `secondary` through `caption` carry increasingly compact evidence. Image names use 18–19px; inspector empty-state titles use 20px. DemiBold maps to weight 600. BWText wraps words and uses plain text; payloads and fingerprints explicitly wrap anywhere. No global line-height or letter-spacing token is set; the shortcut reference alone uses proportional line height 1.6.

## Layout

Default window: 1380 × 900; minimum: 640 × 540. The left rail persists, the connection strip is 78px high, page content scrolls, and the outcome strip remains below it. Work area side margins are 30px. Theme.qml names three spacing roles: `gap` (10px) between sibling controls in a row, `pad` (24px) as the padding of every panel, and `section` (24px) between panels and other major groups. Rows that mix fields, checkboxes, and buttons use 12px. Every row of controls sets its spacing explicitly; the 5px Qt layout default is never relied on. Scrolling pages use PageScroll.qml, which places the scrollbar in the page's own right margin, outside every panel, so it never crosses a field, button or panel edge. Lists inside panels reserve a 16px gutter for theirs. SlimScrollBar hides itself when the content fits. Every workspace ends 20px (12px below 800px window height) above the status strip.

A single 46px client title bar contains the app icon, BootWire title, File/Device/Tools/View/Help menus, theme/preferences actions, and minimize/maximize/close buttons. A styled Qt MenuBar supplies hover switching and arrow-key navigation. The empty title-bar area starts native system dragging, double-click toggles maximize/restore, and 5px edge/8px corner grips start native resizing. An 86px connection strip contains device state, editable port and baud selectors, refresh, and connect/disconnect. At window widths below 1150px, the rail changes from 214px to 184px, the port field narrows from 240px to 156px, and the inline Refresh button is hidden (Refresh remains in Device). Below 1200px the firmware evidence column prefers 230px instead of 290px; it remains alongside the firmware column above the narrow breakpoint. Below 1000px width, the rail becomes a 64px icon rail with hover labels and a shared horizontal centerline for the logo, glyphs, and selected backgrounds, connection status text moves out of the connection toolbar, work margins narrow to 16px, and firmware evidence stacks below the primary workflow. Title-bar branding and theme actions compact without removing the menus. The firmware main column has a 430px minimum, preferred 660px, and expands into available space. At the minimum window size, content scrolls vertically. Below 800px window height, rail buttons use 42px heights and the logo/footer spacing contracts to keep the footer visible. Below 1150px width, protocol and preview metadata use two deliberate lines within the rail. The confirmation dialog width is capped at 500px with 40px clearance on each side.

## Elevation & Depth

Depth comes from tonal layering, one-pixel borders, inset areas, and spacing. Custom QML surfaces have no shadows or gradients; the software renderer used for tests and captures does not support layer effects. Application controls and menus share explicit theme-aware skins. The app draws its unified title bar; move/resize operations are delegated to the operating system. File pickers retain platform conventions.

## Shapes

Panels use the shared 14px panel radius (`Theme.radius`); controls use `Theme.controlRadius` (10px). Controls use the smaller control radius; navigation is slightly rounder, and firmware drop/status areas use the inset radius. Dividers are one logical pixel. Small circular status marks range from 6–8px. Focus increases custom control borders from one to two pixels without adding a shadow.

## Components

### Buttons

`ActionButton.qml` provides primary, secondary, and destructive-text variants. Height is 40px; implicit width is the greater of 82px and label width plus 30px; icon-bearing actions reserve extra room, and compact icon-only actions have a 38px minimum. Labels are centered, 13px DemiBold. Padding is 12px; layouts can expand the control.

Primary fill lightens on hover and darkens on press. Every button scales to 0.975 while pressed, and secondary borders take the accent on hover. Secondary and destructive buttons use surface at rest, accent-fill on hover, and line on press. Destructive changes text to error, not its fill. Keyboard focus uses a two-pixel accent border on secondary actions and contrasting white/deep-navy border on primary actions. Disabled opacity is 0.42. Icon-only glyphs are centered independently of button padding, including compact 34×32px toolbar actions. Keyboard shortcut help uses 76px key columns with a 24px gap to descriptions. Quiet actions have a transparent resting background; hovered actions use accent-fill. Consistent 120ms color transitions provide feedback.

### Inputs / Fields

`Field.qml` uses a 40px implicit height, 12px horizontal padding, surface fill, line border, body-size text, and muted placeholder. Active focus uses a two-pixel accent border. Selection uses accent with surface-colored selected text. Mouse selection is enabled; disabled opacity is 0.5. Error styling is not a field variant. Accessible name comes from placeholder text unless overridden.

### Cards / Containers

`Panel.qml` is a surface-filled, line-bordered rectangle using the shared panel radius. Padding is supplied by each caller rather than embedded in Panel. Firmware drop targets switch inset fill and line border to accent-fill and accent while a drag is present.

### Navigation

Seven persistent rail buttons are 46px high with 8px corners and 14px text. A single selected-fill surface (`navigationSelection`) sits behind the buttons and slides to the active workspace in 220ms; selected items use white DemiBold labels and a brighter glyph, and hover uses the rail hover fill. Focus adds a two-pixel rail-focus border. Navigation is keyboard focusable; Ctrl+1/2/3 select the first three workspaces.

### Operation evidence

The Erase → Write → Verify strip is a connected stepper: 20px markers joined by 2px lines. Completed stages show a success fill with a check and a success connector, the active stage uses accent, and pending stages use a line-colored ring. StageProgress.qml draws a 6px themed track whose accent fill eases to each new value. Chip.qml is the shared status pill (tone as text on a tint of the same tone) used for the image type, activity count, inspector direction, and history result; the result text always accompanies the color. The persistent status strip sits directly above the developer panel and uses a compact rectangular surface, at least 38px height, severity-aware border and text, an activity dot, and a busy-only Stop operation button. ActivitySpinner.qml draws a themed arc with an 850ms rotation while an operation is running. Pending/completed stages come from actual operation callbacks.

### Dropdowns, numeric fields, and checkboxes

SelectField.qml retains Qt ComboBox keyboard/editing behavior with a custom field, outlined 9px corners, semantic leading glyph, rotating chevron, and 11px popup corners. Options use 42px rows, or 58px rows for serial device descriptions. Hover/highlight uses accent-fill; the selected value displays a check. Popups are capped at 320px and use SlimScrollBar in a separate gutter with a 4px gap from option rows. The gutter and scrollbar disappear when all options fit. Manual pyserial URLs and nonstandard baud values remain editable.

NumberField.qml uses themed 40px fields and separate 30px minus/plus targets. CheckField.qml uses a 20px indicator with 6px corners and a drawn check, preserving native keyboard and toggled behavior. Keyboard focus and disabled states are explicit. Mouse activation does not leave a focus outline on buttons, checkboxes, menu headings, or rail navigation. PointerFocus.qml observes taps passively and resets a retained keyboard focus reason after activation, preserving the click, Space activation, and subsequent Tab navigation. Editable fields continue to indicate active editing focus.

### Menus, dialogs, and iconography

ActionMenu.qml uses 284px menus, 11px corners, 6px inner padding, and 39px MenuOption rows with aligned shortcut hints. File, Device, Tools, View, and Help actions route to existing app features. Confirmation, Quick start, and About dialogs use shared surfaces and ActionButton controls. Glyph.qml supplies a custom outline icon set with a consistent 2px stroke on a 24px square grid. Icons repaint on size and theme changes and retain a square aspect ratio. Action icons render at 18px; sidebar icons at 20px. Icon-and-label groups center together, while icon-only buttons center their glyph independently. Theme colors govern normal, selected, hover, and disabled states; platform icon fonts are not used. Micro-interactions are short: 100ms popup fade, 110–120ms feedback, and a 140ms chevron rotation.

The user-approved BootWire logo and all original theme colors are preserved. The SVG mark is shared by the navigation rail and application branding; SVG, PNG, and multi-size ICO files are packaged under bootwire_gui/assets. QGuiApplication and the main QWindow receive the icon; the desktop file ID is bootwire. Native window managers determine where window-title/taskbar icons appear. Window snapping belongs to the operating system, including user-customized tiling shortcuts. Qt advertises normal system-menu/minimize/maximize capabilities; Windows additionally restores native resize/caption styles beneath the custom client frame. No application shortcut implements or overrides tiling.

### Developer panel

The developer panel is the last element at the bottom of the workspace, flush with its lower edge. A compact status strip sits above it. Tabs use semantic outline icons, muted inactive text, and an accent label and underline for the active tab.

A 40px bottom tab strip opens Output, BootWire, or System terminal. Expanded height defaults to 280px and is resizable from its top edge; Ctrl+J or Ctrl+` toggles it. The panel shares existing surface/line/accent tokens. Output uses 10px timestamps and 11px monospaced, selectable messages, with a scrollbar gutter and automatic following. BootWire command input is a 34px Field; destructive commands use the shared confirmation language. The local terminal uses an intentional #111E2C ground, #E7EDF7 default text, 13px DejaVu Sans Mono, ANSI semantic colors, and a cursor block #A8CFFF. It stays dark in either app theme. The shell toolbar uses the existing select/field/button components.

## Do's and Don'ts

### Do:
- Do use Theme.qml semantic colors in both themes.
- Do preserve simulator labels and explicit operation outcomes.
- Do use the existing QML controls and keyboard focus treatments.
- Do keep technical values monospaced and long payloads wrapping.

### Don't:
- Don't substitute a web or mobile navigation pattern for the desktop rail.
- Don't add shadows or gradients. Motion is limited to the documented feedback transitions, the sliding rail selection, and the 160–200ms fade-and-rise when the workspace changes.
- Don't communicate a failure or simulator state through color alone.
- Don't replace the approved logo or palette while extending the control skins.

The title-bar appearance action names its destination: a filled crescent with “Dark” in light mode, and the existing sun with “Light” in dark mode. Tooltips retain full action descriptions.
