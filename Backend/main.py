from dotenv import load_dotenv

# Load local .env before importing modules that read environment variables.
# On Vercel, configure these values in Project Settings -> Environment Variables.
load_dotenv()

import os
import uuid
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langgraph.types import Command

from agents.summrizer import graph
from agents.spam import spam_graph
from agents.email_generator import email_graph
from agents.grammar_check import grammar_graph
from agents.email_approval import approval_graph
from agents.calendar_agent import calendar_graph, TZ_NAME

from services.emailsender import send_email, EmailSendError
from services.calendar_service import CalendarError, parse_event_times
from services.google_oauth import router as google_router
from routers.user_auth import router as auth_router, get_current_user
from routers.stats import router as stats_router, log, resolve


app = FastAPI(title="MailMind API")


# ---------- CORS ----------
ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(google_router)
app.include_router(stats_router)


# ---------- Health ----------
@app.get("/")
async def root():
    return {"status": "ok", "app": "MailMind API"}


@app.get("/health")
async def health():
    # This checks that the application is responding; it does not verify MongoDB/LLM.
    return {"status": "ok", "app": "MailMind API"}


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
    tone: Literal[
        "formal", "professional", "friendly", "casual",
        "persuasive", "apologetic", "urgent",
    ] = "professional"
    length: Literal["short", "medium", "long"] = "medium"
    emoji: Literal["none", "minimal", "moderate", "expressive"] = "none"
    language: str = "English"


class GenerateOut(BaseModel):
    subject: str
    body: str


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
    subject: Optional[str] = None
    body: Optional[str] = None


class EventIn(BaseModel):
    title: str = ""
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    attendees: list[str] = Field(default_factory=list)
    description: str = ""


class CalendarDecisionIn(BaseModel):
    thread_id: str
    action: Literal["approve", "reject"]
    event: Optional[EventIn] = None
    send_invites: bool = False


# ---------- Helpers ----------
def _validate_email(email: EmailIn) -> None:
    if not email.body.strip():
        raise HTTPException(status_code=400, detail="Email body empty hai")


async def _run_spam_check(email: EmailIn) -> dict:
    return await spam_graph.ainvoke(email.model_dump())


def _owner(user: dict) -> str:
    email = user.get("email")
    name = user.get("name")
    if email:
        return email
    if name:
        return name
    raise HTTPException(status_code=400, detail="User profile mein email/name missing hai")


def _require_gmail(user: dict) -> None:
    if not (user.get("google") or {}).get("refresh_token"):
        raise HTTPException(
            status_code=400,
            detail="Pehle Settings mein apna Gmail connect karo.",
        )


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def _get_graph_state(graph_obj, config: dict):
    """Convert missing checkpoint/state into a controlled 404 instead of an unhandled 500."""
    try:
        snapshot = await graph_obj.aget_state(config)
    except Exception as exc:
        # Do not return internal exception details to the client.
        raise HTTPException(
            status_code=404,
            detail="Workflow state nahi mila. Draft expire ho sakta hai.",
        ) from exc

    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Draft nahi mila ya expire ho chuka hai")
    return snapshot


def _verify_owner(snapshot, user: dict) -> None:
    if snapshot.values.get("owner") != _owner(user):
        raise HTTPException(status_code=403, detail="Ye draft tumhara nahi hai")


# ---------- Protected Routes ----------
@app.post("/spam", response_model=SpamOut)
async def check_spam(email: EmailIn, user: dict = Depends(get_current_user)):
    _validate_email(email)
    result = await _run_spam_check(email)
    await log(
        user,
        "spam",
        email.sender,
        "spam" if result["is_spam"] else "not_spam",
    )
    return {
        "verdict": result["verdict"],
        "is_spam": result["is_spam"],
        "confidence": result["confidence"],
        "reason": result["reason"],
    }


