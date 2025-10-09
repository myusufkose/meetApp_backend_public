from typing import List, Optional, Dict, Any
from exceptions import DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
import datetime
from Database.Db import Database
from utils import _convert_to_json

class ActivitiesDB:
    def __init__(self):
        self.activities = Database().db["activities"]

 # Activities Collection İşlemleri
    def get_all_activities(self) -> List[Dict[str, Any]]:
        try:
            activities = list(self.activities.find({}, {"_id": 0}))
            return _convert_to_json(activities)
        except Exception as e:
            raise DatabaseError(f"Aktiviteler getirilirken hata oluştu: {str(e)}")

    def get_activity_by_id(self, activity_id: str) -> Optional[Dict[str, Any]]:
        try:
            activity = self.activities.find_one({"activity_id": activity_id}, {"_id": 0})
            return _convert_to_json(activity) if activity else None
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
            
            return _convert_to_json(list(unique_activities))
        except Exception as e:
            raise DatabaseError(f"Kullanıcı aktiviteleri getirilirken hata oluştu: {str(e)}")