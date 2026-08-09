# Contributing to Macroblock

Thank you for helping improve Macroblock. Contributions of code, tests,
documentation, accessibility fixes, and reproducible bug reports are welcome.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Security vulnerabilities must be reported privately as described in
[SECURITY.md](SECURITY.md), not in a public issue.

## Before starting

- Search existing issues and pull requests to avoid duplicate work.
- Open an issue before a large UI, data-model, or execution-engine change.
- Keep pull requests focused on one problem.
- Put out-of-scope ideas in `docs/ARCHITECTURE.md` under **Future**.

Small fixes and documentation improvements do not need a proposal first.

## Development setup

Macroblock is a Windows application. Use Windows 10 or 11 and Python 3.11 or
newer:

```powershell
git clone https://github.com/IamOumarIbrahim/macroblock-visual-automation.git
cd macroblock
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
```

Run the application with:

```powershell
.\.venv\Scripts\python.exe -m macroblock
```

## Safety invariants

Changes must preserve these guarantees:

- A script never starts until the global abort monitor is active.
- Automation execution never runs on the UI thread.
- The cursor overlay remains layered, click-through, topmost, and nonfocusable.
- Mouse coordinates are physical pixels and off-monitor coordinates are logged
  and skipped.
- `.mbk` scripts stay local and unknown block types fail with a clear message.
- New block UI is driven by the block registry; do not add type-specific canvas
  logic.

Changes to input simulation, abort behavior, persistence, DPI handling, or the
overlay need tests for both the normal and failure paths.

## Tests and verification

Run the normal noninteractive suite before every pull request:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The explicit Windows scripts generate real input or change focus. Run the ones
relevant to your change only when it is safe for them to control the desktop:

```powershell
.\.venv\Scripts\python.exe tests\verify_phase3_windows.py
.\.venv\Scripts\python.exe tests\verify_phase4_windows.py
.\.venv\Scripts\python.exe tests\verify_phase5_reopen.py
```

Packaging changes must also pass:

```powershell
.\scripts\build.ps1
```

Then launch `dist\Macroblock.exe` without an activated virtual environment.

## Pull requests

Use a short imperative title and explain:

- what changed and why;
- safety or compatibility implications;
- exact verification commands and results;
- screenshots for visible UI changes.

Do not commit `.venv`, `build`, `dist`, generated `.mbk` scripts, credentials,
or private automation data. Maintainers may ask for a smaller change or
additional verification before merging.
