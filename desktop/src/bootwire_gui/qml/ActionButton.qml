import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Button {
    id: control
    property bool primary: false
    property bool destructive: false
    property bool quiet: false
    property string glyph: ""
    property string tooltip: ""
    property color foreground: primary ? (Theme.dark ? "#102337" : "#FFFFFF") : destructive ? Theme.error : Theme.ink
    implicitHeight: 40
    implicitWidth: text ? Math.max(82, label.implicitWidth + (glyph ? 56 : 30)) : 40
    padding: 12
    hoverEnabled: true
    PointerFocus { control: parent }
    opacity: enabled ? 1 : 0.42
    Accessible.name: text || tooltip
    ToolTip.visible: hovered && tooltip !== ""
    ToolTip.text: tooltip
    ToolTip.delay: 700
    contentItem: Item {
        implicitHeight: Math.max(label.implicitHeight, 16)
        RowLayout {
            anchors.centerIn: parent
            width: Math.min(implicitWidth, parent.width)
            visible: control.text !== ""
            spacing: 8
            Glyph { visible: control.glyph !== ""; name: control.glyph; ink: control.foreground; Layout.preferredWidth: 18; Layout.preferredHeight: 18; Layout.alignment: Qt.AlignVCenter }
            Label {
                id: label
                text: control.text
                Layout.minimumWidth: 0
                elide: Text.ElideRight
                font.pixelSize: 13
                font.weight: Font.DemiBold
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: control.foreground
            }
        }
        Glyph {
            objectName: "centeredGlyph"
            anchors.centerIn: parent
            width: 18; height: 18
            visible: control.text === "" && control.glyph !== ""
            name: control.glyph
            ink: control.foreground
        }
    }
    scale: control.down ? 0.975 : 1
    Behavior on scale { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: Theme.controlRadius
        color: control.primary ? (control.down ? Qt.darker(Theme.accent, 1.12) : control.hovered ? Qt.lighter(Theme.accent, Theme.dark ? 1.08 : 1.18) : Theme.accent) : control.down ? Theme.line : control.hovered ? Theme.accentFill : control.quiet ? "transparent" : Theme.surface
        border.width: control.visualFocus ? 2 : control.primary || control.quiet ? 0 : 1
        border.color: control.visualFocus ? (control.primary ? (Theme.dark ? "#102337" : "#FFFFFF") : Theme.accent) : control.hovered && !control.quiet ? Theme.accent : Theme.line
        Behavior on border.color { ColorAnimation { duration: 120 } }
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
