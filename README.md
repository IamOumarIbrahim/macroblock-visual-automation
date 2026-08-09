# Macroblock

[![CI](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml/badge.svg)](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)

Macroblock is an open-source Windows desktop application for building local
mouse and keyboard automations from color-coded, Scratch-style blocks. Drag a
block from the categorized palette, edit values directly on the block, snap it
into a sequence, and run the result without writing code.

## Features

- Smooth or instant mouse movement, five-button clicks/holds/releases, drags,
  and scrolling through Win32 `SendInput`
- Key presses, Unicode text, key combinations, and in-block chord recording
- Waits, counted and until-stopped loops, variables, and event entry blocks
- Expandable C-shaped loops that visibly encapsulate complete block stacks,
  including other nested loops
- Numbered blocks, high-contrast connection arrows, snap previews, drag glow,
  combination pulse/wooden-snap feedback, zooming, and space-drag panning
- Duplicate one block with Alt+click, or duplicate a multi-selection while
  preserving its internal links
- System automation for files, folders, URLs, programs, and multiline
  PowerShell scripts
- A global safety abort: hold **Esc for 0.5 seconds** while a script is running
- A topmost, click-through crosshair with live physical-pixel coordinates
- Versioned, local-only `.mbk` save files
- Per-Monitor-V2 DPI awareness for mixed-DPI and multi-monitor desktops

Macroblock never uploads or transmits scripts. Coordinates, typed text, and all
other automation data remain in the save files you choose on your computer.

## Install and run from source

Requirements: Windows 10 or 11, Git, 64-bit Python 3.11 or newer, and an
administrator account. Macroblock always requests elevation at startup because
input injection and system automation must run at a consistent integrity level.

```powershell
git clone https://github.com/IamOumarIbrahim/macroblock.git
cd macroblock
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m macroblock
```

Using the virtual environment's Python directly avoids PowerShell execution
policy changes. Contributors who prefer activation can instead run
`.\.venv\Scripts\Activate.ps1`, followed by `python -m macroblock`.

## Use

1. Choose a category at left and drag blocks onto the canvas, or use the
   always-visible **ADD BLOCK** menu. Double-clicking a palette block also adds
   it after the last canvas block.
2. **ADD BLOCK** appends to the last block automatically. Dragged blocks show a
   green snap preview when they are close enough to interlock.
3. Drag a block into a loop's open cavity to nest it. The loop expands around
   its child stack; drop at its lower connector to place the block after it.
4. Moving a connected block moves its entire child/next stack. Dropping on an
   occupied connector inserts the stack without discarding existing blocks.
5. Use the visible **DRAG** grip to reposition a block stack. Hold Space and
   left-drag the canvas to pan; use Ctrl+wheel or the toolbar to zoom.
6. Alt+click a block to duplicate it. For several blocks, select them and
   right-click empty canvas space to duplicate the selection and its links.
7. Edit numbers, text, choices, key lists, paths, URLs, and multiline scripts
   directly on each block. The arrow buttons on numeric fields increment and
   decrement their value. The red dot on Key Combo, Hold Key, and Release Key
   records and replaces the current key value; press Esc to cancel recording.
8. Select a block and press Delete, or right-click it for duplicate,
   disconnect, and delete operations.
9. Choose **Run Script**. A **When Hotkey Pressed** entry waits for its hotkey;
   hold **Esc for 0.5 seconds** at any time to abort.
10. Use **Show Cursor** to read screen coordinates without blocking clicks.
11. Save and load local scripts with the `.mbk` format.

## Built-in automation blocks

- **Mouse:** smooth absolute/relative movement, five-button click/hold/release
  (including previous, forward, and wheel click), drag, and scroll
- **Keyboard:** key press, text entry, key combinations, and key hold/release
- **Timing:** fixed and randomized interruptible waits
- **Control:** counted/forever loops, variable conditions, and stop
- **Variables:** set, change, and delete
- **Events:** script start, hotkey entry/wait, and wait until a file exists
- **System:** open a file/folder, open a URL, launch a program, and run a
  multiline PowerShell script

Coordinates outside every connected monitor are skipped and logged instead of
being sent. Macroblock also refuses to start execution if its global abort
monitor cannot be activated.

System and PowerShell blocks intentionally run with Macroblock's elevated
permissions. Only open `.mbk` files and run scripts you trust.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The normal suite does not simulate live clicks or Alt+Tab. The explicit Windows
verification scripts are:

```powershell
.\.venv\Scripts\python.exe tests\verify_phase3_windows.py
.\.venv\Scripts\python.exe tests\verify_phase4_windows.py
.\.venv\Scripts\python.exe tests\verify_phase5_reopen.py
```

These scripts briefly take input focus, so run them only when that is safe.

## Build the single-file executable

After installing the development dependencies:

```powershell
.\scripts\build.ps1
```

The reproducible build script regenerates the icon and writes
`dist\Macroblock.exe`. PyInstaller bundles Python and all runtime dependencies;
the resulting executable does not require Python or a virtual environment on
the destination Windows machine. Its embedded manifest requires administrator
elevation, so Windows displays a UAC prompt before the application opens.

## Project structure

- `src/macroblock/blocks`: data-driven definitions and graph model
- `src/macroblock/ui`: palette, inline editors, canvas, and main window
- `src/macroblock/engine`: interpreter, safety monitor, and Win32 input
- `src/macroblock/overlay`: click-through cursor crosshair
- `src/macroblock/persistence`: atomic local `.mbk` save/load
- `docs/ARCHITECTURE.md`: design decisions and future ideas

Macroblock is available under the MIT License.

## Contributing and support

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening a pull request, use [SUPPORT.md](SUPPORT.md) for help, and report
security-sensitive issues according to [SECURITY.md](SECURITY.md). Everyone
participating in the project must follow the [Code of Conduct](CODE_OF_CONDUCT.md).
