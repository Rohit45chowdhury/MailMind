import os
from datetime import datetime
from typing import Optional, TypedDict
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from services.llm import llm
from services.calendar_service import create_event

TZ_NAME = os.getenv("CALENDAR_TIMEZONE", "Asia/Kolkata")  # fallback timezone


# ---------- State ----------
class CalState(TypedDict, total=False):
    owner: str             # user email (draft ownership check)
    user_id: str           # Mongo _id, token isi se load hota hai
    tz: str                # user ka IANA timezone
    sender: str
    subject: str
    body: str
    has_meeting: bool
    event: dict
    decision: str          # "approve" | "reject"
    send_invites: bool
    event_result: dict


# ---------- LLM structured output ----------
class ExtractedEvent(BaseModel):
    has_meeting: bool = Field(
        description="True only if the email proposes or confirms a specific meeting/call/event with a date or time"
    )
    title: str = Field(default="", description="Short event title")
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD, null if not stated")
    start_time: Optional[str] = Field(default=None, description="HH:MM 24-hour, null if not stated")
    end_time: Optional[str] = Field(default=None, description="HH:MM 24-hour, null if not stated")
    location: Optional[str] = Field(default=None, description="Place or meeting link, null if not stated")
    attendees: list[str] = Field(default_factory=list, description="Email addresses that appear in the email")
    description: str = Field(default="", description="One or two lines of agenda/context")


structured_llm = llm.with_structured_output(ExtractedEvent)


# ---------- Nodes ----------
def extract(state: CalState) -> CalState:
    tz_name = state.get("tz") or TZ_NAME
    now = datetime.now(ZoneInfo(tz_name))
    prompt = f"""You extract meeting details from an email.

Today is {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}). Timezone: {tz_name}.
Resolve relative dates like "tomorrow" or "next Monday" using today's date.

Rules:
- has_meeting = true ONLY if the email proposes or confirms a specific meeting, call or event with a date or time.
- Do not invent anything. If the date or time is not stated, leave it null.
- Date as YYYY-MM-DD, times as 24-hour HH:MM.
- attendees: only email addresses that literally appear in the text.

From: {state['sender']}
Subject: {state['subject']}

Body:
{state['body'][:6000]}
"""
    r: ExtractedEvent = structured_llm.invoke(prompt)
    event = {
        "title": (r.title or state["subject"]).strip(),
        "date": r.date,
        "start_time": r.start_time,
        "end_time": r.end_time,
        "location": r.location,
        "attendees": [a.strip() for a in r.attendees if "@" in a],
        "description": r.description.strip(),
    }
    return {"has_meeting": r.has_meeting, "event": event}


def route_after_extract(state: CalState) -> str:
    return "review" if state["has_meeting"] else "end"


def human_review(state: CalState):
    # Graph pauses here. This node re-runs from the top on resume,
    # so keep it free of side effects.
    decision = interrupt({"event": state["event"]})

    if decision.get("action") != "approve":
        return {"decision": "reject"}

    edited = decision.get("event") or {}
    return {
        "decision": "approve",
        "event": {**state["event"], **edited},
        "send_invites": bool(decision.get("send_invites")),
    }


def route_after_review(state: CalState) -> str:
    return "create" if state["decision"] == "approve" else "end"


def create(state: CalState):
    result = create_event(
        state["event"],
        state.get("tz") or TZ_NAME,
        state["user_id"],
        send_invites=state.get("send_invites", False),
    )
    return {"event_result": result}


# ---------- Graph ----------
def build_calendar_graph():
    g = StateGraph(CalState)
    g.add_node("extract", extract)
    g.add_node("human_review", human_review)
    g.add_node("create", create)

    g.add_edge(START, "extract")
    g.add_conditional_edges("extract", route_after_extract,
                            {"review": "human_review", "end": END})
    g.add_conditional_edges("human_review", route_after_review,
                            {"create": "create", "end": END})
    g.add_edge("create", END)

    # NOTE: MemorySaver restart / multiple instances par pending approvals kho deta hai
    return g.compile(checkpointer=MemorySaver())


calendar_graph = build_calendar_graph()