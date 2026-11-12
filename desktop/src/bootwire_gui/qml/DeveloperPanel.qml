import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: panel
    required property var service
    property bool expanded: false
    property int tab: 1
    property int panelHeight: 280
    property int maximumPanelHeight: 600
    property var cs: service ? service.state : ({entries:[],commands:[],pending:{},executing:false,generation:0})
    property var terminal: service ? service.terminal : null
    property var ts: terminal ? terminal.state : ({running:false,starting:false,shells:[],cwd:"",html:"",message:""})
    signal commandSubmitted(string command)
    color: Theme.surface
    implicitHeight: expanded ? panelHeight : 40
    function open(index) { tab = index; expanded = true; if (tab === 1) commandInput.forceActiveFocus(Qt.ShortcutFocusReason) }
    function toggle() { expanded = !expanded; if (expanded && tab === 1) commandInput.forceActiveFocus(Qt.ShortcutFocusReason) }
    // The output list is filled incrementally so it keeps its scroll position
    // while entries arrive. Entry ids only grow; a filter change or a clear rebuilds it.
    ListModel { id: outputModel }
    property int lastEntryId: 0
    readonly property bool outputVisible: expanded && tab !== 2
    readonly property string filterKey: tab + "|" + verbose.checked + "|" + outputSearch.text.toLowerCase() + "|" + cs.generation + "|" + outputVisible
    onFilterKeyChanged: rebuildOutput()
    onCsChanged: syncOutput()
    function entryMatches(e) {
        if (tab === 1) return e.source === "command"
        return e.source !== "command" && (verbose.checked || e.level !== "debug") &&
            (e.message + " " + e.source).toLowerCase().indexOf(outputSearch.text.toLowerCase()) >= 0
    }
    function rebuildOutput() { outputModel.clear(); lastEntryId = 0; syncOutput() }
    function syncOutput() {
        if (!outputVisible) return
        let entries = cs.entries
        if (!entries.length) { outputModel.clear(); lastEntryId = 0; return }
        while (outputModel.count > 0 && outputModel.get(0).id < entries[0].id) outputModel.remove(0)
        let start = entries.length
        while (start > 0 && entries[start - 1].id > lastEntryId) start--
        for (let i = start; i < entries.length; i++) {
            let e = entries[i]
            if (entryMatches(e)) outputModel.append({id: e.id, time: e.time, level: e.level, source: e.source, message: e.message})
        }
        lastEntryId = entries[entries.length - 1].id
    }
    Rectangle { width: parent.width; height: 1; color: Theme.line }
    MouseArea {
        width: parent.width; height: 5; z: 2
        cursorShape: panel.expanded ? Qt.SizeVerCursor : Qt.ArrowCursor
        property int initialHeight: 0
        DragHandler {
            target: null
            enabled: panel.expanded
            xAxis.enabled: false
            onActiveChanged: if (active) parent.initialHeight = panel.panelHeight
            onTranslationChanged: if (active) panel.panelHeight = Math.max(180, Math.min(panel.maximumPanelHeight, parent.initialHeight - translation.y))
        }
    }
    FileDialog {
        id: exportDialog
        title: "Export developer output"
        fileMode: FileDialog.SaveFile
        nameFilters: ["JSON files (*.json)"]
        defaultSuffix: "json"
        onAccepted: panel.service.export(selectedFile.toString())
    }
    Dialog {
        id: confirmation
        objectName: "consoleConfirmation"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(600, parent.width - 60)
        modal: true; padding: 24
        background: Panel { }
        contentItem: ColumnLayout {
            spacing: 14
            BWText { text: "Review device command"; font.pixelSize: 20; font.weight: Font.DemiBold }
            BWText { text: "Target: " + (panel.cs.pending.target || ""); font.weight: Font.DemiBold }
            BWText { text: panel.cs.pending.summary || ""; Layout.fillWidth: true }
            ScrollView {
                Layout.fillWidth: true; Layout.preferredHeight: 170; clip: true
                TextArea { text: panel.cs.pending.details || ""; readOnly: true; selectByMouse: true; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; wrapMode: TextEdit.Wrap; background: Rectangle { color: Theme.inset; radius: 7 } }
            }
            RowLayout {
                spacing: Theme.gap
                Item { Layout.fillWidth: true }
                ActionButton { text: "Cancel"; onClicked: confirmation.reject() }
                ActionButton { objectName: "confirmConsoleCommand"; text: "Execute command"; primary: true; onClicked: confirmation.accept() }
            }
        }
        onAccepted: panel.service.confirm()
        onRejected: panel.service.reject()
    }
    Connections {
        target: panel.service
        function onConfirmationRequested() { confirmation.open() }
    }
    FontMetrics { id: terminalFont; font.family: Theme.mono; font.pixelSize: 13 }
    Timer {
        id: terminalResize
        interval: 100
        onTriggered: if (panel.terminal) panel.terminal.resize(Math.floor((terminalViewport.width-36)/terminalFont.averageCharacterWidth), Math.floor((terminalViewport.height-16)/terminalFont.height))
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        RowLayout {
            Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 10
            Layout.preferredHeight: 40
            spacing: 8
            Repeater {
                model: ["Output", "BootWire", "System terminal"]
                delegate: ActionButton {
                    required property int index
                    required property string modelData
                    objectName: ["outputPanelTab","bootwirePanelTab","terminalPanelTab"][index]
                    foreground: panel.expanded && panel.tab === index ? Theme.accent : Theme.muted
                    text: modelData; glyph: ["output", "chip", "terminal"][index]; quiet: true; implicitHeight: 32
                    onClicked: panel.open(index)
                    Rectangle { anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; width: parent.width-24; height: 2; radius: 1; color: Theme.accent; visible: panel.expanded && panel.tab === index }
                }
            }
            Item { Layout.fillWidth: true }
            BWText { text: panel.expanded ? (panel.tab === 2 && panel.ts.running ? panel.ts.shell : "Developer panel") : "Ctrl+`"; font.pixelSize: 10; color: Theme.muted }
            ActionButton { objectName: "toggleDeveloperPanel"; text: ""; glyph: panel.expanded ? "close" : "chevron-up"; quiet: true; implicitWidth: 32; implicitHeight: 30; tooltip: panel.expanded ? "Hide developer panel" : "Show developer panel"; onClicked: panel.toggle() }
        }
        ColumnLayout {
            visible: panel.expanded && panel.tab !== 2
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.leftMargin: 18; Layout.rightMargin: 18; Layout.topMargin: 6; Layout.bottomMargin: 12
            spacing: 10
            RowLayout {
                visible: panel.tab === 0
                Layout.fillWidth: true
                spacing: Theme.gap
                Field { id: outputSearch; placeholderText: "Filter output, protocol bytes, or errors"; Layout.fillWidth: true; implicitHeight: 32 }
                CheckField { id: verbose; text: "Verbose"; checked: true }
                ActionButton { text: "Export"; glyph: "export"; implicitHeight: 32; onClicked: exportDialog.open() }
                ActionButton { text: "Clear"; glyph: "trash"; implicitHeight: 32; onClicked: panel.service.clear("output") }
            }
            RowLayout {
                visible: panel.tab === 1
                Layout.fillWidth: true
                spacing: Theme.gap
                BWText { text: "Shared device session · BootWire commands"; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true }
                ActionButton { text: "Help"; glyph: "help"; implicitHeight: 30; onClicked: panel.commandSubmitted("help") }
                ActionButton { text: "Clear"; glyph: "trash"; implicitHeight: 30; onClicked: panel.service.clear("command") }
            }
            ListView {
                id: outputList
                objectName: "developerOutputList"
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; spacing: 6
                model: outputModel
                onCountChanged: if (followOutput.checked) Qt.callLater(function(){ outputList.positionViewAtEnd() })
                onContentHeightChanged: if (followOutput.checked) Qt.callLater(function(){ outputList.positionViewAtEnd() })
                delegate: RowLayout {
                    required property string time
                    required property string level
                    required property string source
                    required property string message
                    width: Math.max(0, outputList.width - 14)
                    spacing: 12
                    BWText { text: time; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10; Layout.preferredWidth: 92; Layout.alignment: Qt.AlignTop }
                    TextEdit {
                        text: (panel.tab === 0 ? "["+source+"] " : "") + message
                        textFormat: TextEdit.PlainText
                        color: level === "error" ? Theme.error : level === "warning" ? Theme.warning : level === "input" ? Theme.accent : Theme.ink
                        font.family: Theme.mono; font.pixelSize: 11
                        readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere
                        Layout.fillWidth: true
                    }
                }
                BWText { visible: outputList.count === 0; text: panel.tab === 1 ? "Type help, or try bootwire -p sim info." : "Device activity and frame details appear here as you work."; color: Theme.muted; font.pixelSize: 12 }
                ScrollBar.vertical: SlimScrollBar { }
            }
            RowLayout {
                visible: panel.tab === 1
                Layout.fillWidth: true
                spacing: Theme.gap
                BWText { text: ">"; color: Theme.accent; font.family: Theme.mono }
                Field {
                    id: commandInput; objectName: "bootwireCommandInput"
                    Layout.fillWidth: true; implicitHeight: 34
                    placeholderText: "bootwire -p sim info  ·  help lists commands"
                    font.family: Theme.mono; font.pixelSize: 12
                    property int historyPosition: -1
                    onAccepted: { panel.commandSubmitted(text); text = ""; historyPosition = -1 }
                    Keys.onUpPressed: {
                        let entries = panel.cs.commands
                        if (entries.length) { historyPosition = historyPosition < 0 ? entries.length-1 : Math.max(0,historyPosition-1); text = entries[historyPosition] }
                    }
                    Keys.onDownPressed: {
                        let entries = panel.cs.commands
                        if (historyPosition >= 0) { historyPosition++; if(historyPosition >= entries.length) { historyPosition=-1; text="" } else text=entries[historyPosition] }
                    }
                }
                ActionButton { objectName: "executeBootwireCommand"; text: "Execute"; glyph: "arrow"; primary: true; implicitHeight: 34; enabled: commandInput.text.trim().length > 0; onClicked: { panel.commandSubmitted(commandInput.text); commandInput.text=""; commandInput.historyPosition=-1 } }
            }
            CheckField { id: followOutput; objectName: "followOutput"; text: "Follow output"; checked: true; implicitHeight: 26 }
        }
        ColumnLayout {
            visible: panel.expanded && panel.tab === 2
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 8
            RowLayout {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18; Layout.topMargin: 6
                spacing: Theme.gap
                SelectField { id: shellChoice; objectName: "terminalShellChoice"; model: panel.ts.shells; textRole: "label"; implicitHeight: 34; Layout.preferredWidth: 170; enabled: !panel.ts.running && !panel.ts.starting; Accessible.name: "Local shell" }
                Field { id: workingDirectory; text: panel.ts.cwd; placeholderText: "Working directory"; implicitHeight: 34; Layout.fillWidth: true; enabled: !panel.ts.running && !panel.ts.starting }
                ActionButton { objectName: "startSystemTerminal"; text: panel.ts.starting ? "Starting…" : "Start shell"; glyph: "play"; primary: true; implicitHeight: 34; enabled: !panel.ts.running && !panel.ts.starting && panel.ts.shells.length > 0; onClicked: { panel.terminal.start(panel.ts.shells[shellChoice.currentIndex].id, workingDirectory.text); terminalText.forceActiveFocus(Qt.MouseFocusReason) } }
                ActionButton { text: "Stop"; glyph: "stop"; implicitHeight: 34; enabled: panel.ts.running || panel.ts.starting; onClicked: panel.terminal.stop() }
                ActionButton { text: "Clear"; glyph: "trash"; implicitHeight: 34; enabled: panel.ts.running; onClicked: panel.terminal.clear() }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.leftMargin: 18; Layout.rightMargin: 18
                BWText { text: panel.ts.message; font.pixelSize: 10; color: Theme.muted; Layout.fillWidth: true }
                BWText { text: "Ctrl+Shift+C copy · Ctrl+Shift+V paste · Ctrl+C interrupt"; font.pixelSize: 10; color: Theme.muted }
            }
            Rectangle {
                id: terminalViewport
                objectName: "terminalViewport"
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#111E2C"
                onWidthChanged: terminalResize.restart()
                onHeightChanged: terminalResize.restart()
                ScrollView {
                    id: terminalScroll
                    anchors.fill: parent; anchors.margins: 10
                    clip: true
                    rightPadding: 14
                    TextEdit {
                        id: terminalText; objectName: "systemTerminalInput"
                        text: panel.ts.html
                        color: "#E7EDF7"
                        selectionColor: "#385879"
                        font.family: Theme.mono; font.pixelSize: 13
                        readOnly: true; selectByMouse: true
                        textFormat: TextEdit.RichText
                        wrapMode: TextEdit.NoWrap
                        onTextChanged: Qt.callLater(function(){ terminalScroll.contentItem.contentY = Math.max(0,terminalScroll.contentItem.contentHeight-terminalScroll.availableHeight) })
                        Keys.priority: Keys.BeforeItem
                        Keys.onPressed: function(event) {
                            let ctrl = (event.modifiers & Qt.ControlModifier) !== 0
                            let shift = (event.modifiers & Qt.ShiftModifier) !== 0
                            if(ctrl && shift && event.key === Qt.Key_C) { panel.terminal.copy(selectedText); event.accepted=true; return }
                            if(ctrl && shift && event.key === Qt.Key_V) { panel.terminal.paste(); event.accepted=true; return }
                            if(!panel.ts.running) return
                            let codes = ({})
                            codes[Qt.Key_Return]="\r";codes[Qt.Key_Enter]="\r";codes[Qt.Key_Backspace]="\x7f";codes[Qt.Key_Tab]="\t";codes[Qt.Key_Backtab]="\x1b[Z";codes[Qt.Key_Escape]="\x1b"
                            codes[Qt.Key_Up]="\x1b[A";codes[Qt.Key_Down]="\x1b[B";codes[Qt.Key_Right]="\x1b[C";codes[Qt.Key_Left]="\x1b[D"
                            codes[Qt.Key_Home]="\x1b[H";codes[Qt.Key_End]="\x1b[F";codes[Qt.Key_Delete]="\x1b[3~";codes[Qt.Key_PageUp]="\x1b[5~";codes[Qt.Key_PageDown]="\x1b[6~"
                            codes[Qt.Key_F1]="\x1bOP";codes[Qt.Key_F2]="\x1bOQ";codes[Qt.Key_F3]="\x1bOR";codes[Qt.Key_F4]="\x1bOS"
                            codes[Qt.Key_F5]="\x1b[15~";codes[Qt.Key_F6]="\x1b[17~";codes[Qt.Key_F7]="\x1b[18~";codes[Qt.Key_F8]="\x1b[19~"
                            codes[Qt.Key_F9]="\x1b[20~";codes[Qt.Key_F10]="\x1b[21~";codes[Qt.Key_F11]="\x1b[23~";codes[Qt.Key_F12]="\x1b[24~"
                            let data = codes[event.key] || event.text
                            if(ctrl && event.key >= Qt.Key_A && event.key <= Qt.Key_Z) data = String.fromCharCode(event.key-Qt.Key_A+1)
                            else if(event.modifiers & Qt.AltModifier) data="\x1b"+data
                            if(data) { panel.terminal.write(data); event.accepted=true }
                        }
                        MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton; cursorShape: Qt.IBeamCursor }
                    }
                    ScrollBar.vertical: SlimScrollBar { parent: terminalScroll; x: terminalScroll.width - width; y: 0; height: terminalScroll.height }
                }
                BWText { visible: !panel.ts.html; anchors.centerIn: parent; width: parent.width-40; horizontalAlignment: Text.AlignHCenter; text: "Start a shell above. Use the BootWire tab to work with the connected device; a standalone CLI opens its own connection."; color: "#A4B4C7"; font.pixelSize: 12 }
            }
        }
    }
}
