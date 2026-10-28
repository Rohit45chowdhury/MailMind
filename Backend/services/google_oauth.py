import os
from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token as google_id_token
from google_auth_oauthlib.flow import Flow

from core.token_crypto import enc
from routers.user_auth import users, get_current_user, set_auth_cookie, JWT_SECRET, JWT_ALGO

# Google may return fewer scopes than requested (user unticks a box).
# Without this, oauthlib raises a scope-mismatch error.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Login needs only basic profile scopes (no Google verification needed)
LOGIN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
# Gmail permission is asked separately, from Settings
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"

router = APIRouter(prefix="/google", tags=["google"])


def _scopes_for(mode: str) -> list[str]:
    return LOGIN_SCOPES if mode == "login" else LOGIN_SCOPES + [GMAIL_SCOPE]


def _flow(scopes: list[str]) -> Flow:
    config = {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        config, scopes=scopes, redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,
    )


def _state(mode: str, user_id: str | None = None) -> str:
    payload = {"mode": mode, "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}
    if user_id:
        payload["sub"] = user_id
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def _auth_url(state: str, mode: str, login_hint: str | None = None) -> str:
    if mode == "login":
        # Login only: no Gmail access, no refresh token needed
        kwargs = dict(prompt="select_account", state=state)
    else:
        kwargs = dict(
            access_type="offline", prompt="consent",
            include_granted_scopes="true", state=state,
        )
        if login_hint:
            kwargs["login_hint"] = login_hint
    url, _ = _flow(_scopes_for(mode)).authorization_url(**kwargs)
    return url


def _back(mode: str, result: str) -> RedirectResponse:
    page = "/login" if mode == "login" else "/settings"
    return RedirectResponse(f"{FRONTEND_URL}{page}?gmail={result}")


def _save_tokens(user: dict, creds, google_email: str) -> None:
    old = user.get("google") or {}
    refresh_enc = enc(creds.refresh_token) if creds.refresh_token else old.get("refresh_token")
    users.update_one({"_id": user["_id"]}, {"$set": {"google": {
        "email": google_email,
        "access_token": enc(creds.token),
        "refresh_token": refresh_enc,
        "expiry": creds.expiry,
    }}})


# ---------- Login with Google ----------
@router.get("/login")
def google_login():
    """Login page ka 'Continue with Google' button seedha isko kholta hai."""
    return RedirectResponse(_auth_url(_state("login"), "login"))


# ---------- Connect Gmail (already logged-in users) ----------
@router.get("/connect")
def connect(user: dict = Depends(get_current_user)):
    return {"url": _auth_url(_state("connect", str(user["_id"])), "connect",
                             login_hint=user["email"])}


# ---------- Callback for both ----------
@router.get("/callback")
def callback(code: str = "", state: str = "", error: str = ""):
    try:
        st = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGO])
    except Exception:
        return _back("connect", "invalid")
    mode = st.get("mode", "connect")

    if error or not code:
        return _back(mode, "denied")

    flow = _flow(_scopes_for(mode))
    try:
        flow.fetch_token(code=code)
        creds = flow.credentials
        info = google_id_token.verify_oauth2_token(
            creds.id_token, GoogleRequest(), CLIENT_ID, clock_skew_in_seconds=10,
        )
    except Exception:
        return _back(mode, "failed")

    google_email = (info.get("email") or "").lower()
    if not google_email or not info.get("email_verified"):
        return _back(mode, "failed")

    # ----- Login with Google -----
    if mode == "login":
        user = users.find_one({"email": google_email})
        if not user:
            doc = {
                "name": (info.get("name") or google_email.split("@")[0])[:60],
                "email": google_email,
                "password_hash": None,          # no password, Google-only account
                "email_verified": True,
                "failed_attempts": 0,
                "locked_until": None,
                "created_at": datetime.now(timezone.utc),
            }
            doc["_id"] = users.insert_one(doc).inserted_id
            user = doc
        elif not user.get("email_verified"):
            users.update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}})

        # No token saving here: Gmail is connected separately from Settings
        resp = RedirectResponse(f"{FRONTEND_URL}/")
        set_auth_cookie(resp, str(user["_id"]))
        return resp

    # ----- Connect (already logged in) -----
    user = users.find_one({"_id": ObjectId(st["sub"])}) if st.get("sub") else None
    if not user:
        return _back(mode, "invalid")
    if google_email != user["email"].lower():
        return _back(mode, "mismatch")

    granted = set(getattr(creds, "granted_scopes", None) or creds.scopes or [])
    if GMAIL_SCOPE not in granted:
        return _back(mode, "denied")  # user unticked Gmail permission
    if not creds.refresh_token and not (user.get("google") or {}).get("refresh_token"):
        return _back(mode, "failed")

    _save_tokens(user, creds, google_email)
    return _back(mode, "connected")


@router.get("/status")
def status(user: dict = Depends(get_current_user)):
    g = user.get("google")
    return {"connected": bool(g and g.get("refresh_token")), "email": (g or {}).get("email")}


@router.post("/disconnect")
def disconnect(user: dict = Depends(get_current_user)):
    users.update_one({"_id": user["_id"]}, {"$unset": {"google": ""}})
    return {"ok": True}