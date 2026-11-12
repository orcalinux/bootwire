import QtQuick
import QtQuick.Controls
BusyIndicator {
    id: control
    implicitWidth: 24; implicitHeight: 24
    contentItem: Item {
        opacity: control.running ? 1 : 0
        Canvas {
            anchors.fill: parent
            property color ink: Theme.accent
            onInkChanged: requestPaint()
            onPaint: {
                let c=getContext("2d");c.reset();c.strokeStyle=ink;c.lineWidth=2;c.lineCap="round"
                c.beginPath();c.arc(width/2,height/2,width/2-3,-Math.PI/2,Math.PI);c.stroke()
            }
            RotationAnimator on rotation { running: control.running; from: 0; to: 360; duration: 850; loops: Animation.Infinite }
        }
    }
}
