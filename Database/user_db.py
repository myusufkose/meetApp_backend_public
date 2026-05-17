from bson.json_util import dumps
import pymongo
from exceptions import DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError
from typing import Optional, List, Dict, Any
from bson import ObjectId
import datetime
from Database.Db import Database
from models.UserModels.GeneralUserModels import Detailed_User_Model
from models.UserModels.GeneralUserModels import Friend_Request_Model
from models.UserModels.GeneralUserModels import User_Profile_Model
from models.UserModels.GeneralUserModels import friend_Model
from utils import _convert_to_json
class UserDB:
    def __init__(self):
        self.users = Database().db["users"]
        # Sık kullanılan alanlar için indeksler
        try:
            self.users.create_index([("email", pymongo.ASCENDING)], name="idx_email", background=True)
            self.users.create_index([("user_id", pymongo.ASCENDING)], name="idx_user_id", background=True)
        except Exception:
            # Index oluşturma hatası kritik değil; sessiz geç
            pass

    

    def get_all_users(self) -> List[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            users = list(self.users.find({"is_deleted": {"$ne": True}}, {"_id": 0}))
            return _convert_to_json(users)
        except Exception as e:
            raise DatabaseError(f"Kullanıcılar getirilirken hata oluştu: {str(e)}")

    def search_users(self, search_query: str) -> List[Dict[str, Any]]:
        try:
            # MongoDB'de regex ile arama yap
            # Case-insensitive arama için $regex kullan
            # Hassas bilgileri hariç tut
            users = list(self.users.find({
                "is_deleted": {"$ne": True},
                "name": {"$regex": search_query, "$options": "i"}
            }, {
                "_id": 0,
                "password_hash": 0,
                "created_at": 0,
                "updated_at": 0,
                "is_deleted": 0,
                "friend_requests_received": 0,
                "friend_requests_sent": 0
            }))
            return _convert_to_json(users)
        except Exception as e:
            raise DatabaseError(f"Kullanıcı araması sırasında hata oluştu: {str(e)}")

    def get_user_friends(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            # Arkadaşların bilgilerini tek sorguda getir
            # Boş liste kontrolü ekle
            friends_list = user["friends"]
            if not friends_list:
                return []
                
            friends = list(self.users.find({
                "user_id": {"$in": friends_list},
                "is_deleted": {"$ne": True}
            }, {
                "_id": 0,
                "user_id": 1,
                "name": 1,
                "email": 1,
                "profile_picture": 1
            }))
            
            return _convert_to_json(friends)
        except Exception as e:
            raise DatabaseError(f"Arkadaş listesi getirilirken hata oluştu: {str(e)}")

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            user = self.users.find_one({"email": email, "is_deleted": {"$ne": True}}, {"_id": 0, "password_hash": 0})
            return _convert_to_json(user) if user else None
        except Exception as e:
            raise DatabaseError(f"Kullanıcı getirilirken hata oluştu: {str(e)}")

    def is_user_active(self, email: str) -> bool:
        """
        Kullanıcının var olup olmadığını ve silinmiş olup olmadığını minimal projeksiyonla kontrol eder.
        True dönerse kullanıcı aktiftir (var ve is_deleted != True).
        """
        try:
            doc = self.users.find_one(
                {"email": email},
                {"_id": 0, "is_deleted": 1}
            )
            if not doc:
                return False
            return not bool(doc.get("is_deleted", False))
        except Exception as e:
            raise DatabaseError(f"Kullanıcı durumu kontrol edilirken hata oluştu: {str(e)}")

    def get_all_active_user_ids(self) -> List[str]:
        """
        Silinmemiş (is_deleted != True) tüm kullanıcıların user_id listesini döner.
        """
        try:
            cursor = self.users.find({"is_deleted": {"$ne": True}}, {"_id": 0, "user_id": 1})
            return [doc["user_id"] for doc in cursor if doc.get("user_id")]
        except Exception as e:
            raise DatabaseError(f"Kullanıcı ID listesi getirilirken hata oluştu: {str(e)}")

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            # Sadece silinmemiş kullanıcıları getir
            user = self.users.find_one({"user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0})
            return _convert_to_json(user) if user else None
        except Exception as e:
            raise DatabaseError(f"Kullanıcı getirilirken hata oluştu: {str(e)}")

    def insert_user(self, user_data: Dict[str, Any]) -> None:
        try:
            self.users.insert_one(user_data)
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
                        "updated_at": datetime.datetime.now().isoformat()
                    }
                }
            )
            if result.modified_count == 0:
                raise NotFoundError("Silinecek kullanıcı bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Kullanıcı silinirken hata oluştu: {str(e)}")

    def add_friend_request(self, friend_request_data: Friend_Request_Model) -> bool:
        try:
            # Arkadaş isteği verisini oluştur
            friend_request_dict = {
                "from_user_id": friend_request_data.from_user_id,
                "to_user_id": friend_request_data.to_user_id,
                "status": "pending",
                "created_at": datetime.datetime.now().isoformat()
            }
            
            # Alıcı kullanıcının received_requests listesine ekle
            result1 = self.users.update_one(
                {"user_id": friend_request_data.to_user_id},
                {"$addToSet": {"friend_requests_received": friend_request_dict}}
            )
            
            # Gönderen kullanıcının sent_requests listesine ekle
            result2 = self.users.update_one(
                {"user_id": friend_request_data.from_user_id},
                {"$addToSet": {"friend_requests_sent": friend_request_dict}}
            )
            
            if result1.modified_count == 0 or result2.modified_count == 0:
                raise NotFoundError("Kullanıcı bulunamadı")
            return True
        except Exception as e:
            raise DatabaseError(f"Arkadaş isteği eklenirken hata oluştu: {str(e)}") 

    def get_detailed_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            user = self.users.find_one({"email": email, "is_deleted": {"$ne": True}}, {"_id": 0, "password_hash": 0})
            user["friends"] = self.get_user_friends(user)
            return _convert_to_json(user) if user else None
        except Exception as e:
            raise DatabaseError(f"Kullanıcı getirilirken hata oluştu: {str(e)}")

    def get_user_profile(self, user_id: str) -> Optional[User_Profile_Model]:
        try:
            user = self.users.find_one({"user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0, "password_hash": 0})
            if not user:
                return None
            
            # Arkadaş bilgilerini getir
            friends_data = self.get_user_friends(user)
            
            # Arkadaş verilerini friend_Model objelerine dönüştür
            friends_models = []
            for friend in friends_data:
                friends_models.append(friend_Model(
                    user_id=friend["user_id"],
                    name=friend["name"],
                    email=friend["email"],
                    profile_picture=friend.get("profile_picture", "")
                ))
            
            # User_Profile_Model oluştur
            profile = User_Profile_Model(
                user_id=user["user_id"],
                name=user["name"],
                profile_picture=user.get("profile_picture", ""),
                friends=friends_models
            )
            
            return profile
        except Exception as e:
            raise DatabaseError(f"Kullanıcı profili getirilirken hata oluştu: {str(e)}")