import QtQuick
Item {
    id: root
    required property var targetWindow
    visible: targetWindow.visibility !== Window.Maximized && targetWindow.visibility !== Window.FullScreen
    // Keep a narrow native resize grip on every edge, including the corners.
    Repeater {
        model: [Qt.LeftEdge, Qt.RightEdge, Qt.TopEdge, Qt.BottomEdge,
                Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.TopEdge,
                Qt.LeftEdge | Qt.BottomEdge, Qt.RightEdge | Qt.BottomEdge]
        delegate: MouseArea {
            required property int modelData
            readonly property bool corner: (modelData & (Qt.LeftEdge | Qt.RightEdge)) && (modelData & (Qt.TopEdge | Qt.BottomEdge))
            width: corner ? 8 : (modelData & (Qt.LeftEdge | Qt.RightEdge)) ? 5 : root.width - 16
            height: corner ? 8 : (modelData & (Qt.TopEdge | Qt.BottomEdge)) ? 5 : root.height - 16
            x: (modelData & Qt.LeftEdge) ? 0 : (modelData & Qt.RightEdge) ? root.width - width : 8
            y: (modelData & Qt.TopEdge) ? 0 : (modelData & Qt.BottomEdge) ? root.height - height : 8
            cursorShape: corner ? ((modelData === (Qt.LeftEdge | Qt.TopEdge) || modelData === (Qt.RightEdge | Qt.BottomEdge)) ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor) : (modelData & (Qt.LeftEdge | Qt.RightEdge)) ? Qt.SizeHorCursor : Qt.SizeVerCursor
            onPressed: root.targetWindow.startSystemResize(modelData)
        }
    }
}
