import re
from typing import TypedDict, Literal, List

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from services.llm import llm  

Tone = Literal["formal", "professional", "friendly", "casual", "persuasive", "apologetic", "urgent"]
Length = Literal["short", "medium", "long"]
Emoji = Literal["none", "minimal", "moderate", "expressive"]

TONE_GUIDE = {
    "formal": "Formal and respectful, traditional business language, no slang or contractions.",
    "professional": "Clear, polite and confident, workplace appropriate, to the point.",
    "friendly": "Warm and approachable, positive, like writing to a colleague you like.",
    "casual": "Relaxed and conversational, simple words, contractions are fine.",
    "persuasive": "Convincing and benefit-focused, with a clear call to action.",
    "apologetic": "Sincere and humble, takes responsibility, offers a way to make it right.",
    "urgent": "Direct and time-sensitive, states the deadline/impact early, still polite.",
}

LENGTH_GUIDE = {
    "short": "Short: about 40-80 words in the body, 1-2 small paragraphs.",
    "medium": "Medium: about 100-160 words in the body, 2-3 paragraphs.",
    "long": "Long: about 200-300 words in the body, 3-5 paragraphs with full detail.",
}

EMOJI_GUIDE = {
    "none": "Do NOT use any emoji.",
    "minimal": "Use at most 1-2 emoji in the whole email, only where natural (e.g. greeting or closing).",
    "moderate": "Use around 3-5 emoji spread naturally through the email.",
    "expressive": "Use emoji generously (6-10), including in the subject line, but keep it readable.",
}

NO_RECIPIENT = "the recipient"
MAX_PURPOSE = 2000
MAX_DETAILS = 1000
MAX_RETRIES = 2

EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]+",
    flags=re.UNICODE,
)
PLACEHOLDER_PATTERN = re.compile(r"\[[^\]\n]{1,60}\]")


# ---------- State ----------
class EmailGenState(TypedDict, total=False):
    purpose: str
    details: str
    recipient: str
    sender_name: str
    tone: str
    length: str
    emoji: str
    language: str
    prompt: str
    subject: str
    body: str
    llm_missing: List[str]
    missing_details: List[str]


# ---------- LLM structured output ----------
class GeneratedEmail(BaseModel):
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body including greeting and sign-off")
    missing_details: List[str] = Field(
        default_factory=list,
        description="Important facts this kind of email needs but the user did not give, "
                    "e.g. ['date', 'time', 'venue']. Empty list if nothing important is missing.",
    )


structured_llm = llm.with_structured_output(GeneratedEmail)


# ---------- Helpers ----------
def _fix_placeholders(text: str, recipient: str, sender_name: str) -> str:
    """Sirf NAAM wale placeholders ([Your Name], [Manager's Name]) code se fix karo.
    [DATE], [VENUE] jaise baaki placeholders jaise hain waise rehne do."""

    def repl(m: re.Match) -> str:
        inner = m.group(0).lower()
        if "name" not in inner:
            return m.group(0)  # [DATE], [TIME], [VENUE] ko mat chhedo

        is_sender = any(w in inner for w in ("your", "sender", "my name"))
        if is_sender:
            return sender_name  # khali ho sakta hai
        if recipient and recipient != NO_RECIPIENT:
            return recipient
        return ""

    text = PLACEHOLDER_PATTERN.sub(repl, text)
    text = re.sub(r"[ \t]{2,}", " ", text)   # double space
    text = re.sub(r"\s+,", ",", text)        # "Hi ," -> "Hi,"
    return text.strip()


def _left_placeholders(*texts: str) -> List[str]:
    """Bache hue [DATE]-type placeholders ke labels."""
    found = []
    for t in texts:
        for m in PLACEHOLDER_PATTERN.findall(t):
            label = m.strip("[]").strip().lower()
            if label and label not in found:
                found.append(label)
    return found


# ---------- Nodes ----------
def validate_inputs(state: EmailGenState) -> EmailGenState:
    purpose = (state.get("purpose") or "").strip()
    if not purpose:
        raise ValueError("Email kis baare me likhna hai, ye batao.")
    return {
        "purpose": purpose[:MAX_PURPOSE],
        "details": (state.get("details") or "").strip()[:MAX_DETAILS],
        "tone": state.get("tone") or "professional",
        "length": state.get("length") or "medium",
        "emoji": state.get("emoji") or "none",
        "recipient": (state.get("recipient") or "").strip() or NO_RECIPIENT,
        "sender_name": (state.get("sender_name") or "").strip(),
        "language": state.get("language") or "English",
    }


