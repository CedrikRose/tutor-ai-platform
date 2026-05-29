"""
Authentication API Endpoints

Login, register, token refresh, logout endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db, User
from auth import (
    authenticate_user,
    generate_tokens_for_user,
    verify_refresh_token,
    revoke_refresh_token,
    create_user,
    validate_password,
    get_current_user,
    log_audit
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================================
# Pydantic Models
# ============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: Optional[str] = None


class RegisterWithAccessCodeRequest(BaseModel):
    access_code: str
    email: EmailStr
    password: str
    password_confirm: str
    full_name: Optional[str] = None
    institution: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


# ============================================================================
# Auth Endpoints
# ============================================================================

@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns access token + refresh token.
    """
    # Authenticate user
    user = authenticate_user(request.email, request.password, db)

    if not user:
        logger.warning(f"Failed login attempt for: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Generate tokens
    tokens = generate_tokens_for_user(user, db)

    # Audit log
    log_audit(
        user_id=str(user.user_id),
        action="login",
        resource_type="user",
        resource_id=str(user.user_id),
        details={"email": user.email},
        db=db,
        ip_address=http_request.client.host if http_request.client else None
    )

    logger.info(f"User logged in: {user.email}")

    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user={
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "institution": user.institution
        }
    )


@router.post("/register")
def register(
    request: RegisterRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Register new professor account.
    Account requires admin approval before it can be used.
    """
    # Validate password
    try:
        validate_password(request.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create user
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            institution=request.institution,
            db=db
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    log_audit(
        user_id=None,
        action="register",
        resource_type="user",
        resource_id=str(user.user_id),
        details={"email": user.email},
        db=db,
        ip_address=http_request.client.host if http_request.client else None
    )

    logger.info(f"New registration: {user.email} (awaiting approval)")

    return {
        "message": "Registration successful. Your account is pending admin approval.",
        "user_id": str(user.user_id),
        "email": user.email
    }


@router.post("/register-with-code")
def register_with_access_code(
    request: RegisterWithAccessCodeRequest,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Register new professor account with access code.
    Account is immediately active (no admin approval needed).

    Requires:
    - Valid access code
    - Matching password confirmation
    - Valid email and password
    """
    from config import settings

    # Verify access code
    if request.access_code != settings.professor_registration_code:
        logger.warning(f"Invalid access code attempt from IP: {http_request.client.host if http_request.client else 'unknown'}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access code"
        )

    # Verify password confirmation
    if request.password != request.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    # Validate password strength
    try:
        validate_password(request.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create user (active immediately!)
    try:
        user = create_user(
            email=request.email,
            password=request.password,
            full_name=request.full_name or request.email.split('@')[0],
            institution=request.institution,
            db=db,
            is_active=True,  # Immediately active!
            email_verified=True  # No email verification needed
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Audit log
    log_audit(
        user_id=None,
        action="register_with_code",
        resource_type="user",
        resource_id=str(user.user_id),
        details={"email": user.email, "method": "access_code"},
        db=db,
        ip_address=http_request.client.host if http_request.client else None
    )

    logger.info(f"New registration with access code: {user.email} (immediately active)")

    # Generate tokens immediately so user can login
    tokens = generate_tokens_for_user(user, db)

    return {
        "message": "Registration successful. You can now use your account.",
        "user_id": str(user.user_id),
        "email": user.email,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "user": {
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "institution": user.institution
        }
    }


@router.post("/refresh", response_model=LoginResponse)
def refresh_access_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    # Verify refresh token
    user_id = verify_refresh_token(request.refresh_token, db)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Get user
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Generate new tokens
    tokens = generate_tokens_for_user(user, db)

    # Revoke old refresh token (rotation)
    revoke_refresh_token(request.refresh_token, db)

    logger.info(f"Tokens refreshed for user: {user.email}")

    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user={
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "institution": user.institution
        }
    )


@router.post("/logout")
def logout(
    request: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout (revoke refresh token).
    """
    # Revoke refresh token
    revoked = revoke_refresh_token(request.refresh_token, db)

    # Audit log
    log_audit(
        user_id=str(current_user.user_id),
        action="logout",
        resource_type="user",
        resource_id=str(current_user.user_id),
        details={"email": current_user.email},
        db=db
    )

    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info.
    """
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "institution": current_user.institution,
        "is_active": current_user.is_active,
        "email_verified": current_user.email_verified,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }
