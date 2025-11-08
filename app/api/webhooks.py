from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from svix.webhooks import Webhook
from app.utils import get_logger
from app.consts.user_event_type import UserEventType
from app.core.exceptions import AppError
from app.schemas.response import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service
from app.utils.api_response import created, no_content, ok
from ..configs.settings import settings
import json
import base64
import binascii
import hashlib
import hmac
logger = get_logger(__name__)
router = APIRouter(tags=["Webhooks"])

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


def _process_webhook_secret(webhook_secret: str) -> str:
    """Process webhook secret key to Svix format (whsec_ prefix).

    Composio provides plain text secret key, need to encode to base64 and add whsec_ prefix.
    This function handles multiple secret key formats:
    - Already has whsec_ prefix: use as-is
    - Plain text: encode to base64 and add whsec_ prefix (most common for Composio)
    - Hex string: convert to base64 and add whsec_ prefix
    - Base64 string: add whsec_ prefix

    Args:
        webhook_secret: Raw webhook secret key from settings

    Returns:
        Processed secret key in whsec_ format for Svix Webhook class
    """
    if webhook_secret.startswith("whsec_"):
        logger.debug("Using secret with whsec_ prefix")
        return webhook_secret

    try:
        # Try plain text -> base64 -> whsec_ (this is the working format for Composio)
        secret_base64 = base64.b64encode(webhook_secret.encode('utf-8')).decode('utf-8')
        processed_secret = f"whsec_{secret_base64}"
        logger.debug("Converted plain text secret to whsec_ format")
        return processed_secret
    except Exception as e:
        logger.warning(f"Failed to process secret key as plain text: {e}")
        # Fallback: try other formats
        try:
            # Try hex string -> base64 -> whsec_
            secret_bytes = bytes.fromhex(webhook_secret)
            secret_base64 = base64.b64encode(secret_bytes).decode('utf-8')
            processed_secret = f"whsec_{secret_base64}"
            logger.debug("Converted hex secret to whsec_ format")
            return processed_secret
        except (ValueError, binascii.Error):
            # Try base64 string -> whsec_
            try:
                base64.b64decode(webhook_secret)
                processed_secret = f"whsec_{webhook_secret}"
                logger.debug("Added whsec_ prefix to base64 secret")
                return processed_secret
            except Exception:
                # Use as-is
                logger.debug("Using secret as-is")
                return webhook_secret


@router.post("/integrate")
async def integrate(request: Request):
    webhook_secret = settings.COMPOSIO_WEBHOOK_SECRET
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="COMPOSIO_WEBHOOK_SECRET not set")

    body = await request.body()
    payload_str = body.decode("utf-8")
    headers = dict(request.headers)

    try:


        processed_secret = _process_webhook_secret(webhook_secret)

        wh = Webhook(processed_secret)
        wh.verify(payload_str, headers)

        payload = json.loads(payload_str)
        logger.debug(f"Webhook verified successfully. Payload: {payload}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying webhook: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise AppError(str(e), status_code=HTTP_400_BAD_REQUEST)

    return ok(None, message="Webhook received successfully")


