"""Upload photos to Cloudinary and return public URLs."""
import cloudinary
import cloudinary.uploader
from backend.config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


async def upload_image(file_bytes: bytes, filename: str) -> str:
    """Upload raw bytes to Cloudinary. Returns the secure public URL."""
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="crosslist-eu",
        public_id=filename,
        overwrite=True,
        resource_type="image",
    )
    return result["secure_url"]
