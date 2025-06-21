from services.database import get_db_connection_service
from services.auth import generate_temporary_password, hash_password, generate_reset_token
from models import UserCreate
from fastapi import HTTPException, status
from dependencies import mailjet
import secrets
import string
from datetime import datetime, timedelta
from constants import CHANGE_PASSWORD_LINK

def send_welcome_email(email: str, temp_password: str):
    """Send welcome email with temporary password and password change link"""
    change_password_link = CHANGE_PASSWORD_LINK
    
    html_content = f"""
    <h2>Welcome to Lumen AI Assistant!</h2>
    <p>An admin has created an account for you. Here are your login credentials:</p>
    <p><strong>Email:</strong> {email}</p>
    <p><strong>Temporary Password:</strong> {temp_password}</p>
    <p><strong>Important:</strong> You must change your password after your first login.</p>
    <p><a href="{change_password_link}">Click here to change your password</a></p>
    <p>If the link doesn't work, copy and paste this URL into your browser:</p>
    <p>{change_password_link}</p>
    """
    
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "lumen@bojan-radulovic.xyz",
                    "Name": "Lumen"
                },
                "To": [
                    {
                        "Email": email,
                        "Name": "New User"
                    }
                ],
                "Subject": "Welcome to Lumen - Your Account Details",
                "HTMLPart": html_content + "<p><strong>This email was sent using the Lumen AI agent.</strong></p>"
            }
        ]
    }
    
    try:
        result = mailjet.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email with reset link"""
    reset_link = f"http://localhost:3000/reset-password?token={reset_token}"
    
    html_content = f"""
    <h2>Password Reset Request</h2>
    <p>You have requested to reset your password for your Lumen AI Assistant account.</p>
    <p>Click the link below to reset your password:</p>
    <p><a href="{reset_link}">Reset Your Password</a></p>
    <p>If the link doesn't work, copy and paste this URL into your browser:</p>
    <p>{reset_link}</p>
    <p><strong>This link will expire in 1 hour.</strong></p>
    <p>If you didn't request this reset, please ignore this email.</p>
    """
    
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "lumen@bojan-radulovic.xyz",
                    "Name": "Lumen"
                },
                "To": [
                    {
                        "Email": email,
                        "Name": "User"
                    }
                ],
                "Subject": "Password Reset - Lumen AI Assistant",
                "HTMLPart": html_content + "<p><strong>This email was sent using the Lumen AI agent.</strong></p>"
            }
        ]
    }
    
    try:
        result = mailjet.send.create(data=data)
        return result.status_code == 200
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

async def create_user_service(user_create: UserCreate, admin_user: dict):
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('SELECT * FROM users WHERE email = ?', (user_create.email,))
    if c.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    temp_password = generate_temporary_password()
    password_hash = hash_password(temp_password)
    
    c.execute('''
        INSERT INTO users (email, password_hash, is_temporary_password) 
        VALUES (?, ?, TRUE)
    ''', (user_create.email, password_hash))
    db.commit()
    
    email_sent = send_welcome_email(user_create.email, temp_password)
    
    return {
        "message": "User created successfully",
        "email_sent": email_sent,
        "temporary_password": temp_password
    }

async def forgot_password_service(email: str):
    """Handle forgot password request"""
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}
    
    reset_token = generate_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    c.execute('''
        INSERT OR REPLACE INTO password_reset_tokens 
        (user_id, token, expires_at, created_at) 
        VALUES (?, ?, ?, ?)
    ''', (user['id'], reset_token, expires_at, datetime.utcnow()))
    db.commit()
    
    send_password_reset_email(email, reset_token)
    
    return {
        "message": "If the email exists, a password reset link has been sent",
    }

async def list_users_service(admin_user: dict):
    db = get_db_connection_service()
    c = db.cursor()
    c.execute('SELECT id, email, created_at, is_temporary_password, is_admin FROM users')
    users = [dict(row) for row in c.fetchall()]
    return {"users": users}

async def delete_user_service(user_id: int, admin_user: dict):
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    if user and user['is_admin']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    c.execute('DELETE FROM users WHERE id = ? AND is_admin = FALSE', (user_id,))
    if c.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or cannot be deleted"
        )
    db.commit()
    
    return {"message": "User deleted successfully"}

async def reset_password_service(token: str, new_password: str):
    """Reset password using token"""
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('''
        SELECT prt.id, prt.user_id, prt.expires_at, prt.used_at, u.email 
        FROM password_reset_tokens prt
        JOIN users u ON prt.user_id = u.id
        WHERE prt.token = ?
    ''', (token,))
    
    token_data = c.fetchone()
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    if datetime.utcnow() > datetime.fromisoformat(token_data['expires_at']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    if token_data['used_at']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used"
        )
    
    password_hash = hash_password(new_password)
    
    c.execute('''
        UPDATE users 
        SET password_hash = ?, is_temporary_password = FALSE 
        WHERE id = ?
    ''', (password_hash, token_data['user_id']))
    
    c.execute('''
        UPDATE password_reset_tokens 
        SET used_at = ? 
        WHERE id = ?
    ''', (datetime.utcnow(), token_data['id']))
    
    db.commit()
    
    return {"message": "Password reset successfully"}