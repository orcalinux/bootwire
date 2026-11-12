#!/usr/bin/env python3
"""Draw the BootWire figures that need an exact layout: layers, frames, payloads, memory map.

    python3 bootwire_figures.py OUT_DIR        # writes OUT_DIR/architecture/*.svg and OUT_DIR/frames/*.svg

Plain Python 3, no packages. Text is measured with Arial metrics (the same as Helvetica and
Liberation Sans), so boxes fit on Windows, macOS and Linux. The colours are shared with the
PlantUML and Graphviz diagrams (puml/_style.iuml, dot/*): change them in both places.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

# ----------------------------------------------------------------------------------------------
# Look
# ----------------------------------------------------------------------------------------------
FONT = "Arial, Helvetica, 'Liberation Sans', Arimo, sans-serif"
MONO = "'DejaVu Sans Mono', Menlo, Consolas, 'Liberation Mono', monospace"

INK = "#1F2D3D"        # body text
MUTED = "#5B6B7C"      # secondary text
FAINT = "#8A99A8"      # rulers, hints
NAVY = "#1B3A5F"       # panels, headers, titles
NAVY_SUB = "#AFC6E0"   # text on navy
BLUE = "#1E90D6"       # peer arrows
BLUE_SOFT = "#7FA9D6"  # arrows inside a panel
CARD = "#F4F7FB"       # light card
CARD_LINE = "#DFE6EE"
LINE = "#C9D4E0"
NOTE_BG = "#FFF8E6"
NOTE_LINE = "#E8C66A"
RED = "#C0392B"
RED_BG = "#FDECEA"
GREEN = "#1E8449"
GREEN_BG = "#E6F4EA"

# fill, stroke, text
FIELD = {
    "seq": ("#DCEBFB", "#2F6DB5", "#173E6B"),
    "cmd": ("#E9E2F9", "#6B4FBB", "#3B2A73"),
    "status": ("#FDEBD3", "#C77700", "#6B4000"),
    "addr": ("#E4F3EC", "#2E8B65", "#13513A"),
    "data": ("#CDEBDD", "#2E8B65", "#13513A"),
    "crc": ("#FBE1E4", "#C0394B", "#6E1A26"),
    "end": (NAVY, NAVY, "#FFFFFF"),
    "esc": ("#FFE2A6", "#C98A00", "#5C3D00"),
    "num": ("#EEF3F9", "#8FA8C4", "#1F3B5C"),
    "empty": ("#FFFFFF", "#B7C3CF", FAINT),
    "none": ("#FFFFFF", "#FFFFFF", MUTED),     # text only, no visible box
}

# Arial advance widths (1/1000 em) for ' ' .. '~' and a few extra characters.
_CHARS = (" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
          "abcdefghijklmnopqrstuvwxyz{|}~…→←≤≥≠·—–×µ")
_REG = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556,
        556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722,
        722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722,
        667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556,
        556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500,
        500, 334, 260, 334, 584, 1000, 1000, 1000, 549, 549, 549, 278, 1000, 556, 584, 576]
_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556,
         556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722,
         722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722,
         667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611,
         611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556,
         500, 389, 280, 389, 584, 1000, 1000, 1000, 549, 549, 549, 278, 1000, 556, 584, 576]
_W = {False: dict(zip(_CHARS, _REG)), True: dict(zip(_CHARS, _BOLD))}


def tw(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
    """Width of a text in px."""
    if mono:
        return len(s) * size * 0.602
    table = _W[bold]
    return sum(table.get(c, 600) for c in s) * size / 1000


def wrap(s: str, size: float, width: float, bold: bool = False) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and tw(trial, size, bold) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------------------------
# A very small SVG writer
# ----------------------------------------------------------------------------------------------
class Svg:
    def __init__(self, w: float, h: float):
        self.w, self.h = w, h
        self.body: list[str] = []
        self.markers: dict[str, str] = {}

    def _marker(self, color: str, size: float, start: bool) -> str:
        key = f"{'s' if start else 'e'}{color.strip('#')}-{int(size * 10)}"
        if key not in self.markers:
            path = "M10,0 L0,5 L10,10 z" if start else "M0,0 L10,5 L0,10 z"
            self.markers[key] = (
                f'<marker id="{key}" viewBox="0 0 10 10" refX="{0 if start else 10}" refY="5" '
                f'markerWidth="{size}" markerHeight="{size}" markerUnits="userSpaceOnUse" '
                f'orient="auto"><path d="{path}" fill="{color}"/></marker>')
        return key

    def rect(self, x, y, w, h, fill="none", stroke="none", sw=1.0, rx=0, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.0, dash=None, start=False, end=False, head=10):
        a = f' stroke-dasharray="{dash}"' if dash else ""
        if start:
            a += f' marker-start="url(#{self._marker(stroke, head, True)})"'
        if end:
            a += f' marker-end="url(#{self._marker(stroke, head, False)})"'
        self.body.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{stroke}" stroke-width="{sw}"{a}/>')

    def path(self, d, stroke=INK, sw=1.0, fill="none", dash=None, join="round"):
        a = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                         f'stroke-linejoin="{join}"{a}/>')

    def circle(self, cx, cy, r, fill, stroke="none", sw=1.0):
        self.body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{fill}" '
                         f'stroke="{stroke}" stroke-width="{sw}"/>')

    def text(self, x, y, s, size=13, bold=False, fill=INK, anchor="start", mono=False, italic=False):
        attrs = f'font-family="{MONO if mono else FONT}" font-size="{size}"'
        if bold:
            attrs += ' font-weight="bold"'
        if italic:
            attrs += ' font-style="italic"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        self.body.append(f'<text x="{x:.1f}" y="{y:.1f}" {attrs} fill="{fill}" '
                         f'xml:space="preserve">{escape(s)}</text>')

    def runs(self, x, y, parts, size=13, anchor="start"):
        """parts: list of (text, style) where style holds 'b' (bold), 'm' (mono) and/or a #colour."""
        widths = [tw(t, size, "b" in st, "m" in st) for t, st in parts]
        total = sum(widths)
        if anchor == "middle":
            x -= total / 2
        elif anchor == "end":
            x -= total
        for (t, st), w in zip(parts, widths):
            colour = next((p for p in st.split() if p.startswith("#")), INK)
            self.text(x, y, t, size, bold="b" in st.split(), fill=colour, mono="m" in st.split())
            x += w

    def save(self, path: Path, title: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        defs = "".join(self.markers.values())
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" role="img">\n'
               f'<title>{escape(title)}</title>\n'
               f'<defs>{defs}</defs>\n'
               f'<rect width="{self.w}" height="{self.h}" fill="#FFFFFF"/>\n'
               + "\n".join(self.body) + "\n</svg>\n")
        path.write_text(svg, encoding="utf-8")


