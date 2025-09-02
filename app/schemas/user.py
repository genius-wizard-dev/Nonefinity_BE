from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    clerk_id: str
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    has_image: bool
    profile_image: str
    banned: bool
    created_at: datetime
    updated_at: Optional[datetime]
    is_oauth: bool
    oauth_provider: Optional[str]

class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    username: str
    profile_image: str

class UserResponse(BaseModel):
    clerk_id: str
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    has_image: bool
    profile_image: Optional[str]
    banned: bool
    created_at: datetime
    updated_at: Optional[datetime]
    is_oauth: bool
    oauth_provider: Optional[str]