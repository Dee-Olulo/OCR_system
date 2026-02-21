
import uuid
from datetime import datetime
from fastapi import HTTPException, status
from app.database import get_database
from app.models.user import UserCreate, UserResponse, Token
from app.utils.security import hash_password, verify_password, create_access_token

class AuthService:
    """Authentication service for user management"""

    @staticmethod
    async def register_user(user_data: UserCreate) -> Token:
        db = get_database()

        if await db.users.find_one({"email": user_data.email}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        if await db.users.find_one({"username": user_data.username}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        user_dict = {
            "_id": str(uuid.uuid4()),  # ✅ explicit string ID
            "email": user_data.email,
            "username": user_data.username,
            "hashed_password": hash_password(user_data.password),
            "tenant_id": str(uuid.uuid4()),
            "is_active": True,
            "created_at": datetime.utcnow()
        }

        await db.users.insert_one(user_dict)

        access_token = create_access_token(
            data={"sub": user_dict["_id"]}
        )

        return Token(
            access_token=access_token,
            user=UserResponse(
                id=user_dict["_id"],
                email=user_dict["email"],
                username=user_dict["username"],
                created_at=user_dict["created_at"]
            )
        )

    @staticmethod
    async def login_user(email: str, password: str) -> Token:
        db = get_database()

        user = await db.users.find_one({"email": email})
        if not user or not verify_password(password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        access_token = create_access_token(
            data={"sub": str(user["_id"])}
        )

        return Token(
            access_token=access_token,
            user=UserResponse(
                id=str(user["_id"]),
                email=user["email"],
                username=user["username"],
                created_at=user["created_at"]
            )
        )

auth_service = AuthService()
