from typing import List
import uuid
from datetime import datetime

async def create_chat(user_id: str, participants: List[str]) -> Chat:
    """
    Yeni bir chat oluşturur ve katılımcılara bildirim gönderir
    """
    try:
        # Chat'i oluştur
        chat = Chat(
            id=str(uuid.uuid4()),
            participants=participants,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Chat'i veritabanına kaydet
        await save_chat(chat)
        
        # Diğer katılımcılara bildirim gönder
        await manager.notify_chat_participants(chat, user_id)
        
        return chat
    except Exception as e:
        print(f"Chat oluşturma hatası: {str(e)}")
        raise 