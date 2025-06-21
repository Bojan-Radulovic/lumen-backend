from models import ChatCreate
from services.database import get_db_connection_service
from typing import List
from fastapi import HTTPException, status

def add_message(chat_id: int, content: str, is_human: bool, image_id: str = None):
    """Add a message to a chat"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('''
        INSERT INTO messages (chat_id, content, is_human, image_id) 
        VALUES (?, ?, ?, ?)
    ''', (chat_id, content, is_human, image_id))
    db.commit()

def get_chat_history_for_memory(chat_id: int, limit: int = 10) -> List[dict]:
    """Get recent messages for memory context"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('''
        SELECT content, is_human 
        FROM messages 
        WHERE chat_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (chat_id, limit))
    messages = c.fetchall()
    return [dict(msg) for msg in reversed(messages)]

def delete_chat(chat_id: int, user_id: int):
    """Delete a chat and all its messages"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT id FROM chats WHERE id = ? AND user_id = ?', (chat_id, user_id))
    if not c.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    c.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
    db.commit()

def get_chat_messages(chat_id: int, user_id: int) -> List[dict]:
    """Get all messages for a specific chat (with user validation)"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT id FROM chats WHERE id = ? AND user_id = ?', (chat_id, user_id))
    if not c.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    c.execute('''
        SELECT id, chat_id, content, is_human, image_id, created_at 
        FROM messages 
        WHERE chat_id = ? 
        ORDER BY created_at ASC
    ''', (chat_id,))
    return [dict(row) for row in c.fetchall()]

def create_chat(user_id: int, title: str) -> int:
    """Create a new chat and return its ID"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('INSERT INTO chats (user_id, title) VALUES (?, ?)', (user_id, title))
    db.commit()
    return c.lastrowid

def get_user_chats(user_id: int) -> List[dict]:
    """Get all chats for a user"""
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('''
        SELECT id, title, created_at, user_id 
        FROM chats 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (user_id,))
    return [dict(row) for row in c.fetchall()]

async def create_new_chat_service(chat_create: ChatCreate, current_user: dict):
    chat_id = create_chat(current_user['id'], chat_create.title)
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT id, title, created_at, user_id FROM chats WHERE id = ?', (chat_id,))
    chat = dict(c.fetchone())
    return chat

async def get_chats_service(current_user: dict):
    chats = get_user_chats(current_user['id'])
    return chats

async def get_messages_service(chat_id: int, current_user: dict):
    messages = get_chat_messages(chat_id, current_user['id'])
    return messages

async def delete_chat_service(chat_id: int, current_user: dict):
    delete_chat(chat_id, current_user['id'])
    return {"message": "Chat deleted successfully"}

async def get_last_message_service(chat_id: int, current_user: dict):
    """Get the last AI (is_human = false) message for a specific chat (with user validation)"""
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('SELECT id FROM chats WHERE id = ? AND user_id = ?', (chat_id, current_user['id']))
    if not c.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    c.execute('''
        SELECT id, chat_id, content, is_human, image_id, created_at 
        FROM messages 
        WHERE chat_id = ? AND is_human = 0
        ORDER BY created_at DESC
        LIMIT 1
    ''', (chat_id,))
    
    row = c.fetchone()
    return dict(row) if row else None
