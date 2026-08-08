# Macroblock

[![CI](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml/badge.svg)](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)

Macroblock is an open-source Windows desktop application for building local
mouse and keyboard automations from color-coded, Scratch-style blocks. Drag a
block from the categorized palette, edit values directly on the block, snap it
into a sequence, and run the result without writing code.

## Features

- Mouse movement, clicks, drags, and scrolling through Win32 `SendInput`
- Key presses, Unicode text, and key combinations
- Waits, counted and until-stopped loops, variables, and event entry blocks
- A global safety abort: hold **Esc for 0.5 seconds** while a script is running
- A topmost, click-through crosshair with live physical-pixel coordinates
- Versioned, local-only `.mbk` save files
- Per-Monitor-V2 DPI awareness for mixed-DPI and multi-monitor desktops

Macroblock never uploads or transmits scripts. Coordinates, typed text, and all
other automation data remain in the save files you choose on your computer.

## Install and run from source

Requirements: Windows 10 or 11, Git, and 64-bit Python 3.11 or newer.

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

1. Choose a category at left and drag blocks onto the canvas.
2. Drop a block near the bottom of another to snap-connect them.
3. Edit numbers, text, choices, and key lists directly on each block.
4. Select a block and press Delete, or right-click it to disconnect/delete.
5. Choose **Run Script**. Hold **Esc for 0.5 seconds** at any time to abort.
6. Use **Show Cursor** to read screen coordinates without blocking clicks.
7. Save and load local scripts with the `.mbk` format.

Coordinates outside every connected monitor are skipped and logged instead of
being sent. Macroblock also refuses to start execution if its global abort
monitor cannot be activated.

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
the destination Windows machine.

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
