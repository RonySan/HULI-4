"""Testes do sistema de Skills da fundação."""

import pytest

from huli.core import Kernel, KernelRequest
from huli.skills import DuplicateSkillError, FoundationSkill, SkillRegistry


def build_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(FoundationSkill())
    return registry


def test_registry_registers_and_lists_skill() -> None:
    registry = build_registry()
    assert registry.names == ("foundation",)


def test_registry_rejects_duplicate_skill_name() -> None:
    registry = build_registry()
    with pytest.raises(DuplicateSkillError):
        registry.register(FoundationSkill())


def test_registry_routes_known_request() -> None:
    registry = build_registry()
    request = KernelRequest.from_text("ping")
    response = registry.handle(request)
    assert response.request_id == request.request_id
    assert response.handled_by == "foundation"
    assert response.ok is True


def test_registry_returns_controlled_fallback_for_unknown_request() -> None:
    registry = build_registry()
    request = KernelRequest.from_text("comando que ainda nao existe")
    response = registry.handle(request)
    assert response.handled_by == "skill-registry"
    assert response.ok is False


def test_kernel_delegates_to_registry_without_knowing_skill() -> None:
    kernel = Kernel(handler=build_registry())
    response = kernel.process("status huli")
    assert response.handled_by == "foundation"
