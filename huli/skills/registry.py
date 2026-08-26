"""Registro e roteamento de Skills da Huli."""

from __future__ import annotations

from huli.core.contracts import KernelHandler, KernelRequest, KernelResponse
from huli.skills.base import Skill


class DuplicateSkillError(ValueError):
    """Erro lançado quando uma Skill tenta reutilizar um nome já registrado."""


class SkillRegistry(KernelHandler):
    def __init__(self) -> None:
        self._skills: list[Skill] = []

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(skill.name for skill in self._skills)

    def register(self, skill: Skill) -> None:
        name = skill.name.strip()
        if not name:
            raise ValueError("O nome da Skill não pode estar vazio.")
        if name in self.names:
            raise DuplicateSkillError(f"A Skill '{name}' já está registrada.")
        self._skills.append(skill)

    def resolve(self, request: KernelRequest) -> Skill | None:
        for skill in self._skills:
            if skill.can_handle(request):
                return skill
        return None

    def resolve_intent(self, intent: str) -> Skill | None:
        for skill in self._skills:
            if intent in tuple(getattr(skill, "intents", ())):
                return skill
        return None

    def handle(self, request: KernelRequest) -> KernelResponse:
        skill = self.resolve(request)
        if skill is None:
            return KernelResponse(request_id=request.request_id, text="Ainda não existe uma Skill para essa solicitação nesta fase.", handled_by="skill-registry", ok=False)
        return skill.handle(request)
