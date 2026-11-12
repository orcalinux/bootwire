import QtQuick
import QtQuick.Controls
MenuBarItem {
    id: control
    objectName: menu ? menu.objectName + "Button" : ""
    implicitHeight: 32
    implicitWidth: label.implicitWidth + 24
    leftPadding: 12; rightPadding: 12
    hoverEnabled: true
    PointerFocus { control: parent }
    Accessible.name: text.replace(/&/g, "")
    contentItem: Label {
        id: label
        text: control.text.replace(/&/g, "")
        color: Theme.ink
        font.pixelSize: 13
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 7
        color: (control.menu && control.menu.visible) || control.down || control.hovered || control.visualFocus ? Theme.accentFill : "transparent"
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
    }
}
