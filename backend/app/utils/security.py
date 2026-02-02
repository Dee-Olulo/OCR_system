
# # /backend/app/utils/security.py

# from datetime import datetime, timedelta
# from typing import Optional
# import bcrypt
# from jose import JWTError, jwt
# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from app.config import settings
# from app.database import get_database

# # Token security
# security = HTTPBearer()

# def hash_password(password: str) -> str:
#     """Hash a password using bcrypt (automatically handles 72 byte limit)"""
#     # Encode password to bytes
#     password_bytes = password.encode('utf-8')
    
#     # Bcrypt will handle truncation internally, but let's be explicit
#     if len(password_bytes) > 72:
#         password_bytes = password_bytes[:72]
    
#     # Generate salt and hash
#     salt = bcrypt.gensalt()
#     hashed = bcrypt.hashpw(password_bytes, salt)
    
#     # Return as string
#     return hashed.decode('utf-8')

# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     """Verify password against hash"""
#     # Encode password to bytes
#     password_bytes = plain_password.encode('utf-8')
    
#     # Apply same truncation
#     if len(password_bytes) > 72:
#         password_bytes = password_bytes[:72]
    
#     # Encode hashed password if it's a string
#     if isinstance(hashed_password, str):
#         hashed_password = hashed_password.encode('utf-8')
    
#     # Verify
#     return bcrypt.checkpw(password_bytes, hashed_password)

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     """Create JWT access token"""
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
#     return encoded_jwt

# def decode_token(token: str) -> dict:
#     """Decode JWT token"""
#     try:
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
#         return payload
#     except JWTError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials"
#         )

# async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     """Get current user from JWT token"""
#     token = credentials.credentials
#     payload = decode_token(token)
    
#     user_id: str = payload.get("sub")
#     if user_id is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not validate credentials"
#         )
    
#     # Get user from database
#     db = get_database()
#     user = await db.users.find_one({"_id": user_id})
    
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found"
#         )
    
#     return user
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.database import get_database

security = HTTPBearer()

# =========================
# PASSWORD HASHING
# =========================

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    # bcrypt hard limit
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")

    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    return bcrypt.checkpw(
        password_bytes,
        hashed_password.encode("utf-8")
    )

# =========================
# JWT TOKEN (BACKWARD-COMPATIBLE)
# =========================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

# =========================
# CURRENT USER
# =========================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    db = get_database()
    user = await db.users.find_one({"_id": user_id})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user
