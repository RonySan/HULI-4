"""Skill de resumo diário da Huli."""

from __future__ import annotations

from huli.brain.daily_summary import DailySummaryService
from huli.core.contracts import KernelRequest, KernelResponse


class DailySummarySkill:
    name = "daily-summary"
    intents = ("daily.summary",)

    def __init__(self, service: DailySummaryService) -> None:
        self.service = service

    def can_handle(self, request: KernelRequest) -> bool:
        return str(request.metadata.get("intent", "")) in self.intents

    def handle(self, request: KernelRequest) -> KernelResponse:
        project = str(request.metadata.get("active_project") or "").strip() or None
        return KernelResponse(request_id=request.request_id, text=self.service.build(project=project), handled_by=self.name)
