from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from starlette.status import HTTP_400_BAD_REQUEST
from svix.webhooks import Webhook

from app.consts.user_event_type import UserEventType
from app.core.exceptions import AppError
from app.schemas.response import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service
from app.utils.api_response import created, no_content, ok
from ..configs.settings import settings
import json

router = APIRouter()

@router.post("/clerk", response_model=ApiResponse[UserResponse])
async def create_user(request: Request):
    webhook_secret = settings.CLERK_WEBHOOK_SECRET

    if not webhook_secret:
        raise HTTPException(
            status_code=500, detail="CLERK_WEBHOOK_SECRET not set")

    body = await request.body()
    payload = body.decode("utf-8")
    headers = dict(request.headers)

    try:
        wh = Webhook(webhook_secret)
        wh.verify(payload, headers)

        messages = json.loads(payload)
        message_type = messages.get("type")
        user_data = messages.get("data", {})
        # print(user_data)

        if message_type == UserEventType.USER_CREATED.value:
            external_accounts = user_data.get("external_accounts") or []
            external_account = external_accounts[0] if external_accounts else None

            oauth_provider = external_account.get("provider") if external_account else None
            oauth_providers = [oauth_provider] if oauth_provider else []

            # Pick email
            email_entries = user_data.get("email_addresses") or []
            emails = [e.get("email_address") for e in email_entries if e.get("email_address")]

            primary_email = next(
                (e["email_address"] for e in email_entries if e.get("id") == user_data.get("primary_email_address_id")),
                emails[0] if emails else None,
            )

            if not primary_email:
                raise AppError("No valid email found in Clerk payload.", status_code=HTTP_400_BAD_REQUEST)

            if primary_email not in emails:
                emails.insert(0, primary_email)

            # Pick profile image
            profile_image = (
                (external_account.get("image_url") if external_account else None) or
                (external_account.get("avatar_url") if external_account else None) or
                user_data.get("image_url") or
                user_data.get("profile_image_url")
            )

            create_payload = UserCreate(
                clerk_id=user_data["id"],
                primary_email=primary_email,
                emails=emails,
                username=user_data.get("username") or (external_account.get("username") if external_account else None),
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                has_image=user_data.get("has_image", False),
                profile_image=profile_image,
                banned=user_data.get("banned", False),
                created_at=datetime.fromtimestamp(user_data["created_at"] / 1000),
                updated_at=(
                    datetime.fromtimestamp(user_data["updated_at"] / 1000)
                    if user_data.get("updated_at")
                    else None
                ),
                is_oauth=bool(oauth_providers),
                oauth_providers=oauth_providers,
            )

            created_user = await user_service.create_user(create_payload)
            return created(created_user, message=f"User {user_data['id']} is created")
        elif message_type == UserEventType.USER_UPDATED.value:
            external_accounts = user_data.get("external_accounts") or []
            oauth_providers = []

            # Pick oauth
            for account in external_accounts:
                provider = account.get("provider")
                if provider and provider.startswith("oauth_"):
                    if provider not in oauth_providers:
                        oauth_providers.append(provider)

            # Pick email
            email_entries = user_data.get("email_addresses") or []
            emails = [e.get("email_address") for e in email_entries if e.get("email_address")]

            primary_email = None
            primary_email_id = user_data.get("primary_email_address_id")
            if primary_email_id:
                primary_email = next(
                    (e["email_address"] for e in email_entries
                    if e.get("id") == primary_email_id and e.get("email_address")), None
                )

            if not primary_email and emails:
                primary_email = emails[0]

            if primary_email and primary_email not in emails:
                emails.insert(0, primary_email)

            # Pick profile image
            profile_image = None
            external_account = external_accounts[0] if external_accounts else None

            if user_data.get("has_image", False):
                profile_image = (
                    (external_account.get("image_url") if external_account else None) or
                    (external_account.get("avatar_url") if external_account else None) or
                    user_data.get("image_url") or
                    user_data.get("profile_image_url")
                )

            updated_at = None
            if user_data.get("updated_at"):
                updated_at = datetime.fromtimestamp(user_data["updated_at"] / 1000)

            update_payload = UserUpdate(
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                username=user_data.get("username") or (external_account.get("username") if external_account else None),
                profile_image=profile_image,
                emails=emails if emails else None,
                primary_email=primary_email,
                oauth_providers=oauth_providers if oauth_providers else None,
                has_image=user_data.get("has_image", False),
                banned=user_data.get("banned", False),
                updated_at=updated_at
            )

            updated_user = await user_service.update_user(user_data["id"], update_payload)

            return ok(updated_user, message=f"User {user_data.get("id")} is updated")
        elif message_type == UserEventType.USER_DELETED.value:
            await user_service.delete_user(user_data.get("id"))
            return ok(None, message=f"User {user_data['id']}  is deleted")
        else:
            return no_content()
    except Exception as e:
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)
