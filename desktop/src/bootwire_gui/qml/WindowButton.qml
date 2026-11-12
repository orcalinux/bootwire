import QtQuick
import QtQuick.Controls
Button {
    id: control
    property string symbol: "minimize"
    implicitWidth: 42
    implicitHeight: 36
    hoverEnabled: true
    PointerFocus { control: parent }
    Accessible.name: symbol === "minimize" ? "Minimize window" : symbol === "close" ? "Close window" : symbol === "restore" ? "Restore window" : "Maximize window"
    ToolTip.text: Accessible.name
    ToolTip.visible: hovered
    ToolTip.delay: 800
    contentItem: Item {
        Glyph { anchors.centerIn: parent; name: control.symbol; ink: control.symbol === "close" && control.hovered ? (Theme.dark ? "#102337" : "#FFFFFF") : Theme.ink; width: 14; height: 14 }
    }
    background: Rectangle {
        radius: 6
        color: control.hovered ? (control.symbol === "close" ? Theme.error : Theme.accentFill) : "transparent"
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
    }
    padding: 11
}
