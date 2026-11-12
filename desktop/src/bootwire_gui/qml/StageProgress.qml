import QtQuick
import QtQuick.Controls
ProgressBar {
    id: control
    implicitHeight: 6
    background: Rectangle { implicitHeight: 6; radius: 3; color: Theme.line }
    contentItem: Item {
        Rectangle {
            width: control.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent
            Behavior on width { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        }
    }
}