@app.post("/summarize", response_model=SummaryOut)
async def summarize(email: EmailIn, user: dict = Depends(get_current_user)):
    _validate_email(email)

    spam = await _run_spam_check(email)
    if spam["is_spam"]:
        await log(user, "summarize", email.subject, "spam")
        return {
            "summary": None,
            "is_spam": True,
            "spam_reason": spam["reason"],
        }

    result = await graph.ainvoke(email.model_dump())
    await log(user, "summarize", email.subject, "summarized")
    return {"summary": result["summary"], "is_spam": False}


@app.post("/generate", response_model=GenerateOut)
async def generate_email(req: GenerateIn, user: dict = Depends(get_current_user)):
    if not req.purpose.strip():
        raise HTTPException(status_code=400, detail="purpose empty hai")

    result = await email_graph.ainvoke(req.model_dump())
    await log(user, "generate", req.purpose, "generated")
    return {"subject": result["subject"], "body": result["body"]}


@app.post("/draft", response_model=DraftOut)
async def draft(req: DraftIn, user: dict = Depends(get_current_user)):
    _require_gmail(user)
    if not req.purpose.strip():
        raise HTTPException(status_code=400, detail="purpose empty hai")

    thread_id = str(uuid.uuid4())
    config = _thread_config(thread_id)

    payload = req.model_dump()
    if not payload.get("sender_name", "").strip():
        payload["sender_name"] = user.get("name") or ""
    payload["owner"] = _owner(user)

    try:
        await approval_graph.ainvoke(payload, config)
        snapshot = await approval_graph.aget_state(config)
    except Exception as exc:
        # Details are available in Vercel Runtime Logs.
        print(f"Email draft workflow failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Email draft generate nahi hua. Server logs check karo.",
        ) from exc

    values = snapshot.values or {}
    if not all(key in values for key in ("to", "subject", "body")):
        raise HTTPException(
            status_code=500,
            detail="Draft workflow ne expected subject/body return nahi kiya.",
        )

    await log(user, "draft", req.purpose, "awaiting_approval", thread_id)
    return {
        "thread_id": thread_id,
        "to": values["to"],
        "subject": values["subject"],
        "body": values["body"],
    }


@app.get("/draft/{thread_id}", response_model=DraftOut)
async def get_draft(thread_id: str, user: dict = Depends(get_current_user)):
    config = _thread_config(thread_id)
    snapshot = await _get_graph_state(approval_graph, config)
    _verify_owner(snapshot, user)

    if not snapshot.next:
        raise HTTPException(status_code=404, detail="Draft pehle hi process ho chuka hai")

    values = snapshot.values
    return {
        "thread_id": thread_id,
        "to": values["to"],
        "subject": values["subject"],
        "body": values["body"],
    }


@app.post("/approve")
async def approve(req: DecisionIn, user: dict = Depends(get_current_user)):
    config = _thread_config(req.thread_id)
    snapshot = await _get_graph_state(approval_graph, config)
    _verify_owner(snapshot, user)

    if not snapshot.next:
        raise HTTPException(status_code=404, detail="Draft pehle hi process ho chuka hai")

    if "human_review" in snapshot.next:
        if req.action == "edit" and not (req.subject or req.body):
            raise HTTPException(
                status_code=400,
                detail="edit ke liye subject ya body do",
            )
        if req.action != "reject":
            _require_gmail(user)
        command = Command(resume=req.model_dump())
    else:
        if req.action == "reject":
            await resolve(user, req.thread_id, "rejected")
            return {"status": "rejected"}
        _require_gmail(user)
        command = None

    try:
        result = await approval_graph.ainvoke(command, config)
    except EmailSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Email approval workflow failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Email send workflow fail hua. Server logs check karo.",
        ) from exc

    if result.get("decision") == "reject":
        await resolve(user, req.thread_id, "rejected")
        return {"status": "rejected"}

    await resolve(user, req.thread_id, "approved")
    await log(user, "send", snapshot.values.get("to", ""), "sent")
    return result.get("send_result", {"status": "completed"})


