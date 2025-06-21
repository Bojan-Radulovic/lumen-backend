from fastapi import APIRouter, Depends
from models import UserCreate, ForgotPasswordRequest, ResetPasswordRequest
from services.user import create_user_service, list_users_service, delete_user_service, forgot_password_service, reset_password_service
from routes.auth import get_admin_user_dependency

router = APIRouter(prefix="/api/admin/users", tags=["user"])

@router.post("/")
async def create_user_route(user_create: UserCreate, admin_user: dict = Depends(get_admin_user_dependency)):
    return await create_user_service(user_create, admin_user)

@router.get("/")
async def list_users_route(admin_user: dict = Depends(get_admin_user_dependency)):
    return await list_users_service(admin_user)

@router.delete("/{user_id}")
async def delete_user_route(user_id: int, admin_user: dict = Depends(get_admin_user_dependency)):
    return await delete_user_service(user_id, admin_user)

@router.post("/forgot-password")
async def forgot_password_route(request: ForgotPasswordRequest):
    return await forgot_password_service(request.email)

@router.post("/reset-password")
async def reset_password_route(request: ResetPasswordRequest):
    return await reset_password_service(request.token, request.new_password)