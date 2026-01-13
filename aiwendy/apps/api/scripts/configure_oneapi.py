#!/usr/bin/env python3
"""Configure OneAPI proxy service for AIWendy."""

import asyncio
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import async_session
from core.encryption import get_encryption_service
from core.logging import get_logger

logger = get_logger(__name__)

# OneAPI Configuration
API_KEY = os.environ.get("AIWENDY_API_KEY", "")
USER_EMAIL = os.environ.get("AIWENDY_USER_EMAIL", "admin@aiwendy.com")

# Common OneAPI endpoints (adjust based on your deployment)
ONEAPI_ENDPOINTS = [
    "http://localhost:3000",  # Default OneAPI local port
    "http://localhost:8080",  # Alternative local port
    "http://oneapi:3000",  # Docker service name
    "https://api.oneapi.com",  # Cloud hosted (example)
]


async def test_oneapi_endpoint(base_url: str):
    """Test a OneAPI endpoint."""
    import httpx

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    print(f"Testing: {url}")

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10,
        "temperature": 0.1,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                print(f"✅ SUCCESS! Endpoint {base_url} is working")
                return True
            elif response.status_code == 401:
                print(f"⚠️  Authentication failed at {base_url}")
            elif response.status_code == 404:
                print(f"❌ Endpoint not found at {base_url}")
            else:
                print(f"❌ Status {response.status_code} from {base_url}")

    except httpx.ConnectError:
        print(f"❌ Cannot connect to {base_url}")
    except httpx.TimeoutException:
        print(f"⏱️  Timeout connecting to {base_url}")
    except Exception as e:
        print(f"❌ Error with {base_url}: {str(e)}")

    return False


async def find_working_endpoint():
    """Find a working OneAPI endpoint."""
    print("Searching for OneAPI endpoint...")
    print("-" * 50)

    for endpoint in ONEAPI_ENDPOINTS:
        if await test_oneapi_endpoint(endpoint):
            return endpoint

    return None


async def save_oneapi_config(base_url: str):
    """Save OneAPI configuration to database."""
    encryption_service = get_encryption_service()

    async with async_session() as session:
        try:
            # Get user record
            result = await session.execute(
                text("SELECT id, api_keys_encrypted FROM users WHERE email = :email"),
                {"email": USER_EMAIL},
            )
            row = result.fetchone()

            if not row:
                logger.error(f"User {USER_EMAIL} not found")
                return False

            user_id = row[0]
            existing_config = row[1] or {}

            # Create OneAPI configuration
            oneapi_config = {
                "id": str(uuid4()),
                "name": "OneAPI Proxy Service",
                "provider_type": "custom",  # Use custom provider for OneAPI
                "is_active": True,
                "is_default": True,
                "api_key": encryption_service.encrypt(API_KEY),
                "base_url": base_url,
                # OneAPI is OpenAI-compatible
                "api_format": "openai",
                "auth_type": "bearer",
                # Model settings (OneAPI can route to multiple models)
                "default_model": "gpt-3.5-turbo",
                "available_models": [
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                    "gpt-4",
                    "gpt-4-turbo",
                    "gpt-4-32k",
                    "claude-3-opus",
                    "claude-3-sonnet",
                    "claude-3-haiku",
                    "gemini-pro",
                    "deepseek-chat",
                    "qwen-turbo",
                    "qwen-plus",
                ],
                # API endpoints (OneAPI uses OpenAI format)
                "chat_endpoint": "/v1/chat/completions",
                "completions_endpoint": "/v1/completions",
                "embeddings_endpoint": "/v1/embeddings",
                "models_endpoint": "/v1/models",
                # Features
                "supports_streaming": True,
                "supports_functions": True,
                "supports_vision": True,
                "supports_embeddings": True,
                # Limits (OneAPI handles its own rate limiting)
                "max_tokens_limit": 128000,
                # Metadata
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Update configuration
            existing_config["llm_configs"] = [oneapi_config]

            # Also save to openai_api_key for compatibility
            encrypted_key = encryption_service.encrypt(API_KEY)

            # Update user record
            await session.execute(
                text(
                    """
                    UPDATE users
                    SET api_keys_encrypted = :config,
                        openai_api_key = :openai_key
                    WHERE id = :user_id
                """
                ),
                {
                    "config": json.dumps(existing_config),
                    "openai_key": encrypted_key,
                    "user_id": user_id,
                },
            )

            await session.commit()

            logger.info(f"✅ OneAPI configuration saved for {USER_EMAIL}")
            print(f"✅ OneAPI configuration saved successfully!")
            print(f"   Service: OneAPI Proxy")
            print(f"   Endpoint: {base_url}")
            print(f"   Default Model: gpt-3.5-turbo")
            print(f"   User: {USER_EMAIL}")

            return True

        except Exception as e:
            logger.error(f"Failed to save OneAPI config: {e}")
            print(f"❌ Error saving configuration: {str(e)}")
            await session.rollback()
            return False


async def main():
    """Main configuration function."""
    print("=" * 60)
    print("AIWendy - OneAPI Configuration")
    print("=" * 60)
    if not API_KEY:
        print("❌ Missing API key. Set `AIWENDY_API_KEY` in your environment.")
        return
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print()

    # Check if user wants to specify custom endpoint
    custom = input("Do you have a custom OneAPI endpoint URL? (y/N): ").strip().lower()

    if custom == "y":
        endpoint = input(
            "Enter your OneAPI endpoint URL (e.g., http://localhost:3000): "
        ).strip()
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"http://{endpoint}"

        print(f"\nTesting custom endpoint: {endpoint}")
        if await test_oneapi_endpoint(endpoint):
            working_endpoint = endpoint
        else:
            print("Custom endpoint failed, searching for alternatives...")
            working_endpoint = await find_working_endpoint()
    else:
        # Auto-detect endpoint
        working_endpoint = await find_working_endpoint()

    if working_endpoint:
        print("\n" + "=" * 60)
        print(f"✅ Found working OneAPI endpoint: {working_endpoint}")
        print("=" * 60)

        # Save configuration
        success = await save_oneapi_config(working_endpoint)

        if success:
            print("\n" + "=" * 60)
            print("🎉 Configuration Complete!")
            print("=" * 60)
            print("\nYou can now use AIWendy with OneAPI:")
            print(f"1. Login at http://localhost:3000")
            print(f"2. Email: {USER_EMAIL}")
            print(f"3. Password: Admin@123")
            print("\nOneAPI will route your requests to various AI models")
            print("based on your OneAPI configuration and permissions.")
        else:
            print("\n❌ Failed to save configuration")
    else:
        print("\n" + "=" * 60)
        print("❌ Could not find working OneAPI endpoint")
        print("=" * 60)
        print("\nPlease check:")
        print("1. Is OneAPI service running?")
        print("2. Is the API key correct?")
        print("3. What is the correct OneAPI endpoint URL?")
        print("\nCommon OneAPI deployments:")
        print("- Local: http://localhost:3000")
        print("- Docker: http://oneapi:3000")
        print("- Custom: Your server URL")


if __name__ == "__main__":
    asyncio.run(main())
