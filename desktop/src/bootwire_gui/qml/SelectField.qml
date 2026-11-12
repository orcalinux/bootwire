import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ComboBox {
    id: control
    property string glyph: ""
    property string detailRole: ""
    implicitHeight: 42
    implicitWidth: 180
    leftPadding: glyph ? 38 : 13
    rightPadding: 36
    hoverEnabled: true
    opacity: enabled ? 1 : 0.48
    function entryText(index) {
        let entry = model[index]
        return textRole ? String(entry[textRole]) : String(entry)
    }
    background: Rectangle {
        radius: 9
        color: control.enabled ? (control.hovered ? Theme.inset : Theme.surface) : Theme.inset
        border.width: control.activeFocus || control.popup.visible ? 2 : 1
        border.color: control.activeFocus || control.popup.visible ? Theme.accent : Theme.line
        Behavior on color { ColorAnimation { duration: 120 } }
    }
    Glyph { visible: control.glyph !== ""; name: control.glyph; x: 12; anchors.verticalCenter: parent.verticalCenter; ink: Theme.muted }
    indicator: Glyph {
        name: "chevron"; x: control.width - width - 12; y: (control.height-height)/2
        rotation: control.popup.visible ? 180 : 0
        ink: control.popup.visible ? Theme.accent : Theme.muted
        Behavior on rotation { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    }
    contentItem: TextField {
        text: control.editable ? control.editText : control.displayText
        enabled: control.editable
        readOnly: !control.editable || control.down
        autoScroll: control.editable
        selectByMouse: true
        padding: 0
        color: Theme.ink
        font.pixelSize: 13
        selectionColor: Theme.accent
        selectedTextColor: Theme.dark ? "#102337" : "#FFFFFF"
        verticalAlignment: Text.AlignVCenter
        background: Item { }
        validator: control.validator
        Accessible.name: control.Accessible.name
    }
    delegate: ItemDelegate {
        id: option
        required property int index
        width: options.width
        implicitHeight: control.detailRole ? 58 : 42
        highlighted: control.highlightedIndex === index
        hoverEnabled: true
        leftPadding: 12; rightPadding: 12
        background: Rectangle { radius: 7; color: option.highlighted || option.hovered ? Theme.accentFill : "transparent" }
        contentItem: RowLayout {
            spacing: 12
            ColumnLayout {
                Layout.fillWidth: true; spacing: 3
                BWText { text: control.detailRole ? String(control.model[option.index][control.detailRole]) : control.entryText(option.index); font.pixelSize: 13; font.weight: control.currentIndex === option.index ? Font.DemiBold : Font.Normal; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                BWText { visible: control.detailRole !== ""; text: control.entryText(option.index); color: Theme.muted; font.pixelSize: 11; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
            }
            Glyph { name: "check"; ink: Theme.accent; visible: control.entryText(option.index) === control.editText || (!control.editable && control.currentIndex === option.index); Layout.preferredWidth: 16; Layout.preferredHeight: 16 }
        }
        Accessible.name: control.entryText(index)
    }
    popup: Popup {
        objectName: control.objectName + "Popup"
        y: control.height + 7
        width: Math.max(control.width, control.detailRole ? 280 : 160)
        padding: 6
        implicitHeight: Math.min(options.contentHeight + 12, 320)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        contentItem: Item {
            id: popupContent
            implicitHeight: options.contentHeight
            ListView {
                id: options
                objectName: control.objectName + "Options"
                anchors.fill: parent
                anchors.rightMargin: dropdownScroll.visible ? dropdownScroll.width + 4 : 0
                clip: true
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: SlimScrollBar {
                    id: dropdownScroll
                    objectName: control.objectName + "ScrollBar"
                    parent: popupContent
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.right: parent.right
                    visible: options.contentHeight > options.height + 0.5
                    policy: ScrollBar.AsNeeded
                }
            }
        }
        background: Rectangle { radius: 11; color: Theme.surface; border.color: Theme.line }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 100 } }
    }
}
