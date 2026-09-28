# SPDX-License-Identifier: Apache-2.0
"""A free-form spec (no structured agent register) uses the configured LLM
when there is one, and falls back to the generic starter template when
there isn't. Structured inputs never reach the LLM path."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
import backend.api.routes as routes

FREE_FORM_SPEC = b"""# Claim Intake

Claims arrive by email. Extract documents, classify the claim, check
coverage, score fraud risk and notify the claimant.
"""

LLM_JSON = json.dumps({
    "orchestrators": [{"name": "ClaimIntakeOrchestrator"}],
    "squads": [{"name": "ClaimSquad", "agents": ["FraudRiskAgent"]}],
    "agents": [{"name": "FraudRiskAgent", "type": "K9ValidationLoopAgent",
                "model": "reasoning", "description": "Scores fraud risk"}],
})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_ENABLED", "false")
    return TestClient(app)


def _upload(client, **form):
    return client.post("/api/spec/import",
                       files={"file": ("claim-intake.md", FREE_FORM_SPEC, "text/markdown")},
                       data=form).json()


def test_free_form_spec_without_llm_uses_starter_template(client, monkeypatch):
    monkeypatch.delenv("LLM_ENDPOINT", raising=False)
    monkeypatch.setattr(routes, "get_llm_config", lambda: {}, raising=False)
    import backend.services.config_service as cs
    monkeypatch.setattr(cs, "get_llm_config", lambda: {})
    data = _upload(client)
    assert data["source"] == "spec-fallback"


def test_free_form_spec_with_llm_uses_llm_suggestion(client, monkeypatch):
    calls = []

    def fake_llm(endpoint, provider, model, api_key, prompt, **kw):
        calls.append(model)
        return "<think>planning {not json}</think>```json\n" + LLM_JSON + "\n```"

    monkeypatch.setattr(routes, "_call_llm", fake_llm)
    cfg = json.dumps({"provider": "ollama", "endpoint": "http://llm.example:11434",
                      "model": "qwen3.8:27b", "api_key": ""})
    data = _upload(client, llm_config=cfg)
    assert data["source"] == "spec-llm"
    assert [a["name"] for a in data["suggestion"]["agents"]] == ["FraudRiskAgent"]
    assert "qwen3.8:27b" in calls
