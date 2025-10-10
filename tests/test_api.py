from fastapi.testclient import TestClient

from lift_sys.api.server import app, reset_state


client = TestClient(app)


def test_health():
    reset_state()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_endpoint():
    reset_state()
    response = client.post("/config", json={"model_endpoint": "http://localhost:8001", "temperature": 0.1})
    assert response.status_code == 200


def test_forward_endpoint_rejects_without_config():
    reset_state()
    response = client.post(
        "/forward",
        json={
            "ir": {
                "intent": {"summary": "a", "holes": []},
                "signature": {"name": "f", "parameters": [], "returns": None, "holes": []},
                "effects": [],
                "assertions": [],
                "metadata": {},
            }
        },
    )
    assert response.status_code == 400
