"""Enterprise SSO (Single Sign-On) support for cloud mode.

Supports SAML 2.0 and OAuth 2.0 providers (Google, GitHub, Azure AD, Okta).
Only active when DEPLOYMENT_MODE=cloud and enterprise_sso_enabled=true.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config import get_settings

logger = logging.getLogger(__name__)


class SSOProvider:
    """Base SSO provider interface."""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self._is_enabled()

    def _is_enabled(self) -> bool:
        """Check if SSO is enabled."""
        return self.settings.is_cloud_mode() and self.settings.enterprise_sso_enabled

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get the authorization URL for SSO login."""
        raise NotImplementedError

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        raise NotImplementedError

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from the SSO provider."""
        raise NotImplementedError


class SAMLProvider(SSOProvider):
    """
    SAML 2.0 SSO provider.

    Supports enterprise identity providers like Okta, Azure AD, OneLogin, etc.
    """

    def __init__(self):
        super().__init__()
        self.saml_client = None

        if self.enabled and self.settings.saml_enabled:
            try:
                from onelogin.saml2.auth import OneLogin_Saml2_Auth
                from onelogin.saml2.settings import OneLogin_Saml2_Settings

                # SAML configuration
                self.saml_settings = {
                    "strict": True,
                    "debug": self.settings.debug,
                    "sp": {
                        "entityId": self.settings.saml_entity_id,
                        "assertionConsumerService": {
                            "url": f"{self.settings.app_url}/api/v1/auth/saml/acs",
                            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                        },
                        "singleLogoutService": {
                            "url": f"{self.settings.app_url}/api/v1/auth/saml/sls",
                            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                        },
                        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                        "x509cert": "",
                        "privateKey": "",
                    },
                    "idp": {
                        "entityId": self.settings.saml_entity_id,
                        "singleSignOnService": {
                            "url": self.settings.saml_sso_url,
                            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                        },
                        "singleLogoutService": {
                            "url": f"{self.settings.saml_sso_url}/logout",
                            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                        },
                        "x509cert": self.settings.saml_x509_cert,
                    },
                }

                logger.info("SAML SSO initialized")
            except ImportError:
                logger.warning(
                    "python3-saml library not installed. "
                    "Install with: pip install python3-saml"
                )
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize SAML: {e}")
                self.enabled = False

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get SAML SSO URL."""
        if not self.enabled:
            raise ValueError("SAML SSO is not enabled")

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth

            # Create SAML auth request
            request_data = {
                "https": "on" if self.settings.app_url.startswith("https") else "off",
                "http_host": self.settings.app_url.replace("https://", "").replace(
                    "http://", ""
                ),
                "script_name": "/api/v1/auth/saml/login",
                "server_port": 443 if self.settings.app_url.startswith("https") else 80,
            }

            auth = OneLogin_Saml2_Auth(request_data, self.saml_settings)
            return auth.login(return_to=redirect_uri)
        except Exception as e:
            logger.error(f"SAML authorization URL error: {e}")
            raise

    def process_saml_response(self, saml_response: str) -> Dict[str, Any]:
        """Process SAML response and extract user info."""
        if not self.enabled:
            raise ValueError("SAML SSO is not enabled")

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth

            request_data = {
                "https": "on" if self.settings.app_url.startswith("https") else "off",
                "http_host": self.settings.app_url.replace("https://", "").replace(
                    "http://", ""
                ),
                "script_name": "/api/v1/auth/saml/acs",
                "post_data": {"SAMLResponse": saml_response},
            }

            auth = OneLogin_Saml2_Auth(request_data, self.saml_settings)
            auth.process_response()

            if not auth.is_authenticated():
                errors = auth.get_errors()
                raise ValueError(f"SAML authentication failed: {errors}")

            attributes = auth.get_attributes()
            name_id = auth.get_nameid()

            return {
                "email": name_id,
                "name": attributes.get("name", [name_id])[0],
                "first_name": attributes.get("givenName", [""])[0],
                "last_name": attributes.get("surname", [""])[0],
                "attributes": attributes,
            }
        except Exception as e:
            logger.error(f"SAML response processing error: {e}")
            raise


class OAuthProvider(SSOProvider):
    """
    OAuth 2.0 SSO provider.

    Supports Google, GitHub, Azure AD, Okta, etc.
    """

    def __init__(self, provider_name: str):
        super().__init__()
        self.provider_name = provider_name
        self.client_id = None
        self.client_secret = None
        self.authorize_url = None
        self.token_url = None
        self.userinfo_url = None

        if self.enabled and provider_name in self.settings.oauth_providers:
            self._configure_provider(provider_name)

    def _configure_provider(self, provider_name: str):
        """Configure OAuth provider endpoints."""
        # These would typically come from environment variables
        # For example: OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET

        providers_config = {
            "google": {
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "scope": "openid email profile",
            },
            "github": {
                "authorize_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "userinfo_url": "https://api.github.com/user",
                "scope": "user:email",
            },
            "azure": {
                "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "userinfo_url": "https://graph.microsoft.com/v1.0/me",
                "scope": "openid email profile",
            },
            "okta": {
                # Okta URLs are tenant-specific, these are placeholders
                "authorize_url": f"{self.settings.app_url}/oauth2/v1/authorize",
                "token_url": f"{self.settings.app_url}/oauth2/v1/token",
                "userinfo_url": f"{self.settings.app_url}/oauth2/v1/userinfo",
                "scope": "openid email profile",
            },
        }

        if provider_name in providers_config:
            config = providers_config[provider_name]
            self.authorize_url = config["authorize_url"]
            self.token_url = config["token_url"]
            self.userinfo_url = config["userinfo_url"]
            self.scope = config["scope"]
            logger.info(f"OAuth provider '{provider_name}' configured")

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get OAuth authorization URL."""
        if not self.enabled or not self.authorize_url:
            raise ValueError(f"OAuth provider '{self.provider_name}' is not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
        }

        from urllib.parse import urlencode

        return f"{self.authorize_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        if not self.enabled or not self.token_url:
            raise ValueError(f"OAuth provider '{self.provider_name}' is not configured")

        import httpx

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = httpx.post(self.token_url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OAuth token exchange error: {e}")
            raise

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth provider."""
        if not self.enabled or not self.userinfo_url:
            raise ValueError(f"OAuth provider '{self.provider_name}' is not configured")

        import httpx

        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            response = httpx.get(self.userinfo_url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OAuth user info error: {e}")
            raise


class SSOService:
    """
    SSO service for managing enterprise authentication.

    Automatically disabled in self-hosted mode.
    """

    def __init__(self):
        self.settings = get_settings()
        self.saml_provider = None
        self.oauth_providers = {}

        if self.settings.is_cloud_mode() and self.settings.enterprise_sso_enabled:
            # Initialize SAML if enabled
            if self.settings.saml_enabled:
                self.saml_provider = SAMLProvider()

            # Initialize OAuth providers
            for provider_name in self.settings.oauth_providers:
                self.oauth_providers[provider_name] = OAuthProvider(provider_name)

            logger.info("SSO service initialized")
        else:
            logger.info("SSO disabled: running in self-hosted mode or not configured")

    def is_enabled(self) -> bool:
        """Check if SSO is enabled."""
        return self.settings.is_cloud_mode() and self.settings.enterprise_sso_enabled

    def get_saml_provider(self) -> Optional[SAMLProvider]:
        """Get SAML provider if enabled."""
        return self.saml_provider

    def get_oauth_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name."""
        return self.oauth_providers.get(provider_name)

    def list_available_providers(self) -> Dict[str, bool]:
        """List all available SSO providers."""
        providers = {}

        if self.saml_provider and self.saml_provider.enabled:
            providers["saml"] = True

        for name, provider in self.oauth_providers.items():
            providers[name] = provider.enabled

        return providers


# Global SSO service instance
_sso_service: Optional[SSOService] = None


def get_sso_service() -> SSOService:
    """Get the global SSO service instance."""
    global _sso_service
    if _sso_service is None:
        _sso_service = SSOService()
    return _sso_service
