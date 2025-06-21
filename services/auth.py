from fastapi import HTTPException, status
import jwt
from datetime import timedelta
from models import UserLogin, PasswordChange
from constants import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from services.database import get_db_connection_service
import string
import secrets

def generate_reset_token():
    """Generate a secure random reset token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def generate_temporary_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_token_service(token: str) -> str:
    """
    Verify JWT token and return email.
    Pure service function that takes token as parameter.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return email
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_by_email_service(email: str) -> dict:
    """
    Get user by email from database.
    Pure service function that takes email as parameter.
    """
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return dict(user)

async def login_service(user_login: UserLogin):
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (user_login.email,))
    user = c.fetchone()
    
    if not user or hash_password(user_login.password) != user['password_hash']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['email']}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

async def change_password_service(password_change: PasswordChange):
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (password_change.email,))
    user = c.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if hash_password(password_change.old_password) != user['password_hash']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    new_password_hash = hash_password(password_change.new_password)
    c.execute('''
        UPDATE users 
        SET password_hash = ?, is_temporary_password = FALSE 
        WHERE email = ?
    ''', (new_password_hash, password_change.email))
    db.commit()
    
    return {"message": "Password changed successfully"}

async def get_current_user_info_service(current_user: dict):
    """
    Get current user info from user dict.
    Pure service function that takes user dict as parameter.
    """
    return {
        "email": current_user["email"],
        "is_admin": current_user["is_admin"],
        "is_temporary_password": current_user["is_temporary_password"],
        "id": current_user["id"]
    }
    
def validate_admin_user_service(current_user: dict) -> dict:
    """
    Validate that user is admin.
    Pure service function that takes user dict as parameter.
    """
    if not current_user.get('is_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt