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
- The interpreter owns graph traversal only. Built-in action callbacks live in
  a handler registry, so adding a definition and registering its behavior does
  not require changes to the canvas or interpreter core.
- Execution starts only after the focus-independent Escape monitor signals
  readiness. Holding Escape for 0.5 seconds sets the same cancellation event
  used by interruptible wait and loop operations.
- The cursor tracker is a single virtual-desktop Qt tool window with explicit
  Win32 layered, transparent, tool-window, and no-activate extended styles.
  It polls `GetCursorPos` at 16 ms intervals and never depends on application
  focus or in-window pointer events.

## Future

Ideas outside the current build prompt belong here until intentionally scoped.
