from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from models.chat import CreateNewChat, Chat, Message
from Database.chat_db import ChatDatabase
from auth.auth_bearer import JWTBearer
from Database.user_db import UserDB
from Database.database import Database
from auth.auth import decode_jwt
from pydantic import BaseModel
import jwt
from jwt.exceptions import PyJWTError
from Database.database import DatabaseError
from websocket_manager import get_manager

router = APIRouter(prefix="/chat", tags=["chat"])

# Global database instance'ları
db = None
chat_db = None
user_db = None

def init_chat_router(database):
    global db, chat_db, user_db
    db = database
    chat_db = db.chat_db
    user_db = db.user_db

class ChatMessagesResponse(BaseModel):
    messages: List[Message]
    last_message: Optional[Message] = None
    total_messages: int

@router.post("/", response_model=Chat)
async def create_chat(chat_data: CreateNewChat, token: str = Depends(JWTBearer())):
    """
    Yeni bir chat oluştur
    """
    try:
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Kullanıcıların var olduğunu kontrol et ve katılımcı bilgilerini al
        participants_info = []
        for user_id_ in chat_data.participants:
            user = user_db.get_user_by_id(user_id_)
            if not user:
                raise HTTPException(status_code=404, detail=f"Kullanıcı bulunamadı: {user_id_}")
            
            # Katılımcı bilgilerini ekle
            participants_info.append({
                "user_id": user_id_,
                "full_name": user.get("full_name", "Kullanıcı"),
                "profile_picture": user.get("profile_picture", "/default-avatar.png")
            })

        # Kullanıcının katılımcılar arasında olup olmadığını kontrol et
        if user_id not in chat_data.participants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kullanıcı katılımcılar arasında değil"
            )

        # Chat'i oluştur
        chat = chat_db.create_chat(chat_data)
        
        # Katılımcı bilgilerini ekle
        chat.participants_info = participants_info
        
        # Diğer katılımcılara WebSocket üzerinden bildirim gönder
        manager = get_manager()
        if manager:
            await manager.notify_chat_participants(chat, user_id)
        
        return chat

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat oluşturulurken bir hata oluştu: {str(e)}"
        )

