"""Authentication endpoints."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from config import get_settings
from core.auth import decode_token, get_current_user, hash_password, verify_password
from core.database import get_session
from core.exceptions import DuplicateResourceError, InvalidCredentialsError
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.auth_schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from domain.user.models import User
from domain.user.schemas import SessionListResponse
from services.auth.password_reset import PasswordResetService
from services.auth.projects import ensure_default_project
from services.auth.sessions import AuthSessionService

settings = get_settings()
logger = get_logger()
router = APIRouter()


def _token_response(tokens) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier.value,
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    locale = get_request_locale(http_request)
    result = await session.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise DuplicateResourceError("User", "email", request.email)

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await ensure_default_project(session, user, locale)

    logger.info("User registered", user_id=str(user.id), email=user.email)
    return _user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Login user and return tokens."""
    result = await session.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise InvalidCredentialsError()

    user.last_login_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    await session.commit()

    tokens = await AuthSessionService().issue_tokens(session, user)

    logger.info("User logged in", user_id=str(user.id), email=user.email)
    return _token_response(tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """Refresh access token."""
    session_service = AuthSessionService()

    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidCredentialsError()

        user_id = payload.get("sub")
        old_session_id = payload.get("session_id")

        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise InvalidCredentialsError()

        session_service.validate_cached_session(old_session_id, str(user_id))
        session_service.revoke_cached_session(old_session_id)

        tokens = await session_service.issue_tokens(session, user)
        logger.info("Token refreshed with new session", user_id=str(user.id))
        return _token_response(tokens)
    except Exception as e:
        logger.warning("Token refresh failed", error=str(e))
        raise InvalidCredentialsError()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Logout user and revoke the current session."""
    session_service = AuthSessionService()
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        logger.info("User logged out (no token)", user_id=str(current_user.id))
        return None

    try:
        session_id = session_service.session_id_from_authorization(auth_header)
        if session_id:
            await session_service.revoke_db_session(session, session_id)
            logger.info(
                "User logged out (session revoked)",
                user_id=str(current_user.id),
                session_id=session_id,
            )
        else:
            logger.info(
                "User logged out (legacy token without session_id)",
                user_id=str(current_user.id),
            )
    except Exception as e:
        logger.warning("Logout error", error=str(e), user_id=str(current_user.id))

    return None


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all active sessions for the current user."""
    session_service = AuthSessionService()
    current_session_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            current_session_id = session_service.session_id_from_authorization(auth_header)
        except Exception:
            current_session_id = None

    return await session_service.list_active_sessions(session, current_user.id, current_session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Revoke a specific session."""
    revoked = await AuthSessionService().revoke_db_session(session, session_id, current_user.id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info("Session revoked", user_id=str(current_user.id), session_id=session_id)
    return None


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Request password reset. Disabled by default until email delivery exists."""
    locale = get_request_locale(http_request)
    result = await PasswordResetService().request_reset(session, request.email)

    if not result.enabled:
        logger.info("Password reset requested while disabled")
    elif result.user_exists:
        logger.info("Password reset token created", email=request.email)
    else:
        logger.info("Password reset requested for non-existent email")

    return {"message": t("messages.password_reset_sent", locale)}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Reset password using a reset token, when password reset is enabled."""
    locale = get_request_locale(http_request)

    try:
        ok = await PasswordResetService().reset_password(
            session, request.token, request.new_password
        )
        if not ok:
            raise HTTPException(
                status_code=400,
                detail=t("errors.invalid_or_expired_token", locale),
            )

        logger.info("Password reset successful")
        return {"message": t("messages.password_reset_success", locale)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Password reset failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=t("errors.password_reset_failed", locale),
        )


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    request: GoogleAuthRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate with Google OAuth."""
    if not GOOGLE_AUTH_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Google authentication is not available. Install google-auth package.",
        )

    locale = get_request_locale(http_request)

    try:
        google_client_id = getattr(settings, "google_client_id", None)
        if not google_client_id:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth is not configured on the server",
            )

        idinfo = id_token.verify_oauth2_token(
            request.id_token, google_requests.Request(), google_client_id
        )

        email = idinfo.get("email")
        email_verified = idinfo.get("email_verified", False)
        full_name = idinfo.get("name")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        if not email_verified:
            raise HTTPException(status_code=400, detail="Email not verified by Google")

        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(secrets.token_urlsafe(32)),
                full_name=full_name,
                is_email_verified=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            await ensure_default_project(session, user, locale)
            logger.info(
                "User registered via Google OAuth", user_id=str(user.id), email=user.email
            )
        else:
            if not user.is_email_verified:
                user.is_email_verified = True
            if not user.full_name and full_name:
                user.full_name = full_name
            await session.commit()

        user.last_login_at = datetime.utcnow()
        user.login_count = (user.login_count or 0) + 1
        await session.commit()

        tokens = await AuthSessionService().issue_tokens(session, user)
        logger.info("User authenticated via Google", user_id=str(user.id), email=user.email)
        return _token_response(tokens)
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("Google token verification failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        logger.error("Google authentication failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=t("errors.google_auth_failed", locale))
