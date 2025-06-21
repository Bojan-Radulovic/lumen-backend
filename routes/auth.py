from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import UserLogin, TokenResponse, PasswordChange
from services.auth import (
    login_service, 
    change_password_service, 
    get_current_user_info_service,
    verify_token_service,
    get_user_by_email_service,
    validate_admin_user_service
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to get current user from JWT token.
    This replaces the old get_current_user_service dependency.
    """
    token = credentials.credentials
    email = verify_token_service(token)
    user = get_user_by_email_service(email)
    return user

def get_admin_user_dependency(current_user: dict = Depends(get_current_user_dependency)) -> dict:
    """
    Dependency to get current admin user.
    """
    return validate_admin_user_service(current_user)

@router.post("/login", response_model=TokenResponse)
async def login_route(user_login: UserLogin):
    return await login_service(user_login)

@router.post("/change-password")
async def change_password_route(password_change: PasswordChange):
    return await change_password_service(password_change)

@router.get("/me")
async def get_current_user_info_route(current_user: dict = Depends(get_current_user_dependency)):
    return await get_current_user_info_service(current_user)