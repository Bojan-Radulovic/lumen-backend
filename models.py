from typing import Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordChange(BaseModel):
    email: str
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class ChatCreate(BaseModel):
    title: str

class ChatResponse(BaseModel):
    id: int
    title: str
    created_at: str
    user_id: int

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    content: str
    is_human: bool
    image_id: Optional[str]
    created_at: str

class StreamRequest(BaseModel):
    question: str
    chat_id: Optional[int] = None

class ImageResponse(BaseModel):
    image_id: str
    image_data: str
    file_size: int
    encoding: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
