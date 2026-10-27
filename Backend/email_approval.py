from typing import Optional

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from email_generator import (
    EmailGenState, validate_inputs, build_prompt, generate, finalize,
)
from emailsender import send_email
from user_auth import users
from emailsender import send_email, EmailSendError


class ApprovalState(EmailGenState, total=False):
    owner: str            # kis user ka draft hai
    to: str
    cc: Optional[str]
    bcc: Optional[str]
    html: bool
    decision: str         # "approve" | "reject"
    send_result: dict


def human_review(state: ApprovalState):
    # Yahan graph pause hoga. Resume par interrupt() wahi value return karega
    # jo Command(resume=...) me di gayi.
    # NOTE: resume par ye node shuru se dubara chalta hai, isliye isme
    # koi side effect (send/DB write) mat rakhna.
    decision = interrupt({
        "to": state["to"],
        "subject": state["subject"],
        "body": state["body"],
    })

    action = decision.get("action")
    if action == "approve":
        return {"decision": "approve"}
    if action == "edit":
        return {
            "decision": "approve",
            "subject": (decision.get("subject") or state["subject"]).strip(),
            "body": (decision.get("body") or state["body"]).strip(),
        }
    return {"decision": "reject"}


def send(state: ApprovalState):
    user = users.find_one({"email": state["owner"]})   # owner = login email
    if not user:
        raise EmailSendError("User nahi mila")
    result = send_email(
        user=user,
        to=state["to"],
        subject=state["subject"],
        body=state["body"],
        cc=state.get("cc"),
        bcc=state.get("bcc"),
        html=state.get("html", False),
        sender_name=state.get("sender_name") or None,
    )
    return {"send_result": result}

def route_after_review(state: ApprovalState) -> str:
    return "send" if state["decision"] == "approve" else "end"


def build_approval_graph():
    g = StateGraph(ApprovalState)
    g.add_node("validate_inputs", validate_inputs)
    g.add_node("build_prompt", build_prompt)
    g.add_node("generate", generate)
    g.add_node("finalize", finalize)
    g.add_node("human_review", human_review)
    g.add_node("send", send)

    g.add_edge(START, "validate_inputs")
    g.add_edge("validate_inputs", "build_prompt")
    g.add_edge("build_prompt", "generate")
    g.add_edge("generate", "finalize")
    g.add_edge("finalize", "human_review")
    g.add_conditional_edges("human_review", route_after_review,
                            {"send": "send", "end": END})
    g.add_edge("send", END)

    # checkpointer ke bina interrupt kaam nahi karta
    return g.compile(checkpointer=MemorySaver())


approval_graph = build_approval_graph()