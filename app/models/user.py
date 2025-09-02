from beanie import Indexed
from pydantic import EmailStr, Field

from app.models.time_mixin import TimeMixin


class User(TimeMixin):
    clerk_id: Indexed(str, unique=True) = Field(..., description="Id from clerk authentication")
    email: Indexed(EmailStr, unique=True) = Field(..., description="User email address")
    username: Indexed(str, unique=True) = Field(None, min_length=3, max_length=50, description="Unique username")
    first_name: str = Field(..., description="First Name")
    last_name: str = Field(..., description="Last Name")
    has_image: bool = Field(default=False, description="Has Profile Image")
    profile_image: str = Field(..., description="Profile Image")
    banned: bool = Field(default=False, description="Banned user")
    is_oauth: bool = Field(default=False, description="Is Oauth account")
    oauth_provider: str | None = Field(None, description="Oauth Provider")
    
    class Settings:
        name = "users"
