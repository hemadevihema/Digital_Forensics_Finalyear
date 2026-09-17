from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.database.mongodb import db_client
from app.rag.vector_store import faiss_manager

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_api_test():
    db_client.connect()
    faiss_manager.load_or_create()
    yield
    db_client.close()

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "vector_store" in data

def test_api_empty_chat_rejected():
    response = client.post("/chat", json={"user_question": ""})
    assert response.status_code == 400

def test_api_chat_flow():
    response = client.post("/chat", json={"user_question": "What is the policy?"})
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "answer" in data
    assert "retrieved_chunks" in data
    assert "metrics" in data

    req_id = data["request_id"]
    # Check events retrieval
    ev_resp = client.get(f"/events/request/{req_id}")
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert ev_data["event_count"] > 0

    # Check retrievals inspection
    ret_resp = client.get(f"/requests/{req_id}/retrievals")
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()
    assert "prompt_inspection" in ret_data
