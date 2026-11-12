import QtQuick
Canvas {
    id: icon
    property string name: "chevron"
    property color ink: Theme.muted
    implicitWidth: 18
    implicitHeight: 18
    antialiasing: true
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onNameChanged: requestPaint()
    onInkChanged: requestPaint()
    onPaint: {
        let c = getContext("2d"); c.reset()
        let side = Math.min(width, height)
        c.translate((width-side)/2, (height-side)/2); c.scale(side/24, side/24)
        c.strokeStyle = ink; c.fillStyle = ink; c.lineWidth = 2; c.lineCap = "round"; c.lineJoin = "round"
        function line(points) { c.beginPath(); c.moveTo(points[0], points[1]); for(let i=2;i<points.length;i+=2)c.lineTo(points[i],points[i+1]); c.stroke() }
        switch (name) {
        case "check": line([5,12,10,17,19,7]); break
        case "plus": line([5,12,19,12]); line([12,5,12,19]); break
        case "minus": line([5,12,19,12]); break
        case "refresh": c.beginPath();c.moveTo(20,10);c.bezierCurveTo(18,2,7,2,4,10);c.stroke();line([4,4,4,10,10,10]);c.beginPath();c.moveTo(4,14);c.bezierCurveTo(6,22,17,22,20,14);c.stroke();line([14,14,20,14,20,20]);break
        case "port": line([8,3,8,8]); line([16,3,16,8]); line([6,8,18,8,18,13,14,17,10,17,6,13,6,8]); line([12,17,12,22]); break
        case "speed": c.beginPath();c.arc(12,14,8,Math.PI,2*Math.PI);c.stroke();line([12,14,17,8]);line([4,17,20,17]);break
        case "folder": line([3,7,3,19,21,19,21,7,12,7,10,4,3,4,3,7]); break
        case "settings": line([3,6,9,6]);line([15,6,21,6]);line([3,12,13,12]);line([19,12,21,12]);line([3,18,5,18]);line([11,18,21,18]);for(let knob of [[12,6],[16,12],[8,18]]){c.beginPath();c.arc(knob[0],knob[1],2.5,0,Math.PI*2);c.stroke()}break
        case "sun": c.beginPath();c.arc(12,12,4,0,Math.PI*2);c.stroke();for(let i=0;i<8;i++){let a=i*Math.PI/4;line([12+7*Math.cos(a),12+7*Math.sin(a),12+10*Math.cos(a),12+10*Math.sin(a)])}break
        case "moon":
            c.beginPath();c.moveTo(20,14)
            c.bezierCurveTo(19,18,16,21,12,21)
            c.bezierCurveTo(7,21,3,17,3,12)
            c.bezierCurveTo(3,8,6,4,10,3)
            c.bezierCurveTo(8,7,9,11,12,13)
            c.bezierCurveTo(14,15,17,15,20,14)
            c.closePath();c.stroke();break
        case "minimize": line([5,12,19,12]);break
        case "maximize": line([5,5,19,5,19,19,5,19,5,5]);break
        case "restore": line([8,5,8,3,21,3,21,16,19,16]);line([3,8,16,8,16,21,3,21,3,8]);break
        case "close": line([6,6,18,18]);line([6,18,18,6]);break
        case "search": c.beginPath();c.arc(10,10,6,0,Math.PI*2);c.stroke();line([15,15,21,21]);break
        case "arrow": line([5,12,19,12]);line([13,6,19,12,13,18]);break
        case "terminal": line([4,5,20,5,20,19,4,19,4,5]);line([7,9,10,12,7,15]);line([13,15,17,15]);break
        case "output": line([8,5,21,5]);line([8,12,21,12]);line([8,19,17,19]);for(let y of [5,12,19]){c.beginPath();c.arc(3,y,1,0,Math.PI*2);c.fill()}break
        case "chip": line([6,6,18,6,18,18,6,18,6,6]);line([10,10,14,10,14,14,10,14,10,10]);for(let p of [9,15]){line([p,3,p,6]);line([p,18,p,21]);line([3,p,6,p]);line([18,p,21,p])}break
        case "devices": line([3,4,16,4,16,15,3,15,3,4]);line([7,20,12,20]);line([10,15,10,20]);line([19,10,22,10,22,21,15,21,15,18]);break
        case "library": line([4,4,8,4,8,20,4,20,4,4]);line([11,4,15,4,15,20,11,20,11,4]);line([17,5,20,4,23,19,20,20,17,5]);break
        case "activity": line([2,12,6,12,9,4,14,20,17,12,22,12]);break
        case "history": c.beginPath();c.arc(12,12,8,-2.5,2.9);c.stroke();line([3,4,3,9,8,9]);line([12,7,12,12,16,14]);break
        case "help": c.beginPath();c.arc(12,12,9,0,Math.PI*2);c.stroke();c.beginPath();c.moveTo(9,9);c.bezierCurveTo(9,5,16,6,15,10);c.bezierCurveTo(15,12,12,12,12,14);c.stroke();line([12,17,12,17.1]);break
        case "trash": line([4,6,20,6]);line([9,6,9,3,15,3,15,6]);line([6,6,7,21,17,21,18,6]);line([10,10,10,17]);line([14,10,14,17]);break
        case "export": line([5,14,5,20,19,20,19,14]);line([12,15,12,3]);line([7,8,12,3,17,8]);break
        case "stop": line([6,6,18,6,18,18,6,18,6,6]);break
        case "play": line([8,4,20,12,8,20,8,4]);break
        case "chevron-up": line([6,15,12,9,18,15]);break
        default: line([6,9,12,15,18,9]);
        }
    }
}
