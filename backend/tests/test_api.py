"""Integration tests for FastAPI REST endpoints."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_serve_index_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Linux Hardware AI Assistant" in response.text


def test_serve_css():
    response = client.get("/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert "--bg-primary" in response.text


def test_serve_js():
    response = client.get("/script.js")
    assert response.status_code == 200
    assert "application/javascript" in response.headers.get("content-type", "")
    assert "API_BASE" in response.text


def test_get_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


def test_get_hardware_summary():
    response = client.get("/api/hardware")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "ram" in data
    assert "gpu" in data
    assert "storage" in data
    assert "motherboard" in data
    assert "environment" in data


def test_get_cpu_endpoint():
    response = client.get("/api/hardware/cpu")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "architecture" in data


def test_get_ram_endpoint():
    response = client.get("/api/hardware/ram")
    assert response.status_code == 200
    data = response.json()
    assert "raw_source" in data


def test_get_gpu_endpoint():
    response = client.get("/api/hardware/gpu")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data


def test_get_storage_endpoint():
    response = client.get("/api/hardware/storage")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data


def test_get_motherboard_endpoint():
    response = client.get("/api/hardware/motherboard")
    assert response.status_code == 200
    data = response.json()
    assert "raw_source" in data


def test_get_memory_slots_endpoint():
    response = client.get("/api/hardware/memory-slots")
    assert response.status_code == 200
    data = response.json()
    assert "slots" in data


def test_get_environment_endpoint():
    response = client.get("/api/hardware/environment")
    assert response.status_code == 200
    data = response.json()
    assert "is_wsl2" in data


def test_post_chat_endpoint():
    payload = {
        "message": "How much RAM do I have?",
        "history": [],
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "tools_used" in data
    assert "inspect_ram" in data["tools_used"]
    assert data["is_mock"] is True


def test_post_chat_invalid_empty_body():
    payload = {"message": "", "history": []}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 422  # Pydantic validation error for min_length=1