@app.post("/send")
async def send(req: SendIn, user: dict = Depends(get_current_user)):
    _require_gmail(user)
    data = req.model_dump()
    if not (data.get("sender_name") or "").strip():
        data["sender_name"] = user.get("name") or ""

    try:
        result = await run_in_threadpool(send_email, user, **data)
    except EmailSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await log(user, "send", req.to, "sent")
    return result


@app.post("/grammar-check", response_model=GrammarOut)
async def grammar_check(req: GrammarIn, user: dict = Depends(get_current_user)):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text empty hai")
    if len(req.text) > 8000:
        raise HTTPException(
            status_code=400,
            detail="Text bahut lamba hai (max 8000 characters)",
        )

    try:
        result = await grammar_graph.ainvoke({
            "text": req.text,
            "language": req.language,
            "strict": req.strict,
        })
    except Exception as exc:
        print(f"Grammar check failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Grammar check failed. Server logs check karo.",
        ) from exc

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
    _validate_email(email)

    thread_id = str(uuid.uuid4())
    config = _thread_config(thread_id)

    try:
        await calendar_graph.ainvoke(
            {
                "sender": email.sender,
                "subject": email.subject,
                "body": email.body,
                "owner": _owner(user),
            },
            config,
        )
        snapshot = await calendar_graph.aget_state(config)
    except Exception as exc:
        print(f"Calendar draft workflow failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Calendar draft process nahi hua. Server logs check karo.",
        ) from exc

    if not snapshot.next:
        await log(user, "calendar", email.subject, "no_meeting")
        return {"has_meeting": False, "thread_id": None, "event": None}

    await log(user, "calendar", email.subject, "awaiting_approval", thread_id)
    return {
        "has_meeting": True,
        "thread_id": thread_id,
        "event": snapshot.values["event"],
    }


@app.get("/calendar/draft/{thread_id}")
async def get_calendar_draft(thread_id: str, user: dict = Depends(get_current_user)):
    config = _thread_config(thread_id)
    snapshot = await _get_graph_state(calendar_graph, config)
    _verify_owner(snapshot, user)

    if not snapshot.next:
        raise HTTPException(status_code=404, detail="Calendar draft pehle hi process ho chuka hai")

    return {
        "has_meeting": True,
        "thread_id": thread_id,
        "event": snapshot.values["event"],
    }


@app.post("/calendar/approve")
async def calendar_approve(
    req: CalendarDecisionIn,
    user: dict = Depends(get_current_user),
):
    config = _thread_config(req.thread_id)
    snapshot = await _get_graph_state(calendar_graph, config)
    _verify_owner(snapshot, user)

    if not snapshot.next:
        raise HTTPException(
            status_code=404,
            detail="Calendar draft pehle hi process ho chuka hai",
        )

    title = snapshot.values.get("event", {}).get("title", "")

    if "human_review" in snapshot.next:
        payload = {"action": req.action}

        if req.action == "approve":
            if not req.event:
                raise HTTPException(
                    status_code=400,
                    detail="approve ke liye event details do",
                )

            event = req.event.model_dump()
            try:
                parse_event_times(event, TZ_NAME)
            except CalendarError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            payload["event"] = event
            payload["send_invites"] = req.send_invites

        command = Command(resume=payload)
    else:
        if req.action == "reject":
            await resolve(user, req.thread_id, "rejected")
            return {"status": "rejected"}
        command = None

    try:
        result = await calendar_graph.ainvoke(command, config)
    except CalendarError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"Calendar approval workflow failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Calendar event create nahi hua. Server logs check karo.",
        ) from exc

    if result.get("decision") == "reject":
        await resolve(user, req.thread_id, "rejected")
        return {"status": "rejected"}

    await resolve(user, req.thread_id, "approved")
    await log(user, "calendar", title, "created")
    return result.get("event_result", {"status": "completed"})
