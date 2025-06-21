import os
import base64
from fastapi import HTTPException, status
from services.database import get_db_connection_service
from constants import OUTPUT_DIR

def get_user_image(image_id: str, current_user: dict) -> str:
    """
    Get a base64-encoded image if it belongs to the current user.
    
    Args:
        image_id: The ID of the image to retrieve
        current_user: Dictionary containing user information with 'id' key
        
    Returns:
        Base64-encoded image string
        
    Raises:
        HTTPException: If image not found, doesn't belong to user, or file doesn't exist
    """
    print(f"DEBUG: Looking for image_id: {image_id} for user_id: {current_user['id']}")
    
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('''
        SELECT m.image_id, ch.user_id, ch.id as chat_id
        FROM messages m
        JOIN chats ch ON m.chat_id = ch.id
        WHERE ch.user_id = ? AND m.image_id IS NOT NULL
    ''', (current_user['id'],))
    
    all_user_images = c.fetchall()
    print(f"DEBUG: All images for user {current_user['id']}: {[dict(row) for row in all_user_images]}")
    
    c.execute('''
        SELECT m.image_id 
        FROM messages m
        JOIN chats ch ON m.chat_id = ch.id
        WHERE m.image_id = ? AND ch.user_id = ?
    ''', (image_id, current_user['id']))
    
    result = c.fetchone()
    print(f"DEBUG: Query result for image {image_id}: {result}")
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found or access denied"
        )
    
    image_path = os.path.join(OUTPUT_DIR, image_id + ".png")
    print(f"DEBUG: Looking for image file at: {image_path}")
    print(f"DEBUG: OUTPUT_DIR is: {OUTPUT_DIR}")
    print(f"DEBUG: File exists: {os.path.exists(image_path)}")
    
    if os.path.exists(OUTPUT_DIR):
        files_in_dir = os.listdir(OUTPUT_DIR)
        print(f"DEBUG: Files in OUTPUT_DIR: {files_in_dir[:10]}")
    else:
        print(f"DEBUG: OUTPUT_DIR does not exist: {OUTPUT_DIR}")
    
    if not os.path.exists(image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image file not found on disk at {image_path}"
        )
    
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            print(f"DEBUG: Successfully encoded image, size: {len(base64_encoded)} characters")
            return base64_encoded
    except IOError as e:
        print(f"DEBUG: IOError reading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading image file: {str(e)}"
        )

async def get_user_image_service(image_id: str, current_user: dict) -> dict:
    """
    Service wrapper for getting user images.
    
    Args:
        image_id: The ID of the image to retrieve
        current_user: Dictionary containing user information
        
    Returns:
        Dictionary containing the base64-encoded image and metadata
    """
    base64_image = get_user_image(image_id, current_user)
    
    image_path = os.path.join(OUTPUT_DIR, image_id + ".png")
    file_size = os.path.getsize(image_path)
    
    return {
        "image_id": image_id,
        "image_data": base64_image,
        "file_size": file_size,
        "encoding": "base64"
    }

def validate_image_ownership(image_id: str, current_user: dict) -> bool:
    """
    Check if an image belongs to the current user without retrieving it.
    
    Args:
        image_id: The ID of the image to validate
        current_user: Dictionary containing user information with 'id' key
        
    Returns:
        True if the image belongs to the user, False otherwise
    """
    db = get_db_connection_service()
    c = db.cursor()
    
    c.execute('''
        SELECT 1 
        FROM messages m
        JOIN chats ch ON m.chat_id = ch.id
        WHERE m.image_id = ? AND ch.user_id = ?
    ''', (image_id, current_user['id']))
    
    return c.fetchone() is not None