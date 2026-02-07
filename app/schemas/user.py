from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    acronym: str

class UserLogin(BaseModel):
    identifier: str    
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: str
    acronym: str | None = None
    created_at: datetime | None = None
    avatar: str | None = "default.png"

class UserUpdate(BaseModel):
    username: str | None = None
    acronym: str | None = None
    email: str | None = None
    current_password: str | None = None # Requerido si cambias password
    new_password: str | None = None

class AvatarSchema(BaseModel):
    id: int
    filename: str
    url: str # Calcularemos la URL completa para facilitar al front

    class Config:
        from_attributes = True