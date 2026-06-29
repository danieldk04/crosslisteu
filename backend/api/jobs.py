"""
Job queue API — Chrome extension polls these endpoints.
"""
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from datetime import datetime, timezone

router = APIRouter(prefix="/jobs", tags=["jobs"])
MVP_USER_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/pending")
async def get_pending_jobs(platform: str = None):
    """Extension polls this. Optionally filter by platform."""
    db = get_db()
    q = db.table("jobs").select("*").eq("user_id", MVP_USER_ID).eq("status", "pending")
    if platform:
        q = q.eq("platform", platform)
    result = q.order("created_at").limit(5).execute()
    return result.data


@router.post("/{job_id}/claim")
async def claim_job(job_id: str):
    """Extension claims a job before processing (prevents double processing)."""
    db = get_db()
    result = db.table("jobs").update({
        "status": "claimed",
        "claimed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).eq("status", "pending").execute()
    if not result.data:
        raise HTTPException(status_code=409, detail="Job already claimed or not found")
    return result.data[0]


@router.post("/{job_id}/complete")
async def complete_job(job_id: str, body: dict):
    """Extension reports success. body: {platform_listing_id, platform_listing_url}"""
    db = get_db()
    job = db.table("jobs").select("*").eq("id", job_id).single().execute().data
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    db.table("jobs").update({
        "status": "done",
        "result": body,
        "done_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()

    # Update or create listing record
    if job["action"] == "create":
        if body.get("platform_listing_id"):
            existing = db.table("listings").select("id").eq("item_id", job["item_id"]).eq("platform", job["platform"]).execute()
            if existing.data:
                # Update all matching rows — avoids stale duplicates staying "pending"
                db.table("listings").update({
                    "platform_listing_id": body["platform_listing_id"],
                    "platform_listing_url": body.get("platform_listing_url"),
                    "status": "active",
                    "listed_at": datetime.now(timezone.utc).isoformat(),
                }).eq("item_id", job["item_id"]).eq("platform", job["platform"]).execute()
            else:
                db.table("listings").insert({
                    "item_id": job["item_id"],
                    "platform": job["platform"],
                    "platform_listing_id": body["platform_listing_id"],
                    "platform_listing_url": body.get("platform_listing_url"),
                    "status": "active",
                    "listed_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
        else:
            # Extension reported success but sent no listing ID — mark error
            db.table("listings").update({
                "status": "error",
                "error_message": "Extension completed job but returned no platform_listing_id",
            }).eq("item_id", job["item_id"]).eq("platform", job["platform"]).execute()

    elif job["action"] == "delete":
        db.table("listings").update({"status": "delisted"}).eq("item_id", job["item_id"]).eq("platform", job["platform"]).execute()

    return {"ok": True}


@router.post("/{job_id}/error")
async def fail_job(job_id: str, body: dict):
    """Extension reports failure. body: {error: '...'}"""
    db = get_db()
    job = db.table("jobs").select("item_id,platform,action").eq("id", job_id).single().execute().data
    db.table("jobs").update({
        "status": "error",
        "result": body,
        "done_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()
    # Keep listing in sync — pending listings must become error so the dashboard shows it
    if job and job["action"] == "create":
        db.table("listings").update({
            "status": "error",
            "error_message": body.get("error", "Extension reported failure"),
        }).eq("item_id", job["item_id"]).eq("platform", job["platform"]).eq("status", "pending").execute()
    return {"ok": True}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    db = get_db()
    result = db.table("jobs").select("*").eq("id", job_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found")
    return result.data
