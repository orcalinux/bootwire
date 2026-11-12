import QtQuick
import QtQuick.Controls
// Scrolling workspace page. The scrollbar lives in a reserved gutter on the
// right, so it never sits on top of fields, buttons, or panel edges, and the
// content does not shift when the bar appears.
ScrollView {
    id: control
    property int gutter: 30
    clip: true
    rightPadding: gutter
    bottomPadding: 4
    contentWidth: availableWidth
    ScrollBar.vertical: SlimScrollBar {
        parent: control
        x: control.width - width - Math.max(2, (control.gutter - width) / 2 - 2)
        y: control.topPadding
        height: control.height - control.topPadding
    }
}