def heading(s: Svg, title: str, sub: str = "", y: float = 42):
    s.text(s.w / 2, y, title, 22, bold=True, fill=NAVY, anchor="middle")
    if sub:
        s.text(s.w / 2, y + 24, sub, 13, fill=MUTED, anchor="middle")


def note(s: Svg, x, y, w, lines, size=12.5, kind="info"):
    """Note box; lines is a list of runs lists. Returns its height."""
    pad, lh = 14, size * 1.5
    h = pad * 2 + lh * len(lines) - (lh - size)
    fill, stroke = (NOTE_BG, NOTE_LINE) if kind == "note" else (CARD, CARD_LINE)
    s.rect(x, y, w, h, fill, stroke, 1, rx=10)
    s.rect(x, y, 5, h, stroke if kind == "note" else BLUE, rx=2)
    for i, parts in enumerate(lines):
        s.runs(x + pad + 6, y + pad + size * 0.85 + i * lh, parts, size)
    return h


def byte_box(s: Svg, x, y, label, kind, w=34, h=32, size=14):
    fill, stroke, colour = FIELD[kind]
    s.rect(x, y, w, h, fill, stroke, 1.2, rx=5, dash="4 3" if kind == "empty" else None)
    s.text(x + w / 2, y + h / 2 + size * 0.36, label, size, bold=kind != "empty", fill=colour,
           anchor="middle", mono=kind != "empty")


def bytes_group(s: Svg, x, y, values, kind, label=None, w=34, h=32, gap=3, size=14,
                label_colour=MUTED, kinds=None):
    """Draw a run of bytes; returns the x after the group."""
    for i, v in enumerate(values):
        byte_box(s, x + i * (w + gap), y, v, kinds[i] if kinds else kind, w, h, size)
    end = x + len(values) * (w + gap) - gap
    if label:
        s.text((x + end) / 2, y + h + 16, label, 11.5, fill=label_colour, anchor="middle")
    return end


def chip(s: Svg, x, y, label, fill, stroke, colour, size=11.5, mono=False, bold=True, h=22):
    w = tw(label, size, bold, mono) + 16
    s.rect(x, y, w, h, fill, stroke, 1, rx=h / 2)
    s.text(x + w / 2, y + h / 2 + size * 0.36, label, size, bold=bold, fill=colour,
           anchor="middle", mono=mono)
    return w


# ----------------------------------------------------------------------------------------------
# 1  Layered architecture
# ----------------------------------------------------------------------------------------------
def layered_architecture(out: Path):
    W, H = 1040, 652
    s = Svg(W, H)
    heading(s, "Layered Architecture",
            "Host and target run the same four layers. Each layer uses the one below it "
            "and talks to its peer on the other side.")
    s.rect(24, 92, W - 48, 528, CARD, CARD_LINE, 1, rx=18)

    pw, py, ph = 320, 118, 436
    left, right = 64, W - 64 - pw
    sides = [
        (left, "Host", "PC  ·  Python  ·  desktop/src/bootwire", [
            ("Application layer", "bootwire CLI  ·  BootWireClient.flash()"),
            ("Command layer", "BootWireClient: SEQ, timeout, retry"),
            ("Frame layer", "frame.py (CRC-16)  ·  slip.py"),
            ("Physical layer", "UARTTransport (pyserial)"),
        ]),
        (right, "Target", "Cortex-M bootloader  ·  C firmware", [
            ("Application layer", "flash driver · region check · jump"),
            ("Command layer", "dispatcher  ·  one-entry reply cache"),
            ("Frame layer", "SLIP RX state machine  ·  CRC-16"),
            ("Physical layer", "UART driver (RX interrupt or DMA)"),
        ]),
    ]
    bx_in, bw, bh, pitch, first = 22, 276, 62, 90, py + 80
    for px, name, sub, layers in sides:
        s.rect(px, py, pw, ph, NAVY, "none", rx=16)
        s.text(px + pw / 2, py + 38, name, 21, bold=True, fill="#FFFFFF", anchor="middle")
        s.text(px + pw / 2, py + 59, sub, 12, fill=NAVY_SUB, anchor="middle")
        for i, (title, detail) in enumerate(layers):
            y = first + i * pitch
            s.rect(px + bx_in, y, bw, bh, "#FFFFFF", "none", rx=12)
            s.text(px + pw / 2, y + 27, title, 16, bold=True, fill=NAVY, anchor="middle")
            s.text(px + pw / 2, y + 47, detail, 12, fill=MUTED, anchor="middle")
            if i < len(layers) - 1:
                s.line(px + pw / 2, y + bh + 5, px + pw / 2, y + pitch - 5, BLUE_SOFT, 2,
                       start=True, end=True, head=7)

    links = [
        ("bootloader operations", "connect · erase · write · verify · run", True),
        ("request / response", "SEQ · CMD · STATUS · payload", True),
        ("frames sealed with CRC-16", "SLIP:  C0 … escaped bytes … C0", True),
        ("UART byte stream", "115200 8N1  ·  TX, RX, GND", False),
    ]
    x1, x2 = left + bx_in + bw + 6, right + bx_in - 6
    for i, (top, bottom, logical) in enumerate(links):
        y = first + i * pitch + bh / 2
        s.line(x1, y, x2, y, BLUE, 3 if not logical else 2.4, dash="9 6" if logical else None,
               start=True, end=True, head=13)
        s.text((x1 + x2) / 2, y - 11, top, 14, bold=True, fill=INK, anchor="middle")
        s.text((x1 + x2) / 2, y + 23, bottom, 12, fill=MUTED, anchor="middle")

    ly = 590
    s.line(250, ly, 300, ly, BLUE, 2.4, dash="9 6")
    s.text(310, ly + 4.5, "logical link: peers exchange this through the layers below", 12.5, fill=INK)
    s.line(680, ly, 730, ly, BLUE, 3)
    s.text(740, ly + 4.5, "physical link: the real wire", 12.5, fill=INK)
    s.save(out / "architecture" / "bootwire_layered_architecture.svg", "BootWire layered architecture")


