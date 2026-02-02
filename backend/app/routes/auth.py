# /backend/app/routes/auth.py

from fastapi import APIRouter, HTTPException, Depends
from app.models.user import UserCreate, UserLogin, Token, UserResponse
from app.services.auth_service import auth_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=201)
async def register(user_data: UserCreate):
    """
    Register a new user
    
    - **email**: Valid email address
    - **username**: 3-50 characters
    - **password**: Minimum 6 characters
    """
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """
    Login with email and password
    
    Returns JWT access token valid for 24 hours
    """
    return await auth_service.login_user(user_data.email, user_data.password)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        username=current_user["username"],
        created_at=current_user["created_at"]
    )

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout current user
    
    Note: Since we use JWT, the token will remain valid until expiration.
    Client should discard the token.
    """
    return {"message": "Logged out successfully"}