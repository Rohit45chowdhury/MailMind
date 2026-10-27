from dotenv import load_dotenv
load_dotenv()  # user_auth import se PEHLE

from typing import Optional, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from summrizer import graph
from spam import spam_graph
from email_generator import email_graph
from emailsender import send_email, EmailSendError
from grammar_check import grammar_graph
from user_auth import router as auth_router, get_current_user
from google_oauth import router as google_router
from stats import router as stats_router, log
from calendar_agent import calendar_graph, TZ_NAME
from calendar_service import CalendarError, parse_event_times

import uuid
from langgraph.types import Command
from email_approval import approval_graph

app = FastAPI(title="Email Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(google_router)
app.include_router(stats_router)


# ---------- Schemas ----------
class GrammarIn(BaseModel):
    text: str
    language: str = "English"
    strict: bool = False


class GrammarOut(BaseModel):
    original_text: str
    corrected_text: str
    has_errors: bool
    issue_count: int
    issues: list[dict]


class SendIn(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    html: bool = False
    sender_name: Optional[str] = None


class EmailIn(BaseModel):
    sender: str
    subject: str
    body: str


class SummaryOut(BaseModel):
    summary: Optional[str] = None
    is_spam: bool = False
    spam_reason: Optional[str] = None


class SpamOut(BaseModel):
    verdict: str
    is_spam: bool
    confidence: float
    reason: str


class GenerateIn(BaseModel):
    purpose: str
    recipient: str = ""
    sender_name: str = ""
    tone: Literal["formal", "professional", "friendly", "casual",
                  "persuasive", "apologetic", "urgent"] = "professional"
    length: Literal["short", "medium", "long"] = "medium"
    emoji: Literal["none", "minimal", "moderate", "expressive"] = "none"
    language: str = "English"


class GenerateOut(BaseModel):
    subject: str
    body: str


# ---- approval schemas (GenerateIn ke BAAD) ----
class DraftIn(GenerateIn):
    to: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    html: bool = False


class DraftOut(BaseModel):
    thread_id: str
    to: str
    subject: str
    body: str


class DecisionIn(BaseModel):
    thread_id: str
    action: Literal["approve", "edit", "reject"]
    subject: Optional[str] = None   # sirf edit me
    body: Optional[str] = None      # sirf edit me


# ---------- Calendar (human-in-the-loop) ----------
class EventIn(BaseModel):
    title: str = ""
    date: Optional[str] = None          # YYYY-MM-DD
    start_time: Optional[str] = None    # HH:MM
    end_time: Optional[str] = None      # HH:MM, empty = 1 hour
    location: Optional[str] = None
    attendees: list[str] = []
    description: str = ""


class CalendarDecisionIn(BaseModel):
    thread_id: str
    action: Literal["approve", "reject"]
    event: Optional[EventIn] = None     # edited event, required for approve
    send_invites: bool = False


# ---------- Helpers ----------
def _validate(email: EmailIn):
    if not email.body.strip():
        raise HTTPException(400, "Email body empty hai")


async def _run_spam_check(email: EmailIn) -> dict:
    return await spam_graph.ainvoke(email.model_dump())


def _owner(user: dict) -> str:
    return user.get("email") or user["name"]


def _require_gmail(user: dict) -> None:
    """Mail bhejne se pehle check: user ne apna Gmail connect kiya hai?"""
    if not (user.get("google") or {}).get("refresh_token"):
        raise HTTPException(400, "Pehle Settings me apna Gmail connect karo.")


# ---------- Protected Routes ----------
@app.post("/spam", response_model=SpamOut)
async def check_spam(email: EmailIn, user: dict = Depends(get_current_user)):
    _validate(email)
    result = await _run_spam_check(email)
    await log(user, "spam", email.sender, "spam" if result["is_spam"] else "not_spam")
    return {
        "verdict": result["verdict"],
        "is_spam": result["is_spam"],
        "confidence": result["confidence"],
        "reason": result["reason"],
    }


@app.post("/summarize", response_model=SummaryOut)
async def summarize(email: EmailIn, user: dict = Depends(get_current_user)):
    _validate(email)

    spam = await _run_spam_check(email)
    if spam["is_spam"]:
        await log(user, "summarize", email.subject, "spam")
        return {"summary": None, "is_spam": True, "spam_reason": spam["reason"]}

    result = await graph.ainvoke(email.model_dump())
    await log(user, "summarize", email.subject, "summarized")
    return {"summary": result["summary"], "is_spam": False}


@app.post("/generate", response_model=GenerateOut)
async def generate_email(req: GenerateIn, user: dict = Depends(get_current_user)):
    if not req.purpose.strip():
        raise HTTPException(400, "purpose empty hai")
    result = await email_graph.ainvoke(req.model_dump())
    await log(user, "generate", req.purpose, "generated")
    return {"subject": result["subject"], "body": result["body"]}


@app.post("/draft", response_model=DraftOut)
async def draft(req: DraftIn, user: dict = Depends(get_current_user)):
    _require_gmail(user)  # generate se pehle hi rok do
    if not req.purpose.strip():
        raise HTTPException(400, "purpose empty hai")

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    payload = req.model_dump()
    if not payload["sender_name"].strip():
        payload["sender_name"] = user["name"]
    payload["owner"] = _owner(user)  # login email, send node isi se user dhoondhta hai

    # interrupt() par graph ruk jayega, send node abhi nahi chalega
    await approval_graph.ainvoke(payload, config)

    snap = await approval_graph.aget_state(config)
    await log(user, "draft", req.purpose, "awaiting_approval")
    return {
        "thread_id": thread_id,
        "to": snap.values["to"],
        "subject": snap.values["subject"],
        "body": snap.values["body"],
    }


@app.post("/approve")
async def approve(req: DecisionIn, user: dict = Depends(get_current_user)):
    config = {"configurable": {"thread_id": req.thread_id}}

    snap = await approval_graph.aget_state(config)
    if not snap.values or not snap.next:
        raise HTTPException(404, "Draft nahi mila ya pehle hi process ho chuka hai")
    if snap.values.get("owner") != _owner(user):
        raise HTTPException(403, "Ye draft tumhara nahi hai")

    if "human_review" in snap.next:
        # normal case: user ka decision abhi baaki hai
        if req.action == "edit" and not (req.subject or req.body):
            raise HTTPException(400, "edit ke liye subject ya body do")
        if req.action != "reject":
            _require_gmail(user)
        cmd = Command(resume=req.model_dump())
    else:
        # pehle approve ho chuka tha par send fail hua (jaise Gmail connection expire).
        # Ab sirf send node dubara chalana hai.
        if req.action == "reject":
            await log(user, "draft", snap.values["to"], "rejected")
            return {"status": "rejected"}
        _require_gmail(user)
        cmd = None

    try:
        result = await approval_graph.ainvoke(cmd, config)
    except EmailSendError as e:
        raise HTTPException(400, str(e))

    if result.get("decision") == "reject":
        await log(user, "draft", snap.values["to"], "rejected")
        return {"status": "rejected"}

    await log(user, "send", snap.values["to"], "sent")
    return result["send_result"]


@app.post("/send")
async def send(req: SendIn, user: dict = Depends(get_current_user)):
    _require_gmail(user)
    data = req.model_dump()
    if not (data.get("sender_name") or "").strip():
        data["sender_name"] = user["name"]
    try:
        # user pehla argument hai, mail usi ke Gmail se jaati hai
        result = await run_in_threadpool(send_email, user, **data)
    except EmailSendError as e:
        raise HTTPException(400, str(e))
    await log(user, "send", req.to, "sent")
    return result


@app.post("/grammar-check", response_model=GrammarOut)
async def grammar_check(req: GrammarIn, user: dict = Depends(get_current_user)):
    if not req.text.strip():
        raise HTTPException(400, "Text empty hai")
    if len(req.text) > 8000:
        raise HTTPException(400, "Text bahut lamba hai (max 8000 characters)")

    try:
        result = await grammar_graph.ainvoke({
            "text": req.text,
            "language": req.language,
            "strict": req.strict,
        })
    except Exception as e:
        raise HTTPException(500, f"Grammar check failed: {str(e)}")

    await log(user, "grammar", f"{result['issue_count']} issues", "checked")
    return {
        "original_text": req.text,
        "corrected_text": result["corrected_text"],
        "has_errors": result["has_errors"],
        "issue_count": result["issue_count"],
        "issues": result["issues"],
    }


@app.post("/calendar/draft")
async def calendar_draft(email: EmailIn, user: dict = Depends(get_current_user)):
    _validate(email)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    await calendar_graph.ainvoke(
        {
            "sender": email.sender,
            "subject": email.subject,
            "body": email.body,
            "owner": _owner(user),
        },
        config,
    )

    snap = await calendar_graph.aget_state(config)
    if not snap.next:  # graph ended without pausing -> no meeting found
        await log(user, "calendar", email.subject, "no_meeting")
        return {"has_meeting": False, "thread_id": None, "event": None}

    await log(user, "calendar", email.subject, "awaiting_approval")
    return {"has_meeting": True, "thread_id": thread_id, "event": snap.values["event"]}


@app.post("/calendar/approve")
async def calendar_approve(req: CalendarDecisionIn, user: dict = Depends(get_current_user)):
    config = {"configurable": {"thread_id": req.thread_id}}

    snap = await calendar_graph.aget_state(config)
    if not snap.values or not snap.next:
        raise HTTPException(404, "Draft nahi mila ya pehle hi process ho chuka hai")
    if snap.values.get("owner") != _owner(user):
        raise HTTPException(403, "Ye draft tumhara nahi hai")

    title = snap.values["event"].get("title", "")

    if "human_review" in snap.next:
        payload = {"action": req.action}
        if req.action == "approve":
            if not req.event:
                raise HTTPException(400, "approve ke liye event do")
            event = req.event.model_dump()
            try:
                parse_event_times(event, TZ_NAME)  # validate before resuming
            except CalendarError as e:
                raise HTTPException(400, str(e))
            payload["event"] = event
            payload["send_invites"] = req.send_invites
        cmd = Command(resume=payload)
    else:
        # Approved earlier but create failed (e.g. token problem): just retry create node
        if req.action == "reject":
            await log(user, "calendar", title, "rejected")
            return {"status": "rejected"}
        cmd = None

    try:
        result = await calendar_graph.ainvoke(cmd, config)
    except CalendarError as e:
        raise HTTPException(400, str(e))

    if result.get("decision") == "reject":
        await log(user, "calendar", title, "rejected")
        return {"status": "rejected"}

    await log(user, "calendar", title, "created")
    return result["event_result"]