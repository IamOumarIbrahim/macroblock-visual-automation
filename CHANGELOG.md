# Changelog

All notable changes to Macroblock will be documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and releases use
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Reworked the README around a complete application demo and plain-language
  install, first-automation, control, safety, and troubleshooting guidance.

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
- Blocks now have an explicit drag grip, sequence number, animated drag glow,
  combination pulse, audible connection cue, and high-contrast link arrow.
- Added canvas zoom controls, Ctrl+wheel zoom, Space+left-drag panning, improved
  scrollbars, gesture hints, and clearer live status messages.
- Macroblock now requires elevation both from source and through the packaged
  executable's UAC administrator manifest.
- Mouse movement blocks now expose an editable glide time so consecutive
  destinations remain visibly distinct inside fast or repeated sequences.
- Replaced the Windows system-alert connection sound with a bundled,
  deterministic wooden toy-block snap.

### Fixed

- Restored movement for blocks containing QWidget editors without stealing
  clicks from text, choice, or numeric inputs.
- Fixed A-Z, 0-9, function-key, arrow-key, and key-combination resolution in
  the Win32 input layer.
- Fixed unresponsive numeric up/down buttons embedded in canvas blocks.
- Fixed clipped mouse-button dropdowns and added functional previous, forward,
  and scroll-wheel button choices to click, hold, and release blocks.
- Added regression coverage for repeated Wait -> Move -> Move chains so every
  cursor destination executes in order.

### Added

- Added a versioned Inno Setup 6 wizard with Start Menu and desktop shortcuts,
  launch-after-install, administrator installation, and a reproducible
  PowerShell build command.

- Alt+click duplication, block context-menu duplication, multi-selection
  duplication from the canvas, and palette double-click auto-add.
- Relative mouse movement, mouse/key hold and release, randomized waits,
  variable conditions/deletion, functional hotkey and file-wait events.
- A System category with editable Open File/Folder, Open URL, Launch Program,
  and multiline Run PowerShell Script blocks.
- Data-driven Mouse, Keyboard, Timing, Control, Variables, and Events blocks.
- Scratch-style drag palette, canvas positioning, snapping, inline parameter
  editing, disconnecting, and deletion.
- Background Win32 input execution with mandatory global hold-Esc abort.
- Per-Monitor-V2 coordinate handling and off-monitor action warnings.
- Topmost, layered, click-through live cursor crosshair.
- Versioned, atomic, local-only `.mbk` persistence with clear validation errors.
- Reproducible single-file Windows packaging with PyInstaller.
- Red in-block keystroke recorders for Key Combo, Hold Key, and Release Key;
  successful recordings replace the existing value while cancel keeps it.

[Unreleased]: https://github.com/IamOumarIbrahim/macroblock/commits/main
