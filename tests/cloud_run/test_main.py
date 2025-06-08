import sys
import os
import json
import base64
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/cloud_run"))
)

from main import app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_pubsub_handler_success(client):
    """Test handling a valid Pub/Sub message with a YouTube URL"""
    message = {"title": "imgonnagetyouback", "artist": "Taylor Swift"}
    data = json.dumps(
        {"message": {"data": base64.b64encode(json.dumps(message).encode()).decode()}}
    )

    response = client.post("/", data=data, content_type="application/json")

    assert response.status_code == 200
    assert response.data == b"OK"
