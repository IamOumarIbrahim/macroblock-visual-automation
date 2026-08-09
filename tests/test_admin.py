from pathlib import Path

import macroblock.main as app_main


def test_elevated_process_is_accepted(monkeypatch) -> None:
    monkeypatch.setattr(app_main.sys, "platform", "win32")
    monkeypatch.setattr(app_main, "is_administrator", lambda: True)

    assert app_main.ensure_administrator() is True


def test_packaged_executable_embeds_admin_manifest() -> None:
    build_script = Path("scripts/build.ps1").read_text(encoding="utf-8")

    assert "--uac-admin" in build_script
