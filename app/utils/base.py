import secrets


def generate_secret_key() -> str:
    """Generate a random secret key."""
    return secrets.token_urlsafe(32)
