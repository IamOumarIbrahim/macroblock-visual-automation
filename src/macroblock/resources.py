"""Resolve repository assets both from source and a PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(*parts: str) -> Path:
    if bundle_root := getattr(sys, "_MEIPASS", None):
        return Path(bundle_root) / "assets" / Path(*parts)
    return Path(__file__).resolve().parents[2] / "assets" / Path(*parts)
