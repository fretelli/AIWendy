"""
Pytest configuration and fixtures for the test suite.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI application.
    """
    from main import app

    return TestClient(app)


@pytest.fixture
def sample_user_data():
    """
    Sample user data for testing.
    """
    return {"email": "test@example.com", "password": "testpassword123"}
