from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models import ListingCreate
from backend.database import get_db
from backend.services.crosslist import publish_to_platforms, handle_item_sold
from datetime import datetime, timezone

router = APIRouter(prefix="/listings", tags=["listings"])

# Hardcoded single-user ID for MVP — replace with auth middleware for SaaS
MVP_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/")
async def list_all_listings(limit: int = 200, platform: str = None, status: str = None):
    db = get_db()
    q = db.table("listings").select("*")
    if platform:
        q = q.eq("platform", platform)
    if status:
        q = q.eq("status", status)
    result = q.limit(limit).execute()
    return result.data


@router.post("/publish")
async def publish_listing(body: ListingCreate, background_tasks: BackgroundTasks):
    """Publish an item to one or more platforms concurrently."""
    results = await publish_to_platforms(body.item_id, body.platforms, MVP_USER_ID)
    return {"results": results}


@router.get("/item/{item_id}")
async def get_listings_for_item(item_id: str):
    db = get_db()
    result = db.table("listings").select("*").eq("item_id", item_id).execute()
    return result.data


@router.post("/mark-active")
async def mark_listing_active(body: dict):
    """Manually mark a listing as active (for when user published manually via platform UI)."""
    item_id = body.get("item_id")
    platform = body.get("platform")
    if not item_id or not platform:
        raise HTTPException(status_code=400, detail="item_id and platform required")
    db = get_db()
    existing = db.table("listings").select("id").eq("item_id", item_id).eq("platform", platform).execute()
    now = datetime.now(timezone.utc).isoformat()
    if existing.data:
        db.table("listings").update({
            "status": "active",
            "error_message": None,
            "listed_at": now,
        }).eq("item_id", item_id).eq("platform", platform).execute()
    else:
        db.table("listings").insert({
            "item_id": item_id,
            "platform": platform,
            "status": "active",
            "listed_at": now,
        }).execute()
    return {"ok": True}


@router.post("/sold")
async def mark_sold(item_id: str, platform: str, background_tasks: BackgroundTasks):
    """Manually trigger sold flow (webhook fallback)."""
    background_tasks.add_task(handle_item_sold, item_id, platform)
    return {"status": "delist_triggered"}
