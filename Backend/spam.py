

import re
from typing import TypedDict, List, Optional

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from llm import llm  # shared Groq LLM (llm.py)


# ---------- State ----------
class SpamState(TypedDict, total=False):
    sender: str
    subject: str
    body: str
    rule_score: int
    rule_flags: List[str]
    is_spam: Optional[bool]
    confidence: float
    reason: str
    verdict: str


# ---------- LLM structured output ----------
class SpamResult(BaseModel):
    is_spam: bool = Field(description="True if the email is spam/phishing/scam/unsolicited promo")
    confidence: float = Field(description="Confidence between 0 and 1")
    reason: str = Field(description="One short sentence explaining the decision")


structured_llm = llm.with_structured_output(SpamResult)


# ---------- Nodes ----------
SPAM_KEYWORDS = [
    "you have won", "lottery", "claim your prize", "free money", "act now",
    "urgent action required", "verify your account", "password expired",
    "click here", "limited time offer", "100% free", "guaranteed income",
    "crypto giveaway", "wire transfer", "congratulations", "no investment",
    "work from home and earn", "unsubscribe",
]


def rule_check(state: SpamState) -> SpamState:
    """Fast heuristic pass - obvious spam signals pakadta hai bina LLM call kiye."""
    text = f"{state.get('subject', '')} {state.get('body', '')}".lower()
    flags: List[str] = []
    score = 0

    for kw in SPAM_KEYWORDS:
        if kw in text:
            flags.append(f"keyword: {kw}")
            score += 1

    if len(re.findall(r"https?://\S+", text)) >= 3:
        flags.append("many links")
        score += 2

    if re.search(r"https?://(bit\.ly|tinyurl\.com|t\.co)/", text):
        flags.append("shortened link")
        score += 1

    subject = state.get("subject", "")
    if subject and subject.isupper() and len(subject) > 8:
        flags.append("ALL CAPS subject")
        score += 1

    if text.count("!") >= 4:
        flags.append("too many exclamation marks")
        score += 1

    return {"rule_score": score, "rule_flags": flags}


def route_after_rules(state: SpamState) -> str:
    # Score bahut high hai to seedha spam, warna LLM se poocho
    return "finalize" if state["rule_score"] >= 5 else "llm_classify"


def llm_classify(state: SpamState) -> SpamState:
    prompt = f"""You are an email spam filter. Decide if the email below is spam
(including phishing, scams, unsolicited bulk promotions).
Genuine personal, work, transactional (OTP, receipts) and newsletters the user
likely subscribed to are NOT spam.

Heuristic flags already detected: {state.get('rule_flags') or 'none'}

From: {state.get('sender', 'unknown')}
Subject: {state.get('subject', '')}
Body:
{state.get('body', '')[:3000]}
"""
    result: SpamResult = structured_llm.invoke(prompt)
    return {
        "is_spam": result.is_spam,
        "confidence": result.confidence,
        "reason": result.reason,
    }


def finalize(state: SpamState) -> SpamState:
    # Rule-based shortcut se aaya hua case (LLM skip hua)
    if state.get("is_spam") is None:
        return {
            "is_spam": True,
            "confidence": 0.95,
            "reason": "Multiple spam signals: " + ", ".join(state.get("rule_flags", [])),
            "verdict": "SPAM",
        }
    return {"verdict": "SPAM" if state["is_spam"] else "NOT SPAM"}


# ---------- Graph ----------
def build_graph():
    graph = StateGraph(SpamState)

    graph.add_node("rule_check", rule_check)
    graph.add_node("llm_classify", llm_classify)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "rule_check")
    graph.add_conditional_edges(
        "rule_check",
        route_after_rules,
        {"finalize": "finalize", "llm_classify": "llm_classify"},
    )
    graph.add_edge("llm_classify", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


spam_graph = build_graph()


def check_spam(subject: str, body: str, sender: str = "") -> dict:
    """main.py se call karne ke liye helper."""
    result = spam_graph.invoke({"sender": sender, "subject": subject, "body": body})
    return {
        "verdict": result["verdict"],
        "is_spam": result["is_spam"],
        "confidence": result["confidence"],
        "reason": result["reason"],
    }


if __name__ == "__main__":
    samples = [
        {
            "sender": "promo@win-big.xyz",
            "subject": "CONGRATULATIONS!!! YOU HAVE WON",
            "body": "Click here to claim your prize now! Act now, limited time offer! http://bit.ly/abc",
        },
        {
            "sender": "hr@company.com",
            "subject": "Interview scheduled for Monday",
            "body": "Hi Rohit, your interview is scheduled for Monday 11 AM. Please confirm.",
        },
    ]
    for s in samples:
        print(s["subject"], "->", check_spam(**{k: s[k] for k in ("subject", "body", "sender")}))