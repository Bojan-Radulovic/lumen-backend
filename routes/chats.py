from fastapi import APIRouter, Depends
from models import ChatResponse, ChatCreate, MessageResponse
from services.chats import create_new_chat_service, get_chats_service, get_messages_service, delete_chat_service, get_last_message_service
from routes.auth import get_current_user_dependency
from typing import List

router = APIRouter(prefix="/api/chats", tags=["chats"])

@router.post("/", response_model=ChatResponse)
async def create_new_chat_route(chat_create: ChatCreate, current_user: dict = Depends(get_current_user_dependency)):
    return await create_new_chat_service(chat_create, current_user)

@router.get("/", response_model=List[ChatResponse])
async def get_chats_route(current_user: dict = Depends(get_current_user_dependency)):
    return await get_chats_service(current_user)

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_messages_route(chat_id: int, current_user: dict = Depends(get_current_user_dependency)):
    return await get_messages_service(chat_id, current_user)

@router.delete("/{chat_id}")
async def delete_chat_route(chat_id: int, current_user: dict = Depends(get_current_user_dependency)):
    return await delete_chat_service(chat_id, current_user)

@router.get("/{chat_id}/messages/last", response_model=MessageResponse)
async def get_last_message_route(chat_id: int, current_user: dict = Depends(get_current_user_dependency)):
    return await get_last_message_service(chat_id, current_user)