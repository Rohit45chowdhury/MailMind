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
from stats import router as stats_router, log

app = FastAPI(title="Email Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
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


# ---------- Helpers ----------
def _validate(email: EmailIn):
    if not email.body.strip():
        raise HTTPException(400, "Email body empty hai")


async def _run_spam_check(email: EmailIn) -> dict:
    return await spam_graph.ainvoke(email.model_dump())


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


@app.post("/send")
async def send(req: SendIn, user: dict = Depends(get_current_user)):
    data = req.model_dump()
    if not (data.get("sender_name") or "").strip():
        data["sender_name"] = user["name"]
    try:
        result = await run_in_threadpool(send_email, **data)
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