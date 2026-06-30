"""Upload photos to Supabase Storage and return public URLs."""
from backend.database import get_db

BUCKET = "photos"


async def upload_image(file_bytes: bytes, filename: str) -> str:
    """Upload raw bytes to Supabase Storage. Returns the public URL."""
    db = get_db()

    # Ensure bucket exists (no-op if already exists)
    try:
        db.storage.create_bucket(BUCKET, options={"public": True})
    except Exception:
        pass  # bucket already exists

    db.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"upsert": "true"},
    )

    result = db.storage.from_(BUCKET).get_public_url(filename)
    return result
