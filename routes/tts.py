from fastapi import APIRouter, Depends
from services.tts import tts_service
from routes.auth import get_current_user_dependency

router = APIRouter(prefix="/tts", tags=["tts"])

@router.get("/")
async def tts_route(text: str, current_user: dict = Depends(get_current_user_dependency)):
    return await tts_service(text, current_user)