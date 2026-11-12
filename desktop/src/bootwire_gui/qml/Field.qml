import QtQuick
import QtQuick.Controls
TextField {
    id: control
    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
    selectByMouse: true
    font.pixelSize: 14
    color: Theme.ink
    placeholderTextColor: Theme.muted
    selectionColor: Theme.accent
    selectedTextColor: Theme.surface
    opacity: enabled ? 1 : 0.5
    Accessible.name: placeholderText
    background: Rectangle {
        radius: 9
        color: Theme.surface
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? Theme.accent : Theme.line
    }
}
