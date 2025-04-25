import Database.database as database
from fastapi import APIRouter, Body, Depends, HTTPException, status
from auth.auth_bearer import JWTBearer
from auth.auth import sign_jwt, decode_jwt
from models.model import PostSchema, UserSchema, UserLoginSchema
from exceptions import AuthenticationError, DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError
import uuid
import datetime
from utils import get_user_details
from websocket_manager import get_manager

router = APIRouter()
db = database.Database()


@router.post("/user/signup", tags=["user"])
async def create_user(user: UserSchema = Body(..., example={
    "email": "ornek@email.com",
    "password": "sifre123",
    "full_name": "Ahmet Yılmaz"
})):
    try:
        # Kullanıcı zaten var mı kontrol et
        existing_users = db.get_all_users()
        for existing_user in existing_users:
            if existing_user["email"] == user.email and not existing_user.get("is_deleted", False):
                raise HTTPException(
                    status_code=400,
                    detail="Bu e-posta adresi zaten kayıtlı"
                )
        
        # Kullanıcı ID'si oluştur
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        
        # Kullanıcı verisine ID'yi ekle
        user_data = user.model_dump()
        user_data["user_id"] = user_id
        user_data["friends"] = []  # Boş arkadaş listesi ekle
        user_data["is_deleted"] = False  # Soft delete için
        
        db.insert_user(user_data)
        return {
            "success": True,
            "message": "Kullanıcı başarıyla kaydedildi",
            "data": {
                "user_id": user_id,
                "email": user.email,
                "full_name": user.full_name
            },
            "token": sign_jwt(user_id, user.email, user.full_name)
        }
    except DuplicateError:
        raise
    except Exception as e:
        raise DatabaseError(f"Kullanıcı kaydı sırasında hata oluştu: {str(e)}")

async def check_user(data: UserLoginSchema):
    try:
        users = db.get_all_users()
        for user in users:
            if user["email"] == data.email and user["password"] == data.password:
                # Eğer user_id yoksa email'i kullan
                return user.get("user_id", user["email"])
        return None
    except Exception as e:
        raise DatabaseError(f"Kullanıcı kontrolü sırasında hata oluştu: {str(e)}")

@router.post("/user/login", tags=["user"])
async def user_login(user: UserLoginSchema = Body(..., example={
    "email": "deneme@gmail.com",
    "password": "123"
})):
    try:
        user_id = await check_user(user)
        if user_id:
            # Kullanıcı bilgilerini getir
            user_details = get_user_details(user_id, db)
            
            return {
                "success": True,
                "message": "Kullanıcı bilgileri başarıyla getirildi",
                "data": user_details,
                "token": sign_jwt(user_id, user.email, user_details["full_name"])
            }
        raise HTTPException(
            status_code=401,
            detail="E-posta veya şifre hatalı"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Giriş işlemi sırasında hata oluştu: {str(e)}"
        )

@router.get("/users", dependencies=[Depends(JWTBearer())], tags=["users"])
async def get_all_users():
    try:
        users = db.get_all_users()
        if not users:
            raise HTTPException(
                status_code=404,
                detail="Hiç kullanıcı bulunamadı"
            )
            
        # Hassas bilgileri çıkar ve silinmemiş kullanıcıları filtrele
        safe_users = []
        for user in users:
            if not user.get("is_deleted", False):
                safe_users.append({
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "fullname": user.get("full_name", ""),
                    "friends": user.get("friends", []),
                    "sent_requests": user.get("sent_requests", []),
                    "received_requests": user.get("received_requests", [])
                })
            
        return {
            "success": True,
            "message": "Kullanıcılar başarıyla getirildi",
            "data": {
                "users": safe_users,
                "total_users": len(safe_users)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcılar getirilirken hata oluştu: {str(e)}"
        )

@router.get("/user/me", dependencies=[Depends(JWTBearer())], tags=["users"])
async def get_my_info(token: str = Depends(JWTBearer())):
    try:
        # JWT token'ı decode et
        decoded_token = decode_jwt(token)
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz token"
            )
            
        current_user_id = decoded_token["user_id"]
        
        # Kullanıcı bilgilerini getir
        user_details = get_user_details(current_user_id, db)
        
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
            detail=f"Kullanıcı bilgileri getirilirken hata oluştu: {str(e)}"
        )

