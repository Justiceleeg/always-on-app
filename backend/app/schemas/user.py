from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    email: EmailStr


class UserResponse(BaseModel):
    id: UUID
    firebase_uid: str
    email: str
    name: str
    is_enrolled: bool
    device_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseModel):
    user_id: UUID
    email: str
    name: str
    is_enrolled: bool
    created: bool
