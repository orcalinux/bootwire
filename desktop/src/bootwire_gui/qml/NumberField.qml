import QtQuick
import QtQuick.Controls
SpinBox {
    id: control
    implicitHeight: 40
    implicitWidth: 126
    leftPadding: 36; rightPadding: 36
    editable: true
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    contentItem: TextInput {
        text: control.textFromValue(control.value, control.locale)
        color: Theme.ink
        font.pixelSize: 13
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: !control.editable
        selectByMouse: true
        validator: control.validator
        selectionColor: Theme.accent
        selectedTextColor: Theme.dark ? "#102337" : "#FFFFFF"
        inputMethodHints: Qt.ImhDigitsOnly
        Accessible.name: control.Accessible.name
    }
    background: Rectangle { radius: Theme.controlRadius; color: Theme.surface; border.width: control.activeFocus ? 2 : 1; border.color: control.activeFocus ? Theme.accent : Theme.line }
    up.indicator: Rectangle {
        x: control.width-width-4; y: 4; width: 30; height: control.height-8; radius: 6
        color: control.up.pressed ? Theme.line : control.up.hovered ? Theme.accentFill : Theme.inset
        Glyph { anchors.centerIn: parent; name: "plus"; width: 14; height: 14; ink: control.value < control.to ? Theme.ink : Theme.line }
    }
    down.indicator: Rectangle {
        x: 4; y: 4; width: 30; height: control.height-8; radius: 6
        color: control.down.pressed ? Theme.line : control.down.hovered ? Theme.accentFill : Theme.inset
        Glyph { anchors.centerIn: parent; name: "minus"; width: 14; height: 14; ink: control.value > control.from ? Theme.ink : Theme.line }
    }
}
