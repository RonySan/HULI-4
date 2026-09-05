"""Abertura segura de aplicativos sem iniciar processos durante os testes."""

from pathlib import Path

import pytest

from huli.core import KernelRequest
from huli.infrastructure.applications import ApplicationLaunchError, ApplicationLauncher
from huli.skills.application_skill import ApplicationSkill, extract_application_name


def build_launcher(tmp_path: Path):
    chrome = tmp_path / "Google Chrome.lnk"
    calculator = tmp_path / "calc.exe"
    spotify = tmp_path / "spotify_cli.exe"
    chrome.touch()
    calculator.touch()
    spotify.touch()
    opened: list[str] = []
    launcher = ApplicationLauncher(
        start_menu_roots=(tmp_path,),
        aliases={"calculadora": calculator, "spotify_cli": spotify},
        opener=opened.append,
        platform_name="win32",
    )
    return launcher, chrome, calculator, opened


def test_launcher_resolves_start_menu_and_safe_alias(tmp_path: Path) -> None:
    launcher, chrome, calculator, opened = build_launcher(tmp_path)

    assert launcher.launch("chrome").target == chrome.resolve()
    assert launcher.launch("calculadora").target == calculator.resolve()
    assert opened == [str(chrome.resolve()), str(calculator.resolve())]


def test_spoken_spotify_alias_resolves_only_inside_application_launcher(
    tmp_path: Path,
) -> None:
    launcher, _chrome, _calculator, opened = build_launcher(tmp_path)

    application = launcher.launch("esporte pai")

    assert application.name == "Spotify"
    assert application.target.name == "spotify_cli.exe"
    assert opened == [str(application.target)]

    plural = launcher.launch("esportes pai")
    assert plural.name == "Spotify"


def test_spotify_uses_fixed_web_fallback_when_desktop_is_absent(
    tmp_path: Path,
) -> None:
    opened: list[str] = []
    launcher = ApplicationLauncher(
        start_menu_roots=(tmp_path,),
        aliases={},
        opener=opened.append,
        platform_name="win32",
    )

    application = launcher.launch("esporte pai")

    assert application.name == "Spotify Web"
    assert application.source == "fallback web"
    assert application.target == "https://open.spotify.com"
    assert opened == ["https://open.spotify.com"]


def test_spotify_ignores_empty_windows_execution_alias(tmp_path: Path) -> None:
    windows_apps = tmp_path / "Microsoft" / "WindowsApps"
    windows_apps.mkdir(parents=True)
    stale_alias = windows_apps / "spotify_cli.exe"
    stale_alias.touch()
    opened: list[str] = []
    launcher = ApplicationLauncher(
        start_menu_roots=(tmp_path,),
        aliases={"spotify_cli": stale_alias},
        opener=opened.append,
        platform_name="win32",
    )

    application = launcher.launch("spotify")

    assert application.name == "Spotify Web"
    assert opened == ["https://open.spotify.com"]


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
    assert extract_application_name("abrir o esporte pai") == "esporte pai"


def test_application_skill_explains_spotify_web_fallback(tmp_path: Path) -> None:
    opened: list[str] = []
    launcher = ApplicationLauncher(
        start_menu_roots=(tmp_path,),
        aliases={},
        opener=opened.append,
        platform_name="win32",
    )
    skill = ApplicationSkill(launcher)
    request = KernelRequest.from_text(
        "abrir esporte pai",
        metadata={"intent": "app.open"},
    )

    response = skill.handle(request)

    assert response.ok
    assert response.text == (
        "O aplicativo do Spotify não está instalado no Windows; "
        "abrindo o Spotify Web."
    )
    assert opened == ["https://open.spotify.com"]
