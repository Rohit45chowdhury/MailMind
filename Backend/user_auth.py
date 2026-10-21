import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "mailmind")
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGO = "HS256"
COOKIE_NAME = "mm_token"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
TOKEN_DAYS = 7
MAX_FAILS = 5
LOCK_MINUTES = 15

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
users = client[MONGODB_DB]["users"]
users.create_index([("email", ASCENDING)], unique=True)

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Schemas ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: EmailStr
    password: str = Field(pattern=r"^\d{4}$")  # exactly 4 digits


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


# ---------- Helpers ----------
def hash_password(pw: str) -> bytes:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt())


def verify_password(pw: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed)
    except ValueError:
        return False


def public_user(doc: dict) -> dict:
    return {"id": str(doc["_id"]), "name": doc["name"], "email": doc["email"]}


def set_auth_cookie(response: Response, user_id: str) -> None:
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    token = jwt.encode({"sub": user_id, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGO)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax",
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


# ---------- Routes ----------
@router.post("/register", status_code=201)
def register(data: RegisterIn, response: Response):
    doc = {
        "name": data.name.strip(),
        "email": data.email.lower(),
        "password_hash": hash_password(data.password),
        "failed_attempts": 0,
        "locked_until": None,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        doc["_id"] = users.insert_one(doc).inserted_id
    except DuplicateKeyError:
        raise HTTPException(409, "An account with this email already exists.")
    set_auth_cookie(response, str(doc["_id"]))
    return public_user(doc)


@router.post("/login")
def login(data: LoginIn, response: Response):
    now = datetime.now(timezone.utc)
    doc = users.find_one({"email": data.email.lower()})

    # Account locked?
    if doc and doc.get("locked_until"):
        locked = doc["locked_until"]
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        if locked > now:
            raise HTTPException(429, f"Too many wrong attempts. Try again in {LOCK_MINUTES} minutes.")

    # Same message for wrong email or PIN, so emails can't be guessed
    if not doc or not verify_password(data.password, doc["password_hash"]):
        if doc:
            fails = doc.get("failed_attempts", 0) + 1
            update = {"failed_attempts": fails}
            if fails >= MAX_FAILS:
                update = {"failed_attempts": 0, "locked_until": now + timedelta(minutes=LOCK_MINUTES)}
            users.update_one({"_id": doc["_id"]}, {"$set": update})
        raise HTTPException(401, "Invalid email or PIN.")

    users.update_one({"_id": doc["_id"]}, {"$set": {"failed_attempts": 0, "locked_until": None}})
    set_auth_cookie(response, str(doc["_id"]))
    return public_user(doc)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return public_user(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}