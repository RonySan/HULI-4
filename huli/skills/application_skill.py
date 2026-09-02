"""Skill para abrir aplicativos instalados sem executar comandos arbitrários."""

from __future__ import annotations

import re

from huli.core.contracts import KernelRequest, KernelResponse
from huli.infrastructure.applications import ApplicationLaunchError, ApplicationLauncher
from huli.skills.parsing import strip_huli_prefix


def extract_application_name(text: str) -> str:
    value = strip_huli_prefix(text)
    value = re.sub(
        r"^(?:abra|abre|abrir|inicie|iniciar|execute|executar|rode|rodar)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(
        r"^(?:(?:o|a)\s+)?(?:programa|aplicativo|app)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\s+por\s+favor\s*$", "", value, flags=re.IGNORECASE)
    return " ".join(value.split()).strip(" .,!?")


class ApplicationSkill:
    name = "applications"
    intents = ("app.open",)

    def __init__(self, launcher: ApplicationLauncher) -> None:
        self.launcher = launcher

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent") or "") in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        requested_name = extract_application_name(request.text)
        try:
            application = self.launcher.launch(requested_name)
        except ApplicationLaunchError as exc:
            return KernelResponse(
                request_id=request.request_id,
                text=str(exc),
                handled_by=self.name,
                ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text=f"Abrindo {application.name}.",
            handled_by=self.name,
        )


__all__ = ["ApplicationSkill", "extract_application_name"]