# ----------------------------------------------------------------------------------------------
# 2  One WRITE through the layers
# ----------------------------------------------------------------------------------------------
def layer_encapsulation(out: Path):
    W, H = 1240, 790
    s = Svg(W, H)
    heading(s, "What Each Layer Adds",
            "One WRITE request (SEQ 0x05, 4 bytes C0 DB 11 22 to 0x08008000) on its way down the "
            "host stack. The target runs the same steps upward.")

    pill_x, pill_w = 32, 206
    cx = 290                       # content column
    nx, nw = 990, 220              # note column

    def pill(y, h, name, sub):
        s.rect(pill_x, y, pill_w, h, NAVY, "none", rx=14)
        s.text(pill_x + pill_w / 2, y + h / 2 - 3, name, 15, bold=True, fill="#FFFFFF", anchor="middle")
        s.text(pill_x + pill_w / 2, y + h / 2 + 15, sub, 11.5, fill=NAVY_SUB, anchor="middle")

    def side_note(y, title, text):
        s.text(nx, y, title, 12.5, bold=True, fill=NAVY)
        for i, ln in enumerate(wrap(text, 12, nw)):
            s.text(nx, y + 18 + i * 16, ln, 12, fill=MUTED)

    def step(y_from, y_to):  # host goes down the stack: arrow between two pills
        s.line(pill_x + pill_w / 2, y_from + 4, pill_x + pill_w / 2, y_to - 4, BLUE, 2.2, end=True, head=10)

    # rows
    rows = {"app": 104, "cmd": 196, "crc": 300, "slip": 404, "phy": 528}

    # Application
    y = rows["app"]
    pill(y, 64, "Application layer", "bootwire CLI · bootloader core")
    s.rect(cx, y + 8, 520, 48, "#FFFFFF", LINE, 1.2, rx=10)
    s.runs(cx + 18, y + 38, [("client.write(", "m"), ("0x08008000", "m #13513A"), (", ", "m"),
                             ("b'\\xC0\\xDB\\x11\\x22'", "m #13513A"), (")", "m")], 14)
    side_note(y + 14, "Operation", "Program 4 bytes at an address. Nothing about framing yet.")

    # Command layer
    y = rows["cmd"]
    pill(y, 72, "Command layer", "BootWireClient · dispatcher")
    step(rows["app"] + 64, y)
    x = bytes_group(s, cx, y + 8, ["05"], "seq", "SEQ") + 10
    x = bytes_group(s, x, y + 8, ["11"], "cmd", "CMD") + 10
    x = bytes_group(s, x, y + 8, ["00", "80", "00", "08"], "addr", "address (little-endian)") + 10
    bytes_group(s, x, y + 8, ["C0", "DB", "11", "22"], "data", "data")
    side_note(y + 10, "+ SEQ and CMD",
              "One request in flight. The host waits for the reply with the same SEQ and "
              "resends the same frame on a timeout.")

    # Frame layer: CRC and SLIP
    y = rows["crc"]
    pill(y, 172, "Frame layer", "frame.py, slip.py · RX ISR")
    step(rows["cmd"] + 72, y)
    x = bytes_group(s, cx, y + 8, ["05"], "seq", "SEQ") + 10
    x = bytes_group(s, x, y + 8, ["11"], "cmd", "CMD") + 10
    x = bytes_group(s, x, y + 8, ["00", "80", "00", "08"], "addr", "address") + 10
    x = bytes_group(s, x, y + 8, ["C0", "DB", "11", "22"], "data", "data") + 10
    bytes_group(s, x, y + 8, ["E3", "20"], "crc", "CRC-16 = 0x20E3")
    side_note(y + 10, "+ CRC-16",
              "CRC-16/CCITT-FALSE of every byte before it, low byte first. 12 bytes now.")

    y = rows["slip"]
    x = bytes_group(s, cx, y + 8, ["C0"], "end", "END") + 10
    x = bytes_group(s, x, y + 8, ["05"], "seq", "SEQ") + 10
    x = bytes_group(s, x, y + 8, ["11"], "cmd", "CMD") + 10
    x = bytes_group(s, x, y + 8, ["00", "80", "00", "08"], "addr", "address") + 10
    x = bytes_group(s, x, y + 8, ["DB", "DC", "DB", "DD", "11", "22"], "data",
                    "data: C0 → DB DC, DB → DB DD", kinds=["esc"] * 4 + ["data"] * 2) + 10
    x = bytes_group(s, x, y + 8, ["E3", "20"], "crc", "CRC-16") + 10
    bytes_group(s, x, y + 8, ["C0"], "end", "END")
    side_note(y + 10, "+ SLIP",
              "END (C0) at both ends; C0 and DB inside the frame are escaped. 16 bytes on the wire.")

    # Physical
    y = rows["phy"]
    pill(y, 132, "Physical layer", "UARTTransport · UART")
    step(rows["crc"] + 172, y)
    bit_w, top, low = 40, y + 34, y + 70
    x0 = cx
    bits = [("idle", 1)] + [("start", 0)] + [(f"b{i}", (0xC0 >> i) & 1) for i in range(8)] + [
        ("stop", 1), ("idle", 1)]
    d, prev = f"M{x0},{top}", 1
    for i, (_, v) in enumerate(bits):
        bx = x0 + i * bit_w
        lvl = top if v else low
        if v != prev:
            d += f" L{bx},{lvl}"
        d += f" L{bx + bit_w},{lvl}"
        prev = v
    for i, (name, v) in enumerate(bits):
        bx = x0 + i * bit_w
        shade = "#F4F7FB" if name.startswith("b") else ("#FFF3DC" if name in ("start", "stop") else "#FFFFFF")
        s.rect(bx, top - 6, bit_w, low - top + 12, shade, "none")
        s.line(bx, top - 10, bx, low + 10, CARD_LINE, 1, dash="3 3")
        s.text(bx + bit_w / 2, low + 26, name, 11, fill=MUTED, anchor="middle")
        if name != "idle":
            s.text(bx + bit_w / 2, top - 14, str(v), 12, bold=True, fill=NAVY, anchor="middle", mono=True)
    s.path(d, NAVY, 2.4)
    s.text(x0 + 5 * bit_w + bit_w / 2, low + 46, "data bits of 0xC0, least significant bit first",
           11.5, fill=MUTED, anchor="middle")
    s.text(x0 + len(bits) * bit_w + 14, (top + low) / 2 + 5, "… then 15 more bytes", 12.5, fill=MUTED)
    side_note(y + 10, "Bits on the wire",
              "Each byte: start bit, 8 data bits, stop bit (8N1). 16 bytes at 115200 baud take 1.39 ms.")

    note(s, pill_x, 696, W - 2 * pill_x, [
        [("Target, upward: ", "b"), ("UART RX interrupt  →  SLIP RX state machine (removes END and escapes)  →  "
                                    "CRC-16 check  →  reply cache and dispatcher  →  flash driver.", "")],
        [("The response travels back the same way, with STATUS after CMD | 0x80.", "#5B6B7C")],
    ])
    s.save(out / "architecture" / "bootwire_layer_encapsulation.svg", "BootWire: what each layer adds")


