"""Render the source SVG into the Windows ICO used by the app and PyInstaller."""

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = root / "assets" / "icons" / "macroblock.svg"
    destination = root / "assets" / "icons" / "macroblock.ico"
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise RuntimeError(f"Could not render {source}")
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter, QRectF(0, 0, 256, 256))
    painter.end()
    if not image.save(str(destination), "ICO"):
        raise RuntimeError(f"Could not write {destination}")
    print(f"Generated {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
