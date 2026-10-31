import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from core.token_crypto import enc, dec
from routers.user_auth import users

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_URI = "https://oauth2.googleapis.com/token"

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleAuthError(Exception):
    """User ka Google connection missing, revoked ya expire hai."""


def has_scope(user: dict, scope: str) -> bool:
    g = user.get("google") or {}
    if not g.get("refresh_token"):
        return False
    scopes = g.get("scopes")
    if scopes is None:
        # Purane users: scopes store hone se pehle sirf Gmail connect hota tha
        return scope == GMAIL_SCOPE
    return scope in scopes


def credentials_for(user: dict, scope: str) -> Credentials:
    if not has_scope(user, scope):
        raise GoogleAuthError("Pehle Settings mein Google connect karo.")

    g = user["google"]
    refresh_token = dec(g.get("refresh_token"))
    if not refresh_token:
        raise GoogleAuthError("Google connection kharab hai. Settings mein dobara connect karo.")

    # Mongo naive UTC datetime deta hai, google-auth ko bhi naive UTC chahiye.
    # Aware datetime aaye to ignore karo, neeche refresh ho jayega.
    expiry = g.get("expiry")
    if expiry is not None and expiry.tzinfo is not None:
        expiry = None

    # scopes=None zaroori hai: Gmail aur Calendar ek hi access token share karte hain.
    # Refresh me scope bhejte to token sirf ek scope ka ban kar DB me overwrite ho jata.
    creds = Credentials(
        token=dec(g.get("access_token")),
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        expiry=expiry,
    )

    if not creds.valid:
        try:
            creds.refresh(Request())
        except RefreshError as e:
            if "invalid_grant" in str(e):
                # Refresh token revoke/expire ho gaya. Gmail aur Calendar dono ka
                # token ek hi hai, isliye poora google field hatana sahi hai.
                users.update_one({"_id": user["_id"]}, {"$unset": {"google": ""}})
                raise GoogleAuthError("Google access expire ho gaya. Settings mein dobara connect karo.")
            raise GoogleAuthError(f"Google token refresh fail hua: {e}")
        except Exception as e:
            # Network error etc.: token delete mat karo, sirf error do
            raise GoogleAuthError(f"Google token refresh fail hua: {e}")

        update = {"google.access_token": enc(creds.token), "google.expiry": creds.expiry}
        if creds.refresh_token and creds.refresh_token != refresh_token:
            update["google.refresh_token"] = enc(creds.refresh_token)
        users.update_one({"_id": user["_id"]}, {"$set": update})

    return creds