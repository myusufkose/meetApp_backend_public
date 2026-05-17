from Database.User_db import UserDB
from fastapi import APIRouter, Body, Depends, HTTPException
from auth.auth_bearer import JWTBearer
from auth.auth import sign_jwt, hash_password, verify_password
from models.UserModels.UserAuthModels import User_Create_Model, User_Login_Model
from models.UserModels.GeneralUserModels import User_Model, Friend_Request_Model, Friend_Request_Status, User_Profile_Model
from exceptions import DatabaseError, NotFoundError
import uuid
import datetime
from websocket_manager import get_manager

router = APIRouter()
db = UserDB()


@router.post("/user/signup", tags=["user"])
async def create_user(user: User_Create_Model):
    # Kullanıcı zaten var mı kontrol et
    existing_users = db.get_all_users()
    for existing_user in existing_users:
        if existing_user["email"] == user.email:
            raise HTTPException(
                status_code=400,
                detail="Bu e-posta adresi zaten kayıtlı"
            )

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    # Şifreyi hashle
    hashed_password = hash_password(user.password)
    
    user_data = User_Model(
        user_id=user_id,
        email=user.email,
        password_hash=hashed_password,
        name=user.name
    )

    # DB'ye ekle
    user_dict = user_data.model_dump()
    db.insert_user(user_dict)
    return {
        "success": True,
        "message": "Kullanıcı başarıyla kaydedildi",
        "data": user_data,
        "token": sign_jwt(user.name, user.email, user_id)
    }

async def check_user(data: User_Login_Model):
    try:
        users = db.get_all_users()
        for user in users:
            if user["email"] == data.email and verify_password(data.password, user["password_hash"]):
                return user
        return None
    except Exception as e:
        # Database hatası oluştuğunda 500 hatası döndür
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcı kontrolü sırasında hata oluştu: {str(e)}"
        )

@router.post("/user/login", tags=["user"])
async def user_login(user: User_Login_Model):
    try:
        User = await check_user(user)
        if User:
            return {
                "success": True,
                "message": "Kullanıcı bilgileri başarıyla getirildi",
                "data": User,
                "token": sign_jwt(User["name"], User["email"], User["user_id"])
            }
        else:
            raise HTTPException(
                status_code=401,
                detail="Email veya şifre yanlış"
            )
    except HTTPException:
        # HTTPException'ları olduğu gibi yukarı fırlat
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Giriş işlemi sırasında hata oluştu: {str(e)}"
        )

