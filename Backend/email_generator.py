

from typing import TypedDict, Optional, Literal

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from llm import llm  # shared Groq LLM (llm.py)

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


# ---------- State ----------
class EmailGenState(TypedDict, total=False):
    purpose: str
    recipient: str
    sender_name: str
    tone: str
    length: str
    emoji: str
    language: str
    prompt: str
    subject: str
    body: str


# ---------- LLM structured output ----------
class GeneratedEmail(BaseModel):
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body including greeting and sign-off")


structured_llm = llm.with_structured_output(GeneratedEmail)


# ---------- Nodes ----------
def validate_inputs(state: EmailGenState) -> EmailGenState:
    if not state.get("purpose", "").strip():
        raise ValueError("purpose empty hai, email kis baare me likhna hai batao")
    return {
        "tone": state.get("tone") or "professional",
        "length": state.get("length") or "medium",
        "emoji": state.get("emoji") or "none",
        "recipient": state.get("recipient") or "the recipient",
        "sender_name": state.get("sender_name") or "",
        "language": state.get("language") or "English",
    }


def build_prompt(state: EmailGenState) -> EmailGenState:
    sign_off = (
        f"Sign off with the name: {state['sender_name']}."
        if state["sender_name"]
        else "Sign off with a generic closing and no name placeholder."
    )
    prompt = f"""You are an expert email writer. Write an email based on the details below.

Purpose / what to say: {state['purpose']}
Recipient: {state['recipient']}
Language: {state['language']}

Tone: {TONE_GUIDE[state['tone']]}
Length: {LENGTH_GUIDE[state['length']]}
Emoji: {EMOJI_GUIDE[state['emoji']]}

Rules:
- Include a greeting and a closing.
- {sign_off}
- Do not invent facts, dates or numbers that were not given.
- Do not leave placeholders like [Your Name] or [Date].
"""
    return {"prompt": prompt}


def generate(state: EmailGenState) -> EmailGenState:
    result: GeneratedEmail = structured_llm.invoke(state["prompt"])
    return {"subject": result.subject.strip(), "body": result.body.strip()}


def finalize(state: EmailGenState) -> EmailGenState:
    # Emoji "none" ho to safety ke liye koi emoji bach gaya ho to hata do
    if state["emoji"] == "none":
        import re

        emoji_pattern = re.compile(
            "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]+",
            flags=re.UNICODE,
        )
        return {
            "subject": emoji_pattern.sub("", state["subject"]).strip(),
            "body": emoji_pattern.sub("", state["body"]).strip(),
        }
    return {}


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


def generate_email(
    purpose: str,
    recipient: str = "",
    sender_name: str = "",
    tone: Tone = "professional",
    length: Length = "medium",
    emoji: Emoji = "none",
    language: str = "English",
) -> dict:
    """main.py ya script se call karne ke liye helper."""
    result = email_graph.invoke(
        {
            "purpose": purpose,
            "recipient": recipient,
            "sender_name": sender_name,
            "tone": tone,
            "length": length,
            "emoji": emoji,
            "language": language,
        }
    )
    return {"subject": result["subject"], "body": result["body"]}


if __name__ == "__main__":
    out = generate_email(
        purpose="Request 2 days leave next week for a family function",
        recipient="Manager",
        sender_name="Rohit",
        tone="friendly",
        length="short",
        emoji="minimal",
    )
    print("Subject:", out["subject"])
    print()
    print(out["body"])