def build_prompt(state: EmailGenState) -> EmailGenState:
    recipient = state["recipient"]
    sender = state["sender_name"]

    if recipient == NO_RECIPIENT:
        greeting_rule = "Start with a plain greeting like 'Hello,' (recipient name is unknown, do NOT invent one)."
    else:
        greeting_rule = (
            f"Greet the recipient using exactly this name: '{recipient}' "
            f"(e.g. 'Hi {recipient},' or 'Dear {recipient},' for formal tone). "
            "Do NOT add or invent any other name or surname."
        )

    if sender:
        sign_off_rule = f"Sign off with exactly this name and nothing added: '{sender}'."
    else:
        sign_off_rule = "Sign off with a generic closing (e.g. 'Best regards') and NO name."

    details_block = state["details"] or "none provided"

    prompt = f"""You are an expert email writer. Write an email based on the details below.

Purpose / what to say: {state['purpose']}
Key details (dates, times, venue, amounts, deadlines, etc.): {details_block}
Recipient: {recipient}
Language: {state['language']}

Tone: {TONE_GUIDE[state['tone']]}
Length: {LENGTH_GUIDE[state['length']]}
Emoji: {EMOJI_GUIDE[state['emoji']]}

Rules:
- Include a greeting and a closing.
- {greeting_rule}
- {sign_off_rule}
- Use ONLY facts from the purpose and key details. Never invent dates, times, venues, amounts, names or numbers.
- If an important fact for this kind of email is missing (for example date, time and venue for an invitation, or the deadline for a request), write that spot as an UPPERCASE placeholder such as [DATE], [TIME], [VENUE], [DEADLINE], [AMOUNT]. Use only these short uppercase placeholders.
- Never write placeholders for names (no [Name], [Your Name], [Manager's Name]). If a name is unknown, leave it out.
- In missing_details, list the missing facts in plain words (e.g. "date", "time", "venue"). Use an empty list if nothing important is missing.
"""
    return {"prompt": prompt}


def generate(state: EmailGenState) -> EmailGenState:
    last_err = None
    for _ in range(MAX_RETRIES + 1):
        try:
            result: GeneratedEmail = structured_llm.invoke(state["prompt"])
            if result and result.body and result.body.strip():
                return {
                    "subject": (result.subject or "").strip(),
                    "body": result.body.strip(),
                    "llm_missing": [m.strip().lower() for m in result.missing_details if m.strip()],
                }
        except Exception as e:  # Groq timeout / bad JSON / rate limit
            last_err = e
    raise RuntimeError(f"Email generate nahi ho paya, thodi der baad try karo. ({last_err})")


def finalize(state: EmailGenState) -> EmailGenState:
    subject = _fix_placeholders(state["subject"], state["recipient"], state["sender_name"])
    body = _fix_placeholders(state["body"], state["recipient"], state["sender_name"])

    if state["emoji"] == "none":
        subject = EMOJI_PATTERN.sub("", subject).strip()
        body = EMOJI_PATTERN.sub("", body).strip()

    if not subject:
        subject = "(No subject)"

    # LLM ki list + code se mile bache hue placeholders, dono merge
    missing = list(state.get("llm_missing", []))
    for label in _left_placeholders(subject, body):
        if label not in missing:
            missing.append(label)

    return {"subject": subject, "body": body, "missing_details": missing}


# ---------- Graph ----------
def build_graph():
    graph = StateGraph(EmailGenState)

    graph.add_node("validate_inputs", validate_inputs)
    graph.add_node("build_prompt", build_prompt)
    graph.add_node("generate", generate)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "validate_inputs")
    graph.add_edge("validate_inputs", "build_prompt")
    graph.add_edge("build_prompt", "generate")
    graph.add_edge("generate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


email_graph = build_graph()


async def generate_email(
    purpose: str,
    details: str = "",
    recipient: str = "",
    sender_name: str = "",
    tone: Tone = "professional",
    length: Length = "medium",
    emoji: Emoji = "none",
    language: str = "English",
) -> dict:
    result = await email_graph.ainvoke(
        {
            "purpose": purpose,
            "details": details,
            "recipient": recipient,
            "sender_name": sender_name,
            "tone": tone,
            "length": length,
            "emoji": emoji,
            "language": language,
        }
    )
    return {
        "subject": result["subject"],
        "body": result["body"],
        "missing_details": result.get("missing_details", []),
    }


if __name__ == "__main__":
    import asyncio

    out = asyncio.run(generate_email(
        purpose="Invite Tarang to my birthday party",
        recipient="Tarang",
        sender_name="Rohit Chowdhury",
        tone="friendly",
        length="short",
    ))
    print("Subject:", out["subject"])
    print()
    print(out["body"])
    print("\nMissing:", out["missing_details"])