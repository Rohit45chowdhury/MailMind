import base64
import os
import re
from email.message import EmailMessage
from email.utils import formataddr
from typing import List, Optional, Union

from dotenv import load_dotenv
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from token_crypto import enc, dec
from user_auth import users

load_dotenv()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class EmailSendError(Exception):
    """Email bhejne me koi problem aayi."""


def _to_list(value: Union[str, List[str], None]) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [v.strip() for v in value if v and v.strip()]


def _validate_addresses(addresses: List[str], field: str) -> None:
    for addr in addresses:
        if not EMAIL_REGEX.match(addr):
            raise EmailSendError(f"Invalid email address in '{field}': {addr}")


def _gmail_service(user: dict):
    g = user.get("google") or {}
    refresh = dec(g.get("refresh_token"))
    if not refresh:
        # token hai hi nahi, ya purana plain-text token (decrypt nahi hota)
        raise EmailSendError("Pehle Settings me apna Gmail connect karo.")

    creds = Credentials(
        token=dec(g.get("access_token")),
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=[SEND_SCOPE],
        expiry=g.get("expiry"),
    )
    if not creds.valid:
        try:
            creds.refresh(GoogleRequest())
        except RefreshError:
            users.update_one({"_id": user["_id"]}, {"$unset": {"google": ""}})
            raise EmailSendError("Gmail connection expire ho gaya. Settings me dobara connect karo.")
        users.update_one(
            {"_id": user["_id"]},
            {"$set": {"google.access_token": enc(creds.token), "google.expiry": creds.expiry}},
        )
    return build("gmail", "v1", credentials=creds, cache_discovery=False), g["email"]


def send_email(
    user: dict,
    to: Union[str, List[str]],
    subject: str,
    body: str,
    cc: Union[str, List[str], None] = None,
    bcc: Union[str, List[str], None] = None,
    html: bool = False,
    sender_name: Optional[str] = None,
) -> dict:
    """Mail us user ke apne Gmail se jaati hai jo login hai."""
    to_list, cc_list, bcc_list = _to_list(to), _to_list(cc), _to_list(bcc)

    if not to_list:
        raise EmailSendError("'to' address empty hai")
    if not subject.strip():
        raise EmailSendError("subject empty hai")
    if not body.strip():
        raise EmailSendError("body empty hai")

    _validate_addresses(to_list, "to")
    _validate_addresses(cc_list, "cc")
    _validate_addresses(bcc_list, "bcc")

    service, from_email = _gmail_service(user)

    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, from_email)) if sender_name else from_email
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    if bcc_list:
        msg["Bcc"] = ", ".join(bcc_list)   # Gmail API bhejte waqt ise header se hata deta hai
    msg["Subject"] = subject

    if html:
        msg.set_content("Your email client does not support HTML.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
    except HttpError as e:
        if e.resp.status in (401, 403):
            raise EmailSendError("Gmail permission nahi mili. Settings me Gmail dobara connect karo.")
        raise EmailSendError(f"Email send nahi hua: {e}")

    return {"status": "sent", "from": from_email, "to": to_list, "cc": cc_list, "subject": subject}