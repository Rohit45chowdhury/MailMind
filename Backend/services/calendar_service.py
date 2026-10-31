import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from bson import ObjectId
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from routers.user_auth import users
from services.google_creds import CALENDAR_SCOPE, GoogleAuthError, credentials_for

DEFAULT_TZ = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")
DEFAULT_DURATION_MIN = 60


class CalendarError(Exception):
    """Calendar event banane me koi problem aayi."""


def valid_tz(name: str | None) -> str:
    if name:
        try:
            ZoneInfo(name)
            return name
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return DEFAULT_TZ


def _get_service(user_id: str):
    try:
        user = users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        user = None
    if not user:
        raise CalendarError("User nahi mila")
    try:
        creds = credentials_for(user, CALENDAR_SCOPE)
    except GoogleAuthError as e:
        raise CalendarError(str(e))
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


def create_event(event: dict, tz_name: str, user_id: str, send_invites: bool = False) -> dict:
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
            _get_service(user_id)
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
        if e.resp.status in (401, 403):
            raise CalendarError("Calendar permission nahi mili. Settings mein Calendar dobara connect karo.")
        raise CalendarError(f"Google Calendar error: {e}")

    return {
        "status": "created",
        "event_id": created.get("id"),
        "link": created.get("htmlLink"),
        "start": start.isoformat(),
        "end": end.isoformat(),
    }