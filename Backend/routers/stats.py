from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pymongo import ASCENDING, DESCENDING

from routers.user_auth import MONGODB_DB, client, get_current_user

events = client[MONGODB_DB]["activity"]
events.create_index([("user_id", ASCENDING), ("at", DESCENDING)])
# thread_id sirf draft/calendar rows me hota hai, isliye sparse
events.create_index([("user_id", ASCENDING), ("thread_id", ASCENDING)], sparse=True)

router = APIRouter(tags=["stats"])


def _record(user: dict, tool: str, detail: str, status: str,
            thread_id: Optional[str] = None) -> None:
    try:
        doc = {
            "user_id": user["_id"],
            "tool": tool,                   # spam | summarize | generate | grammar | draft | send | calendar
            "detail": (detail or "")[:80],  # sirf chhota label, email ka body kabhi nahi
            "status": status,
            "at": datetime.now(timezone.utc),
        }
        if thread_id:
            doc["thread_id"] = thread_id    # click karke draft wapas kholne ke liye
        events.insert_one(doc)
    except Exception:
        pass  # stats fail ho to tool call kabhi nahi tootna chahiye


async def log(user: dict, tool: str, detail: str, status: str,
              thread_id: Optional[str] = None) -> None:
    await run_in_threadpool(_record, user, tool, detail, status, thread_id)


def _resolve(user: dict, thread_id: str, status: str) -> None:
    """Draft ka decision hone par uski 'awaiting_approval' row ka status badal do."""
    try:
        events.update_one(
            {"user_id": user["_id"], "thread_id": thread_id, "status": "awaiting_approval"},
            {"$set": {"status": status}},
        )
    except Exception:
        pass


async def resolve(user: dict, thread_id: str, status: str) -> None:
    await run_in_threadpool(_resolve, user, thread_id, status)


def _build_stats(user_id) -> dict:
    counts: dict[tuple, int] = {}
    for row in events.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"tool": "$tool", "status": "$status"}, "n": {"$sum": 1}}},
    ]):
        counts[(row["_id"]["tool"], row["_id"]["status"])] = row["n"]

    def tool_total(tool):
        return sum(n for (t, _), n in counts.items() if t == tool)

    latest = list(events.find({"user_id": user_id}).sort("at", DESCENDING).limit(5))
    seen = {d["_id"] for d in latest}
    pending = events.find(
        {"user_id": user_id, "status": "awaiting_approval", "thread_id": {"$exists": True}}
    ).sort("at", DESCENDING).limit(3)
    latest += [d for d in pending if d["_id"] not in seen]
    latest.sort(key=lambda d: d["at"], reverse=True)

    recent = []
    for e in latest:
        item = {
            "id": str(e["_id"]),
            "tool": e["tool"],
            "detail": e["detail"],
            "status": e["status"],
            "at": e["at"].replace(tzinfo=timezone.utc).isoformat(),
        }
        # thread_id sirf pending draft ke liye bhejte hain (wahi resume ho sakta hai)
        if e.get("thread_id") and e["status"] == "awaiting_approval":
            item["thread_id"] = e["thread_id"]
        recent.append(item)

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