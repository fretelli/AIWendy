"""
Pytest configuration and fixtures for the test suite.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing the app
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-32chars-minimum"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"


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
