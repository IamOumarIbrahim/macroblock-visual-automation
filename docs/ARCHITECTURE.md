# Architecture

Macroblock uses a `src`-layout Python package. UI, block definitions,
execution, overlay, and persistence are isolated so each subsystem can evolve
behind a small interface.

## Decisions

- Python 3.11+ with PySide6 is the fixed application stack.
- Win32-specific behavior is isolated under `engine` and `overlay`.
- A startup call declares Per-Monitor-V2 DPI awareness before creating Qt.
- Script graphs are directed top-to-bottom chains. Container blocks have a
  `child` reference to the first block in their body, so control blocks can be
  nested without introducing graph cycles.
- Canvas positions are optional block metadata in the versioned document. They
  do not affect execution, but preserving them makes a save/load round trip
  restore the visual program exactly.

## Future

Ideas outside the current build prompt belong here until intentionally scoped.
