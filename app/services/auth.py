"""
Admin Authentication & Session Security Service
Enforces server-side authentication for protected operations and APIs.
"""
import os
import hmac
from dotenv import load_dotenv
from fastapi import Request, HTTPException

load_dotenv()

def get_admin_credentials():
    """
    Retrieve admin credentials strictly from environment variables.
    Fails startup/verification if environment configuration is missing.
    """
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    if not admin_user or not admin_pass:
        raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD must be configured in the environment.")
    return admin_user, admin_pass

def get_secret_key():
    """
    Retrieve session secret key strictly from environment.
    """
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError("SECRET_KEY must be configured in the environment.")
    return secret

def authenticate_admin(username: str, password: str) -> bool:
    """
    Secure constant-time comparison against configured administrator credentials.
    """
    try:
        admin_user, admin_pass = get_admin_credentials()
        user_match = hmac.compare_digest(username.strip().encode("utf-8"), admin_user.strip().encode("utf-8"))
        pass_match = hmac.compare_digest(password.encode("utf-8"), admin_pass.encode("utf-8"))
        return user_match and pass_match
    except Exception:
        return False

def is_admin_authenticated(request: Request) -> bool:
    """
    Check whether the current session has an active, validated admin authentication.
    """
    return bool(request.session.get("admin_authenticated") is True)

async def require_admin_api(request: Request):
    """
    FastAPI dependency for protecting JSON API endpoints.
    Rejects unauthenticated requests with HTTP 401 Unauthorized.
    """
    if not is_admin_authenticated(request):
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "message": "Authentication required. Please log in as administrator."
            }
        )
    return True
