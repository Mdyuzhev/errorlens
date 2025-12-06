"""Authentication service with JWT tokens."""

from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class Token(BaseModel):
    """Token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    username: str | None = None
    user_id: str | None = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData | None:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        if username is None:
            return None
        return TokenData(username=username, user_id=user_id)
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Authenticate user by username and password."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    return user


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, username: str, password: str, is_admin: bool = False
) -> User:
    """Create new user."""
    user = User(
        username=username,
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def init_admin_user(db: AsyncSession) -> None:
    """Create admin user if not exists."""
    import logging

    logger = logging.getLogger(__name__)
    logger.info("[AUTH] init_admin_user called")

    try:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        logger.info(f"[AUTH] Admin user exists: {admin is not None}")

        if not admin:
            admin_password = settings.admin_password
            await create_user(db, "admin", admin_password, is_admin=True)
            logger.info("[AUTH] Admin user created. Username: admin")

        # Create demo user for testing
        result = await db.execute(select(User).where(User.username == "demo"))
        demo = result.scalar_one_or_none()
        logger.info(f"[AUTH] Demo user exists: {demo is not None}")

        if not demo:
            await create_user(db, "demo", "ErrorLenseTest", is_admin=True)
            logger.info("[AUTH] Demo user created. Username: demo / Password: ErrorLenseTest")

        logger.info("[AUTH] init_admin_user completed successfully")
    except Exception as e:
        logger.error(f"[AUTH] init_admin_user failed: {e}")
        raise
