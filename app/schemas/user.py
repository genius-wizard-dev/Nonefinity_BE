from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    clerk_id: str
    emails: List[EmailStr]
    primary_email: EmailStr
    username: str
    first_name: str
    last_name: str
    has_image: bool
    profile_image: str
    banned: bool
    created_at: datetime
    updated_at: Optional[datetime]
    is_oauth: bool
    oauth_providers: Optional[List[str]]

class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    username: str = None
    profile_image: Optional[str] = None
    emails: List[EmailStr]
    primary_email: EmailStr
    oauth_providers: Optional[List[str]] = []
    has_image: bool = False
    banned: bool = False
    updated_at: datetime

class UserResponse(BaseModel):
    clerk_id: str
    emails: List[EmailStr]
    primary_email: EmailStr
    username: str
    first_name: str
    last_name: str
    has_image: bool
    profile_image: str
    banned: bool
    created_at: datetime
    updated_at: Optional[datetime]
    is_oauth: bool
    oauth_providers: Optional[List[str]]