@router.get("/user/profile/{user_id}", dependencies=[Depends(JWTBearer())], tags=["users"])
async def get_user_profile(user_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        # Kullanıcıyı bul
        users = db.get_all_users()
        user = None
        for u in users:
            if u["user_id"] == user_id and not u.get("is_deleted", False):
                user = u
                break
        
        if not user:
            raise NotFoundError("Kullanıcı bulunamadı")
        
        return {
            "success": True,
            "message": "Kullanıcı profili başarıyla getirildi",
            "data": {
                "user_id": user["user_id"],
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "friends": user.get("friends", [])
            }
        }
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Kullanıcı profili getirilirken hata oluştu: {str(e)}")

@router.post("/accept-friend-request", dependencies=[Depends(JWTBearer())], tags=["users"])
async def accept_friend_request(friend_id: str = Body(..., example="usr_12345678"), token: str = Depends(JWTBearer())):
    try:
        # JWT token'ı decode et
        decoded_token = decode_jwt(token)
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz token"
            )
            
        current_user_id = decoded_token["user_id"]
        
        # Mevcut kullanıcıyı bul
        current_user_data = None
        users = db.get_all_users()
        for user in users:
            if user["user_id"] == current_user_id:
                current_user_data = user
                break
        
        if not current_user_data:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı"
            )
        
        # Arkadaş olarak eklenecek kullanıcıyı bul
        friend_user = None
        for user in users:
            if user["user_id"] == friend_id:
                friend_user = user
                break
        
        if not friend_user:
            raise HTTPException(
                status_code=404,
                detail="İstek gönderen kullanıcı bulunamadı"
            )
        
        # İstek var mı kontrol et
        if friend_id not in current_user_data.get("received_requests", []):
            raise HTTPException(
                status_code=404,
                detail="Bu kullanıcıdan gelen arkadaşlık isteği bulunamadı"
            )
        
        # Arkadaş listelerini oluştur/güncelle
        if "friends" not in current_user_data:
            current_user_data["friends"] = []
        if "friends" not in friend_user:
            friend_user["friends"] = []
            
        # Arkadaş listelerine ekle
        current_user_data["friends"].append(friend_id)
        friend_user["friends"].append(current_user_id)
        
        # İstek listelerinden çıkar
        current_user_data["received_requests"].remove(friend_id)
        friend_user["sent_requests"].remove(current_user_id)
        
        # Veritabanını güncelle
        db.update_user(current_user_id, {
            "friends": current_user_data["friends"],
            "received_requests": current_user_data["received_requests"]
        })
        db.update_user(friend_id, {
            "friends": friend_user["friends"],
            "sent_requests": friend_user["sent_requests"]
        })
        
        return {
            "success": True,
            "message": "Arkadaşlık isteği başarıyla kabul edildi",
            "data": {
                "friend_id": friend_id,
                "friend_name": friend_user.get("full_name", "")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Arkadaşlık isteği kabul edilirken hata oluştu: {str(e)}"
        )

@router.get("/users/search", dependencies=[Depends(JWTBearer())], tags=["users"])
async def search_users(q: str):
    try:
        if not q or len(q.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Arama sorgusu boş olamaz"
            )
            
        users = db.get_all_users()
        if not users:
            raise HTTPException(
                status_code=404,
                detail="Hiç kullanıcı bulunamadı"
            )
            
        # Arama sorgusunu küçük harfe çevir ve boşlukları temizle
        search_query = q.lower().strip()
        
        # Kullanıcıları filtrele
        matched_users = []
        for user in users:
            if not user.get("is_deleted", False):
                # full_name None ise boş string kullan
                full_name = user.get("full_name", "") or ""
                full_name = full_name.lower()
                
                # İsim veya soyisim ile eşleşme kontrolü
                name_parts = full_name.split()
                if any(search_query in part for part in name_parts):
                    matched_users.append({
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "full_name": user.get("full_name", ""),
                        "friends": user.get("friends", []),
                        "sent_requests": user.get("sent_requests", []),
                        "received_requests": user.get("received_requests", [])
                    })
        
        return {
            "success": True,
            "message": "Arama sonuçları başarıyla getirildi",
            "data": {
                "users": matched_users,
                "total_results": len(matched_users),
                "search_query": q
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcı araması sırasında hata oluştu: {str(e)}"
        )

@router.post("/add-friend", dependencies=[Depends(JWTBearer())], tags=["users"])
async def add_friend(friend_id: str = Body(..., example="usr_12345678"), token: str = Depends(JWTBearer())):
    try:
        # Token'dan kullanıcı bilgilerini al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        user_id = payload["user_id"]

        # Kullanıcıyı kontrol et
        user = db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

        # Arkadaş isteği gönderilecek kullanıcıyı kontrol et
        friend = db.get_user_by_id(friend_id)
        if not friend:
            raise HTTPException(status_code=404, detail="Arkadaş isteği gönderilecek kullanıcı bulunamadı")

        # Arkadaş isteği zaten gönderilmiş mi kontrol et
        if friend_id in user.get("sent_friend_requests", []):
            raise HTTPException(status_code=400, detail="Arkadaş isteği zaten gönderilmiş")

        # Arkadaş isteği gönder
        db.add_friend_request(user_id, friend_id)

        # Bildirim gönder
        await get_manager().send_notification(
            user_id=friend_id,
            notification_type="friend_request",
            data={
                "from_user_id": user_id,
                "from_user_name": user.get("full_name", ""),
                "timestamp": datetime.now().isoformat()
            }
        )

        return {
            "success": True,
            "message": "Arkadaş isteği başarıyla gönderildi"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Arkadaş isteği gönderilirken hata oluştu: {str(e)}"
        )

@router.get("/friends", dependencies=[Depends(JWTBearer())], tags=["users"])
async def get_friends(token: str = Depends(JWTBearer())):
    try:
        # JWT token'ı decode et
        decoded_token = decode_jwt(token)
        if not decoded_token:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz token"
            )
            
        current_user_id = decoded_token["user_id"]
        
        # Mevcut kullanıcıyı bul
        current_user_data = None
        users = db.get_all_users()
        for user in users:
            if user["user_id"] == current_user_id:
                current_user_data = user
                break
        
        if not current_user_data:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı"
            )
        
        # Arkadaş listesini al
        friends_list = current_user_data.get("friends", [])
        
        # Arkadaşların detaylı bilgilerini topla
        friends_details = []
        for friend_id in friends_list:
            for user in users:
                if user["user_id"] == friend_id:
                    friends_details.append({
                        "user_id": user["user_id"],
                        "full_name": user.get("full_name", ""),
                        "email": user["email"]
                    })
                    break
        
        return {
            "success": True,
            "message": "Arkadaş listesi başarıyla getirildi",
            "data": {
                "friends": friends_details,
                "total_friends": len(friends_details)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Arkadaş listesi getirilirken hata oluştu: {str(e)}"
        )

@router.delete("/user/{user_id}", dependencies=[Depends(JWTBearer())], tags=["users"])
async def soft_delete_user(user_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        # Mevcut kullanıcıyı bul
        current_user_data = None
        users = db.get_all_users()
        for user in users:
            if user["user_id"] == current_user["user_id"]:
                current_user_data = user
                break
        
        if not current_user_data:
            raise NotFoundError("Kullanıcı bulunamadı")
        
        # Silinecek kullanıcıyı bul
        user_to_delete = None
        for user in users:
            if user["user_id"] == user_id and not user.get("is_deleted", False):
                user_to_delete = user
                break
        
        if not user_to_delete:
            raise NotFoundError("Silinecek kullanıcı bulunamadı")
        
        # Kullanıcıyı soft delete yap
        user_to_delete["is_deleted"] = True
        user_to_delete["deleted_at"] = datetime.datetime.now().isoformat()
        
        # Veritabanını güncelle
        db.update_user(user_id, user_to_delete)
        
        return {
            "success": True,
            "message": "Kullanıcı başarıyla silindi",
            "data": {
                "user_id": user_id,
                "deleted_at": user_to_delete["deleted_at"]
            }
        }
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Kullanıcı silinirken hata oluştu: {str(e)}")

@router.get("/notifications", dependencies=[Depends(JWTBearer())], tags=["users"])
async def get_notifications(token: str = Depends(JWTBearer())):
    try:
        # Token'dan kullanıcı bilgilerini al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        user_id = payload["user_id"]

        # TODO: Veritabanından bekleyen bildirimleri getir
        notifications = []  # Buraya veritabanından bildirimleri getir

        return {
            "success": True,
            "message": "Bildirimler başarıyla getirildi",
            "data": notifications
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bildirimler getirilirken hata oluştu: {str(e)}"
        )