@router.get("/", response_model=List[Chat])
async def get_user_chats(token: str = Depends(JWTBearer())):
    """
    Kullanıcının tüm chat'lerini getir
    """
    try:
        print(f"\n=== get_user_chats endpoint başladı ===")
        
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            print("Geçersiz token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            print("Token'da user_id yok")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        print(f"Kullanıcı ID: {user_id}")

        # Chat'leri getir
        chats = chat_db.get_user_chats(user_id)
        print(f"Chat sayısı: {len(chats) if chats else 0}")
        
        if not chats:
            print("Chat bulunamadı")
            return []
        
        # Her chat için katılımcı bilgilerini getir
        for chat in chats:
            print(f"\nChat ID: {chat.chat_id}")
            print(f"Katılımcılar: {chat.participants}")
            
            # Katılımcı bilgilerini al
            participants_info = []
            for participant_id in chat.participants:
                user = user_db.get_user_by_id(participant_id)
                if user:
                    print(f"Katılımcı bulundu: {participant_id}")
                    participants_info.append({
                        "user_id": participant_id,
                        "full_name": user.get("full_name", "Kullanıcı"),
                        "profile_picture": user.get("profile_picture", "/default-avatar.png")
                    })
                else:
                    print(f"Katılımcı bulunamadı: {participant_id}")
            chat.participants_info = participants_info
            
            # Son mesajı kontrol et ve dönüştür
            if chat.last_message:
                print(f"Son mesaj: {chat.last_message.dict()}")
            else:
                print("Son mesaj yok")
        
        print("=== get_user_chats endpoint bitti ===\n")
        return chats
        
    except PyJWTError:
        print("JWT hatası")
        raise HTTPException(status_code=401, detail="Geçersiz token")
    except DatabaseError as e:
        print(f"Veritabanı hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        print(f"Hata tipi: {type(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat list")

@router.get("/with-recent-messages", response_model=List[Chat])
async def get_user_chats_with_recent_messages(token: str = Depends(JWTBearer())):
    """
    Kullanıcının tüm sohbetlerini getirir.
    Son 5 sohbetin son 30 mesajını da içerir.
    """
    try:
        print(f"\n=== get_user_chats_with_recent_messages endpoint başladı ===")
        
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            print("Geçersiz token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            print("Token'da user_id yok")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        print(f"Kullanıcı ID: {user_id}")

        # Chat'leri ve son mesajlarını getir
        
        chats = chat_db.get_user_chats_with_recent_messages(user_id)
        print(f"Chat sayısı: {len(chats) if chats else 0}")
        
        if not chats:
            print("Chat bulunamadı")
            return []
        
        # Her chat için katılımcı bilgilerini getir
        for chat in chats:
            print(f"\nChat ID: {chat.chat_id}")
            print(f"Katılımcılar: {chat.participants}")
            
            # Katılımcı bilgilerini al
            participants_info = []
            for participant_id in chat.participants:
                user = user_db.get_user_by_id(participant_id)
                if user:
                    print(f"Katılımcı bulundu: {participant_id}")
                    participants_info.append({
                        "user_id": participant_id,
                        "full_name": user.get("full_name", "Kullanıcı"),
                        "profile_picture": user.get("profile_picture", "/default-avatar.png")
                    })
                else:
                    print(f"Katılımcı bulunamadı: {participant_id}")
            chat.participants_info = participants_info
        
        print("=== get_user_chats_with_recent_messages endpoint bitti ===\n")
        return chats
        
    except PyJWTError:
        print("JWT hatası")
        raise HTTPException(status_code=401, detail="Geçersiz token")
    except DatabaseError as e:
        print(f"Veritabanı hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"Beklenmeyen hata: {str(e)}")
        print(f"Hata tipi: {type(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Could not retrieve chat list")

@router.get("/{chat_id}/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    chat_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    token: str = Depends(JWTBearer())
):
    """
    Belirli bir chat'in mesajlarını getir
    """
    try:
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Chat'in var olduğunu kontrol et
        chat = chat_db.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat bulunamadı"
            )

        # Kullanıcının chat'e erişim yetkisi var mı kontrol et
        if user_id not in chat.participants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu chat'e erişim yetkiniz yok"
            )

        # Mesajları getir
        messages_data = chat_db.get_chat_messages(chat_id, page, page_size)
        
        # Son mesajı al
        last_message = None
        if messages_data["messages"]:
            last_message = messages_data["messages"][0]  # En son mesaj ilk sırada
            
        return {
            "messages": messages_data["messages"],
            "last_message": last_message,
            "total_messages": messages_data["pagination"]["total_messages"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Mesajlar getirilirken hata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesajlar getirilirken bir hata oluştu: {str(e)}"
        )

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: str, message_id: str, token: str = Depends(JWTBearer())):
    """
    Mesajı sil
    """
    try:
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Mesajı sil
        success = chat_db.delete_message(chat_id, message_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesaj bulunamadı veya silme yetkiniz yok"
            )

        return {"message": "Mesaj başarıyla silindi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj silinirken bir hata oluştu: {str(e)}"
        )

@router.put("/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: str, message_id: str, content: str, token: str = Depends(JWTBearer())):
    """
    Mesajı düzenle
    """
    try:
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Mesajı düzenle
        success = chat_db.edit_message(chat_id, message_id, user_id, content)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesaj bulunamadı veya düzenleme yetkiniz yok"
            )

        return {"message": "Mesaj başarıyla düzenlendi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj düzenlenirken bir hata oluştu: {str(e)}"
        )

@router.put("/{chat_id}/messages/{message_id}/read")
async def mark_message_as_read(chat_id: str, message_id: str, token: str = Depends(JWTBearer())):
    """
    Mesajı okundu olarak işaretle
    """
    try:
        # Token'ı doğrula ve payload'ı al
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Token'dan user_id'yi al
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token"
            )

        # Mesajı okundu olarak işaretle
        success = chat_db.mark_message_as_read(chat_id, message_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mesaj bulunamadı"
            )

        return {"message": "Mesaj okundu olarak işaretlendi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj okundu olarak işaretlenirken bir hata oluştu: {str(e)}"
        )
