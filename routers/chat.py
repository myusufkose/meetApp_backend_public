from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from models.Chat_models import CreateNewChat, Chat, Message
from Database.Chat_db import ChatDatabase
from auth.auth_bearer import JWTBearer
from auth.auth import decode_jwt
from jwt.exceptions import PyJWTError
from exceptions import DatabaseError
from websocket_manager import get_manager
import uuid
from datetime import datetime

router = APIRouter(prefix="/chat", tags=["chat"])

chat_db = ChatDatabase()

def get_user_id(current_user: dict):
    if not current_user:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    return user_id

@router.post("/", response_model=Chat)
async def create_chat(chat_data: CreateNewChat, current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)
        
        # Oluşturan kullanıcıyı katılımcı listesine ekle
        participants = chat_data.participants or []
        if user_id not in participants:
            participants = [user_id] + participants
        chat_data.participants = participants
        
        # Katılımcıların varlığını kontrol et (tek sorguda)
        invalid_ids = chat_db.validate_user_ids(chat_data.participants)
        if invalid_ids:
            raise HTTPException(status_code=404, detail=f"Kullanıcı bulunamadı: {', '.join(invalid_ids)}")
        
        if(chat_data.is_group):
            if(len(chat_data.participants) < 2):
                raise HTTPException(status_code=400, detail="Grup sohbeti için en az 2 kişi gereklidir")
            if(chat_data.group_name == "" or chat_data.group_name == " " or chat_data.group_name is None ):
                raise HTTPException(status_code=400, detail="Grup sohbeti için grup adı boş olamaz")
        else:
            if len(chat_data.participants) != 2:
                raise HTTPException(status_code=400, detail="Birebir sohbet için tam olarak 2 kişi gereklidir")
        
        chat = chat_db.create_chat(chat_data)
        
        if chat_data.message_content:
            message = Message(
                message_id=f"msg_{uuid.uuid4().hex[:8]}",
                content=chat_data.message_content,
                sender_id=user_id,
                timestamp=datetime.now()
            )
            chat_db.add_message(chat.chat_id, message)
            # Chat'i tekrar getir (güncel last_message ile)
            chat = chat_db.get_chat_by_id(chat.chat_id)

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
async def get_user_chats(current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)

        chats = chat_db.get_user_chats(user_id)
        
        return chats
        
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not retrieve chat list")

@router.get("/with-recent-messages", response_model=List[Chat])
async def get_user_chats_with_recent_messages(current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)

        chats = chat_db.get_user_chats_with_recent_messages(user_id)
        
        return chats
        
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Could not retrieve chat list")

@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(JWTBearer())
):
    try:
        user_id = get_user_id(current_user)
        messages_data = chat_db.get_chat_messages(chat_id, page, page_size)
        last_message = messages_data["messages"][0] if messages_data["messages"] else None
        return {
            "messages": messages_data["messages"],
            "last_message": last_message,
            "total_messages": messages_data["pagination"]["total_messages"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesajlar getirilirken bir hata oluştu: {str(e)}"
        )

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: str, message_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)
        success = chat_db.delete_message(chat_id, message_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı veya silme yetkiniz yok")
        return {"message": "Mesaj başarıyla silindi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj silinirken bir hata oluştu: {str(e)}"
        )

@router.put("/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: str, message_id: str, content: str, current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)
        success = chat_db.edit_message(chat_id, message_id, user_id, content)
        if not success:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı veya düzenleme yetkiniz yok")

        return {"message": "Mesaj başarıyla düzenlendi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj düzenlenirken bir hata oluştu: {str(e)}"
        )

@router.put("/{chat_id}/messages/{message_id}/read")
async def mark_message_as_read(chat_id: str, message_id: str, current_user: dict = Depends(JWTBearer())):
    try:
        user_id = get_user_id(current_user)

        success = chat_db.mark_message_as_read(chat_id, message_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı")

        return {"message": "Mesaj okundu olarak işaretlendi"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mesaj okundu olarak işaretlenirken bir hata oluştu: {str(e)}"
        )