# ----------------------------------------------------------------------------------------------
# 3  Request and response frames
# ----------------------------------------------------------------------------------------------
def _frame_figure(out: Path, name: str, title: str, sub: str, fields, examples, footer, extra=None):
    gap = 8
    total = sum(f[3] for f in fields) + gap * (len(fields) - 1)
    W = max(980, total + 96)
    x0 = (W - total) / 2
    H = 520 + (60 if extra else 0) + 44 * (len(examples) - 1)
    s = Svg(W, H)
    heading(s, title, sub)

    fy, fh = 128, 72
    x = x0
    xs = []
    for key, label, size, w, offset, lines in fields:
        fill, stroke, colour = FIELD[key]
        s.text(x + w / 2, fy - 12, offset, 12, fill=FAINT, anchor="middle", mono=True)
        s.rect(x, fy, w, fh, fill, stroke, 1.6, rx=10)
        s.text(x + w / 2, fy + 32, label, 17, bold=True, fill=colour, anchor="middle")
        s.text(x + w / 2, fy + 54, size, 12.5, fill=colour, anchor="middle")
        for i, ln in enumerate(lines):
            s.text(x + w / 2, fy + fh + 26 + i * 18, ln, 12.5, fill=INK if i == 0 else MUTED,
                   anchor="middle")
        xs.append((x, w))
        x += w + gap

    # examples: each byte sits under its field, the caption and the wire form below
    ey = fy + fh + 100
    s.text(x0, ey, "Examples", 14, bold=True, fill=NAVY)
    s.line(x0 + 80, ey - 5, x0 + total, ey - 5, CARD_LINE, 1)
    y = ey + 16
    for values, caption in examples:
        for (fx, fw), (key, *_), v in zip(xs, fields, values):
            if not v:
                byte_box(s, fx + fw / 2 - 30, y, "none", "empty", w=60, h=30, size=11)
                continue
            n, bw = len(v), 36
            start = fx + fw / 2 - (n * bw + (n - 1) * 3) / 2
            for i, b in enumerate(v):
                byte_box(s, start + i * (bw + 3), y, b, key, w=bw, h=30, size=13.5)
        wire = "C0 " + " ".join(b for v in values for b in v) + " C0"
        s.runs(x0, y + 52, [(caption, "b"), ("      on the wire:  ", FAINT), (wire, f"m {MUTED}")], 12.5)
        y += 80
    y -= 6
    if extra:
        y = extra(s, x0, y, total) + 16
    h = note(s, x0, y, total, footer)
    s.h = y + h + 28
    s.save(out / "frames" / name, title)


