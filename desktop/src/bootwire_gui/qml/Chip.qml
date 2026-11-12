import QtQuick
// Small status pill: a tinted ground in the tone's own hue, with the tone as text.
Rectangle {
    id: chip
    property string text: ""
    property color tone: Theme.muted
    implicitWidth: label.implicitWidth + 18
    implicitHeight: 22
    radius: height / 2
    color: Qt.rgba(tone.r, tone.g, tone.b, Theme.dark ? 0.20 : 0.11)
    BWText { id: label; anchors.centerIn: parent; text: chip.text; color: chip.tone; font.pixelSize: 10; font.weight: Font.DemiBold; wrapMode: Text.NoWrap }
}
