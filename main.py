from fastapi import FastAPI, Depends, Body, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pymongo.errors import PyMongoError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from routers import users, activities, chat, websocket
from auth import auth
from auth.auth import sign_jwt
from exceptions import DatabaseError, AuthenticationError, ValidationError, NotFoundError, DuplicateError
from error_handler import (
    validation_exception_handler,
    database_exception_handler,
    authentication_exception_handler,
    not_found_exception_handler,
    duplicate_exception_handler,
    pymongo_exception_handler,
    generic_exception_handler
)
from Database.database import Database
from datetime import datetime
import json
import uvicorn
import os
from dotenv import load_dotenv
import asyncio
import signal
import sys

# .env dosyasını yükle
load_dotenv()

app = FastAPI()

# Exception handler'ları ekle
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DatabaseError, database_exception_handler)
app.add_exception_handler(AuthenticationError, authentication_exception_handler)
app.add_exception_handler(NotFoundError, not_found_exception_handler)
app.add_exception_handler(DuplicateError, duplicate_exception_handler)
app.add_exception_handler(PyMongoError, pymongo_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS ayarlarını güncelle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme için tüm originlere izin ver
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ObjectId'yi JSON'a dönüştürmek için özel encoder
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

# Özel JSON response sınıfı
class CustomJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(content, cls=JSONEncoder)

# Global database instance
db = None

# Router'ları ekle
app.include_router(users.router)
app.include_router(activities.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(websocket.router)

@app.get("/")
def read_root():
    return {"Hello": "World", "status": "running"}

# Uygulama başlangıç ve kapanış işlemleri
@app.on_event("startup")
async def startup_event():
    global db
    print("Uygulama başlatılıyor...")
    try:
        # Veritabanı bağlantısını test et
        db = Database()
        db.db.list_collection_names()
        print("Veritabanı bağlantısı başarılı")
        
        # WebSocket manager'ı başlat
        from websocket_manager import init_manager
        init_manager(db)
        print("WebSocket manager başlatıldı")
        
        # Chat router'ı başlat
        from routers.chat import init_chat_router
        init_chat_router(db)
        print("Chat router başlatıldı")
        
    except Exception as e:
        print(f"Başlatma hatası: {str(e)}")
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    global db
    print("Uygulama kapatılıyor...")
    # WebSocket bağlantılarını kapat
    from websocket_manager import get_manager
    manager = get_manager()
    if manager:
        for user_id in list(manager.active_connections.keys()):
            manager.disconnect(user_id)
    # Veritabanı bağlantılarını kapat
    try:
        if db:
            db.close()
    except Exception as e:
        print(f"Veritabanı kapatma hatası: {str(e)}")

# Graceful shutdown için sinyal işleyicileri
def signal_handler(sig, frame):
    print("\nUygulama kapatılıyor...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)