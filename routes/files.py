from fastapi import APIRouter, Depends
from models import ImageResponse
from services.files import get_user_image_service
from routes.auth import get_current_user_dependency

router = APIRouter(prefix="/api/files", tags=["files"])

@router.get("/images/{image_id}", response_model=ImageResponse)
async def get_image_route(image_id: str, current_user: dict = Depends(get_current_user_dependency)):
    """Get a base64-encoded image if it belongs to the current user"""
    return await get_user_image_service(image_id, current_user)