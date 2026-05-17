from pydantic import BaseModel
from typing import Optional

class User_Login_Model(BaseModel):
    email: str
    password: str
     
class User_Create_Model(BaseModel):
    name: str
    email: str
    password: str
    profile_picture: Optional[str] = ""
    
