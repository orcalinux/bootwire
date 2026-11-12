import QtQuick
import QtQuick.Controls
CheckBox {
    id: control
    implicitHeight: 36
    spacing: 10
    padding: 4
    hoverEnabled: true
    PointerFocus { control: parent }
    opacity: enabled ? 1 : 0.45
    indicator: Rectangle {
        implicitWidth: 20; implicitHeight: 20
        x: control.leftPadding; y: (control.height-height)/2
        radius: 6
        color: control.checked ? Theme.accent : control.hovered ? Theme.accentFill : Theme.surface
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? Theme.ink : control.checked ? Theme.accent : Theme.muted
        Glyph { anchors.centerIn: parent; width: 14; height: 14; name: "check"; visible: control.checked; ink: Theme.dark ? "#102337" : "#FFFFFF" }
        Behavior on color { ColorAnimation { duration: 110 } }
    }
    contentItem: Label {
        text: control.text
        color: Theme.ink
        font.pixelSize: 13
        leftPadding: control.indicator.width + control.spacing
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
