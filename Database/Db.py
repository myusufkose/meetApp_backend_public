from bson.json_util import dumps
import pymongo
from exceptions import DatabaseError, NotFoundError, DuplicateError
from pymongo.errors import DuplicateKeyError
from typing import Optional, List, Dict, Any
from bson import ObjectId
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class Database:
    def __init__(self):
        try:
            connection_string = os.getenv("MONGODB_URL")
            if not connection_string:
                raise DatabaseError("MONGODB_URL environment variable is not set")
            myclient = pymongo.MongoClient(connection_string)
            self.db = myclient["test_db"]
        except Exception as e:
            raise DatabaseError(f"Veritabanı bağlantısı kurulurken hata oluştu: {str(e)}")

    def add_user(self, user_data: Dict[str, Any]) -> None:
        """Kullanıcı ekler"""
        try:
            self.db.users.insert_one(user_data)
        except DuplicateKeyError:
            raise DuplicateError("Bu e-posta adresi zaten kayıtlı")
        except Exception as e:
            raise DatabaseError(f"Kullanıcı eklenirken hata oluştu: {str(e)}")

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Tüm kullanıcıları getirir"""
        try:
            users = list(self.db.users.find({"is_deleted": {"$ne": True}}, {"_id": 0}))
            return users
        except Exception as e:
            raise DatabaseError(f"Kullanıcılar getirilirken hata oluştu: {str(e)}")
            
    # Genel İşlemler
    def close(self):
        try:
            self.db.client.close()
        except Exception as e:
            raise DatabaseError(f"Veritabanı bağlantısı kapatılırken hata oluştu: {str(e)}")



