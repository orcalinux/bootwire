pragma Singleton
import QtQuick
QtObject {
    property bool dark: false
    readonly property color canvas: dark ? "#101923" : "#F3F5F8"
    readonly property color surface: dark ? "#182431" : "#FFFFFF"
    readonly property color inset: dark ? "#12202D" : "#F7F9FC"
    readonly property color ink: dark ? "#EBF1F8" : "#182A3D"
    readonly property color muted: dark ? "#A4B4C7" : "#586A7E"
    readonly property color line: dark ? "#344657" : "#DCE3EC"
    readonly property color accent: dark ? "#72B4FF" : "#185DB8"
    readonly property color accentFill: dark ? "#24466B" : "#E9F1FC"
    readonly property color success: dark ? "#72D6B3" : "#157657"
    readonly property color warning: dark ? "#F3C879" : "#916013"
    readonly property color error: dark ? "#FFA3A3" : "#B02F3C"
    readonly property color rail: "#142C44"
    readonly property color railText: "#B9CADB"
    readonly property int radius: 12
    readonly property string mono: "DejaVu Sans Mono"
}
