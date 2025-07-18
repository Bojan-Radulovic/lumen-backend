import os

SECRET_KEY = ""
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'app.db')

OUTPUT_DIR = 'images'
MAILJET_API_KEY = ""
MAILJET_SECRET_KEY = ""

ADMIN_EMAIL = ""
ADMIN_PASSWORD = ""

CHANGE_PASSWORD_LINK = "http://localhost:3000"