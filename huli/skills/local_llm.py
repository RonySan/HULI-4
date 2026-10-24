"""Resposta conversacional local via Ollama, sem execução de ferramentas.

A Skill só recebe intenções 'unknown'. Comandos existentes continuam
sendo tratados pelo roteador determinístico da Huli.
"""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from huli.core.contracts import KernelRequest, KernelResponse
from huli.security.privacy import contains_secret_text, is_private_journal_text

_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
_SYSTEM_PROMPT = (
    "Você é H.U.L.I., assistente pessoal de Rony. Responda em português do Brasil "
    "de maneira útil, objetiva e cordial. Você conversa, mas não tem acesso a "
    "ferramentas, contas, arquivos, Spotify nem comandos do computador nesta "
    "etapa. Nunca diga que abriu programas, tocou música, salvou dados ou "
    "executou ações. Se pedirem uma ação, explique que ela precisa da "
    "integração correspondente. Não invente informações pessoais."
)


class OllamaUnavailable(RuntimeError):
    """O modelo local não respondeu adequadamente."""


class LocalLLMSkill:
    name = "ollama-chat"
    intents = ("unknown",)

    def __init__(self, model: str, timeout_seconds: int = 45) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9._-]+)?", model):
            raise ValueError("HULI_LLM_MODEL contém caracteres inválidos.")
        if not 2 <= timeout_seconds <= 180:
            raise ValueError("Tempo limite do Ollama inválido.")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def can_handle(self, request: KernelRequest) -> bool:
        return request.metadata.get("intent") == "unknown"

    def handle(self, request: KernelRequest) -> KernelResponse:
        if not self.can_handle(request):
            return KernelResponse(
                request_id=request.request_id,
                text="Esta capacidade é apenas para conversas sem comando reconhecido.",
                handled_by=self.name,
                ok=False,
            )
        if is_private_journal_text(request.text) or contains_secret_text(request.text):
            return KernelResponse(
                request_id=request.request_id,
                text="Para proteger sua privacidade, não envio diários ou segredos ao modelo.",
                handled_by=self.name,
                ok=False,
            )
        try:
            answer = self._generate(request.text[:4000])
        except (OllamaUnavailable, HTTPError, URLError, TimeoutError, OSError, ValueError):
            return KernelResponse(
                request_id=request.request_id,
                text=(
                    "Não consegui consultar a IA local. Verifique se o Ollama está "
                    "aberto no computador principal e se o modelo foi instalado."
                ),
                handled_by=self.name,
                ok=False,
            )
        return KernelResponse(
            request_id=request.request_id,
            text=answer[:2500],
            handled_by=self.name,
        )

    def _generate(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "system": _SYSTEM_PROMPT,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.4, "num_predict": 256},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            _OLLAMA_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Não usa proxies do sistema e não aceita uma URL remota configurável.
        with build_opener(ProxyHandler({})).open(request, timeout=self.timeout_seconds) as response:
            raw = response.read(131073)
        if len(raw) > 131072:
            raise OllamaUnavailable("Resposta do Ollama excedeu o limite.")
        result = json.loads(raw.decode("utf-8"))
        answer = result.get("response") if isinstance(result, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise OllamaUnavailable("Resposta do Ollama vazia.")
        return answer.strip()
