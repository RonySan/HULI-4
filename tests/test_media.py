"""Controles de mídia validados sem abrir aplicativos ou tocar áudio."""

from huli.core import KernelRequest
from huli.infrastructure.media import MediaControlError, WindowsMediaController
from huli.skills.media_skill import MediaSkill


def build_controller(*, desktop_available: bool = True):
    opened: list[str] = []
    commands: list[int] = []
    waits: list[float] = []
    controller = WindowsMediaController(
        uri_opener=opened.append,
        command_sender=commands.append,
        spotify_protocol_available=lambda: desktop_available,
        sleeper=waits.append,
        platform_name="win32",
    )
    return controller, opened, commands, waits


def test_favorites_opens_only_fixed_spotify_uri_then_plays() -> None:
    controller, opened, commands, waits = build_controller()

    controller.play_favorites()

    assert opened == ["spotify:collection:tracks"]
    assert commands == [46]
    assert waits == [2.0]


def test_favorites_uses_spotify_web_when_desktop_is_absent() -> None:
    controller, opened, commands, waits = build_controller(desktop_available=False)

    controller.play_favorites()

    assert opened == ["https://open.spotify.com/collection/tracks"]
    assert commands == []
    assert waits == []


def test_media_controls_use_distinct_windows_commands() -> None:
    controller, _opened, commands, _waits = build_controller()

    controller.play()
    controller.pause()
    controller.stop()
    controller.next()
    controller.previous()

    assert commands == [46, 47, 13, 11, 12]


def test_media_skill_handles_user_favorites_request() -> None:
    controller, opened, commands, _waits = build_controller()
    skill = MediaSkill(controller)
    request = KernelRequest.from_text(
        "pode tocar as minhas favoritas",
        metadata={"intent": "media.favorites"},
    )

    response = skill.handle(request)

    assert response.ok
    assert response.handled_by == "media"
    assert "Spotify" in response.text
    assert opened == ["spotify:collection:tracks"]
    assert commands == [46]


def test_media_controller_refuses_unsupported_platform() -> None:
    controller = WindowsMediaController(platform_name="linux")

    try:
        controller.play()
    except MediaControlError as exc:
        assert "Windows" in str(exc)
    else:
        raise AssertionError("O controle deveria recusar plataforma não suportada.")
