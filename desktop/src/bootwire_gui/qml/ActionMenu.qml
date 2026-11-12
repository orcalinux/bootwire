import QtQuick
import QtQuick.Controls
Menu {
    id: control
    popupType: Popup.Item
    width: 284
    padding: 6
    background: Rectangle { radius: 11; color: Theme.surface; border.color: Theme.line }
    delegate: MenuOption { }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 100 } }
}
