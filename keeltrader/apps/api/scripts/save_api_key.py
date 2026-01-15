#!/usr/bin/env python3
"""Save API key configuration for admin user."""

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

# Your API key (do not hardcode secrets in source control)
API_KEY = os.environ.get("KEELTRADER_API_KEY", "")
USER_EMAIL = os.environ.get("KEELTRADER_USER_EMAIL", "admin@keeltrader.com")


async def save_api_key():
    """Save API key to admin user."""
    encryption_service = get_encryption_service()

    async with async_session() as session:
        try:
            # Use raw SQL to avoid ORM issues
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

            # Create LLM configuration
            llm_config = {
                "id": str(uuid4()),
                "name": "OpenAI API",
                "provider_type": "openai",
                "is_active": True,
                "is_default": True,
                "api_key": encryption_service.encrypt(API_KEY),
                "base_url": "https://api.openai.com",
                "default_model": "gpt-3.5-turbo",
                "available_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                "supports_streaming": True,
                "supports_functions": True,
                "supports_vision": False,
                "supports_embeddings": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }

            # Update configuration
            existing_config["llm_configs"] = [llm_config]

            # Also save encrypted API key in dedicated fields
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

            logger.info(f"✅ API key saved successfully for {USER_EMAIL}")
            print(f"✅ API key saved successfully!")
            print(f"   Provider: OpenAI")
            print(f"   Model: gpt-3.5-turbo")
            print(f"   User: {USER_EMAIL}")
            print(f"\nYou can now login at http://localhost:3000")
            print(f"Email: {USER_EMAIL}")
            print(f"Password: Admin@123")

            return True

        except Exception as e:
            logger.error(f"Failed to save API key: {e}")
            print(f"❌ Error: {str(e)}")
            await session.rollback()
            return False


async def test_api_connection():
    """Test the API connection."""
    import httpx

    print("\nTesting API connection...")

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    test_payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Say 'Hello' if you can receive this."}
        ],
        "max_tokens": 50,
        "temperature": 0.1,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=test_payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                print("✅ API connection test successful!")
                result = response.json()
                if "choices" in result:
                    print(f"Response: {result['choices'][0]['message']['content']}")
                return True
            else:
                print(f"❌ API test failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False


async def main():
    """Main function."""
    print("=" * 60)
    print("KeelTrader - Save API Key Configuration")
    print("=" * 60)

    if not API_KEY:
        print("❌ Missing API key. Set `KEELTRADER_API_KEY` in your environment.")
        sys.exit(1)

    # Test API first (optional)
    # await test_api_connection()

    # Save the configuration
    success = await save_api_key()

    if success:
        print("\n" + "=" * 60)
        print("Configuration complete!")
        print("=" * 60)
    else:
        print("\n❌ Configuration failed. Please check the logs.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
