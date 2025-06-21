from fastapi import APIRouter, Depends
from models import StreamRequest
from services.stream import stream_response_service
from routes.auth import get_current_user_dependency

router = APIRouter(prefix="/stream", tags=["stream"])

@router.post("/")
async def stream_response_route(request: StreamRequest, current_user: dict = Depends(get_current_user_dependency)):
    return await stream_response_service(request, current_user)