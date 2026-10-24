"""Regressão do cérebro Ollama opcional e sem ferramentas."""

import json
from pathlib import Path
from urllib.error import URLError

from fastapi.testclient import TestClient

from huli.api import create_app
from huli.bootstrap import build_runtime
from huli.infrastructure import Settings
from huli.skills.local_llm import LocalLLMSkill


def _runtime(tmp_path: Path, *, enabled: bool, remote: bool = False):
    return build_runtime(
        Settings(
            environment="test",
            log_level="CRITICAL",
            data_dir=tmp_path,
            llm_enabled=enabled,
            remote_access_enabled=remote,
        )
    )


def test_ollama_disabled_by_default(tmp_path: Path):
    runtime = _runtime(tmp_path, enabled=False)
    assert "ollama-chat" not in runtime.skills.names
    answer = runtime.kernel.process("xyzzy inexplicavel 98765")
    assert answer.handled_by == "brain-dispatcher"


def test_ollama_answer_only_for_unknown_intent(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, enabled=True)
    monkeypatch.setattr(LocalLLMSkill, "_generate", lambda self, text: "Resposta local de teste.")
    unknown = runtime.kernel.process("xyzzy inexplicavel 98765")
    assert unknown.ok is True
    assert unknown.handled_by == "ollama-chat"
    assert unknown.text == "Resposta local de teste."
    known = runtime.kernel.process("ping")
    assert known.handled_by != "ollama-chat"


def test_ollama_failure_is_safely_reported(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, enabled=True)

    def offline(self, text):
        raise URLError("detalhes internos")

    monkeypatch.setattr(LocalLLMSkill, "_generate", offline)
    answer = runtime.kernel.process("xyzzy inexplicavel 98765")
    assert answer.ok is False
    assert "Ollama" in answer.text
    assert "detalhes internos" not in answer.text


def test_remote_api_preserves_command_allowlist(tmp_path: Path, monkeypatch):
    runtime = _runtime(tmp_path, enabled=True, remote=True)
    runtime.auth.create_owner("rony", "senha-bem-segura")
    monkeypatch.setattr(LocalLLMSkill, "_generate", lambda self, text: "Apenas conversa.")
    client = TestClient(create_app(runtime))
    login = client.post("/v1/auth/login", json={"username": "rony", "password": "senha-bem-segura"})
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    allowed = client.post("/v1/messages", headers=headers, json={"text": "xyzzy inexplicavel 98765"})
    assert allowed.status_code == 200
    assert allowed.json()["handled_by"] == "ollama-chat"
    blocked = client.post("/v1/messages", headers=headers, json={"text": "abrir o Google Chrome"})
    assert blocked.status_code == 403


def test_ollama_request_is_local_no_stream(monkeypatch):
    import huli.skills.local_llm as module

    calls = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, length):
            return b'{"response":"Ol\\u00e1, Rony."}'

    class FakeOpener:
        def open(self, request, timeout):
            calls["url"] = request.full_url
            calls["payload"] = json.loads(request.data)
            calls["timeout"] = timeout
            return FakeResponse()

    monkeypatch.setattr(module, "build_opener", lambda proxy: FakeOpener())
    skill = LocalLLMSkill("qwen2.5:7b", 12)
    assert skill._generate("Como vai?") == "Olá, Rony."
    assert calls["url"] == "http://127.0.0.1:11434/api/generate"
    assert calls["payload"]["stream"] is False
    assert calls["payload"]["model"] == "qwen2.5:7b"
    assert calls["timeout"] == 12