def request_frame(out: Path):
    _frame_figure(
        out, "bootwire_request_frame.svg", "Request Frame",
        "Host → target  ·  the bytes before SLIP encoding  ·  multi-byte fields are little-endian",
        [("seq", "SEQ", "1 byte", 160, "byte 0", ["sequence number", "+1 for every new request",
                                                  "same value on a resend"]),
         ("cmd", "CMD", "1 byte", 160, "byte 1", ["command ID 0x00 … 0x7F", "bit 7 = 0 marks a request"]),
         ("data", "PAYLOAD", "0 … max_payload bytes", 330, "bytes 2 … N+1",
          ["command parameters", "layout depends on CMD", "may be empty"]),
         ("crc", "CRC16", "2 bytes", 200, "bytes N+2, N+3",
          ["CRC-16/CCITT-FALSE", "over bytes 0 … N+1", "low byte first"])],
        [([["01"], ["01"], [], ["1F", "3E"]], "PING, SEQ 0x01, no payload"),
         ([["03"], ["10"], ["00", "80", "00", "08", "00", "08", "00", "00"], ["7D", "03"]],
          "ERASE 0x08008000, length 0x800, SEQ 0x03")],
        [[("No length field. ", "b"), ("The SLIP END byte marks the end of the frame and the CRC-16 "
                                       "proves it arrived complete.", "")],
         [("Shortest request: 4 bytes. Longest: max_payload + 4 bytes; a longer frame is dropped "
           "while it is received.", "#5B6B7C")]],
    )


def response_frame(out: Path):
    def statuses(s: Svg, x0, y, total):
        s.text(x0, y + 15, "STATUS values", 14, bold=True, fill=NAVY)
        x = x0 + 120
        for code, name in enumerate(["OK", "GENERIC", "UNKNOWN_CMD", "BAD_LENGTH", "BAD_PARAM",
                                     "FLASH", "VERIFY", "NO_APP"]):
            ok = code == 0
            x += chip(s, x, y, f"{code}  {name}", GREEN_BG if ok else RED_BG, GREEN if ok else "#E3A39C",
                      GREEN if ok else RED, 11.5) + 6
        return y + 22

    _frame_figure(
        out, "bootwire_response_frame.svg", "Response Frame",
        "Target → host  ·  the bytes before SLIP encoding  ·  multi-byte fields are little-endian",
        [("seq", "SEQ", "1 byte", 140, "byte 0", ["copied from", "the request"]),
         ("cmd", "CMD | 0x80", "1 byte", 160, "byte 1", ["request CMD", "with bit 7 set", "0x80 … 0xFF"]),
         ("status", "STATUS", "1 byte", 150, "byte 2", ["0x00 = OK", "else an error code"]),
         ("data", "PAYLOAD", "0 … max_payload bytes", 290, "bytes 3 … N+2",
          ["result data", "may be empty"]),
         ("crc", "CRC16", "2 bytes", 180, "bytes N+3, N+4",
          ["CRC-16/CCITT-FALSE", "over bytes 0 … N+2", "low byte first"])],
        [([["01"], ["81"], ["00"], [], ["05", "D3"]], "PING response, SEQ 0x01, OK, no payload"),
         ([["03"], ["90"], ["04"], [], ["A3", "CD"]], "ERASE response, SEQ 0x03, BAD_PARAM")],
        [[("Shortest response: 5 bytes. ", "b"), ("Bit 7 of byte 1 tells a response from a request, so a "
                                                  "frame echoed back by a loop-back cable", "")],
         [("or read by the wrong side is never taken for the other kind.", "")]],
        extra=statuses,
    )


