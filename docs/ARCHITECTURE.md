# Architecture

Macroblock uses a `src`-layout Python package. UI, block definitions,
execution, overlay, and persistence are isolated so each subsystem can evolve
behind a small interface.

## Decisions

- Python 3.11+ with PySide6 is the fixed application stack.
- Win32-specific behavior is isolated under `engine` and `overlay`.
- A startup call declares Per-Monitor-V2 DPI awareness before creating Qt.

## Future

Ideas outside the current build prompt belong here until intentionally scoped.

