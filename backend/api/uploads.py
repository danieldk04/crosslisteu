"""
Photo upload endpoint — stores to Supabase Storage bucket 'photos'.
"""
import uuid
import mimetypes
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.database import get_db

router = APIRouter(prefix="/uploads", tags=["uploads"])
BUCKET = "photos"
MAX_SIZE = 25 * 1024 * 1024  # 25 MB
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/photo")
async def upload_photo(file: UploadFile = File(...)):
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if content_type not in ALLOWED:
        raise HTTPException(status_code=400, detail="Alleen JPG, PNG, WEBP of GIF toegestaan")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="Bestand te groot (max 25 MB)")

    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
    path = f"{uuid.uuid4()}.{ext}"

    db = get_db()
    db.storage.from_(BUCKET).upload(path, data, {"content-type": content_type, "upsert": "false"})

    public_url = db.storage.from_(BUCKET).get_public_url(path)
    return {"url": public_url, "path": path}
