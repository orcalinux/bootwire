import QtQuick
TapHandler {
    id: handler
    required property var control
    // Observe the tap without taking the button's grab or interrupting its click.
    gesturePolicy: TapHandler.DragThreshold
    onTapped: Qt.callLater(function() {
        if (handler.control && handler.control.visualFocus) {
            handler.control.focus = false
            handler.control.forceActiveFocus(Qt.MouseFocusReason)
        }
    })
}
