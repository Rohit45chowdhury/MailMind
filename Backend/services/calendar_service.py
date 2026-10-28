import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_FILE = "token.json"
DEFAULT_DURATION_MIN = 60


class CalendarError(Exception):
    """Calendar event banane me koi problem aayi."""


def _get_service():
    if not os.path.exists(TOKEN_FILE):
        raise CalendarError("token.json nahi mila. Pehle `python calendar_login.py` chalao.")

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise CalendarError(f"Google token refresh fail hua: {e}")
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            raise CalendarError("Google login expire ho gaya. `python calendar_login.py` dobara chalao.")

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_event_times(event: dict, tz_name: str) -> tuple[datetime, datetime]:
    """Validate date/time fields and return timezone-aware (start, end)."""
    date = (event.get("date") or "").strip()
    start_time = (event.get("start_time") or "").strip()
    end_time = (event.get("end_time") or "").strip()

    if not date or not start_time:
        raise CalendarError("Date aur start time dono zaroori hain")

    tz = ZoneInfo(tz_name)
    try:
        start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        if end_time:
            end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        else:
            end = start + timedelta(minutes=DEFAULT_DURATION_MIN)
    except ValueError:
        raise CalendarError("Date YYYY-MM-DD aur time HH:MM format me do")

    if end <= start:
        raise CalendarError("End time start time ke baad hona chahiye")
    return start, end


def create_event(event: dict, tz_name: str, send_invites: bool = False) -> dict:
    start, end = parse_event_times(event, tz_name)

    body = {
        "summary": (event.get("title") or "Meeting").strip(),
        "description": (event.get("description") or "").strip(),
        "start": {"dateTime": start.isoformat(), "timeZone": tz_name},
        "end": {"dateTime": end.isoformat(), "timeZone": tz_name},
    }
    if event.get("location"):
        body["location"] = event["location"].strip()

    attendees = [a.strip() for a in (event.get("attendees") or []) if a and "@" in a]
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]

    try:
        created = (
            _get_service()
            .events()
            .insert(
                calendarId="primary",
                body=body,
                # "all" emails real invites to attendees, so it is opt-in
                sendUpdates="all" if (send_invites and attendees) else "none",
            )
            .execute()
        )
    except HttpError as e:
        raise CalendarError(f"Google Calendar error: {e}")

    return {
        "status": "created",
        "event_id": created.get("id"),
        "link": created.get("htmlLink"),
        "start": start.isoformat(),
        "end": end.isoformat(),
    }