#!/usr/bin/env python3
"""Setup custom API endpoint for KeelTrader."""

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

# Configuration
API_KEY = os.environ.get("KEELTRADER_API_KEY", "")
USER_EMAIL = os.environ.get("KEELTRADER_USER_EMAIL", "admin@keeltrader.com")

# You can modify this URL to your actual OneAPI endpoint
# 请将下面的URL修改为你的OneAPI服务地址
CUSTOM_API_URL = os.environ.get(
    "KEELTRADER_CUSTOM_API_URL", "https://your-oneapi-service.com"
)


async def save_custom_api_config(base_url: str):
    """Save custom API configuration to database."""
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

            # Create custom API configuration
            api_config = {
                "id": str(uuid4()),
                "name": "Custom OneAPI Service",
                "provider_type": "custom",
                "is_active": True,
                "is_default": True,
                "api_key": encryption_service.encrypt(API_KEY),
                "base_url": base_url.rstrip("/"),
                # OpenAI compatible settings
                "api_format": "openai",
                "auth_type": "bearer",
                # Model settings (supports various models through proxy)
                "default_model": "gpt-3.5-turbo",
                "available_models": [
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-16k",
                    "gpt-4",
                    "gpt-4-turbo",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "claude-3-opus",
                    "claude-3-sonnet",
                    "claude-3-haiku",
                    "claude-3.5-sonnet",
                    "gemini-pro",
                    "gemini-1.5-pro",
                    "deepseek-chat",
                    "deepseek-coder",
                    "qwen-turbo",
                    "qwen-plus",
                    "qwen-max",
                    "moonshot-v1-8k",
                    "glm-4",
                    "yi-34b-chat",
                ],
                # API endpoints (OpenAI format)
                "chat_endpoint": "/v1/chat/completions",
                "completions_endpoint": "/v1/completions",
                "embeddings_endpoint": "/v1/embeddings",
                "models_endpoint": "/v1/models",
                # Features
                "supports_streaming": True,
                "supports_functions": True,
                "supports_vision": True,
                "supports_embeddings": True,
                # High limits for proxy service
                "max_tokens_limit": 128000,
                # Metadata
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Update configuration
            existing_config["llm_configs"] = [api_config]

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

            logger.info(f"✅ Custom API configuration saved for {USER_EMAIL}")
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            await session.rollback()
            return False


async def test_connection(base_url: str):
    """Test the API connection."""
    import httpx

    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    print(f"\nTesting connection to: {url}")

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Say 'Hello' in one word"}],
        "max_tokens": 10,
        "temperature": 0.1,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                print("✅ Connection successful!")
                result = response.json()
                if "choices" in result:
                    print(f"Response: {result['choices'][0]['message']['content']}")
                return True
            elif response.status_code == 401:
                print("⚠️  Authentication failed - Check your API key")
                return False
            elif response.status_code == 404:
                print("❌ Endpoint not found - Check the URL")
                return False
            else:
                print(f"❌ Error: Status {response.status_code}")
                try:
                    error = response.json()
                    if "error" in error:
                        print(
                            f"Message: {error['error'].get('message', 'Unknown error')}"
                        )
                except:
                    print(f"Response: {response.text[:200]}")
                return False

    except httpx.ConnectError:
        print("❌ Cannot connect to the service - Check the URL")
        return False
    except httpx.TimeoutException:
        print("⏱️  Connection timeout - Service may be slow or unreachable")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


async def main():
    """Main function."""
    print("=" * 60)
    print("KeelTrader - Custom API Service Setup")
    print("=" * 60)
    if not API_KEY:
        print("❌ Missing API key. Set `KEELTRADER_API_KEY` in your environment.")
        return
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")

    print("\n" + "⚠️ " * 10)
    print("IMPORTANT: Edit this file first!")
    print(f"Current URL: {CUSTOM_API_URL}")
    print("Change CUSTOM_API_URL to your actual service address")
    print("⚠️ " * 10)

    if CUSTOM_API_URL == "https://your-oneapi-service.com":
        print(
            "\n❌ Please edit this file and set CUSTOM_API_URL to your actual service URL!"
        )
        print("Example URLs:")
        print("  - https://api.example.com")
        print("  - http://123.456.789.0:3000")
        print("  - https://oneapi.yourdomain.com")
        return

    print(f"\nUsing API endpoint: {CUSTOM_API_URL}")

    # Test connection
    print("\n" + "-" * 60)
    connection_ok = await test_connection(CUSTOM_API_URL)

    if not connection_ok:
        print("\n⚠️  Connection test failed!")
        print("Possible issues:")
        print("1. The URL might be incorrect")
        print("2. The API key might be invalid")
        print("3. The service might be down")
        print("\nSaving configuration anyway...")

    # Save configuration
    print("\n" + "-" * 60)
    print("Saving configuration...")

    success = await save_custom_api_config(CUSTOM_API_URL)

    if success:
        print("\n" + "=" * 60)
        print("✅ Configuration Saved Successfully!")
        print("=" * 60)
        print(f"\nService URL: {CUSTOM_API_URL}")
        print(f"Default Model: gpt-3.5-turbo")
        print("\nYou can now login to KeelTrader:")
        print(f"  URL: http://localhost:3000")
        print(f"  Email: {USER_EMAIL}")
        print(f"  Password: Admin@123")

        if connection_ok:
            print("\n✅ API connection is working!")
        else:
            print("\n⚠️  Note: Connection test failed")
            print("You may need to check your settings in the web interface")
    else:
        print("\n❌ Failed to save configuration")
        print("Please check the logs for errors")


if __name__ == "__main__":
    asyncio.run(main())
