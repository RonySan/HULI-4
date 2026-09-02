"""Abertura segura de aplicativos sem iniciar processos durante os testes."""

from pathlib import Path

import pytest

from huli.core import KernelRequest
from huli.infrastructure.applications import ApplicationLaunchError, ApplicationLauncher
from huli.skills.application_skill import ApplicationSkill, extract_application_name


def build_launcher(tmp_path: Path):
    chrome = tmp_path / "Google Chrome.lnk"
    calculator = tmp_path / "calc.exe"
    chrome.touch()
    calculator.touch()
    opened: list[str] = []
    launcher = ApplicationLauncher(
        start_menu_roots=(tmp_path,),
        aliases={"calculadora": calculator},
        opener=opened.append,
        platform_name="win32",
    )
    return launcher, chrome, calculator, opened


def test_launcher_resolves_start_menu_and_safe_alias(tmp_path: Path) -> None:
    launcher, chrome, calculator, opened = build_launcher(tmp_path)

    assert launcher.launch("chrome").target == chrome.resolve()
    assert launcher.launch("calculadora").target == calculator.resolve()
    assert opened == [str(chrome.resolve()), str(calculator.resolve())]


@pytest.mark.parametrize(
    "query",
    (
        r"C:\Windows\System32\cmd.exe",
        "teste.ps1",
        "chrome & apagar dados",
        "https://example.com",
    ),
)
def test_launcher_rejects_paths_scripts_urls_and_shell_syntax(
    tmp_path: Path,
    query: str,
) -> None:
    launcher, _chrome, _calculator, opened = build_launcher(tmp_path)

    with pytest.raises(ApplicationLaunchError, match="segurança"):
        launcher.launch(query)

    assert opened == []


def test_launcher_suggests_close_installed_name(tmp_path: Path) -> None:
    launcher, _chrome, _calculator, _opened = build_launcher(tmp_path)

    with pytest.raises(ApplicationLaunchError, match="Google Chrome"):
        launcher.launch("gogle crome")


def test_application_skill_extracts_and_opens_by_name(tmp_path: Path) -> None:
    launcher, chrome, _calculator, opened = build_launcher(tmp_path)
    skill = ApplicationSkill(launcher)
    request = KernelRequest.from_text(
        "abrir o programa Google Chrome por favor",
        metadata={"intent": "app.open"},
    )

    response = skill.handle(request)

    assert response.ok
    assert response.text == "Abrindo Google Chrome."
    assert opened == [str(chrome.resolve())]
    assert extract_application_name("Huli, abra o aplicativo Paint") == "Paint"
