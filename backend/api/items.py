from fastapi import APIRouter, HTTPException
from backend.models import ItemCreate, ItemOut
from backend.database import get_db
import uuid

MVP_USER_ID = "00000000-0000-0000-0000-000000000001"

# Fields not yet in the DB schema. To persist these, run in Supabase SQL editor:
#   ALTER TABLE items ADD COLUMN IF NOT EXISTS shopify_title TEXT;
#   ALTER TABLE items ADD COLUMN IF NOT EXISTS compare_at_price NUMERIC;
# Then remove from this set.
_PENDING_COLUMNS = set()

router = APIRouter(prefix="/items", tags=["items"])


def _strip_missing(data: dict) -> dict:
    """Remove columns that don't exist in the DB yet to prevent insert errors."""
    return {k: v for k, v in data.items() if k not in _PENDING_COLUMNS}


@router.post("/", response_model=dict)
async def create_item(item: ItemCreate):
    db = get_db()
    data = item.model_dump()
    data["id"] = str(uuid.uuid4())
    if not data.get("sku"):
        data["sku"] = f"REV-{data['id'][:8].upper()}"
    result = db.table("items").insert(_strip_missing(data)).execute()
    return result.data[0]


@router.get("/", response_model=list)
async def list_items(limit: int = 50, offset: int = 0):
    db = get_db()
    result = db.table("items").select("*").range(offset, offset + limit - 1).execute()
    return result.data


@router.get("/{item_id}")
async def get_item(item_id: str):
    db = get_db()
    result = db.table("items").select("*").eq("id", item_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return result.data


@router.patch("/{item_id}")
async def update_item(item_id: str, updates: dict):
    db = get_db()
    result = db.table("items").update(_strip_missing(updates)).eq("id", item_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return result.data[0]


@router.delete("/{item_id}")
async def delete_item(item_id: str):
    db = get_db()
    listing_ids = [l["id"] for l in (db.table("listings").select("id").eq("item_id", item_id).execute().data or [])]
    for lid in listing_ids:
        db.table("sync_events").delete().eq("listing_id", lid).execute()
    db.table("listings").delete().eq("item_id", item_id).execute()
    db.table("jobs").delete().eq("item_id", item_id).execute()
    db.table("items").delete().eq("id", item_id).execute()
    return {"deleted": item_id}


@router.post("/{item_id}/delist")
async def delist_item(item_id: str):
    """Delist item from all active platforms (API platforms immediately, extension via job queue)."""
    from backend.services.crosslist import delist_all_platforms
    results = await delist_all_platforms(item_id, MVP_USER_ID)
    return {"item_id": item_id, "results": results}


@router.post("/{item_id}/crosslist")
async def crosslist_item(item_id: str, body: dict):
    """
    Publish item to one or more platforms.
    Body: {"platforms": ["marktplaats", "2dehands", "vinted", "ebay"]}
    """
    platforms = body.get("platforms", [])
    if not platforms:
        raise HTTPException(status_code=400, detail="No platforms specified")

    from backend.services.crosslist import publish_to_platforms
    results = await publish_to_platforms(item_id, platforms, MVP_USER_ID)
    return {"item_id": item_id, "results": results}
