# Changelog

All notable changes to Macroblock will be documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Added an always-visible **ADD BLOCK** menu that appends each selection to the
  last-added block while leaving the first block unconnected.
- Improved palette dragging with a visible drag preview, hotspot-correct drop
  placement, live snap-ready feedback, and automatic proximity snapping.
- Redesigned canvas blocks with rounded LEGO-like tabs and sockets over a
  subtle dotted workspace pattern.
- Added recursively expanding C-shaped loop blocks with explicit inside and
  after-loop drop targets, including visual support for nested loops.
- Connected stacks now move together; occupied connectors insert without
  orphaning their old chain, and deletion repairs surrounding connections.
- Strengthened document validation for cycles, multiple parents, malformed
  block entries, non-finite values/positions, and shared mutable defaults.

### Added

- Data-driven Mouse, Keyboard, Timing, Control, Variables, and Events blocks.
- Scratch-style drag palette, canvas positioning, snapping, inline parameter
  editing, disconnecting, and deletion.
- Background Win32 input execution with mandatory global hold-Esc abort.
- Per-Monitor-V2 coordinate handling and off-monitor action warnings.
- Topmost, layered, click-through live cursor crosshair.
- Versioned, atomic, local-only `.mbk` persistence with clear validation errors.
- Reproducible single-file Windows packaging with PyInstaller.

[Unreleased]: https://github.com/IamOumarIbrahim/macroblock/commits/main
