import os
from cryptography.fernet import Fernet, InvalidToken

_key = os.environ.get("GMAIL_TOKEN_KEY")
if not _key:
    raise RuntimeError("GMAIL_TOKEN_KEY .env me set nahi hai")

_f = Fernet(_key.encode())


def enc(value):
    return _f.encrypt(value.encode()).decode() if value else value


def dec(value):
    if not value:
        return None
    try:
        return _f.decrypt(value.encode()).decode()
    except InvalidToken:
        return None