# ----------------------------------------------------------------------------------------------
# 4  SLIP on the wire
# ----------------------------------------------------------------------------------------------
def wire_format(out: Path):
    W, H = 1000, 640
    s = Svg(W, H)
    heading(s, "SLIP Framing on the Wire",
            "WRITE request, SEQ 0x05: 4 data bytes C0 DB 11 22 to 0x08008000")
    bw, gap = 42, 4
    frame = [("05", "seq"), ("11", "cmd"), ("00", "addr"), ("80", "addr"), ("00", "addr"), ("08", "addr"),
             ("C0", "data"), ("DB", "data"), ("11", "data"), ("22", "data"), ("E3", "crc"), ("20", "crc")]
    wire = [("C0", "end"), ("05", "seq"), ("11", "cmd"), ("00", "addr"), ("80", "addr"), ("00", "addr"),
            ("08", "addr"), ("DB", "esc"), ("DC", "esc"), ("DB", "esc"), ("DD", "esc"), ("11", "data"),
            ("22", "data"), ("E3", "crc"), ("20", "crc"), ("C0", "end")]
    # wire byte indices for each frame byte
    mapping = [[1], [2], [3], [4], [5], [6], [7, 8], [9, 10], [11], [12], [13], [14]]

    def row_x(n):
        return (W - (n * bw + (n - 1) * gap)) / 2

    fy, wy, h = 150, 330, 40
    fx0, wx0 = row_x(len(frame)), row_x(len(wire))
    # field labels above the frame
    groups = [("SEQ", 0, 0, "seq"), ("CMD", 1, 1, "cmd"), ("address", 2, 5, "addr"),
              ("data", 6, 9, "data"), ("CRC-16", 10, 11, "crc")]
    for label, a, b, key in groups:
        xa, xb = fx0 + a * (bw + gap), fx0 + b * (bw + gap) + bw
        s.line(xa + 2, fy - 10, xb - 2, fy - 10, FIELD[key][1], 2)
        s.text((xa + xb) / 2, fy - 18, label, 12.5, bold=True, fill=FIELD[key][2], anchor="middle")
    s.text(40, fy + 17, "Frame", 15, bold=True, fill=NAVY)
    s.text(40, fy + 35, "12 bytes", 12, fill=MUTED)
    s.text(40, wy + 17, "On the wire", 15, bold=True, fill=NAVY)
    s.text(40, wy + 35, "16 bytes", 12, fill=MUTED)

    # mapping lines
    for i, targets in enumerate(mapping):
        x1 = fx0 + i * (bw + gap) + bw / 2
        for t in targets:
            x2 = wx0 + t * (bw + gap) + bw / 2
            esc = len(targets) > 1
            s.path(f"M{x1},{fy + h + 2} C{x1},{fy + h + 70} {x2},{wy - 70} {x2},{wy - 2}",
                   FIELD["esc"][1] if esc else LINE, 2 if esc else 1.2)
    for i, (v, k) in enumerate(frame):
        byte_box(s, fx0 + i * (bw + gap), fy, v, k, bw, h, 15)
    for i, (v, k) in enumerate(wire):
        byte_box(s, wx0 + i * (bw + gap), wy, v, k, bw, h, 15)

    # encode / decode hint
    mid = (fy + h + wy) / 2
    s.line(150, fy + h + 14, 150, wy - 14, BLUE, 2, end=True, head=10)
    s.text(162, mid - 4, "SLIP encode", 12.5, bold=True, fill=INK)
    s.text(162, mid + 13, "host TX, target TX", 11.5, fill=MUTED)
    s.line(W - 150, wy - 14, W - 150, fy + h + 14, BLUE, 2, end=True, head=10)
    s.text(W - 162, mid - 4, "SLIP decode", 12.5, bold=True, fill=INK, anchor="end")
    s.text(W - 162, mid + 13, "RX state machine", 11.5, fill=MUTED, anchor="end")

    # labels under the wire row
    under = [("END", 0, 0), ("unchanged", 1, 6), ("C0 → DB DC", 7, 8), ("DB → DB DD", 9, 10),
             ("unchanged", 11, 14), ("END", 15, 15)]
    for label, a, b in under:
        xa, xb = wx0 + a * (bw + gap), wx0 + b * (bw + gap) + bw
        s.path(f"M{xa + 2},{wy + h + 8} L{xa + 2},{wy + h + 13} L{xb - 2},{wy + h + 13} L{xb - 2},{wy + h + 8}",
               FAINT, 1)
        s.text((xa + xb) / 2, wy + h + 30, label, 12, bold=label != "unchanged",
               fill=FIELD["esc"][2] if "→" in label else (NAVY if label == "END" else MUTED), anchor="middle")

    # special bytes
    cy, cw, cg = 440, 218, 12
    cx0 = (W - (4 * cw + 3 * cg)) / 2
    specials = [("C0", "END", "end", "starts and ends every frame"),
                ("DB", "ESC", "esc", "an escape code follows"),
                ("DC", "ESC_END", "num", "after ESC: data byte C0"),
                ("DD", "ESC_ESC", "num", "after ESC: data byte DB")]
    for i, (v, name, k, desc) in enumerate(specials):
        x = cx0 + i * (cw + cg)
        s.rect(x, cy, cw, 64, "#FFFFFF", CARD_LINE, 1.2, rx=10)
        byte_box(s, x + 12, cy + 12, v, k, 40, 40, 15)
        s.text(x + 64, cy + 29, name, 14, bold=True, fill=NAVY)
        s.text(x + 64, cy + 47, desc, 11.5, fill=MUTED)
    note(s, cx0, cy + 86, 4 * cw + 3 * cg, [
        [("CRC-16 is computed before escaping and checked after un-escaping.", "")],
        [("Worst case on the wire: 2 × frame length + 2 bytes. ", "#5B6B7C"),
         ("Bytes before the first END are ignored; END END is an empty frame and is ignored.", "#5B6B7C")]])
    s.save(out / "frames" / "bootwire_wire_format.svg", "BootWire SLIP framing on the wire")


