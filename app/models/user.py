from typing import Annotated, List
from beanie import Document, Indexed
from pydantic import EmailStr, Field

from app.models.time_mixin import TimeMixin


class User(TimeMixin, Document):
    clerk_id: Annotated[str, Indexed(unique=True)] = Field(..., description="Id from clerk authentication")
    emails: List[EmailStr] = Field(default_factory=list, description="List of user email addresses")
    primary_email: Annotated[EmailStr, Indexed(unique=True)] = Field(..., description="Primary email address")
    username: Annotated[str, Indexed(unique=True)] = Field(..., min_length=3, max_length=50, description="Unique username")
    first_name: str = Field(..., description="First Name")
    last_name: str = Field(..., description="Last Name")
    has_image: bool = Field(default=False, description="Has Profile Image")
    profile_image: str = Field(..., description="Profile Image")
    banned: bool = Field(default=False, description="Banned user")
    is_oauth: bool = Field(default=False, description="Is Oauth account")
    oauth_providers: List[str] | None = Field(None, description="List of OAuth providers (e.g. google, facebook, tiktok)")
    
    class Settings:
        name = "users"