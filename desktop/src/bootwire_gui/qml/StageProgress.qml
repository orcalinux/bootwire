import QtQuick
import QtQuick.Controls
ProgressBar {
    id: control
    implicitHeight: 5
    background: Rectangle { implicitHeight: 5; radius: 3; color: Theme.line }
    contentItem: Item {
        Rectangle { width: control.visualPosition * parent.width; height: parent.height; radius: 3; color: Theme.accent }
    }
}
