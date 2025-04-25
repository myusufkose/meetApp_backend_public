from typing import List, Optional
from models.chat import Chat, Message, CreateNewChat
from exceptions import DatabaseError
from datetime import datetime
from pymongo import MongoClient

class ChatDatabase:
    def __init__(self, db):
        print("\n=== ChatDatabase başlatılıyor ===")
        self.chats = db["chats"]
        self.messages = db["messages"]
        self.db = db
        print(f"chats ve messages koleksiyonları seçildi")
        
        # chats koleksiyonundaki toplam doküman sayısını göster
        total_chats = self.chats.count_documents({})
        print(f"\nToplam chat sayısı: {total_chats}")
        
        # Örnek bir chat göster
        if total_chats > 0:
            sample_chat = self.chats.find_one()
            print(f"\nÖrnek chat:")
            print(f"Chat ID: {sample_chat.get('chat_id')}")
            print(f"Katılımcılar: {sample_chat.get('participants')}")
        
        print("=== ChatDatabase başlatma tamamlandı ===\n")

    def __del__(self):
        try:
            if hasattr(self, 'client'):
                self.client.close()
        except Exception as e:
            print(f"Veritabanı bağlantı kapatma hatası: {str(e)}")

    def create_chat(self, chat_data: CreateNewChat) -> Chat:
        """
        Yeni bir chat oluştur
        """
        try:
            # Chat nesnesini oluştur
            chat = Chat(
                participants=chat_data.participants,
                is_group=chat_data.is_group,
                group_name=chat_data.group_name,
                group_admin=chat_data.group_admin,
                messages=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                is_active=True
            )

            # Katılımcı bilgilerini al
            participants_info = []
            for user_id in chat_data.participants:
                user = self.db["users"].find_one({"user_id": user_id})
                if user:
                    participants_info.append({
                        "user_id": user_id,
                        "full_name": user.get("full_name", "Kullanıcı"),
                        "profile_picture": user.get("profile_picture", "/default-avatar.png")
                    })
            
            # Katılımcı bilgilerini ekle
            chat.participants_info = participants_info

            # MongoDB'ye ekle
            self.chats.insert_one(chat.dict())
            return chat
        except Exception as e:
            raise DatabaseError(f"Chat oluşturma hatası: {str(e)}")

    def get_chat_by_id(self, chat_id: str) -> Optional[Chat]:
        """
        Chat ID'sine göre chat'i getir
        """
        try:
            # Chat ve son mesajını tek sorguda getir
            pipeline = [
                {"$match": {
                    "chat_id": chat_id,
                    "is_active": True
                }},
                {"$lookup": {
                    "from": "messages",
                    "let": {"chat_id": "$chat_id"},
                    "pipeline": [
                        {"$match": {
                            "$expr": {"$eq": ["$chat_id", "$$chat_id"]}
                        }},
                        {"$sort": {"timestamp": -1}},
                        {"$limit": 1}
                    ],
                    "as": "last_message"
                }},
                {"$unwind": {
                    "path": "$last_message",
                    "preserveNullAndEmptyArrays": True
                }},
                {"$addFields": {
                    "last_message": {
                        "$cond": {
                            "if": {"$eq": ["$last_message", None]},
                            "then": None,
                            "else": {
                                "message_id": "$last_message.message_id",
                                "chat_id": "$last_message.chat_id",
                                "sender_id": "$last_message.sender_id",
                                "content": "$last_message.content",
                                "timestamp": "$last_message.timestamp",
                                "status": "$last_message.status"
                            }
                        }
                    }
                }},
                {"$project": {
                    "_id": 0,  # _id alanını hariç tut
                    "chat_id": 1,
                    "participants": 1,
                    "is_group": 1,
                    "group_name": 1,
                    "group_admin": 1,
                    "messages": 1,
                    "last_message": 1,
                    "created_at": 1,
                    "updated_at": 1,
                    "is_active": 1,
                    "unread_count": 1
                }}
            ]
            
            chat_data = self.chats.aggregate(pipeline).next()
            if chat_data:
                return Chat(**chat_data)
            return None
        except Exception as e:
            raise DatabaseError(f"Chat getirme hatası: {str(e)}")

    def add_message(self, chat_id: str, message: Message):
        """
        Chat'e yeni mesaj ekle
        """
        try:
            self.messages.insert_one(message.dict())
            self.chats.update_one(
                {"chat_id": chat_id},
                {"$set": {"updated_at": datetime.now().isoformat()}}
            )
            return True
        except Exception as e:
            raise DatabaseError(f"Mesaj ekleme hatası: {str(e)}")

    def update_message_status(self, chat_id: str, message_id: str, user_id: str, is_delivered: bool = False, is_read: bool = False):
        """
        Mesaj durumunu güncelle
        """
        try:
            # Mesajı bul
            message = self.messages.find_one({
                "chat_id": chat_id,
                "message_id": message_id
            })
            
            if not message:
                raise DatabaseError("Mesaj bulunamadı")
            
            # Güncelleme verilerini hazırla
            update_data = {}
            
            if is_delivered:
                if "delivered_to" not in message.get("status", {}):
                    update_data["status.delivered_to"] = []
                update_data["$addToSet"] = {"status.delivered_to": user_id}
            
            if is_read:
                if "read_by" not in message.get("status", {}):
                    update_data["status.read_by"] = []
                update_data["$addToSet"] = {"status.read_by": user_id}
            
            # Mesajı güncelle
            self.messages.update_one(
                {
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                {
                    "$set": update_data
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Mesaj durumu güncelleme hatası: {str(e)}")

    def delete_message(self, chat_id: str, message_id: str, user_id: str):
        """
        Mesajı yumuşak sil (soft delete)
        """
        try:
            # Mesajın varlığını ve sahipliğini kontrol et
            message = self.messages.find_one({
                "chat_id": chat_id,
                "message_id": message_id,
                "sender_id": user_id
            })
            
            if not message:
                raise DatabaseError("Mesaj bulunamadı veya silme yetkiniz yok")
            
            # Mesajı silmek yerine deleted alanını güncelle
            self.messages.update_one(
                {
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                {
                    "$set": {
                        "deleted": True,
                        "deleted_at": datetime.now().isoformat(),
                        "deleted_by": user_id
                    }
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Mesaj silme hatası: {str(e)}")

    def edit_message(self, chat_id: str, message_id: str, user_id: str, content: str):
        """
        Mesajı düzenle ve düzenleme geçmişini tut
        """
        try:
            # Mesajın varlığını ve sahipliğini kontrol et
            message = self.messages.find_one({
                "chat_id": chat_id,
                "message_id": message_id,
                "sender_id": user_id,
                "deleted": {"$ne": True}  # Silinmiş mesajları düzenleyemez
            })
            
            if not message:
                raise DatabaseError("Mesaj bulunamadı veya düzenleme yetkiniz yok")
            
            # Düzenleme geçmişini oluştur
            edit_history = message.get("edit_history", [])
            edit_history.append({
                "old_content": message["content"],
                "edited_at": datetime.now().isoformat(),
                "edited_by": user_id
            })
            
            # Mesajı güncelle
            self.messages.update_one(
                {
                    "chat_id": chat_id,
                    "message_id": message_id
                },
                {
                    "$set": {
                        "content": content,
                        "edited": True,
                        "edit_history": edit_history,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Mesaj düzenleme hatası: {str(e)}")

    def get_message_history(self, chat_id: str, message_id: str) -> List[dict]:
        """
        Mesajın düzenleme geçmişini getir
        """
        try:
            message = self.messages.find_one({
                "chat_id": chat_id,
                "message_id": message_id
            })
            
            if not message:
                raise DatabaseError("Mesaj bulunamadı")
            
            return message.get("edit_history", [])
        except Exception as e:
            raise DatabaseError(f"Mesaj geçmişi getirme hatası: {str(e)}")

    def get_user_chats(self, user_id: str) -> List[Chat]:
        """
        Kullanıcının tüm chat'lerini getir
        """
        try:
            print(f"\n=== get_user_chats başladı ===")
            print(f"Kullanıcı ID: {user_id}")
            
            # Chat'leri ve son mesajlarını tek sorguda getir
            pipeline = [
                {"$match": {
                    "participants": user_id,
                    "is_active": True
                }},
                {"$lookup": {
                    "from": "messages",
                    "let": {"chat_id": "$chat_id"},
                    "pipeline": [
                        {"$match": {
                            "$expr": {"$eq": ["$chat_id", "$$chat_id"]}
                        }},
                        {"$sort": {"timestamp": -1}},
                        {"$limit": 1}
                    ],
                    "as": "last_message"
                }},
                {"$unwind": {
                    "path": "$last_message",
                    "preserveNullAndEmptyArrays": True
                }},
                {"$sort": {"updated_at": -1}}
            ]
            
            print(f"\nPipeline: {pipeline}")
            
            # Önce basit bir sorgu ile chat'leri kontrol et
            simple_query = {"participants": user_id, "is_active": True}
            print(f"\nBasit sorgu sonucu:")
            simple_result = list(self.chats.find(simple_query))
            print(f"Bulunan chat sayısı: {len(simple_result)}")
            for chat in simple_result:
                print(f"Chat ID: {chat.get('chat_id')}, Participants: {chat.get('participants')}")
            
            chats = []
            print("\nAggregation pipeline sonucu:")
            for chat_data in self.chats.aggregate(pipeline):
                print(f"\nChat verisi: {chat_data}")
                
                # Chat nesnesini oluştur
                chat = Chat(
                    chat_id=chat_data["chat_id"],
                    participants=chat_data["participants"],
                    is_group=chat_data.get("is_group", False),
                    group_name=chat_data.get("group_name"),
                    group_admin=chat_data.get("group_admin"),
                    created_at=chat_data["created_at"],
                    updated_at=chat_data["updated_at"],
                    is_active=chat_data["is_active"]
                )
                
                print(f"Oluşturulan chat nesnesi: {chat.dict()}")
                
                # Son mesajı ekle
                if "last_message" in chat_data:
                    print(f"Son mesaj verisi: {chat_data['last_message']}")
                    chat.last_message = Message(
                        message_id=chat_data["last_message"]["message_id"],
                        chat_id=chat_data["chat_id"],
                        sender_id=chat_data["last_message"]["sender_id"],
                        content=chat_data["last_message"]["content"],
                        timestamp=chat_data["last_message"]["timestamp"],
                        status=chat_data["last_message"].get("status", {})
                    )
                
                chats.append(chat)
            
            print(f"\nToplam dönen chat sayısı: {len(chats)}")
            print("=== get_user_chats bitti ===\n")
            
            return chats
        except Exception as e:
            print(f"\n!!! HATA !!!")
            print(f"Hata mesajı: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            print("!!! HATA !!!\n")
            raise DatabaseError(f"Chat listesi getirme hatası: {str(e)}")

    def get_chat_messages(self, chat_id: str, page: int = 1, page_size: int = 20) -> dict:
        """
        Belirli bir chat'in mesajlarını getir
        """
        try:
            # Chat'in varlığını kontrol et
            chat = self.get_chat_by_id(chat_id)
            if not chat:
                raise DatabaseError("Chat bulunamadı")

            # Toplam mesaj sayısını al
            total_messages = self.messages.count_documents({"chat_id": chat_id})
            
            # Toplam sayfa sayısını hesapla
            total_pages = (total_messages + page_size - 1) // page_size if total_messages > 0 else 1
            
            # Sayfa numarasını kontrol et
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages

            # Mesajları getir (en yeniden eskiye sıralı)
            messages = list(self.messages.find(
                {"chat_id": chat_id},
                sort=[("timestamp", -1)]  # En yeni mesajlar önce
            ).skip((page - 1) * page_size).limit(page_size))

            # Mesajları Message nesnelerine dönüştür
            message_objects = []
            for message in messages:
                try:
                    # Eğer content yoksa varsayılan değerler kullan
                    if not message.get('content'):
                        message['content'] = {
                            'type': 'text',
                            'text': '',
                            'content': ''
                        }
                    message_objects.append(Message(**message))
                except Exception as e:
                    print(f"Mesaj dönüştürme hatası: {str(e)}")
                    continue

            return {
                "messages": message_objects,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_messages": total_messages,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        except Exception as e:
            raise DatabaseError(f"Mesajları getirme hatası: {str(e)}")

    def get_message_count(self, chat_id: str) -> int:
        """
        Bir chat'teki toplam mesaj sayısını getir
        """
        try:
            return self.messages.count_documents({"chat_id": chat_id})
        except Exception as e:
            raise DatabaseError(f"Mesaj sayısı getirme hatası: {str(e)}")

    def add_participant_to_group(self, chat_id: str, user_id: str, added_by: str):
        """
        Gruba yeni katılımcı ekle
        """
        try:
            # Chat'in grup olduğunu ve ekleyen kişinin admin olduğunu kontrol et
            chat = self.get_chat_by_id(chat_id)
            if not chat or not chat.is_group:
                raise DatabaseError("Grup bulunamadı")
            
            if chat.group_admin != added_by:
                raise DatabaseError("Grup yöneticisi değilsiniz")
            
            # Kullanıcıyı ekle
            self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$addToSet": {"participants": user_id},
                    "$set": {"updated_at": datetime.now().isoformat()}
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Katılımcı ekleme hatası: {str(e)}")

    def remove_participant_from_group(self, chat_id: str, user_id: str, removed_by: str):
        """
        Gruptan katılımcı çıkar
        """
        try:
            # Chat'in grup olduğunu ve çıkaran kişinin admin olduğunu kontrol et
            chat = self.get_chat_by_id(chat_id)
            if not chat or not chat.is_group:
                raise DatabaseError("Grup bulunamadı")
            
            if chat.group_admin != removed_by:
                raise DatabaseError("Grup yöneticisi değilsiniz")
            
            # Admin kendini çıkaramaz
            if user_id == chat.group_admin:
                raise DatabaseError("Grup yöneticisi gruptan çıkarılamaz")
            
            # Kullanıcıyı çıkar
            self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$pull": {"participants": user_id},
                    "$set": {"updated_at": datetime.now().isoformat()}
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Katılımcı çıkarma hatası: {str(e)}")

    def change_group_admin(self, chat_id: str, new_admin_id: str, current_admin_id: str):
        """
        Grup yöneticisini değiştir
        """
        try:
            # Chat'in grup olduğunu ve mevcut admin olduğunu kontrol et
            chat = self.get_chat_by_id(chat_id)
            if not chat or not chat.is_group:
                raise DatabaseError("Grup bulunamadı")
            
            if chat.group_admin != current_admin_id:
                raise DatabaseError("Grup yöneticisi değilsiniz")
            
            # Yeni admin grubun üyesi olmalı
            if new_admin_id not in chat.participants:
                raise DatabaseError("Yeni yönetici grubun üyesi değil")
            
            # Yöneticiyi değiştir
            self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "group_admin": new_admin_id,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Yönetici değiştirme hatası: {str(e)}")

    def get_group_info(self, chat_id: str) -> dict:
        """
        Grup bilgilerini getir
        """
        try:
            chat = self.get_chat_by_id(chat_id)
            if not chat or not chat.is_group:
                raise DatabaseError("Grup bulunamadı")
            
            # Grup üyelerinin detaylı bilgilerini getir
            participants_info = []
            for participant_id in chat.participants:
                # Burada kullanıcı bilgilerini getiren bir servis çağrısı yapılabilir
                participants_info.append({
                    "user_id": participant_id,
                    "is_admin": participant_id == chat.group_admin
                })
            
            return {
                "chat_id": chat.chat_id,
                "group_name": chat.group_name,
                "group_admin": chat.group_admin,
                "participants": participants_info,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at
            }
        except Exception as e:
            raise DatabaseError(f"Grup bilgileri getirme hatası: {str(e)}")

    def add_media_message(self, chat_id: str, message: Message, media_url: str, media_type: str, thumbnail_url: str = None):
        """
        Medya içerikli mesaj ekle
        """
        try:
            # Medya tipini kontrol et
            if media_type not in ["image", "video", "audio", "file"]:
                raise DatabaseError("Geçersiz medya tipi")
            
            # Mesaj içeriğini güncelle
            message.content = {
                "type": "media",
                "media_type": media_type,
                "media_url": media_url,
                "thumbnail_url": thumbnail_url,
                "text": message.content.get("text", "") if isinstance(message.content, dict) else str(message.content)
            }
            
            # Mesajı kaydet
            self.messages.insert_one(message.dict())
            
            # Chat'i güncelle
            self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "updated_at": datetime.now().isoformat(),
                        "last_message": message.dict()
                    }
                }
            )
            
            return True
        except Exception as e:
            raise DatabaseError(f"Medya mesajı ekleme hatası: {str(e)}")

    def get_media_messages(self, chat_id: str, media_type: str = None, page: int = 1, page_size: int = 20) -> dict:
        """
        Medya mesajlarını getir
        """
        try:
            # Sorgu filtresini oluştur
            query = {
                "chat_id": chat_id,
                "content.type": "media"
            }
            
            if media_type:
                query["content.media_type"] = media_type
            
            # Toplam mesaj sayısını al
            total_messages = self.messages.count_documents(query)
            
            # Toplam sayfa sayısını hesapla
            total_pages = (total_messages + page_size - 1) // page_size
            
            # Mesajları getir
            messages = list(self.messages.find(
                query,
                sort=[("timestamp", -1)]
            ).skip((page - 1) * page_size).limit(page_size))
            
            # Mesajları Message nesnelerine dönüştür
            message_objects = [Message(**message) for message in messages]
            
            return {
                "messages": message_objects,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_messages": total_messages,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        except Exception as e:
            raise DatabaseError(f"Medya mesajları getirme hatası: {str(e)}")

    def search_messages(self, chat_id: str, query: str, page: int = 1, page_size: int = 20) -> dict:
        """
        Mesajlarda arama yap
        """
        try:
            # Arama sorgusunu oluştur
            search_query = {
                "chat_id": chat_id,
                "$or": [
                    {"content.text": {"$regex": query, "$options": "i"}},
                    {"content.media_url": {"$regex": query, "$options": "i"}}
                ]
            }
            
            # Toplam sonuç sayısını al
            total_results = self.messages.count_documents(search_query)
            
            # Toplam sayfa sayısını hesapla
            total_pages = (total_results + page_size - 1) // page_size
            
            # Sonuçları getir
            results = list(self.messages.find(
                search_query,
                sort=[("timestamp", -1)]
            ).skip((page - 1) * page_size).limit(page_size))
            
            # Sonuçları Message nesnelerine dönüştür
            message_objects = [Message(**result) for result in results]
            
            return {
                "messages": message_objects,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_results": total_results,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        except Exception as e:
            raise DatabaseError(f"Mesaj arama hatası: {str(e)}")

    def filter_messages(self, chat_id: str, filters: dict, page: int = 1, page_size: int = 20) -> dict:
        """
        Mesajları filtrele
        """
        try:
            # Filtre sorgusunu oluştur
            filter_query = {"chat_id": chat_id}
            
            # Mesaj tipi filtresi
            if "message_type" in filters:
                filter_query["content.type"] = filters["message_type"]
            
            # Tarih aralığı filtresi
            if "start_date" in filters and "end_date" in filters:
                filter_query["timestamp"] = {
                    "$gte": filters["start_date"],
                    "$lte": filters["end_date"]
                }
            
            # Gönderen kullanıcı filtresi
            if "sender_id" in filters:
                filter_query["sender_id"] = filters["sender_id"]
            
            # Medya tipi filtresi
            if "media_type" in filters:
                filter_query["content.media_type"] = filters["media_type"]
            
            # Toplam sonuç sayısını al
            total_results = self.messages.count_documents(filter_query)
            
            # Toplam sayfa sayısını hesapla
            total_pages = (total_results + page_size - 1) // page_size
            
            # Sonuçları getir
            results = list(self.messages.find(
                filter_query,
                sort=[("timestamp", -1)]
            ).skip((page - 1) * page_size).limit(page_size))
            
            # Sonuçları Message nesnelerine dönüştür
            message_objects = [Message(**result) for result in results]
            
            return {
                "messages": message_objects,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_results": total_results,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                }
            }
        except Exception as e:
            raise DatabaseError(f"Mesaj filtreleme hatası: {str(e)}")

    def save_message(self, message: dict) -> bool:
        """
        Yeni mesaj kaydet
        """
        try:
            # Mesajı messages koleksiyonuna ekle
            self.messages.insert_one(message)
            
            # Chat'in son mesajını güncelle
            self.chats.update_one(
                {"chat_id": message["chat_id"]},
                {
                    "$set": {
                        "last_message": {
                            "message_id": message["message_id"],
                            "content": message["content"],
                            "sender_id": message["sender_id"],
                            "timestamp": message["timestamp"]
                        },
                        "updated_at": datetime.now().isoformat()
                    },
                    "$inc": {"unread_count": 1}
                }
            )
            return True
        except Exception as e:
            print(f"Mesaj kaydetme hatası: {str(e)}")
            return False

    def get_user_chats_with_recent_messages(self, user_id: str) -> List[Chat]:
        """
        Kullanıcının tüm chat'lerini getirir.
        Son 5 sohbetin son 30 mesajını da içerir.
        """
        try:
            print(f"\n=== get_user_chats_with_recent_messages başladı ===")
            print(f"Kullanıcı ID: {user_id}")
            
            # Önce kullanıcının tüm sohbetlerini al
            pipeline = [
                {"$match": {
                    "participants": user_id,
                    "is_active": True
                }},
                {"$sort": {"updated_at": -1}}  # En son güncellenen sohbetler önce
            ]
            
            all_chats = list(self.chats.aggregate(pipeline))
            print(f"Toplam sohbet sayısı: {len(all_chats)}")
            
            # Son 5 sohbeti ayır
            recent_chats = all_chats[:5]
            other_chats = all_chats[5:]
            
            print(f"Son 5 sohbet: {len(recent_chats)}")
            print(f"Diğer sohbetler: {len(other_chats)}")
            
            # Son 5 sohbetin mesajlarını al
            for chat_data in recent_chats:
                chat_id = chat_data["chat_id"]
                messages_pipeline = [
                    {"$match": {"chat_id": chat_id}},
                    {"$sort": {"timestamp": -1}},  # En son mesajlar önce
                    {"$limit": 30}  # Son 30 mesaj
                ]
                
                chat_messages = list(self.messages.aggregate(messages_pipeline))
                chat_data["messages"] = chat_messages
                print(f"Chat {chat_id} için {len(chat_messages)} mesaj bulundu")
            
            # Tüm sohbetleri birleştir
            all_chats = recent_chats + other_chats
            
            # Chat nesnelerini oluştur
            chats = []
            for chat_data in all_chats:
                chat = Chat(
                    chat_id=chat_data["chat_id"],
                    participants=chat_data["participants"],
                    is_group=chat_data.get("is_group", False),
                    group_name=chat_data.get("group_name"),
                    group_admin=chat_data.get("group_admin"),
                    created_at=chat_data["created_at"],
                    updated_at=chat_data["updated_at"],
                    is_active=chat_data["is_active"]
                )
                
                # Son mesajı ekle
                if "messages" in chat_data and chat_data["messages"]:
                    chat.last_message = Message(
                        message_id=chat_data["messages"][0]["message_id"],
                        chat_id=chat_data["chat_id"],
                        sender_id=chat_data["messages"][0]["sender_id"],
                        content=chat_data["messages"][0]["content"],
                        timestamp=chat_data["messages"][0]["timestamp"],
                        status=chat_data["messages"][0].get("status", {})
                    )
                else:
                    # Eğer mesajlar yoksa, son mesajı ayrıca al
                    last_message = self.messages.find_one(
                        {"chat_id": chat_data["chat_id"]},
                        sort=[("timestamp", -1)]
                    )
                    
                    if last_message:
                        chat.last_message = Message(
                            message_id=last_message["message_id"],
                            chat_id=last_message["chat_id"],
                            sender_id=last_message["sender_id"],
                            content=last_message["content"],
                            timestamp=last_message["timestamp"],
                            status=last_message.get("status", {})
                        )
                
                # Son 5 sohbet için mesajları ekle
                if chat_data in recent_chats and "messages" in chat_data:
                    chat.messages = [Message(**msg) for msg in chat_data["messages"]]
                
                chats.append(chat)
            
            print(f"\nToplam dönen chat sayısı: {len(chats)}")
            print("=== get_user_chats_with_recent_messages bitti ===\n")
            
            return chats
        except Exception as e:
            print(f"\n!!! HATA !!!")
            print(f"Hata mesajı: {str(e)}")
            print(f"Hata tipi: {type(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            print("!!! HATA !!!\n")
            raise DatabaseError(f"Chat listesi getirme hatası: {str(e)}") 