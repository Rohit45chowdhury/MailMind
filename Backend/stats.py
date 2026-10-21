from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pymongo import ASCENDING, DESCENDING

from user_auth import MONGODB_DB, client, get_current_user

events = client[MONGODB_DB]["activity"]
events.create_index([("user_id", ASCENDING), ("at", DESCENDING)])

router = APIRouter(tags=["stats"])


def _record(user: dict, tool: str, detail: str, status: str) -> None:
    try:
        events.insert_one({
            "user_id": user["_id"],
            "tool": tool,                 # spam | summarize | generate | grammar | send
            "detail": (detail or "")[:80],  # sirf chhota label, email ka body kabhi nahi
            "status": status,
            "at": datetime.now(timezone.utc),
        })
    except Exception:
        pass  # stats fail ho to tool call kabhi nahi tootna chahiye


async def log(user: dict, tool: str, detail: str, status: str) -> None:
    await run_in_threadpool(_record, user, tool, detail, status)


def _build_stats(user_id) -> dict:
    counts: dict[tuple, int] = {}
    for row in events.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"tool": "$tool", "status": "$status"}, "n": {"$sum": 1}}},
    ]):
        counts[(row["_id"]["tool"], row["_id"]["status"])] = row["n"]

    def tool_total(tool):
        return sum(n for (t, _), n in counts.items() if t == tool)

    recent = []
    for e in events.find({"user_id": user_id}).sort("at", DESCENDING).limit(5):
        recent.append({
            "tool": e["tool"],
            "detail": e["detail"],
            "status": e["status"],
            "at": e["at"].replace(tzinfo=timezone.utc).isoformat(),
        })

    return {
        "checked": tool_total("spam") + tool_total("summarize"),
        "spam": sum(n for (_, s), n in counts.items() if s == "spam"),
        "summaries": counts.get(("summarize", "summarized"), 0),
        "generated": tool_total("generate"),
        "grammar": tool_total("grammar"),
        "sent": counts.get(("send", "sent"), 0),
        "recent": recent,
    }


@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    return await run_in_threadpool(_build_stats, user["_id"])


@router.delete("/stats")
async def reset_stats(user: dict = Depends(get_current_user)):
    await run_in_threadpool(events.delete_many, {"user_id": user["_id"]})
    return {"ok": True}