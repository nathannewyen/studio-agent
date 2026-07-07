import pytest
from fastapi.testclient import TestClient
from main import app

def test_create_agent(test_client):
    response = test_client.post("/v1/agents", json={"name": "Test", "definition": "steps"})
    assert response.status_code == 201

def test_update_agent(test_client):
    create_response = test_client.post("/v1/agents", json={"name": "Test", "definition": "steps"})
    agent_id = create_response.json()["id"]

    update_response = test_client.put(f"/v1/agents/{agent_id}", json={"name": "Test update", "definition": "steps update"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Test update"