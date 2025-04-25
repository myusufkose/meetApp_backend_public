from bson.json_util import dumps
import pymongo
from exceptions import DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError
from typing import Optional, List, Dict, Any
from bson import ObjectId
import datetime

class UserDB:
    def __init__(self, db):
        self.users = db["users"]

    def _convert_to_json(self, data):
        """
        MongoDB'den gelen verileri JSON'a dönüştürür.
        ObjectId'leri string'e çevirir.
        """
        if isinstance(data, list):
            return [self._convert_to_json(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._convert_to_json(value) for key, value in data.items()}
        elif isinstance(data, ObjectId):
            return str(data)
        return data

    def get_all_users(self) -> List[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            users = list(self.users.find({"is_deleted": {"$ne": True}}, {"_id": 0}))
            return self._convert_to_json(users)
        except Exception as e:
            raise DatabaseError(f"Kullanıcılar getirilirken hata oluştu: {str(e)}")

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            user = self.users.find_one({"email": email, "is_deleted": {"$ne": True}}, {"_id": 0})
            return self._convert_to_json(user) if user else None
        except Exception as e:
            raise DatabaseError(f"Kullanıcı getirilirken hata oluştu: {str(e)}")

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            user = self.users.find_one({"user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0})
            return self._convert_to_json(user) if user else None
        except Exception as e:
            raise DatabaseError(f"Kullanıcı getirilirken hata oluştu: {str(e)}")

    def insert_user(self, user_data: Dict[str, Any]) -> None:
        try:
            self.users.insert_one(user_data)
        except DuplicateKeyError:
            raise DuplicateError("Bu e-posta adresi zaten kayıtlı")
        except Exception as e:
            raise DatabaseError(f"Kullanıcı eklenirken hata oluştu: {str(e)}")

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            result = self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            if result.modified_count == 0:
                raise NotFoundError("Güncellenecek kullanıcı bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Kullanıcı güncellenirken hata oluştu: {str(e)}")

    def soft_delete_user(self, user_id: str) -> bool:
        try:
            result = self.users.update_one(
                {"user_id": user_id, "is_deleted": {"$ne": True}},
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.datetime.now().isoformat()
                    }
                }
            )
            if result.modified_count == 0:
                raise NotFoundError("Silinecek kullanıcı bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Kullanıcı silinirken hata oluştu: {str(e)}") 