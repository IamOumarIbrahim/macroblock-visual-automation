# Macroblock

Build useful Windows automations by snapping colorful blocks together—no
programming required.

![Macroblock showing a complete visual automation with connected and nested blocks](Demo.png)

[![CI](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml/badge.svg)](https://github.com/IamOumarIbrahim/macroblock/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4.svg)](https://www.microsoft.com/windows/)

## Download Macroblock

[![Download the Macroblock Setup Wizard](https://img.shields.io/badge/Download-Setup%20Wizard-2563EB?style=for-the-badge&logo=windows)](https://github.com/IamOumarIbrahim/macroblock/releases/download/v0.1.0/Macroblock-Setup-0.1.0.exe)

**[Download Macroblock Setup Wizard 0.1.0 for Windows](https://github.com/IamOumarIbrahim/macroblock/releases/download/v0.1.0/Macroblock-Setup-0.1.0.exe)**

The installer is for 64-bit Windows 10 and 11. It is approximately 46 MB.

Macroblock is a visual automation app for Windows 10 and 11. You choose an
action, place it on the canvas, change its options, and connect it to the next
action. Macroblock then follows those blocks from top to bottom.

Everything runs locally on your computer. Macroblock does not upload your
scripts, coordinates, typed text, or other automation data.

## What can I automate?

Macroblock can:

- Move, click, drag, and scroll the mouse—including previous, forward, and
  scroll-wheel buttons.
- Press, hold, release, and combine keyboard keys, or type complete text.
- Wait for a chosen amount of time and repeat a group of actions.
- Open files, folders, websites, and programs.
- Wait for a hotkey or a file to appear.
- Store simple values and make decisions with them.
- Run a PowerShell script when an advanced automation needs one.

## Install with the Setup Wizard

1. [Download the Setup Wizard](https://github.com/IamOumarIbrahim/macroblock/releases/download/v0.1.0/Macroblock-Setup-0.1.0.exe),
   then open `Macroblock-Setup-0.1.0.exe`.
2. Approve the Windows administrator prompt.
3. Follow the Setup Wizard and keep **Create a desktop icon** selected if you
   want a shortcut.
4. Select **Launch Macroblock** on the final page.

Macroblock always runs as administrator. This is required so its simulated
mouse and keyboard input works consistently with other elevated Windows apps.
Only open `.mbk` files and run PowerShell blocks that you trust.

If you are building the installer yourself, see [Build from source](#build-from-source).

## Create your first automation

1. Select a category on the left, such as **Mouse**, **Keyboard**, or
   **Timing**.
2. Drag a block onto the canvas. You can also double-click it or use the
   always-visible **ADD BLOCK** button.
3. Change the values directly inside the block.
4. Move blocks close together until the green snap preview appears, then
   release them to connect.
5. Put actions inside a Repeat block by dropping them into its open middle.
6. Select **Run Script**.
7. Hold **Esc for 0.5 seconds** whenever you need to stop the automation.

Use **Save** to create a local `.mbk` file and **Load** to reopen it later.

## Helpful controls

| What you want to do | Control |
| --- | --- |
| Move a block or connected stack | Drag its **DRAG** handle |
| Add after the newest block | Use **ADD BLOCK** or double-click a palette block |
| Duplicate one block | Hold **Left Alt** and click the block |
| Duplicate several blocks | Select them, then right-click empty canvas space |
| Record a key or key combination | Click the red dot, press the keys, then release |
| Cancel key recording | Press **Esc** or click the red dot again |
| Move around a large canvas | Hold **Space** and left-drag |
| Zoom | Use the toolbar or hold **Ctrl** and scroll |
| Stop a running automation | Hold **Esc for 0.5 seconds** |

The numbered badges and blue connection arrows show the execution order.
Blocks glow while moving, pulse when connected, and play a short wooden snap
when they lock together.

## Block categories

| Category | Includes |
| --- | --- |
| Mouse | Move, click, drag, scroll, hold, and release |
| Keyboard | Press, type, combine, hold, and release |
| Timing | Fixed and random waits |
| Control | Repeat, repeat forever, conditions, and stop |
| Variables | Set, change, and delete saved values |
| Events | Start, hotkey, and file-wait triggers |
| System | Open a path or URL, launch a program, and run PowerShell |

Coordinates outside every connected monitor are safely skipped. Macroblock
also refuses to run a script if its global Esc safety monitor cannot start.

## If something does not work

- **Windows asks for permission:** choose **Yes**. Macroblock requires
  administrator access for reliable input automation.
- **A block seems to be skipped:** check its numbered badge and blue arrow. An
  unconnected block is a separate sequence.
- **The mouse jumps too quickly:** increase **Move time** on the movement block.
- **A coordinate does nothing:** use **Show Cursor** to confirm the point is on
  a connected monitor.
- **A script will not stop:** hold **Esc**, rather than tapping it, for at least
  half a second.
- **Windows SmartScreen appears:** locally built installers are not digitally
  signed. Only continue when the installer came from this repository or a
  source you trust.

## Build from source

This section is for developers and contributors. You need Windows 10 or 11,
Git, an administrator account, and 64-bit Python 3.11 or newer.

```powershell
git clone https://github.com/IamOumarIbrahim/macroblock.git
cd macroblock
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m macroblock
```

Using the virtual environment's Python directly avoids PowerShell execution
policy changes.

### Build the portable executable

```powershell
.\scripts\build.ps1
```

This creates `dist\Macroblock.exe`. It is a single-file application with the
administrator requirement, icon, and wooden connection sound built in.

### Build the Setup Wizard

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then run:

```powershell
.\scripts\build_installer.ps1
```

The script builds the application first and then creates
`dist\installer\Macroblock-Setup-<version>.exe`. To reuse an existing
`dist\Macroblock.exe`, add `-SkipAppBuild`.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The automated suite does not perform live clicks. The optional Windows
verification scripts in `tests` briefly take input focus and should only be
run when that is safe.

## Project layout

- `src/macroblock/blocks`: block definitions and saved-script graph
- `src/macroblock/ui`: palette, block editors, canvas, and main window
- `src/macroblock/engine`: script runner and Windows input simulation
- `src/macroblock/overlay`: click-through cursor crosshair
- `src/macroblock/persistence`: local `.mbk` save and load
- `installer`: Inno Setup Wizard definition
- `docs/ARCHITECTURE.md`: technical design decisions

## Contributing, help, and license

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before
opening a pull request. Use [SUPPORT.md](SUPPORT.md) for help and
[SECURITY.md](SECURITY.md) for security-sensitive reports. Everyone
participating in the project must follow the [Code of Conduct](CODE_OF_CONDUCT.md).

Macroblock is available under the [MIT License](LICENSE).