@router.get("/users", tags=["users"])
async def get_all_users():
    try:
        users = db.get_all_users()
        if not users:
            raise HTTPException(
                status_code=404,
                detail="Hiç kullanıcı bulunamadı"
            )

        return {
            "success": True,
            "message": "Kullanıcılar başarıyla getirildi",
            "data": {
                "users": users,
                "total_users": len(users)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcılar getirilirken hata oluştu: {str(e)}"
        )


@router.get("/user/me", tags=["users"])
async def get_my_info(current_user: dict = Depends(JWTBearer())):
    try:
        current_user_email = current_user["email"]
        
        # Kullanıcı bilgilerini getir
        user_details = db.get_detailed_user_by_email(current_user_email)
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

@router.get("/user/profile/{user_id}", tags=["users"])
async def get_user_profile(user_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        user_profile = db.get_user_profile(user_id)
        
        if not user_profile:
            raise NotFoundError("Kullanıcı bulunamadı")
        
        return {
            "success": True,
            "message": "Kullanıcı profili başarıyla getirildi",
            "data": user_profile
        }
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Kullanıcı profili getirilirken hata oluştu: {str(e)}")

@router.post("/add-friend", tags=["users"])
async def add_friend(friend_data: dict = Body(..., example={"friend_id": "usr_12345678"}), current_user: dict = Depends(JWTBearer())):
    print("istek alındı ve işleniyor")
    try:
        # Email ile kullanıcıyı bul
        current_user_email = current_user["email"]
        user = db.get_user_by_email(current_user_email)
        if not user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        print("kullanıcı bulundu")
        user_id = user["user_id"]

        # friend_id'yi body'den al
        friend_id = friend_data.get("friend_id")
        if not friend_id:
            raise HTTPException(status_code=400, detail="friend_id gerekli")

        # Arkadaş isteği gönderilecek kullanıcıyı kontrol et
        friend = db.get_user_by_id(friend_id)
        if not friend:
            raise HTTPException(status_code=404, detail="Arkadaş isteği gönderilecek kullanıcı bulunamadı")
        print("arkadaş bulundu")
        # Arkadaş isteği zaten gönderilmiş mi kontrol et
        sent_requests = user.get("friend_requests_sent", [])
        for request in sent_requests:
            if isinstance(request, dict) and request.get("to_user_id") == friend_id:
                raise HTTPException(status_code=400, detail="Arkadaş isteği zaten gönderilmiş")
            elif isinstance(request, str) and request == friend_id:
                raise HTTPException(status_code=400, detail="Arkadaş isteği zaten gönderilmiş")
        print("arkadaş isteği zaten gönderilmiş kontrolü yapıldı")
        friend_request_data = Friend_Request_Model(
            from_user_id=user_id,
            to_user_id=friend_id,
            status=Friend_Request_Status.PENDING,
            created_at=datetime.datetime.now()
        )
        # Arkadaş isteği gönder
        db.add_friend_request(friend_request_data)
        print("arkadaş isteği gönderildi")
        # Bildirim gönder
        await get_manager().send_notification(
            user_id=friend_id,
            notification_type="friend_request",
            data={
                "from_user_id": user_id,
                "from_user_name": user.get("name", ""),
                "timestamp": datetime.datetime.now().isoformat()
            }
        )
        print("bildirim gönderildi")
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

@router.post("/accept-friend-request", tags=["users"])
async def accept_friend_request(friend_id: dict = Body(..., example={"friend_id": "usr_12345678"}), current_user: dict = Depends(JWTBearer())):
    friend_id = friend_id.get("friend_id")
    try:
        # Email ile kullanıcıyı bul
        current_user_email = current_user["email"]
        current_user_data = db.get_user_by_email(current_user_email)
        if not current_user_data:
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı bulunamadı"
            )
        
        current_user_id = current_user_data["user_id"]
        
        # Arkadaş olarak eklenecek kullanıcıyı bul
        friend_user = db.get_user_by_id(friend_id)
        if not friend_user:
            raise HTTPException(
                status_code=404,
                detail="İstek gönderen kullanıcı bulunamadı"
            )
        
        # İstek var mı kontrol et
        received_requests = current_user_data.get("friend_requests_received", [])
        request_found = False
        for request in received_requests:
            if isinstance(request, dict) and request.get("from_user_id") == friend_id:
                request_found = True
                break
            elif isinstance(request, str) and request == friend_id:
                request_found = True
                break
        
        if not request_found:
            raise HTTPException(
                status_code=404,
                detail="Bu kullanıcıdan gelen arkadaşlık isteği bulunamadı"
            )
        
       
        # Arkadaş listelerine ekle
        current_user_data["friends"].append(friend_id)
        friend_user["friends"].append(current_user_id)
        
        # İstek listelerinden çıkar
        # current_user_data'dan friend_id'yi çıkar
        received_requests = current_user_data["friend_requests_received"]
        for i, request in enumerate(received_requests):
            if isinstance(request, dict) and request.get("from_user_id") == friend_id:
                received_requests.pop(i)
                break
            elif isinstance(request, str) and request == friend_id:
                received_requests.pop(i)
                break
        
        # friend_user'dan current_user_id'yi çıkar
        sent_requests = friend_user["friend_requests_sent"]
        for i, request in enumerate(sent_requests):
            if isinstance(request, dict) and request.get("to_user_id") == current_user_id:
                sent_requests.pop(i)
                break
            elif isinstance(request, str) and request == current_user_id:
                sent_requests.pop(i)
                break
        
        # Veritabanını güncelle
        db.update_user(current_user_id, {
            "friends": current_user_data["friends"],
            "friend_requests_received": current_user_data["friend_requests_received"]
        })
        db.update_user(friend_id, {
            "friends": friend_user["friends"],
            "friend_requests_sent": friend_user["friend_requests_sent"]
        })
        
        return {
            "success": True,
            "message": "Arkadaşlık isteği başarıyla kabul edildi",
            "data": {
                "friend_id": friend_id,
                "friend_name": friend_user.get("name", "")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Arkadaşlık isteği kabul edilirken hata oluştu: {str(e)}"
        )

@router.get("/users/search", tags=["users"])
async def search_users(q: str):
    try:
        if not q or len(q.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Arama sorgusu boş olamaz"
            )
        search_query = q.strip()
        users = db.search_users(search_query)
        if not users:
            return {
                "success": True,
                "message": "Arama sonucu bulunamadı",
                "data": {
                    "users": [],
                    "total_results": 0,
                    "search_query": q
                }
            }
        
        return {
            "success": True,
            "message": "Arama sonuçları başarıyla getirildi",
            "data": {
                "users": users,
                "total_results": len(users),
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

@router.get("/friends", tags=["users"])
async def get_friends(current_user: dict = Depends(JWTBearer())):
    try:
        current_user_email = current_user["email"]
        
        # Database'den direkt arkadaş listesini getir
        friends = db.get_user_friends(current_user_email)
        
        return {
            "success": True,
            "message": "Arkadaş listesi başarıyla getirildi",
            "data": {
                "friends": friends,
                "total_friends": len(friends)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Arkadaş listesi getirilirken hata oluştu: {str(e)}"
        )

@router.delete("/user/{user_id}", tags=["users"])
async def soft_delete_user(user_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        # Kullanıcının sadece kendisini silebilmesini sağla
        current_user_email = current_user["email"]
        current_user = db.get_user_by_email(current_user_email)
        
        if not current_user:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        if current_user["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="ID başka bir kullanıcıya ait")
        
        # Kullanıcıyı soft delete yap
        db.soft_delete_user(user_id)
    
        return {
            "success": True,
            "message": "Kullanıcı başarıyla silindi"
        }
    except NotFoundError:
        raise
    except Exception as e:
        raise DatabaseError(f"Kullanıcı silinirken hata oluştu: {str(e)}")