# ----------------------------------------------------------------------------------------------
# 5  Command payloads
# ----------------------------------------------------------------------------------------------
def command_payloads(out: Path):
    W = 1040
    s = Svg(W, 100)
    heading(s, "Command Payloads",
            "Offsets inside PAYLOAD  ·  all fields little-endian  ·  the response STATUS byte is not shown")
    x0, cw = 32, W - 64
    lx = x0 + 22               # row label
    fx0 = x0 + 118             # first field
    fw_total = x0 + cw - 22 - fx0

    def fields_row(y, items, h=50):
        """items: (weight, name, sub, kind). Weights share the row width."""
        gap = 6
        total_w = sum(i[0] for i in items)
        avail = fw_total - gap * (len(items) - 1)
        x = fx0
        for weight, name, sub, kind in items:
            w = avail * weight / total_w
            fill, stroke, colour = FIELD[kind]
            s.rect(x, y, w, h, fill, stroke, 1.2, rx=7, dash="4 3" if kind == "empty" else None)
            if sub:
                s.text(x + w / 2, y + 21, name, 12, bold=True, fill=colour, anchor="middle")
                s.text(x + w / 2, y + 38, sub, 11, fill=MUTED, anchor="middle", mono=True)
            else:
                s.text(x + w / 2, y + h / 2 + 4.5, name, 12.5, bold=kind != "empty", fill=colour,
                       anchor="middle")
            x += w + gap
        return y + h

    def text_row(y, lines, size=12.5):
        for i, ln in enumerate(lines):
            s.runs(fx0, y + 15 + i * 19, ln, size)
        return y + 19 * len(lines) + 2

    def card(y, cid, name, purpose, errors, rows, accent=NAVY):
        top = y
        body: list = []
        mark = len(s.body)          # the card background goes under the rows drawn next
        y += 54
        for label, kind, content in rows:
            body.append((y, label))
            if kind == "fields":
                y = fields_row(y, content) + 12
            else:
                y = text_row(y, content) + 10
        h = y - top + 4
        rows_svg = s.body[mark:]
        del s.body[mark:]
        s.rect(x0, top, cw, h, "#FFFFFF", CARD_LINE, 1.2, rx=12)
        s.path(f"M{x0},{top + 12} a12,12 0 0 1 12,-12 h{cw - 24} a12,12 0 0 1 12,12 v32 h{-cw} z",
               "none", 0, fill=accent)
        s.text(x0 + 20, top + 28, name, 17, bold=True, fill="#FFFFFF")
        idw = chip(s, x0 + 28 + tw(name, 17, True), top + 11, cid, "#FFFFFF", "none", accent, 12,
                   mono=True)
        s.text(x0 + 40 + tw(name, 17, True) + idw, top + 27, purpose, 13, fill=NAVY_SUB)
        ex = x0 + cw - 16
        for e in reversed(errors):
            w = tw(e, 10.5, True) + 14
            ex -= w
            s.rect(ex, top + 12, w, 20, "#FFFFFF", "none", rx=10)
            s.text(ex + w / 2, top + 26, e, 10.5, bold=True, fill=RED, anchor="middle")
            ex -= 5
        if errors:
            s.text(ex - 4, top + 27, "errors", 11.5, fill=NAVY_SUB, anchor="end")
        for ry, label in body:
            s.text(lx, ry + 20, label, 11.5, bold=True, fill=MUTED)
        s.body.extend(rows_svg)
        return top + h + 18

    y = 92
    y = card(y, "0x00", "CONNECT", "start a session, read the device info", ["BAD_LENGTH"], [
        ("REQUEST", "fields", [(2.4, "protocol version = 2", "[0] u8", "num"), (8, "", "", "none")]),
        ("RESPONSE", "fields", [
            (1.1, "protocol", "[0] u8", "num"), (1, "bl major", "[1] u8", "num"),
            (1, "bl minor", "[2] u8", "num"), (1, "bl patch", "[3] u8", "num"),
            (1.4, "max_payload", "[4..5] u16", "num"), (1.35, "device_id", "[6..9] u32", "num"),
            (1.45, "app_start", "[10..13] u32", "addr"), (1.45, "app_size", "[14..17] u32", "addr"),
            (1.45, "erase_block", "[18..21] u32", "num"), (1.3, "write_align", "[22] u8", "num")]),
        ("", "text", [[("23 bytes. The host takes the flash layout from here and never hard-codes it. "
                        "CONNECT always runs and clears the reply cache.", "#5B6B7C")]]),
    ])
    y = card(y, "0x01", "PING", "link test", [], [
        ("REQUEST", "fields", [(1, "any bytes", "0 … max_payload", "data")]),
        ("RESPONSE", "fields", [(1, "the same bytes, echoed (the host checks they are equal)", "",
                                 "data")]),
    ])
    y = card(y, "0x10", "ERASE", "erase whole blocks", ["BAD_LENGTH", "BAD_PARAM", "FLASH"], [
        ("REQUEST", "fields", [(1, "address", "[0..3] u32", "addr"), (1, "length", "[4..7] u32", "num")]),
        ("RULES", "text", [[("Both multiples of ", ""), ("erase_block", "m"), (" (counted from ", ""),
                            ("app_start", "m"), ("), inside the application region.", "")]]),
        ("RESPONSE", "fields", [(1, "empty", "", "empty")]),
    ])
    y = card(y, "0x11", "WRITE", "program bytes, then read them back",
             ["BAD_LENGTH", "BAD_PARAM", "FLASH", "VERIFY"], [
        ("REQUEST", "fields", [(1, "address", "[0..3] u32", "addr"),
                               (2.6, "data", "[4..N-1]  1 … max_payload − 4 bytes", "data")]),
        ("RULES", "text", [[("Address and data length multiples of ", ""), ("write_align", "m"),
                            (", inside the application region, into erased flash.", "")],
                           [("The target reads the data back after programming: a mismatch gives VERIFY.",
                             "")]]),
        ("RESPONSE", "fields", [(1, "empty", "", "empty")]),
    ])
    y = card(y, "0x12", "VERIFY", "compare a CRC-32 of flash", ["BAD_LENGTH", "BAD_PARAM", "VERIFY"], [
        ("REQUEST", "fields", [(1, "address", "[0..3] u32", "addr"), (1, "length", "[4..7] u32", "num"),
                               (1, "CRC-32 expected", "[8..11] u32", "crc")]),
        ("RESPONSE", "fields", [(1, "CRC-32 the target computed, sent with OK and with VERIFY",
                                 "[0..3] u32", "crc")]),
        ("CRC-32", "text", [[("CRC-32/ISO-HDLC: poly 0x04C11DB7 reflected, init and xor-out 0xFFFFFFFF  ·  "
                              "zlib.crc32  ·  check \"123456789\" = 0xCBF43926", "#5B6B7C")]]),
    ])
    y = card(y, "0x13", "RUN", "check the image and start it", ["BAD_LENGTH", "NO_APP"], [
        ("REQUEST", "fields", [(1, "empty", "", "empty")]),
        ("RESPONSE", "fields", [(1, "empty", "", "empty"),
                                (3, "then the target jumps to the application", "", "none")]),
    ])
    y = card(y, "0x40…0x7F", "User commands", "your own commands", [], [
        ("PAYLOADS", "text", [[("Defined by you. Same frame, CRC, SEQ, retry and reply-cache rules.", "")],
                              [("A command ID the target does not know gets ", "#5B6B7C"),
                               ("UNKNOWN_CMD", "b #C0392B"), (". IDs 0x00 … 0x3F are reserved for BootWire.",
                                                              "#5B6B7C")]]),
    ], accent="#4A6582")
    s.h = y + 10
    s.save(out / "frames" / "bootwire_command_payloads.svg", "BootWire command payloads")


