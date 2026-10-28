import hashlib
import hmac
import json
import logging
import os
import secrets
import smtplib
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.errors import DuplicateKeyError

log = logging.getLogger("mailmind.auth")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "mailmind")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
COOKIE_NAME = "mm_token"
TOKEN_DAYS = 7

# ---- Cookie settings (deployment) ----
# Local:                COOKIE_SECURE=false, COOKIE_SAMESITE=lax
# Production, alag domain par frontend (Vercel + Render): COOKIE_SECURE=true, COOKIE_SAMESITE=none
# Production, same site (app.xyz.com + api.xyz.com):      COOKIE_SECURE=true, COOKIE_SAMESITE=lax
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
if COOKIE_SAMESITE not in ("lax", "strict", "none"):
    COOKIE_SAMESITE = "lax"
# SameSite=None ke saath browser Secure cookie hi accept karta hai
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true" or COOKIE_SAMESITE == "none"

# OTP settings
OTP_MINUTES = 10          # OTP validity
OTP_MAX_TRIES = 5         # wrong guesses allowed per OTP
OTP_RESEND_SECONDS = 60   # cooldown between sends
OTP_MAX_SENDS = 5         # max sends per email in one window

# ---- OTP email ----
# Render free par SMTP ports (25/465/587) block hain, isliye production me HTTPS email API use karo:
#   BREVO_API_KEY  (+ OTP_FROM_EMAIL = Brevo me verified sender)   <- domain ke bina bhi chalta hai
#   RESEND_API_KEY (+ OTP_FROM_EMAIL = verified domain ka address)
# Dono set na ho to local ke liye purana SMTP use hota hai.
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("EMAIL_ADDRESS", "")
SMTP_PASS = (os.getenv("SMTP_PASS") or os.getenv("EMAIL_APP_PASSWORD", "")).replace(" ", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MailMind")
OTP_FROM_EMAIL = os.getenv("OTP_FROM_EMAIL") or SMTP_USER

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[MONGODB_DB]
users = db["users"]
login_otps = db["login_otps"]
users.create_index([("email", ASCENDING)], unique=True)
login_otps.create_index([("email", ASCENDING)], unique=True)
# Mongo auto-deletes expired OTP docs (runs about every 60s)
login_otps.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas ----------
class SendOtpIn(BaseModel):
    email: EmailStr


class VerifyIn(BaseModel):
    email: EmailStr
    otp: str = Field(pattern=r"^\d{6}$")


# ---------- Helpers ----------
def public_user(doc: dict) -> dict:
    g = doc.get("google") or {}
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "google_connected": bool(g.get("refresh_token")),
    }


def set_auth_cookie(response: Response, user_id: str) -> None:
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    token = jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE, max_age=TOKEN_DAYS * 86400, path="/",
    )


