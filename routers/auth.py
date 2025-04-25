from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
import uuid
import datetime
from auth.auth import verify_password, get_password_hash, create_access_token
from utils import get_user_details
from Database.database import Database
from models.model import UserLoginSchema as UserLogin, UserSchema as UserSignup

router = APIRouter()
db = Database()

@router.post("/login", tags=["auth"])
async def login(user: UserLogin):
    try:
        # Kullanıcıyı bul
        user_data = None
        users = db.get_all_users()
        for u in users:
            if u["email"] == user.email and not u.get("is_deleted", False):
                user_data = u
                break
        
        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz email veya şifre"
            )
            
        # Şifreyi kontrol et
        if not verify_password(user.password, user_data["password"]):
            raise HTTPException(
                status_code=401,
                detail="Geçersiz email veya şifre"
            )
            
        # JWT token oluştur
        token = create_access_token(user_data["user_id"])
        
        # Kullanıcı bilgilerini getir
        user_details = get_user_details(user_data["user_id"], db)
        
        return {
            "success": True,
            "message": "Kullanıcı bilgileri başarıyla getirildi",
            "data": user_details
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Giriş yapılırken hata oluştu: {str(e)}"
        )

@router.post("/signup", tags=["auth"])
async def signup(user: UserSignup):
    try:
        # Email kontrolü
        users = db.get_all_users()
        for u in users:
            if u["email"] == user.email:
                raise HTTPException(
                    status_code=400,
                    detail="Bu email adresi zaten kullanılıyor"
                )
                
        # Yeni kullanıcı oluştur
        new_user = {
            "user_id": f"usr_{uuid.uuid4().hex[:8]}",
            "email": user.email,
            "password": get_password_hash(user.password),
            "full_name": user.full_name,
            "friends": [],
            "sent_requests": [],
            "received_requests": [],
            "activities": [],
            "is_deleted": False,
            "created_at": datetime.datetime.now().isoformat()
        }
        
        # Veritabanına kaydet
        db.add_user(new_user)
        
        # JWT token oluştur
        token = create_access_token(new_user["user_id"])
        
        # Kullanıcı bilgilerini getir
        user_details = get_user_details(new_user["user_id"], db)
        
        return {
            "success": True,
            "message": "Kayıt başarılı",
            "data": {
                "token": token,
                "user": user_details
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kayıt olurken hata oluştu: {str(e)}"
        ) 