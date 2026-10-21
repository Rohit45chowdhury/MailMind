from typing import Optional, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from summrizer import graph
from spam import spam_graph
from email_generator import email_graph
from fastapi.concurrency import run_in_threadpool
from emailsender import send_email, EmailSendError
from grammar_check import grammar_graph

app = FastAPI(title="Email Agent")


# ---------- CORS Configuration ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    to: str                      # "a@x.com" ya "a@x.com, b@y.com"
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


# ---------- Helpers ----------
def _validate(email: EmailIn):
    if not email.body.strip():
        raise HTTPException(400, "Email body empty hai")


async def _run_spam_check(email: EmailIn) -> dict:
    return await spam_graph.ainvoke(email.model_dump())


# ---------- Routes ----------
@app.post("/spam", response_model=SpamOut)
async def check_spam(email: EmailIn):
    _validate(email)
    result = await _run_spam_check(email)
    return {
        "verdict": result["verdict"],
        "is_spam": result["is_spam"],
        "confidence": result["confidence"],
        "reason": result["reason"],
    }


@app.post("/summarize", response_model=SummaryOut)
async def summarize(email: EmailIn):
    _validate(email)

    # Pehle spam check, spam hai to summarizer (LLM call) skip
    spam = await _run_spam_check(email)
    if spam["is_spam"]:
        return {"summary": None, "is_spam": True, "spam_reason": spam["reason"]}

    result = await graph.ainvoke(email.model_dump())
    return {"summary": result["summary"], "is_spam": False}


@app.post("/generate", response_model=GenerateOut)
async def generate_email(req: GenerateIn):
    if not req.purpose.strip():
        raise HTTPException(400, "purpose empty hai")
    result = await email_graph.ainvoke(req.model_dump())
    return {"subject": result["subject"], "body": result["body"]}


@app.post("/send")
async def send(req: SendIn):
    try:
        # smtplib blocking hai, isliye threadpool me chalate hain
        return await run_in_threadpool(send_email, **req.model_dump())
    except EmailSendError as e:
        raise HTTPException(400, str(e))


@app.post("/grammar-check", response_model=GrammarOut)
async def grammar_check(req: GrammarIn):
    if not req.text.strip():
        raise HTTPException(400, "Text empty hai")

    if len(req.text) > 8000:
        raise HTTPException(
            400,
            "Text bahut lamba hai (max 8000 characters)"
        )

    try:
        result = await grammar_graph.ainvoke({
            "text": req.text,
            "language": req.language,
            "strict": req.strict,
        })

        return {
            "original_text": req.text,
            "corrected_text": result["corrected_text"],
            "has_errors": result["has_errors"],
            "issue_count": result["issue_count"],
            "issues": result["issues"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Grammar check failed: {str(e)}"
        )