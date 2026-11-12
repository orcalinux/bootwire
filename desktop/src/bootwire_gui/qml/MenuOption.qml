import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
MenuItem {
    id: control
    property string hint: ""
    property string glyph: ""
    implicitHeight: 39
    leftPadding: 12; rightPadding: 12
    hoverEnabled: true
    opacity: enabled ? 1 : 0.4
    background: Rectangle { radius: 7; color: control.highlighted || control.hovered ? Theme.accentFill : "transparent" }
    contentItem: RowLayout {
        spacing: 10
        Glyph { visible: control.glyph !== ""; name: control.glyph; ink: Theme.muted; Layout.preferredWidth: 16; Layout.preferredHeight: 16 }
        Label { text: control.text; color: Theme.ink; font.pixelSize: 13; elide: Text.ElideRight; Layout.minimumWidth: 0; Layout.fillWidth: true }
        Label { text: control.hint; color: Theme.muted; font.pixelSize: 10 }
    }
    indicator: Item { }
    arrow: Item { }
}
