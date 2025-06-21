from fastapi import FastAPI
from routes.auth import router as auth_router
from routes.chats import router as chats_router
from routes.stream import router as stream_router
from routes.tts import router as tts_router
from routes.user import router as user_router
from routes.files import router as files_router
import threading
from services.database import initialize_database
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(auth_router)
app.include_router(chats_router)
app.include_router(stream_router)
app.include_router(tts_router)
app.include_router(user_router)
app.include_router(files_router)

thread_local = threading.local()
initialize_database()
print("Application startup complete - Database ready")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)