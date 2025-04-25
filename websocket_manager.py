from fastapi import WebSocket
from typing import Dict, List
import asyncio
from models.chat import Message, MessageContent, MessageStatus
from datetime import datetime
import json
import uuid

class ConnectionManager:
    def __init__(self, db):
        # Kullanıcı ID'sine göre websocket bağlantılarını tutar
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_rooms: Dict[str, List[str]] = {}
        self.chat_db = db.chat_db

    async def connect(self, websocket: WebSocket, user_id: str):
        # Yeni bağlantıyı kabul et ve kaydet
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_rooms[user_id] = []
        print(f"Kullanıcı bağlandı: {user_id}")

    def disconnect(self, user_id: str):
        # Bağlantıyı kaldır
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_rooms:
            del self.user_rooms[user_id]
        print(f"Kullanıcı ayrıldı: {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        # Belirli bir kullanıcıya mesaj gönder
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
            print(f"Kişisel mesaj gönderildi: {message}")

    
    async def handle_read_receipt(self, chat_id: str, message_id: str, user_id: str):
        """
        Okundu bilgisini işle
        """
        # 1. Okundu bilgisini hemen gönder
        chat = self.chat_db.get_chat_by_id(chat_id)
        if chat:
            for participant_id in chat.participants:
                if participant_id != user_id:
                    await self.send_personal_message({
                        "type": "read",
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "user_id": user_id
                    }, participant_id)

        # 2. Veritabanı işlemlerini arka planda yap
        asyncio.create_task(self._update_read_status(chat_id, message_id, user_id))

    async def _update_read_status(self, chat_id: str, message_id: str, user_id: str):
        """
        Okundu durumunu veritabanında güncelle (asenkron)
        """
        try:
            self.chat_db.update_message_status(
                chat_id,
                message_id,
                user_id,
                is_read=True
            )
        except Exception as e:
            print(f"Okundu durumu güncelleme hatası: {str(e)}")

    async def handle_chat_message(self, websocket: WebSocket, message: dict):
        """
        Chat mesajını işle
        """
        try:
            print(f"\n=== handle_chat_message başladı ===")
            print(f"Gelen mesaj: {message}")
            
            # Mesaj içeriğini doğrula
            if not all(k in message for k in ["chat_id", "content", "sender_id", "timestamp"]):
                raise ValueError("Geçersiz mesaj formatı")

            # Mesaj içeriğini düzenle
            content = message["content"]
            if content["type"] == "text":
                content = {
                    "type": "text",
                    "text": content["text"],
                    "content": content["text"]  # text mesajları için content de text olmalı
                }
            
            # Mesajı oluştur
            new_message = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "chat_id": message["chat_id"],
                "sender_id": message["sender_id"],
                "content": content,
                "timestamp": message["timestamp"],
                "status": {
                    "read_by": [],
                    "delivered_to": []
                }
            }

            print(f"Oluşturulan mesaj: {new_message}")

            # Mesajı veritabanına kaydet
            success = self.chat_db.save_message(new_message)
            if not success:
                raise ValueError("Mesaj kaydedilemedi")

            print("Mesaj veritabanına kaydedildi")

            # Mesajı chat katılımcılarına gönder
            chat = self.chat_db.get_chat_by_id(message["chat_id"])
            if chat:
                print(f"Chat bulundu: {chat.dict()}")
                print(f"Katılımcılar: {chat.participants}")
                
                # Mesajı tüm katılımcılara gönder (gönderen dahil)
                for participant_id in chat.participants:
                    print(f"Mesaj gönderiliyor: {participant_id}")
                    # Mesajı JSON serileştirilebilir formata dönüştür
                    message_to_send = {
                        "type": "chat_message",
                        "message": {
                            "message_id": new_message["message_id"],
                            "chat_id": new_message["chat_id"],
                            "sender_id": new_message["sender_id"],
                            "content": new_message["content"],
                            "timestamp": new_message["timestamp"],
                            "status": new_message["status"]
                        }
                    }
                    await self.send_personal_message(message_to_send, participant_id)
                    print(f"Mesaj gönderildi: {participant_id}")

            print("=== handle_chat_message bitti ===\n")

        except Exception as e:
            print(f"Mesaj işleme hatası: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            
            # Hata mesajını gönderene bildir
            await self.send_personal_message(
                {
                    "type": "error",
                    "message": "Mesaj gönderilemedi",
                    "details": str(e)
                },
                message["sender_id"]
            )

    async def handle_friend_request(self, user_id: str, data: dict):
        """
        Arkadaşlık isteği işle
        """
        try:
            # Arkadaşlık isteği bildirimini gönder
            notification = {
                "type": "notification",
                "notification_type": "friend_request",
                "from_user_id": user_id,
                "to_user_id": data["to_user_id"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_personal_message(notification, data["to_user_id"])
            print(f"Arkadaşlık isteği işlendi: {notification}")
            
        except Exception as e:
            print(f"Arkadaşlık isteği işleme hatası: {str(e)}")

    async def handle_typing(self, user_id: str, data: dict):
        """
        Yazıyor bildirimini işle
        """
        try:
            # Yazıyor bildirimini gönder
            typing_message = {
                "type": "typing",
                "user_id": user_id,
                "chat_id": data["chat_id"],
                "is_typing": data["is_typing"]
            }
            
            # Chat katılımcılarına gönder
            chat = self.chat_db.get_chat_by_id(data["chat_id"])
            if chat:
                for participant_id in chat.participants:
                    if participant_id != user_id:  # Gönderen hariç
                        await self.send_personal_message(typing_message, participant_id)
            
            print(f"Yazıyor bildirimi işlendi: {typing_message}")
            
        except Exception as e:
            print(f"Yazıyor bildirimi işleme hatası: {str(e)}")

    async def handle_friend_request_response(self, user_id: str, data: dict):
        """
        Arkadaşlık isteği yanıtını işle
        """
        try:
            # Arkadaşlık isteği yanıtını gönder
            response = {
                "type": "friend_request_response",
                "from_user_id": user_id,
                "request_id": data["request_id"],
                "accepted": data["accepted"],
                "timestamp": datetime.now().isoformat()
            }
            
            # İsteği gönderen kullanıcıya yanıtı gönder
            await self.send_personal_message(response, data["from_user_id"])
            print(f"Arkadaşlık isteği yanıtı işlendi: {response}")
            
        except Exception as e:
            print(f"Arkadaşlık isteği yanıtı işleme hatası: {str(e)}")

    async def notify_chat_participants(self, chat, exclude_user_id: str):
        """
        Yeni chat oluşturulduğunda diğer katılımcılara bildirim gönder
        """
        try:
            # Chat'i JSON serileştirilebilir formata dönüştür
            chat_dict = chat.dict()
            
            # Diğer katılımcılara bildirim gönder (oluşturan kişi hariç)
            for participant_id in chat.participants:
                if participant_id != exclude_user_id:  # Oluşturan kişiye bildirim gönderme
                    await self.send_personal_message({
                        "type": "new_chat",
                        "chat": chat_dict
                    }, participant_id)
                    print(f"Yeni chat bildirimi gönderildi: {participant_id}")
            
        except Exception as e:
            print(f"Yeni chat bildirimi gönderme hatası: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")

# Global manager instance
_manager = None

def init_manager(db):
    global _manager
    if _manager is None:
        _manager = ConnectionManager(db)

def get_manager():
    global _manager
    if _manager is None:
        raise RuntimeError("WebSocket manager is not initialized")
    return _manager 