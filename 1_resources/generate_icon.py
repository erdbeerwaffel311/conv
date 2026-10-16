"""Generate high-res macOS AppIcon.icns using PyQt6 and macOS iconutil."""

import os
import subprocess
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QImage,
    QPainter,
    QPainterPath,
    QColor,
    QLinearGradient,
    QFont,
    QPen,
)
from PyQt6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication([])

size = 1024
img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
img.fill(Qt.GlobalColor.transparent)

painter = QPainter(img)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

# macOS Big Sur / Sonoma style squircle
margin = 80
rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
radius = 200

path = QPainterPath()
path.addRoundedRect(rect, radius, radius)

# Gradient background (Vibrant Indigo to Cyan)
grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
grad.setColorAt(0.0, QColor("#1e1b4b"))  # Deep Indigo
grad.setColorAt(0.4, QColor("#3b82f6"))  # Blue
grad.setColorAt(1.0, QColor("#06b6d4"))  # Cyan

painter.fillPath(path, grad)

# Subtle inner border
pen = QPen(QColor(255, 255, 255, 40), 6)
painter.strokePath(path, pen)

# Center Icon: Symbol ⚡ / 🔄 / 🎬
font = QFont("-apple-system", 340, QFont.Weight.Bold)
painter.setFont(font)
painter.setPen(QColor(255, 255, 255, 240))
painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "⚡")

painter.end()

# Save master PNG
res_dir = os.path.dirname(os.path.abspath(__file__))
master_png = os.path.join(res_dir, "icon_1024.png")
img.save(master_png)

# Create iconset
iconset_dir = os.path.join(res_dir, "AppIcon.iconset")
os.makedirs(iconset_dir, exist_ok=True)

icon_sizes = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]

for s, name in icon_sizes:
    out_file = os.path.join(iconset_dir, name)
    subprocess.run(["sips", "-z", str(s), str(s), master_png, "--out", out_file], check=True, stdout=subprocess.DEVNULL)

# Convert iconset to icns
icns_path = os.path.join(res_dir, "AppIcon.icns")
subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_path], check=True)
print("Created:", icns_path)
