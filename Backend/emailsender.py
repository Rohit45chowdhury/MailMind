

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import List, Optional, Union

from dotenv import load_dotenv

load_dotenv()

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailSendError(Exception):
    """Email bhejne me koi problem aayi."""


def _to_list(value: Union[str, List[str], None]) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        # "a@x.com, b@y.com" bhi chalega
        return [v.strip() for v in value.split(",") if v.strip()]
    return [v.strip() for v in value if v and v.strip()]


def _validate_addresses(addresses: List[str], field: str) -> None:
    for addr in addresses:
        if not EMAIL_REGEX.match(addr):
            raise EmailSendError(f"Invalid email address in '{field}': {addr}")


def send_email(
    to: Union[str, List[str]],
    subject: str,
    body: str,
    cc: Union[str, List[str], None] = None,
    bcc: Union[str, List[str], None] = None,
    html: bool = False,
    sender_name: Optional[str] = None,
) -> dict:
    """
    Email bhejta hai.

    to / cc / bcc : ek address ya list (ya comma separated string)
    html          : True ho to body ko HTML email ki tarah bhejega
    sender_name   : "From" me dikhne wala naam (optional)
    """
    smtp_user = os.getenv("EMAIL_ADDRESS")
    smtp_password = os.getenv("EMAIL_APP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_password:
        raise EmailSendError("EMAIL_ADDRESS ya EMAIL_APP_PASSWORD .env me set nahi hai")

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

    msg = EmailMessage()
    msg["From"] = formataddr((sender_name, smtp_user)) if sender_name else smtp_user
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject

    if html:
        msg.set_content("Your email client does not support HTML.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    recipients = to_list + cc_list + bcc_list  # bcc header me nahi, sirf envelope me

    try:
        context = ssl.create_default_context()
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg, from_addr=smtp_user, to_addrs=recipients)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.send_message(msg, from_addr=smtp_user, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError:
        raise EmailSendError(
            "Login fail hua. Gmail me 2-Step Verification on karke App Password use karo."
        )
    except smtplib.SMTPRecipientsRefused:
        raise EmailSendError("Recipient address server ne reject kar diya")
    except (smtplib.SMTPException, OSError) as e:
        raise EmailSendError(f"Email send nahi hua: {e}")

    return {"status": "sent", "to": to_list, "cc": cc_list, "subject": subject}


if __name__ == "__main__":
    # Pehle apne hi email par test karo
    me = os.getenv("EMAIL_ADDRESS", "")
    print(send_email(to=me, subject="Test from Email Agent", body="Hello! Ye ek test email hai."))