def get_current_user(request: Request) -> dict:
    """Use as a dependency to protect any route."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not signed in.")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        doc = users.find_one({"_id": ObjectId(payload["sub"])})
    except Exception:
        raise HTTPException(401, "Session expired. Sign in again.")
    if not doc:
        raise HTTPException(401, "Account not found.")
    return doc


def _aware(dt: datetime) -> datetime:
    # Mongo returns naive datetimes; treat them as UTC
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(email: str, otp: str) -> str:
    # HMAC with server secret, bound to the email
    return hmac.new(JWT_SECRET.encode(), f"{email}:{otp}".encode(), hashlib.sha256).hexdigest()


# ---------- OTP email senders ----------
def _post_json(url: str, payload: dict, headers: dict) -> None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MailMind/1.0",
            **headers,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"Email API error {e.code}: {detail}")


def _otp_text(otp: str) -> tuple[str, str]:
    subject = f"Your {SMTP_FROM_NAME} sign-in code: {otp}"
    body = (
        f"Your sign-in code is {otp}\n\n"
        f"It is valid for {OTP_MINUTES} minutes. "
        f"If you did not request this, you can ignore this email."
    )
    return subject, body


def _send_via_brevo(to_email: str, otp: str) -> None:
    subject, body = _otp_text(otp)
    _post_json(
        "https://api.brevo.com/v3/smtp/email",
        {
            "sender": {"name": SMTP_FROM_NAME, "email": OTP_FROM_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "textContent": body,
        },
        {"api-key": BREVO_API_KEY},
    )


def _send_via_resend(to_email: str, otp: str) -> None:
    subject, body = _otp_text(otp)
    _post_json(
        "https://api.resend.com/emails",
        {
            "from": f"{SMTP_FROM_NAME} <{OTP_FROM_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        },
        {"Authorization": f"Bearer {RESEND_API_KEY}"},
    )


def _send_via_smtp(to_email: str, otp: str) -> None:
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER / SMTP_PASS not set")
    subject, body = _otp_text(otp)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)


def _send_otp_email(to_email: str, otp: str) -> None:
    if BREVO_API_KEY:
        if not OTP_FROM_EMAIL:
            raise RuntimeError("OTP_FROM_EMAIL not set (Brevo me verified sender)")
        _send_via_brevo(to_email, otp)
    elif RESEND_API_KEY:
        if not OTP_FROM_EMAIL:
            raise RuntimeError("OTP_FROM_EMAIL not set (Resend me verified domain ka address)")
        _send_via_resend(to_email, otp)
    else:
        _send_via_smtp(to_email, otp)  # sirf local dev


# ---------- Routes ----------
@router.post("/send-otp")
def send_otp(data: SendOtpIn):
    """Step 1: mail a 6-digit OTP. Same flow for new and existing users."""
    email = data.email.lower()
    now = datetime.now(timezone.utc)

    prev = login_otps.find_one({"email": email})
    if prev:
        if _aware(prev["resend_after"]) > now:
            raise HTTPException(429, f"Please wait {OTP_RESEND_SECONDS} seconds before requesting a new OTP.")
        if prev.get("sends", 0) >= OTP_MAX_SENDS:
            raise HTTPException(429, "Too many OTP requests. Try again in a few minutes.")

    otp = _new_otp()
    login_otps.update_one(
        {"email": email},
        {
            "$set": {
                "otp_hash": _hash_otp(email, otp),
                "attempts": 0,
                "resend_after": now + timedelta(seconds=OTP_RESEND_SECONDS),
                "expires_at": now + timedelta(minutes=OTP_MINUTES),
            },
            "$inc": {"sends": 1},
        },
        upsert=True,
    )
    try:
        _send_otp_email(email, otp)
    except Exception:
        # Render logs me asli wajah dikhe (OTP ya email address log nahi hota)
        log.exception("OTP email send failed")
        login_otps.delete_one({"email": email})
        raise HTTPException(502, "OTP email nahi bheji ja saki. Thodi der baad try karo.")

    return {
        "status": "otp_sent",
        "email": email,
        "expires_in": OTP_MINUTES * 60,
        "resend_in": OTP_RESEND_SECONDS,
    }


@router.post("/verify-otp")
def verify_otp(data: VerifyIn, response: Response):
    """Step 2: check OTP, then sign in (creating the account if new)."""
    email = data.email.lower()
    now = datetime.now(timezone.utc)

    # Count the attempt first (atomic) so parallel guesses cannot bypass the limit
    rec = login_otps.find_one_and_update(
        {"email": email}, {"$inc": {"attempts": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not rec:
        raise HTTPException(400, "OTP expire ho gaya ya request nahi mili. Naya OTP lo.")
    if _aware(rec["expires_at"]) <= now:
        login_otps.delete_one({"email": email})
        raise HTTPException(400, "OTP expire ho gaya. Naya OTP lo.")
    if rec["attempts"] > OTP_MAX_TRIES:
        login_otps.delete_one({"email": email})
        raise HTTPException(429, "Too many wrong OTPs. Naya OTP lo.")

    if not hmac.compare_digest(rec["otp_hash"], _hash_otp(email, data.otp)):
        left = OTP_MAX_TRIES - rec["attempts"]
        if left <= 0:
            login_otps.delete_one({"email": email})
            raise HTTPException(429, "Too many wrong OTPs. Naya OTP lo.")
        raise HTTPException(400, f"Wrong OTP. {left} attempts left.")

    # OTP is correct: single use
    login_otps.delete_one({"email": email})

    user = users.find_one({"email": email})
    is_new = user is None
    if is_new:
        doc = {
            "name": email.split("@")[0][:60],
            "email": email,
            "password_hash": None,          # passwordless account
            "email_verified": True,
            "created_at": now,
        }
        try:
            doc["_id"] = users.insert_one(doc).inserted_id
            user = doc
        except DuplicateKeyError:
            # Created in parallel (for example via Google login)
            user = users.find_one({"email": email})
    elif not user.get("email_verified"):
        users.update_one({"_id": user["_id"]}, {"$set": {"email_verified": True}})

    set_auth_cookie(response, str(user["_id"]))
    return {**public_user(user), "is_new": is_new}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@router.post("/logout")
def logout(response: Response):
    # delete_cookie me wahi samesite/secure dena zaruri hai jo set karte waqt tha
    response.delete_cookie(
        COOKIE_NAME, path="/", samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE, httponly=True,
    )
    return {"ok": True}