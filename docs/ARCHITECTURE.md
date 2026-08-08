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
  nested without introducing graph cycles. Validation enforces one incoming
  reference per block and rejects cycles before layout or execution.
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
  focus or in-window pointer events. Its native rectangle is set from Win32's
  physical virtual-screen metrics; physical cursor coordinates are divided by
  the window device-pixel ratio only at the QPainter boundary.
- `.mbk` files are versioned UTF-8 JSON and remain entirely local. Saves use a
  same-directory temporary file plus `os.replace` so interruption cannot leave
  a partially written destination. Loading validates every block and reference
  before replacing the current canvas.
- The canvas keeps a transient `last_added_id` for the toolbar's append flow.
  Drag-and-drop remains free-positioned, but both palette drops and existing
  block moves share one proximity-snap function. Drag hotspots are stored in
  MIME data so the block lands under the preview instead of under its corner.
- A snap destination identifies both an owner and a reference kind: `next`
  inserts into the surrounding sequence, while `child` enters an empty
  container. Filled cavities resolve to the tail of their child chain. The
  recursive layout pass sizes each C-shaped container around the full bounds
  of its child sequence, so nesting composes at arbitrary depth.
- Connection edits preserve structure. A dropped stack is inserted ahead of
  an occupied reference, moving a head translates all reachable descendants,
  and deletion splices the surrounding `next` chain while leaving container
  children as an independent root.

## Future

Ideas outside the current build prompt belong here until intentionally scoped:

- User-configurable abort keys and event-hotkey registration
- Conditional branches and comparison blocks
- Undo/redo for canvas editing
- Image recognition and window-relative coordinates
- Importable block packs using the public registry/handler extension points
