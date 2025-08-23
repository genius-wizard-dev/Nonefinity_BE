import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

IGNORE_PATHS = {"/health"}

def init_sentry(
    dsn: str,
    environment: str = "development",
    release: str | None = None,
    traces_sample_rate: float = 0.2,
    send_default_pii: bool = False,
):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=send_default_pii,
        integrations=[
            FastApiIntegration(),
            RedisIntegration(),
            PyMongoIntegration(),
            LoggingIntegration(level=None, event_level="ERROR"),
        ],
        traces_sample_rate=traces_sample_rate,
        max_breadcrumbs=200,
        before_send=_strip_sensitive,
        before_send_transaction=_drop_health_transactions
    )

def _strip_sensitive(event, hint):
    headers = event.get("request", {}).get("headers", {}) or {}
    for k in list(headers.keys()):
        if k.lower() in ("authorization", "cookie", "set-cookie"):
            headers[k] = "[Filtered]"
    return event

def _drop_health_transactions(event):
    name = event.get("transaction")
    if name and any(p in str(name) for p in IGNORE_PATHS):
        return None
    return event
