"""Render the existing BootWire SVG into desktop icon formats.

Run with desktop/.venv/bin/python scripts/render_icons.py.
Requires the GUI extra; ImageMagick's `magick` command writes the multi-size ICO.
"""
from pathlib import Path
import subprocess
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

source = Path(__file__).resolve().parents[1] / 'desktop/src/bootwire_gui/assets/bootwire.svg'
renderer = QSvgRenderer(str(source))
if not renderer.isValid():
    raise SystemExit(f'Invalid SVG: {source}')
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
renderer.render(painter, QRectF(0, 0, 256, 256))
painter.end()
if not image.save(str(source.with_suffix('.png'))):
    raise SystemExit('Could not save PNG icon')
subprocess.run(['magick', str(source.with_suffix('.png')), '-define',
                'icon:auto-resize=256,128,64,48,32,16', str(source.with_suffix('.ico'))], check=True)
print('Rendered BootWire PNG and multi-resolution ICO from the existing mark.')
