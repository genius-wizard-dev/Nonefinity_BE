import secrets

def generate_secret_key(length: int = 32) -> str:
    """Generate a random secret key."""
    return secrets.token_urlsafe(length)
