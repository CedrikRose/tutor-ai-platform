"""
Authentication Module

JWT-based authentication for Professor Dashboard.
- Password hashing with bcrypt
- JWT access + refresh tokens
- Role-based access control (RBAC)
"""
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import SessionLocal, User, RefreshToken
from config import settings

logger = logging.getLogger(__name__)

# Password hashing context (bcrypt, 12 rounds)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = getattr(settings, 'jwt_secret_key', 'CHANGE_THIS_IN_PRODUCTION_USE_SECRETS_MANAGER')
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days

# HTTP Bearer token scheme
security = HTTPBearer()


# ============================================================
# Password Hashing
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt (12 rounds).

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash

    Note:
        Bcrypt has a 72-byte limit. Passwords are truncated if longer.
    """
    # Bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hash

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================
# JWT Token Generation
# ============================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data (user_id, email, role)
        expires_delta: Optional expiration override

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: str, db: Session) -> str:
    """
    Create refresh token and store in database.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        Refresh token string
    """
    # Generate random token
    token_string = str(uuid.uuid4())

    # Hash token for storage
    token_hash = hashlib.sha256(token_string.encode()).hexdigest()

    # Store in database
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=uuid.UUID(user_id),
        token_hash=token_hash,
        expires_at=expires_at
    )

    db.add(refresh_token)
    db.commit()

    return token_string


def verify_refresh_token(token: str, db: Session) -> Optional[str]:
    """
    Verify refresh token and return user_id.

    Args:
        token: Refresh token string
        db: Database session

    Returns:
        User ID if valid, None otherwise
    """
    # Hash token
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Find in database
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

    if not refresh_token:
        return None

    # Update last_used_at
    refresh_token.last_used_at = datetime.utcnow()
    db.commit()

    return str(refresh_token.user_id)


def revoke_refresh_token(token: str, db: Session) -> bool:
    """
    Revoke refresh token (logout).

    Args:
        token: Refresh token string
        db: Database session

    Returns:
        True if revoked
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if refresh_token:
        refresh_token.is_revoked = True
        refresh_token.revoked_at = datetime.utcnow()
        db.commit()
        return True

    return False


# ============================================================
# JWT Token Verification
# ============================================================

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify JWT access token.

    Args:
        token: JWT token string

    Returns:
        Payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Verify token type
        if payload.get("type") != "access":
            return None

        return payload

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# ============================================================
# User Authentication
# ============================================================

def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Authenticate user with email and password.

    Args:
        email: User email
        password: Plain text password
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


# ============================================================
# FastAPI Dependencies
# ============================================================

def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user.

    Raises:
        HTTPException: If token invalid or user not found

    Returns:
        User object
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get current active user.

    Raises:
        HTTPException: If user is inactive

    Returns:
        User object
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to require admin role.

    Raises:
        HTTPException: If user is not admin

    Returns:
        User object
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================
# User Registration
# ============================================================

def create_user(
    email: str,
    password: str,
    full_name: str,
    institution: Optional[str],
    db: Session,
    is_active: bool = False,
    email_verified: bool = False
) -> User:
    """
    Create new user account.

    Args:
        email: User email (must be unique)
        password: Plain text password
        full_name: User's full name
        institution: Institution name
        db: Database session
        is_active: Whether account is immediately active (default: False, requires admin approval)
        email_verified: Whether email is verified (default: False)

    Raises:
        ValueError: If email already exists

    Returns:
        Created User object
    """
    # Check if email exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError("Email already registered")

    # Hash password
    password_hash = hash_password(password)

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        institution=institution,
        role="professor",  # Default role
        is_active=is_active,
        email_verified=email_verified
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    if is_active:
        logger.info(f"User created: {email} (immediately active)")
    else:
        logger.info(f"User created: {email} (awaiting admin approval)")

    return user


def approve_user(user_id: str, db: Session) -> User:
    """
    Approve user account (admin action).

    Args:
        user_id: User UUID
        db: Database session

    Raises:
        ValueError: If user not found

    Returns:
        Updated User object
    """
    user = db.query(User).filter(User.user_id == uuid.UUID(user_id)).first()

    if not user:
        raise ValueError("User not found")

    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"User approved: {user.email}")

    return user


# ============================================================
# Token Generation Helpers
# ============================================================

def generate_tokens_for_user(user: User, db: Session) -> Dict[str, str]:
    """
    Generate access and refresh tokens for user.

    Args:
        user: User object
        db: Database session

    Returns:
        Dict with access_token and refresh_token
    """
    # Access token payload
    access_token_data = {
        "sub": str(user.user_id),
        "email": user.email,
        "role": user.role
    }

    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(str(user.user_id), db)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ============================================================
# Password Validation
# ============================================================

def validate_password(password: str) -> bool:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate

    Returns:
        True if valid

    Raises:
        ValueError: With specific error message
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")

    return True


# ============================================================
# Audit Logging Helper
# ============================================================

def log_audit(
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str],
    resource_id: Optional[str],
    details: Optional[Dict[str, Any]],
    db: Session,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Log action to audit log.

    Args:
        user_id: User UUID (None for anonymous actions)
        action: Action name (e.g., 'login', 'create_course')
        resource_type: Resource type (e.g., 'user', 'course')
        resource_id: Resource UUID
        details: Additional details (JSON)
        db: Database session
        ip_address: Client IP
        user_agent: Client user agent
    """
    from database import AuditLog

    log_entry = AuditLog(
        user_id=uuid.UUID(user_id) if user_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=uuid.UUID(resource_id) if resource_id else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )

    db.add(log_entry)
    db.commit()


if __name__ == "__main__":
    # Test password hashing
    password = "TestPassword123"
    hashed = hash_password(password)
    print(f"Hashed: {hashed}")
    print(f"Verify: {verify_password(password, hashed)}")

    # Test token generation
    test_data = {"sub": "test-user-id", "email": "test@example.com", "role": "professor"}
    token = create_access_token(test_data)
    print(f"Token: {token[:50]}...")

    decoded = decode_access_token(token)
    print(f"Decoded: {decoded}")
