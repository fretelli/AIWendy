"""Usage analytics integration for cloud mode.

Supports PostHog, Mixpanel, and Amplitude for tracking user behavior and usage metrics.
Only active when DEPLOYMENT_MODE=cloud and analytics is configured.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from config import get_settings

logger = logging.getLogger(__name__)


class AnalyticsProvider:
    """Base analytics provider interface."""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self._is_enabled()

    def _is_enabled(self) -> bool:
        """Check if analytics is enabled."""
        return (
            self.settings.is_cloud_mode()
            and self.settings.feature_analytics_enabled
            and self.settings.analytics_provider is not None
        )

    def identify(
        self,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify a user with properties."""
        raise NotImplementedError

    def track(
        self,
        user_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an event."""
        raise NotImplementedError

    def group(
        self,
        user_id: str,
        group_type: str,
        group_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Associate user with a group (e.g., tenant/organization)."""
        raise NotImplementedError


class PostHogProvider(AnalyticsProvider):
    """PostHog analytics provider."""

    def __init__(self):
        super().__init__()
        self.client = None
        if self.enabled and self.settings.posthog_api_key:
            try:
                from posthog import Posthog

                self.client = Posthog(
                    project_api_key=self.settings.posthog_api_key,
                    host=self.settings.posthog_host,
                )
                logger.info("PostHog analytics initialized")
            except ImportError:
                logger.warning(
                    "PostHog library not installed. Install with: pip install posthog"
                )
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize PostHog: {e}")
                self.enabled = False

    def identify(
        self,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify a user in PostHog."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.identify(
                distinct_id=user_id,
                properties=properties or {},
            )
        except Exception as e:
            logger.error(f"PostHog identify error: {e}")

    def track(
        self,
        user_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an event in PostHog."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.capture(
                distinct_id=user_id,
                event=event,
                properties=properties or {},
            )
        except Exception as e:
            logger.error(f"PostHog track error: {e}")

    def group(
        self,
        user_id: str,
        group_type: str,
        group_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Associate user with a group in PostHog."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.group_identify(
                group_type=group_type,
                group_key=group_id,
                properties=properties or {},
            )
            self.client.capture(
                distinct_id=user_id,
                event="$group",
                properties={
                    "$group_type": group_type,
                    "$group_key": group_id,
                },
            )
        except Exception as e:
            logger.error(f"PostHog group error: {e}")


class MixpanelProvider(AnalyticsProvider):
    """Mixpanel analytics provider."""

    def __init__(self):
        super().__init__()
        self.client = None
        if self.enabled and self.settings.mixpanel_token:
            try:
                from mixpanel import Mixpanel

                self.client = Mixpanel(self.settings.mixpanel_token)
                logger.info("Mixpanel analytics initialized")
            except ImportError:
                logger.warning(
                    "Mixpanel library not installed. Install with: pip install mixpanel"
                )
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize Mixpanel: {e}")
                self.enabled = False

    def identify(
        self,
        user_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify a user in Mixpanel."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.people_set(user_id, properties or {})
        except Exception as e:
            logger.error(f"Mixpanel identify error: {e}")

    def track(
        self,
        user_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track an event in Mixpanel."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.track(user_id, event, properties or {})
        except Exception as e:
            logger.error(f"Mixpanel track error: {e}")

    def group(
        self,
        user_id: str,
        group_type: str,
        group_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Associate user with a group in Mixpanel."""
        if not self.enabled or not self.client:
            return

        try:
            self.client.people_set(user_id, {group_type: group_id})
            if properties:
                self.client.group_set(group_type, group_id, properties)
        except Exception as e:
            logger.error(f"Mixpanel group error: {e}")


class NoOpProvider(AnalyticsProvider):
    """No-op provider for self-hosted mode or when analytics is disabled."""

    def __init__(self):
        super().__init__()
        self.enabled = False

    def identify(
        self, user_id: str, properties: Optional[Dict[str, Any]] = None
    ) -> None:
        pass

    def track(
        self, user_id: str, event: str, properties: Optional[Dict[str, Any]] = None
    ) -> None:
        pass

    def group(
        self,
        user_id: str,
        group_type: str,
        group_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass


class Analytics:
    """
    Analytics service for tracking user behavior and usage.

    Automatically selects the appropriate provider based on configuration.
    In self-hosted mode, this is a no-op.
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self._get_provider()

    def _get_provider(self) -> AnalyticsProvider:
        """Get the appropriate analytics provider."""
        if not self.settings.is_cloud_mode():
            logger.info("Analytics disabled: running in self-hosted mode")
            return NoOpProvider()

        provider_name = self.settings.analytics_provider
        if not provider_name:
            logger.info("Analytics disabled: no provider configured")
            return NoOpProvider()

        if provider_name == "posthog":
            return PostHogProvider()
        elif provider_name == "mixpanel":
            return MixpanelProvider()
        else:
            logger.warning(f"Unknown analytics provider: {provider_name}")
            return NoOpProvider()

    def identify_user(
        self,
        user_id: str,
        email: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Identify a user with their properties."""
        props = properties or {}
        props.update(
            {
                "email": email,
                "identified_at": datetime.utcnow().isoformat(),
            }
        )
        self.provider.identify(user_id, props)

    def track_event(
        self,
        user_id: str,
        event: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track a user event."""
        props = properties or {}
        props.update(
            {
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.provider.track(user_id, event, props)

    def associate_tenant(
        self,
        user_id: str,
        tenant_id: str,
        tenant_name: str,
        tenant_plan: str,
    ) -> None:
        """Associate a user with their tenant/organization."""
        self.provider.group(
            user_id=user_id,
            group_type="tenant",
            group_id=tenant_id,
            properties={
                "name": tenant_name,
                "plan": tenant_plan,
            },
        )

    # Convenience methods for common events
    def track_signup(
        self, user_id: str, email: str, source: Optional[str] = None
    ) -> None:
        """Track user signup."""
        self.track_event(
            user_id,
            "user_signed_up",
            {"email": email, "source": source},
        )

    def track_login(self, user_id: str) -> None:
        """Track user login."""
        self.track_event(user_id, "user_logged_in")

    def track_chat_message(
        self,
        user_id: str,
        coach_id: str,
        message_length: int,
        has_context: bool = False,
    ) -> None:
        """Track chat message sent."""
        self.track_event(
            user_id,
            "chat_message_sent",
            {
                "coach_id": coach_id,
                "message_length": message_length,
                "has_context": has_context,
            },
        )

    def track_journal_entry(self, user_id: str, entry_type: str) -> None:
        """Track journal entry created."""
        self.track_event(
            user_id,
            "journal_entry_created",
            {"entry_type": entry_type},
        )

    def track_report_generated(self, user_id: str, report_type: str) -> None:
        """Track report generation."""
        self.track_event(
            user_id,
            "report_generated",
            {"report_type": report_type},
        )

    def track_subscription_change(
        self,
        user_id: str,
        old_tier: str,
        new_tier: str,
    ) -> None:
        """Track subscription tier change."""
        self.track_event(
            user_id,
            "subscription_changed",
            {
                "old_tier": old_tier,
                "new_tier": new_tier,
            },
        )


# Global analytics instance
_analytics: Optional[Analytics] = None


def get_analytics() -> Analytics:
    """Get the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = Analytics()
    return _analytics
