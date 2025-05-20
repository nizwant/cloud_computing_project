import sys
import os


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/app_engine"))
)

from main import app
import pytest


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Discover Music Instantly" in res.data


def test_about(client):
    res = client.get("/about")
    assert res.status_code == 200
    assert b"About Us" in res.data
