import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    objectName: "bootwireWindow"
    width: 1380
    height: 900
    minimumWidth: 640
    minimumHeight: 540
    visible: true
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
    title: "BootWire — Desktop"
    color: Theme.canvas
    font.family: Qt.platform.os === "windows" ? "Segoe UI" : Qt.platform.os === "osx" ? "Helvetica Neue" : "DejaVu Sans"
    font.pixelSize: 14
    palette.window: Theme.canvas
    palette.windowText: Theme.ink
    palette.base: Theme.surface
    palette.text: Theme.ink
    palette.button: Theme.surface
    palette.buttonText: Theme.ink
    palette.highlight: Theme.accent
    palette.highlightedText: Theme.surface
    property var s: backend ? backend.state : ({busy: false, connected: false, image: {}, device: {}, ports: [], profiles: [], library: [], logs: [], history: [], completedStages: [], preferences: {timeout: 0.5, eraseTimeout: 5, retries: 3}, progress: 0, reply: {}, batchResults: [], theme: "light", detail: ""})
    property int page: 0
    property var selectedProfiles: []
    property string exportKind: "logs"
    property string pendingAction: ""
    property var pendingOptions: ({})
    readonly property bool ready: s.connected && !s.busy
    readonly property bool hasImage: !!s.image.path
    readonly property int traceCount: backend ? backend.traces.count : 0
    readonly property bool compact: height < 800
    readonly property bool narrow: width < 1000
    readonly property int pageMargin: narrow ? 16 : 30
    readonly property var titles: ["Firmware workspace", "Devices & batches", "Firmware library", "Diagnostics & commands", "Protocol inspector", "Job history", "Preferences"]
    readonly property var subtitles: [
        "From binary to board. A clear path through every update.",
        "Save connection profiles and update a group of targets in sequence.",
        "Keep your releases, versions, and fingerprints together.",
        "Test your link, exercise recovery, and talk to your firmware.",
        "Follow every request and response at the frame level.",
        "A local record of connections, diagnostics, and firmware jobs.",
        "Make the workspace and connection defaults your own."
    ]
    Binding { target: Theme; property: "dark"; value: s.theme === "dark" }
    onClosing: function(close) {
        if (s.busy) {
            close.accepted = false
            backend.notify("An operation is running. Stop it and wait for the current command before closing.", "warning")
        }
    }
    function toggleMaximized() {
        if (visibility === Window.Maximized) showNormal(); else showMaximized()
    }
    Connections {
        target: backend ? backend.console : null
        function onConnectionOptionsChanged(options) { window.applyConnection(options) }
    }
    onPageChanged: pageEnter.restart()
    ParallelAnimation {
        id: pageEnter
        NumberAnimation { target: pages; property: "opacity"; from: 0; to: 1; duration: 160; easing.type: Easing.OutCubic }
        NumberAnimation { target: pageShift; property: "y"; from: 10; to: 0; duration: 200; easing.type: Easing.OutCubic }
    }
    Shortcut { sequence: "Ctrl+`"; onActivated: developerPanel.toggle() }
    Shortcut { sequence: "Ctrl+J"; onActivated: developerPanel.toggle() }
    function connectionOptions() {
        return {port: portField.editText, baud: Number(baudField.editText), timeout: Number(timeoutField.text), eraseTimeout: Number(eraseTimeoutField.text), retries: retryField.value}
    }
    function applyConnection(options) {
        portField.editText = options.port
        baudField.editText = String(options.baud || 115200)
        timeoutField.text = String(options.timeout === undefined ? 0.5 : options.timeout)
        eraseTimeoutField.text = String(options.eraseTimeout === undefined ? 5 : options.eraseTimeout)
        retryField.value = options.retries === undefined ? 3 : options.retries
    }
    function imageOptions() {
        return {path: s.image.path || "", sha256: s.image.sha256 || "", simulatorOnly: s.image.simulatorOnly || false, address: addressField.text, run: runAfter.checked}
    }
    function confirmAction(action, options, title, description) {
        pendingAction = action; pendingOptions = options
        confirmDialog.title = title; confirmationText.text = description; confirmDialog.open()
    }
    function exportData(kind) { exportKind = kind; exportDialog.open() }
    function levelColor(level) { return level === "error" ? Theme.error : level === "warning" ? Theme.warning : level === "success" ? Theme.success : Theme.muted }
    Shortcut { sequence: "Ctrl+O"; enabled: !s.busy; onActivated: fileDialog.open() }
    Shortcut { sequence: "Ctrl+1"; onActivated: page = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: page = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: page = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: page = 3 }
    Shortcut { sequence: "Ctrl+5"; onActivated: page = 4 }
    Shortcut { sequence: "Ctrl+6"; onActivated: page = 5 }
    FileDialog {
        id: fileDialog
        title: "Choose a firmware image"
        nameFilters: ["Binary firmware (*.bin)", "All files (*)"]
        onAccepted: backend.inspectUrl(selectedFile.toString())
    }
    FileDialog {
        id: exportDialog
        title: "Export " + exportKind
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON files (*.json)"]
        onAccepted: backend.export(selectedFile.toString(), exportKind)
    }
    Dialog {
        id: confirmDialog
        objectName: "confirmDialog"
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 500)
        modal: true
        padding: 24
        header: BWText { text: confirmDialog.title; font.pixelSize: 20; font.weight: Font.DemiBold; padding: 24; bottomPadding: 8 }
        footer: RowLayout {
            spacing: 10
            Item { Layout.fillWidth: true }
            ActionButton { text: "Cancel"; Layout.bottomMargin: 20; onClicked: confirmDialog.reject() }
            ActionButton { text: pendingAction === "erase" ? "Erase application" : pendingAction === "batch" ? "Start batch" : "Continue"; primary: true; Layout.rightMargin: 24; Layout.bottomMargin: 20; onClicked: confirmDialog.accept() }
        }
        background: Panel { }
        contentItem: BWText { id: confirmationText; width: confirmDialog.availableWidth }
        onAccepted: backend.perform(pendingAction, pendingOptions)
    }

    Dialog {
        id: quickStartDialog; objectName: "quickStartDialog"
        anchors.centerIn: parent; width: 500; modal: true; padding: 24
        background: Panel { }
        contentItem: ColumnLayout {
            spacing: 16
            BWText { text: "Your first update"; font.pixelSize: 22; font.weight: Font.DemiBold }
            BWText { text: "Connect a board running the BootWire bootloader, or choose sim to explore without hardware."; Layout.fillWidth: true }
            BWText { text: "Choose a .bin firmware image in Firmware. Flash firmware erases the required blocks, writes your image, and checks its CRC-32."; Layout.fillWidth: true; color: Theme.muted }
            BWText { text: "For a trial run, connect to sim and choose Try a demo image. Inspect every exchange in Inspector, then test retries in Diagnostics."; Layout.fillWidth: true; color: Theme.muted }
            ActionButton { text: "Open firmware workspace"; primary: true; Layout.fillWidth: true; onClicked: { page = 0; quickStartDialog.close() } }
            ActionButton { text: "Close"; Layout.alignment: Qt.AlignRight; onClicked: quickStartDialog.close() }
        }
    }
    Dialog {
        id: aboutDialog; objectName: "aboutDialog"
        anchors.centerIn: parent; width: 440; modal: true; padding: 28
        background: Panel { }
        contentItem: ColumnLayout {
            spacing: 16
            Image { source: "../assets/bootwire.svg"; Layout.preferredWidth: 54; Layout.preferredHeight: 54; sourceSize.width: 108; sourceSize.height: 108 }
            BWText { text: "BootWire Desktop"; font.pixelSize: 24; font.weight: Font.DemiBold }
            BWText { text: "Desktop preview · Protocol v0.2"; color: Theme.muted }
            BWText { text: "Firmware updates, diagnostics, and an inspectable serial connection. Built with Python and Qt Quick."; Layout.fillWidth: true }
            BWText { text: "Settings, firmware references, and history stay on this computer. Firmware is not uploaded."; color: Theme.muted; Layout.fillWidth: true }
            ActionButton { text: "Close"; Layout.alignment: Qt.AlignRight; onClicked: aboutDialog.close() }
        }
    }
    Shortcut { sequence: "Ctrl+Q"; onActivated: window.close() }
    Shortcut { sequence: "Ctrl+,"; onActivated: page = 6 }

    header: Rectangle {
        id: titleBar
        objectName: "titleBar"
        height: 46
        color: Theme.surface
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            onPressed: window.startSystemMove()
            onDoubleClicked: window.toggleMaximized()
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12; anchors.rightMargin: 6
            spacing: 4
            Image { objectName: "titleBarIcon"; source: "../assets/bootwire.svg"; Layout.preferredWidth: 25; Layout.preferredHeight: 25; sourceSize.width: 50; sourceSize.height: 50 }
            BWText { visible: !window.narrow; text: "BootWire"; font.pixelSize: 13; font.weight: Font.DemiBold; Layout.leftMargin: 5; Layout.rightMargin: 14 }
            MenuBar {
                id: appMenuBar
                objectName: "applicationMenuBar"
                // The menus give way first, so the window controls always stay inside a
                // narrow window whatever the platform font width.
                Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.maximumWidth: implicitWidth
                clip: true
                implicitHeight: 36
                spacing: 2
                padding: 2
                topPadding: 2
                bottomPadding: 2
                leftPadding: 2
                rightPadding: 2
                delegate: TitleMenuItem { }
                background: Item { }
ActionMenu {
                        title: "&File"
                            id: fileMenu; objectName: "fileMenu"
                            MenuOption { objectName: "openImageMenuItem"; text: "Open firmware image…"; glyph: "folder"; hint: "Ctrl+O"; enabled: !s.busy; onTriggered: fileDialog.open() }
                            MenuOption { text: "Firmware library"; hint: "Ctrl+3"; onTriggered: page = 2 }
                            MenuRule { }
                            MenuOption { objectName: "exportActivityMenuItem"; text: "Export session activity…"; enabled: s.logs.length > 0; onTriggered: exportData("logs") }
                            MenuOption { text: "Export job history…"; enabled: s.history.length > 0; onTriggered: exportData("history") }
                            MenuRule { }
                            MenuOption { text: "Quit BootWire"; hint: "Ctrl+Q"; onTriggered: window.close() }
                        }
ActionMenu {
                        title: "&Device"
                            id: deviceMenu; objectName: "deviceMenu"
                            MenuOption { text: s.connected ? "Disconnect device" : "Connect device"; glyph: "port"; enabled: !s.busy; onTriggered: backend.perform(s.connected ? "disconnect" : "connect", connectionOptions()) }
                            MenuOption { objectName: "refreshPortsMenuItem"; text: "Refresh serial ports"; glyph: "refresh"; enabled: !s.busy; onTriggered: backend.refreshPorts() }
                            MenuOption { text: "Test connection"; enabled: ready; onTriggered: backend.perform("ping", {payload: "BootWire", count: 5}) }
                            MenuRule { }
                            MenuOption { text: "Device profiles & batches"; hint: "Ctrl+2"; onTriggered: page = 1 }
                            MenuOption { text: "Reset simulator"; enabled: !s.busy && !!s.device.simulated; onTriggered: backend.perform("reset_simulator", {}) }
                        }
ActionMenu {
                        title: "&Tools"
                            id: toolsMenu; objectName: "toolsMenu"
                            MenuOption { objectName: "openDiagnosticsMenuItem"; text: "Diagnostics & commands"; hint: "Ctrl+4"; onTriggered: page = 3 }
                            MenuOption { objectName: "openInspectorMenuItem"; text: "Protocol inspector"; hint: "Ctrl+5"; onTriggered: page = 4 }
                            MenuOption { text: "Job history"; hint: "Ctrl+6"; onTriggered: page = 5 }
                            MenuOption { text: "Export protocol capture…"; enabled: traceCount > 0; onTriggered: exportData("traces") }
                            MenuRule { }
                            MenuOption { text: "Preferences"; glyph: "settings"; hint: "Ctrl+,"; onTriggered: page = 6 }
                        }
ActionMenu {
                        title: "&View"
                            id: viewMenu; objectName: "viewMenu"
                            MenuOption { text: "Firmware workspace"; hint: "Ctrl+1"; onTriggered: page = 0 }
                            MenuOption { text: "Toggle developer panel"; hint: "Ctrl+J"; onTriggered: developerPanel.toggle() }
                            MenuOption { text: "Verbose output"; onTriggered: developerPanel.open(0) }
                            MenuOption { text: "BootWire console"; onTriggered: developerPanel.open(1) }
                            MenuOption { text: "System terminal"; onTriggered: developerPanel.open(2) }
                            MenuRule { }
                            MenuOption { text: "Light appearance"; glyph: s.theme === "light" ? "check" : "sun"; onTriggered: backend.setTheme("light") }
                            MenuOption { text: "Dark appearance"; glyph: s.theme === "dark" ? "check" : "moon"; onTriggered: backend.setTheme("dark") }
                        }
ActionMenu {
                        title: "&Help"
                            id: helpMenu; objectName: "helpMenu"
                            MenuOption { objectName: "quickStartMenuItem"; text: "Quick start"; onTriggered: quickStartDialog.open() }
                            MenuOption { text: "Keyboard shortcuts"; onTriggered: page = 6 }
                            MenuRule { }
                            MenuOption { objectName: "aboutMenuItem"; text: "About BootWire"; onTriggered: aboutDialog.open() }
                        }
            }
            Item { Layout.fillWidth: true }
            BWText { text: s.busy ? "Operation in progress" : "Workspace ready"; color: Theme.muted; font.pixelSize: 11; visible: window.width >= 1150; Layout.rightMargin: 10 }
            ActionButton { objectName: "themeButton"; text: window.narrow ? "" : s.theme === "dark" ? "Light" : "Dark"; glyph: s.theme === "dark" ? "sun" : "moon"; quiet: true; tooltip: s.theme === "dark" ? "Use light appearance" : "Use dark appearance"; implicitWidth: window.narrow ? 34 : 86; implicitHeight: 32; onClicked: backend.setTheme(s.theme === "dark" ? "light" : "dark") }
            ActionButton { objectName: "preferencesButton"; visible: !window.narrow; text: ""; glyph: "settings"; quiet: true; tooltip: "Preferences"; implicitWidth: 34; implicitHeight: 32; onClicked: page = 6 }
            Rectangle { width: 1; height: 18; color: Theme.line; Layout.leftMargin: 8; Layout.rightMargin: 6 }
            WindowButton { objectName: "minimizeWindowButton"; symbol: "minimize"; onClicked: window.showMinimized() }
            WindowButton { objectName: "maximizeWindowButton"; symbol: window.visibility === Window.Maximized ? "restore" : "maximize"; onClicked: window.toggleMaximized() }
            WindowButton { objectName: "closeWindowButton"; symbol: "close"; onClicked: window.close() }
        }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
    }
    WindowResizeEdges { parent: Overlay.overlay; anchors.fill: parent; z: 1000; targetWindow: window }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            objectName: "navigationRail"
            Layout.fillHeight: true
            Layout.preferredWidth: window.narrow ? 64 : window.width < 1150 ? 184 : 214
            color: Theme.rail
            Rectangle {
                objectName: "navigationSelection"
                readonly property Item target: navigationItems.count > 0 ? navigationItems.itemAt(window.page) : null
                visible: target !== null
                x: target ? railColumn.x + target.x : 0
                y: target ? railColumn.y + target.y : 0
                width: target ? target.width : 0
                height: target ? target.height : 0
                radius: 9
                color: "#2B4967"
                Behavior on y { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
            }
            ColumnLayout {
                id: railColumn
                anchors.fill: parent
                anchors.margins: window.narrow ? 10 : 18
                spacing: 8
                RowLayout {
                    Layout.alignment: window.narrow ? Qt.AlignHCenter : Qt.AlignLeft
                    Layout.topMargin: 12
                    Layout.bottomMargin: window.height < 800 ? 18 : 34
                    spacing: 10
                    Image {
                        objectName: "navigationLogo"
                        source: "../assets/bootwire-mark.svg"
                        Layout.preferredWidth: 28; Layout.preferredHeight: 30
                        sourceSize.width: 56; sourceSize.height: 60
                    }
                    Label { visible: !window.narrow; text: "BootWire"; color: "#FFFFFF"; font.pixelSize: 22; font.weight: Font.DemiBold }
                }
                Repeater {
                    id: navigationItems
                    model: ["Firmware", "Devices", "Library", "Diagnostics", "Inspector", "History", "Preferences"]
                    delegate: Button {
                        required property int index
                        required property string modelData
                        objectName: "navigationButton" + index
                        Layout.fillWidth: true
                        implicitHeight: window.height < 800 ? 42 : 46
                        hoverEnabled: true
                        PointerFocus { control: parent }
                        onClicked: window.page = index
                        Accessible.name: modelData
                        ToolTip.visible: window.narrow && hovered
                        ToolTip.text: modelData
                        ToolTip.delay: 500
                        padding: window.narrow ? 12 : 6
                        background: Rectangle {
                            radius: 9
                            color: window.page !== index && parent.hovered ? "#203D59" : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            border.width: parent.visualFocus ? 2 : 0
                            border.color: "#82B9F5"
                        }
                        contentItem: Item {
                            implicitWidth: navigationContent.implicitWidth
                            implicitHeight: navigationContent.implicitHeight
                            RowLayout {
                                id: navigationContent
                                anchors.centerIn: parent
                                width: window.narrow ? implicitWidth : parent.width
                                spacing: 12
                                Glyph { objectName: "navigationGlyph"; name: ["chip", "devices", "library", "activity", "search", "history", "settings"][index]; ink: window.page === index ? "#8FC5FF" : Theme.railText; Layout.preferredWidth: 20; Layout.preferredHeight: 20; Layout.alignment: Qt.AlignVCenter }
                                Label { visible: !window.narrow; Layout.fillWidth: true; text: modelData; color: window.page === index ? "#FFFFFF" : Theme.railText; font.pixelSize: 14; font.weight: window.page === index ? Font.DemiBold : Font.Normal }
                            }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle { visible: !window.narrow; Layout.fillWidth: true; height: 1; color: "#34506B" }
                Label { visible: !window.narrow; Layout.topMargin: 14; text: "Built for the next update."; color: Theme.railText; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label {
                    objectName: "sidebarVersion"
                    visible: !window.narrow
                    text: window.width < 1150 ? "Protocol v0.2\nDesktop preview" : "Protocol v0.2  ·  Desktop preview"
                    color: "#9DB4CB"; font.pixelSize: 10
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    wrapMode: Text.WordWrap
                    Layout.bottomMargin: window.height < 800 ? 0 : 12
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                height: 86
                color: Theme.surface
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: window.narrow ? 16 : 28; anchors.rightMargin: window.narrow ? 16 : 28
                    spacing: 12
                    Rectangle { visible: !window.narrow; width: 8; height: 8; radius: 4; color: s.connected ? Theme.success : Theme.muted }
                    ColumnLayout {
                        visible: !window.narrow
                        spacing: 4; Layout.preferredWidth: window.width < 1150 ? 144 : 190
                        BWText { text: s.connected ? (s.device.simulated ? "Simulator connected" : "Device connected") : "Connect your device"; font.weight: Font.DemiBold; font.pixelSize: 13; Layout.fillWidth: true }
                        BWText { text: s.connected ? "BootWire v" + s.device.protocol_version + " · " + s.device.sizeLabel + " application" : "Serial connection or built-in simulator"; color: Theme.muted; font.pixelSize: 10; Layout.fillWidth: true }
                    }
                    Item { Layout.fillWidth: true }
                    SelectField {
                        id: portField
                        objectName: "portField"
                        Layout.fillWidth: window.narrow
                        Layout.minimumWidth: 120
                        Layout.preferredWidth: window.width < 1150 ? 156 : 240
                        implicitHeight: 40
                        model: s.ports
                        textRole: "port"
                        detailRole: "label"
                        glyph: "port"
                        editable: true
                        enabled: !s.connected && !s.busy
                        Component.onCompleted: editText = s.preferences.port || "sim"
                        Accessible.name: "Serial port or pyserial URL"
                    }
                    SelectField {
                        id: baudField
                        objectName: "baudField"
                        glyph: "speed"
                        editable: true
                        Layout.preferredWidth: 144
                        implicitHeight: 40
                        model: ["9600", "57600", "115200", "230400", "460800", "921600"]
                        currentIndex: Math.max(0, model.indexOf(String(s.preferences.baud)))
                        Component.onCompleted: editText = String(s.preferences.baud || 115200)
                        enabled: !s.connected && !s.busy
                        Accessible.name: "Baud rate"
                    }
                    ActionButton { objectName: "refreshPortsButton"; text: ""; glyph: "refresh"; tooltip: "Refresh serial ports"; implicitWidth: 40; enabled: !s.busy; onClicked: backend.refreshPorts(); visible: window.width >= 1150 }
                    ActionButton {
                        objectName: "connectButton"
                        text: s.busy && s.stage === "connect" ? "Connecting…" : s.connected ? "Disconnect" : "Connect"
                        glyph: s.connected ? "port" : "arrow"
                        primary: !s.connected
                        enabled: !s.busy
                        onClicked: backend.perform(s.connected ? "disconnect" : "connect", connectionOptions())
                    }
                }
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: window.narrow ? 16 : 30; Layout.rightMargin: window.narrow ? 16 : 30; Layout.topMargin: compact ? 16 : 28; Layout.bottomMargin: compact ? 14 : 24
                spacing: 16
                ColumnLayout {
                    spacing: 6
                    Layout.fillWidth: true
                    BWText { Layout.fillWidth: true; text: titles[page]; font.pixelSize: window.narrow ? 20 : compact ? 22 : 27; font.weight: Font.DemiBold; font.letterSpacing: -0.4 }
                    BWText { text: subtitles[page]; color: Theme.muted; font.pixelSize: 13; Layout.fillWidth: true; visible: !compact && !window.narrow }
                }
                Item { Layout.fillWidth: true }
                ActionButton { text: "Open image"; glyph: "folder"; enabled: !s.busy; visible: page === 0; onClicked: fileDialog.open() }
            }
            StackLayout {
                id: pages
                currentIndex: page
                transform: Translate { id: pageShift }
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.leftMargin: window.pageMargin
                Layout.bottomMargin: window.compact ? 12 : 20

                // Firmware evidence stacks when the desktop tiles the window narrowly.
                PageScroll {
                    gutter: window.pageMargin
                    GridLayout {
                        objectName: "firmwareGrid"
                        columns: window.narrow ? 1 : 2
                        width: parent.width
                        columnSpacing: Theme.section; rowSpacing: Theme.section
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.preferredWidth: 660; Layout.minimumWidth: window.narrow ? 0 : 430; Layout.alignment: Qt.AlignTop
                            spacing: Theme.section
                            Panel {
                                Layout.fillWidth: true
                                implicitHeight: firmwareContents.implicitHeight + 2 * Theme.pad
                                ColumnLayout {
                                    id: firmwareContents
                                    anchors.fill: parent; anchors.margins: Theme.pad
                                    spacing: 16
                                    RowLayout {
                                        BWText { text: "Firmware image"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                        Item { Layout.fillWidth: true }
                                        Chip { text: "RAW BINARY" }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; implicitHeight: hasImage ? 92 : 188
                                        radius: Theme.controlRadius
                                        color: dropArea.containsDrag ? Theme.accentFill : Theme.inset
                                        border.color: dropArea.containsDrag ? Theme.accent : Theme.line
                                        DropArea {
                                            id: dropArea
                                            anchors.fill: parent
                                            onDropped: function(drop) { if (!s.busy && drop.hasUrls) backend.inspectUrl(drop.urls[0]) }
                                        }
                                        ColumnLayout {
                                            visible: !hasImage
                                            anchors.fill: parent; anchors.margins: 20
                                            spacing: 8
                                            BWText { text: "Your next firmware starts here"; font.pixelSize: 19; font.weight: Font.DemiBold; Layout.fillWidth: true }
                                            BWText { text: "Drop a .bin file here, or browse your computer."; color: Theme.muted; font.pixelSize: 13; Layout.fillWidth: true }
                                            Item { Layout.fillHeight: true }
                                            RowLayout {
                                                spacing: Theme.gap
                                                ActionButton { text: "Browse files"; enabled: !s.busy; onClicked: fileDialog.open() }
                                                ActionButton { text: "Try a demo image"; enabled: !s.busy; onClicked: backend.perform("demo", {}) }
                                                Item { Layout.fillWidth: true }
                                                BWText { text: "Ctrl+O"; color: Theme.muted; font.pixelSize: 11 }
                                            }
                                        }
                                        RowLayout {
                                            visible: hasImage
                                            anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20
                                            spacing: 16
                                            ColumnLayout {
                                                Layout.fillWidth: true; spacing: 6
                                                BWText { text: s.image.name || ""; font.pixelSize: 18; font.weight: Font.DemiBold; elide: Text.ElideMiddle; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                                                BWText { text: (s.image.sizeLabel || "") + (s.image.simulatorOnly ? " · Simulator demonstration image" : " · Raw binary image"); color: Theme.muted; font.pixelSize: 13; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                                            }
                                            ActionButton { text: "Change image"; tooltip: "Choose another image (Ctrl+O)"; enabled: !s.busy; onClicked: fileDialog.open() }
                                        }
                                    }
                                    RowLayout {
                                        visible: hasImage
                                        spacing: 32
                                        ColumnLayout {
                                            spacing: 4
                                            BWText { text: "FILE CRC-32"; font.pixelSize: 10; color: Theme.muted }
                                            BWText { text: s.image.crc32 || "—"; font.family: Theme.mono; font.pixelSize: 13 }
                                        }
                                        ColumnLayout {
                                            spacing: 4
                                            BWText { text: "INITIAL STACK"; font.pixelSize: 10; color: Theme.muted }
                                            BWText { text: s.image.stackPointer || "—"; font.family: Theme.mono; font.pixelSize: 13 }
                                        }
                                        ColumnLayout {
                                            spacing: 4
                                            BWText { text: "RESET VECTOR"; font.pixelSize: 10; color: Theme.muted }
                                            BWText { text: s.image.resetVector || "—"; font.family: Theme.mono; font.pixelSize: 13 }
                                        }
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                                    BWText { text: "Update options"; font.weight: Font.DemiBold; Layout.topMargin: 4 }
                                    RowLayout {
                                        spacing: 12
                                        BWText { text: "Load address"; color: Theme.muted; Layout.preferredWidth: 105 }
                                        Field { id: addressField; objectName: "addressField"; placeholderText: s.device.startLabel ? s.device.startLabel + " (device default)" : "Use device default"; Layout.fillWidth: true; enabled: !s.busy; font.family: Theme.mono; font.pixelSize: 12 }
                                    }
                                    CheckField { id: runAfter; text: "Start the application after verification"; checked: false; enabled: !s.busy }
                                    BWText { text: "Flash erases the blocks touched by this image, writes it, then verifies the padded image with CRC-32."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    RowLayout {
                                        Layout.topMargin: 4
                                        spacing: Theme.gap
                                        ActionButton { objectName: "flashButton"; text: s.busy && s.stage !== "inspect" ? "Working…" : "Flash firmware"; primary: true; Layout.fillWidth: true; enabled: ready && hasImage; onClicked: confirmAction("flash", imageOptions(), "Flash this firmware?", "The application blocks touched by " + s.image.name + " will be erased and rewritten on " + s.device.port + ". Verification runs before the application can start.") }
                                        ActionButton { text: "Verify only"; enabled: ready && hasImage; onClicked: backend.perform("verify", imageOptions()) }
                                    }
                                    RowLayout {
                                        spacing: Theme.gap
                                        ActionButton { text: "Write only"; enabled: ready && hasImage; onClicked: confirmAction("write", imageOptions(), "Write into erased flash?", "This writes the selected image and verifies it. The target region must already be erased.") }
                                        ActionButton { text: "Erase region"; destructive: true; enabled: ready; onClicked: confirmAction("erase", {address: addressField.text}, "Erase application flash?", "This erases from the selected load address to the end of the application region. The current application will be removed.") }
                                        ActionButton { text: "Run app"; enabled: ready; onClicked: backend.perform("run", {}) }
                                    }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true
                                implicitHeight: stageContents.implicitHeight + 2 * Theme.pad
                                ColumnLayout {
                                    id: stageContents
                                    anchors.fill: parent; anchors.margins: Theme.pad; spacing: 16
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 12
                                        Repeater {
                                            model: ["Erase", "Write", "Verify"]
                                            delegate: RowLayout {
                                                required property int index
                                                required property string modelData
                                                readonly property bool done: s.completedStages.indexOf(modelData.toLowerCase()) >= 0
                                                readonly property bool active: s.stage === modelData.toLowerCase()
                                                Layout.fillWidth: index < 2
                                                spacing: 10
                                                Rectangle {
                                                    Layout.preferredWidth: 20; Layout.preferredHeight: 20; radius: 10
                                                    color: done ? Theme.success : active ? Theme.accent : "transparent"
                                                    border.width: done || active ? 0 : 2
                                                    border.color: Theme.line
                                                    Behavior on color { ColorAnimation { duration: 160 } }
                                                    Glyph { anchors.centerIn: parent; width: 12; height: 12; name: "check"; visible: done; ink: Theme.dark ? "#102337" : "#FFFFFF" }
                                                }
                                                BWText { text: modelData; color: active ? Theme.accent : done ? Theme.ink : Theme.muted; font.pixelSize: 12; font.weight: active || done ? Font.DemiBold : Font.Normal; wrapMode: Text.NoWrap }
                                                Rectangle { visible: index < 2; Layout.fillWidth: true; Layout.minimumWidth: 12; height: 2; radius: 1; color: done ? Theme.success : Theme.line; Behavior on color { ColorAnimation { duration: 160 } } }
                                            }
                                        }
                                    }
                                    StageProgress { Layout.fillWidth: true; value: s.progress }
                                    BWText { text: s.busy ? s.detail : "Target read-back on writes. CRC-32 verification on the image."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: window.narrow
                            Layout.preferredWidth: window.width < 1200 ? 230 : 290
                            Layout.maximumWidth: window.narrow ? 10000 : 290
                            Layout.minimumWidth: 230
                            Layout.alignment: Qt.AlignTop
                            spacing: Theme.section
                            Panel {
                                Layout.fillWidth: true; implicitHeight: targetContents.implicitHeight + 2 * Theme.pad
                                ColumnLayout {
                                    id: targetContents
                                    anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                    RowLayout {
                                        BWText { text: "Target overview"; font.weight: Font.DemiBold; font.pixelSize: 17 }
                                        Item { Layout.fillWidth: true }
                                        Rectangle { width: 7; height: 7; radius: 4; color: s.connected ? Theme.success : Theme.muted }
                                    }
                                    BWText { text: s.connected ? (s.device.simulated ? "Simulated Cortex-M" : "BootWire target") : "Waiting for your device"; font.weight: Font.DemiBold; font.pixelSize: 14; Layout.fillWidth: true }
                                    BWText { text: s.connected ? (s.device.simulated ? "Virtual flash, real protocol. No board required." : s.device.port) : "Choose a port above and connect. Use sim to explore without hardware."; font.pixelSize: 12; color: Theme.muted; Layout.fillWidth: true }
                                    Repeater {
                                        model: [
                                            ["Device ID", s.device.idLabel || "—"], ["Bootloader", s.device.version || "—"],
                                            ["Application", s.device.sizeLabel || "—"], ["Start address", s.device.startLabel || "—"],
                                            ["Erase block", s.device.erase_block ? s.device.erase_block + " bytes" : "—"],
                                            ["Write alignment", s.device.write_align ? s.device.write_align + " bytes" : "—"],
                                            ["Max payload", s.device.max_payload ? s.device.max_payload + " bytes" : "—"]]
                                        delegate: RowLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            spacing: 12
                                            BWText { text: modelData[0]; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                            BWText { text: modelData[1]; font.pixelSize: 12; font.family: Theme.mono; wrapMode: Text.NoWrap }
                                        }
                                    }
                                    Rectangle { Layout.fillWidth: true; Layout.topMargin: 4; height: 1; color: Theme.line }
                                    ActionButton { text: "Test connection"; Layout.topMargin: 4; enabled: ready; Layout.fillWidth: true; onClicked: backend.perform("ping", {payload: "BootWire", count: 5}) }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true; implicitHeight: 300
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: Theme.pad
                                    spacing: 14
                                    RowLayout {
                                        BWText { text: "Session activity"; font.weight: Font.DemiBold; font.pixelSize: 17 }
                                        Item { Layout.fillWidth: true }
                                        Chip { text: String(s.logs.length) }
                                    }
                                    ListView {
                                        id: miniLog
                                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 12
                                        model: s.logs
                                        onCountChanged: positionViewAtEnd()
                                        delegate: ColumnLayout {
                                            required property var modelData
                                            width: miniLog.width - 16
                                            spacing: 4
                                            BWText { text: modelData.time; font.pixelSize: 10; color: Theme.muted; font.family: Theme.mono }
                                            BWText { text: modelData.message; color: levelColor(modelData.level); font.pixelSize: 11; Layout.fillWidth: true }
                                        }
                                        BWText { visible: miniLog.count === 0; width: parent.width; text: "Connections, retries, and results appear here as you work."; color: Theme.muted; font.pixelSize: 12 }
                                        ScrollBar.vertical: SlimScrollBar { }
                                    }
                                    ActionButton { text: "Export activity"; Layout.fillWidth: true; enabled: s.logs.length > 0; onClicked: exportData("logs") }
                                }
                            }
                        }
                    }
                }

                // Devices and batch operations.
                PageScroll {
                    gutter: window.pageMargin
                    ColumnLayout {
                        width: parent.width; spacing: Theme.section
                        Panel {
                            Layout.fillWidth: true; implicitHeight: profileSave.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: profileSave
                                anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Save the connection above as a device profile"; font.weight: Font.DemiBold; font.pixelSize: 17; Layout.fillWidth: true }
                                RowLayout {
                                    spacing: Theme.gap
                                    Field { id: profileName; placeholderText: "Profile name, e.g. Development board"; Layout.fillWidth: true }
                                    ActionButton { text: "Save profile"; primary: true; enabled: !s.busy; onClicked: backend.saveProfile(profileName.text, connectionOptions()) }
                                }
                                BWText { text: "Profiles store port, baud rate, timeouts, and retries. Saving an existing name updates that profile."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                            }
                        }
                        RowLayout {
                            spacing: 16
                            BWText { text: "Your devices"; font.weight: Font.DemiBold; font.pixelSize: 17 }
                            Item { Layout.fillWidth: true }
                            ActionButton { text: "Export profiles"; enabled: s.profiles.length > 0; onClicked: exportData("profiles") }
                        }
                        BWText { visible: s.profiles.length === 0; text: "Save a profile to build your device list. You can start with the built-in simulator."; color: Theme.muted; Layout.fillWidth: true }
                        Repeater {
                            model: s.profiles
                            delegate: Panel {
                                required property var modelData
                                Layout.fillWidth: true; implicitHeight: 88
                                RowLayout {
                                    anchors.fill: parent; anchors.leftMargin: Theme.pad - 4; anchors.rightMargin: Theme.pad; spacing: 12
                                    CheckField {
                                        Accessible.name: "Select " + modelData.name + " for batch"
                                        enabled: !s.busy
                                        checked: selectedProfiles.indexOf(modelData.name) >= 0
                                        onToggled: { let names = selectedProfiles.slice(); if (checked) names.push(modelData.name); else names = names.filter(n => n !== modelData.name); selectedProfiles = names }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 6
                                        BWText { text: modelData.name; font.weight: Font.DemiBold; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                                        BWText { text: modelData.port + " · " + modelData.baud + " baud"; color: Theme.muted; font.pixelSize: 12; elide: Text.ElideMiddle; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                                    }
                                    ActionButton { text: "Connect"; enabled: !s.busy; onClicked: { applyConnection(modelData); backend.perform("connect", modelData) } }
                                    ActionButton { text: "Remove"; enabled: !s.busy; onClicked: { selectedProfiles = selectedProfiles.filter(n => n !== modelData.name); backend.removeProfile(modelData.name) } }
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true; implicitHeight: batchBox.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: batchBox; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Batch update"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                BWText { text: "Each selected target connects, erases, writes, and verifies in sequence. A failed target is recorded and the batch continues. Stopping leaves the current image incomplete."; color: Theme.muted; font.pixelSize: 13; Layout.fillWidth: true }
                                BWText { text: hasImage ? "Image: " + s.image.name + " · " + selectedProfiles.length + " profiles selected" : "Choose an image in Firmware before starting a batch."; Layout.fillWidth: true }
                                ActionButton {
                                    Layout.topMargin: 4
                                    text: "Flash selected devices"; primary: true; enabled: !s.busy && hasImage && selectedProfiles.length > 0
                                    onClicked: {
                                        let options = imageOptions(); options.profiles = s.profiles.filter(p => selectedProfiles.indexOf(p.name) >= 0)
                                        confirmAction("batch", options, "Start batch update?", "The selected image will replace application flash on " + options.profiles.length + " targets. The current connection will close first. Each profile is processed in sequence.")
                                    }
                                }
                                Repeater {
                                    model: s.batchResults
                                    delegate: BWText { required property var modelData; text: modelData.name + " · " + modelData.message; color: modelData.success ? Theme.success : Theme.error; Layout.fillWidth: true; font.pixelSize: 12 }
                                }
                            }
                        }
                    }
                }

                // Local release library.
                PageScroll {
                    gutter: window.pageMargin
                    ColumnLayout {
                        width: parent.width; spacing: Theme.section
                        Panel {
                            Layout.fillWidth: true; implicitHeight: libraryAdd.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: libraryAdd; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Register a release"; font.weight: Font.DemiBold; font.pixelSize: 17 }
                                BWText { text: hasImage ? "Selected: " + s.image.name : "Choose a raw binary to add to your local firmware catalog."; color: Theme.muted; Layout.fillWidth: true }
                                RowLayout {
                                    spacing: Theme.gap
                                    Field { id: versionField; placeholderText: "Version, e.g. 1.0.0"; Layout.preferredWidth: 180; enabled: !s.busy }
                                    Field { id: releaseNotes; placeholderText: "Release notes or build label"; Layout.fillWidth: true; enabled: !s.busy }
                                }
                                RowLayout {
                                    spacing: Theme.gap
                                    ActionButton { text: "Choose image"; enabled: !s.busy; onClicked: fileDialog.open() }
                                    ActionButton { text: "Add release"; primary: true; enabled: !s.busy && hasImage; onClicked: backend.addRelease(versionField.text, releaseNotes.text) }
                                    Item { Layout.fillWidth: true }
                                    ActionButton { text: "Export catalog"; enabled: s.library.length > 0; onClicked: exportData("library") }
                                }
                                BWText { text: "The catalog references files on this computer; it does not copy or upload firmware. SHA-256 detects changes before a release is loaded."; font.pixelSize: 12; color: Theme.muted; Layout.fillWidth: true }
                            }
                        }
                        Field { id: librarySearch; placeholderText: "Search filename, version, or notes"; Layout.fillWidth: true }
                        BWText { visible: s.library.length === 0; text: "Your first release belongs here. Add a binary above to keep its version and fingerprints on hand."; color: Theme.muted; Layout.fillWidth: true }
                        Repeater {
                            model: s.library
                            delegate: Panel {
                                required property var modelData
                                visible: (modelData.name + " " + modelData.version + " " + modelData.notes).toLowerCase().indexOf(librarySearch.text.toLowerCase()) >= 0
                                Layout.fillWidth: true; implicitHeight: releaseRow.implicitHeight + 2 * Theme.pad
                                ColumnLayout {
                                    id: releaseRow; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 10
                                    RowLayout {
                                        spacing: Theme.gap
                                        BWText { text: modelData.name + "  ·  " + modelData.version; font.weight: Font.DemiBold; font.pixelSize: 16; Layout.fillWidth: true; elide: Text.ElideMiddle; wrapMode: Text.NoWrap }
                                        ActionButton { text: "Use image"; primary: true; enabled: !s.busy; onClicked: { backend.loadRelease(modelData.path, modelData.sha256, modelData.simulatorOnly || false); page = 0 } }
                                        ActionButton { text: "Remove"; enabled: !s.busy; onClicked: backend.removeRelease(modelData.sha256) }
                                    }
                                    BWText { text: modelData.sizeLabel + " · CRC-32 " + modelData.crc32 + (modelData.simulatorOnly ? " · Simulator only" : ""); color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    BWText { text: modelData.notes || "No release notes"; font.pixelSize: 13; Layout.fillWidth: true }
                                    BWText { text: modelData.path; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                    BWText { text: "SHA-256  " + modelData.sha256; color: Theme.muted; font.pixelSize: 10; font.family: Theme.mono; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                }
                            }
                        }
                    }
                }

                // Diagnostics and custom commands.
                PageScroll {
                    gutter: window.pageMargin
                    ColumnLayout {
                        width: parent.width; spacing: Theme.section
                        Panel {
                            Layout.fillWidth: true; implicitHeight: pingContents.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: pingContents; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Link test"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                BWText { text: "Send a series of echo requests and measure round-trip time. Hex mode lets you exercise SLIP escape bytes C0 and DB."; color: Theme.muted; Layout.fillWidth: true; font.pixelSize: 13 }
                                RowLayout {
                                    spacing: 12
                                    Field { id: pingPayload; text: "C0 DB 11 22"; placeholderText: "Ping payload"; Layout.fillWidth: true }
                                    CheckField { id: pingHex; text: "Hex"; checked: true }
                                    NumberField { id: pingCount; from: 1; to: 100; value: 5; editable: true; Accessible.name: "Ping count" }
                                    ActionButton { text: "Run ping test"; primary: true; enabled: ready; onClicked: backend.perform("ping", {payload: pingPayload.text, hex: pingHex.checked, count: pingCount.value}) }
                                }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true; implicitHeight: commandContents.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: commandContents; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Custom command console"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                BWText { text: "User commands occupy 0x40–0x7F. Their meaning and payload depend on your firmware. The standard simulator returns UNKNOWN_CMD for unregistered commands."; color: Theme.muted; Layout.fillWidth: true; font.pixelSize: 13 }
                                RowLayout {
                                    spacing: 12
                                    Field { id: commandId; text: "0x40"; placeholderText: "Command ID"; Layout.preferredWidth: 110; font.family: Theme.mono }
                                    Field { id: commandPayload; placeholderText: "Payload, e.g. 01 02"; Layout.fillWidth: true; font.family: Theme.mono }
                                    CheckField { id: commandHex; text: "Hex"; checked: true }
                                    ActionButton { text: "Send command"; primary: true; enabled: ready; onClicked: backend.perform("send", {command: commandId.text, payload: commandPayload.text, hex: commandHex.checked}) }
                                }
                                BWText { text: s.reply.message || "Response payload will appear here after a successful command."; color: Theme.muted; Layout.fillWidth: true }
                                BWText { visible: !!s.reply.hex; text: s.reply.hex || ""; font.family: Theme.mono; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                BWText { visible: !!s.reply.text; text: s.reply.text || ""; Layout.fillWidth: true }
                            }
                        }
                        Panel {
                            Layout.fillWidth: true; implicitHeight: faults.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: faults; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 14
                                BWText { text: "Recovery lab"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                BWText { text: "Simulator only. Affect the next frame, then run a ping test and watch the retry in Inspector. Reset creates a fresh, erased virtual target."; color: Theme.muted; Layout.fillWidth: true; font.pixelSize: 13 }
                                Flow {
                                    Layout.fillWidth: true; spacing: 10
                                    Repeater {
                                        model: [{label:"Drop request", kind:"drop_requests"}, {label:"Drop response", kind:"drop_responses"}, {label:"Corrupt request", kind:"corrupt_requests"}, {label:"Corrupt response", kind:"corrupt_responses"}]
                                        delegate: ActionButton { required property var modelData; text: modelData.label; enabled: ready && s.device.simulated; onClicked: backend.perform("fault", {kind: modelData.kind}) }
                                    }
                                    ActionButton { text: "Reset simulator"; enabled: !s.busy && portField.editText === "sim"; onClicked: backend.perform("reset_simulator", {}) }
                                }
                            }
                        }
                    }
                }

                // Protocol capture.
                ColumnLayout {
                    spacing: 14
                    RowLayout {
                        Layout.rightMargin: window.pageMargin
                        spacing: 12
                        Field { id: traceSearch; objectName: "traceSearch"; placeholderText: "Filter by command, status, direction, or payload bytes, e.g. WRITE or BAD_PARAM"; Layout.fillWidth: true }
                        CheckField { id: followTraces; objectName: "followTraces"; text: "Follow latest"; checked: true }
                        ActionButton { text: "Export capture"; enabled: traceCount > 0; onClicked: exportData("traces") }
                        ActionButton { text: "Clear"; enabled: traceCount > 0; onClicked: backend.clear("traces") }
                    }
                    BWText { text: "Decoded frames, newest at the bottom · latest 500 kept · CRC-invalid frames marked BAD · WIRE shows the bytes after SLIP encoding"; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true; Layout.rightMargin: window.pageMargin }
                    Panel {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.rightMargin: window.pageMargin
                        ListView {
                            id: traceList; objectName: "traceList"
                            anchors.fill: parent; anchors.leftMargin: Theme.pad; anchors.rightMargin: 8; anchors.topMargin: 8; anchors.bottomMargin: 8; clip: true; spacing: 0
                            model: backend ? backend.traces : null
                            onCountChanged: if (followTraces.checked) Qt.callLater(function() { traceList.positionViewAtEnd() })
                            delegate: ColumnLayout {
                                required property var modelData
                                width: traceList.width - 16
                                property bool matches: (modelData.direction + " " + modelData.name + " " + modelData.command + " " + modelData.statusName + " seq " + modelData.seqLabel + " " + modelData.payload).toLowerCase().indexOf(traceSearch.text.toLowerCase()) >= 0
                                readonly property color tone: modelData.direction === "TX" ? Theme.accent : modelData.direction === "BAD" || modelData.status > 0 ? Theme.error : Theme.success
                                visible: matches; height: matches ? implicitHeight : 0
                                spacing: 9
                                RowLayout {
                                    Layout.topMargin: 14; Layout.fillWidth: true; spacing: 14
                                    BWText { text: modelData.time; font.family: Theme.mono; font.pixelSize: 11; color: Theme.muted; Layout.preferredWidth: 92 }
                                    Chip { text: modelData.direction; tone: parent.parent.tone; Layout.preferredWidth: 40 }
                                    BWText { text: modelData.name; font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.preferredWidth: 112; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                    BWText { text: "CMD " + modelData.command; font.family: Theme.mono; font.pixelSize: 11; color: Theme.muted; Layout.preferredWidth: 72 }
                                    BWText { text: "SEQ " + modelData.seqLabel; font.family: Theme.mono; font.pixelSize: 11; color: Theme.muted; Layout.preferredWidth: 72 }
                                    BWText {
                                        text: modelData.direction === "TX" ? "request" : modelData.direction === "BAD" ? "dropped · CRC or frame check failed" : modelData.statusName
                                        color: modelData.direction === "TX" ? Theme.muted : tone
                                        font.family: modelData.direction === "RX" ? Theme.mono : window.font.family
                                        font.pixelSize: 11; font.weight: modelData.direction === "RX" ? Font.DemiBold : Font.Normal
                                        Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                    }
                                    BWText { text: modelData.direction === "BAD" ? "" : modelData.length + (modelData.length === 1 ? " byte" : " bytes"); font.pixelSize: 11; color: Theme.muted }
                                }
                                BWText { text: modelData.payload || "(no payload)"; font.family: Theme.mono; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                BWText { text: "WIRE  " + modelData.wire; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                                Rectangle { Layout.fillWidth: true; Layout.topMargin: 8; height: 1; color: Theme.line }
                            }
                            ScrollBar.vertical: SlimScrollBar { }
                            ColumnLayout {
                                anchors.centerIn: parent; width: Math.min(parent.width - 40, 400); spacing: 12
                                visible: traceList.count === 0
                                BWText { text: "See the conversation on the wire"; font.pixelSize: 20; font.weight: Font.DemiBold; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                                BWText { text: "Connect a target and run a ping or firmware operation. Requests, responses, sequence numbers, and raw bytes will appear here."; color: Theme.muted; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter }
                                ActionButton { text: "Open diagnostics"; Layout.alignment: Qt.AlignHCenter; onClicked: page = 3 }
                            }
                        }
                    }
                }

                // Job history.
                ColumnLayout {
                    spacing: 14
                    RowLayout {
                        Layout.rightMargin: window.pageMargin
                        spacing: Theme.gap
                        Field { id: historySearch; placeholderText: "Search jobs, images, or results"; Layout.fillWidth: true }
                        ActionButton { text: "Export history"; enabled: s.history.length > 0; onClicked: exportData("history") }
                        ActionButton { text: "Clear history"; enabled: s.history.length > 0; onClicked: backend.clear("history") }
                    }
                    BWText { text: "Last 100 jobs · saved on this computer"; color: Theme.muted; font.pixelSize: 12 }
                    Panel {
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.rightMargin: window.pageMargin
                        ListView {
                            id: historyList
                            anchors.fill: parent; anchors.leftMargin: Theme.pad; anchors.rightMargin: 8; anchors.topMargin: Theme.pad - 4; anchors.bottomMargin: 8; clip: true; spacing: 16
                            model: s.history
                            delegate: ColumnLayout {
                                required property var modelData
                                width: historyList.width - 16
                                property bool matches: JSON.stringify(modelData).toLowerCase().indexOf(historySearch.text.toLowerCase()) >= 0
                                visible: matches; height: matches ? implicitHeight : 0
                                spacing: 8
                                RowLayout {
                                    spacing: 16
                                    BWText { text: modelData.action.replace("_", " "); font.weight: Font.DemiBold; font.capitalization: Font.Capitalize; Layout.preferredWidth: 140 }
                                    BWText { text: modelData.time; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    BWText { text: modelData.duration; color: Theme.muted; font.pixelSize: 12; Layout.preferredWidth: 85 }
                                    Chip { text: modelData.result; tone: levelColor(modelData.result) }
                                }
                                BWText { text: modelData.message; font.pixelSize: 12; Layout.fillWidth: true }
                                BWText { text: modelData.target + " · " + modelData.image; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true }
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line; Layout.topMargin: 8 }
                            }
                            BWText { anchors.centerIn: parent; visible: historyList.count === 0; text: "Your work leaves a clear trail. Connect a target to start your history."; color: Theme.muted; width: Math.min(parent.width-60, 450); horizontalAlignment: Text.AlignHCenter }
                            ScrollBar.vertical: SlimScrollBar { }
                        }
                    }
                }

                // Preferences.
                PageScroll {
                    gutter: window.pageMargin
                    ColumnLayout {
                        width: parent.width; spacing: Theme.section
                        Panel {
                            Layout.fillWidth: true; implicitHeight: preferencesContents.implicitHeight + 2 * Theme.pad
                            ColumnLayout {
                                id: preferencesContents; anchors.fill: parent; anchors.margins: Theme.pad; spacing: 18
                                BWText { text: "Connection defaults"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                BWText { text: "Changes apply on the next connection. Save to reuse these values when BootWire opens."; color: Theme.muted; Layout.fillWidth: true }
                                GridLayout {
                                    columns: 2; columnSpacing: 30; rowSpacing: 16; Layout.fillWidth: true
                                    BWText { text: "Response timeout (seconds)"; Layout.fillWidth: true }
                                    Field { id: timeoutField; text: String(s.preferences.timeout); Layout.preferredWidth: 160; enabled: !s.busy && !s.connected; validator: DoubleValidator { bottom: 0.05; top: 60; notation: DoubleValidator.StandardNotation } }
                                    BWText { text: "Erase timeout (seconds)"; Layout.fillWidth: true }
                                    Field { id: eraseTimeoutField; text: String(s.preferences.eraseTimeout); Layout.preferredWidth: 160; enabled: !s.busy && !s.connected; validator: DoubleValidator { bottom: 0.05; top: 120; notation: DoubleValidator.StandardNotation } }
                                    BWText { text: "Retries after the first attempt"; Layout.fillWidth: true }
                                    NumberField { id: retryField; from: 0; to: 10; value: s.preferences.retries; enabled: !s.busy && !s.connected; Accessible.name: "Retry count" }
                                }
                                ActionButton { text: "Save connection defaults"; primary: true; enabled: !s.busy; onClicked: backend.savePreferences(connectionOptions()) }
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                                BWText { text: "Appearance"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                RowLayout {
                                    spacing: Theme.gap
                                    ActionButton { text: "Light workspace"; primary: s.theme === "light"; onClicked: backend.setTheme("light") }
                                    ActionButton { text: "Dark workspace"; primary: s.theme === "dark"; onClicked: backend.setTheme("dark") }
                                }
                                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                                BWText { text: "Keyboard shortcuts"; font.pixelSize: 17; font.weight: Font.DemiBold }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Repeater {
                                        model: [["Ctrl+O", "Choose firmware"], ["Ctrl+1", "Firmware workspace"], ["Ctrl+2", "Devices & batches"], ["Ctrl+3", "Firmware library"], ["Ctrl+4", "Diagnostics & commands"], ["Ctrl+5", "Protocol inspector"], ["Ctrl+6", "Job history"], ["Ctrl+,", "Preferences"], ["Ctrl+Q", "Quit BootWire"], ["Ctrl+J", "Developer panel"], ["Tab", "Move between controls"]]
                                        delegate: RowLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            spacing: 24
                                            BWText { text: modelData[0]; font.family: Theme.mono; font.pixelSize: 12; Layout.preferredWidth: 76 }
                                            BWText { text: modelData[1]; font.pixelSize: 12; Layout.fillWidth: true }
                                        }
                                    }
                                }
                                BWText { text: "BootWire Desktop · Protocol v0.2\nSettings, profiles, release references, and job history stay on this computer. Firmware and activity are not uploaded."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                            }
                        }
                    }
                }
            }
            Rectangle {
                objectName: "workspaceStatus"
                Layout.fillWidth: true
                implicitHeight: Math.max(38, statusMessage.implicitHeight + 16)
                color: Theme.surface
                border.color: s.severity === "error" ? Theme.error : s.severity === "warning" ? Theme.warning : Theme.line
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 18; anchors.topMargin: 8; anchors.bottomMargin: 8; spacing: 12
                    Rectangle { width: 7; height: 7; radius: 4; color: s.busy ? Theme.accent : levelColor(s.severity) }
                    BWText { id: statusMessage; text: s.detail; color: s.severity === "error" || s.severity === "warning" ? levelColor(s.severity) : Theme.ink; font.pixelSize: 12; Layout.fillWidth: true }
                    ActivitySpinner { running: s.busy; visible: s.busy; Layout.preferredWidth: 26; Layout.preferredHeight: 26 }
                    ActionButton { text: "Stop operation"; glyph: "stop"; implicitHeight: 30; visible: s.busy; onClicked: backend.cancel() }
                }
            }
            DeveloperPanel {
                id: developerPanel
                objectName: "developerPanel"
                service: backend ? backend.console : null
                Layout.fillWidth: true
                Layout.preferredHeight: expanded ? panelHeight : 40
                maximumPanelHeight: Math.max(180, window.height - 350)
                onCommandSubmitted: function(command) { backend.console.submit(command, connectionOptions()) }
            }
        }
    }
}
