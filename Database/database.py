from bson.json_util import dumps
import pymongo
from exceptions import DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from typing import Optional, List, Dict, Any
from bson import ObjectId
import os
from dotenv import load_dotenv
from Database.user_db import UserDB

# .env dosyasını yükle
load_dotenv()

class Database:
    def __init__(self):
        try:
            # MongoDB bağlantı URL'ini environment variable'dan al
            connection_string = "os.getenv("MONGODB_URL")"
            if not connection_string:
                raise DatabaseError("MONGODB_URL environment variable is not set")
            myclient = pymongo.MongoClient(connection_string)
            self.db = myclient["search_db"]
            self.user_db = UserDB(self.db)
            from Database.chat_db import ChatDatabase
            self.chat_db = ChatDatabase(self.db)
            self.activities = self.db["activities"]
        except ConnectionFailure as e:
            raise DatabaseError(f"Veritabanına bağlanılamadı: {str(e)}")
        except Exception as e:
            raise DatabaseError(f"Beklenmeyen bir hata oluştu: {str(e)}")

    # Users Collection İşlemleri
    def get_all_users(self) -> List[Dict[str, Any]]:
        return self.user_db.get_all_users()

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.user_db.get_user_by_email(email)

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.user_db.get_user_by_id(user_id)

    def insert_user(self, user_data: Dict[str, Any]) -> None:
        self.user_db.insert_user(user_data)

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        return self.user_db.update_user(user_id, update_data)

    def soft_delete_user(self, user_id: str) -> bool:
        return self.user_db.soft_delete_user(user_id)

    # Activities Collection İşlemleri
    def get_all_activities(self) -> List[Dict[str, Any]]:
        try:
            activities = list(self.activities.find({}, {"_id": 0}))
            return self.user_db._convert_to_json(activities)
        except Exception as e:
            raise DatabaseError(f"Aktiviteler getirilirken hata oluştu: {str(e)}")

    def get_activity_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        try:
            activity = self.activities.find_one({"activity_id": activity_id}, {"_id": 0})
            return self.user_db._convert_to_json(activity) if activity else None
        except Exception as e:
            raise DatabaseError(f"Aktivite getirilirken hata oluştu: {str(e)}")

    def insert_activity(self, activity_data: Dict[str, Any]) -> None:
        try:
            self.activities.insert_one(activity_data)
        except DuplicateKeyError:
            raise DuplicateError("Bu aktivite zaten mevcut")
        except Exception as e:
            raise DatabaseError(f"Aktivite eklenirken hata oluştu: {str(e)}")

    def update_activity(self, activity_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            result = self.activities.update_one(
                {"activity_id": activity_id},
                {"$set": update_data}
            )
            if result.modified_count == 0:
                raise NotFoundError("Güncellenecek aktivite bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Aktivite güncellenirken hata oluştu: {str(e)}")

    def delete_activity(self, activity_id: str) -> bool:
        try:
            result = self.activities.delete_one({"activity_id": activity_id})
            if result.deleted_count == 0:
                raise NotFoundError("Silinecek aktivite bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Aktivite silinirken hata oluştu: {str(e)}")

    def get_user_activities(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            # Kullanıcının oluşturduğu aktiviteler
            created_activities = list(self.activities.find({"creator_id": user_id}, {"_id": 0}))
            
            # Kullanıcının katıldığı aktiviteler
            participated_activities = list(self.activities.find({"participants": user_id}, {"_id": 0}))
            
            # Tüm aktiviteleri birleştir ve tekrar edenleri kaldır
            all_activities = created_activities + participated_activities
            unique_activities = {activity["activity_id"]: activity for activity in all_activities}.values()
            
            return self.user_db._convert_to_json(list(unique_activities))
        except Exception as e:
            raise DatabaseError(f"Kullanıcı aktiviteleri getirilirken hata oluştu: {str(e)}")

    # Genel İşlemler
    def close(self):
        try:
            self.db.client.close()
        except Exception as e:
            raise DatabaseError(f"Veritabanı bağlantısı kapatılırken hata oluştu: {str(e)}")