# ----------------------------------------------------------------------------------------------
# 6  Flash memory map
# ----------------------------------------------------------------------------------------------
def memory_map(out: Path):
    W, H = 1040, 724
    s = Svg(W, H)
    heading(s, "Flash Memory Map",
            "Example: 256 KiB flash, 2 KiB erase blocks (the values the simulator reports in CONNECT)")
    bx, bw = 300, 230
    top, bot = 112, 596
    boot_h, vec_h = 84, 56
    vec_top, boot_top = bot - boot_h - vec_h, bot - boot_h
    app_c = (top + vec_top) / 2

    # application region, one stripe per group of erase blocks
    s.rect(bx, top, bw, vec_top - top, "#DCEBFB", "none")
    for yy in range(int(top) + 24, int(vec_top), 24):
        s.line(bx + 1, yy, bx + bw - 1, yy, "#C2D8F0", 1)
    s.rect(bx + 34, app_c - 52, bw - 68, 62, "#FFFFFF", "#9CC0E6", 1, rx=10)
    s.text(bx + bw / 2, app_c - 26, "application", 16, bold=True, fill="#173E6B", anchor="middle")
    s.text(bx + bw / 2, app_c - 7, "code and data", 12.5, fill=MUTED, anchor="middle")
    s.rect(bx + 44, app_c + 24, bw - 88, 24, "#FFFFFF", "#9CC0E6", 1, rx=12)
    s.text(bx + bw / 2, app_c + 40, "224 KiB · 112 blocks", 12, fill="#173E6B", anchor="middle")
    # vector table and bootloader
    s.rect(bx, vec_top, bw, vec_h, "#2F6DB5", "none")
    s.text(bx + bw / 2, vec_top + 24, "vector table", 14.5, bold=True, fill="#FFFFFF", anchor="middle")
    s.text(bx + bw / 2, vec_top + 43, "[0] initial SP  [4] reset | 1", 11.5, fill="#DCEBFB",
           anchor="middle", mono=True)
    s.rect(bx, boot_top, bw, boot_h, NAVY, "none")
    s.text(bx + bw / 2, boot_top + 37, "bootloader", 16, bold=True, fill="#FFFFFF", anchor="middle")
    s.text(bx + bw / 2, boot_top + 57, "32 KiB · runs first after reset", 12, fill=NAVY_SUB,
           anchor="middle")
    s.rect(bx, top, bw, bot - top, "none", NAVY, 1.6)

    # addresses
    for y, addr, name in [(top, "0x0804_0000", "end of flash = app_start + app_size"),
                          (boot_top, "0x0800_8000", "app_start"), (bot, "0x0800_0000", "flash start")]:
        s.line(bx - 14, y, bx, y, NAVY, 1.4)
        s.text(bx - 22, y + 5, addr, 14, bold=True, fill=NAVY, anchor="end", mono=True)
        s.text(bx - 22, y + 22, name, 11.5, fill=MUTED, anchor="end")

    # who may touch what: brackets on the left
    def bracket(y1, y2, colour, label, sub):
        x = 52
        s.path(f"M{x + 10},{y1 + 3} L{x},{y1 + 3} L{x},{y2 - 3} L{x + 10},{y2 - 3}", colour, 2)
        s.text(x + 18, (y1 + y2) / 2 - 3, label, 13, bold=True, fill=colour)
        s.text(x + 18, (y1 + y2) / 2 + 14, sub, 11.5, fill=MUTED)
    bracket(top, boot_top, "#2F6DB5", "BootWire may change", "ERASE · WRITE · VERIFY")
    bracket(boot_top, bot, NAVY, "protected", "BAD_PARAM")

    # rule callouts on the right, with elbow leader lines
    rx_ = bx + bw + 76
    callouts = [
        (app_c - 20, app_c - 64, "#2F6DB5", "Application region", [
            "app_start … app_start + app_size (end excluded).",
            "ERASE, WRITE and VERIFY are accepted only here,",
            "aligned to erase_block (ERASE) or write_align (WRITE).",
            "Anything outside gets BAD_PARAM."]),
        (vec_top + vec_h / 2, vec_top - 64, "#2F6DB5", "Image check before RUN", [
            "Initial SP inside RAM, reset handler inside the region",
            "with the Thumb bit set; otherwise RUN answers NO_APP.",
            "Then VTOR = app_start, set MSP, jump to reset."]),
        (boot_top + boot_h / 2, boot_top + 38, NAVY, "Bootloader (protected)", [
            "Never erased or written through BootWire:",
            "every address here gets BAD_PARAM."]),
    ]
    for ay, ty, colour, title, lines in callouts:
        ex = bx + bw + 30
        s.circle(bx + bw, ay, 4.5, colour, "#FFFFFF", 1.5)
        s.path(f"M{bx + bw + 5},{ay} L{ex},{ay} L{ex},{ty - 5} L{rx_ - 10},{ty - 5}", colour, 1.3,
               dash="4 3")
        s.text(rx_, ty, title, 14.5, bold=True, fill=colour)
        for i, ln in enumerate(lines):
            s.text(rx_, ty + 19 + i * 17, ln, 12.5, fill=INK)
    note(s, 40, 644, W - 80, [
        [("Link the application for app_start ", "b"), ("(not 0x0800_0000) and keep its vector table "
                                                        "at the start of the image.", "")],
        [("The real values come from your MCU: the target reports them in CONNECT, so the host never "
          "hard-codes them.", "#5B6B7C")]])
    s.save(out / "architecture" / "bootwire_memory_map.svg", "BootWire flash memory map")


def main(argv: list[str]) -> int:
    out = Path(argv[1] if len(argv) > 1 else "image")
    for fn in (layered_architecture, layer_encapsulation, request_frame, response_frame, wire_format,
               command_payloads, memory_map):
        fn(out)
    print(f"figures: 7 SVG files in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
