"""Phase 0 acceptance: /api/health returns 200 and models import cleanly."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import Category, Summary, Transaction

client = TestClient(app)


def test_health_ok():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    # Project decision: Groq is the provider; default model is Llama 3.3 70B.
    assert body["llm_model"] == "llama-3.3-70b-versatile"
    assert "llm_enabled" in body


def test_canonical_models_importable():
    # The cross-phase contract must be constructible.
    assert Category.FOOD.value == "Food"
    assert len(list(Category)) == 10
    assert Transaction.model_fields.keys()
    assert Summary.model_fields.keys()
