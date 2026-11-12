import QtQuick
import QtQuick.Controls
ScrollBar {
    id: control
    padding: 2
    implicitWidth: 10
    implicitHeight: 10
    minimumSize: 0.07
    contentItem: Rectangle {
        implicitWidth: 6; implicitHeight: 6; radius: 3
        color: control.pressed ? Theme.accent : Theme.muted
        opacity: control.active || control.hovered ? 0.65 : 0.24
    }
    background: Item { }
}
